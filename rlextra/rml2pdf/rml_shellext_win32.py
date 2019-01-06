# rml_shellext_win32
# adapted from Adam Twardoch's script in fonttools which
# does exactly the analogous thing!  Thanks,  Adam

# This script installs a Windows 9x/NT shell extension for RML files.
# After installing it, click with the right mouse button on an RML file
# and choose "Convert RML to PDF" from the context menu to run rml2pdf
# over it. 
# or "Convert all RML to PDF" to convert all RML files in the current directory. 


import sys, os, string, tempfile
def run():
  if not sys.platform == 'win32':
    print('This program is for Win32 (Windows 9x/NT) systems only.')
    sys.exit(2)

  # get the folder where Python resides.  assume rml2pdf.exe is here
  pythondir = sys.exec_prefix

  # escape backslashes (regedit.exe requires that the reg files are formatted that way)
  pythondir = string.replace(pythondir, '\\', '\\\\')

  # Prepare the text to write to the temporary reg file
  regtext = r"""REGEDIT4


  [HKEY_CLASSES_ROOT\.rml]
  @="rmlfile"

  [HKEY_CLASSES_ROOT\rmlfile]
  @="RML Document"

  [HKEY_CLASSES_ROOT\rmlfile\shell]
  @=""

  [HKEY_CLASSES_ROOT\rmlfile\shell\Convert current RML to PDF]
  @="Convert current RML to PDF"

  [HKEY_CLASSES_ROOT\rmlfile\shell\Convert current RML to PDF\command]
  @="\"%(pythondir)s\\rml2pdf.exe\"  \"%%1\""

  """ % locals()


  # Create the temporary reg file which will be joined into the Windows registry
  reg_file_name = os.path.join(os.path.dirname(tempfile.mktemp()), "~rmltemp.reg")
  reg_file = open(reg_file_name, "w")
  reg_file.write(regtext)
  reg_file.close()

  # Join the temporary reg file into the Windows registry
  execline = '%windir%\\regedit.exe ' + reg_file_name

  file = os.popen(execline)
  output = ""
  while 1:
    chunk = file.read(1000)
    if not chunk:
      break
      output = output + chunk

  print(output)

  os.remove(reg_file_name)

if __name__=='__main__':
  run()