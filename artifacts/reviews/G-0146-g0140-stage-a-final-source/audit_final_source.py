#!/usr/bin/env python3
"""Independent outcome-blind checker for the frozen G-0140 Stage-A producer.

The checker reads only the five frozen producer bindings, frozen source text,
the historical G-0139 audit receipt, and Git metadata.  The only producer
runtime modes it invokes are --self-test, --preflight-static, and
--preflight-ancestor.  It never opens a G-0140 scientific manifest, candidate,
scientific input, or output, and never invokes scientific replay.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
from typing import Any


FROZEN_COMMIT = "2157fd2a9776277354c45487ae1cbc0670ffc9b8"
G0139_COMMIT = "0bfdbf2db065d8517ad2d98d762473fed052cb54"
G0139_PATH = "artifacts/reviews/G-0139-g0135-result/RESULT_AUDIT_RECEIPT.json"
G0139_SHA256 = "282fba3591b656164d7cce728121de357ad793aa66339813101eb410e988399f"
STAGE_D_PATH = "artifacts/math/G-0135/new_member_global_replay_v1.json"
STAGE_D_SHA256 = "d576e142f213cd1f6b125246d22a766894ada4ade23de575ac5b14c9fd18f875"
STAGE_D_COMMIT = "270a62455097cbaf0a8f80426c54b6121d1afcba"
STAGE_D_AUDIT_PATH = (
    "artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json"
)
STAGE_D_AUDIT_SHA256 = (
    "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944"
)
G0139_EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_AWARE_RESULT_AUDIT"
G0139_CLAIM_BOUNDARY = (
    "Consistency only for the exact committed 135-term Stage-C member and exact "
    "G-0135 Stage-D result bytes. Same-lineage outcome-aware T1 evidence; no T2 "
    "independence, family completeness, frozen-family nonmembership, MAX11 lower "
    "bound, unrestricted nonrepresentability, all-n theorem, refereed status, "
    "formalization, or Lean theorem."
)

AUDIT_SCHEMA = "max11-g0146-g0140-stage-a-final-source-audit-v1"
AUDIT_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
AUDIT_EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
AUDIT_CLAIM_BOUNDARY = (
    "T1 source/custody clearance for the exact frozen Stage-A producer bytes only; "
    "no scientific manifest, input, or output was observed, no scientific replay "
    "was run, and no mathematical claim is promoted."
)

SUBJECT_BINDINGS = {
    "main_source": (
        "artifacts/math/G-0140/stage_a_pool/src/main.rs",
        "5fd91773b1e16cc54d09c20c72ef729a333bef4c8b6804f24a525a4be8258790",
        "100644",
    ),
    "engine_source": (
        "artifacts/math/G-0140/stage_a_pool/src/engine.rs",
        "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c",
        "100644",
    ),
    "cargo_manifest": (
        "artifacts/math/G-0140/stage_a_pool/Cargo.toml",
        "eb20b76b6a133a9c6e18052822974287047c9d1bd92c3b4851d20cf2c1dafc26",
        "100644",
    ),
    "cargo_lock": (
        "artifacts/math/G-0140/stage_a_pool/Cargo.lock",
        "263f994a09ef9d687136e287e300cf7b63caa744015027c051eadd59189e0eae",
        "100644",
    ),
    "release_executable": (
        "artifacts/math/G-0140/stage_a_pool/target/release/"
        "g0140-stage-a-pool128-global-replay",
        "366acb1e70a2699e3a26089263173f142af021b4a6379632e4786d460bf00f4a",
        "100755",
    ),
}


class DuplicateKey(ValueError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run(
    args: list[str], cwd: Path, *, check: bool = True, input_bytes: bytes | None = None
) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        args,
        cwd=cwd,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def git(root: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[bytes]:
    return run(["git", *args], root, check=check)


def git_blob(root: Path, commit: str, path: str) -> bytes:
    return git(root, "show", f"{commit}:{path}").stdout


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateKey(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def strict_json_loads(data: bytes | str) -> Any:
    return json.loads(data, object_pairs_hook=strict_object)


def source_slice(source: str, start: str, end: str) -> str:
    left = source.index(start)
    right = source.index(end, left)
    return source[left:right]


def is_sha256(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def get(value: Any, *path: str) -> Any:
    cursor = value
    for key in path:
        if not isinstance(cursor, dict) or key not in cursor:
            raise KeyError("/" + "/".join(path))
        cursor = cursor[key]
    return cursor


def current_g0139_semantic_predicate(receipt: Any) -> bool:
    """Exact source model of validate_g0139_semantics at the frozen commit."""
    try:
        custody = get(receipt, "input_custody")
        fixed = get(custody, "fixed_inputs")
        transitive = get(custody, "transitive_bound_inputs")
        return (
            isinstance(custody, dict)
            and isinstance(fixed, dict)
            and isinstance(transitive, dict)
            and get(receipt, "schema") == "max11-g0139-g0135-result-audit-v1"
            and get(receipt, "verdict") == "PASS"
            and get(receipt, "result") == "CONSISTENT_RESIDUAL_T1"
            and get(receipt, "evidence_class") == G0139_EVIDENCE_CLASS
            and get(receipt, "claim_boundary") == G0139_CLAIM_BOUNDARY
            and get(receipt, "reviewer", "same_model_lineage") is True
            and get(receipt, "preregistration", "outcome_aware") is True
            and get(receipt, "subject", "path") == STAGE_D_PATH
            and get(receipt, "subject", "sha256") == STAGE_D_SHA256
            and get(receipt, "subject", "git_commit") == STAGE_D_COMMIT
            and get(receipt, "subject", "result_observed_before_checker")
            == "EXACT_RESIDUAL_BATCH_CONTINUE"
            and get(receipt, "git_custody", "subject_commit") == STAGE_D_COMMIT
            and get(receipt, "git_custody", "strict_linear_ancestry") is True
            and get(receipt, "source_audit_anchor", "path") == STAGE_D_AUDIT_PATH
            and get(receipt, "source_audit_anchor", "sha256")
            == STAGE_D_AUDIT_SHA256
            and get(receipt, "source_audit_anchor", "verdict") == "PASS"
            and get(
                receipt,
                "clean_room_execution_boundary",
                "stage_d_bound_bytes_consumed_as_hashes_only",
            )
            is True
            and get(
                receipt,
                "clean_room_execution_boundary",
                "stage_d_scientific_replay_rerun",
            )
            is False
            and get(custody, "entry_exit_rehash_equal") is True
            and type(get(custody, "fixed_input_count")) is int
            and get(custody, "fixed_input_count") == len(fixed)
            and len(fixed) == 8
            and fixed.get(STAGE_D_PATH) == STAGE_D_SHA256
            and fixed.get(STAGE_D_AUDIT_PATH) == STAGE_D_AUDIT_SHA256
            and type(get(custody, "transitive_bound_input_count")) is int
            and get(custody, "transitive_bound_input_count") == len(transitive)
            and len(transitive) == 92
        )
    except (KeyError, TypeError):
        return False


def recursive_bindings(value: Any) -> list[dict[str, str]]:
    output: list[dict[str, str]] = []
    if isinstance(value, list):
        for child in value:
            output.extend(recursive_bindings(child))
    elif isinstance(value, dict):
        path = value.get("path")
        digest = value.get("sha256")
        if isinstance(path, str) and is_sha256(digest):
            output.append({"path": path, "sha256": digest})
        for child in value.values():
            output.extend(recursive_bindings(child))
    return output


def source_audit_envelope_predicate(receipt: Any) -> bool:
    try:
        return (
            get(receipt, "schema") == AUDIT_SCHEMA
            and get(receipt, "verdict") == "PASS"
            and get(receipt, "result") == AUDIT_RESULT
            and get(receipt, "evidence_class") == AUDIT_EVIDENCE_CLASS
            and get(receipt, "claim_boundary") == AUDIT_CLAIM_BOUNDARY
            and get(receipt, "scientific_manifest_observed") is False
            and get(receipt, "scientific_input_observed") is False
            and get(receipt, "scientific_output_observed") is False
            and get(receipt, "scientific_replay_run") is False
            and get(
                receipt,
                "subject",
                "commit_object_and_working_bytes_equal_for_all_bindings",
            )
            is True
        )
    except KeyError:
        return False


def implemented_final_source_audit_predicate(
    receipt: Any, available_by_path: dict[str, str]
) -> bool:
    """Source-exact semantic/content model after outer manifest/audit hash checks."""
    if not source_audit_envelope_predicate(receipt):
        return False
    try:
        if get(receipt, "subject", "git_commit") != FROZEN_COMMIT:
            return False
    except KeyError:
        return False
    observed = recursive_bindings(receipt)
    required = {path: digest for path, digest, _mode in SUBJECT_BINDINGS.values()}
    for path, digest in required.items():
        if not any(
            binding["path"] == path and binding["sha256"] == digest
            for binding in observed
        ):
            return False
    return all(
        available_by_path.get(binding["path"]) == binding["sha256"]
        for binding in observed
    )


def exact_nested_pass_contract(receipt: Any) -> bool:
    """The producer-declared exact five named subject bindings and no self-anchor."""
    if not source_audit_envelope_predicate(receipt):
        return False
    if "audit_git_commit" in receipt:
        return False
    try:
        subject = get(receipt, "subject")
        bindings = get(subject, "bindings")
    except KeyError:
        return False
    if not isinstance(bindings, dict) or set(bindings) != set(SUBJECT_BINDINGS):
        return False
    for label, (path, digest, _mode) in SUBJECT_BINDINGS.items():
        if bindings.get(label) != {"path": path, "sha256": digest}:
            return False
    return subject.get("git_commit") == FROZEN_COMMIT


def baseline_source_audit_receipt() -> dict[str, Any]:
    return {
        "schema": AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": AUDIT_RESULT,
        "evidence_class": AUDIT_EVIDENCE_CLASS,
        "claim_boundary": AUDIT_CLAIM_BOUNDARY,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "subject": {
            "git_commit": FROZEN_COMMIT,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
            "bindings": {
                label: {"path": path, "sha256": digest}
                for label, (path, digest, _mode) in SUBJECT_BINDINGS.items()
            },
        },
    }


def inspect_subject_bindings(root: Path) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for label, (path, expected_sha256, expected_mode) in SUBJECT_BINDINGS.items():
        working_path = root / path
        committed = git_blob(root, FROZEN_COMMIT, path)
        working = working_path.read_bytes()
        tree_line = git(root, "ls-tree", FROZEN_COMMIT, "--", path).stdout.decode().strip()
        metadata, listed_path = tree_line.split("\t", 1)
        mode, object_type, object_id = metadata.split()
        file_stat = os.lstat(working_path)
        actual_sha256 = sha256(working)
        checks = {
            "listed_path_exact": listed_path == path,
            "git_object_is_blob": object_type == "blob",
            "git_mode_exact": mode == expected_mode,
            "working_file_is_regular_not_symlink": stat.S_ISREG(file_stat.st_mode),
            "commit_and_working_bytes_equal": committed == working,
            "sha256_exact": actual_sha256 == expected_sha256,
            "git_blob_oid_matches_working": (
                git(root, "hash-object", path).stdout.decode().strip() == object_id
            ),
        }
        result[label] = {
            "path": path,
            "sha256": actual_sha256,
            "git_mode": mode,
            "git_blob": object_id,
            "bytes": len(working),
            "checks": checks,
            "pass": all(checks.values()),
        }
    return result


def mutate_g0139(receipt: dict[str, Any]) -> dict[str, dict[str, Any]]:
    fixtures: dict[str, dict[str, Any]] = {}

    mutant = copy.deepcopy(receipt)
    mutant["subject"]["git_commit"] = "0" * 40
    fixtures["wrong_subject_commit"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["evidence_class"] = "T2_INDEPENDENT_REPLAY"
    fixtures["wrong_evidence_class"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["reviewer"]["same_model_lineage"] = False
    fixtures["wrong_lineage_disclosure"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["preregistration"]["outcome_aware"] = False
    fixtures["wrong_outcome_awareness"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["claim_boundary"] = ""
    fixtures["wrong_claim_boundary"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["input_custody"]["entry_exit_rehash_equal"] = False
    fixtures["wrong_custody"] = mutant

    mutant = copy.deepcopy(receipt)
    mutant["source_audit_anchor"]["sha256"] = "0" * 64
    fixtures["wrong_source_audit_anchor"] = mutant

    return fixtures


def temp_git_working_drift_control() -> dict[str, Any]:
    """Exercise the same Git-blob/working-byte equality rule on generic bytes."""
    with tempfile.TemporaryDirectory(prefix="g0146-git-drift-") as raw:
        root = Path(raw)
        run(["git", "init", "-q"], root)
        run(["git", "config", "user.email", "g0146@example.invalid"], root)
        run(["git", "config", "user.name", "G-0146 hostile control"], root)
        path = root / "generic-manifest.json"
        path.write_bytes(b'{"state":"committed"}\n')
        run(["git", "add", "--", path.name], root)
        run(["git", "commit", "-q", "-m", "fixture"], root)

        commit = run(
            ["git", "log", "-1", "--format=%H", "--", path.name], root
        ).stdout.decode().strip()

        def model_accepts() -> bool:
            blob = run(["git", "show", f"{commit}:{path.name}"], root).stdout
            return sha256(blob) == sha256(path.read_bytes())

        committed_accepts = model_accepts()
        path.write_bytes(b'{"state":"mutated-working-copy"}\n')
        mutated_accepts = model_accepts()
        return {
            "generic_fixture_only": True,
            "committed_working_bytes_accepted": committed_accepts,
            "mutated_working_bytes_accepted": mutated_accepts,
            "pass": committed_accepts and not mutated_accepts,
        }


def run_permitted_modes(root: Path) -> dict[str, Any]:
    executable = root / SUBJECT_BINDINGS["release_executable"][0]
    commands = {
        "self_test": [str(executable), "--self-test"],
        "static_preflight": [str(executable), "--preflight-static"],
        "ancestor_preflight": [str(executable), "--preflight-ancestor"],
    }
    expected_stdout = {
        "self_test": "G-0140 Stage A self-test PASS\n",
        "static_preflight": "G-0140 Stage A outcome-blind static preflight PASS\n",
        "ancestor_preflight": (
            "G-0140 Stage A ancestor preflight PASS: 135 terms; 100 accumulated "
            "rows; disclosed first32 reconciled\n"
        ),
    }
    results: dict[str, Any] = {}
    for label, command in commands.items():
        started = time.monotonic()
        completed = run(command, root, check=False)
        elapsed = time.monotonic() - started
        stdout = completed.stdout.decode("utf-8", errors="replace")
        stderr = completed.stderr.decode("utf-8", errors="replace")
        results[label] = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": stdout,
            "stderr": stderr,
            "wall_seconds": elapsed,
            "pass": completed.returncode == 0
            and stdout == expected_stdout[label]
            and stderr == "",
        }
    return results


def audit(root: Path) -> dict[str, Any]:
    root = root.resolve()
    bindings = inspect_subject_bindings(root)
    available_by_path = {
        item["path"]: item["sha256"] for item in bindings.values()
    }
    source_bytes = git_blob(root, FROZEN_COMMIT, SUBJECT_BINDINGS["main_source"][0])
    source = source_bytes.decode("utf-8")
    g0139_semantics_source = source_slice(
        source, "fn validate_g0139_semantics(", "fn validate_g0139_gate("
    )
    g0139_gate_source = source_slice(
        source, "fn validate_g0139_gate(", "fn validate_current_release_executable("
    )
    source_audit_envelope_source = source_slice(
        source, "fn validate_source_audit_envelope(", "fn validate_source_audit("
    )
    source_audit_source = source_slice(
        source, "fn validate_source_audit(", "fn validate_compiled_bytes("
    )
    git_binding_source = source_slice(
        source, "fn git_commit_for_path(", "fn publish_exclusive("
    )
    manifest_source = source_slice(
        source, "fn validate_g0140_manifest(", "fn validate_panel("
    )
    compiled_source = source_slice(
        source, "fn validate_compiled_bytes(", "fn validate_shared_manifest("
    )
    self_test_source = source_slice(source, "fn self_test()", "fn static_preflight()")
    run_source = source_slice(source, "fn run(", "fn main()")

    source_repairs = {
        "g0139_exact_digest_pinned": "G0139_AUDIT_SHA256" in g0139_gate_source,
        "g0139_exact_commit_pinned": "G0139_AUDIT_COMMIT" in g0139_gate_source,
        "g0139_semantic_validator_invoked": (
            "validate_g0139_semantics(&receipt)?;" in g0139_gate_source
        ),
        "g0139_subject_commit_checked": '"/subject/git_commit"' in g0139_semantics_source,
        "g0139_evidence_class_checked": '"/evidence_class"' in g0139_semantics_source,
        "g0139_lineage_checked": (
            '"/reviewer/same_model_lineage"' in g0139_semantics_source
        ),
        "g0139_outcome_awareness_checked": (
            '"/preregistration/outcome_aware"' in g0139_semantics_source
        ),
        "g0139_claim_boundary_checked": '"/claim_boundary"' in g0139_semantics_source,
        "g0139_custody_checked": '"/input_custody/entry_exit_rehash_equal"'
        in g0139_semantics_source,
        "g0139_source_audit_anchor_checked": (
            '"/source_audit_anchor/path"' in g0139_semantics_source
            and '"/source_audit_anchor/sha256"' in g0139_semantics_source
            and '"/source_audit_anchor/verdict"' in g0139_semantics_source
        ),
        "g0139_hostile_mutants_built_in": (
            "G-0139 semantic hostile control escaped" in self_test_source
        ),
        "g0140_manifest_commit_check_precedes_parse": (
            manifest_source.index("git_commit_for_path(root, G0140_MANIFEST_PATH)?;")
            < manifest_source.index("strict_json(BufReader")
        ),
        "git_check_compares_blob_to_working_bytes": (
            "working bytes differ from committed binding" in git_binding_source
            and "sha256_bytes(&blob.stdout)"
            in git_binding_source
            and "sha256_path(&checked_repo_path(root, path)?)?" in git_binding_source
        ),
        "compiled_main_engine_cargo_lock_checked": all(
            token in compiled_source
            for token in [
                "COMPILED_SOURCE",
                "COMPILED_ENGINE",
                "COMPILED_MANIFEST",
                "COMPILED_LOCK",
            ]
        ),
        "mutable_inputs_revalidated_at_end": (
            "let end = load_and_validate_inputs(&root)?;" in run_source
            and "let end_protocol_manifest = validate_g0140_manifest(&root)?;"
            in run_source
            and "let end_audit = validate_g0139_gate(&root)?;" in run_source
            and "let end_executable = validate_current_release_executable(&root)?;"
            in run_source
        ),
    }

    g0139_bytes = git_blob(root, G0139_COMMIT, G0139_PATH)
    g0139_receipt = strict_json_loads(g0139_bytes)
    g0139_mutants = mutate_g0139(g0139_receipt)
    g0139_control_results = {
        label: not current_g0139_semantic_predicate(mutant)
        for label, mutant in g0139_mutants.items()
    }
    g0139_working = (root / G0139_PATH).read_bytes()
    g0139_gate = {
        "receipt_sha256_exact": sha256(g0139_bytes) == G0139_SHA256,
        "working_equals_pinned_commit": g0139_working == g0139_bytes,
        "baseline_semantics_accept": current_g0139_semantic_predicate(g0139_receipt),
        "declared_hostile_controls_rejected": all(g0139_control_results.values()),
        "hostile_controls": g0139_control_results,
    }
    g0139_gate["pass"] = all(
        value for key, value in g0139_gate.items() if key != "hostile_controls"
    )

    transitive_mutant = copy.deepcopy(g0139_receipt)
    transitive_key = next(iter(transitive_mutant["input_custody"]["transitive_bound_inputs"]))
    transitive_mutant["input_custody"]["transitive_bound_inputs"][transitive_key] = "0" * 64
    semantic_residual = {
        "mutated_nonanchor_transitive_value_accepted_by_semantic_function_model": (
            current_g0139_semantic_predicate(transitive_mutant)
        ),
        "but_rejected_by_full_frozen_gate_due_exact_receipt_sha": (
            sha256(json.dumps(transitive_mutant, sort_keys=True).encode()) != G0139_SHA256
        ),
        "classification": "RESIDUAL_NOT_RUNTIME_FALSE_POSITIVE_FOR_FROZEN_BYTES",
    }

    baseline = baseline_source_audit_receipt()
    lookalike = copy.deepcopy(baseline)
    displaced_bindings = list(lookalike["subject"].pop("bindings").values())
    lookalike["unrelated_receipt_lookalikes"] = displaced_bindings
    lookalike["audit_git_commit"] = "f" * 40
    lookalike["unknown_envelope_extension"] = {"accepted": True}

    missing = copy.deepcopy(lookalike)
    missing["unrelated_receipt_lookalikes"].pop()
    wrong_hash = copy.deepcopy(baseline)
    wrong_hash["subject"]["bindings"]["engine_source"]["sha256"] = "0" * 64
    wrong_subject = copy.deepcopy(baseline)
    wrong_subject["subject"]["git_commit"] = "0" * 40
    observed_science = copy.deepcopy(baseline)
    observed_science["scientific_input_observed"] = True

    final_audit_controls = {
        "baseline_exact_contract_accepted": implemented_final_source_audit_predicate(
            baseline, available_by_path
        )
        and exact_nested_pass_contract(baseline),
        "missing_required_pair_entirely_rejected": not implemented_final_source_audit_predicate(
            missing, available_by_path
        ),
        "wrong_required_hash_rejected": not implemented_final_source_audit_predicate(
            wrong_hash, available_by_path
        ),
        "wrong_subject_commit_rejected": not implemented_final_source_audit_predicate(
            wrong_subject, available_by_path
        ),
        "scientific_observation_rejected": not implemented_final_source_audit_predicate(
            observed_science, available_by_path
        ),
        "lookalike_without_named_subject_bindings_accepted": (
            implemented_final_source_audit_predicate(lookalike, available_by_path)
        ),
        "lookalike_fails_declared_exact_nested_contract": not exact_nested_pass_contract(
            lookalike
        ),
        "prohibited_audit_git_commit_ignored_and_accepted": (
            "audit_git_commit" not in source_audit_envelope_source
            and "audit_git_commit" not in source_audit_source
            and implemented_final_source_audit_predicate(lookalike, available_by_path)
        ),
        "source_uses_recursive_untyped_binding_search": (
            "collect_recursive_bindings(&receipt, &mut observed);" in source_audit_source
            and ".any(|binding| binding.path == *required" in source_audit_source
            and '"/subject/bindings"' not in source_audit_source
        ),
    }

    strict_parser_controls = {
        "source_duplicate_key_rejection_present": "duplicate JSON key" in source,
        "source_trailing_data_rejection_present": "deserializer.end()?;" in source,
        "checker_duplicate_key_rejected": False,
        "checker_trailing_data_rejected": False,
    }
    try:
        strict_json_loads('{"x":1,"x":2}')
    except DuplicateKey:
        strict_parser_controls["checker_duplicate_key_rejected"] = True
    try:
        strict_json_loads('{"x":1} {"y":2}')
    except json.JSONDecodeError:
        strict_parser_controls["checker_trailing_data_rejected"] = True

    runtime = run_permitted_modes(root)
    manifest_drift = temp_git_working_drift_control()

    blockers: list[dict[str, Any]] = []
    if final_audit_controls["lookalike_without_named_subject_bindings_accepted"]:
        blockers.append(
            {
                "id": "G0146-F1",
                "severity": "BLOCKER",
                "title": "Final source-audit admission accepts recursive binding lookalikes",
                "details": (
                    "The validator does not require the five exact bindings in the declared "
                    "subject structure. It accepts the same path/SHA pairs under unrelated "
                    "objects and ignores unknown fields, including audit_git_commit."
                ),
                "source_locations": [
                    "artifacts/math/G-0140/stage_a_pool/src/main.rs:1267",
                    "artifacts/math/G-0140/stage_a_pool/src/main.rs:1297",
                    "artifacts/math/G-0140/stage_a_pool/src/main.rs:1325",
                ],
            }
        )

    foundational_pass = (
        all(item["pass"] for item in bindings.values())
        and all(source_repairs.values())
        and g0139_gate["pass"]
        and all(strict_parser_controls.values())
        and manifest_drift["pass"]
        and all(item["pass"] for item in runtime.values())
        and final_audit_controls["baseline_exact_contract_accepted"]
        and final_audit_controls["missing_required_pair_entirely_rejected"]
        and final_audit_controls["wrong_required_hash_rejected"]
        and final_audit_controls["wrong_subject_commit_rejected"]
        and final_audit_controls["scientific_observation_rejected"]
    )
    verdict = "FAIL" if blockers or not foundational_pass else "PASS"
    if not foundational_pass and not blockers:
        blockers.append(
            {
                "id": "G0146-F0",
                "severity": "BLOCKER",
                "title": "One or more foundational controls did not pass",
                "details": "See the machine-readable check sections for the exact failure.",
            }
        )
        verdict = "FAIL"

    return {
        "schema": "max11-g0146-final-source-checker-v1",
        "verdict": verdict,
        "subject": {
            "git_commit": FROZEN_COMMIT,
            "frozen_commit_object_type": git(root, "cat-file", "-t", FROZEN_COMMIT)
            .stdout.decode()
            .strip(),
            "frozen_commit_is_ancestor_of_audit_head": (
                git(
                    root,
                    "merge-base",
                    "--is-ancestor",
                    FROZEN_COMMIT,
                    "HEAD",
                    check=False,
                ).returncode
                == 0
            ),
            "bindings": bindings,
        },
        "historical_g0141_blocker_repairs": {
            "g0139_semantic_and_custody_admission": g0139_gate,
            "g0140_manifest_commit_vs_working_bytes": manifest_drift,
            "source_repair_assertions": source_repairs,
            "pass": g0139_gate["pass"]
            and manifest_drift["pass"]
            and all(source_repairs.values()),
        },
        "strict_json_controls": strict_parser_controls,
        "final_source_audit_hostile_controls": final_audit_controls,
        "g0139_semantic_residual": semantic_residual,
        "permitted_runtime_modes": runtime,
        "blockers": blockers,
        "evidence_class": AUDIT_EVIDENCE_CLASS,
        "claim_boundary": AUDIT_CLAIM_BOUNDARY,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
    }


def self_test() -> dict[str, Any]:
    available = {path: digest for path, digest, _mode in SUBJECT_BINDINGS.values()}
    baseline = baseline_source_audit_receipt()
    lookalike = copy.deepcopy(baseline)
    lookalike["decoys"] = list(lookalike["subject"].pop("bindings").values())
    lookalike["audit_git_commit"] = "f" * 40
    missing = copy.deepcopy(lookalike)
    missing["decoys"].pop()
    wrong = copy.deepcopy(baseline)
    wrong["subject"]["bindings"]["main_source"]["sha256"] = "0" * 64

    duplicate_rejected = False
    trailing_rejected = False
    try:
        strict_json_loads('{"x":1,"x":2}')
    except DuplicateKey:
        duplicate_rejected = True
    try:
        strict_json_loads('{"x":1} false')
    except json.JSONDecodeError:
        trailing_rejected = True

    controls = {
        "baseline_passes_both_contracts": implemented_final_source_audit_predicate(
            baseline, available
        )
        and exact_nested_pass_contract(baseline),
        "lookalike_passes_implemented_predicate": implemented_final_source_audit_predicate(
            lookalike, available
        ),
        "lookalike_fails_exact_contract": not exact_nested_pass_contract(lookalike),
        "missing_pair_rejected": not implemented_final_source_audit_predicate(
            missing, available
        ),
        "wrong_hash_rejected": not implemented_final_source_audit_predicate(wrong, available),
        "duplicate_key_rejected": duplicate_rejected,
        "trailing_data_rejected": trailing_rejected,
    }
    return {
        "schema": "max11-g0146-final-source-checker-self-test-v1",
        "status": "PASS" if all(controls.values()) else "FAIL",
        "controls": controls,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    args = parser.parse_args()
    result = self_test() if args.self_test else audit(args.repo)
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.self_test:
        return 0 if result["status"] == "PASS" else 2
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
