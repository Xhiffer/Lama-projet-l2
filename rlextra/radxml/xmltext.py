from __future__ import print_function
"""structured text for general xml

This module encodes xml markup as "more easily editable" structured text,
and provides the structured text --> xml conversion also.

THIS IS "QUICK AND DIRTY" AND IS NOT INTENDED FOR
USE IN "BOUNDARY CASES" -- TO HANDLE BOUNDARY CASES PLEASE
EDIT XML DIRECTLY RATHER THAN USE THIS CONVENIENCE.

It is expected that this approach is "good enough" for
most XML usage -- but for some uses it will break.
See assumptions below.

Conventions:

The XML

# text before <tag a="b">some text</tag> text after

becomes (inline structured text convention)

# text before .tag(a="b")some text\n
# text after

where the parens can be omitted when there are no attributes.
OR for longer text (indentation structured text convention)

# text before .tag(a="b")\n
#      longer\n
#      text\n
# text after

Tag names may be abbreviated.  If "tag" is abbreviated to "t"
then 

# text before <tag>some text</tag> text after

may be written (inline convention)

# text before .t some text\n
# text after

OR (indentation convention)

# text before .t
#     some\n
#     text\n
# text after

OR (equivalently, but maybe more readable)

# text before 
# .t
#     some\n
#     text\n
# text after

Convention for tags with no content:

# text before <tag a="b"/> text after

becomes

# text before .tag(a="b")! text after

or if no attributes and abbreviated

# text before .t! text after

OR if it has been declared converter.contentless("t") simply

# text before .t text after

If you need to make a string of the form "z.strip" without intending
it to indicate markup, spell it "z\.strip".

special case: <b>xxx</b> becomes **xxx** and <i>xxx</i> becomes *xxx*

The following assumptions are assumed by the processor implementation.

ASSUMPTIONS: 
    1) all tags are surrounded by whitespace.
    2) all white space (except newlines) is "the same."
        (no preformatted text, for example -- but preserve newlines!)
    3) indentations are strictly consistent (no replacing of spaces with tabs)
    4) strings of form .X* (where X is alphabetic) never occur in the intended
        XML text output.
    5) double quotes and parentheses and never appear in attribute values
    6) escaped CDATA text is NOT PERMITTED.
    7) nesting of <b> and <i> is NOT PERMITTED.

In the event that tags contain tags indentation conventions are nested.

"""
from reportlab.lib.utils import ascii_letters
import string
class XMLTextConverter:
    def __init__(self, indent=" "*4):
        self.indent = indent
        self.TagToAbbreviation = {}
        self.AbbreviationToTag = {}
        self.contentlessTags = {}
    def contentless(self, tagname):
        self.contentlessTags[tagname] = tagname
    def abbreviate(self, tagname, abbreviation):
        a2t = self.AbbreviationToTag
        t2a = self.TagToAbbreviation
        if not tagname or not abbreviation:
            raise ValueError("cannot abbreviate using the empty string " + repr((abbreviation, tagname)))
        if abbreviation in a2t and a2t[abbreviation]!=tagname:
            raise ValueError("abbreviation in use %s (%s)" % (repr(abbreviation), repr(tagname)))
        # it doesn't matter if tags have multiple abbreviations
        t2a[tagname] = abbreviation
        a2t[abbreviation] = tagname
    def text2XML(self, text, start=0, end=None, level=0):
        # start must point to beginning of line whenever not in the middle of nonwhite line segment
        # the text[start:(end)] must all be at or past the indentation level of the first line.
        levelindent = "  "*level
        resultlist = [] # list of string
        if end is None:
            end = len(text)
        #print levelindent, "===text2xml==="
        #print indentText( text[start:end], levelindent )
        cursor = start
        alphanum = ascii_letters + string.digits
        while cursor<end:
            #print levelindent, "cursor is ", cursor, "near", repr(text[cursor: cursor+10])
            foundtag = None
            beforetag = cursor
            # look for first "." followed by an alpha
            while foundtag is None and cursor<end:
                firstmark = text.find(".", cursor, end)
                #print levelindent, "...cursor is", cursor, "firstmark", firstmark
                if firstmark>=cursor:
                    aftercursor = firstmark+1
                    next = text[aftercursor:aftercursor+1]
                    #print levelindent, "...next", next
                    # only recognize .alpha but not \.alpha
                    if next in ascii_letters and text[firstmark-1:firstmark]!='\\':
                        foundtag = cursor = aftercursor
                    else:
                        cursor = aftercursor
                else:
                    cursor = end
            if foundtag is None:
                # just indent the tagless text
                remainder = text[beforetag:end].strip()
                if "\n" in remainder:
                    remainder = "\n"+indentText(remainder, levelindent)
                #print levelindent, "finishing with remainder", repr(remainder)
                resultlist.append( xmlEscape(remainder) )
                cursor = end
            else: # foundtag is not None: process the tag and content if present
                # find the previous newline
                taglinestart = text.rfind("\n", start, foundtag)
                if taglinestart<start:
                    taglinestart=start
                else:
                    taglinestart = taglinestart+1
                # look for first nonalphanumeric
                cursor = aftercursor
                foundtagnameend = None
                while cursor<end and foundtagnameend is None:
                    aftercursor = cursor+1
                    nextchar = text[cursor:aftercursor]
                    if nextchar not in alphanum:
                        foundtagnameend = aftercursor
                    else:
                        cursor = aftercursor
                if cursor==end:
                    foundtagnameend = end
                tagname = text[foundtag:cursor]
                #print levelindent, "tagname", repr(tagname)
                tagname = self.AbbreviationToTag.get(tagname, tagname)
                #print levelindent, "unabbreviated tagname", repr(tagname)
                textbeforetag = text[beforetag:foundtag-1]
                aftercursor = cursor+1
                nextchar = text[cursor:aftercursor]
                #print levelindent, "nextchar", nextchar
                tagattributesstring = None
                closeparenlocation = cursor-1 # end of tag name is end of attributes by default
                if nextchar=="(":
                    #print levelindent, "tag has attributes, look for next close paren"
                    # look for close paren; make sure the number of quotes inside is even
                    seek = cursor
                    closeparenok = None
                    while not closeparenok and seek<end:
                        closeparenlocation = text.find(")", seek, end)
                        if closeparenlocation<seek:
                            raise ValueError("found '(' after %s tagname %s but no unquoted ')' follows before %s near %s" % (
                                cursor, repr(tagname), end, repr(text[seek:seek+20])))
                        # check that the quotesplits are odd (ie the number of quotes are even)
                        segment = text[cursor:closeparenlocation]
                        #singlequotesplit = segment.split("'")
                        doublequotesplit = segment.split('"')
                        #print doublequotesplit
                        if len(doublequotesplit)%2==1:
                            closeparenok = 1
                        seek = closeparenlocation+1
                    # note: it is legal to have newlines between the parens
                    tagattributesstring = text[aftercursor:closeparenlocation]
                    cursor = closeparenlocation+1
                    # check validity of the attribute string
                    tagattributesstringcursor = 0
                    equallocation = tagattributesstring.find("=", tagattributesstringcursor)
                    while equallocation>=tagattributesstringcursor:
                        attributename = tagattributesstring[tagattributesstringcursor:equallocation]
                        attributename = attributename.strip()
                        #print levelindent, "attributename", attributename
                        afterequal = equallocation+1
                        afterquote = afterequal+1
                        quotechar = tagattributesstring[afterequal:afterquote]
                        #print levelindent, "quotechar", quotechar
                        if quotechar not in ('"', "'"):
                            raise ValueError("after '%s=' a quote character is required in %s" % (
                                attributename, repr(tagattributesstring)))
                        # search for matching quote
                        endquotelocation = tagattributesstring.find(quotechar, afterquote)
                        if endquotelocation<afterquote:
                            raise ValueError("after %s=%s... a matching close quote is required in %s" % (
                                attributename, quotechar, repr(tagattributesstring)))
                        #attributevalue = tagattributesstring[afterquote:endquotelocation]
                        #print levelindent, ".....attribute", repr(attributename), "==", repr(attributevalue)
                        equallocation = tagattributesstring.find("=", endquotelocation)
                        tagattributesstringcursor = endquotelocation+1
                # emit the text before the tag
                textbeforetag = indentText(textbeforetag, levelindent)
                #print levelindent, "textbeforetag is", repr(textbeforetag), "tag is", tagname, "cursor at", repr(text[cursor:cursor+1])
                resultlist.append( xmlEscape(textbeforetag) )
                # emit the start of start tag
                resultlist.append("\n%s <%s" % (levelindent, tagname))
                # emit the attributes XXXX DOES THIS NEED TO BE ESCAPED?
                if tagattributesstring:
                    #print levelindent, "tag attribute string is", repr(tagattributesstring)
                    tagattributesstring = xmlEscape(tagattributesstring) # DOES NOT ESCAPE DOUBLE QUOTES!!
                    resultlist.append(" %s" % tagattributesstring)
                # figure out if there should be content
                cursor = closeparenlocation+1
                aftercursor = cursor+1
                aftercloseparenchar = text[cursor:aftercursor]
                nocontent = None
                if aftercloseparenchar == "!":
                    nocontent = 1
                    cursor = aftercursor
                if tagname in self.contentlessTags:
                    nocontent = 1
                if nocontent:
                    # close the tag and proceed
                    resultlist.append("/> ")
                    #cursor = aftercursor
                else:
                    # close the start tag
                    resultlist.append(">")
                    # find the end of the content
                    # if it is inline the next newline is the end
                    inlinestyle = None
                    nextnewline = text.find("\n", cursor, end)
                    # if no newline then inline
                    if nextnewline<cursor:
                        #print levelindent, "tag is inline because no newline found in region"
                        inlinestyle = 1
                        contentend = end
                    # if newline found and substring to newline is not white then inline
                    elif text[cursor:nextnewline].strip():
                        #print levelindent, "tag is inline because cursor to newline is nonwhite", repr(text[cursor:nextnewline])
                        inlinestyle = 1
                        contentend = nextnewline+1
                    else:
                        # move cursor past the newline
                        cursor = nextnewline+1
                    if inlinestyle:
                        xmlcontent = self.text2XML(text, start=cursor, end=contentend, level=level+1)
                        cursor = contentend
                    else:
                        # otherwise it must be indentation based: find next dedent (no dedent means "" content)
                        # first determine the current indent
                        (thisindent, dummy) = getIndent(text, start=taglinestart, stop=cursor)
                        #lenthisindent = len(thisindent)
                        #print levelindent, "thisindent", repr(thisindent)
                        if thisindent is None:
                            raise ValueError("how did I find a tag on an all white line?")
                        # skip to the end of the indented region, or to end of text segment to scan
                        laststartpoint = endofregion = cursor
                        donescanning = 0
                        while endofregion<end and not donescanning:
                            (nextindent, endofline) = getIndent(text, start=endofregion, stop=end)
                            #print levelindent, "nextindent is", repr(nextindent)
                            laststartpoint = endofregion
                            endofregion = endofline+1
                            if nextindent==thisindent:
                                # done scanning, found same indent
                                #print levelindent, "indent match found", repr(text[laststartpoint:endofline])
                                donescanning = 1
                            elif nextindent is None:
                                # all white line: keep looking
                                pass
                            else:
                                pass
                                # check that indentation matches (THIS IS WRONG IN CASE OF TWO DEDENTS)
