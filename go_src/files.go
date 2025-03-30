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

	"github.com/ipfs/boxo/coreiface/options"
	ipath "github.com/ipfs/boxo/coreiface/path"
	"github.com/ipfs/boxo/files"
	cidlib "github.com/ipfs/go-cid"
)

// AddFile adds a file to IPFS
//export AddFile
func AddFile(repoPath, filePath *C.char) *C.char {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	file := C.GoString(filePath)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Adding file from path %s using repo %s\n", file, path)
	
	// Spawn a node
	api, node, err := spawnNodeFunc(path)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error spawning node: %s\n", err)
		return nil
	}
	defer func() {
		fmt.Fprintf(os.Stderr, "DEBUG: Closing IPFS node\n")
		node.Close()
	}()
	
	// Open the file
	f, err := os.Open(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error opening file: %s\n", err)
		return nil
	}
	defer f.Close()
	
	// Add the file to IPFS
	fileInfo, err := f.Stat()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error getting file info: %s\n", err)
		return nil
	}
	
	var fileNode files.Node
	
	if fileInfo.IsDir() {
		// Handle directory
		var dirErr error
		fileNode, dirErr = files.NewSerialFile(file, true, fileInfo)
		if dirErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating directory node: %s\n", dirErr)
			return nil
		}
	} else {
		// Handle file
		fmt.Fprintf(os.Stderr, "DEBUG: Creating file node for %s\n", file)
		var fileErr error
		fileNode, fileErr = files.NewReaderPathFile(file, f, fileInfo)
		if fileErr != nil {
			fmt.Fprintf(os.Stderr, "Error creating file node: %s\n", fileErr)
			return nil
		}
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: Adding file to IPFS\n")
	resolved, err := api.Unixfs().Add(
		ctx,
		fileNode,
		options.Unixfs.Pin(true),
	)
	
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error adding file to IPFS: %s\n", err)
		return nil
	}
	
	cid := resolved.Cid().String()
	fmt.Fprintf(os.Stderr, "DEBUG: File added with CID: %s\n", cid)
	
	// Return the CID as a C string
	// Note: This allocates memory that should be freed by the caller
	return C.CString(cid)
}

// FreeString is a no-op for now - we'll let Go's garbage collection handle the memory
//export FreeString
func FreeString(str *C.char) {
	fmt.Fprintf(os.Stderr, "DEBUG: FreeString called (NO-OP) for pointer %p\n", unsafe.Pointer(str))
	// We're not actually freeing memory here to avoid the crash
	// C.free(unsafe.Pointer(str)) 
}

// GetFile retrieves a file from IPFS
//export GetFile
func GetFile(repoPath, cidStr, destPath *C.char) C.int {
	ctx := context.Background()
	
	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)
	dest := C.GoString(destPath)
	
	fmt.Fprintf(os.Stderr, "DEBUG: Getting file with CID %s to %s using repo %s\n", cid, dest, path)
	
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
	
	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error decoding CID: %s\n", err)
		return C.int(-2)
	}
	
	ipfsPath := ipath.IpfsPath(decodedCid)
	
	// Get the node from IPFS
	fmt.Fprintf(os.Stderr, "DEBUG: Retrieving content from IPFS\n")
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
	fmt.Fprintf(os.Stderr, "DEBUG: Reading file content\n")
	content, err := ioutil.ReadAll(file)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error reading file content: %s\n", err)
		return C.int(-5)
	}
	
	// Write the file to the destination
	fmt.Fprintf(os.Stderr, "DEBUG: Writing content to destination file\n")
	err = ioutil.WriteFile(dest, content, 0644)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error writing file: %s\n", err)
		return C.int(-6)
	}
	
	fmt.Fprintf(os.Stderr, "DEBUG: File retrieved successfully\n")
	return C.int(0) // Success
}