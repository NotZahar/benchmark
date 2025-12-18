#!/bin/bash

IMAGE_NAME="transport-benchmark-image"
CONTAINER_NAME="transport-benchmark-container"

docker stop "$CONTAINER_NAME"
docker rm "$CONTAINER_NAME"
docker rmi "$IMAGE_NAME"
