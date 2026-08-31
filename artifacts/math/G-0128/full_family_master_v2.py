#!/usr/bin/env python3
"""Exact-Q 380-row all-column master for the preregistered G-0128 study."""

from __future__ import annotations

import argparse
import copy
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import mmap
import os
from pathlib import Path
import resource
import tempfile
import time
from typing import Any, Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md"
MANIFEST_PATH = HERE / "full_family_master_manifest_v2.json"
RESULT_PATH = HERE / "full_family_master_result_v2.json"

ANCESTOR_PATH = ROOT / "artifacts/math/G-0123/full_family_master.py"
ANCESTOR_SHA256 = "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac"
PREREGISTRATION_SHA256 = "ed33f3349780c1e73d64b1a9a75e2a070ae554bd1313dc081187a8d2554e5a9f"
PRIOR_MANIFEST_PATH = ROOT / "artifacts/math/G-0121/full_family_master_manifest_v1.json"
PRIOR_MANIFEST_SHA256 = "9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c"
PRIOR_RESULT_PATH = ROOT / "artifacts/math/G-0121/full_family_master_result_v1.json"
PRIOR_RESULT_SHA256 = "53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036"
ANCESTOR_AUDIT_PATH = ROOT / "artifacts/reviews/G-0123-full-family-master/AUDIT_VERDICT.md"
ANCESTOR_AUDIT_SHA256 = "28404e3832c4f98e14f54abad1c278d4d2e153bca35977783854c8f96e4030dc"

G0126_PREREGISTRATION_PATH = ROOT / "artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md"
G0126_SOURCE_PATH = ROOT / "artifacts/math/G-0126/src/main.rs"
G0126_CARGO_PATH = ROOT / "artifacts/math/G-0126/Cargo.toml"
G0126_LOCK_PATH = ROOT / "artifacts/math/G-0126/Cargo.lock"
G0126_EXECUTABLE_PATH = ROOT / "artifacts/math/G-0126/target/release/g0126-global-replay"
G0126_RECEIPT_PATH = ROOT / "artifacts/math/G-0126/global_replay_v1.json"

G0127_PREREGISTRATION_PATH = ROOT / "artifacts/math/G-0127/BATCH32_COORDINATE_PRICING_PREREGISTRATION.md"
G0127_SOURCE_PATH = ROOT / "artifacts/math/G-0127/src/main.rs"
G0127_CARGO_PATH = ROOT / "artifacts/math/G-0127/Cargo.toml"
G0127_LOCK_PATH = ROOT / "artifacts/math/G-0127/Cargo.lock"
G0127_EXECUTABLE_PATH = ROOT / "artifacts/math/G-0127/target/release/g0127-batch-coordinate-pricer"
G0127_PRICE_PATH = ROOT / "artifacts/math/G-0127/batch32_coordinate_prices_v1.json"

STATIC_EXPECTED_INPUTS: dict[str, str] = {
    "artifacts/math/G-0121/full_family_master_manifest_v1.json": PRIOR_MANIFEST_SHA256,
    "artifacts/math/G-0121/full_family_master_result_v1.json": PRIOR_RESULT_SHA256,
    "artifacts/math/G-0123/full_family_master.py": ANCESTOR_SHA256,
    "artifacts/math/G-0126/Cargo.lock": "316421f8f8907349b9fb9b54a10ebe6bd4c3d4ddb9b44bc0294ff382f96dd45f",
    "artifacts/math/G-0126/Cargo.toml": "14300697a23f010c349bcd2581f62ce85f1efa3b5a759c70d94b7894a8dedb6a",
    "artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md": "d6dd969ae558c7e36eb420c1fa4fa2c1254875eeff073b8580809b6a50a2fadb",
    "artifacts/math/G-0126/global_replay_v1.json": "bd0410d861978956502e9d4c4fc1cd159565f2e170d70509abd0f3eb21b771ea",
    "artifacts/math/G-0126/src/main.rs": "a59f51ed491d50fb8d8e3e93e1a0f53dbc351a67a84fc2ae1f51bd18f74991f3",
    "artifacts/math/G-0127/BATCH32_COORDINATE_PRICING_PREREGISTRATION.md": "ddd823a8c63e42c74e07fd1cbee6a7c5fca573f10ab3deb8138674092bde0070",
    "artifacts/reviews/G-0118-iteration4-batch/review_v1.json": "e7905d258ed05e004c51b449494c9cd7094e967cdf3c29380646f55caaf2b569",
    "artifacts/reviews/G-0123-full-family-master/AUDIT_VERDICT.md": ANCESTOR_AUDIT_SHA256,
}

# These bindings were filled only after G-0127 published its sealed receipt.
FUTURE_EXPECTED_INPUTS: dict[str, str] = {
    "artifacts/math/G-0127/Cargo.lock": "467388a6341a27cc751bf29015a7e62ee98a0f2b8b3bd6560904669e440ec940",
    "artifacts/math/G-0127/Cargo.toml": "653934f2c34d5bee798cdaf9d9cc9bfd49ed070c8034621a2e0d98a24f81180c",
    "artifacts/math/G-0127/batch32_coordinate_prices_v1.json": "c4c5d59b13820027c81bd4e0b74c67027da851f0a6f90bd941484eb9c4533946",
    "artifacts/math/G-0127/src/main.rs": "68a9062fa28a5ad5da614634066685cc7e66f709fe6309f553317b483ba23cd8",
}
G0127_EXECUTABLE_SHA256 = "ab521e503eab3ec014465fffd8da602b1721bf76a00c7c9ef3adadd266379b64"

N = 11
PANEL_ROWS = 301
LINEAR_ROWS = 11
ACCUMULATED_ROWS = 4
OLD_BATCH_ROWS = 32
NEW_BATCH_ROWS = 32
OLD_ROWS = PANEL_ROWS + LINEAR_ROWS + ACCUMULATED_ROWS + OLD_BATCH_ROWS
ROWS = OLD_ROWS + NEW_BATCH_ROWS
RECORDS = 163_740
INITIAL_RANK = 156
MAX_RANK_INCREASES = ROWS - INITIAL_RANK
PRIMES = [1_000_000_007, 1_000_000_009]
OLD_SELECTED_DIGEST = "03d05477b7ac12641fac6b3ebe953d356fc89c4fe70d5ee03535a371d71fe0ac"
OLD_BATCH_RESIDUAL_DIGEST = "98f507b0d4277018a7d704c951c1e6b3cac10243b59c3df407b5a195d0e9686b"
NEW_SELECTED_DIGEST = "0cd2699dec0bc5ffd7cb81c1454aac79143ae4a37c571fcb707c85a55a5c459e"
NEW_EXACT_RESIDUAL_DIGEST = "000ae45daea6c4debf91f47f3accd7877762b830c30945d31f1f1c97d3c7262b"
LINEAR_DIGEST = "84cc206d635fa7f651578ab46cda56f6154d0ebd22ca2be26ceeffcf0594aa51"


class MasterError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MasterError(message)


def no_duplicate_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in output, f"duplicate JSON key: {key}")
        output[key] = value
    return output


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=no_duplicate_object)
    require(isinstance(value, dict), f"top-level object required: {path}")
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
    require(is_sha256(actual) and is_sha256(expected) and actual == expected, f"{label} hash drift")


def contained(path: Path) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT)
    except ValueError as error:
        raise MasterError(f"path escapes workspace: {path}") from error
    return result


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


