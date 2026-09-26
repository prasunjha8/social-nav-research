#!/usr/bin/env python3
"""
ORCA-based pedestrian controller for hospital_corridor.sdf.

Drives person_1..person_N as dynamic cylinders via Gazebo's VelocityControl
plugin (bridged /model/person_i/cmd_vel topics), using RVO2 for local
collision avoidance and a per-pedestrian, per-episode "responsiveness" flag
(H2INT-style, arXiv:2609.05300 Eq. 3) that determines whether that pedestrian
even perceives the robot as an obstacle.

Requires: pip-installed `rvo2` (build from source: see
https://github.com/sybrenstuvel/Python-RVO2 -- needs CMake + Cython,
`python setup.py build && python setup.py install`, not a plain PyPI package).

This is a first working version, not a finished one. Known simplifications
called out inline with TODOs -- read those before assuming this is closed-loop
correct.
"""

import math
import random

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist, PoseStamped
from std_srvs.srv import Trigger
from tf2_msgs.msg import TFMessage

import rvo2

# ---- Corridor / scenario constants (from hospital_corridor.sdf) ----
CORRIDOR_X_MIN, CORRIDOR_X_MAX = -9.0, 9.0
CORRIDOR_Y_MIN, CORRIDOR_Y_MAX = -3.5, 3.5
NUM_PEDESTRIANS = 2
PED_RADIUS = 0.3
PED_MAX_SPEED = 1.2
ROBOT_RADIUS = 0.35
TIMESTEP = 0.1          # 10 Hz control loop
MEAN_RESPONSIVENESS = 0.6   # rho_resp, H2INT Eq. 3
GOAL_TOLERANCE = 0.4


class Pedestrian:
    def __init__(self, pid: int):
        self.id = pid
        self.pos = (0.0, 0.0)
        self.goal = (0.0, 0.0)
        self.responsive = True   # resampled every episode, held fixed within it
        self.pos_confirmed = False  # True once we've received a real pose from Gazebo


