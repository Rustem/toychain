class BaseException(Exception):
    pass


class NodeCannotBeStartedException(Exception):

    def __init__(self, nodeid):
        self.node_id = nodeid


class AccountDoesNotExist(NodeCannotBeStartedException):

    def __str__(self):
        return "Node cannot be started: Account does not exists for the user with id=%s." % self.node_id


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

class TransactionVerificationException(BaseException):

    def __init__(self, txn):
        self.txn = txn


class TransactionNotVerifiable(TransactionVerificationException):

    def __str__(self):
        return "Transaction with id=%s is not verifiable. Please sign it first." % self.txn.id