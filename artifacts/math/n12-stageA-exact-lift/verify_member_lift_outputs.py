#!/usr/bin/env python3
"""Fail-closed custody verifier for a completed sketch-member exact lift."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def all_rows_verified(document: dict, prefix: str) -> int:
    numerator = int(document[f"{prefix}_numerator"])
    denominator = int(document[f"{prefix}_denominator"])
    require(denominator > 0, f"{prefix} denominator")
    require(numerator == denominator, f"{prefix} not fully verified")
    return denominator


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--expected-n", type=int, required=True)
    parser.add_argument("--expected-universe-sha256", required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    run_dir = args.run_dir

    build_path = run_dir / "member_sketch_build_report.json"
    solver_path = run_dir / "member_big_solver_report.json"
    witness_path = run_dir / "member_exact_witness.json"
    lift_path = run_dir / "member_exact_lift_report.json"
    upstream_path = run_dir / "member_upstream.json"
    translation_path = run_dir / "upstream_translation_report.json"
    build = load(build_path)
    solver = load(solver_path)
    witness = load(witness_path)
    lift = load(lift_path)
    upstream = load(upstream_path)
    translation = load(translation_path)

    require(build["schema"] == "max11-sketch-member-problem-v1", "build schema")
    require(solver["schema"] == "max11-lift-large-big-result-v1", "solver schema")
    require(witness["schema"] == "max11-exactlift-witness-v1", "witness schema")
    require(lift["schema"] == "max11-sketch-member-lift-report-v1", "lift schema")
    for name, document in (("build", build), ("solver", solver), ("lift", lift), ("translation", translation)):
        require(document["verdict"] == "PASS", f"{name} verdict")
    require(witness["n"] == upstream["n"] == args.expected_n, "witness/upstream n")

    universe_sha = args.expected_universe_sha256
    require(build["source_universe_sha256"] == universe_sha, "build universe SHA")
    require(witness["system_sha256"] == universe_sha, "witness universe SHA")
    require(lift["source_universe_sha256"] == universe_sha, "lift universe SHA")
    require(translation["universe_sha256"] == universe_sha, "translation universe SHA")

    require(lift["build_report_sha256"] == sha256(build_path), "build-report SHA")
    require(lift["solver_report_sha256"] == sha256(solver_path), "solver-report SHA")
    require(lift["witness_sha256"] == sha256(witness_path), "witness SHA in lift")
    require(translation["witness_sha256"] == sha256(witness_path), "witness SHA in translation")
    require(translation["output_sha256"] == sha256(upstream_path), "upstream SHA")
    require(witness["problem_custody"]["sha256"] == build["problem_sha256"], "problem SHA witness/build")
    require(solver["input_sha256"] == build["problem_sha256"], "problem SHA solver/build")
    pivot_path = Path(lift["pivot_report"])
    require(pivot_path.is_file(), "pivot report is unavailable")
    pivot_sha = sha256(pivot_path)
    require(lift["pivot_report_sha256"] == pivot_sha, "lift pivot SHA")
    require(witness["pivot_report_sha256"] == pivot_sha, "witness pivot SHA")

    real_rows = all_rows_verified(lift, "real_rows_verified")
    combined_rows = all_rows_verified(lift, "combined_rows_verified")
    exact = witness["exact_verification"]
    require(all_rows_verified(exact, "real_rows") == real_rows, "witness real rows")
    require(all_rows_verified(exact, "combined_rows") == combined_rows, "witness combined rows")
    require(all_rows_verified(exact, "linear_rows") == args.expected_n, "linear rows")
    all_rows_verified(exact, "union_hinge_rows")
    all_rows_verified(exact, "sketch_rows")
    require(all_rows_verified(solver, "exact_rows_verified") == combined_rows, "solver exact rows")
    require(int(solver["mutation_nonzero_rows_numerator"]) > 0, "solver mutation is inert")
    require(int(solver["mutation_rows_checked_denominator"]) == combined_rows, "solver mutation rows")
    require(int(lift["mutation_nonzero_rows_numerator"]) > 0, "lift mutation is inert")
    require(int(lift["mutation_rows_checked_denominator"]) == combined_rows, "lift mutation rows")

    coefficients = witness["coefficients"]
    terms = upstream["terms"]
    support = len(coefficients)
    require(support > 0, "empty recovered support")
    require(len(terms) == support, "upstream term count")
    require([item["coefficient"] for item in coefficients] == [item["coefficient"] for item in terms], "translated coefficients")
    require(int(lift["recovered_support_numerator"]) == support, "lift support numerator")
    require(int(translation["support_terms_numerator"]) == support, "translation support numerator")
    require(int(translation["witness_entries_denominator"]) == support, "translation support denominator")
    rank = int(lift["recovered_support_denominator"])
    require(int(build["pivot_columns_numerator"]) == int(build["pivot_columns_denominator"]) == rank, "build pivot count")
    require(int(lift["pivot_columns_numerator"]) == int(lift["pivot_columns_denominator"]) == rank, "lift pivot count")
    require(int(solver["recovered_support_denominator"]) == rank, "solver support denominator")

    denominator_lcm = int(lift["coefficient_denominator_lcm"])
    require(denominator_lcm > 0, "coefficient denominator LCM")
    require(int(witness["coefficient_denominator_lcm"]) == denominator_lcm, "witness denominator LCM")
    require(int(solver["recovered_denominator_lcm"]) == denominator_lcm, "solver denominator LCM")
    for index, item in enumerate(coefficients):
        coefficient = Fraction(item["coefficient"])
        require(coefficient != 0, f"zero stored coefficient {index}")
        require(denominator_lcm % coefficient.denominator == 0, f"coefficient denominator {index}")
    recomputed_lcm = math.lcm(*(Fraction(item["coefficient"]).denominator for item in coefficients))
    require(recomputed_lcm == denominator_lcm, "recomputed coefficient denominator LCM")

    report = {
        "schema": "exp0037-member-lift-custody-verification-v1",
        "result": "PASS",
        "n": args.expected_n,
        "pivot_columns_numerator": rank,
        "pivot_columns_denominator": rank,
        "recovered_support_numerator": support,
        "recovered_support_denominator": rank,
        "real_rows_verified_numerator": real_rows,
        "real_rows_verified_denominator": real_rows,
        "combined_rows_verified_numerator": combined_rows,
        "combined_rows_verified_denominator": combined_rows,
        "coefficient_denominator_lcm": denominator_lcm,
        "witness_sha256": sha256(witness_path),
        "upstream_sha256": sha256(upstream_path),
        "lift_report_sha256": sha256(lift_path),
        "no_claim": (
            f"This verifies custody and the stored all-row exact-verification receipts for the finite n={args.expected_n} identity; "
            "independent upstream evaluation remains separate."
        ),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output:
        if args.output.exists():
            require(args.output.read_text() == encoded, "stored verification differs")
        else:
            args.output.write_text(encoded)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
