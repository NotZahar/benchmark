#!/usr/bin/env python3

from __future__ import annotations

import argparse
import shutil
from pathlib import Path


WORKSPACE_CONFIGS = Path("/root/workspace/configs")
DEFAULT_PAYLOAD_SIZES = [256, 1024, 4096, 16384, 65536, 262144, 1048576, 4194304]
DEFAULT_PROFILES = [
    (10, 10000),
    (20, 10),
    (20, 200),
    (20, 1000),
    (20, 2000),
    (20, 10000),
]


def require_container() -> None:
    if not Path("/.dockerenv").exists():
        raise SystemExit(
            "Генератор конфигов запускается только внутри контейнера из /root/workspace."
        )
    if not WORKSPACE_CONFIGS.is_dir():
        raise SystemExit(f"Не найден каталог конфигов: {WORKSPACE_CONFIGS}")


def write_profile(hz: int, samples: int, payload_sizes: list[int], force: bool) -> None:
    period_ms = int(round(1000 / hz))
    if hz <= 0 or 1000 % hz != 0:
        raise SystemExit("hz должен быть положительным делителем 1000, чтобы период был целым ms")

    profile_dir = WORKSPACE_CONFIGS / f"{hz}hz_{samples}_samples"
    config_dir = profile_dir / "config"
    if config_dir.exists() and force:
        shutil.rmtree(config_dir)
    config_dir.mkdir(parents=True, exist_ok=True)

    for payload_size in payload_sizes:
        path = config_dir / f"{payload_size}_bytes_{period_ms}_ms_{samples}_samples.yaml"
        path.write_text(
            "\n".join(
                [
                    f"payload_size_bytes: {payload_size}",
                    f"publish_period_ms: {period_ms}",
                    f"number_of_samples: {samples}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
    print(f"generated {config_dir}")


def parse_payload_sizes(raw: str) -> list[int]:
    values = [int(item) for item in raw.split(",") if item.strip()]
    if not values or any(value <= 0 for value in values):
        raise argparse.ArgumentTypeError("payload sizes must be positive integers")
    return values


if __name__ == "__main__":
    require_container()
    parser = argparse.ArgumentParser()
    parser.add_argument("--hz", type=int)
    parser.add_argument("--samples", type=int)
    parser.add_argument(
        "--payload-sizes",
        type=parse_payload_sizes,
        default=DEFAULT_PAYLOAD_SIZES,
        help="comma-separated bytes list",
    )
    parser.add_argument("--force", action="store_true", help="replace existing generated files")
    parser.add_argument(
        "--defaults",
        action="store_true",
        help="generate the repository default profiles",
    )
    args = parser.parse_args()

    if args.defaults:
        for hz, samples in DEFAULT_PROFILES:
            write_profile(hz, samples, args.payload_sizes, args.force)
    else:
        if args.hz is None or args.samples is None:
            raise SystemExit("Укажите --hz и --samples или используйте --defaults")
        write_profile(args.hz, args.samples, args.payload_sizes, args.force)
