#!/bin/bash

set -euo pipefail

if command -v perf &>/dev/null; then
	echo "Host 'perf' binary is available"
else
	echo "Error: 'perf' not found"
fi
