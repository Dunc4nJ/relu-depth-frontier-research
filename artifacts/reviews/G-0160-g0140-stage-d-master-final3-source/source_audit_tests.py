#!/usr/bin/env python3
"""Source-only hostile controls for the exact frozen G-0160 Stage-D subject.

The harness inspects source, opaque hash bindings, and Git custody only.  It
never parses a scientific JSON file and exposes no scientific execution mode.
Current G-0140 scientific manifest/result paths are absent from every runtime
fixture.
"""

from __future__ import annotations

import argparse
import ast
import copy
import hashlib
import importlib.util
import inspect
import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
PYTHON = ROOT / ".venv/bin/python"

SUBJECT_PATH = "artifacts/math/G-0140/stage_d_master/rank_aware_master_v1.py"
SUBJECT_SHA256 = "d5b5d96ccf36cf4b76ec851480b8097fb6d95e38d96e635fda60250e71835732"
SUBJECT_COMMIT = "2aed47a3b359c0a6625a8f8fd58225069d6c1498"
SUBJECT_BLOB = "69c774cb86f79ed199eeb78344bf24233518dcc1"

SELECTOR_PATH = (
    "artifacts/math/G-0140/stage_c_selector/complete_matrix_rank_selector_v1.py"
)
SELECTOR_SHA256 = "f6cbb7b83f25ce88b6448ab363eb73bcb7bc4cb8427c167009c98ae0a06a60d3"
SELECTOR_COMMIT = "f56b92ab8e13401ccd8a63d8c24137e16450d5ef"
SELECTOR_BLOB = "e997c97b9a9b38e87034ebffc6bd55c8fce7182a"
STALE_SELECTOR_SHA256 = (
    "9c5e0e7e40c7f12b8d299148fa7f9a942207eacdc26aa6662c59bb86f481b9b0"
)

CORE_PATH = "artifacts/math/G-0135/stage_c_master/full_family_master_v3.py"
CORE_SHA256 = "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"
CORE_RESULT_PATH = "artifacts/math/G-0135/full_family_master_result_v3.json"
CORE_RESULT_SHA256 = (
    "ef1cbdf3abfd32326c35e511057a3450b4942ae9aa901ead8e8b86133c564db8"
)
HELPER_PATH = "artifacts/math/G-0117/fresh_q_cegis_exact.py"
HELPER_SHA256 = "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281"

PREREG_PATH = (
    "artifacts/reviews/G-0160-g0140-stage-d-master-final3-source/"
    "PREREGISTRATION.md"
)
PREREG_SHA256 = "cc14bc321ed9bdbf24b72e721b5d2ff89ae92b66dce1fae6d05f95c38cf3e5b9"
PREREG_COMMIT = "5f43f7971a497bde94d9a9c472403b03f4bec73e"
RECEIPT_PATH = (
    "artifacts/reviews/G-0160-g0140-stage-d-master-final3-source/"
    "SOURCE_AUDIT_RECEIPT.json"
)

EXPECTED_SCHEMA = "max11-g0160-g0140-stage-d-master-final3-source-audit-v1"
EXPECTED_RESULT = "SOURCE_CUSTODY_AUDIT_PASS_T1"
EXPECTED_EVIDENCE = "T1_SAME_LINEAGE_OUTCOME_BLIND_SOURCE_AUDIT"
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

RUNTIME_BINDINGS = (
    SUBJECT_PATH,
    SELECTOR_PATH,
    CORE_PATH,
    CORE_RESULT_PATH,
    HELPER_PATH,
)
FORBIDDEN_G0140_RUNTIME_PATHS = (
    "artifacts/math/G-0140/pool128_manifest_v1.json",
    "artifacts/math/G-0140/pool128_global_replay_v1.json",
    "artifacts/math/G-0140/pool128_coordinate_prices_v1.json",
    "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json",
    "artifacts/math/G-0140/rank_aware_master_result_v1.json",
    RECEIPT_PATH,
)


