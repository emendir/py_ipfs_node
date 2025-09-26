from setuptools import setup, find_packages, Extension, Distribution
import subprocess
import os
import platform
import sys
import glob
from setuptools.command.build_py import build_py
from setuptools.command.install import install
from setuptools.command.develop import develop

try:
    from wheel.bdist_wheel import bdist_wheel
except ImportError:
    bdist_wheel = None

PROJ_DIR = os.path.dirname(os.path.abspath(__file__))


class BinaryDistribution(Distribution):
    """Custom Distribution class to mark package as containing platform-specific binaries."""
    def has_ext_modules(self):
        return True


def is_android() -> bool:
    """Check if OS is android."""
    if "ANDROID_ROOT" in os.environ and "ANDROID_DATA" in os.environ:
        return True
    return (
        "android" in platform.release().lower()
        or "android" in platform.version().lower()
    )


def get_libraries_for_platform(target_platform):
    """Get library files for a specific target platform tag."""
    # Platform tag to library file mapping
    platform_mapping = {
        "manylinux_2_17_x86_64": ["libkubo_linux_x86_64.so", "libkubo_linux_x86_64.h"],
        "manylinux_2_17_aarch64": [
            "libkubo_linux_arm64.so",
            "libkubo_linux_arm64.h",
        ],
        "manylinux_2_17_armv7l": ["libkubo_linux_armhf.so", "libkubo_linux_armhf.h"],
        "win_amd64": [
            "libkubo_windows_x86_64.dll",
            "libkubo_windows_x86_64.h",
            "libkubo_linux_x86_64.h",
        ],
        "macosx_10_9_x86_64": ["libkubo.dylib", "libkubo.h"],
        "android_28_arm64_v8a": [
            "libkubo_android_28_arm64_v8a.so",
            "libkubo_android_28_arm64_v8a.h",
        ],
    }

    platform_files = platform_mapping.get(target_platform, [])

    # Filter to only include files that actually exist
    libkubo_dir = os.path.join(PROJ_DIR, "src", "libkubo")
    existing_files = []
    for filename in platform_files:
        filepath = os.path.join(libkubo_dir, filename)
        if os.path.exists(filepath):
            existing_files.append(filename)

    return existing_files


def get_platform_libraries():
    """Get platform-specific library files to include in the wheel."""
    # Check if target platform is overridden via environment variable
    target_platform = os.environ.get("TARGET_PLATFORM")
    if target_platform:
        return get_libraries_for_platform(target_platform)

    system = platform.system()
    machine = platform.machine().lower()

    libkubo_dir = os.path.join(PROJ_DIR, "src", "libkubo")
    platform_files = []

    if system == "Windows":
        if machine in ("x86_64", "amd64"):
            platform_files.extend(
                [
                    "libkubo_windows_x86_64.dll",
                    "libkubo_windows_x86_64.h",
                    "libkubo_linux_x86_64.h",  # Used as fallback header
                ]
            )
        else:
            raise RuntimeError(f"Unsupported Windows architecture: {machine}")

    elif system == "Darwin":
        platform_files.extend(["libkubo.dylib", "libkubo.h"])

    elif system == "Linux":
        if is_android():
            if machine in ("aarch64", "arm64"):
                platform_files.extend(
                    ["libkubo_android_28_arm64_v8a.so", "libkubo_android_28_arm64_v8a.h"]
                )
            else:
                raise RuntimeError(f"Unsupported Android arch: {machine}")
        else:
            if machine in ("x86_64", "amd64"):
                platform_files.extend(
                    ["libkubo_linux_x86_64.so", "libkubo_linux_x86_64.h"]
                )
            elif machine in ("aarch64", "arm64"):
                platform_files.extend(
                    [
                        "libkubo_linux_arm64.so",
                        "libkubo_linux_arm64.h",
                    ]
                )
            elif machine.startswith("armv7") or machine == "armv7l":
                platform_files.extend(
                    ["libkubo_linux_armhf.so", "libkubo_linux_armhf.h"]
                )
            else:
                raise RuntimeError(f"Unsupported Linux architecture: {machine}")
    else:
        raise RuntimeError(f"Unsupported platform: {system} {machine}")

    # Filter to only include files that actually exist
    existing_files = []
    for filename in platform_files:
        filepath = os.path.join(libkubo_dir, filename)
        if os.path.exists(filepath):
            existing_files.append(filename)

    return existing_files


