#dynamic rml experiments

from reportlab.lib.utils import strTypes, isBytes, isUnicode, rl_exec, asUnicodeEx
from rlextra.radxml import xmlutils
from pprint import pprint as pp
from reportlab.lib.utils import recursiveImport
from rlextra.radxml import xacquire
from rlextra.radxml.xmlutils import xmlEscape

ENTITY_SUBSTITUTIONS_DRAWSTRING_DICT = {    #these must be in utf8
    u"&pound;":u'\xa3',
    u"&amp;":u"&",
    u"&lt;":u"<",
    u"&gt;":u">",
    u"&quot;":u"\"",
    u"&apos;":u"'",
    u"&#039;":u"'",
    }

#we allow multiple names for each tag.
# Sometimes DTD's/schemas are cleaner if you can define
# separate block-level or line-level tags, whose content can
# then be defined as something more helpful than 'anything goes'.

#These could all be redefined for a new app.
TAG_LOOP = [u'loop', u'loop_b',u'loop_i', u'loop_t',u'loop_g', u'loop_s']
TAG_LOOP_INNER = u'var'
TAG_LOOP_OUTER = u'in'

TAG_EXPR = [u'expr',u'expr_i',u'expr_b']
TAG_IF = [u'if', u'if_i',u'if_b',u'if_g',u'if_t', u'if_s']

# this is the general 'if' statement.  The switch contains 1 or
# more cases, and an optional default.
# You may use one of two patterns:
#..a named variable and allowed values....
#<switch expr="colour">
#  <case cond="green">Go</case>
#  <case cond="amber">Slow</case>
#  <case cond="red">Stop</case>
#</switch>
#...or a full python expression in each condition...
#<switch>
#  <case cond="colour==green">Go</case>
#  <case cond="colour==amber">Slow</case>
#  <case cond="colour==red">Stop</case>
#</switch>
#It knows which to do based on the presence/absence of 'expr' in the switch.
#

TAG_SWITCH = [u'switch',u'switch_b',u'switch_i',u'switch_g',u'switch_t',u'switch_s']
TAG_CASE = [u'case',u'case_b',u'case_i',u'case_g',u'case_t',u'switch_s']
TAG_DEFAULT = [u'default',u'default_b',u'default_i',u'default_g',u'default_t',u'default_s']

TAG_ASSIGN = [u'assign',u'assign_b',u'assign_i',u'assign_g',u'assign_t']
TAG_ASSIGN_NAME = u'name'
TAG_ASSIGN_VALUE = u'value'

TAG_SCRIPT = [u'script',u'script_b',u'script_i',u'script_g',u'script_t']

TAG_ACQUIRE = [u'acquire',u'acquire_b',u'acquire_i',u'acquire_g',u'acquire_t']

TAG_DOCLET = [u'doclet',u'doclet_b']

sample1 = b"""<?xml version="1.0" encoding="UTF-8"?>
<document>
<script>import string</script>
<assign name="author" value="Andy Robinson"/>
<author><expr>author + ' ' + string.digits</expr></author>
<para>Here comes a table with <expr>2+2</expr> rows</para>
<table><tr><td>Product</td><td>Units</td><td>Taste</td></tr>
<loop var="(product, units)" in="dataSet">  <tr>
    <td><expr>product</expr></td>
    <td><expr>units</expr></td>
    <td>
        <switch expr="product">
            <case condition="ham">nice</case>
            <case condition="spam">nasty</case>
            <case condition="eggs">OK</case>
            <default>never tried that...</default>
        </switch>
    </td>
  </tr></loop>
</table>
</document>
"""

