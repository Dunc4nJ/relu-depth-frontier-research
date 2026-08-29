#!/usr/bin/env python3
"""Exact S0 rank gate for all 1,465 full-core signed-mass-4 atoms.

The program independently regenerates every selected hinge column against the
complete 99,858-direction degree-four universe, freezes the exact union of
nonzero rows, and performs a second full semantic pass proving that every
selected column is zero off that union.  It then computes two-prime column
rank and augmented-row rank.  A deterministic CountSketch may certify full
column rank because left multiplication cannot increase rank; any deficiency
falls back to the complete union-restricted dense matrix.

No-claim: a no-circuit result concerns only the 1,465 full mass-four seeds.
It says nothing about the 132,728 proper mass-four columns, mass five, or
unrestricted two-hidden-layer networks.  A modular circuit is only a lifting
candidate until exact-Q reconstruction and functional replay.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import combinations_with_replacement
import json
from math import gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from types import ModuleType
from typing import Any, Iterator, Sequence

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
THEOREM_SCRIPT = ROOT / "artifacts/math/G-0047/induction_span_obstruction.py"
THEOREM_REPORT = ROOT / "artifacts/math/G-0047/induction_span_obstruction_v1.json.gz"
SIGNED_STREAM = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"

EXPECTED_THEOREM_SCRIPT_SHA256 = (
    "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d"
)
EXPECTED_THEOREM_REPORT_SHA256 = (
    "47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a"
)
EXPECTED_SIGNED_STREAM_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_G0052_REPORT_SHA256 = (
    "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37"
)
EXPECTED_DESCRIPTOR_SHA256 = (
    "c0e49bda15e0ed17b821ba5a20bc0088a4aeab9ba5ab36da2ed63ac30843053e"
)
EXPECTED_UNIVERSE_SHA256 = (
    "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
)
EXPECTED_ROWS = 99_858
EXPECTED_COLUMNS = 1_465
EXPECTED_UNION_ROWS = 42_457
EXPECTED_TOTAL_NONZEROS = 12_331_131
EXPECTED_SEQUENCE_FIRST = 136_039
EXPECTED_SEQUENCE_LAST = 137_503
EXPECTED_LAMBDA_GCD = 79_833_600
EXPECTED_LAMBDA_HISTOGRAM = {
    -479_001_600: 5,
    -399_168_000: 27,
    -319_334_400: 9,
    -239_500_800: 96,
    -159_667_200: 99,
    -79_833_600: 86,
    0: 354,
    79_833_600: 128,
    159_667_200: 162,
    239_500_800: 154,
    319_334_400: 1,
    399_168_000: 275,
    798_336_000: 69,
}
PRIMES = (1_000_003, 1_000_033)
SCHEMA = "max11-g0054-s0-union-rank-gate-v1"
DEFAULT_OUTPUT = HERE / "s0_union_rank_gate_v1.json.gz"

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

THEOREM: Any = None
ROW_INDEX: dict[Direction, int] = {}


class GateError(RuntimeError):
    """Fail-closed semantic or resource error."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def file_bindings() -> dict[str, str]:
    observed = {
        "g0047_theorem_script_sha256": sha256_path(THEOREM_SCRIPT),
        "g0047_theorem_report_sha256": sha256_path(THEOREM_REPORT),
        "g0038_signed_stream_sha256": sha256_path(SIGNED_STREAM),
        "g0052_cross_check_report_sha256": sha256_path(G0052_REPORT),
    }
    expected = {
        "g0047_theorem_script_sha256": EXPECTED_THEOREM_SCRIPT_SHA256,
        "g0047_theorem_report_sha256": EXPECTED_THEOREM_REPORT_SHA256,
        "g0038_signed_stream_sha256": EXPECTED_SIGNED_STREAM_SHA256,
        "g0052_cross_check_report_sha256": EXPECTED_G0052_REPORT_SHA256,
    }
    if observed != expected:
        raise GateError(f"input binding drift: observed={observed}, expected={expected}")
    return observed


def load_theorem(module_name: str = "g0054_theorem") -> ModuleType:
    if sha256_path(THEOREM_SCRIPT) != EXPECTED_THEOREM_SCRIPT_SHA256:
        raise GateError("G-0047 theorem script drift")
    if sha256_path(THEOREM_REPORT) != EXPECTED_THEOREM_REPORT_SHA256:
        raise GateError("G-0047 theorem report drift")
    spec = importlib.util.spec_from_file_location(module_name, THEOREM_SCRIPT)
    if spec is None or spec.loader is None:
        raise GateError("cannot import frozen G-0047 semantics")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if sha256_path(module.SIGNED_STREAM) != EXPECTED_SIGNED_STREAM_SHA256:
        raise GateError("G-0047 module does not bind the frozen G-0038 stream")
    return module


def weak_compositions(
    total: int, parts: int, prefix: Direction = ()
) -> Iterator[Direction]:
    if parts == 1:
        yield prefix + (total,)
        return
    for first in range(total + 1):
        yield from weak_compositions(total - first, parts - 1, prefix + (first,))


