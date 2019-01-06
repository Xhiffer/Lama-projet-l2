#copyright ReportLab Europe Limited. 2000-2016
from os.path import splitext, isfile, abspath, isdir, normpath, basename
from fnmatch import fnmatch
import os, sys, time, string
try:
    from hashlib import md5
except ImportError:
    from md5 import md5

class FilenameClassifier:
    '''provides simple text/binary filename classification services'''
    txt_exts = [".afm", ".py", ".prep", ".rml", ".xml", ".html", ".txt", ".dtd", ".h", ".c", ".iss", '.js', '.css', '.pas']
    txt_filenames = ['readme*','changes*']

    def getTextExtensions(self):
        "file extensions for this pp which should be treated as ascii"
        return self.txt_exts

    def hasTextFileName(self,filename):
        fn = basename(filename)
        for pat in self.txt_filenames:
            if fnmatch(fn,pat): return 1
        return 0

    def isTextFile(self, filename):
        return (self.hasTextFileName(filename) or splitext(filename)[1] in self.getTextExtensions())

    def isBinaryFile(self, filename):
        return not self.isTextFile(filename)

    def mode(self,filename):
        '''return mode character b or t'''
        return ('b','t')[self.isTextFile(filename)]

class Manifester(FilenameClassifier):
    '''Mix in class providing some standard methods for dealing with manifests'''

    def __init__(self,dirname=None,id='',verbose=0):
        self.id = id
        self.verbose = verbose
        if dirname:
            assert isdir(dirname), "Directory %s not found!" % dirname
        else:
            dirname = os.getcwd()
        self.baseDir = normpath(abspath(dirname))
        if self.verbose: print('running in directory %s' % self.baseDir)
        self.resetDir()

    def resetDir(self):
        "Returns current directory to my base"
        os.chdir(self.baseDir)

    def getMachineInfo(self):
        "Something to identify machine"
        import socket
        return socket.gethostname()

    if sys.hexversion >= 0x02000000:
        def _digester(self,s):
            return md5(s).hexdigest()
    else:
            # hexdigest not available in 1.5
        def _digester(self,s):
            return ''.join(["%02x" % ord(x) for x in md5(s).digest()])

    def _clean(self,data):
        data = data.replace('\r','')
        data = data.replace('\n','')
        return data

    def getTextFileChecksum(self, filename, _id=0):
        "checksum which is robust against line ending problems"
        txt = self._clean(open(filename).read())
        r = self._digester(txt)
        if _id:
            L = string.split(txt)
            for h in  ('#$'+'Header:', '$'+'Header:', '$'+'Id:', '#$'+'Id:', '/*$'+'Id:', '/*$'+'Header:'):
                try:
                    i = L.index(h)
                    return r + ('\t# %s %s %s' % (L[i+2],L[i+3],L[i+4]))
                except (IndexError, ValueError):
                    pass
        return r

    def getBinaryFileChecksum(self, filename):
        "ordinary checksum for all file contents"
        return self._digester(open(filename, 'rb').read())

    def getFileChecksum(self, filename, _id=0):
        "returns unique fingerprint for this file"
        if self.isTextFile(filename):
            return self.getTextFileChecksum(filename,_id=_id)
        else:
            return self.getBinaryFileChecksum(filename)

    def writeSignedManifest(self,fList,mName,_id=0,verbose=None):
        if verbose is None: verbose = getattr(self,'verbose')
        self.resetDir()
        L = ['#signed %s for %s in %s generated on %s at %s' % (mName, self.id, self.baseDir,
                            self.getMachineInfo(), time.ctime(time.time()))]
        M = []
        for f in fList:
            if not isfile(f):
                M.append(f)
                if verbose>1: print('not computing checksum for missing', f)
            else:
                if verbose>1: print('computing checksum for', f)
                L.append('%s\t%s' % (f, self.getFileChecksum(f,_id=_id)))
        L.append('%s\t%s' % (mName, self._digester(string.join(L,''))))
        open(mName,'w').write(string.join(L,'\n'))
        if verbose: print('wrote '+mName)
        assert not M, "Missing files %s" % M

    def stripComments(self, list_of_strings):
        "Removes blank lines and anything after a hash comment"
        entries = []
        for line in list_of_strings:
            beforeComment = line.split('#')[0].strip()
            if beforeComment:
                entries.append(beforeComment)
        return entries

    def _getSignedManifest(self,mName):
        '''return a line ending normalised list of lines'''
        self.resetDir()
        try:
            L = string.replace(open(mName,'rb').read(),'\r\n','\n')
            L = [_f for _f in string.split(string.replace(L,'\r','\n'),'\n') if _f]
        except:
            L = None
        return L

    def verifySignedManifest(self,mName,verbose=None):
        """Reads and checks against a signed manifest.  Returns
        3-tuple of (pass/fail, failed files, missing files)"""
        if verbose is None: verbose = getattr(self,'verbose')
        L = self._getSignedManifest(mName)
        if L:
            L0 = L[0]
            n = len(L)
        else:
            n = 0
        failed = []
        missing = []
        if not n:
            if verbose: print((L is None and 'File %s missing or invalid'   or  'File %s empty') % mName)
        else:
            # check the bottom row, a checksum for the manifest itself
            l = L[-1]
            L = L[1:-1]
            if l:
                l = self.stripComments([l])[0]
                (f, csum) = l.split()
                ok = self._digester(string.join([L0]+L,''))==csum
            else:
                ok = 0
            L = self.stripComments(L)
            if not ok:
                failed = [f]
                if verbose: print('%s failed!\nAbandoning checks for other files.' % f)
                for l in L:
                    (f, csum) = l.split()
                    failed.append(f)
            else:
                for l in L:
                    (f, csum) = l.split()
                    if isfile(f):
                        if self.getFileChecksum(f)!=csum:
                            failed.append(f)
                            if verbose>1: print('%s failed' % f)
                    else:
                        missing.append(f)
                        if verbose > 1: print('%s missing' % f)

        if verbose: print('%d files verified, %d failed, %d missing' % (n - len(failed) - len(missing), len(failed), len(missing)))
        return ((n>0 and failed==[] and missing==[]), failed, missing)

if __name__=='__main__': #noruntest
    for fn in sys.argv[1:]:
        Manifester().verifySignedManifest(fn,verbose=1)
