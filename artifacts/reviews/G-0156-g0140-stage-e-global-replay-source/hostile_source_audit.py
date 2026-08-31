#!/usr/bin/env python3
"""Focused source/custody-only hostile checks for frozen G-0140 Stage E.

This harness reads only the five bound Stage-E subject files, the G-0156
preregistration/receipt, Git objects for those five paths, and an explicitly
supplied clean-rebuild executable. It never opens a scientific manifest,
input, or output and never invokes the producer.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


SUBJECT_COMMIT = "af608ad38dde2a9b4d25aaefca8bd8407c9a0699"
PREREG_COMMIT = "15a9d2cca19532593b76d91b62b9da92fed58720"
SCHEMA = "max11-g0156-g0140-stage-e-global-replay-source-audit-v1"
RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"

BINDINGS = {
    "cargo_manifest": (
        "artifacts/math/G-0140/stage_e_global_replay/Cargo.toml",
        "a701d142aeb88cae15d30997dcc3039b5fee105cb3c26621fec9ddcca552f5c9",
    ),
    "cargo_lock": (
        "artifacts/math/G-0140/stage_e_global_replay/Cargo.lock",
        "eaaa98ae381bed0f1b48f27e5ca7c3841c2e6e1b8fa6b07e09cff11d172ef2d0",
    ),
    "main_source": (
        "artifacts/math/G-0140/stage_e_global_replay/src/main.rs",
        "e2a7121aab0edcea463031ba09ab75bbd9441a443bcf819aa5d653d1db17e2a6",
    ),
    "engine_source": (
        "artifacts/math/G-0140/stage_e_global_replay/src/engine.rs",
        "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c",
    ),
    "release_executable": (
        "artifacts/math/G-0140/stage_e_global_replay/target/release/g0140-stage-e-global-replay",
        "a2151ab92ad732fecaa48d41ebfa8e574db93720393b8afe72c29ca170f1aeb8",
    ),
}

REQUIRED_CHECKS = {
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
    "g0155_stage_d_source_audit_gate_verified",
    "scientific_output_commit_chain_gate_verified",
    "dynamic_stage_d_member_contract_verified",
    "global_zero_and_residual_branches_verified",
    "complete_label_census_and_end_rehash_verified",
    "overwrite_refusal_verified",
    "prohibited_scientific_modes_not_run",
}

TOP_KEYS = {
    "schema", "verdict", "result", "evidence_class", "claim_boundary",
    "reviewer", "preregistration", "subject", "required_checks",
    "scientific_manifest_observed", "scientific_input_observed",
    "scientific_output_observed", "scientific_replay_run", "no_claim",
}


class Rejected(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise Rejected(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def strict_loads(raw: str) -> Any:
    try:
        return json.loads(raw, object_pairs_hook=reject_duplicate_pairs)
    except (json.JSONDecodeError, Rejected) as error:
        raise Rejected(str(error)) from error


def exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != expected:
        raise Rejected(f"{label} key-set drift")
    return value


def exact_bool(value: Any, label: str) -> bool:
    if type(value) is not bool:  # Deliberately reject JSON numeric 1/0.
        raise Rejected(f"{label} is not a JSON boolean")
    return value


def validate_receipt(value: Any) -> None:
    receipt = exact_keys(value, TOP_KEYS, "receipt")
    if (
        receipt["schema"] != SCHEMA
        or receipt["verdict"] != "PASS"
        or receipt["result"] != RESULT
        or receipt["evidence_class"] != EVIDENCE_CLASS
    ):
        raise Rejected("typed identity drift")

    reviewer = exact_keys(
        receipt["reviewer"],
        {"agent_name", "program", "model", "same_model_lineage", "fresh_context"},
        "reviewer",
    )
    if not reviewer["agent_name"] or reviewer["program"] != "codex" or not reviewer["model"]:
        raise Rejected("reviewer identity drift")
    if not exact_bool(reviewer["same_model_lineage"], "same_model_lineage"):
        raise Rejected("wrong lineage")
    if not exact_bool(reviewer["fresh_context"], "fresh_context"):
        raise Rejected("not fresh")

    prereg = exact_keys(
        receipt["preregistration"],
        {
            "path", "sha256", "git_commit",
            "committed_and_pushed_before_subject_source_inspection",
            "committed_and_pushed_before_runtime_checks",
        },
        "preregistration",
    )
    if prereg["git_commit"] != PREREG_COMMIT:
        raise Rejected("preregistration commit drift")
    for key in (
        "committed_and_pushed_before_subject_source_inspection",
        "committed_and_pushed_before_runtime_checks",
    ):
        if not exact_bool(prereg[key], key):
            raise Rejected(f"false preregistration assertion: {key}")

    subject = exact_keys(
        receipt["subject"],
        {"git_commit", "commit_object_and_working_bytes_equal_for_all_bindings", "bindings"},
        "subject",
    )
    if subject["git_commit"] != SUBJECT_COMMIT:
        raise Rejected("subject commit drift")
    if not exact_bool(
        subject["commit_object_and_working_bytes_equal_for_all_bindings"],
        "committed subject bytes",
    ):
        raise Rejected("uncommitted subject")
    bindings = exact_keys(subject["bindings"], set(BINDINGS), "named bindings")
    observed_paths: set[str] = set()
    for name, (path, digest) in BINDINGS.items():
        binding = exact_keys(bindings[name], {"path", "sha256"}, name)
        if binding != {"path": path, "sha256": digest} or path in observed_paths:
            raise Rejected(f"named/duplicate binding drift: {name}")
        observed_paths.add(path)

    checks = exact_keys(receipt["required_checks"], REQUIRED_CHECKS, "required checks")
    for name, value in checks.items():
        if not exact_bool(value, name):
            raise Rejected(f"required check is not true: {name}")
    for name in (
        "scientific_manifest_observed", "scientific_input_observed",
        "scientific_output_observed", "scientific_replay_run",
    ):
        if exact_bool(receipt[name], name):
            raise Rejected(f"prohibited boundary crossed: {name}")


def expect_rejected(label: str, value: Any) -> None:
    try:
        validate_receipt(value)
    except Rejected:
        return
    raise AssertionError(f"mutant escaped: {label}")


def git_output(root: Path, *args: str) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, stdout=subprocess.PIPE, stderr=None
    ).stdout


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--rebuilt-binary", type=Path, required=True)
    args = parser.parse_args()
    root = args.repo_root.resolve()
    audit = root / "artifacts/reviews/G-0156-g0140-stage-e-global-replay-source"

    raw = (audit / "SOURCE_AUDIT_RECEIPT.json").read_text()
    receipt = strict_loads(raw)
    validate_receipt(receipt)

    for _, (path, digest) in BINDINGS.items():
        working = (root / path).read_bytes()
        committed = git_output(root, "show", f"{SUBJECT_COMMIT}:{path}")
        last_commit = git_output(root, "log", "-1", "--format=%H", "--", path).decode().strip()
        assert sha256(working) == digest == sha256(committed)
        assert last_commit == SUBJECT_COMMIT
    assert sha256(args.rebuilt_binary.read_bytes()) == BINDINGS["release_executable"][1]
    assert sha256((audit / "PREREGISTRATION.md").read_bytes()) == receipt["preregistration"]["sha256"]

    mutants: list[tuple[str, dict[str, Any]]] = []
    displaced = copy.deepcopy(receipt)
    displaced["unrelated_binding_decoy"] = displaced["subject"].pop("bindings")
    mutants.append(("displaced_recursive_lookalike", displaced))
    missing = copy.deepcopy(receipt)
    missing["subject"]["unrelated_main_source_decoy"] = missing["subject"]["bindings"].pop("main_source")
    mutants.append(("correct_decoy_missing_named_binding", missing))
    duplicate_path = copy.deepcopy(receipt)
    duplicate_path["subject"]["bindings"]["engine_source"]["path"] = BINDINGS["main_source"][0]
    mutants.append(("duplicate_path_occurrence", duplicate_path))
    unknown = copy.deepcopy(receipt)
    unknown["unknown_extension"] = True
    mutants.append(("unknown_envelope_field", unknown))
    self_reference = copy.deepcopy(receipt)
    self_reference["audit_git_commit"] = "0" * 40
    mutants.append(("audit_git_commit", self_reference))
    false_check = copy.deepcopy(receipt)
    false_check["required_checks"]["scientific_output_commit_chain_gate_verified"] = False
    mutants.append(("false_required_check", false_check))
    numeric_true = copy.deepcopy(receipt)
    numeric_true["required_checks"]["exact_named_binding_contract"] = 1
    mutants.append(("numeric_true_one", numeric_true))
    numeric_false = copy.deepcopy(receipt)
    numeric_false["scientific_output_observed"] = 0
    mutants.append(("numeric_false_zero", numeric_false))
    for label, mutant in mutants:
        expect_rejected(label, mutant)

    duplicate_json = raw.replace(
        '"schema": "max11-', '"schema": "duplicate", "schema": "max11-', 1
    )
    for label, encoded in (
        ("duplicate_json_key", duplicate_json),
        ("trailing_json_data", raw + "{}"),
    ):
        try:
            strict_loads(encoded)
        except Rejected:
            pass
        else:
            raise AssertionError(f"mutant escaped: {label}")

    source = (root / BINDINGS["main_source"][0]).read_text()
    required_source_shapes = {
        "compiled_bytes": "(COMPILED_LOCK, STAGE_E_LOCK_PATH)",
        "engine_identity": "COMPILED_ENGINE == COMPILED_STAGE_A_ENGINE",
        "g0155_gate": "validate_stage_d_source_audit_gate(root, protocol, &candidate.source_audit)?",
        "committed_bytes": "sha256_bytes(&blob.stdout) == sha256_path",
        "output_chain": 'for (earlier, later) in [("A", "B"), ("B", "C"), ("C", "D")]',
        "dynamic_stage_d": "INHERITED_DIRECTIONS + candidate.appended_rows",
        "zero_residual_equivalence": "global_zero == first_nonzero_hinge.is_none()",
        "complete_census": "validate_term_receipts(&aggregate.term_receipts, candidate.terms.len())?",
        "end_rehash": "let end = load_and_validate_inputs(&root)?",
        "overwrite_refusal": "publish_exclusive(output_path, &serialized)?",
        "numeric_true_mutant": "stage_e_numeric_true",
        "numeric_false_mutant": "stage_e_numeric_false",
    }
    missing_shapes = [name for name, token in required_source_shapes.items() if token not in source]
    assert not missing_shapes, f"missing source gate shapes: {missing_shapes}"

    print(json.dumps({
        "schema": "g0156-focused-hostile-source-audit-v1",
        "result": "PASS",
        "bound_files_rehashed": len(BINDINGS),
        "structural_and_numeric_mutants_rejected": len(mutants) + 2,
        "source_gate_shapes_verified": len(required_source_shapes),
        "clean_rebuild_matches_bound_executable": True,
        "scientific_artifacts_opened": 0,
        "scientific_modes_run": 0,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
