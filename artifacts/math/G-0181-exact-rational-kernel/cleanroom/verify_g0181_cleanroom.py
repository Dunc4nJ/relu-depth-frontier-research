#!/usr/bin/env python3
"""Clean-room exact audit of the frozen G-0181 left-kernel candidate.

This implementation was written after the G-0181 freeze.  It deliberately
does not import or invoke any exploratory G-0181 code or receipt.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import sys
import time
from typing import Any

import numpy as np
import scipy
import scipy.sparse as sparse


ROWS = 5_769
COLS = 6_795
BASIS = 478
EQUATIONS = BASIS * COLS
CELL_BYTES = 8
INT64_MAX = (1 << 63) - 1
EXCLUDED = [1_548, 3_140, 4_259, 5_656]
PRIMES = [1_000_003, 1_000_033, 1_000_099, 1_000_037]

MATRIX_BYTES = ROWS * COLS * CELL_BYTES
CANDIDATE_BYTES = 5_366_383
RANK_RECEIPT_BYTES = 26_869
MATRIX_SHA256 = "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd"
CANDIDATE_SHA256 = "56b4177d3e584bbe96eb35b17ba799e5138cf071dc7fd72895a45de6d4d68232"
RANK_RECEIPT_SHA256 = "61925993c97c40fac1ced04f374ffa05144026f2c2c8d3a579fa483d2219178a"
HEADER_KEYS = {
    "basis_shape",
    "crt_modulus",
    "excluded_record_sequences",
    "free_record_sequences",
    "free_rows",
    "matrix_shape",
    "primes",
    "rational_reconstruction_bound",
    "schema",
    "term_encoding",
}
RELATION_KEYS = {
    "basis_column",
    "free_record_sequence",
    "free_row",
    "max_abs_coefficient",
    "primitive_free_coefficient",
    "sum_abs_coefficients",
    "support",
    "terms",
}
DECIMAL = re.compile(r"(?:0|-?[1-9][0-9]*)\Z")


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise AuditError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def reject_constant(value: str) -> Any:
    raise AuditError(f"non-finite JSON constant: {value}")


def strict_json(raw: str, label: str) -> Any:
    try:
        return json.loads(
            raw,
            object_pairs_hook=strict_object,
            parse_constant=reject_constant,
        )
    except AuditError:
        raise
    except Exception as error:
        raise AuditError(f"invalid JSON in {label}: {error}") from error


def is_int(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def require_int(value: Any, label: str) -> int:
    require(is_int(value), f"{label} must be an integer")
    return value


def decimal_integer(value: Any, label: str, *, nonzero: bool = False) -> int:
    require(isinstance(value, str) and DECIMAL.fullmatch(value) is not None,
            f"{label} is not a canonical decimal string")
    parsed = int(value)
    if nonzero:
        require(parsed != 0, f"{label} must be nonzero")
    return parsed


def regular(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    require(resolved.is_file(), f"{label} is not a regular file")
    return resolved


def prime_by_trial_division(value: int) -> bool:
    if value < 2:
        return False
    if value % 2 == 0:
        return value == 2
    divisor = 3
    while divisor * divisor <= value:
        if value % divisor == 0:
            return False
        divisor += 2
    return True


def output_row_sequences() -> list[int]:
    excluded = set(EXCLUDED)
    result = [sequence for sequence in range(5_773) if sequence not in excluded]
    require(len(result) == ROWS, "record-sequence map census failure")
    return result


def load_candidate(path: Path) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        lines = stream.readlines()
    require(len(lines) == BASIS + 1, f"candidate must have exactly {BASIS + 1} lines")
    require(all(line.endswith("\n") for line in lines), "every JSONL line must end in LF")
    require(all("\r" not in line for line in lines), "candidate contains CR bytes")
    header = strict_json(lines[0], "candidate header")
    require(isinstance(header, dict) and set(header) == HEADER_KEYS,
            "candidate header keys drift")
    require(header["schema"] == "g0189.exact-primitive-left-kernel-basis.v1",
            "candidate schema drift")
    require(header["matrix_shape"] == [ROWS, COLS], "matrix shape drift")
    require(header["basis_shape"] == [ROWS, BASIS], "basis shape drift")
    require(header["excluded_record_sequences"] == EXCLUDED, "exclusion list drift")
    require(header["primes"] == PRIMES, "prime list drift")
    require(all(prime_by_trial_division(prime) for prime in PRIMES),
            "header contains a composite modulus")
    modulus = decimal_integer(header["crt_modulus"], "crt_modulus", nonzero=True)
    require(modulus == math.prod(PRIMES), "CRT modulus is not the prime product")
    reconstruction_bound = require_int(
        header["rational_reconstruction_bound"], "rational_reconstruction_bound"
    )
    require(reconstruction_bound == math.isqrt((modulus - 1) // 2),
            "rational reconstruction bound drift")
    require(
        header["term_encoding"]
        == "[output_row, record_sequence, primitive_integer_coefficient_as_decimal_string]",
        "term encoding drift",
    )
    free_rows = header["free_rows"]
    free_sequences = header["free_record_sequences"]
    require(
        isinstance(free_rows, list)
        and len(free_rows) == BASIS
        and all(is_int(value) for value in free_rows)
        and free_rows == sorted(set(free_rows))
        and all(0 <= value < ROWS for value in free_rows),
        "free-row list drift",
    )
    require(
        isinstance(free_sequences, list)
        and len(free_sequences) == BASIS
        and all(is_int(value) for value in free_sequences)
        and free_sequences == sorted(set(free_sequences)),
        "free-record-sequence list drift",
    )
    row_sequences = output_row_sequences()
    require(
        free_sequences == [row_sequences[row] for row in free_rows],
        "free row/record-sequence binding drift",
    )

    relations: list[dict[str, Any]] = []
    total_terms = 0
    maximum_abs_coefficient = 0
    maximum_sum_abs = 0
    support_histogram: Counter[int] = Counter()
    free_row_set = set(free_rows)
    diagonal: list[int] = []
    for basis_column, raw in enumerate(lines[1:]):
        relation = strict_json(raw, f"relation {basis_column}")
        require(isinstance(relation, dict) and set(relation) == RELATION_KEYS,
                f"relation {basis_column} keys drift")
        require(require_int(relation["basis_column"], "basis_column") == basis_column,
                f"basis-column ordering drift at {basis_column}")
        free_row = require_int(relation["free_row"], "free_row")
        free_sequence = require_int(relation["free_record_sequence"], "free_record_sequence")
        require(free_row == free_rows[basis_column], f"free-row drift at {basis_column}")
        require(free_sequence == free_sequences[basis_column],
                f"free-sequence drift at {basis_column}")
        support = require_int(relation["support"], "support")
        terms = relation["terms"]
        require(isinstance(terms, list) and len(terms) == support and support > 0,
                f"support census drift at {basis_column}")
        seen_rows: list[int] = []
        coefficients: list[int] = []
        coefficient_by_row: dict[int, int] = {}
        for term_index, term in enumerate(terms):
            require(isinstance(term, list) and len(term) == 3,
                    f"malformed term {basis_column}:{term_index}")
            row = require_int(term[0], f"term row {basis_column}:{term_index}")
            sequence = require_int(term[1], f"term sequence {basis_column}:{term_index}")
            coefficient = decimal_integer(
                term[2], f"term coefficient {basis_column}:{term_index}", nonzero=True
            )
            require(0 <= row < ROWS, f"term row out of range at {basis_column}:{term_index}")
            require(sequence == row_sequences[row],
                    f"term row/sequence binding drift at {basis_column}:{term_index}")
            seen_rows.append(row)
            coefficients.append(coefficient)
            coefficient_by_row[row] = coefficient
        require(seen_rows == sorted(set(seen_rows)),
                f"term rows are not strictly increasing at {basis_column}")
        computed_gcd = math.gcd(*(abs(value) for value in coefficients))
        require(computed_gcd == 1, f"relation {basis_column} is not primitive")
        computed_max = max(abs(value) for value in coefficients)
        computed_sum = sum(abs(value) for value in coefficients)
        require(
            decimal_integer(relation["max_abs_coefficient"], "max_abs_coefficient")
            == computed_max,
            f"max coefficient statistic drift at {basis_column}",
        )
        require(
            decimal_integer(relation["sum_abs_coefficients"], "sum_abs_coefficients")
            == computed_sum,
            f"sum-abs statistic drift at {basis_column}",
        )
        stored_diagonal = decimal_integer(
            relation["primitive_free_coefficient"], "primitive_free_coefficient", nonzero=True
        )
        require(coefficient_by_row.get(free_row) == stored_diagonal,
                f"free coefficient drift at {basis_column}")
        require(
            free_row_set.intersection(coefficient_by_row) == {free_row},
            f"off-diagonal free coordinate at {basis_column}",
        )
        diagonal.append(stored_diagonal)
        total_terms += support
        maximum_abs_coefficient = max(maximum_abs_coefficient, computed_max)
        maximum_sum_abs = max(maximum_sum_abs, computed_sum)
        support_histogram[support] += 1
        relations.append(
            {
                "basis_column": basis_column,
                "free_row": free_row,
                "terms": [(row, coefficient) for row, coefficient in zip(seen_rows, coefficients)],
                "support": support,
                "sum_abs": computed_sum,
            }
        )
    require(len(relations) == BASIS, "relation census drift")
    require(len(diagonal) == BASIS and all(value != 0 for value in diagonal),
            "diagonal independence witness failed")
    summary = {
        "relations": len(relations),
        "total_terms": total_terms,
        "support_min": min(relation["support"] for relation in relations),
        "support_max": max(relation["support"] for relation in relations),
        "support_histogram_sha256": hashlib.sha256(
            json.dumps(sorted(support_histogram.items()), separators=(",", ":")).encode()
        ).hexdigest(),
        "maximum_abs_coefficient": maximum_abs_coefficient,
        "maximum_sum_abs_coefficients": maximum_sum_abs,
        "diagonal_nonzero_count": len(diagonal),
        "diagonal_min": min(diagonal),
        "diagonal_max": max(diagonal),
        "all_relations_primitive": True,
        "all_row_sequence_bindings_exact": True,
        "free_coordinate_submatrix_diagonal_nonzero": True,
    }
    return header, relations, summary


def validate_rank_receipt(path: Path) -> dict[str, Any]:
    receipt = strict_json(path.read_text(encoding="utf-8"), "rank receipt")
    require(isinstance(receipt, dict), "rank receipt is not an object")
    expected = {
        "schema": "g0180.flint-signed-le-rectangular-rank-certificate.v1",
        "encoding": "i64le",
        "bytes_per_cell": 8,
        "input_rows": ROWS,
        "input_columns": COLS,
        "input_bytes": MATRIX_BYTES,
        "coordinate_start_inclusive": 0,
        "coordinate_end_exclusive": COLS,
        "excluded_source_rows": [],
        "selected_rows": ROWS,
        "selected_columns": COLS,
        "selected_cells": ROWS * COLS,
        "reduction_crosscheck_cells": ROWS * COLS,
        "prime": PRIMES[0],
        "rank_mod_prime": 5_291,
        "full_row_rank_mod_prime": False,
        "pivot_columns_reduced": True,
    }
    for key, value in expected.items():
        require(receipt.get(key) == value, f"rank receipt field drift: {key}")
    pivots = receipt.get("pivot_columns")
    require(
        isinstance(pivots, list)
        and len(pivots) == 5_291
        and all(is_int(value) for value in pivots)
        and pivots == sorted(set(pivots))
        and all(0 <= value < COLS for value in pivots),
        "rank receipt pivot list drift",
    )
    require(receipt.get("selected_raw_cells_sha256") == MATRIX_SHA256,
            "rank receipt is not bound to the frozen raw matrix")
    require(receipt.get("selected_modp_u64le_sha256") == MATRIX_SHA256,
            "rank receipt modular-cell digest drift")
    rref_hash = receipt.get("rref_modp_u64le_sha256")
    require(isinstance(rref_hash, str) and re.fullmatch(r"[0-9a-f]{64}", rref_hash),
            "rank receipt RREF hash malformed")
    return {
        "prime": PRIMES[0],
        "rank_mod_prime": 5_291,
        "pivot_count": len(pivots),
        "first_pivot": pivots[0],
        "last_pivot": pivots[-1],
        "rref_modp_u64le_sha256": rref_hash,
        "proof_direction": (
            "rank_Fp(A)=5291 implies rank_Q(A)>=5291 because a nonzero modular "
            "5291-minor is a nonzero integer minor"
        ),
    }


def matrix_extrema(matrix: np.memmap) -> tuple[int, int, int]:
    minimum: int | None = None
    maximum: int | None = None
    for start in range(0, ROWS, 64):
        block = matrix[start : min(start + 64, ROWS)]
        block_min = int(block.min())
        block_max = int(block.max())
        minimum = block_min if minimum is None else min(minimum, block_min)
        maximum = block_max if maximum is None else max(maximum, block_max)
    assert minimum is not None and maximum is not None
    maximum_abs = max(abs(minimum), abs(maximum))
    return minimum, maximum, maximum_abs


def build_kernel(relations: list[dict[str, Any]]) -> sparse.csr_matrix:
    relation_indices: list[int] = []
    row_indices: list[int] = []
    coefficients: list[int] = []
    for relation in relations:
        basis_column = relation["basis_column"]
        for row, coefficient in relation["terms"]:
            require(-(1 << 63) <= coefficient <= INT64_MAX,
                    "candidate coefficient does not fit signed int64")
            relation_indices.append(basis_column)
            row_indices.append(row)
            coefficients.append(coefficient)
    kernel = sparse.csr_matrix(
        (
            np.asarray(coefficients, dtype=np.int64),
            (np.asarray(relation_indices, dtype=np.int32), np.asarray(row_indices, dtype=np.int32)),
        ),
        shape=(BASIS, ROWS),
        dtype=np.int64,
    )
    require(kernel.nnz == len(coefficients), "sparse kernel coalesced duplicate entries")
    require(kernel.has_sorted_indices, "sparse kernel indices are not sorted")
    return kernel


def zero_digest(byte_count: int) -> str:
    digest = hashlib.sha256()
    block = bytes(1 << 20)
    remaining = byte_count
    while remaining:
        take = min(remaining, len(block))
        digest.update(block[:take])
        remaining -= take
    return digest.hexdigest()


def array_i64le_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array, dtype=np.dtype("<i8"))
    return hashlib.sha256(contiguous.tobytes(order="C")).hexdigest()


def write_new_json(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--rank-receipt", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    arguments = parser.parse_args()
    started = time.monotonic()

    paths = {
        "matrix": regular(arguments.matrix, "matrix"),
        "candidate": regular(arguments.candidate, "candidate"),
        "rank_receipt": regular(arguments.rank_receipt, "rank receipt"),
        "verifier_source": Path(__file__).resolve(strict=True),
    }
    require(not arguments.receipt.exists(), "refusing to overwrite receipt")
    opening = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in paths.items()
    }
    required_bindings = {
        "matrix": (MATRIX_BYTES, MATRIX_SHA256),
        "candidate": (CANDIDATE_BYTES, CANDIDATE_SHA256),
        "rank_receipt": (RANK_RECEIPT_BYTES, RANK_RECEIPT_SHA256),
    }
    for name, (expected_bytes, expected_hash) in required_bindings.items():
        require(opening[name]["bytes"] == expected_bytes, f"{name} byte-size drift")
        require(opening[name]["sha256"] == expected_hash, f"{name} SHA-256 drift")

    _header, relations, candidate_summary = load_candidate(paths["candidate"])
    rank_summary = validate_rank_receipt(paths["rank_receipt"])
    require(sys.byteorder == "little", "clean-room verifier requires a little-endian host")
    matrix = np.memmap(paths["matrix"], dtype=np.dtype("<i8"), mode="r", shape=(ROWS, COLS))
    minimum, maximum, maximum_abs = matrix_extrema(matrix)
    maximum_bound = max(relation["sum_abs"] * maximum_abs for relation in relations)
    require(maximum_bound <= INT64_MAX, "signed-int64 exact-accumulation bound failed")

    kernel = build_kernel(relations)
    multiplication_started = time.monotonic()
    residual = kernel @ matrix
    multiplication_seconds = time.monotonic() - multiplication_started
    require(isinstance(residual, np.ndarray), "sparse product did not return an ndarray")
    require(residual.shape == (BASIS, COLS), "residual shape drift")
    require(residual.dtype == np.dtype("int64"), "residual dtype drift")
    residual_nonzeros = int(np.count_nonzero(residual))
    residual_hash = array_i64le_sha256(residual)
    expected_zero_hash = zero_digest(EQUATIONS * CELL_BYTES)
    require(residual_nonzeros == 0, f"candidate has {residual_nonzeros} nonzero equations")
    require(residual_hash == expected_zero_hash, "zero-residual digest mismatch")

    # Hostile control: change the first frozen coefficient of basis column 0 by +1,
    # rebuild that relation through the same sparse multiplication path, and require
    # a detected residual.  Only this hostile relation is needed to test rejection.
    hostile_terms = list(relations[0]["terms"])
    hostile_row, hostile_old = hostile_terms[0]
    hostile_terms[0] = (hostile_row, hostile_old + 1)
    hostile_sum_abs = sum(abs(coefficient) for _, coefficient in hostile_terms)
    hostile_bound = hostile_sum_abs * maximum_abs
    require(hostile_bound <= INT64_MAX, "hostile signed-int64 bound failed")
    hostile_kernel = sparse.csr_matrix(
        (
            np.asarray([coefficient for _, coefficient in hostile_terms], dtype=np.int64),
            (
                np.zeros(len(hostile_terms), dtype=np.int32),
                np.asarray([row for row, _ in hostile_terms], dtype=np.int32),
            ),
        ),
        shape=(1, ROWS),
        dtype=np.int64,
    )
    hostile_residual = hostile_kernel @ matrix
    require(hostile_residual.shape == (1, COLS) and hostile_residual.dtype == np.dtype("int64"),
            "hostile residual shape or dtype drift")
    hostile_nonzeros = int(np.count_nonzero(hostile_residual))
    require(hostile_nonzeros > 0, "hostile +1 mutation escaped detection")
    require(np.array_equal(hostile_residual[0], matrix[hostile_row]),
            "hostile residual is not the expected +1 source row")
    hostile_nonzero_columns = np.flatnonzero(hostile_residual[0])
    hostile_first_column = int(hostile_nonzero_columns[0])
    hostile_first_value = int(hostile_residual[0, hostile_first_column])

    closing = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in paths.items()
    }
    require(closing == opening, "an input or verifier source changed during audit")
    receipt = {
        "schema": "g0191.g0181-cleanroom-exact-rank-audit.v1",
        "result": "PASS_EXACT_RANK_Q_5291",
        "claim_boundary": (
            "Exact rank only for the frozen 5769x6795 integer restriction matrix. "
            "No complete-function identity, old-span O membership, MAX11 decision, "
            "ansatz completeness, or neural-network lower bound is certified."
        ),
        "bindings": opening,
        "candidate_validation": candidate_summary,
        "independence": {
            "basis_columns": BASIS,
            "witness": "478x478 free-row restriction is diagonal with every diagonal entry nonzero",
            "independent_over_Q": True,
        },
        "exact_arithmetic": {
            "matrix_encoding": "signed-i64 little-endian",
            "matrix_minimum": minimum,
            "matrix_maximum": maximum,
            "matrix_maximum_absolute_value": maximum_abs,
            "maximum_abs_coefficient": candidate_summary["maximum_abs_coefficient"],
            "maximum_sum_abs_coefficients": candidate_summary["maximum_sum_abs_coefficients"],
            "worst_case_absolute_partial_sum_bound": maximum_bound,
            "signed_int64_maximum": INT64_MAX,
            "safety_margin": INT64_MAX - maximum_bound,
            "bound_passed": True,
            "justification": (
                "For every relation and coordinate, every product and every partial sum has "
                "absolute value at most sum_i |c_i| * max_{r,j}|A_rj|. The audited maximum "
                "is below 2^63-1, so signed-int64 sparse multiplication is exact without wraparound."
            ),
            "engine": "scipy.sparse.csr_matrix int64 multiplied by NumPy little-endian int64 memmap",
        },
        "equation_replay": {
            "operator": "C^T A",
            "residual_shape": [BASIS, COLS],
            "scalar_equations_checked": EQUATIONS,
            "nonzero_equations": residual_nonzeros,
            "residual_encoding": "basis-column-major then matrix-column signed-i64 little-endian",
            "residual_sha256": residual_hash,
            "expected_all_zero_sha256": expected_zero_hash,
            "all_exactly_zero": True,
            "multiplication_seconds": multiplication_seconds,
        },
        "hostile_control": {
            "basis_column": 0,
            "term_position": 0,
            "output_row": hostile_row,
            "record_sequence": output_row_sequences()[hostile_row],
            "old_coefficient": str(hostile_old),
            "new_coefficient": str(hostile_old + 1),
            "mutation": "+1",
            "worst_case_absolute_partial_sum_bound": hostile_bound,
            "nonzero_equations": hostile_nonzeros,
            "first_nonzero_column": hostile_first_column,
            "first_nonzero_value": hostile_first_value,
            "residual_sha256": array_i64le_sha256(hostile_residual),
            "residual_equals_added_source_row": True,
            "detected": True,
        },
        "modular_lower_bound": rank_summary,
        "rank_logic": {
            "exact_independent_left_kernel_vectors": BASIS,
            "exact_rank_upper_bound": ROWS - BASIS,
            "modular_rank_lower_bound": 5_291,
            "rank_Q": 5_291,
            "left_nullity_Q": BASIS,
            "direction_check": (
                "478 independent exact vectors in ker(A^T) give rank_Q(A)<=5291; "
                "rank_Fp(A)=5291 gives rank_Q(A)>=5291."
            ),
        },
        "runtime": {
            "elapsed_seconds": time.monotonic() - started,
            "python": sys.version,
            "implementation": platform.python_implementation(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
        },
        "all_inputs_and_source_rehashed_unchanged_at_end": True,
    }
    write_new_json(arguments.receipt, receipt)
    print(
        json.dumps(
            {
                "result": receipt["result"],
                "rank_Q": 5_291,
                "left_nullity_Q": BASIS,
                "equations": EQUATIONS,
                "hostile_nonzeros": hostile_nonzeros,
                "receipt": str(arguments.receipt.resolve()),
                "receipt_sha256": sha256_file(arguments.receipt),
                "source_sha256": opening["verifier_source"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"verify_g0181_cleanroom: {error}", file=sys.stderr)
        raise SystemExit(1)
