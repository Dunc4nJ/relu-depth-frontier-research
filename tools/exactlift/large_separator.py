#!/usr/bin/env python3
"""Lift a finite-sketch exact separator through the large-rank Rust solver."""

from __future__ import annotations

import argparse
import gc
import json
import math
import os
import struct
import subprocess
import tempfile
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

import flint

import exactlift
import sketch_separator


def write_square_problem(
    path: Path,
    matrix_rows: Sequence[Sequence[int]],
    rhs: Sequence[int],
    source_indices: Sequence[int],
) -> dict[str, Any]:
    size = len(matrix_rows)
    if size == 0 or any(len(row) != size for row in matrix_rows):
        raise ValueError("separator problem must be square")
    columns = []
    for column in range(size):
        columns.append(
            [(row, int(matrix_rows[row][column])) for row in range(size) if matrix_rows[row][column]]
        )
    offsets = [0]
    for column in columns:
        offsets.append(offsets[-1] + len(column))
    with path.open("wb") as stream:
        stream.write(b"ELIFTQ01")
        stream.write(struct.pack("<IIIQ", size, size, size, offsets[-1]))
        stream.write(struct.pack(f"<{len(offsets)}Q", *offsets))
        for column in columns:
            stream.write(struct.pack(f"<{len(column)}I", *(row for row, _ in column)))
        for column in columns:
            stream.write(struct.pack(f"<{len(column)}i", *(value for _, value in column)))
        stream.write(struct.pack(f"<{size}I", *range(size)))
        stream.write(struct.pack(f"<{size}q", *rhs))
        stream.write(struct.pack(f"<{size}Q", *source_indices))
    return {
        "schema": "ELIFTQ01",
        "rows": size,
        "columns": size,
        "csc_nonzeros": offsets[-1],
        "bytes": path.stat().st_size,
        "sha256": exactlift.sha256_file(path),
    }


