#!/usr/bin/env python3
"""Exact H1/H2 membership tests for the weighted 9 -> 10 lift recursion.

H1: MAX_10 = sum_tau w_tau * S_tau with
    S_tau = sum over raw extensions (t, e, f) of attachment type tau of
            c_t * col(W(A_t + e, B_t + f)),
    c_t the pinned MAX9 degree-four certificate coefficients.
    Unknowns: one weight per attachment type.
H2: the coefficient of a raw extension may depend freely on (parent term,
    attachment type).  Unknowns: one per realized (t, tau).

Verdicts reuse the exact decision machinery of
artifacts/math/class-sum-n9-n10/class_sum_test.py: MEMBER carries an exact
rational solution verified on every row of the supplied row set, NON_MEMBER an
exact rational dual.  H1 uses the complete row set of the family; H2 uses a
deterministic hash-selected row sketch plus all linear rows, so an H2
NON_MEMBER is exact and an H2 MEMBER is sketch-restricted evidence only.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import sys
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "artifacts/math/class-sum-n9-n10"))
import class_sum_test as cst  # noqa: E402

PRIMES = (1000003, 1000033)
LEVELS = ("T3", "T2", "T2b", "T1", "T1s", "Tv", "Tn", "T0")


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def coarsen_matrix(base: np.ndarray, mapping: np.ndarray) -> np.ndarray:
    out = np.zeros((int(mapping.max()) + 1, base.shape[1]), dtype=np.int64)
    for j in range(base.shape[0]):
        out[int(mapping[j])] += base[j]
    return out


def modular_ranks_safe(matrix: np.ndarray, target: np.ndarray, primes):
    """cst.modular_ranks, but every entry is reduced mod p as an integer first.

    cst.modular_ranks casts int64 straight to float64 before taking the
    residue.  Class-sum entries here exceed 2**53, so that cast would be lossy;
    reducing with integer arithmetic first keeps every residue exact.
    """
    report = {}
    pivot_rows: list[int] = []
    pivot_classes: list[int] = []
    m = matrix.shape[0]
    for prime in primes:
        reduced = np.mod(matrix, prime)
        treduced = np.mod(target, prime)
        state = cst.streamed_rank(((i, reduced[i]) for i in range(m)),
                                  matrix.shape[1], prime)
        rank_s = state.rank
        rows = sorted(state.pivots)
        classes = sorted(state.sources)
        state.add_block(treduced.reshape(1, -1).astype(np.float64), [m])
        report[str(prime)] = {"rank_S": rank_s, "rank_S_augmented": state.rank,
                              "modular_member": state.rank == rank_s}
        if not pivot_rows:
            pivot_rows, pivot_classes = rows, classes
        del state, reduced
    return report, pivot_rows, pivot_classes


def run_case(name: str, matrix: np.ndarray, target: np.ndarray,
             primes=PRIMES) -> dict:
    started = time.monotonic()
    modular, pivot_rows, pivot_classes = modular_ranks_safe(matrix, target, primes)
    decision = cst.decide_membership(matrix, target, pivot_rows, pivot_classes)
    solution = decision.pop("solution", None)
    out = {
        "case": name,
        "classes": int(matrix.shape[0]),
        "rows": int(matrix.shape[1]),
        "modular": modular,
        "verdict": decision["verdict"],
        "certificate": decision["certificate"],
        "seconds": time.monotonic() - started,
    }
    if solution is not None:
        out["solution"] = [str(v) for v in solution]
    print(f"  {name}: classes={matrix.shape[0]} "
          f"rank={modular[str(primes[0])]['rank_S']} "
          f"rank_aug={modular[str(primes[0])]['rank_S_augmented']} "
          f"-> {decision['verdict']}  ({out['seconds']:.1f}s)", flush=True)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sums", type=Path, default=HERE / "class_sums_9to10.npz")
    ap.add_argument("--map", type=Path, default=HERE / "lift_taxonomy_map_9to10.npz")
    ap.add_argument("--taxonomy-report", type=Path,
                    default=HERE / "lift_taxonomy_map_9to10.json")
    ap.add_argument("--out", type=Path, default=HERE / "lift_recursion_9to10.json")
    ap.add_argument("--skip-h2", action="store_true")
    ap.add_argument("--h2-levels", nargs="*", default=["T1", "T2b"])
    ap.add_argument("--n", type=int, default=10)
    ap.add_argument("--suffix", default="", help='"_exact" for the 10->11 npz key names')
    args = ap.parse_args()
    started = time.monotonic()

    sums = np.load(args.sums, allow_pickle=True)
    maps = np.load(args.map, allow_pickle=True)
    taxonomy = json.loads(args.taxonomy_report.read_text(encoding="utf-8"))

    sx = args.suffix
    acc, acc_lin = sums["acc" + sx], sums["acc_lin" + sx]
    n_t3 = acc.shape[0]
    full = np.concatenate([acc_lin, acc], axis=1)
    del acc
    nrows = full.shape[1]
    target = np.zeros(nrows, dtype=np.int64)
    target[args.n - 1] = 1
    print(f"H1 subject: {n_t3} T3 classes, {nrows} rows "
          f"({nrows - args.n} hinge + {args.n} linear)", flush=True)

    results = {"h1": [], "h2": []}
    for level in LEVELS:
        mapping = maps[f"map_{level}"]
        matrix = full if level == "T3" else coarsen_matrix(full, mapping)
        row = run_case(f"H1/{level}", matrix, target)
        row["taxonomy_labels"] = taxonomy["levels"][level]["labels"]
        row["planted_negative"] = (level == "T0")
        results["h1"].append(row)
        if matrix is not full:
            del matrix
    del full

    if not args.skip_h2:
        sk_acc, sk_lin = sums["sk_acc" + sx], sums["sk_lin" + sx]
        labels = sums["h2_labels"]
        map_t2b, map_t1 = maps["map_T2b"], maps["map_T1"]
        n_t2b = int(map_t2b.max()) + 1
        t2b_to_t1 = {}
        for j in range(n_t3):
            key = int(map_t2b[j])
            value = int(map_t1[j])
            require(t2b_to_t1.setdefault(key, value) == value,
                    "T2b does not refine T1")
        sk_full = np.concatenate([sk_lin, sk_acc], axis=1)
        del sk_acc
        sk_rows = sk_full.shape[1]
        sk_target = np.zeros(sk_rows, dtype=np.int64)
        sk_target[args.n - 1] = 1
        print(f"H2 subject: {sk_full.shape[0]} (term,T2b) classes, "
              f"{sk_rows} sketch rows ({sk_rows - args.n} hinge + {args.n} linear)", flush=True)

        terms = labels // n_t2b
        t2bs = labels % n_t2b
        t1s = np.array([t2b_to_t1[int(x)] for x in t2bs], dtype=np.int64)
        n_t1 = int(map_t1.max()) + 1
        h2_t1_lab = terms * n_t1 + t1s
        uniq, inv = np.unique(h2_t1_lab, return_inverse=True)
        m_t1 = np.zeros((uniq.size, sk_rows), dtype=np.int64)
        for j in range(sk_full.shape[0]):
            m_t1[int(inv[j])] += sk_full[j]
        note = ("row-sketch restricted: NON_MEMBER is exact, "
                "MEMBER is sketch evidence only")
        if "T1" in args.h2_levels:
            row = run_case("H2/T1 (sketch rows)", m_t1, sk_target)
            row["note"] = note
            results["h2"].append(row)
        del m_t1
        if "T2b" in args.h2_levels:
            row = run_case("H2/T2b (sketch rows)", sk_full, sk_target)
            row["note"] = note
            results["h2"].append(row)

    report = {
        "schema": "max9-to-max10-weighted-lift-recursion-v1",
        "result": "PASS",
        "primes": list(PRIMES),
        "target": "1 on the last linear row, 0 on every other row",
        "n": args.n,
        "row_convention": f"{args.n} linear rows first, then the hinge rows of the family",
        "taxonomy": {lvl: taxonomy["levels"][lvl]["classes"] for lvl in LEVELS},
        "class_sum_summary": json.loads(
            (args.sums.with_suffix(".json")).read_text(encoding="utf-8")),
        "results": results,
        "wall_seconds": time.monotonic() - started,
        "no_claim": ("Results are for the named finite lift family only. A MEMBER "
                     "verdict is the existence of a recursion-shaped certificate at "
                     "this rung, not a theorem about all n and not a depth bound."),
    }
    args.out.write_text(json.dumps(report, indent=1, sort_keys=False) + "\n",
                        encoding="utf-8")
    print(json.dumps({"verdicts": {r["case"]: r["verdict"]
                                   for r in results["h1"] + results["h2"]}}, indent=1))


if __name__ == "__main__":
    main()
