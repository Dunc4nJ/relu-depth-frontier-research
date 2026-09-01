#!/usr/bin/env python3
"""Strict validator and hostile-mutation harness for the G-0166 receipt.

This validator is deliberately independent of the producer.  A final validation
checks the live receipt, the frozen subject blobs, the working bytes, the
preregistration commit, and the committed audit receipt.  ``--precommit`` exists
only to validate a not-yet-committed receipt structurally; it is visibly
non-final and cannot produce the final success result.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import stat
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable


SCHEMA = "max11-g0166-g0164-global-replay-source-audit-v1"
RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
EVIDENCE_CLASS = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
CLAIM_BOUNDARY = (
    "T1 source/custody clearance for the exact frozen G-0164 "
    "complete-global-replay producer bytes only; no scientific manifest, "
    "finite member, or global output was observed, no scientific replay was "
    "run, and no mathematical claim is promoted."
)
NO_CLAIM = (
    "This source audit does not adjudicate any future G-0164 scientific "
    "manifest, finite member, or global result, establish or exclude a global "
    "exact identity, validate family completeness, prove a MAX11 lower bound, "
    "settle unrestricted two-hidden-layer representation, establish "
    "minimality, prove an all-n statement, or supply a Lean theorem."
)

PREREGISTRATION_PATH = (
    "artifacts/reviews/G-0166-g0164-global-replay-source/PREREGISTRATION.md"
)
RECEIPT_PATH = (
    "artifacts/reviews/G-0166-g0164-global-replay-source/"
    "SOURCE_AUDIT_RECEIPT.json"
)

EXPECTED_BINDINGS: dict[str, tuple[str, str, str]] = {
    "main_source": (
        "artifacts/math/G-0164/stage_b_global_replay/src/main.rs",
        "acadf6bcbc2b0ac6d87b096ff7909d5e07cfd31cae1e84fa7301a2b1488b2ef0",
        "100644",
    ),
    "candidate_source": (
        "artifacts/math/G-0164/stage_b_global_replay/src/candidate.rs",
        "572e2bf6bbd6e5f9b27e4f99700ec1960cc20114f0228e8a2d3343325a8b28fc",
        "100644",
    ),
    "engine_source": (
        "artifacts/math/G-0164/stage_b_global_replay/src/engine.rs",
        "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c",
        "100644",
    ),
    "cargo_manifest": (
        "artifacts/math/G-0164/stage_b_global_replay/Cargo.toml",
        "05df37270ef89f78b8a764484ce2049b4b0bf152f1ef778b4d88352546318996",
        "100644",
    ),
    "cargo_lock": (
        "artifacts/math/G-0164/stage_b_global_replay/Cargo.lock",
        "fc18595480e30ffeda7fcedcd6d63019744b8b9718fff7d6d31a71a373f89595",
        "100644",
    ),
    "g0117_cargo_manifest": (
        "artifacts/math/G-0117/Cargo.toml",
        "0e2ff3c73ce82b508ae21b35bc973c202efbeae03b7e9cf78d3b784664ce5815",
        "100644",
    ),
    "g0117_lib_source": (
        "artifacts/math/G-0117/src/lib.rs",
        "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6",
        "100644",
    ),
    "release_executable": (
        "artifacts/math/G-0164/stage_b_global_replay/target/release/"
        "g0164-stage-b-global-replay",
        "38de94fd68af9eb0aaa4fa2f26908ab4771caa42ab89f569d8ba6b729e93ce94",
        "100755",
    ),
}

REQUIRED_CHECKS = (
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
    "engine_byte_identity_with_g0140_verified",
    "finite_member_source_audit_gate_verified",
    "finite_member_global_manifest_commit_chain_verified",
    "scientific_outputs_excluded_from_manifest_bindings",
    "dynamic_direct_basis_member_contract_verified",
    "global_zero_and_residual_branches_verified",
    "complete_label_census_and_end_rehash_verified",
    "overwrite_refusal_verified",
    "prohibited_scientific_modes_not_run",
)

SCIENTIFIC_FLAGS = (
    "scientific_manifest_observed",
    "scientific_input_observed",
    "scientific_output_observed",
    "scientific_replay_run",
)

TOP_LEVEL_KEYS = {
    "schema",
    "verdict",
    "result",
    "evidence_class",
    "claim_boundary",
    "reviewer",
    "preregistration",
    "subject",
    "required_checks",
    *SCIENTIFIC_FLAGS,
    "no_claim",
}
REVIEWER_KEYS = {
    "agent_name",
    "program",
    "model",
    "same_model_lineage",
    "fresh_context",
}
PREREGISTRATION_KEYS = {
    "path",
    "sha256",
    "git_commit",
    "committed_and_pushed_before_subject_source_inspection",
    "committed_and_pushed_before_runtime_checks",
}
SUBJECT_KEYS = {
    "git_commit",
    "commit_object_and_working_bytes_equal_for_all_bindings",
    "bindings",
}
BINDING_KEYS = {"path", "sha256"}


class AuditError(RuntimeError):
    """A strict receipt or custody requirement failed."""


@dataclass(frozen=True)
class Contract:
    subject_commit: str
    preregistration_sha256: str
    preregistration_commit: str
    agent_name: str
    program: str
    model: str
    audit_commit: str | None


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def require_exact_keys(value: Any, expected: set[str], label: str) -> dict[str, Any]:
    require(type(value) is dict, f"{label} must be an object")
    observed = set(value)
    require(observed == expected, f"{label} keys differ: {sorted(observed ^ expected)}")
    return value


def require_exact_string(value: Any, expected: str, label: str) -> None:
    require(type(value) is str and value == expected, f"{label} differs")


def require_true(value: Any, label: str) -> None:
    require(type(value) is bool and value is True, f"{label} must be strict true")


def require_false(value: Any, label: str) -> None:
    require(type(value) is bool and value is False, f"{label} must be strict false")


def reject_constant(raw: str) -> Any:
    raise AuditError(f"non-JSON numeric constant: {raw}")


def no_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise AuditError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def strict_load(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as error:
        raise AuditError("receipt is not UTF-8") from error
    decoder = json.JSONDecoder(
        object_pairs_hook=no_duplicate_pairs,
        parse_constant=reject_constant,
    )
    leading = len(text) - len(text.lstrip())
    try:
        value, end = decoder.raw_decode(text, leading)
    except (json.JSONDecodeError, AuditError) as error:
        raise AuditError(f"strict JSON parse failed: {error}") from error
    require(not text[end:].strip(), "trailing JSON data")
    return value


def validate_data(receipt: Any, contract: Contract) -> None:
    top = require_exact_keys(receipt, TOP_LEVEL_KEYS, "receipt")
    require_exact_string(top["schema"], SCHEMA, "schema")
    require_exact_string(top["verdict"], "PASS", "verdict")
    require_exact_string(top["result"], RESULT, "result")
    require_exact_string(top["evidence_class"], EVIDENCE_CLASS, "evidence_class")
    require_exact_string(top["claim_boundary"], CLAIM_BOUNDARY, "claim_boundary")
    require_exact_string(top["no_claim"], NO_CLAIM, "no_claim")

    reviewer = require_exact_keys(top["reviewer"], REVIEWER_KEYS, "reviewer")
    require_exact_string(reviewer["agent_name"], contract.agent_name, "reviewer.agent_name")
    require_exact_string(reviewer["program"], contract.program, "reviewer.program")
    require_exact_string(reviewer["model"], contract.model, "reviewer.model")
    require_true(reviewer["same_model_lineage"], "reviewer.same_model_lineage")
    require_true(reviewer["fresh_context"], "reviewer.fresh_context")

    preregistration = require_exact_keys(
        top["preregistration"], PREREGISTRATION_KEYS, "preregistration"
    )
    require_exact_string(
        preregistration["path"], PREREGISTRATION_PATH, "preregistration.path"
    )
    require_exact_string(
        preregistration["sha256"],
        contract.preregistration_sha256,
        "preregistration.sha256",
    )
    require_exact_string(
        preregistration["git_commit"],
        contract.preregistration_commit,
        "preregistration.git_commit",
    )
    require_true(
        preregistration["committed_and_pushed_before_subject_source_inspection"],
        "preregistration.committed_and_pushed_before_subject_source_inspection",
    )
    require_true(
        preregistration["committed_and_pushed_before_runtime_checks"],
        "preregistration.committed_and_pushed_before_runtime_checks",
    )

    subject = require_exact_keys(top["subject"], SUBJECT_KEYS, "subject")
    require_exact_string(subject["git_commit"], contract.subject_commit, "subject.git_commit")
    if contract.audit_commit is not None:
        require(
            subject["git_commit"] != contract.audit_commit,
            "self-referential audit commit rejected",
        )
    require_true(
        subject["commit_object_and_working_bytes_equal_for_all_bindings"],
        "subject.commit_object_and_working_bytes_equal_for_all_bindings",
    )
    bindings = require_exact_keys(
        subject["bindings"], set(EXPECTED_BINDINGS), "subject.bindings"
    )
    observed_paths: set[str] = set()
    for name, (path, sha256, _mode) in EXPECTED_BINDINGS.items():
        binding = require_exact_keys(bindings[name], BINDING_KEYS, f"binding.{name}")
        require_exact_string(binding["path"], path, f"binding.{name}.path")
        require_exact_string(binding["sha256"], sha256, f"binding.{name}.sha256")
        require(binding["path"] not in observed_paths, f"duplicate binding path: {path}")
        observed_paths.add(binding["path"])

    checks = require_exact_keys(
        top["required_checks"], set(REQUIRED_CHECKS), "required_checks"
    )
    for name in REQUIRED_CHECKS:
        require_true(checks[name], f"required_checks.{name}")
    for name in SCIENTIFIC_FLAGS:
        require_false(top[name], name)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def git(repo: Path, *arguments: str) -> bytes:
    result = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        stdout=subprocess.PIPE,
        check=False,
    )
    require(
        result.returncode == 0,
        f"git {' '.join(arguments)} failed with status {result.returncode}",
    )
    return result.stdout


def resolve_commit(repo: Path, commit: str, label: str) -> str:
    resolved = git(repo, "rev-parse", f"{commit}^{{commit}}").decode().strip()
    require(resolved == commit, f"{label} does not resolve exactly")
    return resolved


def require_ancestor(repo: Path, ancestor: str, descendant: str, label: str) -> None:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo,
        check=False,
    )
    require(result.returncode == 0, f"ancestry failed: {label}")


def validate_git_custody(repo: Path, receipt: dict[str, Any], contract: Contract) -> None:
    root = Path(git(repo, "rev-parse", "--show-toplevel").decode().strip()).resolve()
    require(root == repo.resolve(), "--repo is not the Git top level")
    resolve_commit(repo, contract.subject_commit, "subject commit")

    bindings = receipt["subject"]["bindings"]
    for name, (relative, expected_sha256, expected_mode) in EXPECTED_BINDINGS.items():
        path = repo / relative
        metadata = path.lstat()
        require(not stat.S_ISLNK(metadata.st_mode), f"working binding is a symlink: {name}")
        require(stat.S_ISREG(metadata.st_mode), f"working binding is not a file: {name}")
        require(sha256_path(path) == expected_sha256, f"working SHA-256 differs: {name}")
        blob = git(repo, "show", f"{contract.subject_commit}:{relative}")
        require(sha256_bytes(blob) == expected_sha256, f"subject blob SHA-256 differs: {name}")
        tree_lines = git(repo, "ls-tree", contract.subject_commit, "--", relative).decode().splitlines()
        require(len(tree_lines) == 1, f"subject tree occurrence count differs: {name}")
        metadata_text, observed_path = tree_lines[0].split("\t", 1)
        mode, object_type, _object_id = metadata_text.split()
        require(
            mode == expected_mode and object_type == "blob" and observed_path == relative,
            f"subject tree binding differs: {name}",
        )
        status_output = git(repo, "status", "--porcelain=v1", "--", relative)
        require(not status_output, f"working binding is dirty: {name}")
        require(bindings[name]["sha256"] == expected_sha256, f"receipt SHA differs: {name}")

    resolve_commit(repo, contract.preregistration_commit, "preregistration commit")
    preregistration = repo / PREREGISTRATION_PATH
    require(
        sha256_path(preregistration) == contract.preregistration_sha256,
        "working preregistration SHA-256 differs",
    )
    preregistration_blob = git(
        repo,
        "show",
        f"{contract.preregistration_commit}:{PREREGISTRATION_PATH}",
    )
    require(
        sha256_bytes(preregistration_blob) == contract.preregistration_sha256,
        "committed preregistration SHA-256 differs",
    )
    preregistration_latest = git(
        repo, "log", "-1", "--format=%H", "--", PREREGISTRATION_PATH
    ).decode().strip()
    require(
        preregistration_latest == contract.preregistration_commit,
        "preregistration latest commit differs",
    )
    require_ancestor(
        repo,
        contract.subject_commit,
        contract.preregistration_commit,
        "subject -> preregistration",
    )

    if contract.audit_commit is None:
        return
    resolve_commit(repo, contract.audit_commit, "audit commit")
    require(
        contract.audit_commit not in {contract.subject_commit, contract.preregistration_commit},
        "audit commit is self-referential or collapsed into preregistration",
    )
    receipt_path = repo / RECEIPT_PATH
    receipt_sha256 = sha256_path(receipt_path)
    receipt_blob = git(repo, "show", f"{contract.audit_commit}:{RECEIPT_PATH}")
    require(sha256_bytes(receipt_blob) == receipt_sha256, "committed receipt bytes differ")
    receipt_latest = git(repo, "log", "-1", "--format=%H", "--", RECEIPT_PATH).decode().strip()
    require(receipt_latest == contract.audit_commit, "receipt latest commit differs")
    require_ancestor(
        repo,
        contract.preregistration_commit,
        contract.audit_commit,
        "preregistration -> audit receipt",
    )


Mutation = Callable[[dict[str, Any]], None]


def mutation_suite(base: dict[str, Any], contract: Contract) -> int:
    rejected = 0

    def expect_data_rejection(label: str, mutate: Mutation) -> None:
        nonlocal rejected
        candidate = copy.deepcopy(base)
        mutate(candidate)
        candidate_encoding = json.dumps(candidate, sort_keys=True, separators=(",", ":"))
        base_encoding = json.dumps(base, sort_keys=True, separators=(",", ":"))
        require(candidate_encoding != base_encoding, f"mutation was a no-op: {label}")
        try:
            validate_data(candidate, contract)
        except AuditError:
            rejected += 1
            return
        raise AuditError(f"hostile mutation accepted: {label}")

    for name in REQUIRED_CHECKS:
        expect_data_rejection(
            f"check false: {name}",
            lambda value, key=name: value["required_checks"].__setitem__(key, False),
        )
        expect_data_rejection(
            f"check missing: {name}",
            lambda value, key=name: value["required_checks"].__delitem__(key),
        )
        expect_data_rejection(
            f"check integer: {name}",
            lambda value, key=name: value["required_checks"].__setitem__(key, 1),
        )

    for name in SCIENTIFIC_FLAGS:
        expect_data_rejection(
            f"scientific flag true: {name}",
            lambda value, key=name: value.__setitem__(key, True),
        )
        expect_data_rejection(
            f"scientific flag integer one: {name}",
            lambda value, key=name: value.__setitem__(key, 1),
        )
        expect_data_rejection(
            f"scientific flag integer zero: {name}",
            lambda value, key=name: value.__setitem__(key, 0),
        )

    for name, (path, _sha256, _mode) in EXPECTED_BINDINGS.items():
        expect_data_rejection(
            f"binding path substitution: {name}",
            lambda value, key=name, replacement=path + ".decoy": value["subject"][
                "bindings"
            ][key].__setitem__("path", replacement),
        )
        expect_data_rejection(
            f"binding hash substitution: {name}",
            lambda value, key=name: value["subject"]["bindings"][key].__setitem__(
                "sha256", "0" * 64
            ),
        )

    for name in TOP_LEVEL_KEYS:
        expect_data_rejection(
            f"missing top-level field: {name}",
            lambda value, key=name: value.__delitem__(key),
        )

    unknown_mutations: list[tuple[str, Mutation]] = [
        ("unknown top-level", lambda value: value.__setitem__("unknown", True)),
        ("unknown reviewer", lambda value: value["reviewer"].__setitem__("unknown", True)),
        (
            "unknown preregistration",
            lambda value: value["preregistration"].__setitem__("unknown", True),
        ),
        ("unknown subject", lambda value: value["subject"].__setitem__("unknown", True)),
        (
            "unknown bindings",
            lambda value: value["subject"]["bindings"].__setitem__("unknown", {}),
        ),
        (
            "unknown binding field",
            lambda value: value["subject"]["bindings"]["main_source"].__setitem__(
                "unknown", True
            ),
        ),
        (
            "unknown required check",
            lambda value: value["required_checks"].__setitem__("unknown", True),
        ),
    ]
    for label, mutation in unknown_mutations:
        expect_data_rejection(label, mutation)

    def correct_decoy_missing(value: dict[str, Any]) -> None:
        decoy = value["subject"]["bindings"].pop("candidate_source")
        value["subject"]["bindings"]["candidate_source_decoy"] = decoy

    expect_data_rejection("correct decoy with missing named binding", correct_decoy_missing)

    def displaced_recursive(value: dict[str, Any]) -> None:
        displaced = value["subject"]["bindings"].pop("main_source")
        value["subject"]["displaced"] = {"main_source": displaced}

    expect_data_rejection("displaced recursive lookalike", displaced_recursive)
    expect_data_rejection(
        "duplicate path occurrence",
        lambda value: value["subject"]["bindings"]["candidate_source"].__setitem__(
            "path", value["subject"]["bindings"]["main_source"]["path"]
        ),
    )

    audit_commit = contract.audit_commit or ("f" * 40)
    if audit_commit == contract.subject_commit:
        audit_commit = "e" * 40
    expect_data_rejection(
        "self-referential audit commit",
        lambda value: value["subject"].__setitem__("git_commit", audit_commit),
    )

    boolean_mutations: list[tuple[str, list[str]]] = [
        ("reviewer.same_model_lineage", ["reviewer", "same_model_lineage"]),
        ("reviewer.fresh_context", ["reviewer", "fresh_context"]),
        (
            "preregistration.before_source",
            ["preregistration", "committed_and_pushed_before_subject_source_inspection"],
        ),
        (
            "preregistration.before_runtime",
            ["preregistration", "committed_and_pushed_before_runtime_checks"],
        ),
        (
            "subject.working_identity",
            ["subject", "commit_object_and_working_bytes_equal_for_all_bindings"],
        ),
    ]
    for label, path in boolean_mutations:
        def set_nested(value: dict[str, Any], replacement: Any, keys: list[str] = path) -> None:
            cursor = value
            for key in keys[:-1]:
                cursor = cursor[key]
            cursor[keys[-1]] = replacement

        expect_data_rejection(f"strict true false: {label}", lambda value: set_nested(value, False))
        expect_data_rejection(f"strict true integer: {label}", lambda value: set_nested(value, 1))

    compact = json.dumps(base, separators=(",", ":"), ensure_ascii=False).encode()
    raw_mutations = [
        ("duplicate top-level key", compact.replace(b"{", b'{"schema":"duplicate",', 1)),
        (
            "duplicate reviewer key",
            compact.replace(b'"reviewer":{', b'"reviewer":{"agent_name":"duplicate",', 1),
        ),
        (
            "duplicate preregistration key",
            compact.replace(
                b'"preregistration":{',
                b'"preregistration":{"path":"duplicate",',
                1,
            ),
        ),
        (
            "duplicate subject key",
            compact.replace(b'"subject":{', b'"subject":{"git_commit":"duplicate",', 1),
        ),
        (
            "duplicate bindings key",
            compact.replace(b'"bindings":{', b'"bindings":{"main_source":{},', 1),
        ),
        (
            "duplicate binding field",
            compact.replace(b'"main_source":{', b'"main_source":{"path":"duplicate",', 1),
        ),
        (
            "duplicate required check",
            compact.replace(
                b'"required_checks":{',
                b'"required_checks":{"exact_named_binding_contract":false,',
                1,
            ),
        ),
        ("trailing JSON object", compact + b"\n{}"),
        ("trailing JSON scalar", compact + b" true"),
    ]
    for label, raw in raw_mutations:
        require(raw != compact, f"raw mutation was a no-op: {label}")
        try:
            strict_load(raw)
        except AuditError:
            rejected += 1
            continue
        raise AuditError(f"hostile raw JSON mutation accepted: {label}")

    return rejected


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--subject-commit", required=True)
    parser.add_argument("--preregistration-sha256", required=True)
    parser.add_argument("--preregistration-commit", required=True)
    parser.add_argument("--agent-name", required=True)
    parser.add_argument("--program", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--audit-commit")
    parser.add_argument("--precommit", action="store_true")
    return parser.parse_args()


def main() -> int:
    arguments = parse_args()
    require(arguments.receipt.resolve() == (arguments.repo / RECEIPT_PATH).resolve(), "receipt path differs")
    require(
        arguments.precommit == (arguments.audit_commit is None),
        "use --precommit without --audit-commit, or final mode with --audit-commit",
    )
    contract = Contract(
        subject_commit=arguments.subject_commit,
        preregistration_sha256=arguments.preregistration_sha256,
        preregistration_commit=arguments.preregistration_commit,
        agent_name=arguments.agent_name,
        program=arguments.program,
        model=arguments.model,
        audit_commit=arguments.audit_commit,
    )
    receipt = strict_load(arguments.receipt.read_bytes())
    validate_data(receipt, contract)
    validate_git_custody(arguments.repo.resolve(), receipt, contract)
    rejected = mutation_suite(receipt, contract)
    mode = "NONFINAL_PRECOMMIT_STRUCTURE" if arguments.precommit else "FINAL_COMMITTED_RECEIPT"
    print(
        json.dumps(
            {
                "result": "SOURCE_AUDIT_RECEIPT_VALIDATED",
                "mode": mode,
                "hostile_mutations_rejected": rejected,
                "receipt_sha256": sha256_path(arguments.receipt),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, OSError) as error:
        print(f"G-0166 receipt validation FAILED: {error}", file=sys.stderr)
        raise SystemExit(1)
