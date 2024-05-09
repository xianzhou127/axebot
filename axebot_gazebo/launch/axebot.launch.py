# Copyright (c) 2022 Mateus Menezes

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument, ExecuteProcess,\
                           IncludeLaunchDescription, RegisterEventHandler,\
                           OpaqueFunction,Shutdown
from launch.conditions import IfCondition
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration,PythonExpression

import xacro
import yaml
import time

def load_yaml(yaml_file_path):
    with open(yaml_file_path, 'r') as file:
        return yaml.safe_load(file)


def generate_launch_description():
    pkg_name = 'axebot_description'
    robot_start = 'axebot_gazebo'

    # 获取yaml路径，由于使用的share里的yaml而非当前目录，所以每次修改后需要先colcon build
    robot_setting_config = os.path.join(
      get_package_share_directory(robot_start),
      'config',
      'robot_start.yaml'
    )
    config = load_yaml(robot_setting_config)

    # 获取参数
    number_of_bots = config['number_of_bots']
    world_selection = config['world_selection']
    use_sim_time = config['use_sim_time']

    launch_rviz_arg = DeclareLaunchArgument(
        name='launch_rviz',
        default_value='True',
        description='True if to launch rviz, false otherwise'
    )
    
    world_file = os.path.join(
        get_package_share_directory(pkg_name),
        'world',
        world_selection + '.world'
    )

    xacro_file = os.path.join(
        get_package_share_directory(pkg_name),
        'urdf',
        'start.urdf.xacro'
    )

    rviz_config = os.path.join(
      get_package_share_directory(pkg_name),
      'config',
      f'axebot_{number_of_bots}.rviz'
    )

    def spawn_bots(context, *args, **kwargs):
        launch_description = []

        rviz_node = Node(
            package="rviz2",
            executable="rviz2",
            name="rviz2",
            output="log",
            condition=IfCondition(LaunchConfiguration('launch_rviz')),
            arguments=['-d', rviz_config]
        )

        gazebo = IncludeLaunchDescription(
            PythonLaunchDescriptionSource([os.path.join(
                get_package_share_directory('gazebo_ros'), 'launch'),
                                        '/gazebo.launch.py']),
            launch_arguments={'world': world_file,'verbose': 'true'}.items(),
            # launch_arguments={'verbose': 'true'}.items(),
        )

        for i in range(number_of_bots):
            # 定义namespace，多智能体必须使用namespace，每个机器人使用独立的一套节点
            robot_name = f'axebot_{i}'

            # 获取urdf并传递namespace
            robot_description_raw = xacro.process_file(xacro_file, mappings={'robot_name_rc': robot_name}).toxml()
            
            # 发布urdf
            robot_state_publisher_node = Node(
                    package='robot_state_publisher',
                    executable='robot_state_publisher',
                    output='screen',
                    parameters=[{
                        'robot_description': robot_description_raw,
                        'use_sim_time': use_sim_time,
                        'frame_prefix': f"{robot_name}/",   # 给发布的每个tf添加前缀，然后才能在rviz里的robotmodel设置tf prefix以显示所有机器人。最后有个/必须要加
                    }],
                    namespace=robot_name,  # 为节点设置命名空间
            )

            # 装载模型
            spawn_entity = Node(
                package='gazebo_ros', 
                executable='spawn_entity.py',
                arguments=['-topic', f'/{robot_name}/robot_description',  # robot_state_publisher添加命名空间后topic的应该是/{robot_name}/robot_description
                            '-entity', robot_name,
                            '-x', str(i),   # 修改initial position
                            '-y', str(0),
                            '-z', str(0),
                        ],
                output='screen',
                namespace=robot_name,  # 为节点设置命名空间
            )

            # joint_state发布
            joint_state_broadcaster_spawner = Node(
                package="controller_manager",
                executable="spawner",
                arguments=["joint_state_broadcaster"],
                namespace=robot_name,  # 为节点设置命名空间
            )

            joint_state_broadcaster_event_handler = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=spawn_entity,
                    on_exit=[joint_state_broadcaster_spawner]
                )
            )

            # 控制器
            omni_base_controller_spawner = Node(
                package="controller_manager",
                executable="spawner",
                arguments=["omnidirectional_controller"],
                namespace=robot_name,  # 为节点设置命名空间
            )

            omni_base_controller_event_handler = RegisterEventHandler(
                event_handler=OnProcessExit(
                    target_action=joint_state_broadcaster_spawner,
                    on_exit=[omni_base_controller_spawner]
                )
            )

            # 添加最顶层的ground坐标系连接每个robot
            static_transform_publisher = Node(
                    package='tf2_ros',
                    executable='static_transform_publisher',
                    name='static_transform_publisher',  # Use unique node name
                    namespace=robot_name,  # 为节点设置命名空间
                    arguments=[f'0', '0', '0', '0', '0', '0', f'{robot_name}', f'{robot_name}/base_link'], # 修改初始位置和gazebo一致
                    # arguments=['-x','-y','-z','-yaw','-pitch','-roll','-frame_id','-child_frame_id']
            )

            # transform odom.frame_id and odom.child_frame_id
            transform_frame_id = Node(
                    package='transform_frame_id',
                    executable='transform_frame_id_node',
                    name='transform_frame_id_node',  # Use unique node name
                    namespace=robot_name,
                    parameters=[{

                        'frame_id':f'{robot_name}/odom',
                        'child_frame_id':f'{robot_name}/base_link'
                    }],
            )

            # 添加node
            launch_description.extend([
                joint_state_broadcaster_event_handler,
                omni_base_controller_event_handler,
                robot_state_publisher_node,
                spawn_entity,
                transform_frame_id
                # static_transform_publisher,
            ])

            # time.sleep(1)

        # 单独添加rviz和gazebo
        rviz_event_handler = RegisterEventHandler(
            event_handler=OnProcessExit(
                target_action=omni_base_controller_spawner,
                on_exit=[rviz_node]
            )
        )

        launch_description.extend([
            gazebo,
            rviz_event_handler
        ])

        return launch_description


    return LaunchDescription([
        launch_rviz_arg,
        OpaqueFunction(function=spawn_bots),
    ])
