__all__ = ('solve',)
def solve(func, dfunc, target, x=1.0, precision=1e-008, maxIterations=100, failHard=1):
    """Finds x such that f(x)==target.
    Given an equation, 
        f(x) = 0
    and an initial approximation, x(0),
    in Newton's method a better approximation is given by: 
        x(i+1) = x(i) - f(x(i)) / f'(x(i))
    where f'(x) is the first derivative of f, df/dx.
    """
    iters = 0
    bf = None

    while iters<maxIterations:
        d = func(x)-target
        ad = abs(d)
        if bf is None or ad<bf:
            b = x
            bf = ad
        # if solved to RELATIVE precision, return now
        if ad/max(abs(target),1.0)<precision: return x
        x -= d/dfunc(x)
        iters += 1

    if failHard:
        raise ValueError("Failed to converge after %s tries\nbest abs error=%r at x=%r" % (maxIterations,bf,b))
    return b

def _test():
    def f(x):
        return x*x
    def df(x):
        return 2*x
    for target in [3,2,1]:
        x = solve(f,df,target)
        print('target=%f x=%f f(x)=%f' % (target,x,f(x)))

if __name__=='__main__': #noruntests
    _test()
