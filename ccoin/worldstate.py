import plyvel
import json
from ccoin.accounts import Account
from ccoin.exceptions import TransactionBadNonce, TransactionSenderIsOutOfCoins, SenderStateDoesNotExist
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
        """
        :param db:
        :type db: plyvel.DB
        :param block_height:
        :param state_hash:
        """
        self.db = db
        self.height = block_height
        self.state_hash = state_hash
        self.cache = {}

    @staticmethod
    def key_prefix(block_number):
        return ("worldstate.blk-%s" % block_number).encode()

    @staticmethod
    def to_key(block_number, account_addr):
        return ("worldstate.blk-%s:account-%s" % (block_number, account_addr)).encode()

    def new_block(self, block_height):
        """
        Creates new block head with the state of previous block head.
        :param block_height:
        :return:
        """
        prev_block_height = self.height
        self.move_cursor(block_height)
        self.copy_state(prev_block_height)
        return prev_block_height

    def rollback_block(self, move_to_block_height):
        """
        Removes state with associated invalid block and activates `move_to_block_height`.
        :param move_to_block_height:
        :return: cleared (invalid) block number
        """
        invalid_block_height = self.height
        self.move_cursor(move_to_block_height)
        self.clear_block(invalid_block_height)
        return invalid_block_height

    def clear_block(self, block_height):
        """
        Removes all state associated with invalid block
        :param block_height:
        :return:
        """
        range_key = self.key_prefix(block_height)
        with self.db.iterator(prefix=range_key, include_value=False) as it, self.db.write_batch(transaction=True) as wb:
            for k in it:
                wb.delete(k)

    def copy_state(self, block_height):
        """Copies state from `block_height` to active `block_height` in write-batch transaction mode."""
        range_key = self.key_prefix(block_height)
        with self.db.iterator(prefix=range_key) as it, self.db.write_batch(transaction=True) as wb:
            for k, v in it:
                wb.put(k, v)

    def move_cursor(self, new_height):
        self.height = new_height

    def account_state(self, account_addr, create=False):
        """
        :param account_addr:
        :return: instance of AccountState
        :rtype: AccountState
        :raises: KeyError
        """
        if account_addr not in self.cache:
            key = self.to_key(self.height, account_addr)
            try:
                self.cache[account_addr] = AccountState(self.db[key])
            except KeyError:
                if create is False:
                    return None
                self.cache[account_addr] = AccountState(account_addr)
            finally:
                return self.cache.get(account_addr, None)

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

    def make_txn(self, from_, to, command=None, amount=None):
        """
        :param command: command details
        :type command: str
        :param from_: sender public key
        :type from_: str
        :param to: recipient public key
        :param amount: amount of money to send to
        :return: transaction reference
        :rtype: Transaction
        """
        sender = Account(from_)
        sender_state = self.account_state(sender.address)
        if sender_state is None:
            raise SenderStateDoesNotExist(from_)
        txn = Transaction(sender_state.nonce, from_, to=to, amount=amount, data=command)
        return txn

    def set_balance(self, addr, balance):
        account_state = self.account_state(addr)
        account_state.balance = balance

    def incr_balance(self, addr, increment_value):
        account_state = self.account_state(addr)
        account_state.balance += increment_value

    def incr_nonce(self, addr, increment_value):
        account_state = self.account_state(addr)
        account_state.nonce += increment_value

    def set_nonce(self, addr, nonce):
        account_state = self.account_state(addr)
        account_state.nonce = nonce

    def commit(self):
        if not self.cache:
            # nothing to cache
            # TODO may be log here
            return
        with self.db.write_batch(transaction=True) as wb:
            for account_addr, account_state in self.cache:
                account_key = self.to_key(self.height, account_addr)
                wb.put(account_key, account_state.serialize())
        self.set_state_hash(self.calculate_hash())

    def apply_txns(self, txn_list):
        """
        :param block:
        :type txn_list: ccoin.messages.TransactionList
        :return:
        :raises: TransactionApplyException
        """
        # TODO wrap in LEVELDB transaction
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
        recipient_state = self.account_state(transaction.recipient, create=True)
        if not sender_state or not (sender_state.nonce == transaction.number):
            raise TransactionBadNonce(transaction)
        # Check is enough balance to spend
        if sender_state.balance - transaction.amount < 0:
           raise TransactionSenderIsOutOfCoins(transaction)
        self.incr_nonce(transaction.sender, +1)
        self.incr_balance(transaction.sender, -1 * transaction.amount)
        self.incr_balance(transaction.recipient, -1 * transaction.amount)
        # Debig/Credit
        self.commit()
