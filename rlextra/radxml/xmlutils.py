"Some XML helper classes."
from reportlab import xrange
import os, re
from reportlab.lib.utils import strTypes, asUnicode, bytesT, unicodeT, asBytes, isUnicode, isPy3
from rlextra.utils.unifunc import unifunc
from itertools import takewhile

#import logging
#logger = logging.getLogger("reportlab.xmlutils")
from xml.sax.saxutils import escape

nakedAmpRe = re.compile(u'&\\s')

IGNOREWHITESPACE = 1
_XMLESCAPE=1

if _XMLESCAPE:
    xmlEscape = escape
else:
    xmlEscape = lambda x: x

class quotedBytes(bytes):   #use this to avoid re-escaping
    pass
class quotedUnicode(str):   #use this to avoid re-escaping
    pass

def _is_basestring(s):
    return isinstance(s,strTypes)

def __dict_replace(s, d):
    # This is grabbed from xml.sax.saxutils
    """Replace substrings of a string using a dictionary."""
    for key, value in list(d.items()):
        s = s.replace(asUnicode(key), asUnicode(value))
    return s

@unifunc
def unescape(data, entities={}):
    # This is grabbed from xml.sax.saxutils
    """Unescape &amp;, &lt;, and &gt; in a string of data.

    You can unescape other strings of data by passing a dictionary as
    the optional entities parameter.  The keys and values must all be
    strings; each key will be replaced with its corresponding value.
    """
    data = data.replace(u"&lt;", u"<")
    data = data.replace(u"&gt;", u">")
    if entities:
        data = __dict_replace(data, entities)
    # must do ampersand last
    return data.replace("&amp;", "&")

@unifunc
def escapeNakedAmpersands(xmlText):
    # avoid a problem caused by the Fidelity transport
    # protocol - embedding xml in an attribute of a form
    return nakedAmpRe.sub(u'&amp; ', xmlText)

@unifunc
def nakedAmpFix(s,okre=re.compile(u'^(?:[\\w_:][\\w0-9_:.-]+|#(?:\\d+|x[0-9a-f]+));',re.I)):
    L = s.split(u'&')
    R = []
    for l in L:
        if not okre.match(l): l = u'amp;'+l
        R.append(l)
    return u'&'.join(R)[4:]

@unifunc
def translateStandardEntities(s,mode=0):
    ''' &amp; &lt; &gt; &quot; &apos; --> & < > " ' mode = 0 or
        & < > " ' --> &amp; &lt; &gt; &quot; &apos; mode = 1]
    >>> translateStandardEntities("&amp;&lt;&gt;&apos;&quot;",mode=0)=='&<>\\'"'
    True
    >>> translateStandardEntities("&<>'\\"",mode=1)
    '&amp;&lt;&gt;&apos;&quot;'
    '''  #"
    if mode:
        return s.replace("&",'&amp;').replace("<",'&lt;').replace(">",'&gt;').replace('"','&quot;').replace("'",'&apos;')
    else:
        return s.replace('&amp;',"&").replace('&lt;',"<").replace('&gt;',">").replace('&quot;','"').replace('&apos;',"'")

from rlextra.utils.cgisupport import quoteValue
def oQuoteValue(s):
    if not isinstance(s,(quotedBytes,quotedUnicode)): s = quoteValue(s)
    return s

def _makeXMLTag(name,attrs,contents,inner=1,depth=0,space=u' '):
    T = []
    a = T.append
    if inner:
        indent = depth*space
        start = u'%s<%s' % ((depth and '\n' or '')+indent,name)
        a(start)
        for k,v in list(attrs.items()):
            a(u'%s="%s"' % (k,oQuoteValue(v)))
        T[:] = [u' '.join(T)]
    if contents is None:
        if inner: a(u'/>')
    else:
        if inner:
            a(u'>')
            depth += 1
        for c in contents:
            a(reconstructXML(c,inner=1,depth=depth,space=space))
        if inner:
            a(u'%s%s</%s>' % ((not T[-1].endswith(u'\n') and u'\n' or u''),indent,name))
    return u''.join(T)

def reconstructXML(tag,inner=0,depth=0,space=u' '):
    '''Takes a TagWrapper and converts to XML,
    if inner=1 then the outer tag is made explicit'''
    r = [].append
    if isinstance(tag,(list,tuple)):
        r(_makeXMLTag(tag[0],tag[1] or {},tag[2],depth=depth,space=space))
    elif isinstance(tag,TagWrapper):
        r(_makeXMLTag(tag.tagName,tag._attrs,tag._children,inner=inner,depth=depth,space=space))
    else:
        r(oQuoteValue(tag))
    return u''.join(r.__self__)

