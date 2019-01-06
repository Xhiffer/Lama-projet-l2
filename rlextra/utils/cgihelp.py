#cgihelp.py

"""
This centralizes a few things our CGI scripts should use to generate
pages, so that we can manage them centrally
- standard procs to draw the first page and later pages
- a routine to generate a file name
- a routine to do the 'results page'
- a routine to return the 'content frame'
"""
import sys, os, socket
from rlextra.utils import simple_doc
from reportlab.lib.units import inch
from reportlab.rl_config import defaultPageSize
from rlextra.utils.cgisupport import TimeStamp
PAGE_WIDTH, PAGE_HEIGHT = defaultPageSize
PDFOUTDIR = "../pdfout/"

class DevNull:
	def write(self, stuff):
		pass

devnull = DevNull()
OLDOUT=sys.stdout

def hide_stdout():
	sys.stdout = sys.stderr = devnull

def restore_stdout():
	sys.stdout = sys.stderr = OLDOUT

_getUniqueFileNamec = 0
def getUniqueFileName(prefix='out',suffix=None,ext='.pdf',hostname=None):
	# builds one from timestamp
	if prefix and prefix[-1]!='-': prefix += '-'
	global _getUniqueFileNamec
	_getUniqueFileNamec = _getUniqueFileNamec+1
	if hostname:
		if not isinstance(hostname,str):
			hostname = socket.gethostname()
		prefix += hostname + '-'
	return ('%s%03d' % (TimeStamp(pfx=prefix[:-1]).currentId, _getUniqueFileNamec))+(suffix or '')+ext

def getNewLocalFileName():
	"""Return a filename suitable for a new document.  Pseudo-random,
	might get changed to some indirection mechanism."""
	filename = "%s%s" % (PDFOUTDIR, getUniqueFileName())
	return filename

def getScriptName():
	return os.path.basename(sys.argv[0])

def getHttpFileName(localName):
	"""In future we might need different names, or some level
	of indirection to prevent directory reads.	This provides
	a hook.  It should return the URL starting from the site
	root to retrieve the given local file.	For now, returns
	the same string."""
	return localName

def drawFirstPage(canvas, doc):
	"""Decorator for the first page; platypus-compatible."""
	canvas.saveState()
	drawSideBar(canvas)
	canvas.setFont('Helvetica', 12)
	canvas.setFillColorRGB(0,0,0.8)
	canvas.drawString(400, 36, 'http://www.reportlab.com/')

	canvas.restoreState()

def myLaterPages(canvas, doc):

	canvas.saveState()

	drawSideBar(canvas)
	canvas.restoreState()

def drawSideBar(canvas):
	canvas.setFillColorRGB(0,0,0.8)
	canvas.rect(18, 36, 102, canvas._pagesize[1] - 72, stroke=0, fill=1)
	canvas.drawInlineImage('../htdocs/rsrc/replog.gif', 24, canvas._pagesize[1]-1.5*inch, 90, 60)
	canvas.drawInlineImage('../htdocs/rsrc/binarypaper.gif', 24, canvas._pagesize[1]-4*inch, 90, 155)

def confidential(c):
	c.saveState()
	c.rotate(55)
	c.setStrokeColorRGB(1,0.7,0.3)
	t = c.beginText(inch,1)
	t.setFont("Helvetica-BoldOblique", 80)
	t.setTextRenderMode(5) # stroke and add to path (don't need path!)
	t.textLine("ReportLab Confidential")
	c.drawText(t)
	c.restoreState()

def makeHTMLSelect(name, options, selected, size=1):
	S=['<select name="%s" size="%s">\n' % (name,size)]
	a = S.append
	for i in options:
		a(' <option')
		if isinstance(i,(list,tuple)):
			n, v = i[0:2]
			a(' value="%s"' % v)
		else:
			n = v = i
		if str(v)==str(selected):
			a(' selected')
		a('>%s</option>\n' % n)
	a('</select>')
	return ''.join(S)

