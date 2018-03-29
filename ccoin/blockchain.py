import plyvel
import os
from collections import deque
from twisted.python import log
from ccoin.exceptions import GenesisBlockIsRequired, BlockChainViolated, BlockTimeError, BlockWrongDifficulty, \
    BlockWrongNumber, BlockWrongTransactionHash, BlockPoWFailed, TransactionApplyException, BlockApplyException
from ccoin.network_conf import NetworkConf
from .messages import Block, GenesisBlock


class Blockchain(object):

    SPECIAL_KEYS = (b"height",)

    @classmethod
    def load(cls, chain_path, account_id):
        """
        Loads blockchain with necessary properties and returns it
        :return: blockchain instance
        :rtype: Blockchain
        """
        if not os.path.exists(chain_path):
            # Attention: blockchain is empty (even genesis block is not generated)
            # Either request it from the network or start your own
            raise GenesisBlockIsRequired(account_id)
        db = plyvel.DB(chain_path, create_if_missing=False)
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
        start_key = cls.to_key(max(0, height - 10))
        stop_key = cls.to_key(height)
        for block_num, block_bytes in db.iterator(start=start_key, stop=stop_key):
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

    def mine_block(self, block):
        raise NotImplementedError("")

    def apply_blocks(self, blocks, worldstate):
        """
        :param blocks:
        :param worldstate:
        :return:
        :raises: BlockApplyException
        """
        for block in blocks:
            self.apply_block(block, worldstate)

    def apply_block(self, block, worldstate):
        """
        :param block:
        :param worldstate: ccoin.worldstate.Worldstate
        :return:
        :raises: BlockApplyException
        """
        # 1. Check if the previous block referenced exists and is valid.
        if self.head.id != block.hash_parent:
            raise BlockChainViolated(block)
        # 2. Check that the timestamp of the block is greater than that of the referenced previous block
        if block.time <= self.head.time:
            raise BlockTimeError(block)
        # 3. Check that the block number, difficulty, transaction root are valid.
        if NetworkConf["block_mining"]["difficulty"] != block.difficulty:
            raise BlockWrongDifficulty(block)
        if block.number != self.head.number + 1:
            raise BlockWrongNumber(block)
        # 4. Check that transaction root is valid
        if block.get_transactions_hash() != block.hash_txns:
            raise BlockWrongTransactionHash(block)
        # 5. Check that the proof of work on the block is valid.
        if not block.verify():
            raise BlockPoWFailed(block)
        # 5. Let S[0] be the state at the end of the previous block.
        # 6. Let TX be the block's transaction list, with n transactions. For all i in 0...n-1, set S[i+1] = APPLY(S[i],TX[i]). If any applications returns an error, or if the total gas consumed in the block up until this point exceeds the GASLIMIT, return an error.
        # 7. Let S_FINAL be S[n], but adding the block reward paid to the miner.
        prev_block_height = worldstate.new_block(block.number)
        try:
            worldstate.apply_txns(worldstate)
        except TransactionApplyException:
            log.err()
            self.rollback_block(block.number, prev_block_height)
            raise BlockApplyException(block)
        else:
            new_state_root = worldstate.calculate_hash()
            # 8. Check if the Merkle tree root of the state S_FINAL is equal to the final state root provided in the block header.
            # If it is, the block is valid; otherwise, it is not valid.
            if new_state_root != block.state_root:
                self.rollback_block(block.number, prev_block_height)
                raise BlockApplyException(block)
            worldstate.set_hash_state(new_state_root)


    def rollback_block(self, current_block_height, prev_block_height):
        # TODO remove state of current block
        # TODO move cursor to previous block
        raise NotImplementedError("")

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