##                                if nextindent[:lenthisindent]!=thisindent:
##                                    print "<h1>SEGMENT::</H1><pre>"+text[cursor:endofline]+"</pre>"
##                                    raise ValueError, "bad indent following %s in %s" % (
##                                        repr( text[taglinestart:cursor]),
##                                        repr( text[laststartpoint:endofline]) )
                                #print levelindent, "deeper indent found", repr(text[laststartpoint:endofline])
                                # otherwise the indentation must be deeper, keep looking
                        if endofregion>=end and not donescanning:
                            # consume the whole buffer
                            laststartpoint = end
                        # translate the region
                        xmlcontent = self.text2XML(text, start=cursor, end=laststartpoint, level=level+1)
                        cursor = laststartpoint#endofregion+1
                    # emit xml content
                    #print levelindent, "xmlcontent is", repr(xmlcontent)
                    resultlist.append(xmlcontent)
                    # emit the close tag
                    resultlist.append("</%s> " % (tagname))
        #print levelindent, "resultlist is", resultlist
        xml = "".join(resultlist)
        return xml
    def XML2text(self, xml):
        from reportlab.lib import rparsexml
        xml = textEscape(xml)
        parsedxml = rparsexml.parsexmlSimple(xml)
##        from pprint import pprint
##        print "===INPUT=="; print xml; print "===END OF INPUT==="
##        print "===PPRINT OF PARSE=="; pprint(parsedxml); print "===END OF PPRINT==="
        text = self.parsedXML2text(parsedxml, indent=self.indent)
        return text
    def parsedXML2text(self, parsedxml, indent=None, level=0):
        (name, attdict, textlist, extra) = parsedxml
