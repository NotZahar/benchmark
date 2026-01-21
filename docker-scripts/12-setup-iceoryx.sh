#!/bin/bash

set -euo pipefail

mkdir -p /root/iceoryx_ws/config
touch /root/iceoryx_ws/config/roudi_config.toml
cat >"/root/iceoryx_ws/config/roudi_config.toml" <<'EOF'
[general]
version = 1
[[segment]]
[[segment.mempool]]
size = 128
count = 10000
[[segment.mempool]]
size = 1024
count = 1000
[[segment.mempool]]
size = 8192
count = 500
[[segment.mempool]]
size = 65536
count = 200
[[segment.mempool]]
size = 524288
count = 50
[[segment.mempool]]
size = 4194328 
count = 10
EOF
