#!/usr/bin/env python
#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'
'''
This module implements a separating colour postscript renderer
'''
import time, os
from reportlab.pdfbase.pdfmetrics import getFont # for font info
from reportlab.lib.utils import getBytesIO
from reportlab.lib.rl_accel import fp_str
from reportlab.lib.utils import rawBytes, asUnicode
from reportlab.lib.colors import CMYKColor, PCMYKColor, Color, black, white, colorDistance, toColor
from rlextra.graphics.sep_ops import SEP_OPS
from reportlab.graphics.renderPS import PSCanvas, draw
from reportlab import rl_config, isPy3

class PSCanvas_SEP(PSCanvas):
    "Color-separating Encapsulated Postscript canvas"
    def __init__(self,size=(300,300),
                    PostScriptLevel=2,
                    #cmykColors=None,
                    title='',
                    dept='',
                    company='',
                    ttf_embed=None,
                    ):
        self.cmykColors = [] #cmykColors list is built up as one goes
        self.dept = dept
        self.company = company
        self.title = title
        self.delayedFonts = []
        self.fontMapping = {}
        if ttf_embed is None: ttf_embed = rl_config.eps_ttf_embed
        self._ttf_embed = ttf_embed
        PSCanvas.__init__(self,size,PostScriptLevel)

    def _prolog(self,dviPreview=None):
        pColors = {}
        spColors = {}
        sCC = ''
        cmykCC = ''
        for c in self.cmykColors:
            if hasattr(c, 'spotName') and c.spotName: # is not None.
                if c.spotName not in spColors:
                    spColors[c.spotName] = 1
                    if sCC=='':
                        sH0='%%DocumentCustomColors:'
                        sH1='%%CMYKCustomColor:'
                    else:
                        sH0='%%+'
                        sH1='%%+'
                    sCC = '%s%s (%s)\n'%(sCC,sH0,c.spotName)
                    cmykCC = '%s%s %s (%s)\n' % (cmykCC,sH1,fp_str(c.cmyk()),c.spotName)
            else:
                c, m, y, k = c.cyan, c.magenta, c.yellow, c.black #_cmyk
                if c: pColors['cyan']= 1
                if m: pColors['magenta']= 1
                if y: pColors['yellow']= 1
                if k: pColors['black']= 1
        if pColors!={}:
            pC = '%%DocumentProcessColors:'
            for c in list(pColors.keys()):
                pC = pC+' '+c
            pC = pC + '\n'
        else:
            pC = ''

        if self._fontsUsed:
            _fontsUsed = '%%DocumentFonts: '+('\n%%+ '.join(self._fontsUsed))+'\n'
        else:
            _fontsUsed = ''

        if self.delayedFonts:
            from .ttf2ps import ttf2ps
            analyticFonts = '\n%%analytic fonts\n' + ('\n'.join([ttf2ps(f,self) for f in self.delayedFonts]))
        else:
            analyticFonts = ''

        return '''\
%!PS-Adobe-3.0 EPSF-3.0
%%BoundingBox: 0 0 '''+("%d %d"%(self.width,self.height))+'''
%%Title: ('''+self.title+''')
'''+pC+sCC+cmykCC+_fontsUsed+'''
%%CreationDate: '''+time.strftime('(%d/%b/%Y) (%H:%M:%S GMT)', time.gmtime(time.time()))+'''
%%Creator: ReportLab+renderPS_SEP 1.01
%%For: ('''+self.dept+''') ('''+self.company+''')
%%Extensions: CMYK
%%EndComments
%%BeginProlog
'''+SEP_OPS+'''
'''+(dviPreview or '') + '''
%%EndProlog
%%BeginSetup
sep_ops begin
50 dict begin % temp dict for variable definitions
%%EndSetup

/pgsave save def
/m {moveto} def
/l {lineto} def
/c {curveto} bind def
''' + analyticFonts

    def _epilog(self):
        return '''pgsave restore
showpage
%%Trailer
end % temp dictionary
end % sep_ops
%%EOF
'''
    def _setCMYKColor(self,c):
        KO = getattr(c,'knockout',None)
        if KO is None: KO = getattr(rl_config,'PS_SEP_KNOCKOUT',1)
        over = KO and 'false' or 'true'
        spotName = getattr(c,'spotName',None)
        if spotName:
                return '%s (%s) 0\n/tint exch def\nfindcmykcustomcolor %s setoverprint\ntint %s exch sub setcustomcolor' % (fp_str(c.cmyk()),spotName,over,c._density_str())
        else:
                d = c.density
                return '%s setcmykcolor %s setoverprint' % (fp_str(c.cyan*d,c.magenta*d,c.yellow*d,c.black*d),over)

    def _rgbFind(self,color):
        "see if it matches any existing color in my list"
        C = self.cmykColors
        if isinstance(color,(list,tuple)):
            if len(color)==3: color = Color(color[0],color[1],color[2])
            elif len(color)==4: color = CMYKColor(color[0],color[1],color[2],color[3])
            else: raise ValueError("bad color %s"%repr(color))
        isCMYK = isinstance(color, CMYKColor)
        if not isCMYK:
            if isinstance(color,str):
                color = toColor(color)
            if colorDistance(color,black)<1e-8:
                isCMYK = 1
                color = PCMYKColor(0,0,0,100,100)
            elif colorDistance(color,white)<1e-8:
                isCMYK = 1
                color = PCMYKColor(0,0,0,0,100)
        rgb = color.red, color.green, color.blue
        if isCMYK:
            if color not in C: C.append(color)
            return self._setCMYKColor(color)
        else:
            for c in C:
                if (c.red, c.green, c.blue) == rgb:
                    return self._setCMYKColor(c)

        return '%s setrgbcolor' % fp_str(rgb)

    def _postscript(self,dviPreview=None):
        '''create and return the postscript'''
        self.code.insert(0,self._prolog(dviPreview=dviPreview))
        self._t1_re_encode()
        self.code.append(self._epilog())
        r = self._sep.join(self.code)
        del self.code[0], self.code[-1]
        return r

    def save(self,fn, preview=None, dviPreview=None):
        cf = not hasattr(fn,'write')
        if cf: 
            f = open(fn,'wb')
        else:
            f = fn
        try:
            ps = self._postscript(dviPreview)
            if preview:
                import struct
                A = (b'\xc5',b'\xd0',b'\xd3',b'\xc6')if isPy3 else (chr(0xc5),chr(0xd0),chr(0xd3),chr(0xc6))
                hdr=struct.pack(*(
                                ("<4c7i",)
                                +A
                                +( 32,len(ps),0,0,32+len(ps),len(preview),0xffff)
                                )
                                )
                f.write(hdr)
                f.write(rawBytes(ps))
                f.write(preview)
            else:
                f.write(rawBytes(ps))
        finally:
            if cf:
                f.close()
        if cf and os.name=='mac':
            from reportlab.lib.utils import markfilename
            markfilename(fn,ext='EPSF')

    def setColor(self, color):
        if self._color!=color:
            self._color = color
            if color:
                self.code.append(self._rgbFind(color))

    def setFont(self,font,fontSize,leading=None):
        if self._font!=font or self._fontSize!=fontSize:
            self._font = font
            self._fontSize = fontSize
            fontObj = getFont(font)
            if self._ttf_embed and fontObj._dynamicFont:
                fontObj._assignState(self,asciiReadable=False,namePrefix='.RLF')
                self._curSubset = -1
            self._fontCodeLoc = len(self.code)
            self.code_append('')

    def drawString(self, x, y, s, angle=0):
        if self._fillColor != None:
            fontSize = self._fontSize
            fontObj = getFont(self._font)
            dynamicFont = fontObj._dynamicFont
            embedding = self._ttf_embed and dynamicFont
            if not embedding and not self.code[self._fontCodeLoc]:
                psName = fontObj.face.name
                self.code[self._fontCodeLoc]='(%s) findfont %s scalefont setfont' % (psName,fp_str(fontSize))
                if psName not in self._fontsUsed:
                    self._fontsUsed.append(psName)
            self.setColor(self._fillColor)
            if angle!=0:
                self.code_append('gsave %s translate %s rotate' % (fp_str(x,y),fp_str(angle)))
                x = y = 0
            if embedding:
                i = 0
                s = asUnicode(s)
                for subset, t in fontObj.splitString(s, self):
                    if subset!=self._curSubset:
                        psName = fontObj.getSubsetInternalName(subset, self)[1:]
                        sf = '(%s) findfont %s scalefont setfont' % (psName,fp_str(fontSize))
                        if not self.code[self._fontCodeLoc]:
                            self.code[self._fontCodeLoc] = sf
                        else:
                            self.code_append(sf)
                        self._curSubset = subset
                    self.code_append('%s m (%s) show ' % (fp_str(x,y),self._escape(t)))
                    j = i + len(t)
                    x += fontObj.stringWidth(s[i:j],fontSize)
                    i = j
            elif dynamicFont:
                s = self._escape(s)
                self.code_append('%s m (%s) show ' % (fp_str(x,y),s))
            else:
                self._issueT1String(fontObj,x,y,s)
            if angle!=0:
                self.code_append('grestore')

