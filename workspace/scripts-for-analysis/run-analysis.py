#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def require_container() -> None:
    if not Path("/.dockerenv").exists():
        raise SystemExit("Анализ запускается только внутри контейнера.")


def run_script(script_dir: Path, script_name: str, *args: Path | str) -> None:
    subprocess.run(
        [sys.executable, str(script_dir / script_name), *map(str, args)],
        cwd=script_dir,
        check=True,
    )


if __name__ == "__main__":
    require_container()
    parser = argparse.ArgumentParser()
    parser.add_argument("benchmark_data_path")
    parser.add_argument("analysis_data_path")
    args = parser.parse_args()

    script_dir = Path(__file__).resolve().parent
    output_dir = Path(args.analysis_data_path)

    run_script(
        script_dir,
        "collect-latency-data.py",
        args.benchmark_data_path,
        output_dir,
    )
    run_script(script_dir, "collect-perf-data.py", args.benchmark_data_path, output_dir)
    run_script(script_dir, "make-latency-plots.py", output_dir / "latencies.csv", output_dir)
    run_script(
        script_dir,
        "make-perf-plots.py",
        output_dir / "perf_subscribers.csv",
        output_dir / "perf_publishers.csv",
        output_dir,
    )
