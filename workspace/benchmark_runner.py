#!/usr/bin/env python3

from __future__ import annotations

import argparse
import os
import re
import shutil
import signal
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


WORKSPACE = Path("/root/workspace")
ZSH = "/bin/zsh"
FAST_DDS_PROFILES_FILE = WORKSPACE / "ros2_fast" / "dds_config.xml"
FAST_DDS_LOANED_PROFILES_FILE = WORKSPACE / "ros2_fast_loaned" / "dds_config.xml"
ZENOH_QUIC_CERT_DIR = Path("/tmp/transport-benchmark-zenoh-quic-certs")
ZENOH_QUIC_CA_FILE = ZENOH_QUIC_CERT_DIR / "ca.pem"
ZENOH_QUIC_CA_KEY_FILE = ZENOH_QUIC_CERT_DIR / "ca.key"
ZENOH_QUIC_CERT_FILE = ZENOH_QUIC_CERT_DIR / "server.pem"
ZENOH_QUIC_KEY_FILE = ZENOH_QUIC_CERT_DIR / "server.key"
ZENOH_QUIC_CSR_FILE = ZENOH_QUIC_CERT_DIR / "server.csr"
ZENOH_QUIC_EXT_FILE = ZENOH_QUIC_CERT_DIR / "server.ext"
CYCLONE_DDS_URI = (
    '<CycloneDDS><Domain><General><AllowMulticast>false</AllowMulticast>'
    '<Interfaces><NetworkInterface address="127.0.0.1"/></Interfaces>'
    '<MaxMessageSize>65500B</MaxMessageSize></General><Internal>'
    '<Watermarks><WhcHigh>100MB</WhcHigh></Watermarks></Internal>'
    '</Domain></CycloneDDS>'
)


@dataclass(frozen=True)
class BenchmarkSpec:
    key: str
    title: str
    project_dir: Path
    output_dir_name: str
    build_kind: str
    subscriber: list[str]
    publisher: list[str]
    cleanup_patterns: list[str]
    ros_package: str | None = None
    rmw: str | None = None
    custom_latency_dir: bool = False
    cmake_build_dir: str = "build"
    extra_env: dict[str, str] = field(default_factory=dict)
    subscriber_start_delay_s: float = 0.5
    publisher_start_delay_s: float = 0.1
    sidecar: list[str] | None = None
    sidecar_log: str | None = None
    sidecar_start_delay_s: float = 1.0
    transport_arg: str | None = None
    extra_args: list[str] = field(default_factory=list)
    publisher_exits: bool = True
    final_cleanup_patterns: list[str] = field(default_factory=list)


class Runner:
    def __init__(self) -> None:
        self.processes: list[subprocess.Popen] = []
        self.perf_processes: list[subprocess.Popen] = []
        self.sidecars: list[subprocess.Popen] = []

    def add_process(self, process: subprocess.Popen) -> subprocess.Popen:
        self.processes.append(process)
        return process

    def add_perf(self, process: subprocess.Popen | None) -> None:
        if process is not None:
            self.perf_processes.append(process)

    def add_sidecar(self, process: subprocess.Popen) -> subprocess.Popen:
        self.sidecars.append(process)
        return process

    def cleanup_run(self, patterns: Iterable[str]) -> None:
        stop_perf(self.perf_processes)
        terminate_processes(self.processes)
        kill_patterns(patterns)
        self.perf_processes = []
        self.processes = []

    def cleanup_all(self, patterns: Iterable[str]) -> None:
        self.cleanup_run(patterns)
        terminate_processes(self.sidecars)
        self.sidecars = []
        kill_patterns(patterns)


def require_container() -> None:
    in_container = Path("/.dockerenv").exists() or os.environ.get(
        "TRANSPORT_BENCHMARK_CONTAINER"
    ) == "1"
    if not in_container:
        raise SystemExit(
            "Этот скрипт должен запускаться только внутри контейнера. "
            "Сначала выполните ./env_run.sh и запускайте его из /root/workspace."
        )
    if not WORKSPACE.is_dir():
        raise SystemExit(
            "Не найден /root/workspace. Проверьте mount workspace в контейнере."
        )


def natural_key(path: Path) -> list[int | str]:
    parts = re.split(r"(\d+)", path.name)
    return [int(part) if part.isdigit() else part for part in parts]


