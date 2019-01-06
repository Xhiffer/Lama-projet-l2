#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
"""Page Description Parsing tools.  Extracts text from pages.

Currently this correctly extracts text, even kerned text, but does
not find and step into forms.  Called by pdfexplorer.  If we
move on to do a general "page description" parser, this is
where it should live.  This only deals with the "inner layer"
of PDF files.



"""
import re
from reportlab.lib.utils import asNative

patStartString = re.compile(r"\(")
patEndString = re.compile(r"\)")
patStartTextArray = re.compile(r"\[\s*\d*\s*\(")
patEndTextArray = re.compile(r"\)\s*\d*\s*\]")
patStartTextAny = re.compile(r"(\[\s*\d*\s*\()|(\()")
patNumber = re.compile(r"-?[0-9]*\.?[0-9]*")
# one of a number, whitespace, or the start of a string
patNextArrayElement = re.compile(r"(-?[0-9]*\.?[0-9]*)|\s+|\(")
patWhitespace = re.compile(r"\s+")

patFormRef = re.compile(r"/([a-zA-Z0-9\._-]+)\s+Do")
numbers = r"-?[0-9]*\.?[0-9]*"   #does not cover exponentials yet

# match a bracket, followed by anything
# want to find any ')' which is not part of a '\)'.
# solution: find x) where x is any character except backslash
startOfString = r"\("
anything = r".*?"
notBackSlash = r"[^\\]"
#pdf string ends with ), but not if it has \ before it.
#the endString pattern fiunds the end, but remember it contains
#a character.  So, the overall pattern will not match "()".
#then again, we don't find the text content of that pattern interesting anyway.
endString = notBackSlash + '\)'

pdfString = r"\(" + anything + notBackSlash + r"\)"
pdfNumber = r"-?[0-9]+\.?[0-9]*"
whitespace = r"\s+"

def anyOf(*args):
    return '(' + ')|('.join(args) + ')'

pdfTextArrayElement = anyOf(pdfNumber, pdfString)
patTextArrayElement = re.compile(pdfTextArrayElement)

patPdfString = re.compile(pdfString)
patPdfNumber = re.compile(pdfNumber)
patPdfStringOrNumber = re.compile(anyOf(pdfString, pdfNumber))

class PdfTextExtractor:
    "Implements text search, moving through the file"
    # the simple function approach works fine just
    # looking for (...), but gets messy with nexted
    # functions when looking for 2 possibilities, and
    # really would suck with more.  So, use a class
    # to track state.

    # To avoid writing a full parser, I use regex to find
    # any 'text array'.  The individual strings or the
    # "arrays of strings and spacers" are added to a list
    # for analysis later.



    def extractText(self, stuff):
        "returns all words"
        stuff = asNative(stuff,'latin1')    #basicall assumes 1-1 bytes
        self.cursor = 0
        self.maxLen = len(stuff)
        self.stuff = stuff
        self.textFound = []
        # this matches start of a text array, or start of a string
        patStartTextAny = re.compile(r"(\[\s*\d*\s*\()|(\()")

        while self.cursor < self.maxLen:
            match = patStartTextAny.search(self.stuff, self.cursor)
            if match is None:
                break  # we're done
            # set to character after the match, which is in the text
            firstChar = match.group()[0]
            if firstChar == '[':
                #complex case: it is an array
                # find a sequence of strings
                self.cursor = match.start()
                self.textFound.append(self.readTextArray())
            elif firstChar == '(':
                #simple case, it's a string
                self.cursor = match.end()
                self.textFound.append(self.readString())

        text = '\n'.join(self.textFound)

        #now unescape for human readability
        for (find, repl) in [("\\(", "("),
                             ("\\)", ")"),
                             ("\\n", "\n")]:
            text = text.replace(find, repl)
        return text

    def findForms(self, stuff):
        """Attempt to find form xobjects referenced with the Do operator

        If we're overlaying client details on a PDF form, the naive
        implementation would find text we drew on top, but none of the
        text in the form xobject itself.  So, we need to find
        occurrences of
                /FORMNAME Do
        in the page stream, so they can be searched too.
        """
        return patFormRef.findall(stuff)

    def readString(self):
        """Read and return a string at the cursor.

        Advances to next closing ) which is not preceded by a slash"""
        pos = self.cursor
        end = self.stuff.find( ')', pos)
        if end == -1:
            #we're at the end, return the rest of the text anyway although it's technically illegal PDF
            return self.stuff[pos:]
            #raise Exception("Unterminated text string in pdf ops starting at char %d" % self.cursor)
        while self.stuff[end-1] == '\\':
            # if it is a \(, doesn't count.
            end = self.stuff.find( ')', end+1)
            if end == -1:
                raise Exception("Unterminated text string in pdf ops starting at char %d" % self.cursor)

        self.cursor = end
        textFound = self.stuff[pos:end]
        return textFound

    def readTextArray(self):
        "Read and return a list of strings and spacings"

        # put a brake on how far it can go
        match = patEndTextArray.search(self.stuff, self.cursor)
        if match is None:
            raise Exception("Unterminated spaced text array in pdf starting at char %d" % self.cursor)
        # no further search operation need go beyond here.
        endPoint = match.end()
        array = []
        while self.cursor < endPoint:

            match = patPdfStringOrNumber.search(self.stuff, self.cursor, endPoint)
            if match is None:
                break
            found = match.group()
            if found[0] == '(':
                # a string
                array.append(found[1:-1])
            else:
                # a number
                offset = 0 - float(found)
                if offset > 500:
                    chars = int(0.001 * offset)
                    array.append(' ' * chars)
            self.cursor = match.end()

        self.cursor = endPoint
        return ''.join(array)


def extractText(pdfOps):
    """Attempt to extract any plain text within the postscript.

    This is to support searching.  It is not intended to
    find out what is contiguous, unwrap lines etc.  There are
    two patterns of interest:
    (1) literal strings between brackets
       (AWAY again)
    (2) kerned text, displayed as an array of strings
        with numbers between:
        [(HOME AND A)67(WAY)]
    The one above says to make the 'A' and 'W' 67/1000 of a box
    closer together than usual.  Distiller or other apps can often
    do this to text, and this can depend on kerning tables within the
    font.  We found that even the plainest of plain embedded tags within
    a Quark document exhibit this, so we better parse it.

    This returns a big string.  We assume that separate strings are
    separated by a space, but kerned ones like the above are not
    unless the string contains spaces.

    """

    found = []
    cursor = 0
    end = len(pdfOps)
    while 1:
        # find a ( which is not a \(
        start = pdfOps.find('(', cursor+1)
        while pdfOps[start-1:start] == '\\':
            # escaped, try again
            start = pdfOps.find('(', start+1)

        if start == -1:
            break
        end = pdfOps.find(')', start+1)
        while pdfOps[end-1:end] == '\\':
            # escaped, try again
            end = pdfOps.find(')', end+1)
            assert end != -1, 'unbalanced parentheses in postscript'
        slice = pdfOps[start+1:end]
        found.append(slice)
        cursor = end
    return '\n'.join(found)
