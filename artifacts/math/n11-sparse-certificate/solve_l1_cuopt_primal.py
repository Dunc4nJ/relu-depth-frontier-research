#!/usr/bin/env python3
"""GPU split-variable L1 discovery with an exact-witness warm start.

This converts the checked exact CSC matrix A to CSR once and solves
``min w^T(c+ + c-)`` subject to ``[A,-A](c+,c-)=b`` with cuOpt PDLP.
The optional exact witness supplies a genuinely feasible starting point.  The
floating supports are proposals only; exact selection/lifting remains required.
"""

from __future__ import annotations

import argparse
import json
import resource
import time
from fractions import Fraction
from pathlib import Path

import numpy as np
import scipy.sparse

from solve_l1_cuopt_dual import load_checked_matrix, sha256


def split_initial_witness(path: Path, source: np.ndarray, columns: int) -> tuple[np.ndarray, dict]:
    witness = json.loads(path.read_text())
    position_of = {int(source_index): position for position, source_index in enumerate(source)}
    initial = np.zeros(2 * columns, dtype=np.float64)
    support = 0
    for entry in witness.get("coefficients", []):
        coefficient = Fraction(str(entry["coefficient"]))
        if not coefficient:
            continue
        support += 1
        source_index = int(entry["column"])
        if source_index not in position_of:
            raise ValueError(f"initial witness source {source_index} is absent from the LP family")
        position = position_of[source_index]
        initial[position if coefficient > 0 else columns + position] = float(abs(coefficient))
    return initial, {
        "path": str(path),
        "sha256": sha256(path),
        "support_numerator": support,
        "support_denominator": columns,
    }


