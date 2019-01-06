__all__=(
        'getCaptcha',
        )
_allowed = 'ABCDEFGHJKLMNPQRTUVWYX3479'
_mx = len(_allowed)-1
def getCaptcha(n=5,fontName='Courier',fontSize=14,text=None,fillColor=None):
    '''return n random chars in a string and in a byte string structured
    as a GIF image'''
    from reportlab.graphics.shapes import Drawing, Group, String, \
        rotate, skewX, skewY, mmult, translate, Rect
    if not text:
        from random import randint, uniform
        text=''.join([_allowed[randint(0,_mx)] for i in range(n)])
    else:
        uniform = lambda l,h: 0.5*(l+h)
        n = len(text)
    baseline = 0
    x = 0
    G0 = Group()
    for c in text:
        x += 1
        A = translate(x,uniform(baseline-5,baseline+5))
        A = mmult(A,rotate(uniform(-15,15)))
        A = mmult(A,skewX(uniform(-8,8)))
        A = mmult(A,skewY(uniform(-8,8)))
        G = Group(transform=A)
        G.add(String(0,0,c,fontname=fontName,fontSize=fontSize))
        G0.add(G)
        x0,y0,x1,y1 = G0.getBounds()
        x = 1+x1
    G0.transform=translate(2-x0,2-y0)
    W = 4+x1-x0
    H = 4+y1-y0
    D = Drawing(W,H)
    if fillColor:
        from reportlab.lib.colors import toColor
        D.add(Rect(0,0,W,H, fillColor = toColor(fillColor),strokeColor=None))
    D.add(G0)
    return text, D.asString('gif')

if __name__=='__main__':
    text,g=getCaptcha()
    f=open('ci.gif','wb')
    f.write(g)
    f.close()
    print(text,'written to ci.gif')
