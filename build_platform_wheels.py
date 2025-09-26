#!/usr/bin/env python3
"""
Script to build platform-specific wheels for ipfs_node.

This script builds separate wheels for different platforms, each containing
only the relevant compiled libraries for that platform.
"""

import os
import subprocess
import sys
import platform
import shutil
from pathlib import Path

PROJ_DIR = Path(__file__).parent
LIBKUBO_DIR = PROJ_DIR / "src" / "libkubo"
DIST_DIR = PROJ_DIR / "dist"

# Platform configurations: (platform_tag, library_files)
PLATFORMS = {
    "manylinux2014_x86_64": [
        "libkubo_linux_x86_64.so",
        "libkubo_linux_x86_64.h"
    ],
    "manylinux2014_aarch64": [
        "libkubo_linux_arm64.so",
        "libkubo_linux_arm64.h",
        "libkubo_android_arm64.so",
        "libkubo_android_arm64.h"
    ],
    "manylinux2014_armv7l": [
        "libkubo_linux_armhf.so",
        "libkubo_linux_armhf.h"
    ],
    "win_amd64": [
        "libkubo_windows_x86_64.dll",
        "libkubo_windows_x86_64.h",
        "libkubo_linux_x86_64.h"  # Fallback header for Windows
    ],
    "macosx_10_9_x86_64": [
        "libkubo.dylib",
        "libkubo.h"
    ],
}


def clean_build_dirs():
    """Clean build directories."""
    for dir_name in ["build", "dist", "*.egg-info"]:
        for path in PROJ_DIR.glob(dir_name):
            if path.is_dir():
                print(f"Cleaning {path}")
                shutil.rmtree(path, ignore_errors=True)


def backup_libkubo_files():
    """Backup all libkubo files."""
    backup_dir = PROJ_DIR / "libkubo_backup"
    if backup_dir.exists():
        shutil.rmtree(backup_dir)

    print(f"Backing up libkubo files to {backup_dir}")
    shutil.copytree(LIBKUBO_DIR, backup_dir)
    return backup_dir


def restore_libkubo_files(backup_dir):
    """Restore libkubo files from backup."""
    print(f"Restoring libkubo files from {backup_dir}")
    if LIBKUBO_DIR.exists():
        shutil.rmtree(LIBKUBO_DIR)
    shutil.copytree(backup_dir, LIBKUBO_DIR)


def filter_libkubo_for_platform(platform_files):
    """Keep only platform-specific files in libkubo directory."""
    # Remove all .so, .dll, .dylib, and .h files
    for pattern in ["*.so", "*.dll", "*.dylib", "*.h"]:
        for file_path in LIBKUBO_DIR.glob(pattern):
            if file_path.name not in platform_files:
                print(f"Removing {file_path.name}")
                file_path.unlink()


def build_wheel_for_platform(platform_tag, platform_files):
    """Build a wheel for a specific platform."""
    print(f"\n=== Building wheel for {platform_tag} ===")

    # Check if all required files exist
    missing_files = []
    for filename in platform_files:
        if not (LIBKUBO_DIR / filename).exists():
            missing_files.append(filename)

    if missing_files:
        print(f"Skipping {platform_tag}: Missing files {missing_files}")
        return False

    # Filter libkubo directory to only contain platform-specific files
    filter_libkubo_for_platform(platform_files)

    # Clean previous builds
    for dir_name in ["build", "*.egg-info"]:
        for path in PROJ_DIR.glob(dir_name):
            if path.is_dir():
                shutil.rmtree(path, ignore_errors=True)

    # Build the wheel
    cmd = [
        sys.executable, "setup.py",
        "bdist_wheel",
        "--plat-name", platform_tag
    ]

    # Set environment to skip Go compilation for cross-platform builds
    env = os.environ.copy()
    env["SKIP_GO_BUILD"] = "1"
    env["TARGET_PLATFORM"] = platform_tag

    print(f"Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(cmd, cwd=PROJ_DIR, check=True, capture_output=True, text=True, env=env)
        print("Build successful!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        print(f"stdout: {e.stdout}")
        print(f"stderr: {e.stderr}")
        return False


def get_current_platform_tag():
    """Get the platform tag for the current platform."""
    system = platform.system()
    machine = platform.machine().lower()

    if system == "Windows":
        if machine in ("x86_64", "amd64"):
            return "win_amd64"
        else:
            raise RuntimeError(f"Unsupported Windows architecture: {machine}")
    elif system == "Darwin":
        return "macosx_10_9_x86_64"
    elif system == "Linux":
        if machine in ("x86_64", "amd64"):
            return "manylinux2014_x86_64"
        elif machine in ("aarch64", "arm64"):
            return "manylinux2014_aarch64"
        elif machine.startswith("armv7") or machine == "armv7l":
            return "manylinux2014_armv7l"
        else:
            raise RuntimeError(f"Unsupported Linux architecture: {machine}")
    else:
        raise RuntimeError(f"Unsupported platform: {system} {machine}")


def build_current_platform_wheel():
    """Build wheel for the current platform using platform-specific filtering."""
    print(f"\n=== Building wheel for current platform ===")

    current_platform = get_current_platform_tag()
    platform_files = PLATFORMS.get(current_platform)

    if not platform_files:
        print(f"No platform configuration for {current_platform}")
        return False

    return build_wheel_for_platform(current_platform, platform_files)


def main():
    """Main function."""
    if len(sys.argv) > 1 and sys.argv[1] == "--current-platform":
        # Build only for current platform
        # Create dist directory
        DIST_DIR.mkdir(exist_ok=True)

        # Clean build directories
        clean_build_dirs()

        # Backup original libkubo files
        backup_dir = backup_libkubo_files()

        try:
            success = build_current_platform_wheel()
            if not success:
                sys.exit(1)
        finally:
            # Restore original files
            restore_libkubo_files(backup_dir)

            # Clean up backup
            shutil.rmtree(backup_dir, ignore_errors=True)

            # Clean build directories
            for dir_name in ["build", "*.egg-info"]:
                for path in PROJ_DIR.glob(dir_name):
                    if path.is_dir():
                        shutil.rmtree(path, ignore_errors=True)

        return

    # Create dist directory
    DIST_DIR.mkdir(exist_ok=True)

    # Clean build directories
    clean_build_dirs()

    # Backup original libkubo files
    backup_dir = backup_libkubo_files()

    successful_builds = []
    failed_builds = []

    try:
        # Build wheels for each platform
        for platform_tag, platform_files in PLATFORMS.items():
            # Restore original files before each build
            restore_libkubo_files(backup_dir)

            success = build_wheel_for_platform(platform_tag, platform_files)
            if success:
                successful_builds.append(platform_tag)
            else:
                failed_builds.append(platform_tag)

    finally:
        # Restore original files
        restore_libkubo_files(backup_dir)

        # Clean up backup
        shutil.rmtree(backup_dir, ignore_errors=True)

        # Clean build directories
        for dir_name in ["build", "*.egg-info"]:
            for path in PROJ_DIR.glob(dir_name):
                if path.is_dir():
                    shutil.rmtree(path, ignore_errors=True)

    print(f"\n=== Build Summary ===")
    print(f"Successful builds: {successful_builds}")
    print(f"Failed builds: {failed_builds}")

    if failed_builds:
        print(f"\nSome builds failed. Check the logs above for details.")
        sys.exit(1)
    else:
        print(f"\nAll builds completed successfully!")


if __name__ == "__main__":
    main()