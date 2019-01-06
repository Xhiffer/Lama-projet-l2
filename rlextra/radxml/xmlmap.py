"""map xml using into other formats.

A MapController maps one XML format to another by recursive tag
translation.

BASIC USAGE

In basic usage initialize a Map Controller

    M = MapController()

and assign substitution strings or MapNodes for each tag.

Then process text using

    translatedtext = M.process(originaltext)

There will be errors if the xml in originaltext do not
match the assigned substitution strings or MapNodes for M.

TOP LEVEL SUBSTITUTION:

Every MapController must have a top level substitution which
defines a substitution location for "%(__content__)s", for
example as in

    M[''] = ''' <html>
         %(__content__)s
         </BODY>
         </html>
         '''

Here the empty tag '' signifies the top level.  In this particular
example the start of the <BODY> tag might be introduced in the translation
of another tag (like <DOCUMENTTITLE>).

SUBSTITUTION STRINGS:

You can either assign a substitution string to a tag name (for
tags with content) or assign a MapNode for tags which either do
not have content or require other special handling (such as
attribute defaults and transforms).

FOR TAGS WITH CONTENT, you can directly assign a string (which
internally is converted into a MapNode), for example

    M["H1"] = "<br><br><font size=+3><b>%(__content__)s</b></font><br>"

In this case the H1 tag has content (<H1>this is the content</H1>) but
no attributes that effect the translation.  Note that the marker
"%(__content__)s" indicates the location of the recursively translated
content.
    <H1>This is the content</H1>
translates to
    <br><br><font size=+3><b>This is the content</b></font><br>

FOR TAGS WITHOUT CONTENT or which require special handling assign
an explicit MapNode

    M["AUTHOR"] = MapNode(None, "<em>Aaron Watters</em>")

the AUTHOR tag has no content and no attributes that effect translation.
    <AUTHOR/>
translates to
    <em>Aaron Watters</em>

CONTAINED TAGS ARE RECURSIVELY TRANSLATED.  Using the translations
declared above
    <H1><AUTHOR/></H1>
becomes
    <br><br><font size=+3><b><em>Aaron Watters</em></b></font><br>

FOR TAGS WITH ATTRIBUTES include the appropriate attributes in the substition
string, as required.  For example,

    M["RETIRED"] = "<em>%(TITLE)s</em> <b>%(__content__)s</b> <em>Emeritas</em>"

The RETIRED tag has content and one attribute (TITLE) which is
required and effects translation.
    <RETIRED TITLE="Dr.">Carl Fungus</RETIRED>
becomes
    <em>Dr.</em> <b>Carl Fungus</b> <em>Emeritas</em>

For

    M["EXCLAMATION"] = "<FONT COLOR="RED"><B>%(TEXT)</B>, <EM>%(RECIPIENT)s</EM></FONT>"

EXCLAMATION has no content and two attributes (TEXT and RECIPIENT) which are required
and effect formatting.
    <EXCLAMATION TEXT="Holy rusty metal" RECIPIENT="Batman"/>
becomes
    <FONT COLOR="RED"><B>Holy rusty metal</B>, <EM>Batman</EM></FONT>

ATTRIBUTE DEFAULTS can be assigned using a MapNode assigned to a tag.
For example an alternate RETIRED tag might assign "Dr." as the default
value of Title.

    R = MapNode("<em>%(TITLE)s</em> <b>%(__content__)s</b> <em>Emeritas</em>")
    R.default["TITLE"] = "Dr."
    M["RETIRED"] =  R

Then using AUTHOR and RETIRED
    <RETIRED><AUTHOR/></RETIRED>
becomes
    <em>Dr.</em> <b><em>Aaron Watters</em></b> <em>Emeritas</em>
(Note the default "Dr." substitution).  I wish ;(.

ATTRIBUTE TRANSFORMS can be assigned using a MapNode.  For
example to upcase the titles of all retirees:

    R = MapNode("<em>%(TITLE)s</em> <b>%(__content__)s</b> <em>Emeritas</em>")
    R.addTransform(TITLE, str.upper)
    M["RETIRED"] =  R

Then
    <RETIRED TITLE="Dr.">Carl Fungus</RETIRED>
becomes
    <em>DR.</em> <b>Carl Fungus</b> <em>Emeritas</em>
The MapNode.transformContent(transform) will perform a transformation
on the recursively generated content of a tag (be careful when using
this one!)

MapNodes can alter the translation definitions for tags encountered
in their content.  For example

    M["Title"] = "<H1>%(__content__)s</H1>"
    ...
    C = MapNode("<hr>Chapter<hr> %(__content__)s")
    C["Title"] = "<H3>%(__content__)s</H3>"
    M["Chapter"] = C

Then a title outside of the Chapter context defaults to H1 but
a title inside a Chapter context defaults to H3.

"TAG NAME" OF None provides a "default" substitution
to apply to unknown tags, as in

    M[None] = "" # erase unknown tags
    M[None] = "#(__content__)s" # echo content for unknown tags

A substitution for a parent can refer to a substitution for a child

    # ref to %(TITLE.__content__)s refers to the title of the play (not act or scene)
    M["PLAY"] = ''' <html><head><title>%(TITLE.__content__)s</title></head><BODY>
                <CENTER><H1><FONT FACE="Arial">%(PLAY.TITLE.__content__)s</FONT></H1></CENTER>
         %(__content__)s
         <BODY>
         </html>
         '''

Any substitution can also refer to a "dotted path" to a content in the tree,
but it will get the last one if there is more than one match:

    M["ACT"]["TITLE"] = "<CENTER>%(PLAY.TITLE.__content__)s <H2>%(__content__)s</H2></CENTER>"

Here the top level element is "PLAY".  All "paths" must start at the top level element.

When "non local" uses of an elements __content__ are in use it is likely that the substitution
for the element itself will "vanish"

    M["TITLE"] = "" # __content__ used in top level (element vanishes)

__attrs__ entry allows for special handling of attributes
from rlextra.radxml.xmlmap import *
M=MapController()
M['']='%(__content__)s'
M['b']=MapNode('<B%(__attrs__)s>%(__content__)s</B>')
M['a']='<A>%(__content__)s</A>'

def bAttrsFunc(name,value):
    if name=='ZZ':
        return '--HACKED %s: %s' % (name,value)
    elif name=='x':
        return '--REVERSED %s: %s' %(name,''.join(reversed([x for x in value])))
    return value

M['b'].addTransform('__attrs__',AttrsFilter(rename=dict(z='ZZ'),remove=['y'],valueFunc=bAttrsFunc))
print M.process('<a>a contents 0<b z="30" y=\'"quoted"\' x="forward" w="leave alone">b content</b>a contents 1</a>')

"""
#" for emacs
# SET TO RUN HAMLET IN TEST SUITE
from __future__ import unicode_literals
from reportlab import ascii
DOHAMLET = 1
from reportlab.lib.utils import strTypes, asUnicode, asUnicodeEx, isPy3

