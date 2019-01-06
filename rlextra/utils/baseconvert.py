BASE2 = "01"
BASE10 = "0123456789"
BASE16 = "0123456789ABCDEF"
BASE36 = "0123456789abcdefghijklmnopqrstuvwxyz"
BASE62 = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789abcdefghijklmnopqrstuvwxyz"

def baseconvert(number,fromdigits,todigits):
    """ converts a "number" between two bases of arbitrary digits

    The input number is assumed to be a string of digits from the
    fromdigits string (which is in order of smallest to largest
    digit). The return value is a string of elements from todigits
    (ordered in the same way). The input and output bases are
    determined from the lengths of the digit strings. Negative 
    signs are passed through.

    decimal to binary
    >>> baseconvert(555,BASE10,BASE2)
    '1000101011'

    binary to decimal
    >>> baseconvert('1000101011',BASE2,BASE10)
    '555'

    integer interpreted as binary and converted to decimal (!)
    >>> baseconvert(1000101011,BASE2,BASE10)
    '555'

    base10 to base4
    >>> baseconvert(99,BASE10,"0123")
    '1203'

    base4 to base5 (with alphabetic digits)
    >>> baseconvert(1203,"0123","abcde")
    'dee'

    base5, alpha digits back to base 10
    >>> baseconvert('dee',"abcde",BASE10)
    '99'

    decimal to a base that uses A-Z0-9a-z for its digits
    >>> baseconvert(257938572394,BASE10,BASE62)
    'E78Lxik'

    ..convert back
    >>> baseconvert('E78Lxik',BASE62,BASE10)
    '257938572394'

    binary to a base with words for digits (the function cannot convert this back)
    >>> baseconvert('1101',BASE2,('Zero','One'))
    'OneOneZeroOne'
    >>> baseconvert(0,BASE10,BASE62)
    'A'
    >>> baseconvert('A',BASE62,BASE10)
    '0'
    >>> baseconvert('K',BASE62,BASE10)
    '10'
    >>> baseconvert(10,BASE10,BASE62)
    'K'
    """
    snum = str(number)
    neg = snum[0]=='-'
    if neg: snum = snum[1:]

    # make an integer out of the number
    x=0
    b = len(fromdigits)
    a = fromdigits.index
    for d in snum:
       x = x*b + a(d)
    
    # create the result in base 'len(todigits)'
    res = []
    a =res.append
    b = len(todigits)
    if not x: a(todigits[0])
    while x>0:
        x, d = divmod(x,b)
        a(todigits[d])
    if neg: a('-')
    res.reverse()

    return ''.join(res)

def _62_10(s):
    return baseconvert(s,BASE62,BASE10)

def _10_62(s):
    return baseconvert(s,BASE10,BASE62)

def _test():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _test()
