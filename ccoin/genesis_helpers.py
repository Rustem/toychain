from twisted.python import log

from ccoin.blockchain import Blockchain
from ccoin.exceptions import MiningGenesisBlockFailed
from ccoin.messages import GenesisBlock
from ccoin.app_conf import AppConfig
from ccoin.pow import Miner
from ccoin.worldstate import WorldState

def block_from_genesis_declaration(genesis_config):
    return GenesisBlock.loadFromConfig(genesis_config)


def state_from_genesis_declaration(genesis_config, block=None):
    """
    Initializes and stores genesis state.
    :param genesis_config:
    :param block:
    :type block: GenesisBlock
    :return: reference to state
    :rtype: WorldState
    """
    if block:
        assert isinstance(block, GenesisBlock)
    else:
        block = block_from_genesis_declaration(genesis_config)
    state = WorldState.load(AppConfig["storage_path"], AppConfig["state_db"], block.nonce)
    for addr, data in genesis_config["alloc"].items():
        if 'balance' in data:
            state.set_balance(addr, data["balance"])
        if 'nonce' in data:
            state.set_nonce(addr, data["nonce"])
    state.commit()
    block.hash_state = state.calculate_hash()
    return state


def mine_genesis_block(block):
    """
    :param block:
    :return: tuple of nonce, pow_hash
    :rtype: GenesisBlock
    """
    miner = Miner(block)
    blk = miner.mine()
    if blk is None:
        raise MiningGenesisBlockFailed(block)
    log.msg("Genesis block has been mined: nonce=%s, pow_hash=%s" % (blk.nonce, blk.id))
    return blk


def make_genesis_block(genesis_config):
    block = block_from_genesis_declaration(genesis_config)
    state = state_from_genesis_declaration(genesis_config, block=block)
    block = mine_genesis_block(block)
    Blockchain.create_new(AppConfig["storage_path"], AppConfig["chain_db"], block)
    return block

