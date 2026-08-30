#!/usr/bin/env python3
"""Exact coefficient-tied degree-raising tests for the G-0112 discovery."""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import combinations_with_replacement
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Mapping, Sequence

from flint import fmpq_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0112 = ROOT / "artifacts/math/G-0112"
sys.path.insert(0, str(G0112))
import lower_n_double_star_potency as core  # noqa: E402


SCRIPT = Path(__file__).resolve()
CERT5 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_5_2.json"
CERT6 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json"
CERT7 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_7_3.json"
RELATION_REPORT = G0112 / "lower_n_relation_slices_v1.json"
GENERAL_REPORT = G0112 / "lower_n_general_edge_potency_v1.json"
EXPECTED = {
    "certificate_5_2": "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    "certificate_6_2": "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    "certificate_7_3": "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    "relation_report": "abd389675a5aaa39b0f670c0a8cf9394c69f8cc6f37bc3ab58dd3d8409e9c022",
    "general_report": "e2c66d41acfd0b0688dd63370ab9861422dde1fee833c278fb892c261cb2c292",
    "core": "93ff0492a8f0839d30a7b7cab5ab83696d6f54e80048da2586b8ae4afdbafa3b",
}
RELATIONS = (
    "common_nonloop",
    "share_one_nonloop",
    "disjoint_nonloop",
    "unequal_nonloop",
    "has_loop",
    "all",
)

Row = tuple[object, ...]
SparseVector = dict[Row, Fraction]
Semantic = core.Semantic


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def edge_relation(left: tuple[int, int], right: tuple[int, int]) -> str:
    if left[0] == left[1] or right[0] == right[1]:
        return "has_loop"
    if left == right:
        return "common_nonloop"
    if set(left) & set(right):
        return "share_one_nonloop"
    return "disjoint_nonloop"


def relation_targets(kind: str) -> tuple[str, ...]:
    output = [kind, "all"]
    if kind in ("share_one_nonloop", "disjoint_nonloop"):
        output.append("unequal_nonloop")
    return tuple(output)


def degrees(pair: core.one_star.cr.Pair, n: int) -> tuple[list[int], list[int]]:
    output = []
    for side in pair:
        degree = [0] * n
        for u, v in side:
            degree[u] += 1
            degree[v] += 1
        output.append(degree)
    return output[0], output[1]


def local_signature(
    pair: core.one_star.cr.Pair,
    left_edge: tuple[int, int],
    right_edge: tuple[int, int],
    n: int,
) -> str:
    """Branch/endpoint-swap invariant signature frozen in PREREGISTRATION.md."""
    left_degree, right_degree = degrees(pair, n)
    slots = (left_edge[0], left_edge[1], right_edge[0], right_edge[1])
    candidates: list[tuple[object, ...]] = []
    for branch_swap in (False, True):
        for swap_left in (False, True):
            for swap_right in (False, True):
                if branch_swap:
                    left_slots = (2, 3) if not swap_left else (3, 2)
                    right_slots = (0, 1) if not swap_right else (1, 0)
                else:
                    left_slots = (0, 1) if not swap_left else (1, 0)
                    right_slots = (2, 3) if not swap_right else (3, 2)
                order = left_slots + right_slots
                vertices = [slots[index] for index in order]
                block_by_vertex: dict[int, int] = {}
                partition: list[int] = []
                profiles: list[tuple[int, int, int]] = []
                for vertex in vertices:
                    if vertex not in block_by_vertex:
                        block_by_vertex[vertex] = len(block_by_vertex)
                        dl, dr = left_degree[vertex], right_degree[vertex]
                        if branch_swap:
                            dl, dr = dr, dl
                        profiles.append((dl, dr, int(dl == 0 and dr == 0)))
                    partition.append(block_by_vertex[vertex])
                candidates.append(
                    (edge_relation(left_edge, right_edge), tuple(partition), tuple(profiles))
                )
    signature = min(candidates)
    return json.dumps(signature, separators=(",", ":"))


def add_semantic(target: SparseVector, semantic: Semantic, scale: Fraction, block: str) -> None:
    if not scale:
        return
    linear, hinges = semantic
    for index, value in enumerate(linear):
        if value:
            target[(block, "linear", index)] += scale * value
    for direction, value in hinges:
        if value:
            target[(block, "hinge", direction)] += scale * value


