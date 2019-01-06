#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'
__all__=('ttf2ps',)
from reportlab import rl_config
from reportlab.lib.utils import uniChr
from functools import reduce

_template="""10 dict dup begin
/FontType 3 def
/FontMatrix [1 %(unitsPerEm)s div 0 0 1 %(unitsPerEm)s div 0 0] def
/FontBBox [%(fontBBox)s] def
/Encoding 256 array def
0 1 255 {Encoding exch /C32 put}
    for Encoding
    %(charmaps)s

/Metrics %(nglyphs)s dict def
Metrics begin
    %(metrics)s
end
/BBox %(nglyphs)s dict def
BBox begin
    %(bboxes)s
end
/CharacterDefs %(nglyphs)s dict def
CharacterDefs begin
%(chardefs)s
end

/BuildChar
    { 0 begin
    /char exch def
    /fontdict exch def
    /charname fontdict /Encoding get char get def
    fontdict begin
        Metrics charname get 0
        BBox charname get aload pop
        setcachedevice
        CharacterDefs charname get exec
        end
    end
} def
/BuildChar load 0 3 dict put%(uid)s
end
/%(psName)s exch definefont pop
"""
from reportlab.graphics.charts.textlabels import _text2PathDescription
from reportlab.lib.rl_accel import fp_str, escapePDF
from reportlab.graphics.shapes import definePath
def glyphName(c):
    return 'C'+str(c)

def char2glyph(c,last=False):
    return '%s(%s) 0 get /%s put' % (not last and 'dup ' or '',escapePDF(chr(c)), glyphName(c))

def u2P(font,u):
    return _text2PathDescription(u,fontName=font.fontName,fontSize=font.face.unitsPerEm)

def P2PSC(P):
    C = []
    aC = C.append
    n = 0
    for p in P:
        if n>=80:
            aC('\n')
            n = 0
        if isinstance(p,tuple):
            aC(fp_str(*p[1:]))
            aC(p[0][0].lower())
            n += 2+sum(map(len,C[-2:]))
        else:
            aC(p.lower())
            n += 1+len(C[-1])
    return C

def P2PSDef(c,P):
    if not P:
        return '''/%s {} def''' % glyphName(c)
    else:
        return '''/%s {newpath %s fill} def''' % (glyphName(c),' '.join(P2PSC(P)))

def getUID(doc,s):
    #see 
    # open range UniqueId's range from 4000000 to 4999999
    import operator, sha, struct
    return '\n/UniqueID %d def' % (4000000+(reduce(operator.xor,struct.unpack('i'*5,sha.sha(s).digest()))&0x3ffff))

def ttf2ps(font, doc):
    """
    create analytic fonts for inclusion in a postscript document
    """
    state = font._assignState(doc,asciiReadable=False,namePrefix='.RLF')
    state.frozen = 1
    PS = []
    unitsPerEm = font.face.unitsPerEm
    scale = lambda x: int(x*unitsPerEm/1000. + 0.1)
    _fontBBox = list(map(scale,font.face.bbox))
    fontBBox = fp_str(*_fontBBox)
    for i,subset in enumerate(state.subsets):
        n = len(subset)
        psName = font.getSubsetInternalName(i,doc)[1:]
        metrics = []
        bboxes = []
        chardefs = []
        charmaps = []
        nglyphs = 0
        for c in range(n):
            g = subset[c]
            if g==32 and g!=c: continue
            u = uniChr(g).encode('utf8')
            try:
                P = u2P(font,u)
            except:
                P = []
            nglyphs += 1
                #if c==0 and g==0:
                #   P=[('moveTo', 30, 1473), ('lineTo', 30, 0), ('lineTo', 603, 0),('lineTo',603,1473), 'closePath',('moveTo',40,1463),('lineTo',593,1463),('lineTo',593,10),('lineTo',40,10),'closePath']
                #else:
                #   continue
            gn = glyphName(c)
            if g==0 and c==0:
                uw = 633
            else:
                uw = font.stringWidth(u,unitsPerEm)
            if P:
                bb = definePath(P).getBounds()
            else:
                bb = [0,0,uw,0]
            bboxes.append('/%s [%s] def' % (gn,fp_str(*bb)))
            metrics.append('/%s %s def' % (gn, fp_str(uw)))
            chardefs.append(P2PSDef(c,P))
            charmaps.append(char2glyph(c,c==n-1))
        if nglyphs<=0: continue
        metrics = '\n'.join(metrics)
        chardefs = '\n'.join(chardefs)
        charmaps = '\n'.join(charmaps)
        bboxes = '\n'.join(bboxes)
        uid = rl_config.eps_ttf_embed_uid and getUID(doc,metrics+chardefs+charmaps+bboxes+str(unitsPerEm)+fontBBox) or ''
        PS.append(_template % locals())
    return '\n'.join(PS)

    del font.state[doc]
