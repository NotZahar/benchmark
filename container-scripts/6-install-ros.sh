#!/usr/bin/env zsh

set -euo pipefail

ROS_DISTRO="${ROS_DISTRO:-lyrical}"

add-apt-repository universe
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key \
	-o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" \
	| tee /etc/apt/sources.list.d/ros2.list >/dev/null

apt update
apt install -y \
	"ros-${ROS_DISTRO}-ros-base" \
	"ros-${ROS_DISTRO}-rmw-cyclonedds-cpp" \
	"ros-${ROS_DISTRO}-rmw-fastrtps-cpp" \
	"ros-${ROS_DISTRO}-rmw-zenoh-cpp" \
	python3-colcon-common-extensions \
	python3-rosdep \
	python3-vcstool

rosdep init || true
rosdep update --rosdistro "$ROS_DISTRO"
rm -rf /var/lib/apt/lists/*
