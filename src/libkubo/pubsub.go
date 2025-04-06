package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sync"
	"time"
	"unsafe"

	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/boxo/coreiface/options"
	"github.com/libp2p/go-libp2p/core/peer"
)

// PubSub subscription management
var (
	subscriptions      = make(map[int64]*subscriptionInfo) // <-- pointer
	subscriptionsMutex sync.Mutex
	nextSubID          int64 = 1
)

// Message represents a pubsub message
type Message struct {
	From    string   `json:"from"`
	Data    []byte   `json:"data"`
	Seqno   []byte   `json:"seqno,omitempty"`
	Topics  []string `json:"topics,omitempty"`
	TopicID string   `json:"topicID"`
}

// subscriptionInfo holds information about an active subscription
type subscriptionInfo struct {
	topic        string
	subscription iface.PubSubSubscription
	messageQueue []Message
	mutex        sync.Mutex
	ctx          context.Context
	cancel       context.CancelFunc
	repoPath     string // Store repo path instead of node reference
}

// PubSubListTopics lists the topics the node is subscribed to
//
//export PubSubListTopics
func PubSubListTopics(repoPath *C.char) *C.char {
	ctx := context.Background()
	path := C.GoString(repoPath)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error acquiring node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	defer ReleaseNode(path)

	// List topics
	topics, err := api.PubSub().Ls(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error listing topics: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	// Convert to JSON
	topicsJSON, err := json.Marshal(topics)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling topics to JSON: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	return C.CString(string(topicsJSON))
}

// PubSubPublish publishes a message to a topic
//
//export PubSubPublish
func PubSubPublish(repoPath, topic *C.char, data unsafe.Pointer, dataLen C.int) C.int {
	ctx := context.Background()

	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)

	// Convert data to Go byte slice
	dataBytes := C.GoBytes(data, dataLen)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error acquiring node: %s\n", err)
		return C.int(-1)
	}
	defer ReleaseNode(path)

	// Publish message
	err = api.PubSub().Publish(ctx, topicStr, dataBytes)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error publishing to topic: %s\n", err)
		return C.int(-2)
	}

	return C.int(0)
}

// PubSubSubscribe subscribes to a topic
//
//export PubSubSubscribe
func PubSubSubscribe(repoPath, topic *C.char) C.longlong {
	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error acquiring node: %s\n", err)
		return C.longlong(-1)
	}
	// Note: We don't release the node here because the subscription needs it
	// The node will be released when the subscription is closed

	// Create a context with cancel for this subscription
	ctx, cancel := context.WithCancel(context.Background())

	// Subscribe to topic
	subscription, err := api.PubSub().Subscribe(ctx, topicStr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error subscribing to topic: %s\n", err)
		ReleaseNode(path) // Release the node since we failed
		cancel()
		return C.longlong(-2)
	}

	// Generate subscription ID
	subscriptionsMutex.Lock()
	subID := nextSubID
	nextSubID++

	// Store subscription reference
	subInfo := &subscriptionInfo{
		topic:        topicStr,
		subscription: subscription,
		messageQueue: []Message{},
		mutex:        sync.Mutex{},
		ctx:          ctx,
		cancel:       cancel,
		repoPath:     path,
	}
	subscriptions[subID] = subInfo
	subscriptionsMutex.Unlock()

	// Start message receiver goroutine
	go messageReceiver(subID, subscription, topicStr)

	return C.longlong(subID)
}

