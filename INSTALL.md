# Installation Instructions

## Prerequisites

Before installing the Kubo Python library, ensure you have the following prerequisites:

1. **Go**: Version 1.19 is required to compile the Go IPFS bindings.
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
pip install ipfs_node
```

### Option 2: Install from Source

1. Clone the repository:
   ```bash
   git clone https://github.com/emendir/py_ipfs_node.git
   cd ipfs_node
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
   rm -f src/ipfs_node/lib/libkubo* # OPTIONAL: Remove the compiled library
   
   ./compile/compile.sh linux    # Linux
   ./compile/compile.sh android  # Android
   ./compile/compile.sh current  # Current platform
   pip install -e .
   ```



## Verifying Installation

Run the example script to verify your installation:

```bash
python examples/basic_usage.py
```