def preProcess(tree, nameSpace, caller=None):
    """Expands the parsed tree in the namespace and return new one.
    Returns a single tag-tuple in most cases, but a list of them
    if processing a loop node.

    """
    from rlextra.radxml import xmlutils
    #expand this into a class with methods for each tag it handles.
    #then I can put logic tags in one and data access in another.
    tagName, attrs, children, extraStuff = tree

    #any attribute as $name becomes th value of name
    #tags might be nested in a loop, and if so then
    #each dictionary must be a fresh copy rather than
    # a pointer to the same dict
    
    newAttrs = attrs.copy() if attrs is not None else {}
    for key, value in list(newAttrs.items()):
        if isinstance(value,str) and value[0:1] == '$':
            newValue = eval(value[1:], nameSpace)
            newAttrs[key] = newValue
    attrs = newAttrs

    if tagName in TAG_LOOP:
        innerTxt = attrs[TAG_LOOP_INNER]
        outer = eval(attrs[TAG_LOOP_OUTER], nameSpace)
        dataSet = []
        for row in outer:
            nameSpace['__loop_inner__'] = row
            rl_exec((innerTxt + " = __loop_inner__\n"), nameSpace)
            #at this point we're making lots of child nodes.
            # the attribute dictionary of each shold be a copy, not
            # a reference
            newChildren = processChildren(children, nameSpace)
            if newChildren is not None:
                dataSet.extend(newChildren)
        return dataSet

    elif tagName in TAG_ASSIGN:
        name = attrs[TAG_ASSIGN_NAME]
        valueStr = attrs[TAG_ASSIGN_VALUE]
        try:
            value = eval(valueStr)
        except SyntaxError:  #must be a string
            value = valueStr
        nameSpace[name] = value
        return None

    elif tagName in TAG_SCRIPT:
        code = children[0]
        if not code.endswith('\n'): code += '\n'
        try:
            rl_exec(code, nameSpace)
        except SyntaxError:
            raise SyntaxError("Error with following script in xpreppy:\n\n%s" % code)
        return None

    elif tagName in TAG_EXPR:
        exprText = children[0]
        assert isinstance(exprText,strTypes), "expr can only contain strings"

        #attributes may affect escaping
        escape = attrs.get(u'escape', None)
        encoding = attrs.get(u'encoding',u'utf8')

        exprValue = eval(exprText, nameSpace)
        if isBytes(exprValue):
            exprValue = exprValue.decode(encoding)
        elif isUnicode(exprValue):
            pass
        else:
            exprValue = asUnicodeEx(exprValue)

        if escape in (u'CDATA',u'CDATAESCAPE'):
            exprValue = u'<![CDATA[%s]]>' % exprValue
            if escape==u'CDATA': return [exprValue]
        elif escape == u'off':
            return [asUnicodeEx(exprValue)]
        elif escape == u'unescape':
            return [xmlutils.unescape(exprValue, ENTITY_SUBSTITUTIONS_DRAWSTRING_DICT)]
        return [xmlEscape(exprValue)]

    elif tagName in TAG_IF:
        condText = attrs[u'cond']
        yesOrNo = eval(condText, nameSpace)
        if yesOrNo:
            return processChildren(children, nameSpace)
    
    elif tagName in TAG_SWITCH:
        #two modes, with and without top level variable
        exprText = attrs.get(u'expr',u'')

        if exprText:
            expr = eval(exprText, nameSpace)

        selected = None
        for child in children:
            if isinstance(child,tuple):
                (childTagName, childAttrs, grandChildren, stuff) = child
                if childTagName in TAG_CASE:
                    condition = childAttrs[u'condition']
                    if exprText:
                        #check if it equals the value
                        try:
                            value = eval(condition, nameSpace)
                        except NameError:
                            value = condition # assume a string
                        if (expr == value):
                            selected = processChildren(grandChildren, nameSpace)
                            break
                    else:
                        #they gave us a full condition, evaluate it
                        yes = eval(condition, nameSpace)
                        if yes:
                            selected = processChildren(grandChildren, nameSpace)
                            break
                elif childTagName in TAG_DEFAULT:
                    selected = processChildren(grandChildren, nameSpace)
                    break
                else:
                    raise ValueError('%s tag may only contain these tags: ' % (TAG_SWITCH, ', '.join(TAG_CASE+TAG_DEFAULT)))

                    
        return selected

    elif tagName in TAG_ACQUIRE:
        #all children will be data fetchers
        xacquire.acquireData(children, nameSpace)
        return None

    elif tagName in TAG_DOCLET:
        #pull out args needed to initialize
        dirName = attrs.get(u"baseDir", None)
        moduleName = attrs[u"module"]
        className = attrs[u"class"]
        dataStr = attrs.get(u"data", None)

        #load module, import and create it
        if caller == 'rml':
            from rlextra.rml2pdf.rml2pdf import _rml2pdf_locations
            locations = _rml2pdf_locations(dirName)
        else:
            locations = dirName
        m = recursiveImport(moduleName, locations)
        klass = getattr(m, className)
        docletObj = klass()

        #give it the data model
        if dataStr:
            dataObj = eval(dataStr, nameSpace)
        else:
            dataObj = nameSpace

        docletObj.setData(dataObj)
            

        #hide it in the tree so RML can see the object
        attrs[u'__doclet__'] = docletObj

        #return the tag otherwise unmodified        
        return (tagName, attrs, children, extraStuff)
    
    else:
        newChildren = processChildren(children, nameSpace)
        return (tagName, attrs, newChildren, extraStuff)

def processChildren(children, nameSpace):
    """Handles iteration over child tags, one of which may be a loop

    Also substitutes into attributes.
    """

    if children is None:
        newChildren = None
    else:
        newChildren = []
        for child in children:
            if isinstance(child,strTypes):
                newChildren.append(child)
            else:
                newStuff = preProcess(child, nameSpace)
                if isinstance(newStuff,tuple):
                    #returned a single tag-tuple
                    newChildren.append(newStuff)
                elif isinstance(newStuff,list):
                    #must have been a loop tag, returned a list
                    newChildren.extend(newStuff)
                #if None, omit it...
    return newChildren

def processDataAcquitision(children, nameSpace):
    """The data acquisition tags give easy access to data sources.
    They do not return values but put them in the namespace"""
    if children is None:
        newChildren = None
    else:
        for child in children:
            if isinstance(child,strTypes):
                newChildren.append(child)
            else:
                newStuff = preProcess(child, nameSpace)
                if isinstance(newStuff,tuple):
                    #returned a single tag-tuple
                    newChildren.append(newStuff)
                elif isinstance(newStuff,list):
                    #must have been a loop tag, returned a list
                    newChildren.extend(newStuff)
                #if None, omit it...
    return newChildren

def run(sample):
    from reportlab.lib.rparsexml import parsexml
    tree = parsexml(sample)
    xmlutils.stripWhitespace(tree)


    nameSpace = {u'dataSet':[(u'ham',3),(u'spam',15),(u'eggs',12)]}
    processed = preProcess(tree, nameSpace)
    print()
    print('raw results:')
    pp(processed)
    print()
    print('formatted as XML again:')
    tw = xmlutils.TagWrapper(processed)
    xml = xmlutils.reconstructXML(tw)
    print(xml)

if __name__=='__main__':
    run(sample1)
