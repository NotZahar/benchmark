#!/bin/bash

set -euo pipefail

echo "Start to install python 3.13 ..."
add-apt-repository ppa:deadsnakes/ppa
apt update
apt install -y python3.13-dev
