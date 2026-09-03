"""T2: fully independent EXACT recomputation of the n=11 certificate identity.

Uses only my own subset DP (validated against the pinned upstream
verify_certificate.py on 373 columns at n=5..8 and against verify11 on 20
columns at n=11).  Shares no code with tools/verify11.
"""
import json, math, os, sys, time
from math import gcd, lcm
from multiprocessing import Pool
from t2_fastdp import fast_column

CERT = "/data/projects/relu-depth-frontier-research/artifacts/math/n11-stageA-exact-lift/member-F2-forestpair-m64000-p1000003-s1-cuda/member_upstream.json"
N = 11
FACT = [math.factorial(k) for k in range(N + 2)]


def column(left, right):
    """(linear over all n! permutations, {primitive direction: coefficient})."""
    n = N
    m = [[0] * n for _ in range(n)]
    for s, side in ((-1, left), (1, right)):
        for a, b in side:
            m[a][b] += s
            if a != b:
                m[b][a] += s
    full = 1 << n
    inc = []
    for v in range(n):
        row = [0] * full
        row[0] = m[v][v]
        mv = m[v]
        for mask in range(1, full):
            bit = mask & -mask
            row[mask] = row[mask ^ bit] + mv[bit.bit_length() - 1]
        inc.append(row)

    states = {(0, ()): 1}
    for _ in range(n):
        nxt = {}
        get = nxt.get
        for (mask, word), cnt in states.items():
            for v in range(n):
                bit = 1 << v
                if mask & bit:
                    continue
                key = (mask | bit, word + (inc[v][mask],))
                nxt[key] = get(key, 0) + cnt
        states = nxt
        get = None
    if sum(states.values()) != FACT[n]:
        raise AssertionError("permutation census")

    loops = sum(1 for a, b in left if a == b)
    nonloops = len(left) - loops
    linear = [loops * FACT[n - 1] + nonloops * 2 * r * FACT[n - 2] for r in range(n)]
    hinges = {}
    hget = hinges.get
    for (_, word), cnt in states.items():
        nz = 0
        for x in word:
            if x:
                nz = x
                break
        if not nz:
            continue
        if sum(word) != 0:
            raise AssertionError("word not zero-sum")
        if nz < 0:
            for i, x in enumerate(word):
                linear[i] += cnt * x
        g = 0
        for x in word:
            g = gcd(g, x)
        o = 1 if nz > 0 else -1
        d = tuple(o * x // g for x in word)
        pre = 0
        for x in d[:-1]:
            pre += x
            if pre < 0:
                hinges[d] = hget(d, 0) + cnt * g
                break
    return linear, hinges


TERMS = None
SCALED = None


def _init(path):
    global TERMS, SCALED
    d = json.load(open(path))
    assert d["n"] == N
    dens = []
    nums = []
    for t in d["terms"]:
        a, b = t["coefficient"].split("/")
        nums.append(int(a))
        dens.append(int(b))
    D = 1
    for x in dens:
        D = lcm(D, x)
    TERMS = [[[(a - 1, b - 1) for a, b in side] for side in t["pair"]] for t in d["terms"]]
    SCALED = [nu * (D // de) for nu, de in zip(nums, dens)]
    globals()["COMMON_D"] = D


def _work(chunk):
    lin = [0] * N
    hin = {}
    hget = hin.get
    for i in chunk:
        left, right = TERMS[i]
        c = SCALED[i]
        l, h = fast_column(left, right)
        for r in range(N):
            lin[r] += c * l[r]
        for d, v in h.items():
            hin[d] = hget(d, 0) + c * v
    return lin, hin


def main():
    procs = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    _init(CERT)
    total = len(TERMS)
    D = globals()["COMMON_D"]
    idx = list(range(total))
    chunks = [idx[i::procs * 8] for i in range(procs * 8)]
    t0 = time.time()
    lin = [0] * N
    hin = {}
    done = 0
    with Pool(procs, initializer=_init, initargs=(CERT,)) as pool:
        for l, h in pool.imap_unordered(_work, chunks):
            for r in range(N):
                lin[r] += l[r]
            for d, v in h.items():
                hin[d] = hin.get(d, 0) + v
            done += 1
            print(f"  chunk {done}/{len(chunks)}  {time.time()-t0:.0f}s  union={len(hin)}",
                  flush=True)
    lin[N - 1] -= D                      # target x_n, denominators cleared
    bad_lin = [(r + 1, v) for r, v in enumerate(lin) if v]
    bad_h = sorted(d for d, v in hin.items() if v)
    out = {
        "reviewer": "T2 independent Python recomputation (not tools/verify11)",
        "certificate": CERT,
        "n": N,
        "terms": total,
        "common_denominator_digits": len(str(D)),
        "hinge_rows_union": len(hin),
        "bad_linear_rows": len(bad_lin),
        "bad_hinge_rows": len(bad_h),
        "first_bad_linear": bad_lin[0][0] if bad_lin else None,
        "first_bad_hinge": list(bad_h[0]) if bad_h else None,
        "verdict": "OK" if not bad_lin and not bad_h else "FAIL",
        "wall_seconds": time.time() - t0,
    }
    print(json.dumps(out, indent=2))
    json.dump(out, open(sys.argv[2], "w"), indent=2)


if __name__ == "__main__":
    main()
