#copyright ReportLab Inc. 2001-2016
#see license.txt for license details
This is an evaluation copy of Report Markup Language.

Report Markup Language is ReportLab's easy-to-use
enterprise reporting solution.  It consists of:
 - an XML markup language called "Report Markup Language" 
   (RML) which lets you define the precise appearance
   of a printed document
 - a 'black box' compiled python script, rml2pdf.pyc, which
   converts such documents into Adobe's Portable Document Format.

This does NOT use Adobe's Acrobat tools - it is totally
standalone and directly handles rendering, page layout,
image embedding, and direct construction of PDF files.

We are currently shipping an evaluation version in the form of a 
compiled python '.pyc' file.

This version contains all features of the full version but draws
a message on every page you create so that you cannot use it in
a production environment. If you decide to pay for the full
version, you can keep your existing setup and copy the new
license file in to place that we will generate for you.

RML2PDF can run on all common platforms and be accessed via
many protocols and techniques including COM, CORBA, Java and
C bindings and a variety of scripting languages.



Installation
============
The zip or tar file contains:
   rml2pdf.pyc - the pre-compiled python script
   rml_1_0.dtd - the Document Type Declaration
   doc/rml_user_guide.rml - the manual in RML source format,
          plus numbered RML files to accompany the user guide
   demos/  - miscellaneous demos.
   test/ - miscellaneous tests 

Extract the archive file into any location. It will create a 
subdirectory called 'rml2pdf', so you can unzip/untar directly
into /tmp/ on Unix or C:\ or C:\temp on Windows if you wish.

There are no registry entries or external dependencies; when you
delete it, it has gone forever.


Generating the Documentation
============================
Our manual is "just another report" so we start by generating
it from the source file!

cd to the doc directory from a terminal or DOS prompt and enter the 
following:
On windows (assuming you unzipped to C:):
 C:\> cd rml2pdf\doc
 C:\rml2pdf\doc> python gen_rmluserguide.py 
Unix-based (assuming you extracted to /tmp/):
 $ cd /tmp/rml2pdf/doc
 $ python gen_rmluserguide.py

After a few seconds the script will finish and return you to the
command-line. You will notice a new file has been created in the
current directory called 'rml2pdf-userguide.pdf', you have just
used RML to build your own copy of the documentation. Go ahead and
open the PDF in your favourite PDF viewer

These documents all assume that you want a page size of 
"A4". If you want to change this to "letter", look for the 
following line in the file rml_user_guide.rml:
<template pageSize="(595, 842)"

and change it to this:
<template pageSize="(8.5in, 11in)" 

If you need more information about the issue of page sizes, 
look in the section "Template and pageTemplate in more detail" 
in the RML User Guide.


File Locations
==============
There are three directory locations of interest:
(a) where the rml2pdf script and DTD live
(b) where you run the command from
(c) where the RML document lives

The rml2pdf script can be anywhere on your system. We suggest
putting it in a directory on the system path so you can type
'rml2pdf' in any directory. The DTD must be in the same
directory as the rml2pdf script. RML documents should not
include directory path names in the DOCTYPE declaration; only
the form

   <!DOCTYPE document SYSTEM "rml_1_0.dtd"> 
is allowed.  This saves you from copying the DTD all over your
hard disk.

Where you run the command from is intended to have no effect.

The output file is specified in the XML as follows:
   <document filename="sample.pdf">
The PDF will be written in the same directory as the document,
not the running process.  If you include a relative directory,
it will be relative to the document.  So you can do:
   <document filename="..\output\sample.pdf">

You can also give an absolute location:
   <document filename="C:\output\sample.pdf">

These choices were made in order to offer the 'least surprise'
to web designers.


Licensing
=========
RML2PDF is an enterprise-level product intended to be used on 
servers as part of an XML workflow.  This is an evaluation
and it prints a warning across the bottom of every page.

Licensed customers will receive a license file causing the
message to disappear, as well as other tools and materials
as part of the package.

For more information go to http://www.reportlab.com/ or
email info@reportlab.com.


