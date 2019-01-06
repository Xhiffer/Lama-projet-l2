from __future__ import print_function
MatchFail = "MatchFail"
import string

### note this parsing stuff is fairly general purpose and should be in own module.

class ParseNode:
    """match a literal string"""
    verbose = 0
    def __init__(self, s, call=None):
        self.matchstring = s
        self.call = call
    def __repr__(self):
        return "m(%s)" % self.matchstring

    def transform(self, match):
        c = self.call
        if c:
            return c(match)
        return match

    def match(self, text, index=0, grammar=None):
        verbose = self.verbose
        if verbose:
            print("matching ParseNode", self, "at", repr(text[index:index+20]))
        ms = self.matchstring
        l = len(ms)
        end = index+l
        chunk = text[index:end]
        if text[index:end]==ms:
            if verbose:
                print("ParseNode", self, "success", repr(text[index:end]), repr(text[end:end+20]))
            return (index, end, self.transform(chunk)) # (start, end of match, interpretation)
        if verbose:
            print("Fail", self, repr(text[end:end+20]))
        raise MatchFail(repr(self))

    def __or__(self, other):
        other = makeNode(other)
        return Alternate(self, other)
    def __ror__(self, other):
        return self.__or__(other)
    def __rand__(self, other):
        other = makeNode(other)
        return other.__and__(self)
    def __and__(self, other):
        # note, maybe this could be optimized for two simple string nodes (but is it wise?)
        other = makeNode(other)
        return Sequence(self, other)
    def __neg__(self):
        "optional"
        return Several(self, min=0, max=1)
    def __invert__(self):
        "repeat (0 or more)"
        return Several(self, min=0)
    def __pos__(self):
        "one or more"
        return Several(self, min=1)

class AnyChars(ParseNode):
    """match chars in set (at least one)"""
    def __init__(self, set):
        self.set = set
        self.call = None
    def __repr__(self):
        return "[%s]" %(repr(self.set))
    def match(self, text, index=0, grammar=None):
        #print "matching AnyChars", self
        verbose = self.verbose
        if verbose:
            print("matching AnyChars", self, "at", repr(text[index:index+20]))
        set = self.set
        end = index
        last = len(text)
        while end<last and text[end] in set:
            end=end+1
        if end<=index:
            if verbose:
                print("Fail", self, repr(text[end:end+20]))
            raise MatchFail
        if verbose:
            print(self, "success", repr(text[index:end]), repr(text[end:end+20]))
        chunk = text[index:end]
        return (index, end, self.transform(chunk))

class Several(ParseNode):
    """match one or 0"""
    def __init__(self, contained, min=0, max=None):
        self.contained = contained
        self.min = min
        self.max = max
    def __repr__(self):
        return "[%s,%s..%s]" % (self.contained, self.min, self.max)

    def match(self, text, index=0, grammar=None):
        #print "matching Several", self
        verbose = self.verbose
        if verbose:
            print("matching", self, "at", repr(text[index:index+20]))
        end = index
        count = 0
        done = 0
        matches = []
        contained = self.contained
        min = self.min
        max = self.max
        while not done:
            if max is not None and count>=max:
                done = 1
            else:
                try:
                    m = contained.match(text, end, grammar)
                except MatchFail:
                    done = 1
                else:
                    (i, end, match) = m
                    matches.append(match)
                    count = count+1
        if count<min:
            if verbose:
                print("Fail", self, repr(text[end:end+20]))
            raise MatchFail
        if verbose:
            print(self, "success", repr(text[index:end]), repr(text[end:end+20]))
        if not matches:
            matches = None # ignore if empty
        return (index, end, matches)

class Sequence(ParseNode):
    """match in sequence"""
    def __init__(self, *seq):
        myseq = []
        for s in seq:
            #print type(s), ";;", s
            if s.__class__ is Sequence:
                myseq.extend(list(s.seq))
            else:
                myseq.append(s)
        self.seq = myseq
    def __repr__(self):
        rs = list(map(repr, self.seq))
        return "("+ " & ".join(rs) + ")"
