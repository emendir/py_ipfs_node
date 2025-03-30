package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"sync"
	"time"
	"unsafe"

	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/boxo/coreiface/options"
	ipath "github.com/ipfs/boxo/coreiface/path"
	"github.com/ipfs/boxo/files"
	cidlib "github.com/ipfs/go-cid"
	"github.com/ipfs/kubo/config"
	"github.com/ipfs/kubo/core"
	"github.com/ipfs/kubo/core/coreapi"
	"github.com/ipfs/kubo/core/node/libp2p"
	"github.com/ipfs/kubo/plugin/loader"
	"github.com/ipfs/kubo/repo/fsrepo"
	"github.com/libp2p/go-libp2p/core/peer"
)

var plugins *loader.PluginLoader

// PubSub subscription management
var (
	subscriptions      = make(map[int64]subscriptionInfo)
	subscriptionsMutex sync.Mutex
	nextSubID         int64 = 1
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
	node         *core.IpfsNode // Keep reference to node to prevent premature closing
	api          iface.CoreAPI
}

func init() {
	// Load plugins
	plugins, _ = loader.NewPluginLoader("")
	plugins.Initialize()
	plugins.Inject()
}

// CreateRepo initializes a new IPFS repository
//export CreateRepo
func CreateRepo(repoPath *C.char) C.int {
	path := C.GoString(repoPath)
	
	// Check if repo already exists
	if fsrepo.IsInitialized(path) {
		return C.int(0) // Already initialized
	}
	
	// Create and initialize a new config with default settings
	cfg, err := config.Init(os.Stdin, 2048)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error initializing IPFS config: %s\n", err)
		return C.int(-1)
	}
	
	// Set default bootstrap nodes
	cfg.Bootstrap = config.DefaultBootstrapAddresses
	
	// Initialize the repo
	err = fsrepo.Init(path, cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error initializing IPFS repo: %s\n", err)
		return C.int(-2)
	}
	
	return C.int(1) // Success
}

// SpawnNode creates an IPFS node
func spawnNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	fmt.Fprintf(os.Stderr, "DEBUG: Opening repo at %s\n", repoPath)
	// Open the repo
	repo, err := fsrepo.Open(repoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Error opening repo: %v\n", err)
		return nil, nil, err
	}

	// Construct the node
	nodeOptions := &core.BuildCfg{
		Online:  true,
		Routing: libp2p.DHTOption, // This is the default routing mode
		Repo:    repo,
	}

	fmt.Fprintf(os.Stderr, "DEBUG: Creating new IPFS node\n")
	ctx := context.Background()
	node, err := core.NewNode(ctx, nodeOptions)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Error creating node: %v\n", err)
		repo.Close()
		return nil, nil, err
	}

	// Construct the API
	fmt.Fprintf(os.Stderr, "DEBUG: Creating CoreAPI\n")
	api, err := coreapi.NewCoreAPI(node)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Error creating API: %v\n", err)
		node.Close()
		return nil, nil, err
	}

	fmt.Fprintf(os.Stderr, "DEBUG: Node and API created successfully\n")
	return api, node, nil
}

// AddFile adds a file to IPFS
//export AddFile
func AddFile(repoPath, filePath *C.char) *C.char {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	file := C.GoString(filePath)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Adding file from path %s using repo %s\n", file, path)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return nil
	}
	defer func() {
		fmt.Fprintf(os.Stderr, "DEBUG: Closing IPFS node\n")
		node.Close()
	}()
	
	// Open the file
	f, err := os.Open(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening file: %s\n", err)
		return nil
	}
	defer f.Close()
	
	// Add the file to IPFS
	fileInfo, err := f.Stat()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting file info: %s\n", err)
		return nil
	}
	
	var fileNode files.Node
	
	if fileInfo.IsDir() {
		// Handle directory
		var dirErr error
		fileNode, dirErr = files.NewSerialFile(file, true, fileInfo)
		if dirErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating directory node: %s\n", dirErr)
			return nil
		}
	} else {
		// Handle file
		fmt.Fprintf(os.Stderr, "DEBUG: Creating file node for %s\n", file)
		var fileErr error
		fileNode, fileErr = files.NewReaderPathFile(file, f, fileInfo)
		if fileErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating file node: %s\n", fileErr)
			return nil
		}
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: Adding file to IPFS\n")
	resolved, err := api.Unixfs().Add(
		ctx,
		fileNode,
		options.Unixfs.Pin(true),
	)
	
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error adding file to IPFS: %s\n", err)
		return nil
	}
	
	cid := resolved.Cid().String()
	fmt.Fprintf(os.Stderr, "DEBUG: File added with CID: %s\n", cid)
	
	// Return the CID as a C string
	// Note: This allocates memory that should be freed by the caller
	return C.CString(cid)
}

