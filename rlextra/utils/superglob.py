#superglob - attempt at an Ant-like glob
"""
This is an attempt at the glob function in Ant, with ** patterns.

This is like the normal glob, except that ** matches any
number of directories.  This provides a very concise, elegant
way to describe recursive searches, includes and excludes.
There are numerous systems around like the Distutils FileList
and ReportLab's own 'action list' processor to build up
a set of files by using inclde and exclude patterns. These
generally have various flags and options like 'recursive'
to modify how the pattern is applied.  With a "superglob"
this can often be omitted and the patterns themselves
can express what is wanted.

**/*
  will find all files under the current location,
  however far down.

**/CVS/*
  matches all CVS directories and files, however far down

"/home/apps/**/*.pyc"
  matches all pyc files under apps

"""
from __future__ import print_function
import os
import glob
import shutil
import time
from pprint import pprint as pp

def has_two_stars(s):
    "Our special pattern in addition to the new glob"
    return s.find('**') != -1

def findSubDirs(path):
    "Return all subdirectories under path"
    def visit(arg, dirName, filenames):
        arg.append(dirName)
    subDirs = []
    os.path.walk(path, visit, subDirs)
    #chop off any stuff on the front including a leading separator
    return list(map(lambda x,n=len(path)+1: x[n:], subDirs))

def componentize(path):
    "Break a path into a list of components"
    components = []
    #allow for windows
    drive, path = os.path.splitdrive(path)
    #print 'drive=%s, path=%s' % (drive, path)
    left, right = os.path.split(path)
    components.append(right)
    #the terminal case could be nothing or a path separator
    while left not in ['','/','\\',':']:
        #print 'left=',left, 'components=', components
        left, right = os.path.split(left)
        components.append(right)
    if drive:
        components.append(drive)
    components.reverse()
    return components

def superGlob(pattern, verbose=0):
    "Return a list of paths matching a pattern"

    # break it into a list of directory components.
    drive, notDrive = os.path.splitdrive(pattern)
    directories, tail = os.path.split(notDrive)
    if directories:
        components = componentize(directories)
    else:
        components = [os.curdir]
    absolute = (pattern == os.path.abspath(pattern))
    if verbose:
        print('absolute=%d, drive=%s, directories=%s, tail=%s' % (absolute, drive, directories, tail))

    # deal with the first stage explicitly, when there
    # are no candidates yet.
    comp = components[0]
    components = components[1:]
    if absolute:
        if drive:
            start = drive + os.sep
        else:
            start = os.sep
    else:
        start = os.getcwd()


    if comp == '**':
        if verbose: print('top level: trying ** on %s' % start)
        dirs = findSubDirs(start)
    elif glob.has_magic(comp):
        if verbose: print('top level: trying magic')
        found = glob.glob(comp)
        dirs = []
        for dirname in found:
            if os.path.isdir(dirname):
                dirs.append(dirname)
    else:
        if verbose: print('top level: trying static')

        #static directory
        if absolute:
            newDir = drive + os.sep + comp
            if verbose: print('trying %s' % newDir)
            if os.path.isdir(newDir):
                dirs = [newDir]
            else:
                dirs = []
        else:
            if os.path.isdir(comp):
                dirs = [comp]
            else:
                dirs = []

    if verbose:
        print('initial candidate list:')
        pp(dirs)
        print()
    if dirs == []:
        #  no possible match at the outset, bail out
        return []
    candidateDirs = dirs

    #'step into' the pattern one directory or
    #directory pattern at the time.  Then prune
    #the list of candidates to files or directories which
    #exist.
    for component in components:
        if verbose: print('handling component ' + component +': ', end=' ')
        newCandidates = []

        if component == '**':
            if verbose: print('** pattern')
            for cand in candidateDirs:
                if verbose: print('trying %s' % cand)
                subDirs = findSubDirs(cand)
                if verbose: print('found subDirs', subDirs)
                for subDir in subDirs:
                    combined = os.path.join(cand, subDir)
                    newCandidates.append(combined)
        elif glob.has_magic(component):
            #glob pattern. glob filter to
            # what exists.
            if verbose: print('glob')
            for cand in candidateDirs:
                found = glob.glob(os.path.join(cand, component))
                for thing in found:
                    if os.path.isdir(thing):
                        newCandidates.append(thing)
        else:
            #static directory
            if verbose: print('static')
            if candidateDirs == []:
                newDir = component
                if os.path.isdir(newDir):
                    newCandidates.append(newDir)
            else:
                for cand in candidateDirs:
                    newDir = os.path.join(cand, component)
                    if os.path.isdir(newDir):
                        newCandidates.append(newDir)

        if verbose:
            print('%d candidates after scanning "%s":' % (len(newCandidates), component))
            pp(newCandidates)
        candidateDirs = newCandidates
        if candidateDirs == []:
            #no further matching possible
            return []

    # now the final stage - search for files in all the candidate
    # directories
    candidateFiles = []
    if glob.has_magic(tail):
        for candDir in candidateDirs:
            found = glob.glob(os.path.join(candDir, tail))
            for filename in found:
                #only want files not directories
                if os.path.isfile(filename):
                    candidateFiles.append(filename)
    else:
        for dirname in candidateDirs:
            fileName = os.path.join(dirname, tail)
            if os.path.isfile(fileName):
                candidateFiles.append(fileName)

    if not directories:
        # Strip off '.' if we added it earlier
        n = len(os.curdir + os.sep) 
        candidateFiles = [f[n:] for f in candidateFiles]
    return candidateFiles

