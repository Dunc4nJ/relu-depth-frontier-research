#!/usr/bin/env python3
"""Manifest builder and exact-Q all-column master for the G-0121 protocol."""

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
MANIFEST_PATH = ROOT / "artifacts/math/G-0121/full_family_master_manifest_v1.json"
RESULT_PATH = ROOT / "artifacts/math/G-0121/full_family_master_result_v1.json"
PREREGISTRATION = ROOT / "artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md"
HELPER_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"
CACHE_PATH = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"
CACHE_MANIFEST_PATH = ROOT / "artifacts/math/G-0117/full_family_cache_manifest_v1.json"
PANEL_INPUT_PATH = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
PANEL_SCAN_PATH = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
REPLAY_PATH = ROOT / "artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json"
PRICE_PATH = ROOT / "artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json"
CANDIDATE_PATH = ROOT / "artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json"

N = 11
PANEL_ROWS = 301
LINEAR_ROWS = 11
ACCUMULATED_ROWS = 4
BATCH_ROWS = 32
ROWS = PANEL_ROWS + LINEAR_ROWS + ACCUMULATED_ROWS + BATCH_ROWS
RECORDS = 163_740
I128_BYTES = 16
COLUMN_BYTES = PANEL_ROWS * I128_BYTES
CACHE_BYTES = RECORDS * COLUMN_BYTES
PRIMES = [1_000_000_007, 1_000_000_009]
MAX_RANK_INCREASES = ROWS - 115

COORDINATES: list[tuple[Path, list[int]]] = [
    (
        ROOT / "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
    ),
    (
        ROOT / "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
    ),
    (
        ROOT / "artifacts/math/G-0118/iteration3_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -3, 2],
    ),
    (
        ROOT / "artifacts/math/G-0118/iteration4_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
    ),
]

EXPECTED_INPUTS: dict[str, str] = {
    "artifacts/math/G-0111/dual_rows_v1.json": "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c",
    "artifacts/math/G-0113/panel_retained_columns_v1.json": "615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393",
    "artifacts/math/G-0113/panel_scan_v1.json": "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e",
    "artifacts/math/G-0113/panel_solver_input_v1.json": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    "artifacts/math/G-0117/FULL_FAMILY_CEGIS_PREREGISTRATION.md": "ac6cecfe4702866d8177dbeefd81b71a3933578a6f88b1f9cbcbc12f0cfb1022",
    "artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md": "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17",
    "artifacts/math/G-0117/fresh_q_cegis_exact.py": "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281",
    "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json": "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071",
    "artifacts/math/G-0117/full_family_cache_manifest_v1.json": "e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf",
    "artifacts/math/G-0117/full_family_cache_v1.i128le": "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b",
    "artifacts/math/G-0117/src/bin/full_family_cache.rs": "99ecda05de53f261ad4aa2d9a8c0e746bab1f51c35044dd9778edcc961c89435",
    "artifacts/math/G-0117/src/bin/g0118_batch_coordinate_pricer.rs": "35cabc07a3e6a50366c584c737493b393b202092d64f0951a37dde4f515d3058",
    "artifacts/math/G-0117/src/bin/g0118_batch_modular_replay.rs": "172be64103b9ebf7516514923c94bc7de8ee63bfc92a776e321c87c469a58db9",
    "artifacts/math/G-0117/src/lib.rs": "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6",
    "artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json": "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310",
    "artifacts/math/G-0116/src/main.rs": "875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd",
    "artifacts/math/G-0113/src/main.rs": "8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f",
    "artifacts/math/G-0118/BATCH32_ITERATION4_PREREGISTRATION.md": "54a329587786c8824e8eede13a6165983ecc64c27a7f758be9676583bd283feb",
    "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json": "41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f",
    "artifacts/math/G-0118/iteration3_residual_coordinate_v1.json": "58139181228fc2400298f400f1b80c083b72747f8d1ba3830fe4f3ee8b787f48",
    "artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json": "349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b",
    "artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json": "c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80",
    "artifacts/math/G-0118/iteration4_residual_coordinate_v1.json": "862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb",
    "artifacts/math/G-0118/prefix_exact_cegis_iteration4_recheck_v1.json": "f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f",
    "artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json": "728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b",
    "artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md": "e7e2f6de986d839aef8614ae81d91357b34bccfb5b9ec065fd8aa5bd1a689952",
}

CACHE_BINDINGS: dict[str, str] = {
    "completed_scan": EXPECTED_INPUTS["artifacts/math/G-0113/panel_scan_v1.json"],
    "corrected_scan_producer": EXPECTED_INPUTS["artifacts/math/G-0113/src/main.rs"],
    "evaluator": EXPECTED_INPUTS["artifacts/math/G-0116/src/main.rs"],
    "evaluator_gate": EXPECTED_INPUTS["artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json"],
    "input": EXPECTED_INPUTS["artifacts/math/G-0113/panel_solver_input_v1.json"],
    "preregistration": EXPECTED_INPUTS["artifacts/math/G-0117/FULL_FAMILY_CEGIS_PREREGISTRATION.md"],
    "producer": EXPECTED_INPUTS["artifacts/math/G-0117/src/bin/full_family_cache.rs"],
    "rows": EXPECTED_INPUTS["artifacts/math/G-0111/dual_rows_v1.json"],
}

REPLAY_BINDINGS: dict[str, str] = {
    "candidate": EXPECTED_INPUTS["artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json"],
    "candidate_recheck": EXPECTED_INPUTS["artifacts/math/G-0118/prefix_exact_cegis_iteration4_recheck_v1.json"],
    "kernel": EXPECTED_INPUTS["artifacts/math/G-0117/src/lib.rs"],
    "normal_form_uniqueness": EXPECTED_INPUTS["artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md"],
    "panel_input": EXPECTED_INPUTS["artifacts/math/G-0113/panel_solver_input_v1.json"],
    "preregistration": EXPECTED_INPUTS["artifacts/math/G-0118/BATCH32_ITERATION4_PREREGISTRATION.md"],
    "producer": EXPECTED_INPUTS["artifacts/math/G-0117/src/bin/g0118_batch_modular_replay.rs"],
}

