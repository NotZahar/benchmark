#!/bin/bash

set -e

./run-ros2-cyclone.sh --with-dds-config --num-subscribers 3
sleep 10
./run-ros2-fast.sh --with-dds-config --num-subscribers 3
sleep 10
./run-ros2-iceoryx.sh --num-subscribers 3
sleep 10

./run-zmq-flatbuffers.sh --num-subscribers 3 --with-tcp
sleep 10
./run-zmq-flatbuffers.sh --num-subscribers 3 --with-ipc
sleep 10

./run-zmq-protobuf.sh --num-subscribers 3 --with-tcp
sleep 10
./run-zmq-protobuf.sh --num-subscribers 3 --with-ipc
sleep 2