##        print "   "*level, "TAG=", repr(name), attdict
##        print "   "*level, "CONTENT=",
##        if not textlist:
##            print "   "*level, repr(textlist)
##        else:
##            print
##            for x in textlist:
##                print "   "*level, "=", repr(x)
        # translate the name, if defined
        originalname = name
        name = self.TagToAbbreviation.get(name, name)
        # determine the attribute string
        attributestring = ""
        if attdict:
            attlist = []
            attnames = list(attdict.keys())
            attnames.sort()
            for attname in attnames:
                attvalue = attdict[attname]
                if '"' in attvalue:
                    raise ValueError("this translator does not support double quotes in attribute values "+repr((attname,attvalue)))
                formatted = '%s="%s"' % (attname, attvalue)
                attlist.append(formatted)
            attributestring = " ".join(attlist)
            attributestring = "(%s)" % attributestring
        if indent is None:
            indent = self.indent
        if textlist is None:
            # "empty" tag -- if contentless, omit the !
            if not name:
                raise ValueError("empty tag with no name makes no sense!")
            if self.contentlessTags.get(originalname, None):
                return ".%s%s\n" % (name, attributestring)
            else:
                return ".%s%s!\n" % (name, attributestring)
        else:
            # tag with content
            # process the content list
            processedtextlist = []
            cursor = 0
            nlist = len(textlist)
            while cursor<nlist:
                e = textlist[cursor]
                cursor = cursor+1
                if isinstance(e,str):
                    processed = unindentText(e)
                elif isinstance(e,tuple):
                    processed = self.parsedXML2text(e, indent, level=level+1)
                    # if the next element is a string, trim at most one newline from white prefix (prettification)
                    if cursor<nlist:
                        nexte = textlist[cursor]
                        if nexte and isinstance(nexte,str):
                            ln = nexte.split("\n")
                            if not ln[0].strip():
                                textlist[cursor] = "\n".join(ln[1:])
                else:
                    raise ValueError("I don't know what to do with %r in parsed text list" % e)
