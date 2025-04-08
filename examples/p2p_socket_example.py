#!/usr/bin/env python3
"""
Advanced example showing how to use the libp2p stream mounting functionality
to forward a socket server between peers.

This example demonstrates:
1. Creating a P2P listener on one IPFS node
2. Creating a P2P forwarding connection from another node
3. Communicating between the two endpoints via TCP

To run this example:
1. Open two terminals
2. In the first terminal, run: python3 p2p_socket_example.py --server
3. In the second terminal, run: python3 p2p_socket_example.py --client <peer-id>
   (use the peer ID shown from the first terminal)

The example will start a simple echo server on the first node and
establish a connection to it from the second node.
"""

import sys
import os
import socket
import threading
import time
import argparse
from pathlib import Path

# Add the parent directory to the path so we can import the module
sys.path.append(str(Path(__file__).parent.parent))
from src.kubo_python import IpfsNode

def echo_server(port=8765):
    """Simple echo server that listens on the given port."""
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_socket.bind(('127.0.0.1', port))
    server_socket.listen(5)
    print(f"Echo server listening on port {port}")

    try:
        while True:
            client, address = server_socket.accept()
            print(f"Connection from {address}")
            
            # Handle client in a new thread
            client_thread = threading.Thread(
                target=handle_client, 
                args=(client, address),
                daemon=True
            )
            client_thread.start()
    except KeyboardInterrupt:
        print("Server shutting down")
    except Exception as e:
        print(f"Error accepting connection: {e}")
    finally:
        server_socket.close()


def handle_client(client_socket, address):
    """Handle a client connection by echoing all data back."""
    try:
        while True:
            data = client_socket.recv(1024)
            if not data:
                break
                
            print(f"Received: {data.decode('utf-8').strip()}")
            client_socket.send(data)
    except Exception as e:
        print(f"Error handling client {address}: {e}")
    finally:
        client_socket.close()
        print(f"Closed connection from {address}")


def run_client(port=8765):
    """Simple client that sends messages to the echo server."""
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    try:
        client_socket.connect(('127.0.0.1', port))
        
        for i in range(5):
            message = f"Hello, world! ({i+1})"
            print(f"Sending: {message}")
            client_socket.send(message.encode('utf-8'))
            
            response = client_socket.recv(1024)
            print(f"Received: {response.decode('utf-8')}")
            
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("Client shutting down")
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        client_socket.close()


def run_server():
    """Run an IPFS node that listens for node connections and forwards them to the echo server."""
    # Create a temporary IPFS node
    node = IpfsNode.ephemeral(online=True, enable_pubsub=True)
    
    # Print the peer ID
    peer_id = node.peer_id
    print(f"Server node peer ID: {peer_id}")
    print("Use this peer ID when connecting from another node:")
    print(f"python p2p_socket_example.py --client {peer_id}")
    
    # Define the protocol and port
    protocol = "echo-protocol"
    port = 8765
    
    # Start the echo server in a separate thread
    server_thread = threading.Thread(target=echo_server, args=(port,), daemon=True)
    server_thread.start()
    
    # Create a node listener
    success = node.open_listener(protocol, f"/ip4/127.0.0.1/tcp/{port}")
    if success:
        print(f"P2P listener created for protocol '{protocol}' -> /ip4/127.0.0.1/tcp/{port}")
    else:
        print(f"Failed to create P2P listener")
        node.close()
        return
    
    try:
        print("Press Ctrl+C to exit...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
    finally:
        # Clean up
        node.close_streams(protocol)
        node.close()


def run_client_node(server_peer_id):
    """
    Run an IPFS node that connects to another node's node service.
    
    Args:
        server_peer_id: The peer ID of the node running the listener.
    """
    # Create a temporary IPFS node
    node = IpfsNode.ephemeral(online=True, enable_pubsub=True)
    
    # Print our peer ID
    our_peer_id = node.peer_id
    print(f"Client node peer ID: {our_peer_id}")
    
    # Connect to the peer (not always necessary, but can help establish connection)
    target_multiaddr = f"/node/{server_peer_id}"
    print(f"Connecting to peer: {target_multiaddr}")
    try:
        node.connect_to_peer(target_multiaddr)
        print("Connected to peer")
    except Exception as e:
        print(f"Warning: Could not directly connect to peer: {e}")
        print("Will try to establish P2P forwarding anyway...")
    
    # Define the protocol and local port
    protocol = "echo-protocol"
    local_port = 9876
    
    # Create a node forwarding connection
    success = node.open_sender(protocol, f"/ip4/127.0.0.1/tcp/{local_port}", server_peer_id)
    if success:
        print(f"P2P forwarding created: /ip4/127.0.0.1/tcp/{local_port} -> {server_peer_id} via {protocol}")
    else:
        print(f"Failed to create P2P forwarding")
        node.close()
        return
    
    try:
        # Run the client to interact with the forwarded service
        print(f"Connecting to forwarded service on /ip4/127.0.0.1/tcp/{local_port}")
        run_client(local_port)
        
        # Ask if the user wants to keep the connection open
        response = input("Keep connection open? [y/N]: ").lower()
        if response == 'y':
            print("Keeping connection open. Press Ctrl+C to exit...")
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("Client interrupted")
    finally:
        # Clean up
        print("Closing P2P connection...")
        node.close(protocol)
        node.close()


def main():
    """Parse arguments and run either the server or client."""
    parser = argparse.ArgumentParser(description="IPFS P2P Socket Example")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--server", action="store_true", help="Run as a server")
    group.add_argument("--client", metavar="PEER_ID", help="Run as a client, connecting to the specified peer")
    
    args = parser.parse_args()
    
    if args.server:
        run_server()
    else:
        run_client_node(args.client)


if __name__ == "__main__":
    main()