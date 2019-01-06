#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
'''Utilities for grabbing modules and examining the contents'''
from __future__ import print_function
from reportlab import cmp
__version__='3.3.0'
import sys, os, imp, fnmatch, re, inspect, time, traceback
from reportlab.lib.utils import rl_exec, getStringIO, isNonPrimitiveInstance, annotateException
import tokenize
path_join=os.path.join
path_basename=os.path.basename
path_dirname=os.path.dirname
path_isfile=os.path.isfile
path_isdir=os.path.isdir
path_splitext=os.path.splitext
path_normpath=os.path.normpath
path_normcase=os.path.normcase
_tg0 = 0
_ofile = None
def importModule(mName,fails=None):
	'''return a module given the import name ie reportlab.lib.utils or whatever'''
	o, e = sys.stdout, sys.stderr
	cwd = os.getcwd()
	if _ofile: t0 = time.time()
	try:
		try:
			_NS = {}
			rl_exec('import %s as __x__'%mName,_NS)
			if _ofile:
				t = time.time()
				print('##### import',mName,'OK %.3f %.3f' % (t-t0, t-_tg0), file=_ofile)
			return _NS['__x__']
		except:
			if _ofile:
				t = time.time()
				print('!!!!! import',mName,'FAILED %.3f %.3f' % (t-t0, t-_tg0), file=_ofile)
				try:
					traceback.print_exc(None,_ofile)
				except:
					print('!!!!! traceback failure',file=_ofile)
			if fails is not None: fails.append(mName)
			return None
	finally:
		if cwd!=os.getcwd(): os.chdir(cwd)
		sys.stdout, sys.stderr = o, e

def reloadModule(m):
	try:
		if isinstance(m,str):
			if m in list(sys.modules.keys()):
				m = reload(sys.modules[m])
			else:
				m = importModule(m)
	except:
		if _ofile:
			import traceback
			print('reload(%s) failed' % m, file=_ofile)
			traceback.print_exc(None,_ofile)
		m = None
	return m

def loadSrcModule(mPath):
	'''return a module based on the path to a source file'''
	try:
		return imp.load_source(os.path.splitext(os.path.basename(mPath))[0],mPath,open(mPath,'r'))
	except:
		return None

def normpath(x):
	return path_normpath(path_normcase(x))

def isPyFile(p):
	return path_isfile(p) or path_isfile(p+'c') or path_isfile(p+'o')

def _processPackageDir(p,dn,P,allowCompiled=True):
	if _ofile: print('searching package', p, 'dn=',dn, file=_ofile)
	from reportlab.lib.utils import rl_glob, rl_isfile, rl_isdir, isCompactDistro
	if isCompactDistro():
		ext = '.pyc'
		init = '__init__'+ext
		FN = [normpath(x) for x in rl_glob(path_join(dn,'*'))]
		D = []
		dn = normpath(dn)
		for x in FN:
			x = path_dirname(x)
			if x not in D and rl_isdir(x) and path_dirname(x)==dn and rl_isfile(path_join(x,init)): D.append(x)
		F = [x for x in FN if x.endswith(ext) and path_dirname(x)==dn and not path_basename(x).startswith('__init__.')]
	else:
		ext = '.py'
		init = '__init__'+ext
		FN = [path_join(dn,x) for x in os.listdir(dn)]
		D = [x for x in FN if path_isdir(x) and isPyFile(path_join(x,init))]
		F = [x for x in FN if (x.endswith(ext) or (allowCompiled and (x.endswith(ext+'c') or x.endswith(ext+'o')))) and not path_basename(x).startswith('__init__.')]
	for f in F:
		mn = path_splitext(path_basename(f))[0]
		if p: mn = p+'.'+mn
		if mn not in P:
			if _ofile: print('appending 1',mn, file=_ofile)
			P.append(mn)
	for f in D:
		mn = p+('.'+path_basename(f))
		if mn not in P:
			if _ofile: print('appending 2',mn, file=_ofile)
			P.append(mn)

