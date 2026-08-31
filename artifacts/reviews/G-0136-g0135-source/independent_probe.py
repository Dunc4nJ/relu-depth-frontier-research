#!/usr/bin/env python3
"""Independent hostile probes for the frozen G-0135 Stage-A producer.

This file does not import or execute producer internals.  It reimplements the
exact coordinate recurrences in Python integers and compares them with a
temporary Rust program linked only to the separately pinned G-0117 kernel.
It never builds or reads a G-0135 scientific manifest or scientific output.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
import re
import subprocess
import tempfile
from functools import reduce
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "artifacts/reviews/G-0136-g0135-source"
SOURCE_REL = "artifacts/math/G-0135/src/main.rs"
CARGO_REL = "artifacts/math/G-0135/Cargo.toml"
LOCK_REL = "artifacts/math/G-0135/Cargo.lock"
EXECUTABLE_REL = "artifacts/math/G-0135/target/release/g0135-batch32-global-replay"
SOURCE = ROOT / SOURCE_REL
CARGO = ROOT / CARGO_REL
LOCK = ROOT / LOCK_REL
EXECUTABLE = ROOT / EXECUTABLE_REL
PANEL_REL = "artifacts/math/G-0113/panel_solver_input_v1.json"
CANDIDATE_REL = "artifacts/math/G-0128/full_family_master_result_v2.json"
CANDIDATE_MANIFEST_REL = "artifacts/math/G-0128/full_family_master_manifest_v2.json"
PRIOR_REPLAY_REL = "artifacts/math/G-0132/member_global_normal_form_replay_v1.json"
SOURCE_AUDIT_RECEIPT_REL = "artifacts/reviews/G-0136-g0135-source/SOURCE_AUDIT_RECEIPT.json"
REPORT_REL = "artifacts/reviews/G-0136-g0135-source/SOURCE_AUDIT_REPORT.md"
SELF_TEST_RECEIPT_REL = "artifacts/reviews/G-0136-g0135-source/SELF_TEST_RECEIPT.json"
PROBE_SOURCE_REL = "artifacts/reviews/G-0136-g0135-source/independent_probe.py"
PROBE_RECEIPT_REL = "artifacts/reviews/G-0136-g0135-source/INDEPENDENT_PROBE_RECEIPT.json"
SOURCE_AUDIT_RECEIPT = ROOT / SOURCE_AUDIT_RECEIPT_REL
REPORT = ROOT / REPORT_REL
SELF_TEST_RECEIPT = ROOT / SELF_TEST_RECEIPT_REL
PROBE_RECEIPT = ROOT / PROBE_RECEIPT_REL

SCIENTIFIC_PATHS = [
    ROOT / "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json",
    ROOT / "artifacts/math/G-0135/batch32_global_replay_v1.json",
    ROOT / "artifacts/math/G-0135/full_degree5_separator_pricing_v1.json",
]

PRODUCER_COMMIT = "e2f20e14076863737ea3c01fa78073f2c704eceb"
SOURCE_SHA = "6786760c2d9c6d11782ae0f2e7a7efed19ddb026e959cf50701b473a1d979668"
CARGO_SHA = "9d3db2f04d56a9979ca605a177b0a097ff1e44288c7b1a444a5281b3c524664b"
LOCK_SHA = "bb4c2eec22788cd3f705330b163a19638f7f55e87c4b6d659754a0485632811c"
EXECUTABLE_SHA = "f96dbdf5a8998f11629477e81ac0b8ef3fa860fb4e7e813e3ff5b2ccead2d897"
CANDIDATE_SHA = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838"
PRIOR_REPLAY_SHA = "d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50"
SOURCE_AUDIT_BOUNDARY = (
    "T1 source clearance for this exact committed producer and executable only; "
    "no scientific manifest or output was observed, and no mathematical result "
    "is promoted by this receipt."
)
SELF_TEST_COMMAND = f"{EXECUTABLE_REL} --self-test"
PROBE_COMMAND = f"python3 -B {PROBE_SOURCE_REL} --output {PROBE_RECEIPT_REL}"

EXPECTED_FIRST_DIRECTION = [0, 0, 0, 0, 0, 0, 1, -3, -2, 1, 3]
EXPECTED_FIRST_COEFFICIENT = (
    "363926958096805201036820427711562039306502598983761375638772015048437029843340726060005211433825934240455425251219346437121889771857125452344913600504791360"
)
EXPECTED_TARGET_SCALE = (
    "2289393005496338240468982655090335335732668690900751540287809289663720291914849699943112917639850352050294840444775090516901570116753181129941246082620"
)

# Independently transcribed from the preregistered custody graph.  The probe
# rehashes every entry and then submits the independently derived union to the
# producer's fail-closed validator; reaching the later uncommitted-artifact
# guard proves equality with the producer's own frozen set.
DIRECT_BINDINGS: dict[str, tuple[str, str]] = {
    "candidate_result": (CANDIDATE_REL, CANDIDATE_SHA),
    "candidate_manifest": (CANDIDATE_MANIFEST_REL, "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec"),
    "candidate_solver": ("artifacts/math/G-0128/full_family_master_v2.py", "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8"),
    "candidate_preregistration": ("artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md", "ed33f3349780c1e73d64b1a9a75e2a070ae554bd1313dc081187a8d2554e5a9f"),
    "candidate_source_audit": ("artifacts/reviews/G-0128-round2-master/AUDIT_VERDICT.md", "049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed"),
    "model_boundary_audit": ("artifacts/reviews/G-0130-model-boundary/AUDIT_VERDICT.md", "53f90bacf3271ffb94174eb1a7e6bc5a525b36d86bb722ef2c595f111043bfdf"),
    "finite_audit_preregistration": ("artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md", "74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799"),
    "finite_audit_checker": ("artifacts/reviews/G-0131-g0128-result/replay_member_cleanroom.py", "41b4b5d0266ea8b3724dd93938013d02829bbf1bf16ba3be2655369014fece7a"),
    "finite_audit_receipt": ("artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json", "0159910b476b1cac9ea0e8f6ad05e16e061036b361efc8b2f5a3a1aa02c09926"),
    "finite_audit_report": ("artifacts/reviews/G-0131-g0128-result/REPORT.md", "15f3f0f8bd4952d7773effa393a5cecbd0d6f74895ded134efeb5e3701ebb197"),
    "g0135_preregistration": ("artifacts/math/G-0135/PREREGISTRATION.md", "ca9ed1930a8b7539d92d7651caadd06c6bd77742ce11adff682af9ac067fe5ec"),
    "source_audit_preregistration": ("artifacts/reviews/G-0136-g0135-source/PREREGISTRATION.md", "ec8004a00549d205827c283a3d0f3665ebb4260ddc2964c9654869afd0fee66d"),
    "result_audit_preregistration": ("artifacts/reviews/G-0134-g0132-result/PREREGISTRATION.md", "5f0ec755c8aa96bccde392be97e3189f6eb1fc9dfbff508a5ced13ecd9fca6d2"),
    "prior_global_replay_result": (PRIOR_REPLAY_REL, PRIOR_REPLAY_SHA),
    "prior_global_replay_manifest": ("artifacts/math/G-0132/member_global_normal_form_manifest_v1.json", "b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732"),
    "prior_result_audit_checker": ("artifacts/reviews/G-0134-g0132-result/cleanroom_residual_reprice.py", "40109063ed2210b3a9ba11d52618d28e55eac9e5da7146d4bb0377b8da6fa9ee"),
    "prior_result_audit_receipt": ("artifacts/reviews/G-0134-g0132-result/RESIDUAL_AUDIT_RECEIPT.json", "a00aaca7aeb8f960d6fa5a264b72a13c797ae30a75c4eec5eaa90a5a455e2f56"),
    "prior_result_audit_report": ("artifacts/reviews/G-0134-g0132-result/REPORT.md", "98f592ccf0e4541fd596aea7691561342c761cb1e168a2fa1f1bec22c260d9f4"),
    "loop_inclusive_schema": ("artifacts/math/G-0028/LOOP_INCLUSIVE_SIGNED_W_SCHEMA.md", "5652b1136a56294ef6fdbba164e66dd489c86a66675901b45e9a2ed5ab0cc40c"),
    "degree5_transfer_readme": ("artifacts/math/G-0044/README.md", "7a7b763dbfba826b2366139176f6b26611c8f1eac0df8f26fd68fa1b928730cb"),
    "denominator_streamer": ("artifacts/math/G-0038/stream_loop_inclusive_denominator.py", "c22c29072f1b046a76c6d3767f7054efa44852fbdb88ae506ba561c5781a1acf"),
    "denominator_manifest": ("artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json", "1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640"),
    "denominator_stream": ("artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz", "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"),
    "denominator_independent_census": ("artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py", "16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb"),
    "denominator_independent_census_receipt": ("artifacts/cleanroom/G-0038/independent_loop_inclusive_census_v1.json", "98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078"),
    "denominator_stream_verifier": ("artifacts/cleanroom/G-0038/verify_loop_inclusive_denominator_stream.py", "215e7eb359d01078131e3266487f35658cf922f1285d33dec972f51f9e33d165"),
    "denominator_stream_verification": ("artifacts/cleanroom/G-0038/loop_inclusive_signed_degree5_stream_verification_v1.json", "8379177a8597fcfca9e291fd354289af4950976b32d8238b44caa4a2035cf542"),
    "stages_bc_source_audit_preregistration": ("artifacts/reviews/G-0137-g0135-stages-bc-source/PREREGISTRATION.md", "e2bda62986001208e4e611ae147071b6932dc9ed99449aa4f54fcd178771948f"),
    "stages_bc_source_audit_receipt": ("artifacts/reviews/G-0137-g0135-stages-bc-source/SOURCE_AUDIT_RECEIPT.json", "9b6c8cb9492cb57cbf4dff589ed0d97437ae195ed0635eeaf0fe9b12052f956d"),
    "stage_d_source_audit_preregistration": ("artifacts/reviews/G-0138-g0135-stage-d-source/PREREGISTRATION.md", "b63b0ee0d36b1a91da3a35740ab026b7cec833950715189cef473ef1a86e6b8a"),
    "stage_d_source_audit_receipt": ("artifacts/reviews/G-0138-g0135-stage-d-source/SOURCE_AUDIT_RECEIPT.json", "f4e62ee4cd5311f74393e3141161512b62c65ebc9409c1ba5a8811019a2ec944"),
    "stage_b_source": ("artifacts/math/G-0135/stage_b_pricer/src/main.rs", "c591504757815ff63c46d29cfcc2ac10568bea92212ade32490def93b5d862b2"),
    "stage_b_cargo_manifest": ("artifacts/math/G-0135/stage_b_pricer/Cargo.toml", "a4057885f58199feb18e733ca01c7ec2a00dc05d8f2700a6dcb04f56825af11d"),
    "stage_b_cargo_lock": ("artifacts/math/G-0135/stage_b_pricer/Cargo.lock", "72315f7a541bf34fe135a25e651d2d85a885652944bdcac6862fb770d29669d3"),
    "stage_b_executable": ("artifacts/math/G-0135/stage_b_pricer/target/release/g0135-stage-b-batch32-coordinate-pricer", "e2e84801749bc0f2ca7bf18a149895531038ee0eab68f964b01ad25f1a3de7ef"),
    "stage_c_source": ("artifacts/math/G-0135/stage_c_master/full_family_master_v3.py", "c84f259d393756c9ff658aab9a1488b145b9607a939dbccfce47069168b40a1a"),
    "stage_c_executable": ("artifacts/math/G-0135/stage_c_master/run-full-family-master-v3", "b125566098be17edc0a572b776e1887813758afc7412324c29408592275ab508"),
    "python_solver_requirements": ("requirements-solvers.lock", "dae95ec0dd59c0b30ea69bfe541248049cee612a92d56c4d18e0c3217c170fb8"),
    "python_solver_wheel_hashes": ("environment/python-wheel-hashes.txt", "68c90da2eecf3285c99ad135ef142070c830fe4b14a4a35ebec265e6ffb3b311"),
    "solver_toolchain_manifest": ("environment/toolchain-manifest.txt", "a4e7b09efb4d445b9a34217f0aff478771c36542ca8c4d58e5b15e9d6273b81e"),
    "solver_toolchain_document": ("TOOLCHAIN.md", "ffc55f711d52c90f4a1710cfd55366b2d1249a736db97f17c3a1c3e52188f150"),
    "stage_d_source": ("artifacts/math/G-0135/stage_d_global_replay/src/main.rs", "e120f0b1ef7b8465cfcd6d8ae1cd389b6554c19cff1d6f7ae3e8fbc8bace8665"),
    "stage_d_engine": ("artifacts/math/G-0135/stage_d_global_replay/src/engine.rs", "b92b1b1e1f3a88df5c88846f95d67175a161529733587659ddddf03c9425ae2c"),
    "stage_d_cargo_manifest": ("artifacts/math/G-0135/stage_d_global_replay/Cargo.toml", "0dc8c61a7114b7b3625f86f550ae682ac650b21081b7b0a70d19802a337bb4da"),
    "stage_d_cargo_lock": ("artifacts/math/G-0135/stage_d_global_replay/Cargo.lock", "13f29a23a9883e0ec61774532534819df16dcc86599b427952c06da6600f8d18"),
    "stage_d_executable": ("artifacts/math/G-0135/stage_d_global_replay/target/release/g0135-stage-d-global-replay", "1d4142782ff6a81e77162b5c599a71985c934f455b128507519c911a749e63b4"),
}

DIRECTIONS = [
    [0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1],
    EXPECTED_FIRST_DIRECTION,
    [1, -2, 0, 0, 0, 0, 0, 0, 0, 0, 1],
    [0, 0, 0, 0, 0, 0, 0, 1, -3, 1, 1],
    [0, 1, -1, 1, -1, 1, -1, -1, 1, 0, 0],
]
NEAR_FRONTIER_RECORD = {
    "sequence": 2**63 - 1,
    "signed_mass": 5,
    "active_vertices": 10,
    "negative_edges": [[0, 1], [2, 3], [4, 5], [6, 7], [8, 9]],
    "positive_edges": [[0, 9], [1, 2], [3, 4], [5, 6], [7, 8]],
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def safe_repo_file(relative: str) -> Path:
    raw = Path(relative)
    require(not raw.is_absolute() and all(part not in {"", ".", ".."} for part in raw.parts), f"unsafe path: {relative}")
    cursor = ROOT
    for part in raw.parts:
        cursor = cursor / part
        require(not cursor.is_symlink(), f"symlink path component: {relative}")
    resolved = cursor.resolve(strict=True)
    require(resolved.is_relative_to(ROOT) and resolved.is_file(), f"path escapes or is not a file: {relative}")
    return resolved


def binding(relative: str) -> dict[str, str]:
    path = safe_repo_file(relative)
    return {"path": relative, "sha256": sha256_path(path)}


def git_output(args: list[str]) -> bytes:
    completed = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, check=True)
    return completed.stdout


def git_commit_for_path(relative: str) -> str:
    commit = git_output(["log", "-1", "--format=%H", "--", relative]).decode().strip()
    require(re.fullmatch(r"[0-9a-f]{40}", commit) is not None, f"invalid commit for {relative}")
    return commit


def git_blob_sha256(commit: str, relative: str) -> str:
    return hashlib.sha256(git_output(["show", f"{commit}:{relative}"])).hexdigest()


def canonical_integer(raw: str) -> bool:
    if raw == "0":
        return True
    digits = raw[1:] if raw.startswith("-") else raw
    return bool(digits) and not digits.startswith("0") and digits.isascii() and digits.isdigit()


def u64le_digest(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(value.to_bytes(8, "little", signed=False))
    return digest.hexdigest()


def direction_stream_digest(directions: list[list[int]]) -> str:
    return hashlib.sha256(bytes(coordinate & 0xFF for direction in directions for coordinate in direction)).hexdigest()


def decimal_lf_digest(values: list[str]) -> str:
    require(all(canonical_integer(value) for value in values), "noncanonical decimal stream")
    return hashlib.sha256("".join(f"{value}\n" for value in values).encode()).hexdigest()


def direction_valid(direction: list[int]) -> bool:
    if len(direction) != 11 or sum(direction) != 0:
        return False
    divisor = reduce(math.gcd, (abs(value) for value in direction), 0)
    first = next((value for value in direction if value), 0)
    prefix = 0
    active = False
    for value in direction[:-1]:
        prefix += value
        active |= prefix < 0
    return divisor == 1 and first > 0 and active and all(-128 <= value <= 127 for value in direction)


def scientific_paths_absent() -> bool:
    return all(not path.exists() for path in SCIENTIFIC_PATHS)


def write_exclusive(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp.{os.getpid()}")
    require(not path.exists() and not temporary.exists(), f"refusing overwrite: {path}")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.link(temporary, path)
        temporary.unlink()
        directory_fd = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    except BaseException:
        temporary.unlink(missing_ok=True)
        path.unlink(missing_ok=True)
        raise


def function_slice(source: str, name: str) -> str:
    match = re.search(rf"^fn {re.escape(name)}\s*\(", source, re.MULTILINE)
    require(match is not None, f"missing function: {name}")
    next_match = re.search(r"^fn [A-Za-z0-9_]+\s*\(", source[match.end() :], re.MULTILINE)
    end = len(source) if next_match is None else match.end() + next_match.start()
    return source[match.start() : end]


def source_controls(source: str) -> dict[str, bool]:
    selection = function_slice(source, "select_residual_batch")
    direction_digest = function_slice(source, "selected_direction_digest")
    residual_digest = function_slice(source, "selected_residual_digest")
    run = function_slice(source, "run")
    preflight = function_slice(source, "preflight")
    manifest = function_slice(source, "expected_manifest")
    source_audit = function_slice(source, "validate_source_audit")
    publication = function_slice(source, "publish_exclusive")
    validated_form = function_slice(source, "validated_full_normal_form")
    add_exact = function_slice(source, "add_exact")
    controls = {
        "subject_hash_literal": SOURCE_SHA not in source,
        "projection_176_to_132": "nonzero_term_projection" in source and "candidate.terms\n            == nonzero_term_projection" in source,
        "arbitrary_precision_aggregate": "hinges: HashMap<[i8; N], BigInt>" in source and "linear: [BigInt; N]" in source and "coefficient: &BigInt" in add_exact,
        "target_subtraction_bigint": "parse_bigint(&candidate.target_scale)? * BigInt::from(factorial(N))" in run and "aggregate.linear[N - 1] -= &target_subtraction" in run,
        "complete_labelled_census": "EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_269_017_600" in source and "validate_term_receipts(&aggregate.term_receipts)?" in run,
        "exact_then_bounded_crosscheck": "exact_full_normal_form(record)?" in validated_form and "exact_matches_pinned(record, &form)?" in validated_form,
        "pinned_bound_cannot_decide": "pinned diagnostic kernel exceeded its proved frozen-domain bound" in source and "return Ok(form)" not in validated_form,
        "signed_lex_nonzero_first32": "collect::<BTreeMap<_, _>>()" in selection and selection.index(".filter(") < selection.index(".take(BATCH_K)") < selection.index(".map("),
        "no_modular_selection": "decimal_mod(" not in selection and "SCREENING_PRIMES" not in selection,
        "all_11_linear_zero_gate": "aggregate\n            .linear\n            .iter()\n            .all" in selection,
        "all_68_carry_zero_gate": "direct_carry_prices(&input, &candidate)?" in run and "first_carry_forward_failure.is_none()" in run,
        "direction_i8_bytes": "digest.update([coordinate as u8])" in direction_digest,
        "coefficient_decimal_lf": "digest.update(item.coefficient.as_bytes())" in residual_digest and "digest.update(b\"\\n\")" in residual_digest,
        "g0132_reconciliation_precedes_selection": run.index("prior_g0132_reconciled") < run.index("select_residual_batch"),
        "g0132_full_anchor_set": all(token in run for token in ["EXPECTED_HINGE_ENTRIES_PROCESSED", "EXPECTED_AGGREGATE_HINGE_SUPPORT", "EXPECTED_NONZERO_HINGE_DIRECTIONS", "EXPECTED_AGGREGATE_HINGE_SHA256", "EXPECTED_NONZERO_HINGE_SHA256", "EXPECTED_TERM_TRANSCRIPT_SHA256", "EXPECTED_FIRST_DIRECTION", "EXPECTED_FIRST_COEFFICIENT"]),
        "receipt_checks_observation_flags": "!receipt.scientific_manifest_observed" in source_audit and "!receipt.scientific_output_observed" in source_audit,
        "receipt_checks_all_four_nonfinal_commits": "for artifact in artifacts" in source_audit and "git_commit_for_path(root, &artifact.path)?" in source_audit,
        "preflight_calls_source_audit_chain": "expected_manifest(&root, transitive)?" in preflight,
        "manifest_calls_source_audit": "validate_source_audit(" in manifest,
        "end_rehash_before_publication": run.index("load_and_validate_inputs") < run.rindex("load_and_validate_inputs") < run.index("publish_exclusive_with_branch_guard"),
        "manifest_end_rehash": source.count("input/source drift during manifest pre-serialization") == 1,
        "atomic_no_overwrite": "create_new(true)" in publication and "std::fs::hard_link(&temporary, path)" in publication and publication.count("sync_all()") >= 2,
        "branch_guard": "opposite or premature branch output raced publication" in source,
        "compiled_source_cargo_lock": all(token in source for token in ["COMPILED_SOURCE", "COMPILED_MANIFEST", "COMPILED_LOCK", "running binary was compiled from different source"]),
        "path_containment_and_no_symlinks": "symlink input path forbidden" in source and "input escapes repository" in source,
        "hostile_controls_reachable": all(token in run for token in ["first_nonzero_coefficient_plus_one", "final_nonzero_coefficient_plus_one", "omitted_final_nonzero_term", "omitted_first_term_active_direction", "omitted_first_term_linear_coordinate", "omitted_last_orbit_contribution_rejected"]),
        "science_boundary_literal": SOURCE_AUDIT_BOUNDARY in source,
    }
    require(all(controls.values()), f"source structural control failed: {controls}")
    return controls


def expected_frozen_inputs() -> tuple[dict[str, dict[str, str]], int]:
    manifest = json.loads(safe_repo_file(CANDIDATE_MANIFEST_REL).read_text())
    require(manifest["schema"] == "max11-g0128-full-family-master-manifest-v2", "candidate manifest schema drift")
    require(manifest["rows"] == 380 and manifest["records"] == 163_740, "candidate manifest dimension drift")
    transitive = manifest["expected_inputs"]
    require(len(DIRECT_BINDINGS) == 46 and len(transitive) == 41, "frozen input census drift")
    pairs: dict[tuple[str, str], str] = {}
    path_to_sha: dict[str, str] = {}
    for label, (path, expected) in DIRECT_BINDINGS.items():
        require(sha256_path(safe_repo_file(path)) == expected, f"direct binding drift: {path}")
        require(path not in path_to_sha or path_to_sha[path] == expected, f"direct path conflict: {path}")
        path_to_sha[path] = expected
        pairs[(path, expected)] = f"direct_{label}"
    seen_transitive: set[str] = set()
    for index, item in enumerate(transitive):
        path, expected = item["path"], item["sha256"]
        require(path not in seen_transitive, f"duplicate transitive path: {path}")
        seen_transitive.add(path)
        require(sha256_path(safe_repo_file(path)) == expected, f"transitive binding drift: {path}")
        require(path not in path_to_sha or path_to_sha[path] == expected, f"cross-set path conflict: {path}")
        path_to_sha[path] = expected
        pairs.setdefault((path, expected), f"transitive_{index:03d}")
    require(len(pairs) == 87 and len(path_to_sha) == 87, "frozen union cardinality drift")
    frozen = {
        label: {"path": path, "sha256": expected}
        for (path, expected), label in sorted(pairs.items())
    }
    return frozen, len(transitive)


def candidate_controls() -> dict[str, Any]:
    candidate = json.loads(safe_repo_file(CANDIDATE_REL).read_text())
    selected = candidate["selected_sequences"]
    support = candidate["support_sequences"]
    coefficients = candidate["integer_coefficients"]
    terms = candidate["terms"]
    projection = [
        {"sequence": sequence, "coefficient": coefficient}
        for sequence, coefficient in zip(selected, coefficients, strict=True)
        if coefficient != "0"
    ]
    require(
        candidate["schema"] == "max11-g0128-full-family-master-result-v2"
        and candidate["result"] == "FULL_FAMILY_380ROW_EXACT_Q_MEMBER"
        and len(selected) == len(support) == len(coefficients) == 176
        and selected == support
        and all(left < right for left, right in zip(selected, selected[1:]))
        and sum(value == "0" for value in coefficients) == 44
        and all(canonical_integer(value) for value in coefficients)
        and terms == projection
        and len(terms) == 132
        and terms[-1]["sequence"] == 161
        and candidate["target_scale"] == EXPECTED_TARGET_SCALE,
        "candidate projection or identity drift",
    )
    primitive_gcd = reduce(math.gcd, (abs(int(value)) for value in coefficients), int(candidate["target_scale"]))
    require(primitive_gcd == 1, "candidate primitive normalization drift")
    require(u64le_digest(selected) == "4584a7f87748b976f86734308efa4abb621e4caab5fa973673faf6aa0a913bc7", "selected-sequence digest drift")
    require(u64le_digest([term["sequence"] for term in terms]) == "dda733b9e2f52e0abcd95dd7f98809425e1d9743a9339156ac5d54a29491716d", "term-support digest drift")
    require(decimal_lf_digest(coefficients) == "2a581d6f48513e2aea9863f9394a5c922c544f8a29f50e25257a024024b96420", "coefficient digest drift")
    carried = candidate["hinge_directions"]
    require(len(carried) == 68 and len({tuple(value) for value in carried}) == 68 and all(direction_valid(value) for value in carried), "68-direction carry set drift")
    return {
        "selected_slots": len(selected),
        "zero_selected_coefficients": sum(value == "0" for value in coefficients),
        "nonzero_terms": len(terms),
        "last_term_sequence": terms[-1]["sequence"],
        "projection_exact": terms == projection,
        "primitive_gcd": primitive_gcd,
        "complete_labelled_permutations": len(terms) * math.factorial(11),
        "carry_directions": len(carried),
    }


def prior_g0132_controls() -> dict[str, Any]:
    prior_path = safe_repo_file(PRIOR_REPLAY_REL)
    require(sha256_path(prior_path) == PRIOR_REPLAY_SHA, "prior replay hash drift")
    prior = json.loads(prior_path.read_text())
    require(
        prior["schema"] == "max11-g0132-member-global-normal-form-replay-v1"
        and prior["result"] == "MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL"
        and prior["terms"] == 132
        and prior["hinge_entries_processed"] == 4_579_906
        and prior["labelled_permutations_checked"] == 5_269_017_600
        and prior["aggregate_hinge_support"] == 163_036
        and prior["nonzero_hinge_directions"] == 162_929
        and prior["aggregate_hinge_decimal_lf_sha256"] == "955a80d8d6ecab4afd873249e764595dcb750e7d1b5385044d6f5c2b19b55c5c"
        and prior["nonzero_hinge_decimal_lf_sha256"] == "ff51e40c67556bdf813797620e6994ba3d6312f1222c00ed8a44617337ec66c2"
        and prior["term_normal_form_transcript_sha256"] == "5b4efbbd4cca06252545c89e52503b20ba332cd59eeb477d05d09a5a688a62ba"
        and prior["first_nonzero_hinge"] == {"direction": EXPECTED_FIRST_DIRECTION, "coefficient": EXPECTED_FIRST_COEFFICIENT}
        and prior["first_nonzero_linear"] is None
        and len(prior["carry_forward_checks"]) == 68
        and all(item["coefficient"] == "0" and item["exact_zero"] is True for item in prior["carry_forward_checks"])
        and prior["linear_residuals_after_target"] == ["0"] * 11
        and prior["inputs_rehashed_at_end"] is True,
        "G-0132 exact reconciliation anchor drift",
    )
    return {
        "hash": PRIOR_REPLAY_SHA,
        "terms": prior["terms"],
        "labelled_permutations": prior["labelled_permutations_checked"],
        "aggregate_hinge_support": prior["aggregate_hinge_support"],
        "nonzero_hinge_directions": prior["nonzero_hinge_directions"],
        "first_direction": prior["first_nonzero_hinge"]["direction"],
        "first_coefficient": prior["first_nonzero_hinge"]["coefficient"],
        "carry_zero_count": len(prior["carry_forward_checks"]),
        "linear_zero_count": len(prior["linear_residuals_after_target"]),
    }


def record_core(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": int(record["sequence"]),
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_edges": [[int(a), int(b)] for a, b in record["negative_edges"]],
        "positive_edges": [[int(a), int(b)] for a, b in record["positive_edges"]],
    }


def increment_table(record: dict[str, Any]) -> list[list[int]]:
    active = record["active_vertices"]
    require(0 <= record["signed_mass"] <= 5 and active <= 11, "record domain drift")
    require(len(record["negative_edges"]) == len(record["positive_edges"]) == record["signed_mass"], "record mass drift")
    matrix = [[0] * active for _ in range(active)]
    for sign, edges in [(-1, record["negative_edges"]), (1, record["positive_edges"])]:
        for u, v in edges:
            require(0 <= u < v < active, "record is not compact loopless")
            matrix[u][v] += sign
            matrix[v][u] += sign
    table = [[0] * (1 << active) for _ in range(active)]
    for vertex in range(active):
        for mask in range(1, 1 << active):
            bit = mask & -mask
            other = bit.bit_length() - 1
            table[vertex][mask] = table[vertex][mask ^ bit] + matrix[vertex][other]
    return table


def matching_injections(table: list[list[int]], active: int, direction: list[int], scale: int) -> int:
    full = (1 << active) - 1
    inactive = 11 - active
    current = [0] * (1 << active)
    current[0] = 1
    for rank, coordinate in enumerate(direction):
        expected = scale * coordinate
        next_counts = [0] * (1 << active)
        for mask, count in enumerate(current):
            if count == 0:
                continue
            placed = mask.bit_count()
            if placed > rank:
                continue
            inactive_used = rank - placed
            if expected == 0 and inactive_used < inactive:
                next_counts[mask] += count
            for vertex in range(active):
                bit = 1 << vertex
                if mask & bit == 0 and table[vertex][mask] == expected:
                    next_counts[mask | bit] += count
        current = next_counts
    return current[full]


def exact_hinge_coefficients(record: dict[str, Any], directions: list[list[int]]) -> list[int]:
    require(all(direction_valid(direction) for direction in directions), "invalid probe direction")
    table = increment_table(record)
    active = record["active_vertices"]
    return [
        sum(abs(scale) * matching_injections(table, active, direction, scale) for scale in range(-5, 6) if scale) * math.factorial(11 - active)
        for direction in directions
    ]


def exact_linear_vector(record: dict[str, Any]) -> list[int]:
    table = increment_table(record)
    active = record["active_vertices"]
    inactive = 11 - active
    current = [[0, 0, 0] for _ in range(1 << active)]
    current[0][0] = 1
    correction = [0] * 11
    for rank in range(11):
        next_counts = [[0, 0, 0] for _ in range(1 << active)]
        for mask, counts in enumerate(current):
            placed = mask.bit_count()
            if placed > rank:
                continue
            inactive_used = rank - placed
            for status, count in enumerate(counts):
                if count == 0:
                    continue
                if inactive_used < inactive:
                    next_counts[mask][status] += count
                for vertex in range(active):
                    bit = 1 << vertex
                    if mask & bit:
                        continue
                    increment = table[vertex][mask]
                    new_status = status if status or increment == 0 else (1 if increment > 0 else 2)
                    new_mask = mask | bit
                    next_counts[new_mask][new_status] += count
                    if new_status == 2:
                        remaining_slots = 11 - rank - 1
                        remaining_active = active - new_mask.bit_count()
                        remaining_inactive = remaining_slots - remaining_active
                        completions = math.factorial(remaining_slots) // math.factorial(remaining_inactive)
                        correction[rank] += count * increment * completions
        current = next_counts
    injections = sum(current[(1 << active) - 1])
    require(injections * math.factorial(inactive) == math.factorial(11), "independent linear census failed")
    return [10 * rank * math.factorial(9) + correction[rank] * math.factorial(inactive) for rank in range(11)]


def rust_helper_source() -> str:
    directions = json.dumps(DIRECTIONS)
    near = json.dumps(NEAR_FRONTIER_RECORD)
    direction_fixture = json.dumps([EXPECTED_FIRST_DIRECTION, DIRECTIONS[2]])
    coefficient_fixture = json.dumps([EXPECTED_FIRST_COEFFICIENT, "-1", "0", "42"])
    return f'''use g0117_global_coordinate_pricer::{{hinge_coefficients, linear_vector, Record}};
use serde_json::{{json, Value}};
use sha2::{{Digest, Sha256}};
use std::fs;

fn main() {{
    let panel: Value = serde_json::from_slice(&fs::read(std::env::args().nth(1).unwrap()).unwrap()).unwrap();
    let records: Vec<Record> = serde_json::from_value(panel["records"].clone()).unwrap();
    let near: Record = serde_json::from_value(serde_json::from_str::<Value>(r#"{near}"#).unwrap()).unwrap();
    let directions: Vec<[i8; 11]> = serde_json::from_str(r#"{directions}"#).unwrap();
    let cases = vec![("panel_sequence_0", records[0].clone()), ("panel_sequence_1", records[1].clone()), ("active10_near_frontier", near)];
    let mut output = Vec::new();
    for (name, record) in cases {{
        output.push(json!({{
            "name": name,
            "active_vertices": record.active_vertices,
            "coefficients": hinge_coefficients(&record, &directions).unwrap(),
            "linear": linear_vector(&record).unwrap(),
        }}));
    }}
    let direction_fixture: Vec<[i8; 11]> = serde_json::from_str(r#"{direction_fixture}"#).unwrap();
    let mut direction_digest = Sha256::new();
    for direction in direction_fixture {{ for coordinate in direction {{ direction_digest.update([coordinate as u8]); }} }}
    let coefficient_fixture: Vec<String> = serde_json::from_str(r#"{coefficient_fixture}"#).unwrap();
    let mut coefficient_digest = Sha256::new();
    for value in coefficient_fixture {{ coefficient_digest.update(value.as_bytes()); coefficient_digest.update(b"\\n"); }}
    println!("{{}}", json!({{
        "cases": output,
        "direction_stream_sha256": format!("{{:x}}", direction_digest.finalize()),
        "coefficient_stream_sha256": format!("{{:x}}", coefficient_digest.finalize()),
    }}));
}}
'''


def exact_vs_pinned_controls(panel: dict[str, Any]) -> dict[str, Any]:
    cases = [
        ("panel_sequence_0", record_core(panel["records"][0])),
        ("panel_sequence_1", record_core(panel["records"][1])),
        ("active10_near_frontier", copy.deepcopy(NEAR_FRONTIER_RECORD)),
    ]
    python_cases = []
    for name, record in cases:
        python_cases.append({
            "name": name,
            "active_vertices": record["active_vertices"],
            "coefficients": exact_hinge_coefficients(record, DIRECTIONS),
            "linear": exact_linear_vector(record),
        })

    with tempfile.TemporaryDirectory(prefix="g0136-pinned-helper-") as temporary_raw:
        temporary = Path(temporary_raw)
        (temporary / "src").mkdir()
        cargo = f'''[package]
name = "g0136-independent-pinned-helper"
version = "0.1.0"
edition = "2024"

[dependencies]
g0117-global-coordinate-pricer = {{ path = "{ROOT / 'artifacts/math/G-0117'}" }}
serde_json = "1.0"
sha2 = "0.10"
'''
        (temporary / "Cargo.toml").write_text(cargo)
        (temporary / "src/main.rs").write_text(rust_helper_source())
        environment = os.environ.copy()
        environment["CARGO_TARGET_DIR"] = str(temporary / "target")
        completed = subprocess.run(
            ["cargo", "run", "--release", "--quiet", "--offline", "--manifest-path", str(temporary / "Cargo.toml"), "--", str(ROOT / PANEL_REL)],
            cwd=ROOT,
            env=environment,
            text=True,
            capture_output=True,
            timeout=600,
        )
        require(completed.returncode == 0, f"temporary pinned helper failed:\n{completed.stdout}\n{completed.stderr}")
        pinned = json.loads(completed.stdout)

    require(pinned["cases"] == python_cases, "independent exact/pinned kernel disagreement")
    require(any(value != 0 for value in python_cases[-1]["coefficients"]), "near-frontier direction set was uninformative")
    first = python_cases[0]["coefficients"][0]
    second = python_cases[1]["coefficients"][0]
    require(7 * first - 6 * second == 662_784 and 8 * first - 6 * second == 786_432, "planted known-answer drift")

    coefficient_mutant = copy.deepcopy(python_cases)
    coefficient_mutant[-1]["coefficients"][0] += 1
    require(coefficient_mutant != pinned["cases"], "coefficient-plus-one kernel mutant escaped")
    linear_mutant = copy.deepcopy(python_cases)
    linear_mutant[-1]["linear"][-1] += 1
    require(linear_mutant != pinned["cases"], "linear-plus-one kernel mutant escaped")

    direction_fixture = [EXPECTED_FIRST_DIRECTION, DIRECTIONS[2]]
    coefficient_fixture = [EXPECTED_FIRST_COEFFICIENT, "-1", "0", "42"]
    python_direction_digest = direction_stream_digest(direction_fixture)
    python_coefficient_digest = decimal_lf_digest(coefficient_fixture)
    require(python_direction_digest == pinned["direction_stream_sha256"], "signed-i8 byte semantics disagree with Rust")
    require(python_coefficient_digest == pinned["coefficient_stream_sha256"], "decimal-LF semantics disagree with Rust")
    reordered = list(reversed(direction_fixture))
    coefficient_plus_one = coefficient_fixture.copy()
    coefficient_plus_one[0] = str(int(coefficient_plus_one[0]) + 1)
    require(direction_stream_digest(reordered) != python_direction_digest, "direction order mutant escaped")
    require(decimal_lf_digest(coefficient_plus_one) != python_coefficient_digest, "coefficient digest mutant escaped")
    require(hashlib.sha256("".join(coefficient_fixture).encode()).hexdigest() != python_coefficient_digest, "missing-LF mutant escaped")
    require(not canonical_integer("01") and not canonical_integer("-0"), "noncanonical decimal mutant escaped")

    return {
        "method": "fresh_python_arbitrary_precision_dp_vs_temporary_rust_pinned_g0117_helper",
        "directions_checked_per_case": len(DIRECTIONS),
        "cases": python_cases,
        "planted_known_answer": {"seven_minus_six": 662_784, "eight_minus_six": 786_432},
        "active10_near_frontier_checked": True,
        "coefficient_plus_one_mutant_rejected": True,
        "linear_plus_one_mutant_rejected": True,
        "direction_stream_sha256": python_direction_digest,
        "coefficient_stream_sha256": python_coefficient_digest,
        "direction_reorder_mutant_rejected": True,
        "coefficient_digest_mutant_rejected": True,
        "missing_lf_mutant_rejected": True,
        "noncanonical_decimal_mutants_rejected": True,
    }


def independent_mutation_controls() -> dict[str, Any]:
    contribution_a = 123_648
    contribution_b = 34_272
    aggregate = 7 * contribution_a - 6 * contribution_b
    omitted = -6 * contribution_b
    require(aggregate != omitted, "omitted contribution was inert")
    expected_census = 132 * math.factorial(11)
    visited = [math.factorial(11)] * 132
    require(sum(visited) == expected_census, "honest census fixture failed")
    visited[-1] -= 1
    require(sum(visited) != expected_census, "one-orbit census mutant escaped")
    directions = [EXPECTED_FIRST_DIRECTION, DIRECTIONS[2]]
    direction_digest = direction_stream_digest(directions)
    swapped = directions.copy()
    swapped[0], swapped[1] = swapped[1], swapped[0]
    require(direction_stream_digest(swapped) != direction_digest, "direction-order mutant escaped")
    coefficients = [EXPECTED_FIRST_COEFFICIENT, "-7"]
    coefficient_digest = decimal_lf_digest(coefficients)
    mutated = coefficients.copy()
    mutated[0] = str(int(mutated[0]) + 1)
    require(decimal_lf_digest(mutated) != coefficient_digest, "residual coefficient mutant escaped")
    return {
        "coefficient_plus_one_rejected": True,
        "direction_order_rejected": True,
        "omitted_contribution_rejected": True,
        "one_labelled_permutation_census_deficit_rejected": True,
        "residual_digest_mutation_rejected": True,
    }


def run_expected_failure(command: list[str], fragment: str, timeout: int = 420) -> dict[str, Any]:
    require(scientific_paths_absent(), "scientific path existed before hostile CLI case")
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    combined = completed.stdout + completed.stderr
    require(completed.returncode != 0 and fragment in combined, f"expected failure missing: {' '.join(command)}\n{combined}")
    require(scientific_paths_absent(), "hostile CLI case created a scientific path")
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "expected_fragment": fragment,
        "scientific_paths_absent_after": True,
    }


def baseline_source_receipt(frozen: dict[str, dict[str, str]], probe_receipt_binding: dict[str, str]) -> dict[str, Any]:
    report_binding = binding(REPORT_REL)
    self_test_binding = binding(SELF_TEST_RECEIPT_REL)
    probe_source_binding = binding(PROBE_SOURCE_REL)
    return {
        "schema": "max11-g0136-g0135-source-audit-v1",
        "verdict": "PASS",
        "subject": {
            "source": {"path": SOURCE_REL, "sha256": SOURCE_SHA, "git_commit": PRODUCER_COMMIT},
            "cargo_manifest": {"path": CARGO_REL, "sha256": CARGO_SHA},
            "cargo_lock": {"path": LOCK_REL, "sha256": LOCK_SHA},
            "executable": {"path": EXECUTABLE_REL, "sha256": EXECUTABLE_SHA},
        },
        "frozen_inputs": frozen,
        "self_test": {"command": SELF_TEST_COMMAND, "status": "PASS", "receipt": self_test_binding},
        "independent_probe": {"command": PROBE_COMMAND, "status": "PASS", "receipt": probe_receipt_binding},
        "audit_artifacts": {
            "report": report_binding,
            "self_test_receipt": self_test_binding,
            "independent_probe_source": probe_source_binding,
            "independent_probe_receipt": probe_receipt_binding,
        },
        "scientific_manifest_observed": False,
        "scientific_output_observed": False,
        "promotion_boundary": SOURCE_AUDIT_BOUNDARY,
    }


def hostile_receipt_case(name: str, receipt: dict[str, Any], fragment: str) -> dict[str, Any]:
    require(not SOURCE_AUDIT_RECEIPT.exists(), "temporary source-audit receipt collision")
    write_exclusive(SOURCE_AUDIT_RECEIPT, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    try:
        result = run_expected_failure(
            [str(EXECUTABLE), "--preflight", PANEL_REL, CANDIDATE_REL],
            fragment,
        )
        result["name"] = name
        return result
    finally:
        SOURCE_AUDIT_RECEIPT.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=PROBE_RECEIPT_REL)
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    require(output == PROBE_RECEIPT, "probe receipt path drift")
    require(not output.exists() and not SOURCE_AUDIT_RECEIPT.exists(), "pre-existing audit receipt")
    require(REPORT.is_file() and SELF_TEST_RECEIPT.is_file(), "report/self-test receipt must precede probe")
    require(scientific_paths_absent(), "scientific path existed before probe")
    placeholder_written = False
    final_written = False
    try:
        hashes = {
            "source": sha256_path(SOURCE),
            "cargo_manifest": sha256_path(CARGO),
            "cargo_lock": sha256_path(LOCK),
            "executable": sha256_path(EXECUTABLE),
            "candidate": sha256_path(safe_repo_file(CANDIDATE_REL)),
        }
        require(hashes == {"source": SOURCE_SHA, "cargo_manifest": CARGO_SHA, "cargo_lock": LOCK_SHA, "executable": EXECUTABLE_SHA, "candidate": CANDIDATE_SHA}, "replacement subject hash drift")
        require(git_commit_for_path(SOURCE_REL) == PRODUCER_COMMIT, "replacement source commit drift")
        for relative, expected in [(SOURCE_REL, SOURCE_SHA), (CARGO_REL, CARGO_SHA), (LOCK_REL, LOCK_SHA), (EXECUTABLE_REL, EXECUTABLE_SHA)]:
            require(git_blob_sha256(PRODUCER_COMMIT, relative) == expected, f"subject commit blob drift: {relative}")

        source = SOURCE.read_text()
        static = source_controls(source)
        frozen, transitive_count = expected_frozen_inputs()
        candidate = candidate_controls()
        prior = prior_g0132_controls()
        panel = json.loads(safe_repo_file(PANEL_REL).read_text())
        exact_vs_pinned = exact_vs_pinned_controls(panel)
        mutants = independent_mutation_controls()

        release_self_test = subprocess.run([str(EXECUTABLE), "--self-test"], cwd=ROOT, text=True, capture_output=True, timeout=180)
        require(release_self_test.returncode == 0 and release_self_test.stdout.strip() == "G-0135 self-test PASS", "release self-test drift")

        preflight_failures = [
            run_expected_failure([str(EXECUTABLE), "--preflight", PANEL_REL, CANDIDATE_REL], SOURCE_AUDIT_RECEIPT_REL),
            run_expected_failure([str(EXECUTABLE), "--preflight", "/tmp/g0136-wrong-panel.json", CANDIDATE_REL], "panel path drift"),
            run_expected_failure([str(EXECUTABLE), "--preflight", PANEL_REL, "/tmp/g0136-wrong-candidate.json"], "candidate path drift"),
            run_expected_failure([str(EXECUTABLE), "--build-manifest", PANEL_REL, CANDIDATE_REL, "/tmp/g0136-forbidden-manifest.json"], "manifest path drift"),
            run_expected_failure([str(EXECUTABLE), PANEL_REL, CANDIDATE_REL, "artifacts/math/G-0135/batch32_global_replay_manifest_v1.json", "/tmp/g0136-forbidden-output.json"], "output path drift"),
        ]

        placeholder = {"schema": "max11-g0136-probe-placeholder-v1", "status": "RUNNING"}
        write_exclusive(PROBE_RECEIPT, (json.dumps(placeholder, sort_keys=True) + "\n").encode())
        placeholder_written = True
        baseline = baseline_source_receipt(frozen, binding(PROBE_RECEIPT_REL))
        receipt_mutants = []

        mutant = copy.deepcopy(baseline)
        mutant["unknown_field"] = True
        receipt_mutants.append(hostile_receipt_case("unknown_field", mutant, "unknown field"))

        mutant = copy.deepcopy(baseline)
        mutant["verdict"] = "FAIL"
        mutant["scientific_manifest_observed"] = True
        receipt_mutants.append(hostile_receipt_case("verdict_and_observation", mutant, "source audit did not clear exact source"))

        mutant = copy.deepcopy(baseline)
        mutant["subject"]["source"]["sha256"] = "0" * 64
        receipt_mutants.append(hostile_receipt_case("source_sha", mutant, "source audit subject binding mismatch"))

        mutant = copy.deepcopy(baseline)
        mutant["subject"]["source"]["git_commit"] = "0" * 40
        receipt_mutants.append(hostile_receipt_case("source_commit", mutant, "source audit subject binding mismatch"))

        mutant = copy.deepcopy(baseline)
        duplicate = next(iter(mutant["frozen_inputs"].values())).copy()
        mutant["frozen_inputs"]["duplicate_extra"] = duplicate
        receipt_mutants.append(hostile_receipt_case("duplicate_frozen_input", mutant, "source audit frozen-input set mismatch"))

        mutant = copy.deepcopy(baseline)
        first_key = next(iter(mutant["frozen_inputs"]))
        mutant["frozen_inputs"][first_key]["sha256"] = "0" * 64
        receipt_mutants.append(hostile_receipt_case("frozen_input_sha", mutant, "source audit frozen-input set mismatch"))

        mutant = copy.deepcopy(baseline)
        mutant["self_test"]["command"] += " --mutant"
        receipt_mutants.append(hostile_receipt_case("self_test_command", mutant, "source audit self-test or independent-probe binding mismatch"))

        mutant = copy.deepcopy(baseline)
        mutant["audit_artifacts"]["report"]["sha256"] = "0" * 64
        receipt_mutants.append(hostile_receipt_case("audit_artifact_sha", mutant, "source audit self-test or independent-probe binding mismatch"))

        receipt_mutants.append(hostile_receipt_case("uncommitted_artifact_guard", baseline, "uncommitted or invalid binding"))

        PROBE_RECEIPT.unlink()
        placeholder_written = False
        require(scientific_paths_absent() and not SOURCE_AUDIT_RECEIPT.exists(), "hostile probes leaked scientific/audit state")
        receipt = {
            "schema": "max11-g0136-g0135-independent-probe-v1",
            "status": "PASS",
            "subject": {"commit": PRODUCER_COMMIT, "hashes": hashes},
            "static_source_controls": static,
            "candidate_projection": candidate,
            "prior_g0132_reconciliation": prior,
            "frozen_inputs": {
                "direct_bindings": len(DIRECT_BINDINGS),
                "transitive_manifest_inputs": transitive_count,
                "unique_path_sha_pairs": len(frozen),
                "all_rehashed": True,
                "producer_set_equality_reached_later_uncommitted_guard": True,
            },
            "exact_vs_pinned": exact_vs_pinned,
            "independent_hostile_mutants": mutants,
            "release_self_test": {"status": "PASS", "stdout": release_self_test.stdout.strip()},
            "preflight_and_path_failures": preflight_failures,
            "source_audit_receipt_mutants": receipt_mutants,
            "receipt_mutants_rejected": len(receipt_mutants),
            "scientific_manifest_observed": False,
            "scientific_output_observed": False,
            "scientific_paths_absent_after_probes": True,
        }
        write_exclusive(output, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        final_written = True
    finally:
        SOURCE_AUDIT_RECEIPT.unlink(missing_ok=True)
        if placeholder_written and not final_written:
            PROBE_RECEIPT.unlink(missing_ok=True)
        require(scientific_paths_absent(), "probe cleanup observed a scientific path")


if __name__ == "__main__":
    main()
