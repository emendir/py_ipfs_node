#!/bin/bash

# Build script for ipfs_node

set -e  # Exit on error

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    current     Build wheel for current platform only
    all         Build wheels for all supported platforms
    clean       Clean build artifacts
    test        Run tests after building
    help        Show this help message

Examples:
    $0 current          # Build for current platform
    $0 all             # Build for all platforms
    $0 clean           # Clean build artifacts
    $0 test            # Build current platform and run tests
EOF
}

clean_build() {
    echo "Cleaning build artifacts..."
    rm -rf build/
    rm -rf dist/
    rm -rf *.egg-info/
    rm -rf libkubo_backup/
    echo "Clean complete."
}

build_current() {
    echo "Building wheel for current platform..."
    python build_platform_wheels.py --current-platform
    echo "Build complete. Check dist/ directory for the wheel."
}

build_all() {
    echo "Building wheels for all platforms..."
    python build_platform_wheels.py
    echo "All builds complete. Check dist/ directory for wheels."
}

run_tests() {
    echo "Running tests..."
    if build_current; then
        echo "Running test suite..."
        python -m unittest discover tests
    else
        echo "Build failed, skipping tests."
        exit 1
    fi
}

case "${1:-current}" in
    current)
        build_current
        ;;
    all)
        build_all
        ;;
    clean)
        clean_build
        ;;
    test)
        run_tests
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        echo "Unknown command: $1"
        echo "Use '$0 help' for usage information."
        exit 1
        ;;
esac