#xmlobjects.py
"""This helps you map XML to your own objects, and is an alternative
to DOM.  Consider the XML snippet below:

<invoice net="100.00" vat="17.50" gross="100.00" serial="12345">
  <customer id="FBLOGGS">Fred Bloggs, 33 Mercer Road</customer>
  <lines>
      <line amount="50">Basic Package</line>
      <line amount="30">Add-on Widgets</line>
      <line amount="50">On-site handholding</line>
  </lines>
</invoice>

The first stage is to slurp the XML as quickly as possible
into a tuple structure.  This can be done very quickly
by rparsexml2 (pure Python) or pexparse.py (uses pyexpat).
Each tag is represented as a tuple
 (tagName, attributes, children)
"attributes" may be None to save memory, but "children" is
always a list - possibly empty, possibly containing more
tags.  This is not intended for direct use, but you can
just about read it or view it with pprint.

The next stage is to automate mapping into your own
class hierarchy.  We provide a XMLNode class with some
stuff to make it easy to move to/from XML.  You may
inherit from this.  It uses no __init__ methods and
its attributes and methods begin with 'xml', so
it is unlikely to clash with your own class behaviour.

There is an 'easy' and a 'hard' way to control the mapping.
The 'easy' way is to provide a class attribute which
defines the XML attributes, an input-processing function
and an output-processing function for each:

class SampleInvoice(XMLNode):
    xmlAttrMap = {
        'net': (float, str),
        'vat': (float, str),
        'gross': (float, str),
        'serial': (int, str)
        }

'float' and 'str' are functions, and may be built-in
or your own.  float/int will be called on the XML data
when the Node is created, and str when writing back
to XML.  

(should we add default values, or rule that the user
sets them up in __init__?)

The 'hard' way is to override some methods of XMLNode:
    def xmlSetName(self, tagName):
    def xmlSetAttrs(self, attrs):
    def xmlSetChildren(self, childNodes):
    def xmlGetName(self):
    def xmlGetAttrs(self):
    def xmlGetChildren(self):
note that the default implementattion of xmlSetAttrs
and xmlGetAttrs use the xmlAttrMap. 

A common task might be to handle the children
intelligently; we might want all <line> nodes
to be added to a 'self.lines' attribute and
all newlines/whitespace ignored, instead of
adding them all to self.children.
"""
#use either of the parsers below.
from reportlab.lib import rparsexml

def identity(arg):
    return arg

class XMLNodeInterface:
    """Abstract base class defining the interface for nodes"""
    def xmlSetName(self, tagName):
        pass
    def xmlSetAttrs(self, attrs):
        pass
    def xmlSetChildren(self, childNodes):
        pass
    def xmlGetName(self):
        return "XMLNodeInterface"
    def xmlGetAttrs(self):
        return {}
    def xmlGetChildren(self):
        return []

class XMLNode(XMLNodeInterface):
    xmlAttrMap = {}
    def __repr__(self):
        return '<Node "%s">' % self.xmlGetName()
    
    def xmlSetName(self, tagName):
        self.tagName = tagName

    def xmlSetAttrs(self, attrs):
        """Set attributes one at a time, applying
        conversion function if one exists."""
        for (key, value) in list(attrs.items()):
            try:
                f = self.xmlAttrMap[key][0]
            except KeyError:
                f = identity
            setattr(self, key, f(value))
        
    def xmlSetChildren(self, childNodes):
        self.children = childNodes

    def xmlGetName(self):
        return self.tagName

    def xmlGetAttrs(self):
        d = self.__dict__.copy()
        del d['tagName']
        del d['children']
        return d

    def xmlGetChildren(self):
        return self.children

    def toXML(self):
        """Default way to write out XML based on the Get methods.
        Need some options to trim or add whitespace."""
        tagName = self.xmlGetName()
        s = '<%s' % tagName
        for (key, value) in list(self.xmlGetAttrs().items()):
            s = s + ' %s="%s"' % (key, value)
        s = s + '>'
        for child in self.xmlGetChildren():
            if isinstance(child,str):
                s = s + child
            else:
                s = s + child.toXML()
        s = s + '</%s>' % tagName
        return s
    
def treeToObjects(tree, classMap={}):
    #returns either a single node or
    #a list of nodes
    (tagName, attrs, children) = tree[0:3]
    try:
        klass = classMap[tagName]
    except KeyError:
        klass = XMLNode
    obj = klass()
    obj.xmlSetName(tagName)
    if attrs:
        obj.xmlSetAttrs(attrs)
    childNodes = []
    for child in children:
        if isinstance(child,str):
            childNodes.append(child)
        else:
            node = treeToObjects(child, classMap)
            childNodes.append(node)
    obj.xmlSetChildren(childNodes)
    return obj

def parse(rawdata, classMap={}):
    tree = treeToObjects(rparsexml.parsexml(rawdata),classMap)
    #get rid of empty top-level nodes
    result = tree.children
    if len(result)==1:
        return result[0]
    else:
        return result

sample = """<invoice net="100.00" vat="17.50" gross="100.00" serial="12345">
  <customer id="FBLOGGS">Fred Bloggs, 33 Mercer Road</customer>
  <lines>
      <line amount="50">Basic Package</line>
      <line amount="30">Add-on Widgets</line>
      <line amount="50">On-site handholding</line>
  </lines>
</invoice>"""

class SampleInvoice(XMLNode):
    xmlAttrMap = {
        'net': (float, str),
        'vat': (float, str),
        'gross': (float, str),
        'serial': (int, str)
        }

sampleClassMap={'invoice':SampleInvoice}

def test():
    print(parse(sample, sampleClassMap).toXML())
    
if __name__=='__main__':
    import sys
    if len(sys.argv) == 2:
        import time
        data = open(sys.argv[1]).read()
        t0 = time.time()
        #tuples = pexparse.parse(data)
        tuples = rparsexml.parsexml(data)
        t1 = time.time()
        print('parsed %s to tuples in %0.3f seconds' % (sys.argv[1], t1-t0))
        objects = treeToObjects(tuples)
        t2 = time.time()
        print('mapped %s to objects in %0.3f seconds' % (sys.argv[1], t2-t1))
        print('total time %0.3f' % (t2-t0))
    else:        
        test()
    
