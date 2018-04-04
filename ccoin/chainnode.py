from twisted.internet import defer, reactor
from twisted.python import log
import ccoin.settings as ns
from ccoin import settings
from ccoin.accounts import Account
from ccoin.app_conf import AppConfig
from ccoin.blockchain import Blockchain
from ccoin.exceptions import AccountDoesNotExist, TransactionApplyException, BlockApplyException
from ccoin.messages import RequestBlockHeight, ResponseBlockHeight, RequestBlockList, ResponseBlockList
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
        self.fsm_state = fsm_state
        self.state = None  # world state
        self.chain = None
        self.drp = DeferredRequestPool()

    @property
    def genesis_block(self):
        if not self.chain:
            return
        return self.chain.genesis_block

    @property
    def allow_mine(self):
        return self.chain.genesis_block.can_mine(self.account.address)

    def load_account(self):
        self.account = Account.fromConfig()
        if not self.account:
            raise AccountDoesNotExist(self.id)

    def load_chain(self):
        self.chain = Blockchain.load(AppConfig["storage_path"], AppConfig["chain_db"], self.account.address)
        if self.chain.initialized():
            log.msg("Blockchain loaded at block=%s" % self.chain.height)

    def load_state(self):
        self.state = WorldState.load(AppConfig["storage_path"], AppConfig["state_db"], self.chain.height)
        log.msg("Worldstate loaded at block=%s with state_hash=%s" % (self.state.height, self.state.state_hash))

    def receive_block_height_request(self, request_block, sender):
        """
        :param request_block:
        :param sender:
        :type sender:
        :return:
        """

        if self.chain.height > request_block.block_number:
            rebh = ResponseBlockHeight(self.chain.height,
                                       self.id,
                                       request_id=request_block.request_id)
            sender.sendString(rebh.serialize())

    def broadcast_request_block_height(self):
        rbh = RequestBlockHeight(self.chain.height, self.id)
        return self.broadcast_request(rbh, raise_on_timeout=True)

    def request_blocks(self, addr, start_from=settings.GENESIS_BLOCK_NUMBER):
        rbl = RequestBlockList(start_from, addr)
        return self.send_request(addr, rbl, raise_on_timeout=True)

    def receive_block_height_response(self, response_block, sender):
        self.receive_response(response_block)

    def receive_request_blocks(self, request_blocks, sender):
        """
        :param request_blocks:
        :type request_blocks: RequestBlockList
        :param sender:
        :return:
        """
        if request_blocks.start_from_block > self.chain.height:
            # No blocks to provide
            msg = ResponseBlockList([], self.id, request_id=request_blocks.request_id)
            sender.sendString(msg.serialize())
        else:
            blocks = []
            for blk_number in range(request_blocks.start_from_block, self.chain.height + 1):
                blk = self.chain.get_block(blk_number)
                if blk is None:
                    break
                blocks.append(blk)
            msg = ResponseBlockList(blocks, self.id, request_id=request_blocks.request_id)
            sender.sendString(msg.serialize())

    def receive_response_blocks(self, response_blocks, sender):
        """
        :param response_blocks:
        :type response_blocks: ResponseBlockList
        :param sender:
        :return:
        """
        log.msg("Downloaded %s blocks." % len(response_blocks.blocks))
        log.msg("Applying blocks")
        for blk in response_blocks.blocks:
            try:
                self.receive_block(blk)
            except BlockApplyException as ex:
                log.msg(str(ex))
                log.err(ex)
                break
            else:
                log.msg("Applied block = %s successfully" % blk.number)
                log.msg("Changed state from boot to ready")
                if self.allow_mine:
                    log.msg("Ready mine new blocks!!!")
                self.fsm_state = settings.READY_STATE

    def receive_transaction(self, transaction):
        try:
            transaction.verify()
        except TransactionApplyException:
            log.msg("Transaction with id=%s failed to verify." % transaction.id)
        else:
            log.msg("Transaction with id=%s verified successfully." % transaction.id)
            log.err()

    @defer.inlineCallbacks
    def on_bootstrap_network_ok(self):
        log.msg("Network bootstrap successfully accomplished. Ready for the next tasks")
        if self.fsm_state != ns.BOOT_STATE:
            return
        if not self.peers_connection:
            self.fsm_state = ns.READY_STATE
            return
        # # request blocks
        block_results = yield self.broadcast_request_block_height()
        # TODO (block_result = (result, connection)
        max_height = -1
        best_result = None
        for success, value in block_results:
            if not success:
                continue
            msg = value
            if msg.block_number > max_height:
                max_height = msg.block_number
                best_result = msg
        if not best_result:
            log.msg("Nobody has block higher than mine")
            self.fsm_state = ns.READY_STATE
            if self.allow_mine:
                log.msg("Ready to mine new blocks!!!")
            return
        # request blocks
        cur_block_height = self.chain.height
        log.msg("Found max block = %s from peer = %s" % (best_result.block_number, best_result.address))
        log.msg("Start downloading from = %s" % best_result.address)
        try:
            blocks = yield self.request_blocks(best_result.address, start_from=self.chain.height + 1)
            log.msg("Downloaded %s blocks" % len(blocks))
        except defer.TimeoutError:
            log.msg("Timeout to download blocks")

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