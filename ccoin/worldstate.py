import plyvel
import json
from ccoin.exceptions import TransactionBadNonce, TransactionSenderIsOutOfCoins
from ccoin.messages import Transaction
from ccoin.security import hash_message
from ccoin.utils import ensure_dir


class AccountState(object):

    def __init__(self, public_key, nonce=0, balance=0):
        self.public_key = public_key
        self.address = self.public_key[115:155]
        self.nonce = nonce
        self.balance = balance

    @classmethod
    def deserialize(cls, bytes):
        """
        Returns original message instance
        :param bytes: message represented in bytes
        :type bytes: bytes
        :return: message instance
        :rtype: Message
        """
        return cls.from_dict(cls.loads(bytes[3:]))

    def serialize(self):
        """
        Returns bytes representing the object
        :return: bytes
        :rtype: bytes
        """
        return self.dumps(self.to_dict())

    def to_dict(self):
        """
        Returns python dictionary
        :return: dict representation
        :rtype: dict[any]
        """
        return {
            "public_key": self.public_key,
            "nonce": self.nonce,
            "balance": self.balance
        }

    @classmethod
    def from_dict(self, data):
        """
        Returns original message instance
        :param data: message represented with python dict
        :type data: dict
        :return: message instance
        :rtype: Message
        """
        return AccountState(**data)

    @staticmethod
    def dumps(ds):
        return json.dumps(ds).encode(encoding="utf-8")

    @staticmethod
    def loads(bytes):
        return json.loads(bytes, encoding="utf-8")


class WorldState(object):

    SPECIAL_KEYS = (b"state_hash",)


    @classmethod
    def load(cls, state_path, block_height):
        """
        Initializes Worldstate with necessary properties and returns it
        :return: worldstate instance
        :rtype: WorldState
        """
        ensure_dir(state_path)
        db = plyvel.DB(state_path, create_if_missing=True)
        state_hash = db.get(b"state_hash", None)
        return WorldState(db, block_height, state_hash)

    def __init__(self, db, block_height, state_hash=None):
        self.db = db
        self.height = block_height
        self.state_hash = state_hash

    @staticmethod
    def to_key(block_number, account_addr):
        return "worldstate.blk-%s:account-%s".format(block_number, account_addr).encode()

    def new_block(self, block_height):
        prev_block_height = self.height
        self.move_cursor(block_height)
        # TODO copy previous state
        return prev_block_height

    def move_cursor(self, new_height):
        self.height = new_height

    def account_state(self, account_addr, create=False):
        """
        :param account_addr:
        :return: instance of AccountState
        :rtype: AccountState
        :raises: KeyError
        """
        key = self.to_key(self.height, account_addr)
        try:
            return self.db[key]
        except KeyError:
            if create is False:
                return None
            return AccountState(account_addr)

    def update_account_state(self, account_state):
        self.db[account_state.address] = account_state.serialize()

    def set_state_hash(self, state_hash):
        self.state_hash = state_hash
        self.db[b"state_hash"] = self.state_hash

    def calculate_hash(self):
        concat = []
        for state_key, state_bytes in self.db:
            concat.append(state_key + state_bytes)
        if not concat:
            return
        concat_bytes = b"|".join(concat)
        return hash_message(concat_bytes)

    def make_txn(self, command=None, to=None, amount=None):
        """
        :param command: command details
        :type command: str
        :param to: recipient address
        :param amount: amount of money to send to
        :return: transaction id
        :rtype: str
        """
        txn = Transaction(self.account.nonce, self.account.public_key, to=to, amount=amount, data=command)
        return txn

    def apply_txns(self, txn_list):
        """
        :param block:
        :type txn_list: ccoin.messages.TransactionList
        :return:
        :raises: TransactionApplyException
        """
        for txn in txn_list:
            self.apply_txn(txn)

    def apply_txn(self, transaction):
        """
        Changes the state by applying transaction
        :param transaction:
        :type transaction: ccoin.messages.Transaction
        :raises: TransactionApplyException
        """
        # check transaction is well-formed: the signature is valid, and the nonce matches the nonce
        # in the sender's account. If not, return an error
        transaction.verify()
        # Check nonce matches the sender's account
        sender_state = self.account_state(transaction.sender)
        recipient_state = self.account_state(transaction.recipient)
        if not sender_state or not (sender_state.nonce == transaction.number):
            raise TransactionBadNonce(transaction)
        # Check is enough balance to spend
        if sender_state.balance - transaction.amount < 0:
           raise TransactionSenderIsOutOfCoins(transaction)
        sender_state.nonce += 1
        # Debig/Credit
        sender_state.balance -= transaction.amount
        recipient_state.balance += transaction.amount
        self.update_account_state(sender_state)
        self.update_account_state(recipient_state)
