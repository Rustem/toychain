from abc import ABC, abstractmethod, abstractclassmethod
from twisted.enterprise import adbapi
from twisted.internet import defer
import os

class Serializable(ABC):

    @abstractmethod
    def to_dict(self):
        pass

    @classmethod
    @abstractclassmethod
    def from_dict(cls, data):
        pass


class SharedDatabaseServiceMixin(object):

    base_path = None

    db = None

    def __init__(self):
        self.base_path = base_path = os.path.expanduser('~/.ccoin')
        if not os.path.exists(base_path):
            os.makedirs(base_path)
        path = os.path.join(base_path, "accounts.db")
        self.db = adbapi.ConnectionPool("sqlite3", path, check_same_thread=False)

    @defer.inlineCallbacks
    def initialize(self):
        yield self.ensure_table()

    @defer.inlineCallbacks
    @abstractmethod
    def ensure_table(self):
        raise NotImplementedError("")