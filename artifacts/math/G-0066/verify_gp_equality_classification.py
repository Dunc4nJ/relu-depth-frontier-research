#!/usr/bin/env python3
"""Exact controls for the rho_Delta=3 generalized-permutohedron classification.

The structural proof is in README.md.  This verifier checks its finite
support-function, Boolean-Mobius, boundary, and provenance obligations.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from itertools import combinations
import json
from math import comb
from pathlib import Path
from typing import Any, Iterable


Q = Fraction
SCHEMA = "maxrelu-g0066-gp-equality-classification-v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_OUTPUT = HERE / "gp_equality_classification_v1.json"

BOUND_INPUTS = {
    "g0065_readme": (
        ROOT / "artifacts/math/G-0065/README.md",
        "7eb8ed94e48d3cbe3820f3534f465392551a6da3643aca8ff0828f38da260b13",
    ),
    "g0065_frozen_report": (
        ROOT / "artifacts/math/G-0065/single_zonotope_face_bounds_v1.json",
        "863f95db4b06c6d07365a0b3ba850eae8659612acfe59f25c791eec9068ed485",
    ),
    "bakaev_yehudayoff_pdf": (
        ROOT / "artifacts/math/G-0063/source/2607.03815.pdf",
        "4875ffd0fdc33624d8da00fa87709b88a6087587d27db21571f447aa23d2182b",
    ),
    "jochemko_ravichandran_pdf": (
        HERE / "source/1909.08448.pdf",
        "3cfe31dda7b663e49e57b35ffa22eaa60346f5eb7eb15a744b779be3a1f734ba",
    ),
    "jochemko_ravichandran_text": (
        HERE / "source/1909.08448.txt",
        "0ac4aa34f6fcf0ab553c8f6b904436f6df9bb5e12334e266b8889e954f06d24d",
    ),
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def qs(value: Q | int) -> str:
    return str(value)


def dot(left: Iterable[Q], right: Iterable[Q]) -> Q:
    return sum((a * b for a, b in zip(left, right, strict=True)), Q(0))


def basis(m: int, index: int) -> tuple[Q, ...]:
    return tuple(Q(int(i == index)) for i in range(m))


def normals(m: int) -> tuple[tuple[Q, ...], ...]:
    return tuple(
        tuple(Q(1 - m if j == i else 1) for j in range(m))
        for i in range(m)
    )


def support(vertices: Iterable[tuple[Q, ...]], direction: tuple[Q, ...]) -> Q:
    values = tuple(dot(vertex, direction) for vertex in vertices)
    if not values:
        raise ValueError("a polytope needs at least one vertex")
    return max(values)


def asymmetry_sums(vertices: Iterable[tuple[Q, ...]]) -> tuple[Q, Q]:
    vertices = tuple(vertices)
    m = len(vertices[0])
    qs_ = normals(m)
    B = sum((support(vertices, normal) for normal in qs_), Q(0))
    A = sum(
        (support(vertices, tuple(-entry for entry in normal)) for normal in qs_),
        Q(0),
    )
    return A, B


def tetrahedron_controls() -> list[dict[str, Any]]:
    rows = []
    for m in range(4, 12):
        checked = 0
        for subset in combinations(range(m), 4):
            vertices = tuple(basis(m, i) for i in subset)
            A, B = asymmetry_sums(vertices)
            if (A, B) != (Q(3 * m), Q(m)):
                raise AssertionError("ambient coordinate tetrahedron ratio mismatch")
            checked += 1
        rows.append(
            {
                "ambient_coordinate_count": m,
                "tetrahedra_checked": checked,
                "A": qs(3 * m),
                "B": qs(m),
                "rho": "3",
            }
        )
    return rows


def mobius(values: list[Q], m: int) -> list[Q]:
    coefficients = values.copy()
    for bit in range(m):
        step = 1 << bit
        for mask in range(1 << m):
            if mask & step:
                coefficients[mask] -= coefficients[mask ^ step]
    return coefficients


def d_m_controls() -> list[dict[str, Any]]:
    rows = []
    for m in range(5, 12):
        t = Q(m - 4, m * (m - 1))
        edge_count = comb(m, 2)
        edge_contribution = t * edge_count
        lambda_delta = Q(1) + edge_contribution
        lambda_minus_delta = Q(m - 1) + edge_contribution
        if lambda_delta != Q(m - 2, 2):
            raise AssertionError("lambda_Delta(D_m) mismatch")
        if lambda_minus_delta != Q(3 * (m - 2), 2):
            raise AssertionError("lambda_-Delta(D_m) mismatch")
        if lambda_minus_delta / lambda_delta != 3:
            raise AssertionError("rho_Delta(D_m) mismatch")

        full = (1 << m) - 1
        z = []
        for mask in range(1 << m):
            size = mask.bit_count()
            z.append(Q(int(mask == full)) + t * comb(size, 2))
        y = mobius(z, m)
        nonzero = {mask: value for mask, value in enumerate(y) if value}
        expected = {full: Q(1)}
        expected.update(
            {
                (1 << i) | (1 << j): t
                for i, j in combinations(range(m), 2)
            }
        )
        if nonzero != expected:
            raise AssertionError("unique signed-simplex coefficients mismatch")
        rows.append(
            {
                "ambient_coordinate_count": m,
                "t_m": qs(t),
                "edge_count": edge_count,
                "lambda_Delta": qs(lambda_delta),
                "lambda_minus_Delta": qs(lambda_minus_delta),
                "rho": "3",
                "mobius_nonzero_counts": {
                    "full_simplex": 1,
                    "edges": edge_count,
                    "other": 0,
                },
                "full_simplex_coefficient": "1",
                "coordinate_tetrahedron_nonnegative_sum_impossible": True,
            }
        )
    if Q(7 - 4, 7 * 6) != Q(1, 14) or Q(8 - 4, 8 * 7) != Q(1, 14):
        raise AssertionError("seven/eight face coefficient mismatch")
    return rows


def centrally_symmetric(points: tuple[tuple[Q, ...], ...]) -> bool:
    count = len(points)
    center = tuple(
        sum((point[i] for point in points), Q(0)) / count
        for i in range(len(points[0]))
    )
    point_set = set(points)
    return all(
        tuple(2 * center[i] - point[i] for i in range(len(center))) in point_set
        for point in points
    )


def coordinate_symmetry_controls() -> list[dict[str, Any]]:
    rows = []
    for m in range(1, 9):
        vertices = tuple(basis(m, i) for i in range(m))
        central_sizes = []
        for mask in range(1, 1 << m):
            subset = tuple(vertices[i] for i in range(m) if mask & (1 << i))
            if centrally_symmetric(subset):
                central_sizes.append(len(subset))
        if any(size > 2 for size in central_sizes):
            raise AssertionError("unexpected centrally symmetric simplex vertex subset")
        rows.append(
            {
                "coordinate_vertex_count": m,
                "nonempty_subsets_checked": (1 << m) - 1,
                "centrally_symmetric_subset_sizes": sorted(set(central_sizes)),
                "maximum_size": max(central_sizes),
            }
        )
    return rows


def hostile_control() -> dict[str, Any]:
    m = 5
    half = Q(1, 2)
    p0 = (half, half, Q(0), Q(0), Q(0))
    p1 = basis(m, 2)
    q0 = basis(m, 3)
    q1 = basis(m, 4)
    vertices = (p0, p1, q0, q1)
    A, B = asymmetry_sums(vertices)
    if (A, B, A / B) != (Q(15), Q(5), Q(3)):
        raise AssertionError("hostile equality example mismatch")
    cross_direction = tuple(q0[i] - p0[i] for i in range(m))
    nonzero = tuple(value for value in cross_direction if value)
    is_root_parallel = len(nonzero) == 2 and sum(cross_direction, Q(0)) == 0
    if is_root_parallel:
        raise AssertionError("hostile cross edge unexpectedly root-parallel")
    return {
        "P_vertices": [[qs(value) for value in p0], [qs(value) for value in p1]],
        "Q_vertices": [[qs(value) for value in q0], [qs(value) for value in q1]],
        "A": qs(A),
        "B": qs(B),
        "rho": qs(A / B),
        "chosen_cross_direction": [qs(value) for value in cross_direction],
        "chosen_cross_direction_is_root_parallel": False,
        "generalized_permutohedron": False,
    }


def verify_inputs() -> dict[str, Any]:
    report = {}
    for name, (path, expected) in BOUND_INPUTS.items():
        actual = sha256_path(path)
        if actual != expected:
            raise AssertionError(f"SHA-256 mismatch for {name}: {actual}")
        report[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": actual,
        }
    return report


def build_report() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "scope": {
            "classification": "nonpoint generalized permutohedra in P^2 with ambient standard-simplex rho equal to 3",
            "max11_consequence": "strict lower bound for the single-zonotope stabilizer subclass only",
            "unrestricted_MAX11_settled": False,
            "novelty_adjudicated": False,
        },
        "bound_inputs": verify_inputs(),
        "source_locators": {
            "bakaev_yehudayoff": "Theorems 9-10 and their proofs, physical PDF pages 6-11",
            "jochemko_ravichandran": "Proposition 2.1 and Theorems 2.2-2.3, physical PDF pages 4-5",
        },
        "coordinate_tetrahedron_controls": tetrahedron_controls(),
        "D_m_controls": d_m_controls(),
        "coordinate_simplex_central_symmetry_controls": coordinate_symmetry_controls(),
        "hostile_non_braid_control": hostile_control(),
        "single_zonotope_MAX11_consequence": {
            "g0065_equality_candidate": "(1/14) * graphical_zonotope(K_11)",
            "tie_face_sizes": [7, 8],
            "common_edge_coefficient": "1/14",
            "equality_candidate_faces_fail_P2": True,
            "conclusion": "lambda_Delta_10(Z) > 55/14",
            "scope": "Z zonotope and Delta_10 + Z in P^2",
        },
    }


def encoded(report: dict[str, Any]) -> bytes:
    return (json.dumps(report, indent=2, sort_keys=True) + "\n").encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-frozen", action="store_true")
    args = parser.parse_args()
    payload = encoded(build_report())
    if args.check_frozen:
        if not args.output.exists():
            raise SystemExit(f"missing frozen report: {args.output}")
        if args.output.read_bytes() != payload:
            raise SystemExit(f"frozen report differs: {args.output}")
        print(f"PASS {SCHEMA}: frozen report matches")
        return
    args.output.write_bytes(payload)
    print(f"WROTE {args.output}")


if __name__ == "__main__":
    main()
