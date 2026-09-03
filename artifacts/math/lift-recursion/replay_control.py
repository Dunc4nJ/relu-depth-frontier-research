#!/usr/bin/env python3
"""Independent replay control for the 9->10 class-sum accumulation.

Picks attachment classes of the finest taxonomy T3, re-emits exactly the
family-universe records those classes touch with a fresh colgen invocation, and
rebuilds the class sum from scratch.  Every coordinate of the rebuilt vector
must agree with the streamed accumulator, including all the zero coordinates on
rows the class does not touch.  A deliberately mutated weight must disagree.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct
import subprocess
import tempfile
import time

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
COLGEN = ROOT / "tools/colgen/target/release/max11-colgen"
UNIVERSE = ROOT / "artifacts/math/n11-lift-test/n9-lift-n10-family-universe.json.gz"
OFFSET, BITS, MAXDIR = 16, 6, 15
PACK = np.uint64(1) << (np.uint64(BITS) * np.arange(10, dtype=np.uint64))


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


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
    require(buf[:8] == b"MCOLGEN1", "bad magic")
    n, k = struct.unpack_from("<HH", buf, 8)
    modulus, count = struct.unpack_from("<QQ", buf, 12)
    require(n == 10 and k == 5 and modulus == 0, "arity drift")
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
    require(off == len(buf), "trailing bytes")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sums", type=Path, default=HERE / "class_sums_9to10.npz")
    ap.add_argument("--map", type=Path, default=HERE / "lift_taxonomy_map_9to10.npz")
    ap.add_argument("--classes", type=int, default=3)
    ap.add_argument("--max-orbits", type=int, default=6000)
    ap.add_argument("--threads", type=int, default=4)
    ap.add_argument("--out", type=Path, default=HERE / "replay_control_9to10.json")
    args = ap.parse_args()
    started = time.monotonic()

    sums = np.load(args.sums, allow_pickle=True)
    data = np.load(args.map, allow_pickle=True)
    master, acc, acc_lin = sums["master"], sums["acc"], sums["acc_lin"]
    cls, orb, wgt = data["h1_class"], data["h1_orbit"], data["h1_weight"]

    sizes = np.bincount(cls, minlength=acc.shape[0])
    candidates = [int(c) for c in np.argsort(sizes) if 0 < sizes[c] <= args.max_orbits]
    require(len(candidates) >= args.classes, "not enough replayable classes")
    chosen = candidates[: args.classes - 1] + [candidates[len(candidates) // 2]]

    checks = []
    with tempfile.TemporaryDirectory() as tmp:
        for c in chosen:
            sel = cls == c
            orbits, weights = orb[sel], wgt[sel]
            out = Path(tmp) / f"c{c}.bin"
            emit(orbits, out, args.threads)
            hinge = np.zeros(master.size, dtype=np.int64)
            linear = np.zeros(10, dtype=np.int64)
            seen = 0
            wmap = {int(o): int(w) for o, w in zip(orbits, weights)}
            for idx, lin, keys, vals in parse(out):
                w = wmap[int(idx)]
                linear += w * lin
                if keys.size:
                    pos = np.searchsorted(master, keys)
                    require(bool((master[pos] == keys).all()), "replay row outside the master set")
                    hinge[pos] += w * vals
                seen += 1
            out.unlink()
            require(seen == orbits.size, "replay record count drift")
            same = bool((hinge == acc[c]).all() and (linear == acc_lin[c]).all())
            mutant = hinge.copy()
            mutant[int(np.flatnonzero(hinge)[0])] += 1
            checks.append({
                "t3_class": c,
                "orbits": int(orbits.size),
                "nonzero_hinge_rows": int(np.count_nonzero(hinge)),
                "matches_streamed_accumulator": same,
                "planted_mutant_rejected": bool(not (mutant == acc[c]).all()),
                "max_abs_entry": str(int(max(np.abs(hinge).max(initial=0),
                                             np.abs(linear).max(initial=0)))),
            })
            print(checks[-1], flush=True)

    report = {
        "schema": "max9-to-max10-lift-class-sum-replay-control-v1",
        "result": "PASS" if all(c["matches_streamed_accumulator"] and
                                c["planted_mutant_rejected"] for c in checks) else "FAIL",
        "checks": checks,
        "rows": int(master.size),
        "wall_seconds": time.monotonic() - started,
    }
    args.out.write_text(json.dumps(report, indent=1) + "\n", encoding="utf-8")
    print(json.dumps({"result": report["result"]}))


if __name__ == "__main__":
    main()
