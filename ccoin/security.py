# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/dsa/
import msgpack
import base64
import binascii
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa


def generate_key_pair(key_size=1024):
    """Generates private/public RSA key pair"""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size, backend=default_backend())
    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return private_key_pem.decode(), public_key_pem.decode()


def load_private_key_from_file(key_path):
    with open(key_path, "rb") as fh:
        return load_private_key(fh.read())


def load_private_key(private_bytes):
    private_key = serialization.load_pem_private_key(
        private_bytes, password=None, backend=default_backend())
    return private_key


def sign(private_key, message_bytes):
    """Sign message_bytes with RSA cryptography tools"""
    digest = hash_message(message_bytes)
    private_key = serialization.load_pem_private_key(
        private_key, password=None, backend=default_backend())
    pad = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH)
    signature = private_key.sign(digest, pad, utils.Prehashed(hashes.SHA256()))
    return base64.b64encode(signature).decode('ascii')


def verify(base64_signature, message_bytes, public_key):
    """Verifies signature with RSA cryptography tools"""
    signature = base64.b64decode(base64_signature.encode('ascii'))
    digest = hash_message(message_bytes)
    public_key = serialization.load_pem_public_key(public_key.encode(), backend=default_backend())
    pad = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH)
    try:
        public_key.verify(signature, digest, pad, utils.Prehashed(hashes.SHA256()))
    except InvalidSignature:
        return False
    else:
        return True


def hash_message(message_bytes):
    hash_backend = hashes.SHA256()
    hasher = hashes.Hash(hash_backend, default_backend())
    hasher.update(message_bytes)
    digest = hasher.finalize()
    return binascii.hexlify(digest).decode()


def hash_map(data):
    msg_bytes = msgpack.packb(sorted(data.items()))
    return hash_message(msg_bytes)