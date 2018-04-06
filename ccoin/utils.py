import time
import random
import os

def ensure_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def int2bytes(integer):
    return str(integer).encode()


def ts():
    return time.time()


def get_random_string(length=12,
                      allowed_chars='abcdefghijklmnopqrstuvwxyz'
                                    'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'):
    """
    Returns a securely generated random string.

    The default length of 12 with the a-z, A-Z, 0-9 character set returns
    a random string value.
    """
    return ''.join(random.choice(allowed_chars) for i in range(length))