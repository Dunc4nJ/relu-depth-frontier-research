#!/usr/bin/env python3
"""Outcome-blind G-0147 audit of the exact frozen G-0140 Stage-B producer."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any


REVIEW = Path(__file__).resolve().parent
ROOT = REVIEW.parents[2]
SUBJECT_COMMIT = "f55df23361382a9b99b5ca3c07794611a7253c6c"

SOURCE = "artifacts/math/G-0140/stage_b_pricer/src/main.rs"
CARGO = "artifacts/math/G-0140/stage_b_pricer/Cargo.toml"
LOCK = "artifacts/math/G-0140/stage_b_pricer/Cargo.lock"
EXECUTABLE = (
    "artifacts/math/G-0140/stage_b_pricer/target/release/"
    "g0140-stage-b-pool128-coordinate-pricer"
)
STAGE_A_SOURCE = "artifacts/math/G-0140/stage_a_pool/src/main.rs"
KERNEL_SOURCE = "artifacts/math/G-0117/src/lib.rs"
HISTORICAL_RECEIPT = (
    "artifacts/reviews/G-0142-g0140-stage-b-source/SOURCE_AUDIT_RECEIPT.json"
)
PANEL = "artifacts/math/G-0113/panel_solver_input_v1.json"
CANDIDATE = "artifacts/math/G-0135/full_family_master_result_v3.json"

EXPECTED: dict[str, str] = {
    SOURCE: "f6c4c4b210a32c8453626fd9a63bfde8a3083f6fb083dce56646a3361289390a",
    CARGO: "425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c",
    LOCK: "8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a",
    EXECUTABLE: "0dcb50e154797ee8104457a93ce172a46054d9a5836c499cf31796134ccb5050",
}

EXPECTED_STAGE_A_AUDIT_SCHEMA = "max11-g0146-g0140-stage-a-final-source-audit-v1"
EXPECTED_STAGE_B_AUDIT_SCHEMA = "max11-g0147-g0140-stage-b-final-source-audit-v1"
EXPECTED_SOURCE_AUDIT_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
EXPECTED_EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def run(argv: list[str], *, cwd: Path = ROOT, timeout: int = 180) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        argv,
        cwd=cwd,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
    )


def git_bytes(commit: str, path: str) -> bytes:
    result = run(["git", "show", f"{commit}:{path}"], timeout=60)
    if result.returncode != 0:
        raise RuntimeError(
            f"git show failed for {commit}:{path}: {result.stderr.decode(errors='replace')}"
        )
    return result.stdout


def git_tree_entry(commit: str, path: str) -> tuple[str, str]:
    result = run(["git", "ls-tree", commit, "--", path], timeout=60)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.decode(errors="replace"))
    fields = result.stdout.decode().strip().split()
    if len(fields) != 4 or fields[1] != "blob" or fields[3] != path:
        raise RuntimeError(f"missing or malformed tree entry for {path}")
    return fields[0], fields[2]


def function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*(?:<[^>]*>)?\s*\(", source)
    if not match:
        raise ValueError(f"function not found: {name}")
    start = source.find("{", match.end())
    if start < 0:
        raise ValueError(f"function body not found: {name}")
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[start : index + 1]
    raise ValueError(f"unclosed function body: {name}")


def struct_span(source: str, name: str) -> tuple[int, str]:
    match = re.search(rf"\bstruct\s+{re.escape(name)}(?:\s*<[^>]*>)?\s*\{{", source)
    if not match:
        raise ValueError(f"struct not found: {name}")
    start = source.find("{", match.start())
    depth = 0
    for index in range(start, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return match.start(), source[start + 1 : index]
    raise ValueError(f"unclosed struct: {name}")


def struct_fields(source: str, name: str) -> dict[str, str]:
    _, body = struct_span(source, name)
    fields: dict[str, str] = {}
    for line in body.splitlines():
        match = re.match(
            r"^\s*(?:pub(?:\([^)]*\))?\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)(?:,\s*)?$",
            line,
        )
        if match:
            fields[match.group(1)] = re.sub(r"\s+", " ", match.group(2).strip())
    return fields


def denies_unknown_fields(source: str, name: str) -> bool:
    start, _ = struct_span(source, name)
    attributes: list[str] = []
    for line in reversed(source[:start].splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#["):
            attributes.append(stripped)
            continue
        break
    return "#[serde(deny_unknown_fields)]" in attributes


def command_evidence(argv: list[str], *, timeout: int) -> dict[str, Any]:
    started = time.monotonic()
    completed = run(argv, timeout=timeout)
    stdout = completed.stdout.decode(errors="replace")
    stderr = completed.stderr.decode(errors="replace")
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": stdout,
        "stderr": stderr,
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "wall_seconds": round(time.monotonic() - started, 6),
    }


def option_omission_probe() -> dict[str, Any]:
    cargo = b"""[package]
