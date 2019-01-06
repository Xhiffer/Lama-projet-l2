#copyright ReportLab europe Limited 2001-2016
#see license.txt for license details
import re
import collections
from reportlab.lib.utils import isUnicode, asUnicode, strTypes, isStr
_sql_select_re = re.compile(r'\s*select\s+(.+)\s+from\s+',re.I)
_id_re=re.compile(r'\b[a-zA-Z_]\w*\b\s*(?!\()')

def _checkIn(x,N):
    if isinstance(N,int): return N
    return x in N

class DataMaker:
    """class defining data production"""
    def __init__(self,**kw):
        self._data = []
        self.__dict__.update(kw)

    def connect(self, verbose):
        "Open file, database connection, Excel or whatever"
        self.verbose = verbose

    def close(self):
        "Close file, database connection, Excel or whatever"
        pass

    def fetchNextDataSet(self):
        "Return next block of data as nested list, or None if no more"
        if len(self._data) == 0:
            return None
        else:
            block = []
            data = self._data
            grpCol = self.name2Column(self.groupingColumn)
            row = 0
            initialGroup = data[row][grpCol] if grpCol is not None else None
            while 1:
                block.append(data[0])
                data = data[1:]
                if len(data) == 0:
                    break
                if grpCol is None or data[0][grpCol] != initialGroup:
                    break
            self._data = data
            return block

    def fetchData(self):
        "return a list of data sets"
        D = []
        a = D.append
        while 1:
            d = self.fetchNextDataSet()
            if d is None: return D
            a(d)

    def name2Column(self,name):
        if isinstance(name,int) or name is None: return name
        if not getattr(self,'_name_map',None):
            raise ValueError('%r lacks a _name_map attribute' % self)
        try:
            return self._name_map[self.normalizeName(name)]
        except:
            raise ValueError('Cannot map %r to a column' % name)

    def normalizeName(self,name):
        if not isUnicode(name):
            for enc in ('utf8','latin1'):
                try:
                    name = asUnicode(name,enc)
                    break
                except:
                    pass
            else:
                raise ValueError('Cannot normalize name %r' % name)
        r = name.strip().lower()
        nns = getattr(self,'normalizeNameSpaces',None)
        if isStr(nns):
            r = nns.join(filter(None,r.split()))
        return r

    def makeNameMap(self,names):
        self._name_map = {self.normalizeName(n):i for i,n in enumerate(names)} if names else None

