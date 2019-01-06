def main(filters,fileNames):
    import base64, zlib, bz2
    from xml.sax.saxutils import escape
    from reportlab.pdfbase import pdfutils
    if isinstance(filters,str):
        filters = filters.split()
    for fn in fileNames:
        f = open(fn,'rb')
        try:
            data = f.read()
        finally:
            f.close()
        for filter in filters:
            filter = filter.strip()
            if not filter: continue
            if filter=='base64':
                data = base64.standard_b64encode(data)
            elif filter=='ascii85':
                data = pdfutils._AsciiBase85Encode(data)
            elif filter=='bzip2':
                data = bz2.compress(data)
            elif filter=='gzip':
                data = zlib.compress(data)
            else:
                raise ValueError('unknown inlinedata filter %r not one of ascii85, base64, gzip or bzip2' % filter)
        print("<inlineData filters=%r>%s</inlineData>" % (' '.join(reversed(filters)),escape(data)))

if __name__=='__main__':
    import sys
    main(sys.argv[1],sys.argv[2:])
