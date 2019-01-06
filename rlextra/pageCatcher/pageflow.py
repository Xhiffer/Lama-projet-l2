#pageflow.py
"""Support for using PageCatcher within Platypus"""
__all__ = ('LoadPdfFlowable', 'ShowPdfFlowable', 'loadPdf',
            )
import os
from reportlab.lib.utils import pickle
from reportlab.platypus.flowables import Flowable, PageBreak
from rlextra.pageCatcher.pageCatcher import storeFormsInMemory,\
        restoreFormsInMemory, restoreFormsFromDict, fileName2Prefix
from reportlab.pdfbase.pdfdoc import xObjectName
from reportlab.platypus.doctemplate import NextPageTemplate, NotAtTopPageBreak
from reportlab.lib.utils import open_and_read, asUnicodeEx, annotateException
from reportlab.graphics.shapes import transformPoints

class LoadPdfFlowable(Flowable):
    """Imports PDF content into the current canvas when drawn.

    Used by RML2PDF, which has to store the forms itself but defer
    placing them into a document"""
    def __init__(self, pickledStuff, isDict=False):
        Flowable.__init__(self)
        self.pickledStuff = pickledStuff
        self._isDict = isDict

    def drawOn(self, canvas, x, y, _sW=0):
        "This makes sure the form XObjects are loaded into the canvas"
        (self._isDict and restoreFormsFromDict or restoreFormsInMemory)(self.pickledStuff,
                             canvas,
                             allowDuplicates=1)

def _formName2ExtraInfo(canv,name):
    doc = canv._doc
    internalname = xObjectName(name)
    if internalname in doc.idToObject:
        form = doc.idToObject[internalname]
        if hasattr(form,'_extra_pageCatcher_info'):
            return form._extra_pageCatcher_info

def normalizeBoxName(boxName,_normalizedBoxNames=dict(
                                mediabox='MediaBox',
                                cropbox='CropBox',
                                artbox='ArtBox',
                                trimbox='TrimBox',
                                bleedbox='BleedBox',
                                )):
    if boxName is None: return 'MediaBox'
    return _normalizedBoxNames[boxName.lower()]

def _formName2OrientationMatrix(canv,name,orientation,pdfBoxType,pageSize,xi,pageSizeHandler):
    if xi:
        cps = canv._pagesize
        po = xi.get('Rotate',0)
        if isinstance(pdfBoxType,(list,tuple)):
            x0,y0,x1,y1 = pdfBoxType
        else:
            x0,y0,x1,y1 = xi.get(normalizeBoxName(pdfBoxType),xi['MediaBox'])
        xscale = yscale = 1
        w = abs(x1-x0)
        h = abs(y1-y0)
        if pageSize=='set' or isinstance(pageSize,(list,tuple)):
            if pageSize=='set':
                nps = (w,h)
            else:
                nps = abs(pageSize[2]-pageSize[0]),abs(pageSize[3]-pageSize[1])
            canv.setPageSize(nps)
            if pageSizeHandler:
                if pageSizeHandler.first:
                    pageSizeHandler.oldPageSize = cps
                else:
                    canv._hanging_pagesize = pageSizeHandler.oldPageSize
        elif pageSize in ('fit','orthofit'):
            xscale = cps[0]/w
            yscale = cps[1]/h
            if pageSize=='orthofit':
                xscale = yscale = min(xscale,yscale)
            x0 *= xscale
            y0 *= yscale
            x1 *= xscale
            y1 *= yscale
        elif pageSize in ('center','centre'):
            dx = (cps[0] - w) * 0.5
            dy = (cps[1] - h) * 0.5
            x0 -= dx
            x1 -= dx
            y0 -= dy
            y1 -= dy
        if orientation=='auto':
            orientation=po
        elif orientation is None:
            orientation = 0
        orientation = int(orientation % 360)
        if orientation==0:
            matrix = [xscale,0,0,yscale,-x0,-y0]
        elif orientation==90:
            matrix = [0,-yscale,xscale,0,-y0,x1-x0]
        elif orientation==180:
            matrix = [-xscale,0,0,-yscale,x1-x0,y1-y0]
        else:
            matrix = [0,yscale,-xscale,0,y1-y0,-x0]
        return matrix if matrix != [1,0,0,1,0,0] else None

