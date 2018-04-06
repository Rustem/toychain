import plyvel
import json
import os
from ccoin.accounts import Account
from ccoin.app_conf import AppConfig
from ccoin.exceptions import TransactionBadNonce, TransactionSenderIsOutOfCoins, SenderStateDoesNotExist
from ccoin.messages import Transaction
from ccoin.security import hash_message
from ccoin.utils import ensure_dir


class AccountState(object):

    def __init__(self, address, nonce=0, balance=0):
        self.address = address
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
        data = dict(cls.loads(bytes.decode()))
        return cls.from_dict(data)

    def serialize(self):
        """
        Returns bytes representing the object
        :return: bytes
        :rtype: bytes
        """
        sorted_data = sorted(self.to_dict().items())
        return self.dumps(sorted_data)

    def to_dict(self):
        """
        Returns python dictionary
        :return: dict representation
        :rtype: dict[any]
        """
        return {
            "address": self.address,
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
    def loads(json_data):
        return json.loads(json_data)


class WorldState(object):

    SPECIAL_KEYS = (b"hash_state",)


    @classmethod
    def load(cls, storage_path, db_name, block_height):
        """
        Initializes Worldstate with necessary properties and returns it
        :return: worldstate instance
        :rtype: WorldState
        """
        ensure_dir(storage_path)
        db = plyvel.DB(os.path.join(storage_path, db_name), create_if_missing=True)
        hash_state = db.get(b"hash_state", None)
        if hash_state:
            hash_state = hash_state.decode()
        return WorldState(db, block_height, hash_state)

    def __init__(self, db, block_height, hash_state=None):
        """
        :param db:
        :type db: plyvel.DB
        :param block_height:
        :param hash_state:
        """
        self.db = db
        self.height = block_height
        self.hash_state = hash_state
        self.cache = {}

    @staticmethod
    def key_prefix(block_number):
        return ("worldstate.blk-%s" % block_number).encode()

    @staticmethod
    def to_key(block_number, account_addr):
        return ("worldstate.blk-%s:account-%s" % (block_number, account_addr)).encode()

    def from_genesis_block(self, genesis_block, commit=True):
        """Creates/Initializes state from genesis block."""
        genesis_config = genesis_block.loaded_data
        for addr, data in genesis_config.get("alloc", {}).items():
            if 'balance' in data:
                self.set_balance(addr, data["balance"])
            if 'nonce' in data:
                self.set_nonce(addr, data["nonce"])
        if commit:
            self.commit()

    def new_block(self, block_height):
        """
        Creates new block head with the state of previous block head.
        :param block_height:
        :return:
        """
        prev_block_height = self.height
        self.move_cursor(block_height)
        self.copy_state(prev_block_height, block_height)
        return prev_block_height

    def new_candidate_block_state(self, temp_block):
        """
        Builds temporary state from current state and next block and returns instance to it
        :param temp_block:
        :type temp_block: ccoin.messages.Block
        :return:
        """
        state = WorldState(self.db, self.height, hash_state=self.hash_state)
        state.new_block(temp_block.number)
        return state

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

    def copy_state(self, block_height, new_block_height):
        """Copies state from `block_height` to active `block_height` in write-batch transaction mode."""
        range_key = self.key_prefix(block_height)
        new_range_key = self.key_prefix(new_block_height)
        with self.db.iterator(prefix=range_key) as it, self.db.write_batch(transaction=True) as wb:
            for k, v in it:
                new_k = k.replace(range_key, new_range_key)
                wb.put(new_k, v)

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
            account_bytes = self.db.get(key)
            if account_bytes is not None:
                self.cache[account_addr] = AccountState.deserialize(account_bytes)
            else:
                if create is False:
                    return None
                self.cache[account_addr] = AccountState(account_addr)
        return self.cache.get(account_addr, None)

    def set_state_hash(self, hash_state):
        self.hash_state = hash_state
        self.db.put(b"hash_state", self.hash_state.encode())

    def calculate_hash(self):
        concat = []
        for state_key, state_bytes in self.db:
            if state_key == b"hash_state":
                continue
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
        # TODO move to commons.py
        sender = Account(from_)
        sender_state = self.account_state(sender.address)
        if sender_state is None:
            raise SenderStateDoesNotExist(from_)
        txn = Transaction(sender_state.nonce, from_, to=to, amount=amount, data=command)
        return txn

    def set_balance(self, addr, balance):
        account_state = self.account_state(addr, create=True)
        account_state.balance = balance

    def incr_balance(self, addr, increment_value):
        account_state = self.account_state(addr, create=True)
        account_state.balance += increment_value

    def incr_nonce(self, addr, increment_value):
        account_state = self.account_state(addr, create=True)
        account_state.nonce += increment_value

    def set_nonce(self, addr, nonce):
        account_state = self.account_state(addr, create=True)
        account_state.nonce = nonce

    def commit(self):
        if self.cache:
            with self.db.write_batch(transaction=True) as wb:
                for account_addr, account_state in self.cache.items():
                    account_key = self.to_key(self.height, account_addr)
                    wb.put(account_key, account_state.serialize())
        self.set_state_hash(self.calculate_hash())
        return self.hash_state

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
        sender_state = self.account_state(transaction.sender_address)
        recipient_state = self.account_state(transaction.recipient_address, create=True)
        if not sender_state or not (sender_state.nonce == transaction.number):
            raise TransactionBadNonce(transaction)
        # Check is enough balance to spend
        if sender_state.balance - transaction.amount < 0:
           raise TransactionSenderIsOutOfCoins(transaction)
        self.incr_nonce(sender_state.address, +1)
        self.incr_balance(sender_state.address, -1 * transaction.amount)
        self.incr_balance(recipient_state.address, transaction.amount)
        # Debig/Credit
        self.commit()
