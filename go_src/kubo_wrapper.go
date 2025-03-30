package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
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
	// Open the repo
	repo, err := fsrepo.Open(repoPath)
	if err != nil {
		return nil, nil, err
	}

	// Construct the node
	nodeOptions := &core.BuildCfg{
		Online:  true,
		Routing: libp2p.DHTOption, // This is the default routing mode
		Repo:    repo,
	}

	node, err := core.NewNode(context.Background(), nodeOptions)
	if err != nil {
		return nil, nil, err
	}

	// Construct the API
	api, err := coreapi.NewCoreAPI(node)
	if err != nil {
		return nil, nil, err
	}

	return api, node, nil
}

// AddFile adds a file to IPFS
//export AddFile
func AddFile(repoPath, filePath *C.char) *C.char {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	file := C.GoString(filePath)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.CString("")
	}
	defer node.Close()
	
	// Open the file
	f, err := os.Open(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening file: %s\n", err)
		return C.CString("")
	}
	defer f.Close()
	
	// Add the file to IPFS
	fileInfo, err := f.Stat()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting file info: %s\n", err)
		return C.CString("")
	}
	
	var fileNode files.Node
	
	if fileInfo.IsDir() {
		// Handle directory
		var dirErr error
		fileNode, dirErr = files.NewSerialFile(file, true, fileInfo)
		if dirErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating directory node: %s\n", dirErr)
			return C.CString("")
		}
	} else {
		// Handle file
		var fileErr error
		fileNode, fileErr = files.NewReaderPathFile(file, f, fileInfo)
		if fileErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating file node: %s\n", fileErr)
			return C.CString("")
		}
	}
	
	resolved, err := api.Unixfs().Add(
		ctx,
		fileNode,
		options.Unixfs.Pin(true),
	)
	
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error adding file to IPFS: %s\n", err)
		return C.CString("")
	}
	
	// Return the CID as a C string
	// Note: This allocates memory that should be freed by the caller
	return C.CString(resolved.Cid().String())
}

// FreeString frees a C string
//export FreeString
func FreeString(str *C.char) {
	C.free(unsafe.Pointer(str))
}

// GetFile retrieves a file from IPFS
//export GetFile
func GetFile(repoPath, cidStr, destPath *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)
	dest := C.GoString(destPath)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(-1)
	}
	defer node.Close()
	
	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error decoding CID: %s\n", err)
		return C.int(-2)
	}
	
	ipfsPath := ipath.IpfsPath(decodedCid)
	
	// Get the node from IPFS
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
	content, err := ioutil.ReadAll(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file content: %s\n", err)
		return C.int(-5)
	}
	
	// Write the file to the destination
	err = ioutil.WriteFile(dest, content, 0644)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error writing file: %s\n", err)
		return C.int(-6)
	}
	
	return C.int(0) // Success
}

// ConnectToPeer connects to a peer
//export ConnectToPeer
func ConnectToPeer(repoPath, peerAddr *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	addr := C.GoString(peerAddr)
	
	// Spawn a node
	api, node, err := spawnNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return C.int(-1)
	}
	defer node.Close()
	
	// Parse the peer address
	peerInfo, err := peer.AddrInfoFromString(addr)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error parsing peer address: %s\n", err)
		return C.int(-2)
	}
	
	// Connect to the peer
	err = api.Swarm().Connect(ctx, *peerInfo)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error connecting to peer: %s\n", err)
		return C.int(-3)
	}
	
	return C.int(0) // Success
}

func main() {
	// This is required but we don't need to do anything here
}