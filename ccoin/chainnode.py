from copy import deepcopy
from twisted.internet import defer, reactor
from twisted.python import log
import ccoin.settings as ns
from ccoin import settings
from ccoin.accounts import Account
from ccoin.app_conf import AppConfig
from ccoin.blockchain import Blockchain
from ccoin.common import make_head_candidate
from ccoin.exceptions import AccountDoesNotExist, TransactionApplyException, BlockApplyException
from ccoin.messages import RequestBlockHeight, ResponseBlockHeight, RequestBlockList, ResponseBlockList, GenesisBlock
from ccoin.p2p_network import BasePeer
from ccoin.pow import Miner
from ccoin.transaction_queue import TransactionQueue
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

    def load_account(self):
        self.account = Account.fromConfig()
        if not self.account:
            raise AccountDoesNotExist(self.id)

    def load_chain(self, **kwargs):
        self.chain = Blockchain.load(AppConfig["storage_path"], AppConfig["chain_db"], self.account.address, **kwargs)
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
                self.change_fsm_state(settings.READY_STATE)

    def change_fsm_state(self, new_fsm_state):
        assert new_fsm_state in settings.NODE_STATES
        old_fsm_state = self.fsm_state
        self.fsm_state = new_fsm_state
        self.on_change_fsm_state(old_fsm_state, new_fsm_state)
        log.msg("Node state changed from=%s to=%s" % (old_fsm_state, new_fsm_state))

    def on_change_fsm_state(self, old_fsm_state, new_fsm_state):
        pass

    def receive_transaction(self, transaction):
        try:
            transaction.verify()
        except TransactionApplyException:
            log.msg("Transaction with id=%s failed to verify." % transaction.id)
            log.err()
            return False
        else:
            log.msg("Transaction with id=%s verified successfully." % transaction.id)
            return True

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


class MinerNode(ChainNode):

    # TODO can mine should come during loading chain
    # TODO async loop that periodically checks and generates new block

    def __init__(self, address, **kwargs):
        super().__init__(address, **kwargs)
        self.txqueue = TransactionQueue()
        self.can_mine = kwargs.get("can_mine", False)
        self.ready_mine_new_block = kwargs.get("ready_mine_new_block", False)
        self.candidate_block = None
        self.candidate_block_state = None

    def on_change_fsm_state(self, old_fsm_state, new_fsm_state):
        if new_fsm_state == settings.READY_STATE and self.can_mine:
            log.msg("Ready mine new blocks!!!")

    def load_chain(self):
        super().load_chain(new_head_cb=self.on_new_head)

    def on_new_head(self, block):
        self.txqueue = self.txqueue.diff(block.body)
        self.ready_mine_new_block = True
        # In case mining node started without any data
        if isinstance(block, GenesisBlock):
            self.can_mine = block.can_mine(self.id)

    def generate_candidate_block(self):
        """Generates new block from the transaction queue.
        Called for one of the reasons below:
            #. at least 10 transactions under the queue
            #. 10 minutes has left from the last time
        """
        if self.ready_mine_new_block:
            self.ready_mine_new_block = False
            txqueue = deepcopy(self.txqueue)
            self.candidate_block, self.candidate_block_state = make_head_candidate(
                self.chain, txqueue=txqueue)
        return self.candidate_block

    def broadcast_new_block(self, block):
        raise NotImplementedError("")

    def mine_and_broadcast_block(self):
        if not self.candidate_block:
            return
        block = Miner(self.candidate_block).mine(start_nonce=0)
        self.transaction_queue = self.transaction_queue.diff(block.body)
        self.broadcast_new_block(block)

    def receive_transaction(self, transaction):
        verify_status = super().receive_transaction(transaction)
        if verify_status:
            self.txqueue.add_transaction(transaction)
            if self.can_mine:
                self.mine_and_broadcast_block()

    def receive_block(self, block):
        raise NotImplementedError("Require to extend from chain node")
