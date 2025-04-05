# Kubo Python Library

A Python wrapper for the Kubo (Go-IPFS) library.

## Overview

This library provides Python bindings for [Kubo](https://github.com/ipfs/kubo), the Go implementation of IPFS, allowing you to:

- Spawn an in-process IPFS node
- Add and retrieve files/directories from IPFS
- Connect to the IPFS network
- Manage IPFS repositories
- Publish and subscribe to IPFS PubSub topics
- Mount and connect to remote TCP services via libp2p

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

### Using P2P Stream Mounting

```python
from kubo_python import IPFSNode, IPFSP2P

# Create an IPFS node
with IPFSNode.ephemeral() as node:
    p2p = IPFSP2P(node)
    
    # Example 1: Listen for connections on a protocol and forward them to a local service
    p2p.listen("my-service", "127.0.0.1:8080")
    
    # Example 2: Forward local connections to a remote peer
    p2p.forward("their-service", "127.0.0.1:9090", "QmPeerID...")
    
    # List active listeners and streams
    listeners, streams = p2p.list_listeners()
    
    # Close specific connections when done
    p2p.close("my-service")
```

## Documentation

- [Installation Instructions](INSTALL.md)
- [PubSub Documentation](docs/pubsub.md)
- [P2P Stream Mounting](docs/p2p.md)

## Examples

- [Basic Usage](examples/basic_usage.py)
- [File Sharing](examples/file_sharing.py)
- [PubSub Example](examples/pubsub_example.py)
- [Chat Application](examples/chat_app.py)
- [P2P Stream Mounting](examples/p2p_example.py)
- [P2P Socket Communication](examples/p2p_socket_example.py)

## License

MIT License