#!/bin/bash

set -e

cleanup_ros2() {
	pkill -KILL -f 'iox-roudi' 2>/dev/null || true

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

	pkill -KILL -f 'ros2_iceoryx' 2>/dev/null || true
}

ROS2_PIDS=()
NUMBER_OF_SUBSCRIBERS=1
LATENCIES_OUTPUT_DIR="/root/workspace/tmp/ros2_iceoryx/latencies"
PERF_OUTPUT_DIR="/root/workspace/tmp/ros2_iceoryx/perf_data"

while [[ $# -gt 0 ]]; do
	case $1 in
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

cd /root/workspace/ros2_iceoryx

if [ -n "$VIRTUAL_ENV" ]; then
	echo "Deactivating virtual environment: $VIRTUAL_ENV"
	deactivate
fi
export PATH="/usr/bin:$PATH"
unset PYTHONPATH

source /opt/ros/jazzy/setup.bash
source "$HOME/iceoryx_ws/install/setup.bash"

export RMW_IMPLEMENTATION="rmw_iceoryx_cpp"
export ICEORYX_HOME="$HOME/iceoryx_ws/install"
export LD_LIBRARY_PATH="$ICEORYX_HOME/lib:$LD_LIBRARY_PATH"

rm -rf build install log
colcon build --packages-select ros2_iceoryx --cmake-args -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release

source ./install/setup.bash
echo ""
echo "Benchmark started (${NUMBER_OF_SUBSCRIBERS} subscribers) ..."

mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' /root/workspace/configs/20hz_10000_samples/config/*.yaml | sort -V)

for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
	BENCHMARK_CONFIG_NAME=$(basename "$BENCHMARK_CONFIG" .yaml)
	mkdir -p "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}"
	echo "with config: $BENCHMARK_CONFIG_NAME"

	CONFIG_FILE="/root/iceoryx_ws/config/roudi_config.toml"
	iox-roudi --config "$CONFIG_FILE" &
	ROUDI_PID=$!
	ROS2_PIDS+=($ROUDI_PID)
	sleep 2

	SUBSCRIBER_PIDS=()
	PERF_STAT_SUBSCRIBER_PIDS=()

	for I in $(seq 1 "$NUMBER_OF_SUBSCRIBERS"); do
		ros2 run ros2_iceoryx ros2_iceoryx_subscriber "$BENCHMARK_CONFIG" "$I" &
		ROS2_ICEORYX_SUBSCRIBER_PID=$!
		SUBSCRIBER_PIDS+=($ROS2_ICEORYX_SUBSCRIBER_PID)
		ROS2_PIDS+=($ROS2_ICEORYX_SUBSCRIBER_PID)

		perf stat -p "$ROS2_ICEORYX_SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
		PERF_STAT_SUBSCRIBER_PID=$!
		PERF_STAT_SUBSCRIBER_PIDS+=($PERF_STAT_SUBSCRIBER_PID)
	done

	sleep 2

	ros2 run ros2_iceoryx ros2_iceoryx_publisher "$BENCHMARK_CONFIG" &
	ROS2_ICEORYX_PUBLISHER_PID=$!
	ROS2_PIDS+=($ROS2_ICEORYX_PUBLISHER_PID)

	perf stat -p "$ROS2_ICEORYX_PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
	PERF_STAT_PUBLISHER_PID=$!

	for SUBSCRIBER_PID in "${SUBSCRIBER_PIDS[@]}"; do
		wait "$SUBSCRIBER_PID" 2>/dev/null || true
	done

	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
		kill -INT "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
	done

	kill -INT "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true
	kill $ROUDI_PID 2>/dev/null || true

	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
		wait "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
	done
	wait "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true

	cleanup_ros2
	ROS2_PIDS=()

	sleep 1
done

echo "All benchmarks completed!"
