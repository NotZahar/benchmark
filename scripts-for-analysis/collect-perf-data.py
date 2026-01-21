#!/usr/bin/env python3

import os
import re
import csv
from pathlib import Path
from collections import defaultdict


def parse_perf_file(file_path):
    """Parse perf file and extract key metrics."""
    metrics = {}

    try:
        with open(file_path, "r") as f:
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

    except Exception as e:
        print(f"Error parsing {file_path}: {e}")

    return metrics


def collect_perf_data():
    """Collect and average subscriber performance data and collect publisher data."""

    # Dictionaries to store grouped data
    subscriber_grouped_data = defaultdict(list)
    publisher_data = defaultdict(list)

    # Walk through directory structure
    for root, dirs, files in os.walk("."):
        if not root.endswith("perf_data"):
            continue

        # Get middleware name
        middleware = Path(root).parent.name

        # Process each payload size directory
        for subdir in dirs:
            # Extract payload size and frequency
            match = re.match(r"(\d+)_bytes_(\d+)_ms", subdir)
            if not match:
                continue

            payload_size = int(match.group(1))
            period_ms = int(match.group(2))
            hz = 1000.0 / period_ms

            subdir_path = os.path.join(root, subdir)

            # Process subscriber files
            for file in os.listdir(subdir_path):
                if file.endswith(".stat.txt"):
                    file_path = os.path.join(subdir_path, file)
                    metrics = parse_perf_file(file_path)

                    if metrics:
                        key = (middleware, payload_size, hz)

                        if "subscriber" in file:
                            subscriber_grouped_data[key].append(metrics)
                        elif "publisher" in file:
                            publisher_data[key].append(metrics)

    return subscriber_grouped_data, publisher_data


def create_subscriber_averages(subscriber_grouped_data):
    """Calculate averages for subscriber data."""
    averaged_data = []

    for (middleware, payload_size, hz), metrics_list in subscriber_grouped_data.items():
        if not metrics_list:
            continue

        # Create result dictionary
        result = {
            "middleware": middleware,
            "payload_size": payload_size,
            "hz": hz,
            "num_subscribers": len(metrics_list),
        }

        # Get all metric keys
        all_keys = set()
        for metrics in metrics_list:
            all_keys.update(metrics.keys())

        # Calculate average for each metric
        for key in all_keys:
            values = []
            for metrics in metrics_list:
                if key in metrics and isinstance(metrics[key], (int, float)):
                    values.append(metrics[key])

            if values:
                avg_value = sum(values) / len(values)
                result[f"avg_{key}"] = avg_value

        # Calculate derived metrics
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
    """Process publisher data (should be one per configuration)."""
    publisher_processed = []

    for (middleware, payload_size, hz), metrics_list in publisher_data.items():
        if not metrics_list:
            continue

        # Should be only one publisher per configuration
        if len(metrics_list) > 1:
            print(
                f"Warning: Multiple publishers found for {middleware}, {payload_size} bytes. Using first."
            )

        metrics = metrics_list[0]  # Take the first publisher

        # Create result dictionary
        result = {
            "middleware": middleware,
            "payload_size": payload_size,
            "hz": hz,
            "process_type": "publisher",
        }

        # Add all metrics
        for key, value in metrics.items():
            result[key] = value

        # Calculate derived metrics
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


def create_combined_csv(
    subscriber_averages, publisher_data, output_file="perf_combined.csv"
):
    """Create a combined CSV with subscriber averages and publisher data."""

    if not subscriber_averages:
        print("No subscriber data found!")
        return

    # Create a dictionary for quick lookup of publisher data
    publisher_dict = {}
    for pub in publisher_data:
        key = (pub["middleware"], pub["payload_size"], pub["hz"])
        publisher_dict[key] = pub

    combined_data = []

    for sub in subscriber_averages:
        key = (sub["middleware"], sub["payload_size"], sub["hz"])

        combined_row = {
            "middleware": sub["middleware"],
            "payload_size": sub["payload_size"],
            "hz": sub["hz"],
            "num_subscribers": sub["num_subscribers"],
        }

        # Add subscriber averages (with avg_ prefix)
        for key_name, value in sub.items():
            if key_name not in ["middleware", "payload_size", "hz", "num_subscribers"]:
                combined_row[key_name] = value

        # Add publisher data (with publisher_ prefix)
        if key in publisher_dict:
            pub = publisher_dict[key]
            for key_name, value in pub.items():
                if key_name not in ["middleware", "payload_size", "hz", "process_type"]:
                    combined_row[f"publisher_{key_name}"] = value

        combined_data.append(combined_row)

    # Sort by middleware and payload size
    combined_data.sort(key=lambda x: (x["middleware"], x["payload_size"]))

    # Write to CSV
    with open(output_file, "w", newline="") as csvfile:
        # Get all column names
        all_columns = set()
        for row in combined_data:
            all_columns.update(row.keys())

        # Define column order
        base_columns = ["middleware", "payload_size", "hz", "num_subscribers"]

        # Separate subscriber and publisher columns
        sub_columns = sorted([c for c in all_columns if c.startswith("avg_")])
        pub_columns = sorted([c for c in all_columns if c.startswith("publisher_")])

        # Combine in desired order
        fieldnames = base_columns + sub_columns + pub_columns

        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in combined_data:
            # Ensure all fields are present
            for field in fieldnames:
                if field not in row:
                    row[field] = ""

            writer.writerow(row)

    print(f"Created {output_file} with {len(combined_data)} entries")

    return combined_data