class ShowPdfFlowable(Flowable):
    "draws a form xobject in absolute coordinates"
    def __init__(self, formName, orientation=None,iptrans=None, callback=None,
            pdf_data=None, user_data=None,
            pdfBoxType=None,
            autoCrop=None,
            pageSize=None,
            pageSizeHandler=None,
            ):
        Flowable.__init__(self)
        self.formName = formName
        self._orientation = orientation
        self._iptrans = iptrans
        self._pdfBoxType = pdfBoxType
        self._autoCrop = autoCrop
        self._pageSize = pageSize
        self._pageSizeHandler = pageSizeHandler
        self._pdf_data = pdf_data
        if callback:
            self.callback = lambda key,canv: callback(key,canv,self,pdf_data,user_data)
        else:
            self.callback = lambda key,canv: None

    def drawOn(self, canvas, x, y, _sW=0):
        iptrans = self._iptrans
        matrix = self._orientation
        pdfBoxType = self._pdfBoxType
        autoCrop = self._autoCrop
        pageSize = self._pageSize
        doTrans = iptrans and not iptrans.trivial()
        self.callback('raw-pre',canvas)
        restore = doTrans or autoCrop or pdfBoxType or matrix!=None or pageSize
        if restore:
            xi = _formName2ExtraInfo(canvas,self.formName)
            canvas.saveState()
            if pdfBoxType or matrix is not None or pageSize:
                matrix = _formName2OrientationMatrix(canvas,self.formName,matrix,pdfBoxType,pageSize,xi,self._pageSizeHandler)
                if matrix:
                    canvas.transform(*matrix)
            if iptrans:
                if not iptrans.noRotate():
                    canvas.rotate(iptrans.degrees)
                if not iptrans.noTranslate():
                    canvas.translate(iptrans.dx,iptrans.dy)
                if not iptrans.noScale():
                    canvas.scale(iptrans.sx,iptrans.sy)
            self.callback('transformed-pre',canvas)

        if autoCrop:
            if isinstance(autoCrop,(list,tuple)):
                clip = list(map(float,autoCrop))
            elif isinstance(autoCrop,str):
                clip = xi[normalizeBoxName(autoCrop)]
            else:
                clip = xi['CropBox']
            P = (clip[0],clip[1]),(clip[0],clip[3]),(clip[2],clip[3]),(clip[2],clip[1])
            #if canvas._code and canvas._code[-1][-3:]==' cm':
            #   L = canvas._code[-1].split()
            #   transform = list(map(float,L[-7:-1]))
            #   P = transformPoints(transform,P)
            path = canvas.beginPath()
            path.moveTo(*P[0])
            path.lineTo(*P[1])
            path.lineTo(*P[2])
            path.lineTo(*P[3])
            path.close()
            canvas.clipPath(path,0,0)

        try:
            #this won't do much if already loaded
            canvas.doForm(self.formName)
        except:
            annotateException('\ncnvas.doForm(%r) error handling %r' % (self.formName,self._pdf_data))

        if restore:
            self.callback('transformed-post',canvas)
            canvas.restoreState()
        self.callback('raw-post',canvas)

class IPTrans:
    def __init__(self,sx,sy,dx,dy,degrees):
        self.sx = sx
        self.sy = sy
        self.dx = dx
        self.dy = dy
        self.degrees = degrees

    def trivial(self):
        return self.noScale() and self.noTranslate() and self.noRotate()

    def noScale(self):
        return not (abs(self.sx-1)>1e-8 or abs(self.sy-1)>1e-8)

    def noTranslate(self):
        return not (abs(self.dx)>1e-8 or abs(self.dy)>1e-8)

    def noRotate(self):
        return not abs(self.degrees)>1e-8

