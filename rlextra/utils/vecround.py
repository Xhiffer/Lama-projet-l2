from functools import reduce
#Original C version by R. G. Becker 1980
def vecRound(v, s, m):
	'''
	Given the list of numbers v,
	return a list, r, such that
	sum r[i] == s

	and r = m*v with a small number of deviations
	'''
	
	n = len(v)
	if not m: return (n*[0])[:]
	vs = 0
	r = []
	for i in v:
		ir = int(i*m+0.5)
		r.append(float(ir/m))
		vs += ir
	if vs==s: return r
	rincr = 1.0/m
	incr = 1
	if vs<s:
		xs = r
		rs = v
	else:
		xs = v
		rs = r
		incr = -incr
		rincr = -rincr

	while vs!=s:
		o = 10*abs(s)			# infinity
		for i in range(n):
			t = float(xs[i]-rs[i])
			if t<=o:
				if o==t:
					if abs(v[i])>abs(v[j]): j = i
				else:
					j = i
					o = t
		vs += incr
		r[j] += rincr
	return r

def _vecRound(v, s):
	'''
	Given the list of numbers v,
	return a list, r, such that
	sum(r) == int(s+0.5) and r is close to v
	'''
	if type(s) is float: s = int(s+0.5)
	r = [int(i+0.5) for i in v]
	vs = sum(r)
	if vs==s: return r
	if vs<s:
		incr = 1
		xs = r
		rs = v
	else:
		xs = v
		rs = r
		incr = -1

	inf = 10*abs(s)
	N = range(len(v))
	while vs!=s:
		o = inf
		for i in N:
			t = xs[i]-rs[i]
			if t<=o:
				if o==t:
					if abs(v[i])>abs(v[j]): j = i
				else:
					j = i
					o = t
		vs += incr
		r[j] += incr
	return r

def dpVecFormat(v,s,dp,fmt='string'):
	m = 10**dp
	I = _vecRound([_*m for _ in v],s*m)
	if fmt=='string':
		if dp==0: return list(map(str,I))
		sfmt = '%%s.%%0%dd' % dp
		return [sfmt % divmod(int(i),m) for i in I]
	elif fmt=='value':
		if dp==0: return I
		m = float(m)
		return [i/m for i in I]
	elif fmt=='pair':
		return [divmod(int(i),m) for i in I]
	else:
		return I

def test():
	v=[9350,9350,9350,18700,39750,18700]
	import operator
	sum = float(reduce(operator.add,v))
	percen = list(map(lambda x,sum=sum: 100*x/sum, v))
	print(v)
	print(percen)
	print(vecRound(percen,100,1))
	print(vecRound(percen,100,10))
	print(vecRound(percen,100,100))
	print(dpVecFormat([18.2,48.0,33.7],100,1))
	print(dpVecFormat([1.2,5.7,2.8,8.5],18.2,1))
	print(dpVecFormat([9.0,2.7,1.8,34.5],48.1,1))
	print(dpVecFormat([6.6,12.2,9.6,5.4],33.7,1))

if __name__=='__main__':
	test()