class MapController:
    """Top level controller"""
    joinSeparator = ""

    def __init__(self, topLevelSubstitution = "%s", naive=0, eoCB=None, parseOpts={}):
        self.naive = naive # use nonvalidating parser if naive set
        self.topLevelSubstitution = topLevelSubstitution
        self.topDict = {}
        self.nodemappers = {None: None} # default
        self.eoCB = eoCB
        self._parseOpts = parseOpts
        self.preserve = PreserveNode()

    def __setitem__(self, item, value):
        if isinstance(value,strTypes):
            # very simple case, no defaults, no empty case
            value = MapNode(asUnicode(value))
        if isinstance(item,strTypes):
            item = asUnicode(item)
        self.nodemappers[item] = value

    def __getitem__(self, item):
        return self.nodemappers[item]

    def process(self, input, isTupleTree=False):
        if not isTupleTree:
            if self.naive:
                from reportlab.lib.rparsexml import parsexmlSimple as parsexml
            else:
                from reportlab.lib.rparsexml import parsexml
            elts = parsexml(input,eoCB=self.eoCB,parseOpts=self._parseOpts)
        else:
            elts = input
        return self.processParsed(elts)

    def processParsed(self, elts): # added to allow messing with the parsed input if needed
        D = self.topDict = {}
        D["__prefix__"] = ""
        elts = self.clean_elts(elts)
        textout = self.processContent(elts, top_level=1)
        T = asUnicodeEx(textout)
        result = self.topLevelSubstitution % T
        # clean out the topDict
        for k in list(D.keys()):
            del D[k] # possible self reference
        self.topDict = {}
        return result

    def processContent(self, elts, overrides=None, containerdict=None, top_level=1):
        if containerdict is None:
            containerdict = self.topDict
        if overrides is None:
            overrides = {} # no overrides yet
        if isinstance(elts,strTypes):
            return self.processString(asUnicode(elts))
        if isinstance(elts,tuple):
            return self.processTuple(elts, overrides, containerdict)
        else:
            L = []
            for e in elts:
                if isinstance(e,strTypes):
                    e2 = self.processString(asUnicode(e))
                else:
                    if not isinstance(e,tuple):
                        raise ValueError("bad content type %s" % type(e))
                    e2 = self.processTuple(e, overrides, containerdict)
                L.append(e2)
            return self.joinTranslatedContent(L)

    def processTuple(self, e, overrides, containerdict=None):
        tagname = e[0]
        nodemappers = self.nodemappers
        if overrides:
            nodemappers = nodemappers.copy()
            # do overrides
            nodemappers.update(overrides)
        defaultmapper = nodemappers.get(None, None)
        processor = nodemappers.get(tagname, defaultmapper)
        if processor is None:
            raise NameError("no processor for %s" % ascii(tagname))
        e2 = processor.translate(e, self, overrides, containerdict)
        return e2

    def joinTranslatedContent(self, L):
        return DelayedJoin(L, self.joinSeparator)

    def processString(self, elts):
        return elts # default, for now

    def clean_elts(self, elts):
        """optionally do stuff like dispose of all white content"""
        return elts

