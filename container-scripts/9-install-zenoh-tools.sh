#!/usr/bin/env zsh

set -euo pipefail

source "$HOME/.cargo/env"

ZENOH_VERSION="${ZENOH_VERSION:-1.9.0}"
cargo install zenohd --version "$ZENOH_VERSION" --locked --features shared-memory
