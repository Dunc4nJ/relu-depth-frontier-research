#!/usr/bin/env python3
"""Exact-semantics two-prime rank gate on the 3,465 support-eight rows.

Stage S0 contains the 1,465 frozen full-core mass-four columns.  Stage S0+C
appends the lex-first proper support-eight counterexample, G-0038 sequence
92,489.  Every S0 column is reconstructed with the committed clean-room DP;
lambda is recomputed directly from binary chamber evaluations.  At each prime
the verifier extracts a nonzero minor and a complete replayed right-kernel
basis.  Lambda is paired with that basis explicitly, and any gain produces a
normalized modular circuit witness.

No-claim: a modular circuit is a lifting candidate, not an exact-Q circuit.
No stage here contains every proper mass-four column.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import importlib.util
import io
from itertools import combinations
import json
from math import comb, factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Sequence

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
G0054_SCRIPT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py"
G0054_REPORT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate_v1.json.gz"
G0056_SCRIPT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift.py"
G0056_REPORT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift_v1.json.gz"
FILTRATION_SCRIPT = HERE / "support8_proper_filtration.py"
FILTRATION_REPORT = HERE / "support8_proper_filtration_v1.json.gz"
CLEAN_SCRIPT = ROOT / (
    "artifacts/cleanroom/G-0051-mass4-preflight-audit/"
    "independent_mass4_preflight_audit.py"
)
DEFAULT_OUTPUT = HERE / "support8_rank_gate_v1.json.gz"

EXPECTED_HASHES = {
    "g0038_stream": "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    "g0052_report": "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37",
    "g0054_script": "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2",
    "g0054_report": "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053",
    "g0056_script": "484d86ccc494019c802f3f793c8f40c4deda2e7e86913191888a2188fef527c7",
    "g0056_report": "131312761477dc3ae47167caa83aabdde1d7dc6da40b71e33c40c8b5401088d4",
    "filtration_script": "0de659ebef2dea44bc07c3c5f2fbb5f50c7d50338534bdc0e686d087bd120629",
    "filtration_report": "90d801abeb6820a27fe8f181dc35b0cf06ac23dac6a98c2d2bc2548db3397d2f",
    "clean_script": "76c67f4499228fd07b3cdea782bf6fe7b351fe333948062484aa8285c9cdc616",
}
EXPECTED_H8_ROWS = 3_465
EXPECTED_H8_DIRECTIONS_SHA256 = (
    "725ae43e7038199499952d98a454031210e3bcb9da1ccc9076216bf1bf71e572"
)
EXPECTED_S0_COLUMNS = 1_465
EXPECTED_FULL_SEQUENCE_FIRST = 136_039
EXPECTED_FULL_SEQUENCE_LAST = 137_503
COUNTEREXAMPLE_SEQUENCE = 92_489
COUNTEREXAMPLE_AMBIENT_COEFFICIENT = 6_912
PRIMES = (1_000_003, 1_000_033)
SCHEMA = "max11-g0058-support8-rank-gate-v1"

Direction = tuple[int, ...]

CLEAN: ModuleType | None = None
H8_INDEX: dict[Direction, int] = {}


class GateError(RuntimeError):
    """Fail-closed semantic or certificate mismatch."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        result = json.load(source)
    if not isinstance(result, dict):
        raise GateError(f"expected JSON object: {path}")
    return result


def verify_canonical_payload(document: dict[str, object], label: str) -> None:
    copy = dict(document)
    claimed = copy.pop("canonical_payload_sha256", None)
    observed = canonical_sha256(copy)
    if claimed != observed:
        raise GateError(f"{label} canonical payload mismatch: {claimed}/{observed}")