class DelayedJoin:
    value = None
    def __init__(self, L, s):
        self.L = L
        self.s = s

    if isPy3:
        def __str__(self):
            if self.value is not None: return self.value
            L = [asUnicodeEx(l) for l in self.L]
            self.value = result = self.s.join(L)
            # eliminate possible reference loops
            self.L = None
            return result

        def __bytes__(self):
            return self.__unicode__().encode('utf8')
    else:
        def __unicode__(self):
            if self.value is not None: return self.value
            L = [asUnicodeEx(l) for l in self.L]
            self.value = result = self.s.join(L)
            # eliminate possible reference loops
            self.L = None
            return result

        def __str__(self):
            return self.__unicode__().decode('utf8')

class ExtendedTransform:
    def __call__(self, t, sdict):
        return t

class SpecialTransform:
    '''transform that is given the name of the sdict entry so it can access the value directly'''
    def __call__(self, sdict, name):
        return asUnicodeEx(sdict[name])

class AttrsFilter(SpecialTransform):
    def __init__(self,rename={},remove=[],valueFunc=None):
        self.rename = rename
        self.remove = remove
        self.valueFunc = valueFunc
    def __call__(self, sdict, name):
        D = sdict[name]._D.copy()
        for k in self.remove:
            try:
                del D[k]
            except KeyError:
                pass
        for k,v in self.rename.items():
            try:
                D[v] = D.pop(k)
            except KeyError:
                pass
        valueFunc = self.valueFunc
        if valueFunc:
            for k,v in D.items():
                D[k] = valueFunc(k,v)
        return LazyAttrs(D)

class LazyKW:
    jstr = ', '
    pfx = ''
    def __init__(self,D):
        self._D = D
    if isPy3:
        def __str__(self):
            R = []
            for k,v in list(self._D.items()):
                R.append('%s="%s"' % (k,v))
            return self.pfx+self.jstr.join(R)

        def __bytes__(self):
            return self.__str__().encode('utf8')
    else:
        def __unicode__(self):
            R = []
            for k,v in list(self._D.items()):
                R.append('%s="%s"' % (k,v))
            return self.pfx+self.jstr.join(R)

        def __str__(self):
            return self.__unicode__().encode('utf8')

class LazyAttrs(LazyKW):
    jstr = ' '
    pfx = ' '

