from zope.interface import implementer
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ServerEndpoint

from twisted.application import internet, service

from ccoin.chainnode import ChainNode
from ccoin.exceptions import NodeCannotBeStartedException

class Options(usage.Options):

    optParameters = [
        ['nodeid', 'n', "1", 'Node identifier'],
    ]


class StreamServerEndpointService(internet.StreamServerEndpointService):
    """Runs a server on a listening port described by an L{IStreamServerEndpoint}.

        Attributes:
            got_listen (callable): Callback that is called , once a server has run successfully.
    """

    def __init__(self, endpoint, factory, listen_precondition_checks=None, got_listen=None):
        super(StreamServerEndpointService, self).__init__(endpoint, factory)
        self.listen_precondition_checks = listen_precondition_checks
        self.got_listen = got_listen

    @defer.inlineCallbacks
    def privilegedStartService(self):
        """
        Start listening on the endpoint.
        """
        try:
            for precond_chk, is_async in self.listen_precondition_checks:
                if is_async:
                    yield precond_chk()
                else:
                    precond_chk()
        except NodeCannotBeStartedException:
            log.err()
            reactor.stop()
            return
        super(StreamServerEndpointService, self).privilegedStartService()
        if self.got_listen:
            for cb in self.got_listen:
                self._waitingForPort.addCallback(cb)

    def stopService(self):
        if not self._waitingForPort:
            return


@implementer(service.IServiceMaker, IPlugin)
class BlockchainNodeServiceMaker(object):
    tapname = "cnode"
    description = "A simple blockchain node."
    options = Options

    def makeService(self, options):
        """
        :param options: configuration parameters
        :type options: dict
        :return: endpoint service that runs a p2p server node
        :rtype: service.Service
        """
        top_service = service.MultiService()
        chain_node_factory = ChainNode(options["nodeid"])
        # p2p server
        p2p_service = StreamServerEndpointService(
            TCP4ServerEndpoint(reactor, 0),
            chain_node_factory,
            listen_precondition_checks=[(chain_node_factory.load_account, True)],
            got_listen=[chain_node_factory.p2p_listen_ok]
        )
        top_service.addService(p2p_service)
        return top_service

service_maker = BlockchainNodeServiceMaker()
