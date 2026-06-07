#!/usr/bin/env zsh

set -euo pipefail

echo "Start to install shfmt ..."
SHFMT_VERSION="v3.12.0"
MAX_RETRIES=3
RETRY_DELAY=2
for i in $(seq 1 $MAX_RETRIES); do
	if curl -fsSL --max-time 30 "https://github.com/mvdan/sh/releases/download/${SHFMT_VERSION}/shfmt_${SHFMT_VERSION}_linux_amd64" -o /usr/local/bin/shfmt; then
		echo "Download successful"
		break
	else
		echo "Download attempt $i failed, retrying in ${RETRY_DELAY}s..."
		sleep $RETRY_DELAY
	fi

	if [ $i -eq $MAX_RETRIES ]; then
		echo "Failed to download shfmt after $MAX_RETRIES attempts"
		exit 1
	fi
done
chmod +x /usr/local/bin/shfmt
