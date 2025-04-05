#!/usr/bin/env python3
"""
Example script showing how to use libp2p-stream-mounting functionality.

This example demonstrates:
1. Setting up an IPFS node
2. Creating a TCP listening connection
3. Creating a TCP forwarding connection to another peer
4. Listing active connections
5. Closing connections
"""

import os
import sys
import time
import argparse
from pathlib import Path

# Add the parent directory to the Python path so we can import the library
sys.path.append(str(Path(__file__).parent.parent))

from kubo_python import IPFSNode

def main():
    parser = argparse.ArgumentParser(description="Demo of libp2p stream mounting")
    
    parser.add_argument("--listen", action="store_true", 
                        help="Create a TCP listening connection (server mode)")
    
    parser.add_argument("--forward", action="store_true", 
                        help="Create a TCP forwarding connection (client mode)")
    
    parser.add_argument("--protocol", type=str, default="demo",
                        help="Protocol name to use (default: 'demo')")
    
    parser.add_argument("--port", type=int, default=8765,
                        help="Port to use (default: 8765)")
    
    parser.add_argument("--peer-id", type=str,
                        help="Peer ID to connect to (required for --forward)")
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.forward and not args.peer_id:
        print("Error: --peer-id is required when using --forward")
        sys.exit(1)
    
    if not args.listen and not args.forward:
        print("Error: You must specify either --listen or --forward")
        parser.print_help()
        sys.exit(1)
    
    # Create an IPFS node with a temporary repo
    print("Starting IPFS node...")
    node = IPFSNode.ephemeral()
    
    try:
        print(f"Node peer ID: {node.peer_id}")
        
        if args.listen:
            # Create a TCP listening connection
            print(f"Creating a TCP listening connection on protocol '{args.protocol}' and port {args.port}")
            result = node.create_tcp_listening_connection(args.protocol, args.port)
            if result:
                print("✓ Listening connection created successfully")
            else:
                print("✗ Failed to create listening connection")
                sys.exit(1)
                
            # List active connections
            connections = node.list_tcp_connections()
            print(f"Active connections: \n{connections}")
            
            # Keep the program running
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
                
        elif args.forward:
            # Create a TCP forwarding connection
            print(f"Creating a TCP forwarding connection to peer {args.peer_id}")
            print(f"Protocol: {args.protocol}, Local port: {args.port}")
            result = node.create_tcp_forwarding_connection(args.protocol, args.port, args.peer_id)
            if result:
                print("✓ Forwarding connection created successfully")
            else:
                print("✗ Failed to create forwarding connection")
                sys.exit(1)
                
            # List active connections
            connections = node.list_tcp_connections()
            print(f"Active connections: \n{connections}")
            
            # Keep the program running
            print("Press Ctrl+C to stop...")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nStopping...")
    
    finally:
        # Clean up
        if args.listen:
            node.close_all_tcp_listening_connections()
        elif args.forward:
            node.close_all_tcp_forwarding_connections()
        
        # Close the IPFS node
        node.close()

if __name__ == "__main__":
    main()