def load_clean() -> ModuleType:
    if sha256_path(CLEAN_SCRIPT) != EXPECTED_HASHES["clean_script"]:
        raise GateError("clean-room semantic kernel hash drift")
    spec = importlib.util.spec_from_file_location("g0058_rank_clean", CLEAN_SCRIPT)
    if spec is None or spec.loader is None:
        raise GateError("cannot load clean-room semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def falling_factorial(total: int, chosen: int) -> int:
    if not 0 <= chosen <= total:
        return 0
    return factorial(total) // factorial(total - chosen)


def independent_lambda_invariant(record: dict[str, object], n: int = 11) -> int:
    raw_branches = [record.get("negative_edges"), record.get("positive_edges")]
    if not all(isinstance(branch, list) for branch in raw_branches):
        raise GateError("lambda input has malformed branches")
    used = sorted(
        {
            int(vertex)
            for branch in raw_branches
            for edge in branch  # type: ignore[union-attr]
            for vertex in edge
        }
    )
    relabel = {vertex: index for index, vertex in enumerate(used)}
    branches = [
        [
            (relabel[int(left)], relabel[int(right)])
            for left, right in branch  # type: ignore[union-attr]
        ]
        for branch in raw_branches
    ]
    active = len(used)
    binary_values = [0]
    for top_count in range(1, n + 1):
        total = 0
        for mask in range(1 << active):
            active_top = mask.bit_count()
            multiplicity = (
                falling_factorial(top_count, active_top)
                * falling_factorial(n - top_count, active - active_top)
                * factorial(n - active)
            )
            if not multiplicity:
                continue
            branch_values = [
                sum(max((mask >> left) & 1, (mask >> right) & 1) for left, right in branch)
                for branch in branches
            ]
            total += multiplicity * max(branch_values)
        binary_values.append(total)
    coefficients = [0] * n
    for top_count in range(1, n + 1):
        coefficients[n - top_count] = binary_values[top_count] - binary_values[top_count - 1]
    witness = [
        (-1) ** (n - rank) * comb(n - 1, rank - 1)
        for rank in range(1, n + 1)
    ]
    return sum(left * right for left, right in zip(witness, coefficients, strict=True))


def compact_record(record: dict[str, object]) -> tuple[dict[str, object], int]:
    raw_branches = [record.get("negative_edges"), record.get("positive_edges")]
    if not all(isinstance(branch, list) for branch in raw_branches):
        raise GateError("record has malformed branches")
    used = sorted(
        {
            int(vertex)
            for branch in raw_branches
            for edge in branch  # type: ignore[union-attr]
            for vertex in edge
        }
    )
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact = {
        "negative_edges": [
            [relabel[int(left)], relabel[int(right)]]
            for left, right in raw_branches[0]  # type: ignore[union-attr]
        ],
        "positive_edges": [
            [relabel[int(left)], relabel[int(right)]]
            for left, right in raw_branches[1]  # type: ignore[union-attr]
        ],
    }
    return compact, len(used)


def initialize_worker(h8_index: dict[Direction, int]) -> None:
    global CLEAN, H8_INDEX
    CLEAN = load_clean()
    H8_INDEX = h8_index


def s0_worker(record: dict[str, object]) -> dict[str, object]:
    if CLEAN is None:
        raise GateError("clean-room worker was not initialized")
    hinges = +CLEAN.independent_hinge_column(record, n=11)
    full_payload = CLEAN.hinge_payload(hinges)
    sparse = sorted(
        (H8_INDEX[direction], int(value))
        for direction, value in hinges.items()
        if value and direction in H8_INDEX
    )
    return {
        "sequence": int(record["sequence"]),
        "rows": np.fromiter((row for row, _value in sparse), dtype=np.int32),
        "values": np.fromiter((value for _row, value in sparse), dtype=np.int64),
        "complete_support_size": len(full_payload),
        "complete_total_absolute_weight": sum(abs(int(item[1])) for item in full_payload),
        "complete_fingerprint_sha256": canonical_sha256(full_payload),
    }


def read_records() -> tuple[list[dict[str, object]], dict[str, object]]:
    full: list[dict[str, object]] = []
    counterexample: dict[str, object] | None = None
    with gzip.open(STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise GateError("G-0038 stream is missing its header")
        for line in source:
            record = json.loads(line)
            mass = int(record["signed_mass"])
            if mass < 4:
                continue
            if mass > 4:
                break
            sequence = int(record["sequence"])
            if sequence == COUNTEREXAMPLE_SEQUENCE:
                counterexample = record
            if int(record["active_vertices"]) == 11:
                full.append(record)
    sequences = [int(record["sequence"]) for record in full]
    if sequences != list(range(EXPECTED_FULL_SEQUENCE_FIRST, EXPECTED_FULL_SEQUENCE_LAST + 1)):
        raise GateError("full-core sequence interval drift")
    if counterexample is None:
        raise GateError("sequence 92489 is absent from the frozen stream")
    return full, counterexample


def embed_proper_H8_column(
    clean: ModuleType,
    record: dict[str, object],
    h8_index: dict[Direction, int],
) -> np.ndarray:
    compact, active = compact_record(record)
    hinges = clean.independent_hinge_column(compact, n=active)
    column = np.zeros(len(h8_index), dtype=np.int64)
    multiplier = factorial(11 - active)
    for positions in combinations(range(11), active):
        for local_direction, coefficient in hinges.items():
            if not coefficient or sum(value != 0 for value in local_direction) != 8:
                continue
            embedded = [0] * 11
            for local, ambient in enumerate(positions):
                embedded[ambient] = local_direction[local]
            row = h8_index.get(tuple(embedded))
            if row is None:
                raise GateError("proper support-8 hinge escaped the H8 universe")
            column[row] += multiplier * int(coefficient)
    return column


def hash_integer_matrix(matrix: np.ndarray, label: str) -> str:
    encoded = matrix.astype("<i8", copy=False)
    digest = hashlib.sha256()
    digest.update(
        f"{label};int64-little-row-major;shape={matrix.shape[0]}x{matrix.shape[1]}\n".encode()
    )
    digest.update(encoded.tobytes(order="C"))
    return digest.hexdigest()


def hash_modular_matrix(matrix: np.ndarray, prime: int, label: str) -> str:
    encoded = np.remainder(matrix, prime).astype("<u4", copy=False)
    digest = hashlib.sha256()
    digest.update(
        (
            f"{label};uint32-little-row-major;shape={matrix.shape[0]}x"
            f"{matrix.shape[1]};prime={prime}\n"
        ).encode()
    )
    digest.update(encoded.tobytes(order="C"))
    return digest.hexdigest()


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.remainder(matrix, prime).astype(np.int64, copy=False)
    flat = reduced.ravel(order="C").tolist()
    result = nmod_mat(matrix.shape[0], matrix.shape[1], flat, prime)
    del flat, reduced
    return result


def pivot_columns_from_rref(rref_matrix: nmod_mat, rank: int) -> list[int]:
    pivots = []
    previous = -1
    for row in range(rank):
        pivot = next(
            (
                column
                for column in range(previous + 1, rref_matrix.ncols())
                if int(rref_matrix[row, column])
            ),
            None,
        )
        if pivot is None:
            raise GateError(f"RREF row {row} lacks an increasing pivot")
        pivots.append(pivot)
        previous = pivot
    return pivots


def minor_certificate(
    matrix: np.ndarray, field: nmod_mat, prime: int, rank: int, namespace: str
) -> dict[str, object]:
    transpose_rref, transpose_rank = field.transpose().rref()
    if int(transpose_rank) != rank:
        raise GateError("transpose rank drift during minor extraction")
    pivot_rows = pivot_columns_from_rref(transpose_rref, rank)
    row_rref, row_rank = field.rref()
    if int(row_rank) != rank:
        raise GateError("row rank drift during minor extraction")
    pivot_columns = pivot_columns_from_rref(row_rref, rank)
    minor = matrix[np.ix_(pivot_rows, pivot_columns)]
    determinant = int(to_nmod(minor, prime).det()) % prime
    if not determinant:
        raise GateError("selected modular rank minor is singular")
    return {
        "kind": "explicit_nonzero_modular_minor",
        "namespace": namespace,
        "rank": rank,
        "pivot_H8_rows": pivot_rows,
        "pivot_H8_rows_sha256": canonical_sha256(pivot_rows),
        "pivot_columns": pivot_columns,
        "pivot_columns_sha256": canonical_sha256(pivot_columns),
        "minor_matrix_sha256": hash_modular_matrix(
            minor, prime, "max11-g0058-H8-rank-minor-v1"
        ),
        "minor_determinant_mod_prime": determinant,
        "minor_determinant_nonzero": True,
    }


def kernel_certificate(
    matrix: np.ndarray,
    field: nmod_mat,
    lambda_row: np.ndarray,
    prime: int,
    rank: int,
) -> tuple[dict[str, object], dict[str, object] | None]:
    kernel, raw_nullity = field.nullspace()
    nullity = int(raw_nullity)
    if nullity != matrix.shape[1] - rank:
        raise GateError("nullity disagrees with rank")
    coefficient_rows = [
        [int(kernel[row, column]) for column in range(nullity)]
        for row in range(matrix.shape[1])
    ]
    basis_field = nmod_mat(
        matrix.shape[1], nullity, sum(coefficient_rows, []), prime
    )
    residual = field * basis_field
    if residual != nmod_mat(matrix.shape[0], nullity, prime):
        raise GateError("explicit modular kernel replay failed")
    sparse_basis = []
    for basis_column in range(nullity):
        support = [
            row
            for row in range(matrix.shape[1])
            if coefficient_rows[row][basis_column]
        ]
        sparse_basis.append(
            {
                "support_zero_based_columns": support,
                "coefficients": [
                    coefficient_rows[row][basis_column] for row in support
                ],
            }
        )
    identity_rows = []
    for basis_column in range(nullity):
        candidate = next(
            (
                row
                for row, coefficients in enumerate(coefficient_rows)
                if coefficients[basis_column]
                and sum(bool(value) for value in coefficients) == 1
            ),
            None,
        )
        if candidate is None:
            raise GateError(f"kernel basis {basis_column} lacks a unique coordinate")
        identity_rows.append(candidate)
    if len(set(identity_rows)) != nullity:
        raise GateError("kernel unique-coordinate certificate is not injective")

    lambda_pairings = []
    for basis_column in range(nullity):
        pairing = sum(
            int(lambda_row[row] % prime) * coefficient_rows[row][basis_column]
            for row in range(matrix.shape[1])
        ) % prime
        lambda_pairings.append(pairing)
    nonzero_pairings = [
        index for index, pairing in enumerate(lambda_pairings) if pairing
    ]
    witness = None
    if nonzero_pairings:
        chosen = nonzero_pairings[0]
        scale = pow(lambda_pairings[chosen], -1, prime)
        coefficients = np.array(
            [coefficient_rows[row][chosen] * scale % prime for row in range(matrix.shape[1])],
            dtype=np.int64,
        )
        modular_residual = np.remainder(
            np.remainder(matrix, prime) @ coefficients,
            prime,
        )
        if np.count_nonzero(modular_residual):
            raise GateError("normalized modular witness matrix replay failed")
        pairing = sum(
            int(lambda_row[row] % prime) * int(coefficients[row])
            for row in range(matrix.shape[1])
        ) % prime
        if pairing != 1:
            raise GateError("normalized modular witness lambda pairing drift")
        support = np.flatnonzero(coefficients)
        witness = {
            "kind": "explicit_normalized_modular_H8_circuit",
            "normalized_lambda_pairing": pairing,
            "complete_3465_row_replay_zero": True,
            "support_zero_based_columns": [int(row) for row in support],
            "coefficients": [int(coefficients[row]) for row in support],
        }

    certificate = {
        "kind": "complete_replayed_modular_right_kernel",
        "nullity": nullity,
        "basis_vector_count": len(sparse_basis),
        "total_sparse_entries": sum(
            len(item["support_zero_based_columns"]) for item in sparse_basis
        ),
        "basis_columns": sparse_basis,
        "basis_columns_sha256": canonical_sha256(sparse_basis),
        "unique_coordinate_rows_sha256": canonical_sha256(identity_rows),
        "basis_independent_by_unique_coordinates": True,
        "complete_H8_matrix_times_basis_is_zero": True,
        "lambda_pairings_sha256": canonical_sha256(lambda_pairings),
        "nonzero_lambda_pairing_count": len(nonzero_pairings),
        "lambda_annihilates_complete_kernel": not nonzero_pairings,
    }
    return certificate, witness


def certify_stage(
    matrix: np.ndarray, lambda_row: np.ndarray, prime: int, stage: str
) -> dict[str, object]:
    started = time.perf_counter()
    field = to_nmod(matrix, prime)
    rank = int(field.rank())
    lower = minor_certificate(matrix, field, prime, rank, stage)
    upper, witness = kernel_certificate(matrix, field, lambda_row, prime, rank)
    augmented_rank = rank + int(witness is not None)
    direct_augmented_rank = int(to_nmod(np.vstack((matrix, lambda_row)), prime).rank())
    if direct_augmented_rank != augmented_rank:
        raise GateError(
            f"{stage} p={prime}: direct/certificate augmented rank mismatch"
        )
    return {
        "stage": stage,
        "prime": prime,
        "matrix_shape": list(matrix.shape),
        "hinge_rank": rank,
        "augmented_rank": augmented_rank,
        "augmented_rank_gain": augmented_rank - rank,
        "matrix_mod_prime_sha256": hash_modular_matrix(
            matrix, prime, f"max11-g0058-{stage}-H8-v1"
        ),
        "rank_lower_certificate": lower,
        "rank_upper_certificate": upper,
        "lambda_nonzero_circuit": witness,
        "wall_seconds": time.perf_counter() - started,
    }


def self_test() -> dict[str, object]:
    prime = PRIMES[0]
    no_gain = np.array([[1, 0]], dtype=np.int64)
    no_gain_lambda = np.array([1, 0], dtype=np.int64)
    gain_lambda = np.array([0, 1], dtype=np.int64)
    no_gain_report = certify_stage(no_gain, no_gain_lambda, prime, "control-no-gain")
    gain_report = certify_stage(no_gain, gain_lambda, prime, "control-gain")
    if no_gain_report["augmented_rank_gain"] != 0:
        raise GateError("no-gain control failed")
    if gain_report["augmented_rank_gain"] != 1:
        raise GateError("gain control failed")
    witness = gain_report["lambda_nonzero_circuit"]
    if not isinstance(witness, dict) or witness["normalized_lambda_pairing"] != 1:
        raise GateError("gain witness control failed")
    return {
        "explicit_complete_kernel_no_gain_control": True,
        "explicit_normalized_lambda_circuit_gain_control": True,
        "nonzero_minor_controls": True,
    }


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    paths = {
        "g0038_stream": STREAM,
        "g0052_report": G0052_REPORT,
        "g0054_script": G0054_SCRIPT,
        "g0054_report": G0054_REPORT,
        "g0056_script": G0056_SCRIPT,
        "g0056_report": G0056_REPORT,
        "filtration_script": FILTRATION_SCRIPT,
        "filtration_report": FILTRATION_REPORT,
        "clean_script": CLEAN_SCRIPT,
    }
    observed_hashes = {name: sha256_path(path) for name, path in paths.items()}
    if observed_hashes != EXPECTED_HASHES:
        raise GateError(f"input binding drift: {observed_hashes}")
    filtration = load_json_gz(FILTRATION_REPORT)
    verify_canonical_payload(filtration, "G-0058 filtration")
    if filtration.get("result") != (
        "REFUTED_LEX_FIRST_PROPER_SUPPORT8_COUNTEREXAMPLE_SEQUENCE_92489"
    ):
        raise GateError("filtration result drift")

    clean = load_clean()
    full_universe = clean.primitive_ambiguous_directions(4, 11)
    h8_rows = sorted(
        direction
        for direction in full_universe
        if sum(value != 0 for value in direction) == 8
    )
    if len(h8_rows) != EXPECTED_H8_ROWS or canonical_sha256(
        [list(row) for row in h8_rows]
    ) != EXPECTED_H8_DIRECTIONS_SHA256:
        raise GateError("H8 row universe drift")
    h8_index = {direction: index for index, direction in enumerate(h8_rows)}
    full_records, counterexample = read_records()

    g0052 = load_json_gz(G0052_REPORT)
    verify_canonical_payload(g0052, "G-0052")
    expected_summaries = {
        int(item["sequence"]): item for item in g0052["per_record_summaries"]
    }
    lambda_values = [independent_lambda_invariant(record) for record in full_records]
    expected_lambda = [
        int(expected_summaries[int(record["sequence"])]["invariant"])
        for record in full_records
    ]
    if lambda_values != expected_lambda:
        raise GateError("independent S0 lambda vector differs entrywise from G-0052")

    matrix = np.zeros((EXPECTED_H8_ROWS, EXPECTED_S0_COLUMNS), dtype=np.int64)
    h8_support_sizes = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=initialize_worker,
        initargs=(h8_index,),
        maxtasksperchild=32,
    ) as pool:
        for column, result in enumerate(pool.imap(s0_worker, full_records, chunksize=1)):
            sequence = int(result["sequence"])
            expected = expected_summaries[sequence]
            observed_summary = (
                int(result["complete_support_size"]),
                int(result["complete_total_absolute_weight"]),
                str(result["complete_fingerprint_sha256"]),
            )
            expected_summary = (
                int(expected["hinge_support_size"]),
                int(expected["total_absolute_hinge_weight"]),
                str(expected["hinge_fingerprint_sha256"]),
            )
            if observed_summary != expected_summary:
                raise GateError(f"complete S0 semantic mismatch at sequence {sequence}")
            rows = result["rows"]
            values = result["values"]
            matrix[rows, column] = values
            h8_support_sizes.append(len(rows))
            completed = column + 1
            if completed % 100 == 0 or completed == EXPECTED_S0_COLUMNS:
                print(
                    f"G0058_H8 columns={completed}/{EXPECTED_S0_COLUMNS}",
                    file=sys.stderr,
                    flush=True,
                )

    counterexample_column = embed_proper_H8_column(clean, counterexample, h8_index)
    if not np.all(counterexample_column == COUNTEREXAMPLE_AMBIENT_COEFFICIENT):
        raise GateError("sequence 92489 is not constant 6912 on every H8 row")
    counterexample_lambda = independent_lambda_invariant(counterexample)
    if counterexample_lambda != 0:
        raise GateError("sequence 92489 lambda drift")
    appended_matrix = np.column_stack((matrix, counterexample_column))
    appended_lambda = np.append(np.array(lambda_values, dtype=np.int64), counterexample_lambda)

    zero_H8_columns = [
        int(column)
        for column in np.flatnonzero(np.count_nonzero(matrix, axis=0) == 0)
    ]
    exact_unit_candidates = [
        column for column in zero_H8_columns if int(lambda_values[column]) != 0
    ]
    if not exact_unit_candidates:
        raise GateError("modular H8 gain lacks an exact zero-column unit witness")
    exact_unit_column = exact_unit_candidates[0]
    exact_unit_sequence = int(full_records[exact_unit_column]["sequence"])
    exact_unit_lambda = int(lambda_values[exact_unit_column])
    if exact_unit_column != 0 or exact_unit_sequence != EXPECTED_FULL_SEQUENCE_FIRST:
        raise GateError("lex-first exact H8 unit witness drift")
    exact_unit_summary = expected_summaries[exact_unit_sequence]
    if int(exact_unit_summary["hinge_support_size"]) != 1_326:
        raise GateError("exact H8 unit witness complete-support countercheck drift")

    stage_results = []
    for prime in PRIMES:
        stage_results.append(
            certify_stage(matrix, np.array(lambda_values, dtype=np.int64), prime, "S0")
        )
        stage_results.append(
            certify_stage(appended_matrix, appended_lambda, prime, "S0_plus_seq92489")
        )
    rank_tuples = {
        stage: [
            [int(item["hinge_rank"]), int(item["augmented_rank"])]
            for item in stage_results
            if item["stage"] == stage
        ]
        for stage in ("S0", "S0_plus_seq92489")
    }
    if any(len(set(map(tuple, values))) != 1 for values in rank_tuples.values()):
        raise GateError("two-prime rank tuples disagree")

    for item in stage_results:
        witness = item["lambda_nonzero_circuit"]
        if not isinstance(witness, dict):
            raise GateError("certified H8 gain lacks a modular witness")
        if witness["support_zero_based_columns"] != [exact_unit_column]:
            raise GateError("modular witness does not match the exact unit witness")
        prime = int(item["prime"])
        expected_coefficient = pow(exact_unit_lambda % prime, -1, prime)
        if witness["coefficients"] != [expected_coefficient]:
            raise GateError("normalized unit-witness coefficient drift")

    result = "RESTRICTED_H8_GAIN_ALREADY_PRESENT_EXACT_UNIT_WITNESS_SEQUENCE_136039"
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": result,
        "bindings": observed_hashes,
        "controls": controls,
        "H8_semantics": {
            "row_count": len(h8_rows),
            "directions_sha256": canonical_sha256([list(row) for row in h8_rows]),
            "S0_column_count": matrix.shape[1],
            "all_complete_S0_fingerprints_match_G0052": True,
            "lambda_recomputed_and_matches_G0052_entrywise": True,
            "lambda_vector_sha256": canonical_sha256(lambda_values),
            "matrix_integer_sha256": hash_integer_matrix(matrix, "max11-g0058-S0-H8-v1"),
            "nonzero_entry_count": int(np.count_nonzero(matrix)),
            "column_support_minimum": min(h8_support_sizes),
            "column_support_median_low": sorted(h8_support_sizes)[
                (len(h8_support_sizes) - 1) // 2
            ],
            "column_support_maximum": max(h8_support_sizes),
        },
        "counterexample_append": {
            "sequence": COUNTEREXAMPLE_SEQUENCE,
            "column_is_constant_on_all_3465_rows": True,
            "constant_integer_coefficient": COUNTEREXAMPLE_AMBIENT_COEFFICIENT,
            "column_sha256": canonical_sha256(counterexample_column.tolist()),
            "lambda": counterexample_lambda,
            "appended_matrix_integer_sha256": hash_integer_matrix(
                appended_matrix, "max11-g0058-S0-plus-seq92489-H8-v1"
            ),
        },
        "exact_H8_unit_circuit": {
            "kind": "exact_integer_unit_vector_on_restricted_H8_matrix",
            "zero_based_S0_column": exact_unit_column,
            "sequence": exact_unit_sequence,
            "coefficient": 1,
            "all_3465_H8_residuals_exactly_zero": True,
            "lambda_pairing": exact_unit_lambda,
            "lambda_pairing_nonzero": True,
            "zero_H8_column_count_in_S0": len(zero_H8_columns),
            "zero_H8_nonzero_lambda_unit_candidate_count": len(exact_unit_candidates),
            "candidate_zero_based_columns": exact_unit_candidates,
            "candidate_sequences": [
                int(full_records[column]["sequence"])
                for column in exact_unit_candidates
            ],
            "full_degree4_hinge_support_size": int(
                exact_unit_summary["hinge_support_size"]
            ),
            "full_degree4_hinge_fingerprint_sha256": str(
                exact_unit_summary["hinge_fingerprint_sha256"]
            ),
            "complete_99858_row_replay_zero": False,
            "complete_99858_row_nonzero_residual_count": int(
                exact_unit_summary["hinge_support_size"]
            ),
            "not_a_complete_hinge_circuit": True,
        },
        "modular_stage_results": stage_results,
        "two_prime_rank_tuples": rank_tuples,
        "exact_bounded_conclusion": (
            "Restricted-H8 gain was already present in S0: the unit vector on sequence "
            "136039 is exactly zero on all 3465 H8 rows and pairs to lambda=79833600. "
            "It fails the complete 99858-row replay on 1326 hinge rows."
        ),
        "claim_boundary": (
            "The exact unit circuit and rank certificates concern only the 3465 "
            "support-eight rows. Sequence 136039 has 1326 nonzero hinges in the complete "
            "degree-four matrix, so this is not a full hinge-cancelling circuit or a MAX11 "
            "construction. No stage includes all 132728 proper mass-four columns. The "
            "reported rank integers remain finite-field ranks, not exact-Q ranks."
        ),
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "workers": workers,
        },
        "wall_seconds": time.perf_counter() - started,
        "script_sha256": script_hash_before,
    }
    scientific_payload = {
        key: report[key]
        for key in (
            "schema",
            "result",
            "bindings",
            "controls",
            "H8_semantics",
            "counterexample_append",
            "exact_H8_unit_circuit",
            "modular_stage_results",
            "two_prime_rank_tuples",
            "exact_bounded_conclusion",
            "claim_boundary",
        )
    }
    report["canonical_scientific_payload_sha256"] = canonical_sha256(
        scientific_payload
    )
    report["canonical_payload_sha256"] = canonical_sha256(report)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise GateError("script changed during execution")
    return report


def write_gzip_atomic(path: Path, value: object, replace: bool) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise GateError("output must remain inside project") from error
    if resolved.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite {resolved}; pass --replace")
    temporary = resolved.with_name(resolved.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="ascii") as target:
                target.write(canonical_bytes(value).decode("ascii"))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(resolved)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.self_test:
        print(json.dumps({"result": "PASS", "controls": self_test()}, sort_keys=True))
        return
    report = run(args.workers)
    write_gzip_atomic(args.output, report, args.replace)
    print(json.dumps({"result": report["result"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
