import json
from twisted.application import service
from twisted.plugin import IPlugin
from twisted.python import usage, log
from zope.interface import implementer
from ccoin.genesis_helpers import make_genesis_block
from twisted.plugins.base import ExecuteAndForgetService, Configurable


class Options(usage.Options):

    optParameters = [
        ['config', 'c', 'ccoin.json', 'Application config file'],
        ['genesis', 'g', 'genesis.json', 'Genesis configuration file'],
    ]


@implementer(service.IServiceMaker, IPlugin)
class GenesisBlockServiceMaker(Configurable):
    tapname = "initc"
    description = "Initializes blockchain network by defining genesis block."
    options = Options

    def makeService(self, options):
        self.configure(options)
        try:
            with open(options["genesis"], "r") as fh:
                genesis_config = json.load(fh)
        except FileNotFoundError:
            log.err()
            return
        else:
            print(genesis_config)
            return ExecuteAndForgetService(make_genesis_block, genesis_config)


service_maker = GenesisBlockServiceMaker()
