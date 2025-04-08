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
from .ipfs_pubsub import IPFSMessage, IPFSSubscription, NodePubsub
from .lib import libkubo, c_str, from_c_str, ffi
from .ipfs_p2p import NodeTcp
from .ipfs_files import NodeFiles


class IpfsNode:
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
        self._repo_path = repo_path
        self._online = online
        self._enable_pubsub = enable_pubsub
        self._peer_id = None  # Will be set when connecting to the network
        # If no repo path is provided, create a temporary directory
        if self._repo_path is None:
            self._temp_dir = tempfile.TemporaryDirectory()
            self._repo_path = self._temp_dir.name


        # Initialize the repository if it doesn't exist
        if not os.path.exists(os.path.join(self._repo_path, "config")):
            self._init_repo()
        libkubo.RunNode(c_str(self._repo_path.encode('utf-8')))

        # Get the node ID if online
        if self._online:
            self._peer_id = self.get_node_id()
        self._pubsub = NodePubsub(self)
        self._tcp = NodeTcp(self)
        self._files = NodeFiles(self)
        
        # Enable pubsub if requested
        if self._enable_pubsub and self._online:
            self.pubsub._enable_pubsub_config()
    @property
    def tcp(self)->NodeTcp:
        return self._tcp
    @property
    def pubsub(self)->NodePubsub:
        return self._pubsub
    @property
    def files(self)->NodePubsub:
        return self._files
    def _run(self):
        pass

    def _stop(self):
        pass

    def _init_repo(self):
        """Initialize the IPFS repository."""
        repo_path = c_str(self._repo_path.encode('utf-8'))
        result = libkubo.CreateRepo(repo_path)

        if result < 0:
            raise RuntimeError(
                f"Failed to initialize IPFS repository: {result}")
        # print(f"Initalised repo at: {repo_path}")


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
            repo_path = c_str(self._repo_path.encode('utf-8'))
            peer_addr_c = c_str(peer_addr.encode('utf-8'))

            result = libkubo.ConnectToPeer(repo_path, peer_addr_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error connecting to peer: {e}")



    def close(self):
        """Close the IPFS node and clean up resources."""
        self._pubsub.close()
        self._tcp.close()
        self._files.close()
        # Force cleanup of the node in Go
        if self._repo_path:
            try:
                repo_path = c_str(self._repo_path.encode('utf-8'))
                print("Cleaning up node...")
                libkubo.CleanupNode(repo_path)
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




    def test_get_string(self) -> str:
        """Test function to check basic string passing from Go to Python"""
        try:
            id_ptr = libkubo.TestGetString()
            if not id_ptr:
                print("TEST: No string returned from TestGetString")
                return ""

            test_str = from_c_str(id_ptr)
            # print(f"TEST: String from Go: '{test_str}', length: {len(test_str)}")
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

        # try to get the node ID
        try:
            repo_path = c_str(self._repo_path.encode('utf-8'))

            id_ptr = libkubo.GetNodeID(repo_path)

            if not id_ptr:
                print("IPFS: NO ID_PTR")
                return ""

            # Copy the string content
            peer_id = from_c_str(id_ptr)

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
            IpfsNode: A new IPFS node instance with a temporary repository.
        """
        return cls(None, online, enable_pubsub)
    