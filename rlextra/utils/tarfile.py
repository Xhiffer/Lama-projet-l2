#!/usr/bin/env python
#-------------------------------------------------------------------
# tarfile.py
#
# Module for reading and writing .tar and tar.gz files.
#
# Needs at least Python version 2.2.
#
# Please consult the html documentation in this distribution
# for further details on how to use tarfile.
# 
#-------------------------------------------------------------------
# Copyright (C) 2002 Lars Gustaebel <lars@gustaebel.de>
# All rights reserved.
#
# Permission  is  hereby granted,  free  of charge,  to  any person
# obtaining a  copy of  this software  and associated documentation
# files  (the  "Software"),  to   deal  in  the  Software   without
# restriction,  including  without limitation  the  rights to  use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies  of  the  Software,  and to  permit  persons  to  whom the
# Software  is  furnished  to  do  so,  subject  to  the  following
# conditions:
#
# The above copyright  notice and this  permission notice shall  be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS  IS", WITHOUT WARRANTY OF ANY  KIND,
# EXPRESS OR IMPLIED, INCLUDING  BUT NOT LIMITED TO  THE WARRANTIES
# OF  MERCHANTABILITY,  FITNESS   FOR  A  PARTICULAR   PURPOSE  AND
# NONINFRINGEMENT.  IN  NO  EVENT SHALL  THE  AUTHORS  OR COPYRIGHT
# HOLDERS  BE LIABLE  FOR ANY  CLAIM, DAMAGES  OR OTHER  LIABILITY,
# WHETHER  IN AN  ACTION OF  CONTRACT, TORT  OR OTHERWISE,  ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
#copyright ReportLab Europe Limited. 2000-2012
"""Read from and write to tar format archives.
"""
from __future__ import print_function
from reportlab import xrange
__version__='3.3.0'
# $Source: /rl_home/xxx/repository/rlextra/utils/tarfile.py,v $

version = "0.3.3"
__author__ = "Lars Gust\xe4bel (lars@gustaebel.de)"
__date__ = "$Date$"
__cvsid__ = "$Id$"
__credits__ = "Detlef Lannert for some early contributions"

#---------
# Imports
#---------
import sys
import os
try:
    import builtins
except ImportError:
    import __builtin__ as builtins
import shutil
import stat
import time

try:
    import grp, pwd
except ImportError:
    grp = pwd = None

#---------
# Exports
#---------
__all__ = ["TarFile", "TarInfo", "open", "gzopen",
           "REGTYPE", "AREGTYPE", "LNKTYPE",
           "SYMTYPE", "CHRTYPE", "BLKTYPE",
           "DIRTYPE", "FIFOTYPE", "CONTTYPE",
           "REGULAR_TYPES"]

#------------------------
# TAR specific constants
#------------------------
BLOCKSIZE = 512                 # length of processing blocks
RECORDSIZE = BLOCKSIZE * 20     # length of records (a product of BLOCKSIZE)
MAGIC = "ustar"                 # magic tar string
VERSION = "00"                  # version number

LENGTH_NAME = 100               # maximal length of a filename
LENGTH_LINK = 100               # maximal length of a linkname

REGTYPE = "0"                   # regular file
AREGTYPE = "\0"                 # regular file
LNKTYPE = "1"                   # link (inside tarfile)
SYMTYPE = "2"                   # symbolic link
CHRTYPE = "3"                   # character special device
BLKTYPE = "4"                   # block special device
DIRTYPE = "5"                   # directory
FIFOTYPE = "6"                  # fifo special device
CONTTYPE = "7"                  # contiguous file

GNUTYPE_LONGNAME = "L"          # GNUtar longnames
GNUTYPE_LONGLINK = "K"          # GNUtar longlink

#-------------------------------
# tarfile specific constants
#-------------------------------
SUPPORTED_TYPES = (REGTYPE, AREGTYPE, LNKTYPE,  # file types that tarfile
                   SYMTYPE, DIRTYPE, FIFOTYPE,  # can cope with.
                   CONTTYPE, GNUTYPE_LONGNAME,
                   GNUTYPE_LONGLINK)

REGULAR_TYPES = (REGTYPE, AREGTYPE, CONTTYPE)   # file types that represent
                                                # regular files

#-----------------------
# Some useful functions
#-----------------------
def nts(s):
    """Convert a null-terminated string buffer to
    a normal python string."""
    return s.split("\0", 1)[0]

