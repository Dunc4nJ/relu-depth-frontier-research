"""Parallel version of loopless_probe.py (multiprocessing over columns).
Also saves the sparse system to an .npz-free JSON-lines file for later reuse.
Usage: python loopless_probe_par.py n [--workers W] [--prime P]
"""
import sys, math, time, json, os
from collections import defaultdict
from itertools import combinations
from multiprocessing import Pool

sys.path.insert(0, "/data/projects/relu-depth-frontier-research/.venv/lib/python3.13/site-packages")
import flint
from pynauty import Graph, certificate

def canon_key(A, B, n):
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

def column_dp(args):
    A, B, n = args
    nbrA = [[0]*n for _ in range(n)]; nbrB = [[0]*n for _ in range(n)]
    for a, b in A: nbrA[a][b] += 1; nbrA[b][a] += 1
    for a, b in B: nbrB[a][b] += 1; nbrB[b][a] += 1
    states = {(0, ()): 1}
    for pos in range(n):
        nxt = defaultdict(int)
        for (mask, pre), cnt in states.items():
            placed = [u for u in range(n) if mask >> u & 1]
            for v in range(n):
                if mask >> v & 1: continue
                av = 0; bv = 0
                for u in placed:
                    av += nbrA[v][u]; bv += nbrB[v][u]
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
    return (tuple(linear), {",".join(map(str, k)): v for k, v in hinges.items()})

def main():
    n = int(sys.argv[1]); k = (n - 1) // 2
    W = 14
    if "--workers" in sys.argv: W = int(sys.argv[sys.argv.index("--workers") + 1])
    P = 1000003
    if "--prime" in sys.argv: P = int(sys.argv[sys.argv.index("--prime") + 1])
    edges = list(combinations(range(n), 2))
    graphs = list(combinations(edges, k))
    t0 = time.time()
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
    print(f"n={n} k={k}: {len(graphs)} loopless simple {k}-edge graphs; {len(templates)} templates; {time.time()-t0:.1f}s", flush=True)
    t0 = time.time()
    with Pool(W) as pool:
        cols = pool.map(column_dp, [(A, B, n) for A, B in templates], chunksize=8)
    print(f"  columns computed in {time.time()-t0:.1f}s with {W} workers", flush=True)
    rowidx = {}
    for lin, h in cols:
        for d in h:
            if d not in rowidx: rowidx[d] = len(rowidx)
    nh = len(rowidx); nnz = sum(len(h) for _, h in cols)
    print(f"  retained hinge rows={nh}; nnz={nnz} (avg {nnz/len(cols):.1f}/col); linear rows={n}", flush=True)
    out = f"loopless_system_n{n}.jsonl"
    with open(out, "w") as f:
        for (A, B), (lin, h) in zip(templates, cols):
            f.write(json.dumps({"A": A, "B": B, "lin": lin, "h": h}) + "\n")
    print(f"  saved {out}", flush=True)
    nrows = nh + n; ncols = len(cols)
    t0 = time.time()
    M = flint.nmod_mat(nrows, ncols + 1, P)
    for j, (lin, h) in enumerate(cols):
        for d, c in h.items(): M[rowidx[d], j] = c % P
        for i, c in enumerate(lin): M[nh + i, j] = c % P
    M[nh + n - 1, ncols] = 1
    print(f"  matrix built ({nrows}x{ncols+1}) in {time.time()-t0:.1f}s", flush=True)
    t0 = time.time()
    rAb = M.rank()
    print(f"  rank([A|b]) = {rAb} in {time.time()-t0:.1f}s", flush=True)
    t0 = time.time()
    sub = flint.nmod_mat(nrows, ncols, P)
    for j, (lin, h) in enumerate(cols):
        for d, c in h.items(): sub[rowidx[d], j] = c % P
        for i, c in enumerate(lin): sub[nh + i, j] = c % P
    rA = sub.rank()
    print(f"  mod {P}: rank(A)={rA}, rank([A|b])={rAb} -> {'MEMBER (consistent)' if rA == rAb else 'NOT in span'}; nullity={ncols - rA}; in {time.time()-t0:.1f}s", flush=True)

if __name__ == "__main__":
    main()