def solve(
    matrix_dir: Path,
    output: Path,
    log: Path,
    initial_witness: Path,
    rounds: int,
    optimality_tolerance: float,
    support_threshold: float,
    reweight_epsilon: float,
    reweight_cap: float,
    time_limit: float,
    cpu_threads: int,
    pdlp_mode: str,
    formulation: str,
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
    start = np.asarray(start_u64, dtype=np.int32)
    index = index_u32.view(np.int32)
    values = np.empty(nnz, dtype=np.float64)
    chunk = 16_000_000
    for begin in range(0, nnz, chunk):
        end = min(begin + chunk, nnz)
        values[begin:end] = exact_values[begin:end]
    target = np.asarray(target_exact, dtype=np.float64)
    csc = scipy.sparse.csc_matrix((values, index, start), shape=(rows, columns), copy=False)
    a_csr = csc.tocsr()
    if formulation == "split":
        matrix = scipy.sparse.hstack((a_csr, -a_csr), format="csr")
        constraint_lower = target
        constraint_upper = target
        variable_lower = np.zeros(2 * columns, dtype=np.float64)
        model_nnz = 2 * nnz
    else:
        zero = scipy.sparse.csr_matrix((rows, columns), dtype=np.float64)
        top = scipy.sparse.hstack((a_csr, zero), format="csr")
        positions = np.arange(columns, dtype=np.int32)
        abs_row = np.repeat(np.arange(2 * columns, dtype=np.int32), 2)
        abs_column = np.empty(4 * columns, dtype=np.int32)
        abs_column[0::4] = positions
        abs_column[1::4] = columns + positions
        abs_column[2::4] = positions
        abs_column[3::4] = columns + positions
        abs_value = np.tile(np.asarray((1.0, -1.0, -1.0, -1.0)), columns)
        absolute = scipy.sparse.coo_matrix(
            (abs_value, (abs_row, abs_column)), shape=(2 * columns, 2 * columns)
        ).tocsr()
        matrix = scipy.sparse.vstack((top, absolute), format="csr")
        constraint_lower = np.concatenate((target, np.full(2 * columns, -np.inf)))
        constraint_upper = np.concatenate((target, np.zeros(2 * columns)))
        variable_lower = np.concatenate((np.full(columns, -np.inf), np.zeros(columns)))
        model_nnz = nnz + 4 * columns
        del top, absolute, zero
    if matrix.nnz != model_nnz or matrix.indices.dtype != np.int32 or matrix.indptr.dtype != np.int32:
        raise RuntimeError(f"unexpected {formulation} CSR representation")
    del csc, values

    initial_split, initial_report = split_initial_witness(initial_witness, source, columns)
    initial_signed = initial_split[:columns] - initial_split[columns:]
    initial = (
        initial_split
        if formulation == "split"
        else np.concatenate((initial_signed, np.abs(initial_signed)))
    )
    initial_residual = np.asarray(a_csr @ initial_signed - target)
    initial_report.update({
        "max_abs_floating_residual": float(np.max(np.abs(initial_residual))),
        "nonzero_floating_residual_numerator": int(np.count_nonzero(initial_residual)),
        "row_denominator": rows,
    })

    model = lp.DataModel()
    model.set_csr_constraint_matrix(matrix.data, matrix.indices, matrix.indptr)
    model.set_constraint_lower_bounds(constraint_lower)
    model.set_constraint_upper_bounds(constraint_upper)
    model.set_variable_lower_bounds(variable_lower)
    model.set_variable_upper_bounds(np.full(2 * columns, np.inf))
    model.set_initial_primal_solution(initial)

    settings = lp.SolverSettings()
    pdlp_modes = {
        "stable3": lp.PDLPSolverMode.Stable3,
        "methodical1": lp.PDLPSolverMode.Methodical1,
        "fast1": lp.PDLPSolverMode.Fast1,
    }
    settings.set_parameter(parameter.CUOPT_METHOD, lp.SolverMethod.PDLP)
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
        costs = (
            np.concatenate((weights, weights))
            if formulation == "split"
            else np.concatenate((np.zeros(columns), weights))
        )
        model.set_objective_coefficients(costs)
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
        split = np.asarray(solution.get_primal_solution(), dtype=np.float64)
        signed = split[:columns] - split[columns:] if formulation == "split" else split[:columns]
        positions = np.flatnonzero(np.abs(signed) > support_threshold)
        residual = np.asarray(a_csr @ signed - target)
        stats = solution.get_lp_stats()
        report = {
            "round": round_number,
            "kind": "base_l1" if round_number == 0 else "reweighted_l1",
            "seconds": time.monotonic() - phase,
            "model_status": status,
            "termination_reason": str(solution.get_termination_reason()),
            "support_threshold_absolute": support_threshold,
            "support_numerator": int(len(positions)),
            "support_denominator": columns,
            "max_abs_coefficient": float(np.max(np.abs(signed))),
            "min_abs_retained_coefficient": float(np.min(np.abs(signed[positions]))) if len(positions) else None,
            "floating_residual_max_abs": float(np.max(np.abs(residual))),
            "floating_nonzero_residual_numerator": int(np.count_nonzero(residual)),
            "floating_residual_denominator": rows,
            "primal_objective": float(solution.get_primal_objective()),
            "dual_objective": float(solution.get_dual_objective()),
            "lp_stats": {key: float(value) if isinstance(value, float) else int(value) for key, value in stats.items()},
            "candidate": [
                {
                    "column_position": int(position),
                    "source_index": int(source[position]),
                    "coefficient": float(signed[position]),
                }
                for position in positions
            ],
        }
        reports.append(report)
        print(
            f"CUOPT_PRIMAL_L1_ROUND round={round_number}/{rounds} support={len(positions)}/{columns} "
            f"objective={report['primal_objective']} max_residual={report['floating_residual_max_abs']} "
            f"seconds={report['seconds']:.3f}",
            flush=True,
        )
        magnitudes = np.abs(signed)
        raw_weights = 1.0 / (magnitudes + reweight_epsilon)
        positive = magnitudes[magnitudes > support_threshold]
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
        "lp_formulation": f"{formulation}_primal_weighted_basis_pursuit",
        "model_rows_denominator": rows if formulation == "split" else rows + 2 * columns,
        "model_columns_denominator": 2 * columns,
        "model_nonzeros_denominator": model_nnz,
        "solver": f"NVIDIA cuOpt 26.2.0 PDLP {pdlp_mode}, no presolve/crossover",
        "options": {
            "optimality_tolerance": optimality_tolerance,
            "time_limit_seconds_per_round": time_limit,
            "cpu_threads": cpu_threads,
            "support_threshold_absolute": support_threshold,
        },
        "reweighted_rounds_numerator": rounds,
        "reweighted_rounds_denominator": rounds,
        "reweight_epsilon_absolute": reweight_epsilon,
        "reweight_cap": reweight_cap,
        "support_threshold_absolute": support_threshold,
        "initial_feasible_witness": initial_report,
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
    parser.add_argument("--initial-witness", type=Path, required=True)
    parser.add_argument("--reweighted-rounds", type=int, default=4)
    parser.add_argument("--optimality-tolerance", type=float, default=1e-8)
    parser.add_argument("--support-threshold", type=float, default=1e-12)
    parser.add_argument("--reweight-epsilon", type=float, default=1e-9)
    parser.add_argument("--reweight-cap", type=float, default=1e6)
    parser.add_argument("--time-limit", type=float, default=3600.0)
    parser.add_argument("--cpu-threads", type=int, default=16)
    parser.add_argument("--pdlp-mode", choices=("stable3", "methodical1", "fast1"), default="stable3")
    parser.add_argument("--formulation", choices=("split", "epigraph"), default="epigraph")
    args = parser.parse_args()
    report = solve(
        args.matrix_dir,
        args.output,
        args.log,
        args.initial_witness,
        args.reweighted_rounds,
        args.optimality_tolerance,
        args.support_threshold,
        args.reweight_epsilon,
        args.reweight_cap,
        args.time_limit,
        args.cpu_threads,
        args.pdlp_mode,
        args.formulation,
    )
    print(json.dumps({key: report[key] for key in ("schema", "verdict", "total_seconds", "max_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
