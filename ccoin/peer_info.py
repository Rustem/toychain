import msgpack

class PeerInfo(object):
    """Class that encapsulates peer meta information."""

    def __init__(self, ip, port, uuid=None):
        self.ip = ip
        self.port = port
        if uuid is None:
            self.id = self.gen_id()
        else:
            self.id = uuid

    def gen_id(self):
        raise NotImplementedError()

    def to_dict(self):
        return {"ip": self.ip, "port": self.port, "id": self.id}

    @classmethod
    def from_tuple(cls, peer_data):
        _id, ip, port = peer_data
        return PeerInfo(ip, port, _id)

    @classmethod
    def from_dict(cls, peer_data):
        return PeerInfo(ip=peer_data["ip"], port=peer_data["port"], uuid=peer_data["id"])