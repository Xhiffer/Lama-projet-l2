__all__=(
        'CanvasAdapter',
        'TextObject',
        'PSCanvasAdapter',
        'PMCanvasAdapter',
        'SVGCanvasAdapter',
        'DirectDrawFlowable',
        )
from reportlab.pdfbase.pdfmetrics import stringWidth
import collections
from reportlab.lib.colors import toColor
from reportlab.lib.utils import isStr

class TextObject:
    def __init__(self, canv, x=0, y=0):
        self._code = []
        self._canvas = canv  #canvas sets this so it has access to size info
        self._fontname = canv.fontName
        self._fontsize = canv.fontSize
        self.setTextOrigin(x, y)

    def _code_append(self,k,*args,**kw):
        self._code.append((k,args,kw))

    def setTextOrigin(self, x, y):
        self._x0 = self._x = x
        self._y0 = self._y = y
        self._code_append('setTextX',x)
        self._code_append('setTextY',y)

    def moveCursor(self, dx, dy):
        #self._code_append(something)
        self._x0 += dx
        self._y0 += dy
        self._x = self._x0
        self._y = self._y0
        self._code_append('setTextX',self._x0)
        self._code_append('setTextY',self._y0)

    def setXPos(self, dx):
        """Starts a new line dx away from the start of the
        current line - NOT from the current point! So if
        you call it in mid-sentence, watch out."""
        self.moveCursor(dx,0)

    def getCursor(self):
        """Returns current text position relative to the last origin."""
        return (self._x, self._y)

    def getStartOfLine(self):
        """Returns a tuple giving the text position of the start of the
        current line."""
        return (self._x0, self._y0)

    def getX(self):
        """Returns current x position relative to the last origin."""
        return self._x

    def getY(self):
        """Returns current y position relative to the last origin."""
        return self._y

    def _setFont(self, psfontname, size):
        """Sets the font and fontSize
        Raises a readable exception if an illegal font
        is supplied.  Font names are case-sensitive! Keeps track
        of font anme and size for metrics."""
        self._fontname = psfontname
        self._fontsize = size
        self._code_append('setFont',psfontname,size)

    def setFont(self, psfontname, size, leading = None):
        """Sets the font.  If leading not specified, defaults to 1.2 x
        font size. Raises a readable exception if an illegal font
        is supplied.  Font names are case-sensitive! Keeps track
        of font anme and size for metrics."""
        self._fontname = psfontname
        self._fontsize = size
        self._code_append('setFont',psfontname,size)
        if leading is None:
            leading = size * 1.2
        self._leading = leading

    def setCharSpace(self, space):
        """Adjusts inter-character spacing"""
        raise NotImplementedError
        #self._charSpace = space
        #self._code_append('setCharSpace',space)

    def setWordSpace(self, space):
        """Adjust inter-word spacing.  This can be used
        to flush-justify text - you get the width of the
        words, and add some space between them."""
        self._wordSpace = space
        self._code_append('setWordSpace',space)

    def setLeading(self, leading):
        "How far to move down at the end of a line."
        self._leading = leading

    def setRise(self, rise):
        "Move text baseline up or down to allow superscrip/subscripts"
        self._rise = rise
        self._code_append('setTextY',self._y+self._rise)

    def setFillColor(self, aColor):
        """Takes a color object, allowing colors to be referred to by name"""
        aColor = toColor(aColor)
        self._fillColor = aColor
        self._code_append('setFillColor',aColor)

    def setStrokeColor(self, aColor):
        """Takes a color object, allowing colors to be referred to by name"""
        self._StrokeColor = aColor
        self._code_append('setStrokeColor',aColor)

    def setFillGray(self, gray):
        """Sets the gray level; 0.0=black, 1.0=white"""
        raise NotImplementedError
        #self._code_append('setFillGray',gray)

    def setStrokeGray(self, gray):
        """Sets the gray level; 0.0=black, 1.0=white"""
        raise NotImplementedError
        #self._code_append('setStrokeGray',gray)

    def _textOut(self, text, TStar=0):
        "prints string at current point, ignores text cursor"
        self._code_append('textOut',text)
        if TStar:
            self._x = self._x0
            self._y0 = self._y = self._y-self._leading
            self._code_append('setTextY',self._y)
        else:
            self._x = self._x + stringWidth(text, self._fontname, self._fontsize)
        self._code_append('setTextX',self._x)

    def textOut(self, text):
        """prints string at current point, text cursor moves across."""
        self._x = self._x + stringWidth(text, self._fontname, self._fontsize)
        self._code_append('textOut',text)
        self._code_append('setTextX',self._x)

