#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
from __future__ import print_function
__version__='3.3.0'
import os, sys, string, traceback, re, glob, struct, time
from shutil import copy2
from reportlab.lib.utils import rl_exec
path_join = os.path.join
path_basename = os.path.basename
path_dirname = os.path.dirname
isFile = os.path.isfile
isDir = os.path.isdir
isLink = os.path.islink
normPath = os.path.normpath
os_sep = os.sep

try:
	set
except NameError:
	from sets import Set as set	#backward compatibility

if hasattr(sys, 'version_info'):
	_pyvers = sys.version_info[0]*10 + sys.version_info[1]
else:
	toks = string.split(sys.version, '.', 2)
	_pyvers = int(toks[0])*10 + int(toks[1])

def errorMsg(msg,exit=1):
	print(msg, file=sys.stderr)
	if exit is not None: sys.exit(exit)

def getFlag(name,nextVal=0,default=None):
	r = name in sys.argv
	if nextVal and not r:
		name += '='
		for x in sys.argv[1:]:
			if x.find(name)==0:
				name = x
				r = '='.join(name.split('=')[1:])
				nextVal = 0
				break
	if r:
		x = sys.argv.index(name)
		del sys.argv[x]
		if nextVal:
			try:
				r = sys.argv[x]
				del sys.argv[x]
			except:
				r = (nextVal>>1)&1
	else:
		r = default
	return r
_verbose = os.environ.get('RL_verbose',0)

def invalidFlags(allowed,trailersOK=0):
	I = []	#invalid flags
	for a in sys.argv[1:]:
		if a[0]=='-':
			if a[:2]=='--' and a.find('=')>0: a = a.split('=')[0]
		elif trailersOK: continue
		if a not in allowed: I.append(a)
	return I

class STDLOG:
	def __init__(self,fn='log.txt'):
		self.log = [sys.__stdout__,open(path_join(path_dirname(sys.argv[0]),fn),'w')]
		sys.stderr = sys.stdout = self

	def write(self,msg):
		for log in self.log:
			log.write(msg)

	def close(self):
		sys.stderr = sys.__stderr__
		sys.stdout = sys.__stdout__
		self.log[1].close()

	def __del__(self):
		self.close()

def installerDir(P=None):
	import rlextra
	D = path_join(path_dirname(rlextra.__file__),'utils','installer')
	if P:
		if type(P) not in (type(()),type([])):
			D = path_join(D,P)
		else:
			for p in P:
				D = path_join(D,p)
	return normPath(D)

def do_exec(cmd, fout=None, sys_exit=1, verbose=None, fail=1, report=None):
	if verbose is None: verbose = _verbose
	i=os.popen(cmd,'r')
	o = i.read()
	if fout: print(o, file=fout)
	i = i.close()
	if fail and i is not None:
		errorMsg('Error: %s\n%s\n' % (cmd,o),sys_exit)
		raise ValueError('external command failure')
	else:
		if verbose>8: print('do_exec(%s)' % repr(cmd), file=sys.stderr)
		if report: report(cmd)

def get_path():
	p = os.environ.get('PATH','')
	if not p:
		for k,v in os.environ.items():
			if k.upper()=='PATH':
				p = v
				break
	return p.split(os.pathsep)

_find_exe_cache = {}
def find_exe(name, doRaise=0, known_places=[]):
	global _find_exe_cache
	if sys.platform=='win32':
		name = '%s.exe' % name

	exe = _find_exe_cache.get(name,None)
	if exe: return exe

	for p in known_places+get_path():
		f = path_join(p,name)
		if isFile(f):
			if ' ' in f: f = '"%s"' % f
			_find_exe_cache[name] = f
			return f

	msg = "Can't find %s anywhere on the path" % name
	if doRaise: raise RuntimeError(msg)
	errorMsg(msg)

def find_exe_nq(name,*args,**kwds):
	exe = find_exe(name,*args,**kwds)
	if ' ' in exe and exe.startswith('"'):
		exe = exe[1:-1]
	return exe

def patchRead(patchFn,filterFunc=None):
	patchFile = open(patchFn,'r')
	patchText = patchFile.read()
	patchFile.close()
	P = []
	C = []
	for i,l in enumerate(patchText.split('\n')):
		if l.startswith('#'): continue
		if l.startswith('---'):
			fn = l.split()
			if len(fn):
				fn = fn[1]
			else:
				raise ValueError('malformed patch line%03d: "%s"' %(i+1,l))
			if C:
				P.append((C[0],'\n'.join(C[1:])))
				C = []
			C.append(fn)
		elif not C:
			raise ValueError('missing patch filename at line%03d: "%s"' %(i+1,l))
		else:
			C.append(l)
	if C:
		P.append((C[0],'\n'.join(C[1:])))
	if filterFunc:
		P = list(filter(filterFunc,P))
	return P

def patchRestore(patchFn,P=None,filterFunc=None):
	if P is None:
		P = patchRead(patchFn,filterFunc=filterFunc)
	out = []
	for x,(fn,p) in enumerate(P):
		ofn = fn+'.org'
		if isFile(ofn):
			kill(fn)
			os.rename(ofn,fn)
			out.append('Restored '+fn)
	return '\n'.join(out)

def patch(patchFn,testOnly=0,keepOld=1,filterFunc=None):
	exe = find_exe('patch',doRaise=1)
	P = patchRead(patchFn,filterFunc=filterFunc)
	try:
		out = []
		for x,(fn,p) in enumerate(P):
			if not isFile(fn):
				out.append('!!! not patching missing file '+fn)
				continue
			ofn = fn+'.out'
			rfn = fn+'.rej'
			kill(ofn)
			kill(rfn)
			cmd = '%s --force -o "%s" -r "%s" "%s"' % (exe,ofn,rfn,fn)
			i,oe = os.popen4(cmd,'t')
			i.write('\n'+p+'\n')
			i.close()
			outerr = oe.read()
			oe.close()
			kill(fn+'.orig')		#in case patch created an unwanted one
			kill(fn+'.out.orig')	#in case patch created an unwanted one
			if isFile(ofn) and not isFile(rfn):
				#success
				if not testOnly:
					if keepOld:
						gfn = fn+'.org'
						kill(gfn)
						os.rename(fn,gfn)
					else:
						kill(fn)
					os.rename(ofn,fn)
				out.append('#### patched '+fn)
				continue
			out.append('!!!!!!!!!!!!!!!!!!!!\n	  failed to patch '+fn)
			out.append('	'+cmd)
			if not isFile(ofn): out.append('file "%s" not created' % ofn)
			if isFile(rfn): out.append('rej file created')
			out.append(outerr.rstrip())
			out.append('!!!!!!!!!!!!!!!!!!!!')
			if not testOnly:
				err = 'Cannot patch "%s" using\n--------------\n%s\n--------------'%(fn,p)
				raise ValueError(err)
			kill(ofn)
			kill(rfn)
	except:
		if keepOld and not testOnly:
			out.append(patchRestore(patchFn,P=P[:x+1],filterFunc=filterFunc))
		t,e,tb = sys.exc_info()
		raise t(t('\n'.join(list(e.args)+out))).with_traceback(tb)
	return '\n'.join(out)

