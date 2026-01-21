#!/bin/bash

set -euo pipefail

echo "Start to install cmake-format ..."
python3 -m venv /tmp
. /tmp/bin/activate
pip install cmake-format
