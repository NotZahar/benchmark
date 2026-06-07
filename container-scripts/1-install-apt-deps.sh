#!/usr/bin/env zsh

set -euo pipefail

APT_PACKAGES=(
	"build-essential"
	"ca-certificates"
	"cmake"
	"git"
	"curl"
	"gnupg2"
	"lsb-release"
	"software-properties-common"
	"pkg-config"
	"libssl-dev"
	"libacl1-dev"
	"libyaml-cpp-dev"
	"htop"
	"linux-tools-generic"
	"gdb"
	"libclang-dev"
	"wget"
	"zsh"
	"jq"
	"iproute2"
	"procps"
	"python3-venv"
	"protobuf-compiler"
	"libprotobuf-dev"
	"clangd"
	"clang-format"
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

rm -rf /var/lib/apt/lists/*