##                print "   "*level, "before===", repr(e)
##                print "   "*level, "processed", repr(processed)
                processedtextlist.append(processed)
            processedtext = "".join(processedtextlist) # newlines handled lower down
            # if the tag is "" then just return the processed text
            if not name:
##                print; print "   "*level, repr(processedtext); print
                return processedtext
            # use the indent convention if there is a newline not at the end of text or if text is long
            inlineConvention = ".%s%s %s\n" % (name, attributestring, processedtext)
            inlinelen = len(inlineConvention)
            if inlinelen>80 or "\n" in processedtext.rstrip():
                # indent convention
                indentedtext = indentText(processedtext)
                # trim extra leading newline if present
                if indentedtext and indentedtext[0]=="\n": indentedtext=indentedtext[1:]
                if indentedtext and indentedtext[-1]=="\n": indentedtext=indentedtext[:-1]
                result = ".%s%s\n%s\n" % (name, attributestring, indentedtext)
##                print; print "   "*level, repr(result); print
                return result
            else:
                # inline convention
                result = inlineConvention
                if inlinelen>50:
                    # prepend newline
                    result = "\n" + result
##                print "   "*level, repr(result)
                return result
            raise ValueError("unreachable code")

def xmlEscape(text):
    text = text.replace("&", "&amp;")
    text = text.replace("<", "&lt;")
    text = text.replace(">", "&gt;")
    text = replacemarks(text, "**", "<b>", "</b>")
    text = replacemarks(text, "*", "<i>", "</i>")
    ### remove the "." escape hack
    text = text.replace("\\.", ".")
    return text

