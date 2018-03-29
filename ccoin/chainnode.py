from twisted.internet import defer
from twisted.python import log
from ccoin.accounts import Account
from ccoin.app_conf import AppConfig
from ccoin.blockchain import Blockchain
from ccoin.exceptions import AccountDoesNotExist, TransactionApplyException
from ccoin.p2p_network import BasePeer
import ccoin.settings as ns

# ~/.ccoin/blockchain
# ~/.ccoin/.keys/
# ~/.ccoin/config.json

# TODO 2. Node can connect to P2P Network with already loaded account (done)
# TODO 3. P2P listen Port select automatically (done)
# TODO 4. Node can send transactions signed by account's private key
from ccoin.worldstate import WorldState


class ChainNode(BasePeer):

    @defer.inlineCallbacks
    @classmethod
    def load(cls):
        new_node = cls.withAccount()
        new_node.load_chain()
        new_node.load_state()
        defer.returnValue(new_node)

    @classmethod
    def withAccount(cls):
        """
        Initializes and returns node with account object.
        :return: object instance of ChainNode factory
        :rtype: BasePeer
        :raises: NodeCannotBeStartedException if account does not exists
        """
        address = AppConfig["account_address"]
        new_node = ChainNode(address)
        new_node.load_account()
        return new_node

    def __init__(self, address, fsm_state=ns.BOOT_STATE):
        """
        :ivar state: WorldState
        :type state: WorldState
        :ivar chain: Blockchain reference
        :type chain: Blockchain
        """
        super(ChainNode, self).__init__(address)
        self.account = None
        self.allow_mine = False
        self.fsm_state = fsm_state
        self.state = None  # world state
        self.chain = None

    def load_account(self):
        self.account = Account.fromConfig()
        if not self.account:
            raise AccountDoesNotExist(self.id)

    def load_chain(self):
        self.chain = Blockchain.load(AppConfig["chain_path"], self.account.address)
        self.allow_mine = self.chain.genesis_block.can_mine(self.account.public_key)

    def load_state(self):
        self.state = WorldState.load(AppConfig["state_path"], self.account.address)

    def receive_transaction(self, transaction):
        # TODO catch exception and log it
        try:
            transaction.verify()
        except TransactionApplyException:
            log.msg("Incoming Transaction with id=%s failed to verify." % transaction.id)
        else:
            # TODO Add transaction to the pool
            log.msg("Incoming Transaction with id=%s verified successfully." % transaction.id)

    def receive_block(self, block):
        # TODO catch exception and log it
        self.chain.apply_block(block, worldstate=self.state)

    def make_transfer_txn(self, sendto_address, amount):
        """
        Creates spendable transaction.
        :param sendto_address: public key of recepient
        :param amount: amount of money sender is wishing to spend
        :return:
        :rtype: ccoin.messages.Transaction
        """
        return self.make_txn(to=sendto_address, amount=amount)

    def make_txn(self, command=None, to=None, amount=None):
        """
        :param command: command details
        :type command: str
        :param to: recipient address
        :param amount: amount of money to send to
        :return: Transaction reference
        :rtype: ccoin.messages.Transaction
        """
        txn = self.state.make_txn(command=command, to=to, amount=amount)
        return txn

    def relay_txn(self, transaction):
        """
        Sends transaction to the network and returns it's id.
        :param transaction: object instance of Transaction
        :type transaction: ccoin.messages.Transaction
        :return: transaction id
        :rtype: str
        """
        # 1. generate transaction id
        txn_id = transaction.generate_id()
        # 2. sign transaction by sender's private key (ready to be sent)
        transaction.sign(self.account.private_key)
        # 3. relay it to the network
        self.broadcast(transaction, transaction.identifier)
        return txn_id