def clean(vector: SparseVector) -> SparseVector:
    return {row: value for row, value in vector.items() if value}


def target_vector(n: int, block: str) -> SparseVector:
    return {(block, "linear", n - 1): Fraction(1)}


def combine_vectors(vectors: Iterable[tuple[SparseVector, Fraction]]) -> SparseVector:
    output: SparseVector = defaultdict(Fraction)
    for vector, scale in vectors:
        for row, value in vector.items():
            output[row] += scale * value
    return clean(output)


def difference(observed: Mapping[Row, Fraction], expected: Mapping[Row, Fraction]) -> SparseVector:
    rows = set(observed) | set(expected)
    return {row: observed.get(row, Fraction()) - expected.get(row, Fraction()) for row in rows
            if observed.get(row, Fraction()) != expected.get(row, Fraction())}


def vector_digest(vector: Mapping[Row, Fraction]) -> str:
    payload = [
        {"row": row_to_json(row), "value": str(value)}
        for row, value in sorted(vector.items(), key=lambda item: canonical(row_to_json(item[0])))
    ]
    return hashlib.sha256(canonical(payload)).hexdigest()


def row_to_json(row: Row) -> list[object]:
    output: list[object] = []
    for value in row:
        output.append(list(value) if isinstance(value, tuple) else value)
    return output


def build_family(certificate_path: Path, source_n: int, block: str) -> dict[str, object]:
    certificate = core.one_star.load_certificate(certificate_path, source_n, 2)
    edges = tuple(combinations_with_replacement(range(source_n + 1), 2))
    uniform: dict[str, SparseVector] = {name: defaultdict(Fraction) for name in RELATIONS}
    uniform_by_source: dict[tuple[int, str], SparseVector] = {}
    local: dict[str, SparseVector] = {}
    local_by_source: dict[tuple[int, str], SparseVector] = {}
    raw_counts = {name: 0 for name in RELATIONS}
    signature_counts: dict[str, int] = defaultdict(int)
    raw_count = 0
    semantic_digest = hashlib.sha256()
    for term_index, term in enumerate(certificate["terms"]):
        coefficient = Fraction(term["coefficient"])
        pair = core.one_star.parse_pair(term["pair"], source_n)
        for left_edge in edges:
            for right_edge in edges:
                lifted = (pair[0] + (left_edge,), pair[1] + (right_edge,))
                semantic = core.semantic(lifted, source_n + 1)
                require(
                    semantic == core.semantic((lifted[1], lifted[0]), source_n + 1),
                    "branch swap changed semantic column",
                )
                semantic_digest.update(canonical({
                    "term": term_index,
                    "left": left_edge,
                    "right": right_edge,
                    "semantic": semantic,
                }))
                kind = edge_relation(left_edge, right_edge)
                for name in relation_targets(kind):
                    add_semantic(uniform[name], semantic, coefficient, block)
                    source_key = (term_index, name)
                    if source_key not in uniform_by_source:
                        uniform_by_source[source_key] = defaultdict(Fraction)
                    add_semantic(uniform_by_source[source_key], semantic, Fraction(1), block)
                    raw_counts[name] += 1
                signature = local_signature(pair, left_edge, right_edge, source_n + 1)
                if signature not in local:
                    local[signature] = defaultdict(Fraction)
                add_semantic(local[signature], semantic, coefficient, block)
                local_source_key = (term_index, signature)
                if local_source_key not in local_by_source:
                    local_by_source[local_source_key] = defaultdict(Fraction)
                add_semantic(local_by_source[local_source_key], semantic, Fraction(1), block)
                signature_counts[signature] += 1
                raw_count += 1
    expected_raw = len(certificate["terms"]) * len(edges) ** 2
    require(raw_count == expected_raw, "raw edge-pair census drift")
    return {
        "certificate": certificate,
        "source_n": source_n,
        "block": block,
        "source_coefficients": [Fraction(term["coefficient"]) for term in certificate["terms"]],
        "uniform": {key: clean(value) for key, value in uniform.items()},
        "uniform_by_source": {key: clean(value) for key, value in uniform_by_source.items()},
        "local": {key: clean(value) for key, value in local.items()},
        "local_by_source": {key: clean(value) for key, value in local_by_source.items()},
        "raw_counts": raw_counts,
        "signature_counts": dict(signature_counts),
        "raw_count": raw_count,
        "edge_count": len(edges),
        "raw_semantic_stream_sha256": semantic_digest.hexdigest(),
    }