PRICE_BINDINGS: dict[str, str] = {
    "candidate": REPLAY_BINDINGS["candidate"],
    "candidate_recheck": REPLAY_BINDINGS["candidate_recheck"],
    "kernel": REPLAY_BINDINGS["kernel"],
    "normal_form_uniqueness": REPLAY_BINDINGS["normal_form_uniqueness"],
    "panel_input": REPLAY_BINDINGS["panel_input"],
    "preregistration": REPLAY_BINDINGS["preregistration"],
    "producer": EXPECTED_INPUTS["artifacts/math/G-0117/src/bin/g0118_batch_coordinate_pricer.rs"],
    "replay_producer": REPLAY_BINDINGS["producer"],
    "replay_receipt": EXPECTED_INPUTS["artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json"],
}


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


def validate_bindings(
    observed: object,
    expected: dict[str, str],
    *,
    unhashed_executable: bool = False,
) -> None:
    require(isinstance(observed, dict), "bindings object required")
    allowed = set(expected)
    if unhashed_executable:
        allowed.add("executable")
    require(set(observed) == allowed, "binding key set drift")
    for name, digest in expected.items():
        require(observed.get(name) == digest, f"binding drift: {name}")
    if unhashed_executable:
        require(is_sha256(observed.get("executable")), "malformed executable binding")


def validate_cache_size(size: int) -> None:
    require(size == CACHE_BYTES, "cache byte-size drift")


def validate_cache_receipt_documents(
    manifest: dict[str, Any],
    source: dict[str, Any],
    scan: dict[str, Any],
) -> None:
    require(
        manifest.get("schema") == "max11-g0117-full-family-panel-cache-v1"
        and manifest.get("result") == "EXACT_PANEL_CACHE_REPRODUCED",
        "cache manifest identity drift",
    )
    require(
        manifest.get("claim_boundary")
        == "Exact sequence-major cache of the frozen 301-row finite panel over 163,740 columns; not a global identity, Q membership decision, family-completeness theorem, or MAX11 result.",
        "cache claim boundary drift",
    )
    require(
        int(manifest.get("records")) == RECORDS
        and int(manifest.get("rows")) == PANEL_ROWS
        and int(manifest.get("entry_bytes")) == I128_BYTES
        and int(manifest.get("payload_bytes")) == CACHE_BYTES
        and manifest.get("layout") == "sequence-major: offset=((sequence*301)+row)*16"
        and manifest.get("integer_width") == "signed i128"
        and manifest.get("endianness") == "little",
        "cache layout drift",
    )
    require(
        manifest.get("data_sha256") == EXPECTED_INPUTS[relative(CACHE_PATH)]
        and is_sha256(manifest.get("ordered_vector_digests_sha256")),
        "cache data binding drift",
    )
    validate_bindings(manifest.get("bindings"), CACHE_BINDINGS, unhashed_executable=True)

    require(
        source.get("schema") == "max11-g0113-panel-solver-input-v1"
        and source.get("rows_path") == "artifacts/math/G-0111/dual_rows_v1.json"
        and isinstance(source.get("target"), list)
        and len(source["target"]) == PANEL_ROWS,
        "panel input identity drift",
    )
    records = source.get("records")
    require(
        isinstance(records, list)
        and len(records) == RECORDS
        and all(int(record.get("sequence", -1)) == index for index, record in enumerate(records)),
        "panel record order drift",
    )

    require(
        scan.get("schema") == "max11-g0113-panel-scan-v1"
        and scan.get("result") == "MODULAR_MEMBER_PENDING_EXACT_Q"
        and int(scan.get("records")) == RECORDS,
        "panel scan identity drift",
    )
    require(
        scan.get("bindings", {}).get("input") == CACHE_BINDINGS["input"]
        and scan.get("bindings", {}).get("rows") == CACHE_BINDINGS["rows"]
        and scan.get("bindings", {}).get("evaluator") == CACHE_BINDINGS["evaluator"]
        and scan.get("bindings", {}).get("evaluator_report") == CACHE_BINDINGS["evaluator_gate"]
        and scan.get("bindings", {}).get("producer") == CACHE_BINDINGS["corrected_scan_producer"],
        "panel scan transitive binding drift",
    )
    require(
        scan.get("all_vectors_i128_le_sha256") == manifest.get("data_sha256")
        and scan.get("ordered_vector_digests_sha256") == manifest.get("ordered_vector_digests_sha256")
        and int(scan.get("value_minimum")) == int(manifest.get("value_minimum"))
        and int(scan.get("value_maximum")) == int(manifest.get("value_maximum")),
        "cache/scan semantic bridge drift",
    )


def validate_cache_receipt() -> None:
    validate_cache_receipt_documents(
        load_json(CACHE_MANIFEST_PATH),
        load_json(PANEL_INPUT_PATH),
        load_json(PANEL_SCAN_PATH),
    )


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require_digest(actual: str, expected: str, label: str) -> None:
    require(is_sha256(actual) and is_sha256(expected) and actual == expected, f"{label} hash drift")


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


def contained(path: Path) -> Path:
    result = path.resolve()
    try:
        result.relative_to(ROOT)
    except ValueError as error:
        raise MasterError(f"path escapes workspace: {path}") from error
    return result


def relative(path: Path) -> str:
    return contained(path).relative_to(ROOT).as_posix()


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


