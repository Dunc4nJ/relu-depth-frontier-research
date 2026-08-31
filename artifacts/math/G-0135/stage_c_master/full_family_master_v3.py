#!/usr/bin/env python3
"""Exact-Q 412-row all-column master for G-0135 Stage C.

This producer validates the sealed G-0128 380-row member, the future G-0135
Stage A Batch32 selection receipt, and the future Stage B coordinate receipt.
It then reopens the complete frozen 163,740-column family.  It never uses a
modular terminal decision and never writes a scientific result from self-test
or preflight mode.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import mmap
import os
import resource
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPT = Path(__file__).resolve()

PREREGISTRATION_PATH = ROOT / "artifacts/math/G-0135/PREREGISTRATION.md"
SHARED_MANIFEST_PATH = (
    ROOT / "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json"
)
STAGE_A_RECEIPT_PATH = ROOT / "artifacts/math/G-0135/batch32_global_replay_v1.json"
STAGE_B_RECEIPT_PATH = ROOT / "artifacts/math/G-0135/batch32_coordinate_prices_v1.json"
STAGE_A_SOURCE_PATH = ROOT / "artifacts/math/G-0135/src/main.rs"
STAGE_B_SOURCE_PATH = ROOT / "artifacts/math/G-0135/stage_b_pricer/src/main.rs"
RESULT_PATH = ROOT / "artifacts/math/G-0135/full_family_master_result_v3.json"

G0128_SOURCE_PATH = ROOT / "artifacts/math/G-0128/full_family_master_v2.py"
G0128_MANIFEST_PATH = ROOT / "artifacts/math/G-0128/full_family_master_manifest_v2.json"
G0128_RESULT_PATH = ROOT / "artifacts/math/G-0128/full_family_master_result_v2.json"
G0132_MANIFEST_PATH = (
    ROOT / "artifacts/math/G-0132/member_global_normal_form_manifest_v1.json"
)
G0132_RESULT_PATH = (
    ROOT / "artifacts/math/G-0132/member_global_normal_form_replay_v1.json"
)
G0134_RECEIPT_PATH = (
    ROOT / "artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json"
)
G0117_EXACT_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"

N = 11
RECORDS = 163_740
OLD_ROWS = 380
STAGE_B_ROWS = 32
ROWS = OLD_ROWS + STAGE_B_ROWS
INITIAL_RANK = 176
MAX_RANK_INCREASES = ROWS - INITIAL_RANK

PREREGISTRATION_SHA256 = (
    "ca9ed1930a8b7539d92d7651caadd06c6bd77742ce11adff682af9ac067fe5ec"
)
G0128_SOURCE_SHA256 = "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8"
G0128_MANIFEST_SHA256 = (
    "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec"
)
G0128_RESULT_SHA256 = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838"
G0132_MANIFEST_SHA256 = (
    "b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732"
)
G0132_RESULT_SHA256 = "d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50"
G0134_RECEIPT_SHA256 = (
    "a00aaca7aeb8f960d6fa5a264b72a13c797ae30a75c4eec5eaa90a5a455e2f56"
)
G0117_EXACT_SHA256 = "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281"
EXPECTED_FIRST_DIRECTION = [0, 0, 0, 0, 0, 0, 1, -3, -2, 1, 3]
EXPECTED_FIRST_COEFFICIENT = "363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360"

SHARED_MANIFEST_SCHEMA = "max11-g0135-batch32-global-replay-manifest-v1"
STAGE_A_SCHEMA = "max11-g0135-batch32-global-replay-v1"
STAGE_B_SCHEMA = "max11-g0135-batch32-coordinate-prices-v1"
RESULT_SCHEMA = "max11-g0135-full-family-master-result-v3"

MEMBER_RESULT = "FULL_FAMILY_412ROW_EXACT_Q_MEMBER"
NONMEMBER_RESULT = "FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER"
MEMBER_CLAIM_BOUNDARY = (
    "Exact membership only on the frozen 412-row system over the frozen "
    "163,740-column family. This supplies a finite-row member for the separately "
    "preregistered complete global replay; it is not a global MAX11 identity, "
    "family-completeness theorem, lower bound, minimality claim, or Lean theorem."
)
NONMEMBER_CLAIM_BOUNDARY = (
    "Exact nonmembership only in the frozen 163,740-column family on the frozen "
    "412 rows. It does not exclude other degree-five records, asymmetric "
    "constructions, deeper networks, or unrestricted two-hidden-layer ReLU "
    "representations."
)


class MasterError(RuntimeError):
    """Fail-closed validation or exact-arithmetic error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MasterError(message)


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(
        path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_object
    )
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
        raise MasterError(f"path escapes workspace: {path}") from error
    return resolved


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


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
        raise MasterError(f"{label} is not an integer") from error
    require(str(integer) == value, f"{label} is not canonical signed decimal")
    if positive:
        require(integer > 0, f"{label} must be positive")
    if nonzero:
        require(integer != 0, f"{label} must be nonzero")
    return integer


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
        require(0 <= integer < (1 << 64), "u64 digest input overflow")
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


