#!/usr/bin/env python3
"""Count the exact symmetry-reduced template ansatz used for max_n certificates.

The action is simultaneous relabeling by S_n and exchange of the two multisets.
Burnside's lemma avoids enumerating the enormous raw pair space.
"""

from __future__ import annotations

import argparse
from collections import Counter
from math import comb, factorial


def partitions(total: int, maximum: int | None = None):
    if total == 0:
        yield ()
        return
    maximum = total if maximum is None else min(maximum, total)
    for first in range(maximum, 0, -1):
        for rest in partitions(total - first, first):
            yield (first, *rest)


def representative(cycle_type: tuple[int, ...]) -> tuple[int, ...]:
    permutation: list[int] = []
    base = 0
    for length in cycle_type:
        permutation.extend(base + (offset + 1) % length for offset in range(length))
        base += length
    return tuple(permutation)


def class_size(cycle_type: tuple[int, ...]) -> int:
    denominator = 1
    for length, multiplicity in Counter(cycle_type).items():
        denominator *= length**multiplicity * factorial(multiplicity)
    return factorial(sum(cycle_type)) // denominator


def edge_orbit_lengths(permutation: tuple[int, ...]) -> list[int]:
    n = len(permutation)
    edges = [(i, j) for i in range(n) for j in range(i, n)]
    edge_index = {edge: index for index, edge in enumerate(edges)}
    action = []
    for i, j in edges:
        image = tuple(sorted((permutation[i], permutation[j])))
        action.append(edge_index[image])

    seen = [False] * len(edges)
    lengths: list[int] = []
    for start in range(len(edges)):
        if seen[start]:
            continue
        current = start
        length = 0
        while not seen[current]:
            seen[current] = True
            length += 1
            current = action[current]
        lengths.append(length)
    return lengths


def fixed_multisets(orbit_lengths: list[int], cardinality: int) -> int:
    coefficients = [0] * (cardinality + 1)
    coefficients[0] = 1
    for length in orbit_lengths:
        updated = [0] * (cardinality + 1)
        for degree, coefficient in enumerate(coefficients):
            if coefficient == 0:
                continue
            for multiplicity in range((cardinality - degree) // length + 1):
                updated[degree + multiplicity * length] += coefficient
        coefficients = updated
    return coefficients[cardinality]


def template_count(n: int, k: int) -> int:
    burnside_sum = 0
    for cycle_type in partitions(n):
        permutation = representative(cycle_type)
        squared = tuple(permutation[permutation[index]] for index in range(n))
        fixed = fixed_multisets(edge_orbit_lengths(permutation), k)
        fixed_after_square = fixed_multisets(edge_orbit_lengths(squared), k)
        burnside_sum += class_size(cycle_type) * (fixed * fixed + fixed_after_square)
    divisor = 2 * factorial(n)
    quotient, remainder = divmod(burnside_sum, divisor)
    if remainder:
        raise AssertionError("Burnside sum is not divisible by the group order")
    return quotient


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-n", type=int, default=5)
    parser.add_argument("--max-n", type=int, default=11)
    args = parser.parse_args()

    print("n\tk\tedge_types\tmultisets\traw_unordered_pairs\tsymmetry_templates")
    for n in range(args.min_n, args.max_n + 1):
        k = (n - 1) // 2
        edge_types = comb(n + 1, 2)
        multisets = comb(edge_types + k - 1, k)
        raw_pairs = multisets * (multisets + 1) // 2
        print(f"{n}\t{k}\t{edge_types}\t{multisets}\t{raw_pairs}\t{template_count(n, k)}")


if __name__ == "__main__":
    main()
