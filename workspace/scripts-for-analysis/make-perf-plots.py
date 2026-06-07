#!/usr/bin/env python3

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

BAR_GROUP_WIDTH = 1.8
BAR_GROUP_GAP = 0.55
BAR_WIDTH_RATIO = 0.92
MIN_BAR_CHART_WIDTH_IN = 20
BAR_CHART_HEIGHT_IN = 9


def grouped_bar_x(payload_sizes):
    group_step = BAR_GROUP_WIDTH + BAR_GROUP_GAP
    return np.arange(len(payload_sizes)) * group_step


def max_bars_per_payload(df):
    return max(
        df[df["payload_size"] == payload]["middleware"].nunique()
        for payload in sorted(df["payload_size"].unique())
    )


def bar_chart_width(payload_sizes, max_bars_per_group):
    group_step = BAR_GROUP_WIDTH + BAR_GROUP_GAP
    bar_density_width = max_bars_per_group * 0.55
    payload_width = len(payload_sizes) * group_step * 1.35 + 5
    return max(MIN_BAR_CHART_WIDTH_IN, payload_width, bar_density_width)


def bar_center(group_center, bar_idx, bar_count):
    bar_slot_width = BAR_GROUP_WIDTH / max(bar_count, 1)
    group_left = group_center - BAR_GROUP_WIDTH / 2.0
    return group_left + (bar_idx + 0.5) * bar_slot_width


def visible_bar_width(bar_count):
    bar_slot_width = BAR_GROUP_WIDTH / max(bar_count, 1)
    return bar_slot_width * BAR_WIDTH_RATIO


def key_label(row):
    return f"{row.get('middleware')} payload={row.get('payload_size')} hz={row.get('hz')}"


def require_number(row, column):
    if column not in row.index or pd.isna(row[column]):
        raise ValueError(f"Missing perf column '{column}' for {key_label(row)}")
    return float(row[column])


def cpu_percent(row, cpu_column, task_clock_column, time_elapsed_column):
    if cpu_column in row.index and not pd.isna(row[cpu_column]):
        return float(row[cpu_column]) * 100.0

    task_clock_ms = require_number(row, task_clock_column)
    time_elapsed = require_number(row, time_elapsed_column)
    if time_elapsed <= 0:
        raise ValueError(f"Invalid {time_elapsed_column}={time_elapsed} for {key_label(row)}")

    return task_clock_ms / (time_elapsed * 1000.0) * 100.0


def load_and_merge_data(subscriber_csv, publisher_csv):
    """Load and merge subscriber and publisher data."""

    subscriber_df = pd.read_csv(subscriber_csv)
    publisher_df = pd.read_csv(publisher_csv)

    combined_data = []
    key_columns = ["middleware", "payload_size", "hz"]

    subscriber_keys = set(
        map(tuple, subscriber_df[key_columns].drop_duplicates().values)
    )
    publisher_keys = set(
        map(tuple, publisher_df[key_columns].drop_duplicates().values)
    )

    for mw, payload, hz in sorted(subscriber_keys | publisher_keys):
        sub_data = subscriber_df[
            (subscriber_df["middleware"] == mw)
            & (subscriber_df["payload_size"] == payload)
            & (subscriber_df["hz"] == hz)
        ]
        pub_data = publisher_df[
            (publisher_df["middleware"] == mw)
            & (publisher_df["payload_size"] == payload)
            & (publisher_df["hz"] == hz)
        ]

        row = {"middleware": mw, "payload_size": payload, "hz": hz}

        if sub_data.empty:
            raise ValueError(f"Missing subscriber perf data for {key_label(row)}")
        if pub_data.empty:
            raise ValueError(f"Missing publisher perf data for {key_label(row)}")

        sub_row = sub_data.iloc[0]
        pub_row = pub_data.iloc[0]
        row["subscriber_cpu_utilized"] = cpu_percent(
            sub_row, "avg_cpu_utilized", "avg_task_clock_ms", "avg_time_elapsed"
        )
        row["num_subscribers"] = int(require_number(sub_row, "num_subscribers"))
        row["publisher_cpu_utilized"] = cpu_percent(
            pub_row, "cpu_utilized", "task_clock_ms", "time_elapsed"
        )

        row["total_cpu_utilized"] = row["publisher_cpu_utilized"] + (
            row["subscriber_cpu_utilized"] * row["num_subscribers"]
        )

        if row["publisher_cpu_utilized"] > 0:
            row["sub_pub_ratio"] = (
                row["subscriber_cpu_utilized"] / row["publisher_cpu_utilized"]
            )
        else:
            row["sub_pub_ratio"] = 0

        combined_data.append(row)

    combined_df = pd.DataFrame(combined_data)
    if combined_df.empty:
        return combined_df
    combined_df.sort_values(["middleware", "payload_size", "hz"], inplace=True)

    return combined_df


