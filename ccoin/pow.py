def proof_of_work(block):
    """
    Simple proof of work.
    :param block: Block instance
    :type block: Block
    :return: tuple of nonce and proof-of-work hash
    :rtype: tuple[int, str]
    """
    nonce = 0
    difficulty = block.difficulty
    while is_valid(difficulty, block.get_pow_hash(nonce, block.get_hash())) is False:
        nonce += 1
    pow_hash = block.get_pow_hash(nonce, block.get_hash())
    return nonce, pow_hash


def is_valid(difficulty, pow_hash):
    return pow_hash[:difficulty] == "0" * difficulty



class Miner(object):

    def __init__(self, block):
        self.nonce = 0
        self.block = block
        # TODO Special log for mining output
        # log.debug('mining', block_number=self.block.number,
        #           block_hash=utils.encode_hex(self.block.hash),
        #           block_difficulty=self.block.difficulty)
        #

    def mine(self, rounds=1000, start_nonce=0):
        """
        :param rounds:
        :param start_nonce:
        :return: block
        :rtype: Block
        """
        # TODO implement
        pass
        # blk = self.block
        # bin_nonce, mixhash = mine(blk.number, blk.difficulty, blk.mining_hash,
        #                           start_nonce=start_nonce, rounds=rounds)
        # if bin_nonce:
        #     blk.header.mixhash = mixhash
        #     blk.header.nonce = bin_nonce
        #     # assert blk.check_pow()
        #     return blk