def _checkPmw():
	'''remove the Pmw loader interference'''
	mods = {}
	for n in '_Pmw', 'Pmw':
		try:
			m = sys.modules[n]
			del sys.modules[n]
			mods[n] = m
		except:
			pass
	return mods

def _uncheckPmw(mods):
	'''restore the Pmw loader interference'''
	sys.modules.update(mods)

def getModules(P=['reportlab.graphics'],X=[], MF=None, MD=None, FAILS=None, allowCompiled=True):
	'''Locate all modules descendant from elements of P'''

	if isinstance(X,str): X=X.split()
	xp = []
	axp = xp.append
	for p in X:
		rep = fnmatch.translate(p)
		if rep.endswith('$'): rep = rep[:-1]
		elif rep.endswith(r'\Z(?ms)'): rep = rep[:-7]
		axp(rep)
	xp = re.compile('a^' if not xp else '^'+('|'.join(xp))+'$')
	M = []
	P = list(P.split() if isinstance(P,str) else P[:])
	if MF is None: MF = []
	if MD is None: MD = []
	while P:
		p = P[0]
		del P[0]
		if xp.match(p):
			if _ofile:
				t = time.time()
				print('!!!!! import',p,'EXCLUDED %.3f %.3f' % (0, t-_tg0), file=_ofile)
			continue
		if p=='.':
			_processPackageDir('',os.getcwd(),P,allowCompiled=allowCompiled)
		elif p.startswith('!'):
			_processPackageDir('',p[1:],P,allowCompiled=allowCompiled)
		else:
			if _ofile: print('trying importModule(%s)' % p, file=_ofile)
			m = importModule(p,fails=FAILS)
			if m and m not in M:
				mn = getattr(m,'__file__',None)
				if mn is not None:
					if _ofile: print('module %s found __file__=%s' % (m,mn), file=_ofile)
					if mn not in MF:
						M.append(m)
						MF.append(mn)
						if _ofile: print('appending 3', m, mn, file=_ofile)
						if os.path.basename(mn)[:9]=='__init__.':
							MD.append(os.path.dirname(mn))
							#it's a package so recur
							_processPackageDir(p,os.path.dirname(mn),P,allowCompiled=allowCompiled)
	return M

def getModuleClassMethod(moduleName,className,methodName):
	M = importModule(moduleName)
	if not M: return None
	C = getattr(M,className,None)
	if not C: return None
	return getattr(C,methodName,None)

def getModuleClassMethodDefaults(moduleName,className,methodName,**kw):
	method = getModuleClassMethod(moduleName,className,methodName)
	if method:
		argspec = inspect.getargspec(method.__func__)
		V = argspec[3]
		N = argspec[0][1:]
		for k in list(kw.keys()):
			i = N.index(k)
			kw[k] = (i>=0 and i<len(V)) and V[i] or None
	return kw

def getAttributes(obj,private=0,advanced=0):
	from reportlab.graphics.shapes import Group
	A = []
	P = []
	isG = isinstance(obj,Group)
	if hasattr(obj,'contents') and isG:
		contents = obj.contents
		P.append(contents)
	else:
		contents = []

	def addAP(k,v,A=A,P=P):
		if (k,v) in A or v in P: return
		if isNonPrimitiveInstance(v):
			A.append((k,v))
			P.append(v)
		else:
			A.append((k,v))

	attrMap = getattr(obj,'_attrMap',None)
	R = []
	if attrMap:
		for k,a in attrMap.items():
			advancedUsage = getattr(a,'_advancedUsage',0)
			if (not k.startswith('_') or private) and (hasattr(obj,k) and (not advancedUsage or advanced)):
				v = getattr(obj,k,None)
				addAP(k,v)
			else:
				R.append(k)

	for k,v in list(getattr(obj,'__dict__',{}).items()):
		if k not in R and (not k.startswith('_') or private):
			addAP(k,v)
		else:
			R.append(k)
	g = getattr(obj,'getProperties',None)
	#pdb.set_trace()
	if g:
		for k,v in list(g(recur=0).items()):
			if k not in R and (not k.startswith('_') or private):
				addAP(k,v)
			else:
				R.append(k)

	for c in contents:
		addAP('contents[%d]'% contents.index(c),c)

	A.sort()
	return A