def compile_go_library():
    """Compile the Go shared library."""
    # Skip compilation if SKIP_GO_BUILD environment variable is set
    if os.environ.get("SKIP_GO_BUILD"):
        print("Skipping Go compilation (SKIP_GO_BUILD is set)")
        return

    print("Compiling Go shared library...")

    # Define Go source directory
    libkubo_dir = os.path.join(PROJ_DIR, "src", "libkubo")

    # Check if Go is installed
    try:
        subprocess.check_call(
            ["go", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        print(
            "Go compiler not found. Skipping Go compilation (assuming pre-compiled libraries exist)"
        )
        return

    # Build shared library for the current platform
    if not os.path.exists(libkubo_dir):
        os.makedirs(libkubo_dir)

    # Determine the output file extension based on platform
    if platform.system() == "Windows":
        lib_name = "libkubo.dll"
    elif platform.system() == "Darwin":
        lib_name = "libkubo.dylib"
    else:
        lib_name = "libkubo_linux_x86_64.so"

    # Get Kubo library source code if not already fetched
    try:
        if not os.path.exists(os.path.join(libkubo_dir, "go.sum")):
            subprocess.check_call(["go", "mod", "tidy"], cwd=libkubo_dir)
    except subprocess.CalledProcessError as e:
        print(f"Error fetching Go dependencies: {e}")
        print("Continuing with existing code...")

    # Check if the output library already exists
    output_path = os.path.join(libkubo_dir, lib_name)
    if os.path.exists(output_path):
        print(f"Shared library already exists at {output_path}")
        return
    print("Compiling libkubo...")
    # Build the shared library
    build_cmd = ["go", "build", "-buildmode=c-shared", "-o", output_path, libkubo_dir]

    print(f"Running: {' '.join(build_cmd)}")
    try:
        subprocess.check_call(build_cmd, cwd=libkubo_dir)
        print(f"Successfully compiled shared library: {output_path}")
    except subprocess.CalledProcessError as e:
        print(f"Go compilation failed: {e}")
        print("Assuming pre-compiled libraries will be used instead")


class BuildGoLibraryCommand(build_py):
    """Custom build command to compile Go code during build_py."""

    def run(self):
        compile_go_library()
        super().run()


class InstallCommand(install):
    """Custom install command to compile Go code during installation."""

    def run(self):
        compile_go_library()
        super().run()


class DevelopCommand(develop):
    """Custom develop command to compile Go code during development installation."""

    def run(self):
        compile_go_library()
        super().run()


if bdist_wheel:
    class CustomBdistWheel(bdist_wheel):
        """Custom bdist_wheel command to set python and abi tags."""

        def get_tag(self):
            """Override wheel tags to use py3-none-{platform}."""
            # Get the original tags
            python, abi, plat = super().get_tag()

            # Override python and abi tags
            return "py3", "none", plat
else:
    CustomBdistWheel = None


# Install requirements during setup (only in development mode)
if "--develop" in sys.argv or "develop" in sys.argv:
    try:
        subprocess.check_call(
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "-r",
                os.path.join(PROJ_DIR, "requirements.txt"),
            ]
        )
    except subprocess.CalledProcessError:
        print("Warning: Failed to install requirements.txt dependencies")

# Get platform-specific library files
platform_libraries = get_platform_libraries()
print(f"Including platform-specific libraries: {platform_libraries}")

setup(
    distclass=BinaryDistribution,
    packages=find_packages(where="src", include=["ipfs_node*", "libkubo*"]),
    package_dir={"": "src"},
    package_data={
        "libkubo": platform_libraries,
    },
    include_package_data=True,
    zip_safe=False,
    cmdclass={
        "build_py": BuildGoLibraryCommand,
        "install": InstallCommand,
        "develop": DevelopCommand,
        **({} if CustomBdistWheel is None else {"bdist_wheel": CustomBdistWheel}),
    },
)
