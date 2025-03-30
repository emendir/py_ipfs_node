package main

// #include <stdlib.h>
import "C"

import (
	iface "github.com/ipfs/boxo/coreiface"
	"github.com/ipfs/kubo/core"
)

// This will be set during initialization
var spawnNodeFunc func(repoPath string) (iface.CoreAPI, *core.IpfsNode, error)

func main() {
	// Required entry point for buildmode=c-shared
	// Does not need to do anything
}