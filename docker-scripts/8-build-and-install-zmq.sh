#!/bin/bash

set -euo pipefail

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

ldconfig