def digest_i64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(8, "little", signed=True))
    return digest.hexdigest()


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_selected(selected: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in selected:
        for value in item["direction"]:
            digest.update(int(value).to_bytes(1, "little", signed=True))
        for value in item["residues"]:
            digest.update(int(value).to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    path = contained(path)
    require(path.parent.is_dir(), "output parent missing")
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.tmp-", dir=path.parent)
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


def load_module(path: Path, name: str):
    specification = importlib.util.spec_from_file_location(name, path)
    require(specification is not None and specification.loader is not None, f"cannot import {path}")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


require_digest(sha256_path(ANCESTOR_PATH), ANCESTOR_SHA256, "audited ancestor")
AUDITED = load_module(ANCESTOR_PATH, "g0128_audited_g0123_ancestor")


def expected_inputs() -> dict[str, str]:
    return {**AUDITED.EXPECTED_INPUTS, **STATIC_EXPECTED_INPUTS, **FUTURE_EXPECTED_INPUTS}


def require_future_frozen() -> None:
    for name, digest in FUTURE_EXPECTED_INPUTS.items():
        require(is_sha256(digest), f"future input not frozen: {name}")
    require(is_sha256(G0127_EXECUTABLE_SHA256), "future executable not frozen")


def validate_expected_inputs(*, include_future: bool = True) -> dict[str, str]:
    if include_future:
        require_future_frozen()
    frozen = {**AUDITED.EXPECTED_INPUTS, **STATIC_EXPECTED_INPUTS}
    if include_future:
        frozen.update(FUTURE_EXPECTED_INPUTS)
    observed: dict[str, str] = {}
    resolved_paths: set[Path] = set()
    for name, expected in frozen.items():
        require(is_sha256(expected), f"malformed expected SHA-256: {name}")
        path = contained(ROOT / name)
        require(path.is_file(), f"missing input: {name}")
        require(path not in resolved_paths, f"duplicate resolved input: {name}")
        resolved_paths.add(path)
        actual = sha256_path(path)
        require_digest(actual, expected, f"input {name}")
        observed[name] = actual
    require_digest(sha256_path(PREREGISTRATION), PREREGISTRATION_SHA256, "G-0128 preregistration")
    require_digest(sha256_path(G0126_EXECUTABLE_PATH), "ae7f64ce737d8f12d9f4a3d5695fe8ded4b5a89720eff8a0f5a537b2126bfa28", "G-0126 executable")
    if include_future:
        require_digest(sha256_path(G0127_EXECUTABLE_PATH), G0127_EXECUTABLE_SHA256, "G-0127 executable")
    AUDITED.validate_cache_size(AUDITED.CACHE_PATH.stat().st_size)
    return observed


def canonical_integer(value: object, label: str, *, positive: bool = False, nonzero: bool = False) -> int:
    require(isinstance(value, str), f"{label} must be a decimal string")
    integer = int(value)
    require(str(integer) == value, f"{label} is not canonical decimal")
    if positive:
        require(integer > 0, f"{label} must be positive")
    if nonzero:
        require(integer != 0, f"{label} must be nonzero")
    return integer


def validate_direction(direction: object) -> list[int]:
    require(
        isinstance(direction, list)
        and len(direction) == N
        and all(isinstance(value, int) and -128 <= value <= 127 for value in direction),
        "direction i8 shape drift",
    )
    values = [int(value) for value in direction]
    require(sum(values) == 0, "direction must sum to zero")
    first_nonzero = next((value for value in values if value), None)
    require(first_nonzero is not None and first_nonzero > 0, "direction orientation drift")
    divisor = 0
    for value in values:
        divisor = math.gcd(divisor, abs(value))
    require(divisor == 1, "direction is not primitive")
    prefix = 0
    active = False
    for value in values[:-1]:
        prefix += value
        active = active or prefix < 0
    require(active, "direction is linear on the ordered cone")
    return values


def validate_selected_records(
    selected: object,
    expected_count: int,
    expected_digest: str,
) -> list[dict[str, Any]]:
    require(isinstance(selected, list) and len(selected) == expected_count, "selected census drift")
    require(
        all(isinstance(item, dict) and set(item) == {"direction", "residues"} for item in selected),
        "selected record shape drift",
    )
    directions = [item["direction"] for item in selected]
    require(
        directions == sorted(directions)
        and len({tuple(direction) for direction in directions}) == expected_count
        and all(validate_direction(direction) == direction for direction in directions),
        "selected direction order/shape drift",
    )
    require(
        all(
            isinstance(item["residues"], list)
            and len(item["residues"]) == len(PRIMES)
            and all(
                isinstance(value, int) and 0 <= value < prime
                for value, prime in zip(item["residues"], PRIMES, strict=True)
            )
            and item["residues"] != [0, 0]
            for item in selected
        ),
        "selected residue drift",
    )
    require(is_sha256(expected_digest) and digest_selected(selected) == expected_digest, "selected digest drift")
    return selected


def validate_prior_artifacts(
    old_replay: dict[str, Any],
    old_price: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[tuple[int, int]]]:
    require_digest(sha256_path(PRIOR_MANIFEST_PATH), PRIOR_MANIFEST_SHA256, "prior master manifest")
    require_digest(sha256_path(PRIOR_RESULT_PATH), PRIOR_RESULT_SHA256, "prior master result")
    manifest = load_json(PRIOR_MANIFEST_PATH)
    prior_result = load_json(PRIOR_RESULT_PATH)
    AUDITED.validate_master_manifest(
        manifest,
        ANCESTOR_SHA256,
        AUDITED.load_panel_seed(),
        OLD_BATCH_RESIDUAL_DIGEST,
        [item["direction"] for item in old_replay["selected"]],
    )
    require(
        manifest.get("solver") == {"path": relative(ANCESTOR_PATH), "sha256": ANCESTOR_SHA256}
        and int(manifest.get("rows")) == OLD_ROWS
        and manifest.get("exact_batch_residuals_decimal_lf_sha256") == OLD_BATCH_RESIDUAL_DIGEST,
        "prior manifest semantic drift",
    )

    require(
        prior_result.get("schema") == "max11-g0121-full-family-master-result-v1"
        and prior_result.get("result") == "FULL_FAMILY_EXACT_Q_MEMBER"
        and prior_result.get("manifest_path") == relative(PRIOR_MANIFEST_PATH)
        and prior_result.get("manifest_sha256") == PRIOR_MANIFEST_SHA256
        and prior_result.get("solver_sha256") == ANCESTOR_SHA256
        and int(prior_result.get("records")) == RECORDS
        and int(prior_result.get("rows")) == OLD_ROWS
        and prior_result.get("all_rows_replayed") is True
        and prior_result.get("coefficient_plus_one_mutant_rejected") is True
        and prior_result.get("batch_exact_residuals_decimal_lf_sha256") == OLD_BATCH_RESIDUAL_DIGEST,
        "prior result identity drift",
    )
    expected_directions = [direction for _, direction in AUDITED.COORDINATES] + old_price["directions"]
    require(prior_result.get("hinge_directions") == expected_directions, "prior hinge direction drift")

    selected = prior_result.get("selected_sequences")
    support = prior_result.get("support_sequences")
    coordinate_rows = prior_result.get("coordinate_rows")
    require(
        isinstance(selected, list)
        and selected == support
        and len(selected) == len(set(selected)) == INITIAL_RANK
        and selected == sorted(selected)
        and all(isinstance(sequence, int) and 0 <= sequence < RECORDS for sequence in selected),
        "prior selected/support basis drift",
    )
    require(
        isinstance(coordinate_rows, list)
        and len(coordinate_rows) == len(set(coordinate_rows)) == INITIAL_RANK
        and all(isinstance(row, int) and 0 <= row < OLD_ROWS for row in coordinate_rows),
        "prior coordinate-row basis drift",
    )
    require(prior_result.get("selected_basis_i128le_sha256") == OLD_SELECTED_DIGEST, "prior basis digest label drift")

    scale = canonical_integer(prior_result.get("target_scale"), "prior target scale", positive=True)
    raw_coefficients = prior_result.get("integer_coefficients")
    require(isinstance(raw_coefficients, list) and len(raw_coefficients) == INITIAL_RANK, "prior coefficient census drift")
    coefficients = [canonical_integer(value, f"prior coefficient {index}") for index, value in enumerate(raw_coefficients)]
    divisor = scale
    for coefficient in coefficients:
        divisor = math.gcd(divisor, abs(coefficient))
    require(divisor == 1 and any(coefficients), "prior coefficients/scale are not primitive")

    raw_terms = prior_result.get("terms")
    require(isinstance(raw_terms, list), "prior terms missing")
    expected_terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(support, coefficients, strict=True)
        if coefficient
    ]
    require(raw_terms == expected_terms and len(raw_terms) == 131, "prior canonical term projection drift")
    terms = [(item["sequence"], int(item["coefficient"])) for item in raw_terms]

    trials = prior_result.get("trials")
    require(isinstance(trials, list) and len(trials) == 42, "prior trial transcript census drift")
    for iteration, trial in enumerate(trials):
        require(int(trial.get("iteration", -1)) == iteration, "prior trial order drift")
        expected_rank = 115 + iteration
        if iteration < 41:
            require(
                trial.get("result") == "SEPARATOR_VIOLATED"
                and int(trial.get("rank")) == expected_rank
                and int(trial.get("augmented_rank")) == expected_rank + 1
                and isinstance(trial.get("first_violating_sequence"), int)
                and canonical_integer(trial.get("first_violating_price"), f"prior trial {iteration} price", nonzero=True)
                and 1 <= int(trial.get("columns_scanned")) <= RECORDS,
                "prior continuation transcript drift",
            )
        else:
            require(
                trial == {"iteration": 41, "rank": INITIAL_RANK, "augmented_rank": INITIAL_RANK, "result": "EXACT_Q_MEMBER"},
                "prior terminal transcript drift",
            )
    return manifest, prior_result, terms


G0126_BINDINGS = {
    "candidate": PRIOR_RESULT_SHA256,
    "cargo_lock": STATIC_EXPECTED_INPUTS["artifacts/math/G-0126/Cargo.lock"],
    "cargo_manifest": STATIC_EXPECTED_INPUTS["artifacts/math/G-0126/Cargo.toml"],
    "executable": "ae7f64ce737d8f12d9f4a3d5695fe8ded4b5a89720eff8a0f5a537b2126bfa28",
    "kernel": AUDITED.EXPECTED_INPUTS["artifacts/math/G-0117/src/lib.rs"],
    "master_manifest": PRIOR_MANIFEST_SHA256,
    "master_solver": ANCESTOR_SHA256,
    "normal_form_uniqueness": AUDITED.EXPECTED_INPUTS["artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md"],
    "output_protocol": "pre-serialized_same-directory_O_EXCL_temp_then_atomic_no-overwrite_hard-link_after_all_controls_and_end_binding_recheck",
    "panel_input": AUDITED.EXPECTED_INPUTS["artifacts/math/G-0113/panel_solver_input_v1.json"],
    "preregistration": STATIC_EXPECTED_INPUTS["artifacts/math/G-0126/GLOBAL_REPLAY_PREREGISTRATION.md"],
    "producer": STATIC_EXPECTED_INPUTS["artifacts/math/G-0126/src/main.rs"],
}


def validate_g0126_receipt(old_directions: list[list[int]]) -> tuple[dict[str, Any], list[dict[str, Any]], list[int]]:
    receipt = load_json(G0126_RECEIPT_PATH)
    expected_keys = {
        "schema", "result", "claim_boundary", "bindings", "candidate_schema", "candidate_result",
        "target_scale", "primes", "batch_k", "selection_rule", "complete_global_replay", "terms",
        "hinge_entries_processed", "labelled_permutations_checked", "aggregate_hinge_support",
        "nonzero_hinge_residue_directions", "carry_forward_checks", "first_carry_forward_failure",
        "linear_residues_after_target", "all_hinge_and_linear_residues_zero", "selected_count",
        "selected_prefix_i8_u64_le_sha256", "selected", "exact_selected_prices_decimal_lf_sha256",
        "exact_selected_prices", "first_nonzero_linear", "exact_replay", "coefficient_plus_one_mutant",
        "wall_seconds",
    }
    require(set(receipt) == expected_keys, "G-0126 top-level key drift")
    require(
        receipt.get("schema") == "max11-g0126-global-replay-v1"
        and receipt.get("result") == "GLOBAL_MODULAR_RESIDUAL"
        and receipt.get("bindings") == G0126_BINDINGS
        and receipt.get("candidate_schema") == "max11-g0121-full-family-master-result-v1"
        and receipt.get("candidate_result") == "FULL_FAMILY_EXACT_Q_MEMBER"
        and receipt.get("primes") == PRIMES
        and int(receipt.get("batch_k")) == NEW_BATCH_ROWS
        and receipt.get("complete_global_replay") is True
        and int(receipt.get("terms")) == 131,
        "G-0126 identity/protocol drift",
    )
    prior = load_json(PRIOR_RESULT_PATH)
    require(receipt.get("target_scale") == prior.get("target_scale"), "G-0126 target-scale bridge drift")
    require(
        int(receipt.get("hinge_entries_processed")) == 4_667_940
        and int(receipt.get("labelled_permutations_checked")) == 131 * math.factorial(N)
        and int(receipt.get("aggregate_hinge_support")) == 178_145
        and int(receipt.get("nonzero_hinge_residue_directions")) == 178_040
        and receipt.get("all_hinge_and_linear_residues_zero") == [False, False],
        "G-0126 complete-replay census drift",
    )
    carry = receipt.get("carry_forward_checks")
    require(isinstance(carry, list) and len(carry) == len(old_directions), "G-0126 carry-forward census drift")
    for index, (check, direction) in enumerate(zip(carry, old_directions, strict=True)):
        require(
            isinstance(check, dict)
            and check.get("index") == index
            and check.get("direction") == direction
            and check.get("residues") == [0, 0]
            and check.get("zero_in_both_fields") is True,
            f"G-0126 carry-forward check {index} drift",
        )
    require(receipt.get("first_carry_forward_failure") is None, "G-0126 carry-forward failure drift")
    require(receipt.get("linear_residues_after_target") == [[0] * N, [0] * N], "G-0126 linear bridge drift")
    require(receipt.get("first_nonzero_linear") is None, "G-0126 first-linear drift")

    selected = validate_selected_records(receipt.get("selected"), NEW_BATCH_ROWS, NEW_SELECTED_DIGEST)
    require(
        int(receipt.get("selected_count")) == len(selected)
        and receipt.get("selected_prefix_i8_u64_le_sha256") == NEW_SELECTED_DIGEST,
        "G-0126 selected receipt drift",
    )
    exact_records = receipt.get("exact_selected_prices")
    require(isinstance(exact_records, list) and len(exact_records) == NEW_BATCH_ROWS, "G-0126 exact residual census drift")
    exact_values: list[int] = []
    for index, (record, selected_item) in enumerate(zip(exact_records, selected, strict=True)):
        require(
            isinstance(record, dict)
            and set(record) == {"direction", "modular_residues", "exact_residual"}
            and record.get("direction") == selected_item["direction"]
            and record.get("modular_residues") == selected_item["residues"],
            f"G-0126 exact residual record {index} drift",
        )
        exact = canonical_integer(record.get("exact_residual"), f"G-0126 exact residual {index}", nonzero=True)
        require([exact % prime for prime in PRIMES] == selected_item["residues"], f"G-0126 exact/modular bridge {index} drift")
        exact_values.append(exact)
    residual_digest = hashlib.sha256(("\n".join(str(value) for value in exact_values) + "\n").encode()).hexdigest()
    require(
        residual_digest == NEW_EXACT_RESIDUAL_DIGEST
        and receipt.get("exact_selected_prices_decimal_lf_sha256") == NEW_EXACT_RESIDUAL_DIGEST,
        "G-0126 exact residual stream drift",
    )
    require(
        receipt.get("exact_replay", {}).get("performed") is False
        and receipt.get("exact_replay", {}).get("result") == "NOT_TRIGGERED_MODULAR_NONZERO",
        "G-0126 exact replay branch drift",
    )
    require(
        receipt.get("coefficient_plus_one_mutant")
        == {
            "sequence": 0,
            "coefficient_delta": "+1",
            "carry_forward_residues_match": False,
            "linear_residues_match": False,
            "nonzero_hinge_count_matches": False,
            "selected_prefix_matches": False,
            "rejected": True,
        },
        "G-0126 mutant drift",
    )
    return receipt, selected, exact_values


def validate_g0127_price_row(
    row: object,
    selected_item: dict[str, Any],
    exact_residual: int,
    index: int,
    expected_records: int,
) -> tuple[list[int], bytes]:
    require(isinstance(row, dict), f"G-0127 row {index} object required")
    expected_keys = {
        "direction", "modular_residues", "records", "nonzero_hinge_coefficients",
        "minimum_hinge_coefficient", "maximum_hinge_coefficient", "maximum_absolute_hinge_coefficient",
        "hinge_coefficients_i64_le_sha256", "exact_candidate_residual", "hinge_coefficients",
    }
    require(set(row) == expected_keys, f"G-0127 row {index} key drift")
    raw = row.get("hinge_coefficients")
    require(
        isinstance(raw, list)
        and len(raw) == expected_records
        and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in raw),
        f"G-0127 row {index} length/type drift",
    )
    coefficients = [int(value) for value in raw]
    require(
        row.get("direction") == selected_item["direction"]
        and row.get("modular_residues") == selected_item["residues"]
        and int(row.get("records")) == expected_records
        and int(row.get("nonzero_hinge_coefficients")) == sum(value != 0 for value in coefficients)
        and int(row.get("minimum_hinge_coefficient")) == min(coefficients)
        and int(row.get("maximum_hinge_coefficient")) == max(coefficients)
        and int(row.get("maximum_absolute_hinge_coefficient")) == max(abs(value) for value in coefficients)
        and canonical_integer(row.get("exact_candidate_residual"), f"G-0127 row {index} exact residual", nonzero=True) == exact_residual,
        f"G-0127 row {index} semantic drift",
    )
    encoded = b"".join(value.to_bytes(8, "little", signed=True) for value in coefficients)
    require(
        is_sha256(row.get("hinge_coefficients_i64_le_sha256"))
        and hashlib.sha256(encoded).hexdigest() == row["hinge_coefficients_i64_le_sha256"],
        f"G-0127 row {index} digest drift",
    )
    return coefficients, encoded


