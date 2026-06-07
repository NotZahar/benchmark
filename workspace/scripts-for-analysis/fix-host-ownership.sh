#!/usr/bin/env zsh

set -euo pipefail

usage() {
	print -- "Usage: ./fix-host-ownership.sh [PATH ...]"
	print -- ""
	print -- "Run on the host, not inside the container."
	print -- "Without PATH arguments, fixes ownership of the repository workspace mount."
}

die() {
	print -u2 -- "error: $*"
	exit 1
}

if [[ -f /.dockerenv ]]; then
	die "run this script on the host, not inside the container"
fi

SCRIPT_DIR="${0:A:h}"
WORKSPACE_DIR="${SCRIPT_DIR:h}"
REPO_DIR="${WORKSPACE_DIR:h}"

for arg in "$@"; do
	case "$arg" in
		-h|--help)
			usage
			exit 0
			;;
	esac
done

if (( EUID != 0 )); then
	if ! command -v sudo >/dev/null 2>&1; then
		die "sudo is required to change files owned by root"
	fi
	if [[ ! -t 0 ]] && ! sudo -n true 2>/dev/null; then
		die "sudo authentication is required; run this script from an interactive host terminal"
	fi
	exec sudo \
		TRANSPORT_BENCHMARK_CHOWN_UID="$(id -u)" \
		TRANSPORT_BENCHMARK_CHOWN_GID="$(id -g)" \
		"$0" "$@"
fi

TARGET_UID="${TRANSPORT_BENCHMARK_CHOWN_UID:-${SUDO_UID:-}}"
TARGET_GID="${TRANSPORT_BENCHMARK_CHOWN_GID:-${SUDO_GID:-}}"

if [[ -z "$TARGET_UID" || -z "$TARGET_GID" ]]; then
	die "run via sudo from the target host user, or set TRANSPORT_BENCHMARK_CHOWN_UID/GID"
fi
if [[ "$TARGET_UID" == "0" || "$TARGET_GID" == "0" ]]; then
	die "refusing to chown benchmark files to root"
fi

targets=("$WORKSPACE_DIR")
if (( $# > 0 )); then
	targets=()
	for arg in "$@"; do
		targets+=("${arg:A}")
	done
fi

for target in "${targets[@]}"; do
	[[ -e "$target" ]] || die "path does not exist: $target"
	[[ "$target" == "$REPO_DIR" || "$target" == "$REPO_DIR"/* ]] || \
		die "path is outside repository: $target"

	print -- "+ chown ${TARGET_UID}:${TARGET_GID} ${target}"
	find "$target" -path "$REPO_DIR/.git" -prune -o \
		-exec chown "${TARGET_UID}:${TARGET_GID}" {} +
done

print -- "Ownership fixed."
