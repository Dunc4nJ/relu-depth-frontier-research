#!/usr/bin/env python3
"""Bounded streaming incidence audit for G-0016 (temporary execution source)."""

from __future__ import annotations

import argparse
import json
import math
import os
import resource
import struct
import time
from fractions import Fraction
from pathlib import Path

import numpy as np


EXPECTED_SCHEMA = "max11-exactlift-witness-v1"
EXPECTED_MAGIC = b"ELIFTQ02"
EXPECTED_N = 11


def accumulate(
    all_seen: np.ndarray,
    support_seen: np.ndarray,
    hinge_ids: np.ndarray,
    is_support: bool,
) -> None:
    all_seen[hinge_ids] = True
    if is_support:
        support_seen[hinge_ids] = True


def self_test() -> dict[str, str]:
    # Known answer: support columns 100 and 300 touch {0,2}; zero column 200
    # adds hinge 1, so all-support is exactly {1}, touched only by column 200.
    columns = {
        100: np.array([0, 2], dtype=np.uint32),
        200: np.array([1, 2, 2], dtype=np.uint32),
        300: np.array([2], dtype=np.uint32),
    }
    all_seen = np.zeros(4, dtype=np.bool_)
    support_seen = np.zeros(4, dtype=np.bool_)
    support = {100, 300}
    for source, hinges in columns.items():
        accumulate(all_seen, support_seen, hinges, source in support)
    difference = np.flatnonzero(all_seen & ~support_seen).tolist()
    touching = {
        hinge: [source for source, hinges in columns.items() if hinge in hinges]
        for hinge in difference
    }
    assert np.flatnonzero(all_seen).tolist() == [0, 1, 2]
    assert np.flatnonzero(support_seen).tolist() == [0, 2]
    assert difference == [1]
    assert touching == {1: [200]}

    # Deliberately defective support: marking column 200 nonzero must destroy
    # the one-row difference. A result invariant to this mutation is broken.
    bad_support_seen = np.zeros(4, dtype=np.bool_)
    for source, hinges in columns.items():
        if source in {100, 200, 300}:
            bad_support_seen[hinges] = True
    assert np.flatnonzero(all_seen & ~bad_support_seen).tolist() == []
    return {
        "known_answer_positive": "PASS: all=3/4, support=2/4, difference=1/4, toucher=[200]",
        "support_mutation_negative": "PASS: adding source 200 to support changed difference 1/4 -> 0/4",
    }


def read_header(path: Path) -> tuple[dict[str, int | str], np.ndarray, dict[str, int]]:
    with path.open("rb", buffering=16 << 20) as stream:
        magic = stream.read(8)
        if magic != EXPECTED_MAGIC:
            raise ValueError(f"magic {magic!r} != {EXPECTED_MAGIC!r}")
        rows, columns, selected = struct.unpack("<III", stream.read(12))
        (nnz,) = struct.unpack("<Q", stream.read(8))
        offsets = np.fromfile(stream, dtype="<u8", count=columns + 1)
    if len(offsets) != columns + 1:
        raise ValueError("short CSC offsets")
    if offsets[0] != 0 or offsets[-1] != nnz or np.any(offsets[1:] < offsets[:-1]):
        raise ValueError("invalid CSC offsets")

    row_start = 28 + 8 * (columns + 1)
    value_start = row_start + 4 * nnz
    selected_start = value_start + 8 * nnz
    rhs_start = selected_start + 4 * columns
    source_start = rhs_start + 8 * rows
    expected_bytes = source_start + 8 * columns
    actual_bytes = path.stat().st_size
    if actual_bytes != expected_bytes:
        raise ValueError(f"file bytes {actual_bytes} != layout bytes {expected_bytes}")
    if selected != columns:
        raise ValueError(f"selected rows {selected} != columns {columns}")
    return (
        {
            "magic": magic.decode("ascii"),
            "rows": rows,
            "columns": columns,
            "selected_rows": selected,
            "nnz": nnz,
            "bytes": actual_bytes,
        },
        offsets,
        {
            "row_start": row_start,
            "value_start": value_start,
            "selected_start": selected_start,
            "rhs_start": rhs_start,
            "source_start": source_start,
        },
    )