// FreeString is a no-op for now - we'll let Go's garbage collection handle the memory
//export FreeString
func FreeString(str *C.char) {
	fmt.Fprintf(os.Stderr, "DEBUG: FreeString called (NO-OP) for pointer %p\n", unsafe.Pointer(str))
	// We're not actually freeing memory here to avoid the crash
	// C.free(unsafe.Pointer(str)) 
}

// GetFile retrieves a file from IPFS
//export GetFile
func GetFile(repoPath, cidStr, destPath *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)
	dest := C.GoString(destPath)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Getting file with CID %s to %s using repo %s\n", cid, dest, path)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(-1)
	}
	defer func() {
		fmt.Fprintf(os.Stderr, "DEBUG: Closing IPFS node\n")
		node.Close()
	}()
	
	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error decoding CID: %s\n", err)
		return C.int(-2)
	}
	
	ipfsPath := ipath.IpfsPath(decodedCid)
	
	// Get the node from IPFS
	fmt.Fprintf(os.Stderr, "DEBUG: Retrieving content from IPFS\n")
	fileNode, err := api.Unixfs().Get(ctx, ipfsPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting file from IPFS: %s\n", err)
		return C.int(-2)
	}
	
	// Create the destination directory if it doesn't exist
	err = os.MkdirAll(filepath.Dir(dest), 0755)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error creating destination directory: %s\n", err)
		return C.int(-3)
	}
	
	// Handle file vs directory
	file, ok := fileNode.(files.File)
	if !ok {
		fmt.Fprintf(os.Stderr, "Retrieved node is not a file\n")
		return C.int(-4)
	}
	
	// Read file content
	fmt.Fprintf(os.Stderr, "DEBUG: Reading file content\n")
	content, err := ioutil.ReadAll(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file content: %s\n", err)
		return C.int(-5)
	}
	
	// Write the file to the destination
	fmt.Fprintf(os.Stderr, "DEBUG: Writing content to destination file\n")
	err = ioutil.WriteFile(dest, content, 0644)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error writing file: %s\n", err)
		return C.int(-6)
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: File retrieved successfully\n")
	return C.int(0) // Success
}

// ConnectToPeer connects to a peer
//export ConnectToPeer
func ConnectToPeer(repoPath, peerAddr *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	addr := C.GoString(peerAddr)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Connecting to peer %s using repo %s\n", addr, path)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(-1)
	}
	defer func() {
		fmt.Fprintf(os.Stderr, "DEBUG: Closing IPFS node\n")
		node.Close()
	}()
	
	// Parse the peer address
	fmt.Fprintf(os.Stderr, "DEBUG: Parsing peer address\n")
	peerInfo, err := peer.AddrInfoFromString(addr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing peer address: %s\n", err)
		return C.int(-2)
	}
	
	// Connect to the peer
	fmt.Fprintf(os.Stderr, "DEBUG: Connecting to peer\n")
	err = api.Swarm().Connect(ctx, *peerInfo)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error connecting to peer: %s\n", err)
		return C.int(-3)
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: Connected to peer successfully\n")
	return C.int(0) // Success
}

