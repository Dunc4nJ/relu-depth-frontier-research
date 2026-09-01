#!/usr/bin/env python3
"""Outcome-blind exact first-row Schur gate for G-0168.

Scientific mode is manifest-gated and writes exactly one exclusive receipt.
The non-scientific self-test uses synthetic matrices only.  Static preflight
validates frozen input identity and the already-published G-0170 dot bridge;
it does not solve the G-0168 Schur system.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import mmap
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
from typing import Any, Callable, Iterable, Sequence

from flint import fmpq_mat, fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()

PREREGISTRATION_PATH = HERE / "PREREGISTRATION.md"
MANIFEST_PATH = HERE / "first_row_admission_manifest_v1.json"
OUTPUT_PATH = HERE / "first_row_exact_admission_v1.json"

G0164_SOLVER_PATH = ROOT / "artifacts/math/G-0164/all128_direct_basis_master_v1.py"
G0164_MEMBER_PATH = ROOT / "artifacts/math/G-0164/all128_direct_basis_member_v1.json"
G0164_GLOBAL_PATH = ROOT / "artifacts/math/G-0164/all128_global_replay_v1.json"
G0140_SELECTOR_PATH = (
    ROOT / "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
G0140_STAGE_B_PATH = ROOT / "artifacts/math/G-0140/pool128_coordinate_prices_v1.json"
G0140_STAGE_C_PATH = ROOT / "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json"

G0170_PREREGISTRATION_PATH = ROOT / "artifacts/math/G-0170/PREREGISTRATION.md"
G0170_QUERY_PATH = ROOT / "artifacts/math/G-0170/first_fresh_direction_query_v1.json"
G0170_COORDINATE_PATH = (
    ROOT / "artifacts/math/G-0170/first_fresh_direction_coordinate_v1.json"
)
G0170_BRIDGE_PATH = ROOT / "artifacts/math/G-0170/first_fresh_direction_bridge_v1.json"

G0117_CARGO_PATH = ROOT / "artifacts/math/G-0117/Cargo.toml"
G0117_SOURCE_PATH = ROOT / "artifacts/math/G-0117/src/main.rs"
G0117_KERNEL_PATH = ROOT / "artifacts/math/G-0117/src/lib.rs"
G0117_EXECUTABLE_PATH = (
    ROOT / "artifacts/math/G-0117/target/release/g0117-global-coordinate-pricer"
)

SOURCE_AUDIT_PREREGISTRATION_PATH = (
    ROOT / "artifacts/reviews/G-0171-g0168-first-row-source/PREREGISTRATION.md"
)
SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0171-g0168-first-row-source/SOURCE_AUDIT_RECEIPT.json"
)

N = 11
RECORDS = 163_740
OLD_ROWS = 540
OLD_RANK = 349
NEW_ROWS = 1
ROWS = OLD_ROWS + NEW_ROWS
FIXED_MODULAR_PRIMES = (1_000_003, 1_000_033)

PREREGISTRATION_COMMIT = "982efb2d78a7c8ca886efb9f81fa563024bdc4c1"
PREREGISTRATION_SHA256 = (
    "335b82ad402ca0ccc9ca6b0124fd4f1cc133bb2d6854912a326f4e142d11b11b"
)
G0164_SOLVER_SHA256 = "d8ea3d21e419f5a0fa7303a347af068e8f37e3f6fe53730879535f78b5070d90"
G0164_MEMBER_SHA256 = "bc4d1c58587aef6cd3b555b166ba7ec8e0f365cb0089cfd889a235e8f2e20119"
G0164_GLOBAL_SHA256 = "c04e39834de079b7ea89884cedc23956aaaf585c6ac2f3d79241395c943dba6a"
G0140_SELECTOR_SHA256 = "f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3"
G0140_STAGE_B_SHA256 = "7a923266e812bdd29fad2ecdf2d6b5cf2be85e4aacab3f92fe82bfd3b89f5c81"
G0140_STAGE_C_SHA256 = "d2a847b2d39b9111804cac1c3e4f9cc9f1fa152598c5a98610b7c5cc68cb9ba6"
G0170_PREREGISTRATION_SHA256 = (
    "2a57c9846a722f5e7554f35a0512a035c86a6e3700c747ff7a23db5822ba2fd8"
)
G0170_QUERY_SHA256 = "62b19d448697aa77aea034af5ba695d25f5c37ef00202983655151ee718b8685"
G0170_COORDINATE_SHA256 = (
    "7bf3bd1339946ad2999c38f1b8bffe88b7dfa8196bb567fcee7a58e9c897087b"
)
G0170_BRIDGE_SHA256 = "1c836567182224ed56e7b4cb6aba997400deeb167705d2f6e1397adf3ffd9347"
G0117_CARGO_SHA256 = "0e2ff3c73ce82b508ae21b35bc973c202efbeae03b7e9cf78d3b784664ce5815"
G0117_SOURCE_SHA256 = "b8f079d08f1100108433428bc5fe4daa40edf5e90757736013fa07002c1fab0c"
G0117_KERNEL_SHA256 = "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6"
G0117_EXECUTABLE_SHA256 = (
    "66bb82580f8540087a9e0476043390694002f63593ba4bc803346a6f07ae3a04"
)
BASIS_SEQUENCES_SHA256 = (
    "c9ec5dbb017e2f735a115ca2eb757adf4d93f072a287f08286c2776b29ec08b3"
)
BASIS_MATRIX_SHA256 = "7451a36e42c479819b6f9ae28ec8c2f7b23360ddc5203b17cf9e3417d1ac9d10"
SQUARE_MATRIX_SHA256 = "f06bf820562a96575274bd8358b7ca0eef695e3e991034072deecf97823d3606"
TARGET_SHA256 = "a30ec0a4ff135350f217363831c6ffd2ee0a44f74b4d14549aa3b88da3967874"
FIRST_DIRECTION_SHA256 = "401f959ef40eeb099a39f4758dcdb8ac0d681bdae6dec4591a6b78b6eb46003d"
FIRST_RESIDUALS_SHA256 = "b5f51eddada538ba8a8d224abcd97dca04f9c042c08d1548fac43a6826784ce5"
FIRST_ROW_I64_SHA256 = "f4285a36af1c3985576c2471352c36d972e8c69ed32f372b6bd83da4dec89ddc"

MANIFEST_SCHEMA = "max11-g0168-first-row-admission-manifest-v1"
OUTPUT_SCHEMA = "max11-g0168-first-row-exact-admission-v1"
RANK_RESULT = "FIRST_ROW_EXACT_RANK_GROWTH"
DEPENDENCY_RESULT = "FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY"
SOURCE_AUDIT_SCHEMA = "max11-g0171-g0168-first-row-source-audit-v1"
SOURCE_AUDIT_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
SOURCE_AUDIT_EVIDENCE = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"

CLAIM_BOUNDARY = (
    "FIRST_ROW_EXACT_RANK_GROWTH proves only that the exact G-0170 row raises "
    "the frozen 540-row family rank from 349 to 350 and supplies one exact "
    "541-row corrected family member. FIRST_ROW_EXACT_INCOMPATIBLE_DEPENDENCY "
    "excludes only the frozen 163,740-column family under the exact 541-row "
    "target. Neither branch proves family completeness, a global MAX11 "
    "identity, an unrestricted lower bound, minimality, an all-n theorem, "
    "refereed status, formalization, or a Lean theorem."
)
SOURCE_AUDIT_CLAIM_BOUNDARY = (
    "T1 source/custody clearance for the exact frozen G-0168 first-row Schur "
    "producer bytes only; no G-0168 scientific manifest, coordinate input, "
    "rank result, corrected member, or separator was observed or produced."
)
SOURCE_AUDIT_NO_CLAIM = (
    "This source audit does not decide first-row rank growth or dependence, "
    "establish a corrected member or separator, validate family completeness, "
    "prove a global MAX11 identity or lower bound, establish minimality, prove "
    "an all-n statement, or supply a Lean theorem."
)
SOURCE_AUDIT_REQUIRED_CHECKS = {
    "branch_total_rank_or_dependency_contract_verified": True,
    "canonical_column_order_and_first_exact_witness_verified": True,
    "canonical_null_vector_all_540_rows_replay_verified": True,
    "corrected_541_row_member_replay_verified": True,
    "duplicate_json_keys_and_trailing_data_rejected": True,
    "exact_349_square_digest_gate_verified": True,
    "exact_350_minor_determinant_and_digest_verified": True,
    "exact_dependency_full_family_replay_verified": True,
    "exclusive_output_publication_verified": True,
    "g0170_exact_dot_bridge_revalidated": True,
    "input_snapshot_and_end_rehash_verified": True,
    "modular_arithmetic_never_terminal_verified": True,
    "outcome_bearing_modes_not_run": True,
    "scientific_manifest_absent_during_audit": True,
    "synthetic_dependency_branch_passed": True,
    "synthetic_rank_growth_branch_passed": True,
}


class AdmissionError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AdmissionError(message)


def contained(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise AdmissionError(f"path escapes repository: {path}") from error
    return resolved


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with contained(path).open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_sha(path: Path, expected: str, label: str) -> None:
    require(path.is_file(), f"missing {label}: {relative(path)}")
    require(sha256_path(path) == expected, f"{label} SHA-256 drift")


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in output, f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_json(path: Path) -> dict[str, Any]:
    raw = contained(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder(object_pairs_hook=no_duplicate_object)
    value, end = decoder.raw_decode(raw)
    require(not raw[end:].strip(), f"trailing JSON data: {relative(path)}")
    require(isinstance(value, dict), f"non-object JSON: {relative(path)}")
    return value


def load_module(path: Path, name: str) -> Any:
    spec = importlib.util.spec_from_file_location(name, contained(path))
    require(spec is not None and spec.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def git_commit_for_path(path: Path) -> str:
    name = relative(path)
    result = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", name],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    require(
        len(commit) == 40 and all(character in "0123456789abcdef" for character in commit),
        f"missing Git commit for {name}",
    )
    blob = subprocess.run(
        ["git", "show", f"{commit}:{name}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    require(
        hashlib.sha256(blob.stdout).hexdigest() == sha256_path(path),
        f"working bytes differ from committed blob: {name}",
    )
    return commit


def git_is_ancestor(ancestor: str, descendant: str, label: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT
    )
    require(result.returncode == 0, f"Git ancestry failure: {label}")


def binding(path: Path) -> dict[str, str]:
    return {"path": relative(path), "sha256": sha256_path(path)}


def commit_binding(path: Path) -> dict[str, str]:
    return {
        "path": relative(path),
        "sha256": sha256_path(path),
        "git_commit": git_commit_for_path(path),
    }


def digest_signed(values: Iterable[int], width: int) -> str:
    digest = hashlib.sha256()
    for value in values:
        try:
            digest.update(int(value).to_bytes(width, "little", signed=True))
        except OverflowError as error:
            raise AdmissionError(f"signed-{8 * width} overflow") from error
    return digest.hexdigest()


def digest_i64(values: Iterable[int]) -> str:
    return digest_signed(values, 8)


def digest_i128(values: Iterable[int]) -> str:
    return digest_signed(values, 16)


def digest_u64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(0 <= int(value) < 1 << 64, "u64 overflow")
        digest.update(int(value).to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def digest_decimal_lf(values: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def digest_text(value: object) -> str:
    return hashlib.sha256(str(value).encode("ascii")).hexdigest()


def input_snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(snapshot.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\t")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def snapshot_add(snapshot: dict[str, str], path: Path, expected: str, label: str) -> None:
    require_sha(path, expected, label)
    name = relative(path)
    require(name not in snapshot or snapshot[name] == expected, f"snapshot collision: {name}")
    snapshot[name] = expected


def rehash_snapshot(snapshot: dict[str, str]) -> None:
    for name, expected in sorted(snapshot.items()):
        require_sha(ROOT / name, expected, f"end-bound input {name}")


def canonical_integer(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise AdmissionError(f"boolean integer: {label}")
    if isinstance(value, int):
        return value
    require(isinstance(value, str), f"non-integer: {label}")
    require(value == "0" or value.lstrip("-").isdigit(), f"bad integer: {label}")
    require(not (value.startswith("0") and len(value) > 1), f"leading zero: {label}")
    require(not value.startswith("-0"), f"negative zero: {label}")
    return int(value)


def canonical_fraction(value: Fraction) -> str:
    value = Fraction(value)
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def qmatrix(rows: Sequence[Sequence[int]]) -> fmpq_mat:
    require(bool(rows), "empty exact matrix")
    columns = len(rows[0])
    require(columns > 0 and all(len(row) == columns for row in rows), "ragged matrix")
    return fmpq_mat(fmpz_mat([[int(value) for value in row] for row in rows]))


def fractions_from_column(column: fmpq_mat) -> list[Fraction]:
    output: list[Fraction] = []
    for index in range(column.nrows()):
        value = column[index, 0]
        numerator = int(value.numerator)
        denominator = int(value.denominator)
        require(
            denominator > 0 and math.gcd(abs(numerator), denominator) == 1,
            f"noncanonical FLINT rational {index}",
        )
        output.append(Fraction(numerator, denominator))
    return output


def primitive_integer_vector(values: Sequence[Fraction]) -> tuple[list[int], int]:
    require(bool(values), "empty rational vector")
    scale = math.lcm(*(value.denominator for value in values))
    integers = [value.numerator * (scale // value.denominator) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "primitive normalization vanished")
    scale //= divisor
    integers = [value // divisor for value in integers]
    require(scale > 0, "nonpositive primitive scale")
    require(math.gcd(scale, *[abs(value) for value in integers]) == 1, "nonprimitive vector")
    return integers, scale


def solve_relation(square_rows: Sequence[Sequence[int]], hinge_on_basis: Sequence[int]) -> dict[str, Any]:
    rank = len(square_rows)
    require(
        rank > 0
        and len(hinge_on_basis) == rank
        and all(len(row) == rank for row in square_rows),
        "Schur solve shape drift",
    )
    square = qmatrix(square_rows)
    rhs = qmatrix([[int(value)] for value in hinge_on_basis])
    lambdas = fractions_from_column(square.transpose().solve(rhs))
    relation, scale = primitive_integer_vector(lambdas)
    for column in range(rank):
        require(
            sum(relation[row] * int(square_rows[row][column]) for row in range(rank))
            == scale * int(hinge_on_basis[column]),
            f"cleared relation failed basis column {column}",
        )
    return {"lambdas": lambdas, "relation": relation, "scale": scale}


def exact_delta_numerator(
    coordinate_values: Sequence[int],
    hinge_value: int,
    relation: Sequence[int],
    scale: int,
) -> int:
    require(len(coordinate_values) == len(relation), "Schur coordinate width drift")
    return scale * int(hinge_value) - sum(
        coefficient * int(value)
        for coefficient, value in zip(relation, coordinate_values, strict=True)
    )


def canonical_null_vector(
    square_rows: Sequence[Sequence[int]],
    witness_coordinates: Sequence[int],
) -> dict[str, Any]:
    square = qmatrix(square_rows)
    rhs = qmatrix([[int(value)] for value in witness_coordinates])
    coordinates = fractions_from_column(square.solve(rhs))
    basis_integers, witness_integer = primitive_integer_vector(
        [-value for value in coordinates]
    )
    # primitive_integer_vector represents [-x] with a shared positive scale d;
    # appending +d gives the canonical delta = d e_j - d Bx.
    vector = basis_integers + [witness_integer]
    divisor = 0
    for value in vector:
        divisor = math.gcd(divisor, abs(value))
    require(witness_integer > 0 and divisor == 1, "canonical null-vector normalization drift")
    return {
        "basis_coordinates": coordinates,
        "basis_integer_coefficients": basis_integers,
        "witness_integer_coefficient": witness_integer,
    }


def normalize_member(values: Sequence[Fraction]) -> tuple[list[int], int]:
    require(bool(values), "empty corrected member")
    scale = math.lcm(*(value.denominator for value in values))
    integers = [int(value * scale) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "corrected member normalization vanished")
    scale //= divisor
    integers = [value // divisor for value in integers]
    require(scale > 0 and any(integers), "zero corrected member")
    require(math.gcd(scale, *[abs(value) for value in integers]) == 1, "nonprimitive member")
    return integers, scale


def exact_rank_branch(
    matrix_rows: Sequence[Sequence[int]],
    square_rows: Sequence[Sequence[int]],
    target: Sequence[int],
    basis_sequences: Sequence[int],
    coordinate_rows: Sequence[int],
    hinge: Sequence[int],
    relation: dict[str, Any],
    witness_sequence: int,
    witness_column: Sequence[int],
    delta_numerator: int,
    current_basis_coefficients: Sequence[int],
    current_scale: int,
    frozen_residual: int,
) -> dict[str, Any]:
    rank = len(basis_sequences)
    require(
        len(matrix_rows) == len(target)
        and len(square_rows) == rank
        and len(witness_column) == len(matrix_rows)
        and witness_sequence not in set(basis_sequences),
        "rank-branch shape drift",
    )
    witness_coordinates = [int(witness_column[row]) for row in coordinate_rows]
    null = canonical_null_vector(square_rows, witness_coordinates)
    null_basis = null["basis_integer_coefficients"]
    null_witness = null["witness_integer_coefficient"]

    old_residuals = [
        sum(null_basis[column] * int(matrix_rows[row][column]) for column in range(rank))
        + null_witness * int(witness_column[row])
        for row in range(len(matrix_rows))
    ]
    require(not any(old_residuals), "canonical null vector failed an old row")
    null_hinge_pairing = sum(
        null_basis[column] * int(hinge[basis_sequences[column]])
        for column in range(rank)
    ) + null_witness * int(hinge[witness_sequence])
    require(null_hinge_pairing != 0, "canonical null vector lost new-row pairing")
    require(
        Fraction(null_hinge_pairing, null_witness)
        == Fraction(delta_numerator, int(relation["scale"])),
        "canonical null vector/Schur delta mismatch",
    )

    minor_rows = [
        list(map(int, square_rows[row])) + [witness_coordinates[row]] for row in range(rank)
    ]
    minor_rows.append(
        [int(hinge[sequence]) for sequence in basis_sequences] + [int(hinge[witness_sequence])]
    )
    minor = fmpz_mat(minor_rows)
    minor_determinant = int(minor.det())
    square_determinant = int(fmpz_mat(square_rows).det())
    require(minor_determinant != 0 and square_determinant != 0, "rank minor vanished")
    require(
        Fraction(minor_determinant, 1)
        == Fraction(square_determinant * delta_numerator, int(relation["scale"])),
        "literal 350-minor disagrees with Schur determinant formula",
    )

    alpha = Fraction(frozen_residual, current_scale * null_hinge_pairing)
    corrected_rationals = [
        Fraction(int(current_basis_coefficients[column]), current_scale)
        - alpha * int(null_basis[column])
        for column in range(rank)
    ] + [-alpha * null_witness]
    corrected_integers, corrected_scale = normalize_member(corrected_rationals)
    corrected_old_residuals = [
        sum(
            corrected_integers[column] * int(matrix_rows[row][column])
            for column in range(rank)
        )
        + corrected_integers[-1] * int(witness_column[row])
        - corrected_scale * int(target[row])
        for row in range(len(matrix_rows))
    ]
    require(not any(corrected_old_residuals), "corrected member failed an old row")
    corrected_hinge_residual = sum(
        corrected_integers[column] * int(hinge[basis_sequences[column]])
        for column in range(rank)
    ) + corrected_integers[-1] * int(hinge[witness_sequence])
    require(corrected_hinge_residual == 0, "corrected member failed the appended zero target")

    support = [
        {"sequence": int(sequence), "coefficient": str(coefficient)}
        for sequence, coefficient in sorted(
            zip(list(basis_sequences) + [witness_sequence], corrected_integers, strict=True)
        )
        if coefficient
    ]
    mutant_index = next(index for index, value in enumerate(corrected_integers) if value)
    if mutant_index < rank:
        mutant_column = [int(matrix_rows[row][mutant_index]) for row in range(len(matrix_rows))]
        mutant_sequence = int(basis_sequences[mutant_index])
        mutant_hinge_price = int(hinge[mutant_sequence])
        mutant_is_witness = False
    else:
        require(mutant_index == rank, "corrected-member mutant index drift")
        mutant_column = [int(value) for value in witness_column]
        mutant_sequence = witness_sequence
        mutant_hinge_price = int(hinge[witness_sequence])
        mutant_is_witness = True
    mutant_old = [
        corrected_old_residuals[row] + mutant_column[row]
        for row in range(len(matrix_rows))
    ]
    mutant_hinge = corrected_hinge_residual + mutant_hinge_price
    require(any(mutant_old) or mutant_hinge != 0, "corrected-member plus-one mutant survived")

    return {
        "witness_sequence": witness_sequence,
        "delta_numerator": str(delta_numerator),
        "delta_denominator": str(relation["scale"]),
        "old_rank": rank,
        "new_rank": rank + 1,
        "canonical_null_vector": {
            "basis_sequences": list(map(int, basis_sequences)),
            "basis_integer_coefficients": [str(value) for value in null_basis],
            "witness_sequence": witness_sequence,
            "witness_integer_coefficient": str(null_witness),
            "support": sum(value != 0 for value in null_basis) + 1,
            "all_540_old_rows_exact_zero": True,
            "old_residuals_decimal_lf_sha256": digest_decimal_lf(old_residuals),
            "new_row_pairing": str(null_hinge_pairing),
        },
        "exact_350_minor": {
            "rows": rank + 1,
            "columns": rank + 1,
            "coordinate_rows": list(map(int, coordinate_rows)) + [OLD_ROWS],
            "column_sequences": list(map(int, basis_sequences)) + [witness_sequence],
            "matrix_i128le_sha256": digest_i128(
                value for row in minor_rows for value in row
            ),
            "determinant": str(minor_determinant),
            "determinant_decimal_sha256": digest_text(minor_determinant),
            "square_determinant": str(square_determinant),
            "schur_formula_verified": True,
        },
        "corrected_member": {
            "target_scale": str(corrected_scale),
            "basis_sequences": list(map(int, basis_sequences)) + [witness_sequence],
            "integer_coefficients": [str(value) for value in corrected_integers],
            "integer_coefficients_decimal_lf_sha256": digest_decimal_lf(corrected_integers),
            "support_columns": len(support),
            "terms": support,
            "all_540_old_rows_exactly_replayed": True,
            "old_residuals_decimal_lf_sha256": digest_decimal_lf(corrected_old_residuals),
            "appended_zero_target_exactly_replayed": True,
            "appended_residual": "0",
            "coefficient_plus_one_mutant": {
                "coefficient_index": mutant_index,
                "sequence": mutant_sequence,
                "is_witness_column": mutant_is_witness,
                "old_nonzero_rows": sum(value != 0 for value in mutant_old),
                "new_row_residual": str(mutant_hinge),
                "rejected": True,
            },
        },
    }


def exact_dependency_branch(
    target: Sequence[int],
    coordinate_rows: Sequence[int],
    relation: dict[str, Any],
    current_scale: int,
    frozen_residual: int,
    scanned: int,
    residual_digest: str,
) -> dict[str, Any]:
    coefficients = [int(value) for value in relation["relation"]]
    scale = int(relation["scale"])
    target_pairing = sum(
        coefficient * int(target[row])
        for coefficient, row in zip(coefficients, coordinate_rows, strict=True)
    )
    require(target_pairing != 0, "dependent row is target-compatible despite nonzero bridge")
    require(
        scale * frozen_residual == current_scale * target_pairing,
        "dependency separator target pairing disagrees with frozen member bridge",
    )
    separator_values = coefficients + [-scale]
    divisor = 0
    for value in separator_values:
        divisor = math.gcd(divisor, abs(value))
    require(divisor == 1, "dependency separator is not primitive")
    return {
        "records_scanned": scanned,
        "all_columns_exact_zero": True,
        "schur_residuals_decimal_lf_sha256": residual_digest,
        "separator": {
            "old_coordinate_rows": list(map(int, coordinate_rows)),
            "old_row_integer_coefficients": [str(value) for value in coefficients],
            "appended_row": OLD_ROWS,
            "appended_row_integer_coefficient": str(-scale),
            "primitive": True,
            "annihilates_all_163740_columns": True,
            "target_pairing": str(target_pairing),
            "nonzero_target_pairing": True,
            "member_bridge_identity_verified": True,
        },
    }


def synthetic_model(
    old_matrix_rows: Sequence[Sequence[int]],
    target: Sequence[int],
    hinge: Sequence[int],
    current_coefficients: Sequence[int],
    current_scale: int,
) -> tuple[str, dict[str, Any]]:
    rank = len(old_matrix_rows)
    require(rank > 0 and all(len(row) == len(hinge) for row in old_matrix_rows), "fixture shape")
    basis = list(range(rank))
    coordinate_rows = list(range(rank))
    matrix_rows = [list(row[:rank]) for row in old_matrix_rows]
    square_rows = [matrix_rows[row] for row in coordinate_rows]
    relation = solve_relation(square_rows, [hinge[sequence] for sequence in basis])
    frozen_residual = sum(
        int(current_coefficients[sequence]) * int(hinge[sequence])
        for sequence in range(len(hinge))
    )
    residuals = []
    for sequence in range(len(hinge)):
        column = [int(row[sequence]) for row in old_matrix_rows]
        coordinates = [column[row] for row in coordinate_rows]
        delta = exact_delta_numerator(
            coordinates, int(hinge[sequence]), relation["relation"], relation["scale"]
        )
        residuals.append(delta)
        if delta:
            branch = exact_rank_branch(
                matrix_rows,
                square_rows,
                target,
                basis,
                coordinate_rows,
                hinge,
                relation,
                sequence,
                column,
                delta,
                current_coefficients[:rank],
                current_scale,
                frozen_residual,
            )
            return RANK_RESULT, branch
    branch = exact_dependency_branch(
        target,
        coordinate_rows,
        relation,
        current_scale,
        frozen_residual,
        len(hinge),
        digest_decimal_lf(residuals),
    )
    return DEPENDENCY_RESULT, branch


def self_test() -> dict[str, bool]:
    rank_result, rank_branch = synthetic_model(
        [[1, 0, 1], [0, 1, 1]],
        [1, 1],
        [2, 3, 8],
        [1, 1, 0],
        1,
    )
    require(
        rank_result == RANK_RESULT
        and rank_branch["witness_sequence"] == 2
        and rank_branch["corrected_member"]["appended_residual"] == "0",
        "synthetic rank-growth branch failed",
    )

    witness_only_result, witness_only_branch = synthetic_model(
        [[1, 0, 1], [0, 1, 1]],
        [1, 1],
        [2, 3, 0],
        [1, 1, 0],
        1,
    )
    require(
        witness_only_result == RANK_RESULT
        and witness_only_branch["corrected_member"]["integer_coefficients"]
        == ["0", "0", "1"]
        and witness_only_branch["corrected_member"]["coefficient_plus_one_mutant"]
        ["is_witness_column"]
        is True,
        "synthetic witness-only corrected-member regression failed",
    )

    dependency_result, dependency_branch = synthetic_model(
        [[1, 0, 1], [0, 1, 1]],
        [1, 1],
        [2, 3, 5],
        [1, 1, 0],
        1,
    )
    require(
        dependency_result == DEPENDENCY_RESULT
        and dependency_branch["records_scanned"] == 3
        and dependency_branch["separator"]["target_pairing"] == "5",
        "synthetic dependency branch failed",
    )

    for name, malformed in [
        ("duplicate", '{"a":1,"a":2}'),
        ("trailing", '{"a":1}\n{"b":2}'),
    ]:
        temporary: Path | None = None
        try:
            descriptor, raw = tempfile.mkstemp(
                prefix=f"g0168-{name}-", suffix=".json", dir=HERE
            )
            temporary = Path(raw)
            with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
                destination.write(malformed)
            rejected = False
            try:
                load_json(temporary)
            except AdmissionError:
                rejected = True
            require(rejected, f"{name} JSON fixture survived")
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    return {
        "synthetic_rank_growth_branch": True,
        "synthetic_witness_only_corrected_member": True,
        "synthetic_dependency_branch": True,
        "duplicate_json_key_rejected": True,
        "trailing_json_data_rejected": True,
    }


def validate_static_inputs() -> dict[str, Any]:
    require(
        Path.cwd().resolve() == ROOT,
        "run from repository root",
    )
    for path, expected, label in [
        (PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "G-0168 preregistration"),
        (G0164_SOLVER_PATH, G0164_SOLVER_SHA256, "G-0164 solver"),
        (G0164_MEMBER_PATH, G0164_MEMBER_SHA256, "G-0164 member"),
        (G0164_GLOBAL_PATH, G0164_GLOBAL_SHA256, "G-0164 global result"),
        (G0140_SELECTOR_PATH, G0140_SELECTOR_SHA256, "G-0140 selector"),
        (G0140_STAGE_B_PATH, G0140_STAGE_B_SHA256, "G-0140 Stage B"),
        (G0140_STAGE_C_PATH, G0140_STAGE_C_SHA256, "G-0140 Stage C"),
        (
            G0170_PREREGISTRATION_PATH,
            G0170_PREREGISTRATION_SHA256,
            "G-0170 preregistration",
        ),
        (G0170_QUERY_PATH, G0170_QUERY_SHA256, "G-0170 query"),
        (G0170_COORDINATE_PATH, G0170_COORDINATE_SHA256, "G-0170 coordinate"),
        (G0170_BRIDGE_PATH, G0170_BRIDGE_SHA256, "G-0170 bridge"),
        (G0117_CARGO_PATH, G0117_CARGO_SHA256, "G-0117 Cargo manifest"),
        (G0117_SOURCE_PATH, G0117_SOURCE_SHA256, "G-0117 coordinate source"),
        (G0117_KERNEL_PATH, G0117_KERNEL_SHA256, "G-0117 kernel"),
        (G0117_EXECUTABLE_PATH, G0117_EXECUTABLE_SHA256, "G-0117 executable"),
    ]:
        require_sha(path, expected, label)
    require(
        git_commit_for_path(PREREGISTRATION_PATH) == PREREGISTRATION_COMMIT,
        "G-0168 preregistration commit drift",
    )

    member = load_json(G0164_MEMBER_PATH)
    global_result = load_json(G0164_GLOBAL_PATH)
    query = load_json(G0170_QUERY_PATH)
    coordinate = load_json(G0170_COORDINATE_PATH)
    bridge = load_json(G0170_BRIDGE_PATH)

    basis_sequences = member.get("basis_sequences")
    coordinate_rows = member.get("coordinate_rows")
    coefficients_raw = member.get("integer_coefficients")
    target_raw = member.get("target")
    terms = member.get("terms")
    require(
        member.get("schema") == "max11-g0164-all128-direct-basis-member-v1"
        and member.get("result") == "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER"
        and member.get("records") == RECORDS
        and member.get("rows") == OLD_ROWS
        and member.get("rank") == OLD_RANK
        and member.get("augmented_rank") == OLD_RANK
        and member.get("basis_sequences_u64le_sha256") == BASIS_SEQUENCES_SHA256
        and member.get("basis_i128le_sha256") == BASIS_MATRIX_SHA256
        and member.get("square_i128le_sha256") == SQUARE_MATRIX_SHA256
        and member.get("target_i128le_sha256") == TARGET_SHA256
        and member.get("all_540_rational_rows_replayed") is True
        and member.get("all_540_primitive_integer_rows_replayed") is True
        and member.get("primitive_denominator_clearing") is True
        and isinstance(basis_sequences, list)
        and len(basis_sequences) == OLD_RANK
        and basis_sequences == sorted(set(basis_sequences))
        and isinstance(coordinate_rows, list)
        and len(coordinate_rows) == OLD_RANK
        and coordinate_rows == sorted(set(coordinate_rows))
        and isinstance(coefficients_raw, list)
        and len(coefficients_raw) == OLD_RANK
        and isinstance(target_raw, list)
        and len(target_raw) == OLD_ROWS
        and isinstance(terms, list)
        and len(terms) == 304,
        "G-0164 member contract drift",
    )
    require(
        digest_u64(int(value) for value in basis_sequences) == BASIS_SEQUENCES_SHA256,
        "basis sequence digest drift",
    )
    coefficients = [
        canonical_integer(value, f"member coefficient {index}")
        for index, value in enumerate(coefficients_raw)
    ]
    target = [
        canonical_integer(value, f"target {index}") for index, value in enumerate(target_raw)
    ]
    current_scale = canonical_integer(member.get("target_scale"), "member target scale")
    require(current_scale > 0, "member target scale is not positive")
    require(
        digest_i128(target) == TARGET_SHA256,
        "target digest replay drift",
    )
    expected_terms = [
        {"sequence": int(sequence), "coefficient": str(coefficient)}
        for sequence, coefficient in zip(basis_sequences, coefficients, strict=True)
        if coefficient
    ]
    require(terms == expected_terms, "member term projection drift")

    prefix = global_result.get("residual_prefix")
    require(
        global_result.get("schema") == "max11-g0164-all128-global-replay-v1"
        and global_result.get("result") == "EXACT_RESIDUAL_CONTINUE"
        and global_result.get("rows") == OLD_ROWS
        and global_result.get("records") == RECORDS
        and global_result.get("rank") == OLD_RANK
        and global_result.get("support_columns") == 304
        and global_result.get("complete_global_replay") is True
        and global_result.get("all_hinge_and_linear_residuals_zero") is False
        and global_result.get("all_accumulated_directions_exact_zero") is True
        and global_result.get("all_11_linear_residuals_exact_zero") is True
        and global_result.get("residual_prefix_count") == 128
        and global_result.get("residual_prefix_k") == 128
        and global_result.get("residual_prefix_directions_i8_sha256")
        == FIRST_DIRECTION_SHA256
        and global_result.get("residual_prefix_exact_residuals_decimal_lf_sha256")
        == FIRST_RESIDUALS_SHA256
        and isinstance(prefix, list)
        and len(prefix) == 128,
        "G-0164 global residual-prefix contract drift",
    )
    first = prefix[0]
    require(
        isinstance(first, dict)
        and set(first) == {"direction", "coefficient"}
        and isinstance(first.get("direction"), list)
        and len(first["direction"]) == N,
        "first residual-prefix entry drift",
    )
    direction = [canonical_integer(value, f"direction {index}") for index, value in enumerate(first["direction"])]
    frozen_residual = canonical_integer(first.get("coefficient"), "first frozen residual")
    require(frozen_residual != 0, "first frozen residual became zero")

    require(
        query
        == {
            "schema": "max11-g0117-coordinate-query-v1",
            "direction": direction,
            "expected_records": RECORDS,
            "emit_values": True,
        },
        "G-0170 query contract drift",
    )
    hinge = coordinate.get("hinge_coefficients")
    linear = coordinate.get("linear_vectors")
    require(
        coordinate.get("schema") == "max11-g0117-coordinate-price-v1"
        and coordinate.get("result") == "EXACT_COORDINATE_PRICES"
        and coordinate.get("direction") == direction
        and coordinate.get("records") == RECORDS
        and coordinate.get("hinge_coefficients_i64_le_sha256") == FIRST_ROW_I64_SHA256
        and isinstance(hinge, list)
        and len(hinge) == RECORDS
        and all(isinstance(value, int) and not isinstance(value, bool) for value in hinge)
        and isinstance(linear, list)
        and len(linear) == RECORDS,
        "G-0170 coordinate contract drift",
    )
    require(digest_i64(hinge) == FIRST_ROW_I64_SHA256, "G-0170 row digest drift")
    require(
        sum(value != 0 for value in hinge) == coordinate.get("nonzero_hinge_coefficients")
        and max(hinge, default=0) == coordinate.get("maximum_hinge_coefficient"),
        "G-0170 row extrema/census drift",
    )
    expected_bindings = {
        "executable": G0117_EXECUTABLE_SHA256,
        "kernel": G0117_KERNEL_SHA256,
        "panel_input": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
        "producer": G0117_SOURCE_SHA256,
        "query": G0170_QUERY_SHA256,
    }
    require(coordinate.get("bindings") == expected_bindings, "G-0170 producer bindings drift")

    exact_dot = sum(
        int(hinge[int(term["sequence"])])
        * canonical_integer(term["coefficient"], f"term {index} coefficient")
        for index, term in enumerate(terms)
    )
    require(exact_dot == frozen_residual, "independent G-0170 exact dot bridge failed")
    require(
        bridge.get("schema") == "max11-g0170-first-fresh-direction-bridge-v1"
        and bridge.get("result") == "EXACT_PRICE_DOT_BRIDGE_PASS"
        and bridge.get("direction") == direction
        and bridge.get("records") == RECORDS
        and bridge.get("candidate_terms") == 304
        and bridge.get("hinge_coefficients_i64_le_sha256") == FIRST_ROW_I64_SHA256
        and canonical_integer(bridge.get("exact_candidate_dot"), "bridge dot") == exact_dot
        and canonical_integer(bridge.get("frozen_global_residual"), "bridge residual")
        == frozen_residual
        and bridge.get("exact_dot_matches_frozen_residual") is True
        and bridge.get("coordinate_digest_recomputed") is True
        and bridge.get("coordinate_census_recomputed") is True
        and bridge.get("all_frozen_bindings_rehashed") is True
        and bridge.get("augmented_rank_computation_run") is False,
        "G-0170 bridge contract drift",
    )

    return {
        "member": member,
        "global_result": global_result,
        "query": query,
        "coordinate": coordinate,
        "bridge": bridge,
        "basis_sequences": [int(value) for value in basis_sequences],
        "coordinate_rows": [int(value) for value in coordinate_rows],
        "coefficients": coefficients,
        "target": target,
        "current_scale": current_scale,
        "direction": direction,
        "frozen_residual": frozen_residual,
        "hinge": [int(value) for value in hinge],
    }


def validate_source_audit() -> dict[str, Any]:
    require(SOURCE_AUDIT_PREREGISTRATION_PATH.is_file(), "source-audit preregistration missing")
    require(SOURCE_AUDIT_PATH.is_file(), "source-audit receipt missing")
    receipt = load_json(SOURCE_AUDIT_PATH)
    expected_keys = {
        "schema",
        "verdict",
        "result",
        "evidence_class",
        "claim_boundary",
        "reviewer",
        "audit_preregistration",
        "subject",
        "required_checks",
        "scientific_manifest_observed",
        "scientific_input_observed",
        "scientific_output_observed",
        "scientific_run_executed",
        "no_claim",
    }
    require(set(receipt) == expected_keys, "source-audit top-level contract drift")
    reviewer = receipt.get("reviewer")
    require(
        isinstance(reviewer, dict)
        and set(reviewer) == {"agent_name", "model"}
        and isinstance(reviewer.get("agent_name"), str)
        and reviewer["agent_name"] not in {"", "ScarletCave"}
        and isinstance(reviewer.get("model"), str)
        and reviewer["model"],
        "source-audit reviewer is not fresh",
    )
    expected_subject = {
        "preregistration": commit_binding(PREREGISTRATION_PATH),
        "producer": commit_binding(SCRIPT),
        "g0164_solver": commit_binding(G0164_SOLVER_PATH),
        "g0140_selector": commit_binding(G0140_SELECTOR_PATH),
    }
    require(
        receipt.get("schema") == SOURCE_AUDIT_SCHEMA
        and receipt.get("verdict") == "PASS"
        and receipt.get("result") == SOURCE_AUDIT_RESULT
        and receipt.get("evidence_class") == SOURCE_AUDIT_EVIDENCE
        and receipt.get("claim_boundary") == SOURCE_AUDIT_CLAIM_BOUNDARY
        and receipt.get("subject") == expected_subject
        and receipt.get("required_checks") == SOURCE_AUDIT_REQUIRED_CHECKS
        and receipt.get("scientific_manifest_observed") is False
        and receipt.get("scientific_input_observed") is False
        and receipt.get("scientific_output_observed") is False
        and receipt.get("scientific_run_executed") is False
        and receipt.get("no_claim") == SOURCE_AUDIT_NO_CLAIM,
        "source-audit typed PASS gate failed",
    )
    audit_preregistration = receipt.get("audit_preregistration")
    require(
        audit_preregistration == commit_binding(SOURCE_AUDIT_PREREGISTRATION_PATH),
        "source-audit preregistration binding drift",
    )
    producer_commit = git_commit_for_path(SCRIPT)
    audit_prereg_commit = git_commit_for_path(SOURCE_AUDIT_PREREGISTRATION_PATH)
    audit_commit = git_commit_for_path(SOURCE_AUDIT_PATH)
    git_is_ancestor(producer_commit, audit_prereg_commit, "producer -> audit preregistration")
    git_is_ancestor(audit_prereg_commit, audit_commit, "audit preregistration -> audit receipt")
    return receipt


def collect_snapshot(
    static: dict[str, Any], solver: Any, state: dict[str, Any], *, require_audit: bool
) -> dict[str, str]:
    snapshot = dict(solver.collect_snapshot(state, require_audit=True))
    for path, expected, label in [
        (PREREGISTRATION_PATH, PREREGISTRATION_SHA256, "G-0168 preregistration"),
        (SCRIPT, sha256_path(SCRIPT), "G-0168 producer"),
        (G0164_SOLVER_PATH, G0164_SOLVER_SHA256, "G-0164 solver"),
        (G0164_MEMBER_PATH, G0164_MEMBER_SHA256, "G-0164 member"),
        (G0164_GLOBAL_PATH, G0164_GLOBAL_SHA256, "G-0164 global result"),
        (G0140_SELECTOR_PATH, G0140_SELECTOR_SHA256, "G-0140 selector"),
        (G0140_STAGE_B_PATH, G0140_STAGE_B_SHA256, "G-0140 Stage B"),
        (G0140_STAGE_C_PATH, G0140_STAGE_C_SHA256, "G-0140 Stage C"),
        (
            G0170_PREREGISTRATION_PATH,
            G0170_PREREGISTRATION_SHA256,
            "G-0170 preregistration",
        ),
        (G0170_QUERY_PATH, G0170_QUERY_SHA256, "G-0170 query"),
        (G0170_COORDINATE_PATH, G0170_COORDINATE_SHA256, "G-0170 coordinate"),
        (G0170_BRIDGE_PATH, G0170_BRIDGE_SHA256, "G-0170 bridge"),
        (G0117_CARGO_PATH, G0117_CARGO_SHA256, "G-0117 Cargo manifest"),
        (G0117_SOURCE_PATH, G0117_SOURCE_SHA256, "G-0117 coordinate source"),
        (G0117_KERNEL_PATH, G0117_KERNEL_SHA256, "G-0117 kernel"),
        (G0117_EXECUTABLE_PATH, G0117_EXECUTABLE_SHA256, "G-0117 executable"),
    ]:
        snapshot_add(snapshot, path, expected, label)
    if require_audit:
        validate_source_audit()
        snapshot_add(
            snapshot,
            SOURCE_AUDIT_PREREGISTRATION_PATH,
            sha256_path(SOURCE_AUDIT_PREREGISTRATION_PATH),
            "G-0171 preregistration",
        )
        snapshot_add(
            snapshot,
            SOURCE_AUDIT_PATH,
            sha256_path(SOURCE_AUDIT_PATH),
            "G-0171 source audit",
        )
    # Keep the argument live: callers cannot accidentally collect custody for
    # a different static-input object.
    require(static["frozen_residual"] != 0, "static residual gate drift")
    return snapshot


def expected_manifest(snapshot: dict[str, str]) -> dict[str, Any]:
    return {
        "schema": MANIFEST_SCHEMA,
        "result": "FROZEN_BEFORE_G0168_FIRST_ROW_EXACT_ADMISSION",
        "claim_boundary": CLAIM_BOUNDARY,
        "preregistration": commit_binding(PREREGISTRATION_PATH),
        "producer": commit_binding(SCRIPT),
        "source_audit": commit_binding(SOURCE_AUDIT_PATH),
        "g0164_member": commit_binding(G0164_MEMBER_PATH),
        "g0164_global_result": commit_binding(G0164_GLOBAL_PATH),
        "g0170_preregistration": commit_binding(G0170_PREREGISTRATION_PATH),
        "g0170_query": commit_binding(G0170_QUERY_PATH),
        "g0170_coordinate": commit_binding(G0170_COORDINATE_PATH),
        "g0170_bridge": commit_binding(G0170_BRIDGE_PATH),
        "parameters": {
            "n": N,
            "records": RECORDS,
            "old_rows": OLD_ROWS,
            "appended_rows": NEW_ROWS,
            "rows": ROWS,
            "old_rank": OLD_RANK,
            "basis_sequences_u64le_sha256": BASIS_SEQUENCES_SHA256,
            "basis_i128le_sha256": BASIS_MATRIX_SHA256,
            "square_i128le_sha256": SQUARE_MATRIX_SHA256,
            "target_i128le_sha256": TARGET_SHA256,
            "first_row_i64le_sha256": FIRST_ROW_I64_SHA256,
            "column_order": "canonical_sequence_0_through_163739",
            "arithmetic": "python_flint_exact_Q_and_unbounded_Python_int",
            "fixed_modular_primes_diagnostic_only": list(FIXED_MODULAR_PRIMES),
        },
        "input_snapshot": dict(sorted(snapshot.items())),
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "planned_output": {
            "path": relative(OUTPUT_PATH),
            "schema": OUTPUT_SCHEMA,
            "allowed_results": [RANK_RESULT, DEPENDENCY_RESULT],
        },
        "scientific_run_executed": False,
        "scientific_output_created": False,
    }


def prepare_state(*, require_audit: bool) -> tuple[dict[str, Any], Any, dict[str, Any], dict[str, str]]:
    static = validate_static_inputs()
    solver = load_module(G0164_SOLVER_PATH, "g0168_g0164_solver")
    state = solver.validate_sealed_inputs()
    require(
        state["sequences"] == static["basis_sequences"]
        and state["coordinate_rows"] == static["coordinate_rows"]
        and state["target"] == static["target"],
        "G-0164 reconstructed state disagrees with finite member",
    )
    snapshot = collect_snapshot(static, solver, state, require_audit=require_audit)
    return static, solver, state, snapshot


def validate_manifest() -> tuple[dict[str, Any], dict[str, Any], Any, dict[str, Any], dict[str, str]]:
    require(MANIFEST_PATH.is_file(), "G-0168 scientific manifest missing")
    static, solver, state, snapshot = prepare_state(require_audit=True)
    manifest = load_json(MANIFEST_PATH)
    require(manifest == expected_manifest(snapshot), "G-0168 manifest contract drift")
    manifest_commit = git_commit_for_path(MANIFEST_PATH)
    audit_commit = git_commit_for_path(SOURCE_AUDIT_PATH)
    git_is_ancestor(audit_commit, manifest_commit, "source audit -> scientific manifest")
    require(not OUTPUT_PATH.exists(), "scientific output already exists")
    return manifest, static, solver, state, snapshot


def write_exclusive(path: Path, value: object) -> None:
    path = contained(path)
    require(path == OUTPUT_PATH, "output path drift")
    require(path.parent.is_dir(), "output parent missing")
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    temporary: Path | None = None
    try:
        descriptor, raw = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(raw)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        os.link(temporary, path)
        temporary.unlink()
        temporary = None
    except FileExistsError as error:
        raise AdmissionError(f"refusing to overwrite {relative(path)}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def scientific_run() -> dict[str, Any]:
    require(not OUTPUT_PATH.exists(), "refusing to overwrite scientific output")
    self_test()
    manifest, static, solver, state, snapshot = validate_manifest()
    started = time.perf_counter()

    matrix_rows = solver.reconstruct_basis(state)
    require(
        len(matrix_rows) == OLD_ROWS
        and all(len(row) == OLD_RANK for row in matrix_rows)
        and digest_i128(value for row in matrix_rows for value in row) == BASIS_MATRIX_SHA256,
        "reconstructed old basis matrix drift",
    )
    square_rows = [matrix_rows[row] for row in static["coordinate_rows"]]
    require(
        digest_i128(value for row in square_rows for value in row) == SQUARE_MATRIX_SHA256,
        "reconstructed old square drift",
    )
    hinge_on_basis = [static["hinge"][sequence] for sequence in static["basis_sequences"]]
    relation = solve_relation(square_rows, hinge_on_basis)

    residual_digest = hashlib.sha256()
    scanned = 0
    result: str | None = None
    branch: dict[str, Any] | None = None
    first_modular_nonzero: dict[int, int | None] = {
        prime: None for prime in FIXED_MODULAR_PRIMES
    }

    g0135_prepared = state["g0135_prepared"]
    g0135_producer = state["g0135_producer"]
    ancestor = g0135_prepared["ancestor"]
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, inherited_loader = g0135_producer.validate_warm_start(
            g0135_prepared, cache
        )
        require(warm_receipt == state["warm_receipt"], "G-0135 warm loader drift")
        for sequence in range(RECORDS):
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(int(row[sequence]) for row in state["all_pool_rows"])
            require(len(column) == OLD_ROWS, f"old column width drift at {sequence}")
            coordinates = [column[row] for row in static["coordinate_rows"]]
            delta = exact_delta_numerator(
                coordinates,
                static["hinge"][sequence],
                relation["relation"],
                relation["scale"],
            )
            residual_digest.update(str(delta).encode("ascii"))
            residual_digest.update(b"\n")
            scanned += 1
            for prime in FIXED_MODULAR_PRIMES:
                if first_modular_nonzero[prime] is None and delta % prime:
                    first_modular_nonzero[prime] = sequence
            if delta:
                result = RANK_RESULT
                branch = exact_rank_branch(
                    matrix_rows,
                    square_rows,
                    static["target"],
                    static["basis_sequences"],
                    static["coordinate_rows"],
                    static["hinge"],
                    relation,
                    sequence,
                    column,
                    delta,
                    static["coefficients"],
                    static["current_scale"],
                    static["frozen_residual"],
                )
                break

    if result is None:
        require(scanned == RECORDS, "dependency branch truncated the family scan")
        result = DEPENDENCY_RESULT
        branch = exact_dependency_branch(
            static["target"],
            static["coordinate_rows"],
            relation,
            static["current_scale"],
            static["frozen_residual"],
            scanned,
            residual_digest.hexdigest(),
        )
    else:
        require(branch is not None and scanned == branch["witness_sequence"] + 1, "witness order drift")

    require(branch is not None, "scientific branch missing")
    rehash_snapshot(snapshot)
    require(load_json(MANIFEST_PATH) == manifest, "manifest changed during scientific run")
    output = {
        "schema": OUTPUT_SCHEMA,
        "result": result,
        "claim_boundary": CLAIM_BOUNDARY,
        "manifest": {
            **commit_binding(MANIFEST_PATH),
        },
        "preregistration": commit_binding(PREREGISTRATION_PATH),
        "producer": commit_binding(SCRIPT),
        "source_audit": commit_binding(SOURCE_AUDIT_PATH),
        "g0164_member": commit_binding(G0164_MEMBER_PATH),
        "g0164_global_result": commit_binding(G0164_GLOBAL_PATH),
        "g0170_coordinate": commit_binding(G0170_COORDINATE_PATH),
        "g0170_bridge": commit_binding(G0170_BRIDGE_PATH),
        "source_and_input_bindings": {
            path: {"path": path, "sha256": value}
            for path, value in sorted(snapshot.items())
        },
        "n": N,
        "records": RECORDS,
        "old_rows": OLD_ROWS,
        "appended_rows": NEW_ROWS,
        "rows": ROWS,
        "old_rank": OLD_RANK,
        "direction": static["direction"],
        "frozen_primitive_member_residual": str(static["frozen_residual"]),
        "frozen_member_target_scale": str(static["current_scale"]),
        "exact_dot_bridge_replayed": True,
        "basis_sequences": static["basis_sequences"],
        "basis_sequences_u64le_sha256": BASIS_SEQUENCES_SHA256,
        "coordinate_rows": static["coordinate_rows"],
        "basis_i128le_sha256": BASIS_MATRIX_SHA256,
        "square_i128le_sha256": SQUARE_MATRIX_SHA256,
        "relation": {
            "old_coordinate_rows": static["coordinate_rows"],
            "integer_coefficients": [str(value) for value in relation["relation"]],
            "hinge_scale": str(relation["scale"]),
            "basis_relation_exactly_replayed": True,
        },
        "canonical_columns_scanned": scanned,
        "first_modular_nonzero_diagnostics": {
            str(prime): sequence for prime, sequence in first_modular_nonzero.items()
        },
        "modular_role": "DIAGNOSTIC_ONLY_NEVER_A_DECISION",
        "branch": branch,
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "inputs_rehashed_at_end": True,
        "manifest_rehashed_at_end": True,
        "no_automatic_fresh128_run": True,
        "wall_seconds": time.perf_counter() - started,
        "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    write_exclusive(OUTPUT_PATH, output)
    return output


def static_preflight() -> dict[str, Any]:
    self_test()
    static = validate_static_inputs()
    return {
        "status": "STATIC_PREFLIGHT_PASS",
        "records": RECORDS,
        "old_rows": OLD_ROWS,
        "old_rank": OLD_RANK,
        "basis_columns": len(static["basis_sequences"]),
        "coordinate_rows": len(static["coordinate_rows"]),
        "g0170_dot_bridge_replayed": True,
        "scientific_manifest_consumed": False,
        "schur_solve_run": False,
        "scientific_output_created": False,
    }


def print_manifest_template() -> dict[str, Any]:
    _static, _solver, _state, snapshot = prepare_state(require_audit=True)
    return expected_manifest(snapshot)


def preflight() -> dict[str, Any]:
    self_test()
    manifest, static, _solver, _state, snapshot = validate_manifest()
    return {
        "status": "PREFLIGHT_PASS",
        "manifest_sha256": sha256_path(MANIFEST_PATH),
        "input_snapshot_sha256": input_snapshot_digest(snapshot),
        "basis_columns": len(static["basis_sequences"]),
        "allowed_results": manifest["planned_output"]["allowed_results"],
        "schur_solve_run": False,
        "scientific_output_created": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--static-preflight", action="store_true")
    modes.add_argument("--print-manifest-template", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    modes.add_argument("--run", action="store_true")
    arguments = parser.parse_args(argv)

    if arguments.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if arguments.static_preflight:
        print(json.dumps(static_preflight(), sort_keys=True))
        return 0
    if arguments.print_manifest_template:
        print(json.dumps(print_manifest_template(), sort_keys=True, separators=(",", ":")))
        return 0
    if arguments.preflight:
        print(json.dumps(preflight(), sort_keys=True))
        return 0
    if arguments.run:
        output = scientific_run()
        print(
            json.dumps(
                {
                    "schema": output["schema"],
                    "result": output["result"],
                    "output": relative(OUTPUT_PATH),
                    "sha256": sha256_path(OUTPUT_PATH),
                },
                sort_keys=True,
            )
        )
        return 0
    raise AssertionError("unreachable CLI mode")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AdmissionError, OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"G-0168 invalid: {error}", file=sys.stderr)
        raise SystemExit(2) from error
