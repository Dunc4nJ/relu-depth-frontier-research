#!/usr/bin/env python3
"""Attachment-type taxonomy for the MAX9 -> MAX10 degree-five lift family.

For every one of the 337 pinned degree-four MAX9 certificate terms (A_t, B_t)
and every ordered pair of distinct non-loop edges (e, f) on [10], the raw
extension is (A_t + e, B_t + f).  Its signed-W orbit (cancel common edge
occurrences, quotient by S_10 relabeling and global branch/sign reversal) is a
record of the bead-ksi lift family universe.  This script recomputes that map
*with multiplicities* (the published builder deduplicated) and labels every raw
extension with an attachment type.

Output: for each attachment class of the finest taxonomy T3, a sparse vector
over family-universe record indices whose entry at orbit j is

    sum over raw extensions (t, e, f) in the class that land on orbit j of c_t

scaled by the global denominator D = lcm of the 337 coefficient denominators,
so every stored weight is an exact integer.  Coarser taxonomies are unions of
T3 classes, so their class sums are sums of these vectors.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations
import json
import math
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "artifacts/math/n11-lift-test"))
import build_order as common  # noqa: E402

SOURCE = ROOT / "subjects/max-relu-known/certificates/certificate_9_4.json"
SOURCE_SHA = "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88"
UNIVERSE = ROOT / "artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz"
UNIVERSE_SHA = "c22d925e66ab83ae31eb873346ef3709a17753e3b0c36fc03e2d3b12d2123cb3"
SOURCE_TERMS = 337
N = 10
EDGES = tuple(combinations(range(1, N + 1), 2))
EDGE_PAIRS = tuple((a, b) for a in EDGES for b in EDGES if a != b)
RAW_PER_SOURCE = 1980
RAW_TOTAL = SOURCE_TERMS * RAW_PER_SOURCE
EXPECTED_ORBITS = 114814


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def sha256_path(path: Path) -> str:
    d = hashlib.sha256()
    with path.open("rb") as h:
        for block in iter(lambda: h.read(1 << 20), b""):
            d.update(block)
    return d.hexdigest()


def load_terms():
    require(sha256_path(SOURCE) == SOURCE_SHA, "MAX9 certificate SHA drift")
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    require(doc.get("n") == 9, "MAX9 arity drift")
    raw = doc["terms"]
    require(len(raw) == SOURCE_TERMS, "MAX9 term count drift")
    pairs, coeffs = [], []
    for i, term in enumerate(raw):
        pair = (common.canonical_side(term["pair"][0]), common.canonical_side(term["pair"][1]))
        require(len(pair[0]) == len(pair[1]) == 4, f"degree drift {i}")
        require(all(1 <= u < v <= 9 for side in pair for u, v in side), f"label drift {i}")
        pairs.append(pair)
        coeffs.append(Fraction(term["coefficient"]))
    return pairs, coeffs


# ---------------------------------------------------------------- taxonomy ---
def t3_key(A, B, e, f):
    """Finest attachment type.  Everything coarser below is a function of it."""
    VA = {v for edge in A for v in edge}
    VB = {v for edge in B for v in edge}
    V = VA | VB
    se, sf = set(e), set(f)
    aV, bV = len(se & V), len(sf & V)
    s = len(se & sf)
    rep_e = e in A          # e repeats an edge occurrence of its own branch (A)
    rep_f = f in B
    cross_e = e in B        # e cancels against the opposite branch inside W
    cross_f = f in A
    aA, aB = len(se & VA), len(se & VB)
    bA, bB = len(sf & VA), len(sf & VB)
    if s == 1:
        x = next(iter(se & sf))
        svA, svB = x in VA, x in VB
    else:
        svA = svB = False
    return (aV, bV, s, rep_e, rep_f, cross_e, cross_f, aA, aB, bA, bB, svA, svB)


def coarsen(k, level):
    (aV, bV, s, rep_e, rep_f, cross_e, cross_f, aA, aB, bA, bB, svA, svB) = k
    if level == "T3":
        return k
    if level == "T2":
        return (aV, bV, s, rep_e, rep_f, cross_e, cross_f)
    if level == "T2b":            # branch-blind edge roles
        return (aV, bV, s, rep_e or cross_e, rep_f or cross_f)
    if level == "T1":
        return (aV, bV, s)
    if level == "T1s":            # unordered in (e,f)
        return (min(aV, bV), max(aV, bV), s)
    if level == "Tv":             # fresh-vertex count and adjacency only
        touch = s * (1 if (svA or svB) else 0)
        newv = (4 - s) - (aV + bV - touch)
        return (newv, s)
    if level == "Tn":             # fresh-vertex count only
        touch = s * (1 if (svA or svB) else 0)
        return ((4 - s) - (aV + bV - touch),)
    if level == "T0":             # planted negative: one class
        return ()
    raise RuntimeError(f"unknown level {level}")


LEVELS = ("T3", "T2", "T2b", "T1", "T1s", "Tv", "Tn", "T0")


# ------------------------------------------------------------------ workers ---
def census_term(item):
    index, source = item
    A, B = source
    out = Counter()
    for e, f in EDGE_PAIRS:
        pair = (tuple(sorted(A + (e,))), tuple(sorted(B + (f,))))
        cert = common.certificate_sha256(pair, n=N)
        out[(t3_key(A, B, e, f), cert)] += 1
    require(sum(out.values()) == RAW_PER_SOURCE, f"raw denominator drift at {index}")
    return index, out


def universe_cert(item):
    index, record = item
    pair = (
        tuple((int(u) + 1, int(v) + 1) for u, v in record["negative_edges"]),
        tuple((int(u) + 1, int(v) + 1) for u, v in record["positive_edges"]),
    )
    return index, common.certificate_sha256(pair, n=N)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=HERE / "lift_taxonomy_map_9to10.npz")
    ap.add_argument("--report", type=Path, default=HERE / "lift_taxonomy_map_9to10.json")
    args = ap.parse_args()
    started = time.monotonic()

    pairs, coeffs = load_terms()
    D = math.lcm(*[c.denominator for c in coeffs])
    ints = [int(c * D) for c in coeffs]
    require(all(Fraction(v, D) == c for v, c in zip(ints, coeffs)), "coefficient scaling drift")

    require(sha256_path(UNIVERSE) == UNIVERSE_SHA, "lift universe SHA drift")
    with gzip.open(UNIVERSE, "rt", encoding="utf-8") as fh:
        universe = json.load(fh)
    require(universe["schema"] == "max9-to-max10-lift-family-universe-v1", "universe schema drift")
    require(universe["n"] == N and universe["branch_edge_occurrences"] == 5, "universe arity drift")
    records = universe["records"]
    require(len(records) == EXPECTED_ORBITS, "universe record count drift")

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        cert_index = {}
        for index, cert in pool.map(universe_cert, enumerate(records), chunksize=512):
            require(cert not in cert_index, f"duplicate universe certificate at {index}")
            cert_index[cert] = index
        require(len(cert_index) == EXPECTED_ORBITS, "universe certificate collision")
        print(f"universe mapped in {time.monotonic()-started:.1f}s", flush=True)

        # (t3_key, term, orbit) -> multiplicity
        triples = {}
        done = 0
        for index, counter in pool.map(census_term, enumerate(pairs), chunksize=1):
            for (key, cert), mult in counter.items():
                orbit = cert_index.get(cert)
                require(orbit is not None, f"raw extension left the family at term {index}")
                triples[(key, index, orbit)] = triples.get((key, index, orbit), 0) + mult
            done += 1
            if done % 50 == 0:
                print(f"  terms {done}/{SOURCE_TERMS}  {time.monotonic()-started:.1f}s", flush=True)

    require(sum(triples.values()) == RAW_TOTAL, "global raw denominator drift")

    t3_keys = sorted({k for (k, _, _) in triples})
    key_index = {k: i for i, k in enumerate(t3_keys)}

    # H1 accumulation over the finest taxonomy: (class, orbit) -> sum_t D*c_t*mult
    h1 = {}
    for (key, term, orbit), mult in triples.items():
        slot = (key_index[key], orbit)
        h1[slot] = h1.get(slot, 0) + ints[term] * mult
    h1 = {k: v for k, v in h1.items() if v != 0}

    cls = np.array([k[0] for k in h1], dtype=np.int32)
    orb = np.array([k[1] for k in h1], dtype=np.int32)
    wgt = np.array([h1[k] for k in h1], dtype=object)
    order = np.lexsort((cls, orb))          # orbit-major: streaming friendly
    cls, orb = cls[order], orb[order]
    wgt = np.array([int(w) for w in wgt[order]], dtype=np.int64)
    require(all(abs(int(w)) < 2**62 for w in wgt), "H1 weight overflow")

    # H2 incidences: (term, class, orbit) with integer weight D*c_t*mult
    h2_terms = np.array([t for (_, t, _) in triples], dtype=np.int32)
    h2_cls = np.array([key_index[k] for (k, _, _) in triples], dtype=np.int32)
    h2_orb = np.array([o for (_, _, o) in triples], dtype=np.int32)
    h2_w = np.array([ints[t] * m for (_, t, _), m in triples.items()], dtype=np.int64)
    keep = h2_w != 0
    h2_terms, h2_cls, h2_orb, h2_w = h2_terms[keep], h2_cls[keep], h2_orb[keep], h2_w[keep]
    o2 = np.lexsort((h2_cls, h2_terms, h2_orb))
    h2_terms, h2_cls, h2_orb, h2_w = h2_terms[o2], h2_cls[o2], h2_orb[o2], h2_w[o2]

    level_maps = {}
    for level in LEVELS:
        labels = sorted({coarsen(k, level) for k in t3_keys})
        lidx = {lab: i for i, lab in enumerate(labels)}
        level_maps[level] = {
            "labels": [list(map(str, lab)) for lab in labels],
            "t3_to_level": [lidx[coarsen(k, level)] for k in t3_keys],
            "classes": len(labels),
        }

    np.savez_compressed(
        args.out,
        denominator=np.array([D], dtype=object),
        h1_class=cls, h1_orbit=orb, h1_weight=wgt,
        h2_term=h2_terms, h2_class=h2_cls, h2_orbit=h2_orb, h2_weight=h2_w,
        term_numerator=np.array(ints, dtype=np.int64),
        **{f"map_{lvl}": np.array(level_maps[lvl]["t3_to_level"], dtype=np.int32) for lvl in LEVELS},
    )

    report = {
        "schema": "max9-to-max10-lift-attachment-taxonomy-v1",
        "result": "PASS",
        "source_certificate_sha256": SOURCE_SHA,
        "universe_sha256": UNIVERSE_SHA,
        "source_terms": SOURCE_TERMS,
        "raw_extensions": RAW_TOTAL,
        "orbits": EXPECTED_ORBITS,
        "orbits_touched": int(len(set(orb.tolist()))),
        "coefficient_denominator": str(D),
        "coefficient_denominator_factored": str(D),
        "t3_classes": len(t3_keys),
        "t3_key_fields": ["endpoints_of_e_in_V", "endpoints_of_f_in_V", "shared_vertices_e_f",
                          "e_repeats_own_branch", "f_repeats_own_branch",
                          "e_in_opposite_branch", "f_in_opposite_branch",
                          "endpoints_of_e_in_V_A", "endpoints_of_e_in_V_B",
                          "endpoints_of_f_in_V_A", "endpoints_of_f_in_V_B",
                          "shared_vertex_in_V_A", "shared_vertex_in_V_B"],
        "t3_keys": [list(map(str, k)) for k in t3_keys],
        "levels": {lvl: {"classes": level_maps[lvl]["classes"],
                         "labels": level_maps[lvl]["labels"]} for lvl in LEVELS},
        "h1_incidences": int(len(cls)),
        "h2_incidences": int(len(h2_w)),
        "h2_classes_T3": int(len(set(zip(h2_terms.tolist(), h2_cls.tolist())))),
        "max_abs_h1_weight": str(int(np.abs(wgt).max())),
        "max_abs_h2_weight": str(int(np.abs(h2_w).max())),
        "wall_seconds": time.monotonic() - started,
        "no_claim": "A finite source-derived map only; no membership or depth claim.",
    }
    args.report.write_text(json.dumps(report, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items()
                      if k not in ("t3_keys", "levels")}, indent=1))
    print({lvl: level_maps[lvl]["classes"] for lvl in LEVELS})


if __name__ == "__main__":
    main()
