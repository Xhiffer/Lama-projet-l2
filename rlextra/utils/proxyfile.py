class ProxyFile:
    def __init__(self,file=None):
        self._L = []
        self._aL = self._L.append
        self._file = file
        self.hidden = 0

    def getValue(self):
        return ''.join(self._L)

    def flush(self): pass

    def really_flush(self):
        self._file.write(self.getValue())
        del self._L[:]

    def mark(self):
        return len(self._L)

    def write(self,s):
        if not self.hidden: self._aL(s)

    def pop(self,mark):
        L = self._L[mark:]
        if L: del self._L[mark:]
        return L

    def close(self):
        self.really_flush()
        del self._L, self._file, self._aL, self.hidden

class Stdout(ProxyFile):
    import sys
    def __init__(self):
        ProxyFile.__init__(self,self.sys.stdout)
        self._ostdout = self.sys.stdout
        self._ostderr = self.sys.stderr
        self.sys.stdout = self.sys.stderr = self

    def close(self):
        self.really_flush()
        self.restore()

    def restore(self):
        self.sys.stdout = self._ostdout
        self.sys.stderr = self._ostderr

#deletes its content when read
class MemFile:
    def __init__(self, value):
        self._value = value
    def read(self):
        value = self._value
        del self._value
        return value
    def write(self, value):
        self._value += value

if __name__=='__main__':
    stdout = Stdout()
    print('Hello World')
    print('Hello World Again')
    stdout.hidden = 1
    print('This should not appear')
    stdout.hidden = 0
    print('Hello World A Third Time')
    stdout.really_flush()
    stdout.close()
    print('This is normal printing')
