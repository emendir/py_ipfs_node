#!/usr/bin/env python3
"""
Advanced example demonstrating file sharing with Kubo Python library.

This example shows how to:
1. Create a persistent IPFS node
2. Add multiple files and directories to IPFS
3. Share CIDs for retrieval
4. Connect to the IPFS network and retrieve files
"""

import os
import sys
import argparse
import tempfile
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python import IPFSNode

def add_files(node, path, recursive=True):
    """Add a file or directory to IPFS."""
    path = Path(path)
    if path.is_dir() and recursive:
        print(f"Adding directory: {path}")
        cid = node.add_directory(str(path))
        print(f"Directory added with CID: {cid}")
        return cid
    elif path.is_file():
        print(f"Adding file: {path}")
        cid = node.add_file(str(path))
        print(f"File added with CID: {cid}")
        return cid
    else:
        print(f"Skipping {path} (not a file or directory)")
        return None

def retrieve_file(node, cid, output_path):
    """Retrieve a file from IPFS and save it to the specified path."""
    print(f"Retrieving file with CID: {cid}")
    success = node.get_file(cid, output_path)
    if success:
        print(f"File retrieved successfully to: {output_path}")
    else:
        print(f"Failed to retrieve file with CID: {cid}")
    return success

def main():
    parser = argparse.ArgumentParser(description='IPFS File Sharing Example')
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Add command
    add_parser = subparsers.add_parser('add', help='Add files to IPFS')
    add_parser.add_argument('path', help='Path to file or directory to add')
    add_parser.add_argument('--repo', help='Path to IPFS repository', default=os.path.expanduser('~/.ipfs-kubo-python'))
    add_parser.add_argument('--no-recursive', dest='recursive', action='store_false', help='Do not add directories recursively')
    
    # Get command
    get_parser = subparsers.add_parser('get', help='Get files from IPFS')
    get_parser.add_argument('cid', help='Content Identifier of the file to retrieve')
    get_parser.add_argument('output', help='Output path for retrieved file')
    get_parser.add_argument('--repo', help='Path to IPFS repository', default=os.path.expanduser('~/.ipfs-kubo-python'))
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Ensure repository directory exists
    os.makedirs(args.repo, exist_ok=True)
    
    # Create IPFS node with the specified repository
    with IPFSNode(args.repo) as node:
        if args.command == 'add':
            add_files(node, args.path, args.recursive)
        elif args.command == 'get':
            retrieve_file(node, args.cid, args.output)

if __name__ == "__main__":
    main()