'''
functions for solving the internal rate of return problem
'''
__all__=('npv','dnpv','irr')
from rlextra.utils.newton import solve as newton_solve
def npv(r,C):
    '''
    compute the net present value of the cash flows given in C assuming rate r


    >>> print('%.5f' % npv(0.1, [-100.0, 60.0, 60.0, 60.0]))
    49.21112
    '''
    r += 1.0
    return sum(c/r**t for t,c in enumerate(C))

def dnpv(r,C):
    '''
    compute d npv(r,C)/dr

    >>> dnpv(0.1, [-100.0, 60.0, 60.0, 60.0])
    -262.68697493340613
    >>> abs(dnpv(0.1, [-100.0, 60.0, 60.0, 60.0])-(npv(0.1+0.5e-8, [-100.0, 60.0, 60.0, 60.0])-npv(0.1-0.5e-8, [-100.0, 60.0, 60.0, 60.0]))/1e-8)<1e-5  #test the drivative against finite difference
    True
    '''
    r += 1.0
    return sum(-t*c/r**(t+1) for t,c in enumerate(C))

def irr(C, r=0.001, maxIterations=100, precision=1e-8, failHard=True):
    """The IRR or Internal Rate of Return is the annualized effective 
       compounded return rate which can be earned on the invested 
       capital, i.e., the yield on the investment.
       
       >>> print('%.8f' % irr([-100.0, 60.0, 60.0, 60.0]))
       0.36309654

    This function assumes unit time. To convert to other periods use the appropriate calculation.
    If C represents monthly cash flows then the result will be a monthly rate, rm. 
    The annual rate is then ry=(1+rm)*12 - 1
    """
    return newton_solve(
            lambda r,C=C: npv(r,C),         #f(r)
            lambda r,C=C: dnpv(r,C),        #f'(r)
            0,                              #we want func(r)=0
            x=r,                            #initial guess
            maxIterations=maxIterations,
            precision = precision,
            failHard = failHard,
            )

def _doctest():
    import doctest
    doctest.testmod()

if __name__ == "__main__":
    _doctest()