def expandPageNumbers(txt):
    """Convert expression like '1,3,7-10,12' to a list of numbers"""
    if not txt: return None

    chunks = txt.split(',')
    pages = []
    pages_append = pages.append
    for chunk in chunks:
        chunk = chunk.strip()
        bits = chunk.split('-')
        if len(bits) == 1:
            pages_append(int(chunk))
        elif len(bits) == 2:
            start = int(bits[0])
            end = int(bits[1])
            for pg in range(start, end+1):
                pages_append(pg)
        else:
            pass
    return pages

class OutlineEntry(Flowable):
    """make an outline entry (lazily convert content)
       should work either in story or in page graphic mode!
    """
    _ZEROSIZE = 1
    _N = 0
    def __init__(self, level, content, closed, name=None, newBookmark=1):
        self.level = level
        self.content = content
        self.closed = closed
        if name is None:
            name = "k%r%d" % (id(self),self._N)     # arbitrary unique string
            self._N += 1
            newBookmark = 1
        self.name = name
        self.newBookmark = newBookmark

    def wrap(self, w, h):
        return 0,0 # consumes no space
    def draw(self):
        "flowable mode"
        self.doEntry(self.canv)
    def __call__(self, canv, doc):
        "graphic mode"
        self.doEntry(canv)
    def doEntry(self, canv):
        content = "".join(map(asUnicodeEx, self.content))
        name = self.name
        if self.newBookmark:
            canv.bookmarkPage(name)
        # bogus level may result in error here
        canv.addOutlineEntry(content, name, self.level, self.closed)
    def __str__(self):
        return ''

