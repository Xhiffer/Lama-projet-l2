def __bootstrap():
    import sys, zlib, marshal
    from reportlab.lib.rl_accel import asciiBase85Decode
    from reportlab.lib.utils import rl_exec
    mname = 'rlextra.rml2pdf.rml2pdf_%d%d%s' % (sys.version_info[:2]+('c' if not sys.flags.optimize else 'o',))
    m = {}
    rl_exec('import %s as m' % mname, m)
    m = m['m']
    c=sys.modules[__name__]
    N=dict([(a,getattr(c,a)) for a in '__file__ __name__ __path__ __package__'.split() if hasattr(c,a)])
    rl_exec(marshal.loads(zlib.decompress(asciiBase85Decode(m.__code__))),c.__dict__)
    c.__dict__.update(N)
    del sys.modules[mname]

__bootstrap()
del __bootstrap

if __name__=='__main__':
    import sys
    main(exe=1,fn=sys.argv[1:])
