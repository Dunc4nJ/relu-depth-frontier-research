import numpy as np, itertools, math
from fractions import Fraction as F
import sys
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit

def parse_digits(s):
    # "11, 11 | 11, 23"
    l,r=s.split("|")
    f=lambda t:[(int(w.strip()[0])-1,int(w.strip()[1])-1) for w in t.split(",")]
    return f(l),f(r)

def run(N,items,label,T=6,seed=1):
    rng=np.random.default_rng(seed)
    X=rng.integers(-20,20,size=(N,T)).astype(np.int64)
    P=prep(N)
    tot={"class":[F(0)]*T,"perm":[F(0)]*T,"inj":[F(0)]*T}
    for coef,pat in items:
        L,R=parse_digits(pat)
        used=sorted(set([a for p in L+R for a in p]))
        m=len(used)
        stab=orbit_data(P,L,R,N)
        S,_=eval_orbit(P,L,R,X,stab,None)
        for t in range(T):
            v=int(S[t])
            tot["class"][t]+=coef*F(v,stab)
            tot["perm"][t]+=coef*v
            tot["inj"][t]+=coef*F(v,math.factorial(N-m))
    target=[2*int(X[:,t].max()) for t in range(T)]
    print(f"--- {label}")
    for name,tv in tot.items():
        print(f"  convention={name:6s} match={all(tv[t]==target[t] for t in range(T))} vals={[str(v) for v in tv[:3]]} target={target[:3]}")

# Theorem 2.1
t21=[(F(-2,5),"11,11|11,11"),(F(1,30),"11,11|11,23"),(F(1,120),"11,11|23,45"),
     (F(1,60),"11,12|11,34"),(F(1,60),"11,12|13,45"),(F(-1,60),"11,12|23,45"),
     (F(-1,60),"11,23|12,45")]
run(5,t21,"MAX5 Theorem 2.1 (7 orbits)")
# Theorem 2.3
t23=[(F(-2,5),"11,11|11,11"),(F(1,15),"11,11|11,23"),(F(-1,40),"11,22|34,35"),
     (F(1,20),"11,23|24,25"),(F(-1,30),"11,23|25,34")]
run(5,t23,"MAX5 Theorem 2.3 (5 orbits)")
# Theorem 3.1
t31=[(F(-1,3),"11,11|11,11"),(F(1,90),"11,12|11,34"),(F(1,180),"11,12|34,56"),
     (F(-1,360),"11,22|34,56"),(F(1,180),"12,13|14,56"),(F(-1,90),"12,13|24,56"),
     (F(1,720),"12,13|45,46")]
run(6,t31,"MAX6 Theorem 3.1 (7 orbits)")
# Theorem 3.3
t33=[(F(1,45),"11,11|23,24"),(F(-2,45),"11,12|23,44"),(F(1,90),"11,12|33,44"),
     (F(2,15),"11,22|12,12"),(F(1,180),"11,22|34,35"),(F(1,720),"12,12|34,56"),
     (F(1,180),"12,13|14,56"),(F(-1,180),"12,13|24,56"),(F(-1,360),"12,34|13,56")]
run(6,t33,"MAX6 Theorem 3.3 (9 orbits)")
