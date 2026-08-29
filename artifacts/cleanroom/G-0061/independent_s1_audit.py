#!/usr/bin/env python3
"""Independent exact audit of the frozen G-0061 S1 baseline.

The decisive path in this file does not import or execute the G-0061 or G-0057
producer programs.  It reconstructs the row universe and pair-atom semantics
from the mathematical definitions, using only hash-bound descriptor manifests
from G-0050/G-0056 and the raw signed-orbit descriptor stream bound by G-0050.

The output is a bounded consistency verdict.  It says nothing about the
remaining mass-four columns or unrestricted two-hidden-layer MAX11.
"""

from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations, permutations
import json
from math import comb, factorial, gcd, lcm
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Iterable, Iterator, Sequence

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

PRODUCER_COMMIT = "04ff8cfaec3ac3eddfa7f78ae36a8cd783fe3a74"
PRODUCER_SCRIPT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift.py"
PRODUCER_REPORT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift_v1.json.gz"
G0050_EXACT = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"
G0050_RANK_AUDIT = ROOT / "artifacts/math/G-0050/full_row_rank_audit_v1.json.gz"
G0056_EXACT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift_v1.json.gz"
G0059_REPORT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz"
SIGNED_STREAM = (
    ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)

EXPECTED_PRODUCER_SCRIPT_SHA256 = (
    "2e0ad714b2f56104fc70b98c5527f291769acb7a32053e44840a643d7046e7e8"
)
EXPECTED_PRODUCER_REPORT_SHA256 = (
    "d372ac740e485b4608b23a879ed466051aa1d45f899aa9dce89ff8d2ee13b7f2"
)
EXPECTED_SIGNED_STREAM_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_UNIVERSE_SHA256 = (
    "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
)
EXPECTED_ROWS = 99_858
EXPECTED_COLUMNS = 1_358
EXPECTED_RANK = 1_288
EXPECTED_NULLITY = 70
PRIMES = (1_000_003, 1_000_033)

Direction = tuple[int, ...]
Branch = tuple[tuple[int, int], ...]
Pair = tuple[Branch, Branch]

_ROW_INDEX: dict[Direction, int] = {}
_FALLING_MULTIPLICITIES: dict[int, tuple[tuple[int, ...], ...]] = {}


class AuditError(RuntimeError):
    """Fail-closed clean-room audit error."""


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


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AuditError(f"top-level JSON object required: {path}")
    return value


def weak_compositions(total: int, parts: int, prefix: Direction = ()) -> Iterator[Direction]:
    if parts == 1:
        yield prefix + (total,)
        return
    for first in range(total + 1):
        yield from weak_compositions(total - first, parts - 1, prefix + (first,))