def pGetClassModule(v):
	try:
		return sys.modules.get(v.__module__)
	except:
		return None

def _normpath(p):
	return os.path.normcase(os.path.normpath(p))

def _cmpMRCN(a,b):
	'''compare two named modules by refcount and then name'''
	r = cmp(sys.getrefcount(sys.modules[b]), sys.getrefcount(sys.modules[a]))
	if not r: r = cmp(b,a)
	return r

absfile=lambda x: os.path.normcase(os.path.abspath(x))

def _getmembers(m,_gm=inspect.getmembers,_ff=lambda v: v[0][:2]!='__'):
	return list(filter(_ff,_gm(m)))

def _getfunctions(members,m):
	mfile = m.__file__
	if mfile[-1] in ['c','o']: mfile = mfile[:-1]
	try:
		a = m.__loader__.archive + os.sep
		if mfile.startswith(a):
			mfile = mfile[len(a):]
		ff = lambda v,mfile=mfile: inspect.isfunction(v[1]) and v[1].__code__.co_filename==mfile
	except:
		mfile = absfile(mfile)
		ff = lambda v,mfile=mfile: inspect.isfunction(v[1]) and absfile(v[1].__code__.co_filename)==mfile
	return list(filter(ff,members))

def _getclasses(members,m):
	return list(filter(lambda v,m=m: inspect.isclass(v[1]) and pGetClassModule(v[1])==m,members))

def _getvars(members, _ff = lambda v: not (inspect.isclass(v[1]) or inspect.ismethod(v[1])\
					or inspect.ismodule(v[1]) or inspect.isroutine(v[1]) or inspect.istraceback(v[1])\
					or inspect.iscode(v[1]) or inspect.isframe(v[1]))):
	return list(filter(_ff,members))

