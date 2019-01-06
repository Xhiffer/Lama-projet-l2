#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
#history www.reportlab.co.uk/rl-cgi/viewcvs.cgi/rlextra/pageCatcher/pdfexplorer.py
"""Tool to make it easy to split pages and extract text.

This is intended to become a PageCatcher PlugIn, once we have
a standard for such beasties.  It was driven by the need of a
customer to break up some big PDF documents based on hidden
strings embedded within the documents.  SUBJECT TO CHANGE!


Example of use:
    >>> exp = PdfExplorer("myfile.pdf")
    >>> found = exp.findPagesMatching(r"\(\d\d\d(\d?)\)")
    >>> exp.savePagesAsPdf([1,2,3] + found, 'outfile.pdf')


A high level class provides a wrapper around a 'parsed PDF file'
making it friendly to, for example, identify pages with specific
content.  The object produced by this should be easy both
to 'browse into' with a GUI Tree View and inspectors, and
to 'query' based on page content.  Therefore, it does
dumbed down and friendly classes corresponding to stuff
in the PDF.

One key idea is that it should not be unduly hard to create
(a) scripts to do the whole thing, 'saved as macros' from
some wizard, and (b) GUIs to do it interactively, (c) COM
and other objects.  Rather than trying to find the concept for
a PageCatcher mega-app, I'm thinking of 'registering plugins'.


"""
import re

import reportlab.pdfgen.canvas
from reportlab.pdfbase.pdfdoc import xObjectName
from rlextra.pageCatcher.pageCatcher import PDFParseContext, storeFormsInMemory, \
     restoreFormsInMemory

from rlextra.pageCatcher.dumpFields import pythonize, FieldTypeExpander
def testPattern(pat, good, bad):
    for sample in good:
        assert pat.match(sample) is not None, 'should have matched %s' % sample
    for sample in bad:
        assert pat.match(sample) is None, 'should not have matched %s' % sample

def testMatches():
    testPattern(patStartTextArray,
                good = ["[(","[ (","[\n\t\r (", "[67(", "[ 53 ("],
                bad = ["[a(", "[[", "9[", "[-67.4("])



class PageCatcherPlugIn:
    #to be completed and put in PageCatcher next time...
    pass

class PdfExplorer(PageCatcherPlugIn):
    def __init__(self, fileNameOrContent):
        self.cleanText = {}
        self._annotations = None
        self.context = None
        self.rawContent = None

        #when parsing referenced streams, keep the answers so we don't have to
        #do it several times
        self._xobjectStreams = {}

        #if they pass a big string which looks like PDF, assume a literal
        if b"%PDF" in fileNameOrContent[0:20]:
            content = fileNameOrContent
            self.parseContent(content)
        else:
            fileName = fileNameOrContent
            self.open(fileName)

    def parseContent(self, content):
        "Allows use in memory without a file name"
        self.rawContent = content
        self._parse()

    def open(self, fileName):
        """Parse and resolve a PDF file as much as possible"""
        from reportlab.lib.utils import open_and_read
        self.rawContent = open_and_read(fileName)
        self._parse()
        
    def _parse(self):        
        # the PDFParseContext is a parser for the PDF 'language'
        p = PDFParseContext(self.rawContent)
        p.parse()
        self.context = p

        # after parsing all those dictionaries, we need to do
        # the 'cross referencing' - figuring out what the bits
        # mean.  PageCatcher's model lets us do only the bits needed,
        # but what the heck, do the lot.
        # The 'compilation' object is basically the parsed/resolved/
        # reconstructed document, so we cal it pdfTree
        c = p.compilation
        self.pdfTree = c

        (ind, catinfo) = p.catalog
        if p.encrypt:
            getPdfEncrypt()


        c.sanitizePages(save=("Type", "Contents",
                              "MediaBox", "ArtBox", "BleedBox", "CropBox", "TrimBox",
                              "Resources", "Rotate"))
        #c.sanitizePages()  # this drops info we need
        c.findAllReferences()
        #catalog = \
        c.getReference(catinfo)
        c.doTranslations(catinfo)  # this takes the time!
        c.populatePageList()
        self.pageCount = len(c.pageList)


        # keep a lazy array of parsed page objects
        self._pageForms = [None] * len(c.pageList)


        # for text searching, gather all the named form xobjects now
        

    def _readPageForm(self, pageNo):
        "Only fully parse the page contents if asked to."


