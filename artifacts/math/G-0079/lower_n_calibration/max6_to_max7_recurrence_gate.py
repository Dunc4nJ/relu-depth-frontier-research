#!/usr/bin/env python3
"""Exact lower-n falsifier for a grouped Y-spoke coefficient recurrence.

This producer never reads G-0078/G-0079 price artifacts or the registered
G-0079 runner.  It tests one bounded coefficient class on the pinned MAX6
certificate: every eligible two-component base coefficient is inherited,
with one free multiplier for each

    relation (cross/same) x topology (2+4/3+3) x orientation (0/1),

plus the three symmetric carriers C_L, C_E, and C_Y.  Seven Boolean Hamming
profiles and three deterministic off-Boolean profiles give a 10 x 11 exact
rational system.  A primitive integer row dual proves finite-row
nonmembership for this coefficient class.

The result is minimal only along the declared profile sequence.  It is not a
global minimality claim and says nothing about arbitrary per-orbit Y-spoke
coefficients, extra carriers, or lifts of ineligible/degenerate source terms.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
import hashlib
from itertools import permutations
import json
from math import gcd, lcm
from pathlib import Path
import platform
import sys
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPT = Path(__file__).resolve()
MODEL_PATH = ROOT / "cleanroom/maxrelu/model.py"
SOURCE_PATH = ROOT / "subjects/max-relu-known/certificates/certificate_6_2.json"
TARGET_PATH = ROOT / "subjects/max-relu-known/certificates/certificate_7_3.json"

EXPECTED_MODEL_SHA256 = (
    "320c3e99d45f881472a19bfa3d406b9b6a3ff6ebc6a1de211d0062a7299a325a"
)
EXPECTED_SOURCE_RAW_SHA256 = (
    "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83"
)
EXPECTED_SOURCE_NORMALIZED_SHA256 = (
    "b5e5ca7eb0e69a88d988285e847da6816b7eda07aff5664fef2b3b527e14daaa"
)
EXPECTED_TARGET_RAW_SHA256 = (
    "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be"
)
EXPECTED_TARGET_NORMALIZED_SHA256 = (
    "bc2ec7ed82d98f24d1480a72d0899e2c8d4c7075fb3a167616c860d815931448"
)

SCHEMA = "max7-y-spoke-lower-n-recurrence-gate-v1"
OLD_N = 6
N = 7
SOURCE_K = 2
EXPECTED_ELIGIBLE_BASES = 3
EXPECTED_TOPOLOGY = {(2, 4): 2, (3, 3): 1}
EXPECTED_CROSS_SEEDS = 100
EXPECTED_SAME_SEEDS = 80
EXPECTED_ALL_SEEDS = 180
EXPECTED_COLUMN_ORDER = (
    "cross_2+4_o0",
    "cross_2+4_o1",
    "cross_3+3_o0",
    "cross_3+3_o1",
    "same_2+4_o0",
    "same_2+4_o1",
    "same_3+3_o0",
    "same_3+3_o1",
    "C_L",
    "C_E",
    "C_Y",
)
EXPECTED_PREFIX_RANKS = ((7, 7), (8, 8), (9, 9), (9, 10))
EXPECTED_DUAL = (
    2016,
    50400,
    -1240,
    -3020,
    -423,
    6129,
    -3229,
    50616,
    -2160,
    -48456,
)
EXPECTED_DUAL_TARGET_PAIRING = 17

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Profile = tuple[int, ...]


class GateError(RuntimeError):
    """A pinned input, census, exact calculation, or control drifted."""


@dataclass(frozen=True)
class Base:
    position: int
    term_index: int
    coefficient: Fraction
    left: Side
    right: Side
    components: tuple[tuple[int, ...], tuple[int, ...]]

    @property
    def topology(self) -> tuple[int, int]:
        first, second = sorted(map(len, self.components))
        return first, second


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else str(value)


def canonical_side(side: Iterable[Edge]) -> Side:
    return tuple(sorted(tuple(sorted(edge)) for edge in side))  # type: ignore[return-value]


def load_certificates():
    if sha256_path(MODEL_PATH) != EXPECTED_MODEL_SHA256:
        raise GateError("clean-room certificate parser source hash drift")
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from cleanroom.maxrelu.model import parse_registered_certificate_bytes

    source = parse_registered_certificate_bytes(
        SOURCE_PATH.read_bytes(), SOURCE_PATH.name
    )
    target = parse_registered_certificate_bytes(
        TARGET_PATH.read_bytes(), TARGET_PATH.name
    )
    observed = (
        source.raw_sha256,
        source.normalized_sha256,
        target.raw_sha256,
        target.normalized_sha256,
    )
    expected = (
        EXPECTED_SOURCE_RAW_SHA256,
        EXPECTED_SOURCE_NORMALIZED_SHA256,
        EXPECTED_TARGET_RAW_SHA256,
        EXPECTED_TARGET_NORMALIZED_SHA256,
    )
    if observed != expected:
        raise GateError("registered certificate identity drift")
    if (source.n, source.k, source.term_count) != (6, 2, 4):
        raise GateError("MAX6 source shape drift")
    if (target.n, target.k, target.term_count) != (7, 3, 57):
        raise GateError("MAX7 target shape drift")
    return source, target


def forest_components(left: Side, right: Side) -> tuple[tuple[int, ...], ...] | None:
    edges = left + right
    if any(first == second for first, second in edges):
        return None
    if len(set(edges)) != OLD_N - 2:
        return None
    if {vertex for edge in edges for vertex in edge} != set(range(1, OLD_N + 1)):
        return None

    parent = list(range(OLD_N + 1))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for first, second in edges:
        first_root, second_root = find(first), find(second)
        if first_root == second_root:
            return None
        parent[second_root] = first_root
    groups: dict[int, list[int]] = {}
    for vertex in range(1, OLD_N + 1):
        groups.setdefault(find(vertex), []).append(vertex)
    components = tuple(sorted(tuple(group) for group in groups.values()))
    return components if len(components) == 2 else None


def ineligibility_reason(left: Side, right: Side) -> str:
    edges = left + right
    if any(first == second for first, second in edges):
        return "loop"
    if len(set(edges)) != OLD_N - 2:
        return "duplicate_edge"
    if {vertex for edge in edges for vertex in edge} != set(range(1, OLD_N + 1)):
        return "not_full_support"
    return "cycle_or_component_count"


def load_bases(source) -> tuple[list[Base], list[dict[str, object]], Counter[str]]:
    bases: list[Base] = []
    manifest: list[dict[str, object]] = []
    rejected: Counter[str] = Counter()
    for term_index, term in enumerate(source.terms):
        left = canonical_side(term.left)
        right = canonical_side(term.right)
        if len(left) != SOURCE_K or len(right) != SOURCE_K:
            raise GateError("registered source side-length drift")
        components = forest_components(left, right)
        if components is None:
            rejected[ineligibility_reason(left, right)] += 1
            continue
        base = Base(
            position=len(bases),
            term_index=term_index,
            coefficient=term.coefficient,
            left=left,
            right=right,
            components=components,  # type: ignore[arg-type]
        )
        bases.append(base)
        manifest.append(
            {
                "position": base.position,
                "term_index": base.term_index,
                "coefficient": fraction_text(base.coefficient),
                "left": [list(edge) for edge in base.left],
                "right": [list(edge) for edge in base.right],
                "components": [list(component) for component in base.components],
                "topology": list(base.topology),
            }
        )
    topology = Counter(base.topology for base in bases)
    if len(bases) != EXPECTED_ELIGIBLE_BASES or dict(topology) != EXPECTED_TOPOLOGY:
        raise GateError(f"eligible base census drift: {len(bases)}, {topology}")
    if [base.term_index for base in bases] != [1, 2, 3]:
        raise GateError("eligible source term indices drift")
    if rejected != Counter({"duplicate_edge": 1}):
        raise GateError(f"ineligible source census drift: {rejected}")
    return bases, manifest, rejected


def seed_manifest(bases: Sequence[Base]) -> tuple[list[dict[str, object]], Counter]:
    manifest: list[dict[str, object]] = []
    census: Counter = Counter()
    for base in bases:
        component_of = {
            vertex: component_index
            for component_index, component in enumerate(base.components)
            for vertex in component
        }
        topology = f"{base.topology[0]}+{base.topology[1]}"
        for anchor in range(1, OLD_N + 1):
            for auxiliary in range(1, OLD_N + 1):
                if anchor == auxiliary:
                    continue
                relation = (
                    "same"
                    if component_of[anchor] == component_of[auxiliary]
                    else "cross"
                )
                for orientation in (0, 1):
                    manifest.append(
                        {
                            "base_position": base.position,
                            "base_term_index": base.term_index,
                            "anchor": anchor,
                            "auxiliary": auxiliary,
                            "orientation": orientation,
                            "relation": relation,
                            "topology": topology,
                        }
                    )
                    census[(relation, topology, orientation)] += 1
    if len(manifest) != EXPECTED_ALL_SEEDS:
        raise GateError("full raw seed census drift")
    keys = {
        (
            item["base_position"],
            item["anchor"],
            item["auxiliary"],
            item["orientation"],
        )
        for item in manifest
    }
    if len(keys) != len(manifest):
        raise GateError("raw seed manifest contains duplicates")
    cross = sum(value for key, value in census.items() if key[0] == "cross")
    same = sum(value for key, value in census.items() if key[0] == "same")
    if (cross, same) != (EXPECTED_CROSS_SEEDS, EXPECTED_SAME_SEEDS):
        raise GateError(f"relation census drift: cross={cross}, same={same}")
    return manifest, census


def distinct_assignments(profile: Profile) -> tuple[Profile, ...]:
    if len(profile) != N:
        raise GateError("profile length drift")
    return tuple(sorted(set(permutations(profile))))


def expression_value(
    base: Base,
    anchor: int,
    auxiliary: int,
    orientation: int,
    point: Profile,
    *,
    doubled_anchor_coefficient: int,
) -> int:
    left = sum(max(point[first - 1], point[second - 1]) for first, second in base.left)
    right = sum(
        max(point[first - 1], point[second - 1]) for first, second in base.right
    )
    simple = doubled_anchor_coefficient * point[anchor - 1]
    leaf = point[auxiliary - 1] + point[N - 1]
    if orientation == 0:
        return max(left + simple, right + max(simple, leaf))
    if orientation == 1:
        return max(left + max(simple, leaf), right + simple)
    raise GateError("orientation outside {0,1}")


def evaluate_profile(
    bases: Sequence[Base],
    manifest: Sequence[dict[str, object]],
    profile: Profile,
    *,
    doubled_anchor_coefficient: int = 2,
) -> tuple[list[Fraction], Fraction, int]:
    assignments = distinct_assignments(profile)
    denominator = len(assignments)
    by_position = {base.position: base for base in bases}
    grouped = {name: Fraction(0) for name in EXPECTED_COLUMN_ORDER[:-3]}
    for seed in manifest:
        base = by_position[int(seed["base_position"])]
        column = (
            f"{seed['relation']}_{seed['topology']}_o{seed['orientation']}"
        )
        subtotal = sum(
            expression_value(
                base,
                int(seed["anchor"]),
                int(seed["auxiliary"]),
                int(seed["orientation"]),
                point,
                doubled_anchor_coefficient=doubled_anchor_coefficient,
            )
            for point in assignments
        )
        grouped[column] += base.coefficient * Fraction(subtotal, denominator)

    carrier_l = Fraction(sum(point[0] for point in assignments), denominator)
    carrier_e = Fraction(
        sum(max(point[0], point[1]) for point in assignments), denominator
    )
    carrier_y = Fraction(
        sum(max(2 * point[0], point[1] + point[2]) for point in assignments),
        denominator,
    )
    row = [grouped[name] for name in EXPECTED_COLUMN_ORDER[:-3]]
    row.extend((carrier_l, carrier_e, carrier_y))
    return row, Fraction(max(profile)), denominator


def row_subject() -> tuple[list[str], list[Profile]]:
    labels = [f"B{weight}" for weight in range(1, N + 1)]
    profiles = [
        tuple([0] * (N - weight) + [1] * weight)
        for weight in range(1, N + 1)
    ]
    labels.extend(("P012", "P013", "P023"))
    profiles.extend(
        (
            (0, 0, 0, 0, 0, 1, 2),
            (0, 0, 0, 0, 0, 1, 3),
            (0, 0, 0, 0, 0, 2, 3),
        )
    )
    return labels, profiles


def build_matrix(
    bases: Sequence[Base],
    manifest: Sequence[dict[str, object]],
    *,
    doubled_anchor_coefficient: int = 2,
) -> tuple[list[list[Fraction]], list[Fraction], list[int]]:
    _labels, profiles = row_subject()
    matrix: list[list[Fraction]] = []
    target: list[Fraction] = []
    assignment_counts: list[int] = []
    for profile in profiles:
        row, value, count = evaluate_profile(
            bases,
            manifest,
            profile,
            doubled_anchor_coefficient=doubled_anchor_coefficient,
        )
        matrix.append(row)
        target.append(value)
        assignment_counts.append(count)
    return matrix, target, assignment_counts


def rref(matrix: Sequence[Sequence[Fraction]]) -> tuple[list[list[Fraction]], list[int]]:
    rows = [list(map(Fraction, row)) for row in matrix]
    if not rows:
        return rows, []
    columns = len(rows[0])
    if any(len(row) != columns for row in rows):
        raise GateError("ragged exact matrix")
    pivots: list[int] = []
    pivot_row = 0
    for column in range(columns):
        selected = next(
            (row for row in range(pivot_row, len(rows)) if rows[row][column]), None
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [value / scale for value in rows[pivot_row]]
        for row in range(len(rows)):
            if row == pivot_row or not rows[row][column]:
                continue
            coefficient = rows[row][column]
            rows[row] = [
                value - coefficient * pivot
                for value, pivot in zip(rows[row], rows[pivot_row], strict=True)
            ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return rows, pivots


def exact_rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    return len(rref(matrix)[1])


def primitive_integer_vector(values: Sequence[Fraction]) -> list[int]:
    denominator = reduce(lcm, (value.denominator for value in values), 1)
    integers = [
        value.numerator * (denominator // value.denominator) for value in values
    ]
    common = reduce(gcd, (abs(value) for value in integers), 0) or 1
    integers = [value // common for value in integers]
    first = next((value for value in integers if value), 1)
    return [-value for value in integers] if first < 0 else integers


def exact_target_dual(
    matrix: Sequence[Sequence[Fraction]], target: Sequence[Fraction]
) -> list[int]:
    row_count = len(matrix)
    column_count = len(matrix[0])
    transpose = [
        [matrix[row][column] for row in range(row_count)]
        for column in range(column_count)
    ]
    reduced, pivots = rref(transpose)
    pivot_set = set(pivots)
    for free_column in range(row_count):
        if free_column in pivot_set:
            continue
        candidate = [Fraction(0) for _ in range(row_count)]
        candidate[free_column] = 1
        for row, pivot in enumerate(pivots):
            candidate[pivot] = -reduced[row][free_column]
        if sum(
            value * rhs for value, rhs in zip(candidate, target, strict=True)
        ):
            return primitive_integer_vector(candidate)
    raise GateError("exact rank gap yielded no target-bearing row dual")


def matrix_text(matrix: Sequence[Sequence[Fraction]]) -> list[list[str]]:
    return [[fraction_text(value) for value in row] for row in matrix]


def vector_text(vector: Sequence[Fraction]) -> list[str]:
    return [fraction_text(value) for value in vector]


def verify_dual(
    matrix: Sequence[Sequence[Fraction]],
    target: Sequence[Fraction],
    dual: Sequence[int],
) -> tuple[list[Fraction], Fraction]:
    annihilation = [
        sum(
            Fraction(dual[row]) * matrix[row][column]
            for row in range(len(matrix))
        )
        for column in range(len(matrix[0]))
    ]
    pairing = sum(
        Fraction(weight) * value for weight, value in zip(dual, target, strict=True)
    )
    return annihilation, pairing


def strict_json_load(path: Path) -> object:
    def object_without_duplicates(pairs: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in pairs:
            if key in result:
                raise GateError(f"duplicate JSON key in frozen artifact: {key}")
            result[key] = value
        return result

    try:
        return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=object_without_duplicates)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise GateError(f"cannot read frozen artifact: {exc}") from exc


def build_report() -> dict[str, object]:
    source, target_certificate = load_certificates()
    bases, base_manifest, rejected = load_bases(source)
    manifest, census = seed_manifest(bases)
    matrix, target, assignment_counts = build_matrix(bases, manifest)
    labels, profiles = row_subject()

    prefix_ranks = []
    for row_count in range(7, 11):
        rank = exact_rank(matrix[:row_count])
        augmented_rank = exact_rank(
            [
                row + [target[index]]
                for index, row in enumerate(matrix[:row_count])
            ]
        )
        prefix_ranks.append((rank, augmented_rank))
    if tuple(prefix_ranks) != EXPECTED_PREFIX_RANKS:
        raise GateError(f"profile-sequence rank progression drift: {prefix_ranks}")

    dual = exact_target_dual(matrix, target)
    if tuple(dual) != EXPECTED_DUAL:
        raise GateError(f"primitive exact dual drift: {dual}")
    annihilation, pairing = verify_dual(matrix, target, dual)
    if any(annihilation) or pairing != EXPECTED_DUAL_TARGET_PAIRING:
        raise GateError("exact dual replay failed")

    mutant_matrix, mutant_target, mutant_assignments = build_matrix(
        bases, manifest, doubled_anchor_coefficient=1
    )
    if mutant_target != target or mutant_assignments != assignment_counts:
        raise GateError("hostile semantic mutation changed the row subject")
    changed_entries = [
        [row, column]
        for row in range(len(matrix))
        for column in range(len(matrix[0]))
        if matrix[row][column] != mutant_matrix[row][column]
    ]
    mutant_annihilation, _mutant_pairing = verify_dual(
        mutant_matrix, mutant_target, dual
    )
    if not changed_entries or not any(mutant_annihilation):
        raise GateError("hostile doubled-anchor mutation escaped the frozen dual")

    relation_counts = Counter()
    grouped_counts = []
    for (relation, topology, orientation), count in sorted(census.items()):
        relation_counts[relation] += count
        grouped_counts.append(
            {
                "relation": relation,
                "topology": topology,
                "orientation": orientation,
                "count": count,
            }
        )
    matrix_serialized = matrix_text(matrix)
    target_serialized = vector_text(target)
    mutant_serialized = matrix_text(mutant_matrix)
    science: dict[str, object] = {
        "schema": SCHEMA,
        "claim": (
            "MAX7 is not in the rational column span of the displayed eleven-column "
            "source-coefficient recurrence on the ten frozen symmetric profiles."
        ),
        "input": {
            "parser": {
                "path": str(MODEL_PATH.relative_to(ROOT)),
                "sha256": EXPECTED_MODEL_SHA256,
            },
            "source_certificate": {
                "path": str(SOURCE_PATH.relative_to(ROOT)),
                "subject_id": source.subject_id,
                "n": source.n,
                "k": source.k,
                "terms": source.term_count,
                "raw_sha256": source.raw_sha256,
                "normalized_sha256": source.normalized_sha256,
            },
            "target_certificate": {
                "path": str(TARGET_PATH.relative_to(ROOT)),
                "subject_id": target_certificate.subject_id,
                "n": target_certificate.n,
                "k": target_certificate.k,
                "terms": target_certificate.term_count,
                "raw_sha256": target_certificate.raw_sha256,
                "normalized_sha256": target_certificate.normalized_sha256,
                "role": (
                    "pinned context for the already-certified MAX7 target; the gate target "
                    "values are evaluated directly from max(x_1,...,x_7)"
                ),
            },
        },
        "family": {
            "eligible_base_definition": (
                "two sides of two edges whose four-edge union has no loop or duplicate, "
                "uses every label 1..6, and is a two-component forest"
            ),
            "eligible_bases": len(bases),
            "eligible_term_indices": [base.term_index for base in bases],
            "ineligible_source_terms_by_reason": dict(sorted(rejected.items())),
            "topology_census": {
                f"{first}+{second}": count
                for (first, second), count in sorted(EXPECTED_TOPOLOGY.items())
            },
            "base_manifest": base_manifest,
            "base_manifest_sha256": canonical_sha256(base_manifest),
            "raw_seed_definition": (
                "for each eligible base, every ordered distinct anchor/auxiliary pair in "
                "1..6 and both outer orientations"
            ),
            "cross_raw_seeds": relation_counts["cross"],
            "same_raw_seeds": relation_counts["same"],
            "all_raw_seeds": len(manifest),
            "grouped_raw_seed_census": grouped_counts,
            "raw_seed_manifest": manifest,
            "raw_seed_manifest_sha256": canonical_sha256(manifest),
            "coefficient_class": (
                "each raw seed inherits its eligible source certificate coefficient, then "
                "one rational multiplier is free per relation x unordered component "
                "topology x outer orientation; C_L/C_E/C_Y have independent multipliers"
            ),
            "column_order": list(EXPECTED_COLUMN_ORDER),
        },
        "row_subject": {
            "normalization": (
                "each labelled seed is averaged over every distinct assignment of the "
                "profile multiset, exactly equal to its full S_7 average"
            ),
            "row_order": labels,
            "profiles": [list(profile) for profile in profiles],
            "distinct_assignment_counts": assignment_counts,
            "total_distinct_assignments": sum(assignment_counts),
            "conceptual_seed_point_evaluations": len(manifest)
            * sum(assignment_counts),
            "minimality_boundary": (
                "P012 and P013 each raise both ranks; P023 is the first row in this "
                "declared sequence that raises only augmented rank. No global search for "
                "a smaller separating profile set was performed."
            ),
        },
        "exact_gate": {
            "coefficient_field": "Q",
            "matrix_shape": [len(matrix), len(matrix[0])],
            "matrix": matrix_serialized,
            "matrix_sha256": canonical_sha256(matrix_serialized),
            "target": target_serialized,
            "target_sha256": canonical_sha256(target_serialized),
            "prefix_rank_progression": [
                {
                    "through_row": labels[row_count - 1],
                    "rows": row_count,
                    "rank": rank,
                    "augmented_rank": augmented_rank,
                    "target_in_span": rank == augmented_rank,
                }
                for row_count, (rank, augmented_rank) in zip(
                    range(7, 11), prefix_ranks, strict=True
                )
            ],
            "rank": prefix_ranks[-1][0],
            "augmented_rank": prefix_ranks[-1][1],
            "target_in_span": False,
            "primitive_integer_row_dual": dual,
            "dual_row_order": labels,
            "dual_annihilation": vector_text(annihilation),
            "dual_target_pairing": fraction_text(pairing),
        },
        "hostile_mutation": {
            "name": "replace doubled-anchor coefficient 2 by 1 in both Y arms",
            "mutant_matrix_sha256": canonical_sha256(mutant_serialized),
            "changed_matrix_entries": len(changed_entries),
            "changed_entry_coordinates": changed_entries,
            "frozen_dual_pairings_with_mutant_columns": vector_text(
                mutant_annihilation
            ),
            "detected": True,
            "interpretation": (
                "the row subject is unchanged, but the frozen dual ceases to annihilate "
                "the mutated semantics"
            ),
        },
        "decision": (
            "The displayed grouped source-coefficient recurrence is rejected already by "
            "this ten-profile exact gate; Boolean membership was interpolation."
        ),
        "claim_boundary": (
            "This is finite-row nonmembership for one inherited coefficient class. It is "
            "not a statement about arbitrary per-orbit cross+same Y-spoke coefficients, "
            "base-specific rules, additional carriers, lifts of ineligible source terms, "
            "the registered G-0079 experiment, or unrestricted two-hidden-layer networks."
        ),
        "price_custody": (
            "This producer imports no G-0078/G-0079 price artifact and does not evaluate "
            "any G-0079 new-family price."
        ),
    }
    return {
        **science,
        "scientific_payload_sha256": canonical_sha256(science),
        "producer_sha256": sha256_path(SCRIPT),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }


def self_test() -> dict[str, object]:
    member = [[Fraction(1)], [Fraction(2)]]
    member_target = [Fraction(3), Fraction(6)]
    nonmember = [[Fraction(1)], [Fraction(0)]]
    nonmember_target = [Fraction(0), Fraction(1)]
    if exact_rank(member) != exact_rank(
        [row + [rhs] for row, rhs in zip(member, member_target, strict=True)]
    ):
        raise GateError("exact member fixture failed")
    if exact_rank(nonmember) + 1 != exact_rank(
        [row + [rhs] for row, rhs in zip(nonmember, nonmember_target, strict=True)]
    ):
        raise GateError("exact nonmember fixture failed")
    report = build_report()
    return {
        "schema": f"{SCHEMA}-self-test",
        "exact_member_and_nonmember_fixtures": True,
        "full_subject_and_hostile_mutation_replayed": True,
        "scientific_payload_sha256": report["scientific_payload_sha256"],
        "result": "PASS",
    }


def contained_output(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as exc:
        raise GateError("output/check path must remain inside the campaign workspace") from exc
    return resolved


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.self_test:
        if arguments.output is not None:
            raise GateError("--self-test does not accept --output")
        print(json.dumps(self_test(), sort_keys=True))
        return 0

    report = build_report()
    if arguments.check is not None:
        if arguments.output is not None:
            raise GateError("--check does not accept --output")
        path = contained_output(arguments.check)
        frozen = strict_json_load(path)
        if frozen != report:
            raise GateError("frozen artifact differs from exact replay")
        print(
            json.dumps(
                {
                    "artifact_sha256": sha256_path(path),
                    "scientific_payload_sha256": report[
                        "scientific_payload_sha256"
                    ],
                    "result": "PASS",
                },
                sort_keys=True,
            )
        )
        return 0

    if not arguments.run or arguments.output is None:
        raise GateError("--run requires --output")
    path = contained_output(arguments.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "artifact": str(path.relative_to(ROOT)),
                "artifact_sha256": sha256_path(path),
                "scientific_payload_sha256": report["scientific_payload_sha256"],
                "result": "WROTE",
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
