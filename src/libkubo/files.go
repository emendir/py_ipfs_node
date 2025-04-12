package main

// #include <stdlib.h>
// #include <stdbool.h>
import "C"

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	// "unsafe"
	"github.com/ipfs/boxo/coreiface/options"
	ipath "github.com/ipfs/boxo/coreiface/path"
	"github.com/ipfs/boxo/files"
	cidlib "github.com/ipfs/go-cid"
	"log"
)

// AddFile adds a file to IPFS
//
//export AddFile
func AddFile(repoPath, filePath *C.char, onlyHash C.bool) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)
	file := C.GoString(filePath)
	only_hash := bool(onlyHash)
	log.Printf("DEBUG: Adding file from path %s using repo %s\n", file, path)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR:  acquiring node: %s\n", err)
		return nil
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Open the file
	f, err := os.Open(file)
	if err != nil {
		log.Printf("ERROR:  opening file: %s\n", err)
		return nil
	}
	defer f.Close()

	// Add the file to IPFS
	fileInfo, err := f.Stat()
	if err != nil {
		log.Printf("ERROR:  getting file info: %s\n", err)
		return nil
	}

	var fileNode files.Node

	if fileInfo.IsDir() {
		// Handle directory
		var dirErr error
		fileNode, dirErr = files.NewSerialFile(file, true, fileInfo)
		if dirErr != nil {
			log.Printf("ERROR:  creating directory node: %s\n", dirErr)
			return nil
		}
	} else {
		// Handle file
		log.Printf("DEBUG: Creating file node for %s\n", file)
		var fileErr error
		fileNode, fileErr = files.NewReaderPathFile(file, f, fileInfo)
		if fileErr != nil {
			log.Printf("ERROR:  creating file node: %s\n", fileErr)
			return nil
		}
	}

	log.Printf("DEBUG: Adding file to IPFS\n")

	resolved, err := api.Unixfs().Add(
		ctx,
		fileNode,
		options.Unixfs.Pin(!only_hash),
		options.Unixfs.HashOnly(only_hash),
	)

	if err != nil {
		log.Printf("ERROR:  adding file to IPFS: %s\n", err)
		return nil
	}

	cid := resolved.Cid().String()
	log.Printf("DEBUG: File added with CID: %s\n", cid)

	// Return the CID as a C string
	// Note: This allocates memory that should be freed by the caller
	return C.CString(cid)
}

// FreeString is a no-op for now - we'll let Go's garbage collection handle the memory
//
//export FreeString
func FreeString(str *C.char) {
	// log.Printf("DEBUG: FreeString called (NO-OP) for pointer %p\n", unsafe.Pointer(str))
	// We're not actually freeing memory here to avoid the crash
	// C.free(unsafe.Pointer(str))
}

// Download retrieves a file or directory from IPFS
//
//export Download
func Download(repoPath, cidStr, destPath *C.char) C.int {
	ctx := context.Background()

	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)
	dest := C.GoString(destPath)

	log.Printf("DEBUG: Getting content with CID %s to %s using repo %s\n", cid, dest, path)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR:  acquiring node: %s\n", err)
		return C.int(-1)
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		log.Printf("ERROR:  decoding CID: %s\n", err)
		return C.int(-2)
	}

	ipfsPath := ipath.IpfsPath(decodedCid)

	// Get the node from IPFS
	log.Printf("DEBUG: Retrieving content from IPFS\n")
	fileNode, err := api.Unixfs().Get(ctx, ipfsPath)
	if err != nil {
		log.Printf("ERROR:  getting content from IPFS: %s\n", err)
		return C.int(-2)
	}

	// Create the destination directory if it doesn't exist
	err = os.MkdirAll(filepath.Dir(dest), 0755)
	if err != nil {
		log.Printf("ERROR:  creating destination directory: %s\n", err)
		return C.int(-3)
	}

	// Handle different node types (file or directory)
	switch node := fileNode.(type) {
	case files.File:
		// Handle regular file
		log.Printf("DEBUG: Retrieved node is a file\n")
		
		// Read file content
		log.Printf("DEBUG: Reading file content\n")
		content, err := ioutil.ReadAll(node)
		if err != nil {
			log.Printf("ERROR:  reading file content: %s\n", err)
			return C.int(-5)
		}

		// Write the file to the destination
		log.Printf("DEBUG: Writing content to destination file: %s\n", dest)
		err = ioutil.WriteFile(dest, content, 0644)
		if err != nil {
			log.Printf("ERROR:  writing file: %s\n", err)
			return C.int(-6)
		}
		
	case files.Directory:
		// Handle directory
		log.Printf("DEBUG: Retrieved node is a directory\n")
		
		// Create the destination directory if it doesn't exist
		err = os.MkdirAll(dest, 0755)
		if err != nil {
			log.Printf("ERROR:  creating destination directory: %s\n", err)
			return C.int(-7)
		}
		
		// Use the destination path exactly as specified
		log.Printf("DEBUG: Downloading directory to: %s\n", dest)
		
		// Process all entries in the directory
		err = downloadDirectory(node, dest)
		if err != nil {
			log.Printf("ERROR:  processing directory: %s\n", err)
			return C.int(-8)
		}
		
	default:
		log.Printf("ERROR:  unknown node type: %T\n", fileNode)
		return C.int(-9)
	}

	log.Printf("DEBUG: Content retrieved successfully\n")
	return C.int(0) // Success
}