##    def __and__(self, other):
##        other = makeNode(other)
##        if other.__class__ is Sequence:
##            # collapse two sequences together
##            return Sequence(list(self.seq) + list(other.seq))
##        return ParseNode.__and__(self, other)

    def match(self, text, index=0, grammar=None):
        #print "matching Sequence", self
        verbose = self.verbose
        if verbose:
            print()
            print("matching", self, "at", repr(text[index:index+20]))
        end = index
        matches = []
        for contained in self.seq:
            m = contained.match(text, end, grammar)
            (i, end, match) = m
            if verbose:
                print("in Sequence")
                print("contained", contained)
                print("returns", match)
            # IGNORE MATCHES WHICH ARE None (???)
            if match is not None:
                matches.append(match)
        if matches:
            matches = tuple(matches)
        else:
            matches = None # ignore if empty.
        if verbose:
            print("Sequence success", repr(text[index:end]), repr(text[end:end+20]))
            print("matches:")
            print("  ", matches)
            print()
        return (index, end, matches)

class Alternate(ParseNode):
    """match either (preferring the first if ambiguous)"""
    def __init__(self, *alts):
        myalts = []
        for a in alts:
            if a.__class__ is Alternate:
                myalts.extend(list(a.alts))
            else:
                myalts.append(a)
        self.alts = myalts
    def __repr__(self):
        rs = list(map(repr, self.alts))
        return "("+ " | ".join(rs) + ")"

    def match(self, text, index=0, grammar=None):
        verbose = self.verbose
        if verbose:
            print("matching", self, "at", repr(text[index:index+20]))
        #print "matching Alternate", self
        for a in self.alts:
            try:
                return a.match(text, index, grammar)
            except MatchFail:
                pass
        raise MatchFail

class Discard(ParseNode):
    """match it and ignore the result"""
    def __init__(self, node):
        self.node = node
    def __repr__(self):
        if self.verbose:
            return "{%s}" % self.node
        else:
            return " <I/> "
    def match(self, text, index=0, grammar=None):
        #print "matching Discard", self
        if self.verbose: self.node.verbose = 1
        (i, end, m) = self.node.match(text, index, grammar)
        return (i, end, None)

def Trace(node):
    node.verbose = 1
    return node

class Skip(ParseNode):
    """skip stuff, like for comments and PI's"""
    def __init__(self, start, end):
        self.start = start
        self.end = end
    def __repr__(self):
        return "{%s...%s}" % (self.start, self.end)
    def match(self, text, index=0, grammar=None):
        start = self.start
        end = self.end
        lend = len(end)
        lstart = len(start)
        fstart = text.find(start, index)
        if fstart!=index:
            raise MatchFail
        i = index+lstart
        fend = text.find(end, i)
        if fend<index:
            raise MatchFail
        return (index, fend+lend, None)

Comment = Skip("<!--", "-->")
PI = Skip("<?", "?>")

indent = 0
#verbose = 0

class NamedNode(ParseNode):
    """match a nonterminal named in the grammar"""
    def __init__(self, name):
        self.name = name
    def __repr__(self):
        return "<%s/>" % self.name
    def match(self, text, index=0, grammar=None):
        #print "matching NamedNode", self
        verbose = self.verbose
        name = self.name
        node = grammar.node(name)
        if self.verbose:
            print("matching", name)
            self.node.verbose = 1
        global indent
        if verbose:
            oldindent = indent
            ind = " "*indent
            print(ind, "...trying", name, repr(text[index:index+20]))
            indent = indent+1
        try:
            (i, end, m) = node.match(text, index, grammar)
        except MatchFail:
            if verbose:
                print(ind, "matchfail", name, "at", repr(text[index:index+20]))
                indent = oldindent
            raise MatchFail
        if verbose:
            indent=oldindent
            print(ind,"...", name, "succeeded", m)
            print(ind,"...", name, "ending at", repr(text[end:end+20]))
        # omit if ignored
        if m is None:
            d = None
        else:
            d = {name: m}
        return (index, end, d)

