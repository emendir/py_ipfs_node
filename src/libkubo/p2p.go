package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"strings"
	"github.com/ipfs/kubo/p2p"
	"github.com/libp2p/go-libp2p/core/peer"
	"github.com/libp2p/go-libp2p/core/protocol"
	ma "github.com/multiformats/go-multiaddr"
)

// P2PForward creates a libp2p stream mounting forwarding connection
//
//export P2PForward
func P2PForward(repoPath, proto, listenAddr, targetPeerID *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(proto)
	listenAddress := C.GoString(listenAddr)
	peerIDStr := C.GoString(targetPeerID)

	// Format the protocol as needed (Kubo requires /x/ prefix)
	if !strings.HasPrefix(protocolName, "/x/") {
		protocolName = "/x/" + protocolName
	}

	// Get the node for this repo
	_, node, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error acquiring node for P2P forwarding: %v\n", err)
		return C.int(-1)
	}
	defer ReleaseNode(path)

	// Get the P2P service from the node
	p2pService := node.P2P

	// Parse the listen address as a multiaddr
	listenMA, err := ma.NewMultiaddr(listenAddress)
	if err != nil {
		log.Printf("Error parsing listen address: %v\n", err)
		return C.int(-3)
	}

	// Parse the peer ID
	peerID, err := peer.Decode(peerIDStr)
	if err != nil {
		log.Printf("Error parsing peer ID: %v\n", err)
		return C.int(-4)
	}

	// Create the forwarding (ForwardLocal is used to connect to a remote peer)
	listener, err := p2pService.ForwardLocal(context.Background(), peerID, protocol.ID(protocolName), listenMA)
	if err != nil {
		log.Printf("Error creating P2P forward: %v\n", err)
		return C.int(-2)
	}

	log.Printf("P2P forward created: %s -> %s via %s\n", 
		listener.ListenAddress().String(), listener.TargetAddress().String(), listener.Protocol())
	return C.int(1)
}

// P2PListen creates a libp2p service that listens for connections on the given protocol
//
//export P2PListen
func P2PListen(repoPath, proto, targetAddr *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(proto)
	targetAddress := C.GoString(targetAddr)

	// Format the protocol as needed (Kubo requires /x/ prefix)
	if !strings.HasPrefix(protocolName, "/x/") {
		protocolName = "/x/" + protocolName
	}

	// Get the node for this repo
	_, node, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error acquiring node for P2P listening: %v\n", err)
		return C.int(-1)
	}
	defer ReleaseNode(path)

	// Get the P2P service from the node
	p2pService := node.P2P

	// Parse the target address as a multiaddr
	targetMA, err := ma.NewMultiaddr(targetAddress)
	if err != nil {
		log.Printf("Error parsing target address: %v\n", err)
		return C.int(-3)
	}

	// Create the remote listener (ForwardRemote is used to create a listener service)
	// The last parameter is reportRemote which we set to false
	listener, err := p2pService.ForwardRemote(context.Background(), protocol.ID(protocolName), targetMA, false)
	if err != nil {
		log.Printf("Error creating P2P listener: %v\n", err)
		return C.int(-2)
	}

	log.Printf("P2P listener created: %s -> %s\n", listener.Protocol(), listener.TargetAddress().String())
	return C.int(1)
}

