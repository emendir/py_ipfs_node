package main

// #include <stdlib.h>
import "C"

import (
	"log"
	"strings"
)

// P2PForward creates a libp2p stream mounting forwarding connection
//
//export P2PForward
func P2PForward(repoPath, protocol, listenAddr, targetPeerID *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(protocol)
	listenAddress := C.GoString(listenAddr)
	peerID := C.GoString(targetPeerID)

	// Format the protocol as needed (Kubo requires /x/ prefix)
	if !strings.HasPrefix(protocolName, "/x/") {
		protocolName = "/x/" + protocolName
	}

	// TODO
}

// P2PListen creates a libp2p service that listens for connections on the given protocol
//
//export P2PListen
func P2PListen(repoPath, protocol, targetAddr *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(protocol)
	targetAddress := C.GoString(targetAddr)

	// Format the protocol as needed (Kubo requires /x/ prefix)
	if !strings.HasPrefix(protocolName, "/x/") {
		protocolName = "/x/" + protocolName
	}

	// TODO
}

// P2PClose closes p2p listener or stream
//
//export P2PClose
func P2PClose(repoPath, protocol, listenAddr, targetPeerID *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(protocol)
	listenAddress := C.GoString(listenAddr)
	peerID := C.GoString(targetPeerID)

	// TODO
}

// P2PListListeners lists active p2p listeners
//
//export P2PListListeners
func P2PListListeners(repoPath *C.char) *C.char {
	path := C.GoString(repoPath)

	// TODO
}

// P2PEnable ensures p2p functionality is enabled in the config
//
//export P2PEnable
func P2PEnable(repoPath *C.char) C.int {
	path := C.GoString(repoPath)
	
	// Use AcquireNode just to make sure the node is running
	_, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error acquiring node: %v\n", err)
		return C.int(-1)
	}
	defer ReleaseNode(path)

	// Node configuration already has the required experimental features enabled
	log.Printf("P2P functionality enabled for repo: %s\n", path)
	
	return C.int(1)
}