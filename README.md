# Kubo Python Library

A Python wrapper for the Kubo (Go-IPFS) library.

## Overview

This library provides Python bindings for [Kubo](https://github.com/ipfs/kubo), the Go implementation of IPFS, allowing you to:

- Spawn an in-process IPFS node
- Add and retrieve files/directories from IPFS
- Connect to the IPFS network
- Manage IPFS repositories

## Installation

```bash
pip install kubo-python
```

## Requirements

- Go 1.19+
- Python 3.7+
- IPFS Kubo dependencies

## Basic Usage

```python
from kubo_python import IPFSNode

# Create a new node with a temporary repository
with IPFSNode.ephemeral() as node:
    # Add a file to IPFS
    cid = node.add_file("/path/to/file.txt")
    print(f"Added file with CID: {cid}")
    
    # Retrieve a file from IPFS
    node.get_file(cid, "/path/to/destination.txt")
```

## License

MIT License