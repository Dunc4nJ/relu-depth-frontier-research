#!/usr/bin/env python3
"""Source-only hostile controls for the frozen G-0155 audit target.

This verifier reads only frozen source/core bindings and Git custody metadata.
It does not read G-0140 scientific manifests, inputs, or outputs and exposes no
scientific execution mode.
"""

from __future__ import annotations

import copy
import ast
import hashlib
import importlib.util
import inspect
import json
import subprocess
import textwrap
from collections.abc import Callable
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
FROZEN_COMMIT = "69a3449c7bc291f283c10c669e5d39f2a1212782"
SUBJECT_PATH = "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py"
SUBJECT_SHA256 = "6112c55f943c20acd80402a9800db581c1ee6d5caf35c2f418d2a52cf09ad03e"
SELECTOR_PATH = (
    "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
SELECTOR_SHA256 = "9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0"
CORE_PATH = "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py"
CORE_SHA256 = "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"
CORE_RESULT_PATH = "artifacts/math/G-0135/full_family_master_result_v3.json"
CORE_RESULT_SHA256 = (
    "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8"
)
HELPER_PATH = "artifacts/math/G-0117/fresh_q_cegis_exact.py"
HELPER_SHA256 = "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281"
PREREG_PATH = (
    "artifacts/reviews/G-0155-g0140-stage-d-master-final2-source/"
    "PREREGISTRATION.md"
)
RECEIPT_PATH = (
    "artifacts/reviews/G-0155-g0140-stage-d-master-final2-source/"
    "SOURCE_AUDIT_RECEIPT.json"
)
PREREG_SHA256 = "240d471362dabf1a183ae25b11c85fd8f3dfce7594987f3ab87f1bdd70ddad44"
PREREG_COMMIT = "317b4af809c154a18ddc402bc838fb9d2e4d93ff"

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
    "exact_column_generation_protocol_verified": True,
    "member_and_separator_fixtures_verified": True,
    "committed_blob_custody_verified": True,
    "producer_self_test_passed": True,
    "producer_static_preflight_passed": True,
    "prohibited_scientific_modes_not_run": True,
}

EXPECTED_CLAIM = (
    "T1 source/custody clearance for the exact frozen G-0140 reopened-master "
    "producer bytes only; no scientific manifest, input, or output was "
    "observed, no scientific column-generation run was executed, and no "
    "mathematical claim is promoted."
)
EXPECTED_NO_CLAIM = (
    "This source audit does not adjudicate any future G-0140 scientific "
    "manifest or result and does not establish family membership, family "
    "nonmembership, a MAX11 identity, a lower bound, unrestricted "
    "nonrepresentability, minimality, an all-n theorem, refereed status, "
    "formalization, or a Lean theorem."
)


