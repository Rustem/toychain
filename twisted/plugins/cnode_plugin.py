from zope.interface import implementer
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.internet import reactor, defer
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.application import internet, service
from ccoin.chainnode import node_registry
from ccoin.exceptions import NodeCannotBeStartedException
from twisted.plugins.base import Configurable


class Options(usage.Options):

    optParameters = [
        ['port', 'p', 0, 'Port number'],
        ['node_type', 't', 'basic', 'Node type'],
        ['config', 'c', 'ccoin.json', 'Application config file']
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
        self.i = 0

    @defer.inlineCallbacks
    def privilegedStartService(self):
        """
        Start listening on the endpoint.
        """
        # NOTE: somehow yielding here executes service twice, so 'i' counter prevents it
        if self.i > 0:
            return
        self.i += 1
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
class BlockchainNodeServiceMaker(Configurable):
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
        self.configure(options)
        top_service = service.MultiService()
        Node = self.get_node(options)
        node_factory = Node.full()
        # p2p server listens by default on automatically selected port
        # use --port={port_number} to set certain port
        p2p_service = StreamServerEndpointService(
            TCP4ServerEndpoint(reactor, int(options["port"])),
            node_factory,
            listen_precondition_checks=[(node_factory.load_account, True)],
            got_listen=[node_factory.p2p_listen_ok]
        )
        top_service.addService(p2p_service)
        return top_service

    def get_node(self, options):
        node_type = options["node_type"]
        return node_registry[node_type]

service_maker = BlockchainNodeServiceMaker()
