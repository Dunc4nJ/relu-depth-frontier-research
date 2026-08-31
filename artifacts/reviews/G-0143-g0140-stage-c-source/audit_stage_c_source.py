#!/usr/bin/env python3
"""Outcome-blind adversarial source/custody audit for frozen G-0140 Stage C.

This checker never opens or runs the future G-0140 manifest, Stage-A/B inputs,
or Stage-C/D/E outputs.  Its mathematical executions are tiny synthetic exact
fixtures designed to distinguish the frozen selector's advertised contract
from nearby, weaker behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import inspect
import json
import os
import random
import stat
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any, Callable, Sequence


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SUBJECT_COMMIT = "2bdc6f5c7132b0ed30d291c5ba116e84fda5044e"
PREREGISTRATION_COMMIT = "e5e3ead70ce4176155ebb9e6e625462d796d2e73"
PREREGISTRATION_PATH = HERE / "PREREGISTRATION.md"
PREREGISTRATION_SHA256 = (
    "99980ff3314173bf3eaa74ea89d522d2c64c2869952db0257bfdc8a681e37591"
)

SELECTOR_REL = (
    "artifacts/math/G-0140/stage_c_selector/"
    "complete_matrix_rank_selector_v1.py"
)
NATIVE_SOURCE_REL = (
    "artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots.cpp"
)
NATIVE_BINARY_REL = (
    "artifacts/math/G-0140/stage_c_selector/ffpack_modular_pivots_v1"
)
BUILD_RECEIPT_REL = (
    "artifacts/math/G-0140/stage_c_selector/"
    "ffpack_modular_pivots_v1.build.json"
)
LAUNCHER_REL = (
    "artifacts/math/G-0140/stage_c_selector/run-stage-c-selector-v1"
)
NATIVE_TEST_REL = (
    "artifacts/math/G-0140/stage_c_selector/"
    "test_ffpack_modular_pivots_v1.py"
)

EXPECTED: dict[str, dict[str, Any]] = {
    SELECTOR_REL: {
        "mode": "100755",
        "blob": "554aba6ddd26715027253f417a8401a3f195c7e7",
        "bytes": 112422,
        "sha256": "a86e8ac8ee3dd37e980336b09c0345f87327243c1f113546c23ccdb57ddc2c18",
    },
    NATIVE_SOURCE_REL: {
        "mode": "100644",
        "blob": "b73b6c739925b8974ee11f3f621f485411977fa2",
        "bytes": 7783,
        "sha256": "198262e449c901f70b1e26cd260cbd5ade4e6eaf2868659e4cfd59a1ab72d9c7",
    },
    NATIVE_BINARY_REL: {
        "mode": "100755",
        "blob": "ce896fac4b22c9adce25344d963547b8d37b923d",
        "bytes": 344936,
        "sha256": "207fcf88fe3f89c8119bd6b38037d9f0919165eecf04b48d1b0aaae039843171",
    },
    BUILD_RECEIPT_REL: {
        "mode": "100644",
        "blob": "fc1a1b2f5d363408a88e9e9e3ef1910f0040ebca",
        "bytes": 1027,
        "sha256": "5157c020cc343de6bb891fb339a1027a9f8f3059aa03ea2a32722bc13d0fff76",
    },
    LAUNCHER_REL: {
        "mode": "100755",
        "blob": "7e20c32bfa45ac333d2b3282f2845c4d90b514bd",
        "bytes": 566,
        "sha256": "786b42f28d4720ca2578de78a3e312ce0186b8609d2b2c9c85c8f76bdd409d78",
    },
    NATIVE_TEST_REL: {
        "mode": "100755",
        "blob": "afce9ee0bd391b20ab672063a0542205f7736803",
        "bytes": 5360,
        "sha256": "5d2b920f06100a2a7bd4069ebe4f009d4c2ba8aecea8872c9d4c58abe9296b94",
    },
}

FUTURE_SCIENTIFIC_PATHS = [
    ROOT / "artifacts/math/G-0140/pool128_manifest_v1.json",
    ROOT / "artifacts/math/G-0140/pool128_global_replay_v1.json",
    ROOT / "artifacts/math/G-0140/pool128_coordinate_prices_v1.json",
    ROOT / "artifacts/math/G-0140/pool128_exact_rank_selection_v1.json",
    ROOT / "artifacts/math/G-0140/rank_aware_master_result_v1.json",
    ROOT / "artifacts/math/G-0140/new_member_global_replay_v1.json",
]


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def run(argv: Sequence[str], *, cwd: Path = ROOT) -> dict[str, Any]:
    begun = time.perf_counter()
    process = subprocess.run(
        list(argv), cwd=cwd, check=False, capture_output=True, text=True
    )
    elapsed = time.perf_counter() - begun
    if process.stdout:
        sys.stdout.write(process.stdout)
    if process.stderr:
        sys.stderr.write(process.stderr)
    return {
        "argv": list(argv),
        "exit_code": process.returncode,
        "stdout": process.stdout,
        "stderr": process.stderr,
        "stdout_sha256": sha256_bytes(process.stdout.encode("utf-8")),
        "stderr_sha256": sha256_bytes(process.stderr.encode("utf-8")),
        "wall_seconds": elapsed,
    }


def git_output(*args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True, text=True
    )
    return process.stdout.strip()


def subject_bindings() -> dict[str, dict[str, Any]]:
    bindings: dict[str, dict[str, Any]] = {}
    for relative, expected in EXPECTED.items():
        line = git_output("ls-tree", "-l", SUBJECT_COMMIT, "--", relative)
        fields = line.split(None, 4)
        require(len(fields) == 5, f"missing subject tree entry: {relative}")
        mode, kind, blob, raw_size, observed_path = fields
        require(kind == "blob" and observed_path == relative, "Git tree path/type drift")
        committed = subprocess.run(
            ["git", "show", f"{SUBJECT_COMMIT}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        path = ROOT / relative
        status = path.lstat()
        worktree = path.read_bytes()
        observed = {
            "path": relative,
            "git_commit": SUBJECT_COMMIT,
            "git_mode": mode,
            "git_blob": blob,
            "size_bytes": len(worktree),
            "sha256": sha256_bytes(worktree),
            "regular_file": stat.S_ISREG(status.st_mode),
            "symlink": path.is_symlink(),
            "worktree_equals_subject_commit": worktree == committed,
        }
        require(mode == expected["mode"], f"Git mode drift: {relative}")
        require(blob == expected["blob"], f"Git blob drift: {relative}")
        require(int(raw_size) == expected["bytes"], f"Git size drift: {relative}")
        require(len(worktree) == expected["bytes"], f"worktree size drift: {relative}")
        require(observed["sha256"] == expected["sha256"], f"SHA drift: {relative}")
        require(observed["regular_file"] and not observed["symlink"], f"file kind drift: {relative}")
        require(observed["worktree_equals_subject_commit"], f"worktree/commit drift: {relative}")
        bindings[relative] = observed
    return bindings


def load_selector() -> Any:
    path = ROOT / SELECTOR_REL
    specification = importlib.util.spec_from_file_location(
        "g0143_frozen_stage_c_selector", path
    )
    require(
        specification is not None and specification.loader is not None,
        "cannot load frozen selector",
    )
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def absence_snapshot() -> dict[str, Any]:
    present = [path.relative_to(ROOT).as_posix() for path in FUTURE_SCIENTIFIC_PATHS if path.exists()]
    return {
        "paths_checked_for_existence_only": [
            path.relative_to(ROOT).as_posix() for path in FUTURE_SCIENTIFIC_PATHS
        ],
        "present": present,
    }


def prefix_profile_crosscheck(selector: Any, *, cases: int = 96) -> dict[str, Any]:
    rng = random.Random(0x0143C)
    digest = hashlib.sha256()
    for case in range(cases):
        total_rows = rng.randrange(2, 8)
        columns_count = rng.randrange(1, 9)
        rows = [
            [rng.randrange(-4, 5) for _ in range(columns_count)]
            for _ in range(total_rows)
        ]
        if not any(value for row in rows for value in row):
            rows[0][0] = 1
        columns, basis = selector.fixture_complete_basis(rows, prime=101)
        basis_rows = selector.matrix_rows(
            [columns[index] for index in basis["basis_sequences"]], total_rows
        )
        base_rows = rng.randrange(1, total_rows)
        pool_rows = total_rows - base_rows
        fast = selector.exact_prefix_rank_transcript(
            complete_basis_rows=basis_rows,
            base_rows=base_rows,
            pool_rows=pool_rows,
        )["ranks"]
        slow = selector.repeated_exact_prefix_ranks(
            basis_rows, base_rows, pool_rows
        )
        require(fast == slow, f"prefix-rank mismatch in case {case}")
        digest.update(json.dumps([rows, base_rows, fast], separators=(",", ":")).encode())
        digest.update(b"\n")
    return {
        "cases": cases,
        "mismatches": 0,
        "fixture_transcript_sha256": digest.hexdigest(),
    }


def late_dependency_conflict_escape(selector: Any) -> dict[str, Any]:
    # Base e1; two admitted growth rows e2,e3; then a skipped dependent row
    # e1+e2 whose target is 0 although its exact implied target is 1.
    rows = [
        [1, 0, 0],
        [0, 1, 0],
        [0, 0, 1],
        [1, 1, 0],
    ]
    target = [1, 0, 0, 0]
    columns, basis = selector.fixture_complete_basis(rows, prime=101)
    result = selector.exact_rank_selection(
        column_loader=columns.__getitem__,
        complete_basis=basis,
        target=target,
        base_rows=1,
        pool_rows=3,
        admit_rows=2,
        record_count=3,
    )
    basis_rows = selector.matrix_rows(
        [columns[index] for index in basis["basis_sequences"]], 4
    )
    omitted = selector.exact_dependency_certificate(
        complete_basis_rows=basis_rows,
        basis_sequences=basis["basis_sequences"],
        logical_target=target,
        preceding_logical_rows=[0, 1, 2],
        candidate_logical_row=3,
    )
    require(omitted["compatible"] is False, "hostile late row is not incompatible")
    separator = [int(value) for value in omitted["primitive_relation"]]
    replay = selector.exact_separator_replay(
        column_loader=columns.__getitem__,
        separator=separator,
        target=target,
        record_count=3,
    )
    escaped = (
        result["result"] == "SYNTHETIC_EXACT_RANK_LIMIT_SELECTED"
        and result["selected_pool_indices"] == [0, 1]
        and result["post_cap_unadmitted_pool_indices"] == [2]
        and result["incompatible_dependency"] is None
        and result["dependency_certificates"] == []
    )
    require(escaped, "frozen post-cap behavior changed; re-audit required")
    return {
        "hostile_fixture": "base_e1_then_growth_e2_e3_then_dependent_e1_plus_e2",
        "target": target,
        "prefix_ranks": result["prefix_rank_transcript"]["ranks"],
        "increments": result["prefix_rank_transcript"]["increments"],
        "selector_result": result["result"],
        "selected_pool_indices": result["selected_pool_indices"],
        "post_cap_unadmitted_pool_indices": result[
            "post_cap_unadmitted_pool_indices"
        ],
        "selector_incompatible_dependency": result["incompatible_dependency"],
        "omitted_dependency_compatible": omitted["compatible"],
        "omitted_primitive_relation": omitted["primitive_relation"],
        "omitted_target_pairing": omitted["primitive_target_pairing"],
        "independent_full_family_separator_replay": replay,
        "accepted_hostile_case": True,
    }


def minimal_g0139_gate_escape(selector: Any) -> dict[str, Any]:
    minimal = {
        "schema": selector.G0139_SCHEMA,
        "verdict": "PASS",
        "result": "CONSISTENT_RESIDUAL_T1",
        "subject": {
            "path": selector.relative(selector.G0135_STAGE_D_PATH),
            "sha256": selector.G0135_STAGE_D_SHA256,
        },
    }
    selector.validate_g0139_admission(minimal)
    omitted = [
        "evidence_class",
        "claim_boundary",
        "reviewer.same_model_lineage",
        "preregistration.outcome_aware",
        "git_custody",
        "source_audit_anchor",
        "input_custody.transitive_bound_inputs",
        "independently_recomputed",
        "hostile_controls",
    ]
    return {
        "accepted_hostile_case": True,
        "provided_top_level_keys": sorted(minimal),
        "omitted_required_semantics": omitted,
    }


def g0143_scientific_input_escape(selector: Any) -> dict[str, Any]:
    snapshot = {path: EXPECTED[path]["sha256"] for path in EXPECTED}
    receipt = {
        "schema": selector.G0143_SCHEMA,
        "verdict": "PASS",
        "scientific_manifest_observed": False,
        "scientific_input_observed": True,
        "scientific_output_observed": False,
        "subject": {
            "bindings": [
                {"path": path, "sha256": snapshot[path]} for path in sorted(snapshot)
            ]
        },
    }
    old_commit_for_path = selector.git_commit_for_path
    old_is_ancestor = selector.git_is_ancestor
    selector.git_commit_for_path = lambda _path: SUBJECT_COMMIT
    selector.git_is_ancestor = lambda _ancestor, _descendant, _label: None
    try:
        selector.validate_g0143_source_audit(
            receipt,
            snapshot=snapshot,
            stage_c_commit=SUBJECT_COMMIT,
            manifest_commit=SUBJECT_COMMIT,
        )
    finally:
        selector.git_commit_for_path = old_commit_for_path
        selector.git_is_ancestor = old_is_ancestor
    return {
        "accepted_hostile_case": True,
        "scientific_input_observed": True,
        "omitted_required_semantics": [
            "subject.git_commit",
            "preregistration binding",
            "evidence_class/T1 disclosure",
            "claim_boundary",
            "obligation verdicts",
        ],
        "test_scope": (
            "Git ancestry calls replaced only to isolate receipt-semantic validation; "
            "all six real subject path/SHA bindings were still checked"
        ),
    }


def stage_b_optional_binding_escape(selector: Any) -> dict[str, Any]:
    direction = [1, -2, 1, 0, 0, 0, 0, 0, 0, 0, 0]
    directions = [direction[:] for _ in range(selector.POOL_ROWS)]
    residuals = [1] * selector.POOL_ROWS
    encoded_coordinate = (1).to_bytes(8, "little", signed=True)
    row_digest = sha256_bytes(encoded_coordinate)
    rows = [
        {
            "index": index,
            "direction": direction[:],
            "exact_stage_a_residual": "1",
            "exact_candidate_dot": "1",
            "records": 1,
            "nonzero_hinge_coefficients": 1,
            "minimum_hinge_coefficient": 1,
            "maximum_hinge_coefficient": 1,
            "maximum_absolute_hinge_coefficient": 1,
            "hinge_coefficients_i64_le_sha256": row_digest,
            "hinge_coefficients": [1],
        }
        for index in range(selector.POOL_ROWS)
    ]
    receipt = {
        "schema": selector.STAGE_B_SCHEMA,
        "result": "EXACT_FULL_FAMILY_POOL128_COORDINATES",
        "pool_k": selector.POOL_ROWS,
        "pool_count": selector.POOL_ROWS,
        "records": 1,
        "hinge_entries": selector.POOL_ROWS,
        "pool_directions_i8_sha256": selector.digest_directions(directions),
        "pool_exact_residuals_decimal_lf_sha256": selector.digest_decimal_lf(
            residuals
        ),
        "directions": directions,
        "inputs_rehashed_at_end": True,
        "rows": rows,
        "direction_major_hinge_i64_le_sha256": sha256_bytes(
            encoded_coordinate * selector.POOL_ROWS
        ),
        "exact_candidate_dots": ["1"] * selector.POOL_ROWS,
        "exact_candidate_dots_decimal_lf_sha256": selector.digest_decimal_lf(
            residuals
        ),
        "unknown_top_level_field": "accepted",
    }
    parsed = selector.validate_stage_b_prices(
        receipt,
        manifest_sha256="0" * 64,
        stage_a_sha256="1" * 64,
        directions=directions,
        residuals=residuals,
        member_terms=[(0, 1)],
        expected_records=1,
    )
    require(len(parsed) == selector.POOL_ROWS, "Stage-B hostile fixture did not parse")
    return {
        "accepted_hostile_case": True,
        "omitted_binding_fields": [
            "manifest_path/manifest_sha256 or g0140_manifest",
            "stage_a_receipt",
            "candidate",
            "input_mutation_controls",
        ],
        "unknown_top_level_field_accepted": True,
        "rows_accepted": len(parsed),
    }


def source_audit_gate_static_check(selector: Any) -> dict[str, Any]:
    source = inspect.getsource(selector.validate_manifest)
    g0141_loaded = "load_json(G0141_SOURCE_AUDIT_PATH)" in source
    g0142_loaded = "load_json(G0142_SOURCE_AUDIT_PATH)" in source
    require(not g0141_loaded and not g0142_loaded, "source-audit gate implementation changed")
    actual: dict[str, Any] = {}
    for label, path in {
        "G-0141": selector.G0141_SOURCE_AUDIT_PATH,
        "G-0142": selector.G0142_SOURCE_AUDIT_PATH,
    }.items():
        value = json.loads(path.read_text(encoding="utf-8"))
        actual[label] = {
            "path": selector.relative(path),
            "sha256": sha256_path(path),
            "schema": value.get("schema"),
            "verdict": value.get("verdict"),
            "result": value.get("result"),
        }
    return {
        "validate_manifest_loads_g0141_receipt": g0141_loaded,
        "validate_manifest_loads_g0142_receipt": g0142_loaded,
        "actual_current_receipts": actual,
        "accepted_hostile_case": True,
    }


def isolated_rebuild_and_test() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="g0143-native-rebuild-") as raw:
        directory = Path(raw)
        rebuilt = directory / "ffpack_modular_pivots_v1"
        compile_evidence = run(
            [
                "g++",
                "-O2",
                "-std=c++17",
                "-fopenmp",
                NATIVE_SOURCE_REL,
                "-o",
                str(rebuilt),
                "-lblas",
                "-llapack",
                "-lgivaro",
                "-lgmpxx",
                "-lgmp",
            ]
        )
        require(compile_evidence["exit_code"] == 0, "isolated native rebuild failed")
        rebuilt_sha = sha256_path(rebuilt)
        frozen_sha = sha256_path(ROOT / NATIVE_BINARY_REL)
        require(rebuilt_sha == frozen_sha, "isolated native rebuild is not byte-identical")
        harness = run(
            [
                str(ROOT / ".venv/bin/python"),
                str(ROOT / NATIVE_TEST_REL),
                str(rebuilt),
            ]
        )
        require(harness["exit_code"] == 0, "rebuilt native hostile harness failed")
        return {
            "compile": compile_evidence,
            "rebuilt_sha256": rebuilt_sha,
            "frozen_sha256": frozen_sha,
            "byte_identical": True,
            "rebuilt_harness": harness,
        }


def command_checks() -> dict[str, Any]:
    selector_self_test = run([str(ROOT / LAUNCHER_REL), "--self-test"])
    native_harness = run(
        [
            str(ROOT / ".venv/bin/python"),
            str(ROOT / NATIVE_TEST_REL),
            str(ROOT / NATIVE_BINARY_REL),
        ]
    )
    static_preflight = run([str(ROOT / LAUNCHER_REL), "--static-preflight"])
    require(selector_self_test["exit_code"] == 0, "selector self-test failed")
    require(native_harness["exit_code"] == 0, "native harness failed")
    require(static_preflight["exit_code"] == 0, "static preflight failed")
    require("complete_matrix_rank_computation_run\": false" in static_preflight["stdout"], "static preflight scientific-run marker drift")
    require("scientific_result_written\": false" in static_preflight["stdout"], "static preflight result marker drift")
    return {
        "selector_self_test": selector_self_test,
        "native_harness": native_harness,
        "static_preflight": static_preflight,
    }


def write_exclusive(path: Path, value: object) -> None:
    path = path.resolve()
    require(path.parent == HERE.resolve(), "audit output must remain in reserved directory")
    encoded = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with path.open("xb") as destination:
        destination.write(encoded)
        destination.flush()
        os.fsync(destination.fileno())


def perform_audit() -> dict[str, Any]:
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    before_absence = absence_snapshot()
    require(not before_absence["present"], "future scientific artifact exists; audit must stop")
    require(sha256_path(PREREGISTRATION_PATH) == PREREGISTRATION_SHA256, "preregistration SHA drift")
    require(
        git_output("log", "-1", "--format=%H", "--", PREREGISTRATION_PATH.relative_to(ROOT).as_posix())
        == PREREGISTRATION_COMMIT,
        "preregistration commit drift",
    )
    initial = subject_bindings()
    selector = load_selector()
    commands = command_checks()
    rebuild = isolated_rebuild_and_test()
    prefix = prefix_profile_crosscheck(selector)

    hostile = {
        "post_cap_incompatible_dependency_accepted": late_dependency_conflict_escape(selector),
        "minimal_g0139_lookalike_accepted": minimal_g0139_gate_escape(selector),
        "g0143_scientific_input_true_accepted": g0143_scientific_input_escape(selector),
        "g0141_g0142_verdicts_not_parsed": source_audit_gate_static_check(selector),
        "stage_b_missing_bindings_and_unknown_key_accepted": stage_b_optional_binding_escape(selector),
    }

    final = subject_bindings()
    require(initial == final, "subject bytes changed during audit")
    after_absence = absence_snapshot()
    require(not after_absence["present"], "audit created or observed scientific artifact")

    findings = [
        {
            "id": "G0143-F01",
            "severity": "BLOCKING",
            "title": "Post-cap dependent rows are never checked for target compatibility",
            "evidence": (
                "exact_rank_selection limits its loop to the prefix ending at the 32nd "
                "rank-growing row (source lines 1431-1476). The synthetic exact fixture "
                "records ranks [1,2,3,3]; row 3 has primitive relation [1,1,0,-1], "
                "annihilates every column, and pairs 1 with the target, yet the selector "
                "returns SYNTHETIC_EXACT_RANK_LIMIT_SELECTED with no incompatible dependency."
            ),
            "impact": (
                "A future scientific run can label Stage C EXACT_RANK32_SELECTED while a "
                "later skipped Pool128 row already proves exact frozen-family target "
                "nonmembership. This violates G-0140 preregistration lines 153-157."
            ),
            "required_remediation": (
                "Keep the admission cap at 32, but traverse all 128 rows; derive and replay "
                "a certificate for every zero increment, including after the cap, and "
                "terminate on any target-incompatible dependence. Add this late-conflict fixture."
            ),
        },
        {
            "id": "G0143-F02",
            "severity": "BLOCKING",
            "title": "Stage C hash-binds but never authenticates G-0141/G-0142 audit verdicts",
            "evidence": (
                "validate_manifest has no load_json call for either source-audit path; it "
                "only requires their bindings. Both current bound candidates are verdict FAIL."
            ),
            "impact": (
                "A one-shot manifest can bind known failing source audits and still pass the "
                "Stage-C admission code, defeating the hard source-audit gate."
            ),
            "required_remediation": (
                "Add dedicated exact-schema validators for G-0141 and G-0142 requiring PASS, "
                "their bounded result/evidence fields, absence flags, exact subject bytes and "
                "commit ancestry; reject the currently failing receipts."
            ),
        },
        {
            "id": "G0143-F03",
            "severity": "BLOCKING",
            "title": "G-0139 admission accepts a minimal semantic lookalike",
            "evidence": (
                "validate_g0139_admission accepts only schema/PASS/result plus one recursive "
                "Stage-D path/hash pair. The hostile fixture omits evidence_class, outcome-aware "
                "preregistration, reviewer lineage, claim boundary, custody, source-audit anchor, "
                "transitive inputs, recomputation, and hostile controls and is accepted."
            ),
            "impact": "The mandatory G-0139 admission gate is materially weaker than its frozen contract.",
            "required_remediation": (
                "Validate the exact committed G-0139 receipt schema and all decision-bearing "
                "semantic/custody fields, not merely a recursive path/hash pair."
            ),
        },
        {
            "id": "G0143-F04",
            "severity": "BLOCKING",
            "title": "G-0143 self-admission omits scientific-input and review-boundary checks",
            "evidence": (
                "A receipt with scientific_input_observed=true and no subject commit, "
                "preregistration, evidence-class/T1, claim-boundary, or obligation fields is "
                "accepted when the real six path/SHA bindings and Git relation are supplied."
            ),
            "impact": "The future selector does not enforce the full outcome-blind audit contract it claims to consume.",
            "required_remediation": (
                "Require all three observation flags false plus exact audit result/evidence class, "
                "subject/preregistration commits and hashes, obligation verdicts, and claim boundary."
            ),
        },
        {
            "id": "G0143-F05",
            "severity": "BLOCKING",
            "title": "Stage-B input binding fields and exact top-level schema are optional",
            "evidence": (
                "validate_stage_b_prices accepts a 128-row synthetic receipt omitting every "
                "manifest, Stage-A, candidate and mutation-control field while also accepting "
                "an unknown top-level key."
            ),
            "impact": "Stage C can consume a structurally nearby Stage-B object without the advertised transitive bindings.",
            "required_remediation": (
                "Freeze an exact Stage-B key set and make the manifest, Stage-A, candidate, "
                "custody, and mutation-control bindings mandatory."
            ),
        },
    ]

    checks = [
        {"id": "SUBJECT_EXACT_BINDINGS", "passed": True, "evidence": initial},
        {"id": "NO_SCIENTIFIC_ARTIFACT_OBSERVED", "passed": True, "evidence": {"before": before_absence, "after": after_absence}},
        {"id": "EXEC_SELECTOR_SELF_TEST", "passed": True, "evidence": commands["selector_self_test"]},
        {"id": "EXEC_NATIVE_HARNESS", "passed": True, "evidence": commands["native_harness"]},
        {"id": "EXEC_STATIC_PREFLIGHT", "passed": True, "evidence": commands["static_preflight"]},
        {"id": "NATIVE_ISOLATED_REBUILD_BYTE_IDENTITY", "passed": True, "evidence": rebuild},
        {"id": "PREFIX_ROW_PROFILE_THEOREM_SYNTHETIC_CROSSCHECK", "passed": True, "evidence": prefix},
        {"id": "ALL_SKIPPED_DEPENDENCIES_CHECKED", "passed": False, "evidence": hostile["post_cap_incompatible_dependency_accepted"]},
        {"id": "G0141_G0142_EXACT_PASS_GATES", "passed": False, "evidence": hostile["g0141_g0142_verdicts_not_parsed"]},
        {"id": "G0139_COMPLETE_ADMISSION_SEMANTICS", "passed": False, "evidence": hostile["minimal_g0139_lookalike_accepted"]},
        {"id": "G0143_COMPLETE_OUTCOME_BLIND_SEMANTICS", "passed": False, "evidence": hostile["g0143_scientific_input_true_accepted"]},
        {"id": "STAGE_B_STRICT_REQUIRED_BINDINGS", "passed": False, "evidence": hostile["stage_b_missing_bindings_and_unknown_key_accepted"]},
        {"id": "SUBJECT_ENTRY_EXIT_REHASH", "passed": True, "evidence": {"initial_equals_final": initial == final, "final": final}},
    ]

    return {
        "schema": "max11-g0143-g0140-stage-c-source-audit-v1",
        "verdict": "FAIL",
        "result": "SOURCE_CUSTODY_AUDIT_FAIL_T1",
        "started_utc": started,
        "completed_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "reviewer": {
            "agent_name": "ChartreuseCondor",
            "program": "codex",
            "model": "GPT-5",
            "same_model_lineage": True,
            "independence_tier_ceiling": "T1",
            "prior_context_disclosure": (
                "Dispatch disclosed prior stale-binary, parser-binding, and rank-certificate defect classes; no source internals or future G-0140 result was supplied."
            ),
        },
        "preregistration": {
            "path": PREREGISTRATION_PATH.relative_to(ROOT).as_posix(),
            "sha256": PREREGISTRATION_SHA256,
            "git_commit": PREREGISTRATION_COMMIT,
            "frozen_before_source_inspection": True,
        },
        "checker": {
            "path": Path(__file__).resolve().relative_to(ROOT).as_posix(),
            "sha256": sha256_path(Path(__file__).resolve()),
        },
        "subject": {
            "git_commit": SUBJECT_COMMIT,
            "bindings": initial,
            "final_bindings": final,
            "initial_equals_final": initial == final,
        },
        "scientific_manifest_observed": False,
        "scientific_input_observed": False,
        "scientific_output_observed": False,
        "checks": checks,
        "failed_check_ids": [item["id"] for item in checks if not item["passed"]],
        "hostile_controls": hostile,
        "findings": findings,
        "positive_findings": [
            "Exact subject/source/native byte custody passed and the isolated rebuild was byte-identical.",
            "Committed selector self-test, static preflight, native asymmetric oracle and hostile I/O harness passed.",
            "The optimized transpose-RREF prefix-rank method matched direct exact ranks on all 96 preregistered deterministic synthetic cases.",
            "The exact complete-basis, dependency, primitive-separator, and full-family replay primitives behaved correctly on the audited tiny fixtures; the blocking rank defect is the post-cap traversal boundary, not those primitives."
        ],
        "minimum_decision_bearing_repairs": [
            "Inspect every dependent Pool128 row for target compatibility even after the 32-row admission cap, with a must-fail late-conflict fixture.",
            "Reject non-PASS or semantically incomplete G-0141/G-0142/G-0143/G-0139 receipts using exact schema/result/evidence/custody checks.",
            "Make Stage-B top-level schema and manifest/Stage-A/candidate/control bindings mandatory.",
            "Freeze new producer bytes and obtain a fresh source audit; this FAIL receipt cannot be carried forward."
        ],
        "claim_boundary": (
            "FAIL blocks this exact frozen Stage-C producer from a G-0140 scientific run. "
            "It does not show that any future rank is wrong, that the 163740-column family "
            "contains or excludes the target, that MAX11 has or lacks a network, or that any "
            "global/unrestricted theorem holds."
        ),
        "limitations": [
            "No future G-0140 scientific manifest, Stage-A/B input, or Stage-C/D/E output was opened, hashed, parsed, created, or run.",
            "Synthetic fixtures test code semantics and are not represented as live MAX11 evidence.",
            "Same-lineage T1 source review cannot supply T2 independence or mathematical promotion."
        ],
        "inputs_rehashed_at_end": True,
    }


def self_test() -> None:
    require(sha256_bytes(b"") == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855", "SHA self-test drift")
    bindings = subject_bindings()
    require(len(bindings) == 6, "subject binding census drift")
    original_digest = EXPECTED[SELECTOR_REL]["sha256"]
    EXPECTED[SELECTOR_REL]["sha256"] = "0" * 64
    mutation_rejected = False
    try:
        subject_bindings()
    except AuditError:
        mutation_rejected = True
    finally:
        EXPECTED[SELECTOR_REL]["sha256"] = original_digest
    require(mutation_rejected, "subject binding mutation was not rejected")
    selector = load_selector()
    late = late_dependency_conflict_escape(selector)
    require(late["accepted_hostile_case"] is True, "late-conflict detector lost potency")
    print("g0143-stage-c-source-audit-checker-self-test: PASS (binding mutation floor plus late-conflict detector)")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        require(args.output is None, "self-test takes no output")
        self_test()
        return 0
    require(args.output is not None, "--output is required")
    receipt = perform_audit()
    write_exclusive(args.output, receipt)
    print(
        "g0143-stage-c-source-audit: FAIL "
        f"({len(receipt['failed_check_ids'])} blocking checks; no scientific output observed)"
    )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
