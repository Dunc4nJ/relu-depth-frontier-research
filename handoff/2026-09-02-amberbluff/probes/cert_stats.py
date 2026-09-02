"""Structural statistics of the upstream MAX_n certificates (n=5..10).

For each template (A,B): loops per side, vertices touched, whether each side is a
forest (independent generators), rank of generator sets (dim Z_A, dim Z_B),
dim conv(Z_A u Z_B), canonical-labeling difference mass, coefficient denominators.
Pure stdlib + fractions; independent of campaign code.
"""
import json, sys, math
from fractions import Fraction
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path("/data/projects/relu-depth-frontier-research/literature/repos/max-relu-certificates/certificates")

def rank_int(vectors):
    """Rank over Q of a list of integer vectors (Gaussian elimination with Fractions)."""
    rows = [list(map(Fraction, v)) for v in vectors]
    r = 0
    ncols = len(rows[0]) if rows else 0
    for c in range(ncols):
        piv = None
        for i in range(r, len(rows)):
            if rows[i][c] != 0:
                piv = i; break
        if piv is None: continue
        rows[r], rows[piv] = rows[piv], rows[r]
        pv = rows[r][c]
        rows[r] = [x / pv for x in rows[r]]
        for i in range(len(rows)):
            if i != r and rows[i][c] != 0:
                f = rows[i][c]
                rows[i] = [a - f*b for a, b in zip(rows[i], rows[r])]
        r += 1
    return r

def gens(side, n):
    """Zonotope generators e_b - e_a for non-loop pairs; loops give zero vectors."""
    out = []
    for a, b in side:
        v = [0]*n
        if a != b:
            v[a-1] -= 1; v[b-1] += 1
        out.append(v)
    return out

def anchor(side, n):
    """Minkowski sum of segments [e_a,e_b] anchored at sum of e_a (min-corner)."""
    v = [0]*n
    for a, b in side:
        v[a-1] += 1
    return v

def dim_conv_union(A, B, n):
    """dim conv(Z_A u Z_B): affine span of vertices of both zonotopes."""
    # vertices of Z_A: anchor + subset sums of generators; affine hull = anchor + span(gens)
    gA, gB = gens(A, n), gens(B, n)
    aA, aB = anchor(A, n), anchor(B, n)
    diff = [x - y for x, y in zip(aB, aA)]
    vecs = [g for g in gA if any(g)] + [g for g in gB if any(g)] + ([diff] if any(diff) else [])
    return rank_int(vecs) if vecs else 0

def canon_mass(A, B, n):
    """mass of ell_A - ell_B in the identity labeling on the sorted cone."""
    d = [0]*n
    for a, b in A: d[max(a,b)-1] += 1
    for a, b in B: d[max(a,b)-1] -= 1
    return sum(x for x in d if x > 0)

def analyze(path):
    cert = json.loads(path.read_text())
    n = cert["n"]; terms = cert["terms"]
    k = len(terms[0]["pair"][0])
    stats = Counter(); dims = Counter(); masses = Counter(); loops = Counter(); touched = Counter()
    dimpairs = Counter(); dens = Counter(); forests = Counter()
    fulldim = 0
    for t in terms:
        c = Fraction(t["coefficient"])
        if c == 0: continue
        A = [tuple(p) for p in t["pair"][0]]; B = [tuple(p) for p in t["pair"][1]]
        lA = sum(1 for a,b in A if a==b); lB = sum(1 for a,b in B if a==b)
        loops[(lA, lB)] += 1
        verts = set(); [verts.update(p) for p in A+B]
        touched[len(verts)] += 1
        dA = rank_int([g for g in gens(A,n) if any(g)] or [[0]*n]); dB = rank_int([g for g in gens(B,n) if any(g)] or [[0]*n])
        dimpairs[(dA, dB)] += 1
        forests[(dA == k - lA, dB == k - lB)] += 1
        D = dim_conv_union(A, B, n); dims[D] += 1
        if D == n-1: fulldim += 1
        masses[canon_mass(A,B,n)] += 1
        den = c.denominator
        # prime factorization of denominator
        f = []; m = den; p = 2
        while p*p <= m:
            while m % p == 0: f.append(p); m//=p
            p += 1
        if m > 1: f.append(m)
        dens[tuple(sorted(set(f)))] += 1
    print(f"n={n} k={k} terms={len(terms)} full-dim(=n-1) atoms={fulldim}")
    print("  dim conv(Z_A u Z_B):", dict(sorted(dims.items())))
    print("  (dim Z_A, dim Z_B):", dict(sorted(dimpairs.items())))
    print("  (loops A, loops B):", dict(sorted(loops.items())))
    print("  vertices touched:", dict(sorted(touched.items())))
    print("  canonical mass of ell_A-ell_B:", dict(sorted(masses.items())))
    print("  both sides forests:", dict(forests.items()))
    print("  denominator prime supports:", dict(dens.items()))
    print("  lcm denominators:", math.lcm(*[Fraction(t['coefficient']).denominator for t in terms]))

for n, k in [(5,2),(6,2),(7,3),(8,3),(9,4),(10,4)]:
    analyze(ROOT / f"certificate_{n}_{k}.json")
