#!/usr/bin/env python3
"""Exact controls for bias-free Boolean-cube universality.

For every nonempty T subseteq [n], the bias-free ridge with weights one on T
and -n off T evaluates to |U| exactly when a nonempty Boolean support U is
contained in T, and to zero otherwise.  The resulting scaled subset-zeta
matrix is invertible.  The theorem and its global-claim boundary are in
README.md; this program replays bounded exact controls only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator, Mapping


class ControlFailure(RuntimeError):
    """Raised when an exact universality control drifts."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlFailure(message)


def ridge_dot(
    n: int,
    ridge_support: int,
    point_support: int,
    off_weight: int | None = None,
) -> int:
    """Return w_T . 1_U for weights one on T and ``off_weight`` off T."""

    full = (1 << n) - 1
    require(0 < ridge_support <= full, "ridge support must be nonempty")
    require(0 <= point_support <= full, "point support outside cube")
    negative_weight = -n if off_weight is None else off_weight
    inside = (ridge_support & point_support).bit_count()
    outside = ((full ^ ridge_support) & point_support).bit_count()
    return inside + negative_weight * outside


def ridge_value(n: int, ridge_support: int, point_support: int) -> int:
    return max(0, ridge_dot(n, ridge_support, point_support))


def supersets(n: int, subset: int) -> Iterator[int]:
    """Yield every superset inside [n], including ``subset`` itself."""

    complement = ((1 << n) - 1) ^ subset
    extra = complement
    while True:
        yield subset | extra
        if extra == 0:
            break
        extra = (extra - 1) & complement


def mobius_coefficients(
    n: int, labels: Mapping[int, Fraction]
) -> tuple[dict[int, Fraction], int]:
    """Invert q(U)=sum_{T superset U} c(T) exactly."""

    coefficients: dict[int, Fraction] = {}
    terms = 0
    for ridge_support in range(1, 1 << n):
        total = Fraction(0)
        ridge_size = ridge_support.bit_count()
        for vertex in supersets(n, ridge_support):
            require(vertex != 0, "nonempty support acquired empty superset")
            sign = -1 if (vertex.bit_count() - ridge_size) % 2 else 1
            total += sign * labels[vertex] / vertex.bit_count()
            terms += 1
        coefficients[ridge_support] = total
    return coefficients, terms


def reconstruct_label(
    n: int, point_support: int, coefficients: Mapping[int, Fraction]
) -> tuple[Fraction, int]:
    if point_support == 0:
        return Fraction(0), 0
    total = Fraction(0)
    terms = 0
    for ridge_support in supersets(n, point_support):
        total += coefficients[ridge_support]
        terms += 1
    return point_support.bit_count() * total, terms


def evaluation_formula_controls() -> dict[str, Any]:
    pairs = 0
    triangular_entries = 0
    for n in range(2, 9):
        full = (1 << n) - 1
        for ridge_support in range(1, full + 1):
            for point_support in range(full + 1):
                value = ridge_value(n, ridge_support, point_support)
                expected = (
                    point_support.bit_count()
                    if point_support and point_support & ~ridge_support == 0
                    else 0
                )
                require(value == expected, f"ridge evaluation drift at n={n}")
                require(max(0, value) == value, "identity second ReLU changed a ridge")
                pairs += 1

        ordered = sorted(range(1, full + 1), key=lambda mask: (mask.bit_count(), mask))
        for row_index, point_support in enumerate(ordered):
            for column_index, ridge_support in enumerate(ordered):
                value = ridge_value(n, ridge_support, point_support)
                if column_index < row_index:
                    require(value == 0, f"zeta matrix acquired lower entry at n={n}")
                if column_index == row_index:
                    require(value == point_support.bit_count(), f"diagonal drift at n={n}")
                triangular_entries += 1

    n = 11
    full = (1 << n) - 1
    max11_spot_checks = 0
    for point_support in range(1, full + 1):
        least_bit = point_support & -point_support
        excluding = full ^ least_bit
        cases = (
            (point_support, point_support.bit_count()),
            (full, point_support.bit_count()),
            (excluding, 0),
        )
        for ridge_support, expected in cases:
            require(ridge_value(n, ridge_support, point_support) == expected, "MAX11 spot drift")
            max11_spot_checks += 1

    multiplicities = {str(size): math.comb(n, size) for size in range(1, n + 1)}
    determinant = math.prod(
        size ** math.comb(n, size) for size in range(1, n + 1)
    )
    determinant_decimal = str(determinant)
    return {
        "full_pairs_exhausted_n2_through_n8": pairs,
        "triangular_entries_checked_n2_through_n8": triangular_entries,
        "max11_spot_checks": max11_spot_checks,
        "max11_determinant_factor_multiplicities": multiplicities,
        "max11_determinant_decimal_digits": len(determinant_decimal),
        "max11_determinant_decimal_sha256": hashlib.sha256(
            determinant_decimal.encode("ascii")
        ).hexdigest(),
        "max11_determinant_nonzero": determinant != 0,
        "all_biases_zero": True,
        "identity_second_relu_checked": True,
    }


