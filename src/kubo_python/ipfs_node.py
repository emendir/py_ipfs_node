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
from .ipfs_pubsub import IPFSMessage, IPFSSubscription


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
        self._lib.RunNode(ctypes.c_char_p(self._repo_path.encode('utf-8')))
        # Enable pubsub if requested
        if self._enable_pubsub and self._online:
            self._enable_pubsub_config()

        # Get the node ID if online
        if self._online:
            self._peer_id = self.get_node_id()

    def _run(self):
        pass

    def _stop(self):
        pass

    def _load_library(self):
        """Load the Kubo shared library."""
        # Determine library name based on platform
        if platform.system() == 'Windows':
            lib_name = 'libkubo.dll'
        elif platform.system() == 'Darwin':
            lib_name = 'libkubo.dylib'
        else:
            if "aarch64" == platform.machine():
                lib_name = "libkubo_android_arm64.so"
            else:
                lib_name = 'libkubo_linux_x86_64.so'

        # Get the absolute path to the library
        lib_path = Path(__file__).parent / 'lib' / lib_name

        # Load the library
        try:
            self._lib = ctypes.CDLL(str(lib_path))
        except OSError as e:
            raise RuntimeError(f"Failed to load Kubo library: {e}")

        # Define function signatures
        self._lib.RunNode.argtypes = [ctypes.c_char_p]
        self._lib.RunNode.restype = ctypes.c_int

        self._lib.CreateRepo.argtypes = [ctypes.c_char_p]
        self._lib.CreateRepo.restype = ctypes.c_int

        self._lib.AddFile.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.AddFile.restype = ctypes.c_char_p

        self._lib.GetFile.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
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

        self._lib.PubSubPublish.argtypes = [
            ctypes.c_char_p, ctypes.c_char_p, ctypes.c_void_p, ctypes.c_int]
        self._lib.PubSubPublish.restype = ctypes.c_int

        self._lib.PubSubSubscribe.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.PubSubSubscribe.restype = ctypes.c_longlong

        self._lib.PubSubNextMessage.argtypes = [ctypes.c_longlong]
        self._lib.PubSubNextMessage.restype = ctypes.c_char_p

        self._lib.PubSubUnsubscribe.argtypes = [ctypes.c_longlong]
        self._lib.PubSubUnsubscribe.restype = ctypes.c_int

        self._lib.PubSubPeers.argtypes = [ctypes.c_char_p, ctypes.c_char_p]
        self._lib.PubSubPeers.restype = ctypes.c_char_p

        # Test function
        self._lib.TestGetString.argtypes = []
        self._lib.TestGetString.restype = ctypes.c_char_p

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
            raise RuntimeError(
                f"Failed to initialize IPFS repository: {result}")
        print(f"Initalised repo at: {repo_path}")
        print(result)

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
        file_path_c = ctypes.c_char_p(
            os.path.abspath(file_path).encode('utf-8'))

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
            dest_path_c = ctypes.c_char_p(
                os.path.abspath(dest_path).encode('utf-8'))

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
            
    # P2P TCP Methods
    def create_tcp_forwarding_connection(self, proto: str, port: int, peer_id: str) -> bool:
        """
        Equivalent to the `ipfs p2p forward` command.
        Creates a mapping from a local port to a service on a remote peer.
        
        Args:
            proto: Protocol string (will be prefixed with '/x/' if not already)
            port: Local port to forward from
            peer_id: Target peer ID to forward to
            
        Returns:
            bool: True if the forwarding connection was created successfully
        """
        if not self._online:
            raise RuntimeError("Cannot create TCP forwarding in offline mode")
            
        # Construct the listen address
        listen_addr = f"/ip4/127.0.0.1/tcp/{port}"
        
        # Make sure p2p functionality is enabled
        self._enable_p2p()
            
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        proto_c = ctypes.c_char_p(proto.encode('utf-8'))
        listen_addr_c = ctypes.c_char_p(listen_addr.encode('utf-8'))
        peer_id_c = ctypes.c_char_p(peer_id.encode('utf-8'))
        
        # Define function signature if not already defined
        if not hasattr(self._lib, 'P2PForward'):
            self._lib.P2PForward.argtypes = [
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p
            ]
            self._lib.P2PForward.restype = ctypes.c_int
        
        result = self._lib.P2PForward(repo_path, proto_c, listen_addr_c, peer_id_c)
        return result > 0

    def close_tcp_connection(self, proto: str = None, port: int = None, peer_id: str = None) -> int:
        """
        Close specific TCP p2p connections, optionally filtered by protocol, port, or peer ID.
        
        Args:
            proto: Optional protocol filter
            port: Optional port filter
            peer_id: Optional peer ID filter
            
        Returns:
            int: Number of connections closed
        """
        # Define function signature if not already defined
        if not hasattr(self._lib, 'P2PClose'):
            self._lib.P2PClose.argtypes = [
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p
            ]
            self._lib.P2PClose.restype = ctypes.c_int
        
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        
        # Format protocol filter
        proto_c = ctypes.c_char_p((proto if proto else "").encode('utf-8'))
        
        # Format port filter
        listen_addr = f"/ip4/127.0.0.1/tcp/{port}" if port is not None else ""
        listen_addr_c = ctypes.c_char_p(listen_addr.encode('utf-8'))
        
        # Format peer ID filter
        peer_id_c = ctypes.c_char_p((peer_id if peer_id else "").encode('utf-8'))
        
        result = self._lib.P2PClose(repo_path, proto_c, listen_addr_c, peer_id_c)
        return result

    def close_tcp_forwarding_connection(self, proto: str = None, port: int = None, peer_id: str = None) -> int:
        """
        Close a specific TCP forwarding connection, optionally filtered by protocol, port, or peer ID.
        
        Args:
            proto: Optional protocol filter
            port: Optional port filter
            peer_id: Optional peer ID filter
            
        Returns:
            int: Number of forwarding connections closed
        """
        return self.close_tcp_connection(proto, port, peer_id)

    def close_all_tcp_forwarding_connections(self) -> int:
        """
        Close all TCP forwarding connections.
        
        Returns:
            int: Number of forwarding connections closed
        """
        return self.close_tcp_connection()

    def create_tcp_listening_connection(self, proto: str, port: int) -> bool:
        """
        Equivalent to the `ipfs p2p listen` command.
        Creates a libp2p service that forwards incoming connections to a local address.
        
        Args:
            proto: Protocol string (will be prefixed with '/x/' if not already)
            port: Local port to listen on
            
        Returns:
            bool: True if the listening connection was created successfully
        """
        if not self._online:
            raise RuntimeError("Cannot create TCP listener in offline mode")
            
        # Construct the target address
        target_addr = f"/ip4/127.0.0.1/tcp/{port}"
        
        # Make sure p2p functionality is enabled
        self._enable_p2p()
            
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        proto_c = ctypes.c_char_p(proto.encode('utf-8'))
        target_addr_c = ctypes.c_char_p(target_addr.encode('utf-8'))
        
        # Define function signature if not already defined
        if not hasattr(self._lib, 'P2PListen'):
            self._lib.P2PListen.argtypes = [
                ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p
            ]
            self._lib.P2PListen.restype = ctypes.c_int
        
        result = self._lib.P2PListen(repo_path, proto_c, target_addr_c)
        return result > 0

    def close_tcp_listening_connection(self, proto: str = None, port: int = None) -> int:
        """
        Close a specific TCP listening connection, optionally filtered by protocol or port.
        
        Args:
            proto: Optional protocol filter
            port: Optional port filter
            
        Returns:
            int: Number of listening connections closed
        """
        return self.close_tcp_connection(proto, port)

    def close_all_tcp_listening_connections(self) -> int:
        """
        Close all TCP listening connections.
        
        Returns:
            int: Number of listening connections closed
        """
        return self.close_tcp_connection()
        
    def list_tcp_connections(self) -> Dict[str, List[Dict[str, str]]]:
        """
        List all active TCP p2p connections.
        
        Returns:
            Dict[str, List[Dict[str, str]]]: Dictionary containing lists of local listeners and remote streams
        """
        # Import IPFSP2P lazily to avoid circular import
        from .ipfs_p2p import IPFSP2P
        
        # Get the P2P interface
        p2p = IPFSP2P(self)
        
        # Get the listeners and streams
        listeners, streams = p2p.list_listeners()
        
        # Convert to dictionary format
        result = {
            "LocalListeners": [listener.__dict__ for listener in listeners],
            "RemoteStreams": [stream.__dict__ for stream in streams]
        }
        
        return result
        
    def _enable_p2p(self) -> bool:
        """Enable p2p functionality in the IPFS configuration."""
        # Define function signature if not already defined
        if not hasattr(self._lib, 'P2PEnable'):
            self._lib.P2PEnable.argtypes = [ctypes.c_char_p]
            self._lib.P2PEnable.restype = ctypes.c_int
            
        repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
        result = self._lib.P2PEnable(repo_path)
        
        if result <= 0:
            print(f"Warning: Could not enable p2p functionality ({result})")
            return False
        return True

    def test_get_string(self) -> str:
        """Test function to check basic string passing from Go to Python"""
        try:
            id_ptr = self._lib.TestGetString()
            if not id_ptr:
                print("TEST: No string returned from TestGetString")
                return ""

            test_str = ctypes.string_at(id_ptr).decode('utf-8')
            print(f"TEST: String from Go: '{
                  test_str}', length: {len(test_str)}")
            return test_str
        except Exception as e:
            print(f"TEST ERROR: {e}")
            return f"ERROR: {e}"

    def get_node_id(self) -> str:
        """
        Get the peer ID of this IPFS node.

        Returns:
            str: The peer ID of the node, or empty string if not available.
        """
        if not self._online:
            print("IPFS: not online")
            return ""

        # First test the basic string function
        test_str = self.test_get_string()
        print(f"Basic string test result: '{test_str}'")

        # Now try to get the real node ID
        try:
            repo_path = ctypes.c_char_p(self._repo_path.encode('utf-8'))
            print(f"IPFS: Calling GetNodeID with repo path: {self._repo_path}")

            id_ptr = self._lib.GetNodeID(repo_path)

            print(f"IPFS: id_ptr is: {id_ptr}")
            if not id_ptr:
                print("IPFS: NO ID_PTR")
                return ""

            # Copy the string content
            peer_id = ctypes.string_at(id_ptr).decode('utf-8')
            print(f"IPFS: Got peer ID: '{peer_id}', length: {len(peer_id)}")

            # Don't free the memory - let Go's finalizer handle it
            # The memory will be freed when Go's garbage collector runs

            # Strip the prefix we added for debugging
            if peer_id.startswith("ID:"):
                peer_id = peer_id[3:]

            return peer_id
        except Exception as e:
            print(f"IPFS ERROR in get_node_id: {e}")
            return f"ERROR: {e}"

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
