#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
"""Source Obfuscation Utility

usage: subfusc.py file1.py file2.py file3.py

We often have config files containing things like
database user names and passwords.  On a web server
these would typically be compiled to bytecodes; but
a script-kiddie grepping through the source might find
exciting words like 'password'.  Furthermore, Python now
has a widely available and easy-to-use bytecode disassembler.
What's more, a customer has insisted that we encrypt such
files using a well known algorithm such as RC4.

This makes things one step harder.  Given a source file,
we generate an intermediate "obfuscated source file"
which is functionally equivalent but a lot less readable.
We then compile this to a pyc.  For the pyc to run, it must
have access to the subfusc module.

For greater security we could move the encrypt/decrypt functions
into C code in _rl_accel, and allow an optional seed to be passed
in.  Further refinements would involve signing the bytecodes.
Getting past this would require the ability to read binaries :-)

I tested this by running our test suite with an obfuscated
canvas.pyc and it all works.

Time for an example.  Let's say you start with this:
---config.py-----
breakfast='eggs'
lunch='spam'
dinner='beer'
------end---------

The function obfuscateModule('config.py') would return this string:

-----new module------
#obfuscated version of sample_raw.py
data = '5A9LKUj2z+lt36tyrFkJZp4H2vPGspAJRgrlhaV6emWOdGqP31wxNQghuulz'\
       'C3jFRZtRmF0kC3Bl\nfzyAhs7bjznaIdqtQvgxbHnys+U4LyInlNCe6MXI+h4'\
       'cuAqvXZv7rw/GOGEnQTtca1BX3bYynj/y\nnZNJGYrVYYfz1uCRwb6GM64Yxz'\
       'e2uor17IQHg163fMtKphHhD6hwj+OURDgCoKcLSQeOguyNexvJ\ninEZ58dMT'\
       'TZJNQ1UzZfQQ2WdBl5xnQjNcHFsHK6vBCRWx1k=\n'\

import subfusc
exec subfusc.loadByteCode(data)
del data
del subfusc
-----end----------------

The block of goop is actually a marshalled bytecode object,
run through various encryption routines.

The function obfuscompile('srcfile.py') will put the source above
in a temp file, compile it, and create 'srcfile.pyc' alongside
the original exactly as if Python had compiled it.  The script
handler calls this.


"""
__version__='3.3.0'
SEED = 'guido van rossum'
# substitute your desired algorithm module here.
# functions should take encode(text, key) and
# decode(text, key) as signatures.
import os
import sys
import base64
import marshal
import string
import tempfile
import py_compile
from rlextra.utils import rc4 

def lineWrap(stuff, length=60):
    "Wraps a string into list of strings with max length n chars"
    lines = []
    while len(stuff):
        head = stuff[0:length]
        tail = stuff[length:]
        lines.append(head)
        stuff = tail
    return lines


def obfuscateModule(srcFileName):
    """ this generates a runnable pyc file using a compiled
    code object in the "goop", encrypted."""
    output = []
    srcLines = open(srcFileName).readlines()
    if srcLines[0][0:2] == '#!':
        # this is a script, preserve
        output.append(srcLines[0].strip())
        srcText = string.join(srcLines[1:], '\n')
    else:
        srcText = string.join(srcLines, '\n')

    output.append('#obfuscated version of %s' % srcFileName)
    codeObj = compile(srcText, srcFileName, 'exec')
    marshalled = marshal.dumps(codeObj)
    encoded = rc4.encode(marshalled, SEED)
    asciified = base64.encodestring(encoded)
    wrapped = lineWrap(asciified)
    output.append('data = %s\\' % repr(wrapped[0]))
    for line in wrapped[1:]:
        output.append( '       %s\\' % repr(line))
    output.append('')
    output.append('from rlextra.utils import subfusc')
    output.append('exec subfusc.loadByteCode(data)')
    output.append('del data')
    output.append('del subfusc')
    return string.join(output, '\n')


def loadByteCode(textBlock):
    "Loads the compiled code.  This is put at the bottom of generated modules"
    unwrapped = string.join(string.split(textBlock))
    binary = base64.decodestring(unwrapped)
    marshalled = rc4.decode(binary, SEED)
    codeObj = marshal.loads(marshalled)
    return codeObj
    
def obfuscompile(srcFileName):
    """Turns a plain py file to a scrambled pyc next to it"""
    tempfilename = tempfile.mktemp()
    obfuscatedSource = obfuscateModule(srcFileName)
    open(tempfilename, 'w').write(obfuscatedSource)
    py_compile.compile(tempfilename, cfile=srcFileName + 'c', dfile=srcFileName)
    os.remove(tempfilename)

if __name__=='__main__':
    if len(sys.argv) < 1:
        print('usage: subfusc.py file1.py file2.py file3.py')
    else:
        for arg in sys.argv[1:]:
            obfuscompile(arg)
            print('compiled %sc' % arg)
        
    