class Grammar:
    def __init__(self, rootNonTerminal):
        self.rootNonTerminal = rootNonTerminal
        self.nonterminals = {}
    def __repr__(self):
        L = []
        nt = self.nonterminals
        nk = list(nt.keys())
        nk.sort()
        L.append(self.rootNonTerminal+":")
        for n in nk:
            L.append("%s :== %s"%(n, nt[n]))
        return "\n".join(L)
    def match(self, text, index=0):
        r = self.node(self.rootNonTerminal)
        return r.match(text, index, self)
    def node(self, name):
        #print "nonterminal", name
        return self.nonterminals[name]
    def __setitem__(self, name, rhs):
        rhs = makeNode(rhs)
        nonterms = self.nonterminals
        current = nonterms.get(name, None)
        if current is not None:
            rhs = current | rhs
        nonterms[name] = rhs

def makeNode(x):
    """do autoconversions for convenience"""
    if isinstance(x,str):
        return ParseNode(x)
    return x

### end of parsing stuff, beginning of xml specific gunk

def xmlgram():
    N =  NamedNode
    m = makeNode
    ### create the grammar
    G = Grammar("prolog") # just the prolog

    Comment1 = G["Comment"] = Comment
    #Comment1 = N("Comment") # for tracing
    # [3]     S ::=  (#x20 | #x9 | #xD | #xA)+
    S = G["S"] = Discard(AnyChars(string.whitespace))
    # NameChar ::=  Letter | Digit | '.' | '-' | '_' | ':' | CombiningChar | Extender
    #   XXX leaving out CombiningChar | Extender for now
    NameChar = G["NameChar"] = AnyChars(string.letters+string.digits+".-_")
    # Nmtoken ::= (NameChar)+
    G["Nmtoken"] = NameChar
    # Name ::= (Letter | '_' | ':') (NameChar)*
    Name = G["Name"] = AnyChars(string.letters+"_:") & (~NameChar)
    #Name = N("Name") # could comment
    #S = N("S") # for readability: comment out for faster
    Sopt = Discard(-S)
    # prolog ::= XMLDecl? Misc* (doctypedecl Misc*)?
    Misc = N("Misc")
    Miscstar = ~Misc
    G["prolog"] = N("XMLDecl") & Miscstar & (-(N("doctypedecl") & Miscstar))
    # XMLDecl ::= '<?xml' VersionInfo EncodingDecl? SDDecl? S? '?>'\
    G["XMLDecl"] = "<?xml" & N("VersionInfo") & (-N("EncodingDecl")) & (-N("SDDecl")) & Sopt & "?>"
    # VersionInfo ::= S 'version' Eq ("'" VersionNum "'" | '"' VersionNum '"')
    VersionNum = N("VersionNum")
    G["VersionInfo"] = S & "version" & N("Eq") & (("'" & VersionNum & "'") | ('"' & VersionNum & '"'))
    # Eq ::= S? '=' S?
    Eq = G["Eq"] = Sopt & "=" & Sopt
    # VersionNum ::= ([a-zA-Z0-9_.:] | '-')+
    G["VersionNum"] = AnyChars(string.letters+string.digits+".:-")
    # Misc ::= Comment | PI | S
    G["Misc"] = Comment1 | PI | S
    # doctypedecl ::=    '<!DOCTYPE' S Name (S ExternalID)? S? ('[' (markupdecl |
    #                              DeclSep)* ']' S?)? '>'
    decls = G["decls"] = ~(N("markupdecl") | N("DeclSep"))
    #decls = N("decls") # could comment
    optid = -(S & N("ExternalID"))
    optspec = -("[" & decls & "]" & Sopt)
    G["optspec"] = optspec
    #optspec = N("optspec") # could comment
    G["doctypedecl"] = '<!DOCTYPE' & S & Name & optid & Sopt & optspec & ">"
    # DeclSep ::= PEReference | S
    G["DeclSep"] = N("PEReference") | S
    # markupdecl ::= elementdecl | AttlistDecl | EntityDecl | NotationDecl |
    #                              PI | Comment
    # XXXXXX FOR NOW LEAVING OUT ENTITYDECL AND NOTATIONDECL!
    #G["markupdecl"] = ( N("elementdecl") | N("AttlistDecl") | N("EntityDecl") |
    #                    N("NotationDecl") | PI | Comment )
    G["markupdecl"] = ( N("elementdecl") | N("AttlistDecl") |
                     PI | Comment1 )
    yesno = m("yes") | m("no")
    # SDDecl ::= S 'standalone' Eq (("'" ('yes' | 'no') "'") | ('"' ('yes' | 'no') '"'))
    G["SDDecl"] = S & "standalone" & Eq & ( ("'" & yesno & "'") | ('"' & yesno & '"') )
    # elementdecl ::= '<!ELEMENT' S Name S contentspec S? '>'
    G["elementdecl"] = '<!ELEMENT' & S & Name & S & N("contentspec") & Sopt & '>'
    # contentspec ::= 'EMPTY' | 'ANY' | Mixed | children
    G["contentspec"] = m('EMPTY') | 'ANY' | N("Mixed") | N("children")
    # children ::= (choice | seq) ('?' | '*' | '+')?
    G["qsp"] = qsp = -(m('?') | m('*') | m('+'))
    qsp = N("qsp") # could comment
    G["children"] = (N("choice") | N("seq")) & qsp
    # cp ::= (Name | choice | seq) ('?' | '*' | '+')?
    G["cp"] = (Name | N("choice") | N("seq")) & qsp
    #choice ::= '(' S? cp ( S? '|' S? cp )+ S? ')'
    cp = N("cp")
    G["choice"] = '(' & Sopt & cp & (+( Sopt & '|' & Sopt & cp)) & Sopt & ')'
    # seq ::= '(' S? cp ( S? ',' S? cp )* S? ')'
    G["seq"] = '(' & Sopt & cp & (~( Sopt & ',' & Sopt & cp)) & Sopt & ')'
    #Mixed ::= '(' S? '#PCDATA' (S? '|' S? Name)* S? ')*'
    #                       | '(' S? '#PCDATA' S? ')'
    G["Mixed"] = ("(" & Sopt & "#PCDATA" & (~(Sopt & "|" & Sopt & Name)) & Sopt & ")*"
                  ) | ("(" & Sopt & "#PCDATA" & Sopt & ")")
    # AttlistDecl ::= '<!ATTLIST' S Name AttDef* S? '>'
    G["AttlistDecl"] = '<!ATTLIST' & S & Name & (~N("AttDef")) & Sopt & '>'
    # AttDef ::= S Name S AttType S DefaultDecl
    G["AttDef"] = S & Name & S & N("AttType") & S & N("DefaultDecl")
    # AttType ::= StringType | TokenizedType | EnumeratedType
    G["AttType"] = N("StringType") | N("TokenizedType") | N("EnumeratedType")
    # StringType ::= 'CDATA'
    G["StringType"] = m("CDATA")
    # TokenizedType ::=  'ID' | 'IDREF' | 'IDREFS' | 'ENTITY' | 'ENTITIES' | 'NMTOKEN' | 'NMTOKENS'
    G["TokenizedType"] = (m('ID') | m('IDREF') | m('IDREFS') | m('ENTITY') |
                          m('ENTITIES') | m('NMTOKEN') | m('NMTOKENS'))
    # EnumeratedType ::= NotationType | Enumeration
    G["EnumeratedType"] = N("NotationType") | N("Enumeration")
    # NotationType ::= 'NOTATION' S '(' S? Name (S? '|' S? Name)* S? ')'
    G["NotationType"] = 'NOTATION' & S & '(' & Sopt & Name & (~(Sopt & '|' & Sopt & Name)) & Sopt & ')'
    # Enumeration ::= '(' S? Nmtoken (S? '|' S? Nmtoken)* S? ')'
    Nmtoken = N("Nmtoken")
    G["Enumeration"] = "(" & Nmtoken & (~(Sopt & "|" & Sopt & Nmtoken)) & Sopt & ")"
    # DefaultDecl ::= '#REQUIRED' | '#IMPLIED'
    #                             | (('#FIXED' S)? AttValue)
    G["DefaultDecl"] = (m('#REQUIRED') | m('#IMPLIED') |
                        ((-(m('#FIXED') & S)) & N("AttValue")))
    #EncodingDecl ::= S 'encoding' Eq ('"' EncName '"' | "'" EncName "'" )
    EncName = N("EncName")
    G["EncodingDecl"] = S & 'encoding' & Eq & (('"' & EncName & '"') | ("'" & EncName & "'"))
    # EncName  ::= [A-Za-z] ([A-Za-z0-9._] | '-')*
    G["EncName"] = AnyChars(string.letters) & AnyChars(string.letters+string.digits+"._-")

    # PEReference ::= '%' Name ';'
    G["PEReference"] = '%' & Name & ';'
    # ExternalID ::= 'SYSTEM' S SystemLiteral | 'PUBLIC' S PubidLiteral S SystemLiteral
    G["ExternalID"] = ('SYSTEM' & S & N("SystemLiteral")) | ('PUBLIC' & S & N("PubidLiteral") & S & N("SystemLiteral"))
    SystemLiteral = (("'" & AnyChars(allcharsexcept("'")) & "'")
                          | ('"' & AnyChars(allcharsexcept('"')) & '"')
                          )
    G["SystemLiteral"] = SystemLiteral
    G["PubidLiteral"] = SystemLiteral # cheating a bit here!
    G["AttValue"] = SystemLiteral # cheating here
    return G

