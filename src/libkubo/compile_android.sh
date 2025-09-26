#!/bin/bash
""":"

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

set -e # Exit if any command fails
set -x # Print commands for debugging

# Android NDK version constants
ANDROID_API_LEVEL="28"
NDK_VERSION="28c"

# Assert Go version
REQUIRED_GO_VERSION="1.19"
INSTALLED_GO_VERSION=$(go version | awk '{print $3}' | sed 's/go//')

# Compare versions using sort -V (version-aware)
if [ "$INSTALLED_GO_VERSION" != "$REQUIRED_GO_VERSION" ]; then
  echo "Error: Go $REQUIRED_GO_VERSION is required. Installed: $INSTALLED_GO_VERSION"
  exit 1
fi

export GOOS=android
export GOARCH=arm64
export CGO_ENABLED=1
export NDK_PATH=~/.buildozer/android/platform/android-ndk-r${NDK_VERSION}
export TOOLCHAIN=$NDK_PATH/toolchains/llvm/prebuilt/linux-x86_64
export CC=$TOOLCHAIN/bin/aarch64-linux-android21-clang

# Verify NDK version consistency
if ! [ -d "$NDK_PATH" ]; then
  echo "Error: NDK path does not exist: $NDK_PATH"
  echo "Expected NDK version: r${NDK_VERSION}"
  exit 1
fi

if ! [ -e $CC ];then
  echo "The configured CC path doesn't exist:"
  echo "$CC"
  echo "Maybe you upgraded to a newer Android NDK version?"
  exit 1
fi

# Clean old files
rm -f ./libkubo_android_${ANDROID_API_LEVEL}_arm64_v8a.so ./libkubo_android_${ANDROID_API_LEVEL}_arm64_v8a.h

echo "Building libkubo for Android arm64 (API ${ANDROID_API_LEVEL}, NDK r${NDK_VERSION})..."
go mod tidy
go build -v -buildmode=c-shared -o ./libkubo_android_${ANDROID_API_LEVEL}_arm64_v8a.so .

echo "Build completed"
ls -la ./libkubo_android_${ANDROID_API_LEVEL}_arm64_v8a.so

exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp("bash", ["bash", __file__] + sys.argv[1:])