G0127_TOP_LEVEL_KEYS = {
    "schema", "result", "claim_boundary", "bindings", "batch_k", "records", "hinge_entries",
    "linear_entries", "selected_count", "selected_prefix_i8_u64_le_sha256", "directions",
    "modular_residues", "direction_major_hinge_i64_le_sha256", "linear_vectors_i64_le_sha256",
    "exact_candidate_residuals_decimal_lf_sha256", "exact_candidate_residuals",
    "exact_candidate_linear_dots", "rows", "linear_vectors", "coefficient_plus_one_mutant",
    "wall_seconds",
}
G0127_CLAIM_BOUNDARY = (
    "Exact 32-row ordered-cone hinge coordinates and all 11 linear coordinates over the frozen "
    "163,740-record family, with candidate dot-product bridges. This is restricted-master input "
    "only, not a membership decision, family-completeness theorem, global MAX11 identity, lower "
    "bound, or Lean theorem."
)
OUTPUT_PROTOCOL = (
    "pre-serialized_same-directory_O_EXCL_temp_then_atomic_no-overwrite_hard-link_after_all_controls_and_end_binding_recheck"
)


def expected_g0127_bindings() -> dict[str, str]:
    require_future_frozen()
    return {
        "producer": FUTURE_EXPECTED_INPUTS[relative(G0127_SOURCE_PATH)],
        "cargo_manifest": FUTURE_EXPECTED_INPUTS[relative(G0127_CARGO_PATH)],
        "cargo_lock": FUTURE_EXPECTED_INPUTS[relative(G0127_LOCK_PATH)],
        "preregistration": STATIC_EXPECTED_INPUTS[relative(G0127_PREREGISTRATION_PATH)],
        "kernel": AUDITED.EXPECTED_INPUTS["artifacts/math/G-0117/src/lib.rs"],
        "g0126_preregistration": STATIC_EXPECTED_INPUTS[relative(G0126_PREREGISTRATION_PATH)],
        "g0126_producer": STATIC_EXPECTED_INPUTS[relative(G0126_SOURCE_PATH)],
        "g0126_executable": "ae7f64ce737d8f12d9f4a3d5695fe8ded4b5a89720eff8a0f5a537b2126bfa28",
        "audited_ancestor_producer": AUDITED.EXPECTED_INPUTS[
            "artifacts/math/G-0117/src/bin/g0118_batch_coordinate_pricer.rs"
        ],
        "audited_ancestor_review": STATIC_EXPECTED_INPUTS[
            "artifacts/reviews/G-0118-iteration4-batch/review_v1.json"
        ],
        "panel_input": AUDITED.EXPECTED_INPUTS["artifacts/math/G-0113/panel_solver_input_v1.json"],
        "g0126_receipt": STATIC_EXPECTED_INPUTS[relative(G0126_RECEIPT_PATH)],
        "candidate": PRIOR_RESULT_SHA256,
        "executable": G0127_EXECUTABLE_SHA256,
        "output_protocol": OUTPUT_PROTOCOL,
    }


