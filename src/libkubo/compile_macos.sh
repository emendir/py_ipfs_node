#!/bin/bash
## NOTE: This script should be run on linux. It produces dylib files to be used on macOS.

set -e
# set -x

# Assert Go version
REQUIRED_GO_VERSION="1.19"
INSTALLED_GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')

# Compare versions using sort -V (version-aware)
if [ "$INSTALLED_GO_VERSION" != "$REQUIRED_GO_VERSION" ]; then
  echo "Error: Go $REQUIRED_GO_VERSION is required. Installed: $INSTALLED_GO_VERSION"
  exit 1
fi

SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd "$SCRIPT_DIR"

rm -f ./libkubo_darwin_*.dylib ./libkubo_darwin_*.h

go mod tidy

echo "Building libkubo for macOS x86_64..."
CC=o64-clang CGO_ENABLED=1 GOOS=darwin GOARCH=amd64 \
  go build -v -buildmode=c-shared -o ./libkubo_darwin_x86_64.dylib .

echo "Building libkubo for macOS arm64..."
CC=oa64-clang CGO_ENABLED=1 GOOS=darwin GOARCH=arm64 \
  go build -v -buildmode=c-shared -o ./libkubo_darwin_arm64.dylib .

echo "Builds completed"
ls -la ./libkubo_darwin_*.dylib