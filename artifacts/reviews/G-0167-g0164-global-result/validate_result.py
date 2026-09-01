#!/usr/bin/env python3
"""Strict read-only validator for the frozen G-0164 global replay result.

The validator reads subject files from their Git objects.  The only working-tree scientific input
it reads is a finite-manifest SHA-256-bound payload that is absent from Git; that fact is reported
as a durability limitation.  It never invokes the production executable or any production mode.
"""

from __future__ import annotations

import argparse
import copy
import dataclasses
import datetime as dt
import decimal
import fractions
import hashlib
import json
import math
import os
import pathlib
import struct
import subprocess
import tempfile
import time
from collections.abc import Iterable, Mapping, Sequence
from typing import Any


MANIFEST_COMMIT = "bd64ece4a5ad17c77e80f3f2f2dfd2a0b27da243"
RESULT_COMMIT = "1a16346519c11d4616a10a2738a70aa935643053"
PREREG_COMMIT = "b749986"
GLOBAL_MANIFEST_PATH = "artifacts/math/G-0164/all128_global_replay_manifest_v1.json"
RESULT_PATH = "artifacts/math/G-0164/all128_global_replay_v1.json"
FINITE_MANIFEST_PATH = "artifacts/math/G-0164/all128_manifest_v1.json"
MEMBER_PATH = "artifacts/math/G-0164/all128_direct_basis_member_v1.json"
PANEL_PATH = "artifacts/math/G-0113/panel_solver_input_v1.json"
STAGE_A_PATH = "artifacts/math/G-0140/pool128_global_replay_v1.json"
CACHE_PATH = "artifacts/math/G-0117/full_family_cache_v1.i128le"
PREREG_PATH = "artifacts/reviews/G-0167-g0164-global-result/PREREGISTRATION.md"
CPP_PATH = "artifacts/reviews/G-0167-g0164-global-result/independent_exact_route.cpp"
VALIDATOR_PATH = "artifacts/reviews/G-0167-g0164-global-result/validate_result.py"

N = 11
PANEL_ROWS = 301
LINEAR_ROWS = 11
ACCUMULATED_ROWS = 228
ROWS = 540
RANK = 349
RECORDS = 163_740
FACTORIAL_11 = math.factorial(11)
PREFIX_K = 128

RESULT_KEYS = {
    "schema", "result", "claim_boundary", "global_manifest", "finite_manifest",
    "finite_member", "preregistration", "producer_source", "candidate_source",
    "producer_engine", "producer_cargo_manifest", "producer_cargo_lock",
    "g0117_cargo_manifest", "g0117_lib_source", "producer_executable", "source_audit",
    "parent_replay_source", "parent_replay_engine", "parent_source_audit",
    "source_and_audit_bindings", "candidate_schema", "candidate_result", "base_rows",
    "appended_rows", "rows", "records", "selected_pool_indices", "selected_directions",
    "selected_directions_i8_sha256", "rank", "basis_coordinates", "support_columns",
    "terms", "target_scale", "target_subtraction_coordinate_10",
    "finite_all_rational_rows_replayed", "finite_all_integer_rows_replayed",
    "finite_primitive_denominator_clearing", "finite_coefficient_plus_one_mutant_rejected",
    "independent_finite_replay", "arithmetic", "decision_rule", "complete_global_replay",
    "all_hinge_and_linear_residuals_zero", "labelled_permutations_expected",
    "labelled_permutations_checked", "hinge_entries_processed", "aggregate_hinge_support",
    "nonzero_hinge_directions", "aggregate_hinge_decimal_lf_sha256",
    "nonzero_hinge_decimal_lf_sha256", "complete_residual_decimal_lf_sha256",
    "term_normal_form_transcript_sha256", "term_normal_forms",
    "accumulated_direction_checks", "inherited_accumulated_directions",
    "selected_accumulated_directions", "accumulated_direction_count",
    "all_accumulated_directions_exact_zero", "linear_residuals_after_target",
    "all_11_linear_residuals_exact_zero", "first_nonzero_hinge", "first_nonzero_linear",
    "residual_prefix_k", "residual_prefix_count", "residual_prefix_directions_i8_sha256",
    "residual_prefix_exact_residuals_decimal_lf_sha256", "residual_prefix",
    "no_automatic_next_study", "coefficient_plus_one", "target_scale_plus_one",
    "target_coordinate_plus_one", "omitted_final_term", "omitted_first_term_direction",
    "census_controls", "prefix_controls", "inputs_rehashed_at_end",
    "manifest_rehashed_at_end", "candidate_rehashed_at_end", "wall_seconds",
}


