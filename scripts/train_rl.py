import gymnasium as gym
import numpy as np
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from geometry_msgs.msg import Twist
import cv2
import threading
import time
from stable_baselines3 import PPO
from stable_baselines3.common.env_checker import check_env

class SocialNavEnv(gym.Env):
    def __init__(self):
        super().__init__()
        self.action_space = gym.spaces.Box(
            low=np.array([-1.0, -1.0], dtype=np.float32),
            high=np.array([1.0, 1.0], dtype=np.float32)
        )
        self.observation_space = gym.spaces.Box(
            low=np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32),
            high=np.array([1.0, 1.0, 1.0, 1.0], dtype=np.float32)
        )
        self.current_obs = np.array([0.33, 0.33, 0.33, 0.0], dtype=np.float32)
        self.step_count = 0
        self.max_steps = 200
        self.episode_count = 0
        self.total_reward = 0.0

        if not rclpy.ok():
            rclpy.init()
        self.node = Node('nav_env')
        self.cmd_pub = self.node.create_publisher(Twist, '/cmd_vel', 10)
        self.img_sub = self.node.create_subscription(
            Image, '/camera/image_raw', self._image_callback, 10)
        self.ros_thread = threading.Thread(
            target=rclpy.spin, args=(self.node,), daemon=True)
        self.ros_thread.start()
        print('SocialNavEnv ready.')

    def _image_callback(self, msg):
        frame = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.width, 3)
        frame_bgr = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
        hsv = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2HSV)
        red_mask1 = cv2.inRange(hsv, (0, 100, 100), (10, 255, 255))
        red_mask2 = cv2.inRange(hsv, (160, 100, 100), (180, 255, 255))
        orange_mask = cv2.inRange(hsv, (10, 100, 100), (25, 255, 255))
        person_mask = cv2.bitwise_or(red_mask1, cv2.bitwise_or(red_mask2, orange_mask))
        person_pixels = cv2.countNonZero(person_mask)
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        w = edges.shape[1]
        l = cv2.countNonZero(edges[:, :w//3])
        c = cv2.countNonZero(edges[:, w//3:2*w//3])
        r = cv2.countNonZero(edges[:, 2*w//3:])
        total = max(l + c + r, 1)
        self.current_obs = np.array([
            l / total, c / total, r / total,
            min(person_pixels / 500.0, 1.0)
        ], dtype=np.float32)

    def _send_velocity(self, linear, angular):
        msg = Twist()
        msg.linear.x = float(np.clip(linear, -1.0, 1.0))
        msg.angular.z = float(np.clip(angular, -1.0, 1.0))
        self.cmd_pub.publish(msg)

    def _compute_reward(self, action):
        obs = self.current_obs
        reward = 0.0
        if action[0] > 0:
            reward += 0.3
        reward -= obs[3] * 3.0
        reward -= obs[1] * 1.5
        if obs[1] < 0.2 and obs[3] < 0.1:
            reward += 0.5
        if abs(action[1]) > 0.8 and abs(action[0]) < 0.1:
            reward -= 0.3
        return float(reward)

    def step(self, action):
        self._send_velocity(action[0], action[1])
        time.sleep(0.15)
        obs = self.current_obs.copy()
        reward = self._compute_reward(action)
        self.total_reward += reward
        self.step_count += 1
        terminated = bool(obs[3] > 0.95)
        truncated = self.step_count >= self.max_steps
        if terminated or truncated:
            self.episode_count += 1
            print(f'Episode {self.episode_count} | Steps: {self.step_count} | '
                  f'Reward: {self.total_reward:.2f} | Collision: {terminated}')
            self.total_reward = 0.0
        return obs, reward, terminated, truncated, {}

    def reset(self, seed=None, options=None):
        self._send_velocity(0.0, 0.0)
        self.step_count = 0
        time.sleep(0.3)
        return self.current_obs.copy(), {}

    def close(self):
        self._send_velocity(0.0, 0.0)
        self.node.destroy_node()

if __name__ == '__main__':
    print('Checking environment...')
    env = SocialNavEnv()
    check_env(env, warn=True)
    print('Environment check passed! Starting PPO training...')
    model = PPO('MlpPolicy', env, verbose=1,
                learning_rate=3e-4, n_steps=512,
                batch_size=64, n_epochs=10)
    model.learn(total_timesteps=10000)
    model.save('/tmp/social_nav_ppo')
    print('Model saved to /tmp/social_nav_ppo')
    env.close()
