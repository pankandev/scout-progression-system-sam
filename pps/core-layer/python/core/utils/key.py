
SPLITTER = '::'


def join_key(*args):
    return SPLITTER.join(args)


def split_key(key: str):
    return key.split(SPLITTER)
