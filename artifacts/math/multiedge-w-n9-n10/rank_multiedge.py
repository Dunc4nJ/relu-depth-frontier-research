#!/usr/bin/env python3
"""Exact finite-field ranks for cumulative signed-W multiplicity strata.

Columns are read from colgen's exact MCOLGEN1 stream and reduced modulo one
named prime into a python-flint nmod_mat.  W columns are reordered as

    max multiplicity <= 1, target, multiplicity 2, 3, ... , duplicate.

Putting the target immediately after the known simple-W prefix makes its
non-pivot status an explicit simple-family membership gate.  Because that
prefix already contains the target, all cumulative supersets do too.  The
last column deliberately duplicates one real W column and must be non-pivot.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct
import sys
import time
from typing import BinaryIO, Iterator

import flint


SCHEMA = "max11-gmp9-multiedge-rank-v1"
EXPECTED_SIMPLE_COUNT = {9: 6_197, 10: 7_203}
EXPECTED_SIMPLE_RANK = {9: 1_506, 10: 2_166}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def read_exact(handle: BinaryIO, size: int) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise EOFError(f"wanted {size} bytes, received {len(data)}")
    return data


def read_header(handle: BinaryIO) -> tuple[int, int, int, int]:
    if read_exact(handle, 8) != b"MCOLGEN1":
        raise ValueError("not an MCOLGEN1 stream")
    n, branch_edges = struct.unpack("<HH", read_exact(handle, 4))
    modulus, count = struct.unpack("<QQ", read_exact(handle, 16))
    return n, branch_edges, modulus, count


def read_columns(
    path: Path,
) -> Iterator[tuple[int, list[int], list[tuple[tuple[int, ...], int]]]]:
    with path.open("rb") as handle:
        n, _branch_edges, modulus, count = read_header(handle)
        if modulus != 0:
            raise ValueError("rank input must contain exact integer columns")
        direction_format = "<" + "h" * n
        for expected in range(count):
            (record_index,) = struct.unpack("<Q", read_exact(handle, 8))
            if record_index != expected:
                raise ValueError(
                    f"column sequence mismatch: {record_index} != {expected}"
                )
            linear = list(struct.unpack("<" + "q" * n, read_exact(handle, 8 * n)))
            (hinge_count,) = struct.unpack("<Q", read_exact(handle, 8))
            hinges = []
            for _ in range(hinge_count):
                direction = struct.unpack(direction_format, read_exact(handle, 2 * n))
                (coefficient,) = struct.unpack("<q", read_exact(handle, 8))
                hinges.append((direction, coefficient))
            yield record_index, linear, hinges
        if handle.read(1):
            raise ValueError("trailing bytes after MCOLGEN1 stream")


def load_universe(path: Path) -> dict[str, object]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        value = json.load(handle)
    if not value.get("loopless"):
        raise ValueError("universe is not loopless")
    return value


def recompute_max_multiplicity(record: dict[str, object]) -> int:
    edges = [tuple(edge) for edge in record["negative_edges"]]
    edges.extend(tuple(edge) for edge in record["positive_edges"])
    return max(Counter(edges).values(), default=0)


def scan_row_union(columns: Path, expected_count: int) -> tuple[list[tuple[int, ...]], int, int]:
    directions: set[tuple[int, ...]] = set()
    total_hinges = 0
    maximum_hinges = 0
    seen = 0
    for _record_index, _linear, hinges in read_columns(columns):
        directions.update(direction for direction, _coefficient in hinges)
        total_hinges += len(hinges)
        maximum_hinges = max(maximum_hinges, len(hinges))
        seen += 1
    if seen != expected_count:
        raise AssertionError(f"column denominator {seen} != {expected_count}")
    return sorted(directions), total_hinges, maximum_hinges


def pivot_columns(matrix: flint.nmod_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    search_from = 0
    for row in range(rank):
        while search_from < matrix.ncols() and matrix[row, search_from] == 0:
            search_from += 1
        if search_from == matrix.ncols():
            raise AssertionError("RREF row has no pivot")
        pivots.append(search_from)
        search_from += 1
    return pivots


def atomic_write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def rank(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    universe = load_universe(args.universe)
    n = int(universe["n"])
    branch_edges = int(universe["branch_edge_occurrences"])
    records = universe["records"]
    if n != args.n or branch_edges != 4:
        raise ValueError("universe dimensions do not match requested degree-four run")
    maxima = [recompute_max_multiplicity(record) for record in records]
    if any(int(record.get("max_multiplicity", maximum)) != maximum for record, maximum in zip(records, maxima)):
        raise AssertionError("stored maximum multiplicity disagrees with edge lists")
    counts = Counter(maxima)
    simple_indices = [index for index, maximum in enumerate(maxima) if maximum <= 1]
    expected_simple_count = EXPECTED_SIMPLE_COUNT[n]
    if len(simple_indices) != expected_simple_count:
        raise AssertionError(
            f"simple count {len(simple_indices)} != {expected_simple_count}"
        )
    maximum_value = max(maxima)
    grouped_indices = {
        maximum: [index for index, value in enumerate(maxima) if value == maximum]
        for maximum in range(2, maximum_value + 1)
    }
    ordered_indices = simple_indices + [
        index
        for maximum in range(2, maximum_value + 1)
        for index in grouped_indices[maximum]
    ]
    if sorted(ordered_indices) != list(range(len(records))):
        raise AssertionError("multiplicity ordering is not a permutation")
    position = {source: destination for destination, source in enumerate(ordered_indices)}

    with args.columns.open("rb") as handle:
        header_n, header_k, header_modulus, header_count = read_header(handle)
    if (header_n, header_k, header_modulus, header_count) != (
        n,
        branch_edges,
        0,
        len(records),
    ):
        raise ValueError("MCOLGEN1 header does not match universe")

    union_started = time.monotonic()
    directions, total_hinges, maximum_hinges = scan_row_union(
        args.columns, len(records)
    )
    union_seconds = time.monotonic() - union_started
    row_index = {direction: index for index, direction in enumerate(directions)}
    linear_offset = len(directions)
    row_count = linear_offset + n

    target_position = len(simple_indices)
    duplicate_position = len(records) + 1
    matrix_column_count = len(records) + 2
    matrix = flint.nmod_mat(row_count, matrix_column_count, args.prime)
    build_started = time.monotonic()
    duplicate_source = simple_indices[1]
    duplicate_source_position = position[duplicate_source]
    seen = 0
    for source, linear, hinges in read_columns(args.columns):
        destination = position[source]
        if destination >= target_position:
            destination += 1
        for coordinate, coefficient in enumerate(linear):
            residue = coefficient % args.prime
            if residue:
                matrix[linear_offset + coordinate, destination] = residue
        for direction, coefficient in hinges:
            residue = coefficient % args.prime
            if residue:
                matrix[row_index[direction], destination] = residue
        seen += 1
    if seen != len(records):
        raise AssertionError("did not load every exact column")
    matrix[linear_offset + n - 1, target_position] = 1
    for row in range(row_count):
        matrix[row, duplicate_position] = matrix[row, duplicate_source_position]
    build_seconds = time.monotonic() - build_started

    rref_started = time.monotonic()
    reduced, augmented_duplicate_rank = matrix.rref()
    rref_seconds = time.monotonic() - rref_started
    pivots = pivot_columns(reduced, augmented_duplicate_rank)
    del matrix

    if target_position in pivots:
        raise AssertionError("MAX target is not in the simple-W prefix")
    if duplicate_position in pivots:
        raise AssertionError("planted duplicate incorrectly increased rank")
    simple_rank = sum(pivot < target_position for pivot in pivots)
    if simple_rank != EXPECTED_SIMPLE_RANK[n]:
        raise AssertionError(
            f"simple-W rank {simple_rank} != {EXPECTED_SIMPLE_RANK[n]}"
        )

    steps: list[dict[str, object]] = []
    cumulative_count = len(simple_indices)
    cutoff = target_position + 1
    previous_rank = 0
    simple_entry_rank = sum(pivot < cutoff for pivot in pivots)
    steps.append(
        {
            "maximum_multiplicity_leq": 1,
            "added_stratum_count": len(simple_indices),
            "cumulative_column_count": cumulative_count,
            "rank": simple_entry_rank,
            "augmented_rank": simple_entry_rank,
            "max_member": True,
            "rank_growth": simple_entry_rank - previous_rank,
        }
    )
    previous_rank = simple_entry_rank
    for maximum in range(2, maximum_value + 1):
        added = len(grouped_indices[maximum])
        cumulative_count += added
        cutoff += added
        current_rank = sum(pivot < cutoff for pivot in pivots)
        steps.append(
            {
                "maximum_multiplicity_leq": maximum,
                "added_stratum_count": added,
                "cumulative_column_count": cumulative_count,
                "rank": current_rank,
                "augmented_rank": current_rank,
                "max_member": True,
                "rank_growth": current_rank - previous_rank,
            }
        )
        previous_rank = current_rank

    full_rank_without_duplicate = sum(pivot < duplicate_position for pivot in pivots)
    if full_rank_without_duplicate != augmented_duplicate_rank:
        raise AssertionError("duplicate rank accounting mismatch")
    if steps[-1]["rank"] != full_rank_without_duplicate:
        raise AssertionError("cumulative rank table does not reach full rank")
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "n": n,
        "branch_edge_occurrences": branch_edges,
        "prime": args.prime,
        "universe": str(args.universe),
        "universe_sha256": sha256_path(args.universe),
        "exact_columns": str(args.columns),
        "exact_columns_sha256": sha256_path(args.columns),
        "universe_column_denominator": len(records),
        "max_multiplicity_counts": dict(sorted(counts.items())),
        "hinge_row_denominator": len(directions),
        "linear_row_denominator": n,
        "normal_form_row_denominator": row_count,
        "hinge_nonzero_occurrence_denominator": total_hinges,
        "maximum_hinges_in_one_column": maximum_hinges,
        "rank_table": steps,
        "controls": {
            "known_simple_w_count": len(simple_indices),
            "known_simple_w_rank": simple_rank,
            "known_simple_w_augmented_rank": simple_rank,
            "known_simple_w_max_member": True,
            "target_pivot_rejected": target_position not in pivots,
            "duplicate_source_record_index": duplicate_source,
            "duplicate_source_matrix_position": duplicate_source_position,
            "duplicate_rank_growth": 0,
            "duplicate_pivot_rejected": duplicate_position not in pivots,
            "rref_rank_with_duplicate": augmented_duplicate_rank,
            "rref_rank_without_duplicate": full_rank_without_duplicate,
        },
        "timing_seconds": {
            "row_union": union_seconds,
            "matrix_build": build_seconds,
            "rref": rref_seconds,
            "total": time.monotonic() - started,
        },
        "toolchain": {"python": sys.version, "python_flint": flint.__version__},
        "no_claim": (
            "These are exact ranks over one named finite field for the complete finite "
            "loopless degree-four signed-W universe at the named n. They do not establish "
            "an exact-Q identity, anything at n=11, or an unrestricted depth theorem."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, choices=(9, 10), required=True)
    parser.add_argument("--prime", type=int, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--columns", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    report = rank(args)
    atomic_write_json(args.output, report)
    print(
        f"GMP9_RANK_PASS n={report['n']} p={report['prime']} "
        f"full_rank={report['rank_table'][-1]['rank']} "
        f"columns={report['universe_column_denominator']} "
        f"rows={report['normal_form_row_denominator']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
