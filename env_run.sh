#!/usr/bin/env zsh

set -euo pipefail

IMAGE_NAME="${IMAGE_NAME:-transport-benchmark-image:latest}"
CONTAINER_NAME="${CONTAINER_NAME:-transport-benchmark-container}"
CONTAINERFILE="${CONTAINERFILE:-Containerfile}"
WORKSPACE_DIR="${0:A:h}"
IMAGE_FINGERPRINT=""

already_in_container() {
	[[ -f /.dockerenv ]]
}

is_container_running() {
	docker ps --filter "name=^/${CONTAINER_NAME}$" --filter "status=running" --format '{{.Names}}' \
		| grep -Fx "$CONTAINER_NAME" >/dev/null
}

container_exists() {
	docker ps -a --filter "name=^/${CONTAINER_NAME}$" --format '{{.Names}}' \
		| grep -Fx "$CONTAINER_NAME" >/dev/null
}

image_exists() {
	docker image inspect "$IMAGE_NAME" >/dev/null 2>&1
}

compute_image_fingerprint() {
	{
		sha256sum "$WORKSPACE_DIR/$CONTAINERFILE"
		find "$WORKSPACE_DIR/container-scripts" -type f -print0 \
			| sort -z \
			| xargs -0 sha256sum
	} | sha256sum | awk '{print $1}'
}

image_matches_workspace() {
	local actual
	actual="$(docker image inspect \
		--format '{{ index .Config.Labels "transport-benchmark.fingerprint" }}' \
		"$IMAGE_NAME" 2>/dev/null || true)"
	[[ "$actual" == "$IMAGE_FINGERPRINT" ]]
}

build_image() {
	docker build \
		-f "$CONTAINERFILE" \
		--label "transport-benchmark.fingerprint=$IMAGE_FINGERPRINT" \
		-t "$IMAGE_NAME" \
		"$WORKSPACE_DIR"
}

run_container() {
	local -a perf_mount=()
	if [[ -x /usr/bin/perf ]]; then
		perf_mount=(-v /usr/bin/perf:/usr/bin/perf:ro)
	fi

	docker run \
		--detach \
		--name "$CONTAINER_NAME" \
		--ipc host \
		--network host \
		--privileged \
		--cap-add SYS_NICE \
		--cap-add IPC_LOCK \
		--cap-add SYS_PTRACE \
		--ulimit memlock=-1:-1 \
		-e TRANSPORT_BENCHMARK_CONTAINER=1 \
		-v "$WORKSPACE_DIR/workspace:/root/workspace" \
		"${perf_mount[@]}" \
		-it "$IMAGE_NAME"
}

docker_exec() {
	local -a tty_args=()
	if [[ -t 0 && -t 1 ]]; then
		tty_args=(-it)
	fi

	if (( $# > 0 )); then
		docker exec "${tty_args[@]}" -w /root/workspace "$CONTAINER_NAME" "$@"
	else
		docker exec "${tty_args[@]}" -w /root/workspace "$CONTAINER_NAME" /bin/zsh
	fi
}

if already_in_container; then
	echo "Already in container"
	exit 0
fi

IMAGE_FINGERPRINT="$(compute_image_fingerprint)"
image_was_rebuilt=0
if ! image_exists; then
	echo "Image $IMAGE_NAME not found. Building..."
	build_image
	image_was_rebuilt=1
elif ! image_matches_workspace; then
	echo "Image $IMAGE_NAME does not match Containerfile/container-scripts. Rebuilding..."
	build_image
	image_was_rebuilt=1
fi

if (( image_was_rebuilt )) && container_exists; then
	echo "Removing stale $CONTAINER_NAME"
	docker rm -f "$CONTAINER_NAME" >/dev/null
fi

if is_container_running; then
	echo "Attaching to $CONTAINER_NAME"
elif container_exists; then
	echo "Starting existing $CONTAINER_NAME"
	docker start "$CONTAINER_NAME" >/dev/null
else
	echo "Creating $CONTAINER_NAME"
	run_container >/dev/null
fi

docker_exec "$@"
