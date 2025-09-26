#!/bin/bash

set -euo pipefail # Exit if any command fails

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# Navigate to project root, then to libkubo source
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LIBKUBO_DIR="$PROJECT_ROOT/src/libkubo"
cd "$LIBKUBO_DIR"

# Assert Go version
REQUIRED_GO_VERSION="1.19"
INSTALLED_GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')

# Compare versions using sort -V (version-aware)
if [ "$INSTALLED_GO_VERSION" != "$REQUIRED_GO_VERSION" ]; then
  echo "Error: Go $REQUIRED_GO_VERSION is required. Installed: $INSTALLED_GO_VERSION"
  exit 1
fi

rm -f ./libkubo_linux_*.so ./libkubo_linux_*.h

go mod tidy

echo "Building libkubo for Linux x86_64..."
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -v -buildmode=c-shared -o ./libkubo_linux_x86_64.so .

echo "Building libkubo for Linux arm64..."
CC=aarch64-linux-gnu-gcc CGO_ENABLED=1 GOOS=linux GOARCH=arm64 go build -v -buildmode=c-shared -o ./libkubo_linux_arm64.so .

echo "Builds completed"
ls -la ./libkubo_linux_*.so
