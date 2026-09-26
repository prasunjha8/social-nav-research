# social-nav-research/launch/social_nav.launch.py
from launch import LaunchDescription
from launch.actions import ExecuteProcess
from launch_ros.actions import Node

def generate_launch_description():
    return LaunchDescription([
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=[
                '/model/person_1/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist',
                '/model/person_2/cmd_vel@geometry_msgs/msg/Twist@ignition.msgs.Twist',
                # your existing camera/robot bridges go here too, once we see train_rl.py
            ],
            output='screen'
        ),
        ExecuteProcess(
            cmd=['python3', 'scripts/orca_pedestrian_node.py'],
            cwd='.',  # run from social-nav-research/ so relative paths still work
            output='screen'
        ),
    ])