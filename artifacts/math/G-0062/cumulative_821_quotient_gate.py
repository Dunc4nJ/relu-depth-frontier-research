#!/usr/bin/env python3
"""Two-prime cumulative quotient gate for the frozen 821-column family.

The ordered family is exactly

1. sequence 92,489;
2. the 328 G-0059 MAX10-induced proper mass-four atoms in certificate order;
3. the 492 nonzero-G-0053-price G-0055 scheduled atoms not already in (2),
   preserving G-0055 priority-block order.

For each frozen prime, this script reuses only the hash-bound G-0059 pivot
profile, regenerates the exact integer baseline and candidate semantics, and
tests the decisive batch condition

    rank([R_821; delta_821]) - rank(R_821).

The G-0059 prefix and the new 492-column suffix are also measured, but neither
separate-family result substitutes for the cumulative gate.  Any modular gain
is replayed on all 99,858 rows and remains only an exact-Q lift target.
"""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from types import ModuleType
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0055_SCRIPT = ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule.py"
G0055_REPORT = ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule_v1.json.gz"
G0059_SCRIPT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle.py"
G0059_REPORT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz"

EXPECTED_G0055_SCRIPT_SHA256 = "5f78397925e0873b696dc9d4b6c0562b9af58a0198e74ca636049f932fbade17"
EXPECTED_G0055_REPORT_SHA256 = "f6e6c824cbebab126f7452bc922859f5b53fa54f1af91cfb71dfefca41ba5cdc"
EXPECTED_G0055_SCIENTIFIC_SHA256 = "c52b164b769325a3662b1ae273fe3b9db44b4ffc54a053b6a105363feb6f965f"
EXPECTED_G0055_PRIORITY_BLOCKS_SHA256 = "1a2c4c378fc2dc2b719c2a6be091e89bcf04fc9fdd08aeb84060a000b8056526"
EXPECTED_G0055_PER_RECORD_SHA256 = "3985c6d5b32bec227d13fba3d3921d61606f850da984a921683bd8efe699daf4"

EXPECTED_G0059_COMMIT = "0d2d1a4cbb44d326a4984333cffd1a2aa6ea8c1d"
EXPECTED_G0059_SCRIPT_SHA256 = "dd743b702a99541e835b52bbdf5ec4c50c9650344bdf2ea0d4f81d22a7678ecd"
EXPECTED_G0059_REPORT_SHA256 = "72ade3d6c9c507d6843f161419dc92b7b1273a299a7eff7c9def6a7d3e0ddb37"
EXPECTED_G0059_SCIENTIFIC_SHA256 = "9f5d1dfde5a8ccaa4e0e02d98a588e41025c1a973211a7829f14af9ab74c5d6b"
EXPECTED_G0059_PREFIX_STREAM_SHA256 = "8726374387e48b1c91f14a59fc38328e6d3fdecc36f3840e3b0dd0437b446b7f"
EXPECTED_MAX10_ORDER_SHA256 = "6b967f3604ef2774ebf2d5c6c1860ea2da5328a77a97673acb2cff9ad16d60f1"

EXPECTED_OVERLAP_32_SHA256 = "65aac698e49b796965f0e5fbd067886245d6c97b916e8e0c29d0400a3d8f66c9"
EXPECTED_NEW_492_ORDER_SHA256 = "996b1f3a41a363143a6ba1ff61b69bc4e87a2c3f4f76458a2851d9480289a142"
EXPECTED_CUMULATIVE_821_ORDER_SHA256 = "b5950af7c92da6d0eec708c2ba05ab0c8dbec5d7f7b4e9f0084aca86c4a9ba08"

EXPECTED_SCHEDULED = 2_058
EXPECTED_NONZERO = 524
EXPECTED_OVERLAP = 32
EXPECTED_NEW = 492
EXPECTED_PREFIX = 329
EXPECTED_CUMULATIVE = 821
EXPECTED_ROWS = 99_858
EXPECTED_BASELINE_COLUMNS = 1_358
EXPECTED_BASELINE_RANK = 1_288
EXPECTED_PREFIX_RANK = 323
PRIMES = (1_000_003, 1_000_033)

DEFAULT_OUTPUT = HERE / "cumulative_821_quotient_gate_v1.json.gz"
SCHEMA = "max11-g0062-cumulative-821-modular-quotient-gate-v1"