def replacemarks(text, marker, starttag, endtag):
    stext = text.split(marker)
    nsegs = len(stext)
    if nsegs!=0 and nsegs % 2 != 1:
        raise ValueError("odd number of %s markers in text" % repr(marker))
    if len(stext)<2:
        # no marker found
        return text
    first = stext[0]
    # consume extra space at end of prefix
    if first[-2:]=="  ":
        first = first[:-1]
    outlist = [first]
    del stext[0]
    while stext:
        [marked, after] = stext[:2]
        # consume extra spaces in after
        if after[:2]=="  ":
            after = after[1:]
        if after[-2:]=="  ":
            after = after[:-1]
        outlist.append(starttag)
        outlist.append(marked)
        outlist.append(endtag)
        outlist.append(after)
        del stext[:2]
    return "".join(outlist)

def getIndent(text, start=0, stop=None):
    # find the whitespace prefix for the line starting at start
    # if the line is all white, return None (ie, ignore).  Also return the end of line
    stop1 = text.find("\n", start)
    if stop is None:
        stop = stop1
        if stop<start:
            stop = len(text)
    elif stop1>=start and stop>stop1:
        stop = stop1
    line = text[start:stop]
    sline = line.strip()
    if not sline:
        return (None, stop)
    indentend = line.find(sline)
    if indentend<0:
        raise ValueError("CAN'T FIND STRIP STRING IN STRING!")
    thisindent = line[:indentend]
    return (thisindent, stop)

def unindentText(textblock):
    "make sure text block is flush left, also remove whitespace preceding newlines"
    lines = textblock.split("\n")
    slines = [l.strip() for l in lines]
    result = "\n".join(slines)
    return result

def textEscape(xml):
    """ for any '.' that precedes an alpha, change it to a '\.'
        convert <i> and </i> to * and *
        convert <b> and </b> to ** and **
    """
    xml = xml.replace("<i>", " *")
    xml = xml.replace("</i>", "* ")
    xml = xml.replace("<b>", " **")
    xml = xml.replace("</b>", "** ")
    sxml = xml.split(".")
    outlist = [sxml[0]]
    sawbackslash = 0
    for e in sxml[1:]:
        if not sawbackslash and e[0:1] in ascii_letters:
            outlist.append('\\')
        outlist.append('.')
        outlist.append(e)
        if e[-1:]=='\\':
            sawbackslash = 1
        else:
            sawbackslash = 0
    return "".join(outlist)

def indentText(textblock, indentation=" "*4):
    "add indentation to all nonwhite lines of textblock, remove extra whitespace in all white lines"
    lines = textblock.split("\n")
    ilines = []
    for l in lines:
        l2 = l.strip()
        if l2:
            l = indentation+l
            ilines.append(l)
        else:
            ilines.append("") # all white
    # remove extra white lines at the end
    while ilines and not ilines[-1]:
        del ilines[-1]
    return "\n".join(ilines)

