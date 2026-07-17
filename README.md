
# Vision-Guided Socially Aware Navigation for Assistive Mobility

## Research Project
A vision-based RL navigation agent for assistive mobility robots in crowded indoor environments.
No LiDAR. No depth sensors. Camera only.

## Stack
- ROS 2 Humble
- Gazebo Ignition Fortress
- Stable-Baselines3 (PPO)
- OpenCV
- Python 3.10

## Setup
```bash
# Install dependencies
sudo apt install -y ros-humble-ros-gz-sim ros-humble-ros-gz-bridge ros-humble-ros-gz-sim-demos
pip install "numpy<2" opencv-python stable-baselines3 gymnasium tensorboard

# Source ROS
source /opt/ros/humble/setup.bash

# Launch simulation
ros2 launch ros_gz_sim gz_sim.launch.py gz_args:="-r worlds/hospital_corridor.sdf"
```

## Structure
social_nav/
├── worlds/          # Gazebo SDF world files
├── scripts/         # Python ROS nodes and RL training
├── models/          # Robot URDF/SDF files
├── results/         # Training plots and metrics
└── docs/            # Paper notes and references
## Progress
- [x] Gazebo environment with hospital corridor
- [x] Ackermann robot with camera
- [x] OpenCV hazard detection pipeline
- [x] Gymnasium RL environment
- [ ] PPO training complete
- [ ] Benchmark vs Nav2
- [ ] Paper writing
EOF
