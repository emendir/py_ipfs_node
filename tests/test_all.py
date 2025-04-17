import test_tunnels
import test_pubsub
import test_peers
import test_utils
from time import sleep
test_pubsub.run()
sleep(30) # wait for ipfs node to shut down
test_tunnels.run()
sleep(30) # wait for ipfs node to shut down
test_peers.run()
test_utils.run()
