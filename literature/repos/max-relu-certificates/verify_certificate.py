"""Verify a symmetric construction of max(x_1, ..., x_n).

Each certificate term is a rational multiple of the symmetrization of

    max(sum(max(x_a, x_b) for (a, b) in left),
        sum(max(x_a, x_b) for (a, b) in right)).

Both the construction and the target are symmetric, so it is enough to compare
them on the cone x_1 <= ... <= x_n.
"""

import argparse
import json
import math
from collections.abc import Iterable
from fractions import Fraction
from itertools import permutations
from pathlib import Path
from typing import TypeAlias

from tqdm import tqdm

MaxPair: TypeAlias = tuple[int, int]
Side: TypeAlias = tuple[MaxPair, ...]
Vector: TypeAlias = tuple[int, ...]


def read_side(raw_side: Iterable[Iterable[int]], n: int) -> Side:
    side = []
    for raw_pair in raw_side:
        pair = tuple(raw_pair)
        if len(pair) != 2:
            raise ValueError("each endpoint pair must contain exactly two endpoints")
        a, b = pair
        if not (1 <= a <= b <= n):
            raise ValueError(f"invalid endpoint pair {(a, b)}")
        side.append((a - 1, b - 1))
    return tuple(side)


def read_pair(raw_pair: Iterable[Iterable[Iterable[int]]], n: int) -> tuple[Side, Side]:
    sides = tuple(raw_pair)
    if len(sides) != 2:
        raise ValueError("each term must contain exactly two sides")
    left, right = (read_side(side, n) for side in sides)
    if len(left) != len(right):
        raise ValueError("the two sides of a pair must have the same size")
    return left, right


def side_on_ordered_cone(side: Side, position: list[int]) -> Vector:
    coefficients = [0] * len(position)
    for a, b in side:
        coefficients[max(position[a], position[b])] += 1
    return tuple(coefficients)


def nonpositive_on_ordered_cone(direction: Vector) -> bool:
    """Test whether direction . x <= 0 whenever x_1 <= ... <= x_n.

    If direction sums to zero, summation by parts gives

        direction . x = -sum(prefix_i * (x_{i+1} - x_i)).

    Thus this is nonpositive exactly when all proper prefix sums are
    nonnegative.
    """
    if sum(direction) != 0:
        return False

    prefix_sum = 0
    for coefficient in direction[:-1]:
        prefix_sum += coefficient
        if prefix_sum < 0:
            return False
    return True


def symmetrized_pair(
    left: Side, right: Side, n: int
) -> tuple[Vector, dict[Vector, int]]:
    linear = [0] * n
    hinges: dict[Vector, int] = {}

    for order in permutations(range(n)):
        position = [0] * n
        for rank, label in enumerate(order):
            position[label] = rank

        left_form = side_on_ordered_cone(left, position)
        right_form = side_on_ordered_cone(right, position)
        # Lexicographic order gives every hinge a consistent orientation.
        base, other = sorted((left_form, right_form))
        direction = tuple(b - a for a, b in zip(base, other))

        for rank, coefficient in enumerate(base):
            linear[rank] += coefficient

        if nonpositive_on_ordered_cone(direction):
            continue

        # max(0, (k direction).x) = k max(0, direction.x) for k > 0.
        scale = math.gcd(*direction)
        primitive_direction = tuple(value // scale for value in direction)
        hinges[primitive_direction] = hinges.get(primitive_direction, 0) + scale

    return tuple(linear), hinges


def verify(path: Path) -> bool:
    certificate = json.loads(path.read_text(encoding="utf-8"))
    n = int(certificate["n"])

    terms = certificate["terms"]
    total_linear = [Fraction() for _ in range(n)]
    total_hinges: dict[Vector, Fraction] = {}

    print(f"certificate file: {path}")
    print(f"n: {n}")
    print(f"#terms: {len(terms)}")

    for term in tqdm(terms, unit="term"):
        coefficient = Fraction(term["coefficient"])
        if not coefficient:
            continue
        left, right = read_pair(term["pair"], n)
        linear, hinges = symmetrized_pair(left, right, n)

        for rank, value in enumerate(linear):
            total_linear[rank] += coefficient * value
        for direction, value in hinges.items():
            total_hinges[direction] = total_hinges.get(direction, Fraction()) + (
                coefficient * value
            )

    total_linear[-1] -= 1
    bad_linear = [(rank + 1, value) for rank, value in enumerate(total_linear) if value]
    bad_hinges = [
        (direction, value) for direction, value in sorted(total_hinges.items()) if value
    ]

    # Check if max(x_1, ..., x_n) - x_n = 0.
    verfied = not bad_linear and not bad_hinges

    return verfied


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("certificate", type=Path)
    args = parser.parse_args()

    verified = verify(args.certificate)

    print("OK" if verified else "Fail")

    if not verified:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