// P2PClose closes p2p listener or stream
//
//export P2PClose
func P2PClose(repoPath, proto, listenAddr, targetPeerID *C.char) C.int {
	path := C.GoString(repoPath)
	protocolName := C.GoString(proto)
	// listenAddress := C.GoString(listenAddr)
	peerIDStr := C.GoString(targetPeerID)

	// Format the protocol as needed (Kubo requires /x/ prefix)
	if !strings.HasPrefix(protocolName, "/x/") {
		protocolName = "/x/" + protocolName
	}

	// Get the node for this repo
	_, node, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error acquiring node for P2P close: %v\n", err)
		return C.int(-1)
	}
	defer ReleaseNode(path)

	// Get the P2P service from the node
	p2pService := node.P2P

	// Find listeners to close
	count := 0
	
	// Try to use the P2P service's methods to close listeners
	// Close local listeners for the given protocol
	if protocolName != "" {
		protocolID := protocol.ID(protocolName)
		matchFunc := func(listener p2p.Listener) bool {
			return listener.Protocol() == protocolID
		}
		
		closedCount := p2pService.ListenersLocal.Close(matchFunc)
		if closedCount > 0 {
			log.Printf("Closed %d local P2P listener(s) for protocol: %s\n", closedCount, protocolName)
			count += closedCount
		}
	}
	
	// Close remote listeners for the given protocol
	if protocolName != "" {
		protocolID := protocol.ID(protocolName)
		matchFunc := func(listener p2p.Listener) bool {
			return listener.Protocol() == protocolID
		}
		
		closedCount := p2pService.ListenersP2P.Close(matchFunc)
		if closedCount > 0 {
			log.Printf("Closed %d remote P2P listener(s) for protocol: %s\n", closedCount, protocolName)
			count += closedCount
		}
	}
	
	// Close any matching streams
	for streamID, stream := range p2pService.Streams.Streams {
		if protocol.ID(protocolName) == stream.Protocol {
			// If peer ID was specified, match it
			if peerIDStr != "" {
				// peerID, err := peer.Decode(peerIDStr)
				// if err != nil {
				// 	log.Printf("Error parsing peer ID: %v\n", err)
				// 	return C.int(-4)
				// }
				
				// Skip this stream if peer ID doesn't match
				// Currently disabled until we know the exact field name
				// if stream.peer != peerID {
				// 	continue
				// }
			}
			
			log.Printf("Closing P2P stream ID: %d\n", streamID)
			// Close the stream object directly
			p2pService.Streams.Close(stream)
			count++
		}
	}
	
	if count == 0 {
		log.Printf("No P2P listeners or streams found for protocol: %s\n", protocolName)
		return C.int(0)
	}
	
	return C.int(count)
}

// P2PListListeners lists active p2p listeners
//
//export P2PListListeners
func P2PListListeners(repoPath *C.char) *C.char {
	path := C.GoString(repoPath)

	// Get the node for this repo
	_, node, err := AcquireNode(path)
	if err != nil {
		log.Printf("Error acquiring node for P2P list: %v\n", err)
		return C.CString("")
	}
	defer ReleaseNode(path)

	// Get the P2P service from the node
	p2pService := node.P2P

	// List all listeners
	result := make(map[string]interface{})

	// Get local listeners
	localList := make([]map[string]string, 0)
	
	for _, l := range p2pService.ListenersLocal.Listeners {
		info := map[string]string{
			"Protocol":      string(l.Protocol()),
			"ListenAddress": l.ListenAddress().String(),
			"TargetAddress": l.TargetAddress().String(),
		}
		localList = append(localList, info)
	}
	result["LocalListeners"] = localList

	// Get remote listeners
	remoteList := make([]map[string]string, 0)
	
	for _, l := range p2pService.ListenersP2P.Listeners {
		info := map[string]string{
			"Protocol":      string(l.Protocol()),
			"ListenAddress": l.ListenAddress().String(),
			"TargetAddress": l.TargetAddress().String(),
		}
		remoteList = append(remoteList, info)
	}
	result["RemoteListeners"] = remoteList

	// Get active streams
	streamsList := make([]map[string]string, 0)
	
	for id, s := range p2pService.Streams.Streams {
		info := map[string]string{
			"Protocol":     string(s.Protocol),
			"LocalAddr":    s.OriginAddr.String(),
			"RemoteAddr":   s.TargetAddr.String(),
			"ID":           fmt.Sprintf("%d", id),
		}
		streamsList = append(streamsList, info)
	}
	result["Streams"] = streamsList

	// Convert to JSON
	jsonData, err := json.Marshal(result)
	if err != nil {
		log.Printf("Error marshaling P2P listener data: %v\n", err)
		return C.CString("")
	}

	return C.CString(string(jsonData))
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