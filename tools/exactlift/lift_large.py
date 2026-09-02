#!/usr/bin/env python3
"""Large-rank exact lift using the Rust u32 block-LU/Dixon kernel.

This is a consumer of ``max11-streamrank-pivots-v1`` and exact saved-system or
``MCOLGEN1`` columns. It writes a transient sparse-CSC exact problem, invokes
the bounded-memory Rust solver, rebuilds the sparse rational witness, and then
checks every saved row with the independent Python exact verifier.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import json
import os
import random
import resource
import struct
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Sequence

import flint

import exactlift
import support_lift

MAGIC = b"ELIFTQ01"


def select_real_rows(
    columns: Sequence[support_lift.ExactColumn],
    row_index: dict[str, int],
    prime: int,
) -> tuple[list[int], float]:
    started = time.monotonic()
    rank = len(columns)
    row_count = len(row_index) + len(columns[0].linear)
    transposed = flint.nmod_mat(rank, row_count, prime)
    for column_position, column in enumerate(columns):
        for row, value in support_lift.entries(column, row_index):
            transposed[column_position, row] = value % prime
    rref, real_rank = transposed.rref(inplace=True)
    if real_rank != rank:
        raise RuntimeError(f"pivot support real-row rank {real_rank}, expected {rank}")
    selected = exactlift.pivot_columns(rref, rank)
    del transposed, rref
    gc.collect()
    return selected, time.monotonic() - started


def write_problem(
    path: Path,
    columns: Sequence[support_lift.ExactColumn],
    row_index: dict[str, int],
    selected_rows: Sequence[int],
) -> dict[str, Any]:
    rows = len(row_index) + len(columns[0].linear)
    encoded_columns = [list(support_lift.entries(column, row_index)) for column in columns]
    offsets = [0]
    for entries in encoded_columns:
        offsets.append(offsets[-1] + len(entries))
    target_row = len(row_index) + len(columns[0].linear) - 1
    rhs = [0] * rows
    rhs[target_row] = 1
    with path.open("wb") as stream:
        stream.write(MAGIC)
        stream.write(struct.pack("<IIIQ", rows, len(columns), len(selected_rows), offsets[-1]))
        stream.write(struct.pack(f"<{len(offsets)}Q", *offsets))
        for entries in encoded_columns:
            stream.write(struct.pack(f"<{len(entries)}I", *(row for row, _ in entries)))
        for entries in encoded_columns:
            values = [value for _, value in entries]
            if any(not -(1 << 31) <= value < (1 << 31) for value in values):
                raise OverflowError("exact column value exceeds i32 ELIFTQ01 encoding")
            stream.write(struct.pack(f"<{len(values)}i", *values))
        stream.write(struct.pack(f"<{len(selected_rows)}I", *selected_rows))
        stream.write(struct.pack(f"<{rows}q", *rhs))
        stream.write(struct.pack(f"<{len(columns)}Q", *(column.source_index for column in columns)))
    return {
        "schema": "ELIFTQ01",
        "rows": rows,
        "columns": len(columns),
        "csc_nonzeros": offsets[-1],
        "selected_rows": len(selected_rows),
        "bytes": path.stat().st_size,
        "sha256": exactlift.sha256_file(path),
    }


def run(
    pivot_report: Path,
    sketch_index: int,
    system: Path | None,
    batches: Sequence[Path],
    selected_rows_path: Path | None,
    binary: Path,
    prime: int,
    lu_block: int,
    row_tile: int,
    threads: int,
    max_steps: int,
    reconstruct_every: int,
    candidate_support_limit: int,
    crt_primes: str,
    output: Path,
    report_path: Path,
    upstream_output: Path | None,
    expected_upstream_sha256: str | None,
    keep_problem: Path | None,
    precondition_seed: int,
    selected_rows_output: Path | None,
) -> dict[str, Any]:
    if not 1 <= threads <= 16:
        raise ValueError("--threads must be between 1 and 16")
    started = time.monotonic()
    pivot_document, sketch = support_lift.read_pivots(pivot_report, sketch_index)
    n = int(pivot_document["n"])
    pivots = list(map(int, sketch["pivot_columns"]))
    if (system is None) == (not batches):
        raise ValueError("provide exactly one of --system or one-or-more --batch")
    batch_custody: list[dict[str, Any]] = []
    if system is not None:
        if exactlift.sha256_file(system) != pivot_document["input_sha256"]:
            raise ValueError("pivot report and saved-system hashes differ")
        columns, source_count = support_lift.load_saved_selected(system, pivots, n)
        if source_count != int(pivot_document["source_columns_denominator"]):
            raise ValueError("saved-system source-column denominator mismatch")
        source_sha256 = exactlift.sha256_file(system)
    else:
        columns, batch_custody = support_lift.load_mcolgen_selected(
            batches, pivots, n, int(pivot_document["branch_edge_occurrences"])
        )
        source_sha256 = pivot_document["input_sha256"]
    row_index = support_lift.build_row_index(columns)
    row_count = len(row_index) + n
    selection_seconds = 0.0
    if selected_rows_path is None:
        selected_rows, selection_seconds = select_real_rows(
            columns, row_index, int(pivot_document["modulus"])
        )
    else:
        selected_document = json.loads(selected_rows_path.read_text(encoding="utf-8"))
        selected_rows = list(map(int, selected_document["selected_rows"]))
        if selected_document.get("pivot_report_sha256") != exactlift.sha256_file(pivot_report):
            raise ValueError("selected-row artifact is not bound to this pivot report")
        if len(selected_rows) != len(columns) or len(set(selected_rows)) != len(columns):
            raise ValueError("selected-row artifact does not contain one distinct row per pivot")
        if any(not 0 <= row < row_count for row in selected_rows):
            raise ValueError("selected-row artifact names an out-of-range union row")
    if selected_rows_output is not None:
        selected_rows_output.parent.mkdir(parents=True, exist_ok=True)
        selected_rows_output.write_text(
            json.dumps(
                {
                    "schema": "max11-exact-selected-rows-v1",
                    "pivot_report": str(pivot_report),
                    "pivot_report_sha256": exactlift.sha256_file(pivot_report),
                    "union_rows_denominator": row_count,
                    "selected_rows": selected_rows,
                },
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )

    # Independent row/column permutations are an exact preconditioner. They
    # turn an invertible but echelon-ordered minor into generic block pivots;
    # source indices carried with columns undo the column permutation in the
    # emitted witness.
    generator = random.Random(precondition_seed)
    generator.shuffle(selected_rows)
    column_order = list(range(len(columns)))
    generator.shuffle(column_order)
    columns = [columns[position] for position in column_order]
    permutation_hash = hashlib.sha256(
        struct.pack(f"<{len(selected_rows)}I", *selected_rows)
        + struct.pack(f"<{len(column_order)}I", *column_order)
    ).hexdigest()

    temporary: tempfile.TemporaryDirectory[str] | None = None
    if keep_problem is None:
        temporary = tempfile.TemporaryDirectory(prefix="max11-lift-large-")
        problem_path = Path(temporary.name) / "problem.eliftq01"
        rust_report_path = Path(temporary.name) / "rust-result.json"
    else:
        keep_problem.parent.mkdir(parents=True, exist_ok=True)
        problem_path = keep_problem
        rust_report_path = keep_problem.with_suffix(keep_problem.suffix + ".result.json")
    problem_custody = write_problem(problem_path, columns, row_index, selected_rows)
    command = [
        str(binary),
        "solve",
        "--input",
        str(problem_path),
        "--prime",
        str(prime),
        "--lu-block",
        str(lu_block),
        "--row-tile",
        str(row_tile),
        "--threads",
        str(threads),
        "--max-steps",
        str(max_steps),
        "--reconstruct-every",
        str(reconstruct_every),
        "--candidate-support-limit",
        str(candidate_support_limit),
        "--crt-primes",
        crt_primes,
        "--output",
        str(rust_report_path),
    ]
    environment = dict(os.environ)
    environment.update(
        OPENBLAS_NUM_THREADS=str(threads),
        OMP_NUM_THREADS=str(threads),
        RAYON_NUM_THREADS=str(threads),
    )
    completed = subprocess.run(
        command,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=environment,
    )
    if completed.returncode:
        raise RuntimeError(f"Rust lift-large failed ({completed.returncode}): {completed.stderr}")
    rust_report = json.loads(rust_report_path.read_text(encoding="utf-8"))
    if rust_report.get("verdict") != "PASS":
        raise RuntimeError("Rust lift-large did not return PASS")
    coefficients = {
        int(entry["source_index"]): f'{entry["numerator"]}/{entry["denominator"]}'
        for entry in rust_report["coefficients"]
    }
    column_by_index = {column.source_index: column for column in columns}
    witness_entries = []
    for source_index in pivots:
        coefficient = coefficients.get(source_index)
        if coefficient is None:
            continue
        column = column_by_index[source_index]
        entry: dict[str, Any] = {"column": source_index, "coefficient": coefficient}
        if column.left is not None and column.right is not None:
            entry.update(A=column.left, B=column.right)
        witness_entries.append(entry)
    witness = {
        "schema": exactlift.SCHEMA,
        "n": n,
        "method": "u32 block modular LU + sparse-CSC Dixon + early rational reconstruction",
        "system": str(system) if system is not None else pivot_document["input"],
        "system_sha256": source_sha256,
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "sketch_index": sketch_index,
        "solver_prime": prime,
        "problem_custody": problem_custody,
        "exact_preconditioner": {
            "method": "independent deterministic row/column permutations",
            "seed": precondition_seed,
            "permutation_sha256": permutation_hash,
        },
        "coefficients": witness_entries,
        "no_claim": "This finite-system exact witness does not decide MAX11.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    exact_verification = None
    upstream_sha256 = None
    if system is not None:
        exact_verification = exactlift.verify_witness(system, output)
        if exact_verification["verdict"] != "PASS":
            raise RuntimeError("independent full saved-system verifier failed")
        if upstream_output is not None:
            exactlift.witness_to_upstream(system, output, upstream_output)
            upstream_sha256 = exactlift.sha256_file(upstream_output)
            if expected_upstream_sha256 is not None and upstream_sha256 != expected_upstream_sha256:
                raise RuntimeError(
                    f"upstream SHA-256 {upstream_sha256} != expected {expected_upstream_sha256}"
                )
    report = {
        "verdict": "PASS",
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "system": str(system) if system is not None else None,
        "system_sha256": source_sha256,
        "exact_batches": batch_custody,
        "pivot_columns_numerator": len(pivots),
        "source_columns_denominator": int(pivot_document["source_columns_denominator"]),
        "union_rows_denominator": row_count,
        "independent_rows_numerator": len(selected_rows),
        "row_selection_seconds": selection_seconds,
        "problem_custody": problem_custody,
        "rust_binary": str(binary),
        "rust_binary_sha256": exactlift.sha256_file(binary),
        "rust_command": command,
        "rust_result": rust_report,
        "witness": str(output),
        "witness_sha256": exactlift.sha256_file(output),
        "full_exact_verification": exact_verification,
        "upstream_output": str(upstream_output) if upstream_output is not None else None,
        "upstream_output_sha256": upstream_sha256,
        "expected_upstream_sha256": expected_upstream_sha256,
        "max_rss_kib_python_parent": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "total_seconds": time.monotonic() - started,
        "no_claim": "The result concerns only the named finite source system; no n=11 membership claim.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if temporary is not None:
        temporary.cleanup()
    return report


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument("--pivot-report", type=Path, required=True)
    result.add_argument("--sketch-index", type=int, default=0)
    result.add_argument("--system", type=Path)
    result.add_argument("--batch", type=Path, action="append", default=[])
    result.add_argument("--selected-rows", type=Path)
    result.add_argument("--binary", type=Path, required=True)
    result.add_argument("--prime", type=int, default=65521)
    result.add_argument("--lu-block", type=int, default=128)
    result.add_argument("--row-tile", type=int, default=256)
    result.add_argument("--threads", type=int, default=6)
    result.add_argument("--max-steps", type=int, default=6)
    result.add_argument("--reconstruct-every", type=int, default=1)
    result.add_argument("--candidate-support-limit", type=int, default=2000)
    result.add_argument("--crt-primes", default="65519,65497,65479,65449,65447,65437")
    result.add_argument("--output", type=Path, required=True)
    result.add_argument("--report", type=Path, required=True)
    result.add_argument("--upstream-output", type=Path)
    result.add_argument("--expected-upstream-sha256")
    result.add_argument("--keep-problem", type=Path)
    result.add_argument("--precondition-seed", type=int, default=20260902)
    result.add_argument("--selected-rows-output", type=Path)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    args = parser().parse_args(argv)
    report = run(
        args.pivot_report,
        args.sketch_index,
        args.system,
        args.batch,
        args.selected_rows,
        args.binary,
        args.prime,
        args.lu_block,
        args.row_tile,
        args.threads,
        args.max_steps,
        args.reconstruct_every,
        args.candidate_support_limit,
        args.crt_primes,
        args.output,
        args.report,
        args.upstream_output,
        args.expected_upstream_sha256,
        args.keep_problem,
        args.precondition_seed,
        args.selected_rows_output,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
