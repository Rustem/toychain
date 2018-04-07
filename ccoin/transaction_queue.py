import binascii
import heapq


class PriorityValue(object):

    def __lt__(self, other):
        raise NotImplementedError("not implemented")


class TransactionPriorityValue(PriorityValue):

    def __init__(self, address, nonce):
        self.address = address
        self.nonce = nonce

    def __lt__(self, other):
        if self.address < other.address:
            return True
        if self.address == other.address:
            if self.nonce < other.nonce:
                return True
            else:
                return False
        return False

    def __gt__(self, other):
        if self.address > other.address:
            return True
        if self.address == other.address:
            if self.nonce > other.nonce:
                return True
            else:
                return False
        return False

    def __eq__(self, other):
        """
        :param other:
        :type other: TransactionPriorityValue
        :return:
        """
        return self.address == other.address and self.nonce == other.nonce



class OrderableTransaction(object):
    def __init__(self, prio, counter, tx):
        """
        :param prio:
        :type: PriorityValue
        :param counter: monotonically increasing and unique for each transaction under queue
        :type counter:
        :param tx:
        :type tx: ccoin.messages.Transaction
        """
        self.prio = prio
        self.counter = counter
        self.tx = tx

    def __lt__(self, other):
        if self.prio < other.prio:
            return True
        elif self.prio == other.prio:
            return self.counter < other.counter
        else:
            return False



class TransactionQueue():

    """Implements priority queue of transactions where priority is defined by transaction time."""

    def __init__(self):
        self.counter = 0
        self.txs = []

    def __len__(self):
        return len(self.txs)

    def add_transaction(self, tx):
        """
        Add transaction to the place under the queue assigned by its prioirty.
        :param tx: transaction reference
        :type tx: ccoin.messages.Transaction
        """
        # Priority : the lower the timestamp the more higher position transaction has under the queue
        prio = TransactionPriorityValue(tx.sender, tx.nonce)
        heapq.heappush(self.txs, OrderableTransaction(prio, self.counter, tx))
        self.counter += 1

    def pop_transaction(self):
        """
        Pops the transaction from the queue.
        :return: popped out transaction
        :rtype: ccoin.messages.Transaction
        """
        try:
            item = heapq.heappop(self.txs)
        except IndexError:
            return
        else:
            return item.tx

    def peek(self, num=None):
        """
        Peeks the head slice ordered with priorities from the queue.
        :param num: slice size
        :type num: int
        :return: list of transactions
        :rtype: list[OrderableTransaction]
        """
        if num:
            return self.txs[0:num]
        else:
            return self.txs

    def diff(self, txs):
        """
        Removes input transaction list from the queue.
        :param txs: list of transactions
        :type txs: list[ccoin.messages.Transaction]
        :return: reference to transaction queue
        :rtype: TransactionQueue
        """
        remove_hashes = [tx.id for tx in txs]
        keep = [item for item in self.txs if item.tx.id not in remove_hashes]
        q = TransactionQueue()
        q.txs = keep
        return q


def make_test_tx(nonce=0, data='', amount=0, sender=b'\x35'):
    from ccoin.messages import Transaction
    from_ = binascii.hexlify(sender * 20).decode()
    to = binascii.hexlify(b'\x31' * 20).decode()
    tx = Transaction(from_=from_, to=to, number=nonce, amount=amount, data=data)
    tx.generate_id()
    return tx



def test():
    """
from ccoin.transaction_queue import *
test()
    """
    q = TransactionQueue()
    params = [100000, 50000, 40000, 60000, 30000, 30000, 30000]
    operations = [30000,
                  30000,
                  30000,
                  40000,
                  50000,
                  60000,
                  100000,
                  None,]
    # Add transactions to queue
    for param in params:
        q.add_transaction(make_test_tx(nonce=param))
    # Attempt pops from queue
    for expected_nonce in operations:
        tx = q.pop_transaction()
        if tx:
            assert tx.nonce == expected_nonce
        else:
            assert expected_nonce is None
    print('Test successful')


def test_with_different_address():
    """
from ccoin.transaction_queue import *
test_with_different_address()
    """
    q = TransactionQueue()
    params = [(100000, 123), (50000, 124), (40000, 123), (60000, 124), (30000, 125), (30000, 125), (30000, 123)]
    operations = [
        (30000, 123),
        (40000, 123),
        (100000, 123),
        (50000, 124),
        (60000, 124),
        (30000, 125),
        (30000, 125),
    ]

    def int2hex(integ):
        return hex(integ).lstrip('0x').encode()

    # Add transactions to queue
    for param in params:
        q.add_transaction(make_test_tx(nonce=param[0], sender=int2hex(param[1])))
    # Attempt pops from queue
    for expected_nonce, expected_addr in operations:
        tx = q.pop_transaction()
        if tx:
            sender_prefix = binascii.hexlify(int2hex(expected_addr)).decode()
            assert tx.nonce == expected_nonce and tx.sender.startswith(sender_prefix)
        else:
            assert expected_nonce is None
    print('Test successful')

def test_orderable_tx():
    """
from ccoin.transaction_queue import *
test_orderable_tx()
    """
    assert OrderableTransaction(-1, 0, None) < OrderableTransaction(0, 0, None)
    assert OrderableTransaction(-1, 0, None) < OrderableTransaction(-1, 1, None)
    assert not OrderableTransaction(1, 0, None) < OrderableTransaction(-1, 0, None)
    assert not OrderableTransaction(1, 1, None) < OrderableTransaction(-1, 0, None)


def test_ordering_for_same_prio():
    """
from ccoin.transaction_queue import *
test_ordering_for_same_prio()
    """
    q = TransactionQueue()
    count = 10
    # Add <count> transactions to the queue, all with the same
    for i in range(count):
        q.add_transaction(make_test_tx(nonce=i))

    expected_nonce_order = list(range(count))
    nonces = []
    for i in range(count):
        tx = q.pop_transaction()
        nonces.append(tx.nonce)
    # Since they have the same timestamp they should have the same priority and
    # thus be popped in the order they were inserted.
    assert nonces == expected_nonce_order


def test_diff():
    """
from ccoin.transaction_queue import *
test_diff()
    """
    tx1 = make_test_tx(data='a')
    tx2 = make_test_tx(data='b')
    tx3 = make_test_tx(data='c')
    tx4 = make_test_tx(data='d')
    q1 = TransactionQueue()
    for tx in [tx1, tx2, tx3, tx4]:
        q1.add_transaction(tx)
    q2 = q1.diff([tx2])
    assert len(q2) == 3
    assert tx1 in [item.tx for item in q2.txs]
    assert tx3 in [item.tx for item in q2.txs]
    assert tx4 in [item.tx for item in q2.txs]

    q3 = q2.diff([tx4])
    assert len(q3) == 2
    assert tx1 in [item.tx for item in q3.txs]
    assert tx3 in [item.tx for item in q3.txs]