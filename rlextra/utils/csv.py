#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'

def _processLine(line, sep=',', conv=0):
    fields = []
    p = 0
    ll = len(line)
    ls = len(sep)
    line = line + ' '
    while (ll > 0 and (line[ll-1] in ' \012\015')): ll = ll-1

    while p < ll:
        #Skip unquoted space at the start of a field
        while p<ll and line[p]==" ": p = p + 1

        field = ""
        ql = 0
        while p < ll:
            #Skip unquoted space at the end of a field
            if ql == 0 and line[p] == " ":
                q = p
                while q < ll and line[q] == " ":
                    q = q + 1
                if q >= ll:
                    break
                elif line[q : q + ls] == sep:
                    p = q
            if ql == 0 and line[p : p + ls] == sep:
                break
            elif line[p] == '"':
                if ql == 0:
                    ql = 1
                elif line[p+1]=='"':
                    field = field+'"'
                    p = p + 1
                else:
                    ql = 0
            else:
                field = field + line[p]
            p = p + 1
        p = p + ls
        if conv:
            try:
                fields.append(int(field))
            except ValueError:
                try:
                    fields.append(float(field))
                except ValueError:
                    fields.append(field)
        else:
            fields.append(field)
    if line[ll-ls:ll]==sep:
        fields.append('')   #extra field when there's a separator at the end

    return fields

def read(fn,sep=',',conv=0):
    '''
    read the csv file fn and return the fields as a list of lists.
    sep is the separator to use and conv determines whether an attempt is made to convert
    numeric fields.
    '''
    from reportlab.lib.utils import open_for_read
    f = open_for_read(fn,'t')

    F = []
    for l in f.readlines():
        F.append(_processLine(l,sep,conv))

    if f is not fn: f.close()
    return F

class RowWrapper:
    def __init__(self,names,data):
        self.__dict__['_RowWrapper__names'] = names
        self.__dict__['_RowWrapper__data'] = data
    def __getattr__(self,a):
        return self.__data[self.__names[a]]
    def __setattr__(self,a,v):
        self.__data[self.__names[a]] = v
    def __getitem__(self,i):
        return self.__data[i]
    def __setitem__(self,i,v):
        self.__data[i] = v

class CSVWrapper:
    __wrapper = RowWrapper
    def __init__(self, rawNames, aNames, hdrRow, datarows):
        names = {}
        for i,n in enumerate(rawNames):
            try:
                names[aNames[i]] = hdrRow.index(n)
            except:
                raise ValueError('Cannot locate expected column header "%s"' % n)
        self.__names = names
        self.__rows = [self.__wrapper(names,row) for row in datarows]

    def __getitem__(self,i):
        return self.__rows[i]

    def __setitem__(self,i,v):
        if not isinstance(v,self.__wrapper): v = self.__wrapper(self.__names,v)
        self.__rows[i] = v

def modifyCSV(f,L):
    return list(map(lambda x,f=f:list(map(f,x)),L[:]))

def modifyCSVRows(f,L,R=[]):
    L=L[:]
    for r in R:
        L[r] = list(map(f,L[r]))
    return L

def modifyCSVCols(f,L,C):
    L=L[:]
    if C:
        for r in range(len(L)):
            for c in C:
                L[r][c] = f(L[r][c])
    return L

if __name__ == '__main__':
    from reportlab.lib.utils import getStringIO
    L=read(getStringIO('"abc""d,ef""ghi",23,34\n1,2,3\na,4,5\n6,c,d\n'))
    print('originally',L)
    def f(x):
        try:
            x = int(x)
        except:
            pass
        return x

    print('modifyCSV',modifyCSV(f,L))
    print('modifyCSVRows([1,3])',modifyCSVRows(f,L,[1,3]))
    print('modifyCSVCols([0,2])',modifyCSVCols(f,L,[0,2]))
