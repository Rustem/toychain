from zope.interface import implementer
from twisted.python import usage
from twisted.plugin import IPlugin
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint

from twisted.application import internet, service

from ccoin.p2p_network import BasePeer


class Options(usage.Options):

    optParameters = [
        ['nodeid', 'n', "1", 'Node identifier'],
    ]


class StreamServerEndpointService(internet.StreamServerEndpointService):

    def __init__(self, endpoint, factory, got_listen=None):
        super(StreamServerEndpointService, self).__init__(endpoint, factory)
        self.got_listen = got_listen

    def privilegedStartService(self):
        """
        Start listening on the endpoint.
        """
        super(StreamServerEndpointService, self).privilegedStartService()
        if self.got_listen:
            for cb in self.got_listen:
                self._waitingForPort.addCallback(cb)


@implementer(service.IServiceMaker, IPlugin)
class BlockchainNodeServiceMaker(object):
    tapname = "cnode"
    description = "A simple blockchain node."
    options = Options

    def makeService(self, options):
        top_service = service.MultiService()
        factory = BasePeer(options["nodeid"])
        # p2p server
        p2p_service = StreamServerEndpointService(
            TCP4ServerEndpoint(reactor, 0),
            factory,
            got_listen=[factory.p2p_listen_ok]
        )
        top_service.addService(p2p_service)
        return top_service

service_maker = BlockchainNodeServiceMaker()
