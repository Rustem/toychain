from twisted.application import service
from twisted.internet import defer, reactor


class ExecuteAndForgetService(service.Service):

    def __init__(self, callable, *args, **kwargs):
        self.call = (callable, args, kwargs)
        self.callId = None

    @defer.inlineCallbacks
    def startService(self):
        service.Service.startService(self)
        result = yield self.call[0](*self.call[1], **self.call[2])
        # shutting down reactor
        reactor.stop()


    def stopService(self):
        service.Service.stopService(self)
        if self.callId and self.callId.active():
            self.callId.cancel()