package main

// #include <stdlib.h>
import "C"

import (
	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/kubo/core"
)

// Store reference to the spawnNode function from repo.go
var spawnNodeFunc func(repoPath string) (iface.CoreAPI, *core.IpfsNode, error)

func init() {
	// Initialize once all packages are loaded
	spawnNodeFunc = spawnNode
}

func main() {
	// Required entry point for buildmode=c-shared
	// Does not need to do anything
}