"""
Logging functionality
Tried to make it human readable.

Whitespace may be put on either end of entry format.

Store global logging information as basic types (strings, ints, lists of ints...)
in attributes of ThisProcessLogEntry.

All entry lines are prefixed with either "." or "="
"""
import os, sys, time
import collections

LOGDIR = getattr(sys,'_LOGDIR','../logs')
LOGFN = SCRIPT = LOGPATH = now = currentid = None
def _logStart(script=None,dir=LOGDIR,fn=None):
	global LOGDIR, LOGFN, SCRIPT, LOGPATH, LOGGLOB, now, currentid
	from rlextra.utils.cgisupport import BorgTimeStamp
	cds = BorgTimeStamp()
	cds, currentid = cds.currentDateString, cds.currentId

	if script is None: script = sys.argv[0]
	SCRIPT = os.path.splitext(os.path.basename(script))
	PFX = getattr(sys,'_LOGPFX',SCRIPT[0])
	if not PFX: PFX = 'stdin'
	if PFX[-1] not in ['-','_']: PFX = PFX+'_'

	LOGDIR=os.path.abspath(dir)
	LOGFN = fn or "%slog%s.txt" % (PFX,cds)
	LOGGLOB="%slog*.txt" % PFX
	SCRIPT = len(SCRIPT)==2 and script or SCRIPT[0]+'.cgi'
	LOGPATH = os.path.join(LOGDIR, LOGFN)

_logStart()

def logfiles():
	import glob
	return glob.glob(os.path.join(LOGDIR, LOGGLOB))

startmarker = ">>>"
atprefix = atsuffix = "===="
endmarker = ".<<"
tb_limit = 100 # traceback limit

class LogEntry:
	"""
	Log entry that knows how to make itself into a string and restore itself from a string.
	It is hoped that the entry is more or less human readable (especially when attributes are strings).
	All attributes are stored in the stringiffied repr.
	Restrictions: All attribute names except __id__ shouldn't begin with an underscore.
	   All attribute values should be repr-able types (ints, strings, dict of string->string etc).
	"""
	def __init__(self, id=None):
		if id is None:
			id = currentid
		self.__id__ = id

	def _entry(self):
		"""stringiffied entry for self"""
		# for each local attribute if it is a string just put it on a line
		# if not repr it.
		atts = dir(self)
		atts.sort()
		L = []
		a = L.append
		a(startmarker+" "+repr(self.__id__))
		for att in atts:
			if att[0]=="_": continue
			attline = "%s %s %s" % (atprefix, att, atsuffix)
			a(attline)
			v = getattr(self, att)
			if isinstance(v,str):
				v = v.replace("\n", "\n. ")
				a(". "+v)
			else:
				a("= "+repr(v))
		a(endmarker)
		a("")
		return "\n".join(L)

	def _restore(self, entry):
		"""attempt to restore self from entry -- may fail if attributes are too complex"""
		entry = entry.strip()
		ls = len(startmarker)
		if entry[:ls] != startmarker:
			raise ValueError("no start marker")
		le = len(endmarker)
		if entry[-le:] != endmarker:
			raise ValueError("invalid entry termination %s" % repr(entry[-le:]))
		entry = entry[:-le]
		lines = entry.split("\n")
		line0 = lines[0]
		lines = lines[1:]
		[sm, id] = line0.split()
		self.__id__ = eval(id)
		while lines and lines[0]:
			atline = lines[0].strip()
			#print "atline", repr(atline)
			[prefix, attr, suffix] = atline.split()
			if prefix!=atprefix or suffix!=atsuffix:
				raise ValueError("invalid attribute line %s" % repr(atline))
			del lines[0]
			attdone = None
			vlines = []
			prefix = None
			while lines and not attdone:
				vline = lines[0]
				chars2 = vline[:2]
				if prefix is not None and prefix!=chars2:
					attdone = 1
				else:
					vlines.append(vline[2:])
					prefix = chars2
					del lines[0]
			if prefix==". ":
				value = "\n".join(vlines)
			elif prefix=="= ":
				value = "".join(vlines).strip()
				try:
					value = eval(value)
				except:
					value = "*** CAN'T EVAL: %s" % repr(value)
			else:
				raise ValueError("invalid prefix %s" % repr(prefix))
			setattr(self, attr, value)
		if len(lines)>1:
			raise ValueError("trailing garbage in log entry")

