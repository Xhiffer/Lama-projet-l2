#Copyright ReportLab Europe Ltd. 2000-2017
#see license.txt for license details
__version__='3.3.0'

def strip(s):
	#general stripping for dates, ninos, numbers etc.
	s=str(s).upper()
	s=s.replace(' ', '')
	s=s.replace('.', '')
	s=s.replace('-', '')
	s=s.replace('/', '')
	s=s.replace(',', '')
	return s
	
def postcodeFormatter(s, singleSpace=0, fieldWidth=7):
	"""Returns postcode with whitespace normalised.

	By default, pad to fixed-width (fieldWidth chars -- usually 7; this is
	increased if there's not enough space -- e.g. to 8 chars if it's an
	eight-character postcode).  If singleSpace (boolean), format with
	single space.

	8 character postcodes may be mythical, but one major customer asked for them...

>>> from rmlutils import postcodeFormatter as pf
>>> pf("N1 3PQ")
'N1  3PQ'
>>> pf("N12 3PQ")
'N12 3PQ'
>>> pf("SW19 3PQ")
'SW193PQ'
>>> pf("SW19 5ERS")
'SW195ERS'
>>> pf(" S  W19 3   PQ")
'SW193PQ'
>>> pf(" N  1 3   P  Q  ")
'N1  3PQ'
>>> pf("N13PQ")
'N1  3PQ'
>>> pf("SW19 5ERS", fieldWidth=1)
'SW195ERS'
>>> pf("SW19 5ERS", fieldWidth=8)
'SW195ERS'
>>> pf("SW19 5ERS", fieldWidth=9)
'SW19 5ERS'

>>> pf("N1 3PQ", singleSpace=1)
'N1 3PQ'
>>> pf("N12 3PQ", singleSpace=1)
'N12 3PQ'
>>> pf("SW19 5ER", singleSpace=1)
'SW19 5ER'
>>> pf("SW19 5ERS", singleSpace=1)
'SW19 5ERS'
>>> pf("S  W19 5ER ", singleSpace=1)
'SW19 5ER'

"""
	s = strip(str(s))
	nrChars = len(s)
	fieldWidth = max(fieldWidth, nrChars)  # expand field width if necessary
	nrSpaces = fieldWidth - nrChars  # there are fieldWidth characters in which to draw postcode on forms
	if len(s) == 8:
		lenFirstChunk = 4
	else:
		# second chunk (the chars after the whitespace) is 3 chars long
		lenFirstChunk = len(s) - 3
	s = s[:lenFirstChunk] + (singleSpace and ' ' or ' '*nrSpaces) + s[lenFirstChunk:]
	return s

