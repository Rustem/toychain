from twisted.internet import defer
from twisted.python import log
from ccoin.accounts import AccountProvider, AccountUpdater
from ccoin.blockchain import Blockchain
from ccoin.exceptions import AccountDoesNotExist, TransactionVerificationException
from ccoin.messages import Transaction
from ccoin.p2p_network import BasePeer
import ccoin.settings as ns

# ~/.ccoin/blockchain
# ~/.ccoin/.keys/
# ~/.ccoin/config.json

# TODO 2. Node can connect to P2P Network with already loaded account (done)
# TODO 3. P2P listen Port select automatically (done)
# TODO 4. Node can send transactions signed by account's private key



class ChainNode(BasePeer):

    @defer.inlineCallbacks
    @classmethod
    def load(cls, account_id):
        new_node = yield cls.withAccount(account_id)
        new_node.load_chain()
        defer.returnValue(new_node)

    @defer.inlineCallbacks
    @classmethod
    def withAccount(cls, account_id):
        """
        Initializes and returns node with account object.
        :param account_id: account identifier
        :type account_id: str
        :return: object instance of ChainNode factory
        :rtype: BasePeer
        :raises: NodeCannotBeStartedException if account does not exists
        """
        new_node = ChainNode(account_id)
        yield new_node.load_account()
        defer.returnValue(new_node)

    def __init__(self, account_id, state=ns.BOOT_STATE):
        super(ChainNode, self).__init__(account_id)
        self.account = None
        self.chain = None
        self.allow_mine = False
        self.state = state

    @defer.inlineCallbacks
    def load_account(self):
        account_provider = AccountProvider()
        yield account_provider.initialize()
        self.account = yield account_provider.get_by_id(self.id, with_private_key=True)
        self.account_updater = AccountUpdater(self.account)
        if not self.account:
            raise AccountDoesNotExist(self.id)

    def load_chain(self):
        self.chain = Blockchain.load(self.account.id)
        self.allow_mine = self.chain.genesis_block.can_mine(self.account.public_key)

    def receive_transaction(self, transaction):
        try:
            # TODO make a function verify_transaction that checks full process
            transaction.verify()
        except TransactionVerificationException:
            log.msg("Incoming Transaction with id=%s failed to verify." % transaction.id)
        else:
            log.msg("Incoming Transaction with id=%s verified successfully." % transaction.id)

    def receive_block(self, block):
        pass

    def make_transfer_txn(self, sendto_address, amount):
        """
        Creates spendable transaction.
        :param sendto_address: public key of recepient
        :param amount: amount of money sender is wishing to spend
        :return:
        :rtype:
        """
        return self.make_txn(to=sendto_address, amount=amount)

    def make_txn(self, command=None, to=None, amount=None):
        """
        :param command: command details
        :type command: str
        :param to: recipient address
        :param amount: amount of money to send to
        :return: transaction id
        :rtype: str
        """
        self.account_updater.increment_nonce()
        txn = Transaction(self.account.nonce, self.account.public_key, to=to, amount=amount, data=command)
        return txn

    def relay_txn(self, transaction):
        """
        Sends transaction to the network and returns it's id.
        :param transaction: object instance of Transaction
        :type transaction: Transaction
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