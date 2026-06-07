#!/usr/bin/env python3

from benchmark_suite import run_suite


if __name__ == "__main__":
    run_suite(default_config="20hz_10000_samples", default_subscribers=4)
