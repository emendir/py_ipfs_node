import ctypes
import json
from typing import List, Dict, Optional, Tuple, Any, Union

from .ipfs_node import IPFSNode


class P2PMapping:
    """
    Represents a mapping between a libp2p protocol and a network address.
    """
    
    def __init__(self, protocol: str, listen_address: str, target_address: str):
        """
        Initialize a P2P mapping.
        
        Args:
            protocol: The protocol name used for the mapping.
            listen_address: The listen address of the mapping.
            target_address: The target address of the mapping.
        """
        self.protocol = protocol
        self.listen_address = listen_address
        self.target_address = target_address
        
    def __str__(self) -> str:
        """String representation of the mapping."""
        return f"P2PMapping(protocol={self.protocol}, listen={self.listen_address}, target={self.target_address})"


class P2PStream:
    """
    Represents a libp2p stream between peers.
    """
    
    def __init__(self, protocol: str, origin_address: str, target_address: str):
        """
        Initialize a P2P stream.
        
        Args:
            protocol: The protocol name used for the stream.
            origin_address: The origin address of the stream.
            target_address: The target address of the stream.
        """
        self.protocol = protocol
        self.origin_address = origin_address
        self.target_address = target_address
        
    def __str__(self) -> str:
        """String representation of the stream."""
        return f"P2PStream(protocol={self.protocol}, origin={self.origin_address}, target={self.target_address})"


class IPFSP2P:
    """
    Provides P2P stream mounting functionality for IPFS nodes.
    
    Stream mounting allows you to expose local TCP services to the libp2p network
    and connect to remote TCP services exposed by other nodes.
    """
    
    def __init__(self, node: IPFSNode):
        """
        Initialize the P2P interface.
        
        Args:
            node: The IPFS node to use.
        """
        self._node = node
        self._lib = node._lib
        self._repo_path = node._repo_path
        
        # Check if p2p functionality is enabled
        self.enable()
    
    def enable(self) -> bool:
        """
        Enable P2P functionality in the node configuration.
        
        Returns:
            bool: True if P2P functionality is enabled, False otherwise.
        """
        result = self._lib.P2PEnable(ctypes.c_char_p(self._repo_path.encode('utf-8')))
        return result > 0
    
    def forward(self, protocol: str, listen_addr: str, target_peer_id: str) -> bool:
        """
        Forward local connections to a remote peer.
        
        This creates a new listener that forwards connections to the specified
        peer over the libp2p network.
        
        Args:
            protocol: The protocol name to use for the forwarding.
            listen_addr: The local address to listen on (e.g. "127.0.0.1:8080").
            target_peer_id: The peer ID to forward connections to.
            
        Returns:
            bool: True if the forwarding was set up successfully, False otherwise.
        """
        result = self._lib.P2PForward(
            ctypes.c_char_p(self._repo_path.encode('utf-8')),
            ctypes.c_char_p(protocol.encode('utf-8')),
            ctypes.c_char_p(listen_addr.encode('utf-8')),
            ctypes.c_char_p(target_peer_id.encode('utf-8'))
        )
        return result > 0
    
    def listen(self, protocol: str, target_addr: str) -> bool:
        """
        Listen for libp2p connections and forward them to a local TCP service.
        
        This exposes a local TCP service to the libp2p network.
        
        Args:
            protocol: The protocol name to use for the listener.
            target_addr: The local address to forward connections to (e.g. "127.0.0.1:8080").
            
        Returns:
            bool: True if the listener was set up successfully, False otherwise.
        """
        result = self._lib.P2PListen(
            ctypes.c_char_p(self._repo_path.encode('utf-8')),
            ctypes.c_char_p(protocol.encode('utf-8')),
            ctypes.c_char_p(target_addr.encode('utf-8'))
        )
        return result > 0
    
    def close(self, protocol: str, listen_addr: str = "", target_peer_id: str = "") -> bool:
        """
        Close a P2P listener or stream.
        
        Args:
            protocol: The protocol name of the listener or stream to close.
            listen_addr: For streams, the local address that the stream listens on.
            target_peer_id: For streams, the peer ID that the stream connects to.
            
        Returns:
            bool: True if the listener or stream was closed successfully, False otherwise.
        """
        result = self._lib.P2PClose(
            ctypes.c_char_p(self._repo_path.encode('utf-8')),
            ctypes.c_char_p(protocol.encode('utf-8')),
            ctypes.c_char_p(listen_addr.encode('utf-8')),
            ctypes.c_char_p(target_peer_id.encode('utf-8'))
        )
        return result > 0
    
    def list_listeners(self) -> Tuple[List[P2PMapping], List[P2PStream]]:
        """
        List all active P2P listeners and streams.
        
        Returns:
            Tuple[List[P2PMapping], List[P2PStream]]: A tuple containing two lists:
            - The first list contains all local and remote listeners (P2PMapping objects)
            - The second list contains all active streams (P2PStream objects)
        """
        result_ptr = self._lib.P2PListListeners(
            ctypes.c_char_p(self._repo_path.encode('utf-8'))
        )
        
        if not result_ptr:
            return [], []
            
        # Convert the C string to a Python string and release memory
        result_str = ctypes.string_at(result_ptr).decode('utf-8')
        self._lib.free(result_ptr)
        
        if not result_str:
            return [], []
            
        # Parse the JSON
        try:
            result = json.loads(result_str)
        except json.JSONDecodeError:
            return [], []
            
        # Extract all listeners (both local and remote)
        listeners = []
        
        # Add local listeners
        for item in result.get('LocalListeners', []):
            listener = P2PMapping(
                protocol=item.get('Protocol', ''),
                listen_address=item.get('ListenAddress', ''),
                target_address=item.get('TargetAddress', '')
            )
            listeners.append(listener)
            
        # Add remote listeners
        for item in result.get('RemoteListeners', []):
            listener = P2PMapping(
                protocol=item.get('Protocol', ''),
                listen_address=item.get('ListenAddress', ''),
                target_address=item.get('TargetAddress', '')
            )
            listeners.append(listener)
            
        # Extract active streams
        streams = []
        for item in result.get('Streams', []):
            stream = P2PStream(
                protocol=item.get('Protocol', ''),
                origin_address=item.get('LocalAddr', ''),
                target_address=item.get('RemoteAddr', '')
            )
            streams.append(stream)
            
        return listeners, streams