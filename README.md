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

## Project Status

This library is very early in its development, and is published as a proof-of-concept that it is feasible to write a python wrapper around kubo (Go-IPFS) to run IPFS nodes from within python.
Much of the code is LLM-generated, and code coverage is poor.

The API structure of this library WILL CHANGE in the near future!

So far this library has been tested on Linux x86 64-bit and Android ARM 64-bit (in Termux & in Kivy).
Assuming that it proves to be a reliable way of working in python, this library will be developed to maturity and maintained.

## Installation

```bash
pip install kubo_python
```

## Dev Requirements

- Go 1.19+
- Python 3.7+
- IPFS Kubo dependencies

## Basic Usage

### Working with Files

```python
from kubo_python import IpfsNode

# Create a new node with a temporary repository
with IpfsNode.ephemeral() as node:
    # Add a file to IPFS
    cid = node.files.add_file("README.md")
    print(f"Added file with CID: {cid}")

    # Retrieve a file from IPFS
    node.files.download(cid, "/path/to/destination.txt")
```

### Using PubSub

```python
from kubo_python import IpfsNode

with IpfsNode.ephemeral() as node:
    # Subscribe to a topic
    with node.pubsub.subscribe("my-topic") as subscription:
        # Publish a message
        node.pubsub.publish("my-topic", "Hello, IPFS world!")

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
from kubo_python import IpfsNode

# Create an IPFS node
with IpfsNode.ephemeral() as node:

    # Example 1: Listen for connections on a protocol and forward them to a local service
    node.tcp.open_listener("my-service", "127.0.0.1:8080")

    # Example 2: Forward local connections to a remote peer
    node.tcp.open_sender("their-service", "127.0.0.1:9090", "QmPeerID...")

    # List active listeners and streams
    listeners, streams = node.tcp.list_listeners()

    # Close specific connections when done
    node.tcp.close_listener("my-service")
    node.tcp.close_sender("their-service")
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
