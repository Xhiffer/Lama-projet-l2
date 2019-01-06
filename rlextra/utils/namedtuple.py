__all__=('NamedTuple',)
from operator import itemgetter
import sys

def NamedTuple(typename, field_names):
    """Returns a new subclass of tuple with named fields.

    >>> Point = PNamedTuple('Point', 'x y')
    >>> Point.__doc__           # docstring for the new class
    'Point(x, y)'
    >>> p = Point(11, y=22)     # instantiate with positional args or keywords
    >>> p[0] + p[1]             # works just like the tuple (11, 22)
    33
    >>> x, y = p                # unpacks just like a tuple
    >>> x, y
    (11, 22)
    >>> p.x + p.y               # fields also accessable by name
    33
    >>> p                       # readable __repr__ with name=value style 
    Point(x=11, y=22)
    >>> p.__field_names__
    ('x', 'y')
    """

    if isinstance(field_names,str): field_names = field_names.split()
    nargs = len(field_names)

    def __new__(cls, *args, **kwds):
        if kwds:
            try:
                args += tuple(kwds[name] for name in field_names[len(args):])
            except KeyError as name:
                raise TypeError('%s missing required argument: %s' % (typename, name))
        if len(args) != nargs:
            raise TypeError('%s takes exactly %d arguments (%d given)' % (typename, nargs, len(args)))
        return tuple.__new__(cls, args)

    def __from_iterable__(cls,arg):
        return cls.__new__(cls,*arg)

    repr_template = '%s(%s)' % (typename, ', '.join('%s=%%r' % name for name in field_names))

    m = dict(vars(tuple))       # pre-lookup superclass methods (for faster lookup)
    m.update(__doc__= '%s(%s)' % (typename, ', '.join(field_names)),
             __slots__ = (),    # no per-instance dict (so instances are same size as tuples)
             __new__ = __new__,
             __repr__ = lambda self, _format=repr_template.__mod__: _format(self),
             __module__ = sys._getframe(1).f_globals['__name__'],
             __field_names__ = tuple(field_names),
             __from_iterable__=classmethod(__from_iterable__),
             )
    m.update((name, property(itemgetter(index))) for index, name in enumerate(field_names))

    return type(typename, (tuple,), m)

def _test():
    import doctest
    return doctest.testmod()

if __name__ == "__main__":
    _test()
