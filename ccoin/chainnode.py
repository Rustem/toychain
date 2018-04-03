from twisted.internet import defer, reactor
from twisted.python import log
import ccoin.settings as ns
from ccoin import settings
from ccoin.accounts import Account
from ccoin.app_conf import AppConfig
from ccoin.blockchain import Blockchain
from ccoin.exceptions import AccountDoesNotExist, TransactionApplyException, BlockApplyException
from ccoin.messages import RequestBlock
from ccoin.p2p_network import BasePeer
from ccoin.worldstate import WorldState


class DeferredRequestPool(object):

    def __init__(self):
        self.dl = {}

    def add(self, request, timeout=settings.DEFAULT_REQUEST_TIMEOUT):
        d = defer.Deferred()
        d.addTimeout(timeout, reactor, onTimeoutCancel=self.timedout)
        self.dl[request.request_id] = (request, d)
        return request, d

    def get(self, request_id):
        request, d = self.dl.get(request_id, (None, None))
        return request, d

    def remove(self, request_id, result=None, failure=None):
        request, d = self.dl.pop(request_id)
        if result:
            d.callback(result)
        else:
            d.errback(failure)
        return request, d

    def timedout(self, request_id, result, timeout):
        self.remove(request_id=request_id)
        raise NotImplementedError("")


class ChainNode(BasePeer):

    @classmethod
    def full(cls):
        new_node = cls.withAccount()
        new_node.load_chain()
        new_node.load_state()
        return new_node

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
        self.drp = DeferredRequestPool()

    @property
    def genesis_block(self):
        if not self.chain:
            return
        return self.chain.genesis_block

    def load_account(self):
        self.account = Account.fromConfig()
        if not self.account:
            raise AccountDoesNotExist(self.id)

    def load_chain(self):
        self.chain = Blockchain.load(AppConfig["storage_path"], AppConfig["chain_db"], self.account.address)
        if self.chain.initialized():
            self.allow_mine = self.chain.genesis_block.can_mine(self.account.public_key)
            log.msg("Blockchain loaded at block=%s" % self.chain.height)

    def load_state(self):
        self.state = WorldState.load(AppConfig["storage_path"], AppConfig["state_db"], self.chain.height)
        log.msg("Worldstate loaded at block=%s with state_hash=%s" % (self.state.height, self.state.state_hash))

    def receive_transaction(self, transaction):
        try:
            transaction.verify()
        except TransactionApplyException:
            log.msg("Transaction with id=%s failed to verify." % transaction.id)
        else:
            log.msg("Transaction with id=%s verified successfully." % transaction.id)
            log.err()

    def request_block(self, address, block_number):
        rbl = RequestBlock(block_number)
        request_id, d = self.make_request(address, rbl)

    def make_request(self, address, msg, timeout=settings.DEFAULT_REQUEST_TIMEOUT):
        conn = self.peers_connection.get(address)
        if not conn:
            # TODO log
            return
        try:
            conn.sendString(msg.serialize())
        finally:
            return self.drp.add(msg, timeout=timeout)

    def receive_block(self, block):
        try:
            self.chain.apply_block(block, worldstate=self.state)
        except BlockApplyException as ex:
            log.msg(str(ex))
            # TODO move errors to err.log
            log.err(ex)

    def make_transfer_txn(self, sendto_address, amount):
        """
        Creates spendable transaction.
        :param sendto_address: public key of recipient
        :param amount: amount of money sender is wishing to spend
        :return:
        :rtype: ccoin.messages.Transaction
        """
        return self.make_txn(self.account.public_key, sendto_address, amount=amount)

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