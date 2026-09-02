"""Burnside count of templates (A,B) mod S_n x swap where A,B are k-edge SIMPLE
loopless graphs (sets of k distinct non-loop pairs), n=10,k=4 and n=11,k=5.
Also the loop-inclusive multiset count as a cross-check against the import audit
(216,428 for n=10; 12,179,657 for n=11)."""
import itertools, math
from collections import Counter
from fractions import Fraction

def partitions(n, I=1):
    yield (n,)
    for i in range(I, n//2 + 1):
        for p in partitions(n-i, i):
            yield (i,) + p

def cycle_type_count(part, n):
    # number of permutations with this cycle type
    c = Counter(part)
    denom = 1
    for l, m in c.items():
        denom *= (l**m) * math.factorial(m)
    return math.factorial(n) // denom

def edge_orbits(part, loops):
    """orbit lengths of g (cycle type part) on pairs; loops=True includes (i,i)."""
    cycles = []
    idx = 0
    for l in part:
        cycles.append(list(range(idx, idx+l))); idx += l
    n = idx
    perm = [0]*n
    for cyc in cycles:
        for j, v in enumerate(cyc):
            perm[v] = cyc[(j+1) % len(cyc)]
    seen = set(); orbits = []
    pairs = [(i, j) for i in range(n) for j in range(i, n) if loops or i != j]
    for p in pairs:
        if p in seen: continue
        cur = p; L = 0
        while cur not in seen:
            seen.add(cur); L += 1
            a, b = perm[cur[0]], perm[cur[1]]
            cur = (min(a,b), max(a,b))
        orbits.append(L)
    return orbits

def poly_mul(p, q, kmax):
    r = [0]*(kmax+1)
    for i, a in enumerate(p):
        if a == 0: continue
        for j, b in enumerate(q):
            if i+j > kmax: break
            r[i+j] += a*b
    return r

def fixed_count(orbits, k, multiset):
    """# of k-edge structures fixed by g: coefficient of x^k in prod over orbits."""
    p = [1] + [0]*k
    for L in orbits:
        if multiset:
            q = [1 if (i % L == 0) else 0 for i in range(k+1)]   # 1/(1-x^L)
        else:
            q = [0]*(k+1); q[0] = 1
            if L <= k: q[L] = 1                                   # 1 + x^L
        p = poly_mul(p, q, k)
    return p[k]

def g_squared_type(part):
    out = []
    for l in part:
        if l % 2 == 0: out += [l//2, l//2]
        else: out.append(l)
    return tuple(sorted(out, reverse=True))

def count_templates(n, k, loops, multiset):
    total = 0
    for part in partitions(n):
        m = cycle_type_count(part, n)
        orb = edge_orbits(part, loops)
        f = fixed_count(orb, k, multiset)
        total += m * f * f                       # (A,B) both fixed by g
        orb2 = edge_orbits(g_squared_type(part), loops)
        total += m * fixed_count(orb2, k, multiset)  # swap part: A = g^2 A, B = gA
    assert total % (2*math.factorial(n)) == 0
    return total // (2*math.factorial(n))

for n, k in [(5,2),(6,2),(7,3),(8,3),(9,4),(10,4),(11,5)]:
    ms = count_templates(n, k, loops=True, multiset=True)
    sg = count_templates(n, k, loops=False, multiset=False)
    print(f"n={n} k={k}: loop-inclusive multiset templates={ms:,}   simple loopless graph-pair templates={sg:,}")
