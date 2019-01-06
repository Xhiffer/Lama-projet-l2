#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/ers/doclet.py
__version__='3.3.0'

"""Doclets allow chunks of content to be reused acrass projects.


A doclet is a smart object which can render itself in the PDF
and HTML worlds. 

"""
# a trivial parser used for completing the doclets
# in an HTML context
try:
    from html.parser import HTMLParser
except:
    from sgmllib import SGMLParser
    HTMLParser = SGMLParser

# used in making the example doclet.
from reportlab.platypus import Paragraph
from reportlab.platypus.tables import Table, TableStyle
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib import colors

from rlextra.radxml.xmlutils import TagWrapper
from xml.sax.saxutils import escape
from rlextra.radxml.xmlmap import MapNode, MapController
class Doclet:
    def setData(self, data):
        """Called by dynamic RML or preprocessor, data hook.

        Doclets can be parameterised and fetch data and this gives them the
        chance to do it."""        
        pass
    
    def asFlowable(self):
        "Return a flowable or list of flowables"

        #the base class does enough to say 'here is a doclet...'
        sty = ParagraphStyle(
                                name='obvious',
                                fontName='Helvetica',
                                fontSize=10,
                                leading=12,
                                backColor=colors.yellow
                                )
        
        return Paragraph('Doclet class: %s' % self.__class__.__name__, style=sty)


    def asHTML(self, look=None):
        return '<p>This is a Doclet of class %s</p>' % self.__class__.__name__

##  To be discussed:
##    def getPdfStyles(self, look=None):
##         "Return a dictionary mapping style names to styles which are used"
##         return {}
##
##    def htmlNeedsExtraFiles(self):
##        "Does it need to create/reference any bitmap files?"
##        return 0
##
##    def getHtmlStyles(self, look=None):
##         "Return a dictionary mapping style names to CSS styles used"
##         return {}






class TestReverseDoclet(Doclet):
    """Reverses the string it was given and displays as table"""

    defaultParaStyle = ParagraphStyle(
                            name='obvious',
                            fontName='Helvetica',
                            fontSize=10,
                            leading=12,
                            backColor=colors.yellow
                            )

    defaultTableStyle = TableStyle([
         ('GRID',(0,0),(-1,-1),2,colors.grey),
         ('BACKGROUND',(0,0),(-1,0),colors.palegreen),
         ('SPAN',(0,0),(-1,0)),
         ('FONT',(0,0),(-1,-1), 'Helvetica',10,12),
         ('FONT',(1,1),(-1,-1), 'Helvetica-Bold',10,12)
         ])

    def __init__(self):
        #may not be needed but let's initialize with dummy data
        # so it can be tested as it.
        self.text = 'hello world'
        self.reversed = 'dlrow olleh'

                  
    def setData(self, data):
        self.text = data

        #reverse it
        l = list(self.text)
        l.reverse()

        self.reversed = ''.join(l)

    def asHTML(self, look=None):
        return """
        <table border>
            <tr><th colspan="2" style="background:pink">Reverse Doclet Example</th></tr>
            <tr><td>Normal:</td><td>%s</td></tr>
            <tr><td>Reversed:</td><td>%s</td></tr>
        </table>
        """ % (self.text, self.reversed)

    def asFlowable(self):
    
        tableData = [
            ["Reverse Doclet Example",""],
            ["Normal:", self.text],
            ["Reversed:", self.reversed]
            ]
        t = Table(tableData, style=self.defaultTableStyle, colWidths=(100,100))
        
        return t        


##class InspectorDoclet(Doclet):
##    """Little table showing info about the data object"""
##
##    def setData(self, data):
##        self.data = data
##
##        self.typeStr = data.__class__.__name__
##        
##        self.attrs = attrs
##
##    def asHTML(self, look=None):
##        out = ["<table border>\n" +
##        '    <tr><th colspan="2" style="background:pink">%s</th></tr>' % self.title]
##        if self.attrs:
##            for (key, value) in self.attrs:
##                out.append("\n    <tr><td>%s</td><td><b>%s</b></td></tr>" % (key, value))
##        else:
##            out.append('\n    <tr><td colspan="2"><i>No attributes supplied</i></td></tr>')
##        out.append("\n</table>")
##        return ''.join(out)
        


class DocletToHtmlMapNode(MapNode):
    """This is a MapNode which expands doclets to HTML"""

    def __init__(self):
         MapNode.__init__(self, None, None, None)

    def translate(self, nodetuple, controller, overrides, containerdict=None):
        (tagName, attrs, children, stuff) = nodetuple
        if '__doclet__' in attrs:
            theDoclet = attrs['__doclet__']
            return theDoclet.asHTML()
        else:
            return ''

