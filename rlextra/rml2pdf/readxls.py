from __future__ import unicode_literals
import datetime

from rlextra.thirdparty import xlrd

def xlCellSpecToCoord(cs):
    """
>>> xlCellSpecToCoord("AA0")    # doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: bad Excel cell ...'AA0'
>>> xlCellSpecToCoord("AA1")
(26, 0)
>>> xlCellSpecToCoord("A1")
(0, 0)
>>> xlCellSpecToCoord("A0")     # doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: bad Excel cell ...'A0'
>>> xlCellSpecToCoord("A9")
(0, 8)
>>> xlCellSpecToCoord("A09")
(0, 8)
>>> xlCellSpecToCoord("A10")
(0, 9)
>>> xlCellSpecToCoord("A255")
(0, 254)
>>> xlCellSpecToCoord("A258")
(0, 257)
>>> xlCellSpecToCoord("IV5")
(255, 4)
>>> xlCellSpecToCoord("IW5")    # doctest: +ELLIPSIS
Traceback (most recent call last):
...
ValueError: bad Excel cell ...'IW5'
>>>

    """
    assert type(cs) == type('')
    A = ord("A")
    Z = ord("Z")
    if A <= ord(cs[1]) <= Z:
        if len(cs) < 3:
            raise ValueError('bad Excel cell %r' % cs)
        col = 26*(ord(cs[0])-A+1) + (ord(cs[1])-A)
        row = int(cs[2:])-1
    else:
        if len(cs) < 2:
            raise ValueError('bad Excel cell %r' % cs)
        col = ord(cs[0])-A
        row = int(cs[1:])-1
    if col > 255 or col < 0 or row < 0:
        raise ValueError('bad Excel cell %r' % cs)
    return col, row

def extract(fileName, sheetName,
            rangeSpec=None, rangeName=None,
            maxRows=None, maxCols=None):
    """This extracts the data in the sheet in list-of-list
    formats.  It tries to be modern and return Python booleans
    and dates.
    """
    from rlextra.thirdparty.xlrd.biffh import \
         XL_CELL_EMPTY, XL_CELL_DATE#, XL_CELL_TEXT, XL_CELL_NUMBER, XL_CELL_BOOLEAN, XL_CELL_ERROR

    if rangeName is not None:
        raise NotImplementedError('rangeName not yet implemented')

    book = xlrd.open_workbook(fileName, verbosity=0)
    sheet = book.sheet_by_name(sheetName)

    if rangeSpec is not None:
        if rangeSpec.count(':') != 1:
            raise ValueError("Bad Excel cell range: %r" % rangeSpec)
        cell1, cell2 = [xlCellSpecToCoord(cellSpec) for cellSpec in rangeSpec.split(":")]
        cols = cell1[0], cell2[0]
        rows = cell1[1], cell2[1]
        colMin, colMax = min(cols), max(cols)+1
        rowMin, rowMax = min(rows), max(rows)+1

    if rangeSpec is None and rangeName is None:
        rowMin = colMin = 0
        rowMax = sheet.nrows+1
        colMax = sheet.ncols+1

    if maxCols is not None:
        colMax = min(colMax, maxCols)
    if maxRows is not None:
        rowMax = min(rowMax, maxRows)

    out = []
    for rowx in range(rowMin, rowMax):
        row = []
        for colx in range(colMin, colMax):
            cellType = sheet.cell_type(rowx, colx)
            cellValue = sheet.cell_value(rowx, colx)

            if cellType is XL_CELL_EMPTY:
                cellValue = None
            elif cellType is XL_CELL_DATE:
                #convert
                yyyy,mm,dd,hh,nn,ss = xlrd.xldate_as_tuple(cellValue, book.datemode)
                cellValue = datetime.date(yyyy,mm,dd)
            else:
                pass #native value is OK

            row.append(cellValue)
        #now trim empties off the row - we don't want extra stuff on the
        #right, which might be hundreds of rows.
        
        while row and row[-1] is None:
            row.pop()

        out.append(row)

    #now trim off any blank rows at the end
    while out[-1:] == []:
        out.pop()
    return out

def _test(filename, sheetName):
    print('running on spreadsheet "%s"' % filename)

    data = extract(filename, sheetName, rangeSpec="A1:B3")#,maxRows=6)
    from pprint import pprint as pp
    pp(data)

def _doctest():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _doctest()
    #_test("test/exceldata.xls", "Sheet1")
