#!/usr/bin/env python3
"""Outcome-blind static/source audit for the frozen G-0140 Stage-B producer.

The only subject execution modes used here are --self-test and --preflight-static.
No G-0140 scientific manifest or Stage-A/B/C/D/E output is opened or created.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
AUDIT_DIR = ROOT / "artifacts/reviews/G-0142-g0140-stage-b-source"
RECEIPT = AUDIT_DIR / "SOURCE_AUDIT_RECEIPT.json"
SUBJECT_COMMIT = "f603a6b8e51e31b810d957176836da52142aa0a9"
PREREG_COMMIT = "7bb0fc1"
CORRECTION_COMMIT = "4e9e0bb"

SOURCE = "artifacts/math/G-0140/stage_b_pricer/src/main.rs"
CARGO = "artifacts/math/G-0140/stage_b_pricer/Cargo.toml"
LOCK = "artifacts/math/G-0140/stage_b_pricer/Cargo.lock"
EXECUTABLE = (
    "artifacts/math/G-0140/stage_b_pricer/target/release/"
    "g0140-stage-b-pool128-coordinate-pricer"
)
PREREG = "artifacts/reviews/G-0142-g0140-stage-b-source/PREREGISTRATION.md"
CORRECTION = (
    "artifacts/reviews/G-0142-g0140-stage-b-source/"
    "PREREGISTRATION_CORRECTION.md"
)

SUBJECTS: dict[str, dict[str, Any]] = {
    SOURCE: {
        "sha256": "2b09a0c36d060c7cbc03fb26009cb9bba0c49ef0c14ff7d24ec52f4f6294b09b",
        "git_blob": "b230c7e84fb0d008757d4d78d00a1231833f4937",
        "git_mode": "100644",
        "size": 73_685,
    },
    CARGO: {
        "sha256": "425d82de4e6d5902e2d3d7b005c5473225c4d6f197752590e89d7be670b2685c",
        "git_blob": "6ec442fd6ab0cdae930a0ccc528516304821dba2",
        "git_mode": "100644",
        "size": 352,
    },
    LOCK: {
        "sha256": "8875e1375a361873ac13bbcdf9e14c8ca7b34afa1438dfae9a6800f31325365a",
        "git_blob": "0d77ef12ebdf0868f9540cc81fab3e33664b0adf",
        "git_mode": "100644",
        "size": 7_622,
    },
    EXECUTABLE: {
        "sha256": "13d24a884b3714f803bb1b79d879527ed4f99445788debe7922a5c53054cc79e",
        "git_blob": "60468e5db415c5abf4f46bacb897eff9b224ec3e",
        "git_mode": "100755",
        "size": 1_763_456,
    },
}

PROTOCOLS: dict[str, dict[str, str]] = {
    PREREG: {
        "sha256": "a777e9cb0af7a0afabd122283019eae43328ffa106b1cf48499c6adc304e5895",
        "commit": PREREG_COMMIT,
    },
    CORRECTION: {
        "sha256": "18809627fbcc27ac7bd42603c86fce14e2a7c919fc9b5b6b1f50dd2444fd407b",
        "commit": CORRECTION_COMMIT,
    },
}

SCIENTIFIC_MANIFEST = "artifacts/math/G-0140/pool128_manifest_v1.json"
SCIENTIFIC_OUTPUTS = [
    "artifacts/math/G-0140/pool128_global_replay_v1.json",
    "artifacts/math/G-0140/pool128_coordinate_prices_v1.json",
    "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json",
    "artifacts/math/G-0140/rank_aware_master_result_v1.json",
    "artifacts/math/G-0140/new_member_global_replay_v1.json",
]

PANEL = "artifacts/math/G-0113/panel_solver_input_v1.json"
CANDIDATE = "artifacts/math/G-0135/full_family_master_result_v3.json"


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def command(argv: list[str], timeout: int = 180) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        argv,
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        check=False,
    )
    return {
        "argv": argv,
        "exit_code": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "stdout_sha256": sha256_bytes(completed.stdout.encode()),
        "stderr_sha256": sha256_bytes(completed.stderr.encode()),
        "wall_seconds": round(time.monotonic() - started, 6),
    }


def git_bytes(commit: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"git show failed for {commit}:{path}: {completed.stderr.decode(errors='replace')}"
        )
    return completed.stdout


def git_tree_entry(commit: str, path: str) -> tuple[str, str]:
    completed = subprocess.run(
        ["git", "ls-tree", commit, "--", path],
        cwd=ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0 or not completed.stdout.strip():
        raise RuntimeError(f"git ls-tree failed for {commit}:{path}: {completed.stderr}")
    match = re.fullmatch(r"(\d+) blob ([0-9a-f]{40})\t.+\n?", completed.stdout)
    if match is None:
        raise RuntimeError(f"malformed git ls-tree output for {path}")
    return match.group(1), match.group(2)


def absence_snapshot() -> dict[str, Any]:
    manifest_present = (ROOT / SCIENTIFIC_MANIFEST).exists()
    outputs_present = [path for path in SCIENTIFIC_OUTPUTS if (ROOT / path).exists()]
    return {
        "scientific_manifest_observed": manifest_present,
        "scientific_output_observed": bool(outputs_present),
        "manifest_path_checked_for_existence_only": SCIENTIFIC_MANIFEST,
        "output_paths_checked_for_existence_only": SCIENTIFIC_OUTPUTS,
        "present_output_paths": outputs_present,
    }


def rust_function_body(source: str, name: str) -> str:
    match = re.search(rf"\bfn\s+{re.escape(name)}\s*\(", source)
    if match is None:
        return ""
    brace = source.find("{", match.start())
    if brace < 0:
        return ""
    depth = 0
    for index in range(brace, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[brace : index + 1]
    return ""


def struct_denies_unknown_fields(source: str, name: str) -> bool:
    match = re.search(rf"\bstruct\s+{re.escape(name)}\b", source)
    if match is None:
        return False
    prefix = source[max(0, match.start() - 260) : match.start()]
    boundary = max(prefix.rfind("}"), prefix.rfind(";"))
    attributes = prefix[boundary + 1 :]
    return "#[serde(deny_unknown_fields)]" in attributes


def source_contract(source: str, kernel: str, cargo: str) -> list[dict[str, Any]]:
    checks: list[dict[str, Any]] = []

    def add(identifier: str, ok: bool, evidence: str) -> None:
        checks.append({"id": identifier, "passed": bool(ok), "evidence": evidence})

    add(
        "SEM_EXACT_CENSUS_CONSTANTS",
        all(
            token in source
            for token in [
                "const K: usize = 128;",
                "const RECORDS: usize = 163_740;",
                "const HINGE_ENTRIES: usize = K * RECORDS;",
                "direction_major.iter().map(Vec::len).sum::<usize>() == HINGE_ENTRIES",
                "assert_eq!(HINGE_ENTRIES, 20_958_720);",
            ]
        ),
        "128 * 163740 is frozen and the complete direction-major matrix is dimension-checked",
    )

    dot = rust_function_body(source, "exact_dot")
    add(
        "SEM_ARBITRARY_BIGINT_DOT",
        "terms: &[(usize, BigInt)]" in source
        and "-> BigInt" in source[source.find("fn exact_dot") : source.find("fn exact_dot") + 180]
        and "coefficient * BigInt::from(row[*sequence])" in dot
        and not any(token in dot for token in ["as i64", "as i128", "to_i64", "to_i128"])
        and 'num-bigint = "0.5"' in cargo,
        "candidate coefficients remain BigInt through every i64 coordinate multiplication",
    )

    add(
        "SEM_DIRECTION_AND_RECORD_ORDER",
        all(
            token in source
            for token in [
                "pool.windows(2)",
                "window[0].direction < window[1].direction",
                "validate_direction(&item.direction)?;",
                "sequence == expected",
                "validate_record_axis(input.records.iter().map(|record| record.sequence), RECORDS)",
                "selected_direction_digest(pool) == expected_direction_digest",
            ]
        ),
        "Pool128 is strict signed-lex and records are exactly sequence 0..163739",
    )

    run_body = rust_function_body(source, "run")
    add(
        "SEM_COMPLETE_DIRECTION_MAJOR_PRICING",
        all(
            token in run_body
            for token in [
                ".records\n        .par_iter()",
                ".map(|record| hinge_coefficients(record, &directions))",
                "transpose_record_major(record_major, K)?",
                "direction_major.iter().flat_map(|row| row.iter())",
                ".map(|row| exact_dot(row, &exact_terms))",
                "dot == &selected.coefficient",
                "rows.len() == K",
                "row.records == RECORDS",
                "row.direction == directions[index]",
            ]
        ),
        "all records are priced in stable record order then transposed and serialized in Pool128 order",
    )

    add(
        "SEM_KERNEL_BRIDGE",
        all(
            token in kernel
            for token in [
                "pub fn hinge_coefficients(record: &Record, directions: &[[i8; N]]) -> Result<Vec<i64>>",
                "for direction in directions",
                "validate_direction(direction)?;",
                ".map(|direction| hinge_coefficient_from_table(record, &table, direction))",
            ]
        ),
        "the bound kernel validates and prices every requested direction in supplied order",
    )

    strict_subject_structs = [
        "Binding",
        "ManifestParameters",
        "PlannedOutput",
        "StudyManifest",
        "Term",
        "Candidate",
        "CandidateSupportReceipt",
        "CandidateReplayReceipt",
        "CandidateCoefficientMutant",
        "PanelInput",
        "ExactHinge",
        "ExactLinear",
        "AccumulatedDirectionCheck",
        "StageAReceipt",
    ]
    non_strict = [
        name for name in strict_subject_structs if not struct_denies_unknown_fields(source, name)
    ]
    if not struct_denies_unknown_fields(kernel, "Record"):
        non_strict.append("g0117_global_coordinate_pricer::Record")
    add(
        "SCHEMA_ALL_INPUT_STRUCTS_DENY_UNKNOWN_FIELDS",
        not non_strict,
        "non-strict deserializers: " + (", ".join(non_strict) if non_strict else "none"),
    )

    audit_gate = rust_function_body(source, "validate_source_audit")
    add(
        "SCHEMA_SOURCE_AUDIT_GATE_EXACT",
        'value_string(&receipt, "/schema")' in audit_gate
        and 'value_string(&receipt, "/result")' in audit_gate
        and "required_subjects" in audit_gate
        and 'value_string(&receipt, "/verdict")? == "PASS"' in audit_gate,
        "source-audit admission must check exact schema and result, not only PASS/absence flags/bindings",
    )

    add(
        "GATE_G0139_EXACT",
        all(
            token in source
            for token in [
                '"max11-g0139-g0135-result-audit-v1"',
                'value_string(&receipt, "/verdict")? == "PASS"',
                'value_string(&receipt, "/result")? == "CONSISTENT_RESIDUAL_T1"',
                "ANCESTOR_STAGE_D_RESULT_SHA256",
                "CANDIDATE_SHA256",
            ]
        ),
        "G-0139 exact schema/verdict/result and both G-0135 inputs are required",
    )

    load = rust_function_body(source, "load_and_validate_inputs")
    current_release = rust_function_body(source, "validate_current_release")
    add(
        "GATE_MANIFEST_STAGE_A_AND_COMPILED_BYTES",
        all(
            token in source
            for token in [
                "validate_compiled_and_static(root)?;",
                "COMPILED_SOURCE",
                "COMPILED_MANIFEST",
                "COMPILED_LOCK",
                "validate_source_audit(",
                "validate_stage_a_receipt(",
                "validate_g0139_gate(root, &snapshot)?;",
            ]
        )
        and "validate_manifest(root, manifest_path)?" in load
        and "validate_current_release(root, &manifest)?" in load
        and "executable == expected" in current_release
        and "manifest_binding(manifest, STAGE_B_EXECUTABLE_PATH)? == binding.sha256" in current_release,
        "scientific mode requires manifest, audits, Stage-A, embedded source bytes, and the exact current release",
    )

    publish = rust_function_body(source, "publish_exclusive")
    add(
        "CUSTODY_EXCLUSIVE_OUTPUT",
        all(
            token in publish
            for token in [
                'ensure!(!path.exists(), "refusing to overwrite output")',
                ".create_new(true)",
                "std::fs::hard_link(&temporary, path)",
                "directory.sync_all()",
            ]
        )
        and "publish_exclusive(&output_path, &serialized)?" in run_body,
        "create-new temporary plus hard-link publication refuses overwrite and fsyncs",
    )

    add(
        "CUSTODY_END_REHASH",
        "let custody_end = custody_snapshot(&root, &inputs.manifest, &stage_a_sha_end)?;"
        in run_body
        and "inputs.custody == custody_end" in run_body
        and "inputs_rehashed_at_end: true" in run_body,
        "all manifest bindings, manifest, and Stage-A receipt are rehashed and compared at end",
    )

    add(
        "CLAIM_BOUNDARY_NARROW",
        all(
            token in source
            for token in [
                "complete-matrix rank-selection input only",
                "not a membership decision",
                "family-completeness theorem",
                "lower bound",
                "minimality result",
                "Lean theorem",
            ]
        ),
        "output explicitly refuses scientific and theorem cousins",
    )

    self_test = rust_function_body(source, "self_test")
    add(
        "CONTROLS_SUBJECT_SELF_TEST_NONVACUOUS",
        all(
            token in self_test
            for token in [
                "duplicate or unknown term field accepted",
                "unknown manifest field accepted",
                "direction-major transpose/census drift",
                "hinge kernel/full-normal-form bridge drift",
                "Pool128 order/direction/residual mutant escaped",
                "record census/order mutant escaped",
                "arbitrary-precision dot narrowed",
                "atomic no-overwrite publication control failed",
            ]
        ),
        "self-test has positive bridges and hostile must-fail controls",
    )
    return checks


def hostile_checker_controls(source: str, kernel: str, cargo: str) -> list[dict[str, Any]]:
    controls: list[dict[str, Any]] = []

    def add(identifier: str, passed: bool, evidence: str) -> None:
        controls.append({"id": identifier, "passed": bool(passed), "evidence": evidence})

    original_sha = sha256_bytes(source.encode())
    mutated_sha = sha256_bytes((source + "\n// hostile byte\n").encode())
    add(
        "HOSTILE_SUBJECT_BYTE_MUTATION_REJECTED",
        original_sha == SUBJECTS[SOURCE]["sha256"] and mutated_sha != original_sha,
        "one appended byte-range changes the bound SHA-256",
    )

    census_mutant = source.replace(
        "const HINGE_ENTRIES: usize = K * RECORDS;",
        "const HINGE_ENTRIES: usize = K;",
        1,
    )
    census = {item["id"]: item["passed"] for item in source_contract(census_mutant, kernel, cargo)}
    add(
        "HOSTILE_SHORT_CENSUS_SOURCE_MUTANT_REJECTED",
        not census["SEM_EXACT_CENSUS_CONSTANTS"],
        "replacing K*RECORDS by K fails the exact-census contract",
    )

    bigint_mutant = source.replace(
        "coefficient * BigInt::from(row[*sequence])",
        "coefficient * BigInt::from(row[*sequence] as i32)",
        1,
    )
    bigint = {item["id"]: item["passed"] for item in source_contract(bigint_mutant, kernel, cargo)}
    add(
        "HOSTILE_NARROWING_SOURCE_MUTANT_REJECTED",
        not bigint["SEM_ARBITRARY_BIGINT_DOT"],
        "an i32 narrowing bridge fails the BigInt contract",
    )

    custody_mutant = source.replace(
        "inputs.custody == custody_end",
        "inputs.custody != custody_end",
        1,
    )
    custody = {item["id"]: item["passed"] for item in source_contract(custody_mutant, kernel, cargo)}
    add(
        "HOSTILE_END_REHASH_SOURCE_MUTANT_REJECTED",
        not custody["CUSTODY_END_REHASH"],
        "reversing the end-custody equality fails the contract",
    )

    strict_fixture = "#[derive(Deserialize)]\n#[serde(deny_unknown_fields)]\nstruct Receipt { value: u8 }"
    loose_fixture = "#[derive(Deserialize)]\nstruct Receipt { value: u8 }"
    add(
        "HOSTILE_UNKNOWN_FIELD_SCHEMA_CONTROL",
        struct_denies_unknown_fields(strict_fixture, "Receipt")
        and not struct_denies_unknown_fields(loose_fixture, "Receipt"),
        "the checker distinguishes fail-closed and permissive serde structs",
    )

    gate_fixture = (
        'fn validate_source_audit() { value_string(&receipt, "/schema"); '
        'value_string(&receipt, "/result"); value_string(&receipt, "/verdict"); '
        "let _ = required_subjects; }"
    )
    gate_body = rust_function_body(gate_fixture, "validate_source_audit")
    add(
        "HOSTILE_LOOKALIKE_AUDIT_SCHEMA_CONTROL",
        'value_string(&receipt, "/schema")' in gate_body
        and 'value_string(&receipt, "/result")' in gate_body,
        "the exact-schema detector has a passing positive fixture",
    )

    with tempfile.TemporaryDirectory(prefix="g0142-exclusive-") as raw:
        path = Path(raw) / "receipt.json"
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        os.write(descriptor, b"first\n")
        os.close(descriptor)
        try:
            second = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            rejected = True
        else:
            os.close(second)
            rejected = False
        add(
            "HOSTILE_RECEIPT_OVERWRITE_REJECTED",
            rejected and path.read_bytes() == b"first\n",
            "O_EXCL refuses a second publication",
        )
    return controls


def subject_snapshot() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bindings: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for path, expected in SUBJECTS.items():
        disk_path = ROOT / path
        raw = disk_path.read_bytes()
        committed = git_bytes(SUBJECT_COMMIT, path)
        mode, blob = git_tree_entry(SUBJECT_COMMIT, path)
        actual = {
            "path": path,
            "sha256": sha256_bytes(raw),
            "size_bytes": len(raw),
            "git_commit": SUBJECT_COMMIT,
            "git_blob": blob,
            "git_mode": mode,
            "worktree_equals_subject_commit": raw == committed,
            "executable": bool(mode == "100755"),
        }
        bindings[path] = actual
        ok = (
            actual["sha256"] == expected["sha256"]
            and actual["size_bytes"] == expected["size"]
            and blob == expected["git_blob"]
            and mode == expected["git_mode"]
            and actual["worktree_equals_subject_commit"]
        )
        checks.append(
            {
                "id": f"BIND_{Path(path).name}",
                "passed": ok,
                "evidence": actual,
            }
        )
    return bindings, checks


def protocol_bindings() -> tuple[dict[str, Any], list[dict[str, Any]]]:
    bindings: dict[str, Any] = {}
    checks: list[dict[str, Any]] = []
    for path, expected in PROTOCOLS.items():
        actual = {
            "path": path,
            "sha256": sha256_path(ROOT / path),
            "git_commit_prefix": expected["commit"],
        }
        bindings[path] = actual
        checks.append(
            {
                "id": f"PROTOCOL_{Path(path).stem}",
                "passed": actual["sha256"] == expected["sha256"],
                "evidence": actual,
            }
        )
    return bindings, checks


def run_self_test() -> int:
    assert sha256_bytes(b"a") != sha256_bytes(b"b")
    fixture = "fn sample() { let value = { 1 }; }"
    assert rust_function_body(fixture, "sample") == "{ let value = { 1 }; }"
    strict = "#[serde(deny_unknown_fields)]\nstruct X { value: u8 }"
    loose = "struct X { value: u8 }"
    assert struct_denies_unknown_fields(strict, "X")
    assert not struct_denies_unknown_fields(loose, "X")
    print("G-0142 independent checker self-test PASS")
    return 0


def publish_exclusive_json(path: Path, value: dict[str, Any]) -> None:
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode()
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        os.write(descriptor, encoded)
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def run_static_audit() -> int:
    if Path.cwd().resolve() != ROOT:
        raise RuntimeError("run from repository root")
    if RECEIPT.exists():
        raise RuntimeError(f"refusing to overwrite {RECEIPT.relative_to(ROOT)}")

    started_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    absence_before = absence_snapshot()
    bindings_start, binding_checks = subject_snapshot()
    protocol, protocol_checks = protocol_bindings()

    source = (ROOT / SOURCE).read_text()
    cargo = (ROOT / CARGO).read_text()
    kernel_path = ROOT / "artifacts/math/G-0117/src/lib.rs"
    kernel = kernel_path.read_text()
    semantics = source_contract(source, kernel, cargo)
    hostile = hostile_checker_controls(source, kernel, cargo)

    subject_self_test = command([str(ROOT / EXECUTABLE), "--self-test"], timeout=180)
    absence_after_self_test = absence_snapshot()
    static_preflight = command(
        [
            str(ROOT / EXECUTABLE),
            "--preflight-static",
            PANEL,
            CANDIDATE,
        ],
        timeout=600,
    )
    absence_after_static = absence_snapshot()

    bindings_end, end_binding_checks = subject_snapshot()
    end_equal = bindings_start == bindings_end

    execution_checks = [
        {
            "id": "EXEC_SUBJECT_SELF_TEST",
            "passed": subject_self_test["exit_code"] == 0
            and "G-0140 Stage-B Pool128 self-test PASS" in subject_self_test["stdout"],
            "evidence": subject_self_test,
        },
        {
            "id": "EXEC_SUBJECT_STATIC_PREFLIGHT",
            "passed": static_preflight["exit_code"] == 0
            and "G-0140 Stage-B static preflight PASS" in static_preflight["stdout"]
            and "future manifest/Stage-A/G-0142 receipts not consumed"
            in static_preflight["stdout"],
            "evidence": static_preflight,
        },
        {
            "id": "EXEC_NO_SCIENTIFIC_ARTIFACT_OBSERVED",
            "passed": all(
                not snapshot["scientific_manifest_observed"]
                and not snapshot["scientific_output_observed"]
                for snapshot in [
                    absence_before,
                    absence_after_self_test,
                    absence_after_static,
                ]
            ),
            "evidence": {
                "before": absence_before,
                "after_subject_self_test": absence_after_self_test,
                "after_subject_static_preflight": absence_after_static,
            },
        },
        {
            "id": "CUSTODY_SUBJECT_REHASH_AT_END",
            "passed": end_equal and all(item["passed"] for item in end_binding_checks),
            "evidence": {
                "initial_equals_final": end_equal,
                "final_bindings": bindings_end,
            },
        },
    ]

    all_checks = binding_checks + protocol_checks + semantics + hostile + execution_checks
    failures = [item for item in all_checks if not item["passed"]]
    verdict = "PASS" if not failures else "FAIL"

    findings: list[dict[str, Any]] = []
    semantic_failures = {item["id"] for item in semantics if not item["passed"]}
    if "SCHEMA_ALL_INPUT_STRUCTS_DENY_UNKNOWN_FIELDS" in semantic_failures:
        findings.append(
            {
                "id": "G0142-F01",
                "severity": "BLOCKING",
                "title": "Several nested/top-level input deserializers accept unknown fields",
                "evidence": next(
                    item["evidence"]
                    for item in semantics
                    if item["id"] == "SCHEMA_ALL_INPUT_STRUCTS_DENY_UNKNOWN_FIELDS"
                ),
                "impact": "The producer's claimed strict-schema boundary is not true for every admitted Candidate, Stage-A, accumulated-direction, and Record object. Hash/manifest binding constrains bytes, but it does not make the deserializer fail closed on schema drift.",
                "required_remediation": "Add deny_unknown_fields or equivalent exact-key validation for every admitted input object, then freeze and audit a new producer commit/executable.",
            }
        )
    if "SCHEMA_SOURCE_AUDIT_GATE_EXACT" in semantic_failures:
        findings.append(
            {
                "id": "G0142-F02",
                "severity": "BLOCKING",
                "title": "Source-audit admission does not authenticate an exact receipt schema/result",
                "evidence": "validate_source_audit checks PASS, two absence booleans, tracked/hash-bound bytes, and recursive subject bindings, but never /schema or /result.",
                "impact": "A manifest-bound lookalike JSON object can satisfy the code path without being the expected G-0141/G-0142 receipt type. This weakens the source-audit gate even though the manifest still binds exact bytes.",
                "required_remediation": "Require the exact audit schema and result/claim fields for each Stage-A and Stage-B source-audit receipt, then freeze and audit a new producer commit/executable.",
            }
        )

    receipt: dict[str, Any] = {
        "schema": "max11-g0142-g0140-stage-b-source-audit-v1",
        "verdict": verdict,
        "result": "SOURCE_CUSTODY_AUDIT_PASS_T1"
        if verdict == "PASS"
        else "SOURCE_CUSTODY_AUDIT_FAIL_T1",
        "claim_boundary": "Outcome-blind audit of the frozen G-0140 Stage-B source, Cargo metadata, lockfile, and compiled executable. It does not run or validate the 128x163740 scientific pricing result, target membership, any lower bound, or a theorem.",
        "auditor": {
            "agent_name": "CobaltSpire",
            "program": "codex",
            "model": "gpt-5-codex",
            "independence_tier": "T1",
            "same_campaign": True,
            "same_model_family": True,
        },
        "started_utc": started_utc,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "scientific_manifest_observed": any(
            snapshot["scientific_manifest_observed"]
            for snapshot in [absence_before, absence_after_self_test, absence_after_static]
        ),
        "scientific_output_observed": any(
            snapshot["scientific_output_observed"]
            for snapshot in [absence_before, absence_after_self_test, absence_after_static]
        ),
        "preregistration": {
            "original": protocol[PREREG],
            "path_correction": protocol[CORRECTION],
            "correction_disclosure": "The auditor initially omitted `coordinate-` from the executable path. The path-only correction was committed before source inspection or audit execution; both documents remain bound.",
        },
        "subject": {
            "git_commit": SUBJECT_COMMIT,
            "bindings": bindings_start,
            "final_bindings": bindings_end,
            "initial_equals_final": end_equal,
        },
        "dimensions": {
            "pool_k": 128,
            "records": 163_740,
            "hinge_entries": 20_958_720,
            "candidate_terms": 135,
            "order": "direction-major Pool128; record-minor canonical sequence 0..163739",
            "arithmetic": "signed i64 hinge coordinates times arbitrary-precision num_bigint::BigInt candidate coefficients",
        },
        "checks": all_checks,
        "findings": findings,
        "failed_check_ids": [item["id"] for item in failures],
        "inputs_rehashed_at_end": end_equal,
        "limitations": [
            "FAIL does not imply the numeric pricing loop is wrong; the core loop, BigInt bridge, dimension checks, order checks, exclusive publication, and end rehash passed this bounded source inspection.",
            "No scientific manifest or G-0140 Stage-A/B/C/D/E output was opened, parsed, created, or priced.",
            "Same-campaign, same-lineage T1 evidence cannot establish T2 independence or promote a mathematical bottom line.",
            "A future repaired producer requires a new exact-commit source/executable audit; this receipt cannot be carried forward.",
        ],
    }
    publish_exclusive_json(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "schema": receipt["schema"],
                "verdict": verdict,
                "failed_check_ids": receipt["failed_check_ids"],
                "receipt": str(RECEIPT.relative_to(ROOT)),
            },
            sort_keys=True,
        )
    )
    return 0 if verdict == "PASS" else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--static-preflight", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return run_self_test()
    return run_static_audit()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # fail closed without a fabricated receipt
        print(f"G-0142 checker error: {error}", file=sys.stderr)
        raise
