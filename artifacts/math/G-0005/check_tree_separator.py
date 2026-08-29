#!/usr/bin/env python3
"""Exact checks for the balanced two-coloured tree-template separator.

The proof is in TREE_TEMPLATE_SEPARATOR.md.  This program is corroborative: it directly sums the
four {0,1,2}-assignment orbits, exhausts all labelled balanced colourings at n=5, samples larger
odd arities deterministically, and requires a non-tree negative control to break the separator.
"""

from __future__ import annotations

import argparse
from itertools import combinations, product
from math import factorial
import random
from typing import Iterable

Edge = tuple[int, int]


def phi(assignment: tuple[int, ...], red: tuple[Edge, ...], blue: tuple[Edge, ...]) -> int:
    def side(edges: tuple[Edge, ...]) -> int:
        return sum(max(assignment[a], assignment[b]) for a, b in edges)

    return max(side(red), side(blue))


def assignment_sum(
    n: int, red: tuple[Edge, ...], blue: tuple[Edge, ...], ones: int, twos: int
) -> int:
    vertices = tuple(range(n))
    total = 0
    for high in combinations(vertices, twos):
        high_set = set(high)
        remaining = tuple(v for v in vertices if v not in high_set)
        for middle in combinations(remaining, ones):
            values = [0] * n
            for v in middle:
                values[v] = 1
            for v in high:
                values[v] = 2
            total += phi(tuple(values), red, blue)
    return total


def symmetrized_orbit_value(
    n: int, red: tuple[Edge, ...], blue: tuple[Edge, ...], ones: int, twos: int
) -> int:
    zeroes = n - ones - twos
    return (
        factorial(zeroes)
        * factorial(ones)
        * factorial(twos)
        * assignment_sum(n, red, blue, ones, twos)
    )


def coefficients(n: int) -> tuple[int, int, int, int]:
    return (
        12 * n * (n - 2) * (n - 3),
        -5 * n * (n - 2) * (n - 3),
        -4 * n * (n - 4) * (n - 2),
        -(n - 3) * (3 * n * n - 2 * n + 4),
    )


def separator_value(n: int, red: tuple[Edge, ...], blue: tuple[Edge, ...]) -> int:
    cz, cu, cv, cw = coefficients(n)
    values = (
        symmetrized_orbit_value(n, red, blue, 2, n - 4),
        symmetrized_orbit_value(n, red, blue, 0, n - 4),
        symmetrized_orbit_value(n, red, blue, 0, n - 3),
        symmetrized_orbit_value(n, red, blue, 0, n - 2),
    )
    return sum(c * value for c, value in zip((cz, cu, cv, cw), values, strict=True))


def tree_from_pruefer(sequence: Iterable[int], n: int) -> tuple[Edge, ...]:
    sequence = tuple(sequence)
    degree = [1] * n
    for vertex in sequence:
        degree[vertex] += 1
    edges: list[Edge] = []
    for vertex in sequence:
        leaf = next(index for index, value in enumerate(degree) if value == 1)
        edges.append(tuple(sorted((leaf, vertex))))
        degree[leaf] -= 1
        degree[vertex] -= 1
    last = tuple(index for index, value in enumerate(degree) if value == 1)
    if len(last) != 2:
        raise AssertionError("invalid Prüfer decoder state")
    edges.append(tuple(sorted(last)))
    return tuple(edges)


def check_colouring(n: int, edges: tuple[Edge, ...], red_indices: tuple[int, ...]) -> None:
    k = (n - 1) // 2
    chosen = set(red_indices)
    red = tuple(edges[index] for index in red_indices)
    blue = tuple(edge for index, edge in enumerate(edges) if index not in chosen)
    if len(red) != k or len(blue) != k:
        raise AssertionError("unbalanced colouring")
    value = separator_value(n, red, blue)
    if value != 0:
        raise AssertionError((n, edges, red_indices, value))


def exhaustive_n5() -> int:
    n = 5
    checked = 0
    for sequence in product(range(n), repeat=n - 2):
        edges = tree_from_pruefer(sequence, n)
        for red_indices in combinations(range(n - 1), (n - 1) // 2):
            check_colouring(n, edges, red_indices)
            checked += 1
    return checked


def random_checks(n: int, trials: int, generator: random.Random) -> int:
    k = (n - 1) // 2
    for _ in range(trials):
        edges = list(tree_from_pruefer((generator.randrange(n) for _ in range(n - 2)), n))
        generator.shuffle(edges)
        check_colouring(n, tuple(edges), tuple(range(k)))
    return trials


def negative_control() -> int:
    # A simple balanced two-coloured graph on 11 vertices that is not a tree.
    red = ((4, 5), (5, 10), (5, 9), (3, 8), (5, 6))
    blue = ((8, 10), (0, 7), (2, 4), (3, 10), (1, 5))
    value = separator_value(11, red, blue)
    if value == 0:
        raise AssertionError("non-tree negative control unexpectedly satisfied the separator")
    return value


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--random-trials", type=int, default=250)
    args = parser.parse_args()
    if args.random_trials < 0:
        raise SystemExit("--random-trials must be nonnegative")

    for n in (5, 7, 9, 11):
        if sum(coefficients(n)) != 12:
            raise AssertionError(f"coefficient sum failed at n={n}")

    exact = exhaustive_n5()
    generator = random.Random(20260829)
    sampled = {
        n: random_checks(n, args.random_trials, generator) for n in (7, 9, 11)
    }
    control = negative_control()
    print(f"exhaustive labelled balanced n=5 colourings: {exact}")
    print(f"deterministic random tree checks: {sampled}")
    print(f"non-tree negative-control separator value: {control}")
    print("MAX_n separator value at every checked odd n: 24")
    print("OK")


if __name__ == "__main__":
    main()
