import os
import json
from ccoin.dict_tools import LazyDict, merge_deep

"""Blockchain Network configuration is loaded from genesis block."""

NetworkConf = LazyDict({
    "network_id": 1,
    "miners": [],
    "block_mining": {
        "interval": 600, # mine block each 10 minutes
        "max_bound": 100,  # hundred transactions per block is max
        "min_bound": 10, # 10 transactions per block is min
        "reward": 100, # 100 coins is coinbase transaction in every block mined by miner
        "difficulty": 5, # mining difficulty
        "allow_empty": True, # allow empty block
        "placeholder_data": ["rnd", 15] # if empty block get mined it will be extended with extra 15 bits of data
    },
    "transaction": {
        "placeholder_data": ["rnd", 15] # if data is not provided for transaction it will be provided by default with this configuration
    },
    "max_peers": 0,
        "genesis_block": {
        "coinbase": "", # coinbase address
        "difficulty": 4
    }
})


def configure(genesis_config=None):
    """
    Configures app
    :param genesis_config: app configuration object
    :type genesis_config: dict
    """
    if genesis_config is None:
        return
    global NetworkConf
    NetworkConf = merge_deep(genesis_config, NetworkConf)