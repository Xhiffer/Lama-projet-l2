# -*- coding: utf-8 -*-
from __future__ import unicode_literals
#normaliser for XHTML input
"""
Takes (possibly bad) html chunks and normalises to a valid XHTML subset.

Borrows from BeautifulSoup, and StrippingParser in ActiveState cookbook.

Previous attempts at a normalize function have gone badly as
we ended up with a huge mix of approaches:  search-and-replaces,
Soup, Tidy, regexes and so on.  We end up with them fighting
each other.

Also, we failed to define our intended context clearly enough.
When you want to use someone else's content in RML, typically
you know whether you're using it like this...

<h2>{{attraction.name}}<h2>

..or like this...

<h2>Some heading</h2>
{{possibleMultipleParagraphsHere}}

The HTML Cleaner asks you to specify the target context, and then cleans
and normalizes your code to match.  The full language is as follows:

Block level tags:  p, h1, h2, h3, h4, h5, table, ul, ol, table

Inline tags: i, b, u, br, a, img, sup, sub, strong, em

Others:

  table contains tr/td
  ul/ol contains li   (are nested lists OK?)

Plain text can only appear inside blocks, never between them.

Requirements
============
Accepts 8-bit content.  Assume it's UTF8, but if we get
illegal characters, try a conversion from Latin-1.

Fix naked ampersands and unescaped < or >.  Japanese sometimes
does "<<phrase>>" for emphasis.

Fix case problems in tags (<I> etc).

Close unclosed tags where possible, raise exception for gross
imbalances.

Gather warnings for inspection.

Strip out all but a small, defined set of tags and attributes
"""
import re, sys, os
from xml.sax.saxutils import escape
from rlextra.utils.tagstripper import stripTags
from rlextra.radxml.xmlutils import nakedAmpFix
import collections
from rlextra.utils.unifunc import unifunc
from reportlab.lib.utils import asUnicode, strTypes, isUnicode, isSeq

@unifunc
def cleanBlocks(input, **options):
    """Accept markup as one or more blocks.

    The output of this should be safe for use within a
    <div> or <body> tag in HTML, and also convertible to RML.

    """
    return Cleaner(target='block', **options).process(input)

@unifunc
def cleanInline(input, **options):
    """Accept and normalize markup for use inline.

    The output of this should be safe for use within a
    <p> tag in HTML, and also convertible to RML.
    """
    return Cleaner(target='inline', **options).process(input)

@unifunc
def cleanPlain(input, **options):
    """Remove all tags to output plain text.

    """
    return escape(stripTags(input))

@unifunc
def filterRE(s, r):
    'Substitutes the matches of r in str with an empty string.'
    try:
        sub = r.sub
    except AttributeError:
        return re.sub(r, '', s)
    return sub('', s)

truncated_tag = re.compile('<[^>]{1,100}$')
@unifunc
def fixTruncated(s):
    'Try to remove truncated tags at the end of str.'
    return filterRE(s, truncated_tag)

@unifunc
def truncateHTML(input, maxLines, **options):
    '''
    Truncates html to a maximum of maxlength characters.
    Tags don't count towards the character count.
    Lists, tables and other big blocks get removed completed if
    the character limit is reached inside.
    '''
    return Cleaner(breaksAllowed=False, maxLines=maxLines, **options).process(input)

from reportlab.platypus.paraparser import HTMLParser, known_entities
if sys.version_info>=(3,4):
    from html.parser import unescape as htmlUnescape, tagfind_tolerant, attrfind_tolerant
    __html_parser__ = HTMLParser
    class HTMLParser(__html_parser__):
        def parse_starttag(self, i):
            self.__starttag_text = None
            endpos = self.check_for_whole_start_tag(i)
            if endpos < 0:
                return endpos
            rawdata = self.rawdata
            self.__starttag_text = rawdata[i:endpos]

            # Now parse the data between i+1 and j into a tag and attrs
            attrs = []
            match = tagfind_tolerant.match(rawdata, i+1)
            assert match, 'unexpected call to parse_starttag()'
            k = match.end()
            self.lasttag = tag = match.group(1).lower()
            while k < endpos:
                m = attrfind_tolerant.match(rawdata, k)
                if not m:
                    break
                attrname, rest, attrvalue = m.group(1, 2, 3)
                if not rest:
                    attrvalue = None
                elif attrvalue[:1] == '\'' == attrvalue[-1:] or \
                     attrvalue[:1] == '"' == attrvalue[-1:]:
                    attrvalue = attrvalue[1:-1]
                if attrvalue:
                    attrvalue = self.unescape(attrvalue)
                attrs.append((attrname.lower(), attrvalue))
                k = m.end()

            end = rawdata[k:endpos].strip()
            if end not in (">", "/>"):
                lineno, offset = self.getpos()
                if "\n" in self.__starttag_text:
                    lineno = lineno + self.__starttag_text.count("\n")
                    offset = len(self.__starttag_text) \
                             - self.__starttag_text.rfind("\n")
                else:
                    offset = offset + len(self.__starttag_text)
                self.handle_data(rawdata[i:endpos])
                return endpos
            if end.endswith('/>'):
                # XHTML-style empty tag: <span attr="value" />
                self.handle_startendtag(tag, attrs)
            else:
                self.handle_starttag(tag, attrs)
                if tag in self.CDATA_CONTENT_ELEMENTS:
                    self.set_cdata_mode(tag)
            return endpos
        def unescape(self,s):
            return htmlUnescape(s)