def validate_g0127_receipt(
    selected: list[dict[str, Any]],
    exact_residuals: list[int],
    prior_terms: list[tuple[int, int]],
    prior_scale: int,
) -> tuple[dict[str, Any], list[list[int]], list[list[int]]]:
    price = load_json(G0127_PRICE_PATH)
    require(set(price) == G0127_TOP_LEVEL_KEYS, "G-0127 top-level key drift")
    require(
        price.get("schema") == "max11-g0127-batch32-coordinate-prices-v1"
        and price.get("result") == "EXACT_FULL_FAMILY_BATCH32_COORDINATES"
        and price.get("claim_boundary") == G0127_CLAIM_BOUNDARY
        and price.get("bindings") == expected_g0127_bindings(),
        "G-0127 identity/binding drift",
    )
    require(
        int(price.get("batch_k")) == NEW_BATCH_ROWS
        and int(price.get("records")) == RECORDS
        and int(price.get("hinge_entries")) == NEW_BATCH_ROWS * RECORDS
        and int(price.get("linear_entries")) == RECORDS * N
        and int(price.get("selected_count")) == NEW_BATCH_ROWS
        and price.get("selected_prefix_i8_u64_le_sha256") == NEW_SELECTED_DIGEST,
        "G-0127 dimension/selection drift",
    )
    directions = [item["direction"] for item in selected]
    residues = [item["residues"] for item in selected]
    require(
        price.get("directions") == directions and price.get("modular_residues") == residues,
        "G-0127 direction/residue order drift",
    )
    raw_rows = price.get("rows")
    raw_linear = price.get("linear_vectors")
    require(isinstance(raw_rows, list) and len(raw_rows) == NEW_BATCH_ROWS, "G-0127 row census drift")
    require(
        isinstance(raw_linear, list)
        and len(raw_linear) == RECORDS
        and all(
            isinstance(row, list)
            and len(row) == N
            and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in row)
            for row in raw_linear
        ),
        "G-0127 linear vector shape/type drift",
    )
    linear = [[int(value) for value in row] for row in raw_linear]
    require(
        digest_i64(value for row in linear for value in row) == LINEAR_DIGEST
        and price.get("linear_vectors_i64_le_sha256") == LINEAR_DIGEST,
        "G-0127 linear stream drift",
    )

    aggregate = hashlib.sha256()
    rows: list[list[int]] = []
    recomputed_residuals: list[int] = []
    for index, (raw_row, selected_item, expected_exact) in enumerate(
        zip(raw_rows, selected, exact_residuals, strict=True)
    ):
        coefficients, encoded = validate_g0127_price_row(
            raw_row, selected_item, expected_exact, index, RECORDS
        )
        aggregate.update(encoded)
        exact = sum(coefficient * coefficients[sequence] for sequence, coefficient in prior_terms)
        require(exact == expected_exact, f"G-0127 independent candidate dot bridge {index} drift")
        require([exact % prime for prime in PRIMES] == selected_item["residues"], f"G-0127 modular bridge {index} drift")
        recomputed_residuals.append(exact)
        rows.append(coefficients)
    require(
        aggregate.hexdigest() == price.get("direction_major_hinge_i64_le_sha256"),
        "G-0127 aggregate hinge stream drift",
    )
    require(
        price.get("exact_candidate_residuals") == [str(value) for value in recomputed_residuals]
        and price.get("exact_candidate_residuals_decimal_lf_sha256") == NEW_EXACT_RESIDUAL_DIGEST
        and hashlib.sha256(("\n".join(str(value) for value in recomputed_residuals) + "\n").encode()).hexdigest()
        == NEW_EXACT_RESIDUAL_DIGEST,
        "G-0127 exact residual stream drift",
    )
    linear_dots = [
        sum(coefficient * linear[sequence][rank] for sequence, coefficient in prior_terms)
        for rank in range(N)
    ]
    require(
        linear_dots == [0] * (N - 1) + [prior_scale * math.factorial(N)]
        and price.get("exact_candidate_linear_dots") == [str(value) for value in linear_dots],
        "G-0127 exact linear bridge drift",
    )
    require(
        price.get("coefficient_plus_one_mutant")
        == {
            "sequence": 0,
            "coefficient_delta": "+1",
            "hinge_dot_receipt_changed": True,
            "linear_dot_receipt_changed": True,
            "rejected": True,
        },
        "G-0127 mutant drift",
    )
    return price, rows, linear


def load_validated_components() -> dict[str, Any]:
    validate_expected_inputs(include_future=True)
    AUDITED.validate_cache_receipt()
    old_candidate, old_replay, old_price, old_exact_residuals = AUDITED.validate_batch_receipts()
    old_candidate_terms = AUDITED.canonical_terms(old_candidate)
    accumulated = AUDITED.load_accumulated(old_price["linear_vectors"], old_candidate_terms)
    old_linear = [[int(value) for value in row] for row in old_price["linear_vectors"]]
    old_batch = [[int(value) for value in row["hinge_coefficients"]] for row in old_price["rows"]]
    require(
        len(accumulated) == ACCUMULATED_ROWS
        and len(old_batch) == OLD_BATCH_ROWS
        and len(old_linear) == RECORDS,
        "old row component census drift",
    )
    _, prior_result, prior_terms = validate_prior_artifacts(old_replay, old_price)
    prior_scale = canonical_integer(prior_result["target_scale"], "prior target scale", positive=True)
    old_directions = prior_result["hinge_directions"]
    g0126, selected, exact_residuals = validate_g0126_receipt(old_directions)
    g0127, new_batch, new_linear = validate_g0127_receipt(selected, exact_residuals, prior_terms, prior_scale)
    require(old_linear == new_linear, "old/G-0127 linear vectors differ")
    return {
        "old_candidate": old_candidate,
        "old_replay": old_replay,
        "old_price": old_price,
        "old_exact_residuals": old_exact_residuals,
        "accumulated": accumulated,
        "linear": old_linear,
        "old_batch": old_batch,
        "prior_result": prior_result,
        "prior_terms": prior_terms,
        "prior_scale": prior_scale,
        "g0126": g0126,
        "selected": selected,
        "new_exact_residuals": exact_residuals,
        "g0127": g0127,
        "new_batch": new_batch,
    }


