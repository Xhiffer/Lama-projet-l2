import collections
#!c:/Python/python.exe
_SPACELEN=20
_SPACER= _SPACELEN*' '
def tryImport(name,vname=None,severity='Fatal'):
    try:
        m = __import__(name)
        f = getattr(m,'__file__','')
        if f: f = ' "%s"' % f
        if vname:
            if isinstance(vname, collections.Callable):
                v = vname()
            else:
                v = getattr(m,vname,'[unknown]')
            msg = 'version %s present%s.'  % (v, f)
        else:
            msg = 'present%s.'  % f
    except:
        msg = 'not present. %s!' % severity
    return '%s%s%s' % (name,max(_SPACELEN-len(name),1)*' ',msg) 
def main():
    import sys
    hexversion, platform, executable, exec_prefix, path = sys.hexversion, sys.platform, sys.executable, sys.exec_prefix, sys.path
    path = ('\n'+_SPACER).join(path)
    print('''
Python version:     %(hexversion)x
Python executable:  %(executable)s
Python exec prefix: %(exec_prefix)s
Python path:        %(path)s

Dependencies:''' % locals())

    def PIL_VERSION():
        from PIL import Image
        return Image.VERSION
    def Pmw_VERSION():
        from Pmw import version
        return version()
    for name, vname, severity in (
                                ('reportlab','Version','Fatal you need this'),
                                ('_rl_accel','version','Needed for speed'),
                                ('sgmlop',None,'Needed for paragraph speed'),
                                ('zlib',None,'Required for page compression'),
                                ('PIL',PIL_VERSION,'Required for PDF  & renderPM images.'),
                                ('_renderPM','_version','Required for bitmap image renderer.'),
                                ('pyRXP','version','Required for fast validating XML parser.'),
                                ('rlextra','Version','Fatal you need this'),
                                ('Pmw',Pmw_VERSION,'Required for the drawing editor'),
                                ('mx','__version__','Possibly required for datacharts'),
                                ):
        print(tryImport(name,vname,severity))


if __name__=='__main__':
    main()
