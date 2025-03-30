#!/usr/bin/env python3
"""
IPFS PubSub Chat Application using Kubo Python library.

This example creates a simple chat application where users can:
1. Join different chat rooms (topics)
2. Send messages to everyone in the room
3. Receive messages from other users
4. List available rooms and participants
"""

import os
import sys
import time
import json
import threading
import argparse
import datetime
import random
import string
from pathlib import Path

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python import IPFSNode, IPFSMessage, IPFSSubscription

class ChatApp:
    """A simple chat application using IPFS PubSub."""
    
    def __init__(self, repo_path: str, username: str = None):
        """
        Initialize the chat application.
        
        Args:
            repo_path: Path to the IPFS repository.
            username: Optional username. If None, a random one will be generated.
        """
        self.repo_path = repo_path
        
        # Generate random username if not provided
        if username is None:
            rnd = ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))
            self.username = f"user-{rnd}"
        else:
            self.username = username
            
        # Create IPFS node
        self.node = IPFSNode(repo_path, enable_pubsub=True)
        
        # Dict to keep track of active room subscriptions
        self.rooms = {}
        
        # Subscribe to the control topic for room discovery
        self.control_topic = "chat-control"
        self.control_subscription = self.node.pubsub_subscribe(self.control_topic)
        self.control_subscription.subscribe(self._handle_control_message)
        
        # Announce ourselves
        self._announce_presence()
        
    def _announce_presence(self):
        """Announce our presence in the control topic."""
        # Prepare announcement message
        announcement = {
            "type": "announce",
            "username": self.username,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Publish announcement
        self.node.pubsub_publish(self.control_topic, json.dumps(announcement))
        
    def join_room(self, room_name: str):
        """
        Join a chat room.
        
        Args:
            room_name: The name of the room to join.
        """
        if room_name in self.rooms:
            print(f"Already in room: {room_name}")
            return
            
        # Subscribe to the room's topic
        topic = f"chat-room-{room_name}"
        subscription = self.node.pubsub_subscribe(topic)
        subscription.subscribe(self._handle_room_message)
        
        # Add to our list of rooms
        self.rooms[room_name] = {
            "topic": topic,
            "subscription": subscription,
            "joined_at": datetime.datetime.now().isoformat()
        }
        
        # Announce joining the room
        join_message = {
            "type": "join",
            "room": room_name,
            "username": self.username,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Publish to both the control topic and the room topic
        self.node.pubsub_publish(self.control_topic, json.dumps(join_message))
        self.node.pubsub_publish(topic, json.dumps({
            "type": "system",
            "content": f"{self.username} has joined the room",
            "timestamp": datetime.datetime.now().isoformat()
        }))
        
        print(f"Joined room: {room_name}")
        
    def leave_room(self, room_name: str):
        """
        Leave a chat room.
        
        Args:
            room_name: The name of the room to leave.
        """
        if room_name not in self.rooms:
            print(f"Not in room: {room_name}")
            return
            
        # Get room info
        room = self.rooms.pop(room_name)
        
        # Announce leaving the room
        leave_message = {
            "type": "leave",
            "room": room_name,
            "username": self.username,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Publish to both the control topic and the room topic
        self.node.pubsub_publish(self.control_topic, json.dumps(leave_message))
        self.node.pubsub_publish(room["topic"], json.dumps({
            "type": "system",
            "content": f"{self.username} has left the room",
            "timestamp": datetime.datetime.now().isoformat()
        }))
        
        # Close the subscription
        room["subscription"].close()
        
        print(f"Left room: {room_name}")
        
    def send_message(self, room_name: str, content: str):
        """
        Send a message to a chat room.
        
        Args:
            room_name: The name of the room to send to.
            content: The message content.
        """
        if room_name not in self.rooms:
            print(f"Not in room: {room_name}")
            return False
            
        # Prepare message
        message = {
            "type": "message",
            "username": self.username,
            "content": content,
            "timestamp": datetime.datetime.now().isoformat()
        }
        
        # Publish to the room's topic
        topic = self.rooms[room_name]["topic"]
        success = self.node.pubsub_publish(topic, json.dumps(message))
        
        return success
        
    def list_rooms(self):
        """List all joined rooms."""
        if not self.rooms:
            print("Not in any rooms")
        else:
            print("Joined rooms:")
            for name, room in self.rooms.items():
                peers = self.node.pubsub_peers(room["topic"])
                print(f"- {name} ({len(peers)} peers)")
                
    def list_peers(self, room_name: str = None):
        """
        List peers in a room or all connected peers.
        
        Args:
            room_name: Optional room name to filter peers.
        """
        if room_name:
            if room_name not in self.rooms:
                print(f"Not in room: {room_name}")
                return
                
            topic = self.rooms[room_name]["topic"]
            peers = self.node.pubsub_peers(topic)
            print(f"Peers in room {room_name}:")
            for peer in peers:
                print(f"- {peer}")
                
            if not peers:
                print("No peers found")
        else:
            # List all pubsub peers
            peers = self.node.pubsub_peers()
            print(f"All connected peers:")
            for peer in peers:
                print(f"- {peer}")
                
            if not peers:
                print("No peers found")
                
    def _handle_control_message(self, message: IPFSMessage):
        """
        Handle messages on the control topic.
        
        Args:
            message: The received message.
        """
        try:
            # Skip our own messages
            if message.from_peer == self.node._peer_id:
                return
                
            # Parse the message
            data = json.loads(message.data.decode('utf-8'))
            msg_type = data.get("type")
            
            if msg_type == "announce":
                username = data.get("username", "unknown")
                print(f"[SYSTEM] User {username} is online")
                
            elif msg_type == "join":
                username = data.get("username", "unknown")
                room = data.get("room", "unknown")
                print(f"[SYSTEM] User {username} joined room: {room}")
                
            elif msg_type == "leave":
                username = data.get("username", "unknown")
                room = data.get("room", "unknown")
                print(f"[SYSTEM] User {username} left room: {room}")
                
        except Exception as e:
            print(f"Error handling control message: {e}")
            
    def _handle_room_message(self, message: IPFSMessage):
        """
        Handle messages in chat rooms.
        
        Args:
            message: The received message.
        """
        try:
            # Parse the message
            data = json.loads(message.data.decode('utf-8'))
            msg_type = data.get("type")
            
            # Find which room this message is for
            room_name = None
            for name, room in self.rooms.items():
                if room["topic"] == message.topic_id:
                    room_name = name
                    break
                    
            if not room_name:
                return
                
            if msg_type == "message":
                username = data.get("username", "unknown")
                content = data.get("content", "")
                timestamp = data.get("timestamp", "")
                time_str = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
                
                # Skip our own messages
                if username == self.username:
                    return
                    
                print(f"[{time_str}] [{room_name}] {username}: {content}")
                
            elif msg_type == "system":
                content = data.get("content", "")
                timestamp = data.get("timestamp", "")
                time_str = datetime.datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
                print(f"[{time_str}] [{room_name}] SYSTEM: {content}")
                
        except Exception as e:
            print(f"Error handling room message: {e}")
            
    def close(self):
        """Close the chat application and clean up resources."""
        # Leave all rooms
        for room_name in list(self.rooms.keys()):
            self.leave_room(room_name)
            
        # Close control subscription
        if self.control_subscription:
            self.control_subscription.close()
            
        # Close the IPFS node
        self.node.close()
        
    def __enter__(self):
        """Support for context manager protocol."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the context manager."""
        self.close()

def chat_interface(chat_app: ChatApp):
    """
    Simple text-based interface for the chat application.
    
    Args:
        chat_app: The chat application instance.
    """
    print(f"Chat application started. Username: {chat_app.username}")
    print("Type commands preceded by a slash (e.g., /join room1), or just type to send a message")
    print("Available commands:")
    print("  /join <room> - Join a chat room")
    print("  /leave <room> - Leave a chat room")
    print("  /rooms - List joined rooms")
    print("  /peers [room] - List peers (in a specific room if provided)")
    print("  /switch <room> - Switch to a different room for messaging")
    print("  /quit - Exit the application")
    
    current_room = None
    
    try:
        while True:
            if current_room:
                prompt = f"[{current_room}]> "
            else:
                prompt = "> "
                
            user_input = input(prompt).strip()
            
            if not user_input:
                continue
                
            if user_input.startswith("/"):
                # Parse command
                parts = user_input.split()
                command = parts[0][1:]  # Remove slash
                args = parts[1:] if len(parts) > 1 else []
                
                if command == "join" and args:
                    chat_app.join_room(args[0])
                    if not current_room:
                        current_room = args[0]
                        
                elif command == "leave" and args:
                    chat_app.leave_room(args[0])
                    if current_room == args[0]:
                        current_room = None
                        
                elif command == "rooms":
                    chat_app.list_rooms()
                    
                elif command == "peers":
                    if args:
                        chat_app.list_peers(args[0])
                    else:
                        chat_app.list_peers()
                        
                elif command == "switch" and args:
                    if args[0] in chat_app.rooms:
                        current_room = args[0]
                        print(f"Switched to room: {current_room}")
                    else:
                        print(f"Not in room: {args[0]}")
                        
                elif command == "quit":
                    break
                    
                else:
                    print("Unknown command or missing arguments")
                    
            else:
                # Send message to current room
                if current_room:
                    success = chat_app.send_message(current_room, user_input)
                    if success:
                        # Echo message to our own console
                        time_str = datetime.datetime.now().strftime("%H:%M:%S")
                        print(f"[{time_str}] [{current_room}] {chat_app.username}: {user_input}")
                    else:
                        print("Failed to send message")
                else:
                    print("Not in any room. Join a room first with /join <room>")
                    
    except KeyboardInterrupt:
        print("\nExiting...")

def main():
    parser = argparse.ArgumentParser(description='IPFS PubSub Chat Application')
    parser.add_argument('--repo', help='Path to IPFS repository', 
                        default=os.path.expanduser('~/.ipfs-kubo-python'))
    parser.add_argument('--username', help='Username to use in the chat')
    
    args = parser.parse_args()
    
    # Ensure repository directory exists
    os.makedirs(args.repo, exist_ok=True)
    
    with ChatApp(args.repo, args.username) as chat_app:
        chat_interface(chat_app)

if __name__ == "__main__":
    main()