class DocletToHtmlMapper(MapController):
    """Top level map controller which expands doclet tags"""
    def __init__(self, topLevelSubstitution = "%s", naive=0, eoCB=None):
        MapController.__init__(self, topLevelSubstitution, naive, eoCB)
        self['doclet'] = DocletToHtmlMapNode()

        



def _makeXMLTag(name,attrs,contents,inner=1):
    if name == 'doclet':
        return attrs['__doclet__'].asHTML()
    else:
        T = []
        a = T.append
        if inner:
            a('\n<%s' % name)
            for k,v in list(attrs.items()):
                a('%s="%s"' % (k,escape(v)))
            T[:] = [' '.join(T)]
        if contents in ([],None):
            if inner: a('/>')
        else:
            if inner: a('>')
            for c in contents:
                a(createHTML(c,inner=1))
            if inner: a('</%s>' % name)
        return ''.join(T)

def createHTML(tag,inner=0):
    '''Takes a TagWrapper and converts to XML,
    if inner=1 then the outer tag is made explicit'''
    R = []
    r = R.append
    if isinstance(tag,(list,tuple)):
        r(_makeXMLTag(tag[0],tag[1] or {},tag[2]))
    elif isinstance(tag,TagWrapper):
        r(_makeXMLTag(tag.tagName,tag._attrs,tag._children,inner=inner))
    else:
        #r(escape(tag))
        r(tag)
    return ''.join(R)




class DocletParser(HTMLParser):
    """Passes through an HTML or XML document, expands doclets,
    and returns final string.  Ideally, it should affect nothing
    but the doclets.  In practice this depends on the python parser,
    and we'll settle for 'no serious change'.

    """

    def asDict(self, attrs):
        d = {}
        for (k,v) in attrs:
            d[k] = v
        return d

    def process(self, source, docletMap, nameSpace, tempDir):
        "Do it all for me"
        self.reset()

        self._docletMap = docletMap
        self._nameSpace = nameSpace
        self._output = []
        
        self.feed(source)
        self.close()

        return self.getOutput()
    

    def getOutput(self):
        return ''.join(self._output)

    def handle_starttag(self, tag, attrs):
        #is it a special doclet?
        if tag in self._docletMap:
            self.handle_start_doclet(tag, attrs)
        else:
            out = ['<%s' % tag]
            for (k, v) in attrs:
                out.append('%s="%s"' % (k, v))
            out.append('>')
            self._output.append(' '.join(out))

    def handle_endtag(self, tag):
        if tag in self._docletMap:
            self.handle_end_doclet(tag)
        else:
            self._output.append("</%s>" % tag)

    def handle_data(self, data):
        #assume the data was just parsed, cdata not handled yet.
        self._output.append(data)

    def handle_charref(self, name):
        self._output.append(name)

    def handle_entityref(self, name):
        self._output.append(name)

    def handle_comment(self, data):
        self._output.append('<!--%s-->' % data)
        
    def handle_decl(self, decl):
        self._output.append('<!%s>' % decl)

    def handle_pi(self, data):
        self._output.append('<?%s>' % data)


    def handle_start_doclet(self, tag, attrs):
        #attributes override namespace and go into
        # dict passed to setData
        print('doclet %s, attrs=%s' % (tag, str(attrs)))
        if attrs:
            ns = self._nameSpace.copy()
            for (key, value) in attrs:
                ns[key] = value
        else:
            ns = self._nameSpace

        #create the thing
        klass = self._docletMap[tag]
        objekt = klass()

        #let it pull data
        objekt.setData(tag, self.asDict(attrs), ns)

        #make the HTML
        html = objekt.asHTML()

        self._output.append(html)

    def handle_end_doclet(self, tag):
        pass
    


def testRml():
    from reportlab.platypus.doctemplate import SimpleDocTemplate
    from reportlab.platypus.flowables import Spacer
    from reportlab.lib.randomtext import randomText

    templ = SimpleDocTemplate('doclet_output.pdf')

    #need a style
    story = []
    normal = ParagraphStyle('normal')
    normal.firstLineIndent = 18
    normal.spaceBefore = 6

    para = Paragraph("Test of doclets.  You should see a little table with a reversed word.", normal)
    story.append(para)

    story.append(Spacer(36,36))
                 
    theDoclet = TestReverseDoclet()
    story.append(theDoclet.asFlowable())
    
    for i in range(5):
        para = Paragraph(randomText(), normal)
        story.append(para)



    templ.build(story)    

    print('saved doclet_output.pdf')

    
if __name__=='__main__':
    #make a platypus doc and an HTML one with the
    #test objects
    testRml()
