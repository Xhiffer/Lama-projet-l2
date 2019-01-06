#copyright ReportLab Inc. 2000-2016
#see license.txt for license details
__version__='3.3.0'
__all__=('tt2xml',)
from xml.sax.saxutils import escape, quoteattr
from reportlab.lib.utils import isBytes, isUnicode, isStr
def tt2xml(tt):
    '''convert tuple tree form to unicode xml'''
    if tt is None: return ''
    if isBytes(tt):
        return tt2xml(tt.decode('utf8'))
    if isUnicode(tt):
        return escape(tt)
    if isinstance(tt,list):
        return ''.join(tt2xml(x) for x in tt)
    if isinstance(tt,tuple):
        tag = tt[0].decode('utf8')
        L=['<'+tag].append
        C = tt[2]
        if tt[1]:
            for k,v in tt[1].items():
                L((' %s=%s' % (k,quoteattr(v))).decode('utf8'))
        if C is not None:
            L('>')
            L(tt2xml(C))
            L('</'+tag+'>')
        else:
            L('/>')
        return ''.join(L.__self__)
    raise ValueError('Invalid value %r passed to tt2xml' % tt)

def findTags(tt, tname, tags=None):
    '''looks for a named tag in a pyRXP tuple tree (t)
    returns R where R is  a list of items (X) where items are either tuple 
    trees (t) where the tag is found or the items can be a list of t[X]
    R = [X*]
    X = t | [t[X]]
    '''
    if tags is None: tags=[]
    if isStr(tt) or tt is None:
        return tags
    if isinstance(tt, tuple):
        if tt[0]==tname:
            T1 = findTags(tt[2],tname,[])
            if T1:
                tags.append([tt,T1])
            else:
                tags.append(tt)
            return tags
        else:
            return findTags(tt[2],tname,tags)
    if isinstance(tt, list):
        for x in tt:
            findTags(x, tname, tags)
        return tags
    raise ValueError('invalid argument for tt=%r' % tt)
