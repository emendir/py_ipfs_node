#!/usr/bin/env python3
"""
Basic usage example for the Kubo Python library.

This example demonstrates how to:
1. Create an ephemeral IPFS node
2. Add a file to IPFS
3. Add a string to IPFS
4. Retrieve data from IPFS
"""

import os
import sys
import tempfile

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python import IpfsNode

def main():
    # Create a temporary file for the example
    with tempfile.NamedTemporaryFile(mode='w', delete=False) as temp_file:
        temp_file.write("Hello, IPFS!")
        temp_file_path = temp_file.name
    
    try:
        # Create an ephemeral IPFS node
        print("Creating ephemeral IPFS node...")
        with IpfsNode.ephemeral() as node:
            print("Created IPFS node with ID:", node.peer_id)
            print("Created IPFS node with Multiaddress:", node.get_addrs())
            
            # Add a file to IPFS
            print(f"Adding file: {temp_file_path}")
            file_cid = node.files.publish(temp_file_path)
            print(f"File added with CID: {file_cid}")
            
            # Add a string to IPFS
            content = "Hello, IPFS from Python!"
            
            # Retrieve the file content
            retrieved_content = node.files.read(file_cid)
            print(f"Retrieved content from file: {retrieved_content}")
            
            
            # Try to connect to a public IPFS node
            try:
                print("Connecting to public IPFS node...")
                # ipfs.io multiaddress
                peer_addr = "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN"
                success = node.peers.connect(peer_addr)
                print(f"Connection {'successful' if success else 'failed'}")
            except Exception as e:
                print(f"Error connecting to peer: {e}")
            
            print("IPFS node operations completed successfully!")
    
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    main()