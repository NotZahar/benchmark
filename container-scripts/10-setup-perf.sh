#!/usr/bin/env zsh

set -euo pipefail

if command -v perf >/dev/null 2>&1; then
	echo "perf is available: $(command -v perf)"
else
	echo "Warning: perf not found. Mount host /usr/bin/perf or install matching linux-tools." >&2
fi
