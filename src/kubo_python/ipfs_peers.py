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
from .lib import libkubo, c_str, from_c_str, ffi
DEF_FIND_TIMEOUT=10
from ipfs_tk_generics.peers import BasePeers
class NodePeers(BasePeers):
    def __init__(self, node):
        self._node = node
        self._repo_path = self._node._repo_path
    def find(self, peer_id:str, timeout=DEF_FIND_TIMEOUT)->list[str]:
        data = from_c_str(
            libkubo.FindPeer(c_str(self._repo_path), c_str(peer_id), timeout), 
        )
        return json.loads(data)
    def list_peers(self)->list[str]:
        data = from_c_str(
            libkubo.ListPeers(c_str(self._repo_path))
        )
    
        return json.loads(data)
    def list_ids(self)->list[str]:
        data = from_c_str(
            libkubo.ListPeersIDs(c_str(self._repo_path))
        )
    
        return json.loads(data)
    def connect(self, peer_addr: str) -> bool:
        """
        Connect to an IPFS peer.

        Args:
            peer_addr: Multiaddress of the peer to connect to.

        Returns:
            bool: True if successfully connected, False otherwise.
        """
        if not self._node._online:
            raise RuntimeError("Cannot connect to peers in offline mode")

        try:
            repo_path = c_str(self._repo_path.encode('utf-8'))
            peer_addr_c = c_str(peer_addr.encode('utf-8'))

            result = libkubo.ConnectToPeer(repo_path, peer_addr_c)

            return result == 0
        except Exception as e:
            # Handle any exceptions during the process
            raise RuntimeError(f"Error connecting to peer: {e}")
        def list_peers(self):
            data = from_c_str(
                libkubo.ListPeers(c_str(self._repo_path))
            )
            
            return json.loads(data)
    def is_peer_connected(self, peer_id:str, *args, **kwargs):
        #TODO: replace with ping
        return peer_id in self.list_ids()
    def terminate(self):
        pass
    def __del__(self):
        self.terminate()