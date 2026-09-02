import numpy as np, math, sys
from fractions import Fraction as F
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit
from verify_small import parse_digits
N=6
pats=["11,11|23,24","11,12|23,44","11,12|33,44","11,22|12,12","11,22|34,34",
      "12,12|34,56","12,13|14,56","12,13|24,56","12,34|13,56"]
printed=[F(1,45),F(-2,45),F(1,90),F(2,15),F(1,180),F(1,720),F(1,180),F(-1,180),F(-1,360)]
T=40
rng=np.random.default_rng(999)
X=rng.integers(-50,50,size=(N,T)).astype(np.int64)
P=prep(N); tot=[F(0)]*T
for coef,pat in zip(printed,pats):
    L,R=parse_digits(pat)
    used=sorted(set([a for p in L+R for a in p])); m=len(used)
    stab=orbit_data(P,L,R,N); S,_=eval_orbit(P,L,R,X,stab,None)
    for t in range(T): tot[t]+=coef*F(int(S[t]),math.factorial(N-m))
tgt=[2*int(X[:,t].max()) for t in range(T)]
print("REPAIRED Thm 3.3 (P69 -> [11,22|34,34]) exact on",T,"random points:",all(tot[t]==tgt[t] for t in range(T)))