def ignoreWhitespace(L):
    N = []
    a = N.append
    for e in L:
        if isinstance(e,strTypes):
            e = e.strip()
            if not e: continue
        a(e)
    L[:] = N
    return L

    #####################################################
    #
    # miscellaneous tree manipulating utilities.  Work in
    # place where possible.
    #####################################################

def writeXML(tree):
    "Convert to a string.  No auto-indenting provided yet"
    if isUnicode(tree):
        return tree
    else:
        (tagName, attrs, children, spare) = tree
        chunks = []
        chunks.append(u'<%s ' % tree)

def stripWhitespace(tree):
    "Remove any whitespace-only text nodes from the tree."
    tagName, attrs, children, spare = tree
    if children is None:
        return
    to_remove = []
    for child in children:
        if isinstance(child,strTypes):
            if not child.strip():
                to_remove.append(child)
        elif isinstance(child,tuple):
            stripWhitespace(child)
    for rem in to_remove:
        children.remove(rem)

def transformTagNames(tree, func):
    "Replace tagName with func(tagName)"
    tagName, attrs, children, spare = tree

    newTagName = func(tagName)
    if children is None:
        newChildren = None
    else:
        newChildren = []
        for child in children:
            if isinstance(child,strTypes):
                newChildren.append(child)
            elif isinstance(child,tuple):
                newChildren.append(transformTagNames(child, func))
    return (newTagName, attrs, newChildren, spare)

def textTransform(tree, func, errorCb=None):
    tagName, attrs, children, stuff = tree
    if attrs is not None:
        newAttrs = {}
        for key, value in list(attrs.items()):
            newAttrs[key] = func(value, errorCb)[0]
    else:
        newAttrs = None

    if children is not None:
        newChildren = []
        for child in children:
            if isinstance(child,strTypes):
                newChildren.append(func(child, errorCb)[0])
            else:
                newChildren.append(textTransform(child, func, errorCb))
    else:
        newChildren = None

    return (tagName, newAttrs, newChildren, stuff)

def unicodeToUTF8(tree):
    tagName, attrs, children, spare = tree
    newTagName = asBytes(tagName)
    if attrs is None:
        newAttrs = None
    else:
        newAttrs = {}
        for key, value in list(attrs.items()):
            newAttrs[key.encode('utf8')] = value.encode('utf8')
    if children is None:
        newChildren = None
    else:
        newChildren = []
        for child in children:
            if isinstance(child,bytesT):
                newChildren.append(child.encode('utf8'))
            elif isinstance(child,unicodeT):
                newChildren.append(child)
            else:
                newChildren.append(unicodeToUTF8(child))
    return (newTagName, newAttrs, newChildren, spare)

def escapeTree(tag):
    "Apply <, >, & escapes throughout and return new tree"
    tagName, attrs, children, stuff = tag
    if children is None:
        newChildren = None
    else:
        newChildren = []
        for child in children:
            if child is None:
                newChildren.append(child)
            elif isinstance(child,strTypes):
                newChildren.append(escape(child))
            else:
                newChildren.append(escapeTree(child))
    return (tagName, attrs, newChildren, stuff)

class TupleTreeWalker:
    """Iterates over a pyRXPU-parsed tree generating events.

    This works on a 'tree in memory' so does not offer the same small footprint
    as a pure event-driven parser.

    """
    def __init__(self, tree):
        self.tree = tree
        self._stack = []
    def begin(self):
        pass
    def startElement(self, tagName, attrs):
        #print('startTag(%s)' % tagName)
        pass
    def endElement(self, tagName):
        pass
    def characters(self, text):
        pass
    def end(self):
        pass

    def handleNode(self, node):
        self._stack.append(node)
        (tagName, attrs, children, spare) = node
        if attrs is None:
            attrs = {}
        self.startElement(tagName, attrs)
        if children is not None:
            for child in children:
                if isinstance(child,strTypes):
                    self.characters(child)
                else:
                    self.handleNode(child)
        self.endElement(tagName)
        self._stack.pop()

    def getParentTagName(self):
        if self.stack:
            return self._stack[-1][0]
        else:
            return None

    def getCurrentNode(self):
        "For cheating and switching to DOM node. You may use this in your overridden methods"
        return self._stack[-1]
    
    def go(self):
        self.begin()
        self.handleNode(self.tree)
        self.end()

