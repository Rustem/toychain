import logging
import struct

import msgpack
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ClientEndpoint, TCP4ServerEndpoint, connectProtocol
from twisted.internet.protocol import connectionDone, Factory
from twisted.protocols.basic import IntNStringReceiver

from ccoin.discovery import PeerDiscoveryService
from ccoin.peer_info import PeerInfo
from twisted.python import log

from ccoin.rest_api import run_http_site

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


class SimpleHandshakeProtocol(IntNStringReceiver):
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
        if msg_type == "HEY":
            msg = msgpack.unpackb(string[3:], raw=False)
            # handle handshake
            self.handle_hi(msg)
        elif msg_type == "ACK":
            msg = msgpack.unpackb(string[3:], raw=False)
            # handle handshake acknowledgement
            self.handle_hi_ack(msg)
        else:
            self.factory.message_callback(msg_type, string, self)

    def handle_hi(self, msg):
        """Handles incoming handshake message by persisting the details of connected peer and
        sending him acknowledgement."""
        print(msg)
        peer_node_id = msg["node_id"]
        logger.debug('Handshake from %s with peer_node_id = %s ', str(self.transport.getPeer()), peer_node_id)
        if peer_node_id not in self.factory.peers_connection:
            self.factory.add_peer(peer_node_id, self)
            self.peer_node_id = peer_node_id
        self.send_hi_ack()

    def handle_hi_ack(self, msg):
        """Handles incoming handshake acknowledgement message by persisting the details of acknowledging peer."""
        peer_node_id = msg["node_id"]
        logger.debug('Handshake ACK from %s with peer_node_id = %s ', str(self.transport.getPeer()), peer_node_id)
        if peer_node_id not in self.factory.peers_connection:
            self.factory.add_peer(peer_node_id, self)
            self.peer_node_id = peer_node_id
        # TODO define ping reconnecting loop

    def send_hi(self):
        """Send handshake message so that other node gets to ack this node."""
        s = msgpack.packb({"node_id": self.node_id})
        # send utf-8 encoded string to the wire
        self.sendString(b'HEY' + s)

    def send_hi_ack(self):
        """Send handshake acknowledgement so that other node can ack this node"""
        s = msgpack.packb({"node_id": self.node_id})
        # send utf-8 encoded string to the wire
        self.sendString(b'ACK' + s)


class BasePeer(Factory):
    """This class defines the logic of representing the peer and its connected peers consistently.

    Attributes:
        peers_connection (dict): Maps from str to Connection. The key represents the node_id and the value the
            Connection to the node with this node_id.
        id (int): unique identifier of this factory which represents a node.
        peers (dict): stores for each node id a peer instance with ip and port information.
        reconnect_loop (LoopingCall): keeps trying to connect to peers if connection to at least one is lost.

    """

    def __init__(self, uuid):
        self.id = uuid
        self.peers_connection = {}
        self.peers = {}
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

    def buildProtocol(self, addr):
        return SimpleHandshakeProtocol(self)

    @staticmethod
    def got_protocol(p):
        """The callback to start the protocol handshake. Let connecting nodes start the hello handshake."""
        p.send_hi()

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
            self.connect_to_peer(peer)

    def connect_to_peer(self, peer):
        """
        :param peer:
        :type peer: PeerInfo
        :return:
        """
        if peer.id not in self.peers_connection:
            point = TCP4ClientEndpoint(reactor, peer.ip, peer.port)
            d = connectProtocol(point, SimpleHandshakeProtocol(self))
            d.addCallback(self.got_protocol)
            d.addErrback(self.fail_got_protocol, peer.id)

    def run_p2p(self, port):
        """Starts a server listening on a port given in peers dict and then connect to other peers."""
        endpoint = TCP4ServerEndpoint(reactor, port)
        d = endpoint.listen(self)
        d.addCallback(self.p2p_listen_ok)
        d.addErrback(log.err)
        reactor.run()

    @defer.inlineCallbacks
    def p2p_listen_ok(self, host_info):
        host = host_info.getHost()
        # Start HTTP RPC server
        yield run_http_site(self, host.port + 1, callback=self.http_listen_ok, errback=log.err)
        # P2P Network bootstrap
        yield self.discovery_service.initialize()
        yield self.discovery_service.add_member(PeerInfo(host.host, host.port, self.id))
        yield self.bootstrap_network()

    def http_listen_ok(self, *args, **kwargs):
        print("hi", args)

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

    def parse_msg(self, msg_type, msg, sender):
        raise NotImplementedError("Can\'t parse %s: %s" % (msg_type, msg))





