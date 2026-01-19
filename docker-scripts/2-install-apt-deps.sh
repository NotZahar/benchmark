#!/bin/bash

set -e

download_with_retry() {
	local url="$1"
	local output="$2"
	local max_retries=5
	local retry_delay=10
	local timeout=180

	for method in curl wget; do
		if command -v $method >/dev/null 2>&1; then
			echo "Trying to download using $method..."

			for i in $(seq 1 $max_retries); do
				echo "Attempt $i of $max_retries..."

				case $method in
				curl)
					if curl -fsSL --max-time $timeout --connect-timeout 30 \
						--retry 3 --retry-delay 5 \
						"$url" -o "$output" 2>/dev/null; then
						echo "Download successful using curl"
						return 0
					fi
					;;
				wget)
					if wget --timeout=$timeout --tries=3 --waitretry=5 \
						-q "$url" -O "$output" 2>/dev/null; then
						echo "Download successful using wget"
						return 0
					fi
					;;
				esac

				if [ $i -lt $max_retries ]; then
					echo "Download failed, retrying in ${retry_delay}s..."
					sleep $retry_delay
					retry_delay=$((retry_delay * 2)) # Exponential backoff
				fi
			done
		fi
	done

	echo "Failed to download after all attempts"
	return 1
}

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

# Python 3.13
echo "Start to install python 3.13 ..."
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install -y python3.13-dev

# Cmake-format
echo "Start to install cmake-format ..."
python3 -m venv /tmp
. /tmp/bin/activate
pip install cmake-format

# Shfmt
echo "Start to install shfmt ..."
SHFMT_VERSION="v3.8.0"
MAX_RETRIES=3
RETRY_DELAY=2
for i in $(seq 1 $MAX_RETRIES); do
	if curl -fsSL --max-time 30 "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_linux_amd64" -o /usr/local/bin/shfmt; then
		echo "Download successful"
		break
	else
		echo "Download attempt $i failed, retrying in ${RETRY_DELAY}s..."
		sleep $RETRY_DELAY
	fi

	if [ $i -eq $MAX_RETRIES ]; then
		echo "Failed to download shfmt after $MAX_RETRIES attempts"
		exit 1
	fi
done
chmod +x /usr/local/bin/shfmt

# Rust
install_rust() {
	echo "Installing Rust..."

	# Method 1: Direct binary download
	local rustup_binary_url="https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init"

	if download_with_retry "$rustup_binary_url" /tmp/rustup-init; then
		chmod +x /tmp/rustup-init
		echo "Running Rust installer..."
		RUSTUP_DIST_SERVER=https://mirrors.tuna.tsinghua.edu.cn/rustup \
			RUSTUP_UPDATE_ROOT=https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup \
			/tmp/rustup-init -y --default-toolchain stable --profile minimal
		return 0
	fi

	# Method 2: Downloading via Tsinghua mirror directly
	echo "Trying Tsinghua mirror for Rust..."
	if download_with_retry \
		"https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup/archive/stable/x86_64-unknown-linux-gnu/rustup-init" \
		/tmp/rustup-init; then
		chmod +x /tmp/rustup-init
		echo "Running Rust installer from Tsinghua mirror..."
		RUSTUP_DIST_SERVER=https://mirrors.tuna.tsinghua.edu.cn/rustup \
			RUSTUP_UPDATE_ROOT=https://mirrors.tuna.tsinghua.edu.cn/rustup/rustup \
			/tmp/rustup-init -y --default-toolchain stable --profile minimal
		return 0
	fi

	echo "All Rust installation methods failed"
	return 1
}

if install_rust; then
	echo "Rust installed successfully"
	source "$HOME/.cargo/env" 2>/dev/null || true
else
	echo "Error: Failed to install Rust"
	exit 1
fi

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