##        nameToObj = c.pagesAsForm(pagenumbers, prefix, all=all,fformname=fformname)
##        print '        pagesAsForm done: %0.2f' % (time.clock() - started)
##        #print 'storeForms extracted %d items' % len(nameToObj)
##        pickledData = cPickle.dumps(nameToObj, 1)
##        print '        pickle dump: %0.2f' % (time.clock() - started)
##        formnames = nameToObj[None]
##        result = (formnames, pickledData)


        assert pageNo < self.pageCount, "Page number out of range!"
        if self._pageForms[pageNo] is None:
            nameToObj = self.pdfTree.pagesAsForm([pageNo], 'page')
            #pickledData = cPickle.dumps(nameToObj, 1)
            self._pageForms[pageNo] = nameToObj

        return self._pageForms[pageNo]

    def getPage(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page

    def getPageSize(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["MediaBox"].sequence

    def getMediaBox(self, pageNo):
        "Same as pagesize, the latter was poorly named and may change one day"
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["MediaBox"].sequence

    def getArtBox(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["ArtBox"].sequence

    def getBleedBox(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["BleedBox"].sequence
    
    def getTrimBox(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["TrimBox"].sequence

    def getCropBox(self, pageNo):
        objectKey = self.pdfTree.pageList[pageNo]
        page = self.pdfTree.objects[objectKey]
        return page.dict["CropBox"].sequence

    def getPageRotation(self, pageNo):
        return self.getPage(pageNo).dict.get('Rotate', 0)

    def getPdfOps(self, pageNo):
        self.getForm(pageNo)
        return self.pdfTree.plainText[pageNo]

    def getXObjects(self, pageNo):
        pageObjKey = self.pdfTree.pageList[pageNo]
        pageObj = self.pdfTree.objects[pageObjKey]
        found = []
        #our PDFDictionary classes wrap a python dict, hence the dict.dict.dict stuff
        if 'Resources' in pageObj.dict:
            resDict = self.pdfTree.resolve(pageObj.dict['Resources']).dict
            if 'XObject' in resDict:
                xobDict = resDict['XObject'].dict
                for key, value in list(xobDict.items()):
                    object = self.pdfTree.resolve(value)
                    found.append((key, object))
        return found

    def getText(self, pageNo):
        from . import pdparse
        
        if pageNo not in self.cleanText:
            
            texts = []
            raw = self.getPdfOps(pageNo)
            texts.append(pdparse.PdfTextExtractor().extractText(raw))
            
            #now track through all referenced streams
            xobjects = self.getXObjects(pageNo)
            for (xobName, xob) in xobjects:
                texts.append(self._getXobjectText(xob))
            self.cleanText[pageNo] = '\n\n'.join(texts)
        return self.cleanText[pageNo]

    def _getXobjectText(self, xob):
        "Extract its text, including recursing into any of its own resources"
        from rlextra.pageCatcher.pdparse import PdfTextExtractor
        xtrac = PdfTextExtractor()
        texts = []
        texts.append(xtrac.extractText(xob.content))

        if hasattr(xob, 'dictionary'):
            xobDict = xob.dictionary.dict
            if 'Resources' in xobDict:
                resDict = self.pdfTree.resolve(xobDict['Resources']).dict
                if 'XObject' in resDict:
                    xobDict2 = resDict['XObject'].dict
                    for key, value in list(xobDict2.items()):
                        xob2 = self.pdfTree.resolve(value)
                        text = self._getXobjectText(xob2)
                        texts.append(text)

        return '\n\n'.join(texts)
        

    def getForm(self, pageNo):
        """The form object for that page"""
        return self._readPageForm(pageNo)

    def getPageContent(self, pageNo):
        """The decompressed PDF, which includes the text"""
        # ensure it is fully parsed
        self._readPageForm(pageNo)
        return self.pdfTree.plainText[pageNo]


    def pageMatchesRe(self, pageNo, regex, textOnly=0):
        """Return None or match object. For regex wizards."""
        if textOnly:
            content = self.getText(pageNo)
        else:
            content = self.getPageContent(pageNo)
        return regex.search(content)


    def findTextMatching(self, pageNo, pattern, textOnly=0):
        """Return matched string or None.  For mortals."""
        regex = re.compile(pattern)
        match = self.pageMatchesRe(pageNo, regex, textOnly)
        if match is None:
            return None
        else:
            return match.group()

    def findPagesMatching(self, pattern, textOnly=0, showGroups=0):
        """Return a list with an entry for each page.  The entry will
        either be the text matched, or None if not found."""
        regex = re.compile(pattern)
        results = []
        for pageNo in range(self.pageCount):
            match = self.pageMatchesRe(pageNo, regex, textOnly)
            if match is None:
                results.append(None)
            else:
                if showGroups:
                    row = [match.group()]
                    row.extend(match.groups())
                    results.append(row)
                else:
                    results.append(match.group())

        return results


    def _calcName(self, namePattern, groups):
        """Substitution system for building up an output filename patterm"""
        for i in range(len(groups)):
            namePattern = namePattern.replace('%%%d' % i, groups[i])
        return namePattern

    def prepareSplitPlan(self, report, namePattern=None):
        if namePattern is None:
            namePattern = '%0'
        prevDoc = None
        result = []
        pageList = []
        for pageNo in range(self.pageCount):
            row = report[pageNo]
            if row is None:
                continue
            else:
                found = row[0]
                groups = row[1:]
                if found != prevDoc:
                    fileName = self._calcName(namePattern, row)
                    result.append((fileName, pageList))
                    pageList = []
                pageList.append(pageNo)
                prevDoc = found

        if pageList != []:
            fileName = self._calcName(namePattern, [found] + groups)
            result.append((fileName, pageList))

        return result

    def splitOnPattern(self, searchPattern, outFilePattern=None, textOnly=1):
        "Makes individual PDFs out of any which match the pattern"
        matches = self.findPagesMatching(searchPattern, textOnly=textOnly, showGroups=1)
        splitPlan = self.prepareSplitPlan(matches, outFilePattern)
        for fileName, pages in splitPlan:
            self.savePagesAsPdf(pages, fileName)
            print('saved %s' % fileName)



    def savePagesAsPdf(self, pageNumbers, fileName):
        "Saves the named pages into file of given name"

        (names, pickledData) = storeFormsInMemory(self.rawContent,
               pagenumbers=pageNumbers, prefix="page", BBoxes=0,
               extractText=0, fformname=None)
        (x,y,w,h) = self.getPageSize(0)
        c = reportlab.pdfgen.canvas.Canvas(fileName,pagesize=(w-x,h-y))
        restoreFormsInMemory(pickledData, c)
        for pageNo in pageNumbers:
            c.doForm('page%d' % pageNo)
            c.showPage()

            # check the rotation and try to preserve it
            #rot = self.getPageRotation(pageNo)
            #if rot:
            #    c._doc.Pages[-1].Rotate = rot
        c.save()


    def rewritePage(self, pageNo, canvas, width, height):
        "Override this to decorate your pages. Draws OVER your graphics"
        pass
        
        #example - uncomment if you wish!
#        #draw over the top.  This text should be near bottom left in red.
#        c = canvas
#        from reportlab.lib.colors import red
#        c.setFillColor(red)
#        c.setFont('Helvetica', 12)
#        c.drawString(0, 0, 'x')
#        c.drawString(10, 10, 'page size (corrected): %d x %d' % (width, height))
#        #overlay a red rectangle 5 points in, just to see if we got the sizes right
#        c.setStrokeColor(red)
#        c.rect(5, 5, width - 10, height - 10)

    def rewriteUnderPage(self, pageNo, canvas, width, height):
        "Override this to decorate your pages. Draws UNDER your graphics"
        pass
        

    def rewrite(self, outFileName):
        """Rewrite PDF, optionally with user decoration
        
        This will create a new PDF file from the existing one.
        It attempts to take care of rotated and cropped input files,
        and always outputs a file with no page-rotation and width the
        width and height you would normally expect.
        
        To decorate a page (e.g. overprint a timestamp), subclass
        PdfExplorer, and implement the rewritePage method:

            def rewritePage(self, pageNo, canvas, width, height):
                #your code here

        Take care to use the passed-in width and height, which will
        have been corrected by rotation and crop box.
        """


        
        pageNumbers = list(range(self.pageCount))
        (names, pickledData) = storeFormsInMemory(self.rawContent,
               pagenumbers=pageNumbers, prefix="page", BBoxes=0,
               extractText=0, fformname=None)
        c = reportlab.pdfgen.canvas.Canvas(outFileName)
        restoreFormsInMemory(pickledData, c)
        for pageNo in pageNumbers:
            (x,y,w,h) = self.getPageSize(0)
            rot = self.getPageRotation(pageNo)
            if rot in [90, 270]:
                w, h = h, w

                #go dumpster diving in the PDF and try to correct for
                #the bounds, which can otherwise clip off the content.
                #Ideally PageCatcher itself would do this when
                #reading in a rotated/cropped document, but I cannot
                #get that to work yet.
                formName = xObjectName(names[pageNo])
                form = c._doc.idToObject[formName]
                form.uppery, form.upperx = form.upperx, form.uppery


    
            #if a crop box is set, the user originally 'saw'
            #a window onto the page specified by an extra box in the
            #PDF with (x1, y1, x2, y2) coords.  We need to shift
            #our underlying form across
            try:
                cropBox = self.getCropBox(pageNo)
            except KeyError:
                cropBox = None

            if cropBox:
                if rot in [90, 270]:
                    cropY1, cropX1, cropY2, cropX2 = cropBox
                else:
                    cropX1, cropY1, cropX2, cropY2 = cropBox
                h = cropY2 - cropY1
                w = cropX2 - cropX1
            c.setPageSize((w,h))

            #user hook - subclass this to overprint
            c.saveState()
            self.rewriteUnderPage(pageNo, c, w, h)
            c.restoreState()

        
            c.saveState()
            if cropBox:
                c.translate(-cropX1, -cropY1)
            c.doForm('page%d' % pageNo)
            c.restoreState()
            
            #user hook - subclass this to overprint
            self.rewritePage(pageNo, c, w, h)
            
            #save it
            c.showPage()

        c.save()








##        import time
##        started = time.clock()
##        print 'entered savePagesAsPdf at %0.2f' % (time.clock() - started)
##        c = reportlab.pdfgen.canvas.Canvas(fileName)
##        print '    canvas created at %0.2f' % (time.clock() - started)
##
##        masterDict = {}
##        for num in pageNumbers:
##            nameToObj = self.getForm(num)
##            masterDict.update(nameToObj)
##        pickledData = cPickle.dumps(masterDict, 1)
##        restoreFormsInMemory(pickledData, c)
####        (names, pickledData) = storeFormsInMemory(self.rawContent,
####               pagenumbers=pageNumbers, prefix="page", BBoxes=0,
####               extractText=0, fformname=None)
##        print '    storeFormsInMemory done at %0.2f' % (time.clock() - started)
##        # pickledData is a cPickled binary dictionary
##        # mapping names to objects
####        nameToObj = {}
####        for number in pageNumbers:
####
##        restoreFormsInMemory(pickledData, c)
##        print '    restored forms at %0.2f' % (time.clock() - started)
##        for pageNo in pageNumbers:
##            c.doForm('page%d' % pageNo)
##            c.showPage()
##
##            # check the rotation and try to preserve it
##            rot = self.getPageRotation(pageNo)
##            if rot:
##                c._doc.Pages[-1].Rotate = rot
##        print '    drew pages at %0.2f' % (time.clock() - started)
##
##        c.save()
##        print '    saved  at %0.2f' % (time.clock() - started)
####        print 'bombing out now...'
####        import sys
####        sys.exit()


    def _extractAnnotations(self):
        """
        Returns list of annotation dictionaries on page.dict

        Here is what an annotation dictionary looks like:
        { 'F': 4,
          'FT': '/Tx',
          'Rect': [108, 577, 407, 594],
          'Subtype': '/Widget',
          'T': 'AgentName',
          'TU': 'blah again',
          'Type': '/Annot'}"""
        self._annotations = {}
        p = PDFParseContext(self.rawContent)
        p.parse()
        (ind, catinfo) = p.catalog
        c = p.compilation
        c.sanitizePages(save=("Type", "Contents",
                              "MediaBox", "ArtBox", "BleedBox", "CropBox", "TrimBox",
                              "Resources", "Rotate", "Annots"))
        #c.sanitizePages()  # this drops info we need
        c.findAllReferences()
        #catalog = \
        c.getReference(catinfo)
        c.doTranslations(catinfo)  # this takes the time!
        c.populatePageList()
        pageCount = len(c.pageList)

        for pageNo in range(pageCount):
            pageId = c.pageList[pageNo]
            page = c.objects[pageId]
            pageDict = page.dict
            if "Annots" in pageDict:
                rawPageAnnots = c.resolve(pageDict["Annots"])
                friendlyPageAnnots = pythonize(rawPageAnnots, c)

            else:
                friendlyPageAnnots = []
            self._annotations[pageNo] = friendlyPageAnnots

    def getAnnotations(self, pageNo):
        if self._annotations is None:
            self._extractAnnotations()
        return self._annotations[pageNo]

    def getAnnotationsTable(self, pageNo):
        """Tries to tabulate into something suitable for a grid report.

        Columns:  fieldtype, name,  rect, text"""
        report = []
        annots = self.getAnnotations(pageNo)
        for annot in annots:
            typ = annot.get('FT',None)
            try:
                typ = FieldTypeExpander[typ[1:]]
            except KeyError:
                pass
            name = annot.get('T',None)
            rect = annot.get('Rect',None)
            text = annot.get('TU',None)
            report.append((typ, name, rect, text))
        return report

def test():
    import sys
    try:
        fn = sys.argv[1]
    except:
        fn = 'PH_Offshore_Q3_2002.pdf'
    exp = PdfExplorer(fn)
    page1ops = exp.getPdfOps(0)
    print('\nextracting...\n')
    from . import pdparse
    xtr = pdparse.PdfTextExtractor().extractText(page1ops)
    print(xtr)

if __name__=='__main__':
    test()
