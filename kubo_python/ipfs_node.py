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


class IPFSNode:
    """
    Python wrapper for a Kubo IPFS node.
    
    This class provides an interface to work with IPFS functionality
    through the Kubo implementation.
    """
    
    def __init__(self, repo_path: Optional[str] = None, online: bool = True, enable_pubsub: bool = True):
        """
        Initialize an IPFS node with a specific repository path.
        
        Args:
            repo_path: Path to the IPFS repository. If None, a temporary
                       repository will be created.
            online: Whether the node should connect to the IPFS network.
            enable_pubsub: Whether to enable pubsub functionality.
        """
        self._temp_dir = None
        self._lib = None
        self._repo_path = repo_path
        self._online = online
        self._enable_pubsub = enable_pubsub
        self._subscriptions = {}  # Track active subscriptions by topic
        self._peer_id = None  # Will be set when connecting to the network
        
        # If no repo path is provided, create a temporary directory
        if self._repo_path is None:
            self._temp_dir = tempfile.TemporaryDirectory()
            self._repo_path = self._temp_dir.name
        
        # Load the shared library
        self._load_library()
        
        # Initialize the repository if it doesn't exist
        if not os.path.exists(os.path.join(self._repo_path, "config")):
            self._init_repo()
            
        # Enable pubsub if requested
        if self._enable_pubsub and self._online:
            self._enable_pubsub_config()
            
        # Get the node ID if online
        if self._online:
            self._peer_id = self.get_node_id()
    
    def _load_library(self):
        """Load the Kubo shared library."""
        # Determine library name based on platform
        if platform.system() == 'Windows':
            lib_name = 'libkubo.dll'
        elif platform.system() == 'Darwin':
            lib_name = 'libkubo.dylib'
        else:
            lib_name = 'libkubo.so'
        
        # Get the absolute path to the library
        lib_path = Path(__file__).parent / 'lib' / lib_name
        
        # Load the library
        try:
            self._lib = ctypes.CDLL(str(lib_path))
        except OSError as e:
            raise RuntimeError(f"Failed to load Kubo library: {e}")
        
        # Define function signatures
        self._lib.CreateRepo.argtypes = [ctypes.c_char_p]
        self._lib.CreateRepo.restype = ctypes.c_int
        
        self._lib.AddFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.AddFile.restype = ctypes.c_char_p
        
        self._lib.GetFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        self._lib.GetFile.restype = ctypes.c_int
        
        self._lib.ConnectToPeer.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.ConnectToPeer.restype = ctypes.c_int
        
        self._lib.FreeString.argtypes = [ctypes.c_char_p]
        self._lib.FreeString.restype = None
        
        # PubSub function signatures
        self._lib.PubSubEnable.argtypes = [ctypes.c_char_p]
        self._lib.PubSubEnable.restype = ctypes.c_int
        
        self._lib.PubSubListTopics.argtypes = [ctypes.c_char_p]
        self._lib.PubSubListTopics.restype = ctypes.c_char_p
        
        self._lib.PubSubPublish.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int]
        self._lib.PubSubPublish.restype = ctypes.c_int
        
        self._lib.PubSubSubscribe.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.PubSubSubscribe.restype = ctypes.c_longlong
        
        self._lib.PubSubNextMessage.argtypes = [ctypes.c_longlong]
        self._lib.PubSubNextMessage.restype = ctypes.c_char_p
        
        self._lib.PubSubUnsubscribe.argtypes = [ctypes.c_longlong]
        self._lib.PubSubUnsubscribe.restype = ctypes.c_int
        
        self._lib.PubSubPeers.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.PubSubPeers.restype = ctypes.c_char_p
        
        # Node ID function signature
        self._lib.GetNodeID.argtypes = [ctypes.c_char_p]
        self._lib.GetNodeID.restype = ctypes.c_char_p
        
        # Node cleanup function signature
        self._lib.CleanupNode.argtypes = [ctypes.c_char_p]
        self._lib.CleanupNode.restype = ctypes.c_int
    
    def _init_repo(self):
        """Initialize the IPFS repository."""
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        result = self._lib.CreateRepo(repo_path)
        
        if result < 0:
            raise RuntimeError(f"Failed to initialize IPFS repository: {result}")
    
    def add_file(self, file_path: str) -> str:
        """
        Add a file to IPFS.
        
        Args:
            file_path: Path to the file to add.
            
        Returns:
            str: The CID (Content Identifier) of the added file.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        file_path_c = ctypes.c_char_p(os.path.abspath(file_path).encode('utf-8'))
        
        try:
            cid_ptr = self._lib.AddFile(repo_path, file_path_c)
            if not cid_ptr:
                raise RuntimeError("Failed to add file to IPFS")
                
            # Copy the string content before freeing the pointer
            cid = ctypes.string_at(cid_ptr).decode('utf-8')
            
            # Store the memory freeing operation in a separate try block
            try:
                # Free the memory allocated by C.CString in Go
                self._lib.FreeString(cid_ptr)
            except Exception as e:
                print(f"Warning: Failed to free memory: {e}")
            
            if not cid:
                raise RuntimeError("Failed to add file to IPFS")
            
            return cid
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error adding file to IPFS: {e}")
    
    def add_directory(self, dir_path: str) -> str:
        """
        Add a directory to IPFS.
        
        Args:
            dir_path: Path to the directory to add.
            
        Returns:
            str: The CID (Content Identifier) of the added directory.
        """
        if not os.path.isdir(dir_path):
            raise NotADirectoryError(f"Not a directory: {dir_path}")
        
        # The underlying Go implementation handles directories
        return self.add_file(dir_path)
    
    def get_file(self, cid: str, dest_path: str) -> bool:
        """
        Retrieve a file from IPFS by its CID.
        
        Args:
            cid: The Content Identifier of the file to retrieve.
            dest_path: Destination path where the file will be saved.
            
        Returns:
            bool: True if the file was successfully retrieved, False otherwise.
        """
        try:
            repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
            cid_c = ctypes.c_char_p(cid.encode('utf-8'))
            dest_path_c = ctypes.c_char_p(os.path.abspath(dest_path).encode('utf-8'))
            
            result = self._lib.GetFile(repo_path, cid_c, dest_path_c)
            
            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error retrieving file from IPFS: {e}")
    
    def connect_to_peer(self, peer_addr: str) -> bool:
        """
        Connect to an IPFS peer.
        
        Args:
            peer_addr: Multiaddress of the peer to connect to.
            
        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if not self._online:
            raise RuntimeError("Cannot connect to peers in offline mode")
        
        try:
            repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
            peer_addr_c = ctypes.c_char_p(peer_addr.encode('utf-8'))
            
            result = self._lib.ConnectToPeer(repo_path, peer_addr_c)
            
            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error connecting to peer: {e}")
    
    def add_bytes(self, data: bytes, filename: Optional[str] = None) -> str:
        """
        Add bytes data to IPFS.
        
        Args:
            data: Bytes to add to IPFS.
            filename: Optional filename to use as a temporary file.
            
        Returns:
            str: The CID of the added data.
        """
        # Create a temporary file
        temp_file = None
        temp_file_path = None
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=filename if filename else '') as temp_file:
                temp_file.write(data)
                temp_file_path = temp_file.name
            
            # Add the temporary file to IPFS
            return self.add_file(temp_file_path)
        except Exception as e:
            raise RuntimeError(f"Error adding bytes to IPFS: {e}")
        finally:
            # Clean up the temporary file
            if temp_file_path is not None and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    # Silently ignore cleanup errors
                    pass
    
    def add_str(self, content: str, filename: Optional[str] = None) -> str:
        """
        Add string content to IPFS.
        
        Args:
            content: String content to add.
            filename: Optional filename to use as a temporary file.
            
        Returns:
            str: The CID of the added content.
        """
        return self.add_bytes(content.encode('utf-8'), filename)
    
    def get_bytes(self, cid: str) -> bytes:
        """
        Get bytes data from IPFS.
        
        Args:
            cid: The Content Identifier of the data to retrieve.
            
        Returns:
            bytes: The retrieved data.
        """
        temp_file = None
        temp_file_path = None
        try:
            # Create a temporary file to store the retrieved data
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file_path = temp_file.name
            temp_file.close()
            
            # Get the file from IPFS
            success = self.get_file(cid, temp_file_path)
            if not success:
                raise RuntimeError(f"Failed to retrieve data for CID: {cid}")
            
            # Read the data from the temporary file
            with open(temp_file_path, 'rb') as f:
                return f.read()
        except Exception as e:
            raise RuntimeError(f"Error retrieving bytes from IPFS: {e}")
        finally:
            # Clean up the temporary file
            if temp_file_path is not None and os.path.exists(temp_file_path):
                try:
                    os.unlink(temp_file_path)
                except Exception:
                    # Silently ignore cleanup errors
                    pass
    
    def get_str(self, cid: str, encoding: str = 'utf-8') -> str:
        """
        Get string content from IPFS.
        
        Args:
            cid: The Content Identifier of the content to retrieve.
            encoding: The encoding to use when decoding the bytes.
            
        Returns:
            str: The retrieved content as a string.
        """
        data = self.get_bytes(cid)
        return data.decode(encoding)
    
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
        
    def close(self):
        """Close the IPFS node and clean up resources."""
        # Close all active subscriptions
        for topic, subscriptions in list(self._subscriptions.items()):
            for sub in list(subscriptions):
                try:
                    sub.close()
                except Exception as e:
                    print(f"Warning: Error closing subscription: {e}")
                    
        self._subscriptions.clear()
        
        # Force cleanup of the node in Go
        if self._repo_path:
            try:
                repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
                self._lib.CleanupNode(repo_path)
                print(f"Node for repo {self._repo_path} explicitly cleaned up")
            except Exception as e:
                print(f"Warning: Error cleaning up node: {e}")
        
        # Clean up temporary directory if one was created
        if self._temp_dir is not None:
            self._temp_dir.cleanup()
            self._temp_dir = None
    
    def __enter__(self):
        """Support for context manager protocol."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Clean up when exiting the context manager."""
        self.close()
    
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
    
    def get_node_id(self) -> str:
        """
        Get the peer ID of this IPFS node.
        
        Returns:
            str: The peer ID of the node, or empty string if not available.
        """
        if not self._online:
            return ""
            
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        id_ptr = self._lib.GetNodeID(repo_path)
        
        if not id_ptr:
            return ""
            
        # Copy the string content before freeing the pointer
        peer_id = ctypes.string_at(id_ptr).decode('utf-8')
        
        try:
            # Free the memory allocated in Go
            self._lib.FreeString(id_ptr)
        except Exception as e:
            print(f"Warning: Failed to free memory: {e}")
            
        return peer_id
        
    @property
    def peer_id(self) -> str:
        """Get the peer ID of this node."""
        if not self._peer_id:
            self._peer_id = self.get_node_id()
        return self._peer_id
            
    @classmethod
    def ephemeral(cls, online: bool = True, enable_pubsub: bool = True):
        """
        Create an ephemeral IPFS node with a temporary repository.
        
        Args:
            online: Whether the node should connect to the IPFS network.
            enable_pubsub: Whether to enable pubsub functionality.
            
        Returns:
            IPFSNode: A new IPFS node instance with a temporary repository.
        """
        return cls(None, online, enable_pubsub)