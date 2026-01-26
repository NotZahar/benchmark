#!/bin/bash

set -e

./run-ros2-cyclone.sh --config 20hz_10000_samples --num-subscribers 3 --with-dds-config
sleep 10
./run-ros2-fast.sh --config 20hz_10000_samples --num-subscribers 3 --with-dds-config
sleep 10
./run-ros2-iceoryx.sh --config 20hz_10000_samples --num-subscribers 3
sleep 10

./run-zmq-flatbuffers.sh --with-tcp --config 20hz_10000_samples --num-subscribers 3
sleep 10
./run-zmq-flatbuffers.sh --with-ipc --config 20hz_10000_samples --num-subscribers 3
sleep 10

./run-zmq-protobuf.sh --with-tcp --config 20hz_10000_samples --num-subscribers 3
sleep 10
./run-zmq-protobuf.sh --with-ipc --config 20hz_10000_samples --num-subscribers 3
sleep 10

./run-zmq-capnproto.sh --with-tcp --config 20hz_10000_samples --num-subscribers 3
sleep 10
./run-zmq-capnproto.sh --with-ipc --config 20hz_10000_samples --num-subscribers 3
sleep 10

./run-rust-iceoryx2.sh --config 20hz_10000_samples --num-subscribers 3
sleep 10
./run-rust-iceoryx2-flatbuffers.sh --config 20hz_10000_samples --num-subscribers 3
sleep 10
