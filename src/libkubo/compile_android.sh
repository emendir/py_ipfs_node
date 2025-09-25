#!/bin/bash
""":"

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

set -e # Exit if any command fails
set -x # Print commands for debugging

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
export NDK_PATH=~/.buildozer/android/platform/android-ndk-r28c
export TOOLCHAIN=$NDK_PATH/toolchains/llvm/prebuilt/linux-x86_64
export CC=$TOOLCHAIN/bin/aarch64-linux-android21-clang

if ! [ -e $CC ];then
  echo "The configured CC path doesn't exist:"
  echo "$CC"
  echo "Maybe you upgraded to a newer Android NDK version?"
  exit 1
fi

# Clean old files
rm -f ./libkubo_android_arm64.so ./libkubo_android_arm64.h

echo "Building libkubo for Android arm64..."
go mod tidy
go build -v -buildmode=c-shared -o ./libkubo_android_arm64.so .

echo "Build completed"
ls -la ./libkubo_android_arm64.so

exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp("bash", ["bash", __file__] + sys.argv[1:])
