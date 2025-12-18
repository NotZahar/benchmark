#!/bin/bash

set -e

cleanup() {
	for ROS2_PID in "${ROS2_PIDS[@]}"; do
		if kill -0 "$ROS2_PID" 2>/dev/null; then
			kill -TERM "$ROS2_PID" 2>/dev/null || true
		fi
	done

	sleep 1

	for ROS2_PID in "${ROS2_PIDS[@]}"; do
		if kill -0 "$ROS2_PID" 2>/dev/null; then
			kill -KILL "$ROS2_PID" 2>/dev/null || true
		fi
	done

	pkill -KILL -f 'ros2_cyclone' 2>/dev/null || true
}

ROS2_PIDS=()
USE_CUSTOM_DDS_CONFIG=false

while [[ $# -gt 0 ]]; do
	case $1 in
	--with-dds-config)
		USE_CUSTOM_DDS_CONFIG=true
		shift
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
done

trap cleanup EXIT INT TERM

cd /root/workspace/ros2_cyclone
source /opt/ros/jazzy/setup.bash

rm -rf build install log
VERBOSE=1 colcon build --event-handlers console_direct+ --packages-select ros2_cyclone --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release

export RMW_IMPLEMENTATION="rmw_cyclonedds_cpp"
if [[ "$USE_CUSTOM_DDS_CONFIG" = true ]]; then
	export CYCLONEDDS_URI='<CycloneDDS><Domain><General><Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces><MaxMessageSize>65500B</MaxMessageSize></General></Domain></CycloneDDS>'
	echo "DDS: $RMW_IMPLEMENTATION (with custom dds config)"
	echo "DDS config: $CYCLONEDDS_URI"
else
	unset CYCLONEDDS_URI
	echo "DDS: $RMW_IMPLEMENTATION (with default dds config)"
fi

source ./install/setup.bash
echo "Benchmark started..."
echo ""

mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' /root/workspace/ros2_cyclone/config/*.yaml | sort -V)

for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
	echo "Benchmark config: $BENCHMARK_CONFIG"
	echo "========================================="

	ros2 run ros2_cyclone ros2_cyclone_subscriber "$BENCHMARK_CONFIG" &
	ROS2_CYCLONE_SUBSCRIBER_PID=$!
	ROS2_PIDS+=($ROS2_CYCLONE_SUBSCRIBER_PID)

	sleep 0.5

	ros2 run ros2_cyclone ros2_cyclone_publisher "$BENCHMARK_CONFIG" &
	ROS2_CYCLONE_PUBLISHER_PID=$!
	ROS2_PIDS+=($ROS2_CYCLONE_PUBLISHER_PID)

	wait "$ROS2_CYCLONE_SUBSCRIBER_PID"
	echo "========================================="

	cleanup

	sleep 1
	echo ""
done

echo "All benchmarks completed!"
