import threading
import time
import socket
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kubo_python import IpfsNode

import pytest
def test_preparations():
    pytest.node_1 = IpfsNode.ephemeral(online=True, enable_pubsub=True)
    pytest.node_2 = IpfsNode.ephemeral(online=True, enable_pubsub=True)
    
def test_connect():
    pytest.node_2.peers.connect(f"/p2p/{pytest.node_1.peer_id}")

def test_findpeer():
    multi_addresses = pytest.node_2.peers.find(pytest.node_1.peer_id)
    print("MultiAdresses",multi_addresses)
    if len (multi_addresses) > 1:
        print("Success!")
    else:
        print("Failure.")
def test_list_peers():
    node_2_peers = [
        multiaddr.split("/")[-1] for multiaddr in pytest.node_2.peers.list()
    ]
    # print("Peers", node_2_peers)
    success = pytest.node_1.peer_id in node_2_peers
    print("List peers", success)
def test_cleanup():
    # Clean up
    pytest.node_1.close()
    pytest.node_2.close()
def run():
    test_preparations()
    test_findpeer()
    test_connect()
    test_findpeer()
    test_list_peers()
    test_cleanup()

    


if __name__ == "__main__":
    run()
