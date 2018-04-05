import logging

import struct
from abc import abstractmethod
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import connectionDone, Factory
from twisted.protocols.basic import IntNStringReceiver
from twisted.python import log

from ccoin.base import DeferredRequestMixin
from ccoin.discovery import PeerDiscoveryService
from ccoin.exceptions import NotSupportedMessage
from ccoin.messages import Transaction, HelloMessage, HelloAckMessage, RequestBlockHeight, ResponseBlockHeight, \
    RequestBlockList, ResponseBlockList
from ccoin.peer_info import PeerInfo
from ccoin.rest_api import run_http_api

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SimpleHandshakeProtocol(IntNStringReceiver, DeferredRequestMixin):
    """This class encapsulates behaviour of establishing and keeping connection with remote peers.
    Args:
        factory (BasePeer): Twisted Factory used to keep a shared state among multiple connections.

    Attributes:
        factory (Factory): The factory that created the connection. It keeps a consistent state
            among connections.
        node_id (str): Unique id of the node on this side of the connection.
        peer_node_id (str): Unique id of the node on the other side of the connection.
    """


    # little endian, unsigned int
    structFormat = '<I'
    prefixLength = struct.calcsize(structFormat)
    MAX_LENGTH = 3000000  # max message size to 3MB

    def __init__(self, factory):
        """
        :param factory:
        :type factory: BasePeer
        """
        super().__init__(cnt=0)
        self.factory = factory
        self.node_id = str(self.factory.id)
        self.peer_node_id = None

    def connectionMade(self):
        """Callback called once a connection with another node got established."""
        logger.debug('Connected to %s.', str(self.transport.getPeer()))

    def connectionLost(self, reason=connectionDone):
        """Callback called once a connection with another node got lost."""
        logger.debug('Lost connection to %s with id %s: %s',
                     str(self.transport.getPeer()), self.peer_node_id, reason.getErrorMessage())

        # remove peer_node_id from peers
        if self.peer_node_id is not None and self.peer_node_id in self.factory.peers_connection:
            self.factory.remove_peer(self.peer_node_id)

    def stringReceived(self, string):
        """Callback called once a complete message is received"""
        msg_type = string[:3].decode()
        log.msg("RECEIVED MSG: %s" % string)
        if msg_type == "HEY":
            msg = HelloMessage.deserialize(string)
            # handle handshake
            self.handle_hi(msg)
        elif msg_type == "ACK":
            msg = HelloAckMessage.deserialize(string)
            # handle handshake acknowledgement
            self.handle_hi_ack(msg)
        else:
            raise NotSupportedMessage(msg_type)

    def handle_hi(self, msg):
        """Handles incoming handshake message by persisting the details of connected peer and
        sending him acknowledgement."""
        peer_node_id = msg.address
        logger.debug('Handshake from %s with peer_node_id = %s ', str(self.transport.getPeer()), peer_node_id)
        if peer_node_id not in self.factory.peers_connection:
            self.factory.add_peer(peer_node_id, self)
            self.peer_node_id = peer_node_id
        self.send_hi_ack(msg.request_id)

    def handle_hi_ack(self, msg):
        """Handles incoming handshake acknowledgement message by persisting the details of acknowledging peer."""
        peer_node_id = msg.address
        logger.debug('Handshake ACK from %s with peer_node_id = %s ', str(self.transport.getPeer()), peer_node_id)
        if peer_node_id not in self.factory.peers_connection:
            self.factory.add_peer(peer_node_id, self)
            self.peer_node_id = peer_node_id
        # Trigger deferred callbacks
        self.receive_response(msg)

        # TODO define ping reconnecting loop

    def send_hi(self):
        hi_msg = HelloMessage(self.node_id)
        d = self.send_request(self.peer_node_id, hi_msg, raise_on_timeout=True)
        return d

    def send_hi_ack(self, request_id):
        """
        Send handshake acknowledgement so that other node can ack this node
        :return: deferred object
        :rtype: defer.Deferred
        """
        ack_msg = HelloAckMessage(self.node_id, request_id=request_id)
        self.sendString(ack_msg.serialize())

    def get_connections(self):
        return {self.peer_node_id: self}


class BasePeerConnection(SimpleHandshakeProtocol):

    def stringReceived(self, string):
        try:
            super(BasePeerConnection, self).stringReceived(string)
        except NotSupportedMessage as exc:
            self.factory.message_callback(exc.msg_type, string, self)