def http_ref_fix(src,fixes,dst=None):
	'''
	src is a folder to be fixed, fixes is a dictionary
	'src relative filename': [http refs]

	for each file
		1) check it exists
		2) replace the http://ref with /ref
		3) ensure the file referenced is created as dst/ref
		4) ensure no http://refs remain in the file
	'''
	import io, traceback, urllib.request, urllib.parse, urllib.error
	if not dst: dst = src
	out = io.StringIO()
	err = io.StringIO()
	for fn,L in fixes.items():
		try:
			fn = path_join(src,fn)
			f = open(fn,'r')
			text = f.read()
			f.close()
			for ref in L:
				if ref.startswith('http://'):
					rref = ref[6:]
				elif ref.startswith('https://'):
					rref = ref[7:]
				text = text.replace(ref,rref)
				dfn = path_join(dst,rref[1:].replace('/',os.sep))
				if not isFile(dfn):
					safe_makedirs(path_dirname(dfn))
					f = open(dfn,'wb')
					f.write(urllib.request.urlopen(ref).read())
					f.close()
					print('Copied',ref,'to',dfn, file=out)
			f = open(fn,'w')
			f.write(text)
			f.close()
		except:
			print('http_fix: Error processing file', fn, file=err)
			traceback.print_exc(file=err)
			continue
		print('http_fix: processed',fn, file=out)
	return out.getvalue(), err.getvalue()

def ext_remove(d,ext):
	'remove .ext n d and subtree'
	if isDir(d):
		for p in os.listdir(d):
			fn = path_join(d,p)
			if isFile(fn) and fn[-len(ext):]==ext:
				os.remove(fn)
			else:
				ext_remove(fn,ext)

def rmdir(d):
	'destroy directory d'
	if isDir(d):
		try:
			os.chmod(d,0o777)
		except:
			pass
		for p in os.listdir(d):
			fn = path_join(d,p)
			if isDir(fn):
				rmdir(fn)
			else:
				remove(fn)
		os.rmdir(d)

def remove(f):
	'destroy an existing file'
	try:
		if not isLink(f):
			try:
				os.chmod(f,0o666)
			except:
				pass
		os.remove(f)
	except OSError:
		pass

def _kill(f):
	'remove a single directory or file unconditionally'
	if isFile(f): remove(f)
	elif isDir(f): rmdir(f)

def kill(f):
	'remove directory or file unconditionally'
	list(map(_kill,glob.glob(f)))

def filesMatch(patterns):
	L = []
	Lappend = L.append
	for p in patterns:
		G = glob.glob(p)
		while G:
			g = G[-1]
			del G[-1]
			if isDir(g):
				G.extend(listAllFiles(g,rel=0))
			else:
				Lappend(g.replace(os.sep,'/'))
	return L

def copyTree(src, dst, symlinks=0,excludeSVN=1,exclude=[]):
	"""Recursively copy a directory tree using copy2."""
	if not isDir(dst): os.mkdir(dst)
	for f in os.listdir(src):
		if f in exclude: continue
		s = path_join(src, f)
		d = path_join(dst, f)
		try:
			if symlinks and os.path.islink(s):
				linkto = os.readlink(s)
				os.symlink(linkto, d)
			elif isDir(s):
				if not (excludeSVN and path_basename(s)=='.svn'): copyTree(s, d, symlinks,excludeSVN)
			else:
				if not (excludeSVN and path_basename(s)[:4]=='.svn'): copy2(s, d)
		except (IOError, os.error) as why:
			print("Can't copy %s to %s: %s" % (repr(s), repr(d), str(why)))
			raise


def safe_umask(mask):
	'''non erroring umask'''
	if mask is None: return None
	try:
		return os.umask(mask)
	except:
		return None

def safe_makedirs(dir,mode=0o777):
	'''non erroring makedirs'''
	try:
		um = safe_umask(0)
		os.makedirs(dir,mode)
	except:
		pass
	safe_umask(um)

def _src2dst(src,dst,excludeSVN=1):
	if isFile(src):
		if _verbose>1: print(' %s --> ' % src, end=' ')
		D = path_dirname(dst)
		if not isDir(D): os.makedirs(D)
		copy2(src,dst)
		if _verbose>1: print(dst)
	elif isDir(src):
		if _verbose>1: print(' %s --> ' % src, end=' ')
		if not isDir(dst): os.makedirs(dst)
		copyTree(src,dst,excludeSVN=excludeSVN)
		if _verbose>1: print(dst)

def copyOver(L,src,dst,xtra=None,excludeSVN=1):
	assert type(L) in (type(()),type([])), 'L should be list or tuple'
	for x in L:
		d = path_join(dst,x)
		_src2dst(path_join(src,x),d,excludeSVN)
		if xtra: _src2dst(path_join(xtra,x),d,excludeSVN)	#overwrite with any specials

_bpath=None
_ppath=None
def getExpandedPath():
	"""Return sys.path as expanded by packages"""
	global _ppath
	if _ppath is None:
		raise NotImplementedError('_ppath = expand(sys.path)')
	return _ppath

def _locate(nm, xtrapath=None, base=None):
	"""Find a file / directory named NM in likely places.
	
	   XTRAPATH is a list of paths to prepend to BASE.
	   If BASE is None, sys.path (as extended by packages) is used."""
	ppath = base
	if base is None:
		ppath = getExpandedPath()
	if xtrapath:
		ppath = xtrapath + ppath
	for pth in ppath:
		fullnm = path_join(pth, nm)
		#print " _locate trying", fullnm
		if os.path.exists(fullnm):
			break
	else:
		return ''
	return fullnm

def getWindowsPath():
	"""Return the path that Windows will search for dlls."""
	global _bpath
	if _bpath is None:
		try:
			import win32api
		except ImportError:
			print("W: Cannot determine your Windows or System directories")
			print("W: Please add them to your PATH if .dlls are not found")
			_bpath = []
		else:
			sysdir = win32api.GetSystemDirectory()
			sysdir2 = path_join(sysdir, '../SYSTEM')
			windir = win32api.GetWindowsDirectory()
			_bpath = [sysdir, sysdir2, windir]
		_bpath.extend(string.split(os.environ.get('PATH', ''), ';'))
	return _bpath

class SpecialDistros:
	def pythonDistro(self,full=0,postcludes=[]):
		from rlextra.utils.superglob import FileSet
		lib = _locatePythonLib()
		fs = FileSet(lib)
		fs.include('./**/*')
		fs.exclude('./site-packages/**/*')
		fs.exclude('./**/*.pyc')
		fs.exclude('./**/*.pyo')
		if not full:
			fs.exclude('./test/**/*')
			fs.exclude('./email/test/**/*')
			fs.exclude('./idlelib/**/*')
			fs.exclude('./distutils/**/*')
			fs.exclude('./lib-old/**/*')
			fs.exclude('./lib-tk/**/*')
		for d in postcludes: getattr(fs,d[0])(d[1])
		return fs

	def pilDistro(self,full=1,postcludes=[],dlls=0):
		from rlextra.utils.superglob import FileSet
		lib = _locatePythonLib()
		fs = FileSet(path_join(lib,'site-packages','PIL'))
		if not dlls:
			fs.include('./**/*.py')
		else:
			if sys.platform=='win32':
				ext = '.pyd'
			else:
				ext = '.so'
			fs.include('./**/*'+ext)
		for d in postcludes: getattr(fs,d[0])(d[1])
		return fs

	def pythonDLLs(self,postcludes=[]):
		from rlextra.utils.superglob import FileSet, SuperFileSet
		fs = FileSet(path_join(sys.exec_prefix,'DLLs'))
		fs.include('./*.pyd')
		#fs.include('./*.dll')
		F = [fs]
		for fn in (_locateVerDLL('Python'), _locateVerDLL('PyWinTypes')):
			fs = FileSet(path_dirname(fn))
			fs.include('./'+path_basename(fn))
			F.append(fs)
		sfs = SuperFileSet(F)
		for d in postcludes: getattr(sfs,d[0])(d[1])
		return sfs

	def reportlabDLLs(self,postcludes=[]):
		from rlextra.utils.superglob import FileSet, SuperFileSet
		F = []
		for modname in '''_renderPM _rl_accel sgmlop pyRXPU pyRXP pyHnj'''.split():
			NS = {}
			rl_exec("import %s as mod" % modname,NS)
			mod = NS['mod']
			del NS
			fn = mod.__file__
			fs = FileSet(path_dirname(fn))
			fs.include('./'+path_basename(fn))
			F.append(fs)
		sfs = SuperFileSet(F)
		for d in postcludes: getattr(sfs,d[0])(d[1])
		return sfs

