import json
from twisted.internet.endpoints import TCP4ServerEndpoint
from twisted.web import resource, server
from twisted.internet import reactor


class P2PRelayResource(resource.Resource):

    node = None

    def __init__(self, node=None):
        if node:
            self.node = node
        super(P2PRelayResource, self).__init__()

    def putChild(self, path, child):
        child.node = self.node
        super(P2PRelayResource, self).putChild(path, child)


class JSONP2PRelayResource(P2PRelayResource):

    def render(self, request):
        request.setHeader(b"accept", b"application/json")
        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        response = super(JSONP2PRelayResource, self).render(request)
        return self.format_response(response)

    def format_response(self, response):
        return json.dumps(response,
                          allow_nan=False,).encode('utf-8')


class RootResource(JSONP2PRelayResource):

    def getChild(self, name, request):
        return resource.Resource.getChild(self, name, request)


class NodeResource(JSONP2PRelayResource):
    isLeaf = False

    def getChild(self, name, request):
        if name == b"":
            return self
        return resource.Resource.getChild(self, name, request)

    def render_GET(self, request):
        request.responseHeaders.addRawHeader(b"content-type", b"application/json")
        return {"peers": len(self.node.peers_connection)}


class TransactionManageResource(JSONP2PRelayResource):
    isLeaf = True

    def render_POST(self, request):
        data = json.loads(request.content.getvalue().decode())
        txn = self.node.make_transfer_txn(data["sendto_address"], data["amount"])
        txn_id = self.node.relay_txn(txn)
        print("TransactionId", txn_id)
        return txn.to_dict()

def run_http_api(node, port, callback=None, errback=None):
    RestApi = RootResource(node)
    node_resource = NodeResource()
    RestApi.putChild(node.id.encode(), node_resource)
    # manage transaction resource
    node_resource.putChild(b"txn", TransactionManageResource())

    site = server.Site(RestApi)

    http_endpoint = TCP4ServerEndpoint(reactor, port)
    d = http_endpoint.listen(site)
    if callback:
        d.addCallback(callback)
    if errback:
        d.addErrback(errback)
    return d

