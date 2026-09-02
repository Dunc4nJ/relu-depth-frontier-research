#!/usr/bin/env python3
"""Lift a sketched modular pivot support on real rows over Q.

The rank engine chooses source-column indices using a finite-field row sketch.
This consumer reopens the exact saved columns, forms their real-row support
union, chooses an independent real-row minor modulo the named prime, solves
that integer minor with FLINT Dixon arithmetic, and verifies the resulting
rational combination on the complete saved row universe.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import resource
import struct
import time
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterator, Sequence

import flint

import exactlift


@dataclass
class ExactColumn:
    source_index: int
    linear: list[int]
    hinges: dict[str, int]
    left: list[list[int]] | None
    right: list[list[int]] | None


def read_pivots(path: Path, sketch_index: int) -> tuple[dict[str, Any], dict[str, Any]]:
    report = json.loads(path.read_text(encoding="utf-8"))
    if report.get("schema") != "max11-streamrank-pivots-v1":
        raise ValueError("unsupported pivot report schema")
    sketches = report.get("sketches", [])
    if not 0 <= sketch_index < len(sketches):
        raise ValueError(f"sketch index {sketch_index} outside 0..{len(sketches) - 1}")
    sketch = sketches[sketch_index]
    pivots = list(map(int, sketch["pivot_columns"]))
    if len(pivots) != len(set(pivots)):
        raise ValueError("pivot report repeats a source column")
    if len(pivots) != int(sketch["rank_a"]):
        raise ValueError("pivot count does not equal reported rank")
    if sketch.get("verdict") != "MEMBER":
        raise ValueError(f"support lifting requires MEMBER, got {sketch.get('verdict')}")
    return report, sketch


def load_saved_selected(
    system: Path, pivots: list[int], n: int
) -> tuple[list[ExactColumn], int]:
    wanted = set(pivots)
    selected: dict[int, ExactColumn] = {}
    total_columns = 0
    for source_index, raw in enumerate(exactlift.iter_columns(system)):
        total_columns += 1
        if len(raw["lin"]) != n:
            raise ValueError(f"column {source_index} has wrong linear dimension")
        if source_index not in wanted:
            continue
        selected[source_index] = ExactColumn(
            source_index=source_index,
            linear=list(map(int, raw["lin"])),
            hinges={key: int(value) for key, value in raw["h"].items()},
            left=raw["A"],
            right=raw["B"],
        )
    missing = sorted(wanted - set(selected))
    if missing:
        raise ValueError(f"pivot source columns missing from saved system: {missing[:10]}")
    return [selected[index] for index in pivots], total_columns


def read_mcolgen_batch(path: Path) -> tuple[int, int, int, list[ExactColumn]]:
    with path.open("rb") as stream:
        if stream.read(8) != b"MCOLGEN1":
            raise ValueError(f"{path} has invalid MCOLGEN1 magic")
        header_size = struct.calcsize("<HHQQ")
        header = stream.read(header_size)
        if len(header) != header_size:
            raise ValueError(f"{path} has truncated MCOLGEN1 header")
        n, branch_edges, modulus, count = struct.unpack("<HHQQ", header)
        if modulus != 0:
            raise ValueError(f"{path} is modular; exact lifting requires modulus=0")
        columns = []
        for record in range(count):
            raw_index = stream.read(8)
            raw_linear = stream.read(8 * n)
            raw_hinge_count = stream.read(8)
            if len(raw_index) != 8 or len(raw_linear) != 8 * n or len(raw_hinge_count) != 8:
                raise ValueError(f"{path} truncates record {record}")
            source_index = struct.unpack("<Q", raw_index)[0]
            linear = list(struct.unpack(f"<{n}q", raw_linear))
            hinge_count = struct.unpack("<Q", raw_hinge_count)[0]
            hinges: dict[str, int] = {}
            for hinge in range(hinge_count):
                raw_direction = stream.read(2 * n)
                raw_coefficient = stream.read(8)
                if len(raw_direction) != 2 * n or len(raw_coefficient) != 8:
                    raise ValueError(f"{path} truncates record {record}, hinge {hinge}")
                direction = struct.unpack(f"<{n}h", raw_direction)
                coefficient = struct.unpack("<q", raw_coefficient)[0]
                key = ",".join(map(str, direction))
                if key in hinges:
                    raise ValueError(f"{path} repeats a hinge direction in record {record}")
                hinges[key] = coefficient
            columns.append(
                ExactColumn(
                    source_index=int(source_index),
                    linear=linear,
                    hinges=hinges,
                    left=None,
                    right=None,
                )
            )
        if stream.read(1):
            raise ValueError(f"{path} has trailing bytes after {count} records")
    return n, branch_edges, int(count), columns


def load_mcolgen_selected(
    batches: Sequence[Path], pivots: list[int], n: int, branch_edges: int
) -> tuple[list[ExactColumn], list[dict[str, Any]]]:
    wanted = set(pivots)
    selected: dict[int, ExactColumn] = {}
    custody = []
    for path in batches:
        batch_n, batch_k, count, columns = read_mcolgen_batch(path)
        if (batch_n, batch_k) != (n, branch_edges):
            raise ValueError(f"{path} dimensions {(batch_n, batch_k)} != {(n, branch_edges)}")
        custody.append({"path": str(path), "sha256": exactlift.sha256_file(path), "records": count})
        for column in columns:
            if column.source_index not in wanted:
                raise ValueError(f"batch contains non-pivot source index {column.source_index}")
            if column.source_index in selected:
                raise ValueError(f"duplicate source index {column.source_index} across batches")
            selected[column.source_index] = column
    missing = sorted(wanted - set(selected))
    if missing:
        raise ValueError(f"exact batches omit pivot source indices: {missing[:10]}")
    return [selected[index] for index in pivots], custody


def build_row_index(columns: Sequence[ExactColumn]) -> dict[str, int]:
    row_index: dict[str, int] = {}
    for column in columns:
        for direction in column.hinges:
            if direction not in row_index:
                row_index[direction] = len(row_index)
    return row_index


def entries(column: ExactColumn, row_index: dict[str, int]) -> Iterator[tuple[int, int]]:
    for direction, value in column.hinges.items():
        if value:
            yield row_index[direction], value
    hinge_rows = len(row_index)
    for row, value in enumerate(column.linear):
        if value:
            yield hinge_rows + row, value


def verify_selected(
    columns: Sequence[ExactColumn], coefficients: Sequence[Fraction], n: int
) -> dict[str, Any]:
    linear = [Fraction() for _ in range(n)]
    hinges: dict[str, Fraction] = defaultdict(Fraction)
    for coefficient, column in zip(coefficients, columns):
        if not coefficient:
            continue
        for row, value in enumerate(column.linear):
            linear[row] += coefficient * value
        for direction, value in column.hinges.items():
            hinges[direction] += coefficient * value
    target = [Fraction() for _ in range(n)]
    target[-1] = 1
    bad_linear = [(row, value - target[row]) for row, value in enumerate(linear) if value != target[row]]
    bad_hinges = [(direction, value) for direction, value in hinges.items() if value]
    return {
        "verdict": "PASS" if not bad_linear and not bad_hinges else "FAIL",
        "union_hinge_rows": len({direction for column in columns for direction in column.hinges}),
        "linear_rows": n,
        "nonzero_linear_residuals": [
            {"row": row, "value": exactlift.fraction_text(value)} for row, value in bad_linear
        ],
        "nonzero_hinge_residual_count": len(bad_hinges),
        "nonzero_hinge_residual_examples": [
            {"direction": direction, "value": exactlift.fraction_text(value)}
            for direction, value in sorted(bad_hinges)[:10]
        ],
    }


def lift(
    pivot_report: Path,
    sketch_index: int,
    system: Path | None,
    batches: Sequence[Path],
    output: Path,
    report_path: Path,
    upstream_output: Path | None,
) -> dict[str, Any]:
    started = time.monotonic()
    pivot_document, sketch = read_pivots(pivot_report, sketch_index)
    n = int(pivot_document["n"])
    prime = int(pivot_document["modulus"])
    pivots = list(map(int, sketch["pivot_columns"]))
    expected_denominator = int(pivot_document["source_columns_denominator"])
    if (system is None) == (not batches):
        raise ValueError("provide exactly one of --system or one-or-more --batch files")
    batch_custody: list[dict[str, Any]] = []
    if system is not None:
        if pivot_document["input_sha256"] != exactlift.sha256_file(system):
            raise ValueError("pivot report input digest does not match saved system")
        columns, total_columns = load_saved_selected(system, pivots, n)
        if pivot_document.get("subject") == "saved-system:all" and total_columns != expected_denominator:
            raise ValueError("saved all-column denominator mismatch")
        source_description = str(system)
        source_sha256 = exactlift.sha256_file(system)
    else:
        columns, batch_custody = load_mcolgen_selected(
            batches, pivots, n, int(pivot_document["branch_edge_occurrences"])
        )
        source_description = pivot_document["input"]
        source_sha256 = pivot_document["input_sha256"]

    row_index = build_row_index(columns)
    row_count = len(row_index) + n
    rank = len(columns)
    timings: dict[str, float] = {}

    phase = time.monotonic()
    transposed = flint.nmod_mat(rank, row_count, prime)
    for column_position, column in enumerate(columns):
        for row, value in entries(column, row_index):
            transposed[column_position, row] = value % prime
    timings["build_real_row_transpose_seconds"] = time.monotonic() - phase

    phase = time.monotonic()
    transposed_rref, real_rank = transposed.rref(inplace=True)
    if real_rank != rank:
        raise RuntimeError(f"sketched pivots have real-row modular rank {real_rank}, expected {rank}")
    row_pivots = exactlift.pivot_columns(transposed_rref, rank)
    timings["select_independent_real_rows_seconds"] = time.monotonic() - phase
    del transposed, transposed_rref
    gc.collect()

    phase = time.monotonic()
    selected_row_position = {row: position for position, row in enumerate(row_pivots)}
    square_rows = [[0] * rank for _ in range(rank)]
    for column_position, column in enumerate(columns):
        for global_row, value in entries(column, row_index):
            selected_row = selected_row_position.get(global_row)
            if selected_row is not None:
                square_rows[selected_row][column_position] = value
    target_row = len(row_index) + n - 1
    if target_row not in selected_row_position:
        raise RuntimeError("independent real-row minor omits the target linear row")
    rhs_values = [0] * rank
    rhs_values[selected_row_position[target_row]] = 1
    integer_matrix = flint.fmpz_mat(square_rows)
    integer_rhs = flint.fmpz_mat(rank, 1, rhs_values)
    timings["build_exact_minor_seconds"] = time.monotonic() - phase
    del square_rows
    gc.collect()

    phase = time.monotonic()
    solution = flint.fmpq_mat(integer_matrix).solve(
        flint.fmpq_mat(integer_rhs), algorithm="dixon"
    )
    timings["exact_dixon_solve_seconds"] = time.monotonic() - phase
    coefficients = [Fraction(str(solution[row, 0])) for row in range(rank)]
    selected_verification = verify_selected(columns, coefficients, n)
    if selected_verification["verdict"] != "PASS":
        raise RuntimeError("solution fails exact selected-support verification")

    witness_entries = []
    for coefficient, column in zip(coefficients, columns):
        if not coefficient:
            continue
        entry = {
            "column": column.source_index,
            "coefficient": exactlift.fraction_text(coefficient),
        }
        if column.left is not None and column.right is not None:
            entry["A"] = column.left
            entry["B"] = column.right
        witness_entries.append(entry)
    denominator_lcm = math.lcm(*(value.denominator for value in coefficients if value))
    witness = {
        "schema": exactlift.SCHEMA,
        "n": n,
        "method": "sketched pivot support, independent exact real-row minor, FLINT Dixon solve",
        "system": source_description,
        "system_sha256": source_sha256,
        "exact_batches": batch_custody,
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "sketch_index": sketch_index,
        "prime": prime,
        "rank": rank,
        "support_size": len(witness_entries),
        "coefficient_denominator_lcm": denominator_lcm,
        "coefficients": witness_entries,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(witness, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if system is not None:
        full_verification = exactlift.verify_witness(system, output)
        if full_verification["verdict"] != "PASS":
            raise RuntimeError("solution fails complete saved-system verification")
    else:
        full_verification = {
            "verdict": selected_verification["verdict"],
            "rows_checked": row_count,
            "boundary": "complete support-union verification; non-support rows are identically zero",
        }
    if upstream_output:
        if system is None:
            raise ValueError("upstream output requires saved graph-pair representatives")
        exactlift.witness_to_upstream(system, output, upstream_output)

    timings["total_seconds"] = time.monotonic() - started
    report = {
        "verdict": "PASS",
        "n": n,
        "prime": prime,
        "sketch_index": sketch_index,
        "sketch": sketch["sketch"],
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "exact_batches": batch_custody,
        "source_columns_denominator": expected_denominator,
        "pivot_columns_numerator": rank,
        "real_union_rows_denominator": row_count,
        "independent_real_rows_numerator": len(row_pivots),
        "witness_support_numerator": len(witness_entries),
        "coefficient_denominator_lcm": denominator_lcm,
        "timings_seconds": timings,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "selected_support_verification": selected_verification,
        "complete_exact_verification": full_verification,
        "witness": str(output),
        "witness_sha256": exactlift.sha256_file(output),
        "upstream_output": str(upstream_output) if upstream_output else None,
        "upstream_output_sha256": exactlift.sha256_file(upstream_output) if upstream_output else None,
        "support_union_proof": (
            "The witness has zero coefficients outside the pivot support. Therefore every hinge "
            "row absent from the union of those exact support columns has identically zero left "
            "side; the MAX target has zero hinge coefficient on every row. All n linear rows are "
            "included separately. Checking the support union is therefore checking every possibly "
            "nonzero residual row. The subsequent full saved-system replay is an additional control."
        ),
        "no_claim": "A positive n=10 control does not test or decide n=11 membership.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--sketch-index", type=int, default=0)
    parser.add_argument("--system", type=Path)
    parser.add_argument("--batch", type=Path, action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--upstream-output", type=Path)
    args = parser.parse_args(argv)
    report = lift(
        args.pivot_report,
        args.sketch_index,
        args.system,
        args.batch,
        args.output,
        args.report,
        args.upstream_output,
    )
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
