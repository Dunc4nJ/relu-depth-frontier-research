#!/usr/bin/env python3
"""Fail-closed structural verifier for the two KWA streamrank sketches."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import struct


PRIME = 1_000_003
BUCKETS = 64_000
EXPECTED_SEEDS = {2_026_090_201, 2_026_090_202}
UNIVERSE_RECORDS = 18_285
SOURCE_COLUMNS = 18_286
RANK_A = 3_514
RANK_AUGMENTED = 3_515
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
    if not isinstance(carrier, dict):
        raise ValueError("4L carrier descriptor absent")
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
        raise ValueError("each low-headroom report must contain exactly one sketch")
    sketch = sketches[0]
    seed = int(sketch["sketch"]["seed"])
    if seed not in EXPECTED_SEEDS:
        raise ValueError(f"unexpected sketch seed {seed}")
    if int(sketch["rank_a"]) != RANK_A or int(sketch["rank_augmented"]) != RANK_AUGMENTED:
        raise ValueError("rank pair mismatch")
    if sketch.get("verdict") != "NON_MEMBER" or sketch.get("saturated") is not False:
        raise ValueError("verdict/saturation mismatch")
    if int(sketch["source_columns_denominator"]) != SOURCE_COLUMNS:
        raise ValueError("sketch source-column denominator mismatch")
    pivots = [int(value) for value in sketch["pivot_columns"]]
    if len(pivots) != RANK_A or len(set(pivots)) != RANK_A:
        raise ValueError("pivot-column denominator or uniqueness mismatch")
    if sha256_u64_le(pivots) != sketch["pivot_columns_u64_le_sha256"]:
        raise ValueError("pivot-column hash mismatch")
    separator = sketch.get("left_separator")
    if not isinstance(separator, dict):
        raise ValueError("NON_MEMBER report lacks a separator")
    if int(separator["length"]) != BUCKETS:
        raise ValueError("separator length mismatch")
    if int(separator["verified_basis_columns_denominator"]) != RANK_A:
        raise ValueError("separator basis-column denominator mismatch")
    y = {int(item["bucket"]): int(item["residue"]) for item in separator["entries"]}
    target = {
        int(item["bucket"]): int(item["residue"])
        for item in sketch["target_sketch_nonzero"]
    }
    dot = sum(value * target.get(bucket, 0) for bucket, value in y.items()) % PRIME
    if dot == 0 or dot != int(separator["dot_target_mod_prime"]):
        raise ValueError("separator/target dot-product replay mismatch")
    return {
        "seed": seed,
        "rank_a": RANK_A,
        "rank_augmented": RANK_AUGMENTED,
        "verdict": "NON_MEMBER",
        "pivot_columns": len(pivots),
        "separator_nonzero_entries": len(y),
        "separator_dot_target_mod_prime": dot,
    }


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

    hostile = copy.deepcopy(reports[0])
    hostile["sketches"][0]["rank_augmented"] = RANK_A
    try:
        validate_report(hostile, universe_sha256)
    except ValueError:
        rank_mutant_rejected = True
    else:
        raise AssertionError("rank-gain mutation was accepted")

    output = {
        "schema": "max11-kwa-streamrank-verification-v1",
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
        "rank_gain_mutant_rejected": rank_mutant_rejected,
        "verifier_sha256": sha256_path(Path(__file__).resolve()),
        "no_claim": (
            "This verifies report structure, hashes, denominators, pivot hashes, and the stored "
            "bucket-separator/target dot products. It does not independently regenerate columns "
            "or prove characteristic-zero or unrestricted-network nonmembership."
        ),
    }
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"result": "PASS", "output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
