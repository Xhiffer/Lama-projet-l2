#!/usr/local/bin/python
"""Script to check for bad UTF-8 in a MySQL database.
NOT dependent on any assumptions about Django.

Tested on:
 - MySQL 5.0
"""
from __future__ import print_function
import sys

def getConnection(db='',host='',user='',passwd=''):
    import MySQLdb
    conn = MySQLdb.connect(
        host=host,
        user=user,
        passwd=passwd,
        db=db,
        charset='utf8',
        use_unicode=False,
        )
    return conn

def parseCommandLine():
    """Examines options and does preliminary checking"""
    from optparse import OptionParser

    parser = OptionParser(usage="%prog [options] database....",version='1.0')
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
                      help="user name (root)")
    parser.add_option("-p","--password",
                      dest="passwd",
                      default='',
                      help="user name (root)")
    options,args = parser.parse_args()
    if not len(args):
        parser.error("%prog needs at least one database argument")
    return options,args

def checkdb(options,db):
    conn = getConnection(db=db,host=options.host,user=options.user,passwd=options.passwd)
    cur = conn.cursor()
    try:
        cur.execute("""\
SELECT t.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE FROM information_schema.TABLES t, information_schema.COLUMNS c
  where t.TABLE_SCHEMA = c.TABLE_SCHEMA
  and t.TABLE_NAME = c.TABLE_NAME
  and (c.COLUMN_TYPE like '%%char%%' or c.COLUMN_TYPE like '%%text%%')
  and t.TABLE_SCHEMA = %s
  order by t.TABLE_NAME, c.COLUMN_NAME, c.COLUMN_TYPE
""",
                (db,),
                )
        columnRows = cur.fetchall()
    except:
        try:
            import re
            pat=re.compile('^.*(?:text|char).*$',re.I)
            cur.execute("""show table status from `%s`""" % db)
            T = [t[0] for t in cur.fetchall()]
            columnRows = []
            for tableName in T:
                cur.execute("""show columns from `%s`.`%s`""" % (db,tableName))
                data = cur.fetchall()
                columnRows += [(tableName,x[0],x[1]) for x in data if pat.match(x[1])] 
        except:
            print("""Could not get schema as per modern MySQL and older version failed as well""", file=sys.stderr)
            raise
    verbose = options.verbose
    if verbose:
        print(db)
    if verbose>2:
        print(columnRows)
    allRows = [None,None]
    for tableName, colName, colType in columnRows:
        if verbose>1:
            print(tableName, colName, colType)
        cur.execute("SELECT `%s` FROM %s.`%s`" % (colName, db, tableName))
        dataRows = cur.fetchall()
        for ii, dataRow in enumerate(dataRows):
            data = dataRow[0]
            if data is None: continue
            try:
                data.decode('utf-8')
            except UnicodeError:
                # we can't assume when doing the dataRows query that the first
                # primary key is called 'id' since that's not true in general
                # even of Django's primary keys (and MySQL < 5.1 doesn't tell us
                # which is the primary key), so select * now so we can report
                # which row we're looking at if we find a problem
                if allRows[0]!=tableName:
                    cur.execute("SELECT * FROM `%s`.`%s`" % (db, tableName))
                    allRows[0]=tableName
                    allRows[1]=cur.fetchall()
                if verbose>1:
                    print()
                print('%s.`%s`.`%s`:\n%s\n%s\n\n' % (
                    db, tableName, colName, data, allRows[1][ii][0]))
            if verbose>1 and not ii%10:
                print('.', end=' ')
        if verbose>1: print()

def main():
    options,args = parseCommandLine()
    for db in args:
        checkdb(options,db)


if __name__ == '__main__':
    main()