// PubSubEnable enables pubsub on an IPFS node configuration
//export PubSubEnable
func PubSubEnable(repoPath *C.char) C.int {
	path := C.GoString(repoPath)

	// Ensure repo exists
	if !fsrepo.IsInitialized(path) {
		fmt.Fprintf(os.Stderr, "Error: Repository not initialized at %s\n", path)
		return C.int(-1)
	}

	// Open the repo config
	repo, err := fsrepo.Open(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening repository: %s\n", err)
		return C.int(-2)
	}
	defer repo.Close()

	// Get the config
	cfg, err := repo.Config()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting repository config: %s\n", err)
		return C.int(-3)
	}

	// Enable experimental features
	cfg.Experimental.Libp2pStreamMounting = true
	cfg.Experimental.P2pHttpProxy = true
	
	// IPFS API doesn't expose Pubsub setting in the new structure
	// Directly modify the raw config
	
	// Convert cfg to plain config map
	cfgMap := map[string]interface{}{}
	cfgRaw, err := json.Marshal(cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling config: %s\n", err)
		return C.int(-5)
	}
	
	err = json.Unmarshal(cfgRaw, &cfgMap)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error unmarshaling config map: %s\n", err)
		return C.int(-6)
	}
	
	// Ensure the Pubsub field is set in Experimental section
	if expMap, ok := cfgMap["Experimental"].(map[string]interface{}); ok {
		expMap["Pubsub"] = true
		fmt.Fprintf(os.Stderr, "DEBUG: Enabled Pubsub in Experimental map\n")
	} else {
		// Create Experimental map if it doesn't exist
		cfgMap["Experimental"] = map[string]interface{}{
			"Pubsub": true,
		}
		fmt.Fprintf(os.Stderr, "DEBUG: Created new Experimental map with Pubsub enabled\n")
	}
	
	// Marshal back to JSON
	cfgRaw, err = json.Marshal(cfgMap)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error marshaling modified config: %s\n", err)
		return C.int(-7)
	}
	
	// Create a new config to override the existing one
	var newCfg config.Config
	if err := json.Unmarshal(cfgRaw, &newCfg); err != nil {
		fmt.Fprintf(os.Stderr, "Error unmarshaling to config: %s\n", err)
		return C.int(-8)
	}
	
	// Set the updated config
	if err := repo.SetConfig(&newCfg); err != nil {
		fmt.Fprintf(os.Stderr, "Error setting updated config: %s\n", err)
		return C.int(-9)
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: Updated config successfully\n")

	return C.int(0)
}

// PubSubListTopics lists the topics the node is subscribed to
//export PubSubListTopics
func PubSubListTopics(repoPath *C.char) *C.char {
	ctx := context.Background()
	path := C.GoString(repoPath)

	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	defer node.Close()

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
//export PubSubPublish
func PubSubPublish(repoPath, topic *C.char, data unsafe.Pointer, dataLen C.int) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)
	
	// Convert data to Go byte slice
	dataBytes := C.GoBytes(data, dataLen)

	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(-1)
	}
	defer node.Close()

	// Publish message
	err = api.PubSub().Publish(ctx, topicStr, dataBytes)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error publishing to topic: %s\n", err)
		return C.int(-2)
	}

	return C.int(0)
}

// PubSubSubscribe subscribes to a topic
//export PubSubSubscribe
func PubSubSubscribe(repoPath, topic *C.char) C.longlong {
	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)

	// Spawn a node
	ctx, cancel := context.WithCancel(context.Background())
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		cancel()
		return C.longlong(-1)
	}

	// Subscribe to topic
	subscription, err := api.PubSub().Subscribe(ctx, topicStr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error subscribing to topic: %s\n", err)
		node.Close()
		cancel()
		return C.longlong(-2)
	}

	// Generate subscription ID
	subscriptionsMutex.Lock()
	subID := nextSubID
	nextSubID++
	
	// Store subscription
	subscriptions[subID] = subscriptionInfo{
		topic:        topicStr,
		subscription: subscription,
		messageQueue: []Message{},
		mutex:        sync.Mutex{},
		ctx:          ctx,
		cancel:       cancel,
		node:         node,
		api:          api,
	}
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
//export PubSubNextMessage
func PubSubNextMessage(subID C.longlong) *C.char {
	id := int64(subID)

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

	return C.CString(string(messageJSON))
}

// PubSubUnsubscribe unsubscribes from a topic
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

	// Close the node
	if err := subInfo.node.Close(); err != nil {
		fmt.Fprintf(os.Stderr, "Error closing node: %s\n", err)
	}

	// Remove from map
	delete(subscriptions, id)

	return C.int(0)
}

// PubSubPeers lists peers participating in a topic
//export PubSubPeers
func PubSubPeers(repoPath, topic *C.char) *C.char {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	topicStr := C.GoString(topic)

	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	defer node.Close()

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

// GetNodeID gets the ID of the IPFS node
//export GetNodeID
func GetNodeID(repoPath *C.char) *C.char {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.CString("")
	}
	defer node.Close()
	
	// Get the node ID
	id, err := api.Key().Self(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting node ID: %s\n", err)
		return C.CString("")
	}
	
	return C.CString(id.ID().String())
}

func main() {
	// This is required but we don't need to do anything here
}