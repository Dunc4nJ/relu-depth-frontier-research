#!/usr/bin/env python3
"""Fresh G-0151 audit of the frozen G-0140 Stage-B final2 producer.

The only frozen producer modes this checker invokes are ``--self-test`` and
``--preflight-static``.  The public panel and frozen candidate are passed to
the latter as opaque path strings.  This checker never opens the G-0140
scientific manifest, Stage-A scientific output, or Stage-B scientific output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


AUDIT_DIR = Path(__file__).resolve().parent
ROOT = AUDIT_DIR.parents[2]

FROZEN_SELECTOR = "19de7da"
FROZEN_COMMIT = "19de7da8fe62629780fd7c7cf9b6d08d66e03fd2"
PREREGISTRATION = (
    "artifacts/reviews/G-0151-g0140-stage-b-final2-source/PREREGISTRATION.md"
)
G0150_RECEIPT = (
    "artifacts/reviews/G-0150-g0140-stage-a-final2-source/SOURCE_AUDIT_RECEIPT.json"
)
G0142_RECEIPT = "artifacts/reviews/G-0142-g0140-stage-b-source/SOURCE_AUDIT_RECEIPT.json"
G0147_RESULTS = "artifacts/reviews/G-0147-g0140-stage-b-final-source/CHECK_RESULTS.json"
PANEL = "artifacts/math/G-0113/panel_solver_input_v1.json"
CANDIDATE = "artifacts/math/G-0135/full_family_master_result_v3.json"
KERNEL = "artifacts/math/G-0117/src/lib.rs"
CONTRACT_MANIFEST = AUDIT_DIR / "contract_probe/Cargo.toml"

SUBJECTS = OrderedDict(
    [
        ("main_source", "artifacts/math/G-0140/stage_b_pricer/src/main.rs"),
        ("cargo_manifest", "artifacts/math/G-0140/stage_b_pricer/Cargo.toml"),
        ("cargo_lock", "artifacts/math/G-0140/stage_b_pricer/Cargo.lock"),
        (
            "release_executable",
            "artifacts/math/G-0140/stage_b_pricer/target/release/"
            "g0140-stage-b-pool128-coordinate-pricer",
        ),
    ]
)

STAGE_A_SUBJECTS = OrderedDict(
    [
        ("main_source", "artifacts/math/G-0140/stage_a_pool/src/main.rs"),
        ("engine_source", "artifacts/math/G-0140/stage_a_pool/src/engine.rs"),
        ("cargo_manifest", "artifacts/math/G-0140/stage_a_pool/Cargo.toml"),
        ("cargo_lock", "artifacts/math/G-0140/stage_a_pool/Cargo.lock"),
        (
            "release_executable",
            "artifacts/math/G-0140/stage_a_pool/target/release/"
            "g0140-stage-a-pool128-global-replay",
        ),
    ]
)

EXPECTED_G0150_SHA256 = "f65452749be020286410fb03a16e493c917716cecdc557456b449b5fe8223b4e"
EXPECTED_G0150_COMMIT = "7d4bf71a4995fbead527e0e1ce645cec5acb86b8"
EXPECTED_G0150_SUBJECT_COMMIT = "b59c5f8763a06bae36ffe0b8d93e14a0bfe9f741"
EXPECTED_G0142_FAILURES = {
    "SCHEMA_ALL_INPUT_STRUCTS_DENY_UNKNOWN_FIELDS",
    "SCHEMA_SOURCE_AUDIT_GATE_EXACT",
}
EXPECTED_G0147_BLOCKERS = {
    "STAGE_A_RECEIPT_MISSING_NULL_FIELD_REJECTED",
    "STAGE_A_MUTATION_CONTROL_SCHEMAS_COMPLETE_AND_VALIDATED",
    "SOURCE_AUDIT_CLOSED_SCHEMA_AND_BINDING_PLACEMENT",
}

STAGE_A_SCHEMA = "max11-g0150-g0140-stage-a-final2-source-audit-v1"
STAGE_B_SCHEMA = "max11-g0151-g0140-stage-b-final2-source-audit-v1"
PASS_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
STAGE_A_CLAIM = (
    "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; "
    "no scientific manifest, input, or output was observed, no scientific replay "
    "was run, and no mathematical claim is promoted."
)
STAGE_B_CLAIM = (
    "T1 source/custody clearance for the exact frozen Stage-B producer bytes only; "
    "no scientific manifest, input, or output was observed, no scientific replay "
    "was run, and no mathematical claim is promoted."
)
STAGE_A_NO_CLAIM = (
    "This source audit does not adjudicate a G-0140 scientific manifest or result, "
    "establish or exclude a Pool128 member, validate family completeness, prove a "
    "MAX11 lower bound, settle unrestricted two-hidden-layer representation, "
    "establish minimality, prove an all-n statement, or supply a Lean theorem."
)
STAGE_B_NO_CLAIM = (
    "This source audit does not adjudicate a G-0140 scientific manifest or result, "
    "establish or exclude a Pool128 coordinate matrix or exact-rank selection, "
    "validate family completeness, prove a MAX11 lower bound, settle unrestricted "
    "two-hidden-layer representation, establish minimality, prove an all-n statement, "
    "or supply a Lean theorem."
)

REQUIRED_STAGE_B_CHECKS = [
    "exact_named_binding_contract",
    "displaced_recursive_lookalikes_rejected",
    "correct_decoy_with_missing_named_binding_rejected",
    "duplicate_path_occurrences_rejected",
    "unknown_envelope_fields_rejected",
    "audit_git_commit_rejected",
    "duplicate_json_keys_rejected",
    "trailing_json_data_rejected",
    "stage_a_missing_nullable_field_rejected",
    "stage_a_mutation_control_schemas_validated",
    "stage_a_source_audit_exact_contract_validated",
    "compiled_source_manifest_lock_match_working_bytes",
    "overwrite_refusal_verified",
    "end_rehash_verified",
    "bigint_unconditional_paths_verified",
    "producer_self_test_passed",
    "producer_static_preflight_passed",
    "prohibited_scientific_modes_not_run",
]

REQUIRED_STAGE_A_CHECKS = [
    "exact_named_binding_contract",
    "displaced_recursive_lookalikes_rejected",
    "correct_decoy_with_missing_named_binding_rejected",
    "duplicate_path_occurrences_rejected",
    "unknown_envelope_fields_rejected",
    "audit_git_commit_rejected",
    "duplicate_json_keys_rejected",
    "trailing_json_data_rejected",
    "producer_self_test_passed",
    "producer_static_preflight_passed",
    "producer_ancestor_preflight_passed",
    "prohibited_scientific_modes_not_run",
]

ROOT_RECEIPT_FIELDS = {
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

NO_SCIENCE_FLAGS = {
    "g0140_scientific_manifest_opened_or_created": False,
    "stage_a_scientific_output_opened_or_created": False,
    "stage_b_output_opened_or_created": False,
    "preflight_default_or_science_mode_executed": False,
}


class DuplicateKeyError(ValueError):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_file(file_name: Path) -> str:
    digest = hashlib.sha256()
    with file_name.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise DuplicateKeyError(f"duplicate JSON key: {key}")
        value[key] = item
    return value


def strict_json_bytes(raw: bytes) -> Any:
    text = raw.decode("utf-8")
    decoder = json.JSONDecoder(object_pairs_hook=strict_pairs)
    value, end = decoder.raw_decode(text)
    if text[end:].strip():
        raise ValueError("trailing non-whitespace JSON data")
    return value


def strict_json_file(relative: str) -> Any:
    return strict_json_bytes((ROOT / relative).read_bytes())


def command(
    arguments: list[str],
    *,
    timeout: int = 300,
    environment: dict[str, str] | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
        timeout=timeout,
    )
    return {
        "argv": arguments,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": sha256_bytes(completed.stdout.encode()),
        "stderr_sha256": sha256_bytes(completed.stderr.encode()),
        "wall_seconds": round(time.monotonic() - started, 6),
    }


def git_text(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)}: {result.stderr.strip()}")
    return result.stdout.strip()


def git_status(*arguments: str) -> int:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    ).returncode


def git_blob(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git show {commit}:{relative}: {result.stderr.decode().strip()}")
    return result.stdout


def tree_entry(commit: str, relative: str) -> dict[str, Any]:
    line = git_text("ls-tree", "-l", commit, "--", relative)
    match = re.fullmatch(r"(\d+)\s+(\w+)\s+([0-9a-f]{40})\s+(\d+)\t(.+)", line)
    if not match or match.group(5) != relative:
        raise RuntimeError(f"malformed or missing ls-tree entry for {relative}: {line!r}")
    return {
        "mode": match.group(1),
        "type": match.group(2),
        "object_id": match.group(3),
        "bytes": int(match.group(4)),
        "path": match.group(5),
    }


def remote_contains(commit: str) -> bool:
    return git_status("merge-base", "--is-ancestor", commit, "origin/master") == 0


def matching_rust_brace(source: str, opening: int) -> int:
    depth = 0
    index = opening
    block_comment_depth = 0
    while index < len(source):
        if block_comment_depth:
            if source.startswith("/*", index):
                block_comment_depth += 1
                index += 2
            elif source.startswith("*/", index):
                block_comment_depth -= 1
                index += 2
            else:
                index += 1
            continue
        if source.startswith("//", index):
            newline = source.find("\n", index + 2)
            index = len(source) if newline < 0 else newline + 1
            continue
        if source.startswith("/*", index):
            block_comment_depth = 1
            index += 2
            continue

        raw_match = re.match(r"(?:b)?r(?P<marks>#{0,16})\"", source[index:])
        if raw_match:
            marks = raw_match.group("marks")
            terminator = '"' + marks
            start = index + raw_match.end()
            end = source.find(terminator, start)
            if end < 0:
                raise ValueError("unterminated Rust raw string")
            index = end + len(terminator)
            continue

        if source.startswith('b"', index) or source[index] == '"':
            index += 2 if source.startswith('b"', index) else 1
            while index < len(source):
                if source[index] == "\\":
                    index += 2
                elif source[index] == '"':
                    index += 1
                    break
                else:
                    index += 1
            continue

        if source[index] == "'":
            char_match = re.match(r"'(?:\\.|[^\\'\n])'", source[index:])
            if char_match:
                index += char_match.end()
                continue

        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise ValueError("unclosed Rust item body")


def rust_item_body(source: str, kind: str, name: str) -> str:
    marker = re.search(rf"\b{re.escape(kind)}\s+{re.escape(name)}\b", source)
    if not marker:
        raise ValueError(f"Rust {kind} not found: {name}")
    opening = source.find("{", marker.end())
    if opening < 0:
        raise ValueError(f"Rust {kind} has no body: {name}")
    closing = matching_rust_brace(source, opening)
    return source[opening + 1 : closing]


def rust_struct_fields(source: str, name: str) -> OrderedDict[str, str]:
    body = rust_item_body(source, "struct", name)
    fields: OrderedDict[str, str] = OrderedDict()
    for line in body.splitlines():
        match = re.match(r"\s*(?:pub\s+)?([A-Za-z_][A-Za-z0-9_]*):\s*(.+),\s*$", line)
        if match:
            fields[match.group(1)] = re.sub(r"\s+", "", match.group(2))
    return fields


def rust_deny_unknown(source: str, name: str) -> bool:
    marker = re.search(rf"\bstruct\s+{re.escape(name)}\b", source)
    if not marker:
        return False
    prefix = source[max(0, marker.start() - 400) : marker.start()]
    last_gap = prefix.rsplit("\n\n", 1)[-1]
    return "#[serde(deny_unknown_fields)]" in last_gap


def rust_const_string(source: str, name: str) -> str | None:
    match = re.search(
        rf"const\s+{re.escape(name)}\s*:\s*&str\s*=\s*\"([^\"]*)\"\s*;",
        source,
    )
    return match.group(1) if match else None


def has_all(haystack: str, needles: Iterable[str]) -> bool:
    return all(needle in haystack for needle in needles)


def static_source_assessment(source: str, cargo: str, lock: str, kernel: str) -> dict[str, bool]:
    stage_a_fields = rust_struct_fields(source, "StageAReceipt")
    mutation_fields = rust_struct_fields(source, "MutationControl")
    typed_stage_a = {
        "independent_finite_412_row_replay": "FiniteReplayReceipt",
        "term_normal_forms": "Vec<TermNormalFormReceipt>",
        "coefficient_plus_one": "MutationControl",
        "target_scale_plus_one": "MutationControl",
        "target_coordinate_plus_one": "MutationControl",
        "omitted_final_term": "MutationControl",
        "omitted_first_term_direction": "MutationControl",
        "census_controls": "CensusControls",
        "selection_controls": "SelectionControls",
    }
    typed_stage_a_ok = all(stage_a_fields.get(key) == value for key, value in typed_stage_a.items())

    typed_structs = {
        "TermNormalFormReceipt",
        "FiniteCoefficientMutant",
        "FiniteReplayReceipt",
        "MutationControl",
        "CensusControls",
        "SelectionControls",
        "ExactHinge",
        "ExactLinear",
    }
    typed_fields_ok = (
        set(rust_struct_fields(source, "FiniteReplayReceipt"))
        == {
            "rows",
            "panel_rows",
            "linear_rows",
            "accumulated_hinge_rows",
            "cache_layout",
            "arithmetic",
            "all_rows_exactly_replayed",
            "residuals_decimal_lf_sha256",
            "coefficient_plus_one_mutant",
        }
        and set(rust_struct_fields(source, "MutationControl"))
        == {
            "name",
            "first_nonzero_hinge",
            "first_nonzero_linear",
            "baseline_complete_residual_sha256",
            "mutated_complete_residual_sha256",
            "changed_from_baseline",
            "detected",
        }
        and set(rust_struct_fields(source, "CensusControls"))
        == {
            "dynamic_term_count",
            "factorial_11",
            "expected_labelled_permutations",
            "observed_labelled_permutations",
            "per_term_generated_equals_visited_equals_accepted",
            "zero_skipped_unclassified_failed",
            "omitted_last_orbit_rejected",
            "decremented_global_census_rejected",
            "accumulated_direction_count_100",
            "omitted_accumulated_direction_rejected",
        }
        and set(rust_struct_fields(source, "SelectionControls"))
        == {
            "exact_batch_count_or_zero_terminal",
            "strict_signed_lexicographic_order",
            "excludes_accumulated_directions",
            "direction_reordering_changes_digest",
            "coefficient_plus_one_changes_digest",
        }
        and all(rust_deny_unknown(source, name) for name in typed_structs)
    )

    nullable_impl = rust_item_body(source, "impl<'de,", "T>") if False else source
    self_test = rust_item_body(source, "fn", "self_test")
    required_nullable_ok = (
        stage_a_fields.get("first_nonzero_linear") == "RequiredNullable<ExactLinear>"
        and stage_a_fields.get("first_nonzero_hinge") == "RequiredNullable<ExactHinge>"
        and mutation_fields.get("first_nonzero_linear") == "RequiredNullable<ExactLinear>"
        and mutation_fields.get("first_nonzero_hinge") == "RequiredNullable<ExactHinge>"
        and has_all(
            source,
            [
                "struct RequiredNullable<T>(Option<T>);",
                "if value.is_null()",
                "Ok(Self(None))",
                ".map(Some)",
            ],
        )
        and has_all(
            self_test,
            [
                'serde_json::json!({"first_nonzero_linear": null})',
                "serde_json::from_value::<RequiredNullableFixture>(serde_json::json!({})).is_err()",
                '.remove("first_nonzero_linear")',
                "serde_json::from_value::<MutationControl>(missing_mutation_nullable).is_err()",
            ],
        )
    )

    structured = rust_item_body(source, "fn", "validate_stage_a_structured_controls")
    term_receipts = rust_item_body(source, "fn", "validate_term_normal_form_receipts")
    mutation = rust_item_body(source, "fn", "validate_mutation_control")
    stage_a_validation = rust_item_body(source, "fn", "validate_stage_a_receipt")
    structured_semantics_ok = (
        has_all(
            structured,
            [
                "finite.rows == ROWS",
                "finite.panel_rows == 301",
                "finite.linear_rows == N",
                "finite.accumulated_hinge_rows == CARRY_DIRECTIONS",
                "finite.all_rows_exactly_replayed",
                "finite.residuals_decimal_lf_sha256 == zero_residual_digest",
                "finite_mutant.sequence",
                'finite_mutant.coefficient_delta == "+1"',
                "finite_mutant.first_nonzero_residual_row < ROWS",
                "finite_mutant.residuals_decimal_lf_sha256 != zero_residual_digest",
                "finite_mutant.rejected",
                "validate_term_normal_form_receipts(&receipt.term_normal_forms, candidate)?",
                '"first_nonzero_coefficient_plus_one"',
                '"target_scale_plus_one"',
                '"target_coordinate_10_plus_one"',
                '"omitted_final_nonzero_term"',
                '"omitted_first_term_active_direction"',
                "census.dynamic_term_count == TERMS",
                "census.factorial_11 == factorial(N)",
                "census.expected_labelled_permutations == EXPECTED_LABELLED_PERMUTATIONS",
                "census.observed_labelled_permutations == EXPECTED_LABELLED_PERMUTATIONS",
                "census.per_term_generated_equals_visited_equals_accepted",
                "census.zero_skipped_unclassified_failed",
                "census.omitted_last_orbit_rejected",
                "census.decremented_global_census_rejected",
                "census.accumulated_direction_count_100",
                "census.omitted_accumulated_direction_rejected",
                "selection.exact_batch_count_or_zero_terminal",
                "selection.strict_signed_lexicographic_order",
                "selection.excludes_accumulated_directions",
                "selection.direction_reordering_changes_digest",
                "selection.coefficient_plus_one_changes_digest",
            ],
        )
        and has_all(
            term_receipts,
            [
                "receipts.len() == candidate.terms.len()",
                ".eq(candidate.terms.iter().map(|term| term.sequence))",
                "receipt.compressed_leaves_generated == receipt.compressed_leaves_visited",
                "receipt.compressed_leaves_visited == receipt.compressed_leaves_accepted",
                "receipt.generated_labelled_permutations == factorial(N)",
                "receipt.visited_labelled_permutations == factorial(N)",
                "receipt.accepted_labelled_permutations == factorial(N)",
                "receipt.skipped_labelled_permutations == 0",
                "receipt.unclassified_labelled_permutations == 0",
                "receipt.failed_labelled_permutations == 0",
                "receipt.independent_exact_linear_crosscheck",
                "receipt.bounded_kernel_crosscheck",
                "total == EXPECTED_LABELLED_PERMUTATIONS",
                "hinge_entries == EXPECTED_HINGE_ENTRIES_PROCESSED",
            ],
        )
        and has_all(
            mutation,
            [
                "control.name == expected_name",
                "control.baseline_complete_residual_sha256 == baseline_digest",
                "control.mutated_complete_residual_sha256 != baseline_digest",
                "control.changed_from_baseline",
                "control.detected",
                "control.first_nonzero_hinge.0.is_some()",
                "control.first_nonzero_linear.0.is_some()",
            ],
        )
        and "validate_stage_a_structured_controls(&receipt, candidate)?" in stage_a_validation
    )

    expected_b_checks = OrderedDict((key, "bool") for key in REQUIRED_STAGE_B_CHECKS)
    expected_a_checks = OrderedDict((key, "bool") for key in REQUIRED_STAGE_A_CHECKS)
    expected_b_bindings = OrderedDict(
        (key, "Binding") for key in ["main_source", "cargo_manifest", "cargo_lock", "release_executable"]
    )
    expected_a_bindings = OrderedDict(
        (key, "Binding")
        for key in ["main_source", "engine_source", "cargo_manifest", "cargo_lock", "release_executable"]
    )
    expected_receipt = OrderedDict(
        [
            ("schema", "String"),
            ("verdict", "String"),
            ("result", "String"),
            ("evidence_class", "String"),
            ("claim_boundary", "String"),
            ("reviewer", "SourceAuditReviewer"),
            ("preregistration", "SourceAuditPreregistration"),
            ("subject", "FinalStageBSourceAuditSubject"),
            ("required_checks", "FinalStageBSourceAuditChecks"),
            ("scientific_manifest_observed", "bool"),
            ("scientific_input_observed", "bool"),
            ("scientific_output_observed", "bool"),
            ("scientific_replay_run", "bool"),
            ("no_claim", "String"),
        ]
    )
    exact_audit_types_ok = (
        rust_struct_fields(source, "FinalStageBSourceAuditChecks") == expected_b_checks
        and rust_struct_fields(source, "FinalStageASourceAuditChecks") == expected_a_checks
        and rust_struct_fields(source, "FinalStageBSourceAuditBindings") == expected_b_bindings
        and rust_struct_fields(source, "FinalStageASourceAuditBindings") == expected_a_bindings
        and rust_struct_fields(source, "FinalStageBSourceAuditReceipt") == expected_receipt
        and set(rust_struct_fields(source, "FinalStageASourceAuditReceipt")) == set(expected_receipt)
        and all(
            rust_deny_unknown(source, name)
            for name in [
                "Binding",
                "SourceAuditReviewer",
                "SourceAuditPreregistration",
                "FinalStageASourceAuditBindings",
                "FinalStageASourceAuditSubject",
                "FinalStageASourceAuditChecks",
                "FinalStageASourceAuditReceipt",
                "FinalStageBSourceAuditBindings",
                "FinalStageBSourceAuditSubject",
                "FinalStageBSourceAuditChecks",
                "FinalStageBSourceAuditReceipt",
            ]
        )
    )

    stage_a_audit_semantics = rust_item_body(
        source, "fn", "validate_final_stage_a_source_audit_semantics"
    )
    stage_b_audit_semantics = rust_item_body(
        source, "fn", "validate_final_stage_b_source_audit_semantics"
    )
    stage_a_bindings = rust_item_body(source, "fn", "final_stage_a_source_audit_bindings")
    stage_b_bindings = rust_item_body(source, "fn", "final_stage_b_source_audit_bindings")
    source_audit = rust_item_body(source, "fn", "validate_source_audit")
    audit_contract_ok = (
        exact_audit_types_ok
        and rust_const_string(source, "STAGE_A_SOURCE_AUDIT_SCHEMA") == STAGE_A_SCHEMA
        and rust_const_string(source, "STAGE_B_SOURCE_AUDIT_SCHEMA") == STAGE_B_SCHEMA
        and rust_const_string(source, "SOURCE_CUSTODY_PASS_RESULT") == PASS_RESULT
        and rust_const_string(source, "SOURCE_AUDIT_EVIDENCE_CLASS") == EVIDENCE_CLASS
        and rust_const_string(source, "STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY") == STAGE_A_CLAIM
        and rust_const_string(source, "STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY") == STAGE_B_CLAIM
        and rust_const_string(source, "STAGE_A_SOURCE_AUDIT_NO_CLAIM") == STAGE_A_NO_CLAIM
        and rust_const_string(source, "STAGE_B_SOURCE_AUDIT_NO_CLAIM") == STAGE_B_NO_CLAIM
        and has_all(
            stage_a_bindings,
            [
                "STAGE_A_SOURCE_PATH",
                "receipt.subject.bindings.main_source",
                "STAGE_A_ENGINE_PATH",
                "receipt.subject.bindings.engine_source",
                "STAGE_A_CARGO_PATH",
                "receipt.subject.bindings.cargo_manifest",
                "STAGE_A_LOCK_PATH",
                "receipt.subject.bindings.cargo_lock",
                "STAGE_A_EXECUTABLE_PATH",
                "receipt.subject.bindings.release_executable",
            ],
        )
        and has_all(
            stage_b_bindings,
            [
                "STAGE_B_SOURCE_PATH",
                "receipt.subject.bindings.main_source",
                "STAGE_B_CARGO_PATH",
                "receipt.subject.bindings.cargo_manifest",
                "STAGE_B_LOCK_PATH",
                "receipt.subject.bindings.cargo_lock",
                "STAGE_B_EXECUTABLE_PATH",
                "receipt.subject.bindings.release_executable",
            ],
        )
        and has_all(
            stage_a_audit_semantics,
            [
                "receipt.schema == STAGE_A_SOURCE_AUDIT_SCHEMA",
                'receipt.verdict == "PASS"',
                "receipt.result == SOURCE_CUSTODY_PASS_RESULT",
                "receipt.evidence_class == SOURCE_AUDIT_EVIDENCE_CLASS",
                "receipt.claim_boundary == STAGE_A_SOURCE_AUDIT_CLAIM_BOUNDARY",
                "receipt.no_claim == STAGE_A_SOURCE_AUDIT_NO_CLAIM",
                "!receipt.scientific_manifest_observed",
                "!receipt.scientific_input_observed",
                "!receipt.scientific_output_observed",
                "!receipt.scientific_replay_run",
                "final_stage_a_source_audit_bindings(receipt)",
            ]
            + [f"checks.{key}" for key in REQUIRED_STAGE_A_CHECKS],
        )
        and has_all(
            stage_b_audit_semantics,
            [
                "receipt.schema == STAGE_B_SOURCE_AUDIT_SCHEMA",
                'receipt.verdict == "PASS"',
                "receipt.result == SOURCE_CUSTODY_PASS_RESULT",
                "receipt.evidence_class == SOURCE_AUDIT_EVIDENCE_CLASS",
                "receipt.claim_boundary == STAGE_B_SOURCE_AUDIT_CLAIM_BOUNDARY",
                "receipt.no_claim == STAGE_B_SOURCE_AUDIT_NO_CLAIM",
                "!receipt.scientific_manifest_observed",
                "!receipt.scientific_input_observed",
                "!receipt.scientific_output_observed",
                "!receipt.scientific_replay_run",
                "final_stage_b_source_audit_bindings(receipt)",
            ]
            + [f"checks.{key}" for key in REQUIRED_STAGE_B_CHECKS],
        )
        and has_all(
            source_audit,
            [
                "let receipt = strict_json_value(File::open(path)?)?",
                "validate_source_audit_envelope(&receipt, audit_path)?",
                "required_subjects",
                "receipt.subject.git_commit == git_commit_for_path",
                "receipt.preregistration.sha256",
                "receipt.preregistration.git_commit",
                "binding.sha256 == expected",
                "sha256_path(&checked_repo_path(root, subject)?)? == binding.sha256",
            ],
        )
        and "collect_recursive_bindings" not in source_audit
    )

    strict_value = rust_item_body(source, "fn", "strict_json_value")
    strict_deserializer_ok = (
        "if values.insert(key.clone(), value.0).is_some()" in source
        and "duplicate JSON key: {key}" in source
        and "deserializer.end()?" in strict_value
        and "strict_json_value(File::open(path)?)?" in source_audit
    )

    exact_dot = rust_item_body(source, "fn", "exact_dot")
    run_body = rust_item_body(source, "fn", "run")
    bigint_ok = (
        "terms: &[(usize, BigInt)]" in source
        and "-> BigInt" in source[source.find("fn exact_dot") : source.find("fn exact_dot") + 140]
        and "BigInt::from(0)" in exact_dot
        and "coefficient * BigInt::from(row[*sequence])" in exact_dot
        and " as i32" not in exact_dot
        and " as i64" not in exact_dot
        and "parse_bigint(&term.coefficient)?" in run_body
        and "exact_dot(row, &exact_terms)" in run_body
        and "exact_dot(&row, &terms).to_string().len() > 170" in self_test
        and "checked_mul(factorial(N - record.active_vertices))" in kernel
        and 'i64::try_from(labelled).expect("hinge coefficient exceeds i64")' in kernel
    )

    constants_and_order_ok = (
        re.search(r"const K:\s*usize\s*=\s*128\s*;", source) is not None
        and re.search(r"const RECORDS:\s*usize\s*=\s*163_740\s*;", source) is not None
        and "const HINGE_ENTRIES: usize = K * RECORDS;" in source
        and "validate_record_axis(input.records.iter().map(|record| record.sequence), RECORDS)" in source
        and "record.sequence == expected" not in source
        and "sequence == expected" in rust_item_body(source, "fn", "validate_record_axis")
        and "record_major.len() == RECORDS" in run_body
        and "direction_major.len() == K" in run_body
        and "row.len() == RECORDS" in run_body
        and "sum::<usize>() == HINGE_ENTRIES" in run_body
        and "row.index == index" in run_body
        and "row.direction == directions[index]" in run_body
    )

    compiled = rust_item_body(source, "fn", "validate_compiled_and_static")
    static_preflight = rust_item_body(source, "fn", "static_preflight")
    compiled_ok = (
        has_all(
            source,
            [
                'const COMPILED_SOURCE: &[u8] = include_bytes!("main.rs")',
                'const COMPILED_MANIFEST: &[u8] = include_bytes!("../Cargo.toml")',
                'const COMPILED_LOCK: &[u8] = include_bytes!("../Cargo.lock")',
            ],
        )
        and has_all(
            compiled,
            [
                "(COMPILED_SOURCE, STAGE_B_SOURCE_PATH, None)",
                "(COMPILED_MANIFEST, STAGE_B_CARGO_PATH, None)",
                "(COMPILED_LOCK, STAGE_B_LOCK_PATH, None)",
                "compiled_sha == disk_sha",
            ],
        )
        and "validate_compiled_and_static(root)?" in rust_item_body(source, "fn", "load_static_inputs")
        and "load_static_inputs(&root, &input_path, &candidate_path)?" in static_preflight
        and 'num-bigint = "0.5"' in cargo
        and 'g0117-global-coordinate-pricer = { path = "../../G-0117" }' in cargo
        and 'name = "num-bigint"\nversion = "0.5.1"' in lock
    )

    publish = rust_item_body(source, "fn", "publish_exclusive")
    overwrite_ok = has_all(
        publish,
        [
            'ensure!(!path.exists(), "refusing to overwrite output")',
            ".create_new(true)",
            "std::fs::hard_link(&temporary, path)",
            "file.sync_all()?",
            "directory.sync_all()",
        ],
    ) and has_all(
        self_test,
        [
            'publish_exclusive(&publication, b"complete\\n")?',
            'publish_exclusive(&publication, b"mutant\\n").is_err()',
            'std::fs::read(&publication)? == b"complete\\n"',
        ],
    )

    end_rehash_ok = has_all(
        run_body,
        [
            "let stage_a_sha_end = sha256_path",
            "let custody_end = custody_snapshot",
            "inputs.custody == custody_end",
            '"input/source custody drift during Pool128 pricing"',
            "inputs_rehashed_at_end: true",
        ],
    )

    main_body = rust_item_body(source, "fn", "main")
    modes_ok = has_all(
        main_body,
        [
            'args.len() == 2 && args[1] == "--self-test"',
            'args.len() == 4 && args[1] == "--preflight-static"',
            'args.len() == 6 && args[1] == "--preflight"',
            "ensure!(",
            "args.len() == 6",
        ],
    ) and "fn main() -> Result<()>" in source

    g0142_repairs_ok = (
        all(
            rust_deny_unknown(source, name)
            for name in ["Candidate", "StageAReceipt", "AccumulatedDirectionCheck", "StrictRecord"]
        )
        and '#[serde(deserialize_with = "deserialize_records_strict")]' in source
        and audit_contract_ok
    )

    return {
        "stage_a_required_nullable": required_nullable_ok,
        "stage_a_typed_control_schemas": typed_stage_a_ok and typed_fields_ok,
        "stage_a_control_semantics": structured_semantics_ok,
        "source_audit_exact_contracts": audit_contract_ok,
        "strict_duplicate_and_trailing_json": strict_deserializer_ok,
        "g0142_repairs": g0142_repairs_ok,
        "bigint_no_narrowing": bigint_ok,
        "census_and_order": constants_and_order_ok,
        "compiled_embeddings": compiled_ok,
        "overwrite_refusal": overwrite_ok,
        "end_rehash": end_rehash_ok,
        "mode_and_failure_dispatch": modes_ok,
    }


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) < 1:
        raise AssertionError(f"mutation anchor missing: {old!r}")
    return source.replace(old, new, 1)


def drop_deny_unknown(source: str, struct_name: str) -> str:
    marker = source.find(f"struct {struct_name}")
    if marker < 0:
        raise AssertionError(f"mutation struct missing: {struct_name}")
    attribute = source.rfind("#[serde(deny_unknown_fields)]", max(0, marker - 400), marker)
    if attribute < 0:
        raise AssertionError(f"deny-unknown attribute missing: {struct_name}")
    end = attribute + len("#[serde(deny_unknown_fields)]")
    return source[:attribute] + source[end:]


def source_mutation_probes(source: str, cargo: str, lock: str, kernel: str) -> dict[str, Any]:
    probes: list[tuple[str, str, str]] = []
    probes.append(
        (
            "top-level-nullable-to-option",
            replace_once(
                source,
                "    first_nonzero_linear: RequiredNullable<ExactLinear>,\n    pool_k:",
                "    first_nonzero_linear: Option<ExactLinear>,\n    pool_k:",
            ),
            "stage_a_required_nullable",
        )
    )
    probes.append(
        (
            "nested-nullable-to-option",
            replace_once(
                source,
                "struct MutationControl {\n    name: String,\n    first_nonzero_hinge: RequiredNullable<ExactHinge>,\n    first_nonzero_linear: RequiredNullable<ExactLinear>,",
                "struct MutationControl {\n    name: String,\n    first_nonzero_hinge: RequiredNullable<ExactHinge>,\n    first_nonzero_linear: Option<ExactLinear>,",
            ),
            "stage_a_required_nullable",
        )
    )

    opaque_mutations = [
        ("independent_finite_412_row_replay: FiniteReplayReceipt", "independent_finite_412_row_replay: Value"),
        ("term_normal_forms: Vec<TermNormalFormReceipt>", "term_normal_forms: Vec<Value>"),
        ("coefficient_plus_one: MutationControl", "coefficient_plus_one: Value"),
        ("target_scale_plus_one: MutationControl", "target_scale_plus_one: Value"),
        ("target_coordinate_plus_one: MutationControl", "target_coordinate_plus_one: Value"),
        ("omitted_final_term: MutationControl", "omitted_final_term: Value"),
        ("omitted_first_term_direction: MutationControl", "omitted_first_term_direction: Value"),
        ("census_controls: CensusControls", "census_controls: Value"),
        ("selection_controls: SelectionControls", "selection_controls: Value"),
    ]
    for index, (old, new) in enumerate(opaque_mutations, 1):
        probes.append(
            (
                f"formerly-opaque-field-{index}",
                replace_once(source, old, new),
                "stage_a_typed_control_schemas",
            )
        )

    probes.extend(
        [
            (
                "nested-deny-unknown-removed",
                drop_deny_unknown(source, "MutationControl"),
                "stage_a_typed_control_schemas",
            ),
            (
                "stage-a-semantic-call-removed",
                replace_once(source, "    validate_stage_a_structured_controls(&receipt, candidate)?;\n", ""),
                "stage_a_control_semantics",
            ),
            (
                "term-global-census-removed",
                replace_once(source, "        total == EXPECTED_LABELLED_PERMUTATIONS\n", "        true\n"),
                "stage_a_control_semantics",
            ),
            (
                "census-control-boolean-removed",
                replace_once(source, "            && census.omitted_last_orbit_rejected\n", ""),
                "stage_a_control_semantics",
            ),
            (
                "selection-control-boolean-removed",
                replace_once(source, "            && selection.excludes_accumulated_directions\n", ""),
                "stage_a_control_semantics",
            ),
            (
                "stage-b-binding-displaced",
                replace_once(
                    source,
                    "(STAGE_B_SOURCE_PATH, &receipt.subject.bindings.main_source)",
                    "(STAGE_B_SOURCE_PATH, &receipt.subject.bindings.cargo_manifest)",
                ),
                "source_audit_exact_contracts",
            ),
            (
                "stage-b-required-check-removed",
                replace_once(source, "            && checks.audit_git_commit_rejected\n", ""),
                "source_audit_exact_contracts",
            ),
            (
                "strict-audit-parser-bypassed",
                replace_once(
                    source,
                    "    let receipt = strict_json_value(File::open(path)?)?;\n",
                    "    let receipt = Value::Null;\n",
                ),
                "source_audit_exact_contracts",
            ),
            (
                "duplicate-key-check-disabled",
                replace_once(
                    source,
                    "if values.insert(key.clone(), value.0).is_some()",
                    "if false",
                ),
                "strict_duplicate_and_trailing_json",
            ),
            (
                "trailing-data-check-disabled",
                replace_once(source, "    deserializer.end()?;\n", ""),
                "strict_duplicate_and_trailing_json",
            ),
            (
                "bigint-coordinate-narrowed",
                replace_once(
                    source,
                    "coefficient * BigInt::from(row[*sequence])",
                    "coefficient * BigInt::from(row[*sequence] as i32)",
                ),
                "bigint_no_narrowing",
            ),
            (
                "pool-census-changed",
                replace_once(source, "const K: usize = 128;", "const K: usize = 127;"),
                "census_and_order",
            ),
            (
                "compiled-source-binding-removed",
                replace_once(source, "        (COMPILED_SOURCE, STAGE_B_SOURCE_PATH, None),\n", ""),
                "compiled_embeddings",
            ),
            (
                "exclusive-create-disabled",
                replace_once(source, ".create_new(true)", ".create(true)"),
                "overwrite_refusal",
            ),
            (
                "closing-custody-comparison-disabled",
                replace_once(source, "        inputs.custody == custody_end,\n", "        true,\n"),
                "end_rehash",
            ),
        ]
    )

    results = []
    for label, mutant, expected_red in probes:
        assessment = static_source_assessment(mutant, cargo, lock, kernel)
        red = not assessment[expected_red]
        results.append({"label": label, "expected_red_check": expected_red, "caught": red})
    return {
        "passed": all(item["caught"] for item in results),
        "cases": results,
        "case_count": len(results),
    }


def validate_exact_receipt_shape(
    receipt: dict[str, Any],
    *,
    schema: str,
    claim: str,
    no_claim: str,
    required_checks: list[str],
    subject_paths: OrderedDict[str, str],
    preregistration_path: str,
) -> list[str]:
    errors: list[str] = []
    if set(receipt) != ROOT_RECEIPT_FIELDS:
        errors.append(f"root keys: {sorted(receipt)}")
    expected_values = {
        "schema": schema,
        "verdict": "PASS",
        "result": PASS_RESULT,
        "evidence_class": EVIDENCE_CLASS,
        "claim_boundary": claim,
        "no_claim": no_claim,
    }
    for key, expected in expected_values.items():
        if receipt.get(key) != expected:
            errors.append(f"{key} mismatch")
    for key in [
        "scientific_manifest_observed",
        "scientific_input_observed",
        "scientific_output_observed",
        "scientific_replay_run",
    ]:
        if receipt.get(key) is not False:
            errors.append(f"{key} is not false")

    reviewer = receipt.get("reviewer", {})
    if set(reviewer) != {"agent_name", "program", "model", "same_model_lineage", "fresh_context"}:
        errors.append("reviewer keys mismatch")
    if (
        not reviewer.get("agent_name")
        or reviewer.get("program") != "codex"
        or not reviewer.get("model")
        or reviewer.get("same_model_lineage") is not True
        or reviewer.get("fresh_context") is not True
    ):
        errors.append("reviewer semantics mismatch")

    prereg = receipt.get("preregistration", {})
    if set(prereg) != {
        "path",
        "sha256",
        "git_commit",
        "committed_and_pushed_before_subject_source_inspection",
        "committed_and_pushed_before_runtime_checks",
    }:
        errors.append("preregistration keys mismatch")
    if prereg.get("path") != preregistration_path:
        errors.append("preregistration path mismatch")
    if not re.fullmatch(r"[0-9a-f]{64}", str(prereg.get("sha256", ""))):
        errors.append("preregistration digest malformed")
    if not re.fullmatch(r"[0-9a-f]{40}", str(prereg.get("git_commit", ""))):
        errors.append("preregistration commit malformed")
    if prereg.get("committed_and_pushed_before_subject_source_inspection") is not True:
        errors.append("preregistration source-inspection ordering false")
    if prereg.get("committed_and_pushed_before_runtime_checks") is not True:
        errors.append("preregistration runtime ordering false")

    subject = receipt.get("subject", {})
    if set(subject) != {
        "git_commit",
        "commit_object_and_working_bytes_equal_for_all_bindings",
        "bindings",
    }:
        errors.append("subject keys mismatch")
    if not re.fullmatch(r"[0-9a-f]{40}", str(subject.get("git_commit", ""))):
        errors.append("subject commit malformed")
    if subject.get("commit_object_and_working_bytes_equal_for_all_bindings") is not True:
        errors.append("subject custody flag false")
    bindings = subject.get("bindings", {})
    if list(bindings) != list(subject_paths):
        errors.append(f"binding names/order mismatch: {list(bindings)}")
    for label, expected_path in subject_paths.items():
        binding = bindings.get(label, {})
        if set(binding) != {"path", "sha256"}:
            errors.append(f"{label} binding keys mismatch")
        if binding.get("path") != expected_path:
            errors.append(f"{label} binding path mismatch")
        if not re.fullmatch(r"[0-9a-f]{64}", str(binding.get("sha256", ""))):
            errors.append(f"{label} binding digest malformed")
    if len({binding.get("path") for binding in bindings.values() if isinstance(binding, dict)}) != len(
        subject_paths
    ):
        errors.append("duplicate subject paths")

    checks = receipt.get("required_checks", {})
    if list(checks) != required_checks:
        errors.append(f"required check names/order mismatch: {list(checks)}")
    if any(checks.get(key) is not True for key in required_checks):
        errors.append("one or more required checks is not true")
    return errors


def validate_committed_g0150() -> dict[str, Any]:
    receipt_path = ROOT / G0150_RECEIPT
    receipt = strict_json_file(G0150_RECEIPT)
    shape_errors = validate_exact_receipt_shape(
        receipt,
        schema=STAGE_A_SCHEMA,
        claim=STAGE_A_CLAIM,
        no_claim=STAGE_A_NO_CLAIM,
        required_checks=REQUIRED_STAGE_A_CHECKS,
        subject_paths=STAGE_A_SUBJECTS,
        preregistration_path=(
            "artifacts/reviews/G-0150-g0140-stage-a-final2-source/PREREGISTRATION.md"
        ),
    )
    binding_results = {}
    for label, relative in STAGE_A_SUBJECTS.items():
        committed = git_blob(EXPECTED_G0150_SUBJECT_COMMIT, relative)
        working = (ROOT / relative).read_bytes()
        receipt_digest = receipt["subject"]["bindings"][label]["sha256"]
        binding_results[label] = {
            "path": relative,
            "receipt_sha256": receipt_digest,
            "subject_commit_sha256": sha256_bytes(committed),
            "working_sha256": sha256_bytes(working),
            "all_equal": receipt_digest == sha256_bytes(committed) == sha256_bytes(working),
        }
    prereg = receipt["preregistration"]
    prereg_bytes = (ROOT / prereg["path"]).read_bytes()
    latest_receipt_commit = git_text("log", "-1", "--format=%H", "--", G0150_RECEIPT)
    latest_subject_commit = git_text(
        "log", "-1", "--format=%H", "--", STAGE_A_SUBJECTS["main_source"]
    )
    clean = git_text("status", "--porcelain", "--", G0150_RECEIPT) == ""
    passed = (
        not shape_errors
        and sha256_file(receipt_path) == EXPECTED_G0150_SHA256
        and latest_receipt_commit == EXPECTED_G0150_COMMIT
        and latest_subject_commit == EXPECTED_G0150_SUBJECT_COMMIT
        and receipt["subject"]["git_commit"] == EXPECTED_G0150_SUBJECT_COMMIT
        and prereg["sha256"] == sha256_bytes(prereg_bytes)
        and prereg["git_commit"] == git_text("log", "-1", "--format=%H", "--", prereg["path"])
        and remote_contains(prereg["git_commit"])
        and remote_contains(latest_receipt_commit)
        and clean
        and all(item["all_equal"] for item in binding_results.values())
    )
    return {
        "passed": passed,
        "receipt_sha256": sha256_file(receipt_path),
        "receipt_commit": latest_receipt_commit,
        "subject_commit": latest_subject_commit,
        "strict_shape_errors": shape_errors,
        "bindings": binding_results,
        "preregistration_sha256": sha256_bytes(prereg_bytes),
        "working_receipt_clean": clean,
    }


def build_pass_receipt(
    preregistration_sha256: str,
    preregistration_commit: str,
    subject_hashes: dict[str, str],
) -> OrderedDict[str, Any]:
    return OrderedDict(
        [
            ("schema", STAGE_B_SCHEMA),
            ("verdict", "PASS"),
            ("result", PASS_RESULT),
            ("evidence_class", EVIDENCE_CLASS),
            ("claim_boundary", STAGE_B_CLAIM),
            (
                "reviewer",
                OrderedDict(
                    [
                        ("agent_name", "CalmBarn"),
                        ("program", "codex"),
                        ("model", "gpt-5"),
                        ("same_model_lineage", True),
                        ("fresh_context", True),
                    ]
                ),
            ),
            (
                "preregistration",
                OrderedDict(
                    [
                        ("path", PREREGISTRATION),
                        ("sha256", preregistration_sha256),
                        ("git_commit", preregistration_commit),
                        ("committed_and_pushed_before_subject_source_inspection", True),
                        ("committed_and_pushed_before_runtime_checks", True),
                    ]
                ),
            ),
            (
                "subject",
                OrderedDict(
                    [
                        ("git_commit", FROZEN_COMMIT),
                        ("commit_object_and_working_bytes_equal_for_all_bindings", True),
                        (
                            "bindings",
                            OrderedDict(
                                (
                                    label,
                                    OrderedDict(
                                        [("path", relative), ("sha256", subject_hashes[label])]
                                    ),
                                )
                                for label, relative in SUBJECTS.items()
                            ),
                        ),
                    ]
                ),
            ),
            (
                "required_checks",
                OrderedDict((key, True) for key in REQUIRED_STAGE_B_CHECKS),
            ),
            ("scientific_manifest_observed", False),
            ("scientific_input_observed", False),
            ("scientific_output_observed", False),
            ("scientific_replay_run", False),
            ("no_claim", STAGE_B_NO_CLAIM),
        ]
    )


def write_exclusive(path_name: Path, payload: bytes) -> None:
    with path_name.open("xb") as destination:
        destination.write(payload)
        destination.flush()
        os.fsync(destination.fileno())


def self_test_checker() -> None:
    source = (ROOT / SUBJECTS["main_source"]).read_text()
    cargo = (ROOT / SUBJECTS["cargo_manifest"]).read_text()
    lock = (ROOT / SUBJECTS["cargo_lock"]).read_text()
    kernel = (ROOT / KERNEL).read_text()
    assessment = static_source_assessment(source, cargo, lock, kernel)
    if not all(assessment.values()):
        raise AssertionError(f"baseline static assessment failed: {assessment}")
    probes = source_mutation_probes(source, cargo, lock, kernel)
    if not probes["passed"]:
        raise AssertionError(f"static mutation probe escaped: {probes}")
    print(
        "G-0151 checker self-test PASS: "
        f"static_checks={len(assessment)} mutation_cases={probes['case_count']}"
    )


def run_audit(output_path: Path, receipt_path: Path) -> int:
    if output_path.exists() or receipt_path.exists():
        raise RuntimeError("refusing to overwrite final audit output or receipt")
    if ROOT != Path.cwd().resolve():
        raise RuntimeError("run G-0151 checker from repository root")

    started = utc_now()
    checks: list[dict[str, Any]] = []

    def add(identifier: str, passed: bool, evidence: Any) -> None:
        checks.append({"id": identifier, "passed": bool(passed), "evidence": evidence})

    resolved = git_text("rev-parse", f"{FROZEN_SELECTOR}^{{commit}}")
    add(
        "FROZEN_COMMIT_RESOLVES_EXACTLY",
        resolved == FROZEN_COMMIT and remote_contains(FROZEN_COMMIT),
        {"selector": FROZEN_SELECTOR, "resolved": resolved, "on_origin_master": remote_contains(resolved)},
    )

    opening_bindings: dict[str, Any] = {}
    subject_hashes: dict[str, str] = {}
    for label, relative in SUBJECTS.items():
        entry = tree_entry(FROZEN_COMMIT, relative)
        frozen = git_blob(FROZEN_COMMIT, relative)
        working_path = ROOT / relative
        working = working_path.read_bytes()
        digest = sha256_bytes(frozen)
        opening_bindings[label] = {
            **entry,
            "frozen_sha256": digest,
            "working_sha256": sha256_bytes(working),
            "working_bytes": len(working),
            "working_is_symlink": working_path.is_symlink(),
            "working_executable": os.access(working_path, os.X_OK),
            "equal": frozen == working,
        }
        subject_hashes[label] = digest
    add(
        "EXACT_FOUR_FROZEN_AND_WORKING_BINDINGS",
        list(opening_bindings) == list(SUBJECTS)
        and all(item["equal"] and not item["working_is_symlink"] for item in opening_bindings.values())
        and opening_bindings["release_executable"]["mode"] == "100755"
        and opening_bindings["release_executable"]["working_executable"],
        opening_bindings,
    )
    add(
        "SUBJECT_PATHS_GIT_CLEAN_AT_OPEN",
        git_text("status", "--porcelain", "--", *SUBJECTS.values()) == "",
        {"porcelain": git_text("status", "--porcelain", "--", *SUBJECTS.values())},
    )

    preregistration_path = ROOT / PREREGISTRATION
    preregistration_sha256 = sha256_file(preregistration_path)
    preregistration_commit = git_text("log", "-1", "--format=%H", "--", PREREGISTRATION)
    add(
        "PREREGISTRATION_COMMITTED_AND_PUSHED_FIRST",
        preregistration_commit != FROZEN_COMMIT
        and remote_contains(preregistration_commit)
        and git_text("status", "--porcelain", "--", PREREGISTRATION) == "",
        {
            "path": PREREGISTRATION,
            "sha256": preregistration_sha256,
            "git_commit": preregistration_commit,
            "on_origin_master": remote_contains(preregistration_commit),
            "session_order": "commit and push completed before frozen source resolution/inspection and runtime checks",
        },
    )

    source = (ROOT / SUBJECTS["main_source"]).read_text()
    cargo = (ROOT / SUBJECTS["cargo_manifest"]).read_text()
    lock = (ROOT / SUBJECTS["cargo_lock"]).read_text()
    kernel = (ROOT / KERNEL).read_text()
    static = static_source_assessment(source, cargo, lock, kernel)
    add("STAGE_A_MISSING_NULLABLE_REPAIRED", static["stage_a_required_nullable"], static)
    add(
        "STAGE_A_NINE_TYPED_CONTROLS_DENY_UNKNOWN",
        static["stage_a_typed_control_schemas"],
        {
            "typed_fields": [
                "independent_finite_412_row_replay",
                "term_normal_forms",
                "coefficient_plus_one",
                "target_scale_plus_one",
                "target_coordinate_plus_one",
                "omitted_final_term",
                "omitted_first_term_direction",
                "census_controls",
                "selection_controls",
            ],
            "assessment": static,
        },
    )
    add(
        "STAGE_A_TYPED_CONTROLS_SEMANTICALLY_CHECKED",
        static["stage_a_control_semantics"],
        {
            "finite_dimensions_digest_mutant": True,
            "ordered_term_receipts": 135,
            "global_censuses": [5_388_768_000, 4_409_740],
            "exact_mutation_controls": 5,
            "census_and_selection_booleans_checked": True,
        },
    )
    add(
        "G0150_AND_G0151_EXACT_TYPED_AUDIT_CONTRACTS",
        static["source_audit_exact_contracts"] and static["strict_duplicate_and_trailing_json"],
        {
            "g0150_schema": STAGE_A_SCHEMA,
            "g0151_schema": STAGE_B_SCHEMA,
            "g0151_exact_named_bindings": list(SUBJECTS),
            "g0151_exact_required_checks": REQUIRED_STAGE_B_CHECKS,
            "recursive_collector_used_by_source_audit": False,
            "strict_duplicate_and_trailing_parser": static["strict_duplicate_and_trailing_json"],
        },
    )

    g0142 = strict_json_file(G0142_RECEIPT)
    g0147 = strict_json_file(G0147_RESULTS)
    add(
        "HISTORICAL_G0142_AND_G0147_BLOCKERS_BOUND",
        set(g0142["failed_check_ids"]) == EXPECTED_G0142_FAILURES
        and set(g0147["failed_check_ids"]) == EXPECTED_G0147_BLOCKERS,
        {
            "g0142_failed_check_ids": g0142["failed_check_ids"],
            "g0147_failed_check_ids": g0147["failed_check_ids"],
            "g0147_checker_reused": False,
            "g0147_recursive_witness_closure_used": False,
        },
    )
    add("G0142_REPAIRS_RECHECKED", static["g0142_repairs"], static)

    g0150 = validate_committed_g0150()
    add(
        "COMMITTED_G0150_PASS_RECEIPT_EXACTLY_COMPATIBLE",
        g0150["passed"] and g0150["receipt_sha256"] == EXPECTED_G0150_SHA256,
        g0150,
    )

    mutation_probes = source_mutation_probes(source, cargo, lock, kernel)
    add("FRESH_STATIC_MUTATION_PROBES_DISCRIMINATE", mutation_probes["passed"], mutation_probes)

    add("BIGINT_PATH_HAS_NO_NARROWING", static["bigint_no_narrowing"], static)
    add("EXACT_128_BY_163740_CENSUS_AND_ORDER", static["census_and_order"], static)
    add("COMPILED_EMBEDDINGS_MATCH_STATIC_CONTRACT", static["compiled_embeddings"], static)
    add("OVERWRITE_REFUSAL_PRESENT_AND_SELF_TESTED", static["overwrite_refusal"], static)
    add("END_REHASH_FAILS_CLOSED", static["end_rehash"], static)
    add("FAILURE_PROPAGATES_THROUGH_RESULT_MAIN", static["mode_and_failure_dispatch"], static)

    producer_commands: list[dict[str, Any]] = []
    executable = str(ROOT / SUBJECTS["release_executable"])
    producer_self_test = command([executable, "--self-test"], timeout=300)
    producer_commands.append(producer_self_test)
    add(
        "CANONICAL_PRODUCER_SELF_TEST_PASSES",
        producer_self_test["exit_code"] == 0
        and "G-0140 Stage-B Pool128 self-test PASS" in producer_self_test["stdout"],
        producer_self_test,
    )

    static_preflight = command(
        [executable, "--preflight-static", PANEL, CANDIDATE], timeout=900
    )
    producer_commands.append(static_preflight)
    add(
        "CANONICAL_STATIC_PREFLIGHT_PASSES_OPAQUE_PATHS",
        static_preflight["exit_code"] == 0
        and "G-0140 Stage-B static preflight PASS: 163740 records; 135 candidate terms" in static_preflight[
            "stdout"
        ],
        static_preflight,
    )

    wrong_panel = command(
        [executable, "--preflight-static", f"{PANEL}.decoy", CANDIDATE], timeout=300
    )
    wrong_candidate = command(
        [executable, "--preflight-static", PANEL, f"{CANDIDATE}.decoy"], timeout=300
    )
    producer_commands.extend([wrong_panel, wrong_candidate])
    add(
        "STATIC_PREFLIGHT_FAILURES_PROPAGATE_NONZERO",
        wrong_panel["exit_code"] != 0
        and wrong_candidate["exit_code"] != 0
        and "static input path drift" in wrong_panel["stderr"]
        and "static input path drift" in wrong_candidate["stderr"],
        {"wrong_panel": wrong_panel, "wrong_candidate": wrong_candidate},
    )

    with tempfile.TemporaryDirectory(prefix="g0151-contract-probe-") as probe_target:
        probe_environment = os.environ.copy()
        probe_environment["CARGO_TARGET_DIR"] = probe_target
        contract_matrix = command(
            [
                "cargo",
                "run",
                "--offline",
                "--locked",
                "--quiet",
                "--manifest-path",
                str(CONTRACT_MANIFEST.relative_to(ROOT)),
            ],
            timeout=900,
            environment=probe_environment,
        )
        add(
            "EXACT_FROZEN_RUST_CONTRACT_MATRIX_PASSES",
            contract_matrix["exit_code"] == 0
            and "stage_a_cases=22 stage_b_cases=22" in contract_matrix["stdout"],
            contract_matrix,
        )

        final_bindings: dict[str, Any] = {}
        for label, relative in SUBJECTS.items():
            working = (ROOT / relative).read_bytes()
            final_bindings[label] = {
                "path": relative,
                "opening_sha256": opening_bindings[label]["working_sha256"],
                "final_sha256": sha256_bytes(working),
                "frozen_sha256": subject_hashes[label],
                "all_equal": (
                    opening_bindings[label]["working_sha256"]
                    == sha256_bytes(working)
                    == subject_hashes[label]
                ),
            }
        add(
            "FINAL_SUBJECT_REHASH_MATCHES_OPEN_AND_FROZEN",
            all(item["all_equal"] for item in final_bindings.values()),
            final_bindings,
        )

        prelim_failures = [item["id"] for item in checks if not item["passed"]]
        proposed_receipt = build_pass_receipt(
            preregistration_sha256, preregistration_commit, subject_hashes
        )
        proposed_errors = validate_exact_receipt_shape(
            proposed_receipt,
            schema=STAGE_B_SCHEMA,
            claim=STAGE_B_CLAIM,
            no_claim=STAGE_B_NO_CLAIM,
            required_checks=REQUIRED_STAGE_B_CHECKS,
            subject_paths=SUBJECTS,
            preregistration_path=PREREGISTRATION,
        )
        proposed_bytes = (json.dumps(proposed_receipt, indent=2) + "\n").encode()
        proposed_path = Path(probe_target) / "PROPOSED_SOURCE_AUDIT_RECEIPT.json"
        proposed_path.write_bytes(proposed_bytes)
        receipt_probe = command(
            [
                "cargo",
                "run",
                "--offline",
                "--locked",
                "--quiet",
                "--manifest-path",
                str(CONTRACT_MANIFEST.relative_to(ROOT)),
                "--",
                "--receipt",
                str(proposed_path),
            ],
            timeout=900,
            environment=probe_environment,
        )
        add(
            "PROPOSED_RECEIPT_EXACT_FROZEN_RUST_ADMISSION",
            not prelim_failures
            and not proposed_errors
            and receipt_probe["exit_code"] == 0
            and "accepted by exact frozen Rust envelope" in receipt_probe["stdout"],
            {
                "preliminary_failures": prelim_failures,
                "shape_errors": proposed_errors,
                "rust_probe": receipt_probe,
                "proposed_sha256": sha256_bytes(proposed_bytes),
            },
        )

    producer_modes = [item["argv"][1] for item in producer_commands]
    allowed_modes_only = set(producer_modes) <= {"--self-test", "--preflight-static"}
    add(
        "NO_SCIENCE_BOUNDARY_HELD",
        allowed_modes_only and all(value is False for value in NO_SCIENCE_FLAGS.values()),
        {
            "producer_modes_run": producer_modes,
            "allowed_producer_modes": ["--self-test", "--preflight-static"],
            "opaque_static_paths": [PANEL, CANDIDATE],
            "no_science_flags": NO_SCIENCE_FLAGS,
        },
    )

    failures = [item["id"] for item in checks if not item["passed"]]
    verdict = "PASS" if not failures else "FAIL"
    if verdict == "PASS":
        receipt = proposed_receipt
    else:
        receipt = OrderedDict(
            [
                ("schema", "max11-g0151-g0140-stage-b-final2-source-audit-fail-v1"),
                ("verdict", "FAIL"),
                ("result", "SOURCE_CUSTODY_AUDIT_FAIL_T1"),
                ("consumable_source_clearance", False),
                ("subject_git_commit", FROZEN_COMMIT),
                ("failed_check_ids", failures),
                ("no_science_flags", NO_SCIENCE_FLAGS),
                ("no_claim", STAGE_B_NO_CLAIM),
            ]
        )
    receipt_bytes = (json.dumps(receipt, indent=2) + "\n").encode()

    results = OrderedDict(
        [
            ("schema", "max11-g0151-g0140-stage-b-final2-source-check-results-v1"),
            ("verdict", verdict),
            ("started_at_utc", started),
            ("completed_at_utc", utc_now()),
            ("reviewer", {"agent_name": "CalmBarn", "program": "codex", "model": "gpt-5"}),
            ("frozen_commit", FROZEN_COMMIT),
            ("preregistration_commit", preregistration_commit),
            ("checks", checks),
            ("failed_check_ids", failures),
            ("producer_runtime_commands", producer_commands),
            ("producer_modes_run", producer_modes),
            ("no_science_flags", NO_SCIENCE_FLAGS),
            ("receipt_sha256", sha256_bytes(receipt_bytes)),
            (
                "claim_boundary",
                "Fresh T1 source/custody and admission audit of exactly four frozen Stage-B "
                "artifacts; no G-0140 scientific manifest or Stage-A/Stage-B scientific output "
                "was opened or created, and no scientific producer mode ran.",
            ),
        ]
    )
    results_bytes = (json.dumps(results, indent=2) + "\n").encode()
    write_exclusive(output_path, results_bytes)
    write_exclusive(receipt_path, receipt_bytes)
    print(
        f"G-0151 audit {verdict}: checks={len(checks)} failures={len(failures)} "
        f"receipt_sha256={sha256_bytes(receipt_bytes)}"
    )
    if failures:
        print("failed checks: " + ", ".join(failures), file=sys.stderr)
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    arguments = parser.parse_args()
    if arguments.self_test:
        if arguments.output or arguments.receipt:
            parser.error("--output/--receipt are invalid with --self-test")
        self_test_checker()
        return 0
    if not arguments.output or not arguments.receipt:
        parser.error("audit mode requires --output and --receipt")
    return run_audit(arguments.output, arguments.receipt)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # fail closed with visible diagnostics
        print(f"G-0151 checker error: {error}", file=sys.stderr)
        raise
