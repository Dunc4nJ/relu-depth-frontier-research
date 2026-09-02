import json, itertools, numpy as np
from fractions import Fraction as F
import sys

SP="/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad/"
tabs=json.load(open(SP+"wb_tables.json"))

def perms_arr(N):
    P=np.array(list(itertools.permutations(range(N))),dtype=np.int64)
    return P

def prep(N):
    return perms_arr(N)

def sidekey(P,pairs,N):
    B=N*N
    codes=[]
    for (a,b) in pairs:
        u=P[:,a]; v=P[:,b]
        mn=np.minimum(u,v); mx=np.maximum(u,v)
        codes.append(mn*N+mx)
    C=np.stack(codes,axis=1)
    C.sort(axis=1)
    key=np.zeros(P.shape[0],dtype=np.int64)
    for j in range(C.shape[1]):
        key=key*B+C[:,j]
    return key

def orbit_data(P,L,R,N):
    kL=sidekey(P,L,N); kR=sidekey(P,R,N)
    lo=np.minimum(kL,kR); hi=np.maximum(kL,kR)
    B=N*N; k=len(L)
    key=lo*(B**k)+hi
    idkey=key[0]  # identity permutation is first in itertools.permutations
    stab=int((key==idkey).sum())
    return stab

def eval_orbit(P,L,R,X,stab,mode):
    # X: (N,T) integer test points (arbitrary, not necessarily sorted)
    valL=np.zeros((P.shape[0],X.shape[1]),dtype=np.int64)
    valR=np.zeros_like(valL)
    for (a,b) in L:
        valL+=np.maximum(X[P[:,a]],X[P[:,b]])
    for (a,b) in R:
        valR+=np.maximum(X[P[:,a]],X[P[:,b]])
    S=np.maximum(valL,valR).sum(axis=0)
    return S,stab

def letters_to_pairs(side,letters):
    return [(letters[s[0]],letters[s[1]]) for s in side]

def run(N,k,entries,label,T=6,seed=0):
    rng=np.random.default_rng(seed)
    X=rng.integers(-20,20,size=(N,T)).astype(np.int64)
    P=prep(N)
    tot_by_conv={"class":[F(0)]*T,"perm":[F(0)]*T,"inj":[F(0)]*T}
    for idx,(sign,num,den,l,r) in entries:
        used=sorted(set("".join(l)+"".join(r)))
        letters={c:i for i,c in enumerate(used)}
        m=len(used)
        L=letters_to_pairs(l,letters); R=letters_to_pairs(r,letters)
        stab=orbit_data(P,L,R,N)
        S,_=eval_orbit(P,L,R,X,stab,None)
        c=F(sign*num,den)
        import math
        for t in range(T):
            v=int(S[t])
            tot_by_conv["class"][t]+= c*F(v,stab)
            tot_by_conv["perm"][t] += c*v
            tot_by_conv["inj"][t]  += c*F(v,math.factorial(N-m))
    target=[2*int(X[:,t].max()) for t in range(T)]
    print(f"--- {label} (N={N},k={k},{len(entries)} orbit terms) test pts T={T}")
    for name,tot in tot_by_conv.items():
        ok=all(tot[t]==target[t] for t in range(T))
        print(f"  convention={name:6s} match={ok}  vals={[str(v) for v in tot[:3]]} target={target[:3]}")
    return tot_by_conv,target

if __name__=="__main__":
    which=sys.argv[1]
    if which=="7":
        e=[(int(j),tuple(v)) for j,v in tabs["max7"].items()]
        e.sort()
        run(7,3,[(j,v) for j,v in e],"MAX7 Thm 4.1")
    elif which=="8":
        e=[(int(j),tuple(v)) for j,v in tabs["max8"].items()]
        e.sort()
        run(8,4,[(j,v) for j,v in e],"MAX8 Thm 5.1",T=4)
