#!/bin/bash
set -eu

cleanup_iceoryx() {
    echo "Cleaning up iceoryx processes..."

    # Clean up perf stat processes first
    for PERF_PID in "${PERF_PIDS[@]:-}"; do
        if kill -0 "$PERF_PID" 2> /dev/null; then
            kill -INT "$PERF_PID" 2> /dev/null || true
        fi
    done

    for PERF_PID in "${PERF_PIDS[@]:-}"; do
        if kill -0 "$PERF_PID" 2> /dev/null; then
            wait "$PERF_PID" 2> /dev/null || true
        fi
    done

    for ICEORYX_PID in "${ICEORYX_PIDS[@]:-}"; do
        if kill -0 "$ICEORYX_PID" 2> /dev/null; then
            kill -TERM "$ICEORYX_PID" 2> /dev/null || true
        fi
    done

    sleep 1

    for ICEORYX_PID in "${ICEORYX_PIDS[@]:-}"; do
        if kill -0 "$ICEORYX_PID" 2> /dev/null; then
            kill -KILL "$ICEORYX_PID" 2> /dev/null || true
        fi
    done

    pkill -TERM -f 'iox-roudi' 2> /dev/null || true
    pkill -KILL -f 'iox-roudi' 2> /dev/null || true

    pkill -TERM -f 'rust_iceoryx2_flatbuffers' 2> /dev/null || true
    pkill -KILL -f 'rust_iceoryx2_flatbuffers' 2> /dev/null || true

    rm -rf /tmp/iceoryx* 2> /dev/null || true
    rm -rf /dev/shm/iceoryx* 2> /dev/null || true
}

ICEORYX_PIDS=()
PERF_PIDS=()
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

LATENCIES_OUTPUT_DIR="/root/workspace/tmp/rust_iceoryx2_flatbuffers/latencies"
PERF_OUTPUT_DIR="/root/workspace/tmp/rust_iceoryx2_flatbuffers/perf_data"

rm -rf "$LATENCIES_OUTPUT_DIR" "$PERF_OUTPUT_DIR"
mkdir -p "$LATENCIES_OUTPUT_DIR"
mkdir -p "$PERF_OUTPUT_DIR"

cd /root/workspace/rust_iceoryx2_flatbuffers

echo "Starting iceoryx daemon..."
iox-roudi -c /etc/iceoryx/roudi_config.toml > /dev/null 2>&1 &
IOX_DAEMON_PID=$!
sleep 1

echo "Building Rust project..."
cargo clean
cargo build --release

echo ""
echo "FlatBuffers Benchmark started (${NUMBER_OF_SUBSCRIBERS} subscribers, config: ${CONFIG_DIR}) ..."

CONFIG_PATH="/root/workspace/configs/${CONFIG_DIR}/config"
if [[ ! -d "$CONFIG_PATH" ]]; then
    echo "Error: Config directory not found: $CONFIG_PATH"
    exit 1
fi

mapfile -t BENCHMARK_CONFIGS < <(printf '%s\n' "${CONFIG_PATH}"/*.yaml | sort -V)

for BENCHMARK_CONFIG in "${BENCHMARK_CONFIGS[@]}"; do
    BENCHMARK_CONFIG_NAME=$(basename "$BENCHMARK_CONFIG" .yaml)
    mkdir -p "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}"
    echo "Running with config: $BENCHMARK_CONFIG_NAME"

    SUBSCRIBER_PIDS=()
    PERF_STAT_SUBSCRIBER_PIDS=()

    for I in $(seq 1 "$NUMBER_OF_SUBSCRIBERS"); do
        ./target/release/subscriber "$BENCHMARK_CONFIG" "$I" &
        SUBSCRIBER_PID=$!
        SUBSCRIBER_PIDS+=($SUBSCRIBER_PID)
        ICEORYX_PIDS+=($SUBSCRIBER_PID)

        sleep 0.1

        perf stat -p "$SUBSCRIBER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/${I}_subscriber.stat.txt" &
        PERF_PID=$!
        PERF_STAT_SUBSCRIBER_PIDS+=($PERF_PID)
        PERF_PIDS+=($PERF_PID)
    done

    sleep 2

    ./target/release/publisher "$BENCHMARK_CONFIG" &
    PUBLISHER_PID=$!
    ICEORYX_PIDS+=($PUBLISHER_PID)

    sleep 0.1

    perf stat -p "$PUBLISHER_PID" -o "${PERF_OUTPUT_DIR}/${BENCHMARK_CONFIG_NAME}/publisher.stat.txt" &
    PERF_PID=$!
    PERF_PIDS+=($PERF_PID)

    echo "Waiting for subscribers to complete..."
    for SUBSCRIBER_PID in "${SUBSCRIBER_PIDS[@]}"; do
        wait "$SUBSCRIBER_PID" 2> /dev/null || true
    done

    echo "Stopping perf monitoring..."
    for PERF_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
        kill -INT "$PERF_PID" 2> /dev/null || true
    done
    kill -INT "$PERF_PID" 2> /dev/null || true

    for PERF_PID in "${PERF_STAT_SUBSCRIBER_PIDS[@]}"; do
        wait "$PERF_PID" 2> /dev/null || true
    done
    wait "$PERF_PID" 2> /dev/null || true

    echo "Cleaning up benchmark run..."
    cleanup_iceoryx
    ICEORYX_PIDS=()
    PERF_PIDS=()

    sleep 1
done

echo "Stopping iceoryx daemon..."
kill -TERM "$IOX_DAEMON_PID" 2> /dev/null || true
sleep 1
kill -KILL "$IOX_DAEMON_PID" 2> /dev/null || true

echo "All FlatBuffers benchmarks completed!"
