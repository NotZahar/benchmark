#!/bin/bash

set -e

add-apt-repository universe
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list >/dev/null
apt update
apt install -y \
	ros-jazzy-ros-base \
	ros-jazzy-rmw-cyclonedds-cpp \
	ros-jazzy-rmw-fastrtps-cpp \
	ros-jazzy-iceoryx-posh \
	ros-jazzy-iceoryx-binding-c \
	ros-jazzy-iceoryx-hoofs \
	python3-colcon-common-extensions \
	python3-rosdep \
	python3-vcstool
