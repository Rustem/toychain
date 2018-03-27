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
