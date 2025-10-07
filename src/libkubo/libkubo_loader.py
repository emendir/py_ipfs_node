import os
from cffi import FFI
import platform
from pathlib import Path

ffi = FFI()


def is_android() -> bool:
    """Check if OS is android."""
    if "ANDROID_ROOT" in os.environ and "ANDROID_DATA" in os.environ:
        return True
    return (
        "android" in platform.release().lower()
        or "android" in platform.version().lower()
    )


system = platform.system()
machine = platform.machine().lower()

if system == "Windows":
    if machine in ("x86_64", "amd64"):
        lib_name = "libkubo_windows_x86_64.dll"
        # header_name = "libkubo_windows_x86_64.h"
        # windows header causes problems, so parse linux header instead
        header_name = "libkubo_linux_x86_64.h"
    # elif machine in ("aarch64", "arm64"):
    #     lib_name = "libkubo_windows_arm64.dll"
    #     header_name = "libkubo_windows_arm64.h"
    else:
        raise RuntimeError(f"Unsupported Windows architecture: {machine}")

elif system == "Darwin":
    if machine in ("x86_64", "amd64"):
        lib_name = "libkubo_darwin_x86_64.dylib"
        header_name = "libkubo_darwin_x86_64.h"
    elif machine in ("aarch64", "arm64"):
        lib_name = "libkubo_darwin_arm64.dylib"
        header_name = "libkubo_darwin_arm64.h"
    else:
        raise RuntimeError(f"Unsupported MacOS architecture: {machine}")


elif system == "Linux":
    if is_android():
        if machine in ("aarch64", "arm64"):
            lib_name = "libkubo_android_28_arm64_v8a.so"
            header_name = "libkubo_android_28_arm64_v8a.h"
        else:
            raise RuntimeError(f"Unsupported Android arch: {machine}")
    else:
        if machine in ("x86_64", "amd64"):
            lib_name = "libkubo_linux_x86_64.so"
            header_name = "libkubo_linux_x86_64.h"
        elif machine in ("aarch64", "arm64"):
            lib_name = "libkubo_linux_arm64.so"
            header_name = "libkubo_linux_arm64.h"
        elif machine.startswith("armv7") or machine == "armv7l":
            lib_name = "libkubo_linux_armhf.so"
            header_name = "libkubo_linux_armhf.h"
        else:
            raise RuntimeError(f"Unsupported Linux architecture: {machine}")
else:
    raise RuntimeError(f"Unsupported platform: {system} {machine}")

print(lib_name)
print(header_name)

# Get the absolute path to the library
lib_path = str(Path(__file__).parent / lib_name)
header_path = str(Path(__file__).parent / header_name)

with open(header_path) as file:
    lines = [line.strip() for line in file.readlines()]
func_declarations = [
    line for line in lines if line.startswith("extern ") and line.endswith(";")
]
ffi.cdef("\n".join(func_declarations))
ffi.set_source("libkubo", None)
libkubo = ffi.dlopen(lib_path)


def c_str(data: str | bytes):
    if isinstance(data, str):
        data = data.encode()
    return ffi.new("char[]", data)


def from_c_str(string_ptr):
    return ffi.string(string_ptr).decode("utf-8")


def c_bool(value: bool):
    return ffi.new("bool *", value)[0]