def stn(s, maxlen=None):
    """Reverse method to nts. Pad with zero-chars up to
    maxlen (optional)."""
    if not maxlen: return s + "\0"
    return s + "\0" * (maxlen - len(s))

def calc_chksum(buf):
    """Calculate the checksum for an member's header. It's a simple addition
    of all bytes, treating the chksum field as if filled with spaces.
    buf is a 512 byte long string buffer which holds the header.
    """
    chk = 256                           # chksum field is treated as blanks,
                                        # so the initial value is 8 * ord(" ")
    for c in buf[:148]: chk += ord(c)   # sum up all bytes before chksum
    for c in buf[156:]: chk += ord(c)   # sum up all bytes after chksum
    return chk

def copyfileobj(fo1, fo2, length):
    """Copy length bytes from fileobj fo1 to fileobj fo2.
    """
    BUFSIZE = 65535
    blocks, remainder = divmod(length, BUFSIZE)
    for b in range(blocks):
        buf = fo1.read(BUFSIZE)
        if buf is None: raise IOError("end of file (EOF) reached")
        fo2.write(buf)

    buf = fo1.read(remainder)
    if buf is None: raise IOError("end of file (EOF) reached")
    fo2.write(buf)    

if os.sep != "/":
    def normpath(path):
        return os.path.normpath(path).replace(os.sep, "/")
else:
    normpath = os.path.normpath

class TarError(Exception):
    """Internal exception"""
    pass

#--------------------
# exported functions
#--------------------
def open(name, mode="r", fileobj=None):
    """Open a (uncompressed) tar archive for reading, writing
    or appending.
    """
    return TarFile(name, mode, fileobj)

def gzopen(gzname, gzmode="r", compresslevel=9, fileobj=None):
    """Open a gzip compressed tar archive for reading or writing.
    Appending is not allowed.
    """
    if gzmode == "a":
        raise RuntimeError("Appending to gzipped archive is not allowed")
    
    import gzip
    pre, ext = os.path.splitext(gzname)
    if ext == ".tgz": ext = ".tar"
    if ext == ".gz": ext = ""
    tarname = pre + ext
    mode = gzmode
    if "b" not in gzmode: gzmode += "b"
    if mode[0:1] == "w":
        if not fileobj:
            #AR 2.1 downgrade
            fileobj = builtins.open(gzname, gzmode)
            #fileobj = __builtin__.file(gzname, gzmode)
        #t = TarFile(tarname, mode, gzip.GzipFile(tarname, gzmode,
        #                                         compresslevel, fileobj))
        t = TarFile(tarname, mode[0:1], gzip.GzipFile(tarname, gzmode,
                                                 compresslevel, fileobj))
    else:
        t = TarFile(tarname, mode, gzip.open(gzname, gzmode, compresslevel))
    t._extfileobj = 0
    return t

def is_tarfile(name):
    """Return 1 if name points to a valid tar archive,
    else return 0.
    """
    buf = builtins.open(name, "rb").read(BLOCKSIZE)
    buftoinfo = TarFile.__dict__["_buftoinfo"]
    try:
        buftoinfo(None, buf)
    except ValueError:
        try:
            import gzip
            buf = gzip.open(name, "rb").read(BLOCKSIZE)
            buftoinfo(None, buf)
        except:
            try:
                import bz2
                buf = bz2.BZ2File(name, "r").read(BLOCKSIZE)
                buftoinfo(None, buf)
            except:
                return 0
    return 1
    
