__all__=('unifunc',)
from functools import wraps
from reportlab.lib.utils import isBytes
def unifunc(f=None,tx=0,enc='utf8'):
    '''makes a function which accepts both unicode and bytes'''
    if f:
        @wraps(f)
        def inner(*args, **kwds):
            text = args[tx]
            if isBytes(tx):
                text = text.decode(enc)
                args = args[:tx]+(text,)+args[tx:]
                return f(*args, **kwds).encode(enc)
            else:
                return f(*args, **kwds)
        return inner
    else:
        return lambda f: unifunc(f,tx=tx,enc=enc)