name = \"g0147-serde-option-omission-probe\"
version = \"0.0.0\"
edition = \"2024\"

[dependencies]
serde = { version = \"=1.0.229\", features = [\"derive\"] }
serde_json = \"=1.0.151\"
"""
    main = br'''use serde::Deserialize;

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ExactLinear {
    coordinate: usize,
    coefficient: String,
}

#[allow(dead_code)]
#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct ReceiptProjection {
    first_nonzero_linear: Option<ExactLinear>,
}

fn main() {
    let omitted: ReceiptProjection = serde_json::from_str("{}").unwrap();
    let explicit_null: ReceiptProjection =
        serde_json::from_str(r#"{"first_nonzero_linear":null}"#).unwrap();
    let unknown_rejected = serde_json::from_str::<ReceiptProjection>(r#"{"extra":1}"#).is_err();
    assert!(omitted.first_nonzero_linear.is_none());
    assert!(explicit_null.first_nonzero_linear.is_none());
    assert!(unknown_rejected);
    println!("omitted_is_none=true explicit_null_is_none=true unknown_rejected=true");
}
'''
    with tempfile.TemporaryDirectory(prefix="g0147-serde-probe-") as raw:
        root = Path(raw)
        (root / "src").mkdir()
        (root / "Cargo.toml").write_bytes(cargo)
        (root / "src/main.rs").write_bytes(main)
        environment = os.environ.copy()
        environment["CARGO_TARGET_DIR"] = str(root / "target")
        started = time.monotonic()
        completed = subprocess.run(
            ["cargo", "run", "--quiet", "--offline"],
            cwd=root,
            env=environment,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=180,
        )
        return {
            "argv": ["cargo", "run", "--quiet", "--offline"],
            "locked_dependency_versions": {"serde": "1.0.229", "serde_json": "1.0.151"},
            "exit_code": completed.returncode,
            "stdout": completed.stdout.decode(errors="replace"),
            "stderr": completed.stderr.decode(errors="replace"),
            "stdout_sha256": sha256_bytes(completed.stdout),
            "stderr_sha256": sha256_bytes(completed.stderr),
            "wall_seconds": round(time.monotonic() - started, 6),
        }


def recursive_bindings(value: Any) -> list[dict[str, str]]:
    found: list[dict[str, str]] = []
    if isinstance(value, list):
        for item in value:
            found.extend(recursive_bindings(item))
    elif isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if (
            isinstance(path, str)
            and isinstance(digest, str)
            and re.fullmatch(r"[0-9a-f]{64}", digest)
        ):
            found.append({"path": path, "sha256": digest})
        for item in value.values():
            found.extend(recursive_bindings(item))
    return found


def semantic_lookalike_witness() -> dict[str, Any]:
    required = [SOURCE, CARGO, LOCK, EXECUTABLE]
    witness = {
        "schema": EXPECTED_STAGE_B_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": EXPECTED_SOURCE_AUDIT_RESULT,
        "evidence_class": EXPECTED_EVIDENCE_CLASS,
        "claim_boundary": "T1 source/custody clearance for the exact frozen Stage-B producer bytes only; no scientific manifest, input, or output was observed, no scientific replay was run, and no mathematical claim is promoted.",
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "subject": {
            "git_commit": SUBJECT_COMMIT,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
        },
        "unrecognized_decoy_container": [
            {"path": path, "sha256": EXPECTED[path]} for path in required
        ],
    }
    observed = recursive_bindings(witness)
    all_found = all(
        any(item["path"] == path and item["sha256"] == EXPECTED[path] for item in observed)
        for path in required
    )
    return {
        "description": "Exact envelope with no declared binding slots; required subjects occur only under an unknown decoy key.",
        "all_required_subjects_found_by_recursive_collector": all_found,
        "unknown_top_level_key": "unrecognized_decoy_container",
        "required_subjects": required,
        "witness": witness,
    }


def snapshot_subject(isolated_root: Path) -> tuple[dict[str, Any], bool]:
    bindings: dict[str, Any] = {}
    all_equal = True
    for path, expected in EXPECTED.items():
        committed = git_bytes(SUBJECT_COMMIT, path)
        working = (ROOT / path).read_bytes()
        isolated = isolated_root / path
        isolated.parent.mkdir(parents=True, exist_ok=True)
        if not isolated.exists():
            isolated.write_bytes(committed)
            if path == EXECUTABLE:
                isolated.chmod(isolated.stat().st_mode | stat.S_IXUSR)
        isolated_bytes = isolated.read_bytes()
        mode, blob = git_tree_entry(SUBJECT_COMMIT, path)
        actual = {
            "path": path,
            "sha256": sha256_bytes(committed),
            "working_sha256": sha256_bytes(working),
            "isolated_sha256": sha256_bytes(isolated_bytes),
            "git_blob": blob,
            "git_mode": mode,
            "size_bytes": len(committed),
            "commit_equals_working": committed == working,
            "commit_equals_isolated": committed == isolated_bytes,
            "matches_required_sha256": sha256_bytes(committed) == expected,
        }
        actual_ok = (
            actual["commit_equals_working"]
            and actual["commit_equals_isolated"]
            and actual["matches_required_sha256"]
        )
        all_equal = all_equal and actual_ok
        bindings[path] = actual
    return bindings, all_equal


def add(checks: list[dict[str, Any]], identifier: str, passed: bool, evidence: Any) -> None:
    checks.append({"id": identifier, "passed": bool(passed), "evidence": evidence})


def audit(output_path: Path) -> int:
    if ROOT != Path(run(["git", "rev-parse", "--show-toplevel"]).stdout.decode().strip()):
        raise RuntimeError("checker root resolution drift")
    if output_path.resolve().parent != REVIEW.resolve():
        raise RuntimeError("result path must be directly inside the G-0147 review directory")
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite {output_path}")

    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    source_bytes = git_bytes(SUBJECT_COMMIT, SOURCE)
    cargo_bytes = git_bytes(SUBJECT_COMMIT, CARGO)
    lock_bytes = git_bytes(SUBJECT_COMMIT, LOCK)
    executable_bytes = git_bytes(SUBJECT_COMMIT, EXECUTABLE)
    source = source_bytes.decode()
    cargo = cargo_bytes.decode()
    lock = lock_bytes.decode()
    stage_a_source = (ROOT / STAGE_A_SOURCE).read_text()
    frozen_stage_a_source = git_bytes(SUBJECT_COMMIT, STAGE_A_SOURCE).decode()
    kernel = git_bytes(SUBJECT_COMMIT, KERNEL_SOURCE).decode()
    historical = json.loads((ROOT / HISTORICAL_RECEIPT).read_text())

    with tempfile.TemporaryDirectory(prefix="g0147-frozen-custody-") as raw:
        isolated_root = Path(raw)
        bindings_start, custody_start_ok = snapshot_subject(isolated_root)
        isolated_executable = isolated_root / EXECUTABLE

        subject_self_test = command_evidence(
            [str(isolated_executable), "--self-test"], timeout=180
        )
        static_preflight = command_evidence(
            [str(isolated_executable), "--preflight-static", PANEL, CANDIDATE], timeout=600
        )
        option_probe = option_omission_probe()

        checks: list[dict[str, Any]] = []
        add(
            checks,
            "CUSTODY_EXACT_FOUR_FILE_BINDINGS",
            custody_start_ok,
            bindings_start,
        )
        add(
            checks,
            "HISTORICAL_G0142_EXACT_BLOCKERS_BOUND",
            historical.get("verdict") == "FAIL"
            and historical.get("failed_check_ids")
            == [
                "SCHEMA_ALL_INPUT_STRUCTS_DENY_UNKNOWN_FIELDS",
                "SCHEMA_SOURCE_AUDIT_GATE_EXACT",
            ],
            {
                "path": HISTORICAL_RECEIPT,
                "sha256": sha256_bytes((ROOT / HISTORICAL_RECEIPT).read_bytes()),
                "failed_check_ids": historical.get("failed_check_ids"),
            },
        )

        strict_types = ["Candidate", "StageAReceipt", "AccumulatedDirectionCheck", "StrictRecord"]
        non_strict = [name for name in strict_types if not denies_unknown_fields(source, name)]
        record_fields = struct_fields(kernel, "Record")
        strict_record_fields = struct_fields(source, "StrictRecord")
        adapter = function_body(source, "deserialize_records_strict")
        record_adapter_ok = (
            set(record_fields)
            == {"sequence", "signed_mass", "active_vertices", "negative_edges", "positive_edges"}
            and set(strict_record_fields)
            == {
                "stage",
                "orbit_index",
                "representative",
                "signed_class_sha256",
                "sequence",
                "signed_mass",
                "active_vertices",
                "negative_edges",
                "positive_edges",
                "in_disjoint",
                "in_shared_distinct",
            }
            and "Vec::<StrictRecord>::deserialize" in adapter
            and "map(Record::from)" in adapter
            and static_preflight["exit_code"] == 0
        )
        add(
            checks,
            "G0142_UNKNOWN_FIELD_BLOCKER_REPAIRED_WITH_REAL_RECORD_SCHEMA",
            not non_strict and record_adapter_ok,
            {
                "strict_types": strict_types,
                "non_strict_types": non_strict,
                "imported_record_fields": sorted(record_fields),
                "strict_real_record_fields": sorted(strict_record_fields),
                "real_static_preflight_accepted": static_preflight["exit_code"] == 0,
            },
        )

        envelope = function_body(source, "validate_source_audit_envelope")
        exact_gate_tokens = [
            "value_string(receipt, \"/schema\")? == expected_schema",
            "value_string(receipt, \"/result\")? == expected_result",
            "value_string(receipt, \"/verdict\")? == \"PASS\"",
            "value_string(receipt, \"/evidence_class\")? == SOURCE_AUDIT_EVIDENCE_CLASS",
            "value_string(receipt, \"/claim_boundary\")? == expected_boundary",
        ]
        exact_gate_ok = all(token in envelope for token in exact_gate_tokens)
        add(
            checks,
            "G0142_EXACT_SOURCE_AUDIT_SCHEMA_RESULT_BLOCKER_REPAIRED",
            exact_gate_ok,
            {"required_comparisons_present": exact_gate_ok, "tokens": exact_gate_tokens},
        )

        stage_a_output_fields = struct_fields(stage_a_source, "Output")
        stage_a_receipt_fields = struct_fields(source, "StageAReceipt")
        interface_sets_equal = set(stage_a_output_fields) == set(stage_a_receipt_fields)
        add(
            checks,
            "CURRENT_STAGE_A_TOP_LEVEL_INTERFACE_COMPATIBLE",
            stage_a_source == frozen_stage_a_source and interface_sets_equal,
            {
                "current_stage_a_source_sha256": sha256_bytes(stage_a_source.encode()),
                "frozen_stage_a_source_sha256": sha256_bytes(frozen_stage_a_source.encode()),
                "producer_field_count": len(stage_a_output_fields),
                "consumer_field_count": len(stage_a_receipt_fields),
                "producer_only": sorted(set(stage_a_output_fields) - set(stage_a_receipt_fields)),
                "consumer_only": sorted(set(stage_a_receipt_fields) - set(stage_a_output_fields)),
            },
        )

        option_missing_is_none = (
            option_probe["exit_code"] == 0
            and "omitted_is_none=true" in option_probe["stdout"]
        )
        stage_a_validation = function_body(source, "validate_stage_a_receipt")
        first_linear_type = stage_a_receipt_fields.get("first_nonzero_linear", "")
        omission_rejected = not (
            first_linear_type == "Option<ExactLinear>"
            and "receipt.first_nonzero_linear.is_none()" in stage_a_validation
            and option_missing_is_none
        )
        add(
            checks,
            "STAGE_A_RECEIPT_MISSING_NULL_FIELD_REJECTED",
            omission_rejected,
            {
                "field": "first_nonzero_linear",
                "consumer_type": first_linear_type,
                "validation": "is_none",
                "exact_version_serde_probe": option_probe,
                "impact": "missing and explicit null are conflated, so the produced top-level field is not mandatory",
            },
        )

        opaque_stage_a_fields = {
            name: stage_a_receipt_fields[name]
            for name in [
                "independent_finite_412_row_replay",
                "term_normal_forms",
                "coefficient_plus_one",
                "target_scale_plus_one",
                "target_coordinate_plus_one",
                "omitted_final_term",
                "omitted_first_term_direction",
                "census_controls",
                "selection_controls",
            ]
        }
        semantically_checked = {
            name: (f"receipt.{name}." in stage_a_validation)
            for name in opaque_stage_a_fields
        }
        stage_a_nested_controls_closed = all(
            type_name != "Value" and type_name != "Vec<Value>"
            for type_name in opaque_stage_a_fields.values()
        ) and all(semantically_checked.values())
        add(
            checks,
            "STAGE_A_MUTATION_CONTROL_SCHEMAS_COMPLETE_AND_VALIDATED",
            stage_a_nested_controls_closed,
            {
                "opaque_fields": opaque_stage_a_fields,
                "field_specific_semantic_checks": semantically_checked,
                "impact": "arbitrary objects/arrays satisfy mandatory mutation-control slots without their declared inner schema or result",
            },
        )

        lookalike = semantic_lookalike_witness()
        audit_validator = function_body(source, "validate_source_audit")
        source_audit_closed = (
            "strict_json_value(File::open(path)?)?" not in audit_validator
            and "collect_recursive_bindings(&receipt" not in audit_validator
            and not lookalike["all_required_subjects_found_by_recursive_collector"]
        )
        add(
            checks,
            "SOURCE_AUDIT_CLOSED_SCHEMA_AND_BINDING_PLACEMENT",
            source_audit_closed,
            {
                "generic_value_parser": "strict_json_value(File::open(path)?)?" in audit_validator,
                "recursive_anywhere_binding_search": "collect_recursive_bindings(&receipt" in audit_validator,
                "semantic_lookalike": lookalike,
                "impact": "an exact schema/result envelope can omit declared binding slots and satisfy them only through unknown decoy content",
            },
        )

        output_fields = struct_fields(source, "Output")
        required_output_fields = {
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
            "directions",
            "rows",
            "input_mutation_controls",
            "coefficient_plus_one_mutant",
            "inputs_rehashed_at_end",
        }
        output_complete = required_output_fields.issubset(output_fields) and not any(
            type_name == "Value" or type_name.startswith("Option<")
            for type_name in output_fields.values()
        )
        add(
            checks,
            "STAGE_B_TOP_LEVEL_OUTPUT_COMPLETE",
            output_complete,
            {
                "field_count": len(output_fields),
                "missing_required": sorted(required_output_fields - set(output_fields)),
                "optional_or_opaque_fields": {
                    key: value
                    for key, value in output_fields.items()
                    if value == "Value" or value.startswith("Option<")
                },
            },
        )

        manifest_validator = function_body(source, "validate_manifest")
        required_binding_paths = [
            "PREREGISTRATION_PATH",
            "PANEL_INPUT_PATH",
            "CANDIDATE_PATH",
            "ANCESTOR_STAGE_D_RESULT_PATH",
            "KERNEL_PATH",
            "G0139_AUDIT_PATH",
            "STAGE_A_SOURCE_PATH",
            "STAGE_A_ENGINE_PATH",
            "STAGE_A_CARGO_PATH",
            "STAGE_A_LOCK_PATH",
            "STAGE_A_EXECUTABLE_PATH",
            "STAGE_A_SOURCE_AUDIT_PATH",
            "STAGE_B_SOURCE_PATH",
            "STAGE_B_CARGO_PATH",
            "STAGE_B_LOCK_PATH",
            "STAGE_B_EXECUTABLE_PATH",
            "STAGE_B_SOURCE_AUDIT_PATH",
        ]
        mandatory_upstream = all(token in manifest_validator for token in required_binding_paths)
        add(
            checks,
            "MANIFEST_STAGE_A_CANDIDATE_G0139_BINDINGS_MANDATORY",
            mandatory_upstream,
            {"required_path_constants": required_binding_paths},
        )

        manifest_structs = ["Binding", "ManifestParameters", "PlannedOutput", "StudyManifest"]
        manifest_non_strict = [
            name for name in manifest_structs if not denies_unknown_fields(source, name)
        ]
        manifest_fields = struct_fields(source, "StudyManifest")
        expected_manifest_fields = {
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
        add(
            checks,
            "MANIFEST_SCHEMA_CLOSED_AND_COMPLETE",
            not manifest_non_strict
            and set(manifest_fields) == expected_manifest_fields
            and "manifest.planned_outputs == expected_outputs" in manifest_validator,
            {
                "strict_structs": manifest_structs,
                "non_strict_structs": manifest_non_strict,
                "missing_fields": sorted(expected_manifest_fields - set(manifest_fields)),
                "extra_fields": sorted(set(manifest_fields) - expected_manifest_fields),
            },
        )

        candidate_validator = function_body(source, "validate_candidate")
        static_loader = function_body(source, "load_static_inputs")
        candidate_exact = all(
            token in source
            for token in [
                'const CANDIDATE_SCHEMA: &str = "max11-g0135-full-family-master-result-v3";',
                'const CANDIDATE_RESULT: &str = "FULL_FAMILY_412ROW_EXACT_Q_MEMBER";',
                'const CANDIDATE_SHA256: &str = "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8";',
                'const CANDIDATE_GIT_COMMIT: &str = "2a567c1fcc8eed745235a50e638fc8c5e3ca83cc";',
            ]
        ) and all(
            token in candidate_validator
            for token in [
                "candidate.schema == CANDIDATE_SCHEMA",
                "candidate.result == CANDIDATE_RESULT",
                "candidate.records == RECORDS",
                "candidate.terms.len() == TERMS",
                "candidate.inputs_rehashed_at_end",
            ]
        ) and all(
            token in static_loader
            for token in [
                "validate_compiled_and_static(root)?;",
                "validate_candidate(&candidate)?;",
            ]
        )
        add(
            checks,
            "CANDIDATE_EXACT_IDENTITY_CUSTODY_AND_SCHEMA",
            candidate_exact and static_preflight["exit_code"] == 0,
            {
                "actual_candidate_opened_by_auditor": False,
                "accepted_only_via_allowed_static_preflight": static_preflight["exit_code"] == 0,
                "schema_result_hash_commit_constants_exact": candidate_exact,
            },
        )

        stage_a_named_bindings = all(
            token in stage_a_validation
            for token in [
                "receipt.g0140_manifest.path == MANIFEST_PATH",
                "receipt.g0140_manifest.sha256 == manifest.sha256",
                "receipt.g0135_manifest.path == candidate.manifest_path",
                "receipt.g0135_manifest.sha256 == candidate.manifest_sha256",
                "receipt.protocol.path == PREREGISTRATION_PATH",
                "receipt.producer_source.path == STAGE_A_SOURCE_PATH",
                "receipt.producer_engine.path == STAGE_A_ENGINE_PATH",
                "receipt.producer_executable.path == STAGE_A_EXECUTABLE_PATH",
                "receipt.g0139_result_audit.path == G0139_AUDIT_PATH",
                "receipt.ancestor_stage_d_result.path == ANCESTOR_STAGE_D_RESULT_PATH",
                "receipt.stage_c_member.path == CANDIDATE_PATH",
                "binding_matches(root, manifest, binding)?;",
            ]
        )
        add(
            checks,
            "STAGE_A_MANIFEST_PRODUCER_CANDIDATE_G0139_BINDINGS_EXACT",
            stage_a_named_bindings,
            "all named Stage-A provenance bindings are path-fixed, digest-admitted by the manifest, and rehashed on disk",
        )

        g0139_validator = function_body(source, "validate_g0139_gate")
        g0139_exact = all(
            token in g0139_validator
            for token in [
                'value_string(&receipt, "/schema")? == "max11-g0139-g0135-result-audit-v1"',
                'value_string(&receipt, "/verdict")? == "PASS"',
                'value_string(&receipt, "/result")? == "CONSISTENT_RESIDUAL_T1"',
                "item.path == ANCESTOR_STAGE_D_RESULT_PATH",
                "item.sha256 == ANCESTOR_STAGE_D_RESULT_SHA256",
                "item.path == CANDIDATE_PATH",
                "item.sha256 == CANDIDATE_SHA256",
            ]
        )
        add(
            checks,
            "G0139_EXACT_GATE_AND_G0135_INPUT_BINDINGS",
            g0139_exact,
            "exact schema/verdict/result plus exact ancestor and candidate path/SHA-256 pairs",
        )

        exact_dot = function_body(source, "exact_dot")
        bigint_ok = (
            "BigInt" in exact_dot
            and "coefficient * BigInt::from(row[*sequence])" in exact_dot
            and " as " not in exact_dot
            and "parse_bigint(&term.coefficient)?" in source
        )
        add(
            checks,
            "BIGINT_DOT_WITHOUT_NARROWING",
            bigint_ok,
            {"exact_dot_body": exact_dot},
        )

        census_ok = all(
            token in source
            for token in [
                "const K: usize = 128;",
                "const RECORDS: usize = 163_740;",
                "const HINGE_ENTRIES: usize = K * RECORDS;",
                "HINGE_ENTRIES, 20_958_720",
                "direction_major.iter().map(Vec::len).sum::<usize>() == HINGE_ENTRIES",
            ]
        )
        add(
            checks,
            "EXACT_128_BY_163740_CENSUS",
            census_ok and 128 * 163_740 == 20_958_720,
            {"directions": 128, "records": 163_740, "cells": 20_958_720},
        )

        deterministic_ok = all(
            token in source
            for token in [
                "window[0].direction < window[1].direction",
                "sequence == expected",
                ".par_iter()",
                ".collect::<Result<Vec<_>>>()?",
                "transpose_record_major(record_major, K)?",
                "row.index == index",
                "row.direction == directions[index]",
            ]
        )
        add(
            checks,
            "DETERMINISTIC_DIRECTION_AND_ROW_ORDER",
            deterministic_ok,
            "strict signed-lex Pool128, sequence 0..163739, indexed Rayon collect, explicit transpose, indexed output checks",
        )

        embedded_subject_bytes = all(
            item in executable_bytes for item in [source_bytes, cargo_bytes, lock_bytes]
        )
        compiled_ok = (
            embedded_subject_bytes
            and subject_self_test["exit_code"] == 0
            and "G-0140 Stage-B Pool128 self-test PASS" in subject_self_test["stdout"]
            and static_preflight["exit_code"] == 0
            and "163740 records; 135 candidate terms" in static_preflight["stdout"]
            and "COMPILED_SOURCE" in source
            and "COMPILED_MANIFEST" in source
            and "COMPILED_LOCK" in source
        )
        add(
            checks,
            "COMPILED_BYTE_SOURCE_CARGO_CUSTODY",
            compiled_ok,
            {
                "source_cargo_lock_each_embedded_verbatim_in_frozen_executable": embedded_subject_bytes,
                "subject_self_test": subject_self_test,
                "static_preflight": static_preflight,
            },
        )

        publish = function_body(source, "publish_exclusive")
        overwrite_ok = all(
            token in publish
            for token in [
                "ensure!(!path.exists(), \"refusing to overwrite output\")",
                ".create_new(true)",
                "std::fs::hard_link(&temporary, path)",
                "directory.sync_all()",
            ]
        )
        add(
            checks,
            "ATOMIC_OUTPUT_OVERWRITE_REFUSAL",
            overwrite_ok,
            "create_new temporary plus hard-link publication and directory fsync",
        )

        run_body = function_body(source, "run")
        end_rehash_ok = (
            "let custody_end = custody_snapshot(&root, &inputs.manifest, &stage_a_sha_end)?;"
            in run_body
            and "inputs.custody == custody_end" in run_body
            and "inputs_rehashed_at_end: true" in run_body
        )
        add(
            checks,
            "INPUTS_REHASHED_AFTER_PRICING_BEFORE_PUBLICATION",
            end_rehash_ok,
            "manifest bindings plus manifest and Stage-A receipt rehashed and compared after pricing",
        )

        main_body = function_body(source, "main")
        static_body = function_body(source, "static_preflight")
        runtime_firewall = all(
            token in main_body
            for token in [
                'args.len() == 2 && args[1] == "--self-test"',
                'args.len() == 4 && args[1] == "--preflight-static"',
                'args.len() == 6 && args[1] == "--preflight"',
            ]
        ) and all(
            token in static_body
            for token in [
                "load_static_inputs(&root, &input_path, &candidate_path)?",
                "future manifest/Stage-A/G-0142 receipts not consumed",
            ]
        ) and "load_and_validate_inputs" not in static_body
        add(
            checks,
            "AUDIT_RUNTIME_MODE_FIREWALL",
            runtime_firewall
            and subject_self_test["exit_code"] == 0
            and static_preflight["exit_code"] == 0,
            {
                "executed_modes": ["--self-test", "--preflight-static"],
                "static_mode_does_not_call_full_input_loader": "load_and_validate_inputs" not in static_body,
                "scientific_mode_executed": False,
            },
        )

        bindings_end, custody_end_ok = snapshot_subject(isolated_root)
        end_equal = bindings_start == bindings_end
        add(
            checks,
            "AUDIT_END_REHASH_FOUR_FILE_CUSTODY",
            custody_end_ok and end_equal,
            {"initial_equals_final": end_equal, "final_bindings": bindings_end},
        )

        mutated = bytearray(source_bytes)
        mutated[len(mutated) // 2] ^= 1
        short_census_mutant = source.replace(
            "const HINGE_ENTRIES: usize = K * RECORDS;",
            "const HINGE_ENTRIES: usize = K;",
            1,
        )
        narrowing_mutant = source.replace(
            "coefficient * BigInt::from(row[*sequence])",
            "coefficient * BigInt::from(row[*sequence] as i32)",
            1,
        )
        loose_candidate = source.replace(
            "#[serde(deny_unknown_fields)]\nstruct Candidate",
            "struct Candidate",
            1,
        )
        result_lookalike = source.replace(
            "value_string(receipt, \"/result\")? == expected_result",
            "value_string(receipt, \"/result\")?.contains(\"PASS\")",
            1,
        )
        hostile_controls = [
            {
                "id": "HOSTILE_ONE_BYTE_CUSTODY_MUTANT_REJECTED",
                "passed": sha256_bytes(bytes(mutated)) != EXPECTED[SOURCE],
            },
            {
                "id": "HOSTILE_REMOVED_DENY_UNKNOWN_REJECTED",
                "passed": not denies_unknown_fields(loose_candidate, "Candidate"),
            },
            {
                "id": "HOSTILE_RESULT_SUBSTRING_LOOKALIKE_REJECTED_BY_CHECKER",
                "passed": not all(
                    token in function_body(result_lookalike, "validate_source_audit_envelope")
                    for token in exact_gate_tokens
                ),
            },
            {
                "id": "HOSTILE_SHORT_CENSUS_REJECTED_BY_CHECKER",
                "passed": "const HINGE_ENTRIES: usize = K * RECORDS;" not in short_census_mutant,
            },
            {
                "id": "HOSTILE_I32_NARROWING_REJECTED_BY_CHECKER",
                "passed": " as " in function_body(narrowing_mutant, "exact_dot"),
            },
            {
                "id": "HOSTILE_MISSING_OPTION_WITNESS_CONFIRMED",
                "passed": option_missing_is_none,
            },
            {
                "id": "HOSTILE_RECURSIVE_DECOY_BINDING_WITNESS_CONFIRMED",
                "passed": lookalike["all_required_subjects_found_by_recursive_collector"],
            },
        ]

    failures = [item for item in checks if not item["passed"]]
    hostile_failures = [item for item in hostile_controls if not item["passed"]]
    verdict = "PASS" if not failures and not hostile_failures else "FAIL"
    result = {
        "schema": "max11-g0147-g0140-stage-b-final-source-check-results-v1",
        "verdict": verdict,
        "started_utc": started_utc,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "subject_commit": SUBJECT_COMMIT,
        "outcome_blind": True,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "allowed_runtime_modes": ["subject --self-test", "subject --preflight-static PANEL CANDIDATE"],
        "checks": checks,
        "hostile_controls": hostile_controls,
        "failed_check_ids": [item["id"] for item in failures],
        "failed_hostile_control_ids": [item["id"] for item in hostile_failures],
        "claim_boundary": "T1 source/custody inspection only; static preflight treated its two frozen inputs as opaque and no scientific manifest, Stage-A result, Stage-B output, or science mode was opened or run.",
    }
    encoded = (json.dumps(result, indent=2, sort_keys=True) + "\n").encode()
    descriptor = os.open(output_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    print(
        json.dumps(
            {
                "verdict": verdict,
                "failed_check_ids": result["failed_check_ids"],
                "failed_hostile_control_ids": result["failed_hostile_control_ids"],
                "output": str(output_path.resolve().relative_to(ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0 if verdict == "PASS" else 1


def self_test() -> int:
    fixture = "#[derive(Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct X { value: u8 }"
    assert denies_unknown_fields(fixture, "X")
    assert struct_fields(fixture, "X") == {"value": "u8"}
    function_fixture = "fn x() { if true { let _ = 1; } }"
    assert function_body(function_fixture, "x") == "{ if true { let _ = 1; } }"
    witness = semantic_lookalike_witness()
    assert witness["all_required_subjects_found_by_recursive_collector"]
    assert sha256_bytes(b"a") != sha256_bytes(b"b")
    print("G-0147 independent checker self-test PASS")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--static-audit", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        if args.output is not None:
            parser.error("--output is not valid with --self-test")
        return self_test()
    if args.output is None:
        parser.error("--static-audit requires --output")
    return audit(args.output)


if __name__ == "__main__":
    raise SystemExit(main())
