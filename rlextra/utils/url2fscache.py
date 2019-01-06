#copyright ReportLab Inc. 2000-2016
__version__='3.3.0'
__all__=('URL2FSCacheKey','URL2FSCacheValue','URLValue','URL2FSCache',
        )
#generic url cacher
try:
    import urllib.request, urllib.error
    urllib_Request = urllib.request.Request
    urllib_urlopen = urllib.request.urlopen
    urllib_HTTPError = urllib.error.HTTPError
    del urllib.request, urllib.error
except ImportError:
    import urllib2
    urllib_Request = urllib2.Request
    urllib_urlopen = urllib2.urlopen
    urllib_HTTPError = urllib2.HTTPError
    del urllib2
    
import os, time, zlib
from reportlab.lib.utils import pickle
class URL2FSCacheKey(tuple):
    for i,x in enumerate("url".split()):
        exec("%s=property(lambda self: self[%d])" % (x,i))

class URL2FSCacheValue(tuple):
    for i,x in enumerate("path lastmod etag lastfetch".split()):
        exec("%s=property(lambda self: self[%d])" % (x,i))

class URLValue(str):
    def __new__(cls,value,info=None):
        self = str.__new__(cls,value)
        self._info = info
        return self

def recentLocalFile(path,tooOld=None):
    '''return True for files that exists and are less than tooOld'''
    return path and os.path.isfile(path) and tooOld is not None and os.stat(path)[8]<tooOld

class URL2FSCache:
    def __init__(self,path):
        self._lastfetch = 0
        self._path = path
        self.readCache()

    def readCache(self):
        try:
            cache = pickle.loads(zlib.decompress(open(self._path,'rb').read()))
            #print '_readCache', self._path, cache
        except:
            cache = {}
        self._cache = cache

    def writeCache(self):
        open(self._path,'wb').write(zlib.compress(pickle.dumps(self._cache)))
        #print 'writeCache',self._path, self._cache

    def readText(self,url,msgFunc=None):
        v = self._cache[url]
        f = open(v.path,'rb')
        text = f.read()
        now = time.time()
        f.close()
        self._cache[url] = URL2FSCacheValue(v[:3]+(now,))
        if msgFunc: msgFunc(' '.join(('cached',url,v.path)))
        return URLValue(text,'cached')

    def fetch(self, url, path, force=1, delay=0, msgFunc=None, tooOld=None):
        cache = self._cache
        req = urllib_Request(url)
        v = cache.get(url,None)
        if v and recentLocalFile(v.path,tooOld):
            if not force:
                return self.readText(url)

            v = cache[url]
            if v.etag: req.add_header('If-None-Match',v.etag)
            if v.lastmod: req.add_header('If-Modified-Since',v.lastmod)
            try:
                if delay>0: time.sleep(delay)
                res = urllib_urlopen(req)
            except urllib_HTTPError as e:
                if '304' not in str(e): raise
                #unchanged
                print('unchanged')
                return self.readText(url,msgFunc)
            if msgFunc: msgFunc(' '.join(('fresh',url)))
            self.delete(url)
        else:
            self.delete(url)
            if delay>0: time.sleep(delay)
            res = urllib_urlopen(req)
            if msgFunc: msgFunc(' '.join(('new',url)))
        text = res.read()
        if path: self.writeText(text,path,msgFunc)
        get = res.headers.dict.get
        now = time.time()
        cache[url] = URL2FSCacheValue((path,get('last-modified'),get('etag'),now))
        return URLValue(text,'fresh')

    def __getitem__(self,url):
        return self._cache[url]

    @staticmethod
    def writeText(text,path,msgFunc=None):
        dir = os.path.dirname(path)
        try:
            os.makedirs(dir)
        except:
            pass
        f = open(path,'wb')
        f.write(text)
        f.close()
        if msgFunc: msgFunc(' '.join(('wrote',path,'length',str(len(text)))))

    def setPath(self,url,path):
        v = self._cache[url]
        self._cache[url] = URL2FSCacheValue((path,)+v[1:])

    def delete(self,url):
        try:
            v = self._cache[url]
            if v.path:
                try:
                    os.remove(v.path)
                except OSError:
                    pass
            del self._cache[url]
        except KeyError:
            pass

def test():
    u=URL2FSCache('mycache.zpckl')
    print(u.fetch('http://svn.reportlab.com/testa/a.txt','testa/a.txt'))
    print(u.fetch('http://svn.reportlab.com/testb/b.txt','testb/b.txt'))
    u.writeCache()

if __name__=='__main__':
    test()
