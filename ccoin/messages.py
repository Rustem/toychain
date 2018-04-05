import random

import msgpack
import time
import json

from ccoin import settings
from ccoin.security import hash_map, sign, verify, hash_message
from .exceptions import MessageDeserializationException, TransactionNotVerifiable, TransactionBadSignature
from abc import ABC, abstractmethod, abstractclassmethod


class BaseMessage(ABC):

    identifier = None

    @classmethod
    def deserialize(cls, bytes):
        """
        Returns original message instance
        :param bytes: message represented in bytes
        :type bytes: bytes
        :return: message instance
        :rtype: Message
        """
        msg_type = bytes[:3].decode()
        if cls.identifier != msg_type:
            raise MessageDeserializationException(cls.identifier, msg_type)
        return cls.from_dict(cls.loads(bytes[3:]))

    def serialize(self):
        """
        Returns bytes representing the object
        :return: bytes
        :rtype: bytes
        """
        msg_bytes = self.dumps(self.to_dict())
        return self.identifier.encode() + msg_bytes

    @abstractmethod
    def to_dict(self):
        """
        Returns python dictionary
        :return: dict representation
        :rtype: dict[any]
        """
        pass

    @classmethod
    @abstractclassmethod
    def from_dict(self, data):
        """
        Returns original message instance
        :param data: message represented with python dict
        :type data: bytes
        :return: message instance
        :rtype: Message
        """
        pass

    @staticmethod
    def dumps(ds):
        return msgpack.packb(ds)

    @staticmethod
    def loads(bytes):
        return msgpack.unpackb(bytes, raw=False)


class Transaction(BaseMessage):
    """Encapsulates transaction data structure and behaviour.

    Attributes:
        id (str): hash of the transaction
        number (int): transaction index id.
        to (str): address of the recipient account.
        from_ (str): address of the sender account.
        amount (int): amount of money spent by sender and credited to the recipient
        data (varies): attached data
        signature: RSA signature created from the transaction message with sender's private key
    """
    identifier = "TXN"

    def __init__(self, number, from_, to=None, id=None, amount=0, data=None, signature=None, time=None):
        self.id = id
        self.number = number
        self.from_ = from_
        self.to = to
        self.amount = amount
        self.data = data
        self.time=time
        # RSA signature
        self.signature = signature

    @property
    def sender(self):
        return self.from_

    @property
    def recipient(self):
        return self.to

    @property
    def nonce(self):
        return self.number

    def generate_id(self):
        if self.id is None:
            self.id = self.get_hash()
        self.time = time.time()
        return self.id

    def get_hash(self):
        """Generates transaction hash."""
        data = self.to_dict()
        data.pop("signature", None)
        return hash_map(data)

    @property
    def is_signed(self):
        return self.signature is not None

    def sign(self, private_key):
        """Signs transaction with account’s secret key and returns signature. Sets signature and sender's public key"""
        msg_bytes = self.serialize()
        if self.signature is None:
            self.signature = sign(private_key, msg_bytes)
        return self.signature

    def verify(self):
        """Verifies signatures of transaction"""
        if self.signature is None:
            raise TransactionNotVerifiable(self)
        if verify(self.signature, self.serialize(), self.from_):
            return
        raise TransactionBadSignature(self)

    def to_dict(self):
        data = {
            "id": self.id,
            "number": self.number,
            "to": self.to,
            "from": self.from_,
            "time": self.time,
            "amount": self.amount,}
        if self.data is not None:
            data["data"] = self.data
        if self.is_signed:
            data["signature"] = self.signature
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(id=data.get("id", None),
                   number=data["number"],
                   to=data["to"],
                   from_=data["from"],
                   time=data.get("time", None),
                   amount=data.get("amount", None),
                   data=data.get("data", None),
                   signature=data.get("signature", None),)


class CoinbaseTransaction(Transaction):

    def __init__(self, number, from_to, id=None, amount=0, data=None, signature=None):
        super(CoinbaseTransaction, self).__init__(number,
                                                  from_=from_to,
                                                  to=from_to,
                                                  id=id,
                                                  amount=amount,
                                                  data=data,
                                                  signature=signature)

