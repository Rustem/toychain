import msgpack
import time
import json

from ccoin import settings
from ccoin.accounts import Account
from ccoin.security import hash_map, sign, verify, hash_message
from .exceptions import MessageDeserializationException, TransactionNotVerifiable, TransactionBadSignature, \
    AccountDoesNotExist
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

    @classmethod
    def coinbase(cls, number, to, reward):
        return Transaction(number, None, to=to, amount=reward)

    def __init__(self, number, from_, to=None, id=None, amount=0, data=None, signature=None):
        self.id = id
        self.number = number
        self.from_ = from_
        self.to = to
        self.amount = amount
        self.data = data
        # RSA signature
        self.signature = signature

    @property
    def sender(self):
        return self.from_

    @property
    def recipient(self):
        return self.to

    def generate_id(self):
        if self.id is None:
            self.id = self.get_hash()
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
                   amount=data.get("amount", None),
                   data=data.get("data", None),
                   signature=data.get("signature", None),)


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
        self.txns = txns

    def calc_hash(self):
        txn_ids = [txn.id for txn in self.txns]
        return hash_message(msgpack.packb(txn_ids))

    def __iter__(self):
        return self.txns

    def to_dict(self):
        rv = []
        for txn in self.txns:
            rv.append(txn.to_dict())
        return rv

    @property
    def coinbase(self):
        return self.txns[0]


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

    def __init__(self, number, hash_parent, body, hash_state=None, id=None, hash_txns=None,
                 data=None, nonce=0, time=None, reward=DEFAULT_REWARD, difficulty=DEFAULT_DIFFICULTY):
        self.number = number
        self.id = id
        self.hash_state = hash_state
        self.hash_parent = hash_parent
        self.hash_txns = hash_txns
        self.body = TransactionList(body)
        self.data = data
        self.nonce = nonce
        self.time = time
        self.reward = reward
        self.difficulty = difficulty

        if self.hash_txns is None and body:
            self.get_transactions_hash()

    @property
    def coinbase_txn(self):
        """Return coinbase transaction"""
        return self.body.coinbase

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
        return cls(
            number=data["number"],
            hash_parent=data["hash_parent"],
            body=[Transaction.from_dict(t) for t in data["body"]],
            id=data.get("id"),
            hash_txns=data.get("hash_txns"),
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
            "genesis_block": config["genesis_block"]}
        json_data = json.dumps(data)
        genesis_block = cls(number=1,
                            hash_parent=settings.BLANK_SHA_256,
                            body=None,
                            data=json_data,
                            nonce=1,)
        if "difficulty" in data["genesis_block"]:
            genesis_block.difficulty = data["genesis_block"]["difficulty"]
        if "coinbase" in data["genesis_block"]:
            genesis_data = data["genesis_block"]
            # load coinbase account to get his private key
            coinbase_account = Account.fromAddress(genesis_data["coinbase"])
            if coinbase_account is None:
                raise AccountDoesNotExist(genesis_data["coinbase"])
            private_key = coinbase_account.load_private_key()
            # Generate coinbase transaction and sign it with coinbase account's private key
            coinbase_txn = Transaction.coinbase(1, genesis_data["coinbase"], genesis_data["coinbase_reward"])
            coinbase_txn.generate_id()
            coinbase_txn.sign(private_key)
            genesis_block.set_transactions([coinbase_txn])
            genesis_block.get_transactions_hash()
        genesis_block.set_timestamp()
        return genesis_block

    def __init__(self, *args, **kwargs):
        super(GenesisBlock, self).__init__(*args, **kwargs)
        self.loaded_data = json.loads(self.data)

    def get_miners(self):
        """Returns miners's addresses list."""
        return self.loaded_data["miners"]

    def can_mine(self, address):
        """Returns flag whether address is allowed to mine new blocks."""
        return address in self.get_miners()