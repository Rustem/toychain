from ccoin.accounts import AccountProvider
from ccoin.p2p_network import BasePeer


# ~/.ccoin/blockchain
# ~/.ccoin/.keys/
# ~/.ccoin/config.json

# TODO 2. Node can connect to P2P Network with already loaded account
# TODO 3. P2P listen Port select automatically (done)
# TODO 4. Node can send transactions signed by account's private key



class Node(BasePeer):

    def __init__(self, uuid):
        super(Node, self).__init__(uuid)
        self.account = AccountProvider.get_by_uid(uuid, with_private_key=True)