class TagWrapper:
    """Lazy utility for navigating XML.

    The following Python code works:

    tag.attribute      # returns given attribute
    tag.child          # returns first child with matching tag name
    for child in tag:  # iterates over them
    tag[3]             # returns fourth child
    len(tag)           # no of children

    TagWrapper is subclass-safe.  As it wraps, it returns
    instances of its runtime class.

    >>> import pyRXPU
    >>> sample = '<breakfast><drink value="juice"/><food value="eggs"/><food value="bacon"/><drink value="coffee"/><food value="toast"/></breakfast>'
    >>> top = TagWrapper(pyRXPU.Parser().parse(sample))
    """
    def __init__(self, node, parent=None):
        tagName, attrs, children, spare = node
        self.tagName = tagName

        if attrs is None:
            self._attrs = {}
        else:
            self._attrs = attrs  # share the dictionary

        if children is None:
            self._children = []
        elif IGNOREWHITESPACE:
            self._children = ignoreWhitespace(children)
        else:
            self._children = children
        self._parent = parent
        self._spare = spare

    def __del__(self):
        if '_parent' in self.__dict__:
            del self.__dict__['_parent']

    def __repr__(self):
        return u'[%s %s@%8.8x]' % (self.tagName, self.__class__.__name__, id(self))

    def __str__(self):
        '''
        return concatenated leading string children or '' if empty
        raises a ValueError if the leading child is true and not a string
        >>> import pyRXPU
        >>> s = '<a><b>1111<![CDATA[2222]]>3333<c>4444</c>5555</b><d><e>5555</e>6666</d></a>'
        >>> t = TagWrapper(pyRXPU.Parser().parse(s))
        >>> print(str(t.b))
        111122223333
        >>> print(str(t.b.c))
        4444
        >>> print(str(t.d)) #doctest: +ELLIPSIS
        Traceback (most recent call last):
            ...
        ValueError: [d TagWrapper@...]: __str()__ first child is [e TagWrapper@...] not string
        '''
        if len(self._children):
            if isinstance(self._children[0],strTypes):
                return ''.join(takewhile(_is_basestring,self))
            elif self[0]:
                raise ValueError('%r: __str()__ first child is %r not string' % (self,self[0]))
        return ''
    
    def myfunc(self):
        if len(self._children):
            if isinstance(self._children[0],strTypes):
                return ''.join(takewhile(_is_basestring,self))
            elif self[0]:
                raise ValueError('%r: __str()__ first child is %r not string' % (self,self[0]))
        return ''

    def __iter__(self):
        i = 0
        while i<len(self._children):
            yield self[i]
            i += 1

    def _cxiter(self):
        i = 0
        while i<len(self._children):
            yield i,self[i]
            i += 1

    def __len__(self):
        return len(self._children)

    def _value(self,name,default):
        try:
            r = getattr(self,name)
            if isinstance(r,strTypes): return r
            return r[0]
        except (AttributeError, IndexError):
            return default

    def __getattr__(self, attr):
        "Try various priorities"
        if attr in self._attrs:
            return self.xmlEscape(self._attrs[attr])
        else:
            #first child tag whose name matches?
            for child in self._children:
                if not isinstance(child,strTypes):
                    tagName, attrs, children, spare = child
                    if tagName == attr:
                        return self.__class__(child,(self._children,self._children.index(child)))
        # not found, barf
        return self.handleFailedGetAttr(attr)

    def handleFailedGetAttr(self, attr):
        """Called when getattr fails.  Default is to raise attribute error.

        >>> import pyRXPU
        >>> sample = '<breakfast><drink value="juice"/><food value="eggs"/><food value="bacon"/><drink value="coffee"/><food value="toast"/></breakfast>'
        >>> top = TagWrapper(pyRXPU.Parser().parse(sample))
        >>> top.tagName
        u'breakfast'
        >>> top.drink.value
        u'juice'
        >>> top.drink.quantity
        Traceback (most recent call last):
        ...
        AttributeError: "quantity" not found in attributes of drink tag or its children

        """
        #logger.debug("TagWrapper.handleFailedGetAttr('%s')" % attr)
        msg = '"%s" not found in attributes of %s tag or its children' % (attr, self.tagName)
        raise AttributeError(msg)

    def keys(self):
        "return list of valid keys"
        result = list(self._attrs.keys())
        for child in self._children:
            if not isinstance(child,strTypes):
                result.append(child[0])
        return result

    def __contains__(self,k):
        return k in list(self.keys())

    def __getitem__(self, idx):
        try:
            child = self._children[idx]
        except IndexError:
            raise IndexError('%s no index %s' % (self.__repr__(), repr(idx)))
        if isinstance(child,strTypes):
            return self.xmlEscape(child)
        else: return self.__class__(child,(self._children,idx))

    def _tagChildren(self):
        return [self.__class__(c) for c in self._children if not isinstance(c,strTypes)]

    def _namedChildren(self,name):
        """Used to select tags of a given name from
        a parent.

        >>> import pyRXPU
        >>> sample = '<breakfast><drink value="juice"/><food value="eggs"/><food value="bacon"/><drink value="coffee"/><food value="toast"/></breakfast>'
        >>> top = TagWrapper(pyRXPU.Parser().parse(sample))
        >>> top.tagName
        u'breakfast'
        >>> [x.value for x in top]
        [u'juice', u'eggs', u'bacon', u'coffee', u'toast']
        >>> [x.value for x in top._namedChildren("food")]
        [u'eggs', u'bacon', u'toast']
        """
        R = []
        aR = R.append
        for c in self:
            if isinstance(c,strTypes):
                if name is None: aR(c)
            elif name==c.tagName: aR(c)
        return R

    def _cxNamedChildren(self,name):
       """Used to select children index and tag for tags of a given name from a parent.

       >>> import pyRXPU
       >>> sample = '<breakfast><drink value="juice"/><food value="eggs"/><food value="bacon"/><drink value="coffee"/><food value="toast"/></breakfast>'
       >>> top = TagWrapper(pyRXPU.Parser().parse(sample))
       >>> top.tagName
       u'breakfast'
       >>> [(i,x.value) for i,x in top._cxiter()]
       [(0, u'juice'), (1, u'eggs'), (2, u'bacon'), (3, u'coffee'), (4, u'toast')]
       >>> [(i,x.value) for i,x in top._cxNamedChildren("food")]
       [(1, u'eggs'), (2, u'bacon'), (4, u'toast')]
       """
       R = []
       aR = R.append
       for i,c in self._cxiter():
           if isinstance(c,strTypes):
               if name is None: aR((i,c))
           elif name==c.tagName: aR((i,c))
       return R

    def getNamedChildren(self, name):
        """Used to select child tags of a given name from
        a parent.

        >>> import pyRXPU
        >>> sample = '<breakfast><drink value="juice"/><food value="eggs"/><food value="bacon"/><drink value="coffee"/><food value="toast"/></breakfast>'
        >>> top = TagWrapper(pyRXPU.Parser().parse(sample))
        >>> top.tagName
        u'breakfast'
        >>> [x.value for x in top]
        [u'juice', u'eggs', u'bacon', u'coffee', u'toast']
        >>> [x.value for x in top.getNamedChildren("food")]
        [u'eggs', u'bacon', u'toast']
        """
        R = []
        for child in self._children:
            if not isinstance(child,strTypes):
                tagName, attrs, children, spare = child
                if name==tagName:
                    R.append(self.__class__(child))
        return R

    def getChild(self, name):
        """Return first child of given name, or None."""
        children = self.getNamedChildren(name)
        if children:
            if len(children) > 1:
                # raise all kinds of hell, or just
                pass
            return children[0]

    def _namedNodes(self,name):
        R = []
        idx = 0
        while 1:
            try:
                c = self._children[idx]
            except IndexError:
                break
            if isinstance(c,strTypes) and name is None:
                c = self.xmlEscape(c)
                R.append(c)
            elif c[0]==name: R.append(c)
            idx = idx+1
        return R

    def _replaceNamedChildren(self,name,nodes,all=0):
        '''given some tuples use to populate equivalent nodes under here'''
        if type(nodes) is not type([]): nodes = [nodes]
        C = self._children
        if not nodes:
            i = -1
        else:
            for i in xrange(len(C)):
                c = C[i]
                if c[0]==name:
                    C[i] = nodes[0]
                    del nodes[0]
                    if not nodes: break
        if all:
            i = i+1
            while i<len(C):
                if C[i][0]==name: del C[i]
                else: i = i+1
            list(map(C.append,nodes))

        p = self._parent
        if p:
            t = p[0][p[1]]
            n,a,c,o = t
            t = isinstance(t,tuple) and (n,self._attrs,self._children,o) or [n,self._attrs,self._children,o]
            p[0][p[1]] = t

    def shallowClone(self,parent=None,kids=[]):
        if parent is None:
            parent = self._parent
        c = self.__class__((self.tagName,self._attrs.copy(),None,self._spare),parent)
        c._children = kids
        return c

    def removeChild(self,child):
        if callable(child):
            self._children[:] = [k for k in self._children if not child(k)]
        else:
            self._children[:] =  [k for k in self._children if child is not k]

    def _setAttr(self,**kw):
        self._attrs.update(kw)
        p = self._parent
        if p:
            t = p[0][p[1]]
            n,a,c,o = t
            t = isinstance(t,tuple) and (n,self._attrs,c,o) or [n,self._attrs,c,o]
            p[0][p[1]] = t

    @staticmethod
    def xmlEscape(a):
        if _XMLESCAPE: a = xmlEscape(a)
        return a

    def toTupleTree(self):
        return (self.tagName, self._attrs, self._children or None, self._spare)

