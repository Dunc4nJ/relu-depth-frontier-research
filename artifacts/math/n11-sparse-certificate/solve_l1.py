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
    formulation: str = "split",
    solver: str = "simplex",
    presolve: str = "on",
    reweight_solver: str = "same",
    initial_reweight_from_witness: bool = False,
    reweight_floor: float = 0.0,
    initial_basis: Path | None = None,
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

    if formulation not in ("split", "epigraph"):
        raise ValueError("formulation must be split or epigraph")
    if solver not in ("simplex", "ipm"):
        raise ValueError("solver must be simplex or ipm")
    if presolve not in ("on", "off"):
        raise ValueError("presolve must be on or off")
    if reweight_solver not in ("same", "simplex", "ipm"):
        raise ValueError("reweight_solver must be same, simplex, or ipm")
    if not 0.0 <= reweight_floor <= reweight_cap:
        raise ValueError("reweight_floor must be in [0, reweight_cap]")
    # HiGHS requires float64 values. Keep one block resident. The split model
    # passes it again with negative sign; the epigraph model uses free c and
    # explicit -t <= c <= t rows, halving the dominant matrix block.
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
        "solver": solver,
        "simplex_strategy": 1,
        "run_crossover": "on",
        "parallel": "off",
        "threads": threads,
        "presolve": presolve,
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
    if formulation == "split":
        costs = np.ones(columns, dtype=np.float64)
        lower = np.zeros(columns, dtype=np.float64)
        upper = np.full(columns, highspy.kHighsInf, dtype=np.float64)
        check(highs.addCols(columns, costs, lower, upper, nnz, start, index, values), "addCols(+)")
        values *= -1.0
        check(highs.addCols(columns, costs, lower, upper, nnz, start, index, values), "addCols(-)")
        model_rows = rows
        model_nnz = 2 * nnz
    else:
        zero_cost = np.zeros(columns, dtype=np.float64)
        free_lower = np.full(columns, -highspy.kHighsInf, dtype=np.float64)
        free_upper = np.full(columns, highspy.kHighsInf, dtype=np.float64)
        check(highs.addCols(columns, zero_cost, free_lower, free_upper, nnz, start, index, values), "addCols(c)")
        t_cost = np.ones(columns, dtype=np.float64)
        t_lower = np.zeros(columns, dtype=np.float64)
        t_upper = np.full(columns, highspy.kHighsInf, dtype=np.float64)
        zero_col_start = np.zeros(columns + 1, dtype=np.int32)
        check(highs.addCols(columns, t_cost, t_lower, t_upper, 0, zero_col_start, empty_i32, empty_f64), "addCols(t)")
        abs_lower = np.full(2 * columns, -highspy.kHighsInf, dtype=np.float64)
        abs_upper = np.zeros(2 * columns, dtype=np.float64)
        abs_start = np.arange(0, 4 * columns + 1, 2, dtype=np.int32)
        abs_index = np.empty(4 * columns, dtype=np.int32)
        abs_value = np.empty(4 * columns, dtype=np.float64)
        positions = np.arange(columns, dtype=np.int32)
        abs_index[0::4] = positions
        abs_index[1::4] = columns + positions
        abs_index[2::4] = positions
        abs_index[3::4] = columns + positions
        abs_value[0::4] = 1.0
        abs_value[1::4] = -1.0
        abs_value[2::4] = -1.0
        abs_value[3::4] = -1.0
        check(highs.addRows(2 * columns, abs_lower, abs_upper, 4 * columns, abs_start, abs_index, abs_value), "addRows(abs epigraph)")
        model_rows = rows + 2 * columns
        model_nnz = nnz + 4 * columns
    del values

    initial = None
    initial_magnitudes = np.zeros(columns, dtype=np.float64)
    if initial_witness is not None:
        witness = json.loads(initial_witness.read_text())
        position_of = {int(source_index): position for position, source_index in enumerate(source)}
        initial_indices = []
        initial_values = []
        initial_witness_support = 0
        for entry in witness.get("coefficients", []):
            coefficient = Fraction(str(entry["coefficient"]))
            if not coefficient:
                continue
            initial_witness_support += 1
            source_index = int(entry["column"])
            if source_index not in position_of:
                raise ValueError(f"initial witness source {source_index} is absent from the LP family")
            position = position_of[source_index]
            initial_magnitudes[position] = float(abs(coefficient))
            if formulation == "split":
                initial_indices.append(position if coefficient > 0 else columns + position)
                initial_values.append(float(abs(coefficient)))
            else:
                initial_indices.extend((position, columns + position))
                initial_values.extend((float(coefficient), float(abs(coefficient))))
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
            "support_numerator": initial_witness_support,
            "support_denominator": columns,
            "model_values_set": len(initial_indices),
        }

    if initial_reweight_from_witness and initial_witness is None:
        raise ValueError("initial_reweight_from_witness requires initial_witness")
    initial_basis_record = None
    if initial_basis is not None:
        if formulation != "split":
            raise ValueError("initial_basis is supported only for the split formulation")
        basis_report = json.loads(initial_basis.read_text())
        if basis_report.get("verdict") != "PASS" or basis_report.get("exact") != "modular":
            raise ValueError("initial basis report is not an exact modular PASS")
        if basis_report.get("matrix_report_sha256") != sha256(meta_path):
            raise ValueError("initial basis matrix SHA mismatch")
        basis_positions = [int(position) for position in basis_report["column_positions"]]
        basis_sources = [int(source_index) for source_index in basis_report["source_indices"]]
        basis_signs = basis_report.get("basis_signs")
        if basis_signs is None:
            basis_signs = [1] * len(basis_positions)
        basis_signs = [int(sign) for sign in basis_signs]
        if len(basis_positions) != rows or len(set(basis_positions)) != rows:
            raise ValueError(f"initial basis has {len(basis_positions)}/{rows} distinct columns")
        if any(position < 0 or position >= columns for position in basis_positions):
            raise ValueError("initial basis column position is out of range")
        if basis_sources != [int(source[position]) for position in basis_positions]:
            raise ValueError("initial basis source/position mismatch")
        if len(basis_signs) != rows or any(sign not in (-1, 1) for sign in basis_signs):
            raise ValueError("initial basis signs must contain one +/-1 entry per row")
        basis = highspy.HighsBasis()
        basis.valid = True
        basis.col_status = [highspy.HighsBasisStatus.kLower] * (2 * columns)
        for position, sign in zip(basis_positions, basis_signs, strict=True):
            basis.col_status[position if sign > 0 else columns + position] = highspy.HighsBasisStatus.kBasic
        basis.row_status = [highspy.HighsBasisStatus.kNonbasic] * rows
        check(highs.setBasis(basis), "setBasis(exact modular initial basis)")
        initial_basis_record = {
            "path": str(initial_basis),
            "sha256": sha256(initial_basis),
            "exact": "modular",
            "prime": int(basis_report["prime"]),
            "basis_columns_numerator": len(basis_positions),
            "basis_columns_denominator": rows,
            "negative_basis_columns_numerator": sum(sign < 0 for sign in basis_signs),
        }
    reports = []
    weights = np.ones(columns, dtype=np.float64)
    if initial_reweight_from_witness:
        # Seed only by exact support membership. Using the witness's potentially
        # enormous rational magnitudes here creates an ill-conditioned LP and
        # has no intrinsic sparsity meaning.
        weights = np.where(initial_magnitudes > support_threshold, 1.0, reweight_cap)
    for round_number in range(rounds + 1):
        phase = time.monotonic()
        if round_number or initial_reweight_from_witness:
            if round_number == 1 and reweight_solver != "same":
                check(highs.setOptionValue("solver", reweight_solver), "setOptionValue(reweight solver)")
            if formulation == "split":
                changed_cost = np.concatenate((weights, weights))
                changed_columns = np.arange(2 * columns, dtype=np.int32)
            else:
                changed_cost = weights
                changed_columns = np.arange(columns, 2 * columns, dtype=np.int32)
            check(highs.changeColsCost(len(changed_columns), changed_columns, changed_cost), "changeColsCost")
        check(highs.run(), "run")
        status = highs.getModelStatus()
        if status != highspy.HighsModelStatus.kOptimal:
            raise RuntimeError(f"round {round_number} model status {highs.modelStatusToString(status)}")
        solution = np.asarray(highs.getSolution().col_value, dtype=np.float64)
        signed = solution[:columns] - solution[columns:] if formulation == "split" else solution[:columns]
        support_positions = np.flatnonzero(np.abs(signed) > support_threshold)
        reports.append(
            {
                "round": round_number,
                "kind": (
                    "witness_seeded_reweighted_l1"
                    if round_number == 0 and initial_reweight_from_witness
                    else "base_l1"
                    if round_number == 0
                    else "reweighted_l1"
                ),
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
        weights = np.clip(raw_weights / normalizer, reweight_floor, reweight_cap)
        partial = {
            "schema": "max11-sparse-l1-partial-report-v1",
            "verdict": "CANDIDATES_PARTIAL",
            "exact": False,
            "matrix_report": str(meta_path),
            "matrix_report_sha256": sha256(meta_path),
            "rows_denominator": rows,
            "columns_denominator": columns,
            "matrix_nonzeros_denominator": nnz,
            "lp_formulation": formulation,
            "initial_solver": solver,
            "reweight_solver": reweight_solver,
            "initial_reweight_from_witness": initial_reweight_from_witness,
            "reweight_floor": reweight_floor,
            "initial_basis": initial_basis_record,
            "rounds_requested_denominator": rounds + 1,
            "rounds_completed_numerator": round_number + 1,
            "rounds": reports,
            "no_claim": "Incomplete floating LP output only proposes supports; exact modular selection and all-row verification remain required.",
        }
        Path(str(output) + ".partial.json").write_text(json.dumps(partial, indent=2, sort_keys=True) + "\n")
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
        "lp_formulation": formulation,
        "model_rows_denominator": model_rows,
        "model_columns_denominator": 2 * columns,
        "model_nonzeros_denominator": model_nnz,
        "solver": f"HiGHS {solver}" + (" serial dual" if solver == "simplex" else " with crossover"),
        "reweight_solver": reweight_solver,
        "initial_reweight_from_witness": initial_reweight_from_witness,
        "highs_version": highs.version(),
        "options": options,
        "reweighted_rounds_numerator": rounds,
        "reweighted_rounds_denominator": rounds,
        "reweight_epsilon_absolute": reweight_epsilon,
        "reweight_cap": reweight_cap,
        "reweight_floor": reweight_floor,
        "support_threshold_absolute": support_threshold,
        "initial_feasible_witness": initial,
        "initial_basis": initial_basis_record,
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
    parser.add_argument("--formulation", choices=("split", "epigraph"), default="split")
    parser.add_argument("--solver", choices=("simplex", "ipm"), default="simplex")
    parser.add_argument("--presolve", choices=("on", "off"), default="on")
    parser.add_argument("--reweight-solver", choices=("same", "simplex", "ipm"), default="same")
    parser.add_argument("--initial-reweight-from-witness", action="store_true")
    parser.add_argument("--reweight-floor", type=float, default=0.0)
    parser.add_argument("--initial-basis", type=Path)
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
        args.formulation,
        args.solver,
        args.presolve,
        args.reweight_solver,
        args.initial_reweight_from_witness,
        args.reweight_floor,
        args.initial_basis,
    )
    print(json.dumps({key: report[key] for key in ("schema", "verdict", "total_seconds", "max_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
