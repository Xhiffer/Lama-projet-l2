#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
'''release helper utility'''

import sys, os, time
from .buildutils import	do_exec, find_exe, getFlag, kill
from reportlab.lib.utils import getStringIO
from reportlab import rl_config

def _getArgs(f,args=None):
	m = f in args
	if m: args.remove(f)
	return m

def getNow():
	return time.strftime('%Y%m%d%H%M%S',time.gmtime(time.time()))

def _makeTag(tag,s,major,minor,st):
	return tag + s + s.join(map(str,[major,minor])) + (not st and s + getNow() or '')

class Releaser:
	tagfn= 'PROJECT_CVS_TAG', 'version.txt'
	def __init__(self,d,verbose=rl_config.verbose):
		assert os.path.isdir(d), 'Argument d="%s" isn\'t a directory!' % d
		self.cwd = os.getcwd()
		try:
			os.chdir(d)
			self.workingDir = os.getcwd()
		finally:
			os.chdir(self.cwd)
		self.verbose = verbose

	def goWorkingDir(self):
		os.chdir(self.workingDir)

	def resetDir(self):
		os.chdir(self.cwd)

	def _readtag(self,fn):
		try:
			return open(fn,'r').read().strip().split()[0]
		except:
			return None

	def __getattr__(self,name):
		if name=='tag':
			try:
				self.goWorkingDir()
				for fn in self.tagfn:
					tag = self._readtag(fn)
					if tag:
						self.tag = tag
						return tag
				raise ValueError('Can\'t locate tagfile in %s' % repr(self.tagfn))
			finally:
				self.resetDir()
		else:
			raise AttributeError("'%s' instance has no attribute '%s'" % (self.__class__.__name__, name))

	def _svn(self,args,fail=1):
		''' do a svn command and return the results '''
		svn = find_exe('svn')
		if type(args) is type([]): args = ' '.join(args)
		self.goWorkingDir()
		fout=getStringIO()
		do_exec(svn + ' ' + args,fout=fout,sys_exit=0,verbose=self.verbose>1,fail=fail)
		self.resetDir()
		T = fout.getvalue()
		T.replace('\r\n','\n')
		T.replace('\r','\n')
		return '\n'.join([x for x in T.split('\n') if not x or x[0]!='?'])

	def major_minor(self,t,s=None):
		if not s: s = t[len(self.tag)]
		x = t.split(s)[1:]
		if len(x[-1])>4: del x[-1]
		n = len(x)
		return list(map(int,(n>=1 and x[0] or 0, n>=2 and x[1] or 0)))

	def _tagFromArg(self,a):
		T = self._listTags(asList=1)
		if a is None:
			return T[-1]
		elif len(a)>len(self.tag):
			if a in T: return a
		else:
			# assume we have 0.0 or whatever
			for s in ('_','-','.'):
				if s in a:
					t = a.split(s)
					major_minor = int(t[0]), int(t[1])
					for t in T:
						if tuple(self.major_minor(t))==major_minor: return t
					break
		raise ValueError('%s is not a valid tag' % a)

	def _splitTag(self,a):
		for s in ('.','_','-'):
			if s in a:
				a = a.split(s)
				return '%s-%s-%s-%s' % (self.tag, a[0], a[1], getNow())
		return None

	def release(self,*args):
		'''
		find tag
		SVN update
		appmonitor.py dir writeSignedSourceManifest
		appmonitor.py dir verifySignedSourceManifest
		SVN tag
		appmonitor.py dir makeSourceArchive fullname
		'''
		args = list(args)
		nosvn = _getArgs('-nosvn',args)
		nvd = _getArgs('-n',args)
		zip = _getArgs('-zip',args)
		tgz = _getArgs('-tgz',args)
		tar = _getArgs('-tar',args)
		dt = _getArgs('-dt',args)
		n = len(args)
		if n==1:
			tag = self._splitTag(args[0])
		else:
			raise ValueError('release takes flags -n -nosvn -zip -tgz -tar tag')
		sTag = dt and tag or self.tag+'-%s-%s' % tuple(self.major_minor(tag))
		if self.verbose: print('Creating release files for '+sTag)
		if not nosvn:
			self._svn('up')
			if self.verbose: print('directory "%s" svn updated' % self.workingDir)
		from .appmonitor import AppMonitor
		a = AppMonitor(self.workingDir,verbose=self.verbose)
		a.writeSignedSourceManifest()
		if not a.verifySignedSourceManifest(): raise ValueError("Can't verify source_manifest")
		if nvd: copyDir = None
		else: copyDir = tag
		for go, kind in ((zip,'zip'),(tar,'tar'),(tgz,'tgz')):
			if go: a.makeSourceArchive('%s.%s' % (sTag,kind),kind=kind,copyDir=copyDir)

	def _getProject(self):
		try:
			self.goWorkingDir()
			root = open('CVS/Root','r').read().strip()
			repos = open('CVS/Repository','r').read().strip()
			if repos[0]=='/': repos = repos[len(root[root.find('/'):])+1:]
			return repos
		finally:
			self.resetDir()

	def getArchive(self,*args):
		args = list(args)
		fs = _getArgs('-fs',args)
		zip = _getArgs('-zip',args)
		tgz = _getArgs('-tgz',args)
		tar = _getArgs('-tar',args)
		dt = _getArgs('-dt',args)
		if not (fs or zip or tgz or tar): raise ValueError('getArchive needs an output format from -fs -tgz -tar -zip')
		n = len(args)
		if n>1: raise ValueError('getArchive takes at most one tag argument')
		if n and args[0]=='now':
			aTag = 'now'
			sTag = self.tag+'-now'
			act = '-D'
		else:
			aTag = self._tagFromArg(n and args[0] or None)
			sTag = dt and aTag or self.tag+'-%s-%s' % tuple(self.major_minor(aTag))
			act = '-r'
		xDir = os.path.join(self.workingDir,sTag)
		kill(xDir)
		self._cvs(['-z3 export','-d',sTag,act,aTag,self._getProject()])
		from .appmonitor import AppMonitor
		a = AppMonitor(xDir,verbose=self.verbose)
		a.writeSignedSourceManifest()
		if not a.verifySignedSourceManifest(): raise ValueError("Can't verify source_manifest")
		for go, kind in ((zip,'zip'),(tar,'tar'),(tgz,'tgz')):
			if go: a.makeSourceArchive('../%s.%s' % (sTag,kind),kind=kind,copyDir=None)
		if not fs:
			self.resetDir()
			self.goWorkingDir()
			kill(sTag)

if __name__=='__main__':
	def usage(msg=None):
		cmd = os.path.basename(sys.argv[0])
		if msg: print('%s error: %s' % (cmd, msg))
		print('       %s directory release [-n(oversiondir)] [-zip] [-tgz] [-tar] [-dt] tag' % cmd)
		print('       %s directory getArchive [-fs] [-zip] [-tgz] [-tar] [-dt] tag' % cmd)
		sys.exit(msg and 1 or 0)
	argv = sys.argv
	v = (getFlag('-v') and 1 or 0)+(getFlag('-v') and 1 or 0)

	if len(argv) < 2:
		usage()
	else:
		D = argv[1]
		if not os.path.isdir(D): usage('directory %s not found!' % D)

		name = argv[2]
		a = Releaser(D, verbose=v)
		m = getattr(a, name, None)
		if not m: usage('method "%s" not found!' % name)
		else:
			r = m(*argv[3:])
			if r: print(r)
