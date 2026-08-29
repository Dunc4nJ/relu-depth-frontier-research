#!/usr/bin/env python3
"""Exact controls for Boolean-cube universality of dense--local mixed terms.

The proof and no-go boundary are in README.md.  This program exhausts the
one-hot basis table for n=2,...,11, checks exact arbitrary-label and MAX11 cube
reconstruction, and verifies that the dense parent changes every basis function
off the sampled cube.  It makes no global MAX representation claim.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence


class ControlFailure(RuntimeError):
    """Raised when an exact universality control drifts."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ControlFailure(message)


def relu(value: int) -> int:
    return max(0, value)


def mixed_hat_at_indicator(n: int, vertex: int, point: int) -> int:
    """Evaluate (14) at Boolean masks using the exact first-layer values."""

    require(0 <= vertex < 1 << n, "vertex mask outside cube")
    require(0 <= point < 1 << n, "point mask outside cube")
    dense = relu(point.bit_count() - n)
    local_hamming_sum = (vertex ^ point).bit_count()
    return relu(1 + 2 * dense - local_hamming_sum)


def mixed_hat_at_integer_point(
    n: int,
    vertex: int,
    point: Sequence[int],
    dense_coefficient: int = 2,
) -> int:
    """Evaluate the displayed ReLU network away from the Boolean cube."""

    require(len(point) == n, "point dimension drift")
    dense = relu(sum(point) - n)
    local_sum = 0
    for coordinate, value in enumerate(point):
        if (vertex >> coordinate) & 1:
            local_sum += relu(1 - value)
        else:
            local_sum += relu(value)
    return relu(1 + dense_coefficient * dense - local_sum)


def exhaustive_basis_controls() -> dict[str, Any]:
    pair_count = 0
    charge_histograms: dict[str, dict[str, int]] = {}
    dimension_summaries: list[dict[str, Any]] = []
    for n in range(2, 12):
        size = 1 << n
        histogram: dict[int, int] = {}
        for vertex in range(size):
            charge = 0
            for point in range(size):
                value = mixed_hat_at_indicator(n, vertex, point)
                require(value == int(point == vertex), f"basis drift at n={n}")
                sign = -1 if (n - point.bit_count()) % 2 else 1
                charge += sign * value
                pair_count += 1
            expected_charge = (-1) ** (n - vertex.bit_count())
            require(charge == expected_charge, f"basis charge drift at n={n}")
            histogram[charge] = histogram.get(charge, 0) + 1
        require(histogram == {-1: size // 2, 1: size // 2}, f"sign span drift at n={n}")
        charge_histograms[str(n)] = {str(key): value for key, value in sorted(histogram.items())}
        dimension_summaries.append(
            {
                "n": n,
                "cube_dimension": size,
                "first_width": 2 * n + 1,
                "basis_second_width": size,
                "second_fan_in": n + 1,
            }
        )
    return {
        "basis_pairs_exhausted_n2_through_n11": pair_count,
        "charge_histograms": charge_histograms,
        "dimension_summaries": dimension_summaries,
    }


def arbitrary_label_control() -> dict[str, Any]:
    n = 4
    size = 1 << n
    labels = {
        vertex: Fraction(((7 * vertex + 3) % 17) - 8, 7) for vertex in range(size)
    }
    for point in range(size):
        reconstructed = sum(
            (
                labels[vertex] * mixed_hat_at_indicator(n, vertex, point)
                for vertex in range(size)
            ),
            Fraction(0),
        )
        require(reconstructed == labels[point], "arbitrary rational label reconstruction failed")
    return {
        "n": n,
        "cube_vertices_checked": size,
        "coefficient_field": "fractions.Fraction",
        "distinct_labels": len(set(labels.values())),
        "exact_reconstruction": True,
    }


def max11_cube_control() -> dict[str, Any]:
    n = 11
    size = 1 << n
    checked_terms = 0
    for point in range(size):
        reconstructed = 0
        for vertex in range(1, size):
            reconstructed += mixed_hat_at_indicator(n, vertex, point)
            checked_terms += 1
        require(reconstructed == int(point != 0), "MAX11 cube reconstruction failed")
    return {
        "cube_vertices_checked": size,
        "nonzero_vertex_second_neurons": size - 1,
        "basis_term_evaluations": checked_terms,
        "target_full_charge": 1,
        "exact_cube_reconstruction": True,
        "global_max11_claim": False,
    }


def dense_parent_controls() -> dict[str, Any]:
    checks = 0
    for n in range(2, 12):
        point = (2,) * n
        for vertex in range(1 << n):
            with_dense = mixed_hat_at_integer_point(n, vertex, point, dense_coefficient=2)
            without_dense = mixed_hat_at_integer_point(n, vertex, point, dense_coefficient=0)
            require(with_dense != without_dense, f"dense parent redundant at n={n}")
            checks += 1
    return {
        "ray_point": "2*(1,...,1)",
        "basis_neurons_checked_n2_through_n11": checks,
        "dense_parent_changes_every_basis_neuron": True,
    }


def run_controls() -> dict[str, Any]:
    return {
        "schema": "g0060-mixed-cube-universality-controls-v1",
        "arithmetic": "integers and fractions.Fraction",
        "theorem": (
            "One shared dense first neuron plus 2n coordinate-local first neurons "
            "and dense-local mixed second neurons span every function on {0,1}^n."
        ),
        "exhaustive_basis_controls": exhaustive_basis_controls(),
        "arbitrary_label_control": arbitrary_label_control(),
        "max11_cube_control": max11_cube_control(),
        "dense_parent_controls": dense_parent_controls(),
        "falsifier": (
            "A Boolean pair (u,v) with H_v(u) different from the Kronecker delta, "
            "or a cube label vector not reconstructed by the displayed basis."
        ),
        "route_decision": (
            "Single-cube values and Mobius coefficients cannot obstruct unrestricted "
            "dense-local mixing; use cross-basepoint, wall, or width/wiring structure."
        ),
        "claim_boundary": (
            "This is exact finite-set interpolation, not a global MAX_n identity, an "
            "unrestricted width lower bound, or a novelty claim."
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