def run(
    pivot_report: Path,
    sketch_index: int,
    system: Path,
    binary: Path,
    threads: int,
    output: Path,
    report_path: Path,
) -> dict[str, Any]:
    if not 1 <= threads <= 6:
        raise ValueError("threads must be in 1..6")
    started = time.monotonic()
    document = json.loads(pivot_report.read_text(encoding="utf-8"))
    if document.get("schema") != "max11-streamrank-pivots-v1":
        raise ValueError("unsupported pivot schema")
    if document["input_sha256"] != exactlift.sha256_file(system):
        raise ValueError("pivot/system digest mismatch")
    record = document["sketches"][sketch_index]
    if record["verdict"] != "NON_MEMBER":
        raise ValueError("separator requires NON_MEMBER sketch")
    sketch = record["sketch"]
    if sketch["algorithm"] != sketch_separator.ALGORITHM:
        raise ValueError("unsupported sketch algorithm")
    n = int(document["n"])
    seed = int(sketch["seed"])
    buckets = int(sketch["buckets"])
    prime = int(document["modulus"])
    columns, source_count = sketch_separator.load_filtered(system, n, document["subject"])
    if source_count != int(document["source_columns_denominator"]):
        raise ValueError("filtered source denominator mismatch")
    sketched = [sketch_separator.sketch_column(column, seed, buckets) for column in columns]
    target = sketch_separator.target_sketch(n, seed, buckets)

    matrix = flint.nmod_mat(buckets, source_count, prime)
    augmented = flint.nmod_mat(buckets, source_count + 1, prime)
    for column_position, values in enumerate(sketched):
        for bucket, value in enumerate(values):
            if value:
                matrix[bucket, column_position] = value % prime
                augmented[bucket, column_position] = value % prime
    for bucket, value in enumerate(target):
        if value:
            augmented[bucket, source_count] = value % prime
    rank_a = matrix.rank()
    rank_augmented = augmented.rank()
    if (rank_a, rank_augmented) != (int(record["rank_a"]), int(record["rank_augmented"])):
        raise RuntimeError("exact replay rank mismatch")
    transposed_rref, transposed_rank = augmented.transpose().rref(inplace=True)
    if transposed_rank != rank_augmented:
        raise RuntimeError("augmented transpose rank mismatch")
    bucket_support = exactlift.pivot_columns(transposed_rref, rank_augmented)
    del transposed_rref, matrix, augmented
    gc.collect()

    supported = flint.nmod_mat(rank_augmented, source_count + 1, prime)
    for row_position, bucket in enumerate(bucket_support):
        for column_position, values in enumerate(sketched):
            supported[row_position, column_position] = values[bucket] % prime
        supported[row_position, source_count] = target[bucket] % prime
    supported_rref, supported_rank = supported.rref(inplace=True)
    if supported_rank != rank_augmented:
        raise RuntimeError("supported augmented rows lost rank")
    equation_support = exactlift.pivot_columns(supported_rref, rank_augmented)
    if source_count not in equation_support:
        raise RuntimeError("separator minor omits target equation")
    del supported, supported_rref
    gc.collect()

    equation_rows = [
        [
            target[bucket] if equation == source_count else sketched[equation][bucket]
            for bucket in bucket_support
        ]
        for equation in equation_support
    ]
    rhs = [1 if equation == source_count else 0 for equation in equation_support]
    with tempfile.TemporaryDirectory(prefix="max11-large-separator-") as temporary:
        problem_path = Path(temporary) / "separator.eliftq01"
        rust_path = Path(temporary) / "result.json"
        custody = write_square_problem(problem_path, equation_rows, rhs, bucket_support)
        command = [
            str(binary), "solve-big", "--input", str(problem_path),
            "--prime", "65521", "--lu-block", "64", "--row-tile", "128",
            "--threads", str(threads), "--max-steps", "100", "--reconstruct-every", "1",
            "--output", str(rust_path),
        ]
        environment = dict(os.environ, OPENBLAS_NUM_THREADS=str(threads), OMP_NUM_THREADS=str(threads))
        completed = subprocess.run(command, text=True, capture_output=True, env=environment)
        if completed.returncode:
            raise RuntimeError(f"large separator solve failed: {completed.stderr}")
        rust = json.loads(rust_path.read_text(encoding="utf-8"))
    bucket_weights = {
        int(entry["source_index"]): Fraction(int(entry["numerator"]), int(entry["denominator"]))
        for entry in rust["coefficients"]
    }
    linear_weights = []
    for rank in range(n):
        bucket, sign = sketch_separator.linear_bucket(seed, buckets, n, rank)
        linear_weights.append(sign * bucket_weights.get(bucket, Fraction()))
    hinge_directions = sorted({direction for column in columns for direction in column.hinges})
    hinge_weights = {}
    for raw_direction in hinge_directions:
        direction = tuple(map(int, raw_direction.split(",")))
        bucket, sign = sketch_separator.hinge_bucket(seed, buckets, direction)
        value = sign * bucket_weights.get(bucket, Fraction())
        if value:
            hinge_weights[raw_direction] = value
    denominator_lcm = math.lcm(
        *(value.denominator for value in bucket_weights.values()),
        *(value.denominator for value in linear_weights if value),
        *(value.denominator for value in hinge_weights.values()),
    )
    separator = {
        "schema": "max11-exact-sketch-separator-v1",
        "method": "large-rank u32 block-LU/Dixon separator on sketch buckets, composed with CountSketch",
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "sketch_index": sketch_index,
        "system": str(system),
        "system_sha256": exactlift.sha256_file(system),
        "subject": document["subject"],
        "n": n,
        "prime": prime,
        "sketch": sketch,
        "bucket_weights": {
            str(bucket): exactlift.fraction_text(value)
            for bucket, value in sorted(bucket_weights.items())
        },
        "linear_weights": [exactlift.fraction_text(value) for value in linear_weights],
        "hinge_weights": {
            direction: exactlift.fraction_text(value) for direction, value in hinge_weights.items()
        },
        "coefficient_denominator_lcm": denominator_lcm,
    }
    exact_verification = sketch_separator.verify_real_separator(columns, separator, n)
    if exact_verification["verdict"] != "PASS":
        raise RuntimeError("composed separator fails exact all-column check")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(separator, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "verdict": "PASS",
        "prime": prime,
        "rank_a": rank_a,
        "rank_augmented": rank_augmented,
        "source_columns_denominator": source_count,
        "sketch_buckets_denominator": buckets,
        "bucket_support_numerator": len(bucket_support),
        "nonzero_bucket_weights_numerator": len(bucket_weights),
        "problem_custody": custody,
        "rust_binary_sha256": exactlift.sha256_file(binary),
        "rust_result": rust,
        "exact_verification": exact_verification,
        "separator": str(output),
        "separator_sha256": exactlift.sha256_file(output),
        "coefficient_denominator_lcm": denominator_lcm,
        "total_seconds": time.monotonic() - started,
        "no_claim": "The separator concerns only the named finite tree family, not MAX11.",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--sketch-index", type=int, default=0)
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(run(
        args.pivot_report, args.sketch_index, args.system, args.binary,
        args.threads, args.output, args.report,
    ), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
