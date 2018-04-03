from twisted.application import service
from twisted.internet import defer, reactor
from twisted.python import log

from ccoin.app_conf import configure_from_file

# TODO  use task.react() instead for one-off operation https://twistedmatrix.com/documents/16.3.1/api/twisted.internet.task.html

class ExecuteAndForgetService(service.Service):

    def __init__(self, callable, *args, **kwargs):
        self.call = (callable, args, kwargs)
        self.callId = None

    @defer.inlineCallbacks
    def startService(self):
        service.Service.startService(self)
        result = yield self.call[0](*self.call[1], **self.call[2])
        self.stopService()

    def stopService(self):
        service.Service.stopService(self)
        if self.callId and self.callId.active():
            self.callId.cancel()
        reactor.callFromThread(reactor.stop)


class Configurable(object):

    def configure(self, options):
        # Ensures application is configured prior to any calls
        try:
            configure_from_file(options["config"])
        except FileNotFoundError:
            log.err()
            reactor.stop()
            return
