#!/bin/bash
## NOTE: This script should be run on macOS. It produces dylib files natively.

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

rm -f ./libkubo_darwin_*.dylib ./libkubo_darwin_*.h

go mod tidy

# Detect current architecture
CURRENT_ARCH=$(uname -m)

if [ "$CURRENT_ARCH" = "arm64" ]; then
  echo "Building libkubo for macOS arm64 (native)..."
  CGO_ENABLED=1 GOOS=darwin GOARCH=arm64 go build -v -buildmode=c-shared -o ./libkubo_darwin_arm64.dylib .
  
  echo "Building libkubo for macOS x86_64 (cross-compile)..."
  CGO_ENABLED=1 GOOS=darwin GOARCH=amd64 go build -v -buildmode=c-shared -o ./libkubo_darwin_x86_64.dylib .
else
  echo "Building libkubo for macOS x86_64 (native)..."
  CGO_ENABLED=1 GOOS=darwin GOARCH=amd64 go build -v -buildmode=c-shared -o ./libkubo_darwin_x86_64.dylib .
  
  echo "Building libkubo for macOS arm64 (cross-compile)..."
  CGO_ENABLED=1 GOOS=darwin GOARCH=arm64 go build -v -buildmode=c-shared -o ./libkubo_darwin_arm64.dylib .
fi

echo "Builds completed"
ls -la ./libkubo_darwin_*.dylib