class KnownNames:
	def __init__(self,SX=([],[])):
		self._ga = {'modules':[],'classes':{},'funcs':{},'varsN':{}, 'varsI':{}, 'search':()}
		self._MD = []
		self.search = SX

	def __setattr__(self,name,value):
		if name=='search':
			self._search(value)
		elif name[0]=='_':
			self.__dict__[name] = value
		else:
			raise AttributeError(name)

	def __getattr__(self,name):
		if name in self._ga: return self._ga[name]
		raise AttributeError(name)

	def findName(self,name):
		R = {}
		A = self._ga
		for k,v in list(A.items()):
			if k=='search': continue
			if k == 'classObjs':
				if name in v: R['module'] = v[name]
			elif k == 'modules':
				N = [m.__name__ for m in v]
				if name in N: R[''] = name
			else:
				if	name in v: R[k] = v[name]
		return R

	def checkPath(self,path):
		'''return 1 if path is covered by our modules/dirs else 0'''
		D = _normpath(os.path.dirname(path))
		for d in self._MD:
			if D==_normpath(d): return 1
		return 0

	def reloadModule(self,M):
		'''reload a single module or set of modules R'''
		if not isinstance(M,(list,tuple)): R = [M]
		else:
			R = list(M)[:]
			R.sort()
			R.reverse()
		OM = []
		K = []
		M = R[:]
		while M:
			RR = []
			for m in M:
				om = self._delModule(m)
				if om:
					RR.append(m)
					OM.append(om[1])
					if om[0]: K.append(m)
			if not RR: break
			list(map(M.remove,RR))
		if not OM: return
		#if _ofile:
		#	print >>_ofile, '+++++++++++++++Final module links'
		#	for m in OM:
		#		print >>_ofile, m.__name__, sys.getrefcount(m)
		del OM
		#if _ofile and M: print >>_ofile, '#####UNDELETED modules',M
		ga = self._ga
		M = ga['modules']
		#if _ofile and M: print >>_ofile, '#####UNDELETED known modules',M
		C = ga['classes']
		F = ga['funcs']
		VN = ga['varsN']
		VI = ga['varsI']
		R.reverse()
		while R:
			RR = []
			for m in R:
				im = importModule(m)
				if im: RR.append(m)
				if m in K:
					self._addModule(m,M,C,F,VN,VI)
					self._finish(M,C,F,VN,VI)
			if not RR: break
			list(map(R.remove,RR))

	def _search(self,SX):
		ga=self._ga
		if not isinstance(SX,(list,tuple)): SX = [SX,ga['search'][1]]
		if SX==ga['search']: return
		ga['search'] = SX
		self._MD = []
		M = getModules(SX[0],SX[1],MD=self._MD)
		if _ofile:
			t = time.time()
			print("	getmodules done %.3f" % (t-_tg0), file=_ofile)
		if M==ga['modules']: return
		F={}
		C={}
		VN={}
		VI={}
		for m in M:
			self._addModule(m,M,C,F,VN,VI)
		if _ofile:
			t = time.time()
			print("	_addModule done %.3f" % (t-_tg0), file=_ofile)
		self._finish(M,C,F,VN,VI)
		if _ofile:
			t = time.time()
			print("	_finish done %.3f" % (t-_tg0), file=_ofile)

	def _addModule(self,m,M,C,F,VN,VI):
		if isinstance(m,str):
			m = importModule(m)
			if m is None: return
		if m not in M: M.append(m)
		members = _getmembers(m)
		for X,V in ((F,_getfunctions(members,m)),(C,_getclasses(members,m))):
			for v in V:
				n = v[0]
				X.setdefault(n,[]).append(m)
		V = _getvars(members)
		for v in V:
			i = id(v[1])
			n = v[0]
			VN.setdefault(n,[]).append(m)
			n = (n,m)
			VI.setdefault(i,[]).append(n)

	def _delModule(self,m):
		'''delete a module by name and remove it from sys.modules
		return (flag,module) flag is 1 if the module was in the controlled set
		'''
		if isinstance(m,str):
			m = sys.modules.get(m,None)
			if m is None: return None
		del sys.modules[m.__name__]
		ga = self._ga
		M = ga['modules']
		r = m in M
		if r:
			C = ga['classes']
			F = ga['funcs']
			VN = ga['varsN']
			VI = ga['varsI']
			members = [v for v in inspect.getmembers(m) if v[0][:2]!='__']
			for X,V in ((F,_getfunctions(members,m)),(C,_getclasses(members,m))):
				for v in V:
					n = v[0]
					try:
						X[n].remove(m)
						if X[n]==[]: del X[n]
					except:
						pass

			V = _getvars(members)
			for v in V:
				i = id(v[1])
				n = v[0]
				try:
					VN[n].remove(m)
					if VN[n]==[]: del VN[n]
				except:
					pass
				n = (n,m)
				try:
					VI[i].remove(n)
					if VN[i]==[]: del VN[i]
				except:
					pass
			M.remove(m)
			self._finish(M,C,F,VN,VI)
		#if _ofile: print('delModule(%s) rc=%d known=%d len(M)==%d' % (m.__name__,sys.getrefcount(m),r,len(M)),file=_ofile)
		return r,m


	def _finish(self,M,C,F,VN,VI):
		ga=self._ga
		ga['modules'] = M
		ga['classes'] = C
		ga['funcs'] = F
		ga['varsN'] = VN
		ga['varsI'] = VI
		CO = []
		for n,M in list(C.items()):
			for m in M:
				CO.append(getattr(m,n))
		ga['classObjs'] = CO

