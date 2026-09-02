#!/usr/bin/env python3
"""Fail-closed verifier for the committed gmp.13 code and light-custody outputs."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile


UNIVERSE_SHA256 = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
UNIVERSE_RECORDS = 7_015_841
PRIME = 1_000_003
CERTIFICATE_HASHES = {
    5: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    7: "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
}
SAMPLE_HASHES = {
    "sample_benchmark_n11.jsonl": "5b1e373e911673460598ed46d053e36f8b0f06bf250c73f7a639304ae512dfe3",
    "sample_loopless_n11.jsonl": "39601c0e2322c793ed885ba35d721621f35adeb19727d144490b5dc9dd992c0d",
    "sample_python_n9.jsonl": "c37d70e8d8938a13b9cca069dbc83961056c7afc857bde8e4703f98344ebc390",
    "sample_python_n10.jsonl": "e3c95e261dfa47c827d6b492987fe0f1c205df83fda03b9bf68924b60b7ee51d",
}
LOOP_COUNTS = {
    "0": 754_017,
    "1": 1_805_136,
    "2": 2_026_736,
    "3": 1_413_037,
    "4": 686_507,
    "5": 246_170,
    "6": 67_098,
    "7": 14_376,
    "8": 2_428,
    "9": 308,
    "10": 28,
}
MASS_COUNTS = {
    "0": 1,
    "1": 5,
    "2": 107,
    "3": 3_198,
    "4": 134_193,
    "5": 6_878_337,
}


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text())
    require(isinstance(value, dict), f"{path} is not a JSON object")
    return value


def pair(report: dict[str, object], numerator: str, denominator: str, expected: int) -> None:
    require(
        report.get(numerator) == expected and report.get(denominator) == expected,
        f"{numerator}/{denominator} is not {expected}/{expected}",
    )


def validate_universe_report(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "universe audit did not pass")
    pair(report, "records_checked", "record_denominator", UNIVERSE_RECORDS)
    pair(report, "strata_checked", "strata_denominator", 46)
    require(report.get("universe_compressed_sha256") == UNIVERSE_SHA256, "audit universe hash")
    require(report.get("record_count_by_signed_mass") == MASS_COUNTS, "signed-mass counts")
    require(
        report.get("record_count_by_total_signed_loop_occurrences") == LOOP_COUNTS,
        "loop-occurrence counts",
    )
    require(report.get("loopless_records") == 754_017, "loopless count")
    require(report.get("loop_bearing_records") == 6_261_824, "loop-bearing count")
    require(sum(LOOP_COUNTS.values()) == UNIVERSE_RECORDS, "loop count denominator")
    require(sum(MASS_COUNTS.values()) == UNIVERSE_RECORDS, "mass count denominator")


def validate_certificates(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "certificate controls did not pass")
    pair(report, "certificates_passed", "certificate_denominator", 2)
    pair(report, "templates_checked", "template_denominator", 60)
    pair(report, "exact_max_identities_passed", "exact_max_identity_denominator", 2)
    pair(report, "diagonal_sign_mutants_rejected", "diagonal_sign_mutant_denominator", 2)
    pair(report, "minimum_coordinate_control_passed", "minimum_coordinate_control_denominator", 1)
    require(int(report.get("minimum_coordinate_control_d0_hinges", 0)) > 0, "no d0 hinge")
    rows = report.get("rows")
    require(isinstance(rows, list) and len(rows) == 2, "certificate row denominator")
    for row in rows:
        require(isinstance(row, dict), "certificate row type")
        n = int(row["n"])
        require(row.get("input_sha256") == CERTIFICATE_HASHES[n], f"n={n} certificate hash")
        require(row.get("exact_max_identity") is True, f"n={n} exact identity")
        require(
            row.get("exact_dp_literal_matches") == row.get("terms_checked_denominator"),
            f"n={n} literal permutation gate",
        )


def validate_cross(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "cross-validation did not pass")
    pair(report, "python_dp_matches", "python_dp_denominator", 2_000)
    pair(report, "modular_binary_matches", "modular_binary_denominator", 16)
    require(report.get("modular_binary_modulus") == PRIME, "cross prime")
    samples = report.get("python_dp_samples")
    require(isinstance(samples, dict), "cross sample table")
    for name in ("n9", "n10"):
        row = samples.get(name)
        require(isinstance(row, dict), f"missing cross {name}")
        require(row.get("matches") == 1_000 and row.get("denominator") == 1_000, name)
        require(row.get("loop_bearing_records") == 1_000, f"{name} loop-bearing denominator")
    carriers = report.get("carrier_controls")
    require(isinstance(carriers, dict), "carrier controls")
    pair(carriers, "exact_base_atoms", "exact_base_atom_denominator", 2)
    pair(carriers, "modular_base_atoms", "modular_base_atom_denominator", 2)
    require(carriers.get("modulus") == PRIME, "carrier prime")
    require(carriers.get("binary_magic") == "MCOLGEN1", "carrier binary magic")
    require(carriers.get("five_loops_minimum_coordinate") == 18_144_000, "5L coefficient")
    require(carriers.get("five_nonloops_minimum_coordinate") == 0, "5E coefficient")


def validate_loopless(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "loopless parity did not pass")
    pair(report, "native_dependency_matches", "record_denominator", 1_000)
    pair(report, "production_dependency_matches", "record_denominator", 1_000)
    require(report.get("records_checked") == 1_000, "loopless checked denominator")


def validate_benchmark(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "benchmark did not pass")
    pair(report, "sample_size", "sample_denominator", 1_000)
    require(report.get("sample_loop_bearing_records") == 890, "benchmark loop-bearing sample")
    require(report.get("universe_records") == UNIVERSE_RECORDS, "benchmark universe count")
    require(report.get("base_atoms") == 2, "benchmark carriers")
    require(report.get("projected_columns") == 7_015_843, "projected column denominator")
    require(report.get("threads") == 4, "benchmark thread count")
    require(report.get("sample_sha256") == SAMPLE_HASHES["sample_benchmark_n11.jsonl"], "sample hash")
    require(report.get("minimum_coordinate_hinge_records") == 886, "d0 record count")
    require(report.get("minimum_coordinate_hinge_record_denominator") == 1_000, "d0 denominator")
    require(
        report.get("minimum_coordinate_hinges_denominator") == report.get("sampled_hinges_numerator"),
        "d0 hinge denominator",
    )
    require(float(report.get("wall_seconds", 0.0)) > 0.0, "benchmark wall time")


def validate_final_smoke(report: dict[str, object]) -> None:
    require(report.get("result") == "PASS", "final binary smoke did not pass")
    pair(report, "prefix_records_checked", "prefix_record_denominator", 8)
    pair(report, "stream_direct_exact_matches", "stream_direct_exact_denominator", 8)
    pair(report, "python_dp_matches", "python_dp_denominator", 8)
    pair(report, "modular_matches", "modular_denominator", 8)
    pair(
        report,
        "planted_modular_mutants_rejected",
        "planted_modular_mutant_denominator",
        1,
    )
    require(report.get("modulus") == PRIME, "final smoke prime")
    require(report.get("mcolgen_magic") == "MCOLGEN1", "final smoke magic")
    require(report.get("universe_compressed_sha256") == UNIVERSE_SHA256, "smoke universe hash")


def count_universe(universe: Path) -> None:
    with gzip.open(universe, "rb") as handle:
        header = json.loads(handle.readline())
        require(header.get("record_type") == "header", "G-0038 header type")
        require(header.get("n") == 11, "G-0038 n")
        require(header.get("branch_edge_occurrences") == 5, "G-0038 k")
        require(header.get("loops_allowed") is True, "G-0038 loop flag")
        require(header.get("expected_record_count") == UNIVERSE_RECORDS, "G-0038 header count")
        count = sum(1 for line in handle if line)
    require(count == UNIVERSE_RECORDS, f"G-0038 line count {count}/{UNIVERSE_RECORDS}")


def validate_samples(artifact_dir: Path) -> None:
    for name, expected_hash in SAMPLE_HASHES.items():
        path = artifact_dir / name
        require(sha256_path(path) == expected_hash, f"{name} hash")
        rows = [json.loads(line) for line in path.read_text().splitlines() if line]
        require(len(rows) == 1_000, f"{name} denominator")
        require(len({int(row["sequence"]) for row in rows}) == 1_000, f"{name} duplicate sequence")


def run_control(command: list[str], cwd: Path) -> None:
    subprocess.run(command, cwd=cwd, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-runtime", action="store_true", help="skip Cargo and current-binary reruns")
    args = parser.parse_args()
    artifact_dir = Path(__file__).resolve().parent
    root = artifact_dir.parents[2]
    crate = root / "tools/colgen-loops"
    universe = root / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"

    require(sha256_path(universe) == UNIVERSE_SHA256, "G-0038 compressed SHA-256")
    count_universe(universe)
    validate_samples(artifact_dir)
    universe_report = load_json(artifact_dir / "universe_audit.json")
    validate_universe_report(universe_report)
    validate_certificates(load_json(artifact_dir / "certificate_controls.json"))
    validate_cross(load_json(artifact_dir / "cross_validation.json"))
    validate_loopless(load_json(artifact_dir / "loopless_parity.json"))
    validate_benchmark(load_json(artifact_dir / "benchmark_n11.json"))
    committed_smoke = load_json(artifact_dir / "final_binary_smoke.json")
    validate_final_smoke(committed_smoke)

    for prior in ("certificate_controls_pre_d0.json", "benchmark_n11_pre_d0.json"):
        require(load_json(artifact_dir / prior).get("result") == "PASS", f"{prior} trial result")

    mutant = copy.deepcopy(universe_report)
    mutant["records_checked"] = UNIVERSE_RECORDS - 1
    try:
        validate_universe_report(mutant)
    except VerificationError:
        pass
    else:
        raise VerificationError("planted verifier denominator mutant survived")

    run_control(["python", str(artifact_dir / "audit_universe.py"), "--self-test"], root)
    run_control(["python", str(artifact_dir / "cross_validate.py"), "--self-test"], root)
    if not args.skip_runtime:
        run_control(["cargo", "build", "--release"], crate)
        run_control(["cargo", "test", "--release"], crate)
        with tempfile.TemporaryDirectory(prefix="gmp13-verify-") as raw_temporary:
            rerun = Path(raw_temporary) / "final-smoke.json"
            run_control(
                [
                    "python",
                    str(artifact_dir / "final_binary_smoke.py"),
                    "--rust-binary",
                    str(crate / "target/release/max11-colgen-loops"),
                    "--rust-lib",
                    str(crate / "src/lib.rs"),
                    "--rust-main",
                    str(crate / "src/main.rs"),
                    "--universe",
                    str(universe),
                    "--python-dp",
                    str(root / "artifacts/math/span-structure-n5-n10/span_structure.py"),
                    "--cross-module",
                    str(artifact_dir / "cross_validate.py"),
                    "--output",
                    str(rerun),
                    "--records",
                    "8",
                    "--prime",
                    str(PRIME),
                    "--threads",
                    "4",
                ],
                root,
            )
            current = load_json(rerun)
            validate_final_smoke(current)
            for key in ("rust_binary_sha256", "rust_lib_sha256", "rust_main_sha256"):
                require(current.get(key) == committed_smoke.get(key), f"current {key}")

    print(
        "GMP13_VERIFY_PASS "
        "universe=7015841/7015841 certificates=2/2 templates=60/60 "
        "python=2000/2000 loopless=1000/1000 benchmark=1000/1000 "
        "current_binary_python=8/8 verifier_mutant=1/1",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