def includePdfFlowables(fileName,
                        pages=None,
                        dx=0, dy=0, sx=1, sy=1, degrees=0,
                        orientation=None,
                        isdata=False,       #True if this is a preprocessed data file
                        leadingBreak=True,  #True/False or 'notattop'
                        template=None,
                        outlineText=None,
                        outlineLevel=0,
                        outlineClosed=0,
                        pdfBoxType = None,
                        autoCrop = False,
                        pageSize=None,
                        callback=None,
                        user_data=None,
                        ):
    '''
    includePdfFlowables creates a list of story flowables that
                        represents an included PDF.
    Arguments       meaning
    fileName        string name of a .pdf or .data file
    pages           If None all pages will be used, else this argument can
                    be a string like '1,2,4-6,12-10,15' or an explicit
                    list of integers eg [1,2,7].

    dx,dy,          translation together all these make up a transformation
    sx,sy,          scaling     matrix
    degrees,        rotation

    orientation     None or integer degrees eg 0 90 270 or 'portrait'/'landscape'
    isdata          True if fileName argument refers to a .data file (as
                    produced by pageCatcher)
    leadingBreak    True/False or 'notattop' specifies whether a leading
                    page break should be used; 'notattop' means a page break
                    will not be used if the story is at the top of a frame.
    template        If specified the index or name of a template to be used.
    outlineText     Any outline text to be used (default None)
    outlineLevel    The level of any outline text.
    outlineClosed   True/False if the outline should be closed or open.

    pdfBoxType      which box to use or None or [x0,y0,  x1,y1]

    autoCrop        True/False crop/don't crop with CropBox (default is False)
                    boxname use for cropping
                    [x0,y0,  x1,y1] crop area

    pageSize        default None ie leave page size alone
                    'set' adjust page size to incoming box
                    'fit' scale incoming box to fit page size
                    'orthfit' orthogonally scale incoming box to fit
                    'center' or 'centre' center the incoming box in
                    the existing page size
                    [x0,y0, x1,y1] use this as the page size

    callback        draw time callback with signature

                    callback(canvas,key,obj,pdf_data,user_data)

                    canvas the canvas being drawn on
                    key may be 'raw-pre'|'transformed-pre'|'transformed-post'|'raw-post'
                    obj the flowable calling the callback
                    pdf_data ('fileName',pageNumber)
                    user_data user data passed down to the flowable from
                              IncludePdfFlowable.

    user_data       information to be passed to the callback
    '''
    try:
        orientation=int(orientation)
        orientation = orientation % 360
    except:
        if orientation=='portrait':
            orientation = 0
        elif orientation=='landscape':
            orientation = 90
        elif orientation!='auto' and orientation!=None:
            raise ValueError('Bad value %r for orientation attribute' % orientation)

    iptrans = IPTrans(sx,sy,dx,dy,degrees)
    if iptrans.trivial(): iptrans = None

    pages = expandPageNumbers(pages)

    # this one is unusual in that it returns a list of objects to
    # go into the story.
    output = []
    output_append = output.append

    if template:
        output_append(NextPageTemplate(template))

    try:
        if isdata:
            pickledStuff = pickle.loads(open_and_read(fileName))
            formNames = pickledStuff[None]
        else:
            #read in the PDF file right now and get the pickled object
            # and names
            pdfContent = open_and_read(fileName)
            prefix = fileName2Prefix(fileName)
            (formNames, pickledStuff) = storeFormsInMemory(
                    pdfContent,
                    prefix=prefix,
                    all=1,
                    BBoxes=0,
                    extractText=0,
                    fformname=None)
    except:
        annotateException('\nerror storing %r in memory\n' % fileName)

    #if explicit pages requested, slim it down.
    if pages:
        newNames = []
        for pgNo in pages:
            newNames.append(formNames[pgNo-1])
        formNames = newNames

    #make object 1 for story
    loader = LoadPdfFlowable(pickledStuff,isdata)
    output_append(loader)

    #now do first page.  This is special as it might
    #have an outline
    formName = formNames[0]
    if leadingBreak:
        output_append((leadingBreak=='notattop' and NotAtTopPageBreak or PageBreak)())
    if outlineText:
        output_append(OutlineEntry(outlineLevel, outlineText, outlineClosed))

    if pageSize=='fit':
        class PageSizeHandler(object):
            '''simple class to allow communications between first and last ShowPdfFlowables'''
            _oldPageSize = [None]
            def __init__(self,first):
                self.first = first

            def oldPageSize(self,v):
                self._oldPageSize[0] = v
            oldPageSize = property(lambda self: self._oldPageSize[0],oldPageSize)
        pageSizeHandler = PageSizeHandler(True)
    else:
        pageSizeHandler = None
    output_append(ShowPdfFlowable(formName,orientation=orientation,iptrans=iptrans,
                        callback=callback,
                        pdf_data=(fileName,pages[0] if pages else 1),
                        user_data=user_data,
                        pdfBoxType=pdfBoxType,
                        autoCrop=autoCrop,
                        pageSize=pageSize,
                        pageSizeHandler=pageSizeHandler,
                        ))

    #now make a shower for each laterpage, and a page break
    for i,formName in enumerate(formNames[1:]):
        i += 1
        output_append(PageBreak())
        output_append(ShowPdfFlowable(formName,orientation=orientation,iptrans=iptrans,
                callback=callback,
                pdf_data=(fileName,pages[i] if pages else i),
                user_data=user_data,
                pdfBoxType=pdfBoxType,
                autoCrop=autoCrop,
                pageSize=pageSize,
                pageSizeHandler=None,
                ))
    if pageSize=='fit':
        output[-1]._pageSizeHandler = PageSizeHandler(False)
    return output

