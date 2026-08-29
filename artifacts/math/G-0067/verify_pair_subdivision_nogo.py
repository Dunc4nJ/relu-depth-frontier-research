#!/usr/bin/env python3
"""Exact controls for the G-0067 maximum-coordinate-cell P^2 no-go."""

from __future__ import annotations

from fractions import Fraction as Q
import hashlib
import itertools
import json
from pathlib import Path
from typing import Iterable, Sequence

import z3


Point = tuple[Q, ...]


def subsets(indices: Iterable[int]) -> Iterable[tuple[int, ...]]:
    values = tuple(indices)
    for size in range(len(values) + 1):
        yield from itertools.combinations(values, size)


def sum_z3(values: Iterable[z3.ArithRef | int]) -> z3.ArithRef:
    return z3.Sum(*tuple(values))


def type_cone_equivalence(dimension: int) -> None:
    """Check the full subset inequalities iff the d complement inequalities."""
    c = [z3.Real(f"c_{dimension}_{i}") for i in range(dimension)]
    total = sum_z3(c)
    complete = []
    for i in range(dimension):
        for subset in subsets(j for j in range(dimension) if j != i):
            complete.append(
                (len(subset) + 1) * c[i] >= sum_z3(c[j] for j in subset)
            )
    compressed = [(dimension + 1) * c[i] >= total for i in range(dimension)]

    solver = z3.Solver()
    solver.add(*complete, z3.Or(*(z3.Not(item) for item in compressed)))
    assert solver.check() == z3.unsat

    solver = z3.Solver()
    solver.add(*compressed, z3.Or(*(z3.Not(item) for item in complete)))
    assert solver.check() == z3.unsat

    # The only zero-total point is zero; all other cone points have c_i>0.
    solver = z3.Solver()
    solver.add(*compressed, total == 0, z3.Or(*(value != 0 for value in c)))
    assert solver.check() == z3.unsat


def candidate_vertex(c: Sequence[Q], active_upper: frozenset[int]) -> Point:
    denominator = len(active_upper) + 1
    coordinate_sum = sum((c[i] for i in active_upper), Q(0)) / denominator
    return tuple(
        c[i] - coordinate_sum if i in active_upper else Q(0)
        for i in range(len(c))
    )


def ray_vertex_control(dimension: int) -> dict[str, int]:
    """Reconstruct every orthant ray and its pyramid-over-D_(d-1) vertices."""
    counts = set()
    for distinguished in range(dimension):
        c = tuple(Q(2 if i == distinguished else 1) for i in range(dimension))
        vertices = {
            candidate_vertex(c, frozenset(active))
            for active in subsets(range(dimension))
        }
        apex = tuple(Q(1 if i == distinguished else 0) for i in range(dimension))
        expected = {apex}
        for active in subsets(i for i in range(dimension) if i != distinguished):
            expected.add(tuple(
                Q(1, len(active) + 1) if i in active else Q(0)
                for i in range(dimension)
            ))
        assert vertices == expected
        counts.add(len(vertices))

    # (1/(d+1)) times the sum of all ray support vectors is the all-one vector.
    rays = [
        tuple(Q(2 if coordinate == ray else 1) for coordinate in range(dimension))
        for ray in range(dimension)
    ]
    reconstructed = tuple(
        sum((ray[coordinate] for ray in rays), Q(0)) / (dimension + 1)
        for coordinate in range(dimension)
    )
    assert reconstructed == (Q(1),) * dimension
    assert counts == {2 ** (dimension - 1) + 1}
    return {"ray_count": dimension, "vertices_per_ray": counts.pop()}


def reflection_membership(
    solver: z3.Solver,
    center: Sequence[z3.ArithRef],
    axis: int,
    supports: Sequence[z3.ArithRef | Q],
) -> None:
    """Require the reflection of (c_axis/2)e_axis to lie in P(c)."""
    c_axis = supports[axis]
    reflection = [
        2 * center[i] - (c_axis / 2 if i == axis else 0)
        for i in range(len(center))
    ]
    solver.add(*(coordinate >= 0 for coordinate in reflection))
    total = sum_z3(reflection)
    solver.add(*(total + reflection[i] <= supports[i] for i in range(len(center))))