def validate_expected_inputs() -> dict[str, str]:
    observed: dict[str, str] = {}
    resolved_paths: set[Path] = set()
    for name, expected in EXPECTED_INPUTS.items():
        require(is_sha256(expected), f"malformed expected SHA-256: {name}")
        path = contained(ROOT / name)
        require(path.is_file(), f"missing input: {name}")
        require(path not in resolved_paths, f"duplicate resolved input: {name}")
        resolved_paths.add(path)
        actual = sha256_path(path)
        require_digest(actual, expected, f"input {name}")
        observed[name] = actual
    validate_cache_size(CACHE_PATH.stat().st_size)
    return observed


def canonical_terms(candidate: dict[str, Any]) -> list[tuple[int, int]]:
    require(
        candidate.get("schema") == "max11-g0118-prefix-exact-cegis-accumulated-v1"
        and candidate.get("result") == "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS"
        and int(candidate.get("iteration")) == 4
        and int(candidate.get("prefix_records")) == 40_000
        and int(candidate.get("family_sequences")) == 40_003
        and candidate.get("hinge_directions") == [direction for _, direction in COORDINATES]
        and candidate.get("all_rows_replayed") is True
        and candidate.get("coefficient_plus_one_mutant_rejected") is True,
        "candidate identity drift",
    )
    require(
        isinstance(candidate.get("target_scale"), str)
        and str(int(candidate["target_scale"])) == candidate["target_scale"]
        and int(candidate["target_scale"]) > 0,
        "candidate target scale drift",
    )
    raw_terms = candidate.get("terms")
    require(isinstance(raw_terms, list), "candidate terms missing")
    require(
        all(
            isinstance(item, dict)
            and isinstance(item.get("sequence"), int)
            and isinstance(item.get("coefficient"), str)
            and str(int(item["coefficient"])) == item["coefficient"]
            for item in raw_terms
        ),
        "noncanonical candidate term",
    )
    terms = [(item["sequence"], int(item["coefficient"])) for item in raw_terms]
    require(len(terms) == 102, "candidate term census drift")
    require(len({sequence for sequence, _ in terms}) == len(terms), "duplicate candidate sequence")
    require(terms == sorted(terms) and all(0 <= sequence < RECORDS and coefficient for sequence, coefficient in terms), "invalid term")
    return terms


def validate_selected_records(
    selected: object,
    expected_count: int,
    expected_digest: str,
) -> list[dict[str, Any]]:
    require(isinstance(selected, list) and len(selected) == expected_count, "selected batch census drift")
    require(all(isinstance(item, dict) and set(item) == {"direction", "residues"} for item in selected), "selected record shape drift")
    directions = [item["direction"] for item in selected]
    require(
        directions == sorted(directions)
        and len({tuple(value) for value in directions}) == expected_count
        and all(
            isinstance(direction, list)
            and len(direction) == N
            and all(isinstance(value, int) and -128 <= value <= 127 for value in direction)
            for direction in directions
        ),
        "selected order drift",
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


def validate_price_row(
    row: object,
    selected_item: dict[str, Any],
    index: int,
    expected_records: int,
) -> tuple[list[int], bytes]:
    require(isinstance(row, dict), f"hinge row {index} object required")
    coefficients_raw = row.get("hinge_coefficients")
    require(
        isinstance(coefficients_raw, list)
        and len(coefficients_raw) == expected_records
        and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in coefficients_raw),
        f"hinge row {index} length/type drift",
    )
    coefficients = [int(value) for value in coefficients_raw]
    require(
        row.get("direction") == selected_item["direction"]
        and row.get("modular_residues") == selected_item["residues"],
        "price row identity drift",
    )
    require(
        int(row.get("nonzero_hinge_coefficients")) == sum(value != 0 for value in coefficients)
        and int(row.get("maximum_hinge_coefficient")) == max(coefficients),
        f"hinge row {index} census drift",
    )
    encoded = b"".join(value.to_bytes(8, "little", signed=True) for value in coefficients)
    require(
        is_sha256(row.get("hinge_coefficients_i64_le_sha256"))
        and hashlib.sha256(encoded).hexdigest() == row["hinge_coefficients_i64_le_sha256"],
        f"row {index} digest drift",
    )
    return coefficients, encoded


