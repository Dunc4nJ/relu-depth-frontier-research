#!/usr/bin/env python3
"""Streaming class-sum accumulation for the MAX10 -> MAX11 lift family.

Same accumulators as accumulate_class_sums.py one rung up, but the columns are
emitted by colgen through the frozen bead-ksi ``--order-file``, so orbit index
== position in that order file, and the record index stamped in the binary
stream is the original G-0027 index, which is checked against the order file.

Exact int64 accumulation is used when the a-priori bound
``(sum of |class weights|) * (max |column coefficient|)`` fits inside the
int64 headroom; otherwise the run accumulates modulo the named primes.  The
mode actually used is recorded in the output summary.
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
OFFSET = 15
BITS = 5
MAXDIR = 15


def require(cond: bool, msg: str) -> None:
    if not cond:
        raise RuntimeError(msg)


def splitmix64(x: np.ndarray) -> np.ndarray:
    with np.errstate(over="ignore"):
        z = x + np.uint64(0x9E3779B97F4A7C15)
        z = (z ^ (z >> np.uint64(30))) * np.uint64(0xBF58476D1CE4E5B9)
        z = (z ^ (z >> np.uint64(27))) * np.uint64(0x94D049BB133111EB)
        return z ^ (z >> np.uint64(31))


def parse_chunk(path: Path, n: int, pack: np.ndarray):
    buf = path.read_bytes()
    require(buf[:8] == b"MCOLGEN1", f"bad magic in {path}")
    rn, k = struct.unpack_from("<HH", buf, 8)
    modulus, count = struct.unpack_from("<QQ", buf, 12)
    require(rn == n and k == 5 and modulus == 0, "chunk arity/modulus drift")
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
            require(int(np.abs(dirs).max()) <= MAXDIR, "direction out of packing range")
            keys = ((dirs.astype(np.int64) + OFFSET).astype(np.uint64) * pack).sum(
                axis=1, dtype=np.uint64)
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
    ap.add_argument("--map", type=Path, default=HERE / "lift_taxonomy_map_10to11.npz")
    ap.add_argument("--order-file", type=Path, required=True)
    ap.add_argument("--chunks", type=Path, required=True)
    ap.add_argument("--n", type=int, default=11)
    ap.add_argument("--chunk-size", type=int, default=2000)
    ap.add_argument("--sketch-stride", type=int, default=8)
    ap.add_argument("--primes", type=int, nargs="*", default=[1000003, 1000033])
    ap.add_argument("--max-coeff-assumption", type=int, default=1 << 27)
    ap.add_argument("--out", type=Path, default=HERE / "class_sums_10to11.npz")
    args = ap.parse_args()
    started = time.monotonic()

    n = args.n
    pack = np.uint64(1) << (np.uint64(BITS) * np.arange(n, dtype=np.uint64))
    require(BITS * n <= 64, "packing does not fit in uint64")

    order = json.loads(args.order_file.read_text(encoding="utf-8"))
    total = len(order)
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

    bound_h1 = int(np.abs(h1_weight).sum())
    bound_h2 = int(np.abs(h2_weight).sum())
    exact = (max(bound_h1, bound_h2) * args.max_coeff_assumption) < 2**62
    mode = "exact-int64" if exact else "modular"
    moduli = [0] if exact else list(args.primes)
    print(f"mode={mode} classes T3={n_t3} H2={n_h2} orbits={total} "
          f"bound={max(bound_h1, bound_h2) * args.max_coeff_assumption}", flush=True)

    h1_start = np.searchsorted(h1_orbit, np.arange(total + 1), side="left")
    h2_start = np.searchsorted(h2_orbit, np.arange(total + 1), side="left")

    master = np.zeros(0, dtype=np.uint64)
    sk_master = np.zeros(0, dtype=np.uint64)
    accs = [np.zeros((n_t3, 0), dtype=np.int64) for _ in moduli]
    acc_lins = [np.zeros((n_t3, n), dtype=np.int64) for _ in moduli]
    sk_accs = [np.zeros((n_h2, 0), dtype=np.int64) for _ in moduli]
    sk_lins = [np.zeros((n_h2, n), dtype=np.int64) for _ in moduli]

    stride = np.uint64(args.sketch_stride)
    max_coeff = 0
    expect = 0
    for start in range(0, total, args.chunk_size):
        path = args.chunks / f"c{start}.bin"
        done = args.chunks / f"c{start}.done"
        while not done.exists():
            time.sleep(4)
        cols = parse_chunk(path, n, pack)
        chunk_keys = np.unique(np.concatenate([c[2] for c in cols] + [np.zeros(0, np.uint64)]))
        sel = chunk_keys[(splitmix64(chunk_keys) % stride) == np.uint64(0)]
        for i in range(len(moduli)):
            master_i, accs[i] = grow(master, accs[i], chunk_keys)
            sk_i, sk_accs[i] = grow(sk_master, sk_accs[i], sel)
        master, sk_master = master_i, sk_i
        for idx, lin, keys, vals in cols:
            require(idx == order[expect], f"order drift at position {expect}")
            expect += 1
            pos = expect - 1
            if vals.size:
                max_coeff = max(max_coeff, int(np.abs(vals).max()))
            max_coeff = max(max_coeff, int(np.abs(lin).max()))
            rows = np.searchsorted(master, keys)
            if keys.size and sk_master.size:
                sp = np.searchsorted(sk_master, keys)
                sp = np.clip(sp, 0, sk_master.size - 1)
                hit = sk_master[sp] == keys
                srows, svals = sp[hit], vals[hit]
            else:
                srows = np.zeros(0, np.int64); svals = np.zeros(0, np.int64)
            a1, b1 = h1_start[pos], h1_start[pos + 1]
            a2, b2 = h2_start[pos], h2_start[pos + 1]
            for mi, p in enumerate(moduli):
                acc, acc_lin = accs[mi], acc_lins[mi]
                for q in range(a1, b1):
                    c = int(h1_class[q])
                    w = int(h1_weight[q]) if p == 0 else int(h1_weight[q]) % p
                    if vals.size:
                        acc[c][rows] += w * vals
                    acc_lin[c] += w * lin
                sk_acc, sk_lin = sk_accs[mi], sk_lins[mi]
                for q in range(a2, b2):
                    s = int(h2_slot[q])
                    w = int(h2_weight[q]) if p == 0 else int(h2_weight[q]) % p
                    if svals.size:
                        sk_acc[s][srows] += w * svals
                    sk_lin[s] += w * lin
        if not exact:
            for mi, p in enumerate(moduli):
                np.mod(accs[mi], p, out=accs[mi])
                np.mod(acc_lins[mi], p, out=acc_lins[mi])
                np.mod(sk_accs[mi], p, out=sk_accs[mi])
                np.mod(sk_lins[mi], p, out=sk_lins[mi])
        del cols
        path.unlink(); done.unlink()
        print(f"chunk {start:>7}/{total} rows={master.size} sketch={sk_master.size} "
              f"t={time.monotonic()-started:.0f}s", flush=True)

    require(expect == total, "record denominator drift")
    if exact:
        require(bound_h1 * max_coeff < 2**62, "H1 exact bound exceeded")
        require(bound_h2 * max_coeff < 2**62, "H2 exact bound exceeded")
    require(max_coeff <= args.max_coeff_assumption, "max coefficient exceeded the assumption")

    payload = {"master": master, "sk_master": sk_master, "h2_labels": h2_labels,
               "map_T2b": map_t2b,
               "meta": np.array([n_t3, n_t2b, n_h2, args.sketch_stride, max_coeff, n],
                                dtype=np.int64)}
    for mi, p in enumerate(moduli):
        tag = "exact" if p == 0 else f"p{p}"
        payload[f"acc_{tag}"] = accs[mi]
        payload[f"acc_lin_{tag}"] = acc_lins[mi]
        payload[f"sk_acc_{tag}"] = sk_accs[mi]
        payload[f"sk_lin_{tag}"] = sk_lins[mi]
    np.savez_compressed(args.out, **payload)
    summary = {
        "schema": "max10-to-max11-lift-class-sums-v1",
        "result": "PASS",
        "mode": mode,
        "moduli": moduli,
        "records": expect,
        "n": n,
        "hinge_rows": int(master.size),
        "sketch_rows": int(sk_master.size),
        "t3_classes": n_t3,
        "h2_classes": n_h2,
        "max_abs_column_coefficient": max_coeff,
        "h1_entry_bound": str(bound_h1 * max_coeff),
        "h2_entry_bound": str(bound_h2 * max_coeff),
        "row_key_sha256": hashlib.sha256(master.tobytes()).hexdigest(),
        "wall_seconds": time.monotonic() - started,
    }
    args.out.with_suffix(".json").write_text(json.dumps(summary, indent=1) + "\n")
    print(json.dumps(summary, indent=1))


if __name__ == "__main__":
    main()