class SimpleStateTracker:
    def __init__(self,state={},ignore=[],rename={}):
        _ = self.__state = state.copy()
        for k in ignore:
            del _[k]
        for k,v in list(rename.items()):
            _[v] = _[k]
            del _[k]
        self.__stack = []

    def push(self,obj):
        _ = self.__state
        for k in list(self.__state.keys()):
            _[k] = getattr(obj,k)
        self.__stack.append(_)
        self.__state = _.copy()

    def apply(self,obj):
        for k,v in list(self.__state.items()):
            setattr(obj,k,v)

    def printState(self,msg):
        print('\n'+msg,len(self.__stack))
        for k,v in list(self.__state.items()):
            print('%s=%s' % (k,v))

    def pop(self):
        self.__state = self.__stack.pop()
        return self.__state

    def __getitem__(self,a):
        return self.__state[a]

    def __setitem__(self,a,v):
        self.__state[a] = v

    def __len__(self):
        return len(self.__stack)

    def setLen(self,n):
        del self.__stack[n:]

class CanvasAdapter:
    def __init__(self,baseCanvas,trans={},baseRenderer=None,**kw):
        self.__trans = trans
        self.__rtrans = kw.pop('rtrans',{})
        self.__canv = baseCanvas
        from reportlab.graphics.shapes import STATE_DEFAULTS
        if baseRenderer:
            D = baseRenderer._combined[-1]
        else:
            D = STATE_DEFAULTS.copy()
        D['fillOpacity'] = D['strokeOpacity'] = 1
        self.__canv.setFont(D['fontName'],D['fontSize'])
        _ = self.__tracker = SimpleStateTracker(D,
                ignore=('textAnchor','strokeMiterLimit','fillOverprint','overprintMask','strokeOverprint'),
                rename=dict(transform='ctm',))
        _.apply(self)
        self.__textWordSpace = 0
        self.__textX = 0
        self.__textY = 0
        self.__dict__['stringWidth'] = stringWidth

    def saveState(self):
        self.__canv.saveState()
        self.__tracker.push(self)

    def restoreState(self):
        self.__tracker.pop()
        self.__tracker.apply(self)
        self.__canv.restoreState()

    def beginText(self, x=0, y=0):
        return TextObject(self, x, y)

    def setTextX(self,x):
        self.__textX = x

    def setTextY(self,y):
        self.__textY = y

    def drawText(self, aTextObject):
        for k,args,kw in aTextObject._code:
            getattr(self,k)(*args,**kw)

    def setWordSpace(self,space):
        self.__textWordSpace = space

    def textOut(self,text):
        drawString = getattr(self,'drawString',self.__canv.drawString)
        xws = self.__textWordSpace
        if not xws:
            drawString(self.__textX,self.__textY,text)
            self.__textX += stringWidth(text,self.fontName,self.fontSize)+xws
        else:
            x = self.__textX
            y = self.__textY
            ws = stringWidth(' ',self.fontName,self.fontSize)+xws
            ww = 0
            for w in text.split():
                drawString(x,y,w)
                ww = stringWidth(w,self.fontName,self.fontSize)+ws
                x += ww
            self.__textX = x-ww

    def __getattr__(self,name):
        if not (name.startswith('_CanvasAdapter__') or name.startswith('_%s__'%self.__class__.__name__)):
            try:
                if name in self.__trans:
                    t = self.__trans[name]
                    if callable(t): return t(self.__canv,name)
                    else:
                        return getattr(self.__canv,t)
                elif name in self.__rtrans:
                    t = self.__rtrans[name]
                    return t(self.__canv,name) if callable(t) else getattr(self.__canv,t)
            except:
                raise AttributeError('No attribute "%s"' % name)
        return getattr(self.__canv,name)

    def __setattr__(self,name,value):
        if name.startswith('_CanvasAdapter__') or name.startswith('_%s__'% self.__class__.__name__):
            self.__dict__[name] = value
        elif name in self.__trans:
            t = self.__trans[name]
            if callable(t): t(self.__canv,name,value)
            else:
                setattr(self.__canv,t,value)
        else:
            setattr(self.__canv,name,value)

    def _getCanvas(self):
        return self.__canv

    def setFillColor(self, aColor):
        self.__canv.setFillColor(toColor(aColor))

