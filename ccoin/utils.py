import time
import os

def ensure_dir(dir):
    if not os.path.exists(dir):
        os.makedirs(dir)


def int2bytes(integer):
    return str(integer).encode()


def ts():
    return time.time()