def qmatrix(rows: Sequence[Row], columns: Sequence[Mapping[Row, Fraction]]) -> fmpq_mat:
    return fmpq_mat([[str(column.get(row, Fraction())) for column in columns] for row in rows])


def pivots(matrix: fmpq_mat, rank: int) -> list[int]:
    reduced, observed_rank = matrix.rref()
    require(int(observed_rank) == rank, "RREF rank drift")
    output: list[int] = []
    start = 0
    for row in range(rank):
        pivot = next((column for column in range(start, matrix.ncols()) if reduced[row, column]), None)
        require(pivot is not None, "RREF pivot missing")
        output.append(int(pivot))
        start = int(pivot) + 1
    return output


def primitive_integer(values: Sequence[Fraction]) -> list[int]:
    denominator = 1
    for value in values:
        denominator = math.lcm(denominator, value.denominator)
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    common = 0
    for value in integers:
        common = math.gcd(common, abs(value))
    require(common > 0, "zero dual")
    integers = [value // common for value in integers]
    first = next(value for value in integers if value)
    return [-value for value in integers] if first < 0 else integers


def exact_decide(
    named_columns: Mapping[str, SparseVector],
    target: SparseVector,
    label: str,
) -> dict[str, object]:
    descriptors = sorted(named_columns)
    columns = [named_columns[name] for name in descriptors]
    row_set = set(target)
    for column in columns:
        row_set.update(column)
    rows = sorted(row_set, key=lambda row: canonical(row_to_json(row)))
    matrix = qmatrix(rows, columns)
    rhs = fmpq_mat([[str(target.get(row, Fraction()))] for row in rows])
    rank = int(matrix.rank())
    augmented = fmpq_mat([
        [str(column.get(row, Fraction())) for column in columns]
        + [str(target.get(row, Fraction()))]
        for row in rows
    ])
    augmented_rank = int(augmented.rank())
    require(augmented_rank in (rank, rank + 1), f"{label}: rank jump drift")
    digest = hashlib.sha256()
    for row in rows:
        digest.update(canonical({
            "row": row_to_json(row),
            "values": [str(column.get(row, Fraction())) for column in columns],
            "target": str(target.get(row, Fraction())),
        }))
    basis_columns = pivots(matrix, rank)
    basis_matrix = fmpq_mat([
        [str(columns[column].get(row, Fraction())) for column in basis_columns]
        for row in rows
    ])
    basis_rows = pivots(basis_matrix.transpose(), rank)
    square = fmpq_mat([
        [str(columns[column].get(rows[row], Fraction())) for column in basis_columns]
        for row in basis_rows
    ])
    if augmented_rank == rank:
        square_rhs = fmpq_mat([[str(target.get(rows[row], Fraction()))] for row in basis_rows])
        solution = square.solve(square_rhs)
        coefficients = [Fraction(str(solution[index, 0])) for index in range(rank)]
        observed = combine_vectors(
            (columns[column], coefficients[index])
            for index, column in enumerate(basis_columns)
        )
        residual = difference(observed, target)
        require(not residual, f"{label}: exact membership replay failed")
        support = [
            {"descriptor": descriptors[column], "coefficient": str(coefficients[index])}
            for index, column in enumerate(basis_columns)
            if coefficients[index]
        ]
        require(support, f"{label}: empty support")
        first = support[0]
        mutated = combine_vectors([
            (observed, Fraction(1)),
            (named_columns[str(first["descriptor"])], Fraction(1)),
        ])
        mutation_residual = difference(mutated, target)
        require(mutation_residual, f"{label}: coefficient mutation escaped")
        return {
            "label": label,
            "result": "EXACT_Q_MEMBERSHIP",
            "rows": len(rows),
            "columns": len(columns),
            "rank_over_Q": rank,
            "augmented_rank_over_Q": augmented_rank,
            "matrix_and_target_sha256": digest.hexdigest(),
            "support_size": len(support),
            "support": support,
            "complete_row_replay": True,
            "one_unit_weight_mutation_rejected_at": row_to_json(next(iter(mutation_residual))),
        }

    for extra_row in range(len(rows)):
        if extra_row in basis_rows:
            continue
        extra_rhs = fmpq_mat([[
            str(columns[column].get(rows[extra_row], Fraction()))
        ] for column in basis_columns])
        alpha = square.transpose().solve(extra_rhs)
        rational = [-Fraction(str(alpha[index, 0])) for index in range(rank)] + [Fraction(1)]
        support_rows = list(basis_rows) + [extra_row]
        target_pairing_q = sum(
            rational[index] * target.get(rows[row], Fraction())
            for index, row in enumerate(support_rows)
        )
        if not target_pairing_q:
            continue
        weights = primitive_integer(rational)
        for column in columns:
            pairing = sum(
                weights[index] * column.get(rows[row], Fraction())
                for index, row in enumerate(support_rows)
            )
            require(pairing == 0, f"{label}: dual failed to annihilate a column")
        target_pairing = sum(
            weights[index] * target.get(rows[row], Fraction())
            for index, row in enumerate(support_rows)
        )
        require(target_pairing, f"{label}: dual target pairing vanished")
        support = [
            {
                "row": row_to_json(rows[row]),
                "integer_weight": str(weights[index]),
            }
            for index, row in enumerate(support_rows)
            if weights[index]
        ]
        return {
            "label": label,
            "result": "EXACT_Q_NONMEMBERSHIP",
            "rows": len(rows),
            "columns": len(columns),
            "rank_over_Q": rank,
            "augmented_rank_over_Q": augmented_rank,
            "matrix_and_target_sha256": digest.hexdigest(),
            "dual_support_size": len(support),
            "dual_support": support,
            "integer_target_pairing": str(target_pairing),
            "all_columns_annihilated": True,
        }
    raise RuntimeError(f"{label}: rank gap but no exact dual found")


def weights(decision: Mapping[str, object]) -> dict[str, Fraction]:
    require(decision["result"] == "EXACT_Q_MEMBERSHIP", "weights requested from nonmembership")
    return {
        str(item["descriptor"]): Fraction(str(item["coefficient"]))
        for item in decision["support"]  # type: ignore[index]
    }


def replay_law(
    named_columns: Mapping[str, SparseVector],
    law: Mapping[str, Fraction],
    target: SparseVector,
) -> dict[str, object]:
    observed = combine_vectors(
        (named_columns[descriptor], coefficient)
        for descriptor, coefficient in law.items()
        if descriptor in named_columns
    )
    residual = difference(observed, target)
    return {
        "result": "EXACT_REPLAY_PASS" if not residual else "EXACT_REPLAY_FAIL",
        "residual_support_size": len(residual),
        "residual_sha256": vector_digest(residual),
        "first_residual": None if not residual else {
            "row": row_to_json(next(iter(residual))),
            "value": str(residual[next(iter(residual))]),
        },
        "law_support_present": sum(descriptor in named_columns for descriptor in law),
        "law_support_missing": sum(descriptor not in named_columns for descriptor in law),
    }


def source_mutation_rejected(
    family: Mapping[str, object],
    law: Mapping[str, Fraction],
    law_kind: str,
    target: SparseVector,
) -> bool:
    if law_kind == "uniform":
        by_source = family["uniform_by_source"]  # type: ignore[index]
    else:
        by_source = family["local_by_source"]  # type: ignore[index]
    mutation_parts = []
    for descriptor, coefficient in law.items():
        column = by_source.get((0, descriptor))  # type: ignore[union-attr]
        if column is not None:
            mutation_parts.append((column, coefficient))
    mutation = combine_vectors(mutation_parts)
    return bool(mutation) and bool(difference(combine_vectors([(target, 1), (mutation, 1)]), target))


def deleted_weight_rejected(
    named_columns: Mapping[str, SparseVector], law: Mapping[str, Fraction], target: SparseVector
) -> bool:
    descriptor = next(iter(law))
    reduced = dict(law)
    del reduced[descriptor]
    return replay_law(named_columns, reduced, target)["result"] == "EXACT_REPLAY_FAIL"


def stacked_columns(
    left: Mapping[str, SparseVector], right: Mapping[str, SparseVector]
) -> dict[str, SparseVector]:
    return {
        descriptor: combine_vectors([
            (left.get(descriptor, {}), Fraction(1)),
            (right.get(descriptor, {}), Fraction(1)),
        ])
        for descriptor in sorted(set(left) | set(right))
    }


def linear_summary(vector: Mapping[Row, Fraction], block: str) -> dict[str, object]:
    linear = {
        str(row[2] + 1): str(value)
        for row, value in vector.items()
        if row[0] == block and row[1] == "linear" and value
    }
    hinges = {
        row: value for row, value in vector.items()
        if row[0] == block and row[1] == "hinge" and value
    }
    return {
        "linear_nonzero": linear,
        "hinge_support_size": len(hinges),
        "hinge_part_sha256": vector_digest(hinges),
    }


def run(output: Path) -> None:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {
        "certificate_5_2": sha256(CERT5),
        "certificate_6_2": sha256(CERT6),
        "certificate_7_3": sha256(CERT7),
        "relation_report": sha256(RELATION_REPORT),
        "general_report": sha256(GENERAL_REPORT),
        "core": sha256(G0112 / "lower_n_double_star_potency.py"),
    }
    require(bindings == EXPECTED, "bound input drift")
    certificate5 = core.one_star.load_certificate(CERT5, 5, 2)
    certificate6 = core.one_star.load_certificate(CERT6, 6, 2)
    certificate7 = core.one_star.load_certificate(CERT7, 7, 3)
    controls = {
        "public_certificates_replayed": {
            "MAX5": core.one_star.replay_certificate(certificate5),
            "MAX6": core.one_star.replay_certificate(certificate6),
            "MAX7": core.one_star.replay_certificate(certificate7),
        }
    }
    family67 = build_family(CERT6, 6, "n7")
    family56 = build_family(CERT5, 5, "n6")
    target7 = target_vector(7, "n7")
    target6 = target_vector(6, "n6")

    uniform67 = family67["uniform"]
    uniform56 = family56["uniform"]
    uniform_summaries = {
        relation: linear_summary(uniform67[relation], "n7")
        for relation in RELATIONS
    }
    uniform_decision67 = exact_decide(uniform67, target7, "uniform-relations-6-to-7")
    uniform_law67 = weights(uniform_decision67) if uniform_decision67["result"] == "EXACT_Q_MEMBERSHIP" else {}
    uniform_replay56 = (
        replay_law(uniform56, uniform_law67, target6) if uniform_law67
        else {"result": "NOT_APPLICABLE_NO_6_TO_7_LAW"}
    )
    uniform_joint = exact_decide(
        stacked_columns(uniform67, uniform56),
        combine_vectors([(target7, 1), (target6, 1)]),
        "uniform-relations-joint-5-to-6-and-6-to-7",
    )

    per_source = {}
    for relation in ("share_one_nonloop", "disjoint_nonloop"):
        columns = {
            str(index): family67["uniform_by_source"][(index, relation)]
            for index in range(len(family67["source_coefficients"]))
        }
        decision = exact_decide(columns, target7, f"per-source-{relation}-6-to-7")
        ratios = None
        if decision["result"] == "EXACT_Q_MEMBERSHIP":
            solution = weights(decision)
            ratios = {
                descriptor: str(value / family67["source_coefficients"][int(descriptor)])
                for descriptor, value in solution.items()
            }
        per_source[relation] = {"decision": decision, "solution_over_source_coefficient": ratios}

    local67 = family67["local"]
    local56 = family56["local"]
    local_decision67 = exact_decide(local67, target7, "local-incidence-6-to-7")
    local_law67 = weights(local_decision67) if local_decision67["result"] == "EXACT_Q_MEMBERSHIP" else {}
    local_replay56 = (
        replay_law(local56, local_law67, target6) if local_law67
        else {"result": "NOT_APPLICABLE_NO_6_TO_7_LAW"}
    )
    local_joint = exact_decide(
        stacked_columns(local67, local56),
        combine_vectors([(target7, 1), (target6, 1)]),
        "local-incidence-joint-5-to-6-and-6-to-7",
    )

    controls.update({
        "branch_swap_checked_for_every_raw_column": True,
        "uniform_source_coefficient_mutation_rejected": (
            source_mutation_rejected(family67, uniform_law67, "uniform", target7)
            if uniform_law67 else None
        ),
        "uniform_deleted_weight_rejected": (
            deleted_weight_rejected(uniform67, uniform_law67, target7)
            if uniform_law67 else None
        ),
        "local_source_coefficient_mutation_rejected": (
            source_mutation_rejected(family67, local_law67, "local", target7)
            if local_law67 else None
        ),
        "local_deleted_weight_rejected": (
            deleted_weight_rejected(local67, local_law67, target7)
            if local_law67 else None
        ),
    })

    report = {
        "schema": "max11-g0114-degree-raising-identity-v1",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "claim_boundary": (
            "Exact coefficient-law tests on the public MAX5/MAX6 certificates and their "
            "one-edge-per-branch lifts. A passing lower-arity or joint law is not a MAX11 "
            "identity until replayed without refitting at MAX10->MAX11."
        ),
        "families": {
            "6_to_7": {
                "source_terms": len(family67["source_coefficients"]),
                "edge_count": family67["edge_count"],
                "raw_count": family67["raw_count"],
                "raw_counts": family67["raw_counts"],
                "local_signature_count": len(local67),
                "raw_semantic_stream_sha256": family67["raw_semantic_stream_sha256"],
            },
            "5_to_6": {
                "source_terms": len(family56["source_coefficients"]),
                "edge_count": family56["edge_count"],
                "raw_count": family56["raw_count"],
                "raw_counts": family56["raw_counts"],
                "local_signature_count": len(local56),
                "raw_semantic_stream_sha256": family56["raw_semantic_stream_sha256"],
            },
        },
        "uniform_relation_test": {
            "aggregate_normal_forms_6_to_7": uniform_summaries,
            "decision_6_to_7": uniform_decision67,
            "frozen_6_to_7_law_replay_5_to_6": uniform_replay56,
            "joint_shared_law_decision": uniform_joint,
        },
        "per_source_scalar_test": per_source,
        "local_incidence_test": {
            "decision_6_to_7": local_decision67,
            "free_signature_count": len(local67),
            "frozen_6_to_7_law_replay_5_to_6": local_replay56,
            "joint_shared_law_decision": local_joint,
            "joint_signature_union_count": len(set(local67) | set(local56)),
        },
        "controls": controls,
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as destination:
        destination.write(canonical(report))
        destination.flush()
        os.fsync(destination.fileno())
    print(json.dumps({
        "output": str(output),
        "uniform_6_to_7": uniform_decision67["result"],
        "uniform_joint": uniform_joint["result"],
        "local_6_to_7": local_decision67["result"],
        "local_joint": local_joint["result"],
        "wall_seconds": report["wall_seconds"],
    }, sort_keys=True))


def self_test() -> dict[str, object]:
    require(edge_relation((0, 1), (0, 1)) == "common_nonloop", "common relation")
    require(edge_relation((0, 1), (1, 2)) == "share_one_nonloop", "share relation")
    require(edge_relation((0, 1), (2, 3)) == "disjoint_nonloop", "disjoint relation")
    require(edge_relation((0, 0), (1, 2)) == "has_loop", "loop relation")
    vector = {("x", "linear", 0): Fraction(2)}
    require(not difference(combine_vectors([(vector, Fraction(1, 2))]), {
        ("x", "linear", 0): Fraction(1)
    }), "fractional vector arithmetic")
    certificate = core.one_star.load_certificate(CERT5, 5, 2)
    pair = core.one_star.parse_pair(certificate["terms"][0]["pair"], 5)
    a = local_signature(pair, (0, 1), (2, 3), 6)
    b = local_signature((pair[1], pair[0]), (2, 3), (0, 1), 6)
    require(a == b, "signature branch-swap drift")
    return {"relations": True, "fraction_arithmetic": True, "signature_invariance": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.output is None, "self-test refuses output")
        print(json.dumps(self_test(), sort_keys=True))
        return
    require(args.output is not None and not args.output.exists(), "unused output required")
    run(args.output)


if __name__ == "__main__":
    main()
