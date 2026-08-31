#!/usr/bin/env python3
"""Independent exact audit of the bounded G-0121 full-family member.

This file deliberately does not import or execute the G-0123 master solver.
It consumes only sealed data artifacts and reconstructs the registered 348-row
columns directly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

from flint import fmpz_mat
import flint


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

RESULT_REL = "artifacts/math/G-0121/full_family_master_result_v1.json"
MANIFEST_REL = "artifacts/math/G-0121/full_family_master_manifest_v1.json"
SOURCE_PREREG_REL = "artifacts/math/G-0121/FULL_FAMILY_MASTER_PREREGISTRATION.md"
AUDIT_PREREG_REL = "artifacts/reviews/G-0121-full-family-member/PREREGISTRATION.md"
PANEL_INPUT_REL = "artifacts/math/G-0113/panel_solver_input_v1.json"
PANEL_SCAN_REL = "artifacts/math/G-0113/panel_scan_v1.json"
CACHE_MANIFEST_REL = "artifacts/math/G-0117/full_family_cache_manifest_v1.json"
CACHE_REL = "artifacts/math/G-0117/full_family_cache_v1.i128le"
GLOBAL_REPLAY_REL = (
    "artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json"
)
BATCH_PRICE_REL = "artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json"

ACCUMULATED = [
    (
        "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4],
    ),
    (
        "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3],
    ),
    (
        "artifacts/math/G-0118/iteration3_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -3, 2],
    ),
    (
        "artifacts/math/G-0118/iteration4_residual_coordinate_v1.json",
        [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
    ),
]

EXPECTED = {
    RESULT_REL: "53bc7d8894a3552c226ca64f51bf7b369ce1d7c71f532241b14271964abc1036",
    MANIFEST_REL: "9234415af8719ea0f46eaf7952d76cab006afe44e4d7e111813fde61e4a5032c",
    SOURCE_PREREG_REL: "e7e2f6de986d839aef8614ae81d91357b34bccfb5b9ec065fd8aa5bd1a689952",
    CACHE_REL: "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b",
    CACHE_MANIFEST_REL: "e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf",
    ACCUMULATED[0][0]: "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071",
    ACCUMULATED[1][0]: "41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f",
    ACCUMULATED[2][0]: "58139181228fc2400298f400f1b80c083b72747f8d1ba3830fe4f3ee8b787f48",
    ACCUMULATED[3][0]: "862dbbbd6c2bee9424b8faf4e8cb0a2e7b4c76c94ef0a6bd78bc3e14b90258cb",
    BATCH_PRICE_REL: "349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b",
    GLOBAL_REPLAY_REL: "c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80",
    PANEL_INPUT_REL: "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    PANEL_SCAN_REL: "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e",
    AUDIT_PREREG_REL: "3a19573c37f5bcfb308b7e5d54e3b999661d5f48c9def4b87c47252873576aa4",
    "artifacts/math/G-0113/panel_retained_columns_v1.json": (
        "615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393"
    ),
}

RECORDS = 163_740
PANEL_ROWS = 301
LINEAR_ROWS = 11
ACCUMULATED_ROWS = 4
BATCH_ROWS = 32
ROWS = 348
ENTRY_BYTES = 16
SEED_COLUMNS = 115
SELECTED_COLUMNS = 156
RANK_TRIALS = 42
DECIMAL_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def contained(relative: str) -> Path:
    require(isinstance(relative, str) and relative, "empty or non-string path")
    raw = Path(relative)
    require(not raw.is_absolute(), f"absolute path refused: {relative}")
    path = (ROOT / raw).resolve(strict=True)
    require(path.is_relative_to(ROOT), f"path escape refused: {relative}")
    require(path.is_file(), f"not a regular file: {relative}")
    return path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def load_json(relative: str) -> dict[str, Any]:
    path = contained(relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditFailure(f"cannot parse {relative}: {exc}") from exc
    require(isinstance(payload, dict), f"{relative}: top-level JSON is not an object")
    return payload


def exact_json_int(value: Any, label: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{label}: not JSON integer")
    return value


def exact_decimal(value: Any, label: str) -> int:
    require(isinstance(value, str), f"{label}: expected canonical decimal string")
    require(DECIMAL_RE.fullmatch(value) is not None, f"{label}: noncanonical decimal")
    return int(value)


def i64_bytes(value: int, label: str = "i64") -> bytes:
    require(-(1 << 63) <= value < (1 << 63), f"{label}: signed-i64 overflow")
    return value.to_bytes(8, "little", signed=True)


def i128_bytes(value: int, label: str = "i128") -> bytes:
    require(-(1 << 127) <= value < (1 << 127), f"{label}: signed-i128 overflow")
    return value.to_bytes(16, "little", signed=True)


def digest_i64(values: Iterable[int], label: str) -> str:
    digest = hashlib.sha256()
    for index, value in enumerate(values):
        digest.update(i64_bytes(value, f"{label}[{index}]"))
    return digest.hexdigest()


def digest_linear(vectors: Sequence[Any], label: str) -> tuple[str, list[list[int]]]:
    require(len(vectors) == RECORDS, f"{label}: wrong linear-vector count")
    digest = hashlib.sha256()
    parsed: list[list[int]] = []
    for sequence, raw in enumerate(vectors):
        require(isinstance(raw, list) and len(raw) == LINEAR_ROWS, f"{label}[{sequence}]: bad shape")
        row = []
        for coordinate, value in enumerate(raw):
            integer = exact_json_int(value, f"{label}[{sequence}][{coordinate}]")
            digest.update(i64_bytes(integer, f"{label}[{sequence}][{coordinate}]"))
            row.append(integer)
        parsed.append(row)
    return digest.hexdigest(), parsed


def digest_matrix_i128(
    columns: Sequence[Sequence[int]], rows: Sequence[int], row_major: bool
) -> str:
    digest = hashlib.sha256()
    if row_major:
        for row in rows:
            for column_index, column in enumerate(columns):
                digest.update(i128_bytes(column[row], f"basis[{row}][{column_index}]"))
    else:
        for column_index, column in enumerate(columns):
            for row in rows:
                digest.update(i128_bytes(column[row], f"basis[{row}][{column_index}]"))
    return digest.hexdigest()


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    resolved_parent = path.parent.resolve(strict=True)
    require(resolved_parent == HERE, "output must remain in the registered review directory")
    data = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError as exc:
        raise AuditFailure(f"refusing to overwrite {path}") from exc
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        try:
            path.unlink()
        except OSError:
            pass
        raise


def validate_unique_sequences(values: Any, label: str, expected: int | None = None) -> list[int]:
    require(isinstance(values, list), f"{label}: not a list")
    parsed = [exact_json_int(value, f"{label}[{index}]") for index, value in enumerate(values)]
    if expected is not None:
        require(len(parsed) == expected, f"{label}: expected {expected}, got {len(parsed)}")
    require(len(set(parsed)) == len(parsed), f"{label}: duplicate sequence")
    require(all(0 <= value < RECORDS for value in parsed), f"{label}: out-of-range sequence")
    return parsed


def identity_residuals(
    columns: Sequence[Sequence[int]], coefficients: Sequence[int], target: Sequence[int], scale: int
) -> list[int]:
    require(len(columns) == len(coefficients), "column/coefficient length mismatch")
    require(columns, "empty column system")
    rows = len(target)
    require(all(len(column) == rows for column in columns), "ragged column system")
    return [
        sum(coefficient * column[row] for coefficient, column in zip(coefficients, columns, strict=True))
        - scale * target[row]
        for row in range(rows)
    ]


def rank_pair(columns: Sequence[Sequence[int]], target: Sequence[int]) -> tuple[int, int]:
    require(columns, "rank requested for empty column system")
    require(all(len(column) == len(target) for column in columns), "ragged rank matrix")
    row_major = [
        [column[row] for column in columns] for row in range(len(target))
    ]
    rank = int(fmpz_mat(row_major).rank())
    augmented = int(
        fmpz_mat([row + [target[index]] for index, row in enumerate(row_major)]).rank()
    )
    return rank, augmented


def self_test() -> None:
    columns = [[1, 0], [0, 1]]
    coefficients = [2, 3]
    target = [2, 3]
    require(identity_residuals(columns, coefficients, target, 1) == [0, 0], "toy identity failed")
    mutant = coefficients.copy()
    mutant[0] += 1
    require(identity_residuals(columns, mutant, target, 1) != [0, 0], "toy mutant survived")
    require(math.gcd(2, 2, 4) != 1, "nonprimitive toy was accepted")
    try:
        validate_unique_sequences([1, 1], "duplicate")
    except AuditFailure:
        pass
    else:
        raise AuditFailure("duplicate support self-test did not fail")
    try:
        identity_residuals([[1], [0, 1]], [1, 1], [1], 1)
    except AuditFailure:
        pass
    else:
        raise AuditFailure("ragged identity self-test did not fail")
    require(rank_pair(columns, target) == (2, 2), "member rank control failed")
    require(rank_pair([[1, 0]], [0, 1]) == (1, 2), "augmented-rank control failed")
    print("SELF_TEST_PASS")


def verify_hash_bindings(manifest: dict[str, Any]) -> dict[str, str]:
    manifest_rows = manifest.get("expected_inputs")
    require(isinstance(manifest_rows, list) and manifest_rows, "manifest expected_inputs missing")
    manifest_expected: dict[str, str] = {}
    for index, row in enumerate(manifest_rows):
        require(isinstance(row, dict), f"manifest expected_inputs[{index}] malformed")
        relative = row.get("path")
        expected = row.get("sha256")
        require(isinstance(relative, str), f"manifest expected_inputs[{index}] path")
        require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected), f"manifest expected_inputs[{index}] sha")
        require(relative not in manifest_expected, f"duplicate manifest input {relative}")
        manifest_expected[relative] = expected

    for relative, expected in EXPECTED.items():
        if relative not in {RESULT_REL, MANIFEST_REL, AUDIT_PREREG_REL}:
            require(manifest_expected.get(relative) == expected, f"manifest binding mismatch for {relative}")

    combined = dict(manifest_expected)
    combined[RESULT_REL] = EXPECTED[RESULT_REL]
    combined[MANIFEST_REL] = EXPECTED[MANIFEST_REL]
    combined[AUDIT_PREREG_REL] = EXPECTED[AUDIT_PREREG_REL]
    observed: dict[str, str] = {}
    for relative, expected in sorted(combined.items()):
        actual = sha256_file(contained(relative))
        require(actual == expected, f"SHA-256 mismatch for {relative}: {actual}")
        observed[relative] = actual
    return observed


def read_panel_column(handle: Any, sequence: int) -> list[int]:
    offset = sequence * PANEL_ROWS * ENTRY_BYTES
    raw = os.pread(handle.fileno(), PANEL_ROWS * ENTRY_BYTES, offset)
    require(len(raw) == PANEL_ROWS * ENTRY_BYTES, f"truncated panel column {sequence}")
    return [
        int.from_bytes(raw[start : start + ENTRY_BYTES], "little", signed=True)
        for start in range(0, len(raw), ENTRY_BYTES)
    ]


def verify_panel(
    selected: Sequence[int], observed_hashes: dict[str, str]
) -> tuple[list[list[int]], list[int], dict[str, Any]]:
    cache_manifest = load_json(CACHE_MANIFEST_REL)
    require(cache_manifest.get("schema") == "max11-g0117-full-family-panel-cache-v1", "cache manifest schema")
    require(cache_manifest.get("records") == RECORDS, "cache manifest records")
    require(cache_manifest.get("rows") == PANEL_ROWS, "cache manifest rows")
    require(cache_manifest.get("entry_bytes") == ENTRY_BYTES, "cache entry width")
    require(cache_manifest.get("payload_bytes") == RECORDS * PANEL_ROWS * ENTRY_BYTES, "cache payload bytes")
    require(cache_manifest.get("layout") == "sequence-major: offset=((sequence*301)+row)*16", "cache layout")
    require(cache_manifest.get("integer_width") == "signed i128", "cache integer width")
    require(cache_manifest.get("endianness") == "little", "cache endianness")
    require(cache_manifest.get("data_sha256") == observed_hashes[CACHE_REL], "cache data binding")
    cache_path = contained(CACHE_REL)
    require(cache_path.stat().st_size == RECORDS * PANEL_ROWS * ENTRY_BYTES, "cache byte size")

    controls = cache_manifest.get("control_vector_sha256")
    require(isinstance(controls, dict) and controls, "cache controls missing")
    with cache_path.open("rb") as handle:
        for raw_sequence, expected in controls.items():
            sequence = int(raw_sequence)
            column = read_panel_column(handle, sequence)
            actual = hashlib.sha256(b"".join(i128_bytes(value) for value in column)).hexdigest()
            require(actual == expected, f"cache control digest mismatch at {sequence}")
        columns = [read_panel_column(handle, sequence) for sequence in selected]

    panel_input = load_json(PANEL_INPUT_REL)
    require(panel_input.get("schema") == "max11-g0113-panel-solver-input-v1", "panel input schema")
    target_raw = panel_input.get("target")
    require(isinstance(target_raw, list) and len(target_raw) == PANEL_ROWS, "panel target shape")
    target = [exact_json_int(value, f"panel target[{index}]") for index, value in enumerate(target_raw)]
    records = panel_input.get("records")
    require(isinstance(records, list) and len(records) == RECORDS, "panel record count")
    order_digest = hashlib.sha256()
    for expected_sequence, record in enumerate(records):
        require(isinstance(record, dict), f"panel record {expected_sequence} malformed")
        sequence = exact_json_int(record.get("sequence"), f"panel record {expected_sequence} sequence")
        require(sequence == expected_sequence, f"panel record order mismatch at {expected_sequence}")
        order_digest.update(sequence.to_bytes(8, "little"))

    panel_scan = load_json(PANEL_SCAN_REL)
    require(panel_scan.get("records") == RECORDS, "panel scan records")
    target_i64 = digest_i64(target, "panel target")
    target_i128 = hashlib.sha256(b"".join(i128_bytes(value) for value in target)).hexdigest()
    require(panel_scan.get("target_i64_le_sha256") == target_i64, "panel target i64 digest")
    require(panel_scan.get("target_i128_le_sha256") == target_i128, "panel target i128 digest")
    return columns, target, {
        "cache_controls_checked": len(controls),
        "cache_bytes": cache_path.stat().st_size,
        "record_order_u64le_sha256": order_digest.hexdigest(),
        "target_i64_le_sha256": target_i64,
        "target_i128_le_sha256": target_i128,
    }


def verify_accumulated(
    selected: Sequence[int],
) -> tuple[list[list[int]], list[list[int]], str, list[dict[str, Any]]]:
    accumulated: list[list[int]] = []
    selected_linear_reference: list[list[int]] | None = None
    reference_digest: str | None = None
    summaries: list[dict[str, Any]] = []
    for relative, expected_direction in ACCUMULATED:
        payload = load_json(relative)
        require(payload.get("schema") == "max11-g0117-coordinate-price-v1", f"{relative}: schema")
        require(payload.get("result") == "EXACT_COORDINATE_PRICES", f"{relative}: result")
        require(payload.get("records") == RECORDS, f"{relative}: records")
        require(payload.get("direction") == expected_direction, f"{relative}: direction")
        hinges_raw = payload.get("hinge_coefficients")
        require(isinstance(hinges_raw, list) and len(hinges_raw) == RECORDS, f"{relative}: hinge shape")
        hinges = [exact_json_int(value, f"{relative}: hinge[{index}]") for index, value in enumerate(hinges_raw)]
        hinge_digest = digest_i64(hinges, f"{relative}: hinge")
        require(hinge_digest == payload.get("hinge_coefficients_i64_le_sha256"), f"{relative}: hinge digest")
        nonzero = sum(value != 0 for value in hinges)
        maximum = max(abs(value) for value in hinges)
        require(nonzero == payload.get("nonzero_hinge_coefficients"), f"{relative}: nonzero count")
        require(maximum == payload.get("maximum_hinge_coefficient"), f"{relative}: maximum")

        linear_digest, linear = digest_linear(payload.get("linear_vectors"), f"{relative}: linear")
        require(linear_digest == payload.get("linear_vectors_i64_le_sha256"), f"{relative}: linear digest")
        selected_linear = [linear[sequence] for sequence in selected]
        if selected_linear_reference is None:
            selected_linear_reference = selected_linear
            reference_digest = linear_digest
        else:
            require(linear_digest == reference_digest, f"{relative}: linear stream differs")
            require(selected_linear == selected_linear_reference, f"{relative}: selected linears differ")
        accumulated.append([hinges[sequence] for sequence in selected])
        summaries.append(
            {
                "path": relative,
                "direction": expected_direction,
                "hinge_i64le_sha256": hinge_digest,
                "linear_i64le_sha256": linear_digest,
                "nonzero_hinges": nonzero,
                "maximum_abs_hinge": maximum,
            }
        )
        del payload, hinges, hinges_raw, linear
    assert selected_linear_reference is not None and reference_digest is not None
    return accumulated, selected_linear_reference, reference_digest, summaries


def selected_prefix_digest(selected: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for index, row in enumerate(selected):
        direction = row.get("direction")
        residues = row.get("residues")
        require(isinstance(direction, list) and len(direction) == 11, f"selected[{index}] direction")
        require(isinstance(residues, list) and len(residues) == 2, f"selected[{index}] residues")
        for coordinate, value in enumerate(direction):
            integer = exact_json_int(value, f"selected[{index}].direction[{coordinate}]")
            require(-128 <= integer <= 127, f"selected[{index}] direction i8 overflow")
            digest.update(integer.to_bytes(1, "little", signed=True))
        for prime_index, value in enumerate(residues):
            integer = exact_json_int(value, f"selected[{index}].residues[{prime_index}]")
            require(0 <= integer < (1 << 64), f"selected[{index}] residue u64 overflow")
            digest.update(integer.to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def verify_batch(
    selected_sequences: Sequence[int], linear_reference: Sequence[Sequence[int]], linear_digest: str
) -> tuple[list[list[int]], list[list[int]], dict[str, Any]]:
    replay = load_json(GLOBAL_REPLAY_REL)
    require(replay.get("schema") == "max11-g0118-batch32-global-modular-replay-v1", "global replay schema")
    require(replay.get("result") == "BATCH_RESIDUAL_PREFIX_SELECTED", "global replay result")
    require(replay.get("complete_global_replay") is True, "global replay completeness label")
    require(replay.get("batch_k") == BATCH_ROWS, "global replay batch K")
    selected = replay.get("selected")
    require(isinstance(selected, list) and len(selected) == BATCH_ROWS, "global replay selected shape")
    prefix_digest = selected_prefix_digest(selected)
    require(prefix_digest == replay.get("selected_prefix_i8_u64_le_sha256"), "selected-prefix digest")

    price = load_json(BATCH_PRICE_REL)
    require(price.get("schema") == "max11-g0118-batch32-coordinate-price-v1", "batch price schema")
    require(price.get("result") == "EXACT_BATCH_COORDINATE_PRICES", "batch price result")
    require(price.get("batch_k") == BATCH_ROWS, "batch price K")
    require(price.get("selected_count") == BATCH_ROWS, "batch selected count")
    require(price.get("records") == RECORDS, "batch records")
    directions = [row.get("direction") for row in selected]
    residues = [row.get("residues") for row in selected]
    require(price.get("directions") == directions, "batch direction order")
    require(price.get("modular_residues") == residues, "batch residue order")
    rows = price.get("rows")
    require(isinstance(rows, list) and len(rows) == BATCH_ROWS, "batch row shape")
    aggregate = hashlib.sha256()
    selected_hinges: list[list[int]] = []
    row_summaries: list[dict[str, Any]] = []
    for row_index, row in enumerate(rows):
        require(isinstance(row, dict), f"batch row {row_index} malformed")
        require(row.get("direction") == directions[row_index], f"batch row {row_index} direction")
        require(row.get("modular_residues") == residues[row_index], f"batch row {row_index} residues")
        raw = row.get("hinge_coefficients")
        require(isinstance(raw, list) and len(raw) == RECORDS, f"batch row {row_index} hinge shape")
        digest = hashlib.sha256()
        chosen: list[int] = []
        selected_set = set(selected_sequences)
        chosen_by_sequence: dict[int, int] = {}
        nonzero = 0
        maximum = 0
        for sequence, value in enumerate(raw):
            integer = exact_json_int(value, f"batch[{row_index}].hinge[{sequence}]")
            packed = i64_bytes(integer, f"batch[{row_index}].hinge[{sequence}]")
            digest.update(packed)
            aggregate.update(packed)
            if sequence in selected_set:
                chosen_by_sequence[sequence] = integer
            nonzero += integer != 0
            maximum = max(maximum, abs(integer))
        chosen = [chosen_by_sequence[sequence] for sequence in selected_sequences]
        actual = digest.hexdigest()
        require(actual == row.get("hinge_coefficients_i64_le_sha256"), f"batch row {row_index} digest")
        require(nonzero == row.get("nonzero_hinge_coefficients"), f"batch row {row_index} nonzero")
        require(maximum == row.get("maximum_hinge_coefficient"), f"batch row {row_index} maximum")
        selected_hinges.append(chosen)
        row_summaries.append(
            {
                "index": row_index,
                "direction": directions[row_index],
                "hinge_i64le_sha256": actual,
                "nonzero_hinges": nonzero,
                "maximum_abs_hinge": maximum,
            }
        )
    aggregate_digest = aggregate.hexdigest()
    require(aggregate_digest == price.get("direction_major_hinge_i64_le_sha256"), "batch aggregate digest")
    batch_linear_digest, batch_linear = digest_linear(price.get("linear_vectors"), "batch linear")
    require(batch_linear_digest == price.get("linear_vectors_i64_le_sha256"), "batch linear digest")
    require(batch_linear_digest == linear_digest, "batch/accumulated linear digest mismatch")
    selected_linear = [batch_linear[sequence] for sequence in selected_sequences]
    require(selected_linear == list(linear_reference), "batch/accumulated selected linears mismatch")
    return selected_hinges, directions, {
        "selected_prefix_i8_u64_le_sha256": prefix_digest,
        "direction_major_hinge_i64_le_sha256": aggregate_digest,
        "linear_vectors_i64_le_sha256": batch_linear_digest,
        "rows": row_summaries,
    }


def parse_result_and_transcript(
    result: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    require(result.get("schema") == "max11-g0121-full-family-master-result-v1", "result schema")
    require(result.get("result") == "FULL_FAMILY_EXACT_Q_MEMBER", "result branch")
    require(result.get("manifest_path") == MANIFEST_REL, "result manifest path")
    require(result.get("manifest_sha256") == EXPECTED[MANIFEST_REL], "result manifest hash")
    require(result.get("solver_sha256") == manifest.get("solver", {}).get("sha256"), "result solver binding")
    require(result.get("records") == RECORDS and result.get("rows") == ROWS, "result dimensions")
    require(result.get("all_rows_replayed") is True, "result all-row label")
    require(result.get("coefficient_plus_one_mutant_rejected") is True, "result mutant label")

    selected = validate_unique_sequences(result.get("selected_sequences"), "selected_sequences", SELECTED_COLUMNS)
    support = validate_unique_sequences(result.get("support_sequences"), "support_sequences", SELECTED_COLUMNS)
    require(support == selected, "support_sequences differs from selected_sequences")
    require(selected == sorted(selected), "selected sequences are not in increasing family order")
    seed = validate_unique_sequences(manifest.get("seed_sequences"), "manifest seed_sequences", SEED_COLUMNS)

    raw_coefficients = result.get("integer_coefficients")
    require(isinstance(raw_coefficients, list) and len(raw_coefficients) == SELECTED_COLUMNS, "coefficient shape")
    coefficients = [exact_decimal(value, f"integer_coefficients[{index}]") for index, value in enumerate(raw_coefficients)]
    scale = exact_decimal(result.get("target_scale"), "target_scale")
    require(scale > 0, "target_scale is not positive")
    normalization_gcd = abs(scale)
    for coefficient in coefficients:
        normalization_gcd = math.gcd(normalization_gcd, abs(coefficient))
    require(normalization_gcd == 1, f"coefficient/scale gcd is {normalization_gcd}")

    expected_terms = [
        {"coefficient": raw, "sequence": sequence}
        for sequence, raw, coefficient in zip(selected, raw_coefficients, coefficients, strict=True)
        if coefficient != 0
    ]
    require(result.get("terms") == expected_terms, "terms do not equal nonzero selected coefficients")
    nonzero_support = [term["sequence"] for term in expected_terms]

    coordinate_rows_raw = result.get("coordinate_rows")
    require(isinstance(coordinate_rows_raw, list), "coordinate_rows missing")
    coordinate_rows = [
        exact_json_int(value, f"coordinate_rows[{index}]")
        for index, value in enumerate(coordinate_rows_raw)
    ]
    require(len(coordinate_rows) == SELECTED_COLUMNS, "coordinate-row count")
    require(coordinate_rows == sorted(set(coordinate_rows)), "coordinate rows not canonical sorted unique")
    require(all(0 <= row < ROWS for row in coordinate_rows), "coordinate row out of range")

    trials = result.get("trials")
    require(isinstance(trials, list) and len(trials) == RANK_TRIALS, "rank trial count")
    appended: list[int] = []
    for iteration, trial in enumerate(trials):
        require(isinstance(trial, dict), f"trial {iteration} malformed")
        require(trial.get("iteration") == iteration, f"trial {iteration} iteration label")
        if iteration < RANK_TRIALS - 1:
            require(trial.get("result") == "SEPARATOR_VIOLATED", f"trial {iteration} branch")
            sequence = exact_json_int(trial.get("first_violating_sequence"), f"trial {iteration} violating sequence")
            require(trial.get("columns_scanned") == sequence + 1, f"trial {iteration} scan count")
            require(exact_decimal(trial.get("first_violating_price"), f"trial {iteration} price") != 0, f"trial {iteration} zero price")
            require(exact_decimal(trial.get("separator_target_pairing"), f"trial {iteration} target pairing") != 0, f"trial {iteration} zero target pairing")
            free_row = exact_json_int(trial.get("separator_free_row"), f"trial {iteration} free row")
            require(0 <= free_row < ROWS, f"trial {iteration} free row range")
            appended.append(sequence)
        else:
            require(trial.get("result") == "EXACT_Q_MEMBER", "final trial branch")
    require(len(set(seed + appended)) == SELECTED_COLUMNS, "seed/appended transcript has duplicates")
    require(sorted(seed + appended) == selected, "sorted seed-plus-trial union differs from selected basis")

    return {
        "selected": selected,
        "support_field": support,
        "nonzero_support": nonzero_support,
        "coefficients": coefficients,
        "raw_coefficients": raw_coefficients,
        "scale": scale,
        "normalization_gcd": normalization_gcd,
        "coordinate_rows": coordinate_rows,
        "trials": trials,
        "seed": seed,
        "appended": appended,
    }


def run_audit() -> dict[str, Any]:
    started = time.monotonic()
    result = load_json(RESULT_REL)
    manifest = load_json(MANIFEST_REL)
    require(manifest.get("schema") == "max11-g0121-full-family-master-manifest-v1", "manifest schema")
    require(manifest.get("rows") == ROWS and manifest.get("records") == RECORDS, "manifest dimensions")
    observed_hashes = verify_hash_bindings(manifest)
    transcript = parse_result_and_transcript(result, manifest)
    selected = transcript["selected"]

    panel_columns, panel_target, panel_summary = verify_panel(selected, observed_hashes)
    accumulated, selected_linears, linear_digest, accumulated_summary = verify_accumulated(selected)
    batch, batch_directions, batch_summary = verify_batch(selected, selected_linears, linear_digest)

    expected_directions = [direction for _, direction in ACCUMULATED] + batch_directions
    require(result.get("hinge_directions") == expected_directions, "result hinge-direction order")
    require(len(expected_directions) == ACCUMULATED_ROWS + BATCH_ROWS, "hinge direction count")

    columns: list[list[int]] = []
    for column_index in range(SELECTED_COLUMNS):
        column = (
            panel_columns[column_index]
            + selected_linears[column_index]
            + [row[column_index] for row in accumulated]
            + [row[column_index] for row in batch]
        )
        require(len(column) == ROWS, f"reconstructed column {column_index} row count")
        columns.append(column)
    target = panel_target + [0] * 10 + [math.factorial(11)] + [0] * (ACCUMULATED_ROWS + BATCH_ROWS)
    require(len(target) == ROWS, "target row count")

    residuals = identity_residuals(columns, transcript["coefficients"], target, transcript["scale"])
    nonzero_rows = [index for index, value in enumerate(residuals) if value != 0]
    if nonzero_rows:
        raise AuditFailure(
            f"denominator-cleared identity fails first at row {nonzero_rows[0]}"
        )

    first_nonzero = next(index for index, value in enumerate(transcript["coefficients"]) if value != 0)
    mutant_coefficients = list(transcript["coefficients"])
    mutant_coefficients[first_nonzero] += 1
    mutant_residuals = identity_residuals(columns, mutant_coefficients, target, transcript["scale"])
    mutant_rows = [index for index, value in enumerate(mutant_residuals) if value != 0]
    require(mutant_rows, "coefficient +1 mutant survived")

    coordinate_rows = transcript["coordinate_rows"]
    expected_basis_digest = result.get("selected_basis_i128le_sha256")
    require(isinstance(expected_basis_digest, str) and re.fullmatch(r"[0-9a-f]{64}", expected_basis_digest), "selected basis digest label")
    basis_row_major = digest_matrix_i128(columns, coordinate_rows, row_major=True)
    basis_column_major = digest_matrix_i128(columns, coordinate_rows, row_major=False)
    full_row_major = digest_matrix_i128(columns, list(range(ROWS)), row_major=True)
    full_column_major = digest_matrix_i128(columns, list(range(ROWS)), row_major=False)
    basis_serializations = {
        "coordinate_square_row_major": basis_row_major,
        "coordinate_square_column_major": basis_column_major,
        "full_348_by_156_row_major": full_row_major,
        "full_348_by_156_column_major": full_column_major,
    }
    matching_basis_serializations = [
        name for name, digest in basis_serializations.items() if digest == expected_basis_digest
    ]
    require(
        len(matching_basis_serializations) == 1,
        "selected-basis digest matched "
        f"{matching_basis_serializations}; natural candidates were {basis_serializations}",
    )
    square_rank = int(
        fmpz_mat([[columns[column][row] for column in range(SELECTED_COLUMNS)] for row in coordinate_rows]).rank()
    )
    require(square_rank == SELECTED_COLUMNS, f"coordinate square rank {square_rank}")

    rank_receipts: list[dict[str, Any]] = []
    previous_rank: int | None = None
    column_by_sequence = dict(zip(selected, columns, strict=True))
    for iteration, trial in enumerate(transcript["trials"]):
        trial_sequences = transcript["seed"] + transcript["appended"][:iteration]
        column_count = len(trial_sequences)
        trial_columns = [column_by_sequence[sequence] for sequence in trial_sequences]
        rank_started = time.monotonic()
        rank, augmented = rank_pair(trial_columns, target)
        reported_rank = exact_json_int(trial.get("rank"), f"trial {iteration} reported rank")
        reported_augmented = exact_json_int(trial.get("augmented_rank"), f"trial {iteration} reported augmented rank")
        require(rank == reported_rank, f"trial {iteration} rank mismatch {rank} != {reported_rank}")
        require(augmented == reported_augmented, f"trial {iteration} augmented rank mismatch {augmented} != {reported_augmented}")
        if previous_rank is not None:
            require(rank == previous_rank + 1, f"trial {iteration} appended column does not raise rank")
        previous_rank = rank
        rank_receipts.append(
            {
                "iteration": iteration,
                "columns": column_count,
                "rank": rank,
                "augmented_rank": augmented,
                "wall_seconds": time.monotonic() - rank_started,
            }
        )
    require(rank_receipts[-1]["rank"] == rank_receipts[-1]["augmented_rank"] == SELECTED_COLUMNS, "final membership rank")

    support_semantics_match = transcript["support_field"] == transcript["nonzero_support"]
    support_is_increasing = transcript["support_field"] == sorted(transcript["support_field"])
    preregistration_deviations: list[dict[str, Any]] = []
    if not support_semantics_match:
        preregistration_deviations.append(
            {
                "code": "SUPPORT-FIELD-INCLUDES-ZERO-COEFFICIENTS",
                "detail": (
                    f"support_sequences has {len(transcript['support_field'])} entries, while the "
                    f"nonzero term support has {len(transcript['nonzero_support'])}; the field is the "
                    "selected basis transcript, not mathematical coefficient support"
                ),
                "load_bearing_for_identity": False,
            }
        )
    if not support_is_increasing:
        preregistration_deviations.append(
            {
                "code": "SUPPORT-FIELD-NOT-NUMERICALLY-INCREASING",
                "detail": "support_sequences preserves seed-plus-CEGIS append order rather than increasing family order",
                "load_bearing_for_identity": False,
            }
        )

    end_rehash_paths = [RESULT_REL, MANIFEST_REL, CACHE_REL, BATCH_PRICE_REL] + [row[0] for row in ACCUMULATED]
    end_hashes = {relative: sha256_file(contained(relative)) for relative in end_rehash_paths}
    for relative, digest in end_hashes.items():
        require(digest == observed_hashes[relative], f"input drift during audit: {relative}")

    certificate_verdict = "CONSISTENT"
    review_verdict = "INCONSISTENT" if preregistration_deviations else "CONSISTENT"
    return {
        "schema": "max11-g0125-cleanroom-member-audit-v1",
        "verdict": review_verdict,
        "mathematical_certificate_verdict": certificate_verdict,
        "tier_boundary": "Fresh-context same OpenAI GPT-5 lineage: at most T1.",
        "claim_boundary": (
            "Exact consistency only on the frozen 348-row system over the frozen 163,740-column family; "
            "not a global identity, network, family-completeness theorem, or MAX11 result."
        ),
        "source": {
            "commit": "492462854538c563f57cbf77f87283305e18a36e",
            "result_path": RESULT_REL,
            "result_sha256": observed_hashes[RESULT_REL],
            "manifest_sha256": observed_hashes[MANIFEST_REL],
            "audit_preregistration_sha256": observed_hashes[AUDIT_PREREG_REL],
        },
        "environment": {
            "python": sys.version,
            "python_flint": getattr(flint, "__version__", "unknown"),
            "script_sha256": sha256_file(Path(__file__).resolve()),
        },
        "dimensions": {
            "family_records": RECORDS,
            "rows": ROWS,
            "panel_rows": PANEL_ROWS,
            "linear_rows": LINEAR_ROWS,
            "accumulated_hinge_rows": ACCUMULATED_ROWS,
            "batch_hinge_rows": BATCH_ROWS,
            "selected_columns": SELECTED_COLUMNS,
            "nonzero_terms": len(transcript["nonzero_support"]),
            "zero_selected_coefficients": SELECTED_COLUMNS - len(transcript["nonzero_support"]),
            "rank_trials": len(rank_receipts),
        },
        "normalization": {
            "target_scale_positive": transcript["scale"] > 0,
            "coefficient_and_scale_gcd": transcript["normalization_gcd"],
            "target_scale": str(transcript["scale"]),
        },
        "support": {
            "selected_equals_support_field": transcript["selected"] == transcript["support_field"],
            "support_field_equals_nonzero_term_support": support_semantics_match,
            "support_field_is_numerically_increasing": support_is_increasing,
            "seed_prefix_count": len(transcript["seed"]),
            "appended_count": len(transcript["appended"]),
            "nonzero_term_count": len(transcript["nonzero_support"]),
        },
        "identity": {
            "all_348_rows_zero": True,
            "nonzero_residual_rows": nonzero_rows,
            "target_final_linear_coordinate": math.factorial(11),
            "target_other_added_coordinates_zero": True,
        },
        "mutant": {
            "kind": "add one to first nonzero integer coefficient",
            "selected_position": first_nonzero,
            "sequence": transcript["selected"][first_nonzero],
            "rejected": True,
            "first_mismatch_row": mutant_rows[0],
            "first_mismatch_residual": str(mutant_residuals[mutant_rows[0]]),
            "mismatch_row_count": len(mutant_rows),
        },
        "selected_basis": {
            "coordinate_row_count": len(coordinate_rows),
            "coordinate_square_rank": square_rank,
            "row_major_i128le_sha256": basis_row_major,
            "column_major_i128le_sha256_control": basis_column_major,
            "full_row_major_i128le_sha256_control": full_row_major,
            "full_column_major_i128le_sha256_control": full_column_major,
            "reported_sha256": expected_basis_digest,
            "matches_reported": True,
            "matching_serialization": matching_basis_serializations[0],
            "serialization_note": (
                "Four natural signed-i128 little-endian matrix traversals were tested without "
                "consulting the producer; exactly one matched."
            ),
        },
        "rank_trials": rank_receipts,
        "panel": panel_summary,
        "accumulated_rows": accumulated_summary,
        "batch": batch_summary,
        "preregistration_deviations": preregistration_deviations,
        "hashes_at_start": observed_hashes,
        "hashes_at_end": end_hashes,
        "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "wall_seconds": time.monotonic() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.output is None, "--self-test does not write output")
        self_test()
        return
    require(args.output is not None, "scientific run requires --output")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    receipt = run_audit()
    write_exclusive(output, receipt)
    print(json.dumps({"verdict": receipt["verdict"], "certificate": receipt["mathematical_certificate_verdict"], "output": str(output)}))


if __name__ == "__main__":
    try:
        main()
    except AuditFailure as exc:
        print(f"AUDIT_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
