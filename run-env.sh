#!/bin/bash

set -eu

SERVICE_NAME="transport-benchmark"
IMAGE_NAME="transport-benchmark-image"
CONTAINER_NAME="transport-benchmark-container"

already_in_container() {
	if [ -f /.dockerenv ]; then
		return 0
	fi

	return 1
}

is_container_running() {
	docker ps --filter "name=$CONTAINER_NAME" --filter "status=running" | grep $CONTAINER_NAME >/dev/null

	return $?
}

if already_in_container; then
	echo "Already in container"
else
	if is_container_running; then
		echo "Attaching to $CONTAINER_NAME"
		docker exec -it $CONTAINER_NAME /bin/bash
	else
		echo "Building a $IMAGE_NAME and attaching to $CONTAINER_NAME"
		KERNEL_VERSION=$(uname -r) docker compose up -d --build --force-recreate $SERVICE_NAME
		docker exec -it $CONTAINER_NAME /bin/bash
	fi
fi