class AuditFailure(RuntimeError):
    """A source-only control escaped or an exact custody binding drifted."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def run(
    command: Sequence[str | Path],
    *,
    cwd: Path = ROOT,
    check: bool = False,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    process = subprocess.run(
        [str(item) for item in command],
        cwd=cwd,
        check=False,
        capture_output=True,
        text=True,
        env=env,
    )
    if check and process.returncode != 0:
        raise AuditFailure(
            f"command failed ({process.returncode}): {' '.join(map(str, command))}\n"
            f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
        )
    return process


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_stdout(*arguments: str) -> str:
    return run(("git", *arguments), check=True).stdout.strip()


def verify_binding(
    path: str,
    expected_sha256: str,
    *,
    expected_commit: str | None = None,
    expected_blob: str | None = None,
) -> dict[str, str]:
    working = (ROOT / path).read_bytes()
    head = run(("git", "show", f"HEAD:{path}"), check=True).stdout.encode()
    # Git's text-mode decoding above is safe for these UTF-8 source bindings.
    if path == CORE_RESULT_PATH:
        head = run(("git", "show", f"HEAD:{path}"), check=True).stdout.encode()
    require(sha256_bytes(working) == expected_sha256, f"working digest drift: {path}")
    require(sha256_bytes(head) == expected_sha256, f"HEAD digest drift: {path}")
    require(working == head, f"HEAD/working byte mismatch: {path}")
    last_commit = git_stdout("log", "-1", "--format=%H", "--", path)
    if expected_commit is not None:
        require(last_commit == expected_commit, f"last-modifying commit drift: {path}")
        committed = run(("git", "show", f"{expected_commit}:{path}"), check=True)
        committed_bytes = committed.stdout.encode()
        require(committed_bytes == working, f"commit/working byte mismatch: {path}")
    blob = git_stdout("hash-object", path)
    tracked_blob = git_stdout("rev-parse", f"HEAD:{path}")
    require(blob == tracked_blob, f"Git blob identity drift: {path}")
    if expected_blob is not None:
        require(blob == expected_blob, f"expected Git blob drift: {path}")
    return {"path": path, "sha256": expected_sha256, "commit": last_commit, "blob": blob}


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


def function_ast(source: str, name: str) -> str:
    tree = ast.parse(source)
    matches = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name
    ]
    require(len(matches) == 1, f"cannot isolate function AST: {name}")
    return ast.dump(matches[0], annotate_fields=True, include_attributes=False)


def fixture() -> dict[str, Any]:
    return {
        "schema": EXPECTED_SCHEMA,
        "verdict": "PASS",
        "result": EXPECTED_RESULT,
        "evidence_class": EXPECTED_EVIDENCE,
        "claim_boundary": EXPECTED_CLAIM,
        "reviewer": {
            "agent_name": "DustyOsprey",
            "program": "codex",
            "model": "gpt-5",
            "same_model_lineage": True,
            "fresh_context": True,
        },
        "preregistration": {
            "path": PREREG_PATH,
            "sha256": PREREG_SHA256,
            "git_commit": PREREG_COMMIT,
            "committed_and_pushed_before_subject_source_inspection": True,
            "committed_and_pushed_before_runtime_checks": True,
        },
        "subject": {
            "git_commit": SUBJECT_COMMIT,
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
        "no_claim": EXPECTED_NO_CLAIM,
    }


def validate_receipt_shape(selector: Any, value: dict[str, Any]) -> None:
    selector.validate_source_audit_shape(
        value,
        schema=EXPECTED_SCHEMA,
        claim_boundary=EXPECTED_CLAIM,
        no_claim=EXPECTED_NO_CLAIM,
        required_checks=EXPECTED_CHECKS,
        preregistration_path=PREREG_PATH,
        named_bindings={"master_source": (SUBJECT_PATH, SUBJECT_SHA256)},
        subject_commit=SUBJECT_COMMIT,
    )


def strict_receipt_mutants(selector: Any) -> list[str]:
    good = fixture()
    parsed = selector.strict_json_text(
        json.dumps(good, separators=(",", ":")), "positive receipt fixture"
    )
    require(isinstance(parsed, dict), "positive fixture did not parse as an object")
    validate_receipt_shape(selector, parsed)
    rejected: list[str] = []

    def reject(label: str, mutate: Callable[[dict[str, Any]], None]) -> None:
        mutant = copy.deepcopy(good)
        mutate(mutant)
        try:
            validate_receipt_shape(selector, mutant)
        except selector.SelectorError:
            rejected.append(label)
            return
        raise AuditFailure(f"hostile receipt mutant escaped: {label}")

    def set_nested(value: dict[str, Any], path: tuple[str, ...], hostile: Any) -> None:
        destination: dict[str, Any] = value
        for component in path[:-1]:
            destination = destination[component]
        destination[path[-1]] = hostile

    true_paths = [
        *(("required_checks", key) for key in EXPECTED_CHECKS),
        ("reviewer", "same_model_lineage"),
        ("reviewer", "fresh_context"),
        ("preregistration", "committed_and_pushed_before_subject_source_inspection"),
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
    for path in true_paths:
        for kind, hostile in true_hostiles:
            reject(
                f"true_boolean:{'.'.join(path)}:{kind}",
                lambda value, path=path, hostile=hostile: set_nested(
                    value, path, hostile
                ),
            )

    false_paths = [
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
    for path in false_paths:
        for kind, hostile in false_hostiles:
            reject(
                f"false_boolean:{'.'.join(path)}:{kind}",
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

    require(len(true_paths) == 20, "true-Boolean denominator drift")
    require(len(false_paths) == 4, "false-Boolean denominator drift")
    require(len(rejected) == 177, "strict hostile receipt denominator drift")
    return rejected


def materialize_isolated_tree(*, stale_selector_pin: bool) -> tuple[Path, tempfile.TemporaryDirectory[str]]:
    temporary = tempfile.TemporaryDirectory(prefix="g0160-source-only-")
    fixture_root = Path(temporary.name)
    for relative_path in RUNTIME_BINDINGS:
        destination = fixture_root / relative_path
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative_path, destination)
    if stale_selector_pin:
        subject = fixture_root / SUBJECT_PATH
        raw = subject.read_text(encoding="utf-8")
        require(raw.count(SELECTOR_SHA256) == 1, "repaired selector pin census drift")
        subject.write_text(
            raw.replace(SELECTOR_SHA256, STALE_SELECTOR_SHA256), encoding="utf-8"
        )
    for forbidden in FORBIDDEN_G0140_RUNTIME_PATHS:
        require(not (fixture_root / forbidden).exists(), f"forbidden fixture path: {forbidden}")
    run(("git", "init", "-q"), cwd=fixture_root, check=True)
    run(("git", "config", "user.name", "G-0160 Source Audit"), cwd=fixture_root, check=True)
    run(
        ("git", "config", "user.email", "g0160-source-audit@example.invalid"),
        cwd=fixture_root,
        check=True,
    )
    run(("git", "add", "--", *RUNTIME_BINDINGS), cwd=fixture_root, check=True)
    run(("git", "commit", "-q", "-m", "isolated source fixture"), cwd=fixture_root, check=True)
    return fixture_root, temporary


def isolated_runtime_checks() -> dict[str, Any]:
    fixture_root, temporary = materialize_isolated_tree(stale_selector_pin=False)
    try:
        environment = dict(os.environ)
        environment["PYTHONDONTWRITEBYTECODE"] = "1"
        compile_process = run(
            (PYTHON, "-m", "py_compile", fixture_root / SUBJECT_PATH),
            cwd=fixture_root,
            env=environment,
        )
        require(compile_process.returncode == 0, "isolated py_compile failed")
        self_test = run(
            (PYTHON, fixture_root / SUBJECT_PATH, "--self-test"),
            cwd=fixture_root,
            env=environment,
        )
        require(self_test.returncode == 0, f"isolated self-test failed: {self_test.stderr}")
        require(
            "g0140-rank-aware-master-self-test: PASS" in self_test.stdout,
            "isolated self-test PASS token missing",
        )
        static = run(
            (PYTHON, fixture_root / SUBJECT_PATH, "--static-preflight"),
            cwd=fixture_root,
            env=environment,
        )
        require(static.returncode == 0, f"isolated static-preflight failed: {static.stderr}")
        lines = [line for line in static.stdout.splitlines() if line.strip()]
        require(lines, "isolated static-preflight emitted no output")
        payload = json.loads(lines[-1])
        require(
            payload.get("result") == "G0140_RANK_AWARE_MASTER_STATIC_PREFLIGHT_PASS"
            and payload.get("solver_sha256") == SUBJECT_SHA256
            and payload.get("selector_sha256") == SELECTOR_SHA256
            and payload.get("future_inputs_present")
            == {
                "manifest": False,
                "source_audit": False,
                "stage_a": False,
                "stage_b": False,
                "stage_c": False,
            }
            and payload.get("all_future_inputs_present") is False
            and payload.get("scientific_column_generation_run") is False
            and payload.get("scientific_result_written") is False,
            "isolated static-preflight source-only contract drift",
        )
        for forbidden in FORBIDDEN_G0140_RUNTIME_PATHS:
            require(
                not (fixture_root / forbidden).exists(),
                f"permitted runtime created forbidden path: {forbidden}",
            )
        return {
            "py_compile_exit": compile_process.returncode,
            "self_test_exit": self_test.returncode,
            "self_test_stdout": self_test.stdout.strip(),
            "static_preflight_exit": static.returncode,
            "static_preflight": payload,
        }
    finally:
        temporary.cleanup()


def stale_pin_mutant_check() -> dict[str, Any]:
    fixture_root, temporary = materialize_isolated_tree(stale_selector_pin=True)
    try:
        process = run((PYTHON, fixture_root / SUBJECT_PATH, "--self-test"), cwd=fixture_root)
        require(process.returncode != 0, "stale selector-pin mutant escaped")
        require(
            "self-test imported byte drift" in process.stderr,
            "stale selector-pin mutant failed for an unexpected reason",
        )
        for forbidden in FORBIDDEN_G0140_RUNTIME_PATHS:
            require(
                not (fixture_root / forbidden).exists(),
                f"stale-pin mutant created forbidden path: {forbidden}",
            )
        return {
            "mutated_pin": STALE_SELECTOR_SHA256,
            "exit": process.returncode,
            "rejected": True,
            "failure": "self-test imported byte drift",
        }
    finally:
        temporary.cleanup()


def source_protocol_checks(subject: Any, selector: Any, core: Any) -> dict[str, Any]:
    subject_source = (ROOT / SUBJECT_PATH).read_text(encoding="utf-8")
    selector_source = (ROOT / SELECTOR_PATH).read_text(encoding="utf-8")
    parent_source = run(
        ("git", "show", f"{SUBJECT_COMMIT}^:{SUBJECT_PATH}"), check=True
    ).stdout

    require(subject.SELECTOR_SHA256 == SELECTOR_SHA256, "subject selector pin drift")
    require(subject.G0135_MASTER_SHA256 == CORE_SHA256, "subject core pin drift")
    require(
        subject.G0135_RESULT_SHA256 == CORE_RESULT_SHA256,
        "subject opaque core-result pin drift",
    )
    require(subject.RECORDS == selector.RECORDS == core.RECORDS == 163_740, "record census drift")
    require(subject.SOURCE_AUDIT_SCHEMA == EXPECTED_SCHEMA, "audit schema drift")
    require(subject.SOURCE_AUDIT_RESULT == EXPECTED_RESULT, "audit result drift")
    require(subject.SOURCE_AUDIT_EVIDENCE == EXPECTED_EVIDENCE, "evidence class drift")
    require(subject.SOURCE_AUDIT_CLAIM == EXPECTED_CLAIM, "claim drift")
    require(subject.SOURCE_AUDIT_NO_CLAIM == EXPECTED_NO_CLAIM, "no-claim drift")
    require(subject.SOURCE_AUDIT_CHECKS == EXPECTED_CHECKS, "required-check set drift")
    require(
        selector.STAGE_C_SOURCE_AUDIT_PATH.relative_to(selector.ROOT).as_posix()
        == "artifacts/reviews/G-0159-g0140-stage-c-final4-source/SOURCE_AUDIT_RECEIPT.json",
        "selector generic Stage-C audit path drift",
    )
    require(
        "bound(selector.STAGE_C_SOURCE_AUDIT_PATH)" in subject_source
        and "selector.G0154_SOURCE_AUDIT_PATH" not in subject_source
        and "STAGE_C_SOURCE_AUDIT_PATH" in selector_source,
        "generic selector Stage-C source-audit accessor drift",
    )

    terminal_functions = (
        "with_column_loader",
        "preflight",
        "rehash_snapshot",
        "run",
        "selector_result",
    )
    for name in terminal_functions:
        require(
            function_ast(subject_source, name) == function_ast(parent_source, name),
            f"scientific terminal function changed: {name}",
        )

    run_source = inspect.getsource(subject.run)
    loader_source = inspect.getsource(subject.with_column_loader)
    static_source = inspect.getsource(subject.static_preflight)
    self_test_source = inspect.getsource(subject.self_test)
    core_source = inspect.getsource(core.exact_column_generation)
    separator_source = inspect.getsource(core.separator_scan)
    require(
        "core.exact_column_generation(" in run_source
        and "record_count=RECORDS" in run_source
        and "decision = with_column_loader(state, solve)" in run_source,
        "exact full-family dispatch drift",
    )
    require(
        "all_pool_rows = prepared[\"stage_b_rows\"]" in loader_source
        and "selector.exact_rank_selection(" in loader_source
        and "column.extend(int(row[sequence]) for row in all_pool_rows)" in loader_source
        and "column.extend(int(row[sequence]) for row in selected_rows)" in loader_source,
        "rank-aware loader protocol drift",
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
        "full 163,740-column separator census drift",
    )
    require(
        self_test_source.count("core.exact_column_generation(") == 2
        and "synthetic reopened member route drift" in self_test_source
        and "synthetic terminal separator route drift" in self_test_source,
        "member/separator source fixtures drift",
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
        f"static preflight calls scientific path: {sorted(forbidden_static_calls & observed_static_calls)}",
    )
    return {
        "record_count": 163_740,
        "terminal_functions_ast_equal_to_parent": list(terminal_functions),
        "selector_generic_stage_c_audit_path": True,
        "exact_core_protocol": True,
        "full_separator_census": True,
        "static_mode_has_no_scientific_call_edge": True,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--receipt", action="store_true")
    args = parser.parse_args(argv)

    custody = [
        verify_binding(
            SUBJECT_PATH,
            SUBJECT_SHA256,
            expected_commit=SUBJECT_COMMIT,
            expected_blob=SUBJECT_BLOB,
        ),
        verify_binding(
            SELECTOR_PATH,
            SELECTOR_SHA256,
            expected_commit=SELECTOR_COMMIT,
            expected_blob=SELECTOR_BLOB,
        ),
        verify_binding(CORE_PATH, CORE_SHA256),
        verify_binding(CORE_RESULT_PATH, CORE_RESULT_SHA256),
        verify_binding(HELPER_PATH, HELPER_SHA256),
        verify_binding(PREREG_PATH, PREREG_SHA256, expected_commit=PREREG_COMMIT),
    ]
    require(git_stdout("rev-parse", f"{SUBJECT_COMMIT}^{{commit}}") == SUBJECT_COMMIT, "subject commit unavailable")
    require(git_stdout("rev-parse", f"{SELECTOR_COMMIT}^{{commit}}") == SELECTOR_COMMIT, "selector commit unavailable")
    for ancestor, descendant, label in (
        (SELECTOR_COMMIT, SUBJECT_COMMIT, "selector -> subject"),
        (SUBJECT_COMMIT, PREREG_COMMIT, "subject -> preregistration"),
        (PREREG_COMMIT, "origin/master", "preregistration -> pushed master"),
    ):
        ancestry = run(("git", "merge-base", "--is-ancestor", ancestor, descendant))
        require(ancestry.returncode == 0, f"Git ancestry drift: {label}")

    selector = load_module(SELECTOR_PATH, "g0160_source_only_selector")
    subject = load_module(SUBJECT_PATH, "g0160_source_only_subject")
    core = load_module(CORE_PATH, "g0160_source_only_core")
    protocol = source_protocol_checks(subject, selector, core)
    rejected = strict_receipt_mutants(selector)
    runtime = isolated_runtime_checks()
    stale_pin = stale_pin_mutant_check()

    actual_receipt_validated = False
    if args.receipt:
        actual = selector.load_json(ROOT / RECEIPT_PATH)
        validate_receipt_shape(selector, actual)
        require(actual == fixture(), "actual strict receipt differs from exact fixture")
        actual_receipt_validated = True

    evidence = {
        "schema": "max11-g0160-g0140-stage-d-master-final3-source-audit-tests-v1",
        "verdict": "PASS",
        "custody": custody,
        "protocol": protocol,
        "strict_receipt_positive_control": True,
        "strict_boolean_and_structural_mutants_rejected": len(rejected),
        "stale_selector_pin_mutant": stale_pin,
        "isolated_runtime": runtime,
        "actual_receipt_validated": actual_receipt_validated,
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "scientific_replay_run": False,
    }
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