class PMCanvasAdapter(CanvasAdapter):
    __TRANS = dict(
                strokeDashArray = 'dashArray',
                strokeLineCap = 'lineCap',
                strokeLineJoin = 'lineJoin',
                )
    __RTRANS = dict(
                _lineWidth = 'strokeWidth',
                )
    def __init__(self,pmCanv):
        D = self.__TRANS
        if 'fontName' not in D:
            def _0(canv,name,*args):
                if args:
                    canv.setFont(args[0],canv.fontSize)
                else:
                    return canv.fontName
            D['fontName'] = D['_fontname'] = _0
            def _1(canv,name,*args):
                if args:
                    if canv.fontName is not None:
                        canv.setFont(canv.fontName,args[0])
                else:
                    return canv.fontSize
            D['fontSize'] = D['_fontsize'] = _1
            def _2(canv,name,*args):
                pass
            D['_leading'] = _2  #ignored
        ctm = pmCanv.ctm
        CanvasAdapter.__init__(self,pmCanv,trans=D,rtrans=self.__RTRANS)
        self.ctm = ctm

    def transform(self, a,b,c,d,e,f):
        a0,b0,c0,d0,e0,f0 = self.ctm
        self.ctm = a0*a+c0*b, b0*a+d0*b, a0*c+c0*d, b0*c+d0*d, a0*e+c0*f+e0, b0*e+d0*f+f0

    def translate(self,dx,dy):
        self.transform(1,0,0,1,dx,dy)

    def scale(self,xscale,yscale):
        self.transform(xscale,0,0,yscale,0,0)

class PSCanvasAdapter(CanvasAdapter):
    __TRANS = {
                'strokeLineCap': '_lineCap',
                'strokeLineJoin': '_lineJoin',
                'fontSize': '_fontSize',
                'strokeWidth': '_lineWidth',
                'fillColor': '_fillColor',
                'strokeColor': '_strokeColor',
                }
    def __init__(self,psSepCanv):
        D = self.__TRANS
        if 'fontName' not in D:
            def _0(canv,name,*args):
                if args:
                    canv.setFont(args[0],canv._fontSize)
                else:
                    return canv._font
            D['fontName'] = D['_fontname'] = D['_font'] = _0
            def _1(canv,name,*args):
                if args:
                    canv.setFont(canv._font,args[0])
                else:
                    return canv._fontSize
            D['fontSize'] = D['_fontsize'] = _1
            def _2(canv,name,*args):
                pass
            D['_leading'] = _2  #ignored
            def _3(canv,name,*args):
                if args:
                    canv.setDash(args[0])
                    canv.__strokeDashArray = args[0]
                else:
                    return canv.__strokeDashArray
            D['strokeDashArray'] = _3
            def _4(canv,name,*args):
                if args:
                    canv.__ctm = args[0]
                else:
                    return canv.__ctm
            D['ctm'] = _4
        CanvasAdapter.__init__(self,psSepCanv,trans=D)

    def rect(self,x1,y1,w,h,stroke=1,fill=1):
        self._getCanvas().rect(x1,y1,x1+w,y1+h,stroke=stroke,fill=fill)

    def transform(self, a,b,c,d,e,f):
        a0,b0,c0,d0,e0,f0 = self.ctm
        _ = self.ctm = a0*a+c0*b, b0*a+d0*b, a0*c+c0*d, b0*c+d0*d, a0*e+c0*f+e0, b0*e+d0*f+f0
        self._getCanvas().transform(*_)

    def translate(self,dx,dy):
        a0,b0,c0,d0,e0,f0 = self.ctm
        self.ctm = a0, b0, c0, d0, a0*dx+c0*dy+e0, b0*dx+d0*dy+f0
        self._getCanvas().translate(dx,dy)

