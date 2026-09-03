#!/usr/bin/env python3
"""First-order basis pursuit on a checked CSC matrix, with exact gates downstream.

The ADMM x-step is the Euclidean projection onto ``A x = b``.  A Cholesky
factor of ``A A^T`` is built once and reused.  The z-step is weighted soft
thresholding.  Floating candidates remain discovery output only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import resource
import time
from fractions import Fraction
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_checked_dense(matrix_dir: Path) -> tuple[Path, dict, np.ndarray, np.ndarray, np.ndarray]:
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
    start = np.memmap(matrix_dir / files["start"]["path"], mode="r", dtype="<u8")
    index = np.memmap(matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    value = np.memmap(matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    source = np.memmap(matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    target = np.asarray(
        np.memmap(matrix_dir / files["target"]["path"], mode="r", dtype="<i8"),
        dtype=np.float64,
    )
    if len(start) != columns + 1 or int(start[-1]) != nnz or len(index) != nnz or len(value) != nnz:
        raise ValueError("CSC dimension mismatch")
    dense = np.zeros((rows, columns), dtype=np.float64, order="F")
    for column in range(columns):
        begin, end = int(start[column]), int(start[column + 1])
        dense[index[begin:end], column] = value[begin:end]
    return meta_path, meta, dense, target, np.asarray(source, dtype=np.uint64)


def soft_threshold(values: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    return np.sign(values) * np.maximum(np.abs(values) - thresholds, 0.0)


def solve(
    matrix_dir: Path,
    output: Path,
    log_path: Path,
    rounds: int,
    max_iterations: int,
    absolute_tolerance: float,
    relative_tolerance: float,
    support_threshold: float,
    candidate_cap: int,
    rho: float,
    reweight_epsilon: float,
    reweight_cap: float,
    reweight_floor: float,
    initial_witness: Path | None,
    initial_reweight_from_witness: bool,
    adaptive_rho: bool,
    rho_min: float,
    rho_max: float,
) -> dict:
    import scipy
    import scipy.linalg

    started = time.monotonic()
    meta_path, meta, matrix, target, source = load_checked_dense(matrix_dir)
    input_rows, columns = matrix.shape
    if not 0 < candidate_cap <= columns:
        raise ValueError("candidate_cap must be in 1..columns")
    if rho <= 0 or max_iterations <= 0:
        raise ValueError("rho and max_iterations must be positive")
    row_norm = np.linalg.norm(matrix, axis=1)
    active_rows = row_norm != 0
    if np.any(target[~active_rows] != 0):
        raise ValueError("ADMM projection matrix has an empty row with a nonzero target")
    matrix = matrix[active_rows, :]
    target = target[active_rows]
    row_norm = row_norm[active_rows]
    rows = matrix.shape[0]
    matrix /= row_norm[:, None]
    target /= row_norm
    gram_started = time.monotonic()
    gram = matrix @ matrix.T
    factor = scipy.linalg.cho_factor(gram, lower=True, overwrite_a=True, check_finite=False)
    gram_seconds = time.monotonic() - gram_started
    del gram

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_stream = log_path.open("w", buffering=1)

    def log(message: str) -> None:
        print(message, file=log_stream, flush=True)
        print(message, flush=True)

    def affine_projection(values: np.ndarray) -> tuple[np.ndarray, float]:
        residual = matrix @ values - target
        multiplier = scipy.linalg.cho_solve(factor, residual, check_finite=False)
        projected = values - matrix.T @ multiplier
        projected_residual = float(np.max(np.abs(matrix @ projected - target)))
        return projected, projected_residual

    log(
        f"ADMM_START rows={rows} columns={columns} nnz={meta['nonzeros_denominator']} "
        f"rounds={rounds + 1} max_iterations={max_iterations} rho={rho}"
    )
    initial_rho = rho
    current_rho = rho
    x = np.zeros(columns, dtype=np.float64)
    z = np.zeros(columns, dtype=np.float64)
    u = np.zeros(columns, dtype=np.float64)
    initial_witness_record = None
    weights = np.ones(columns, dtype=np.float64)
    if initial_reweight_from_witness:
        if initial_witness is None:
            raise ValueError("initial_reweight_from_witness requires initial_witness")
        document = json.loads(initial_witness.read_text())
        position_of = {int(source_index): position for position, source_index in enumerate(source)}
        seed_positions = []
        for entry in document.get("coefficients", []):
            if not Fraction(str(entry["coefficient"])):
                continue
            source_index = int(entry["column"])
            if source_index not in position_of:
                raise ValueError(f"initial witness source {source_index} is absent from the LP family")
            seed_positions.append(position_of[source_index])
        weights.fill(reweight_cap)
        weights[np.asarray(seed_positions, dtype=np.int64)] = 1.0
        initial_witness_record = {
            "path": str(initial_witness),
            "sha256": sha256(initial_witness),
            "support_numerator": len(seed_positions),
            "support_denominator": columns,
            "use": "round-0 support-membership weights only; coefficients are not a primal start",
        }
    reports = []
    for round_number in range(rounds + 1):
        round_started = time.monotonic()
        converged = False
        projected_residual = float("inf")
        r_norm = float("inf")
        s_norm = float("inf")
        eps_primal = float("inf")
        eps_dual = float("inf")
        for iteration in range(1, max_iterations + 1):
            x, projected_residual = affine_projection(z - u)
            old_z = z
            z = soft_threshold(x + u, weights / current_rho)
            u += x - z
            if iteration == 1 or iteration % 25 == 0 or iteration == max_iterations:
                r_norm = float(np.linalg.norm(x - z))
                s_norm = float(current_rho * np.linalg.norm(z - old_z))
                eps_primal = float(
                    np.sqrt(columns) * absolute_tolerance
                    + relative_tolerance * max(np.linalg.norm(x), np.linalg.norm(z))
                )
                eps_dual = float(
                    np.sqrt(columns) * absolute_tolerance
                    + relative_tolerance * np.linalg.norm(current_rho * u)
                )
                log(
                    f"ADMM_ITER round={round_number}/{rounds} iteration={iteration}/{max_iterations} "
                    f"objective={float(weights @ np.abs(z)):.17g} "
                    f"r={r_norm:.6g}/{eps_primal:.6g} s={s_norm:.6g}/{eps_dual:.6g} "
                    f"projection_inf={projected_residual:.6g} rho={current_rho:.6g} "
                    f"support={int(np.count_nonzero(np.abs(z) > support_threshold))}/{columns}"
                )
                if r_norm <= eps_primal and s_norm <= eps_dual:
                    converged = True
                    break
                if adaptive_rho and r_norm > 10.0 * s_norm and current_rho < rho_max:
                    old_rho = current_rho
                    current_rho = min(rho_max, current_rho * 2.0)
                    u *= old_rho / current_rho
                elif adaptive_rho and s_norm > 10.0 * r_norm and current_rho > rho_min:
                    old_rho = current_rho
                    current_rho = max(rho_min, current_rho / 2.0)
                    u *= old_rho / current_rho
        magnitudes = np.abs(z)
        threshold_positions = np.flatnonzero(magnitudes > support_threshold)
        if len(threshold_positions) > candidate_cap:
            selected = np.argpartition(magnitudes, -candidate_cap)[-candidate_cap:]
            positions = selected[np.argsort(magnitudes[selected])[::-1]]
        else:
            positions = threshold_positions[np.argsort(magnitudes[threshold_positions])[::-1]]
        reports.append(
            {
                "round": round_number,
                "kind": (
                    "witness_seeded_reweighted_l1_admm"
                    if round_number == 0 and initial_reweight_from_witness
                    else "base_l1_admm"
                    if round_number == 0
                    else "reweighted_l1_admm"
                ),
                "converged": converged,
                "iterations_numerator": iteration,
                "iterations_denominator": max_iterations,
                "seconds": time.monotonic() - round_started,
                "weighted_objective": float(weights @ magnitudes),
                "primal_consensus_residual_l2": r_norm,
                "primal_consensus_tolerance_l2": eps_primal,
                "dual_residual_l2": s_norm,
                "dual_tolerance_l2": eps_dual,
                "affine_projection_residual_infinity": projected_residual,
                "rho_final": current_rho,
                "support_threshold_absolute": support_threshold,
                "threshold_support_numerator": len(threshold_positions),
                "threshold_support_denominator": columns,
                "candidate_cap": candidate_cap,
                "support_numerator": len(positions),
                "support_denominator": columns,
                "candidate": [
                    {
                        "column_position": int(position),
                        "source_index": int(source[position]),
                        "coefficient": float(z[position]),
                    }
                    for position in positions
                ],
            }
        )
        raw_weights = 1.0 / (magnitudes + reweight_epsilon)
        positive = magnitudes[magnitudes > support_threshold]
        normalizer = float(np.median(1.0 / (positive + reweight_epsilon))) if len(positive) else 1.0
        weights = np.clip(raw_weights / normalizer, reweight_floor, reweight_cap)
        x = z.copy()
        u.fill(0.0)
        partial = {
            "schema": "max11-sparse-l1-admm-partial-report-v1",
            "verdict": "CANDIDATES_PARTIAL",
            "exact": False,
            "matrix_report": str(meta_path),
            "matrix_report_sha256": sha256(meta_path),
            "rows_denominator": input_rows,
            "projection_rows_numerator": rows,
            "columns_denominator": columns,
            "matrix_nonzeros_denominator": int(meta["nonzeros_denominator"]),
            "rounds_requested_denominator": rounds + 1,
            "rounds_completed_numerator": round_number + 1,
            "rounds": reports,
            "no_claim": "First-order floating candidates require exact modular selection and exact all-row verification.",
        }
        Path(str(output) + ".partial.json").write_text(json.dumps(partial, indent=2, sort_keys=True) + "\n")

    report = {
        "schema": "max11-sparse-l1-admm-report-v1",
        "verdict": "CANDIDATES",
        "exact": False,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "rows_denominator": input_rows,
        "projection_rows_numerator": rows,
        "columns_denominator": columns,
        "matrix_nonzeros_denominator": int(meta["nonzeros_denominator"]),
        "solver": "ADMM basis pursuit with reusable dense Cholesky affine projection",
        "numpy_version": np.__version__,
        "scipy_version": scipy.__version__,
        "row_scaling": "divide each equality by its float64 L2 row norm (exact-equivalent search preconditioner)",
        "gram_cholesky_seconds": gram_seconds,
        "rho_initial": initial_rho,
        "rho_final": current_rho,
        "rho_min": rho_min,
        "rho_max": rho_max,
        "rho_adaptation": (
            "every 25 iterations: double when primal residual > 10x dual; halve when dual > 10x primal; preserve the unscaled dual"
            if adaptive_rho
            else "disabled"
        ),
        "absolute_tolerance": absolute_tolerance,
        "relative_tolerance": relative_tolerance,
        "support_threshold_absolute": support_threshold,
        "candidate_cap": candidate_cap,
        "reweighted_rounds_numerator": rounds,
        "reweighted_rounds_denominator": rounds,
        "reweight_epsilon_absolute": reweight_epsilon,
        "reweight_cap": reweight_cap,
        "reweight_floor": reweight_floor,
        "initial_witness": initial_witness_record,
        "initial_reweight_from_witness": initial_reweight_from_witness,
        "rounds": reports,
        "total_seconds": time.monotonic() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": "Floating ADMM output only proposes supports; no identity is claimed until exact rational solve and all-row verification pass.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    log_stream.close()
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("--reweighted-rounds", type=int, default=4)
    parser.add_argument("--max-iterations", type=int, default=2000)
    parser.add_argument("--absolute-tolerance", type=float, default=1e-10)
    parser.add_argument("--relative-tolerance", type=float, default=1e-8)
    parser.add_argument("--support-threshold", type=float, default=1e-10)
    parser.add_argument("--candidate-cap", type=int, required=True)
    parser.add_argument("--rho", type=float, default=1e8)
    parser.add_argument("--reweight-epsilon", type=float, default=1e-9)
    parser.add_argument("--reweight-cap", type=float, default=1e6)
    parser.add_argument("--reweight-floor", type=float, default=1e-6)
    parser.add_argument("--initial-witness", type=Path)
    parser.add_argument("--initial-reweight-from-witness", action="store_true")
    parser.add_argument("--adaptive-rho", action="store_true")
    parser.add_argument("--rho-min", type=float, default=1e-16)
    parser.add_argument("--rho-max", type=float, default=1e16)
    args = parser.parse_args()
    report = solve(
        args.matrix_dir,
        args.output,
        args.log,
        args.reweighted_rounds,
        args.max_iterations,
        args.absolute_tolerance,
        args.relative_tolerance,
        args.support_threshold,
        args.candidate_cap,
        args.rho,
        args.reweight_epsilon,
        args.reweight_cap,
        args.reweight_floor,
        args.initial_witness,
        args.initial_reweight_from_witness,
        args.adaptive_rho,
        args.rho_min,
        args.rho_max,
    )
    print(json.dumps({key: report[key] for key in ("schema", "verdict", "total_seconds", "max_rss_kib")}, indent=2))


if __name__ == "__main__":
    main()
