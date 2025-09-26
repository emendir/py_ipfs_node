#!/bin/bash
## NOTE: This script should be run on linux. It produces DLL files to be used on windows.

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

rm -f ./libkubo_windows_*.dll ./libkubo_windows_*.h

go mod tidy

echo "Building libkubo for Windows x86_64..."
CC=x86_64-w64-mingw32-gcc CGO_ENABLED=1 GOOS=windows GOARCH=amd64 \
  go build -v -buildmode=c-shared -o ./libkubo_windows_x86_64.dll .

echo "Building libkubo for Windows arm64..."
CC=aarch64-w64-mingw32-gcc CGO_ENABLED=1 GOOS=windows GOARCH=arm64 \
  go build -v -buildmode=c-shared -o ./libkubo_windows_arm64.dll .

echo "Builds completed"
ls -la ./libkubo_windows_*.dll
