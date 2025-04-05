#!/bin/bash
""":"

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

set -e # Exit if any command fails
set -x # Print commands for debugging

export GOOS=android
export GOARCH=arm64
export CGO_ENABLED=1
export NDK_PATH=~/.buildozer/android/platform/android-ndk-r25b
export TOOLCHAIN=$NDK_PATH/toolchains/llvm/prebuilt/linux-x86_64
export CC=$TOOLCHAIN/bin/aarch64-linux-android21-clang

# Clean old files
rm -f ../kubo_python/lib/libkubo_android_arm64.so ../kubo_python/lib/libkubo_android_arm64.h

echo "Building libkubo for Android arm64..."
go mod tidy
go build -v -buildmode=c-shared -o ../kubo_python/lib/libkubo_android_arm64.so .

echo "Build completed"
ls -la ../kubo_python/lib/libkubo_android_arm64.so

exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp("bash", ["bash", __file__] + sys.argv[1:])