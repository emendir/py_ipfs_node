package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"sync"

	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/kubo/config"
	"github.com/ipfs/kubo/core"
	"github.com/ipfs/kubo/core/coreapi"
	"github.com/ipfs/kubo/core/node/libp2p"
	"github.com/ipfs/kubo/plugin/loader"
	"github.com/ipfs/kubo/repo/fsrepo"
)

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
	
	// Initialize the shared function reference for other files
	spawnNodeFunc = AcquireNode
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

// AcquireNode gets or creates an IPFS node, increasing its reference count
func AcquireNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()
	
	// Check if we already have an active node for this repo
	if nodeInfo, exists := activeNodes[repoPath]; exists {
		fmt.Fprintf(os.Stderr, "DEBUG: Reusing existing node for repo %s (refcount: %d -> %d)\n", 
			repoPath, nodeInfo.RefCount, nodeInfo.RefCount+1)
		nodeInfo.RefCount++
		return nodeInfo.API, nodeInfo.Node, nil
	}
	
	// Otherwise create a new node
	fmt.Fprintf(os.Stderr, "DEBUG: Creating new node for repo %s\n", repoPath)
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
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(0)
	}
	return C.int(1) // Success
}
// ReleaseNode decreases the reference count for a node, closing it if no references remain
func ReleaseNode(repoPath string) {
	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()
	
	nodeInfo, exists := activeNodes[repoPath]
	if !exists {
		fmt.Fprintf(os.Stderr, "DEBUG: Attempted to release non-existent node for repo %s\n", repoPath)
		return
	}
	
	nodeInfo.RefCount--
	fmt.Fprintf(os.Stderr, "DEBUG: Released node for repo %s (refcount: %d)\n", repoPath, nodeInfo.RefCount)
	
	if nodeInfo.RefCount <= 0 {
		fmt.Fprintf(os.Stderr, "DEBUG: Closing node for repo %s\n", repoPath)
		nodeInfo.Node.Close()
		delete(activeNodes, repoPath)
	}
}

// createNewNode creates a new IPFS node (internal function)
func createNewNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	fmt.Fprintf(os.Stderr, "DEBUG: Opening repo at %s\n", repoPath)
	// Open the repo
	repo, err := fsrepo.Open(repoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Error opening repo: %v\n", err)
		return nil, nil, err
	}

	// Get the config to check if pubsub is enabled
	cfg, err := repo.Config()
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Error getting repo config: %v\n", err)
		repo.Close()
		return nil, nil, err
	}

	// Automatically enable pubsub experiments in the node options
	// We're modifying the raw config file and also setting the Experimental flag

	// Convert to JSON map for direct manipulation
	cfgRaw, err := json.Marshal(cfg)
	if err == nil {
		cfgMap := map[string]interface{}{}
		if json.Unmarshal(cfgRaw, &cfgMap) == nil {
			// Check the experimental section
			if expMap, ok := cfgMap["Experimental"].(map[string]interface{}); ok {
				// Set pubsub enabled
				expMap["Pubsub"] = true
				fmt.Fprintf(os.Stderr, "DEBUG: Setting pubsub enabled in config\n")
			}
		}
	}
    
	// Update the repo config with pubsub enabled
	err = repo.SetConfig(cfg)
	if err != nil {
		fmt.Fprintf(os.Stderr, "DEBUG: Warning - could not update repo config: %v\n", err)
		// Continue anyway
	}

	// Construct the node with experimental features enabled
	nodeOptions := &core.BuildCfg{
		Online:  true,
		Routing: libp2p.DHTOption, // This is the default routing mode
		Repo:    repo,
		ExtraOpts: map[string]bool{
			"pubsub": true,
			"ipnsps": true,
			"mplex":  true,
		},
	}

	fmt.Fprintf(os.Stderr, "DEBUG: Creating new IPFS node with pubsub enabled\n")
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

// SpawnNode creates or reuses an IPFS node (backward compatible API)
// This is the function other files will call
func spawnNode(repoPath string) (iface.CoreAPI, *core.IpfsNode, error) {
	return AcquireNode(repoPath)
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

// GetNodeID gets the ID of the IPFS node
//
//export TestGetString
func TestGetString() *C.char {
	// Hard-coded test string to see if this works on Android
	return C.CString("TEST_STRING_123")
}

//export GetNodeID
func GetNodeID(repoPath *C.char) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)

	// Spawn a node
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.CString("")
	}
	defer ReleaseNode(path)
	
	// Get the node ID
	id, err := api.Key().Self(ctx)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting node ID: %s\n", err)
		return C.CString("")
	}
	
	return C.CString(id.ID().String())
}

// CleanupNode explicitly releases a node by path
//export CleanupNode
func CleanupNode(repoPath *C.char) C.int {
	path := C.GoString(repoPath)
	
	activeNodesMutex.Lock()
	defer activeNodesMutex.Unlock()
	
	nodeInfo, exists := activeNodes[path]
	if !exists {
		return C.int(-1) // Node doesn't exist
	}
	
	// Force close regardless of reference count
	fmt.Fprintf(os.Stderr, "DEBUG: Force closing node for repo %s (refcount was: %d)\n", 
		path, nodeInfo.RefCount)
	nodeInfo.Node.Close()
	delete(activeNodes, path)
	
	return C.int(0)
}