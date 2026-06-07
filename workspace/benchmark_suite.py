#!/usr/bin/env python3

from __future__ import annotations

import argparse
import subprocess
import sys
import time
from pathlib import Path

from benchmark_runner import require_container


WORKSPACE = Path("/root/workspace")

BENCHMARKS = [
    ["run-ros2-cyclone.py"],
    ["run-ros2-fast.py"],
    ["run-ros2-fast-loaned.py"],
    ["run-ros2-zenoh.py"],
    ["run-zmq-flatbuffers.py", "--with-tcp"],
    ["run-zmq-flatbuffers.py", "--with-ipc"],
    ["run-zmq-protobuf.py", "--with-tcp"],
    ["run-zmq-protobuf.py", "--with-ipc"],
    ["run-zmq-capnproto.py", "--with-tcp"],
    ["run-zmq-capnproto.py", "--with-ipc"],
    ["run-rust-iceoryx2.py"],
    ["run-rust-iceoryx2-flatbuffers.py"],
    ["run-rust-zenoh.py"],
    ["run-rust-zenoh-quic.py"],
    ["run-rust-zenoh-unixsock.py"],
    ["run-rust-zenoh-shm.py"],
    ["run-rust-zenoh-flatbuffers-tcp.py"],
    ["run-rust-zenoh-flatbuffers-quic.py"],
    ["run-rust-zenoh-flatbuffers-unixsock.py"],
    ["run-rust-zenoh-flatbuffers-shm.py"],
]


def run_suite(
    default_config: str,
    default_subscribers: int,
    argv: list[str] | None = None,
) -> None:
    require_container()
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=default_config)
    parser.add_argument("--num-subscribers", type=int, default=default_subscribers)
    parser.add_argument("--clean", action="store_true")
    parser.add_argument("--no-perf", action="store_true")
    parser.add_argument("--pause-between-s", type=float, default=2.0)
    args = parser.parse_args(argv)

    for benchmark in BENCHMARKS:
        command = [
            sys.executable,
            str(WORKSPACE / benchmark[0]),
            *benchmark[1:],
            "--config",
            args.config,
            "--num-subscribers",
            str(args.num_subscribers),
        ]
        if args.clean:
            command.append("--clean")
        if args.no_perf:
            command.append("--no-perf")

        print("\n## " + " ".join(command), flush=True)
        subprocess.run(command, cwd=WORKSPACE, check=True)
        time.sleep(args.pause_between_s)
