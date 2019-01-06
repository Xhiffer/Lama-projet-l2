#copyright ReportLab Europe Limited. 2000-2016
#all rights reserved
'''
CGI support utilities
'''
__version__='3.3.0'
import sys, string, os, cgi, random, struct, time
from rlextra.utils.unifunc import unifunc

@unifunc
def quoteValue(v):
	"""Defense against people embedding Javascript in parameters.
	Script kiddies often hope that you will echo through some form
	parameter like a surname in a text field into HTML, so they
	can embed some huge chunk of their own HTMl code in it.
	This ensures any tags in input are escaped and thus deactivated"""

	vs = v.split(u"&")
	if len(vs)>1:
		# quote ampersands, but not twice
		v = u'&'.join([vs[0]]+
				[((u";" not in f or len(f.split(u";")[0].split())>1) and u'amp;' or '')+f for f in vs[1:]]
				)
	return v.replace(u"<",u"&lt;").replace(u">",u"&gt;").replace(u'"',"&quot;").replace(u"'",u"&#039;")

@unifunc
def unQuoteValue(v):
	"""Opposite of quoteValue()"""
	return v.replace(u'&#039;', u"'").replace(u'&quot;', u'"').replace(u'&gt;', u'>').replace(u'&lt;', u'<').replace(u'&amp;', u'&')

def makeCgiScript(cgiDir, scriptName, workDir, workModule, workFunc, verbose=0,
					kind='kfdserver', script_pfx=None):
	"""Generates a well formed CGI script in the given directory.
	Does nothing if one exists and if it would be identical to the
	one created.  Thus, programs can call this often or in setup
	scripts."""
	if kind=='kfdserver':
		text =	[
				'import os, sys',
				'os.chdir("%s")' % workDir,
				'sys.path.insert(0, os.getcwd())',
				'import %s' % workModule,
				'%s.%s()' % (workModule, workFunc),
				]
	elif kind=='ers':
		if not script_pfx: script_pfx = os.path.splitext(os.path.basename(scriptName))[0]
		text =	[
				'if __name__=="__main__": #noruntests',
				'	from rlextra.ers.controller import main',
				'	main(1,APPDIR="%s",SCRIPT_PFX="%s")' % (workDir,script_pfx),
				]
	else:
		raise ValueError("Unknown script kind='%s'" % kind)

	text = string.join(['#!%s -u'%sys.executable]+text,'\n')
	filename = os.path.join(cgiDir, scriptName)
	if os.path.isfile(filename):
		currentText = open(filename, 'r').read()
		if currentText == text:
			if verbose:print('cgi already correct, no change needed')
		else:
			open(filename, 'w').write(text)
			if verbose: print('wrote %s' % filename)
	else:
		open(filename, 'w').write(text)
		if verbose: print('wrote %s' % filename)
	# now check executable permissions. How could we detect mode?
	if sys.platform != 'win32':
		os.chmod(filename, 0o755)
		if verbose: print('set to executable')

def getCgiParams():
	"""Returns dictionary of CGI parameters. Quoted for safety
	by default; this will not affects most real world things we do"""
	dictionary = {}
	form = cgi.FieldStorage()
	for name in list(form.keys()):
		try:
			value = form[name].value
		except AttributeError:
			raise AttributeError('form["%s"]=%s'%(name,str(form[name])))
		dictionary[name] = quoteValue(value)
	return dictionary

def getCommandLineParams():
	"""Alternate syntax for getting key/value params.
	Use key=value on the command line"""
	dictionary = {}
	for arg in sys.argv[1:]:
		chunks = string.split(arg, '=')
		if len(chunks) == 2:
			key, value = chunks
			dictionary[key] = value
	return dictionary

def isCGI():
	"Attempt to guess if current process is running CGI"
	# use environment variables.  There are many candidates
	# and we should probably check ten of them and give
	# a fractional answer :-(
	return 'GATEWAY_INTERFACE' in os.environ

def getParams():
	"""Returns either CGI or command line parameters.

	Should be the generic handler, so we can always
	test a CGI app by doing the likes of
	  ./myapp.cgi action=request codename=wombat
	"""
	if isCGI():
		return getCgiParams()
	else:
		return getCommandLineParams()

try:
	pid = open('/dev/urandom','rb')
	dur = pid.read(4)
	pid.close()
	dur = struct.unpack('L',dur)[0]
except:
	dur = 0x7895

try:
	pid = int(os.getpid())
except:
	pid = 0x1234

random.seed(int(time.time()*0xfabcd13)|(pid<<64)|(dur<<32))
del pid, dur
def n_random_bits16(n):
	'''return at least n random bits in hex'''
	return hex(random.getrandbits(n))[2:-1].upper()

def n_random_bits36(n,b=36):
	'''return at least n random bits in base36 0-9a-z'''
	from . import baseconvert
	return baseconvert.baseconvert(n_random_bits16(n),baseconvert.BASE16,getattr(baseconvert,'BASE%d'%b))

class TimeStamp:
	def __init__(self,pfx=None,sfx=None,appName=None,hostname=None, base=36):
		import time, socket
		self.pfx = pfx
		self.sfx = sfx
		self.now = time.time()
		(self.year, self.month, self.day, self.hour, self.minute, self.second) = time.gmtime(self.now)[:6]
		self.currentDateString = "%s%02d%02d" % (self.year, self.month, self.day)
		self.timeStamp = "%s%02d%02d%02d" % (self.currentDateString, self.hour, self.minute, self.second)
		if hostname is None: hostname = socket.gethostname()
		self.hostname = hostname
		self.appName = appName
		self.random_bits = n_random_bits36(128, b=base)
		self.getCurrentId()

	def getCurrentId(self):
		self.currentId = '-'.join([_f for _f in (self.pfx, self.hostname, self.appName, self.timeStamp,  self.random_bits, self.sfx) if _f])
		return self.currentId

def thisYear():
	return time.gmtime()[0]

def copyrightYearRange(startYear,sep='-'):
	latestYear = thisYear()
	if latestYear<=startYear: return str(startYear)
	return str(startYear)+sep+str(latestYear)

class BorgTimeStamp(TimeStamp):
	__borg = {}
	def __init__(self,pfx=None,sfx=None,appName=None,hostname=None,isBorg=True):
		if isBorg: self.__dict__ = self.__borg
		if not self.__dict__:
			if not appName:
				appName = os.environ.get('SCRIPT_NAME','')
				if not appName:
					appName = sys.argv[0]
					i = 1
					while not appName:
						try:
							frame = sys._getframe(i)
							i += 1
						except:
							break
						upLocals = frame.f_locals
						for name in ('req','request'):
							req = upLocals.get(name,None)
							if req:
								appName = getattr(req,'url','')
								if appName: break
				if appName: appName=os.path.splitext(os.path.basename(appName))[0]
			if not appName: appName = 'unknownapp'
			TimeStamp.__init__(self,pfx=pfx,sfx=sfx,appName=appName,hostname=hostname)

	def reset(self,pfx=None,sfx=None,appName=None,hostname=None):
		if self.__dict__:
			pfx = pfx or self.pfx
			sfx = sfx or self.sfx
			appName = appName or self.appName
			hostname = hostname or self.appName
			self.clear()
			self.__init__(pfx=pfx,sfx=sfx,appName=appName,hostname=hostname)

	def clear(self):
		self.__dict__.clear()

def _reset():
	BorgTimeStamp().clear()

from reportlab.rl_config import register_reset
register_reset(_reset)
del register_reset