def validate_batch_receipts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], list[int]]:
    candidate = load_json(CANDIDATE_PATH)
    replay = load_json(REPLAY_PATH)
    price = load_json(PRICE_PATH)
    terms = canonical_terms(candidate)
    require(
        replay.get("schema") == "max11-g0118-batch32-global-modular-replay-v1"
        and replay.get("result") == "BATCH_RESIDUAL_PREFIX_SELECTED"
        and replay.get("complete_global_replay") is True,
        "global replay identity drift",
    )
    validate_bindings(replay.get("bindings"), REPLAY_BINDINGS, unhashed_executable=True)
    require(
        replay.get("candidate_schema") == candidate.get("schema")
        and replay.get("candidate_result") == candidate.get("result")
        and replay.get("target_scale") == candidate.get("target_scale"),
        "candidate/replay semantic bridge drift",
    )
    require(replay.get("primes") == PRIMES and int(replay.get("batch_k")) == BATCH_ROWS, "replay protocol drift")
    require(int(replay.get("terms")) == 102, "replay term census drift")
    require(int(replay.get("labelled_permutations_checked")) == 102 * math.factorial(N), "permutation census drift")
    require(
        int(replay.get("hinge_entries_processed")) == 3_585_323
        and int(replay.get("aggregate_hinge_support")) == 172_454
        and int(replay.get("nonzero_hinge_residue_directions")) == 172_430
        and replay.get("all_hinge_and_linear_residues_zero") == [False, False],
        "complete replay census drift",
    )
    checks = replay.get("accumulated_row_checks")
    require(isinstance(checks, list) and len(checks) == ACCUMULATED_ROWS, "accumulated check census drift")
    for check, (_, direction) in zip(checks, COORDINATES, strict=True):
        require(check["direction"] == direction and check["residues"] == [0, 0] and check["zero_in_both_fields"] is True, "accumulated replay drift")
    require(replay.get("linear_residues_after_target") == [[0] * N, [0] * N], "linear replay drift")
    require(replay.get("coefficient_plus_one_mutant", {}).get("rejected") is True, "replay mutant failed")
    selected = validate_selected_records(
        replay.get("selected"),
        BATCH_ROWS,
        replay.get("selected_prefix_i8_u64_le_sha256"),
    )
    require(int(replay.get("selected_count")) == len(selected), "selected count label drift")
    directions = [item["direction"] for item in selected]

    require(
        price.get("schema") == "max11-g0118-batch32-coordinate-price-v1"
        and price.get("result") == "EXACT_BATCH_COORDINATE_PRICES",
        "price identity drift",
    )
    validate_bindings(price.get("bindings"), PRICE_BINDINGS, unhashed_executable=True)
    require(
        int(price.get("batch_k")) == BATCH_ROWS
        and int(price.get("records")) == RECORDS
        and int(price.get("selected_count")) == BATCH_ROWS,
        "price dimensions drift",
    )
    require(price.get("directions") == directions, "price direction order drift")
    residues = [item["residues"] for item in selected]
    require(price.get("modular_residues") == residues, "price residues drift")
    rows = price.get("rows")
    linear = price.get("linear_vectors")
    require(isinstance(rows, list) and len(rows) == BATCH_ROWS, "price row census drift")
    require(isinstance(linear, list) and len(linear) == RECORDS, "linear census drift")
    require(
        all(
            isinstance(row, list)
            and len(row) == N
            and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in row)
            for row in linear
        ),
        "ragged or non-i64 linear vectors",
    )
    aggregate_hinge = hashlib.sha256()
    exact_residuals: list[int] = []
    for index, (row, selected_item) in enumerate(zip(rows, selected, strict=True)):
        coefficients, encoded = validate_price_row(row, selected_item, index, RECORDS)
        aggregate_hinge.update(encoded)
        exact = sum(coefficient * coefficients[sequence] for sequence, coefficient in terms)
        require([exact % prime for prime in PRIMES] == selected_item["residues"], f"row {index} modular bridge drift")
        require(exact != 0, f"selected row {index} exact residual vanished")
        exact_residuals.append(exact)
    require(aggregate_hinge.hexdigest() == price.get("direction_major_hinge_i64_le_sha256"), "aggregate hinge digest drift")
    require(digest_i64(value for row in linear for value in row) == price.get("linear_vectors_i64_le_sha256"), "linear digest drift")
    linear_value = [sum(coefficient * int(linear[sequence][rank]) for sequence, coefficient in terms) for rank in range(N)]
    linear_value[-1] -= math.factorial(N) * int(candidate["target_scale"])
    require(linear_value == [0] * N, "exact linear bridge drift")
    return candidate, replay, price, exact_residuals


def load_accumulated(price_linear: list[list[int]], terms: list[tuple[int, int]]) -> list[list[int]]:
    hinge_rows: list[list[int]] = []
    reference_linear_digest = digest_i64(value for row in price_linear for value in row)
    for path, direction in COORDINATES:
        document = load_json(path)
        require(
            document.get("schema") == "max11-g0117-coordinate-price-v1"
            and document.get("result") == "EXACT_COORDINATE_PRICES"
            and int(document["records"]) == RECORDS
            and document["direction"] == direction,
            "coordinate identity drift",
        )
        require(
            document.get("bindings", {}).get("panel_input") == EXPECTED_INPUTS[relative(PANEL_INPUT_PATH)],
            "coordinate panel binding drift",
        )
        hinge = [int(value) for value in document["hinge_coefficients"]]
        require(
            len(hinge) == RECORDS
            and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in document["hinge_coefficients"]),
            "coordinate hinge length/type drift",
        )
        require(
            int(document.get("nonzero_hinge_coefficients")) == sum(value != 0 for value in hinge)
            and int(document.get("maximum_hinge_coefficient")) == max(hinge)
            and digest_i64(hinge) == document["hinge_coefficients_i64_le_sha256"],
            "coordinate hinge census/digest drift",
        )
        linear = document["linear_vectors"]
        require(
            len(linear) == RECORDS
            and all(
                isinstance(row, list)
                and len(row) == N
                and all(isinstance(value, int) and -(1 << 63) <= value < (1 << 63) for value in row)
                for row in linear
            ),
            "coordinate linear shape drift",
        )
        require(
            document.get("linear_vectors_i64_le_sha256") == reference_linear_digest
            and digest_i64(value for row in linear for value in row) == reference_linear_digest,
            "coordinate linear stream drift",
        )
        require(sum(coefficient * hinge[sequence] for sequence, coefficient in terms) == 0, "candidate accumulated exact residual drift")
        hinge_rows.append(hinge)
    return hinge_rows