# the global default log entry
def resetThisProcessEntryLog():
	global ThisProcessLogEntry, now
	ThisProcessLogEntry = LogEntry()

resetThisProcessEntryLog()

def _tb2html(tbt,tbv,tb):
	if sys.hexversion<0x2020000:
		from rlextra.utils.cgisupport import quoteValue
		import traceback
		html = quoteValue('\n'.join(traceback.format_tb(tb) + ['%s: %s' % (str(tbt),str(tbv))]))
	else:
		import cgitb
		html = cgitb.html((tbt,tbv,tb),context=None)
		html = html[html.find('>')+1:html.find('<!-- The above')]
	return '<pre>%s</pre>'%html

_timeStarted = 0
def apply_wrapper(f, args, kwargs=None, logentry=None, logfile=LOGPATH, dolog=1, log_filter=(lambda :1),errorHandle=None, restoreSYS={'stdout':sys.__stdout__, 'stderr': sys.__stdout__},removeFromDict=['include']):
	"""apply f.  If error, put error info into log entry, re-raise Error
	   if no error, return (result,)
	"""
	if logentry is None:
		logentry = ThisProcessLogEntry
	global _timeStarted
	_timeStarted = time.time()
	logentry.B_function_name = f.__name__
	logentry.C_args = args
	if kwargs is None: kwargs = {}
	logentry.D_kwargs = kwargs
	import traceback
	cwd = os.getcwd()
	try:
		f(*args, **kwargs)
		if os.getcwd() != cwd: os.chdir(cwd)
		if dolog and log_filter(): writeToLog(logfile, logentry, removeFromDict+['data'])
	except:
		if os.getcwd() != cwd: os.chdir(cwd)
		tbt,tbv,tb = sys.exc_info()
		tblist = traceback.format_tb(tb)
		logentry.AA_ERROR_traceback = "\n".join(tblist)
		logentry.AA_ERROR_type = str(tbt)
		logentry.AA_ERROR_value = str(tbv)
		if dolog:
			writeToLog(logfile, logentry, removeFromDict)
		for k, v in list(restoreSYS.items()): setattr(sys,k,v)
		if not errorHandle: raise
		if errorHandle in ('html', 'partial_html'):
			if errorHandle=='html': print('Content-Type: text/html\n\n<html><head></head><body>')
			print('<h1><font color="red">ERROR</font></h1>%s' % _tb2html(tbt,tbv,tb))
			if errorHandle=='html': print('</body></html>')
			del tbt,tbv,tb
		elif isinstance(errorHandle, collections.Callable):
			errorHandle(logentry,tbt,tbv,tblist)
		else:
			trace_back.print_exc()

def writeToLog(logfile, e, removeFromDict=[]):
	e.timing = _timeStarted,time.time()-_timeStarted
	e.timeStarted = _timeStarted
	args = e.C_args
	if args:
		D = args[0]
		if type(D) is type({}):
			for r in removeFromDict:
				if r in D: del D[r]
	cwd = os.getcwd()
	text = e._entry()
	f = open(logfile, "a")
	f.write(text)
	f.close()

def rerun(f, logentrytext):
	e = LogEntry()
	e._restore(logentrytext)
	#print e._entry()
	return apply_wrapper(f, e.C_args, e.D_kwargs)

def getentry(id, logfile=LOGPATH):
	"""Look thrue logfile for (first occurrence) id, rerun it if found"""
	if type(logfile) is type(''):
		f = open(logfile, "r")
	else:
		f = logfile
	ls = len(startmarker)
	found = 0
	# look for start
	while not found:
		line = f.readline()
		if not line:
			raise ValueError("eof before finding id=%s in %s" % (repr(id), repr(logfile)))
		if line[:ls] == startmarker:
			[sm, idr] = line.strip().split()
			thisid = eval(idr)
			if thisid==id:
				found = 1
	# now look for end
	found = 0
	L = [line]
	a = L.append
	le = len(endmarker)
	while not found:
		line = f.readline()
		if not line:
			raise ValueError("eof before finding end of id=%s in %s" % (repr(id), repr(logfile)))
		#wrap dictionary somewhat
		if line[0:4] == '= ({':
			line = line.replace(',',',\n')
		a(line)
		if line[:le]==endmarker:
			found = 1
	text = "".join(L)
	return text

