import json
from twisted.internet import defer
from twisted.web import resource
from twisted.web.server import NOT_DONE_YET

from ccoin.base import SharedDatabaseServiceMixin
from ccoin.peer_info import PeerInfo

# TODO 1 take ccoin/discover code
# TODO 2 create http server that listens for commands
    # add member
    # remove member
    # get_all_members
# TODO 3 wrap into docker container


class PeerDiscoveryService(SharedDatabaseServiceMixin):
    """Simple discovery service"""

    def __init__(self):
        super().__init__()
        self.ensure_check_done = False

    @defer.inlineCallbacks
    def ensure_table(self):
        yield self.db.runInteraction(self.exec_create_table)
        self.ensure_check_done = True

    @staticmethod
    def exec_create_table(cursor):
        cursor.execute("""
          CREATE TABLE IF NOT EXISTS members (id text PRIMARY KEY, ip text NOT NULL, port integer NOT NULL)
        """)

    @defer.inlineCallbacks
    def add_member(self, peer):
        """
        :param peer:
        :type peer: PeerInfo
        :return:
        """
        if not self.ensure_check_done:
            yield self.ensure_table()
        yield self.db.runInteraction(self.exec_insert, **peer)
        return True

    @staticmethod
    def exec_insert(cursor, id=None, ip=None, port=None):
        # TODO if not exists https://stackoverflow.com/questions/19337029/insert-if-not-exists-statement-in-sqlite
        cursor.execute("INSERT OR REPLACE INTO members VALUES(?, ?, ?)", (id, ip, port))

    @defer.inlineCallbacks
    def remove_member(self, peer_id):
        if not self.ensure_check_done:
            yield self.ensure_table()
        yield self.db.runInteraction(self.exec_remove, (peer_id,))
        return True

    @staticmethod
    def exec_remove(cursor, peer_id):
        cursor.execute("DELETE FROM members WHERE id=?", peer_id)

    @defer.inlineCallbacks
    def get_members(self):
        """
        Stream peers that resided under the k-v storage.
        """
        if not self.ensure_check_done:
            yield self.ensure_table()
        members = yield self.db.runQuery('SELECT * FROM members')
        return [PeerInfo.from_tuple(member).to_dict() for member in members]


class MembershipHttpResource(resource.Resource):

    discovery_service = None
    isLeaf = True

    def __init__(self, discovery_service):
        super().__init__()
        self.discovery_service = discovery_service

    def render(self, request):
        request.setHeader(b"accept", b"application/json")
        request.setHeader(b"content-type", b"application/json; charset=utf-8")
        response = super(MembershipHttpResource, self).render(request)
        return response

    def format_response(self, response):
        return json.dumps(response,
                          allow_nan=False,).encode('utf-8')

    def render_POST(self, request):
        data = json.loads(request.content.getvalue().decode())
        d = None
        if data["command"] == "add":
            d = self.handle_add_member(request, data)
        elif data["command"] == "remove":
            d = self.handle_remove_member(request, data)
        elif data["command"] == "get_all":
            d = self.handle_get_all_members(request, data)
        else:
            self._responseFailed(Exception("no such command registered"), request)
        # request.notify_finish().addErrback(self._responseFailed, request)
        if d:
            d.addErrback(self._responseFailed, request)
        return NOT_DONE_YET

    def _responseFailed(self, err, request):
        request.setResponseCode(400)
        request.write(str(err).encode())
        request.finish()
        return err

    @defer.inlineCallbacks
    def handle_add_member(self, request, data):
        ok = yield self.discovery_service.add_member(data["peer"])
        request.write(self.format_response(ok))
        request.finish()

    @defer.inlineCallbacks
    def handle_remove_member(self, request, data):
        ok = yield self.discovery_service.remove_member(data["peer_id"])
        request.write(self.format_response(ok))
        request.finish()

    @defer.inlineCallbacks
    def handle_get_all_members(self, request, data):
        peers = yield self.discovery_service.get_members()
        request.write(self.format_response(peers))
        request.finish()