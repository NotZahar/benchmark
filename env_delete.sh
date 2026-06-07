#!/usr/bin/env zsh

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-transport-benchmark-image:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-transport-benchmark-container}"
REMOVE_IMAGE=0

usage() {
	print -- "Usage: ./env_delete.sh [--image]"
	print -- ""
	print -- "Removes the benchmark container. Use --image to remove the image too."
}

for arg in "$@"; do
	case "$arg" in
		--image)
			REMOVE_IMAGE=1
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

docker rm -f "$CONTAINER_NAME" >/dev/null 2>&1 || true
if (( REMOVE_IMAGE )); then
	docker rmi "$IMAGE_NAME" >/dev/null 2>&1 || true
fi
