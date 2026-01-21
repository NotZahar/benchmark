#!/bin/bash

set -euo pipefail

APT_PACKAGES=(
	"build-essential"
	"cmake"
	"git"
	"curl"
	"gnupg2"
	"lsb-release"
	"software-properties-common"
	"pkg-config"
	"libssl-dev"
	"libacl1-dev"
	"libncurses5-dev"
	"htop"
	"linux-tools-generic"
	"gdb"
	"libclang-dev"
	"wget"
	"python3-venv"
	"protobuf-compiler"
	"libprotobuf-dev"
	"clangd-20"
	"clang-format-20"
	"libncurses-dev"
	"ninja-build"
	"capnproto"
	"libcapnp-dev"
)

apt update
if apt install -y "${APT_PACKAGES[@]}"; then
	echo "All packages installed successfully!"
else
	echo "Error: Some packages failed to install!" >&2
	exit 1
fi
