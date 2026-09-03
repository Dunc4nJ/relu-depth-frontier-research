#!/usr/bin/env python3
"""Fail-closed verifier for a sou loop-inclusive degree-four universe."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import sys
from typing import Sequence


ROOT = Path(__file__).resolve().parents[3]
REFERENCE = (
    ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
EXPECTED_REFERENCE_SHA256 = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
EXPECTED_RECORDS = {10: 136_036, 11: 137_504}
RECORD_KEYS = (
    "sequence",
    "signed_mass",
    "active_vertices",
    "negative_edges",
    "positive_edges",
    "abs_components",
    "abs_beta",
)


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


def components(edges: list[tuple[int, int]], active: int) -> int:
    neighbours = [set() for _ in range(active)]
    for left, right in edges:
        if left != right:
            neighbours[left].add(right)
            neighbours[right].add(left)
    unseen = set(range(active))
    count = 0
    while unseen:
        count += 1
        stack = [unseen.pop()]
        while stack:
            vertex = stack.pop()
            reached = neighbours[vertex] & unseen
            unseen.difference_update(reached)
            stack.extend(reached)
    return count


def verify_record(record: dict[str, object], n: int, sequence: int) -> None:
    if set(record) != set(RECORD_KEYS):
        raise VerificationError(f"record {sequence}: unexpected field set")
    if record["sequence"] != sequence:
        raise VerificationError(f"record {sequence}: sequence mismatch")
    mass = int(record["signed_mass"])
    active = int(record["active_vertices"])
    if not (0 <= mass <= 4 and 0 <= active <= n):
        raise VerificationError(f"record {sequence}: mass/support outside bounds")
    negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]
    positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]
    if len(negative) != mass or len(positive) != mass:
        raise VerificationError(f"record {sequence}: unbalanced signing")
    if negative != sorted(negative) or positive != sorted(positive):
        raise VerificationError(f"record {sequence}: edges are not sorted")
    if set(negative) & set(positive):
        raise VerificationError(f"record {sequence}: opposite signs were not cancelled")
    all_edges = negative + positive
    for left, right in all_edges:
        if not (0 <= left <= right < active):
            raise VerificationError(f"record {sequence}: invalid edge endpoint")
    support = {endpoint for edge in all_edges for endpoint in edge}
    if support != set(range(active)):
        raise VerificationError(f"record {sequence}: inactive or missing support")
    observed_components = components(all_edges, active) if active else 0
    if int(record["abs_components"]) != observed_components:
        raise VerificationError(f"record {sequence}: component count mismatch")
    if int(record["abs_beta"]) != 2 * mass - active + observed_components:
        raise VerificationError(f"record {sequence}: cycle-rank mismatch")


def normalized_reference(record: dict[str, object], sequence: int) -> dict[str, object]:
    return {
        "sequence": sequence,
        "signed_mass": record["signed_mass"],
        "active_vertices": record["active_vertices"],
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "abs_components": record["abs_components"],
        "abs_beta": record["abs_beta"],
    }


def self_test() -> dict[str, object]:
    valid = {
        "sequence": 0,
        "signed_mass": 1,
        "active_vertices": 2,
        "negative_edges": [[0, 0]],
        "positive_edges": [[1, 1]],
        "abs_components": 2,
        "abs_beta": 2,
    }
    verify_record(valid, 2, 0)
    rejected = 0
    endpoint_mutant = dict(valid)
    endpoint_mutant["positive_edges"] = [[1, 2]]
    try:
        verify_record(endpoint_mutant, 2, 0)
    except VerificationError:
        rejected += 1
    overlap_mutant = dict(valid)
    overlap_mutant["positive_edges"] = [[0, 0]]
    try:
        verify_record(overlap_mutant, 2, 0)
    except VerificationError:
        rejected += 1
    if rejected != 2:
        raise VerificationError("a planted record mutant survived")
    return {
        "valid_known_answer_passed_numerator": 1,
        "valid_known_answer_passed_denominator": 1,
        "planted_mutants_rejected_numerator": rejected,
        "planted_mutants_rejected_denominator": 2,
    }


def verify_universe(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="ascii") as source:
        universe = json.load(source)
    if universe.get("schema") != "max11-sou-loop-inclusive-signed-degree4-universe-v1":
        raise VerificationError("universe schema mismatch")
    n = int(universe.get("n", -1))
    if n not in EXPECTED_RECORDS:
        raise VerificationError("unsupported universe dimension")
    if universe.get("branch_edge_occurrences") != 4 or universe.get("loopless") is not False:
        raise VerificationError("universe family metadata mismatch")
    if universe.get("record_zero_carrier") != "4E" or universe.get("external_carrier") != "4L":
        raise VerificationError("degree-four carrier convention mismatch")
    records = universe.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_RECORDS[n]:
        raise VerificationError("universe record denominator mismatch")
    mass_counts: Counter[int] = Counter()
    loop_bearing = 0
    for sequence, record in enumerate(records):
        verify_record(record, n, sequence)
        mass_counts[int(record["signed_mass"])] += 1
        loop_bearing += int(any(
            left == right
            for left, right in record["negative_edges"] + record["positive_edges"]
        ))
    if records[0] != {
        "sequence": 0,
        "signed_mass": 0,
        "active_vertices": 0,
        "negative_edges": [],
        "positive_edges": [],
        "abs_components": 0,
        "abs_beta": 0,
    }:
        raise VerificationError("record zero is not the 4E carrier")
    if sha256_path(REFERENCE) != EXPECTED_REFERENCE_SHA256:
        raise VerificationError("pinned G-0038 reference hash mismatch")
    compared = 0
    with gzip.open(REFERENCE, "rt", encoding="ascii") as source:
        header = json.loads(next(source))
        if header.get("loops_allowed") is not True:
            raise VerificationError("reference does not admit loops")
        for raw in source:
            reference = json.loads(raw)
            if int(reference["signed_mass"]) > 4:
                break
            if int(reference["active_vertices"]) > n:
                continue
            if normalized_reference(reference, compared) != records[compared]:
                raise VerificationError(f"reference comparison failed at {compared}")
            compared += 1
    if compared != len(records):
        raise VerificationError("reference comparison denominator mismatch")
    return {
        "n": n,
        "universe": str(path),
        "universe_sha256": sha256_path(path),
        "records_checked_numerator": len(records),
        "records_checked_denominator": len(records),
        "reference_records_compared_numerator": compared,
        "reference_records_compared_denominator": len(records),
        "loop_bearing_records_numerator": loop_bearing,
        "loop_bearing_records_denominator": len(records),
        "mass_counts": {str(key): value for key, value in sorted(mass_counts.items())},
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    controls = self_test()
    rows = [verify_universe(path) for path in args.universe]
    if len({int(row["n"]) for row in rows}) != len(rows):
        raise VerificationError("duplicate universe dimension")
    report = {
        "schema": "max11-sou-loop-inclusive-degree4-verification-v1",
        "result": "PASS",
        "command": sys.argv,
        "reference": str(REFERENCE.relative_to(ROOT)),
        "reference_sha256": sha256_path(REFERENCE),
        "controls": controls,
        "rows": rows,
        "no_claim": (
            "This verifies finite universe records and their equality to a pinned audited prefix. "
            "It does not verify a span membership verdict or an unrestricted depth claim."
        ),
    }
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_bytes(canonical_bytes(report))
    print(canonical_bytes({
        "result": "PASS",
        "rows": len(rows),
        "output": str(args.output),
        "output_sha256": sha256_path(args.output),
    }).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