def create_publisher_cpu_chart(combined_df, output_dir):
    """Create bar chart showing publisher CPU utilization."""

    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    def format_payload(p):
        if p >= 1048576:  # 1 MiB = 1024 * 1024 bytes
            return f"{p // 1048576}MB"
        elif p >= 1024:
            return f"{p // 1024}KB"
        else:
            return f"{p}B"

    plt.figure(
        figsize=(
            bar_chart_width(payload_sizes, max_bars_per_payload(combined_df)),
            BAR_CHART_HEIGHT_IN,
        )
    )
    x = grouped_bar_x(payload_sizes)

    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}
    legend_added = set()

    for payload_idx, payload in enumerate(payload_sizes):
        payload_data = combined_df[combined_df["payload_size"] == payload]
        sorted_data = payload_data.sort_values("publisher_cpu_utilized")
        bar_count = len(sorted_data)
        bar_width = visible_bar_width(bar_count)

        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["publisher_cpu_utilized"]
            color = color_dict[mw]
            center = bar_center(x[payload_idx], bar_idx, bar_count)

            bar = plt.bar(
                center,
                value,
                bar_width,
                color=color,
                edgecolor="black",
                label=mw if mw not in legend_added else "",
            )
            legend_added.add(mw)

            if value > 0:
                height = bar[0].get_height()
                plt.text(
                    center,
                    height,
                    f"{value:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    rotation=90,
                )

    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel("Publisher CPU Utilization (%)", fontsize=12, fontweight="bold")
    plt.title(
        "Publisher CPU Utilization Across Middlewares (Bars sorted by value)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xticks(x, [format_payload(p) for p in payload_sizes], rotation=45)

    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)
    plt.tight_layout()

    output_path = Path(output_dir) / "perf_publisher_cpu_utilization.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Created: {output_path}")


def create_subscriber_cpu_chart(combined_df, output_dir):
    """Create bar chart showing subscriber CPU utilization (per subscriber)."""

    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    def format_payload(p):
        if p >= 1048576:
            return f"{p // 1048576}MB"
        elif p >= 1024:
            return f"{p // 1024}KB"
        else:
            return f"{p}B"

    plt.figure(
        figsize=(
            bar_chart_width(payload_sizes, max_bars_per_payload(combined_df)),
            BAR_CHART_HEIGHT_IN,
        )
    )
    x = grouped_bar_x(payload_sizes)

    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}
    legend_added = set()

    for payload_idx, payload in enumerate(payload_sizes):
        payload_data = combined_df[combined_df["payload_size"] == payload]
        sorted_data = payload_data.sort_values("subscriber_cpu_utilized")
        bar_count = len(sorted_data)
        bar_width = visible_bar_width(bar_count)

        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["subscriber_cpu_utilized"]
            color = color_dict[mw]
            center = bar_center(x[payload_idx], bar_idx, bar_count)

            bar = plt.bar(
                center,
                value,
                bar_width,
                color=color,
                edgecolor="black",
                label=mw if mw not in legend_added else "",
            )
            legend_added.add(mw)

            if value > 0:
                height = bar[0].get_height()
                if value < 0.1:
                    fmt = f"{value:.2f}%"
                    offset = max(height * 0.02, 0.02)
                    fontsize = 7
                else:
                    fmt = f"{value:.1f}%"
                    offset = 0
                    fontsize = 7

                plt.text(
                    center,
                    height + offset,
                    fmt,
                    ha="center",
                    va="bottom",
                    fontsize=fontsize,
                    rotation=90,
                )

    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel(
        "Subscriber CPU Utilization (%) per subscriber", fontsize=12, fontweight="bold"
    )
    plt.title(
        "Subscriber CPU Utilization Across Middlewares (Bars sorted by value, per subscriber)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xticks(x, [format_payload(p) for p in payload_sizes], rotation=45)

    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)
    plt.tight_layout()

    output_path = Path(output_dir) / "perf_subscriber_cpu_utilization.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Created: {output_path}")


