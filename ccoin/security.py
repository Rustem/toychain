# https://cryptography.io/en/latest/hazmat/primitives/asymmetric/dsa/
import msgpack
import base64
import binascii
from unittest.mock import patch
from cryptography.hazmat.primitives.asymmetric import utils
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization

from ccoin import settings


def generate_private_key(public_exponent, key_size, backend):
    # to avoid best practices checks
    with patch("cryptography.hazmat.primitives.asymmetric.rsa._verify_rsa_parameters", return_value=None):
        return backend.generate_rsa_private_key(public_exponent=public_exponent, key_size=key_size)

def generate_key_pair(key_size=1024):
    """Generates private/public RSA key pair and returns them hex-encoded"""
    private_key = generate_private_key(public_exponent=17, key_size=key_size, backend=default_backend())

    private_key_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )
    private_key_hex = binascii.hexlify(private_key_pem)

    public_key = private_key.public_key()
    public_key_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    public_key_hex = binascii.hexlify(public_key_pem)
    return private_key_hex.decode(), public_key_hex.decode()


def load_private_key_from_file(key_path):
    with open(key_path, "rb") as fh:
        return binascii.unhexlify(load_private_key(fh.read()))


def load_private_key(private_hex):
    private_bytes = binascii.unhexlify(private_hex)
    private_key = serialization.load_pem_private_key(
        private_bytes, password=None, backend=default_backend())
    return private_key


def sign(private_hex, message_bytes):
    """Sign message_bytes with RSA cryptography tools"""
    digest = hash_message(message_bytes, hex=False)
    private_bytes = binascii.unhexlify(private_hex)
    private_key = serialization.load_pem_private_key(
        private_bytes, password=None, backend=default_backend())
    pad = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH)
    signature = private_key.sign(digest, pad, utils.Prehashed(hashes.SHA256()))
    return base64.b64encode(signature).decode('ascii')


def verify(base64_signature, message_bytes, public_hex):
    """Verifies signature with RSA cryptography tools"""
    public_bytes = binascii.unhexlify(public_hex)
    public_key = serialization.load_pem_public_key(public_bytes.encode(), backend=default_backend())
    signature = base64.b64decode(base64_signature.encode('ascii'))
    digest = hash_message(message_bytes, hex=False)
    pad = padding.PSS(
        mgf=padding.MGF1(hashes.SHA256()),
        salt_length=padding.PSS.MAX_LENGTH)
    try:
        public_key.verify(signature, digest, pad, utils.Prehashed(hashes.SHA256()))
    except InvalidSignature:
        return False
    else:
        return True


def hash_message(message_bytes, hex=True):
    if not message_bytes:
        return settings.BLANK_SHA_256
    hash_backend = hashes.SHA256()
    hasher = hashes.Hash(hash_backend, default_backend())
    hasher.update(message_bytes)
    digest = hasher.finalize()
    if not hex:
        return digest
    return binascii.hexlify(digest).decode()


def hash_map(data):
    msg_bytes = msgpack.packb(sorted(data.items()))
    return hash_message(msg_bytes)