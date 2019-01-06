"""
This script enumerates all loaded modules, creates a pythonxx.zip for each
and copyies associated .pyds. The aim is to prepare a package of modules
you will need to distribute.

Usage: When your program ends, add these two lines:

import dumpmods
dumpmods.analyze_modules(<path to store files in>)

where <path to store files in> has obvious connotations.
"""
import sys
import os
import shutil
import zipfile

def getarcname(filename):
    lfn=filename.lower()
    for p in [p for p in sys.path if p.endswith('site-packages')]+[p for p in sys.path if not p.endswith('site-packages')]:
        if lfn.startswith(p.lower()):
            return filename[len(p)+1:]
    return filename

def analyze_modules(targetdir):
    if os.path.isfile(targetdir):
        print("Cannot use %s as a target dir" % targetdir)
    else:
        try:
            os.makedirs(targetdir)
        except IOError:
            pass
    print("Analyzing modules needed...")

    zname = os.path.join(targetdir, "python%s.zip" % ''.join(sys.version.split()[0].split('.')[:2]))
    print("Creating %s..." % zname)
    z = zipfile.ZipFile(zname, "w", zipfile.ZIP_DEFLATED)

    encpath = None

    for modulename in list(sys.modules.keys()):
        module = sys.modules[modulename]
        try:
            filename = module.__file__
        except:
            if repr(module).find("(built-in)") < 0:
                print("---> IGNORING %s (%s)" % (modulename, module))
            continue

        # windows:
        #filename = filename.lower()
        if filename.lower().endswith(".pyc") or filename.lower().endswith(".py"):
            arcname = getarcname(filename)
            if arcname.startswith("encodings\\"):
                print("skipping encodings, will be filled in later...")
                if not encpath:
                    encpath = os.path.dirname(filename)
            else:
                print("adding %s as %s" % (filename, arcname))
                z.write(filename, arcname)
        elif filename.endswith(".pyd"):
            nname = os.path.join(targetdir, os.path.basename(filename))
            print("copying %s as %s" % (filename, nname))
            shutil.copy( filename, nname )

    # add encodings
    if encpath:
        F = os.listdir(encpath)
        FC = [x for x in F if x.lower().endswith('.pyc')]
        F = list(filter(lambda x,FC=FC: x.lower().endswith('.py') and x+'c' not in FC,F))
        for f in FC+F:
            source = os.path.join(encpath, f)
            target = "encodings\\%s" % f
            print("adding %s as %s" % (source, target))
            z.write(source, target)

    z.close()

if __name__ == "__main__":
    analyze_modules("z:\\")