class Cleaner(HTMLParser):

    def __init__(self,
                target="block",
                breaksAllowed=True,
                stripComments=False,
                stripUnknownEntities=True,
                allowImages=True,
                allowTables=True,
                allowAtags=True,
                allowStyleAttr=True, #passed through to para and headings
                allowAlignAttr=True, #passed through to para and headings  
                aHrefTr=None,
                imgSrcTr=None,
                substitutions=[],
                maxLines=None,
                lineWidth=40,
                entities = known_entities.keys(),
                encoding = None,
                ):
        """Initialising defines your language options.
        You can re-use the same parser many times.
        if breaksAllowed, they will be written to output.
        if not, in inline mode they vanish, and in block
        mode they end the block.

        substitutions is a a singleton or list containing
            pat         pat --> ''
            (pat,str)   pat --> str
            callable    c(src) --> src

        pat may be a str or a compiled pattern. These substitutions
        are done before parsing.
        """
        target = self.asUnicode(target)
        self.stripUnknownEntities = stripUnknownEntities
        self.allowImages = allowImages
        self.allowTables = allowTables
        self.allowAtags = allowAtags
        self.aHrefTr = aHrefTr
        self.imgSrcTr = imgSrcTr
        self.encoding = encoding
        self.allowAlignAttr = allowAlignAttr
        self.allowStyleAttr = allowStyleAttr
        self._setupGrammar()

        assert target in (u"block", u"inline"), "unexpected block '%s', must be 'block' or 'inline'" % target
        self.target = target
        HTMLParser.__init__(self,
            **(dict(convert_charrefs=False) if sys.version_info>=(3,4) else {}))
        self.breaksAllowed = breaksAllowed
        self.stripComments = stripComments
        self.entities = set(entities).union(('lt', 'gt', 'amp'))

        #prefix up the substitutions list
        if not isinstance(substitutions,(list,tuple)):
            substitutions = (substitutions,)
        S=[].append
        for s in substitutions:
            if isinstance(s,strTypes):
                s = lambda x,pat=re.compile(asUnicode(s)): pat.sub('',x)
            elif hasattr(s,'sub'):
                s = lambda x,pat=s: pat.sub('',x)
            elif isinstance(s,(tuple,list)) and len(s)==2:
                p=s[0]
                if isinstance(p,str):
                    s = lambda x,pat=re.compile(p),s=s[1]: pat.sub(s,x)
                elif hasattr(p,'sub'):
                    s = lambda x,pat=p,s=s[1]: pat.sub(s,x)
                else:
                    raise ValueError('Invalid value %r in substitions list' % s)
            elif not isinstance(s, collections.Callable):
                raise ValueError('Invalid value %r in substitions list' % s)
            S(s)
        self.substitutions = S.__self__
        self.remainingLines = maxLines
        self.lineWidth = lineWidth
        self.textLength = 0

    def _setupGrammar(self):

        self.DEFAULT_BLOCK_TAG = 'p'    #used to close blocks if nothing else given
        def uniDict(d):
            r = {}
            for k in d:
                r[asUnicode(k)] = d[k]
            return r

        def byName(listOfDicts):
            out = {}
            for d in listOfDicts:
                d = uniDict(d)
                out[d['name']] = d
            return out

        #situations in which a tag can appear.
        self._contextDict = byName([
            dict(name='block', allowedIn=None),  #None=top-level
            dict(name='inline', allowedIn='block'),
            dict(name='table', allowedIn='block'),
            dict(name='list', allowedIn='block'),
            dict(name='li', allowedIn='list'),
            dict(name='tr', allowedIn='table'),
            dict(name='td', allowedIn='tr'),    #no contents for now
            ])
#        if not self.allowTables:
#            del self._contextDict['table']

        for context in self._contextDict.values():
            context['canContain'] = set()

        allowParaAttrs = []
        if self.allowStyleAttr: allowParaAttrs.append('style')
        if self.allowAlignAttr: allowParaAttrs.append('align')

        self._tagDict = byName([
            dict(name='p',context='block', attrs=allowParaAttrs),
            dict(name='h1',context='block', attrs=allowParaAttrs),
            dict(name='h2',context='block', attrs=allowParaAttrs),
            dict(name='h3',context='block', attrs=allowParaAttrs),
            dict(name='h4',context='block', attrs=allowParaAttrs),
            dict(name='h5',context='block', attrs=allowParaAttrs),
            dict(name='h6',context='block', attrs=allowParaAttrs),

            dict(name='strong',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='em',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='i',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='b',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='sup',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='sub',context=('inline', 'li', 'td'), attrs=[]),
            dict(name='br',context=('inline', 'li', 'td'), attrs=[], selfClosing=True),
            dict(name='a',context=('inline', 'li', 'td'), attrs=['href']),

            # force_attrs. These attributes will be added to make sure xhtml validation passes.
            dict(name='img',context=('inline', 'li'), attrs=['src','width','height','alt'], force_attrs=['alt'], selfClosing=True),

            dict(name='table',context='block', attrs=[]),
            dict(name='tr',context='table', attrs=[]),
            dict(name='td',context='tr', attrs=[]),
            dict(name='th',context='tr', attrs=[]),

            dict(name='ul',context='block', attrs=[]),
            dict(name='ol',context='block', attrs=[]),
            dict(name='li',context='list', attrs=[]),
            ])

        # Tags to use to cover naked text up with in the given context
        self._dataCover = uniDict(dict(
            block=(self.DEFAULT_BLOCK_TAG,),
            table=('tr', 'td'),
            tr=('td',),
            list=('li',),
            ))

