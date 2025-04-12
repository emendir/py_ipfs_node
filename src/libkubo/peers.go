package main

// #include <stdlib.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"github.com/ipfs/kubo/core"
	"github.com/libp2p/go-libp2p/core/peer"
	routing "github.com/libp2p/go-libp2p/core/routing"
	"log"
	"time"
)

// ConnectToPeer connects to a peer
//
//export ConnectToPeer
func ConnectToPeer(repoPath, peerAddr *C.char) C.int {
	ctx := context.Background()

	path := C.GoString(repoPath)
	addr := C.GoString(peerAddr)


	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR: Error acquiring node: %s\n", err)
		return C.int(-1)
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Parse the peer address
	peerInfo, err := peer.AddrInfoFromString(addr)
	if err != nil {
		log.Printf("ERROR: Error parsing peer address: %s\n", err)
		return C.int(-2)
	}

	// Connect to the peer
	err = api.Swarm().Connect(ctx, *peerInfo)
	if err != nil {
		log.Printf("ERROR: Error connecting to peer: %s\n", err)
		return C.int(-3)
	}

	return C.int(0) // Success
}

// ListPeers connects to a peer
//
//export ListPeers
func ListPeers(repoPath *C.char) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)


	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR: Error acquiring node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Connect to the peer
	peers, err := api.Swarm().Peers(ctx)
	if err != nil {
		log.Printf("ERROR: Error connecting to peer: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	peer_ids := make([]string, len(peers))
	for i, e := range peers {
		peer_ids[i] = e.Address().String() + "/" + e.ID().String()
	}
	// Convert to JSON
	peersJSON, err := json.Marshal(peer_ids)
	if err != nil {
		log.Printf("Error marshaling peers to JSON: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	return C.CString(string(peersJSON))

}
// ListPeers connects to a peer
//
//export ListPeersIDs
func ListPeersIDs(repoPath *C.char) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)


	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR: Error acquiring node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Connect to the peer
	peers, err := api.Swarm().Peers(ctx)
	if err != nil {
		log.Printf("ERROR: Error connecting to peer: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	peer_ids := make([]string, len(peers))
	for i, e := range peers {
		peer_ids[i] = e.ID().String()
	}
	// Convert to JSON
	peersJSON, err := json.Marshal(peer_ids)
	if err != nil {
		log.Printf("Error marshaling peers to JSON: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}

	return C.CString(string(peersJSON))

}
func SearchForPeer(ctx context.Context, node *core.IpfsNode, pid peer.ID, timeout int) ([]*peer.AddrInfo, error) {
	ctx, cancel := context.WithTimeout(ctx, time.Duration(timeout)*time.Second)
	defer cancel()

	ctx, events := routing.RegisterForQueryEvents(ctx)

	resultChan := make(chan []*peer.AddrInfo, 1)
	errChan := make(chan error, 1)

	// Start FindPeer query
	go func() {
		_, err := node.Routing.FindPeer(ctx, pid)
		if err != nil {
			// propagate error via event
			routing.PublishQueryEvent(ctx, &routing.QueryEvent{
				Type:  routing.QueryError,
				Extra: err.Error(),
			})
		}
		// when FindPeer exits, events channel will be closed automatically
	}()

	// Collect responses from events
	go func() {
		var peers []*peer.AddrInfo
		for evt := range events {
			switch evt.Type {
			case routing.FinalPeer:
				peers = append(peers, evt.Responses...)
			case routing.QueryError:
				errChan <- fmt.Errorf("query error: %s", evt.Extra)
				return
			}
		}
		resultChan <- peers
	}()

	// Await results
	select {
	case peers := <-resultChan:
		return peers, nil
	case err := <-errChan:
		return nil, err
	case <-ctx.Done():
		return nil, ctx.Err()
	}
}
// FindPeer connects to a peer
//
//export FindPeer
func FindPeer(repoPath, peerAddr *C.char, timeOut C.int) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)
	addr := C.GoString(peerAddr)
	timeout := int(timeOut)

	// Get or create a node from the registry
	_, node, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR: Error acquiring node: %s\n", err)
		return C.CString("[]") // Return empty JSON array
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Parse the peer address
	pid, err := peer.Decode(addr)
	if err != nil {
		return C.CString("[]") // Return empty JSON array
	}
	// Connect to the peer
	multi_addresses, err := node.Routing.FindPeer(ctx, pid)
	if err != nil || len(multi_addresses.Addrs) == 0 {
		SearchForPeer(ctx, node, pid, timeout)
		multi_addresses2, err2 := node.Routing.FindPeer(ctx, pid)
		if err2 != nil {
			log.Printf("ERROR: Error finding peer: %s\n", err)
			return C.CString("[]") // Return empty JSON array
		}
		multi_addresses = multi_addresses2
	}
	
	

	// Convert to JSON
	multi_addressesJSON, err := json.Marshal(multi_addresses.Addrs)
	if err != nil {
		log.Printf("Error marshaling multi_addresses to JSON: %s\n", err)
		return nil
	}
	// log.Printf( "Got next message! %s\n", messageJSON)

	return C.CString(string(multi_addressesJSON))
}
