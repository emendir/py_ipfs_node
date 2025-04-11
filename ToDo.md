
## General
- test all features
- improve API

## libkubo
- CleanupNode: wait till IPFS node is fully shutdown
- SearchForPeer: make events work, so that we can return as soon as peer is found instead of waiting for end of timeout

## ipfs_node:
- auto-generate IpfsNode._lib
- implement ReleaseNode
- IpfsNode.Tcp: cleanup close and listen methods

## Features
- [x] PubSub
- [x] P2P Stream Mounting implemented
- [ ] peer management
- [ ] Key management
- [ ] Config management