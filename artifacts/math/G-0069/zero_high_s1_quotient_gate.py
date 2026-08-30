#!/usr/bin/env python3
"""Two-prime S1 quotient gate for the first exact zero-high mass-five atoms.

The three frozen candidates are genuine signed-mass-five single-edge lifts but
have no primitive hinge of positive mass five.  Their complete normal forms
therefore live on the 99,858-row degree-four universe.  This program reduces
those exact columns against the certified rank-1,288 G-0061 S1 basis.

Unlike the proper candidates in G-0059, these candidates may have nonzero
Lambda.  The Schur functional is therefore

    delta = candidate_Lambda - lambda_C B^{-1} candidate_on_pivot_rows.

Every modular circuit is replayed on all 99,858 rows and normalized to Lambda
one.  It remains a finite-field discovery witness until an exact-Q lift and a
complete linear-normal-form/function replay are supplied.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import gzip
import hashlib
import importlib.util
import json
from math import factorial
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Any, Sequence

from flint import nmod_mat
import numpy as np


N = 11
PRIMES = (1_000_003, 1_000_033)
EXPECTED_ROWS = 99_858
EXPECTED_BASELINE_COLUMNS = 1_358
EXPECTED_BASELINE_RANK = 1_288
EXPECTED_CANDIDATES = 3
FULL_ORBIT_MULTIPLIER = factorial(N)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0049_SCRIPT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
G0060_SCRIPT = ROOT / "artifacts/math/G-0060/boolean_mobius_ancestry.py"
G0060_REPORT = ROOT / "artifacts/math/G-0060/report_v1.json"
G0061_SCRIPT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift.py"
G0061_REPORT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift_v1.json.gz"
DEFAULT_OUTPUT = HERE / "zero_high_s1_quotient_gate_v1.json.gz"
SCHEMA = "max11-g0069-zero-high-s1-quotient-gate-v1"

EXPECTED_INPUT_HASHES = {
    "g0049_script_sha256": "0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04",
    "g0060_script_sha256": "da249cad23877d78be4de93ebdc49f771033e9084b1b7168893f35bbeb8c6e53",
    "g0060_report_sha256": "2bf930f9bcc77c6da27199e5e9374fd0a0d31844222d9afff43c65b50b58513a",
    "g0061_script_sha256": "2e0ad714b2f56104fc70b98c5527f291769acb7a32053e44840a643d7046e7e8",
    "g0061_report_sha256": "d372ac740e485b4608b23a879ed466051aa1d45f899aa9dce89ff8d2ee13b7f2",
}

# Zero-based class indices with one-based edge endpoints, in the exact G-0049 order.
WITNESSES: dict[int, dict[str, Any]] = {
    161: {
        "pair": [
            [[1, 2], [1, 3], [1, 4], [1, 5], [6, 11]],
            [[1, 6], [2, 7], [6, 8], [9, 10], [2, 11]],
        ],
        "seed_boolean_mobius_charge": 0,
    },
    3_600: {
        "pair": [
            [[1, 2], [1, 3], [1, 4], [5, 6], [7, 11]],
            [[1, 7], [1, 8], [7, 9], [9, 10], [2, 11]],
        ],
        "seed_boolean_mobius_charge": 0,
    },
    7_172: {
        "pair": [
            [[1, 2], [1, 3], [2, 4], [5, 6], [7, 11]],
            [[1, 5], [1, 7], [8, 9], [8, 10], [3, 11]],
        ],
        "seed_boolean_mobius_charge": -12,
    },
}
CANDIDATE_ORDER = tuple(WITNESSES)

Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]
Direction = tuple[int, ...]


class GateError(RuntimeError):
    """Fail-closed input, semantic, or algebra error."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def int64_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(
        value.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()


def uint32_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(
        value.astype("<u4", copy=False).tobytes(order="C")
    ).hexdigest()


