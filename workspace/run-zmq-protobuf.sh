#!/bin/bash

set -eu

cleanup_zmq() {
	for ZMQ_PID in "${ZMQ_PIDS[@]}"; do
		if kill -0 "$ZMQ_PID" 2>/dev/null; then
			kill -TERM "$ZMQ_PID" 2>/dev/null || true
		fi
	done

	sleep 1

	for ZMQ_PID in "${ZMQ_PIDS[@]}"; do
		if kill -0 "$ZMQ_PID" 2>/dev/null; then
			kill -KILL "$ZMQ_PID" 2>/dev/null || true
		fi
	done

	pkill -KILL -f 'zmq_protobuf' 2>/dev/null || true
}

ZMQ_PIDS=()
NUMBER_OF_SUBSCRIBERS=1
WITH_TCP=false
WITH_IPC=false
CONFIG_DIR="20hz_10000_samples"

while [[ $# -gt 0 ]]; do
	case $1 in
	--num-subscribers)
		NUMBER_OF_SUBSCRIBERS="$2"
		shift 2
		;;
	--with-tcp)
		WITH_TCP=true
		shift 1
		;;
	--with-ipc)
		WITH_IPC=true
		shift 1
		;;
	--config)
		CONFIG_DIR="$2"
		shift 2
		;;
	*)
		echo "Unknown option: $1"
		exit 1
		;;
	esac
done

if [[ "$WITH_TCP" == false && "$WITH_IPC" == false ]]; then
	echo "Need to choose a transport type: tcp or ipc"
	exit 1
fi

TRANSPORT_TYPE=""
if [[ "$WITH_TCP" == true ]]; then
	TRANSPORT_TYPE="tcp"
else
	TRANSPORT_TYPE="ipc"
fi

trap cleanup_zmq EXIT INT TERM

LATENCIES_OUTPUT_DIR="/root/workspace/tmp/zmq_protobuf_$TRANSPORT_TYPE/latencies"
PERF_OUTPUT_DIR="/root/workspace/tmp/zmq_protobuf_$TRANSPORT_TYPE/perf_data"

rm -rf $LATENCIES_OUTPUT_DIR $PERF_OUTPUT_DIR
mkdir -p "$LATENCIES_OUTPUT_DIR"
mkdir -p "$PERF_OUTPUT_DIR"

cd /root/workspace/zmq_protobuf

rm -rf build
mkdir -p build
cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
cd ..

echo ""
echo "Benchmark started (${NUMBER_OF_SUBSCRIBERS} subscribers, config: ${CONFIG_DIR}) ..."

CONFIG_PATH="/root/workspace/configs/${CONFIG_DIR}/config"
if [[ ! -d "$CONFIG_PATH" ]]; then
	echo "Error: Config directory not found: $CONFIG_PATH"
	exit 1
fi

mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' "${CONFIG_PATH}"/*.yaml | sort -V)

for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
	BENCHMARK_CONFIG_NAME=$(basename "$BENCHMARK_CONFIG" .yaml)
	mkdir -p "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}"
	echo "with config: $BENCHMARK_CONFIG_NAME"

	SUBSCRIBER_PIDS=()
	PERF_STAT_SUBSCRIBER_PIDS=()

	for I in $(seq 1 "$NUMBER_OF_SUBSCRIBERS"); do
		./build/zmq_protobuf_subscriber "$BENCHMARK_CONFIG" "$I" "$TRANSPORT_TYPE" &
		ZMQ_SUBSCRIBER_PID=$!
		SUBSCRIBER_PIDS+=($ZMQ_SUBSCRIBER_PID)
		ZMQ_PIDS+=($ZMQ_SUBSCRIBER_PID)

		perf stat -p "$ZMQ_SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
		PERF_STAT_SUBSCRIBER_PID=$!
		PERF_STAT_SUBSCRIBER_PIDS+=($PERF_STAT_SUBSCRIBER_PID)
	done

	sleep 1

	./build/zmq_protobuf_publisher "$BENCHMARK_CONFIG" "$TRANSPORT_TYPE" &
	ZMQ_PUBLISHER_PID=$!
	ZMQ_PIDS+=($ZMQ_PUBLISHER_PID)

	perf stat -p "$ZMQ_PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
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

	cleanup_zmq
	ZMQ_PIDS=()

	sleep 1
done

echo "All benchmarks completed!"