class XMLWalker:
    def __init__(self):
        pass

    def walk(self, tree):
        if isinstance(tree,dict):
            if len(tree)>1:
                raise ValueError("dicts should have len 1")
            [k] = list(tree.keys())
            [v] = list(tree.values())
            methodname = "walk_"+k
            if hasattr(self, methodname):
                m = getattr(self, methodname)
                m(v)
            else:
                # if there's no handler, just walk the value
                self.walk(v)
        elif isinstance(tree,(list,tuple)):
            for x in tree:
                self.walk(x)
        else:
            pass

    def walk_elementdecl(self, n):
        from pprint import pprint
        print();print("element declaration::")
        pprint(n)
        elementdecl(self, n)

    def walk_doctypedecl(self, n):
        from pprint import pprint
        print();print("doctype declaration:: (first 2 elts)")
        pprint(n[:2])
        # the root of the docu
        self.root = n[1]
        #stop
        #walker = elementdecl(self, n)
        self.walk(n)

    def walk_AttlistDecl(self, n):
        from pprint import pprint
        print();print("attribute list declaration::")
        pprint(n)
        AttlistDecl(self, n)

    def add_element(self, name):
        print("registering new element", name)

    def add_attribute(self, eltname, attname, type, default):
        print("registering att", attname, "for element", eltname)
        print(".. type", type)
        print(".. default", default)

