from twisted.application import service
from twisted.internet import defer
from twisted.plugin import IPlugin
from twisted.python import usage, log
from zope.interface import implementer

from ccoin.accounts import AccountCreator
from twisted.plugins.base import ExecuteAndForgetService


class Options(usage.Options):

    optParameters = [
        ['nodeid', 'n', None, 'Node identifier'],
        ['is_miner', 'im', False, 'Whether this account has miner privilledge'],
        ['balance', 'b', 0, 'Initial account balance'],
    ]


@defer.inlineCallbacks
def create_account(uid, is_miner=False, balance=0):
    account_creator = AccountCreator()
    yield account_creator.initialize()
    account = yield account_creator.create(uid, is_miner=is_miner, balance=balance)
    defer.returnValue(account)
    log.msg("Created account: %s" % account.to_dict())


@implementer(service.IServiceMaker, IPlugin)
class CreateAccountServiceMaker(object):
    tapname = "create-account"
    description = "Creates blockchain network account."
    options = Options

    def makeService(self, options):
        nodeid = options['nodeid']
        is_miner = options['is_miner']
        balance = int(options['balance'])
        return ExecuteAndForgetService(create_account, nodeid, balance=balance)



service_maker = CreateAccountServiceMaker()
