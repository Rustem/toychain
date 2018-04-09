from twisted.python import log
from random import randint
from time import sleep
from ccoin.security import hash_message


def proof_of_work(difficulty, mining_hash, start_nonce=0, rounds=10000000):
    """
    Simple hashimoto proof of work.
    :param difficulty: mining difficulty
    :type difficulty: int
    :param mining_hash: mining hash
    :type mining_hash: str
    :return: tuple of nonce and proof-of-work hash
    :rtype: tuple[int, str]
    """
    nonce = start_nonce - 1
    isvalid = False
    pow_hash = None
    while isvalid is False and nonce <= rounds:
        concat_str = "%s%s" % (nonce + 1, mining_hash)
        pow_hash = hash_message(concat_str.encode(), hex=True)
        isvalid = is_valid(difficulty, pow_hash)
        nonce += 1
        if nonce % 10000 == 0:
            print(nonce, "attempts", mining_hash, difficulty, pow_hash)
    if isvalid:
        return nonce, pow_hash
    return None, None


def is_valid(difficulty, pow_hash):
    n = len(pow_hash)
    cnt = 0
    for i in range(n):
        if pow_hash[i] != '0':
            break
        cnt += 1
    return cnt >= difficulty


def verify(difficulty, mining_hash, nonce, expected_pow_hash):
    concat_str = "%s%s" % (nonce, mining_hash)
    actual_pow_hash = hash_message(concat_str.encode())
    if actual_pow_hash != expected_pow_hash:
        raise False
    return is_valid(difficulty, expected_pow_hash)


class Miner(object):

    """
    Mines on the current head
    Stores received transactions
    The process of finalising a block involves four stages:
    1) validate (or, if mining, determine) transactions;
    2) apply rewards;
    3) verify (or, if mining, compute a valid) state and nonce.
    :param block: the block for which to find a valid nonce
    """

    def __init__(self, block):
        """
        :param block:
        :type block: Block
        """
        self.nonce = 0
        self.block = block
        # TODO Special log for mining output
        # log.debug('mining', block_number=self.block.number,
        #           block_hash=utils.encode_hex(self.block.hash),
        #           block_difficulty=self.block.difficulty)
        #

    def mine(self, rounds=10000000, start_nonce=0):
        """
        Mines block with simple pow algorithm based on hashimoto.
        :param rounds: max allowed rounds
        :param start_nonce:
        :return: block
        :rtype: ccoin.messages.Block
        """
        log.msg("Started Mining Block")
        # This is done to decrease the probability of chain partitioning
        blk = self.block
        nonce, pow_hash = proof_of_work(blk.difficulty, blk.mining_hash,
                                        start_nonce=start_nonce, rounds=rounds)
        if nonce:
            blk.nonce = nonce
            blk.id = pow_hash
            assert verify(blk.difficulty, blk.mining_hash, nonce, pow_hash), "pow failed; check the code"
            return blk