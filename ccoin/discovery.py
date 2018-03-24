import os
from twisted.enterprise import adbapi
from twisted.internet import defer
from .peer_info import PeerInfo


class PeerDiscoveryService(object):
    """Simple discovery service"""
    def __init__(self):
        base_path = os.path.expanduser('~/.ccoin')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, "discovery.db")
        self.db = adbapi.ConnectionPool("sqlite3", path, check_same_thread=False)

    @defer.inlineCallbacks
    def initialize(self):
        yield self.db.runInteraction(self.exec_create_table)

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
        yield self.db.runInteraction(self.exec_insert, **peer.to_dict())

    @staticmethod
    def exec_insert(cursor, id=None, ip=None, port=None):
        # TODO if not exists https://stackoverflow.com/questions/19337029/insert-if-not-exists-statement-in-sqlite
        cursor.execute("INSERT OR REPLACE INTO members VALUES(?, ?, ?)", (id, ip, port))

    @defer.inlineCallbacks
    def remove_member(self, peer_id):
        yield self.db.runInteraction(self.exec_remove, peer_id)

    @staticmethod
    def exec_remove(cursor, peer_id):
        cursor.execute("DELETE FROM members WHERE id=?", peer_id)

    @defer.inlineCallbacks
    def get_members(self):
        """
        Stream peers that resided under the k-v storage.
        """
        members = yield self.db.runQuery('SELECT * FROM members')
        return [PeerInfo.from_tuple(member) for member in members]