def old_column(
    cache: mmap.mmap,
    sequence: int,
    linear: Sequence[Sequence[int]],
    accumulated: Sequence[Sequence[int]],
    old_batch: Sequence[Sequence[int]],
) -> list[int]:
    result = AUDITED.panel_column(cache, sequence)
    result.extend(int(value) for value in linear[sequence])
    result.extend(int(row[sequence]) for row in accumulated)
    result.extend(int(row[sequence]) for row in old_batch)
    require(len(result) == OLD_ROWS, "old column dimension drift")
    return result


def full_column(
    cache: mmap.mmap,
    sequence: int,
    linear: Sequence[Sequence[int]],
    accumulated: Sequence[Sequence[int]],
    old_batch: Sequence[Sequence[int]],
    new_batch: Sequence[Sequence[int]],
) -> list[int]:
    result = old_column(cache, sequence, linear, accumulated, old_batch)
    result.extend(int(row[sequence]) for row in new_batch)
    require(len(result) == ROWS, "full column dimension drift")
    return result


def matrix_rows(columns: Sequence[Sequence[int]], row_count: int = ROWS) -> list[list[int]]:
    require(columns and all(len(column) == row_count for column in columns), "ragged columns")
    return [[int(column[row]) for column in columns] for row in range(row_count)]


def scan_first_violation_records(
    separator: Sequence[int],
    record_count: int,
    column_loader,
) -> tuple[int, int, int] | None:
    require(record_count >= 0 and separator and any(separator), "invalid separator")
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    for sequence in range(record_count):
        column = column_loader(sequence)
        require(len(column) == len(separator), "separator/column dimension drift")
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price, sequence + 1
    return None


def scan_first_violation(separator: Sequence[int], column_loader) -> tuple[int, int, int] | None:
    require(len(separator) == ROWS, "separator row dimension drift")
    return scan_first_violation_records(separator, RECORDS, column_loader)


def normalize_member(values: Sequence[Fraction]) -> tuple[list[int], int]:
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
    require(scale > 0 and common == 1, "member not primitive")
    return integers, scale


def validate_primitive_separator(separator: Sequence[int], pairing: int, target: Sequence[int]) -> None:
    require(len(separator) == len(target) == ROWS and any(separator), "separator dimension/zero drift")
    divisor = 0
    for value in separator:
        divisor = math.gcd(divisor, abs(int(value)))
    require(divisor == 1, "separator is not primitive")
    require(next(int(value) for value in separator if value) > 0, "separator sign normalization drift")
    require(pairing == sum(int(a) * int(b) for a, b in zip(separator, target, strict=True)) and pairing != 0, "separator target pairing drift")


def build_target() -> list[int]:
    source = load_json(AUDITED.PANEL_INPUT_PATH)
    target = [int(value) for value in source["target"]] + [0] * (ROWS - PANEL_ROWS)
    target[PANEL_ROWS + N - 1] = math.factorial(N)
    require(len(target) == ROWS, "target dimension drift")
    return target


def validate_manifest_input_records(items: object, expected: dict[str, str]) -> dict[str, str]:
    require(isinstance(items, list) and len(items) == len(expected), "manifest input census drift")
    names: list[str] = []
    observed: dict[str, str] = {}
    for item in items:
        require(isinstance(item, dict) and set(item) == {"path", "sha256"}, "malformed manifest input record")
        name = item["path"]
        digest = item["sha256"]
        require(isinstance(name, str) and name and not Path(name).is_absolute(), "invalid manifest input path")
        require(relative(ROOT / name) == name, "noncanonical manifest input path")
        require(is_sha256(digest), f"malformed manifest input SHA-256: {name}")
        names.append(name)
        require(name not in observed, f"duplicate manifest input: {name}")
        observed[name] = digest
    require(names == sorted(names) and observed == expected, "manifest input set/order drift")
    return observed


def manifest_row_decisions(components: dict[str, Any]) -> list[dict[str, Any]]:
    old_selected = components["old_replay"]["selected"]
    new_selected = components["selected"]
    decisions = [
        {
            "row_index": OLD_ROWS - OLD_BATCH_ROWS + index,
            "source": "G-0118",
            "receipt_index": index,
            "direction": item["direction"],
            "decision": "KEPT_CONSERVATIVELY",
        }
        for index, item in enumerate(old_selected)
    ]
    decisions.extend(
        {
            "row_index": OLD_ROWS + index,
            "source": "G-0126",
            "receipt_index": index,
            "direction": item["direction"],
            "decision": "KEPT_CONSERVATIVELY",
        }
        for index, item in enumerate(new_selected)
    )
    require(len(decisions) == OLD_BATCH_ROWS + NEW_BATCH_ROWS, "manifest decision census drift")
    return decisions


MANIFEST_KEYS = {
    "schema", "result", "claim_boundary", "solver", "preregistration", "audited_ancestor",
    "prior_master_manifest", "prior_master_result", "g0126_receipt", "g0127_price_receipt",
    "expected_inputs", "records", "panel_rows", "linear_rows", "accumulated_rows",
    "old_batch_rows", "new_batch_rows", "rows", "row_order", "batch_row_policy",
    "batch_row_decisions", "discarded_rows", "warm_seed_policy", "seed_sequences",
    "initial_rank", "max_rank_increases", "prior_candidate_terms", "old_batch_residuals_decimal_lf_sha256",
    "new_selected_prefix_i8_u64_le_sha256", "new_exact_residuals_decimal_lf_sha256",
    "complete_arithmetic_bridge", "wall_seconds",
}


def build_manifest(output: Path) -> dict[str, Any]:
    begun = time.perf_counter()
    output = contained(output)
    require(output == MANIFEST_PATH, "manifest output path drift")
    require(not output.exists(), "refusing to overwrite manifest")
    components = load_validated_components()
    inputs = validate_expected_inputs(include_future=True)
    script_sha256 = sha256_path(SCRIPT)
    result: dict[str, Any] = {
        "schema": "max11-g0128-full-family-master-manifest-v2",
        "result": "BOUND_380ROW_INPUTS_VALIDATED",
        "claim_boundary": "Inputs for an exact 380-row rational decision over the frozen 163,740-column family; not a global identity, family-completeness theorem, unrestricted MAX11 lower bound, or Lean theorem.",
        "solver": {"path": relative(SCRIPT), "sha256": script_sha256},
        "preregistration": {"path": relative(PREREGISTRATION), "sha256": PREREGISTRATION_SHA256},
        "audited_ancestor": {"path": relative(ANCESTOR_PATH), "sha256": ANCESTOR_SHA256},
        "prior_master_manifest": {"path": relative(PRIOR_MANIFEST_PATH), "sha256": PRIOR_MANIFEST_SHA256},
        "prior_master_result": {"path": relative(PRIOR_RESULT_PATH), "sha256": PRIOR_RESULT_SHA256},
        "g0126_receipt": {"path": relative(G0126_RECEIPT_PATH), "sha256": STATIC_EXPECTED_INPUTS[relative(G0126_RECEIPT_PATH)]},
        "g0127_price_receipt": {"path": relative(G0127_PRICE_PATH), "sha256": FUTURE_EXPECTED_INPUTS[relative(G0127_PRICE_PATH)]},
        "expected_inputs": [{"path": name, "sha256": digest} for name, digest in sorted(inputs.items())],
        "records": RECORDS,
        "panel_rows": PANEL_ROWS,
        "linear_rows": LINEAR_ROWS,
        "accumulated_rows": ACCUMULATED_ROWS,
        "old_batch_rows": OLD_BATCH_ROWS,
        "new_batch_rows": NEW_BATCH_ROWS,
        "rows": ROWS,
        "row_order": ["panel:301", "linear:11", "accumulated:G-0117/G-0118:4", "batch:G-0118:32", "batch:G-0126:32"],
        "batch_row_policy": "All prior 32 and new 32 Batch32 rows retained in source-receipt order; no dependency discard attempted.",
        "batch_row_decisions": manifest_row_decisions(components),
        "discarded_rows": [],
        "warm_seed_policy": "The sealed G-0121 selected_sequences/support_sequences basis, independently replayed on 348 rows and exact-rank checked again on 380 rows.",
        "seed_sequences": components["prior_result"]["selected_sequences"],
        "initial_rank": INITIAL_RANK,
        "max_rank_increases": MAX_RANK_INCREASES,
        "prior_candidate_terms": len(components["prior_terms"]),
        "old_batch_residuals_decimal_lf_sha256": OLD_BATCH_RESIDUAL_DIGEST,
        "new_selected_prefix_i8_u64_le_sha256": NEW_SELECTED_DIGEST,
        "new_exact_residuals_decimal_lf_sha256": NEW_EXACT_RESIDUAL_DIGEST,
        "complete_arithmetic_bridge": True,
        "wall_seconds": time.perf_counter() - begun,
    }
    require(set(result) == MANIFEST_KEYS, "manifest key census drift")
    require_digest(sha256_path(SCRIPT), script_sha256, "solver during manifest build")
    validate_expected_inputs(include_future=True)
    write_exclusive(output, result)
    return result


