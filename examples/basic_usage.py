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
            # Add a file to IPFS
            print(f"Adding file: {temp_file_path}")
            file_cid = node.files.add_file(temp_file_path)
            print(f"File added with CID: {file_cid}")
            
            # Add a string to IPFS
            content = "Hello, IPFS from Python!"
            print(f"Adding string: {content}")
            str_cid = node.files.add_str(content)
            print(f"String added with CID: {str_cid}")
            
            # Retrieve the file content
            retrieved_content = node.files.get_str(file_cid)
            print(f"Retrieved content from file: {retrieved_content}")
            
            # Retrieve the string content
            retrieved_str = node.files.get_str(str_cid)
            print(f"Retrieved string: {retrieved_str}")
            
            # Try to connect to a public IPFS node
            try:
                print("Connecting to public IPFS node...")
                # ipfs.io multiaddress
                peer_addr = "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN"
                success = node.connect_to_peer(peer_addr)
                print(f"Connection {'successful' if success else 'failed'}")
            except Exception as e:
                print(f"Error connecting to peer: {e}")
            
            print("IPFS node operations completed successfully!")
    
    finally:
        # Clean up the temporary file
        os.unlink(temp_file_path)

if __name__ == "__main__":
    main()