def create_separate_csvs(subscriber_averages, publisher_data):
    """Create separate CSV files for subscribers and publishers."""

    # Create subscriber averages CSV
    if subscriber_averages:
        write_csv(subscriber_averages, "perf_subscribers.csv")

    # Create publisher CSV
    if publisher_data:
        write_csv(publisher_data, "perf_publishers.csv")


def write_csv(data, filename):
    """Write data to CSV file."""
    if not data:
        print(f"No data to write for {filename}")
        return

    # Sort data
    if "payload_size" in data[0]:
        data.sort(key=lambda x: (x.get("middleware", ""), x.get("payload_size", 0)))

    # Get all column names
    all_keys = set()
    for row in data:
        all_keys.update(row.keys())

    # Define column order
    if "middleware" in data[0]:
        base_cols = ["middleware", "payload_size", "hz"]
        if "num_subscribers" in data[0]:
            base_cols.insert(3, "num_subscribers")
        if "process_type" in data[0]:
            base_cols.insert(3, "process_type")
    else:
        base_cols = []

    metric_cols = sorted([k for k in all_keys if k not in base_cols])
    fieldnames = base_cols + metric_cols

    with open(filename, "w", newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in data:
            writer.writerow(row)

    print(f"Created {filename} with {len(data)} entries")


def main():
    print("Collecting performance data...")

    # Collect both subscriber and publisher data
    subscriber_grouped_data, publisher_grouped_data = collect_perf_data()

    # Process subscriber data (calculate averages)
    print("\nProcessing subscriber data...")
    subscriber_averages = create_subscriber_averages(subscriber_grouped_data)

    # Process publisher data
    print("Processing publisher data...")
    publisher_data = process_publisher_data(publisher_grouped_data)

    if not subscriber_averages:
        print("No subscriber data found!")
        return

    # Print summary
    print(f"\nSummary:")
    print(f"- Number of subscriber configurations: {len(subscriber_averages)}")
    print(f"- Number of publisher configurations: {len(publisher_data)}")
    print(f"- Middlewares: {sorted(set(d['middleware'] for d in subscriber_averages))}")
    print(
        f"- Payload sizes: {sorted(set(d['payload_size'] for d in subscriber_averages))}"
    )

    # Create combined CSV
    # print("\nCreating combined CSV with subscriber averages and publisher data...")
    # combined_data = create_combined_csv(
    #     subscriber_averages, publisher_data, "perf_data_with_publishers.csv"
    # )

    # Create separate CSVs
    print("\nCreating separate CSVs...")
    create_separate_csvs(subscriber_averages, publisher_data)

    # Print sample data
    # if combined_data:
    #     print(f"\nSample data (first configuration):")
    #     sample = combined_data[0]
    #     print(f"Middleware: {sample.get('middleware', 'N/A')}")
    #     print(f"Payload: {sample.get('payload_size', 'N/A')} bytes")
    #     print(f"Frequency: {sample.get('hz', 'N/A'):.1f} Hz")
    #     print(f"Number of subscribers: {sample.get('num_subscribers', 'N/A')}")

    #     # Show key subscriber metrics
    #     print(f"\nSubscriber Averages:")
    #     print(f"  IPC: {sample.get('avg_ipc', 'N/A'):.3f}")
    #     print(f"  Branch miss rate: {sample.get('avg_branch_miss_rate', 'N/A'):.1f}%")
    #     print(f"  Instructions: {sample.get('avg_instructions', 'N/A'):,.0f}")

    #     # Show key publisher metrics if available
    #     if "publisher_ipc" in sample:
    #         print(f"\nPublisher Data:")
    #         print(f"  IPC: {sample.get('publisher_ipc', 'N/A'):.3f}")
    #         print(
    #             f"  Branch miss rate: {sample.get('publisher_branch_miss_rate', 'N/A'):.1f}%"
    #         )
    #         print(f"  Instructions: {sample.get('publisher_instructions', 'N/A'):,.0f}")


if __name__ == "__main__":
    main()
