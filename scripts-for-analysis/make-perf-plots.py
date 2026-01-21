#!/usr/bin/env python3

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


def load_and_merge_data(
    subscriber_csv="perf_subscriber_averages.csv", publisher_csv="perf_publishers.csv"
):
    """Load and merge subscriber and publisher data."""

    # Load subscriber data
    subscriber_df = pd.read_csv(subscriber_csv)

    # Load publisher data
    publisher_df = pd.read_csv(publisher_csv)

    # Create a combined dataframe
    # For subscriber data, we have avg_cpu_utilized
    # For publisher data, we have cpu_utilized
    combined_data = []

    # Get all unique configurations
    all_middlewares = set(subscriber_df["middleware"].unique()) | set(
        publisher_df["middleware"].unique()
    )
    all_payloads = set(subscriber_df["payload_size"].unique()) | set(
        publisher_df["payload_size"].unique()
    )

    # Process each configuration
    for mw in sorted(all_middlewares):
        # Get subscriber data for this middleware
        sub_mw_data = subscriber_df[subscriber_df["middleware"] == mw]

        # Get publisher data for this middleware
        pub_mw_data = publisher_df[publisher_df["middleware"] == mw]

        # Process each payload size
        for payload in sorted(all_payloads):
            # Get subscriber data for this payload
            sub_data = sub_mw_data[sub_mw_data["payload_size"] == payload]

            # Get publisher data for this payload
            pub_data = pub_mw_data[pub_mw_data["payload_size"] == payload]

            if not sub_data.empty or not pub_data.empty:
                row = {
                    "middleware": mw,
                    "payload_size": payload,
                    "hz": 20.0,  # All are 20Hz
                }

                # Add subscriber data if available
                if not sub_data.empty:
                    row["subscriber_cpu_utilized"] = (
                        sub_data.iloc[0]["avg_cpu_utilized"] * 100
                    )  # Convert to percentage
                    row["num_subscribers"] = sub_data.iloc[0]["num_subscribers"]
                else:
                    row["subscriber_cpu_utilized"] = 0
                    row["num_subscribers"] = 0

                # Add publisher data if available
                if not pub_data.empty:
                    row["publisher_cpu_utilized"] = (
                        pub_data.iloc[0]["cpu_utilized"] * 100
                    )  # Convert to percentage
                else:
                    row["publisher_cpu_utilized"] = 0

                # Calculate total CPU utilization (publisher + sum of subscribers)
                # Note: This assumes subscribers run in parallel
                # For 3 subscribers: total = publisher + (avg_subscriber * 3)
                row["total_cpu_utilized"] = row["publisher_cpu_utilized"] + (
                    row["subscriber_cpu_utilized"] * row["num_subscribers"]
                )

                # Calculate ratio (subscriber/publisher)
                if row["publisher_cpu_utilized"] > 0:
                    row["sub_pub_ratio"] = (
                        row["subscriber_cpu_utilized"] / row["publisher_cpu_utilized"]
                    )
                else:
                    row["sub_pub_ratio"] = 0

                combined_data.append(row)

    combined_df = pd.DataFrame(combined_data)

    # Sort the dataframe
    combined_df.sort_values(["middleware", "payload_size"], inplace=True)

    return combined_df


