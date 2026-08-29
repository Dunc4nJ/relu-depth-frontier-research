#!/usr/bin/env python3
"""Exact support-filtration proof for the frozen G-0053 hinge dual.

For an ``a``-active local hinge direction ``d``, the induced dual coefficient is

    y_a(d) = sum_{P subset [11], |P|=a} y(embed_P(d)).

This script computes that functional in reverse from the 64 nonzero entries of
the G-0053 dual.  An empty induced map is therefore an exact identity on every
local hinge column, not a sample of mass-4 orbit atoms.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import io
from itertools import combinations
import json
from math import gcd
from pathlib import Path
import platform
import sys
from typing import Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0053_SCRIPT = ROOT / "artifacts/math/G-0053/mass3_dual_extension.py"
G0053_REPORT = ROOT / "artifacts/math/G-0053/mass3_dual_extension_v1.json.gz"
EXPECTED_G0053_SCRIPT_HASH = "dac2425f18c96712e2718a5bb6706ddd04e44c8d854307befa50954b48148b9b"
EXPECTED_G0053_REPORT_HASH = "b998c750b676593c65b44adaff9fd0f72788fbe95a65aafa7499d802cda37d0d"
DEFAULT_OUTPUT = HERE / "dual_support_filtration_v1.json.gz"
SCHEMA = "max11-g0055-dual-support-filtration-v1"
N = 11

Direction = tuple[int, ...]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def nonzero_support(direction: Direction) -> tuple[int, ...]:
    return tuple(index for index, value in enumerate(direction) if value)


def local_restriction(direction: Direction, positions: tuple[int, ...]) -> Direction:
    return tuple(direction[index] for index in positions)


def embedding(direction: Direction, positions: tuple[int, ...]) -> Direction:
    result = [0] * N
    for local_index, global_index in enumerate(positions):
        result[global_index] = direction[local_index]
    return tuple(result)


def containing_position_sets(support: tuple[int, ...], active: int) -> Iterable[tuple[int, ...]]:
    complement = tuple(index for index in range(N) if index not in support)
    for extras in combinations(complement, active - len(support)):
        yield tuple(sorted(support + extras))


def induced_reverse(y: dict[Direction, int], active: int) -> dict[Direction, int]:
    result: Counter[Direction] = Counter()
    for direction, coefficient in y.items():
        support = nonzero_support(direction)
        if len(support) > active:
            continue
        for positions in containing_position_sets(support, active):
            result[local_restriction(direction, positions)] += coefficient
    return {direction: value for direction, value in sorted(result.items()) if value}


def induced_forward(
    y: dict[Direction, int], active: int, candidates: Iterable[Direction]
) -> dict[Direction, int]:
    result: dict[Direction, int] = {}
    position_sets = tuple(combinations(range(N), active))
    for direction in sorted(set(candidates)):
        coefficient = sum(y.get(embedding(direction, positions), 0) for positions in position_sets)
        if coefficient:
            result[direction] = coefficient
    return result


def candidates_from_reverse_support(y: dict[Direction, int], active: int) -> set[Direction]:
    candidates: set[Direction] = set()
    for direction in y:
        support = nonzero_support(direction)
        if len(support) <= active:
            for positions in containing_position_sets(support, active):
                candidates.add(local_restriction(direction, positions))
    return candidates


def entries_payload(induced: dict[Direction, int]) -> list[dict[str, object]]:
    return [
        {"direction": list(direction), "numerator": coefficient}
        for direction, coefficient in sorted(induced.items())
    ]


def map_summary(induced: dict[Direction, int], candidate_count: int) -> dict[str, object]:
    entries = entries_payload(induced)
    common_divisor = 0
    for value in induced.values():
        common_divisor = gcd(common_divisor, abs(value))
    return {
        "reverse_candidate_direction_count": candidate_count,
        "nonzero_direction_count": len(induced),
        "l1_numerator": sum(abs(value) for value in induced.values()),
        "gcd_nonzero_numerators": common_divisor,
        "entries": entries,
        "entries_sha256": canonical_sha256(entries),
    }


def run() -> dict[str, object]:
    script_hash_before = sha256_path(Path(__file__))
    if sha256_path(G0053_SCRIPT) != EXPECTED_G0053_SCRIPT_HASH:
        raise ValueError("G-0053 script drift")
    if sha256_path(G0053_REPORT) != EXPECTED_G0053_REPORT_HASH:
        raise ValueError("G-0053 report drift")
    source = load_json_gz(G0053_REPORT)
    dual = source["exact_mass3_dual"]
    denominator = int(dual["common_denominator"])
    sparse_entries = dual["sparse_entries"]
    y: dict[Direction, int] = {}
    for entry in sparse_entries:
        if int(entry["denominator"]) != denominator:
            raise AssertionError("nonuniform frozen dual denominator")
        direction = tuple(map(int, entry["direction"]))
        numerator = int(entry["numerator"])
        if not numerator or direction in y:
            raise AssertionError("invalid sparse dual entry")
        y[direction] = numerator
    if len(y) != 64:
        raise AssertionError(f"sparse dual support drift: {len(y)}")

    support_histogram = Counter(len(nonzero_support(direction)) for direction in y)
    if support_histogram != Counter({5: 16, 6: 48}):
        raise AssertionError(f"dual support-size drift: {support_histogram}")

    by_active: dict[str, object] = {}
    forward_checks = []
    for active in range(2, N):
        candidates = candidates_from_reverse_support(y, active)
        reverse = induced_reverse(y, active)
        forward = induced_forward(y, active, candidates)
        if reverse != forward:
            raise AssertionError(f"forward/reverse induced-map mismatch at active={active}")
        by_active[str(active)] = map_summary(reverse, len(candidates))
        forward_checks.append(
            {
                "active_vertices": active,
                "candidate_direction_count": len(candidates),
                "agreement": True,
            }
        )

    if any(by_active[str(active)]["nonzero_direction_count"] for active in range(2, 7)):
        raise AssertionError("claimed active<=6 filtration identity failed")
    expected_nonzero_counts = {7: 7, 8: 24, 9: 57, 10: 76}
    observed_nonzero_counts = {
        active: by_active[str(active)]["nonzero_direction_count"] for active in range(7, 11)
    }
    if observed_nonzero_counts != expected_nonzero_counts:
        raise AssertionError(f"high-active induced-map drift: {observed_nonzero_counts}")

    # A one-unit mutation of the first frozen coefficient must destroy at least
    # one of the low-active zero maps.  This guards against an always-empty
    # implementation or a accidentally skipped support class.
    mutant = dict(y)
    first_direction = sorted(mutant)[0]
    mutant[first_direction] += 1
    mutant_counts = {
        str(active): len(induced_reverse(mutant, active)) for active in range(2, 7)
    }
    if not any(mutant_counts.values()):
        raise AssertionError("coefficient mutant was not detected")

    result: dict[str, object] = {
        "schema": SCHEMA,
        "bindings": {
            "g0053_script": str(G0053_SCRIPT.relative_to(ROOT)),
            "g0053_script_sha256": EXPECTED_G0053_SCRIPT_HASH,
            "g0053_report": str(G0053_REPORT.relative_to(ROOT)),
            "g0053_report_sha256": EXPECTED_G0053_REPORT_HASH,
            "g0053_sparse_entries_sha256": dual["sparse_entries_sha256"],
        },
        "frozen_dual": {
            "ambient_dimension": N,
            "common_denominator": denominator,
            "nonzero_direction_count": len(y),
            "support_size_histogram": {
                str(key): value for key, value in sorted(support_histogram.items())
            },
        },
        "induced_dual_by_active_support": by_active,
        "controls": {
            "forward_reverse_agreement": forward_checks,
            "single_coefficient_mutant_low_active_nonzero_counts": mutant_counts,
            "single_coefficient_mutant_detected": True,
        },
        "result": {
            "active_at_most_6_induced_dual_is_identically_zero": True,
            "first_active_support_with_nonzero_induced_dual": 7,
            "proof_scope": (
                "Every full-symmetrized local hinge column supported on at most six "
                "active coordinates pairs to zero with this particular frozen G-0053 dual."
            ),
        },
        "claim_boundary": [
            "This is an exact identity of the particular G-0053 dual functional, not a rank or span theorem.",
            "Zero price does not make an atom irrelevant for cancelling other hinge coordinates.",
            "The identity applies to all local hinge maps, hence in particular to every proper signed-mass-4 atom with active support at most six.",
        ],
        "environment": {"python": sys.version, "platform": platform.platform()},
        "script_sha256": script_hash_before,
    }
    payload = dict(result)
    payload.pop("environment")
    payload.pop("script_sha256")
    result["canonical_payload_sha256"] = canonical_sha256(payload)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise RuntimeError("script changed during execution")
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = run()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as raw_target:
        with gzip.GzipFile(fileobj=raw_target, mode="wb", filename="", mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8") as target:
                json.dump(result, target, sort_keys=True, separators=(",", ":"))
                target.write("\n")
    print(json.dumps({"output": str(args.output), "result": result["result"]}, sort_keys=True))


if __name__ == "__main__":
    main()