// messageReceiver continuously receives messages from a subscription and adds them to the queue
func messageReceiver(subID int64, subscription iface.PubSubSubscription, topic string) {
	subscriptionsMutex.Lock()
	subInfo, exists := subscriptions[subID]
	subscriptionsMutex.Unlock()

	if !exists {
		return
	}

	// Process messages until context is canceled
	for {
		select {
		case <-subInfo.ctx.Done():
			return
		default:
			// Try to receive a message with timeout
			msgCtx, msgCancel := context.WithTimeout(subInfo.ctx, 100*time.Millisecond)
			msg, err := subscription.Next(msgCtx)
			msgCancel()

			if err != nil {
				// Context timeout or error
				if err != context.DeadlineExceeded && err != context.Canceled {
					fmt.Fprintf(os.Stderr, "Error receiving message: %s\n", err)
				}
				// Small sleep to avoid tight CPU loop
				time.Sleep(10 * time.Millisecond)
				continue
			}

			// Convert message to our struct
			message := Message{
				From:    msg.From().String(),
				Data:    msg.Data(),
				TopicID: topic,
			}
			// fmt.Fprintf(os.Stderr, "SubID: %d Received message! \n", subID)

			if msg.Seq() != nil {
				message.Seqno = msg.Seq()
			}

			if len(msg.Topics()) > 0 {
				message.Topics = msg.Topics()
			}

			// Add message to queue
			subInfo.mutex.Lock()
			subInfo.messageQueue = append(subInfo.messageQueue, message)
			subInfo.mutex.Unlock()
		}
	}
}

// PubSubNextMessage gets the next message from a subscription
//
//export PubSubNextMessage
func PubSubNextMessage(subID C.longlong) *C.char {
	id := int64(subID)
	// fmt.Fprintf(os.Stderr, "Getting next message..\n")

	subscriptionsMutex.Lock()
	subInfo, exists := subscriptions[id]
	subscriptionsMutex.Unlock()

	if !exists {
		fmt.Fprintf(os.Stderr, "Error: Subscription %d not found\n", id)
		return nil
	}

	// Check if there are messages in the queue
	subInfo.mutex.Lock()
	defer subInfo.mutex.Unlock()

	if len(subInfo.messageQueue) == 0 {
		// No messages available
		// fmt.Fprintf(os.Stderr, "SubID: %d No message available.\n", subID)
		return nil
	}

	// Get the first message
	message := subInfo.messageQueue[0]
	// Remove it from the queue
	subInfo.messageQueue = subInfo.messageQueue[1:]

	// Convert to JSON
	messageJSON, err := json.Marshal(message)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling message to JSON: %s\n", err)
		return nil
	}
	// fmt.Fprintf(os.Stderr, "Got next message! %s\n", messageJSON)

	return C.CString(string(messageJSON))
}

// PubSubUnsubscribe unsubscribes from a topic
//
//export PubSubUnsubscribe
func PubSubUnsubscribe(subID C.longlong) C.int {
	id := int64(subID)

	subscriptionsMutex.Lock()
	defer subscriptionsMutex.Unlock()

	subInfo, exists := subscriptions[id]
	if !exists {
		fmt.Fprintf(os.Stderr, "Error: Subscription %d not found\n", id)
		return C.int(-1)
	}

	// Cancel the context to stop message receiving
	subInfo.cancel()

	// Close the subscription
	if err := subInfo.subscription.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "Error closing subscription: %s\n", err)
	}

	// Release the node associated with this subscription
	ReleaseNode(subInfo.repoPath)

	// Remove from map
	delete(subscriptions, id)

	return C.int(0)
}

// PubSubPeers lists peers participating in a topic
//
//export PubSubPeers
func PubSubPeers(repoPath, topic *C.char) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error acquiring node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	defer ReleaseNode(path)

	// List peers
	var peers []peer.ID
	if topicStr == "" {
		// List all pubsub peers
		peers, err = api.PubSub().Peers(ctx)
	} else {
		// List peers for specific topic
		peers, err = api.PubSub().Peers(ctx, options.PubSub.Topic(topicStr))
	}

	if err != nil {
		fmt.Fprintf(os.Stderr, "Error listing peers: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	// Convert to string array
	peerStrs := make([]string, len(peers))
	for i, p := range peers {
		peerStrs[i] = p.String()
	}

	// Convert to JSON
	peersJSON, err := json.Marshal(peerStrs)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling peers to JSON: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	return C.CString(string(peersJSON))
}
