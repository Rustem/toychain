import msgpack
from ccoin.security import hash_map, sign
from .exceptions import MessageDeserializationException
from abc import ABC, abstractmethod, abstractclassmethod


class BaseMessage(ABC):

    identifier = None

    @classmethod
    def unserialize(cls, bytes):
        """
        Returns original message instance
        :param bytes: message represented in bytes
        :type bytes: bytes
        :return: message instance
        :rtype: Message
        """
        msg_type = bytes[:3].decode()
        if cls.identifier != msg_type:
            raise MessageDeserializationException(self.identifier, msg_type)
        return cls.from_dict(cls.loads(bytes[3:]))

    def serialize(self):
        """
        Returns bytes representing the object
        :return: bytes
        :rtype: bytes
        """
        msg_bytes = self.dumps(self.to_dict())
        return "b" + self.identifier.encode() + msg_bytes

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
        amount (int): amount of money spent by sender and credited to the recipient
        data (varies): attached data
        signature:
    """
    identifier = "TXN"

    def __init__(self, number, from_, to, id=None, amount=0, data=None, signature=None):
        self.id = id
        self.number = number
        self.to = to
        self.from_ = from_
        self.amount = amount
        self.data = data

        # RSA signature
        self.signature = signature

    @property
    def hash(self):
        """Generates transaction id by hashing it."""
        if self.id is None:
            self.id = hash_map(self.to_dict())
        return self.id

    @property
    def is_signed(self):
        return self.signature is not None

    def sign(self, private_key):
        """Signs transaction with account’s secret key and returns signature. Sets signature and sender's public key"""
        msg_bytes = self.serialize()
        if self.signature is None:
            self.signature = sign(private_key, msg_bytes)
        return self.signature

    def to_dict(self):
        data = {
            "id": self.hash,
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
