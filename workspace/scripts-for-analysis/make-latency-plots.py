#!/usr/bin/env python3

import argparse
import os
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


def create_sorted_bar_chart(
    df,
    metric="avg_latency_ms",
    title="Average Latency",
    exclude_middlewares=None,
    output_dir=".",
):
    """Create bar chart with bars sorted in increasing order for each payload size."""

    # Filter out excluded middlewares
    if exclude_middlewares:
        df = df[~df["middleware"].isin(exclude_middlewares)]

    if df.empty:
        print(f"Warning: No data left after filtering for {title}. Skipping plot.")
        return

    # Get unique payload sizes and middlewares
    payload_sizes = sorted(df["payload_size"].unique())
    middlewares = df["middleware"].unique()
    max_bars_per_group = max(
        df[df["payload_size"] == payload]["middleware"].nunique()
        for payload in payload_sizes
    )

    # Create figure
    plt.figure(
        figsize=(
            bar_chart_width(payload_sizes, max_bars_per_group),
            BAR_CHART_HEIGHT_IN,
        )
    )

    # Colors for each middleware (consistent across all plots)
    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    mw_to_color = {mw: colors[i] for i, mw in enumerate(middlewares)}

    # Set width and positions
    x = grouped_bar_x(payload_sizes)

    # Track which middlewares have been added to legend
    legend_added = set()

    # For each payload size
    for payload_idx, payload in enumerate(payload_sizes):
        # Get all data for this payload size
        payload_df = df[df["payload_size"] == payload]

        # Sort middlewares by metric value in increasing order
        sorted_mws = payload_df.sort_values(metric)["middleware"].tolist()

        # Plot bars in sorted order
        bar_count = len(sorted_mws)
        bar_width = visible_bar_width(bar_count)
        for bar_idx, mw in enumerate(sorted_mws):
            value = payload_df[payload_df["middleware"] == mw][metric].values[0]
            color = mw_to_color[mw]
            center = bar_center(x[payload_idx], bar_idx, bar_count)

            # Plot bar
            bar = plt.bar(
                center,
                value,
                bar_width,
                color=color,
                edgecolor="black",
                label=mw if mw not in legend_added else "",
            )

            # Add to legend set
            legend_added.add(mw)

            # Add value label
            height = bar[0].get_height()
            plt.text(
                center,
                height + 0.01,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=7,
                rotation=90,
            )

    # Configure plot
    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel(f"{title} (ms)", fontsize=12, fontweight="bold")

    # Update title if excluding middlewares
    if exclude_middlewares:
        excluded_str = ", ".join(exclude_middlewares)
        plt.title(
            f"{title} vs Payload Size (Excluding: {excluded_str})",
            fontsize=14,
            fontweight="bold",
        )
    else:
        plt.title(f"{title} vs Payload Size", fontsize=14, fontweight="bold")

    # Format x-axis labels
    def format_payload(p):
        if p >= 1048576:
            return f"{p // 1048576}MB"
        elif p >= 1024:
            return f"{p // 1024}KB"
        else:
            return f"{p}B"

    plt.xticks(x, [format_payload(p) for p in payload_sizes])

    handles = []
    labels = []
    for mw in middlewares:
        handles.append(plt.Rectangle((0, 0), 1, 1, fc=mw_to_color[mw]))
        labels.append(mw)
    plt.legend(handles, labels, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()

    # Update filename if excluding middlewares
    if exclude_middlewares:
        excluded_suffix = "_exclude_" + "_".join(exclude_middlewares)
        filename = f"bar_chart_{metric.split('_')[0]}{excluded_suffix}.png"
    else:
        filename = f"bar_chart_{metric.split('_')[0]}.png"

    full_path = Path(output_dir) / filename
    plt.savefig(full_path, dpi=300, bbox_inches="tight")
    plt.close()  # Close to free memory

    print(f"Created: {full_path}")


def create_line_plot(
    df,
    metric="avg_latency_ms",
    title="Average Latency",
    exclude_middlewares=None,
    output_dir=".",
):
    """Create line plot showing all middlewares."""

    # Filter out excluded middlewares
    if exclude_middlewares:
        df = df[~df["middleware"].isin(exclude_middlewares)]

    if df.empty:
        print(f"Warning: No data left after filtering for {title}. Skipping plot.")
        return

    middlewares = df["middleware"].unique()
    payload_sizes = sorted(df["payload_size"].unique())

    plt.figure(figsize=(12, 7))

    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))

    for i, mw in enumerate(middlewares):
        mw_data = df[df["middleware"] == mw].sort_values("payload_size")
        plt.plot(
            mw_data["payload_size"],
            mw_data[metric],
            marker="o",
            linewidth=2,
            markersize=6,
            label=mw,
            color=colors[i],
        )

    plt.xscale("log")
    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel(f"{title} (ms)", fontsize=12, fontweight="bold")

    # Update title if excluding middlewares
    if exclude_middlewares:
        excluded_str = ", ".join(exclude_middlewares)
        plt.title(
            f"{title} vs Payload Size (Excluding: {excluded_str})",
            fontsize=14,
            fontweight="bold",
        )
    else:
        plt.title(f"{title} vs Payload Size", fontsize=14, fontweight="bold")

    plt.grid(True, alpha=0.3, which="both")

    def format_payload(p):
        if p >= 1048576:
            return f"{p // 1048576}MB"
        elif p >= 1024:
            return f"{p // 1024}KB"
        else:
            return f"{p}B"

    plt.xticks(payload_sizes, [format_payload(p) for p in payload_sizes], rotation=45)
    plt.legend(bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.tight_layout()

    # Update filename if excluding middlewares
    if exclude_middlewares:
        excluded_suffix = "_exclude_" + "_".join(exclude_middlewares)
        filename = f"latencies_{metric.split('_')[0]}{excluded_suffix}.png"
    else:
        filename = f"latencies_{metric.split('_')[0]}.png"

    full_path = Path(output_dir) / filename
    plt.savefig(full_path, dpi=300, bbox_inches="tight")
    plt.close()  # Close to free memory

    print(f"Created: {full_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Create latency plots from CSV data with optional middleware exclusion"
    )
    parser.add_argument(
        "input_csv", help="Path to the input CSV file (e.g., latencies.csv)"
    )
    parser.add_argument("output_dir", help="Directory where plots will be saved")
    parser.add_argument(
        "--exclude", nargs="+", help="List of middlewares to exclude", default=None
    )
    args = parser.parse_args()

    input_csv = Path(args.input_csv)
    output_dir = Path(args.output_dir)

    if not input_csv.exists():
        print(f"Error: Input CSV file '{input_csv}' not found!")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Reading {input_csv}...")
    df = pd.read_csv(input_csv)

    # Show available middlewares
    all_middlewares = df["middleware"].unique()
    print(f"Available middlewares: {list(all_middlewares)}")

    if args.exclude:
        print(f"Excluding middlewares: {args.exclude}")
        # Validate excluded middlewares
        invalid = [mw for mw in args.exclude if mw not in all_middlewares]
        if invalid:
            print(f"Warning: The following middlewares were not found: {invalid}")

    print("\nCreating sorted bar charts...")
    print("=" * 50)

    create_sorted_bar_chart(
        df, "avg_latency_ms", "Average Latency", args.exclude, output_dir
    )
    create_sorted_bar_chart(
        df, "median_latency_ms", "Median Latency", args.exclude, output_dir
    )
    create_sorted_bar_chart(
        df, "p99_latency_ms", "P99 Latency", args.exclude, output_dir
    )

    print("\nCreating line plots...")
    print("=" * 50)

    create_line_plot(df, "avg_latency_ms", "Average Latency", args.exclude, output_dir)
    create_line_plot(
        df, "median_latency_ms", "Median Latency", args.exclude, output_dir
    )
    create_line_plot(df, "p99_latency_ms", "P99 Latency", args.exclude, output_dir)

    print("\n" + "=" * 50)
    print("All plots created successfully!")


if __name__ == "__main__":
    main()
