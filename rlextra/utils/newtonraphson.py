__all__ = ('solve',)
def solve(func, target, x0=1.0, precision=1e-008, maxIterations=100, x1=None, failHard=1):
    """Finds x such that f(x)==target.
    To quote Newton & Raphson:  Given an equation, 
            f(x) = 0
        and an initial approximation, x(0),
        In Newton's method a better approximation is given by: 
            x(i+1) = x(i) - f(x(i)) / f'(x(i))
        where f'(x) is the first derivative of f, df/dx.
    In the Raphson adaptation we use an approximation to
    the differential which is given by
        deltaF/deltaX = (f(x+dx)-f(x))/dx
    """
    iters = 0
    f0 = func(x0)
    if failHard:
        b = x0
        bf = abs(f0-target)
    if x1 is None:
        if x0 == 0.0:
            x1 = 1.0  # otherwise a zero would kill ts
        else:
            x1 = x0 * 1.1
    while 1:
        if iters>=maxIterations:
            if failHard:
                assert iters < maxIterations, "Failed to converge after %s tries" % maxIterations
            else:
                return b
        f1 = func(x1)
        d = f1-target
        ad = abs(d)
        if failHard and ad<bf:
            b = x1
            bf = ad
        # if solved to RELATIVE precision, return now
        if ad/max(abs(target),1.0)<precision: return x1
        x2 = x1 - d/((f1-f0)/(x1-x0)) 
        x0 = x1
        f0 = f1
        x1 = x2
        iters += 1

def _test():
    def f(x):
        v = x*x
        return x<0 and -v or v
    for target in [-1, 1, 0]:
        x = solve(f,target)
        print('target=%f x=%f f(x)=%f' % (target,x,f(x)))

if __name__=='__main__': #noruntests
    _test()
