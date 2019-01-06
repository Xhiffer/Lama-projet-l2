# attempt to make a tuple tree from Expat.
# This should be in most Pythons.
# In weird ones like Java or .NET, we should use
# whatever the OS gives us
import time
from xml.parsers import expat

class ExpatTreeParser:
    """Make a tuple tree using Expat"""
    def __init__(self):
        self._parser = expat.ParserCreate()
        self._parser.StartElementHandler = self.handle_start
        self._parser.EndElementHandler = self.handle_end
        self._parser.CharacterDataHandler = self.handle_data

    def reset(self):
        self._stack = [(None,None,[],None)]
        self._stack_append = self._stack.append
        self._hdc = 0   #count calls to handle_data

    def parseText(self, text):
        self.reset()
        self._parser.Parse(text)
        top = self._stack[0][2]
        if top: return top[0]

    def handle_start(self, name, attrs):
        tag = (name, attrs or None, [], None)
        parent = self._stack[-1]
        parent[2].append(tag)  #build the tree
        self._stack_append(tag)
        self._chdc = self._hdc
        #self._cbi = self._parser.CurrentByteIndex, self._parser.CurrentLineNumber, self._parser.CurrentColumnNumber

    def handle_end(self, name):
        top = self._stack.pop()
        if self._hdc==self._chdc:
            self._stack[-1][2][-1] = top[:2]+(None,)+top[3:]
            #print self._cbi,self._parser.CurrentByteIndex, self._parser.CurrentLineNumber, self._parser.CurrentColumnNumber

    def handle_data(self, data):
        #wrinkle: concat adjacent text nodes. todo
        self._hdc += 1
        contentList = self._stack[-1][2]
        if not contentList:
            contentList.append(data)
        elif not isinstance(contentList[-1],tuple):
            #last one is a string, concat
            contentList[-1] = contentList[-1] + data
        else:
            contentList.append(data)

sample1  = """<?xml version="1.0"?>
<parent id="top">
  <child1 name="paul">Text goes here</child1>
  <child2 name="fred">More text</child2>
  <child3 name="bill">&amp; more &amp; more...</child3>
  <child3 name="sam">Trademark &#8482;</child3>
  <child3><![CDATA[Lethal naked stuff: <, & and >]]></child3>
  <closed id="my id"/>
  <just_empty id="another id"></just_empty>
</parent>"""



if __name__=='__main__':
    import sys
    from pprint import pprint as pp
    if len(sys.argv) < 2:
        print('usage: expattree.py myfile.xml')
        print('Example follows....')
        xmlText = sample1
        small = 1
    else:
        filename = sys.argv[1]
        xmlText = open(filename, 'r').read()
        small = 0

    print('Try 1: with expat based treebuilder')
    p = ExpatTreeParser()
    start = time.clock()
    tree = p.parseText(xmlText)
    finish = time.clock()
    print('parsed %d bytes in %0.4f seconds' % (len(xmlText), finish-start))
    if small:
        print('expat tree:')
        pp(tree)
    print('Try 2: with pyRXP based treebuilder')

    try:
        import  pyRXPU
    except ImportError:
        sys.exit()
    print()
    #try comparison
    p = pyRXPU.Parser()
    start = time.clock()
    tree2 = p.parse(xmlText)
    finish = time.clock()
    print('parsed %d bytes in %0.4f seconds' % (len(xmlText), finish-start))
    if small:
        print('pyRXP tree:')
        pp(tree2)

    if tree == tree2:
        print('Exact match!')
    else:
        print('trees differ!')
        if not small:
            pp(tree,stream=open('/tmp/expat_tree.txt','w'))
            pp(tree2,stream=open('/tmp/pyrxp_tree.txt','w'))
