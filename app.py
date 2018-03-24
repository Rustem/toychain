import argparse
import logging
from ccoin.p2p_network import BasePeer

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("node_id", help='Id of the node in the given peers dict.')
    args = parser.parse_args()
    node_id = args.node_id
    node = BasePeer(node_id)
    node.run()


if __name__ == "__main__":
    main()