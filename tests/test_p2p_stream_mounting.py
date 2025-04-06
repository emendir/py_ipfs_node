import threading
import time
import socket
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from kubo_python import IpfsNode


def start_echo_server(port):
    """Start a simple echo server."""
    def handle_client(sock, addr):
        try:
            while True:
                data = sock.recv(1024)
                if not data:
                    break
                sock.sendall(data)
        finally:
            sock.close()

    def server_thread():
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('127.0.0.1', port))
        server_socket.listen(5)
        print(f"[SERVER] Echo server listening on port {port}")
        while True:
            client, addr = server_socket.accept()
            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

    thread = threading.Thread(target=server_thread, daemon=True)
    thread.start()
    return thread


def run():
    # Setup server node
    server_node = IpfsNode.ephemeral(online=True, enable_pubsub=True)
    protocol = "test-protocol"
    echo_port = 7777

    # Start echo server on server node
    start_echo_server(echo_port)

    # Listen for incoming P2P connections on the server
    assert server_node.listen(protocol, f"/ip4/127.0.0.1/tcp/{echo_port}")
    print(f"[SERVER] Listening for P2P on protocol {protocol}")

    # Setup client node
    client_node = IpfsNode.ephemeral(online=True, enable_pubsub=True)

    # Optionally, attempt direct connection
    try:
        client_node.connect_to_peer(f"/p2p/{server_node.peer_id}")
    except Exception as e:
        print(f"[CLIENT] Could not directly connect: {e}")

    # Forward P2P traffic from client to server
    client_port = 8888
    assert client_node.forward(protocol, f"/ip4/127.0.0.1/tcp/{client_port}", server_node.peer_id)
    print(f"[CLIENT] Forwarding {protocol} -> server {server_node.peer_id}")

    # Allow some time for things to set up
    time.sleep(2)

    # Send test message through the forwarded TCP port
    test_message = "Hello through P2P!"
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(("127.0.0.1", client_port))
    client_socket.sendall(test_message.encode("utf-8"))

    response = client_socket.recv(1024).decode("utf-8")
    client_socket.close()

    # Check the response
    print(f"[TEST] Sent: {test_message}")
    print(f"[TEST] Received: {response}")
    assert response == test_message, "Response did not match sent message!"

    # Clean up
    server_node.close_streams(protocol)
    server_node.close()
    client_node.close_streams(protocol)
    client_node.close()
    print("[TEST] Test passed and cleaned up successfully.")


if __name__ == "__main__":
    run()
