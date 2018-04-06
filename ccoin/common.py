from twisted.python import log

from ccoin import settings
from ccoin.exceptions import TransactionApplyException
from ccoin.utils import get_random_string


def make_candidate_block(worldstate, chain, txqueue, coinbase=settings.BLANK_SHA_256):
    """
    :param worldstate:
    :type worldstate: ccoin.worldstate.WorldState
    :param chain:
    :type chain: ccoin.blockchain.Blockchain
    :param txqueue:
    :return: tuple of <candidate_block, candidate_state>
    :rtype: tuple[ccoin.blockchain.Blockchain, ccoin.worldstate.WorldState]
    """
    # 1 create candidate block from previous state
    temp_block = chain.create_candidate_block(coinbase=coinbase)
    # 2 build temporary state for candidate block
    temp_state = worldstate.new_candidate_block_state(temp_block)
    # 3 add/apply transactions to that state
    add_transactions(temp_state, temp_block, txqueue)
    # 4 finalize with coinbase debit/credit
    temp_state.incr_balance(temp_block.coinbase, temp_block.reward)
    temp_state.commit()
    return temp_block, temp_state


def generate_block_data(config):
    if config[0] == "rnd":
        rnd_len = config[1]
        return get_random_string(length=rnd_len)
    elif config[0] == "predef":
        # predefined string
        return config[1]
    assert False, "Unrecognized data generator"


def add_transactions(state, block, txqueue):
    """
    Add transactions from queue to block by applying them
    :param state: state object
    :type state: ccoin.worldstate.WorldState
    :param block: block object
    :type block: ccoin.messages.Block
    :param txqueue: transaction queue
    :type txqueue: ccoin.transaction_queue.TransactionQueue
    :return:
    """
    if not txqueue:
        return
    pre_txns = len(block.body)
    log.msg('Adding transactions, %d in txqueue, %d dunkles' %
             (len(txqueue), pre_txns))
    new_txns = []
    while True:
        tx = txqueue.pop_transaction()
        if tx is None:
            break
        try:
            state.apply_txn(tx)
            new_txns.append(tx)
        except TransactionApplyException:
            log.err()
    # finalizes block with transactions and timestamp
    block.set_transactions(new_txns)
    log.msg('Added %d transactions' % (len(block.body) - pre_txns))

