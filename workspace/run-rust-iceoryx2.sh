#!/bin/bash

set -eu

cleanup_iceoryx() {
    for ICEORYX_PID in "${ICEORYX_PIDS[@]}"; do
        if kill -0 "$ICEORYX_PID" 2> /dev/null; then
            kill -TERM "$ICEORYX_PID" 2> /dev/null || true
        fi
    done

    sleep 1

    for ICEORYX_PID in "${ICEORYX_PIDS[@]}"; do
        if kill -0 "$ICEORYX_PID" 2> /dev/null; then
            kill -KILL "$ICEORYX_PID" 2> /dev/null || true
        fi
    done

    pkill -KILL -f 'rust_iceoryx2' 2> /dev/null || true
}

ICEORYX_PIDS=()
NUMBER_OF_SUBSCRIBERS=1
CONFIG_DIR="20hz_10000_samples"

while [[ $# -gt 0 ]]; do
    case $1 in
        --num-subscribers)
            NUMBER_OF_SUBSCRIBERS="$2"
            shift 2
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

trap cleanup_iceoryx EXIT INT TERM

LATENCIES_OUTPUT_DIR="/root/workspace/tmp/rust_iceoryx2/latencies"
PERF_OUTPUT_DIR="/root/workspace/tmp/rust_iceoryx2/perf_data"

rm -rf $LATENCIES_OUTPUT_DIR $PERF_OUTPUT_DIR
mkdir -p "$LATENCIES_OUTPUT_DIR"
mkdir -p "$PERF_OUTPUT_DIR"

cd /root/workspace/rust_iceoryx2

echo "Building Rust project..."
cargo build --release

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
        ./target/release/subscriber "$BENCHMARK_CONFIG" "$I" &
        ICEORYX_SUBSCRIBER_PID=$!
        SUBSCRIBER_PIDS+=($ICEORYX_SUBSCRIBER_PID)
        ICEORYX_PIDS+=($ICEORYX_SUBSCRIBER_PID)

        perf stat -p "$ICEORYX_SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
        PERF_STAT_SUBSCRIBER_PID=$!
        PERF_STAT_SUBSCRIBER_PIDS+=($PERF_STAT_SUBSCRIBER_PID)
    done

    sleep 2

    ./target/release/publisher "$BENCHMARK_CONFIG" &
    ICEORYX_PUBLISHER_PID=$!
    ICEORYX_PIDS+=($ICEORYX_PUBLISHER_PID)

    perf stat -p "$ICEORYX_PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
    PERF_STAT_PUBLISHER_PID=$!

    for SUBSCRIBER_PID in "${SUBSCRIBER_PIDS[@]}"; do
        wait "$SUBSCRIBER_PID" 2> /dev/null || true
    done

    for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
        kill -INT "$PERF_STAT_SUBSCRIBER_PID" 2> /dev/null || true
    done

    kill -INT "$PERF_STAT_PUBLISHER_PID" 2> /dev/null || true

    for PERF_STAT_SUBSCRIBER_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
        wait "$PERF_STAT_SUBSCRIBER_PID" 2> /dev/null || true
    done
    wait "$PERF_STAT_PUBLISHER_PID" 2> /dev/null || true

    cleanup_iceoryx
    ICEORYX_PIDS=()

    sleep 1
done

echo "All benchmarks completed!"