RESULT_TEMPLATE = """
%(body)s
<p>
<center>
<h3>Your %(docname)s is ready!</h3>
In order to read or print the document your computer will need
<a href="http://www.adobe.com/products/acrobat/readstep.html">
Adobe Acrobat Reader Installed.
</a>
</center>
<p>
<center>
<table border bgcolor="#ffff55"><tr><td>
<b><a href="%(filename)s">Click here to download %(linkname)s%(filesize)s</a></b>
</tr></td></table>
</center>
%(form)s
%(warning)s
<center>
<h2><a href="http://www.reportlab.com">ReportLab Home</a></h2>
</center>
"""

FORM_TEMPLATE='''
<hr>
<center>
<table><tr>
<td><h1>...Or try again</h1></td>
<td>
<form action="%(script_name)s" method="post">
<input type="hidden" name="mode" value="start">
<input type="submit" value="try again">
</form>
</td>
</tr> </table>
</center>
'''

WARNING="""
<hr>
<H3>Problems viewing PDF files on the web?</h3>
<P>Many versions of Acrobat Reader include a timing bug to do with display
of PDF documents.  If you view the document 'in place' within your web
browser, you may see a blank page for a few seconds while the document
loads; then some or all of the images may not appear.  This is worse
over dialup lines and slow connections.
<P>This never occurs if you download files to your local disk, or
configure your web browser to use an external rather than in-place
Acrobat Reader.
<P><b><i>To configuring Acrobat Reader 4.0 for safe viewing</i></b>,
<ol><li>Shut down your web browsers and Acrobat Reader
<li>Start Acrobat Reader, go to
	'File | Preferences | General' and turn off the check box saying
	'Web Browser Integration'
</ol>
From now on, you should be given the option to save or open each PDF link
you click on.
"""

def formatFileSize(size,fmt="%.1f %s"):
	if size<1024:
		unit = 'B'
	elif size<1024*1024:
		unit = 'KB'
		size = size/1024.0
	else:
		unit = 'MB'
		size = size/(1024*1024.0)
	return  fmt % (size, unit)

def writeResultPage(filename, script_name=None, title="Your PDF result",
				body='', heading='',
				docname='personalized PDF document', filesize=None, linkname=None):
	"""This prints some standard output saying 'Here is the link to your file',
	and a load of dire warnings and advice about plug ins."""
	D = {}
	D["filename"] = getHttpFileName(filename)
	if linkname is None: linkname = filename
	D["linkname"] = linkname
	if script_name is not None: D['form'] = FORM_TEMPLATE % {'script_name': script_name }
	else: D['form']= ''
	D['body'] = body
	D['docname'] = docname
	D['filesize'] = filesize is not None and formatFileSize(filesize,fmt=' (%.1f %s)') or ''

	#Dire Warnings
	D['warning'] = WARNING
	return simple_doc.get_templated_HTML(	title = title,
											heading = heading,
											body = RESULT_TEMPLATE % D)
def writeQueryPage(script_name=None,
		title="Your Query", body=None, heading=None, form=None, preform=None, adobe=None, enctype=None, method="post"):
	D = {}
	if script_name is None: script_name =''
	if body is None: body = ''
	if form is None: form = ''
	if preform is None: preform = """<p>To generate a personalized PDF document, please modify the form parameters below and click the "Generate PDF" button.</p>"""
	D['script_name'] =  script_name
	D['body'] = body
	D['method'] = method
	D['form'] = form
	D['preform'] = preform
	D['adobe'] = adobe is None and ADOBE or adobe
	D['enctype'] = enctype and ' enctype="'+enctype+'"' or ''

	#Dire Warnings
	return simple_doc.get_templated_HTML(	title = title,
											heading = heading,
											body = QUERY_TEMPLATE % D)
QUERY_TEMPLATE = """
%(body)s
%(preform)s

<form action="%(script_name)s" method="%(method)s"%(enctype)s>
%(form)s
</form>
%(adobe)s
"""
ADOBE="""
<!--center-->
<p>
In order to read or print the generated document your computer will need
<a href="http://www.adobe.com/products/acrobat/readstep.html">
Adobe Acrobat Reader Installed.
</a>
<!--/center-->
<center>
<a href="http://www.reportlab.com">ReportLab Home</a>
</center>
"""
