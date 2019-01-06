"dump fields from annotations in pages in a document"
from .pageCatcher import PDFParseContext

# optional friendly translation of field types and names

AnnotationExpander = {
    # common to all annotations
    'C':'Color',
    'T':'Title',
    'M':'ModDate',
    'F':'Flags',
    'H':'Highlight',
    'BS':'BorderStyle',
    'AA':'AdditionalActions',
    'AP':'Appearance',
    'AS':'AppearanceState',
    
    }

FieldTypeExpander = {
    'Btn':'Button',
    'Tx':'TextField',
    'Ch':'Choice',
    'Sig':'Signature',
    'T':'Text',
    'V':'Value',
    'DV':'DefaultValue',
    'Ff':'Flags',
    'TU':'UserName',
    'TM':'MappingName',
    'Opt':'Options'
    }

def dumpAnnotationFields(frompdffile):
    """dump annotations per page
    Returns a list containing one list per page
    Each list per page contains a list of dictionaries representing the annotations
    in that page, with representations converted to standard python types and object references
    resolved.
    """
    result = []
    text = open(frompdffile,"rb").read()
    p = PDFParseContext(text, frompdffile)
    p.parse()
    (ind, catinfo) = p.catalog
    c= p.compilation
    c.findAllReferences()
    c.getReference(catinfo)
    c.doTranslations(catinfo)
    c.populatePageList()
    pagenumber = 0
    for pagename in c.pageList:
        thispageannotations = []
        page = c.objects[pagename]
        pagedict = page.dict
        if "Annots" in pagedict:
            pageannots = c.resolve(pagedict["Annots"])
            thispageannotations = pythonize(pageannots, c)
        pagenumber += 1
        result.append(thispageannotations)
    return result

from reportlab.pdfbase.pdfdoc import PDFText, PDFString, PDFDictionary, PDFArray

def pythonize(structure, compilation, seen=None):
    "translate basic pdf structures into roughly equivalent python types. return None for obscure structures"
    if seen is None:
        seen = {}
    structure = compilation.resolve(structure)
    sid = id(structure)
    viewcount = seen[sid] = seen.get(sid, 0) +1
    if isinstance(structure,(str,float,int)):
        return structure
    if isinstance(structure, PDFText):
        return structure.t
    if isinstance(structure, PDFString):
        return structure.s
    if isinstance(structure, PDFArray):
        r = []
        for x in structure.sequence:
            r.append(pythonize(x, compilation, seen))
        return r
    # skip dictionaries already seen
    if viewcount>1:
        return None
    if isinstance(structure, PDFDictionary):
        r = {}
        sdict = structure.dict.copy()
        if sdict.get("Type", None)=="/Page":
            return None # don't traverse a page tree
        # paste in inherited stuff if it has a parent
        if sdict.get("Type", None)=="/Annot" and sdict.get("Subtype", None)=="/Widget":
            collectAncestorAttributes(sdict, compilation)
            # forget the parent, if present
            #if "Parent" in sdict:
            #    del sdict["Parent"]
            # forget the resources (we don't need them)
            if "DR" in sdict:
                del sdict["DR"]
        for (a,b) in list(sdict.items()):
            test = pythonize(b, compilation, seen)
            if test is not None:
                r[a] = test
        return r
    return None # default

def collectAncestorAttributes(sdict, compilation, parentDict=None, seen=None):
    if seen is None:
        seen = {}
    if parentDict is None:
        parentDict = sdict
    seen[id(parentDict)] = 1
    nextparent = parentDict.get("Parent", None)
    # delete kids if present
    if "Kids" in parentDict:
        del parentDict["Kids"]
    if sdict!=parentDict:
        for k in list(parentDict.keys()):
            if k not in sdict:
                sdict[k] = parentDict[k]
        #sdict.update(parentDict)
    if nextparent is not None:
        #print "parent found"
        nextparent = compilation.resolve(nextparent)
        nextparentdict = nextparent.dict
        if id(nextparentdict) in seen:
            raise ValueError("infinite parent loop")
        collectAncestorAttributes(sdict, compilation, nextparentdict, seen)

def test(pdfFileName):
    from pprint import pprint
    dump = dumpAnnotationFields(pdfFileName)
    pprint(dump)

if __name__=="__main__":
    import sys
    try:
        pdfFileName = sys.argv[1]
    except:
        print("usage: dumpFields.py pdfFileName")
        print("defaulting to snow.pdf")
        pdfFileName = "snow.pdf"
    test(pdfFileName)