class CSVDataMaker(DataMaker):
    """Defines how to make data from a CSV file"""
    filename =  None        # name of the file or perhaps something with a readlines method
    headerRows = 1          # number of header rows
    nameRow = 0             # nameRow which row defines column names
    columnNames = None      # use if you need fake column names and headerRows = 0
    columnCount = None      # number of columns
    groupingColumn = 0      # which column to group by
    integerColumns = ()     # which columns are integer
    dateColumns = ()        # which columns are dates
    floatColumns = ()       # which columns are floats
    floatIgnoreChars = ''   # extra characters to strip out from floats
    sep = ','               # what is the csv separator
    fast = 0                # use fast parsing ie assume that sep will work fine
    na = ['None', 'N/A']    # the not availble string
    sbl = 1                 # if blank lines should be stripped
    sql = None              # the sql to be used for calcs (we only handle real simple stuff)
    dateParser = None       # the date parser or None 
    no_na_dates = None      # if dates must be valid, either None, 0/1 or a sequence
                            # of date columns which must be checked
    ignoreLinesMatching = None  #if set, ignore any line matching given regular expression
    normalizeNameSpaces = None

    def __init__(self,**kw):
        DataMaker.__init__(self,**kw)

    class _arithNone:
        def __add__(self,other):
            return self
        __sub__ = __mul__ = __div__ = __pow__ = __neg__ = __abs__ = __rsub__ = __rdiv__ = __add__
    _arithNone = _arithNone()

    def parseDate(self, text):
        """Attempt to get a date out.

          Currently only supports default Excel/CSV format of 31/01/1999 00:00:00
          and ignores hours/minutes."""
        daytext = text.split(' ')[0] # chop off hours if present
        d, m, y = list(map(int, daytext.split('/')))
        if y < 100:
            if y > 80:
                y = y + 1900
            else:
                y = y + 2000
        from reportlab.lib.normalDate import NormalDate
        return NormalDate((y, m, d))

    def connect(self,verbose=0):
        from rlextra.utils.csv import _processLine
        lines = (hasattr(self.filename,'readlines') and self.filename or open(self.filename,'r')).readlines()
        if self.sbl: lines = [x for x in lines if x.strip()]

        if self.ignoreLinesMatching:
            pat = re.compile(self.ignoreLinesMatching)
            lines = [x for x in lines if pat.match(x) is None]

        #remove unicode byte order marks if present
        BOM = '\xEF\xBB\xBF'
        if lines[0].startswith(BOM):
            #print('Found unicode byte order mark, stripping it')
            first = lines[0][3:]
            lines = [first] + lines[1:]

        n = self.headerRows
        if n>0:
            headers = lines[:n]
            lines = lines[n:]
            j = self.nameRow
            if j is not None:
                if j>=n: raise ValueError("nameRow=%d not in headerRows [0:%d]" % (j,n))
                names = _processLine(headers[j],self.sep)
        else:
            names = getattr(self,'columnNames',None)
        names = self._names = [self.normalizeName(x) for x in names] if names is not None else None

        sql = self.sql
        if isinstance(sql, collections.Callable): sql = sql()
        sql.strip()
        if sql:
            if not names: raise ValueError("sql attribute and no column names")
            self._checkCSVColumnNames('integerColumns',names)
            self._checkCSVColumnNames('floatColumns',names)
            self._checkCSVColumnNames('dateColumns',names)
            m = _sql_select_re.match(sql)
            if not m: raise ValueError("can't match %s.sql='%s'" % (self.__class__.__name__,sql))
            X = str.lower(str.strip(m.group(1)))
            if X!='*':
                sqlIDs = self._sqlIDs = list(map(str.strip,_id_re.findall(X)))
                self._checkCSVColumnNames('_sqlIDs',names)
                X = map(str.strip,X.split(','))
                E = []
                def handleID(m,names=names):
                    c = str.strip(m.group(0))
                    if c in names:
                        x = names.index(c)
                        return "self._exConvertField(_f,%d,'%s',lineNo)" % (x,c)
                    else:
                        return c

                for c in X:
                    c = c.strip()
                    if c in names: v = names.index(c)
                    else: v = _id_re.sub(handleID,c)
                    E.append((c,v))
            else:
                E = list(zip(names,list(range(len(names)))))

            grpCol = self.groupingColumn
            if isinstance(grpCol,strTypes):
                #try to map using E
                lg = self.normalizeName(grpCol)
                lgv = names.index(lg)
                if lgv<0:
                    raise ValueError('groupingColumn, %r, not found in header\nnames %r' % (lg,names))
                for i,(c,v) in enumerate(E):
                    if lgv==v:
                        break
                else:
                    #we didn't find it so add to E
                    E.append((lg,lgv))
            elif isinstance(grpCol,int):
                if not (0<=grpCol<len(E)):
                    raise ValueError('groupingColumn, %r, is invalid' % grpCol)
            elif self.groupingColumn is not None:
                raise ValueError('groupingColumn, %r, is invalid' % grpCol)
            self.makeNameMap([x[0] for x in E])

        self._na = list(map(str.lower,self.na))+['']

        lineNo = 1
        rows = []
        for line in lines:
            if self.fast:
                _f = line.split(self.sep)
            else:
                _f = _processLine(line,self.sep)
            lineNo += 1
            row = []

            if sql:
                for c,j in E:
                    if isinstance(j,int):
                        if j<len(_f):
                            v = self._convertField(_f[j],c,lineNo)
                        else:
                            v = None
                    else:
                        try:
                            v = eval(j,locals(),globals())
                            if v is self._arithNone: v = None
                        except:
                            raise ValueError("Can't evaluate %s in %s line %d" % (c,self.filename,lineNo))
                    row.append(v)
            else:
                cols = self.columnCount
                if cols is None:
                    cols = getattr(self,'_names',None)
                    if cols: cols = len(cols)
                    else: cols = len(_f)
                    self.columnCount = cols
                else:
                    assert len(_f) <= cols, "Incorrect number of fields at line %d in %s" % (lineNo, self.filename)
                    # we can have missing columns on the right, and they get padded with empty strings
                    while len(_f) < cols: _f.append('')
                for j in range(cols):
                    row.append(self._convertField(_f[j],j,lineNo))

            rows.append(row)

        self._data = rows
        del self._na

    def _checkCSVColumnNames(self,aName,names):
        A = getattr(self,aName,None)
        if A is None: return
        _A = not isinstance(A,(list,tuple))
        if _A:
            A = [A,]
            fnc = None
        else:
            fnc = isinstance(A,list) and list or tuple
            A = list(A)
        for i in range(len(A)):
            a = A[i]
            if not isinstance(a,strTypes):
                raise ValueError("%s instance has sql, but attribute %s contains non-string %r" % (self.__class__.__name__,aName,a))
            A[i] = a = self.normalizeName(a)
            if a not in names:
                raise ValueError("%s instance has sql, but attribute %s contains %r not in column names\n%r" % (self.__class__.__name__,aName,a,names))
        if fnc: A = fnc(A)
        else: A = A[0]
        setattr(self,aName,A)

    def _exConvertField(self,f,j,x,n):
        if j>=len(f): return self._arithNone
        r = self._convertField(f[j],x,n)
        if r is None: return self._arithNone
        return r

    def _convertField(self,f,x,n):
        try:
            typ = 'str'
            #accept nulls
            if f.lower() in self._na:
                no_na_dates = self.no_na_dates
                if no_na_dates and x in self.dateColumns and _checkIn(x,no_na_dates):
                    raise ValueError('Bad date field')
                return None
            elif x in self.integerColumns:
                typ = 'int'
                return int(f)
            elif x in self.floatColumns:
                typ = 'float'
                try:
                    value = float(f)
                except ValueError:
                    #try removing special characters flagged
                    for ch in self.floatIgnoreChars:
                        f = f.replace(ch, '')
                    value = float(f)
                return value
            elif x in self.dateColumns:
                typ = 'date'
                return (self.dateParser or self.parseDate)(f)
            else:
                return f
        except:
            import traceback
            traceback.print_exc()
            raise ValueError("Bad field at line %d field %s, expected %s: '%s'" % (n, str(x), typ, f))

