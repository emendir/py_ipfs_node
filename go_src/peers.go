package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"fmt"
	"os"

	"github.com/libp2p/go-libp2p/core/peer"
)

// ConnectToPeer connects to a peer
//export ConnectToPeer
func ConnectToPeer(repoPath, peerAddr *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	addr := C.GoString(peerAddr)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Connecting to peer %s using repo %s\n", addr, path)
	
	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error acquiring node: %s\n", err)
		return C.int(-1)
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)
	
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