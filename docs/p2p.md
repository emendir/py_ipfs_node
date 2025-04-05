# P2P Stream Mounting in KuboPythonLib

This document describes how to use the libp2p stream mounting functionality in KuboPythonLib.

## Overview

P2P stream mounting allows you to:

1. Expose local TCP services to the libp2p network (listening)
2. Connect to remote TCP services exposed by other nodes (forwarding)

This is useful for building distributed applications, where services running on one node can be accessed by other nodes over the IPFS/libp2p network, regardless of NATs or firewalls.

## Basic Concepts

- **Protocol:** A name that identifies the service being exposed/connected to
- **Listener:** An IPFS node that exposes a local TCP service to the libp2p network
- **Stream:** A connection between two peers over the libp2p network
- **Forwarding:** The process of connecting to a remote TCP service exposed by another node

## Using the IPFSP2P Class

The `IPFSP2P` class provides an interface to the stream mounting functionality:

```python
from kubo_python import IPFSNode, IPFSP2P

# Create an IPFS node
node = IPFSNode.ephemeral(online=True)

# Create a P2P interface
p2p = IPFSP2P(node)

# Enable P2P functionality (automatically called by the constructor)
p2p.enable()
```

### Exposing a Local Service

To expose a local TCP service to the libp2p network:

```python
# Listen for connections on the given protocol and forward them to a local address
success = p2p.listen("my-protocol", "127.0.0.1:8080")
```

This will make the local service running on `127.0.0.1:8080` available to other IPFS nodes via the protocol `my-protocol`.

### Connecting to a Remote Service

To connect to a remote TCP service exposed by another node:

```python
# Forward local connections to a remote peer
success = p2p.forward("my-protocol", "127.0.0.1:8080", "QmTarget...")
```

This will forward connections from local port `8080` to the service exposed by peer `QmTarget...` with protocol `my-protocol`.

### Listing Active Connections

To list all active P2P connections:

```python
# Get active listeners and streams
listeners, streams = p2p.list_listeners()

# Display listeners
for listener in listeners:
    print(f"Protocol: {listener.protocol}, Target: {listener.target_address}")
    
# Display streams
for stream in streams:
    print(f"Protocol: {stream.protocol}, Origin: {stream.origin_address}, Target: {stream.target_address}")
```

### Closing Connections

To close a specific connection:

```python
# Close a connection by protocol
p2p.close("my-protocol")

# Close a specific forwarding connection
p2p.close("my-protocol", "127.0.0.1:8080", "QmTarget...")
```

## Examples

See the `examples/p2p_example.py` and `examples/p2p_socket_example.py` files for complete examples.

## Use Cases

P2P stream mounting can be used for:

1. Building distributed applications
2. Creating peer-to-peer services
3. Tunneling services through NATs and firewalls
4. Creating secure communication channels between nodes

## Limitations

- Both nodes must have P2P stream mounting enabled
- The protocol names must match on both sides
- The nodes must be able to connect to each other via libp2p