def digest_text_lf(values: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def digest_directions(directions: Sequence[Sequence[int]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        require(len(direction) == N, "direction digest width drift")
        for coordinate in direction:
            integer = int(coordinate)
            require(-128 <= integer <= 127, "direction digest i8 overflow")
            digest.update(integer.to_bytes(1, "little", signed=True))
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    path = contained(path)
    require(path.parent.is_dir(), "output parent missing")
    require(not path.exists(), "refusing to overwrite output")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-", dir=path.parent
    )
    temporary = Path(temporary_name)
    linked = False
    try:
        with os.fdopen(descriptor, "wb") as destination:
            os.fchmod(destination.fileno(), 0o644)
            destination.write(payload)
            destination.flush()
            os.fsync(destination.fileno())
        os.link(temporary, path)
        linked = True
        directory = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except BaseException:
        if linked:
            path.unlink(missing_ok=True)
        raise
    finally:
        temporary.unlink(missing_ok=True)


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    require(
        specification is not None and specification.loader is not None,
        f"cannot import {path}",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


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


def validate_strict_axis(
    values: object, count: int, upper: int, label: str
) -> list[int]:
    require(
        isinstance(values, list)
        and len(values) == count
        and all(
            isinstance(value, int)
            and not isinstance(value, bool)
            and 0 <= value < upper
            for value in values
        ),
        f"{label} shape/range drift",
    )
    result = [int(value) for value in values]
    require(result == sorted(set(result)), f"{label} order/uniqueness drift")
    return result


def validate_exact_target(observed: object, expected: Sequence[int]) -> list[int]:
    require(
        isinstance(observed, list)
        and len(observed) == len(expected)
        and all(
            isinstance(value, int) and not isinstance(value, bool) for value in observed
        )
        and observed == list(expected),
        "exact target drift or prior-scale carryover",
    )
    return [int(value) for value in observed]


def validate_fixed_inputs() -> dict[str, str]:
    expected = {
        relative(PREREGISTRATION_PATH): PREREGISTRATION_SHA256,
        relative(G0128_SOURCE_PATH): G0128_SOURCE_SHA256,
        relative(G0128_MANIFEST_PATH): G0128_MANIFEST_SHA256,
        relative(G0128_RESULT_PATH): G0128_RESULT_SHA256,
        relative(G0132_MANIFEST_PATH): G0132_MANIFEST_SHA256,
        relative(G0132_RESULT_PATH): G0132_RESULT_SHA256,
        relative(G0134_RECEIPT_PATH): G0134_RECEIPT_SHA256,
        relative(G0117_EXACT_PATH): G0117_EXACT_SHA256,
    }
    for name, digest in expected.items():
        path = contained(ROOT / name)
        require(path.is_file(), f"missing immutable input: {name}")
        require_digest(sha256_path(path), digest, name)
    return expected


def validate_prior_admission_gate() -> None:
    replay = load_json(G0132_RESULT_PATH)
    require(
        replay.get("schema") == "max11-g0132-member-global-normal-form-replay-v1"
        and replay.get("result") == "MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL"
        and replay.get("manifest_path") == relative(G0132_MANIFEST_PATH)
        and replay.get("manifest_sha256") == G0132_MANIFEST_SHA256
        and replay.get("complete_global_replay") is True
        and replay.get("all_hinge_and_linear_residuals_zero") is False
        and int(replay.get("terms", -1)) == 132
        and int(replay.get("labelled_permutations_checked", -1)) == 5_269_017_600
        and int(replay.get("aggregate_hinge_support", -1)) == 163_036
        and int(replay.get("nonzero_hinge_directions", -1)) == 162_929
        and replay.get("first_nonzero_hinge")
        == {
            "direction": EXPECTED_FIRST_DIRECTION,
            "coefficient": EXPECTED_FIRST_COEFFICIENT,
        }
        and replay.get("first_nonzero_linear") is None
        and replay.get("inputs_rehashed_at_end") is True,
        "G-0132 exact residual identity drift",
    )

    audit = load_json(G0134_RECEIPT_PATH)
    custody = audit.get("custody", {}).get("fixed_primary_hashes_at_end", {})
    require(
        audit.get("schema") == "max11-g0134-cleanroom-residual-reprice-v1"
        and audit.get("verdict") == "CONSISTENT_RESIDUAL"
        and audit.get("exact_match") is True
        and audit.get("nonzero") is True
        and audit.get("lexicographic_first") == "VERIFIED"
        and audit.get("direction") == EXPECTED_FIRST_DIRECTION
        and audit.get("reported_coefficient") == EXPECTED_FIRST_COEFFICIENT
        and audit.get("independent_coefficient") == EXPECTED_FIRST_COEFFICIENT
        and int(audit.get("terms", -1)) == 132
        and int(audit.get("labelled_permutations_reconciled", -1)) == 5_269_017_600
        and custody.get("candidate") == G0128_RESULT_SHA256
        and custody.get("manifest") == G0132_MANIFEST_SHA256
        and custody.get("result") == G0132_RESULT_SHA256,
        "G-0134 prior-result admission gate is not exact PASS",
    )


def validate_binding(record: object, label: str) -> tuple[str, str]:
    require(
        isinstance(record, dict) and set(record) == {"path", "sha256"},
        f"{label} binding shape drift",
    )
    name = record.get("path")
    digest = record.get("sha256")
    require(
        isinstance(name, str) and name and not Path(name).is_absolute(),
        f"{label} binding path drift",
    )
    require(relative(ROOT / name) == name, f"{label} binding path is noncanonical")
    require(is_sha256(digest), f"{label} binding digest malformed")
    return name, digest


def validate_shared_manifest(
    manifest: dict[str, Any], manifest_sha256: str, script_sha256: str
) -> dict[str, str]:
    require(
        manifest.get("schema") == SHARED_MANIFEST_SCHEMA
        and manifest.get("selected_branch") == "MEMBER"
        and manifest.get("output_path") == relative(STAGE_A_RECEIPT_PATH)
        and manifest.get("stage_order")
        == [
            "A_REPLAY_SELECT",
            "B_PRICE",
            "C_MASTER",
            "D_GLOBAL_REPLAY_IF_MEMBER",
        ]
        and isinstance(manifest.get("planned_outputs"), dict)
        and manifest["planned_outputs"].get("C")
        == {"path": relative(RESULT_PATH), "schema": RESULT_SCHEMA},
        "shared manifest identity drift",
    )
    for field in [
        "preregistration_git_commit",
        "producer_git_commit",
        "source_audit_git_commit",
    ]:
        value = manifest.get(field)
        require(
            isinstance(value, str)
            and len(value) == 40
            and all(character in "0123456789abcdef" for character in value),
            f"shared manifest {field} drift",
        )

    bindings = manifest.get("bindings")
    require(isinstance(bindings, dict) and bindings, "shared manifest bindings missing")
    require(
        list(bindings) == sorted(bindings), "shared manifest binding labels unsorted"
    )
    observed: dict[str, str] = {}
    for label, record in bindings.items():
        require(isinstance(label, str) and label, "empty manifest binding label")
        name, digest = validate_binding(record, f"manifest binding {label}")
        require(name not in observed, f"duplicate manifest binding path: {name}")
        observed[name] = digest

    transitive = manifest.get("transitive_inputs")
    require(isinstance(transitive, list), "manifest transitive inputs missing")
    transitive_names: list[str] = []
    for index, record in enumerate(transitive):
        name, digest = validate_binding(record, f"manifest transitive input {index}")
        require(name not in observed, f"duplicate resolved manifest input: {name}")
        observed[name] = digest
        transitive_names.append(name)
    require(
        transitive_names == sorted(transitive_names),
        "manifest transitive input order drift",
    )

    required = {
        relative(PREREGISTRATION_PATH): PREREGISTRATION_SHA256,
        relative(G0128_SOURCE_PATH): G0128_SOURCE_SHA256,
        relative(G0128_MANIFEST_PATH): G0128_MANIFEST_SHA256,
        relative(G0128_RESULT_PATH): G0128_RESULT_SHA256,
        relative(G0132_MANIFEST_PATH): G0132_MANIFEST_SHA256,
        relative(G0132_RESULT_PATH): G0132_RESULT_SHA256,
        relative(G0134_RECEIPT_PATH): G0134_RECEIPT_SHA256,
        relative(G0117_EXACT_PATH): G0117_EXACT_SHA256,
        relative(SCRIPT): script_sha256,
    }
    require(
        relative(STAGE_A_SOURCE_PATH) in observed,
        "shared manifest does not bind Stage A producer",
    )
    require(
        relative(STAGE_B_SOURCE_PATH) in observed,
        "shared manifest does not bind Stage B producer",
    )
    for name, expected in required.items():
        require(
            observed.get(name) == expected, f"shared manifest binding drift: {name}"
        )

    for name, expected in observed.items():
        path = contained(ROOT / name)
        require(path.is_file(), f"manifest-bound input missing: {name}")
        require_digest(sha256_path(path), expected, f"manifest-bound input {name}")
    require_digest(
        sha256_path(SHARED_MANIFEST_PATH), manifest_sha256, "shared manifest"
    )
    return observed


G0128_RESULT_KEYS = {
    "all_380_rows_replayed",
    "audited_ancestor_sha256",
    "augmented_rank",
    "claim_boundary",
    "coefficient_plus_one_mutant_rejected",
    "coordinate_rows",
    "hinge_directions",
    "integer_coefficients",
    "manifest_path",
    "manifest_sha256",
    "maximum_rss_kib",
    "new_exact_residuals_decimal_lf_sha256",
    "new_selected_prefix_i8_u64_le_sha256",
    "old_batch_residuals_decimal_lf_sha256",
    "prior_candidate_rejected_on_all_32_new_rows",
    "rank",
    "records",
    "result",
    "rows",
    "schema",
    "selected_basis_i128le_sha256",
    "selected_sequences",
    "solver_sha256",
    "support_sequences",
    "target_scale",
    "terms",
    "trials",
    "wall_seconds",
}


def validate_g0128_candidate(candidate: dict[str, Any]) -> dict[str, Any]:
    require(set(candidate) == G0128_RESULT_KEYS, "G-0128 result key drift")
    require(
        candidate.get("schema") == "max11-g0128-full-family-master-result-v2"
        and candidate.get("result") == "FULL_FAMILY_380ROW_EXACT_Q_MEMBER"
        and candidate.get("manifest_path") == relative(G0128_MANIFEST_PATH)
        and candidate.get("manifest_sha256") == G0128_MANIFEST_SHA256
        and candidate.get("solver_sha256") == G0128_SOURCE_SHA256
        and int(candidate.get("records", -1)) == RECORDS
        and int(candidate.get("rows", -1)) == OLD_ROWS
        and int(candidate.get("rank", -1)) == INITIAL_RANK
        and int(candidate.get("augmented_rank", -1)) == INITIAL_RANK
        and candidate.get("all_380_rows_replayed") is True
        and candidate.get("coefficient_plus_one_mutant_rejected") is True
        and candidate.get("prior_candidate_rejected_on_all_32_new_rows") is True,
        "G-0128 result identity drift",
    )
    selected = validate_strict_axis(
        candidate.get("selected_sequences"), INITIAL_RANK, RECORDS, "G-0128 selected"
    )
    require(candidate.get("support_sequences") == selected, "G-0128 support drift")
    validate_strict_axis(
        candidate.get("coordinate_rows"), INITIAL_RANK, OLD_ROWS, "G-0128 coordinates"
    )

    raw_coefficients = candidate.get("integer_coefficients")
    require(
        isinstance(raw_coefficients, list) and len(raw_coefficients) == INITIAL_RANK,
        "G-0128 coefficient census drift",
    )
    coefficients = [
        canonical_integer(value, f"G-0128 coefficient {index}")
        for index, value in enumerate(raw_coefficients)
    ]
    scale = canonical_integer(
        candidate.get("target_scale"), "G-0128 target scale", positive=True
    )
    divisor = scale
    for coefficient in coefficients:
        divisor = math.gcd(divisor, abs(coefficient))
    require(divisor == 1 and any(coefficients), "G-0128 certificate is not primitive")

    expected_terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(selected, coefficients, strict=True)
        if coefficient
    ]
    require(
        candidate.get("terms") == expected_terms and len(expected_terms) == 132,
        "G-0128 term projection drift",
    )
    directions = candidate.get("hinge_directions")
    require(
        isinstance(directions, list) and len(directions) == 68,
        "G-0128 direction census drift",
    )
    validated = [
        validate_direction(direction, f"G-0128 direction {index}")
        for index, direction in enumerate(directions)
    ]
    require(
        len({tuple(direction) for direction in validated}) == 68,
        "duplicate G-0128 direction",
    )
    require(
        is_sha256(candidate.get("selected_basis_i128le_sha256")),
        "G-0128 basis digest drift",
    )

    trials = candidate.get("trials")
    require(isinstance(trials, list) and len(trials) == 21, "G-0128 trial census drift")
    for iteration, trial in enumerate(trials):
        require(
            isinstance(trial, dict) and trial.get("iteration") == iteration,
            "G-0128 trial order drift",
        )
        if iteration < 20:
            require(
                trial.get("result") == "SEPARATOR_VIOLATED"
                and int(trial.get("rank", -1)) == 156 + iteration
                and int(trial.get("augmented_rank", -1)) == 157 + iteration
                and trial.get("first_violating_sequence") == 142 + iteration
                and trial.get("columns_scanned") == 143 + iteration
                and canonical_integer(
                    trial.get("first_violating_price"),
                    f"G-0128 trial {iteration} price",
                    nonzero=True,
                ),
                "G-0128 continuation transcript drift",
            )
        else:
            require(
                trial
                == {
                    "iteration": 20,
                    "rank": INITIAL_RANK,
                    "augmented_rank": INITIAL_RANK,
                    "result": "EXACT_Q_MEMBER",
                },
                "G-0128 terminal transcript drift",
            )
    return candidate


def validate_g0128_manifest(manifest: dict[str, Any]) -> list[int]:
    require(
        manifest.get("schema") == "max11-g0128-full-family-master-manifest-v2"
        and manifest.get("result") == "BOUND_380ROW_INPUTS_VALIDATED"
        and manifest.get("solver")
        == {"path": relative(G0128_SOURCE_PATH), "sha256": G0128_SOURCE_SHA256}
        and int(manifest.get("records", -1)) == RECORDS
        and int(manifest.get("rows", -1)) == OLD_ROWS
        and manifest.get("row_order")
        == [
            "panel:301",
            "linear:11",
            "accumulated:G-0117/G-0118:4",
            "batch:G-0118:32",
            "batch:G-0126:32",
        ],
        "G-0128 manifest identity/row order drift",
    )
    target = manifest.get("target")
    require(
        isinstance(target, list)
        and len(target) == OLD_ROWS
        and all(
            isinstance(value, int) and not isinstance(value, bool) for value in target
        ),
        "G-0128 unscaled target drift",
    )
    return [int(value) for value in target]


STAGE_A_KEYS = {
    "schema",
    "result",
    "claim_boundary",
    "manifest_path",
    "manifest_sha256",
    "bindings",
    "candidate_schema",
    "candidate_result",
    "target_scale",
    "target_subtraction_coordinate_10",
    "arithmetic",
    "decision_rule",
    "screening_primes_control_only",
    "complete_global_replay",
    "all_hinge_and_linear_residuals_zero",
    "terms",
    "hinge_entries_processed",
    "labelled_permutations_checked",
    "aggregate_hinge_support",
    "nonzero_hinge_directions",
    "aggregate_hinge_decimal_lf_sha256",
    "nonzero_hinge_decimal_lf_sha256",
    "term_normal_form_transcript_sha256",
    "term_normal_forms",
    "carry_forward_checks",
    "first_carry_forward_failure",
    "linear_residuals_after_target",
    "first_nonzero_hinge",
    "first_nonzero_linear",
    "prior_g0132_reconciled",
    "batch_k",
    "selected_count",
    "selected_directions_i8_sha256",
    "selected_exact_residuals_decimal_lf_sha256",
    "selected",
    "selection_controls",
    "first_coefficient_plus_one",
    "final_coefficient_plus_one",
    "target_scale_plus_one",
    "target_coordinate_10_plus_one",
    "omitted_final_term",
    "omitted_first_term_active_direction",
    "omitted_first_term_linear_coordinate",
    "census_controls",
    "inputs_rehashed_at_end",
    "wall_seconds",
}


def require_all_true(record: object, expected_keys: set[str], label: str) -> None:
    require(
        isinstance(record, dict) and set(record) == expected_keys,
        f"{label} key drift",
    )
    require(all(value is True for value in record.values()), f"{label} not all green")


def validate_stage_a_mutation(record: object, expected_name: str) -> None:
    expected_keys = {
        "name",
        "first_nonzero_hinge",
        "first_nonzero_linear",
        "unmutated_residual_decimal_lf_sha256",
        "mutated_residual_decimal_lf_sha256",
        "changed_from_unmutated",
        "rejected",
    }
    require(
        isinstance(record, dict)
        and set(record) == expected_keys
        and record.get("name") == expected_name
        and is_sha256(record.get("unmutated_residual_decimal_lf_sha256"))
        and is_sha256(record.get("mutated_residual_decimal_lf_sha256"))
        and record.get("unmutated_residual_decimal_lf_sha256")
        != record.get("mutated_residual_decimal_lf_sha256")
        and record.get("changed_from_unmutated") is True
        and record.get("rejected") is True,
        f"Stage A {expected_name} mutation control drift",
    )


def validate_stage_a_receipt(
    receipt: dict[str, Any],
    receipt_sha256: str,
    manifest: dict[str, Any],
    manifest_sha256: str,
    candidate: dict[str, Any],
) -> tuple[list[list[int]], list[int]]:
    require(set(receipt) == STAGE_A_KEYS, "Stage A top-level key drift")
    scale = canonical_integer(
        candidate.get("target_scale"), "G-0128 target scale", positive=True
    )
    require(
        receipt.get("schema") == STAGE_A_SCHEMA
        and receipt.get("result") == "EXACT_RESIDUAL_BATCH"
        and isinstance(receipt.get("claim_boundary"), str)
        and bool(receipt.get("claim_boundary"))
        and receipt.get("manifest_path") == relative(SHARED_MANIFEST_PATH)
        and receipt.get("manifest_sha256") == manifest_sha256
        and receipt.get("bindings") == manifest.get("bindings")
        and receipt.get("candidate_schema") == candidate.get("schema")
        and receipt.get("candidate_result") == candidate.get("result")
        and receipt.get("target_scale") == candidate.get("target_scale")
        and canonical_integer(
            receipt.get("target_subtraction_coordinate_10"),
            "Stage A target subtraction",
            positive=True,
        )
        == scale * math.factorial(N)
        and receipt.get("arithmetic") == "signed_num_bigint_BigInt_unconditional_exact"
        and receipt.get("decision_rule")
        == "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate"
        and receipt.get("screening_primes_control_only")
        == [1_000_000_007, 1_000_000_009]
        and receipt.get("complete_global_replay") is True
        and receipt.get("all_hinge_and_linear_residuals_zero") is False
        and receipt.get("prior_g0132_reconciled") is True
        and receipt.get("inputs_rehashed_at_end") is True
        and float(receipt.get("wall_seconds", 0.0)) > 0.0,
        "Stage A identity/custody drift",
    )
    require_digest(sha256_path(STAGE_A_RECEIPT_PATH), receipt_sha256, "Stage A receipt")
    require(
        int(receipt.get("terms", -1)) == 132
        and int(receipt.get("hinge_entries_processed", -1)) == 4_579_906
        and int(receipt.get("labelled_permutations_checked", -1)) == 5_269_017_600
        and int(receipt.get("aggregate_hinge_support", -1)) == 163_036
        and int(receipt.get("nonzero_hinge_directions", -1)) == 162_929
        and all(
            is_sha256(receipt.get(field))
            for field in [
                "aggregate_hinge_decimal_lf_sha256",
                "nonzero_hinge_decimal_lf_sha256",
                "term_normal_form_transcript_sha256",
            ]
        ),
        "Stage A exact replay census/digest drift",
    )

    term_forms = receipt.get("term_normal_forms")
    require(
        isinstance(term_forms, list)
        and len(term_forms) == 132
        and [item.get("sequence") for item in term_forms]
        == [item["sequence"] for item in candidate["terms"]],
        "Stage A term transcript order drift",
    )
    for index, item in enumerate(term_forms):
        require(
            isinstance(item, dict)
            and int(item.get("generated_labelled_permutations", -1))
            == math.factorial(N)
            and int(item.get("visited_labelled_permutations", -1)) == math.factorial(N)
            and int(item.get("accepted_labelled_permutations", -1)) == math.factorial(N)
            and int(item.get("skipped_labelled_permutations", -1)) == 0
            and int(item.get("unclassified_labelled_permutations", -1)) == 0
            and int(item.get("failed_labelled_permutations", -1)) == 0
            and item.get("independent_exact_linear_crosscheck") is True
            and item.get("bounded_pinned_kernel_crosscheck") is True,
            f"Stage A term transcript {index} drift",
        )

    carried = candidate["hinge_directions"]
    carry_checks = receipt.get("carry_forward_checks")
    require(
        isinstance(carry_checks, list) and len(carry_checks) == len(carried),
        "Stage A carry-forward census drift",
    )
    for index, (check, direction) in enumerate(zip(carry_checks, carried, strict=True)):
        require(
            isinstance(check, dict)
            and set(check) == {"index", "direction", "coefficient", "exact_zero"}
            and check.get("index") == index
            and check.get("direction") == direction
            and check.get("coefficient") == "0"
            and check.get("exact_zero") is True,
            f"Stage A carry-forward row {index} drift",
        )
    require(
        receipt.get("first_carry_forward_failure") is None
        and receipt.get("linear_residuals_after_target") == ["0"] * N
        and receipt.get("first_nonzero_hinge")
        == {
            "direction": EXPECTED_FIRST_DIRECTION,
            "coefficient": EXPECTED_FIRST_COEFFICIENT,
        }
        and receipt.get("first_nonzero_linear") is None,
        "Stage A old-row/linear reconciliation drift",
    )

    selected = receipt.get("selected")
    require(
        isinstance(selected, list)
        and len(selected) == STAGE_B_ROWS
        and int(receipt.get("batch_k", -1)) == STAGE_B_ROWS
        and int(receipt.get("selected_count", -1)) == STAGE_B_ROWS,
        "Stage A selected census drift",
    )
    directions: list[list[int]] = []
    residuals: list[int] = []
    for index, item in enumerate(selected):
        require(
            isinstance(item, dict) and set(item) == {"direction", "coefficient"},
            f"Stage A selected row {index} key drift",
        )
        directions.append(
            validate_direction(
                item.get("direction"), f"Stage A selected direction {index}"
            )
        )
        residuals.append(
            canonical_integer(
                item.get("coefficient"),
                f"Stage A selected residual {index}",
                nonzero=True,
            )
        )
    require(
        directions == sorted(directions)
        and len({tuple(direction) for direction in directions}) == STAGE_B_ROWS,
        "Stage A selected direction order/uniqueness drift",
    )
    carried_set = {tuple(direction) for direction in carried}
    require(
        all(tuple(direction) not in carried_set for direction in directions),
        "Stage A selected direction duplicates an old member row",
    )
    direction_digest = digest_directions(directions)
    residual_digest = digest_decimal_lf(residuals)
    require(
        receipt.get("selected_directions_i8_sha256") == direction_digest
        and receipt.get("selected_exact_residuals_decimal_lf_sha256") == residual_digest
        and directions[0] == EXPECTED_FIRST_DIRECTION
        and str(residuals[0]) == EXPECTED_FIRST_COEFFICIENT,
        "Stage A Batch32 digest/firstness drift",
    )
    require_all_true(
        receipt.get("selection_controls"),
        {
            "exact_batch_count",
            "strict_signed_lexicographic_order",
            "first_direction_matches_g0132",
            "first_coefficient_matches_g0132",
            "direction_reordering_changes_digest",
            "residual_plus_one_changes_digest",
        },
        "Stage A selection controls",
    )
    require_all_true(
        receipt.get("census_controls"),
        {
            "per_term_generated_equals_visited_equals_accepted",
            "zero_skipped_unclassified_failed",
            "omitted_final_term_rejected",
            "omitted_last_orbit_contribution_rejected",
            "omitted_active_direction_changed_terminal_residual",
            "omitted_linear_coordinate_changed_terminal_residual",
            "screening_prime_collision_found_exactly",
        },
        "Stage A census controls",
    )
    for field, control_name in {
        "first_coefficient_plus_one": "first_nonzero_coefficient_plus_one",
        "final_coefficient_plus_one": "final_nonzero_coefficient_plus_one",
        "target_scale_plus_one": "target_scale_plus_one",
        "target_coordinate_10_plus_one": "target_coordinate_10_plus_one",
        "omitted_final_term": "omitted_final_nonzero_term",
        "omitted_first_term_active_direction": "omitted_first_term_active_direction",
        "omitted_first_term_linear_coordinate": "omitted_first_term_linear_coordinate",
    }.items():
        validate_stage_a_mutation(receipt.get(field), control_name)
    return directions, residuals


STAGE_B_KEYS = {
    "schema",
    "result",
    "claim_boundary",
    "manifest_path",
    "manifest_sha256",
    "bindings",
    "stage_a_receipt",
    "candidate",
    "batch_k",
    "records",
    "hinge_entries",
    "selected_count",
    "selected_directions_i8_sha256",
    "selected_exact_residuals_decimal_lf_sha256",
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


def validate_stage_b_receipt(
    receipt: dict[str, Any],
    receipt_sha256: str,
    manifest: dict[str, Any],
    manifest_sha256: str,
    stage_a_sha256: str,
    candidate: dict[str, Any],
    directions: list[list[int]],
    residuals: list[int],
    *,
    expected_records: int = RECORDS,
) -> list[list[int]]:
    require(set(receipt) == STAGE_B_KEYS, "Stage B top-level key drift")
    require(
        receipt.get("schema") == STAGE_B_SCHEMA
        and receipt.get("result") == "EXACT_FULL_FAMILY_BATCH32_COORDINATES"
        and isinstance(receipt.get("claim_boundary"), str)
        and bool(receipt.get("claim_boundary"))
        and receipt.get("manifest_path") == relative(SHARED_MANIFEST_PATH)
        and receipt.get("manifest_sha256") == manifest_sha256
        and receipt.get("bindings") == manifest.get("bindings")
        and receipt.get("stage_a_receipt")
        == {"path": relative(STAGE_A_RECEIPT_PATH), "sha256": stage_a_sha256}
        and receipt.get("candidate")
        == {"path": relative(G0128_RESULT_PATH), "sha256": G0128_RESULT_SHA256}
        and int(receipt.get("batch_k", -1)) == STAGE_B_ROWS
        and int(receipt.get("records", -1)) == expected_records
        and int(receipt.get("hinge_entries", -1)) == STAGE_B_ROWS * expected_records
        and int(receipt.get("selected_count", -1)) == STAGE_B_ROWS
        and receipt.get("inputs_rehashed_at_end") is True
        and float(receipt.get("wall_seconds", 0.0)) > 0.0,
        "Stage B identity/custody/dimension drift",
    )
    require_digest(sha256_path(STAGE_B_RECEIPT_PATH), receipt_sha256, "Stage B receipt")
    direction_digest = digest_directions(directions)
    residual_digest = digest_decimal_lf(residuals)
    require(
        receipt.get("selected_directions_i8_sha256") == direction_digest
        and receipt.get("selected_exact_residuals_decimal_lf_sha256") == residual_digest
        and receipt.get("directions") == directions,
        "Stage B Stage-A selection bridge drift",
    )

    raw_rows = receipt.get("rows")
    require(
        isinstance(raw_rows, list) and len(raw_rows) == STAGE_B_ROWS,
        "Stage B row census drift",
    )
    rows: list[list[int]] = []
    aggregate = hashlib.sha256()
    exact_dots: list[int] = []
    terms = [
        (int(item["sequence"]), int(item["coefficient"])) for item in candidate["terms"]
    ]
    for index, (raw_row, direction, residual) in enumerate(
        zip(raw_rows, directions, residuals, strict=True)
    ):
        require(
            isinstance(raw_row, dict) and set(raw_row) == STAGE_B_ROW_KEYS,
            f"Stage B row {index} key drift",
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
            f"Stage B row {index} coordinate shape/i64 drift",
        )
        coordinates = [int(value) for value in raw_coordinates]
        encoded = b"".join(
            value.to_bytes(8, "little", signed=True) for value in coordinates
        )
        row_digest = hashlib.sha256(encoded).hexdigest()
        exact_dot = sum(
            coefficient * coordinates[sequence] for sequence, coefficient in terms
        )
        require(
            raw_row.get("index") == index
            and raw_row.get("direction") == direction
            and canonical_integer(
                raw_row.get("exact_stage_a_residual"),
                f"Stage B row {index} Stage A residual",
                nonzero=True,
            )
            == residual
            and canonical_integer(
                raw_row.get("exact_candidate_dot"),
                f"Stage B row {index} candidate dot",
                nonzero=True,
            )
            == exact_dot
            == residual
            and int(raw_row.get("records", -1)) == expected_records
            and int(raw_row.get("nonzero_hinge_coefficients", -1))
            == sum(value != 0 for value in coordinates)
            and int(raw_row.get("minimum_hinge_coefficient")) == min(coordinates)
            and int(raw_row.get("maximum_hinge_coefficient")) == max(coordinates)
            and int(raw_row.get("maximum_absolute_hinge_coefficient"))
            == max(abs(value) for value in coordinates)
            and raw_row.get("hinge_coefficients_i64_le_sha256") == row_digest,
            f"Stage B row {index} exact receipt drift",
        )
        aggregate.update(encoded)
        exact_dots.append(exact_dot)
        rows.append(coordinates)

    exact_dot_digest = digest_decimal_lf(exact_dots)
    require(
        aggregate.hexdigest() == receipt.get("direction_major_hinge_i64_le_sha256")
        and exact_dots == residuals
        and receipt.get("exact_candidate_dots") == [str(value) for value in exact_dots]
        and receipt.get("exact_candidate_dots_decimal_lf_sha256")
        == exact_dot_digest
        == residual_digest,
        "Stage B aggregate coordinate/exact-dot digest drift",
    )
    require_all_true(
        receipt.get("input_mutation_controls"),
        {
            "selected_count_mutant_rejected",
            "selection_order_mutant_rejected",
            "selection_duplicate_mutant_rejected",
            "direction_invalidity_mutant_rejected",
            "residual_plus_one_mutant_rejected",
            "record_census_truncation_rejected",
            "record_order_mutant_rejected",
            "all_rejected",
        },
        "Stage B input mutation controls",
    )

    mutant = receipt.get("coefficient_plus_one_mutant")
    require(
        isinstance(mutant, dict)
        and set(mutant)
        == {
            "sequence",
            "coefficient_delta",
            "baseline_exact_dots_decimal_lf_sha256",
            "mutated_exact_dots_decimal_lf_sha256",
            "changed_rows",
            "rejected",
        },
        "Stage B coefficient mutant key drift",
    )
    mutant_sequence = mutant.get("sequence")
    require(
        isinstance(mutant_sequence, int)
        and not isinstance(mutant_sequence, bool)
        and any(sequence == mutant_sequence for sequence, _ in terms),
        "Stage B coefficient mutant sequence drift",
    )
    mutated_dots = [
        exact_dot + row[mutant_sequence]
        for exact_dot, row in zip(exact_dots, rows, strict=True)
    ]
    changed_rows = sum(
        mutated != baseline
        for mutated, baseline in zip(mutated_dots, exact_dots, strict=True)
    )
    require(
        mutant.get("coefficient_delta") == "+1"
        and mutant.get("baseline_exact_dots_decimal_lf_sha256") == exact_dot_digest
        and mutant.get("mutated_exact_dots_decimal_lf_sha256")
        == digest_decimal_lf(mutated_dots)
        and int(mutant.get("changed_rows", -1)) == changed_rows
        and changed_rows > 0
        and mutant.get("mutated_exact_dots_decimal_lf_sha256") != exact_dot_digest
        and mutant.get("rejected") is True,
        "Stage B coefficient-plus-one mutant drift",
    )
    return rows


def matrix_rows(columns: Sequence[Sequence[int]], row_count: int) -> list[list[int]]:
    require(
        columns
        and row_count > 0
        and all(len(column) == row_count for column in columns),
        "ragged or empty column matrix",
    )
    return [[int(column[row]) for column in columns] for row in range(row_count)]


def normalize_member(values: Sequence[Fraction]) -> tuple[list[int], int]:
    require(values, "empty rational member")
    scale = math.lcm(*(value.denominator for value in values))
    integers = [int(value * scale) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "member normalization gcd vanished")
    scale //= divisor
    integers = [value // divisor for value in integers]
    common = scale
    for value in integers:
        common = math.gcd(common, abs(value))
    require(scale > 0 and any(integers) and common == 1, "member is not primitive")
    return integers, scale


def validate_primitive_separator(
    separator: Sequence[int], pairing: int, target: Sequence[int]
) -> None:
    require(
        len(separator) == len(target) and separator and any(separator),
        "separator dimension/zero drift",
    )
    divisor = 0
    for value in separator:
        divisor = math.gcd(divisor, abs(int(value)))
    require(divisor == 1, "separator is not primitive")
    require(
        next(int(value) for value in separator if value) > 0,
        "separator sign normalization drift",
    )
    require(
        pairing
        == sum(
            int(value) * int(rhs) for value, rhs in zip(separator, target, strict=True)
        )
        and pairing != 0,
        "separator target pairing drift",
    )


def separator_scan(
    separator: Sequence[int],
    record_count: int,
    column_loader: Callable[[int], Sequence[int]],
    *,
    stop_at_first_violation: bool,
) -> dict[str, Any]:
    require(record_count > 0 and separator and any(separator), "invalid separator scan")
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    digest = hashlib.sha256()
    first_violation: tuple[int, int] | None = None
    first_active_coordinate: tuple[int, int, int] | None = None
    columns_scanned = 0
    for sequence in range(record_count):
        column = [int(value) for value in column_loader(sequence)]
        require(len(column) == len(separator), "separator/column dimension drift")
        if first_active_coordinate is None:
            for row, value in enumerate(column):
                if value:
                    first_active_coordinate = (row, sequence, value)
                    break
        price = sum(value * column[row] for row, value in nonzero)
        digest.update(str(price).encode("ascii"))
        digest.update(b"\n")
        columns_scanned = sequence + 1
        if price and first_violation is None:
            first_violation = (sequence, price)
            if stop_at_first_violation:
                break
    if not stop_at_first_violation:
        require(columns_scanned == record_count, "terminal separator scan truncated")
    return {
        "first_violation": first_violation,
        "columns_scanned": columns_scanned,
        "prices_decimal_lf_sha256": digest.hexdigest(),
        "first_active_coordinate": first_active_coordinate,
    }


def expect_rejected(action: Callable[[], object], label: str) -> None:
    try:
        action()
    except MasterError:
        return
    raise MasterError(f"hostile control escaped: {label}")


def exact_column_generation(
    *,
    helper: Any,
    target: list[int],
    seed_sequences: list[int],
    column_loader: Callable[[int], Sequence[int]],
    record_count: int,
    expected_initial_rank: int,
    prior_target_scale: int,
) -> dict[str, Any]:
    """Run the exact-Q separator/column-generation loop with dynamic row count."""

    row_count = len(target)
    require(
        row_count > 0
        and 0 < expected_initial_rank <= row_count
        and seed_sequences == sorted(set(seed_sequences))
        and len(seed_sequences) == expected_initial_rank
        and all(0 <= sequence < record_count for sequence in seed_sequences),
        "invalid exact column-generation seed",
    )
    selected = seed_sequences[:]
    rhs = helper.qmatrix([[value] for value in target])
    trials: list[dict[str, Any]] = []
    previous_rank: int | None = None

    for iteration in range(row_count - expected_initial_rank + 1):
        require(selected == sorted(set(selected)), "selected column order drift")
        columns = [
            [int(value) for value in column_loader(sequence)] for sequence in selected
        ]
        integer_rows = matrix_rows(columns, row_count)
        matrix = helper.qmatrix(integer_rows)
        augmented = helper.qmatrix(
            [row + [target[index]] for index, row in enumerate(integer_rows)]
        )
        rank = int(matrix.rank())
        augmented_rank = int(augmented.rank())
        if iteration == 0:
            require(rank == expected_initial_rank, "warm-start exact rank drift")
        else:
            require(
                previous_rank is not None and rank == previous_rank + 1,
                "appended column failed exact unit rank increase",
            )
        require(rank == len(selected), "selected columns are not an exact basis")
        require(
            augmented_rank in {rank, rank + 1},
            "exact augmented-rank relation drift",
        )
        previous_rank = rank

        if rank == augmented_rank:
            reduced, reduced_rank = matrix.rref()
            require(int(reduced_rank) == rank, "member RREF rank drift")
            pivot_indices = helper.pivot_columns(reduced, rank, len(selected))
            support_sequences = [selected[index] for index in pivot_indices]
            require(
                support_sequences == selected,
                "unit-rank column transcript did not remain its own pivot basis",
            )
            support_columns = [columns[index] for index in pivot_indices]
            basis_rows = matrix_rows(support_columns, row_count)
            basis = helper.qmatrix(basis_rows)
            transposed, transposed_rank = basis.transpose().rref()
            require(int(transposed_rank) == rank, "member basis rank drift")
            coordinate_rows = helper.pivot_columns(transposed, rank, row_count)
            square = helper.qmatrix(
                [
                    [basis_rows[row][column] for column in range(rank)]
                    for row in coordinate_rows
                ]
            )
            rational = square.solve(
                helper.qmatrix([[target[row]] for row in coordinate_rows])
            )
            require(basis * rational == rhs, "all-row exact-Q member replay failed")
            fractions = [Fraction(str(rational[index, 0])) for index in range(rank)]
            rational_lhs = [
                sum(
                    fractions[column] * basis_rows[row][column]
                    for column in range(rank)
                )
                for row in range(row_count)
            ]
            require(
                rational_lhs == [Fraction(value) for value in target],
                "independent rational all-row replay failed",
            )
            integers, scale = normalize_member(fractions)
            integer_residuals = [
                sum(
                    integers[column] * basis_rows[row][column] for column in range(rank)
                )
                - scale * target[row]
                for row in range(row_count)
            ]
            require(
                not any(integer_residuals), "primitive integer all-row replay failed"
            )

            first_nonzero = next(index for index, value in enumerate(integers) if value)
            mutant = integers[:]
            mutant[first_nonzero] += 1
            mutant_residuals = [
                sum(mutant[column] * basis_rows[row][column] for column in range(rank))
                - scale * target[row]
                for row in range(row_count)
            ]
            require(any(mutant_residuals), "member coefficient-plus-one mutant escaped")

            contaminated_target = [prior_target_scale * value for value in target]
            expect_rejected(
                lambda contaminated_target=contaminated_target, target=target: (
                    validate_exact_target(contaminated_target, target)
                ),
                "prior target-scale carryover",
            )
            trials.append(
                {
                    "iteration": iteration,
                    "rank": rank,
                    "augmented_rank": augmented_rank,
                    "result": "EXACT_Q_MEMBER",
                }
            )
            terms = [
                {"sequence": sequence, "coefficient": str(coefficient)}
                for sequence, coefficient in zip(
                    support_sequences, integers, strict=True
                )
                if coefficient
            ]
            return {
                "branch": "MEMBER",
                "rank": rank,
                "augmented_rank": augmented_rank,
                "selected_sequences": selected,
                "support_sequences": support_sequences,
                "coordinate_rows": coordinate_rows,
                "selected_basis_i128le_sha256": digest_i128(
                    basis_rows[row][column]
                    for row in range(row_count)
                    for column in range(rank)
                ),
                "rational_coefficients": [str(value) for value in fractions],
                "rational_coefficients_lf_sha256": digest_text_lf(fractions),
                "target_scale": str(scale),
                "integer_coefficients": [str(value) for value in integers],
                "integer_coefficients_decimal_lf_sha256": digest_decimal_lf(integers),
                "terms": terms,
                "support_receipt": {
                    "selected_columns": len(selected),
                    "support_columns": len(support_sequences),
                    "support_is_exact_pivot_basis": True,
                    "selected_sequences_u64le_sha256": digest_u64(selected),
                    "support_sequences_u64le_sha256": digest_u64(support_sequences),
                    "term_support_u64le_sha256": digest_u64(
                        item["sequence"] for item in terms
                    ),
                },
                "replay_receipt": {
                    "rows": row_count,
                    "rational_all_rows_replayed": True,
                    "rational_lhs_lf_sha256": digest_text_lf(rational_lhs),
                    "primitive_denominator_clearing": True,
                    "integer_all_rows_replayed": True,
                    "integer_residuals_decimal_lf_sha256": digest_decimal_lf(
                        integer_residuals
                    ),
                },
                "coefficient_plus_one_mutant": {
                    "support_index": first_nonzero,
                    "sequence": support_sequences[first_nonzero],
                    "coefficient_delta": "+1",
                    "first_nonzero_residual_row": next(
                        index for index, value in enumerate(mutant_residuals) if value
                    ),
                    "residuals_decimal_lf_sha256": digest_decimal_lf(mutant_residuals),
                    "rejected": True,
                },
                "prior_target_scale_carryover_mutant_rejected": True,
                "trials": trials,
            }

        require(augmented_rank == rank + 1, "outside-span augmented rank drift")
        separator, pairing, free_row = helper.first_target_separator(
            matrix, integer_rows, target
        )
        separator = [int(value) for value in separator]
        pairing = int(pairing)
        validate_primitive_separator(separator, pairing, target)
        scan = separator_scan(
            separator,
            record_count,
            column_loader,
            stop_at_first_violation=True,
        )
        violation = scan["first_violation"]
        trial = {
            "iteration": iteration,
            "rank": rank,
            "augmented_rank": augmented_rank,
            "separator_target_pairing": str(pairing),
            "separator_free_row": int(free_row),
            "first_violating_sequence": None if violation is None else violation[0],
            "first_violating_price": None if violation is None else str(violation[1]),
            "columns_scanned": scan["columns_scanned"],
            "scanned_prices_decimal_lf_sha256": scan["prices_decimal_lf_sha256"],
            "result": NONMEMBER_RESULT if violation is None else "SEPARATOR_VIOLATED",
        }
        if violation is not None:
            trials.append(trial)
            require(violation[0] not in selected, "separator returned selected column")
            selected.append(violation[0])
            selected.sort()
            continue

        terminal_scan = separator_scan(
            separator,
            record_count,
            column_loader,
            stop_at_first_violation=False,
        )
        require(
            terminal_scan["first_violation"] is None
            and terminal_scan["columns_scanned"] == record_count,
            "terminal separator replay failed",
        )
        trial["columns_scanned"] = terminal_scan["columns_scanned"]
        trial["scanned_prices_decimal_lf_sha256"] = terminal_scan[
            "prices_decimal_lf_sha256"
        ]
        trials.append(trial)

        sign_mutant = [-value for value in separator]
        expect_rejected(
            lambda sign_mutant=sign_mutant, pairing=pairing, target=target: (
                validate_primitive_separator(sign_mutant, -pairing, target)
            ),
            "separator sign mutation",
        )
        active = terminal_scan["first_active_coordinate"]
        require(active is not None, "family matrix is identically zero")
        active_row, active_sequence, active_value = active
        coordinate_mutant = separator[:]
        coordinate_mutant[active_row] += 1
        coordinate_scan = separator_scan(
            coordinate_mutant,
            record_count,
            column_loader,
            stop_at_first_violation=True,
        )
        coordinate_violation = coordinate_scan["first_violation"]
        require(
            coordinate_violation is not None
            and coordinate_violation[0] <= active_sequence,
            "separator coordinate-plus-one mutant escaped",
        )
        expect_rejected(
            lambda separator=separator, pairing=pairing, target=target: (
                validate_primitive_separator(separator, pairing + 1, target)
            ),
            "separator target-pairing mutation",
        )
        return {
            "branch": "NONMEMBER",
            "rank": rank,
            "augmented_rank": augmented_rank,
            "primitive_integer_separator": [str(value) for value in separator],
            "separator_target_pairing": str(pairing),
            "separator_free_row": int(free_row),
            "complete_separator_replay": {
                "columns": record_count,
                "all_family_columns_exactly_annihilated": True,
                "prices_decimal_lf_sha256": terminal_scan["prices_decimal_lf_sha256"],
                "target_pairing_replayed": True,
            },
            "separator_sign_mutant": {
                "operation": "multiply_by_-1",
                "canonical_orientation_rejected": True,
            },
            "separator_coordinate_plus_one_mutant": {
                "coordinate": active_row,
                "known_active_sequence": active_sequence,
                "known_active_value": str(active_value),
                "first_violating_sequence": coordinate_violation[0],
                "first_violating_price": str(coordinate_violation[1]),
                "rejected": True,
            },
            "separator_target_pairing_plus_one_mutant_rejected": True,
            "trials": trials,
        }

    raise MasterError("exact master exceeded the dynamic rank-increase bound")


def load_g0128_ancestor() -> Any:
    require_digest(
        sha256_path(G0128_SOURCE_PATH), G0128_SOURCE_SHA256, "G-0128 master source"
    )
    ancestor = load_module(G0128_SOURCE_PATH, "g0135_stage_c_g0128_ancestor")
    require(
        ancestor.ROWS == OLD_ROWS
        and ancestor.RECORDS == RECORDS
        and ancestor.INITIAL_RANK == 156,
        "G-0128 ancestor dimensions drift",
    )
    return ancestor


def old_prefix_column(
    ancestor: Any,
    cache: mmap.mmap,
    components: dict[str, Any],
    sequence: int,
) -> list[int]:
    column = ancestor.full_column(
        cache,
        sequence,
        components["linear"],
        components["accumulated"],
        components["old_batch_block"],
        components["new_batch_block"],
    )
    require(len(column) == OLD_ROWS, "G-0128 immutable prefix dimension drift")
    return [int(value) for value in column]


def full_stage_c_column(
    ancestor: Any,
    cache: mmap.mmap,
    components: dict[str, Any],
    stage_b_rows: Sequence[Sequence[int]],
    sequence: int,
) -> list[int]:
    require(
        len(stage_b_rows) == STAGE_B_ROWS
        and all(len(row) == RECORDS for row in stage_b_rows),
        "Stage B block shape drift",
    )
    column = old_prefix_column(ancestor, cache, components, sequence)
    column.extend(int(row[sequence]) for row in stage_b_rows)
    require(len(column) == ROWS, "dynamic Stage C column dimension drift")
    return column


def validate_warm_start_matrices(
    *,
    helper: Any,
    candidate: dict[str, Any],
    old_target: list[int],
    full_target: list[int],
    old_columns: list[list[int]],
    full_columns: list[list[int]],
    stage_a_residuals: list[int],
) -> dict[str, Any]:
    selected = candidate["selected_sequences"]
    coefficients = [int(value) for value in candidate["integer_coefficients"]]
    prior_scale = int(candidate["target_scale"])
    require(
        len(old_columns) == len(full_columns) == INITIAL_RANK
        and all(len(column) == OLD_ROWS for column in old_columns)
        and all(len(column) == ROWS for column in full_columns),
        "warm-start column dimensions drift",
    )
    old_rows = matrix_rows(old_columns, OLD_ROWS)
    full_rows = matrix_rows(full_columns, ROWS)
    old_basis_digest = digest_i128(
        old_rows[row][column]
        for row in range(OLD_ROWS)
        for column in range(INITIAL_RANK)
    )
    require(
        old_basis_digest == candidate.get("selected_basis_i128le_sha256"),
        "G-0128 immutable selected-basis digest drift",
    )

    old_matrix = helper.qmatrix(old_rows)
    old_augmented = helper.qmatrix(
        [row + [old_target[index]] for index, row in enumerate(old_rows)]
    )
    old_rank = int(old_matrix.rank())
    old_augmented_rank = int(old_augmented.rank())
    require(
        old_rank == old_augmented_rank == INITIAL_RANK,
        "G-0128 exact old rank/augmented rank drift",
    )
    old_residuals = [
        sum(
            coefficients[column] * old_rows[row][column]
            for column in range(INITIAL_RANK)
        )
        - prior_scale * old_target[row]
        for row in range(OLD_ROWS)
    ]
    require(not any(old_residuals), "G-0128 exact old identity replay failed")

    full_matrix = helper.qmatrix(full_rows)
    full_augmented = helper.qmatrix(
        [row + [full_target[index]] for index, row in enumerate(full_rows)]
    )
    full_rank = int(full_matrix.rank())
    full_augmented_rank = int(full_augmented.rank())
    require(
        full_rank == INITIAL_RANK and full_augmented_rank == INITIAL_RANK + 1,
        "32 appended rows did not exactly reject the old member",
    )
    appended_residuals = [
        sum(
            coefficients[column] * full_rows[OLD_ROWS + row][column]
            for column in range(INITIAL_RANK)
        )
        for row in range(STAGE_B_ROWS)
    ]
    require(
        appended_residuals == stage_a_residuals
        and all(value != 0 for value in appended_residuals),
        "exact old-member rejection does not match all 32 Stage A residuals",
    )
    return {
        "old_rows": OLD_ROWS,
        "old_rank": old_rank,
        "old_augmented_rank": old_augmented_rank,
        "old_selected_columns": len(selected),
        "old_selected_sequences_u64le_sha256": digest_u64(selected),
        "old_selected_basis_i128le_sha256": old_basis_digest,
        "old_target_scale": str(prior_scale),
        "all_old_rows_exactly_replayed": True,
        "old_integer_residuals_decimal_lf_sha256": digest_decimal_lf(old_residuals),
        "full_seed_rank": full_rank,
        "full_seed_augmented_rank": full_augmented_rank,
        "appended_rows": STAGE_B_ROWS,
        "appended_rows_reject_old_member": True,
        "all_32_appended_residuals_nonzero": True,
        "appended_residuals_decimal_lf_sha256": digest_decimal_lf(appended_residuals),
    }


def input_snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for name, value in sorted(snapshot.items()):
        digest.update(name.encode("utf-8"))
        digest.update(b"\t")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def rehash_snapshot(snapshot: dict[str, str]) -> None:
    for name, expected in sorted(snapshot.items()):
        path = contained(ROOT / name)
        require(path.is_file(), f"bound input vanished: {name}")
        require_digest(sha256_path(path), expected, f"end-bound input {name}")


def load_validated_inputs(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
) -> dict[str, Any]:
    manifest_path = contained(manifest_path)
    stage_a_path = contained(stage_a_path)
    stage_b_path = contained(stage_b_path)
    require(manifest_path == SHARED_MANIFEST_PATH, "shared manifest path drift")
    require(stage_a_path == STAGE_A_RECEIPT_PATH, "Stage A receipt path drift")
    require(stage_b_path == STAGE_B_RECEIPT_PATH, "Stage B receipt path drift")
    require(
        manifest_path.is_file() and stage_a_path.is_file() and stage_b_path.is_file(),
        "future Stage A/B/manifest input missing",
    )

    fixed = validate_fixed_inputs()
    validate_prior_admission_gate()
    script_sha256 = sha256_path(SCRIPT)
    manifest_sha256 = sha256_path(manifest_path)
    stage_a_sha256 = sha256_path(stage_a_path)
    stage_b_sha256 = sha256_path(stage_b_path)
    manifest = load_json(manifest_path)
    manifest_bindings = validate_shared_manifest(
        manifest, manifest_sha256, script_sha256
    )
    candidate = validate_g0128_candidate(load_json(G0128_RESULT_PATH))
    old_target = validate_g0128_manifest(load_json(G0128_MANIFEST_PATH))
    full_target = old_target + [0] * STAGE_B_ROWS
    require(
        len(full_target) == ROWS and full_target[:OLD_ROWS] == old_target,
        "Stage C target assembly drift",
    )
    validate_exact_target(full_target, old_target + [0] * STAGE_B_ROWS)

    stage_a = load_json(stage_a_path)
    directions, residuals = validate_stage_a_receipt(
        stage_a,
        stage_a_sha256,
        manifest,
        manifest_sha256,
        candidate,
    )
    stage_b = load_json(stage_b_path)
    stage_b_rows = validate_stage_b_receipt(
        stage_b,
        stage_b_sha256,
        manifest,
        manifest_sha256,
        stage_a_sha256,
        candidate,
        directions,
        residuals,
    )

    ancestor = load_g0128_ancestor()
    ancestor.validate_expected_inputs(include_future=True)
    ancestor.AUDITED.validate_cache_receipt()
    components = ancestor.load_validated_components()
    require(
        ancestor.build_target() == old_target,
        "G-0128 reconstructed target differs from sealed unscaled target",
    )
    helper = ancestor.AUDITED.load_module(
        ancestor.AUDITED.HELPER_PATH, "g0135_stage_c_exact_helper"
    )

    snapshot = dict(manifest_bindings)
    snapshot.update(fixed)
    snapshot[relative(SHARED_MANIFEST_PATH)] = manifest_sha256
    snapshot[relative(STAGE_A_RECEIPT_PATH)] = stage_a_sha256
    snapshot[relative(STAGE_B_RECEIPT_PATH)] = stage_b_sha256
    snapshot[relative(SCRIPT)] = script_sha256
    require(len(snapshot) == len(set(snapshot)), "input snapshot path collision")
    return {
        "manifest": manifest,
        "manifest_sha256": manifest_sha256,
        "stage_a_sha256": stage_a_sha256,
        "stage_b_sha256": stage_b_sha256,
        "script_sha256": script_sha256,
        "candidate": candidate,
        "stage_a": stage_a,
        "stage_b": stage_b,
        "old_target": old_target,
        "target": full_target,
        "directions": directions,
        "residuals": residuals,
        "stage_b_rows": stage_b_rows,
        "ancestor": ancestor,
        "components": components,
        "helper": helper,
        "snapshot": snapshot,
    }


def validate_warm_start(
    prepared: dict[str, Any], cache: mmap.mmap
) -> tuple[dict[str, Any], Callable[[int], list[int]]]:
    ancestor = prepared["ancestor"]
    components = prepared["components"]
    stage_b_rows = prepared["stage_b_rows"]
    candidate = prepared["candidate"]
    selected = candidate["selected_sequences"]
    require(len(cache) == ancestor.AUDITED.CACHE_BYTES, "cache mmap size drift")
    old_columns = [
        old_prefix_column(ancestor, cache, components, sequence)
        for sequence in selected
    ]
    full_columns = [
        full_stage_c_column(ancestor, cache, components, stage_b_rows, sequence)
        for sequence in selected
    ]
    receipt = validate_warm_start_matrices(
        helper=prepared["helper"],
        candidate=candidate,
        old_target=prepared["old_target"],
        full_target=prepared["target"],
        old_columns=old_columns,
        full_columns=full_columns,
        stage_a_residuals=prepared["residuals"],
    )

    def loader(sequence: int) -> list[int]:
        require(0 <= sequence < RECORDS, "column sequence outside frozen family")
        return full_stage_c_column(ancestor, cache, components, stage_b_rows, sequence)

    return receipt, loader


def common_result_fields(
    prepared: dict[str, Any],
    warm_receipt: dict[str, Any],
) -> dict[str, Any]:
    candidate = prepared["candidate"]
    stage_a = prepared["stage_a"]
    stage_b = prepared["stage_b"]
    target = prepared["target"]
    return {
        "schema": RESULT_SCHEMA,
        "claim_boundary": "",
        "manifest_path": relative(SHARED_MANIFEST_PATH),
        "manifest_sha256": prepared["manifest_sha256"],
        "solver": {
            "path": relative(SCRIPT),
            "sha256": prepared["script_sha256"],
        },
        "stage_a_receipt": {
            "path": relative(STAGE_A_RECEIPT_PATH),
            "sha256": prepared["stage_a_sha256"],
        },
        "stage_b_receipt": {
            "path": relative(STAGE_B_RECEIPT_PATH),
            "sha256": prepared["stage_b_sha256"],
        },
        "prior_master_result": {
            "path": relative(G0128_RESULT_PATH),
            "sha256": G0128_RESULT_SHA256,
        },
        "prior_master_manifest": {
            "path": relative(G0128_MANIFEST_PATH),
            "sha256": G0128_MANIFEST_SHA256,
        },
        "audited_exact_q_core": {
            "g0128_source": {
                "path": relative(G0128_SOURCE_PATH),
                "sha256": G0128_SOURCE_SHA256,
            },
            "g0117_source": {
                "path": relative(G0117_EXACT_PATH),
                "sha256": G0117_EXACT_SHA256,
            },
        },
        "records": RECORDS,
        "old_rows": OLD_ROWS,
        "appended_rows": len(prepared["stage_b_rows"]),
        "rows": len(target),
        "target": target,
        "target_i128le_sha256": digest_i128(target),
        "target_construction": (
            "original_unscaled_G0128_380_entry_target_followed_by_32_exact_zeros"
        ),
        "prior_target_scale_not_reused": True,
        "row_order": [
            "immutable_prefix:G-0128:380",
            "batch:G-0135-stage-A-receipt-order:32",
        ],
        "stage_a_selected_directions_i8_sha256": stage_a[
            "selected_directions_i8_sha256"
        ],
        "stage_a_selected_exact_residuals_decimal_lf_sha256": stage_a[
            "selected_exact_residuals_decimal_lf_sha256"
        ],
        "stage_b_direction_major_hinge_i64_le_sha256": stage_b[
            "direction_major_hinge_i64_le_sha256"
        ],
        "stage_b_exact_candidate_dots_decimal_lf_sha256": stage_b[
            "exact_candidate_dots_decimal_lf_sha256"
        ],
        "warm_seed_policy": (
            "all_176_G0128_selected_sequences_then_every_separator_scan_reopens_"
            "all_163740_columns_in_canonical_sequence_order"
        ),
        "initial_selected_sequences": candidate["selected_sequences"],
        "initial_selected_sequences_u64le_sha256": digest_u64(
            candidate["selected_sequences"]
        ),
        "initial_rank": INITIAL_RANK,
        "max_rank_increases": len(target) - INITIAL_RANK,
        "all_columns_reopened": True,
        "canonical_column_order": True,
        "no_modular_terminal_decision": True,
        "no_support_freeze": True,
        "no_zero_price_column_deletion": True,
        "no_row_dependency_deletion": True,
        "no_preferred_sparsity_search": True,
        "old_member_validation": warm_receipt,
        "input_snapshot_sha256": input_snapshot_digest(prepared["snapshot"]),
        "inputs_rehashed_at_end": False,
        "wall_seconds": 0.0,
        "maximum_rss_kib": 0,
    }


def preflight(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
) -> dict[str, Any]:
    require(not RESULT_PATH.exists(), "scientific result already exists")
    prepared = load_validated_inputs(manifest_path, stage_a_path, stage_b_path)
    ancestor = prepared["ancestor"]
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, _ = validate_warm_start(prepared, cache)
    rehash_snapshot(prepared["snapshot"])
    ancestor.validate_expected_inputs(include_future=True)
    return {
        "result": "G0135_STAGE_C_PREFLIGHT_PASS",
        "rows": ROWS,
        "records": RECORDS,
        "initial_rank": warm_receipt["full_seed_rank"],
        "initial_augmented_rank": warm_receipt["full_seed_augmented_rank"],
        "old_member_rejected_on_all_32_rows": warm_receipt[
            "all_32_appended_residuals_nonzero"
        ],
        "target_i128le_sha256": digest_i128(prepared["target"]),
        "input_snapshot_sha256": input_snapshot_digest(prepared["snapshot"]),
        "scientific_result_written": False,
    }


def run(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    begun = time.perf_counter()
    output_path = contained(output_path)
    require(output_path == RESULT_PATH, "Stage C result path drift")
    require(not output_path.exists(), "refusing to overwrite Stage C result")
    prepared = load_validated_inputs(manifest_path, stage_a_path, stage_b_path)
    ancestor = prepared["ancestor"]
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, loader = validate_warm_start(prepared, cache)
        decision = exact_column_generation(
            helper=prepared["helper"],
            target=prepared["target"],
            seed_sequences=prepared["candidate"]["selected_sequences"],
            column_loader=loader,
            record_count=RECORDS,
            expected_initial_rank=INITIAL_RANK,
            prior_target_scale=int(prepared["candidate"]["target_scale"]),
        )

    result = common_result_fields(prepared, warm_receipt)
    branch = decision.pop("branch")
    if branch == "MEMBER":
        result.update(
            {
                "result": MEMBER_RESULT,
                "claim_boundary": MEMBER_CLAIM_BOUNDARY,
                "all_412_rows_replayed": True,
                **decision,
            }
        )
    else:
        require(branch == "NONMEMBER", "unknown exact decision branch")
        result.update(
            {
                "result": NONMEMBER_RESULT,
                "claim_boundary": NONMEMBER_CLAIM_BOUNDARY,
                **decision,
            }
        )

    require(
        result["rows"] == ROWS
        and result["appended_rows"] == STAGE_B_ROWS
        and result["target"][:OLD_ROWS] == prepared["old_target"]
        and result["target"][OLD_ROWS:] == [0] * STAGE_B_ROWS,
        "final Stage C dimension/target drift",
    )
    rehash_snapshot(prepared["snapshot"])
    ancestor.validate_expected_inputs(include_future=True)
    require_digest(sha256_path(SCRIPT), prepared["script_sha256"], "Stage C solver")
    require_digest(
        sha256_path(SHARED_MANIFEST_PATH),
        prepared["manifest_sha256"],
        "shared manifest",
    )
    result["inputs_rehashed_at_end"] = True
    result["wall_seconds"] = time.perf_counter() - begun
    result["maximum_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    write_exclusive(output_path, result)
    return result


def self_test() -> None:
    rejected: list[str] = []

    def rejected_control(label: str, action: Callable[[], object]) -> None:
        try:
            action()
        except (MasterError, TypeError, ValueError):
            rejected.append(label)
            return
        raise MasterError(f"self-test hostile control escaped: {label}")

    for value in ["0", "1", "-1", "12345678901234567890"]:
        canonical_integer(value, "synthetic integer")
    for value in ["", "+1", "00", "01", "-0", "1/2", " 1"]:
        rejected_control(
            f"noncanonical integer {value!r}",
            lambda value=value: canonical_integer(value, "synthetic integer"),
        )

    directions = [
        [0] * 8 + [1, -2, 1],
        [0] * 7 + [1, -3, 0, 2],
    ]
    require(directions == sorted(directions), "synthetic direction order drift")
    for index, direction in enumerate(directions):
        validate_direction(direction, f"synthetic direction {index}")
    direction_digest = digest_directions(directions)
    reordered = list(reversed(directions))
    require(
        digest_directions(reordered) != direction_digest,
        "direction reorder did not change digest",
    )
    invalid_direction = directions[0][:]
    invalid_direction[-1] += 1
    rejected_control(
        "nonzero-sum direction",
        lambda: validate_direction(invalid_direction, "mutant direction"),
    )
    require(
        digest_decimal_lf([1, -2]) != digest_decimal_lf([-2, 1]),
        "residual reorder did not change digest",
    )

    target = [1, 1, 0]
    validate_exact_target(target, target)
    rejected_control(
        "target scale carryover",
        lambda: validate_exact_target([2, 2, 0], target),
    )
    values, scale = normalize_member([Fraction(1, 3), Fraction(2, 3)])
    require(values == [1, 2] and scale == 3, "fresh primitive clearing drift")
    rejected_control(
        "ragged dynamic matrix",
        lambda: matrix_rows([[1, 0], [0]], 2),
    )

    require_digest(
        sha256_path(G0117_EXACT_PATH), G0117_EXACT_SHA256, "G-0117 exact helper"
    )
    helper = load_module(G0117_EXACT_PATH, "g0135_stage_c_selftest_helper")
    member_columns = [[1, 0, 1], [0, 1, 1], [0, 0, 1]]
    member = exact_column_generation(
        helper=helper,
        target=target,
        seed_sequences=[0, 1],
        column_loader=member_columns.__getitem__,
        record_count=3,
        expected_initial_rank=2,
        prior_target_scale=2,
    )
    require(
        member["branch"] == "MEMBER"
        and member["rank"] == member["augmented_rank"] == 3
        and member["support_sequences"] == [0, 1, 2]
        and member["replay_receipt"]["rational_all_rows_replayed"] is True
        and member["replay_receipt"]["integer_all_rows_replayed"] is True
        and member["coefficient_plus_one_mutant"]["rejected"] is True
        and member["prior_target_scale_carryover_mutant_rejected"] is True,
        "planted exact member route failed",
    )
    nonmember = exact_column_generation(
        helper=helper,
        target=target,
        seed_sequences=[0, 1],
        column_loader=member_columns.__getitem__,
        record_count=2,
        expected_initial_rank=2,
        prior_target_scale=2,
    )
    require(
        nonmember["branch"] == "NONMEMBER"
        and nonmember["complete_separator_replay"][
            "all_family_columns_exactly_annihilated"
        ]
        is True
        and nonmember["complete_separator_replay"]["columns"] == 2
        and nonmember["separator_sign_mutant"]["canonical_orientation_rejected"] is True
        and nonmember["separator_coordinate_plus_one_mutant"]["rejected"] is True
        and nonmember["separator_target_pairing_plus_one_mutant_rejected"] is True,
        "planted exact nonmember route failed",
    )

    duplicate_json = '{"x":1,"x":2}'
    rejected_control(
        "duplicate JSON key",
        lambda: json.loads(duplicate_json, object_pairs_hook=no_duplicate_object),
    )
    with tempfile.TemporaryDirectory(dir=HERE) as raw_directory:
        directory = Path(raw_directory)
        output = directory / "atomic.json"
        write_exclusive(output, {"ok": True})
        rejected_control(
            "output overwrite", lambda: write_exclusive(output, {"ok": False})
        )
        aborted = directory / "serialization-abort.json"
        rejected_control(
            "serialization abort",
            lambda: write_exclusive(aborted, {"not_json": {1}}),
        )
        require(not aborted.exists(), "serialization abort left final output")

    required_rejections = {
        "noncanonical integer ''",
        "noncanonical integer '+1'",
        "noncanonical integer '00'",
        "noncanonical integer '01'",
        "noncanonical integer '-0'",
        "noncanonical integer '1/2'",
        "noncanonical integer ' 1'",
        "nonzero-sum direction",
        "target scale carryover",
        "ragged dynamic matrix",
        "duplicate JSON key",
        "output overwrite",
        "serialization abort",
    }
    require(set(rejected) == required_rejections, "self-test rejection census drift")
    print(
        "g0135-stage-c-master-self-test: PASS "
        f"({len(rejected)} hostile controls plus exact member/nonmember routes)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    require(not (args.self_test and args.preflight), "choose exactly one mode")
    if args.self_test:
        require(not args.paths, "self-test takes no paths")
        self_test()
        return 0
    if args.preflight:
        require(
            len(args.paths) == 3,
            "preflight requires MANIFEST STAGE_A_RECEIPT STAGE_B_RECEIPT",
        )
        value = preflight(*(Path(path) for path in args.paths))
        print(json.dumps(value, sort_keys=True))
        return 0
    require(
        len(args.paths) == 4,
        "run requires MANIFEST STAGE_A_RECEIPT STAGE_B_RECEIPT OUTPUT",
    )
    value = run(*(Path(path) for path in args.paths))
    print(
        json.dumps(
            {
                "result": value["result"],
                "rank": value["rank"],
                "augmented_rank": value["augmented_rank"],
                "trials": len(value["trials"]),
                "wall_seconds": value["wall_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
