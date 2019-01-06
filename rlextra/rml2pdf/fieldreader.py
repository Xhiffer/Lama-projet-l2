#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__='3.3.0'
__all__=['FieldReader','XMLTreeGetter']
from .rml2pdf import readLength
from reportlab.lib.rl_accel import fp_str
def _defaultDataGetter(name, intent=None):
    return '''<!-- unknown data for field %s -->''' % name

def strStrip(s):
    return s.strip()

def _gridPrint(x, text, eps=1E-6):
    """Useful for writing unit tests that fail if alignment is out.

    Always assume a grid of box width 1.0 units "without loss of generality" (I hope :-).

    >>> _gridPrint(0.0, 'spam')
    spam
    >>> _gridPrint(1.0, 'spam')
     spam
    >>> _gridPrint(1.01, 'spam')  # misaligned --> prints nothing
    >>> _gridPrint(1.00000001, 'spam')  # inside tolerance
     spam

    """
    d, r = divmod(abs(x), 1.0)
    if 0. <= r < eps:
        print(' '*int(d)+text)

def _percentageInSmallBox(content, x, boxWidth, omitDecimalPoint=False):
    """Format a number for printing over pre-printed letterboxes on a form.

    content is a floating point number, or an object that yields one when
    passed to float().

    x is the x co-ordinate of LHS of the rightmost box.

    This function assumes there's no decimal point pre-printed, and we're
    trying to cram as much as possible into a small number of boxes, so we
    don't much care where the decimal point goes.  Also, since we're printing a
    percentage, we can truncate trailing zeroes.

    >>> def amt(content, x, omitDecimalPoint=False):
    ...     x, text, dpIndex = _percentageInSmallBox(content, x, boxWidth=1.0,
    ...                                              omitDecimalPoint=omitDecimalPoint)
    ...     _gridPrint(x, text)
    ...     if omitDecimalPoint:
    ...         print 'decimal point at:', dpIndex

    >>> amt('1.5', 2)
    1.5
    >>> amt('0.25', 4)
     0.25
    >>> amt('0.375', 4)
    0.375
    >>> amt('1.5', 4)
      1.5
    >>> amt('1.52', 4)
     1.52
    >>> amt('7.75', 4)
     7.75
    >>> amt('10.55', 4)
    10.55
    >>> amt('1.0', 4)
       1.
    >>> amt('1', 4)
       1.
    >>> amt('10', 4)
      10.

    We don't bother with more than 3 decimal places.

    >>> amt('1.5678', 4)
    1.568


    Everything again, this time without a decimal point taking up a whole box
    (instead, the function returns an x position at which to print the decimal
    point).  The x position returned is that needed if using the letterBoxes
    RML tag.

    >>> amt('1.5', 2, omitDecimalPoint=True)
     15
    decimal point at: 1.5
    >>> amt('0.25', 4, omitDecimalPoint=True)
      025
    decimal point at: 2.5
    >>> amt('0.375', 4, omitDecimalPoint=True)
     0375
    decimal point at: 1.5
    >>> amt('1.5', 4, omitDecimalPoint=True)
       15
    decimal point at: 3.5
    >>> amt('1.52', 4, omitDecimalPoint=True)
      152
    decimal point at: 2.5
    >>> amt('7.75', 4, omitDecimalPoint=True)
      775
    decimal point at: 2.5
    >>> amt('10.55', 4, omitDecimalPoint=True)
     1055
    decimal point at: 2.5
    >>> amt('1.0', 4, omitDecimalPoint=True)
        1
    decimal point at: None

    >>> amt('1', 4, omitDecimalPoint=True)
        1
    decimal point at: None

    >>> amt('10', 4, omitDecimalPoint=True)
       10
    decimal point at: None

    >>> amt('1.5678', 4, omitDecimalPoint=True)
     1568
    decimal point at: 1.5


    Failure cases:

    >>> amt('', 0)
    Traceback (most recent call last):
    ValueError: empty string for float()
    >>> amt('nonsense', 0)
    Traceback (most recent call last):
    ValueError: invalid literal for float(): nonsense

    """
    content = float(content)
    text = ("%.3f" % content).rstrip('0')
    if omitDecimalPoint:
        dpIndex = text.find('.')
        if dpIndex >= 0:
            text = text[:dpIndex]+text[dpIndex+1:]
    x -= ((len(text) - 1) * boxWidth)
    if omitDecimalPoint:
        if dpIndex >= 0 and dpIndex == len(text):
            dpX = None
        else:
            dpX = x + (dpIndex-0.5)*boxWidth
    else:
        dpX = None
    return x, text, dpX