class CSVReader:
    def __init__(self,filename,lineEndings=['\r\n','\r','\n\r']):
        self.filename = filename
        self.lineEndings = lineEndings

    def readlines(self):
        filename = self.filename
        data = (hasattr(filename,'read') and filename or open(filename,'rb')).read()
        for le in self.lineEndings:
            data = data.replace(le,'\n')
        return data.split('\n')

if __name__=='__main__':
    from reportlab.lib.utils import getStringIO
    f = getStringIO('''chartId\tFundId\tReturn\tVolatility
119\t1\t0.303739275\t0.045788029
119\t2\t0.340259329\t0.056684527
119\t3\t0.244538056\t0.044776268
119\t4\t0.379326509\t0.05526936
119\t5\t0.269164078\t0.048254073
120\t1\t0.212006856\t0.045515668
120\t2\t0.404000212\t0.049965404
120\t3\t0.416953391\t0.050843349
120\t4\t0.451333469\t0.040626584
666\t1\t0.417259534\t0.051285696
666\t2\t0.21576762\t0.047812899
666\t3\t0.420633734\t0.040486482
666\t4\t0.22950049\t0.059180818
666\t5\t0.485586939\t0.047515184
''')
    dm = CSVDataMaker(
                    filename=f,
                    sep='\t',
                    integerColumns=['chartId'],
                    floatColumns=['Return','Volatility'],
                    sql='SELECT chartId, 100*Return, 100*Volatility FROM scatterplot_data',
                    groupingColumn=0,
                    )
    dm.connect()
    r = 0
    while 1:
        fetched = dm.fetchNextDataSet()
        if not fetched: break
        r = r+1
        print('Dataset',r)
        for d in fetched:
            print(d)
