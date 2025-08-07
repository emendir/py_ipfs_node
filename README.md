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

## Project Status **EXPERIMENTAL**

This library is very early in its development, and is published as a proof-of-concept that it is feasible to write a python wrapper around kubo (Go-IPFS) to run IPFS nodes from within python.
Much of the code is LLM-generated, and code coverage is poor.

The API of this library WILL CHANGE in the near future!

So far this library has been tested on Linux x86 64-bit and Android ARM 64-bit (in Termux & in Kivy).
Assuming that it proves to be a reliable way of working in python, this library will be developed to maturity and maintained.

## Roadmap

[py_ipfs_node](https://github.com/emendir/py_ipfs_node), will be incorporated into [ipfs_toolkit](https://github.com/emendir/IPFS-Toolkit-Python) [when py_ipfs_node's API has stabilised](https://github.com/emendir/py_ipfs_node/issues/1).

[ipfs_toolkit](https://github.com/emendir/IPFS-Toolkit-Python) will become a multimodal IPFS library with a unified API for alternative modes of using IPFS:
- running an embedded IPFS node
- interacting with a separate IPFS node via its HTTP RPC

You can check out a prototype version of the combination of these two libraries under the `kubo_python` branch of the IPFS-Toolkit repo:
https://github.com/emendir/IPFS-Toolkit-Python/tree/kubo_python

## Installation

```bash
pip install ipfs_node
```

## Dev Requirements

- Go 1.19
- Python 3.7+
- IPFS Kubo dependencies

## Basic Usage

### Working with Files

```python
from ipfs_node import IpfsNode

# Create a new node with a temporary repository
with IpfsNode.ephemeral() as node:
    # Add a file to IPFS
    cid = node.files.publish("README.md")
    print(f"Added file with CID: {cid}")
    
    # Retrieve a file from IPFS
    node.files.download(cid, "download.md")
```

### Using PubSub

```python
from ipfs_node import IpfsNode

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

### Using TCP Tunnels (LibP2P Stream Mounting)

```python
from ipfs_node import IpfsNode

# Create an IPFS node
with IpfsNode.ephemeral() as node:
    
    # Example 1: Listen for connections on a protocol and forward them to a local service
    node.tunnels.open_listener("my-service", 8888)
    
    # Example 2: Forward local connections to a remote peer
    node.tunnels.open_sender("their-service", 8889, node.peer_id)
    
    # List active listeners and streams
    tunnels = node.tunnels.get_tunnels()
    print(tunnels.listeners)
    print(tunnels.senders)
    
    # Close specific connections when done
    node.tunnels.close_listener("my-service")
    node.tunnels.close_sender("their-service")
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