class OrcaPedestrianNode(Node):
    def __init__(self):
        super().__init__('orca_pedestrian_node')

        self.declare_parameter('robot_pose_topic', '/model/ackermann_robot/pose')
        robot_topic = self.get_parameter('robot_pose_topic').value

        self.robot_pos = (-8.0, 0.0)

        self.pedestrians = [Pedestrian(i) for i in range(1, NUM_PEDESTRIANS + 1)]
        self._reset_episode()

        self.cmd_pubs = {
            p.id: self.create_publisher(Twist, f'/model/person_{p.id}/cmd_vel', 10)
            for p in self.pedestrians
        }

        self.create_subscription(PoseStamped, robot_topic, self._robot_pose_cb, 10)
        self.create_subscription(
            TFMessage,
            '/world/hospital_corridor/dynamic_pose/info',
            self._dynamic_pose_cb,
            10,
        )
        self.create_service(Trigger, 'reset_pedestrians', self._handle_reset)

        self.timer = self.create_timer(TIMESTEP, self._step)
        self.get_logger().info(
            f'ORCA pedestrian node running with {NUM_PEDESTRIANS} agents, '
            f'mean responsiveness={MEAN_RESPONSIVENESS}'
        )

    # ---- episode management ----

    def _reset_episode(self):
        """Randomize start/goal (opposite ends of the corridor) and resample
        each pedestrian's responsiveness flag. Call this from the Gym env's
        reset() via the /reset_pedestrians service so pedestrian state doesn't
        carry over between RL episodes."""
        for p in self.pedestrians:
            side = random.choice([-1, 1])
            y_start = random.uniform(CORRIDOR_Y_MIN + 0.5, CORRIDOR_Y_MAX - 0.5)
            y_goal = random.uniform(CORRIDOR_Y_MIN + 0.5, CORRIDOR_Y_MAX - 0.5)
            p.pos = (side * (CORRIDOR_X_MAX - 0.5), y_start)
            p.goal = (-side * (CORRIDOR_X_MAX - 0.5), y_goal)
            p.responsive = random.random() < MEAN_RESPONSIVENESS
        self.get_logger().info(
            'Episode reset: '
            + ', '.join(f'ped{p.id} responsive={p.responsive}' for p in self.pedestrians)
        )

    def _handle_reset(self, request, response):
        self._reset_episode()
        response.success = True
        response.message = 'pedestrians reset'
        return response

    def _robot_pose_cb(self, msg: PoseStamped):
        self.robot_pos = (msg.pose.position.x, msg.pose.position.y)

    def _dynamic_pose_cb(self, msg: TFMessage):
        """Ground-truth pose feedback from Gazebo's scene broadcaster, via
        /world/hospital_corridor/dynamic_pose/info. Replaces the earlier
        dead-reckoned position estimate with the real simulated pose, so the
        ORCA computation reacts to where the pedestrian actually is, not
        where our own open-loop integration guessed it might be.

        NOTE: child_frame_id matching below assumes it equals the plain
        model name ("person_1", "person_2"). Verify with
        `ros2 topic echo /world/hospital_corridor/dynamic_pose/info`
        and adjust the match below if Gazebo is using a different
        (e.g. scoped) frame naming convention on your version.
        """
        by_id = {f'person_{p.id}': p for p in self.pedestrians}
        for transform in msg.transforms:
            frame = transform.child_frame_id
            ped = by_id.get(frame)
            if ped is None:
                continue
            t = transform.transform.translation
            ped.pos = (t.x, t.y)
            ped.pos_confirmed = True

    # ---- per-step control ----

    def _step(self):
        for ped in self.pedestrians:
            if self._reached_goal(ped):
                self._respawn_goal(ped)

            vx, vy = self._compute_orca_velocity(ped)

            if not ped.pos_confirmed:
                # No ground-truth pose received yet (bridge not up, or this
                # is the very first tick before the first /dynamic_pose/info
                # message has arrived) -- fall back to dead-reckoning so the
                # node still does *something* sensible rather than commanding
                # from a stale (0,0)-ish position. This self-corrects the
                # moment the first real pose callback fires.
                ped.pos = (ped.pos[0] + vx * TIMESTEP, ped.pos[1] + vy * TIMESTEP)
            # else: ped.pos is kept up to date by _dynamic_pose_cb directly.

            self._publish_cmd(ped, vx, vy)

    def _reached_goal(self, ped: Pedestrian) -> bool:
        dx = ped.goal[0] - ped.pos[0]
        dy = ped.goal[1] - ped.pos[1]
        return math.hypot(dx, dy) < GOAL_TOLERANCE

    def _respawn_goal(self, ped: Pedestrian):
        """Pedestrian reached its goal mid-episode -- give it a new one at the
        far end so it keeps moving instead of idling for the rest of the
        episode. Responsiveness flag is NOT resampled here (H2INT keeps it
        temporally persistent within an episode)."""
        side = 1 if ped.pos[0] < 0 else -1
        y_goal = random.uniform(CORRIDOR_Y_MIN + 0.5, CORRIDOR_Y_MAX - 0.5)
        ped.goal = (side * (CORRIDOR_X_MAX - 0.5), y_goal)

    def _compute_orca_velocity(self, ped: Pedestrian):
        """Builds a throwaway RVO2 simulator scoped to what THIS pedestrian
        can see: every other pedestrian always, the robot only if `responsive`
        is True. This is what implements the H2INT-style per-agent visibility
        -- plain RVO2 has no native per-agent neighbor masking, so each
        pedestrian gets its own small simulator instance instead of sharing
        one global sim. Cheap at this scale (2-4 agents); would need a
        different approach at H2INT's 30-pedestrian scale."""
        sim = rvo2.PyRVOSimulator(
            TIMESTEP,       # timeStep
            3.0,            # neighborDist
            5,              # maxNeighbors
            2.0,            # timeHorizon (agents)
            2.0,            # timeHorizonObst
            PED_RADIUS,
            PED_MAX_SPEED,
        )

        self_id = sim.addAgent(ped.pos)

        for other in self.pedestrians:
            if other.id == ped.id:
                continue
            sim.addAgent(other.pos)

        if ped.responsive:
            # Robot added as a near-static obstacle-like agent: near-zero max
            # speed since we don't model the robot's own avoidance intent here,
            # just its current position as something to avoid.
            sim.addAgent(self.robot_pos, 3.0, 5, 2.0, 2.0, ROBOT_RADIUS, 0.01, (0.0, 0.0))

        goal_dx = ped.goal[0] - ped.pos[0]
        goal_dy = ped.goal[1] - ped.pos[1]
        dist = max(math.hypot(goal_dx, goal_dy), 1e-6)
        pref_vel = (goal_dx / dist * PED_MAX_SPEED, goal_dy / dist * PED_MAX_SPEED)
        sim.setAgentPrefVelocity(self_id, pref_vel)

        # Other agents in this throwaway sim don't have a real preferred
        # velocity here (we're only solving for `ped`'s own avoidance
        # response) -- give them zero preference so ORCA just treats them as
        # near-stationary obstacles rather than actively fleeing.
        for i in range(sim.getNumAgents()):
            if i != self_id:
                sim.setAgentPrefVelocity(i, (0.0, 0.0))

        sim.doStep()
        return sim.getAgentVelocity(self_id)

    def _publish_cmd(self, ped: Pedestrian, vx: float, vy: float):
        msg = Twist()
        msg.linear.x = vx
        msg.linear.y = vy
        self.cmd_pubs[ped.id].publish(msg)


def main():
    rclpy.init()
    node = OrcaPedestrianNode()
    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()