class MapNode(MapController):

    def __init__(self, full_substitution_string, empty_substitution_string=None, defaults=None):
        self.full_substitution_string = full_substitution_string
        self.empty_substitution_string = empty_substitution_string
        self.nodemappers = {}
        if defaults is None:
            defaults = {}
        self.defaults = defaults
        # transforms to apply per attribute to the content (eg make it have 2 digits and put a dollar in front)...
        self.transforms = {}

    def addTransform(self, name, t):
        self.transforms[name] = t

    def transformContent(self, t):
        self.addTransform('__content__',t)

    def translate(self, nodetuple, controller, overrides, containerdict=None):
        # add own overrides if present
        if self.nodemappers:
            overrides = overrides.copy()
            overrides.update(self.nodemappers)
        (tagname, attdict, content, extra) = nodetuple
        #tagname = nodedict[0]
        #content = nodedict.get(1, None)
        if not attdict: attdict = {}
        sdict = attdict.copy() # for modification
        prefix = tagname
        # prefix must be set before processing children
        #print "processing", tagname
        #print containerdict
        if containerdict is not None:
            cprefix = containerdict["__prefix__"]
            if cprefix:
                prefix = "%s.%s" % (cprefix, prefix)
        else:
            cprefix = ''
        sdict['__prefix__'] = prefix
        sdict['__parent_prefix__'] = cprefix
        sdict['__depth__'] = prefix.count('.')
        sdict['__parent_depth__'] = sdict['__depth__']-1
        sdict['__tag_depth__'] = (prefix+'.').count(tagname+'.')
        sdict['__mapnode__'] = self
        sdict['__controller__'] = controller
        sdict['__overrides__'] = overrides
        sdict['__containerdict__'] = containerdict
        sdict['__nodetuple__'] = nodetuple
        sdict["__tagname__"] = tagname
        sdict["__attrs__"] = LazyAttrs(attdict)
        defaults = self.defaults
        for name in list(defaults.keys()):
            if name not in sdict:
                sdict[name] = defaults[name]
        shadow = ShadowDict(tagname, sdict, containerdict)
        sdict['__shadow__'] = shadow
        #if content is None: stop
        if content is not None:
            pcontent = self.MyProcessContent(content, controller, overrides, shadow)
            sdict["__content__"] = pcontent
            # you can refer to TITLE.__content__
            top = controller.topDict
            if containerdict is not None:
                containerdict[tagname+".__content__"] = pcontent
            # you can refer to PLAY.TITLE.__content__
            top[prefix+".__content__"] = pcontent
            sstring = self.full_substitution_string
            if sstring is None:
                raise ValueError("no content allowed for %s" % ascii(tagname))
        else:
            sstring = self.empty_substitution_string
            if sstring is None:
                raise ValueError("content required for %s" % ascii(tagname))
        transforms = self.transforms
        for name in list(transforms.keys()):
            if name in sdict:
                t = transforms[name]
                if isinstance(t,SpecialTransform) or name=='__attrs__':
                    sdict[name] = t(sdict,name)
                else:
                    oldvalue = asUnicodeEx(sdict[name]) # IS STRING CONVERSION ALWAYS RIGHT?
                    if isinstance(t,ExtendedTransform):
                        sdict[name] = t(oldvalue, sdict)
                    else:
                        sdict[name] = t(oldvalue)
        try:
            result = shadow.substitute(sstring) #sstring % sdict
        except:
            raise ValueError("for tagname %s bad string %s for dict %s" % (
                ascii(tagname), ascii(sstring), ascii(list(sdict.keys()))))
        return result

    def MyProcessContent(self, content, controller, overrides, containerdict):
        """by default ask the global controller to do it"""
        return controller.processContent(content, overrides, containerdict)

class PreserveNode(MapNode):
    """This is a MapNode which aims to write out something
    close to the original tag"""

    def __init__(self):
         MapNode.__init__(self, None, None, None)

    def translate(self, nodetuple, controller, overrides, containerdict=None):

        #we want to leave this node unchanged, but let children through
        (tagName, attrs, content, extra) = nodetuple

        chunks = ['<%s' % tagName]
        if attrs is not None:
            for key, value in list(attrs.items()):
                chunks.append('%s="%s"' % (key, value))
        if content is None:
            chunks.append('/>')
        else:
            #must do children
            chunks.append('>')
            processedContent = self.MyProcessContent(content, controller, overrides, containerdict)
            chunks.append(asUnicodeEx(processedContent))
            chunks.append('</%s>' % tagName)
        return ''.join(chunks)

