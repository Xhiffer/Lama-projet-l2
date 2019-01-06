#chartconfig
"""Allows charts to be overridden by configuration files.

This feature is an addition in November 2005.  I've tried to implement
it with minimum changes to the code base.

Here's the kind of file you can create:

    ---------------------------diagra.ini--------------------------------

    [DEFAULT]
    #this will apply to all chart types. So, it's a great place
    #to set database connection parameters.
    dataSource.name = 'mydata_uat'
    dataSource.user = 'gordon'
    dataSource.password = 'drongo'



    [module]
    #any in here will apply to modules with corresponding names. This is
    #the usual way to do it, as end users will not see the class names
    #very often.

    #specifics in module override stuff in DEFAULT


Lots of doctests follow.  Start by making a drawing

>>> from reportlab.graphics.shapes import Drawing
>>> from reportlab.graphics.charts.barcharts import HorizontalBarChart
>>> d = Drawing()
>>> chart = HorizontalBarChart()
>>> d.add(chart, name='chart')
>>> d.height
200
>>> d.chart.valueAxis.labels.fontName
'Times-Roman'

>>> d.__class__.__module__
'reportlab.graphics.shapes'
>>> #hack it so I can test better
>>> d.__class__.__module__ = 'mychart'
>>> d.__class__.__module__
'mychart'

>>> configData = '''
... [DEFAULT]
... dataSource.name = 'mydata_uat'
... dataSource.user = 'gordon'
... dataSource.password = 'drongo'
...
... [mychart]
... chart.valueAxis.labels.fontName='Helvetica'
... chart.valueAxis.labels.fontSize=12
... someColor = red
... height = 250
... '''
>>> #parse it by hand
>>> from reportlab.lib.utils import getStringIO
>>> config = SafeConfigParser()
>>> config.optionxform = str
>>> buf = getStringIO(configData)
>>> config.readfp(buf)
>>> del buf
>>> config.has_section('mychart')
True
>>> from pprint import pprint as pp
>>> pp(sorted(config.items('DEFAULT')))
[('dataSource.name', "'mydata_uat'"),
 ('dataSource.password', "'drongo'"),
 ('dataSource.user', "'gordon'")]
>>> pp(sorted(config.items('mychart')))
[('chart.valueAxis.labels.fontName', "'Helvetica'"),
 ('chart.valueAxis.labels.fontSize', '12'),
 ('dataSource.name', "'mydata_uat'"),
 ('dataSource.password', "'drongo'"),
 ('dataSource.user', "'gordon'"),
 ('height', '250'),
 ('someColor', 'red')]
>>> applied = applyToDrawing(config, d)
>>> applied
3
>>> d.height
250
"""
import sys, os
try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser

def findConfigFilesUpwards(fileName, startDir=None, maxLevels=None):
    """Find and return list of full paths to config file, searching up.

    If startDir not provided, take current directory.
    if maxLevels not set, it tracks up to the top of the file system.

    If not found, return empty list"""
    if startDir is None:
        startDir = os.getcwd()

    found = []
    dirName = startDir
    levels = 1
    while 1:
        searchFor = dirName + os.sep + fileName
        if os.path.isfile(searchFor):
            found.append(searchFor)
        newDirName = os.path.dirname(dirName)
        if newDirName == dirName:
            break
        else:
            dirName = newDirName
            levels += 1
            if (maxLevels is not None) and (levels > maxLevels):
                break

    return found

def getConfig(fileName, startDir=None, maxLevels=None, verbose=False):
    """Returns a parsed configParser object using all config files
    found above the search path.

    """
    confFileNames = findConfigFilesUpwards(fileName, startDir, maxLevels)
    cp = SafeConfigParser()
    cp.optionxform = str   #make it case sensitive
    if confFileNames:
        #found it/them
        #the one closest to start has highest priority
        #so read the highest first
        confFileNames.reverse()
        for confFileName in confFileNames:
            if verbose:
                print('found config %s' % confFileName)
            cp.read(confFileName)
    return cp

def applyToDrawing(config, drawing, verbose=False):
    """Applies all relevant info to the drawing.

    If verbose, reports 'misses' to alert you to any
    config entries not used.
    """
    if config is None:
        return

    if verbose:
        print('Applying config options:')

    items =dict([(k,v) for k,v in config.items('DEFAULT')])
    moduleName = drawing.__class__.__module__
    if moduleName=='__main__':
        moduleName = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    if verbose: print('module name=%r' % moduleName)
    if config.has_section(moduleName):
        #this is intended for us.  The configparser puts all
        #the default in here anyway
        items.update(dict([(k,v) for k,v in config.items(moduleName)]))
    if verbose: print('config items=%r' % items)

    #we really want the namespace of the chart module, but if
    try:
        ns = sys.modules[moduleName].__dict__.copy()
        if verbose: print('Using namespace from', moduleName)
    except:
        ns = {}
    #that fails we want one allowing colour imports at the least.
    #presumably Robin could apply here whatever trickery he did
    #in guiedit to type-convert

    from reportlab.graphics.shapes import STATE_DEFAULTS
    SDK = list(STATE_DEFAULTS.keys())
    ns.update(dict(drawing=drawing, STATE_DEFAULTS=STATE_DEFAULTS))
    exec("from reportlab.lib.colors import *", ns)

    setOK = 0
    for fullPath, strValue in items.items():
        if fullPath in SDK:
            command = 'STATE_DEFAULTS[%r] = %s' % (fullPath,strValue)
        else:
            command = 'drawing.%s = %s' % (fullPath, strValue)
        try:
            if verbose and 'password' not in command:
                sys.stdout.write('  trying %s'%command)
            exec(command, ns)
            setOK += 1
            if verbose: print('...OK')
        except Exception as e:
            if verbose: print('...failed: %s' % e)
    if verbose: print()

    return setOK

if __name__=='__main__':
    import doctest, chartconfig
    doctest.testmod(chartconfig)