def _locatePythonLib():
	if sys.platform=='win32':
		return path_join(sys.exec_prefix,'Lib')
	else:
		return path_join(sys.prefix,'lib','python'+sys.version[:3])

def _locateVerDLL(name):
	return _locate('%s%2d.dll'%(name,_pyvers),[],getWindowsPath())

def chdir(dir):
	'''chdir to dir and return old cwd'''
	cwd = os.path.abspath(os.getcwd())
	os.chdir(dir)
	return cwd

class PythonCopier:
	sources = ['py.ico','pyc.ico','pycon.ico','w9xpopen.exe', 'Lib', 'DLLs']
	nocopy = [	'Lib/lib-tk', 'Lib/test', 'Lib/imputil.py', 'Libs',
				'Lib/lib-old', 'Lib/site-packages', 'Lib/email/test',
				'DLLs/tcl83.dll', 'DLLs/tk83.dll',
				'DLLs/cCopy.pyd', 'Dlls/calldll.pyd', 'DLLs/npstruct.pyd',
				'DLLs/_functional.pyd','DLLs/_pyfribidi.pyd','DLLs/fribidi.dll', 'DLLs/libeay32.dll',
				'DLLs/_tkinter.pyd', 'DLLs/gaxtra.pyd','DLLs/old','Dlls/_grabscreen.pyd',
				'DLLs/m2crypto.dll', 'DLLs/_imagingtk.pyd', 'Doc/XTRA','Doc/Grimoire','Doc/Zope',
				]
	
	_pythonDir = path_dirname(sys.executable)

	def doCopy(self,where, srcDir, pythonDir=None):
		'''make a reduced copy of python'''
		if _verbose: print('Copying python from %s & %s\n  --> %s' % (pythonDir,srcDir,where))
		cwd = chdir(where)
		copyOver(self.sources,pythonDir or self._pythonDir,where,srcDir)

		#clean up unwanted things
		for x in self.nocopy:
			p = path_join(where,x)
			kill(p)
			if _verbose>1: print('	   kill(%s)' % p)
		if not isDir('Doc'): os.mkdir('Doc')
		p = _locateVerDLL('Python')
		copy2(p,'DLLs')
		if _verbose>1: print('	%s --> DLLs' % p)
		chdir(cwd)

def copyPIL(where, tk=0):
	import _imaging, PIL
	src = path_dirname(_imaging.__file__)
	for F in ('_imaging.pyd','libjpeg.dll','libz.dll') + (tk and ('_imagingtk.pyd',) or ()):
		condCopyF(F,src,path_join(where,'Dlls'))
	src = path_join(path_dirname(PIL.__file__),'..')
	copyOver(('PIL',),src,path_join(where,'Lib','site-packages'))

def copy_rl_remove(where):
	from rlextra.utils import _rl_remove
	src = path_dirname(_rl_remove.__file__)
	copyOver(('_rl_remove.py',),src,path_join(where,'Lib'))

def _svnUpdate(svn, url, opts='',target='', rev='',report=None):
	url = string.replace(url,'\\','/')
	if url.endswith('/'): url = url[:-1]
	if target:
		module = target
	else:
		module = url.split('/')[-1]
	if os.path.exists(module):
		act = 'up'
		url = module
	else:
		act = 'co'
	if rev: act += rev
	if opts: act = '%s %s' % (act,opts)
	act = '%s %s %s' % (svn, act, url)
	if target: act = '%s %s' % (act,target)
	do_exec(act,report=report)

def _svnRevSplit(x,pfx='@'):
	x = x or ''
	if '@' in x:
		x, r = x.rsplit('@',1)
		r = pfx+r
	else:
		r = ''
	return x, r

def svnUpdate(svn, url, L, opts='',target=''):
	url, rev = _svnRevSplit(url,' -r ')
	if not L:
		_svnUpdate(svn, url, opts=opts,target=target,rev=rev)
	else:
		for x in L:
			_svnUpdate(svn, '%s/%s' % (url,x), opts=opts, target=target,rev=rev)

def svn_update(workDir, url=None, L=None,opts='',target=''):
	svn = find_exe('svn')
	try:
		os.makedirs(workDir)
	except:
		if not isDir(workDir): raise
	cwd = chdir(workDir)
	try:
		svnUpdate(svn, url, L, opts=opts,target=target)
	finally:
		chdir(cwd)

class SVN:
	exeName = 'svn'
	exe = None
	excludePats=('/**/*.pyc','/**/*.pyo','/**/.svn/**/*')
	def __init__(self, url, target=None, distro=None, copySrc=None, copyTarget=None, fetchOpts='',
						revision=None,excludePats=(),includePats=(),report=None, verbose=False,makePkg=False):
		'''
		url is the repository source URL
		target is an optional staging area subdirectorty to check out in, defaults to last URL component
		distro is an option FileSet filter for the copying, paths should be relative to the copy position'
		copySrc a path to add to target to start the copy from
		copyTarget where in the destination to copy our tree to.
		fetchOpts	additional options for the fetch from repository operation
		revision	what SVN revsion to checkout
		'''

		self.url = url
		self.target = target
		self.distro = distro
		self.copySrc = copySrc
		self.copyTarget = copyTarget
		self.fetchOpts = fetchOpts
		self.revision = revision
		self.excludePats = tuple(set(tuple(excludePats)+self.excludePats))
		self.includePats = tuple(set(tuple(includePats)))
		self.report = report
		self.verbose = verbose
		self.makePkg = makePkg
		if not self.exe:
			self.__class__.exe = find_exe(self.exeName)

	def fetch(self,stagingDir=None):
		'''fetch or update self into dir dst'''
		try:
			os.makedirs(stagingDir)
		except:
			if not isDir(stagingDir): raise
		cwd = chdir(stagingDir)
		try:
			self.update()
		finally:
			chdir(cwd)

	def update(self):
		_svnUpdate(self.exe, self.url, opts=self.fetchOpts, target=self.target, rev=self.revision, report=self.report)

	def copy(self,stagingDir,dstDir,pfb=False):
		FS = self.distro
		report = self.report
		if not os.path.isabs(stagingDir):
			stagingDir = os.path.abspath(stagingDir)
		if not os.path.isabs(dstDir):
			dstDir = os.path.abspath(dstDir)
		target = self.target or self.url.split('/')[-1]
		copySrc = self.copySrc
		if copySrc:
			target = '/'.join((target,copySrc))
			stagingDir = '/'.join((stagingDir,'/'.join(target.split('/')[:-1])))
			stagingDir = stagingDir.replace('/',os.sep)
			target = copySrc.split('/')[-1]
		if not FS or FS=='[skiptop]':
			from rlextra.utils.superglob import FileSet
			fs = FileSet(stagingDir)
			if FS=='[skiptop]':
				fs = FileSet('/'.join((stagingDir,target)))
				target = '.'
			fs.include(target+'/**/*')
			for x in self.excludePats:
				fs.exclude(target+x)
			for x in self.includePats:
				fs.include(target+x)
		else:
			fs = FS(stagingDir)

		if self.copyTarget:
			dstDir = os.path.join(dstDir,self.copyTarget)
		try:
			os.makedirs(dstDir)
		except:
			if not isDir(dstDir): raise
		if self.verbose>2 and report:
			report('####### copying: %s(%r)' % (fs.__class__.__name__,fs.baseDir))
			report('        filenames = %s' % '\n'.join(fs.getFileNames()))
		fs.copyFiles(dstDir)
		if pfb:
			if report: report('##### fetchPFB(%r)'% dstDir)
			fetchPFB(dstDir,report=report)
		makePkg = getattr(self,'makePkg',None)
		if makePkg:
			if not isinstance(makePkg,(tuple,list)):
				makePkg = (makePkg,)
			for pkg in makePkg:
				if not pkg: continue
				if isinstance(pkg,str):
					pkgFn = os.path.join(dstDir,pkg,'__init__.py')
				else:
					pkgFn = os.path.join(dstDir,target.split('/')[-1],'__init__.py')
				if self.verbose>2 and report:
					report('##### make package file %r' % pkgFn)
				if not os.path.isfile(pkgFn):
					open(pkgFn,'w').close()