def direction_universe(n: int = 11, degree: int = 4) -> tuple[Direction, ...]:
    compositions = tuple(weak_compositions(degree, n))
    directions: set[Direction] = set()
    for left, right in combinations_with_replacement(compositions, 2):
        if left == right:
            continue
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        directions.add(tuple(value // divisor for value in direction))
    result = tuple(sorted(directions))
    if (n, degree) == (11, 4) and len(result) != EXPECTED_ROWS:
        raise GateError(f"degree-four row census drift: {len(result)}")
    return result


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


def read_records() -> tuple[dict[str, object], list[dict[str, object]], str]:
    records = []
    mass4_count = 0
    with gzip.open(SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise GateError("G-0038 stream header missing")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            mass4_count += 1
            if int(record["active_vertices"]) == 11:
                records.append(record)
    if mass4_count != 134_193 or len(records) != EXPECTED_COLUMNS:
        raise GateError(f"mass-four/full census drift: {mass4_count}/{len(records)}")
    sequences = [int(record["sequence"]) for record in records]
    if sequences != list(range(EXPECTED_SEQUENCE_FIRST, EXPECTED_SEQUENCE_LAST + 1)):
        raise GateError("full-seed sequence interval drift")
    descriptors = [descriptor(record) for record in records]
    descriptor_hash = canonical_sha256(descriptors)
    if descriptor_hash != EXPECTED_DESCRIPTOR_SHA256:
        raise GateError(
            f"full-seed descriptor drift: {descriptor_hash} != {EXPECTED_DESCRIPTOR_SHA256}"
        )
    return header, records, descriptor_hash


def init_worker() -> None:
    global THEOREM
    THEOREM = load_theorem(f"g0054_worker_{os.getpid()}")
    if not ROW_INDEX:
        raise GateError("worker did not inherit the complete row dictionary")


def semantic_column_hash(
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


def semantic_worker(record: dict[str, object]) -> dict[str, object]:
    pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    used = {vertex for branch in pair for edge in branch for vertex in edge}
    if used != set(range(11)):
        raise GateError(f"non-full signed core at sequence {record['sequence']}")
    counter = THEOREM.permutation_t_counter_dp(pair, 11)
    _linear, hinge_counter = THEOREM.primitive_normal_form(counter, 11)
    sparse = []
    escaped = []
    for direction, raw_value in hinge_counter.items():
        value = int(raw_value)
        if not value:
            continue
        row = ROW_INDEX.get(tuple(map(int, direction)))
        if row is None:
            escaped.append(tuple(map(int, direction)))
        else:
            sparse.append((row, value))
    if escaped:
        raise GateError(
            f"hinge escaped complete universe at sequence {record['sequence']}: "
            f"{min(escaped)}"
        )
    sparse.sort()
    if len({row for row, _value in sparse}) != len(sparse):
        raise GateError(f"duplicate hinge row at sequence {record['sequence']}")
    rows = np.fromiter((row for row, _value in sparse), dtype=np.uint32)
    values = np.fromiter((value for _row, value in sparse), dtype=np.int64)
    binary = THEOREM.binary_chamber_vector_from_full_symmetry(pair, 11)
    invariant = int(THEOREM.dot(THEOREM.alternating_invariant(11), binary))
    sequence = int(record["sequence"])
    return {
        "sequence": sequence,
        "rows": rows,
        "values": values,
        "invariant": invariant,
        "semantic_sha256": semantic_column_hash(sequence, rows, values, invariant),
    }


def generate_pass(
    records: list[dict[str, object]], workers: int, label: str
) -> list[dict[str, object]]:
    results: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_worker,
        maxtasksperchild=32,
    ) as pool:
        for result in pool.imap_unordered(semantic_worker, records, chunksize=1):
            results.append(result)
            if len(results) % 50 == 0 or len(results) == len(records):
                print(
                    f"G0054_{label} columns={len(results)}/{len(records)}",
                    file=sys.stderr,
                    flush=True,
                )
    results.sort(key=lambda item: int(item["sequence"]))
    expected_sequences = list(range(EXPECTED_SEQUENCE_FIRST, EXPECTED_SEQUENCE_LAST + 1))
    if [int(item["sequence"]) for item in results] != expected_sequences:
        raise GateError(f"{label} result sequence drift")
    return results


def sparse_stream_hash(results: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0054-ordered-full-row-column-stream-v1\n")
    for result in results:
        digest.update(bytes.fromhex(str(result["semantic_sha256"])))
    return digest.hexdigest()


def hash_dense_matrix(matrix: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(
        f"int64-little-row-major;shape={matrix.shape[0]}x{matrix.shape[1]}\n".encode()
    )
    for start in range(0, matrix.shape[0], 256):
        block = matrix[start : start + 256]
        digest.update(block.astype("<i8", copy=False).tobytes(order="C"))
    return digest.hexdigest()


def hash_modular_matrix(matrix: np.ndarray, prime: int, label: str) -> str:
    reduced = np.remainder(matrix, prime).astype("<u4", copy=False)
    digest = hashlib.sha256()
    digest.update(
        f"{label};uint32-little-row-major;shape={matrix.shape[0]}x{matrix.shape[1]};"
        f"prime={prime}\n".encode()
    )
    digest.update(reduced.tobytes(order="C"))
    return digest.hexdigest()


def build_union_matrix(
    universe: tuple[Direction, ...], results: list[dict[str, object]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    union_mask = np.zeros(len(universe), dtype=np.bool_)
    total_nonzeros = 0
    support_sizes = []
    invariants = []
    for result in results:
        rows = result["rows"]
        values = result["values"]
        if not isinstance(rows, np.ndarray) or not isinstance(values, np.ndarray):
            raise GateError("semantic result lost typed sparse arrays")
        if len(rows) != len(values) or np.any(values == 0):
            raise GateError("malformed sparse semantic column")
        union_mask[rows] = True
        total_nonzeros += len(rows)
        support_sizes.append(len(rows))
        invariants.append(int(result["invariant"]))
    union_rows = np.flatnonzero(union_mask).astype(np.uint32)
    if len(union_rows) != EXPECTED_UNION_ROWS:
        raise GateError(f"nonzero-row union drift: {len(union_rows)}")
    if total_nonzeros != EXPECTED_TOTAL_NONZEROS:
        raise GateError(f"total sparse nonzero drift: {total_nonzeros}")
    if (min(support_sizes), statistics.median(support_sizes), max(support_sizes)) != (
        714,
        8_155,
        21_854,
    ):
        raise GateError(
            "per-column support summary drift: "
            f"{min(support_sizes)}/{statistics.median(support_sizes)}/{max(support_sizes)}"
        )
    compressed_index = np.full(len(universe), -1, dtype=np.int32)
    compressed_index[union_rows] = np.arange(len(union_rows), dtype=np.int32)
    matrix = np.zeros((len(union_rows), len(results)), dtype=np.int64)
    for column, result in enumerate(results):
        rows = result["rows"]
        values = result["values"]
        local = compressed_index[rows]
        if np.any(local < 0):
            raise GateError(f"column {column} has an entry outside its frozen union")
        matrix[local, column] = values
    encoded_nonzeros = int(np.count_nonzero(matrix))
    if encoded_nonzeros != total_nonzeros:
        raise GateError(
            f"union matrix lost or duplicated entries: {encoded_nonzeros}/{total_nonzeros}"
        )
    lambda_row = np.array(invariants, dtype=np.int64)
    invariant_histogram = Counter(invariants)
    if invariant_histogram != Counter(EXPECTED_LAMBDA_HISTOGRAM):
        raise GateError(f"lambda histogram drift: {dict(invariant_histogram)}")
    nonzero_gcd = 0
    for value in invariants:
        nonzero_gcd = gcd(nonzero_gcd, abs(value))
    if nonzero_gcd != EXPECTED_LAMBDA_GCD:
        raise GateError(f"lambda gcd drift: {nonzero_gcd}")
    union_directions = [list(universe[int(row)]) for row in union_rows]
    metadata = {
        "union_row_indices_sha256": hashlib.sha256(
            union_rows.astype("<u4", copy=False).tobytes(order="C")
        ).hexdigest(),
        "union_directions_sha256": canonical_sha256(union_directions),
        "union_lex_first_direction": union_directions[0],
        "union_lex_last_direction": union_directions[-1],
        "total_nonzeros": total_nonzeros,
        "support_minimum": min(support_sizes),
        "support_median": statistics.median(support_sizes),
        "support_maximum": max(support_sizes),
        "support_mean": str(Fraction(sum(support_sizes), len(support_sizes))),
        "lambda_histogram": {
            str(key): value for key, value in sorted(invariant_histogram.items())
        },
        "lambda_nonzero_count": sum(value != 0 for value in invariants),
        "lambda_zero_count": sum(value == 0 for value in invariants),
        "lambda_nonzero_gcd": nonzero_gcd,
        "matrix_sha256": hash_dense_matrix(matrix),
    }
    return union_rows, matrix, lambda_row, metadata


def replay_off_union(
    replay: list[dict[str, object]],
    first: list[dict[str, object]],
    union_mask: np.ndarray,
) -> dict[str, object]:
    mismatches = []
    escaped_columns = []
    replay_nonzeros = 0
    for index, (observed, expected) in enumerate(zip(replay, first, strict=True)):
        if observed["semantic_sha256"] != expected["semantic_sha256"]:
            mismatches.append(index)
        rows = observed["rows"]
        if np.any(~union_mask[rows]):
            escaped_columns.append(index)
        replay_nonzeros += len(rows)
    if mismatches or escaped_columns or replay_nonzeros != EXPECTED_TOTAL_NONZEROS:
        raise GateError(
            "complete semantic replay failed: "
            f"mismatches={mismatches[:3]}, escaped={escaped_columns[:3]}, "
            f"nonzeros={replay_nonzeros}"
        )
    omitted_rows = int(np.count_nonzero(~union_mask))
    return {
        "second_pass_ordered_sparse_stream_sha256": sparse_stream_hash(replay),
        "all_column_semantic_hashes_match_first_pass": True,
        "every_replayed_hinge_belongs_to_frozen_union": True,
        "omitted_complete_rows": omitted_rows,
        "verified_zero_off_union_matrix_entries": omitted_rows * EXPECTED_COLUMNS,
        "replayed_nonzeros": replay_nonzeros,
    }


def sketch_map(
    full_row_indices: np.ndarray, buckets: int, prime: int, seed: str
) -> tuple[np.ndarray, np.ndarray, str]:
    bucket_map = np.empty(len(full_row_indices), dtype=np.int32)
    weights = np.empty(len(full_row_indices), dtype=np.int64)
    digest = hashlib.sha256()
    digest.update(
        f"max11-g0054-countsketch-v1;seed={seed};buckets={buckets};prime={prime}\n".encode()
    )
    for local, raw_row in enumerate(full_row_indices):
        full_row = int(raw_row)
        payload = f"{seed}|{full_row}".encode("ascii")
        hashed = hashlib.sha256(payload).digest()
        bucket = int.from_bytes(hashed[:8], "little") % buckets
        weight = int.from_bytes(hashed[8:16], "little") % (prime - 1) + 1
        bucket_map[local] = bucket
        weights[local] = weight
        digest.update(full_row.to_bytes(4, "little"))
        digest.update(bucket.to_bytes(4, "little"))
        digest.update(weight.to_bytes(8, "little"))
    return bucket_map, weights, digest.hexdigest()


def build_sketch(
    matrix: np.ndarray,
    union_rows: np.ndarray,
    prime: int,
    buckets: int,
    seed: str,
) -> tuple[np.ndarray, dict[str, object]]:
    bucket_map, weights, map_hash = sketch_map(union_rows, buckets, prime, seed)
    sketch = np.zeros((buckets, matrix.shape[1]), dtype=np.int64)
    max_abs_entry = int(np.max(np.abs(matrix)))
    int64_limit = (1 << 63) - 1
    maximum_rows_per_bucket_in_chunk = 0
    maximum_accumulator_bound = 0
    for row_start in range(0, matrix.shape[0], 256):
        row_stop = min(row_start + 256, matrix.shape[0])
        counts = np.bincount(bucket_map[row_start:row_stop], minlength=buckets)
        rows_per_bucket = int(counts.max())
        bound = (prime - 1) + max_abs_entry * (prime - 1) * rows_per_bucket
        maximum_rows_per_bucket_in_chunk = max(
            maximum_rows_per_bucket_in_chunk, rows_per_bucket
        )
        maximum_accumulator_bound = max(maximum_accumulator_bound, bound)
    if maximum_accumulator_bound > int64_limit:
        raise GateError(
            "CountSketch int64 overflow bound failed: "
            f"{maximum_accumulator_bound} > {int64_limit}"
        )
    for row_start in range(0, matrix.shape[0], 256):
        row_stop = min(row_start + 256, matrix.shape[0])
        affected_buckets = bucket_map[row_start:row_stop]
        for local_row in range(row_start, row_stop):
            bucket = int(bucket_map[local_row])
            sketch[bucket] += matrix[local_row] * weights[local_row]
        sketch[np.unique(affected_buckets)] %= prime
    sketch %= prime
    sketch_hash = hashlib.sha256()
    sketch_hash.update(
        f"uint32-little-row-major;shape={buckets}x{matrix.shape[1]};prime={prime}\n".encode()
    )
    sketch_hash.update(sketch.astype("<u4", copy=False).tobytes(order="C"))
    return sketch, {
        "buckets": buckets,
        "seed": seed,
        "map_definition": (
            "For each complete lex-row index r, SHA256(ASCII(seed+'|'+str(r))); "
            "bucket=little_u64(bytes[0:8]) mod buckets; "
            "weight=1+(little_u64(bytes[8:16]) mod (prime-1))."
        ),
        "map_sha256": map_hash,
        "matrix_sha256": sketch_hash.hexdigest(),
        "int64_overflow_control": {
            "maximum_absolute_integer_matrix_entry": max_abs_entry,
            "maximum_field_weight": prime - 1,
            "reduction_chunk_rows": 256,
            "maximum_rows_in_one_bucket_within_a_chunk": (
                maximum_rows_per_bucket_in_chunk
            ),
            "worst_case_absolute_accumulator_bound_including_prior_residue": (
                maximum_accumulator_bound
            ),
            "signed_int64_maximum": int64_limit,
            "strictly_within_signed_int64": True,
        },
    }


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.remainder(matrix, prime).astype(np.int64, copy=False)
    flat = reduced.ravel(order="C").tolist()
    value = nmod_mat(matrix.shape[0], matrix.shape[1], flat, prime)
    del flat, reduced
    return value


def rank_array(matrix: np.ndarray, prime: int) -> int:
    value = to_nmod(matrix, prime)
    rank = int(value.rank())
    del value
    return rank


def pivot_columns_from_rref(rref_matrix: nmod_mat, rank: int) -> list[int]:
    pivots = []
    for row in range(rank):
        pivot = next(
            (
                column
                for column in range(rref_matrix.ncols())
                if int(rref_matrix[row, column])
            ),
            None,
        )
        if pivot is None:
            raise GateError(f"RREF row {row} lacks a pivot")
        pivots.append(pivot)
    if len(set(pivots)) != rank:
        raise GateError("RREF pivot duplication")
    return pivots


def nonzero_minor_certificate(
    matrix: np.ndarray,
    prime: int,
    rank: int,
    row_labels: np.ndarray,
    namespace: str,
) -> dict[str, object]:
    if len(row_labels) != matrix.shape[0]:
        raise GateError("rank-certificate row-label length mismatch")
    field = to_nmod(matrix, prime)
    transpose_rref, transpose_rank = field.transpose().rref()
    if int(transpose_rank) != rank:
        raise GateError(
            f"rank-certificate transpose rank drift: {transpose_rank}/{rank}"
        )
    pivot_local_rows = pivot_columns_from_rref(transpose_rref, rank)
    if rank == matrix.shape[1]:
        pivot_columns = list(range(matrix.shape[1]))
    else:
        row_rref, row_rank = field.rref()
        if int(row_rank) != rank:
            raise GateError(f"rank-certificate row rank drift: {row_rank}/{rank}")
        pivot_columns = pivot_columns_from_rref(row_rref, rank)
    minor = matrix[np.ix_(pivot_local_rows, pivot_columns)]
    minor_field = to_nmod(minor, prime)
    determinant = int(minor_field.det()) % prime
    if not determinant:
        raise GateError("selected rank-certificate minor has zero determinant")
    labeled_rows = [int(row_labels[index]) for index in pivot_local_rows]
    return {
        "kind": "explicit_nonzero_modular_minor",
        "row_namespace": namespace,
        "rank": rank,
        "pivot_local_rows": pivot_local_rows,
        "pivot_labeled_rows": labeled_rows,
        "pivot_labeled_rows_sha256": canonical_sha256(labeled_rows),
        "pivot_columns": pivot_columns,
        "pivot_columns_sha256": canonical_sha256(pivot_columns),
        "minor_shape": [rank, rank],
        "minor_matrix_sha256": hash_modular_matrix(
            minor, prime, "max11-g0054-rank-minor-v1"
        ),
        "minor_determinant_mod_prime": determinant,
        "minor_determinant_nonzero": True,
    }


def rank_deficiency_upper_certificate(
    matrix: np.ndarray,
    field_matrix: nmod_mat,
    prime: int,
    rank: int,
) -> dict[str, object]:
    kernel, nullity = field_matrix.nullspace()
    nullity = int(nullity)
    expected_nullity = matrix.shape[1] - rank
    if nullity != expected_nullity:
        raise GateError(f"nullity drift: {nullity}/{expected_nullity}")
    coefficient_rows = [
        [int(kernel[row, column]) for column in range(nullity)]
        for row in range(matrix.shape[1])
    ]
    basis_field = nmod_mat(matrix.shape[1], nullity, sum(coefficient_rows, []), prime)
    residual = field_matrix * basis_field
    if residual != nmod_mat(matrix.shape[0], nullity, prime):
        raise GateError("explicit nullspace basis did not replay to zero")
    basis_columns = []
    for column in range(nullity):
        support = [
            row for row in range(matrix.shape[1]) if coefficient_rows[row][column]
        ]
        basis_columns.append(
            {
                "support_zero_based_columns": support,
                "coefficients": [coefficient_rows[row][column] for row in support],
            }
        )
    return {
        "kind": "explicit_replayed_modular_nullspace_basis",
        "nullity": nullity,
        "rank_upper_bound": matrix.shape[1] - nullity,
        "basis_columns": basis_columns,
        "basis_columns_sha256": canonical_sha256(basis_columns),
        "complete_union_matrix_times_basis_is_zero": True,
    }


def mutation_controls(
    sketch: np.ndarray, lambda_row: np.ndarray, prime: int, actual_rank: int
) -> dict[str, object]:
    if actual_rank != EXPECTED_COLUMNS:
        return {"executed": False, "reason": "requires full-column-rank subject"}
    duplicate = np.column_stack((sketch, sketch[:, 0]))
    same_lambda = np.concatenate((lambda_row, [lambda_row[0]]))
    changed_lambda = np.concatenate((lambda_row, [lambda_row[0] + 1]))
    duplicate_rank = rank_array(duplicate, prime)
    same_augmented_rank = rank_array(np.vstack((duplicate, same_lambda)), prime)
    changed_augmented_rank = rank_array(
        np.vstack((duplicate, changed_lambda)), prime
    )
    if (
        duplicate_rank != EXPECTED_COLUMNS
        or same_augmented_rank != EXPECTED_COLUMNS
        or changed_augmented_rank != EXPECTED_COLUMNS + 1
    ):
        raise GateError(
            "duplicate/lambda mutation control failed: "
            f"{duplicate_rank}/{same_augmented_rank}/{changed_augmented_rank}"
        )
    return {
        "executed": True,
        "duplicate_first_column_rank": duplicate_rank,
        "duplicate_with_same_lambda_augmented_rank": same_augmented_rank,
        "duplicate_with_lambda_plus_one_augmented_rank": changed_augmented_rank,
        "lambda_plus_one_mutant_detected_as_rank_gain": True,
    }


def extract_and_replay_witness(
    field_matrix: nmod_mat,
    first_pass: list[dict[str, object]],
    lambda_row: np.ndarray,
    prime: int,
) -> dict[str, object]:
    kernel, nullity = field_matrix.nullspace()
    nullity = int(nullity)
    if nullity < 1:
        raise GateError("rank gain claimed but complete hinge nullspace is zero")
    chosen = None
    for basis_column in range(nullity):
        coefficients = np.array(
            [int(kernel[row, basis_column]) for row in range(EXPECTED_COLUMNS)],
            dtype=np.int64,
        )
        pairing = int(
            sum(
                int(lambda_row[index] % prime) * int(coefficients[index])
                for index in range(EXPECTED_COLUMNS)
            )
            % prime
        )
        if pairing:
            scale = pow(pairing, -1, prime)
            chosen = np.remainder(coefficients * scale, prime).astype(np.int64)
            break
    if chosen is None:
        raise GateError("augmented rank gain lacks a nonzero-lambda null vector")
    residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
    for coefficient, result in zip(chosen, first_pass, strict=True):
        if not coefficient:
            continue
        rows = result["rows"]
        values = np.remainder(result["values"], prime)
        residual[rows] = np.remainder(
            residual[rows] + coefficient * values,
            prime,
        )
    bad = np.flatnonzero(residual)
    if len(bad):
        raise GateError(f"full 99,858-row witness replay failed at row {int(bad[0])}")
    pairing = sum(
        int(lambda_row[index] % prime) * int(chosen[index])
        for index in range(EXPECTED_COLUMNS)
    ) % prime
    if pairing != 1:
        raise GateError(f"normalized witness lambda pairing drift: {pairing}")
    support = np.flatnonzero(chosen)
    return {
        "normalized_lambda_pairing": pairing,
        "full_99858_row_replay_zero": True,
        "nonzero_coefficient_count": int(len(support)),
        "support_zero_based_columns": [int(index) for index in support],
        "coefficients": [int(chosen[index]) for index in support],
    }


def modular_gate(
    matrix: np.ndarray,
    union_rows: np.ndarray,
    lambda_row: np.ndarray,
    first_pass: list[dict[str, object]],
    prime: int,
    sketch_buckets: int,
) -> dict[str, object]:
    started = time.perf_counter()
    seed = f"g0054-s0-p{prime}-primary"
    sketch, sketch_metadata = build_sketch(
        matrix, union_rows, prime, sketch_buckets, seed
    )
    sketch_rank_started = time.perf_counter()
    sketch_field = to_nmod(sketch, prime)
    sketch_rank = int(sketch_field.rank())
    sketch_rank_seconds = time.perf_counter() - sketch_rank_started
    complete_field: nmod_mat | None = None
    if sketch_rank == EXPECTED_COLUMNS:
        complete_rank = EXPECTED_COLUMNS
        augmented_rank = EXPECTED_COLUMNS
        rank_method = (
            "deterministic complete-row CountSketch lower bound equals the column-count "
            "upper bound; left multiplication cannot increase rank"
        )
        complete_rank_seconds = 0.0
        lower_certificate = nonzero_minor_certificate(
            sketch,
            prime,
            complete_rank,
            np.arange(sketch.shape[0], dtype=np.uint32),
            "deterministic_countsketch_bucket",
        )
        upper_certificate = {
            "kind": "column_count_upper_bound",
            "rank_upper_bound": EXPECTED_COLUMNS,
        }
    else:
        dense_started = time.perf_counter()
        complete_field = to_nmod(matrix, prime)
        complete_rank = int(complete_field.rank())
        complete_rank_seconds = time.perf_counter() - dense_started
        if complete_rank == EXPECTED_COLUMNS:
            augmented_rank = EXPECTED_COLUMNS
        else:
            augmented_rank = rank_array(np.vstack((matrix, lambda_row)), prime)
        rank_method = "direct complete exact-union dense FLINT rank"
        lower_certificate = nonzero_minor_certificate(
            matrix,
            prime,
            complete_rank,
            union_rows,
            "complete_degree4_lex_row_index",
        )
        upper_certificate = (
            {
                "kind": "column_count_upper_bound",
                "rank_upper_bound": EXPECTED_COLUMNS,
            }
            if complete_rank == EXPECTED_COLUMNS
            else rank_deficiency_upper_certificate(
                matrix, complete_field, prime, complete_rank
            )
        )
    if not (complete_rank <= augmented_rank <= complete_rank + 1):
        raise GateError(f"invalid rank arithmetic mod {prime}")
    gain = augmented_rank - complete_rank
    witness = None
    if gain:
        if complete_field is None:
            complete_field = to_nmod(matrix, prime)
        witness = extract_and_replay_witness(
            complete_field, first_pass, lambda_row, prime
        )
    mutations = mutation_controls(sketch, lambda_row, prime, complete_rank)
    del sketch_field, complete_field, sketch
    return {
        "prime": prime,
        "complete_hinge_rank": complete_rank,
        "augmented_hinge_plus_lambda_rank": augmented_rank,
        "augmented_rank_gain": gain,
        "rank_method": rank_method,
        "rank_lower_certificate": lower_certificate,
        "rank_upper_certificate": upper_certificate,
        "sketch": {
            **sketch_metadata,
            "rank": sketch_rank,
            "rank_seconds": sketch_rank_seconds,
        },
        "direct_complete_rank_seconds": complete_rank_seconds,
        "witness": witness,
        "mutation_controls": mutations,
        "seconds": time.perf_counter() - started,
    }


def self_test() -> dict[str, object]:
    theorem = load_theorem("g0054_self_test_theorem")
    loop_pair: Pair = (((0, 0), (0, 1)), ((1, 1), (1, 2)))
    if theorem.permutation_t_counter_dp(
        loop_pair, 3
    ) != theorem.permutation_t_counter_bruteforce(loop_pair, 3):
        raise AssertionError("loop-sensitive DP/brute control failed")
    prime = PRIMES[0]
    full = np.array([[1, 0], [0, 1]], dtype=np.int64)
    if rank_array(full, prime) != 2 or rank_array(
        np.vstack((full, [1, 1])), prime
    ) != 2:
        raise AssertionError("full-rank negative control failed")
    minor_control = nonzero_minor_certificate(
        full,
        prime,
        2,
        np.arange(2, dtype=np.uint32),
        "self_test_row",
    )
    if not minor_control["minor_determinant_nonzero"]:
        raise AssertionError("explicit nonzero-minor certificate control failed")
    positive = np.array([[1, 1]], dtype=np.int64)
    positive_lambda = np.array([1, 0], dtype=np.int64)
    if rank_array(positive, prime) != 1 or rank_array(
        np.vstack((positive, positive_lambda)), prime
    ) != 2:
        raise AssertionError("planted rank-gain control failed")
    zero_lambda = np.array([1, 1], dtype=np.int64)
    if rank_array(np.vstack((positive, zero_lambda)), prime) != 1:
        raise AssertionError("zero-lambda dependency control failed")
    positive_field = to_nmod(positive, prime)
    upper_control = rank_deficiency_upper_certificate(
        positive, positive_field, prime, 1
    )
    if upper_control["rank_upper_bound"] != 1:
        raise AssertionError("explicit nullspace upper-certificate control failed")
    original = np.array([[1, 2], [3, 4]], dtype=np.int64)
    original_hash = hash_dense_matrix(original)
    mutant = original.copy()
    mutant[0, 0] += 1
    if hash_dense_matrix(mutant) == original_hash:
        raise AssertionError("matrix entry +1 hash mutation was not detected")
    return {
        "result": "PASS",
        "loop_sensitive_subset_DP_matches_direct_permutations": True,
        "full_column_rank_negative_control": True,
        "planted_nonzero_lambda_rank_gain_control": True,
        "planted_zero_lambda_dependency_control": True,
        "explicit_nonzero_minor_lower_certificate_control": True,
        "explicit_nullspace_upper_certificate_control": True,
        "matrix_entry_plus_one_hash_mutation_rejected": True,
    }


def memory_available_bytes() -> int:
    with Path("/proc/meminfo").open("r", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise GateError("cannot read MemAvailable")


def preflight() -> dict[str, object]:
    started = time.perf_counter()
    bindings = file_bindings()
    universe = direction_universe()
    universe_hash = canonical_sha256([list(direction) for direction in universe])
    if universe_hash != EXPECTED_UNIVERSE_SHA256:
        raise GateError(f"degree-four universe hash drift: {universe_hash}")
    _header, records, descriptor_hash = read_records()
    return {
        "result": "PASS",
        "bindings": bindings,
        "complete_rows": len(universe),
        "complete_row_universe_sha256": universe_hash,
        "selected_columns": len(records),
        "selected_descriptors_sha256": descriptor_hash,
        "expected_union_rows": EXPECTED_UNION_ROWS,
        "expected_total_nonzeros": EXPECTED_TOTAL_NONZEROS,
        "expected_union_dense_int64_bytes": (
            EXPECTED_UNION_ROWS * EXPECTED_COLUMNS * 8
        ),
        "memory_available_bytes": memory_available_bytes(),
        "seconds": time.perf_counter() - started,
    }


def run(workers: int, minimum_available_gib: float, sketch_buckets: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    ready = preflight()
    minimum_bytes = int(minimum_available_gib * (1 << 30))
    if memory_available_bytes() < minimum_bytes:
        raise GateError(
            f"available memory below guard: {memory_available_bytes()} < {minimum_bytes}"
        )
    universe_started = time.perf_counter()
    universe = direction_universe()
    universe_seconds = time.perf_counter() - universe_started
    universe_payload = [list(direction) for direction in universe]
    universe_hash = canonical_sha256(universe_payload)
    global ROW_INDEX
    ROW_INDEX = {direction: row for row, direction in enumerate(universe)}
    header, records, descriptor_hash = read_records()

    first_started = time.perf_counter()
    first = generate_pass(records, workers, "PASS1")
    first_seconds = time.perf_counter() - first_started
    first_stream_hash = sparse_stream_hash(first)
    union_rows, matrix, lambda_row, union_metadata = build_union_matrix(
        universe, first
    )
    union_mask = np.zeros(EXPECTED_ROWS, dtype=np.bool_)
    union_mask[union_rows] = True

    replay_started = time.perf_counter()
    replay = generate_pass(records, workers, "PASS2")
    replay_metadata = replay_off_union(replay, first, union_mask)
    replay_seconds = time.perf_counter() - replay_started
    if replay_metadata["second_pass_ordered_sparse_stream_sha256"] != first_stream_hash:
        raise GateError("first/second complete sparse stream hashes differ")
    del replay

    modular_results = [
        modular_gate(
            matrix,
            union_rows,
            lambda_row,
            first,
            prime,
            sketch_buckets,
        )
        for prime in PRIMES
    ]
    ranks = [int(item["complete_hinge_rank"]) for item in modular_results]
    gains = [int(item["augmented_rank_gain"]) for item in modular_results]
    if ranks == [EXPECTED_COLUMNS, EXPECTED_COLUMNS]:
        result = "S0_TWO_PRIME_FULL_COLUMN_RANK_NO_SEED_ONLY_CIRCUIT"
        exact_conclusion = (
            "The 1,465 full-core signed-mass-4 hinge columns are linearly independent over Q. "
            "Therefore no nonzero hinge-free rational combination exists using only these "
            "seeds, regardless of the lambda values."
        )
    elif gains == [1, 1] and all(item["witness"] for item in modular_results):
        result = "S0_TWO_PRIME_NONZERO_LAMBDA_CIRCUIT_REPLAYED_REQUIRES_Q_LIFT"
        exact_conclusion = None
    else:
        result = "S0_MIXED_MODULAR_OUTCOME_REQUIRES_REVIEW"
        exact_conclusion = None

    first_hash_mutant = matrix.copy()
    first_nonzero = np.argwhere(first_hash_mutant != 0)[0]
    mutant_row, mutant_column = map(int, first_nonzero)
    original_value = int(first_hash_mutant[mutant_row, mutant_column])
    first_hash_mutant[mutant_row, mutant_column] += 1
    mutant_hash = hash_dense_matrix(first_hash_mutant)
    del first_hash_mutant
    if mutant_hash == union_metadata["matrix_sha256"]:
        raise GateError("complete matrix entry +1 mutation did not change its hash")

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("G-0054 script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": result,
        "script_sha256": script_hash_before,
        "bindings": ready["bindings"],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
            "minimum_available_gib": minimum_available_gib,
            "sketch_buckets": sketch_buckets,
        },
        "controls": {
            **controls,
            "preflight": ready,
            "complete_second_semantic_pass": replay_metadata,
            "matrix_entry_plus_one_mutant": {
                "union_row": mutant_row,
                "column": mutant_column,
                "original_value": original_value,
                "mutated_value": original_value + 1,
                "original_matrix_sha256": union_metadata["matrix_sha256"],
                "mutant_matrix_sha256": mutant_hash,
                "rejected": True,
            },
        },
        "complete_degree4_row_universe": {
            "row_count": len(universe),
            "directions_sha256": universe_hash,
            "lex_first_direction": universe_payload[0],
            "lex_last_direction": universe_payload[-1],
        },
        "selected_s0_columns": {
            "count": len(records),
            "sequence_interval_inclusive": [
                EXPECTED_SEQUENCE_FIRST,
                EXPECTED_SEQUENCE_LAST,
            ],
            "descriptors_sha256": descriptor_hash,
            "ordered_full_row_sparse_stream_sha256": first_stream_hash,
        },
        "exact_nonzero_row_union": {
            "row_count": len(union_rows),
            "omitted_complete_rows": EXPECTED_ROWS - len(union_rows),
            **union_metadata,
            "matrix_shape": [matrix.shape[0], matrix.shape[1]],
            "matrix_encoding": "int64 little-endian row-major with declared shape header",
            "all_selected_columns_zero_off_union": True,
        },
        "modular_results": modular_results,
        "exact_bounded_conclusion": exact_conclusion,
        "mandatory_next_gate": (
            "If a replayed modular circuit exists, obtain common support across primes, lift "
            "over Q, replay all 99,858 integer hinge rows, and correct/verify the ordered-"
            "chamber linear part before any identity claim. If S0 is full rank, move only to "
            "the separately authorised S1 union with the frozen low-mass basis."
        ),
        "claim_boundary": (
            "This result concerns only rational combinations of the 1,465 frozen full-core "
            "signed-mass-4 hinge columns. A no-circuit result is not a mass-four-wide "
            "obstruction because 132,728 proper-core mass-four columns are omitted. It is not "
            "a mass-five result or an unrestricted two-hidden-layer lower bound."
        ),
        "timing": {
            "universe_seconds": universe_seconds,
            "first_semantic_pass_seconds": first_seconds,
            "second_semantic_pass_seconds": replay_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
        "source_header_census_report_sha256": header["census_report_sha256"],
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--minimum-available-gib", type=float, default=12.0)
    parser.add_argument("--sketch-buckets", type=int, default=4_096)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return
    if args.preflight_only:
        print(json.dumps(preflight(), sort_keys=True))
        return
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.minimum_available_gib <= 0:
        raise SystemExit("--minimum-available-gib must be positive")
    if args.sketch_buckets < EXPECTED_COLUMNS:
        raise SystemExit(f"--sketch-buckets must be at least {EXPECTED_COLUMNS}")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside the project") from error
    report = run(args.workers, args.minimum_available_gib, args.sketch_buckets)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
