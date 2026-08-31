#!/usr/bin/env python3
"""Outcome-blind semantic probe for the frozen G-0140 Stage-A source.

The probe reads only the exact subject source and the already-published G-0139
audit receipt.  It never resolves or opens any G-0140 scientific manifest or
output.  Hostile receipts are constructed in memory and evaluated against a
source-exact model of the private `validate_g0139_gate` predicate; the private
Rust function is not invoked directly.
"""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from typing import Any


SUBJECT_COMMIT = "1ee34276dcbbd35aedf090cb19bddf57283eb1d2"
SUBJECT_SOURCE = "artifacts/math/G-0140/stage_a_pool/src/main.rs"
SUBJECT_SOURCE_SHA256 = (
    "9c5051e4027a78330fcfb23a3d024b3042849215642f1bc4b4f85c6037419334"
)
G0139_COMMIT = "0bfdbf2db065d8517ad2d98d762473fed052cb54"
G0139_PATH = "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json"
G0139_SHA256 = "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f"
STAGE_D_PATH = "artifacts/math/G-0135/new_member_global_replay_v1.json"
STAGE_D_SHA256 = "d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875"
STAGE_D_COMMIT = "270a62455097cbaf0a8f80426c54b6121d1afcba"
STAGE_D_SOURCE_AUDIT_PATH = (
    "artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json"
)
STAGE_D_SOURCE_AUDIT_SHA256 = (
    "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944"
)


def git_show(commit: str, path: str) -> bytes:
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
    ).stdout


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def source_slice(source: str, start: str, end: str) -> str:
    left = source.index(start)
    right = source.index(end, left)
    return source[left:right]


def recursive_bindings(value: Any) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    if isinstance(value, list):
        for child in value:
            found.extend(recursive_bindings(child))
    elif isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and isinstance(digest, str) and len(digest) == 64:
            found.append((path, digest))
        for child in value.values():
            found.extend(recursive_bindings(child))
    return found


def implemented_g0139_predicate(receipt: dict[str, Any]) -> bool:
    """Exact semantic field predicate at main.rs lines 1107-1122."""
    return (
        receipt.get("schema") == "max11-g0139-g0135-result-audit-v1"
        and receipt.get("verdict") == "PASS"
        and receipt.get("result") == "CONSISTENT_RESIDUAL_T1"
        and (STAGE_D_PATH, STAGE_D_SHA256) in recursive_bindings(receipt)
    )


def preregistered_semantic_predicate(receipt: dict[str, Any]) -> bool:
    """Decision-bearing G-0139 fields frozen by the G-0141 preregistration."""
    reviewer = receipt.get("reviewer", {})
    preregistration = receipt.get("preregistration", {})
    subject = receipt.get("subject", {})
    source_audit = receipt.get("source_audit_anchor", {})
    custody = receipt.get("input_custody", {})
    fixed_inputs = custody.get("fixed_inputs", {})
    transitive = custody.get("transitive_bound_inputs", {})
    claim_boundary = receipt.get("claim_boundary")
    return (
        implemented_g0139_predicate(receipt)
        and receipt.get("evidence_class")
        == "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT"
        and reviewer.get("same_model_lineage") is True
        and preregistration.get("outcome_aware") is True
        and isinstance(claim_boundary, str)
        and bool(claim_boundary.strip())
        and "no T2 independence" in claim_boundary
        and subject.get("path") == STAGE_D_PATH
        and subject.get("sha256") == STAGE_D_SHA256
        and subject.get("git_commit") == STAGE_D_COMMIT
        and source_audit.get("path") == STAGE_D_SOURCE_AUDIT_PATH
        and source_audit.get("sha256") == STAGE_D_SOURCE_AUDIT_SHA256
        and source_audit.get("verdict") == "PASS"
        and custody.get("entry_exit_rehash_equal") is True
        and fixed_inputs.get(STAGE_D_PATH) == STAGE_D_SHA256
        and fixed_inputs.get(STAGE_D_SOURCE_AUDIT_PATH)
        == STAGE_D_SOURCE_AUDIT_SHA256
        and custody.get("transitive_bound_input_count") == len(transitive)
        and len(transitive) > 0
    )


