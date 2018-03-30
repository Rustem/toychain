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
    :return: reference to state
    :rtype: WorldState
    """
    if block:
        assert isinstance(block, GenesisBlock)
    else:
        block = block_from_genesis_declaration(genesis_config)
    state = WorldState(AppConfig["state_path"], block.nonce)
    for addr, data in genesis_config["alloc"]:
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
    :rtype: tuple[int, str]
    """
    miner = Miner(block)
    blk = miner.mine()
    if blk is None:
        raise MiningGenesisBlockFailed(block)
    return blk


def make_genesis_block(genesis_config):
    block = block_from_genesis_declaration(genesis_config)
    state = state_from_genesis_declaration(genesis_config, block=block)
    nonce, pow_hash = mine_genesis_block(block)
    return block

