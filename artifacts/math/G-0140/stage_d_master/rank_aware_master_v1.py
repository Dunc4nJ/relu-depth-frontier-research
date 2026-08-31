#!/usr/bin/env python3
"""Outcome-blind reopened exact-Q master for G-0140.

This producer consumes the frozen G-0140 Stage-C rank-selection receipt.  It
appends only the selected rank-growing Pool128 rows to the inherited 412-row
G-0135 system, seeds the exact solve with the 204 independent G-0135 columns,
and reopens every one of the 163,740 canonical family columns.  The imported
G-0135 exact column-generation core makes only exact-Q terminal decisions.

Source-audit and preflight modes never run the scientific column scan or write
the scientific result.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import mmap
import resource
import sys
import time
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPT = Path(__file__).resolve()

SELECTOR_PATH = (
    ROOT
    / "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
G0135_MASTER_PATH = (
    ROOT / "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py"
)
G0135_RESULT_PATH = ROOT / "artifacts/math/G-0135/full_family_master_result_v3.json"
MANIFEST_PATH = ROOT / "artifacts/math/G-0140/pool128_manifest_v1.json"
STAGE_A_PATH = ROOT / "artifacts/math/G-0140/pool128_global_replay_v1.json"
STAGE_B_PATH = ROOT / "artifacts/math/G-0140/pool128_coordinate_prices_v1.json"
STAGE_C_PATH = ROOT / "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json"
OUTPUT_PATH = ROOT / "artifacts/math/G-0140/rank_aware_master_result_v1.json"
SOURCE_AUDIT_PATH = (
    ROOT
    / "artifacts/reviews/G-0160-g0140-stage-d-master-final3-source/SOURCE_AUDIT_RECEIPT.json"
)
AUDIT_PREREGISTRATION_PATH = (
    ROOT / "artifacts/reviews/G-0160-g0140-stage-d-master-final3-source/PREREGISTRATION.md"
)

N = 11
RECORDS = 163_740
BASE_ROWS = 412
POOL_ROWS = 128
ADMIT_LIMIT = 32
INITIAL_RANK = 204

SELECTOR_SHA256 = "f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3"
G0135_MASTER_SHA256 = (
    "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"
)
G0135_RESULT_SHA256 = (
    "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8"
)

MANIFEST_SCHEMA = "max11-g0140-rank-aware-manifest-v1"
STAGE_C_SCHEMA = "max11-g0140-pool128-exact-rank-selection-v1"
OUTPUT_SCHEMA = "max11-g0140-rank-aware-master-result-v1"
MEMBER_RESULT = "RANK_AWARE_SELECTED_ROWS_EXACT_Q_MEMBER"
NONMEMBER_RESULT = "FROZEN_163740_FAMILY_EXACT_Q_NONMEMBER"
SOURCE_AUDIT_SCHEMA = "max11-g0160-g0140-stage-d-master-final3-source-audit-v1"
SOURCE_AUDIT_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
SOURCE_AUDIT_EVIDENCE = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
SOURCE_AUDIT_CLAIM = "T1 source/custody clearance for the exact frozen G-0140 reopened-master producer bytes only; no scientific manifest, input, or output was observed, no scientific column-generation run was executed, and no mathematical claim is promoted."
SOURCE_AUDIT_NO_CLAIM = "This source audit does not adjudicate any future G-0140 scientific manifest or result and does not establish family membership, family nonmembership, a MAX11 identity, a lower bound, unrestricted nonrepresentability, minimality, an all-n theorem, refereed status, formalization, or a Lean theorem."
SOURCE_AUDIT_CHECKS = {
    "exact_named_binding_contract": True,
    "displaced_recursive_lookalikes_rejected": True,
    "correct_decoy_with_missing_named_binding_rejected": True,
    "unknown_envelope_fields_rejected": True,
    "audit_git_commit_rejected": True,
    "duplicate_json_keys_rejected": True,
    "trailing_json_data_rejected": True,
    "imported_exact_core_binding_verified": True,
    "future_input_gate_verified": True,
    "exact_column_generation_protocol_verified": True,
    "member_and_separator_fixtures_verified": True,
    "committed_blob_custody_verified": True,
    "producer_self_test_passed": True,
    "producer_static_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}

STAGE_C_KEYS = {
    "schema",
    "result",
    "claim_boundary",
    "manifest",
    "stage_a_receipt",
    "stage_b_receipt",
    "g0139_admission_receipt",
    "stage_c_source_audit",
    "solver",
    "launcher",
    "runtime",
    "native_proposer",
    "rows",
    "base_rows",
    "pool_rows",
    "records",
    "admit_limit",
    "target",
    "target_i128le_sha256",
    "target_construction",
    "row_order",
    "inherited_g0135_warm_start",
    "complete_column_basis",
    "rank_selection",
    "input_snapshot_sha256",
    "inputs_rehashed_at_end",
    "wall_seconds",
    "maximum_rss_kib",
}

STAGE_C_CLAIMS = {
    "EXACT_RANK32_SELECTED": (
        "Exact rank-aware selection of the first 32 growing Pool128 rows; "
        "this is not a membership, global identity, or MAX11 result."
    ),
    "FIXED_POOL128_EXACT_RANK_GAIN_LT32": (
        "Exact complete-matrix rank gain below 32 for the frozen Pool128; "
        "no reopened master or global identity was run."
    ),
}

COMPLETE_BASIS_KEYS = {
    "row_count",
    "record_count",
    "modular_role",
    "modular_primes",
    "modular_proposal_receipts",
    "proposed_union_sequences",
    "proposed_union_u64le_sha256",
    "initial_exact_basis_sequences",
    "initial_exact_rank",
    "completion_passes",
    "basis_sequences",
    "basis_sequences_u64le_sha256",
    "basis_rank",
    "basis_i128le_sha256",
    "nonzero_minor",
    "all_columns_exactly_spanned",
    "no_modular_terminal_decision",
}

COMPLETION_PASS_KEYS = {
    "pass",
    "rank",
    "annihilator_dimension",
    "columns_scanned",
    "prices_scanned",
    "nonzero_prices",
    "prices_decimal_lf_sha256",
    "first_violating_sequence",
    "first_violating_annihilator",
    "first_violating_price",
    "full_row_rank_shortcut",
    "complete",
}

NONZERO_MINOR_KEYS = {
    "rank",
    "coordinate_rows",
    "column_sequences",
    "determinant",
    "square_i128le_sha256",
}

NATIVE_PROPOSER_KEYS = {"source", "binary", "build_receipt", "role", "executions"}
NATIVE_EXECUTION_KEYS = {
    "schema",
    "role",
    "prime",
    "threads",
    "matrix_layout",
    "byte_order",
    "transpose_rows",
    "transpose_columns",
    "transpose_i32le_bytes",
    "transpose_i32le_sha256",
    "pivot_u32le_bytes",
    "pivot_u32le_sha256",
    "rank",
    "selected_sequences_u64le_sha256",
    "native_stdout",
}
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

RANK_SELECTION_KEYS = {
    "result",
    "base_rows",
    "pool_rows",
    "admit_limit",
    "prefix_rank_transcript",
    "full_pool_rank_transcript_precomputed_before_target_compatibility_checks",
    "selected_pool_indices",
    "selected_count",
    "rank_basis_pool_indices_before_terminal",
    "dependent_pool_indices_before_terminal",
    "post_cap_unadmitted_pool_indices",
    "post_terminal_unprocessed_pool_indices",
    "all_pool_rows_compatibility_checked",
    "compatibility_decision_complete",
    "dependency_certificates",
    "incompatible_dependency",
    "selected_system_rank",
    "selected_system_nonzero_minor",
    "no_modular_row_selection",
}

PREFIX_TRANSCRIPT_KEYS = {
    "base_rank",
    "full_pool_rank",
    "ordered_independent_logical_rows",
    "ordered_independent_logical_rows_u64le_sha256",
    "ranks",
    "increments",
    "rank_growing_indices",
    "dependent_indices",
    "ranks_decimal_lf_sha256",
    "increments_decimal_lf_sha256",
    "exact_q",
    "complete_basis_restriction",
    "method",
}


class RankAwareMasterError(RuntimeError):
    """Fail-closed G-0140 reopened-master error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RankAwareMasterError(message)


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    require(
        specification is not None and specification.loader is not None,
        f"cannot import module: {path}",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def relative(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT).as_posix()
    except ValueError as error:
        raise RankAwareMasterError(f"path escapes repository: {path}") from error


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        integer = int(value)
        require(-(1 << 127) <= integer < (1 << 127), "i128 digest overflow")
        digest.update(integer.to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_u64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        integer = int(value)
        require(0 <= integer < (1 << 64), "u64 digest overflow")
        digest.update(integer.to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def input_snapshot_digest(snapshot: dict[str, str]) -> str:
    digest = hashlib.sha256()
    for path, value in sorted(snapshot.items()):
        digest.update(path.encode("utf-8"))
        digest.update(b"\0")
        digest.update(value.encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def validate_source_audit(selector: Any, snapshot: dict[str, str]) -> None:
    script_name = relative(SCRIPT)
    audit_name = relative(SOURCE_AUDIT_PATH)
    require(
        snapshot.get(script_name) == sha256_path(SCRIPT)
        and snapshot.get(audit_name) == sha256_path(SOURCE_AUDIT_PATH),
        "manifest omits exact reopened-master source/audit bytes",
    )
    script_commit = selector.git_commit_for_path(SCRIPT)
    receipt = selector.load_json(SOURCE_AUDIT_PATH)
    expected_binding = (script_name, snapshot[script_name])
    observed_checks = receipt.get("required_checks")
    require(
        isinstance(observed_checks, dict)
        and set(observed_checks) == set(SOURCE_AUDIT_CHECKS)
        and all(type(value) is bool for value in observed_checks.values()),
        "G-0160 required checks must be exact JSON booleans",
    )
    selector.validate_source_audit_shape(
        receipt,
        schema=SOURCE_AUDIT_SCHEMA,
        claim_boundary=SOURCE_AUDIT_CLAIM,
        no_claim=SOURCE_AUDIT_NO_CLAIM,
        required_checks=SOURCE_AUDIT_CHECKS,
        preregistration_path=relative(AUDIT_PREREGISTRATION_PATH),
        named_bindings={"master_source": expected_binding},
        subject_commit=script_commit,
    )
    observed_binding = selector.validate_binding(
        receipt["subject"]["bindings"]["master_source"],
        "G-0160 reopened-master source",
    )
    require(observed_binding == expected_binding, "G-0160 live subject binding drift")
    preregistration = receipt.get("preregistration")
    preregistration_name = relative(AUDIT_PREREGISTRATION_PATH)
    require(
        isinstance(preregistration, dict)
        and preregistration.get("path") == preregistration_name
        and is_sha256(preregistration.get("sha256"))
        and preregistration.get("sha256")
        == sha256_path(AUDIT_PREREGISTRATION_PATH)
        and preregistration.get(
            "committed_and_pushed_before_subject_source_inspection"
        )
        is True
        and preregistration.get("committed_and_pushed_before_runtime_checks") is True,
        "G-0160 preregistration semantic/byte custody drift",
    )
    prereg_commit = selector.validate_commit(
        preregistration.get("git_commit"), "G-0160 preregistration"
    )
    require(
        prereg_commit == selector.git_commit_for_path(AUDIT_PREREGISTRATION_PATH),
        "G-0160 preregistration Git custody drift",
    )
    audit_commit = selector.git_commit_for_path(SOURCE_AUDIT_PATH)
    manifest_commit = selector.git_commit_for_path(MANIFEST_PATH)
    selector.git_is_ancestor(script_commit, prereg_commit, "master source -> G-0160 prereg")
    selector.git_is_ancestor(prereg_commit, audit_commit, "G-0160 prereg -> receipt")
    selector.git_is_ancestor(audit_commit, manifest_commit, "G-0160 receipt -> manifest")


def validate_stage_c_receipt(
    selector: Any,
    receipt: dict[str, Any],
    prepared: dict[str, Any],
) -> list[int]:
    require(set(receipt) == STAGE_C_KEYS, "Stage-C receipt top-level schema drift")
    manifest_sha256 = prepared["manifest_sha256"]
    stage_a_sha256 = prepared["stage_a_sha256"]
    stage_b_sha256 = prepared["stage_b_sha256"]
    snapshot = prepared["snapshot"]

    def bound(path: Path) -> dict[str, str]:
        name = relative(path)
        digest = snapshot.get(name)
        require(is_sha256(digest), f"Stage-C upstream binding missing: {name}")
        return {"path": name, "sha256": str(digest)}

    raw_target = receipt.get("target")
    require(
        isinstance(raw_target, list) and len(raw_target) == BASE_ROWS + POOL_ROWS,
        "Stage-C target shape drift",
    )
    target = [
        selector.canonical_integer(value, f"Stage-C target {index}")
        for index, value in enumerate(raw_target)
    ]
    result_name = receipt.get("result")
    require(
        receipt.get("schema") == STAGE_C_SCHEMA
        and result_name in STAGE_C_CLAIMS
        and receipt.get("claim_boundary") == STAGE_C_CLAIMS[result_name]
        and receipt.get("manifest")
        == {"path": relative(MANIFEST_PATH), "sha256": manifest_sha256}
        and receipt.get("stage_a_receipt")
        == {"path": relative(STAGE_A_PATH), "sha256": stage_a_sha256}
        and receipt.get("stage_b_receipt")
        == {"path": relative(STAGE_B_PATH), "sha256": stage_b_sha256}
        and receipt.get("g0139_admission_receipt")
        == bound(selector.G0139_RECEIPT_PATH)
        and receipt.get("stage_c_source_audit")
        == bound(selector.STAGE_C_SOURCE_AUDIT_PATH)
        and receipt.get("solver")
        == {"path": relative(SELECTOR_PATH), "sha256": SELECTOR_SHA256}
        and receipt.get("launcher") == bound(selector.LAUNCHER_PATH)
        and receipt.get("runtime") == prepared["runtime"]
        and receipt.get("rows") == BASE_ROWS + POOL_ROWS
        and receipt.get("base_rows") == BASE_ROWS
        and receipt.get("pool_rows") == POOL_ROWS
        and receipt.get("records") == RECORDS
        and receipt.get("admit_limit") == ADMIT_LIMIT
        and target == prepared["target"]
        and receipt.get("target_i128le_sha256") == digest_i128(target)
        and receipt.get("target_construction")
        == "immutable_G0135_412_entry_unscaled_target_followed_by_128_exact_zeros"
        and receipt.get("row_order")
        == [
            "immutable_prefix:G-0135:412",
            "pool:G-0140-stage-A-receipt-order:128",
        ]
        and receipt.get("inherited_g0135_warm_start") == prepared["warm_receipt"]
        and receipt.get("input_snapshot_sha256") == input_snapshot_digest(snapshot)
        and receipt.get("inputs_rehashed_at_end") is True
        and isinstance(receipt.get("wall_seconds"), (int, float))
        and not isinstance(receipt.get("wall_seconds"), bool)
        and math.isfinite(receipt["wall_seconds"])
        and receipt["wall_seconds"] > 0
        and isinstance(receipt.get("maximum_rss_kib"), int)
        and not isinstance(receipt.get("maximum_rss_kib"), bool)
        and receipt["maximum_rss_kib"] > 0,
        "Stage-C receipt identity/custody drift",
    )

    basis = receipt.get("complete_column_basis")
    native = receipt.get("native_proposer")
    require(
        isinstance(native, dict)
        and set(native) == NATIVE_PROPOSER_KEYS
        and native.get("source") == bound(selector.NATIVE_PROPOSER_SOURCE_PATH)
        and native.get("binary") == bound(selector.NATIVE_PROPOSER_PATH)
        and native.get("build_receipt")
        == bound(selector.NATIVE_BUILD_RECEIPT_PATH)
        and native.get("role") == selector.MODULAR_ROLE
        and isinstance(native.get("executions"), list),
        "Stage-C native proposer identity/schema drift",
    )
    require(
        isinstance(basis, dict) and set(basis) == COMPLETE_BASIS_KEYS,
        "Stage-C complete-basis schema drift",
    )
    proposals = basis.get("modular_proposal_receipts")
    fixed_primes = tuple(selector.FIXED_MODULAR_PRIMES)
    require(isinstance(proposals, list), "Stage-C modular proposals missing")
    selector.validate_modular_proposals(
        proposals, record_count=RECORDS, primes=fixed_primes
    )
    executions = native["executions"]
    require(
        len(executions) == len(proposals) == len(fixed_primes),
        "Stage-C native execution/proposal census drift",
    )
    expected_threads = selector.MANIFEST_PARAMETERS["threads"]
    expected_transpose_bytes = RECORDS * (BASE_ROWS + POOL_ROWS) * 4
    for index, (execution, proposal, prime) in enumerate(
        zip(executions, proposals, fixed_primes, strict=True)
    ):
        require(
            isinstance(execution, dict)
            and set(execution) == NATIVE_EXECUTION_KEYS,
            f"Stage-C native execution {index} schema drift",
        )
        stdout = execution.get("native_stdout")
        require(
            isinstance(stdout, dict) and set(stdout) == NATIVE_STDOUT_KEYS,
            f"Stage-C native stdout {index} schema drift",
        )
        seconds = stdout.get("factor_seconds")
        rank = proposal["rank"]
        require(
            execution.get("schema") == selector.NATIVE_EXECUTION_SCHEMA
            and execution.get("role") == selector.MODULAR_ROLE
            and execution.get("prime") == proposal.get("prime") == prime
            and execution.get("threads") == expected_threads
            and execution.get("matrix_layout")
            == "row_major_transpose_family_columns"
            and execution.get("byte_order") == "little_endian_runtime_asserted"
            and execution.get("transpose_rows") == RECORDS
            and execution.get("transpose_columns") == BASE_ROWS + POOL_ROWS
            and execution.get("transpose_i32le_bytes") == expected_transpose_bytes
            and is_sha256(execution.get("transpose_i32le_sha256"))
            and execution.get("pivot_u32le_bytes") == 4 * rank
            and is_sha256(execution.get("pivot_u32le_sha256"))
            and execution.get("rank") == rank
            and execution.get("selected_sequences_u64le_sha256")
            == proposal.get("selected_sequences_u64le_sha256")
            and stdout.get("schema") == selector.NATIVE_PROPOSER_SCHEMA
            and stdout.get("role") == selector.MODULAR_ROLE
            and stdout.get("matrix_layout")
            == "row_major_transpose_family_columns"
            and stdout.get("byte_order") == "little_endian_runtime_asserted"
            and stdout.get("transpose_rows") == RECORDS
            and stdout.get("transpose_columns") == BASE_ROWS + POOL_ROWS
            and stdout.get("prime") == prime
            and stdout.get("threads") == expected_threads
            and stdout.get("rank") == rank
            and isinstance(seconds, (int, float))
            and not isinstance(seconds, bool)
            and math.isfinite(float(seconds))
            and float(seconds) >= 0,
            f"Stage-C native execution {index} semantic drift",
        )

    proposed = basis.get("proposed_union_sequences")
    initial_basis = basis.get("initial_exact_basis_sequences")
    basis_sequences = basis.get("basis_sequences")
    require(
        basis.get("row_count") == BASE_ROWS + POOL_ROWS
        and basis.get("record_count") == RECORDS
        and basis.get("modular_role") == selector.MODULAR_ROLE
        and basis.get("modular_primes") == list(fixed_primes)
        and isinstance(proposed, list)
        and proposed
        == sorted(
            {
                int(sequence)
                for proposal in proposals
                for sequence in proposal["selected_sequences"]
            }
        )
        and proposed == sorted(set(proposed))
        and basis.get("proposed_union_u64le_sha256") == digest_u64(proposed)
        and isinstance(initial_basis, list)
        and initial_basis == sorted(set(initial_basis))
        and set(initial_basis).issubset(proposed)
        and basis.get("initial_exact_rank") == len(initial_basis)
        and isinstance(basis_sequences, list)
        and basis_sequences == sorted(set(basis_sequences))
        and set(initial_basis).issubset(basis_sequences)
        and all(
            isinstance(sequence, int)
            and not isinstance(sequence, bool)
            and 0 <= sequence < RECORDS
            for sequence in basis_sequences
        )
        and basis.get("basis_rank") == len(basis_sequences)
        and 0 < len(basis_sequences) <= BASE_ROWS + POOL_ROWS
        and basis.get("basis_sequences_u64le_sha256")
        == digest_u64(basis_sequences)
        and is_sha256(basis.get("basis_i128le_sha256"))
        and basis.get("all_columns_exactly_spanned") is True
        and basis.get("no_modular_terminal_decision") is True,
        "Stage-C complete-basis identity/order/digest drift",
    )
    selector.validate_completion_scan_census(basis, record_count=RECORDS)
    passes = basis.get("completion_passes")
    require(
        isinstance(passes, list)
        and all(isinstance(item, dict) and set(item) == COMPLETION_PASS_KEYS for item in passes)
        and [item["rank"] for item in passes]
        == list(range(len(initial_basis), len(basis_sequences) + 1)),
        "Stage-C completion rank/schema transcript drift",
    )
    terminal = passes[-1]
    require(
        terminal.get("rank") == len(basis_sequences)
        and terminal.get("complete") is True
        and terminal.get("first_violating_sequence") is None
        and terminal.get("first_violating_annihilator") is None
        and terminal.get("first_violating_price") is None
        and (
            (
                len(basis_sequences) == BASE_ROWS + POOL_ROWS
                and terminal.get("full_row_rank_shortcut") is True
            )
            or (
                len(basis_sequences) < BASE_ROWS + POOL_ROWS
                and terminal.get("full_row_rank_shortcut") is False
                and terminal.get("columns_scanned") == RECORDS
                and terminal.get("nonzero_prices") == 0
            )
        )
        and all(
            item.get("complete") is False
            and item.get("nonzero_prices", 0) > 0
            and isinstance(item.get("first_violating_sequence"), int)
            and 0 <= item["first_violating_sequence"] < RECORDS
            and isinstance(item.get("first_violating_annihilator"), int)
            and isinstance(item.get("first_violating_price"), str)
            for item in passes[:-1]
        ),
        "Stage-C completion terminal/nonterminal semantics drift",
    )
    minor = basis.get("nonzero_minor")
    require(
        isinstance(minor, dict)
        and set(minor) == NONZERO_MINOR_KEYS
        and minor.get("rank") == len(basis_sequences)
        and isinstance(minor.get("coordinate_rows"), list)
        and minor["coordinate_rows"] == sorted(set(minor["coordinate_rows"]))
        and len(minor["coordinate_rows"]) == len(basis_sequences)
        and all(
            isinstance(row, int)
            and not isinstance(row, bool)
            and 0 <= row < BASE_ROWS + POOL_ROWS
            for row in minor["coordinate_rows"]
        )
        and minor.get("column_sequences") == basis_sequences
        and selector.canonical_integer(
            minor.get("determinant"), "Stage-C exact nonzero minor", nonzero=True
        )
        and is_sha256(minor.get("square_i128le_sha256")),
        "Stage-C exact nonzero-minor receipt drift",
    )

    selection = receipt.get("rank_selection")
    require(
        isinstance(selection, dict)
        and set(selection) == RANK_SELECTION_KEYS
        and selection.get("result") == result_name
        and selection.get("base_rows") == BASE_ROWS
        and selection.get("pool_rows") == POOL_ROWS
        and selection.get("admit_limit") == ADMIT_LIMIT
        and selection.get(
            "full_pool_rank_transcript_precomputed_before_target_compatibility_checks"
        )
        is True
        and selection.get("incompatible_dependency") is None
        and selection.get("all_pool_rows_compatibility_checked") is True
        and selection.get("compatibility_decision_complete") is True
        and selection.get("post_terminal_unprocessed_pool_indices") == []
        and selection.get("no_modular_row_selection") is True
        and isinstance(selection.get("dependency_certificates"), list),
        "Stage-C complete-basis/compatibility terminal drift",
    )
    transcript = selection.get("prefix_rank_transcript")
    require(
        isinstance(transcript, dict)
        and set(transcript) == PREFIX_TRANSCRIPT_KEYS
        and transcript.get("exact_q") is True
        and transcript.get("complete_basis_restriction") is True
        and transcript.get("method")
        == "single_exact_Q_RREF_of_complete_basis_transpose_row_rank_profile"
        and isinstance(transcript.get("ranks"), list)
        and len(transcript["ranks"]) == POOL_ROWS + 1
        and all(
            isinstance(rank, int) and not isinstance(rank, bool)
            for rank in transcript["ranks"]
        )
        and isinstance(transcript.get("increments"), list)
        and transcript["increments"]
        == [
            transcript["ranks"][index + 1] - transcript["ranks"][index]
            for index in range(POOL_ROWS)
        ]
        and all(increment in {0, 1} for increment in transcript["increments"])
        and transcript.get("base_rank") == transcript["ranks"][0]
        and transcript.get("full_pool_rank") == transcript["ranks"][-1]
        and basis.get("basis_rank") == transcript["ranks"][-1]
        and transcript.get("ranks_decimal_lf_sha256")
        == selector.digest_decimal_lf(transcript["ranks"])
        and transcript.get("increments_decimal_lf_sha256")
        == selector.digest_decimal_lf(transcript["increments"]),
        "Stage-C prefix-rank/basis bridge drift",
    )
    growth = transcript.get("rank_growing_indices")
    dependent = transcript.get("dependent_indices")
    selected = selection.get("selected_pool_indices")
    ordered_rows = transcript.get("ordered_independent_logical_rows")
    require(
        isinstance(growth, list)
        and growth
        == [index for index, increment in enumerate(transcript["increments"]) if increment]
        and all(isinstance(index, int) and 0 <= index < POOL_ROWS for index in growth)
        and isinstance(dependent, list)
        and dependent
        == [
            index
            for index, increment in enumerate(transcript["increments"])
            if not increment
        ]
        and sorted(growth + dependent) == list(range(POOL_ROWS))
        and isinstance(ordered_rows, list)
        and ordered_rows == sorted(set(ordered_rows))
        and len(ordered_rows) == basis["basis_rank"]
        and all(
            isinstance(row, int)
            and not isinstance(row, bool)
            and 0 <= row < BASE_ROWS + POOL_ROWS
            for row in ordered_rows
        )
        and transcript.get("ordered_independent_logical_rows_u64le_sha256")
        == digest_u64(ordered_rows)
        and isinstance(selected, list)
        and selected == growth[:ADMIT_LIMIT]
        and selection.get("selected_count") == len(selected)
        and selection.get("rank_basis_pool_indices_before_terminal") == growth
        and selection.get("dependent_pool_indices_before_terminal") == dependent
        and selection.get("selected_system_rank")
        == transcript.get("base_rank") + len(selected)
        and (len(selected) == ADMIT_LIMIT)
        == (result_name == "EXACT_RANK32_SELECTED"),
        "Stage-C exact admission transcript drift",
    )
    return [int(index) for index in selected]


def validate_g0135_seed(selector: Any, result: dict[str, Any]) -> list[int]:
    selector.validate_g0135_member(result)
    selected = result.get("selected_sequences")
    require(
        result.get("rank") == result.get("augmented_rank") == INITIAL_RANK
        and isinstance(selected, list)
        and len(selected) == INITIAL_RANK
        and selected == sorted(set(selected))
        and all(isinstance(sequence, int) and 0 <= sequence < RECORDS for sequence in selected),
        "G-0135 204-column seed drift",
    )
    return [int(sequence) for sequence in selected]


def prepare(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
    stage_c_path: Path,
) -> dict[str, Any]:
    selector = load_module(SELECTOR_PATH, "g0140_rank_master_selector")
    require(
        sha256_path(SELECTOR_PATH) == SELECTOR_SHA256
        and sha256_path(G0135_MASTER_PATH) == G0135_MASTER_SHA256
        and sha256_path(G0135_RESULT_PATH) == G0135_RESULT_SHA256,
        "imported exact source/result byte drift",
    )
    require(
        stage_c_path.resolve() == STAGE_C_PATH.resolve() and STAGE_C_PATH.is_file(),
        "Stage-C receipt path/missing drift",
    )
    prepared = selector.load_validated_future_inputs(
        manifest_path, stage_a_path, stage_b_path
    )
    validate_source_audit(selector, prepared["snapshot"])
    stage_c_sha256 = sha256_path(STAGE_C_PATH)
    stage_c = selector.load_json(STAGE_C_PATH)
    selected = validate_stage_c_receipt(selector, stage_c, prepared)
    stage_c_commit = selector.git_commit_for_path(STAGE_C_PATH)
    manifest_commit = selector.git_commit_for_path(MANIFEST_PATH)
    selector.git_is_ancestor(
        manifest_commit, stage_c_commit, "G-0140 manifest -> Stage-C result"
    )
    seed = validate_g0135_seed(selector, selector.load_json(G0135_RESULT_PATH))
    snapshot = dict(prepared["snapshot"])
    snapshot[relative(STAGE_C_PATH)] = stage_c_sha256
    snapshot[relative(SCRIPT)] = sha256_path(SCRIPT)
    return {
        "selector": selector,
        "prepared": prepared,
        "stage_c": stage_c,
        "stage_c_sha256": stage_c_sha256,
        "stage_c_commit": stage_c_commit,
        "selected": selected,
        "seed": seed,
        "snapshot": snapshot,
    }


def with_column_loader(
    state: dict[str, Any],
    action: Callable[[Any, Callable[[int], list[int]], list[int]], Any],
) -> Any:
    prepared = state["prepared"]
    g0135_prepared = prepared["g0135_prepared"]
    g0135_producer = prepared["g0135_producer"]
    ancestor = g0135_prepared["ancestor"]
    selector = state["selector"]
    all_pool_rows = prepared["stage_b_rows"]
    selected_rows = [prepared["stage_b_rows"][index] for index in state["selected"]]
    target = prepared["target"][:BASE_ROWS] + [0] * len(selected_rows)
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        inherited_warm, inherited_loader = g0135_producer.validate_warm_start(
            g0135_prepared, cache
        )
        require(
            inherited_warm == prepared["warm_receipt"],
            "inherited G-0135 loader changed",
        )

        def full_loader(sequence: int) -> list[int]:
            require(0 <= sequence < RECORDS, "full column sequence outside family")
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(int(row[sequence]) for row in all_pool_rows)
            require(
                len(column) == BASE_ROWS + POOL_ROWS,
                "full Stage-C column width drift",
            )
            return column

        basis = state["stage_c"]["complete_column_basis"]
        basis_sequences = [int(value) for value in basis["basis_sequences"]]
        basis_columns = [full_loader(sequence) for sequence in basis_sequences]
        basis_rows = selector.matrix_rows(basis_columns, BASE_ROWS + POOL_ROWS)
        require(
            int(selector.qmatrix(basis_rows).rank()) == basis["basis_rank"]
            and digest_i128(value for row in basis_rows for value in row)
            == basis["basis_i128le_sha256"]
            and selector.exact_nonzero_minor(basis_rows, basis_sequences)
            == basis["nonzero_minor"],
            "Stage-C live complete-basis replay drift",
        )
        replayed_selection = selector.exact_rank_selection(
            column_loader=full_loader,
            complete_basis=basis,
            target=prepared["target"],
            base_rows=BASE_ROWS,
            pool_rows=POOL_ROWS,
            admit_rows=ADMIT_LIMIT,
            record_count=RECORDS,
        )
        require(
            replayed_selection == state["stage_c"]["rank_selection"],
            "Stage-C exact row-selection replay drift",
        )

        def loader(sequence: int) -> list[int]:
            require(0 <= sequence < RECORDS, "column sequence outside family")
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(int(row[sequence]) for row in selected_rows)
            require(len(column) == len(target), "rank-aware column width drift")
            return column

        return action(g0135_producer, loader, target)


def preflight(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
    stage_c_path: Path,
) -> dict[str, Any]:
    require(not OUTPUT_PATH.exists(), "scientific master output already exists")
    state = prepare(manifest_path, stage_a_path, stage_b_path, stage_c_path)

    def check_seed(core: Any, loader: Callable[[int], list[int]], target: list[int]) -> dict[str, int]:
        columns = [loader(sequence) for sequence in state["seed"]]
        rows = core.matrix_rows(columns, len(target))
        matrix = state["prepared"]["g0135_prepared"]["helper"].qmatrix(rows)
        augmented = state["prepared"]["g0135_prepared"]["helper"].qmatrix(
            [row + [target[index]] for index, row in enumerate(rows)]
        )
        rank = int(matrix.rank())
        augmented_rank = int(augmented.rank())
        require(
            rank == INITIAL_RANK and augmented_rank in {rank, rank + 1},
            "rank-aware warm seed exact-rank drift",
        )
        return {"rank": rank, "augmented_rank": augmented_rank}

    seed = with_column_loader(state, check_seed)
    rehash_snapshot(state["snapshot"])
    return {
        "result": "G0140_RANK_AWARE_MASTER_PREFLIGHT_PASS",
        "records": RECORDS,
        "base_rows": BASE_ROWS,
        "selected_rows": len(state["selected"]),
        "rows": BASE_ROWS + len(state["selected"]),
        "initial_rank": seed["rank"],
        "initial_augmented_rank": seed["augmented_rank"],
        "target_i128le_sha256": digest_i128(
            state["prepared"]["target"][:BASE_ROWS] + [0] * len(state["selected"])
        ),
        "scientific_column_generation_run": False,
        "scientific_result_written": False,
    }


def rehash_snapshot(snapshot: dict[str, str]) -> None:
    for path, digest in sorted(snapshot.items()):
        resolved = (ROOT / path).resolve()
        require(resolved.is_file(), f"bound input vanished: {path}")
        require(sha256_path(resolved) == digest, f"bound input drift: {path}")


def run(
    manifest_path: Path,
    stage_a_path: Path,
    stage_b_path: Path,
    stage_c_path: Path,
    output_path: Path,
) -> dict[str, Any]:
    begun = time.perf_counter()
    require(output_path.resolve() == OUTPUT_PATH.resolve(), "master output path drift")
    require(not OUTPUT_PATH.exists(), "refusing to overwrite master output")
    state = prepare(manifest_path, stage_a_path, stage_b_path, stage_c_path)

    def solve(core: Any, loader: Callable[[int], list[int]], target: list[int]) -> dict[str, Any]:
        return core.exact_column_generation(
            helper=state["prepared"]["g0135_prepared"]["helper"],
            target=target,
            seed_sequences=state["seed"],
            column_loader=loader,
            record_count=RECORDS,
            expected_initial_rank=INITIAL_RANK,
            prior_target_scale=int(
                selector_result(state["selector"])["target_scale"]
            ),
        )

    decision = with_column_loader(state, solve)
    branch = decision.pop("branch")
    selected = state["selected"]
    prepared = state["prepared"]
    target = prepared["target"][:BASE_ROWS] + [0] * len(selected)
    directions = [prepared["directions"][index] for index in selected]
    if branch == "MEMBER":
        result_name = MEMBER_RESULT
        claim = "Exact-Q member only for the frozen G-0135 412 rows plus the selected G-0140 rank-growing rows; complete global replay has not yet been run, so this is not a MAX11 identity or lower bound."
    else:
        require(branch == "NONMEMBER", "unknown exact master branch")
        result_name = NONMEMBER_RESULT
        claim = "Exact nonmembership only for the frozen selected-row target against the frozen 163,740-column family; not unrestricted nonrepresentability, minimality, or an all-n theorem."
    result = {
        "schema": OUTPUT_SCHEMA,
        "result": result_name,
        "claim_boundary": claim,
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
        "stage_c_receipt": {
            "path": relative(STAGE_C_PATH),
            "sha256": state["stage_c_sha256"],
        },
        "source_audit": {
            "path": relative(SOURCE_AUDIT_PATH),
            "sha256": prepared["snapshot"][relative(SOURCE_AUDIT_PATH)],
        },
        "solver": {"path": relative(SCRIPT), "sha256": sha256_path(SCRIPT)},
        "records": RECORDS,
        "base_rows": BASE_ROWS,
        "selected_pool_indices": selected,
        "selected_pool_indices_u64le_sha256": digest_u64(selected),
        "selected_directions": directions,
        "selected_directions_i8_sha256": state["selector"].digest_directions(
            directions
        ),
        "appended_rows": len(selected),
        "rows": len(target),
        "target": [str(value) for value in target],
        "target_i128le_sha256": digest_i128(target),
        "target_construction": "immutable_G0135_412_entry_unscaled_target_followed_by_selected_exact_zeros",
        "initial_selected_sequences": state["seed"],
        "initial_selected_sequences_u64le_sha256": digest_u64(state["seed"]),
        "initial_rank": INITIAL_RANK,
        "all_columns_reopened": True,
        "canonical_column_order": True,
        "no_modular_terminal_decision": True,
        "no_support_freeze": True,
        "no_zero_price_column_deletion": True,
        "no_row_dependency_deletion": True,
        "no_preferred_sparsity_search": True,
        **decision,
        "input_snapshot_sha256": input_snapshot_digest(state["snapshot"]),
        "inputs_rehashed_at_end": False,
        "wall_seconds": 0.0,
        "maximum_rss_kib": 0,
    }
    rehash_snapshot(state["snapshot"])
    require(sha256_path(SCRIPT) == state["snapshot"][relative(SCRIPT)], "solver drift")
    result["inputs_rehashed_at_end"] = True
    result["wall_seconds"] = time.perf_counter() - begun
    result["maximum_rss_kib"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    state["selector"].write_exclusive(OUTPUT_PATH, result)
    return result


def selector_result(selector: Any) -> dict[str, Any]:
    result = selector.load_json(G0135_RESULT_PATH)
    require(
        result.get("target_scale") is not None,
        "G-0135 target scale missing",
    )
    return result


def self_test() -> None:
    require(
        sha256_path(SELECTOR_PATH) == SELECTOR_SHA256
        and sha256_path(G0135_MASTER_PATH) == G0135_MASTER_SHA256
        and sha256_path(G0135_RESULT_PATH) == G0135_RESULT_SHA256,
        "self-test imported byte drift",
    )
    core = load_module(G0135_MASTER_PATH, "g0140_rank_master_fixture_core")
    selector = load_module(SELECTOR_PATH, "g0140_rank_master_fixture_selector")
    helper = load_module(
        ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py",
        "g0140_rank_master_fixture_helper",
    )

    audit_binding = (relative(SCRIPT), "0" * 64)
    audit_fixture = {
        "schema": SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": SOURCE_AUDIT_RESULT,
        "evidence_class": SOURCE_AUDIT_EVIDENCE,
        "claim_boundary": SOURCE_AUDIT_CLAIM,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": True,
            "fresh_context": True,
        },
        "preregistration": {
            "path": relative(AUDIT_PREREGISTRATION_PATH),
            "sha256": "1" * 64,
            "git_commit": "0" * 40,
            "committed_and_pushed_before_subject_source_inspection": True,
            "committed_and_pushed_before_runtime_checks": True,
        },
        "subject": {
            "git_commit": "0" * 40,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
            "bindings": {
                "master_source": {
                    "path": audit_binding[0],
                    "sha256": audit_binding[1],
                }
            },
        },
        "required_checks": SOURCE_AUDIT_CHECKS,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "no_claim": SOURCE_AUDIT_NO_CLAIM,
    }
    selector.validate_source_audit_shape(
        audit_fixture,
        schema=SOURCE_AUDIT_SCHEMA,
        claim_boundary=SOURCE_AUDIT_CLAIM,
        no_claim=SOURCE_AUDIT_NO_CLAIM,
        required_checks=SOURCE_AUDIT_CHECKS,
        preregistration_path=relative(AUDIT_PREREGISTRATION_PATH),
        named_bindings={"master_source": audit_binding},
        subject_commit="0" * 40,
    )
    displaced = json.loads(json.dumps(audit_fixture))
    displaced["unrelated_receipt_lookalikes"] = displaced["subject"].pop("bindings")
    displaced_rejected = False
    try:
        selector.validate_source_audit_shape(
            displaced,
            schema=SOURCE_AUDIT_SCHEMA,
            claim_boundary=SOURCE_AUDIT_CLAIM,
            no_claim=SOURCE_AUDIT_NO_CLAIM,
            required_checks=SOURCE_AUDIT_CHECKS,
            preregistration_path=relative(AUDIT_PREREGISTRATION_PATH),
            named_bindings={"master_source": audit_binding},
            subject_commit="0" * 40,
        )
    except selector.SelectorError:
        displaced_rejected = True
    require(displaced_rejected, "source-audit displaced-binding fixture escaped")

    integer_check = json.loads(json.dumps(audit_fixture))
    integer_check["required_checks"]["producer_self_test_passed"] = 1
    integer_check_rejected = False
    try:
        selector.validate_source_audit_shape(
            integer_check,
            schema=SOURCE_AUDIT_SCHEMA,
            claim_boundary=SOURCE_AUDIT_CLAIM,
            no_claim=SOURCE_AUDIT_NO_CLAIM,
            required_checks=SOURCE_AUDIT_CHECKS,
            preregistration_path=relative(AUDIT_PREREGISTRATION_PATH),
            named_bindings={"master_source": audit_binding},
            subject_commit="0" * 40,
        )
    except selector.SelectorError:
        integer_check_rejected = True
    require(integer_check_rejected, "source-audit integer boolean fixture escaped")

    member_columns = [[1, 0], [0, 1]]
    member = core.exact_column_generation(
        helper=helper,
        target=[1, 1],
        seed_sequences=[0],
        column_loader=member_columns.__getitem__,
        record_count=2,
        expected_initial_rank=1,
        prior_target_scale=7,
    )
    require(
        member.get("branch") == "MEMBER"
        and member.get("rank") == member.get("augmented_rank") == 2
        and member.get("selected_sequences") == [0, 1],
        "synthetic reopened member route drift",
    )

    nonmember_columns = [[1, 0]]
    nonmember = core.exact_column_generation(
        helper=helper,
        target=[0, 1],
        seed_sequences=[0],
        column_loader=nonmember_columns.__getitem__,
        record_count=1,
        expected_initial_rank=1,
        prior_target_scale=7,
    )
    require(
        nonmember.get("branch") == "NONMEMBER"
        and nonmember.get("complete_separator_replay", {}).get(
            "all_family_columns_exactly_annihilated"
        )
        is True
        and nonmember.get("separator_target_pairing") != "0",
        "synthetic terminal separator route drift",
    )

    with Path(__file__).open("rb") as source:
        require(bool(source.read(1)), "empty solver source")
    print("g0140-rank-aware-master-self-test: PASS (member and separator routes)")


def static_preflight() -> dict[str, Any]:
    self_test()
    selector = load_module(SELECTOR_PATH, "g0140_rank_master_static_selector")
    selector.git_commit_for_path(SCRIPT)
    selector.git_commit_for_path(SELECTOR_PATH)
    selector.git_commit_for_path(G0135_MASTER_PATH)
    future = {
        "manifest": MANIFEST_PATH.is_file(),
        "stage_a": STAGE_A_PATH.is_file(),
        "stage_b": STAGE_B_PATH.is_file(),
        "stage_c": STAGE_C_PATH.is_file(),
        "source_audit": SOURCE_AUDIT_PATH.is_file(),
    }
    return {
        "result": "G0140_RANK_AWARE_MASTER_STATIC_PREFLIGHT_PASS",
        "solver_sha256": sha256_path(SCRIPT),
        "selector_sha256": SELECTOR_SHA256,
        "g0135_master_sha256": G0135_MASTER_SHA256,
        "g0135_result_sha256": G0135_RESULT_SHA256,
        "future_inputs_present": future,
        "all_future_inputs_present": all(future.values()),
        "scientific_column_generation_run": False,
        "scientific_result_written": False,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--static-preflight", action="store_true")
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
    if args.preflight:
        require(len(args.paths) == 4, "preflight requires MANIFEST A B C")
        print(
            json.dumps(
                preflight(*(Path(path) for path in args.paths)), sort_keys=True
            )
        )
        return 0
    require(len(args.paths) == 5, "run requires MANIFEST A B C OUTPUT")
    result = run(*(Path(path) for path in args.paths))
    print(
        json.dumps(
            {
                "result": result["result"],
                "rank": result["rank"],
                "augmented_rank": result["augmented_rank"],
                "terms": len(result.get("terms", [])),
                "wall_seconds": result["wall_seconds"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
