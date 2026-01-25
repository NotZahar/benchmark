#!/usr/bin/env python3

import argparse
import csv
import os
import re
import sys
from pathlib import Path


def process_latencies(input_path, output_path):
    data = []

    # Ensure output directory exists
    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert input_path to Path object for easier handling
    input_root = Path(input_path)

    # Find all latencies directories starting from input_path
    for root, dirs, files in os.walk(input_root):
        if not str(root).endswith("latencies"):
            continue

        # Get middleware name (parent of latencies directory)
        middleware = Path(root).parent.name

        # Process each payload size directory
        for subdir in dirs:
            # Extract payload size and frequency from directory name
            match = re.match(r"(\d+)_bytes_(\d+)_ms", subdir)
            if not match:
                continue

            payload_size = int(match.group(1))
            period_ms = int(match.group(2))
            hz = 1000.0 / period_ms

            # Path to subscriber files
            subdir_path = Path(root) / subdir

            # Collect data from all 3 subscribers
            latencies = {"avg": [], "median": [], "p99": []}

            for i in range(1, 4):
                file_path = subdir_path / f"{i}_subscriber.txt"
                if not file_path.exists():
                    continue

                with open(file_path, "r") as f:
                    content = f.read()

                    # Extract values using regex
                    avg = re.search(r"Average latency:\s*([\d.]+)\s*ns", content)
                    median = re.search(r"Median latency:\s*([\d.]+)\s*ns", content)
                    p99 = re.search(r"P99 latency:\s*([\d.]+)\s*ns", content)

                    if avg and median and p99:
                        latencies["avg"].append(float(avg.group(1)))
                        latencies["median"].append(float(median.group(1)))
                        latencies["p99"].append(float(p99.group(1)))

            # Calculate averages if we have data
            if latencies["avg"]:
                avg_ms = sum(latencies["avg"]) / len(latencies["avg"]) / 1_000_000
                median_ms = (
                    sum(latencies["median"]) / len(latencies["median"]) / 1_000_000
                )
                p99_ms = sum(latencies["p99"]) / len(latencies["p99"]) / 1_000_000

                data.append(
                    {
                        "middleware": middleware,
                        "payload_size": payload_size,
                        "hz": hz,
                        "avg_latency_ms": avg_ms,
                        "median_latency_ms": median_ms,
                        "p99_latency_ms": p99_ms,
                    }
                )

    # Sort by middleware and payload size
    data.sort(key=lambda x: (x["middleware"], x["payload_size"]))

    # Write to CSV in the specified output directory
    csv_path = output_dir / "latencies.csv"
    with open(csv_path, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "middleware",
                "payload_size",
                "hz",
                "avg_latency_ms",
                "median_latency_ms",
                "p99_latency_ms",
            ],
        )
        writer.writeheader()
        for row in data:
            # Format floats to 6 decimal places
            formatted_row = {
                k: (f"{v:.6f}" if isinstance(v, float) else v) for k, v in row.items()
            }
            writer.writerow(formatted_row)

    print(f"Created {csv_path} with {len(data)} entries")
    return data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Process latency measurement data.")
    parser.add_argument(
        "input_path",
        help="Path to the root directory containing latency measurement data",
    )
    parser.add_argument(
        "output_path", help="Path to the directory where results will be saved"
    )

    args = parser.parse_args()
    process_latencies(args.input_path, args.output_path)
