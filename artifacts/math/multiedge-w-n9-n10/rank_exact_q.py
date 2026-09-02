#!/usr/bin/env python3
"""Optional exact-Q cumulative multiplicity ranks for n=7 and n=8."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import sys
import time

import flint


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rank_multiedge as common  # noqa: E402


SCHEMA = "max11-gmp9-multiedge-exact-q-rank-v1"
EXPECTED_SIMPLE_COUNT = {7: 2_034, 8: 4_315}


def pivot_columns(matrix: flint.fmpz_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    search_from = 0
    for row in range(rank):
        while search_from < matrix.ncols() and matrix[row, search_from] == 0:
            search_from += 1
        if search_from == matrix.ncols():
            raise AssertionError("exact RREF row has no pivot")
        pivots.append(search_from)
        search_from += 1
    return pivots


def run(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    universe = common.load_universe(args.universe)
    n = int(universe["n"])
    records = universe["records"]
    if n != args.n or int(universe["branch_edge_occurrences"]) != 4:
        raise ValueError("universe dimensions do not match")
    maxima = [common.recompute_max_multiplicity(record) for record in records]
    counts = Counter(maxima)
    simple = [index for index, maximum in enumerate(maxima) if maximum <= 1]
    if len(simple) != EXPECTED_SIMPLE_COUNT[n]:
        raise AssertionError("simple-W count known answer failed")
    maximum_value = max(maxima)
    groups = {
        maximum: [index for index, value in enumerate(maxima) if value == maximum]
        for maximum in range(2, maximum_value + 1)
    }
    order = simple + [
        index
        for maximum in range(2, maximum_value + 1)
        for index in groups[maximum]
    ]
    position = {source: destination for destination, source in enumerate(order)}
    if sorted(order) != list(range(len(records))):
        raise AssertionError("multiplicity ordering is not a permutation")

    directions, total_hinges, maximum_hinges = common.scan_row_union(
        args.columns, len(records)
    )
    row_index = {direction: index for index, direction in enumerate(directions)}
    linear_offset = len(directions)
    row_count = linear_offset + n
    target_position = len(simple)
    duplicate_position = len(records) + 1
    duplicate_source_index = simple[1]
    duplicate_source_position = position[duplicate_source_index]

    build_started = time.monotonic()
    matrix = flint.fmpz_mat(row_count, len(records) + 2)
    for source, linear, hinges in common.read_columns(args.columns):
        destination = position[source]
        if destination >= target_position:
            destination += 1
        for coordinate, coefficient in enumerate(linear):
            if coefficient:
                matrix[linear_offset + coordinate, destination] = coefficient
        for direction, coefficient in hinges:
            if coefficient:
                matrix[row_index[direction], destination] = coefficient
    matrix[linear_offset + n - 1, target_position] = 1
    for row in range(row_count):
        matrix[row, duplicate_position] = matrix[row, duplicate_source_position]
    build_seconds = time.monotonic() - build_started

    rref_started = time.monotonic()
    reduced, denominator, exact_rank = matrix.rref()
    rref_seconds = time.monotonic() - rref_started
    pivots = pivot_columns(reduced, exact_rank)
    if target_position in pivots:
        raise AssertionError("MAX target is not in the exact-Q simple-W span")
    if duplicate_position in pivots:
        raise AssertionError("planted duplicate raised exact-Q rank")

    steps = []
    cumulative_count = len(simple)
    cutoff = target_position + 1
    previous_rank = 0
    for maximum in range(1, maximum_value + 1):
        if maximum == 1:
            added = len(simple)
        else:
            added = len(groups[maximum])
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
    full_without_duplicate = sum(pivot < duplicate_position for pivot in pivots)
    if full_without_duplicate != exact_rank or steps[-1]["rank"] != exact_rank:
        raise AssertionError("exact-Q rank accounting mismatch")

    return {
        "schema": SCHEMA,
        "result": "PASS",
        "field": "Q",
        "n": n,
        "branch_edge_occurrences": 4,
        "universe": str(args.universe),
        "universe_sha256": common.sha256_path(args.universe),
        "exact_columns": str(args.columns),
        "exact_columns_sha256": common.sha256_path(args.columns),
        "universe_column_denominator": len(records),
        "max_multiplicity_counts": dict(sorted(counts.items())),
        "hinge_row_denominator": len(directions),
        "linear_row_denominator": n,
        "normal_form_row_denominator": row_count,
        "hinge_nonzero_occurrence_denominator": total_hinges,
        "maximum_hinges_in_one_column": maximum_hinges,
        "common_rref_denominator": str(denominator),
        "rank_table": steps,
        "controls": {
            "target_pivot_rejected": target_position not in pivots,
            "duplicate_source_record_index": duplicate_source_index,
            "duplicate_rank_growth": 0,
            "duplicate_pivot_rejected": duplicate_position not in pivots,
            "exact_rank_with_duplicate": exact_rank,
            "exact_rank_without_duplicate": full_without_duplicate,
        },
        "timing_seconds": {
            "matrix_build": build_seconds,
            "rref": rref_seconds,
            "total": time.monotonic() - started,
        },
        "toolchain": {"python": sys.version, "python_flint": flint.__version__},
        "no_claim": (
            "This is an exact-Q rank computation only for the finite loopless "
            "degree-four signed-W universe at the named n. It says nothing at n=11."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, choices=(7, 8), required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--columns", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = run(args)
    common.atomic_write_json(args.output, result)
    print(
        f"GMP9_EXACT_Q_PASS n={args.n} rank={result['rank_table'][-1]['rank']} "
        f"columns={result['universe_column_denominator']} rows={result['normal_form_row_denominator']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
