import plyvel
import os
from collections import deque

from ccoin.exceptions import GenesisBlockIsRequired
from .messages import Block, GenesisBlock


class Blockchain(object):

    SPECIAL_KEYS = (b"height",)

    @classmethod
    def load(cls, account_id):
        """
        Loads blockchain with necessary properties and returns it
        :return: blockchain instance
        :rtype: Blockchain
        """

        base_path = os.path.expanduser('~/.pichain')
        path = base_path + '/node_' + str(account_id)
        if not os.path.exists(path):
            # Attention: blockchain is empty (even genesis block is not generated)
            # Either request it from the network or start your own
            raise GenesisBlockIsRequired(account_id)
        db = plyvel.DB(path, create_if_missing=True)
        # load genesis block
        block_bytes = db.get(cls.to_key(0))
        if not block_bytes:
            # Attention: blockchain is empty (even genesis block is not generated)
            # Either request it from the network or start your own
            raise GenesisBlockIsRequired(account_id)
        genesis_block = Block.deserialize(block_bytes)
        # load height
        height = int(db.get(b"height"))
        # load 10 latest block to the memory
        latest_10 = deque([], maxlen=10)
        for block_num, block_bytes in db.iterator(start=str(max(0, height - 10)).encode()):
            latest_10.appendleft(Block.deserialize(block_bytes))
        return Blockchain(db, genesis_block, height, latest_10=latest_10)

    @staticmethod
    def to_key(key):
        if key in Blockchain.SPECIAL_KEYS:
            return key
        return "blk-%s".format(key).encode()

    def __init__(self, db, genesis_block, height, latest_10=None):
        """
        :param db: blockchain database connection
        :type db: plyvel.DB
        :param genesis_block: genesis block
        :type genesis_block: GenesisBlock|None
        :param height: number of blocks
        :type height: int
        :param latest_10: last 10 blocks
        :type latest_10: deque[Block]
        """
        self.db = db
        self.genesis_block = genesis_block
        self.height = height
        self.latest_10 = latest_10 or deque([self.genesis_block], maxlen=10)
        # TODO add transaction pool

    @property
    def head(self):
        """
        :return:
        :rtype: Block
        """
        return self.latest_10[0]

    def new_block(self, nonce, transactions):
        """
        Builds new block with set of transactions
        :param nonce:
        :param transactions:
        :return:
        """
        prev_hash = self.head.hash_parent
        # TODO implement new block
        raise NotImplementedError("Not implemented")
