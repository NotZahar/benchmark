#!/usr/bin/env zsh

set -euo pipefail

DRY_RUN=0

warn() {
	print -u2 -- "warning: $*"
}

usage() {
	print -- "Usage: ./setup-host.sh [--dry-run]"
	print -- ""
	print -- "Applies host settings for lower-noise benchmark runs."
	print -- "--dry-run  print actions and validate available sysctl keys without changes"
}

require_command() {
	if ! command -v "$1" >/dev/null 2>&1; then
		print -u2 -- "error: required command not found: $1"
		exit 1
	fi
}

run_sudo() {
	if (( DRY_RUN )); then
		print -- "+ sudo $*"
	else
		sudo "$@"
	fi
}

run_sudo_quiet() {
	if (( DRY_RUN )); then
		print -- "+ sudo $*"
	else
		sudo "$@" >/dev/null
	fi
}

set_sysctl() {
	local key="$1"
	local value="$2"

	if ! sysctl -n "$key" >/dev/null 2>&1; then
		warn "sysctl key is not available: $key"
		return
	fi
	run_sudo_quiet sysctl -w "${key}=${value}"
}

for arg in "$@"; do
	case "$arg" in
		--dry-run)
			DRY_RUN=1
			;;
		-h|--help)
			usage
			exit 0
			;;
		*)
			print -u2 -- "error: unknown argument: $arg"
			usage >&2
			exit 2
			;;
	esac
done

if (( ! DRY_RUN )); then
	require_command sudo
	sudo -v
fi

if command -v cpupower >/dev/null 2>&1; then
	run_sudo cpupower frequency-set --governor performance
else
	warn "cpupower is not installed; CPU governor was not changed"
	warn "on Ubuntu install linux-tools-common and linux-tools-\$(uname -r)"
fi

if [[ -e /sys/devices/system/cpu/smt/control ]]; then
	if (( DRY_RUN )); then
		print -- "+ print -- off | sudo tee /sys/devices/system/cpu/smt/control >/dev/null"
	else
		print -- off | sudo tee /sys/devices/system/cpu/smt/control >/dev/null || \
			warn "failed to disable SMT"
	fi
else
	warn "SMT control is not available on this host"
fi

set_sysctl kernel.randomize_va_space 0
set_sysctl kernel.sched_rt_runtime_us -1
set_sysctl kernel.perf_event_paranoid -1
set_sysctl kernel.kptr_restrict 0

if (( DRY_RUN )); then
	print -- "Dry run finished."
else
	print -- "Host benchmark settings applied."
fi
print -- "Validate perf with: perf stat -- sleep 0.1"
