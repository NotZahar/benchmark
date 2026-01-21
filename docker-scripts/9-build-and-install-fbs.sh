#!/bin/bash

set -euo pipefail

BUILD_DIR="/root/libs"

mkdir -p $BUILD_DIR

echo "Building Flatbuffers ..."
cd $BUILD_DIR
git clone https://github.com/google/flatbuffers.git
cd flatbuffers
mkdir build && cd build
cmake .. -DCMAKE_BUILD_TYPE=Release -DFLATBUFFERS_BUILD_TESTS=OFF
make -j$(nproc) install

ldconfig
