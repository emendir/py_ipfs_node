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
import base64
from base64 import urlsafe_b64decode, urlsafe_b64encode


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

        # decode data field
        data_bytes = bytes(urlsafe_b64decode(data.get('data')))

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

    def __init__(self, node: 'IpfsNode', sub_id: int, topic: str):
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


class NodePubsub:
    # PubSub methods
    def pubsub_subscribe(self, topic: str) -> IPFSSubscription:
        """
        Subscribe to a pubsub topic.

        Args:
            topic: The topic to subscribe to.

        Returns:
            IPFSSubscription: A subscription object for the topic.
        """
        if not self._online:
            raise RuntimeError("Cannot subscribe to topics in offline mode")

        if not self._enable_pubsub:
            raise RuntimeError("PubSub is not enabled for this node")

        # Subscribe to the topic
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        topic_c = ctypes.c_char_p(topic.encode('utf-8'))

        sub_id = self._lib.PubSubSubscribe(repo_path, topic_c)
        if sub_id < 0:
            raise RuntimeError(f"Failed to subscribe to topic: {topic}")

        # Create the subscription object
        subscription = IPFSSubscription(self, sub_id, topic)

        # Track the subscription
        if topic not in self._subscriptions:
            self._subscriptions[topic] = set()
        self._subscriptions[topic].add(subscription)

        return subscription

    def pubsub_publish(self, topic: str, data: Union[str, bytes]) -> bool:
        """
        Publish a message to a pubsub topic.

        Args:
            topic: The topic to publish to.
            data: The message data to publish. If a string is provided, it will be
                  encoded as UTF-8 bytes.

        Returns:
            bool: True if the message was published successfully.
        """
        if not self._online:
            raise RuntimeError("Cannot publish to topics in offline mode")

        if not self._enable_pubsub:
            raise RuntimeError("PubSub is not enabled for this node")

        # Convert string to bytes if needed
        if isinstance(data, str):
            data_bytes = data.encode('utf-8')
        else:
            data_bytes = data

        # Get the repository path
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        topic_c = ctypes.c_char_p(topic.encode('utf-8'))

        # Create a data buffer for the message
        data_len = len(data_bytes)
        data_buffer = ctypes.create_string_buffer(data_bytes, data_len)

        # Publish the message
        result = self._lib.PubSubPublish(
            repo_path,
            topic_c,
            ctypes.cast(data_buffer, ctypes.c_void_p),
            ctypes.c_int(data_len)
        )

        return result == 0

    def pubsub_peers(self, topic: Optional[str] = None) -> List[str]:
        """
        List peers participating in pubsub.

        Args:
            topic: Optional topic to filter peers. If None, returns all pubsub peers.

        Returns:
            List[str]: List of peer IDs.
        """
        if not self._online:
            raise RuntimeError("Cannot list peers in offline mode")

        if not self._enable_pubsub:
            raise RuntimeError("PubSub is not enabled for this node")

        # Get the repository path
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        topic_c = ctypes.c_char_p((topic or "").encode('utf-8'))

        # Get peers
        peers_ptr = self._lib.PubSubPeers(repo_path, topic_c)
        if not peers_ptr:
            return []

        # Copy the string content before freeing the pointer
        json_data = ctypes.string_at(peers_ptr).decode('utf-8')

        try:
            # Free the memory allocated in Go
            self._lib.FreeString(peers_ptr)
        except Exception as e:
            print(f"Warning: Failed to free memory: {e}")

        try:
            # Parse the JSON array
            return json.loads(json_data)
        except json.JSONDecodeError:
            return []

    def pubsub_topics(self) -> List[str]:
        """
        List subscribed pubsub topics.

        Returns:
            List[str]: List of topic names.
        """
        if not self._online:
            raise RuntimeError("Cannot list topics in offline mode")

        if not self._enable_pubsub:
            raise RuntimeError("PubSub is not enabled for this node")

        # Get the repository path
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))

        # Get topics
        topics_ptr = self._lib.PubSubListTopics(repo_path)
        if not topics_ptr:
            return []

        # Copy the string content before freeing the pointer
        json_data = ctypes.string_at(topics_ptr).decode('utf-8')

        try:
            # Free the memory allocated in Go
            self._lib.FreeString(topics_ptr)
        except Exception as e:
            print(f"Warning: Failed to free memory: {e}")

        try:
            # Parse the JSON array
            return json.loads(json_data)
        except json.JSONDecodeError:
            return []
            
    def _enable_pubsub_config(self):
        """Enable pubsub in the IPFS configuration."""
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        result = self._lib.PubSubEnable(repo_path)

        if result < 0:
            raise RuntimeError(f"Failed to enable pubsub: {result}")

    def _pubsub_next_message(self, subscription_id: int) -> Optional[IPFSMessage]:
        """
        Get the next message from a subscription.

        Args:
            subscription_id: The subscription ID.

        Returns:
            IPFSMessage or None: The next message, or None if no message is available.
        """
        sub_id = ctypes.c_longlong(subscription_id)

        # Get message as JSON string
        message_ptr = self._lib.PubSubNextMessage(sub_id)
        if not message_ptr:
            return None

        # Copy the string content before freeing the pointer
        json_data = ctypes.string_at(message_ptr).decode('utf-8')

        try:
            # Free the memory allocated in Go
            self._lib.FreeString(message_ptr)
        except Exception as e:
            print(f"Warning: Failed to free memory: {e}")

        try:
            # Parse the message
            return IPFSMessage.from_json(json_data)
        except Exception as e:
            print(f"Warning: Failed to parse message: {e}")
            return None

    def _pubsub_unsubscribe(self, subscription_id: int) -> bool:
        """
        Unsubscribe from a topic.

        Args:
            subscription_id: The subscription ID.

        Returns:
            bool: True if successfully unsubscribed.
        """
        sub_id = ctypes.c_longlong(subscription_id)
        result = self._lib.PubSubUnsubscribe(sub_id)

        # Clean up local subscription tracking
        to_remove = []
        for topic, subscriptions in self._subscriptions.items():
            for sub in list(subscriptions):
                if sub.id == subscription_id:
                    subscriptions.remove(sub)
                    # If no more subscriptions for this topic, remove the topic
                    if not subscriptions:
                        to_remove.append(topic)

        for topic in to_remove:
            del self._subscriptions[topic]

        return result == 0