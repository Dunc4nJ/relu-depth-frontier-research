#!/usr/bin/env python3
"""Independent source/custody and hostile-contract checks for G-0163.

This script must be run against the sanitized sparse audit worktree.  It reads
only source/build inputs and source-audit artifacts; it refuses to proceed if
the G-0140 manifest or any Stage-A--E scientific output is present.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any, Callable


SUBJECT_COMMIT = "4944a58e0816fcf8e62dbdd134448daffce10738"
STAGE_D_COMMIT = "19107c5eed2cad00d48eff3dd9bea0c015ecce89"
G0162_PREREG_COMMIT = "a264e1c7ae1e7df7ac13b38b85d2dad7abde93e0"
G0162_RECEIPT_COMMIT = "e93afa3abb8128f955792f95150e889433100f3b"
G0163_PREREG_COMMIT = "24fc630c083649772df3933172e2263199b46f6d"

MAIN = "artifacts/math/G-0140/stage_e_global_replay/src/main.rs"
ENGINE = "artifacts/math/G-0140/stage_e_global_replay/src/engine.rs"
CARGO = "artifacts/math/G-0140/stage_e_global_replay/Cargo.toml"
LOCK = "artifacts/math/G-0140/stage_e_global_replay/Cargo.lock"
BINARY = "artifacts/math/G-0140/stage_e_global_replay/target/release/g0140-stage-e-global-replay"
STAGE_A_ENGINE = "artifacts/math/G-0140/stage_a_pool/src/engine.rs"
STAGE_D = "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py"
G0162_PREREG = "artifacts/reviews/G-0162-g0140-stage-d-master-final4-source/PREREGISTRATION.md"
G0162_RECEIPT = "artifacts/reviews/G-0162-g0140-stage-d-master-final4-source/SOURCE_AUDIT_RECEIPT.json"
G0163_PREREG = "artifacts/reviews/G-0163-g0140-stage-e-final4-source/PREREGISTRATION.md"
G0163_RECEIPT = "artifacts/reviews/G-0163-g0140-stage-e-final4-source/SOURCE_AUDIT_RECEIPT.json"

PINS = {
    MAIN: "be4852b63ff2118182cdd07ead85708f0b4ef0785445f0f873ebd4367c9e866a",
    ENGINE: "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c",
    CARGO: "a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9",
    LOCK: "eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0",
    BINARY: "99ba4017c42ab08043b9aacaef554192ce50beff37a41df07ba8d4f7e4ba7179",
    STAGE_D: "1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581",
    G0162_RECEIPT: "2e09106c38cdb366b7cf2ef62aa43b61c28a41eeb42587ec83ea808d39fca2d0",
    G0162_PREREG: "83a04b4ae21845b4450a31a2b17b7ac2156f3cc9ccfebd3d46b0d4bc4c4d42f8",
    G0163_PREREG: "6a4224e500676455566fb4c5a295fc5cb8ef9860027fa08dc84ab7236e3a5622",
}

FORBIDDEN = [
    "artifacts/math/G-0140/pool128_manifest_v1.json",
    "artifacts/math/G-0140/pool128_global_replay_v1.json",
    "artifacts/math/G-0140/pool128_coordinate_prices_v1.json",
    "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json",
    "artifacts/math/G-0140/rank_aware_master_result_v1.json",
    "artifacts/math/G-0140/new_member_global_replay_v1.json",
]

STAGE_D_CHECKS = {
    "exact_named_binding_contract",
    "displaced_recursive_lookalikes_rejected",
    "correct_decoy_with_missing_named_binding_rejected",
    "unknown_envelope_fields_rejected",
    "audit_git_commit_rejected",
    "duplicate_json_keys_rejected",
    "trailing_json_data_rejected",
    "imported_exact_core_binding_verified",
    "future_input_gate_verified",
    "stage_c_snapshot_digest_contract_verified",
    "exact_column_generation_protocol_verified",
    "member_and_separator_fixtures_verified",
    "committed_blob_custody_verified",
    "producer_self_test_passed",
    "producer_static_preflight_passed",
    "prohibited_scientific_modes_not_run",
}

STAGE_E_CHECKS = {
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
    "compiled_source_manifest_lock_match_working_bytes",
    "engine_byte_identity_with_stage_a_verified",
    "stage_d_source_audit_gate_verified",
    "scientific_output_commit_chain_gate_verified",
    "scientific_outputs_excluded_from_manifest_bindings",
    "dynamic_stage_d_member_contract_verified",
    "global_zero_and_residual_branches_verified",
    "complete_label_census_and_end_rehash_verified",
    "overwrite_refusal_verified",
    "prohibited_scientific_modes_not_run",
}

TOP_KEYS = {
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
FLAGS = {
    "scientific_manifest_observed",
    "scientific_input_observed",
    "scientific_output_observed",
    "scientific_replay_run",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_loads(raw: str) -> dict[str, Any]:
    value = json.loads(raw, object_pairs_hook=no_duplicate_pairs)
    assert type(value) is dict
    return value


def git(root: Path, *args: str) -> bytes:
    return subprocess.check_output(["git", "-C", str(root), *args])


def git_ok(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True)


def last_commit(root: Path, path: str) -> str:
    return git(root, "log", "-1", "--format=%H", "--", path).decode().strip()


def rust_const(source: str, name: str) -> str:
    match = re.search(
        rf'const\s+{re.escape(name)}\s*:\s*&str\s*=\s*"((?:[^"\\]|\\.)*)"\s*;',
        source,
        re.DOTALL,
    )
    assert match, f"missing Rust constant {name}"
    return json.loads(f'"{match.group(1)}"')


def struct_bool_fields(source: str, name: str) -> set[str]:
    match = re.search(rf"struct\s+{re.escape(name)}\s*\{{(.*?)\n\}}", source, re.DOTALL)
    assert match, f"missing Rust struct {name}"
    return set(re.findall(r"(?m)^\s*(\w+)\s*:\s*bool\s*,\s*$", match.group(1)))


def function_source(source: str, name: str) -> str:
    start = source.index(f"fn {name}")
    next_fn = source.find("\nfn ", start + 3)
    return source[start:] if next_fn < 0 else source[start:next_fn]


def assert_exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    assert set(value) == expected, f"{label} key drift: {set(value) ^ expected}"


def assert_bool(value: Any, label: str) -> None:
    assert type(value) is bool, f"{label} is not a JSON boolean"


def validate_common(
    receipt: dict[str, Any],
    *,
    schema: str,
    claim: str,
    no_claim: str,
    checks: set[str],
) -> None:
    assert_exact_keys(receipt, TOP_KEYS, "receipt")
    assert receipt["schema"] == schema
    assert receipt["verdict"] == "PASS"
    assert receipt["result"] == "SOURCE_CUSTODY_AUDIT_PASS_T1"
    assert receipt["evidence_class"] == "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
    assert receipt["claim_boundary"] == claim
    assert receipt["no_claim"] == no_claim
    assert_exact_keys(
        receipt["reviewer"],
        {"agent_name", "program", "model", "same_model_lineage", "fresh_context"},
        "reviewer",
    )
    reviewer = receipt["reviewer"]
    assert type(reviewer["agent_name"]) is str and reviewer["agent_name"]
    assert reviewer["program"] == "codex"
    assert type(reviewer["model"]) is str and reviewer["model"]
    assert reviewer["same_model_lineage"] is True
    assert reviewer["fresh_context"] is True
    assert_exact_keys(
        receipt["preregistration"],
        {
            "path",
            "sha256",
            "git_commit",
            "committed_and_pushed_before_subject_source_inspection",
            "committed_and_pushed_before_runtime_checks",
        },
        "preregistration",
    )
    prereg = receipt["preregistration"]
    assert re.fullmatch(r"[0-9a-f]{64}", prereg["sha256"])
    assert re.fullmatch(r"[0-9a-f]{40}", prereg["git_commit"])
    assert prereg["committed_and_pushed_before_subject_source_inspection"] is True
    assert prereg["committed_and_pushed_before_runtime_checks"] is True
    assert_exact_keys(receipt["required_checks"], checks, "required_checks")
    for key, value in receipt["required_checks"].items():
        assert_bool(value, f"required_checks.{key}")
        assert value
    for flag in FLAGS:
        assert_bool(receipt[flag], flag)
        assert receipt[flag] is False


def validate_stage_d(receipt: dict[str, Any], source: str) -> None:
    validate_common(
        receipt,
        schema=rust_const(source, "STAGE_D_SOURCE_AUDIT_SCHEMA_G0140"),
        claim=rust_const(source, "STAGE_D_SOURCE_AUDIT_CLAIM_G0140"),
        no_claim=rust_const(source, "STAGE_D_SOURCE_AUDIT_NO_CLAIM_G0140"),
        checks=STAGE_D_CHECKS,
    )
    assert receipt["preregistration"]["path"] == G0162_PREREG
    assert receipt["preregistration"]["sha256"] == PINS[G0162_PREREG]
    assert receipt["preregistration"]["git_commit"] == G0162_PREREG_COMMIT
    assert_exact_keys(receipt["subject"], {"git_commit", "commit_object_and_working_bytes_equal_for_all_bindings", "bindings"}, "Stage-D subject")
    assert receipt["subject"]["git_commit"] == STAGE_D_COMMIT
    assert receipt["subject"]["commit_object_and_working_bytes_equal_for_all_bindings"] is True
    bindings = receipt["subject"]["bindings"]
    assert_exact_keys(bindings, {"master_source"}, "Stage-D bindings")
    assert bindings["master_source"] == {"path": STAGE_D, "sha256": PINS[STAGE_D]}


def validate_stage_e(receipt: dict[str, Any], source: str) -> None:
    validate_common(
        receipt,
        schema=rust_const(source, "STAGE_E_SOURCE_AUDIT_SCHEMA"),
        claim=rust_const(source, "STAGE_E_SOURCE_AUDIT_CLAIM_BOUNDARY"),
        no_claim=rust_const(source, "STAGE_E_SOURCE_AUDIT_NO_CLAIM"),
        checks=STAGE_E_CHECKS,
    )
    assert receipt["reviewer"]["agent_name"] == "BlueMarsh"
    assert receipt["preregistration"] == {
        "path": G0163_PREREG,
        "sha256": PINS[G0163_PREREG],
        "git_commit": G0163_PREREG_COMMIT,
        "committed_and_pushed_before_subject_source_inspection": True,
        "committed_and_pushed_before_runtime_checks": True,
    }
    assert_exact_keys(receipt["subject"], {"git_commit", "commit_object_and_working_bytes_equal_for_all_bindings", "bindings"}, "Stage-E subject")
    assert receipt["subject"]["git_commit"] == SUBJECT_COMMIT
    assert receipt["subject"]["commit_object_and_working_bytes_equal_for_all_bindings"] is True
    expected_bindings = {
        "main_source": {"path": MAIN, "sha256": PINS[MAIN]},
        "engine_source": {"path": ENGINE, "sha256": PINS[ENGINE]},
        "cargo_manifest": {"path": CARGO, "sha256": PINS[CARGO]},
        "cargo_lock": {"path": LOCK, "sha256": PINS[LOCK]},
        "release_executable": {"path": BINARY, "sha256": PINS[BINARY]},
    }
    assert receipt["subject"]["bindings"] == expected_bindings
    assert len({item["path"] for item in expected_bindings.values()}) == 5


def expect_rejected(validator: Callable[[dict[str, Any]], None], mutant: dict[str, Any]) -> None:
    try:
        validator(mutant)
    except (AssertionError, KeyError, TypeError):
        return
    raise AssertionError("hostile receipt mutant escaped")


def hostile_count(
    baseline: dict[str, Any],
    checks: set[str],
    validator: Callable[[dict[str, Any]], None],
) -> int:
    count = 0
    for key in checks:
        for action in ("false", "missing", "numeric"):
            mutant = copy.deepcopy(baseline)
            if action == "false":
                mutant["required_checks"][key] = False
            elif action == "missing":
                del mutant["required_checks"][key]
            else:
                mutant["required_checks"][key] = 1
            expect_rejected(validator, mutant)
            count += 1
    mutants: list[dict[str, Any]] = []
    for key, value in (
        ("schema", "lookalike"),
        ("verdict", "FAIL"),
        ("result", "LOOKALIKE_PASS"),
        ("evidence_class", "T2_INDEPENDENT_REPLAY"),
        ("claim_boundary", ""),
        ("no_claim", ""),
    ):
        mutant = copy.deepcopy(baseline)
        mutant[key] = value
        mutants.append(mutant)
    for flag in FLAGS:
        mutant = copy.deepcopy(baseline)
        mutant[flag] = True
        mutants.append(mutant)
        mutant = copy.deepcopy(baseline)
        mutant[flag] = 0
        mutants.append(mutant)
    mutant = copy.deepcopy(baseline)
    mutant["unknown_extension"] = True
    mutants.append(mutant)
    mutant = copy.deepcopy(baseline)
    mutant["required_checks"]["unknown_check"] = True
    mutants.append(mutant)
    mutant = copy.deepcopy(baseline)
    mutant["audit_git_commit"] = "0" * 40
    mutants.append(mutant)
    for mutant in mutants:
        expect_rejected(validator, mutant)
        count += 1
    return count


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--receipt", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()

    for path in FORBIDDEN:
        assert not (root / path).exists(), f"prohibited scientific path present: {path}"
    assert not (root / G0163_RECEIPT).exists(), "prospective receipt must be absent from static audit tree"

    for path, expected in PINS.items():
        if path == G0163_PREREG or (root / path).exists():
            assert sha256((root / path).read_bytes()) == expected, f"working hash drift: {path}"
    for path in (MAIN, ENGINE, CARGO, LOCK, BINARY):
        assert sha256(git(root, "show", f"{SUBJECT_COMMIT}:{path}")) == PINS[path]
    assert sha256(git(root, "show", f"{STAGE_D_COMMIT}:{STAGE_D}")) == PINS[STAGE_D]
    assert sha256(git(root, "show", f"{G0162_RECEIPT_COMMIT}:{G0162_RECEIPT}")) == PINS[G0162_RECEIPT]
    assert last_commit(root, MAIN) == SUBJECT_COMMIT
    assert last_commit(root, STAGE_D) == STAGE_D_COMMIT
    assert last_commit(root, G0162_RECEIPT) == G0162_RECEIPT_COMMIT
    for ancestor, descendant in (
        (STAGE_D_COMMIT, G0162_PREREG_COMMIT),
        (G0162_PREREG_COMMIT, SUBJECT_COMMIT),
        (SUBJECT_COMMIT, G0162_RECEIPT_COMMIT),
        (G0162_RECEIPT_COMMIT, G0163_PREREG_COMMIT),
        (G0163_PREREG_COMMIT, "origin/master"),
    ):
        git_ok(root, "merge-base", "--is-ancestor", ancestor, descendant)

    assert (root / ENGINE).read_bytes() == (root / STAGE_A_ENGINE).read_bytes()
    source = (root / MAIN).read_text(encoding="utf-8")
    assert rust_const(source, "STAGE_E_SOURCE_AUDIT_SCHEMA") == "max11-g0163-g0140-stage-e-final4-source-audit-v1"
    assert struct_bool_fields(source, "StageDSourceAuditChecks") == STAGE_D_CHECKS
    assert struct_bool_fields(source, "StageESourceAuditChecks") == STAGE_E_CHECKS
    for name, checks in (
        ("validate_stage_d_source_audit_semantics", STAGE_D_CHECKS),
        ("validate_stage_e_source_audit_semantics", STAGE_E_CHECKS),
    ):
        body = function_source(source, name)
        for check in checks:
            assert f"checks.{check}" in body, f"{name} omits {check}"

    array = re.search(r"const G0140_SCIENTIFIC_OUTPUT_PATHS: \[&str; 5\] = \[(.*?)\];", source, re.DOTALL)
    assert array
    assert re.findall(r"\b([A-Z][A-Z0-9_]+),", array.group(1)) == [
        "G0140_STAGE_A_RESULT_PATH",
        "STAGE_B_OUTPUT_PATH",
        "STAGE_C_OUTPUT_PATH",
        "STAGE_D_OUTPUT_PATH",
        "STAGE_E_OUTPUT_PATH",
    ]
    boundary = function_source(source, "validate_protocol_manifest_output_boundary")
    assert "for output_path in G0140_SCIENTIFIC_OUTPUT_PATHS" in boundary
    assert "!protocol.bindings_by_path.contains_key(output_path)" in boundary
    manifest_gate = function_source(source, "validate_g0140_manifest")
    assert "for (label, binding) in &manifest.bindings" in manifest_gate
    assert "for binding in &manifest.transitive_inputs" in manifest_gate
    assert "validate_protocol_manifest_output_boundary(&snapshot)?" in manifest_gate
    exclusion_hostiles = 0
    output_paths = FORBIDDEN[1:]
    for output_path in output_paths:
        for direct, transitive in (({output_path}, set()), (set(), {output_path})):
            merged = direct | transitive
            assert any(path in merged for path in output_paths)
            exclusion_hostiles += 1
    assert exclusion_hostiles == 10

    g0162_raw = (root / G0162_RECEIPT).read_text(encoding="utf-8")
    g0162 = strict_loads(g0162_raw)
    validate_stage_d(g0162, source)
    g0162_hostiles = hostile_count(g0162, STAGE_D_CHECKS, lambda value: validate_stage_d(value, source))
    for special in (False, 1):
        mutant = copy.deepcopy(g0162)
        mutant["required_checks"]["stage_c_snapshot_digest_contract_verified"] = special
        expect_rejected(lambda value: validate_stage_d(value, source), mutant)
        g0162_hostiles += 1
    duplicate = g0162_raw.replace('"schema":', '"schema":"duplicate","schema":', 1)
    for raw in (duplicate, g0162_raw + "\ntrue"):
        try:
            strict_loads(raw)
        except (ValueError, json.JSONDecodeError):
            g0162_hostiles += 1
        else:
            raise AssertionError("strict JSON hostile escaped")

    g0163_raw = args.receipt.read_text(encoding="utf-8")
    g0163 = strict_loads(g0163_raw)
    validate_stage_e(g0163, source)
    g0163_hostiles = hostile_count(g0163, STAGE_E_CHECKS, lambda value: validate_stage_e(value, source))
    bindings = list(g0163["subject"]["bindings"])
    for binding_name in bindings:
        mutant = copy.deepcopy(g0163)
        mutant["subject"]["bindings"][binding_name]["sha256"] = "0" * 64
        expect_rejected(lambda value: validate_stage_e(value, source), mutant)
        g0163_hostiles += 1
    mutant = copy.deepcopy(g0163)
    mutant["subject"]["bindings"]["engine_source"]["path"] = MAIN
    expect_rejected(lambda value: validate_stage_e(value, source), mutant)
    g0163_hostiles += 1
    duplicate = g0163_raw.replace('"schema":', '"schema":"duplicate","schema":', 1)
    for raw in (duplicate, g0163_raw + "\ntrue"):
        try:
            strict_loads(raw)
        except (ValueError, json.JSONDecodeError):
            g0163_hostiles += 1
        else:
            raise AssertionError("strict Stage-E JSON hostile escaped")

    print(
        json.dumps(
            {
                "status": "PASS",
                "g0162_typed_negative_controls": g0162_hostiles,
                "g0163_typed_negative_controls": g0163_hostiles,
                "direct_and_transitive_output_exclusion_controls": exclusion_hostiles,
                "stage_d_required_checks": len(STAGE_D_CHECKS),
                "stage_e_required_checks": len(STAGE_E_CHECKS),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
