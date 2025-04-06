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

