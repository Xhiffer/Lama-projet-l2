#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
"""This script lets you make zip files programmatically.

Usage:
    zipper.py input_spec archive_name [prefix=whatever]
        [notexts=...] [notdirs=...] [verbose=[1|0]]

    input_spec:  glob pattern, filename or directory name
    archive_name: zip file name you want, should end in .zip
    prefix: optional directory prefix which goes in the archive
            so you can have it make a directory when unzipped.

    notdirs: comma separated list of directories to exclude.
                e.g 'CVS' will exclude all directories with
                CVS in their path
    notexts: comma separated list of file extensions to ignore.

Examples:    
    zipper.py myfile.ext myfile.zip
        -> makes a zip file containing myfile.ext
    zipper.py *.py myarchive.zip
        -> zips up all files matching the pattern.

    zipper.py mydir myarchive.zip
        -> recursively zips everything in the diretory.
            The directory name is included at the top of the
            archive.

    zipper.py *.py archive.zip prefix=spam
        -> prefixes each archive name with 'spam', so
            it creates its own subdirectory when expanded.

    zipper.py mydir archive.zip notexts=pyc,pyo
        -> zips up but excludes any files ending in pyc or pyo

    zipper.py mydir archive.zip notdirs=CVS
        -> zips up but excludes any subdirectories called CVS

    C:\\code>c:\code\\rlextra\\utils\\zipper.py reportlab rl.zip
    notexts=pdf,pyc,a85 notdirs=CVS
        -> makes a fairly clean distro on my PC!
        
"""
__version__='3.3.0'
import zipfile
import os
import sys
import string


def getFilesUnder(directory, includeTop=0, extensions=None):
    "recursion utility"
    filelist = []
    def walker(arg, dirname, names, extensions=extensions):
        for name in names:
            if os.path.isfile(os.path.join(dirname,name)):
                if extensions is None:
                    arg.append(dirname + os.sep + name)
                else:
                    if os.path.splitext(name)[1] in extensions:
                        arg.append(dirname + os.sep + name)
    os.path.walk(directory, walker, filelist)
    if includeTop:
        for i in range(len(filelist)):
            filelist[i] = directory + os.sep + filelist[i]
    return filelist


def run(input, output,
        verbose=0,
        prefix=None,
        notdirs = [],
        notexts = []
        ):
    if verbose:
        print('input=%s, output=%s, prefix=%s' % (input, output, prefix))
        print('notdirs=%s' % notdirs)
        print('notexts=%s' % notexts)
    if os.path.isfile(input):
        filelist = [input]
    elif os.path.isdir(input):
        filelist = getFilesUnder(input)
    else:
        import glob
        filelist = glob.glob(input)

    if len(filelist) == 0:
        print('No files found')
        print(__doc__)
        sys.exit(1)

    z = zipfile.ZipFile(output, 'w', zipfile.ZIP_DEFLATED)
    for filename in filelist:
        # check if it is banned...
        dirname, rest = os.path.split(filename)
        dirBits = string.split(string.lower(dirname), os.sep)
        skipIt = 0
        for dirBit in dirBits:
            if dirBit in notdirs:
                skipIt = 1
        if skipIt:
            if verbose:
                print('skipping %s due to excluded directory "%s"' % (filename, dirBit)) 
            continue
        root, ext = os.path.splitext(rest)
        if string.lower(ext[1:]) in notexts:
            if verbose:
                print('skipping %s due to excluded extension "%s"' % (filename, ext)) 
            continue
            

        # Still here so we want the file. Do we need to add a directory prefix?
        if prefix:
            arcname = os.path.join(prefix, filename)
        else:
            arcname = filename

        # add to zip file            
        z.write(filename, arcname)
        if verbose:
            print('compressed %s' % arcname)
    z.close()
    print('wrote',output)
    
if __name__=='__main__':
    if len(sys.argv) < 2:
        print("Usage: zipper.py input_file_or_directory output.zip")
    else:
        args = sys.argv[1:]

        # separate keywords from normal args
        positional = []
        keywords = {
            'prefix':None,
            'notdirs':'',
            'notexts':'',
            'verbose':'0'
            }
        for arg in args:
            bits = string.split(arg, '=')
            if len(bits) == 1:
                positional.append(arg)
            elif len(bits) == 2:
                key, value = bits
                keywords[key] = value

        

        input = positional[0]
        output = positional[1]
        run(input, output,
            prefix=keywords['prefix'],
            notdirs=string.split(string.lower(keywords['notdirs']),','),
            notexts=string.split(string.lower(keywords['notexts']),','),
            verbose=(keywords['verbose']=='1')
            )
        
