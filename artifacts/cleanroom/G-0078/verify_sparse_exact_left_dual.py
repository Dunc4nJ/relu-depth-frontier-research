#!/usr/bin/env python3
"""Independent verifier for the frozen G-0078 sparse exact left dual.

This program deliberately does not import code from either G-0077 or G-0078.
NumPy loads, slices, hashes, and forms int64 primitive-row quotients only after
Python has checked exact divisibility.  Every large linear combination and
target pairing is evaluated with Python arbitrary-precision integers (and
``Fraction`` reconstructs the reported raw-row weights).
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import re
import sys
from fractions import Fraction
from pathlib import Path
from typing import Any, NoReturn

import numpy as np


EXPECTED_ARTIFACT_GZIP_SHA256 = (
    "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96"
)
EXPECTED_FULL_INPUT_INT64_SHA256 = (
    "41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095"
)
EXPECTED_G0078_PRODUCER_SHA256 = (
    "6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229"
)
EXPECTED_G0078_PREFLIGHT_SHA256 = (
    "34e60905e504448980317057e617fe3e7dbf27ef1c07d1541d8c0c2b593a24be"
)
EXPECTED_G0078_PREFLIGHT_SCIENCE_SHA256 = (
    "2e055acf291460f793e6673c9df4d76441ee2d52eda59d49ddb9f809bc91ffec"
)
EXPECTED_G0077_MODULAR_SHA256 = (
    "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4"
)
EXPECTED_G0077_PRODUCER_SHA256 = (
    "278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279"
)
EXPECTED_G0077_PREFLIGHT_SHA256 = (
    "49e6e9714ef427d461d2940f7ccc7751ebf0b3d06a4a29065779b251429602a6"
)
EXPECTED_G0077_PREFLIGHT_SCIENCE_SHA256 = (
    "de58fc800430dcaaf151ca20bc37e6f379d942057b2dcf045162002b35073217"
)

EXPECTED_SHAPE = (16_738, 8_108)
EXPECTED_A_COLUMNS = 8_107
EXPECTED_SUPPORT_SIZE = 229
EXPECTED_SCHEMA = "max11-g0078-sparse-exact-left-dual-v1"
EXPECTED_RESULT = "EXACT_SPARSE_LEFT_DUAL_FROZEN_FAMILY_OBSTRUCTION"
EXPECTED_THEOREM = (
    "MAX11 is not in the rational or real span of the frozen 8107-column "
    "Y-spoke family on the bound 16738-row system."
)
EXPECTED_BOUNDARY = (
    "success concerns only the frozen finite construction family; it is not "
    "an unrestricted two-hidden-layer ReLU lower bound"
)

DECIMAL_RE = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")


class AuditError(RuntimeError):
    """A hard failure of artifact custody or exact verification."""


def fail(message: str) -> NoReturn:
    raise AuditError(message)


def require(condition: bool, message: str) -> None:
    if not condition:
        fail(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(16 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_array_bytes(array: np.ndarray) -> str:
    require(array.flags.c_contiguous, "array hash requested for non-C-contiguous data")
    digest = hashlib.sha256()
    view = memoryview(array).cast("B")
    try:
        block = 64 * 1024 * 1024
        for start in range(0, len(view), block):
            digest.update(view[start : start + block])
    finally:
        view.release()
    return digest.hexdigest()


def canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            fail(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def load_gzip_json(path: Path) -> dict[str, Any]:
    try:
        raw = gzip.decompress(path.read_bytes())
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path}: {exc}")
    require(type(value) is dict, f"top-level JSON value in {path} is not an object")
    return value


def exact_int_list(value: Any, label: str, length: int) -> list[int]:
    require(type(value) is list, f"{label} is not a list")
    require(len(value) == length, f"{label} length is {len(value)}, expected {length}")
    require(all(type(item) is int for item in value), f"{label} contains a non-integer")
    return value


def decimal_int(value: Any, label: str) -> int:
    require(type(value) is str, f"{label} is not a decimal string")
    require(DECIMAL_RE.fullmatch(value) is not None, f"{label} is not canonical decimal")
    return int(value)


def row_gcd(row: np.ndarray) -> int:
    divisor = 0
    for value in row:
        divisor = math.gcd(divisor, int(value))
    return divisor


def verify_row_divisor(row: np.ndarray, declared: int, label: str) -> int:
    require(type(declared) is int and declared > 0, f"{label} divisor is not positive")
    actual = row_gcd(row)
    require(actual > 0, f"{label} is the all-zero augmented row")
    require(actual == declared, f"{label} gcd {actual} != declared {declared}")
    for column, value in enumerate(row):
        if int(value) % declared:
            fail(f"{label} column {column} is not divisible by {declared}")
    return actual


def replay_columns(
    numerators: list[int],
    failing_weight: int,
    primitive_rows: np.ndarray,
    primitive_failing_row: np.ndarray,
    columns: int,
) -> list[int]:
    """Replay a left-dual relation using Python integers only."""
    residuals = [failing_weight * int(value) for value in primitive_failing_row[:columns]]
    for coefficient, row in zip(numerators, primitive_rows, strict=True):
        for column, value in enumerate(row[:columns]):
            residuals[column] += coefficient * int(value)
    return residuals


def integer_lines_sha256(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def first_nonzero(values: list[int]) -> tuple[int, int] | None:
    for index, value in enumerate(values):
        if value != 0:
            return index, value
    return None


def strict_increasing(values: list[int]) -> bool:
    return all(left < right for left, right in zip(values, values[1:], strict=False))


def verify_preflight(
    path: Path,
    expected_file_sha256: str,
    expected_science_sha256: str,
    expected_script_sha256: str,
) -> tuple[dict[str, Any], str]:
    file_sha256 = sha256_file(path)
    require(file_sha256 == expected_file_sha256, f"preflight hash mismatch: {path}")
    document = load_gzip_json(path)
    require(
        document.get("scientific_payload_sha256") == expected_science_sha256,
        f"recorded preflight science hash mismatch: {path}",
    )
    require(
        canonical_sha256(document.get("scientific_payload")) == expected_science_sha256,
        f"recomputed preflight science hash mismatch: {path}",
    )
    require(
        document.get("script_sha256") == expected_script_sha256,
        f"preflight script binding mismatch: {path}",
    )
    return document, file_sha256


def audit(repo: Path) -> dict[str, Any]:
    artifact_path = repo / "artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz"
    full_path = repo / "artifacts/math/G-0076/cache/full-N.npy"
    producer_78_path = repo / "artifacts/math/G-0078/sparse_exact_left_dual.py"
    preflight_78_path = repo / "artifacts/math/G-0078/sparse_exact_preflight_v1.json.gz"
    modular_77_path = repo / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
    producer_77_path = repo / "artifacts/math/G-0077/exact_left_dual_lift.py"
    preflight_77_path = repo / "artifacts/math/G-0077/exact_left_dual_preflight_v1.json.gz"

    required_paths = (
        artifact_path,
        full_path,
        producer_78_path,
        preflight_78_path,
        modular_77_path,
        producer_77_path,
        preflight_77_path,
    )
    for path in required_paths:
        require(path.is_file(), f"missing required input: {path}")

    artifact_sha_start = sha256_file(artifact_path)
    require(
        artifact_sha_start == EXPECTED_ARTIFACT_GZIP_SHA256,
        "G-0078 exact artifact gzip hash mismatch",
    )
    producer_78_sha = sha256_file(producer_78_path)
    producer_77_sha = sha256_file(producer_77_path)
    modular_77_sha = sha256_file(modular_77_path)
    require(producer_78_sha == EXPECTED_G0078_PRODUCER_SHA256, "G-0078 producer hash mismatch")
    require(producer_77_sha == EXPECTED_G0077_PRODUCER_SHA256, "G-0077 producer hash mismatch")
    require(modular_77_sha == EXPECTED_G0077_MODULAR_SHA256, "G-0077 modular hash mismatch")

    preflight_78, preflight_78_sha = verify_preflight(
        preflight_78_path,
        EXPECTED_G0078_PREFLIGHT_SHA256,
        EXPECTED_G0078_PREFLIGHT_SCIENCE_SHA256,
        EXPECTED_G0078_PRODUCER_SHA256,
    )
    preflight_77, preflight_77_sha = verify_preflight(
        preflight_77_path,
        EXPECTED_G0077_PREFLIGHT_SHA256,
        EXPECTED_G0077_PREFLIGHT_SCIENCE_SHA256,
        EXPECTED_G0077_PRODUCER_SHA256,
    )

    document = load_gzip_json(artifact_path)
    payload = document.get("scientific_payload")
    require(type(payload) is dict, "scientific_payload is not an object")
    require(document.get("schema") == EXPECTED_SCHEMA, "artifact schema mismatch")
    science_sha = canonical_sha256(payload)
    require(
        science_sha == document.get("scientific_payload_sha256"),
        "artifact scientific payload hash mismatch",
    )
    require(document.get("script_sha256") == producer_78_sha, "artifact producer binding mismatch")
    require(document.get("preflight_sha256") == preflight_78_sha, "artifact preflight binding mismatch")
    require(
        document.get("preflight_science_sha256") == EXPECTED_G0078_PREFLIGHT_SCIENCE_SHA256,
        "artifact preflight science binding mismatch",
    )
    require(document.get("g0077_modular_sha256") == modular_77_sha, "artifact G-0077 binding mismatch")
    require(
        document.get("full_input_int64_sha256") == EXPECTED_FULL_INPUT_INT64_SHA256,
        "artifact full-matrix raw binding mismatch",
    )

    modular_77 = load_gzip_json(modular_77_path)
    require(modular_77.get("schema") == "max11-g0077-canonical-modular-dual-v1", "G-0077 schema mismatch")
    require(modular_77.get("A_columns") == EXPECTED_A_COLUMNS, "G-0077 A-column count mismatch")

    support_size = payload.get("support_size")
    require(support_size == EXPECTED_SUPPORT_SIZE, "support size mismatch")
    rows = exact_int_list(payload.get("selected_raw_rows"), "selected_raw_rows", support_size)
    divisors = exact_int_list(
        payload.get("selected_raw_row_divisors"), "selected_raw_row_divisors", support_size
    )
    support = exact_int_list(
        payload.get("selected_support_positions"), "selected_support_positions", support_size
    )
    selected_columns = exact_int_list(
        payload.get("selected_A_columns"), "selected_A_columns", support_size
    )
    numerator_strings = payload.get("integer_dual_numerators")
    require(type(numerator_strings) is list, "integer_dual_numerators is not a list")
    require(len(numerator_strings) == support_size, "integer_dual_numerators length mismatch")
    numerators = [
        decimal_int(value, f"integer_dual_numerators[{index}]")
        for index, value in enumerate(numerator_strings)
    ]
    failing_weight = decimal_int(
        payload.get("integer_failing_row_weight"), "integer_failing_row_weight"
    )
    target_claim = decimal_int(payload.get("exact_target_pairing"), "exact_target_pairing")
    failing_row = payload.get("failing_raw_row")
    failing_divisor = payload.get("failing_raw_row_divisor")
    require(type(failing_row) is int, "failing_raw_row is not an integer")
    require(type(failing_divisor) is int, "failing_raw_row_divisor is not an integer")

    require(strict_increasing(rows), "selected raw rows are not strictly increasing")
    require(strict_increasing(support), "selected support positions are not strictly increasing")
    require(strict_increasing(selected_columns), "selected A columns are not strictly increasing")
    require(len(set(rows)) == support_size, "selected raw rows are not unique")
    require(failing_row not in set(rows), "failing row is also a selected row")
    require(all(0 <= row < EXPECTED_SHAPE[0] for row in rows), "selected raw row out of range")
    require(0 <= failing_row < EXPECTED_SHAPE[0], "failing raw row out of range")
    require(
        all(0 <= column < EXPECTED_A_COLUMNS for column in selected_columns),
        "selected A column out of range",
    )

    modular_support = exact_int_list(
        modular_77.get("dual_support"), "G-0077 dual_support", support_size
    )
    require(support == modular_support, "G-0078 support differs from frozen G-0077 support")
    basis_rows = modular_77.get("basis_rows")
    primitive_divisors_77 = modular_77.get("primitive_row_divisors")
    require(type(basis_rows) is list, "G-0077 basis_rows is not a list")
    require(type(primitive_divisors_77) is list, "G-0077 primitive divisors are not a list")
    require(
        [basis_rows[position] for position in support] == rows,
        "selected raw rows do not equal basis_rows[dual_support]",
    )
    require(
        [primitive_divisors_77[position] for position in support] == divisors,
        "selected divisors differ from G-0077 basis-row divisors",
    )
    require(modular_77.get("first_mismatch_row") == failing_row, "failing row differs from G-0077")
    require(
        modular_77.get("failing_row_primitive_divisor") == failing_divisor,
        "failing-row divisor differs from G-0077",
    )
    require(
        preflight_78["scientific_payload"]["support_sha256"]
        == canonical_sha256(support),
        "G-0078 preflight support hash mismatch",
    )
    require(
        preflight_78["scientific_payload"]["bindings"]["full_matrix_raw_sha256"]
        == EXPECTED_FULL_INPUT_INT64_SHA256,
        "G-0078 preflight full-matrix binding mismatch",
    )
    require(
        preflight_77["scientific_payload"]["bindings"] == modular_77.get("bindings"),
        "G-0077 modular receipt does not preserve the preflight custody bindings",
    )

    full_file_sha_before = sha256_file(full_path)
    loaded_full = np.load(full_path, allow_pickle=False)
    require(type(loaded_full) is np.ndarray, "full-N cache did not load as an ndarray")
    # np.load may return a reshaped view over its in-memory allocation.  Make a
    # second explicit copy so the audited snapshot has unambiguous ownership.
    full = np.array(loaded_full, dtype=np.int64, order="C", copy=True)
    del loaded_full
    require(full.shape == EXPECTED_SHAPE, f"full-N shape is {full.shape}, expected {EXPECTED_SHAPE}")
    require(full.dtype.str == "<i8", f"full-N dtype is {full.dtype.str}, expected <i8")
    require(full.flags.c_contiguous, "full-N cache is not C-contiguous")
    require(full.flags.owndata, "full-N cache is not an owned snapshot")
    full.setflags(write=False)
    full_file_sha_after_load = sha256_file(full_path)
    require(full_file_sha_before == full_file_sha_after_load, "full-N file changed during snapshot load")
    full_raw_sha = sha256_array_bytes(full)
    require(full_raw_sha == EXPECTED_FULL_INPUT_INT64_SHA256, "full-N raw int64 hash mismatch")

    selected_raw = np.ascontiguousarray(full[np.asarray(rows, dtype=np.intp), :])
    failing_raw = np.ascontiguousarray(full[failing_row, :])
    selected_raw.setflags(write=False)
    failing_raw.setflags(write=False)
    del full

    recomputed_divisors: list[int] = []
    for index, (row, divisor) in enumerate(zip(selected_raw, divisors, strict=True)):
        recomputed_divisors.append(
            verify_row_divisor(row, divisor, f"selected augmented row {index} (raw {rows[index]})")
        )
    recomputed_failing_divisor = verify_row_divisor(
        failing_raw, failing_divisor, f"failing augmented row {failing_row}"
    )

    primitive_rows = np.ascontiguousarray(
        selected_raw // np.asarray(divisors, dtype=np.int64)[:, None]
    )
    primitive_failing = np.ascontiguousarray(failing_raw // failing_divisor)
    primitive_rows.setflags(write=False)
    primitive_failing.setflags(write=False)

    # The frozen solve was B^T u = -d f, so its bound coefficient square is
    # the transpose of the selected primitive-row restriction and its RHS
    # records the negated failing row.
    coefficient_square = np.ascontiguousarray(primitive_rows[:, selected_columns].T)
    selected_rhs = np.ascontiguousarray(-primitive_failing[selected_columns])
    require(
        sha256_array_bytes(coefficient_square)
        == document.get("coefficient_square_int64_sha256"),
        "selected coefficient-square hash mismatch",
    )
    require(
        sha256_array_bytes(selected_rhs) == document.get("rhs_int64_sha256"),
        "selected RHS hash mismatch",
    )

    raw_weights = [Fraction(value, divisor) for value, divisor in zip(numerators, divisors, strict=True)]
    raw_failing_weight = Fraction(failing_weight, failing_divisor)
    raw_weight_pairs = [
        [str(weight.numerator), str(weight.denominator)] for weight in raw_weights
    ] + [[str(raw_failing_weight.numerator), str(raw_failing_weight.denominator)]]

    certificate_gcd = 0
    for value in [failing_weight, *numerators]:
        certificate_gcd = math.gcd(certificate_gcd, value)
    require(certificate_gcd == payload.get("certificate_gcd") == 1, "certificate is not primitive")
    require(
        failing_weight.bit_length() == payload.get("common_denominator_bits"),
        "failing-weight bit length mismatch",
    )
    max_numerator_bits = max(abs(value).bit_length() for value in numerators)
    require(
        max_numerator_bits == payload.get("max_abs_numerator_bits"),
        "maximum numerator bit length mismatch",
    )
    nonzero_numerators = sum(value != 0 for value in numerators)
    require(
        nonzero_numerators == payload.get("nonzero_numerator_weights"),
        "nonzero numerator count mismatch",
    )

    prime = modular_77.get("prime")
    require(type(prime) is int and prime > 2, "invalid G-0077 prime")
    require(failing_weight % prime != 0, "exact failing weight cannot be normalized modulo G-0077 prime")
    inverse_failing = pow(failing_weight, -1, prime)
    modular_support_coefficients = [
        (value % prime) * inverse_failing % prime for value in numerators
    ]
    modular_support_array = np.asarray(modular_support_coefficients, dtype=np.int64)
    require(
        sha256_array_bytes(modular_support_array)
        == document.get("modular_support_coefficients_sha256"),
        "modular support coefficient hash mismatch",
    )
    expanded_modular = np.zeros(len(basis_rows), dtype=np.int64)
    expanded_modular[np.asarray(support, dtype=np.intp)] = modular_support_array
    require(
        sha256_array_bytes(expanded_modular)
        == modular_77.get("dual_coefficients_mod_prime_sha256"),
        "exact certificate does not reduce to the frozen G-0077 modular dual",
    )

    residuals = replay_columns(
        numerators,
        failing_weight,
        primitive_rows,
        primitive_failing,
        EXPECTED_A_COLUMNS,
    )
    exact_failure = first_nonzero(residuals)
    require(exact_failure is None, f"first exact A-column residual: {exact_failure}")
    require(payload.get("all_A_columns_annihilated_exactly") is True, "artifact does not claim all-column success")
    require(payload.get("verified_A_columns") == EXPECTED_A_COLUMNS, "verified-column count mismatch")
    require(payload.get("first_exact_failure") is None, "artifact records an exact failure")
    require(payload.get("exact_verifier_failure") is None, "artifact records verifier failure")
    require(payload.get("failure_semantics") is None, "successful artifact has failure semantics")

    target_pairing = failing_weight * int(primitive_failing[EXPECTED_A_COLUMNS])
    for coefficient, row in zip(numerators, primitive_rows, strict=True):
        target_pairing += coefficient * int(row[EXPECTED_A_COLUMNS])
    require(target_pairing == target_claim, "exact target pairing differs from serialized value")
    require(target_pairing != 0, "exact target pairing is zero")
    require(payload.get("exact_target_pairing_nonzero") is True, "artifact target status mismatch")

    mutated_numerators = numerators.copy()
    mutated_numerators[0] += 1
    mutant_residuals = replay_columns(
        mutated_numerators,
        failing_weight,
        primitive_rows,
        primitive_failing,
        EXPECTED_A_COLUMNS,
    )
    mutant_failure = first_nonzero(mutant_residuals)
    require(mutant_failure is not None, "one-unit numerator mutant was incorrectly accepted")
    numerator_mutants_rejected = sum(
        any(int(value) != 0 for value in row[:EXPECTED_A_COLUMNS]) for row in primitive_rows
    )
    failing_weight_mutant_rejected = any(
        int(value) != 0 for value in primitive_failing[:EXPECTED_A_COLUMNS]
    )
    require(
        numerator_mutants_rejected == support_size,
        "not every one-unit numerator mutant is rejected",
    )
    require(failing_weight_mutant_rejected, "one-unit failing-weight mutant is not rejected")
    require(payload.get("one_unit_mutant_rejected") is True, "artifact mutant status mismatch")
    require(
        payload.get("one_unit_mutant_failure") == "nonzero-A-column-residual",
        "artifact mutant failure category mismatch",
    )

    require(payload.get("result") == EXPECTED_RESULT, "result label mismatch")
    require(payload.get("theorem") == EXPECTED_THEOREM, "theorem text mismatch")
    require(payload.get("claim_boundary") == EXPECTED_BOUNDARY, "claim boundary mismatch")

    artifact_sha_end = sha256_file(artifact_path)
    full_file_sha_end = sha256_file(full_path)
    require(artifact_sha_end == artifact_sha_start, "exact artifact changed during audit")
    require(full_file_sha_end == full_file_sha_before, "full-N file changed during audit")
    require(sha256_file(producer_78_path) == producer_78_sha, "G-0078 producer changed during audit")
    require(sha256_file(preflight_78_path) == preflight_78_sha, "G-0078 preflight changed during audit")
    require(sha256_file(modular_77_path) == modular_77_sha, "G-0077 modular receipt changed during audit")
    require(sha256_file(producer_77_path) == producer_77_sha, "G-0077 producer changed during audit")
    require(sha256_file(preflight_77_path) == preflight_77_sha, "G-0077 preflight changed during audit")

    verifier_sha = sha256_file(Path(__file__).resolve())
    audit_payload: dict[str, Any] = {
        "bindings": {
            "exact_artifact_gzip_sha256": artifact_sha_start,
            "exact_artifact_scientific_payload_sha256": science_sha,
            "full_input_int64_sha256": full_raw_sha,
            "full_npy_file_sha256": full_file_sha_before,
            "g0077_modular_gzip_sha256": modular_77_sha,
            "g0077_preflight_gzip_sha256": preflight_77_sha,
            "g0077_preflight_science_sha256": EXPECTED_G0077_PREFLIGHT_SCIENCE_SHA256,
            "g0077_producer_sha256": producer_77_sha,
            "g0078_preflight_gzip_sha256": preflight_78_sha,
            "g0078_preflight_science_sha256": EXPECTED_G0078_PREFLIGHT_SCIENCE_SHA256,
            "g0078_producer_sha256": producer_78_sha,
            "verifier_sha256": verifier_sha,
        },
        "certificate": {
            "certificate_gcd": certificate_gcd,
            "common_failing_weight_bits": failing_weight.bit_length(),
            "exact_target_pairing": str(target_pairing),
            "exact_target_pairing_nonzero": target_pairing != 0,
            "max_abs_numerator_bits": max_numerator_bits,
            "nonzero_numerators": nonzero_numerators,
            "raw_rational_weights_sha256": canonical_sha256(raw_weight_pairs),
            "support_size": support_size,
        },
        "claim": {
            "established": (
                "MAX11 target column is outside the rational and real column spans of the "
                "exact frozen 16738-by-8107 Y-spoke construction matrix bound above."
            ),
            "excluded": [
                "an unrestricted two-hidden-layer ReLU lower bound",
                "completeness of the frozen Y-spoke family for all networks",
                "nonrepresentability by construction families not present in the frozen matrix",
            ],
            "reason": "an exact rational left dual annihilates A and pairs nontrivially with b",
        },
        "decision": "SHIP",
        "dimensions": {
            "A_columns": EXPECTED_A_COLUMNS,
            "augmented_columns": EXPECTED_SHAPE[1],
            "full_rows": EXPECTED_SHAPE[0],
            "selected_columns": len(selected_columns),
            "witness_raw_rows": support_size + 1,
        },
        "independence": {
            "exact_arithmetic": "Python arbitrary-precision integers and fractions.Fraction",
            "forbidden_producer_imports": 0,
            "numpy_role": (
                "load/slice/hash frozen int64 input and form primitive quotients only after "
                "Python exact-divisibility checks; no NumPy dot or linear algebra"
            ),
            "producer_functions_called": 0,
        },
        "mutant_control": {
            "all_one_unit_failing_weight_mutants_rejected": failing_weight_mutant_rejected,
            "all_one_unit_numerator_mutants_rejected": numerator_mutants_rejected,
            "first_mutant_column": mutant_failure[0],
            "first_mutant_residual": str(mutant_failure[1]),
            "tested_mutation": "integer_dual_numerators[0] += 1",
        },
        "normalization": {
            "declared_divisors_sha256": canonical_sha256(divisors),
            "failing_augmented_row_gcd": recomputed_failing_divisor,
            "failing_primitive_row_int64_sha256": sha256_array_bytes(primitive_failing),
            "failing_raw_row_int64_sha256": sha256_array_bytes(failing_raw),
            "recomputed_divisors_sha256": canonical_sha256(recomputed_divisors),
            "selected_augmented_rows_checked": len(recomputed_divisors),
            "selected_primitive_rows_int64_sha256": sha256_array_bytes(primitive_rows),
            "selected_raw_rows_int64_sha256": sha256_array_bytes(selected_raw),
        },
        "replay": {
            "all_A_columns_zero": exact_failure is None,
            "exact_residual_lines_sha256": integer_lines_sha256(residuals),
            "first_nonzero_A_column": None,
            "max_abs_A_residual": max(abs(value) for value in residuals),
            "verified_A_columns": len(residuals),
        },
        "schema": "max11-g0078-independent-cleanroom-audit-payload-v1",
    }
    return {
        "audit_payload": audit_payload,
        "audit_payload_sha256": canonical_sha256(audit_payload),
        "schema": "max11-g0078-independent-cleanroom-audit-receipt-v1",
    }


def parse_args() -> argparse.Namespace:
    default_repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=default_repo, help="repository root")
    parser.add_argument(
        "--receipt",
        type=Path,
        default=Path(__file__).resolve().with_name("audit_receipt_v1.json"),
        help="deterministic JSON receipt path",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        receipt = audit(args.repo.resolve())
        encoded = canonical_json_bytes(receipt)
        args.receipt.parent.mkdir(parents=True, exist_ok=True)
        args.receipt.write_bytes(encoded)
    except AuditError as exc:
        print(f"BLOCK: {exc}", file=sys.stderr)
        return 1
    print(f"SHIP: {receipt['audit_payload_sha256']}")
    print(f"receipt: {args.receipt}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
