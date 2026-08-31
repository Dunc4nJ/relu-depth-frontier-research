#!/usr/bin/env python3
"""Outcome-blind exact complete-matrix rank selector for G-0140 Stage C.

The scientific Pool128 price receipt does not exist when this source is frozen.
Consequently no scientific execution is performed while this source is being
frozen.  The producer nevertheless exposes the complete future run path:

* ``--self-test`` runs small exact fixtures and hostile controls;
* ``--interface`` prints the frozen future input/output contract; and
* ``--static-preflight`` checks the frozen local implementation without future
  scientific inputs;
* ``--preflight`` validates future inputs and the inherited G-0135 loader, but
  never scans the scientific matrix or writes a result; and
* the default four-path mode performs the frozen scientific Stage-C run once
  all source audits and prior-stage receipts exist.

The reusable core below certifies a complete exact-Q column basis, computes the
complete row-prefix rank transcript, selects the first rank-growing rows, and
constructs compatible or incompatible dependency certificates.  Modular
arithmetic is represented only by proposal records; all decisions are repeated
and certified with exact integer/rational arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import mmap
import os
import platform
import resource
import struct
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

import flint
from flint import fmpq_mat, fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPT = Path(__file__).resolve()
NATIVE_PROPOSER_SOURCE_PATH = HERE / "ffpack_modular_pivots.cpp"
NATIVE_PROPOSER_PATH = HERE / "ffpack_modular_pivots_v1"
NATIVE_BUILD_RECEIPT_PATH = HERE / "ffpack_modular_pivots_v1.build.json"
NATIVE_TEST_PATH = HERE / "test_ffpack_modular_pivots_v1.py"
LAUNCHER_PATH = HERE / "run-stage-c-selector-v1"

PREREGISTRATION_PATH = ROOT / "artifacts/math/G-0140/PREREGISTRATION.md"
MANIFEST_PATH = ROOT / "artifacts/math/G-0140/pool128_manifest_v1.json"
STAGE_A_PATH = ROOT / "artifacts/math/G-0140/pool128_global_replay_v1.json"
STAGE_B_PATH = ROOT / "artifacts/math/G-0140/pool128_coordinate_prices_v1.json"
OUTPUT_PATH = ROOT / "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json"
MASTER_OUTPUT_PATH = ROOT / "artifacts/math/G-0140/rank_aware_master_result_v1.json"
GLOBAL_REPLAY_OUTPUT_PATH = (
    ROOT / "artifacts/math/G-0140/new_member_global_replay_v1.json"
)

G0135_SOURCE_PATH = (
    ROOT / "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py"
)
G0135_RESULT_PATH = ROOT / "artifacts/math/G-0135/full_family_master_result_v3.json"
G0135_STAGE_D_PATH = ROOT / "artifacts/math/G-0135/new_member_global_replay_v1.json"
G0135_MANIFEST_PATH = (
    ROOT / "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json"
)
G0135_STAGE_A_PATH = ROOT / "artifacts/math/G-0135/batch32_global_replay_v1.json"
G0135_STAGE_B_PATH = ROOT / "artifacts/math/G-0135/batch32_coordinate_prices_v1.json"
G0117_EXACT_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"
G0139_RECEIPT_PATH = (
    ROOT / "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json"
)
G0150_SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0150-g0140-stage-a-final2-source/SOURCE_AUDIT_RECEIPT.json"
)
G0150_AUDIT_PREREGISTRATION_PATH = (
    ROOT
    / "artifacts/reviews/G-0150-g0140-stage-a-final2-source/PREREGISTRATION.md"
)
STAGE_B_SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0158-g0140-stage-b-final3-source/SOURCE_AUDIT_RECEIPT.json"
)
STAGE_B_AUDIT_PREREGISTRATION_PATH = (
    ROOT
    / "artifacts/reviews/G-0158-g0140-stage-b-final3-source/PREREGISTRATION.md"
)
STAGE_C_SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0159-g0140-stage-c-final4-source/SOURCE_AUDIT_RECEIPT.json"
)
STAGE_C_AUDIT_PREREGISTRATION_PATH = (
    ROOT
    / "artifacts/reviews/G-0159-g0140-stage-c-final4-source/PREREGISTRATION.md"
)

STAGE_A_SOURCE_PATH = ROOT / "artifacts/math/G-0140/stage_a_pool/src/main.rs"
STAGE_B_SOURCE_PATH = ROOT / "artifacts/math/G-0140/stage_b_pricer/src/main.rs"

REQUIREMENTS_PATH = ROOT / "requirements-solvers.lock"
PYTHON_WHEEL_HASHES_PATH = ROOT / "environment/python-wheel-hashes.txt"
TOOLCHAIN_MANIFEST_PATH = ROOT / "environment/toolchain-manifest.txt"
TOOLCHAIN_PATH = ROOT / "TOOLCHAIN.md"

N = 11
RECORDS = 163_740
BASE_ROWS = 412
POOL_ROWS = 128
LOGICAL_ROWS = BASE_ROWS + POOL_ROWS
ADMIT_ROWS = 32

PREREGISTRATION_COMMIT = "af7ff480359c59544293c492b8f2913ab94773a2"
PREREGISTRATION_SHA256 = (
    "e358f0ef9a6dcdcc798ec3cee780f3d220200bf70a2eaf2755060354e28dddb4"
)
G0135_SOURCE_SHA256 = (
    "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"
)
G0135_RESULT_SHA256 = (
    "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8"
)
G0135_STAGE_D_SHA256 = (
    "d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875"
)
G0135_STAGE_D_COMMIT = "270a62455097cbaf0a8f80426c54b6121d1afcba"
G0139_RECEIPT_SHA256 = (
    "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f"
)
G0139_RECEIPT_COMMIT = "0bfdbf2db065d8517ad2d98d762473fed052cb54"
G0139_EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT"
G0139_CLAIM_BOUNDARY = "Consistency only for the exact committed 135-term Stage-C member and exact G-0135 Stage-D result bytes. Same-lineage outcome-aware T1 evidence; no T2 independence, family completeness, frozen-family nonmembership, MAX11 lower bound, unrestricted nonrepresentability, all-n theorem, refereed status, formalization, or Lean theorem."
G0138_SOURCE_AUDIT_RELATIVE_PATH = (
    "artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json"
)
G0138_SOURCE_AUDIT_SHA256 = (
    "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944"
)
G0117_EXACT_SHA256 = (
    "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281"
)
REQUIREMENTS_SHA256 = (
    "dae95ec0dd59c0b30ea69bfe541248049cee612a92d56c4d18e0c3217c170fb8"
)
PYTHON_WHEEL_HASHES_SHA256 = (
    "68c90da2eecf3285c99ad135ef142070c830fe4b14a4a35ebec265e6ffb3b311"
)
TOOLCHAIN_MANIFEST_SHA256 = (
    "a4e7b09efb4d445b9a34217f0aff478771c36542ca8c4d58e5b15e9d6273b81e"
)
TOOLCHAIN_SHA256 = (
    "ffc55f711d52c90f4a1710cfd55366b2d1249a736db97f17c3a1c3e52188f150"
)

MANIFEST_SCHEMA = "max11-g0140-rank-aware-manifest-v1"
STAGE_A_SCHEMA = "max11-g0140-pool128-global-replay-v1"
STAGE_B_SCHEMA = "max11-g0140-pool128-coordinate-prices-v1"
OUTPUT_SCHEMA = "max11-g0140-pool128-exact-rank-selection-v1"
MASTER_OUTPUT_SCHEMA = "max11-g0140-rank-aware-master-result-v1"
GLOBAL_REPLAY_OUTPUT_SCHEMA = "max11-g0140-new-member-global-replay-v1"
G0139_SCHEMA = "max11-g0139-g0135-result-audit-v1"
G0150_SCHEMA = "max11-g0150-g0140-stage-a-final2-source-audit-v1"
STAGE_B_SOURCE_AUDIT_SCHEMA = "max11-g0158-g0140-stage-b-final3-source-audit-v1"
STAGE_C_SOURCE_AUDIT_SCHEMA = "max11-g0159-g0140-stage-c-final4-source-audit-v1"
SOURCE_CUSTODY_PASS_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
SOURCE_AUDIT_EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
G0150_CLAIM_BOUNDARY = "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted."
STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY = "T1 source/custody clearance for the exact frozen Stage-B producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted."
STAGE_C_SOURCE_AUDIT_CLAIM_BOUNDARY = "T1 source/custody clearance for the exact frozen Stage-C producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted."
G0150_NO_CLAIM = "This source audit does not adjudicate a G-0140 scientific manifest or result, establish or exclude a Pool128 member, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem."
STAGE_B_SOURCE_AUDIT_NO_CLAIM = "This source audit does not adjudicate a G-0140 scientific manifest or result, establish or exclude a Pool128 coordinate matrix or exact-rank selection, validate family completeness, prove a MAX11 lower bound, settle unrestricted two-hidden-layer representation, establish minimality, prove an all-n statement, or supply a Lean theorem."
STAGE_C_SOURCE_AUDIT_NO_CLAIM = "This source audit does not adjudicate any future G-0140 scientific manifest or result and does not establish family membership, family nonmembership, a MAX11 lower bound, unrestricted nonrepresentability, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem."
G0150_REQUIRED_CHECKS = {
    "exact_named_binding_contract": True,
    "displaced_recursive_lookalikes_rejected": True,
    "correct_decoy_with_missing_named_binding_rejected": True,
    "duplicate_path_occurrences_rejected": True,
    "unknown_envelope_fields_rejected": True,
    "audit_git_commit_rejected": True,
    "duplicate_json_keys_rejected": True,
    "trailing_json_data_rejected": True,
    "producer_self_test_passed": True,
    "producer_static_preflight_passed": True,
    "producer_ancestor_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}
STAGE_B_SOURCE_AUDIT_REQUIRED_CHECKS = {
    "exact_named_binding_contract": True,
    "displaced_recursive_lookalikes_rejected": True,
    "correct_decoy_with_missing_named_binding_rejected": True,
    "duplicate_path_occurrences_rejected": True,
    "unknown_envelope_fields_rejected": True,
    "audit_git_commit_rejected": True,
    "duplicate_json_keys_rejected": True,
    "trailing_json_data_rejected": True,
    "stage_a_missing_nullable_field_rejected": True,
    "stage_a_mutation_control_schemas_validated": True,
    "stage_a_source_audit_exact_contract_validated": True,
    "g0139_subject_and_exact_fixed_inputs_gate_verified": True,
    "compiled_source_manifest_lock_match_working_bytes": True,
    "overwrite_refusal_verified": True,
    "end_rehash_verified": True,
    "bigint_unconditional_paths_verified": True,
    "producer_self_test_passed": True,
    "producer_static_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}
STAGE_C_SOURCE_AUDIT_REQUIRED_CHECKS = {
    "exact_named_binding_contract": True,
    "displaced_recursive_lookalikes_rejected": True,
    "correct_decoy_with_missing_named_binding_rejected": True,
    "duplicate_path_occurrences_rejected": True,
    "unknown_envelope_fields_rejected": True,
    "audit_git_commit_rejected": True,
    "duplicate_json_keys_rejected": True,
    "trailing_json_data_rejected": True,
    "complete_basis_protocol_verified": True,
    "full_pool_dependency_compatibility_scan_verified": True,
    "committed_blob_custody_verified": True,
    "native_build_custody_verified": True,
    "g0139_subject_and_exact_fixed_inputs_gate_verified": True,
    "stage_b_final3_source_audit_exact_contract_validated": True,
    "producer_self_test_passed": True,
    "native_oracle_passed": True,
    "producer_static_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}
NATIVE_PROPOSER_SCHEMA = "max11-g0140-ffpack-modular-pivots-v1"
NATIVE_EXECUTION_SCHEMA = "max11-g0140-native-modular-proposal-receipt-v1"
NATIVE_BUILD_SCHEMA = "max11-g0140-ffpack-native-build-v1"
NATIVE_BUILD_COMMAND = (
    "g++ -O2 -std=c++17 -fopenmp "
    "artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots.cpp "
    "-o artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1 "
    "-lblas -llapack -lgivaro -lgmpxx -lgmp"
)

STAGE_ORDER = [
    "A_REPLAY_POOL128",
    "B_PRICE_POOL128",
    "C_COMPLETE_MATRIX_RANK_SELECT",
    "D_REOPENED_EXACT_MASTER",
    "E_GLOBAL_REPLAY_IF_MEMBER",
]
PLANNED_OUTPUTS = {
    "A": {"path": "artifacts/math/G-0140/pool128_global_replay_v1.json", "schema": STAGE_A_SCHEMA},
    "B": {"path": "artifacts/math/G-0140/pool128_coordinate_prices_v1.json", "schema": STAGE_B_SCHEMA},
    "C": {"path": "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json", "schema": OUTPUT_SCHEMA},
    "D": {"path": "artifacts/math/G-0140/rank_aware_master_result_v1.json", "schema": MASTER_OUTPUT_SCHEMA},
    "E": {"path": "artifacts/math/G-0140/new_member_global_replay_v1.json", "schema": GLOBAL_REPLAY_OUTPUT_SCHEMA},
}
MANIFEST_PARAMETERS = {
    "n": N,
    "records": RECORDS,
    "existing_rows": BASE_ROWS,
    "existing_terms": 135,
    "accumulated_hinge_rows": 100,
    "pool_k": POOL_ROWS,
    "max_admitted_rows": ADMIT_ROWS,
    "threads": 12,
    "arithmetic": "signed_num_bigint_BigInt_and_exact_Q",
    "direction_order": "ordinary_signed_i8_tuple_lexicographic",
    "column_order": "canonical_sequence_0_through_163739",
}

# These primes are frozen only as proposal lanes.  A prime can miss exact rank
# (for example when every witness minor is divisible by it); exact completion
# must repair every such miss.
FIXED_MODULAR_PRIMES = (1_000_003, 1_000_033, 1_000_037)
MODULAR_ROLE = "WORK_ORDER_PROPOSAL_ONLY_NEVER_A_DECISION"


class SelectorError(RuntimeError):
    """Fail-closed validation or exact-arithmetic error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SelectorError(message)


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_text(raw: str, label: str) -> object:
    try:
        return json.loads(raw, object_pairs_hook=no_duplicate_object)
    except json.JSONDecodeError as error:
        raise SelectorError(f"malformed or trailing JSON in {label}: {error}") from error


def load_json(path: Path) -> dict[str, Any]:
    value = strict_json_text(path.read_text(encoding="utf-8"), str(path))
    require(isinstance(value, dict), f"top-level JSON object required: {path}")
    return value


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_digest(actual: str, expected: str, label: str) -> None:
    require(is_sha256(actual) and actual == expected, f"{label} SHA-256 drift")


