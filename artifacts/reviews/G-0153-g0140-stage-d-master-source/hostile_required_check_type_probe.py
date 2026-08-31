#!/usr/bin/env python3
"""Minimal G-0153 counterexample: JSON integer 1 escapes a Boolean audit field."""

from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
SUBJECT_REL = "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py"
SELECTOR_REL = (
    "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
PREREG_REL = (
    "artifacts/reviews/G-0153-g0140-stage-d-master-source/PREREGISTRATION.md"
)
SUBJECT_COMMIT = "5b9fb81168d1a1f964b123b31edc3763439ecd7b"
SUBJECT_SHA256 = "aa7ea5ca9174667ecae0c5e2d28d50e616b2da24d57f62d2026150c67f244935"
SELECTOR_SHA256 = "3f2dde3fdf2f458adc90f5d4e8ed2e5338013c95bab8b296d5136fb529a06838"
PREREG_COMMIT = "af02117648e607895b6aba3ad5dddc1bfa07612d"
MUTATED_CHECK = "exact_named_binding_contract"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def git_blob(relative_path: str) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{SUBJECT_COMMIT}:{relative_path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        raise RuntimeError(f"frozen Git blob unavailable: {relative_path}")
    return process.stdout


def subject_constants(source: bytes) -> dict[str, Any]:
    wanted = {
        "SOURCE_AUDIT_SCHEMA",
        "SOURCE_AUDIT_CLAIM",
        "SOURCE_AUDIT_NO_CLAIM",
        "SOURCE_AUDIT_CHECKS",
    }
    result: dict[str, Any] = {}
    for node in ast.parse(source.decode("utf-8")).body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id in wanted
        ):
            result[node.targets[0].id] = ast.literal_eval(node.value)
    if set(result) != wanted:
        raise RuntimeError("frozen source constants unavailable")
    return result


def load_selector(source: bytes) -> Any:
    with tempfile.TemporaryDirectory(prefix="g0153-frozen-selector-") as raw:
        path = Path(raw) / SELECTOR_REL
        path.parent.mkdir(parents=True)
        path.write_bytes(source)
        specification = importlib.util.spec_from_file_location("g0153_type_probe", path)
        if specification is None or specification.loader is None:
            raise RuntimeError("selector import unavailable")
        module = importlib.util.module_from_spec(specification)
        specification.loader.exec_module(module)
        return module


def leaf_differences(left: Any, right: Any, pointer: str = "") -> list[str]:
    if isinstance(left, dict) and isinstance(right, dict) and set(left) == set(right):
        return [
            difference
            for key in sorted(left)
            for difference in leaf_differences(left[key], right[key], f"{pointer}/{key}")
        ]
    if isinstance(left, list) and isinstance(right, list) and len(left) == len(right):
        return [
            difference
            for index, (left_item, right_item) in enumerate(zip(left, right, strict=True))
            for difference in leaf_differences(
                left_item, right_item, f"{pointer}/{index}"
            )
        ]
    return [pointer] if type(left) is not type(right) or left != right else []


def validate(selector: Any, receipt: dict[str, Any], constants: dict[str, Any]) -> None:
    binding = (SUBJECT_REL, SUBJECT_SHA256)
    selector.validate_source_audit_shape(
        receipt,
        schema=constants["SOURCE_AUDIT_SCHEMA"],
        claim_boundary=constants["SOURCE_AUDIT_CLAIM"],
        no_claim=constants["SOURCE_AUDIT_NO_CLAIM"],
        required_checks=constants["SOURCE_AUDIT_CHECKS"],
        preregistration_path=PREREG_REL,
        named_bindings={"master_source": binding},
        subject_commit=SUBJECT_COMMIT,
    )


def main() -> int:
    prereg_path = ROOT / PREREG_REL
    subject_source = git_blob(SUBJECT_REL)
    selector_source = git_blob(SELECTOR_REL)
    if (
        sha256_bytes(subject_source) != SUBJECT_SHA256
        or sha256_bytes(selector_source) != SELECTOR_SHA256
    ):
        raise RuntimeError("frozen source/import custody drift")
    constants = subject_constants(subject_source)
    checks = constants["SOURCE_AUDIT_CHECKS"]
    if not isinstance(checks, dict) or checks.get(MUTATED_CHECK) is not True:
        raise RuntimeError("expected Boolean source contract unavailable")
    binding = {"path": SUBJECT_REL, "sha256": SUBJECT_SHA256}
    baseline = {
        "schema": constants["SOURCE_AUDIT_SCHEMA"],
        "verdict": "PASS",
        "result": "SOURCE_CUSTODY_AUDIT_PASS_T1",
        "evidence_class": "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT",
        "claim_boundary": constants["SOURCE_AUDIT_CLAIM"],
        "reviewer": {
            "agent_name": "GentlePine",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": True,
            "fresh_context": True,
        },
        "preregistration": {
            "path": PREREG_REL,
            "sha256": sha256_bytes(prereg_path.read_bytes()),
            "git_commit": PREREG_COMMIT,
            "committed_and_pushed_before_subject_source_inspection": True,
            "committed_and_pushed_before_runtime_checks": True,
        },
        "subject": {
            "git_commit": SUBJECT_COMMIT,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
            "bindings": {"master_source": binding},
        },
        "required_checks": checks,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "no_claim": constants["SOURCE_AUDIT_NO_CLAIM"],
    }
    selector = load_selector(selector_source)
    parsed_baseline = selector.strict_json_text(
        json.dumps(baseline), "G-0153 Boolean baseline"
    )
    validate(selector, parsed_baseline, constants)

    mutant = copy.deepcopy(baseline)
    mutant["required_checks"][MUTATED_CHECK] = 1
    expected_pointer = f"/required_checks/{MUTATED_CHECK}"
    differences = leaf_differences(baseline, mutant)
    if differences != [expected_pointer]:
        raise RuntimeError(f"counterexample is not one-field minimal: {differences}")
    parsed_mutant = selector.strict_json_text(
        json.dumps(mutant), "G-0153 hostile integer mutant"
    )
    accepted = True
    error = None
    try:
        validate(selector, parsed_mutant, constants)
    except selector.SelectorError as caught:
        accepted = False
        error = str(caught)

    result = {
        "verdict": "FAIL" if accepted else "PASS",
        "reason": "hostile JSON integer accepted as required Boolean" if accepted else None,
        "subject_git_commit": SUBJECT_COMMIT,
        "subject_path": SUBJECT_REL,
        "subject_sha256": SUBJECT_SHA256,
        "selector_sha256": SELECTOR_SHA256,
        "one_binding_count": len(mutant["subject"]["bindings"]),
        "mutated_json_pointer": expected_pointer,
        "baseline_json_value": True,
        "baseline_python_type": type(
            parsed_baseline["required_checks"][MUTATED_CHECK]
        ).__name__,
        "mutant_json_value": 1,
        "mutant_python_type": type(
            parsed_mutant["required_checks"][MUTATED_CHECK]
        ).__name__,
        "differing_leaf_count": len(differences),
        "hostile_fixture_accepted": accepted,
        "validator_error": error,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
    }
    print(json.dumps(result, sort_keys=True))
    return 1 if accepted else 0


if __name__ == "__main__":
    raise SystemExit(main())
