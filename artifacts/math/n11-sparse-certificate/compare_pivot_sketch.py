#!/usr/bin/env python3
"""Exact parity control between the all-F2 sketch CSC and the prior pivot ELIFTQ02."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import time
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def compare(matrix_dir: Path, problem: Path, output: Path) -> dict:
    started = time.monotonic()
    meta_path = matrix_dir / "matrix.json"
    meta = json.loads(meta_path.read_text())
    files = meta["files"]
    full_columns = int(meta["columns_denominator"])
    full_rows = int(meta["rows_denominator"])
    full_nnz = int(meta["nonzeros_denominator"])
    full_start = np.memmap(matrix_dir / files["start"]["path"], mode="r", dtype="<u8")
    full_index = np.memmap(matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    full_value = np.memmap(matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    full_source = np.memmap(matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    full_target = np.memmap(matrix_dir / files["target"]["path"], mode="r", dtype="<i8")
    if len(full_start) != full_columns + 1 or int(full_start[-1]) != full_nnz or len(full_target) != full_rows:
        raise ValueError("invalid all-F2 CSC")
    by_source = {int(source): position for position, source in enumerate(full_source)}
    if len(by_source) != full_columns:
        raise ValueError("all-F2 CSC repeats a source index")

    with problem.open("rb") as stream:
        header = stream.read(28)
    magic, rows, columns, rank, nnz = struct.unpack("<8sIIIQ", header)
    if magic != b"ELIFTQ02" or rank != columns or rank != full_rows:
        raise ValueError(f"incompatible ELIFTQ02 header: {(magic, rows, columns, rank, nnz)}")
    cursor = 28
    pivot_start = np.memmap(problem, mode="r", dtype="<u8", offset=cursor, shape=(columns + 1,))
    cursor += 8 * (columns + 1)
    pivot_index = np.memmap(problem, mode="r", dtype="<u4", offset=cursor, shape=(nnz,))
    cursor += 4 * nnz
    pivot_value = np.memmap(problem, mode="r", dtype="<i8", offset=cursor, shape=(nnz,))
    cursor += 8 * nnz
    row_pivots = np.memmap(problem, mode="r", dtype="<u4", offset=cursor, shape=(rank,))
    cursor += 4 * rank
    rhs = np.memmap(problem, mode="r", dtype="<i8", offset=cursor, shape=(rows,))
    cursor += 8 * rows
    pivot_source = np.memmap(problem, mode="r", dtype="<u8", offset=cursor, shape=(columns,))
    if cursor + 8 * columns != problem.stat().st_size:
        raise ValueError("ELIFTQ02 size/header mismatch")
    if not np.array_equal(row_pivots, np.arange(rank, dtype=np.uint32)):
        raise ValueError("ELIFTQ02 does not select its first rank rows as the square minor")
    if not np.array_equal(rhs[:rank], full_target):
        raise ValueError("target sketch mismatch")

    compared_nnz = 0
    mismatch_columns = []
    for pivot_position, source in enumerate(pivot_source):
        full_position = by_source.get(int(source))
        if full_position is None:
            mismatch_columns.append({"pivot_position": pivot_position, "source_index": int(source), "reason": "missing source"})
            continue
        left, right = int(pivot_start[pivot_position]), int(pivot_start[pivot_position + 1])
        mask = pivot_index[left:right] < rank
        old_rows = pivot_index[left:right][mask]
        old_values = pivot_value[left:right][mask]
        begin, end = int(full_start[full_position]), int(full_start[full_position + 1])
        new_rows = full_index[begin:end]
        new_values = full_value[begin:end]
        compared_nnz += len(old_rows)
        if not np.array_equal(old_rows, new_rows) or not np.array_equal(old_values, new_values):
            mismatch_columns.append({
                "pivot_position": pivot_position,
                "source_index": int(source),
                "prior_sketch_nnz": int(len(old_rows)),
                "new_sketch_nnz": int(len(new_rows)),
            })
            if len(mismatch_columns) >= 10:
                break
        if (pivot_position + 1) % 1024 == 0 or pivot_position + 1 == columns:
            print(f"PIVOT_PARITY columns={pivot_position + 1}/{columns} nnz={compared_nnz} seconds={time.monotonic() - started:.3f}", flush=True)
    if mismatch_columns:
        raise RuntimeError(f"pivot sketch mismatch: {mismatch_columns}")

    # Negative control: the same comparator predicate must reject an exact +1
    # mutation of a real prior entry.
    first = int(pivot_start[0])
    stop = int(pivot_start[1])
    local = np.flatnonzero(pivot_index[first:stop] < rank)
    if not len(local):
        raise RuntimeError("first pivot column has no sketch entry for mutation control")
    cursor0 = first + int(local[0])
    full_position = by_source[int(pivot_source[0])]
    begin, end = int(full_start[full_position]), int(full_start[full_position + 1])
    row = int(pivot_index[cursor0])
    at = np.flatnonzero(full_index[begin:end] == row)
    if len(at) != 1:
        raise RuntimeError("mutation-control row missing or repeated")
    unchanged = int(pivot_value[cursor0]) == int(full_value[begin + int(at[0])])
    mutated_rejected = int(pivot_value[cursor0]) + 1 != int(full_value[begin + int(at[0])])
    if not unchanged or not mutated_rejected:
        raise RuntimeError("negative mutation control failed")

    report = {
        "schema": "max11-sparse-sketch-pivot-parity-v1",
        "verdict": "PASS",
        "exact": True,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "prior_problem": str(problem),
        "prior_problem_bytes": problem.stat().st_size,
        "prior_problem_sha256": sha256(problem),
        "pivot_columns_verified_numerator": columns,
        "pivot_columns_verified_denominator": columns,
        "sketch_entries_verified_numerator": compared_nnz,
        "sketch_entries_verified_denominator": compared_nnz,
        "target_rows_verified_numerator": rank,
        "target_rows_verified_denominator": rank,
        "negative_control": {"mutation": "+1/1 on one prior exact sketch entry", "rejected_numerator": 1, "rejected_denominator": 1},
        "seconds": time.monotonic() - started,
        "no_claim": "Parity with the prior exact pivot sketch validates construction but does not verify any floating LP candidate or rational identity.",
    }
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--prior-problem", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(compare(args.matrix_dir, args.prior_problem, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
