#!/usr/bin/env zsh

set -euo pipefail

download_with_retry() {
	local url="$1"
	local output="$2"
	local max_retries=5
	local retry_delay=1
	local timeout=180

	for method in curl wget; do
		if command -v "$method" >/dev/null 2>&1; then
			echo "Trying to download using $method..."

			for i in $(seq 1 "$max_retries"); do
				echo "Attempt $i of $max_retries..."

				case $method in
				curl)
					if curl -fsSL --max-time "$timeout" --connect-timeout 30 \
						--retry 3 --retry-delay 5 \
						"$url" -o "$output" 2>/dev/null; then
						echo "Download successful using curl"
						return 0
					fi
					;;
				wget)
					if wget --timeout="$timeout" --tries=3 --waitretry=5 \
						-q "$url" -O "$output" 2>/dev/null; then
						echo "Download successful using wget"
						return 0
					fi
					;;
				esac

				if [ "$i" -lt "$max_retries" ]; then
					echo "Download failed, retrying in ${retry_delay}s..."
					sleep "$retry_delay"
					retry_delay=$((retry_delay))
				fi
			done
		fi
	done

	echo "Failed to download after all attempts"
	return 1
}

install_rust_stable() {
	echo "Installing Rust stable via official rustup..."

	local official_url="https://static.rust-lang.org/rustup/dist/x86_64-unknown-linux-gnu/rustup-init"

	if download_with_retry "$official_url" /tmp/rustup-init; then
		chmod +x /tmp/rustup-init
		echo "Running Rust installer (stable) from official server..."
		/tmp/rustup-init -y --default-toolchain stable --profile minimal
		return 0
	fi

	echo "Rust installer download failed"
	return 1
}

if install_rust_stable; then
	echo "Rust stable installed successfully"
	source "$HOME/.cargo/env" 2>/dev/null || true
else
	echo "Error: Failed to install Rust"
	exit 1
fi