#        if not self.allowTables:
#            del self._tagDict['table']
#            del self._tagDict['tr']
#            del self._tagDict['td']

        if not self.allowImages:
            del self._tagDict['img']
        if not self.allowAtags:
            del self._tagDict['a']

        #work out in-place the set of tags allowed in each context.

        for tagName,tag in self._tagDict.items():
            if 'selfClosing' not in tag:
                tag['selfClosing'] = False

            contexts = tag['context']
            if not isSeq(contexts):
                contexts = contexts,
            for ctxName in contexts:
                context = self._contextDict.get(ctxName)
                context['canContain'].add(tagName)

        #work out certain useful attributes
        self.valid_tags = set(self._tagDict.keys())
        self.valid_block_tags = self.tagsAllowedInContext('block')
        self.valid_inline_tags = self.tagsAllowedInContext('inline')
        self.valid_other_tags = self.valid_tags - self.valid_block_tags - self.valid_inline_tags

    def allowedAttrs(self, tagName):
        """Return set of allowed attributes for the tag"""
        return self._tagDict[tagName]['attrs']

    def forcedAttrs(self, tagName):
        """Return set of forced attributes for the tag"""
        if 'force_attrs' in self._tagDict[tagName]:
            return self._tagDict[tagName]['force_attrs']
        else:
            return None

    def getContext(self, tag):
        """Return main context for tag

        >>> g = Cleaner()
        >>> eqCheck(g.getContext('i'),'inline')
        >>> eqCheck(g.getContext('li'),'list')
        """
        context = self._tagDict[tag]['context']
        if isSeq(context):
            return context[0]
        return context

    def context(self):
        if self.openTagStack:
            c = self.openTagStack[-1][1]
        else:
            c = self.target == 'block' and 'block' or 'inline'
        return c
    context=property(context)

    def isTagAllowedInContext(self, tag, context):
        """Is the tag allowed here?

        >>> g = Cleaner()
        >>> g.isTagAllowedInContext('b','block')
        False
        >>> g.isTagAllowedInContext('a','inline')
        True
        """
        return context in self._tagDict[tag]['context']

    def tagsAllowedInContext(self, context):
        """Set of tag names allowed in this context

        >>> g = Cleaner()
        >>> eqCheck(g.tagsAllowedInContext('table'),set(['tr']))
        >>> eqCheck(g.tagsAllowedInContext('inline'),set(['em', 'a', 'b', 'sub', 'img', 'i', '', 'br', 'sup', 'strong']))
        """
        #special case - extreme table removal!
        if context == 'table' and not self.allowTables:
            return []

        return self._contextDict[context]['canContain']

    def reset(self):
        "get ready to do some work"
        HTMLParser.reset(self)
        self.buf = []   #holds output
        self.fixes = []  #holds warnings / debug messages / fixups done
        self.openTagStack = []      #checks for balancing
        self._started = False
        self._currentBlockTag = None   #what kind of block tag are we inside?  Usually <p>
        self._justAfterEntity = False   #flag to say if the last thing we saw was an entity.  Used to detect doubled entities in input

    def close(self):
        "Final tidyups"
        HTMLParser.close(self)
        self.cleanupClosingTags()

    def process(self, markup):
        "The main loop - call this with your markup"
        markup = self.asUnicode(markup)
        for s in self.substitutions:
            markup=s(markup)
        markup = re.sub('<([A-Za-z]+\\w*)/>', '<\\1 />', markup)
        markup = nakedAmpFix(markup.strip())
        self.reset()
        markup = self.asUnicode(markup)
        self.feed(markup)
        self.close()
        r = ''.join(self.buf)
        return r.encode(self.encoding) if self.encoding else r

    def dump(self):
        print(''.join(self.buf))

    def asUnicode(self, markup):
        """convert to unicode"""
        #TODO
        if not isUnicode(markup):
            try:
                markup = markup.decode('utf8', 'strict')
            except UnicodeDecodeError:
                #assume windows encoding
                markup = markup.decode('cp1252', 'replace')
        return markup

    def writeStartTag(self, tag, attrs={}):
        """Helper to do what it says.  Called to write a tag to output.

        Never write your own tags to output; instead call this.  This will
        maintain a stack and ensure they are balanced. It also sets the
        mode every time for you."""
        #for table removal, we just don't write it out. It's easier
        #to have writeStartTag called (from several places) because we
        #need to keep track of the fact that we are in a table-to-be-removed.
        if self.remainingLines != None and self.remainingLines <= 0:
            return
        if tag == 'table' and not self.allowTables:
            self.openTagStack.append((tag,'table'))
            return

        #self.dump()
        #prefilter to remove all block tags in inline markup

        if tag not in self.valid_inline_tags:
            if self.target == 'inline':
                return

        adict = dict(attrs)

        if tag == 'img' and self.imgSrcTr:
            if isinstance(self.imgSrcTr, str):
                p = os.path.join(self.imgSrcTr, os.path.split(adict['src'])[-1])
                p = p.replace('\\', '/')
                adict['src'] = p
            else:
                adict['src'] = self.imgSrcTr(adict['src'])

        if tag == 'a' and self.aHrefTr:
            href = adict['href']
            if isinstance(self.aHrefTr, str):
                if not (href.startswith('http://') or href.startswith('https://')):
                    adict['href'] = self.aHrefTr.rstrip('/') + '/' + href.lstrip('/')
            else:
                adict['href'] = self.aHrefTr(href)

        attrs = [ (k, adict[k]) for k, _ in attrs ]

        allowedAttrs = self.allowedAttrs(tag)
        forcedAttrs = self.forcedAttrs(tag)
        selfClosing = self._tagDict[tag]['selfClosing']
        #if selfClosing: print "found self-closing tag %s" % tag

        #rebuild the tag as a piece of text
        tagBits = ['<']
        tagBits.append(tag)
        for k, v in attrs:
            v = self.asUnicode(v)
            if k in allowedAttrs:
                if k[0:2].lower() != 'on' and v[0:10].lower() != 'javascript':
                    tagBits.append(' %s="%s"' % (k, v))

        # If there are any forced attributes
        if forcedAttrs and len(forcedAttrs) > 0:
            tag_attrs = [k for k,v in attrs]
            for k in forcedAttrs:
                if k not in tag_attrs:
                    tagBits.append(' %s=""'% k)
        if selfClosing:
            tagBits.append('/>')
        else:
            tagBits.append('>')
        tagText = ''.join(tagBits)

        self.buf.append(tagText)

        #and put it on the stack....
        if not selfClosing:
            context = self.context  #current context
            #if block, remember how to close
            if context == 'block':
                self._currentBlockTag = (tag,'block')
            #set the mode
            if tag == 'table':
                ncontext = 'table'
            elif tag == 'tr':
                ncontext = 'tr'
            elif tag in ('td', 'th'):
                ncontext = 'td'
            elif tag in ('ul', 'ol'):
                ncontext = 'list'
            elif tag == 'li':
                ncontext = 'li'
            else:
                #block and inline always lead to inline
                ncontext = 'inline'
            self.openTagStack.append((tag,ncontext))

    def writeEndTag(self, tag):
        """Close the tag, but check for nesting errors.

        Never write to the buffer directly; this keeps the stack
        and mode organised."""
        if not self.enoughSpace(tag):
            return
        try:
            lastTag,lastContext = self.openTagStack.pop()
        except:
            print(self.openTagStack)
            raise
        if tag == 'table':
            if not self.allowTables:
                return
            if not self.currentTableHasContent():
                #remove everything inside the present table
                while True:
                    popped = self.buf.pop()
                    if popped.startswith('<table'):
                        break
                return

        #prefilter to remove all block tags in inline markup
        if self.target == 'inline':
            if tag not in self.valid_inline_tags:
                return
        if lastTag != tag:
            raise ValueError("stack is messed up trying to close %s; current open tag was %s" % (tag, lastTag))
        self.buf.append('</%s>' % tag)

    def pendingTag(self):
        "What tag is waiting?"
        try:
            return self.openTagStack[-1][0]
        except IndexError:
            return None

    def atStart(self):
        return (len(self.buf) == 0)

    def discardTag(self, tag):
        'Remove everything inside this tag from the stack and buffer'
        while self.openTagStack:
            ctag,ctxt = self.openTagStack.pop()
            n = len(self.buf) - 1
            while n:
                if self.buf[n].startswith('<' + ctag):
                    break
                n -= 1
            self.buf = self.buf[:n]
            if ctag == tag:
                return


    def currentTableHasContent(self):
        'backtrack to last <table> and see if we have any actual non-whitespace content'
        pointer = -1
        item = self.buf[pointer]
        while not item.startswith('<table'):
            #print pointer, item
            pointer -= 1
            item = self.buf[pointer]
            if not item.startswith('<'):
                if item.strip():
                    return True
        return False

    def enoughSpace(self, tag):
        '''
        Tries to determine if the text in the current tag will fit on the remaining number of lines.
        If it does, this method returns True.
        If not, it will discard the text of the current tag and return False.
        '''
        if self.remainingLines == None:
            return True
        if tag == 'p':
            lines = float(self.textLength) / self.lineWidth
        elif tag == 'li':
            # Count 3 characters for the bullet point
            lines = float(self.textLength) / (self.lineWidth - 3)
        else:
            return True
        import math
        lines = int(math.ceil(lines))
        self.remainingLines -= lines
        if self.remainingLines >= 0:
            self.textLength = 0
            return True
        self.discardTag(tag)
        return False

    def writeData(self, text):
        "Used to write out non-tag content"
        if self.remainingLines != None and self.remainingLines <= 0:
            return
        self.textLength += len(text)
        self.buf.append(text)

    def closeCurrentBlock(self):
        """This is used to close any pending inline tags, whenever
        we hit a new block start,  Healthy closing never calls this."""
        if self.atStart():
            return
        if self.target == 'inline':
            return #write nothing
        tag = self.pendingTag()
        if tag is not None:
            while tag in self.valid_inline_tags:
                self.writeEndTag(tag)
                tag = self.pendingTag()
        assert self._currentBlockTag is not None

        #if there are any more end-tags in the stack, chuck them.
        self.openTagStack = [self._currentBlockTag]
        self.writeEndTag(self._currentBlockTag[0])

    def tagInStack(self,tag):
        stack = self.openTagStack
        x = len(stack)
        while x:
            x -= 1
            if tag==stack[x][0]: return True
        return False

    def handle_data(self, data):
        data = data.replace('<', '&lt;').replace('>', '&gt;')

        if not data.strip():
            self.writeData(data)
            return

        if not self.allowTables:
            if self.tagInStack('table'):
                return

        #are we in the right mode?
        tags = self._dataCover.get(self.context,[])
        for t in tags:
            self.writeStartTag(t)

        self.writeData(data)

    def handle_comment(self, name):
        if not self.stripComments:
            self.buf.append('<!--' + self.asUnicode(name) + '-->')

    def handle_entityref(self, name):
        "Handles a named entity.  "
        if self.stripUnknownEntities and not name in self.entities:
            return ''
        self.handle_data('&%s;' % name)

    def handle_charref(self,name):
        self.handle_data('&#%s;' % name)

    def handle_starttag(self, tag, attrs):
        """ Delete all tags except for legal ones, and strip some obvious javascript

        The 'state machine' choices are all here, and in unknown_endtag. At any point,
        we know the current context, and the next tag which has its own context. If
        the next tag is expected, fine.  If not, we need to handle each state
        transition intelligently.

        """
        tag = tag.lower()

        #remove ANYTHING inside a table, if removing tables.
        if not self.allowTables:
            if self.tagInStack('table'):
                return

        if tag=='br':
            """Handles the <br/> tag.

            Called directly by sgmllib instead of unknown_starttag,
            because it's a singleton tag.  What we do depends on whether
            (a) breaks are allowed in this normalisation, and
            (b) we are inside a block or between them.

            As presently implemented, with breaksAllowed=False...
               <p>one<br/>two</p>   ->  <p>one</p><p>two</p>

            ..and multiple <br> tags beyond the first will create
            extra empty paragraphs.
            """
            if self.remainingLines != None and self.remainingLines <= 0:
                return

            if self.breaksAllowed:
                if self.isTagAllowedInContext('br', self.context):
                    self.buf.append(u"<br/>")
                    if self.remainingLines != None:
                        self.remainingLines -= 1
            else:
                if self.target == 'block':
                    if self.context == 'inline':
                        self.closeCurrentBlock()
                    elif self.context == 'block':
                        #give them an empty para for each extra <br> they added
                        self.writeStartTag(self.DEFAULT_BLOCK_TAG)
                        self.writeEndTag(self.DEFAULT_BLOCK_TAG)
                else:
                    self.buf.append(' ')  #if they had two lines in the input,
                    #at least a space should separate them in the output.
        elif tag in self.valid_tags:
            context = self.context
            if tag in self.tagsAllowedInContext(context):
                #expected, write it out.  The writer will filter out any unexpected attributes.
                self.writeStartTag(tag, attrs)
            else:
                #Unexpected.  Each context combination has its own rules.
                #We have 6 contexts so 36 combinations, but in most we
                #just want to ignore the tag.
                nextContext = self.getContext(tag)

                if context == 'inline':
                    if nextContext == 'block':
                        self.closeCurrentBlock()
                        self.writeStartTag(tag, attrs)
                    else:
                        pass   #if we get a naked tr, td, li, we'll just ignore it.
                elif context == 'block':
                    if nextContext == 'inline':  #e.g. <i> at start of document
                        self.writeStartTag(self.DEFAULT_BLOCK_TAG)
                        self.writeStartTag(tag, attrs)
                    elif nextContext in ('table', 'tr', 'list'):
                        #very out-of-context tag, ignore it. e.g. <p><tr>
                        pass
                elif context == 'table':
                    #anything but a tr or td is disallowed
                    if nextContext == 'tr':  #i.e. tag is a td
                        #they forgot the tr, repair it
                        self.writeStartTag('tr', {})
                        self.writeStartTag(tag, attrs)
                    else:
                        pass
                elif context == 'tr':
                    #expected a td, anything higher up means we need to close
                    if nextContext == 'table':
                        #got a tr - close the current tr
                        self.writeEndTag('tr')
                        self.writeStartTag(tag, attrs)
                    elif nextContext == 'block':
                        #close the whole table
                        self.writeEndTag('tr')
                        self.writeEndTag('table')
                        self.writeStartTag(tag, attrs)
                    else:
                        pass
                elif context == 'td':
                    #brutal for now, no tags allowed here yet, but
                    #should be like inline.
                    if nextContext == 'table':
                        #got a tr - close the td
                        self.writeEndTag('td')
                        self.writeEndTag('tr')
                        self.writeStartTag(tag, attrs)
                    #elif nextContext == 'block':
                    #    pass
                    else:
                        pass
                elif context == 'list':  #tag is li
                    if nextContext == 'list':   #got another li, close the last li
                        self.writeEndTag('li')
                        self.writeStartTag(tag, attrs)
                    elif nextContext == 'block':
                        self.closeCurrentBlock()
                        self.writeStartTag(tag, attrs)
                    else:
                        pass
                elif context == 'li':   #tag is li
                    if nextContext == 'list':   #got another li, close the last li
                        self.writeEndTag('li')
                        self.writeStartTag(tag, attrs)
                    elif nextContext == 'block':
                        self.writeEndTag('li')
                        self.closeCurrentBlock()
                        self.writeStartTag(tag, attrs)
                    else:
                        pass
                else:
                    raise ValueError("unexpected context '%s'" % context)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in self.valid_tags:
            pending = self.pendingTag()
            if tag == pending:
                #all is wonderful, close it
                self.writeEndTag(tag)
            else:
                #normally, we just ignore unexpected end tags.
                #the stack will be closed at the end.  However
                #if we get a </table>, </ul> etc, it may make
                #sense to close.
                if tag == 'tr':
                    if pending == 'td':
                        #close it
                        self.writeEndTag('td')
                        self.writeEndTag(tag)
                elif tag in ('ul','ol'):
                    if pending == 'li':
                        self.writeEndTag('li')
                        self.writeEndTag(tag)
                elif tag == 'table':
                    if pending == 'td':
                        self.writeEndTag('td')
                        self.writeEndTag('tr')
                        self.writeEndTag(tag)
                    elif pending == 'tr':
                        self.writeEndTag('tr')
                        self.writeEndTag(tag)
        else:
            self.fixes.append("Ignoring unexpected end tag %s" % tag)

    def cleanupClosingTags(self):
        """ Append any missing closing tags. Called at end."""
        while self.openTagStack:
            tag = self.pendingTag()
            if not self.enoughSpace(tag):
                continue
            self.openTagStack.pop()
            #special case for <table></table> which we want to discard
            if tag == 'table' and self.buf[-1].startswith('<table'):
                self.buf.pop()
            else:
                self.buf.append(u"</%s>" % tag)
            self.fixes.append("appended missing end tag </%s>" % tag)

    def unescape(self,s):
        '''overrides entity handling in attributeValues'''
        return s