class SVGCanvasAdapter(CanvasAdapter):
    __TRANS = {
                'strokeColor':'_strokeColor',
                'strokeWidth': '_lineWidth',
                'strokeLineCap':'_lineCap',
                'strokeLineJoin':'_lineJoin',
                'fillColor':'_fillColor',
                }
    def __init__(self,svgCanv):
        D = self.__TRANS
        if 'fontName' not in D:
            def _0(canv,name,*args):
                if args:
                    canv.setFont(args[0],canv._fontSize)
                else:
                    return canv._font
            D['fontName'] = D['_font'] = D['_fontname'] = _0
            def _1(canv,name,*args):
                if args:
                    canv.setFont(canv._font,args[0])
                else:
                    return canv._fontSize
            D['fontSize'] = D['_fontsize'] = _1
            def _3(canv,name,*args):
                if args:
                    canv.setDash(args[0])
                    canv.__strokeDashArray = args[0]
                else:
                    return canv.__strokeDashArray
            D['strokeDashArray'] = _3
        CanvasAdapter.__init__(self,svgCanv,trans=D)
        self._savedStates = []

    def setFont(self,fontName,fontSize,*args):
        self._getCanvas().setFont(fontName,fontSize)
        if args: self._leading = args[0]

    def drawString(self, x, y, s, **kwds):
        self._getCanvas().drawString(s,x,y,**kwds)

    def drawCentredString(self, x, y, s, **kwds):
        self._getCanvas().drawCentredString(s,x,y,**kwds)

    def drawRightString(self, x, y, s, **kwds):
        self._getCanvas().drawRightString(s,x,y,**kwds)

    def saveState(self):
        CanvasAdapter.saveState(self)
        currGroup = self._getCanvas().currGroup
        self._savedStates.append(currGroup)
        attrDict = currGroup.attributes
        self._getCanvas().startGroup()

    def rect(self, x, y, w, h, stroke=1, fill=0):
        canv = self._getCanvas()
        style = canv.style
        if not stroke:
            ostroke = style['stroke']
            style['stroke'] = 'none'
        if not fill:
            ofill = canv.style['fill']
            style['fill'] = 'none'
        try:
            canv.rect(x,y,x+w,y+h)
        finally:
            if not stroke:
                style['stroke'] = ostroke
            if not fill:
                style['fill'] = ofill

    def restoreState(self):
        self._getCanvas().endGroup(self._savedStates.pop())
        CanvasAdapter.restoreState(self)

from reportlab.graphics.shapes import DirectDraw
from reportlab.graphics.renderPS import PSCanvas
from reportlab.graphics.renderPM import PMCanvas
from reportlab.graphics.renderSVG import SVGCanvas
from reportlab.pdfgen.canvas import Canvas
class DirectDrawFlowable(DirectDraw):
    def __init__(self,f):
        self.f = f  #our flowable which should be ready to draw

    def drawDirectly(self,renderer):
        canvas = renderer._canvas
        if isinstance(canvas,PMCanvas):
            canv = PMCanvasAdapter(canvas)
        elif isinstance(canvas,PSCanvas):
            canv = PSCanvasAdapter(canvas)
        elif isinstance(canvas,SVGCanvas):
            canv = SVGCanvasAdapter(canvas)
        elif isinstance(canvas,Canvas):
            canv = canvas
        else:
            raise ValueError('cannot adapt to canvas %s from renderer %s' % (canvas,renderer))
        self.f.drawOn(canv,0,0)
