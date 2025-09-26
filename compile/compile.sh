#!/bin/bash

set -euo pipefail # Exit if any command fails

# the absolute path of this script's directory
SCRIPT_DIR="$( cd -- "$(dirname "$0")" >/dev/null 2>&1 ; pwd -P )"

# Compilation script for libkubo Go libraries

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

show_help() {
    cat << EOF
Usage: $0 [COMMAND]

Commands:
    linux       Compile for Linux (x86_64 and arm64)
    android     Compile for Android (arm64)
    macos       Compile for macOS (x86_64 and arm64)
    windows     Compile for Windows (x86_64 and arm64)
    all         Compile for all supported platforms
    clean       Clean compiled libraries
    current     Compile for current platform (auto-detect)
    help        Show this help message

Examples:
    $0 linux            # Compile for Linux
    $0 android          # Compile for Android
    $0 all              # Compile for all platforms
    $0 clean            # Clean compiled artifacts
    $0 current          # Compile for current platform
EOF
}

clean_libraries() {
    echo "Cleaning compiled libraries..."
    PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
    LIBKUBO_DIR="$PROJECT_ROOT/src/libkubo"

    cd "$LIBKUBO_DIR"
    rm -f ./*.so ./*.dll ./*.dylib ./*.h
    echo "Clean complete."
}

compile_linux() {
    echo "Compiling for Linux..."
    "$SCRIPT_DIR/linux.sh"
}

compile_android() {
    echo "Compiling for Android..."
    "$SCRIPT_DIR/android.sh"
}

compile_macos() {
    echo "Compiling for macOS..."
    "$SCRIPT_DIR/macos.sh"
}

compile_windows() {
    echo "Compiling for Windows..."
    "$SCRIPT_DIR/windows.sh"
}

# Safe compilation function that doesn't exit on failure
compile_platform_safe() {
    local platform="$1"
    local script_name="$2"

    echo "\n=== Compiling for $platform ==="
    if "$SCRIPT_DIR/$script_name" 2>&1; then
        return 0
    else
        echo "Warning: $platform compilation failed"
        return 1
    fi
}

compile_all() {
    echo "Compiling for all platforms..."

    # Temporarily disable exit on error for compile_all
    set +e

    # Track results
    declare -A results

    # Compile each platform and track results
    platforms=("Linux:linux.sh" "Android:android.sh" "macOS:macos.sh" "Windows:windows.sh")

    for platform_script in "${platforms[@]}"; do
        platform="${platform_script%:*}"
        script="${platform_script#*:}"

        if compile_platform_safe "$platform" "$script"; then
            results["$platform"]="SUCCESS"
        else
            results["$platform"]="FAILED"
        fi
    done

    # Re-enable exit on error
    set -e

    # Print summary report
    echo "\n"
    echo "========================================"
    echo "         COMPILATION SUMMARY"
    echo "========================================"

    local success_count=0
    local total_count=0

    for platform in "Linux" "Android" "macOS" "Windows"; do
        total_count=$((total_count + 1))
        if [[ "${results[$platform]}" == "SUCCESS" ]]; then
            echo -e "${GREEN}✓ $platform: SUCCESS${NC}"
            success_count=$((success_count + 1))
        else
            echo -e "${RED}✗ $platform: FAILED${NC}"
        fi
    done

    echo "========================================"
    if [ $success_count -eq $total_count ]; then
        echo -e "${GREEN}All $total_count platforms compiled successfully!${NC}"
        exit 0
    else
        failed_count=$((total_count - success_count))
        echo -e "${YELLOW}$success_count/$total_count platforms compiled successfully${NC}"
        echo -e "${RED}$failed_count platforms failed${NC}"
        exit 1
    fi
}

compile_current() {
    echo "Auto-detecting current platform..."
    case "$(uname -s)" in
        Linux*)
            compile_linux
            ;;
        Darwin*)
            compile_macos
            ;;
        CYGWIN*|MINGW32*|MSYS*|MINGW*)
            compile_windows
            ;;
        *)
            echo "Warning: Unsupported platform $(uname -s), defaulting to Linux"
            compile_linux
            ;;
    esac
}

case "${1:-help}" in
    linux)
        compile_linux
        ;;
    android)
        compile_android
        ;;
    macos)
        compile_macos
        ;;
    windows)
        compile_windows
        ;;
    all)
        compile_all
        ;;
    clean)
        clean_libraries
        ;;
    current)
        compile_current
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