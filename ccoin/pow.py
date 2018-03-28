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