#!/usr/bin/env python3
"""Solve base and iteratively reweighted L1 equality LPs from exact CSC files."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import time
from fractions import Fraction
from pathlib import Path

import highspy
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def check(status, label: str) -> None:
    if status != highspy.HighsStatus.kOk:
        raise RuntimeError(f"HiGHS {label} failed: {status}")


def info_fields(info) -> dict:
    names = (
        "simplex_iteration_count",
        "ipm_iteration_count",
        "crossover_iteration_count",
        "objective_function_value",
        "max_primal_infeasibility",
        "sum_primal_infeasibilities",
        "num_primal_infeasibilities",
        "max_dual_infeasibility",
        "sum_dual_infeasibilities",
        "num_dual_infeasibilities",
    )
    return {name: getattr(info, name) for name in names if hasattr(info, name)}


def solve(
    matrix_dir: Path,
    output: Path,
    log: Path,
    threads: int,
    rounds: int,
    feasibility_tolerance: float,
    support_threshold: float,
    reweight_epsilon: float,
    reweight_cap: float,
    initial_witness: Path | None = None,
) -> dict:
    started = time.monotonic()
    meta_path = matrix_dir / "matrix.json"
    meta = json.loads(meta_path.read_text())
    if meta.get("verdict") != "PASS":
        raise ValueError("matrix report is not PASS")
    rows = int(meta["rows_denominator"])
    columns = int(meta["columns_denominator"])
    nnz = int(meta["nonzeros_denominator"])
    files = meta["files"]
    for record in files.values():
        path = matrix_dir / record["path"]
        if path.stat().st_size != int(record["bytes"]) or sha256(path) != record["sha256"]:
            raise ValueError(f"matrix custody mismatch: {path}")

    start_u64 = np.memmap(matrix_dir / files["start"]["path"], mode="r", dtype="<u8")
    if len(start_u64) != columns + 1 or int(start_u64[-1]) != nnz:
        raise ValueError("invalid CSC start array")
    if nnz > np.iinfo(np.int32).max:
        raise ValueError(f"one signed matrix block has {nnz} nnz > HighsInt limit")
    start = np.asarray(start_u64, dtype=np.int32)
    index_u32 = np.memmap(matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    if len(index_u32) != nnz or (nnz and int(index_u32.max()) >= rows):
        raise ValueError("invalid CSC row array")
    index = index_u32.view(np.int32)
    exact_values = np.memmap(matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    if len(exact_values) != nnz:
        raise ValueError("invalid CSC value array")
    target_exact = np.memmap(matrix_dir / files["target"]["path"], mode="r", dtype="<i8")
    if len(target_exact) != rows:
        raise ValueError("invalid target array")
    source = np.memmap(matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    if len(source) != columns:
        raise ValueError("invalid source-index array")

    # HiGHS requires float64 values. Keep one block resident, pass it once with
    # positive sign, negate it in place, then pass the negative block. HiGHS
    # copies each block internally, avoiding a second Python-side nnz array.
    values = np.empty(nnz, dtype=np.float64)
    chunk = 16_000_000
    for begin in range(0, nnz, chunk):
        end = min(begin + chunk, nnz)
        values[begin:end] = exact_values[begin:end]
    target = np.asarray(target_exact, dtype=np.float64)

    highs = highspy.Highs()
    options = {
        "log_file": str(log),
        "output_flag": True,
        "solver": "simplex",
        "simplex_strategy": 1,
        "parallel": "off",
        "threads": threads,
        "presolve": "on",
        "primal_feasibility_tolerance": feasibility_tolerance,
        "dual_feasibility_tolerance": feasibility_tolerance,
        "random_seed": 20260903,
    }
    for name, value in options.items():
        check(highs.setOptionValue(name, value), f"setOptionValue({name})")

    empty_i32 = np.empty(0, dtype=np.int32)
    empty_f64 = np.empty(0, dtype=np.float64)
    zero_start = np.zeros(rows + 1, dtype=np.int32)
    check(highs.addRows(rows, target, target, 0, zero_start, empty_i32, empty_f64), "addRows")
    costs = np.ones(columns, dtype=np.float64)
    lower = np.zeros(columns, dtype=np.float64)
    upper = np.full(columns, highspy.kHighsInf, dtype=np.float64)
    check(highs.addCols(columns, costs, lower, upper, nnz, start, index, values), "addCols(+)")
    values *= -1.0
    check(highs.addCols(columns, costs, lower, upper, nnz, start, index, values), "addCols(-)")
    del values

    initial = None
    if initial_witness is not None:
        witness = json.loads(initial_witness.read_text())
        position_of = {int(source_index): position for position, source_index in enumerate(source)}
        initial_indices = []
        initial_values = []
        for entry in witness.get("coefficients", []):
            coefficient = Fraction(str(entry["coefficient"]))
            if not coefficient:
                continue
            source_index = int(entry["column"])
            if source_index not in position_of:
                raise ValueError(f"initial witness source {source_index} is absent from the LP family")
            position = position_of[source_index]
            initial_indices.append(position if coefficient > 0 else columns + position)
            initial_values.append(float(abs(coefficient)))
        check(
            highs.setSolution(
                len(initial_indices),
                np.asarray(initial_indices, dtype=np.int32),
                np.asarray(initial_values, dtype=np.float64),
            ),
            "setSolution(initial witness)",
        )
        initial = {
            "path": str(initial_witness),
            "sha256": sha256(initial_witness),
            "support_numerator": len(initial_indices),
            "support_denominator": columns,
        }

    all_columns = np.arange(2 * columns, dtype=np.int32)
    reports = []
    weights = np.ones(columns, dtype=np.float64)
    for round_number in range(rounds + 1):
        phase = time.monotonic()
        if round_number:
            doubled = np.concatenate((weights, weights))
            check(highs.changeColsCost(2 * columns, all_columns, doubled), "changeColsCost")
        check(highs.run(), "run")
        status = highs.getModelStatus()
        if status != highspy.HighsModelStatus.kOptimal:
            raise RuntimeError(f"round {round_number} model status {highs.modelStatusToString(status)}")
        solution = np.asarray(highs.getSolution().col_value, dtype=np.float64)
        signed = solution[:columns] - solution[columns:]
        support_positions = np.flatnonzero(np.abs(signed) > support_threshold)
        reports.append(
            {
                "round": round_number,
                "kind": "base_l1" if round_number == 0 else "reweighted_l1",
                "seconds": time.monotonic() - phase,
                "model_status": highs.modelStatusToString(status),
                "support_threshold_absolute": support_threshold,
                "support_numerator": int(len(support_positions)),
                "support_denominator": columns,
                "max_abs_coefficient": float(np.max(np.abs(signed))),
                "min_abs_retained_coefficient": (
                    float(np.min(np.abs(signed[support_positions]))) if len(support_positions) else None
                ),
                "highs_info": info_fields(highs.getInfo()),
                "candidate": [
                    {"column_position": int(position), "source_index": int(source[position]), "coefficient": float(signed[position])}
                    for position in support_positions
                ],
            }
        )
        magnitudes = np.abs(signed)
        raw_weights = 1.0 / (magnitudes + reweight_epsilon)
        positive = magnitudes[magnitudes > support_threshold]
        normalizer = float(np.median(1.0 / (positive + reweight_epsilon))) if len(positive) else 1.0
        weights = np.minimum(raw_weights / normalizer, reweight_cap)
        print(
            f"L1_ROUND round={round_number}/{rounds} support={len(support_positions)}/{columns} "
            f"objective={reports[-1]['highs_info'].get('objective_function_value')} "
            f"seconds={reports[-1]['seconds']:.3f}",
            flush=True,
        )

    report = {
        "schema": "max11-sparse-l1-report-v1",
        "verdict": "CANDIDATES",
        "exact": False,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "rows_denominator": rows,
        "columns_denominator": columns,
        "matrix_nonzeros_denominator": nnz,
        "signed_variable_columns_denominator": 2 * columns,
        "signed_matrix_nonzeros_denominator": 2 * nnz,
        "solver": "HiGHS serial dual simplex",
        "highs_version": highs.version(),
        "options": options,
        "reweighted_rounds_numerator": rounds,
        "reweighted_rounds_denominator": rounds,
        "reweight_epsilon_absolute": reweight_epsilon,
        "reweight_cap": reweight_cap,
        "support_threshold_absolute": support_threshold,
        "initial_feasible_witness": initial,
        "rounds": reports,
        "total_seconds": time.monotonic() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": "Floating LP output only proposes supports; no identity is claimed until an exact rational solve and all-row verification pass.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--threads", type=int, default=1)
    parser.add_argument("--reweighted-rounds", type=int, default=4)
    parser.add_argument("--feasibility-tolerance", type=float, default=1e-8)
    parser.add_argument("--support-threshold", type=float, default=1e-12)
    parser.add_argument("--reweight-epsilon", type=float, default=1e-9)
    parser.add_argument("--reweight-cap", type=float, default=1e6)
    parser.add_argument("--initial-witness", type=Path)
    args = parser.parse_args()
    report = solve(
        args.matrix_dir,
        args.output,
        args.log,
        args.threads,
        args.reweighted_rounds,
        args.feasibility_tolerance,
        args.support_threshold,
        args.reweight_epsilon,
        args.reweight_cap,
        args.initial_witness,
    )
    print(json.dumps({key: report[key] for key in ("schema", "verdict", "total_seconds", "max_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