def parametric_three_axis_query(dimension: int, proof: bool = False) -> tuple[str, str | None]:
    """No center reflects three axis vertices for any nonzero type-cone point."""
    lambdas = [z3.Real(f"lambda_{dimension}_{i}") for i in range(dimension)]
    supports = [1 + value for value in lambdas]  # Normalize L=sum(lambda)=1.
    center = [z3.Real(f"q_{dimension}_{i}") for i in range(dimension)]
    solver = z3.Solver()
    solver.add(*(value >= 0 for value in lambdas), sum_z3(lambdas) == 1)
    for axis in (0, 1, 2):
        reflection_membership(solver, center, axis, supports)
    result = solver.check()
    proof_hash = None
    if proof:
        assert result == z3.unsat
        encoded = str(solver.proof()).encode()
        proof_hash = hashlib.sha256(encoded).hexdigest()
    return str(result), proof_hash


def group_center_sat(dimension: int, axes: frozenset[int]) -> bool:
    center = [z3.Real(f"group_{dimension}_{len(axes)}_{i}") for i in range(dimension)]
    solver = z3.Solver()
    supports = [Q(1)] * dimension
    for axis in axes:
        reflection_membership(solver, center, axis, supports)
    return solver.check() == z3.sat


def two_branch_axis_cover(dimension: int) -> dict[str, object]:
    """Exhaust all two-colorings, fixing axis zero in the first branch."""
    feasible_partition = None
    checked = 0
    for mask in range(1 << (dimension - 1)):
        first = frozenset(
            {0}
            | {
                index + 1
                for index in range(dimension - 1)
                if (mask >> index) & 1
            }
        )
        second = frozenset(set(range(dimension)) - set(first))
        checked += 1
        if group_center_sat(dimension, first) and group_center_sat(dimension, second):
            feasible_partition = [sorted(first), sorted(second)]
            break
    return {
        "result": "sat" if feasible_partition is not None else "unsat",
        "colorings_checked_until_decision": checked,
        "witness_partition": feasible_partition,
    }


def canonical_sha256(value: object) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    z3.set_param(proof=True)
    dimensions = tuple(range(2, 11))
    for dimension in dimensions:
        type_cone_equivalence(dimension)
    ray_controls = {
        str(dimension): ray_vertex_control(dimension)
        for dimension in range(2, 8)
    }
    three_axis = {}
    proof_hash = None
    for dimension in range(3, 8):
        result, candidate_hash = parametric_three_axis_query(
            dimension, proof=dimension == 7
        )
        assert result == "unsat"
        three_axis[str(dimension)] = result
        if candidate_hash is not None:
            proof_hash = candidate_hash

    two_branch = {
        str(dimension): two_branch_axis_cover(dimension)
        for dimension in range(4, 8)
    }
    assert two_branch["4"]["result"] == "sat"
    assert all(two_branch[str(dimension)]["result"] == "unsat" for dimension in (5, 6, 7))

    report = {
        "schema": "g0067-pair-subdivision-type-cone-nogo-v1",
        "arithmetic": "fractions.Fraction plus exact Z3 QF_LRA",
        "result": "PASS",
        "type_cone_equivalence_dimensions": list(dimensions),
        "type_cone_compressed_inequalities": "(d+1)c_i >= sum_j c_j",
        "ray_vertex_controls": ray_controls,
        "parametric_one_branch_three_axis_queries": three_axis,
        "d7_unsat_proof_sha256": proof_hash,
        "target_two_branch_axis_cover": two_branch,
        "sharp_obstruction_boundary": {"d4": "SAT", "d5": "UNSAT"},
        "scope": "D_d is not in P2 for d>=5; unrestricted MAX11 remains open",
        "source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "z3_version": z3.get_version_string(),
    }
    report["scientific_payload_sha256"] = canonical_sha256(report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
