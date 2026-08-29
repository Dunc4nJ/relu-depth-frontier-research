"""Independent direct-definition checks for the sparse ordered-cone accumulator.

These finite point comparisons are implementation-oracle tests only.  They do
not establish a certificate identity: agreement at sampled points is never an
acceptance rule.  The production verifier still accepts solely from its exact
zero-hinge and target-vector criteria after a complete census.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import permutations
import json
import random
import unittest

from cleanroom.maxrelu import (
    SubjectSpec,
    parse_certificate_bytes,
    verify_certificate,
)


def _fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def _parse_synthetic(
    subject_id: str,
    n: int,
    k: int,
    terms: list[dict[str, object]],
):
    raw = json.dumps(
        {"n": n, "terms": terms},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return parse_certificate_bytes(
        raw,
        SubjectSpec(
            subject_id=subject_id,
            filename=f"{subject_id}.json",
            n=n,
            k=k,
            term_count=len(terms),
        ),
    )


def _direct_definition_value(certificate, point: tuple[Fraction, ...]) -> Fraction:
    """Evaluate the defining nested maxima, without production helpers."""

    total = Fraction(0)
    for term in certificate.terms:
        for permutation in permutations(range(certificate.n)):
            left = sum(
                (
                    max(point[permutation[a - 1]], point[permutation[b - 1]])
                    for a, b in term.left
                ),
                Fraction(0),
            )
            right = sum(
                (
                    max(point[permutation[a - 1]], point[permutation[b - 1]])
                    for a, b in term.right
                ),
                Fraction(0),
            )
            total += term.coefficient * max(left, right)
    return total


def _sparse_value(result, point: tuple[Fraction, ...]) -> Fraction:
    linear = sum(
        (coefficient * value for coefficient, value in zip(result.residual.linear, point)),
        Fraction(0),
    )
    hinges = Fraction(0)
    for direction, coefficient in result.residual.hinges:
        argument = sum(
            (weight * value for weight, value in zip(direction, point)),
            Fraction(0),
        )
        hinges += coefficient * max(argument, Fraction(0))
    return linear + hinges


def _identity_side_counts(side, n: int) -> tuple[int, ...]:
    counts = [0] * n
    for a, b in side:
        counts[max(a, b) - 1] += 1
    return tuple(counts)


def _ordered_points(n: int, seed: int) -> tuple[tuple[Fraction, ...], ...]:
    rng = random.Random(seed)
    points: list[tuple[Fraction, ...]] = [
        tuple(Fraction(0) for _ in range(n)),
        tuple(Fraction(index - n, 1) for index in range(n)),
        tuple(Fraction(index * index - n, 2) for index in range(n)),
    ]
    for _ in range(5):
        coordinates = [
            Fraction(rng.randint(-9, 9), rng.choice((1, 2, 3, 5)))
            for _ in range(n)
        ]
        points.append(tuple(sorted(coordinates)))
    return tuple(points)


def _hand_authored_cases():
    # The first term has mixed direction (1,-2,1) at the identity labelling;
    # the second reverses its sides, exercising the opposite raw orientation.
    yield _parse_synthetic(
        "oracle-hand-n3",
        3,
        2,
        [
            {
                "coefficient": "2/3",
                "pair": [
                    [[2, 2], [2, 2]],
                    [[1, 1], [3, 3]],
                ],
            },
            {
                "coefficient": "-5/7",
                "pair": [
                    [[1, 1], [3, 3]],
                    [[2, 2], [2, 2]],
                ],
            },
            {
                "coefficient": "1/4",
                "pair": [
                    [[1, 2], [1, 2]],
                    [[2, 3], [3, 3]],
                ],
            },
        ],
    )

    yield _parse_synthetic(
        "oracle-hand-n4",
        4,
        3,
        [
            {
                "coefficient": "-3/5",
                "pair": [
                    [[1, 4], [2, 2], [2, 2]],
                    [[1, 1], [2, 3], [4, 4]],
                ],
            },
            {
                "coefficient": "7/6",
                "pair": [
                    [[1, 3], [2, 4], [3, 3]],
                    [[1, 2], [1, 2], [4, 4]],
                ],
            },
        ],
    )


def _generated_cases():
    rng = random.Random(0xE002A)
    coefficient_pool = (
        Fraction(1),
        Fraction(-1),
        Fraction(1, 2),
        Fraction(-2, 3),
        Fraction(3, 5),
        Fraction(-7, 4),
    )
    for case_index in range(24):
        n = 2 + case_index % 3
        k = 1 + case_index % 3
        pair_pool = [
            (a, b)
            for a in range(1, n + 1)
            for b in range(a, n + 1)
        ]
        terms: list[dict[str, object]] = []
        for _ in range(1 + case_index % 4):
            coefficient = rng.choice(coefficient_pool)
            sides = []
            for _side_index in range(2):
                side = [list(rng.choice(pair_pool)) for _ in range(k)]
                sides.append(side)
            terms.append(
                {
                    "coefficient": _fraction_text(coefficient),
                    "pair": sides,
                }
            )
        yield _parse_synthetic(
            f"oracle-generated-{case_index:02d}", n, k, terms
        )


class DirectDefinitionOracleTests(unittest.TestCase):
    def test_sparse_accumulator_equals_brute_force_on_diverse_exact_cases(self) -> None:
        saw_loop = False
        saw_repetition = False
        saw_negative = False
        saw_rational = False
        saw_nonzero_hinge = False
        checked_points = 0

        certificates = tuple(_hand_authored_cases()) + tuple(_generated_cases())
        orientation_case = certificates[0]
        raw_directions = []
        for term in orientation_case.terms[:2]:
            left = _identity_side_counts(term.left, orientation_case.n)
            right = _identity_side_counts(term.right, orientation_case.n)
            raw_directions.append(tuple(b - a for a, b in zip(left, right)))
        self.assertEqual(raw_directions, [(1, -2, 1), (-1, 2, -1)])

        for case_index, certificate in enumerate(certificates):
            result = verify_certificate(certificate)
            self.assertTrue(result.census.complete)
            self.assertNotEqual(result.outcome, "INCOMPLETE")
            saw_nonzero_hinge |= bool(result.residual.hinges)

            for term in certificate.terms:
                saw_negative |= term.coefficient < 0
                saw_rational |= term.coefficient.denominator != 1
                for side in (term.left, term.right):
                    saw_loop |= any(a == b for a, b in side)
                    saw_repetition |= len(set(side)) != len(side)

            for point in _ordered_points(certificate.n, 1000 + case_index):
                direct = _direct_definition_value(certificate, point)
                sparse = _sparse_value(result, point)
                self.assertEqual(
                    sparse,
                    result.integer_scale * direct,
                    msg=(certificate.subject_id, point),
                )
                checked_points += 1

        self.assertEqual(len(certificates), 26)
        self.assertEqual(checked_points, 26 * 8)
        self.assertTrue(saw_loop)
        self.assertTrue(saw_repetition)
        self.assertTrue(saw_negative)
        self.assertTrue(saw_rational)
        self.assertTrue(saw_nonzero_hinge)


if __name__ == "__main__":
    unittest.main()
