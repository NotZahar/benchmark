#!/usr/bin/env zsh

set -euo pipefail

apt update
apt install -y python3-dev python3-pip python3-venv python3-matplotlib python3-pandas
python3 --version
rm -rf /var/lib/apt/lists/*
