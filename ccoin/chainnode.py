from twisted.internet import defer

from ccoin.accounts import AccountProvider
from ccoin.exceptions import AccountDoesNotExist
from ccoin.p2p_network import BasePeer


# ~/.ccoin/blockchain
# ~/.ccoin/.keys/
# ~/.ccoin/config.json

# TODO 2. Node can connect to P2P Network with already loaded account (done)
# TODO 3. P2P listen Port select automatically (done)
# TODO 4. Node can send transactions signed by account's private key



class ChainNode(BasePeer):

    @defer.inlineCallbacks
    @classmethod
    def withAccount(cls, account_id):
        """
        Initializes and returns node with account object.
        :param account_id: account identifier
        :type account_id: str
        :return: object instance of ChainNode factory
        :rtype: BasePeer
        :raises: NodeCannotBeStartedException if account does not exists
        """
        new_node = ChainNode(account_id)
        yield new_node.load_account()
        return new_node

    def __init__(self, uuid):
        super(ChainNode, self).__init__(uuid)
        self.account = None

    @defer.inlineCallbacks
    def load_account(self):
        self.account = yield AccountProvider().get_by_id(self.id, with_private_key=True)
        if not self.account:
            raise AccountDoesNotExist(self.id)
