#!/usr/bin/env python3
"""Fail-closed verifier preregistered for the KWA second-prime sketches."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct


PRIME = 1_000_033
BUCKETS = 64_000
EXPECTED_SEEDS = {2_026_090_201, 2_026_090_202}
UNIVERSE_RECORDS = 18_285
SOURCE_COLUMNS = 18_286
FOUR_L_COEFFICIENT = 14_515_200


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def sha256_u64_le(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<Q", value))
    return digest.hexdigest()


def validate_report(report: dict[str, object], universe_sha256: str) -> dict[str, object]:
    if report.get("schema") != "max11-streamrank-pivots-v1":
        raise ValueError("report schema mismatch")
    if report.get("result") != "OBSERVATION":
        raise ValueError("report result mismatch")
    expected_scalars = {
        "n": 11,
        "branch_edge_occurrences": 4,
        "modulus": PRIME,
        "buckets": BUCKETS,
        "rank_panel": 64,
        "threads": 8,
        "backend": "cuda",
        "source_column_count": SOURCE_COLUMNS,
        "source_columns_denominator": SOURCE_COLUMNS,
        "input_sha256": universe_sha256,
    }
    for field, expected in expected_scalars.items():
        if report.get(field) != expected:
            raise ValueError(f"{field} mismatch: {report.get(field)!r} != {expected!r}")
    if report.get("five_l_carrier") is not None:
        raise ValueError("degree-four report unexpectedly contains 5L")
    carrier = report.get("linear_loop_carrier")
    expected_carrier = {
        "label": "4L",
        "branch_edge_occurrences": 4,
        "source_index": UNIVERSE_RECORDS,
        "exact_linear_coefficient_each_of_n_coordinates": FOUR_L_COEFFICIENT,
        "coordinate_count": 11,
        "hinge_count": 0,
    }
    if carrier != expected_carrier:
        raise ValueError(f"4L descriptor mismatch: {carrier!r}")

    sketches = report.get("sketches")
    if not isinstance(sketches, list) or len(sketches) != 1:
        raise ValueError("each gated-memory report must contain exactly one sketch")
    sketch = sketches[0]
    seed = int(sketch["sketch"]["seed"])
    if seed not in EXPECTED_SEEDS:
        raise ValueError(f"unexpected sketch seed {seed}")
    if int(sketch["sketch"]["buckets"]) != BUCKETS:
        raise ValueError("sketch bucket denominator mismatch")

    rank_a = int(sketch["rank_a"])
    rank_augmented = int(sketch["rank_augmented"])
    verdict = str(sketch["verdict"])
    if sketch.get("saturated") is not False:
        raise ValueError("64,000-row sketch unexpectedly saturated")
    if int(sketch["source_columns_denominator"]) != SOURCE_COLUMNS:
        raise ValueError("sketch source-column denominator mismatch")
    if rank_augmented not in {rank_a, rank_a + 1}:
        raise ValueError("augmented rank is not rank(A) or rank(A)+1")
    expected_verdict = "MEMBER" if rank_augmented == rank_a else "NON_MEMBER"
    if verdict != expected_verdict:
        raise ValueError("rank pair and verdict disagree")

    pivots = [int(value) for value in sketch["pivot_columns"]]
    if len(pivots) != rank_a or len(set(pivots)) != rank_a:
        raise ValueError("pivot-column denominator or uniqueness mismatch")
    if sha256_u64_le(pivots) != sketch["pivot_columns_u64_le_sha256"]:
        raise ValueError("pivot-column hash mismatch")

    check: dict[str, object] = {
        "seed": seed,
        "rank_a": rank_a,
        "rank_augmented": rank_augmented,
        "verdict": verdict,
        "pivot_columns": len(pivots),
    }
    separator = sketch.get("left_separator")
    if verdict == "MEMBER":
        if separator is not None:
            raise ValueError("MEMBER report unexpectedly contains a separator")
    else:
        if not isinstance(separator, dict):
            raise ValueError("NON_MEMBER report lacks a separator")
        if int(separator["length"]) != BUCKETS:
            raise ValueError("separator length mismatch")
        if int(separator["verified_basis_columns_denominator"]) != rank_a:
            raise ValueError("separator basis-column denominator mismatch")
        entries = separator["entries"]
        if not isinstance(entries, list):
            raise ValueError("separator entries are not a list")
        y = {int(item["bucket"]): int(item["residue"]) for item in entries}
        target = {
            int(item["bucket"]): int(item["residue"])
            for item in sketch["target_sketch_nonzero"]
        }
        dot = sum(value * target.get(bucket, 0) for bucket, value in y.items()) % PRIME
        if dot == 0 or dot != int(separator["dot_target_mod_prime"]):
            raise ValueError("separator/target dot-product replay mismatch")
        check.update(
            separator_nonzero_entries=len(y),
            separator_dot_target_mod_prime=dot,
            verified_basis_columns_denominator=rank_a,
        )
    return check


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--reports", type=Path, nargs=2, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    universe_sha256 = sha256_path(args.universe)
    reports = [json.loads(path.read_text()) for path in args.reports]
    checks = [validate_report(report, universe_sha256) for report in reports]
    if {item["seed"] for item in checks} != EXPECTED_SEEDS:
        raise ValueError("two distinct registered seeds were not both verified")
    outcomes = {
        (item["rank_a"], item["rank_augmented"], item["verdict"])
        for item in checks
    }
    if len(outcomes) != 1:
        raise ValueError(f"cross-seed rank/verdict disagreement: {outcomes!r}")

    hostile = copy.deepcopy(reports[0])
    hostile_sketch = hostile["sketches"][0]
    hostile_sketch["rank_augmented"] = int(hostile_sketch["rank_a"])
    hostile_sketch["verdict"] = "NON_MEMBER"
    try:
        validate_report(hostile, universe_sha256)
    except ValueError:
        rank_verdict_mutant_rejected = True
    else:
        raise AssertionError("rank/verdict mutation was accepted")

    separator_mutant_rejected: bool | None = None
    if checks[0]["verdict"] == "NON_MEMBER":
        hostile = copy.deepcopy(reports[0])
        hostile["sketches"][0]["left_separator"]["dot_target_mod_prime"] = 0
        try:
            validate_report(hostile, universe_sha256)
        except ValueError:
            separator_mutant_rejected = True
        else:
            raise AssertionError("separator-dot mutation was accepted")

    output = {
        "schema": "max11-kwa-streamrank-second-prime-verification-v1",
        "result": "PASS",
        "universe": str(args.universe),
        "universe_sha256": universe_sha256,
        "report_sha256": {str(path): sha256_path(path) for path in args.reports},
        "prime": PRIME,
        "buckets": BUCKETS,
        "serialized_universe_records": UNIVERSE_RECORDS,
        "source_columns_including_4l": SOURCE_COLUMNS,
        "sketches": checks,
        "cross_seed_rank_and_verdict_agreement": True,
        "rank_verdict_mutant_rejected": rank_verdict_mutant_rejected,
        "separator_mutant_rejected": separator_mutant_rejected,
        "verifier_sha256": sha256_path(Path(__file__).resolve()),
        "no_claim": (
            "This verifies report structure, hashes, denominators, pivot hashes, verdict/rank "
            "consistency, and any stored bucket-separator/target dot products at p=1,000,033. "
            "It does not independently regenerate columns or prove characteristic-zero or "
            "unrestricted-network nonmembership."
        ),
    }
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "PASS", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
