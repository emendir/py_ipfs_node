"""
Tests for the Kubo Python library utilities.
"""

import unittest
import sys
import os

# Add the parent directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from kubo_python.utils import cid_utils, peer_utils

class TestCIDUtils(unittest.TestCase):
    """Tests for CID utilities."""
    
    def test_valid_cid_v0(self):
        """Test validation of CID v0."""
        valid_cid = "QmY7Yh4UquoXHLPFo2XbhXkhBvFoPwmQUSa92pxnxjQuPU"
        self.assertTrue(cid_utils.is_valid_cid(valid_cid))
    
    def test_invalid_cid(self):
        """Test validation of invalid CIDs."""
        invalid_cids = [
            "not-a-cid",
            "Qm123",  # Too short
            "baInvalidCIDv1",
            "",
            None,
        ]
        for cid in invalid_cids:
            self.assertFalse(cid_utils.is_valid_cid(cid))
    
    def test_format_cid_link(self):
        """Test formatting CID as a gateway link."""
        cid = "QmY7Yh4UquoXHLPFo2XbhXkhBvFoPwmQUSa92pxnxjQuPU"
        link = cid_utils.format_cid_link(cid)
        self.assertEqual(link, f"https://ipfs.io/ipfs/{cid}")
        
        # Test with custom gateway
        custom_gateway = "https://gateway.pinata.cloud/ipfs/"
        custom_link = cid_utils.format_cid_link(cid, custom_gateway)
        self.assertEqual(custom_link, f"{custom_gateway}{cid}")
        
        # Test with gateway without trailing slash
        no_slash_gateway = "https://dweb.link/ipfs"
        no_slash_link = cid_utils.format_cid_link(cid, no_slash_gateway)
        self.assertEqual(no_slash_link, f"{no_slash_gateway}/{cid}")

class TestPeerUtils(unittest.TestCase):
    """Tests for peer utilities."""
    
    def test_valid_multiaddr(self):
        """Test validation of multiaddresses."""
        valid_addrs = [
            "/ip4/127.0.0.1/tcp/4001/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN",
            "/dnsaddr/bootstrap.libp2p.io/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN",
        ]
        for addr in valid_addrs:
            self.assertTrue(peer_utils.is_valid_multiaddr(addr))
    
    def test_invalid_multiaddr(self):
        """Test validation of invalid multiaddresses."""
        invalid_addrs = [
            "not-a-multiaddr",
            "ip4/127.0.0.1",  # Missing leading slash
            "",
            None,
        ]
        for addr in invalid_addrs:
            self.assertFalse(peer_utils.is_valid_multiaddr(addr))
    
    def test_extract_peer_id(self):
        """Test extracting peer ID from multiaddress."""
        addr = "/ip4/127.0.0.1/tcp/4001/p2p/QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN"
        peer_id = peer_utils.extract_peer_id(addr)
        self.assertEqual(peer_id, "QmNnooDu7bfjPFoTZYxMNLWUQJyrVwtbZg5gBMjTezGAJN")
        
        # Test with no peer ID
        no_peer_addr = "/ip4/127.0.0.1/tcp/4001"
        no_peer_id = peer_utils.extract_peer_id(no_peer_addr)
        self.assertEqual(no_peer_id, "")
    
    def test_bootstrap_peers(self):
        """Test getting bootstrap peers."""
        peers = peer_utils.get_bootstrap_peers()
        self.assertTrue(len(peers) > 0)
        for peer in peers:
            self.assertTrue(peer_utils.is_valid_multiaddr(peer))

def run():
    unittest.main()
if __name__ == "__main__":
    run()
