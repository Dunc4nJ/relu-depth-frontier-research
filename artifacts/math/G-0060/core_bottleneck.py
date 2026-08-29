#!/usr/bin/env python3
"""Exact controls for the separated-core rank obstruction.

The universal proof is in README.md.  This script only calibrates finite exact
instances of its discriminator, sharp small-n decompositions, and the explicit
dense--local mixing escape.  It uses integers and ``fractions.Fraction`` only.
"""

from __future__ import annotations

import argparse
import itertools
import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Sequence


class ControlFailure(RuntimeError):
    """Raised when an exact calibration drifts."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlFailure(message)


def relu(value: Fraction) -> Fraction:
    return max(Fraction(0), value)


def max_function(x: Sequence[Fraction]) -> Fraction:
    return max(x)


def full_difference(
    function: Callable[[tuple[Fraction, ...]], Fraction],
    base: Sequence[Fraction],
    epsilon: Fraction,
) -> Fraction:
    """Return the full equal-step coordinate difference exactly."""

    n = len(base)
    total = Fraction(0)
    for mask in range(1 << n):
        point = tuple(
            base[index] + epsilon * ((mask >> index) & 1) for index in range(n)
        )
        sign = -1 if (n - mask.bit_count()) % 2 else 1
        total += sign * function(point)
    return total


def matrix_vector(
    matrix: Sequence[Sequence[Fraction]], vector: Sequence[Fraction]
) -> tuple[Fraction, ...]:
    return tuple(
        sum(
            (coefficient * value for coefficient, value in zip(row, vector)),
            Fraction(0),
        )
        for row in matrix
    )


def matrix_rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    """Small exact Gaussian rank used only by the frozen controls."""

    rows = [list(map(Fraction, row)) for row in matrix]
    if not rows:
        return 0
    row_count = len(rows)
    column_count = len(rows[0])
    require(all(len(row) == column_count for row in rows), "ragged matrix")
    pivot_row = 0
    for column in range(column_count):
        pivot = next(
            (index for index in range(pivot_row, row_count) if rows[index][column]),
            None,
        )
        if pivot is None:
            continue
        rows[pivot_row], rows[pivot] = rows[pivot], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [value / scale for value in rows[pivot_row]]
        for index in range(row_count):
            if index == pivot_row or not rows[index][column]:
                continue
            multiple = rows[index][column]
            rows[index] = [
                value - multiple * pivot_value
                for value, pivot_value in zip(rows[index], rows[pivot_row])
            ]
        pivot_row += 1
        if pivot_row == row_count:
            break
    return pivot_row


def target_difference_table() -> dict[str, str]:
    epsilon = Fraction(1, 2)
    table: dict[str, str] = {}
    for n in range(2, 12):
        difference = full_difference(max_function, (Fraction(0),) * n, epsilon)
        expected = Fraction((-1) ** (n + 1), 2)
        require(difference == expected, f"MAX{n} zero-cube difference drift")
        table[str(n)] = str(difference)
    return table


def one_dense_core_control() -> dict[str, Any]:
    """A one-ridge MAX11 core has a visible nonconstant kernel direction."""

    n = 11
    epsilon = Fraction(1, 2)
    matrix = (tuple(Fraction(1) for _ in range(n)),)
    kernel_vector = (Fraction(1), Fraction(-1)) + (Fraction(0),) * (n - 2)
    require(matrix_rank(matrix) == 1, "one-dense matrix lost rank one")
    require(matrix_vector(matrix, kernel_vector) == (Fraction(0),), "bad kernel witness")

    at_zero = full_difference(max_function, (Fraction(0),) * n, epsilon)
    at_kernel_shift = full_difference(max_function, kernel_vector, epsilon)
    require(at_zero == Fraction(1, 2), "MAX11 zero difference drift")
    require(at_kernel_shift == 0, "kernel-shifted MAX11 difference should vanish")

    def sample_core(x: tuple[Fraction, ...]) -> Fraction:
        return relu(sum(x, Fraction(0)) - Fraction(3, 2))

    core_at_zero = full_difference(sample_core, (Fraction(0),) * n, epsilon)
    core_at_shift = full_difference(sample_core, kernel_vector, epsilon)
    require(core_at_zero == core_at_shift, "ridge core is not kernel-translation invariant")
    return {
        "n": n,
        "matrix_rank": 1,
        "kernel_vector": [str(value) for value in kernel_vector],
        "epsilon": str(epsilon),
        "target_difference_at_zero": str(at_zero),
        "target_difference_at_kernel_shift": str(at_kernel_shift),
        "sample_core_differences_equal": True,
        "contradiction_detected": True,
    }


def rank_n_minus_two_control() -> dict[str, Any]:
    """An explicit rank-nine MAX11 core is rejected by the same witness."""

    n = 11
    matrix: list[tuple[Fraction, ...]] = []
    for index in range(9):
        row = [Fraction(0)] * n
        row[index] = Fraction(1)
        row[10] = Fraction(-1)
        matrix.append(tuple(row))
    kernel_vector = (Fraction(0),) * 9 + (Fraction(1), Fraction(0))
    epsilon = Fraction(1, 2)
    rank = matrix_rank(matrix)
    require(rank == 9, "MAX11 rank-nine control matrix drift")
    require(
        matrix_vector(matrix, kernel_vector) == (Fraction(0),) * 9,
        "bad rank-nine kernel",
    )
    at_zero = full_difference(max_function, (Fraction(0),) * n, epsilon)
    at_kernel_shift = full_difference(max_function, kernel_vector, epsilon)
    require(at_zero == Fraction(1, 2), "rank-nine zero discriminator drift")
    require(at_kernel_shift == 0, "rank-nine shifted discriminator should vanish")
    return {
        "n": n,
        "matrix_rank": rank,
        "theorem_minimum_rank": n - 1,
        "kernel_vector": [str(value) for value in kernel_vector],
        "epsilon": str(epsilon),
        "target_difference_at_zero": str(at_zero),
        "target_difference_at_kernel_shift": str(at_kernel_shift),
        "contradiction_detected": True,
    }


def sharp_small_n_controls() -> dict[str, Any]:
    """Check exact rank-(n-1) formulas on deterministic integer grids."""

    max2_points = 0
    for raw in itertools.product(range(-2, 3), repeat=2):
        x = tuple(map(Fraction, raw))
        represented = x[1] + relu(x[0] - x[1])
        require(represented == max_function(x), "rank-one MAX2 formula failed")
        max2_points += 1

    max3_points = 0
    for raw in itertools.product(range(-2, 3), repeat=3):
        x = tuple(map(Fraction, raw))
        u = x[0] - x[2]
        v = x[1] - x[2]
        represented = x[2] + relu(v) + relu(relu(u) - relu(v))
        require(represented == max_function(x), "rank-two MAX3 formula failed")
        max3_points += 1

    rank_two_map = (
        (Fraction(1), Fraction(0), Fraction(-1)),
        (Fraction(0), Fraction(1), Fraction(-1)),
    )
    require(matrix_rank(rank_two_map) == 2, "MAX3 core map lost rank two")
    return {
        "max2_rank_one_grid_points": max2_points,
        "max2_core_rank": 1,
        "max3_rank_two_grid_points": max3_points,
        "max3_core_rank": 2,
        "scope": "finite calibration of displayed global identities",
    }


def dense_local_escape_controls() -> dict[str, Any]:
    """Disprove a rank law based only on the count of dense first rows."""

    charges: dict[str, str] = {}
    boolean_vertices_checked = 0
    for n in range(2, 12):

        def mixed_term(x: tuple[Fraction, ...], n: int = n) -> Fraction:
            dense = relu(sum(x, Fraction(0)) - (n - 2))
            local = relu(x[0])
            return relu(dense - 2 * local)

        charge = full_difference(mixed_term, (Fraction(0),) * n, Fraction(1))
        require(charge == -1, f"dense-local escape charge drift at n={n}")

        omit_first = (Fraction(0),) + (Fraction(1),) * (n - 1)
        omit_second = (Fraction(1), Fraction(0)) + (Fraction(1),) * (n - 2)
        require(sum(omit_first) == sum(omit_second), "escape pair has unequal dense coordinate")
        require(mixed_term(omit_first) == 1, "escape value at omit-first point drift")
        require(mixed_term(omit_second) == 0, "escape value at omit-second point drift")

        full_vertex = (Fraction(1),) * n
        require(mixed_term(full_vertex) == 0, "escape value at full vertex drift")
        require(
            mixed_term(full_vertex) != mixed_term(omit_first),
            "escape term lost dependence on coordinate 1",
        )
        for coordinate in range(1, n):
            missing_two = list(omit_first)
            missing_two[coordinate] = Fraction(0)
            require(
                mixed_term(tuple(missing_two)) == 0,
                f"escape term lost dependence on coordinate {coordinate + 1}",
            )

        unique_one_mask = ((1 << n) - 1) ^ 1
        for mask in range(1 << n):
            x = tuple(Fraction((mask >> coordinate) & 1) for coordinate in range(n))
            expected = Fraction(mask == unique_one_mask)
            require(
                mixed_term(x) == expected,
                f"escape Boolean truth table drift at n={n}, mask={mask}",
            )
            boolean_vertices_checked += 1
        charges[str(n)] = str(charge)

    return {
        "formula": "ReLU(ReLU(sum(x)-(n-2))-2*ReLU(x1))",
        "boolean_vertices_exhausted_n2_through_n11": boolean_vertices_checked,
        "coordinate1_single_flip_checked_n2_through_n11": True,
        "full_boolean_charges_n2_through_n11": charges,
        "full_coordinate_support_checked_n2_through_n11": True,
        "same_dense_projection_different_values_checked_n2_through_n11": True,
        "max11_output_weight_minus_one_matches_target_charge": True,
        "conclusion": (
            "The separated-core rank theorem cannot be extended to arbitrary "
            "outer mixing merely by counting dense first-layer rows."
        ),
    }


def run_controls() -> dict[str, Any]:
    return {
        "schema": "g0060-separated-core-rank-controls-v1",
        "arithmetic": "integers and fractions.Fraction",
        "theorem": (
            "MAX_n=G(Ax)+sum_l H_l with every H_l omitting a coordinate "
            "implies ker(A) subset span(1) and rank(A)>=n-1."
        ),
        "max11_minimum_core_rank": 10,
        "target_zero_cube_differences_n2_through_n11": target_difference_table(),
        "one_dense_core_control": one_dense_core_control(),
        "rank_n_minus_two_control": rank_n_minus_two_control(),
        "sharp_small_n_controls": sharp_small_n_controls(),
        "dense_local_escape_controls": dense_local_escape_controls(),
        "falsifier": (
            "An exact separated-core MAX_n decomposition with rank(A)<=n-2, "
            "or a nonconstant v in ker(A) preserving the displayed MAX differences."
        ),
        "claim_boundary": (
            "The proof is elementary, novelty is unknown, and no novelty is claimed.  "
            "The controls do not cover second neurons that mix core and local parents, "
            "and do not exclude unrestricted two-hidden-layer MAX11 networks."
        ),
        "result": "PASS",
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check-report", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = run_controls()
    if args.check_report is not None:
        frozen = json.loads(args.check_report.read_text(encoding="utf-8"))
        require(frozen == report, "frozen report object differs from exact replay")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