def _amount(content, x, boxWidth, nrDecimalPlaces=2):
    """Format a number for printing over printed letterboxes on a form.

    content is a floating point number, or an object that yields one when
    passed to float().

    x is the x co-ordinate of the LHS of the box of the first digit before
    (i.e. to the left of) the decimal point.

    This function assumes the form has a decimal point pre-printed, and
    that the decimal point takes up zero boxes.

    Define a function useful for testing: this won't print anything unless
    we've got the alignment correct (with an imaginary grid of box width 1).

    >>> def amt(content, x, nrDecimalPlaces):
    ...     x, text = _amount(content, x, boxWidth=1.0, nrDecimalPlaces=nrDecimalPlaces)
    ...     _gridPrint(x, text)

    >>> amt('1.5', 1.5, 2)  # supplied x is misaligned with unit grid

    Simple cases:

    >>> amt('1.5', 0, 2)
    150
    >>> amt('15', 1, 1)
    150
    >>> amt('1.52', 0, 2)
    152

    It shouldn't matter how big the number gets: the _amount doesn't know
    how far left the printed letterboxes go, so we can and it will run past
    the left edge of the printed letterboxes if necessary (better to do
    that than to truncate 1200 pounds to 200 pounds!):

     -------
    1|2|0|0|
     -------

    >>> amt('1.5', 2, 1)
      15
    >>> amt('15', 2, 1)
     150
    >>> amt('150', 2, 1)
    1500

    >>> amt('', 0, 2)
    Traceback (most recent call last):
    ValueError: empty string for float()
    >>> amt('nonsense', 0, 2)
    Traceback (most recent call last):
    ValueError: invalid literal for float(): nonsense

    """
    content = float(content)
    text = ('%%.%dd' % (nrDecimalPlaces+1)) % int(float(content)*10**nrDecimalPlaces)
    nrCharsToLeftOfDot = len(text) - nrDecimalPlaces
    x = x - (nrCharsToLeftOfDot-1)*boxWidth
    return x, text
    
def _amount2(content, nboxes, ndp=2, lPad=' '):
    """
    >>> _amount2('', 5)
    '     '
    >>> _amount2('five', 5)
    'ERR'
    >>> _amount2('1234.00', 5)
    'ERR'
    >>> _amount2(-3,1,0)
    'ERR'
    >>> _amount2('0.99', 5)
    '  099'
    >>> _amount2('.99', 2)
    '99'
    >>> _amount2('0', 3)
    '000'
    >>> _amount2('0', 1, 0)
    '0'
    >>> _amount2(-4,10)
    '      -400'
    """
    text = ''
    if content != '':
        try: float(content) 
        except: return 'ERR'
        if 0 <= float(content) < 1 and nboxes != ndp: zero = '0'
        else: zero = ''
        content = float(content)
        text = ('%s%%.%dd' % (zero,ndp)) % int(float(content)*10**ndp)
        if len(text) > nboxes: return 'ERR'
    text = lPad*(nboxes - len(text)) + text
    return text


class XMLTreeGetter:
    '''
    >>> from rlextra.radxml import xmlutils
    >>> T = xmlutils.xml2doctree('<a><b>bval</b><c ca="cattr"><d>dval</d></c></a>',0)
    >>> x = XMLTreeGetter(T,stripDots=1)
    >>> print x('a.b')
    bval
    >>> print x('a.c.d')
    dval
    >>> print x('a.c.ca')
    cattr
    '''
    def __init__(self,tree,stripDots=0,default='',prefix='',strip=lambda x: x):
        self.tree = tree
        self.stripDots = stripDots
        self.default = ''
        self.prefix = prefix
        self.strip = strip

    def getValue(self,name,intent=None):
        name = self.prefix+name
        A = name.split('.')
        if self.stripDots: A = A[self.stripDots:]
        obj = self.tree
        for a in A:
            obj = getattr(obj,a)
        return self.strip(str(obj))

    def __call__(self,name,intent=None):
        try:
            return self.getValue(name,intent)
        except:
            if self.default is not None: return self.default
            raise

