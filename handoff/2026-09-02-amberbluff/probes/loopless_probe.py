"""Exploratory probe (unregistered): is MAX_n in the span of the LOOPLESS SIMPLE
k-edge graph-pair Rueß templates, k = floor((n-1)/2)?  Independent reimplementation.

Column semantics (matches upstream verifier conventions):
  F_{A,B}|_C = sum_sigma max(l_{sigma A}, l_{sigma B})
  = linear part + sum over retained primitive hinge directions of coeff * ReLU(d.x)
Retained hinge = primitive zero-sum d with mixed-sign proper prefix sums, oriented so
the lexicographically larger of (a,b) minus the smaller (first nonzero entry > 0).

Usage: python loopless_probe.py n [--brute] [--prime P]
Outputs rank A, rank [A|b] mod P over the loopless family, plus column stats.
"""
import sys, math, itertools, time, json
from collections import defaultdict
from itertools import permutations, combinations

sys.path.insert(0, "/data/projects/relu-depth-frontier-research/.venv/lib/python3.13/site-packages")
import flint
from pynauty import Graph, certificate

def canon_key(A, B, n):
    """Canonical key of 2-colored simple graph (A,B) under S_n x color swap."""
    def cert(X, Y):
        m = n + len(X) + len(Y)
        adj = {v: [] for v in range(m)}
        idx = n
        for (a, b) in X:
            adj[idx] = [a, b]; idx += 1
        for (a, b) in Y:
            adj[idx] = [a, b]; idx += 1
        g = Graph(m, directed=False, adjacency_dict=adj,
                  vertex_coloring=[set(range(n)), set(range(n, n+len(X))), set(range(n+len(X), m))])
        return certificate(g)
    return min(cert(A, B), cert(B, A))

def nonpositive_on_cone(d):
    if sum(d) != 0: return False
    s = 0
    for c in d[:-1]:
        s += c
        if s < 0: return False
    return True

def column_dp(A, B, n):
    """Distribution of vote-difference vectors d = votes(B) - votes(A) over all n! orderings,
    via DP over placed-vertex subsets. Returns dict d(tuple)->count and linear part."""
    nbrA = [[0]*n for _ in range(n)]; nbrB = [[0]*n for _ in range(n)]
    for a, b in A: nbrA[a][b] += 1; nbrA[b][a] += 1
    for a, b in B: nbrB[a][b] += 1; nbrB[b][a] += 1
    # state: (mask, prefix tuple of (aVote, bVote) pairs) -> count.  We track a and b
    # prefixes jointly because orientation/linear bookkeeping needs both full vectors.
    states = {(0, ()): 1}
    for pos in range(n):
        nxt = defaultdict(int)
        for (mask, pre), cnt in states.items():
            for v in range(n):
                if mask >> v & 1: continue
                av = sum(nbrA[v][u] for u in range(n) if mask >> u & 1)
                bv = sum(nbrB[v][u] for u in range(n) if mask >> u & 1)
                nxt[(mask | (1 << v), pre + ((av, bv),))] += cnt
        states = nxt
    linear = [0]*n; hinges = defaultdict(int)
    for (mask, pre), cnt in states.items():
        a = tuple(p[0] for p in pre); b = tuple(p[1] for p in pre)
        base, other = sorted((a, b))
        d = tuple(o - s for s, o in zip(base, other))
        for i, c in enumerate(base): linear[i] += cnt * c
        if nonpositive_on_cone(d): continue
        g = math.gcd(*d)
        dp = tuple(x // g for x in d)
        hinges[dp] += cnt * g
    return tuple(linear), dict(hinges)

def column_brute(A, B, n):
    linear = [0]*n; hinges = defaultdict(int)
    for order in permutations(range(n)):
        pos = [0]*n
        for r, v in enumerate(order): pos[v] = r
        a = [0]*n; b = [0]*n
        for x, y in A: a[max(pos[x], pos[y])] += 1
        for x, y in B: b[max(pos[x], pos[y])] += 1
        base, other = sorted((tuple(a), tuple(b)))
        d = tuple(o - s for s, o in zip(base, other))
        for i, c in enumerate(base): linear[i] += c
        if nonpositive_on_cone(d): continue
        g = math.gcd(*d); dp = tuple(x // g for x in d)
        hinges[dp] += g
    return tuple(linear), dict(hinges)

def main():
    n = int(sys.argv[1]); k = (n - 1) // 2
    brute = "--brute" in sys.argv
    P = 1000003
    if "--prime" in sys.argv: P = int(sys.argv[sys.argv.index("--prime") + 1])
    edges = list(combinations(range(n), 2))
    graphs = list(combinations(edges, k))
    t0 = time.time()
    # orbit-aware enumeration: one representative A per S_n-class of single graphs,
    # then all labelled B; every (A,B) orbit meets some (rep, B).
    reps = {}
    for A in graphs:
        key = canon_key(A, (), n)
        if key not in reps: reps[key] = A
    reps = list(reps.values())
    seen = {}
    for A in reps:
        for B in graphs:
            key = canon_key(A, B, n)
            if key not in seen: seen[key] = (A, B)
    templates = list(seen.values())
    print(f"n={n} k={k}: {len(graphs)} loopless simple {k}-edge graphs; {len(templates)} templates (canonical); {time.time()-t0:.1f}s", flush=True)
    # validate DP vs brute on a few templates
    if n <= 8:
        for A, B in templates[:5]:
            assert column_dp(A, B, n) == column_brute(A, B, n), "DP/brute mismatch"
        print("  DP validated against brute force on 5 templates", flush=True)
    t0 = time.time()
    cols = []; rowidx = {}
    for A, B in templates:
        lin, h = (column_brute if brute else column_dp)(A, B, n)
        for d in h:
            if d not in rowidx: rowidx[d] = len(rowidx)
        cols.append((lin, h))
    nh = len(rowidx)
    nnz = sum(len(h) for _, h in cols)
    print(f"  columns computed in {time.time()-t0:.1f}s; retained hinge rows={nh}; nnz={nnz} (avg {nnz/len(cols):.1f}/col); linear rows={n}", flush=True)
    nrows = nh + n; ncols = len(cols)
    M = flint.nmod_mat(nrows, ncols + 1, P)
    for j, (lin, h) in enumerate(cols):
        for d, c in h.items(): M[rowidx[d], j] = c % P
        for i, c in enumerate(lin): M[nh + i, j] = c % P
    M[nh + n - 1, ncols] = 1   # target: hinges 0, linear = x_n
    t0 = time.time()
    rA = flint.nmod_mat(nrows, ncols, P)
    # rank of A: copy without last column
    sub = [[M[i, j] for j in range(ncols)] for i in range(nrows)]
    rA = flint.nmod_mat(sub, P).rank()
    rAb = M.rank()
    print(f"  mod {P}: rank(A)={rA}, rank([A|b])={rAb} -> {'MEMBER (consistent)' if rA == rAb else 'NOT in span'}; nullity={ncols - rA}; ranks in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
