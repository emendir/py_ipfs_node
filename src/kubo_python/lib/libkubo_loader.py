from cffi import FFI
import platform
from pathlib import Path
ffi = FFI()


# Determine library name based on platform
if platform.system() == 'Windows':
    lib_name = 'libkubo.dll'
    header_name = 'libkubo.h'
elif platform.system() == 'Darwin':
    lib_name = 'libkubo.dylib'
    header_name = 'libkubo.h'
else:
    if "aarch64" == platform.machine():
        lib_name = "libkubo_android_arm64.so"
        header_name = "libkubo_android_arm64.h"
    else:
        lib_name = 'libkubo_linux_x86_64.so'
        header_name = 'libkubo_linux_x86_64.h'



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


def c_str(data:str|bytes):
    if isinstance(data, str):
        data = data.encode()
    return ffi.new("char[]", data)
def from_c_str(string_ptr):
    return ffi.string(string_ptr).decode('utf-8')
