import plyvel
import os
from twisted.python import log
from ccoin import settings
from ccoin.common import generate_block_data
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
    def load(cls, storage_path, db_name, account_id, **kwargs):
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
            return Blockchain(db, None, 0, None, **kwargs)
        genesis_block = None
        if block_bytes:
            # Attention: blockchain is empty (even genesis block is not generated)
            # Either request it from the network or start your own
            genesis_block = GenesisBlock.deserialize(block_bytes)

        # load height
        height = int(db.get(b"height"))
        # load head
        head_key = cls.to_key(height)
        head = Block.deserialize(db.get(head_key))
        return Blockchain(db, genesis_block, height, head, **kwargs)

    @classmethod
    def create_new(cls, storage_path, db_name, genesis_block, **kwargs):
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
        return Blockchain(db, genesis_block, 0, genesis_block, **kwargs)

    @staticmethod
    def to_key(key):
        if key in Blockchain.SPECIAL_KEYS:
            return key
        return ("blk-%s" % key).encode()

    def __init__(self, db, genesis_block, height, head, new_head_cb=None):
        """
        :param db: blockchain database connection
        :type db: plyvel.DB
        :param genesis_block: genesis block
        :type genesis_block: GenesisBlock|None
        :param height: number of blocks
        :type height: int
        :param head: latest block
        :type head: Block
        :param new_head_cb: callback executed once head is changed
        :type new_head_cb: callable
        """
        self.db = db
        self.genesis_block = genesis_block
        self.height = height
        self.head = head
        self.new_head_cb = new_head_cb

    def initialized(self):
        return self.genesis_block is not None

    def change_head(self, new_height):
        self.height = new_height
        self.head = Block.deserialize(self.db.get(self.to_key(new_height)))
        self.db.put(b"height", str(self.height).encode())

    def get_block(self, blk_number):
        """
        Loads block by block number from database.
        :param blk_number:
        :return:
        """
        blk_bytes = self.db.get(self.to_key(blk_number))
        if blk_bytes is None:
            return
        return Block.deserialize(blk_bytes)

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
        if isinstance(block, GenesisBlock):
            self.apply_genesis_block(block, worldstate)
        elif isinstance(block, Block):
            self.apply_next_block(block, worldstate)

    def apply_next_block(self, block, worldstate):
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
        if self.genesis_block.mine_difficulty != block.difficulty:
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
            worldstate.incr_balance(block.coinbase, block.reward)
            new_state_root = worldstate.commit()
            # 8. Check if the Merkle tree root of the state S_FINAL is equal to the final state root provided in the block header.
            # If it is, the block is valid; otherwise, it is not valid.
            log.msg("Comparing state with actual and expected: %s<>%s" % (new_state_root, block.hash_state))
            if new_state_root != block.hash_state:
                self.rollback_block(worldstate, block.number, prev_block_height)
                raise BlockApplyException(block)
            block.set_hash_state(new_state_root)
            if self.new_head_cb:
                self.new_head_cb(block)
            log.msg("Applied new block %s . Current height is %s" % (block.number, self.height))

    def apply_genesis_block(self, genesis_block, worldstate):
        if genesis_block is None or genesis_block.number != 1:
            raise BlockApplyException(self.genesis_block)
        # 4. Check that transaction root is valid
        if genesis_block.get_transactions_hash() != genesis_block.hash_txns:
            raise BlockWrongTransactionHash(genesis_block)
        # 5. Check that the proof of work on the block is valid.
        if not verify_pow(genesis_block.difficulty, genesis_block.mining_hash, genesis_block.nonce, genesis_block.id):
            raise BlockPoWFailed(genesis_block)
        # 6. Create Initial State from genesis configuration
        prev_block_height = self.new_block(worldstate, genesis_block)
        worldstate.from_genesis_block(genesis_block, commit=True)
        # 7. Let S_FINAL be S[n], but adding the block reward paid to the miner.
        hash_state = worldstate.hash_state
        # 8. Check if the Merkle tree root of the state S_FINAL is equal to the final state root provided in the block header.
        # If it is, the block is valid; otherwise, it is not valid.
        if hash_state != genesis_block.hash_state:
            self.rollback_block(worldstate, genesis_block.number, prev_block_height)
            raise BlockApplyException(genesis_block)
        genesis_block.set_hash_state(hash_state)
        # set genesis block
        self.genesis_block = genesis_block
        if self.new_head_cb:
            self.new_head_cb(genesis_block)

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

    def create_candidate_block(self, coinbase):
        number = self.height + 1
        assert number > settings.GENESIS_BLOCK_NUMBER, "Genesis block should be defined differently"
        parent = self.head
        block = Block(number=number,
                      hash_parent=parent.id,
                      body=None,
                      coinbase=coinbase,
                      hash_state=self.head.hash_state,
                      hash_txns=None,
                      data=generate_block_data(self.genesis_block.blk_placeholder_config),
                      reward=self.genesis_block.miner_reward,
                      difficulty=self.genesis_block.mine_difficulty)
        block.set_timestamp()
        return block

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
