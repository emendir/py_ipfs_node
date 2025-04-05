import os
import tempfile
import ctypes
import shutil
import platform
import json
import time
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, List, Dict, Any, Callable, Tuple, Iterator, Set


@dataclass
class IPFSMessage:
    """
    Represents a message received from the IPFS pubsub system.
    """
    from_peer: str
    """The peer ID of the message sender."""
    
    data: bytes
    """The message data as bytes."""
    
    topic_id: str
    """The topic this message was published to."""
    
    seqno: Optional[bytes] = None
    """Optional sequence number of the message."""
    
    topics: Optional[List[str]] = None
    """Optional list of topics this message was published to."""
    
    @classmethod
    def from_json(cls, json_data: str) -> 'IPFSMessage':
        """
        Create a message object from JSON string.
        
        Args:
            json_data: JSON string representation of a message.
            
        Returns:
            IPFSMessage: A new message object.
        """
        if not json_data:
            raise ValueError("Empty JSON data")
            
        data = json.loads(json_data)
        
        # Convert data field back to bytes
        if isinstance(data.get('data'), list):
            data_bytes = bytes(data.get('data', []))
        else:
            data_bytes = bytes()
            
        # Convert seqno field back to bytes
        seqno = None
        if data.get('seqno'):
            if isinstance(data.get('seqno'), list):
                seqno = bytes(data.get('seqno', []))
        
        return cls(
            from_peer=data.get('from', ''),
            data=data_bytes,
            topic_id=data.get('topicID', ''),
            seqno=seqno,
            topics=data.get('topics')
        )
        
    def __str__(self) -> str:
        """String representation of the message."""
        try:
            # Try to decode as UTF-8
            data_str = self.data.decode('utf-8')
        except UnicodeDecodeError:
            # Fall back to hex representation
            data_str = f"0x{self.data.hex()}"
            
        return f"IPFSMessage(from={self.from_peer}, topic={self.topic_id}, data={data_str})"


class IPFSSubscription:
    """
    Represents a subscription to an IPFS pubsub topic.
    """
    
    def __init__(self, node: 'IPFSNode', sub_id: int, topic: str):
        """
        Initialize a subscription.
        
        Args:
            node: The IPFS node this subscription belongs to.
            sub_id: The subscription ID from the Go wrapper.
            topic: The topic subscribed to.
        """
        self._node = node
        self._sub_id = sub_id
        self._topic = topic
        self._active = True
        self._callback = None
        self._callback_thread = None
        self._stop_event = threading.Event()
        
        # Get message queue ready
        self._message_queue = []
        
    @property
    def topic(self) -> str:
        """Get the topic name for this subscription."""
        return self._topic
        
    @property
    def id(self) -> int:
        """Get the subscription ID."""
        return self._sub_id
        
    @property
    def active(self) -> bool:
        """Check if the subscription is active."""
        return self._active
        
    def next_message(self, timeout: Optional[float] = None) -> Optional[IPFSMessage]:
        """
        Get the next message from this subscription.
        
        Args:
            timeout: Maximum time to wait in seconds. None means no timeout.
            
        Returns:
            IPFSMessage or None: The next message, or None if no message is available
            before the timeout.
        """
        if not self._active:
            raise RuntimeError("Subscription is no longer active")
            
        start_time = time.time()
        while timeout is None or (time.time() - start_time) < timeout:
            # Try to get a message
            message = self._node._pubsub_next_message(self._sub_id)
            if message:
                return message
                
            # Wait a bit before trying again
            time.sleep(0.1)
            
        return None
        
    def __iter__(self) -> Iterator[IPFSMessage]:
        """
        Iterate over incoming messages.
        
        Yields:
            IPFSMessage: Each message as it arrives.
        """
        while self._active:
            msg = self.next_message(timeout=1.0)
            if msg:
                yield msg
                
    def close(self) -> None:
        """Close the subscription."""
        if self._active:
            self._stop_callback()
            self._node._pubsub_unsubscribe(self._sub_id)
            self._active = False
            
    def __enter__(self) -> 'IPFSSubscription':
        """Support for context manager protocol."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Clean up when exiting the context manager."""
        self.close()
        
    def _callback_loop(self, callback: Callable[[IPFSMessage], None]) -> None:
        """
        Run the callback loop in a separate thread.
        
        Args:
            callback: Function to call for each message.
        """
        while not self._stop_event.is_set() and self._active:
            try:
                msg = self.next_message(timeout=0.5)
                if msg:
                    callback(msg)
            except Exception as e:
                # Just log the error and continue
                print(f"Error in subscription callback: {e}")
                
    def _stop_callback(self) -> None:
        """Stop the callback thread if running."""
        if self._callback_thread is not None:
            self._stop_event.set()
            self._callback_thread.join(timeout=2.0)
            self._callback_thread = None
            self._stop_event.clear()
                
    def subscribe(self, callback: Callable[[IPFSMessage], None]) -> None:
        """
        Set a callback to be called for each incoming message.
        
        Args:
            callback: Function to call for each message.
        """
        if not self._active:
            raise RuntimeError("Subscription is no longer active")
            
        # Stop any existing callback
        self._stop_callback()
        
        # Set the new callback
        self._callback = callback
        
        # Start a new thread to run the callback
        self._stop_event.clear()
        self._callback_thread = threading.Thread(
            target=self._callback_loop,
            args=(callback,),
            daemon=True
        )
        self._callback_thread.start()

