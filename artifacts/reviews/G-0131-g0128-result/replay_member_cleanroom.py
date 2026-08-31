#!/usr/bin/env python3
"""Independent exact audit of the bounded G-0128 380-row member.

The checker does not import or execute the G-0128 scientific solver.  It
reconstructs the target and selected columns directly from the frozen cache
and coordinate receipts, then checks the delivered certificate in exact
integer arithmetic.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import resource
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Sequence

import flint
from flint import fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

RESULT_REL = "artifacts/math/G-0128/full_family_master_result_v2.json"
MANIFEST_REL = "artifacts/math/G-0128/full_family_master_manifest_v2.json"
SOURCE_REL = "artifacts/math/G-0128/full_family_master_v2.py"
SOURCE_PREREG_REL = "artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md"
SOURCE_AUDIT_REL = "artifacts/reviews/G-0128-round2-master/AUDIT_VERDICT.md"
AUDIT_PREREG_REL = "artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md"

PANEL_INPUT_REL = "artifacts/math/G-0113/panel_solver_input_v1.json"
PANEL_SCAN_REL = "artifacts/math/G-0113/panel_scan_v1.json"
CACHE_MANIFEST_REL = "artifacts/math/G-0117/full_family_cache_manifest_v1.json"
CACHE_REL = "artifacts/math/G-0117/full_family_cache_v1.i128le"
PRIOR_RESULT_REL = "artifacts/math/G-0121/full_family_master_result_v1.json"
OLD_CANDIDATE_REL = "artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json"
OLD_SELECTION_REL = "artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json"
OLD_PRICE_REL = "artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json"
NEW_SELECTION_REL = "artifacts/math/G-0126/global_replay_v1.json"
NEW_PRICE_REL = "artifacts/math/G-0127/batch32_coordinate_prices_v1.json"

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

RESULT_SHA256 = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838"
MANIFEST_SHA256 = "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec"
SOURCE_SHA256 = "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8"
AUDIT_PREREG_SHA256 = "74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799"
SOURCE_AUDIT_SHA256 = "049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed"
RESULT_COMMIT = "b5b73a1b6ffec75ca2c54a31bf2ebb62ec9dbf0c"
AUDIT_PREREG_COMMIT = "0f384376dde61e025e1978c3f5102c951396aef5"
MANIFEST_COMMIT = "3676d68e14815296c9c424837625993ea4d0c3d2"
SOURCE_AUDIT_COMMIT = "2269652fc689519220ecfcef028519b8ac6283e5"

RECORDS = 163_740
PANEL_ROWS = 301
LINEAR_ROWS = 11
ACCUMULATED_ROWS = 4
OLD_BATCH_ROWS = 32
NEW_BATCH_ROWS = 32
ROWS = 380
ENTRY_BYTES = 16
SEED_COLUMNS = 156
SELECTED_COLUMNS = 176
RANK_TRIALS = 21
DECIMAL_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def contained(relative: str) -> Path:
    require(isinstance(relative, str) and relative, "empty or non-string path")
    raw = Path(relative)
    require(not raw.is_absolute(), f"absolute path refused: {relative}")
    candidate = ROOT / raw
    resolved = candidate.resolve(strict=True)
    require(resolved.is_relative_to(ROOT), f"path escape refused: {relative}")
    require(candidate.absolute() == resolved, f"noncanonical or symlink path refused: {relative}")
    require(resolved.is_file(), f"not a regular file: {relative}")
    return resolved


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json_sha256(value: Any) -> str:
    data = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()
    return sha256_bytes(data)


def load_json(relative: str) -> dict[str, Any]:
    path = contained(relative)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise AuditFailure(f"cannot parse {relative}: {exc}") from exc
    require(isinstance(payload, dict), f"{relative}: top-level JSON is not an object")
    return payload


def exact_json_int(value: Any, label: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool), f"{label}: not a JSON integer")
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


def decimal_lf_sha256(values: Sequence[int]) -> str:
    return sha256_bytes("".join(f"{value}\n" for value in values).encode("ascii"))


def u64le_sha256(values: Sequence[int]) -> str:
    digest = hashlib.sha256()
    for index, value in enumerate(values):
        require(0 <= value < (1 << 64), f"u64[{index}] out of range")
        digest.update(value.to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def digest_i64(values: Iterable[int], label: str) -> str:
    digest = hashlib.sha256()
    for index, value in enumerate(values):
        digest.update(i64_bytes(value, f"{label}[{index}]"))
    return digest.hexdigest()


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


def selected_prefix_digest(selected: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for index, row in enumerate(selected):
        require(isinstance(row, dict), f"selected[{index}] malformed")
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


def validate_sequences(values: Any, label: str, expected: int | None = None) -> list[int]:
    require(isinstance(values, list), f"{label}: not a list")
    parsed = [exact_json_int(value, f"{label}[{index}]") for index, value in enumerate(values)]
    if expected is not None:
        require(len(parsed) == expected, f"{label}: expected {expected}, got {len(parsed)}")
    require(len(set(parsed)) == len(parsed), f"{label}: duplicate sequence")
    require(all(0 <= value < RECORDS for value in parsed), f"{label}: out-of-range sequence")
    return parsed


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    require(path.parent.resolve(strict=True) == HERE, "output must remain in review directory")
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


def identity_residuals(
    columns: Sequence[Sequence[int]], coefficients: Sequence[int], target: Sequence[int], scale: int
) -> list[int]:
    require(len(columns) == len(coefficients), "column/coefficient length mismatch")
    require(columns and all(len(column) == len(target) for column in columns), "ragged column system")
    return [
        sum(coefficient * column[row] for coefficient, column in zip(coefficients, columns, strict=True))
        - scale * target[row]
        for row in range(len(target))
    ]


def rank_pair(columns: Sequence[Sequence[int]], target: Sequence[int]) -> tuple[int, int]:
    require(columns and all(len(column) == len(target) for column in columns), "ragged rank matrix")
    rows = [[column[row] for column in columns] for row in range(len(target))]
    rank = int(fmpz_mat(rows).rank())
    augmented = int(
        fmpz_mat([values + [target[index]] for index, values in enumerate(rows)]).rank()
    )
    return rank, augmented


def git_output(*args: str) -> bytes:
    try:
        return subprocess.check_output(["git", *args], cwd=ROOT, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as exc:
        raise AuditFailure(f"git {' '.join(args)} failed: {exc.output.decode(errors='replace')}") from exc


def git_blob_sha256(commit: str, relative: str) -> str:
    return sha256_bytes(git_output("show", f"{commit}:{relative}"))


def self_test() -> None:
    columns = [[1, 0, 2], [0, 1, 3]]
    target = [2, 3, 13]
    coefficients = [2, 3]
    require(identity_residuals(columns, coefficients, target, 1) == [0, 0, 0], "toy identity")
    mutant = coefficients.copy()
    mutant[0] += 1
    require(identity_residuals(columns, mutant, target, 1) != [0, 0, 0], "toy mutant survived")
    require(math.gcd(6, 12, 18) != 1, "nonprimitive control")
    require(rank_pair(columns, target) == (2, 2), "member rank control")
    require(rank_pair([[1, 0, 0]], target) == (1, 2), "nonmember rank control")
    try:
        exact_decimal("01", "bad decimal")
    except AuditFailure:
        pass
    else:
        raise AuditFailure("noncanonical decimal self-test survived")
    try:
        exact_json_int(True, "bool")
    except AuditFailure:
        pass
    else:
        raise AuditFailure("boolean integer self-test survived")
    try:
        validate_sequences([1, 1], "duplicate")
    except AuditFailure:
        pass
    else:
        raise AuditFailure("duplicate sequence self-test survived")
    control = [{"direction": [0] * 10 + [1], "residues": [2, 3]}]
    original = selected_prefix_digest(control)
    mutated = json.loads(json.dumps(control))
    mutated[0]["direction"][-1] = -1
    require(selected_prefix_digest(mutated) != original, "prefix mutation did not change digest")
    print("SELF_TEST_PASS")


def verify_git_custody() -> dict[str, Any]:
    require(git_output("rev-parse", RESULT_COMMIT).decode().strip() == RESULT_COMMIT, "result commit missing")
    parents = git_output("show", "-s", "--format=%P", RESULT_COMMIT).decode().strip().split()
    require(parents == [AUDIT_PREREG_COMMIT], f"result commit parent drift: {parents}")
    require(git_blob_sha256(RESULT_COMMIT, RESULT_REL) == RESULT_SHA256, "result commit blob mismatch")
    require(git_blob_sha256(RESULT_COMMIT, AUDIT_PREREG_REL) == AUDIT_PREREG_SHA256, "audit prereg blob mismatch")
    require(git_blob_sha256(MANIFEST_COMMIT, MANIFEST_REL) == MANIFEST_SHA256, "manifest commit blob mismatch")
    require(git_blob_sha256(SOURCE_AUDIT_COMMIT, SOURCE_REL) == SOURCE_SHA256, "source-audit source blob mismatch")
    require(git_blob_sha256(SOURCE_AUDIT_COMMIT, SOURCE_AUDIT_REL) == SOURCE_AUDIT_SHA256, "source-audit verdict blob mismatch")
    return {
        "result_commit": RESULT_COMMIT,
        "result_parent_is_preregistration_commit": True,
        "preregistration_commit": AUDIT_PREREG_COMMIT,
        "manifest_commit": MANIFEST_COMMIT,
        "source_audit_commit": SOURCE_AUDIT_COMMIT,
        "working_head": git_output("rev-parse", "HEAD").decode().strip(),
    }


def verify_manifest_and_hashes(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    require(sha256_file(contained(MANIFEST_REL)) == MANIFEST_SHA256, "manifest SHA-256 mismatch")
    require(sha256_file(contained(RESULT_REL)) == RESULT_SHA256, "result SHA-256 mismatch")
    require(sha256_file(contained(SOURCE_REL)) == SOURCE_SHA256, "source SHA-256 mismatch")
    require(sha256_file(contained(AUDIT_PREREG_REL)) == AUDIT_PREREG_SHA256, "audit prereg SHA-256 mismatch")
    require(sha256_file(contained(SOURCE_AUDIT_REL)) == SOURCE_AUDIT_SHA256, "source audit SHA-256 mismatch")

    require(manifest.get("schema") == "max11-g0128-full-family-master-manifest-v2", "manifest schema")
    require(manifest.get("result") == "BOUND_380ROW_INPUTS_VALIDATED", "manifest result")
    require(manifest.get("rows") == ROWS and manifest.get("records") == RECORDS, "manifest dimensions")
    require(manifest.get("panel_rows") == PANEL_ROWS, "manifest panel rows")
    require(manifest.get("linear_rows") == LINEAR_ROWS, "manifest linear rows")
    require(manifest.get("accumulated_rows") == ACCUMULATED_ROWS, "manifest accumulated rows")
    require(manifest.get("old_batch_rows") == OLD_BATCH_ROWS, "manifest old batch rows")
    require(manifest.get("new_batch_rows") == NEW_BATCH_ROWS, "manifest new batch rows")
    require(manifest.get("initial_rank") == SEED_COLUMNS, "manifest initial rank")
    require(manifest.get("max_rank_increases") == ROWS - SEED_COLUMNS, "manifest rank ceiling")
    require(
        manifest.get("row_order")
        == [
            "panel:301",
            "linear:11",
            "accumulated:G-0117/G-0118:4",
            "batch:G-0118:32",
            "batch:G-0126:32",
        ],
        "manifest row order",
    )
    require(manifest.get("discarded_rows") == [], "manifest discarded rows")
    require(manifest.get("row_dependency_pivot_enrichment_columns") == [], "manifest pivot enrichment")
    require(manifest.get("complete_arithmetic_bridge") is True, "manifest arithmetic bridge")

    solver = manifest.get("solver")
    prereg = manifest.get("preregistration")
    ancestor = manifest.get("audited_ancestor")
    require(solver == {"path": SOURCE_REL, "sha256": SOURCE_SHA256}, "manifest solver binding")
    require(
        isinstance(prereg, dict)
        and prereg.get("path") == SOURCE_PREREG_REL
        and SHA256_RE.fullmatch(str(prereg.get("sha256"))) is not None,
        "manifest source preregistration binding",
    )
    require(
        ancestor
        == {
            "path": "artifacts/math/G-0123/full_family_master.py",
            "sha256": "dc77467b31c12b40eaec8b33bbe806d0c6f2ea8e2dac3f2731324deb3c1b9cac",
        },
        "manifest audited ancestor",
    )

    rows = manifest.get("expected_inputs")
    require(isinstance(rows, list) and len(rows) == 41, "manifest expected-input count")
    expected: dict[str, str] = {}
    resolved_seen: set[Path] = set()
    for index, row in enumerate(rows):
        require(isinstance(row, dict) and set(row) == {"path", "sha256"}, f"expected_inputs[{index}] shape")
        relative = row.get("path")
        digest = row.get("sha256")
        require(isinstance(relative, str) and isinstance(digest, str), f"expected_inputs[{index}] types")
        require(SHA256_RE.fullmatch(digest) is not None, f"expected_inputs[{index}] SHA-256")
        require(relative not in expected, f"duplicate expected input: {relative}")
        path = contained(relative)
        require(path not in resolved_seen, f"resolved duplicate expected input: {relative}")
        expected[relative] = digest
        resolved_seen.add(path)

    required = {
        PANEL_INPUT_REL,
        PANEL_SCAN_REL,
        CACHE_MANIFEST_REL,
        CACHE_REL,
        PRIOR_RESULT_REL,
        OLD_CANDIDATE_REL,
        OLD_SELECTION_REL,
        OLD_PRICE_REL,
        NEW_SELECTION_REL,
        NEW_PRICE_REL,
        *(relative for relative, _ in ACCUMULATED),
    }
    require(required.issubset(expected), f"manifest missing required inputs: {sorted(required - set(expected))}")
    require(expected[NEW_PRICE_REL] == manifest.get("g0127_price_receipt", {}).get("sha256"), "G-0127 binding")
    require(expected[NEW_SELECTION_REL] == manifest.get("g0126_receipt", {}).get("sha256"), "G-0126 binding")

    observed: dict[str, dict[str, Any]] = {}
    for relative, expected_digest in sorted(expected.items()):
        path = contained(relative)
        actual = sha256_file(path)
        require(actual == expected_digest, f"SHA-256 mismatch for {relative}: {actual}")
        observed[relative] = {"sha256": actual, "bytes": path.stat().st_size}

    extras = {
        RESULT_REL: RESULT_SHA256,
        MANIFEST_REL: MANIFEST_SHA256,
        SOURCE_REL: SOURCE_SHA256,
        SOURCE_AUDIT_REL: SOURCE_AUDIT_SHA256,
        AUDIT_PREREG_REL: AUDIT_PREREG_SHA256,
    }
    for relative, expected_digest in extras.items():
        path = contained(relative)
        actual = sha256_file(path)
        require(actual == expected_digest, f"SHA-256 mismatch for {relative}: {actual}")
        observed[relative] = {"sha256": actual, "bytes": path.stat().st_size}
    return observed


def read_panel_column(handle: Any, sequence: int) -> list[int]:
    offset = sequence * PANEL_ROWS * ENTRY_BYTES
    raw = os.pread(handle.fileno(), PANEL_ROWS * ENTRY_BYTES, offset)
    require(len(raw) == PANEL_ROWS * ENTRY_BYTES, f"truncated panel column {sequence}")
    return [
        int.from_bytes(raw[start : start + ENTRY_BYTES], "little", signed=True)
        for start in range(0, len(raw), ENTRY_BYTES)
    ]


def verify_panel(selected: Sequence[int]) -> tuple[list[list[int]], list[int], dict[str, Any]]:
    cache_manifest = load_json(CACHE_MANIFEST_REL)
    require(cache_manifest.get("schema") == "max11-g0117-full-family-panel-cache-v1", "cache schema")
    require(cache_manifest.get("records") == RECORDS, "cache records")
    require(cache_manifest.get("rows") == PANEL_ROWS, "cache rows")
    require(cache_manifest.get("entry_bytes") == ENTRY_BYTES, "cache entry bytes")
    require(cache_manifest.get("payload_bytes") == RECORDS * PANEL_ROWS * ENTRY_BYTES, "cache payload bytes")
    require(cache_manifest.get("layout") == "sequence-major: offset=((sequence*301)+row)*16", "cache layout")
    require(cache_manifest.get("integer_width") == "signed i128", "cache integer width")
    require(cache_manifest.get("endianness") == "little", "cache endianness")
    require(cache_manifest.get("data_sha256") == MANIFEST_INPUT_HASHES[CACHE_REL], "cache data binding")
    cache_path = contained(CACHE_REL)
    require(cache_path.stat().st_size == RECORDS * PANEL_ROWS * ENTRY_BYTES, "cache file size")

    controls = cache_manifest.get("control_vector_sha256")
    require(isinstance(controls, dict) and controls, "cache controls")
    with cache_path.open("rb") as handle:
        for raw_sequence, expected in controls.items():
            sequence = int(raw_sequence)
            column = read_panel_column(handle, sequence)
            require(
                sha256_bytes(b"".join(i128_bytes(value) for value in column)) == expected,
                f"cache control mismatch at {sequence}",
            )
        columns = [read_panel_column(handle, sequence) for sequence in selected]

    panel_input = load_json(PANEL_INPUT_REL)
    require(panel_input.get("schema") == "max11-g0113-panel-solver-input-v1", "panel input schema")
    target_raw = panel_input.get("target")
    require(isinstance(target_raw, list) and len(target_raw) == PANEL_ROWS, "panel target shape")
    target = [exact_json_int(value, f"panel target[{index}]") for index, value in enumerate(target_raw)]
    records = panel_input.get("records")
    require(isinstance(records, list) and len(records) == RECORDS, "panel record count")
    order = []
    for expected_sequence, record in enumerate(records):
        require(isinstance(record, dict), f"panel record {expected_sequence} shape")
        sequence = exact_json_int(record.get("sequence"), f"panel record {expected_sequence} sequence")
        require(sequence == expected_sequence, f"panel record order at {expected_sequence}")
        order.append(sequence)

    panel_scan = load_json(PANEL_SCAN_REL)
    require(panel_scan.get("records") == RECORDS, "panel scan records")
    i64_digest = digest_i64(target, "panel target")
    i128_digest = sha256_bytes(b"".join(i128_bytes(value) for value in target))
    require(panel_scan.get("target_i64_le_sha256") == i64_digest, "panel target i64 digest")
    require(panel_scan.get("target_i128_le_sha256") == i128_digest, "panel target i128 digest")
    return columns, target, {
        "cache_bytes": cache_path.stat().st_size,
        "cache_controls_checked": len(controls),
        "record_order_u64le_sha256": u64le_sha256(order),
        "target_i64le_sha256": i64_digest,
        "target_i128le_sha256": i128_digest,
    }


def audit_linear_vectors(
    vectors: Any, selected: Sequence[int], label: str
) -> tuple[str, list[list[int]]]:
    require(isinstance(vectors, list) and len(vectors) == RECORDS, f"{label}: vector count")
    selected_set = set(selected)
    chosen: dict[int, list[int]] = {}
    digest = hashlib.sha256()
    for sequence, raw in enumerate(vectors):
        require(isinstance(raw, list) and len(raw) == LINEAR_ROWS, f"{label}[{sequence}] shape")
        parsed = []
        for coordinate, value in enumerate(raw):
            integer = exact_json_int(value, f"{label}[{sequence}][{coordinate}]")
            digest.update(i64_bytes(integer, f"{label}[{sequence}][{coordinate}]"))
            parsed.append(integer)
        if sequence in selected_set:
            chosen[sequence] = parsed
    require(len(chosen) == len(selected), f"{label}: missing selected linears")
    return digest.hexdigest(), [chosen[sequence] for sequence in selected]


def verify_accumulated(
    selected: Sequence[int],
) -> tuple[list[list[int]], list[list[int]], str, list[dict[str, Any]]]:
    accumulated: list[list[int]] = []
    linear_reference: list[list[int]] | None = None
    linear_digest_reference: str | None = None
    summaries: list[dict[str, Any]] = []
    selected_set = set(selected)
    for relative, expected_direction in ACCUMULATED:
        payload = load_json(relative)
        require(payload.get("schema") == "max11-g0117-coordinate-price-v1", f"{relative}: schema")
        require(payload.get("result") == "EXACT_COORDINATE_PRICES", f"{relative}: result")
        require(payload.get("records") == RECORDS, f"{relative}: records")
        require(payload.get("direction") == expected_direction, f"{relative}: direction")
        raw = payload.get("hinge_coefficients")
        require(isinstance(raw, list) and len(raw) == RECORDS, f"{relative}: hinge count")
        chosen: dict[int, int] = {}
        digest = hashlib.sha256()
        nonzero = 0
        maximum = 0
        for sequence, value in enumerate(raw):
            integer = exact_json_int(value, f"{relative}: hinge[{sequence}]")
            digest.update(i64_bytes(integer, f"{relative}: hinge[{sequence}]"))
            if sequence in selected_set:
                chosen[sequence] = integer
            nonzero += integer != 0
            maximum = max(maximum, abs(integer))
        hinge_digest = digest.hexdigest()
        require(hinge_digest == payload.get("hinge_coefficients_i64_le_sha256"), f"{relative}: hinge digest")
        require(nonzero == payload.get("nonzero_hinge_coefficients"), f"{relative}: nonzero census")
        require(maximum == payload.get("maximum_hinge_coefficient"), f"{relative}: maximum")
        accumulated.append([chosen[sequence] for sequence in selected])

        linear_digest, linears = audit_linear_vectors(payload.get("linear_vectors"), selected, f"{relative}: linear")
        require(linear_digest == payload.get("linear_vectors_i64_le_sha256"), f"{relative}: linear digest")
        if linear_reference is None:
            linear_reference = linears
            linear_digest_reference = linear_digest
        else:
            require(linears == linear_reference, f"{relative}: selected linear drift")
            require(linear_digest == linear_digest_reference, f"{relative}: linear digest drift")
        summaries.append(
            {
                "path": relative,
                "direction": expected_direction,
                "hinge_i64le_sha256": hinge_digest,
                "linear_i64le_sha256": linear_digest,
                "nonzero_hinges": nonzero,
                "maximum_absolute_hinge": maximum,
            }
        )
        del payload, raw, linears
    assert linear_reference is not None and linear_digest_reference is not None
    return accumulated, linear_reference, linear_digest_reference, summaries


def parse_prior_candidate() -> tuple[list[tuple[int, int]], int, dict[str, Any]]:
    prior = load_json(PRIOR_RESULT_REL)
    require(prior.get("schema") == "max11-g0121-full-family-master-result-v1", "prior result schema")
    require(prior.get("result") == "FULL_FAMILY_EXACT_Q_MEMBER", "prior result branch")
    raw_terms = prior.get("terms")
    require(isinstance(raw_terms, list) and len(raw_terms) == 131, "prior term count")
    terms: list[tuple[int, int]] = []
    for index, term in enumerate(raw_terms):
        require(isinstance(term, dict) and set(term) == {"sequence", "coefficient"}, f"prior term {index}")
        sequence = exact_json_int(term.get("sequence"), f"prior term {index} sequence")
        coefficient = exact_decimal(term.get("coefficient"), f"prior term {index} coefficient")
        require(coefficient != 0 and 0 <= sequence < RECORDS, f"prior term {index} value")
        terms.append((sequence, coefficient))
    require([sequence for sequence, _ in terms] == sorted(sequence for sequence, _ in terms), "prior term order")
    scale = exact_decimal(prior.get("target_scale"), "prior target scale")
    require(scale > 0, "prior target scale sign")
    old_digest = prior.get("batch_exact_residuals_decimal_lf_sha256")
    require(isinstance(old_digest, str) and SHA256_RE.fullmatch(old_digest), "prior batch digest")
    return terms, scale, {"old_batch_residuals_decimal_lf_sha256": old_digest}


def parse_old_candidate() -> tuple[list[tuple[int, int]], int]:
    candidate = load_json(OLD_CANDIDATE_REL)
    require(
        candidate.get("schema") == "max11-g0118-prefix-exact-cegis-accumulated-v1",
        "old candidate schema",
    )
    require(
        candidate.get("result") == "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS",
        "old candidate result",
    )
    raw_terms = candidate.get("terms")
    require(isinstance(raw_terms, list) and len(raw_terms) == 102, "old candidate term count")
    terms: list[tuple[int, int]] = []
    for index, term in enumerate(raw_terms):
        require(
            isinstance(term, dict) and set(term) == {"sequence", "coefficient"},
            f"old candidate term {index}",
        )
        sequence = exact_json_int(term.get("sequence"), f"old candidate term {index} sequence")
        coefficient = exact_decimal(
            term.get("coefficient"), f"old candidate term {index} coefficient"
        )
        require(coefficient != 0 and 0 <= sequence < RECORDS, f"old candidate term {index} value")
        terms.append((sequence, coefficient))
    require(
        [sequence for sequence, _ in terms] == sorted(sequence for sequence, _ in terms),
        "old candidate term order",
    )
    scale = exact_decimal(candidate.get("target_scale"), "old candidate target scale")
    require(scale > 0, "old candidate target scale sign")
    return terms, scale


def verify_batch(
    *,
    selected_sequences: Sequence[int],
    linear_reference: Sequence[Sequence[int]],
    linear_digest_reference: str,
    selection_rel: str,
    price_rel: str,
    selection_schema: str,
    selection_result: str,
    price_schema: str,
    price_result: str,
    candidate_rel: str,
    candidate_terms: Sequence[tuple[int, int]],
    candidate_scale: int,
    expected_residual_digest: str,
    is_new: bool,
) -> tuple[list[list[int]], list[list[int]], dict[str, Any]]:
    selection = load_json(selection_rel)
    require(selection.get("schema") == selection_schema, f"{selection_rel}: schema")
    require(selection.get("result") == selection_result, f"{selection_rel}: result")
    require(selection.get("complete_global_replay") is True, f"{selection_rel}: completeness")
    require(selection.get("batch_k") == 32, f"{selection_rel}: batch K")
    require(selection.get("selected_count") == 32, f"{selection_rel}: selected count")
    bindings = selection.get("bindings")
    require(isinstance(bindings, dict), f"{selection_rel}: bindings")
    require(
        bindings.get("candidate") == MANIFEST_INPUT_HASHES[candidate_rel],
        f"{selection_rel}: candidate binding",
    )
    require(selection.get("terms") == len(candidate_terms), f"{selection_rel}: candidate term count")
    require(
        exact_decimal(selection.get("target_scale"), f"{selection_rel}: target scale")
        == candidate_scale,
        f"{selection_rel}: candidate target scale",
    )
    selected = selection.get("selected")
    require(isinstance(selected, list) and len(selected) == 32, f"{selection_rel}: selected shape")
    prefix_digest = selected_prefix_digest(selected)
    require(prefix_digest == selection.get("selected_prefix_i8_u64_le_sha256"), f"{selection_rel}: prefix digest")
    directions = [row.get("direction") for row in selected]
    residues = [row.get("residues") for row in selected]

    selection_residuals: list[int] | None = None
    if is_new:
        exact_rows = selection.get("exact_selected_prices")
        require(isinstance(exact_rows, list) and len(exact_rows) == 32, "G-0126 exact selected prices")
        selection_residuals = []
        for index, row in enumerate(exact_rows):
            require(isinstance(row, dict), f"G-0126 exact row {index}")
            require(row.get("direction") == directions[index], f"G-0126 exact direction {index}")
            require(row.get("modular_residues") == residues[index], f"G-0126 exact residues {index}")
            selection_residuals.append(exact_decimal(row.get("exact_residual"), f"G-0126 residual {index}"))
        require(
            decimal_lf_sha256(selection_residuals)
            == selection.get("exact_selected_prices_decimal_lf_sha256"),
            "G-0126 exact residual digest",
        )

    price = load_json(price_rel)
    require(price.get("schema") == price_schema, f"{price_rel}: schema")
    require(price.get("result") == price_result, f"{price_rel}: result")
    require(price.get("batch_k") == 32, f"{price_rel}: batch K")
    require(price.get("selected_count") == 32, f"{price_rel}: selected count")
    require(price.get("records") == RECORDS, f"{price_rel}: record count")
    require(price.get("directions") == directions, f"{price_rel}: direction order")
    require(price.get("modular_residues") == residues, f"{price_rel}: residue order")
    if is_new:
        require(price.get("selected_prefix_i8_u64_le_sha256") == prefix_digest, f"{price_rel}: prefix binding")
        require(price.get("hinge_entries") == 32 * RECORDS, "G-0127 hinge entry count")
        require(price.get("linear_entries") == RECORDS * LINEAR_ROWS, "G-0127 linear entry count")

    rows = price.get("rows")
    require(isinstance(rows, list) and len(rows) == 32, f"{price_rel}: row count")
    selected_set = set(selected_sequences)
    aggregate = hashlib.sha256()
    selected_hinges: list[list[int]] = []
    candidate_residuals: list[int] = []
    row_summaries: list[dict[str, Any]] = []
    term_sequences = {sequence for sequence, _ in candidate_terms}
    require(term_sequences.issubset(selected_set), f"{price_rel}: prior terms outside selected audit basis")

    for row_index, row in enumerate(rows):
        require(isinstance(row, dict), f"{price_rel}: row {row_index} shape")
        require(row.get("direction") == directions[row_index], f"{price_rel}: direction {row_index}")
        require(row.get("modular_residues") == residues[row_index], f"{price_rel}: residues {row_index}")
        if is_new:
            require(row.get("records") == RECORDS, f"{price_rel}: records {row_index}")
        raw = row.get("hinge_coefficients")
        require(isinstance(raw, list) and len(raw) == RECORDS, f"{price_rel}: hinge count {row_index}")
        chosen: dict[int, int] = {}
        digest = hashlib.sha256()
        nonzero = 0
        minimum: int | None = None
        maximum: int | None = None
        maximum_abs = 0
        for sequence, value in enumerate(raw):
            integer = exact_json_int(value, f"{price_rel}: hinge[{row_index}][{sequence}]")
            packed = i64_bytes(integer, f"{price_rel}: hinge[{row_index}][{sequence}]")
            digest.update(packed)
            aggregate.update(packed)
            if sequence in selected_set:
                chosen[sequence] = integer
            nonzero += integer != 0
            minimum = integer if minimum is None else min(minimum, integer)
            maximum = integer if maximum is None else max(maximum, integer)
            maximum_abs = max(maximum_abs, abs(integer))
        row_digest = digest.hexdigest()
        require(row_digest == row.get("hinge_coefficients_i64_le_sha256"), f"{price_rel}: row digest {row_index}")
        require(nonzero == row.get("nonzero_hinge_coefficients"), f"{price_rel}: nonzero {row_index}")
        if is_new:
            require(minimum == row.get("minimum_hinge_coefficient"), f"{price_rel}: minimum {row_index}")
            require(maximum == row.get("maximum_hinge_coefficient"), f"{price_rel}: maximum {row_index}")
            require(maximum_abs == row.get("maximum_absolute_hinge_coefficient"), f"{price_rel}: abs maximum {row_index}")
        else:
            require(maximum_abs == row.get("maximum_hinge_coefficient"), f"{price_rel}: maximum {row_index}")
        require(len(chosen) == len(selected_sequences), f"{price_rel}: selected values {row_index}")
        chosen_row = [chosen[sequence] for sequence in selected_sequences]
        selected_hinges.append(chosen_row)
        candidate_dot = sum(coefficient * chosen[sequence] for sequence, coefficient in candidate_terms)
        candidate_residuals.append(candidate_dot)
        if is_new:
            require(
                exact_decimal(row.get("exact_candidate_residual"), f"{price_rel}: row residual {row_index}")
                == candidate_dot,
                f"{price_rel}: row residual mismatch {row_index}",
            )
        row_summaries.append(
            {
                "index": row_index,
                "direction": directions[row_index],
                "hinge_i64le_sha256": row_digest,
                "nonzero_hinges": nonzero,
                "minimum_hinge": minimum,
                "maximum_hinge": maximum,
                "maximum_absolute_hinge": maximum_abs,
                "candidate_residual": str(candidate_dot),
            }
        )
        del raw, chosen, chosen_row

    aggregate_digest = aggregate.hexdigest()
    require(aggregate_digest == price.get("direction_major_hinge_i64_le_sha256"), f"{price_rel}: aggregate digest")
    residual_digest = decimal_lf_sha256(candidate_residuals)
    require(residual_digest == expected_residual_digest, f"{price_rel}: candidate residual digest")
    if is_new:
        require(selection_residuals == candidate_residuals, "G-0126/G-0127 exact residual mismatch")
        require(price.get("exact_candidate_residuals") == [str(value) for value in candidate_residuals], "G-0127 residual list")
        require(price.get("exact_candidate_residuals_decimal_lf_sha256") == residual_digest, "G-0127 residual digest field")
        require(all(value != 0 for value in candidate_residuals), "prior candidate did not fail every new row")

    linear_digest, selected_linears = audit_linear_vectors(
        price.get("linear_vectors"), selected_sequences, f"{price_rel}: linear"
    )
    require(linear_digest == price.get("linear_vectors_i64_le_sha256"), f"{price_rel}: linear digest")
    require(linear_digest == linear_digest_reference, f"{price_rel}: accumulated linear digest drift")
    require(selected_linears == list(linear_reference), f"{price_rel}: selected linear drift")
    selected_index = {sequence: index for index, sequence in enumerate(selected_sequences)}
    linear_dots = [
        sum(
            coefficient * selected_linears[selected_index[sequence]][coordinate]
            for sequence, coefficient in candidate_terms
        )
        for coordinate in range(LINEAR_ROWS)
    ]
    require(linear_dots[:10] == [0] * 10, f"{price_rel}: candidate linear dots 0..9")
    require(linear_dots[10] == candidate_scale * math.factorial(11), f"{price_rel}: candidate linear dot 10")
    if is_new:
        require(price.get("exact_candidate_linear_dots") == [str(value) for value in linear_dots], "G-0127 linear dots")

    return selected_hinges, directions, {
        "selection_path": selection_rel,
        "price_path": price_rel,
        "selected_prefix_i8_u64_le_sha256": prefix_digest,
        "direction_major_hinge_i64_le_sha256": aggregate_digest,
        "linear_vectors_i64_le_sha256": linear_digest,
        "candidate_residuals_decimal_lf_sha256": residual_digest,
        "candidate_residuals_all_nonzero": all(value != 0 for value in candidate_residuals),
        "candidate_linear_dots": [str(value) for value in linear_dots],
        "rows": row_summaries,
    }


def parse_result(
    result: dict[str, Any], manifest: dict[str, Any]
) -> dict[str, Any]:
    expected_keys = {
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
    require(set(result) == expected_keys, f"result key set drift: {sorted(set(result) ^ expected_keys)}")
    require(result.get("schema") == "max11-g0128-full-family-master-result-v2", "result schema")
    require(result.get("result") == "FULL_FAMILY_380ROW_EXACT_Q_MEMBER", "result branch")
    require(result.get("manifest_path") == MANIFEST_REL, "result manifest path")
    require(result.get("manifest_sha256") == MANIFEST_SHA256, "result manifest digest")
    require(result.get("solver_sha256") == SOURCE_SHA256, "result solver digest")
    require(
        result.get("audited_ancestor_sha256")
        == manifest.get("audited_ancestor", {}).get("sha256"),
        "result audited ancestor",
    )
    require(result.get("rows") == ROWS and result.get("records") == RECORDS, "result dimensions")
    require(result.get("rank") == SELECTED_COLUMNS, "result rank")
    require(result.get("augmented_rank") == SELECTED_COLUMNS, "result augmented rank")
    require(result.get("all_380_rows_replayed") is True, "result all-row flag")
    require(result.get("coefficient_plus_one_mutant_rejected") is True, "result mutant flag")
    require(result.get("prior_candidate_rejected_on_all_32_new_rows") is True, "result prior-candidate flag")
    require(
        result.get("new_selected_prefix_i8_u64_le_sha256")
        == manifest.get("new_selected_prefix_i8_u64_le_sha256"),
        "result new-prefix binding",
    )
    require(
        result.get("new_exact_residuals_decimal_lf_sha256")
        == manifest.get("new_exact_residuals_decimal_lf_sha256"),
        "result new-residual binding",
    )
    require(
        result.get("old_batch_residuals_decimal_lf_sha256")
        == manifest.get("old_batch_residuals_decimal_lf_sha256"),
        "result old-residual binding",
    )

    selected = validate_sequences(result.get("selected_sequences"), "selected_sequences", SELECTED_COLUMNS)
    basis_support = validate_sequences(result.get("support_sequences"), "support_sequences", SELECTED_COLUMNS)
    require(selected == sorted(selected), "selected sequences are not increasing")
    require(basis_support == selected, "support_sequences differs from selected basis")
    seed = validate_sequences(manifest.get("seed_sequences"), "manifest seed_sequences", SEED_COLUMNS)
    require(seed == sorted(seed), "manifest seed order")

    raw_coefficients = result.get("integer_coefficients")
    require(
        isinstance(raw_coefficients, list) and len(raw_coefficients) == SELECTED_COLUMNS,
        "integer coefficient shape",
    )
    coefficients = [
        exact_decimal(value, f"integer_coefficients[{index}]")
        for index, value in enumerate(raw_coefficients)
    ]
    scale = exact_decimal(result.get("target_scale"), "target_scale")
    require(scale > 0, "target scale sign")
    normalization_gcd = abs(scale)
    for coefficient in coefficients:
        normalization_gcd = math.gcd(normalization_gcd, abs(coefficient))
    require(normalization_gcd == 1, f"coefficient/scale gcd is {normalization_gcd}")
    expected_terms = [
        {"coefficient": raw, "sequence": sequence}
        for sequence, raw, coefficient in zip(selected, raw_coefficients, coefficients, strict=True)
        if coefficient != 0
    ]
    require(result.get("terms") == expected_terms, "terms differ from exact nonzero coefficient support")
    term_support = [row["sequence"] for row in expected_terms]
    require(term_support == sorted(set(term_support)), "mathematical term support order")

    coordinate_rows_raw = result.get("coordinate_rows")
    require(isinstance(coordinate_rows_raw, list), "coordinate rows missing")
    coordinate_rows = [
        exact_json_int(value, f"coordinate_rows[{index}]")
        for index, value in enumerate(coordinate_rows_raw)
    ]
    require(len(coordinate_rows) == SELECTED_COLUMNS, "coordinate row count")
    require(coordinate_rows == sorted(set(coordinate_rows)), "coordinate rows not sorted unique")
    require(all(0 <= row < ROWS for row in coordinate_rows), "coordinate row out of range")

    trials = result.get("trials")
    require(isinstance(trials, list) and len(trials) == RANK_TRIALS, "trial count")
    appended: list[int] = []
    for iteration, trial in enumerate(trials):
        require(isinstance(trial, dict), f"trial {iteration} shape")
        require(trial.get("iteration") == iteration, f"trial {iteration} index")
        if iteration < RANK_TRIALS - 1:
            require(
                set(trial)
                == {
                    "iteration",
                    "rank",
                    "augmented_rank",
                    "result",
                    "separator_target_pairing",
                    "separator_free_row",
                    "first_violating_sequence",
                    "first_violating_price",
                    "columns_scanned",
                },
                f"trial {iteration} key set",
            )
            require(trial.get("result") == "SEPARATOR_VIOLATED", f"trial {iteration} result")
            require(trial.get("rank") == SEED_COLUMNS + iteration, f"trial {iteration} rank label")
            require(trial.get("augmented_rank") == SEED_COLUMNS + iteration + 1, f"trial {iteration} augmented label")
            sequence = exact_json_int(trial.get("first_violating_sequence"), f"trial {iteration} sequence")
            require(trial.get("columns_scanned") == sequence + 1, f"trial {iteration} scan census")
            require(exact_decimal(trial.get("first_violating_price"), f"trial {iteration} price") != 0, f"trial {iteration} zero price")
            require(
                exact_decimal(trial.get("separator_target_pairing"), f"trial {iteration} pairing") != 0,
                f"trial {iteration} zero target pairing",
            )
            free_row = exact_json_int(trial.get("separator_free_row"), f"trial {iteration} free row")
            require(0 <= free_row < ROWS, f"trial {iteration} free row")
            appended.append(sequence)
        else:
            require(set(trial) == {"iteration", "rank", "augmented_rank", "result"}, "final trial key set")
            require(trial.get("result") == "EXACT_Q_MEMBER", "final trial result")
            require(trial.get("rank") == SELECTED_COLUMNS, "final trial rank")
            require(trial.get("augmented_rank") == SELECTED_COLUMNS, "final trial augmented rank")
    require(len(set(seed + appended)) == SELECTED_COLUMNS, "seed/appended transcript duplicates")
    require(sorted(seed + appended) == selected, "seed/appended transcript union")

    return {
        "selected": selected,
        "basis_support": basis_support,
        "term_support": term_support,
        "coefficients": coefficients,
        "raw_coefficients": raw_coefficients,
        "scale": scale,
        "normalization_gcd": normalization_gcd,
        "coordinate_rows": coordinate_rows,
        "trials": trials,
        "seed": seed,
        "appended": appended,
        "terms": expected_terms,
    }


MANIFEST_INPUT_HASHES: dict[str, str] = {}


def run_audit() -> dict[str, Any]:
    started = time.monotonic()
    git_custody = verify_git_custody()
    manifest = load_json(MANIFEST_REL)
    observed_start = verify_manifest_and_hashes(manifest)
    global MANIFEST_INPUT_HASHES
    MANIFEST_INPUT_HASHES = {
        relative: row["sha256"]
        for relative, row in observed_start.items()
        if relative not in {RESULT_REL, MANIFEST_REL, SOURCE_REL, AUDIT_PREREG_REL}
    }
    result = load_json(RESULT_REL)
    transcript = parse_result(result, manifest)
    selected = transcript["selected"]

    prior_terms, prior_scale, prior_summary = parse_prior_candidate()
    old_terms, old_scale = parse_old_candidate()
    require(
        prior_summary["old_batch_residuals_decimal_lf_sha256"]
        == manifest.get("old_batch_residuals_decimal_lf_sha256"),
        "prior/manifest old residual digest",
    )

    panel_columns, panel_target, panel_summary = verify_panel(selected)
    accumulated, selected_linears, linear_digest, accumulated_summary = verify_accumulated(selected)
    old_batch, old_directions, old_summary = verify_batch(
        selected_sequences=selected,
        linear_reference=selected_linears,
        linear_digest_reference=linear_digest,
        selection_rel=OLD_SELECTION_REL,
        price_rel=OLD_PRICE_REL,
        selection_schema="max11-g0118-batch32-global-modular-replay-v1",
        selection_result="BATCH_RESIDUAL_PREFIX_SELECTED",
        price_schema="max11-g0118-batch32-coordinate-price-v1",
        price_result="EXACT_BATCH_COORDINATE_PRICES",
        candidate_rel=OLD_CANDIDATE_REL,
        candidate_terms=old_terms,
        candidate_scale=old_scale,
        expected_residual_digest=manifest["old_batch_residuals_decimal_lf_sha256"],
        is_new=False,
    )
    new_batch, new_directions, new_summary = verify_batch(
        selected_sequences=selected,
        linear_reference=selected_linears,
        linear_digest_reference=linear_digest,
        selection_rel=NEW_SELECTION_REL,
        price_rel=NEW_PRICE_REL,
        selection_schema="max11-g0126-global-replay-v1",
        selection_result="GLOBAL_MODULAR_RESIDUAL",
        price_schema="max11-g0127-batch32-coordinate-prices-v1",
        price_result="EXACT_FULL_FAMILY_BATCH32_COORDINATES",
        candidate_rel=PRIOR_RESULT_REL,
        candidate_terms=prior_terms,
        candidate_scale=prior_scale,
        expected_residual_digest=manifest["new_exact_residuals_decimal_lf_sha256"],
        is_new=True,
    )

    expected_directions = [direction for _, direction in ACCUMULATED] + old_directions + new_directions
    require(len(expected_directions) == 68, "hinge direction total")
    require(result.get("hinge_directions") == expected_directions, "result hinge direction order")
    decisions = manifest.get("batch_row_decisions")
    require(isinstance(decisions, list) and len(decisions) == 64, "manifest batch decisions")
    for index, row in enumerate(decisions):
        require(isinstance(row, dict), f"batch decision {index}")
        expected_new = index >= 32
        local_index = index - 32 if expected_new else index
        require(row.get("decision") == "KEPT_CONSERVATIVELY", f"batch decision {index} label")
        require(row.get("row_index") == 316 + index, f"batch decision {index} row")
        require(row.get("receipt_index") == local_index, f"batch decision {index} receipt index")
        expected_direction = new_directions[local_index] if expected_new else old_directions[local_index]
        require(row.get("direction") == expected_direction, f"batch decision {index} direction")
        require(
            row.get("price_receipt") == (NEW_PRICE_REL if expected_new else OLD_PRICE_REL),
            f"batch decision {index} price source",
        )
        require(
            row.get("selection_receipt") == (NEW_SELECTION_REL if expected_new else OLD_SELECTION_REL),
            f"batch decision {index} selection source",
        )

    columns: list[list[int]] = []
    for column_index in range(SELECTED_COLUMNS):
        column = (
            panel_columns[column_index]
            + selected_linears[column_index]
            + [row[column_index] for row in accumulated]
            + [row[column_index] for row in old_batch]
            + [row[column_index] for row in new_batch]
        )
        require(len(column) == ROWS, f"reconstructed column {column_index} row count")
        columns.append(column)
    target = panel_target + [0] * 10 + [math.factorial(11)] + [0] * 68
    require(len(target) == ROWS, "target row count")
    require(manifest.get("target") == target, "manifest target differs from independent reconstruction")

    residuals = identity_residuals(columns, transcript["coefficients"], target, transcript["scale"])
    nonzero_rows = [index for index, value in enumerate(residuals) if value]
    require(not nonzero_rows, f"exact identity first fails at row {nonzero_rows[0] if nonzero_rows else 'unknown'}")

    first_nonzero = next(index for index, value in enumerate(transcript["coefficients"]) if value)
    mutant_coefficients = list(transcript["coefficients"])
    mutant_coefficients[first_nonzero] += 1
    mutant_residuals = identity_residuals(columns, mutant_coefficients, target, transcript["scale"])
    mutant_rows = [index for index, value in enumerate(mutant_residuals) if value]
    require(mutant_rows, "coefficient +1 mutant survived")

    coordinate_rows = transcript["coordinate_rows"]
    reported_basis_digest = result.get("selected_basis_i128le_sha256")
    require(isinstance(reported_basis_digest, str) and SHA256_RE.fullmatch(reported_basis_digest), "basis digest field")
    full_row_major = digest_matrix_i128(columns, list(range(ROWS)), row_major=True)
    full_column_major = digest_matrix_i128(columns, list(range(ROWS)), row_major=False)
    coordinate_row_major = digest_matrix_i128(columns, coordinate_rows, row_major=True)
    coordinate_column_major = digest_matrix_i128(columns, coordinate_rows, row_major=False)
    require(full_row_major == reported_basis_digest, "selected basis digest mismatch")
    require(
        reported_basis_digest
        not in {full_column_major, coordinate_row_major, coordinate_column_major},
        "basis digest serialization not unique among controls",
    )
    square = [
        [columns[column][row] for column in range(SELECTED_COLUMNS)]
        for row in coordinate_rows
    ]
    square_rank = int(fmpz_mat(square).rank())
    require(square_rank == SELECTED_COLUMNS, f"coordinate square rank {square_rank}")
    coordinate_identity = [
        sum(
            transcript["coefficients"][column] * square[row][column]
            for column in range(SELECTED_COLUMNS)
        )
        - transcript["scale"] * target[coordinate_rows[row]]
        for row in range(SELECTED_COLUMNS)
    ]
    require(coordinate_identity == [0] * SELECTED_COLUMNS, "final coefficient solve fails coordinate square")

    column_by_sequence = dict(zip(selected, columns, strict=True))
    rank_receipts: list[dict[str, Any]] = []
    previous_rank: int | None = None
    for iteration, trial in enumerate(transcript["trials"]):
        trial_sequences = transcript["seed"] + transcript["appended"][:iteration]
        trial_columns = [column_by_sequence[sequence] for sequence in trial_sequences]
        rank_started = time.monotonic()
        rank, augmented = rank_pair(trial_columns, target)
        require(rank == trial.get("rank"), f"trial {iteration} exact rank mismatch")
        require(augmented == trial.get("augmented_rank"), f"trial {iteration} exact augmented-rank mismatch")
        if previous_rank is not None:
            require(rank == previous_rank + 1, f"trial {iteration} did not grow rank by one")
        previous_rank = rank
        rank_receipts.append(
            {
                "iteration": iteration,
                "columns": len(trial_sequences),
                "rank": rank,
                "augmented_rank": augmented,
                "wall_seconds": time.monotonic() - rank_started,
            }
        )
    require(
        rank_receipts[-1]["rank"] == rank_receipts[-1]["augmented_rank"] == SELECTED_COLUMNS,
        "final exact membership rank",
    )

    payload_digest = canonical_json_sha256(
        {
            "selected_sequences": selected,
            "support_sequences": transcript["basis_support"],
            "integer_coefficients": transcript["raw_coefficients"],
            "target_scale": str(transcript["scale"]),
            "terms": transcript["terms"],
            "coordinate_rows": coordinate_rows,
            "trials": transcript["trials"],
        }
    )
    transcript_digest = canonical_json_sha256(transcript["trials"])
    coefficient_decimal_lf_digest = decimal_lf_sha256(transcript["coefficients"])
    selected_u64le_digest = u64le_sha256(selected)
    term_support_u64le_digest = u64le_sha256(transcript["term_support"])
    target_decimal_lf_digest = decimal_lf_sha256(target)

    end_paths = sorted(observed_start)
    observed_end: dict[str, dict[str, Any]] = {}
    for relative in end_paths:
        path = contained(relative)
        digest = sha256_file(path)
        require(digest == observed_start[relative]["sha256"], f"input drift during audit: {relative}")
        require(path.stat().st_size == observed_start[relative]["bytes"], f"input size drift during audit: {relative}")
        observed_end[relative] = {"sha256": digest, "bytes": path.stat().st_size}

    basis_support_is_term_support = transcript["basis_support"] == transcript["term_support"]
    schema_notes = []
    if not basis_support_is_term_support:
        schema_notes.append(
            {
                "code": "SUPPORT_SEQUENCES_IS_BASIS_AXIS",
                "severity": "NOTE",
                "detail": (
                    f"support_sequences contains all {len(transcript['basis_support'])} selected pivot columns, "
                    f"including {len(transcript['basis_support']) - len(transcript['term_support'])} zero "
                    f"coefficients; the exact mathematical support is the canonical {len(transcript['term_support'])}-term terms list"
                ),
                "load_bearing_for_identity": False,
            }
        )

    return {
        "schema": "max11-g0131-cleanroom-380row-member-audit-v1",
        "verdict": "CONSISTENT_MEMBER",
        "mathematical_certificate_verdict": "CONSISTENT",
        "tier_boundary": "Fresh-context same OpenAI GPT-5 lineage: at most T1.",
        "claim_boundary": (
            "Exact consistency only on the frozen 380-row system over the frozen 163,740-column family; "
            "not a global identity, MAX11 settlement, unrestricted network theorem, family-completeness "
            "theorem, or Lean theorem. A separately committed preregistration is required before global replay."
        ),
        "custody": {
            "git": git_custody,
            "source_sha256": SOURCE_SHA256,
            "source_audit_commit": SOURCE_AUDIT_COMMIT,
            "manifest_sha256": MANIFEST_SHA256,
            "result_sha256": RESULT_SHA256,
            "audit_preregistration_sha256": AUDIT_PREREG_SHA256,
            "files_rehashed_at_start": len(observed_start),
            "files_rehashed_at_end": len(observed_end),
            "hashes_at_start": observed_start,
            "hashes_at_end": observed_end,
        },
        "environment": {
            "python": sys.version,
            "python_flint": getattr(flint, "__version__", "unknown"),
            "checker_sha256": sha256_file(Path(__file__).resolve()),
        },
        "dimensions": {
            "family_records": RECORDS,
            "rows": ROWS,
            "panel_rows": PANEL_ROWS,
            "linear_rows": LINEAR_ROWS,
            "accumulated_hinge_rows": ACCUMULATED_ROWS,
            "old_batch_hinge_rows": OLD_BATCH_ROWS,
            "new_batch_hinge_rows": NEW_BATCH_ROWS,
            "selected_columns": SELECTED_COLUMNS,
            "nonzero_terms": len(transcript["term_support"]),
            "zero_selected_coefficients": SELECTED_COLUMNS - len(transcript["term_support"]),
            "rank_trials": RANK_TRIALS,
        },
        "normalization": {
            "target_scale": str(transcript["scale"]),
            "target_scale_positive": transcript["scale"] > 0,
            "coefficient_and_scale_gcd": transcript["normalization_gcd"],
        },
        "support_and_coefficients": {
            "selected_equals_support_sequences": transcript["selected"] == transcript["basis_support"],
            "support_sequences_equals_nonzero_term_support": basis_support_is_term_support,
            "selected_sequences_u64le_sha256": selected_u64le_digest,
            "term_support_u64le_sha256": term_support_u64le_digest,
            "integer_coefficients_decimal_lf_sha256": coefficient_decimal_lf_digest,
            "certificate_payload_canonical_json_sha256": payload_digest,
            "transcript_canonical_json_sha256": transcript_digest,
        },
        "identity": {
            "all_380_rows_zero": True,
            "nonzero_residual_rows": nonzero_rows,
            "target_decimal_lf_sha256": target_decimal_lf_digest,
            "target_final_linear_coordinate": math.factorial(11),
            "target_other_added_coordinates_zero": True,
            "coordinate_square_solve_zero": True,
        },
        "mutant": {
            "kind": "add one to first nonzero integer coefficient",
            "selected_position": first_nonzero,
            "sequence": selected[first_nonzero],
            "rejected": True,
            "first_mismatch_row": mutant_rows[0],
            "first_mismatch_residual": str(mutant_residuals[mutant_rows[0]]),
            "mismatch_row_count": len(mutant_rows),
        },
        "selected_basis": {
            "reported_sha256": reported_basis_digest,
            "full_380_by_176_row_major_i128le_sha256": full_row_major,
            "full_380_by_176_column_major_i128le_control_sha256": full_column_major,
            "coordinate_square_row_major_i128le_control_sha256": coordinate_row_major,
            "coordinate_square_column_major_i128le_control_sha256": coordinate_column_major,
            "coordinate_row_count": len(coordinate_rows),
            "coordinate_square_rank": square_rank,
            "matches_reported": True,
        },
        "rank_trials": rank_receipts,
        "panel": panel_summary,
        "accumulated_rows": accumulated_summary,
        "old_batch": old_summary,
        "new_batch": new_summary,
        "schema_notes": schema_notes,
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
    require(args.output is not None, "audit run requires --output")
    output = args.output if args.output.is_absolute() else ROOT / args.output
    receipt = run_audit()
    write_exclusive(output, receipt)
    print(
        json.dumps(
            {
                "verdict": receipt["verdict"],
                "certificate": receipt["mathematical_certificate_verdict"],
                "output": str(output),
            }
        )
    )


if __name__ == "__main__":
    try:
        main()
    except AuditFailure as exc:
        print(f"AUDIT_FAIL: {exc}", file=sys.stderr)
        raise SystemExit(2)
