from ccoin.base import Serializable
from ccoin.p2p_network import BasePeer
from ccoin.security import generate_key_pair


class AccountManager(object):

    def __init__(self, account):
        self.account = account
        self.ensure_tables()

    def save(self):
        pass

# ~/.ccoin/blockchain
# ~/.ccoin/.keys/
# ~/.ccoin/config.json

# TODO 0. Setup restful server on differnet port
# TODO 1. Command line & Restful API utility that creates accounts
#     Account is created with keys
#     Private key is stored under # ~/.ccoin/.keys/
#     Private key is loaded when node itself is started to listen

# TODO 2. Node can connect to P2P Network with already loaded account
# TODO 3. P2P listen Port select automatically
# TODO 4. Node can send transactions signed by account's private key



class Account(Serializable):
    """Defines account object inside the simple blockchain network."""

    def __init__(self, id, private_key=None, public_key=None, balance=0, is_miner=False):
        self.id = id
        self.private_key = private_key
        self.public_key = public_key
        self.balance = balance
        self.is_miner = is_miner

    @property
    def is_activated(self):
        return self.public_key is not None

    @property
    def address(self):
        return self.public_key

    def generate_keypair(self):
        """Generates private/public key pair."""
        self.private_key, self.public_key = generate_key_pair()


    def to_dict(self):
        data = {
            "id": self.id,
            "balance": self.balance}
        if self.is_activated:
            data.update({
                "private_key": self.private_key,
                "public_key": self.public_key})

    @classmethod
    def from_dict(cls, data):
        return cls({
            "id": data["id"],
            "private_key": data.get("private_key"),
            "public_key": data.get("public_key", None),
            "balance": data.get("balance")
        })


class Node(BasePeer):

    def __init__(self, uuid):
        super(Node, self).__init__(uuid)
        self.account = AccountManager.load_account(uuid)

