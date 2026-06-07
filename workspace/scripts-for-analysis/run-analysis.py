#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
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


def host_owner() -> tuple[int, int]:
    uid = os.environ.get("TRANSPORT_BENCHMARK_CHOWN_UID")
    gid = os.environ.get("TRANSPORT_BENCHMARK_CHOWN_GID")
    if not uid or not gid:
        raise SystemExit(
            "TRANSPORT_BENCHMARK_CHOWN_UID/GID are not set; "
            "run analysis through ./env_run.sh"
        )

    target_uid = int(uid)
    target_gid = int(gid)
    if target_uid == 0 or target_gid == 0:
        raise SystemExit("refusing to chown analysis results to root")
    return target_uid, target_gid


def fix_output_ownership(output_dir: Path) -> None:
    target_uid, target_gid = host_owner()
    for root, dirs, files in os.walk(output_dir):
        os.lchown(root, target_uid, target_gid)
        for name in [*dirs, *files]:
            os.lchown(Path(root) / name, target_uid, target_gid)


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
    fix_output_ownership(output_dir)
