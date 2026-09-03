#!/usr/bin/env python3
"""Attachment-type taxonomy for the MAX10 -> MAX11 degree-five lift family.

Same construction and same taxonomy as build_lift_taxonomy.py one rung up: the
402 pinned degree-four MAX10 certificate terms, every ordered pair of distinct
non-loop edges on [11], and the 163,740 signed-W orbits of G-0027 that the
1,193,940 raw extensions land on.  Orbits are indexed by their *position in the
frozen bead-ksi order file*, which is the order colgen emits with
``--order-file``.
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
sys.path.insert(0, str(HERE))
import build_order as common  # noqa: E402
from build_lift_taxonomy import t3_key, coarsen, LEVELS  # noqa: E402

SOURCE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
SOURCE_SHA = "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
UNIVERSE = ROOT / "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
UNIVERSE_SHA = "8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8"
ORDER = ROOT / "artifacts/math/n11-lift-test/max10-lift-g0027-order.json"
SOURCE_TERMS = 402
N = 11
EDGES = tuple(combinations(range(1, N + 1), 2))
EDGE_PAIRS = tuple((a, b) for a in EDGES for b in EDGES if a != b)
RAW_PER_SOURCE = 2970
RAW_TOTAL = SOURCE_TERMS * RAW_PER_SOURCE
EXPECTED_ORBITS = 163740
UNIVERSE_RECORDS = 754017


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
    require(sha256_path(SOURCE) == SOURCE_SHA, "MAX10 certificate SHA drift")
    doc = json.loads(SOURCE.read_text(encoding="utf-8"))
    require(doc.get("n") == 10, "MAX10 arity drift")
    raw = doc["terms"]
    require(len(raw) == SOURCE_TERMS, "MAX10 term count drift")
    pairs, coeffs = [], []
    for i, term in enumerate(raw):
        pair = (common.canonical_side(term["pair"][0]), common.canonical_side(term["pair"][1]))
        require(len(pair[0]) == len(pair[1]) == 4, f"degree drift {i}")
        require(all(1 <= u < v <= 10 for side in pair for u, v in side), f"label drift {i}")
        pairs.append(pair)
        coeffs.append(Fraction(term["coefficient"]))
    return pairs, coeffs


def census_term(item):
    index, source = item
    A, B = source
    out = Counter()
    for e, f in EDGE_PAIRS:
        pair = (tuple(sorted(A + (e,))), tuple(sorted(B + (f,))))
        out[(t3_key(A, B, e, f), common.certificate_sha256(pair, n=N))] += 1
    require(sum(out.values()) == RAW_PER_SOURCE, f"raw denominator drift at {index}")
    return index, out


def universe_cert(item):
    position, record = item
    pair = (
        tuple((int(u) + 1, int(v) + 1) for u, v in record["negative_edges"]),
        tuple((int(u) + 1, int(v) + 1) for u, v in record["positive_edges"]),
    )
    return position, common.certificate_sha256(pair, n=N)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--out", type=Path, default=HERE / "lift_taxonomy_map_10to11.npz")
    ap.add_argument("--report", type=Path, default=HERE / "lift_taxonomy_map_10to11.json")
    args = ap.parse_args()
    started = time.monotonic()

    pairs, coeffs = load_terms()
    D = math.lcm(*[c.denominator for c in coeffs])
    ints = [int(c * D) for c in coeffs]
    require(all(Fraction(v, D) == c for v, c in zip(ints, coeffs)), "coefficient scaling drift")

    require(sha256_path(UNIVERSE) == UNIVERSE_SHA, "G-0027 universe SHA drift")
    order = json.loads(ORDER.read_text(encoding="utf-8"))
    require(len(order) == EXPECTED_ORBITS and len(set(order)) == EXPECTED_ORBITS,
            "order file drift")
    with gzip.open(UNIVERSE, "rt", encoding="utf-8") as fh:
        universe = json.load(fh)
    records = universe["records"]
    require(len(records) == UNIVERSE_RECORDS, "G-0027 record count drift")
    subject = [records[i] for i in order]
    del universe, records
    print(f"universe loaded {time.monotonic()-started:.1f}s", flush=True)

    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        cert_index = {}
        for position, cert in pool.map(universe_cert, enumerate(subject), chunksize=512):
            require(cert not in cert_index, f"duplicate certificate at order position {position}")
            cert_index[cert] = position
        require(len(cert_index) == EXPECTED_ORBITS, "certificate collision in the subject")
        print(f"subject mapped {time.monotonic()-started:.1f}s", flush=True)

        triples = {}
        done = 0
        for index, counter in pool.map(census_term, enumerate(pairs), chunksize=1):
            for (key, cert), mult in counter.items():
                position = cert_index.get(cert)
                require(position is not None, f"raw extension left the family at term {index}")
                slot = (key, index, position)
                triples[slot] = triples.get(slot, 0) + mult
            done += 1
            if done % 50 == 0:
                print(f"  terms {done}/{SOURCE_TERMS} {time.monotonic()-started:.1f}s", flush=True)
    require(sum(triples.values()) == RAW_TOTAL, "global raw denominator drift")

    t3_keys = sorted({k for (k, _, _) in triples})
    key_index = {k: i for i, k in enumerate(t3_keys)}

    h1 = {}
    for (key, term, orbit), mult in triples.items():
        slot = (key_index[key], orbit)
        h1[slot] = h1.get(slot, 0) + ints[term] * mult
    h1 = {k: v for k, v in h1.items() if v != 0}
    cls = np.array([k[0] for k in h1], dtype=np.int32)
    orb = np.array([k[1] for k in h1], dtype=np.int32)
    wgt = np.array([h1[k] for k in h1], dtype=np.int64)
    o1 = np.lexsort((cls, orb))
    cls, orb, wgt = cls[o1], orb[o1], wgt[o1]

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
        level_maps[level] = {"labels": [list(map(str, lab)) for lab in labels],
                             "t3_to_level": [lidx[coarsen(k, level)] for k in t3_keys],
                             "classes": len(labels)}

    np.savez_compressed(
        args.out,
        h1_class=cls, h1_orbit=orb, h1_weight=wgt,
        h2_term=h2_terms, h2_class=h2_cls, h2_orbit=h2_orb, h2_weight=h2_w,
        term_numerator=np.array(ints, dtype=np.int64),
        **{f"map_{lvl}": np.array(level_maps[lvl]["t3_to_level"], dtype=np.int32) for lvl in LEVELS},
    )
    report = {
        "schema": "max10-to-max11-lift-attachment-taxonomy-v1",
        "result": "PASS",
        "source_certificate_sha256": SOURCE_SHA,
        "universe_sha256": UNIVERSE_SHA,
        "source_terms": SOURCE_TERMS,
        "raw_extensions": RAW_TOTAL,
        "orbits": EXPECTED_ORBITS,
        "orbits_touched": int(len(set(orb.tolist()))),
        "coefficient_denominator": str(D),
        "t3_classes": len(t3_keys),
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
    print(json.dumps({k: v for k, v in report.items() if k not in ("t3_keys", "levels")}, indent=1))
    print({lvl: level_maps[lvl]["classes"] for lvl in LEVELS})


if __name__ == "__main__":
    main()