class NonEscapingTagWrapper(TagWrapper):
    @staticmethod
    def xmlEscape(a):
        if isinstance(a,bytesT): return quotedBytes(a)
        return quotedUnicode(a)

class SilentTagWrapper(TagWrapper):
    """Does not complain when nonexistent leaf attributes accessed.
    Returns the default value which is an empty string (web-template friendly).

    >>> import pyRXPU
    >>> p = pyRXPU.Parser().parse("<document id='123'><body>Hello World</body></document>")
    >>> stw = SilentTagWrapper(p)
    >>> body = stw[0]
    >>> body.__class__.__name__   #does it create the right child types?
    'SilentTagWrapper'
    >>> body.tagName
    u'body'
    >>> str(body.href)   #try something nonexistent as it would appear in preppy
    ''
    >>> str(body.arm.hand.finger)  #recursive!
    ''
    """
    _default = ''

    def handleFailedGetAttr(self, attr):
        #logger.debug("SilentTagWrapper.handleFailedGetAttr('%s')" % attr)
        child = (attr,None,[self._default],None,)
        parent = (self.tagName,None,[],None,)
        return self.__class__(child, parent)

class _FakingIt(object):
    def __getattr__(self, attr):
        if not (attr.startswith('__') and attr.endswith('__')):
            return self.__class__(self._default) if self else self
        else:
            raise AttributeError('no such attribute %r' % attr)

    def __getitem__(self,x):
        try:
            return self.__class__.__mro__[2].__getitem__(self,x)
        except:
            return self.__getattr__(x)

    def __call__(self,*args,**kwds):
        return self.__class__(self._default) if self else self