def arbitrary_label_control() -> dict[str, Any]:
    n = 8
    labels = {0: Fraction(0)}
    for vertex in range(1, 1 << n):
        labels[vertex] = Fraction(((17 * vertex + 5) % 29) - 14, 11)
    coefficients, inversion_terms = mobius_coefficients(n, labels)
    reconstruction_terms = 0
    for vertex in range(1 << n):
        reconstructed, terms = reconstruct_label(n, vertex, coefficients)
        require(reconstructed == labels[vertex], "arbitrary rational reconstruction failed")
        reconstruction_terms += terms
    return {
        "n": n,
        "cube_vertices_checked": 1 << n,
        "distinct_labels": len(set(labels.values())),
        "mobius_inversion_terms": inversion_terms,
        "reconstruction_terms": reconstruction_terms,
        "coefficient_field": "fractions.Fraction",
        "exact_reconstruction": True,
    }


def max11_control() -> dict[str, Any]:
    n = 11
    labels = {0: Fraction(0)}
    labels.update({vertex: Fraction(1) for vertex in range(1, 1 << n)})
    coefficients, inversion_terms = mobius_coefficients(n, labels)
    closed_form_checks = 0
    for ridge_support, coefficient in coefficients.items():
        size = ridge_support.bit_count()
        expected = Fraction(1, size * math.comb(n, size))
        require(coefficient == expected, "MAX11 closed coefficient formula drift")
        require(coefficient > 0, "MAX11 coefficient lost positivity")
        closed_form_checks += 1

    reconstruction_terms = 0
    for vertex in range(1 << n):
        reconstructed, terms = reconstruct_label(n, vertex, coefficients)
        require(reconstructed == labels[vertex], "MAX11 cube reconstruction failed")
        reconstruction_terms += terms

    return {
        "cube_vertices_checked": 1 << n,
        "nonempty_bias_free_ridges": (1 << n) - 1,
        "first_hidden_width": (1 << n) - 1,
        "identity_second_hidden_width": (1 << n) - 1,
        "second_neuron_fan_in": 1,
        "mobius_inversion_terms": inversion_terms,
        "reconstruction_terms": reconstruction_terms,
        "closed_positive_coefficient_checks": closed_form_checks,
        "closed_coefficient": "1/(|T|*binom(11,|T|))",
        "origin_value": "0",
        "nonempty_vertex_value": "1",
        "target_full_charge": "1",
        "exact_cube_reconstruction": True,
        "global_max11_claim": False,
    }


def hostile_control() -> dict[str, Any]:
    n = 4
    ridge_support = 0b0111
    point_support = 0b1111
    original = max(0, ridge_dot(n, ridge_support, point_support))
    mutated = max(0, ridge_dot(n, ridge_support, point_support, off_weight=-(n - 2)))
    require(original == 0, "original off-support weight leaked")
    require(mutated == 1, "weakened off-support weight mutation escaped")
    return {
        "off_support_weight_minus_n_value": original,
        "mutated_off_support_weight_minus_n_plus_2_value": mutated,
        "mutation_rejected": True,
    }


def run_controls() -> dict[str, Any]:
    return {
        "schema": "g0060-bias-free-subset-zeta-controls-v1",
        "arithmetic": "integers and fractions.Fraction",
        "theorem": (
            "Bias-free dense ReLU ridges indexed by nonempty subsets span exactly "
            "all standard Boolean-cube label vectors whose origin value is zero."
        ),
        "evaluation_formula_controls": evaluation_formula_controls(),
        "arbitrary_label_control": arbitrary_label_control(),
        "max11_control": max11_control(),
        "hostile_control": hostile_control(),
        "falsifier": (
            "A nonempty pair (U,T) violating g_T(1_U)=|U|*1{U subset T}, "
            "a zero scaled-zeta determinant, or an unreconstructed label with F(0)=0."
        ),
        "route_decision": (
            "Even after bias-free recession reduction, output values on the standard "
            "Boolean cube cannot obstruct unrestricted width; use cross-basepoint, wall, "
            "weight, or width/wiring information."
        ),
        "claim_boundary": (
            "This is exact cube interpolation, not a global MAX_n identity, a bounded-"
            "width result, a bounded-dense-row result, or a novelty claim."
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
