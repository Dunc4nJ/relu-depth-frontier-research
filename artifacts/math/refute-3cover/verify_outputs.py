#!/usr/bin/env python3
"""Independent known-answer verifier for the GMP.6 certificate audit."""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from math import comb
from pathlib import Path
import sys


EXPECTED = {
    5: ("698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694", 3, 9, 3, 10, 4),
    6: ("026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83", 4, 16, 0, 15, 6),
    7: ("b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be", 57, 226, 116, 21, 9),
    8: ("68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3", 69, 317, 97, 28, 12),
    9: ("4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88", 337, 2696, 0, 36, 16),
    10: ("10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4", 402, 3216, 0, 45, 20),
}
PAPER_TEXT_SHA256 = "05222fe630d1c6248ac90f02d7bcc6fb0f1e6460dde5eda17e3d2a31228aa742"
PAPER_PDF_SHA256 = "22ca802e8b66cb087899cd52ec0089cf456295a28b9c2ac2fa0f22ad39fb64c8"


def load_checker(path: Path):
    spec = importlib.util.spec_from_file_location("gmp6_checker", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate(report: dict[str, object], checker, certificates: Path) -> None:
    if report["schema"] != checker.SCHEMA or report["result"] != "PASS":
        raise AssertionError("schema/result known answer failed")
    if report["certificate_denominator"] != 6:
        raise AssertionError("certificate denominator must be 6")
    records = report["records"]
    if not isinstance(records, list) or [record["n"] for record in records] != list(EXPECTED):
        raise AssertionError("record dimensions must be exactly n=5..10")
    for record in records:
        n = record["n"]
        digest, terms, nonloops, loops, distinct_pairs, minimum = EXPECTED[n]
        expected_path = certificates / Path(record["path"]).name
        if checker.sha256_path(expected_path) != digest or record["sha256"] != digest:
            raise AssertionError(f"n={n}: certificate hash mismatch")
        observed = (
            record["terms"],
            record["nonloop_pair_occurrences_per_unsymmetrized_terms"],
            record["loop_occurrences_per_unsymmetrized_terms"],
            record["distinct_pair_supports_after_symmetrization"],
            record["minimum_pair_3cover_size"],
        )
        if observed != (terms, nonloops, loops, distinct_pairs, minimum):
            raise AssertionError(f"n={n}: count known answer failed: {observed}")
        if record["triples_covered"] != comb(n, 3) or record["triple_denominator"] != comb(n, 3):
            raise AssertionError(f"n={n}: triple coverage mismatch")
        controls = record["controls"]
        if controls["destructive_mutation_missing_triples"] != [[1, 2, 3]]:
            raise AssertionError(f"n={n}: destructive cover control failed")
        if controls["empty_supports_missed_triples"] != comb(n, 3):
            raise AssertionError(f"n={n}: empty-cover null failed")
    n11 = report["n11_pair_3cover"]
    if n11["minimum_pair_3cover_size"] != 25 or n11["triple_denominator"] != 165:
        raise AssertionError("n=11 25/165 known answer failed")


def expect_rejected(report: dict[str, object], checker, certificates: Path) -> None:
    mutant = copy.deepcopy(report)
    mutant["records"][0]["triples_covered"] -= 1
    try:
        validate(mutant, checker, certificates)
    except AssertionError:
        return
    raise AssertionError("altered coverage count was accepted")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--audit", type=Path, required=True)
    parser.add_argument("--checker", type=Path, required=True)
    parser.add_argument("--certificates", type=Path, required=True)
    parser.add_argument("--paper-text", type=Path, required=True)
    parser.add_argument("--paper-pdf", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    checker = load_checker(args.checker)
    report = json.loads(args.audit.read_text())
    validate(report, checker, args.certificates)

    recomputed = checker.run(args.certificates)
    for value in (report, recomputed):
        value.pop("wall_seconds", None)
        value["certificate_directory"] = str(args.certificates)
        for record in value["records"]:
            record["path"] = str(args.certificates / Path(record["path"]).name)
    if recomputed != report:
        raise AssertionError("fresh audit recomputation differs from saved audit")
    if checker.sha256_path(args.paper_text) != PAPER_TEXT_SHA256:
        raise AssertionError("Safran paper text hash differs from reviewed input")
    if checker.sha256_path(args.paper_pdf) != PAPER_PDF_SHA256:
        raise AssertionError("Safran paper PDF hash differs from reviewed input")
    expect_rejected(report, checker, args.certificates)
    print(
        "GMP6_VERIFY_PASS certificates=6/6 covers=6/6 "
        "destructive_mutations=7/7 empty_nulls=6/6 paper_hashes=2/2"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
