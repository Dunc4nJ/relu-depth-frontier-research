#!/usr/bin/env python3
"""Exact gate for the preregistered isolation-aware rooted Reynolds law."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import importlib.util
from itertools import combinations_with_replacement
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Sequence

from flint import fmpz_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREREGISTRATION.md"
BASE_PATH = ROOT / "artifacts/math/G-0120/rooted_reynolds_gap.py"
BASE_PREREG = ROOT / "artifacts/math/G-0120/PREREGISTRATION.md"
BASE_RESULT = ROOT / "artifacts/math/G-0120/rooted_reynolds_gap_result.json"
BASE_VERIFIER = ROOT / "artifacts/math/G-0120/verify_rooted_reynolds_gap_result.py"

EXPECTED = {
    PREREGISTRATION: "c70d2e3edace6a9148796ec364d3c5b10e5ca285204e0db83beadd490a98134d",
    BASE_PREREG: "1f43bc85f8124e3147499527e6bd522e901c91d391b14d1d9c4fe12416ef8b79",
    BASE_PATH: "988a354bf797e138c720c24694b0c2f3c6da31874b7ca3dab027dbb937469846",
    BASE_RESULT: "918de947cd2fb0bbc49849cbe76253b28f282c4f553c46525c73d6e98a6c9754",
    BASE_VERIFIER: "29d7c922dd917832d32c55c26ba8aa5f0056f3be78c8b18d1a9676f468009cd7",
}

OLD_LEFT_RELATION = (
    24877879652,
    5644990098,
    18735931395,
    36075148648,
    1774428225462,
    -486075915678,
    72061959924,
    -30238018092,
    349051285883,
    196759610464,
    -4358895750,
    -622183212,
    311091606,
)
OLD_LEFT_TARGET_PAIRING = -74661985440
ORBIT_COUNT = 17


class IsolationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise IsolationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def matrix_sha(matrix: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(f"{matrix.shape[0]}x{matrix.shape[1]}\n".encode())
    for row in matrix:
        digest.update((",".join(str(int(value)) for value in row) + "\n").encode())
    return digest.hexdigest()


def vector_sha(vector: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(f"{vector.shape[0]}\n".encode())
    for value in vector:
        digest.update(f"{int(value)}\n".encode())
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    resolved = path.resolve(strict=False)
    require(resolved.parent == HERE, "output must be a direct child of G-0124")
    require(not resolved.exists() and not resolved.is_symlink(), f"refusing to overwrite {resolved}")
    descriptor = os.open(resolved, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def bind_inputs() -> dict[str, str]:
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"bound-input drift: {observed}")
    return {str(path.relative_to(ROOT)): digest for path, digest in observed.items()}


def isolated_old_labels(pair, n: int) -> int:
    used: set[int] = set()
    for side in pair:
        for u, v in side:
            require(0 <= u <= v < n, "source edge outside old-label set")
            used.add(u)
            used.add(v)
    return n - len(used)


def relabel_pair(base, pair, permutation: Sequence[int]):
    return tuple(
        tuple(sorted(base.relabel_edge(edge, permutation) for edge in side)) for side in pair
    )


def isolation_controls(base) -> dict[str, object]:
    planted = (((0, 0), (1, 2)), ((0, 3), (1, 3)))
    n = 6
    baseline = isolated_old_labels(planted, n)
    require(baseline == 2, "planted isolation count drift")
    permutations = ((2, 4, 0, 5, 1, 3), (5, 1, 3, 0, 4, 2))
    for permutation in permutations:
        require(
            isolated_old_labels(relabel_pair(base, planted, permutation), n) == baseline,
            "old-label relabelling changed isolation count",
        )
    swapped = (planted[1], planted[0])
    require(isolated_old_labels(swapped, n) == baseline, "branch swap changed isolation count")
    require(isolated_old_labels(planted, n + 1) == baseline + 1, "unused-label control failed")
    activated = (planted[0] + ((4, 4),), planted[1])
    require(isolated_old_labels(activated, n) == baseline - 1, "activation control failed")
    root_counting_mutant = (n + 1) - len({v for side in planted for edge in side for v in edge})
    require(root_counting_mutant == baseline + 1, "root-counting mutant was not detected")
    return {
        "definition": "q_n(t)=n-|V(A_t) union V(B_t)| before adjoining the root",
        "planted_q": baseline,
        "old_label_relabellings_checked": len(permutations),
        "branch_swap_preserved": True,
        "unused_old_label_increments_q": True,
        "activating_isolated_old_label_decrements_q": True,
        "adjoined_root_counting_mutant_rejected": True,
    }


@dataclass
class IsolationAggregate:
    transition: str
    source_n: int
    target_n: int
    degree: int
    denominator: int
    raw_count: int
    signed_classes: int
    directions: tuple
    matrix34: np.ndarray
    row_labels: list[dict[str, object]]
    orbit_raw_counts: dict[str, int]
    overflow_bounds: list[int]
    reconciliation: dict[str, object]
    q_distribution: dict[int, int]


def aggregate_isolation(base, dp, source, source_n: int, degree: int, transition: str) -> IsolationAggregate:
    target_n = source_n + 1
    root = target_n - 1
    edges = tuple(combinations_with_replacement(range(target_n), 2))
    denominator = base.coefficient_lcm(source)
    source_integer = [int(term.coefficient * denominator) for term in source]
    q_values = [isolated_old_labels(term.pair, source_n) for term in source]
    expected_raw = len(source) * len(edges) ** 2
    buckets: dict[bytes, dict[str, object]] = {}
    use_object = target_n >= 11
    dtype = object if use_object else np.int64
    common_loop = np.zeros(2 * ORBIT_COUNT, dtype=dtype)
    common_nonloop = np.zeros(2 * ORBIT_COUNT, dtype=dtype)
    orbit_raw = Counter()
    raw_count = 0
    for term_index, term in enumerate(source):
        coefficient = source_integer[term_index]
        q_value = q_values[term_index]
        for left_edge in edges:
            for right_edge in edges:
                orbit = base.rooted_orbit(left_edge, right_edge, root)
                orbit_index = base.ORBIT_INDEX[orbit]
                pair = (
                    tuple(sorted(term.pair[0] + (left_edge,))),
                    tuple(sorted(term.pair[1] + (right_edge,))),
                )
                residual, common = base.cancel_with_common(pair)
                key = base.signed_key(residual, target_n)
                bucket = buckets.setdefault(
                    key,
                    {"representative": residual, "weights": [0] * (2 * ORBIT_COUNT), "raw": 0},
                )
                weights = bucket["weights"]
                require(isinstance(weights, list), "bucket weight shape drift")
                weights[orbit_index] += coefficient
                weights[ORBIT_COUNT + orbit_index] += coefficient * q_value
                bucket["raw"] = int(bucket["raw"]) + 1
                loops, nonloops = base.common_counts(common)
                common_loop[orbit_index] += coefficient * loops
                common_nonloop[orbit_index] += coefficient * nonloops
                common_loop[ORBIT_COUNT + orbit_index] += coefficient * q_value * loops
                common_nonloop[ORBIT_COUNT + orbit_index] += coefficient * q_value * nonloops
                orbit_raw[orbit] += 1
                raw_count += 1
        print(f"G0124_RAW_{transition} {term_index + 1}/{len(source)}", flush=True)
    require(raw_count == expected_raw, f"{transition}: raw count drift")
    require(sum(orbit_raw.values()) == expected_raw, f"{transition}: orbit count drift")
    require(tuple(sorted(orbit_raw)) == tuple(sorted(base.ORBIT_NAMES)), f"{transition}: orbit loss")
    require(sum(int(bucket["raw"]) for bucket in buckets.values()) == expected_raw, f"{transition}: fiber drift")

    directions = base.direction_universe(target_n, degree + 1)
    row_by_direction = {direction: index for index, direction in enumerate(directions)}
    matrix = np.zeros((len(directions) + target_n, 2 * ORBIT_COUNT), dtype=dtype)
    semantic_bound = math.factorial(target_n) * (degree + 1)
    sum_abs_weights = [0] * (2 * ORBIT_COUNT)
    for bucket in buckets.values():
        for index, value in enumerate(bucket["weights"]):
            sum_abs_weights[index] += abs(int(value))
    loop_semantic = base.normal_form(dp, (((0, 0),), ((0, 0),)), target_n)
    nonloop_semantic = base.normal_form(dp, (((0, 1),), ((0, 1),)), target_n)
    require(not loop_semantic[1] and not nonloop_semantic[1], "common edge acquired hinge")
    overflow_bounds = []
    for column in range(2 * ORBIT_COUNT):
        bound = (
            sum_abs_weights[column] * semantic_bound
            + abs(int(common_loop[column])) * max(map(abs, loop_semantic[0]))
            + abs(int(common_nonloop[column])) * max(map(abs, nonloop_semantic[0]))
        )
        if not use_object:
            require(bound < base.INT64_SAFE_BOUND, f"{transition}: int64 bound exceeded at {column}")
        overflow_bounds.append(bound)

    for index, key in enumerate(sorted(buckets), start=1):
        bucket = buckets[key]
        weights = np.asarray(bucket["weights"], dtype=dtype)
        active = np.asarray([i for i, value in enumerate(weights) if int(value)], dtype=np.int64)
        if len(active):
            semantic = base.normal_form(dp, bucket["representative"], target_n)
            if semantic[1]:
                indices = np.asarray([row_by_direction[direction] for direction in semantic[1]], dtype=np.int64)
                values = np.asarray(list(semantic[1].values()), dtype=dtype)
                matrix[np.ix_(indices, active)] += values[:, None] * weights[active][None, :]
            matrix[len(directions) :, active] += (
                np.asarray(semantic[0], dtype=dtype)[:, None] * weights[active][None, :]
            )
        if index % 1000 == 0 or index == len(buckets):
            print(f"G0124_SEMANTIC_{transition} {index}/{len(buckets)}", flush=True)
    matrix[len(directions) :, :] += (
        np.asarray(loop_semantic[0], dtype=dtype)[:, None] * common_loop[None, :]
    )
    matrix[len(directions) :, :] += (
        np.asarray(nonloop_semantic[0], dtype=dtype)[:, None] * common_nonloop[None, :]
    )
    row_labels = [
        {"kind": "hinge", "direction": list(direction)} for direction in directions
    ] + [{"kind": "linear", "rank": rank + 1} for rank in range(target_n)]
    return IsolationAggregate(
        transition=transition,
        source_n=source_n,
        target_n=target_n,
        degree=degree,
        denominator=denominator,
        raw_count=raw_count,
        signed_classes=len(buckets),
        directions=directions,
        matrix34=matrix,
        row_labels=row_labels,
        orbit_raw_counts={name: orbit_raw[name] for name in base.ORBIT_NAMES},
        overflow_bounds=overflow_bounds,
        reconciliation={
            "raw_descriptors": raw_count,
            "fiber_raw_sum": sum(int(bucket["raw"]) for bucket in buckets.values()),
            "orbit_raw_sum": sum(orbit_raw.values()),
            "intercept_common_loop_weight_sums": [int(v) for v in common_loop[:ORBIT_COUNT]],
            "intercept_common_nonloop_weight_sums": [int(v) for v in common_nonloop[:ORBIT_COUNT]],
            "slope_common_loop_weight_sums": [int(v) for v in common_loop[ORBIT_COUNT:]],
            "slope_common_nonloop_weight_sums": [int(v) for v in common_nonloop[ORBIT_COUNT:]],
        },
        q_distribution=dict(sorted(Counter(q_values).items())),
    )


def target_for(aggregate: IsolationAggregate) -> np.ndarray:
    target = np.zeros(aggregate.matrix34.shape[0], dtype=object)
    target[-2] = -aggregate.denominator
    target[-1] = aggregate.denominator
    return target


def stage_matrix(aggregate: IsolationAggregate, stage: str) -> np.ndarray:
    intercept = aggregate.matrix34[:, :ORBIT_COUNT]
    slopes = aggregate.matrix34[:, ORBIT_COUNT:]
    if stage == "A":
        main_effect = np.asarray(
            [sum(int(value) for value in row) for row in slopes], dtype=object
        ).reshape((-1, 1))
        return np.concatenate((intercept.astype(object), main_effect), axis=1)
    require(stage == "B", f"unknown stage {stage}")
    return aggregate.matrix34.astype(object)


def stage_names(base, stage: str) -> list[str]:
    intercepts = [f"gamma:{name}" for name in base.ORBIT_NAMES]
    if stage == "A":
        return intercepts + ["delta:q"]
    return intercepts + [f"eta:{name}:q" for name in base.ORBIT_NAMES]


def rank_exact(matrix: np.ndarray) -> int:
    return int(fmpz_mat([[int(value) for value in row] for row in matrix]).rank())


def independent_row_indices(matrix: np.ndarray, target_rank: int) -> list[int]:
    basis: dict[int, list[Fraction]] = {}
    selected: list[int] = []
    for index, raw in enumerate(matrix):
        row = [Fraction(int(value)) for value in raw]
        for pivot in sorted(basis):
            if row[pivot]:
                factor = row[pivot]
                row = [x - factor * y for x, y in zip(row, basis[pivot], strict=True)]
        pivot = next((column for column, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        scale = row[pivot]
        basis[pivot] = [value / scale for value in row]
        selected.append(index)
        if len(selected) == target_rank:
            return selected
    raise IsolationError(f"could not find {target_rank} independent rows")


def primitive_null_vector(matrix: list[list[int]]) -> tuple[int, ...]:
    rows = [[Fraction(value) for value in row] for row in matrix]
    row_count = len(rows)
    column_count = len(rows[0])
    pivot_columns: list[int] = []
    pivot_row = 0
    for column in range(column_count):
        selected = next((i for i in range(pivot_row, row_count) if rows[i][column]), None)
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [value / scale for value in rows[pivot_row]]
        for i in range(row_count):
            if i != pivot_row and rows[i][column]:
                factor = rows[i][column]
                rows[i] = [x - factor * y for x, y in zip(rows[i], rows[pivot_row], strict=True)]
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == row_count:
            break
    free = [column for column in range(column_count) if column not in pivot_columns]
    require(len(free) == 1, f"expected unique null direction, got {len(free)}")
    vector = [Fraction() for _ in range(column_count)]
    vector[free[0]] = 1
    for row_index, column in reversed(list(enumerate(pivot_columns))):
        vector[column] = -sum(
            rows[row_index][j] * vector[j] for j in range(column + 1, column_count)
        )
    denominator = 1
    for value in vector:
        denominator = math.lcm(denominator, value.denominator)
    integers = [int(value * denominator) for value in vector]
    divisor = math.gcd(*(abs(value) for value in integers if value))
    integers = [value // divisor for value in integers]
    first = next(value for value in integers if value)
    if first < 0:
        integers = [-value for value in integers]
    return tuple(integers)


def old_witness_control(base_result: dict[str, object], first: IsolationAggregate) -> dict[str, object]:
    witness = base_result["joint_exact_Q_decision"]["witness"]
    indices = [int(index) for index in witness["row_indices"][:13]]
    old_matrix = [[int(value) for value in row] for row in witness["coefficient_matrix"][:13]]
    old_target = [int(value) for value in witness["target"][:13]]
    observed = [[int(value) for value in first.matrix34[index, :ORBIT_COUNT]] for index in indices]
    require(observed == old_matrix, "new intercept columns do not reproduce old witness rows")
    require([int(target_for(first)[index]) for index in indices] == old_target, "old target rows drift")
    transposed = [[old_matrix[row][column] for row in range(13)] for column in range(ORBIT_COUNT)]
    relation = primitive_null_vector(transposed)
    require(relation == OLD_LEFT_RELATION, "primitive old left relation drift")
    pairings = [
        sum(relation[row] * old_matrix[row][column] for row in range(13))
        for column in range(ORBIT_COUNT)
    ]
    require(pairings == [0] * ORBIT_COUNT, "old left relation does not annihilate intercepts")
    target_pairing = sum(relation[row] * old_target[row] for row in range(13))
    require(target_pairing == OLD_LEFT_TARGET_PAIRING, "old left target pairing drift")
    slope_sensitivities = [
        sum(
            relation[row] * int(first.matrix34[indices[row], ORBIT_COUNT + column])
            for row in range(13)
        )
        for column in range(ORBIT_COUNT)
    ]
    return {
        "rows": 13,
        "old_rank_over_Q": rank_exact(np.asarray(old_matrix, dtype=object)),
        "old_augmented_rank_over_Q": rank_exact(
            np.column_stack((np.asarray(old_matrix, dtype=object), np.asarray(old_target, dtype=object)))
        ),
        "primitive_left_relation": list(relation),
        "left_times_old_columns": pairings,
        "left_times_target": target_pairing,
        "stage_A_new_column_sensitivity": sum(slope_sensitivities),
        "stage_B_new_column_sensitivities": slope_sensitivities,
        "stage_A_old_witness_killed": sum(slope_sensitivities) != 0,
        "stage_B_old_witness_killed": any(slope_sensitivities),
        "zero_target_augmented_rank_over_Q": rank_exact(np.asarray(old_matrix, dtype=object)),
    }


def exact_decision(base, aggregates: Sequence[IsolationAggregate], stage: str):
    matrices = [stage_matrix(aggregate, stage) for aggregate in aggregates]
    targets = [target_for(aggregate) for aggregate in aggregates]
    matrix = np.concatenate(matrices, axis=0)
    target = np.concatenate(targets)
    augmented = np.column_stack((matrix, target))
    rank = rank_exact(matrix)
    augmented_rank = rank_exact(augmented)
    require(augmented_rank in (rank, rank + 1), "augmented rank jump exceeded one")
    labels = [
        {"transition": aggregate.transition, **label}
        for aggregate in aggregates
        for label in aggregate.row_labels
    ]
    names = stage_names(base, stage)
    output: dict[str, object] = {
        "stage": stage,
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "column_names": names,
        "rank_over_Q": rank,
        "augmented_rank_over_Q": augmented_rank,
        "matrix_sha256": matrix_sha(matrix),
        "target_sha256": vector_sha(target),
    }
    if augmented_rank > rank:
        selected = independent_row_indices(augmented, augmented_rank)
        small_matrix = matrix[selected]
        small_target = target[selected]
        small_rank = rank_exact(small_matrix)
        small_augmented_rank = rank_exact(np.column_stack((small_matrix, small_target)))
        require(small_rank < small_augmented_rank, "small rows are not an inconsistency witness")
        payload = {
            "matrix": [[int(value) for value in row] for row in small_matrix],
            "target": [int(value) for value in small_target],
        }
        output.update(
            {
                "result": "EXACT_Q_NONMEMBERSHIP",
                "witness": {
                    "row_indices": selected,
                    "row_labels": [labels[index] for index in selected],
                    "coefficient_matrix": [[str(int(value)) for value in row] for row in small_matrix],
                    "target": [str(int(value)) for value in small_target],
                    "rank_over_Q": small_rank,
                    "augmented_rank_over_Q": small_augmented_rank,
                    "canonical_sha256": canonical_sha(payload),
                },
            }
        )
        return output, None

    selected = independent_row_indices(matrix, rank)
    rows = [
        [Fraction(int(value)) for value in matrix[index]] + [Fraction(int(target[index]))]
        for index in selected
    ]
    pivots: dict[int, list[Fraction]] = {}
    for row in rows:
        for pivot in sorted(pivots):
            if row[pivot]:
                factor = row[pivot]
                row = [x - factor * y for x, y in zip(row, pivots[pivot], strict=True)]
        pivot = next((column for column, value in enumerate(row[:-1]) if value), None)
        require(pivot is not None, "solution pivot vanished")
        scale = row[pivot]
        pivots[pivot] = [value / scale for value in row]
    for pivot in sorted(pivots, reverse=True):
        for earlier in sorted(value for value in pivots if value < pivot):
            if pivots[earlier][pivot]:
                factor = pivots[earlier][pivot]
                pivots[earlier] = [
                    x - factor * y for x, y in zip(pivots[earlier], pivots[pivot], strict=True)
                ]
    solution = [Fraction() for _ in names]
    for pivot, row in pivots.items():
        solution[pivot] = row[-1]
    residual = [
        sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, solution, strict=True))
        - int(rhs)
        for row, rhs in zip(matrix, target, strict=True)
    ]
    require(not any(residual), "membership solution replay failed")
    active = next((i for i, value in enumerate(solution) if value and any(int(row[i]) for row in matrix)), None)
    require(active is not None, "membership solution has no active weight")
    deleted = solution.copy()
    deleted[active] = Fraction()
    require(
        any(
            sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, deleted, strict=True))
            != int(rhs)
            for row, rhs in zip(matrix, target, strict=True)
        ),
        "deleted-weight mutant escaped",
    )
    common_denominator = 1
    for value in solution:
        common_denominator = math.lcm(common_denominator, value.denominator)
    unit_mutant = solution.copy()
    unit_mutant[active] += Fraction(1, common_denominator)
    require(
        any(
            sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, unit_mutant, strict=True))
            != int(rhs)
            for row, rhs in zip(matrix, target, strict=True)
        ),
        "one-unit solution mutant escaped",
    )
    output.update(
        {
            "result": "EXACT_Q_MEMBERSHIP",
            "solution": {name: str(value) for name, value in zip(names, solution, strict=True)},
            "support": sum(bool(value) for value in solution),
            "free_variables_set_to_zero": len(names) - rank,
            "solution_common_denominator": common_denominator,
            "deleted_first_active_weight_mutant_rejected": names[active],
            "one_numerator_unit_mutant_rejected": names[active],
        }
    )
    return output, solution


def span_shift_controls(base, aggregates: Sequence[IsolationAggregate]) -> dict[str, object]:
    reports = {}
    for stage in ("A", "B"):
        original = np.concatenate([stage_matrix(aggregate, stage) for aggregate in aggregates], axis=0)
        shifted_parts = []
        for aggregate in aggregates:
            intercept = aggregate.matrix34[:, :ORBIT_COUNT].astype(object)
            slopes = aggregate.matrix34[:, ORBIT_COUNT:].astype(object)
            shifted_slopes = slopes + 3 * intercept
            if stage == "A":
                shifted = np.concatenate(
                    (
                        intercept,
                        np.asarray(
                            [sum(int(value) for value in row) for row in shifted_slopes], dtype=object
                        ).reshape((-1, 1)),
                    ),
                    axis=1,
                )
            else:
                shifted = np.concatenate((intercept, shifted_slopes), axis=1)
            shifted_parts.append(shifted)
        shifted_matrix = np.concatenate(shifted_parts, axis=0)
        original_rank = rank_exact(original)
        shifted_rank = rank_exact(shifted_matrix)
        joined_rank = rank_exact(np.concatenate((original, shifted_matrix), axis=1))
        require(original_rank == shifted_rank == joined_rank, f"q-origin shift changed Stage {stage} span")
        reports[stage] = {
            "shift": 3,
            "original_rank_over_Q": original_rank,
            "shifted_rank_over_Q": shifted_rank,
            "joined_rank_over_Q": joined_rank,
            "span_preserved": True,
        }
    return reports


def holdout_replay(base, aggregate: IsolationAggregate, stage: str, solution: Sequence[Fraction]) -> dict[str, object]:
    matrix = stage_matrix(aggregate, stage)
    target = target_for(aggregate)
    residual = [
        sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, solution, strict=True))
        - int(rhs)
        for row, rhs in zip(matrix, target, strict=True)
    ]
    nonzero = [
        {"row_index": index, "row_label": aggregate.row_labels[index], "residual": str(value)}
        for index, value in enumerate(residual)
        if value
    ]
    return {
        "evaluated": True,
        "stage": stage,
        "result": "EXACT_GAP11_IDENTITY" if not nonzero else "EXACT_GAP11_RESIDUAL",
        "rows": len(residual),
        "matrix_sha256": matrix_sha(matrix),
        "target_sha256": vector_sha(target),
        "nonzero_residual_count": len(nonzero),
        "complete_sparse_residual": nonzero,
        "compiled_MAX11_evaluated": False,
        "compiled_MAX11_reason": (
            "Gap11 identity failed; preregistered stop."
            if nonzero
            else "Gap11 identity passed; finite-certificate emission requires a separately bound serializer before promotion."
        ),
    }


def self_test() -> dict[str, object]:
    bind_inputs()
    base = load_module("g0124_base_selftest", BASE_PATH)
    verifier = load_module("g0124_verifier_selftest", BASE_VERIFIER)
    verified = verifier.verify(BASE_RESULT)
    require(verified["verdict"] == "VERIFIED_EXACT_Q_NONMEMBERSHIP", "base verifier failed")
    q_controls = isolation_controls(base)
    toy_null = primitive_null_vector([[1, 0, 1], [0, 1, 1]])
    require(toy_null == (1, 1, -1), "primitive-null self-test failed")
    require(matrix_sha(np.asarray([[1, 2], [3, 4]], dtype=object)) == matrix_sha(np.asarray([[1, 2], [3, 4]], dtype=np.int64)), "matrix digest depends on dtype")
    return {
        "base_exact_null_verified": True,
        "isolation_controls": q_controls,
        "primitive_null_control": list(toy_null),
        "dtype_independent_matrix_digest": True,
    }


def transition_report(
    base,
    aggregate: IsolationAggregate,
    old_report: dict[str, object] | None,
) -> dict[str, object]:
    intercept = aggregate.matrix34[:, :ORBIT_COUNT]
    if old_report is not None:
        intercept_i64 = np.asarray(intercept, dtype=np.int64)
        intercept_digest = base.array_sha(intercept_i64)
        require(
            intercept_digest == old_report["matrix_sha256"],
            f"{aggregate.transition}: old matrix digest drift",
        )
        intercept_digest_kind = "g0120_i64"
    else:
        intercept_digest = matrix_sha(intercept.astype(object))
        intercept_digest_kind = "canonical_decimal"
    require(len(aggregate.q_distribution) >= 2, f"{aggregate.transition}: isolation statistic is constant")
    slope_sum = stage_matrix(aggregate, "A")[:, -1]
    require(
        all(
            int(slope_sum[row])
            == sum(int(aggregate.matrix34[row, ORBIT_COUNT + column]) for column in range(ORBIT_COUNT))
            for row in range(aggregate.matrix34.shape[0])
        ),
        f"{aggregate.transition}: Stage A/Stage B reconciliation failed",
    )
    return {
        "source_n": aggregate.source_n,
        "target_n": aggregate.target_n,
        "source_degree": aggregate.degree,
        "target_degree": aggregate.degree + 1,
        "source_coefficient_lcm": aggregate.denominator,
        "raw_descriptors": aggregate.raw_count,
        "signed_W_classes": aggregate.signed_classes,
        "complete_hinge_rows": len(aggregate.directions),
        "linear_rows": aggregate.target_n,
        "q_distribution_by_source_term": {str(k): v for k, v in aggregate.q_distribution.items()},
        "orbit_raw_counts": aggregate.orbit_raw_counts,
        "intercept_matrix_sha256": intercept_digest,
        "intercept_matrix_digest_kind": intercept_digest_kind,
        "matrix34_canonical_sha256": matrix_sha(aggregate.matrix34),
        "row_order_sha256": canonical_sha(aggregate.row_labels),
        "int64_or_bigint_absolute_bounds": aggregate.overflow_bounds,
        "reconciliation": aggregate.reconciliation,
        "stage_A_column_equals_sum_stage_B_slope_columns": True,
    }


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = bind_inputs()
    base = load_module("g0124_bound_base", BASE_PATH)
    verifier = load_module("g0124_bound_verifier", BASE_VERIFIER)
    verified = verifier.verify(BASE_RESULT)
    require(verified["verdict"] == "VERIFIED_EXACT_Q_NONMEMBERSHIP", "base witness verification failed")
    base_result = json.loads(BASE_RESULT.read_text(encoding="utf-8"))
    base.bind_inputs()
    dp = base.load_dp("g0124_bound_dp")

    controls = {
        "g0120_independent_verifier": verified,
        "isolation_statistic": isolation_controls(base),
        **base.classifier_controls(dp),
        "signed_W_quotient_reconciliation": base.quotient_reconciliation_control(dp),
    }
    c5 = base.load_certificate(base.CERT5, 5, 2)
    c6 = base.load_certificate(base.CERT6, 6, 2)
    c7 = base.load_certificate(base.CERT7, 7, 3)
    c8 = base.load_certificate(base.CERT8, 8, 3)
    c9 = base.load_certificate(base.CERT9_395, 9, 4)
    c10 = base.load_certificate(base.CERT10, 10, 4)
    controls["public_certificate_replays"] = {
        "C5": base.replay_certificate(dp, c5, 5, 2, "public-C5"),
        "C6": base.replay_certificate(dp, c6, 6, 2, "public-C6"),
        "C7": base.replay_certificate(dp, c7, 7, 3, "public-C7"),
        "C8": base.replay_certificate(dp, c8, 8, 3, "public-C8"),
        "C9_G0115_395": base.replay_certificate(dp, c9, 9, 4, "G0115-395-C9"),
        "C10": base.replay_certificate(dp, c10, 10, 4, "public-C10"),
    }
    controls["source_gap_replays"] = {
        "Gap6": base.replay_gap(dp, c6, c5, 6, 2),
        "Gap8": base.replay_gap(dp, c8, c7, 8, 3),
        "Gap10": base.replay_gap(dp, c10, c9, 10, 4),
    }

    gap6 = base.gap_terms(c6, c5, 6)
    gap8 = base.gap_terms(c8, c7, 8)
    first = aggregate_isolation(base, dp, gap6, 6, 2, "Gap6_to_Gap7")
    second = aggregate_isolation(base, dp, gap8, 8, 3, "Gap8_to_Gap9")
    old_transitions = base_result["transitions"]
    transitions = {
        first.transition: transition_report(base, first, old_transitions[first.transition]),
        second.transition: transition_report(base, second, old_transitions[second.transition]),
    }
    controls["old_witness"] = old_witness_control(base_result, first)
    controls["q_origin_shift"] = span_shift_controls(base, (first, second))

    stage_a, stage_a_solution = exact_decision(base, (first, second), "A")
    if stage_a_solution is not None:
        chosen_stage = "A"
        chosen_solution = stage_a_solution
        stage_b = {"evaluated": False, "reason": "Stage A passed; preregistered minimal-stage rule."}
    else:
        stage_b, stage_b_solution = exact_decision(base, (first, second), "B")
        chosen_stage = "B" if stage_b_solution is not None else None
        chosen_solution = stage_b_solution

    holdout: dict[str, object]
    if chosen_solution is None:
        holdout = {
            "evaluated": False,
            "reason": "Both preregistered lower stages are exactly inconsistent.",
        }
        result_name = "LOWER_TRANSITION_EXACT_Q_NONMEMBERSHIP"
    else:
        gap10 = base.gap_terms(c10, c9, 10)
        third = aggregate_isolation(base, dp, gap10, 10, 4, "Gap10_to_Gap11")
        require(len(third.q_distribution) >= 2, "holdout isolation statistic is constant")
        holdout = holdout_replay(base, third, chosen_stage, chosen_solution)
        holdout["transition"] = transition_report(base, third, None)
        result_name = holdout["result"]

    result = {
        "schema": "g0124-isolation-aware-rooted-reynolds-v1",
        "result": result_name,
        "bindings": bindings | {
            "artifacts/math/G-0124/isolation_aware_reynolds_gap.py": script_hash,
            **base.bind_inputs(),
        },
        "operator": {
            "semantic_object": "G_n=n*MAX_n-Ind_n(MAX_(n-1))=top_gap",
            "source_statistic": "q_n(t)=number of old labels isolated in both source branches",
            "stage_A": "gamma_orbit + delta*q; 18 parameters",
            "stage_B": "gamma_orbit + eta_orbit*q; 34 parameters",
            "arity_dependence": "none",
            "aggregation": "raw_sum",
        },
        "controls": controls,
        "transitions": transitions,
        "lower_decisions": {"stage_A": stage_a, "stage_B": stage_b},
        "chosen_stage": chosen_stage,
        "MAX10_to_MAX11": holdout,
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Exact decision only for the preregistered isolation-affine rooted raw-sum kernels "
            "on the frozen source representations. A null does not decide other rooted flag "
            "algebras, source laws, MAX10 lift-span membership, or MAX11 representability."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    require(sha256(PREREGISTRATION) == EXPECTED[PREREGISTRATION], "preregistration changed during execution")
    write_exclusive(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require(args.self_test ^ args.run, "choose exactly one of --self-test or --run")
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(args.output is not None, "--run requires --output")
    result = run(args.output)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