class elementdecl(XMLWalker):
    def __init__(self, parent, node):
        self.parent = parent
        self.elementname = elementname = node[1]
        self.parent.add_element(elementname)
        self.walk(node[2:])
    # add handlers...
    def walk_children(self, n):
        from pprint import pprint
        print();print("children declaration::")
        pprint(n)

class AttlistDecl(elementdecl):
    def __init__(self, parent, node):
        self.parent = parent
        self.elementname = node[1]
        #self.parent.add_element(elementname)
        self.walk(node[2:])
    def walk_AttDef(self, n):
        from pprint import pprint
        print();print("AttDef declaration::")
        pprint(n)
        AttDef(self.parent, self.elementname, n)

class AttDef(elementdecl):
    def __init__(self, parent, elementname, node):
        self.parent = parent
        self.elementname = elementname
        attname = self.attributename = node[0]
        self.default = None
        self.type = None
        self.walk(node[1:])
        parent.add_attribute(elementname, attname, self.type, self.default)
    ### ignoring types for now...
    def walk_AttValue(self, n):
        self.default = n[1] # the stuff inside the quotes
    def walk_AttType(self, n):
        self.type = n # really should do more: breakdown by subtype...

class Element:
    def __init__(self, name):
        self.name = name
        # name --> value
        self.defaults = {}
        # name --> type
        self.attributes = {}
        self.required = [] # names of required atts
        self.contents = None

