### How to run
- ##### ROS2 (Cyclone DDS):
    - With default dds config and 1 subscriber: `./run-ros2-cyclone.sh --num-subscribers 1`
    - With custom dds config and 1 subscriber: `./run-ros2-cyclone.sh --with-dds-config --num-subscribers 1`
- ##### ROS2 (Fast DDS):
    - With default dds config and 1 subscriber: `./run-ros2-fast.sh --num-subscribers 1`
    - With custom dds config and 1 subscriber: `./run-ros2-fast.sh --with-dds-config --num-subscribers 1`
- ##### ZMQ + FlatBuffers:
    - With tcp and 1 subscriber: `./run-zmq-flatbuffers.sh --num-subscribers 1 --with-tcp`
    - With ipc and 1 subscriber: `./run-zmq-flatbuffers.sh --num-subscribers 1 --with-ipc`
- ##### ZMQ + Protobuf:
    - With tcp and 1 subscriber: `./run-zmq-protobuf.sh --num-subscribers 1 --with-tcp`
    - With ipc and 1 subscriber: `./run-zmq-protobuf.sh --num-subscribers 1 --with-ipc`

### Where are results
- Latency: `./tmp/TRANSPORT_TYPE/latencies/`
- Perf stat: `./tmp/TRANSPORT_TYPE/perf_data/`
