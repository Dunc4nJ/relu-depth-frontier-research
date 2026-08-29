#!/usr/bin/env python3
"""Independent certificate audit and exact lift for the G-0054 S0 rank result.

The subject's FLINT rank calls are not rerun.  Instead this verifier imports
the previously committed clean-room semantic kernel, reconstructs all 1,465
columns from the raw G-0038 stream, checks the reported 867x867 minors with a
separate NumPy modular determinant, and replays every one of the 598 sparse
nullspace vectors on every complete degree-four row.  It then CRT-lifts all
598 vectors, rationally reconstructs and primitive-integral normalizes their
coefficients, and replays every lifted relation exactly over Z on both H and
lambda.  Nullspace independence is checked by explicit unique coordinates.

The resulting exact conclusion is bounded to the frozen 1,465-column S0
experiment.  It is not a mass-four-wide or unrestricted MAX11 result.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import importlib.util
import json
from math import comb, factorial, gcd, isqrt, lcm
import multiprocessing as mp
import os
from pathlib import Path
import platform
from statistics import median
import sys
import time
from types import ModuleType
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SUBJECT_README = ROOT / "artifacts/math/G-0054/README.md"
SUBJECT_SCRIPT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py"
SUBJECT_REPORT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate_v1.json.gz"
CLEAN_SCRIPT = ROOT / (
    "artifacts/cleanroom/G-0051-mass4-preflight-audit/"
    "independent_mass4_preflight_audit.py"
)
CLEAN_REPORT = ROOT / (
    "artifacts/cleanroom/G-0051-mass4-preflight-audit/audit_report_v1.json"
)
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
DEFAULT_OUTPUT = HERE / "rank_audit_v1.json"

EXPECTED_HASHES = {
    "subject_readme": "4842f4d6e72200a5ef39a27cf949375004d3f0fb929162bf506b1538ac71c277",
    "subject_script": "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2",
    "subject_report": "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053",
    "clean_script": "76c67f4499228fd07b3cdea782bf6fe7b351fe333948062484aa8285c9cdc616",
    "clean_report": "0af7666d1c3d1e3259c6ecd5b67d500e29ac75e83ed0e17d3f2493638c2d1aa9",
    "g0052_report": "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37",
}

N_ROWS = 99_858
N_COLUMNS = 1_465
RANK = 867
NULLITY = 598
PRIMES = (1_000_003, 1_000_033)
SCHEMA = "max11-cleanroom-g0054-rank-audit-v1"

CLEAN: ModuleType | None = None
ROW_INDEX: dict[tuple[int, ...], int] = {}


class AuditError(RuntimeError):
    """Fail-closed certificate mismatch."""


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


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as source:
        result = json.load(source)
    if not isinstance(result, dict):
        raise AuditError(f"expected JSON object: {path}")
    return result


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        result = json.load(source)
    if not isinstance(result, dict):
        raise AuditError(f"expected gzip JSON object: {path}")
    return result


def load_clean() -> ModuleType:
    if sha256_path(CLEAN_SCRIPT) != EXPECTED_HASHES["clean_script"]:
        raise AuditError("clean-room semantic kernel hash drift")
    spec = importlib.util.spec_from_file_location("g0054_clean_semantics", CLEAN_SCRIPT)
    if spec is None or spec.loader is None:
        raise AuditError("cannot load clean-room semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_canonical_payload(document: dict[str, object], label: str) -> None:
    copy = dict(document)
    claimed = copy.pop("canonical_payload_sha256", None)
    observed = canonical_sha256(copy)
    if claimed != observed:
        raise AuditError(f"{label} canonical payload mismatch: {claimed} != {observed}")


def hash_modular_matrix(matrix: np.ndarray, prime: int, label: str) -> str:
    reduced = np.remainder(matrix, prime).astype("<u4", copy=False)
    digest = hashlib.sha256()
    digest.update(
        (
            f"{label};uint32-little-row-major;shape={matrix.shape[0]}x"
            f"{matrix.shape[1]};prime={prime}\n"
        ).encode()
    )
    digest.update(reduced.tobytes(order="C"))
    return digest.hexdigest()


def determinant_mod_numpy(matrix: np.ndarray, prime: int, block_rows: int = 128) -> int:
    """Modular Gaussian determinant using NumPy only, not FLINT."""
    if matrix.ndim != 2 or matrix.shape[0] != matrix.shape[1]:
        raise AuditError("determinant input must be square")
    value = np.remainder(matrix, prime).astype(np.int64, copy=True)
    size = value.shape[0]
    determinant = 1
    sign = 1
    for column in range(size):
        candidates = np.flatnonzero(value[column:, column])
        if not len(candidates):
            return 0
        pivot_row = column + int(candidates[0])
        if pivot_row != column:
            value[[column, pivot_row]] = value[[pivot_row, column]]
            sign = -sign
        pivot = int(value[column, column])
        determinant = (determinant * pivot) % prime
        inverse = pow(pivot, -1, prime)
        pivot_tail = value[column, column + 1 :].copy()
        for start in range(column + 1, size, block_rows):
            stop = min(size, start + block_rows)
            factors = (value[start:stop, column] * inverse) % prime
            if pivot_tail.size:
                update = factors[:, None] * pivot_tail[None, :]
                value[start:stop, column + 1 :] = (
                    value[start:stop, column + 1 :] - update
                ) % prime
            value[start:stop, column] = 0
    return determinant if sign > 0 else (-determinant) % prime


def determinant_3x3(matrix: np.ndarray, prime: int) -> int:
    a, b, c = map(int, matrix[0])
    d, e, f = map(int, matrix[1])
    g, h, i = map(int, matrix[2])
    return (a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)) % prime


def crt_pair(left: int, left_modulus: int, right: int, right_modulus: int) -> int:
    correction = ((right - left) * pow(left_modulus, -1, right_modulus)) % right_modulus
    return (left + left_modulus * correction) % (left_modulus * right_modulus)


def rational_reconstruct(residue: int, modulus: int) -> tuple[int, int]:
    """Unique |numerator|,denominator <= floor(sqrt(modulus/2)) lift."""
    bound = isqrt(modulus // 2)
    old_remainder, remainder = modulus, residue % modulus
    old_denominator, denominator = 0, 1
    while abs(remainder) > bound:
        quotient = old_remainder // remainder
        old_remainder, remainder = remainder, old_remainder - quotient * remainder
        old_denominator, denominator = denominator, old_denominator - quotient * denominator
    numerator = remainder
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    divisor = gcd(abs(numerator), denominator)
    if divisor:
        numerator //= divisor
        denominator //= divisor
    if (
        denominator <= 0
        or abs(numerator) > bound
        or denominator > bound
        or (numerator - residue * denominator) % modulus
    ):
        raise AuditError(f"rational reconstruction failed for residue {residue} mod {modulus}")
    return numerator, denominator


def independent_lambda_invariant(record: dict[str, object], n: int = 11) -> int:
    """Compute lambda directly from binary chamber evaluations of a raw core."""
    branches = [
        [tuple(map(int, edge)) for edge in record[field]]
        for field in ("negative_edges", "positive_edges")
    ]
    used = {vertex for branch in branches for edge in branch for vertex in edge}
    if used != set(range(n)):
        raise AuditError(f"lambda input is not a full {n}-vertex core")
    binary_values = [0]
    for top_count in range(1, n + 1):
        orbit_multiplicity = factorial(top_count) * factorial(n - top_count)
        total = 0
        for mask in range(1 << n):
            if mask.bit_count() != top_count:
                continue
            branch_values = [
                sum(max((mask >> left) & 1, (mask >> right) & 1) for left, right in branch)
                for branch in branches
            ]
            total += orbit_multiplicity * max(branch_values)
        binary_values.append(total)
    chamber_coefficients = [0] * n
    for top_count in range(1, n + 1):
        chamber_coefficients[n - top_count] = (
            binary_values[top_count] - binary_values[top_count - 1]
        )
    alternating_witness = [
        (-1) ** (n - rank) * comb(n - 1, rank - 1)
        for rank in range(1, n + 1)
    ]
    return sum(
        witness * coefficient
        for witness, coefficient in zip(
            alternating_witness, chamber_coefficients, strict=True
        )
    )


def self_test() -> dict[str, object]:
    prime = PRIMES[0]
    matrices = [
        np.eye(3, dtype=np.int64),
        np.array([[2, 1, 3], [1, 0, 4], [5, 2, 1]], dtype=np.int64),
        np.array([[0, 1, 0], [1, 0, 0], [0, 0, 1]], dtype=np.int64),
        np.array([[1, 2, 3], [1, 2, 3], [4, 5, 6]], dtype=np.int64),
    ]
    for matrix in matrices:
        observed = determinant_mod_numpy(matrix, prime, block_rows=2)
        expected = determinant_3x3(matrix, prime)
        if observed != expected:
            raise AuditError(f"independent determinant control mismatch: {observed}/{expected}")
    mutant = matrices[1].copy()
    original_hash = hash_modular_matrix(mutant, prime, "control")
    mutant[0, 0] += 1
    if hash_modular_matrix(mutant, prime, "control") == original_hash:
        raise AuditError("matrix-entry hash mutant was not detected")
    modulus = PRIMES[0] * PRIMES[1]
    for numerator, denominator in ((-13, 4), (-1, 2), (0, 1), (7, 2), (11, 1)):
        residues = [numerator * pow(denominator, -1, prime) % prime for prime in PRIMES]
        combined = crt_pair(residues[0], PRIMES[0], residues[1], PRIMES[1])
        if rational_reconstruct(combined, modulus) != (numerator, denominator):
            raise AuditError("CRT/rational-reconstruction control failed")
    return {
        "numpy_modular_determinant_matches_closed_3x3_formula": True,
        "row_swap_sign_detected": True,
        "duplicate_row_singularity_detected": True,
        "matrix_entry_plus_one_hash_mutant_detected": True,
        "CRT_rational_reconstruction_recovers_signed_quarters": True,
    }


def basis_data(
    modular_result: dict[str, object], prime: int
) -> tuple[list[list[tuple[int, int]]], list[list[tuple[int, int]]], dict[str, object]]:
    upper = modular_result.get("rank_upper_certificate")
    if not isinstance(upper, dict) or upper.get("kind") != "explicit_replayed_modular_nullspace_basis":
        raise AuditError(f"prime {prime}: missing explicit nullspace upper certificate")
    raw_basis = upper.get("basis_columns")
    if not isinstance(raw_basis, list) or len(raw_basis) != NULLITY:
        raise AuditError(f"prime {prime}: nullspace basis census mismatch")
    if canonical_sha256(raw_basis) != upper.get("basis_columns_sha256"):
        raise AuditError(f"prime {prime}: nullspace basis digest mismatch")

    basis: list[list[tuple[int, int]]] = []
    column_references: list[list[tuple[int, int]]] = [[] for _ in range(N_COLUMNS)]
    occurrences: dict[int, list[tuple[int, int]]] = defaultdict(list)
    total_entries = 0
    for basis_index, raw in enumerate(raw_basis):
        if not isinstance(raw, dict):
            raise AuditError(f"prime {prime}: malformed basis vector {basis_index}")
        support = raw.get("support_zero_based_columns")
        coefficients = raw.get("coefficients")
        if not isinstance(support, list) or not isinstance(coefficients, list):
            raise AuditError(f"prime {prime}: malformed sparse basis vector {basis_index}")
        if len(support) != len(coefficients) or not support:
            raise AuditError(f"prime {prime}: sparse basis vector length mismatch")
        pairs: list[tuple[int, int]] = []
        previous = -1
        for raw_column, raw_coefficient in zip(support, coefficients, strict=True):
            column = int(raw_column)
            coefficient = int(raw_coefficient) % prime
            if not (previous < column < N_COLUMNS) or coefficient == 0:
                raise AuditError(f"prime {prime}: invalid sparse basis entry")
            previous = column
            pairs.append((column, coefficient))
            column_references[column].append((basis_index, coefficient))
            occurrences[column].append((basis_index, coefficient))
        total_entries += len(pairs)
        basis.append(pairs)

    # Each basis vector must expose a distinct coordinate on which the full
    # basis restriction is exactly the identity.  This is a direct and cheap
    # independence certificate, not a solver rank assertion.
    identity_rows: list[int] = []
    for basis_index in range(NULLITY):
        candidates = [
            row
            for row, entries in occurrences.items()
            if entries == [(basis_index, 1)]
        ]
        if not candidates:
            raise AuditError(f"prime {prime}: basis vector {basis_index} lacks an identity row")
        identity_rows.append(min(candidates))
    if len(set(identity_rows)) != NULLITY:
        raise AuditError(f"prime {prime}: identity-row certificate is not injective")

    return basis, column_references, {
        "basis_sha256": upper["basis_columns_sha256"],
        "basis_vector_count": len(basis),
        "total_sparse_entries": total_entries,
        "identity_rows_sha256": canonical_sha256(identity_rows),
        "identity_rows_are_distinct": True,
        "identity_restriction_is_exact": True,
    }


def initialize_worker(row_index: dict[tuple[int, ...], int]) -> None:
    global CLEAN, ROW_INDEX
    CLEAN = load_clean()
    ROW_INDEX = row_index


def semantic_worker(record: dict[str, object]) -> dict[str, object]:
    if CLEAN is None:
        raise AuditError("worker semantic kernel is not initialized")
    hinges = CLEAN.independent_hinge_column(record)
    payload = CLEAN.hinge_payload(hinges)
    rows = np.fromiter((ROW_INDEX[tuple(item[0])] for item in payload), dtype=np.int32)
    values = np.fromiter((int(item[1]) for item in payload), dtype=np.int64)
    return {
        "sequence": int(record["sequence"]),
        "rows": rows,
        "values": values,
        "support_size": len(payload),
        "total_absolute_weight": int(np.abs(values).sum()),
        "fingerprint_sha256": canonical_sha256(payload),
    }


def sketch_map_audit(
    union_rows: np.ndarray,
    buckets: int,
    prime: int,
    seed: str,
    maximum_absolute_entry: int,
) -> dict[str, object]:
    digest = hashlib.sha256()
    digest.update(
        f"max11-g0054-countsketch-v1;seed={seed};buckets={buckets};prime={prime}\n".encode()
    )
    bucket_map = np.empty(len(union_rows), dtype=np.int32)
    for local, raw_row in enumerate(union_rows):
        row = int(raw_row)
        hashed = hashlib.sha256(f"{seed}|{row}".encode("ascii")).digest()
        bucket = int.from_bytes(hashed[:8], "little") % buckets
        weight = int.from_bytes(hashed[8:16], "little") % (prime - 1) + 1
        bucket_map[local] = bucket
        digest.update(row.to_bytes(4, "little"))
        digest.update(bucket.to_bytes(4, "little"))
        digest.update(weight.to_bytes(8, "little"))
    maximum_rows = 0
    maximum_bound = 0
    for start in range(0, len(union_rows), 256):
        stop = min(len(union_rows), start + 256)
        rows_per_bucket = int(np.bincount(bucket_map[start:stop], minlength=buckets).max())
        bound = (prime - 1) + maximum_absolute_entry * (prime - 1) * rows_per_bucket
        maximum_rows = max(maximum_rows, rows_per_bucket)
        maximum_bound = max(maximum_bound, bound)
    return {
        "map_sha256": digest.hexdigest(),
        "maximum_rows_in_one_bucket_within_a_chunk": maximum_rows,
        "worst_case_absolute_accumulator_bound_including_prior_residue": maximum_bound,
        "strictly_within_signed_int64": maximum_bound < (1 << 63),
    }


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    paths = {
        "subject_readme": SUBJECT_README,
        "subject_script": SUBJECT_SCRIPT,
        "subject_report": SUBJECT_REPORT,
        "clean_script": CLEAN_SCRIPT,
        "clean_report": CLEAN_REPORT,
        "g0052_report": G0052_REPORT,
    }
    observed_hashes = {name: sha256_path(path) for name, path in paths.items()}
    if observed_hashes != EXPECTED_HASHES:
        raise AuditError(f"input binding drift: {observed_hashes}")

    subject = load_json_gz(SUBJECT_REPORT)
    clean_report = load_json(CLEAN_REPORT)
    g0052 = load_json_gz(G0052_REPORT)
    verify_canonical_payload(subject, "G-0054")
    verify_canonical_payload(clean_report, "clean-room G-0051")
    verify_canonical_payload(g0052, "G-0052")
    if subject.get("result") != "S0_MIXED_MODULAR_OUTCOME_REQUIRES_REVIEW":
        raise AuditError("subject classification drift")
    if subject.get("exact_bounded_conclusion") is not None:
        raise AuditError("subject improperly asserts an exact bounded conclusion")

    clean = load_clean()
    universe = clean.primitive_ambiguous_directions(4, 11)
    if len(universe) != N_ROWS or canonical_sha256([list(row) for row in universe]) != (
        subject["complete_degree4_row_universe"]["directions_sha256"]
    ):
        raise AuditError("independent complete row universe mismatch")
    row_index = {direction: index for index, direction in enumerate(universe)}
    _header, records, _counts = clean.scan_stream()
    if len(records) != N_COLUMNS:
        raise AuditError("S0 record count mismatch")
    expected_summaries = {
        int(item["sequence"]): item for item in g0052["per_record_summaries"]
    }
    g0052_lambda = [
        int(expected_summaries[int(record["sequence"])]["invariant"])
        for record in records
    ]
    independently_recomputed_lambda = [
        independent_lambda_invariant(record) for record in records
    ]
    if independently_recomputed_lambda != g0052_lambda:
        mismatch = next(
            index
            for index, (observed, expected) in enumerate(
                zip(independently_recomputed_lambda, g0052_lambda, strict=True)
            )
            if observed != expected
        )
        raise AuditError(
            f"entrywise lambda mismatch at column {mismatch}: "
            f"{independently_recomputed_lambda[mismatch]} != {g0052_lambda[mismatch]}"
        )
    lambda_row = np.array(independently_recomputed_lambda, dtype=np.int64)
    if Counter(map(int, lambda_row)) != Counter(
        {int(key): int(value) for key, value in subject["exact_nonzero_row_union"]["lambda_histogram"].items()}
    ):
        raise AuditError("lambda histogram mismatch")

    modular_results = subject.get("modular_results")
    if not isinstance(modular_results, list) or [int(item["prime"]) for item in modular_results] != list(PRIMES):
        raise AuditError("modular-result prime order mismatch")
    lower_certificates = [item["rank_lower_certificate"] for item in modular_results]
    for item, prime in zip(modular_results, PRIMES, strict=True):
        if (
            int(item["complete_hinge_rank"]) != RANK
            or int(item["augmented_hinge_plus_lambda_rank"]) != RANK
            or int(item["augmented_rank_gain"]) != 0
        ):
            raise AuditError(f"prime {prime}: reported rank tuple drift")
    if lower_certificates[0]["pivot_labeled_rows"] != lower_certificates[1]["pivot_labeled_rows"]:
        raise AuditError("two primes use different lower-certificate rows")
    if lower_certificates[0]["pivot_columns"] != lower_certificates[1]["pivot_columns"]:
        raise AuditError("two primes use different lower-certificate columns")
    pivot_rows = list(map(int, lower_certificates[0]["pivot_labeled_rows"]))
    pivot_columns = list(map(int, lower_certificates[0]["pivot_columns"]))
    if len(pivot_rows) != RANK or len(set(pivot_rows)) != RANK:
        raise AuditError("lower-certificate row census mismatch")
    if len(pivot_columns) != RANK or len(set(pivot_columns)) != RANK:
        raise AuditError("lower-certificate column census mismatch")
    for certificate in lower_certificates:
        if canonical_sha256(certificate["pivot_labeled_rows"]) != certificate["pivot_labeled_rows_sha256"]:
            raise AuditError("lower-certificate row digest mismatch")
        if canonical_sha256(certificate["pivot_columns"]) != certificate["pivot_columns_sha256"]:
            raise AuditError("lower-certificate column digest mismatch")

    basis = []
    column_references = []
    basis_metadata = []
    for item, prime in zip(modular_results, PRIMES, strict=True):
        parsed, references, metadata = basis_data(item, prime)
        basis.append(parsed)
        column_references.append(references)
        basis_metadata.append(metadata)

    modulus = PRIMES[0] * PRIMES[1]
    exact_basis: list[list[tuple[int, int]]] = []
    exact_column_references: list[list[tuple[int, int]]] = [
        [] for _ in range(N_COLUMNS)
    ]
    denominator_histogram: Counter[int] = Counter()
    vector_denominator_lcm_histogram: Counter[int] = Counter()
    maximum_numerator = 0
    maximum_integer_coefficient = 0
    maximum_integer_l1_norm = 0
    exact_occurrences: dict[int, list[tuple[int, int]]] = defaultdict(list)
    support_sizes: list[int] = []
    for basis_index, (left, right) in enumerate(zip(basis[0], basis[1], strict=True)):
        left_support = [column for column, _coefficient in left]
        right_support = [column for column, _coefficient in right]
        if left_support != right_support:
            raise AuditError(f"basis {basis_index}: supports differ across primes")
        rational_coefficients: list[tuple[int, int, int]] = []
        scale = 1
        for (column, left_value), (_same_column, right_value) in zip(
            left, right, strict=True
        ):
            combined = crt_pair(left_value, PRIMES[0], right_value, PRIMES[1])
            numerator, denominator = rational_reconstruct(combined, modulus)
            for residue, prime in ((left_value, PRIMES[0]), (right_value, PRIMES[1])):
                if numerator * pow(denominator, -1, prime) % prime != residue:
                    raise AuditError(f"basis {basis_index}: reconstructed coefficient mismatch")
            rational_coefficients.append((column, numerator, denominator))
            scale = lcm(scale, denominator)
            denominator_histogram[denominator] += 1
            maximum_numerator = max(maximum_numerator, abs(numerator))
        vector_denominator_lcm_histogram[scale] += 1
        integer_vector: list[tuple[int, int]] = []
        common_divisor = 0
        for column, numerator, denominator in rational_coefficients:
            coefficient = numerator * (scale // denominator)
            common_divisor = gcd(common_divisor, abs(coefficient))
            integer_vector.append((column, coefficient))
        if common_divisor > 1:
            integer_vector = [
                (column, coefficient // common_divisor)
                for column, coefficient in integer_vector
            ]
        if not integer_vector or any(coefficient == 0 for _column, coefficient in integer_vector):
            raise AuditError(f"basis {basis_index}: malformed exact lift")
        for column, coefficient in integer_vector:
            exact_column_references[column].append((basis_index, coefficient))
            exact_occurrences[column].append((basis_index, coefficient))
            maximum_integer_coefficient = max(
                maximum_integer_coefficient, abs(coefficient)
            )
        maximum_integer_l1_norm = max(
            maximum_integer_l1_norm,
            sum(abs(coefficient) for _column, coefficient in integer_vector),
        )
        support_sizes.append(len(integer_vector))
        exact_basis.append(integer_vector)

    exact_identity_rows = []
    for basis_index in range(NULLITY):
        candidates = [
            row
            for row, entries in exact_occurrences.items()
            if len(entries) == 1
            and entries[0][0] == basis_index
            and entries[0][1] != 0
        ]
        if not candidates:
            raise AuditError(
                f"exact basis {basis_index}: lacks a unique nonzero coordinate"
            )
        exact_identity_rows.append(min(candidates))
    if len(set(exact_identity_rows)) != NULLITY:
        raise AuditError("exact-basis identity rows are not distinct")

    # This absolute-sum bound covers every intermediate int64 accumulator:
    # each row/vector residual contains at most the vector's full coefficient
    # L1 mass, and every hinge entry is bounded by the frozen semantic census.
    exact_hinge_accumulator_bound = 774_144 * maximum_integer_l1_norm
    exact_lambda_accumulator_bound = (
        int(np.abs(lambda_row).max()) * maximum_integer_l1_norm
    )
    if max(exact_hinge_accumulator_bound, exact_lambda_accumulator_bound) >= (1 << 63):
        raise AuditError("exact replay is not certified safe in signed int64")

    pivot_row_position = np.full(N_ROWS, -1, dtype=np.int32)
    pivot_row_position[pivot_rows] = np.arange(RANK, dtype=np.int32)
    pivot_column_position = {column: index for index, column in enumerate(pivot_columns)}
    minor = np.zeros((RANK, RANK), dtype=np.int64)
    residuals = [np.zeros((N_ROWS, NULLITY), dtype=np.uint32) for _ in PRIMES]
    exact_residual = np.zeros((N_ROWS, NULLITY), dtype=np.int64)
    union_mask = np.zeros(N_ROWS, dtype=np.bool_)
    maximum_absolute_entry = 0
    total_nonzeros = 0

    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=initialize_worker,
        initargs=(row_index,),
        maxtasksperchild=32,
    ) as pool:
        for column, result in enumerate(pool.imap(semantic_worker, records, chunksize=1)):
            sequence = int(result["sequence"])
            expected = expected_summaries[sequence]
            observed_summary = (
                int(result["support_size"]),
                int(result["total_absolute_weight"]),
                str(result["fingerprint_sha256"]),
            )
            expected_summary = (
                int(expected["hinge_support_size"]),
                int(expected["total_absolute_hinge_weight"]),
                str(expected["hinge_fingerprint_sha256"]),
            )
            if observed_summary != expected_summary:
                raise AuditError(f"semantic mismatch at sequence {sequence}")
            rows = result["rows"]
            values = result["values"]
            if not isinstance(rows, np.ndarray) or not isinstance(values, np.ndarray):
                raise AuditError("worker returned non-array sparse column")
            union_mask[rows] = True
            total_nonzeros += len(rows)
            if len(values):
                maximum_absolute_entry = max(maximum_absolute_entry, int(np.abs(values).max()))

            minor_column = pivot_column_position.get(column)
            if minor_column is not None:
                positions = pivot_row_position[rows]
                selected = positions >= 0
                minor[positions[selected], minor_column] = values[selected]

            rows_intp = rows.astype(np.intp, copy=False)
            for prime_index, prime in enumerate(PRIMES):
                residual = residuals[prime_index]
                values_mod_prime = np.remainder(values, prime)
                for basis_index, coefficient in column_references[prime_index][column]:
                    current = residual[rows_intp, basis_index].astype(np.int64)
                    updated = (current + values_mod_prime * coefficient) % prime
                    residual[rows_intp, basis_index] = updated.astype(np.uint32)
            for basis_index, coefficient in exact_column_references[column]:
                current = exact_residual[rows_intp, basis_index]
                exact_residual[rows_intp, basis_index] = (
                    current + values * coefficient
                )
            completed = column + 1
            if completed % 100 == 0 or completed == N_COLUMNS:
                print(f"CLEANROOM_G0054 columns={completed}/{N_COLUMNS}", file=sys.stderr, flush=True)

    if total_nonzeros != 12_331_131:
        raise AuditError(f"complete semantic nnz mismatch: {total_nonzeros}")
    union_rows = np.flatnonzero(union_mask).astype(np.uint32)
    union_payload = [list(universe[int(index)]) for index in union_rows]
    union_metadata = subject["exact_nonzero_row_union"]
    if len(union_rows) != 42_457:
        raise AuditError(f"union row count mismatch: {len(union_rows)}")
    # G-0054 binds this field to raw little-endian uint32 bytes, not JSON.
    union_row_indices_sha256 = hashlib.sha256(
        union_rows.astype("<u4", copy=False).tobytes(order="C")
    ).hexdigest()
    if union_row_indices_sha256 != union_metadata["union_row_indices_sha256"]:
        raise AuditError("union row-index digest mismatch")
    if canonical_sha256(union_payload) != union_metadata["union_directions_sha256"]:
        raise AuditError("union direction digest mismatch")
    if maximum_absolute_entry != 774_144:
        raise AuditError(f"maximum absolute matrix entry mismatch: {maximum_absolute_entry}")

    exact_nonzero_residuals = int(np.count_nonzero(exact_residual))
    if exact_nonzero_residuals:
        first = np.argwhere(exact_residual != 0)[0]
        location = tuple(map(int, first))
        raise AuditError(
            f"exact H*B residual nonzero at row/basis {location}: "
            f"{int(exact_residual[location])}"
        )
    exact_lambda_residuals = [
        sum(int(lambda_row[column]) * coefficient for column, coefficient in vector)
        for vector in exact_basis
    ]
    if any(exact_lambda_residuals):
        first = next(index for index, value in enumerate(exact_lambda_residuals) if value)
        raise AuditError(
            f"exact lambda*B residual nonzero at basis {first}: "
            f"{exact_lambda_residuals[first]}"
        )
    del exact_residual

    prime_audits = []
    for prime_index, (item, prime, certificate) in enumerate(
        zip(modular_results, PRIMES, lower_certificates, strict=True)
    ):
        minor_hash = hash_modular_matrix(minor, prime, "max11-g0054-rank-minor-v1")
        if minor_hash != certificate["minor_matrix_sha256"]:
            raise AuditError(f"prime {prime}: independently reconstructed minor hash mismatch")
        determinant_started = time.perf_counter()
        determinant = determinant_mod_numpy(minor, prime)
        determinant_seconds = time.perf_counter() - determinant_started
        if determinant != int(certificate["minor_determinant_mod_prime"]) or determinant == 0:
            raise AuditError(f"prime {prime}: independent minor determinant mismatch")

        nonzero_residuals = int(np.count_nonzero(residuals[prime_index]))
        if nonzero_residuals:
            first = np.argwhere(residuals[prime_index] != 0)[0]
            raise AuditError(
                f"prime {prime}: H*B residual nonzero at row/basis {tuple(map(int, first))}"
            )
        lambda_residuals = []
        for vector in basis[prime_index]:
            value = sum(int(lambda_row[column]) * coefficient for column, coefficient in vector) % prime
            lambda_residuals.append(value)
        if any(lambda_residuals):
            raise AuditError(f"prime {prime}: lambda does not annihilate the certified kernel")

        sketch = item["sketch"]
        sketch_audit = sketch_map_audit(
            union_rows,
            int(sketch["buckets"]),
            prime,
            str(sketch["seed"]),
            maximum_absolute_entry,
        )
        overflow = sketch["int64_overflow_control"]
        if sketch_audit["map_sha256"] != sketch["map_sha256"]:
            raise AuditError(f"prime {prime}: CountSketch map digest mismatch")
        for field in (
            "maximum_rows_in_one_bucket_within_a_chunk",
            "worst_case_absolute_accumulator_bound_including_prior_residue",
            "strictly_within_signed_int64",
        ):
            if sketch_audit[field] != overflow[field]:
                raise AuditError(f"prime {prime}: CountSketch overflow field mismatch: {field}")

        prime_audits.append(
            {
                "prime": prime,
                "lower_minor_rank": RANK,
                "minor_matrix_sha256": minor_hash,
                "minor_determinant_mod_prime": determinant,
                "minor_determinant_nonzero": True,
                "determinant_backend": "independent NumPy blocked modular Gaussian elimination",
                "determinant_seconds": determinant_seconds,
                "kernel_vector_count": NULLITY,
                "kernel_total_sparse_entries": basis_metadata[prime_index]["total_sparse_entries"],
                "kernel_basis_sha256": basis_metadata[prime_index]["basis_sha256"],
                "kernel_identity_rows_sha256": basis_metadata[prime_index]["identity_rows_sha256"],
                "kernel_vectors_independent_by_identity_restriction": True,
                "complete_99858_row_H_times_kernel_is_zero": True,
                "lambda_annihilates_complete_kernel": True,
                "certified_hinge_rank": RANK,
                "certified_augmented_rank": RANK,
                "countsketch_map_and_overflow_bound_replayed": True,
            }
        )
    del residuals

    if sha256_path(Path(__file__)) != script_hash_before:
        raise AuditError("audit script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "HARD_PASS_G0054_EXACT_Q_RANK_867_NO_GAIN_ON_FROZEN_S0",
        "script_sha256": script_hash_before,
        "bindings": observed_hashes,
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "workers": workers,
        },
        "independence": {
            "subject_producer_code_imported": False,
            "semantic_kernel": "committed G-0051 clean-room base-five subset-state DP",
            "rank_backend": (
                "explicit sparse modular and exact-integer kernel replay plus "
                "independent NumPy determinant"
            ),
            "subject_FLINT_rank_calls_reused": False,
        },
        "controls": controls,
        "semantic_replay": {
            "complete_rows": N_ROWS,
            "selected_columns": N_COLUMNS,
            "all_1465_column_fingerprints_match": True,
            "total_nonzeros": total_nonzeros,
            "union_rows": len(union_rows),
            "union_row_indices_encoding": "raw uint32 little-endian bytes",
            "union_row_indices_sha256": union_row_indices_sha256,
            "union_directions_sha256": canonical_sha256(union_payload),
            "maximum_absolute_matrix_entry": maximum_absolute_entry,
            "all_57401_off_union_rows_zero_by_complete_reconstruction": True,
            "lambda_recomputed_from_raw_records_by_binary_chamber_formula": True,
            "lambda_matches_G0052_entry_by_entry": True,
            "lambda_vector_sha256": canonical_sha256(independently_recomputed_lambda),
        },
        "prime_audits": prime_audits,
        "exact_rational_lift": {
            "source_primes": list(PRIMES),
            "CRT_modulus": modulus,
            "rational_reconstruction_bound": isqrt(modulus // 2),
            "supports_identical_across_primes": True,
            "basis_vector_count": len(exact_basis),
            "total_sparse_entries": sum(support_sizes),
            "support_size_minimum": min(support_sizes),
            "support_size_median": median(support_sizes),
            "support_size_maximum": max(support_sizes),
            "coefficient_denominator_histogram": {
                str(key): value for key, value in sorted(denominator_histogram.items())
            },
            "vector_denominator_LCM_histogram": {
                str(key): value
                for key, value in sorted(vector_denominator_lcm_histogram.items())
            },
            "maximum_absolute_rational_numerator": maximum_numerator,
            "primitive_integer_basis_sha256": canonical_sha256(exact_basis),
            "maximum_absolute_primitive_integer_coefficient": maximum_integer_coefficient,
            "maximum_primitive_integer_L1_norm": maximum_integer_l1_norm,
            "unique_coordinate_rows_sha256": canonical_sha256(exact_identity_rows),
            "basis_independent_over_Q_by_unique_nonzero_coordinates": True,
            "exact_hinge_accumulator_bound": exact_hinge_accumulator_bound,
            "exact_lambda_accumulator_bound": exact_lambda_accumulator_bound,
            "strictly_within_signed_int64": True,
            "complete_99858_row_H_times_integer_basis_is_exactly_zero": True,
            "lambda_times_integer_basis_is_exactly_zero": True,
        },
        "rank_orientation": {
            "matrix_shape": [42_457, N_COLUMNS],
            "kernel_vectors_have_length": N_COLUMNS,
            "H_times_kernel_orientation_verified": True,
            "lambda_is_one_row_of_length": N_COLUMNS,
            "rank_plus_nullity": RANK + NULLITY,
        },
        "classification_audit": {
            "two_prime_modular_rank_867": "CERTIFIED",
            "two_prime_modular_augmented_no_gain": "CERTIFIED",
            "exact_Q_hinge_rank_867": "CERTIFIED_BY_NONZERO_INTEGER_MINOR_AND_EXACT_KERNEL",
            "exact_Q_augmented_no_gain": "CERTIFIED_BY_COMPLETE_EXACT_KERNEL_ANNIHILATION",
            "subject_mixed_review_classification_at_delivery": "HONEST",
            "subject_exact_bounded_conclusion_was_null": True,
        },
        "exact_proof_chain": [
            (
                "The independently reconstructed 867x867 integer minor has nonzero "
                "determinant modulo both audited primes, hence its integer determinant "
                "is nonzero and rank_Q(H) is at least 867."
            ),
            (
                "The 598 primitive integer vectors are independent and exactly annihilated "
                "by all 99,858 rows, hence nullity_Q(H) is at least 598 and rank_Q(H) "
                "is at most 1465-598=867."
            ),
            (
                "Therefore those 598 vectors form a complete Q-kernel basis. Lambda "
                "annihilates every vector exactly, so lambda is in the Q-row-span of H "
                "and augmenting by lambda does not increase rank."
            ),
        ],
        "claim_boundary": (
            "This audit certifies exact rank_Q(H)=rank_Q([H;lambda])=867 only for the "
            "1,465 frozen full-core mass-four S0 columns. It does not include the 132,728 "
            "proper-core mass-four columns, does not rule out a lambda circuit after adding "
            "other columns, and proves no mass-four-wide or unrestricted MAX11 obstruction."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_json_atomic(path: Path, value: object, replace: bool) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise AuditError("output must remain inside project") from error
    if resolved.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite {resolved}; pass --replace explicitly")
    temporary = resolved.with_name(resolved.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as sink:
        sink.write(canonical_bytes(value))
        sink.flush()
        os.fsync(sink.fileno())
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
    write_json_atomic(args.output, report, args.replace)
    print(json.dumps({"result": report["result"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
