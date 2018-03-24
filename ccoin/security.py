# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/dsa/
import msgpack
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization


def sign(private_key, message_bytes):
    """Sign message_bytes with RSA cryptography tools"""
    digest = hash_message(message_bytes)
    private_key = serialization.load_pem_private_key(
        private_key, password=None, backend=default_backend())
    pad = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH)
    signature = private_key.sign(digest, pad, utils.Prehashed(hashes.SHA256()))
    return signature


def verify(signature, message_bytes, public_key):
    """Verifies signature with RSA cryptography tools"""
    digest = hash_message(message_bytes)
    public_key = serialization.load_pem_public_key(public_key, backend=default_backend())
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
    return digest


def hash_map(data):
    msg_bytes = msgpack.packb(frozenset(sorted(data.items())))
    return hash_message(msg_bytes)