if isPy3:
    class FakingStr(_FakingIt,bytes):
        _default = b''
        def __new__(cls,v):
            return str.__new__(FakingUni,v) if isinstance(v,str) else bytes.__new__(cls,v)

    class FakingUni(_FakingIt,str):
        _default = u''
        def __new__(cls,v):
            return bytes.__new__(FakingStr,v) if isinstance(v,bytes) else str.__new__(cls,v)
else:
    class FakingStr(_FakingIt,str):
        _default = b''
        def __new__(cls,v):
            return unicode.__new__(FakingUni,v) if isinstance(v,unicode) else str.__new__(cls,v)

    class FakingUni(_FakingIt,unicode):
        _default = u''
        def __new__(cls,v):
            return str.__new__(FakingStr,v) if isinstance(v,str) else unicode.__new__(cls,v)

class FakingTagWrapper(TagWrapper):
    '''
    >>> import pyRXPU
    >>> p = pyRXPU.Parser().parse("<document id='123'><body>Hello World</body></document>")
    >>> stw = FakingTagWrapper(p)
    >>> body = stw[0]
    >>> body.__class__.__name__   #does it create the right child types?
    'FakingTagWrapper'
    >>> body.tagName
    u'body'
    >>> str(body.href)   #try something nonexistent as it would appear in preppy
    ''
    >>> str(body.arm.hand.finger)  #recursive!
    ''
    >>> str(body)
    'Hello World'
    >>> stw[14].zzzz
    u''
    >>> stw.id
    u'123'
    >>> stw.id.bilbo
    u''
    >>> body = stw.body
    >>> body.__class__.__name__   #does it create the right child types?
    'FakingTagWrapper'
    >>> body.tagName
    u'body'
    >>> str(body.href)   #try something nonexistent as it would appear in preppy
    ''
    >>> str(body.arm.hand.finger)  #recursive!
    ''
    >>> str(body)
    'Hello World'
    >>> 'TRUE' if stw.A and stw.B else 'FALSE'
    'FALSE'
    >>> vehicle = stw.vehicle
    >>> 'TRUE' if vehicle.A and vehicle.B else 'FALSE'
    'FALSE'
    >>> 'TRUE' if stw.body or stw.B else 'FALSE'
    'TRUE'
    >>> 'TRUE' if stw.B or stw.body else 'FALSE'
    'TRUE'
    >>> vehicle.A(1)
    ''
    >>> stw._namedChildren('body')[0].bongo
    ''
    >>> stw._namedChildren('body')[:][0].bongo
    ''
    '''
    def handleFailedGetAttr(self, a):
        return ''

    def __getattr__(self, a):
        if not (a.startswith('__') and a.endswith('__')):
            v = TagWrapper.__getattr__(self,a)
            return FakingStr(v) if isinstance(v,strTypes) else v
        else:
            raise AttributeError('no such attribute %r' % a)

    def __getitem__(self, x):
        try:
            v = TagWrapper.__getitem__(self,x)
            return FakingStr(v) if isinstance(v,strTypes) else v
        except:
            return FakingStr(u'' if isUnicode(self.tagName) else '')

