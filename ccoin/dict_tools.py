import contextlib


def merge_deep(source, destination):
    """
    >>> a = { 'first' : { 'all_rows' : { 'pass' : 'dog', 'number' : '1' } } }
    >>> b = { 'first' : { 'all_rows' : { 'fail' : 'cat', 'number' : '5' } } }
    >>> merge_deep(b, a) == { 'first' : { 'all_rows' : { 'pass' : 'dog', 'fail' : 'cat', 'number' : '5' } } }
    True
    """
    for key, value in source.items():
        if isinstance(value, dict):
            # get node or create one
            node = destination.setdefault(key, {})
            destination[key] = merge_deep(value, node)
        else:
            destination[key] = value

    return destination


def remove_empty(d):
    keys = []
    for k, v in d.items():
        if v is None:
            keys.append(k)
    for k in keys:
        d.pop(k, None)
    return d


class LazyDict(dict):
    root = None

    def set_root(self, root):
        self.root = root

    def format_string(self, value):
        formatter = self.root or self
        formatted = value.format(**formatter)
        if formatted != value:
            return self.format_string(formatted)
        return formatted

    def __getitem__(self, key):
        value = super(LazyDict, self).__getitem__(key)
        if isinstance(value, str):
            return self.format_string(value)
        if isinstance(value, dict):
            d = LazyDict(value)
            d.set_root(self)
            return d
        return value

    @contextlib.contextmanager
    def patch(self, key, val):
        old_val = self.get(key)
        self[key] = val
        yield self
        self[key] = old_val