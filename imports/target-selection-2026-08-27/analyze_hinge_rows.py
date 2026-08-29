#!/usr/bin/env python3
"""Count exact hinge rows in the full max_n certificate ansatz.

The full ansatz has sides whose ordered-cone coefficient histograms are all
weak compositions of k.  A hinge direction is therefore a nonzero integer
vector d with sum(d) = 0 and positive mass at most k, modulo positive scaling
and sign.  We orient it by making its first nonzero entry positive.

On x_1 <= ... <= x_n, summation by parts shows that this oriented hinge is
identically inactive exactly when every proper prefix sum of d is nonnegative.
All other primitive directions give distinct retained hinge rows.
"""

from __future__ import annotations

import argparse
from itertools import combinations
from math import gcd


def compositions(total: int, parts: int):
    """Yield positive ordered compositions of total into parts parts."""
    if parts == 1:
        yield (total,)
        return
    for cuts in combinations(range(1, total), parts - 1):
        points = (0, *cuts, total)
        yield tuple(points[index + 1] - points[index] for index in range(parts))


def primitive_rays(n: int, k: int) -> set[tuple[int, ...]]:
    """Enumerate canonical primitive zero-sum rays of positive mass <= k."""
    rays: set[tuple[int, ...]] = set()
    indices = tuple(range(n))

    for mass in range(1, k + 1):
        for positive_count in range(1, min(n - 1, mass) + 1):
            for positive_support in combinations(indices, positive_count):
                positive_set = set(positive_support)
                remaining = tuple(index for index in indices if index not in positive_set)
                for negative_count in range(1, min(len(remaining), mass) + 1):
                    for negative_support in combinations(remaining, negative_count):
                        for positive_values in compositions(mass, positive_count):
                            for negative_values in compositions(mass, negative_count):
                                direction = [0] * n
                                for index, value in zip(
                                    positive_support, positive_values, strict=True
                                ):
                                    direction[index] = value
                                for index, value in zip(
                                    negative_support, negative_values, strict=True
                                ):
                                    direction[index] = -value

                                # Quotient by d ~ -d before primitive reduction.
                                if next(value for value in direction if value) < 0:
                                    continue
                                scale = 0
                                for value in direction:
                                    scale = gcd(scale, abs(value))
                                rays.add(tuple(value // scale for value in direction))

    return rays


def row_counts(n: int, k: int) -> tuple[int, int, int]:
    rays = primitive_rays(n, k)
    inactive = 0
    for direction in rays:
        prefix = 0
        minimum_prefix = 0
        for value in direction[:-1]:
            prefix += value
            minimum_prefix = min(minimum_prefix, prefix)
        if minimum_prefix >= 0:
            inactive += 1
    retained = len(rays) - inactive
    return len(rays), inactive, retained


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=5)
    parser.add_argument("--max-n", type=int, default=11)
    args = parser.parse_args()

    print("n\tk\tprimitive_rays\tinactive_rays\thinge_rows\tlinear_rows\ttotal_rows")
    for n in range(args.min_n, args.max_n + 1):
        k = (n - 1) // 2
        rays, inactive, hinges = row_counts(n, k)
        print(f"{n}\t{k}\t{rays}\t{inactive}\t{hinges}\t{n}\t{hinges + n}")


if __name__ == "__main__":
    main()
