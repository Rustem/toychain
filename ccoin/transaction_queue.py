import heapq


class OrderableTransaction(object):
    def __init__(self, prio, counter, tx):
        """
        :param prio:
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

    """Implements priority queue of transactions where priority is defined by transaction nonce."""

    def __init__(self):
        self.counter = 0
        self.txs = []

    def __len__(self):
        return len(self.txs)

    def add_transaction(self, tx):
        # TODO use better timestamp not nonce (those who added earlier should be added to th enext block earlier)
        prio = -tx.nonce
        heapq.heappush(self.txs, OrderableTransaction(prio, self.counter, tx))
        self.counter += 1

    def pop_transaction(self, max_seek_depth=16, min_gasprice=0):
        return heapq.heappop(self.txs)

    def peek(self, num=None):
        if num:
            return self.txs[0:num]
        else:
            return self.txs

    def diff(self, txs):
        remove_hashes = [tx.id for tx in txs]
        keep = [item for item in self.txs if item.tx.id not in remove_hashes]
        q = TransactionQueue()
        q.txs = keep
        return q