def rerunentry(function, id, logfile=LOGPATH):
	text = getentry(id, logfile)
	return rerun(function, text)

def readEntries(logfile):
	try:
		log = open(logfile).read()
	except:
		log = "" # no such file?
	L = []
	a = L.append
	cursor = 0
	le = len(endmarker)
	while 1:
		st = log.find(startmarker, cursor)
		if st<0: break
		en = log.find(endmarker, st)
		if en<0: break	# partial/incomplete ignore it
		cursor = en+le
		entrytext = log[st:en+le]
		e = LogEntry()
		e._restore(entrytext)
		a(e)
	return L

def entryListing(back=0, limit=100, logfile=LOGPATH):
	"""hyperlinked text of entries going back from most recent"""
	# this implementation may not be advisable if the log gets huge
	text = "<h1>Recent Log lists going back %s</h1>" % back
	try:
		logf = open(LOGPATH)
		log = logf.read()
	except:
		log = "" # no such file?
	L = []
	a = L.append
	cursor = 0
	done = 0
	le = len(endmarker)
	while not done:
		st = log.find(startmarker, cursor)
		if st<0:
			done=1
			break
		else:
			en = log.find(endmarker, st)
			if en<0:
				raise ValueError("incomplete log")
				# just ignore it (?)
				done = 1
				break
			else:
				cursor = en+le
				entrytext = log[st:en+le]
				e = LogEntry()
				e._restore(entrytext)

				id = e.__id__
				action = "(none)"
				try:
					args = e.C_args
					dict = args[0]
					action = dict["action"]
				except:
					pass
				if hasattr(e, 'AA_ERROR_type'):
					item = """<a href="%s?action=test_list_log_entry&id=%s"><font color="red">id=%s action=%s error=%s</font></a>""" % (
							SCRIPT,id, id, action, e.AA_ERROR_type)
				else:
					item = """<a href="%s?action=test_list_log_entry&id=%s">id=%s action=%s</a>""" % (
							SCRIPT, id, id, action)

				a(item)
	# cut out the requested entries
	n = len(L)
	last = max(0,n-back)
	first = max(0, n-back-limit)
	L = L[first:last]
	if first>0:
		nextlink = """\n<a href="%s?action=test_log_probe&back=%s">get more</a>"""% (SCRIPT,(back+limit))
		L.append(nextlink)
	listing = "".join(L)
	listing = "\n<pre>\n%s\n<pre>" % listing
	return text + listing

def testentries():
	L1 = LogEntry()
	L1.list = list(range(3))
	L1.name = "first entry"
	L1.text = """
	a lot
	of information
	"""
	s = L1._entry()
	print(s)
	L2 = LogEntry()
	L2._restore(s)
	if L1.list!=L2.list or L1.name!=L2.name or L1.text!=L2.text or L1.__id__!=L2.__id__:
		print(L1.__dict__)
		print(L2.__dict__)
		balk
	if L2._entry()!=s:
		balk2
	print("testing error mechanism")
	def f(x):
		if type(x) is not type(1):
			raise ValueError("bad x %s" % repr(x))
		print("good x=", x)
	apply_wrapper(f, ("example argument",))
	print("ThisProcessLogEntry entry is now")
	print(ThisProcessLogEntry._entry())
	firstid = ThisProcessLogEntry.__id__
	print(); print("resetting")
	resetThisProcessEntryLog()
	print("running with good arg")
	apply_wrapper(f, (33,))
	print("entry is now")
	text = ThisProcessLogEntry._entry()
	print(text)
	print(); print("now rerunning from text")
	rerun(f, text)
	print(); print("now rerunning first run from log file (should get traceback again)")
	rerunentry(f, firstid)
	print("now printing entryListing")
	print(); print(entryListing())

if __name__ == "__main__": #noruntests
	if len(sys.argv)>1:
		for id in sys.argv[1:]:
			print(getentry(id,sys.stdin))
	else:
		testentries()
