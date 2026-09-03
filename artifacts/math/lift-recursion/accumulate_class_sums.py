#!/usr/bin/env python3
"""Stream exact colgen columns for the 9->10 lift family and accumulate class sums.

Two accumulators are built in one pass over the exact column stream:

* H1 (attachment-type only): the full-row class sum for every class of the
  finest taxonomy T3.  Every coarser taxonomy is a union of T3 classes, so its
  class sums are obtained by adding these vectors; nothing else is needed.
* H2 (parent x attachment type): the same sums keyed by (parent term, T2b
  class), restricted to a deterministic hash-selected row sketch plus all
  linear rows, because the full-row object is far too large to hold.

Everything is exact integer arithmetic.  A rigorous a-priori bound on every
accumulated entry is checked against the int64 range; the run aborts if the
bound is not met.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import time

import numpy as np

HERE = Path(__file__).resolve().parent
M64 = np.uint64(0xFFFFFFFFFFFFFFFF)
OFFSET = 16          # direction entries are packed as (d + OFFSET) in 6 bits
BITS = 6
MAXDIR = 15


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def splitmix64(x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        z = (x + np.uint64(0x9E3779B97F4A7C15))
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


PACK = (np.uint64(1) << (np.uint64(BITS) * np.arange(10, dtype=np.uint64)))


def pack_dirs(dirs: np.ndarray) -> np.ndarray:
    require(int(np.abs(dirs).max(initial=0)) <= MAXDIR, "direction entry out of packing range")
    return ((dirs.astype(np.int64) + OFFSET).astype(np.uint64) * PACK).sum(axis=1, dtype=np.uint64)


def unpack_key(key: int) -> list[int]:
    return [((key >> (BITS * i)) & ((1 << BITS) - 1)) - OFFSET for i in range(10)]


def parse_chunk(path: Path):
    buf = path.read_bytes()
    require(buf[:8] == b"MCOLGEN1", f"bad magic in {path}")
    n, k = struct.unpack_from("<HH", buf, 8)
    modulus, count = struct.unpack_from("<QQ", buf, 12)
    require(n == 10 and k == 5 and modulus == 0, "chunk arity/modulus drift")
    off = 28
    out = []
    for _ in range(count):
        (idx,) = struct.unpack_from("<Q", buf, off); off += 8
        lin = np.frombuffer(buf, dtype="<i8", count=n, offset=off).copy(); off += 8 * n
        (hc,) = struct.unpack_from("<Q", buf, off); off += 8
        if hc:
            blk = np.frombuffer(buf, dtype=np.uint8, count=hc * (2 * n + 8), offset=off)
            blk = blk.reshape(hc, 2 * n + 8)
            off += hc * (2 * n + 8)
            dirs = blk[:, : 2 * n].copy().view("<i2").reshape(hc, n)
            vals = blk[:, 2 * n:].copy().view("<i8").reshape(hc)
            keys = pack_dirs(dirs)
        else:
            keys = np.zeros(0, dtype=np.uint64)
            vals = np.zeros(0, dtype=np.int64)
        out.append((idx, lin, keys, vals))
    require(off == len(buf), f"trailing bytes in {path}")
    return out


def grow(master: np.ndarray, acc: np.ndarray, new_keys: np.ndarray):
    merged = np.union1d(master, new_keys)
    if merged.size == master.size:
        return master, acc
    fresh = np.zeros((acc.shape[0], merged.size), dtype=np.int64)
    if master.size:
        fresh[:, np.searchsorted(merged, master)] = acc
    return merged, fresh


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--map", type=Path, default=HERE / "lift_taxonomy_map_9to10.npz")
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--total", type=int, default=114814)
    ap.add_argument("--chunk-size", type=int, default=4000)
    ap.add_argument("--sketch-stride", type=int, default=16)
    ap.add_argument("--out", type=Path, default=HERE / "class_sums_9to10.npz")
    args = ap.parse_args()
    started = time.monotonic()

    data = np.load(args.map, allow_pickle=True)
    h1_class, h1_orbit, h1_weight = data["h1_class"], data["h1_orbit"], data["h1_weight"]
    h2_term, h2_cls3, h2_orbit, h2_weight = (data["h2_term"], data["h2_class"],
                                             data["h2_orbit"], data["h2_weight"])
    map_t2b = data["map_T2b"]
    n_t3 = int(map_t2b.size)
    n_t2b = int(map_t2b.max()) + 1

    h2_lab = h2_term.astype(np.int64) * n_t2b + map_t2b[h2_cls3].astype(np.int64)
    h2_labels, h2_slot = np.unique(h2_lab, return_inverse=True)
    n_h2 = int(h2_labels.size)
    print(f"T3 classes {n_t3}, T2b classes {n_t2b}, H2 (term,T2b) classes {n_h2}", flush=True)

    # a-priori bound on any accumulated entry
    max_coeff = 0
    bound_h1 = int(np.abs(h1_weight).sum())
    bound_h2 = int(np.abs(h2_weight).sum())

    h1_start = np.searchsorted(h1_orbit, np.arange(args.total + 1), side="left")
    h2_start = np.searchsorted(h2_orbit, np.arange(args.total + 1), side="left")

    master = np.zeros(0, dtype=np.uint64)
    acc = np.zeros((n_t3, 0), dtype=np.int64)
    acc_lin = np.zeros((n_t3, 10), dtype=np.int64)
    sk_master = np.zeros(0, dtype=np.uint64)
    sk_acc = np.zeros((n_h2, 0), dtype=np.int64)
    sk_lin = np.zeros((n_h2, 10), dtype=np.int64)

    stride = np.uint64(args.sketch_stride)
    expect = 0
    for start in range(0, args.total, args.chunk_size):
        path = args.chunks / f"c{start}.bin"
        done = args.chunks / f"c{start}.done"
        while not done.exists():
            time.sleep(4)
        cols = parse_chunk(path)
        chunk_keys = np.unique(np.concatenate([c[2] for c in cols] + [np.zeros(0, np.uint64)]))
        sel = chunk_keys[(splitmix64(chunk_keys) % stride) == np.uint64(0)]
        master, acc = grow(master, acc, chunk_keys)
        sk_master, sk_acc = grow(sk_master, sk_acc, sel)
        for idx, lin, keys, vals in cols:
            require(idx == expect, f"record order drift at {idx}")
            expect += 1
            if vals.size:
                m = int(np.abs(vals).max())
                if m > max_coeff:
                    max_coeff = m
            m = int(np.abs(lin).max())
            if m > max_coeff:
                max_coeff = m
            rows = np.searchsorted(master, keys)
            a, b = h1_start[idx], h1_start[idx + 1]
            for p in range(a, b):
                c, w = int(h1_class[p]), int(h1_weight[p])
                if vals.size:
                    acc[c][rows] += w * vals        # rows are distinct within a column
                acc_lin[c] += w * lin
            a, b = h2_start[idx], h2_start[idx + 1]
            if b > a:
                if keys.size:
                    pos = np.searchsorted(sk_master, keys)
                    pos = np.clip(pos, 0, max(sk_master.size - 1, 0))
                    hit = sk_master[pos] == keys if sk_master.size else np.zeros(keys.size, bool)
                    srows, svals = pos[hit], vals[hit]
                else:
                    srows = np.zeros(0, np.int64); svals = np.zeros(0, np.int64)
                for p in range(a, b):
                    s, w = int(h2_slot[p]), int(h2_weight[p])
                    if svals.size:
                        sk_acc[s][srows] += w * svals
                    sk_lin[s] += w * lin
        del cols
        path.unlink()
        done.unlink()
        print(f"chunk {start:>7} rows={master.size} sketch={sk_master.size} "
              f"t={time.monotonic()-started:.0f}s", flush=True)

    require(expect == args.total, "record denominator drift")
    require(bound_h1 * max_coeff < 2**62, "H1 accumulator bound exceeds int64 headroom")
    require(bound_h2 * max_coeff < 2**62, "H2 accumulator bound exceeds int64 headroom")

    row_digest = hashlib.sha256(master.tobytes()).hexdigest()
    np.savez_compressed(
        args.out,
        master=master, acc=acc, acc_lin=acc_lin,
        sk_master=sk_master, sk_acc=sk_acc, sk_lin=sk_lin,
        h2_labels=h2_labels, map_T2b=map_t2b,
        meta=np.array([n_t3, n_t2b, n_h2, args.sketch_stride, max_coeff], dtype=np.int64),
    )
    summary = {
        "schema": "max9-to-max10-lift-class-sums-v1",
        "result": "PASS",
        "records": expect,
        "hinge_rows": int(master.size),
        "sketch_rows": int(sk_master.size),
        "t3_classes": n_t3,
        "h2_classes": n_h2,
        "max_abs_column_coefficient": max_coeff,
        "h1_entry_bound": str(bound_h1 * max_coeff),
        "h2_entry_bound": str(bound_h2 * max_coeff),
        "int64_headroom_bits": 62,
        "row_key_sha256": row_digest,
        "wall_seconds": time.monotonic() - started,
    }
    (args.out.with_suffix(".json")).write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