def validate_master_manifest(
    manifest: dict[str, Any],
    script_sha256: str,
    components: dict[str, Any],
) -> None:
    require(set(manifest) == MANIFEST_KEYS, "master manifest key drift")
    require(
        manifest.get("schema") == "max11-g0128-full-family-master-manifest-v2"
        and manifest.get("result") == "BOUND_380ROW_INPUTS_VALIDATED"
        and manifest.get("claim_boundary")
        == "Inputs for an exact 380-row rational decision over the frozen 163,740-column family; not a global identity, family-completeness theorem, unrestricted MAX11 lower bound, or Lean theorem.",
        "master manifest identity drift",
    )
    require(
        manifest.get("solver") == {"path": relative(SCRIPT), "sha256": script_sha256}
        and manifest.get("preregistration") == {"path": relative(PREREGISTRATION), "sha256": PREREGISTRATION_SHA256}
        and manifest.get("audited_ancestor") == {"path": relative(ANCESTOR_PATH), "sha256": ANCESTOR_SHA256}
        and manifest.get("prior_master_manifest") == {"path": relative(PRIOR_MANIFEST_PATH), "sha256": PRIOR_MANIFEST_SHA256}
        and manifest.get("prior_master_result") == {"path": relative(PRIOR_RESULT_PATH), "sha256": PRIOR_RESULT_SHA256}
        and manifest.get("g0126_receipt") == {"path": relative(G0126_RECEIPT_PATH), "sha256": STATIC_EXPECTED_INPUTS[relative(G0126_RECEIPT_PATH)]}
        and manifest.get("g0127_price_receipt") == {"path": relative(G0127_PRICE_PATH), "sha256": FUTURE_EXPECTED_INPUTS[relative(G0127_PRICE_PATH)]},
        "master manifest custody drift",
    )
    validate_manifest_input_records(manifest.get("expected_inputs"), expected_inputs())
    require(
        int(manifest.get("records")) == RECORDS
        and int(manifest.get("panel_rows")) == PANEL_ROWS
        and int(manifest.get("linear_rows")) == LINEAR_ROWS
        and int(manifest.get("accumulated_rows")) == ACCUMULATED_ROWS
        and int(manifest.get("old_batch_rows")) == OLD_BATCH_ROWS
        and int(manifest.get("new_batch_rows")) == NEW_BATCH_ROWS
        and int(manifest.get("rows")) == ROWS
        and int(manifest.get("initial_rank")) == INITIAL_RANK
        and int(manifest.get("max_rank_increases")) == MAX_RANK_INCREASES
        and int(manifest.get("prior_candidate_terms")) == 131
        and manifest.get("complete_arithmetic_bridge") is True,
        "master manifest dimension/protocol drift",
    )
    require(
        manifest.get("row_order") == ["panel:301", "linear:11", "accumulated:G-0117/G-0118:4", "batch:G-0118:32", "batch:G-0126:32"]
        and manifest.get("batch_row_policy")
        == "All prior 32 and new 32 Batch32 rows retained in source-receipt order; no dependency discard attempted."
        and manifest.get("batch_row_decisions") == manifest_row_decisions(components)
        and manifest.get("discarded_rows") == [],
        "master manifest row order/policy drift",
    )
    require(
        manifest.get("warm_seed_policy")
        == "The sealed G-0121 selected_sequences/support_sequences basis, independently replayed on 348 rows and exact-rank checked again on 380 rows."
        and manifest.get("seed_sequences") == components["prior_result"]["selected_sequences"]
        and manifest.get("old_batch_residuals_decimal_lf_sha256") == OLD_BATCH_RESIDUAL_DIGEST
        and manifest.get("new_selected_prefix_i8_u64_le_sha256") == NEW_SELECTED_DIGEST
        and manifest.get("new_exact_residuals_decimal_lf_sha256") == NEW_EXACT_RESIDUAL_DIGEST,
        "master manifest seed/digest drift",
    )


def validate_warm_start(
    cache: mmap.mmap,
    components: dict[str, Any],
    helper: Any,
    target: list[int],
) -> tuple[list[int], list[list[int]]]:
    prior = components["prior_result"]
    selected = [int(value) for value in prior["selected_sequences"]]
    require(selected == sorted(set(selected)) and len(selected) == INITIAL_RANK, "warm seed drift")
    old_columns = [
        old_column(cache, sequence, components["linear"], components["accumulated"], components["old_batch"])
        for sequence in selected
    ]
    old_rows = matrix_rows(old_columns, OLD_ROWS)
    require(
        digest_i128(old_rows[row][column] for row in range(OLD_ROWS) for column in range(INITIAL_RANK))
        == OLD_SELECTED_DIGEST,
        "warm seed prior basis digest drift",
    )
    old_matrix = helper.qmatrix(old_rows)
    require(int(old_matrix.rank()) == INITIAL_RANK, "warm seed old exact rank drift")
    coefficients = [int(value) for value in prior["integer_coefficients"]]
    scale = int(prior["target_scale"])
    require(
        all(
            sum(coefficients[column] * old_rows[row][column] for column in range(INITIAL_RANK))
            == scale * target[row]
            for row in range(OLD_ROWS)
        ),
        "warm seed prior 348-row identity replay drift",
    )
    columns = [
        full_column(
            cache, sequence, components["linear"], components["accumulated"], components["old_batch"], components["new_batch"]
        )
        for sequence in selected
    ]
    rows = matrix_rows(columns)
    matrix = helper.qmatrix(rows)
    augmented = helper.qmatrix([row + [target[index]] for index, row in enumerate(rows)])
    require(int(matrix.rank()) == INITIAL_RANK, "warm seed 380-row exact rank drift")
    require(int(augmented.rank()) == INITIAL_RANK + 1, "new rows did not exactly reject warm-seed member")
    return selected, columns


