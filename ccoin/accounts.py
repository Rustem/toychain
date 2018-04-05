from ccoin.app_conf import AppConfig
from ccoin.security import generate_key_pair
from ccoin.utils import ensure_dir


class Account(object):

    @classmethod
    def fromConfig(cls):
        key_path = cls.public_key_path()
        try:
            with open(key_path, "r") as fh:
                public_key_hex = fh.read()
                return cls(public_key_hex)
        except FileNotFoundError:
            return

    @classmethod
    def fromAddress(cls, address):
        with AppConfig.patch("account_address", address) as conf:
            key_path = cls.public_key_path()
            try:
                with open(key_path, "r") as fh:
                    public_key_hex = fh.read()
                    return cls(public_key_hex)
            except FileNotFoundError:
                return

    def __init__(self, public_key):
        self.public_key = public_key
        self.address = self.public_key[115:155]
        self.private_key = None

    @staticmethod
    def private_key_path():
        join = AppConfig["pj"]
        return join(AppConfig["key_dir"], "id_rsa")

    @staticmethod
    def public_key_path():
        join = AppConfig["pj"]
        return join(AppConfig["key_dir"], "id_rsa.pub")

    def load_private_key(self):
        if not self.private_key and AppConfig["key_dir"]:
            with open(self.private_key_path(), 'r') as fh:
                self.private_key = fh.read()
        return self.private_key

    def store_keys(self, private_key):
        """Stores keys and ensures that necessary directories are exists."""
        with AppConfig.patch("account_address", self.address):
            ensure_dir(AppConfig["key_dir"])
            with open(self.private_key_path(), "w") as fh:
                fh.write(private_key)
            with open(self.public_key_path(), "w") as fh:
                fh.write(self.public_key)

    @classmethod
    def create(cls):
        private_key_hex, public_key_hex = generate_key_pair()
        account = cls(public_key_hex)
        account.store_keys(private_key_hex)
        return account