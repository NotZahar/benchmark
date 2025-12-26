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
		if [[ -z "$(docker images -q $IMAGE_NAME 2>/dev/null)" ]]; then
			echo "Image $IMAGE_NAME not found. Building..."
			COMPOSE_FLAGS="--build --force-recreate"
		else
			echo "Image $IMAGE_NAME found. Starting container..."
			COMPOSE_FLAGS="--force-recreate"
		fi

		KERNEL_VERSION=$(uname -r) docker compose up -d $COMPOSE_FLAGS $SERVICE_NAME
		docker exec -it $CONTAINER_NAME /bin/bash
	fi
fi
