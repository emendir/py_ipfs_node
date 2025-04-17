#!/usr/bin/env python3
"""
Simple test for the IPFS PubSub functionality using a single IPFS node.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ipfs_node import IpfsNode, IPFSMessage

# Create a temporary directory for the test
import tempfile
temp_dir = tempfile.TemporaryDirectory()
repo_path = temp_dir.name

messages_received = []

def message_callback(message):
    """Callback for received messages."""
    print(f"Message callback received: {message}")
    messages_received.append(message)

def main():
    """Main test function."""
    # Create the repository directory
    os.makedirs(repo_path, exist_ok=True)
    
    print(f"Using repo: {repo_path}")
    
    try:
        # Create a single IPFS node
        with IpfsNode(repo_path) as node:
            print(f"IPFS node created with ID: {node.peer_id}")
            
            # Subscribe to the test topic
            with node.pubsub.subscribe("test-topic") as subscription:
                print(f"Subscribed to test-topic")
                
                # Set up the callback
                subscription.subscribe(message_callback)
                
                # Wait a moment for the subscription to initialize
                time.sleep(1)
                
                # Publish some messages to our topic
                for i in range(3):
                    message = f"Test message {i}"
                    print(f"Publishing: {message}")
                    success = node.pubsub.publish("test-topic", message)
                    print(f"Publish success: {success}")
                    
                    # Wait a moment
                    time.sleep(0.5)
                
                # Wait for messages to be processed (should be near instant with local node)
                time.sleep(1)
                
            # Check if messages were received
            print(f"Received {len(messages_received)} messages:")
            for i, msg in enumerate(messages_received):
                print(f"  {i+1}. {msg}")
                
            if len(messages_received) == 3:
                print("Test PASSED!")
            else:
                print("Test FAILED: Not all messages were received")
                
    finally:
        # Clean up
        temp_dir.cleanup()

if __name__ == "__main__":
    main()