class FieldsGetter:
    """Get a sequence of positioned Fields whose text comes from a single data field.

    You pass instances satisfying this interface (e.g. this class, or more
    usually a subclass, for convenience) to FieldReader.multiTextRml() -- see
    that docstring for what this stuff is for.

    Interface for FieldGetter instances:

    .setFieldMap() will be called with a mapping of field name to field
    objects.  The field objects have attributes as returned by dictFromRow().

    The instance will be called as a callable with field name and content
    and should return a list of Fields.

    The base class also provides an implementation.  The implementation assumes
    the (fixed number, nrParts, of) positioned field names to be used to are
    generated by appending integer indices to the name passed in when calling
    the instance, e.g. 'postcode' --> 'postcode1', 'postcode2'.  To split the
    data into chunks, it uses a normalization function and a separator
    character.

    """
    def __init__(self, normalize, nrParts, separator):
        self.nrParts = nrParts
        self.separator = separator
        self.normalize = normalize

    def setFieldMap(self, fieldFromName):
        self.fieldFromName = fieldFromName

    def __call__(self, name, content):
        content = self.normalize(content)
        parts = content.split(' ')
        assert len(parts) == self.nrParts
        fields = []
        for ii, part in enumerate(parts):
            partName = '%s%d' % (name, ii+1)
            field = self.fieldFromName[partName]
            field.content = part
            fields.append(field)
        return fields


class PostcodeFieldsGetter(FieldsGetter):
    def __init__(self):
        from rlextra.utils.layoututils import postcodeFormatter
        pcf = lambda t: postcodeFormatter(t, singleSpace=True)
        FieldsGetter.__init__(self, pcf, nrParts=2, separator=' ')


class DrawnField:
    # XXX class FieldStruct should probably go away and be replaced with this class

    def __init__(self, intentSpec):
        self._intentSpec = intentSpec

    def setAttrs(self, attrs):
        self._attrs = attrs

    def rml(self):
        content = self._attrs[self._intentSpec.valueName]
        return self._rml(self._intentSpec.tagName, self._attrs, content, self._intentSpec.attributeNames)

    def _rml(self, tagName, attrs, content, allowedAttrNames):
        rml = []
        add = rml.append
        tagAttrs = []
        aa = tagAttrs.append
        for k,v in list(attrs.items()):
            if k in allowedAttrNames:
                aa(' %s=%s' % (k,repr(str(v))))
        tagAttrs.sort()
        d = dict(tagName=tagName,tagAttrs=''.join(tagAttrs))
        if self._intentSpec.isEmpty:
            add('<%(tagName)s%(tagAttrs)s/>' % d)
        else:
            d['content'] = content
            add('<%(tagName)s%(tagAttrs)s>%(content)s</%(tagName)s>' % d)
        return ''.join(rml)


class PercentageDrawnField(DrawnField):

    def rml(self):
        rml = []
        rml.append(DrawnField.rml(self))
        decimalPointAttrs = self._attrs.copy()
        dpX = decimalPointAttrs['dpX']
        if dpX is not None:
            decimalPointAttrs['x'] = dpX
            decimalPointAttrs['count'] = 1
            rml.append(self._rml('letterBoxes', decimalPointAttrs, '\xc2\xb7', self._intentSpec.attributeNames))
        return ''.join(rml)


class IntentSpec:

    def __init__(self,intentName,tagName,valueName,attributeNames,isEmpty=False,preRenderFunc=None):
        self.intentName = intentName
        self.tagName = tagName
        self.valueName = valueName
        self.attributeNames = attributeNames
        self.isEmpty = isEmpty
        self.preRenderFunc = preRenderFunc

    def _createDrawnField(self, attrs):
        drawnFieldClass = {
            'percentage': PercentageDrawnField,
            }.get(self.intentName, DrawnField)
        df = drawnFieldClass(self)
        df.setAttrs(attrs)
        return df

    def rml(self, attrs):
        df = self._createDrawnField(attrs)
        return df.rml()


