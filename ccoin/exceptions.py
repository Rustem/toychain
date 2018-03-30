class BaseException(Exception):
    pass


class NodeCannotBeStartedException(Exception):

    def __init__(self, nodeid):
        self.node_id = nodeid


class AccountDoesNotExist(NodeCannotBeStartedException):

    def __str__(self):
        return "Node cannot be started: Account does not exists for the user with id=%s." % self.node_id


class GenesisBlockIsRequired(NodeCannotBeStartedException):

    def __str__(self):
        return "Genesis block should be generated or downloaded from other peers"

class MessageDeserializationException(BaseException):

    def __init__(self, actual_msg_type, expected_msg_type):
        self.actual_msg_type = actual_msg_type
        self.expected_msg_type = expected_msg_type

    def __str__(self):
        return "DeserializationError: Expected %s message type, but received %s message type" % (
            self.expected_msg_type, self.actual_msg_type)


class NotSupportedMessage(BaseException):

    def __init__(self, msg_type):
        self.msg_type = msg_type


class BlockApplyException(BaseException):

    def __init__(self, block):
        """

        :param block:
        :type txn: ccoin.messages.Block
       """
        self.block = block

    def __str__(self):
        return "Block is invalid, Failed to apply block"


class BlockChainViolated(BlockApplyException):

    def __str__(self):
        return "New block should reference previous block that exists and valid"


class BlockTimeError(BlockApplyException):

    def __str__(self):
        return "New block should be created later than latest block in the chain"


class BlockWrongDifficulty(BlockApplyException):

    def __str__(self):
        return "New block does not match difficulty in genesis block"


class BlockWrongNumber(BlockApplyException):
    def __str__(self):
        return "New block should have next to head's block number"


class BlockWrongTransactionHash(BlockApplyException):

    def __str__(self):
        return "New block has wrong transaction hash"


class BlockPoWFailed(BlockApplyException):
    def __str__(self):
        return "Miner computed block's proof-of-work incorrectly"


class TransactionApplyException(BaseException):

    def __init__(self, txn):
        """

        :param txn:
        :type txn: ccoin.messages.Transaction
        """
        self.txn = txn


class TransactionBadSignature(BaseException):

    def __str__(self):
        return "Transaction signature cannot be verified."

class TransactionNotVerifiable(TransactionApplyException):

    def __str__(self):
        return "Transaction with id=%s is not verifiable. Please sign it first." % self.txn.id


class TransactionBadNonce(TransactionApplyException):

    def __str__(self):
        return "Transaction has nonce=%s that does not match sender nonce's." % self.txn.number


class TransactionSenderIsOutOfCoins(TransactionApplyException):

    def __str__(self):
        return "Transaction error: sender has less than %s coins on his balance" % self.txn.number


class SenderStateDoesNotExist(BaseException):

    def __init__(self, sender_address):
        self.sender_address = sender_address

    def __str__(self):
        return "Sender=%s state is not committed in database." % self.sender_address