// downloadDirectory recursively downloads a directory and its contents
func downloadDirectory(dir files.Directory, destPath string) error {
	// Ensure the destination path exists
	if err := os.MkdirAll(destPath, 0755); err != nil {
		return fmt.Errorf("creating base directory %s: %w", destPath, err)
	}
	
	// Process directory entries
	entries := dir.Entries()
	for entries.Next() {
		entry := entries.Node()
		name := entries.Name()
		
		// Combine the destination path with the entry name
		destFilePath := filepath.Join(destPath, name)
		log.Printf("DEBUG: Processing entry: %s -> %s\n", name, destFilePath)
		
		switch node := entry.(type) {
		case files.File:
			// Create the file
			content, err := ioutil.ReadAll(node)
			if err != nil {
				return fmt.Errorf("reading file content for %s: %w", name, err)
			}
			
			log.Printf("DEBUG: Writing file: %s\n", destFilePath)
			err = ioutil.WriteFile(destFilePath, content, 0644)
			if err != nil {
				return fmt.Errorf("writing file %s: %w", destFilePath, err)
			}
			
		case files.Directory:
			// Create the directory
			log.Printf("DEBUG: Creating directory: %s\n", destFilePath)
			err := os.MkdirAll(destFilePath, 0755)
			if err != nil {
				return fmt.Errorf("creating directory %s: %w", destFilePath, err)
			}
			
			// Recursively process the subdirectory
			err = downloadDirectory(node, destFilePath)
			if err != nil {
				return err
			}
			
		default:
			log.Printf("WARNING: Unknown node type for %s: %T\n", name, node)
		}
	}
	
	if err := entries.Err(); err != nil {
		return fmt.Errorf("error iterating directory entries: %w", err)
	}
	
	return nil
}

// PinCID pins a CID to the IPFS node
//
//export PinCID
func PinCID(repoPath, cidStr *C.char) C.int {
	ctx := context.Background()

	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)

	log.Printf("DEBUG: Pinning CID %s using repo %s\n", cid, path)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR:  acquiring node: %s\n", err)
		return C.int(-1)
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		log.Printf("ERROR:  decoding CID: %s\n", err)
		return C.int(-2)
	}

	ipfsPath := ipath.IpfsPath(decodedCid)

	// Pin the CID
	err = api.Pin().Add(ctx, ipfsPath, options.Pin.Recursive(true))
	if err != nil {
		log.Printf("ERROR:  pinning CID: %s\n", err)
		return C.int(-3)
	}

	log.Printf("DEBUG: CID pinned successfully\n")
	return C.int(0) // Success
}

// UnpinCID unpins a CID from the IPFS node
//
//export UnpinCID
func UnpinCID(repoPath, cidStr *C.char) C.int {
	ctx := context.Background()

	path := C.GoString(repoPath)
	cid := C.GoString(cidStr)

	log.Printf("DEBUG: Unpinning CID %s using repo %s\n", cid, path)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR:  acquiring node: %s\n", err)
		return C.int(-1)
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// Parse the CID
	decodedCid, err := cidlib.Decode(cid)
	if err != nil {
		log.Printf("ERROR:  decoding CID: %s\n", err)
		return C.int(-2)
	}

	ipfsPath := ipath.IpfsPath(decodedCid)

	// Unpin the CID
	err = api.Pin().Rm(ctx, ipfsPath)
	if err != nil {
		log.Printf("ERROR:  unpinning CID: %s\n", err)
		return C.int(-3)
	}

	log.Printf("DEBUG: CID unpinned successfully\n")
	return C.int(0) // Success
}

// ListPins returns a list of pinned CIDs
//
//export ListPins
func ListPins(repoPath *C.char) *C.char {
	ctx := context.Background()

	path := C.GoString(repoPath)

	log.Printf("DEBUG: Listing pins using repo %s\n", path)

	// Get or create a node from the registry
	api, _, err := AcquireNode(path)
	if err != nil {
		log.Printf("ERROR:  acquiring node: %s\n", err)
		return nil
	}
	// Release the node when done (decreases reference count)
	defer ReleaseNode(path)

	// List all pins
	pinCh, err := api.Pin().Ls(ctx)
	if err != nil {
		log.Printf("ERROR:  listing pins: %s\n", err)
		return nil
	}

	// Collect all pins
	pins := []string{}
	for pin := range pinCh {
		pins = append(pins, pin.Path().Cid().String())
	}

	// Convert to JSON
	pinsJSON, err := json.Marshal(pins)
	if err != nil {
		log.Printf("ERROR:  marshaling pins to JSON: %s\n", err)
		return nil
	}

	log.Printf("DEBUG: Listed %d pins\n", len(pins))
	return C.CString(string(pinsJSON))
}

// RemoveCID removes a pinned CID from IPFS (alias for UnpinCID for clarity)
//
//export RemoveCID
func RemoveCID(repoPath, cidStr *C.char) C.int {
	// This is just an alias for UnpinCID for clarity in the API
	return UnpinCID(repoPath, cidStr)
}
