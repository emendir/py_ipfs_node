# Kubo Python Library

A Python wrapper for the Kubo (Go-IPFS) library.

## Overview

This library provides Python bindings for [Kubo](https://github.com/ipfs/kubo), the Go implementation of IPFS, allowing you to:

- Spawn an in-process IPFS node
- Add and retrieve files/directories from IPFS
- Connect to the IPFS network
- Manage IPFS repositories
- Publish and subscribe to IPFS PubSub topics

## Installation

```bash
pip install kubo-python
```

## Requirements

- Go 1.19+
- Python 3.7+
- IPFS Kubo dependencies

## Basic Usage

### Working with Files

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

### Using PubSub

```python
from kubo_python import IPFSNode

with IPFSNode.ephemeral() as node:
    # Subscribe to a topic
    with node.pubsub_subscribe("my-topic") as subscription:
        # Publish a message
        node.pubsub_publish("my-topic", "Hello, IPFS world!")
        
        # Receive messages
        message = subscription.next_message(timeout=2.0)
        if message:
            print(f"Received: {message.data.decode('utf-8')}")
            
        # Or use a callback
        def on_message(msg):
            print(f"Received via callback: {msg.data.decode('utf-8')}")
            
        subscription.subscribe(on_message)
```

## Documentation

- [Installation Instructions](INSTALL.md)
- [PubSub Documentation](docs/pubsub.md)

## Examples

- [Basic Usage](examples/basic_usage.py)
- [File Sharing](examples/file_sharing.py)
- [PubSub Example](examples/pubsub_example.py)
- [Chat Application](examples/chat_app.py)

## License

MIT License