def parse_witness(path: Path) -> tuple[dict, dict[int, Fraction]]:
    with path.open("r", encoding="utf-8") as stream:
        document = json.load(stream)
    if document.get("schema") != EXPECTED_SCHEMA or int(document.get("n", -1)) != EXPECTED_N:
        raise ValueError("wrong witness schema or n")
    coefficients: dict[int, Fraction] = {}
    for entry in document["coefficients"]:
        source = int(entry["column"])
        if source in coefficients:
            raise ValueError(f"repeated witness source column {source}")
        coefficient = Fraction(entry["coefficient"])
        if coefficient == 0 or coefficient.denominator <= 0:
            raise ValueError(f"noncanonical/zero sparse coefficient at {source}")
        coefficients[source] = coefficient
    return document, coefficients


def read_source_indices(
    path: Path, source_start: int, columns: int
) -> np.ndarray:
    with path.open("rb", buffering=16 << 20) as stream:
        stream.seek(source_start)
        source_indices = np.fromfile(stream, dtype="<u8", count=columns)
    if len(source_indices) != columns:
        raise ValueError("short source-index array")
    if len(np.unique(source_indices)) != columns:
        raise ValueError("repeated source index in ELIFTQ02")
    return source_indices


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--problem", required=True, type=Path)
    parser.add_argument("--witness", required=True, type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    controls = self_test()
    witness, coefficients = parse_witness(args.witness)
    header, offsets, layout = read_header(args.problem)
    rows = int(header["rows"])
    columns = int(header["columns"])
    nnz = int(header["nnz"])
    source_indices = read_source_indices(args.problem, layout["source_start"], columns)
    source_to_position = {int(source): position for position, source in enumerate(source_indices)}
    unknown_support = sorted(set(coefficients) - set(source_to_position))
    if unknown_support:
        raise ValueError(f"witness has {len(unknown_support)} non-pivot source IDs")
    support_position = np.array(
        [int(source) in coefficients for source in source_indices], dtype=np.bool_
    )
    if int(support_position.sum()) != len(coefficients):
        raise ValueError("witness support/pivot intersection count mismatch")

    n = int(witness["n"])
    hinge_base = columns + n
    hinge_universe = rows - hinge_base
    if hinge_universe <= 0:
        raise ValueError("empty hinge universe")
    all_seen = np.zeros(hinge_universe, dtype=np.bool_)
    support_seen = np.zeros(hinge_universe, dtype=np.bool_)
    raw_hinge_entries_all = 0
    raw_hinge_entries_support = 0
    stored_zero_values = 0
    pass1_started = time.monotonic()
    with args.problem.open("rb", buffering=16 << 20) as row_stream, args.problem.open(
        "rb", buffering=16 << 20
    ) as value_stream:
        row_stream.seek(layout["row_start"])
        value_stream.seek(layout["value_start"])
        for column in range(columns):
            count = int(offsets[column + 1] - offsets[column])
            row_ids = np.fromfile(row_stream, dtype="<u4", count=count)
            values = np.fromfile(value_stream, dtype="<i8", count=count)
            if len(row_ids) != count or len(values) != count:
                raise ValueError(f"short CSC column {column}")
            if count and int(row_ids.max()) >= rows:
                raise ValueError(f"row outside universe in column {column}")
            stored_zero_values += int(np.count_nonzero(values == 0))
            is_hinge = row_ids >= hinge_base
            hinge_ids = row_ids[is_hinge] - hinge_base
            raw_hinge_entries_all += len(hinge_ids)
            if support_position[column]:
                raw_hinge_entries_support += len(hinge_ids)
            accumulate(all_seen, support_seen, hinge_ids, bool(support_position[column]))
        if row_stream.tell() != layout["value_start"]:
            raise ValueError("row-index pass ended at wrong byte")
        if value_stream.tell() != layout["selected_start"]:
            raise ValueError("value pass ended at wrong byte")
    if stored_zero_values:
        raise ValueError(f"ELIFTQ02 stores {stored_zero_values} zero CSC values")
    pass1_seconds = time.monotonic() - pass1_started

    difference = np.flatnonzero(all_seen & ~support_seen).astype(np.int64)
    difference_lookup = np.full(hinge_universe, -1, dtype=np.int32)
    difference_lookup[difference] = np.arange(len(difference), dtype=np.int32)
    touching_positions: list[list[int]] = [[] for _ in difference]
    raw_difference_entries = 0
    pass2_started = time.monotonic()
    with args.problem.open("rb", buffering=16 << 20) as row_stream:
        row_stream.seek(layout["row_start"])
        for column in range(columns):
            count = int(offsets[column + 1] - offsets[column])
            row_ids = np.fromfile(row_stream, dtype="<u4", count=count)
            if len(row_ids) != count:
                raise ValueError(f"short second-pass CSC column {column}")
            is_hinge = row_ids >= hinge_base
            hinge_ids = row_ids[is_hinge] - hinge_base
            slots = difference_lookup[hinge_ids]
            slots = slots[slots >= 0]
            raw_difference_entries += len(slots)
            for slot in np.unique(slots):
                touching_positions[int(slot)].append(column)
    pass2_seconds = time.monotonic() - pass2_started

    difference_rows = []
    support_touchers = 0
    touching_source_union: set[int] = set()
    for slot, hinge_id in enumerate(difference.tolist()):
        positions = touching_positions[slot]
        if not positions:
            raise ValueError(f"difference hinge {hinge_id} has no touching column")
        sources = [int(source_indices[position]) for position in positions]
        present = [source for source in sources if source in coefficients]
        support_touchers += len(present)
        touching_source_union.update(sources)
        difference_rows.append(
            {
                "hinge_id_zero_based": hinge_id,
                "combined_row_zero_based": hinge_base + hinge_id,
                "touching_pivot_positions_zero_based": positions,
                "touching_source_columns": sources,
                "touching_columns_numerator": len(sources),
                "touching_columns_denominator": columns,
                "witness_nonzero_touching_columns_numerator": len(present),
                "witness_nonzero_touching_columns_denominator": len(sources),
            }
        )
    if support_touchers:
        raise ValueError(f"difference rows have {support_touchers} support-column touchers")

    all_count = int(all_seen.sum())
    support_count = int(support_seen.sum())
    observed = {
        "all_column_hinge_union_numerator": all_count,
        "all_column_hinge_union_denominator": hinge_universe,
        "support_column_hinge_union_numerator": support_count,
        "support_column_hinge_union_denominator": hinge_universe,
        "difference_hinge_rows_numerator": len(difference),
        "difference_hinge_rows_denominator": hinge_universe,
        "pivot_columns_numerator": columns,
        "pivot_columns_denominator": columns,
        "witness_support_columns_numerator": len(coefficients),
        "witness_support_columns_denominator": columns,
        "zero_coefficient_pivot_columns_numerator": columns - len(coefficients),
        "zero_coefficient_pivot_columns_denominator": columns,
        "difference_touching_source_columns_numerator": len(touching_source_union),
        "difference_touching_source_columns_denominator": columns - len(coefficients),
        "support_touching_difference_rows_numerator": support_touchers,
        "support_touching_difference_rows_denominator": len(difference),
        "raw_hinge_entries_all_numerator": raw_hinge_entries_all,
        "raw_hinge_entries_all_denominator": nnz,
        "raw_hinge_entries_support_numerator": raw_hinge_entries_support,
        "raw_hinge_entries_support_denominator": nnz,
        "raw_difference_entries_numerator": raw_difference_entries,
        "raw_difference_entries_denominator": raw_hinge_entries_all,
    }
    expected_hinge_union = int(
        witness["exact_verification"]["union_hinge_rows_denominator"]
    )
    verdict = (
        "CONFIRMED"
        if all_count == expected_hinge_union
        and support_count == 169166
        and len(difference) == 84
        and support_touchers == 0
        else "REFUTED"
    )
    output = {
        "schema": "max11-g0016-hinge-union-audit-v1",
        "verdict": verdict,
        "controls": controls,
        "problem_header": header,
        "layout": layout,
        "witness_problem_custody": witness["problem_custody"],
        "observed": observed,
        "difference_rows": difference_rows,
        "timing_seconds": {
            "pass1_rows_and_values": pass1_seconds,
            "pass2_rows": pass2_seconds,
            "total": time.monotonic() - started,
        },
        "threads_maximum": 1,
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": (
            "This audit only reconciles the named run7 problem-row union with the "
            "named sparse witness support. It does not reverify the rational identity, "
            "the upstream translation, the realization lemma, or MAX_11 itself."
        ),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
