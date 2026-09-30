# Vision-Guided Socially Aware Navigation for Assistive Mobility

Camera-only navigation for assistive mobility robots in crowded indoor environments. The project studies whether visual scene semantics derived from a vision-language model (VLM) can improve socially aware navigation compared with a reactive PPO policy using camera/OpenCV features alone. No LiDAR or depth sensor is used.

## Research Question

Can VLM-derived scene understanding improve social navigation quality in a simulated hospital corridor?

The headline outcome is social navigation quality: proxemics violations, path legibility, collision rate, and the time-to-goal trade-off. VLM-derived semantics are the proposed method, supplied to the policy as observation features or used for reward shaping. The required baseline is PPO trained on raw camera/OpenCV features without VLM input; a run without moving pedestrians does not count as this baseline.

## Stack

- ROS 2 Humble and Gazebo Ignition Fortress
- Python 3.10, Gymnasium, Stable-Baselines3 PPO
- OpenCV; camera-only perception
- RVO2 for ORCA pedestrian control

## Repository Layout

```text
launch/       ROS launch configuration
models/       robot SDF/URDF models
scripts/      ORCA pedestrian node, hazard detector, and RL training environment
worlds/       Gazebo worlds, including hospital_corridor.sdf
```

An optional, larger crowd stress-test using Open-RMF's Airport Terminal world
is documented in [docs/crowded_area_benchmark.md](docs/crowded_area_benchmark.md).
The hospital corridor remains the controlled baseline environment.

## Setup

Install ROS/Gazebo bridge packages once, then install the Python dependencies in the Python environment used with ROS 2:

```bash
sudo apt install -y ros-humble-ros-gz-sim ros-humble-ros-gz-bridge \
  ros-humble-ros-gz-sim-demos ros-humble-tf2-msgs
python3 -m pip install "numpy<2" opencv-python stable-baselines3 gymnasium tensorboard
```

The ORCA node also requires `rvo2`. Its source/build instructions are in the docstring at the top of `scripts/orca_pedestrian_node.py`; it is not installed by the command above. Check the Python environment before starting:

```bash
python3 -c 'import rclpy, rvo2; from tf2_msgs.msg import TFMessage; print("ROS, RVO2, and TF dependencies are available")'
```

## Start The Pedestrian Simulation

Run each numbered step in a separate terminal. Source ROS 2 in every terminal. These commands start Gazebo and the two ORCA-controlled pedestrians; the complete robot-camera bridge and training workflow are not yet wired into one launch command.

1. Start the world:

   ```bash
   cd ~/social-nav-research
   source /opt/ros/humble/setup.bash
   ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r worlds/hospital_corridor.sdf"
   ```

2. Start the pedestrian command bridges and Gazebo dynamic-pose bridge:

   ```bash
   cd ~/social-nav-research
   source /opt/ros/humble/setup.bash
   ros2 run ros_gz_bridge parameter_bridge \
     '/model/person_1/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist' \
     '/model/person_2/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist' \
     '/world/hospital_corridor/dynamic_pose/info@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V'
   ```

3. Start the ORCA node:

   ```bash
   cd ~/social-nav-research
   source /opt/ros/humble/setup.bash
   python3 scripts/orca_pedestrian_node.py
   ```

4. To inspect the pose topic, run this in another sourced terminal:

   ```bash
   ros2 topic echo /world/hospital_corridor/dynamic_pose/info
   ```

   The observed `child_frame_id` values for the pedestrians are `person_1` and `person_2`. After a clean start, check that both remain upright and move as expected. Stop the processes with Ctrl+C in their respective terminals.

## Current Status

- Hospital corridor world, Ackermann robot model, and camera-based hazard-detection prototype are present.
- A Gymnasium/PPO training prototype is present; a valid moving-pedestrian baseline has not yet been trained.
- The ORCA node controls `person_1` and `person_2`, samples an episode-persistent responsiveness flag per pedestrian, and includes the robot in that pedestrian's ORCA calculation when responsive.
- The node subscribes to `/world/hospital_corridor/dynamic_pose/info`; observed frame names match its lookup, and Gazebo poses replace dead-reckoned positions after the first message.
- ORCA now registers 2D footprints for the main corridor walls, trolley, bench, cart, and static `person_3`; these footprints are manually mirrored from the SDF and must be kept synchronized if the world geometry changes.
- Both dynamic pedestrian links are configured as kinematic. The latest report says pedestrians routed around static furniture and no longer toppled on contact; a fresh run is still needed after correcting `person_2`'s misplaced kinematic tag in the local SDF.
- The world file now removes the goal-marker collision, uses the relative `../models/robot.sdf` include, and omits the unused inertial block from static `person_3`.
- Robot avoidance in ORCA is gated by each pedestrian's episode-level responsiveness flag. Geometric line-of-sight gating is not implemented yet.
- The pedestrian command and pose bridges have been exercised from the command line. `launch/social_nav.launch.py` currently includes only the two command bridges, not the dynamic-pose bridge or robot/camera bridges.
- Rooms 1 and 2 remain sealed. `person_3` is currently static; the recommendation is to keep it static for now, with two ORCA-driven pedestrians and one standing obstacle.

## Next Steps

1. Fully restart Gazebo and verify both pedestrians stay upright and route around each other, the robot when they are responsive, and the registered static footprints after the `person_2` SDF correction.
2. Call `/reset_pedestrians` from `SocialNavEnv.reset()` and add geometric line-of-sight gating, so pedestrian positions, goals, and responsiveness reset correctly and robot visibility follows the scenario definition.
3. Define numeric proxemics thresholds and a path-legibility metric, then implement the H2INT-style reward terms and metric logging.
4. Train the real PPO baseline end to end with camera/OpenCV observations and moving, partially responsive pedestrians. Previous no-pedestrian convergence does not count as this baseline.
5. Once the baseline is reproducible, add VLM-derived semantics and compare social-navigation metrics; then benchmark against Nav2 and write up the results.

## Research Reference

Ao Shen et al., "Human-Human & Human-Robot Interaction Transformer (H2INT) for Robot Navigation in Dense and Uncertain Crowds," [arXiv:2609.05300](https://arxiv.org/abs/2609.05300).

Use this work as a source for the ORCA-plus-responsiveness formulation, reward template (Eqs. 5-7), and evaluation metrics. Do not attempt to extend its architecture: its observations are relative 2D positions, while this project focuses on camera-only perception and VLM-derived scene understanding.

## License and Third-Party Material

Original project code, models, worlds, and documentation are licensed under the MIT License; see [LICENSE](LICENSE). This does not relicense third-party software or research material. The ORCA implementation is provided by the separately installed [Python-RVO2 project](https://github.com/sybrenstuvel/Python-RVO2), which is Apache-2.0 licensed. The H2INT paper remains subject to its own terms; cite the arXiv page rather than redistributing the downloaded PDF unless its applicable license explicitly permits that.