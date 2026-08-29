#!/usr/bin/env python3
"""Exact controls for single-zonotope MAX stabilizer face bounds.

Scope: identities Delta_{N-1} + Z = B with Z a zonotope and B in P^2.
This is deliberately narrower than a general virtual identity Delta+A=B.
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
SCHEMA = "maxrelu-g0065-single-zonotope-face-bounds-v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0063_REPORT = ROOT / "artifacts/math/G-0063/simplex_asymmetry_certificate_controls_v1.json"
G0063_REPORT_SHA256 = "c0309de77923802be53b40799679bc31e6125e8e8a832fdb047b2c111f2abb91"
G0063_README = ROOT / "artifacts/math/G-0063/README.md"
G0063_README_SHA256 = "6b0541b537956e2d720111911f04ad8787a7129570886d96371de282b2523dc1"
G0064_README = ROOT / "artifacts/math/G-0064/README.md"
G0064_README_SHA256 = "cd3ffe8a51e4722b92b82a7fc1a4a34072a315d0152edc3f45cf42957b0914e8"
DEFAULT_OUTPUT = HERE / "single_zonotope_face_bounds_v1.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def q(value: int | Q) -> str:
    return str(value)


def dot(left: tuple[Q, ...], right: tuple[Q, ...]) -> Q:
    return sum((a * b for a, b in zip(left, right, strict=True)), Q(0))


def root_segment_lambda(simplex_vertex_count: int, a: int, b: int) -> Q:
    """Compute lambda_Delta([e_a,e_b]) from all simplex facet normals."""

    if not (0 <= a < b < simplex_vertex_count):
        raise ValueError("distinct in-range endpoints required")
    support_sum = Q(0)
    for special in range(simplex_vertex_count):
        normal = [Q(1)] * simplex_vertex_count
        normal[special] = Q(-(simplex_vertex_count - 1))
        support_sum += max(normal[a], normal[b])
    return support_sum / simplex_vertex_count


def centered_segment_lambda(generator: tuple[Q, ...]) -> Q:
    """Compute lambda_Delta([0,g]) directly at all simplex facet normals."""

    size = len(generator)
    if sum(generator, Q(0)) != 0:
        raise ValueError("generator must lie in the centered hyperplane")
    support_sum = Q(0)
    for special in range(size):
        normal = tuple(Q(1 if i != special else -(size - 1)) for i in range(size))
        support_sum += max(Q(0), dot(generator, normal))
    return support_sum / size


def local_bound(tie_size: int) -> Q:
    if tie_size < 5:
        return Q(0)
    # The localized simplex has dimension tie_size-1.  G-0063 with p=3 and
    # rho(Z)=1 gives (dimension-3)/(3-1).
    return Q(tie_size - 4, 2)


def exact_double_count(N: int, tie_size: int) -> dict[str, Any]:
    vertices = range(N)
    edges = tuple(combinations(vertices, 2))
    subsets = tuple(combinations(vertices, tie_size))
    multiplicities = {edge: 0 for edge in edges}
    incidence_total = 0
    for subset_tuple in subsets:
        subset = set(subset_tuple)
        for edge in edges:
            if edge[0] in subset and edge[1] in subset:
                multiplicities[edge] += 1
                incidence_total += 1
    expected_multiplicity = comb(N - 2, tie_size - 2)
    if set(multiplicities.values()) != {expected_multiplicity}:
        raise AssertionError("edge/subset incidence is not uniform")
    if incidence_total != comb(N, tie_size) * comb(tie_size, 2):
        raise AssertionError("incidence total mismatch")
    aggregate = Q(comb(N, tie_size), expected_multiplicity) * local_bound(tie_size)
    closed_form = Q(N * (N - 1) * (tie_size - 4), 2 * tie_size * (tie_size - 1))
    if aggregate != closed_form:
        raise AssertionError("double-counted bound differs from closed form")
    return {
        "tie_set_size": tie_size,
        "simplex_face_dimension": tie_size - 1,
        "per_subset_induced_edge_weight_lower_bound": q(local_bound(tie_size)),
        "subset_count": len(subsets),
        "each_edge_subset_multiplicity": expected_multiplicity,
        "enumerated_edge_subset_incidences": incidence_total,
        "total_edge_weight_lower_bound": q(aggregate),
    }


def graphical_constraints(N: int) -> dict[str, Any]:
    rows = [exact_double_count(N, size) for size in range(5, N + 1)]
    if not rows:
        return {
            "N_coordinates": N,
            "constraints": [],
            "strongest_total_edge_weight_lower_bound": "0",
            "strongest_tie_set_sizes": [],
            "uniform_edge_weight": "0",
            "uniform_checks": [],
        }
    strongest = max(Q(row["total_edge_weight_lower_bound"]) for row in rows)
    strongest_sizes = [
        row["tie_set_size"]
        for row in rows
        if Q(row["total_edge_weight_lower_bound"]) == strongest
    ]
    uniform_weight = strongest / comb(N, 2)
    uniform_checks = []
    for size in range(5, N + 1):
        induced = comb(size, 2) * uniform_weight
        required = local_bound(size)
        if induced < required:
            raise AssertionError("uniform weight failed a local subset constraint")
        uniform_checks.append(
            {
                "tie_set_size": size,
                "induced_edge_weight": q(induced),
                "required": q(required),
                "slack": q(induced - required),
            }
        )
    return {
        "N_coordinates": N,
        "constraints": rows,
        "strongest_total_edge_weight_lower_bound": q(strongest),
        "strongest_tie_set_sizes": strongest_sizes,
        "uniform_edge_weight": q(uniform_weight),
        "uniform_checks": uniform_checks,
    }


def support_multiplicity(N: int, tie_size: int, generator_support_size: int) -> int:
    if generator_support_size > tie_size:
        return 0
    return comb(N - generator_support_size, tie_size - generator_support_size)


def modular_rank(matrix: list[list[int]], prime: int = 1_000_003) -> int:
    """Rank over F_p; full column rank also certifies full rank over Q."""

    if not matrix:
        return 0
    work = [[value % prime for value in row] for row in matrix]
    rows = len(work)
    columns = len(work[0])
    rank = 0
    for column in range(columns):
        pivot = next((r for r in range(rank, rows) if work[r][column]), None)
        if pivot is None:
            continue
        work[rank], work[pivot] = work[pivot], work[rank]
        inverse = pow(work[rank][column], prime - 2, prime)
        work[rank] = [(value * inverse) % prime for value in work[rank]]
        for r in range(rows):
            if r == rank or work[r][column] == 0:
                continue
            factor = work[r][column]
            work[r] = [
                (left - factor * right) % prime
                for left, right in zip(work[r], work[rank], strict=True)
            ]
        rank += 1
        if rank == columns:
            break
    return rank


def general_zonotope_double_count(N: int = 11) -> dict[str, Any]:
    """Double-count generic tie-face retention for arbitrary generators."""

    rows = []
    strongest = Q(0)
    strongest_sizes: list[int] = []
    for size in range(5, N + 1):
        pair_multiplicity = support_multiplicity(N, size, 2)
        multiplicities = []
        previous = None
        for support_size in range(2, N + 1):
            multiplicity = support_multiplicity(N, size, support_size)
            if previous is not None and multiplicity > previous:
                raise AssertionError("support multiplicity should be nonincreasing")
            previous = multiplicity
            multiplicities.append(
                {
                    "generator_support_size": support_size,
                    "number_of_tie_sets_retaining_generator": multiplicity,
                }
            )
        aggregate = Q(comb(N, size), pair_multiplicity) * local_bound(size)
        if aggregate > strongest:
            strongest = aggregate
            strongest_sizes = [size]
        elif aggregate == strongest:
            strongest_sizes.append(size)
        rows.append(
            {
                "tie_set_size": size,
                "per_tie_set_lambda_lower_bound": q(local_bound(size)),
                "pair_support_multiplicity": pair_multiplicity,
                "support_multiplicities": multiplicities,
                "global_lambda_Delta_Z_lower_bound": q(aggregate),
            }
        )

    edges = tuple(combinations(range(N), 2))
    seven_sets = tuple(combinations(range(N), 7))
    incidence = [
        [int(edge[0] in subset and edge[1] in subset) for edge in edges]
        for subset in map(set, seven_sets)
    ]
    incidence_rank = modular_rank(incidence)
    if incidence_rank != len(edges):
        raise AssertionError("seven-set/edge incidence lacks full column rank")
    uniform = Q(1, 14)
    if comb(7, 2) * uniform != local_bound(7):
        raise AssertionError("uniform seven-set equality control failed")
    if comb(N, 2) * uniform != strongest:
        raise AssertionError("uniform total does not attain the general bound")

    return {
        "scope": "all_finite_zonotopes_in_the_centered_MAX11_space",
        "per_tie_size_double_counts": rows,
        "strongest_tie_set_sizes": strongest_sizes,
        "global_lambda_Delta_Z_lower_bound": q(strongest),
        "equality_rigidity": {
            "support_size_two_forced": True,
            "reason": "at_size_7_every_support_size_greater_than_2_has_strictly_smaller_retention_multiplicity",
            "seven_set_edge_incidence_shape": [len(seven_sets), len(edges)],
            "seven_set_edge_incidence_rank_mod_1000003": incidence_rank,
            "full_Q_column_rank_certified": incidence_rank == len(edges),
            "unique_merged_edge_weight": q(uniform),
            "equality_zonotope_up_to_translation": "(1/14) * graphical_zonotope(K_11)",
        },
    }


def generic_tie_retention_control(N: int, tie_size: int) -> dict[str, Any]:
    """Check <e_a-e_b,x>=0 iff a,b lie in the generic top-tie set."""

    S = set(range(tie_size))
    # Equal top coordinates, pairwise-distinct lower coordinates.  Centering
    # x is unnecessary because every root direction annihilates constants.
    x = tuple(Q(0) if i in S else Q(-(i + 1)) for i in range(N))
    retained = []
    for a, b in combinations(range(N), 2):
        generator = tuple(Q(1 if i == a else -1 if i == b else 0) for i in range(N))
        observed = dot(generator, x) == 0
        expected = a in S and b in S
        if observed != expected:
            raise AssertionError("generic root-generator retention mismatch")
        if observed:
            retained.append([a, b])
    if len(retained) != comb(tie_size, 2):
        raise AssertionError("wrong retained root-edge count")
    return {
        "N_coordinates": N,
        "tie_set_size": tie_size,
        "retained_edge_count": len(retained),
        "expected_induced_edge_count": comb(tie_size, 2),
    }


def delta_zonotope_facet_control(N: int) -> dict[str, Any]:
    """Check that centered simplex-vertex generators survive no facet."""

    mu = tuple(Q(1, N) for _ in range(N))
    generators = []
    for j in range(N):
        generators.append(tuple(Q(1 if i == j else 0) - mu[i] for i in range(N)))
    zero_pair_count = 0
    for i in range(N):
        direction = tuple(mu[k] - Q(1 if k == i else 0) for k in range(N))
        for generator in generators:
            pairing = dot(generator, direction)
            if pairing == 0:
                zero_pair_count += 1
            if pairing != -generator[i]:
                raise AssertionError("facet pairing identity mismatch")
    if zero_pair_count != 0:
        raise AssertionError("a centered simplex generator unexpectedly survived a facet")
    facet_dimension = N - 2
    rejected_by_P2_face_bound = facet_dimension > 3
    return {
        "N_coordinates": N,
        "generator_facet_pairings_checked": N * N,
        "zero_pairings": zero_pair_count,
        "exposed_stabilizer_face": "point",
        "resulting_B_facet": f"translate_of_Delta_{facet_dimension}",
        "facet_simplex_rho": facet_dimension,
        "P2_bound": 3,
        "rejected_by_face_closure": rejected_by_P2_face_bound,
    }


def low_arity_scope_controls(g0063: dict[str, Any]) -> dict[str, Any]:
    # Delta_3 is a single primitive P^2 block: split its four vertices into
    # two segments.  Thus Z=point is a valid small-dimensional control and
    # explains why the inequality begins only with five tied vertices.
    max4 = {
        "target": "MAX4/Delta_3",
        "identity": "Delta_3 + point = conv([e1,e2] union [e3,e4])",
        "two_zonotope_branches": ["segment_[e1,e2]", "segment_[e3,e4]"],
        "constraint_triggered": False,
    }

    public = []
    for control in g0063["public_certificate_controls"]:
        negative = control["sides"]["A_negative"]
        rho = Q(negative["rho_Delta"])
        if rho == 1:
            raise AssertionError("a public negative side unexpectedly passes the zonotope symmetry test")
        public.append(
            {
                "N_coordinates": control["N_coordinates"],
                "negative_side_rho_Delta": q(rho),
                "rho_not_one": True,
                "scope_adjudication": "general_P2_stabilizer_not_a_zonotope;_G0065_does_not_apply",
            }
        )
    return {"MAX4_positive_control": max4, "MAX5_through_MAX10_scope_controls": public}


def converse_hostile_controls(target: dict[str, Any]) -> dict[str, Any]:
    total_bound = Q(target["strongest_total_edge_weight_lower_bound"])
    uniform = Q(target["uniform_edge_weight"])
    # A total-weight bound alone is not sufficient: concentrate all mass on
    # edge {0,1}; a seven-set avoiding that edge has zero induced weight.
    concentrated_subset = tuple(range(2, 9))
    concentrated_induced = Q(0)
    concentrated_required = local_bound(len(concentrated_subset))
    if not (total_bound >= Q(7, 2) and concentrated_induced < concentrated_required):
        raise AssertionError("concentrated-weight hostile control failed")
    # Dropping the uniform value must fail a tight seven-set constraint.
    below = uniform - Q(1, 1000)
    below_induced = comb(7, 2) * below
    if not below_induced < local_bound(7):
        raise AssertionError("below-threshold uniform hostile control was not rejected")
    return {
        "total_weight_bound_is_not_sufficient": {
            "global_total_weight": q(total_bound),
            "all_weight_on_edge": [0, 1],
            "violating_seven_set": list(concentrated_subset),
            "induced_weight": q(concentrated_induced),
            "required": q(concentrated_required),
        },
        "uniform_weight_below_one_fourteenth_is_rejected": {
            "mutant_uniform_weight": q(below),
            "seven_set_induced_weight": q(below_induced),
            "required": q(local_bound(7)),
        },
    }


def build_report() -> dict[str, Any]:
    bindings = {
        str(G0063_REPORT.relative_to(ROOT)): G0063_REPORT_SHA256,
        str(G0063_README.relative_to(ROOT)): G0063_README_SHA256,
        str(G0064_README.relative_to(ROOT)): G0064_README_SHA256,
    }
    for relative, expected in bindings.items():
        if sha256_path(ROOT / relative) != expected:
            raise AssertionError(f"bound input drift: {relative}")
    g0063 = json.loads(G0063_REPORT.read_text())
    if g0063.get("status") != "PASS":
        raise AssertionError("G-0063 prerequisite is not PASS")

    root_lambda_checks = []
    for vertex_count in range(2, 12):
        values = {
            root_segment_lambda(vertex_count, a, b)
            for a, b in combinations(range(vertex_count), 2)
        }
        if values != {Q(1)}:
            raise AssertionError("translated root segment does not have lambda_Delta=1")
        root_lambda_checks.append(
            {
                "simplex_vertex_count": vertex_count,
                "root_segments_checked": comb(vertex_count, 2),
                "lambda_Delta": "1",
            }
        )

    dense_lambda_checks = []
    for size in range(3, 12):
        samples = [
            tuple(Q(1 if i == 0 else -1 if i == 1 else 0) for i in range(size)),
            tuple(Q(1 if i in (0, 1) else -2 if i == 2 else 0) for i in range(size)),
        ]
        if size >= 4:
            samples.append(tuple(Q(value) for value in ([1, 2, 3, -6] + [0] * (size - 4))))
        for generator in samples:
            direct = centered_segment_lambda(generator)
            positive_mass = sum((max(Q(0), value) for value in generator), Q(0))
            l1_half = sum((abs(value) for value in generator), Q(0)) / 2
            if direct != positive_mass or direct != l1_half:
                raise AssertionError("general centered-segment lambda formula failed")
            dense_lambda_checks.append(
                {
                    "ambient_coordinate_count": size,
                    "support_size": sum(value != 0 for value in generator),
                    "lambda_Delta": q(direct),
                    "positive_coordinate_mass": q(positive_mass),
                    "l1_norm_over_two": q(l1_half),
                }
            )

    small_graphical = [graphical_constraints(N) for N in range(4, 11)]
    target = graphical_constraints(11)
    general_target = general_zonotope_double_count(11)
    if target["strongest_total_edge_weight_lower_bound"] != "55/14":
        raise AssertionError("MAX11 graphical bound drift")
    if target["uniform_edge_weight"] != "1/14":
        raise AssertionError("MAX11 uniform sharp control drift")

    return {
        "schema": SCHEMA,
        "status": "PASS",
        "claim": "necessary_conditions_for_single_zonotope_stabilizer_only",
        "input_bindings": bindings,
        "general_MAX11_single_zonotope_facet_condition": {
            "identity_scope": "Delta_10 + Z = B with Z a zonotope and B in P^2",
            "facet_i_retained_generators": "{g : g_i=0} in centered coordinates",
            "required_on_each_of_11_facets": "lambda_Delta9(F_i(Z)) >= 3",
        },
        "MAX11_delta_zonotope_no_go": delta_zonotope_facet_control(11),
        "root_segment_lambda_controls": root_lambda_checks,
        "general_centered_segment_lambda_controls": dense_lambda_checks,
        "generic_tie_retention_controls": [
            generic_tie_retention_control(11, size) for size in range(5, 11)
        ],
        "MAX11_arbitrary_zonotope_double_count": general_target,
        "MAX11_weighted_graphical_constraints": target,
        "MAX4_through_MAX10_hostile_controls": {
            "scope": low_arity_scope_controls(g0063),
            "graphical_constraint_thresholds": small_graphical,
            "delta_zonotope_facet_thresholds": [
                delta_zonotope_facet_control(N) for N in range(4, 11)
            ],
        },
        "converse_hostile_controls": converse_hostile_controls(target),
        "boundaries": [
            "No condition here is sufficient for Delta_10+Z to lie in P^2.",
            "The result does not apply when the negative stabilizer A is a non-zonotopal P^2 polytope.",
            "The 55/14 bound applies to every finite zonotope, but still only in the single-zonotope-stabilizer scope.",
            "No unrestricted MAX11 representation or impossibility theorem is proved.",
        ],
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, indent=2, sort_keys=True) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-frozen", action="store_true")
    args = parser.parse_args(argv)
    payload = canonical_json(build_report())
    if args.check_frozen:
        if not args.output.is_file() or args.output.read_text() != payload:
            raise SystemExit("frozen report differs from exact recomputation")
        print("PASS: frozen report matches exact recomputation")
        return 0
    args.output.write_text(payload)
    print(f"PASS: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