XMLSAMPLE = """<this type="xml">text brackets: &lt;&gt;. <b>in</b> <funnytag foo="bar"/> xml</this>
                <narf><narf></narf></narf>
                 <!-- comment -->
                 <tag with="<brackets in values>">just testing brackets feature</tag>"""

XMLSAMPLE2 = '''<endorsementHeader number="{{number}}" title="APPROVED CUSTOMER ENDORSEMENT" issuedBy="{{issuedBy}}" issuedTo="{{companyName}}"
    policyNo="{{policyNo}}" effDate="{{effectiveDate}}"/>


<p>The following are <b>approved customers</b> on the terms outlined below:</p>
<spacer length="0.5cm"/>

<approvedCustomerHeader/>

{{for C in ApprovedCustomers}}

{{script}}
from projects.AIGRisk.do_policy_main import formatLines
theName = formatLines([ C["Name1"], C["Name2"] ], 32)
theAddress = formatLines([ C["Address1"], C["Address2"] ], 32)
amountApproved = C["limitApproved"].strip()[:-3]
currencyApproved = C["limitApproved"].strip()[-3:]
{{endscript}}

<approvedCustomer>
    <ACName><p>{{theName}}</p></ACName>
    <ACAddress><p>{{theAddress}}</p></ACAddress>
    <ACEffDate><p>{{ C["effDate"] }}</p></ACEffDate>
    <ACLimit><p>{{ amountApproved + "\n" + currencyApproved }}</p>
    </ACLimit>
    <ACMaxTerms><p>{{ C["maxPayTerms"] }}</p></ACMaxTerms>
</approvedCustomer>
{{endfor}}

<spacer length="0.5cm"/>
<p>All other terms, conditions, and exclusions of this Policy shall remain unchanged.</p>

<signatures/>

'''

XMLSAMPLE3 = """ <ACLimit><p>{{ amountApproved + "\n" + currencyApproved }}</p>
    </ACLimit> """

