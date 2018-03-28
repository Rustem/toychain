# CryptoCoin

This is a "toy" implementation of Blockchain with Proof-of-Authority(PoA) as final project
of Toptal's Blockchain Academy. 

Project is developed with twisted networking tools.

## Road Map
1. Send and Receive Transactions (March 27, 2018) - done
2. Verify signed transactions (March 27, 2018) - done
3. Http API for relaying new transactions (March 27, 2018) - done
2. Define Block and Blockchain data structures (March 28, 2018) - doing
3. Run new node from Genesis Block (March 28, 2018) - doing
4. Aggregate Transactions under TransactionPool (March 28, 2018)
5. Generate block from transactions under TransactionPool and commit block to blockchain (March 29, 2018) 
6. Relay block to the chain network (March 29, 2018)
7. Mine block with Proof-of-Authority (March 30, 2018)

## Current Todos
1. Blocks must be signed
1. Tools for generating genesis transaction
2. Load Node with blockchain loaded
3. Miner logic: Aggregate new transactions in the in-memory transaction pool
 

## Requirements

Python 3.6, pip

recommended - virtualenv

## Installation

Activate virtualenv:
```bash
virtualenv --python=python3 <venv>
source <venv>/bin/activate
```

Prerequisites:

LevelDB should be installed prior to installing project dependencies. The installation
process depends on the OS.

For MacOSX:
```bash
brew install leveldb
CFLAGS='-mmacosx-version-min=10.7 -stdlib=libc++' pip install --no-use-wheel plyvel
```

Install ccoin:
```bash
git clone https://github.com/Rustem/tacademy-ccoin.git
cd tacademy-ccoin
pip install -r requirements.txt
python setup.py install
```

## Usage
All communication with application is handled using microservices (a.k.a twisted plugins). In order to run
blockchain node, firstly it is necessary to create account with generated keypair and (non-zero) balance:

```bash
twistd -n create-account --nodeid=1 --balance=120
```

Blockchain node is represented by ChainNode entity. Having just created account, it is possible to run an instance
of ChainNode with the following command:

```bash
twistd --pidfile twistd_1.pid --nodaemon cnode --nodeid=1
```

If everything is created successfully you will be able to see a log similar to the one below:

```bash
2018-03-27T15:19:52+0600 [twisted.scripts._twistd_unix.UnixAppLogger#info] twistd 17.9.0 (/Users/rustem/.virtualenvs/bchain-academy/bin/python3.5 3.5.2) starting up.
2018-03-27T15:19:52+0600 [twisted.scripts._twistd_unix.UnixAppLogger#info] reactor class: twisted.internet.selectreactor.SelectReactor.
2018-03-27T15:19:52+0600 [-] ChainNode starting on 63261
2018-03-27T15:19:52+0600 [ccoin.chainnode.ChainNode#info] Starting factory <ccoin.chainnode.ChainNode object at 0x10580b8d0>
2018-03-27T15:19:52+0600 [-] Site starting on 63262
2018-03-27T15:19:52+0600 [twisted.web.server.Site#info] Starting factory <twisted.web.server.Site object at 0x10591e048>
2018-03-27T15:19:52+0600 [-] HTTP API ENDPOINT Started got up and listening on port: 63262
2018-03-27T15:19:52+0600 [-] ChainNode starting on 63263
2018-03-27T15:19:52+0600 [-] Site starting on 63264
2018-03-27T15:19:52+0600 [twisted.web.server.Site#info] Starting factory <twisted.web.server.Site object at 0x10591e4a8>
2018-03-27T15:19:52+0600 [-] HTTP API ENDPOINT Started got up and listening on port: 63264
``` 
The log above clearly indicates that the node has run as p2p endpoint on port 63263 as well as http api endpoint on port 63264.  

## Author

Made by Rustem Kamun a.k.a xepa4ep

rustem@toptal.com

## DEVELOPER NOTES

```bash

About blockchain

1. Genesis block stores configuration of the chain
2. Node can be in different modes:
    "genesis" => node generates genesis block
    "boot" => node is downloaded data from other peers
    "ready" => if node is miner he can start mine new blocks because node is actualized

Genesis state: 
    - node generates genesis block
    - relays it over the network
    - move it states to 'ready'

Boot state
    - node broadcast request about blockchain "height"
    - takes the maximum among all the answers (or from the leader)
    - if his height is less than height of the current => actualized 
    - move it state to "ready"

Ready state
    - if node is miner, then can mine new blocks every 10 minutes

Dying state
    - if no genesis block yet created
    - if wait for longer than 10 minutes

Dead state
    - causes node to stop (closing all the ports)


Creating network
0. Create miner account with twistd create-account
1. Prepare json configuration file e.g. genesis.json
2. Use twistd init -c genesis.json

Initializing blockchain / Generating genesis block
1. Creates a special block with configuration data and coinbase transaction
2. Stores it in the level db of the specified user
3. Stops the service

Connecting as client
1. Connect to the network
2. Sends request about the highest block known so far
3. if somebody has block higher => goes to "boot" mode in background thread
4. once blocks are downlaoded  move to "ready" mode
5. If miner can mine


Reconcialiation:

1. Node A sends request of higest block including to Node B
2. Node B responded with his highest block
3. Node A sends ack with his highest block

4. If Node A has block higher than B => Node B moves to boot mode
    - Node B have to find LCA between A, B chains
    - once LCA found, Node B can download starting from the block height

Finding LCA
    - get 100 blocks ids starting from block number X
    - if among them found common ids, take the highest
    - otherwise take next 100 starting from X - 100 and so on





```