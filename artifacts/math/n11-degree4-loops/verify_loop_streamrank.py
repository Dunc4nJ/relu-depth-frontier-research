#!/usr/bin/env python3
"""Verify sou streamrank reports without hard-coding the observed rank/verdict."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
from typing import Sequence


EXPECTED_INPUTS = {
    10: (136_036, "e739d8671b91b51dbdcff8e131ab65e3ffac22972ccd7cbb3489347aaa7b590f"),
    11: (137_504, "e507784414e85667cfe18f68e55b2db22015cf112f05ea110f5ccf388dafb5c0"),
}


class VerificationError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pivot_hash(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<Q", value))
    return digest.hexdigest()


def verify_separator(separator: object, rank: int, buckets: int, prime: int) -> None:
    if not isinstance(separator, dict):
        raise VerificationError("NON_MEMBER sketch lacks a separator")
    if separator.get("encoding") != "sparse-bucket-residues-v1":
        raise VerificationError("separator encoding mismatch")
    if separator.get("length") != buckets:
        raise VerificationError("separator length mismatch")
    if separator.get("verified_basis_columns_denominator") != rank:
        raise VerificationError("separator basis denominator mismatch")
    dot = separator.get("dot_target_mod_prime")
    if not isinstance(dot, int) or not (1 <= dot < prime):
        raise VerificationError("separator does not separate the target")
    entries = separator.get("entries")
    if not isinstance(entries, list) or not entries:
        raise VerificationError("separator sparse vector is empty")
    previous = -1
    for entry in entries:
        bucket = entry.get("bucket")
        residue = entry.get("residue")
        if not isinstance(bucket, int) or not (previous < bucket < buckets):
            raise VerificationError("separator buckets are not strictly ordered")
        if not isinstance(residue, int) or not (1 <= residue < prime):
            raise VerificationError("separator residue is not canonical nonzero")
        previous = bucket


def verify_report(report: dict[str, object], path: Path) -> dict[str, object]:
    if report.get("schema") != "max11-streamrank-pivots-v1":
        raise VerificationError(f"{path}: report schema mismatch")
    if report.get("result") not in ("CONTROL_PASS", "OBSERVATION"):
        raise VerificationError(f"{path}: incomplete or failed run")
    n = int(report.get("n", -1))
    if n not in EXPECTED_INPUTS:
        raise VerificationError(f"{path}: unsupported dimension")
    records, expected_hash = EXPECTED_INPUTS[n]
    if report.get("input_sha256") != expected_hash:
        raise VerificationError(f"{path}: universe hash mismatch")
    if report.get("branch_edge_occurrences") != 4:
        raise VerificationError(f"{path}: branch size mismatch")
    if report.get("loop_inclusive_generation") is not True:
        raise VerificationError(f"{path}: loop generator was not selected")
    if report.get("backend") != "cuda":
        raise VerificationError(f"{path}: final report is not from CUDA")
    if report.get("source_column_count") != records + 1:
        raise VerificationError(f"{path}: source-column denominator mismatch")
    if report.get("source_columns_denominator") != records + 1:
        raise VerificationError(f"{path}: explicit denominator mismatch")
    if report.get("five_l_carrier") is not None:
        raise VerificationError(f"{path}: legacy 5L carrier unexpectedly present")
    carrier = report.get("linear_loop_carrier")
    if not isinstance(carrier, dict):
        raise VerificationError(f"{path}: 4L carrier missing")
    expected_coefficient = 4 * math.factorial(n - 1)
    expected_carrier = {
        "label": "4L",
        "branch_edge_occurrences": 4,
        "source_index": records,
        "exact_linear_coefficient_each_of_n_coordinates": expected_coefficient,
        "coordinate_count": n,
        "hinge_count": 0,
    }
    if carrier != expected_carrier:
        raise VerificationError(f"{path}: 4L carrier descriptor mismatch")
    if not str(report.get("subject", "")).startswith("colgen-loops-universe-"):
        raise VerificationError(f"{path}: subject does not bind colgen-loops")
    prime = int(report.get("modulus", 0))
    if prime not in (1_000_003, 1_000_033):
        raise VerificationError(f"{path}: unregistered modulus")
    buckets = int(report.get("buckets", 0))
    sketches = report.get("sketches")
    if not isinstance(sketches, list) or not sketches:
        raise VerificationError(f"{path}: report has no sketch")
    rows = []
    for sketch in sketches:
        rank = int(sketch["rank_a"])
        augmented = int(sketch["rank_augmented"])
        verdict = sketch["verdict"]
        if sketch.get("saturated") is not False or rank >= buckets:
            raise VerificationError(f"{path}: saturated sketch has no verdict")
        if buckets < 3 * rank:
            raise VerificationError(f"{path}: buckets are less than three times rank")
        expected_augmented = rank + int(verdict == "NON_MEMBER")
        if verdict not in ("MEMBER", "NON_MEMBER") or augmented != expected_augmented:
            raise VerificationError(f"{path}: rank/verdict relation is inconsistent")
        pivots = sketch.get("pivot_columns")
        pivot_buckets = sketch.get("pivot_buckets")
        if not isinstance(pivots, list) or len(pivots) != rank or len(set(pivots)) != rank:
            raise VerificationError(f"{path}: pivot source indices are invalid")
        if not isinstance(pivot_buckets, list) or len(pivot_buckets) != rank:
            raise VerificationError(f"{path}: pivot bucket denominator mismatch")
        if pivot_hash(pivots) != sketch.get("pivot_columns_u64_le_sha256"):
            raise VerificationError(f"{path}: ordered pivot hash mismatch")
        target = sketch.get("target_sketch_nonzero")
        if not isinstance(target, list) or not target:
            raise VerificationError(f"{path}: target sketch is empty")
        if verdict == "NON_MEMBER":
            verify_separator(sketch.get("left_separator"), rank, buckets, prime)
        elif sketch.get("left_separator") is not None:
            raise VerificationError(f"{path}: MEMBER sketch unexpectedly has a separator")
        seed = int(sketch["sketch"]["seed"])
        rows.append({
            "seed": seed,
            "rank_a": rank,
            "rank_augmented": augmented,
            "verdict": verdict,
            "pivot_columns_u64_le_sha256": sketch["pivot_columns_u64_le_sha256"],
        })
    expected = report.get("expected")
    if not isinstance(expected, dict) or expected.get("exact_match") is not True:
        raise VerificationError(f"{path}: registered expectation did not pass")
    if n == 10 and any(row["verdict"] != "MEMBER" for row in rows):
        raise VerificationError(f"{path}: n=10 known-answer control failed")
    return {
        "path": str(path),
        "sha256": sha256_path(path),
        "n": n,
        "prime": prime,
        "buckets": buckets,
        "source_columns": records + 1,
        "wall_seconds": report.get("wall_seconds"),
        "max_rss_kib": report.get("max_rss_kib"),
        "sketches": rows,
    }


def verify_bundle(paths: list[Path]) -> dict[str, object]:
    loaded = [(path, json.loads(path.read_text())) for path in paths]
    rows = [verify_report(report, path) for path, report in loaded]
    grouped: dict[tuple[int, int], list[dict[str, object]]] = {}
    for row in rows:
        grouped.setdefault((int(row["n"]), int(row["prime"])), []).extend(row["sketches"])
    for key, sketches in grouped.items():
        seeds = [int(sketch["seed"]) for sketch in sketches]
        if len(seeds) != len(set(seeds)):
            raise VerificationError(f"duplicate seed in group {key}")
        verdicts = {str(sketch["verdict"]) for sketch in sketches}
        ranks = {(int(sketch["rank_a"]), int(sketch["rank_augmented"])) for sketch in sketches}
        pivot_hashes = {str(sketch["pivot_columns_u64_le_sha256"]) for sketch in sketches}
        if len(verdicts) != 1 or len(ranks) != 1 or len(pivot_hashes) != 1:
            raise VerificationError(f"cross-seed disagreement in group {key}")
        if key[0] == 11 and len(sketches) != 2:
            raise VerificationError(f"n=11 group {key} does not contain two sketches")
    primary = grouped.get((11, 1_000_003), [])
    if len(primary) != 2:
        raise VerificationError("two primary-prime n=11 sketches are required")
    primary_verdict = str(primary[0]["verdict"])
    secondary = grouped.get((11, 1_000_033), [])
    if primary_verdict == "NON_MEMBER" and len(secondary) != 2:
        raise VerificationError("NON_MEMBER requires two second-prime sketches")
    if secondary and {str(row["verdict"]) for row in secondary} != {primary_verdict}:
        raise VerificationError("cross-prime verdict disagreement")
    return {
        "rows": rows,
        "primary_verdict": primary_verdict,
        "primary_sketches_numerator": len(primary),
        "primary_sketches_denominator": 2,
        "secondary_sketches_numerator": len(secondary),
        "secondary_sketches_required_denominator": 2 if primary_verdict == "NON_MEMBER" else 0,
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    bundle = verify_bundle(args.report)
    first = json.loads(args.report[0].read_text())
    mutants_rejected = 0
    rank_mutant = copy.deepcopy(first)
    rank_mutant["sketches"][0]["rank_a"] += 1
    try:
        verify_report(rank_mutant, Path("rank-mutant"))
    except VerificationError:
        mutants_rejected += 1
    verdict_mutant = copy.deepcopy(first)
    verdict_mutant["sketches"][0]["verdict"] = (
        "NON_MEMBER" if verdict_mutant["sketches"][0]["verdict"] == "MEMBER" else "MEMBER"
    )
    try:
        verify_report(verdict_mutant, Path("verdict-mutant"))
    except VerificationError:
        mutants_rejected += 1
    if mutants_rejected != 2:
        raise VerificationError("a planted report mutant survived")
    report = {
        "schema": "max11-sou-loop-streamrank-verification-v1",
        "result": "PASS",
        "command": sys.argv,
        "bundle": bundle,
        "controls": {
            "planted_mutants_rejected_numerator": mutants_rejected,
            "planted_mutants_rejected_denominator": 2,
        },
        "no_claim": (
            "This checks internal report consistency, custody, registered controls, and "
            "cross-sketch agreement. It does not turn modular MEMBER into an exact rational "
            "identity or a bounded NON_MEMBER into an unrestricted depth lower bound."
        ),
    }
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_bytes(canonical_bytes(report))
    print(canonical_bytes({
        "result": "PASS",
        "verdict": bundle["primary_verdict"],
        "output": str(args.output),
        "output_sha256": sha256_path(args.output),
    }).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
