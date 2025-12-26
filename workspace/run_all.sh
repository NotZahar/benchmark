#!/bin/bash

set -e

./run-ros2-cyclone.sh --with-dds-config --num-subscribers 2
sleep 10
./run-ros2-fast.sh --with-dds-config --num-subscribers 2
sleep 10
./run-zmq-flatbuffers.sh --num-subscribers 2 --with-tcp
sleep 2
