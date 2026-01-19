#!/bin/bash

set -e

BUILD_DIR="/root/libs"

mkdir -p $BUILD_DIR

echo "Building ZeroMQ ..."
cd $BUILD_DIR
git clone https://github.com/zeromq/libzmq.git
cd libzmq
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DWITH_PERF_TOOL=OFF -DZMQ_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building cppzmq ..."
cd $BUILD_DIR
git clone https://github.com/zeromq/cppzmq.git
cd cppzmq
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCPPZMQ_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building Flatbuffers ..."
cd $BUILD_DIR
git clone https://github.com/google/flatbuffers.git
cd flatbuffers
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DFLATBUFFERS_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building Iceoryx ..."
mkdir -p ~/iceoryx_ws/src
cd ~/iceoryx_ws
source /opt/ros/jazzy/setup.bash
rosdep init || true
rosdep update
vcs import src/ <<EOF
repositories:
  rmw_iceoryx:
    type: git
    url: https://github.com/ros2/rmw_iceoryx.git
    version: jazzy
  rcl_interfaces:
    type: git
    url: https://github.com/ros2/rcl_interfaces.git
    version: jazzy
  test_interface_files:
    type: git
    url: https://github.com/ros2/test_interface_files.git
    version: jazzy
EOF
find src/ -name "package.xml" | head -10
colcon list --names-only
if ! rosdep install --from-paths src --ignore-src -y --rosdistro jazzy 2>&1 | grep -q "Failed to install"; then
	echo "rosdep finished successfully."
else
	echo "rosdep encountered errors but continuing."
fi
colcon build --packages-select test_interface_files --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release --allow-overriding builtin_interfaces
source install/setup.bash
colcon build --packages-select test_msgs --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release --allow-overriding builtin_interfaces
source install/setup.bash
colcon build --packages-up-to rmw_iceoryx_cpp --symlink-install --cmake-args -DCMAKE_BUILD_TYPE=Release
echo "source ~/iceoryx_ws/install/setup.bash" >>~/.bashrc

echo "Building Iceoryx2 ..."
ICEORYX2_VERSION="v0.8.1"
git clone --branch ${ICEORYX2_VERSION} https://github.com/eclipse-iceoryx/iceoryx2.git /tmp/iceoryx2
cd /tmp/iceoryx2
rm -f Cargo.lock
RUSTFLAGS="--cfg tokio_unstable" cargo build \
	--release \
	--package iceoryx2-ffi-c \
	-Z unstable-options \
	--config "build.rustflags=['--cfg', 'tokio_unstable']"
RUSTFLAGS="--cfg tokio_unstable" cargo build \
	--release \
	--package iceoryx2-cpp-binding \
	-Z unstable-options \
	--config "build.rustflags=['--cfg', 'tokio_unstable']"
mkdir -p /usr/local/include/iceoryx2
mkdir -p /usr/local/lib/iceoryx2
cp target/release/libiceoryx2_ffi_c.so /usr/local/lib/iceoryx2/
cp iceoryx2-ffi-c/include/* /usr/local/include/iceoryx2/
ln -sf /usr/local/lib/iceoryx2/libiceoryx2_ffi_c.so /usr/local/lib/
cp -r iceoryx2-cpp-binding/include/* /usr/local/include/iceoryx2/
cp target/release/libiceoryx2_cpp_binding.so /usr/local/lib/iceoryx2/
ln -sf /usr/local/lib/iceoryx2/libiceoryx2_cpp_binding.so /usr/local/lib/

ldconfig

rm -rf /tmp/iceoryx2