class ShadowDict:
    def __init__(self, name, dict=None, parent=None):
        self.name = name
        self.parent = {}
        self.dict = {}
        if parent is not None:
            self.parent = parent
        if dict is not None:
            self.dict = dict
    def __repr__(self):
        """tag like repr (but don't include parent info)"""
        n = self.name
        c = self.get("__content__", None)
        L = ["<%s" % n]
        d = self.dict
        K = list(d.keys())
        for name in K:
            if name[:2]!="__":
                v = d[name]
                L.append(' %s="%s"' % (name, v))
        if c is None:
            L.append("/>")
        else:
            L.append(">")
            L.append(c)
            L.append("</%s>" % n)
        return ''.join(L)
    def __getitem__(self, item):
        try:
            return self.dict[item]
        except KeyError:
            # special case: __repr__
            if item=="__repr__":
                return repr(self)
            return self.parent[item]
    def __setitem__(self, item, value):
        self.dict[item] = value
    def __contains__(self,item):
        return item in self.dict
    def get(self, item, default):
        try:
            return self[item]
        except:
            return default
    def namedsetitem(self, name, item, value):
        if self.name == name:
            self[item] = value
        else:
            try:
                self.parent.namedsetitem(name, item, value)
            except:
                raise ValueError("can't match name %s" % ascii(name))
    def substitute(self, s):
        return LazySubstitution(s, self)

class LazySubstitution:
    value = None
    def __init__(self, fmt, dictionary):
        self.fmt = fmt
        self.dictionary = dictionary

    if isPy3:
        def __str__(self):
            if self.value is not None: return self.value
            self.value = result = self.fmt % self.dictionary
            # now eliminate possible reference loops
            self.dictionary = None
            return result

        def __bytes__(self):
            return self.__str__().encode('utf8')
    else:
        def __str__(self):
            return self.__unicode__().encode('utf8')

        def __unicode__(self):
            if self.value is not None: return self.value
            self.value = result = self.fmt % self.dictionary
            # now eliminate possible reference loops
            self.dictionary = None
            return result

# hex colors for html
LIMEGREEN = "#32CD32"
LEMONCHIFFON = "#FFFACD"
LIGHTCORAL = "#F08080"
SKYBLUE = "#87CEEB"
CORNSILK = "#FFF8DC"

def textsection(title):
    L = [
    '<TABLE CELLSPACING="8" CELLPADDING="3" BORDER="0" WIDTH="98%%">',
    '<tr><TH bgcolor=%s align="right"><font face="arial">%s</font></td></tr>' % (LIMEGREEN, title),
    '<TR><TD><font face="arial">%(__content__)s</font></TD></TR>',
    '</TABLE>']
    return ''.join(L)

def customer_entry(title):
    return """<tr><td align="right" bgcolor="%s">
              <font face="arial"><em>%s</em></font></td>
        <td bgcolor="%s">
              <font face="arial"><b>%s</b></font></td></tr>""" % (
                  LEMONCHIFFON, title, LIGHTCORAL, "%(__content__)s")

charges_table_format = """
<center><TABLE BORDER="0" width=70%%>""" + """
<tr><td bgcolor=#87CEEB ALIGN="CENTER" colspan=4><font face="Arial">  American Fund </font></td></tr>
            <tr><td  bgcolor=#FFF8DC rowspan=3 colspan=2><font face="Arial"> Amount Invested:
            %(AMOUNT_INVESTED)s
            </font></td>
                <td  bgcolor=#FFFACD colspan=2><font face="Arial"> Initial Charge Ratio:
                %(INITIAL_CHARGE_RATIO)s
                </font></td></tr>
            <tr><td  bgcolor=#FFFACD colspan=2><font face="Arial"> Growth Rate:
            %(GROWTH_RATE)s
            </font></td></tr>
            <tr><td  bgcolor=#FFFACD colspan=2><font face="Arial"> Annual Charge Ratio:
            %(ANNUAL_CHARGE_RATIO)s
            </font></td></tr>
<tr><td  bgcolor=#FFF8DC align="right"><font face="Arial"> For year</font></td>
        <td  bgcolor=#FFFACD align=right><font face="Arial"> Invested to Date</font></td>
        <td  bgcolor=#FFFACD align=right><font face="Arial"> Total charges</font></td>
        <td  bgcolor=#FFFACD align=right><font face="Arial"> Valuation</font></td></tr>
        %(__content__)s
</table></CENTER>
"""
charges_row_format = """
<tr><td  bgcolor=#FFF8DC align="right"><font face="Arial">
                     %(YEAR)s
                     </font></td>
                        <td  bgcolor=#FFFACD align="right"><font face="Arial">
                        %(INVESTED_TO_DATE)s
                        </font></td>
                        <td  bgcolor=#FFFACD align="right"><font face="Arial">
                        %(EFFECT_OF_CHARGES)s
                        </font></td>
                        <td  bgcolor=#FFFACD align="right"><font face="Arial">
                        %(VALUATION)s</font></td></tr>
                        """