"""Usage:
    import renderPS_SEP
    renderPS_SEP.draw(drawing, canvas, x, y)
Execute the script to see some test drawings."""
from reportlab.graphics.shapes import *

def _dviPreview(drawing):
    #not yet implemented
    raise 'Not implemented'
#   gd=renderGD.drawToGD(d)
    gdWidth = gd._im.width
    gdHeight = gd._im.height
    data=['%%BeginPreview: '+('%d %d %d %d' %(gdWidth,gdHeight,1,gdHeight))]
    for i in range(gdHeight):
        b = 0
        n = 7
        row='%'
        for j in range(gdWidth):
            p = gd._im.getPixel((i,j))
            if p!=gd.black and gd!=gd.white: p = 1
            b = b | (p<<n)
            if n:
                n = n - 1
            else:
                n = 7
                row = row + ('%02X'%b)
                b = 0
        if n!=7:
            row = row + ('%02X'%b)
        data.append(row)
    data.append('%%EndPreview')
    data='\n'.join(data)
    return data

def _preview(d,preview):
    '''create a device dependent preview image from drawing d'''
    from reportlab.graphics import renderPM
    if isinstance(preview,(int,float)):
        assert preview>0, "negative scaling is forbidden"
        g = d
        d = Drawing(g.width*preview, g.height*preview)
        g.transform = (preview,0,0,preview,0,0) #scale so it fits
        d.add(g)
    pilf = getBytesIO()
    transparent = getattr(g,'preview_transparent',None) or rl_config.eps_preview_transparent
    kwds = dict(fmt='TIFF')
    if transparent:
        configPIL = {}
        bg = configPIL['transparent'] = toColor(transparent)
        kwds['configPIL'] = configPIL
        kwds['bg'] = bg.int_rgb()
    renderPM.drawToFile(d,pilf,**kwds)
    return pilf.getvalue()

