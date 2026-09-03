#!/usr/bin/env python3
"""Select an exact modular column basis for a secondary LP matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import select_exact_support


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(
    matrix_dir: Path,
    pivot_report: Path,
    output: Path,
    prime: int,
    selection: str = "modular-rref",
) -> dict:
    started = time.monotonic()
    meta_path, _meta, rows, columns, start, index, value, source, target = (
        select_exact_support.load_matrix(matrix_dir)
    )
    pivot = json.loads(pivot_report.read_text())
    candidate_sources = [int(item) for item in pivot["sketches"][0]["pivot_columns"]]
    position_of = {int(source_index): position for position, source_index in enumerate(source)}
    missing = [source_index for source_index in candidate_sources if source_index not in position_of]
    if missing:
        raise ValueError(f"{len(missing)} pivot sources are absent from the LP matrix")
    candidate_positions = [position_of[source_index] for source_index in candidate_sources]
    numerical_record = None
    basis_signs = None
    if selection == "modular-rref":
        exact_candidates = candidate_positions
    elif selection == "qr-exact":
        import scipy
        import scipy.linalg

        dense = np.zeros((rows, len(candidate_positions)), dtype=np.float64)
        for local_column, position in enumerate(candidate_positions):
            begin, end = int(start[position]), int(start[position + 1])
            dense[index[begin:end], local_column] = value[begin:end]
        row_scale = np.max(np.abs(dense), axis=1)
        active_rows = np.flatnonzero(row_scale != 0)
        dense = dense[active_rows, :]
        row_scale = row_scale[active_rows]
        dense /= row_scale[:, None]
        _q, triangular, pivots = scipy.linalg.qr(
            dense,
            mode="economic",
            pivoting=True,
            overwrite_a=True,
            check_finite=False,
        )
        diagonal = np.abs(np.diag(triangular))
        numerical_rank_bound = len(active_rows)
        exact_candidates = [candidate_positions[int(local)] for local in pivots[:numerical_rank_bound]]
        basic_solution = scipy.linalg.solve(
            dense[:, pivots[:numerical_rank_bound]],
            np.asarray(target, dtype=np.float64)[active_rows] / row_scale,
            assume_a="gen",
            check_finite=False,
        )
        basis_signs = [1 if coefficient >= 0 else -1 for coefficient in basic_solution]
        residual = (
            dense[:, pivots[:numerical_rank_bound]] @ basic_solution
            - np.asarray(target, dtype=np.float64)[active_rows] / row_scale
        )
        numerical_record = {
            "selector": "scipy.linalg.qr with column pivoting on row-scaled float64 matrix",
            "scipy_version": scipy.__version__,
            "largest_abs_r_diagonal": float(np.max(diagonal)),
            "smallest_abs_r_diagonal": float(np.min(diagonal)),
            "diagonal_ratio": float(np.max(diagonal) / np.min(diagonal)),
            "basic_solution_min_abs_coefficient": float(np.min(np.abs(basic_solution))),
            "basic_solution_max_abs_coefficient": float(np.max(np.abs(basic_solution))),
            "basic_solution_scaled_residual_infinity_norm": float(np.max(np.abs(residual))),
            "nonzero_rows_numerator": len(active_rows),
            "rows_denominator": rows,
        }
        del dense, _q, triangular
    else:
        raise ValueError("selection must be modular-rref or qr-exact")
    rank_a, rank_augmented, selected_local = select_exact_support.analyze_candidate(
        rows, exact_candidates, start, index, value, target, prime
    )
    if rank_a != rank_augmented:
        raise RuntimeError(f"candidate columns omit the target: rank {rank_a}/{rank_augmented}")
    selected_positions = [exact_candidates[local] for local in selected_local]
    selected_sources = [int(source[position]) for position in selected_positions]
    if len(selected_positions) != rank_a:
        raise RuntimeError(f"selected {len(selected_positions)}/{rank_a} independent columns")
    if basis_signs is not None:
        basis_signs = [basis_signs[local] for local in selected_local]

    transposed = select_exact_support.flint.nmod_mat(rank_a, rows, prime)
    for local_column, position in enumerate(selected_positions):
        begin, end = int(start[position]), int(start[position + 1])
        for cursor in range(begin, end):
            transposed[local_column, int(index[cursor])] = int(value[cursor]) % prime
    reduced, row_rank = transposed.rref(inplace=True)
    if row_rank != rank_a:
        raise RuntimeError(f"selected-column row rank is {row_rank}/{rank_a}")
    independent_rows = set(select_exact_support.pivot_columns(reduced, row_rank))
    basic_row_positions = [row for row in range(rows) if row not in independent_rows]
    if len(selected_positions) + len(basic_row_positions) != rows:
        raise RuntimeError("column/row-slack basis does not have exactly one entry per row")
    report = {
        "schema": "max11-highs-initial-basis-v1",
        "verdict": "PASS",
        "exact": "modular",
        "prime": prime,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "candidate_pivot_report": str(pivot_report),
        "candidate_pivot_report_sha256": sha256(pivot_report),
        "candidate_columns_numerator": len(candidate_positions),
        "candidate_columns_denominator": columns,
        "selection": selection,
        "numerical_selection": numerical_record,
        "rank_a_mod_prime": rank_a,
        "rank_augmented_mod_prime": rank_augmented,
        "basis_columns_numerator": len(selected_positions),
        "basis_columns_denominator": rows,
        "basic_row_slacks_numerator": len(basic_row_positions),
        "basic_row_slacks_denominator": rows,
        "column_positions": selected_positions,
        "source_indices": selected_sources,
        "basis_signs": basis_signs,
        "basic_row_positions": basic_row_positions,
        "seconds": time.monotonic() - started,
        "no_claim": "This is an exact modular LP starting basis, not a rational identity or sparse certificate.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prime", type=int, required=True)
    parser.add_argument("--selection", choices=("modular-rref", "qr-exact"), default="modular-rref")
    args = parser.parse_args()
    print(
        json.dumps(
            prepare(args.matrix_dir, args.pivot_report, args.output, args.prime, args.selection),
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