#------------------
# Exported Classes
#------------------
class TarInfo:
    """Informational class which represents a tar Header Block
    (POSIX 1003.1-1990).TarInfo objects are returned by
    TarFile.getinfo() and TarFile.getmembers() and are usually
    created internally.
    If you want to create a TarInfo object from the outside, you
    can use TarFile.gettarinfo() if the file already exists (recommended),
    or you can instanciate the class yourself.
    """

    name = ""               # member name (dirnames must end with '/')
    mode = 0o100666          # file permissions (default)
    uid = 0                 # user id
    gid = 0                 # group id
    size = 0                # file size
    mtime = 0               # modification time
    chksum = 0              # header checksum
    type = "0"              # member type, default REGTYPE
    linkname = ""           # link name
    uname = "user"          # user name
    gname = "group"         # group name
    devmajor = ""           #-+
    devminor = ""           # + not neccessary at this time
    prefix = ""             #-+
    
    offset = 0              # the tar header starts here
    offset_data = 0         # the REGTYPE file's data starts here

    def __init__(self, name=""):
        """Create a TarInfo object. name is the optional name
        of the member.
        """
        self.name = name
        
    def getheader(self):
        """Return a tar header as a 512 byte string.
        """
        # The following code was contributed by Detlef Lannert. Danke, Detlef.
        parts = []
        for value, fieldsize in (
                (self.name, 100),                       # file name
                ("%07o" % self.mode, 8),                # file permissions
                ("%07o" % self.uid, 8),                 # user id
                ("%07o" % self.gid, 8),                 # group id
                ("%011o" % self.size, 12),              # file size
                ("%011o" % self.mtime, 12),             # modification time
                ("        ", 8),                        # for checksum
                (self.type, 1),                         # file type
                (self.linkname, 100),                   # link name
                (MAGIC, 6),                             # magic string
                (VERSION, 2),                           # version number
                (self.uname, 32),                       # user name
                (self.gname, 32),                       # group name
                ):
            l = len(value)
            parts.append(value + (fieldsize - l) * "\0")
        
        buf = "".join(parts)
        chksum = calc_chksum(buf)
        buf = buf[:148] + "%07o" % chksum + buf[155:]
        buf += (512 - len(buf)) * "\0"
        self.buf = buf
        return buf
# class TarInfo