class HG(SVN):
	exe = None
	exeName = 'hg'
	excludePats = ('/**/*.pyc','/**/*.pyo','/**/.htags','/**/.hgignore','/**/.hg/**/*')
	def __init__(self, url, target=None, distro=None, copySrc=None, copyTarget=None,
					fetchOpts='', revision=None, branch=None,excludePats=(),
					includePats=(),report=None,verbose=False,makePkg=False):
		SVN.__init__(self, url, target=target, distro=distro,
						copySrc=copySrc, copyTarget=copyTarget,
						fetchOpts=fetchOpts, revision=revision,excludePats=excludePats,
						includePats=includePats,report=report,verbose=verbose,makePkg=makePkg)
		self.branch = branch

	def update(self):
		target = self.target
		rev = self.revision
		branch = self.branch
		opts = self.fetchOpts
		url = self.url.replace('\\','/')
		if url.endswith('/'): url = url[:-1]
		if target:
			module = target
		else:
			module = url.split('/')[-1]
		C = [self.exe]
		aC = C.append
		if os.path.exists(module):
			aC('pull -q')
			cmd = ' '.join(C)
			cwd = chdir(module)
			try:
				r = do_exec(cmd,report=self.report)
			finally:
				chdir(cwd)
		else:
			aC('clone')
			aC(url)
			if target: aC(target)
			cmd = ' '.join(C)
			r =  do_exec(cmd,report=self.report)
		if r: return r
		if not branch: branch ='default'
		C = [self.exe,'up',branch]
		aC = C.append
		if rev: aC('-r '+rev)
		if opts: aC(opts)
		cmd = ' '.join(C)
		cwd = chdir(module)
		try:
			return do_exec(cmd,report=self.report)
		finally:
			chdir(cwd)

def svn_info(what,withVersion=True):
	'''return the svn info output for a working file/folder as a dictionary'''
	cwd = os.getcwd()
	if not what: what = cwd
	if isDir(what):
		wd = what
		obj = ''
	elif isFile(what):
		wd = path_dirname(what)
		obj = '"%s"' % path_basename(what)
	else:
		raise ValueError('Not file or folder: "%s"' % what)
	from io import StringIO
	out = StringIO()
	if withVersion: out1 = StringIO()
	try:
		chdir(wd)
		do_exec('%s info %s' % (find_exe('svn'), obj), out)
		if withVersion:
			do_exec('%s %s' % (find_exe('svnversion'), obj or '.'), out1)
	finally:
		chdir(cwd)
	D = {}
	out = out.getvalue().split('\n')
	for o in out:
		o = o.split(':')
		D[o[0].strip()] = ':'.join(o[1:]).strip()
	if withVersion: D['svnversion'] = out1.getvalue().strip() or '?????'
	return D

def _findSVNURL(W):
	'''return the URL corresponding to working folder W'''
	try:
		D = svn_info(W,withVersion=False)
		return D['URL']
	except:
		raise ValueError('Can\'t find SVN URL for working dir '+W)

def _locate_trunk(url, starts=('/branches/','/tags/')):
	from subprocess import Popen, PIPE
	svn = find_exe_nq('svn')
	for s in starts:
		i = url.find(s)
		if i<0: continue
		pfx = url[:i]
		if pfx.endswith('/'): pfx = pfx[:-1]
		SFX = url[i+len(s):].split('/')[1:]
		while SFX:
			u = '/'.join([pfx,'trunk']+SFX)
			p = Popen((svn,'ls',u),stdout=PIPE,stderr=PIPE)
			i = p.wait()
			if not i: return u
			del SFX[0]
	raise ValueError('Cannot locate trunk version of\n\t'+url)

def findSVNURL(W, branch=None):
	url = _findSVNURL(W)
	branch, rev = _svnRevSplit(branch)
	s = '/trunk/'
	i = -1
	if branch:
		if branch.startswith('/'): branch = branch[1:]
		if branch and branch!='trunk':
			if not (branch.startswith('branches/') or branch.startswith('tags/')):
				raise ValueError('branch should start with "branches/" or "tags/" not "%s"' % branch)
			if branch.endswith('/'): branch = branch[:-1]
			i=url.find(branch)
	if i>=0:
		i -= 1
		url = url[:i]+s+url[i+len(branch)+2:]
	else:
		i = url.find(s)
		if i<0:
			url = _locate_trunk(url,('branches','tags'))
			i = url.find(s)
	if branch=='trunk': branch = ''
	if branch:
		url = '%s/%s/%s' % (url[:i],branch,url[i+len(s):])
	if rev: url += rev

	return url

def import_free_call(func,*args,**kw):
	'''eliminate unwanted import side effects and return func()'''
	try:
		OLD = {}
		for x in 'path','modules','meta_path','path_hooks','path_importer_cache':
			try:
				_ = getattr(sys,x)
				if hasattr(_,'copy'): _ = _.copy()
				else: _ = _[:]
				OLD[x] = _
			except:
				pass
		return func(*args,**kw)
	finally:
		for x,v in list(OLD.items()):
			_ = getattr(sys,x)
			if hasattr(_,'copy'):
				_.clear()
				_.update(v)
			else:
				_[:] = v

def inferSVNURL(URL,modulename):
	'''try to infer the SVN URL from a module import location'''
	def func(URL,modulename):
		try:
			NS = {}
			rl_exec('import %s as mod' % modulename,NS)
			mod = NS['mod']
			del NS
			from urllib.parse import urlparse, urlunparse
			host = urlparse(findSVNURL(path_dirname(mod.__file__)),allow_fragments=0)
			url = urlparse(URL)
			return urlunparse((url[0],host[1])+url[2:])
		except:
			return URL
	return import_free_call(func,URL,modulename)

