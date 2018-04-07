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
    isLeaf = False

    txn_id = None

    def getChild(self, path, request):
        if path:
            self.txn_id = path.decode()
        return self

    def render_POST(self, request):
        print(self.txn_id)
        if not self.txn_id:
            data = json.loads(request.content.getvalue().decode())
            txn = self.node.make_transfer_txn(data["sendto_address"], data["amount"])
            txn_id = self.node.relay_txn(txn)
            print("TransactionId", txn_id)
            return txn.to_dict()
        else:
            assert self.txn_id is not None, "Pass transaction id parameter"
            data = json.loads(request.content.getvalue().decode())
            txn = self.node.get_txn_info(self.txn_id, data["block_number"])
            return txn and txn.to_dict() or None


class BlockManageResource(JSONP2PRelayResource):
    isLeaf = False

    def getChild(self, path, request):
        print(path, path == b'cnt')
        if path == b'cnt':
            return BlockCountResource(self.node)
        elif path.isdigit():
            return BlockInfoResource(self.node, int(path))
        return self


class BlockInfoResource(JSONP2PRelayResource):
    # blk/1/
    isLeaf = True

    def __init__(self, node, block_number):
        super().__init__(node)
        self.block_number = block_number

    def render_GET(self, request):
        block_data = self.node.get_block_info(self.block_number)
        return block_data and block_data or None


class BlockCountResource(JSONP2PRelayResource):
    # blk/cnt/
    isLeaf = True

    def render_GET(self, request):
        return self.node.get_block_count()


def run_http_api(node, port, callback=None, errback=None):
    RestApi = RootResource(node)
    node_resource = NodeResource()
    RestApi.putChild(node.id.encode(), node_resource)
    # manage transaction resource
    node_resource.putChild(b"txn", TransactionManageResource())
    node_resource.putChild(b"blk", BlockManageResource())

    site = server.Site(RestApi)

    http_endpoint = TCP4ServerEndpoint(reactor, port)
    d = http_endpoint.listen(site)
    if callback:
        d.addCallback(callback)
    if errback:
        d.addErrback(errback)
    return d

