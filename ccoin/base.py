import os
from abc import ABC, abstractmethod, abstractclassmethod
from twisted.enterprise import adbapi
from twisted.internet import defer, reactor
from twisted.python import log

from ccoin import settings


class Serializable(ABC):

    @abstractmethod
    def to_dict(self):
        pass

    @classmethod
    @abstractclassmethod
    def from_dict(cls, data):
        pass


class SharedDatabaseServiceMixin(object):

    base_path = None

    db = None

    def __init__(self):
        self.base_path = base_path = os.path.expanduser('~/.ccoin')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, "accounts.db")
        self.db = adbapi.ConnectionPool("sqlite3", path, check_same_thread=False)

    @defer.inlineCallbacks
    def initialize(self):
        yield self.ensure_table()

    @defer.inlineCallbacks
    @abstractmethod
    def ensure_table(self):
        raise NotImplementedError("")


class DeferredRequestMixin(object):

    def __init__(self, cnt=0):
        """
        :param cnt: request number
        :type cnt: int
        """
        self.cnt = cnt
        self.request_registry = {}

    def broadcast_request(self, msg_object, msg_type):
        conn_map = self.get_connections()
        if not conn_map:
            return
        defer_reqs = [self.send_request(addr, msg_object) for addr in conn_map.keys()]
        return defer.DeferredList(defer_reqs)

    def send_request(self, addr, msg, timeout=settings.DEFAULT_REQUEST_TIMEOUT,
                     response_callback=None, response_errback=None):
        """
        :param addr:
        :param msg:
        :type msg: ccoin.messages.BaseMessage
        :return: deferred request
        :rtype: defer.Deferred
        """
        # Build request
        req_id = self.cnt
        msg.request_id = req_id
        d = defer.Deferred()
        d.addTimeout(timeout, reactor)
        if response_callback is None:
            response_callback = self.on_request_success
        d.addCallback(response_callback)

        if response_errback is None:
            response_errback = self.on_request_failure
        d.addErrback(response_errback, request_id=req_id)

        self.request_registry[req_id] = d
        # Send request over the wire
        connection = self.get_connection(addr)
        connection.sendString(msg.serialize())
        # Increment counter
        self.cnt += 1
        return d

    def receive_response(self, msg):
        """
        :param msg: ccoin.messages.BaseMessage
        :return:
        """
        assert isinstance(msg.request_id, int), "Request id Must be int. verify you code."
        d = self.request_registry.pop(msg.request_id, None)
        if d is None:
            log.msg("WARNING: request with request_id=%s and msg=%s has been timedout" % (msg.request_id, msg.identifier))
        d.callback(msg)

    def get_connection(self, addr):
        conn_map = self.get_connections()
        return conn_map.get(addr)

    def get_connections(self):
        """
        :return: connection map
        :rtype: dict(str, BasePeer)
        """

        raise NotImplementedError("Implement me")

    def on_request_success(self, msg):
        log.msg("INFO: request with request_id=%s received response successfully" % msg.request_id)
        return msg

    def on_request_failure(self, failure, request_id):
        """Defauler deferred request error handler"""
        failure.trap(defer.TimeoutError)
        log.msg("ERROR: request with request_id=%s failed for the reason=%s" % (request_id, str(failure)))
        # return failure