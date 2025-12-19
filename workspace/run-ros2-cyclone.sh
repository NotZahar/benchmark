#!/bin/bash

set -e

cleanup_ros2() {
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
NUMBER_OF_SUBSCRIBERS=1
LATENCIES_OUTPUT_DIR="/root/workspace/tmp/ros2_cyclone/latencies"
PERF_OUTPUT_DIR="/root/workspace/tmp/ros2_cyclone/perf_data"

while [[ $# -gt 0 ]]; do
	case $1 in
	--with-dds-config)
		USE_CUSTOM_DDS_CONFIG=true
		shift
		;;
	--num-subscribers)
		NUMBER_OF_SUBSCRIBERS="$2"
		shift 2
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
done

trap cleanup_ros2 EXIT INT TERM

rm -rf $LATENCIES_OUTPUT_DIR $PERF_OUTPUT_DIR
mkdir -p "$LATENCIES_OUTPUT_DIR"
mkdir -p "$PERF_OUTPUT_DIR"

cd /root/workspace/ros2_cyclone
source /opt/ros/jazzy/setup.bash

rm -rf build install log
colcon build --packages-select ros2_cyclone --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release

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
echo "Benchmark started (${NUMBER_OF_SUBSCRIBERS} subscribers) ..."

mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' /root/workspace/ros2_cyclone/config/*.yaml | sort -V)

for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
	BENCHMARK_CONFIG_NAME=$(basename "$BENCHMARK_CONFIG" .yaml)
	mkdir -p "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}"
	echo "Benchmark started with config: $BENCHMARK_CONFIG_NAME"

	SUBSCRIBER_PIDS=()
	PERF_STAT_SUBSCRIBER_PIDS=()

	for I in $(seq 1 "$NUMBER_OF_SUBSCRIBERS"); do
		ros2 run ros2_cyclone ros2_cyclone_subscriber "$BENCHMARK_CONFIG" "$I" &
		ROS2_CYCLONE_SUBSCRIBER_PID=$!
		SUBSCRIBER_PIDS+=($ROS2_CYCLONE_SUBSCRIBER_PID)
		ROS2_PIDS+=($ROS2_CYCLONE_SUBSCRIBER_PID)

		perf stat -p "$ROS2_CYCLONE_SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
		PERF_STAT_SUBSCRIBER_PID=$!
		PERF_STAT_SUBSCRIBER_PIDS+=($PERF_STAT_SUBSCRIBER_PID)
	done

	sleep 0.5

	ros2 run ros2_cyclone ros2_cyclone_publisher "$BENCHMARK_CONFIG" &
	ROS2_CYCLONE_PUBLISHER_PID=$!
	ROS2_PIDS+=($ROS2_CYCLONE_PUBLISHER_PID)

	perf stat -p "$ROS2_CYCLONE_PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
	PERF_STAT_PUBLISHER_PID=$!

	for SUBSCRIBER_PID in "${SUBSCRIBER_PIDS[@]}"; do
		wait "$SUBSCRIBER_PID" 2>/dev/null || true
	done

	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
		kill -INT "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
	done

	kill -INT "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true

	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
		wait "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
	done
	wait "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true

	cleanup_ros2
	ROS2_PIDS=()

	sleep 1
done

echo "All benchmarks completed!"
echo "Perf data stored in $PERF_OUTPUT_DIR"