def deterministic_view(value: object) -> object:
    dynamic = {
        "seconds",
        "semantic_seconds",
        "wall_seconds",
        "available_gib",
        "memory_available_bytes",
    }
    if isinstance(value, dict):
        return {
            key: deterministic_view(item)
            for key, item in value.items()
            if key not in dynamic
        }
    if isinstance(value, list):
        return [deterministic_view(item) for item in value]
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise GateError(f"bound script drift: {path}: {observed} != {expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def input_bindings() -> dict[str, str]:
    paths = {
        "g0049_script_sha256": G0049_SCRIPT,
        "g0060_script_sha256": G0060_SCRIPT,
        "g0060_report_sha256": G0060_REPORT,
        "g0061_script_sha256": G0061_SCRIPT,
        "g0061_report_sha256": G0061_REPORT,
    }
    observed = {key: sha256_path(path) for key, path in paths.items()}
    if observed != EXPECTED_INPUT_HASHES:
        raise GateError(f"input binding drift: observed={observed}")
    return observed


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [
        [[int(u), int(v)] for u, v in branch]
        for branch in pair
    ]


def zero_based(pair: Pair) -> Pair:
    return tuple(
        tuple((u - 1, v - 1) for u, v in branch) for branch in pair
    )  # type: ignore[return-value]


def positive_mass(direction: Direction) -> int:
    if sum(direction):
        raise GateError(f"non-zero-sum primitive direction: {direction}")
    return sum(value for value in direction if value > 0)


def reconstruct_candidates(
    g0049: ModuleType, charge_tools: ModuleType
) -> tuple[list[Pair], list[dict[str, Any]]]:
    same, cross, reconstruction = g0049.build_raw_lift_families()
    if len(same) != 9_804 or len(cross) != 3_615:
        raise GateError("G-0049 lift-family census drift")
    pairs: list[Pair] = []
    descriptors: list[dict[str, Any]] = []
    for class_index in CANDIDATE_ORDER:
        pair = same[class_index]
        expected = WITNESSES[class_index]
        if serialize_pair(pair) != expected["pair"]:
            raise GateError(f"same-family representative drift at {class_index}")
        zero_pair = zero_based(pair)
        charge = charge_tools.boolean_mobius_charge(
            N, lambda point, p=zero_pair: charge_tools.pair_atom_value(p, point)
        )
        if charge.denominator != 1 or int(charge) != expected["seed_boolean_mobius_charge"]:
            raise GateError(f"Boolean charge drift at same class {class_index}: {charge}")
        pairs.append(pair)
        descriptors.append(
            {
                "candidate_position": len(descriptors),
                "family": "same",
                "class_index": class_index,
                "pair": serialize_pair(pair),
                "signed_mass_after_exact_common_edge_cancellation": 5,
                "seed_boolean_mobius_charge": int(charge),
                "expected_full_orbit_lambda": FULL_ORBIT_MULTIPLIER * int(charge),
            }
        )
    return pairs, [
        *descriptors,
        {
            "reconstruction_control": {
                "same_raw_and_orbit_family_rebuilt_from_G0049": True,
                "upstream_reconstruction_sha256": canonical_sha256(reconstruction),
            }
        },
    ]


def candidate_payloads(pairs: list[Pair]) -> list[tuple[int, str, int, dict[str, Any]]]:
    payloads = []
    for order, (class_index, pair) in enumerate(zip(CANDIDATE_ORDER, pairs, strict=True)):
        pair_zero = zero_based(pair)
        used = {vertex for branch in pair_zero for edge in branch for vertex in edge}
        if used != set(range(N)):
            raise GateError(f"candidate {class_index} is not active on all coordinates")
        payloads.append(
            (
                order,
                "g0069_same_zero_high",
                class_index,
                {
                    "sequence": 6_900_000 + class_index,
                    "negative_edges": [list(edge) for edge in pair_zero[0]],
                    "positive_edges": [list(edge) for edge in pair_zero[1]],
                },
            )
        )
    return payloads


def generate_and_crosscheck_candidates(
    g0057: ModuleType,
    g0049: ModuleType,
    charge_tools: ModuleType,
    universe: tuple[Direction, ...],
    workers: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    pairs, descriptors_plus = reconstruct_candidates(g0049, charge_tools)
    descriptors = descriptors_plus[:-1]
    reconstruction_control = descriptors_plus[-1]
    results, seconds = g0057.generate_semantics(
        candidate_payloads(pairs), g0057.ROW_INDEX, workers, "G0069_ZERO_HIGH"
    )
    if len(results) != EXPECTED_CANDIDATES:
        raise GateError("candidate semantic census drift")

    crosschecks = []
    for position, (class_index, pair, result, descriptor) in enumerate(
        zip(CANDIDATE_ORDER, pairs, results, descriptors, strict=True)
    ):
        if int(result["source_id"]) != class_index or int(result["order"]) != position:
            raise GateError(f"candidate identity/order drift at {class_index}")
        expected_lambda = int(descriptor["expected_full_orbit_lambda"])
        if int(result["lambda"]) != expected_lambda:
            raise GateError(
                f"full-orbit Lambda drift at {class_index}: "
                f"{result['lambda']} != {expected_lambda}"
            )
        observed_hinges = {
            universe[int(row)]: int(value)
            for row, value in zip(result["rows"], result["values"], strict=True)
        }
        independent = g0049.exact_semantic_column(pair, N)
        if observed_hinges != independent.hinges:
            raise GateError(f"G-0057/G-0049 exact hinge disagreement at {class_index}")
        degree_histogram = Counter(positive_mass(direction) for direction in observed_hinges)
        if any(degree >= 5 for degree in degree_histogram):
            raise GateError(f"zero-high candidate leaked a mass-five hinge: {class_index}")
        crosschecks.append(
            {
                **descriptor,
                "active_vertices": int(result["active_vertices"]),
                "degree4_universe_support_size": len(result["rows"]),
                "hinge_positive_mass_histogram": {
                    str(key): value for key, value in sorted(degree_histogram.items())
                },
                "full_orbit_lambda": int(result["lambda"]),
                "g0057_sparse_semantic_sha256": str(result["semantic_sha256"]),
                "g0049_complete_normal_form_sha256": g0049.semantic_column_digest(independent),
                "g0049_linear_coordinates": [int(value) for value in independent.linear],
                "g0049_g0057_complete_hinges_identical": True,
                "all_primitive_hinges_have_positive_mass_at_most_four": True,
            }
        )
    return results, {
        "semantic_seconds": seconds,
        "ordered_candidates": crosschecks,
        "ordered_candidate_descriptors_sha256": canonical_sha256(descriptors),
        "ordered_g0057_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(results),
        **reconstruction_control,
    }


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.int64)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def from_nmod(matrix: nmod_mat) -> np.ndarray:
    return np.asarray(matrix.tolist(), dtype=np.int64)


def rank_mod(matrix: np.ndarray, prime: int) -> int:
    return int(to_nmod(matrix, prime).rank())


def subset_record(
    residual: np.ndarray,
    delta: np.ndarray,
    indices: tuple[int, ...],
    prime: int,
) -> dict[str, Any]:
    selected = np.ascontiguousarray(residual[:, indices], dtype=np.int64)
    selected_delta = np.ascontiguousarray(delta[list(indices)], dtype=np.int64)
    candidate_major = selected.T
    augmented = np.column_stack((candidate_major, selected_delta))
    residual_rank = rank_mod(candidate_major, prime)
    augmented_rank = rank_mod(augmented, prime)
    gain = augmented_rank - residual_rank
    if gain not in (0, 1):
        raise GateError(f"invalid quotient gain {gain}")
    return {
        "candidate_positions": list(indices),
        "class_indices": [CANDIDATE_ORDER[index] for index in indices],
        "residual_rank": residual_rank,
        "residual_plus_delta_rank": augmented_rank,
        "augmented_gain": gain,
    }


def potent_vector(
    residual: np.ndarray, delta: np.ndarray, prime: int
) -> tuple[np.ndarray, dict[str, Any]]:
    field = to_nmod(residual, prime)
    rank = int(field.rank())
    kernel, nullity_object = field.nullspace()
    nullity = int(nullity_object)
    if nullity != residual.shape[1] - rank:
        raise GateError("quotient nullity drift")
    for basis_column in range(nullity):
        vector = np.fromiter(
            (int(kernel[row, basis_column]) % prime for row in range(residual.shape[1])),
            dtype=np.int64,
            count=residual.shape[1],
        )
        potency = int(np.remainder(delta @ vector, prime))
        if not potency:
            continue
        vector = np.remainder(vector * pow(potency, -1, prime), prime).astype(np.int64)
        if np.any(np.remainder(residual @ vector, prime)):
            raise GateError("potent quotient vector failed residual replay")
        if int(np.remainder(delta @ vector, prime)) != 1:
            raise GateError("potent quotient vector failed normalization")
        support = [[index, int(value)] for index, value in enumerate(vector) if value]
        return vector, {
            "quotient_rank": rank,
            "quotient_nullity": nullity,
            "kernel_basis_column_used": basis_column,
            "normalization": "delta_dot_candidate_coefficients_mod_prime_equals_one",
            "support": support,
            "support_sha256": canonical_sha256(support),
        }
    raise GateError("reported augmented gain has no potent quotient vector")


def lift_modular_circuit(
    indices: tuple[int, ...],
    residual: np.ndarray,
    delta: np.ndarray,
    schur_coefficients: np.ndarray,
    pivot_columns: list[int],
    baseline_results: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
    g0057: ModuleType,
    prime: int,
) -> dict[str, Any]:
    local_vector, quotient = potent_vector(
        np.ascontiguousarray(residual[:, indices], dtype=np.int64),
        np.ascontiguousarray(delta[list(indices)], dtype=np.int64),
        prime,
    )
    candidate_vector = np.zeros(EXPECTED_CANDIDATES, dtype=np.int64)
    candidate_vector[list(indices)] = local_vector
    baseline_pivot = np.remainder(
        -(schur_coefficients @ candidate_vector), prime
    ).astype(np.int64, copy=False)
    full_coefficients = [0] * (EXPECTED_BASELINE_COLUMNS + EXPECTED_CANDIDATES)
    for position, column in enumerate(pivot_columns):
        full_coefficients[column] = int(baseline_pivot[position])
    for position, coefficient in enumerate(candidate_vector):
        full_coefficients[EXPECTED_BASELINE_COLUMNS + position] = int(coefficient)
    replay = g0057.replay_witness(
        baseline_results + candidate_results, full_coefficients, prime
    )
    sparse_baseline = [
        [pivot_columns[position], int(value)]
        for position, value in enumerate(baseline_pivot)
        if value
    ]
    return {
        "candidate_positions": list(indices),
        "class_indices": [CANDIDATE_ORDER[index] for index in indices],
        "quotient_witness": quotient,
        "candidate_coefficients": candidate_vector.astype(int).tolist(),
        "candidate_coefficients_sha256": canonical_sha256(
            candidate_vector.astype(int).tolist()
        ),
        "baseline_pivot_sparse_coefficients": sparse_baseline,
        "baseline_pivot_sparse_coefficients_sha256": canonical_sha256(sparse_baseline),
        "complete_modular_replay": replay,
    }


def analyze_prime(
    prime: int,
    profile: dict[str, Any],
    baseline_union_rows: np.ndarray,
    baseline_matrix: np.ndarray,
    lambda_row: np.ndarray,
    combined_rows: np.ndarray,
    baseline_positions: np.ndarray,
    candidate_matrix: np.ndarray,
    baseline_results: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
    g0057: ModuleType,
) -> dict[str, Any]:
    started = time.perf_counter()
    if int(profile["prime"]) != prime or int(profile["rank"]) != EXPECTED_BASELINE_RANK:
        raise GateError(f"frozen rank profile drift at {prime}")
    columns = list(map(int, profile["pivot_columns"]))
    row_positions = list(map(int, profile["pivot_union_row_positions"]))
    if len(columns) != EXPECTED_BASELINE_RANK or len(row_positions) != EXPECTED_BASELINE_RANK:
        raise GateError("pivot minor census drift")
    complete_pivot_rows = baseline_union_rows[row_positions].astype(np.uint32, copy=False)
    minor = np.ascontiguousarray(
        baseline_matrix[np.ix_(row_positions, columns)], dtype=np.int64
    )
    minor_field = to_nmod(minor, prime)
    determinant = int(minor_field.det())
    if not determinant:
        raise GateError(f"singular frozen pivot minor at {prime}")

    lambda_c = np.remainder(lambda_row[columns], prime).astype(np.int64, copy=False)
    dual_field = minor_field.transpose().solve(to_nmod(lambda_c.reshape(-1, 1), prime))
    dual = from_nmod(dual_field).reshape(-1)
    baseline_on_rows = np.ascontiguousarray(baseline_matrix[row_positions, :], dtype=np.int64)
    dual_replay = from_nmod(
        to_nmod(dual.reshape(1, -1), prime) * to_nmod(baseline_on_rows, prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_replay - lambda_row, prime)):
        raise GateError(f"baseline dual replay failed at {prime}")

    complete_to_combined = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    complete_to_combined[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    pivot_combined_positions = complete_to_combined[complete_pivot_rows]
    if np.any(pivot_combined_positions < 0):
        raise GateError("pivot row escaped combined union")
    candidate_on_rows = np.ascontiguousarray(
        candidate_matrix[pivot_combined_positions, :], dtype=np.int64
    )
    coefficients_field = minor_field.solve(to_nmod(candidate_on_rows, prime))
    coefficients = from_nmod(coefficients_field)
    if np.any(
        np.remainder(
            from_nmod(minor_field * coefficients_field) - candidate_on_rows, prime
        )
    ):
        raise GateError(f"B inverse candidate solve failed at {prime}")

    basis_columns = np.ascontiguousarray(baseline_matrix[:, columns], dtype=np.int64)
    predicted_baseline = from_nmod(to_nmod(basis_columns, prime) * coefficients_field)
    predicted = np.zeros_like(candidate_matrix)
    predicted[baseline_positions, :] = predicted_baseline
    residual = np.remainder(candidate_matrix - predicted, prime).astype(np.int64, copy=False)
    if np.any(residual[pivot_combined_positions, :]):
        raise GateError(f"Schur residual nonzero on pivot rows at {prime}")

    candidate_lambda = np.array(
        [int(result["lambda"]) for result in candidate_results], dtype=np.int64
    )
    dual_prices = np.remainder(
        dual @ np.remainder(candidate_on_rows, prime), prime
    ).astype(np.int64, copy=False)
    delta = np.remainder(candidate_lambda - dual_prices, prime).astype(np.int64, copy=False)
    formula_replay = np.remainder(
        candidate_lambda - np.remainder(lambda_c @ coefficients, prime), prime
    )
    if np.any(np.remainder(delta - formula_replay, prime)):
        raise GateError(f"nonzero-candidate-Lambda Schur formula failed at {prime}")

    subset_records = []
    circuits = []
    for mask in range(1, 1 << EXPECTED_CANDIDATES):
        indices = tuple(index for index in range(EXPECTED_CANDIDATES) if mask & (1 << index))
        record = subset_record(residual, delta, indices, prime)
        subset_records.append(record)
        if int(record["augmented_gain"]):
            circuits.append(
                lift_modular_circuit(
                    indices,
                    residual,
                    delta,
                    coefficients,
                    columns,
                    baseline_results,
                    candidate_results,
                    g0057,
                    prime,
                )
            )

    residual_records = []
    for index, class_index in enumerate(CANDIDATE_ORDER):
        column = residual[:, index]
        support = int(np.count_nonzero(column))
        residual_records.append(
            {
                "candidate_position": index,
                "class_index": class_index,
                "residual_support_size": support,
                "residual_sha256": uint32_sha256(column),
                "candidate_lambda_integer": int(candidate_lambda[index]),
                "candidate_lambda_mod_prime": int(candidate_lambda[index] % prime),
                "dual_price_mod_prime": int(dual_prices[index]),
                "delta_mod_prime": int(delta[index]),
                "exact_Q_nonmembership_in_baseline_if_residual_nonzero": bool(support),
            }
        )

    result = {
        "prime": prime,
        "baseline_rank": int(profile["rank"]),
        "baseline_nullity": int(profile["nullity"]),
        "pivot_minor": {
            "rank": len(columns),
            "determinant_mod_prime": determinant,
            "pivot_columns_sha256": canonical_sha256(columns),
            "pivot_complete_rows_sha256": canonical_sha256(
                complete_pivot_rows.astype(int).tolist()
            ),
            "minor_int64_sha256": int64_sha256(minor),
        },
        "candidate_schur_coefficients": {
            "shape": list(coefficients.shape),
            "candidate_major_mod_prime": coefficients.T.astype(int).tolist(),
            "candidate_major_sha256": canonical_sha256(
                coefficients.T.astype(int).tolist()
            ),
        },
        "residual_columns": residual_records,
        "all_nonempty_candidate_subsets": subset_records,
        "replayed_potent_modular_circuits": circuits,
        "all_residuals_zero_on_pivot_rows": True,
        "all_1358_baseline_dual_values_replayed": True,
        "delta_formula_includes_candidate_lambda": True,
        "seconds": time.perf_counter() - started,
    }
    del basis_columns, predicted_baseline, predicted, residual, minor_field
    gc.collect()
    return result


def synthetic_schur_control() -> dict[str, Any]:
    prime = 101
    baseline = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.int64)
    baseline_lambda = np.array([2, 3], dtype=np.int64)
    coefficients = np.array([[4, 7, 0], [5, 11, 0]], dtype=np.int64)
    candidates = baseline @ coefficients
    candidates[:, 2] = np.array([0, 0, 1])
    candidate_lambda = np.array([24, 47, 9], dtype=np.int64)
    residual = np.remainder(candidates - baseline @ coefficients, prime)
    price = np.remainder(baseline_lambda @ coefficients, prime)
    delta = np.remainder(candidate_lambda - price, prime)
    first = subset_record(residual, delta, (0,), prime)
    second = subset_record(residual, delta, (1,), prime)
    third = subset_record(residual, delta, (2,), prime)
    if (
        first["augmented_gain"] != 1
        or second["augmented_gain"] != 0
        or third["augmented_gain"] != 0
        or list(delta) != [1, 0, 9]
    ):
        raise GateError("synthetic nonzero-candidate-Lambda Schur control failed")
    old_zero_lambda_formula = np.remainder(-price, prime)
    if int(old_zero_lambda_formula[1]) == 0:
        raise GateError("synthetic control failed to reject the old zero-Lambda formula")
    return {
        "correct_delta": delta.astype(int).tolist(),
        "old_zero_lambda_delta": old_zero_lambda_formula.astype(int).tolist(),
        "decisive_span_member_detected": first,
        "nonpotent_span_member_detected": second,
        "nonspan_column_not_misclassified": third,
        "old_G0059_zero_candidate_lambda_formula_rejected": True,
        "passed": True,
    }


def load_upstreams() -> tuple[
    dict[str, Any], dict[str, Any], dict[str, Any], ModuleType, ModuleType, ModuleType, ModuleType
]:
    direct = input_bindings()
    g0061 = import_bound("g0069_g0061", G0061_SCRIPT, direct["g0061_script_sha256"])
    inherited, g0057_report, g0059_report, g0057 = g0061.checked_bindings()
    g0061_report = g0061.load_json_gz(G0061_REPORT)
    if int(g0061_report["exact_rank_certificate"]["exact_rank_Q"]) != EXPECTED_BASELINE_RANK:
        raise GateError("G-0061 exact rank certificate drift")
    g0049 = import_bound("g0069_g0049", G0049_SCRIPT, direct["g0049_script_sha256"])
    charge_tools = import_bound("g0069_g0060", G0060_SCRIPT, direct["g0060_script_sha256"])
    g0059 = import_bound(
        "g0069_g0059", g0061.G0059_SCRIPT, g0061.EXPECTED_HASHES["g0059_script_sha256"]
    )
    return (
        {**direct, "inherited_g0061_bindings": inherited},
        g0057_report,
        g0059_report,
        g0057,
        g0059,
        g0049,
        charge_tools,
    )


def run(workers: int, minimum_available_gib: float) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    (
        bindings,
        g0057_report,
        g0059_report,
        g0057,
        g0059,
        g0049,
        charge_tools,
    ) = load_upstreams()
    preflight = g0057.resource_preflight(minimum_available_gib)
    synthetic = synthetic_schur_control()
    g0061 = sys.modules["g0069_g0061"]
    (
        universe,
        baseline_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        baseline_controls,
    ) = g0061.regenerate_semantics(g0057, g0057_report, g0059_report, workers)
    candidate_results, candidate_controls = generate_and_crosscheck_candidates(
        g0057, g0049, charge_tools, universe, workers
    )
    combined_rows, baseline_positions, candidate_matrix, combined_metadata = (
        g0059.build_candidate_matrix(baseline_union_rows, candidate_results)
    )
    profiles = g0059_report["baseline"]["per_prime_rank_profiles_and_preserved_nullspaces"]
    if [int(profile["prime"]) for profile in profiles] != list(PRIMES):
        raise GateError("frozen prime profile order drift")
    prime_results = [
        analyze_prime(
            prime,
            profile,
            baseline_union_rows,
            baseline_matrix,
            lambda_row,
            combined_rows,
            baseline_positions,
            candidate_matrix,
            baseline_results,
            candidate_results,
            g0057,
        )
        for prime, profile in zip(PRIMES, profiles, strict=True)
    ]

    per_class = []
    for position, class_index in enumerate(CANDIDATE_ORDER):
        records = [result["residual_columns"][position] for result in prime_results]
        singleton_gains = [
            next(
                item["augmented_gain"]
                for item in result["all_nonempty_candidate_subsets"]
                if item["candidate_positions"] == [position]
            )
            for result in prime_results
        ]
        per_class.append(
            {
                "candidate_position": position,
                "class_index": class_index,
                "residual_support_sizes": [item["residual_support_size"] for item in records],
                "deltas_mod_primes": [item["delta_mod_prime"] for item in records],
                "singleton_augmented_gains": singleton_gains,
                "exact_Q_baseline_nonmembership_certified": any(
                    int(item["residual_support_size"]) for item in records
                ),
            }
        )
    full_records = [
        next(
            item
            for item in result["all_nonempty_candidate_subsets"]
            if item["candidate_positions"] == [0, 1, 2]
        )
        for result in prime_results
    ]
    full_gains = [int(item["augmented_gain"]) for item in full_records]
    full_residual_ranks = [int(item["residual_rank"]) for item in full_records]
    exact_q_quotient_rank = (
        EXPECTED_CANDIDATES
        if max(full_residual_ranks) == EXPECTED_CANDIDATES
        else None
    )
    class7172_gains = per_class[2]["singleton_augmented_gains"]
    if exact_q_quotient_rank == EXPECTED_CANDIDATES:
        result_label = "THREE_ZERO_HIGH_ATOMS_ADD_EXACTLY_THREE_Q_HINGE_DIMENSIONS_OVER_S1"
    elif class7172_gains == [1, 1]:
        result_label = "CLASS7172_HAS_REPLAYED_POTENT_SINGLETON_CIRCUIT_AT_BOTH_PRIMES"
    elif full_gains == [1, 1]:
        result_label = "THREE_ZERO_HIGH_ATOMS_HAVE_REPLAYED_JOINT_CIRCUIT_AT_BOTH_PRIMES"
    else:
        result_label = "MIXED_ZERO_HIGH_S1_QUOTIENT_OUTCOME"

    after = input_bindings()
    if bindings | {} and {key: value for key, value in bindings.items() if key in after} != after:
        raise GateError("direct inputs changed during execution")
    if sha256_path(Path(__file__)) != script_hash_before:
        raise GateError("script changed during execution")
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": result_label,
        "bindings": bindings,
        "baseline": {
            "column_count": EXPECTED_BASELINE_COLUMNS,
            "exact_rank_Q": EXPECTED_BASELINE_RANK,
            "complete_degree4_rows": EXPECTED_ROWS,
            "regeneration_controls": baseline_controls,
        },
        "candidate_semantics": {
            **candidate_controls,
            "combined_union": combined_metadata,
        },
        "prime_results": prime_results,
        "cross_prime_summary": {
            "per_class": per_class,
            "full_three_candidate_augmented_gains": full_gains,
            "full_three_candidate_residual_ranks": full_residual_ranks,
            "two_prime_potent_circuit_agreement_would_require_exact_Q_lifting": True,
        },
        "exact_Q_rank_bridge": {
            "baseline_exact_rank_Q": EXPECTED_BASELINE_RANK,
            "full_candidate_quotient_rank_mod_each_prime": full_residual_ranks,
            "combined_rank_mod_each_prime": [
                EXPECTED_BASELINE_RANK + rank for rank in full_residual_ranks
            ],
            "combined_rank_Q_lower_bound_from_nonzero_modular_minor": (
                EXPECTED_BASELINE_RANK + exact_q_quotient_rank
                if exact_q_quotient_rank is not None
                else None
            ),
            "combined_rank_Q_upper_bound_from_baseline_plus_three_columns": (
                EXPECTED_BASELINE_RANK + EXPECTED_CANDIDATES
            ),
            "exact_combined_rank_Q": (
                EXPECTED_BASELINE_RANK + exact_q_quotient_rank
                if exact_q_quotient_rank is not None
                else None
            ),
            "exact_candidate_quotient_rank_Q": exact_q_quotient_rank,
            "the_three_candidates_are_Q_linearly_independent_modulo_S1": (
                exact_q_quotient_rank == EXPECTED_CANDIDATES
            ),
        },
        "controls": {
            "resource_preflight": preflight,
            "synthetic_nonzero_candidate_lambda_schur_control": synthetic,
        },
        "mandatory_next_gate": (
            "If any modular gain survives both primes, lift its aligned coefficients over Q, "
            "replay all 99,858 hinge rows exactly, correct the complete 11-coordinate linear "
            "normal form with F1 through F10, and independently replay the compiled network. "
            "If no singleton gains, test the exhaustive zero-high block jointly because "
            "charge-zero residual columns may cancel the charged residual."
        ),
        "claim_boundary": [
            "A nonzero singleton residual at either nonsingular frozen prime certifies that candidate is not in the exact-Q S1 hinge span.",
            "Residual quotient rank three modulo either good prime, together with exact baseline rank 1288 and the trivial three-column upper bound, certifies exact combined rank 1291 over Q.",
            "A zero residual and nonzero delta gives only a replayed finite-field potent circuit until exact-Q lifting succeeds.",
            "A nonzero delta is irrelevant when the corresponding Schur residual is nonzero.",
            "The three-column outcome does not cover the exhaustive zero-high family, all mass-five atoms, asymmetric atoms, or unrestricted two-hidden-layer networks.",
            "Even an exact potent hinge circuit still needs its linear chamber vector corrected and the final MAX11 network identity independently replayed.",
        ],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "timing": {"wall_seconds": time.perf_counter() - started},
        "script_sha256": script_hash_before,
    }
    scientific = deterministic_view(
        {key: value for key, value in report.items() if key not in {"script_sha256"}}
    )
    report["canonical_scientific_payload_sha256"] = canonical_sha256(scientific)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen output: {path}")
    if path.resolve().parent != HERE.resolve():
        raise GateError("output must be a direct G-0069 child")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial output exists: {partial}")
    with partial.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(canonical_bytes(value))
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--minimum-available-gib", type=float, default=20.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be in [1,16]")
    if args.minimum_available_gib <= 0:
        parser.error("--minimum-available-gib must be positive")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        print(json.dumps(synthetic_schur_control(), sort_keys=True))
        return 0
    if args.preflight_only:
        bindings, _g0057_report, _g0059_report, g0057, _g0059, g0049, charge = load_upstreams()
        _pairs, descriptors = reconstruct_candidates(g0049, charge)
        print(
            json.dumps(
                {
                    "result": "PASS",
                    "bindings": bindings,
                    "resource_preflight": g0057.resource_preflight(args.minimum_available_gib),
                    "candidate_descriptors": descriptors,
                },
                sort_keys=True,
            )
        )
        return 0
    report = run(args.workers, args.minimum_available_gib)
    if not args.no_write:
        write_gzip_atomic(args.output, report)
    print(
        json.dumps(
            {
                "result": report["result"],
                "output": None if args.no_write else str(args.output),
                "wall_seconds": report["timing"]["wall_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
