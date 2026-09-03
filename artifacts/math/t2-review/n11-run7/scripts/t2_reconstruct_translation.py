#!/usr/bin/env python3
"""T2: independently reconstruct member_upstream.json from universe + witness.

Written from the G-0027 universe schema and the pinned upstream atom
definition, without importing tools/exactlift/universe_to_upstream.py.
Prints the SHA-256 of the reconstruction for comparison with the pinned file.
"""
import gzip, hashlib, json, sys
from fractions import Fraction

U = "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
W = "artifacts/math/n11-stageA-exact-lift/run7-dense-insurance/member_exact_witness.json"

u = json.load(gzip.open(U, "rt", encoding="utf-8"))
w = json.load(open(W, encoding="utf-8"))
recs, B, n = u["records"], int(u["branch_edge_occurrences"]), int(u["n"])
assert n == int(w["n"])

terms = []
for e in w["coefficients"]:
    c, coef = int(e["column"]), Fraction(e["coefficient"])
    if not coef:
        continue
    if c < len(recs):
        r = recs[c]
        m = int(r["signed_mass"])
        neg = [[int(a), int(b)] for a, b in r["negative_edges"]]
        pos = [[int(a), int(b)] for a, b in r["positive_edges"]]
        assert len(neg) == len(pos) == m and 0 <= m <= B
        pad = [[0, 1]] * (B - m)          # common loopless carrier, cancels in B-A
        pair = [neg + pad, pos + pad]
    elif c == len(recs):
        pair = [[[0, 0]] * B, [[0, 0]] * B]   # synthetic 5L all-ones linear column
    else:
        raise SystemExit(f"column {c} outside universe")
    assert all(len(s) == B for s in pair)
    terms.append({"coefficient": str(coef),
                  "pair": [[[a + 1, b + 1] for a, b in s] for s in pair]})

out = json.dumps({"n": n, "terms": terms}, indent=2) + "\n"
print("terms:", len(terms))
print("sha256:", hashlib.sha256(out.encode()).hexdigest())