class IncludePdfFlowable(Flowable):
    '''
    includePdfFlowable flowabnle that splits to a list of story flowables that
                        represents an included PDF.
    Arguments       meaning
    fileName        string name of a .pdf or .data file
    pages           If None all pages will be used, else this argument can
                    be a string like '1,2,4-6,12-10,15' or an explicit
                    list of integers eg [1,2,7].

    dx,dy,          translation together all these make up a transformation
    sx,sy,          scaling     matrix
    degrees,        rotation

    orientation     None or integer degrees eg 0 90 270 or 'portrait'/'landscape'
    isdata          True if fileName argument refers to a .data file (as
                    produced by pageCatcher)
    leadingBreak    True/False or 'notattop' specifies whether a leading
                    page break should be used; 'notattop' means a page break
                    will not be used if the story is at the top of a frame.
    template        If specified the index or name of a template to be used.
    outlineText     Any outline text to be used (default None)
    outlineLevel    The level of any outline text.
    outlineClosed   True/False if the outline should be closed or open.

    pdfBoxType      which box to use or None or [x0,y0,  x1,y1]

    autoCrop        True/False crop/don't crop with CropBox (default is False)
                    boxname use for cropping
                    [x0,y0,  x1,y1] crop area

    pageSize        default None ie leave page size alone
                    'set' adjust page size to incoming box
                    'fit' scale incoming box to fit page size
                    'orthfit' orthogonally scale incoming box to fit
                    'center' or 'centre' center the incoming box in
                    the existing page size
                    [x0,y0, x1,y1] use this as the page size

    callback        draw time callback with signature

                    callback(canvas,key,obj,pdf_data,user_data)

                    canvas the canvas being drawn on
                    key may be 'raw-pre'|'transformed-pre'|'transformed-post'|'raw-post'
                    obj the flowable calling the callback
                    pdf_data ('fileName',pageNumber)
                    user_data user data passed down to the flowable from
                              IncludePdfFlowable.

    user_data       information to be passed to the callback
    '''
    def __init__(self,
                fileName,
                pages=None,
                dx=0, dy=0, sx=1, sy=1, degrees=0,
                orientation=None,
                isdata=False,       #True if this is a preprocessed data file
                leadingBreak=True,  #True/False or 'notattop'
                template=None,
                outlineText=None,
                outlineLevel=0,
                outlineClosed=0,
                pdfBoxType = None,
                autoCrop = None,
                pageSize=None,
                callback=None,
                user_data=None,
                ):
        self.fileName = fileName
        self._kwds = dict(
                        pages = pages,
                        dx = dx,
                        dy = dy,
                        sx = sx,
                        sy = sy,
                        degrees = degrees,
                        orientation = orientation,
                        isdata = isdata,
                        leadingBreak = leadingBreak,
                        template = template,
                        outlineText = outlineText,
                        outlineLevel = outlineLevel,
                        outlineClosed = outlineClosed,
                        pdfBoxType = pdfBoxType,
                        autoCrop = autoCrop,
                        pageSize = pageSize,
                        callback = callback,
                        user_data = user_data,
                        )
        self._list = None

    def wrap(self,aW,aH):
        '''force a split'''
        return aW, 0x7fffffff

    def split(self,aW,aH):
        if not self._list:
            self._list = includePdfFlowables(self.fileName,**self._kwds)
        return self._list

    def identity(self, maxLen=None):
        msg = "<%s at %s%s> fileName=%s" % (self.__class__.__name__,hex(id(self)),self._frameName(),self.fileName)
        if maxLen:
            return msg[0:maxLen]
        else:
            return msg

def loadPdf(filename, canvas, pageNumbers=None, prefix=None):
    if prefix is None:
        prefix = os.path.splitext(filename)[0] + '_page'
    prefix = prefix.replace('/','_')
    pdfContent = open(filename,"rb").read()
    (formNames, stuff) = storeFormsInMemory(pdfContent,
                                            pagenumbers=pageNumbers,
                                            prefix=prefix,
                                            all=1)

    if pageNumbers:
        namesToInclude = []
        for num in pageNumbers:
            namesToInclude.append(formNames[num])
    else:
        namesToInclude = None
    restoreFormsInMemory(stuff, canvas,
                         allowDuplicates=1,
                         formnames=namesToInclude)
    return formNames
