import numpy as np, itertools, math, sys
from fractions import Fraction as F
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit
from verify_small import parse_digits

N=6
pats=["11,11|23,24","11,12|23,44","11,12|33,44","11,22|12,12","11,22|34,35",
      "12,12|34,56","12,13|14,56","12,13|24,56","12,34|13,56"]
names=["P15","P44","P47","P56","P69","P118","P130","P135","P142"]
printed=[F(1,45),F(-2,45),F(1,90),F(2,15),F(1,180),F(1,720),F(1,180),F(-1,180),F(-1,360)]
T=40
rng=np.random.default_rng(7)
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
# exact gaussian elimination least-norm: solve A c = b, A is T x 9
A=[[cols[j][i] for j in range(9)] for i in range(T)]
# row reduce augmented
M=[row[:]+[b[i]] for i,row in enumerate(A)]
rows=len(M); ncol=9
piv=[]; r=0
for c in range(ncol):
    pr=None
    for i in range(r,rows):
        if M[i][c]!=0: pr=i;break
    if pr is None: continue
    M[r],M[pr]=M[pr],M[r]
    pv=M[r][c]
    M[r]=[v/pv for v in M[r]]
    for i in range(rows):
        if i!=r and M[i][c]!=0:
            f=M[i][c]
            M[i]=[M[i][j]-f*M[r][j] for j in range(ncol+1)]
    piv.append(c); r+=1
    if r==rows: break
incons=[i for i in range(r,rows) if M[i][ncol]!=0 and all(M[i][j]==0 for j in range(ncol))]
print("rank",r,"inconsistent rows:",len(incons))
if not incons:
    sol=[F(0)]*ncol
    for i,c in enumerate(piv): sol[c]=M[i][ncol]
    print("free vars:",[c for c in range(ncol) if c not in piv])
    for n,s,p in zip(names,sol,printed):
        print(f"  {n:5s} solved={s}  printed={p}  {'MATCH' if s==p else '<<< DIFF'}")
# also check printed residual per point
res=[sum(printed[j]*cols[j][i] for j in range(9))-b[i] for i in range(T)]
print("printed residuals (first 5):",[str(x) for x in res[:5]])