class MarkingTagWrapper(TagWrapper):
    """Returns a marker for non-existent leaf value.

    >>> import pyRXPU
    >>> p = pyRXPU.Parser().parse("<document id='123'><body>Hello World</body></document>")
    >>> stw = MarkingTagWrapper(p)
    >>> body = stw[0]
    >>> body.__class__.__name__   #does it create the right child types?
    'MarkingTagWrapper'
    >>> body.tagName
    u'body'
    >>> str(body.href)   #try something nonexistent
    '[[** href **]]'
    >>> str(body.arm.hand.finger)  #recursive, complains on leaf!
    '[[** finger **]]'
    """
    def handleFailedGetAttr(self, attr):
        #logger.debug("MarkingTagWrapper.handleFailedGetAttr('%s')" % attr)
        child = (attr,None,['[[** '+ attr +' **]]'],None,)#Marking
        parent = (self.tagName,None,[],None,)
        return self.__class__(child, parent)

def diffTrees(tree1, tree2, ancestry=''):
    "Returns a helpful description of the first difference found"

    (tagname1, attrs1, children1, stuff1) = tree1
    (tagname2, attrs2, children2, stuff2) = tree2

    if tagname1 != tagname2:
        return "Tag Names Differ: %s versus %s at %s" % (
            tagname1, tagname2, ancestry)

    elif attrs1 != attrs2:
        return "Attributes Differ: at %s" % ancestry

def compactDistro_eoCB(targets=(), dtdDirs=(), fs_eoCB=None):
    '''create an entity opening callback
    targets is a list of possible dtd basenames
    dtdDirs is a list of possible dtdDirs
    fs_eoCB is an alternate eoCB for when we're not compact
    '''
    from reportlab.lib.utils import isCompactDistro
    if isCompactDistro():
        def eoCB(s,targets=targets,dtdDirs=dtdDirs):
            from reportlab.lib.utils import open_and_read, rl_isfile
            bn = os.path.basename(s)
            if bn in targets:
                for d in dtdDirs:
                    fn = os.path.join(d,bn)
                    if rl_isfile(fn): return fn, open_and_read(fn,'t')
            return s
    else:
        eoCB = fs_eoCB
    return eoCB

def xml2rad(xml, validating=1, eoCB=None):
    '''convert xml to radxml form'''
    if validating:
        from reportlab.lib.utils import isCompactDistro, open_and_read
        if not eoCB and isCompactDistro():
            eoCB = lambda x, open_and_read=open_and_read: (x, open_and_read(x))
        import pyRXPU
        rad = pyRXPU.Parser().parse(xml,eoCB=eoCB)
    else:
        from reportlab.lib import rparsexml
        rad = rparsexml.parsexml0(xml)[0][2][0]
    return rad

