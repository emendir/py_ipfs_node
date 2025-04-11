# PubSub Functionality in Kubo Python Library

The Kubo Python library provides comprehensive support for IPFS PubSub, allowing you to publish and subscribe to topics on the IPFS network.

## Overview

PubSub (Publish/Subscribe) is a messaging pattern where publishers send messages to topics, and subscribers receive messages from topics they're interested in. IPFS PubSub allows nodes to communicate in real-time across the IPFS network.

## Usage

### Enabling PubSub

PubSub is enabled by default when creating an online IPFS node. You can explicitly control this with the `enable_pubsub` parameter:

```python
from kubo_python import IpfsNode

# Create a node with pubsub enabled (default)
node = IpfsNode(repo_path='/path/to/repo', enable_pubsub=True)

# Create a node without pubsub
node_no_pubsub = IpfsNode(repo_path='/path/to/repo', enable_pubsub=False)

# For ephemeral nodes
ephemeral_node = IpfsNode.ephemeral(enable_pubsub=True)
```

### Subscribing to a Topic

To subscribe to a topic, use the `pubsub_subscribe` method:

```python
subscription = node.pubsub.subscribe("my-topic")
```

This returns an `IPFSSubscription` object that you can use to receive messages.

### Receiving Messages

There are several ways to receive messages:

#### Option 1: Using a callback

```python
def message_callback(message):
    print(f"Received: {message.data.decode('utf-8')} from {message.from_peer}")

subscription.subscribe(message_callback)
```

The callback will be called in a background thread whenever a message arrives.

#### Option 2: Polling for messages

```python
# Get the next message with a timeout (in seconds)
message = subscription.next_message(timeout=1.0)
if message:
    print(f"Received: {message.data.decode('utf-8')}")
```

#### Option 3: Using an iterator

```python
for message in subscription:
    print(f"Received: {message.data.decode('utf-8')}")
    # Note: This iterator uses a 1-second timeout internally
```

### Publishing Messages

To publish a message to a topic:

```python
# Publish a string (will be UTF-8 encoded)
node.pubsub.publish("my-topic", "Hello, world!")

# Publish binary data
node.pubsub.publish("my-topic", b"\x00\x01\x02\x03")
```

### Listing Topics and Peers

```python
# List subscribed topics
topics = node.pubsub.list_topics()
print(f"Subscribed topics: {topics}")

# List peers participating in pubsub (all topics)
peers = node.pubsub.list_peers()
print(f"Pubsub peers: {peers}")

# List peers for a specific topic
topic_peers = node.pubsub.list_peers("my-topic")
print(f"Peers in 'my-topic': {topic_peers}")
```

### Unsubscribing

```python
# Close a subscription when you're done with it
subscription.close()

# Or using a context manager
with node.pubsub.subscribe("my-topic") as subscription:
    # Use subscription here
    pass  # Automatically closed when the block exits
```

## Message Objects

Messages received from subscriptions are represented by `IPFSMessage` objects with the following properties:

- `from_peer`: The peer ID of the sender
- `data`: The message payload as bytes
- `topic_id`: The topic the message was published to
- `seqno`: Optional sequence number (bytes)
- `topics`: Optional list of topics (if the message was published to multiple topics)

Example:

```python
def process_message(message):
    print(f"From: {message.from_peer}")
    print(f"Topic: {message.topic_id}")
    try:
        # Attempt to decode as UTF-8 text
        print(f"Data: {message.data.decode('utf-8')}")
    except UnicodeDecodeError:
        # Fall back to hexadecimal representation for binary data
        print(f"Data (hex): {message.data.hex()}")
```

## Example: Chat Application

See the `examples/chat_app.py` script for a complete example of building a chat application using IPFS PubSub.

## Considerations and Limitations

- PubSub requires the IPFS node to be online (`online=True`).
- Messages are not persisted - only online peers receive the messages.
- Peers need to be connected to the IPFS network to participate.
- For better reliability, you may need to manually connect to specific peers using `node.connect_to_peer()`.
- Large messages may be fragmented or dropped by the network.