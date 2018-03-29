from twisted.application import service
from twisted.internet import defer
from twisted.plugin import IPlugin
from twisted.python import usage, log
from zope.interface import implementer

from ccoin.accounts import Account
from twisted.plugins.base import ExecuteAndForgetService, Configurable


class Options(usage.Options):

    optParameters = [
        ['config', 'c', 'ccoin.json', 'Application config file'],
    ]


@defer.inlineCallbacks
def create_account():
    """Generates public/private keys under the specified path"""
    account = yield defer.maybeDeferred(Account.create)
    log.msg("Created account: %s" % account.address)


@implementer(service.IServiceMaker, IPlugin)
class CreateAccountServiceMaker(Configurable):
    tapname = "create-account"
    description = "Creates blockchain network account."
    options = Options

    def makeService(self, options):
        self.configure(options)
        return ExecuteAndForgetService(create_account)


service_maker = CreateAccountServiceMaker()
