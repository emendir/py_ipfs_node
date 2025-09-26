# Building Platform-Specific Wheels

This document describes how to build platform-specific wheels for the `ipfs_node` Python package.

## Overview

The `ipfs_node` package includes compiled Go libraries (libkubo) for different platforms. Previously, all compiled libraries were packaged into a single wheel, making it very large (~121MB). Now, the packaging system creates separate wheels for different platforms, each containing only the relevant compiled libraries (~32MB per wheel).

## Quick Start

### Build for Current Platform
```bash
# Using the build script
./packaging/build.sh current

# Or directly with Python
python packaging/build_platform_wheels.py --current-platform
```

### Build for All Platforms
```bash
# Using the build script
./packaging/build.sh all

# Or directly with Python
python packaging/build_platform_wheels.py
```

### Clean Build Artifacts
```bash
./packaging/build.sh clean
```

## How It Works

1. **Platform Detection**: The build system detects the target platform and determines which library files are needed.

2. **File Filtering**: During the build process, only the platform-specific library files are included in the wheel:
   - Linux x86_64: `libkubo_linux_x86_64.so` and `libkubo_linux_x86_64.h`
   - Linux ARM64: `libkubo_linux_arm64.so` and `libkubo_linux_arm64.h`
   - Windows x86_64: `libkubo_windows_x86_64.dll` and related headers
   - Android ARM64: `libkubo_android_arm64.so` and `libkubo_android_arm64.h`
   - etc.

3. **Backup and Restore**: The build system temporarily backs up all library files, filters them for each platform build, then restores the original files.

## Supported Platforms

The build system supports wheels for:

- `manylinux_2_17_x86_64`: Linux 64-bit Intel/AMD (glibc 2.17+)
- `manylinux_2_17_aarch64`: Linux 64-bit ARM (ARM64) **includes both Linux and Android libraries**
- `manylinux_2_17_armv7l`: Linux 32-bit ARM (ARMv7)
- `win_amd64`: Windows 64-bit Intel/AMD
- `macosx_10_9_x86_64`: macOS Intel (requires `libkubo.dylib`)

### Android Support

Android ARM64 applications are supported through the `manylinux_2_17_aarch64` wheel, which contains both:
- `libkubo_linux_arm64.so` - for regular Linux ARM64 systems
- `libkubo_android_arm64.so` - for Android systems (optimized for Android's networking stack)

The `libkubo_loader.py` automatically detects Android at runtime and selects the appropriate library. This approach:
- ✅ Uses PyPI-compatible platform tags
- ✅ Provides Android-optimized libraries for better networking performance
- ✅ Works seamlessly with Buildozer and python-for-android toolchains
- ✅ Maintains compatibility with regular Linux ARM64 systems

## Prerequisites

### For Cross-Platform Building

To build wheels for all platforms, you need:

1. **Pre-compiled Libraries**: All the platform-specific `.so`, `.dll`, `.dylib`, and `.h` files must exist in `src/libkubo/`.

2. **Compilation Scripts**: Use the compilation scripts to generate libraries:
   ```bash
   ./compile/compile.sh linux     # For Linux variants
   ./compile/compile.sh windows   # For Windows
   ./compile/compile.sh android   # For Android
   ./compile/compile.sh macos     # For macOS
   ./compile/compile.sh all       # For all platforms
   ```

## Configuration Files

### pyproject.toml
Contains all package metadata (name, version, dependencies, etc.) following modern Python packaging standards.

### setup.py
Minimal setup configuration focused on:
- Platform-specific file inclusion
- Custom build commands for Go compilation
- Development mode dependency installation

## Wheel Naming Convention

The generated wheels follow the standard Python wheel naming convention:
```
{package_name}-{version}-py3-none-{platform_tag}.whl
```

Examples:
```
ipfs_node-0.1.12rc1-py3-none-manylinux_2_17_x86_64.whl
ipfs_node-0.1.12rc1-py3-none-manylinux_2_17_aarch64.whl
ipfs_node-0.1.12rc1-py3-none-win_amd64.whl
```

## Size Comparison

- **Old approach**: Single wheel ~121MB (all platforms)
- **New approach**:
  - Most platform-specific wheels: ~25-32MB each
  - `linux_aarch64` wheel: ~64MB (includes both Linux and Android libraries)

This represents a 47-75% reduction in wheel size for any given platform.

## Troubleshooting

### Build Failures

If building for specific platforms fails:

1. **Missing Libraries**: Ensure the required `.so`/`.dll`/`.dylib` files exist
2. **Go Compilation Issues**: Use the dedicated compilation scripts instead of letting setup.py compile
3. **Platform Mismatch**: The build system will skip platforms for which libraries don't exist

### Development Installation

For development, use:
```bash
pip install -e .
```

This installs the package in development mode with the current platform's libraries.

## Integration with CI/CD

To build wheels for distribution:

1. Use the existing compilation scripts on each target platform
2. Collect all compiled libraries in one location
3. Run `python packaging/build_platform_wheels.py` to generate all platform-specific wheels
4. Upload each wheel to PyPI as a separate distribution

This allows users to automatically download only the wheel appropriate for their platform.