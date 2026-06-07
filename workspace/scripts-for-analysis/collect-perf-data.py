#!/usr/bin/env python3

import argparse
import csv
import os
import re
from collections import defaultdict
from pathlib import Path


def parse_perf_file(file_path):
    """Parse perf file and extract key metrics."""
    metrics = {}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

            # Key metrics to extract
            patterns = {
                "instructions": r"(\d+(?:,\d+)*)\s+instructions",
                "cycles": r"(\d+(?:,\d+)*)\s+cycles",
                "branch_misses": r"(\d+(?:,\d+)*)\s+branch-misses",
                "branches": r"(\d+(?:,\d+)*)\s+branches",
                "task_clock_ms": r"(\d+\.\d+)\s+msec task-clock",
                "context_switches": r"(\d+(?:,\d+)*)\s+context-switches",
                "cpu_migrations": r"(\d+(?:,\d+)*)\s+cpu-migrations",
                "page_faults": r"(\d+(?:,\d+)*)\s+page-faults",
                "time_elapsed": r"(\d+\.\d+)\s+seconds time elapsed",
                "cpu_utilized": r"#\s+(\d+\.\d+)\s+CPUs utilized",
            }

            for key, pattern in patterns.items():
                match = re.search(pattern, content)
                if match:
                    # Remove commas from numbers
                    value_str = match.group(1).replace(",", "")
                    try:
                        metrics[key] = float(value_str)
                    except ValueError:
                        metrics[key] = 0

            if (
                "cpu_utilized" not in metrics
                and "task_clock_ms" in metrics
                and "time_elapsed" in metrics
                and metrics["time_elapsed"] > 0
            ):
                metrics["cpu_utilized"] = metrics["task_clock_ms"] / (
                    metrics["time_elapsed"] * 1000.0
                )

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return metrics


def collect_perf_data(input_root):
    """Collect and average subscriber performance data and collect publisher data."""

    subscriber_grouped_data = defaultdict(list)
    publisher_data = defaultdict(list)

    for root, dirs, files in os.walk(input_root):
        if Path(root).name != "perf_data":
            continue

        middleware = Path(root).parent.name

        for subdir in dirs:
            match = re.match(r"(\d+)_bytes_(\d+)_ms", subdir)
            if not match:
                continue

            payload_size = int(match.group(1))
            period_ms = int(match.group(2))
            hz = 1000.0 / period_ms

            subdir_path = Path(root) / subdir

            for file in sorted(os.listdir(subdir_path)):
                if file.endswith(".stat.txt"):
                    file_path = subdir_path / file
                    metrics = parse_perf_file(file_path)

                    if not metrics:
                        continue

                    key = (middleware, payload_size, hz)

                    if "subscriber" in file:
                        subscriber_grouped_data[key].append(metrics)
                    elif "publisher" in file:
                        publisher_data[key].append(metrics)

    return subscriber_grouped_data, publisher_data


def create_subscriber_averages(subscriber_grouped_data):
    averaged_data = []

    for (middleware, payload_size, hz), metrics_list in subscriber_grouped_data.items():
        if not metrics_list:
            continue

        result = {
            "middleware": middleware,
            "payload_size": payload_size,
            "hz": hz,
            "num_subscribers": len(metrics_list),
        }

        all_keys = set()
        for metrics in metrics_list:
            all_keys.update(metrics.keys())

        for key in all_keys:
            values = [
                m[key]
                for m in metrics_list
                if key in m and isinstance(m[key], (int, float))
            ]
            if values:
                result[f"avg_{key}"] = sum(values) / len(values)

        # Derived metrics
        if (
            "avg_instructions" in result
            and "avg_cycles" in result
            and result["avg_cycles"] > 0
        ):
            result["avg_ipc"] = result["avg_instructions"] / result["avg_cycles"]

        if (
            "avg_branch_misses" in result
            and "avg_branches" in result
            and result["avg_branches"] > 0
        ):
            result["avg_branch_miss_rate"] = (
                result["avg_branch_misses"] / result["avg_branches"]
            ) * 100

        averaged_data.append(result)

    return averaged_data


def process_publisher_data(publisher_data):
    publisher_processed = []

    for (middleware, payload_size, hz), metrics_list in publisher_data.items():
        if not metrics_list:
            continue

        if len(metrics_list) > 1:
            print(
                f"Warning: Multiple publishers found for {middleware}, {payload_size} bytes. Using first."
            )

        metrics = metrics_list[0]
        result = {
            "middleware": middleware,
            "payload_size": payload_size,
            "hz": hz,
            "process_type": "publisher",
        }

        result.update(metrics)

        if "instructions" in result and "cycles" in result and result["cycles"] > 0:
            result["ipc"] = result["instructions"] / result["cycles"]

        if (
            "branch_misses" in result
            and "branches" in result
            and result["branches"] > 0
        ):
            result["branch_miss_rate"] = (
                result["branch_misses"] / result["branches"]
            ) * 100

        publisher_processed.append(result)

    return publisher_processed


def write_csv(data, output_path, filename):
    if not data:
        print(f"No data to write for {filename}")
        return

    data.sort(key=lambda x: (x.get("middleware", ""), x.get("payload_size", 0)))

    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    base_cols = ["middleware", "payload_size", "hz"]
    if "num_subscribers" in data[0]:
        base_cols.insert(3, "num_subscribers")
    if "process_type" in data[0]:
        base_cols.insert(3, "process_type")

    metric_cols = sorted([k for k in all_keys if k not in base_cols])
    fieldnames = base_cols + metric_cols

    full_path = Path(output_path) / filename
    with open(full_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        for row in data:
            writer.writerow(row)

    print(f"Created {full_path} with {len(data)} entries")


def main():
    parser = argparse.ArgumentParser(
        description="Process performance measurement data from perf stat outputs."
    )
    parser.add_argument(
        "input_path",
        help="Path to the root directory containing performance data (e.g., ./measurements)",
    )
    parser.add_argument(
        "output_path",
        help="Path to the directory where CSV results will be saved (e.g., ./results)",
    )
    args = parser.parse_args()

    input_root = Path(args.input_path)
    output_dir = Path(args.output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    if not input_root.exists():
        print(f"Error: Input path '{input_root}' does not exist.")
        return

    print(f"Collecting performance data from: {input_root}")
    subscriber_grouped_data, publisher_grouped_data = collect_perf_data(input_root)

    print("\nProcessing subscriber data...")
    subscriber_averages = create_subscriber_averages(subscriber_grouped_data)

    print("Processing publisher data...")
    publisher_data = process_publisher_data(publisher_grouped_data)

    print(f"\nSummary:")
    print(f"- Subscriber configurations: {len(subscriber_averages)}")
    print(f"- Publisher configurations: {len(publisher_data)}")
    all_rows = [*subscriber_averages, *publisher_data]
    print(f"- Middlewares: {sorted(set(d['middleware'] for d in all_rows))}")
    print(f"- Payload sizes: {sorted(set(d['payload_size'] for d in all_rows))}")

    print("\nCreating separate CSVs...")
    write_csv(subscriber_averages, output_dir, "perf_subscribers.csv")
    write_csv(publisher_data, output_dir, "perf_publishers.csv")


if __name__ == "__main__":
    main()
