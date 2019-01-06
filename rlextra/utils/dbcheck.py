#!/usr/local/bin/python
"""Script to check for bad UTF-8 in a MySQL database.
NOT dependent on any assumptions about Django.

Tested on:
 - MySQL 5.0
"""
from __future__ import print_function
import sys

def getConnection(db='',host='',user='',passwd=''):
    # local
    import MySQLdb
    conn = MySQLdb.connect(
        host=host,
        user=user,
        passwd=passwd,
        db=db,
        )
    return conn

def parseCommandLine():
    """Examines options and does preliminary checking"""
    from optparse import OptionParser

    parser = OptionParser(usage="%prog [options] database....",version='$LastChangedRevision$'.split(':')[1].strip('$').strip())
    parser.add_option("-v", "--verbose",
                      action="count", dest="verbose", default=0,
                      help="Print lots of information about what is going on")
    parser.add_option("--host",
                      dest="host",
                      default='localhost',
                      help="hostname (localhost)")
    parser.add_option("-u","--user",
                      dest="user",
                      default='root',
                      help="user name (root) for the db")
    parser.add_option("-p","--password",
                      dest="passwd",
                      default='',
                      help="password for the db")
    parser.add_option("--utf8",
                      action="store_true", dest="utf8", default=False,
                      help="checks given field(s) are in utf8")
    parser.add_option("--table",
                      dest="table",
                      default='',
                      help="only check specified table")
    parser.add_option("--field",
                      dest="field",
                      default='',
                      help="only check specified field, a table must also be specified")
    parser.add_option("--wellformed",
                      action="store_true", dest="wellformed", default=False,
                      help="check if xml is well formed")
    parser.add_option("--tags",
                      action="store_true", dest="tags", default=False,
                      help="shows different tags and attributes encountered")
    parser.add_option("--test",
                      action="store_true",
                      dest="test",
                      default=False,
                      help="Run unit tests")

    """options for
  
    --tags:  will run records
        through a forgiving html parser and show all different tags and attributes encountered

    #limiting output
    --max=10  just an idea, limit to this many records?
    other common problems:  entities (which ones); double-escaping; unescaped special characters

    --show  (duplicates verbose?) actually shows you the fields, rather than the content.    
    """
    options,args = parser.parse_args()
    if not options.test:
        if not len(args):
            parser.error("%prog needs at least one database argument")
    return options,args

def getSchema(options,conn, db):
    #Gets all columnRows
    cur = conn.cursor()
    try:
        cur.execute("""\
        SELECT t.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE FROM information_schema.TABLES t, information_schema.COLUMNS c
        where t.TABLE_SCHEMA = c.TABLE_SCHEMA
        and t.TABLE_NAME = c.TABLE_NAME
        and (c.COLUMN_TYPE like '%%char%%' or c.COLUMN_TYPE like '%%text%%')
        and t.TABLE_SCHEMA = %s
        order by t.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE""",(db,),)
        columnRows = cur.fetchall()
        return columnRows
    except:
        try:
            import re
            pat=re.compile('^.*(?:text|char).*$',re.I)
            cur.execute("""show table status from `%s`""" % db)
            T = [t[0] for t in cur.fetchall()]
            columnRows = []
            if options.table:
                tableName = options.table
                cur.execute("""show columns from `%s`.`%s`""" % (db,tableName))
                data = cur.fetchall()
                columnRows += [(tableName,x[0],x[1]) for x in data if pat.match(x[1])]
                return columnRows
            else:
                for tableName in T:
                    cur.execute("""show columns from `%s`.`%s`""" % (db,tableName))
                    data = cur.fetchall()
                    columnRows += [(tableName,x[0],x[1]) for x in data if pat.match(x[1])]
                return columnRows
        except:
            print("""Could not get schema as per modern MySQL and older version failed as well""", file=sys.stderr)
            raise

def getTable(conn, db, tableName):
    sql = 'SELECT * FROM `%s`.`%s`' % (db, tableName)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    return data

def getField(conn, db, tableName, colName):
    sql = 'SELECT `%s` FROM `%s`.`%s`' % (colName, db, tableName)
    cur = conn.cursor()
    cur.execute(sql)
    data = cur.fetchall()
    return data

def checkUTF8(data):
    """Verifies that data is proper UTF8
    """
    try:
        str(data).decode('utf8')
    except UnicodeDecodeError:
        print('Failed to decode as UTF8:\n%s\n' % str(data))

