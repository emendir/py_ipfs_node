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
	
	// Spawn a node
	api, node, err := spawnNodeFunc(path)
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