class BasePeer(Factory, DeferredRequestMixin):
    """This class defines the logic of representing the peer and its connected peers consistently.

    Attributes:
        peers_connection (dict): Maps from str to Connection. The key represents the node_id and the value the
            Connection to the node with this node_id.
        id (int): unique identifier of this factory which represents a node.
        peers (dict): stores for each node id a peer instance with ip and port information.
        reconnect_loop (LoopingCall): keeps trying to connect to peers if connection to at least one is lost.

    """

    def __init__(self, uuid):
        super().__init__(cnt=0)
        self.id = uuid
        self.peers_connection = {}
        self.peers = {}
        # TODO make it as http client
        self.discovery_service = PeerDiscoveryService()
        self.message_callback = self.parse_msg
        self.reconnect_loop = None

    @property
    def peer(self):
        """
        :return:
        :rtype: PeerInfo
        """
        return self.peers[self.id]

    def get_connections(self):
        return self.peers_connection

    def buildProtocol(self, addr):
        return BasePeerConnection(self)

    @staticmethod
    def got_protocol(p):
        """The callback to start the protocol handshake. Let connecting nodes start the hello handshake."""
        d = p.send_hi()
        return d

    @staticmethod
    def fail_got_protocol(failure, node_id):
        logger.debug('Peer not online (%s): peer node id = %s ', str(failure.type), node_id)

    @defer.inlineCallbacks
    def stopFactory(self):
        yield self.discovery_service.remove_member(self.id)

    @defer.inlineCallbacks
    def bootstrap_network(self):
        """Connect to each online peer if not yet connected."""
        if not self.peers:
            for peer in (yield self.discovery_service.get_members()):
                self.peers[peer.id] = peer
        for peer in self.peers.values():
            if peer.id == self.id:
                continue # skip
            yield self.connect_to_peer(peer)
        self.on_bootstrap_network_ok()

    @abstractmethod
    def on_bootstrap_network_ok(self):
        """Callback called once network bootstrap is ended."""
        pass

    def connect_to_peer(self, peer):
        """
        :param peer:
        :type peer: PeerInfo
        :return:
        """
        if peer.id not in self.peers_connection:
            point = TCP4ClientEndpoint(reactor, peer.ip, peer.port)
            d = connectProtocol(point, BasePeerConnection(self))
            d.addCallback(self.got_protocol)
            d.addErrback(self.fail_got_protocol, peer.id)
            return d
        else:
            d = defer.Deferred()
            d.callback(self.peers_connection.get(peer.id))
            return d

    @defer.inlineCallbacks
    def p2p_listen_ok(self, portObject):
        """Callback called once node started to listen"""
        host = portObject.getHost()
        # Start HTTP RPC server
        yield run_http_api(self, host.port + 1, callback=self.http_listen_ok, errback=log.err)
        # P2P Network bootstrap
        # TODO replace it with http discover client
        yield self.discovery_service.initialize()
        yield self.discovery_service.add_member(PeerInfo(host.host, host.port, self.id))
        yield self.bootstrap_network()

    def http_listen_ok(self, portObject):
        host = portObject.getHost()
        log.msg("HTTP API ENDPOINT Started got up and listening on port: %s" % host.port)

    def add_peer(self, peer_node_id, peer_connection):
        """
        :param peer_node_id:
        :param peer_connection:
        :return:
        """
        self.peers_connection[peer_node_id] = peer_connection
        peer_ip_port = peer_connection.transport.getPeer()
        self.peers[peer_node_id] = PeerInfo(peer_ip_port.host, peer_ip_port.port, peer_node_id)

    def remove_peer(self, peer_node_id):
        self.peers_connection.pop(peer_node_id, None)
        self.peers.pop(peer_node_id, None)

    def broadcast(self, msg_object):
        """
        Broadcast message object to each known peer.
        :param msg_object: Message instance (Transaction, Block, etc.)
        :type msg_object: Message
        """
        msg_bytes = msg_object.serialize()
        for peer_id, peer_conn in self.peers_connection.items():
            peer_conn.sendString(msg_bytes)

    def send(self, peer_address, msg_object, msg_type):
        if peer_address in self.peers_connection:
            self.peers_connection[peer_address].sendString(msg_object.serialize())

    def parse_msg(self, msg_type, msg, sender):
        if msg_type == "RBH":
            obj = RequestBlockHeight.deserialize(msg)
            self.receive_block_height_request(obj, sender)
            return
        if msg_type == "BLH":
            obj = ResponseBlockHeight.deserialize(msg)
            self.receive_block_height_response(obj, sender)
            return
        elif msg_type == "TXN":
            obj = Transaction.deserialize(msg)
            self.receive_transaction(obj)
            return
        elif msg_type == "RBL":
            obj = RequestBlockList.deserialize(msg)
            self.receive_request_blocks(obj, sender)
            return
        elif msg_type == "ABL":
            obj = ResponseBlockList.deserialize(msg)
            self.receive_response_blocks(obj, sender)
            return
        elif msg_type == "BLK":
            obj = None #Block.deserialize(msg)
            self.receive_block(obj)
            return
        else:
            raise NotImplementedError("Can\'t parse %s: %s" % (msg_type, msg))

    @abstractmethod
    def receive_block_height_request(self, request_block_height, sender):
        """
        Handles block request with block response
        :param request_block_height:
        :type request_block_height: RequestBlockHeight
        :param sender
        :type sender: BasePeerConnection
        :return:
        """
        pass

    @abstractmethod
    def receive_block_height_response(self, response_block_height, sender):
        """
        :param response_block_height:
        :param sender:
        :return:
        """
        pass

    @abstractmethod
    def receive_request_blocks(self, request_blocks, sender):
        """
        Handles download blocks request
        :param request_blocks:
        :param sender:
        :return:
        """
        pass

    @abstractmethod
    def receive_response_blocks(self, response_blocks, sender):
        """
        Handles download blocks response.
        :param response_blocks:
        :param sender:
        :return:
        """
        pass

    @abstractmethod
    def receive_transaction(self, transaction):
        """Handles new transaction."""
        pass

    @abstractmethod
    def receive_block(self, block):
        """Handles new block."""
        pass