class FileSet:
    "Makes it easy to build collections of files"
    def __init__(self, baseDir):
        self.baseDir = baseDir
        self._patterns = []
        self._fileNames = []
        self.verbose = 0
        self.scan = self._scanned 

    def _add(self,pattern,found):
        for fn in superGlob(pattern):
            found[fn] = 1

    def _sub(self,pattern,found):
        for fn in superGlob(pattern):
            if fn in found:
                del found[fn]

    def include(self, *patterns):
        self._add_patterns(self._add,*patterns)

    def exclude(self, *patterns):
        self._add_patterns(self._sub,*patterns)

    def _add_patterns(self,action,*patterns):
        if not patterns: return
        self.scan = self._scan
        self._filenames = []
        list(map(self._patterns.append,list(zip(patterns,len(patterns)*[action]))))

    def _scanned(self):
        pass

    def _scan(self):
        "Find what matches"
        cwd = os.path.abspath(os.getcwd())
        os.chdir(self.baseDir)
        try:
            # use a dictionary for fast deletion of candidates
            found = {}
            for pattern,func in self._patterns:
                func(pattern,found)
            self._fileNames = list(found.keys())
            self._fileNames.sort()
            self.scan = self._scanned
        finally:
            os.chdir(cwd)

    def getFileNames(self,abs=0):
        self.scan()
        if not abs: return self._fileNames
        return list(map(lambda x,join=os.path.join, base=self.baseDir: join(base,x), self._fileNames))

    def copyFiles(self, toDir):
        "Copy all of them to toDir"
        # to do: must be workable for absolute and relative paths
        cwd = os.path.abspath(os.getcwd())
        os.chdir(self.baseDir)
        try:
            if self.verbose:
                count = 0
                started = time.clock()
            for item in self.getFileNames():
                dirname, filename = os.path.split(item)
                destDir = os.path.join(toDir, dirname)
                if not os.path.isdir(destDir):
                    os.makedirs(destDir)
                destFile = os.path.join(destDir, filename)
                shutil.copy2(item, destFile)
                if self.verbose:
                    count = count + 1
                    if self.verbose>1: print('\t\tcopied %s' % destFile)
            if self.verbose: print('\tcopied %d files in %0.2f seconds\n' % (count, time.clock()-started))
        finally:
            os.chdir(cwd)

class SuperFileSet:
    def __init__(self,fsList=[]):
        if type(fsList) is not type([]):
            if type(fsList) is type(()): fsList = list(fsList)
            else: fsList = [fsList]
        self.fsList = fsList

    def append(self,fs):
        self.fsList.append(fs)

    def scan(self):
        for fs in self.fsList: fs.scan()

    def baseDir(self):
        return [x.baseDir for x in self.fsList]
    baseDir = property(baseDir)

    def copyFiles(self,toDir):
        L = self.fsList[:]
        L.reverse()
        for fs in L: fs.copyFiles(toDir)

    def include(self, *pattern):
        for fs in self.fsList: fs.include(*pattern)

    def exclude(self, *pattern):
        for fs in self.fsList: fs.exclude(*pattern)

    def getFileNames(self,abs=0):
        L = {}
        for fs in self.fsList:
            for fn in fs.getFileNames(abs=abs):
                L[fn] = None
        L = list(L.keys())
        L.sort()
        return L

if __name__=='__main__':
    import sys
    args = sys.argv[1:]
    if '-v' in args:
        args.remove('-v')
        verbose = 1
    else:
        verbose = 0
    if len(args) != 1:
        print('usage: superglob.py [-v] pattern')
    else:
        pattern = args[0]
        print('superGlob searching pattern: ' + pattern)
        started = time.clock()
        found = superGlob(pattern, verbose)
        finished = time.clock()
        print()
        for filename in found:
            print('   ' + filename)
        print()
        print('%d files found in %0.4f seconds' % (len(found), finished - started))