def primitive_direction_universe(n: int = 11, degree: int = 4) -> tuple[Direction, ...]:
    """Enumerate chamber-crossing primitive differences of degree-k compositions."""

    compositions = tuple(weak_compositions(degree, n))
    directions: set[Direction] = set()
    for left, right in combinations(compositions, 2):
        raw = tuple(b - a for a, b in zip(left, right, strict=True))
        running = 0
        prefixes = []
        for value in raw[:-1]:
            running += value
            prefixes.append(running)
        # Then raw.x <= 0 on the ordered cone, so this comparison is linear there.
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in raw:
            divisor = gcd(divisor, abs(value))
        if not divisor:
            raise AuditError("zero composition difference escaped")
        directions.add(tuple(value // divisor for value in raw))
    return tuple(sorted(directions))


def compact_pair(record: dict[str, Any]) -> tuple[Pair, int]:
    branches: list[Branch] = []
    for key in ("negative_edges", "positive_edges"):
        raw_branch = tuple(tuple(map(int, edge)) for edge in record[key])
        branches.append(raw_branch)
    used = sorted({vertex for branch in branches for edge in branch for vertex in edge})
    if not used:
        raise AuditError(f"empty signed core at sequence {record.get('sequence')}")
    relabel = {vertex: index for index, vertex in enumerate(used)}
    pair: Pair = tuple(
        tuple((relabel[u], relabel[v]) for u, v in branch) for branch in branches
    )  # type: ignore[assignment]
    return pair, len(used)


def branch_incidence(branch: Branch, active: int) -> tuple[list[int], list[list[int]]]:
    loops = [0] * active
    adjacency = [[0] * active for _ in range(active)]
    for u, v in branch:
        if u == v:
            loops[u] += 1
        else:
            adjacency[u][v] += 1
            adjacency[v][u] += 1
    return loops, adjacency


def rank_word_pairs(pair: Pair, active: int) -> Counter[tuple[Direction, Direction]]:
    """Subset DP over all active-vertex orders, coalescing identical rank words."""

    prepared = tuple(branch_incidence(branch, active) for branch in pair)
    states: dict[int, Counter[tuple[Direction, Direction]]] = {
        0: Counter({((), ()): 1})
    }
    full_mask = (1 << active) - 1
    for _rank in range(active):
        following: dict[int, Counter[tuple[Direction, Direction]]] = {}
        for subset, prefixes in states.items():
            for vertex in range(active):
                if (subset >> vertex) & 1:
                    continue
                next_values = []
                for loops, adjacency in prepared:
                    next_values.append(
                        loops[vertex]
                        + sum(
                            adjacency[vertex][other]
                            for other in range(active)
                            if (subset >> other) & 1
                        )
                    )
                extended = following.setdefault(subset | (1 << vertex), Counter())
                for (left, right), multiplicity in prefixes.items():
                    extended[
                        (
                            left + (next_values[0],),
                            right + (next_values[1],),
                        )
                    ] += multiplicity
        states = following
    raw = states.get(full_mask)
    if raw is None:
        raise AuditError("rank-word DP failed to reach full subset")
    result: Counter[tuple[Direction, Direction]] = Counter()
    for (left, right), multiplicity in raw.items():
        result[(left, right) if left <= right else (right, left)] += multiplicity
    if sum(result.values()) != factorial(active):
        raise AuditError("rank-word permutation census mismatch")
    return result


def hinge_normal_form(
    rank_words: Counter[tuple[Direction, Direction]],
) -> Counter[Direction]:
    """Return exact primitive hinge coefficients on the ordered cone."""

    hinges: Counter[Direction] = Counter()
    for (base, other), multiplicity in rank_words.items():
        if base == other:
            continue
        raw = tuple(b - a for a, b in zip(base, other, strict=True))
        if sum(raw):
            raise AuditError("equal-degree branch direction is not zero-sum")
        running = 0
        prefixes = []
        for value in raw[:-1]:
            running += value
            prefixes.append(running)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in raw:
            divisor = gcd(divisor, abs(value))
        if not divisor:
            raise AuditError("zero hinge direction escaped branch equality")
        primitive = tuple(value // divisor for value in raw)
        hinges[primitive] += multiplicity * divisor
    return hinges


def falling(total: int, chosen: int) -> int:
    if not 0 <= chosen <= total:
        return 0
    return factorial(total) // factorial(total - chosen)


def falling_multiplicities(active: int, n: int = 11) -> tuple[tuple[int, ...], ...]:
    cached = _FALLING_MULTIPLICITIES.get(active)
    if cached is not None:
        return cached
    table = tuple(
        tuple(
            falling(top, selected)
            * falling(n - top, active - selected)
            * factorial(n - active)
            for selected in range(active + 1)
        )
        for top in range(n + 1)
    )
    _FALLING_MULTIPLICITIES[active] = table
    return table


def binary_finite_difference(pair: Pair, active: int, n: int = 11) -> int:
    """Compute Delta^n of the full permutation-symmetrized binary profile."""

    table = falling_multiplicities(active, n)
    profile = [0] * (n + 1)
    for mask in range(1 << active):
        selected = mask.bit_count()
        branch_values = [
            sum(bool((mask >> u) & 1 or (mask >> v) & 1) for u, v in branch)
            for branch in pair
        ]
        atom_value = max(branch_values)
        if not atom_value:
            continue
        for top in range(n + 1):
            profile[top] += table[top][selected] * atom_value
    return sum(
        (-1) ** (n - top) * comb(n, top) * profile[top]
        for top in range(n + 1)
    )


def g0057_column_hash(
    namespace: str,
    source_id: int,
    rows: np.ndarray,
    values: np.ndarray,
    invariant: int,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0057-complete-row-sparse-column-v1\n")
    digest.update(namespace.encode("ascii") + b"\n")
    digest.update(int(source_id).to_bytes(8, "little", signed=False))
    digest.update(int(invariant).to_bytes(8, "little", signed=True))
    digest.update(int(len(rows)).to_bytes(8, "little", signed=False))
    digest.update(rows.astype("<u4", copy=False).tobytes(order="C"))
    digest.update(values.astype("<i8", copy=False).tobytes(order="C"))
    return digest.hexdigest()


def g0054_column_hash(
    sequence: int, rows: np.ndarray, values: np.ndarray, invariant: int
) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0054-full-row-sparse-column-v1\n")
    digest.update(int(sequence).to_bytes(8, "little", signed=False))
    digest.update(int(invariant).to_bytes(8, "little", signed=True))
    digest.update(int(len(rows)).to_bytes(8, "little", signed=False))
    digest.update(rows.astype("<u4", copy=False).tobytes(order="C"))
    digest.update(values.astype("<i8", copy=False).tobytes(order="C"))
    return digest.hexdigest()


def semantic_worker(payload: tuple[int, str, int, dict[str, Any]]) -> dict[str, Any]:
    order, namespace, source_id, record = payload
    if not _ROW_INDEX:
        raise AuditError("worker row index is uninitialized")
    pair, active = compact_pair(record)
    local_hinges = hinge_normal_form(rank_word_pairs(pair, active))
    multiplier = factorial(11 - active)
    selected: Counter[int] = Counter()
    for positions in combinations(range(11), active):
        for local_direction, raw_weight in local_hinges.items():
            embedded = [0] * 11
            for local_index, value in enumerate(local_direction):
                embedded[positions[local_index]] = value
            direction = tuple(embedded)
            row = _ROW_INDEX.get(direction)
            if row is None:
                raise AuditError(
                    f"hinge escaped degree-four universe at order {order}: {direction}"
                )
            selected[row] += multiplier * int(raw_weight)
    sparse = sorted((row, value) for row, value in selected.items() if value)
    rows = np.fromiter((row for row, _value in sparse), dtype=np.uint32)
    values = np.fromiter((value for _row, value in sparse), dtype=np.int64)
    invariant = binary_finite_difference(pair, active)
    sequence = int(record["sequence"])
    return {
        "order": order,
        "namespace": namespace,
        "source_id": source_id,
        "sequence": sequence,
        "active_vertices": active,
        "rows": rows,
        "values": values,
        "lambda": invariant,
        "semantic_sha256": g0057_column_hash(
            namespace, source_id, rows, values, invariant
        ),
    }


def init_semantic_worker(row_index: dict[Direction, int]) -> None:
    global _ROW_INDEX
    _ROW_INDEX = row_index


def load_lowmass_records(expected_stream_hash: str) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    observed = sha256_path(SIGNED_STREAM)
    if observed != expected_stream_hash:
        raise AuditError(f"signed descriptor stream drift: {observed}")
    header: dict[str, Any] | None = None
    records: list[dict[str, Any]] = []
    with gzip.open(SIGNED_STREAM, "rt", encoding="utf-8") as source:
        for line in source:
            item = json.loads(line)
            if header is None:
                header = item
                if item.get("record_type") != "header":
                    raise AuditError("signed stream lacks header")
                continue
            if item.get("record_type") != "orbit":
                raise AuditError("unexpected signed stream record type")
            signed_mass = int(item["signed_mass"])
            if signed_mass > 3:
                break
            if signed_mass > 0:
                records.append(item)
    if header is None:
        raise AuditError("empty signed stream")
    if len(records) != 3_310:
        raise AuditError(f"low-mass record count drift: {len(records)}")
    if [int(item["sequence"]) for item in records] != list(range(1, 3_311)):
        raise AuditError("low-mass sequence order drift")
    if any(int(item["active_vertices"]) >= 11 for item in records[:-3]):
        raise AuditError("unexpected full-support low-mass record")
    if any(int(item["active_vertices"]) != 11 for item in records[-3:]):
        raise AuditError("three full-support seed descriptors missing")
    return header, records


def ordered_sparse_stream_hash(semantics: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0057-ordered-complete-row-sparse-stream-v1\n")
    for column in semantics:
        digest.update(bytes.fromhex(str(column["semantic_sha256"])))
    return digest.hexdigest()


def dense_matrix_hash(matrix: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(
        f"int64-little-row-major;shape={matrix.shape[0]}x{matrix.shape[1]}\n".encode()
    )
    for start in range(0, matrix.shape[0], 256):
        digest.update(
            matrix[start : start + 256]
            .astype("<i8", copy=False)
            .tobytes(order="C")
        )
    return digest.hexdigest()


def scientific_view(value: object) -> object:
    dynamic = {
        "seconds",
        "wall_seconds",
        "semantic_seconds",
        "available_gib",
        "memory_available_bytes",
        "minimum_required_gib",
    }
    if isinstance(value, dict):
        return {
            key: scientific_view(item)
            for key, item in value.items()
            if key not in dynamic
        }
    if isinstance(value, list):
        return [scientific_view(item) for item in value]
    return value


def producer_scientific_hash(report: dict[str, Any]) -> str:
    keys = (
        "schema",
        "result",
        "epistemic_status",
        "bindings",
        "controls",
        "two_prime_rational_reconstruction",
        "exact_kernel_basis",
        "exact_complete_replay",
        "deterministic_height_certificate",
        "exact_rank_certificate",
        "canonical_exact_s1_basis",
        "exact_bounded_conclusion",
        "claim_boundary",
        "mandatory_next_gate",
    )
    return canonical_sha256(scientific_view({key: report[key] for key in keys}))


def relation_coefficients(relation: dict[str, Any]) -> tuple[list[int], list[int]]:
    support = list(map(int, relation["support_zero_based_columns"]))
    coefficients = list(map(int, relation["cleared_integer_coefficients"]))
    if len(support) != len(coefficients) or not support:
        raise AuditError("malformed displayed relation")
    if support != sorted(set(support)):
        raise AuditError("displayed relation support is not sorted and unique")
    if any(not 0 <= column < EXPECTED_COLUMNS for column in support):
        raise AuditError("displayed relation column out of range")
    return support, coefficients


def determinant_mod_prime(matrix: np.ndarray, prime: int) -> int:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.int64)
    field = nmod_mat(
        reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime
    )
    return int(field.det())


def run_self_tests() -> dict[str, Any]:
    pair: Pair = (
        ((0, 0), (3, 3)),
        ((1, 1), (2, 2)),
    )
    active = 4
    dynamic = rank_word_pairs(pair, active)
    brute: Counter[tuple[Direction, Direction]] = Counter()
    for order in permutations(range(active)):
        position = [0] * active
        for rank, vertex in enumerate(order):
            position[vertex] = rank
        words = []
        for branch in pair:
            word = [0] * active
            for u, v in branch:
                word[max(position[u], position[v])] += 1
            words.append(tuple(word))
        left, right = words
        brute[(left, right) if left <= right else (right, left)] += 1
    if dynamic != brute:
        raise AuditError("subset DP disagrees with direct permutation control")
    honest = hinge_normal_form(dynamic)
    if not honest:
        raise AuditError("small exact positive control has no hinges")
    broken = Counter(dynamic)
    first_key = next(iter(broken))
    broken[first_key] += 1
    if broken == brute:
        raise AuditError("multiplicity mutant escaped small control")
    return {
        "direct_permutation_matches_subset_dp": True,
        "small_positive_hinge_count": len(honest),
        "multiplicity_plus_one_mutant_rejected": True,
    }


def verify_bindings(producer: dict[str, Any]) -> dict[str, Any]:
    if sha256_path(PRODUCER_SCRIPT) != EXPECTED_PRODUCER_SCRIPT_SHA256:
        raise AuditError("producer script bytes drifted from frozen commit")
    if sha256_path(PRODUCER_REPORT) != EXPECTED_PRODUCER_REPORT_SHA256:
        raise AuditError("producer report bytes drifted from frozen commit")
    if producer["script_sha256"] != EXPECTED_PRODUCER_SCRIPT_SHA256:
        raise AuditError("producer report script binding mismatch")
    paths = {
        "g0050_script_sha256": ROOT / "artifacts/math/G-0050/exact_q_bridge.py",
        "g0050_report_sha256": G0050_EXACT,
        "g0054_script_sha256": ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py",
        "g0054_report_sha256": ROOT / "artifacts/math/G-0054/s0_union_rank_gate_v1.json.gz",
        "g0055_script_sha256": ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule.py",
        "g0055_report_sha256": ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule_v1.json.gz",
        "g0056_script_sha256": ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift.py",
        "g0056_report_sha256": G0056_EXACT,
        "g0057_script_sha256": ROOT / "artifacts/math/G-0057/s1_high_active_extension_gate.py",
        "g0057_report_sha256": ROOT / "artifacts/math/G-0057/s1_baseline_gate_v1.json.gz",
        "g0059_script_sha256": ROOT / "artifacts/math/G-0059/modular_quotient_oracle.py",
        "g0059_report_sha256": G0059_REPORT,
    }
    observed = {key: sha256_path(path) for key, path in paths.items()}
    expected = {key: str(producer["bindings"][key]) for key in paths}
    if observed != expected:
        raise AuditError(f"upstream byte binding mismatch: {observed}")
    return {
        "producer_commit": PRODUCER_COMMIT,
        "producer_script_sha256": EXPECTED_PRODUCER_SCRIPT_SHA256,
        "producer_report_sha256": EXPECTED_PRODUCER_REPORT_SHA256,
        "all_twelve_upstream_file_hashes_match": True,
        "upstream_hashes": observed,
    }


def run(workers: int) -> dict[str, Any]:
    started = time.perf_counter()
    self_tests = run_self_tests()
    producer = load_json_gz(PRODUCER_REPORT)
    g0050 = load_json_gz(G0050_EXACT)
    g0050_rank = load_json_gz(G0050_RANK_AUDIT)
    g0056 = load_json_gz(G0056_EXACT)
    g0059 = load_json_gz(G0059_REPORT)
    bindings = verify_bindings(producer)

    if producer.get("schema") != "max11-g0061-exact-s1-kernel-lift-v1":
        raise AuditError("unexpected producer schema")
    if producer.get("result") != "EXACT_Q_S1_BASELINE_RANK_1288_KERNEL_70_ALL_LAMBDA_ZERO":
        raise AuditError("unexpected producer result label")

    scientific_hash = producer_scientific_hash(producer)
    expected_scientific_hash = str(producer["canonical_scientific_payload_sha256"])
    if scientific_hash != expected_scientific_hash:
        raise AuditError("producer canonical scientific payload hash mismatch")
    runtime_mutant = deepcopy(producer)
    runtime_mutant["controls"]["resource_preflight"]["available_gib"] = -12345.0
    if producer_scientific_hash(runtime_mutant) != scientific_hash:
        raise AuditError("runtime-only scientific projection mutant changed digest")
    scientific_mutant = deepcopy(producer)
    scientific_mutant["exact_rank_certificate"]["exact_rank_Q"] -= 1
    if producer_scientific_hash(scientific_mutant) == scientific_hash:
        raise AuditError("scientific rank mutant escaped digest")

    universe_started = time.perf_counter()
    universe = primitive_direction_universe()
    universe_hash = canonical_sha256([list(direction) for direction in universe])
    if len(universe) != EXPECTED_ROWS or universe_hash != EXPECTED_UNIVERSE_SHA256:
        raise AuditError(f"complete row universe mismatch: {len(universe)} {universe_hash}")
    if universe_hash != producer["bindings"]["complete_degree4_universe_sha256"]:
        raise AuditError("producer universe binding mismatch")
    row_drop_mutant_hash = canonical_sha256([list(direction) for direction in universe[:-1]])
    if row_drop_mutant_hash == universe_hash:
        raise AuditError("dropped-row universe mutant escaped hash")
    row_index = {direction: index for index, direction in enumerate(universe)}
    universe_seconds = time.perf_counter() - universe_started

    stream_hash = str(g0050_rank["bindings"]["g0038_stream_sha256"])
    if stream_hash != EXPECTED_SIGNED_STREAM_SHA256:
        raise AuditError("G-0050 does not bind the expected signed descriptor stream")
    stream_header, lowmass_records = load_lowmass_records(stream_hash)
    proper_indices = list(map(int, g0050["fixed_exact_basis"]["proper_basis_column_indices"]))
    if len(proper_indices) != 488 or proper_indices != sorted(set(proper_indices)):
        raise AuditError("G-0050 proper-basis index manifest malformed")
    seed_indices = [3_307, 3_308, 3_309]

    s0_manifest = g0056["canonical_exact_s0_basis"]["basis_manifest"]
    if len(s0_manifest) != 867:
        raise AuditError("G-0056 exact S0 descriptor manifest malformed")
    payloads: list[tuple[int, str, int, dict[str, Any]]] = []
    for source_id, item in enumerate(s0_manifest):
        descriptor = dict(item["descriptor"])
        payloads.append((len(payloads), "s0_mass4_pivot", source_id, descriptor))
    for source_id in proper_indices:
        payloads.append(
            (
                len(payloads),
                "lowmass_proper_basis",
                source_id,
                lowmass_records[source_id],
            )
        )
    for source_id in seed_indices:
        payloads.append(
            (
                len(payloads),
                "lowmass_full_seed",
                source_id,
                lowmass_records[source_id],
            )
        )
    if len(payloads) != EXPECTED_COLUMNS:
        raise AuditError("S1 payload count drift")

    semantic_started = time.perf_counter()
    global _ROW_INDEX
    _ROW_INDEX = row_index
    semantics: list[dict[str, Any]] = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_semantic_worker,
        initargs=(row_index,),
        maxtasksperchild=32,
    ) as pool:
        for result in pool.imap_unordered(semantic_worker, payloads, chunksize=1):
            semantics.append(result)
            if len(semantics) % 50 == 0 or len(semantics) == len(payloads):
                print(
                    f"G0061_CLEANROOM semantics={len(semantics)}/{len(payloads)}",
                    file=sys.stderr,
                    flush=True,
                )
    semantics.sort(key=lambda item: int(item["order"]))
    if [int(item["order"]) for item in semantics] != list(range(EXPECTED_COLUMNS)):
        raise AuditError("semantic worker output order drift")
    semantic_seconds = time.perf_counter() - semantic_started

    # G-0056 is an older, independently frozen descriptor/lambda/hash manifest for S0.
    for column, expected in enumerate(s0_manifest):
        observed = semantics[column]
        legacy_hash = g0054_column_hash(
            int(observed["sequence"]),
            observed["rows"],
            observed["values"],
            int(observed["lambda"]),
        )
        if (
            int(observed["sequence"]) != int(expected["source_sequence"])
            or int(observed["lambda"]) != int(expected["lambda"])
            or len(observed["rows"]) != int(expected["support_size"])
            or legacy_hash != expected["semantic_sha256"]
        ):
            raise AuditError(f"independent S0 semantic mismatch at column {column}")

    if any(int(item["lambda"]) for item in semantics[867 : 867 + 488]):
        raise AuditError("proper-support low-mass Lambda did not vanish")
    seed_lambdas = [int(item["lambda"]) for item in semantics[-3:]]
    if seed_lambdas != [239_500_800] * 3:
        raise AuditError(f"low-mass full-seed Lambda mismatch: {seed_lambdas}")

    stream_digest = ordered_sparse_stream_hash(semantics)
    expected_stream_digest = str(
        producer["controls"]["semantic_regeneration"]["ordered_sparse_stream_sha256"]
    )
    if stream_digest != expected_stream_digest:
        raise AuditError("independent ordered sparse semantic stream mismatch")

    pivot_manifest = producer["canonical_exact_s1_basis"]["basis_manifest"]
    pivot_columns = list(map(int, producer["exact_rank_certificate"]["pivot_columns"]))
    if len(pivot_manifest) != EXPECTED_RANK or len(pivot_columns) != EXPECTED_RANK:
        raise AuditError("producer pivot basis count drift")
    for expected, column in zip(pivot_manifest, pivot_columns, strict=True):
        observed = semantics[column]
        if (
            int(expected["basis_index"]) != pivot_columns.index(column)
            or expected["namespace"] != observed["namespace"]
            or int(expected["source_id"]) != int(observed["source_id"])
            or int(expected["source_sequence"]) != int(observed["sequence"])
            or int(expected["active_vertices"]) != int(observed["active_vertices"])
            or int(expected["support_size"]) != len(observed["rows"])
            or int(expected["lambda"]) != int(observed["lambda"])
            or expected["semantic_sha256"] != observed["semantic_sha256"]
        ):
            raise AuditError(f"producer pivot manifest mismatch at S1 column {column}")

    union_mask = np.zeros(EXPECTED_ROWS, dtype=np.bool_)
    total_nonzeros = 0
    for column in semantics:
        union_mask[column["rows"]] = True
        total_nonzeros += len(column["rows"])
    union_rows = np.flatnonzero(union_mask).astype(np.uint32)
    compressed = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    compressed[union_rows] = np.arange(len(union_rows), dtype=np.int32)
    matrix = np.zeros((len(union_rows), EXPECTED_COLUMNS), dtype=np.int64)
    for column, semantic in enumerate(semantics):
        local_rows = compressed[semantic["rows"]]
        if np.any(local_rows < 0):
            raise AuditError("semantic column escaped exact union")
        matrix[local_rows, column] = semantic["values"]
    if int(np.count_nonzero(matrix)) != total_nonzeros:
        raise AuditError("dense union construction lost or duplicated entries")
    lambda_row = np.array([item["lambda"] for item in semantics], dtype=np.int64)

    union_hash = hashlib.sha256(
        union_rows.astype("<u4", copy=False).tobytes(order="C")
    ).hexdigest()
    matrix_hash = dense_matrix_hash(matrix)
    lambda_hash = hashlib.sha256(
        lambda_row.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    semantic_expected = producer["controls"]["semantic_regeneration"]
    expected_triplet = (
        semantic_expected["union_row_indices_sha256"],
        semantic_expected["integer_matrix_sha256"],
        semantic_expected["lambda_row_sha256"],
    )
    if (union_hash, matrix_hash, lambda_hash) != expected_triplet:
        raise AuditError("independent matrix/row/Lambda bytes disagree with producer")

    relations = producer["exact_kernel_basis"]["relations"]
    if len(relations) != EXPECTED_NULLITY:
        raise AuditError("displayed relation count drift")
    if canonical_sha256(relations) != producer["exact_kernel_basis"]["relations_sha256"]:
        raise AuditError("displayed relation manifest hash mismatch")
    distinguished = list(
        map(int, producer["exact_kernel_basis"]["distinguished_nonpivot_columns"])
    )
    if len(distinguished) != EXPECTED_NULLITY or len(set(distinguished)) != EXPECTED_NULLITY:
        raise AuditError("distinguished free-coordinate manifest malformed")
    if sorted(pivot_columns + distinguished) != list(range(EXPECTED_COLUMNS)):
        raise AuditError("pivot/free columns do not partition the S1 columns")
    free_set = set(distinguished)

    replayed_terms = 0
    maximum_intermediate = 0
    maximum_relation_absolute_bound = 0
    lambda_residuals: list[int] = []
    column_maxima = [
        max((abs(int(value)) for value in semantic["values"]), default=0)
        for semantic in semantics
    ]
    for relation_index, relation in enumerate(relations):
        support, coefficients = relation_coefficients(relation)
        if int(relation["basis_index"]) != relation_index:
            raise AuditError("displayed relation basis index/order mismatch")
        own_free = int(relation["distinguished_nonpivot_column"])
        if own_free != distinguished[relation_index]:
            raise AuditError("displayed relation/free-coordinate order mismatch")
        rational = [Fraction(value) for value in relation["rational_coefficients"]]
        if len(rational) != len(support):
            raise AuditError("rational relation length mismatch")
        denominator_lcm = int(relation["denominator_lcm"])
        exact_denominator_lcm = 1
        for coefficient in rational:
            exact_denominator_lcm = lcm(exact_denominator_lcm, coefficient.denominator)
        if denominator_lcm != exact_denominator_lcm:
            raise AuditError("displayed denominator LCM is not the exact coefficient LCM")
        if [int(coefficient * denominator_lcm) for coefficient in rational] != coefficients:
            raise AuditError("rational and cleared-integer coefficients disagree")
        if set(support) & free_set != {own_free}:
            raise AuditError("relation uses another relation's free coordinate")
        own_index = support.index(own_free)
        if rational[own_index] != 1:
            raise AuditError("distinguished rational coefficient is not one")
        absolute_bound = sum(
            abs(coefficient) * column_maxima[column]
            for column, coefficient in zip(support, coefficients, strict=True)
        )
        if absolute_bound > np.iinfo(np.int64).max:
            raise AuditError("relation replay could overflow signed int64")
        maximum_relation_absolute_bound = max(
            maximum_relation_absolute_bound, absolute_bound
        )
        residual = np.zeros(len(union_rows), dtype=np.int64)
        for column, coefficient in zip(support, coefficients, strict=True):
            residual += matrix[:, column] * coefficient
            maximum_intermediate = max(
                maximum_intermediate, int(np.max(np.abs(residual), initial=0))
            )
            replayed_terms += len(semantics[column]["rows"])
        nonzero = np.flatnonzero(residual)
        if len(nonzero):
            complete_row = int(union_rows[int(nonzero[0])])
            raise AuditError(
                f"relation {relation_index} fails at row {complete_row}: "
                f"{int(residual[int(nonzero[0])])}"
            )
        lambda_residual = sum(
            coefficient * int(lambda_row[column])
            for column, coefficient in zip(support, coefficients, strict=True)
        )
        if lambda_residual:
            raise AuditError(
                f"relation {relation_index} has nonzero Lambda: {lambda_residual}"
            )
        lambda_residuals.append(lambda_residual)

    # Exact coefficient mutation: one displayed coefficient is incremented by one.
    mutant_support, mutant_coefficients = relation_coefficients(relations[0])
    mutant_coefficients[0] += 1
    mutant_residual = matrix[:, mutant_support] @ np.array(
        mutant_coefficients, dtype=np.int64
    )
    mutant_nonzero = np.flatnonzero(mutant_residual)
    if not len(mutant_nonzero):
        raise AuditError("coefficient +1 relation mutant was not rejected")
    mutant_local_row = int(mutant_nonzero[0])
    mutant_complete_row = int(union_rows[mutant_local_row])

    # A Lambda-byte mutation must destroy the same relation's Lambda identity.
    lambda_mutant = lambda_row.copy()
    lambda_mutant[mutant_support[0]] += 1
    lambda_mutant_residual = sum(
        coefficient * int(lambda_mutant[column])
        for column, coefficient in zip(
            mutant_support,
            relation_coefficients(relations[0])[1],
            strict=True,
        )
    )
    if not lambda_mutant_residual:
        raise AuditError("Lambda +1 mutant was not rejected")

    pivot_complete_rows = list(
        map(int, producer["exact_rank_certificate"]["pivot_complete_rows"])
    )
    if len(pivot_complete_rows) != EXPECTED_RANK or len(set(pivot_complete_rows)) != EXPECTED_RANK:
        raise AuditError("pivot row manifest malformed")
    pivot_columns_hash = canonical_sha256(pivot_columns)
    pivot_rows_hash = canonical_sha256(pivot_complete_rows)
    if (
        pivot_columns_hash
        != producer["exact_rank_certificate"]["pivot_columns_sha256"]
        or pivot_rows_hash
        != producer["exact_rank_certificate"]["pivot_complete_rows_sha256"]
    ):
        raise AuditError("producer pivot row/column canonical hash mismatch")
    local_pivot_rows = compressed[np.array(pivot_complete_rows, dtype=np.int64)]
    if np.any(local_pivot_rows < 0):
        raise AuditError("pivot row escaped independently reconstructed union")
    minor = np.ascontiguousarray(
        matrix[np.ix_(local_pivot_rows, np.array(pivot_columns, dtype=np.int64))],
        dtype=np.int64,
    )
    if minor.shape != (EXPECTED_RANK, EXPECTED_RANK):
        raise AuditError("pivot minor shape mismatch")
    minor_hash = hashlib.sha256(
        minor.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    if minor_hash != producer["exact_rank_certificate"]["minor_int64_row_major_sha256"]:
        raise AuditError("pivot minor byte hash mismatch")

    expected_primes = tuple(
        int(item["prime"])
        for item in producer["exact_rank_certificate"]["minor_determinant_residues"]
    )
    if expected_primes != PRIMES:
        raise AuditError("producer determinant-prime manifest drift")
    g0059_prime_items = g0059["prime_results"]
    if tuple(int(item["prime"]) for item in g0059_prime_items) != PRIMES:
        raise AuditError("G-0059 determinant-prime manifest drift")
    g0059_primes = {int(item["prime"]): item for item in g0059_prime_items}
    determinant_results = []
    for expected in producer["exact_rank_certificate"]["minor_determinant_residues"]:
        prime = int(expected["prime"])
        determinant = determinant_mod_prime(minor, prime)
        frozen = g0059_primes[prime]
        frozen_minor = frozen["pivot_minor"]
        if (
            determinant != int(expected["determinant"])
            or determinant != int(frozen_minor["determinant_mod_prime"])
            or int(frozen["baseline_rank"]) != EXPECTED_RANK
            or int(frozen["baseline_nullity"]) != EXPECTED_NULLITY
            or int(frozen_minor["rank"]) != EXPECTED_RANK
            or list(map(int, frozen_minor["pivot_columns"])) != pivot_columns
            or list(map(int, frozen_minor["pivot_complete_rows"])) != pivot_complete_rows
            or frozen_minor["pivot_columns_sha256"] != pivot_columns_hash
            or frozen_minor["pivot_complete_rows_sha256"] != pivot_rows_hash
            or frozen_minor["minor_int64_sha256"] != minor_hash
        ):
            raise AuditError(f"prime-{prime} pivot-minor manifest mismatch")
        if not determinant:
            raise AuditError(f"prime-{prime} pivot minor is singular")
        determinant_results.append({"prime": prime, "determinant": determinant})

    duplicate_row_minor = minor.copy()
    duplicate_row_minor[-1, :] = duplicate_row_minor[0, :]
    duplicate_row_determinant = determinant_mod_prime(duplicate_row_minor, PRIMES[0])
    if duplicate_row_determinant:
        raise AuditError("duplicate-row singular-minor mutant was not rejected")

    # The exact nonzero minor gives rank_Q >= 1288.  Seventy exact independent
    # kernel vectors, triangular on distinct free coordinates, give rank_Q <= 1288.
    exact_rank = EXPECTED_RANK
    exact_nullity = EXPECTED_COLUMNS - exact_rank
    if exact_nullity != EXPECTED_NULLITY:
        raise AuditError("rank-nullity arithmetic mismatch")

    output: dict[str, Any] = {
        "schema": "max11-g0061-independent-cleanroom-audit-v1",
        "result": "CONSISTENT_EXACT_BOUNDED_S1_RANK_1288_KERNEL_70_ALL_LAMBDA_ZERO",
        "subject": {
            "producer_commit": PRODUCER_COMMIT,
            "producer_script_sha256": EXPECTED_PRODUCER_SCRIPT_SHA256,
            "producer_report_sha256": EXPECTED_PRODUCER_REPORT_SHA256,
        },
        "independence_boundary": {
            "g0061_or_g0057_code_imported_or_executed": False,
            "semantic_method": (
                "fresh subset-state rank-word DP, primitive chamber-hinge reduction, "
                "injection embedding, and direct binary finite differences"
            ),
            "descriptor_sources": [
                "G-0056 exact S0 basis manifest (867 descriptors)",
                "G-0050 exact proper-basis index manifest (488 indices)",
                "G-0050 rank-audit-bound raw G-0038 descriptor stream (3 seeds and selected proper records)",
            ],
            "method_disjoint_T3_claim": False,
        },
        "bindings": bindings,
        "row_universe": {
            "degree": 4,
            "row_count": len(universe),
            "canonical_sha256": universe_hash,
            "first_direction": list(universe[0]),
            "last_direction": list(universe[-1]),
        },
        "descriptor_census": {
            "signed_stream_sha256": EXPECTED_SIGNED_STREAM_SHA256,
            "signed_stream_header_sha256": canonical_sha256(stream_header),
            "s0_descriptors": 867,
            "lowmass_proper_basis_descriptors": 488,
            "lowmass_full_seed_descriptors": 3,
            "total_columns": len(payloads),
        },
        "exact_semantics": {
            "complete_row_count": EXPECTED_ROWS,
            "union_row_count": len(union_rows),
            "omitted_all_zero_rows": EXPECTED_ROWS - len(union_rows),
            "total_nonzeros": total_nonzeros,
            "support_minimum": min(len(item["rows"]) for item in semantics),
            "support_maximum": max(len(item["rows"]) for item in semantics),
            "ordered_sparse_stream_sha256": stream_digest,
            "union_row_indices_sha256": union_hash,
            "integer_matrix_shape": list(matrix.shape),
            "integer_matrix_sha256": matrix_hash,
            "lambda_row_sha256": lambda_hash,
            "all_867_s0_columns_match_g0056_semantic_hashes": True,
            "all_1288_pivot_columns_match_g0061_semantic_hashes": True,
        },
        "displayed_relations": {
            "relation_count": len(relations),
            "relations_sha256": canonical_sha256(relations),
            "complete_rows_per_relation": EXPECTED_ROWS,
            "all_exact_hinge_residuals_zero": True,
            "all_exact_lambda_residuals_zero": True,
            "lambda_residuals_sha256": canonical_sha256(lambda_residuals),
            "replayed_sparse_nonzero_terms": replayed_terms,
            "maximum_observed_absolute_intermediate": maximum_intermediate,
            "maximum_proved_absolute_residual_bound": maximum_relation_absolute_bound,
            "signed_int64_replay_proved_overflow_safe": True,
            "distinct_free_coordinates": distinguished,
            "free_coordinate_triangular_independence": True,
            "rational_and_cleared_integer_coefficients_match": True,
            "all_denominator_lcms_are_exact": True,
        },
        "exact_rank_certificate": {
            "pivot_columns_sha256": pivot_columns_hash,
            "pivot_complete_rows_sha256": pivot_rows_hash,
            "both_g0059_prime_manifests_match_pivot_arrays_and_hashes": True,
            "minor_shape": list(minor.shape),
            "minor_int64_row_major_sha256": minor_hash,
            "minor_determinant_residues": determinant_results,
            "rank_Q_lower_bound_from_nonzero_integer_minor": EXPECTED_RANK,
            "rank_Q_upper_bound_from_70_independent_exact_kernel_vectors": EXPECTED_RANK,
            "exact_rank_Q": exact_rank,
            "exact_nullity_Q": exact_nullity,
        },
        "producer_scientific_hash": {
            "recomputed_sha256": scientific_hash,
            "matches_report": True,
            "runtime_only_mutation_ignored": True,
            "scientific_rank_mutation_detected": True,
        },
        "controls": {
            "small_semantic_controls": self_tests,
            "dropped_universe_row_hash_mutation_detected": True,
            "coefficient_plus_one_mutation": {
                "rejected": True,
                "relation_index": 0,
                "support_local_index": 0,
                "first_nonzero_complete_row": mutant_complete_row,
                "first_nonzero_direction": list(universe[mutant_complete_row]),
                "residual_value": int(mutant_residual[mutant_local_row]),
            },
            "lambda_plus_one_mutation": {
                "rejected": True,
                "residual_value": lambda_mutant_residual,
            },
            "duplicate_minor_row_mutation": {
                "prime": PRIMES[0],
                "determinant": duplicate_row_determinant,
                "rejected": True,
            },
        },
        "claim_boundary": [
            "This certifies only the frozen 1,358-column S1 integer hinge matrix on the complete 99,858-row degree-four primitive universe.",
            "It does not include sequence 92,489, the 328 MAX10-induced columns, the remaining proper mass-four atoms, higher masses, arbitrary weights, or nonsymmetric models.",
            "It is not an unrestricted two-hidden-layer lower bound or a settlement of MAX11.",
        ],
        "caveats": [
            "The same OpenAI model lineage limits this audit to T1; it is not T2 review.",
            "The raw G-0038 descriptor stream is hash-bound by G-0050 but is untracked at producer commit 04ff8cf in the observed worktree, so a clone of the commit alone cannot replay low-mass descriptor selection.",
            "This audit reconstructs semantics independently of G-0061/G-0057 execution, but it uses their published wire-format hashes for byte-for-byte comparison and therefore does not claim method-disjoint T3 independence.",
        ],
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "workers": workers,
        },
        "timing": {
            "universe_seconds": universe_seconds,
            "semantic_seconds": semantic_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
    }
    deterministic = deepcopy(output)
    deterministic.pop("environment")
    deterministic.pop("timing")
    output["audit_scientific_payload_sha256"] = canonical_sha256(deterministic)
    return output


def write_json_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as destination:
        destination.write(canonical_bytes(value))
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument(
        "--output", type=Path, default=HERE / "audit_report_v1.json"
    )
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.self_test:
        print(json.dumps({"result": "SELF_TEST_PASS", **run_self_tests()}, sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(HERE.resolve())
    except ValueError as error:
        raise SystemExit("output must stay inside artifacts/cleanroom/G-0061") from error
    report = run(args.workers)
    write_json_atomic(output, report)
    print(
        json.dumps(
            {
                "result": report["result"],
                "output": str(output),
                "audit_scientific_payload_sha256": report[
                    "audit_scientific_payload_sha256"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