def currencystring(t):
    f = float(t)
    return "%10.2f" % f

def test():
    fn = "samples/hamlet.xml"
    ofn = "samples/hamlet.html"
    text = open(fn).read()
    M = MapController()
    # ref to %(TITLE.__content__)s should refer to the title of the play (not act or scene)
    M["PLAY"] = """ <html><head><title>%(TITLE.__content__)s</title></head><BODY>
                <CENTER><H1><FONT FACE="Arial">%(PLAY.TITLE.__content__)s</FONT></H1></CENTER>
         %(__content__)s
         <BODY>
         </html>
         """
    M[""] = "%(__content__)s"
    # TITLE VANISHES IT'S __CONTENT__ IS USED IN THE TOP LEVEL SUBSTITUTION
    M["TITLE"] = ""
##    # top level title
##    M["TITLE"] = """<HEAD>
##                <TITLE>%(__content__)s</TITLE>
##                </HEAD>
##                <BODY>
##                <CENTER><H1><FONT FACE="Arial">%(__content__)s</FONT></H1></CENTER>
##                """
    M["FM"] = """<BR><BR><BR>
                 <CENTER><TABLE><TR><TD BGCOLOR="#99A9FF">
                 %(__content__)s
                 </TD></TR></TABLE></CENTER>
                 """
    M["P"] = """<BR>%(__content__)s<BR>\n"""
    M["PERSONAE"] = """<BR><BR><BR>
                 <CENTER><TABLE>
                 %(__content__)s
                 </TABLE></CENTER>
                 """
    # override title
    M["PERSONAE"]["TITLE"] = "<CENTER><H3>%(PLAY.TITLE.__content__)s %(__content__)s</H3></CENTER>"
    M["PERSONA"] = """<TR><TD BGCOLOR="#A9FF99">%(__content__)s</TD></TR>\n"""
    M["PGROUP"] = """<TR><TD><HR></TR></TD>
                    %(__content__)s
                    <TR><TD><HR></TR></TD>"""
    M["GRPDESCR"] = """<TR><TD ALIGN="RIGHT"><EM>%(__content__)s</EM></TD></TR>"""
    M["SCNDESCR"] = """<CENTER><B>%(__content__)s</B></CENTER>\n"""
    M["PLAYSUBT"] = """<HR><BR><BR>%(__content__)s<BR><BR><HR>\n"""
    M["ACT"] = """%(__content__)s"""
    # override title behaviour
    M["ACT"]["TITLE"] = "<CENTER>%(PLAY.TITLE.__content__)s <H2>%(__content__)s</H2></CENTER>"
    M["SCENE"] = """%(__content__)s"""
    # override title behaviour
    M["SCENE"]["TITLE"] = "<CENTER><H3>%(PLAY.TITLE.__content__)s %(__content__)s</H3></CENTER>"
    THEAD = """<TABLE BORDER="0" WIDTH="98%%"><TR>\n"""
    TTAIL = """\n</TR></TABLE>\n"""
    M["STAGEDIR"] = THEAD + """<TD WIDTH="30%%"></TD><TD ALIGN=RIGHT><em>%(__content__)s</em></TD>\n""" + TTAIL
    M["SPEECH"] = THEAD + "%(__content__)s\n" + TTAIL + "<BR><BR>"
    # A stagedir inside a speech
    M["SPEECH"]["STAGEDIR"] = """<TD></TD><TD ALIGN=RIGHT><em>%(__content__)s</em></TD></TR><TR>\n"""
    M["SPEAKER"] = """<TD width="30%%"><B>%(__content__)s</B>\n</TD><TD></TD></TR><TR>"""
    M["LINE"] = """<TD></TD><TD>%(__content__)s</TD></TR><TR>"""
    M["LINE"]["STAGEDIR"] = "<EM>[%(__content__)s]</EM>"
    import os
    os.chdir('samples')
    otext = M.process(text)
    os.chdir('..')
    open(ofn, "w").write(otext)
    print("wrote", ofn)

if __name__=="__main__":
    from time import time
    now = time()
    print('processing samples/hamlet.xml')
    test()
    print("elapsed", time()-now)
