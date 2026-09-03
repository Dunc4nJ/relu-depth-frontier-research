#!/usr/bin/env python3
"""Consistency control for the NON_MEMBER duals of the 9->10 lift recursion.

Rebuilds the exact rational dual y for a named taxonomy level (y is supported
on rank+1 rows, y^T S_c = 0 for every class, y . b != 0) and then dots it with
a deterministic sample of *individual* family columns.

The point: bead ksi established that the whole 114,814-column lift family spans
MAX_10 at n=10.  If y annihilated every column of that family it would also
annihilate b, contradicting that.  So a correct pipeline must produce a dual
that separates the class sums from the target while still pairing nontrivially
with individual columns.  A dual orthogonal to every sampled column would be
evidence of a bug rather than of mathematics.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "artifacts/math/class-sum-n9-n10"))
sys.path.insert(0, str(HERE))
import class_sum_test as cst  # noqa: E402
from test_lift_recursion import modular_ranks_safe, coarsen_matrix, PRIMES  # noqa: E402

COLGEN = ROOT / "tools/colgen/target/release/max11-colgen"
UNIVERSE = ROOT / "artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz"
OFFSET, BITS = 16, 6
PACK = np.uint64(1) << (np.uint64(BITS) * np.arange(10, dtype=np.uint64))


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def build_dual(matrix: np.ndarray, target: np.ndarray):
    _, R, C = modular_ranks_safe(matrix, target, PRIMES)
    R, C = sorted(int(x) for x in R), sorted(int(x) for x in C)
    require(len(R) == len(C), "pivot sets disagree")
    D = matrix[np.ix_(C, R)].T
    primal_C = cst.square_solve(D, [int(target[i]) for i in R])
    require(primal_C is not None, "pivot minor singular")
    primal = [Fraction(0)] * matrix.shape[0]
    for pos, c in enumerate(C):
        primal[c] = primal_C[pos]
    lcm, scaled = cst.clear_denominators(primal)
    extra = cst.first_nonzero_row(matrix.T, scaled, [int(x) * lcm for x in target])
    require(extra is not None, "primal already exact: the level is MEMBER")
    u = cst.square_solve(D.T, [int(matrix[c, extra]) for c in C])
    require(u is not None, "transposed minor singular")
    y_rows = R + [int(extra)]
    y_values = list(u) + [Fraction(-1)]
    ylcm, yscaled = cst.clear_denominators(y_values)
    ok, _ = cst.exact_product_matches(matrix[:, y_rows], [yscaled], [[0] * matrix.shape[0]])
    require(ok, "dual does not annihilate every class sum")
    dot_b = sum((y_values[i] * int(target[y_rows[i]]) for i in range(len(y_rows))), Fraction(0))
    require(dot_b != 0, "dual is orthogonal to the target")
    return y_rows, yscaled, ylcm, dot_b


def emit(indices, out: Path, threads: int) -> None:
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump([int(i) for i in indices], fh)
        order = Path(fh.name)
    try:
        subprocess.run([str(COLGEN), "emit-universe", "--universe", str(UNIVERSE),
                        "--threads", str(threads), "--order-file", str(order),
                        "--format", "binary", "--output", str(out)],
                       check=True, capture_output=True)
    finally:
        order.unlink()


def parse(path: Path):
    buf = path.read_bytes()
    n, _ = struct.unpack_from("<HH", buf, 8)
    _, count = struct.unpack_from("<QQ", buf, 12)
    off = 28
    for _ in range(count):
        (idx,) = struct.unpack_from("<Q", buf, off); off += 8
        lin = np.frombuffer(buf, "<i8", count=n, offset=off).copy(); off += 8 * n
        (hc,) = struct.unpack_from("<Q", buf, off); off += 8
        if hc:
            blk = np.frombuffer(buf, np.uint8, count=hc * (2 * n + 8), offset=off)
            blk = blk.reshape(hc, 2 * n + 8); off += hc * (2 * n + 8)
            dirs = blk[:, :2 * n].copy().view("<i2").reshape(hc, n)
            vals = blk[:, 2 * n:].copy().view("<i8").reshape(hc)
            keys = ((dirs.astype(np.int64) + OFFSET).astype(np.uint64) * PACK).sum(
                axis=1, dtype=np.uint64)
        else:
            keys = np.zeros(0, np.uint64); vals = np.zeros(0, np.int64)
        yield idx, lin, keys, vals


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sums", type=Path, default=HERE / "class_sums_9to10.npz")
    ap.add_argument("--map", type=Path, default=HERE / "lift_taxonomy_map_9to10.npz")
    ap.add_argument("--levels", nargs="*", default=["T1", "T3"])
    ap.add_argument("--sample", type=int, default=4000)
    ap.add_argument("--threads", type=int, default=5)
    ap.add_argument("--out", type=Path, default=HERE / "dual_control_9to10.json")
    args = ap.parse_args()
    started = time.monotonic()

    sums = np.load(args.sums, allow_pickle=True)
    maps = np.load(args.map, allow_pickle=True)
    master = sums["master"]
    full = np.concatenate([sums["acc_lin"], sums["acc"]], axis=1)
    nrows = full.shape[1]
    target = np.zeros(nrows, dtype=np.int64)
    target[9] = 1

    total = 114814
    step = max(1, total // args.sample)
    sample = list(range(0, total, step))

    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / "sample.bin"
        emit(sample, out, args.threads)
        columns = list(parse(out))
        require(len(columns) == len(sample), "sample record count drift")
        for level in args.levels:
            matrix = full if level == "T3" else coarsen_matrix(full, maps[f"map_{level}"])
            y_rows, y_scaled, y_lcm, dot_b = build_dual(matrix, target)
            row_set = {int(r): i for i, r in enumerate(y_rows)}
            hinge_rows = {int(master[r - 10]): i for r, i in row_set.items() if r >= 10}
            lin_rows = {r: i for r, i in row_set.items() if r < 10}
            nonzero = 0
            for idx, lin, keys, vals in columns:
                acc = 0
                for r, i in lin_rows.items():
                    acc += y_scaled[i] * int(lin[r])
                if keys.size and hinge_rows:
                    for pos in np.flatnonzero(np.isin(keys, list(hinge_rows.keys()))):
                        acc += y_scaled[hinge_rows[int(keys[pos])]] * int(vals[pos])
                if acc != 0:
                    nonzero += 1
            checks.append({
                "level": level,
                "classes": int(matrix.shape[0]),
                "dual_support_rows": len(y_rows),
                "y_denominator_lcm": str(y_lcm),
                "y_dot_target": str(dot_b),
                "sampled_columns": len(columns),
                "columns_with_nonzero_dual_pairing": nonzero,
                "separates_class_sums_from_target": True,
            })
            print(checks[-1], flush=True)
            if matrix is not full:
                del matrix

    report = {
        "schema": "max9-to-max10-lift-dual-control-v1",
        "result": "PASS" if all(c["columns_with_nonzero_dual_pairing"] > 0 for c in checks)
                  else "FAIL",
        "rationale": ("The lift family spans MAX_10 (bead ksi, rank 17,127), so a correct "
                      "NON_MEMBER dual for the class sums must still pair nontrivially with "
                      "individual family columns."),
        "sample_stride": step,
        "checks": checks,
        "wall_seconds": time.monotonic() - started,
    }
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"]}))


if __name__ == "__main__":
    main()
