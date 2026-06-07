#!/usr/bin/env python3

import argparse
import csv
import re
from pathlib import Path


RESULT_DIR_RE = re.compile(r"(\d+)_bytes_(\d+)_ms(?:_(\d+)_samples)?$")
METRIC_PATTERNS = {
    "avg": re.compile(r"Average latency:\s*([\d.]+)\s*ns"),
    "median": re.compile(r"Median latency:\s*([\d.]+)\s*ns"),
    "p99": re.compile(r"P99 latency:\s*([\d.]+)\s*ns"),
}


def natural_key(path):
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def parse_latency_file(file_path):
    content = file_path.read_text(encoding="utf-8")
    metrics = {}
    for name, pattern in METRIC_PATTERNS.items():
        match = pattern.search(content)
        if match is None:
            return None
        metrics[name] = float(match.group(1))
    return metrics


def process_latencies(input_path, output_path):
    data = []

    output_dir = Path(output_path)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_root = Path(input_path)
    if not input_root.exists():
        raise SystemExit(f"Input path does not exist: {input_root}")

    for latency_root in sorted(input_root.rglob("latencies")):
        if not latency_root.is_dir():
            continue

        middleware = latency_root.parent.name

        for result_dir in sorted(
            [path for path in latency_root.iterdir() if path.is_dir()],
            key=natural_key,
        ):
            match = RESULT_DIR_RE.match(result_dir.name)
            if not match:
                continue

            payload_size = int(match.group(1))
            period_ms = int(match.group(2))
            hz = 1000.0 / period_ms

            latencies = {"avg": [], "median": [], "p99": []}
            subscriber_files = sorted(
                result_dir.glob("*_subscriber.txt"), key=natural_key
            )

            for file_path in subscriber_files:
                metrics = parse_latency_file(file_path)
                if metrics is None:
                    continue
                for metric_name, value in metrics.items():
                    latencies[metric_name].append(value)

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
                        "num_subscribers": len(latencies["avg"]),
                        "avg_latency_ms": avg_ms,
                        "median_latency_ms": median_ms,
                        "p99_latency_ms": p99_ms,
                    }
                )

    data.sort(key=lambda x: (x["middleware"], x["payload_size"], x["hz"]))

    csv_path = output_dir / "latencies.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "middleware",
                "payload_size",
                "hz",
                "num_subscribers",
                "avg_latency_ms",
                "median_latency_ms",
                "p99_latency_ms",
            ],
        )
        writer.writeheader()
        for row in data:
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