def drawToFile(d,fn,
                showBoundary=rl_config.showBoundary,
                dviPreview=None,
                title='',
                company='',
                dept='',
                preview=0,
                ttf_embed=None,
                ):
    c = PSCanvas_SEP((d.width,d.height),
                #cmykColors=cmykColors,
                title=title,
                company=company,
                dept=dept,
                ttf_embed=ttf_embed,
                )
    draw(d, c, 0, 0, showBoundary=showBoundary)
    #c.save(fn,preview=preview and _preview(d,preview),dviPreview=dviPreview and _dviPreview(d) or None)
    c.save(fn,
           preview=preview and _preview(d,preview),
           dviPreview='')

def drawToString(d,
                showBoundary=rl_config.showBoundary,
                dviPreview='',
                title='Diagra EPS',
                company='ReportLab',
                dept='',
                preview=0):
    "Outputs the EPS to a string in memory"
    f = getBytesIO()
    drawToFile(d, f,
                dviPreview=dviPreview,
                title = title,
                dept = dept,
                company = company,
                preview = preview,
                showBoundary=showBoundary)
    return f.getvalue()

if __name__=='__main__':
    w = 6*72
    h = 3*72
    D = Drawing(w,h)
    dX = w/5.0
    dY = h/5.0
    for i in range(5):
        x = i*dX + 36
        y = i*dY + 18
        c = PCMYKColor(100, 65, 0, 30, spotName='PANTONE 288 CV',density=i*20)
        if i%2:
            D.add(Circle(x,y,36,fillColor=c,strokeColor=black))
        else:
            D.add(Rect(x,y,36,18,fillColor=c,strokeColor=black))
    fn = 'renderPS_SEP.eps'
    drawToFile( D,fn,
                title = fn,
                dept = 'Robin',
                company = 'ReportLab',
                preview = 1,
                showBoundary=rl_config.showBoundary)