XMLSAMPLE4 = """


<!-- declarations page starts here -->

<AIGLogo/>

<bigCentered>{{THECOMPANY}}</bigCentered>

<centered><font face="Helvetica">
(A Stock Insurance Company, Hereinafter Called the Company)</font>
</centered>

<centered>
<b>Executive Offices</b>
</centered>

<centered>
<b>{{issuedByAddress1}}</b>
</centered>

<centered>
<b>{{issuedByAddress2}}</b>
</centered>

<spacer length="0.5cm"/>

<centered>
<b>AIG TRADECREDIT.COM DECLARATIONS</b>
</centered>

<spacer length="0.5cm"/>

<p>If <b>you</b> have any questions about <b>your</b> insurance policy, 
or questions about claims relating to <b>your</b> insurance policy, please contact <b>us</b>
at 1-888-437-3662.</p>

<spacer length="1cm"/>

<p>
POLICY NO.: <font face="Courier">{{policyNo}}</font>
</p>

<spacer length="0.5cm"/>

<policyItem number="Item 1." title="Insured's Name and Address:">
    <p>{{companyName}}</p>
    {{if companyAddress1.strip()}} <p>{{companyAddress1}}</p> {{endif}}
    {{if companyAddress2.strip()}} <p>{{companyAddress2}}</p> {{endif}}
    {{if companyAddress3.strip()}} <p>{{companyAddress3}}</p> {{endif}}
    {{if companyAddress4.strip()}} <p>{{companyAddress4}}</p> {{endif}}
</policyItem>

<policyItem number="Item 1.a." title="Insured's E-Mail Address:">
    <p>{{contactEmail}}</p>
</policyItem>

<policyItem number="Item 2." title="Policy Period:">
    <p>For <b>shipments</b> made on and after <b>
    {{effectiveDate}}
    </b> (12:01 a.m., at the
    address stated in Item 1. of these Declarations) to 
    <b> 
    {{expirationDate}}
    </b> (12:01 a.m., at the address stated in Item 1. of these
    Declarations)</p>
</policyItem>

<policyItem number="Item 3." title="Premium:"><p>
    As per the attached Premium Endorsement
</p></policyItem>

<policyItem number="Item 4." title="Insured Percentage:"><p>
For <b>documented obligations</b> due and owing from an <b>approved
customer</b> which are submitted to the Collection Agency stated in Item 6.
of these Declarations:
</p></policyItem>

<policyItem2 number="">
<p>a. Within 0 to 90 days from the oldest unpaid due date of payment: 85% of the <b>approved customer limit.</b></p>
<p>b. Within 91 to 120 days from the oldest unpaid due date of payment: 70% of the <b>approved customer limit.</b></p>
<p>c. On or after 121 days from the oldest unpaid due date of payment: 0% of the <b>approved customer limit.</b></p>
</policyItem2>

<policyItem number="Item 5." title="Deductible:"><p>
{{deductible}} for <b>shipments</b> made during the period of {{effectiveDate}} to {{expirationDate}}.
</p></policyItem>

<policyItem3 number="Item 6." title="Collection Agency's Name and Address">
    <p>{{collectionAgencyName1}}</p>
    {{if collectionAgencyName2.strip()}} <p>{{collectionAgencyName2}}</p> {{endif}}
    {{if collectionAgencyAddress1.strip()}} <p>{{collectionAgencyAddress1}}</p> {{endif}}
    {{if collectionAgencyAddress2.strip()}} <p>{{collectionAgencyAddress2}}</p> {{endif}}
    {{if collectionAgencyAddress3.strip()}} <p>{{collectionAgencyAddress3}}</p> {{endif}}
    {{if collectionAgencyAddress4.strip()}} <p>{{collectionAgencyAddress4}}</p> {{endif}}
</policyItem3>

<policyItem number="Item 7." title="Insured Product(s):">
<p>{{insuredProduct}}</p>
</policyItem>

<policyItem2 number="Item 8."><p>
These Declarations and the following Endorsements are made part of this policy: </p>
<p> {{endorsementList1}}
    {{endorsementList2}}
</p>
</policyItem2>

<p>
<b>IN WITNESS WHEREOF, we</b> have caused this Policy and this 
Declarations page to be signed by <b>our</b> President, <b>our</b> Secretary and
<b>our</b> duly authorized representative.
</p>

<signatures/>

<!-- declarations page ends here -->
"""

