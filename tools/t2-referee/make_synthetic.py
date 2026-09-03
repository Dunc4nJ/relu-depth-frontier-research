#!/usr/bin/env python3
"""Generate a synthetic certificate-shaped file for timing the lattice checker.

The output is deliberately NOT a valid certificate: coefficients are random, so
``lattice_check.py`` will report FAIL on it.  Its only purpose is to make the
checker do the same amount of work a real large certificate would.

Two coefficient shapes are supported.

``--denominators shared``
    One random denominator reused by every term, with independent random signed
    numerators.  This matches the shape the campaign's n=11 candidate is
    expected to have (a dense lift over one common denominator).

``--denominators independent``
    An independent random denominator per term.  Exact rational accumulation
    then has to build a common denominator across all terms, which is
    intrinsically expensive for any exact tool.  Included so the timing report
    states the adversarial cost rather than hiding it.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from itertools import combinations
from pathlib import Path


def random_odd(rng: random.Random, bits: int) -> int:
    return rng.getrandbits(bits) | (1 << (bits - 1)) | 1


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--n", type=int, default=11)
    parser.add_argument("--terms", type=int, default=16000)
    parser.add_argument("--branch-edges", type=int, default=5)
    parser.add_argument("--min-bits", type=int, default=1000)
    parser.add_argument("--max-bits", type=int, default=4000)
    parser.add_argument(
        "--denominators", choices=["shared", "independent"], default="shared"
    )
    parser.add_argument("--seed", type=int, default=20260903)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)

    if args.output.exists():
        print(f"refusing to overwrite existing output {args.output}", file=sys.stderr)
        return 2

    rng = random.Random(args.seed)
    pairs = list(combinations(range(1, args.n + 1), 2))  # loopless: a < b
    shared_den = random_odd(rng, args.max_bits)

    terms = []
    for _ in range(args.terms):
        left = [list(p) for p in rng.sample(pairs, args.branch_edges)]
        right = [list(p) for p in rng.sample(pairs, args.branch_edges)]
        num = random_odd(rng, rng.randint(args.min_bits, args.max_bits))
        if rng.random() < 0.5:
            num = -num
        den = shared_den if args.denominators == "shared" else random_odd(rng, args.max_bits)
        terms.append({"coefficient": f"{num}/{den}", "pair": [left, right]})

    with open(args.output, "x", encoding="utf-8") as handle:
        json.dump({"n": args.n, "terms": terms}, handle)
        handle.write("\n")
    print(f"wrote {args.output} ({args.output.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
