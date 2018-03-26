# CryptoCoin

This is a "toy" implementation of Blockchain with Proof-of-Authority(PoA) as final project
of Toptal's Blockchain Academy. 

Project is developed with twisted networking tools.



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
Node represents the peer in the network. To start the node it is necessary to pass his id and list of
connecting peers. 

Note: `run_p2p()` starts the twisted loop.

```python
import argparse
from ccoin.p2p_network import BasePeer


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("node_id", help='Id of the node in the given peers dict.')
    args = parser.parse_args()
    node_id = args.node_id
    node = BasePeer(node_id)
    node.run_p2p()
```

## Author

Made by Rustem Kamun a.k.a xepa4ep

rustem@toptal.com