class FixBoolean:
    def __init__(self,name):
        self.name = name
    def __call__(self,D):
        value = D[self.name]
        if not value:
            D[self.name] = '0'

class FieldStruct:
    def __init__(self, pairs):
        self.__dict__.update(dict(pairs))
##     def __str__(self):
##         r = []
##         for kv in self.__dict__.items():
##             r.append('%s=%r' % kv)
##         return '<%s %s>' % (self.__class__, ', '.join(r))

FIELD_INFO_NAMES = ['name', 'pageNum', 'x', 'y', 'width', 'height', 'intent', 'count']

def dictFromRow(row):
    nkwds = {}
    for ii, name in enumerate(FIELD_INFO_NAMES):
        nkwds[name] = row[ii]
    nkwds['name'] = nkwds['name'].strip()
    return nkwds

def _convertListParam(L):
    L = list(map(float,L))
    return '|'.join(map(fp_str,L))

class FieldReader:
    '''
    >>> from StringIO import StringIO
    >>> csv=StringIO("""\
    ... name,pageNum,x,y,width,height,intent
    ... sippDetails.clientDetails.houseName,3,21.0,604.0,352.0,16.0,letterBoxes,10
    ... sippDetails.clientDetails.occupation,3,21.0,410.0,552.0,16.0,textBox,0
    ... sippDetails.clientDetails.isExistingClient,3,23.0,499.0,10.5,9.5,checkBox,0
    ... sippDetails.clientDetails.amount,3,20,100,30,10,amount,3
    ... sippDetails.clientDetails.percentage,3,20,100,10,10,percentage,1
    ... """)
    >>> F = FieldReader(csv)
    >>> print F.fieldRml('sippDetails.clientDetails.houseName',content='Hello World')
    <letterBoxes boxHeight='16.0' boxWidth='35.2' count='10' x='21.0' y='604.0'>Hello World</letterBoxes>
    >>> print F.fieldRml('sippDetails.clientDetails.occupation',content='Widget Grokker')
    <textBox boxHeight='16.0' boxWidth='552.0' x='21.0' y='410.0'>Widget Grokker</textBox>
    >>> print F.fieldRml('sippDetails.clientDetails.isExistingClient',checked="1")
    <checkBox boxHeight='9.5' boxWidth='10.5' checked='1' x='23.0' y='499.0'/>
    >>> print F.fieldRml('sippDetails.clientDetails.amount',content="123.454")
    <letterBoxes boxHeight='10' boxWidth='10.0' count='5' x='0.0' y='100'>12345</letterBoxes>
    >>> print F.fieldRml('sippDetails.clientDetails.amount',content="1234.56")
    <letterBoxes boxHeight='10' boxWidth='10.0' count='6' x='-10.0' y='100'>123456</letterBoxes>
    >>> print F.fieldRml('sippDetails.clientDetails.percentage',content="12.34")
    <letterBoxes boxHeight='10' boxWidth='10.0' count='4' x='-10.0' y='100'>1234</letterBoxes><letterBoxes boxHeight='10' boxWidth='10.0' count='1' x='5.0' y='100'>\xb7</letterBoxes>

    We can also use the xmltree as a value getter
    >>> csv.seek(0)
    >>> from rlextra.radxml import xmlutils
    >>> T=xmlutils.xml2doctree('<a><clientDetails houseName="The Willows" occupation="Builder"/></a>',0)
    >>> F=FieldReader(csv,XMLTreeGetter(T,stripDots=1))
    >>> print F.fieldRml('sippDetails.clientDetails.houseName')
    <letterBoxes boxHeight='16.0' boxWidth='35.2' count='10' x='21.0' y='604.0'>The Willows</letterBoxes>
    >>> print F.fieldRml('sippDetails.clientDetails.occupation')
    <textBox boxHeight='16.0' boxWidth='552.0' x='21.0' y='410.0'>Builder</textBox>

    playing with defaults
    >>> F.setDefaults(textBox=dict(textColor='red'))
    >>> print F.fieldRml('sippDetails.clientDetails.occupation')
    <textBox boxHeight='16.0' boxWidth='552.0' textColor='red' x='21.0' y='410.0'>Builder</textBox>
    >>> F.setDefaults(textBox=dict(textColor=None,shrinkToFit='1'))
    >>> print F.fieldRml('sippDetails.clientDetails.occupation')
    <textBox boxHeight='16.0' boxWidth='552.0' shrinkToFit='1' x='21.0' y='410.0'>Builder</textBox>
    '''
    uppercase = False
    def __init__(self,fileName,dataGetter=_defaultDataGetter,defaults={}):
        '''
        fileName        the .fld file
        dataGetter      a callable to get default content using the field name
        defaults        dict of dict of default values ie defaults[intent][attributeName]
                        will be used if set and not overriden
        '''
        self.fileName = fileName
        self.dataGetter = dataGetter
        self.FIELD_ROWS = self.readFields(fileName)
        self._defaults = {}
        self._defaults['letterBoxes'] = self._defaults['letterBox'] = {}    #hack aliasing
        self.supportedEntities = ['&amp;', '&gt;', '&lt;', '&quot;']  #these will not get uppercased when upercasing output
        self.setDefaults(**defaults)

    def setDefaults(self,**defaults):
        for intent,intentDefaults in list(defaults.items()):
            if intent not in self.intentSpecs:
                raise KeyError("Don't know about intent \"%s\"" % intent)
            spec = self.intentSpecs[intent]
            D = self._defaults.setdefault(intent,{})
            for kk,vv in list(intentDefaults.items()):
                if kk not in spec.attributeNames:
                    raise ValueError('Intent "%s" has no attribute named "%s"' % (intent,kk))
                if vv is None:
                    if kk in D: del D[kk]
                else:
                    D[kk] = vv

    def readFields(self,fileName):
        import csv
        from reportlab.lib.utils import open_for_read
        if hasattr(fileName,'read'):
            f=fileName
        else:
            f=open_for_read(fileName, "rb")
        ROWS=[list(map(str.strip,row)) for row in csv.reader(f)][1:]
        if f is not fileName: f.close()
        return ROWS

    def upper(self,content):
        content = content.upper()
        #now switch back any entities we just broke - &amp; is common in input and &AMP; is not XML!
        for ent in self.supportedEntities:
            entUp = ent.upper()
            if entUp in content:
                content = content.replace(entUp, ent)
        return content

    def _render(self,name,intent,dataGetter,**kwds):
        from xml.sax.saxutils import escape
        spec = self.intentSpecs[intent]
        valueName = spec.valueName
        D=self._defaults.get(intent,{}).copy()
        escapeAction=D.get('escape')
        D.update(kwds)
        if self.uppercase and 'content' in D and isinstance(D['content'],str):
            D['content'] = self.upper(D['content'])
        if valueName not in kwds:
            data = dataGetter(name, intent)
            if self.uppercase and isinstance(data,str):
                data = self.upper(data)
            if escapeAction == 'escape':
                data = escape(data)
            D[valueName] = data
        if spec.preRenderFunc: spec.preRenderFunc(D)
        rml = []
        add = rml.append
        if 'rotation' in D:
            angle = D['rotation']
            add('<saveState/><rotate degrees="%s"/>' % angle)
            angle = float(angle)
            from reportlab.graphics.shapes import rotate, inverse, transformPoint
            D['x'],D['y'] = transformPoint(inverse(rotate(float(angle))),(float(D['x']),float(D['y'])))
        add(spec.rml(D))
        if 'rotation' in D: add('<restoreState/>')
        return ''.join(rml)#+('<!--%s-->' % name)

    def _fieldRml(self,dataGetter,name,pageNum,width,height,intent,count,**kwds):
        if intent in ('letterBoxes','letterBox'):
            kwds['count']=count
            kwds.setdefault('boxWidth',str(readLength(width)/int(count)))
            kwds.setdefault('boxHeight',height)
        elif intent in ('checkBox','textBox'):
            kwds.setdefault('boxWidth',width)
            kwds.setdefault('boxHeight',height)
        elif intent=='amount':
            count = int(count)
            ndp = count - 1
            kwds.setdefault('boxHeight',height)
            boxWidth = float(kwds.setdefault('boxWidth',str(readLength(width)/count)))
            try:
                content = kwds['content']
            except:
                content = dataGetter(name)
            content=content.strip()
            if content == '': return ''
            x = readLength(kwds['x'])
            x, text = _amount(content, x, boxWidth, ndp)
            kwds['content'] = text
            kwds['x'] = str(x)
            kwds['count'] = len(text)
        elif intent=='amount2':
            kwds['count']=count
            kwds.setdefault('boxHeight',height)
            kwds.setdefault('boxWidth',str(readLength(width)/int(count)))
            try:
                content = kwds['content']
            except:
                content = dataGetter(name)
            content=content.strip()
            if content == '': return ''
            ndp = kwds.get('ndp',2)
            lPad = kwds.get('lPad',' ')
            kwds['content'] = _amount2(content, int(count), ndp, lPad)
        elif intent=='percentage':
            count = int(count)
            kwds.setdefault('boxHeight',height)
            boxWidth = float(kwds.setdefault('boxWidth',str(readLength(width)/count)))
            content = kwds['content']
            if content == '':
                return ''
            x = readLength(kwds['x'])
            x, text, dpX = _percentageInSmallBox(content, x, boxWidth, omitDecimalPoint=True)
            kwds['content'] = text
            kwds['x'] = str(x)
            kwds['count'] = len(text)
            kwds['dpX'] = dpX
        elif intent in ('multiBox','multiAmountBox'):
            try:
                content = kwds['content']
            except:
                content = dataGetter(name)
            if intent == 'multiAmountBox':
                ndp = kwds.get('ndp',2)
                lPad = kwds.get('lPad',' ')
                content = _amount2(content, int(count), ndp,lPad)
            kwds['content'] = content
            xl = kwds['x'].split('|')
            yl = kwds['y'].split('|')
            wl = width.split('|')
            hl = height.split('|')
            kwds['count'] = len(xl)
            kwds['x'] = _convertListParam(xl)
            kwds['y'] = _convertListParam(yl)
            kwds['boxWidth'] = _convertListParam(wl)
            kwds['boxHeight'] = _convertListParam(hl)
            return self._render(name,intent,dataGetter,**kwds)
        else:
            return '''<!-- unknown intent "%(name)s" "%(pageNum)s" "%(width)s" "%(height)s" "%(intent)s" "%(count)s" "%(kwds)s" -->''' % locals()
        return self._render(name,intent,dataGetter,**kwds)

    def multiTextRml(self,name,fieldsGetter,dataGetter=None,debugLabelDataGetter=None,**kwds):
        """Return RML for things like postcodes, National Insurance numbers.

        This is for formatting single-data-field text that is displayed using
        more than one positioned field (usually using letterBox).  For example:
        postcodes, NI numbers sort codes, etc.

        We want to give one name in a prep file and have the code fetch all the
        fields we need, get the content for each, and format the content in
        blocks.

        fieldsGetter is an object satisfying FieldsGetter interface.

        """
        if dataGetter is None:
            dataGetter = self.dataGetter
        rowDict = dict([(row[0], FieldStruct(dictFromRow(row))) for row in self.FIELD_ROWS])
        fieldsGetter.setFieldMap(rowDict)
        content = dataGetter(name)
        fields = fieldsGetter(name, content)
        rml = []
        for field in fields:
            kwds['content'] = field.content
            rml.append(self.fieldRml(field.name,dataGetter,**kwds))
        return '\n'.join(rml)

    def fieldSetRml(self,pattern,dataGetter,debugLabelDataGetter=None,onPage=None,**kwds):
        import re
        fields = [row for row in self.FIELD_ROWS if re.search(pattern, row[0])]
        if onPage:
            fields = [row for row in fields if row[1] and int(row[1])==onPage]
        return self._fieldSetRml(fields,kwds,dataGetter,debugLabelDataGetter)

    def fieldRml(self,name,dataGetter=None,**kwds):
        from xml.sax.saxutils import escape
        rows=[row for row in self.FIELD_ROWS if row[0].strip()==name]
        if not rows:
            def htmlCommentEscape(text):
                return escape(text.replace('--', '__'))
            return ('''<!--RML for %s kwds=%s should have been here-->''' %
                    (htmlCommentEscape(name), htmlCommentEscape(str(kwds))))
        return self._fieldSetRml(rows,kwds,dataGetter)

    def coords(self,name,dataGetter=None):
        rows=[row for row in self.FIELD_ROWS if row[0].strip()==name]
        if len(rows) != 1:
            raise ValueError()
        row = rows[0]
        rowDict = dictFromRow(row)
        return tuple([float(c) for c in (rowDict['x'], rowDict['y'])])

    def _fieldSetRml(self,rows,kwds,dataGetter=None,debugLabelDataGetter=None):
        if dataGetter is None:
            dataGetter = self.dataGetter
        rml = []
        for ROW in rows:
            nkwds = dictFromRow(ROW)
            nkwds.update(kwds)
            name = nkwds['name']
            pageNum = nkwds['pageNum']
            width=nkwds['width']
            height=nkwds['height']
            intent=nkwds['intent']
            count=nkwds['count']
            for unwanted in ('name','pageNum',
                'width','height','intent','count'):
                del nkwds[unwanted]
            rml.append(self._fieldRml(dataGetter,name,pageNum,width,height,intent,count,**nkwds))
            if debugLabelDataGetter is not None:
                x = float(nkwds['x'])
                y = float(nkwds['y'])
                boxWidth = 100
                boxHeight = 7
                rml.append(self._render(name,'textBox',debugLabelDataGetter,
                                        x=str(x),y=str(y),
                                        boxWidth=str(boxWidth),
                                        boxHeight=str(boxHeight),
                                        #boxFillColor='white',
                                        )
                           )
        return '\n'.join(rml)

    intentSpecs = dict(
            checkBox=IntentSpec('checkBox', 'checkBox','checked','''style x y labelFontName labelFontSize labelTextColor boxWidth boxHeight checkStrokeColor boxStrokeColor boxFillColor lineWidth line1 line2 line3 checked bold graphicOn graphicOff'''.split(),True,preRenderFunc=FixBoolean('checked')),
            textBox=IntentSpec('textBox','textBox','content','''style x y boxWidth boxHeight labelFontName labelFontSize labelTextColor labelOffsetX labelOffsetY boxStrokeColor boxFillColor textColor lineWidth fontName fontSize align vAlign shrinkToFit label borderSpec'''.split(),False),
            letterBoxes=IntentSpec('letterBoxes','letterBoxes','content','''style x y count label labelFontName labelFontSize labelTextColor labelOffsetX labelOffsetY boxWidth boxGap boxHeight combHeight boxStrokeColor boxFillColor textColor lineWidth fontName fontSize'''.split(),False),
            amount=IntentSpec('amount','letterBoxes','content','''style x y count label labelFontName labelFontSize labelTextColor labelOffsetX labelOffsetY boxWidth boxGap boxHeight combHeight boxStrokeColor boxFillColor textColor lineWidth fontName fontSize'''.split(),False),
            percentage=IntentSpec('percentage','letterBoxes','content','''style x y count label labelFontName labelFontSize labelTextColor labelOffsetX labelOffsetY boxWidth boxGap boxHeight combHeight boxStrokeColor boxFillColor textColor lineWidth fontName fontSize'''.split(),False),
            amount2=IntentSpec('amount','letterBoxes','content','''style x y count label labelFontName labelFontSize labelTextColor labelOffsetX labelOffsetY boxWidth boxGap boxHeight combHeight boxStrokeColor boxFillColor textColor lineWidth fontName fontSize boxExtraGaps'''.split(),False),
            )
    intentSpecs['letterBox'] = intentSpecs['letterBoxes']
    intentSpecs['multiBox'] = intentSpecs['letterBoxes']
    intentSpecs['multiAmountBox'] = intentSpecs['letterBoxes']

def _test():
    import doctest
    return doctest.testmod()

if __name__ == "__main__":
    _test()