def _fetchRLPrivate(srcDir,branchName,desiredBN=None,what='rlextra',report=None):
		if not desiredBN: desiredBN = branchName
		else:
			if desiredBN.startswith('/'): desiredBN = desiredBN[1:]
			if not (desiredBN=='trunk' or desiredBN.startswith('branches/') or desiredBN.startswith('tags/')):
				raise ValueError('desiredBN should start with "branches/" or "tags/" not "%s"' % desiredBN)
		desiredBN, rev = _svnRevSplit(desiredBN)
		url = inferSVNURL('https://svn.reportlab.com/svn/private/%s/%s' % (desiredBN,what),'rlextra')+rev
		if report: report('Fetching %s from %s'%(what,url))
		svn_update(srcDir,url=url,L=None)
		if report: report('%s fetched' % what)

def fetchPFB(dstDir,report=None):
	#fetch the standard pfb files into ./fonts
	from reportlab.pdfbase._fontdata import _font2fnrMapWin32, findT1File
	N = []
	for fontName in list(_font2fnrMapWin32.keys()):
		try:
			fn = findT1File(fontName)
			if fn is None: raise ValueError
		except:
			N.append(fontName)
			continue
		if sys.platform=='win32':
			fn = path_join(path_dirname(fn),path_basename(fn).lower())
		dd = path_join(dstDir,'reportlab','fonts')
		_src2dst(fn,dd)
		os.chmod(path_join(dd,path_basename(fn)),0o666)
	if N: raise ValueError('Can\'t copy pfb fonts '+ ' '.join(N)) 
	if report: report('pfb font files copied to fonts')

def fetchRL(srcDir,rl=1,rlx=1,rla=None,report=None,pfb=None, branchName=None, branchNameX=None,
				rli=0, branchNameI=None):
	'''convenience routine assumes our reportlab & rlextra (& rlinfra) are SVN controlled'''
	if not branchName: branchName = 'trunk'
	else:
		if branchName.startswith('/'): branchName = branchName[1:]
		if not (branchName=='trunk' or branchName.startswith('branches/') or branchName.startswith('tags/')):
			raise ValueError('branchName should start with "branches/" or "tags/" not "%s"' % branchName)
	if rl or rla:
		branchName, rev = _svnRevSplit(branchName)
		if ('/nomtrail' in branchName or '/isa2009' in branchName or '/isa2008' in branchName
				or '/cmaimp' in branchName or '/isa2010' in branchName or '/nov2010' in branchName
				or '/kiid' in branchName or '/rdr' in branchName or '/cstan' in branchName 
				or '/mstar2012' in branchName):
			url = ('https://svn.reportlab.com/svn/public/reportlab/%s/reportlab' % branchName)+rev
		else:
			url = ('https://svn.reportlab.com/svn/public/reportlab/%s/src/reportlab' % branchName)+rev
		if rl:
			if report: report('Fetching reportlab from '+url)
			svn_update(srcDir,url=url,L=None)
			if report: report('reportlab fetched')
			if pfb:
				fetchPFB(srcDir,report=report)
		if rla:
			if report: report('Fetching rl_addons from '+url)
			url = 'https://svn.reportlab.com/svn/public/reportlab/%s/src/rl_addons' % branchName+rev
			svn_update(srcDir,url=url,L=None)
			if report: report('rl_addons fetched')
	if rlx:
		_fetchRLPrivate(srcDir,branchName,desiredBN=branchNameX,what='rlextra',report=report)
	if rli:
		_fetchRLPrivate(srcDir,branchName,desiredBN=branchNameI,what='rlinfra',report=report)

def stagingArea(suffix=''):
	from reportlab.lib.utils import get_rl_tempdir
	return get_rl_tempdir('SA_'+suffix)

def copyRL(where,srcDir,rl=1,rlx=1,noFetch=0):
	'''copy reportlab or rlextra from the staging area to the result area'''
	if not noFetch: fetchRL(srcDir,rl=rl,rlx=rlx)	#get export to srcDir
	cwd = chdir(where)
	if _verbose: print('Copying RL from %s\n  --> %s' % (srcDir,where))
	copyOver((rl and ('reportlab',) or ())+(rlx and ('rlextra',) or ()), srcDir, where,None)
	chdir(cwd)

def make_stub(stubname,fn,unix=0):
	stubs= {'rml2pdf':'''import sys
from rlextra.rml2pdf import rml2pdf
from reportlab import rl_config
fn=sys.argv[1:]
x = filter(lambda x:x[:9]=='--outdir=',fn)
outDir=None
if x:
	outDir=x[-1][9:]
	map(fn.remove,x)
rml2pdf.main(quiet=rl_config.verbose==0,outDir=outDir,exe=1,fn=fn)
''',
	'pagecatcher': 'from rlextra.pageCatcher.pageCatcher import scriptInterp\nscriptInterp()\n',
	'pythonpoint': 'from reportlab.tools.pythonpoint.pythonpoint import main\nmain()\n',
	}
	open(fn,'w').write((unix and '#!/usr/bin/env python\n' or '') + stubs[stubname])

def postCopyFixupRL(where):
	cwd = chdir(where)
	if sys.hexversion>=0x02020000:
		src = path_join(PythonCopier._pythonDir,'Lib','site-packages')
		for F in ('_renderPM.pyd','_rl_accel.pyd','pyRXP.pyd','sgmlop.pyd','pyHnj.pyd'):
			condCopyF(F,src,'Dlls')
	sys.path.insert(0,where)
	import reportlab.rl_config
	sys.path.remove(where)
	L = []
	for d in dir(reportlab.rl_config):
		if d in ('__builtins__','sys','os','string'): continue
		L.append(d)
	src = path_join(where,'reportlab','rl_config.py')
	dst = path_join(where,'_rl_config.py')
	rename(src,dst)
	open(src,'w').write('from _rl_config import %s\n' % ', '.join(L))
	make_stub('rml2pdf',path_join(where,'rlextra','rml2pdf','exe_stub_rml2pdf_distro.py'))
	make_stub('pagecatcher', path_join(where,'rlextra','pageCatcher','exe_stub_pageCatcher_distro.py'))
	make_stub('pythonpoint',path_join(where,'reportlab','tools','pythonpoint', 'exe_stub_pythonpoint_distro.py'))
	chdir(cwd)

def _compileApp(project,app,zip):
	from rlextra.utils.appmonitor import AppMonitor
	from rlextra.utils.superglob import FileSet
	FS = FileSet(app)
	FS.include('**/*')
	m = AppMonitor(dirname=app,id=project,fileList=FS.getFileNames())
	m._force_ssmName = 0
	m.compileApp()
	m.writeSignedTargetManifest()

	#assembly should now be complete we build everything into an installer
	print('Creating application archive',zip)
	m.makeTargetArchive(zip)

def _compileAppX(ifn,project,app,zip):
	'''special purpose function designed to be run externally'''
	from io import StringIO
	sys.stdout = StringIO()
	sys.stderr = StringIO()
	try:
		_compileApp(project,app,zip)
	except:
		traceback.print_exc()
	from marshal import dump
	f = open(ifn,'wb')
	dump((sys.stdout.getvalue(),sys.stderr.getvalue()),f)
	f.close()

def _externalRun(ifn, cmd, PPATH, verbose=1, errMsg=None):
	if PPATH: os.environ['PYTHONPATH'] = PPATH
	try:
		f = os.popen(cmd,'w')
		#status= \
		f.close()
	finally:
		if PPATH: del os.environ['PYTHONPATH']
	f = open(ifn,'rb')
	from marshal import load
	out,err = load(f)
	f.close()
	if verbose:
		print(out)
		print(err)
	if err and errMsg:
		raise ValueError(errMsg+('\n%s'%cmd))
	return out,err

