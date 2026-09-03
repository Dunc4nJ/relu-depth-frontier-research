#!/usr/bin/env python3
"""GPU basis-pursuit discovery through the bounded dual LP.

For ``min sum_j w_j |c_j|`` subject to ``A c = b``, this solves

    max b^T y  subject to  -w <= A^T y <= w.

The saved matrix is CSC for A, so its bytes are already CSR for the dual.  cuOpt's
dual multipliers on those constraints are candidate primal coefficients c.  All
output remains floating discovery evidence until select_exact_support.py and the
exact all-row verifier accept it.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_checked_matrix(matrix_dir: Path):
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
    index_u32 = np.memmap(matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    exact_values = np.memmap(matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    target_exact = np.memmap(matrix_dir / files["target"]["path"], mode="r", dtype="<i8")
    source = np.memmap(matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    if (
        len(start_u64) != columns + 1
        or int(start_u64[-1]) != nnz
        or len(index_u32) != nnz
        or len(exact_values) != nnz
        or len(target_exact) != rows
        or len(source) != columns
    ):
        raise ValueError("CSC dimension mismatch")
    if nnz > np.iinfo(np.int32).max:
        raise ValueError(f"dual CSR has {nnz} nnz > cuOpt int32 offset limit")
    if nnz and int(index_u32.max()) >= rows:
        raise ValueError("CSC row index outside matrix")
    return meta_path, meta, rows, columns, nnz, start_u64, index_u32, exact_values, target_exact, source


def constraint_activity(start, index, values, y):
    """Compute A[:,j]^T y for every original column j."""
    result = np.empty(len(start) - 1, dtype=np.float64)
    for column in range(len(result)):
        begin, end = int(start[column]), int(start[column + 1])
        result[column] = np.dot(values[begin:end], y[index[begin:end]])
    return result


def candidate_positions(
    primal_coefficients,
    activity,
    weights,
    coefficient_threshold: float,
    active_absolute_tolerance: float,
    active_relative_tolerance: float,
):
    """Keep nontrivial multipliers that are complementary-slackness active."""
    magnitudes = np.abs(primal_coefficients)
    slack = weights - np.abs(activity)
    active_tolerance = active_absolute_tolerance + active_relative_tolerance * weights
    mask = (magnitudes > coefficient_threshold) & (slack <= active_tolerance)
    return np.flatnonzero(mask), slack


def solve(
    matrix_dir: Path,
    output: Path,
    log: Path,
    rounds: int,
    optimality_tolerance: float,
    coefficient_threshold: float,
    active_absolute_tolerance: float,
    active_relative_tolerance: float,
    reweight_epsilon: float,
    reweight_cap: float,
    time_limit: float,
    cpu_threads: int,
    pdlp_mode: str,
) -> dict:
    from cuopt import linear_programming as lp
    from cuopt.linear_programming.solver import solver_parameters as parameter

    started = time.monotonic()
    (
        meta_path,
        meta,
        rows,
        columns,
        nnz,
        start_u64,
        index_u32,
        exact_values,
        target_exact,
        source,
    ) = load_checked_matrix(matrix_dir)

    # The CSC of A is the CSR of A^T.  cuOpt consumes float64 values and signed
    # int32 indices/offsets; retain the exact byte arrays for custody reporting.
    start = np.asarray(start_u64, dtype=np.int32)
    index = index_u32.view(np.int32)
    values = np.empty(nnz, dtype=np.float64)
    chunk = 16_000_000
    for begin in range(0, nnz, chunk):
        end = min(begin + chunk, nnz)
        values[begin:end] = exact_values[begin:end]
    target = np.asarray(target_exact, dtype=np.float64)

    # Positive row scaling of the dual constraints is exactly equivalent and
    # materially reduces the 1..50,000,000 coefficient range.  The multiplier
    # returned for scaled constraint j must be divided by this scale to recover
    # the original primal coefficient c_j.
    constraint_scale = np.empty(columns, dtype=np.float64)
    for column in range(columns):
        begin, end = int(start[column]), int(start[column + 1])
        scale = float(np.max(np.abs(values[begin:end]))) if end > begin else 1.0
        constraint_scale[column] = max(scale, 1.0)
        values[begin:end] /= constraint_scale[column]

    model = lp.DataModel()
    model.set_csr_constraint_matrix(values, index, start)
    model.set_objective_coefficients(target)
    model.set_variable_lower_bounds(np.full(rows, -np.inf, dtype=np.float64))
    model.set_variable_upper_bounds(np.full(rows, np.inf, dtype=np.float64))
    model.set_maximize(True)

    settings = lp.SolverSettings()
    settings.set_parameter(parameter.CUOPT_METHOD, lp.SolverMethod.PDLP)
    pdlp_modes = {
        "stable3": lp.PDLPSolverMode.Stable3,
        "methodical1": lp.PDLPSolverMode.Methodical1,
        "fast1": lp.PDLPSolverMode.Fast1,
    }
    settings.set_parameter(parameter.CUOPT_PDLP_SOLVER_MODE, pdlp_modes[pdlp_mode])
    settings.set_parameter(parameter.CUOPT_PRESOLVE, 0)
    settings.set_parameter(parameter.CUOPT_CROSSOVER, 0)
    settings.set_parameter(parameter.CUOPT_LOG_FILE, str(log))
    settings.set_parameter(parameter.CUOPT_LOG_TO_CONSOLE, True)
    settings.set_parameter(parameter.CUOPT_NUM_CPU_THREADS, cpu_threads)
    settings.set_parameter(parameter.CUOPT_TIME_LIMIT, time_limit)
    settings.set_optimality_tolerance(optimality_tolerance)

    reports = []
    weights = np.ones(columns, dtype=np.float64)
    prior_solution = None
    for round_number in range(rounds + 1):
        phase = time.monotonic()
        scaled_bounds = weights / constraint_scale
        model.set_constraint_lower_bounds(-scaled_bounds)
        model.set_constraint_upper_bounds(scaled_bounds)
        if prior_solution is not None:
            model.set_initial_primal_solution(prior_solution.get_primal_solution())
            model.set_initial_dual_solution(prior_solution.get_dual_solution())
            settings.set_pdlp_warm_start_data(prior_solution.get_pdlp_warm_start_data())
        solution = lp.Solve(model, settings)
        status = str(solution.get_termination_status()).split(".")[-1]
        if status not in ("Optimal", "PrimalFeasible"):
            raise RuntimeError(
                f"cuOpt round {round_number} status {status}: "
                f"{solution.get_termination_reason()} / {solution.get_error_message()}"
            )
        y = np.asarray(solution.get_primal_solution(), dtype=np.float64)
        scaled_multipliers = np.asarray(solution.get_dual_solution(), dtype=np.float64)
        primal_coefficients = scaled_multipliers / constraint_scale
        if len(y) != rows or len(primal_coefficients) != columns:
            raise RuntimeError("cuOpt returned unexpected primal/dual dimensions")
        activity = constraint_activity(start, index, values, y)
        positions, slack = candidate_positions(
            primal_coefficients,
            activity,
            scaled_bounds,
            coefficient_threshold,
            active_absolute_tolerance,
            active_relative_tolerance,
        )
        multiplier_positions = np.flatnonzero(np.abs(primal_coefficients) > coefficient_threshold)
        active_positions = np.flatnonzero(
            slack <= active_absolute_tolerance + active_relative_tolerance * scaled_bounds
        )
        lp_stats = solution.get_lp_stats()
        report = {
            "round": round_number,
            "kind": "base_l1" if round_number == 0 else "reweighted_l1",
            "seconds": time.monotonic() - phase,
            "model_status": status,
            "termination_reason": str(solution.get_termination_reason()),
            "support_threshold_absolute": coefficient_threshold,
            "active_absolute_tolerance": active_absolute_tolerance,
            "active_relative_tolerance": active_relative_tolerance,
            "support_numerator": int(len(positions)),
            "support_denominator": columns,
            "multiplier_support_numerator": int(len(multiplier_positions)),
            "active_constraints_numerator": int(len(active_positions)),
            "max_abs_coefficient": float(np.max(np.abs(primal_coefficients))),
            "min_abs_retained_coefficient": (
                float(np.min(np.abs(primal_coefficients[positions]))) if len(positions) else None
            ),
            "max_active_slack": float(np.max(slack[positions])) if len(positions) else None,
            "min_slack_all_constraints": float(np.min(slack)),
            "dual_constraint_scaling": "each A column divided by its maximum absolute entry; returned multiplier divided by the same scale",
            "primal_objective": float(solution.get_primal_objective()),
            "dual_objective": float(solution.get_dual_objective()),
            "lp_stats": {key: float(value) if isinstance(value, float) else int(value) for key, value in lp_stats.items()},
            "candidate": [
                {
                    "column_position": int(position),
                    "source_index": int(source[position]),
                    "coefficient": float(primal_coefficients[position]),
                    "dual_bound_slack": float(slack[position]),
                }
                for position in positions
            ],
        }
        reports.append(report)
        print(
            f"CUOPT_L1_ROUND round={round_number}/{rounds} support={len(positions)}/{columns} "
            f"multipliers={len(multiplier_positions)}/{columns} active={len(active_positions)}/{columns} "
            f"objective={report['dual_objective']} seconds={report['seconds']:.3f}",
            flush=True,
        )
        magnitudes = np.abs(primal_coefficients)
        raw_weights = 1.0 / (magnitudes + reweight_epsilon)
        positive = magnitudes[magnitudes > coefficient_threshold]
        normalizer = float(np.median(1.0 / (positive + reweight_epsilon))) if len(positive) else 1.0
        weights = np.minimum(raw_weights / normalizer, reweight_cap)
        prior_solution = solution

    report = {
        "schema": "max11-sparse-l1-report-v1",
        "verdict": "CANDIDATES",
        "exact": False,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "rows_denominator": rows,
        "columns_denominator": columns,
        "matrix_nonzeros_denominator": nnz,
        "lp_formulation": "bounded_dual_of_weighted_basis_pursuit",
        "model_rows_denominator": columns,
        "model_columns_denominator": rows,
        "model_nonzeros_denominator": nnz,
        "solver": f"NVIDIA cuOpt 26.2.0 PDLP {pdlp_mode}, no presolve/crossover",
        "options": {
            "optimality_tolerance": optimality_tolerance,
            "time_limit_seconds_per_round": time_limit,
            "cpu_threads": cpu_threads,
            "pdlp_mode": pdlp_mode,
            "coefficient_threshold_absolute": coefficient_threshold,
            "active_absolute_tolerance": active_absolute_tolerance,
            "active_relative_tolerance": active_relative_tolerance,
        },
        "reweighted_rounds_numerator": rounds,
        "reweighted_rounds_denominator": rounds,
        "reweight_epsilon_absolute": reweight_epsilon,
        "reweight_cap": reweight_cap,
        "support_threshold_absolute": coefficient_threshold,
        "initial_feasible_witness": None,
        "rounds": reports,
        "total_seconds": time.monotonic() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": "GPU floating LP output only proposes supports; no identity is claimed until exact rational lifting and all-row verification pass.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--reweighted-rounds", type=int, default=4)
    parser.add_argument("--optimality-tolerance", type=float, default=1e-10)
    parser.add_argument("--coefficient-threshold", type=float, default=1e-12)
    parser.add_argument("--active-absolute-tolerance", type=float, default=1e-8)
    parser.add_argument("--active-relative-tolerance", type=float, default=1e-8)
    parser.add_argument("--reweight-epsilon", type=float, default=1e-9)
    parser.add_argument("--reweight-cap", type=float, default=1e6)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--cpu-threads", type=int, default=16)
    parser.add_argument("--pdlp-mode", choices=("stable3", "methodical1", "fast1"), default="stable3")
    args = parser.parse_args()
    report = solve(
        args.matrix_dir,
        args.output,
        args.log,
        args.reweighted_rounds,
        args.optimality_tolerance,
        args.coefficient_threshold,
        args.active_absolute_tolerance,
        args.active_relative_tolerance,
        args.reweight_epsilon,
        args.reweight_cap,
        args.time_limit,
        args.cpu_threads,
        args.pdlp_mode,
    )
    print(json.dumps({key: report[key] for key in ("schema", "verdict", "total_seconds", "max_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