class TarFile:
    """Class representing a TAR archive on disk.
    """    
    debug = 0                   # may be set from 0 (no msgs) to 2 (all msgs)
    
    dereference = 1             # if true, add content of linked file to the
                                # tar file, else the link.
    fileobj = None

    def __init__(self, name=None, mode="r", fileobj=None):
        self.name = name
        
        if len(mode) > 1 or mode not in "raw":
            raise RuntimeError("mode must be either 'r', 'a' or 'w', " \
                                "not '%s'" % mode)
        self._mode = mode
        self.mode = {"r": "rb", "a": "r+b", "w": "wb"}[mode]
        
        if not fileobj:
            fileobj = builtins.open(self.name, self.mode)
            self._extfileobj = 0
        else:
            if self.name is None and hasattr(fileobj, "name"):
                self.name = fileobj.name
            if hasattr(fileobj, "mode"):
                self.mode = fileobj.mode
            self._extfileobj = 1
        self.fileobj = fileobj

        # Init datastructures
        self.members = []           # list of entires as TarInfo objects
        self.membernames = []       # names of members 
        self.chunks = [0]           # chunk cache
        self._loaded = 0            # flag if members have all been read
        self.offset = 0            # current position in the tarfile
        self.inodes = {}            # dictionary caching the inodes of archive
                                    # members already written

        if self._mode == "a":
            self.fileobj.seek(0)
            self._load()
            #self.fileobj.seek(self.chunks[-1])
            #DEL
            

        
    def _load(self):
        """Read through the entire tarfile and look for valid members.
        Is executed when e.g. getmembers() or getnames() is called,
        when there is a random access via read() or readstr().
        """
        while 1:
            tarinfo = next(self)
            if not tarinfo: break
        self._loaded = 1            
        #DEL self.fileobj.seek(0)
        return

    def _proc_gnulong(self, tarinfo, type):
        """Evaluate the two blocks that hold a longname.
        """
        name = None
        linkname = None
        
        buf = self.fileobj.read(BLOCKSIZE)
        if not buf: return None
        self.offset += BLOCKSIZE
        if type == GNUTYPE_LONGNAME:
            name = nts(buf)
        if type == GNUTYPE_LONGLINK:
            linkname = nts(buf)

        buf = self.fileobj.read(BLOCKSIZE)
        if not buf: return None
        tarinfo = self._buftoinfo(buf, tarinfo)
        if name is not None:
            tarinfo.name = name
        if linkname is not None:
            tarinfo.linkname = linkname
        self.offset += BLOCKSIZE
        return tarinfo
    
    def _buftoinfo(self, buf, tarinfo=None):
        """Return a TarInfo object filled with data
        provided by a 512 byte buffer.
        """
        if not tarinfo:
            tarinfo = TarInfo()
        tarinfo.name = nts(buf[0:100])
        tarinfo.mode = int(buf[100:108], 8)           
        tarinfo.uid = int(buf[108:116],8)             
        tarinfo.gid = int(buf[116:124],8)             
        tarinfo.size = int(buf[124:136], 8)          
        tarinfo.mtime = int(buf[136:148], 8)    
        tarinfo.chksum = int(buf[148:156], 8)
        tarinfo.type = buf[156:157]
        tarinfo.linkname = nts(buf[157:257])          
        tarinfo.uname = nts(buf[265:297])             
        tarinfo.gname = nts(buf[297:329])
        tarinfo.prefix = buf[345:500]
        return tarinfo

    def __next__(self):
        """Return the next member from the tarfile.
        Return None if the end of tarfile is reached.
        Can be used in a while statement and is used
        for Iteration (see __iter__()) and internally.
        """
        if not self.fileobj:
            raise IOError("Cannot access closed file")
        if self._mode not in "ra":
            raise IOError("File is not openend for reading.")

        # Read the next block ignoring empty or non-standard blocks.
        self.fileobj.seek(self.chunks[-1])
        while 1:
            buf = self.fileobj.read(BLOCKSIZE)
            if not buf: return None
            # Try to convert 512 byte block
            # to a TarInfo object.
            try: tarinfo = self._buftoinfo(buf)
            except ValueError:
                self.offset += BLOCKSIZE
                continue
            break

        # If the TarInfo object contains a GNUTYPE longname or longlink
        # statement, we must parse them first.
        if tarinfo.type in (GNUTYPE_LONGLINK, GNUTYPE_LONGNAME):
            tarinfo = self._proc_gnulong(tarinfo, tarinfo.type)

        # Add offsets to tarinfo
        tarinfo.offset = self.offset
        tarinfo.offset_data = self.offset + BLOCKSIZE

        # Proceed with the next block.
        self.offset += BLOCKSIZE

        if tarinfo.type in REGULAR_TYPES and tarinfo.size:
            # If header contains a size field,
            # the following n data blocks are skipped.
            blocks, remainder = divmod(tarinfo.size, BLOCKSIZE)
            if remainder: blocks += 1
            self.offset += blocks * BLOCKSIZE

        self.members.append(tarinfo)
        self.membernames.append(tarinfo.name)
        self.chunks.append(self.offset)       # next member's offset
        return tarinfo

    def _create_gnulong(self, name, type):
        """Insert a GNU longname/longlink member into a tarfile.
        It consists of a usual tar header, with the length
        of the filename as size, followed by data blocks (normally 1),
        which contain the filename as a null terminated string.
        """
        tarinfo = TarInfo()
        tarinfo.name = "././@LongLink"
        tarinfo.type = type
        tarinfo.mode = 0
        self.writestr(tarinfo, name + "\0")

    def getmembers(self):
        """Return a list of all members in tarfile (as TarInfo objects).
        """
        if not self._loaded: self._load()   # if we want to obtain a list of
                                            # all members, we first have to
                                            # read through the tar file.
        return self.members

    def getnames(self):
        """Return a list of names of all members in tarfile.
        """
        if not self._loaded: self._load()
        return self.membernames

    def __iter__(self):
        """Provide an iterator object for use in a for statement.
        Requires Python >= 2.2
        """
        if self._loaded:
            # All members read, iterate over internal list.
            return self.members.__iter__()
        else:
            return TarIter(self)

    def readstr(self, member):
        """Extract `member' and return its bytes. member may be a filename
        or a TarInfo instance.
        """
        if not self.fileobj: raise IOError("Cannot access closed file")
        if self._mode != "r":
            raise IOError("Cannot read from tar archive opened for writing")

        if isinstance(member, TarInfo):
            tarinfo = member
        else:
            tarinfo = self.getinfo(member)

        if tarinfo.type in REGULAR_TYPES:
            self.fileobj.seek(tarinfo.offset_data)
            return self.fileobj.read(tarinfo.size)
        elif tarinfo.type == LNKTYPE:
            linkname = tarinfo.linkname
            return self.readstr(self._getmember(linkname, tarinfo))
        else:
            return ""

    def read(self, member, path=""):
        """Extract `member' from the tarfile and write
        it to path (optional). member may be a filename or a TarInfo instance.
        """
        if not self.fileobj: raise IOError("Cannot access closed file")
        if self._mode != "r": raise IOError("Cannot read from write-mode file")

        if isinstance(member, TarInfo):
            tarinfo = member
        else:
            tarinfo = self.getinfo(member)

        if self.debug > 1: print(tarinfo.name, end=' ')
        try:
            self._extract_member(tarinfo, os.path.join(path, tarinfo.name))
        except TarError as e:
            if self.debug > 1:
                print()
                print("tarfile: '%s'" % e)
            return
        if self.debug > 1: print()

    def _extract_member(self, tarinfo, targetpath):
        """Extract the TarInfo object tarinfo to a pysical
        file called targetpath.
        """
        # Fetch the TarInfo object for the given name
        # and build the destination pathname, replacing
        # forward slashes to platform specific separators
        if targetpath[-1:] == "/": targetpath = targetpath[:-1]
        targetpath = os.path.normpath(targetpath)

        if tarinfo.type not in SUPPORTED_TYPES:
            raise TarError("Unsupported type `%s'" % tarinfo.type)

        # If the member is a directory, we are so nice
        # and create all upper directories on the fly.
        # os.makedirs() does a good job for that.
        if tarinfo.type == DIRTYPE:
            try: os.makedirs(targetpath)
            except (IOError, OSError) as e:
                raise TarError("Could not create %s" % tarinfo.name)

        # The member is regular file, resp. a contiguous file
        # which we treat like a regular one.
        # At first, all upper directories are created,
        # then we seek to the offset in the tarfile, where the
        # data locates and write it to the destination file.
        if tarinfo.type in REGULAR_TYPES:
            try:
                os.makedirs(os.path.dirname(targetpath))
            except (IOError, OSError) as e:
                pass
            try:
                self.fileobj.seek(tarinfo.offset_data)
                target = builtins.open(targetpath, "wb")
                copyfileobj(self.fileobj, target, tarinfo.size)
                target.close()
            except (IOError, OSError) as e:
                raise TarError(e)

        # The member is either a symbolic link or a hardlink
        # (a link inside the tarfile).
        # GNUtar behaviour is imitated. That means, if the link cannot
        # be created (because of an error or lacking support by filesystem)
        # we try to resolve the link. First we look for a valid member in the
        # tar archive, second we look in the filesystem.
        if tarinfo.type in (SYMTYPE, LNKTYPE):
            linkpath = tarinfo.linkname
            linkpath = os.path.normpath(linkpath)
            if self.debug > 1: print("->", linkpath, end=' ')

            created = 1
            if tarinfo.type == SYMTYPE:
                try: os.symlink(linkpath, targetpath)
                except (AttributeError, IOError, OSError) as e: created = 0
            elif tarinfo.type == LNKTYPE:
                try: os.link(linkpath, targetpath)
                except (AttributeError, IOError, OSError) as e: created = 0
                    
            if not created:
                linkpath = os.path.join(os.path.dirname(tarinfo.name),
                                        tarinfo.linkname)
                linkpath = os.path.normpath(linkpath)
                linkpath = normpath(linkpath)
                try:
                    self._extract_member(self.getinfo(linkpath), targetpath)
                except (IOError, OSError, KeyError) as e:
                    linkpath = os.path.normpath(linkpath)
                    try:
                        shutil.copy2(linkpath, targetpath)
                    except (IOError, OSError) as e:
                        raise TarError("Link could not be created")

        # The member is a fifo, so if the platform supports
        # fifos, we create one.
        if tarinfo.type in (FIFOTYPE,):
            if hasattr(os, "mkfifo"):
                try:
                    os.mkfifo(targetpath)
                except (IOError, OSError) as e:
                    raise TarError(e)
            else:
                raise TarError("fifo not supported by os")

        # The file has now been extracted. There are still some
        # things to be done.
        # All following tasks are skipped if the file was a symbolic
        # link.

        # Here we set the file's last modification time.
        # XXX If file is a directory, we do not set its mtime
        # because in most of the cases, it is reset to
        # current time when accessing files underneath.
        # Seems to make problems under win32 anyway.
        # (could possibly be resolved by an untar() method)
        if tarinfo.type not in (DIRTYPE, SYMTYPE):
            try:
                os.utime(targetpath, (tarinfo.mtime, tarinfo.mtime))
            except (IOError, OSError) as e:
                if self.debug > 2: print("utime '%s'" % e)

        # Here we set the ownership for the file.
        # We must be logged in as root. So, we
        # look for the owner on our system, and
        # if found, give it to him, else it's ours.
        if tarinfo.type != SYMTYPE and pwd and os.getgid() == 0:
            try: g = grp.getgrnam(tarinfo.gname)[2]
            except KeyError:
                try: g = grp.getgrgid(tarinfo.gid)[2]
                except KeyError: g = os.getgid()
            try: u = pwd.getpwnam(tarinfo.uname)[2]
            except KeyError:
                try: u = pwd.getpwuid(tarinfo.uid)
                except KeyError: u = os.getuid()
            try:
                os.chown(targetpath, u, g)
            except (IOError, OSError) as e:
                if self.debug > 2: print("chown '%s'" % e)

        # Here we set the file's permissions.
        if tarinfo.type != SYMTYPE:
            try:
                os.chmod(targetpath, tarinfo.mode)
            except (IOError, OSError) as e:
                if self.debug > 2: print("chmod '%s'" % e)
    
    def writestr(self, tarinfo, data="", fileobj=None):
        """Add the string buffer `data' to the tarfile.
        File information is passed by the tarinfo object.
        fileobj is used internally, for low memory consuming copying.
        """
        if not self.fileobj: raise IOError("Cannot access closed file")
        
        # If fileobj is not given, we write `data' to the archive.
        # So, the filesize is the length of the data. If fileobj
        # is given, tarinfo.size must have already been set.
        if not fileobj: tarinfo.size = len(data)

        # First, write out the tar header.
        try: self.fileobj.seek(self.chunks[-1])
        except IOError: pass
        header = tarinfo.getheader()
        self.fileobj.write(header)
        self.offset += BLOCKSIZE

        # If there's data to follow, we append it.        
        if data:
            self.fileobj.write(data)
            blocks, remainder = divmod(tarinfo.size, BLOCKSIZE)
            if remainder > 0:
                self.fileobj.write("\0" * (BLOCKSIZE - remainder))
                blocks += 1
            self.offset += blocks * BLOCKSIZE
        elif fileobj:
            copyfileobj(fileobj, self.fileobj, tarinfo.size)
            blocks, remainder = divmod(tarinfo.size, BLOCKSIZE)
            if remainder > 0:
                self.fileobj.write("\0" * (BLOCKSIZE - remainder))
                blocks += 1
            self.offset += blocks * BLOCKSIZE

        self.members.append(tarinfo)
        self.membernames.append(tarinfo.name)
        self.chunks.append(self.offset)

    def write(self, name, arcname=None, recursive=1):
        """Add a file or a directory to the tarfile.
        Directory addition is recursive by default.
        """
        if not self.fileobj: raise IOError("Cannot access closed file")
        if self._mode == "r":
            raise IOError("Cannot write to a read-mode file")

        if not arcname: arcname = name        

        # Skip if somebody tries to archive the archive...
        if os.path.abspath(name) == os.path.abspath(self.name):
            if self.debug > 2: print(name, "(skipped)")
            return

        # Special case: The user wants to add the current working directory.
        if name == ".":
            if recursive:
                if arcname == ".": arcname = ""
                for f in os.listdir("."):
                    self.write(f, os.path.join(arcname, f))
            return

        if self.debug > 1: print(name)

        # Create a TarInfo object from the file.
        tarinfo = self.gettarinfo(name, arcname)

        # Now we must check if the strings for filename
        # and linkname fit into the posix header. (99 chars + "\0" for each)
        # If not, we must create GNUtar specific extra headers.
        # If both filename and linkname are too long,
        # the longlink is first to be written out.
        if len(tarinfo.linkname) >= LENGTH_LINK - 1:
            self._create_gnulong(tarinfo.linkname, GNUTYPE_LONGLINK)
            tarinfo.linkname = tarinfo.linkname[:LENGTH_LINK -1]
        if len(tarinfo.name) >= LENGTH_NAME - 1:
            self._create_gnulong(tarinfo.name, GNUTYPE_LONGNAME)
            tarinfo.name = tarinfo.name[:LENGTH_NAME - 1]


        # In the end, we append the tar header and data
        # to the archive. If the file is a directory
        # we recurse its subdirectories (default).
        if tarinfo.type == REGTYPE:
            addf = builtins.open(name, "rb")        
            self.writestr(tarinfo, fileobj = addf)
            addf.close()

        if tarinfo.type in (LNKTYPE, SYMTYPE, FIFOTYPE):
            tarinfo.size = 0
            self.writestr(tarinfo, "")

        if tarinfo.type == DIRTYPE:
            self.writestr(tarinfo, "")
            if recursive: 
                for f in os.listdir(name):
                    self.write(os.path.join(name, f), os.path.join(arcname, f))

    def gettarinfo(self, name, arcname=None):
        """Create a TarInfo object from an existing file named
        `name'. Optional `arcname' defines the name under which
        the file shall appear in the archive. It defaults to `name'
        """
        # Building the name of the member in the archive.
        # Backward slashes are converted to forward slashes,
        # Absolute paths are turned to relative paths.
        if not arcname: arcname = name
        arcname = normpath(arcname)
        drv, arcname = os.path.splitdrive(arcname)
        while arcname[0:1] == "/": arcname = arcname[1:]

        # Now, we are about to fill the TarInfo object with
        # information specific for the file.
        tarinfo = TarInfo()

        # Use os.stat or os.lstat, depending on platform
        # and if symlinks shall be resolved.
        if hasattr(os, "lstat") and not self.dereference:
            osstat = os.lstat
        else:
            osstat = os.stat
            
        statres = osstat(name)
        linkname = ""

        # Here we test, which file type it is.
        stmd = statres[stat.ST_MODE]
        
        if stat.S_ISREG(stmd):                  # a regular file?
            inode = (statres[stat.ST_INO], statres[stat.ST_DEV], statres[stat.ST_MTIME])
            if inode in list(self.inodes.keys()):
                # Is it a hardlink to an already
                # archived file?
                type = LNKTYPE
                linkname = self.inodes[inode]
            else:
                # The inode is added only if its valid.
                # For win32 it is always 0.
                # So always self.inodes = {}
                type = REGTYPE
                if inode[0]: self.inodes[inode] = arcname
                
        elif stat.S_ISDIR(stmd):                # a directory?
            type = DIRTYPE
            if arcname[-1:] != "/": arcname += "/"

        elif stat.S_ISFIFO(stmd):               # a fifo?
            type = FIFOTYPE

        elif stat.S_ISLNK(stmd):                # a symlink?
            type = SYMTYPE
            linkname = os.readlink(name)

        else:
            if self.debug > 1: print("'%s' has an unsupported type" % name)
            return

        # Fill the TarInfo with all information we can get.
        #
        tarinfo.name = arcname
        tarinfo.mode = stmd
        tarinfo.uid = statres[stat.ST_UID]
        tarinfo.gid = statres[stat.ST_GID]
        tarinfo.size = statres[stat.ST_SIZE]
        tarinfo.mtime = statres[stat.ST_MTIME]
        tarinfo.type = type
        tarinfo.linkname = linkname
        if pwd: tarinfo.uname = pwd.getpwuid(tarinfo.uid)[0]
        if grp: tarinfo.gname = grp.getgrgid(tarinfo.gid)[0]

        return tarinfo        

    def getinfo(self, name):
        """Return a TarInfo object for file `name'.
        """
        # If the name is not found in the current
        # list of member's names, we force loading
        # the entire table of contents (which actually
        # does not exist).

        if name not in self.membernames and not self._loaded:
            self._load()
        if name not in self.membernames:
            raise KeyError("filename `%s' not found in tar archive" % name)

        return self._getmember(name)
        # DEL
        #for i in xrange(len(self.membernames) - 1, -1, -1):
        #    if name == self.membernames[i]:
        #        return self.members[i]

    def _getmember(self, name, tarinfo=None):
        """Find an archive member by name from bottom
        to top.
        If tarinfo is given, it is used as the starting point.
        """
        if not tarinfo:
            end = len(self.members)
        else:
            end = self.members.index(tarinfo)
            
        for i in range(end - 1, -1, -1):
            if name == self.membernames[i]:
                return self.members[i]
    
    def list(self):
        """Print a formatted listing of tarfile's contents to stdout.
        """
        print("%-46s %19s %12s" % ("File Name", "Modified    ", "Size"))
        for tarinfo in self.getmembers():
            date = "%d-%02d-%02d %02d:%02d:%02d" \
                   % time.gmtime(tarinfo.mtime)[:6]

            name = tarinfo.name
            if len(name) > 46: name = name[:20] + "[...]" + name[-21:]

            size = str(tarinfo.size)
            if tarinfo.type not in REGULAR_TYPES:
                size = ""

            print("%-46s %s %12s" % (name, date, size))

    def close(self):
        """Close the TarFile Object and do some cleanup.
        """
        if self.fileobj:
            if self._mode in "aw":
                # fill up the end with zero-blocks
                # (like option -b20 for tar does)
                blocks, remainder = divmod(self.offset, RECORDSIZE)
                if remainder > 0:
                    self.fileobj.write("\0" * (RECORDSIZE - remainder))

            if not self._extfileobj:
                self.fileobj.close()
            self.fileobj = None
