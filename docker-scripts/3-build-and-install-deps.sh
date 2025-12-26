#!/bin/bash

set -eu

BUILD_DIR="/root/libs"

mkdir -p $BUILD_DIR
source "$HOME/.cargo/env"

echo "Building ZeroMQ"
cd $BUILD_DIR
git clone https://github.com/zeromq/libzmq.git
cd libzmq
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DWITH_PERF_TOOL=OFF -DZMQ_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building cppzmq"
cd $BUILD_DIR
git clone https://github.com/zeromq/cppzmq.git
cd cppzmq
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DCPPZMQ_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building Flatbuffers"
cd $BUILD_DIR
git clone https://github.com/google/flatbuffers.git
cd flatbuffers
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DFLATBUFFERS_BUILD_TESTS=OFF
make -j$(nproc) install

echo "Building Iceoryx"
cd $BUILD_DIR
git clone https://github.com/eclipse-iceoryx/iceoryx.git
cd iceoryx
cmake -Bbuild -Hiceoryx_meta -DCMAKE_BUILD_TYPE=Release -DBUILD_TEST=OFF -DBUILD_EXAMPLES=OFF
cmake --build build --target install -j$(nproc)

echo "Building Iceoryx2"
cd $BUILD_DIR
git clone https://github.com/eclipse-iceoryx/iceoryx2.git
cd iceoryx2
cargo build --release --jobs $(nproc)

ldconfig