def build_manifest(output: Path) -> dict[str, Any]:
    begun = time.perf_counter()
    output = contained(output)
    require(output == MANIFEST_PATH, "manifest output path drift")
    require(not output.exists(), "refusing to overwrite manifest")
    inputs = validate_expected_inputs()
    validate_cache_receipt()
    candidate, replay, price, exact_residuals = validate_batch_receipts()
    terms = canonical_terms(candidate)
    accumulated = load_accumulated(price["linear_vectors"], terms)
    require(len(accumulated) == ACCUMULATED_ROWS, "accumulated row census drift")
    seed = load_panel_seed()
    script_sha256 = sha256_path(SCRIPT)
    result: dict[str, Any] = {
        "schema": "max11-g0121-full-family-master-manifest-v1",
        "result": "BOUND_INPUTS_VALIDATED",
        "claim_boundary": "Inputs for an exact 348-row rational decision over the frozen 163,740-column family; not a global identity, family-completeness theorem, or unrestricted MAX11 result.",
        "solver": {"path": relative(SCRIPT), "sha256": script_sha256},
        "preregistration": {"path": relative(PREREGISTRATION), "sha256": EXPECTED_INPUTS[relative(PREREGISTRATION)]},
        "expected_inputs": [{"path": name, "sha256": digest} for name, digest in sorted(inputs.items())],
        "records": RECORDS,
        "panel_rows": PANEL_ROWS,
        "linear_rows": LINEAR_ROWS,
        "accumulated_rows": ACCUMULATED_ROWS,
        "batch_rows": BATCH_ROWS,
        "batch_row_policy": "All 32 frozen Batch32 rows retained in receipt order; no dependency discard attempted.",
        "batch_row_decisions": [
            {"receipt_index": index, "direction": item["direction"], "decision": "KEPT_CONSERVATIVELY"}
            for index, item in enumerate(replay["selected"])
        ],
        "discarded_batch_rows": [],
        "row_dependency_pivot_enrichment_columns": [],
        "rows": ROWS,
        "seed_sequences": seed,
        "max_rank_increases": MAX_RANK_INCREASES,
        "candidate_terms": len(terms),
        "exact_batch_residuals_decimal_lf_sha256": hashlib.sha256(("\n".join(str(value) for value in exact_residuals) + "\n").encode()).hexdigest(),
        "complete_arithmetic_bridge": True,
        "wall_seconds": time.perf_counter() - begun,
    }
    require_digest(sha256_path(SCRIPT), script_sha256, "solver during manifest build")
    validate_expected_inputs()
    write_exclusive(output, result)
    return result


def load_panel_seed() -> list[int]:
    scan = load_json(PANEL_SCAN_PATH)
    primes = scan.get("primes")
    require(isinstance(primes, list) and len(primes) == len(PRIMES), "panel prime census drift")
    require([int(item.get("prime")) for item in primes] == PRIMES, "panel prime order drift")
    bases = [item.get("selected_sequences") for item in primes]
    require(all(isinstance(base, list) for base in bases), "panel bases missing")
    seed = [int(value) for value in bases[0]]
    require(seed == [int(value) for value in bases[1]], "panel bases differ")
    require(
        len(seed) == len(set(seed)) == 115
        and seed == sorted(seed)
        and all(isinstance(value, int) and 0 <= value < RECORDS for value in bases[0] + bases[1]),
        "panel seed drift",
    )
    return seed


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


def validate_master_manifest(
    manifest: dict[str, Any],
    script_sha256: str,
    expected_seed: list[int],
    expected_residual_digest: str,
    expected_batch_directions: list[list[int]],
) -> None:
    require(
        manifest.get("schema") == "max11-g0121-full-family-master-manifest-v1"
        and manifest.get("result") == "BOUND_INPUTS_VALIDATED"
        and manifest.get("claim_boundary")
        == "Inputs for an exact 348-row rational decision over the frozen 163,740-column family; not a global identity, family-completeness theorem, or unrestricted MAX11 result.",
        "manifest identity drift",
    )
    require(
        manifest.get("solver") == {"path": relative(SCRIPT), "sha256": script_sha256}
        and manifest.get("preregistration")
        == {"path": relative(PREREGISTRATION), "sha256": EXPECTED_INPUTS[relative(PREREGISTRATION)]},
        "manifest source/preregistration binding drift",
    )
    validate_manifest_input_records(manifest.get("expected_inputs"), EXPECTED_INPUTS)
    require(
        int(manifest.get("records")) == RECORDS
        and int(manifest.get("panel_rows")) == PANEL_ROWS
        and int(manifest.get("linear_rows")) == LINEAR_ROWS
        and int(manifest.get("accumulated_rows")) == ACCUMULATED_ROWS
        and int(manifest.get("batch_rows")) == BATCH_ROWS
        and int(manifest.get("rows")) == ROWS
        and int(manifest.get("max_rank_increases")) == MAX_RANK_INCREASES
        and int(manifest.get("candidate_terms")) == 102
        and manifest.get("complete_arithmetic_bridge") is True,
        "manifest dimension/protocol drift",
    )
    decisions = manifest.get("batch_row_decisions")
    require(
        manifest.get("batch_row_policy")
        == "All 32 frozen Batch32 rows retained in receipt order; no dependency discard attempted."
        and isinstance(decisions, list)
        and len(decisions) == BATCH_ROWS
        and [int(item.get("receipt_index", -1)) for item in decisions] == list(range(BATCH_ROWS))
        and all(item.get("decision") == "KEPT_CONSERVATIVELY" for item in decisions)
        and [item.get("direction") for item in decisions] == expected_batch_directions
        and manifest.get("discarded_batch_rows") == []
        and manifest.get("row_dependency_pivot_enrichment_columns") == [],
        "manifest Batch32 row policy drift",
    )
    seed = manifest.get("seed_sequences")
    require(
        isinstance(seed, list)
        and len(seed) == len(set(seed)) == 115
        and seed == sorted(seed)
        and all(isinstance(value, int) and 0 <= value < RECORDS for value in seed)
        and seed == expected_seed,
        "manifest seed drift",
    )
    require(
        is_sha256(manifest.get("exact_batch_residuals_decimal_lf_sha256"))
        and manifest.get("exact_batch_residuals_decimal_lf_sha256") == expected_residual_digest,
        "manifest residual digest drift",
    )


