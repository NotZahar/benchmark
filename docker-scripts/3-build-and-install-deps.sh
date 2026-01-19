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
source "$HOME/.cargo/env"
if [ -f "/usr/local/lib/libiceoryx2_ffi_c.so" ] && [ -f "/usr/local/lib/libiceoryx2_cpp.so" ]; then
	echo "Iceoryx2 libraries already installed, skipping build..."
	exit 0
fi
if ! rustup toolchain list | grep -q nightly; then
	echo "Installing nightly Rust toolchain..."
	rustup toolchain install nightly --profile minimal --no-self-update
fi
ICEORYX2_VERSION="v0.8.1"
ICEORYX2_BUILD_DIR="/tmp/iceoryx2"
echo "Cloning Iceoryx2 ${ICEORYX2_VERSION}..."
rm -rf "${ICEORYX2_BUILD_DIR}"
git clone --depth 1 --branch "${ICEORYX2_VERSION}" \
	https://github.com/eclipse-iceoryx/iceoryx2.git "${ICEORYX2_BUILD_DIR}"
cd "${ICEORYX2_BUILD_DIR}"
echo "Checking repository structure..."
echo "Available packages in workspace:"
if [ -f "Cargo.toml" ]; then
	grep -E '^\[\[package\]\]|^\[workspace\]' Cargo.toml || echo "No workspace definition found"
	find . -name "Cargo.toml" -type f | head -10
fi
echo "Building Iceoryx2 with nightly toolchain..."
echo "Building C FFI..."
if cargo +nightly build --release --package iceoryx2-ffi-c 2>&1 | tail -10; then
	echo "✓ C FFI built successfully"
else
	echo "Trying with unstable features..."
	cargo +nightly build --release \
		--package iceoryx2-ffi-c \
		-Z unstable-options \
		--config "build.rustflags=['--cfg', 'tokio_unstable']"
fi
echo "Looking for C++ package..."
CPP_PACKAGE=""
for pkg in iceoryx2-cpp iceoryx2-cpp-binding iceoryx2-cpp-rs iceoryx2_cpp; do
	if cargo +nightly metadata --format-version=1 2>/dev/null | grep -q "\"$pkg\""; then
		CPP_PACKAGE="$pkg"
		echo "Found C++ package: $CPP_PACKAGE"
		break
	fi
done
if [ -n "$CPP_PACKAGE" ]; then
	echo "Building $CPP_PACKAGE..."
	if cargo +nightly build --release --package "$CPP_PACKAGE" 2>&1 | tail -10; then
		echo "✓ $CPP_PACKAGE built successfully"
	else
		echo "Trying with unstable features..."
		cargo +nightly build --release \
			--package "$CPP_PACKAGE" \
			-Z unstable-options \
			--config "build.rustflags=['--cfg', 'tokio_unstable']"
	fi
else
	echo "Warning: No C++ package found. Trying to build all packages..."
	cargo +nightly build --release
fi
echo "Installing libraries..."
mkdir -p /usr/local/include/iceoryx2
mkdir -p /usr/local/lib/iceoryx2
if [ -f "target/release/libiceoryx2_ffi_c.so" ]; then
	cp target/release/libiceoryx2_ffi_c.so /usr/local/lib/iceoryx2/
	echo "Copied: libiceoryx2_ffi_c.so"
else
	echo "Warning: libiceoryx2_ffi_c.so not found in release, checking debug..."
	if [ -f "target/debug/libiceoryx2_ffi_c.so" ]; then
		cp target/debug/libiceoryx2_ffi_c.so /usr/local/lib/iceoryx2/
		echo "Copied debug version: libiceoryx2_ffi_c.so"
	else
		find target -name "*iceoryx2*.so" -type f | while read lib; do
			cp "$lib" /usr/local/lib/iceoryx2/
			echo "Copied: $(basename "$lib")"
		done
	fi
fi
CPP_LIB=""
for lib in libiceoryx2_cpp.so libiceoryx2_cpp_binding.so libiceoryx2-cpp.so; do
	if [ -f "target/release/$lib" ]; then
		CPP_LIB="$lib"
		break
	elif [ -f "target/debug/$lib" ]; then
		CPP_LIB="$lib"
		break
	fi
done
if [ -n "$CPP_LIB" ]; then
	if [ -f "target/release/$CPP_LIB" ]; then
		cp "target/release/$CPP_LIB" /usr/local/lib/iceoryx2/
	else
		cp "target/debug/$CPP_LIB" /usr/local/lib/iceoryx2/
	fi
	echo "Copied C++ library: $CPP_LIB"
fi
echo "Copying headers..."
[ -d "iceoryx2-ffi-c/include" ] && cp iceoryx2-ffi-c/include/* /usr/local/include/iceoryx2/ 2>/dev/null || true
for dir in iceoryx2-cpp/include iceoryx2-cpp-binding/include; do
	if [ -d "$dir" ]; then
		cp -r "$dir"/* /usr/local/include/iceoryx2/ 2>/dev/null || true
		echo "Copied headers from: $dir"
	fi
done
echo "Creating symbolic links..."
for lib in /usr/local/lib/iceoryx2/*.so; do
	if [ -f "$lib" ]; then
		ln -sf "$lib" /usr/local/lib/
		echo "Linked: $(basename "$lib")"
	fi
done
echo "Iceoryx2 installation completed!"
echo "Installed libraries:"
ls -la /usr/local/lib/iceoryx2/ 2>/dev/null || echo "No libraries found"
echo "Installed headers:"
ls -la /usr/local/include/iceoryx2/ 2>/dev/null || echo "No headers found"

ldconfig

rm -rf /tmp/iceoryx2
