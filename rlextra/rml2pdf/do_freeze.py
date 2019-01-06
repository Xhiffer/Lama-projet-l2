#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
if __name__=='__main__': #no run tests
	import os, shutil, sys
	try:
		import Installer
		INSTALLER_DIR=os.path.dirname(Installer.__file__)
	except:
		import rlextra
		INSTALLER_DIR=os.path.join(os.path.dirname(rlextra.__file__),'distro\\tools\\Installer')

	BUILD_DIR='build_freeze'
	NAME='rml2pdf'
	EXE=NAME+'.exe'
	SCRIPT='exemain.py'
	CFG=NAME+'.cfg'
	DEBUG="-d" in sys.argv
	PDEBUG="-pd" in sys.argv

	#these are forced into the EXE
	MISC_DLLS='' #'ws2_32.dll, ws2help.dll'

	def bpath(fn):
		return os.path.join(BUILD_DIR,fn)
	def ipath(fn):
		return os.path.join(INSTALLER_DIR,fn)
	PIL_names=['Image.py',
				'ImagePalette.py',
				'BmpImagePlugin.py',
				'ImageFile.py',
				'GifImagePlugin.py',
				'JpegImagePlugin.py',
				'PpmImagePlugin.py',
				'TiffImagePlugin.py',
				]
	EXCLUDES = 'dospath, posixpath, macpath, tk83, tcl83, _tkinter, pyHnj, _imagingtk, Tkinter, GimpPaletteFile, GimpGradientFile, PIL.ImageTk, FixTk, TkConstants, xmllib'
	INCLUDES='reportlab.platypus.paragraph, reportlab.lib.xmllib'
	for f in PIL_names:
		INCLUDES=INCLUDES+(',PIL.%s'%os.path.splitext(f)[0])
	DIRS=[]

	def force_rm(d):
		'destroy directory d'
		if os.path.isdir(d):
			for p in os.listdir(d):
				force_rm(os.path.join(d,p))
			os.rmdir(d)
		elif os.path.isfile(d):
			os.remove(d)

	DIRS=repr(DIRS)[1:-1]
	cfg='''[MYSINGLEFILE]
name=%(EXE)s
type=FULLEXE
userunw=0
zlib=MYZLIB
misc=%(MISC_DLLS)s
excludes=%(EXCLUDES)s
script=%(SCRIPT)s
debug=%(DEBUG)d

[MYZLIB]
type=PYZ
name=%(NAME)s.pyz
dependencies=%(SCRIPT)s
excludes=%(EXCLUDES)s
includes=%(INCLUDES)s
directories=%(DIRS)s
''' % globals()
	if not '-noclean' in sys.argv: force_rm(BUILD_DIR)
	if not os.path.exists(BUILD_DIR): os.mkdir(BUILD_DIR)
	if not os.path.exists(bpath(SCRIPT)):
		shutil.copyfile(SCRIPT, bpath(SCRIPT))
		open(bpath(CFG),'w').write(cfg)
	cwd = os.getcwd()
	force_rm(EXE)
	os.chdir(BUILD_DIR)
	force_rm(EXE)
	print("<<<<Freezing %(SCRIPT)s to %(EXE)s>>>>"%globals())
	rc = os.system('python%s %s %s %s' % (PDEBUG and "_d" or "",ipath('Builder.py'),DEBUG and "-d" or "",CFG))
	print("return code:", rc)
	DST = os.path.join(cwd,EXE)
	if os.path.isfile(EXE):
		shutil.copyfile(EXE,DST)
		force_rm(EXE)
		print('Moved %(EXE)s to %(cwd)s' % globals())
