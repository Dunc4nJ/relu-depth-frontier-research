import itertools, math
from functools import lru_cache
from sympy.utilities.iterables import partitions as sympart

def cycle_type_on_pairs(lam, N):
    """lam: list of cycle lengths of sigma on {1..N}. Return dict cyclen->count for
    induced action on unordered pairs {a,b} with a<=b (including a==b)."""
    from math import gcd
    cnt={}
    def add(l,c):
        cnt[l]=cnt.get(l,0)+c
    # pairs inside one cycle of length L (incl diagonal)
    for L in lam:
        # action on unordered pairs from a single L-cycle, including {a,a}
        # orbits: diagonal {a,a} -> one cycle of length L
        add(L,1)
        # non-diagonal pairs within the cycle: {a, a+d}, d=1..L-1 mod, unordered
        # orbit of {a,a+d} has length L, except when L even and d=L/2 -> length L/2
        if L%2==0:
            for d in range(1,L//2):
                add(L,1)
            add(L//2,1)
        else:
            for d in range(1,(L+1)//2):
                add(L,1)
    # pairs across two different cycles L1,L2
    for i in range(len(lam)):
        for j in range(i+1,len(lam)):
            L1,L2=lam[i],lam[j]
            g=math.gcd(L1,L2); l=L1*L2//g
            add(l,g)
    return cnt

def F_side(cnt,k):
    """number of sigma-invariant multisets of size k from the pair-set with cycle counts cnt"""
    poly=[0]*(k+1); poly[0]=1
    for L,c in cnt.items():
        for _ in range(c):
            # multiply by 1/(1-t^L)
            for i in range(L,k+1):
                poly[i]+=poly[i-L]
    return poly[k]

def square_type(lam):
    out=[]
    for L in lam:
        if L%2==0: out+= [L//2,L//2]
        else: out.append(L)
    return out

def orbits(N,k):
    total=0
    for p in sympart(N):
        lam=[]
        for part,mult in p.items(): lam+= [part]*mult
        # z_lambda
        z=1
        for part,mult in p.items(): z*= (part**mult)*math.factorial(mult)
        c1=cycle_type_on_pairs(lam,N)
        f1=F_side(c1,k)
        lam2=square_type(lam)
        c2=cycle_type_on_pairs(lam2,N)
        f2=F_side(c2,k)
        total+= (f1*f1+f2)//2 / z if False else 0
        total+= __import__('fractions').Fraction(f1*f1+f2,2*z)
    assert total.denominator==1, total
    return int(total)

if __name__=="__main__":
    for N,k in [(5,2),(6,2),(7,3),(8,3),(8,4),(9,4),(10,4),(11,4),(11,5),(9,5),(10,5)]:
        print(f"N={N:2d} k={k}: |P/Sigma_N| = {orbits(N,k):,}")
