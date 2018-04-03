import plyvel
import os
from twisted.python import log

from ccoin import settings
from ccoin.exceptions import BlockChainViolated, BlockTimeError, BlockWrongDifficulty, \
    BlockWrongNumber, BlockWrongTransactionHash, BlockPoWFailed, TransactionApplyException, BlockApplyException, \
    MiningGenesisBlockFailed
from ccoin.network_conf import NetworkConf
from ccoin.pow import verify as verify_pow, Miner
from ccoin.utils import ensure_dir, int2bytes
from .messages import Block, GenesisBlock


class Blockchain(object):

    SPECIAL_KEYS = (b"height",)

    @classmethod
    def load(cls, storage_path, db_name, account_id):
        """
        Loads blockchain with necessary properties and returns it
        :return: blockchain instance
        :rtype: Blockchain
        """
        ensure_dir(storage_path)
        db = plyvel.DB(os.path.join(storage_path, db_name), create_if_missing=True)
        # load genesis block
        block_bytes = db.get(cls.to_key(settings.GENESIS_BLOCK_NUMBER))
        if not block_bytes:
            return Blockchain(db, None, 0, None)
        genesis_block = None
        if block_bytes:
            # Attention: blockchain is empty (even genesis block is not generated)
            # Either request it from the network or start your own
            genesis_block = GenesisBlock.deserialize(block_bytes)

        # load height
        height = int(db.get(b"height"))
        # load head
        head_key = cls.to_key(b"height")
        head = db.get(head_key)
        return Blockchain(db, genesis_block, height, head)

    @classmethod
    def create_new(cls, storage_path, db_name, genesis_block):
        """
        Creates new blockchain with genesis block
        :param storage_path:
        :param db_name:
        :param genesis_block:
        :type genesis_block: GenesisBlock
        :return: blockchain instance
        :rtype: Blockchain
        """
        ensure_dir(storage_path)
        db = plyvel.DB(os.path.join(storage_path, db_name), create_if_missing=True)
        block_key = cls.to_key(genesis_block.number)
        db.put(block_key, genesis_block.serialize())
        db.put(b"height", int2bytes(genesis_block.number))
        return Blockchain(db, genesis_block, 0, genesis_block)

    @staticmethod
    def to_key(key):
        if key in Blockchain.SPECIAL_KEYS:
            return key
        return ("blk-%s" % key).encode()

    def __init__(self, db, genesis_block, height, head):
        """
        :param db: blockchain database connection
        :type db: plyvel.DB
        :param genesis_block: genesis block
        :type genesis_block: GenesisBlock|None
        :param height: number of blocks
        :type height: int
        :param head: latest block
        :type head: Block
        """
        self.db = db
        self.genesis_block = genesis_block
        self.height = height
        self.head = head

    def initialized(self):
        return self.genesis_block is not None

    def change_head(self, new_height):
        self.height = new_height
        self.head = self.db.get(self.to_key(new_height))
        self.db.put(b"height", self.height)

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
        :type block: ccoin.messages.Block
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
        if not verify_pow(block.difficulty, block.mining_hash, block.nonce, block.id):
            raise BlockPoWFailed(block)
        # 5. Let S[0] be the state at the end of the previous block.
        prev_block_height = self.new_block(worldstate, block)
        try:
            # 6. Let TX be the block's transaction list, with n transactions. For all i in 0...n-1, set S[i+1] = APPLY(S[i],TX[i]). If any applications returns an error, or if the total gas consumed in the block up until this point exceeds the GASLIMIT, return an error.
            worldstate.apply_txns(block.body)
        except TransactionApplyException:
            log.err()
            self.rollback_block(worldstate, block.number, prev_block_height)
            raise BlockApplyException(block)
        else:
            # 7. Let S_FINAL be S[n], but adding the block reward paid to the miner.
            worldstate.incr_balance(block.coinbase, self.genesis_block.miner_reward)
            new_state_root = worldstate.calculate_hash()
            # 8. Check if the Merkle tree root of the state S_FINAL is equal to the final state root provided in the block header.
            # If it is, the block is valid; otherwise, it is not valid.
            if new_state_root != block.hash_state:
                self.rollback_block(worldstate, block.number, prev_block_height)
                raise BlockApplyException(block)
            block.set_hash_state(new_state_root)

    def apply_genesis_block(self, worldstate):
        blk = self.genesis_block
        if blk is None or blk.number != 1:
            raise BlockApplyException(self.genesis_block)
        # 4. Check that transaction root is valid
        if blk.get_transactions_hash() != blk.hash_txns:
            raise BlockWrongTransactionHash(blk)
        # 5. Check that the proof of work on the block is valid.
        if not verify_pow(blk.difficulty, blk.mining_hash, blk.nonce, blk.id):
            raise BlockPoWFailed(blk)
        try:
            # 6. Let TX be the block's transaction list, with n transactions. For all i in 0...n-1, set S[i+1] = APPLY(S[i],TX[i]). If any applications returns an error, or if the total gas consumed in the block up until this point exceeds the GASLIMIT, return an error.
            worldstate.apply_txns(blk.body)
        except TransactionApplyException:
            log.err()
            raise BlockApplyException(blk)
        else:
            # 7. Let S_FINAL be S[n], but adding the block reward paid to the miner.
            new_state_root = worldstate.calculate_hash()
            # 8. Check if the Merkle tree root of the state S_FINAL is equal to the final state root provided in the block header.
            # If it is, the block is valid; otherwise, it is not valid.
            if new_state_root != blk.hash_state:
                raise BlockApplyException(blk)
            blk.set_hash_state(new_state_root)

    def rollback_block(self, worldstate, current_block_height, prev_block_height):
        """
        Delete block from chain and associated world state
        :param worldstate:
        :param current_block_height:
        :param prev_block_height:
        :return:
        """
        self.db.delete(self.to_key(self.height))
        self.change_head(prev_block_height)
        return worldstate.rollback_block(prev_block_height)

    def new_block(self, worldstate, block):
        """
        Delete block from chain and associated world state
        :param worldstate:
        :type worldstate: Worldstate
        :param block:
        :return:
        """
        block_key = self.to_key(block.number)
        self.db.put(block_key, block.serialize())
        self.change_head(block.number)
        return worldstate.new_block(block.number)

    def generate_block(self, transaction_pool):
        """
        Generates new block from a transaction pool, mines it and stores
        :param transaction_pool:
        :return: block
        :rtype: Block
        """
        raise NotImplementedError("")

    def mine_block(self, block):
        """
        Mines block
        Builds new block from transaction pool
        :param nonce:
        :param transaction_pool:
        :return: block
        """
        miner = Miner(block)
        blk = miner.mine()
        if blk is None:
            raise MiningGenesisBlockFailed(block)
        return blk
