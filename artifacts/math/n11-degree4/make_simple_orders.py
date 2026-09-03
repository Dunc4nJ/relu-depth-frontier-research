#!/usr/bin/env python3
"""Select the simple-W prefix controls from degree-four universe records."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import json
from pathlib import Path


EXPECTED = {9: 6_197, 10: 7_203}


def maximum_multiplicity(record: dict[str, object]) -> int:
    counts = Counter(
        tuple(map(int, edge))
        for field in ("negative_edges", "positive_edges")
        for edge in record[field]  # type: ignore[index]
    )
    return max(counts.values(), default=0)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    with gzip.open(args.universe, "rt") as source:
        universe = json.load(source)
    n = int(universe["n"])
    if int(universe["branch_edge_occurrences"]) != 4:
        raise ValueError("expected a degree-four universe")
    order = [
        index
        for index, record in enumerate(universe["records"])
        if maximum_multiplicity(record) <= 1
    ]
    expected = EXPECTED.get(n)
    if expected is None or len(order) != expected:
        raise ValueError(f"n={n} simple-W denominator mismatch: {len(order)} != {expected}")
    if not order or order[0] != 0:
        raise ValueError("simple-W control omitted record-zero 4E")
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_text(json.dumps(order, separators=(",", ":")) + "\n")
    print(f"PASS n={n} selected={len(order)} output={args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