def create_total_cpu_chart(combined_df, output_dir):
    """Create bar chart showing total CPU utilization."""

    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    def format_payload(p):
        if p >= 1048576:
            return f"{p // 1048576}MB"
        elif p >= 1024:
            return f"{p // 1024}KB"
        else:
            return f"{p}B"

    plt.figure(
        figsize=(
            bar_chart_width(payload_sizes, max_bars_per_payload(combined_df)),
            BAR_CHART_HEIGHT_IN,
        )
    )
    x = grouped_bar_x(payload_sizes)

    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}
    legend_added = set()

    for payload_idx, payload in enumerate(payload_sizes):
        payload_data = combined_df[combined_df["payload_size"] == payload]
        sorted_data = payload_data.sort_values("total_cpu_utilized")
        bar_count = len(sorted_data)
        bar_width = visible_bar_width(bar_count)

        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["total_cpu_utilized"]
            color = color_dict[mw]
            center = bar_center(x[payload_idx], bar_idx, bar_count)

            bar = plt.bar(
                center,
                value,
                bar_width,
                color=color,
                edgecolor="black",
                label=mw if mw not in legend_added else "",
            )
            legend_added.add(mw)

            if value > 1:
                height = bar[0].get_height()
                plt.text(
                    center,
                    height,
                    f"{value:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    rotation=90,
                )

    subscriber_counts = sorted(
        {int(value) for value in combined_df["num_subscribers"].dropna().unique()}
    )
    if len(subscriber_counts) == 1:
        subscriber_label = f"{subscriber_counts[0]} Subscribers"
    else:
        subscriber_label = "Subscribers"

    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel(
        f"Total CPU Utilization (%)\n(Publisher + {subscriber_label})",
        fontsize=12,
        fontweight="bold",
    )
    plt.title(
        "Total CPU Utilization Across Middlewares (Bars sorted by value)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xticks(x, [format_payload(p) for p in payload_sizes], rotation=45)

    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)
    plt.tight_layout()

    output_path = Path(output_dir) / "perf_total_cpu_utilization.png"
    plt.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close()
    print(f"Created: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create CPU utilization plots from performance CSV data"
    )
    parser.add_argument(
        "subscriber_csv",
        help="Path to subscriber averages CSV file (e.g., perf_subscribers.csv)",
    )
    parser.add_argument(
        "publisher_csv", help="Path to publisher CSV file (e.g., perf_publishers.csv)"
    )
    parser.add_argument("output_dir", help="Directory where plots will be saved")
    args = parser.parse_args()

    subscriber_path = Path(args.subscriber_csv)
    publisher_path = Path(args.publisher_csv)
    output_dir = Path(args.output_dir)

    if not subscriber_path.exists():
        print(f"Error: Subscriber CSV file '{subscriber_path}' not found!")
        return

    if not publisher_path.exists():
        print(f"Error: Publisher CSV file '{publisher_path}' not found!")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print("Loading and processing data...")
    combined_df = load_and_merge_data(subscriber_path, publisher_path)
    if combined_df.empty:
        print("No performance data found.")
        return

    print(f"\nData loaded:")
    print(f"- Middlewares: {len(combined_df['middleware'].unique())}")
    print(f"- Payload sizes: {len(combined_df['payload_size'].unique())}")
    print(f"- Total configurations: {len(combined_df)}")

    # Print sample data
    if not combined_df[combined_df["payload_size"] == 256].empty:
        print("\nSample of sorted data for 256B payload (Publisher CPU):")
        sample_256 = combined_df[combined_df["payload_size"] == 256].sort_values(
            "publisher_cpu_utilized"
        )
        for _, row in sample_256.iterrows():
            print(f"  {row['middleware']:25} {row['publisher_cpu_utilized']:.2f}%")

        print("\nSample of sorted data for 256B payload (Subscriber CPU):")
        sample_256 = combined_df[combined_df["payload_size"] == 256].sort_values(
            "subscriber_cpu_utilized"
        )
        for _, row in sample_256.iterrows():
            print(f"  {row['middleware']:25} {row['subscriber_cpu_utilized']:.2f}%")

    # Create all three charts
    create_publisher_cpu_chart(combined_df, output_dir)
    create_subscriber_cpu_chart(combined_df, output_dir)
    create_total_cpu_chart(combined_df, output_dir)

    print("\nAll CPU utilization plots created successfully!")


if __name__ == "__main__":
    main()
