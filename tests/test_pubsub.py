#!/usr/bin/env python3
"""
Simple test for the IPFS PubSub functionality.
"""

import os
import sys
import time
import threading
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python import IPFSNode, IPFSMessage

# Create temporary directories for the test
import tempfile
pub_temp_dir = tempfile.TemporaryDirectory()
sub_temp_dir = tempfile.TemporaryDirectory()
pub_repo_path = pub_temp_dir.name
sub_repo_path = sub_temp_dir.name

messages_received = []
subscription = None

def message_callback(message):
    """Callback for received messages."""
    print(f"Message callback received: {message}")
    messages_received.append(message)

def publisher_thread():
    """Thread for publishing messages."""
    with IPFSNode(pub_repo_path) as node:
        print(f"Publisher node created with ID: {node.peer_id}")
        
        # Connect to the subscriber by multiaddress
        if subscriber_addr:
            print(f"Connecting to subscriber: {subscriber_addr}")
            try:
                success = node.connect_to_peer(subscriber_addr)
                if success:
                    print("Successfully connected to subscriber")
                else:
                    print("Failed to connect to subscriber")
                    
                # Find a peer to connect to
                peers = node.pubsub_peers()
                print(f"Available pubsub peers: {peers}")
            except Exception as e:
                print(f"Error connecting to peer: {e}")
        
        time.sleep(2)  # Wait for subscriber to be ready
        
        # Publish some messages
        for i in range(3):
            message = f"Test message {i}"
            print(f"Publishing: {message}")
            success = node.pubsub_publish("test-topic", message)
            print(f"Publish success: {success}")
            
            # Print topics
            try:
                topics = node.pubsub_topics()
                print(f"Active topics: {topics}")
            except Exception as e:
                print(f"Error getting topics: {e}")
                
            time.sleep(1)

# Global variable to store subscriber information
subscriber_id = ""
subscriber_addr = ""

def subscriber_thread():
    """Thread for subscribing to messages."""
    global subscription, subscriber_id, subscriber_addr
    with IPFSNode(sub_repo_path) as node:
        # Store the subscriber ID
        subscriber_id = node.peer_id
        
        # Get the full address with IP and port
        try:
            # Create a multiaddress - this is normally provided by swarm.addrs but we'll
            # construct a reasonable guess for localhost testing
            subscriber_addr = f"/ip4/127.0.0.1/tcp/4001/p2p/{subscriber_id}"
            print(f"Subscriber address: {subscriber_addr}")
        except Exception as e:
            print(f"Error getting subscriber address: {e}")
        print(f"Subscriber node created with ID: {subscriber_id}")
        
        # Subscribe to the topic
        subscription = node.pubsub_subscribe("test-topic")
        print(f"Subscribed to test-topic")
        subscription.subscribe(message_callback)
        
        # Wait for messages to be received
        timeout = time.time() + 15  # 15 second timeout
        while time.time() < timeout and len(messages_received) < 3:
            time.sleep(0.1)
        
        # Close the subscription
        print(f"Closing subscription, received {len(messages_received)} messages")
        subscription.close()

def main():
    """Main test function."""
    # Create the repository directories
    os.makedirs(pub_repo_path, exist_ok=True)
    os.makedirs(sub_repo_path, exist_ok=True)
    
    print(f"Publisher repo: {pub_repo_path}")
    print(f"Subscriber repo: {sub_repo_path}")
    
    try:
        # Start both threads
        sub_thread = threading.Thread(target=subscriber_thread)
        
        # Start subscriber first
        sub_thread.start()
        
        # Wait for subscriber to initialize
        time.sleep(5)
        
        # Start publisher after subscriber is ready
        pub_thread = threading.Thread(target=publisher_thread)
        pub_thread.start()
        
        # Wait for both threads to complete
        sub_thread.join()
        pub_thread.join()
        
        # Check if messages were received
        print(f"Received {len(messages_received)} messages:")
        for msg in messages_received:
            print(f"  - {msg}")
            
        if len(messages_received) == 3:
            print("Test PASSED!")
        else:
            print("Test FAILED: Not all messages were received")
            
    finally:
        # Clean up
        pub_temp_dir.cleanup()
        sub_temp_dir.cleanup()

if __name__ == "__main__":
    main()