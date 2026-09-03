"""Vectorised version of my independent subset DP (same semantics, numpy state merge).

Packing: key = mask (low 11 bits) | word[d] + 16 packed in 5 bits at 11 + 5d,
for d = 0..9 only.  word[10] is recovered from the zero-sum invariant, keeping
every key inside int64.
"""
import math
import numpy as np
from math import gcd

N = 11
FACT = [math.factorial(k) for k in range(N + 2)]
OFF, BITS, FULL = 16, 5, 1 << N
MASKBITS = FULL - 1


def fast_column(left, right):
    n = N
    m = np.zeros((n, n), dtype=np.int64)
    for s, side in ((-1, left), (1, right)):
        for a, b in side:
            m[a, b] += s
            if a != b:
                m[b, a] += s
    inc = np.zeros((n, FULL), dtype=np.int64)
    inc[:, 0] = np.diag(m)
    for mask in range(1, FULL):
        bit = mask & -mask
        inc[:, mask] = inc[:, mask ^ bit] + m[:, bit.bit_length() - 1]
    if np.abs(inc).max() > 15:
        raise AssertionError("increment out of packing range")

    keys = np.zeros(1, dtype=np.int64)
    counts = np.ones(1, dtype=np.int64)
    for depth in range(n):
        masks = keys & MASKBITS
        ck, cc = [], []
        for v in range(n):
            sel = (masks & (1 << v)) == 0
            if not sel.any():
                continue
            km = masks[sel]
            child = keys[sel] | (1 << v)
            if depth < n - 1:                    # last entry is implied by zero-sum
                child = child | ((inc[v][km] + OFF) << (N + BITS * depth))
            ck.append(child)
            cc.append(counts[sel])
        allk = np.concatenate(ck)
        allc = np.concatenate(cc)
        keys, inv = np.unique(allk, return_inverse=True)
        counts = np.zeros(keys.size, dtype=np.int64)
        np.add.at(counts, inv.ravel(), allc)
    if int(counts.sum()) != FACT[n]:
        raise AssertionError("permutation census")

    words = np.empty((keys.size, n), dtype=np.int64)
    for i in range(n - 1):
        words[:, i] = ((keys >> (N + BITS * i)) & ((1 << BITS) - 1)) - OFF
    words[:, n - 1] = -words[:, : n - 1].sum(axis=1)

    loops = sum(1 for a, b in left if a == b)
    nonloops = len(left) - loops
    linear = [loops * FACT[n - 1] + nonloops * 2 * r * FACT[n - 2] for r in range(n)]
    hinges = {}
    hget = hinges.get
    for row, cnt in zip(words.tolist(), counts.tolist()):
        nz = 0
        for x in row:
            if x:
                nz = x
                break
        if not nz:
            continue
        if nz < 0:
            for i, x in enumerate(row):
                linear[i] += cnt * x
        g = 0
        for x in row:
            g = gcd(g, x)
        d = tuple(x // g for x in row) if nz > 0 else tuple(-x // g for x in row)
        pre = 0
        for x in d[:-1]:
            pre += x
            if pre < 0:
                hinges[d] = hget(d, 0) + cnt * g
                break
    return linear, hinges