def panel_column(cache: mmap.mmap, sequence: int) -> list[int]:
    require(0 <= sequence < RECORDS, "sequence outside family")
    offset = sequence * COLUMN_BYTES
    return [
        int.from_bytes(cache[offset + I128_BYTES * row : offset + I128_BYTES * (row + 1)], "little", signed=True)
        for row in range(PANEL_ROWS)
    ]


def full_column(
    cache: mmap.mmap,
    sequence: int,
    linear: Sequence[Sequence[int]],
    accumulated: Sequence[Sequence[int]],
    batch: Sequence[Sequence[int]],
) -> list[int]:
    result = panel_column(cache, sequence)
    result.extend(int(value) for value in linear[sequence])
    result.extend(int(row[sequence]) for row in accumulated)
    result.extend(int(row[sequence]) for row in batch)
    require(len(result) == ROWS, "column dimension drift")
    return result


def matrix_rows(columns: Sequence[Sequence[int]]) -> list[list[int]]:
    require(columns and all(len(column) == ROWS for column in columns), "ragged columns")
    return [[int(column[row]) for column in columns] for row in range(ROWS)]


def first_violation(
    cache: mmap.mmap,
    separator: Sequence[int],
    linear: Sequence[Sequence[int]],
    accumulated: Sequence[Sequence[int]],
    batch: Sequence[Sequence[int]],
) -> tuple[int, int, int] | None:
    return scan_first_violation(
        separator,
        RECORDS,
        lambda sequence: full_column(cache, sequence, linear, accumulated, batch),
    )


def scan_first_violation(
    separator: Sequence[int],
    record_count: int,
    column_loader,
) -> tuple[int, int, int] | None:
    require(record_count >= 0 and separator, "invalid separator scan dimensions")
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    require(nonzero, "zero separator")
    for sequence in range(record_count):
        column = column_loader(sequence)
        require(len(column) == len(separator), "separator/column dimension drift")
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price, sequence + 1
    return None


