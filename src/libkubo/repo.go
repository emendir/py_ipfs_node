package main

// #include <stdlib.h>
import "C"

import (
	"context"
	// "encoding/json"
	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/kubo/config"
	"github.com/ipfs/kubo/core"
	"github.com/ipfs/kubo/core/coreapi"
	nodep2p "github.com/ipfs/kubo/core/node/libp2p"
	"github.com/ipfs/kubo/plugin/loader"
	"github.com/ipfs/kubo/repo/fsrepo"
	// "github.com/libp2p/go-libp2p/core/peer"
	"log"
	"os"
	"runtime"
	"sync"
)

func init() {
	// f, err := os.OpenFile("kubo.log", os.O_APPEND|os.O_CREATE|os.O_WRONLY, 0644)
	// if err == nil {
	// 	log.SetOutput(f)
	// 	log.SetPrefix("IPFS: ")
	// 	log.Println("DEBUG: Logging to file now")
	// } else {
	// 	// Optional fallback
	// 	log.Printf("Failed to open log file: %v", err)
	// }
}

var plugins *loader.PluginLoader

// NodeInfo holds the active IPFS node and API instance
type NodeInfo struct {
	API  iface.CoreAPI
	Node *core.IpfsNode
	// We count references to know when to safely close a node
	RefCount int
}

// Registry for active nodes, indexed by repo path
var (
	activeNodes      = make(map[string]*NodeInfo)
	activeNodesMutex sync.Mutex
)

func init() {
	// Load plugins
	plugins, _ = loader.NewPluginLoader("")
	plugins.Initialize()
	plugins.Inject()
}

// CreateRepo initializes a new IPFS repository
//
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
		log.Printf("Error initializing IPFS config: %s\n", err)
		return C.int(-1)
	}

	// Set default bootstrap nodes
	cfg.Bootstrap = config.DefaultBootstrapAddresses
	if os.Getenv("ANDROID_ROOT") != "" || runtime.GOOS == "android" {
		log.Printf("DEBUG: Detected Android environment, using Android-specific configuration\n")
		cfg.Swarm.ResourceMgr.Enabled = config.False
	}

	// Initialize the repo
	err = fsrepo.Init(path, cfg)
	if err != nil {
		log.Printf("Error initializing IPFS repo: %s\n", err)
		return C.int(-2)
	}
	return C.int(1) // Success
}

// AcquireNode gets or creates an IPFS node, increasing its reference count
func AcquireNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()

	// Check if we already have an active node for this repo
	if nodeInfo, exists := activeNodes[repoPath]; exists {
		// log.Printf("DEBUG: Reusing existing node for repo %s (refcount: %d -> %d)\n",
		// repoPath, nodeInfo.RefCount, nodeInfo.RefCount+1)
		nodeInfo.RefCount++
		return nodeInfo.API, nodeInfo.Node, nil
	}

	// Otherwise create a new node
	// log.Printf("DEBUG: Creating new node for repo %s\n", repoPath)
	api, node, err := createNewNode(repoPath)
	if err != nil {
		return nil, nil, err
	}

	// Register the new node
	activeNodes[repoPath] = &NodeInfo{
		API:      api,
		Node:     node,
		RefCount: 1,
	}

	return api, node, nil
}

//export RunNode
func RunNode(repoPath *C.char) C.int {
	path := C.GoString(repoPath)
	// Spawn a node
	_, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error spawning node: %s\n", err)
		return C.int(0)
	}
	return C.int(1) // Success
}

// ReleaseNode decreases the reference count for a node, closing it if no references remain
//
//export ReleaseNode
func ReleaseNode(repoPath string) {
	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()

	nodeInfo, exists := activeNodes[repoPath]
	if !exists {
		log.Printf("DEBUG: Attempted to release non-existent node for repo %s\n", repoPath)
		return
	}

	nodeInfo.RefCount--
	log.Printf("DEBUG: Released node for repo %s (refcount: %d)\n", repoPath, nodeInfo.RefCount)

	if nodeInfo.RefCount <= 0 {
		log.Printf("DEBUG: Closing node for repo %s\n", repoPath)
		nodeInfo.Node.Close()
		delete(activeNodes, repoPath)
	}
}

