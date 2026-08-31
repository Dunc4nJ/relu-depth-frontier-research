#!/usr/bin/env python3
"""Bind and run the fresh-context literal orbit verifier on one MAX9 certificate."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tempfile
import time


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
HELPER_SOURCE = HERE / "literal_orbit_replay.cpp"


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(payload))
        destination.flush()
        os.fsync(destination.fileno())


def parse_pair(raw: object, n: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[list[tuple[int, int]]] = []
    for raw_side in raw:
        require(isinstance(raw_side, list) and raw_side, "malformed/empty side")
        side: list[tuple[int, int]] = []
        for raw_edge in raw_side:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            require(
                all(isinstance(value, int) and not isinstance(value, bool) for value in raw_edge),
                "noninteger edge endpoint",
            )
            first, second = raw_edge
            require(1 <= first <= second <= n, "edge endpoint/order outside arity")
            side.append((first - 1, second - 1))
        sides.append(side)
    require(len(sides[0]) == len(sides[1]) <= 4, "unequal or excessive branch degree")
    return sides[0], sides[1]


def prepare_input(certificate: dict[str, object], destination) -> dict[str, object]:
    n = certificate.get("n")
    terms = certificate.get("terms")
    require(n == 9 and isinstance(terms, list) and terms, "expected nonempty n=9 certificate")
    parsed: list[tuple[Fraction, tuple[list[tuple[int, int]], list[tuple[int, int]]]]] = []
    denominator = 1
    degrees: Counter[int] = Counter()
    groups: Counter[str] = Counter()
    for index, term in enumerate(terms):
        require(isinstance(term, dict), f"term {index} is not an object")
        raw_coefficient = term.get("coefficient")
        require(isinstance(raw_coefficient, str), f"term {index} coefficient is not a string")
        coefficient = Fraction(raw_coefficient)
        require(str(coefficient) == raw_coefficient, f"term {index} coefficient is noncanonical")
        pair = parse_pair(term.get("pair"), n)
        parsed.append((coefficient, pair))
        denominator = math.lcm(denominator, coefficient.denominator)
        degrees[len(pair[0])] += 1
        group = term.get("group")
        if group is None and isinstance(term.get("provenance"), dict):
            group = term["provenance"].get("kind")
        groups[str(group or "unspecified")] += 1
    require(0 < denominator < 2**63, "common denominator does not fit signed 64-bit input")
    destination.write(f"{n} {len(parsed)} {denominator}\n")
    max_scaled_bits = 0
    for coefficient, (left, right) in parsed:
        scaled = coefficient * denominator
        require(scaled.denominator == 1 and -(2**63) < scaled.numerator < 2**63, "scaled coefficient overflow")
        max_scaled_bits = max(max_scaled_bits, abs(scaled.numerator).bit_length())
        fields = [str(scaled.numerator), str(len(left))]
        for side in (left, right):
            for first, second in side:
                fields.extend((str(first), str(second)))
        destination.write(" ".join(fields) + "\n")
    destination.flush()
    return {
        "terms": len(parsed),
        "common_denominator": str(denominator),
        "common_denominator_bits": denominator.bit_length(),
        "maximum_scaled_coefficient_bits": max_scaled_bits,
        "degree_counts": {str(key): value for key, value in sorted(degrees.items())},
        "group_counts": dict(sorted(groups.items())),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--helper", type=Path, required=True)
    parser.add_argument("--expected-helper-sha256", required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--claim-boundary", required=True)
    args = parser.parse_args()
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    helper_source_hash = sha256(HELPER_SOURCE)
    certificate = args.certificate.resolve()
    helper = args.helper.resolve()
    report_path = args.report.resolve()
    require(certificate.is_file() and helper.is_file(), "certificate/helper missing")
    certificate_hash = sha256(certificate)
    helper_hash = sha256(helper)
    require(helper_hash == args.expected_helper_sha256, "helper binary hash drift")
    document = json.loads(certificate.read_text(encoding="utf-8"))
    require(isinstance(document, dict), "certificate root is not an object")
    with tempfile.NamedTemporaryFile(mode="w+", encoding="utf-8") as stream:
        input_summary = prepare_input(document, stream)
        stream.seek(0)
        process = subprocess.run(
            [str(helper)],
            stdin=stream,
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        )
    require(process.returncode == 0, f"literal helper failed with exit {process.returncode}: {process.stdout}")
    helper_report = json.loads(process.stdout)
    require(
        isinstance(helper_report, dict)
        and helper_report.get("result") == "PASS"
        and helper_report.get("terms") == input_summary["terms"],
        "literal helper report mismatch",
    )
    report = {
        "schema": "g0115-fresh-context-literal-orbit-replay-v1",
        "result": "PASS",
        "bindings": {
            str(certificate.relative_to(ROOT)): certificate_hash,
            str(SCRIPT.relative_to(ROOT)): script_hash,
            str(HELPER_SOURCE.relative_to(ROOT)): helper_source_hash,
            "literal_helper_binary_sha256": helper_hash,
        },
        "input_summary": input_summary,
        "literal_replay": helper_report,
        "method": (
            "For each serialized pair, enumerate every injective assignment of its active labels "
            "to the nine ordered ranks; multiply by the inactive-label factorial, evaluate both "
            "branch forms literally, lexicographically orient their difference, and aggregate the "
            "exact common-denominator linear and active-hinge normal form."
        ),
        "independence_boundary": (
            "This replay imports no G-0115/G-0094 Python module and reads no matrix, cache, solver, "
            "checkpoint, compiler report, asserted semantic field, or CEGIS report. JSON parsing "
            "and rational scaling are performed by this wrapper; the C++ helper independently "
            "executes the literal permutation-orbit definition."
        ),
        "claim_boundary": args.claim_boundary,
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash and sha256(HELPER_SOURCE) == helper_source_hash, "verifier source changed")
    write_exclusive(report_path, report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
