import numpy as np, math, sys, itertools
from fractions import Fraction as F
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit
from verify_small import parse_digits
from orbits import all_orbits
N=6
pats=["11,11|23,24","11,12|23,44","11,12|33,44","11,22|12,12","11,22|34,35",
      "12,12|34,56","12,13|14,56","12,13|24,56","12,34|13,56"]
names=["P15","P44","P47","P56","P69","P118","P130","P135","P142"]
printed=[F(1,45),F(-2,45),F(1,90),F(2,15),F(1,180),F(1,720),F(1,180),F(-1,180),F(-1,360)]
T=25
rng=np.random.default_rng(101)
X=rng.integers(-30,30,size=(N,T)).astype(np.int64)
P=prep(N)
def col_of(L,R):
    used=sorted(set([a for p in list(L)+list(R) for a in p])); m=len(used)
    stab=orbit_data(P,list(L),list(R),N)
    S,_=eval_orbit(P,list(L),list(R),X,stab,None)
    return [F(int(S[t]),math.factorial(N-m)) for t in range(T)]
cols=[]
for pat in pats:
    L,R=parse_digits(pat); cols.append(col_of(L,R))
b=[F(2*int(X[:,t].max())) for t in range(T)]
_,reps=all_orbits(N,2)
allcols=[(c,col_of(c[0],c[1])) for c,_ in reps]
found=[]
for j in range(9):
    resid=[b[i]-sum(printed[q]*cols[q][i] for q in range(9) if q!=j) for i in range(T)]
    tgt=[r/printed[j] for r in resid]
    for c,col in allcols:
        if col==tgt:
            found.append((names[j],c))
print("single-pattern repairs found:",len(found))
for n,c in found:
    print("  replace",n,"by",c)