class GateError(RuntimeError):
    """Fail-closed input, semantic, algebra, or report error."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise GateError(f"top-level object required: {path}")
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise GateError(f"bound script drift: {path}: {observed} != {expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def git_blob_sha256(commit: str, relative_path: str) -> str:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{relative_path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode:
        raise GateError(
            f"cannot read bound Git blob {commit}:{relative_path}: "
            f"{completed.stderr.decode(errors='replace').strip()}"
        )
    return hashlib.sha256(completed.stdout).hexdigest()


def deterministic_scientific_view(value: object) -> object:
    """Strip every runtime measurement and resource threshold recursively."""

    dynamic_keys = {
        "seconds",
        "wall_seconds",
        "semantic_seconds",
        "available_gib",
        "minimum_available_gib",
        "minimum_required_gib",
        "resource_preflight",
        "workers",
    }
    if isinstance(value, dict):
        return {
            key: deterministic_scientific_view(item)
            for key, item in value.items()
            if key not in dynamic_keys
            and not key.endswith("_seconds")
            and not key.endswith("_gib")
        }
    if isinstance(value, list):
        return [deterministic_scientific_view(item) for item in value]
    return value


def checked_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    expected_files = {
        "g0055_script_sha256": EXPECTED_G0055_SCRIPT_SHA256,
        "g0055_report_sha256": EXPECTED_G0055_REPORT_SHA256,
        "g0059_script_sha256": EXPECTED_G0059_SCRIPT_SHA256,
        "g0059_report_sha256": EXPECTED_G0059_REPORT_SHA256,
    }
    observed_files = {
        "g0055_script_sha256": sha256_path(G0055_SCRIPT),
        "g0055_report_sha256": sha256_path(G0055_REPORT),
        "g0059_script_sha256": sha256_path(G0059_SCRIPT),
        "g0059_report_sha256": sha256_path(G0059_REPORT),
    }
    if observed_files != expected_files:
        raise GateError(f"input file drift: observed={observed_files}, expected={expected_files}")

    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", EXPECTED_G0059_COMMIT, "HEAD"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if ancestor.returncode:
        raise GateError(f"bound G-0059 commit is not an ancestor of HEAD: {EXPECTED_G0059_COMMIT}")
    committed_script = git_blob_sha256(
        EXPECTED_G0059_COMMIT, "artifacts/math/G-0059/modular_quotient_oracle.py"
    )
    committed_report = git_blob_sha256(
        EXPECTED_G0059_COMMIT,
        "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz",
    )
    if committed_script != EXPECTED_G0059_SCRIPT_SHA256 or committed_report != EXPECTED_G0059_REPORT_SHA256:
        raise GateError("G-0059 commit blob binding drift")

    g0055 = load_json_gz(G0055_REPORT)
    g0059 = load_json_gz(G0059_REPORT)
    if (
        g0055.get("script_sha256") != EXPECTED_G0055_SCRIPT_SHA256
        or g0055.get("canonical_scientific_payload_sha256")
        != EXPECTED_G0055_SCIENTIFIC_SHA256
        or g0055.get("priority_blocks_sha256")
        != EXPECTED_G0055_PRIORITY_BLOCKS_SHA256
        or g0055.get("exact_first_block_pricing", {}).get("per_record_sha256")
        != EXPECTED_G0055_PER_RECORD_SHA256
        or canonical_sha256(g0055.get("priority_blocks"))
        != EXPECTED_G0055_PRIORITY_BLOCKS_SHA256
        or canonical_sha256(g0055.get("exact_first_block_pricing", {}).get("per_record"))
        != EXPECTED_G0055_PER_RECORD_SHA256
    ):
        raise GateError("G-0055 report binding or internal hash drift")
    if (
        g0059.get("script_sha256") != EXPECTED_G0059_SCRIPT_SHA256
        or g0059.get("canonical_scientific_payload_sha256")
        != EXPECTED_G0059_SCIENTIFIC_SHA256
        or g0059.get("result")
        != "NO_JOINT_329_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME"
        or g0059.get("candidate_semantics", {}).get("ordered_sparse_stream_sha256")
        != EXPECTED_G0059_PREFIX_STREAM_SHA256
        or g0059.get("max10_induced_block_reconstruction", {}).get(
            "term_order_sequence_sha256"
        )
        != EXPECTED_MAX10_ORDER_SHA256
    ):
        raise GateError("G-0059 report binding or scientific payload drift")
    prefix_records = [
        item["joint_sequence_92489_plus_max10_block"]["full_prefix"]
        for item in g0059.get("prime_results", [])
    ]
    if len(prefix_records) != 2 or any(
        int(item.get("prefix", -1)) != EXPECTED_PREFIX
        or int(item.get("rank_residual", -1)) != EXPECTED_PREFIX_RANK
        or int(item.get("rank_residual_plus_delta", -1)) != EXPECTED_PREFIX_RANK
        or int(item.get("augmented_gain", -1)) != 0
        for item in prefix_records
    ):
        raise GateError("G-0059 frozen prefix rank record drift")

    bindings: dict[str, Any] = {
        **observed_files,
        "g0055_scientific_payload_sha256": EXPECTED_G0055_SCIENTIFIC_SHA256,
        "g0059_commit": EXPECTED_G0059_COMMIT,
        "g0059_commit_script_blob_sha256": committed_script,
        "g0059_commit_report_blob_sha256": committed_report,
        "g0059_scientific_payload_sha256": EXPECTED_G0059_SCIENTIFIC_SHA256,
        "g0059_upstream_bindings": g0059["bindings"],
    }
    return bindings, g0055, g0059


def reconstruct_selection(
    g0055: dict[str, Any], g0059: dict[str, Any]
) -> tuple[list[int], list[int], list[int], dict[str, Any]]:
    records = list(g0055["exact_first_block_pricing"]["per_record"])
    if len(records) != EXPECTED_SCHEDULED:
        raise GateError("G-0055 scheduled record census drift")
    prices = {int(item["sequence"]): int(item["pairing_numerator"]) for item in records}
    if len(prices) != EXPECTED_SCHEDULED:
        raise GateError("G-0055 scheduled sequences are not unique")
    scheduled_order = [
        int(sequence)
        for block in g0055["priority_blocks"]
        for sequence in block["sequences"]
    ]
    if (
        len(scheduled_order) != EXPECTED_SCHEDULED
        or len(set(scheduled_order)) != EXPECTED_SCHEDULED
        or set(scheduled_order) != set(prices)
    ):
        raise GateError("G-0055 priority-block order does not reconcile to priced records")
    nonzero_order = [sequence for sequence in scheduled_order if prices[sequence] != 0]
    if len(nonzero_order) != EXPECTED_NONZERO:
        raise GateError("G-0055 nonzero-price census drift")

    manifest = g0059["max10_induced_block_reconstruction"]["manifest"]
    max10_order = [int(item["g0038_sequence"]) for item in manifest]
    if len(max10_order) != 328 or len(set(max10_order)) != 328:
        raise GateError("G-0059 MAX10-induced order census drift")
    if canonical_sha256(max10_order) != EXPECTED_MAX10_ORDER_SHA256:
        raise GateError("G-0059 MAX10-induced order hash drift")
    max10_set = set(max10_order)
    overlap = [sequence for sequence in nonzero_order if sequence in max10_set]
    first_block = list(map(int, g0055["priority_blocks"][0]["sequences"]))
    if (
        len(overlap) != EXPECTED_OVERLAP
        or overlap != first_block
        or any(prices[sequence] == 0 for sequence in overlap)
        or canonical_sha256(overlap) != EXPECTED_OVERLAP_32_SHA256
    ):
        raise GateError("G-0055/G-0059 overlap is not exactly the first 32-column priority block")

    new_order = [sequence for sequence in nonzero_order if sequence not in max10_set]
    cumulative_order = [92_489, *max10_order, *new_order]
    if (
        len(new_order) != EXPECTED_NEW
        or len(set(new_order)) != EXPECTED_NEW
        or canonical_sha256(new_order) != EXPECTED_NEW_492_ORDER_SHA256
        or len(cumulative_order) != EXPECTED_CUMULATIVE
        or len(set(cumulative_order)) != EXPECTED_CUMULATIVE
        or canonical_sha256(cumulative_order) != EXPECTED_CUMULATIVE_821_ORDER_SHA256
    ):
        raise GateError("new-492 or cumulative-821 ordered selection drift")
    metadata = {
        "g0055_scheduled_record_count": len(scheduled_order),
        "g0055_nonzero_price_record_count": len(nonzero_order),
        "max10_induced_count": len(max10_order),
        "overlap_count": len(overlap),
        "overlap_is_exactly_first_priority_block": True,
        "overlap_order_sha256": canonical_sha256(overlap),
        "new_nonzero_price_count": len(new_order),
        "new_492_order_sha256": canonical_sha256(new_order),
        "cumulative_821_order_sha256": canonical_sha256(cumulative_order),
        "ordered_composition": [
            {"positions": [0, 0], "family": "single support-eight atom", "sequence": 92_489},
            {
                "positions": [1, 328],
                "family": "328 MAX10-induced atoms in original certificate-term order",
            },
            {
                "positions": [329, 820],
                "family": "492 new G-0055 nonzero-price scheduled atoms in priority-block order",
            },
        ],
    }
    return max10_order, new_order, cumulative_order, metadata


def validate_frozen_profiles(
    g0059: ModuleType,
    g0059_report: dict[str, Any],
    baseline_union_rows: np.ndarray,
) -> list[dict[str, Any]]:
    profiles = list(g0059_report["baseline"]["per_prime_rank_profiles_and_preserved_nullspaces"])
    prime_results = list(g0059_report["prime_results"])
    if [int(item["prime"]) for item in profiles] != list(PRIMES):
        raise GateError("G-0059 profile prime order drift")
    for profile, old_result in zip(profiles, prime_results, strict=True):
        columns = list(map(int, profile["pivot_columns"]))
        positions = list(map(int, profile["pivot_union_row_positions"]))
        complete_rows = baseline_union_rows[positions].astype(int).tolist()
        if (
            int(profile["rank"]) != EXPECTED_BASELINE_RANK
            or int(profile["nullity"]) != 70
            or len(columns) != EXPECTED_BASELINE_RANK
            or len(set(columns)) != EXPECTED_BASELINE_RANK
            or len(positions) != EXPECTED_BASELINE_RANK
            or len(set(positions)) != EXPECTED_BASELINE_RANK
            or g0059.canonical_sha256(columns) != profile["pivot_columns_sha256"]
            or g0059.canonical_sha256(positions)
            != profile["pivot_union_row_positions_sha256"]
            or g0059.canonical_sha256(complete_rows)
            != old_result["pivot_minor"]["pivot_complete_rows_sha256"]
            or complete_rows != old_result["pivot_minor"]["pivot_complete_rows"]
        ):
            raise GateError(f"frozen G-0059 pivot profile drift at {profile['prime']}")
    if (
        profiles[0]["pivot_columns"] != profiles[1]["pivot_columns"]
        or profiles[0]["pivot_union_row_positions"]
        != profiles[1]["pivot_union_row_positions"]
    ):
        raise GateError("G-0059 primes no longer share the frozen pivot minor")
    return profiles


def prepare_semantics(
    g0059: ModuleType,
    g0055_report: dict[str, Any],
    g0059_report: dict[str, Any],
    workers: int,
) -> tuple[
    ModuleType,
    list[dict[str, Any]],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[dict[str, Any]],
    dict[str, Any],
]:
    _max10_order, new_order, cumulative_order, selection = reconstruct_selection(
        g0055_report, g0059_report
    )
    upstream_bindings, bound_g0057_report, bound_g0058_report = g0059.checked_bindings()
    if upstream_bindings != g0059_report["bindings"]:
        raise GateError("current G-0057/G-0058/MAX10 inputs differ from bound G-0059 inputs")
    g0057 = g0059.import_bound(
        "g0062_g0057", g0059.G0057_SCRIPT, g0059.EXPECTED_G0057_SCRIPT_SHA256
    )
    (
        _universe,
        baseline_results,
        prefix_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        _block_metadata,
        prefix_controls,
    ) = g0059.prepare_semantics(
        g0057,
        bound_g0057_report,
        bound_g0058_report,
        workers,
    )
    if (
        len(prefix_results) != EXPECTED_PREFIX
        or [int(item["sequence"]) for item in prefix_results]
        != cumulative_order[:EXPECTED_PREFIX]
        or g0057.ordered_sparse_stream_hash(prefix_results)
        != EXPECTED_G0059_PREFIX_STREAM_SHA256
    ):
        raise GateError("regenerated G-0059 prefix semantics drift")

    mass4_records = g0057.read_mass4_records(g0057.THEOREM, set(new_order))
    if set(mass4_records) != set(new_order):
        raise GateError("new-492 mass-four record extraction incomplete")
    payloads = [
        (position, "g0062_g0055_new_nonzero_price", position, mass4_records[sequence])
        for position, sequence in enumerate(new_order)
    ]
    new_results, new_semantic_seconds = g0057.generate_semantics(
        payloads, g0057.ROW_INDEX, workers, "G0062_NEW492_SEMANTIC"
    )
    if [int(item["sequence"]) for item in new_results] != new_order:
        raise GateError("new-492 semantic order drift")
    candidate_results = prefix_results + new_results
    if (
        len(candidate_results) != EXPECTED_CUMULATIVE
        or [int(item["sequence"]) for item in candidate_results] != cumulative_order
        or any(int(item["lambda"]) for item in candidate_results)
        or any(int(item["active_vertices"]) >= 11 for item in candidate_results)
    ):
        raise GateError("cumulative candidate semantics are not 821 proper zero-lambda columns")
    semantic_metadata = {
        "g0059_upstream_inputs_revalidated_before_semantic_generation": True,
        "prefix_controls": prefix_controls,
        "new_492_semantic_seconds": new_semantic_seconds,
        "new_492_ordered_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(new_results),
        "cumulative_821_ordered_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(
            candidate_results
        ),
        "all_821_candidates_are_proper": True,
        "all_821_candidate_lambdas_are_zero": True,
    }
    return (
        g0057,
        baseline_results,
        candidate_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        new_results,
        {"selection": selection, "semantics": semantic_metadata},
    )


def replay_potent_circuit(
    g0059: ModuleType,
    g0057: ModuleType,
    prime: int,
    prefix: int,
    residual: np.ndarray,
    delta: np.ndarray,
    coefficients: np.ndarray,
    pivot_columns: list[int],
    baseline_results: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
) -> dict[str, Any]:
    candidate_coefficients, quotient_witness = g0059.quotient_potent_vector(
        residual, delta, prime, prefix
    )
    baseline_pivot_coefficients = np.remainder(
        -(coefficients[:, :prefix] @ candidate_coefficients), prime
    ).astype(np.int64, copy=False)
    full_coefficients = [0] * (EXPECTED_BASELINE_COLUMNS + prefix)
    for position, column in enumerate(pivot_columns):
        full_coefficients[column] = int(baseline_pivot_coefficients[position])
    for position, value in enumerate(candidate_coefficients):
        full_coefficients[EXPECTED_BASELINE_COLUMNS + position] = int(value)
    replay = g0057.replay_witness(
        baseline_results + candidate_results[:prefix], full_coefficients, prime
    )
    return {
        "first_gain_prefix": prefix,
        "last_added_candidate_position": prefix - 1,
        "last_added_sequence": int(candidate_results[prefix - 1]["sequence"]),
        "quotient_witness": quotient_witness,
        "baseline_pivot_coefficients": baseline_pivot_coefficients.astype(int).tolist(),
        "baseline_pivot_coefficients_sha256": g0059.canonical_sha256(
            baseline_pivot_coefficients.astype(int).tolist()
        ),
        "candidate_coefficients": candidate_coefficients.astype(int).tolist(),
        "candidate_coefficients_sha256": g0059.canonical_sha256(
            candidate_coefficients.astype(int).tolist()
        ),
        "full_99858_row_replay": replay,
    }


def analyze_prime(
    g0059: ModuleType,
    g0057: ModuleType,
    prime: int,
    profile: dict[str, Any],
    old_result: dict[str, Any],
    baseline_union_rows: np.ndarray,
    baseline_matrix: np.ndarray,
    lambda_row: np.ndarray,
    combined_rows: np.ndarray,
    baseline_positions: np.ndarray,
    candidate_matrix: np.ndarray,
    baseline_results: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
) -> dict[str, Any]:
    started = time.perf_counter()
    columns = list(map(int, profile["pivot_columns"]))
    row_positions = list(map(int, profile["pivot_union_row_positions"]))
    complete_pivot_rows = baseline_union_rows[row_positions].astype(np.uint32, copy=False)
    minor = np.ascontiguousarray(
        baseline_matrix[np.ix_(row_positions, columns)], dtype=np.int64
    )
    minor_field = g0059.to_nmod(minor, prime)
    determinant = int(minor_field.det())
    if not determinant or determinant != int(old_result["pivot_minor"]["determinant_mod_prime"]):
        raise GateError(f"frozen pivot minor determinant drift at {prime}")

    lambda_c = np.remainder(lambda_row[columns], prime).astype(np.int64, copy=False)
    dual = np.asarray(
        old_result["sparse_on_pivot_rows_dual"]["weights_mod_prime"], dtype=np.int64
    )
    baseline_on_rows = np.ascontiguousarray(baseline_matrix[row_positions, :], dtype=np.int64)
    dual_replay = g0059.from_nmod(
        g0059.to_nmod(dual.reshape(1, -1), prime)
        * g0059.to_nmod(baseline_on_rows, prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_replay - lambda_row, prime)):
        raise GateError(f"frozen sparse dual failed regenerated baseline replay at {prime}")

    complete_to_combined = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    complete_to_combined[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    pivot_combined_positions = complete_to_combined[complete_pivot_rows]
    if np.any(pivot_combined_positions < 0):
        raise GateError("pivot row escaped cumulative union")
    candidate_on_rows = np.ascontiguousarray(
        candidate_matrix[pivot_combined_positions, :], dtype=np.int64
    )
    coefficients_field = minor_field.solve(g0059.to_nmod(candidate_on_rows, prime))
    coefficients = g0059.from_nmod(coefficients_field)
    solved = g0059.from_nmod(minor_field * coefficients_field)
    if np.any(np.remainder(solved - candidate_on_rows, prime)):
        raise GateError(f"B^-1 cumulative candidate solve replay failed at {prime}")
    old_coefficients = np.asarray(
        old_result["candidate_schur_coefficients"]["candidate_major_mod_prime"],
        dtype=np.int64,
    ).T
    if (
        old_coefficients.shape != (EXPECTED_BASELINE_RANK, EXPECTED_PREFIX)
        or np.any(np.remainder(coefficients[:, :EXPECTED_PREFIX] - old_coefficients, prime))
    ):
        raise GateError(f"regenerated G-0059 prefix Schur coefficients drift at {prime}")

    basis = np.ascontiguousarray(baseline_matrix[:, columns], dtype=np.int64)
    predicted_on_baseline = g0059.from_nmod(
        g0059.to_nmod(basis, prime) * coefficients_field
    )
    residual = np.remainder(candidate_matrix, prime).astype(np.int64, copy=False)
    residual[baseline_positions, :] = np.remainder(
        residual[baseline_positions, :] - predicted_on_baseline, prime
    )
    if np.any(residual[pivot_combined_positions, :]):
        raise GateError(f"cumulative Schur residual nonzero on pivot rows at {prime}")
    delta = np.remainder(
        -np.remainder(lambda_c @ coefficients, prime), prime
    ).astype(np.int64, copy=False)
    dual_prices = np.remainder(
        dual @ np.remainder(candidate_on_rows, prime), prime
    ).astype(np.int64, copy=False)
    if np.any(np.remainder(dual_prices + delta, prime)):
        raise GateError(f"dual-price/delta bridge failed at {prime}")

    prefix_record = g0059.rank_record(
        residual[:, :EXPECTED_PREFIX], delta[:EXPECTED_PREFIX], prime, EXPECTED_PREFIX
    )
    if (
        int(prefix_record["rank_residual"]) != EXPECTED_PREFIX_RANK
        or int(prefix_record["rank_residual_plus_delta"]) != EXPECTED_PREFIX_RANK
        or int(prefix_record["augmented_gain"]) != 0
    ):
        raise GateError(f"G-0059 prefix 323/323 no-gain replay failed at {prime}")
    suffix_residual = residual[:, EXPECTED_PREFIX:]
    suffix_delta = delta[EXPECTED_PREFIX:]
    suffix_record = g0059.rank_record(
        suffix_residual, suffix_delta, prime, EXPECTED_NEW
    )
    first_record, cumulative_queries = g0059.first_gain_prefix(residual, delta, prime)
    cumulative_full = next(
        item for item in cumulative_queries if int(item["prefix"]) == EXPECTED_CUMULATIVE
    )
    if int(suffix_record["augmented_gain"]) > int(cumulative_full["augmented_gain"]):
        raise GateError("subfamily gain exceeded cumulative-family gain")
    potent_circuit = None
    if int(cumulative_full["augmented_gain"]):
        first_prefix = int(first_record["prefix"])
        if first_prefix <= EXPECTED_PREFIX:
            raise GateError("first cumulative gain contradicts frozen no-gain prefix")
        potent_circuit = replay_potent_circuit(
            g0059,
            g0057,
            prime,
            first_prefix,
            residual,
            delta,
            coefficients,
            columns,
            baseline_results,
            candidate_results,
        )

    result = {
        "prime": prime,
        "frozen_baseline_rank": int(profile["rank"]),
        "frozen_baseline_nullity": int(profile["nullity"]),
        "pivot_minor": {
            "rank": len(columns),
            "pivot_columns_sha256": g0059.canonical_sha256(columns),
            "pivot_complete_rows_sha256": g0059.canonical_sha256(
                complete_pivot_rows.astype(int).tolist()
            ),
            "determinant_mod_prime": determinant,
            "minor_int64_sha256": hashlib.sha256(
                minor.astype("<i8", copy=False).tobytes(order="C")
            ).hexdigest(),
        },
        "frozen_sparse_dual": {
            "weights_sha256": g0059.canonical_sha256(dual.astype(int).tolist()),
            "all_1358_regenerated_baseline_columns_replayed": True,
        },
        "candidate_schur_coefficients": {
            "shape": list(coefficients.shape),
            "candidate_major_mod_prime": coefficients.T.astype(int).tolist(),
            "candidate_major_sha256": g0059.canonical_sha256(
                coefficients.T.astype(int).tolist()
            ),
            "first_329_equal_frozen_g0059_coefficients": True,
            "all_B_times_a_equal_h_R": True,
        },
        "g0059_prefix_329_replay": {
            **prefix_record,
            "residual_matrix_sha256": g0059.array_sha256(
                residual[:, :EXPECTED_PREFIX]
            ),
            "delta_sha256": g0059.array_sha256(delta[:EXPECTED_PREFIX]),
        },
        "new_492_only_diagnostic": {
            **suffix_record,
            "residual_matrix_sha256": g0059.array_sha256(suffix_residual),
            "delta_sha256": g0059.array_sha256(suffix_delta),
            "not_a_substitute_for_cumulative_gate": True,
        },
        "cumulative_821_primary_gate": {
            "full_prefix": cumulative_full,
            "first_gain_prefix": (
                int(first_record["prefix"])
                if int(cumulative_full["augmented_gain"])
                else None
            ),
            "binary_search_rank_queries": cumulative_queries,
            "residual_matrix_shape": list(residual.shape),
            "residual_matrix_sha256": g0059.array_sha256(residual),
            "delta_sha256": g0059.array_sha256(delta),
            "potent_circuit": potent_circuit,
        },
        "all_residuals_zero_on_pivot_rows": True,
        "all_dual_prices_equal_negative_delta": True,
        "seconds": time.perf_counter() - started,
    }
    del (
        solved,
        predicted_on_baseline,
        residual,
        coefficients_field,
        minor_field,
        candidate_on_rows,
        basis,
    )
    gc.collect()
    return result


def synthetic_controls(g0059: ModuleType) -> dict[str, Any]:
    controls = g0059.synthetic_schur_controls()
    if (
        int(controls["joint_regression_left_singleton_has_no_gain"]["augmented_gain"])
        or int(controls["joint_regression_right_singleton_has_no_gain"]["augmented_gain"])
        or int(controls["two_column_potent_circuit_has_gain"]["augmented_gain"]) != 1
        or not controls.get("passed")
    ):
        raise GateError("joint-family synthetic regression failed")
    return controls


def synthetic_projection_control() -> dict[str, Any]:
    """A novel nested runtime key must not perturb the scientific digest."""

    left = {
        "science": {
            "rank": 7,
            "nested": {
                "keep": "bound",
                "novel_phase_seconds": 1.25,
                "novel_budget_gib": 16.0,
            },
        },
        "workers": 2,
        "resource_preflight": {"available_gib": 24.0, "passed": True},
    }
    right = {
        "science": {
            "rank": 7,
            "nested": {
                "keep": "bound",
                "novel_phase_seconds": 9_999.5,
                "novel_budget_gib": 128.0,
            },
        },
        "workers": 64,
        "resource_preflight": {"available_gib": 256.0, "passed": False},
    }
    expected = {"science": {"rank": 7, "nested": {"keep": "bound"}}}
    projected_left = deterministic_scientific_view(left)
    projected_right = deterministic_scientific_view(right)
    if projected_left != expected or projected_right != expected:
        raise GateError("novel nested runtime/resource suffix escaped scientific projection")
    if canonical_sha256(projected_left) != canonical_sha256(projected_right):
        raise GateError("scientific projection changed under runtime-only perturbation")
    return {
        "novel_nested_seconds_suffix_removed": True,
        "novel_nested_gib_suffix_removed": True,
        "explicit_worker_and_resource_preflight_keys_removed": True,
        "runtime_perturbation_leaves_projection_unchanged": True,
        "projected_fixture_sha256": canonical_sha256(expected),
        "passed": True,
    }


def result_label(prime_results: list[dict[str, Any]]) -> str:
    gains = [
        int(item["cumulative_821_primary_gate"]["full_prefix"]["augmented_gain"])
        for item in prime_results
    ]
    if gains == [0, 0]:
        return "NO_CUMULATIVE_821_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME"
    if gains == [1, 1]:
        return "BOTH_PRIMES_CUMULATIVE_821_HAS_REPLAYED_QUOTIENT_GAIN"
    return "MIXED_PRIME_CUMULATIVE_821_QUOTIENT_OUTCOME"


SCIENTIFIC_KEYS = (
    "schema",
    "result",
    "bindings",
    "family_selection",
    "exact_integer_semantics",
    "baseline_profile_reuse",
    "candidate_union",
    "prime_results",
    "cross_prime_comparison",
    "controls",
    "epistemic_status",
    "claim_boundary",
)


def run(workers: int, minimum_available_gib: float) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    bindings, g0055_report, g0059_report = checked_inputs()
    g0059 = import_bound("g0062_g0059", G0059_SCRIPT, EXPECTED_G0059_SCRIPT_SHA256)
    preflight = g0059.import_bound(
        "g0062_preflight_g0057", g0059.G0057_SCRIPT, g0059.EXPECTED_G0057_SCRIPT_SHA256
    ).resource_preflight(minimum_available_gib)
    synthetic = synthetic_controls(g0059)
    synthetic_projection_control()
    (
        g0057,
        baseline_results,
        candidate_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        new_results,
        semantic_bundle,
    ) = prepare_semantics(g0059, g0055_report, g0059_report, workers)
    profiles = validate_frozen_profiles(g0059, g0059_report, baseline_union_rows)
    combined_rows, baseline_positions, candidate_matrix, combined_metadata = (
        g0059.build_candidate_matrix(baseline_union_rows, candidate_results)
    )
    prime_results = []
    for prime, profile, old_result in zip(
        PRIMES, profiles, g0059_report["prime_results"], strict=True
    ):
        prime_results.append(
            analyze_prime(
                g0059,
                g0057,
                prime,
                profile,
                old_result,
                baseline_union_rows,
                baseline_matrix,
                lambda_row,
                combined_rows,
                baseline_positions,
                candidate_matrix,
                baseline_results,
                candidate_results,
            )
        )
        gc.collect()

    cumulative_ranks = [
        [
            int(item["cumulative_821_primary_gate"]["full_prefix"]["rank_residual"]),
            int(
                item["cumulative_821_primary_gate"]["full_prefix"][
                    "rank_residual_plus_delta"
                ]
            ),
        ]
        for item in prime_results
    ]
    suffix_ranks = [
        [
            int(item["new_492_only_diagnostic"]["rank_residual"]),
            int(item["new_492_only_diagnostic"]["rank_residual_plus_delta"]),
        ]
        for item in prime_results
    ]
    first_gain_prefixes = [
        item["cumulative_821_primary_gate"]["first_gain_prefix"] for item in prime_results
    ]
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": result_label(prime_results),
        "bindings": bindings,
        "family_selection": semantic_bundle["selection"],
        "exact_integer_semantics": {
            **semantic_bundle["semantics"],
            "new_492_column_count": len(new_results),
            "cumulative_candidate_column_count": len(candidate_results),
        },
        "baseline_profile_reuse": {
            "source": "hash-bound G-0059 commit/report pivot profiles; no baseline RREF rerun",
            "profile_primes": [int(item["prime"]) for item in profiles],
            "pivot_columns_sha256": [item["pivot_columns_sha256"] for item in profiles],
            "pivot_union_row_positions_sha256": [
                item["pivot_union_row_positions_sha256"] for item in profiles
            ],
            "baseline_rank": EXPECTED_BASELINE_RANK,
            "baseline_nullity": 70,
        },
        "candidate_union": combined_metadata,
        "prime_results": prime_results,
        "cross_prime_comparison": {
            "g0059_prefix_329_ranks": [
                [
                    int(item["g0059_prefix_329_replay"]["rank_residual"]),
                    int(item["g0059_prefix_329_replay"]["rank_residual_plus_delta"]),
                ]
                for item in prime_results
            ],
            "new_492_only_diagnostic_ranks": suffix_ranks,
            "cumulative_821_primary_ranks": cumulative_ranks,
            "cumulative_821_augmented_gains": [right - left for left, right in cumulative_ranks],
            "cumulative_first_gain_prefixes": first_gain_prefixes,
            "first_gain_prefixes_agree_when_both_primes_gain": (
                first_gain_prefixes[0] == first_gain_prefixes[1]
                if [right - left for left, right in cumulative_ranks] == [1, 1]
                else None
            ),
            "no_exact_Q_inference_from_two_prime_agreement": True,
        },
        "controls": {
            "resource_preflight": preflight,
            "synthetic_schur_controls": synthetic,
            "selection_reconstructed_from_bound_g0055_and_g0059_reports": True,
            "script_unchanged_during_run": True,
        },
        "epistemic_status": "COMPUTED_BOUNDED_MODULAR_DISCOVERY_GATE",
        "claim_boundary": [
            "The primary conclusion concerns only the ordered cumulative family of 821 proper signed-mass-four columns over each separately reported finite field.",
            "The first 329 columns are sequence 92489 followed by the 328 MAX10-induced atoms in certificate order; the remaining 492 are exactly the nonzero-price G-0055 scheduled atoms not already in that MAX10 block, in G-0055 priority-block order.",
            "The new-492-only rank is diagnostic; separate no-gain results never imply cumulative no-gain.",
            "Agreement at two primes does not prove the corresponding rank or kernel over Q; exact reconstruction remains mandatory.",
            "This 821-column test is not a census of all 132728 proper mass-four atoms and says nothing directly about arbitrary-real-weight two-hidden-layer networks.",
        ],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
            "minimum_available_gib": minimum_available_gib,
        },
        "timing": {"wall_seconds": time.perf_counter() - started},
        "script_sha256": script_hash_before,
    }
    scientific_payload = {key: report[key] for key in SCIENTIFIC_KEYS}
    report["canonical_scientific_payload_sha256"] = canonical_sha256(
        deterministic_scientific_view(scientific_payload)
    )
    report["canonical_scientific_payload_projection"] = (
        "recursive projection excluding all runtime measurements, worker counts, resource "
        "preflights, and resource thresholds"
    )
    if sha256_path(Path(__file__)) != script_hash_before:
        raise GateError("script changed during execution")
    return report


def check_report(path: Path) -> dict[str, Any]:
    _bindings, g0055_report, g0059_report = checked_inputs()
    g0059 = import_bound("g0062_check_g0059", G0059_SCRIPT, EXPECTED_G0059_SCRIPT_SHA256)
    upstream_bindings, _g0057_report, _g0058_report = g0059.checked_bindings()
    if upstream_bindings != g0059_report["bindings"]:
        raise GateError("current upstream semantics differ from bound G-0059 inputs")
    reconstruct_selection(g0055_report, g0059_report)
    report = load_json_gz(path)
    if report.get("schema") != SCHEMA:
        raise GateError("report schema mismatch")
    if report.get("script_sha256") != sha256_path(Path(__file__)):
        raise GateError("report/script hash mismatch")
    scientific_payload = {key: report[key] for key in SCIENTIFIC_KEYS}
    observed_scientific = canonical_sha256(deterministic_scientific_view(scientific_payload))
    if report.get("canonical_scientific_payload_sha256") != observed_scientific:
        raise GateError("report scientific payload hash mismatch")
    if report.get("family_selection", {}).get("cumulative_821_order_sha256") != EXPECTED_CUMULATIVE_821_ORDER_SHA256:
        raise GateError("report cumulative order hash mismatch")
    prime_results = report.get("prime_results", [])
    if len(prime_results) != 2 or [int(item["prime"]) for item in prime_results] != list(PRIMES):
        raise GateError("report prime census/order mismatch")
    for item in prime_results:
        prefix = item["g0059_prefix_329_replay"]
        if (
            int(prefix["rank_residual"]) != EXPECTED_PREFIX_RANK
            or int(prefix["rank_residual_plus_delta"]) != EXPECTED_PREFIX_RANK
            or int(prefix["augmented_gain"]) != 0
        ):
            raise GateError("report does not replay the frozen 323/323 prefix")
        full = item["cumulative_821_primary_gate"]["full_prefix"]
        gain = int(full["augmented_gain"])
        witness = item["cumulative_821_primary_gate"]["potent_circuit"]
        if gain and (
            witness is None
            or not witness["full_99858_row_replay"]["all_99858_hinge_rows_zero_mod_prime"]
            or int(witness["full_99858_row_replay"]["lambda_mod_prime"]) != 1
        ):
            raise GateError("gaining report lacks a full normalized witness replay")
        if not gain and witness is not None:
            raise GateError("no-gain report unexpectedly carries a potent witness")
    expected_label = result_label(prime_results)
    if report.get("result") != expected_label:
        raise GateError("report top-level result does not match prime gates")
    return {
        "result": "REPORT_CHECK_PASS",
        "report": str(path),
        "report_sha256": sha256_path(path),
        "script_sha256": sha256_path(Path(__file__)),
        "scientific_payload_sha256": observed_scientific,
        "scientific_projection_excludes_runtime_and_resource_thresholds": True,
    }


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--minimum-available-gib", type=float, default=16.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--check-report", type=Path)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.check_report is not None:
        print(json.dumps(check_report(args.check_report.resolve()), sort_keys=True))
        return
    bindings, g0055_report, g0059_report = checked_inputs()
    g0059 = import_bound("g0062_main_g0059", G0059_SCRIPT, EXPECTED_G0059_SCRIPT_SHA256)
    if args.self_test:
        upstream_bindings, _g0057_report, _g0058_report = g0059.checked_bindings()
        if upstream_bindings != g0059_report["bindings"]:
            raise GateError("current upstream semantics differ from bound G-0059 inputs")
        _max10, _new, _all, selection = reconstruct_selection(g0055_report, g0059_report)
        controls = synthetic_controls(g0059)
        controls["scientific_projection_hostile_regression"] = (
            synthetic_projection_control()
        )
        print(
            json.dumps(
                {
                    "result": "SELF_TEST_PASS",
                    "bindings": bindings,
                    "selection": selection,
                    "controls": controls,
                },
                sort_keys=True,
            )
        )
        return
    g0057 = g0059.import_bound(
        "g0062_main_g0057", g0059.G0057_SCRIPT, g0059.EXPECTED_G0057_SCRIPT_SHA256
    )
    if args.preflight_only:
        print(json.dumps(g0057.resource_preflight(args.minimum_available_gib), sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.minimum_available_gib)
    write_gzip_atomic(output, report)
    checked = check_report(output)
    print(
        json.dumps(
            {
                "result": report["result"],
                "output": str(output),
                "report_check": checked,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
