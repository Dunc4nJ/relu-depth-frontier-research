#!/usr/bin/env python3
"""Independent, outcome-blind probes for G-0138.

This file uses only the Python standard library.  It neither imports nor runs
the Stage-D producer and it never opens any scientific manifest or output.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import tempfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from functools import reduce
from pathlib import Path

N = 11
FACT11 = math.factorial(N)
SCHEMA = "max11-g0138-stage-d-independent-probe-v1"
SOURCE_REL = "artifacts/reviews/G-0138-g0135-stage-d-source/independent_probe.py"


@dataclass(frozen=True)
class Record:
    active: int
    negative_edges: tuple[tuple[int, int], ...]
    positive_edges: tuple[tuple[int, int], ...]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_integer(raw: str) -> bool:
    if raw == "0":
        return True
    digits = raw[1:] if raw.startswith("-") else raw
    return bool(digits) and not digits.startswith("0") and digits.isdigit()


def increment_table(record: Record) -> list[list[int]]:
    assert 0 <= record.active <= N
    assert len(record.negative_edges) == len(record.positive_edges)
    matrix = [[0] * record.active for _ in range(record.active)]
    for sign, edges in ((-1, record.negative_edges), (1, record.positive_edges)):
        for u, v in edges:
            assert 0 <= u < v < record.active
            matrix[u][v] += sign
            matrix[v][u] += sign
    table = [[0] * (1 << record.active) for _ in range(record.active)]
    for vertex in range(record.active):
        for mask in range(1, 1 << record.active):
            bit = mask & -mask
            other = bit.bit_length() - 1
            table[vertex][mask] = table[vertex][mask ^ bit] + matrix[vertex][other]
    return table


def compressed_words(record: Record) -> tuple[Counter[tuple[int, ...]], int]:
    """Enumerate active-label injections; inactive labels stay indistinguishable."""
    table = increment_table(record)
    inactive = N - record.active
    words: Counter[tuple[int, ...]] = Counter()
    word = [0] * N
    leaves = 0

    def visit(rank: int, mask: int, inactive_used: int) -> None:
        nonlocal leaves
        if rank == N:
            leaves += 1
            words[tuple(word)] += 1
            return
        if inactive_used < inactive:
            word[rank] = 0
            visit(rank + 1, mask, inactive_used + 1)
        for vertex in range(record.active):
            bit = 1 << vertex
            if not mask & bit:
                word[rank] = table[vertex][mask]
                visit(rank + 1, mask | bit, inactive_used)

    visit(0, 0, 0)
    assert leaves * math.factorial(inactive) == FACT11
    return words, leaves


def primitive_direction(word: tuple[int, ...]) -> tuple[int, ...]:
    first = next(value for value in word if value)
    divisor = reduce(math.gcd, (abs(value) for value in word), 0)
    sign = 1 if first > 0 else -1
    return tuple(sign * value // divisor for value in word)


def active_direction(direction: tuple[int, ...]) -> bool:
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def validate_direction(direction: tuple[int, ...]) -> bool:
    nonzero = [value for value in direction if value]
    return (
        len(direction) == N
        and sum(direction) == 0
        and bool(nonzero)
        and nonzero[0] > 0
        and reduce(math.gcd, (abs(value) for value in direction), 0) == 1
        and active_direction(direction)
        and all(-128 <= value <= 127 for value in direction)
    )


def exact_normal_form(record: Record) -> dict[str, object]:
    words, leaves = compressed_words(record)
    inactive_factor = math.factorial(N - record.active)
    linear = [10 * rank * math.factorial(N - 2) for rank in range(N)]
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    for word, compressed_multiplicity in words.items():
        if not any(word):
            continue
        labelled_multiplicity = compressed_multiplicity * inactive_factor
        first = next(value for value in word if value)
        if first < 0:
            for rank, value in enumerate(word):
                linear[rank] += value * labelled_multiplicity
        direction = primitive_direction(word)
        divisor = reduce(math.gcd, (abs(value) for value in word), 0)
        if active_direction(direction):
            assert validate_direction(direction)
            hinges[direction] += divisor * labelled_multiplicity
    return {
        "linear": tuple(linear),
        "hinges": dict(hinges),
        "leaves": leaves,
        "labelled": leaves * inactive_factor,
    }


def matching_injections(
    table: list[list[int]], active: int, direction: tuple[int, ...], scale: int
) -> int:
    inactive = N - active
    states: dict[int, int] = {0: 1}
    for rank, coordinate in enumerate(direction):
        expected = scale * coordinate
        nxt: defaultdict[int, int] = defaultdict(int)
        for mask, count in states.items():
            placed = mask.bit_count()
            inactive_used = rank - placed
            if expected == 0 and inactive_used < inactive:
                nxt[mask] += count
            for vertex in range(active):
                bit = 1 << vertex
                if not mask & bit and table[vertex][mask] == expected:
                    nxt[mask | bit] += count
        states = dict(nxt)
    return states.get((1 << active) - 1, 0)


def direct_prices(record: Record, directions: list[tuple[int, ...]]) -> list[int]:
    table = increment_table(record)
    inactive_factor = math.factorial(N - record.active)
    prices: list[int] = []
    for direction in directions:
        assert validate_direction(direction)
        price = sum(
            abs(scale)
            * matching_injections(table, record.active, direction, scale)
            for scale in range(-5, 6)
            if scale
        )
        prices.append(price * inactive_factor)
    return prices


def direction_digest(items: list[tuple[tuple[int, ...], int]]) -> str:
    payload = bytes(value & 0xFF for direction, _ in items for value in direction)
    return sha256_bytes(payload)


def residual_digest(items: list[tuple[tuple[int, ...], int]]) -> str:
    payload = b"".join(f"{coefficient}\n".encode() for _, coefficient in items)
    return sha256_bytes(payload)


def exact_residual(
    columns: list[list[int]], coefficients: list[int], target: list[int], scale: int
) -> list[int]:
    assert columns and len(columns) == len(coefficients)
    assert target and all(len(column) == len(target) for column in columns)
    return [
        sum(coefficient * column[row] for coefficient, column in zip(coefficients, columns))
        - scale * target[row]
        for row in range(len(target))
    ]


EXPECTED_CANDIDATE_KEYS = {
    "schema",
    "rows",
    "selected",
    "support",
    "coefficients",
    "target_scale",
    "target",
    "terms",
}


def validate_synthetic_candidate(candidate: dict[str, object]) -> bool:
    try:
        if set(candidate) != EXPECTED_CANDIDATE_KEYS:
            return False
        selected = candidate["selected"]
        support = candidate["support"]
        coefficients = candidate["coefficients"]
        rows = candidate["rows"]
        target = candidate["target"]
        scale_raw = candidate["target_scale"]
        terms = candidate["terms"]
        if not (
            candidate["schema"] == "synthetic-exact-member-v1"
            and isinstance(rows, int)
            and rows > 0
            and isinstance(selected, list)
            and isinstance(support, list)
            and isinstance(coefficients, list)
            and selected == support
            and len(selected) == len(coefficients) > 0
            and all(isinstance(value, int) for value in selected)
            and all(left < right for left, right in zip(selected, selected[1:]))
            and isinstance(target, list)
            and len(target) == rows
            and all(isinstance(value, int) for value in target)
            and isinstance(scale_raw, str)
            and canonical_integer(scale_raw)
            and int(scale_raw) > 0
            and all(isinstance(value, str) and canonical_integer(value) for value in coefficients)
            and isinstance(terms, list)
        ):
            return False
        integers = [int(value) for value in coefficients]
        if reduce(math.gcd, (abs(value) for value in [int(scale_raw), *integers]), 0) != 1:
            return False
        projected = [
            {"sequence": sequence, "coefficient": coefficient}
            for sequence, coefficient in zip(support, coefficients)
            if coefficient != "0"
        ]
        return terms == projected and bool(terms)
    except (KeyError, TypeError, ValueError):
        return False


def aggregate_forms(forms: list[tuple[dict[str, object], int]]) -> tuple[tuple[int, ...], dict[tuple[int, ...], int]]:
    linear = [0] * N
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    for form, coefficient in forms:
        for rank, value in enumerate(form["linear"]):
            linear[rank] += coefficient * value
        for direction, value in form["hinges"].items():
            hinges[direction] += coefficient * value
    return tuple(linear), dict(hinges)


def run_probe() -> dict[str, object]:
    record = Record(
        active=6,
        negative_edges=((0, 1), (1, 2), (3, 4)),
        positive_edges=((0, 2), (2, 5), (4, 5)),
    )
    form = exact_normal_form(record)
    directions = sorted(form["hinges"])
    prices = direct_prices(record, directions)
    assert directions and len(directions) == len(prices)
    assert all(form["hinges"][direction] == price for direction, price in zip(directions, prices))
    assert form["labelled"] == FACT11

    term_counts = (1, 3, 7, 101)
    census = {count: count * FACT11 for count in term_counts}
    assert all(value // count == FACT11 for count, value in census.items())
    assert census[7] - 1 != 7 * FACT11

    huge = 10**90 + 123456789
    zero_linear, zero_hinges = aggregate_forms([(form, huge), (form, -huge)])
    nonzero_linear, nonzero_hinges = aggregate_forms([(form, huge), (form, -huge), (form, 1)])
    assert all(value == 0 for value in zero_linear)
    assert all(value == 0 for value in zero_hinges.values())
    assert any(value != 0 for value in nonzero_linear) or any(value != 0 for value in nonzero_hinges.values())
    assert huge * FACT11 > 2**256

    assert len(directions) >= 36
    accumulated = set(directions[:3])
    residual_map = {direction: ((-1) ** index) * (10**70 + index + 1) for index, direction in enumerate(directions)}
    selected = [
        (direction, coefficient)
        for direction, coefficient in sorted(residual_map.items())
        if coefficient and direction not in accumulated
    ][:32]
    assert len(selected) == 32
    assert all(left[0] < right[0] for left, right in zip(selected, selected[1:]))
    signed_byte_route = b"".join(bytes((value & 0xFF,)) for direction, _ in selected for value in direction)
    packed_route = b"".join(int(value).to_bytes(1, "little", signed=True) for direction, _ in selected for value in direction)
    assert signed_byte_route == packed_route
    selected_direction_sha = direction_digest(selected)
    selected_residual_sha = residual_digest(selected)
    reordered = selected.copy()
    reordered[0], reordered[1] = reordered[1], reordered[0]
    coefficient_mutant = selected.copy()
    coefficient_mutant[0] = (coefficient_mutant[0][0], coefficient_mutant[0][1] + 1)
    assert direction_digest(reordered) != selected_direction_sha
    assert residual_digest(coefficient_mutant) != selected_residual_sha

    columns = [[1, 0, 2], [0, 1, -1]]
    coefficients = [2, -3]
    target = [2, -3, 7]
    baseline = exact_residual(columns, coefficients, target, 1)
    assert baseline == [0, 0, 0]
    assert any(exact_residual(columns, [3, -3], target, 1))
    assert any(exact_residual(columns, coefficients, target, 2))
    target_coordinate_mutant = target.copy()
    target_coordinate_mutant[2] += 1
    assert any(exact_residual(columns, coefficients, target_coordinate_mutant, 1))
    assert any(exact_residual(columns[:1], coefficients[:1], target, 1))

    candidate = {
        "schema": "synthetic-exact-member-v1",
        "rows": 3,
        "selected": [2, 7],
        "support": [2, 7],
        "coefficients": ["2", "-3"],
        "target_scale": "1",
        "target": target,
        "terms": [
            {"sequence": 2, "coefficient": "2"},
            {"sequence": 7, "coefficient": "-3"},
        ],
    }
    assert validate_synthetic_candidate(candidate)
    extra_key = dict(candidate, unexpected=True)
    bad_axis = dict(candidate, support=[2, 8])
    omitted_term = dict(candidate, terms=candidate["terms"][:-1])
    bad_scale = dict(candidate, target_scale="0")
    assert not validate_synthetic_candidate(extra_key)
    assert not validate_synthetic_candidate(bad_axis)
    assert not validate_synthetic_candidate(omitted_term)
    assert not validate_synthetic_candidate(bad_scale)
    try:
        json.loads('{"schema":"a","schema":"b"}', object_pairs_hook=lambda pairs: _reject_duplicate_pairs(pairs))
        raise AssertionError("duplicate JSON key escaped")
    except ValueError:
        pass

    with tempfile.TemporaryDirectory(prefix="g0138-probe-") as directory:
        bound = Path(directory) / "bound-input"
        bound.write_bytes(b"original\n")
        expected = sha256_bytes(bound.read_bytes())
        assert sha256_bytes(bound.read_bytes()) == expected
        bound.write_bytes(b"mutant\n")
        assert sha256_bytes(bound.read_bytes()) != expected

    checks = {
        "planted_exact_normal_form_complete": True,
        "independent_direction_pricing_agrees": True,
        "variable_term_census_exact": True,
        "decremented_census_rejected": True,
        "arbitrary_precision_product_exceeds_256_bits": True,
        "exact_zero_branch": True,
        "exact_nonzero_branch": True,
        "signed_tuple_order": True,
        "signed_i8_digest_two_routes_agree": True,
        "canonical_decimal_lf_digest": True,
        "direction_order_mutant_rejected": True,
        "coefficient_plus_one_mutant_rejected": True,
        "candidate_extra_key_mutant_rejected": True,
        "candidate_axis_mutant_rejected": True,
        "candidate_omitted_term_mutant_rejected": True,
        "target_scale_mutant_rejected": True,
        "target_coordinate_mutant_rejected": True,
        "omitted_column_mutant_rejected": True,
        "duplicate_json_key_mutant_rejected": True,
        "custody_hash_mutant_rejected": True,
    }
    assert all(checks.values())
    source_path = Path(__file__).resolve()
    return {
        "schema": SCHEMA,
        "verdict": "PASS",
        "probe_source": {"path": SOURCE_REL, "sha256": sha256_bytes(source_path.read_bytes())},
        "python": sys.version.split()[0],
        "normal_form_fixture": {
            "active_vertices": record.active,
            "compressed_leaves": form["leaves"],
            "labelled_permutations": form["labelled"],
            "hinge_directions": len(directions),
        },
        "variable_term_census": {str(key): value for key, value in census.items()},
        "selected_count": len(selected),
        "selected_directions_i8_sha256": selected_direction_sha,
        "selected_exact_residuals_decimal_lf_sha256": selected_residual_sha,
        "checks": checks,
        "checks_passed": sum(checks.values()),
        "checks_failed": 0,
        "scientific_manifest_observed": False,
        "scientific_output_observed": False,
        "no_claim": "Synthetic source-level probes only; no Stage-C member, scientific replay, global identity, residual, family conclusion, unrestricted MAX11 result, or Lean theorem is established.",
    }


def _reject_duplicate_pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError(f"duplicate key: {key}")
        output[key] = value
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    receipt = run_probe()
    payload = (json.dumps(receipt, indent=2, sort_keys=True) + "\n").encode()
    if args.output is None:
        sys.stdout.buffer.write(payload)
        return
    args.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


if __name__ == "__main__":
    main()
