#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import argparse


def create_sorted_bar_chart(
    df, metric="avg_latency_ms", title="Average Latency", exclude_middlewares=None
):
    """Create bar chart with bars sorted in increasing order for each payload size."""

    # Filter out excluded middlewares
    if exclude_middlewares:
        df = df[~df["middleware"].isin(exclude_middlewares)]

    # Get unique payload sizes and middlewares
    payload_sizes = sorted(df["payload_size"].unique())
    middlewares = df["middleware"].unique()

    # Create figure
    plt.figure(figsize=(14, 8))

    # Colors for each middleware (consistent across all plots)
    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    mw_to_color = {mw: colors[i] for i, mw in enumerate(middlewares)}

    # Set width and positions
    num_middlewares = len(middlewares)
    bar_width = 0.8 / num_middlewares
    x = np.arange(len(payload_sizes))

    # Track which middlewares have been added to legend
    legend_added = set()

    # For each payload size
    for payload_idx, payload in enumerate(payload_sizes):
        # Get all data for this payload size
        payload_df = df[df["payload_size"] == payload]

        # Sort middlewares by metric value in increasing order
        sorted_mws = payload_df.sort_values(metric)["middleware"].tolist()

        # Plot bars in sorted order
        for bar_idx, mw in enumerate(sorted_mws):
            value = payload_df[payload_df["middleware"] == mw][metric].values[0]
            color = mw_to_color[mw]

            # Plot bar
            bar = plt.bar(
                x[payload_idx] + bar_idx * bar_width - 0.4,
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
                x[payload_idx] + bar_idx * bar_width - 0.4 + bar_width / 2,
                height + 0.01,
                f"{value:.2f}",
                ha="center",
                va="bottom",
                fontsize=8,
                rotation=45,
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
            return f"{p//1048576}MB"
        elif p >= 1024:
            return f"{p//1024}KB"
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

    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Created: {filename}")


def create_line_plot(
    df, metric="avg_latency_ms", title="Average Latency", exclude_middlewares=None
):
    """Create line plot showing all middlewares."""

    # Filter out excluded middlewares
    if exclude_middlewares:
        df = df[~df["middleware"].isin(exclude_middlewares)]

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
            return f"{p//1048576}MB"
        elif p >= 1024:
            return f"{p//1024}KB"
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

    plt.savefig(filename, dpi=300, bbox_inches="tight")
    plt.show()

    print(f"Created: {filename}")


def main():
    parser = argparse.ArgumentParser(
        description="Create latency plots with optional middleware exclusion"
    )
    parser.add_argument(
        "--exclude", nargs="+", help="List of middlewares to exclude", default=None
    )
    args = parser.parse_args()

    csv_file = "latencies.csv"

    if not os.path.exists(csv_file):
        print(f"Error: {csv_file} not found!")
        return

    print(f"Reading {csv_file}...")
    df = pd.read_csv(csv_file)

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

    create_sorted_bar_chart(df, "avg_latency_ms", "Average Latency", args.exclude)
    create_sorted_bar_chart(df, "median_latency_ms", "Median Latency", args.exclude)
    create_sorted_bar_chart(df, "p99_latency_ms", "P99 Latency", args.exclude)

    print("\nCreating line plots...")
    print("=" * 50)

    create_line_plot(df, "avg_latency_ms", "Average Latency", args.exclude)
    create_line_plot(df, "median_latency_ms", "Median Latency", args.exclude)
    create_line_plot(df, "p99_latency_ms", "P99 Latency", args.exclude)

    print("\n" + "=" * 50)
    print("All plots created successfully!")


if __name__ == "__main__":
    main()
