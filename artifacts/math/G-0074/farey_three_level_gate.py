#!/usr/bin/env python3
"""Exact all-spacings three-level gate for the frozen MAX11 Y-spoke family.

This program retains one shared coefficient vector across the registered
four-level G-0073 rows and every three-colour count profile at every Farey F6
breakpoint.  A positive result certifies the entire infinite locus of inputs
with at most three distinct coordinate values.  It is still not a global
CPWL identity verifier.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import combinations
import json
from math import comb, factorial, gcd
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Sequence

import flint
from flint import fmpq_mat, fmpz_mat, nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
G0073_SCRIPT = ROOT / "artifacts/math/G-0073/y_spoke_profile_gate.py"
G0073_PREFLIGHT = ROOT / "artifacts/math/G-0073/y_spoke_orbit_preflight_v1.json.gz"
G0073_OUTCOME = ROOT / "artifacts/math/G-0073/y_spoke_profile_gate_v1.json.gz"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0074.subject.manifest"

SCHEMA = "max11-g0074-farey-three-level-gate-v1"
PREFLIGHT_SCHEMA = "max11-g0074-farey-three-level-preflight-v1"
N = 11
PRIMES = (1_000_003, 1_000_033, 1_000_037)
FAREY_F6 = (
    (0, 1),
    (1, 6),
    (1, 5),
    (1, 4),
    (1, 3),
    (2, 5),
    (1, 2),
    (3, 5),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (1, 1),
)
EXPECTED_G0073_SCRIPT_SHA256 = (
    "333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67"
)
EXPECTED_G0073_PREFLIGHT_SHA256 = (
    "05908cba9a9ea47ccda0d07f2fa5af630c38c7031986ede57cb6a78dad611e1d"
)
EXPECTED_G0073_PREFLIGHT_SCIENTIFIC_SHA256 = (
    "d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8"
)
EXPECTED_G0073_OUTCOME_SHA256 = (
    "59b81312f44e98ae61481fcac2e61075d60d187c4bf5b4201a821c44ec3b60bb"
)
EXPECTED_G0073_OUTCOME_SCIENTIFIC_SHA256 = (
    "6c006df13c7e010128b8f2ce71b5a2eb9e599581d575f262ef8084637ef92f56"
)
EXPECTED_G0073_MATRIX_SHA256 = (
    "958bcdc7fbfc3d925aaed739aa98b60e10da35056186ec7e7c620cd26f34dc32"
)
EXPECTED_G0073_TARGET_SHA256 = (
    "a3d3be16df8de6f25b40e318f656efbee4607806413e72a48b2d276d7f21f4d7"
)
EXPECTED_ENVIRONMENT_SHA256 = (
    "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c"
)

# Filled only after the theorem/control preflight is frozen and adversarially
# reviewed.  Registered execution refuses to proceed while either is absent.
EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256: str | None = (
    "fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df"
)
EXPECTED_ROW_MANIFEST_SHA256: str | None = (
    "53e1766ce236da801ae963b47ee9ce42cdf5a10b978ccd69c9c9152b03ca140f"
)


class GateError(RuntimeError):
    """A frozen binding, exact control, or certificate contract failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_gzip(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise GateError(f"malformed JSON object: {path}")
    return document


def write_gzip(path: Path, document: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(document))


def load_frozen_g0073() -> ModuleType:
    observed = sha256_path(G0073_SCRIPT)
    if observed != EXPECTED_G0073_SCRIPT_SHA256:
        raise GateError(f"G-0073 producer drift: {observed}")
    module_name = "g0073_frozen_for_g0074"
    specification = importlib.util.spec_from_file_location(module_name, G0073_SCRIPT)
    if specification is None or specification.loader is None:
        raise GateError("could not construct frozen G-0073 import specification")
    module = importlib.util.module_from_spec(specification)
    sys.modules[module_name] = module
    specification.loader.exec_module(module)
    return module


G73 = load_frozen_g0073()


def verify_bindings() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    expected_files = {
        "g0073_producer": (G0073_SCRIPT, EXPECTED_G0073_SCRIPT_SHA256),
        "g0073_preflight": (G0073_PREFLIGHT, EXPECTED_G0073_PREFLIGHT_SHA256),
        "g0073_outcome": (G0073_OUTCOME, EXPECTED_G0073_OUTCOME_SHA256),
        "environment_manifest": (ENVIRONMENT_MANIFEST, EXPECTED_ENVIRONMENT_SHA256),
    }
    bindings: dict[str, dict[str, object]] = {}
    for name, (path, expected) in expected_files.items():
        observed = sha256_path(path)
        if observed != expected:
            raise GateError(f"binding drift for {name}: {observed} != {expected}")
        bindings[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    preflight = read_gzip(G0073_PREFLIGHT)
    if (
        preflight.get("scientific_payload_sha256")
        != EXPECTED_G0073_PREFLIGHT_SCIENTIFIC_SHA256
    ):
        raise GateError("G-0073 preflight scientific payload drift")
    outcome = read_gzip(G0073_OUTCOME)
    if (
        outcome.get("scientific_payload_sha256")
        != EXPECTED_G0073_OUTCOME_SCIENTIFIC_SHA256
    ):
        raise GateError("G-0073 outcome scientific payload drift")
    matrix_report = outcome.get("matrix")
    decision = outcome.get("decision")
    if not isinstance(matrix_report, dict) or not isinstance(decision, dict):
        raise GateError("malformed G-0073 outcome")
    if (
        matrix_report.get("matrix_int64_c_sha256") != EXPECTED_G0073_MATRIX_SHA256
        or matrix_report.get("target_int64_c_sha256") != EXPECTED_G0073_TARGET_SHA256
        or decision.get("result") != "PROFILE_GATE_EXACT_Q_MEMBERSHIP"
    ):
        raise GateError("G-0073 registered outcome contract drift")
    return bindings, outcome


def all_three_profiles() -> list[tuple[int, int, int]]:
    return [
        (zero, middle, N - zero - middle)
        for zero in range(N + 1)
        for middle in range(N + 1 - zero)
    ]


def three_assignment_count(profile: tuple[int, int, int]) -> int:
    result = factorial(sum(profile))
    for count in profile:
        result //= factorial(count)
    return result


def three_assignments(
    profile: tuple[int, int, int], numerator: int, denominator: int
) -> np.ndarray:
    zero_count, middle_count, top_count = profile
    if zero_count + middle_count + top_count != N:
        raise GateError(f"invalid three-profile: {profile}")
    vertices = tuple(range(N))
    rows: list[list[int]] = []
    for tops in combinations(vertices, top_count):
        top_set = set(tops)
        without_top = tuple(vertex for vertex in vertices if vertex not in top_set)
        for middles in combinations(without_top, middle_count):
            row = [0] * N
            for vertex in middles:
                row[vertex] = numerator
            for vertex in tops:
                row[vertex] = denominator
            rows.append(row)
    levels = np.asarray(rows, dtype=np.int16).T
    expected = (N, three_assignment_count(profile))
    if levels.shape != expected:
        raise GateError(f"three-assignment census drift at {profile}: {levels.shape}")
    return levels


def evaluate_all_columns(
    bases: Sequence[object], representatives: Sequence[object], levels: np.ndarray
) -> np.ndarray:
    grouped = G73.group_by_base(representatives, len(bases))
    row = np.zeros(len(representatives) + 3, dtype=np.int64)
    for base in bases:
        entries = grouped[base.position]
        if not entries:
            continue
        columns = np.asarray([column for column, _seed in entries], dtype=np.intp)
        values = G73.evaluate_seed_block(
            base, [seed for _column, seed in entries], levels
        )
        row[columns] = values.sum(axis=1, dtype=np.int64)
    offset = len(representatives)
    row[offset] = levels[0].sum(dtype=np.int64)
    row[offset + 1] = np.maximum(levels[0], levels[1]).sum(dtype=np.int64)
    row[offset + 2] = np.maximum(
        2 * levels[0], levels[1] + levels[2]
    ).sum(dtype=np.int64)
    return row


def evaluate_ratio_panel(
    ratio_index: int,
    numerator: int,
    denominator: int,
    bases: Sequence[object],
    representatives: Sequence[object],
) -> tuple[int, np.ndarray, np.ndarray]:
    profiles = all_three_profiles()
    matrix = np.zeros((len(profiles), len(representatives) + 3), dtype=np.int64)
    target = np.zeros(len(profiles), dtype=np.int64)
    for row, profile in enumerate(profiles):
        levels = three_assignments(profile, numerator, denominator)
        matrix[row] = evaluate_all_columns(bases, representatives, levels)
        if profile[2] > 0:
            highest = denominator
        elif profile[1] > 0:
            highest = numerator
        else:
            highest = 0
        target[row] = levels.shape[1] * highest
    return ratio_index, matrix, target


def build_ratio_panels(
    ratios: Sequence[tuple[int, int]],
    bases: Sequence[object],
    representatives: Sequence[object],
    workers: int,
    label: str,
) -> tuple[np.ndarray, np.ndarray]:
    results: dict[int, tuple[np.ndarray, np.ndarray]] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(
                evaluate_ratio_panel,
                index,
                numerator,
                denominator,
                bases,
                representatives,
            ): index
            for index, (numerator, denominator) in enumerate(ratios)
        }
        for future in as_completed(futures):
            index, matrix, target = future.result()
            results[index] = matrix, target
            print(
                f"G0074_{label} completed={len(results)}/{len(ratios)} index={index}",
                file=sys.stderr,
                flush=True,
            )
    matrix = np.concatenate([results[index][0] for index in range(len(ratios))])
    target = np.concatenate([results[index][1] for index in range(len(ratios))])
    expected_rows = len(ratios) * len(all_three_profiles())
    if matrix.shape != (expected_rows, len(representatives) + 3):
        raise GateError(f"ratio-panel matrix shape drift: {matrix.shape}")
    if target.shape != (expected_rows,):
        raise GateError("ratio-panel target shape drift")
    return matrix, target


def row_descriptors() -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = [
        {"kind": "G-0073-four-level", "profile": list(profile)}
        for profile in G73.all_profiles()
    ]
    for numerator, denominator in FAREY_F6:
        for profile in all_three_profiles():
            descriptors.append(
                {
                    "kind": "three-level-Farey-F6",
                    "ratio": [numerator, denominator],
                    "profile": list(profile),
                }
            )
    return descriptors


def farey_roots(coefficient_bound: int) -> set[Fraction]:
    roots: set[Fraction] = set()
    for slope in range(-coefficient_bound, coefficient_bound + 1):
        if slope == 0:
            continue
        for intercept in range(-coefficient_bound, coefficient_bound + 1):
            root = Fraction(-intercept, slope)
            if 0 <= root <= 1:
                roots.add(root)
    return roots


def structural_affine_switch_control() -> dict[str, object]:
    # On a fixed three-colour assignment with levels (0,t,1), a coordinate or
    # an edge maximum is one of the affine forms 0, t, or 1.  The following
    # finite Minkowski arithmetic is a structural superset of every frozen
    # expression/assignment; it therefore certifies the coefficient bound
    # without sampling expressions or points.
    level_forms = {(0, 0), (0, 1), (1, 0)}  # (intercept, slope)
    four_edge_sums = {
        (
            first[0] + second[0] + third[0] + fourth[0],
            first[1] + second[1] + third[1] + fourth[1],
        )
        for first in level_forms
        for second in level_forms
        for third in level_forms
        for fourth in level_forms
    }
    p_forms = {
        (left[0] - right[0], left[1] - right[1])
        for left in four_edge_sums
        for right in four_edge_sums
    }
    q_forms = {
        (
            auxiliary[0] + new_label[0] - 2 * anchor[0],
            auxiliary[1] + new_label[1] - 2 * anchor[1],
        )
        for auxiliary in level_forms
        for new_label in level_forms
        for anchor in level_forms
    }
    minus_forms = {
        (p[0] - q[0], p[1] - q[1]) for p in p_forms for q in q_forms
    }
    plus_forms = {
        (p[0] + q[0], p[1] + q[1]) for p in p_forms for q in q_forms
    }
    switch_forms = p_forms | q_forms | minus_forms | plus_forms
    maximum = max(abs(value) for form in switch_forms for value in form)
    if maximum != 6:
        raise GateError(f"structural affine coefficient bound drift: {maximum} != 6")
    roots = {
        Fraction(-intercept, slope)
        for intercept, slope in switch_forms
        if slope and 0 <= Fraction(-intercept, slope) <= 1
    }
    expected = {Fraction(numerator, denominator) for numerator, denominator in FAREY_F6}
    if not roots <= expected:
        raise GateError(f"structural switch root escaped F6: {sorted(roots - expected)}")
    serialized = [list(form) for form in sorted(switch_forms)]
    return {
        "level_affine_forms": len(level_forms),
        "four_edge_sum_forms": len(four_edge_sums),
        "p_forms": len(p_forms),
        "q_forms": len(q_forms),
        "orientation_zero_p_minus_q_forms": len(minus_forms),
        "orientation_one_p_plus_q_forms": len(plus_forms),
        "switch_forms": len(switch_forms),
        "switch_forms_sha256": canonical_sha256(serialized),
        "maximum_absolute_intercept_or_slope": maximum,
        "root_count": len(roots),
        "roots_sha256": canonical_sha256(
            [[root.numerator, root.denominator] for root in sorted(roots)]
        ),
        "all_roots_are_in_farey_f6": True,
    }


def point_from_code(code: int, values: Sequence[object]) -> list[object]:
    point: list[object] = []
    base = len(values)
    for _ in range(N):
        point.append(values[code % base])
        code //= base
    return point


def flattened_value(expression: object, point: Sequence[object]) -> object:
    left = sum(max(point[a - 1], point[b - 1]) for a, b in expression.left)
    right = sum(max(point[a - 1], point[b - 1]) for a, b in expression.right)
    simple = 2 * point[expression.anchor - 1]
    q = (
        point[expression.auxiliary - 1]
        + point[expression.new_label - 1]
        - simple
    )
    p = left - right
    if expression.orientation == 0:
        return right + simple + max(0, p, q)
    return right + simple + max(0, p, p + q)


def binary_matrix(
    bases: Sequence[object], representatives: Sequence[object]
) -> tuple[np.ndarray, np.ndarray]:
    matrix = np.zeros((N + 1, len(representatives) + 3), dtype=np.int64)
    target = np.zeros(N + 1, dtype=np.int64)
    vertices = tuple(range(N))
    for zero_count in range(N + 1):
        rows: list[list[int]] = []
        for zeros in combinations(vertices, zero_count):
            zero_set = set(zeros)
            rows.append([0 if vertex in zero_set else 1 for vertex in vertices])
        levels = np.asarray(rows, dtype=np.int16).T
        matrix[zero_count] = evaluate_all_columns(bases, representatives, levels)
        target[zero_count] = 0 if zero_count == N else levels.shape[1]
    return matrix, target


def pivot_columns_from_rref(rref: object, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    for row in range(rank):
        pivot = next(
            (column for column in range(columns) if rref[row, column] != 0),  # type: ignore[index]
            None,
        )
        if pivot is None:
            raise GateError("RREF row lacks a pivot")
        pivots.append(pivot)
    if pivots != sorted(set(pivots)):
        raise GateError("invalid RREF pivot sequence")
    return pivots


def modular_analysis(
    matrix: np.ndarray, target: np.ndarray, prime: int
) -> dict[str, object]:
    begun = time.perf_counter()
    field = nmod_mat(matrix.tolist(), prime)
    rref, rank_object = field.rref()
    rank = int(rank_object)
    pivots = pivot_columns_from_rref(rref, rank, matrix.shape[1])
    pivot_rows: list[int] = []
    mismatch_row: int | None = None
    if rank == 0:
        mismatch_row = next(
            (row for row, value in enumerate(target.tolist()) if int(value) % prime),
            None,
        )
    else:
        restricted = matrix[:, np.asarray(pivots, dtype=np.intp)]
        transposed = nmod_mat(restricted.T.tolist(), prime)
        row_rref, row_rank_object = transposed.rref()
        row_rank = int(row_rank_object)
        if row_rank != rank:
            raise GateError("modular pivot-column block lost rank under transpose")
        pivot_rows = pivot_columns_from_rref(row_rref, rank, matrix.shape[0])
        square = nmod_mat(
            matrix[
                np.ix_(
                    np.asarray(pivot_rows, dtype=np.intp),
                    np.asarray(pivots, dtype=np.intp),
                )
            ].tolist(),
            prime,
        )
        rhs = nmod_mat([[int(target[row]) % prime] for row in pivot_rows], prime)
        solution = square.solve(rhs)
        if square * solution != rhs:
            raise GateError("modular pivot-minor solution failed replay")
        for row in range(matrix.shape[0]):
            observed = sum(
                (int(matrix[row, column]) % prime) * int(solution[position, 0])
                for position, column in enumerate(pivots)
            ) % prime
            if observed != int(target[row]) % prime:
                mismatch_row = row
                break
    augmented_rank = rank if mismatch_row is None else rank + 1
    return {
        "prime": prime,
        "column_rank": rank,
        "augmented_rank": augmented_rank,
        "rank_gap": augmented_rank - rank,
        "pivot_columns": pivots,
        "pivot_rows": pivot_rows,
        "first_inconsistent_row": mismatch_row,
        "pivot_columns_sha256": canonical_sha256(pivots),
        "pivot_rows_sha256": canonical_sha256(pivot_rows),
        "seconds": time.perf_counter() - begun,
    }


def primitive_integer_vector(values: Sequence[int]) -> list[int]:
    divisor = 0
    for value in values:
        divisor = gcd(divisor, abs(int(value)))
    if divisor == 0:
        raise GateError("zero vector cannot be primitive-normalized")
    result = [int(value) // divisor for value in values]
    first = next(value for value in result if value)
    if first < 0:
        result = [-value for value in result]
    return result


def exact_dual_from_modular_violation(
    matrix: np.ndarray,
    target: np.ndarray,
    row_description: Sequence[dict[str, object]],
    modular: dict[str, object],
) -> dict[str, object] | None:
    prime = int(modular["prime"])
    pivot_columns = [int(value) for value in modular["pivot_columns"]]  # type: ignore[arg-type]
    pivot_rows = [int(value) for value in modular["pivot_rows"]]  # type: ignore[arg-type]
    mismatch = modular.get("first_inconsistent_row")
    if mismatch is None:
        return None
    mismatch_row = int(mismatch)
    if mismatch_row in pivot_rows:
        raise GateError("modularly inconsistent row is already a pivot row")
    selected_rows = [*pivot_rows, mismatch_row]
    selected_matrix = matrix[np.asarray(selected_rows, dtype=np.intp), :]
    selected_target = target[np.asarray(selected_rows, dtype=np.intp)]
    if not pivot_columns:
        vector = [1]
        nullity = 1
    else:
        reduced_transpose = fmpz_mat(
            selected_matrix[:, np.asarray(pivot_columns, dtype=np.intp)].T.tolist()
        )
        nullspace, nullity_object = reduced_transpose.nullspace()
        nullity = int(nullity_object)
        if nullity != 1:
            raise GateError(f"reduced exact dual nullity drift: {nullity} != 1")
        vector = primitive_integer_vector(
            [int(nullspace[row, 0]) for row in range(len(selected_rows))]
        )
    target_inner = sum(
        vector[position] * int(selected_target[position])
        for position in range(len(selected_rows))
    )
    if target_inner == 0:
        return None
    for column in range(matrix.shape[1]):
        residual = sum(
            vector[position] * int(selected_matrix[position, column])
            for position in range(len(selected_rows))
        )
        if residual != 0:
            return None
    normalized = [
        {
            "row_index": int(selected_rows[position]),
            "coefficient": str(Fraction(value, target_inner)),
            "descriptor": row_description[selected_rows[position]],
        }
        for position, value in enumerate(vector)
        if value
    ]
    normalized_inner = sum(
        Fraction(vector[position], target_inner) * int(selected_target[position])
        for position in range(len(selected_rows))
    )
    if normalized_inner != 1:
        raise GateError("normalized exact dual does not send target to one")
    return {
        "prime_used_for_basis_and_violation_selection": prime,
        "selected_pivot_rows": len(pivot_rows),
        "violating_row": mismatch_row,
        "selected_rows": len(selected_rows),
        "exact_reduced_nullity": nullity,
        "support_size": len(normalized),
        "normalized_sparse_rows": normalized,
        "normalized_sparse_rows_sha256": canonical_sha256(normalized),
        "selected_rows_sha256": canonical_sha256(selected_rows),
        "integer_target_inner_product": str(target_inner),
        "exact_replay": {
            "reduced_pivot_columns": len(pivot_columns),
            "all_original_columns_annihilated": matrix.shape[1],
            "normalized_target_inner_product": "1",
        },
    }


def exact_member_from_modular_basis(
    matrix: np.ndarray,
    target: np.ndarray,
    column_description: Sequence[dict[str, object]],
    modular: dict[str, object],
) -> dict[str, object] | None:
    prime = int(modular["prime"])
    pivot_columns = [int(value) for value in modular["pivot_columns"]]  # type: ignore[arg-type]
    pivot_rows = [int(value) for value in modular["pivot_rows"]]  # type: ignore[arg-type]
    rank = len(pivot_columns)
    if rank == 0:
        if np.any(target):
            return None
        return {
            "prime_used_for_basis_selection": prime,
            "rank": 0,
            "support_size": 0,
            "sparse_coefficients": [],
            "sparse_coefficients_sha256": canonical_sha256([]),
            "pivot_rows_sha256": canonical_sha256([]),
            "pivot_columns_sha256": canonical_sha256([]),
            "coefficient_convention": "all-zero exact coefficient vector",
            "exact_replay": {
                "rows_checked": matrix.shape[0],
                "original_columns": matrix.shape[1],
                "selected_original_columns": 0,
                "flint_square_residual_zero": True,
                "stdlib_fraction_full_residual_zero": True,
            },
        }
    if len(pivot_rows) != rank:
        raise GateError("modular report lacks a square pivot-row basis")
    square_array = matrix[
        np.ix_(
            np.asarray(pivot_rows, dtype=np.intp),
            np.asarray(pivot_columns, dtype=np.intp),
        )
    ]
    square = fmpq_mat(fmpz_mat(square_array.tolist()))
    if int(square.rank()) != rank:
        return None
    rhs = fmpq_mat(fmpz_mat([[int(target[row])] for row in pivot_rows]))
    solution = square.solve(rhs)
    if square * solution != rhs:
        raise GateError("exact square member solve failed its pivot replay")
    coefficients = [Fraction(str(solution[position, 0])) for position in range(rank)]
    for row in range(matrix.shape[0]):
        residual = sum(
            int(matrix[row, column]) * coefficients[position]
            for position, column in enumerate(pivot_columns)
        ) - int(target[row])
        if residual:
            return None
    sparse = [
        {
            "column_index": int(column),
            "coefficient": str(coefficients[position]),
            "descriptor": column_description[column],
        }
        for position, column in enumerate(pivot_columns)
        if coefficients[position]
    ]
    return {
        "prime_used_for_basis_selection": prime,
        "rank": rank,
        "support_size": len(sparse),
        "sparse_coefficients": sparse,
        "sparse_coefficients_sha256": canonical_sha256(sparse),
        "pivot_rows_sha256": canonical_sha256(pivot_rows),
        "pivot_columns_sha256": canonical_sha256(pivot_columns),
        "coefficient_convention": (
            "coefficients multiply Sym_avg; a literal unnormalized S_11 permutation "
            "sum must divide them by 11!"
        ),
        "exact_replay": {
            "rows_checked": matrix.shape[0],
            "original_columns": matrix.shape[1],
            "selected_original_columns": rank,
            "flint_square_residual_zero": True,
            "stdlib_fraction_full_residual_zero": True,
        },
    }


def public_modular_report(report: dict[str, object]) -> dict[str, object]:
    private = {"pivot_columns", "pivot_rows"}
    return {key: value for key, value in report.items() if key not in private}


def resolve_exact(
    matrix: np.ndarray,
    target: np.ndarray,
    column_description: Sequence[dict[str, object]],
    row_description: Sequence[dict[str, object]],
) -> dict[str, object]:
    if matrix.ndim != 2 or target.shape != (matrix.shape[0],):
        raise GateError("malformed exact-system shapes")
    if len(column_description) != matrix.shape[1] or len(row_description) != matrix.shape[0]:
        raise GateError("descriptor count disagrees with exact system")
    reports = [modular_analysis(matrix, target, prime) for prime in PRIMES]

    for report in reports:
        if int(report["rank_gap"]) == 0:
            solution = exact_member_from_modular_basis(
                matrix, target, column_description, report
            )
        else:
            solution = None
        if solution is not None:
            return {
                "result": "FAREY_GATE_EXACT_Q_MEMBERSHIP",
                "modular_diagnostics": [public_modular_report(item) for item in reports],
                "exact_dual": None,
                "exact_solution": solution,
                "interpretation": (
                    "One exact rational coefficient vector matches the G-0073 rows and every "
                    "three-level profile at every F6 node.  The Farey theorem extends this to "
                    "all inputs with at most three distinct values, but not to generic inputs."
                ),
            }
        if int(report["rank_gap"]) == 1:
            dual = exact_dual_from_modular_violation(
                matrix, target, row_description, report
            )
        else:
            dual = None
        if dual is not None:
            return {
                "result": "FAREY_GATE_EXACT_Q_NONMEMBERSHIP",
                "modular_diagnostics": [public_modular_report(item) for item in reports],
                "exact_dual": dual,
                "exact_solution": None,
                "interpretation": (
                    "The exact rational row dual rejects one shared coefficient vector even "
                    "over real outputs for this frozen family.  It is not an unrestricted "
                    "network lower bound."
                ),
            }

    return {
        "result": "FAREY_GATE_EXACT_Q_UNRESOLVED",
        "modular_diagnostics": [public_modular_report(item) for item in reports],
        "exact_dual": None,
        "exact_solution": None,
        "interpretation": (
            "The registered primes yielded neither a replayed exact member nor an exact dual; "
            "no membership or nonmembership inference is licensed."
        ),
    }


def run_controls(
    bases: Sequence[object],
    seeds: Sequence[object],
    representatives: Sequence[object],
) -> dict[str, object]:
    expected_farey = {Fraction(numerator, denominator) for numerator, denominator in FAREY_F6}
    observed_farey = farey_roots(6)
    if observed_farey != expected_farey:
        raise GateError("affine-root enumeration does not equal Farey F6")
    if Fraction(1, 7) in observed_farey or Fraction(1, 7) not in farey_roots(7):
        raise GateError("coefficient-bound mutant failed to expose 1/7")
    structural_affine = structural_affine_switch_control()

    samples = [
        expression
        for orientation in (0, 1)
        for expression in [
            seed.expression
            for seed in seeds
            if seed.expression.orientation == orientation
        ][:8]
    ]
    flattened_checks = 0
    orientation_mutant_differences = {"0": 0, "1": 0}
    for expression in samples:
        for code in range(0, 3**N, 977):
            point = point_from_code(code, (0, 1, 3))
            literal = G73.evaluate_expression(expression, point)
            flattened = flattened_value(expression, point)
            if literal != flattened:
                raise GateError("orientation-specific flattened identity failed")
            left = sum(max(point[a - 1], point[b - 1]) for a, b in expression.left)
            right = sum(max(point[a - 1], point[b - 1]) for a, b in expression.right)
            simple = 2 * point[expression.anchor - 1]
            q = point[expression.auxiliary - 1] + point[N - 1] - simple
            p = left - right
            mutant = (
                right + simple + max(0, p, p + q)
                if expression.orientation == 0
                else right + simple + max(0, p, q)
            )
            if mutant != literal:
                orientation_mutant_differences[str(expression.orientation)] += 1
            flattened_checks += 1
    if min(orientation_mutant_differences.values()) == 0:
        raise GateError("orientation p-q/p+q mutant was not detected")

    rational_scaling_checks = 0
    for numerator, denominator in ((1, 6), (2, 5), (5, 6)):
        rational_values = (Fraction(0), Fraction(numerator, denominator), Fraction(1))
        integer_values = (0, numerator, denominator)
        for expression in samples[:6]:
            for code in range(0, 3**N, 7919):
                integer_point = point_from_code(code, integer_values)
                rational_point = point_from_code(code, rational_values)
                integer_value = G73.evaluate_expression(expression, integer_point)
                rational_value = G73.evaluate_expression(expression, rational_point)
                if Fraction(integer_value, denominator) != rational_value:
                    raise GateError("integer/Fraction ratio scaling failed")
                rational_scaling_checks += 1

    shift_checks = 0
    homogeneity_checks = 0
    for expression in samples:
        point = [((17 * vertex + 3) % 9) - 4 for vertex in range(N)]
        shifted = [value + 5 for value in point]
        scaled = [3 * value for value in point]
        value = G73.evaluate_expression(expression, point)
        if G73.evaluate_expression(expression, shifted) != value + 30:
            raise GateError("Y-spoke shift degree is not six")
        if G73.evaluate_expression(expression, scaled) != 3 * value:
            raise GateError("Y-spoke positive homogeneity failed")
        shift_checks += 1
        homogeneity_checks += 1
    carrier_point = [((11 * vertex + 1) % 7) - 2 for vertex in range(N)]
    carrier_shift = [value + 4 for value in carrier_point]
    carriers = (
        lambda x: x[0],
        lambda x: max(x[0], x[1]),
        lambda x: max(2 * x[0], x[1] + x[2]),
    )
    for carrier, degree in zip(carriers, (1, 1, 2), strict=True):
        if carrier(carrier_shift) != carrier(carrier_point) + 4 * degree:
            raise GateError("carrier shift-degree control failed")
    vector_point = np.asarray(carrier_point, dtype=np.int16).reshape(N, 1)
    vector_shift = np.asarray(
        [value + 4 for value in carrier_point], dtype=np.int16
    ).reshape(N, 1)
    vector_scale = np.asarray(
        [3 * value for value in carrier_point], dtype=np.int16
    ).reshape(N, 1)
    vector_values = evaluate_all_columns(bases, representatives, vector_point)
    shifted_values = evaluate_all_columns(bases, representatives, vector_shift)
    scaled_values = evaluate_all_columns(bases, representatives, vector_scale)
    expected_shift = np.asarray(
        [24] * len(representatives) + [4, 4, 8], dtype=np.int64
    )
    if not np.array_equal(shifted_values, vector_values + expected_shift):
        raise GateError("all-column vectorized shift-degree control failed")
    if not np.array_equal(scaled_values, 3 * vector_values):
        raise GateError("all-column vectorized homogeneity control failed")

    endpoint_matrix, endpoint_target = build_ratio_panels(
        ((0, 1), (1, 1)),
        bases,
        representatives,
        min(2, max(1, os.cpu_count() or 1)),
        "ENDPOINT_CONTROL",
    )
    profile_count = len(all_three_profiles())
    endpoint_zero_matrix = endpoint_matrix[:profile_count]
    endpoint_zero_target = endpoint_target[:profile_count]
    endpoint_one_matrix = endpoint_matrix[profile_count:]
    endpoint_one_target = endpoint_target[profile_count:]
    binary, binary_target = binary_matrix(bases, representatives)
    profiles = all_three_profiles()
    for row, profile in enumerate(profiles):
        zero_factor = comb(profile[0] + profile[1], profile[1])
        zero_binary_row = profile[0] + profile[1]
        if not np.array_equal(
            endpoint_zero_matrix[row], zero_factor * binary[zero_binary_row]
        ) or int(endpoint_zero_target[row]) != zero_factor * int(binary_target[zero_binary_row]):
            raise GateError(f"t=0 endpoint multiplicity failed at {profile}")
        one_factor = comb(profile[1] + profile[2], profile[1])
        one_binary_row = profile[0]
        if not np.array_equal(
            endpoint_one_matrix[row], one_factor * binary[one_binary_row]
        ) or int(endpoint_one_target[row]) != one_factor * int(binary_target[one_binary_row]):
            raise GateError(f"t=1 endpoint multiplicity failed at {profile}")
    middle_only = profiles.index((0, N, 0))
    if int(endpoint_zero_target[middle_only]) != 0:
        raise GateError("target used colour index instead of actual level at t=0")

    one_column = [{"kind": "toy-column"}]
    point_row = [{"kind": "toy-row"}]
    for value in (0, 1):
        pointwise = resolve_exact(
            np.asarray([[1]], dtype=np.int64),
            np.asarray([value], dtype=np.int64),
            one_column,
            point_row,
        )
        if pointwise["result"] != "FAREY_GATE_EXACT_Q_MEMBERSHIP":
            raise GateError("pointwise-solvable shared-vector toy control failed")
    stacked = resolve_exact(
        np.asarray([[1], [1]], dtype=np.int64),
        np.asarray([0, 1], dtype=np.int64),
        one_column,
        [{"kind": "toy-row-0"}, {"kind": "toy-row-1"}],
    )
    if stacked["result"] != "FAREY_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("stacked common-coefficient toy mutant was not rejected")
    rank_deficient_member = resolve_exact(
        np.asarray([[1, 0], [2, 0]], dtype=np.int64),
        np.asarray([3, 6], dtype=np.int64),
        [{"kind": "toy-a"}, {"kind": "toy-b"}],
        [{"kind": "toy-row-0"}, {"kind": "toy-row-1"}],
    )
    if rank_deficient_member["result"] != "FAREY_GATE_EXACT_Q_MEMBERSHIP":
        raise GateError("rank-deficient exact-member control failed")
    rational_member_matrix = np.asarray(
        [[2, 0, 2], [0, 3, 3], [2, 3, 5], [4, 6, 10]], dtype=np.int64
    )
    rational_rows = [{"kind": f"rational-toy-row-{row}"} for row in range(4)]
    rational_columns = [{"kind": f"rational-toy-column-{column}"} for column in range(3)]
    rational_member = resolve_exact(
        rational_member_matrix,
        np.asarray([1, 1, 2, 4], dtype=np.int64),
        rational_columns,
        rational_rows,
    )
    if rational_member["result"] != "FAREY_GATE_EXACT_Q_MEMBERSHIP":
        raise GateError("fractional rank-deficient exact-member control failed")
    rational_mutant = resolve_exact(
        rational_member_matrix,
        np.asarray([1, 1, 2, 5], dtype=np.int64),
        rational_columns,
        rational_rows,
    )
    if rational_mutant["result"] != "FAREY_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("fractional member target mutant was not exactly rejected")
    exact_nonmember = resolve_exact(
        np.asarray([[0], [0]], dtype=np.int64),
        np.asarray([0, 1], dtype=np.int64),
        one_column,
        [{"kind": "toy-row-0"}, {"kind": "toy-row-1"}],
    )
    if exact_nonmember["result"] != "FAREY_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("exact-dual nonmember control failed")
    bad_prime_member = resolve_exact(
        np.asarray([[PRIMES[0]]], dtype=np.int64),
        np.asarray([1], dtype=np.int64),
        one_column,
        point_row,
    )
    if bad_prime_member["result"] != "FAREY_GATE_EXACT_Q_MEMBERSHIP":
        raise GateError("exceptional-prime exact-member control failed")
    hidden_gap = resolve_exact(
        np.asarray([[1], [1]], dtype=np.int64),
        np.asarray([0, PRIMES[0]], dtype=np.int64),
        one_column,
        [{"kind": "toy-row-0"}, {"kind": "toy-row-1"}],
    )
    if hidden_gap["result"] != "FAREY_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("exceptional-prime hidden-gap control failed")
    overflow_nonmember = resolve_exact(
        np.asarray([[10**12], [2 * 10**12]], dtype=np.int64),
        np.asarray([1, 3], dtype=np.int64),
        one_column,
        [{"kind": "toy-row-0"}, {"kind": "toy-row-1"}],
    )
    if overflow_nonmember["result"] != "FAREY_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("large-entry no-Gram exact-dual control failed")

    return {
        "affine_root_bound_six_equals_farey_f6": True,
        "farey_f6": [[n, d] for n, d in FAREY_F6],
        "bound_seven_mutant_exposes_one_seventh": True,
        "structural_affine_switch_control": structural_affine,
        "orientation_specific_flattened_checks": flattened_checks,
        "orientation_mutant_differences": orientation_mutant_differences,
        "integer_fraction_scaling_checks": rational_scaling_checks,
        "y_spoke_shift_degree_six_checks": shift_checks,
        "positive_homogeneity_checks": homogeneity_checks,
        "all_8107_columns_shift_and_homogeneity": True,
        "carrier_shift_degrees": [1, 1, 2],
        "endpoint_profiles_checked_each": len(profiles),
        "endpoint_matrix_sha256": {
            "t=0": hashlib.sha256(endpoint_zero_matrix.tobytes(order="C")).hexdigest(),
            "t=1": hashlib.sha256(endpoint_one_matrix.tobytes(order="C")).hexdigest(),
        },
        "actual_level_target_mutant_rejected": True,
        "separate_pointwise_solve_mutant_rejected": True,
        "rank_deficient_member_control": True,
        "fractional_rank_deficient_member_control": True,
        "fractional_target_mutant_dual_control": True,
        "exact_dual_nonmember_control": True,
        "exceptional_prime_member_control": True,
        "exceptional_prime_hidden_gap_control": True,
        "large_entry_no_gram_dual_control": True,
    }


def build_preflight(
    *, verify_vf2: bool
) -> tuple[list[object], list[object], list[object], dict[str, object]]:
    bindings, outcome = verify_bindings()
    bases, seeds, representatives, upstream = G73.build_preflight(
        verify_vf2=verify_vf2
    )
    if verify_vf2:
        G73.enforce_frozen_preflight(upstream)
        if (
            upstream.get("scientific_payload_sha256")
            != EXPECTED_G0073_PREFLIGHT_SCIENTIFIC_SHA256
        ):
            raise GateError("reconstructed G-0073 preflight drift")
    else:
        subject = upstream.get("subject")
        if not isinstance(subject, dict):
            raise GateError("malformed reduced G-0073 preflight")
        orbits = subject.get("orbits")
        charge = subject.get("boolean_charge")
        if not isinstance(orbits, dict) or not isinstance(charge, dict):
            raise GateError("malformed reduced G-0073 subject")
        reduced_observed = (
            subject.get("raw_seed_manifest_sha256"),
            orbits.get("orbit_manifest_sha256"),
            orbits.get("representative_manifest_sha256"),
            charge.get("charge_rows_sha256"),
            orbits.get("orbit_count"),
        )
        reduced_expected = (
            G73.EXPECTED_RAW_SEED_MANIFEST_SHA256,
            G73.EXPECTED_ORBIT_MANIFEST_SHA256,
            G73.EXPECTED_REPRESENTATIVE_MANIFEST_SHA256,
            G73.EXPECTED_CHARGE_ROWS_SHA256,
            G73.EXPECTED_ORBIT_COUNT,
        )
        if reduced_observed != reduced_expected:
            raise GateError("reduced G-0073 structural preflight drift")
    if len(representatives) != 8_104:
        raise GateError("G-0073 representative census drift")
    descriptors = row_descriptors()
    controls = run_controls(bases, seeds, representatives)
    subject = {
        "upstream_schema": outcome.get("schema"),
        "upstream_scientific_payload_sha256": outcome.get("scientific_payload_sha256"),
        "orbit_columns": len(representatives),
        "carrier_columns": ["C_L", "C_E", "C_Y"],
        "columns": len(representatives) + 3,
        "baseline_rows": len(G73.all_profiles()),
        "three_level_profiles": len(all_three_profiles()),
        "farey_nodes": len(FAREY_F6),
        "farey_rows": len(FAREY_F6) * len(all_three_profiles()),
        "total_rows": len(descriptors),
        "row_manifest_sha256": canonical_sha256(descriptors),
        "coefficient_policy": (
            "one shared free coefficient per frozen Y-spoke orbit and carrier across every row"
        ),
        "theorem_boundary": (
            "F6 equality certifies all real inputs with at most three distinct coordinate "
            "values after the registered shift-degree and homogeneity controls; it does not "
            "certify inputs with four or more distinct values"
        ),
    }
    scientific = {
        "schema": PREFLIGHT_SCHEMA,
        "bindings": bindings,
        "controls": controls,
        "subject": subject,
    }
    report = {
        **scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "script_sha256": sha256_path(SCRIPT),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": getattr(flint, "__version__", "unknown"),
        },
        "claim_boundary": (
            "This freezes an infinite-locus necessary gate and its exact solver only; no "
            "matrix outcome or global MAX11 identity is asserted by preflight."
        ),
    }
    return bases, seeds, representatives, report


def enforce_frozen_preflight(report: dict[str, object]) -> None:
    if EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256 is None or EXPECTED_ROW_MANIFEST_SHA256 is None:
        raise GateError("registered execution disabled until G-0074 preflight pins are frozen")
    subject = report.get("subject")
    if not isinstance(subject, dict):
        raise GateError("malformed G-0074 preflight subject")
    observed = (
        report.get("scientific_payload_sha256"),
        subject.get("row_manifest_sha256"),
    )
    expected = (EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256, EXPECTED_ROW_MANIFEST_SHA256)
    if observed != expected:
        raise GateError(f"frozen G-0074 preflight drift: {observed} != {expected}")


def build_combined_matrix(
    bases: Sequence[object],
    representatives: Sequence[object],
    workers: int,
    profile_budget: int,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    begun = time.perf_counter()
    _profiles, baseline_matrix, baseline_target, baseline_report = G73.build_profile_matrix(
        bases, representatives, workers, profile_budget
    )
    if (
        baseline_report.get("matrix_int64_c_sha256") != EXPECTED_G0073_MATRIX_SHA256
        or baseline_report.get("target_int64_c_sha256") != EXPECTED_G0073_TARGET_SHA256
    ):
        raise GateError("recomputed G-0073 baseline matrix drift")
    farey_matrix, farey_target = build_ratio_panels(
        FAREY_F6, bases, representatives, workers, "FAREY_PANEL"
    )
    matrix = np.concatenate((baseline_matrix, farey_matrix))
    target = np.concatenate((baseline_target, farey_target))
    descriptors = row_descriptors()
    if matrix.shape != (len(descriptors), len(representatives) + 3):
        raise GateError(f"combined matrix shape drift: {matrix.shape}")
    if target.shape != (len(descriptors),):
        raise GateError("combined target shape drift")
    report = {
        "rows": matrix.shape[0],
        "columns": matrix.shape[1],
        "baseline_rows": baseline_matrix.shape[0],
        "farey_rows": farey_matrix.shape[0],
        "row_manifest_sha256": canonical_sha256(descriptors),
        "column_manifest_sha256": baseline_report["column_manifest_sha256"],
        "baseline_matrix_sha256": baseline_report["matrix_int64_c_sha256"],
        "baseline_target_sha256": baseline_report["target_int64_c_sha256"],
        "farey_matrix_int64_c_sha256": hashlib.sha256(
            farey_matrix.tobytes(order="C")
        ).hexdigest(),
        "farey_target_int64_c_sha256": hashlib.sha256(
            farey_target.tobytes(order="C")
        ).hexdigest(),
        "combined_matrix_int64_c_sha256": hashlib.sha256(
            matrix.tobytes(order="C")
        ).hexdigest(),
        "combined_target_int64_c_sha256": hashlib.sha256(
            target.tobytes(order="C")
        ).hexdigest(),
        "maximum_absolute_entry": int(np.max(np.abs(matrix))),
        "seconds": time.perf_counter() - begun,
    }
    return matrix, target, report


def verify_member_between_nodes(
    bases: Sequence[object],
    representatives: Sequence[object],
    workers: int,
    solution: dict[str, object],
) -> dict[str, object]:
    nodes = [Fraction(numerator, denominator) for numerator, denominator in FAREY_F6]
    midpoints = [(left + right) / 2 for left, right in zip(nodes, nodes[1:])]
    ratios = [(value.numerator, value.denominator) for value in midpoints]
    matrix, target = build_ratio_panels(
        ratios, bases, representatives, workers, "INTERIOR_REPLAY"
    )
    sparse = solution.get("sparse_coefficients")
    if not isinstance(sparse, list):
        raise GateError("member solution lacks sparse coefficients")
    coefficients = [
        (int(item["column_index"]), Fraction(str(item["coefficient"])))
        for item in sparse
        if isinstance(item, dict)
    ]
    for row in range(matrix.shape[0]):
        observed = sum(
            int(matrix[row, column]) * coefficient
            for column, coefficient in coefficients
        )
        if observed != int(target[row]):
            raise GateError(f"interior rational member replay failed at row {row}")
    return {
        "midpoint_ratios": [[n, d] for n, d in ratios],
        "rows_checked": matrix.shape[0],
        "matrix_sha256": hashlib.sha256(matrix.tobytes(order="C")).hexdigest(),
        "target_sha256": hashlib.sha256(target.tobytes(order="C")).hexdigest(),
        "stdlib_fraction_residual_zero": True,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--profile-budget", type=int, default=600_000)
    parser.add_argument("--skip-full-vf2", action="store_true")
    parser.add_argument("--expected-script-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    begun = time.perf_counter()
    if arguments.workers < 1:
        raise GateError("workers must be positive")
    bases, seeds, representatives, preflight = build_preflight(
        verify_vf2=not arguments.skip_full_vf2
    )
    if arguments.self_test:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "mode": "self-test",
                    "controls": preflight["controls"],
                    "rows": preflight["subject"]["total_rows"],
                    "columns": preflight["subject"]["columns"],
                },
                sort_keys=True,
            )
        )
        return
    if arguments.preflight_only:
        if arguments.output is not None:
            write_gzip(arguments.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return

    observed_script = sha256_path(SCRIPT)
    if arguments.expected_script_sha256 != observed_script:
        raise GateError("registered run requires the exact preregistered script SHA-256")
    if arguments.output is None:
        raise GateError("registered run requires --output")
    enforce_frozen_preflight(preflight)
    matrix, target, matrix_report = build_combined_matrix(
        bases, representatives, arguments.workers, arguments.profile_budget
    )
    columns = G73.profile_column_descriptors(representatives)
    rows = row_descriptors()
    decision = resolve_exact(matrix, target, columns, rows)
    interior_replay = None
    if decision["result"] == "FAREY_GATE_EXACT_Q_MEMBERSHIP":
        solution = decision.get("exact_solution")
        if not isinstance(solution, dict):
            raise GateError("member decision lacks exact solution")
        interior_replay = verify_member_between_nodes(
            bases, representatives, arguments.workers, solution
        )
    scientific_decision = {
        **decision,
        "modular_diagnostics": [
            {key: value for key, value in report.items() if key != "seconds"}
            for report in decision["modular_diagnostics"]
        ],
    }
    scientific = {
        "schema": SCHEMA,
        "subject": preflight["subject"],
        "preflight_scientific_payload_sha256": preflight["scientific_payload_sha256"],
        "matrix": {key: value for key, value in matrix_report.items() if key != "seconds"},
        "decision": scientific_decision,
        "interior_member_replay": interior_replay,
    }
    result = {
        **scientific,
        "mode": "registered-run",
        "bindings": preflight["bindings"],
        "controls": preflight["controls"],
        "script_sha256": observed_script,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "matrix_seconds": matrix_report["seconds"],
        "rank_seconds": [
            report["seconds"] for report in decision["modular_diagnostics"]
        ],
        "workers": arguments.workers,
        "wall_seconds": time.perf_counter() - begun,
        "interpretation_boundary": (
            "Exact membership certifies the infinite at-most-three-valued locus only; exact "
            "nonmembership rejects only the frozen 8,107-column family.  Neither outcome alone "
            "is an unrestricted network theorem."
        ),
    }
    write_gzip(arguments.output, result)
    print(
        json.dumps(
            {
                "output": str(arguments.output),
                "output_sha256": sha256_path(arguments.output),
                "scientific_payload_sha256": result["scientific_payload_sha256"],
                "decision": scientific_decision,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
