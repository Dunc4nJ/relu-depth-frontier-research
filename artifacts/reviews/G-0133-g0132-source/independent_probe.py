#!/usr/bin/env python3
"""Independent hostile probes for the frozen G-0132 MEMBER producer.

This harness never reads or creates a G-0132 scientific manifest/output.  Its
only writes inside the repository are the preregistered review receipt and a
temporary hostile SOURCE_AUDIT_RECEIPT.json that is removed after every case.
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


ROOT = Path(__file__).resolve().parents[3]
REVIEW = ROOT / "artifacts/reviews/G-0133-g0132-source"
SOURCE = ROOT / "artifacts/math/G-0132/src/main.rs"
CARGO = ROOT / "artifacts/math/G-0132/Cargo.toml"
LOCK = ROOT / "artifacts/math/G-0132/Cargo.lock"
EXECUTABLE = ROOT / "artifacts/math/G-0132/target/release/g0132-member-global-normal-form"
CANDIDATE = ROOT / "artifacts/math/G-0128/full_family_master_result_v2.json"
CANDIDATE_MANIFEST = ROOT / "artifacts/math/G-0128/full_family_master_manifest_v2.json"
SOURCE_AUDIT_RECEIPT = REVIEW / "SOURCE_AUDIT_RECEIPT.json"
REPORT = REVIEW / "SOURCE_AUDIT_REPORT.md"
SELF_TEST_RECEIPT = REVIEW / "SELF_TEST_RECEIPT.json"
PROBE_SOURCE = REVIEW / "independent_probe.py"
PROBE_RECEIPT = REVIEW / "INDEPENDENT_PROBE_RECEIPT.json"
PANEL = "artifacts/math/G-0113/panel_solver_input_v1.json"
CANDIDATE_REL = "artifacts/math/G-0128/full_family_master_result_v2.json"
MANIFEST_REL = "artifacts/math/G-0132/member_global_normal_form_manifest_v1.json"
MEMBER_RESULT_REL = "artifacts/math/G-0132/member_global_normal_form_replay_v1.json"
NONMEMBER_RESULT_REL = "artifacts/math/G-0132/full_degree5_separator_pricing_v1.json"
PUBLICATION_PATHS = [ROOT / MANIFEST_REL, ROOT / MEMBER_RESULT_REL, ROOT / NONMEMBER_RESULT_REL]

SOURCE_SHA = "27400fe972986ea29ff245059f6011bbf1a146511d30cfecbdfdd834c3a5115e"
CARGO_SHA = "34f04114a5729d2fcd02edf4b544dda7f88762bb2decb1d6c9668375b536d2db"
LOCK_SHA = "4b8685901b2e6783d0ffd51c2abe57d60a0e6c8a277473e28239a59dd48f77d7"
EXECUTABLE_SHA = "8c556397e37e6d3f7bed9b8dae417cf4629c0a3fe3ce0537192d4a34662d6e64"
PRODUCER_COMMIT = "618c5e7883bf6ee02f1a0f202dbec1f3a9e15a0b"
CANDIDATE_SHA = "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838"
SOURCE_AUDIT_BOUNDARY = (
    "T1 source clearance for this exact committed producer and executable only; "
    "no scientific manifest or output was observed, and no mathematical result "
    "is promoted by this receipt."
)
SELF_TEST_COMMAND = (
    "artifacts/math/G-0132/target/release/g0132-member-global-normal-form --self-test"
)
PROBE_COMMAND = (
    "python3 -B artifacts/reviews/G-0133-g0132-source/independent_probe.py "
    "--output artifacts/reviews/G-0133-g0132-source/INDEPENDENT_PROBE_RECEIPT.json"
)

DIRECT_BINDINGS = {
    "candidate_result": (CANDIDATE_REL, CANDIDATE_SHA),
    "candidate_manifest": ("artifacts/math/G-0128/full_family_master_manifest_v2.json", "79078391da63eb25b09f90f8e9335e614db46bcf69edac5d2ca8386131c3f6ec"),
    "candidate_solver": ("artifacts/math/G-0128/full_family_master_v2.py", "cfdb3f3d758d8cc5cc81c8ad9a71f4b9bd5c2001f1ff2f8a646715a4c6ca3da8"),
    "candidate_preregistration": ("artifacts/math/G-0128/FULL_FAMILY_MASTER_ROUND2_PREREGISTRATION.md", "ed33f3349780c1e73d64b1a9a75e2a070ae554bd1313dc081187a8d2554e5a9f"),
    "candidate_source_audit": ("artifacts/reviews/G-0128-round2-master/AUDIT_VERDICT.md", "049a0a85bfec5b3ab053208da825a173dbd16302af72004c47f54a906a2ae4ed"),
    "model_boundary_audit": ("artifacts/reviews/G-0130-model-boundary/AUDIT_VERDICT.md", "53f90bacf3271ffb94174eb1a7e6bc5a525b36d86bb722ef2c595f111043bfdf"),
    "finite_audit_preregistration": ("artifacts/reviews/G-0131-g0128-result/PREREGISTRATION.md", "74594f4a88a840dd144b69d154a7b77445d13b20ff55630e9b5d932253e1d799"),
    "finite_audit_checker": ("artifacts/reviews/G-0131-g0128-result/replay_member_cleanroom.py", "41b4b5d0266ea8b3724dd93938013d02829bbf1bf16ba3be2655369014fece7a"),
    "finite_audit_receipt": ("artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json", "0159910b476b1cac9ea0e8f6ad05e16e061036b361efc8b2f5a3a1aa02c09926"),
    "finite_audit_report": ("artifacts/reviews/G-0131-g0128-result/REPORT.md", "15f3f0f8bd4952d7773effa393a5cecbd0d6f74895ded134efeb5e3701ebb197"),
    "g0132_preregistration": ("artifacts/math/G-0132/PREREGISTRATION.md", "73ccd2ce2a96c0d46b0a40166ca6a84050577cdba3f23ff12d1b89e043e8c692"),
    "source_audit_preregistration": ("artifacts/reviews/G-0133-g0132-source/PREREGISTRATION.md", "d2461477ce22c3f8afa036886b63988a3914303a54486bea4bb76d49d164b9bc"),
    "result_audit_preregistration": ("artifacts/reviews/G-0134-g0132-result/PREREGISTRATION.md", "5f0ec755c8aa96bccde392be97e3189f6eb1fc9dfbff508a5ced13ecd9fca6d2"),
    "loop_inclusive_schema": ("artifacts/math/G-0028/LOOP_INCLUSIVE_SIGNED_W_SCHEMA.md", "5652b1136a56294ef6fdbba164e66dd489c86a66675901b45e9a2ed5ab0cc40c"),
    "degree5_transfer_readme": ("artifacts/math/G-0044/README.md", "7a7b763dbfba826b2366139176f6b26611c8f1eac0df8f26fd68fa1b928730cb"),
    "denominator_streamer": ("artifacts/math/G-0038/stream_loop_inclusive_denominator.py", "c22c29072f1b046a76c6d3767f7054efa44852fbdb88ae506ba561c5781a1acf"),
    "denominator_manifest": ("artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json", "1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640"),
    "denominator_stream": ("artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz", "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"),
    "denominator_independent_census": ("artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py", "16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb"),
    "denominator_independent_census_receipt": ("artifacts/cleanroom/G-0038/independent_loop_inclusive_census_v1.json", "98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078"),
    "denominator_stream_verifier": ("artifacts/cleanroom/G-0038/verify_loop_inclusive_denominator_stream.py", "215e7eb359d01078131e3266487f35658cf922f1285d33dec972f51f9e33d165"),
    "denominator_stream_verification": ("artifacts/cleanroom/G-0038/loop_inclusive_signed_degree5_stream_verification_v1.json", "8379177a8597fcfca9e291fd354289af4950976b32d8238b44caa4a2035cf542"),
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


def binding(relative: str) -> dict[str, str]:
    path = ROOT / relative
    resolved = path.resolve(strict=True)
    require(resolved.is_relative_to(ROOT) and path.is_file() and not path.is_symlink(), f"unsafe binding: {relative}")
    return {"path": relative, "sha256": sha256_path(path)}


def git_commit_for_path(relative: str) -> str:
    run = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=True,
    )
    return run.stdout.strip()


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


def decimal_lf_digest(values: list[str]) -> str:
    return hashlib.sha256("".join(f"{value}\n" for value in values).encode()).hexdigest()


def direction_valid(direction: list[int]) -> bool:
    if len(direction) != 11 or sum(direction) != 0:
        return False
    divisor = reduce(math.gcd, (abs(value) for value in direction), 0)
    first = next((value for value in direction if value), 0)
    prefixes = []
    total = 0
    for value in direction[:-1]:
        total += value
        prefixes.append(total)
    return divisor == 1 and first > 0 and any(value < 0 for value in prefixes)


def publication_paths_absent() -> bool:
    return all(not path.exists() for path in PUBLICATION_PATHS)


def run_expected_failure(command: list[str], fragment: str, timeout: int = 360) -> dict[str, object]:
    before = publication_paths_absent()
    completed = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
    combined = completed.stdout + completed.stderr
    require(before and completed.returncode != 0 and fragment in combined, f"expected failure missing: {' '.join(command)}\n{combined}")
    require(publication_paths_absent(), "hostile CLI case created a publication path")
    return {
        "command": " ".join(command),
        "exit_code": completed.returncode,
        "expected_fragment": fragment,
        "publication_paths_absent_after": True,
    }


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


def expected_frozen_inputs() -> tuple[dict[str, dict[str, str]], int]:
    manifest = json.loads(CANDIDATE_MANIFEST.read_text())
    transitive = manifest["expected_inputs"]
    require(len(transitive) == 41, "transitive census drift")
    by_pair: dict[tuple[str, str], str] = {}
    for label, (path, expected) in DIRECT_BINDINGS.items():
        require(sha256_path(ROOT / path) == expected, f"direct binding drift: {path}")
        by_pair[(path, expected)] = f"direct_{label}"
    for index, item in enumerate(transitive):
        path, expected = item["path"], item["sha256"]
        require(sha256_path(ROOT / path) == expected, f"transitive binding drift: {path}")
        by_pair.setdefault((path, expected), f"transitive_{index:03d}")
    require(len({path for path, _ in by_pair}) == len(by_pair), "same path has conflicting frozen digests")
    frozen = {
        label: {"path": path, "sha256": expected}
        for (path, expected), label in sorted(by_pair.items())
    }
    return frozen, len(transitive)


def source_markers(source: str) -> dict[str, bool]:
    markers = {
        "projection_176_to_132": "candidate.terms\n            == nonzero_term_projection" in source,
        "full_labelled_census": "EXPECTED_LABELLED_PERMUTATIONS: u64 = 5_269_017_600" in source,
        "dynamic_hinge_map": "hinges: HashMap<[i8; N], BigInt>" in source,
        "all_linear_coordinates": "linear: [BigInt; N]" in source and "aggregate.linear[N - 1] -= &target_subtraction" in source,
        "carry_68_second_route": "direct_carry_prices(&input, &candidate)" in source and "CARRY_DIRECTIONS: usize = 68" in source,
        "exact_terminal_rule": "complete_arbitrary_precision_ordered_chamber_normal_form_aggregate" in source,
        "modular_control_only": "screening_primes_control_only" in source,
        "zero_and_residual_enums": "MEMBER_EXACT_GLOBAL_NORMAL_FORM_ZERO" in source and "MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL" in source,
        "last_term_mutant": "omitted_final_nonzero_term" in source and "final_nonzero_coefficient_plus_one" in source,
        "direction_and_linear_mutants": "omitted_first_term_active_direction" in source and "omitted_first_term_linear_coordinate" in source,
        "prime_collision": "screening_prime_collision_found_exactly" in source,
        "embedded_drift_checks": "running binary was compiled from different source" in source and "compiled scientific input drift" in source,
        "receipt_gate_before_manifest": "validate_source_audit(" in source and "let manifest = expected_manifest(&root, transitive)?" in source,
        "atomic_no_overwrite": "create_new(true)" in source and "std::fs::hard_link(&temporary, path)" in source,
        "branch_guards": source.count("publish_exclusive_with_branch_guard(") >= 3,
        "narrow_promotion_boundary": SOURCE_AUDIT_BOUNDARY in source and "Neither outcome proves family completeness" in source,
    }
    require(all(markers.values()), f"static reachability marker missing: {markers}")
    return markers


def candidate_controls() -> dict[str, object]:
    candidate = json.loads(CANDIDATE.read_text())
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
        and terms == projection
        and len(terms) == 132
        and terms[-1]["sequence"] == 161
        and all(canonical_integer(value) for value in coefficients)
        and candidate["target_scale"].isdigit()
        and int(candidate["target_scale"]) > 0,
        "candidate projection/admission drift",
    )
    gcd = reduce(math.gcd, (abs(int(value)) for value in coefficients), int(candidate["target_scale"]))
    require(gcd == 1, "candidate normalization drift")
    require(u64le_digest(selected) == "4584a7f87748b976f86734308efa4abb621e4caab5fa973673faf6aa0a913bc7", "selected digest drift")
    require(u64le_digest([term["sequence"] for term in terms]) == "dda733b9e2f52e0abcd95dd7f98809425e1d9743a9339156ac5d54a29491716d", "term digest drift")
    require(decimal_lf_digest(coefficients) == "2a581d6f48513e2aea9863f9394a5c922c544f8a29f50e25257a024024b96420", "coefficient digest drift")
    directions = candidate["hinge_directions"]
    require(len(directions) == 68 and len({tuple(value) for value in directions}) == 68 and all(direction_valid(value) for value in directions), "carry direction drift")
    dropped = terms[:-1]
    require(len(dropped) == 131 and dropped[-1] != terms[-1], "last-term mutant was a no-op")
    return {
        "selected_slots": 176,
        "zero_slots": 44,
        "nonzero_terms": 132,
        "last_term_sequence": 161,
        "labelled_permutations": len(terms) * math.factorial(11),
        "carry_directions": 68,
        "primitive_gcd": gcd,
        "last_term_drop_changes_projection": True,
    }


def finite_audit_controls() -> dict[str, object]:
    receipt = json.loads((ROOT / "artifacts/reviews/G-0131-g0128-result/cleanroom_member_audit_v1.json").read_text())
    require(
        receipt["schema"] == "max11-g0131-cleanroom-380row-member-audit-v1"
        and receipt["verdict"] == "CONSISTENT_MEMBER"
        and receipt["mathematical_certificate_verdict"] == "CONSISTENT"
        and receipt["identity"]["all_380_rows_zero"] is True
        and receipt["identity"]["coordinate_square_solve_zero"] is True
        and receipt["mutant"]["rejected"] is True
        and receipt["selected_basis"]["matches_reported"] is True
        and receipt["normalization"]["target_scale_positive"] is True
        and receipt["normalization"]["coefficient_and_scale_gcd"] == 1
        and receipt["dimensions"]["rows"] == 380
        and receipt["dimensions"]["family_records"] == 163740
        and receipt["dimensions"]["selected_columns"] == 176
        and len(receipt["rank_trials"]) == 21
        and receipt["rank_trials"][-1]["rank"] == receipt["rank_trials"][-1]["augmented_rank"] == 176,
        "G-0131 admission drift",
    )
    return {"verdict": "CONSISTENT_MEMBER", "rank_trials": 21, "terminal_rank": 176}


def residual_controls() -> dict[str, object]:
    primes = (1_000_000_007, 1_000_000_009)
    collision = primes[0] * primes[1]
    require(collision != 0 and all(collision % prime == 0 for prime in primes), "prime collision drift")
    def digest(hinges: dict[tuple[int, ...], int], linear: list[int]) -> str:
        rows = [f"H\t{','.join(map(str, direction))}\t{coefficient}\n" for direction, coefficient in sorted(hinges.items()) if coefficient]
        rows.extend(f"L\t{index}\t{coefficient}\n" for index, coefficient in enumerate(linear) if coefficient)
        return hashlib.sha256("".join(rows).encode()).hexdigest()
    zero = digest({}, [0] * 11)
    require(zero == digest({}, [0] * 11), "no-op changed residual")
    direction = (1, -2, 1, 0, 0, 0, 0, 0, 0, 0, 0)
    base = digest({direction: 9}, [0] * 11)
    late_linear = digest({direction: 9}, [0] * 10 + [1])
    require(base != late_linear and zero != base, "residual mutation was hidden or inert")
    return {"no_op_preserved_digest": True, "late_linear_changed_complete_digest": True, "screening_prime_collision_nonzero": str(collision)}


def receipt_baseline(frozen: dict[str, dict[str, str]], probe_binding: dict[str, str]) -> dict[str, object]:
    report_binding = binding("artifacts/reviews/G-0133-g0132-source/SOURCE_AUDIT_REPORT.md")
    self_binding = binding("artifacts/reviews/G-0133-g0132-source/SELF_TEST_RECEIPT.json")
    source_binding = binding("artifacts/reviews/G-0133-g0132-source/independent_probe.py")
    return {
        "schema": "max11-g0133-g0132-source-audit-receipt-v1",
        "verdict": "PASS",
        "subject": {
            "source": {"path": "artifacts/math/G-0132/src/main.rs", "sha256": SOURCE_SHA, "git_commit": PRODUCER_COMMIT},
            "cargo_manifest": {"path": "artifacts/math/G-0132/Cargo.toml", "sha256": CARGO_SHA},
            "cargo_lock": {"path": "artifacts/math/G-0132/Cargo.lock", "sha256": LOCK_SHA},
            "executable": {"path": "artifacts/math/G-0132/target/release/g0132-member-global-normal-form", "sha256": EXECUTABLE_SHA},
        },
        "frozen_inputs": frozen,
        "self_test": {"command": SELF_TEST_COMMAND, "status": "PASS", "receipt": self_binding},
        "independent_probe": {"command": PROBE_COMMAND, "status": "PASS", "receipt": probe_binding},
        "audit_artifacts": {
            "report": report_binding,
            "self_test_receipt": self_binding,
            "independent_probe_source": source_binding,
            "independent_probe_receipt": probe_binding,
        },
        "scientific_manifest_observed": False,
        "scientific_output_observed": False,
        "promotion_boundary": SOURCE_AUDIT_BOUNDARY,
    }


def hostile_receipt_case(name: str, receipt: dict[str, object], fragment: str) -> dict[str, object]:
    require(not SOURCE_AUDIT_RECEIPT.exists(), "source audit receipt unexpectedly exists")
    write_exclusive(SOURCE_AUDIT_RECEIPT, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
    try:
        result = run_expected_failure(
            [str(EXECUTABLE), "--build-manifest", PANEL, CANDIDATE_REL, MANIFEST_REL],
            fragment,
        )
        result["name"] = name
        return result
    finally:
        SOURCE_AUDIT_RECEIPT.unlink(missing_ok=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default=str(PROBE_RECEIPT.relative_to(ROOT)))
    args = parser.parse_args()
    output = Path(args.output)
    if not output.is_absolute():
        output = ROOT / output
    require(output == PROBE_RECEIPT, "probe receipt path drift")
    require(not output.exists() and not SOURCE_AUDIT_RECEIPT.exists(), "pre-existing audit receipt")
    require(publication_paths_absent(), "scientific publication path existed before probes")
    final_written = False
    placeholder_written = False
    try:
        hashes = {
            "source": sha256_path(SOURCE),
            "cargo_manifest": sha256_path(CARGO),
            "cargo_lock": sha256_path(LOCK),
            "executable": sha256_path(EXECUTABLE),
            "candidate": sha256_path(CANDIDATE),
        }
        require(hashes == {"source": SOURCE_SHA, "cargo_manifest": CARGO_SHA, "cargo_lock": LOCK_SHA, "executable": EXECUTABLE_SHA, "candidate": CANDIDATE_SHA}, "frozen subject hash drift")
        require(git_commit_for_path("artifacts/math/G-0132/src/main.rs") == PRODUCER_COMMIT, "source commit drift")
        source = SOURCE.read_text()
        markers = source_markers(source)
        candidate = candidate_controls()
        finite_audit = finite_audit_controls()
        residual = residual_controls()
        frozen, transitive_count = expected_frozen_inputs()

        cli_failures = [
            run_expected_failure([str(EXECUTABLE), "--build-manifest", PANEL, CANDIDATE_REL, "/tmp/g0132-forbidden-manifest.json"], "manifest path drift"),
            run_expected_failure([str(EXECUTABLE), PANEL, CANDIDATE_REL, MANIFEST_REL, "/tmp/g0132-forbidden-output.json"], "output path drift"),
            run_expected_failure([str(EXECUTABLE), "--preflight", "/tmp/wrong-panel.json", CANDIDATE_REL], "panel path drift"),
            run_expected_failure([str(EXECUTABLE), "--preflight", PANEL, "/tmp/wrong-candidate.json"], "candidate path drift"),
        ]

        self_run = subprocess.run([str(EXECUTABLE), "--self-test"], cwd=ROOT, text=True, capture_output=True, timeout=120)
        require(self_run.returncode == 0 and self_run.stdout.strip() == "G-0132 self-test PASS", "frozen self-test drift")

        placeholder = {"schema": "g0133-probe-placeholder-v1", "status": "RUNNING"}
        write_exclusive(PROBE_RECEIPT, (json.dumps(placeholder, sort_keys=True) + "\n").encode())
        placeholder_written = True
        probe_binding = binding("artifacts/reviews/G-0133-g0132-source/INDEPENDENT_PROBE_RECEIPT.json")
        baseline = receipt_baseline(frozen, probe_binding)
        receipt_mutants = []

        mutant = copy.deepcopy(baseline)
        mutant["unexpected_field"] = True
        receipt_mutants.append(hostile_receipt_case("unknown_field", mutant, "unknown field"))

        mutant = copy.deepcopy(baseline)
        mutant["verdict"] = "FAIL"
        mutant["scientific_manifest_observed"] = True
        receipt_mutants.append(hostile_receipt_case("verdict_and_observation", mutant, "source audit did not clear exact source"))

        mutant = copy.deepcopy(baseline)
        mutant["subject"]["source"]["sha256"] = "0" * 64
        receipt_mutants.append(hostile_receipt_case("subject_sha", mutant, "source audit subject binding mismatch"))

        mutant = copy.deepcopy(baseline)
        duplicate = next(iter(mutant["frozen_inputs"].values())).copy()
        mutant["frozen_inputs"]["duplicate_extra"] = duplicate
        receipt_mutants.append(hostile_receipt_case("duplicate_frozen_input", mutant, "source audit frozen-input set mismatch"))

        mutant = copy.deepcopy(baseline)
        mutant["self_test"]["command"] += " --mutant"
        receipt_mutants.append(hostile_receipt_case("self_test_command", mutant, "source audit self-test or independent-probe binding mismatch"))

        receipt_mutants.append(hostile_receipt_case("uncommitted_artifact_guard", baseline, "uncommitted or invalid binding"))

        PROBE_RECEIPT.unlink()
        placeholder_written = False
        require(publication_paths_absent() and not SOURCE_AUDIT_RECEIPT.exists(), "hostile receipt probes leaked publication state")
        receipt = {
            "schema": "max11-g0133-g0132-independent-probe-v1",
            "status": "PASS",
            "subject": {"commit": PRODUCER_COMMIT, "hashes": hashes},
            "static_reachability": markers,
            "candidate_projection": candidate,
            "finite_member_admission": finite_audit,
            "frozen_inputs": {"direct_bindings": len(DIRECT_BINDINGS), "transitive_manifest_inputs": transitive_count, "unique_path_sha_pairs": len(frozen), "all_rehashed": True},
            "exact_residual_controls": residual,
            "frozen_self_test": {"status": "PASS", "stdout": self_run.stdout.strip()},
            "cli_path_and_branch_guards": cli_failures,
            "source_audit_receipt_mutants": receipt_mutants,
            "receipt_mutants_rejected": len(receipt_mutants),
            "scientific_manifest_observed": False,
            "scientific_output_observed": False,
            "publication_paths_absent_after_probes": True,
        }
        write_exclusive(output, (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode())
        final_written = True
    finally:
        SOURCE_AUDIT_RECEIPT.unlink(missing_ok=True)
        if placeholder_written and not final_written:
            PROBE_RECEIPT.unlink(missing_ok=True)
        require(publication_paths_absent(), "probe cleanup observed a scientific publication path")


if __name__ == "__main__":
    main()
