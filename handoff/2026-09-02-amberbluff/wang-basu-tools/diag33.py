import numpy as np, math, sys, itertools
from fractions import Fraction as F
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit
from verify_small import parse_digits
N=6
pats=["11,11|23,24","11,12|23,44","11,12|33,44","11,22|12,12","11,22|34,35",
      "12,12|34,56","12,13|14,56","12,13|24,56","12,34|13,56"]
names=["P15","P44","P47","P56","P69","P118","P130","P135","P142"]
printed=[F(1,45),F(-2,45),F(1,90),F(2,15),F(1,180),F(1,720),F(1,180),F(-1,180),F(-1,360)]
T=30
rng=np.random.default_rng(11)
X=rng.integers(-30,30,size=(N,T)).astype(np.int64)
P=prep(N)
cols=[]
for pat in pats:
    L,R=parse_digits(pat)
    used=sorted(set([a for p in L+R for a in p])); m=len(used)
    stab=orbit_data(P,L,R,N)
    S,_=eval_orbit(P,L,R,X,stab,None)
    cols.append([F(int(S[t]),math.factorial(N-m)) for t in range(T)])
b=[F(2*int(X[:,t].max())) for t in range(T)]
# single-coefficient repair test
for j in range(9):
    resid=[b[i]-sum(printed[q]*cols[q][i] for q in range(9) if q!=j) for i in range(T)]
    # need c_j * cols[j][i] == resid[i] for all i
    cand=None; ok=True
    for i in range(T):
        if cols[j][i]==0:
            if resid[i]!=0: ok=False;break
            continue
        v=resid[i]/cols[j][i]
        if cand is None: cand=v
        elif cand!=v: ok=False;break
    print(f"  free {names[j]:5s}: repairable={ok} value={cand if ok else '-'} printed={printed[j]}")
# also: does dropping one orbit and solving all 8 work? (rank test)
def consistent(idx):
    M=[[cols[j][i] for j in idx]+[b[i]] for i in range(T)]
    nc=len(idx); r=0
    for c in range(nc):
        pr=None
        for i in range(r,T):
            if M[i][c]!=0: pr=i;break
        if pr is None: continue
        M[r],M[pr]=M[pr],M[r]
        pv=M[r][c]; M[r]=[v/pv for v in M[r]]
        for i in range(T):
            if i!=r and M[i][c]!=0:
                f=M[i][c]; M[i]=[M[i][q]-f*M[r][q] for q in range(nc+1)]
        r+=1
    return not any(M[i][nc]!=0 and all(M[i][q]==0 for q in range(nc)) for i in range(r,T))
print("full 9-orbit span consistent:",consistent(list(range(9))))
