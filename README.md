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
5. Generate block from transactions under TransactionPool and commit block to blockchain (doing) 
6. Relay block to the chain network (March 29, 2018) (done)
7. Design World state (done)
7. Apply block to the chain and world state (done)
8. Apply transactions to the chain and world state (not tested)
9. Mine block with Proof-of-Authority (done)
10. Finish API (doing)

## Current Todos
1. Aggregate transactions under transaction pool (need to test)
2. Start miner nodes with special option --node_type=validator (done)
3. API to send transactions
4. API to check transaction pool size
5. API to query a block count
6. API to query a single block and return all its structure





Callbacks todos:
 on_new_head() 
    if miner should remove those transactions from the queue that came from new block head
    
```python
def _on_new_head(self, block):
    self.transaction_queue = self.transaction_queue.diff(block.transactions)
    self._head_candidate_needs_updating = True
    
def fsm_state_changed()
```

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

3. Finally, you can start blockchain nodes with by running a special service called `cnode`:

```bash
twistd --pidfile=twistd_1.pid --nodaemon cnode -c ccoin.json
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