def create_publisher_cpu_chart(combined_df):
    """Create bar chart showing publisher CPU utilization."""

    # Get unique middlewares and payload sizes
    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    # Format payload size for display
    def format_payload(p):
        if p >= 1048576:
            return f"{p//1048576}MB"
        elif p >= 1024:
            return f"{p//1024}KB"
        else:
            return f"{p}B"

    plt.figure(figsize=(16, 8))

    # Group by payload size
    x = np.arange(len(payload_sizes))

    # Create a color map for consistent coloring
    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}

    # Track which middlewares have been added to legend
    legend_added = set()

    # For each payload size, sort middlewares by publisher CPU in increasing order
    for payload_idx, payload in enumerate(payload_sizes):
        # Get all data for this payload size
        payload_data = combined_df[combined_df["payload_size"] == payload]

        # Sort middlewares by publisher CPU utilization (increasing order)
        sorted_data = payload_data.sort_values("publisher_cpu_utilized")

        # Calculate bar width based on number of middlewares
        bar_width = 0.8 / len(sorted_data)

        # Plot bars in sorted order
        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["publisher_cpu_utilized"]
            color = color_dict[mw]

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

            # FIXED: Add value label on top of bar for ALL values > 0
            if value > 0:  # Changed from > 0.5 to > 0
                height = bar[0].get_height()
                plt.text(
                    bar[0].get_x() + bar_width / 2.0,
                    height,
                    f"{value:.1f}%",  # Shows 1 decimal place
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel("Publisher CPU Utilization (%)", fontsize=12, fontweight="bold")
    plt.title(
        "Publisher CPU Utilization Across Middlewares (Bars sorted by value)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xticks(x, [format_payload(p) for p in payload_sizes], rotation=45)

    # Create custom legend
    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)  # Start y-axis from 0

    plt.tight_layout()
    plt.savefig("perf_publisher_cpu_utilization.png", dpi=300, bbox_inches="tight")
    plt.show()


def create_subscriber_cpu_chart(combined_df):
    """Create bar chart showing subscriber CPU utilization (per subscriber)."""

    # Get unique middlewares and payload sizes
    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    # Format payload size for display
    def format_payload(p):
        if p >= 1048576:
            return f"{p//1048576}MB"
        elif p >= 1024:
            return f"{p//1024}KB"
        else:
            return f"{p}B"

    plt.figure(figsize=(16, 8))

    # Group by payload size
    x = np.arange(len(payload_sizes))

    # Create a color map for consistent coloring
    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}

    # Track which middlewares have been added to legend
    legend_added = set()

    # For each payload size, sort middlewares by subscriber CPU in increasing order
    for payload_idx, payload in enumerate(payload_sizes):
        # Get all data for this payload size
        payload_data = combined_df[combined_df["payload_size"] == payload]

        # Sort middlewares by subscriber CPU utilization (increasing order)
        sorted_data = payload_data.sort_values("subscriber_cpu_utilized")

        # Calculate bar width based on number of middlewares
        bar_width = 0.8 / len(sorted_data)

        # Plot bars in sorted order
        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["subscriber_cpu_utilized"]
            color = color_dict[mw]

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

            # FIXED: Add value label on top of bar for ALL values > 0
            if value > 0:  # Changed from > 0.5 to > 0
                height = bar[0].get_height()

                # Use 2 decimal places for very small values (< 0.1%)
                if value < 0.1:
                    fmt = f"{value:.2f}%"
                else:
                    fmt = f"{value:.1f}%"

                # Add a small offset so labels don't sit right on top of tiny bars
                offset = max(height * 0.02, 0.02)
                plt.text(
                    bar[0].get_x() + bar_width / 2.0,
                    height + offset,
                    fmt,
                    ha="center",
                    va="bottom",
                    fontsize=(
                        7 if value < 0.1 else 8
                    ),  # Smaller font for very small values
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

    # Create custom legend
    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)  # Start y-axis from 0

    plt.tight_layout()
    plt.savefig("perf_subscriber_cpu_utilization.png", dpi=300, bbox_inches="tight")
    plt.show()


