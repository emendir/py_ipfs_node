#!/bin/bash
""":"

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

set -e # Exit if any command fails

export GOOS=android
export GOARCH=arm64
export CGO_ENABLED=1
export NDK_PATH=/home/llearuin/.buildozer/android/platform/android-ndk-r25b
export TOOLCHAIN=$NDK_PATH/toolchains/llvm/prebuilt/linux-x86_64
export CC=$TOOLCHAIN/bin/aarch64-linux-android21-clang

go build -buildmode=c-shared -o ../kubo_python/lib/libkubo_android_arm64.so



exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp("bash", ["bash", __file__] + sys.argv[1:])