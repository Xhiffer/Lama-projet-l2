#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
#
##################################################################################
# This script assumes that McMillan's installer is in in c:\python\devel\Installer
#
#My DLLs are located as follows
#
# 1) reportlab\lib\pyHnj.pyd
#                 \_rl_accel.pyd
#                 \sgmlop.pyd
# 
# 2) rlextra\radxml\pyRXP.pyd
# 
# The original rml2pdf.py script is wrapped by rlextra\rml2pdf\exemain.py;
# the main intention of the wrapper is to allow for some primitive
# debugging and also stuff to force the path into a controlled state and
# therefore avoid clashing with existing python installations.
# 
# To make an exe try the following
# 
# cd \python\rlextra\rml2pdf
# 
# do_freeze.py -clean
# 
# if this runs OK to completion it should be able to make an exe and then
# copy it parallel to rml2pdf.py. Even so it doesn't follow that stuff
# works OK as the awful PIL location problem and or some other dlls may
# intervene and crash things.
##################################################################################
from __future__ import print_function
import sys, os, string

def list_print(name,L):
	print(name)
	for l in L:
		print('  ',l)

def items_print(name,L):
	for l, k in list(L.items()):
		print('  %s["%s"]="%s"' %(name,l,k))

def try_import(name):
	print('import',name, end=' ')
	try:
		exec('import '+name)
		print('succeeded')
		return 1
	except ImportError:
		print('failed')
		return 0

def getFlag(name,nextVal=0):
	r = name in sys.argv
	if r:
		x = sys.argv.index(name)
		del sys.argv[x]
		if nextVal:
			r = sys.argv[x]
			del sys.argv[x]
	return r

if __name__ == '__main__': #NO RUN TESTS
	try:
		import archive_rt
		exe = 1
		if getFlag('-rt_verbose'): archive_rt._verbose = 1
	except ImportError:
		exe = 0
	from reportlab import rl_config
	rl_config.defaultImageCaching = 0
	from reportlab.lib import pagesizes
	letter = getFlag('-letter')
	if letter:
		rl_config.defaultPageSize = pagesizes.letter
	from rlextra.rml2pdf import rml2pdf
	version = rml2pdf.version
	def Usage(msg=None,e=0):
		if msg:
			print(msg)
		print('Usage:\n  rml2pdf [options] rmlfiles....')
		print(' files rml files to be converted to pdf')
		print('    options')
		print('    -help     give this help')
		print('    -letter   paper size letter (default is A4)')
		print('    -path     print python path')
		print('    -env      print python environent')
		print('    -outdir   directory where output is stored, default')
		print('              is parallel to the input file')
		print('    -verbose  be verbose')
		print('    -import   show some python imports')
		print('    -version  show the rml2pdf version (%s)' % version)
		print('    -arcview  show the exe contents')
		print('    -arcviewx show the exe and pyz contents')
		print('    -timing   show the time used')
		sys.exit(e)

	if getFlag('-help'): Usage()

	showPath = getFlag('-path')
	showEnv = getFlag('-env')
	showImport = getFlag('-import')
	verbose = getFlag('-verbose')
	noconf = getFlag('-noconfirm')
	outDir = getFlag('-outdir',1)
	showVersion = getFlag('-version')
	arcView = getFlag('-arcview')
	if getFlag('-arcviewx'): arcView=2
	timing = getFlag('-timing')
		
	if not outDir: outDir = None
	if verbose: showPath = showEnv = showImport = 1
	if showPath: list_print('Initial sys.path',sys.path)
	if exe:
		exeDefinedPath = string.split(os.environ['PYTHONPATH'],';')
		newPath = []
		for p in sys.path:
			if p in exeDefinedPath: newPath.append(p)

		if verbose: print('Running as Exe')
		sys.path = newPath
		if showPath:
			list_print('Final sys.path', sys.path)
			list_print('sys.importers ', sys.importers)
		if arcView:
			try:
				from Installer.ArchiveViewer import printToc
				printToc(sys.argv[0],arcView==2)
			except:
				import traceback
				print("Can't print Archive Contents")
				traceback.print_exc()
	else:
		if verbose: print('Normal python')
	if showEnv: items_print('os.environ',os.environ)
	if showImport:
		try_import('PIL')
		try_import('reportlab.lib._rl_accel')
		try_import('rlextra.radxml.pyRXP')
	if verbose or showVersion:
		print('rml2pdf version %s' % version)
	FN=sys.argv[1:]
	for fn in FN:
		if not os.path.isfile(fn):
			Usage("'%s' is not a file" % fn, 1)

	if timing:
		import time
		t0 = time.time()
	rml2pdf.main(exe=exe,fn=FN,quiet=noconf,outDir=outDir)
	if timing: print('That took %.2f"' % (time.time()-t0))