def hostile_fixtures(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}

    mutant = copy.deepcopy(receipt)
    mutant["subject"]["git_commit"] = "0" * 40
    fixtures["wrong_subject_commit"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["evidence_class"] = "T2_INDEPENDENT_REPLAY"
    fixtures["false_evidence_class"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["reviewer"]["same_model_lineage"] = False
    mutant["preregistration"]["outcome_aware"] = False
    fixtures["false_independence_disclosure"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["claim_boundary"] = ""
    fixtures["missing_claim_boundary"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant.pop("input_custody")
    fixtures["missing_transitive_custody"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["source_audit_anchor"]["sha256"] = "0" * 64
    mutant["source_audit_anchor"]["verdict"] = "FAIL"
    fixtures["false_source_audit_anchor"] = mutant

    return fixtures


def main() -> int:
    source_bytes = git_show(SUBJECT_COMMIT, SUBJECT_SOURCE)
    assert sha256(source_bytes) == SUBJECT_SOURCE_SHA256
    source = source_bytes.decode("utf-8")
    g0139_gate = source_slice(
        source,
        "fn validate_g0139_gate(",
        "fn validate_current_release_executable(",
    )
    g0140_manifest_gate = source_slice(
        source,
        "fn validate_g0140_manifest(",
        "fn validate_panel(",
    )
    self_test = source_slice(source, "fn self_test()", "fn static_preflight()")

    receipt_bytes = git_show(G0139_COMMIT, G0139_PATH)
    assert sha256(receipt_bytes) == G0139_SHA256
    receipt = json.loads(receipt_bytes)
    assert implemented_g0139_predicate(receipt)
    assert preregistered_semantic_predicate(receipt)

    required_tokens_absent = {
        "subject_git_commit": '"/subject/git_commit"' not in g0139_gate,
        "evidence_class": '"/evidence_class"' not in g0139_gate,
        "same_model_lineage": '"/reviewer/same_model_lineage"' not in g0139_gate,
        "outcome_aware": '"/preregistration/outcome_aware"' not in g0139_gate,
        "claim_boundary": '"/claim_boundary"' not in g0139_gate,
        "source_audit_anchor": '"/source_audit_anchor"' not in g0139_gate,
        "input_custody": '"/input_custody"' not in g0139_gate,
    }
    assert all(required_tokens_absent.values())

    fixtures = hostile_fixtures(receipt)
    fixture_results = {
        name: {
            "implemented_gate_accepts": implemented_g0139_predicate(mutant),
            "preregistered_semantic_gate_accepts": preregistered_semantic_predicate(mutant),
        }
        for name, mutant in fixtures.items()
    }
    assert all(
        result["implemented_gate_accepts"]
        and not result["preregistered_semantic_gate_accepts"]
        for result in fixture_results.values()
    )

    manifest_sha_mitigation_present = (
        "snapshot.bindings_by_path.get(G0139_AUDIT_PATH) == Some(&g0139.sha256)"
        in g0140_manifest_gate
    )
    committed_receipt_mitigation_present = (
        "git_commit_for_path(root, G0139_AUDIT_PATH)?;" in g0139_gate
    )
    g0140_manifest_commit_required = (
        "git_commit_for_path(root, G0140_MANIFEST_PATH)" in g0140_manifest_gate
    )
    g0139_semantic_mutant_in_self_test = any(
        token in self_test
        for token in [
            "same_model_lineage",
            "outcome_aware",
            "source_audit_anchor",
            "transitive_bound_inputs",
        ]
    )
    assert manifest_sha_mitigation_present
    assert committed_receipt_mitigation_present
    assert not g0140_manifest_commit_required
    assert not g0139_semantic_mutant_in_self_test

    result = {
        "schema": "max11-g0141-g0139-gate-hostile-fixtures-v1",
        "status": "FAIL_G0139_SEMANTIC_ADMISSION",
        "probe_method": {
            "type": "static_source_extraction_plus_source_exact_model",
            "private_rust_function_invoked_directly": False,
            "details": "The checker extracts the exact committed Rust gate, asserts required semantic tokens are absent, and evaluates an exact Python model of main.rs lines 1107-1122.",
        },
        "subject": {
            "git_commit": SUBJECT_COMMIT,
            "path": SUBJECT_SOURCE,
            "sha256": SUBJECT_SOURCE_SHA256,
        },
        "g0139_receipt": {
            "git_commit": G0139_COMMIT,
            "path": G0139_PATH,
            "sha256": G0139_SHA256,
            "baseline_implemented_gate_accepts": True,
            "baseline_preregistered_semantic_gate_accepts": True,
        },
        "checked_by_implemented_gate": [
            "schema",
            "verdict",
            "result",
            "one recursive Stage-D path/SHA binding",
        ],
        "required_semantic_tokens_absent_from_gate": required_tokens_absent,
        "hostile_fixtures": fixture_results,
        "mitigations": {
            "future_manifest_binds_exact_g0139_sha": manifest_sha_mitigation_present,
            "g0139_receipt_must_match_a_committed_blob": committed_receipt_mitigation_present,
            "why_insufficient": "Byte custody does not validate omitted semantic fields; a semantically deficient committed receipt can be bound exactly.",
        },
        "additional_custody_gap": {
            "future_g0140_manifest_commit_required_by_parser": g0140_manifest_commit_required,
            "meaning": "The parser validates commit fields for inputs but does not require the one-shot G-0140 manifest itself to equal committed Git bytes.",
        },
        "mutation_coverage": {
            "g0139_semantic_mutant_present_in_builtin_self_test": g0139_semantic_mutant_in_self_test,
        },
        "scientific_manifest_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