def makePat(P):
	'''
	P is a list of	glob style patterns
	return the corresponding compiled re
	'''
	import re, fnmatch
	L=[]
	for p in P:
		L.append(fnmatch.translate(p))
	return re.compile('^(?:%s)$'%string.join(L,'|'))

def makeRLDocs(where):
	cwd = chdir(path_join(where,'reportlab','docs'))
	opp = os.environ.get('PYTHONPATH',None)
	pp = where
	if opp: pp += ';'+opp
	os.environ['PYTHONPATH'] = pp
	do_exec(sys.executable + ' genAll.py')
	PDF = glob.glob('*.pdf')
	if _verbose>2: print('pdf=',PDF)
	if opp: os.environ['PYTHONPATH'] = opp
	else: del os.environ['PYTHONPATH']
	chdir(cwd)
	chdir(path_join(where,'rlextra','graphics','doc'))
	do_exec('%s %s diagradoc.rml' % (sys.executable, path_join(where,'rlextra','rml2pdf','rml2pdf.py')))
	chdir(cwd)
	return PDF

_binexts = ('dll', 'pyc', 'pyo', 'pyz', 'exe')
def _resource_fixcase(name, path):
	parts = string.split(name, '.')
	name = parts[-1]
	if name in _binexts:
		name = parts[-2]
	d, bnm = os.path.split(path)
	nm, ext = os.path.splitext(bnm)
	if string.lower(name) == string.lower(nm):
		return path_join(d, name + ext)
	return path

def GetCompiled(seq, lvl='c'):
	"""SEQ is a list of .py files, or a logical TOC.
	 Return as .pyc or .pyo files (LVL) after ensuring their existence"""
	if len(seq) == 0: return seq
	rslt = []
	isTOC = type(seq[0])==type(())
	for py in seq:
		if isTOC:
			(nm, fnm), rest = py[:2], py[2:]
		else:
			fnm = py
			nm = os.path.splitext(fnm)[0]
		fnm = os.path.splitext(fnm)[0] + '.py'
		cmpl = 1
		pyc = fnm + lvl
		if os.path.exists(pyc):
			pytm = int(os.stat(fnm)[8])
			ctm = int(os.stat(pyc)[8])
			if pytm < ctm: cmpl = 0
		if cmpl:
			fnm = _resource_fixcase(nm, fnm)
			import py_compile
			py_compile.compile(fnm, pyc)
		if isTOC:
			rslt.append((nm, pyc)+rest)
		else:
			rslt.append(pyc)
	return rslt

def assembleArchive(pkg,toc,fullName=0):
	'''
	pkg is the name of the archive file
	toc is the list of contents path, type
	'''
	from rlextra.utils.installer import CArchive
	A = CArchive()
	L = []
	for p, t in toc:
		n = os.path.splitext(path_basename(p))[0]
		c = {'s':2,'m':0,'b':1,'x':1,'a':0,'z':0}[t]
		if t=='b' or (fullName and t in 'ms'): n = n + os.path.splitext(p)[1]
		if t=='m': L += GetCompiled([(n, p, c, t)])
		else: L.append((n, p, c, t))
	A.build(pkg,L)
	return A

def copyFiles(src,dst,mode='wb'):
	w = open(dst,mode)
	for r in src:
		w.write(open(r,'rb').read())

_MAGIC = {'RLP':"RLP\02\04\03\014\015", 'RLW':"RLW\01\02\03\017\016", 'RLE':"RLE\07\04\01\013\012"}
def _wrapEXE(src,dst,magic,project,script=None,version=None,icon=None):
	v = sys.version
	v = int(v[0])*10+int(v[2])
	if _verbose: print('making %s(%d) from %s icon=%s version=%s' % (dst,v,src,icon,version))
	d = open(dst,'wb')
	d.write(open(src,'rb').read())
	if script:
		d.write(script)
		s = struct.pack('<ihh',len(script),len(project),v)
	else:
		s = struct.pack('<hh',len(project),v)
	d.write(project)
	d.write(s)
	d.write(magic)
	d.close()
	if icon:
		odst = dst+'.tmp'
		os.rename(dst,odst)
		import pywintypes
		try:
			from rlextra.utils.installer.icon import CopyIcons
			CopyIcons(dst, icon)
		except ImportError:
			raise ValueError("win32api & NT/W2K are required for updating icons.")
		except pywintypes.error:
			raise ValueError("NT/Win2k required to update icons")
		os.remove(odst)
	if version:
		odst = dst+'.tmp'
		os.rename(dst,odst)
		import pywintypes
		try:
			from rlextra.utils.installer.versionInfo import SetVersion
			SetVersion(dst, version)
		except ImportError:
			raise ValueError("win32api & NT/W2K are required for setting Version resources.")
		except pywintypes.error:
			raise ValueError("NT/Win2k required to update version resource")
		os.remove(odst)

def _makeEXE(where,n,debug,magic,project,script=None,version=None,icon=None,stub=None,ext='exe'):
	supDir = installerDir('support')
	if ext and ext[0]!='.': ext = '.'+ext
	w = (stub or n)+(debug and '_d' or '')+ext
	n = n+ext
	src = path_join(supDir,w)
	dst = path_join(where,n)
	_wrapEXE(src,dst,magic,project,script=script,version=version,icon=icon)

def makeEXES(where,PROJECT,RLP=('python','pythonw',),RLW=(),debug=1):
	if _verbose: print('Making exe files in ',where)
	for n,p,w,v,i in RLW:
		_makeEXE(where,n,debug,
				_MAGIC['RLW'],
				PROJECT,
				script=open(p,'r').read(),
				icon=i,
				version=v,
				stub=w and 'rlwrapw' or 'rlwrap')
	for n in RLP:
		_makeEXE(where,n,debug,_MAGIC['RLP'],PROJECT)

def getHere():
	global _cached_getHere
	if '_cached_getHere' not in list(globals().keys()):
		_cached_getHere = getFlag('--where',1,sys.argv[0])
		if not os.path.isabs(_cached_getHere): _cached_getHere = os.path.abspath(_cached_getHere)
		if not isDir(_cached_getHere): _cached_getHere = path_dirname(_cached_getHere)
	return _cached_getHere

def listAllFiles(dir,rel=1):
	def record(F,dir,names):
		F.extend(list(filter(isFile,list(map(lambda x, dir=dir: path_join(dir,x),names)))))
	F = []
	os.path.walk(dir,record,F)
	if rel:
		n = len(dir)+len(os.sep)
		F = list(map(lambda x,n=n: x[n:],F))
	return F

def listAllDirs(dir,rel=1):
	def record(F,dir,names):
		F.extend(list(filter(isDir,list(map(lambda x, dir=dir: path_join(dir,x),names)))))
	F = []
	os.path.walk(dir,record,F)
	if rel:
		n = len(dir)+len(os.sep)
		F = list(map(lambda x,n=n: x[n:],F))
	return F

def cleanEmpties(dir):
	D = listAllDirs(dir)
	D.reverse()
	cwd = chdir(dir)
	for d in D:
		if not os.listdir(d): os.rmdir(d)
	chdir(cwd)

def _forceDir(d):
	D = path_dirname(d)
	if not isDir(D): os.makedirs(D)

def _copyF(s,d):
	if isFile(d):
		remove(d)
	else:
		_forceDir(d)
	copy2(s,d)

def sitecustomize(where):
	'''for versions < 2.2 put site-packages into the path'''
	if sys.hexversion<0x02020000:
		open(path_join(where,'Lib','sitecustomize.py'),'w').write(
'''import sys, os
from site import addsitedir
addsitedir(path_join(os.path.dirname(__file__),'site-packages'))
'''
		)

