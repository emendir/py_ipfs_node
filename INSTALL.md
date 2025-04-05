# Installation Instructions

## Prerequisites

Before installing the Kubo Python library, ensure you have the following prerequisites:

1. **Go**: Version 1.19 or later is required to compile the Go IPFS bindings.
   - Install from [golang.org](https://golang.org/doc/install)
   - Verify with `go version`

2. **Python**: Version 3.7 or later.
   - Verify with `python --version` or `python3 --version`

3. **C Compiler**: Required for building the shared library.
   - Linux: GCC (`sudo apt install build-essential`)
   - macOS: Xcode Command Line Tools (`xcode-select --install`)
   - Windows: MinGW or Visual C++ Build Tools

## Installation

### Option 1: Install from PyPI (Not available yet)

```bash
pip install kubo-python
```

### Option 2: Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/kubo-python.git
   cd kubo-python
   ```

2. Install the package:
   ```bash
   pip install -e .
   ```

   This will:
   - Download the Kubo Go dependencies
   - Compile the shared library
   - Install the Python package in development mode

3. If installation fails because of Go compilation errors, you can manually build the Go library:
   ```bash
   # Ensure CGO is enabled
   export CGO_ENABLED=1
   
   # Navigate to the go_src directory
   cd go_src
   
   # Initialize the Go module and get dependencies
   go mod tidy
   
   # Build the shared library
   mkdir -p ../kubo_python/lib
   go build -buildmode=c-shared -o ../kubo_python/lib/libkubo_linux_x86_64.so .
   
   # Return to the main directory and install the Python package
   cd ..
   pip install -e .
   ```

## Troubleshooting

### Common Issues

1. **Missing Go**: If you get an error about Go not being found, ensure it's installed and in your PATH.

2. **CGO_ENABLED**: The build requires CGO to be enabled. If you're having trouble, try:
   ```bash
   export CGO_ENABLED=1
   pip install -e .
   ```

3. **Library Load Errors**: If you get errors about the shared library not being found:
   - On Linux: Set `LD_LIBRARY_PATH` to include the library directory
     ```bash
     export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$(pwd)/kubo_python/lib
     ```
   - On macOS: Set `DYLD_LIBRARY_PATH` to include the library directory
     ```bash
     export DYLD_LIBRARY_PATH=$DYLD_LIBRARY_PATH:$(pwd)/kubo_python/lib
     ```
   - On Windows: Add the library directory to your PATH

4. **Go Module Errors**: If you encounter errors related to Go modules:
   ```bash
   cd go_src
   go mod tidy
   cd ..
   pip install -e .
   ```

5. **Force Rebuild**: If you need to force a rebuild of the Go library:
   ```bash
   # Remove the compiled library
   rm -f kubo_python/lib/libkubo*
   
   # Reinstall
   pip install -e .
   ```

## Verifying Installation

Run the example script to verify your installation:

```bash
python examples/basic_usage.py
```

If the script runs successfully and connects to the IPFS network, your installation is working correctly.

## Manual Testing

If you're experiencing issues, you can test the Go library compilation directly:

```bash
cd go_src
export CGO_ENABLED=1
go build -buildmode=c-shared -o ../kubo_python/lib/libkubo_linux_x86_64.so .
```

This should produce a shared library in the kubo_python/lib directory. If this step succeeds but the Python package still fails, the issue is likely with the Python wrapper.