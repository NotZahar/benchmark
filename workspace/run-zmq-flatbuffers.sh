#!/bin/bash

set -e

# cleanup_zmq() {
# 	for ZMQ_PID in "${ZMQ_PIDS[@]}"; do
# 		if kill -0 "$ZMQ_PID" 2>/dev/null; then
# 			kill -TERM "$ZMQ_PID" 2>/dev/null || true
# 		fi
# 	done

# 	sleep 1

# 	for ZMQ_PID in "${ZMQ_PIDS[@]}"; do
# 		if kill -0 "$ZMQ_PID" 2>/dev/null; then
# 			kill -KILL "$ZMQ_PID" 2>/dev/null || true
# 		fi
# 	done

# 	pkill -KILL -f 'zmq_flatbuf' 2>/dev/null || true
# }

# ZMQ_PIDS=()
# NUMBER_OF_SUBSCRIBERS=1
# LATENCIES_OUTPUT_DIR="/root/workspace/tmp/zmq_flatbuf/latencies"
# PERF_OUTPUT_DIR="/root/workspace/tmp/zmq_flatbuf/perf_data"

# while [[ $# -gt 0 ]]; do
# 	case $1 in
# 	--num-subscribers)
# 		NUMBER_OF_SUBSCRIBERS="$2"
# 		shift 2
# 		;;
# 	*)
# 		echo "Unknown option: $1"
# 		exit 1
# 		;;
# 	esac
# done

# trap cleanup_zmq EXIT INT TERM

# rm -rf $LATENCIES_OUTPUT_DIR $PERF_OUTPUT_DIR
# mkdir -p "$LATENCIES_OUTPUT_DIR"
# mkdir -p "$PERF_OUTPUT_DIR"

cd /root/workspace/zmq_flatbuffers

rm -rf build
mkdir -p build
cd build
cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -DCMAKE_BUILD_TYPE=Release ..
make -j$(nproc)
# cd ..

# echo ""
# echo "Benchmark started (${NUMBER_OF_SUBSCRIBERS} subscribers) ..."

# mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' /root/workspace/zmq_flatbuf/config/*.yaml | sort -V)

# for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
# 	BENCHMARK_CONFIG_NAME=$(basename "$BENCHMARK_CONFIG" .yaml)
# 	mkdir -p "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}"
# 	echo "with config: $BENCHMARK_CONFIG_NAME"

# 	SUBSCRIBER_PIDS=()
# 	PERF_STAT_SUBSCRIBER_PIDS=()

# 	for I in $(seq 1 "$NUMBER_OF_SUBSCRIBERS"); do
# 		./build/zmq_subscriber "$BENCHMARK_CONFIG" "$I" &
# 		ZMQ_SUBSCRIBER_PID=$!
# 		SUBSCRIBER_PIDS+=($ZMQ_SUBSCRIBER_PID)
# 		ZMQ_PIDS+=($ZMQ_SUBSCRIBER_PID)

# 		perf stat -p "$ZMQ_SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
# 		PERF_STAT_SUBSCRIBER_PID=$!
# 		PERF_STAT_SUBSCRIBER_PIDS+=($PERF_STAT_SUBSCRIBER_PID)
# 	done

# 	sleep 1

# 	./build/zmq_publisher "$BENCHMARK_CONFIG" &
# 	ZMQ_PUBLISHER_PID=$!
# 	ZMQ_PIDS+=($ZMQ_PUBLISHER_PID)

# 	perf stat -p "$ZMQ_PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
# 	PERF_STAT_PUBLISHER_PID=$!

# 	for SUBSCRIBER_PID in "${SUBSCRIBER_PIDS[@]}"; do
# 		wait "$SUBSCRIBER_PID" 2>/dev/null || true
# 	done

# 	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
# 		kill -INT "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
# 	done

# 	kill -INT "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true

# 	for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
# 		wait "$PERF_STAT_SUBSCRIBER_PID" 2>/dev/null || true
# 	done
# 	wait "$PERF_STAT_PUBLISHER_PID" 2>/dev/null || true

# 	cleanup_zmq
# 	ZMQ_PIDS=()

# 	sleep 1
# done

# echo "All benchmarks completed!"
