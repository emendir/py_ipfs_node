#!/usr/bin/env python3
"""
IPFS PubSub example for the Kubo Python library.

This example demonstrates how to:
1. Create an IPFS node with pubsub enabled
2. Subscribe to a topic
3. Publish messages to a topic
4. Receive messages with callbacks
"""

import os
import sys
import time
import threading
import argparse
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python import IpfsNode, IPFSMessage

def message_callback(message: IPFSMessage) -> None:
    """Callback function for received messages."""
    print(f"\nReceived message from {message.from_peer}: {message.data.decode('utf-8')}")

def subscriber_mode(repo_path: str, topic: str):
    """Run in subscriber mode."""
    print(f"Starting subscriber for topic: {topic}")
    
    with IpfsNode(repo_path) as node:
        print("IPFS node created")
        print(f"Subscribing to topic: {topic}")
        
        # Subscribe to the topic with a callback
        with node.pubsub.subscribe(topic) as subscription:
            print(f"Subscribed to {topic}")
            subscription.subscribe(message_callback)
            
            print("Waiting for messages. Press Ctrl+C to exit.")
            try:
                # Keep the main thread alive
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nExiting...")

def publisher_mode(repo_path: str, topic: str):
    """Run in publisher mode."""
    print(f"Starting publisher for topic: {topic}")
    
    with IpfsNode(repo_path) as node:
        print("IPFS node created")
        
        try:
            while True:
                # Get user input for the message
                message = input("\nEnter message to publish (or 'exit' to quit): ")
                if message.lower() == 'exit':
                    break
                
                # Publish the message
                success = node.pubsub.publish(topic, message)
                if success:
                    print(f"Message published to {topic}")
                else:
                    print("Failed to publish message")
                    
                # List peers for the topic
                peers = node.pubsub.peers(topic)
                if peers:
                    print(f"Peers for topic {topic}: {', '.join(peers)}")
                else:
                    print(f"No peers found for topic {topic}")
        except KeyboardInterrupt:
            print("\nExiting...")

def main():
    parser = argparse.ArgumentParser(description='IPFS PubSub Example')
    parser.add_argument('--repo', help='Path to IPFS repository', 
                        default=os.path.expanduser('~/.ipfs-kubo-python'))
    parser.add_argument('--topic', help='PubSub topic', default='kubo-python-test')
    parser.add_argument('--mode', choices=['publisher', 'subscriber', 'both'], 
                        default='both', help='Mode to run in')
    
    args = parser.parse_args()
    
    # Ensure repository directory exists
    os.makedirs(args.repo, exist_ok=True)
    
    if args.mode == 'publisher':
        publisher_mode(args.repo, args.topic)
    elif args.mode == 'subscriber':
        subscriber_mode(args.repo, args.topic)
    else:
        # Both mode - run subscriber in a thread, publisher in main thread
        subscriber_thread = threading.Thread(
            target=subscriber_mode,
            args=(args.repo, args.topic),
            daemon=True
        )
        subscriber_thread.start()
        
        # Wait a moment for the subscriber to start
        time.sleep(2)
        
        publisher_mode(args.repo, args.topic)
        
        # Wait for the subscriber thread to exit
        subscriber_thread.join(timeout=1.0)

if __name__ == "__main__":
    main()