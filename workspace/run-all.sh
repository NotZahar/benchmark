#!/bin/bash

set -e

./run-ros2-cyclone.sh --num-subscribers 3 --with-dds-config
sleep 10
./run-ros2-fast.sh --num-subscribers 3 --with-dds-config
sleep 10
./run-ros2-iceoryx.sh --num-subscribers 3
sleep 10

./run-zmq-flatbuffers.sh --with-tcp --num-subscribers 3
sleep 10
./run-zmq-flatbuffers.sh --with-ipc --num-subscribers 3
sleep 10

./run-zmq-protobuf.sh --with-tcp --num-subscribers 3
sleep 10
./run-zmq-protobuf.sh --with-ipc --num-subscribers 3
sleep 10

./run-zmq-capnproto.sh --with-tcp --num-subscribers 3
sleep 10
./run-zmq-capnproto.sh --with-ipc --num-subscribers 3
sleep 10
