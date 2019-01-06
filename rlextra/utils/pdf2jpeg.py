#copyright ReportLab Inc. 2000-2016
#see license.txt for license details
from __future__ import print_function
__version__='3.3.0'
'''
Attempt at making a fairly general pdf --> jpeg conversion using Ghostscript

'''
__all__=('normalize_gs_device','gsExeFind','epsBBox','pdf2jpeg','epsConvert','gsConvert','pdfConvert','pdfBBox')
import sys, os, glob, subprocess, re
from reportlab.lib.utils import open_and_read

def _cleanFiles(pat):
    try:
        list(map(os.remove, glob.glob(pat)))
    except:
        pass
    return glob.glob(pat)

def gsExeFind(gsExe=None):
    if not gsExe:
        from rlextra.utils.buildutils import find_exe
        known_places = []
        if sys.platform=='win32':
            exeName = 'gswin32c'
            known_places = (
                    list(sorted(glob.glob(r'C:\Program Files\gs\gs*\bin')))
                    +list(sorted(glob.glob(r'c:\Program Files (x86)\gs\gs*\bin')))
                    )
            if 'RL_GS_BIN' in os.environ:
                known_places.append(os.environ['RL_GS_BIN'])
        else:
            exeName = 'gs'
        gsExe = find_exe(exeName,known_places=known_places)
    if sys.platform in ('win32',):
        gsExe = gsExe.strip('"')
    return gsExe

_device2ext = dict( pswrite='ps',epswrite='eps',pdfwrite='pdf',jpeg='jpg',
                    png16m='png',pnggray='png',png256='png',png16='png',pngmono='png',
                    tiffgray='tif', tiff12nc='tif', tiff24nc='tif', tiff32nc='tif',
                    tiffsep='tif', tiffcrle='tif', tiffg3='tif', tiffg32d='tif',
                    tiffg4='tif', tifflzw='tif', tiffpack='tif',
                    bmpmono='bmp',bmpgray='bmp',bmpsep1='bmp',bmpsep8='bmp',
                    bmp16='bmp',bmp256='bmp',bmp16m='bmp',bmp32b='bmp',
                    )

def normalize_gs_device(odevice):
    K = list(_device2ext.keys())
    device = str(odevice).lower()
    if device not in K:
        d = device+'write'
        if d in K:
            device = d
        else:
            raise ValueError('Unsupported gs device "%s"' % odevice)
    return device

def _checkOutputFiles(pat,fn,out,err,verbose=0):
    F = glob.glob(pat)
    if not F:
        raise ValueError('No files produced from "%s"\ngs returned this output\n"""%s"""\nand error"""%s"""' %(fn,out,err))
    if verbose>1 and out:
        print(out, file=sys.stderr)
    if verbose and err:
        print(err, file=sys.stderr)
    return F

def _prepare(fn,outDir,ext,device,outfile=None,gsExe=None):
    if outDir is None:
        outDir = os.path.dirname(fn)
        if not outDir:
            outDir = '.'
    if outDir=='.':
        outDir = os.getcwd()
    if ext is None:
        ext=_device2ext[device]
    if outfile:
        outfile = os.path.splitext(os.path.basename(outfile))[0]
        if '%' in outfile:
            outfile = outfile.replace('%','_')+'%04d'
    else:
        outfile = os.path.splitext(os.path.basename(fn))[0].replace('%','_')+'-page%04d'
    outfile = os.path.join(outDir,outfile+'.'+ext)
    pat = outfile.replace('%04d','*')
    F=_cleanFiles(pat)
    if F:
        raise ValueError('Cannot clean output files for "%s"' % fn)
    return gsExeFind(gsExe),pat,outfile

