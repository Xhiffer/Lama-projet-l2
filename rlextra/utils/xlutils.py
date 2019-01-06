import string, traceback, re, os
_rcrc_re=re.compile(r'=(?P<sh>\w+)!R(?P<r1>\d+)C(?P<c1>\d+)(?::R(?P<r2>\d+)C(?P<c2>\d+)|)',re.I)

def AddWorkBook(xl):
	if string.atoi(xl.Version[0])>=8:
		wb=xl.Workbooks.Add()
	else:
		wb=xl.Workbooks().Add()
	return wb

def DeleteSheet(wb,name):
	a=wb.Application
	da=a.DisplayAlerts
	if da: a.DisplayAlerts=0
	try:
		wb.Sheets(name).Delete()
	except:
		pass
	if da: a.DisplayAlerts=da

def NewSheet(wb,name):
	DeleteSheet(wb,name)
	sh=wb.Sheets.Add()
	sh.Name=name
	return sh

_ALPHABET="ABCDEFGHIJKLMNOPQRSTUVWXYZ"
def	Letter(i):
	i = i - 1
	j = i % 26
	i = i / 26
	if i>0:
		return _ALPHABET[i-1]+_ALPHABET[j]
	else:
		return _ALPHABET[j]

def RC(i,j):
	return Letter(j)+str(i)

def GetRange(sh, i,j,k,l):
	return sh.Range(RC(i,j)+':'+RC(k,l))

def WriteMX(sh,r,c,MX, label=None, fmt=None):
	if not label is None:
		sh.Cells(r,c).Value=label
		r=r+1
		c=c+1
	n,m = MX.shape
	rfmt="%s%%d:%s%%d"%(Letter(c),Letter(c+m-1))
	for i in range(n):
		sh.Range(rfmt%(r+i,r+i)).Value=tuple(MX[i,:].tolist())
	if not fmt is None: sh.Range(rfmt%(r,r+n)).NumberFormat=fmt
	return (r+n,c+m)

def _NoneToDefault(r,NoneValue=0):
	if type(r)==type(()): r=list(r)
	while 1:
		try:
			i=r.index(None)
		except ValueError:
			return r
		n=r[i:].count(None)
		r[i:i+n]=[NoneValue]*n

def _ReadMX(sh,r,c, n,m, NoneValue=0, typecode='d'):
	from Numeric import array, zeros
	A,B = Letter(c),Letter(c+m-1)
	try:
		cell1="%s%d" % (A,r)
		cell2="%s%d" % (B,r+n-1)
		def filt(x,d=0):
 			if x is None: return d
 			return x
		MX=array(list(map(lambda x,filt=filt: list(map(filt,x)),sh.Range(cell1,cell2).Value)),typecode)
	except:
		MX = zeros((n,m),typecode)
		fmt="%s%%d:%s%%d"%(A,B)
		for i in range(n):
			R=sh.Range(fmt%(r+i,r+i)).Value
			if m>1:
				R = R[0]
			try:
				MX[i,:]=array(R,typecode)
			except:
				MX[i,:]=array(_NoneToDefault(R,NoneValue),typecode)
	return MX,(r+n,c+m)

def ReadMX(sh,r,c, n,m, NoneValue=0, typecode='d'):
	return _ReadMX(sh,r,c, n,m, NoneValue=NoneValue, typecode=typecode)[0]

def splitNR(wb,nr):
	'''splits a named range from wb'''
	m = _rcrc_re.match(str(wb.Names(nr).RefersToR1C1))

	sh,r,c,n,m = m.group('sh'),int(m.group('r1')),int(m.group('c1')),m.group('r2'),m.group('c2')
	if n is not None:
		n = int(n) - r + 1
		m = int(m) - c + 1
	else:
		n = m = 1
	return sh, r,c, n,m

def readNR(wb,nr):
	'''returns a value from wb correponding to a named range'''
	sh, r,c, n,m = splitNR(wb,nr)
	return wb.Sheets(sh).Cells(r,c).Value

def readNRMX(wb,nr,NoneValue=0,typecode='d'):
	'''returns a matrix from wb correponding to a named range'''
	sh, r,c, n,m = splitNR(wb,nr)
	return _ReadMX(wb.Sheets(sh),r,c, n,m, NoneValue=NoneValue, typecode=typecode)[0]

def writeNRMX(wb,nr,mx):
	sh, r,c, n,m = splitNR(wb,nr)
	A,B = Letter(c),Letter(c+m-1)
	cell1="%s%d" % (A,r)
	cell2="%s%d" % (B,r+n-1)
	wb.Sheets(sh).Range(cell1,cell2).Value = mx[0:n,0:m]


def NumValid(x):
	if x is None: return 0
	try:
		if string.strip(str(x))=='': return 0
		return 1
	except:
		return 0

def CheckMinMax(sh, lim, refs):
	if lim is None: return
	v=(sh.Cells(refs[0][0],refs[0][1]).Value, sh.Cells(refs[1][0],refs[1][1]).Value)
	if NumValid(v[0]) and NumValid(v[1]):
		try:
			if v[0]<=v[1] and v[0]>=lim[0] and v[1]<=lim[1]: return
		except:
			pass
	raise ValueError("Bad dimensions in sheet %s\n\rlim=%s refs=%s v=%s"%(sh.Name,str(lim),str(refs),str(v)))

def	CCount(sh,row,start,lim=None):
	i=start
	while NumValid(sh.Cells(row,i).Value):
		i=i+1
	CheckMinMax( sh, lim, ((row, start), (row, i-1)))
	return i-start,i+1

def	RCount(sh,col,start,lim=None):
	i=start
	while NumValid(sh.Cells(i,col).Value):
		i=i+1
	CheckMinMax( sh, lim, ((start,col), (i-1,col)))
	return i-start,i+1

def TextBoxChange(TB,msg,append=0):
	try:
		locked = TB.Locked
		if locked: TB.Locked=0
		if append:
			TB.Value = TB.Value + msg
		else:
			TB.Value = msg

		if locked: TB.Locked=locked
	except:
		traceback.print_exc()

def getExcel():
	from win32com.client import Dispatch
	return Dispatch('Excel.Application')

def ensureOpen(xl,fn):
	fn = str(fn)
	if not os.path.isabs(fn):
		fn = os.path.abspath(fn)
	fn = string.lower(os.path.normcase(os.path.normpath(fn)))
	WB = xl.WorkBooks
	n = WB.Count
	while n:
		wb = WB(n)
		n -= 1
		if string.lower(str(wb.fullName))==fn: return wb

	return WB.Open(fn)

def normalizeLabel(w):
	return ''.join([_f for _f in w.lower().split() if _f])

def normalizeAndFixLabels(L, R={}):
	f = lambda x, K=list(R.keys()), R=R: x in K and R[x] or x
	return list(map(lambda n,f=f:''.join(map(f, [_f for _f in n.lower().split() if _f])),L))

class IndexedRow:
	'''a set of values with named indeces'''
	def __init__(self,indeces,values,norm=normalizeLabel):
		assert len(indeces)==len(values)
		self.__dict__['_indeces'], self.__dict__['_values'] = list(map(norm,list(indeces))), list(values)
		self.__dict__['_norm'] = norm

	def __getitem__(self,x):
		return self._values[self._indeces.index(self._norm(x))]

	def __setitem__(self,x,v):
		self._values[self._indeces.index(self._norm(x))] = v

	__getattr__ = __getitem__
	__setattr__ = __setitem__

	def index(self,x):
		return self._indeces.index(self._norm(x))