def run(manifest_path: Path, output: Path) -> dict[str, Any]:
    begun = time.perf_counter()
    manifest_path = contained(manifest_path)
    output = contained(output)
    require(manifest_path == MANIFEST_PATH and manifest_path.is_file(), "master manifest path drift")
    require(output == RESULT_PATH, "master result output path drift")
    require(not output.exists(), "refusing to overwrite master result")
    manifest_sha256 = sha256_path(manifest_path)
    manifest = load_json(manifest_path)
    script_sha256 = sha256_path(SCRIPT)
    require(manifest.get("solver") == {"path": relative(SCRIPT), "sha256": script_sha256}, "solver binding drift")
    components = load_validated_components()
    validate_master_manifest(manifest, script_sha256, components)
    target = build_target()
    helper = AUDITED.load_module(AUDITED.HELPER_PATH, "g0128_exact_helper")
    rhs = helper.qmatrix([[value] for value in target])
    trials: list[dict[str, Any]] = []
    previous_rank = -1

    with AUDITED.CACHE_PATH.open("rb") as cache_file, mmap.mmap(
        cache_file.fileno(), 0, access=mmap.ACCESS_READ
    ) as cache:
        require(len(cache) == AUDITED.CACHE_BYTES, "cache mmap size drift")
        selected, warm_columns = validate_warm_start(cache, components, helper, target)
        for iteration in range(MAX_RANK_INCREASES + 1):
            require(selected == sorted(set(selected)), "selected column order drift")
            columns = warm_columns if iteration == 0 else [
                full_column(
                    cache,
                    sequence,
                    components["linear"],
                    components["accumulated"],
                    components["old_batch"],
                    components["new_batch"],
                )
                for sequence in selected
            ]
            integer_rows = matrix_rows(columns)
            matrix = helper.qmatrix(integer_rows)
            augmented = helper.qmatrix(
                [row + [target[index]] for index, row in enumerate(integer_rows)]
            )
            rank = int(matrix.rank())
            augmented_rank = int(augmented.rank())
            if iteration == 0:
                require(rank == INITIAL_RANK and augmented_rank == INITIAL_RANK + 1, "frozen warm-start rank drift")
            else:
                require(rank == previous_rank + 1, "appended column failed unit exact rank increase")
            previous_rank = rank

            if rank == augmented_rank:
                reduced, reduced_rank = matrix.rref()
                require(int(reduced_rank) == rank, "member RREF rank drift")
                pivot_indices = AUDITED.load_module(
                    AUDITED.HELPER_PATH, "g0128_exact_helper_pivots"
                ).pivot_columns(reduced, rank, len(selected))
                support_sequences = [selected[index] for index in pivot_indices]
                support_columns = [columns[index] for index in pivot_indices]
                basis_rows = matrix_rows(support_columns)
                basis = helper.qmatrix(basis_rows)
                transposed, transposed_rank = basis.transpose().rref()
                require(int(transposed_rank) == rank, "basis rank drift")
                coordinate_rows = helper.pivot_columns(transposed, rank, ROWS)
                square = helper.qmatrix(
                    [[basis_rows[row][column] for column in range(rank)] for row in coordinate_rows]
                )
                rational = square.solve(helper.qmatrix([[target[row]] for row in coordinate_rows]))
                require(basis * rational == rhs, "all-row rational replay failed")
                fractions = [Fraction(str(rational[index, 0])) for index in range(rank)]
                integers, scale = normalize_member(fractions)
                require(
                    all(
                        sum(integers[column] * basis_rows[row][column] for column in range(rank))
                        == scale * target[row]
                        for row in range(ROWS)
                    ),
                    "denominator-cleared all-row replay failed",
                )
                first_nonzero = next(index for index, value in enumerate(integers) if value)
                mutant = integers[:]
                mutant[first_nonzero] += 1
                mutant_rejected = any(
                    sum(mutant[column] * basis_rows[row][column] for column in range(rank))
                    != scale * target[row]
                    for row in range(ROWS)
                )
                require(mutant_rejected, "member coefficient mutant escaped")
                trials.append(
                    {
                        "iteration": iteration,
                        "rank": rank,
                        "augmented_rank": augmented_rank,
                        "result": "EXACT_Q_MEMBER",
                    }
                )
                result: dict[str, Any] = {
                    "schema": "max11-g0128-full-family-master-result-v2",
                    "result": "FULL_FAMILY_380ROW_EXACT_Q_MEMBER",
                    "claim_boundary": "Exact membership only on the frozen 380-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem, global MAX11 identity, lower bound, or Lean theorem.",
                    "manifest_path": relative(manifest_path),
                    "manifest_sha256": manifest_sha256,
                    "solver_sha256": script_sha256,
                    "audited_ancestor_sha256": ANCESTOR_SHA256,
                    "records": RECORDS,
                    "rows": ROWS,
                    "rank": rank,
                    "augmented_rank": augmented_rank,
                    "hinge_directions": components["prior_result"]["hinge_directions"]
                    + [item["direction"] for item in components["selected"]],
                    "selected_sequences": selected,
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_i128le_sha256": digest_i128(
                        basis_rows[row][column]
                        for row in range(ROWS)
                        for column in range(rank)
                    ),
                    "target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "terms": [
                        {"sequence": sequence, "coefficient": str(coefficient)}
                        for sequence, coefficient in zip(support_sequences, integers, strict=True)
                        if coefficient
                    ],
                    "all_380_rows_replayed": True,
                    "coefficient_plus_one_mutant_rejected": mutant_rejected,
                    "prior_candidate_rejected_on_all_32_new_rows": all(
                        value != 0 for value in components["new_exact_residuals"]
                    ),
                    "old_batch_residuals_decimal_lf_sha256": OLD_BATCH_RESIDUAL_DIGEST,
                    "new_selected_prefix_i8_u64_le_sha256": NEW_SELECTED_DIGEST,
                    "new_exact_residuals_decimal_lf_sha256": NEW_EXACT_RESIDUAL_DIGEST,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require_digest(sha256_path(SCRIPT), script_sha256, "solver during run")
                require_digest(sha256_path(manifest_path), manifest_sha256, "manifest during run")
                validate_expected_inputs(include_future=True)
                write_exclusive(output, result)
                return result

            separator, pairing, free_row = helper.first_target_separator(matrix, integer_rows, target)
            validate_primitive_separator(separator, pairing, target)
            violation = scan_first_violation(
                separator,
                lambda sequence: full_column(
                    cache,
                    sequence,
                    components["linear"],
                    components["accumulated"],
                    components["old_batch"],
                    components["new_batch"],
                ),
            )
            trial = {
                "iteration": iteration,
                "rank": rank,
                "augmented_rank": augmented_rank,
                "separator_target_pairing": str(pairing),
                "separator_free_row": free_row,
                "first_violating_sequence": None if violation is None else violation[0],
                "first_violating_price": None if violation is None else str(violation[1]),
                "columns_scanned": RECORDS if violation is None else violation[2],
                "result": "FULL_FAMILY_380ROW_EXACT_Q_NONMEMBER"
                if violation is None
                else "SEPARATOR_VIOLATED",
            }
            trials.append(trial)
            if violation is None:
                first_nonzero = next(index for index, value in enumerate(separator) if value)
                mutant = separator[:]
                mutant[first_nonzero] += 1
                mutant_violation = scan_first_violation(
                    mutant,
                    lambda sequence: full_column(
                        cache,
                        sequence,
                        components["linear"],
                        components["accumulated"],
                        components["old_batch"],
                        components["new_batch"],
                    ),
                )
                mutant_pairing = sum(
                    value * rhs_value for value, rhs_value in zip(mutant, target, strict=True)
                )
                mutant_rejected = mutant_violation is not None or mutant_pairing == 0
                require(mutant_rejected, "separator mutant escaped")
                result = {
                    "schema": "max11-g0128-full-family-master-result-v2",
                    "result": "FULL_FAMILY_380ROW_EXACT_Q_NONMEMBER",
                    "claim_boundary": "Exact nonmembership only in the frozen 163,740-column family on the frozen 380 rows; not a family-completeness theorem, global MAX11 result, unrestricted lower bound, or Lean theorem.",
                    "manifest_path": relative(manifest_path),
                    "manifest_sha256": manifest_sha256,
                    "solver_sha256": script_sha256,
                    "audited_ancestor_sha256": ANCESTOR_SHA256,
                    "records": RECORDS,
                    "rows": ROWS,
                    "rank": rank,
                    "augmented_rank": augmented_rank,
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_family_columns_exactly_annihilated": True,
                    "complete_separator_scan": RECORDS,
                    "separator_plus_one_mutant_rejected": mutant_rejected,
                    "prior_candidate_rejected_on_all_32_new_rows": all(
                        value != 0 for value in components["new_exact_residuals"]
                    ),
                    "old_batch_residuals_decimal_lf_sha256": OLD_BATCH_RESIDUAL_DIGEST,
                    "new_selected_prefix_i8_u64_le_sha256": NEW_SELECTED_DIGEST,
                    "new_exact_residuals_decimal_lf_sha256": NEW_EXACT_RESIDUAL_DIGEST,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require_digest(sha256_path(SCRIPT), script_sha256, "solver during run")
                require_digest(sha256_path(manifest_path), manifest_sha256, "manifest during run")
                validate_expected_inputs(include_future=True)
                write_exclusive(output, result)
                return result
            require(violation[0] not in selected, "separator returned selected column")
            selected.append(violation[0])
            selected.sort()
    raise MasterError("exact master exceeded frozen rank-increase bound")


def self_test() -> None:
    rejected_controls: list[str] = []

    def expect_rejected(label: str, action) -> None:
        try:
            action()
        except Exception:
            rejected_controls.append(label)
            return
        raise MasterError(f"hostile control escaped: {label}")

    # Retain the exact 15-mutation hostile suite of the audited ancestor.
    AUDITED.self_test()
    require_future_frozen()
    validate_expected_inputs(include_future=True)

    helper = AUDITED.load_module(AUDITED.HELPER_PATH, "g0128_selftest_helper")
    false_member = helper.qmatrix([[1], [1]])
    false_target = helper.qmatrix([[1], [0]])
    require(
        int(false_member.rank()) == 1
        and int(helper.qmatrix([[1, 1], [1, 0]]).rank()) == 2
        and false_member * helper.qmatrix([[1]]) != false_target,
        "new-row false-member control failed",
    )
    old_only = helper.qmatrix([[1]])
    require(old_only * helper.qmatrix([[1]]) == helper.qmatrix([[1]]), "old-row positive control failed")

    omitted_columns = [[1, 0], [0, 1]]
    require(
        scan_first_violation_records([0, 1], 2, omitted_columns.__getitem__) == (1, 1, 2),
        "omitted final column control failed",
    )
    require(
        scan_first_violation_records([1, -1], 2, [[1, 1], [2, 2]].__getitem__) is None,
        "valid separator control failed",
    )
    require(
        scan_first_violation_records([2, -1], 2, [[1, 1], [2, 2]].__getitem__) is not None,
        "separator +1 mutant escaped",
    )
    values, scale = normalize_member([Fraction(2, 3), Fraction(-4, 9)])
    require(values == [6, -4] and scale == 9, "primitive member normalization failed")

    sample = [
        {"direction": [0] * 8 + [1, -2, 1], "residues": [1, 2]},
        {"direction": [0] * 7 + [1, -3, 0, 2], "residues": [3, 4]},
    ]
    sample_digest = digest_selected(sample)
    validate_selected_records(sample, 2, sample_digest)
    expect_rejected(
        "G-0126 selected order mutation",
        lambda: validate_selected_records(list(reversed(sample)), 2, sample_digest),
    )
    changed_residue = copy.deepcopy(sample)
    changed_residue[0]["residues"][0] += 1
    expect_rejected(
        "G-0126 selected residue mutation",
        lambda: validate_selected_records(changed_residue, 2, sample_digest),
    )
    nonzero_sum = copy.deepcopy(sample)
    nonzero_sum[0]["direction"][-1] += 1
    expect_rejected(
        "G-0126 nonzero-sum direction mutation",
        lambda: validate_selected_records(nonzero_sum, 2, sample_digest),
    )
    reversed_orientation = copy.deepcopy(sample)
    reversed_orientation[0]["direction"] = [-value for value in reversed_orientation[0]["direction"]]
    expect_rejected(
        "G-0126 reversed direction mutation",
        lambda: validate_selected_records(reversed_orientation, 2, sample_digest),
    )
    nonprimitive = copy.deepcopy(sample)
    nonprimitive[0]["direction"] = [2 * value for value in nonprimitive[0]["direction"]]
    expect_rejected(
        "G-0126 nonprimitive direction mutation",
        lambda: validate_selected_records(nonprimitive, 2, sample_digest),
    )
    inactive = copy.deepcopy(sample)
    inactive[0]["direction"] = [0] * 9 + [1, -1]
    expect_rejected(
        "G-0126 inactive direction mutation",
        lambda: validate_selected_records(inactive, 2, sample_digest),
    )
    exact_values = [5, -7]
    require(
        hashlib.sha256(("\n".join(str(value) for value in exact_values) + "\n").encode()).hexdigest()
        != hashlib.sha256(("5\n-8\n").encode()).hexdigest(),
        "exact residual stream mutant escaped",
    )

    coefficients = [1, -2, 0]
    selected_item = sample[0]
    price_row = {
        "direction": selected_item["direction"],
        "modular_residues": selected_item["residues"],
        "records": 3,
        "nonzero_hinge_coefficients": 2,
        "minimum_hinge_coefficient": -2,
        "maximum_hinge_coefficient": 1,
        "maximum_absolute_hinge_coefficient": 2,
        "hinge_coefficients_i64_le_sha256": digest_i64(coefficients),
        "exact_candidate_residual": "5",
        "hinge_coefficients": coefficients,
    }
    validate_g0127_price_row(price_row, selected_item, 5, 0, 3)
    truncated = copy.deepcopy(price_row)
    truncated["hinge_coefficients"] = truncated["hinge_coefficients"][:-1]
    expect_rejected(
        "G-0127 row truncation",
        lambda: validate_g0127_price_row(truncated, selected_item, 5, 0, 3),
    )
    reordered = copy.deepcopy(price_row)
    reordered["hinge_coefficients"] = [-2, 1, 0]
    expect_rejected(
        "G-0127 record order mutation",
        lambda: validate_g0127_price_row(reordered, selected_item, 5, 0, 3),
    )
    wrong_extrema = copy.deepcopy(price_row)
    wrong_extrema["minimum_hinge_coefficient"] = -1
    expect_rejected(
        "G-0127 extrema mutation",
        lambda: validate_g0127_price_row(wrong_extrema, selected_item, 5, 0, 3),
    )
    wrong_nonzero = copy.deepcopy(price_row)
    wrong_nonzero["nonzero_hinge_coefficients"] = 3
    expect_rejected(
        "G-0127 nonzero census mutation",
        lambda: validate_g0127_price_row(wrong_nonzero, selected_item, 5, 0, 3),
    )
    wrong_digest = copy.deepcopy(price_row)
    wrong_digest["hinge_coefficients_i64_le_sha256"] = "0" * 64
    expect_rejected(
        "G-0127 row digest mutation",
        lambda: validate_g0127_price_row(wrong_digest, selected_item, 5, 0, 3),
    )
    wrong_exact = copy.deepcopy(price_row)
    wrong_exact["exact_candidate_residual"] = "6"
    expect_rejected(
        "G-0127 exact residual mutation",
        lambda: validate_g0127_price_row(wrong_exact, selected_item, 5, 0, 3),
    )

    bindings = expected_g0127_bindings()
    changed_bindings = dict(bindings)
    changed_bindings["candidate"] = "0" * 64
    expect_rejected(
        "G-0127 binding mutation",
        lambda: require(changed_bindings == bindings, "G-0127 binding drift"),
    )
    require(
        ["old-0", "old-1"] + ["new-0", "new-1"]
        != ["new-0", "new-1"] + ["old-0", "old-1"],
        "old/new Batch32 source-confusion control failed",
    )
    expect_rejected("stale source", lambda: require_digest("0" * 64, "1" * 64, "source"))
    expect_rejected("stale preregistration", lambda: require_digest("2" * 64, "3" * 64, "preregistration"))
    expect_rejected("stale prior result", lambda: require_digest("4" * 64, "5" * 64, "prior result"))
    expect_rejected("stale future receipt", lambda: require_digest("6" * 64, "7" * 64, "future receipt"))
    expect_rejected("path escape", lambda: contained(ROOT.parent / "g0128-escape"))
    expect_rejected("ragged 380-row matrix", lambda: matrix_rows([[0] * ROWS, [0] * (ROWS - 1)]))

    small_expected = {
        relative(SCRIPT): sha256_path(SCRIPT),
        relative(PREREGISTRATION): sha256_path(PREREGISTRATION),
    }
    small_items = [{"path": name, "sha256": digest} for name, digest in sorted(small_expected.items())]
    validate_manifest_input_records(small_items, small_expected)
    expect_rejected(
        "duplicate manifest input",
        lambda: validate_manifest_input_records([small_items[0], copy.deepcopy(small_items[0])], small_expected),
    )
    expect_rejected("noncanonical coefficient", lambda: canonical_integer("+1", "coefficient"))

    with tempfile.TemporaryDirectory(dir=HERE) as raw:
        path = Path(raw) / "exclusive.json"
        write_exclusive(path, {"ok": True})
        expect_rejected("output overwrite", lambda: write_exclusive(path, {"ok": False}))
        partial = Path(raw) / "serialization-abort.json"
        expect_rejected("serialization abort", lambda: write_exclusive(partial, {"bad": {1}}))
        require(not partial.exists(), "serialization abort left a final-path artifact")

    components = load_validated_components()
    require(
        len(components["new_batch"]) == NEW_BATCH_ROWS
        and len(components["old_batch"]) == OLD_BATCH_ROWS
        and len(components["prior_terms"]) == 131,
        "full input-validation reachability control failed",
    )
    required_controls = {
        "G-0126 selected order mutation",
        "G-0126 selected residue mutation",
        "G-0126 nonzero-sum direction mutation",
        "G-0126 reversed direction mutation",
        "G-0126 nonprimitive direction mutation",
        "G-0126 inactive direction mutation",
        "G-0127 row truncation",
        "G-0127 record order mutation",
        "G-0127 extrema mutation",
        "G-0127 nonzero census mutation",
        "G-0127 row digest mutation",
        "G-0127 exact residual mutation",
        "G-0127 binding mutation",
        "stale source",
        "stale preregistration",
        "stale prior result",
        "stale future receipt",
        "path escape",
        "ragged 380-row matrix",
        "duplicate manifest input",
        "noncanonical coefficient",
        "output overwrite",
        "serialization abort",
    }
    require(set(rejected_controls) == required_controls, "G-0128 hostile control census drift")
    print(
        "g0128-full-family-master-self-test: PASS "
        f"(ancestor 15 + {len(rejected_controls)} G-0128 hostile mutations rejected)"
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--build-manifest", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    modes = int(args.self_test) + int(args.build_manifest) + int(args.output is not None)
    require(modes == 1, "choose exactly one mode")
    if args.self_test:
        require(args.manifest is None, "self-test takes no manifest")
        self_test()
        return 0
    if args.build_manifest:
        require(args.manifest is None and args.output is None, "manifest builder takes no paths")
        value = build_manifest(MANIFEST_PATH)
        print(
            json.dumps(
                {"result": value["result"], "rows": value["rows"], "wall_seconds": value["wall_seconds"]},
                sort_keys=True,
            )
        )
        return 0
    require(args.manifest is not None and args.output is not None, "run requires --manifest and --output")
    value = run(args.manifest, args.output)
    print(
        json.dumps(
            {"result": value["result"], "trials": value["trials"], "wall_seconds": value["wall_seconds"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