class TransactionList(object):
    """Represents immutable list of transactions.

        Attributes:
            txns (list): list of transactions
    """

    def __init__(self, txns):
        """
        :param txns: transaction list
        :type txns: list[Transaction]
        """
        self.txns = txns or []

    def calc_hash(self):
        if not self.txns:
            return settings.BLANK_SHA_256
        txn_ids = [txn.id for txn in self.txns]
        return hash_message(msgpack.packb(txn_ids))

    def __iter__(self):
        return iter(self.txns)

    def to_dict(self):
        rv = []
        for txn in self.txns:
            rv.append(txn.to_dict())
        return rv


class Block(BaseMessage):
    """Represents immutable block data structure.

        Attributes:
            number (int): block’s height in the chain
            id (str): hash of the block
            hash_parent (str): hash of previous block
            hash_state (str): hash of world state
            hash_txns (str): hash of transactions included in the block
            body (TransactionList): list of all transactions being included in the block
            data (varies): extra data e.g. genesis block that contains miners addresses
            nonce (int): 32-bit number (starts at 0)
            time (float): Mining timestamp as seconds since 1970-01-01T00:00 UTC
            reward (int): reward for the block to miners
    """

    identifier = "BLK"
    DEFAULT_REWARD = 100
    DEFAULT_DIFFICULTY = 4  # four zeroes

    def __init__(self, number, hash_parent, body, coinbase=None, hash_state=None, id=None, hash_txns=None,
                 data=None, nonce=0, time=None, reward=DEFAULT_REWARD, difficulty=DEFAULT_DIFFICULTY):
        self.number = number
        self.id = id
        self.hash_state = hash_state
        self.hash_parent = hash_parent
        self.hash_txns = hash_txns
        self.body = TransactionList(body)
        self.coinbase = coinbase   # coinbase address
        self.data = data
        self.nonce = nonce
        self.time = time
        self.reward = reward
        self.difficulty = difficulty

        if self.hash_txns is None:
            self.get_transactions_hash()

    @property
    def is_mined(self):
        return self.time is not None

    @property
    def mining_hash(self):
        return self.get_hash()

    def set_timestamp(self):
        if not self.time:
            self.time = time.time()

    def set_hash_state(self, hash_state):
        if not self.hash_state:
            self.hash_state = hash_state

    def set_transactions(self, txns):
        self.body = TransactionList(txns)

    def get_transactions_hash(self):
        if not self.hash_txns:
            self.hash_txns = self.body.calc_hash()
        return self.hash_txns

    def get_hash(self):
        concat_str = str(self.number) + self.hash_parent + self.hash_state + self.hash_txns + str(self.time)
        if self.data:
            concat_str += self.data
        concat_bytes = concat_str.encode()
        return hash_message(concat_bytes)

    def get_pow_hash(self, nonce, block_hash):
        concat_str = "%s%s" % (nonce, block_hash)
        return hash_message(concat_str.encode())

    @classmethod
    def deserialize(cls, bytes):
        """
        Deserializes block depending on its type.
        Supported types: Block, GenesisBlock
        :param bytes:
        :return:
        """
        blk_registry = {cls.identifier: cls}
        for kls in Block.__subclasses__():
            blk_registry[kls.identifier] = kls
        blk_type = bytes[:3].decode()
        if blk_type not in blk_registry:
            raise MessageDeserializationException(cls.identifier, blk_type)
        kls = blk_registry.get(blk_type)
        return kls.from_dict(kls.loads(bytes[3:]))

    def to_dict(self):
        data = {
            "number": self.number,
            "hash_parent": self.hash_parent,
            "hash_state": self.hash_state,
            "hash_txns": self.hash_txns,
            "body": self.body.to_dict(),
            "data": self.data,
            "reward": self.reward,
            "difficulty": self.difficulty
        }
        if self.is_mined:
            data["id"] = self.id
            data["nonce"] = self.nonce
            data["time"] = self.time
        return data

    @classmethod
    def from_dict(cls, data):
        if cls == Block and data["number"] == settings.GENESIS_BLOCK_NUMBER:
            return GenesisBlock.from_dict(data)
        return cls(
            id=data.get("id"),
            number=data["number"],
            hash_parent=data["hash_parent"],
            hash_state=data["hash_state"],
            hash_txns=data.get("hash_txns"),
            body=[Transaction.from_dict(t) for t in data["body"]],
            data=data.get("data"),
            nonce=data.get("nonce", 0),
            time=data.get("time"),
            reward=data.get("reward", cls.DEFAULT_REWARD),
            difficulty=data.get("difficulty", cls.DEFAULT_DIFFICULTY)
        )