def xml2doctree(xml, validating=1, eoCB=None):
    return TagWrapper(xml2rad(xml,validating, eoCB=None))

def applyDocType(source, rootElement, dtdName):
    """This will add or replace a DOCTYPE element at the top
    of the file. It can occur in the first or second line."""

    newDocType = '<!DOCTYPE %s SYSTEM "%s">' % (rootElement, dtdName)

    startDocType = source.find('<!DOCTYPE')
    if startDocType >= 0:
        #formally it ends with the first '>' not in quotes; I'm not that picky.
        endDocType = source.find('>', startDocType+1) + 1
        modified = source[0:startDocType] + newDocType + source[endDocType:]

    else:
        #it might still start with a declaration
        if source.strip().startswith('<?xml'):
            endDecl = source.find('?>') + 2
            xmlDecl = source[0:endDecl]
            modified = xmlDecl + '\n' + newDocType + '\n' + source[endDecl:]
        else:
            modified = newDocType + '\n' + source
    return modified.strip()

def validateXhtml(source, rootElement="html", wrapIfNeeded=True):
    """Validates against canned DTD and returns the tuple-tree, or an exception.

    It uses a canned copy of the standard in rlextra/dtd.
    You don't have to supply a whole document; if you want to check
    that the content is a valid paragraph, supply 'p' as rootElement.

    By default it's a little bit forgiving and will add the rootElement
    if needed at the start or the finish.  This is useful with tinyMCE
    text.  If you turn off wrapIfNeeded, it will assume your tag is there.

    >>> t = validateXhtml('''<html><head><title>hello</title></head><body></body></html>''')
    >>> t = validateXhtml('''<html><head this="unexpected"><title>hello</title></head><body></body></html>''') #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    error: Error: Undeclared attribute this for element head
     in unnamed entity at line 2 char 17 of [unknown]
    Undeclared attribute this for element head
    Parse Failed!
    <BLANKLINE>
    >>> # now for some intra-paragraph stuff - you can validate any tag
    >>> t = validateXhtml('''<p>Normal<i>text</i> here</p>''', rootElement='p')
    >>> t = validateXhtml('''<p>Normal<i>text</i> here, but no <p>paras</p>!</p>''', rootElement='p') #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    error: Error: Content model for p does not allow element p here
     in unnamed entity at line 2 char 37 of [unknown]
    Content model for p does not allow element p here
    Parse Failed!
    <BLANKLINE>

    #check it can supply the missing p tag with intra-paragraph content, at start or end
    #as one can get from tinyMCE, with wrapIfNeeded.
    >>> t = validateXhtml('''Normal<i>text</i> here''', rootElement='p')
    >>> t = validateXhtml('''Missing a lead p.</p>''', rootElement='p')
    >>> t = validateXhtml('''<p>Missing a trailing p.''', rootElement='p')

    """
    if wrapIfNeeded:
        #we can cope with missing root element at beginning and end.
        #but if they supplied a doctype or xml declaration, we assume it's
        #complete.

        source = source.strip()
        if source.startswith('<!DOCTYPE') or source.startswith('<?'):
            pass
        else:
            if not source.startswith("<" + rootElement):
                source = "<%s>%s" % (rootElement, source)
            if not source.endswith(rootElement + ">"):
                source = "%s</%s>" % (source, rootElement)

    source = applyDocType(source.strip(), rootElement,'xhtml1-strict.dtd')
    import pyRXPU
    from rlextra.radxml import xhtml
    p = pyRXPU.Parser(eoCB = xhtml.openEntity)
    #try:
    tree = p.parse(source)
    #except:
    #ought to raise an exception with the offending text
    return tree

