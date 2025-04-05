"""
Utilities for working with IPFS Content Identifiers (CIDs).
"""

import re

# Regular expression for matching CID v0 (Qm...)
CID_V0_REGEX = re.compile(r"^Qm[1-9A-Za-z]{44}$")

# Regular expression for matching CID v1
CID_V1_REGEX = re.compile(r"^ba[a-zA-Z2-7]{57}$")

def is_valid_cid(cid: str) -> bool:
    """
    Check if a string is a valid IPFS CID.
    
    Args:
        cid: The Content Identifier to check.
        
    Returns:
        bool: True if the CID is valid, False otherwise.
    """
    if not cid or not isinstance(cid, str):
        return False
    
    # Check for CID v0 (starts with "Qm" and is 46 characters long)
    if CID_V0_REGEX.match(cid):
        return True
    
    # Check for CID v1 (starts with "ba" and is 59 characters long)
    if CID_V1_REGEX.match(cid):
        return True
    
    # Could add more sophisticated validation here
    return False

def format_cid_link(cid: str, gateway: str = "https://ipfs.io/ipfs/") -> str:
    """
    Format a CID as a link through an IPFS gateway.
    
    Args:
        cid: The Content Identifier.
        gateway: The IPFS gateway URL. Defaults to the public ipfs.io gateway.
        
    Returns:
        str: The gateway URL for the CID.
    """
    if not is_valid_cid(cid):
        raise ValueError(f"Invalid CID: {cid}")
    
    # Ensure the gateway URL ends with a slash
    if not gateway.endswith("/"):
        gateway += "/"
    
    return f"{gateway}{cid}"