def contained(path: Path) -> Path:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT)
    except ValueError as error:
        raise SelectorError(f"path escapes workspace: {path}") from error
    require(not path.is_symlink(), f"symlink input refused: {path}")
    return resolved


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    require(
        specification is not None and specification.loader is not None,
        f"cannot import module: {path}",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def canonical_integer(
    value: object,
    label: str,
    *,
    positive: bool = False,
    nonzero: bool = False,
) -> int:
    require(isinstance(value, str), f"{label} must be a decimal string")
    try:
        integer = int(value)
    except ValueError as error:
        raise SelectorError(f"{label} is not an integer") from error
    require(str(integer) == value, f"{label} is not canonical signed decimal")
    if positive:
        require(integer > 0, f"{label} must be positive")
    if nonzero:
        require(integer != 0, f"{label} must be nonzero")
    return integer


def canonical_fraction(value: Fraction) -> str:
    value = Fraction(value)
    return str(value.numerator) if value.denominator == 1 else str(value)


def digest_i64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        integer = int(value)
        require(-(1 << 63) <= integer < (1 << 63), "i64 digest input overflow")
        digest.update(integer.to_bytes(8, "little", signed=True))
    return digest.hexdigest()


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        integer = int(value)
        require(-(1 << 127) <= integer < (1 << 127), "i128 digest input overflow")
        digest.update(integer.to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_u64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        integer = int(value)
        require(0 <= integer < 1 << 64, "u64 digest input overflow")
        digest.update(integer.to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def digest_decimal_lf(values: Iterable[int | str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        rendered = str(value)
        require(str(int(rendered)) == rendered, "noncanonical decimal digest input")
        digest.update(rendered.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def digest_fraction_lf(values: Iterable[Fraction]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(canonical_fraction(Fraction(value)).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def digest_directions(directions: Sequence[Sequence[int]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        require(len(direction) == N, "direction digest width drift")
        for coordinate in direction:
            require(
                isinstance(coordinate, int)
                and not isinstance(coordinate, bool)
                and -(1 << 7) <= coordinate < (1 << 7),
                "direction digest coordinate is not i8",
            )
            digest.update(int(coordinate).to_bytes(1, "little", signed=True))
    return digest.hexdigest()


def input_snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(snapshot.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\t")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    path = contained(path)
    require(path.parent.is_dir(), "output parent is missing")
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    temporary: Path | None = None
    try:
        descriptor, raw_temporary = tempfile.mkstemp(
            prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
        )
        temporary = Path(raw_temporary)
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(encoded)
            destination.flush()
            os.fsync(destination.fileno())
        os.link(temporary, path)
        temporary.unlink()
        temporary = None
    except FileExistsError as error:
        raise SelectorError(f"refusing to overwrite output: {path}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def qmatrix(integer_rows: Sequence[Sequence[int]]) -> fmpq_mat:
    require(bool(integer_rows), "exact matrix must have at least one row")
    columns = len(integer_rows[0])
    require(
        columns > 0 and all(len(row) == columns for row in integer_rows),
        "exact matrix is empty or ragged",
    )
    return fmpq_mat(fmpz_mat([[int(value) for value in row] for row in integer_rows]))


def pivot_columns(reduced: fmpq_mat, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    cursor = 0
    for row in range(rank):
        while cursor < columns and not reduced[row, cursor]:
            cursor += 1
        require(cursor < columns, "RREF pivot extraction failed")
        pivots.append(cursor)
        cursor += 1
    return pivots


def matrix_rows(
    columns: Sequence[Sequence[int]], row_count: int
) -> list[list[int]]:
    require(
        bool(columns)
        and row_count > 0
        and all(len(column) == row_count for column in columns),
        "column family is empty or ragged",
    )
    return [
        [int(column[row]) for column in columns] for row in range(row_count)
    ]


def primitive_integer(values: Sequence[Fraction]) -> list[int]:
    require(bool(values) and any(values), "zero relation cannot be primitive")
    denominator = 1
    for value in values:
        denominator = math.lcm(denominator, Fraction(value).denominator)
    integers = [
        Fraction(value).numerator * (denominator // Fraction(value).denominator)
        for value in values
    ]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "primitive relation gcd vanished")
    integers = [value // divisor for value in integers]
    first = next(value for value in integers if value)
    if first < 0:
        integers = [-value for value in integers]
    return integers


def exact_independent_sequences(
    *,
    column_loader: Callable[[int], Sequence[int]],
    sequences: Sequence[int],
    row_count: int,
    record_count: int,
) -> tuple[list[int], list[list[int]], int]:
    ordered = sorted(set(int(sequence) for sequence in sequences))
    require(
        bool(ordered)
        and all(0 <= sequence < record_count for sequence in ordered),
        "invalid proposed column axis",
    )
    columns = [
        [int(value) for value in column_loader(sequence)] for sequence in ordered
    ]
    rows = matrix_rows(columns, row_count)
    reduced, rank = qmatrix(rows).rref()
    rank = int(rank)
    pivots = pivot_columns(reduced, rank, len(ordered))
    selected = [ordered[index] for index in pivots]
    selected_columns = [columns[index] for index in pivots]
    require(
        selected == sorted(set(selected)) and len(selected) == rank,
        "exact proposal reduction failed",
    )
    return selected, selected_columns, rank


def exact_left_annihilator(integer_rows: Sequence[Sequence[int]]) -> list[list[int]]:
    """Return a canonical primitive integer basis of null(C^T)."""

    matrix = qmatrix(integer_rows)
    row_count = matrix.nrows()
    column_count = matrix.ncols()
    reduced, rank = matrix.transpose().rref()
    rank = int(rank)
    pivots = pivot_columns(reduced, rank, row_count)
    pivot_set = set(pivots)
    annihilators: list[list[int]] = []
    for free in range(row_count):
        if free in pivot_set:
            continue
        rational = [Fraction() for _ in range(row_count)]
        rational[free] = Fraction(1)
        for equation, pivot in enumerate(pivots):
            rational[pivot] = -Fraction(str(reduced[equation, free]))
        integer = primitive_integer(rational)
        for column in range(column_count):
            require(
                sum(
                    integer[row] * int(integer_rows[row][column])
                    for row in range(row_count)
                )
                == 0,
                "left annihilator failed selected-column replay",
            )
        annihilators.append(integer)
    require(
        len(annihilators) == row_count - rank,
        "left annihilator dimension drift",
    )
    return annihilators


def scan_annihilator_prices(
    *,
    column_loader: Callable[[int], Sequence[int]],
    annihilators: Sequence[Sequence[int]],
    row_count: int,
    record_count: int,
) -> dict[str, Any]:
    require(
        bool(annihilators)
        and all(len(vector) == row_count for vector in annihilators),
        "invalid annihilator scan shape",
    )
    digest = hashlib.sha256()
    first_violation: tuple[int, int, int] | None = None
    nonzero_prices = 0
    for sequence in range(record_count):
        column = [int(value) for value in column_loader(sequence)]
        require(len(column) == row_count, "scanned column dimension drift")
        for annihilator_index, annihilator in enumerate(annihilators):
            price = sum(
                coefficient * column[row]
                for row, coefficient in enumerate(annihilator)
                if coefficient
            )
            digest.update(str(price).encode("ascii"))
            digest.update(b"\n")
            if price:
                nonzero_prices += 1
                if first_violation is None:
                    first_violation = (sequence, annihilator_index, price)
    return {
        "columns_scanned": record_count,
        "annihilators_scanned": len(annihilators),
        "prices_scanned": record_count * len(annihilators),
        "nonzero_prices": nonzero_prices,
        "prices_decimal_lf_sha256": digest.hexdigest(),
        "first_violation": first_violation,
    }


def exact_nonzero_minor(
    integer_rows: Sequence[Sequence[int]], column_sequences: Sequence[int]
) -> dict[str, Any]:
    matrix = qmatrix(integer_rows)
    rank = int(matrix.rank())
    require(
        rank == matrix.ncols() == len(column_sequences),
        "minor source is not a full-column-rank basis",
    )
    transposed, transposed_rank = matrix.transpose().rref()
    require(int(transposed_rank) == rank, "coordinate-row rank drift")
    coordinate_rows = pivot_columns(transposed, rank, matrix.nrows())
    square_rows = [
        [int(integer_rows[row][column]) for column in range(rank)]
        for row in coordinate_rows
    ]
    determinant = int(fmpz_mat(square_rows).det())
    require(determinant != 0, "exact basis minor determinant vanished")
    return {
        "rank": rank,
        "coordinate_rows": coordinate_rows,
        "column_sequences": [int(value) for value in column_sequences],
        "determinant": str(determinant),
        "square_i128le_sha256": digest_i128(
            value for row in square_rows for value in row
        ),
    }


def certify_complete_column_basis(
    *,
    column_loader: Callable[[int], Sequence[int]],
    row_count: int,
    record_count: int,
    proposed_sequences: Sequence[int],
    proposal_receipts: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """Certify an exact-Q basis of every loaded column.

    Proposal receipts affect only the initial work set.  Exact RREF removes
    proposal dependencies, and exact annihilator scans add the first missing
    canonical column until a complete basis is proved.
    """

    require(row_count > 0 and record_count > 0, "invalid logical matrix shape")
    validate_modular_proposals(
        proposal_receipts, record_count=record_count, primes=None
    )
    proposed = sorted(set(int(value) for value in proposed_sequences))
    receipt_union = sorted(
        {
            int(sequence)
            for receipt in proposal_receipts
            for sequence in receipt["selected_sequences"]
        }
    )
    require(
        proposed == receipt_union and bool(proposed),
        "proposed column union does not match modular receipts",
    )
    selected, selected_columns, rank = exact_independent_sequences(
        column_loader=column_loader,
        sequences=proposed,
        row_count=row_count,
        record_count=record_count,
    )
    initial_selected = selected[:]
    passes: list[dict[str, Any]] = []
    while True:
        rows = matrix_rows(selected_columns, row_count)
        require(int(qmatrix(rows).rank()) == len(selected), "basis rank drift")
        annihilators = exact_left_annihilator(rows)
        if not annihilators:
            require(len(selected) == row_count, "empty annihilator before full row rank")
            passes.append(
                {
                    "pass": len(passes),
                    "rank": len(selected),
                    "annihilator_dimension": 0,
                    "columns_scanned": 0,
                    "prices_scanned": 0,
                    "nonzero_prices": 0,
                    "prices_decimal_lf_sha256": digest_decimal_lf([]),
                    "first_violating_sequence": None,
                    "first_violating_annihilator": None,
                    "first_violating_price": None,
                    "full_row_rank_shortcut": True,
                    "complete": True,
                }
            )
            break

        scan = scan_annihilator_prices(
            column_loader=column_loader,
            annihilators=annihilators,
            row_count=row_count,
            record_count=record_count,
        )
        violation = scan["first_violation"]
        passes.append(
            {
                "pass": len(passes),
                "rank": len(selected),
                "annihilator_dimension": len(annihilators),
                "columns_scanned": scan["columns_scanned"],
                "prices_scanned": scan["prices_scanned"],
                "nonzero_prices": scan["nonzero_prices"],
                "prices_decimal_lf_sha256": scan[
                    "prices_decimal_lf_sha256"
                ],
                "first_violating_sequence": None if violation is None else violation[0],
                "first_violating_annihilator": (
                    None if violation is None else violation[1]
                ),
                "first_violating_price": None if violation is None else str(violation[2]),
                "full_row_rank_shortcut": False,
                "complete": violation is None,
            }
        )
        if violation is None:
            break
        sequence = int(violation[0])
        require(sequence not in selected, "annihilator violated a selected column")
        old_rank = len(selected)
        selected.append(sequence)
        selected.sort()
        selected_columns = [
            [int(value) for value in column_loader(item)] for item in selected
        ]
        rows = matrix_rows(selected_columns, row_count)
        new_rank = int(qmatrix(rows).rank())
        require(new_rank == old_rank + 1, "completion column lacked exact unit rank")
        rank = new_rank

    rows = matrix_rows(selected_columns, row_count)
    rank = int(qmatrix(rows).rank())
    require(rank == len(selected), "terminal complete basis lost independence")
    terminal = passes[-1]
    require(terminal["complete"] is True, "basis completion lacked terminal pass")
    if rank < row_count:
        require(
            terminal["columns_scanned"] == record_count
            and terminal["nonzero_prices"] == 0,
            "rank-deficient basis lacks complete exact zero scan",
        )
    minor = exact_nonzero_minor(rows, selected)
    receipt = {
        "row_count": row_count,
        "record_count": record_count,
        "modular_role": MODULAR_ROLE,
        "modular_primes": [receipt["prime"] for receipt in proposal_receipts],
        "modular_proposal_receipts": list(proposal_receipts),
        "proposed_union_sequences": proposed,
        "proposed_union_u64le_sha256": digest_u64(proposed),
        "initial_exact_basis_sequences": initial_selected,
        "initial_exact_rank": len(initial_selected),
        "completion_passes": passes,
        "basis_sequences": selected,
        "basis_sequences_u64le_sha256": digest_u64(selected),
        "basis_rank": rank,
        "basis_i128le_sha256": digest_i128(
            rows[row][column]
            for row in range(row_count)
            for column in range(rank)
        ),
        "nonzero_minor": minor,
        "all_columns_exactly_spanned": True,
        "no_modular_terminal_decision": True,
    }
    validate_completion_scan_census(receipt, record_count=record_count)
    return receipt


def validate_completion_scan_census(
    receipt: dict[str, Any], *, record_count: int
) -> None:
    passes = receipt.get("completion_passes")
    require(isinstance(passes, list) and bool(passes), "completion pass census missing")
    for index, item in enumerate(passes):
        require(
            isinstance(item, dict)
            and item.get("pass") == index
            and isinstance(item.get("rank"), int)
            and isinstance(item.get("annihilator_dimension"), int)
            and item.get("complete") in {True, False},
            f"completion pass {index} shape drift",
        )
        if item.get("full_row_rank_shortcut") is True:
            require(
                item.get("rank") == receipt.get("row_count")
                and item.get("annihilator_dimension") == 0
                and item.get("columns_scanned") == 0
                and item.get("prices_scanned") == 0
                and item.get("complete") is True,
                f"completion pass {index} full-rank shortcut drift",
            )
        else:
            require(
                item.get("columns_scanned") == record_count
                and item.get("prices_scanned")
                == record_count * item.get("annihilator_dimension"),
                f"completion pass {index} truncated full-family scan",
            )
    require(
        passes[-1].get("complete") is True
        and all(item.get("complete") is False for item in passes[:-1]),
        "completion terminal-pass ordering drift",
    )


MODULAR_PROPOSAL_KEYS = {
    "role",
    "prime",
    "rows",
    "records_scanned",
    "rank",
    "selected_sequences",
    "selected_sequences_u64le_sha256",
}


def is_prime(value: int) -> bool:
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


def validate_modular_proposals(
    receipts: Sequence[dict[str, Any]],
    *,
    record_count: int,
    primes: Sequence[int] | None,
) -> None:
    require(bool(receipts), "at least one modular proposal is required")
    observed_primes: list[int] = []
    for index, receipt in enumerate(receipts):
        require(
            isinstance(receipt, dict) and set(receipt) == MODULAR_PROPOSAL_KEYS,
            f"modular proposal {index} schema drift",
        )
        prime = receipt.get("prime")
        rows = receipt.get("rows")
        rank = receipt.get("rank")
        selected = receipt.get("selected_sequences")
        require(
            isinstance(prime, int)
            and not isinstance(prime, bool)
            and is_prime(prime),
            f"modular proposal {index} modulus is not prime",
        )
        require(
            receipt.get("role") == MODULAR_ROLE
            and isinstance(rows, int)
            and not isinstance(rows, bool)
            and rows > 0
            and receipt.get("records_scanned") == record_count
            and isinstance(rank, int)
            and not isinstance(rank, bool)
            and isinstance(selected, list)
            and selected == sorted(set(selected))
            and rank == len(selected)
            and rank <= rows
            and all(
                isinstance(sequence, int)
                and not isinstance(sequence, bool)
                and 0 <= sequence < record_count
                for sequence in selected
            )
            and receipt.get("selected_sequences_u64le_sha256")
            == digest_u64(selected),
            f"modular proposal {index} dimension/order/digest drift",
        )
        observed_primes.append(prime)
    require(
        len(observed_primes) == len(set(observed_primes)),
        "duplicate modular proposal prime",
    )
    if primes is not None:
        require(
            tuple(observed_primes) == tuple(primes),
            "modular proposal prime order drift",
        )


def modular_column_proposal(
    *,
    column_loader: Callable[[int], Sequence[int]],
    row_count: int,
    record_count: int,
    prime: int,
) -> dict[str, Any]:
    """Deterministic modular work proposal; never an exact verdict.

    This deliberately simple incremental RREF is used only by small self-test
    fixtures in this frozen prototype.  A future scientific execution may
    replace its implementation with an outcome-blind compiled proposer while
    preserving the receipt contract and the exact completion that follows.
    """

    require(is_prime(prime), "proposal modulus is not prime")
    basis: dict[int, list[int]] = {}
    selected: list[int] = []
    for sequence in range(record_count):
        raw = [int(value) for value in column_loader(sequence)]
        require(len(raw) == row_count, "modular proposal column dimension drift")
        if len(selected) == row_count:
            # Keep the declared census truthful even though no later column can
            # increase a full modular row rank.
            continue
        vector = [value % prime for value in raw]
        for pivot in sorted(basis):
            factor = vector[pivot]
            if factor:
                pivot_vector = basis[pivot]
                vector = [
                    (value - factor * pivot_value) % prime
                    for value, pivot_value in zip(vector, pivot_vector, strict=True)
                ]
        pivot = next((index for index, value in enumerate(vector) if value), None)
        if pivot is None:
            continue
        inverse = pow(vector[pivot], -1, prime)
        vector = [(value * inverse) % prime for value in vector]
        for old_pivot, old_vector in list(basis.items()):
            factor = old_vector[pivot]
            if factor:
                basis[old_pivot] = [
                    (value - factor * new_value) % prime
                    for value, new_value in zip(old_vector, vector, strict=True)
                ]
        basis[pivot] = vector
        selected.append(sequence)
    receipt = {
        "role": MODULAR_ROLE,
        "prime": prime,
        "rows": row_count,
        "records_scanned": record_count,
        "rank": len(selected),
        "selected_sequences": selected,
        "selected_sequences_u64le_sha256": digest_u64(selected),
    }
    validate_modular_proposals([receipt], record_count=record_count, primes=[prime])
    return receipt


NATIVE_STDOUT_KEYS = {
    "schema",
    "role",
    "matrix_layout",
    "byte_order",
    "transpose_rows",
    "transpose_columns",
    "prime",
    "threads",
    "rank",
    "factor_seconds",
}


def parse_native_stdout(
    raw: str,
    *,
    record_count: int,
    row_count: int,
    prime: int,
    threads: int,
) -> dict[str, Any]:
    require(raw.endswith("\n") and raw.count("\n") == 1, "native stdout framing drift")
    value = json.loads(raw, object_pairs_hook=no_duplicate_object)
    require(
        isinstance(value, dict) and set(value) == NATIVE_STDOUT_KEYS,
        "native stdout schema drift",
    )
    seconds = value.get("factor_seconds")
    require(
        value.get("schema") == NATIVE_PROPOSER_SCHEMA
        and value.get("role") == MODULAR_ROLE
        and value.get("matrix_layout") == "row_major_transpose_family_columns"
        and value.get("byte_order") == "little_endian_runtime_asserted"
        and value.get("transpose_rows") == record_count
        and value.get("transpose_columns") == row_count
        and value.get("prime") == prime
        and value.get("threads") == threads
        and isinstance(value.get("rank"), int)
        and not isinstance(value.get("rank"), bool)
        and 0 <= value["rank"] <= min(record_count, row_count)
        and isinstance(seconds, (int, float))
        and not isinstance(seconds, bool)
        and math.isfinite(float(seconds))
        and float(seconds) >= 0,
        "native stdout identity/dimension drift",
    )
    return value


def stream_modular_transposes(
    *,
    column_loader: Callable[[int], Sequence[int]],
    row_count: int,
    record_count: int,
    primes: Sequence[int],
    directory: Path,
) -> list[dict[str, Any]]:
    """Stream M^T once into one canonical signed-i32 residue lane per prime."""

    require(
        row_count > 0
        and record_count > 0
        and tuple(primes) == FIXED_MODULAR_PRIMES,
        "native modular transpose dimensions/prime order drift",
    )
    row_struct = struct.Struct(f"<{row_count}i")
    paths = [directory / f"transpose_mod_{prime}.i32le" for prime in primes]
    handles = [path.open("xb") for path in paths]
    digests = [hashlib.sha256() for _ in primes]
    try:
        for sequence in range(record_count):
            column = [int(value) for value in column_loader(sequence)]
            require(len(column) == row_count, "native transpose column width drift")
            for prime, handle, digest in zip(
                primes, handles, digests, strict=True
            ):
                encoded = row_struct.pack(*(value % prime for value in column))
                require(handle.write(encoded) == len(encoded), "native transpose write failed")
                digest.update(encoded)
        for handle in handles:
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        for handle in handles:
            handle.close()

    expected_bytes = record_count * row_count * 4
    receipts: list[dict[str, Any]] = []
    for prime, path, digest in zip(primes, paths, digests, strict=True):
        require(
            path.is_file()
            and not path.is_symlink()
            and path.stat().st_size == expected_bytes,
            "native transpose file census drift",
        )
        require_digest(sha256_path(path), digest.hexdigest(), "native transpose")
        receipts.append(
            {
                "prime": prime,
                "path": path,
                "bytes": expected_bytes,
                "i32le_sha256": digest.hexdigest(),
            }
        )
    return receipts


def invoke_native_proposer(
    *,
    binary_path: Path,
    transpose: dict[str, Any],
    row_count: int,
    record_count: int,
    threads: int,
) -> tuple[dict[str, Any], dict[str, Any]]:
    require(
        binary_path.is_file()
        and not binary_path.is_symlink()
        and os.access(binary_path, os.X_OK),
        "native proposer is missing, symlinked, or non-executable",
    )
    binary_path = binary_path.resolve()
    input_path = Path(transpose["path"])
    prime = int(transpose["prime"])
    output_path = input_path.with_suffix(".pivots.u32le")
    require(not output_path.exists(), "native pivot output collision")
    process = subprocess.run(
        [
            str(binary_path),
            str(input_path),
            str(output_path),
            str(record_count),
            str(row_count),
            str(prime),
            str(threads),
        ],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    require(
        process.returncode == 0 and process.stderr == "",
        f"native proposer failed for prime {prime}: {process.stderr.strip()}",
    )
    native = parse_native_stdout(
        process.stdout,
        record_count=record_count,
        row_count=row_count,
        prime=prime,
        threads=threads,
    )
    raw_pivots = output_path.read_bytes()
    require(
        len(raw_pivots) == 4 * native["rank"],
        "native pivot byte/rank census drift",
    )
    selected = [
        item[0] for item in struct.iter_unpack("<I", raw_pivots)
    ]
    require(
        selected == sorted(set(selected))
        and all(sequence < record_count for sequence in selected),
        "native pivot order/range drift",
    )
    proposal = {
        "role": MODULAR_ROLE,
        "prime": prime,
        "rows": row_count,
        "records_scanned": record_count,
        "rank": len(selected),
        "selected_sequences": selected,
        "selected_sequences_u64le_sha256": digest_u64(selected),
    }
    validate_modular_proposals(
        [proposal], record_count=record_count, primes=[prime]
    )
    execution = {
        "schema": NATIVE_EXECUTION_SCHEMA,
        "role": MODULAR_ROLE,
        "prime": prime,
        "threads": threads,
        "matrix_layout": "row_major_transpose_family_columns",
        "byte_order": "little_endian_runtime_asserted",
        "transpose_rows": record_count,
        "transpose_columns": row_count,
        "transpose_i32le_bytes": transpose["bytes"],
        "transpose_i32le_sha256": transpose["i32le_sha256"],
        "pivot_u32le_bytes": len(raw_pivots),
        "pivot_u32le_sha256": hashlib.sha256(raw_pivots).hexdigest(),
        "rank": len(selected),
        "selected_sequences_u64le_sha256": digest_u64(selected),
        "native_stdout": native,
    }
    return proposal, execution


def native_modular_proposals(
    *,
    column_loader: Callable[[int], Sequence[int]],
    row_count: int,
    record_count: int,
    threads: int,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    require(threads == MANIFEST_PARAMETERS["threads"], "native thread count drift")
    with tempfile.TemporaryDirectory(prefix="g0140-stage-c-modular-") as raw_directory:
        directory = Path(raw_directory)
        transposes = stream_modular_transposes(
            column_loader=column_loader,
            row_count=row_count,
            record_count=record_count,
            primes=FIXED_MODULAR_PRIMES,
            directory=directory,
        )
        proposals: list[dict[str, Any]] = []
        executions: list[dict[str, Any]] = []
        for transpose in transposes:
            proposal, execution = invoke_native_proposer(
                binary_path=NATIVE_PROPOSER_PATH,
                transpose=transpose,
                row_count=row_count,
                record_count=record_count,
                threads=threads,
            )
            proposals.append(proposal)
            executions.append(execution)
    validate_modular_proposals(
        proposals,
        record_count=record_count,
        primes=FIXED_MODULAR_PRIMES,
    )
    require(
        any(receipt["selected_sequences"] for receipt in proposals),
        "all native proposal lanes returned empty work orders",
    )
    return proposals, executions


def exact_rank(integer_rows: Sequence[Sequence[int]]) -> int:
    return int(qmatrix(integer_rows).rank())


def exact_prefix_rank_transcript(
    *,
    complete_basis_rows: Sequence[Sequence[int]],
    base_rows: int,
    pool_rows: int,
) -> dict[str, Any]:
    require(
        len(complete_basis_rows) == base_rows + pool_rows
        and base_rows > 0
        and pool_rows > 0,
        "prefix-rank row census drift",
    )
    # A single exact RREF of M_S^T yields the ordered row-rank profile of M_S:
    # its pivot columns are precisely the lexicographically first independent
    # original rows.  The rank of any original-row prefix is therefore the
    # number of these pivot indices below the prefix boundary.
    transposed = qmatrix(complete_basis_rows).transpose()
    reduced, full_rank = transposed.rref()
    full_rank = int(full_rank)
    ordered_row_rank_profile = pivot_columns(
        reduced, full_rank, base_rows + pool_rows
    )
    pivot_set = set(ordered_row_rank_profile)
    ranks = [
        sum(row < base_rows + prefix for row in ordered_row_rank_profile)
        for prefix in range(pool_rows + 1)
    ]
    increments = [
        int(base_rows + index in pivot_set) for index in range(pool_rows)
    ]
    require(
        ranks[-1] == full_rank
        and all(
            ranks[index + 1] - ranks[index] == increments[index]
            for index in range(pool_rows)
        ),
        "ordered row-rank profile/prefix transcript drift",
    )
    return {
        "base_rank": ranks[0],
        "full_pool_rank": ranks[-1],
        "ordered_independent_logical_rows": ordered_row_rank_profile,
        "ordered_independent_logical_rows_u64le_sha256": digest_u64(
            ordered_row_rank_profile
        ),
        "ranks": ranks,
        "increments": increments,
        "rank_growing_indices": [
            index for index, increment in enumerate(increments) if increment == 1
        ],
        "dependent_indices": [
            index for index, increment in enumerate(increments) if increment == 0
        ],
        "ranks_decimal_lf_sha256": digest_decimal_lf(ranks),
        "increments_decimal_lf_sha256": digest_decimal_lf(increments),
        "exact_q": True,
        "complete_basis_restriction": True,
        "method": "single_exact_Q_RREF_of_complete_basis_transpose_row_rank_profile",
    }


def repeated_exact_prefix_ranks(
    complete_basis_rows: Sequence[Sequence[int]], base_rows: int, pool_rows: int
) -> list[int]:
    """Slow theorem oracle used only by small asymmetric self-tests."""

    return [
        exact_rank(complete_basis_rows[: base_rows + prefix])
        for prefix in range(pool_rows + 1)
    ]


def row_pivot_minor(
    *,
    rows: Sequence[Sequence[int]],
    logical_row_indices: Sequence[int],
    basis_sequences: Sequence[int],
) -> dict[str, Any]:
    require(
        len(rows) == len(logical_row_indices)
        and bool(rows)
        and all(len(row) == len(basis_sequences) for row in rows),
        "row-pivot minor source drift",
    )
    matrix = qmatrix(rows)
    rank = int(matrix.rank())
    transposed, transposed_rank = matrix.transpose().rref()
    require(int(transposed_rank) == rank, "row-pivot rank drift")
    row_positions = pivot_columns(transposed, rank, len(rows))
    independent_rows = [rows[position] for position in row_positions]
    reduced, reduced_rank = qmatrix(independent_rows).rref()
    require(int(reduced_rank) == rank, "independent-row RREF drift")
    column_positions = pivot_columns(reduced, rank, len(basis_sequences))
    square_rows = [
        [int(row[column]) for column in column_positions]
        for row in independent_rows
    ]
    determinant = int(fmpz_mat(square_rows).det())
    require(determinant != 0, "row-pivot exact determinant vanished")
    return {
        "rank": rank,
        "logical_row_indices": [logical_row_indices[index] for index in row_positions],
        "column_sequences": [basis_sequences[index] for index in column_positions],
        "determinant": str(determinant),
        "square_i128le_sha256": digest_i128(
            value for row in square_rows for value in row
        ),
    }


def exact_dependency_certificate(
    *,
    complete_basis_rows: Sequence[Sequence[int]],
    basis_sequences: Sequence[int],
    logical_target: Sequence[int],
    preceding_logical_rows: Sequence[int],
    candidate_logical_row: int,
) -> dict[str, Any]:
    """Express one dependent row using independent preceding rows exactly."""

    require(
        len(complete_basis_rows) == len(logical_target)
        and all(len(row) == len(basis_sequences) for row in complete_basis_rows)
        and preceding_logical_rows == sorted(set(preceding_logical_rows))
        and candidate_logical_row not in preceding_logical_rows
        and 0 <= candidate_logical_row < len(complete_basis_rows),
        "dependency certificate axes drift",
    )
    preceding = [complete_basis_rows[index] for index in preceding_logical_rows]
    candidate = complete_basis_rows[candidate_logical_row]
    preceding_matrix = qmatrix(preceding)
    preceding_rank = int(preceding_matrix.rank())
    require(
        exact_rank([*preceding, candidate]) == preceding_rank,
        "dependency certificate requested for rank-growing row",
    )

    transposed, transposed_rank = preceding_matrix.transpose().rref()
    require(int(transposed_rank) == preceding_rank, "dependency row-rank drift")
    independent_positions = pivot_columns(
        transposed, preceding_rank, len(preceding_logical_rows)
    )
    independent_rows = [preceding[position] for position in independent_positions]
    independent_logical_rows = [
        preceding_logical_rows[position] for position in independent_positions
    ]
    reduced, reduced_rank = qmatrix(independent_rows).rref()
    require(int(reduced_rank) == preceding_rank, "dependency basis rank drift")
    coordinate_columns = pivot_columns(
        reduced, preceding_rank, len(basis_sequences)
    )
    square = qmatrix(
        [
            [int(row[column]) for column in coordinate_columns]
            for row in independent_rows
        ]
    )
    right = qmatrix([[int(candidate[column])] for column in coordinate_columns])
    rational = square.transpose().solve(right)
    coefficients = [
        Fraction(str(rational[index, 0])) for index in range(preceding_rank)
    ]
    replay = [
        sum(
            coefficients[index] * independent_rows[index][column]
            for index in range(preceding_rank)
        )
        for column in range(len(basis_sequences))
    ]
    require(
        replay == [Fraction(value) for value in candidate],
        "dependency failed complete-basis exact replay",
    )
    implied_target = sum(
        coefficients[index] * logical_target[logical_row]
        for index, logical_row in enumerate(independent_logical_rows)
    )
    candidate_target = Fraction(logical_target[candidate_logical_row])
    pairing = candidate_target - implied_target

    relation = [Fraction() for _ in complete_basis_rows]
    for logical_row, coefficient in zip(
        independent_logical_rows, coefficients, strict=True
    ):
        relation[logical_row] -= coefficient
    relation[candidate_logical_row] = Fraction(1)
    primitive = primitive_integer(relation)
    primitive_pairing = sum(
        coefficient * int(logical_target[row])
        for row, coefficient in enumerate(primitive)
    )
    require(
        (pairing == 0) == (primitive_pairing == 0),
        "dependency target compatibility normalization drift",
    )
    return {
        "candidate_logical_row": candidate_logical_row,
        "preceding_row_count": len(preceding_logical_rows),
        "preceding_rank": preceding_rank,
        "independent_logical_rows": independent_logical_rows,
        "coordinate_column_sequences": [
            basis_sequences[index] for index in coordinate_columns
        ],
        "coefficients": [canonical_fraction(value) for value in coefficients],
        "coefficients_lf_sha256": digest_fraction_lf(coefficients),
        "complete_basis_replay_lf_sha256": digest_fraction_lf(replay),
        "primitive_relation": [str(value) for value in primitive],
        "primitive_relation_decimal_lf_sha256": digest_decimal_lf(primitive),
        "primitive_target_pairing": str(primitive_pairing),
        "compatible": primitive_pairing == 0,
        "exact_q": True,
    }


def exact_separator_replay(
    *,
    column_loader: Callable[[int], Sequence[int]],
    separator: Sequence[int],
    target: Sequence[int],
    record_count: int,
) -> dict[str, Any]:
    require(
        len(separator) == len(target) and any(separator),
        "invalid full-family separator shape",
    )
    canonical = primitive_integer([Fraction(value) for value in separator])
    require(list(separator) == canonical, "separator is not primitive/canonical")
    pairing = sum(
        coefficient * int(target[row])
        for row, coefficient in enumerate(separator)
    )
    require(pairing != 0, "separator lost target pairing")
    prices: list[int] = []
    first_nonzero: tuple[int, int] | None = None
    for sequence in range(record_count):
        column = [int(value) for value in column_loader(sequence)]
        require(len(column) == len(separator), "separator column dimension drift")
        price = sum(
            coefficient * column[row]
            for row, coefficient in enumerate(separator)
            if coefficient
        )
        prices.append(price)
        if price and first_nonzero is None:
            first_nonzero = (sequence, price)
    require(first_nonzero is None, "separator failed full-family replay")
    return {
        "columns_scanned": record_count,
        "all_family_columns_exactly_annihilated": True,
        "prices_decimal_lf_sha256": digest_decimal_lf(prices),
        "target_pairing": str(pairing),
        "separator_decimal_lf_sha256": digest_decimal_lf(separator),
    }


def exact_rank_selection(
    *,
    column_loader: Callable[[int], Sequence[int]],
    complete_basis: dict[str, Any],
    target: Sequence[int],
    base_rows: int,
    pool_rows: int,
    admit_rows: int,
    record_count: int,
) -> dict[str, Any]:
    """Compute exact prefix ranks and rank-aware admission on a complete basis."""

    require(
        complete_basis.get("all_columns_exactly_spanned") is True
        and complete_basis.get("no_modular_terminal_decision") is True,
        "rank selection requires an exact complete-basis certificate",
    )
    logical_rows = base_rows + pool_rows
    require(
        len(target) == logical_rows and 0 < admit_rows <= pool_rows,
        "rank selection target/dimension drift",
    )
    basis_sequences = [int(value) for value in complete_basis["basis_sequences"]]
    basis_columns = [
        [int(value) for value in column_loader(sequence)]
        for sequence in basis_sequences
    ]
    basis_rows = matrix_rows(basis_columns, logical_rows)
    require(
        exact_rank(basis_rows) == complete_basis["basis_rank"],
        "complete basis changed before rank selection",
    )
    transcript = exact_prefix_rank_transcript(
        complete_basis_rows=basis_rows,
        base_rows=base_rows,
        pool_rows=pool_rows,
    )
    growth = transcript["rank_growing_indices"]
    provisional_selected = growth[:admit_rows]
    admission_cap_stop_exclusive = (
        provisional_selected[-1] + 1
        if len(provisional_selected) == admit_rows
        else pool_rows
    )

    dependency_certificates: list[dict[str, Any]] = []
    selected_indices: list[int] = []
    rank_basis_indices: list[int] = []
    processed_dependent: list[int] = []
    incompatible: dict[str, Any] | None = None
    processed_stop_exclusive = 0
    # The cap limits only downstream admission.  Target compatibility is a
    # statement on the full base+pool row system, so every later row is still
    # processed.  Post-cap rank-growing rows join the dependency basis without
    # joining the admitted set.
    for pool_index in range(pool_rows):
        processed_stop_exclusive = pool_index + 1
        if transcript["increments"][pool_index] == 1:
            rank_basis_indices.append(pool_index)
            if len(selected_indices) < admit_rows:
                selected_indices.append(pool_index)
            continue
        candidate_logical_row = base_rows + pool_index
        preceding = [
            logical_row
            for logical_row in transcript["ordered_independent_logical_rows"]
            if logical_row < candidate_logical_row
        ]
        certificate = exact_dependency_certificate(
            complete_basis_rows=basis_rows,
            basis_sequences=basis_sequences,
            logical_target=target,
            preceding_logical_rows=preceding,
            candidate_logical_row=candidate_logical_row,
        )
        certificate["pool_index"] = pool_index
        dependency_certificates.append(certificate)
        processed_dependent.append(pool_index)
        if not certificate["compatible"]:
            separator = [int(value) for value in certificate["primitive_relation"]]
            replay = exact_separator_replay(
                column_loader=column_loader,
                separator=separator,
                target=target,
                record_count=record_count,
            )
            incompatible = {
                "pool_index": pool_index,
                "dependency": certificate,
                "separator": separator,
                "separator_replay": replay,
            }
            break

    require(
        incompatible is not None
        or (
            processed_stop_exclusive == pool_rows
            and selected_indices == provisional_selected
            and rank_basis_indices == growth
            and processed_dependent == transcript["dependent_indices"]
        ),
        "full-pool compatibility scan diverged without an incompatible dependency",
    )
    post_terminal = (
        list(range(processed_stop_exclusive, pool_rows))
        if incompatible is not None
        else []
    )
    post_cap = (
        list(range(admission_cap_stop_exclusive, pool_rows))
        if incompatible is None and len(selected_indices) == admit_rows
        else []
    )

    scientific_labels = (
        base_rows == BASE_ROWS
        and pool_rows == POOL_ROWS
        and admit_rows == ADMIT_ROWS
        and record_count == RECORDS
    )
    if incompatible is not None:
        result = (
            "FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER"
            if scientific_labels
            else "SYNTHETIC_INCOMPATIBLE_DEPENDENCY"
        )
    elif len(selected_indices) < admit_rows:
        result = (
            "FIXED_POOL128_EXACT_RANK_GAIN_LT32"
            if scientific_labels
            else "SYNTHETIC_FIXED_POOL_EXACT_RANK_GAIN_LT_LIMIT"
        )
    else:
        result = (
            "EXACT_RANK32_SELECTED"
            if scientific_labels
            else "SYNTHETIC_EXACT_RANK_LIMIT_SELECTED"
        )

    selected_logical_rows = list(range(base_rows)) + [
        base_rows + index for index in selected_indices
    ]
    selected_rows = [basis_rows[index] for index in selected_logical_rows]
    selected_rank = exact_rank(selected_rows)
    require(
        selected_rank == transcript["base_rank"] + len(selected_indices),
        "admitted system rank did not equal base rank plus admissions",
    )
    minor = row_pivot_minor(
        rows=selected_rows,
        logical_row_indices=selected_logical_rows,
        basis_sequences=basis_sequences,
    )
    require(minor["rank"] == selected_rank, "selected-system minor rank drift")
    return {
        "result": result,
        "base_rows": base_rows,
        "pool_rows": pool_rows,
        "admit_limit": admit_rows,
        "prefix_rank_transcript": transcript,
        "full_pool_rank_transcript_precomputed_before_target_compatibility_checks": True,
        "selected_pool_indices": selected_indices,
        "selected_count": len(selected_indices),
        "rank_basis_pool_indices_before_terminal": rank_basis_indices,
        "dependent_pool_indices_before_terminal": processed_dependent,
        "post_cap_unadmitted_pool_indices": post_cap,
        "post_terminal_unprocessed_pool_indices": post_terminal,
        "all_pool_rows_compatibility_checked": (
            incompatible is None and processed_stop_exclusive == pool_rows
        ),
        "compatibility_decision_complete": (
            incompatible is not None or processed_stop_exclusive == pool_rows
        ),
        "dependency_certificates": dependency_certificates,
        "incompatible_dependency": incompatible,
        "selected_system_rank": selected_rank,
        "selected_system_nonzero_minor": minor,
        "no_modular_row_selection": True,
    }


MANIFEST_KEYS = {
    "schema",
    "selected_branch",
    "preregistration_git_commit",
    "producer_git_commit",
    "source_audit_git_commit",
    "bindings",
    "transitive_inputs",
    "parameters",
    "stage_order",
    "planned_outputs",
}
BINDING_KEYS = {"path", "sha256"}
SOURCE_AUDIT_KEYS = {
    "schema",
    "verdict",
    "result",
    "evidence_class",
    "claim_boundary",
    "reviewer",
    "preregistration",
    "subject",
    "required_checks",
    "scientific_manifest_observed",
    "scientific_input_observed",
    "scientific_output_observed",
    "scientific_replay_run",
    "no_claim",
}
SOURCE_AUDIT_REVIEWER_KEYS = {
    "agent_name",
    "program",
    "model",
    "same_model_lineage",
    "fresh_context",
}
SOURCE_AUDIT_PREREGISTRATION_KEYS = {
    "path",
    "sha256",
    "git_commit",
    "committed_and_pushed_before_subject_source_inspection",
    "committed_and_pushed_before_runtime_checks",
}
SOURCE_AUDIT_SUBJECT_KEYS = {
    "git_commit",
    "commit_object_and_working_bytes_equal_for_all_bindings",
    "bindings",
}


def validate_direction(raw: object, label: str) -> list[int]:
    require(
        isinstance(raw, list)
        and len(raw) == N
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and -128 <= value <= 127
            for value in raw
        ),
        f"{label} must be an 11-coordinate i8 direction",
    )
    direction = [int(value) for value in raw]
    require(sum(direction) == 0, f"{label} does not sum to zero")
    first_nonzero = next((value for value in direction if value), None)
    require(first_nonzero is not None and first_nonzero > 0, f"{label} sign drift")
    divisor = 0
    for value in direction:
        divisor = math.gcd(divisor, abs(value))
    require(divisor == 1, f"{label} is not primitive")
    prefix = 0
    active = False
    for value in direction[:-1]:
        prefix += value
        active = active or prefix < 0
    require(active, f"{label} is inactive on the ordered cone")
    return direction


def validate_binding_shape(value: object, label: str) -> tuple[str, str]:
    require(
        isinstance(value, dict) and set(value) == BINDING_KEYS,
        f"{label} binding schema drift",
    )
    path = value.get("path")
    digest = value.get("sha256")
    require(
        isinstance(path, str)
        and path == Path(path).as_posix()
        and not Path(path).is_absolute()
        and ".." not in Path(path).parts
        and is_sha256(digest),
        f"{label} binding malformed",
    )
    return path, str(digest)


def validate_binding(value: object, label: str) -> tuple[str, str]:
    path, digest = validate_binding_shape(value, label)
    resolved = contained(ROOT / path)
    require(resolved.is_file(), f"{label} bound file missing: {path}")
    require_digest(sha256_path(resolved), digest, label)
    return path, digest


def git_commit_for_path(path: Path) -> str:
    relative_path = relative(path)
    process = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative_path],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = process.stdout.strip()
    require(
        len(commit) == 40 and all(character in "0123456789abcdef" for character in commit),
        f"no canonical Git commit for {path}",
    )
    blob = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(blob.returncode == 0, f"cannot read committed blob for {path}")
    require(
        hashlib.sha256(blob.stdout).hexdigest() == sha256_path(path),
        f"working bytes differ from committed binding: {path}",
    )
    return commit


def validate_commit(commit: object, label: str) -> str:
    require(
        isinstance(commit, str)
        and len(commit) == 40
        and all(character in "0123456789abcdef" for character in commit),
        f"{label} Git commit malformed",
    )
    process = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}^{{commit}}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(process.returncode == 0, f"{label} Git commit unavailable")
    return commit


def git_is_ancestor(ancestor: str, descendant: str, label: str) -> None:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(process.returncode == 0, f"Git ancestry drift: {label}")


def recursive_bindings(value: object) -> Iterable[tuple[str, str]]:
    """Find binding pairs even when an audit adds provenance metadata."""

    if isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and is_sha256(digest):
            yield path, str(digest)
        for nested in value.values():
            yield from recursive_bindings(nested)
    elif isinstance(value, list):
        for nested in value:
            yield from recursive_bindings(nested)


def snapshot_add(
    snapshot: dict[str, str], path: str, digest: str, label: str
) -> None:
    require(is_sha256(digest), f"{label} snapshot digest malformed")
    if path in snapshot:
        require(snapshot[path] == digest, f"{label} snapshot collision drift: {path}")
    else:
        snapshot[path] = digest


def validate_fixed_inputs() -> dict[str, str]:
    expected = {
        PREREGISTRATION_PATH: PREREGISTRATION_SHA256,
        G0135_SOURCE_PATH: G0135_SOURCE_SHA256,
        G0135_RESULT_PATH: G0135_RESULT_SHA256,
        G0135_STAGE_D_PATH: G0135_STAGE_D_SHA256,
        G0117_EXACT_PATH: G0117_EXACT_SHA256,
        REQUIREMENTS_PATH: REQUIREMENTS_SHA256,
        PYTHON_WHEEL_HASHES_PATH: PYTHON_WHEEL_HASHES_SHA256,
        TOOLCHAIN_MANIFEST_PATH: TOOLCHAIN_MANIFEST_SHA256,
        TOOLCHAIN_PATH: TOOLCHAIN_SHA256,
    }
    snapshot: dict[str, str] = {}
    for path, digest in expected.items():
        resolved = contained(path)
        require(resolved.is_file(), f"fixed input missing: {path}")
        require_digest(sha256_path(resolved), digest, relative(path))
        snapshot[relative(path)] = digest
    require(
        git_commit_for_path(PREREGISTRATION_PATH) == PREREGISTRATION_COMMIT,
        "G-0140 preregistration Git commit drift",
    )
    return snapshot


def validate_python_runtime() -> dict[str, str]:
    expected_prefix = (ROOT / ".venv").resolve()
    require(
        sys.version_info[:3] == (3, 13, 7),
        "Stage-C requires the pinned CPython 3.13.7 runtime",
    )
    require(
        str(flint.__version__) == "0.9.0",
        "Stage-C requires the pinned python-flint 0.9.0 runtime",
    )
    require(
        Path(sys.prefix).resolve() == expected_prefix,
        "Stage-C must run inside the project .venv",
    )
    return {
        "python": ".".join(str(value) for value in sys.version_info[:3]),
        "python_flint": str(flint.__version__),
        "venv": relative(expected_prefix),
    }


NATIVE_BUILD_KEYS = {
    "schema",
    "compiler",
    "command",
    "architecture",
    "byte_order",
    "source",
    "binary",
    "toolchain_manifest",
    "toolchain",
}


def compiler_identity() -> str:
    process = subprocess.run(
        ["g++", "--version"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    first = process.stdout.splitlines()[0] if process.stdout else ""
    require(bool(first), "g++ identity is empty")
    return first


def validate_native_build_receipt() -> dict[str, str]:
    receipt = load_json(NATIVE_BUILD_RECEIPT_PATH)
    require(set(receipt) == NATIVE_BUILD_KEYS, "native build receipt key drift")
    require(
        receipt.get("schema") == NATIVE_BUILD_SCHEMA
        and receipt.get("compiler") == compiler_identity()
        and receipt.get("command") == NATIVE_BUILD_COMMAND
        and receipt.get("architecture") == platform.machine() == "x86_64"
        and receipt.get("byte_order") == sys.byteorder == "little",
        "native build toolchain/architecture/endianness drift",
    )
    expected = {
        "source": (relative(NATIVE_PROPOSER_SOURCE_PATH), sha256_path(NATIVE_PROPOSER_SOURCE_PATH)),
        "binary": (relative(NATIVE_PROPOSER_PATH), sha256_path(NATIVE_PROPOSER_PATH)),
        "toolchain_manifest": (
            relative(TOOLCHAIN_MANIFEST_PATH),
            TOOLCHAIN_MANIFEST_SHA256,
        ),
        "toolchain": (relative(TOOLCHAIN_PATH), TOOLCHAIN_SHA256),
    }
    observed: dict[str, str] = {}
    for label, (expected_path, expected_digest) in expected.items():
        path, digest = validate_binding(receipt.get(label), f"native build {label}")
        require(
            path == expected_path and digest == expected_digest,
            f"native build {label} custody drift",
        )
        observed[path] = digest
    return observed


def validate_manifest(
    manifest: dict[str, Any], manifest_sha256: str, script_sha256: str
) -> dict[str, str]:
    require(set(manifest) == MANIFEST_KEYS, "G-0140 manifest top-level key drift")
    require(
        manifest.get("schema") == MANIFEST_SCHEMA
        and manifest.get("selected_branch") == "G0135_EXACT_RESIDUAL_POOL128"
        and manifest.get("stage_order") == STAGE_ORDER
        and manifest.get("planned_outputs") == PLANNED_OUTPUTS
        and manifest.get("parameters") == MANIFEST_PARAMETERS,
        "G-0140 manifest identity/parameter/output drift",
    )
    preregistration_commit = validate_commit(
        manifest.get("preregistration_git_commit"), "manifest preregistration"
    )
    producer_commit = validate_commit(
        manifest.get("producer_git_commit"), "manifest producer"
    )
    stage_a_source_audit_commit = validate_commit(
        manifest.get("source_audit_git_commit"), "manifest source audit"
    )
    require(
        preregistration_commit == PREREGISTRATION_COMMIT,
        "manifest preregistration commit differs from frozen protocol",
    )

    raw_bindings = manifest.get("bindings")
    raw_transitive = manifest.get("transitive_inputs")
    require(
        isinstance(raw_bindings, dict)
        and all(isinstance(label, str) and label for label in raw_bindings)
        and isinstance(raw_transitive, list),
        "manifest binding containers malformed",
    )
    snapshot: dict[str, str] = {}
    for label, value in raw_bindings.items():
        path, digest = validate_binding(value, f"manifest binding {label}")
        require(path not in snapshot, f"duplicate manifest-bound path: {path}")
        snapshot[path] = digest
    for index, value in enumerate(raw_transitive):
        path, digest = validate_binding(value, f"manifest transitive {index}")
        require(path not in snapshot, f"duplicate manifest/transitive path: {path}")
        snapshot[path] = digest

    required = {
        relative(PREREGISTRATION_PATH): PREREGISTRATION_SHA256,
        relative(G0135_RESULT_PATH): G0135_RESULT_SHA256,
        relative(G0135_STAGE_D_PATH): G0135_STAGE_D_SHA256,
        relative(G0139_RECEIPT_PATH): G0139_RECEIPT_SHA256,
        relative(SCRIPT): script_sha256,
        relative(NATIVE_PROPOSER_SOURCE_PATH): sha256_path(
            NATIVE_PROPOSER_SOURCE_PATH
        ),
        relative(NATIVE_PROPOSER_PATH): sha256_path(NATIVE_PROPOSER_PATH),
        relative(NATIVE_BUILD_RECEIPT_PATH): sha256_path(NATIVE_BUILD_RECEIPT_PATH),
        relative(NATIVE_TEST_PATH): sha256_path(NATIVE_TEST_PATH),
        relative(LAUNCHER_PATH): sha256_path(LAUNCHER_PATH),
        relative(STAGE_A_SOURCE_PATH): None,
        relative(STAGE_A_SOURCE_PATH.parent / "engine.rs"): None,
        relative(STAGE_A_SOURCE_PATH.parent.parent / "Cargo.toml"): None,
        relative(STAGE_A_SOURCE_PATH.parent.parent / "Cargo.lock"): None,
        relative(
            STAGE_A_SOURCE_PATH.parent.parent
            / "target/release/g0140-stage-a-pool128-global-replay"
        ): None,
        relative(STAGE_B_SOURCE_PATH): None,
        relative(STAGE_B_SOURCE_PATH.parent.parent / "Cargo.toml"): None,
        relative(STAGE_B_SOURCE_PATH.parent.parent / "Cargo.lock"): None,
        relative(
            STAGE_B_SOURCE_PATH.parent.parent
            / "target/release/g0140-stage-b-pool128-coordinate-pricer"
        ): None,
        relative(G0150_SOURCE_AUDIT_PATH): None,
        relative(STAGE_B_SOURCE_AUDIT_PATH): None,
        relative(STAGE_C_SOURCE_AUDIT_PATH): None,
    }
    for path, expected in required.items():
        require(path in snapshot, f"manifest omits required Stage-C input: {path}")
        if expected is not None:
            require(snapshot[path] == expected, f"manifest binding drift: {path}")
    require(
        manifest_sha256 == sha256_path(MANIFEST_PATH),
        "manifest entry digest drift",
    )
    manifest_commit = git_commit_for_path(MANIFEST_PATH)
    require(
        producer_commit == git_commit_for_path(STAGE_A_SOURCE_PATH)
        and stage_a_source_audit_commit
        == git_commit_for_path(G0150_SOURCE_AUDIT_PATH),
        "manifest producer/G-0150 commit semantics drift",
    )
    git_is_ancestor(
        preregistration_commit,
        producer_commit,
        "G-0140 preregistration -> Stage-A producer",
    )
    git_is_ancestor(
        producer_commit,
        stage_a_source_audit_commit,
        "Stage-A producer -> G-0150 source audit",
    )
    git_is_ancestor(
        stage_a_source_audit_commit,
        manifest_commit,
        "G-0150 source audit -> shared manifest",
    )

    stage_c_subjects = (
        SCRIPT,
        NATIVE_PROPOSER_SOURCE_PATH,
        NATIVE_PROPOSER_PATH,
        NATIVE_BUILD_RECEIPT_PATH,
        NATIVE_TEST_PATH,
        LAUNCHER_PATH,
    )
    stage_c_commits = {path: git_commit_for_path(path) for path in stage_c_subjects}
    for path, commit in stage_c_commits.items():
        git_is_ancestor(
            preregistration_commit,
            commit,
            f"G-0140 preregistration -> Stage-C subject {relative(path)}",
        )

    validate_source_audit_receipt(
        load_json(G0150_SOURCE_AUDIT_PATH),
        audit_path=G0150_SOURCE_AUDIT_PATH,
        schema=G0150_SCHEMA,
        claim_boundary=G0150_CLAIM_BOUNDARY,
        no_claim=G0150_NO_CLAIM,
        required_checks=G0150_REQUIRED_CHECKS,
        preregistration_path=G0150_AUDIT_PREREGISTRATION_PATH,
        snapshot=snapshot,
        named_subjects={
            "main_source": STAGE_A_SOURCE_PATH,
            "engine_source": STAGE_A_SOURCE_PATH.parent / "engine.rs",
            "cargo_manifest": STAGE_A_SOURCE_PATH.parent.parent / "Cargo.toml",
            "cargo_lock": STAGE_A_SOURCE_PATH.parent.parent / "Cargo.lock",
            "release_executable": STAGE_A_SOURCE_PATH.parent.parent
            / "target/release/g0140-stage-a-pool128-global-replay",
        },
        subject_commit=git_commit_for_path(STAGE_A_SOURCE_PATH),
        manifest_commit=manifest_commit,
    )
    validate_source_audit_receipt(
        load_json(STAGE_B_SOURCE_AUDIT_PATH),
        audit_path=STAGE_B_SOURCE_AUDIT_PATH,
        schema=STAGE_B_SOURCE_AUDIT_SCHEMA,
        claim_boundary=STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY,
        no_claim=STAGE_B_SOURCE_AUDIT_NO_CLAIM,
        required_checks=STAGE_B_SOURCE_AUDIT_REQUIRED_CHECKS,
        preregistration_path=STAGE_B_AUDIT_PREREGISTRATION_PATH,
        snapshot=snapshot,
        named_subjects={
            "main_source": STAGE_B_SOURCE_PATH,
            "cargo_manifest": STAGE_B_SOURCE_PATH.parent.parent / "Cargo.toml",
            "cargo_lock": STAGE_B_SOURCE_PATH.parent.parent / "Cargo.lock",
            "release_executable": STAGE_B_SOURCE_PATH.parent.parent
            / "target/release/g0140-stage-b-pool128-coordinate-pricer",
        },
        subject_commit=git_commit_for_path(STAGE_B_SOURCE_PATH),
        manifest_commit=manifest_commit,
    )
    validate_stage_c_source_audit(
        load_json(STAGE_C_SOURCE_AUDIT_PATH),
        snapshot=snapshot,
        stage_c_commits=stage_c_commits,
        manifest_commit=manifest_commit,
    )
    return snapshot


def validate_g0139_admission(receipt: dict[str, Any]) -> None:
    custody = receipt.get("input_custody")
    require(isinstance(custody, dict), "G-0139 input-custody object missing")
    fixed = custody.get("fixed_inputs")
    transitive = custody.get("transitive_bound_inputs")
    require(
        isinstance(fixed, dict) and isinstance(transitive, dict),
        "G-0139 fixed/transitive custody maps missing",
    )
    require(
        receipt.get("schema") == G0139_SCHEMA
        and receipt.get("verdict") == "PASS"
        and receipt.get("result") == "CONSISTENT_RESIDUAL_T1"
        and receipt.get("evidence_class") == G0139_EVIDENCE_CLASS
        and receipt.get("claim_boundary") == G0139_CLAIM_BOUNDARY
        and isinstance(receipt.get("reviewer"), dict)
        and receipt["reviewer"].get("same_model_lineage") is True
        and isinstance(receipt.get("preregistration"), dict)
        and receipt["preregistration"].get("outcome_aware") is True
        and receipt.get("subject")
        == {
            "git_commit": G0135_STAGE_D_COMMIT,
            "path": relative(G0135_STAGE_D_PATH),
            "result_observed_before_checker": "EXACT_RESIDUAL_BATCH_CONTINUE",
            "sha256": G0135_STAGE_D_SHA256,
        }
        and isinstance(receipt.get("git_custody"), dict)
        and receipt["git_custody"].get("subject_commit") == G0135_STAGE_D_COMMIT
        and receipt["git_custody"].get("strict_linear_ancestry") is True
        and receipt.get("source_audit_anchor")
        == {
            "path": G0138_SOURCE_AUDIT_RELATIVE_PATH,
            "sha256": G0138_SOURCE_AUDIT_SHA256,
            "verdict": "PASS",
        }
        and isinstance(receipt.get("clean_room_execution_boundary"), dict)
        and receipt["clean_room_execution_boundary"].get(
            "stage_d_bound_bytes_consumed_as_hashes_only"
        )
        is True
        and receipt["clean_room_execution_boundary"].get(
            "stage_d_scientific_replay_rerun"
        )
        is False
        and custody.get("entry_exit_rehash_equal") is True
        and custody.get("fixed_input_count") == len(fixed) == 8
        and fixed.get(relative(G0135_STAGE_D_PATH)) == G0135_STAGE_D_SHA256
        and fixed.get(relative(G0135_RESULT_PATH)) == G0135_RESULT_SHA256
        and fixed.get(G0138_SOURCE_AUDIT_RELATIVE_PATH)
        == G0138_SOURCE_AUDIT_SHA256
        and custody.get("transitive_bound_input_count") == len(transitive) == 92,
        "G-0139 semantic/custody admission drift",
    )

    observed = set(recursive_bindings(receipt))
    require(
        (relative(G0135_STAGE_D_PATH), G0135_STAGE_D_SHA256) in observed,
        "G-0139 receipt does not bind the admitted G-0135 Stage-D result",
    )


def validate_source_audit_shape(
    receipt: dict[str, Any],
    *,
    schema: str,
    claim_boundary: str,
    no_claim: str,
    required_checks: dict[str, bool],
    preregistration_path: str,
    named_bindings: dict[str, tuple[str, str]],
    subject_commit: str,
) -> None:
    require(set(receipt) == SOURCE_AUDIT_KEYS, "source-audit top-level key drift")
    reviewer = receipt.get("reviewer")
    require(
        isinstance(reviewer, dict)
        and set(reviewer) == SOURCE_AUDIT_REVIEWER_KEYS
        and isinstance(reviewer.get("agent_name"), str)
        and bool(reviewer["agent_name"])
        and reviewer.get("program") == "codex"
        and isinstance(reviewer.get("model"), str)
        and bool(reviewer["model"])
        and reviewer.get("same_model_lineage") is True
        and reviewer.get("fresh_context") is True,
        "source-audit reviewer disclosure drift",
    )
    preregistration = receipt.get("preregistration")
    require(
        isinstance(preregistration, dict)
        and set(preregistration) == SOURCE_AUDIT_PREREGISTRATION_KEYS
        and preregistration.get("path") == preregistration_path
        and is_sha256(preregistration.get("sha256"))
        and isinstance(preregistration.get("git_commit"), str)
        and len(preregistration["git_commit"]) == 40
        and all(
            character in "0123456789abcdef"
            for character in preregistration["git_commit"]
        )
        and preregistration.get(
            "committed_and_pushed_before_subject_source_inspection"
        )
        is True
        and preregistration.get("committed_and_pushed_before_runtime_checks") is True,
        "source-audit preregistration shape drift",
    )
    subject = receipt.get("subject")
    require(
        isinstance(subject, dict)
        and set(subject) == SOURCE_AUDIT_SUBJECT_KEYS
        and subject.get("git_commit") == subject_commit
        and subject.get("commit_object_and_working_bytes_equal_for_all_bindings")
        is True
        and isinstance(subject.get("bindings"), dict)
        and set(subject["bindings"]) == set(named_bindings),
        "source-audit subject shape or identity drift",
    )
    observed_required_checks = receipt.get("required_checks")
    require(
        isinstance(observed_required_checks, dict)
        and set(observed_required_checks) == set(required_checks)
        and all(type(value) is bool for value in observed_required_checks.values())
        and observed_required_checks == required_checks,
        "source-audit required-check boolean contract drift",
    )
    require(
        receipt.get("schema") == schema
        and receipt.get("verdict") == "PASS"
        and receipt.get("result") == SOURCE_CUSTODY_PASS_RESULT
        and receipt.get("evidence_class") == SOURCE_AUDIT_EVIDENCE_CLASS
        and receipt.get("claim_boundary") == claim_boundary
        and receipt.get("scientific_manifest_observed") is False
        and receipt.get("scientific_input_observed") is False
        and receipt.get("scientific_output_observed") is False
        and receipt.get("scientific_replay_run") is False
        and receipt.get("no_claim") == no_claim,
        "source audit is not the exact outcome-blind T1 PASS contract",
    )
    observed_paths: list[str] = []
    for label, expected in named_bindings.items():
        path, digest = validate_binding_shape(subject["bindings"][label], label)
        require(
            (path, digest) == expected,
            f"source audit does not bind exact named subject: {label}",
        )
        observed_paths.append(path)
    require(
        len(observed_paths) == len(set(observed_paths)),
        "source-audit duplicate subject path drift",
    )


def validate_source_audit_receipt(
    receipt: dict[str, Any],
    *,
    audit_path: Path,
    schema: str,
    claim_boundary: str,
    no_claim: str,
    required_checks: dict[str, bool],
    preregistration_path: Path,
    snapshot: dict[str, str],
    named_subjects: dict[str, Path],
    subject_commit: str,
    manifest_commit: str,
) -> None:
    expected_bindings = {
        label: (relative(path), snapshot[relative(path)])
        for label, path in named_subjects.items()
    }
    validate_source_audit_shape(
        receipt,
        schema=schema,
        claim_boundary=claim_boundary,
        no_claim=no_claim,
        required_checks=required_checks,
        preregistration_path=relative(preregistration_path),
        named_bindings=expected_bindings,
        subject_commit=subject_commit,
    )
    subject_bindings = receipt["subject"]["bindings"]
    for label in named_subjects:
        observed = validate_binding(subject_bindings[label], f"source-audit {label}")
        require(
            observed == expected_bindings[label],
            f"source-audit live binding drift: {label}",
        )

    preregistration = receipt["preregistration"]
    require_digest(
        sha256_path(preregistration_path),
        str(preregistration["sha256"]),
        "source-audit preregistration",
    )
    prereg_commit = validate_commit(
        preregistration["git_commit"], "source-audit preregistration"
    )
    require(
        prereg_commit == git_commit_for_path(preregistration_path),
        "source-audit preregistration Git custody drift",
    )
    audit_commit = git_commit_for_path(audit_path)
    for label, path in named_subjects.items():
        git_is_ancestor(
            git_commit_for_path(path),
            prereg_commit,
            f"source-audit {label} -> preregistration",
        )
    git_is_ancestor(prereg_commit, audit_commit, "source-audit preregistration -> receipt")
    git_is_ancestor(
        audit_commit,
        manifest_commit,
        f"{relative(audit_path)} -> shared manifest",
    )


def validate_stage_c_source_audit(
    receipt: dict[str, Any],
    *,
    snapshot: dict[str, str],
    stage_c_commits: dict[Path, str],
    manifest_commit: str,
) -> None:
    script_commit = stage_c_commits[SCRIPT]
    validate_source_audit_receipt(
        receipt,
        audit_path=STAGE_C_SOURCE_AUDIT_PATH,
        schema=STAGE_C_SOURCE_AUDIT_SCHEMA,
        claim_boundary=STAGE_C_SOURCE_AUDIT_CLAIM_BOUNDARY,
        no_claim=STAGE_C_SOURCE_AUDIT_NO_CLAIM,
        required_checks=STAGE_C_SOURCE_AUDIT_REQUIRED_CHECKS,
        preregistration_path=STAGE_C_AUDIT_PREREGISTRATION_PATH,
        snapshot=snapshot,
        named_subjects={
            "selector_source": SCRIPT,
            "native_proposer_source": NATIVE_PROPOSER_SOURCE_PATH,
            "native_proposer_executable": NATIVE_PROPOSER_PATH,
            "native_build_receipt": NATIVE_BUILD_RECEIPT_PATH,
            "native_test": NATIVE_TEST_PATH,
            "launcher": LAUNCHER_PATH,
        },
        subject_commit=script_commit,
        manifest_commit=manifest_commit,
    )


def validate_g0135_member(receipt: dict[str, Any]) -> list[tuple[int, int]]:
    require(
        receipt.get("schema") == "max11-g0135-full-family-master-result-v3"
        and receipt.get("result") == "FULL_FAMILY_412ROW_EXACT_Q_MEMBER"
        and receipt.get("rows") == BASE_ROWS
        and receipt.get("records") == RECORDS
        and receipt.get("rank") == receipt.get("augmented_rank") == 204
        and receipt.get("all_412_rows_replayed") is True
        and receipt.get("inputs_rehashed_at_end") is True,
        "G-0135 Stage-C member identity/replay drift",
    )
    terms = receipt.get("terms")
    require(isinstance(terms, list) and len(terms) == 135, "G-0135 term census drift")
    parsed: list[tuple[int, int]] = []
    for index, item in enumerate(terms):
        require(
            isinstance(item, dict) and set(item) == {"sequence", "coefficient"},
            f"G-0135 term {index} schema drift",
        )
        sequence = item.get("sequence")
        require(
            isinstance(sequence, int)
            and not isinstance(sequence, bool)
            and 0 <= sequence < RECORDS,
            f"G-0135 term {index} sequence drift",
        )
        coefficient = canonical_integer(
            item.get("coefficient"), f"G-0135 term {index} coefficient", nonzero=True
        )
        parsed.append((sequence, coefficient))
    require(
        [sequence for sequence, _ in parsed]
        == sorted(set(sequence for sequence, _ in parsed)),
        "G-0135 term sequence order/uniqueness drift",
    )
    return parsed


def validate_stage_a_pool(
    receipt: dict[str, Any], manifest_sha256: str
) -> tuple[list[list[int]], list[int]]:
    require(
        receipt.get("schema") == STAGE_A_SCHEMA
        and receipt.get("result") == "EXACT_RESIDUAL_POOL128"
        and receipt.get("g0140_manifest")
        == {"path": relative(MANIFEST_PATH), "sha256": manifest_sha256}
        and receipt.get("rows") == BASE_ROWS
        and receipt.get("records") == RECORDS
        and receipt.get("terms") == 135
        and receipt.get("all_100_accumulated_directions_exact_zero") is True
        and receipt.get("all_11_linear_residuals_exact_zero") is True
        and receipt.get("pool_k") == POOL_ROWS
        and receipt.get("pool_count") == POOL_ROWS
        and receipt.get("inputs_rehashed_at_end") is True
        and receipt.get("manifest_rehashed_at_end") is True
        and receipt.get("candidate_rehashed_at_end") is True,
        "Stage-A Pool128 identity/census/custody drift",
    )
    pool = receipt.get("pool")
    require(isinstance(pool, list) and len(pool) == POOL_ROWS, "Pool128 census drift")
    directions: list[list[int]] = []
    residuals: list[int] = []
    for index, item in enumerate(pool):
        require(
            isinstance(item, dict) and set(item) == {"direction", "coefficient"},
            f"Pool128 item {index} schema drift",
        )
        directions.append(validate_direction(item.get("direction"), f"Pool128 item {index}"))
        residuals.append(
            canonical_integer(
                item.get("coefficient"), f"Pool128 item {index} coefficient", nonzero=True
            )
        )
    require(
        directions == sorted(directions)
        and len({tuple(direction) for direction in directions}) == POOL_ROWS
        and receipt.get("pool_directions_i8_sha256") == digest_directions(directions)
        and receipt.get("pool_exact_residuals_decimal_lf_sha256")
        == digest_decimal_lf(residuals),
        "Pool128 order/digest drift",
    )
    ancestor = load_json(G0135_STAGE_D_PATH)
    ancestor_first = ancestor.get("next_selected")
    require(
        isinstance(ancestor_first, list)
        and len(ancestor_first) == ADMIT_ROWS
        and pool[:ADMIT_ROWS] == ancestor_first
        and digest_directions(directions[:ADMIT_ROWS])
        == ancestor.get("next_selected_directions_i8_sha256")
        and digest_decimal_lf(residuals[:ADMIT_ROWS])
        == ancestor.get("next_selected_exact_residuals_decimal_lf_sha256"),
        "Pool128 does not preserve the public G-0135 first-32 prefix",
    )
    controls = receipt.get("selection_controls")
    require(
        isinstance(controls, dict)
        and controls.get("exact_batch_count_or_zero_terminal") is True
        and controls.get("strict_signed_lexicographic_order") is True
        and controls.get("excludes_accumulated_directions") is True
        and controls.get("direction_reordering_changes_digest") is True
        and controls.get("coefficient_plus_one_changes_digest") is True,
        "Stage-A Pool128 selection controls drift",
    )
    return directions, residuals


STAGE_B_ROW_KEYS = {
    "index",
    "direction",
    "exact_stage_a_residual",
    "exact_candidate_dot",
    "records",
    "nonzero_hinge_coefficients",
    "minimum_hinge_coefficient",
    "maximum_hinge_coefficient",
    "maximum_absolute_hinge_coefficient",
    "hinge_coefficients_i64_le_sha256",
    "hinge_coefficients",
}
STAGE_B_OUTPUT_KEYS = {
    "schema",
    "result",
    "claim_boundary",
    "manifest_path",
    "manifest_sha256",
    "source_and_input_bindings",
    "stage_a_receipt",
    "candidate",
    "g0139_result_audit",
    "pool_k",
    "records",
    "hinge_entries",
    "pool_count",
    "pool_directions_i8_sha256",
    "pool_exact_residuals_decimal_lf_sha256",
    "directions",
    "direction_major_hinge_i64_le_sha256",
    "exact_candidate_dots_decimal_lf_sha256",
    "exact_candidate_dots",
    "rows",
    "input_mutation_controls",
    "coefficient_plus_one_mutant",
    "inputs_rehashed_at_end",
    "wall_seconds",
}
STAGE_B_INPUT_MUTATION_CONTROL_KEYS = {
    "pool_count_mutant_rejected",
    "pool_order_mutant_rejected",
    "pool_duplicate_mutant_rejected",
    "direction_invalidity_mutant_rejected",
    "residual_plus_one_mutant_rejected",
    "record_census_truncation_rejected",
    "record_order_mutant_rejected",
    "all_rejected",
}
STAGE_B_COEFFICIENT_MUTANT_KEYS = {
    "sequence",
    "coefficient_delta",
    "baseline_exact_dots_decimal_lf_sha256",
    "mutated_exact_dots_decimal_lf_sha256",
    "changed_rows",
    "rejected",
}
STAGE_B_CLAIM_BOUNDARY = "Exact 128-row ordered-cone hinge coordinates over the frozen 163,740-record family, in deterministic G-0140 Stage-A pool order, with arbitrary-precision 135-term member dot bridges. This is complete-matrix rank-selection input only, not a membership decision, family-completeness theorem, global MAX11 identity, lower bound, minimality result, or Lean theorem."


def validate_stage_b_prices(
    receipt: dict[str, Any],
    *,
    manifest_sha256: str,
    manifest_bindings: dict[str, str],
    stage_a_sha256: str,
    directions: Sequence[Sequence[int]],
    residuals: Sequence[int],
    member_terms: Sequence[tuple[int, int]],
    expected_records: int = RECORDS,
) -> list[list[int]]:
    require(
        set(receipt) == STAGE_B_OUTPUT_KEYS
        and receipt.get("schema") == STAGE_B_SCHEMA
        and receipt.get("result") == "EXACT_FULL_FAMILY_POOL128_COORDINATES"
        and receipt.get("claim_boundary") == STAGE_B_CLAIM_BOUNDARY
        and receipt.get("manifest_path") == relative(MANIFEST_PATH)
        and receipt.get("manifest_sha256") == manifest_sha256
        and receipt.get("pool_k") == POOL_ROWS
        and receipt.get("pool_count") == POOL_ROWS
        and receipt.get("records") == expected_records
        and receipt.get("hinge_entries") == POOL_ROWS * expected_records
        and receipt.get("pool_directions_i8_sha256")
        == digest_directions(directions)
        and receipt.get("pool_exact_residuals_decimal_lf_sha256")
        == digest_decimal_lf(residuals)
        and receipt.get("directions") == list(directions)
        and receipt.get("inputs_rehashed_at_end") is True
        and isinstance(receipt.get("wall_seconds"), (int, float))
        and not isinstance(receipt.get("wall_seconds"), bool)
        and math.isfinite(receipt["wall_seconds"])
        and receipt["wall_seconds"] > 0,
        "Stage-B Pool128 identity/census/digest drift",
    )
    require(
        receipt.get("stage_a_receipt")
        == {"path": relative(STAGE_A_PATH), "sha256": stage_a_sha256}
        and receipt.get("candidate")
        == {"path": relative(G0135_RESULT_PATH), "sha256": G0135_RESULT_SHA256}
        and receipt.get("g0139_result_audit")
        == {"path": relative(G0139_RECEIPT_PATH), "sha256": G0139_RECEIPT_SHA256},
        "Stage-B mandatory input binding drift",
    )
    expected_source_bindings = dict(manifest_bindings)
    expected_source_bindings[relative(MANIFEST_PATH)] = manifest_sha256
    expected_source_bindings[relative(STAGE_A_PATH)] = stage_a_sha256
    raw_source_bindings = receipt.get("source_and_input_bindings")
    require(
        isinstance(raw_source_bindings, dict)
        and set(raw_source_bindings) == set(expected_source_bindings),
        "Stage-B source/input custody key drift",
    )
    for key, expected_digest in expected_source_bindings.items():
        path, digest = validate_binding(
            raw_source_bindings[key], f"Stage-B source/input {key}"
        )
        require(
            path == key and digest == expected_digest,
            f"Stage-B source/input custody drift: {key}",
        )

    raw_rows = receipt.get("rows")
    require(
        isinstance(raw_rows, list) and len(raw_rows) == POOL_ROWS,
        "Stage-B Pool128 row census drift",
    )
    rows: list[list[int]] = []
    exact_dots: list[int] = []
    aggregate = hashlib.sha256()
    for index, (raw_row, direction, residual) in enumerate(
        zip(raw_rows, directions, residuals, strict=True)
    ):
        require(
            isinstance(raw_row, dict) and set(raw_row) == STAGE_B_ROW_KEYS,
            f"Stage-B row {index} key drift",
        )
        raw_coordinates = raw_row.get("hinge_coefficients")
        require(
            isinstance(raw_coordinates, list)
            and len(raw_coordinates) == expected_records
            and all(
                isinstance(value, int)
                and not isinstance(value, bool)
                and -(1 << 63) <= value < (1 << 63)
                for value in raw_coordinates
            ),
            f"Stage-B row {index} coordinate shape/i64 drift",
        )
        coordinates = [int(value) for value in raw_coordinates]
        encoded = b"".join(
            value.to_bytes(8, "little", signed=True) for value in coordinates
        )
        row_digest = hashlib.sha256(encoded).hexdigest()
        exact_dot = sum(
            coefficient * coordinates[sequence]
            for sequence, coefficient in member_terms
        )
        require(
            raw_row.get("index") == index
            and raw_row.get("direction") == direction
            and canonical_integer(
                raw_row.get("exact_stage_a_residual"),
                f"Stage-B row {index} Stage-A residual",
                nonzero=True,
            )
            == residual
            and canonical_integer(
                raw_row.get("exact_candidate_dot"),
                f"Stage-B row {index} candidate dot",
                nonzero=True,
            )
            == exact_dot
            == residual
            and raw_row.get("records") == expected_records
            and raw_row.get("nonzero_hinge_coefficients")
            == sum(value != 0 for value in coordinates)
            and raw_row.get("minimum_hinge_coefficient") == min(coordinates)
            and raw_row.get("maximum_hinge_coefficient") == max(coordinates)
            and raw_row.get("maximum_absolute_hinge_coefficient")
            == max(abs(value) for value in coordinates)
            and raw_row.get("hinge_coefficients_i64_le_sha256") == row_digest,
            f"Stage-B row {index} exact receipt drift",
        )
        aggregate.update(encoded)
        exact_dots.append(exact_dot)
        rows.append(coordinates)

    require(
        aggregate.hexdigest() == receipt.get("direction_major_hinge_i64_le_sha256")
        and exact_dots == list(residuals)
        and receipt.get("exact_candidate_dots")
        == [str(value) for value in exact_dots]
        and receipt.get("exact_candidate_dots_decimal_lf_sha256")
        == digest_decimal_lf(exact_dots),
        "Stage-B aggregate coordinate/exact-dot bridge drift",
    )
    controls = receipt.get("input_mutation_controls")
    require(
        isinstance(controls, dict)
        and set(controls) == STAGE_B_INPUT_MUTATION_CONTROL_KEYS
        and all(value is True for value in controls.values()),
        "Stage-B input mutation controls drift",
    )
    mutant = receipt.get("coefficient_plus_one_mutant")
    require(
        isinstance(mutant, dict)
        and set(mutant) == STAGE_B_COEFFICIENT_MUTANT_KEYS
        and isinstance(mutant.get("sequence"), int)
        and not isinstance(mutant.get("sequence"), bool)
        and 0 <= mutant["sequence"] < expected_records
        and mutant.get("coefficient_delta") == "+1"
        and mutant.get("baseline_exact_dots_decimal_lf_sha256")
        == receipt.get("exact_candidate_dots_decimal_lf_sha256")
        and is_sha256(mutant.get("mutated_exact_dots_decimal_lf_sha256"))
        and mutant.get("mutated_exact_dots_decimal_lf_sha256")
        != mutant.get("baseline_exact_dots_decimal_lf_sha256")
        and isinstance(mutant.get("changed_rows"), int)
        and not isinstance(mutant.get("changed_rows"), bool)
        and 0 < mutant["changed_rows"] <= POOL_ROWS
        and mutant.get("rejected") is True,
        "Stage-B coefficient-plus-one hostile control drift",
    )
    return rows


def rehash_snapshot(snapshot: dict[str, str]) -> None:
    for name, expected in sorted(snapshot.items()):
        path = contained(ROOT / name)
        require(path.is_file(), f"bound input vanished: {name}")
        require_digest(sha256_path(path), expected, f"end-bound input {name}")


def load_g0135_base_preflight() -> tuple[list[int], dict[str, Any], Any, dict[str, Any]]:
    require_digest(
        sha256_path(G0135_SOURCE_PATH), G0135_SOURCE_SHA256, "G-0135 Stage-C source"
    )
    producer = load_module(G0135_SOURCE_PATH, "g0140_stage_c_g0135_loader")
    prepared = producer.load_validated_inputs(
        G0135_MANIFEST_PATH,
        G0135_STAGE_A_PATH,
        G0135_STAGE_B_PATH,
    )
    ancestor = prepared["ancestor"]
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, loader = producer.validate_warm_start(prepared, cache)
        for sequence in (0, RECORDS - 1):
            column = loader(sequence)
            require(len(column) == BASE_ROWS, "G-0135 inherited loader width drift")
    require(
        len(prepared["target"]) == BASE_ROWS
        and warm_receipt["appended_rows"] == 32
        and warm_receipt["appended_rows_reject_old_member"] is True,
        "G-0135 inherited warm-start validation drift",
    )
    return [int(value) for value in prepared["target"]], warm_receipt, producer, prepared


def load_validated_future_inputs(
    manifest_path: Path, stage_a_path: Path, stage_b_path: Path
) -> dict[str, Any]:
    manifest_path = contained(manifest_path)
    stage_a_path = contained(stage_a_path)
    stage_b_path = contained(stage_b_path)
    require(manifest_path == MANIFEST_PATH, "G-0140 manifest path drift")
    require(stage_a_path == STAGE_A_PATH, "G-0140 Stage-A path drift")
    require(stage_b_path == STAGE_B_PATH, "G-0140 Stage-B path drift")
    require(
        manifest_path.is_file() and stage_a_path.is_file() and stage_b_path.is_file(),
        "future G-0140 manifest/Stage-A/Stage-B input missing",
    )
    require(G0139_RECEIPT_PATH.is_file(), "mandatory G-0139 audit receipt missing")
    require_digest(
        sha256_path(G0139_RECEIPT_PATH), G0139_RECEIPT_SHA256, "G-0139 receipt"
    )
    require(
        git_commit_for_path(G0139_RECEIPT_PATH) == G0139_RECEIPT_COMMIT,
        "G-0139 receipt Git commit drift",
    )

    runtime = validate_python_runtime()
    native_build = validate_native_build_receipt()
    fixed = validate_fixed_inputs()
    validate_g0139_admission(load_json(G0139_RECEIPT_PATH))
    script_sha256 = sha256_path(SCRIPT)
    manifest_sha256 = sha256_path(manifest_path)
    stage_a_sha256 = sha256_path(stage_a_path)
    stage_b_sha256 = sha256_path(stage_b_path)
    manifest = load_json(manifest_path)
    manifest_bindings = validate_manifest(manifest, manifest_sha256, script_sha256)
    member_terms = validate_g0135_member(load_json(G0135_RESULT_PATH))
    stage_a = load_json(stage_a_path)
    directions, residuals = validate_stage_a_pool(stage_a, manifest_sha256)
    stage_b = load_json(stage_b_path)
    stage_b_rows = validate_stage_b_prices(
        stage_b,
        manifest_sha256=manifest_sha256,
        manifest_bindings=manifest_bindings,
        stage_a_sha256=stage_a_sha256,
        directions=directions,
        residuals=residuals,
        member_terms=member_terms,
    )
    base_target, warm_receipt, g0135_producer, g0135_prepared = (
        load_g0135_base_preflight()
    )
    member = load_json(G0135_RESULT_PATH)
    require(
        member.get("target") == base_target,
        "inherited G-0135 target differs from committed member receipt",
    )
    target = base_target + [0] * POOL_ROWS

    snapshot = dict(manifest_bindings)
    for path, digest in fixed.items():
        snapshot_add(snapshot, path, digest, "fixed input")
    snapshot_add(
        snapshot,
        relative(G0139_RECEIPT_PATH),
        G0139_RECEIPT_SHA256,
        "G-0139",
    )
    snapshot_add(snapshot, relative(MANIFEST_PATH), manifest_sha256, "manifest")
    snapshot_add(snapshot, relative(STAGE_A_PATH), stage_a_sha256, "Stage A")
    snapshot_add(snapshot, relative(STAGE_B_PATH), stage_b_sha256, "Stage B")
    snapshot_add(snapshot, relative(SCRIPT), script_sha256, "selector")
    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "stage_a": stage_a,
        "stage_a_sha256": stage_a_sha256,
        "stage_b": stage_b,
        "stage_b_sha256": stage_b_sha256,
        "stage_b_rows": stage_b_rows,
        "directions": directions,
        "residuals": residuals,
        "target": target,
        "warm_receipt": warm_receipt,
        "g0135_producer": g0135_producer,
        "g0135_prepared": g0135_prepared,
        "snapshot": snapshot,
        "script_sha256": script_sha256,
        "runtime": runtime,
        "native_build": native_build,
    }


def future_interface() -> dict[str, Any]:
    return {
        "schema": "max11-g0140-stage-c-selector-interface-v1",
        "mode": "OUTCOME_BLIND_FROZEN_PRODUCER_AWAITING_INPUTS_AND_SOURCE_AUDIT",
        "manifest": {"path": relative(MANIFEST_PATH), "schema": MANIFEST_SCHEMA},
        "stage_a": {"path": relative(STAGE_A_PATH), "schema": STAGE_A_SCHEMA},
        "stage_b": {"path": relative(STAGE_B_PATH), "schema": STAGE_B_SCHEMA},
        "selector_output": {"path": relative(OUTPUT_PATH), "schema": OUTPUT_SCHEMA},
        "downstream_master": {
            "path": relative(MASTER_OUTPUT_PATH),
            "schema": MASTER_OUTPUT_SCHEMA,
        },
        "downstream_global_replay": {
            "path": relative(GLOBAL_REPLAY_OUTPUT_PATH),
            "schema": GLOBAL_REPLAY_OUTPUT_SCHEMA,
        },
        "rows": LOGICAL_ROWS,
        "records": RECORDS,
        "pool_rows": POOL_ROWS,
        "admit_limit": ADMIT_ROWS,
        "stage_order": STAGE_ORDER,
        "modular_primes": list(FIXED_MODULAR_PRIMES),
        "modular_role": MODULAR_ROLE,
        "native_proposer": {
            "source": relative(NATIVE_PROPOSER_SOURCE_PATH),
            "binary": relative(NATIVE_PROPOSER_PATH),
            "build_receipt": relative(NATIVE_BUILD_RECEIPT_PATH),
            "schema": NATIVE_PROPOSER_SCHEMA,
            "matrix_layout": "row_major_transpose_family_columns",
        },
        "launcher": relative(LAUNCHER_PATH),
        "native_test": relative(NATIVE_TEST_PATH),
        "stage_c_source_audit": {
            "path": relative(STAGE_C_SOURCE_AUDIT_PATH),
            "schema": STAGE_C_SOURCE_AUDIT_SCHEMA,
        },
        "scientific_execution_enabled_after_all_frozen_gates_pass": True,
        "scientific_result_written": False,
    }


def preflight(
    manifest_path: Path, stage_a_path: Path, stage_b_path: Path
) -> dict[str, Any]:
    require(not OUTPUT_PATH.exists(), "scientific selector output already exists")
    prepared = load_validated_future_inputs(manifest_path, stage_a_path, stage_b_path)
    rehash_snapshot(prepared["snapshot"])
    require_digest(sha256_path(SCRIPT), prepared["script_sha256"], "selector source")
    return {
        "result": "G0140_STAGE_C_SELECTOR_PREFLIGHT_PASS",
        "rows": LOGICAL_ROWS,
        "records": RECORDS,
        "pool_rows": POOL_ROWS,
        "admit_limit": ADMIT_ROWS,
        "stage_b_rows_validated": len(prepared["stage_b_rows"]),
        "runtime": prepared["runtime"],
        "target_i128le_sha256": digest_i128(prepared["target"]),
        "input_snapshot_sha256": input_snapshot_digest(prepared["snapshot"]),
        "complete_matrix_rank_computation_run": False,
        "scientific_result_written": False,
    }


def static_preflight() -> dict[str, Any]:
    """Check frozen local bytes without consuming not-yet-published science."""

    require(not OUTPUT_PATH.exists(), "scientific selector output already exists")
    runtime = validate_python_runtime()
    fixed = validate_fixed_inputs()
    for path in (
        SCRIPT,
        NATIVE_PROPOSER_SOURCE_PATH,
        NATIVE_PROPOSER_PATH,
        NATIVE_BUILD_RECEIPT_PATH,
        NATIVE_TEST_PATH,
        LAUNCHER_PATH,
    ):
        resolved = contained(path)
        require(resolved.is_file(), f"Stage-C frozen subject missing: {path}")
        git_commit_for_path(resolved)
    require(
        os.access(NATIVE_PROPOSER_PATH, os.X_OK),
        "frozen native proposer is not executable",
    )
    validate_native_build_receipt()
    future_paths = {
        "manifest": MANIFEST_PATH,
        "stage_a": STAGE_A_PATH,
        "stage_b": STAGE_B_PATH,
        "g0139": G0139_RECEIPT_PATH,
        "g0150": G0150_SOURCE_AUDIT_PATH,
        "stage_b_source_audit": STAGE_B_SOURCE_AUDIT_PATH,
        "stage_c_source_audit": STAGE_C_SOURCE_AUDIT_PATH,
    }
    present = {label: path.is_file() for label, path in future_paths.items()}
    return {
        "result": "G0140_STAGE_C_STATIC_PREFLIGHT_PASS",
        "rows": LOGICAL_ROWS,
        "records": RECORDS,
        "pool_rows": POOL_ROWS,
        "admit_limit": ADMIT_ROWS,
        "selector_sha256": sha256_path(SCRIPT),
        "native_source_sha256": sha256_path(NATIVE_PROPOSER_SOURCE_PATH),
        "native_binary_sha256": sha256_path(NATIVE_PROPOSER_PATH),
        "native_build_receipt_sha256": sha256_path(NATIVE_BUILD_RECEIPT_PATH),
        "native_test_sha256": sha256_path(NATIVE_TEST_PATH),
        "launcher_sha256": sha256_path(LAUNCHER_PATH),
        "runtime": runtime,
        "fixed_input_snapshot_sha256": input_snapshot_digest(fixed),
        "future_inputs_present": present,
        "all_future_inputs_present": all(present.values()),
        "complete_matrix_rank_computation_run": False,
        "scientific_result_written": False,
    }


def scientific_run(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    begun = time.perf_counter()
    output_path = contained(output_path)
    require(output_path == OUTPUT_PATH, "Stage-C selector output path drift")
    require(not output_path.exists(), "refusing to overwrite Stage-C selector output")
    prepared = load_validated_future_inputs(
        manifest_path, stage_a_path, stage_b_path
    )
    g0135_prepared = prepared["g0135_prepared"]
    g0135_producer = prepared["g0135_producer"]
    ancestor = g0135_prepared["ancestor"]

    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        inherited_warm, inherited_loader = g0135_producer.validate_warm_start(
            g0135_prepared, cache
        )
        require(
            inherited_warm == prepared["warm_receipt"],
            "G-0135 inherited warm-start changed between preflight and run",
        )

        def column_loader(sequence: int) -> list[int]:
            require(0 <= sequence < RECORDS, "full column sequence outside family")
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(row[sequence] for row in prepared["stage_b_rows"])
            require(len(column) == LOGICAL_ROWS, "full M column width drift")
            return column

        for sequence in (0, RECORDS - 1):
            column_loader(sequence)

        proposals, native_executions = native_modular_proposals(
            column_loader=column_loader,
            row_count=LOGICAL_ROWS,
            record_count=RECORDS,
            threads=MANIFEST_PARAMETERS["threads"],
        )
        proposed_union = sorted(
            {
                sequence
                for proposal in proposals
                for sequence in proposal["selected_sequences"]
            }
        )
        complete_basis = certify_complete_column_basis(
            column_loader=column_loader,
            row_count=LOGICAL_ROWS,
            record_count=RECORDS,
            proposed_sequences=proposed_union,
            proposal_receipts=proposals,
        )
        selection = exact_rank_selection(
            column_loader=column_loader,
            complete_basis=complete_basis,
            target=prepared["target"],
            base_rows=BASE_ROWS,
            pool_rows=POOL_ROWS,
            admit_rows=ADMIT_ROWS,
            record_count=RECORDS,
        )

    require(
        len(selection["prefix_rank_transcript"]["ranks"]) == POOL_ROWS + 1
        and selection["prefix_rank_transcript"]["exact_q"] is True,
        "scientific prefix-rank transcript census drift",
    )
    if selection["incompatible_dependency"] is not None:
        claim_boundary = (
            "Exact nonmembership only for the frozen 540-row target against the "
            "frozen 163,740-column family; not a global identity, network, "
            "family-completeness theorem, or MAX11 result."
        )
    elif selection["selected_count"] < ADMIT_ROWS:
        claim_boundary = (
            "Exact complete-matrix rank gain below 32 for the frozen Pool128; "
            "no reopened master or global identity was run."
        )
    else:
        claim_boundary = (
            "Exact rank-aware selection of the first 32 growing Pool128 rows; "
            "this is not a membership, global identity, or MAX11 result."
        )

    result = {
        "schema": OUTPUT_SCHEMA,
        "result": selection["result"],
        "claim_boundary": claim_boundary,
        "manifest": {
            "path": relative(MANIFEST_PATH),
            "sha256": prepared["manifest_sha256"],
        },
        "stage_a_receipt": {
            "path": relative(STAGE_A_PATH),
            "sha256": prepared["stage_a_sha256"],
        },
        "stage_b_receipt": {
            "path": relative(STAGE_B_PATH),
            "sha256": prepared["stage_b_sha256"],
        },
        "g0139_admission_receipt": {
            "path": relative(G0139_RECEIPT_PATH),
            "sha256": prepared["snapshot"][relative(G0139_RECEIPT_PATH)],
        },
        "stage_c_source_audit": {
            "path": relative(STAGE_C_SOURCE_AUDIT_PATH),
            "sha256": prepared["snapshot"][relative(STAGE_C_SOURCE_AUDIT_PATH)],
        },
        "solver": {"path": relative(SCRIPT), "sha256": prepared["script_sha256"]},
        "launcher": {
            "path": relative(LAUNCHER_PATH),
            "sha256": prepared["snapshot"][relative(LAUNCHER_PATH)],
        },
        "runtime": prepared["runtime"],
        "native_proposer": {
            "source": {
                "path": relative(NATIVE_PROPOSER_SOURCE_PATH),
                "sha256": prepared["snapshot"][
                    relative(NATIVE_PROPOSER_SOURCE_PATH)
                ],
            },
            "binary": {
                "path": relative(NATIVE_PROPOSER_PATH),
                "sha256": prepared["snapshot"][relative(NATIVE_PROPOSER_PATH)],
            },
            "build_receipt": {
                "path": relative(NATIVE_BUILD_RECEIPT_PATH),
                "sha256": prepared["snapshot"][
                    relative(NATIVE_BUILD_RECEIPT_PATH)
                ],
            },
            "role": MODULAR_ROLE,
            "executions": native_executions,
        },
        "rows": LOGICAL_ROWS,
        "base_rows": BASE_ROWS,
        "pool_rows": POOL_ROWS,
        "records": RECORDS,
        "admit_limit": ADMIT_ROWS,
        "target": [str(value) for value in prepared["target"]],
        "target_i128le_sha256": digest_i128(prepared["target"]),
        "target_construction": (
            "immutable_G0135_412_entry_unscaled_target_followed_by_128_exact_zeros"
        ),
        "row_order": [
            "immutable_prefix:G-0135:412",
            "pool:G-0140-stage-A-receipt-order:128",
        ],
        "inherited_g0135_warm_start": inherited_warm,
        "complete_column_basis": complete_basis,
        "rank_selection": selection,
        "input_snapshot_sha256": input_snapshot_digest(prepared["snapshot"]),
        "inputs_rehashed_at_end": False,
        "wall_seconds": 0.0,
        "maximum_rss_kib": 0,
    }
    rehash_snapshot(prepared["snapshot"])
    ancestor.validate_expected_inputs(include_future=True)
    require_digest(sha256_path(SCRIPT), prepared["script_sha256"], "selector source")
    require_digest(
        sha256_path(NATIVE_PROPOSER_PATH),
        prepared["snapshot"][relative(NATIVE_PROPOSER_PATH)],
        "native proposer binary",
    )
    result["inputs_rehashed_at_end"] = True
    result["wall_seconds"] = time.perf_counter() - begun
    result["maximum_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_exclusive(output_path, result)
    return result


def expect_rejected(
    action: Callable[[], object], label: str, rejected: list[str]
) -> None:
    try:
        action()
    except SelectorError:
        rejected.append(label)
        return
    raise SelectorError(f"hostile control escaped: {label}")


def fixture_columns(rows: Sequence[Sequence[int]]) -> list[list[int]]:
    require(bool(rows) and bool(rows[0]), "fixture rows are empty")
    width = len(rows[0])
    require(all(len(row) == width for row in rows), "fixture rows are ragged")
    return [[int(row[column]) for row in rows] for column in range(width)]


def fixture_complete_basis(
    rows: Sequence[Sequence[int]], *, prime: int = 101
) -> tuple[list[list[int]], dict[str, Any]]:
    columns = fixture_columns(rows)
    proposal = modular_column_proposal(
        column_loader=columns.__getitem__,
        row_count=len(rows),
        record_count=len(columns),
        prime=prime,
    )
    certificate = certify_complete_column_basis(
        column_loader=columns.__getitem__,
        row_count=len(rows),
        record_count=len(columns),
        proposed_sequences=proposal["selected_sequences"],
        proposal_receipts=[proposal],
    )
    return columns, certificate


def self_test() -> None:
    rejected: list[str] = []
    validate_python_runtime()

    g0139 = load_json(G0139_RECEIPT_PATH)
    validate_g0139_admission(g0139)
    g0139_mutants: list[tuple[str, dict[str, Any]]] = []
    for label in (
        "wrong subject commit",
        "false evidence class",
        "false lineage and outcome awareness",
        "empty claim boundary",
        "missing custody",
        "false source-audit anchor",
    ):
        g0139_mutants.append((label, json.loads(json.dumps(g0139))))
    g0139_mutants[0][1]["subject"]["git_commit"] = "0" * 40
    g0139_mutants[1][1]["evidence_class"] = "T2_INDEPENDENT_REPLAY"
    g0139_mutants[2][1]["reviewer"]["same_model_lineage"] = False
    g0139_mutants[2][1]["preregistration"]["outcome_aware"] = False
    g0139_mutants[3][1]["claim_boundary"] = ""
    del g0139_mutants[4][1]["input_custody"]
    g0139_mutants[5][1]["source_audit_anchor"]["sha256"] = "0" * 64
    g0139_mutants[5][1]["source_audit_anchor"]["verdict"] = "FAIL"
    missing_candidate = json.loads(json.dumps(g0139))
    del missing_candidate["input_custody"]["fixed_inputs"][relative(G0135_RESULT_PATH)]
    missing_candidate["input_custody"]["fixed_inputs"]["fixture/replacement"] = (
        "6" * 64
    )
    g0139_mutants.append(("missing candidate fixed binding", missing_candidate))
    wrong_candidate = json.loads(json.dumps(g0139))
    wrong_candidate["input_custody"]["fixed_inputs"][relative(G0135_RESULT_PATH)] = (
        "f" * 64
    )
    g0139_mutants.append(("wrong candidate fixed binding", wrong_candidate))
    displaced_candidate = json.loads(json.dumps(missing_candidate))
    displaced_candidate["unrelated_recursive_decoy"] = {
        "path": relative(G0135_RESULT_PATH),
        "sha256": G0135_RESULT_SHA256,
    }
    g0139_mutants.append(
        ("missing candidate with recursive decoy", displaced_candidate)
    )
    for label, mutant in g0139_mutants:
        expect_rejected(
            lambda mutant=mutant: validate_g0139_admission(mutant),
            f"G-0139 {label}",
            rejected,
        )

    def audit_fixture(
        *,
        schema: str,
        claim_boundary: str,
        no_claim: str,
        required_checks: dict[str, bool],
        preregistration_path: Path,
        named_bindings: dict[str, tuple[str, str]],
    ) -> dict[str, Any]:
        return {
            "schema": schema,
            "verdict": "PASS",
            "result": SOURCE_CUSTODY_PASS_RESULT,
            "evidence_class": SOURCE_AUDIT_EVIDENCE_CLASS,
            "claim_boundary": claim_boundary,
            "reviewer": {
                "agent_name": "FreshReviewer",
                "program": "codex",
                "model": "gpt-5",
                "same_model_lineage": True,
                "fresh_context": True,
            },
            "preregistration": {
                "path": relative(preregistration_path),
                "sha256": "0" * 64,
                "git_commit": "0" * 40,
                "committed_and_pushed_before_subject_source_inspection": True,
                "committed_and_pushed_before_runtime_checks": True,
            },
            "subject": {
                "git_commit": "0" * 40,
                "commit_object_and_working_bytes_equal_for_all_bindings": True,
                "bindings": {
                    label: {"path": path, "sha256": digest}
                    for label, (path, digest) in named_bindings.items()
                },
            },
            "required_checks": required_checks,
            "scientific_manifest_observed": False,
            "scientific_input_observed": False,
            "scientific_output_observed": False,
            "scientific_replay_run": False,
            "no_claim": no_claim,
        }

    audit_cases = [
        (
            G0150_SCHEMA,
            G0150_CLAIM_BOUNDARY,
            G0150_NO_CLAIM,
            G0150_REQUIRED_CHECKS,
            G0150_AUDIT_PREREGISTRATION_PATH,
            {
                "main_source": (relative(STAGE_A_SOURCE_PATH), "0" * 64),
                "engine_source": (
                    relative(STAGE_A_SOURCE_PATH.parent / "engine.rs"),
                    "1" * 64,
                ),
                "cargo_manifest": (
                    relative(STAGE_A_SOURCE_PATH.parent.parent / "Cargo.toml"),
                    "2" * 64,
                ),
                "cargo_lock": (
                    relative(STAGE_A_SOURCE_PATH.parent.parent / "Cargo.lock"),
                    "3" * 64,
                ),
                "release_executable": (
                    relative(
                        STAGE_A_SOURCE_PATH.parent.parent
                        / "target/release/g0140-stage-a-pool128-global-replay"
                    ),
                    "4" * 64,
                ),
            },
        ),
        (
            STAGE_B_SOURCE_AUDIT_SCHEMA,
            STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY,
            STAGE_B_SOURCE_AUDIT_NO_CLAIM,
            STAGE_B_SOURCE_AUDIT_REQUIRED_CHECKS,
            STAGE_B_AUDIT_PREREGISTRATION_PATH,
            {
                "main_source": (relative(STAGE_B_SOURCE_PATH), "5" * 64),
                "cargo_manifest": (
                    relative(STAGE_B_SOURCE_PATH.parent.parent / "Cargo.toml"),
                    "6" * 64,
                ),
                "cargo_lock": (
                    relative(STAGE_B_SOURCE_PATH.parent.parent / "Cargo.lock"),
                    "7" * 64,
                ),
                "release_executable": (
                    relative(
                        STAGE_B_SOURCE_PATH.parent.parent
                        / "target/release/g0140-stage-b-pool128-coordinate-pricer"
                    ),
                    "8" * 64,
                ),
            },
        ),
        (
            STAGE_C_SOURCE_AUDIT_SCHEMA,
            STAGE_C_SOURCE_AUDIT_CLAIM_BOUNDARY,
            STAGE_C_SOURCE_AUDIT_NO_CLAIM,
            STAGE_C_SOURCE_AUDIT_REQUIRED_CHECKS,
            STAGE_C_AUDIT_PREREGISTRATION_PATH,
            {
                "selector_source": (relative(SCRIPT), "9" * 64),
                "native_proposer_source": (
                    relative(NATIVE_PROPOSER_SOURCE_PATH),
                    "a" * 64,
                ),
                "native_proposer_executable": (
                    relative(NATIVE_PROPOSER_PATH),
                    "b" * 64,
                ),
                "native_build_receipt": (
                    relative(NATIVE_BUILD_RECEIPT_PATH),
                    "c" * 64,
                ),
                "native_test": (relative(NATIVE_TEST_PATH), "d" * 64),
                "launcher": (relative(LAUNCHER_PATH), "e" * 64),
            },
        ),
    ]
    for (
        schema,
        claim_boundary,
        no_claim,
        required_checks,
        preregistration_path,
        named_bindings,
    ) in audit_cases:
        validate_source_audit_shape(
            audit_fixture(
                schema=schema,
                claim_boundary=claim_boundary,
                no_claim=no_claim,
                required_checks=required_checks,
                preregistration_path=preregistration_path,
                named_bindings=named_bindings,
            ),
            schema=schema,
            claim_boundary=claim_boundary,
            no_claim=no_claim,
            required_checks=required_checks,
            preregistration_path=relative(preregistration_path),
            named_bindings=named_bindings,
            subject_commit="0" * 40,
        )

    own_case = audit_cases[-1]
    own_fixture = audit_fixture(
        schema=own_case[0],
        claim_boundary=own_case[1],
        no_claim=own_case[2],
        required_checks=own_case[3],
        preregistration_path=own_case[4],
        named_bindings=own_case[5],
    )

    def reject_audit(mutant: dict[str, Any], label: str) -> None:
        expect_rejected(
            lambda: validate_source_audit_shape(
                mutant,
                schema=own_case[0],
                claim_boundary=own_case[1],
                no_claim=own_case[2],
                required_checks=own_case[3],
                preregistration_path=relative(own_case[4]),
                named_bindings=own_case[5],
                subject_commit="0" * 40,
            ),
            label,
            rejected,
        )

    mutant = json.loads(json.dumps(own_fixture))
    mutant["unknown_extension"] = True
    reject_audit(mutant, "source audit unknown envelope")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["audit_git_commit"] = "0" * 40
    reject_audit(mutant, "source audit self reference")
    mutant = json.loads(json.dumps(own_fixture))
    displaced = mutant["subject"].pop("bindings")
    mutant["unrelated_receipt_lookalikes"] = displaced
    reject_audit(mutant, "source audit displaced bindings")
    mutant = json.loads(json.dumps(own_fixture))
    decoy = mutant["subject"]["bindings"].pop("selector_source")
    mutant["subject"]["unrelated_selector_decoy"] = decoy
    reject_audit(mutant, "source audit missing named binding with decoy")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["subject"]["bindings"]["native_proposer_source"]["path"] = mutant[
        "subject"
    ]["bindings"]["selector_source"]["path"]
    reject_audit(mutant, "source audit duplicate subject path")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["subject"]["unknown"] = True
    reject_audit(mutant, "source audit unknown subject field")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["schema"] = "lookalike-source-audit"
    reject_audit(mutant, "source audit wrong schema")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["required_checks"]["native_oracle_passed"] = False
    reject_audit(mutant, "source audit false required check")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["required_checks"]["native_oracle_passed"] = 1
    reject_audit(mutant, "source audit integer required check")
    mutant = json.loads(json.dumps(own_fixture))
    mutant["scientific_input_observed"] = True
    reject_audit(mutant, "source audit scientific observation")

    stage_b_case = audit_cases[-2]
    stage_b_fixture = audit_fixture(
        schema=stage_b_case[0],
        claim_boundary=stage_b_case[1],
        no_claim=stage_b_case[2],
        required_checks=stage_b_case[3],
        preregistration_path=stage_b_case[4],
        named_bindings=stage_b_case[5],
    )

    def reject_stage_b_audit(mutant: dict[str, Any], label: str) -> None:
        expect_rejected(
            lambda: validate_source_audit_shape(
                mutant,
                schema=stage_b_case[0],
                claim_boundary=stage_b_case[1],
                no_claim=stage_b_case[2],
                required_checks=stage_b_case[3],
                preregistration_path=relative(stage_b_case[4]),
                named_bindings=stage_b_case[5],
                subject_commit="0" * 40,
            ),
            label,
            rejected,
        )

    mutant = json.loads(json.dumps(stage_b_fixture))
    mutant["schema"] = "max11-g0151-g0140-stage-b-final2-source-audit-v1"
    reject_stage_b_audit(mutant, "Stage-B audit retired schema")
    mutant = json.loads(json.dumps(stage_b_fixture))
    del mutant["required_checks"][
        "g0139_subject_and_exact_fixed_inputs_gate_verified"
    ]
    reject_stage_b_audit(mutant, "Stage-B audit missing G-0139 gate check")
    mutant = json.loads(json.dumps(stage_b_fixture))
    mutant["required_checks"][
        "g0139_subject_and_exact_fixed_inputs_gate_verified"
    ] = False
    reject_stage_b_audit(mutant, "Stage-B audit false G-0139 gate check")
    mutant = json.loads(json.dumps(stage_b_fixture))
    mutant["required_checks"][
        "g0139_subject_and_exact_fixed_inputs_gate_verified"
    ] = 1
    reject_stage_b_audit(mutant, "Stage-B audit integer G-0139 gate check")
    mutant = json.loads(json.dumps(stage_b_fixture))
    del mutant["required_checks"][
        "g0139_subject_and_exact_fixed_inputs_gate_verified"
    ]
    mutant["unrelated_recursive_decoy"] = {
        "g0139_subject_and_exact_fixed_inputs_gate_verified": True
    }
    reject_stage_b_audit(mutant, "Stage-B audit displaced G-0139 gate check")

    def crosscheck_prefix_profile(
        columns: Sequence[Sequence[int]],
        basis: dict[str, Any],
        base_rows: int,
        pool_rows: int,
    ) -> None:
        rows = matrix_rows(
            [columns[index] for index in basis["basis_sequences"]],
            base_rows + pool_rows,
        )
        fast = exact_prefix_rank_transcript(
            complete_basis_rows=rows,
            base_rows=base_rows,
            pool_rows=pool_rows,
        )["ranks"]
        slow = repeated_exact_prefix_ranks(rows, base_rows, pool_rows)
        require(fast == slow, "transpose-RREF prefix theorem oracle mismatch")

    # A whole exact direction can vanish modulo the proposal prime.  Exact
    # completion must find it and finish with a full zero annihilator scan.
    bad_prime = FIXED_MODULAR_PRIMES[0]
    bad_prime_columns = [
        [1, 0, 0, 0],
        [0, bad_prime, 0, 0],
        [0, 0, 1, 0],
        [1, bad_prime, 1, 0],
        [2, 0, 1, 0],
    ]
    bad_proposal = modular_column_proposal(
        column_loader=bad_prime_columns.__getitem__,
        row_count=4,
        record_count=len(bad_prime_columns),
        prime=bad_prime,
    )
    require(
        bad_proposal["selected_sequences"] == [0, 2],
        "false-modular-zero fixture did not hide the exact column",
    )
    repaired = certify_complete_column_basis(
        column_loader=bad_prime_columns.__getitem__,
        row_count=4,
        record_count=len(bad_prime_columns),
        proposed_sequences=bad_proposal["selected_sequences"],
        proposal_receipts=[bad_proposal],
    )
    require(
        repaired["basis_sequences"] == [0, 1, 2]
        and repaired["basis_rank"] == 3
        and repaired["initial_exact_rank"] == 2
        and repaired["completion_passes"][0]["first_violating_sequence"] == 1
        and repaired["completion_passes"][-1]["columns_scanned"]
        == len(bad_prime_columns)
        and repaired["completion_passes"][-1]["nonzero_prices"] == 0,
        "exact completion failed to repair a modular false zero",
    )

    # The only missing exact direction is the final canonical column.
    final_columns = [[1, 0], [2, 0], [0, bad_prime]]
    final_proposal = modular_column_proposal(
        column_loader=final_columns.__getitem__,
        row_count=2,
        record_count=3,
        prime=bad_prime,
    )
    final_certificate = certify_complete_column_basis(
        column_loader=final_columns.__getitem__,
        row_count=2,
        record_count=3,
        proposed_sequences=final_proposal["selected_sequences"],
        proposal_receipts=[final_proposal],
    )
    require(
        final_certificate["completion_passes"][0]["first_violating_sequence"] == 2
        and final_certificate["completion_passes"][0]["columns_scanned"] == 3,
        "omitted-final-column positive fixture drift",
    )
    truncated = json.loads(json.dumps(final_certificate))
    truncated["completion_passes"][0]["columns_scanned"] = 2
    expect_rejected(
        lambda: validate_completion_scan_census(truncated, record_count=3),
        "omitted final column census",
        rejected,
    )

    # Compatible dependencies, one growth row, then an incompatible dependency
    # yielding a complete-family separator.
    mixed_rows = [
        [1, 0, 1, 0],
        [0, 1, 1, 0],
        [1, 1, 2, 0],
        [0, 0, 0, 1],
        [0, 0, 0, 2],
        [1, 0, 1, 0],
    ]
    mixed_columns, mixed_basis = fixture_complete_basis(mixed_rows)
    crosscheck_prefix_profile(mixed_columns, mixed_basis, 2, 4)
    mixed_target = [1, -1, 0, 0, 0, 0]
    mixed = exact_rank_selection(
        column_loader=mixed_columns.__getitem__,
        complete_basis=mixed_basis,
        target=mixed_target,
        base_rows=2,
        pool_rows=4,
        admit_rows=2,
        record_count=len(mixed_columns),
    )
    require(
        mixed["result"] == "SYNTHETIC_INCOMPATIBLE_DEPENDENCY"
        and mixed["prefix_rank_transcript"]["ranks"] == [2, 2, 3, 3, 3]
        and mixed["selected_pool_indices"] == [1]
        and [item["compatible"] for item in mixed["dependency_certificates"]]
        == [True, True, False]
        and mixed["incompatible_dependency"]["separator_replay"][
            "columns_scanned"
        ]
        == len(mixed_columns),
        "compatible/incompatible dependency fixture drift",
    )
    mutated_separator = mixed["incompatible_dependency"]["separator"][:]
    mutated_separator[0] += 1
    expect_rejected(
        lambda: exact_separator_replay(
            column_loader=mixed_columns.__getitem__,
            separator=mutated_separator,
            target=mixed_target,
            record_count=len(mixed_columns),
        ),
        "separator coordinate plus one",
        rejected,
    )

    # An incompatible dependency terminates before a later rank-growing row;
    # the complete transcript may be precomputed, but that row is not admitted.
    early_rows = [[1, 0], [1, 0], [0, 1]]
    early_columns, early_basis = fixture_complete_basis(early_rows)
    crosscheck_prefix_profile(early_columns, early_basis, 1, 2)
    early = exact_rank_selection(
        column_loader=early_columns.__getitem__,
        complete_basis=early_basis,
        target=[1, 0, 0],
        base_rows=1,
        pool_rows=2,
        admit_rows=1,
        record_count=2,
    )
    require(
        early["selected_pool_indices"] == []
        and early["incompatible_dependency"]["pool_index"] == 0
        and early["post_terminal_unprocessed_pool_indices"] == [1],
        "early incompatible dependency admitted a later row",
    )

    cap_rows = [
        [1, 0, 0, 0],
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
    ]
    cap_columns, cap_basis = fixture_complete_basis(cap_rows)
    crosscheck_prefix_profile(cap_columns, cap_basis, 1, 4)
    capped = exact_rank_selection(
        column_loader=cap_columns.__getitem__,
        complete_basis=cap_basis,
        target=[1, 1, 0, 0, 0],
        base_rows=1,
        pool_rows=4,
        admit_rows=2,
        record_count=4,
    )
    require(
        capped["result"] == "SYNTHETIC_EXACT_RANK_LIMIT_SELECTED"
        and capped["selected_pool_indices"] == [1, 2]
        and capped["rank_basis_pool_indices_before_terminal"] == [1, 2, 3]
        and capped["post_cap_unadmitted_pool_indices"] == [3],
        "first-rank-growing admission cap fixture drift",
    )

    # Reaching the admission cap must not suppress a later incompatible
    # dependency.  The final row is e1+e2, while its target value violates the
    # implied relation.  This is the exact regression that the frozen G-0143
    # adversarial audit found.
    late_rows = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 1, 0],
    ]
    late_columns, late_basis = fixture_complete_basis(late_rows)
    late = exact_rank_selection(
        column_loader=late_columns.__getitem__,
        complete_basis=late_basis,
        target=[1, 0, 0, 0],
        base_rows=1,
        pool_rows=3,
        admit_rows=2,
        record_count=3,
    )
    require(
        late["result"] == "SYNTHETIC_INCOMPATIBLE_DEPENDENCY"
        and late["selected_pool_indices"] == [0, 1]
        and late["incompatible_dependency"]["pool_index"] == 2
        and late["incompatible_dependency"]["separator"] == [1, 1, 0, -1]
        and late["incompatible_dependency"]["separator_replay"]["target_pairing"]
        == "1",
        "post-cap incompatible dependency escaped",
    )

    # A later rank-growing row is not admitted, but it must enter the basis
    # used to certify dependencies that follow it.
    post_cap_growth_rows = [
        [1, 0, 0, 0],
        [0, 1, 0, 0],
        [0, 0, 1, 0],
        [0, 0, 0, 1],
        [0, 0, 1, 1],
    ]
    post_cap_columns, post_cap_basis = fixture_complete_basis(post_cap_growth_rows)
    post_cap_growth = exact_rank_selection(
        column_loader=post_cap_columns.__getitem__,
        complete_basis=post_cap_basis,
        target=[0, 0, 0, 0, 1],
        base_rows=1,
        pool_rows=4,
        admit_rows=1,
        record_count=4,
    )
    require(
        post_cap_growth["result"] == "SYNTHETIC_INCOMPATIBLE_DEPENDENCY"
        and post_cap_growth["selected_pool_indices"] == [0]
        and post_cap_growth["rank_basis_pool_indices_before_terminal"] == [0, 1, 2]
        and post_cap_growth["incompatible_dependency"]["pool_index"] == 3
        and post_cap_growth["incompatible_dependency"]["separator"]
        == [0, 0, 1, 1, -1]
        and post_cap_growth["incompatible_dependency"]["separator_replay"][
            "target_pairing"
        ]
        == "-1",
        "post-cap rank-growth dependency basis drift",
    )

    less_rows = [[1], [2], [3]]
    less_columns, less_basis = fixture_complete_basis(less_rows)
    crosscheck_prefix_profile(less_columns, less_basis, 1, 2)
    less = exact_rank_selection(
        column_loader=less_columns.__getitem__,
        complete_basis=less_basis,
        target=[1, 2, 3],
        base_rows=1,
        pool_rows=2,
        admit_rows=2,
        record_count=1,
    )
    require(
        less["result"] == "SYNTHETIC_FIXED_POOL_EXACT_RANK_GAIN_LT_LIMIT"
        and less["selected_count"] == 0
        and all(item["compatible"] for item in less["dependency_certificates"]),
        "rank-gain-below-limit fixture drift",
    )

    # The modular scanner must still load later columns after reaching full
    # modular row rank so its declared complete record census is truthful.
    census_columns = [[1, 0], [0, 1], [4, 5]]
    calls: list[int] = []

    def counted_loader(sequence: int) -> list[int]:
        calls.append(sequence)
        return census_columns[sequence]

    modular_column_proposal(
        column_loader=counted_loader,
        row_count=2,
        record_count=3,
        prime=101,
    )
    require(calls == [0, 1, 2], "modular proposal overstated its scan census")

    with tempfile.TemporaryDirectory(prefix="g0140-transpose-self-test-") as raw:
        streams = stream_modular_transposes(
            column_loader=mixed_columns.__getitem__,
            row_count=len(mixed_rows),
            record_count=len(mixed_columns),
            primes=FIXED_MODULAR_PRIMES,
            directory=Path(raw),
        )
        first = Path(streams[0]["path"]).read_bytes()
        expected_first = struct.pack(
            f"<{len(mixed_rows)}i",
            *(value % FIXED_MODULAR_PRIMES[0] for value in mixed_columns[0]),
        )
        require(
            first[: len(expected_first)] == expected_first,
            "M-transpose stream order fixture drift",
        )

    extra_metadata_gate = json.loads(json.dumps(g0139))
    extra_metadata_gate["audit_note"] = "nonsemantic provenance metadata is allowed"
    validate_g0139_admission(extra_metadata_gate)
    minimal_gate = {
        "schema": G0139_SCHEMA,
        "verdict": "PASS",
        "result": "CONSISTENT_RESIDUAL_T1",
        "subject": {
            "path": relative(G0135_STAGE_D_PATH),
            "sha256": G0135_STAGE_D_SHA256,
            "git_commit": "0" * 40,
            "result": "FULL_GLOBAL_EXACT_NONZERO_RESIDUAL",
        },
    }
    expect_rejected(
        lambda: validate_g0139_admission(minimal_gate),
        "G-0139 semantic lookalike",
        rejected,
    )
    bad_gate = json.loads(json.dumps(g0139))
    bad_gate["subject"]["sha256"] = "0" * 64
    expect_rejected(
        lambda: validate_g0139_admission(bad_gate),
        "G-0139 superset binding digest",
        rejected,
    )

    expect_rejected(
        lambda: json.loads(
            '{"same":1,"same":2}', object_pairs_hook=no_duplicate_object
        ),
        "duplicate JSON key",
        rejected,
    )
    expect_rejected(
        lambda: strict_json_text('{"first":1}{"second":2}', "trailing fixture"),
        "trailing JSON data",
        rejected,
    )
    expect_rejected(
        lambda: canonical_integer("01", "hostile integer"),
        "noncanonical integer",
        rejected,
    )
    expect_rejected(
        lambda: validate_direction([1, 1, -2, 0, 0, 0, 0, 0, 0, 0, 0], "hostile"),
        "inactive direction",
        rejected,
    )
    malformed_proposal = dict(bad_proposal)
    malformed_proposal["terminal_verdict"] = "RANK_COMPLETE"
    expect_rejected(
        lambda: validate_modular_proposals(
            [malformed_proposal],
            record_count=len(bad_prime_columns),
            primes=[bad_prime],
        ),
        "modular terminal verdict field",
        rejected,
    )
    expect_rejected(
        lambda: exact_dependency_certificate(
            complete_basis_rows=early_rows,
            basis_sequences=[0, 1],
            logical_target=[1, 0, 0],
            preceding_logical_rows=[0],
            candidate_logical_row=2,
        ),
        "dependency certificate on growing row",
        rejected,
    )
    good_native = {
        "schema": NATIVE_PROPOSER_SCHEMA,
        "role": MODULAR_ROLE,
        "matrix_layout": "row_major_transpose_family_columns",
        "byte_order": "little_endian_runtime_asserted",
        "transpose_rows": 4,
        "transpose_columns": 6,
        "prime": 101,
        "threads": 1,
        "rank": 3,
        "factor_seconds": 0.0,
    }
    parse_native_stdout(
        json.dumps(good_native, separators=(",", ":")) + "\n",
        record_count=4,
        row_count=6,
        prime=101,
        threads=1,
    )
    bad_native = dict(good_native)
    bad_native["exact_rank"] = 3
    expect_rejected(
        lambda: parse_native_stdout(
            json.dumps(bad_native, separators=(",", ":")) + "\n",
            record_count=4,
            row_count=6,
            prime=101,
            threads=1,
        ),
        "native exact-rank field",
        rejected,
    )

    with tempfile.TemporaryDirectory(prefix="g0140-output-self-test-", dir=HERE) as raw:
        destination = Path(raw) / "exclusive.json"
        write_exclusive(destination, {"first": True})
        expect_rejected(
            lambda: write_exclusive(destination, {"second": True}),
            "output overwrite",
            rejected,
        )

    required_rejections = {
        "omitted final column census",
        "separator coordinate plus one",
        "G-0139 wrong subject commit",
        "G-0139 false evidence class",
        "G-0139 false lineage and outcome awareness",
        "G-0139 empty claim boundary",
        "G-0139 missing custody",
        "G-0139 false source-audit anchor",
        "G-0139 missing candidate fixed binding",
        "G-0139 wrong candidate fixed binding",
        "G-0139 missing candidate with recursive decoy",
        "G-0139 semantic lookalike",
        "G-0139 superset binding digest",
        "source audit unknown envelope",
        "source audit self reference",
        "source audit displaced bindings",
        "source audit missing named binding with decoy",
        "source audit duplicate subject path",
        "source audit unknown subject field",
        "source audit wrong schema",
        "source audit false required check",
        "source audit integer required check",
        "source audit scientific observation",
        "Stage-B audit retired schema",
        "Stage-B audit missing G-0139 gate check",
        "Stage-B audit false G-0139 gate check",
        "Stage-B audit integer G-0139 gate check",
        "Stage-B audit displaced G-0139 gate check",
        "duplicate JSON key",
        "trailing JSON data",
        "noncanonical integer",
        "inactive direction",
        "modular terminal verdict field",
        "dependency certificate on growing row",
        "native exact-rank field",
        "output overwrite",
    }
    require(set(rejected) == required_rejections, "self-test rejection census drift")
    print(
        "g0140-stage-c-selector-self-test: PASS "
        f"({len(rejected)} hostile controls; exact completion/rank/dependency routes)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--static-preflight", action="store_true")
    modes.add_argument("--interface", action="store_true")
    modes.add_argument("--preflight", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    if args.self_test:
        require(not args.paths, "self-test takes no paths")
        self_test()
        return 0
    if args.static_preflight:
        require(not args.paths, "static preflight takes no paths")
        print(json.dumps(static_preflight(), sort_keys=True))
        return 0
    if args.interface:
        require(not args.paths, "interface mode takes no paths")
        print(json.dumps(future_interface(), sort_keys=True))
        return 0
    if args.preflight:
        require(
            len(args.paths) == 3,
            "preflight requires MANIFEST STAGE_A_RECEIPT STAGE_B_RECEIPT",
        )
        print(
            json.dumps(
                preflight(*(Path(path) for path in args.paths)), sort_keys=True
            )
        )
        return 0
    require(
        len(args.paths) == 4,
        "run requires MANIFEST STAGE_A_RECEIPT STAGE_B_RECEIPT OUTPUT",
    )
    result = scientific_run(*(Path(path) for path in args.paths))
    print(
        json.dumps(
            {
                "result": result["result"],
                "basis_rank": result["complete_column_basis"]["basis_rank"],
                "selected_count": result["rank_selection"]["selected_count"],
                "wall_seconds": result["wall_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