def _getKnown(gM=0,gK=1,dbg=0,
				search = ['fidelity.epscharts','reportlab.lib','reportlab','rlextra'],
				exclude = ['*fidelity.epscharts.do_*','reportlab.demo.*','reportlab.test*',
							'reportlab.doc*','reportlab.utils.*',
							'*fidelity.epscharts.updatedoc','reportlab.lib.graphdocpy',
							'*.guiedit.guiedit','*.guidialogs','*.CVS',
							],
			):
	global _tg0, _ofile
	try:
		from rlextra.graphics.guiedit.guiedit import _getConfig
		config = _getConfig(os.path.join(os.path.dirname(sys.argv[0]),'_guiedit.ini'))
		search = config.package.search
		exclude = config.package.exclude+['*.guiedit.guiedit','*.guidialogs']
	except:
		pass
	_ofile=dbg and sys.stdout or None
	if gM:
		_tg0 = time.time()
		pmwMods = _checkPmw()
		getModules(search,exclude)
		_uncheckPmw(pmwMods)
		print('getModules %.2f' % (time.time()-_tg0), file=_ofile)
	if gK:
		_tg0 = time.time()
		pmwMods = _checkPmw()
		globals()['_known']=K=KnownNames((search,exclude))
		_uncheckPmw(pmwMods)
		print('KnownNames %.2f' % (time.time()-_tg0), file=_ofile)
		print('#M=%d #F=%d #C=%d #V=%d'%(len(K.modules),len(list(K.funcs.keys())),
					len(list(K.classes.keys())),len(list(K.varsN.keys()))), file=_ofile)

class AssignCheckerLine:
	def __init__(self,text):
		self.text = text
		T = self.tokens(text)
		s = 0
		self.deletions = []
		self.assigns = []
		a = self.assigns.append
		for i in (i for i,x in enumerate(T) if x[1]=='=' and (i<2 or T[i-2][1] not in (',','('))):
			lhs = []
			for j in range(s,i):
				t = T[j][1]
				if t[-1] in "\"'":
					t = repr(eval(t))
				lhs.append(t)
			a((''.join(lhs),T[s][2][1],T[i+1][2][1]))
			s = i+1
		self.nAssigns = len(self.assigns)

	def delete(self,j):
		self.deletions.append(j)

	def restore(self,j):
		self.deletions.remove(j)

	def render(self):
		if len(self.deletions)==self.nAssigns: return ''
		t = self.text
		a = self.assigns
		for j in self.deletions:
			s,f = a[j][1:]
			t = t[:s]+(' '*(f-s))+t[f:]
		return t.lstrip()

	def LHS(self):
		L = getattr(self,'_LHS',None)
		if L==None:
			L = self._LHS = list(a[0] for a in self.assigns)
		return L
	LHS = property(LHS)

	@staticmethod
	def tokens(s):
		try:
			return list(tokenize.generate_tokens(getStringIO(s).readline))
		except:
			annotateException(': line=%r' % s)

class AssignChecker:
	def __init__(self,lines):
		self.lines = [AssignCheckerLine(l) for l in lines]

	def repeatedAssigns(self):
		RA = getattr(self,'_repeatedAssigns',None)
		if RA is None:
			LHS = {}
			for i,l in enumerate(self.lines):
				for j,lhs in enumerate(l.LHS):
					LHS.setdefault(lhs,[]).append((i,j))
			RA = self._repeatedAssigns = []
			for v in LHS.values():
				if len(v)>1:
					RA.extend(v[:-1])
			RA.sort()
		return RA
	repeatedAssigns = property(repeatedAssigns)

if __name__=='__main__':
	if '-prof' in sys.argv:
		import profile
		profile.run('_getKnown()','mutils.prof')
	else:
		_getKnown(dbg=1)
