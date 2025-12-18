#!/bin/bash

set -eu

APT_PACKAGES=(
	"build-essential"
	"cmake"
	"git"
	"curl"
	"gnupg2"
	"lsb-release"
	"software-properties-common"
	"pkg-config"
	"libssl-dev"
	"libacl1-dev"
	"libncurses5-dev"
	"htop"
	"linux-tools-generic"
	"gdb"
	"libclang-dev"
	"wget"
)

apt update
for APT_PACKAGE in "${APT_PACKAGES[@]}"; do
	echo "Installing: $APT_PACKAGE"
	apt install -y "$APT_PACKAGE"
done

add-apt-repository -y ppa:deadsnakes/ppa
apt update
apt install -y libpython3.13

# LLVM
cd /tmp
wget https://apt.llvm.org/llvm.sh
chmod +x llvm.sh
./llvm.sh 20 all

# Rust
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs |
	RUSTUP_DIST_SERVER=https://mirrors.tuna.tsinghua.edu.cn/rustup \
		RUSTUP_UPDATE_ROOT=https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup \
		sh -s -- -y
source "$HOME/.cargo/env"

# ROS 2
add-apt-repository universe
curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] https://mirrors.tuna.tsinghua.edu.cn/ros2/ubuntu $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/ros2.list >/dev/null
apt update
apt install -y \
	ros-jazzy-ros-base \
	ros-jazzy-rmw-cyclonedds-cpp \
	python3-colcon-common-extensions

# Cleanup
rm -rf /var/lib/apt/lists/*