class ContentSequence:
    def __init__(self, elements, option=None):
        self.elements = elements
        self.option = option # (None, "+", "?", "*")

def allcharsexcept(chrs):
    r = list(range(256))
    r = list(map(chr, r))
    for c in chrs:
        r.remove(c)
    return "".join(r)

def test2():
    Discard(-AnyChars(string.whitespace))
    num = AnyChars(string.digits)
    N = NamedNode
    G = Grammar("sum")
    t = N("term")
    s = N("sum")
    # note! order important here (more complex must go first)
    G["sum"] = t & "+" & s
    G["sum"] = t & "-" & s
    G["sum"] = t
    G["term"] = num & "*" & t
    G["term"] = num & "/" & t
    G["term"] = num
    print(G)
    #return
    for s in ["13", "1+2", "2*7-9"]:
        print("..matching", s)
        print(G.match(s))

def test1():
    succeed = []
    yes = succeed.append
    fail = []
    no = fail.append
    m = makeNode
    this = m("this")
    that = m("that")
    m("here")
    a,b,c,d = list(map(m, list("abcd")))
    thisaaa = this & (+a)
    yes(thisaaa, "thisa")
    yes(thisaaa, "thisaa")
    yes(thisaaa, "thisaaaaa")
    no(thisaaa, "this")
    no(thisaaa, "thata")
    thisoptthat = this & (-that)
    yes(thisoptthat, "this")
    yes(thisoptthat, "thisthat")
    no(thisoptthat, "tisthat")
    no(thisoptthat, "thisthisthat")
    thisorthat = this | that
    yes(thisorthat, "this")
    yes(thisorthat, "that")
    no(thisorthat, "other")
    uppers = AnyChars(string.uppercase)
    yes(uppers, "THIS")
    yes(Comment, "<!-- this -- is a comment -->")
    no(Comment, "<- this -- is NOT a comment -->")
    no(uppers, "This")
    for (m,s) in succeed:
        print("attempting", m, s)
        try:
            mm = m.match(s)
        except MatchFail:
            print("MATCH FAILED")
            return
        else:
            (index, end, match) = mm
            print(".. match succeeded", match)
            if end!=len(s):
                print("DIDN'T MATCH WHOLE STRING", end, len(s))
                return
    for (m,s) in fail:
        print("should fail:", m, s)
        try:
            mm = m.match(s)
        except MatchFail:
            print(".. failed as expected")
        else:
            print(".. succeeded, checking for extra", mm, len(s))
            (index, end, match) = mm
            if end!=len(s):
                print(".. didn't consume string, as expected", mm)
            else:
                print("MATCH SUCCEEDED", mm)
                return
    print("tests all pass")

if __name__=="__main__":
    #test1()
    #test2()
    g = xmlgram()
    # print g
    #text = open("toykfd2.xml").read()
    text = open("samples/toykfd.xml").read()
    print(); print(); print("attempting an xml file parse")
    m = g.match(text)
    if 0:
        print("successful match, now dumping...")
        from pprint import pprint
        pprint(m)
    if 1:
        print("successful match", type(m))
        print(); print(); print(); print("now walking")
        w = XMLWalker()
        w.walk(m)
