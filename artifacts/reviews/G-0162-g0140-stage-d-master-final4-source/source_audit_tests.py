#!/usr/bin/env python3
"""Independent source-only controls for the G-0162 Stage-D final4 audit."""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any


SUBJECT_REL = Path(
    "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py"
)
SELECTOR_REL = Path(
    "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
CORE_REL = Path("artifacts/math/G-0135/stage_c_master/full_family_master_v3.py")
G0135_RESULT_REL = Path("artifacts/math/G-0135/full_family_master_result_v3.json")
HELPER_REL = Path("artifacts/math/G-0117/fresh_q_cegis_exact.py")
PREREG_REL = Path(
    "artifacts/reviews/G-0162-g0140-stage-d-master-final4-source/PREREGISTRATION.md"
)

TARGET_COMMIT = "19107c5eed2cad00d48eff3dd9bea0c015ecce89"
SUBJECT_SHA256 = "1f4e7f3a141bfbfb7a090ee681bab649ba0cebc191021b112db0368fe2256581"
SELECTOR_SHA256 = "f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3"
CORE_SHA256 = "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"
G0135_RESULT_SHA256 = (
    "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8"
)
RECEIPT_SCHEMA = "max11-g0162-g0140-stage-d-master-final4-source-audit-v1"
CLAIM = (
    "T1 source/custody clearance for the exact frozen G-0140 reopened-master "
    "producer bytes only; no scientific manifest, input, or output was "
    "observed, no scientific column-generation run was executed, and no "
    "mathematical claim is promoted."
)
NO_CLAIM = (
    "This source audit does not adjudicate any future G-0140 scientific "
    "manifest or result and does not establish family membership, family "
    "nonmembership, a MAX11 identity, a lower bound, unrestricted "
    "nonrepresentability, minimality, an all-n theorem, refereed status, "
    "formalization, or a Lean theorem."
)
EXPECTED_CHECKS = {
    "exact_named_binding_contract": True,
    "displaced_recursive_lookalikes_rejected": True,
    "correct_decoy_with_missing_named_binding_rejected": True,
    "unknown_envelope_fields_rejected": True,
    "audit_git_commit_rejected": True,
    "duplicate_json_keys_rejected": True,
    "trailing_json_data_rejected": True,
    "imported_exact_core_binding_verified": True,
    "future_input_gate_verified": True,
    "stage_c_snapshot_digest_contract_verified": True,
    "exact_column_generation_protocol_verified": True,
    "member_and_separator_fixtures_verified": True,
    "committed_blob_custody_verified": True,
    "producer_self_test_passed": True,
    "producer_static_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}
PROHIBITED_RELATIVE_PATHS = (
    Path("artifacts/math/G-0140/pool128_manifest_v1.json"),
    Path("artifacts/math/G-0140/pool128_global_replay_v1.json"),
    Path("artifacts/math/G-0140/pool128_coordinate_prices_v1.json"),
    Path("artifacts/math/G-0140/pool128_exact_rank_selection_v1.json"),
    Path("artifacts/math/G-0140/rank_aware_master_result_v1.json"),
)


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def git(root: Path, *arguments: str, binary: bool = False) -> bytes | str:
    process = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=True,
        capture_output=True,
        text=not binary,
    )
    return process.stdout if not binary else bytes(process.stdout)


def git_success(root: Path, *arguments: str) -> bool:
    return (
        subprocess.run(
            ["git", *arguments], cwd=root, check=False, capture_output=True
        ).returncode
        == 0
    )


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    require(
        specification is not None and specification.loader is not None,
        f"cannot load source module: {path}",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def top_level_functions(source: str) -> dict[str, str]:
    tree = ast.parse(source)
    return {
        node.name: ast.dump(node, include_attributes=False)
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def expect_rejected(
    action: Callable[[], object], error_type: type[BaseException], label: str
) -> None:
    try:
        action()
    except error_type:
        return
    raise AuditFailure(f"hostile source-audit control escaped: {label}")


def audit(root: Path, main_root: Path, prereg_commit: str) -> dict[str, Any]:
    root = root.resolve()
    main_root = main_root.resolve()
    subject_path = root / SUBJECT_REL
    selector_path = root / SELECTOR_REL
    core_path = root / CORE_REL
    result_path = root / G0135_RESULT_REL
    helper_path = root / HELPER_REL

    require(all(not (root / path).exists() for path in PROHIBITED_RELATIVE_PATHS),
            "a prohibited G-0140 manifest/result path is present")
    require(sha256_path(subject_path) == SUBJECT_SHA256, "subject working SHA drift")
    require(
        sha256_path(main_root / SUBJECT_REL) == SUBJECT_SHA256,
        "main-worktree subject SHA drift",
    )
    require(
        not str(git(main_root, "status", "--porcelain", "--", str(SUBJECT_REL))).strip(),
        "main-worktree subject has an uncommitted change",
    )

    committed_subject = git(
        root, "show", f"{TARGET_COMMIT}:{SUBJECT_REL.as_posix()}", binary=True
    )
    require(sha256_bytes(committed_subject) == SUBJECT_SHA256,
            "target-commit subject SHA drift")
    require(committed_subject == subject_path.read_bytes(),
            "commit object and sanitized working subject differ")
    require(
        str(git(root, "log", "-1", "--format=%H", TARGET_COMMIT, "--", str(SUBJECT_REL))).strip()
        == TARGET_COMMIT,
        "supplied commit is not the subject-changing commit",
    )
    require(
        str(git(root, "log", "-1", "--format=%H", prereg_commit, "--", str(SUBJECT_REL))).strip()
        == TARGET_COMMIT,
        "subject changed after the supplied commit",
    )
    target_blob = str(git(root, "rev-parse", f"{TARGET_COMMIT}:{SUBJECT_REL.as_posix()}")).strip()
    working_blob = str(git(root, "hash-object", str(SUBJECT_REL))).strip()
    require(target_blob == working_blob, "Git blob identity drift")
    require(git_success(root, "diff", "--quiet", TARGET_COMMIT, prereg_commit, "--", str(SUBJECT_REL)),
            "subject differs between frozen and preregistration commits")
    require(git_success(root, "merge-base", "--is-ancestor", TARGET_COMMIT, prereg_commit),
            "subject commit is not ancestor of preregistration")

    changed_paths = {
        line
        for line in str(git(root, "diff", "--name-only", f"{TARGET_COMMIT}^", TARGET_COMMIT)).splitlines()
        if line
    }
    require(changed_paths == {SUBJECT_REL.as_posix()},
            "subject-changing commit touched an unexpected path")
    old_source = str(git(root, "show", f"{TARGET_COMMIT}^:{SUBJECT_REL.as_posix()}"))
    new_source = subject_path.read_text(encoding="utf-8")
    old_functions = top_level_functions(old_source)
    new_functions = top_level_functions(new_source)
    require(set(old_functions) == set(new_functions), "top-level function census drift")
    changed_functions = {
        name for name in new_functions if new_functions[name] != old_functions[name]
    }
    require(
        changed_functions == {"input_snapshot_digest", "self_test"},
        f"unexpected changed functions: {sorted(changed_functions)}",
    )

    require(sha256_path(selector_path) == SELECTOR_SHA256, "selector SHA drift")
    require(sha256_path(core_path) == CORE_SHA256, "exact core SHA drift")
    require(sha256_path(result_path) == G0135_RESULT_SHA256,
            "G-0135 result binding SHA drift")
    dependency_commits: dict[str, str] = {}
    for label, path, expected in (
        ("selector", SELECTOR_REL, SELECTOR_SHA256),
        ("core", CORE_REL, CORE_SHA256),
    ):
        commit = str(git(root, "log", "-1", "--format=%H", prereg_commit, "--", str(path))).strip()
        blob = git(root, "show", f"{commit}:{path.as_posix()}", binary=True)
        require(sha256_bytes(blob) == expected, f"{label} committed SHA drift")
        require(blob == (root / path).read_bytes(), f"{label} working/blob drift")
        dependency_commits[label] = commit

    sys.dont_write_bytecode = True
    subject = load_module(subject_path, "g0162_subject")
    selector = load_module(selector_path, "g0162_selector")
    core = load_module(core_path, "g0162_core")
    helper = load_module(helper_path, "g0162_helper")

    require(subject.SOURCE_AUDIT_SCHEMA == RECEIPT_SCHEMA, "receipt schema drift")
    require(subject.SOURCE_AUDIT_CLAIM == CLAIM, "claim constant drift")
    require(subject.SOURCE_AUDIT_NO_CLAIM == NO_CLAIM, "no-claim constant drift")
    require(subject.SOURCE_AUDIT_CHECKS == EXPECTED_CHECKS,
            "required-check set/value drift")
    require(set(subject.SOURCE_AUDIT_CHECKS) == set(EXPECTED_CHECKS),
            "required-check key set drift")
    require(subject.SELECTOR_SHA256 == SELECTOR_SHA256, "source selector pin drift")
    require(subject.G0135_MASTER_SHA256 == CORE_SHA256, "source core pin drift")
    require(subject.G0135_RESULT_SHA256 == G0135_RESULT_SHA256,
            "source G-0135 result pin drift")

    snapshot = {"b": "2" * 64, "a": "1" * 64}
    tab_bytes = b"a\t" + b"1" * 64 + b"\n" + b"b\t" + b"2" * 64 + b"\n"
    nul_bytes = b"a\0" + b"1" * 64 + b"\n" + b"b\0" + b"2" * 64 + b"\n"
    tab_digest = sha256_bytes(tab_bytes)
    nul_digest = sha256_bytes(nul_bytes)
    require(
        tab_digest == "9973c87a16e71a92d98c70278c07a46a3d224e103e643b2bc359e476dfc31fb9",
        "independent TAB fixture digest drift",
    )
    require(
        nul_digest == "ab7b0f7fcd820a946bfa33d060317501b816a6aceb55d476c6379292ae7819dc",
        "independent NUL fixture digest drift",
    )
    require(subject.input_snapshot_digest(snapshot) == tab_digest,
            "subject does not implement the TAB fixture")
    require(selector.input_snapshot_digest(snapshot) == tab_digest,
            "selector does not implement the TAB fixture")
    require(subject.input_snapshot_digest(snapshot) != nul_digest,
            "retired NUL fixture was accepted")

    binding = (SUBJECT_REL.as_posix(), SUBJECT_SHA256)
    audit_fixture = {
        "schema": subject.SOURCE_AUDIT_SCHEMA,
        "verdict": "PASS",
        "result": subject.SOURCE_AUDIT_RESULT,
        "evidence_class": subject.SOURCE_AUDIT_EVIDENCE,
        "claim_boundary": subject.SOURCE_AUDIT_CLAIM,
        "reviewer": {
            "agent_name": "FreshReviewer",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": True,
            "fresh_context": True,
        },
        "preregistration": {
            "path": PREREG_REL.as_posix(),
            "sha256": "1" * 64,
            "git_commit": prereg_commit,
            "committed_and_pushed_before_subject_source_inspection": True,
            "committed_and_pushed_before_runtime_checks": True,
        },
        "subject": {
            "git_commit": TARGET_COMMIT,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
            "bindings": {
                "master_source": {"path": binding[0], "sha256": binding[1]}
            },
        },
        "required_checks": copy.deepcopy(subject.SOURCE_AUDIT_CHECKS),
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "no_claim": subject.SOURCE_AUDIT_NO_CLAIM,
    }

    def validate(value: dict[str, Any]) -> None:
        selector.validate_source_audit_shape(
            value,
            schema=subject.SOURCE_AUDIT_SCHEMA,
            claim_boundary=subject.SOURCE_AUDIT_CLAIM,
            no_claim=subject.SOURCE_AUDIT_NO_CLAIM,
            required_checks=subject.SOURCE_AUDIT_CHECKS,
            preregistration_path=PREREG_REL.as_posix(),
            named_bindings={"master_source": binding},
            subject_commit=TARGET_COMMIT,
        )

    validate(audit_fixture)
    hostile_count = 0

    def hostile(label: str, mutate: Callable[[dict[str, Any]], None]) -> None:
        nonlocal hostile_count
        mutant = copy.deepcopy(audit_fixture)
        mutate(mutant)
        expect_rejected(lambda: validate(mutant), selector.SelectorError, label)
        hostile_count += 1

    hostile("wrong named binding", lambda value: value["subject"]["bindings"]["master_source"].update(sha256="f" * 64))

    def displace(value: dict[str, Any]) -> None:
        value["recursive_decoy"] = value["subject"].pop("bindings")

    hostile("displaced recursive lookalike", displace)

    def decoy(value: dict[str, Any]) -> None:
        item = value["subject"]["bindings"].pop("master_source")
        value["subject"]["bindings"]["master_source_decoy"] = item

    hostile("correct decoy with missing named binding", decoy)
    hostile("unknown envelope field", lambda value: value.update(unknown=True))
    hostile("audit_git_commit field", lambda value: value.update(audit_git_commit="0" * 40))
    hostile("wrong schema", lambda value: value.update(schema="lookalike"))
    hostile("wrong verdict", lambda value: value.update(verdict="FAIL"))
    hostile("wrong result", lambda value: value.update(result="LOOKALIKE"))
    hostile("wrong evidence", lambda value: value.update(evidence_class="T2"))
    hostile("wrong claim", lambda value: value.update(claim_boundary=""))
    hostile("wrong no-claim", lambda value: value.update(no_claim=""))
    hostile("scientific manifest observed", lambda value: value.update(scientific_manifest_observed=True))
    hostile("scientific input observed", lambda value: value.update(scientific_input_observed=True))
    hostile("scientific output observed", lambda value: value.update(scientific_output_observed=True))
    hostile("scientific replay run", lambda value: value.update(scientific_replay_run=True))
    hostile("reviewer not fresh", lambda value: value["reviewer"].update(fresh_context=False))
    hostile("preregistration not pre-inspection", lambda value: value["preregistration"].update(committed_and_pushed_before_subject_source_inspection=False))
    hostile("wrong subject commit", lambda value: value["subject"].update(git_commit="0" * 40))
    hostile("working/blob equality false", lambda value: value["subject"].update(commit_object_and_working_bytes_equal_for_all_bindings=False))
    hostile("missing required check", lambda value: value["required_checks"].pop("stage_c_snapshot_digest_contract_verified"))
    hostile("extra required check", lambda value: value["required_checks"].update(extra=True))
    hostile("false required check", lambda value: value["required_checks"].update(stage_c_snapshot_digest_contract_verified=False))
    hostile("integer required check", lambda value: value["required_checks"].update(stage_c_snapshot_digest_contract_verified=1))

    expect_rejected(
        lambda: selector.strict_json_text('{"x":1,"x":2}', "duplicate fixture"),
        selector.SelectorError,
        "duplicate JSON keys",
    )
    expect_rejected(
        lambda: selector.strict_json_text('{"x":1}\n{"y":2}', "trailing fixture"),
        selector.SelectorError,
        "trailing JSON data",
    )
    hostile_count += 2

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
        and member.get("selected_sequences") == [0, 1]
        and member.get("replay_receipt", {}).get("rational_all_rows_replayed") is True
        and member.get("replay_receipt", {}).get("integer_all_rows_replayed") is True,
        "independent member fixture failed",
    )

    nonmember_columns = [[1, 0]]
    nonmember_target = [0, 1]
    nonmember = core.exact_column_generation(
        helper=helper,
        target=nonmember_target,
        seed_sequences=[0],
        column_loader=nonmember_columns.__getitem__,
        record_count=1,
        expected_initial_rank=1,
        prior_target_scale=7,
    )
    separator = [int(value) for value in nonmember["primitive_integer_separator"]]
    require(
        nonmember.get("branch") == "NONMEMBER"
        and nonmember.get("complete_separator_replay", {}).get(
            "all_family_columns_exactly_annihilated"
        )
        is True
        and sum(a * b for a, b in zip(separator, nonmember_columns[0], strict=True)) == 0
        and sum(a * b for a, b in zip(separator, nonmember_target, strict=True)) != 0,
        "independent separator fixture failed",
    )

    subject.self_test()
    static = subject.static_preflight()
    require(
        static.get("result") == "G0140_RANK_AWARE_MASTER_STATIC_PREFLIGHT_PASS"
        and static.get("future_inputs_present")
        == {
            "manifest": False,
            "stage_a": False,
            "stage_b": False,
            "stage_c": False,
            "source_audit": False,
        }
        and static.get("all_future_inputs_present") is False
        and static.get("scientific_column_generation_run") is False
        and static.get("scientific_result_written") is False,
        "sanitized static-preflight contract failed",
    )
    require(all(not (root / path).exists() for path in PROHIBITED_RELATIVE_PATHS),
            "a prohibited G-0140 path was created")

    checks = copy.deepcopy(EXPECTED_CHECKS)
    require(checks == subject.SOURCE_AUDIT_CHECKS,
            "emitted required-check set differs from frozen source")
    return {
        "schema": "g0162-independent-source-audit-tests-v1",
        "subject": {
            "path": SUBJECT_REL.as_posix(),
            "git_commit": TARGET_COMMIT,
            "git_blob": target_blob,
            "sha256": SUBJECT_SHA256,
            "changed_functions": sorted(changed_functions),
        },
        "dependencies": {
            "selector": {
                "path": SELECTOR_REL.as_posix(),
                "sha256": SELECTOR_SHA256,
                "git_commit": dependency_commits["selector"],
            },
            "exact_core": {
                "path": CORE_REL.as_posix(),
                "sha256": CORE_SHA256,
                "git_commit": dependency_commits["core"],
            },
        },
        "snapshot_digest_fixture": {
            "tab_positive_sha256": tab_digest,
            "nul_negative_sha256": nul_digest,
            "subject_equals_imported_selector": True,
        },
        "hostile_source_audit_controls_rejected": hostile_count,
        "prohibited_paths_absent": [path.as_posix() for path in PROHIBITED_RELATIVE_PATHS],
        "required_checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--main-root", type=Path, required=True)
    parser.add_argument("--prereg-commit", required=True)
    args = parser.parse_args()
    print(
        json.dumps(
            audit(args.root, args.main_root, args.prereg_commit),
            sort_keys=True,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