def _run(ARGS,input=None):
    p = subprocess.Popen(ARGS,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
    out, err = p.communicate()
    return out,err

def pdf2jpeg(fn,scale=0.125, outDir='.', gsExe=None, device='jpeg', ext=None):
    '''
    Create scaled jpeg versions of the pages in a pdf file.
    The filename will be
        basename-page0001.jpg for the first page
        basename-page0002.jpg for the second page etc

    fn      filename of the pdf(or eps) to be converted
    scale   the scalefactor default 1/8th, ignored for
            epswrite/pdfwrite device
    outDir  the folder to place outputs
            None = parallel
            default = '.'
    gsExe   The path to the ghostscript exe file
            if None we attempt to find it ourselves
    device  the output device name defaults to jpeg
            another suitable device is pdfwrite
    ext     the output ext the default is None
            if None then we use .jpg for jpeg and pdf
            for pdfwrite
    '''
    outfile=None
    return pdfConvert(fn, None, scale, outDir, device, ext,True,outfile,'art',0,gsExe)

def epsBBox(fn,bbpat=re.compile(r'^\s*%%boundingbox:\s*(.*)\s*$',re.I|re.M)):
    '''
    read an eps file and attempt to obtain its bounding box

    >>> cleanup()
    >>> x=pdfConvert('zzzdingo.pdf',scale=0.5,device='eps',outfile='zzzdingo.eps')
    >>> assert x and os.path.isfile(os.path.basename(x[0]))
    >>> print epsBBox('zzzdingo.eps')
    [0, 0, 100, 50]
    '''
    text = open_and_read(fn)
    m=bbpat.search(text)
    if not m:
        raise ValueError('Cannot find bounding box in "%s"' % fn)
    bb = m.group(1).strip().split()
    if len(bb)!=4: 
        raise ValueError('Not enough bounding box entries "%s" found in "%s"' % (m.group(0).strip(),fn))
    try:
        return list(map(float,bb))
    except:
        raise ValueError('Bad bounding box entries "%s" found in "%s"' % (m.group(0).strip(),fn))

def _ffmt(f):
    return ('%.6f' % f).rstrip('0').rstrip('.')

def gsConvert(fn,bb,size,scale,outDir,device,ext,preserveAspectRatio,outfile,gsExe,gsExtraArgs=[],pdfMode=0,verbose=0, antialiasing=4, quality=85, useCropBox=0):
    device = normalize_gs_device(device)
    owidth = bb[2]-bb[0]
    oheight = bb[3]-bb[1]
    if not size:
        if scale:
            if isinstance(scale,float):
                xscale = yscale = scale
            else:
                xscale, yscale = scale
        else:
            xscale = yscale = 1
        width = owidth*xscale
        height = oheight*yscale
    else:
        width,height = size
        width = (width is None and owidth or min(width,1))
        height = (height is None and oheight or min(height,1))
        xscale = width/float(owidth)
        yscale = height/float(oheight)
    if preserveAspectRatio and xscale!=yscale:
        xscale = yscale = min(xscale,yscale)
        width = owidth * xscale
        height = oheight * yscale
    if device in ('png','jpeg'):
        width = int(width)
        height = int(height)
    gsExe,pat,outfile = _prepare(fn,outDir,ext,device,outfile,gsExe)
    ARGS = [gsExe, '-q', '-dSAFER', '-dNOPAUSE', '-dBATCH', '-dTextAlphaBits=%d'%antialiasing, '-dGraphicsAlphaBits=%d'%antialiasing, '-dJPEGQ=%d'%quality, '-sOutputFile=%s'%outfile, '-sDEVICE=%s'%device]
    if not pdfMode: ARGS += ['-dDEVICEWIDTHPOINTS='+_ffmt(width),'-dDEVICEHEIGHTPOINTS='+_ffmt(height),'-DFIXEDMEDIA']
    if useCropBox: ARGS += ['-dUseCropBox']
    ARGS += gsExtraArgs
    if device=='pdfwrite': ARGS += ['-c','.setpdfwrite']
    if pdfMode:
        ARGS += ['-r%sx%s' % (_ffmt(72*xscale),_ffmt(72*yscale))]
    else:
        ARGS += ['-c','%s %s translate %s %s scale' % (_ffmt(-bb[0]*xscale),_ffmt(-bb[1]*yscale),_ffmt(xscale),_ffmt(yscale))]
    ARGS += ['-f',fn]
    out,err = _run(ARGS)
    return _checkOutputFiles(pat,fn,out,err,verbose=verbose)

def epsConvert(fn, size=None, scale=None, outDir='.', device='jpeg', ext=None, preserveAspectRatio=True,outfile=None,gsExe=None,gsExtraArgs=[],verbose=0):
    '''
    Convert an eps file to another format using GS
    size either None or (width,height)
    scale either None or (scalex,scaley) or scalexandy
    outDir is where the file(s) will be made
    device is the desired conversion mode (jpeg,png,pdf,ps,eps etc etc)
    ext desired extension or None to get an appropriate one based on the device
    preserveAspectRatio set to false to get skewed output that exactly fits your specified width x height
    outfile None to get an automatically named file or use the extensionless part of outfile
    gsExe   path to your gs program or None when it will be searched for
    gsExtraArgs extra arguments passed to gs

    If you don't set size then scale will be used. If unset the scale will default to 1 for both x and y.

    >>> cleanup()
    >>> x=pdfConvert('zzzdingo.pdf',scale=0.5,device='eps',outfile='zzzdingo.eps')
    >>> assert x and os.path.basename(x[0])=='zzzdingo.eps' and os.path.isfile('zzzdingo.eps')
    >>> x=epsConvert('zzzdingo.eps',scale=0.5,device='jpeg',outfile='zzzdingo.jpg')
    >>> assert x and os.path.basename(x[0])=='zzzdingo.jpg' and os.path.isfile('zzzdingo.jpg')
    >>> x=epsConvert('zzzdingo.eps',scale=0.5,device='pdf',outfile='zzzdingo1.jpg')
    >>> assert x and os.path.basename(x[0])=='zzzdingo1.pdf' and os.path.isfile('zzzdingo1.pdf')
    '''
    bb = epsBBox(fn)
    return gsConvert(fn,bb,size,scale,outDir,device,ext,preserveAspectRatio,outfile,gsExe,gsExtraArgs,verbose=verbose)

def pdfBBox(fn,boxName='art',pageNo=0):
    ''' Bounding box for a pdf

    >>> cleanup()
    >>> print pdfBBox('zzzdingo.pdf')
    [0, 0, 200, 100]
    '''
    from rlextra.pageCatcher.pdfexplorer import PdfExplorer
    boxName = boxName.capitalize()
    if boxName.endswith('box'):
        boxName = boxName[-3:]+'Box'
    elif not boxName.endswith('Box'):
        boxName += 'Box'
    meth = 'get'+boxName
    if not hasattr(PdfExplorer,meth):
        raise ValueError('No box method for "%s" in PdfExplorer' % boxName)
    p = PdfExplorer(fn)
    try:
        return getattr(p,meth)(pageNo)
    except KeyError:
        try:
            return p.getMediaBox(pageNo)
        except:
            et,ev = list(map(str,sys.exc_info()[:2]))
            raise ValueError('method %s failed for file "%s"\n%s:%s' % (meth,fn,et,ev))

def pdfConvert(fn, size=None, scale=None, outDir='.', device='jpeg', ext=None, preserveAspectRatio=True,outfile=None, boxName='art',pageNo=0,gsExe=None,gsExtraArgs=[],verbose=0, antialiasing=4, quality=85, useCropBox=0):
    '''
    Convert a pdf file to another format use GS
    size either None or (width,height)
    scale either None or (scalex,scaley) or scalexandy
    outDir is where the file(s) will be made
    device is the desired conversion mode (jpeg,png,pdf,ps,eps etc etc)
    ext desired extension or None to get an appropriate one based on the device
    preserveAspectRatio set to false to get skewed output that exactly fits your spcified width x height
    outfile None to get an automatically named file or use the extensionless part of outfile
    boxName which of the many boxes to use. if the first fails we drop back to media
    pageNo which page to get the box for
    gsExe   path to your gs program or None when it will be searched for
    gsExtraArgs extra arguments passed to gs

    If you don't set size then scale will be used. If unset the scale will default to 1 for both x and y.

    >>> cleanup()
    >>> x=pdfConvert('zzzdingo.pdf',scale=0.5,device='jpeg')
    >>> assert x and os.path.isfile(os.path.basename(x[0]))
    >>> x=pdfConvert('zzzdingo.pdf',scale=0.5,device='eps',outfile='zzzdingo.eps')
    >>> assert x and os.path.isfile(os.path.basename(x[0]))
    '''
    if isinstance(useCropBox,str): useCropBox=int(useCropBox)
    bb = pdfBBox(fn,boxName,pageNo)
    return gsConvert(fn,bb,size,scale,outDir,device,ext,preserveAspectRatio,outfile,gsExe,gsExtraArgs,pdfMode=1,verbose=verbose, antialiasing=antialiasing, quality=quality, useCropBox=useCropBox)

def test():
    from reportlab.pdfgen.canvas import Canvas
    c = Canvas('zzzdingo.pdf',(200,100))
    c.drawString(72,72,'Hello World')
    c.showPage()
    c.save()
    def cleanup(keepBase=True):
        from .buildutils import kill
        for x in glob.glob('zzzdingo*.*'):
            if keepBase and x=='zzzdingo.pdf': continue
            kill(x)
    import doctest
    doctest.testmod(extraglobs=dict(os=os,cleanup=cleanup))
    cleanup(0)

if __name__=='__main__':
    device = 'jpeg'
    boxName = 'art'
    scale = 0.125
    verbose = 0
    useCropBox = 0
    argv = sys.argv[1:]

    if '--help' in argv:
        print("""pdf2jpeg options pdffile
    options
    --scale=factor
            the scalefactor default 1/8th, ignored for
            epswrite/pdfwrite device
    --outDir=dir
            the folder to place outputs
            None = parallel
            default = '.'
    --device=jpeg|pdf
            the output device name defaults to jpeg
            another suitable device is pdfwrite
    --boxName=box
            pdfbox name default is art
    --verbose=value
            verbosity""")
        sys.exit(0)

    if not len(argv):
        test()
    else:
        for a,d in (('device','jpeg'),('boxName','art'),
                    ('scale',0.125),('verbose',0),
                    ('useCropBox',0),
                    ('outDir','.'),
                    ):
            ox = '--'+a+'='
            x = [x for x in argv if x.startswith(ox)]
            list(map(argv.remove,x))
            v = x and x[0].lstrip(ox) or d
            v = type(d)(v)
            globals()[a] = v

        for x in argv:
            func = x.lower().endswith('.eps') and epsConvert or pdfConvert
            kwds = dict(size=None, scale=scale,
                    outDir=outDir, device=device,
                    ext=None, preserveAspectRatio=True,
                    outfile=None,
                    gsExe=None,gsExtraArgs=[],
                    verbose=verbose,
                    )
            if func==pdfConvert:
                kwds.update(dict(pageNo=0,boxName=boxName,useCropBox=useCropBox))
            func(x,**kwds)
