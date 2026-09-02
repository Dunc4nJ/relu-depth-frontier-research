#!/usr/bin/env python3
"""Finalize a SHA-bound exact sketch-minor MEMBER witness.

The Rust builder replays the named CountSketch and writes a problem containing
both the square pivot-bucket minor and every exact real support-union row.  The
Rust solver verifies its reconstructed rational solution on every problem row.
This program checks custody and count invariants, normalizes the coefficients,
and emits the standard finite-system witness consumed by
``universe_to_upstream.py``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any

from flint import fmpz


WITNESS_SCHEMA = "max11-exactlift-witness-v1"
BUILD_SCHEMA = "max11-sketch-member-problem-v1"
SOLVER_SCHEMAS = {
    "max11-lift-large-result-v1": "bounded Dixon/CRT",
    "max11-lift-large-big-result-v1": "arbitrary-precision Dixon",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if not isinstance(document, dict):
        raise ValueError(f"{path} is not a JSON object")
    return document


def require_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise ValueError(f"{label}: {actual!r} != {expected!r}")


def factorization(value: int) -> dict[str, int]:
    if value <= 0:
        raise ValueError("denominator LCM must be positive")
    return {str(prime): int(exponent) for prime, exponent in fmpz(value).factor()}


def write_new(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(payload, stream, indent=2, sort_keys=True)
        stream.write("\n")


def finalize(
    build_report_path: Path,
    solver_report_path: Path,
    pivot_report_path: Path,
    witness_path: Path,
    report_path: Path,
) -> dict[str, Any]:
    build = load(build_report_path)
    solver = load(solver_report_path)
    pivot = load(pivot_report_path)
    require_equal(build.get("schema"), BUILD_SCHEMA, "builder schema")
    require_equal(build.get("verdict"), "PASS", "builder verdict")
    solver_schema = solver.get("schema")
    if solver_schema not in SOLVER_SCHEMAS:
        raise ValueError(f"solver schema: {solver_schema!r} is not accepted")
    require_equal(solver.get("verdict"), "PASS", "solver verdict")
    require_equal(build["pivot_report_sha256"], sha256(pivot_report_path), "pivot SHA-256")

    problem_path = Path(build["problem"])
    problem_sha = sha256(problem_path)
    require_equal(build["problem_sha256"], problem_sha, "builder problem SHA-256")
    require_equal(solver.get("input_sha256"), problem_sha, "solver problem SHA-256")
    require_equal(
        Path(solver["input"]).resolve(),
        problem_path.resolve(),
        "solver problem path",
    )

    source_universe = Path(build["source_universe"])
    require_equal(
        build["source_universe_sha256"],
        sha256(source_universe),
        "source universe SHA-256",
    )
    sketches = pivot.get("sketches")
    if not isinstance(sketches, list) or len(sketches) != 1:
        raise ValueError("expected the one-sketch stage-A pivot report")
    pivot_sketch = sketches[0]
    require_equal(pivot_sketch.get("verdict"), "MEMBER", "pivot verdict")
    require_equal(pivot_sketch.get("rank_a"), pivot_sketch.get("rank_augmented"), "pivot ranks")
    rank = int(pivot_sketch["rank_a"])
    pivots = [int(value) for value in pivot_sketch["pivot_columns"]]
    require_equal(len(pivots), rank, "pivot column count")
    require_equal(build["pivot_columns_numerator"], rank, "builder pivot numerator")
    require_equal(build["pivot_columns_denominator"], rank, "builder pivot denominator")
    require_equal(solver["columns_denominator"], rank, "solver column denominator")
    require_equal(solver["selected_minor_rows_numerator"], rank, "selected minor numerator")
    require_equal(solver["selected_minor_rows_denominator"], rank, "selected minor denominator")

    sketch_rows = int(build["sketch_rows_denominator"])
    real_rows = int(build["real_rows_denominator"])
    combined_rows = int(build["combined_rows_denominator"])
    require_equal(sketch_rows, rank, "sketch row denominator")
    require_equal(combined_rows, sketch_rows + real_rows, "combined row decomposition")
    require_equal(solver["rows_checked_denominator"], combined_rows, "solver row denominator")
    require_equal(solver["exact_rows_verified_numerator"], combined_rows, "verified row numerator")
    require_equal(solver["exact_rows_verified_denominator"], combined_rows, "verified row denominator")
    require_equal(solver["mutation_rows_checked_denominator"], combined_rows, "mutation denominator")
    if int(solver["mutation_nonzero_rows_numerator"]) <= 0:
        raise ValueError("the +1 known-answer mutation did not fail on any exact row")
    require_equal(
        build["exact_batch_records_numerator"],
        build["exact_batch_records_denominator"],
        "exact batch records",
    )
    require_equal(build["exact_batch_records_denominator"], rank, "exact batch denominator")

    pivot_set = set(pivots)
    seen: set[int] = set()
    coefficients: list[dict[str, Any]] = []
    denominator_lcm = 1
    for raw in solver["coefficients"]:
        source_index = int(raw["source_index"])
        if source_index not in pivot_set:
            raise ValueError(f"solver returned non-pivot source index {source_index}")
        if source_index in seen:
            raise ValueError(f"solver repeated source index {source_index}")
        seen.add(source_index)
        numerator = int(raw["numerator"])
        denominator = int(raw["denominator"])
        if denominator <= 0 or math.gcd(numerator, denominator) != 1:
            raise ValueError(f"coefficient {source_index} is not reduced with positive denominator")
        coefficient = Fraction(numerator, denominator)
        if coefficient == 0:
            raise ValueError(f"solver serialized zero coefficient {source_index}")
        denominator_lcm = math.lcm(denominator_lcm, coefficient.denominator)
        coefficients.append({"column": source_index, "coefficient": str(coefficient)})
    require_equal(len(coefficients), solver["recovered_support_numerator"], "support numerator")
    require_equal(solver["recovered_support_denominator"], rank, "support denominator")
    require_equal(int(solver["recovered_denominator_lcm"]), denominator_lcm, "denominator LCM")
    coefficients.sort(key=lambda entry: int(entry["column"]))

    witness = {
        "schema": WITNESS_SCHEMA,
        "n": int(pivot["n"]),
        "method": (
            "exact pivot-bucket CountSketch minor + u32 modular LU + "
            f"{SOLVER_SCHEMAS[solver_schema]} + exact all-real-row verification"
        ),
        "system": str(source_universe),
        "system_sha256": build["source_universe_sha256"],
        "pivot_report": str(pivot_report_path),
        "pivot_report_sha256": build["pivot_report_sha256"],
        "sketch_index": 0,
        "solver_prime": int(solver["prime"]),
        "problem_custody": {
            "path": str(problem_path),
            "schema": build["problem_schema"],
            "bytes": int(build["problem_bytes"]),
            "sha256": problem_sha,
        },
        "exact_verification": {
            "sketch_rows_numerator": sketch_rows,
            "sketch_rows_denominator": sketch_rows,
            "linear_rows_numerator": int(build["linear_rows_denominator"]),
            "linear_rows_denominator": int(build["linear_rows_denominator"]),
            "union_hinge_rows_numerator": int(build["union_hinge_rows_denominator"]),
            "union_hinge_rows_denominator": int(build["union_hinge_rows_denominator"]),
            "real_rows_numerator": real_rows,
            "real_rows_denominator": real_rows,
            "combined_rows_numerator": combined_rows,
            "combined_rows_denominator": combined_rows,
        },
        "coefficient_denominator_lcm": denominator_lcm,
        "coefficient_denominator_factorization": factorization(denominator_lcm),
        "coefficients": coefficients,
        "no_claim": "This proves an exact identity only for the named finite stage-A family; it does not decide MAX11 or the complete loopless family.",
    }
    write_new(witness_path, witness)
    witness_sha = sha256(witness_path)
    report = {
        "schema": "max11-sketch-member-lift-report-v1",
        "verdict": "PASS",
        "pivot_report": str(pivot_report_path),
        "pivot_report_sha256": build["pivot_report_sha256"],
        "build_report": str(build_report_path),
        "build_report_sha256": sha256(build_report_path),
        "solver_report": str(solver_report_path),
        "solver_report_sha256": sha256(solver_report_path),
        "source_universe": str(source_universe),
        "source_universe_sha256": build["source_universe_sha256"],
        "problem": str(problem_path),
        "problem_bytes": int(build["problem_bytes"]),
        "problem_sha256": problem_sha,
        "pivot_columns_numerator": rank,
        "pivot_columns_denominator": rank,
        "recovered_support_numerator": len(coefficients),
        "recovered_support_denominator": rank,
        "coefficient_denominator_lcm": denominator_lcm,
        "coefficient_denominator_factorization": factorization(denominator_lcm),
        "sketch_rows_verified_numerator": sketch_rows,
        "sketch_rows_verified_denominator": sketch_rows,
        "linear_rows_verified_numerator": int(build["linear_rows_denominator"]),
        "linear_rows_verified_denominator": int(build["linear_rows_denominator"]),
        "union_hinge_rows_verified_numerator": int(build["union_hinge_rows_denominator"]),
        "union_hinge_rows_verified_denominator": int(build["union_hinge_rows_denominator"]),
        "real_rows_verified_numerator": real_rows,
        "real_rows_verified_denominator": real_rows,
        "combined_rows_verified_numerator": combined_rows,
        "combined_rows_verified_denominator": combined_rows,
        "mutation_nonzero_rows_numerator": int(solver["mutation_nonzero_rows_numerator"]),
        "mutation_rows_checked_denominator": combined_rows,
        "recovery_method": solver.get(
            "recovery_method", SOLVER_SCHEMAS[solver_schema]
        ),
        "witness": str(witness_path),
        "witness_sha256": witness_sha,
        "no_claim": "This exact stage-A identity does not decide MAX11 or membership in any larger finite family.",
    }
    write_new(report_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-report", required=True, type=Path)
    parser.add_argument("--solver-report", required=True, type=Path)
    parser.add_argument("--pivot-report", required=True, type=Path)
    parser.add_argument("--witness", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    print(
        json.dumps(
            finalize(
                args.build_report,
                args.solver_report,
                args.pivot_report,
                args.witness,
                args.report,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