class GenesisBlock(Block):
    """Represents immutable genesis block data structure.
        Attributes:
            loaded_data: contains information about miners and their addresses
    """

    identifier = "GLK"   # genesis block

    @classmethod
    def loadFromConfig(cls, config):
        """
        {
            "miners": ["12312412412fajkdsfj1424", "124j1k2jrkfjakj124j12"],
            "block_mining": {
                "interval": 60 * 10,  # 10 minutes
                "max_bound": 100,  # hundred transactions per block is max
                "min_bound": 10, # 10 transactions per block is min
                "reward": 100, # 100 coins is coinbase transaction in every block mined by miner
                "difficulty": 4,
                "allow_empty": true, # allow empty block
                "placeholder_data": ["rnd", 15] # if empty block get mined it will be extended with extra 15 bits of data
            },
            "network_id": 1,
            "max_peers": 0, # maximum amount of peers per node (if 0 => unlimited)
            "coinbase": "12412", # hex representation of the address who will be awarded with coins
        }
        :param config:
        :return:
        """
        data = {
            "miners": config["miners"],
            "block_mining": config["block_mining"],
            "network_id": config["network_id"],
            "max_peers": config["max_peers"],
            "genesis_block": config["genesis_block"],
            "alloc": config["alloc"]}
        json_data = json.dumps(data)
        genesis_block = cls(number=settings.GENESIS_BLOCK_NUMBER,
                            hash_parent=settings.BLANK_SHA_256,
                            body=None,
                            data=json_data,
                            nonce=1,)
        if "difficulty" in data["genesis_block"]:
            genesis_block.difficulty = data["genesis_block"]["difficulty"]
        if "txns" in data:
            # TODO apply initial transactions
            pass
        genesis_block.set_timestamp()
        return genesis_block

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.loaded_data = json.loads(self.data)

    @property
    def miner_reward(self):
        return self.loaded_data["block_mining"]["reward"]

    def get_miners(self):
        """Returns miners's addresses list."""
        return self.loaded_data["miners"]

    def can_mine(self, address):
        """Returns flag whether address is allowed to mine new blocks."""
        return address in self.get_miners()


class BaseRequestMessage(BaseMessage):

    def __init__(self, address, request_id=None):
        """
        :param address: sender address
        :type address: str
        :param request_id:
        """
        self.address = address
        self.request_id = request_id

    def gen_request_id(self):
        return "%s_%s" % (self.identifier, random.randint(1, 100000) * random.randint(1, 100000))


class HelloMessage(BaseRequestMessage):

    identifier = "HEY"

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "address": self.address,
        }

    @classmethod
    def from_dict(cls, data):
        return HelloMessage(data["address"], data["request_id"])


class HelloAckMessage(HelloMessage):
    identifier = "ACK"


class RequestBlockHeight(BaseRequestMessage):

    identifier = "RBH"

    def __init__(self, block_number, address, request_id=None):
        super().__init__(address, request_id)
        self.block_number = block_number

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "block_number": self.block_number,
            "address": self.address
        }

    @classmethod
    def from_dict(self, data):
        return RequestBlockHeight(data["block_number"], data["address"], data["request_id"])


class ResponseBlockHeight(RequestBlockHeight):
    identifier = "BLH" # block height


class RequestBlockList(BaseRequestMessage):

    identifier = "RBL"

    def __init__(self, start_from_block, address, request_id=None):
        super().__init__(address, request_id)
        self.start_from_block = start_from_block

    def to_dict(self):
        return {
            "request_id": self.request_id,
            "start_from_block": self.start_from_block,
            "address": self.address
        }

    @classmethod
    def from_dict(self, data):
        return RequestBlockList(data["start_from_block"], data["address"], data["request_id"])


class ResponseBlockList(BaseRequestMessage):
    identifier = "ABL"

    def __init__(self, blocks, address, request_id=None):
        """
        :param blocks:
        :type blocks: list[any]
        :param address:
        :param request_id:
        """
        super().__init__(address, request_id)
        if blocks:
            if isinstance(blocks[0], bytes):
                blocks = [Block.deserialize(b) for b in blocks]
            elif isinstance(blocks[0], dict):
                blocks = [Block.from_dict(b) for b in blocks]
        self.blocks = blocks

    def to_dict(self):
        return {"request_id": self.request_id,
                "address": self.address,
                "blocks": [blk.to_dict() for blk in self.blocks],}

    @classmethod
    def from_dict(cls, data):
        return ResponseBlockList(data["blocks"],
                                 data["address"],
                                 data["request_id"])