# class TarFile

#---------------------------------------------
# zipfile compatible TarFile class
#
# for details consult zipfile's documentation
#---------------------------------------------
TAR_PLAIN = 0           # zipfile.ZIP_STORED
TAR_GZIPPED = 8         # zipfile.ZIP_DEFLATED
class TarFileCompat:
    """TarFile class in accordance with standard module zipfile.
    """
    def __init__(self, file, mode="r", compression=TAR_PLAIN):
        if compression == TAR_PLAIN:
            self.tarfile = open(file, mode)
        elif compression == TAR_GZIPPED:
            self.tarfile = gzopen(file, mode)
        else:
            raise IOError("unknown compression constant")
        if mode[0:1] == "r":
            import time
            members = self.tarfile.getmembers()
            for i in range(len(members)):
                m = members[i]
                m.filename = m.name
                m.file_size = m.size
                m.date_time = time.gmtime(m.mtime)[:6]
    def namelist(self):
        return [m.name for m in self.infolist()]
    def infolist(self):
        return [m for m in self.tarfile.getmembers() if m.type in REGULAR_TYPES]
    def printdir(self):
        self.tarfile.list()
    def testzip(self): return
    def getinfo(self, name):
        return self.tarfile.getinfo(name)
    def read(self, name):
        return self.tarfile.readstr(self.tarfile.getinfo(name))
    def write(self, filename, arcname=None, compress_type=None):
        self.tarfile.write(filename, arcname)
    def writestr(self, zinfo, bytes):
        import calendar
        zinfo.name = zinfo.filename
        zinfo.size = zinfo.file_size
        zinfo.mtime = calendar.timegm(zinfo.date_time)
        self.tarfile.writestr(zinfo, bytes)
    def close(self):
        self.tarfile.close()
