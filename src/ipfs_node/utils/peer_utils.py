"""
Utilities for working with IPFS peer addresses and connections.
"""

import re

# Regular expression for matching multiaddress format
MULTIADDR_REGEX = re.compile(r"^(/[^/]+)+$")

# Regular expression for matching peer ID format (with multiaddress)
PEER_ID_REGEX = re.compile(r"/p2p/([a-zA-Z0-9]+)$")

def is_valid_multiaddr(addr: str) -> bool:
    """
    Check if a string is a valid IPFS multiaddress.
    
    Args:
        addr: The multiaddress to check.
        
    Returns:
        bool: True if the multiaddress is valid, False otherwise.
    """
    if not addr or not isinstance(addr, str):
        return False
    
    # Basic check for multiaddress format
    return bool(MULTIADDR_REGEX.match(addr))

def extract_peer_id(multiaddr: str) -> str:
    """
    Extract the peer ID from a multiaddress.
    
    Args:
        multiaddr: The multiaddress containing a peer ID.
        
    Returns:
        str: The peer ID, or an empty string if not found.
    """
    if not is_valid_multiaddr(multiaddr):
        return ""
    
    # Find the peer ID component
    match = PEER_ID_REGEX.search(multiaddr)
    if match:
        return match.group(1)
    
    return ""

def get_bootstrap_peers() -> list:
    """
    Get a list of default IPFS bootstrap peers.
    
    Returns:
        list: A list of multiaddresses for the default bootstrap peers.
    """
    return [
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmQCU2EcMqAqQPR2i9bChDtGNJchTbq5TbXJJ16u19uLTa",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmbLHAnMoJPWSCR5Zhtx6BHJX9KiKNN6tpvbUcqanj75Nb",
        "/dnsaddr/bootstrap.libp2p.io/p2p/QmcZf59bWwK5XFi76CZX8cbJ4BhTzzA3gU1ZjYZcYW3dwt",
        "/ip4/104.131.131.82/tcp/4001/p2p/QmaCpDMGvV2BGHeYERUEnRQAwe3N8SzbUtfsmvsqQLuvuJ",
    ]