XMLSAMPLE5 = """
<endorsementHeader number="{{number}}" title="VIRGINIA AMENDATORY ENDORSEMENT" issuedBy="{{issuedBy}}" issuedTo="{{companyName}}"
    policyNo="{{policyNo}}" effDate="{{effectiveDate}}"/>

<spacer length="0.5cm"/>

<p>The Policy is amended as follows:</p>

<spacer length="0.5cm"/>

<p>The first paragraph of <b>ARTICLE IV., HOW A CLAIM IS PAID,</b> Paragraph
<b>B., CALCULATION OF YOUR CLAIM</b>
is deleted in its entirety and replaced with the following:</p>

<spacer length="0.5cm"/>

<policyItem2 number = "B.">
<p>CALCULATION OF <b>YOUR</b> CLAIM</p>

<spacer length="0.5cm"/>

<p><b>We</b> shall pay <b>you</b>
the lesser of the following
<b>A.</b> the Insured Percentage of the
<b>approved customer's uncollected debt,</b>
minus the amount of the Deductible, if any, stated in the Declarations, or
<b>B.</b> the Insured Percentage of the
<b>approved customer's limit,</b>
minus the amount of the Deductible, if any, stated
in the Declarations.
</p>
</policyItem2>

<spacer length="0.5cm"/>

<p>In <b>ARTICLE VI., CONDITIONS,</b>
Paragraph G., CONFORMANCE TO STATUTE is deleted in its entirety.</p>

<spacer length="0.5cm"/>

<p>In <b>ARTICLE VI., CONDITIONS,</b>
Paragraph I., ARBITRATION is deleted in its entirety and replaced with the following:</p>

<spacer length="0.5cm"/>

<policyItem2 number = "I.">
<p>ARBITRATION</p>

<spacer length="0.5cm"/>

<p><b>You</b> must inform <b>us</b> in writing of any dispute you may have regarding coverage 
under this Policy within two (2) years of an <b>uncollected debt.</b>
All disputes, including disputes over coverage, will be submitted to
the American Arbitration Association for resolution.  The dispute will be
handled in accordance with their prevailing rules for commercial disputes. Their decision however,
shall be non-binding on <b>you</b> and on <b>us.</b>
</p>
</policyItem2>

<spacer length="0.5cm"/>
<p>In <b>ARTICLE VI., CONDITIONS,</b>
Paragraph L., REPRESENTATIONS is deleted in its entirety and replaced with the following.</p>

<spacer length="0.5cm"/>

<policyItem2 number = "L.">
<p>CONDITIONS</p>

<spacer length="0.5cm"/>

<p>By accepting this Policy, <b>you</b> agree that the statements made
in the Application and Declarations are true and <b>you</b> also agree
that this Policy, which includes the Application, is issued
in reliance upon the truth of those representations.
Accordingly, this Policy may be voided by <b>us</b> in any case of
fraud, intentional concealment, or misrepresentation of
material fact by <b>you</b>.
</p>
</policyItem2>

<spacer length="0.5cm"/>
<p>All other terms, conditions, and exclusions shall remain unchanged.</p>

<spacer length="0.5cm"/>

<signatures/>

"""

#XMLSAMPLE = XMLSAMPLE5 + XMLSAMPLE4 + XMLSAMPLE3 + XMLSAMPLE2

XMLSAMPLE = XMLSAMPLE2

def example0():
    c = XMLTextConverter()
    c.abbreviate("AIGLogo", "logo")
    c.abbreviate("centered", "c")
    c.abbreviate("bigcentered", "B")
    c.abbreviate("spacer", "s")
    c.abbreviate("signatures", "sign")
    c.abbreviate("Alphalist", "A")
    c.abbreviate("alphalist", "a")
    c.abbreviate("numberlist", "n")
    c.abbreviate("policyItem", "Item")
    c.abbreviate("policyItem2", "N")
    c.abbreviate("element", "li")
    c.contentless("signatures")
    c.contentless("spacer")
    return c
    
def test():
    c = example0()
##    c = XMLTextConverter()
##    c.abbreviate("this", "t")
##    c.abbreviate("funnytag", "f")
##    c.abbreviate("tag", "tg")
    xml = savexml = XMLSAMPLE
    savetext = ""
    print("=== XML at start ===")
    print(xml)
    for i in range(20):
        print("--------------- PASS", i, "--------------")
        text = c.XML2text(xml)
        print("=== TEXT ===", end=' ')
        if text==savetext:
            print("unchanged!")
        else:
            print("changed!")
        # try to analyse the text changes
        stext = text.split("\n")
        ssavetext = savetext.split("\n")
        if len(stext)!=len(ssavetext):
            print("DIFFERING NUMBERS OF LINES -- OLD", len(ssavetext), "NEW", len(stext))
        for (a,b) in map(None, stext, ssavetext):
            if a!=b:
                print("FIRST LINES THAT DIFFER")
                print("NEW:", repr(a))
                print("OLD:", repr(b))
                print("===============")
                break
        print(text)
        xml = c.text2XML(text)
        print("=== XML ===", end=' ')
        if xml==savexml:
            print("unchanged!")
        else:
            print("changed!")
        print(xml)
        savexml = xml
        savetext = text

if __name__=="__main__":
    test()

