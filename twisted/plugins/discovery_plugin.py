from twisted.web import server
from zope.interface import implementer
from twisted.python import usage, log
from twisted.plugin import IPlugin
from twisted.internet import reactor
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.application import internet, service
from discovery import PeerDiscoveryService, MembershipHttpResource


class Options(usage.Options):

    optParameters = [
        ['host', 'h', '', 'Listen on All interfaces by default'],
        ['port', 'p', 4444, 'Port number'],
    ]


@implementer(service.IServiceMaker, IPlugin)
class SimpleDiscoveryServiceMaker(object):
    tapname = "discovery"
    description = "A simple discovery service."
    options = Options

    def makeService(self, options):
        """
        :param options: configuration parameters
        :type options: dict
        :return: endpoint service that runs a p2p server node
        :rtype: service.Service
        """
        membership_resource = MembershipHttpResource(PeerDiscoveryService())
        site = server.Site(membership_resource)
        p2p_service = internet.StreamServerEndpointService(
            TCP4ServerEndpoint(reactor, int(options["port"]), interface=options["host"]),
            site,)
        log.msg("Discover Service listen on port=%s and host=%s" % (options["port"], options["host"] or "0.0.0.0"))
        return p2p_service

service_maker = SimpleDiscoveryServiceMaker()