class AuditFailure(RuntimeError):
    """A source-only hostile control escaped or a frozen binding drifted."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_frozen(path: str) -> bytes:
    process = subprocess.run(
        ["git", "show", f"{FROZEN_COMMIT}:{path}"],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(process.returncode == 0, f"frozen blob unavailable: {path}")
    return process.stdout


def verify_binding(path: str, expected: str) -> None:
    frozen = read_frozen(path)
    working = (ROOT / path).read_bytes()
    require(sha256_bytes(frozen) == expected, f"frozen digest drift: {path}")
    require(sha256_bytes(working) == expected, f"working digest drift: {path}")
    require(frozen == working, f"frozen/working byte mismatch: {path}")


def load_module(path: str, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, ROOT / path)
    require(
        specification is not None and specification.loader is not None,
        f"cannot import audited source: {path}",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def called_names(source: str) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(ast.parse(textwrap.dedent(source))):
        if not isinstance(node, ast.Call):
            continue
        if isinstance(node.func, ast.Name):
            names.add(node.func.id)
        elif isinstance(node.func, ast.Attribute):
            names.add(node.func.attr)
    return names


def fixture(subject: Any) -> dict[str, Any]:
    return {
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
            "path": PREREG_PATH,
            "sha256": "1" * 64,
            "git_commit": "2" * 40,
            "committed_and_pushed_before_subject_source_inspection": True,
            "committed_and_pushed_before_runtime_checks": True,
        },
        "subject": {
            "git_commit": FROZEN_COMMIT,
            "commit_object_and_working_bytes_equal_for_all_bindings": True,
            "bindings": {
                "master_source": {
                    "path": SUBJECT_PATH,
                    "sha256": SUBJECT_SHA256,
                }
            },
        },
        "required_checks": copy.deepcopy(EXPECTED_CHECKS),
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
        "no_claim": subject.SOURCE_AUDIT_NO_CLAIM,
    }


def main() -> int:
    pins = {
        SUBJECT_PATH: SUBJECT_SHA256,
        SELECTOR_PATH: SELECTOR_SHA256,
        CORE_PATH: CORE_SHA256,
        CORE_RESULT_PATH: CORE_RESULT_SHA256,
        HELPER_PATH: HELPER_SHA256,
    }
    for path, expected in pins.items():
        verify_binding(path, expected)

    selector = load_module(SELECTOR_PATH, "g0155_source_only_selector")
    subject = load_module(SUBJECT_PATH, "g0155_source_only_subject")
    core = load_module(CORE_PATH, "g0155_source_only_core")

    require(subject.SELECTOR_SHA256 == SELECTOR_SHA256, "subject selector pin drift")
    require(subject.G0135_MASTER_SHA256 == CORE_SHA256, "subject core pin drift")
    require(
        subject.G0135_RESULT_SHA256 == CORE_RESULT_SHA256,
        "subject core-result pin drift",
    )
    require(selector.G0135_SOURCE_SHA256 == CORE_SHA256, "selector core pin drift")
    require(
        selector.G0135_RESULT_SHA256 == CORE_RESULT_SHA256,
        "selector core-result pin drift",
    )
    require(selector.G0117_EXACT_SHA256 == HELPER_SHA256, "selector helper pin drift")
    require(core.G0117_EXACT_SHA256 == HELPER_SHA256, "core helper pin drift")
    require(subject.SOURCE_AUDIT_CHECKS == EXPECTED_CHECKS, "check-name drift")
    require(subject.SOURCE_AUDIT_CLAIM == EXPECTED_CLAIM, "claim-boundary drift")
    require(subject.SOURCE_AUDIT_NO_CLAIM == EXPECTED_NO_CLAIM, "no-claim drift")

    named = {"master_source": (SUBJECT_PATH, SUBJECT_SHA256)}

    def validate(value: dict[str, Any]) -> None:
        selector.validate_source_audit_shape(
            value,
            schema=subject.SOURCE_AUDIT_SCHEMA,
            claim_boundary=EXPECTED_CLAIM,
            no_claim=EXPECTED_NO_CLAIM,
            required_checks=EXPECTED_CHECKS,
            preregistration_path=PREREG_PATH,
            named_bindings=named,
            subject_commit=FROZEN_COMMIT,
        )

    good = fixture(subject)
    parsed_good = selector.strict_json_text(
        json.dumps(good, separators=(",", ":")), "positive fixture"
    )
    require(isinstance(parsed_good, dict), "positive fixture did not parse as object")
    validate(parsed_good)

    rejected: list[str] = []

    def reject(label: str, mutate: Callable[[dict[str, Any]], None]) -> None:
        mutant = copy.deepcopy(good)
        mutate(mutant)
        try:
            validate(mutant)
        except selector.SelectorError:
            rejected.append(label)
            return
        raise AuditFailure(f"hostile validator mutant escaped: {label}")

    def set_nested(value: dict[str, Any], path: tuple[str, ...], hostile: Any) -> None:
        destination: dict[str, Any] = value
        for component in path[:-1]:
            destination = destination[component]
        destination[path[-1]] = hostile

    true_boolean_paths = [
        *(("required_checks", key) for key in EXPECTED_CHECKS),
        ("reviewer", "same_model_lineage"),
        ("reviewer", "fresh_context"),
        (
            "preregistration",
            "committed_and_pushed_before_subject_source_inspection",
        ),
        ("preregistration", "committed_and_pushed_before_runtime_checks"),
        ("subject", "commit_object_and_working_bytes_equal_for_all_bindings"),
    ]
    true_hostiles = (
        ("integer_1", 1),
        ("float_1", 1.0),
        ("string_true", "true"),
        ("null", None),
        ("array", []),
        ("object", {}),
        ("opposite_boolean", False),
    )
    for path in true_boolean_paths:
        for type_label, hostile in true_hostiles:
            reject(
                f"true_boolean:{'.'.join(path)}:{type_label}",
                lambda value, path=path, hostile=hostile: set_nested(
                    value, path, hostile
                ),
            )

    false_boolean_paths = [
        ("scientific_manifest_observed",),
        ("scientific_input_observed",),
        ("scientific_output_observed",),
        ("scientific_replay_run",),
    ]
    false_hostiles = (
        ("integer_0", 0),
        ("float_0", 0.0),
        ("string_false", "false"),
        ("null", None),
        ("array", []),
        ("object", {}),
        ("opposite_boolean", True),
    )
    for path in false_boolean_paths:
        for type_label, hostile in false_hostiles:
            reject(
                f"false_boolean:{'.'.join(path)}:{type_label}",
                lambda value, path=path, hostile=hostile: set_nested(
                    value, path, hostile
                ),
            )

    reject("unknown_envelope", lambda value: value.__setitem__("unknown", True))
    reject(
        "audit_git_commit",
        lambda value: value.__setitem__("audit_git_commit", "0" * 40),
    )
    reject(
        "missing_required_check",
        lambda value: value["required_checks"].pop("producer_self_test_passed"),
    )
    reject(
        "unknown_required_check",
        lambda value: value["required_checks"].__setitem__("lookalike", True),
    )
    reject(
        "wrong_subject_commit",
        lambda value: value["subject"].__setitem__("git_commit", "0" * 40),
    )

    def displace(value: dict[str, Any]) -> None:
        bindings = value["subject"].pop("bindings")
        value["unrelated_receipt_lookalikes"] = bindings

    reject("displaced_recursive_lookalike", displace)

    def decoy(value: dict[str, Any]) -> None:
        binding = value["subject"]["bindings"].pop("master_source")
        value["subject"]["correct_master_source_decoy"] = binding

    reject("correct_decoy_missing_named_binding", decoy)
    for label, raw in (
        ("duplicate_json_key", '{"same":true,"same":false}'),
        ("trailing_json_data", '{"first":true}{"second":false}'),
    ):
        try:
            selector.strict_json_text(raw, label)
        except selector.SelectorError:
            rejected.append(label)
        else:
            raise AuditFailure(f"hostile JSON mutant escaped: {label}")

    audit_wrapper_source = inspect.getsource(subject.validate_source_audit)
    static_source = inspect.getsource(subject.static_preflight)
    prepare_source = inspect.getsource(subject.prepare)
    loader_source = inspect.getsource(subject.with_column_loader)
    run_source = inspect.getsource(subject.run)
    self_test_source = inspect.getsource(subject.self_test)
    core_source = inspect.getsource(core.exact_column_generation)
    separator_source = inspect.getsource(core.separator_scan)

    require(
        "all(type(value) is bool for value in observed_checks.values())"
        in audit_wrapper_source,
        "subject wrapper lacks strict required-check boolean test",
    )
    require(
        "stage_c_path.resolve() == STAGE_C_PATH.resolve()" in prepare_source
        and "selector.load_validated_future_inputs(" in prepare_source
        and "validate_source_audit(selector, prepared[\"snapshot\"])" in prepare_source,
        "future input/source-audit gate drift",
    )
    require(
        "self_test()" in static_source
        and "git_commit_for_path(SCRIPT)" in static_source
        and "scientific_column_generation_run\": False" in static_source
        and "scientific_result_written\": False" in static_source,
        "static preflight positive/source-only contract drift",
    )
    forbidden_static_calls = {
        "prepare",
        "preflight",
        "run",
        "with_column_loader",
        "load_validated_future_inputs",
        "exact_column_generation",
    }
    observed_static_calls = called_names(static_source)
    require(
        forbidden_static_calls.isdisjoint(observed_static_calls),
        "static preflight calls forbidden scientific path: "
        f"{sorted(forbidden_static_calls & observed_static_calls)}",
    )
    require(
        "all_pool_rows = prepared[\"stage_b_rows\"]" in loader_source
        and "selected_rows = [prepared[\"stage_b_rows\"][index]" in loader_source
        and "column.extend(int(row[sequence]) for row in all_pool_rows)" in loader_source
        and "column.extend(int(row[sequence]) for row in selected_rows)" in loader_source
        and "selector.exact_rank_selection(" in loader_source,
        "rank-aware all-row/selected-row loader protocol drift",
    )
    require(
        "core.exact_column_generation(" in run_source
        and "record_count=RECORDS" in run_source
        and "seed_sequences=state[\"seed\"]" in run_source
        and "decision = with_column_loader(state, solve)" in run_source,
        "subject exact column-generation dispatch drift",
    )
    require(
        "for iteration in range(row_count - expected_initial_rank + 1)" in core_source
        and "matrix = helper.qmatrix(integer_rows)" in core_source
        and "augmented_rank in {rank, rank + 1}" in core_source
        and core_source.count("separator_scan(") >= 3
        and '"all_family_columns_exactly_annihilated": True' in core_source,
        "imported exact-Q terminal protocol drift",
    )
    require(
        "for sequence in range(record_count)" in separator_source
        and "columns_scanned == record_count" in separator_source,
        "complete separator census drift",
    )
    require(
        self_test_source.count("core.exact_column_generation(") == 2
        and "source-audit integer boolean fixture escaped" in self_test_source
        and "source-audit displaced-binding fixture escaped" in self_test_source
        and "synthetic reopened member route drift" in self_test_source
        and "synthetic terminal separator route drift" in self_test_source,
        "producer hostile member/separator fixture contract drift",
    )

    actual_receipt = selector.load_json(ROOT / RECEIPT_PATH)
    validate(actual_receipt)
    require(
        actual_receipt["reviewer"]["agent_name"] == "CoralRabbit"
        and actual_receipt["preregistration"]["sha256"] == PREREG_SHA256
        and actual_receipt["preregistration"]["git_commit"] == PREREG_COMMIT
        and sha256_bytes((ROOT / PREREG_PATH).read_bytes()) == PREREG_SHA256,
        "actual receipt reviewer/preregistration binding drift",
    )
    prereg_log = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", PREREG_PATH],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    require(prereg_log == PREREG_COMMIT, "preregistration Git commit drift")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", FROZEN_COMMIT, PREREG_COMMIT],
        cwd=ROOT,
        check=False,
        capture_output=True,
    )
    require(ancestry.returncode == 0, "subject -> preregistration ancestry drift")

    evidence = {
        "schema": "max11-g0155-g0140-stage-d-source-audit-tests-v1",
        "frozen_commit": FROZEN_COMMIT,
        "subject": {"path": SUBJECT_PATH, "sha256": SUBJECT_SHA256},
        "checks": {
            "frozen_blob_and_worktree_identity": True,
            "declared_import_pins": True,
            "validator_positive_control": True,
            "strict_boolean_mutants_rejected": True,
            "material_fail_open_mutants_rejected": True,
            "future_mode_separation_static": True,
            "exact_core_protocol_static": True,
            "member_separator_fixture_contract_static": True,
            "actual_receipt_exact_shape": True,
        },
        "rejected_mutant_count": len(rejected),
        "rejected_mutants": rejected,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
