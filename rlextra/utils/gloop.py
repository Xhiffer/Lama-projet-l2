#copyright ReportLab Europe Limited. 2000-2016
#see license.txt for license details
__version__='3.3.0'
from zlib import compress, decompress
from rlextra.utils.rc4 import RC4
from reportlab.pdfbase.pdfutils import _wrap, _AsciiHexEncode, _AsciiHexDecode
from reportlab.lib.rl_accel import asciiBase85Encode, asciiBase85Decode
import time

class Gloop(RC4):
	def reset(self):
		if self._key: RC4.reset(self)

	def encode(self,S):
		self.__setKey(time.time())
		return _wrap(self._aenc(compress(RC4.encode(self,S+self.__fwd))))

	def __decode(self,S,now,R):
		m = now[4]
		l = len(self.__fwd)
		for s in R:
			now[4] = s+m
			self.__setKey(time.mktime(now))
			D = RC4.encode(self,S)
			if D[-l:]==self.__fwd: return D[:-l]

	def __setKey(self,now):
		self._key = time.strftime('%H%M%d%m%Y',time.gmtime(now))+self.__fwd
		self.reset()

	def decode(self,S,now=None):
		if now is None: now = list(time.gmtime(time.time()))
		S = ''.join(S.split(S))
		I = decompress(self._adec(S))
		D = self.__decode(I,now[:],range(0,-66,-1))
		if not D:
			D = self.__decode(I,now[:],range(1,66))
			if not D: raise ValueError("Can't decode message")
		return D

	def __init__(self,aenc='base64'):
		if aenc=='base64':
			from base64 import encodestring, decodestring
			self._aenc, self._adec = encodestring, decodestring
		elif aenc=='base85':
			self._aenc, self._adec = asciiBase85Encode, asciiBase85Decode
		elif aenc=='hex':
			self._aenc, self._adec = _AsciiHexEncode, _AsciiHexDecode
		else:
			raise ValueError('bad value for aenc=%s' % aenc) 
		from .rc4 import _TESTS
		self.__fwd = _TESTS[-1]['output'][:16]

if '__main__'==__name__:
	import sys
	def _usage():
		print('use gloop.py [--hex] [--test | --encode < plaintextfile | --decode <cipherfile]')
	if len(sys.argv):
		from .buildutils import getFlag
		aenc = ('base85','hex')
		if getFlag('--base64'): aenc = 'base64'
		elif getFlag('--hex'): aenc = 'hex'
		elif getFlag('--base85'): aenc = 'base85'
		else: aenc='base64'
		if getFlag('--encode'):
			print(Gloop(aenc).encode(sys.stdin.read()))
		elif getFlag('--decode'):
			print(Gloop(aenc).decode(sys.stdin.read()))
		elif getFlag('--test'):
			P='Hello World'
			C = Gloop(aenc=aenc).encode(P)
			D = Gloop(aenc=aenc).decode(C) 
			print(C, D, D==P and 'ok' or 'bad')
		else:
			_usage()
	else:
		_usage()
