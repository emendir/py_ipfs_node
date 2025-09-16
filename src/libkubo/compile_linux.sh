#!/bin/bash
set -e
set -x

# Assert Go version
REQUIRED_GO_VERSION="1.19"
INSTALLED_GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')

# Compare versions using sort -V (version-aware)
if [ "$(printf '%s\n' "$REQUIRED_GO_VERSION" "$INSTALLED_GO_VERSION" | sort -V | head -n1)" != "$REQUIRED_GO_VERSION" ]; then
  echo "Error: Go $REQUIRED_GO_VERSION or higher is required. Installed: $INSTALLED_GO_VERSION"
  exit 1
fi

SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

rm -f ./libkubo_linux_*.so ./libkubo_linux_*.h

go mod tidy

echo "Building libkubo for Linux x86_64..."
CGO_ENABLED=1 GOOS=linux GOARCH=amd64 go build -v -buildmode=c-shared -o ./libkubo_linux_x86_64.so .

echo "Building libkubo for Linux arm64..."
CC=aarch64-linux-gnu-gcc CGO_ENABLED=1 GOOS=linux GOARCH=arm64 go build -v -buildmode=c-shared -o ./libkubo_linux_arm64.so .

echo "Builds completed"
ls -la ./libkubo_linux_*.so