def create_total_cpu_chart(combined_df):
    """Create bar chart showing total CPU utilization."""

    # Get unique middlewares and payload sizes
    middlewares = combined_df["middleware"].unique()
    payload_sizes = sorted(combined_df["payload_size"].unique())

    # Format payload size for display
    def format_payload(p):
        if p >= 1048576:
            return f"{p//1048576}MB"
        elif p >= 1024:
            return f"{p//1024}KB"
        else:
            return f"{p}B"

    plt.figure(figsize=(16, 8))

    # Group by payload size
    x = np.arange(len(payload_sizes))

    # Create a color map for consistent coloring
    colors = plt.cm.tab20(np.linspace(0, 1, len(middlewares)))
    color_dict = {mw: colors[i] for i, mw in enumerate(middlewares)}

    # Track which middlewares have been added to legend
    legend_added = set()

    # For each payload size, sort middlewares by total CPU in increasing order
    for payload_idx, payload in enumerate(payload_sizes):
        # Get all data for this payload size
        payload_data = combined_df[combined_df["payload_size"] == payload]

        # Sort middlewares by total CPU utilization (increasing order)
        sorted_data = payload_data.sort_values("total_cpu_utilized")

        # Calculate bar width based on number of middlewares
        bar_width = 0.8 / len(sorted_data)

        # Plot bars in sorted order
        for bar_idx, (_, row) in enumerate(sorted_data.iterrows()):
            mw = row["middleware"]
            value = row["total_cpu_utilized"]
            color = color_dict[mw]

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

            # Add value label on top of bar
            if value > 1:  # Only label values > 1%
                height = bar[0].get_height()
                plt.text(
                    bar[0].get_x() + bar_width / 2.0,
                    height,
                    f"{value:.1f}%",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                )

    plt.xlabel("Payload Size", fontsize=12, fontweight="bold")
    plt.ylabel(
        "Total CPU Utilization (%)\n(Publisher + 3 Subscribers)",
        fontsize=12,
        fontweight="bold",
    )
    plt.title(
        "Total CPU Utilization Across Middlewares (Bars sorted by value)",
        fontsize=14,
        fontweight="bold",
    )
    plt.xticks(x, [format_payload(p) for p in payload_sizes], rotation=45)

    # Create custom legend
    from matplotlib.patches import Patch

    legend_elements = [Patch(facecolor=color_dict[mw], label=mw) for mw in middlewares]
    plt.legend(handles=legend_elements, bbox_to_anchor=(1.05, 1), loc="upper left")

    plt.grid(True, alpha=0.3, axis="y")
    plt.ylim(bottom=0)  # Start y-axis from 0

    plt.tight_layout()
    plt.savefig("perf_total_cpu_utilization.png", dpi=300, bbox_inches="tight")
    plt.show()


def main():
    # Define CSV files
    subscriber_csv = "perf_subscribers.csv"
    publisher_csv = "perf_publishers.csv"

    # Check if files exist
    if not os.path.exists(subscriber_csv):
        print(f"Error: {subscriber_csv} not found!")
        return

    if not os.path.exists(publisher_csv):
        print(f"Error: {publisher_csv} not found!")
        return

    # Load and merge data
    print("Loading and processing data...")
    combined_df = load_and_merge_data(subscriber_csv, publisher_csv)

    print(f"\nData loaded:")
    print(f"- Middlewares: {len(combined_df['middleware'].unique())}")
    print(f"- Payload sizes: {len(combined_df['payload_size'].unique())}")
    print(f"- Total configurations: {len(combined_df)}")

    # Print sample of sorted data for publisher CPU
    print("\nSample of sorted data for 256B payload (Publisher CPU):")
    sample_256 = combined_df[combined_df["payload_size"] == 256].sort_values(
        "publisher_cpu_utilized"
    )
    for _, row in sample_256.iterrows():
        print(f"  {row['middleware']:25} {row['publisher_cpu_utilized']:.2f}%")

    # Print sample of sorted data for subscriber CPU
    print("\nSample of sorted data for 256B payload (Subscriber CPU):")
    sample_256 = combined_df[combined_df["payload_size"] == 256].sort_values(
        "subscriber_cpu_utilized"
    )
    for _, row in sample_256.iterrows():
        print(f"  {row['middleware']:25} {row['subscriber_cpu_utilized']:.2f}%")

    # Create all three charts
    create_publisher_cpu_chart(combined_df)
    create_subscriber_cpu_chart(combined_df)


if __name__ == "__main__":
    main()
