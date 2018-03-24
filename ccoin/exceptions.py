class BaseException(Exception):
    pass


class MessageDeserializationException(BaseException):

    def __init__(self, actual_msg_type, expected_msg_type):
        self.actual_msg_type = actual_msg_type
        self.expected_msg_type = expected_msg_type

    def __str__(self):
        return "DeserializationError: Expected %s message type, but received %s message type" % (
            self.expected_msg_type, self.actual_msg_type)