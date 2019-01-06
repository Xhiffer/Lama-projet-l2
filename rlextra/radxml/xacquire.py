"""XML Data Acquisition Languagelet.

Basic data acquisition tasks which could be done with Python
scriptlets are provided as XML tags.

"""
try:
    import urllib.request
    urllib_urlopen = urllib.request.urlopen
except ImportError:
    import urllib
    urllib_urlopen = urllib.urlopen

from rlextra.radxml.xmlutils import TagWrapper
from reportlab.lib.rparsexml import parsexml

class DataFetcher:
    def __init__(self, **kw):
        self.name = None
        self.assignTo = None
        self.children = []
        for key, value in list(kw.items()):
            setattr(self, key, value)

    def getData(self):
        "Override this to retrieve the data"
        return None

    def fetch(self, nameSpace):
        "This is called by external environment"
        data = self.getData()
        if self.assignTo:
            parent = nameSpace[self.assignTo]
            setattr(parent, self.name, data)
        else:
            nameSpace[self.name] = data


class XmlDataFetcher(DataFetcher):
    "Read xml file from a file or url"
    #needs support for dtdDir etc.
    def getData(self):
        if hasattr(self, 'url'):
            xmlText = urllib_urlopen(self.url).read()
        elif hasattr(self, 'fileName'):
            xmlText = open(self.fileName,'rb').read()
        elif type(self.children[0]) is type(''):
            xmlText = self.children[0]
        else:
            raise ValueError("xml tag must have a 'fileName' or 'url' attribute")
        tree = parsexml(xmlText)
        wrapped = TagWrapper(tree)
        return wrapped

tagMap = {'xmlData':XmlDataFetcher}

def acquireData(nodeList, nameSpace):
    """Convert nodelist to relevant fetchers and get data"""
    for elem in nodeList:
        if isinstance(elem,tuple):
            (tagName, attrs, children, stuff) = elem
            klass = tagMap[tagName]
            obj = klass(**attrs)
            obj.children = children
            obj.fetch(nameSpace)

        