def read_config_values(path: Path) -> dict[str, int]:
    values: dict[str, int] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if key in {"payload_size_bytes", "publish_period_ms", "number_of_samples"}:
            values[key] = int(value)
    missing = {"publish_period_ms", "number_of_samples"} - values.keys()
    if missing:
        missing_keys = ", ".join(sorted(missing))
        raise RuntimeError(f"config {path} does not define: {missing_keys}")
    return values


def benchmark_timeout_s(config_path: Path) -> float:
    values = read_config_values(config_path)
    expected_s = values["publish_period_ms"] * values["number_of_samples"] / 1000.0
    return max(30.0, expected_s * 1.2 + 30.0)


def config_files(config_dir: str) -> list[Path]:
    config_path = WORKSPACE / "configs" / config_dir / "config"
    if not config_path.is_dir():
        raise SystemExit(f"Не найден каталог конфигов: {config_path}")
    files = sorted(config_path.glob("*.yaml"), key=natural_key)
    if not files:
        raise SystemExit(f"В каталоге нет yaml-конфигов: {config_path}")
    return files


def run_checked(
    command: list[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=cwd, env=env, check=True)


def env_with_appended_flags(
    env: dict[str, str],
    key: str,
    flags: Iterable[str],
) -> dict[str, str]:
    next_env = env.copy()
    existing = next_env.get(key, "").strip()
    appended = " ".join(flags)
    next_env[key] = f"{existing} {appended}".strip() if existing else appended
    return next_env


def remove_tree(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)


def env_from_zsh(
    setup_files: Iterable[Path],
    extra: dict[str, str] | None = None,
) -> dict[str, str]:
    source_commands = []
    for setup_file in setup_files:
        if not setup_file.is_file():
            raise SystemExit(f"Не найден setup-файл: {setup_file}")
        source_commands.append(f"source {quote_zsh(setup_file)}")

    command = " && ".join(source_commands + ["env -0"])
    completed = subprocess.run(
        [ZSH, "-lc", command],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    env = os.environ.copy()
    for item in completed.stdout.split(b"\0"):
        if not item:
            continue
        key, _, value = item.partition(b"=")
        env[key.decode()] = value.decode(errors="surrogateescape")
    if extra:
        env.update(extra)
    return env


def quote_zsh(path: Path | str) -> str:
    return "'" + str(path).replace("'", "'\\''") + "'"


def build(spec: BenchmarkSpec, clean: bool) -> dict[str, str]:
    project_dir = spec.project_dir
    if spec.build_kind == "ros":
        assert spec.ros_package is not None
        ros_distro = os.environ.get("ROS_DISTRO", "lyrical")
        ros_setup = Path(f"/opt/ros/{ros_distro}/setup.zsh")
        base_env = env_from_zsh([ros_setup])
        for name in ("build", "install", "log"):
            remove_tree(project_dir / name)
        run_checked(
            [
                "colcon",
                "build",
                "--packages-select",
                spec.ros_package,
                "--cmake-args",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=1",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_COMPILE_WARNING_AS_ERROR=ON",
            ],
            cwd=project_dir,
            env=base_env,
        )
        return env_from_zsh([ros_setup, project_dir / "install" / "setup.zsh"])

    if spec.build_kind == "cargo":
        cargo_env = env_with_appended_flags(os.environ.copy(), "RUSTFLAGS", ["-Dwarnings"])
        if clean:
            run_checked(["cargo", "clean"], cwd=project_dir, env=cargo_env)
        run_checked(["cargo", "build", "--release"], cwd=project_dir, env=cargo_env)
        return cargo_env

    if spec.build_kind == "cmake":
        build_dir = project_dir / spec.cmake_build_dir
        if clean:
            remove_tree(build_dir)
        build_dir.mkdir(parents=True, exist_ok=True)
        run_checked(
            [
                "cmake",
                "-DCMAKE_EXPORT_COMPILE_COMMANDS=1",
                "-DCMAKE_BUILD_TYPE=Release",
                "-DCMAKE_COMPILE_WARNING_AS_ERROR=ON",
                "..",
            ],
            cwd=build_dir,
        )
        run_checked(["make", f"-j{os.cpu_count() or 1}"], cwd=build_dir)
        return os.environ.copy()

    raise SystemExit(f"Неизвестный build_kind: {spec.build_kind}")


def start_process(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
    stdout=None,
    stderr=None,
) -> subprocess.Popen:
    print("+ " + " ".join(command), flush=True)
    return subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=stdout,
        stderr=stderr,
        start_new_session=True,
    )


def start_perf(
    target_pid: int,
    output_file: Path,
    enabled: bool,
) -> subprocess.Popen | None:
    if not enabled:
        return None
    if shutil.which("perf") is None:
        print("warning: perf не найден в контейнере, perf stat пропущен", file=sys.stderr)
        return None

    output_file.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(
        ["perf", "stat", "-p", str(target_pid), "-o", str(output_file)],
        start_new_session=True,
    )
    time.sleep(0.15)
    if process.poll() is not None:
        print(
            f"warning: perf stat завершился сразу для pid {target_pid}; "
            f"проверьте {output_file}",
            file=sys.stderr,
        )
    return process


def stop_perf(processes: Iterable[subprocess.Popen]) -> None:
    for process in processes:
        if process.poll() is None:
            process.send_signal(signal.SIGINT)
    for process in processes:
        wait_or_kill(process, timeout_s=5)


def terminate_processes(processes: Iterable[subprocess.Popen]) -> None:
    processes = list(processes)
    for process in processes:
        terminate_group(process, signal.SIGTERM)
    time.sleep(0.5)
    for process in processes:
        if process.poll() is None:
            terminate_group(process, signal.SIGKILL)
    live = [process for process in processes if process.poll() is None]
    for process in live:
        wait_or_kill(process, timeout_s=2)


def terminate_group(process: subprocess.Popen, sig: signal.Signals) -> None:
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        return


def wait_or_kill(process: subprocess.Popen, timeout_s: float) -> None:
    try:
        process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        terminate_group(process, signal.SIGKILL)
        process.wait(timeout=2)


def wait_success(
    process: subprocess.Popen,
    role: str,
    timeout_s: float | None = None,
) -> None:
    try:
        return_code = process.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired as exc:
        terminate_group(process, signal.SIGKILL)
        process.wait(timeout=2)
        raise RuntimeError(f"{role} did not finish within {timeout_s}s") from exc
    if return_code != 0:
        raise RuntimeError(f"{role} finished with exit code {return_code}")


def kill_patterns(patterns: Iterable[str]) -> None:
    patterns = [pattern for pattern in patterns if pattern]
    for pattern in patterns:
        subprocess.run(["pkill", "-TERM", "-f", pattern], check=False)
    time.sleep(0.2)
    for pattern in patterns:
        subprocess.run(["pkill", "-KILL", "-f", pattern], check=False)


def assert_no_processes(patterns: Iterable[str]) -> None:
    if shutil.which("pgrep") is None:
        return
    leftovers: list[str] = []
    for pattern in {pattern for pattern in patterns if pattern}:
        completed = subprocess.run(
            ["pgrep", "-af", pattern],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        leftovers.extend(line for line in completed.stdout.splitlines() if line)
    if leftovers:
        raise RuntimeError("cleanup left processes: " + "; ".join(leftovers))


def uses_zenoh_unix_socket(spec: BenchmarkSpec) -> bool:
    return bool(spec.extra_args and spec.extra_args[0].startswith("unixsock-stream/"))


def clean_ipc_leftovers(*, remove_zenoh_sockets: bool = True) -> None:
    for root in (Path("/tmp"), Path("/dev/shm")):
        patterns = [
            "iceoryx*",
            "iox2_*",
            "zmq_benchmark_*.ipc",
        ]
        if remove_zenoh_sockets:
            patterns.append("transport-benchmark-zenoh*.sock")
        for pattern in patterns:
            for path in root.glob(pattern):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass


def ensure_zenoh_quic_certs() -> None:
    if (
        ZENOH_QUIC_CA_FILE.is_file()
        and ZENOH_QUIC_CERT_FILE.is_file()
        and ZENOH_QUIC_KEY_FILE.is_file()
    ):
        return
    remove_tree(ZENOH_QUIC_CERT_DIR)
    ZENOH_QUIC_CERT_DIR.mkdir(parents=True, exist_ok=True)
    ZENOH_QUIC_EXT_FILE.write_text(
        "\n".join(
            [
                "basicConstraints=critical,CA:FALSE",
                "keyUsage=critical,digitalSignature,keyEncipherment",
                "extendedKeyUsage=serverAuth",
                "subjectAltName=DNS:localhost,IP:127.0.0.1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    run_checked(
        [
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(ZENOH_QUIC_CA_KEY_FILE),
            "-out",
            str(ZENOH_QUIC_CA_FILE),
            "-days",
            "1",
            "-subj",
            "/CN=transport-benchmark-zenoh-ca",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
        ]
    )
    run_checked(
        [
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            str(ZENOH_QUIC_KEY_FILE),
            "-out",
            str(ZENOH_QUIC_CSR_FILE),
            "-subj",
            "/CN=localhost",
        ]
    )
    run_checked(
        [
            "openssl",
            "x509",
            "-req",
            "-in",
            str(ZENOH_QUIC_CSR_FILE),
            "-CA",
            str(ZENOH_QUIC_CA_FILE),
            "-CAkey",
            str(ZENOH_QUIC_CA_KEY_FILE),
            "-CAcreateserial",
            "-out",
            str(ZENOH_QUIC_CERT_FILE),
            "-days",
            "1",
            "-sha256",
            "-extfile",
            str(ZENOH_QUIC_EXT_FILE),
        ]
    )


def apply_dds_tuning(spec: BenchmarkSpec, env: dict[str, str]) -> None:
    if spec.key == "ros2_fast":
        env["FASTDDS_DEFAULT_PROFILES_FILE"] = str(FAST_DDS_PROFILES_FILE)
        env["RMW_FASTRTPS_USE_QOS_FROM_XML"] = "1"
    elif spec.key == "ros2_fast_loaned":
        env["FASTDDS_DEFAULT_PROFILES_FILE"] = str(FAST_DDS_LOANED_PROFILES_FILE)
        env["RMW_FASTRTPS_USE_QOS_FROM_XML"] = "1"
        env["ROS_DISABLE_LOANED_MESSAGES"] = "0"
    elif spec.key == "ros2_cyclone":
        env["CYCLONEDDS_URI"] = CYCLONE_DDS_URI


def run_benchmark(spec: BenchmarkSpec, args: argparse.Namespace) -> None:
    require_container()
    runner = Runner()
    latency_dir = WORKSPACE / "tmp" / spec.output_dir_name / "latencies"
    perf_dir = WORKSPACE / "tmp" / spec.output_dir_name / "perf_data"
    remove_tree(latency_dir)
    remove_tree(perf_dir)
    latency_dir.mkdir(parents=True, exist_ok=True)
    perf_dir.mkdir(parents=True, exist_ok=True)

    env = build(spec, clean=args.clean)
    env.update(spec.extra_env)
    if spec.rmw:
        env["RMW_IMPLEMENTATION"] = spec.rmw
    if spec.custom_latency_dir:
        env["TRANSPORT_BENCHMARK_LATENCIES_DIR"] = str(latency_dir)
    apply_dds_tuning(spec, env)
    if "zenoh" in spec.key and "quic" in spec.key:
        ensure_zenoh_quic_certs()
        env["ZENOH_QUIC_CA_CERTIFICATE"] = str(ZENOH_QUIC_CA_FILE)

    clean_ipc_leftovers()
    if spec.sidecar:
        log_handle = None
        if spec.sidecar_log:
            log_handle = open(spec.sidecar_log, "w", encoding="utf-8")
        sidecar = start_process(
            spec.sidecar,
            cwd=spec.project_dir,
            env=env,
            stdout=log_handle or subprocess.DEVNULL,
            stderr=subprocess.STDOUT,
        )
        runner.add_sidecar(sidecar)
        time.sleep(spec.sidecar_start_delay_s)
        if sidecar.poll() is not None:
            runner.cleanup_all([*spec.cleanup_patterns, *spec.final_cleanup_patterns])
            raise RuntimeError(
                f"sidecar exited early with code {sidecar.returncode}; "
                f"check {spec.sidecar_log or 'sidecar output'}"
            )

    configs = config_files(args.config)
    print(
        f"{spec.title}: subscribers={args.num_subscribers}, "
        f"config={args.config}, files={len(configs)}",
        flush=True,
    )

    try:
        for benchmark_config in configs:
            name = benchmark_config.stem
            print(f"\n== {name} ==", flush=True)
            (perf_dir / name).mkdir(parents=True, exist_ok=True)
            subscribers: list[subprocess.Popen] = []
            timeout_s = benchmark_timeout_s(benchmark_config)

            for index in range(1, args.num_subscribers + 1):
                command = spec.subscriber + [
                    str(benchmark_config),
                    str(index),
                    *spec.extra_args,
                ]
                if spec.transport_arg:
                    command.append(spec.transport_arg)
                subscriber = runner.add_process(
                    start_process(command, cwd=spec.project_dir, env=env)
                )
                subscribers.append(subscriber)
                time.sleep(spec.publisher_start_delay_s)
                runner.add_perf(
                    start_perf(
                        subscriber.pid,
                        perf_dir / name / f"{index}_subscriber.stat.txt",
                        enabled=not args.no_perf,
                    )
                )

            time.sleep(spec.subscriber_start_delay_s)
            publisher_command = spec.publisher + [str(benchmark_config), *spec.extra_args]
            if spec.transport_arg:
                publisher_command.append(spec.transport_arg)
            publisher = runner.add_process(
                start_process(publisher_command, cwd=spec.project_dir, env=env)
            )
            runner.add_perf(
                start_perf(
                    publisher.pid,
                    perf_dir / name / "publisher.stat.txt",
                    enabled=not args.no_perf,
                )
            )

            failures: list[str] = []
            for index, subscriber in enumerate(subscribers, start=1):
                try:
                    wait_success(
                        subscriber,
                        f"subscriber {index}",
                        timeout_s=timeout_s,
                    )
                except RuntimeError as exc:
                    failures.append(str(exc))
            if spec.publisher_exits:
                try:
                    wait_success(publisher, "publisher", timeout_s=10)
                except RuntimeError as exc:
                    failures.append(str(exc))
            runner.cleanup_run(spec.cleanup_patterns)
            clean_ipc_leftovers(remove_zenoh_sockets=not uses_zenoh_unix_socket(spec))
            assert_no_processes(spec.cleanup_patterns)
            if failures:
                raise RuntimeError("; ".join(failures))
            time.sleep(args.pause_s)
    finally:
        runner.cleanup_all([*spec.cleanup_patterns, *spec.final_cleanup_patterns])
        clean_ipc_leftovers()
        assert_no_processes([*spec.cleanup_patterns, *spec.final_cleanup_patterns])

    print("\nВсе benchmark-запуски завершены.")


def make_parser(description: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--config", default="20hz_10000_samples")
    parser.add_argument("--num-subscribers", type=int, default=1)
    parser.add_argument(
        "--clean",
        action="store_true",
        help="очистить build cache перед сборкой",
    )
    parser.add_argument("--no-perf", action="store_true", help="не запускать perf stat")
    parser.add_argument(
        "--pause-s",
        type=float,
        default=1.0,
        help="пауза между yaml-конфигами",
    )
    return parser


def run(spec: BenchmarkSpec, argv: list[str] | None = None) -> None:
    parser = make_parser(spec.title)
    args = parser.parse_args(argv)
    if args.num_subscribers < 1:
        raise SystemExit("--num-subscribers должен быть >= 1")
    run_benchmark(spec, args)


def run_zmq(kind: str, argv: list[str] | None = None) -> None:
    parser = make_parser(f"ZMQ {kind}")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--with-tcp", action="store_true")
    group.add_argument("--with-ipc", action="store_true")
    args = parser.parse_args(argv)
    transport = "tcp" if args.with_tcp else "ipc"
    executable_prefix = f"zmq_{kind}"
    spec = BenchmarkSpec(
        key=executable_prefix,
        title=f"ZMQ {kind} ({transport})",
        project_dir=WORKSPACE / executable_prefix,
        output_dir_name=f"{executable_prefix}_{transport}",
        build_kind="cmake",
        subscriber=[f"./build/{executable_prefix}_subscriber"],
        publisher=[f"./build/{executable_prefix}_publisher"],
        cleanup_patterns=[executable_prefix],
        transport_arg=transport,
    )
    if args.num_subscribers < 1:
        raise SystemExit("--num-subscribers должен быть >= 1")
    run_benchmark(spec, args)


ROS2_CYCLONE = BenchmarkSpec(
    key="ros2_cyclone",
    title="ROS 2 Cyclone DDS",
    project_dir=WORKSPACE / "ros2_cyclone",
    output_dir_name="ros2_cyclone",
    build_kind="ros",
    ros_package="ros2_cyclone",
    rmw="rmw_cyclonedds_cpp",
    subscriber=["ros2", "run", "ros2_cyclone", "ros2_cyclone_subscriber"],
    publisher=["ros2", "run", "ros2_cyclone", "ros2_cyclone_publisher"],
    cleanup_patterns=["ros2_cyclone"],
    publisher_exits=False,
)

ROS2_FAST = BenchmarkSpec(
    key="ros2_fast",
    title="ROS 2 Fast DDS",
    project_dir=WORKSPACE / "ros2_fast",
    output_dir_name="ros2_fast",
    build_kind="ros",
    ros_package="ros2_fast",
    rmw="rmw_fastrtps_cpp",
    subscriber=["ros2", "run", "ros2_fast", "ros2_fast_subscriber"],
    publisher=["ros2", "run", "ros2_fast", "ros2_fast_publisher"],
    cleanup_patterns=["ros2_fast"],
    publisher_exits=False,
)

ROS2_FAST_LOANED = BenchmarkSpec(
    key="ros2_fast_loaned",
    title="ROS 2 Fast DDS strict loaned messages",
    project_dir=WORKSPACE / "ros2_fast_loaned",
    output_dir_name="ros2_fast_loaned",
    build_kind="ros",
    ros_package="ros2_fast_loaned",
    rmw="rmw_fastrtps_cpp",
    subscriber=["ros2", "run", "ros2_fast_loaned", "ros2_fast_loaned_subscriber"],
    publisher=["ros2", "run", "ros2_fast_loaned", "ros2_fast_loaned_publisher"],
    cleanup_patterns=["ros2_fast_loaned"],
    publisher_exits=False,
)

ROS2_ZENOH = BenchmarkSpec(
    key="ros2_zenoh",
    title="ROS 2 Zenoh RMW",
    project_dir=WORKSPACE / "ros2_fast",
    output_dir_name="ros2_zenoh",
    build_kind="ros",
    ros_package="ros2_fast",
    rmw="rmw_zenoh_cpp",
    custom_latency_dir=True,
    subscriber=["ros2", "run", "ros2_fast", "ros2_fast_subscriber"],
    publisher=["ros2", "run", "ros2_fast", "ros2_fast_publisher"],
    cleanup_patterns=["ros2_fast"],
    final_cleanup_patterns=["rmw_zenohd"],
    sidecar=["ros2", "run", "rmw_zenoh_cpp", "rmw_zenohd"],
    sidecar_start_delay_s=2.0,
    publisher_exits=False,
)

RUST_ICEORYX2 = BenchmarkSpec(
    key="rust_iceoryx2",
    title="Rust iceoryx2 raw",
    project_dir=WORKSPACE / "rust_iceoryx2",
    output_dir_name="rust_iceoryx2",
    build_kind="cargo",
    subscriber=["./target/release/subscriber"],
    publisher=["./target/release/publisher"],
    cleanup_patterns=[],
    subscriber_start_delay_s=2.0,
)

RUST_ICEORYX2_FLATBUFFERS = BenchmarkSpec(
    key="rust_iceoryx2_flatbuffers",
    title="Rust iceoryx2 FlatBuffers",
    project_dir=WORKSPACE / "rust_iceoryx2_flatbuffers",
    output_dir_name="rust_iceoryx2_flatbuffers",
    build_kind="cargo",
    subscriber=["./target/release/subscriber"],
    publisher=["./target/release/publisher"],
    cleanup_patterns=[],
    subscriber_start_delay_s=2.0,
)

ZENOH_SHM_CFG = [
    "--cfg",
    "transport/shared_memory/enabled:true",
    "--cfg",
    'transport/shared_memory/mode:"init"',
    "--cfg",
    "transport/shared_memory/transport_optimization/message_size_threshold:1",
    "--cfg",
    "transport/shared_memory/transport_optimization/pool_size:67108864",
]

ZENOH_QUIC_TLS_CFG = [
    "--cfg",
    'transport/link/protocols:["quic"]',
    "--cfg",
    f'transport/link/tls/listen_private_key:"{ZENOH_QUIC_KEY_FILE}"',
    "--cfg",
    f'transport/link/tls/listen_certificate:"{ZENOH_QUIC_CERT_FILE}"',
    "--cfg",
    "transport/link/tls/verify_name_on_connect:false",
]


def zenoh_router_spec(
    *,
    key: str,
    title: str,
    output_dir_name: str,
    endpoint: str,
    codec: str,
    payload_mode: str = "bytes",
    sidecar_extra: list[str] | None = None,
) -> BenchmarkSpec:
    return BenchmarkSpec(
        key=key,
        title=title,
        project_dir=WORKSPACE / "rust_zenoh",
        output_dir_name=output_dir_name,
        build_kind="cargo",
        subscriber=["./target/release/subscriber"],
        publisher=["./target/release/publisher"],
        cleanup_patterns=["rust_zenoh/target/release"],
        final_cleanup_patterns=["zenohd"],
        subscriber_start_delay_s=1.0,
        sidecar=[
            "zenohd",
            "--no-multicast-scouting",
            "--no-timestamp",
            "-l",
            endpoint,
            *(sidecar_extra or []),
        ],
        sidecar_log=f"/tmp/transport-benchmark-{output_dir_name}.log",
        sidecar_start_delay_s=1.0,
        extra_args=[endpoint, codec, payload_mode, output_dir_name],
    )


RUST_ZENOH = zenoh_router_spec(
    key="rust_zenoh_tcp",
    title="Rust Zenoh raw router TCP",
    output_dir_name="rust_zenoh_router_tcp",
    endpoint="tcp/127.0.0.1:17447",
    codec="raw",
)

RUST_ZENOH_QUIC = zenoh_router_spec(
    key="rust_zenoh_quic",
    title="Rust Zenoh raw router QUIC",
    output_dir_name="rust_zenoh_router_quic",
    endpoint="quic/localhost:17448",
    codec="raw",
    sidecar_extra=ZENOH_QUIC_TLS_CFG,
)

RUST_ZENOH_UNIXSOCK = zenoh_router_spec(
    key="rust_zenoh_unixsock",
    title="Rust Zenoh raw router Unix socket",
    output_dir_name="rust_zenoh_router_unixsock",
    endpoint="unixsock-stream//tmp/transport-benchmark-zenoh-raw.sock",
    codec="raw",
)

RUST_ZENOH_SHM = zenoh_router_spec(
    key="rust_zenoh_shm",
    title="Rust Zenoh raw shared memory over TCP",
    output_dir_name="rust_zenoh_shm_tcp",
    endpoint="tcp/127.0.0.1:17450",
    codec="raw",
    payload_mode="shm",
    sidecar_extra=ZENOH_SHM_CFG,
)

RUST_ZENOH_FLATBUFFERS_TCP = zenoh_router_spec(
    key="rust_zenoh_flatbuffers_tcp",
    title="Rust Zenoh FlatBuffers router TCP",
    output_dir_name="rust_zenoh_flatbuffers_router_tcp",
    endpoint="tcp/127.0.0.1:17451",
    codec="flatbuffers",
)

RUST_ZENOH_FLATBUFFERS_QUIC = zenoh_router_spec(
    key="rust_zenoh_flatbuffers_quic",
    title="Rust Zenoh FlatBuffers router QUIC",
    output_dir_name="rust_zenoh_flatbuffers_router_quic",
    endpoint="quic/localhost:17452",
    codec="flatbuffers",
    sidecar_extra=ZENOH_QUIC_TLS_CFG,
)

RUST_ZENOH_FLATBUFFERS_UNIXSOCK = zenoh_router_spec(
    key="rust_zenoh_flatbuffers_unixsock",
    title="Rust Zenoh FlatBuffers router Unix socket",
    output_dir_name="rust_zenoh_flatbuffers_router_unixsock",
    endpoint="unixsock-stream//tmp/transport-benchmark-zenoh-flatbuffers.sock",
    codec="flatbuffers",
)

RUST_ZENOH_FLATBUFFERS_SHM = zenoh_router_spec(
    key="rust_zenoh_flatbuffers_shm",
    title="Rust Zenoh FlatBuffers shared memory over TCP",
    output_dir_name="rust_zenoh_flatbuffers_shm_tcp",
    endpoint="tcp/127.0.0.1:17454",
    codec="flatbuffers",
    payload_mode="shm",
    sidecar_extra=ZENOH_SHM_CFG,
)
