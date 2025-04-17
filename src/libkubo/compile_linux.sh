#!/bin/bash
""":"

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"
cd $SCRIPT_DIR

set -e # Exit if any command fails
set -x # Print commands for debugging

# Clean old files
rm -f ../ipfs_node/libkubo/libkubo_linux_x86_64.so ../ipfs_node/libkubo/libkubo_linux_x86_64.h

echo "Building libkubo for Linux x86_64..."
go mod tidy
go build -v -buildmode=c-shared -o ../ipfs_node/libkubo/libkubo_linux_x86_64.so .

echo "Build completed"
ls -la ../ipfs_node/libkubo/libkubo_linux_x86_64.so

exit 0
"""
import os
import sys

# Python: re-execute the script in Bash
os.execvp("bash", ["bash", __file__] + sys.argv[1:])