def test(dummy=None,verbose=False,gentests=False):
    #encoding detection tests
    _testCp1252 = b'copyright \xa9 trademark \x99 registered \xae ReportLab! Ol\xe9!'
    _testUni = _testCp1252.decode('cp1252')
    _testUTF8 = _testUni.encode('utf-8')

    TEST_CASES = [
    #list of (testname, mode, options, input, output) quads
    ('empty string', 'inline', None, "", ""),
    ('plain text not modified', 'inline', None, "Hello world", "Hello world"),
    ('simple ampersand preserved', 'inline', None, "Smith &amp; Jones", "Smith &amp; Jones"),

    #encoding detection
    ('utf8 OK', 'inline', None, _testUTF8, _testUTF8),
    ('cp1252 converted to utf8', 'inline', None, _testCp1252, _testUTF8),

    ('naked ampersand fixed', 'inline', None, "Smith & Jones", "Smith &amp; Jones"),
    ('respects trendy quotes', 'inline', None, "the &lt;&lt;ultra&gt;&gt; bar", "the &lt;&lt;ultra&gt;&gt; bar"),

    #tag processing
    ('respects tags and expected attributes', 'inline', None,
         'Click <a href="/help" alt="x">here</a> for help', 'Click <a href="/help">here</a> for help'),

    ('singleton <br> fixed', 'inline', None, 'line<br>two', 'line<br/>two'),
    ('cases fixed', 'inline', None, '<I>foo</i>', '<i>foo</i>'),
    ('superscripts and subscripts', 'inline', None, 'Normal<sub>sub</sub>m<sup>2</sup>', 'Normal<sub>sub</sub>m<sup>2</sup>'),

    #basic nesting repairs - pretty dumb algorithm, it ignores any unexpected end tags and closes any leftovers at the end.
    # a smarter parser might close on any 'end block' event.
    ('nesting test 1', 'inline', None, '<b>foo</i>', '<b>foo</b>'),
    ('nesting test 2', 'inline', None, '<b><i>foo</i>', '<b><i>foo</i></b>'),
    ('nesting test 3', 'block', None, '<p><b>foo', '<p><b>foo</b></p>'),

    #input cp1252 and smart quotes, see if it guesses - to be completed.

    #inline converted to block if not started off.
    ('block to inline', 'inline', None, '<p>foo</p>', 'foo'),
    ('inline to block', 'block', None, 'foo', '<p>foo</p>'),
    ('block respected', 'block', None, '<h1>foo</h1>', '<h1>foo</h1>'),
    ('blocks finished at end of document', 'block', None, '<h1>foo', '<h1>foo</h1>'),
    ('block finished off with correct tag', 'block', None, '<h1>foo<p>text</p>', '<h1>foo</h1><p>text</p>'),

    #detect and wrap text between / outside blocks
    ('naked text 1', 'block', None, 'first<p>second</p>', '<p>first</p><p>second</p>'),
    ('naked text 2', 'block', None, 'first<p>second</p>three', '<p>first</p><p>second</p><p>three</p>'),

    #br tag handling.  May or may not be allowed depending on mode.
    ('breaks rewritten with trailing slash', 'inline', None, 'one<br>two<br>three', 'one<br/>two<br/>three'),
    ('fixes expanded break', 'inline', None, 'one<br>two</br>three', 'one<br/>twothree'),

    ('breaks become paras in block', 'block', {'breaksAllowed':False}, 'one<br>two<br>three', '<p>one</p><p>two</p><p>three</p>'),
    ('breaks vanish inline', 'inline', {'breaksAllowed':False}, 'one<br>two<br>three', 'one two three'),
    ('breaks inside p preserved', 'block', None, '<p>Apple<br/><br/>Banana</p>', '<p>Apple<br/><br/>Banana</p>'),
    ('breaks with space inside p preserved', 'block', None, '<p>Apple<br /><br />Banana</p>', '<p>Apple<br/><br/>Banana</p>'),

    #tables
    ('tables start a block', 'block', {'breaksAllowed':False},
        'hello<br>line two<table>oooo</table>stuff after',
        '<p>hello</p><p>line two</p><table><tr><td>oooo</td></tr></table><p>stuff after</p>'),

    ('tables with tr and td', 'block', {'breaksAllowed':False},
        'hello<br>line two<table><tr><td>Hello</td></tr><tr><td>Dick & jane</td></tr></table>stuff after',
        '<p>hello</p><p>line two</p><table><tr><td>Hello</td></tr><tr><td>Dick &amp; jane</td></tr></table><p>stuff after</p>'),

    ('unfinished table gets closed', 'block', None, '<table><tr><td>Stuff', '<table><tr><td>Stuff</td></tr></table>'),
    ('unfinished table gets closed 2', 'block', None, '<table><tr><td>Stuff</td><p>more</p>', '<table><tr><td>Stuff</td></tr></table><p>more</p>'),

    ('tables with tr and td bad block', 'block', {'breaksAllowed':False},
        'hello<br>line two<table><tr><td>Hello</td><tr><td>Dick & jane</table>stuff after',
        '<p>hello</p><p>line two</p><table><tr><td>Hello</td></tr><tr><td>Dick &amp; jane</td></tr></table><p>stuff after</p>'),

    #lists
    ('list copied OK','block',None, '<ul><li>one</li><li>two</li></ul>','<ul><li>one</li><li>two</li></ul>'),
    ('li tags closed early','block',None, '<ul><li>one<li>two</ul>','<ul><li>one</li><li>two</li></ul>'),
    ('li tags closed early 2','block',None, '<ul><li>one<li>two</ul>end','<ul><li>one</li><li>two</li></ul><p>end</p>'),
    ('blocks in ul','block',None, '<ul><p>end</p>', '<ul></ul><p>end</p>'),

    ('Bad list html','block',None, '<li>one</li><ul><li>two</li></ul>','<p>one</p><ul><li>two</li></ul>'),
    ('Bad table html','block',None, '<td>one</td><table><tr>two</tr></table>','<p>one</p><table><tr><td>two</td></tr></table>'),

    ('Html with unicode characters', 'block', None, """  <p>Refuge luxueux et original située à 50 km à l’est de Mahé, Frégate Island Private se compose de 16 villas privées.  La règle qui prévaut dans l’île est la préservation et la protection d’un environnement naturel unique.  Dans ce lieu harmonieusement préservé, l’hôtel propose un somptueux décor et des installations luxueuses qui vous permettront de vivre à l’écart du monde et de jouir d’un repos complet dans une totale intimité.  La beauté naturelle de l’île, une cuisine gastronomique délicieuse, un large éventail d’activités sportives et de loisirs, deux piscines (dont une de 25 mètres pour ceux qui souhaitent faire des longueurs!): tout est organisé pour répondre à vos attentes les plus exigeantes.  Sont également accessibles le “Castaway Kids Club” et “The Rock Spa”.</p>""", """<p>Refuge luxueux et original située à 50 km à l’est de Mahé, Frégate Island Private se compose de 16 villas privées.  La règle qui prévaut dans l’île est la préservation et la protection d’un environnement naturel unique.  Dans ce lieu harmonieusement préservé, l’hôtel propose un somptueux décor et des installations luxueuses qui vous permettront de vivre à l’écart du monde et de jouir d’un repos complet dans une totale intimité.  La beauté naturelle de l’île, une cuisine gastronomique délicieuse, un large éventail d’activités sportives et de loisirs, deux piscines (dont une de 25 mètres pour ceux qui souhaitent faire des longueurs!): tout est organisé pour répondre à vos attentes les plus exigeantes.  Sont également accessibles le “Castaway Kids Club” et “The Rock Spa”.</p>"""),
    ('Para with anchor tags', 'block', None, '<p><a href="http://www.yahoo.com">Yahoo</a></p>', '<p><a href="http://www.yahoo.com">Yahoo</a></p>'),

    #Entity
    ('Entities remain untouched', 'block', None, '<p>&copy;</p>', '<p>&copy;</p>'),
    ('Entities remain untouched big', 'block', None,
    '<p><img src="dick &copy; jane" alt=""/></p>',
    '<p><img src="dick &copy; jane" alt=""/></p>',
    ),
    ('Valid entities', 'block', None, '<p>Apple&sup2;</p>', '<p>Apple&sup2;</p>'),
    ('Unknown entities', 'block', None, '<p>Apple &unknownent;</p>', '<p>Apple </p>'),
    ('Dot not strip unknown entities', 'block', {'stripUnknownEntities': False}, '<p>Apple &unknownent;</p>', '<p>Apple &unknownent;</p>'),

    #images
    ('image inside block', 'block', None, '<img src="foo.jpg"/>', '<p><img src="foo.jpg" alt=""/></p>'),
    ('image starts new block', 'block', None, 'before<img src="foo.jpg"/>after', '<p>before<img src="foo.jpg" alt=""/>after</p>'),
    ('alt attribute gets added to img', 'block', None, '<p><img src="apple.jpg"/></p>', '<p><img src="apple.jpg" alt=""/></p>'),
    ('old alt attribute will not be touched', 'block', None, '<p><img src="apple.jpg" alt="happy"/></p>', '<p><img src="apple.jpg" alt="happy"/></p>'),
    ('html with images', 'block', None,
    """Go& There can be yacht.<br /><br />Seychelles n<br /><strong>Sunday:</strong><br />We proposMah&eacute;, principal iort.<img height="225" alt="Sailing in Seychelles - Copyright Koos van der Lende" hspace="5" width="150" align="right" vspace="5" src="/media/Sailbad.jpg" /><br /><br />This imposing, verdant granite island whose topmost peak towers to over 900m boasts over 65 beaches <p><img height="134" alt="Sailing in Seychelles - Copyright Sunsail / Jonathan Smith" hspace="5" width="200" align="right" vspace="5" src="/media/Sunsail_of_Sisters_Island.jpg" /></p><br /></strong>It will not be lon""",
    """<p>Go&amp; There can be yacht.<br/><br/>Seychelles n<br/><strong>Sunday:</strong><br/>We proposMah&eacute;, principal iort.<img height="225" alt="Sailing in Seychelles - Copyright Koos van der Lende" width="150" src="/media/Sailbad.jpg"/><br/><br/>This imposing, verdant granite island whose topmost peak towers to over 900m boasts over 65 beaches </p><p><img height="134" alt="Sailing in Seychelles - Copyright Sunsail / Jonathan Smith" width="200" src="/media/Sunsail_of_Sisters_Island.jpg"/></p><p>It will not be lon</p>"""
    ),
    ('comments would be preserved', 'block', None,
    """<p><!-- page_break --></p>""",
    """<p><!-- page_break --></p>"""
    ),
    ('paras with break', 'block', None,
    """sajdfdskjfhsk <br/> <br/>asfdfkshkfjsjfks""",
    """<p>sajdfdskjfhsk <br/> <br/>asfdfkshkfjsjfks</p>"""
    ),
    ('Complex para with breaks', 'block', None,
    """<p>Il y a trois langues officielles aux Seychelles: le Cr&#233;ole (patois bas&#233; sur le Fran&#231;ais), l&#8217;Anglais et le Fran&#231;ais. &#160;Beaucoup de seychellois parlent &#233;galement couramment l&#8217;Italien et l&#8217;Allemand.<br /><br />Voici quelques expressions cr&#233;oles bien utiles:</p><table class="btxt" cellspacing="2" cellpadding="2" align="left" border="0"><tbody><tr class="tablerow"><td class="tableheader" width="160">Fran&#231;ais</td><td class="tableheader" width="160">Creole</td></tr><tr bgcolor="#eeeeee"><td width="160">Bonjour</td><td width="160">Bonzour</td></tr><tr bgcolor="#eeeeee"><td width="160">Au revoir</td><td width="160">Orevwar</td></tr><tr bgcolor="#eeeeee"><td width="160">Comment allez vous?</td><td width="160">Ki dir?</td></tr><tr bgcolor="#eeeeee"><td width="160">Merci</td><td width="160">Mersi</td></tr><tr bgcolor="#eeeeee"><td width="160">O&#249;?</td><td width="160">Kote?</td></tr><tr bgcolor="#eeeeee"><td width="160">S&#8217;il vous pla&#206;t</td><td width="160">Silvouple</td></tr><tr bgcolor="#eeeeee"><td width="160">Non</td><td width="160">Non</td></tr><tr bgcolor="#eeeeee"><td width="160">Oui</td><td width="160">Wi</td></tr><tr bgcolor="#eeeeee"><td width="160">Je ne comprends pas</td><td width="160">Mon pa konpran</td></tr><tr bgcolor="#eeeeee"><td width="160">&#231;a me pla&#206;t</td><td width="160">Mon kontan</td></tr><tr bgcolor="#eeeeee"><td width="160">Comment &#231;a va?</td><td width="160">Konman sava?</td></tr><tr bgcolor="#eeeeee"><td width="160">Qu&#8217;est ce que c&#8217;est?</td><td width="160">Kisisa?</td></tr></tbody></table>""",
    """<p>Il y a trois langues officielles aux Seychelles: le Cr&#233;ole (patois bas&#233; sur le Fran&#231;ais), l&#8217;Anglais et le Fran&#231;ais. &#160;Beaucoup de seychellois parlent &#233;galement couramment l&#8217;Italien et l&#8217;Allemand.<br/><br/>Voici quelques expressions cr&#233;oles bien utiles:</p><table><tr><td>Fran&#231;ais</td><td>Creole</td></tr><tr><td>Bonjour</td><td>Bonzour</td></tr><tr><td>Au revoir</td><td>Orevwar</td></tr><tr><td>Comment allez vous?</td><td>Ki dir?</td></tr><tr><td>Merci</td><td>Mersi</td></tr><tr><td>O&#249;?</td><td>Kote?</td></tr><tr><td>S&#8217;il vous pla&#206;t</td><td>Silvouple</td></tr><tr><td>Non</td><td>Non</td></tr><tr><td>Oui</td><td>Wi</td></tr><tr><td>Je ne comprends pas</td><td>Mon pa konpran</td></tr><tr><td>&#231;a me pla&#206;t</td><td>Mon kontan</td></tr><tr><td>Comment &#231;a va?</td><td>Konman sava?</td></tr><tr><td>Qu&#8217;est ce que c&#8217;est?</td><td>Kisisa?</td></tr></table>"""
    ),
    ('Para with one break gets split when breaks not allowed', 'block', {'breaksAllowed' : False},
    """<p>Part one<br />Part two</p>""",
    """<p>Part one</p><p>Part two</p>"""
    ),

    ('Para with double <br/> when breaks not allowed', 'block', {'breaksAllowed' : False},
    """<p>Part one<br /><br />Part two</p>""",
    """<p>Part one</p><p></p><p>Part two</p>"""
    ),
    ('Para with treble <br/> when breaks not allowed', 'block', {'breaksAllowed' : False},
    """<p>Part one<br /><br /><br />Part two</p>""",
    """<p>Part one</p><p></p><p></p><p>Part two</p>"""
    ),

    ('Entity examples', 'inline', None,
    '&amp;', '&amp;'
    ),
    ('Entity examples1', 'inline', None,
    '&eacute;', '&eacute;'
    ),
    ('Preserves numeric entity', 'inline', None,
    '&#233;', '&#233;'
    ),
    ('div  gets converted to para', 'block', None,
    """<div id="hello">fashd kjah asfh aasfda</div>""",
    """<p>fashd kjah asfh aasfda</p>"""
    ),
    #if allowTables is false, we should remove anything which
    #appeared in a table tag
    ('removes tables', 'block', {'allowTables':False},
    """<p>before table</p><table><tr><td>cell one</td><td>cell two</td></tr></table><p>after table</p>""",
    """<p>before table</p><p>after table</p>""",
    ),
    ('removes images', 'block', {'allowImages':False},
    """<p>image<img src="foo" alt="">gone</p>""",
    """<p>imagegone</p>""",
    ),
    ('removes inline images', 'inline', {'allowImages':False},
    """<img src="foo" alt="">""",
    """""",
    ),
    ('truncate html', 'block', {'maxLines': 3},
    '<p>testinnng<ul><li>i1</li><li>i2<table><tr>hello<p>you<b>litte<i>b..</table><p>ok ok</p>',
    '<p>testinnng</p><ul><li>i1</li><li>i2</li></ul>',
    ),
    ('truncate html 2', 'block', {'maxLines': 2},
    '<p>testinnng this text which should wrap on two lines</p>this should be discareded</p>',
    '<p>testinnng this text which should wrap on two lines</p>',
    ),
    ('truncate html 3', 'block', {'maxLines': 3},
    '<ul><li>testinnng this text which should wrap on two lines</li><li>one line</li><li>should not appear',
    '<ul><li>testinnng this text which should wrap on two lines</li><li>one line</li></ul>',
    ),
    ('truncate html 4', 'block', {'maxLines': 2, 'breaksAllowed': False},
    '<p>a<br>b<br>c<br>d<br>e<br>f<br>g<br>h<br>i',
    '<p>a</p><p>b</p>',
    ),
    ('truncate html 5', 'block', {'maxLines': 4, 'lineWidth': 5},
    '<p>test test test test</p><p>ok</p>',
    '<p>test test test test</p>',
    ),
    ('truncate html 6', 'block', {'maxLines': 4, 'lineWidth': 5},
    'test test test test ok',
    '',
    ),
    ('remove empty tables', 'block', {},
    '<p>ohooo<table></table>',
    '<p>ohooo</p>',
    ),
    ('remove empty tables 2', 'block', {},
    '<table cellspacing="0" cellpadding="0" border="0"></table><p>Fifteen minutes from Heathrow and linked to Paddington station by footbridge, the Hilton London Paddington hotel has 18 meeting rooms for 2-350, a <strong>business centre</strong> and <strong>Executive Lounge</strong>.</p>',
    '<p>Fifteen minutes from Heathrow and linked to Paddington station by footbridge, the Hilton London Paddington hotel has 18 meeting rooms for 2-350, a <strong>business centre</strong> and <strong>Executive Lounge</strong>.</p>',
    ),
    ('handle <a> inside <li>','block',{'maxLines':14, 'lineWidth':40},
    '<ul><li><a href="http://www.reportlab.com">link</a>after the link</li><li>another listitem</li></ul>',
    '<ul><li><a href="http://www.reportlab.com">link</a>after the link</li><li>another listitem</li></ul>',
    ),
    ('handle <p> inside <p>','block',{'maxLines':14, 'lineWidth':40},
    '<p>aaaa <img src="img1">bbbb<p>cccc<img src="img2"> dddd</p> eeeee</p>',
    '<p>aaaa <img src="img1" alt=""/>bbbb</p><p>cccc<img src="img2" alt=""/> dddd</p><p> eeeee</p>',
    ),
    ('handle <p> inside <p>','block',{'maxLines':14, 'lineWidth':40},
    '<img src="img0"><p>aaaa <img src="img1">bbbb<p>cccc<img src="img2"> dddd</p> eeeee</p>',
    '<p><img src="img0" alt=""/></p><p>aaaa <img src="img1" alt=""/>bbbb</p><p>cccc<img src="img2" alt=""/> dddd</p><p> eeeee</p>',
    ),
    ('a <td> contains text only',
    'block',
    {},
    '<table><tr><td>hello</td></tr></table>',
    '<table><tr><td>hello</td></tr></table>',
    ),
    ('a <td> contains img, img is removed',
    'block',
    {},
    '<table><tr><td>preimage text<img src="" />postimage text</td></tr></table>',
    '<table><tr><td>preimage textpostimage text</td></tr></table>',
    ),
    ('a <td> contains p, p is removed',
    'block',
    {},
    '<table><tr><td>pretext <p>paragrapgh text</p> posttext</td></tr></table>',
    '<table><tr><td>pretext paragrapgh text posttext</td></tr></table>',
    ),
    ('a <td> contains p, p contains img, only text should be left',
    'block',
    {},
    '<table><tr><td><p>paragrapgh <img src=""/>text</p></td></tr></table>',
    '<table><tr><td>paragrapgh text</td></tr></table>',
    ),
    #do we need this test and, if so, what's the test case?  All real world examples
    #seem to become something different after further processing.
    ('html self closing tags should all be converted into xhtml self closing tags <br />',
    'block',
    {},
    '',  #todo
    '', #todo
    ),

    ('tables should be discarded if they have no printable content',
    'block',
    {},
    '<table><tr><td></td></tr></table>' + 
    '<table><tr></tr></table>' + 
    '<table><tr>\n</tr></table>' +    #whitespace only
    '<table><tr/></table>' + 
    '<table><tr><td/></tr></table>' + 
    '<table/>'  
    ,
    '',
    ),

    ('tables with whitespace',
    'block',
    {},
    '<table>x</table>',
    '<table><tr><td>x</td></tr></table>',
    ),

    ('allowStyleAttr=False test',
    'block',
    {'allowStyleAttr':False},
    '<p style="margin-left:18px">hello</p>',
    '<p>hello</p>',
    ),

    ('allowStyleAttr on by default',
    'block',
    {},
    '<p style="margin-left:18px">hello</p>',
    '<p style="margin-left:18px">hello</p>',
    ),

    ]
    if gentests:
        from unittest import TestCase, FunctionTestCase
        R = [].append
    for test in TEST_CASES:
        def subtest(test=test):
            testName, mode, options, input, expected = test
            if verbose:
                print('testing ', testName)
            #options may be a dict
            if options is None:
                options = {}

            c = Cleaner(target=mode, **options)
            out = c.process(input)
            expected = c.asUnicode(expected)
            if out != expected or (c.fixes and verbose):
                sys.stdout.write(testName+'...')
            if out != expected:
                msg = 'failed.  \n  Input\n    %s\n  Expected\n    %s\n  Got\n    %s\n' % (input, expected, out)
                if gentests:
                    raise TestCase.failureException(msg)
                else:
                    print(msg)
            if c.fixes:
                if verbose:
                    print('  fixes applied:')
                    for fix in c.fixes:
                        print('    %s' % fix)
                    print()
        if gentests:
            R(FunctionTestCase(subtest))
        else:
            subtest()
    import doctest
    from reportlab.lib.testutils import eqCheck
    from reportlab.lib.utils import rl_add_builtins
    rl_add_builtins(eqCheck=eqCheck)
    if not gentests:
        doctest.testmod()
    else:
        R(doctest.DocTestSuite())
        return R.__self__

if __name__=='__main__':
    args = sys.argv[:]
    verbose = ('-v' in args) or ('--verbose' in args)
    test(verbose=verbose)
