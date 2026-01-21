#!/bin/bash

set -euo pipefail

BENCHMARK_DATA_PATH="/root/workspace/tmp"
ANALYSIS_DATA_PATH="/root/workspace/scripts-for-analysis/csv-and-plots"

rm -rf $ANALYSIS_DATA_PATH
mkdir -p $ANALYSIS_DATA_PATH

python3 collect-latency-data.py $BENCHMARK_DATA_PATH $ANALYSIS_DATA_PATH
python3 collect-perf-data.py $BENCHMARK_DATA_PATH $ANALYSIS_DATA_PATH
python3 make-latency-plots.py $ANALYSIS_DATA_PATH/latencies.csv $ANALYSIS_DATA_PATH # --exclude cyclone
python3 make-perf-plots.py $ANALYSIS_DATA_PATH/perf_subscribers.csv $ANALYSIS_DATA_PATH/perf_publishers.csv $ANALYSIS_DATA_PATH