def normalize_member(values: Sequence[Fraction]) -> tuple[list[int], int]:
    scale = math.lcm(*(value.denominator for value in values))
    integers = [int(value * scale) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "member normalization gcd vanished")
    scale //= divisor
    integers = [value // divisor for value in integers]
    require(scale > 0 and math.gcd(scale, math.gcd(*[abs(value) for value in integers])) == 1, "member not primitive")
    return integers, scale


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
    require(
        manifest.get("solver") == {"path": relative(SCRIPT), "sha256": script_sha256},
        "solver binding drift",
    )
    validate_expected_inputs()
    validate_cache_receipt()
    candidate, replay, price, exact_residuals = validate_batch_receipts()
    seed = load_panel_seed()
    residual_digest = hashlib.sha256(
        ("\n".join(str(value) for value in exact_residuals) + "\n").encode()
    ).hexdigest()
    validate_master_manifest(
        manifest,
        script_sha256,
        seed,
        residual_digest,
        [item["direction"] for item in replay["selected"]],
    )
    terms = canonical_terms(candidate)
    accumulated = load_accumulated(price["linear_vectors"], terms)
    linear = [[int(value) for value in row] for row in price["linear_vectors"]]
    batch = [[int(value) for value in row["hinge_coefficients"]] for row in price["rows"]]
    source = load_json(PANEL_INPUT_PATH)
    target = [int(value) for value in source["target"]] + [0] * (LINEAR_ROWS + ACCUMULATED_ROWS + BATCH_ROWS)
    target[PANEL_ROWS + N - 1] = math.factorial(N)
    require(len(target) == ROWS, "target dimension drift")
    helper = load_module(HELPER_PATH, "g0123_full_family_master_helper")
    rhs = helper.qmatrix([[value] for value in target])
    selected = [int(value) for value in manifest["seed_sequences"]]
    require(len(selected) == len(set(selected)) == 115 and selected == sorted(selected), "seed drift")
    trials: list[dict[str, Any]] = []
    previous_rank = -1

    with CACHE_PATH.open("rb") as cache_file, mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache:
        require(len(cache) == CACHE_BYTES, "cache mmap size drift")
        for iteration in range(int(manifest["max_rank_increases"]) + 1):
            require(selected == sorted(set(selected)), "selected column order drift")
            columns = [full_column(cache, sequence, linear, accumulated, batch) for sequence in selected]
            integer_rows = matrix_rows(columns)
            matrix = helper.qmatrix(integer_rows)
            augmented = helper.qmatrix([row + [target[index]] for index, row in enumerate(integer_rows)])
            rank = int(matrix.rank())
            augmented_rank = int(augmented.rank())
            require(rank > previous_rank, "appended column failed exact rank increase")
            previous_rank = rank
            if rank == augmented_rank:
                reduced, reduced_rank = matrix.rref()
                require(int(reduced_rank) == rank, "member RREF rank drift")
                pivot_indices = helper.pivot_columns(reduced, rank, len(selected))
                support_sequences = [selected[index] for index in pivot_indices]
                support_columns = [columns[index] for index in pivot_indices]
                basis_rows = matrix_rows(support_columns)
                basis = helper.qmatrix(basis_rows)
                transposed, transposed_rank = basis.transpose().rref()
                require(int(transposed_rank) == rank, "basis rank drift")
                coordinate_rows = helper.pivot_columns(transposed, rank, ROWS)
                square = helper.qmatrix([[basis_rows[row][column] for column in range(rank)] for row in coordinate_rows])
                rational = square.solve(helper.qmatrix([[target[row]] for row in coordinate_rows]))
                require(basis * rational == rhs, "all-row rational replay failed")
                fractions = [Fraction(str(rational[index, 0])) for index in range(rank)]
                integers, scale = normalize_member(fractions)
                require(
                    all(sum(integers[column] * basis_rows[row][column] for column in range(rank)) == scale * target[row] for row in range(ROWS)),
                    "denominator-cleared all-row replay failed",
                )
                first_nonzero = next(index for index, value in enumerate(integers) if value)
                mutant = integers[:]
                mutant[first_nonzero] += 1
                mutant_rejected = any(
                    sum(mutant[column] * basis_rows[row][column] for column in range(rank)) != scale * target[row]
                    for row in range(ROWS)
                )
                require(mutant_rejected, "member coefficient mutant escaped")
                trials.append({"iteration": iteration, "rank": rank, "augmented_rank": augmented_rank, "result": "EXACT_Q_MEMBER"})
                result: dict[str, Any] = {
                    "schema": "max11-g0121-full-family-master-result-v1",
                    "result": "FULL_FAMILY_EXACT_Q_MEMBER",
                    "claim_boundary": "Exact membership only on the frozen 348-row system over the frozen 163,740-column family; a finite-row candidate for separate complete global replay, not a family-completeness theorem or MAX11 result.",
                    "manifest_path": relative(manifest_path),
                    "manifest_sha256": manifest_sha256,
                    "solver_sha256": script_sha256,
                    "records": RECORDS,
                    "rows": ROWS,
                    "hinge_directions": [direction for _, direction in COORDINATES] + price["directions"],
                    "selected_sequences": selected,
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_i128le_sha256": digest_i128(basis_rows[row][column] for row in range(ROWS) for column in range(rank)),
                    "target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "terms": [
                        {"sequence": sequence, "coefficient": str(coefficient)}
                        for sequence, coefficient in zip(support_sequences, integers, strict=True)
                        if coefficient
                    ],
                    "all_rows_replayed": True,
                    "coefficient_plus_one_mutant_rejected": mutant_rejected,
                    "batch_exact_residuals_decimal_lf_sha256": hashlib.sha256(("\n".join(str(value) for value in exact_residuals) + "\n").encode()).hexdigest(),
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require_digest(sha256_path(SCRIPT), script_sha256, "solver during run")
                require_digest(sha256_path(manifest_path), manifest_sha256, "manifest during run")
                validate_expected_inputs()
                write_exclusive(output, result)
                return result

            separator, pairing, free_row = helper.first_target_separator(matrix, integer_rows, target)
            violation = first_violation(cache, separator, linear, accumulated, batch)
            trial = {
                "iteration": iteration,
                "rank": rank,
                "augmented_rank": augmented_rank,
                "separator_target_pairing": str(pairing),
                "separator_free_row": free_row,
                "first_violating_sequence": None if violation is None else violation[0],
                "first_violating_price": None if violation is None else str(violation[1]),
                "columns_scanned": RECORDS if violation is None else violation[2],
                "result": "FULL_FAMILY_EXACT_Q_NONMEMBER" if violation is None else "SEPARATOR_VIOLATED",
            }
            trials.append(trial)
            if violation is None:
                first_nonzero = next(index for index, value in enumerate(separator) if value)
                mutant = separator[:]
                mutant[first_nonzero] += 1
                mutant_violation = first_violation(cache, mutant, linear, accumulated, batch)
                mutant_pairing = sum(value * rhs_value for value, rhs_value in zip(mutant, target, strict=True))
                mutant_rejected = mutant_violation is not None or mutant_pairing == 0
                require(mutant_rejected, "separator mutant escaped")
                result = {
                    "schema": "max11-g0121-full-family-master-result-v1",
                    "result": "FULL_FAMILY_EXACT_Q_NONMEMBER",
                    "claim_boundary": "Exact nonmembership only in the frozen 163,740-column family on the frozen 348 rows; not a family-completeness theorem or unrestricted MAX11 lower bound.",
                    "manifest_path": relative(manifest_path),
                    "manifest_sha256": manifest_sha256,
                    "solver_sha256": script_sha256,
                    "records": RECORDS,
                    "rows": ROWS,
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_family_columns_exactly_annihilated": True,
                    "complete_separator_scan": RECORDS,
                    "separator_plus_one_mutant_rejected": mutant_rejected,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require_digest(sha256_path(SCRIPT), script_sha256, "solver during run")
                require_digest(sha256_path(manifest_path), manifest_sha256, "manifest during run")
                validate_expected_inputs()
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

    helper = load_module(HELPER_PATH, "g0123_full_family_master_selftest")
    member = helper.qmatrix([[1, 0], [0, 1], [1, 1]])
    solution = helper.qmatrix([[1, 0], [0, 1]]).solve(helper.qmatrix([[2], [3]]))
    require(member * solution == helper.qmatrix([[2], [3], [5]]), "member control failed")
    member_coefficients = [2, 3]
    member_mutant = member_coefficients[:]
    member_mutant[0] += 1
    require(
        any(
            sum(member_mutant[column] * [[1, 0], [0, 1], [1, 1]][row][column] for column in range(2))
            != [2, 3, 5][row]
            for row in range(3)
        ),
        "member +1 mutant escaped",
    )

    nonmember = helper.qmatrix([[1], [0]])
    rows = [[1], [0]]
    separator, pairing, _ = helper.first_target_separator(nonmember, rows, [1, 1])
    require(sum(separator[row] * rows[row][0] for row in range(2)) == 0 and pairing != 0, "separator control failed")
    omitted_columns = [[1, 0], [0, 1]]
    require(
        scan_first_violation(separator, len(omitted_columns), omitted_columns.__getitem__) == (1, 1, 2),
        "old-support false nonmembership was not reopened",
    )
    dependency_columns = [[1, 1], [0, 1]]
    require(
        scan_first_violation([-1, 1], len(dependency_columns), dependency_columns.__getitem__) == (1, 1, 2),
        "restricted dependent-row mutation escaped all-column scan",
    )
    valid_separator_columns = [[1, 1], [2, 2]]
    require(
        scan_first_violation([1, -1], len(valid_separator_columns), valid_separator_columns.__getitem__) is None,
        "valid separator control failed",
    )
    require(
        scan_first_violation([2, -1], len(valid_separator_columns), valid_separator_columns.__getitem__) is not None,
        "separator +1 mutant escaped",
    )

    values, scale = normalize_member([Fraction(2, 3), Fraction(-4, 9)])
    require(values == [6, -4] and scale == 9, "primitive member normalization failed")

    sample = [
        {"direction": [0] * 10 + [1], "residues": [1, 2]},
        {"direction": [0] * 9 + [1, 0], "residues": [3, 4]},
    ]
    sample_digest = digest_selected(sample)
    validate_selected_records(sample, 2, sample_digest)
    expect_rejected(
        "reordered Batch32 directions",
        lambda: validate_selected_records(list(reversed(sample)), 2, sample_digest),
    )
    changed = copy.deepcopy(sample)
    changed[0]["residues"][0] += 1
    expect_rejected(
        "selected-prefix stream mutation",
        lambda: validate_selected_records(changed, 2, sample_digest),
    )

    coefficients = [1, 2, 3]
    price_row = {
        "direction": sample[0]["direction"],
        "modular_residues": sample[0]["residues"],
        "nonzero_hinge_coefficients": 3,
        "maximum_hinge_coefficient": 3,
        "hinge_coefficients": coefficients,
        "hinge_coefficients_i64_le_sha256": digest_i64(coefficients),
    }
    validate_price_row(price_row, sample[0], 0, 3)
    reordered_price = copy.deepcopy(price_row)
    reordered_price["hinge_coefficients"] = [3, 2, 1]
    expect_rejected(
        "changed price-record order",
        lambda: validate_price_row(reordered_price, sample[0], 0, 3),
    )
    bad_price_digest = copy.deepcopy(price_row)
    bad_price_digest["hinge_coefficients_i64_le_sha256"] = "0" * 64
    expect_rejected(
        "price stream digest mutation",
        lambda: validate_price_row(bad_price_digest, sample[0], 0, 3),
    )

    valid_cache_bindings = {**CACHE_BINDINGS, "executable": "a" * 64}
    validate_bindings(valid_cache_bindings, CACHE_BINDINGS, unhashed_executable=True)
    bad_cache_bindings = dict(valid_cache_bindings)
    bad_cache_bindings["producer"] = "b" * 64
    expect_rejected(
        "cache transitive binding mutation",
        lambda: validate_bindings(bad_cache_bindings, CACHE_BINDINGS, unhashed_executable=True),
    )

    cache_manifest = load_json(CACHE_MANIFEST_PATH)
    panel_input = load_json(PANEL_INPUT_PATH)
    panel_scan = load_json(PANEL_SCAN_PATH)
    validate_cache_receipt_documents(cache_manifest, panel_input, panel_scan)
    bad_cache_manifest = copy.deepcopy(cache_manifest)
    bad_cache_manifest["layout"] = "row-major"
    expect_rejected(
        "cache semantic mutation behind a valid outer hash layer",
        lambda: validate_cache_receipt_documents(bad_cache_manifest, panel_input, panel_scan),
    )
    expect_rejected("cache truncation", lambda: validate_cache_size(CACHE_BYTES - 1))
    expect_rejected("input hash mutation", lambda: require_digest("0" * 64, "1" * 64, "input"))
    expect_rejected("stale solver source", lambda: require_digest("2" * 64, "3" * 64, "solver"))
    expect_rejected("stale manifest", lambda: require_digest("4" * 64, "5" * 64, "manifest"))
    expect_rejected("path escape", lambda: contained(ROOT.parent / "g0123-escape"))
    expect_rejected("ragged matrix", lambda: matrix_rows([[0] * ROWS, [0] * (ROWS - 1)]))

    small_expected = {
        relative(SCRIPT): sha256_path(SCRIPT),
        relative(PREREGISTRATION): sha256_path(PREREGISTRATION),
    }
    small_items = [{"path": name, "sha256": digest} for name, digest in sorted(small_expected.items())]
    validate_manifest_input_records(small_items, small_expected)
    duplicate_items = [small_items[0], copy.deepcopy(small_items[0])]
    expect_rejected(
        "duplicate manifest input",
        lambda: validate_manifest_input_records(duplicate_items, small_expected),
    )

    with tempfile.TemporaryDirectory(dir=HERE) as raw:
        path = Path(raw) / "exclusive.json"
        write_exclusive(path, {"ok": True})
        expect_rejected("output overwrite", lambda: write_exclusive(path, {"ok": False}))
        partial = Path(raw) / "serialization-abort.json"
        expect_rejected("serialization abort", lambda: write_exclusive(partial, {"bad": {1}}))
        require(not partial.exists(), "serialization abort left a final-path artifact")

    required_controls = {
        "reordered Batch32 directions",
        "selected-prefix stream mutation",
        "changed price-record order",
        "price stream digest mutation",
        "cache transitive binding mutation",
        "cache semantic mutation behind a valid outer hash layer",
        "cache truncation",
        "input hash mutation",
        "stale solver source",
        "stale manifest",
        "path escape",
        "ragged matrix",
        "duplicate manifest input",
        "output overwrite",
        "serialization abort",
    }
    require(set(rejected_controls) == required_controls, "hostile control census drift")
    print(f"g0123-full-family-master-self-test: PASS ({len(rejected_controls)} hostile mutations rejected)")


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
        print(json.dumps({"result": value["result"], "rows": value["rows"], "wall_seconds": value["wall_seconds"]}, sort_keys=True))
        return 0
    require(args.manifest is not None and args.output is not None, "run requires --manifest and --output")
    value = run(args.manifest, args.output)
    print(json.dumps({"result": value["result"], "trials": value["trials"], "wall_seconds": value["wall_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
