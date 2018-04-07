# CryptoCoin

This is a "toy" implementation of Blockchain with Proof-of-Authority(PoA) as final project
of Toptal's Blockchain Academy. 

Project is developed with twisted networking tools.

## Road Map
1. Send and Receive Transactions (March 27, 2018) - done
2. Verify signed transactions (March 27, 2018) - done
3. Http API for relaying new transactions (March 27, 2018) - done
2. Define Block and Blockchain data structures (March 28, 2018) - done
3. Run new node from Genesis Block (March 28, 2018) - done
4. Aggregate Transactions under TransactionPool (March 28, 2018)
5. Generate block from transactions under TransactionPool (done) 
6. Commit block to blockchain (testing) 
6. Relay block to the chain network (March 29, 2018) (done)
7. Design World state (done)
7. Apply block to the chain and world state (done)
8. Apply transactions to the chain and world state (done)
9. Mine block with Proof-of-Authority (done)
10. Design API (done)
11. Sender can create many transactions (done)
12. Leader election among miners (very simple, but allows only one node to mine)
13. Discovery service via http (done)
14. Deploy and check on two servers (doing)


## Features
1. Proof-of-Authority: Only a specific set of miners (authors) may mine (create) new blocks. The list of miners is specified in the genesis block and is static.
2. Proof-of-Work: Miners uses HashCash proof-of-work to generate next block by enabling trustless network
3. Basic coins: Each block rewards 100 coins to the miner.
4. RSA Digital signature is used to sign and verify transactions
5. Addresses are derived from RSA public key
6. Etherium Accounting is used as transaction format (Transaction State Machine)
7. There is a protection against double spending of coins using ~nonce~. FYI https://ethereum.stackexchange.com/questions/1172/how-does-the-ethereum-eth-accounting-system-work-and-prevent-double-spends
8. Transactions can have additional data payload (Signed as part of the block)
9. Blocks can have additional data payload (signed as part of the block)
10. P2P Network is based on TCP network
11. Each node exposes JSON HTTP API
- Query the block count.
- Query a single block and return all its transaction data and state.
- Query a single transaction and return all its data.
- Create a transaction and send it to be mined.
12. SHA 256 is used as Hashing algorithm
13. Base64 and hex format are used for storing binary data e.g. certificates
14. Messages are packed to message pack binary protocol. Each message has the following format:
"HEADER+BODY", where HEADER is 3-char string and BODY is message pack serialized message.
15. Apply transaction is done according to Etherium white/yellow papers
16. Apply block is done according to Etherium/Bitcoin white papers
17. Block syncronization between peers is done using simple Finite State Machine protocol 

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
0. In order to start using application plugins, please add application root directory under PYTHONPATH 

```bash
export PYTHONPATH="${PYTHONPATH}:./"
```

1. All communication with application is handled using microservices (a.k.a twisted plugins). In order to run
blockchain node, firstly it is necessary to create account with generated keypair:

```bash
twistd -n create-account -c ccoin.json
```

As a result you should be able to see a created account address message:
```bash
2018-03-29T16:55:37+0600 [-] Created account with address=968414e683062785876545154556573356357415
2018-03-29T16:55:37+0600 [-] Main loop terminated.
```


Then update configuration file ccoin.json to include new account address, under the path `client.account_address`:
```json
{
  "app": {
    "base_path": "/Users/rustem/.ccoin"
  },
  "client": {
    "account_address": "968414e683062785876545154556573356357415"
  },
  "discovery_service": {
      "host": "127.0.0.1",
      "port": 8000,
      "proto": "http"
  }
}
```

2. Next you have to initialize blockchain by generating genesis block from genesis config.
Genesis config example is provided under genesis.json. Below its example:

```json
{
  "network_id": 1,
  "miners": ["968414a7573534a414f4f704b51366f536751764", "968414c6a686a74316a615a4d364f4f317164624"],
  "block_mining": {
    "interval": 600, // mine block each 10 minutes
    "max_bound": 100,  // hundred transactions per block is max
    "min_bound": 10, // 10 transactions per block is min
    "reward": 100, // 100 coins is coinbase transaction in every block mined by miner
    "difficulty": 5, // mining difficulty
    "allow_empty": true, // allow empty block
    "placeholder_data": ["rnd", 15] // if empty block get mined it will be extended with extra 15 bits of data
  },
  "max_peers": 0,
  "genesis_block": {
    "coinbase": "", // coinbase address
    "coinbase_reward": 100,
    "difficulty": 4
  },
  "alloc": { // allocate initial balance among different accounts
    "968414d67505a526b6b34614d354d34546734584": {
      "balance": 10000000
    },
    "968414c6a686a74316a615a4d364f4f317164624": {
      "balance": 100
    }
  }
}
```

Once you've got satisfied with genesis config, you can execute corresponding twisted service to generate
genesis block:

```bash
twistd -n initc --genesis=genesis.json
>>> Output
Genesis block has been mined: nonce=4000, pow_hash=0000b900ae7c1b52d09ed50b2b912c0d5bba9434ac10aa6f8b8998288a49d644
``` 

3. After that you have to start simple discovery service so that peers can connect to each other and 
bootstrap initial network. By default discovery service started at port 4444 and listen on all interfaces.
You can start it as daemon using discovery service as simple as below: 

```bash
twistd discovery -p 4444 -h 0.0.0.0
```

and test that 4444 port is opened with telnet:

```bash
telnet 127.0.0.1 4444
```

4. Finally, you can start blockchain nodes by running a special service called `cnode`. It comes with 
few options to be passed on startup:

```bash
Usage: twistd [options] cnode [options]
Options:
  -c, --config=     Application config file [default: ccoin.json]
      --help        Display this help and exit.
  -p, --port=       Port number [default: 0]
  -t, --node_type=  Node type [default: basic]
```

Make sure that application config file is properly setup with address and discovery service information:

```json
{
  "app": {
    "base_path": "/Users/rustem/.ccoin"
  },
  "client": {
    "account_address": "34268774b426751444e55786d594e46505459325"
  },
  "discovery_service": {
      "host": "127.0.0.1",
      "port": 4444,
      "proto": "http"
  }
}
```

If you want to start your node as miner, use `-t validator`:

```bash
twistd --pidfile=twistd_2.pid --nodaemon cnode -c ccoin_miner_2.json -t validator
``` 

Otherwise you can start it as simple node that can relay transactions into the network:

```bash
twistd --pidfile=twistd_1.pid --nodaemon cnode -c ccoin.json -t basic
```

If everything is created successfully you will be able to see a log similar to the one below:

```bash

2018-03-30T11:18:46+0600 [-] ChainNode starting on 49719
2018-03-30T11:18:46+0600 [ccoin.chainnode.ChainNode#info] Starting factory <ccoin.chainnode.ChainNode object at 0x105352748>
2018-03-30T11:18:46+0600 [twisted.web.server.Site#info] Starting factory <twisted.web.server.Site object at 0x10689bf98>
2018-03-30T11:18:46+0600 [-] HTTP API ENDPOINT Started got up and listening on port: 49720
``` 
The log above clearly indicates that the node has run as p2p endpoint on port 63263 as well as http api endpoint on port 63264.  

## Author

Made by Rustem Kamun a.k.a xepa4ep

rustem@toptal.com