class AuditFailure(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message


def require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise AuditFailure(code, message)


def run(command: Sequence[str], *, cwd: pathlib.Path, input_bytes: bytes | None = None,
        timeout: int = 1800, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    completed = subprocess.run(
        list(command), cwd=cwd, input=input_bytes, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, timeout=timeout, check=False,
    )
    if check and completed.returncode != 0:
        raise AuditFailure(
            "COMMAND_FAILED",
            f"{command!r} exited {completed.returncode}; stderr={completed.stderr.decode(errors='replace')}",
        )
    return completed


def git(root: pathlib.Path, *arguments: str, check: bool = True) -> bytes:
    return run(["git", *arguments], cwd=root, check=check).stdout


def git_blob(root: pathlib.Path, commit: str, path: str) -> bytes:
    completed = run(["git", "cat-file", "blob", f"{commit}:{path}"], cwd=root, check=False)
    if completed.returncode != 0:
        raise AuditFailure("MISSING_GIT_BLOB", f"{commit}:{path}")
    return completed.stdout


def git_blob_exists(root: pathlib.Path, commit: str, path: str) -> bool:
    return run(["git", "cat-file", "-e", f"{commit}:{path}"], cwd=root, check=False).returncode == 0


def git_blob_id(root: pathlib.Path, commit: str, path: str) -> str:
    return git(root, "rev-parse", f"{commit}:{path}").decode().strip()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: pathlib.Path) -> tuple[str, int]:
    digest = hashlib.sha256()
    length = 0
    with path.open("rb") as handle:
        while chunk := handle.read(8 * 1024 * 1024):
            digest.update(chunk)
            length += len(chunk)
    return digest.hexdigest(), length


def strict_json(raw: bytes, label: str) -> Any:
    def pairs(items: list[tuple[str, Any]]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for key, value in items:
            if key in output:
                raise AuditFailure("JSON_DUPLICATE_KEY", f"{label}: {key}")
            output[key] = value
        return output

    def constant(value: str) -> Any:
        raise AuditFailure("JSON_NONFINITE", f"{label}: {value}")

    try:
        return json.loads(
            raw, object_pairs_hook=pairs, parse_float=decimal.Decimal,
            parse_constant=constant,
        )
    except AuditFailure:
        raise
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise AuditFailure("JSON_PARSE", f"{label}: {error}") from error


def canonical_integer(raw: Any, *, nonzero: bool = False, positive: bool = False) -> int:
    require(isinstance(raw, str), "INTEGER_ENCODING", f"not a string: {raw!r}")
    require(
        raw == "0" or (
            (raw[1:] if raw.startswith("-") else raw).isdigit()
            and not (raw[1:] if raw.startswith("-") else raw).startswith("0")
            and raw != "-0"
        ),
        "INTEGER_ENCODING", f"noncanonical integer: {raw!r}",
    )
    value = int(raw)
    require(not nonzero or value != 0, "INTEGER_ZERO", "expected nonzero integer")
    require(not positive or value > 0, "INTEGER_SIGN", "expected positive integer")
    return value


def require_plain_int(value: Any, label: str) -> int:
    require(type(value) is int, "INTEGER_TYPE", f"{label} is not a JSON integer")
    return value


def require_sha(value: Any, label: str) -> str:
    require(
        isinstance(value, str) and len(value) == 64
        and all(character in "0123456789abcdef" for character in value),
        "SHA256_FORMAT", f"{label}: {value!r}",
    )
    return value


def safe_repo_path(root: pathlib.Path, raw: Any) -> pathlib.Path:
    require(isinstance(raw, str) and raw and "\\" not in raw, "PATH_ENCODING", repr(raw))
    relative = pathlib.PurePosixPath(raw)
    require(not relative.is_absolute() and ".." not in relative.parts, "PATH_ESCAPE", raw)
    resolved = (root / pathlib.Path(*relative.parts)).resolve()
    require(resolved.is_relative_to(root.resolve()), "PATH_ESCAPE", raw)
    return resolved


def direction_tuple(raw: Any) -> tuple[int, ...]:
    require(isinstance(raw, list) and len(raw) == N, "DIRECTION_SHAPE", repr(raw))
    direction = tuple(require_plain_int(value, "direction coordinate") for value in raw)
    require(sum(direction) == 0, "DIRECTION_SUM", repr(direction))
    first = next((value for value in direction if value), None)
    require(first is not None and first > 0, "DIRECTION_ORIENTATION", repr(direction))
    divisor = 0
    for value in direction:
        divisor = math.gcd(divisor, abs(value))
    require(divisor == 1, "DIRECTION_PRIMITIVE", repr(direction))
    prefix = 0
    active = False
    for value in direction[:-1]:
        prefix += value
        active |= prefix < 0
    require(active, "DIRECTION_INACTIVE", repr(direction))
    return direction


def direction_digest(directions: Iterable[Sequence[int]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        require(len(direction) == N, "DIRECTION_SHAPE", repr(direction))
        digest.update(bytes(value & 0xFF for value in direction))
    return digest.hexdigest()


def decimal_lf_digest(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.encode())
        digest.update(b"\n")
    return digest.hexdigest()


def u64le_digest(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(0 <= value < 2**64, "U64_RANGE", str(value))
        digest.update(struct.pack("<Q", value))
    return digest.hexdigest()


def i128le_digest(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(-(2**127) <= value < 2**127, "I128_RANGE", str(value))
        digest.update(value.to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def snapshot_digest(snapshot: Mapping[str, str]) -> str:
    digest = hashlib.sha256()
    for path in sorted(snapshot):
        digest.update(path.encode())
        digest.update(b"\t")
        digest.update(snapshot[path].encode())
        digest.update(b"\n")
    return digest.hexdigest()


def json_compact_digest(value: Any) -> str:
    encoded = json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode()
    return sha256_bytes(encoded)


def normalize_rationals(raw_values: Sequence[Any]) -> tuple[list[int], int]:
    fractions_: list[fractions.Fraction] = []
    for raw in raw_values:
        require(isinstance(raw, str), "RATIONAL_ENCODING", repr(raw))
        try:
            value = fractions.Fraction(raw)
        except (ValueError, ZeroDivisionError) as error:
            raise AuditFailure("RATIONAL_ENCODING", raw) from error
        require(str(value) == raw, "RATIONAL_ENCODING", f"noncanonical rational {raw}")
        fractions_.append(value)
    scale = 1
    for value in fractions_:
        scale = math.lcm(scale, value.denominator)
    integers = [value.numerator * (scale // value.denominator) for value in fractions_]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    if divisor > 1:
        scale //= divisor
        integers = [value // divisor for value in integers]
    require(scale > 0, "RATIONAL_SCALE", str(scale))
    return integers, scale


def extract_accumulated(stage_a: Mapping[str, Any]) -> list[tuple[int, ...]]:
    require(stage_a.get("schema") == "max11-g0140-pool128-global-replay-v1",
            "STAGE_A_SCHEMA", "unexpected Stage-A schema")
    inherited = stage_a.get("accumulated_direction_checks")
    pool = stage_a.get("pool")
    require(isinstance(inherited, list) and len(inherited) == 100,
            "STAGE_A_CENSUS", "expected 100 inherited directions")
    require(isinstance(pool, list) and len(pool) == 128,
            "STAGE_A_CENSUS", "expected 128 pool directions")
    output: list[tuple[int, ...]] = []
    for index, item in enumerate(inherited):
        require(item.get("index") == index, "STAGE_A_INDEX", str(index))
        direction = direction_tuple(item.get("direction"))
        require(item.get("aggregate_coefficient") == "0"
                and item.get("direct_dp_coefficient") == "0"
                and item.get("routes_agree") is True and item.get("exact_zero") is True,
                "STAGE_A_RESIDUAL", str(index))
        output.append(direction)
    pool_directions: list[tuple[int, ...]] = []
    for item in pool:
        pool_directions.append(direction_tuple(item.get("direction")))
        canonical_integer(item.get("coefficient"), nonzero=True)
    require(pool_directions == sorted(pool_directions) and len(set(pool_directions)) == 128,
            "STAGE_A_POOL_ORDER", "pool is not unique signed-lex order")
    require(direction_digest(pool_directions) == stage_a.get("pool_directions_i8_sha256"),
            "STAGE_A_POOL_DIGEST", "direction digest mismatch")
    require(decimal_lf_digest(item["coefficient"] for item in pool)
            == stage_a.get("pool_exact_residuals_decimal_lf_sha256"),
            "STAGE_A_POOL_DIGEST", "coefficient digest mismatch")
    output.extend(pool_directions)
    require(len(output) == 228 and len(set(output)) == 228,
            "ACCUMULATED_CENSUS", "accumulated directions duplicate or missing")
    return output


def validate_result_semantics(result: Mapping[str, Any], manifest: Mapping[str, Any],
                              member: Mapping[str, Any], stage_a: Mapping[str, Any]) -> dict[str, Any]:
    require(set(result) == RESULT_KEYS, "RESULT_SCHEMA_KEYS",
            f"missing={sorted(RESULT_KEYS-set(result))}, extra={sorted(set(result)-RESULT_KEYS)}")
    require(result.get("schema") == "max11-g0164-all128-global-replay-v1",
            "RESULT_SCHEMA", repr(result.get("schema")))
    require(result.get("result") in {"GLOBAL_EXACT_ZERO", "EXACT_RESIDUAL_CONTINUE"},
            "RESULT_BRANCH", repr(result.get("result")))
    require(result.get("claim_boundary") == manifest.get("claim_boundary"),
            "CLAIM_BOUNDARY", "manifest/result claim boundary differs")
    require(result.get("result") in manifest["planned_output"]["allowed_results"],
            "RESULT_BRANCH", "result branch not preregistered")
    require(isinstance(result.get("wall_seconds"), decimal.Decimal)
            and result["wall_seconds"].is_finite() and result["wall_seconds"] > 0,
            "WALL_SECONDS", "invalid metadata float")

    parameters = manifest["parameters"]
    fixed = {
        "records": RECORDS, "base_rows": 412, "appended_rows": 128, "rows": ROWS,
        "rank": RANK, "terms": 304,
    }
    for key, expected in fixed.items():
        require_plain_int(result.get(key), key)
        require(result.get(key) == expected == parameters.get(key),
                "DIMENSION_DRIFT", f"{key}: {result.get(key)}")
    require(result.get("basis_coordinates") == RANK and result.get("support_columns") == 304,
            "DIMENSION_DRIFT", "basis/support counts")
    require(result.get("selected_pool_indices") == list(range(128)),
            "BRANCH_CENSUS", "selected pool indices are not exactly 0..127")
    selected = [direction_tuple(value) for value in result.get("selected_directions", [])]
    member_selected = [direction_tuple(value) for value in member.get("selected_directions", [])]
    require(len(selected) == 128 and len(set(selected)) == 128 and selected == member_selected,
            "BRANCH_CENSUS", "selected directions mismatch/duplicate")
    require(direction_digest(selected) == result.get("selected_directions_i8_sha256")
            == member.get("selected_directions_i8_sha256"),
            "SELECTED_DIRECTION_DIGEST", "selected-direction digest mismatch")

    terms = member.get("terms")
    require(isinstance(terms, list) and len(terms) == 304, "TERM_CENSUS", "member terms")
    term_sequences: list[int] = []
    for term in terms:
        require(set(term) == {"sequence", "coefficient"}, "TERM_SCHEMA", repr(term))
        term_sequences.append(require_plain_int(term["sequence"], "term sequence"))
        canonical_integer(term["coefficient"], nonzero=True)
    require(term_sequences == sorted(term_sequences) and len(set(term_sequences)) == 304,
            "TERM_CENSUS", "member terms not unique and ordered")
    receipts = result.get("term_normal_forms")
    require(isinstance(receipts, list) and len(receipts) == 304,
            "TERM_CENSUS", "term receipt count")
    require([item.get("sequence") for item in receipts] == term_sequences,
            "TERM_CENSUS", "term receipt sequences do not cover member terms exactly")
    hinge_entries = 0
    for receipt in receipts:
        active = require_plain_int(receipt.get("active_vertices"), "active_vertices")
        compressed = require_plain_int(receipt.get("compressed_leaves"), "compressed_leaves")
        inactive = require_plain_int(receipt.get("inactive_label_multiplicity"), "inactive multiplicity")
        labelled = require_plain_int(receipt.get("labelled_permutations"), "labelled permutations")
        entries = require_plain_int(receipt.get("hinge_entries"), "hinge entries")
        require(0 <= active <= N and inactive == math.factorial(N-active)
                and compressed*inactive == FACTORIAL_11 and labelled == FACTORIAL_11,
                "TERM_RECONCILIATION", str(receipt.get("sequence")))
        require(receipt.get("independent_exact_linear_crosscheck") is True
                and receipt.get("bounded_kernel_crosscheck") is True,
                "TERM_RECONCILIATION", "embedded crosscheck false")
        require_sha(receipt.get("normal_form_sha256"), "term normal-form digest")
        hinge_entries += entries
    require(result.get("labelled_permutations_expected") == 304*FACTORIAL_11
            == result.get("labelled_permutations_checked"),
            "LABELLED_CENSUS", "labelled permutation total")
    require(result.get("hinge_entries_processed") == hinge_entries,
            "TERM_RECONCILIATION", "hinge-entry sum")
    require(json_compact_digest(receipts) == result.get("term_normal_form_transcript_sha256"),
            "TERM_TRANSCRIPT_DIGEST", "compact receipt transcript mismatch")

    accumulated = extract_accumulated(stage_a)
    checks = result.get("accumulated_direction_checks")
    require(isinstance(checks, list) and len(checks) == 228,
            "ACCUMULATED_CENSUS", "result checks")
    for index, (item, expected_direction) in enumerate(zip(checks, accumulated, strict=True)):
        require(item.get("index") == index and direction_tuple(item.get("direction")) == expected_direction,
                "ACCUMULATED_CENSUS", f"row {index}")
        expected_source = "G0128_ACCUMULATED_68" if index < 68 else (
            "G0135_STAGE_A_BATCH32" if index < 100 else "G0140_POOL128")
        expected_source_index = index if index < 68 else (index-68 if index < 100 else index-100)
        require(item.get("source") == expected_source and item.get("source_index") == expected_source_index,
                "ACCUMULATED_SOURCE", str(index))
        require(item.get("aggregate_coefficient") == "0" and item.get("direct_dp_coefficient") == "0"
                and item.get("routes_agree") is True and item.get("exact_zero") is True,
                "ACCUMULATED_RESIDUAL", str(index))
    require(result.get("inherited_accumulated_directions") == 100
            and result.get("selected_accumulated_directions") == 128
            and result.get("accumulated_direction_count") == 228
            and result.get("all_accumulated_directions_exact_zero") is True,
            "ACCUMULATED_CENSUS", "summary fields")

    linear = result.get("linear_residuals_after_target")
    require(isinstance(linear, list) and len(linear) == 11
            and all(canonical_integer(value) == 0 for value in linear)
            and result.get("all_11_linear_residuals_exact_zero") is True,
            "LINEAR_RESIDUAL", "reported linear residuals")

    prefix_raw = result.get("residual_prefix")
    require(isinstance(prefix_raw, list) and len(prefix_raw) == PREFIX_K,
            "PREFIX_CENSUS", "prefix must contain 128 rows")
    prefix: list[tuple[tuple[int, ...], str]] = []
    for item in prefix_raw:
        require(set(item) == {"direction", "coefficient"}, "PREFIX_SCHEMA", repr(item))
        direction = direction_tuple(item["direction"])
        coefficient = item["coefficient"]
        canonical_integer(coefficient, nonzero=True)
        prefix.append((direction, coefficient))
    prefix_directions = [item[0] for item in prefix]
    require(prefix_directions == sorted(prefix_directions) and len(set(prefix_directions)) == PREFIX_K,
            "PREFIX_ORDER", "prefix is not strict signed lexicographic order")
    require(not set(prefix_directions).intersection(accumulated),
            "PREFIX_EXCLUSION", "prefix contains accumulated direction")
    require(result.get("residual_prefix_k") == PREFIX_K
            and result.get("residual_prefix_count") == PREFIX_K,
            "PREFIX_CENSUS", "prefix totals")
    require(direction_digest(prefix_directions) == result.get("residual_prefix_directions_i8_sha256"),
            "PREFIX_DIRECTION_DIGEST", "prefix direction digest")
    require(decimal_lf_digest(item[1] for item in prefix)
            == result.get("residual_prefix_exact_residuals_decimal_lf_sha256"),
            "PREFIX_COEFFICIENT_DIGEST", "prefix coefficient digest")
    first = result.get("first_nonzero_hinge")
    require(isinstance(first, dict)
            and direction_tuple(first.get("direction")) == prefix[0][0]
            and first.get("coefficient") == prefix[0][1]
            and result.get("first_nonzero_linear") is None,
            "FIRST_NONZERO", "first-nonzero summary/prefix mismatch")
    require(result.get("result") == "EXACT_RESIDUAL_CONTINUE"
            and result.get("complete_global_replay") is True
            and result.get("all_hinge_and_linear_residuals_zero") is False,
            "RESULT_CLASSIFICATION", "branch does not follow exact nonzero")
    require(result.get("no_automatic_next_study") is True,
            "RESULT_CLASSIFICATION", "automatic continuation flag")

    census = result.get("census_controls")
    require(census == {
        "dynamic_term_count": 304, "factorial_11": FACTORIAL_11,
        "expected_labelled_permutations": 304*FACTORIAL_11,
        "observed_labelled_permutations": 304*FACTORIAL_11,
        "all_term_receipts_reconciled": True,
        "expected_accumulated_directions": 228,
        "observed_accumulated_directions": 228,
    }, "CENSUS_CONTROLS", repr(census))
    prefix_controls = result.get("prefix_controls")
    require(prefix_controls == {
        "maximum_k": 128, "expected_count": 128, "observed_count": 128,
        "strict_signed_lexicographic_order": True,
        "excludes_accumulated_directions": True,
    }, "PREFIX_CONTROLS", repr(prefix_controls))

    require(result.get("inputs_rehashed_at_end") is True
            and result.get("manifest_rehashed_at_end") is True
            and result.get("candidate_rehashed_at_end") is True,
            "END_REHASH_FLAGS", "one or more false")
    for field in (
        "aggregate_hinge_decimal_lf_sha256", "nonzero_hinge_decimal_lf_sha256",
        "complete_residual_decimal_lf_sha256", "term_normal_form_transcript_sha256",
    ):
        require_sha(result.get(field), field)
    baseline = result["complete_residual_decimal_lf_sha256"]
    expected_mutants = {
        "coefficient_plus_one": "first_nonzero_coefficient_plus_one",
        "target_scale_plus_one": "target_scale_plus_one",
        "target_coordinate_plus_one": "target_coordinate_10_plus_one",
        "omitted_final_term": "omitted_final_nonzero_term",
        "omitted_first_term_direction": "omitted_first_term_active_direction",
    }
    for field, name in expected_mutants.items():
        control = result.get(field)
        require(isinstance(control, dict) and control.get("name") == name
                and control.get("baseline_sha256") == baseline
                and require_sha(control.get("mutated_sha256"), field) != baseline
                and control.get("detected") is True,
                "EMBEDDED_MUTANT", field)
        if control.get("first_nonzero_hinge") is not None:
            direction_tuple(control["first_nonzero_hinge"]["direction"])
            canonical_integer(control["first_nonzero_hinge"]["coefficient"], nonzero=True)
        if control.get("first_nonzero_linear") is not None:
            require_plain_int(control["first_nonzero_linear"].get("coordinate"), "mutant coordinate")
            canonical_integer(control["first_nonzero_linear"].get("coefficient"), nonzero=True)

    return {
        "terms": len(terms), "term_receipts": len(receipts),
        "labelled_permutations": result["labelled_permutations_checked"],
        "accumulated_rows": len(checks), "selected_pool_rows": len(selected),
        "prefix_rows": len(prefix), "prefix": prefix, "accumulated": accumulated,
    }


def validate_member(member: Mapping[str, Any], finite_manifest: Mapping[str, Any],
                    panel: Mapping[str, Any]) -> dict[str, Any]:
    require(member.get("schema") == "max11-g0164-all128-direct-basis-member-v1"
            and member.get("result") == "ALL128_DIRECT_BASIS_EXACT_Q_MEMBER",
            "MEMBER_SCHEMA", "member identity")
    require(member.get("manifest", {}).get("path") == FINITE_MANIFEST_PATH,
            "MEMBER_BINDING", "finite manifest path")
    require(member.get("records") == RECORDS and member.get("rows") == ROWS
            and member.get("rank") == RANK and member.get("augmented_rank") == RANK,
            "MEMBER_DIMENSIONS", "record/row/rank")
    basis = member.get("basis_sequences")
    coordinate_rows = member.get("coordinate_rows")
    require(isinstance(basis, list) and len(basis) == RANK
            and basis == sorted(basis) and len(set(basis)) == RANK
            and all(type(value) is int and 0 <= value < RECORDS for value in basis),
            "MEMBER_BASIS", "basis sequence axis")
    require(isinstance(coordinate_rows, list) and len(coordinate_rows) == RANK
            and coordinate_rows == sorted(coordinate_rows) and len(set(coordinate_rows)) == RANK
            and all(type(value) is int and 0 <= value < ROWS for value in coordinate_rows),
            "MEMBER_COORDINATES", "coordinate row axis")
    require(u64le_digest(basis) == member.get("basis_sequences_u64le_sha256")
            == finite_manifest.get("basis_sequences_u64le_sha256"),
            "MEMBER_BASIS_DIGEST", "basis sequences")
    rational = member.get("rational_coefficients")
    integer_raw = member.get("integer_coefficients")
    require(isinstance(rational, list) and isinstance(integer_raw, list)
            and len(rational) == len(integer_raw) == RANK,
            "MEMBER_COEFFICIENT_CENSUS", "coefficient axes")
    require(decimal_lf_digest(rational) == member.get("rational_coefficients_decimal_lf_sha256")
            and decimal_lf_digest(integer_raw) == member.get("integer_coefficients_decimal_lf_sha256"),
            "MEMBER_COEFFICIENT_DIGEST", "coefficient digest")
    normalized, scale = normalize_rationals(rational)
    integers = [canonical_integer(value) for value in integer_raw]
    require(normalized == integers and scale == canonical_integer(member.get("target_scale"), positive=True),
            "MEMBER_DENOMINATOR_CLEARING", "rational/integer coordinates")
    expected_terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(basis, integers, strict=True) if coefficient
    ]
    require(member.get("terms") == expected_terms and member.get("support_columns") == len(expected_terms),
            "MEMBER_TERM_PROJECTION", "nonzero term projection")
    target_raw = member.get("target")
    require(isinstance(target_raw, list) and len(target_raw) == ROWS,
            "MEMBER_TARGET", "target axis")
    target = [canonical_integer(value) for value in target_raw]
    require(i128le_digest(target) == member.get("target_i128le_sha256")
            == finite_manifest.get("target_i128le_sha256"),
            "MEMBER_TARGET_DIGEST", "target digest")
    panel_target = panel.get("target")
    require(isinstance(panel_target, list) and len(panel_target) == PANEL_ROWS,
            "PANEL_TARGET", "panel target axis")
    require(target[:PANEL_ROWS] == panel_target
            and target[PANEL_ROWS:PANEL_ROWS+10] == [0]*10
            and target[PANEL_ROWS+10] == FACTORIAL_11
            and target[PANEL_ROWS+11:] == [0]*228,
            "MEMBER_TARGET", "target construction")
    return {
        "basis": basis, "coordinate_rows": coordinate_rows, "integers": integers,
        "scale": scale, "target": target, "terms": expected_terms,
    }


def hash_binding_at(root: pathlib.Path, commit: str, binding: Mapping[str, Any], label: str) -> None:
    require(set(binding) >= {"path", "sha256"}, "BINDING_SCHEMA", label)
    path = binding["path"]
    safe_repo_path(root, path)
    expected = require_sha(binding["sha256"], label)
    observed = sha256_bytes(git_blob(root, commit, path))
    require(observed == expected, "BINDING_DIGEST", f"{label}: {path}")


def validate_custody(root: pathlib.Path, manifest_raw: bytes, result_raw: bytes,
                     manifest: Mapping[str, Any], result: Mapping[str, Any],
                     finite_manifest: Mapping[str, Any]) -> dict[str, Any]:
    for commit in (MANIFEST_COMMIT, RESULT_COMMIT):
        require(git(root, "cat-file", "-t", commit).decode().strip() == "commit",
                "CUSTODY_COMMIT", commit)
    parent = git(root, "rev-parse", f"{RESULT_COMMIT}^1").decode().strip()
    require(parent == MANIFEST_COMMIT, "CUSTODY_PARENT", parent)
    manifest_diff = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r",
                        f"{MANIFEST_COMMIT}^1", MANIFEST_COMMIT).decode().splitlines()
    result_diff = git(root, "diff-tree", "--no-commit-id", "--name-only", "-r",
                      MANIFEST_COMMIT, RESULT_COMMIT).decode().splitlines()
    require(manifest_diff == [GLOBAL_MANIFEST_PATH], "CUSTODY_MANIFEST_DIFF", repr(manifest_diff))
    require(result_diff == [RESULT_PATH], "CUSTODY_RESULT_DIFF", repr(result_diff))
    require(not git_blob_exists(root, MANIFEST_COMMIT, RESULT_PATH),
            "CUSTODY_PREEXISTING_RESULT", RESULT_PATH)
    require(git_blob_id(root, MANIFEST_COMMIT, GLOBAL_MANIFEST_PATH)
            == git_blob_id(root, RESULT_COMMIT, GLOBAL_MANIFEST_PATH),
            "CUSTODY_MANIFEST_DRIFT", GLOBAL_MANIFEST_PATH)

    manifest_sha = sha256_bytes(manifest_raw)
    result_sha = sha256_bytes(result_raw)
    require(result.get("global_manifest") == {"path": GLOBAL_MANIFEST_PATH, "sha256": manifest_sha},
            "GLOBAL_MANIFEST_BINDING", repr(result.get("global_manifest")))
    require(manifest.get("planned_output", {}).get("path") == RESULT_PATH
            and manifest.get("planned_output", {}).get("schema") == result.get("schema"),
            "PLANNED_OUTPUT", "manifest output contract")
    require(manifest.get("scientific_replay_executed") is False
            and manifest.get("scientific_output_created") is False,
            "MANIFEST_PREOPEN_FLAGS", "manifest flags are not false")

    finite_manifest_raw = git_blob(root, RESULT_COMMIT, FINITE_MANIFEST_PATH)
    member_raw = git_blob(root, RESULT_COMMIT, MEMBER_PATH)
    require(result.get("finite_manifest") == {
        "path": FINITE_MANIFEST_PATH, "sha256": sha256_bytes(finite_manifest_raw)},
        "FINITE_MANIFEST_BINDING", "result binding")
    require(result.get("finite_member") == {
        "path": MEMBER_PATH, "sha256": sha256_bytes(member_raw)},
        "FINITE_MEMBER_BINDING", "result binding")

    producer = manifest.get("producer")
    require(isinstance(producer, dict), "PRODUCER_BINDING", "missing producer object")
    producer_commit = producer.get("git_commit")
    require(isinstance(producer_commit, str)
            and git(root, "cat-file", "-t", producer_commit).decode().strip() == "commit",
            "PRODUCER_BINDING", "producer commit")
    for field in ("main_source", "candidate_source", "engine_source", "cargo_manifest",
                  "cargo_lock", "release_executable"):
        hash_binding_at(root, producer_commit, producer[field], f"producer.{field}@producer")
        hash_binding_at(root, RESULT_COMMIT, producer[field], f"producer.{field}@result")

    for field in (
        "preregistration", "finite_manifest", "finite_member", "g0117_cargo_manifest",
        "g0117_lib_source", "source_audit_preregistration", "source_audit",
        "parent_replay_source", "parent_replay_engine", "parent_source_audit",
    ):
        binding = manifest[field]
        commit = binding.get("git_commit")
        require(isinstance(commit, str), "COMMIT_BINDING", field)
        hash_binding_at(root, commit, binding, f"manifest.{field}@declared")
        hash_binding_at(root, RESULT_COMMIT, binding, f"manifest.{field}@result")

    source_map = result.get("source_and_audit_bindings")
    require(isinstance(source_map, dict) and len(source_map) == 16,
            "SOURCE_BINDING_CENSUS", repr(type(source_map)))
    for key, binding in source_map.items():
        require(binding.get("path") == key, "SOURCE_BINDING_KEY", key)
        hash_binding_at(root, RESULT_COMMIT, binding, f"source_map.{key}")

    snapshot = finite_manifest.get("input_snapshot")
    require(isinstance(snapshot, dict) and len(snapshot) == 104,
            "INPUT_SNAPSHOT_CENSUS", repr(type(snapshot)))
    for path, expected in snapshot.items():
        safe_repo_path(root, path)
        require_sha(expected, f"snapshot {path}")
    require(snapshot_digest(snapshot) == finite_manifest.get("input_snapshot_sha256"),
            "INPUT_SNAPSHOT_DIGEST", "snapshot table")
    tracked_paths = set(git(root, "ls-tree", "-r", "--name-only", RESULT_COMMIT).decode().splitlines())
    working_only: list[str] = []
    total_bytes = 0
    for path, expected in sorted(snapshot.items()):
        if path in tracked_paths:
            raw = git_blob(root, RESULT_COMMIT, path)
            observed = sha256_bytes(raw)
            total_bytes += len(raw)
        else:
            working_only.append(path)
            observed, length = sha256_file(safe_repo_path(root, path))
            total_bytes += length
        require(observed == expected, "INPUT_SNAPSHOT_FILE_DIGEST", path)
    return {
        "manifest_commit": MANIFEST_COMMIT, "result_commit": RESULT_COMMIT,
        "manifest_blob": git_blob_id(root, MANIFEST_COMMIT, GLOBAL_MANIFEST_PATH),
        "result_blob": git_blob_id(root, RESULT_COMMIT, RESULT_PATH),
        "manifest_sha256": manifest_sha, "manifest_bytes": len(manifest_raw),
        "result_sha256": result_sha, "result_bytes": len(result_raw),
        "input_snapshot_entries": len(snapshot), "input_snapshot_bytes_observed": total_bytes,
        "input_snapshot_git_tracked": len(snapshot)-len(working_only),
        "input_snapshot_working_only": len(working_only),
        "working_only_paths": working_only,
    }


def compile_route(root: pathlib.Path, build: pathlib.Path) -> tuple[pathlib.Path, str, str]:
    source = root / CPP_PATH
    binary = build / "independent_exact_route"
    compiler = run(["g++", "--version"], cwd=root).stdout.decode().splitlines()[0]
    completed = run([
        "g++", "-O3", "-std=c++20", "-fopenmp", "-Wall", "-Wextra", "-Werror",
        str(source), "-o", str(binary),
    ], cwd=root, timeout=120)
    require(completed.stderr == b"", "INDEPENDENT_BUILD_WARNING", completed.stderr.decode())
    self_test = run([str(binary), "--self-test"], cwd=root, timeout=120)
    require(self_test.stdout == b"SELF_TEST_PASS\n" and self_test.stderr == b"",
            "INDEPENDENT_SELF_TEST", (self_test.stdout+self_test.stderr).decode())
    return binary, compiler, sha256_file(source)[0]


def route_matrix(root: pathlib.Path, binary: pathlib.Path, records: Sequence[Mapping[str, Any]],
                 directions: Sequence[tuple[int, ...]]) -> dict[int, tuple[list[int], list[int]]]:
    require(list(directions) == sorted(directions) and len(set(directions)) == len(directions),
            "ROUTE_INPUT_ORDER", "directions")
    lines = [str(len(directions)), *(" ".join(map(str, item)) for item in directions), str(len(records))]
    for record in records:
        fields = [record["sequence"], record["active_vertices"], record["signed_mass"]]
        negative = record["negative_edges"]
        positive = record["positive_edges"]
        require(len(negative) == len(positive) == record["signed_mass"],
                "RECORD_EDGE_CENSUS", str(record["sequence"]))
        for edge in [*negative, *positive]:
            require(isinstance(edge, list) and len(edge) == 2,
                    "RECORD_EDGE", str(record["sequence"]))
            fields.extend(edge)
        lines.append(" ".join(map(str, fields)))
    environment = os.environ.copy()
    environment["OMP_NUM_THREADS"] = "12"
    completed = subprocess.run(
        [str(binary), "--matrix"], cwd=root, input=("\n".join(lines)+"\n").encode(),
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=1800, env=environment, check=False,
    )
    require(completed.returncode == 0 and completed.stderr == b"",
            "INDEPENDENT_ROUTE", completed.stderr.decode(errors="replace"))
    output = completed.stdout.decode().splitlines()
    require(output and output[0] == f"AUDIT_EXACT_ROUTE_V1 {len(records)} {len(directions)}",
            "INDEPENDENT_ROUTE_PROTOCOL", output[0] if output else "empty")
    parsed: dict[int, tuple[list[int], list[int]]] = {}
    for line in output[1:]:
        fields = line.split()
        require(fields and fields[0] == "R" and len(fields) == 2+N+len(directions),
                "INDEPENDENT_ROUTE_PROTOCOL", "row width")
        sequence = int(fields[1])
        require(sequence not in parsed, "INDEPENDENT_ROUTE_PROTOCOL", "duplicate sequence")
        parsed[sequence] = (
            [int(value) for value in fields[2:2+N]],
            [int(value) for value in fields[2+N:]],
        )
    require(len(parsed) == len(records), "INDEPENDENT_ROUTE_PROTOCOL", "row count")
    return parsed


def enumerate_directions_through(limit: tuple[int, ...], bound: int = 5) -> list[tuple[int, ...]]:
    require(len(limit) == N, "PREFIX_LIMIT", repr(limit))
    output: list[tuple[int, ...]] = []

    def visit(index: int, values: list[int], total: int, divisor: int,
              started: bool, active: bool, relation: int) -> None:
        if index == N:
            if total == 0 and started and active and divisor == 1 and relation <= 0:
                output.append(tuple(values))
            return
        for value in range(-bound, bound+1):
            if relation == 0 and value > limit[index]:
                continue
            if not started and value < 0:
                continue
            next_total = total+value
            remaining = N-index-1
            if not (-bound*remaining <= -next_total <= bound*remaining):
                continue
            next_relation = relation
            if relation == 0 and value < limit[index]:
                next_relation = -1
            visit(
                index+1, [*values, value], next_total, math.gcd(divisor, abs(value)),
                started or value != 0, active or (index < N-1 and next_total < 0), next_relation,
            )

    visit(0, [], 0, 0, False, False, 0)
    output = sorted(set(output))
    require(output and output[-1] == limit, "PREFIX_LIMIT", "limit absent from enumeration")
    return output


def read_panel_columns(cache: pathlib.Path, sequences: Sequence[int]) -> list[list[int]]:
    width = PANEL_ROWS*16
    require(cache.stat().st_size == RECORDS*width, "CACHE_SIZE", str(cache.stat().st_size))
    columns: list[list[int]] = []
    with cache.open("rb") as handle:
        for sequence in sequences:
            handle.seek(sequence*width)
            raw = handle.read(width)
            require(len(raw) == width, "CACHE_TRUNCATION", str(sequence))
            columns.append([
                int.from_bytes(raw[offset:offset+16], "little", signed=True)
                for offset in range(0, width, 16)
            ])
    return columns


def independent_replay(root: pathlib.Path, result: Mapping[str, Any], member: Mapping[str, Any],
                       panel: Mapping[str, Any], stage_a: Mapping[str, Any],
                       member_info: Mapping[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    records = panel.get("records")
    require(isinstance(records, list) and len(records) == RECORDS
            and all(item.get("sequence") == index for index, item in enumerate(records)),
            "PANEL_RECORD_CENSUS", "records")
    accumulated = extract_accumulated(stage_a)
    sorted_accumulated = sorted(accumulated)
    basis = member_info["basis"]
    basis_records = [records[sequence] for sequence in basis]
    cache = safe_repo_path(root, CACHE_PATH)
    cache_sha_before, cache_bytes = sha256_file(cache)
    finite_manifest = strict_json(git_blob(root, RESULT_COMMIT, FINITE_MANIFEST_PATH), FINITE_MANIFEST_PATH)
    require(cache_sha_before == finite_manifest["input_snapshot"][CACHE_PATH],
            "CACHE_DIGEST", "before replay")

    with tempfile.TemporaryDirectory(prefix="g0167-independent-") as temporary:
        build = pathlib.Path(temporary)
        binary, compiler, source_sha = compile_route(root, build)

        finite_route_started = time.monotonic()
        finite_values = route_matrix(root, binary, basis_records, sorted_accumulated)
        finite_route_seconds = time.monotonic()-finite_route_started
        accumulated_position = {direction: index for index, direction in enumerate(sorted_accumulated)}
        panel_columns = read_panel_columns(cache, basis)
        columns: list[list[int]] = []
        for sequence, panel_column in zip(basis, panel_columns, strict=True):
            linear, sorted_hinges = finite_values[sequence]
            hinges = [sorted_hinges[accumulated_position[direction]] for direction in accumulated]
            column = [*panel_column, *linear, *hinges]
            require(len(column) == ROWS, "FINITE_COLUMN_WIDTH", str(sequence))
            columns.append(column)

        integers = member_info["integers"]
        target = member_info["target"]
        scale = member_info["scale"]
        residuals = [
            sum(coefficient*column[row] for coefficient, column in zip(integers, columns, strict=True))
            - scale*target[row]
            for row in range(ROWS)
        ]
        require(residuals == [0]*ROWS, "FINITE_EXACT_REPLAY", "one or more of 540 rows nonzero")
        residual_digest = decimal_lf_digest(str(value) for value in residuals)

        row_major = (columns[column][row] for row in range(ROWS) for column in range(RANK))
        basis_digest = i128le_digest(row_major)
        square_digest = i128le_digest(
            columns[column][row]
            for row in member_info["coordinate_rows"] for column in range(RANK)
        )
        require(basis_digest == member.get("basis_i128le_sha256")
                == result["independent_finite_replay"]["selected_basis_i128le_sha256"],
                "FINITE_BASIS_DIGEST", basis_digest)
        require(square_digest == member.get("square_i128le_sha256")
                == result["independent_finite_replay"]["square_i128le_sha256"],
                "FINITE_SQUARE_DIGEST", square_digest)
        require(residual_digest == result["independent_finite_replay"]["residuals_decimal_lf_sha256"],
                "FINITE_RESIDUAL_DIGEST", residual_digest)

        mutant = member["coefficient_plus_one_mutant"]
        mutant_column = columns[mutant["basis_index"]]
        first_nonzero_row = next(index for index, value in enumerate(mutant_column) if value)
        mutant_digest = decimal_lf_digest(str(value) for value in mutant_column)
        recomputed_mutant = {
            "basis_index": mutant["basis_index"],
            "sequence": basis[mutant["basis_index"]],
            "first_nonzero_row": first_nonzero_row,
            "first_nonzero_residual": str(mutant_column[first_nonzero_row]),
            "nonzero_rows": sum(value != 0 for value in mutant_column),
            "residuals_decimal_lf_sha256": mutant_digest,
            "rejected": True,
        }
        require(recomputed_mutant == mutant == result["independent_finite_replay"]["coefficient_plus_one_mutant"],
                "FINITE_MUTANT", "coefficient-plus-one replay")

        reported_prefix = [
            (direction_tuple(item["direction"]), item["coefficient"])
            for item in result["residual_prefix"]
        ]
        candidates = enumerate_directions_through(reported_prefix[-1][0], bound=5)
        term_records = [records[item["sequence"]] for item in member_info["terms"]]
        prefix_route_started = time.monotonic()
        prefix_values = route_matrix(root, binary, term_records, candidates)
        prefix_route_seconds = time.monotonic()-prefix_route_started
        coefficients = {item["sequence"]: int(item["coefficient"]) for item in member_info["terms"]}
        aggregate = [0]*len(candidates)
        for sequence, coefficient in coefficients.items():
            hinges = prefix_values[sequence][1]
            for index, value in enumerate(hinges):
                aggregate[index] += coefficient*value
        excluded = set(accumulated)
        independent_prefix = [
            (direction, str(value))
            for direction, value in zip(candidates, aggregate, strict=True)
            if value and direction not in excluded
        ][:PREFIX_K]
        require(independent_prefix == reported_prefix,
                "INDEPENDENT_PREFIX", "first 128 exact nonzero directions/coefficients differ")
        first_direction = reported_prefix[0][0]
        predecessor_count = candidates.index(first_direction)
        require(predecessor_count == 25 and all(value == 0 for value in aggregate[:predecessor_count]),
                "INDEPENDENT_FIRST_NONZERO", "a signed-lex predecessor is nonzero")
        require(str(aggregate[predecessor_count]) == reported_prefix[0][1],
                "INDEPENDENT_FIRST_NONZERO", "first residual coefficient differs")

    cache_sha_after, cache_bytes_after = sha256_file(cache)
    require((cache_sha_after, cache_bytes_after) == (cache_sha_before, cache_bytes),
            "CACHE_DRIFT_DURING_REPLAY", CACHE_PATH)
    return {
        "cpp_source_sha256": source_sha, "compiler": compiler,
        "known_answer_and_edge_mutant_self_test": "PASS",
        "finite_rows_replayed": ROWS, "finite_panel_rows": PANEL_ROWS,
        "finite_linear_rows": LINEAR_ROWS, "finite_accumulated_rows": ACCUMULATED_ROWS,
        "finite_selected_basis_columns": RANK,
        "finite_selected_basis_i128le_sha256": basis_digest,
        "finite_square_i128le_sha256": square_digest,
        "finite_residuals_decimal_lf_sha256": residual_digest,
        "finite_coefficient_plus_one_mutant": recomputed_mutant,
        "prefix_candidate_directions_checked": len(candidates),
        "signed_lex_predecessors_before_first": predecessor_count,
        "independent_first_nonzero": {
            "direction": list(first_direction), "coefficient": reported_prefix[0][1],
        },
        "independent_prefix_rows": len(independent_prefix),
        "independent_prefix_directions_i8_sha256": direction_digest(item[0] for item in independent_prefix),
        "independent_prefix_coefficients_decimal_lf_sha256": decimal_lf_digest(item[1] for item in independent_prefix),
        "cache_sha256_before_and_after": cache_sha_before,
        "cache_bytes": cache_bytes,
        "finite_route_seconds": round(finite_route_seconds, 6),
        "prefix_route_seconds": round(prefix_route_seconds, 6),
        "total_seconds": round(time.monotonic()-started, 6),
    }


def expect_failure(label: str, operation: Any) -> dict[str, str]:
    try:
        operation()
    except AuditFailure as error:
        return {"name": label, "result": "REJECTED", "failure_code": error.code}
    raise AuditFailure("MUTANT_ESCAPED", label)


def mutation_controls(result_raw: bytes, result: Mapping[str, Any], manifest: Mapping[str, Any],
                      member: Mapping[str, Any], stage_a: Mapping[str, Any], root: pathlib.Path) -> list[dict[str, str]]:
    controls: list[dict[str, str]] = []

    def semantic(mutator: Any) -> None:
        value = copy.deepcopy(result)
        mutator(value)
        validate_result_semantics(value, manifest, member, stage_a)

    controls.append(expect_failure("delete-one-prefix-row", lambda: semantic(
        lambda value: value["residual_prefix"].pop())))
    controls.append(expect_failure("duplicate-prefix-preserve-count", lambda: semantic(
        lambda value: value["residual_prefix"].__setitem__(-1, copy.deepcopy(value["residual_prefix"][0])))))
    controls.append(expect_failure("swap-adjacent-prefix-rows", lambda: semantic(
        lambda value: value["residual_prefix"].__setitem__(slice(0, 2), value["residual_prefix"][1::-1]))))
    controls.append(expect_failure("branch-total-127", lambda: semantic(
        lambda value: value.__setitem__("residual_prefix_count", 127))))
    controls.append(expect_failure("duplicate-selected-pool-index", lambda: semantic(
        lambda value: value["selected_pool_indices"].__setitem__(0, 1))))
    controls.append(expect_failure("flip-first-nonzero-to-zero", lambda: semantic(
        lambda value: value["residual_prefix"][0].__setitem__("coefficient", "0"))))
    controls.append(expect_failure("alter-exact-residual-component", lambda: semantic(
        lambda value: value["residual_prefix"][0].__setitem__(
            "coefficient", str(int(value["residual_prefix"][0]["coefficient"])+1)))))
    controls.append(expect_failure("alter-prefix-digest", lambda: semantic(
        lambda value: value.__setitem__("residual_prefix_directions_i8_sha256", "0"*64))))
    controls.append(expect_failure("alter-global-class-only", lambda: semantic(
        lambda value: value.__setitem__("result", "GLOBAL_EXACT_ZERO"))))

    schema_token = b'"schema": "max11-g0164-all128-global-replay-v1",'
    duplicate_raw = result_raw.replace(schema_token, schema_token+b'\n  "schema": "max11-g0164-all128-global-replay-v1",', 1)
    controls.append(expect_failure("duplicate-json-key", lambda: strict_json(duplicate_raw, "duplicate mutant")))
    nan_raw = result_raw.replace(b'"residual_prefix_k": 128', b'"residual_prefix_k": NaN', 1)
    controls.append(expect_failure("nan-proof-field", lambda: strict_json(nan_raw, "NaN mutant")))
    controls.append(expect_failure("truncated-json", lambda: strict_json(result_raw[:-17], "truncated mutant")))

    def reorder_and_rehash(value: dict[str, Any]) -> None:
        value["residual_prefix"][0], value["residual_prefix"][1] = (
            value["residual_prefix"][1], value["residual_prefix"][0])
        value["residual_prefix_directions_i8_sha256"] = direction_digest(
            item["direction"] for item in value["residual_prefix"])
        value["residual_prefix_exact_residuals_decimal_lf_sha256"] = decimal_lf_digest(
            item["coefficient"] for item in value["residual_prefix"])
        value["first_nonzero_hinge"] = copy.deepcopy(value["residual_prefix"][0])
    controls.append(expect_failure("reorder-with-naive-digests-recomputed", lambda: semantic(reorder_and_rehash)))

    def path_escape() -> None:
        value = copy.deepcopy(result)
        value["global_manifest"]["path"] = "../../all128_global_replay_manifest_v1.json"
        safe_repo_path(root, value["global_manifest"]["path"])
    controls.append(expect_failure("binding-path-escape", path_escape))
    controls.append(expect_failure("label-preserving-plus-sign-integer", lambda: semantic(
        lambda value: value["residual_prefix"][0].__setitem__(
            "coefficient", "+"+value["residual_prefix"][0]["coefficient"]))))

    require(len(controls) == 15 and all(item["result"] == "REJECTED" for item in controls),
            "MUTANT_CENSUS", "not all hostile controls rejected")
    return controls


def make_receipt(root: pathlib.Path) -> dict[str, Any]:
    manifest_raw = git_blob(root, MANIFEST_COMMIT, GLOBAL_MANIFEST_PATH)
    result_raw = git_blob(root, RESULT_COMMIT, RESULT_PATH)
    finite_manifest_raw = git_blob(root, RESULT_COMMIT, FINITE_MANIFEST_PATH)
    member_raw = git_blob(root, RESULT_COMMIT, MEMBER_PATH)
    panel_raw = git_blob(root, RESULT_COMMIT, PANEL_PATH)
    stage_a_raw = git_blob(root, RESULT_COMMIT, STAGE_A_PATH)
    manifest = strict_json(manifest_raw, GLOBAL_MANIFEST_PATH)
    result = strict_json(result_raw, RESULT_PATH)
    finite_manifest = strict_json(finite_manifest_raw, FINITE_MANIFEST_PATH)
    member = strict_json(member_raw, MEMBER_PATH)
    panel = strict_json(panel_raw, PANEL_PATH)
    stage_a = strict_json(stage_a_raw, STAGE_A_PATH)

    semantics = validate_result_semantics(result, manifest, member, stage_a)
    member_info = validate_member(member, finite_manifest, panel)
    custody = validate_custody(root, manifest_raw, result_raw, manifest, result, finite_manifest)
    replay = independent_replay(root, result, member, panel, stage_a, member_info)
    mutants = mutation_controls(result_raw, result, manifest, member, stage_a, root)

    require(replay["independent_prefix_directions_i8_sha256"]
            == result["residual_prefix_directions_i8_sha256"],
            "INDEPENDENT_PREFIX_DIGEST", "direction digest")
    require(replay["independent_prefix_coefficients_decimal_lf_sha256"]
            == result["residual_prefix_exact_residuals_decimal_lf_sha256"],
            "INDEPENDENT_PREFIX_DIGEST", "coefficient digest")

    generated = dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    head = git(root, "rev-parse", "HEAD").decode().strip()
    return {
        "schema": "max11-g0167-g0164-global-result-audit-v1",
        "result": "RESULT_AUDIT_PASS_T1",
        "overall": "PASS",
        "generated_utc": generated,
        "auditor": {
            "agent": "PurpleBison", "program": "codex", "model_family": "openai-gpt-5",
            "independence_tier": "T1_SAME_LINEAGE_FRESH_CONTEXT_DISJOINT_IMPLEMENTATION",
        },
        "audit_code_parent_head": head,
        "validator": {
            "path": VALIDATOR_PATH,
            "sha256": sha256_file(root / VALIDATOR_PATH)[0],
            "independent_route_path": CPP_PATH,
            "independent_route_sha256": replay["cpp_source_sha256"],
        },
        "preregistration": {
            "path": PREREG_PATH, "commit": PREREG_COMMIT,
            "sha256": sha256_bytes(git_blob(root, head, PREREG_PATH)),
        },
        "claim_boundary": (
            "PASS validates the frozen G-0164 EXACT_RESIDUAL_CONTINUE branch for the exact "
            "manifest-bound 304-term all-128 direct-basis member: exact 540-row finite replay, "
            "the complete 128-item signed-lex residual prefix through its last item, and the exact "
            "first nonzero hinge. It does not establish family completeness, frozen-family "
            "nonmembership, an unrestricted depth theorem, a lower bound, minimality, the all-n "
            "target, REFEREED/FORMALIZED standing, or a Lean theorem."
        ),
        "subject": custody,
        "verdict": {
            "exact_result_classification": "EXACT_RESIDUAL_CONTINUE",
            "classification": "PASS",
            "custody": "PASS_LOCAL_HASH_ATTESTATION",
            "schema": "PASS",
            "complete_declared_census": "PASS",
            "prefix_order_and_digests": "PASS",
            "independent_finite_replay": "PASS",
            "independent_first_nonzero": "PASS",
            "hostile_controls": "PASS",
        },
        "census": {
            key: semantics[key] for key in (
                "terms", "term_receipts", "labelled_permutations", "accumulated_rows",
                "selected_pool_rows", "prefix_rows",
            )
        },
        "independent_replay": replay,
        "hostile_controls": mutants,
        "scientific_flags": {
            "production_run_command_executed": False,
            "production_executable_executed": False,
            "producer_or_result_modified": False,
            "independent_540_row_finite_replay": True,
            "independent_complete_128_prefix_replay": True,
            "independent_first_nonzero_replay": True,
            "full_196125_direction_global_map_recomputed": False,
            "all_304_term_normal_form_payloads_recomputed": False,
        },
        "limitations": [
            (
                "T1 only: the auditor is GPT-5 lineage; no human/different-lineage T2 transport "
                "is authenticated, so this receipt cannot earn REFEREED, PROVED_HERE, or PROVED."
            ),
            (
                f"{custody['input_snapshot_working_only']} of 104 finite input-snapshot files "
                "(including the 789 MB panel cache) are absent from the frozen Git tree. Their "
                "current bytes matched the SHA-256 values frozen in the manifest before replay; "
                "the cache was rehashed unchanged afterward. A clone alone cannot reproduce them."
            ),
            (
                "The independent route recomputed all 540 finite rows and every mathematically "
                "possible canonical direction through the 128th reported residual-prefix item. "
                "It did not regenerate the entire 196,125-direction aggregate map, so the opaque "
                "aggregate_hinge/nonzero_hinge/complete_residual digest preimages and each of the "
                "304 per-term normal-form digest preimages received structural/reconciliation "
                "checks, not a second full global-map replay."
            ),
            (
                "Git/Agent-Mail custody is a local procedural attestation without signatures, "
                "provider authentication, or protection against same-user history rewriting."
            ),
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="emit one JSON receipt")
    arguments = parser.parse_args()
    root = pathlib.Path(__file__).resolve().parents[3]
    try:
        receipt = make_receipt(root)
    except AuditFailure as error:
        failure = {
            "schema": "max11-g0167-g0164-global-result-audit-v1",
            "result": "RESULT_AUDIT_FAIL",
            "overall": "FAIL",
            "failure_code": error.code,
            "failure": error.message,
        }
        print(json.dumps(failure, indent=2, sort_keys=False))
        return 1
    if arguments.json:
        print(json.dumps(receipt, indent=2, sort_keys=False))
    else:
        print(f"{receipt['overall']}: {receipt['verdict']['exact_result_classification']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