def checkWellFormed(data):
    """Checks content is valid XML.
    >>> 2 + 2
    4
    >>> 2 + 3
    6
    >>> data = [["<p>blah blah >/p>"]]
    >>> checkWellFormed(data)
    0
    """    
    import pyRXP
    parser = pyRXP.Parser(ExpandCharacterEntities = 0,
                          ExpandGeneralEntities = 0,
                          XMLPredefinedEntities = 1,
                          ErrorOnBadCharacterEntities = 0,
                          ErrorOnUndefinedEntities = 0,
                          CaseInsensitive = 0,
                          IgnoreEntities = 1,
                          ReturnList=1,
                          AllowMultipleElements = 1,
                          )
    if str(data).find('<')>-1 or str(data).find('>')>-1:
        try:
            parser('<fragment>%s</fragment>' % str(data))
        except pyRXP.error as e:
            print(e.args[0]) #first error message
            print(str(data)+'\n')

def findTags(t,tags=None):
    if tags is None: tags = []
    tag = t[0]
    if tag not in tags:
        tags.append(tag)
    if t[2]:
        for c in t[2]:
            if isinstance(c,tuple):
                findTags(c,tags)
    return tags

def checkTags(data, tags=None):
    if tags == None:
        tags = []
    import pyRXP
    parser = pyRXP.Parser(ExpandCharacterEntities = 0,
                          ExpandGeneralEntities = 0,
                          XMLPredefinedEntities = 1,
                          ErrorOnBadCharacterEntities = 0,
                          ErrorOnUndefinedEntities = 0,
                          CaseInsensitive = 0,
                          IgnoreEntities = 1,
                          ReturnList=1,
                          AllowMultipleElements = 0,
                          )
    if str(data).find('<')>-1 or str(data).find('>')>-1:
        try:
            d = parser('<fragment>%s</fragment>' % str(data))
            newTags = findTags(d[0])
            for t in newTags:
                if t not in tags:
                    tags.append(t)
            tags.remove('fragment')
            return tags
        except pyRXP.error:
            pass
        
def checkDataSet(dataset, checkFunc, rtrn=None):
    """Applies checkFunc to each cell of each row of dataset.
    Handles errors and tells you what row they occurred in.
    Can also return a result"""
    collection = []
    for d in dataset:
        for i in d:
            if rtrn:
                result = checkFunc(i)
                if result:
                    for a in result:
                        if a not in collection:
                            collection.append(a)
            else:
                checkFunc(i)
    if rtrn: return collection
                
def checkdb(options,db):
    conn = getConnection(db=db,host=options.host,user=options.user,passwd=options.passwd)
    verbose = options.verbose

    if options.field and not options.table:
        print('You have to specify which table %s is in' % options.field)
        sys.exit()

    #optionsDict = {'utf8': checkUTF8, 'wellformed': checkWellFormed, 'tags': checkTags,}
    if options.table:
        if options.field:
            dataset = getField(conn, db, options.table, options.field)
        else:
            dataset = getTable(conn, db, options.table)

        print('***checking table %s***\n' % options.table)
        if options.utf8:
            checkDataSet(dataset, checkUTF8)
        if options.wellformed:
            checkDataSet(dataset, checkWellFormed)
        if options.tags:
            print(checkDataSet(dataset, checkTags, True))
        print('***Done checking table %s***' % options.table)
        
    else:
        columnRows = getSchema(options,conn, db)        
        if verbose:
            print(db)
        if verbose>2:
            print(columnRows)
        cur = conn.cursor()
        tags = []
        for tableName, colName, colType in columnRows:
            if verbose>1:
                print(tableName, colName, colType)
            cur.execute("SELECT `%s` FROM `%s`.`%s`" % (colName, db, tableName))
            dataset = cur.fetchall()
            if options.utf8:
                print('Checking column %s in table %s...' % (colName, tableName))
                checkDataSet(dataset, checkUTF8)
                print('Done checking column %s in table %s...\n' % (colName, tableName))
            if options.wellformed:
                print('Checking column %s in table %s...' % (colName, tableName))
                checkDataSet(dataset, checkWellFormed)
                print('Done checking column %s in table %s...\n' % (colName, tableName))
            if options.tags:
                newTags =  checkDataSet(dataset, checkTags, True)
                if newTags:
                    for t in newTags:
                        if t not in tags:
                            tags.append(t)
        if options.tags:
            print(tags)
        
def main():
    options,args = parseCommandLine()
    if options.test:
        import doctest, rlextra.utils.dbcheck
        doctest.testmod(rlextra.utils.dbcheck)
    else:
        for db in args:
            checkdb(options,db)


if __name__ == '__main__':
    main()
