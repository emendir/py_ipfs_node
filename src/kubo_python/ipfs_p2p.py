import ctypes
import json
from typing import List, Dict, Optional, Tuple, Any, Union
from ipfs_toolkit_generics import BaseTcp
from .lib import libkubo, c_str, from_c_str, ffi


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


class NodeTcp(BaseTcp):
    """
    Provides P2P stream mounting functionality for IPFS nodes.

    Stream mounting allows you to expose local TCP services to the libp2p network
    and connect to remote TCP services exposed by other nodes.
    """
    def __init__(self, node):
        self._node = node
        self._repo_path = self._node._repo_path
    def _enable_p2p(self) -> bool:
        """Enable p2p functionality in the IPFS configuration."""

        repo_path = c_str(self._repo_path.encode('utf-8'))
        result = libkubo.P2PEnable(repo_path)

        if result <= 0:
            print(f"Warning: Could not enable p2p functionality ({result})")
            return False
        return True

    def open_sender(self, protocol: str, listen_addr: str, target_peer_id: str) -> bool:
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
        result = libkubo.P2PForward(
            c_str(self._repo_path.encode('utf-8')),
            c_str(protocol.encode('utf-8')),
            c_str(listen_addr.encode('utf-8')),
            c_str(target_peer_id.encode('utf-8'))
        )
        return result > 0

    def open_listener(self, protocol: str, target_addr: str) -> bool:
        """
        Listen for libp2p connections and forward them to a local TCP service.

        This exposes a local TCP service to the libp2p network.

        Args:
            protocol: The protocol name to use for the listener.
            target_addr: The local address to forward connections to (e.g. "127.0.0.1:8080").

        Returns:
            bool: True if the listener was set up successfully, False otherwise.
        """
        result = libkubo.P2PListen(
            c_str(self._repo_path.encode('utf-8')),
            c_str(protocol.encode('utf-8')),
            c_str(target_addr.encode('utf-8'))
        )
        return result > 0

    def close_sender(self, proto: str = None, port: int = None, peer_id: str = None) -> int:
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

    def close_listener(self, proto: str = None, port: int = None) -> int:
        """
        Close a specific TCP listening connection, optionally filtered by protocol or port.

        Args:
            proto: Optional protocol filter
            port: Optional port filter

        Returns:
            int: Number of listening connections closed
        """
        return self.close_tcp_connection(proto, port)

    def close_streams(self, protocol: str, listen_addr: str = "", target_peer_id: str = "") -> bool:
        """
        Close a P2P listener or stream.

        Args:
            protocol: The protocol name of the listener or stream to close.
            listen_addr: For streams, the local address that the stream listens on.
            target_peer_id: For streams, the peer ID that the stream connects to.

        Returns:
            bool: True if the listener or stream was closed successfully, False otherwise.
        """
        result = libkubo.P2PClose(
            c_str(self._repo_path.encode('utf-8')),
            c_str(protocol.encode('utf-8')),
            c_str(listen_addr.encode('utf-8')),
            c_str(target_peer_id.encode('utf-8'))
        )
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

        repo_path = c_str(self._repo_path.encode('utf-8'))

        # Format protocol filter
        proto_c = c_str((proto if proto else "").encode('utf-8'))

        # Format port filter
        listen_addr = f"/ip4/127.0.0.1/tcp/{port}" if port is not None else ""
        listen_addr_c = c_str(listen_addr.encode('utf-8'))

        # Format peer ID filter
        peer_id_c = c_str((peer_id if peer_id else "").encode('utf-8'))

        result = libkubo.P2PClose(
            repo_path, proto_c, listen_addr_c, peer_id_c)
        return result

    def close_all_tcp_forwarding_connections(self) -> int:
        """
        Close all TCP forwarding connections.

        Returns:
            int: Number of forwarding connections closed
        """
        return self.close_tcp_connection()

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

        # Get the listeners and streams
        listeners, streams = self.list_listeners()

        # Convert to dictionary format
        result = {
            "LocalListeners": [listener.__dict__ for listener in listeners],
            "RemoteStreams": [stream.__dict__ for stream in streams]
        }

        return result
    def list_listeners(self) -> Tuple[List[P2PMapping], List[P2PStream]]:
        """
        List all active P2P listeners and streams.

        Returns:
            Tuple[List[P2PMapping], List[P2PStream]]: A tuple containing two lists:
            - The first list contains all local and remote listeners (P2PMapping objects)
            - The second list contains all active streams (P2PStream objects)
        """
        result_ptr = libkubo.P2PListListeners(
            c_str(self._repo_path.encode('utf-8'))
        )

        if not result_ptr:
            return [], []

        # Convert the C string to a Python string and release memory
        result_str = from_c_str(result_ptr)
        libkubo.free(result_ptr)

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
    def close(self):
        pass