// createNewNode creates a new IPFS node (internal function)
func createNewNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	// log.Printf("DEBUG: Opening repo at %s\n", repoPath)
	// Open the repo
	repo, err := fsrepo.Open(repoPath)
	if err != nil {
		log.Printf("DEBUG: Error opening repo: %v\n", err)
		return nil, nil, err
	}

	// Create a custom build configuration based on platform
	var nodeOptions *core.BuildCfg

	if os.Getenv("ANDROID_ROOT") != "" || runtime.GOOS == "android" {
		log.Printf("DEBUG: Detected Android environment, using Android-specific configuration\n")

		// Android-specific configuration that avoids using resource manager
		nodeOptions = &core.BuildCfg{
			Online:  true,
			Routing: nodep2p.DHTOption,
			Repo:    repo,
			ExtraOpts: map[string]bool{
				"pubsub":                 true,
				"ipnsps":                 true,
				"mplex":                  true,
				"libp2p-stream-mounting": true,
				"p2p-http-proxy":         true,
				"disableResourceManager": true,
				"DisableResourceManager": true,
			},
		}
	} else {
		// Regular configuration for desktop
		nodeOptions = &core.BuildCfg{
			Online:  true,
			Routing: nodep2p.DHTOption,
			Repo:    repo,
			ExtraOpts: map[string]bool{
				"pubsub":                 true,
				"ipnsps":                 true,
				"mplex":                  true,
				"libp2p-stream-mounting": true,
				"p2p-http-proxy":         true,
			},
		}
	}

	// log.Printf("DEBUG: Creating new IPFS node with pubsub and p2p streaming enabled\n")
	ctx := context.Background()
	node, err := core.NewNode(ctx, nodeOptions)
	if err != nil {
		log.Printf("DEBUG: Error creating node: %v\n", err)
		repo.Close()
		return nil, nil, err
	}

	// Construct the API
	// log.Printf("DEBUG: Creating CoreAPI\n")
	api, err := coreapi.NewCoreAPI(node)
	if err != nil {
		log.Printf("DEBUG: Error creating API: %v\n", err)
		node.Close()
		return nil, nil, err
	}

	// log.Printf("DEBUG: Node and API created successfully\n")
	return api, node, nil
}

// PubSubEnable enables pubsub on an IPFS node configuration
//
//export PubSubEnable
func PubSubEnable(repoPath *C.char) C.int {
	path := C.GoString(repoPath)

	// Ensure repo exists
	if !fsrepo.IsInitialized(path) {
		log.Printf("Error: Repository not initialized at %s\n", path)
		return C.int(-1)
	}

	// Open the repo config
	repo, err := fsrepo.Open(path)
	if err != nil {
		log.Printf("Error opening repository: %s\n", err)
		return C.int(-2)
	}
	defer repo.Close()

	// Get the config
	cfg, err := repo.Config()
	if err != nil {
		log.Printf("Error getting repository config: %s\n", err)
		return C.int(-3)
	}

	// Enable experimental features
	cfg.Experimental.Libp2pStreamMounting = true
	cfg.Experimental.P2pHttpProxy = true
	if err := repo.SetConfig(cfg); err != nil {
		log.Printf("Error setting updated config: %s\n", err)
		return C.int(-9)
	}

	// log.Printf("DEBUG: Updated config successfully\n")

	return C.int(0)
}

//export TestGetString
func TestGetString() *C.char {
	// Hard-coded test string to see if this works on Android
	return C.CString("TEST_STRING_123")
}

// GetNodeID gets the ID of the IPFS node
//
//export GetNodeID
func GetNodeID(repoPath *C.char) *C.char {

	ctx := context.Background()

	path := C.GoString(repoPath)

	// Spawn a node
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error spawning node: %s\n", err)
		log.Println("Error spawning node:")

		return C.CString("")
	}
	defer ReleaseNode(path)

	// Get the node ID
	id, err := api.Key().Self(ctx)
	if err != nil {
		log.Printf("Error getting node ID: %s\n", err)
		log.Println("Error  getting node ID:")
		return C.CString("")
	}
	log.Println("Got Node ID")
	log.Println(id.ID().String())

	return C.CString(id.ID().String())
}

// CleanupNode explicitly releases a node by path
//
//export CleanupNode
func CleanupNode(repoPath *C.char) C.int {
	log.Printf("DEBUG: Cleaning up node...")
	
	log.Printf("Closing listeners...")
	P2PCloseAllListeners(repoPath)
	log.Printf("Closing forwarders...")
	P2PCloseAllForwards(repoPath)
	log.Printf("Closing subscriptions...")
	PubSubCloseRepoSubscriptions(repoPath)
	
	path := C.GoString(repoPath)

	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()

	nodeInfo, exists := activeNodes[path]
	if !exists {
		log.Printf("WARNING: Didn't find node to clean up!\n")
		return C.int(-1) // Node doesn't exist
	}

	// Force close regardless of reference count
	log.Printf("DEBUG: Force closing node for repo %s (refcount was: %d)\n",
		path, nodeInfo.RefCount)
	nodeInfo.Node.Close()
	delete(activeNodes, path)

	return C.int(0)
}
