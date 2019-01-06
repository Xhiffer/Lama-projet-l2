#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
'''
RC4 Stream  ciphering
'''
__version__='3.3.0'

from reportlab.lib.arciv import ArcIV as RC4, _TESTS

if __name__=='__main__':
	i = 0
	for t in _TESTS:
		o = RC4(t['key']).encode(t['input'])
		print('Forward test %d %s!' %(i,o!=t['output'] and 'failed' or 'succeeded'))
		o = RC4(t['key']).encode(t['output'])
		print('Reverse test %d %s!' %(i,o!=t['input'] and 'failed' or 'succeeded'))
		i += 1
