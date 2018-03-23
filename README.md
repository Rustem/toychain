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
to be done

## Author

Made by Rustem Kamun a.k.a xepa4ep

rustem@toptal.com
