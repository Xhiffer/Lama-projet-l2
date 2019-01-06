#copyright ReportLab Europe Ltd. 2000-2016
#see license.txt for license details
__version__='3.3.0'
"""Removes all files matching a given pattern (e.g. .pyc) under directory"""

import sys, os
from fnmatch import fnmatch

def run(D,P):
	"Remove all files matching P (e.g. '*.pyc') under directory D"
	L = []
	aL = L.append
	pjoin = os.path.join
	for root, dirs, files in os.walk(D):
		for fn in files:
			for p in P:
				if fnmatch(n, p):
					aL(pjoin(root,fn))
					break
	map(os.remove,L)

if __name__=='__main__':
	D = '.'
	P = ('*.pyc',)
	n = len(sys.argv)
	if n>1:
		D = sys.argv[1]
		if n>2: P = sys.argv[2:]
	run(D,P)
