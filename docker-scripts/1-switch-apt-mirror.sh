#!/bin/bash

set -eu

sed -i 's|http://archive.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources &&
	sed -i 's|http://security.ubuntu.com/ubuntu|http://mirror.yandex.ru/ubuntu|g' /etc/apt/sources.list.d/ubuntu.sources
