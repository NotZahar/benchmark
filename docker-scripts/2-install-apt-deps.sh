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
	"python3-venv"
	"protobuf-compiler"
	"libprotobuf-dev"
	"clangd-20"
	"clang-format-20"
	"libncurses-dev"
	"ninja-build"
)

apt update
if apt install -y "${APT_PACKAGES[@]}"; then
	echo "All packages installed successfully!"
else
	echo "Error: Some packages failed to install!" >&2
	exit 1
fi

# Cmake-format
echo "Start to install cmake-format ..."
python3 -m venv /tmp
. /tmp/bin/activate
pip install cmake-format

# Shfmt
echo "Start to install shfmt ..."
SHFMT_VERSION="v3.8.0"
wget -q "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_linux_amd64" -O /usr/local/bin/shfmt
chmod +x /usr/local/bin/shfmt

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
	ros-jazzy-rmw-fastrtps-cpp \
	ros-jazzy-iceoryx-posh \
	ros-jazzy-iceoryx-binding-c \
	ros-jazzy-iceoryx-hoofs \
	python3-colcon-common-extensions \
	python3-rosdep \
	python3-vcstool

# Clean up
apt clean && rm -rf /var/lib/apt/lists/*