def copyF(F,src,dst):
	_copyF(os.path.abspath(path_join(src,F)), os.path.abspath(path_join(dst,F)))

def condCopyF(F,src,dst):
	srcF = os.path.abspath(path_join(src,F))
	if isFile(srcF):
		_copyF(srcF, os.path.abspath(path_join(dst,F)))

class PyComCopier:
	sources=(
		'win32/win32api.pyd', 'win32/win32trace.pyd',
		'win32/lib/commctrl.py', 'win32/lib/win32con.py', 'win32/lib/win32traceutil.py', 'win32/lib/winerror.py',
		'win32com/__init__.py', 'win32com/client/CLSIDToClass.py', 'win32com/client/__init__.py', 'win32com/client/build.py',
		'win32com/client/connect.py', 'win32com/client/dynamic.py', 'win32com/client/gencache.py',
		'win32com/client/genpy.py', 'win32com/client/makepy.py', 'win32com/client/selecttlb.py',
		'win32com/client/util.py', 'win32com/olectl.py', 'win32com/server/__init__.py', 'win32com/server/connect.py',
		'win32com/server/dispatcher.py', 'win32com/server/exception.py', 'win32com/server/factory.py', 'win32com/server/localserver.py',
		'win32com/server/policy.py', 'win32com/server/register.py', 'win32com/server/util.py', 'win32com/storagecon.py',
		'win32com/universal.py', 'win32com/util.py',

		# these are only used by gui type things
		#'Pythonwin/pywin/__init__.py', 'Pythonwin/pywin/dialogs/__init__.py', 'Pythonwin/pywin/dialogs/list.py', 'Pythonwin/pywin/dialogs/status.py',
		#'Pythonwin/pywin/mfc/__init__.py', 'Pythonwin/pywin/mfc/dialog.py', 'Pythonwin/pywin/mfc/object.py', 'Pythonwin/pywin/mfc/window.py',
		#'win32com/client/combrowse.py', 'Pythonwin/win32ui.pyd', 'Pythonwin/win32uiole.pyd', 'win32com/client/tlbrowse.py',
		)

	def doCopy(self,where):
		import win32com
		src = os.path.abspath(path_join(path_dirname(win32com.__file__),'..'))
		sp = os.path.abspath(path_join(where,'Lib','site-packages'))
		d = path_join(sp,'win32com.pth')
		_forceDir(d)
		open(d,'w').write('win32\nwin32\\lib\n')
		list(map(lambda x,dst=sp,src=src: copyF(x,src,dst),self.sources))
		for f in ('PythonCOM', 'PyWinTypes'):
			s = _locateVerDLL(f)
			d = path_join(where,'Dlls',string.lower(path_basename(s)))
			_copyF(s,d)
		sitecustomize(where)

def findModules(d,wlen,ipfx='',excl_re=None,incl_list=None):
	from py_compile import compile
	cwd = chdir(d)
	here = os.getcwd()
	R = []
	for m in glob.glob('*.py'):
		n = ipfx+m
		if incl_list and n not in incl_list: continue
		n = n[:-3]
		c = normPath(path_join(here,m + 'c'))
		co = '_p:'+c[wlen:-1]
		if n[-9:]=='.__init__': n = n[:-9]
		if excl_re and excl_re.match(n): continue
		if _verbose>9: print('Adding %s to pyz' % c[:-1])
		compile(m,c,co)
		R.append((n,c))
	P = list(filter(lambda x, d=d: isDir(x) and isFile(path_join(x,'__init__.py')), os.listdir(here)))
	for p in P:
		R.extend(findModules(p,wlen,ipfx+p+'.',excl_re,incl_list))
	chdir(cwd)
	return R

def rename(src,dst):
	remove(dst)
	try:
		os.rename(src,dst)
	except:
		pass

def move_files(root,files):
	for f, d in list(files.items()):
		rename(path_join(root,f),path_join(root,d,path_basename(f)))

def cleanupBeforePYZ(where,movethese={},copythese={},remove_before_pyz=()):
	if _verbose: print('Moving RL files to', where)
	#move to root dir
	move_files(where,movethese)

	for f, d in list(copythese.items()):
		copy2(path_join(where,f),path_join(where,d))

	if _verbose: print('Removing unwanted files')
	list(map(kill,remove_before_pyz))

def makePYZ(where, pyz_exclude=(), remove_after_pyz=(), pyzName=None, preLoad=1, addLib=1, cleanUp=1, incl_list=None, verbose=None):
	if verbose is None: verbose = _verbose
	if verbose: print('Locating modules for PYZ')
	from rlextra.utils.installer._rl_archive import ZlibArchive
	from py_compile import compile
	instDir = installerDir()
	Z = []
	if preLoad:
		for n in ('_rl_archive','_rl_iu','_rl_boot')[:max(2,preLoad)]:
			f = path_join(instDir,n+'.py')
			c = f+'c'
			compile(f,c,f)
			Z.append((n,c))

	excl_re = makePat(pyz_exclude)
	where = os.path.abspath(where)
	wlen = len(where)+len(os.sep)
	lib = path_join(where,'Lib')
	for D in (where,)+(addLib and (lib,) or ()):
		Z.extend(findModules(D,wlen,excl_re=excl_re,incl_list=incl_list))
	if verbose: print('Building PYZ, number of modules=%d' % len(Z))
	ZlibArchive().build(pyzName or path_join(lib,'reportlab.pyz'),Z)
	if cleanUp:
		for m,p in Z[preLoad and max(preLoad,2) or 0:]: #first two belong to us
			remove(p)		#x.pyc
			remove(p[:-1])	#x.py
		list(map(kill,remove_after_pyz))

def compile_files(F,removePy=0):
	'''compile_files(F)
	python compile files in F'''
	from py_compile import compile
	for fn in F:
		compile(fn)
		if removePy: remove(fn)
	return len(F)

def removePYC(F,removePy=0):
	'''removePYC(F)
	remove pyc files parallel to files in F'''
	for f in F:
		f = f.split('/')
		if sys.platform=='mac': f.insert(0,'')
		remove(os.path.splitext(os.sep.join(f))[0]+'.pyc')

def compile_dir(dir, removePy=0, noCompile=[]):
	cwd = os.getcwd()
	if not os.path.isabs(dir): dir = path_join(cwd,dir)
	chdir(dir)
	from rlextra.utils.superglob import FileSet
	fsPy = FileSet(dir)
	fsPy.include('**/*.py')
	fsPy.scan()
	count = 0
	F = fsPy.getFileNames()
	count = compile_files(list(filter(lambda x,NC=noCompile: x not in NC,F)), removePy=removePy)
	removePYC(noCompile)
	if removePy:
		for f in [x for x in F if x[-4:]=='.pyc']:
			remove(f[:-1])
	chdir(cwd)
	return count

def runInno(fileName,where=None):
	Inno = None
	for c in (	'C:\\Program Files\\Inno Setup 5\\Compil32.exe',
				'C:\\Program Files\\Inno Setup 4\\Compil32.exe',
				'C:\\Program Files\\Inno\\Compil32.exe',
				'C:\\Program Files\\My Inno Setup Extensions\\Compil32.exe',
				'C:\\Inno\\Compil32.exe',
				'C:\\My Inno Setup Extensions\\Compil32.exe'):
		if isFile(c):
			Inno = c
			break
	if Inno:
		cmd = [Inno,'/cc',where and path_join(where,fileName) or fileName]
		from distutils.spawn import spawn
		#rc = \
		spawn(cmd,search_path=0,verbose=_verbose,dry_run=0)
	else:
		print('Cannot find Inno, run manually')