#class TarFileCompat    

class TarIter:
    """Iterator Class. Enables the use of TarFile
    in a for statement. This needs Python >= 2.2.
    
    for tarinfo in TarFile(...):
        suite...
    """
    def __init__(self, tarfile):
        """Construct TarIter object.
        """
        self.tarfile = tarfile
    def __iter__(self):
        """Return iteration object, in this case self.
        """
        return self
    def __next__(self):
        """Return the next item using TarFile's next() method.
        When all members have been read, set TarFile as _loaded.
        """
        tarinfo = next(self.tarfile)
        if not tarinfo:
            self.tarfile._loaded = 1
            raise StopIteration
        return tarinfo
# class TarIter

if __name__ == "__main__":
    # a "light-weight" implementation of GNUtar ;-)
    usage = """
Usage: %s [options] [files]

-h      display this help message
-c      create a tarfile
-r      append to an existing archive
-x      extract archive
-t      list archive contents
-f FILENAME
        use archive FILENAME, else STDOUT (-c)
-z      filter archive through gzip
-C DIRNAME
        with opt -x:     extract to directory DIRNAME
        with opt -c, -r: put files to archive under DIRNAME
-q      quiet

wildcards *, ?, [seq], [!seq] are accepted.
    """ % sys.argv[0]
    
    import getopt, glob
    try:
        opts, args = getopt.getopt(sys.argv[1:], "htcrzxf:C:q")
    except getopt.GetoptError as e:
        print()
        print("ERROR:", e)
        print(usage)
        sys.exit(0)
    
    file = None
    mode = None
    dir = ""
    comp = 0
    debug = 3
    for o, a in opts:
        if o == "-t": mode = "l"        # list archive
        if o == "-c": mode = "w"        # write to archive
        if o == "-r": mode = "a"        # append to archive
        if o == "-x": mode = "r"        # extract from archive
        if o == "-f": file = a          # specify filename else use stdout
        if o == "-C": dir = a           # change to dir
        if o == "-z": comp = 1          # filter through gzip
        if o == "-q": debug = 0         # quiet mode
        if o == "-h":                   # help message
            print(usage)
            sys.exit(0)

    if not mode:
        print(usage)
        sys.exit(0)

    if comp:
        func = gzopen
    else:
        func = open
    
    if not file:
        if mode != "w":
            print(usage)
            sys.exit(0)
        debug = 0

        # If under Win32, set stdout to binary.
        try:
            import msvcrt
            msvcrt.setmode(1, os.O_BINARY)
        except: pass

        tarfile = func("sys.stdout.tar", mode, sys.stdout)
    else:
        if mode == "l":
            tarfile = func(file, "r")
        else:
            tarfile = func(file, mode)
        
    
    tarfile.debug = debug

    if mode == "r":
        while 1:
            tarinfo = next(tarfile)
            if not tarinfo: break
            tarfile.read(tarinfo, dir)
            
    elif mode == "l":
        tarfile.list()
    else:
        for arg in args:
            files = glob.glob(arg)
            for f in files:
                tarfile.write(f, dir)

    tarfile.close()                
