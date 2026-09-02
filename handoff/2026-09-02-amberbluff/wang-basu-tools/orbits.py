import itertools, sys, math
from fractions import Fraction as F
import numpy as np
sys.path.insert(0,"/home/ubuntu/.cache/tmp/claude-1000/-data-projects-relu-depth-frontier-research/e3c7772e-be35-41c0-9f1a-451dc7cbd45b/scratchpad")
from verify_wb import prep, orbit_data, eval_orbit

def canon(L,R):
    l=tuple(sorted(tuple(sorted(p)) for p in L))
    r=tuple(sorted(tuple(sorted(p)) for p in R))
    return (l,r) if l<=r else (r,l)

def all_orbits(N,k):
    pairs=[(a,b) for a in range(N) for b in range(a,N)]
    sides=list(itertools.combinations_with_replacement(pairs,k))
    classes=set()
    for i,L in enumerate(sides):
        for R in sides[i:]:
            classes.add(canon(list(L),list(R)))
    perms=list(itertools.permutations(range(N)))
    seen=set(); reps=[]
    for c in sorted(classes):
        if c in seen: continue
        orb=set()
        for s in perms:
            L=[(s[a],s[b]) for a,b in c[0]]
            R=[(s[a],s[b]) for a,b in c[1]]
            orb.add(canon(L,R))
        seen|=orb
        reps.append((c,len(orb)))
    return len(classes),reps

for N,k in [(5,2),(6,2)]:
    nc,reps=all_orbits(N,k)
    print(f"N={N} k={k}: |P| (equivalence classes) = {nc}, |P/Sigma_N| (orbits) = {len(reps)}")