def makeTGZ(tgzName, archDir,AFL=(),tarName=None):
	#AR the tar module I found is Python 2.2 only and chokes
	#when gzipping; had to handle that myself
	AFL = AFL or listAllFiles(archDir,rel=0)
	from rlextra.utils import tarfile
	if not tarName:
		from reportlab.lib.utils import get_rl_tempfile
		tarName = get_rl_tempfile()
	arch = tarfile.TarFileCompat(tarName, 'w', compression=tarfile.TAR_PLAIN)
	for fn in AFL: arch.write(fn)
	arch.close()
	import gzip
	if tgzName[:-4]!='.tgz': tgzName = tgzName + '.tgz'
	remove(tgzName)
	g = gzip.GzipFile(tgzName, 'wb', 9)
	f = open(tarName, 'rb')
	while 1:
		chunk = f.read(1024)
		if not chunk: break
		g.write(chunk)
	g.close()
	f.close()
	remove(tarName)

def expandTGZ(tgzName,tarName=None):
	'''Expands tgz archives
	Warning this only handles regular files'''
	import tarfile, gzip
	if not tarName:
		from reportlab.lib.utils import get_rl_tempfile
		tarName = get_rl_tempfile()
	g = gzip.GzipFile(tgzName)
	t = open(tarName, 'wb')
	while 1:
		data = g.read(1024)
		if not data: break
		t.write(data)
	g.close()
	t.close()
	t = tarfile.TarFile(tarName)
	m = t.getmembers()

	for d in filter(lambda x, t=tarfile.REGTYPE: x.type==t, m):
		n = d.name.split('/')
		if n[0]=='.': del n[0]
		if len(n)>1:
			dn = os.sep.join(n[:-1])
			if not isDir(dn): os.makedirs(dn)
		open(os.sep.join(n),'wb').write(t.readstr(d))

	t.close()
	remove(tarName)

def makeZIP(zipName, archDir, AFL=()):
	AFL = AFL or listAllFiles(archDir,rel=0)
	import zipfile
	if zipName[-4:]!='.zip': zipName = zipName + '.zip'
	remove(zipName)
	arch = zipfile.ZipFile(zipName, 'w', compression=zipfile.ZIP_DEFLATED)
	for fn in AFL: arch.write(fn)
	arch.close()

def makeArchive(name, where, what='.', convertCRLF=sys.platform=='win32',zipmode='tgz'):
	"Archives file/dir in 'what', or current directory if not specified"
	cwd = chdir(where)
	if name[-4:]=='.tgz' or name[-4:]=='.tar': name = name[:-4]
	name = path_join(os.getcwd(),name)
	if zipmode=='tgz':
		remove(name+'.tar')
		remove(name+'.tgz')
		tar = find_exe('tar')
		do_exec(tar + ' cf %s.tar %s' % (name,what))
		gzip = find_exe('gzip')
		do_exec(gzip + ' %s.tar' % name)
		rename(name+'.tar.gz', name+'.tgz')
	elif zipmode=='zip':
		zip = find_exe('zip')
		remove(name+'.zip')
		do_exec(zip+' -ur %s.zip . -i %s' % (name,what))
	else:
		raise ValueError('Illegal zipmode %s' % zipmode)
	chdir(cwd)

def generateProductInfo(where):
	cwd = chdir(where)
	python = sys.executable
	for (cmd,dir) in [
		("%(python)s genuserguide.py --outdir=%(where)s/docs", "%(where)s/reportlab/docs/userguide"),
		("%(python)s gen_rmluserguide.py --outdir=%(where)s/docs", "%(where)s/rlextra/rml2pdf/doc"),
		("%(python)s %(where)s/rlextra/rml2pdf/rml2pdf.py %(where)s/rlextra/pageCatcher/PageCatchIntro.rml", "%(where)s/rlextra/pageCatcher"),
		("%(python)s %(where)s/reportlab/tools/pythonpoint/pythonpoint.py %(where)s/reportlab/tools/pythonpoint/demos/pythonpoint.xml", "%(where)s/reportlab/tools/pythonpoint/demos"),
		("%(python)s %(where)s/rlextra/rml2pdf/rml2pdf.py diagradoc.rml", "%(where)s/rlextra/graphics/doc"),
		]:
		cmd = cmd.replace('/',os_sep)
		dir = dir.replace('/',os_sep)
		dir = dir % locals()
		if not isDir(dir): continue
		chdir(dir)
		cmd = cmd % locals()
		if _verbose>5: print('################ %s: start %s' % (time.asctime(time.gmtime()), cmd))
		i, o = os.popen4(cmd,'t')
		t = o.read()
		if _verbose>1 and t: print(t)
		if _verbose>5: print('################ %s: finished' % time.asctime(time.gmtime()))
	chdir(cwd)

_re_exts2del=re.compile(r'.*\.(?:bat|c|cc|cpp|h|py|pyc|pyo|prep)$',re.I)
def cleanProductInfo(dir1, dir2, keep):
	'''
	removes code like files eg, .py, .pyc, .c, .h, etc from underneath dir1
	removes corresponding survivors from under dir2
	'''
	dir1 = os.path.abspath(dir1)
	dir2 = os.path.abspath(dir2)


	K = listAllFiles(dir1)
	D = list(filter(_re_exts2del.match,K))
	for f in D:
		if f in keep:
			D.remove(f)
		else:
			K.remove(f)
	if _verbose>9:
		import pprint
		print('dir1=',dir1, '\nK=')
		pprint.pprint(K)
		print('dir2=',dir2, '\nD=')
		pprint.pprint(D)
	cwd = chdir(dir1)
	list(map(kill,D))
	chdir(dir2)
	list(map(kill,K))
	chdir(cwd)

def getFileActionList(dir,patterns={},L=None,fal=None):
	cwd = chdir(dir)
	if L is None: L = []
	A = [x[1] for x in L]
	for k,p in list(patterns.items()):
		F = list(filter(lambda x,A=A: x not in A,filesMatch(p)))
		A.extend(F)
		for f in F:
			L.append((k,f))
	F = listAllFiles(dir)
	F.sort()
	for f in F:
		fs = f.replace('\\','/')
		if fs in A: continue
		d = path_dirname(f)
		fn, ext = os.path.splitext(f)
		bn = path_basename(fn)
		ext = ext.lower()
		if ext == '.pyc': continue
		if ext=='.py':
			if isFile(path_join(dir,d,'__init__.py')):
				k = 'z'
			else:
				k = 'k' #keep
		elif ext in ('.bat','.exe'):
			k = 'd'
		elif ext=='.pdf':
			if d!='docs':
				k = 'm', path_join(dir,'docs')
			else:
				k = 'k'
		elif bn.lower() in ('readme', 'changes', '00readme'):
			k = 'k'
		elif ext in ('.txt','.rml'):
			k = 'k'
		else:
			k = 'k'
		L.append(type(k) is type('') and (k,fs) or (k[0],fs,k[1].replace('\\','/')))
	L.sort()
	chdir(cwd)
	return L

def writeFileActionList(dir,patterns={},filename='new_fileactions.txt',L=None):
	fa = open(filename,'w')
	for x in getFileActionList(dir,patterns=patterns,L=L):
		print(repr(x)[1:-1], file=fa)

def readFileActionList(filename='fileactions.txt'):
	return list(map(eval,open(filename,'r').readlines()))