def validateXhtmlDocument(docText):
    """Parse, with validation, an XHTML 1.0 Strict document and return pyRXPU tuple tree.

    Raises pyRXPU.error on failure.

    >>> import pyRXPU

    >>> r = validateXhtmlDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-strict.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p></p></body>
    ... </html>
    ... ''')
    >>> r = validateXhtmlDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-strict.dtd">
    ... <boo></boo>
    ... ''')
    ... #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    error: Error: Start tag for undeclared element boo
     in unnamed entity at line 3 char 5 of [unknown]
    Start tag for undeclared element boo
    Parse Failed!
    <BLANKLINE>

    XHTML Transitional attributes like bgcolor are NOT OK:

    >>> r = validateXhtmlDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-strict.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p><img border="1"></p></body>
    ... </html>
    ... ''')
    ... #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    error: Error: Undeclared attribute border for element img
     in unnamed entity at line 5 char 21 of [unknown]
    Undeclared attribute border for element img
    Parse Failed!
    <BLANKLINE>

    It's an error to supply a document that's declared to be XHTML transitional:

    >>> try:
    ...     r = validateXhtmlDocument('''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-transitional.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p></p></body>
    ... </html>
    ... ''')
    ... except pyRXPU.error:
    ...     pass
    ... else:
    ...     print("expected pyRXPU.error")
    """
    import pyRXPU
    from rlextra.radxml import xhtml
    p = pyRXPU.Parser(eoCB=xhtml.openEntity)
    return p.parse(docText)

def validateXhtmlTransitionalDocument(docText):
    """Parse, with validation, an XHTML 1.0 Transitional document and return pyRXPU tuple tree.

    Raises pyRXPU.error on failure.

    >>> import pyRXPU

    >>> r = validateXhtmlTransitionalDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-transitional.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p></p></body>
    ... </html>
    ... ''')
    >>> r = validateXhtmlTransitionalDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-transitional.dtd">
    ... <boo></boo>
    ... ''')
    ... #doctest: +IGNORE_EXCEPTION_DETAIL
    Traceback (most recent call last):
    error: Error: Start tag for undeclared element boo
     in unnamed entity at line 3 char 5 of [unknown]
    Start tag for undeclared element boo
    Parse Failed!
    <BLANKLINE>

    XHTML Transitional attributes like border are OK:

    >>> r = validateXhtmlTransitionalDocument(b'''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-transitional.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p><img src="blah" alt="blah" border="1"></img></p></body>
    ... </html>
    ... ''')

    It's an error to supply a document that's declared to be XHTML strict:

    >>> try:
    ...     r = validateXhtmlTransitionalDocument('''<?xml version="1.0" encoding="UTF-8"?>
    ... <!DOCTYPE html SYSTEM "xhtml1-strict.dtd">
    ... <html>
    ... <head><title>Title</title></head>
    ... <body><p></p></body>
    ... </html>
    ... ''')
    ... except pyRXPU.error:
    ...     pass
    ... else:
    ...     print("expected pyRXPU.error")
    """
    import pyRXPU
    from rlextra.radxml import xhtml
    p = pyRXPU.Parser(eoCB=xhtml.openEntityTransitional)
    return p.parse(docText)

import xml.etree.cElementTree as etree
import io
def etreeParse(src, stripWhitespace=False):
    """Compatibility hook to make use of etree.

    This will use an elementtree-based parser and
    generate the ReportLab-style tuple tree. It
    should help us get rid of xmllib.

    """
    stuff = etree.parse(io.StringIO(src))
    root = stuff.getroot()
    return etreeConvertNode(root, stripWhitespace)

def etreeConvertNode(node, stripWhitespace=False):
    out = {'tagName': node.tag}
    out.update(node.attrib)

    children = []
    if node.text:
        text = node.text
        if stripWhitespace:
            text = text.strip()
        if text:
            children.append(text)

    for child in node:
        children.append(etreeConvertNode(child, stripWhitespace))

    if node.tail:
        text = node.tail
        if stripWhitespace:
            text = text.strip()
        if text:
            children.append(text)
 

    return (node.tag, node.attrib.copy(), children, None)

def test(gentests=False):
    import doctest, sys
    if gentests:
        R = [].append
    if sys.version_info[0]>2:
        from rlextra.radxml import xmlutils as mod
        class Py23DocChecker(doctest.OutputChecker):
            def check_output(self, want, got, optionflags):
                want = re.sub("u'(.*?)'", "'\\1'", want)
                want = re.sub('u"(.*?)"', '"\\1"', want)
                return doctest.OutputChecker.check_output(self, want, got, optionflags)
        checker = Py23DocChecker()
        if gentests:
            R(doctest.DocTestSuite(checker=checker))
        else:
            finder = doctest.DocTestFinder(exclude_empty=False)
            runner = doctest.DocTestRunner(checker=checker)
            for test in finder.find(mod, mod.__name__, globs=None, extraglobs=None):
                runner.run(test)
            runner.summarize()
    elif gentests:
        R(doctest.DocTestSuite())
    else:
        doctest.testmod()
    return R.__self__

if __name__=='__main__':
    test()
