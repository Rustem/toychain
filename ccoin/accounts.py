import os
from twisted.internet import defer
from ccoin.base import Serializable, SharedDatabaseServiceMixin
from ccoin.security import generate_key_pair, load_private_key


class Account(Serializable):
    """Defines account object inside the simple blockchain network."""

    def __init__(self, id, private_key=None, public_key=None, key_path=None, balance=0, is_miner=False, nonce=0):
        self.id = id
        self.private_key = private_key
        self.public_key = public_key
        self.balance = balance
        self.is_miner = is_miner
        self.key_path = key_path
        self.nonce = nonce

    def load_private_key(self):
        if not self.private_key and self.key_path:
            with open(self.key_path, 'rb') as fh:
                self.private_key = fh.read()
        return self.private_key

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
            "balance": self.balance,
            "is_miner": self.is_miner,
            "nonce": self.nonce}
        if self.is_activated:
            data.update({"public_key": self.public_key,
                         "key_path": self.key_path})
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(id=data["id"],
                   is_miner=data.get("is_miner", False),
                   balance=data.get("balance"),
                   key_path=data.get("key_path"),
                   public_key=data.get("public_key", None),
                   nonce=data.get("nonce", 0))

class AccountManager(SharedDatabaseServiceMixin):

    def __init__(self):
        super(AccountManager, self).__init__()
        self.key_path = os.path.join(self.base_path, '.keys')

    @defer.inlineCallbacks
    def initialize(self):
        self.ensure_dirs()
        yield super(AccountManager, self).initialize()

    @defer.inlineCallbacks
    def ensure_table(self):
        yield self.db.runInteraction(self.exec_create_table)

    def ensure_dirs(self):
        if not os.path.exists(self.key_path):
            os.makedirs(self.key_path)

    @staticmethod
    def exec_create_table(cursor):
        cursor.execute("""
              CREATE TABLE IF NOT EXISTS accounts (
                id text PRIMARY KEY,
                public_key text NULL,
                balance integer DEFAULT 0,
                is_miner integer DEFAULT 0,
                key_path text NULL,
                nonce integer DEFAULT 0)
            """)

    @staticmethod
    def tuple_to_dict(account_tuple):
        return {
            "id": account_tuple[0],
            "public_key": account_tuple[1],
            "balance": account_tuple[2],
            "is_miner": account_tuple[3],
            "key_path": account_tuple[4],
            "nonce": account_tuple[5]
        }

class AccountCreator(AccountManager):

    def full_key_path(self, user_id):
        return os.path.join(self.key_path, "%s.key" % user_id)

    def create(self, user_id, **kwargs):
        account = Account(user_id, **kwargs)
        if not account.is_activated:
            # Generate and store key
            account.generate_keypair()
            account.key_path = self.store_key(account.id, account.private_key)
        defer = self.db.runInteraction(self.q_create_account, **account.to_dict())
        defer.addCallback(lambda *args: account)
        return defer

    @staticmethod
    def q_create_account(cursor, id=None, public_key=None, balance=0, is_miner=False, key_path=None, nonce=None):
        cursor.execute("INSERT OR REPLACE INTO accounts VALUES(?, ?, ?, ?, ?, ?)",
                       (id, public_key, balance, is_miner, key_path, nonce))

    def store_key(self, user_id, private_key):
        full_key_path = self.full_key_path(user_id)
        with open(full_key_path, "wb") as fh:
            fh.write(private_key.encode())
        return full_key_path


class AccountUpdater(AccountManager):

    def __init__(self, account):
        super(AccountUpdater, self).__init__()
        self.account = account

    @defer.inlineCallbacks
    def increment_nonce(self):
        self.account.nonce += 1
        yield self.db.runInteraction(self.q_increment_nonce, self.account.nonce, self.account.id)

    @staticmethod
    def q_increment_nonce(cursor, nonce, account_id):
        cursor.execute("UPDATE accounts SET nonce = ? WHERE id = ?", (nonce, account_id,))

class AccountProvider(AccountManager):

    @defer.inlineCallbacks
    def get_by_id(self, account_id, with_private_key=False):
        """
        Returns Account object found by its identifier.
        :param account_id: unique account identifier
        :type account_id: str
        :param with_private_key: flag if set then loads private key to the returned object
        :type with_private_key: bool
        :return: Account object
        :rtype: Account
        """
        result = yield self.db.runQuery('SELECT * FROM accounts WHERE id=?', account_id)
        if not result:
            return None
        account_data = self.tuple_to_dict(result[0])
        account = Account.from_dict(account_data)
        if with_private_key:
            account.load_private_key()
        defer.returnValue(account)