#!/usr/bin/env python3
"""Clean-room audit of the corrected MAX11 signed-mass-four preflight.

This verifier deliberately imports none of the G-0047, G-0051, or G-0052
producer code.  It reconstructs the complete degree-four row universe from
signed supports, scans the frozen orbit stream directly, and recomputes every
full-core mass-four hinge column with an independently written base-five
subset-state dynamic program.

The resulting report is an audit of finite geometry and resource arithmetic.
It computes no quotient rank and proves no MAX11 construction or obstruction.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations, permutations
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Iterable, Iterator, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
EXACT_Q = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"
PREFLIGHT_README = ROOT / "artifacts/math/G-0051/README.md"
PREFLIGHT_SCRIPT = ROOT / "artifacts/math/G-0051/preflight_resource_estimator.py"
PREFLIGHT_REPORT = ROOT / "artifacts/math/G-0051/preflight_benchmark_v1.json"
CENSUS_SCRIPT = ROOT / "artifacts/math/G-0052/mass4_full_core_census.py"
CENSUS_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
DEFAULT_OUTPUT = HERE / "audit_report_v1.json"

EXPECTED_HASHES = {
    "stream": "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    "exact_q": "64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b",
    "preflight_readme": "b933fb3b940c3ec02ab56167d0950679787e9c9ebfe7981b7eb3ad4f71ec5619",
    "preflight_script": "c08cdc0520970995bf47ab64483f33845c9468d8fd9a1e1b01be2060c02baa1b",
    "preflight_report": "89faea4146e589c33548130bcb466696c873d7aaab7e0d602e602363f06c34e6",
    "census_script": "435832fb62ca75981a11f3193f4546c0ca817ad7752a0636bbaeb8730cc23d51",
    "census_report": "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37",
}

N = 11
EXPECTED_DEGREE3_ROWS = 10_065
EXPECTED_DEGREE4_ROWS = 99_858
EXPECTED_DEGREE4_HASH = "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
EXPECTED_DEGREE3_HASH = "9141a8ad6ada52b06e71830277e53fe81736878bbede8f7208b3e79a42f46fbe"
EXPECTED_FULL = 1_465
EXPECTED_S0_NNZ = 12_331_131
EXPECTED_S0_UNION = 42_457
EXPECTED_MASS4_BY_ACTIVE = {
    2: 7,
    3: 259,
    4: 3_131,
    5: 14_491,
    6: 31_452,
    7: 37_350,
    8: 27_412,
    9: 13_617,
    10: 5_009,
    11: 1_465,
}
SCHEMA = "max11-cleanroom-g0051-mass4-preflight-audit-v1"

Direction = tuple[int, ...]
Edge = tuple[int, int]
State = tuple[int, int]


class AuditError(RuntimeError):
    """Fail-closed audit mismatch."""


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


def load_json(path: Path) -> dict[str, object]:
    with path.open("r", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {path}")
    return value


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AuditError(f"expected gzip JSON object: {path}")
    return value


def verify_embedded_payload_hash(document: dict[str, object], label: str) -> None:
    copy = dict(document)
    claimed = copy.pop("canonical_payload_sha256", None)
    observed = canonical_sha256(copy)
    if claimed != observed:
        raise AuditError(f"{label} canonical payload drift: {claimed} != {observed}")


def positive_compositions(total: int, parts: int, prefix: Direction = ()) -> Iterator[Direction]:
    """Positive ordered compositions, independently of weak-composition pairs."""
    if parts == 1:
        yield prefix + (total,)
        return
    for first in range(1, total - parts + 2):
        yield from positive_compositions(total - first, parts - 1, prefix + (first,))


def primitive_ambiguous_directions(max_mass: int, n: int) -> tuple[Direction, ...]:
    """Enumerate primitive zero-sum directions by disjoint signed supports.

    A difference of two degree-m branch vectors has equal positive and negative
    mass at most m.  Removing common support and dividing by the gcd gives a
    unique primitive signed-support description.  Fixed-length lex orientation
    means that the first nonzero coordinate is positive.  Such a direction is
    a genuine ordered-cone hinge exactly when at least one proper prefix is
    negative; otherwise its sign is fixed on x_1 <= ... <= x_n.
    """
    directions: set[Direction] = set()
    vertices = tuple(range(n))
    for mass in range(1, max_mass + 1):
        for positive_size in range(1, mass + 1):
            for negative_size in range(1, mass + 1):
                for positive_support in combinations(vertices, positive_size):
                    remaining = tuple(v for v in vertices if v not in positive_support)
                    for negative_support in combinations(remaining, negative_size):
                        if min(positive_support + negative_support) not in positive_support:
                            continue
                        for positive_values in positive_compositions(mass, positive_size):
                            for negative_values in positive_compositions(mass, negative_size):
                                direction = [0] * n
                                for vertex, value in zip(positive_support, positive_values, strict=True):
                                    direction[vertex] = value
                                for vertex, value in zip(negative_support, negative_values, strict=True):
                                    direction[vertex] = -value
                                divisor = 0
                                for value in direction:
                                    divisor = gcd(divisor, abs(value))
                                if divisor != 1:
                                    continue
                                prefix = 0
                                ambiguous = False
                                for value in direction[:-1]:
                                    prefix += value
                                    if prefix < 0:
                                        ambiguous = True
                                if ambiguous:
                                    directions.add(tuple(direction))
    return tuple(sorted(directions))


def edge_data(edges: Sequence[Sequence[int]], n: int) -> tuple[list[int], list[list[int]]]:
    loops = [0] * n
    adjacency = [[0] * n for _ in range(n)]
    for raw in edges:
        if len(raw) != 2:
            raise AuditError(f"malformed edge: {raw}")
        u, v = map(int, raw)
        if not (0 <= u <= v < n):
            raise AuditError(f"edge outside 0..{n - 1}: {raw}")
        if u == v:
            loops[u] += 1
        else:
            adjacency[u][v] += 1
            adjacency[v][u] += 1
    return loops, adjacency


def increment_table(edges: Sequence[Sequence[int]], n: int) -> list[list[int]]:
    loops, adjacency = edge_data(edges, n)
    width = 1 << n
    table = [[0] * width for _ in range(n)]
    for vertex in range(n):
        table[vertex][0] = loops[vertex]
        for mask in range(1, width):
            least = mask & -mask
            other = least.bit_length() - 1
            table[vertex][mask] = table[vertex][mask ^ least] + adjacency[vertex][other]
    return table


def decode_word(code: int, n: int, radix: int) -> Direction:
    values = [0] * n
    for index in range(n - 1, -1, -1):
        values[index] = code % radix
        code //= radix
    if code:
        raise AuditError("branch-word decode overflow")
    return tuple(values)


def normal_form_from_pairs(pair_counter: Counter[State], n: int, radix: int) -> Counter[Direction]:
    hinges: Counter[Direction] = Counter()
    for (left_code, right_code), multiplicity in pair_counter.items():
        if multiplicity <= 0:
            raise AuditError("nonpositive permutation multiplicity")
        if left_code > right_code:
            left_code, right_code = right_code, left_code
        if left_code == right_code:
            continue
        left = decode_word(left_code, n, radix)
        right = decode_word(right_code, n, radix)
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        if sum(direction):
            raise AuditError("unequal branch degree escaped input validation")
        prefix = 0
        sign_fixed = True
        for value in direction[:-1]:
            prefix += value
            if prefix < 0:
                sign_fixed = False
        if sign_fixed:
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        if divisor == 0:
            raise AuditError("zero direction escaped equal-word case")
        primitive = tuple(value // divisor for value in direction)
        hinges[primitive] += multiplicity * divisor
    return hinges


def independent_hinge_column(record: dict[str, object], n: int = N) -> Counter[Direction]:
    branches = (record.get("negative_edges"), record.get("positive_edges"))
    if not all(isinstance(branch, list) for branch in branches):
        raise AuditError("orbit record is missing branch edge lists")
    left_edges = branches[0]
    right_edges = branches[1]
    assert isinstance(left_edges, list) and isinstance(right_edges, list)
    if len(left_edges) != len(right_edges):
        raise AuditError("branch degree mismatch")
    degree = len(left_edges)
    radix = degree + 1
    tables = (increment_table(left_edges, n), increment_table(right_edges, n))

    # State keys are base-(degree+1) encodings of the two complete branch
    # coefficient words.  Branch orientation remains ordered throughout the
    # DP and is canonicalized only after all labels have been placed.
    layer: dict[int, Counter[State]] = {0: Counter({(0, 0): 1})}
    full_mask = (1 << n) - 1
    for _rank in range(n):
        following: dict[int, Counter[State]] = {}
        for mask, states in layer.items():
            remaining = full_mask ^ mask
            while remaining:
                bit = remaining & -remaining
                vertex = bit.bit_length() - 1
                remaining ^= bit
                target = following.setdefault(mask | bit, Counter())
                left_increment = tables[0][vertex][mask]
                right_increment = tables[1][vertex][mask]
                for (left_code, right_code), multiplicity in states.items():
                    target[
                        (
                            left_code * radix + left_increment,
                            right_code * radix + right_increment,
                        )
                    ] += multiplicity
        layer = following
    final = layer.get(full_mask)
    if final is None or sum(final.values()) != factorial(n):
        raise AuditError("subset-state DP did not enumerate n! label orders")

    unordered: Counter[State] = Counter()
    for (left_code, right_code), multiplicity in final.items():
        unordered[(min(left_code, right_code), max(left_code, right_code))] += multiplicity
    return normal_form_from_pairs(unordered, n, radix)


def brute_force_hinge_column(record: dict[str, object], n: int) -> Counter[Direction]:
    branches = (record["negative_edges"], record["positive_edges"])
    assert isinstance(branches[0], list) and isinstance(branches[1], list)
    degree = len(branches[0])
    if len(branches[1]) != degree:
        raise AuditError("small brute-force control has unequal branch degree")
    radix = degree + 1
    pairs: Counter[State] = Counter()
    for order in permutations(range(n)):
        position = [0] * n
        for rank, vertex in enumerate(order):
            position[vertex] = rank
        words = []
        for branch in branches:
            word = [0] * n
            for u, v in branch:
                word[max(position[int(u)], position[int(v)])] += 1
            code = 0
            for value in word:
                code = code * radix + value
            words.append(code)
        pairs[(min(words), max(words))] += 1
    return normal_form_from_pairs(pairs, n, radix)


def hinge_payload(hinges: Counter[Direction]) -> list[list[object]]:
    return [[list(direction), int(weight)] for direction, weight in sorted(hinges.items()) if weight]


def worker(record: dict[str, object]) -> dict[str, object]:
    hinges = independent_hinge_column(record)
    payload = hinge_payload(hinges)
    return {
        "sequence": int(record["sequence"]),
        "hinges": tuple((tuple(row[0]), int(row[1])) for row in payload),
        "support_size": len(payload),
        "total_absolute_weight": sum(abs(int(row[1])) for row in payload),
        "fingerprint_sha256": canonical_sha256(payload),
    }


def descriptor(record: dict[str, object]) -> dict[str, object]:
    return {
        "sequence": int(record["sequence"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "abs_components": int(record["abs_components"]),
    }


def scan_stream() -> tuple[dict[str, object], list[dict[str, object]], Counter[tuple[int, int]]]:
    counts: Counter[tuple[int, int]] = Counter()
    full: list[dict[str, object]] = []
    with gzip.open(STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise AuditError("orbit stream has no header")
        for line in source:
            record = json.loads(line)
            mass = int(record["signed_mass"])
            if mass > 4:
                break
            active = int(record["active_vertices"])
            counts[mass, active] += 1
            if mass == 4 and active == N:
                if len(record["negative_edges"]) != 4 or len(record["positive_edges"]) != 4:
                    raise AuditError("full mass-four record has wrong branch degree")
                full.append(record)
    sequences = [int(record["sequence"]) for record in full]
    if sequences != list(range(136_039, 137_504)):
        raise AuditError("full mass-four sequence interval drift")
    return header, full, counts


def rank_mod(rows: Sequence[Sequence[int]], prime: int) -> int:
    matrix = [[int(value) % prime for value in row] for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    if any(len(row) != width for row in matrix):
        raise AuditError("ragged matrix in rank control")
    pivot_row = 0
    for column in range(width):
        pivot = next((row for row in range(pivot_row, len(matrix)) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        inverse = pow(matrix[pivot_row][column], -1, prime)
        matrix[pivot_row] = [(value * inverse) % prime for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                (left - factor * right) % prime
                for left, right in zip(matrix[row], matrix[pivot_row], strict=True)
            ]
        pivot_row += 1
        if pivot_row == len(matrix):
            break
    return pivot_row


def rank_q(rows: Sequence[Sequence[int]]) -> int:
    matrix = [[Fraction(value) for value in row] for row in rows]
    if not matrix:
        return 0
    width = len(matrix[0])
    pivot_row = 0
    for column in range(width):
        pivot = next((row for row in range(pivot_row, len(matrix)) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[pivot_row], matrix[pivot] = matrix[pivot], matrix[pivot_row]
        divisor = matrix[pivot_row][column]
        matrix[pivot_row] = [value / divisor for value in matrix[pivot_row]]
        for row in range(len(matrix)):
            if row == pivot_row or not matrix[row][column]:
                continue
            factor = matrix[row][column]
            matrix[row] = [
                left - factor * right
                for left, right in zip(matrix[row], matrix[pivot_row], strict=True)
            ]
        pivot_row += 1
    return pivot_row


def self_test() -> dict[str, object]:
    small = {
        "negative_edges": [[0, 0], [0, 1]],
        "positive_edges": [[2, 2], [1, 3]],
    }
    dp = independent_hinge_column(small, n=4)
    brute = brute_force_hinge_column(small, n=4)
    if dp != brute:
        raise AuditError("loop-sensitive DP differs from direct 4! enumeration")

    prime = 5
    full = [[1, 0], [0, 1]]
    if rank_mod(full, prime) != 2 or rank_mod(full + [[1, 1]], prime) != 2:
        raise AuditError("full-column-rank negative control failed")
    hinge = [[1, 1]]
    if rank_mod(hinge, prime) != 1 or rank_mod(hinge + [[1, 0]], prime) != 2:
        raise AuditError("rank-gain positive control failed")
    if (1 + (-1)) % prime or (1 * 1 + 0 * -1) % prime == 0:
        raise AuditError("explicit planted nonzero-lambda kernel control failed")

    # These two examples ensure the report cannot promote modular agreement to
    # a rational conclusion in either direction.
    modular_false_positive_h = [[prime, 0], [0, 1]]
    modular_false_positive_lambda = [1, 0]
    if rank_q(modular_false_positive_h + [modular_false_positive_lambda]) != rank_q(
        modular_false_positive_h
    ):
        raise AuditError("rational false-positive control was specified incorrectly")
    if rank_mod(modular_false_positive_h + [modular_false_positive_lambda], prime) != rank_mod(
        modular_false_positive_h, prime
    ) + 1:
        raise AuditError("modular false-positive control did not fire")

    modular_false_negative_h = [[prime, 0]]
    modular_false_negative_lambda = [0, prime]
    if rank_q(modular_false_negative_h + [modular_false_negative_lambda]) != rank_q(
        modular_false_negative_h
    ) + 1:
        raise AuditError("rational false-negative control was specified incorrectly")
    if rank_mod(modular_false_negative_h + [modular_false_negative_lambda], prime) != rank_mod(
        modular_false_negative_h, prime
    ):
        raise AuditError("modular false-negative control did not fire")
    return {
        "loop_sensitive_subset_state_DP_matches_direct_4_factorial_enumeration": True,
        "planted_full_column_rank_negative": True,
        "planted_nonzero_lambda_kernel_positive": True,
        "modular_gain_without_rational_gain_detected": True,
        "modular_no_gain_despite_rational_gain_detected": True,
    }


def bytes_record(rows: int, columns: int) -> dict[str, object]:
    return {
        "shape": [rows, columns],
        "int64_bytes": rows * columns * 8,
        "one_prime_uint32_bytes": rows * columns * 4,
    }


def audit(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()

    paths = {
        "stream": STREAM,
        "exact_q": EXACT_Q,
        "preflight_readme": PREFLIGHT_README,
        "preflight_script": PREFLIGHT_SCRIPT,
        "preflight_report": PREFLIGHT_REPORT,
        "census_script": CENSUS_SCRIPT,
        "census_report": CENSUS_REPORT,
    }
    observed_hashes = {label: sha256_path(path) for label, path in paths.items()}
    if observed_hashes != EXPECTED_HASHES:
        raise AuditError(f"input binding drift: {observed_hashes}")

    preflight = load_json(PREFLIGHT_REPORT)
    census = load_json_gz(CENSUS_REPORT)
    exact_q = load_json_gz(EXACT_Q)
    verify_embedded_payload_hash(preflight, "G-0051")
    verify_embedded_payload_hash(census, "G-0052")

    degree3 = primitive_ambiguous_directions(3, N)
    degree4 = primitive_ambiguous_directions(4, N)
    degree3_payload = [list(direction) for direction in degree3]
    degree4_payload = [list(direction) for direction in degree4]
    if len(degree3) != EXPECTED_DEGREE3_ROWS or canonical_sha256(degree3_payload) != EXPECTED_DEGREE3_HASH:
        raise AuditError("independent degree-three universe mismatch")
    if len(degree4) != EXPECTED_DEGREE4_ROWS or canonical_sha256(degree4_payload) != EXPECTED_DEGREE4_HASH:
        raise AuditError("independent degree-four universe mismatch")
    if not set(degree3) < set(degree4):
        raise AuditError("degree-three universe is not a strict subset of degree four")
    support_histogram = Counter(sum(value != 0 for value in direction) for direction in degree4)
    expected_support_histogram = Counter({3: 825, 4: 8_250, 5: 28_182, 6: 38_346, 7: 20_790, 8: 3_465})
    if support_histogram != expected_support_histogram:
        raise AuditError(f"degree-four support histogram mismatch: {support_histogram}")

    header, records, counts = scan_stream()
    mass4_by_active = {active: counts[4, active] for active in range(2, N + 1)}
    if mass4_by_active != EXPECTED_MASS4_BY_ACTIVE or len(records) != EXPECTED_FULL:
        raise AuditError("raw-stream mass-four census mismatch")
    proper = sum(value for (mass, active), value in counts.items() if 1 <= mass <= 4 and active < N)
    full = sum(value for (mass, active), value in counts.items() if 1 <= mass <= 4 and active == N)
    low_proper = sum(value for (mass, active), value in counts.items() if 1 <= mass <= 3 and active < N)
    low_full = sum(value for (mass, active), value in counts.items() if 1 <= mass <= 3 and active == N)
    if (proper, full, low_proper, low_full) != (136_035, 1_468, 3_307, 3):
        raise AuditError("through-mass-four proper/full census mismatch")

    basis = exact_q.get("fixed_exact_basis", {}).get("proper_basis_column_indices")
    if not isinstance(basis, list) or len(basis) != 488 or len(set(map(int, basis))) != 488:
        raise AuditError("G-0050 exact proper basis binding mismatch")

    descriptors = [descriptor(record) for record in records]
    if descriptors != census.get("full_core_descriptors"):
        raise AuditError("G-0052 descriptors differ from raw stream")
    if canonical_sha256(descriptors) != census.get("full_core_descriptors_sha256"):
        raise AuditError("G-0052 descriptor digest mismatch")
    expected_summaries = {
        int(row["sequence"]): row for row in census.get("per_record_summaries", [])
    }
    if len(expected_summaries) != EXPECTED_FULL:
        raise AuditError("G-0052 per-record summary census mismatch")

    universe_set = set(degree4)
    union: set[Direction] = set()
    total_nnz = 0
    support_sizes: list[int] = []
    mismatches: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(processes=workers, maxtasksperchild=32) as pool:
        for completed, result in enumerate(pool.imap(worker, records, chunksize=1), start=1):
            sequence = int(result["sequence"])
            expected = expected_summaries.get(sequence)
            if expected is None:
                raise AuditError(f"unexpected sequence from worker: {sequence}")
            observed_triple = (
                int(result["support_size"]),
                int(result["total_absolute_weight"]),
                str(result["fingerprint_sha256"]),
            )
            expected_triple = (
                int(expected["hinge_support_size"]),
                int(expected["total_absolute_hinge_weight"]),
                str(expected["hinge_fingerprint_sha256"]),
            )
            if observed_triple != expected_triple:
                mismatches.append(
                    {"sequence": sequence, "observed": observed_triple, "expected": expected_triple}
                )
            hinges = result["hinges"]
            assert isinstance(hinges, tuple)
            directions = {tuple(direction) for direction, _weight in hinges}
            escaped = directions - universe_set
            if escaped:
                raise AuditError(f"sequence {sequence} escaped degree-four universe: {min(escaped)}")
            union.update(directions)
            total_nnz += int(result["support_size"])
            support_sizes.append(int(result["support_size"]))
            if completed % 100 == 0 or completed == len(records):
                print(f"CLEANROOM_G0051 full={completed}/{len(records)}", file=sys.stderr, flush=True)
    if mismatches:
        raise AuditError(f"G-0052 per-column mismatch: {mismatches[:3]}")
    if total_nnz != EXPECTED_S0_NNZ or len(union) != EXPECTED_S0_UNION:
        raise AuditError(f"S0 geometry mismatch: nnz={total_nnz}, union={len(union)}")

    union_payload = [list(direction) for direction in sorted(union)]
    union_outside_degree3 = sorted(union - set(degree3))
    if not union_outside_degree3:
        raise AuditError("degree-three omission mutant unexpectedly covers the S0 union")

    mutant_record = json.loads(json.dumps(records[0]))
    original_fingerprint = expected_summaries[136_039]["hinge_fingerprint_sha256"]
    mutant_record["negative_edges"][0][1] = 4
    mutant_fingerprint = canonical_sha256(hinge_payload(independent_hinge_column(mutant_record)))
    if mutant_fingerprint == original_fingerprint:
        raise AuditError("edge-endpoint mutant did not change the hinge fingerprint")

    mass4_total = sum(EXPECTED_MASS4_BY_ACTIVE.values())
    reduced_columns = mass4_total + 488 + 3
    if reduced_columns != 134_684:
        raise AuditError("span-equivalent reduced-column arithmetic mismatch")
    resources = {
        "s4_full_only_global": bytes_record(EXPECTED_DEGREE4_ROWS, 1_465),
        "all_full_plus_g0050_proper_basis_global": bytes_record(EXPECTED_DEGREE4_ROWS, 1_956),
        "then_all_s4_active10_proper_global": bytes_record(EXPECTED_DEGREE4_ROWS, 6_965),
        "then_all_s4_active9_proper_global": bytes_record(EXPECTED_DEGREE4_ROWS, 20_582),
        "complete_span_equivalent_reduced_global": bytes_record(EXPECTED_DEGREE4_ROWS, 134_684),
        "literal_complete_global": bytes_record(EXPECTED_DEGREE4_ROWS, 137_503),
        "s0_exact_union_restricted": bytes_record(len(union), 1_465),
        "s1_rigorous_union_upper_bound": bytes_record(len(union) + len(degree3), 1_956),
    }
    producer_resources = preflight.get("dense_resource_table")
    if not isinstance(producer_resources, dict):
        raise AuditError("G-0051 dense resource table missing")
    resource_key_map = {
        "s4_full_only_global": "s4_full_only",
        "all_full_plus_g0050_proper_basis_global": "all_full_plus_g0050_proper_basis",
        "then_all_s4_active10_proper_global": "then_all_s4_active10_proper",
        "then_all_s4_active9_proper_global": "then_all_s4_active9_proper",
        "complete_span_equivalent_reduced_global": "complete_span_equivalent_reduced_subject",
        "literal_complete_global": "literal_complete_subject",
    }
    for audit_key, producer_key in resource_key_map.items():
        producer = producer_resources.get(producer_key)
        if not isinstance(producer, dict):
            raise AuditError(f"G-0051 resource row missing: {producer_key}")
        for field in ("shape", "int64_bytes", "one_prime_uint32_bytes"):
            if producer.get(field) != resources[audit_key][field]:
                raise AuditError(f"G-0051 resource arithmetic mismatch: {producer_key}.{field}")

    if sha256_path(Path(__file__)) != script_hash_before:
        raise AuditError("audit script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "HARD_PASS_CORRECTED_MASS4_PREFLIGHT_AND_S0_GEOMETRY",
        "script_sha256": script_hash_before,
        "bindings": observed_hashes,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "independence": {
            "producer_code_imported": False,
            "row_universe_method": "disjoint signed supports plus positive compositions and primitive gcd",
            "column_method": "base-(degree+1) ordered branch-word subset-state DP",
            "input_source": "frozen raw G-0038 gzip JSONL stream",
        },
        "controls": {
            **controls,
            "all_1465_fingerprints_support_sizes_and_absolute_weights_match_G0052": True,
            "all_recomputed_hinges_belong_to_degree4_universe": True,
            "degree3_row_omission_mutant_rejected": {
                "degree3_rows": len(degree3),
                "s0_union_rows_outside_degree3": len(union_outside_degree3),
                "lex_first_missed_direction": list(union_outside_degree3[0]),
            },
            "first_record_endpoint_mutant_rejected": {
                "sequence": 136_039,
                "original_fingerprint_sha256": original_fingerprint,
                "mutant_fingerprint_sha256": mutant_fingerprint,
            },
        },
        "row_universe": {
            "degree3_count": len(degree3),
            "degree3_sha256": canonical_sha256(degree3_payload),
            "degree4_count": len(degree4),
            "degree4_sha256": canonical_sha256(degree4_payload),
            "degree3_is_strict_subset": True,
            "new_degree4_rows": len(set(degree4) - set(degree3)),
            "degree4_support_histogram": {
                str(key): value for key, value in sorted(support_histogram.items())
            },
            "lex_first": list(degree4[0]),
            "lex_last": list(degree4[-1]),
        },
        "column_census": {
            "raw_stream_header_census_report_sha256": header.get("census_report_sha256"),
            "mass4_by_active_vertices": {
                str(key): value for key, value in sorted(mass4_by_active.items())
            },
            "mass4_total": mass4_total,
            "mass4_proper": mass4_total - EXPECTED_FULL,
            "mass4_full": EXPECTED_FULL,
            "proper_signed_mass1_through4": proper,
            "full_signed_mass1_through4": full,
            "literal_signed_mass1_through4": proper + full,
            "low_mass_proper": low_proper,
            "low_mass_full": low_full,
            "g0050_exact_proper_basis_columns": len(basis),
            "span_equivalent_reduced_columns": reduced_columns,
        },
        "exact_s0_replay": {
            "column_count": len(records),
            "sequence_interval": [136_039, 137_503],
            "total_nonzeros": total_nnz,
            "global_union_direction_count": len(union),
            "global_union_directions_sha256": canonical_sha256(union_payload),
            "support_minimum": min(support_sizes),
            "support_median_low": int(statistics.median_low(support_sizes)),
            "support_maximum": max(support_sizes),
        },
        "dense_resources": resources,
        "rank_criterion_audit": {
            "verdict": "VALID_OVER_ANY_FIELD",
            "statement": "exists c with Hc=0 and lambda*c!=0 iff rank([H;lambda])=rank(H)+1",
            "selected_subset_positive_is_global_by_zero_extension": True,
            "subset_negative_does_not_extend_to_omitted_columns": True,
            "full_column_rank_mod_prime_implies_full_column_rank_over_Q": True,
            "modular_gain_alone_is_only_a_rational_lifting_candidate": True,
            "modular_no_gain_alone_is_not_a_rational_obstruction": True,
        },
        "boundary_audit": {
            "g0051_resource_preflight_only": "PASS",
            "g0052_full_core_census_only": "PASS",
            "mass4_negative_remains_bounded_to_frozen_pair_orbit_ansatz": "PASS",
            "no_rank_construction_or_unrestricted_network_claim_earned": True,
        },
        "claim_boundary": (
            "This clean-room audit independently verifies the 99,858-row degree-four universe, "
            "the frozen column arithmetic, dense byte estimates, and the S0 full-core geometry "
            "(42,457-row exact union and 12,331,131 nonzeros). It computes no S0 rank, no "
            "rational circuit, and no mass-four or unrestricted MAX11 theorem."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_json_atomic(path: Path, value: object, replace: bool) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise AuditError("output must remain inside the project") from error
    if resolved.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite {resolved}; pass --replace explicitly")
    temporary = resolved.with_name(resolved.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as sink:
        sink.write(canonical_bytes(value))
        sink.flush()
        os.fsync(sink.fileno())
    temporary.replace(resolved)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.self_test:
        print(json.dumps({"result": "PASS", "controls": self_test()}, sort_keys=True))
        return
    report = audit(args.workers)
    write_json_atomic(args.output, report, args.replace)
    print(json.dumps({"result": report["result"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
