#!/usr/bin/env python
"""Removes all markup from a string

Should ideally not affect any entities - just remove tags.
Currently (6/9/2012) this aspect seems broken.


>>> 2+2
4
>>> stripTags('hello')
'hello'
>>> stripTags('hello<a href="crap"> world</a>')
'hello world'
>>> stripTags('goodbye<!--stuff--> comments')
'goodbye comments'
>>> stripTags('Entities &amp; stuff')
'Entities & stuff'
>>> stripTags('Fr&#233;gate Island')    #accents etc preserved
'Fr&#233;gate Island'
>>> from reportlab.lib.utils import asBytes
>>> asBytes(stripTags('Space&nbsp;here'))==u'Space\xa0here'.encode('utf8')
True
>>> resolveEntities(b'Fr&#233;gate Island')==b'Fr\\xc3\\xa9gate Island'
True
>>> stripTags('Ch\\xc2\\xa3teau & <tag>Summerhouse</tag>')=='Ch\\xc2\\xa3teau & Summerhouse'
True
>>> stripTags(b'Ch\\xc2\\xa3teau & <tag>Summerhouse</tag>'.decode('utf8'))==b'Ch\\xc2\\xa3teau & Summerhouse'.decode('utf8')
True
"""
from reportlab.platypus.paraparser import HTMLParser, known_entities
from reportlab.lib.utils import uniChr, isUnicode
from rlextra.radxml.xmlutils import nakedAmpFix

def stripTags(text,enc='utf8'):
    return TagStripper().strip(text,enc=enc)

def resolveEntities(text):
    "Turn them to UTF8 text"
    return EntityResolver().resolve(text)

class TagStripper(HTMLParser):
    def strip(self, text, enc='utf8'):
        self._output = []
        self.reset()
        if not isUnicode(text):
            text = text.decode(enc)
        else:
            enc = None
        self.feed(nakedAmpFix(text).replace(u'<br/>',u'<br />'))
        v = u''.join(self._output)
        return v.encode(enc) if enc else v

    def handle_data(self, data):
        self._output.append(data)

    def handle_charref(self, ref):
        "We want char refs to be preserved"
        #print 'ref=',ref, type(ref)
        self.handle_data(u'&#%s;' % ref)

    def handle_entityref(self, name):
        "Handles a named entity.  "
        try:
            v = known_entities[name]
        except:
            v = u'&%s;' % name
        self.handle_data(v)

class EntityResolver(HTMLParser):
    def resolve(self, text, enc='utf8'):
        self._output = []
        self.reset()
        if not isUnicode(text):
            text = text.decode(enc)
        else:
            enc = None
        self.feed(nakedAmpFix(text).replace(u'<br/>',u'<br />'))
        v = u''.join(self._output)
        return v.encode(enc) if enc else v

    def handle_data(self, data):
        self._output.append(data)

    def handle_charref(self, ref):
        try:
            if ref.startswith(u'x'):
                v = int(ref[1:],16)
            else:
                v = int(ref)
            v = uniChr(v)
        except:
            v = u'&#%s;' % ref
        self.handle_data(v)

    def handle_entityref(self, name):
        "Handles a named entity.  "
        try:
            v = known_entities[name]
        except:
            v = u'&%s;' % name
        self.handle_data(v)

if __name__=='__main__':
    import doctest, tagstripper
    doctest.testmod(tagstripper)
