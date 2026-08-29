#!/usr/bin/env python3
"""Extract a replayable finite-field left-dual from a failed MAX11 cut solve.

This is a finite-field certificate only.  It deliberately does not infer
inconsistency over Q: a rational solution may have a denominator divisible by
the recorded prime when the candidate columns are not full rank modulo p.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import modular_cegis as mc  # noqa: E402


SCHEMA = "max11-modular-left-dual-v2"


def current_environment() -> dict[str, str]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "python_flint": __import__("flint").__version__,
    }


def execution_snapshot(
    solution_path: Path,
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
) -> dict[str, str]:
    expected_extractor = (HERE / "extract_modular_obstruction.py").resolve()
    actual_extractor = Path(__file__).resolve()
    if actual_extractor != expected_extractor:
        raise ValueError(
            f"extractor runtime path mismatch: {actual_extractor} != {expected_extractor}"
        )
    paths = {
        "input/solution": solution_path.resolve(),
        "input/selection": selection_path.resolve(),
        "input/classes": classes_path.resolve(),
        "input/cut_matrix": cut_matrix_path.resolve(),
        "source/extractor": actual_extractor,
        "source/modular_cegis": Path(mc.__file__).resolve(),
        "source/build_cut_matrix": Path(mc.g8.__file__).resolve(),
        "source/exact_lift_search": Path(mc.g8.g6.__file__).resolve(),
        "source/evaluate_minimal_lifts": (
            mc.ROOT / "artifacts/math/G-0006/evaluate_minimal_lifts.py"
        ).resolve(),
    }
    orbit_paths = sorted(orbit_directory.resolve().glob("group-*.npz"))
    if not orbit_paths:
        raise ValueError("orbit directory contains no group files")
    for path in orbit_paths:
        paths[f"input/orbit/{path.name}"] = path
    return {label: mc.g8.sha256_path(path) for label, path in sorted(paths.items())}


def pivot_columns_fast(rref, rank: int, column_count: int) -> list[int]:
    """Read the strictly increasing leading positions of an RREF matrix."""

    pivots: list[int] = []
    lower_bound = 0
    for row in range(rank):
        for column in range(lower_bound, column_count):
            if rref[row, column]:
                if int(rref[row, column]) != 1:
                    raise AssertionError("RREF leading entry is not one")
                pivots.append(column)
                lower_bound = column + 1
                break
        else:
            raise AssertionError(f"RREF row {row} has no pivot")
    if len(pivots) != rank or pivots != sorted(set(pivots)):
        raise AssertionError("invalid pivot-column census")
    return pivots


def row_kind(row: int, orbit_rows: int, hinge_rows: int, n: int) -> str:
    if row < orbit_rows:
        return "orbit"
    if row < orbit_rows + hinge_rows:
        return "hinge"
    if row < orbit_rows + hinge_rows + n:
        return "linear"
    raise ValueError(f"row out of range: {row}")


def checked_failed_solution(
    solution_path: Path,
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
) -> tuple[dict[str, object], np.ndarray, np.ndarray, int, int]:
    solution = json.loads(solution_path.read_text(encoding="utf-8"))
    if solution.get("schema") != mc.MOD_SOLUTION_SCHEMA or solution.get("n") != mc.N:
        raise ValueError("wrong modular-solution schema")
    if solution.get("target_member_mod_prime") is not False:
        raise ValueError("left-dual extraction requires a failed modular solve")
    if "terms" in solution or "complete_modular_constraint_replay" in solution:
        raise ValueError("failed modular solution unexpectedly contains certificate terms")
    prime = solution.get("prime")
    if type(prime) is not int:
        raise ValueError("solution prime is not an integer")
    mc.require_prime(prime)
    if solution.get("environment") != current_environment():
        raise ValueError("solution environment mismatch")
    for label, digest in mc.runtime_source_hashes().items():
        if solution.get(label) != digest:
            raise ValueError(f"solution source mismatch: {label}")

    system, target, _classes, _representatives, orbit_files = mc.load_system(
        selection_path, classes_path, cut_matrix_path, orbit_directory
    )
    expected = {
        "selection_sha256": mc.g8.sha256_path(selection_path),
        "classes_sha256": mc.g8.sha256_path(classes_path),
        "cut_matrix_sha256": mc.g8.sha256_path(cut_matrix_path),
        "cut_matrix_int64_c_sha256": mc.g8.sha256_bytes(
            mc.load_cut_matrix_array(cut_matrix_path).tobytes(order="C")
        ),
        "system_int64_c_sha256": mc.g8.sha256_bytes(system.tobytes(order="C")),
        "target_int64_c_sha256": mc.g8.sha256_bytes(target.tobytes(order="C")),
    }
    for label, digest in expected.items():
        if solution.get(label) != digest:
            raise ValueError(f"solution input mismatch: {label}")
    if solution.get("orbit_input_files") != orbit_files:
        raise ValueError("solution orbit-input manifest mismatch")
    if solution.get("system_rows") != system.shape[0] or solution.get(
        "candidate_columns"
    ) != system.shape[1]:
        raise ValueError("solution shape metadata mismatch")
    rank = solution.get("rank_mod_prime")
    augmented_rank = solution.get("augmented_rank_mod_prime")
    if type(rank) is not int or type(augmented_rank) is not int:
        raise ValueError("solution ranks are not integers")
    if augmented_rank != rank + 1:
        raise ValueError("solution does not record a one-rank target obstruction")
    return solution, system, target, prime, rank


def extract(
    solution_path: Path,
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
) -> dict[str, object]:
    from flint import nmod_mat

    snapshot = execution_snapshot(
        solution_path,
        selection_path,
        classes_path,
        cut_matrix_path,
        orbit_directory,
    )
    source_hashes = mc.runtime_source_hashes()
    environment = current_environment()
    solution, system, target, prime, recorded_rank = checked_failed_solution(
        solution_path,
        selection_path,
        classes_path,
        cut_matrix_path,
        orbit_directory,
    )
    selection, directions = mc.g8.load_selection(selection_path)
    orbit_rows = system.shape[0] - len(directions) - mc.N
    if orbit_rows <= 0:
        raise AssertionError("invalid orbit-row census")

    begun = time.time()
    modular = nmod_mat(system.tolist(), prime)
    rref, rank = modular.rref()
    augmented_rank = nmod_mat(
        np.column_stack((system, target)).tolist(), prime
    ).rank()
    if rank != recorded_rank or augmented_rank != rank + 1:
        raise ValueError(
            f"independent rank replay mismatch: {rank}/{augmented_rank}"
        )
    pivot_columns = pivot_columns_fast(rref, rank, system.shape[1])
    del rref

    column_basis = nmod_mat(system[:, pivot_columns].tolist(), prime)
    row_rref, row_rank = column_basis.transpose().rref()
    if row_rank != rank:
        raise AssertionError("column-basis transpose lost rank")
    pivot_rows = pivot_columns_fast(row_rref, row_rank, system.shape[0])
    del row_rref

    square = nmod_mat(system[np.ix_(pivot_rows, pivot_columns)].tolist(), prime)
    determinant = int(square.det())
    if not determinant:
        raise AssertionError("recorded pivot minor is singular")
    rhs = nmod_mat([[int(target[row]) % prime] for row in pivot_rows], prime)
    coefficients = square.solve(rhs)
    prediction = column_basis * coefficients
    target_mod = nmod_mat([[int(value) % prime] for value in target], prime)
    failing_rows = [
        row for row in range(system.shape[0]) if prediction[row, 0] != target_mod[row, 0]
    ]
    if not failing_rows:
        raise AssertionError("failed solve has no failing row")
    failing_row = failing_rows[0]
    if failing_row in set(pivot_rows):
        raise AssertionError("pivot-system solution fails a pivot row")

    dual_rhs = nmod_mat(
        [[(-int(system[failing_row, column])) % prime] for column in pivot_columns],
        prime,
    )
    pivot_dual = square.transpose().solve(dual_rhs)
    dual = [0] * system.shape[0]
    for position, row in enumerate(pivot_rows):
        dual[row] = int(pivot_dual[position, 0])
    dual[failing_row] = 1
    dual_row = nmod_mat([dual], prime)
    annihilator = dual_row * modular
    if any(annihilator[0, column] for column in range(system.shape[1])):
        raise AssertionError("constructed dual does not annihilate every candidate column")
    target_pairing = int((dual_row * target_mod)[0, 0])
    direct_residual = (
        int(target[failing_row]) - int(prediction[failing_row, 0])
    ) % prime
    if not target_pairing or target_pairing != direct_residual:
        raise AssertionError("dual target pairing/residual mismatch")

    support = [
        {"row_index": row, "coefficient_mod_prime": coefficient}
        for row, coefficient in enumerate(dual)
        if coefficient
    ]
    kind_counts = Counter(
        row_kind(item["row_index"], orbit_rows, len(directions), mc.N)
        for item in support
    )
    failing_kind = row_kind(failing_row, orbit_rows, len(directions), mc.N)
    failing_semantic: dict[str, object] = {"kind": failing_kind}
    if failing_kind == "hinge":
        direction_index = failing_row - orbit_rows
        failing_semantic.update(
            {
                "direction_index": direction_index,
                "direction": list(directions[direction_index]),
            }
        )
    elif failing_kind == "linear":
        failing_semantic["linear_index"] = failing_row - orbit_rows - len(directions)

    result = {
        "schema": SCHEMA,
        "n": mc.N,
        "prime": prime,
        "solution_sha256": mc.g8.sha256_path(solution_path),
        "selection_sha256": mc.g8.sha256_path(selection_path),
        "classes_sha256": mc.g8.sha256_path(classes_path),
        "cut_matrix_sha256": mc.g8.sha256_path(cut_matrix_path),
        "system_int64_c_sha256": solution["system_int64_c_sha256"],
        "target_int64_c_sha256": solution["target_int64_c_sha256"],
        "system_rows": int(system.shape[0]),
        "candidate_columns": int(system.shape[1]),
        "rank_mod_prime": rank,
        "augmented_rank_mod_prime": augmented_rank,
        "pivot_column_count": len(pivot_columns),
        "pivot_columns": pivot_columns,
        "pivot_row_count": len(pivot_rows),
        "pivot_rows": pivot_rows,
        "pivot_minor_determinant_mod_prime": determinant,
        "failing_row": failing_row,
        "failing_row_semantic": failing_semantic,
        "failing_row_count": len(failing_rows),
        "dual_support_count": len(support),
        "dual_support_kind_counts": dict(sorted(kind_counts.items())),
        "dual_support": support,
        "target_pairing_mod_prime": target_pairing,
        "all_candidate_columns_annihilated_mod_prime": True,
        "claim_boundary": (
            "exact finite-field left-dual only; because column rank is below 9804, "
            "this alone does not prove nonmembership over Q or R"
        ),
        "extractor_sha256": snapshot["source/extractor"],
        "execution_snapshot": snapshot,
        "execution_snapshot_sha256": mc.g8.sha256_bytes(
            mc.g8.canonical_bytes(snapshot)
        ),
        **source_hashes,
        "environment": environment,
        "seconds": time.time() - begun,
        "selection_source_manifest": selection.get("source_selections", []),
    }
    ending_snapshot = execution_snapshot(
        solution_path,
        selection_path,
        classes_path,
        cut_matrix_path,
        orbit_directory,
    )
    if ending_snapshot != snapshot:
        changed = sorted(
            label
            for label in set(snapshot) | set(ending_snapshot)
            if snapshot.get(label) != ending_snapshot.get(label)
        )
        raise ValueError(f"execution inputs/sources changed during extraction: {changed}")
    if mc.runtime_source_hashes() != source_hashes:
        raise ValueError("runtime source manifest changed during extraction")
    if current_environment() != environment:
        raise ValueError("runtime environment changed during extraction")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--solution", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--cut-matrix", type=Path, required=True)
    parser.add_argument("--orbit-directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError(f"refusing to overwrite {args.output}")
    mc.write_json(
        args.output,
        extract(
            args.solution,
            args.selection,
            args.classes,
            args.cut_matrix,
            args.orbit_directory,
        ),
    )


if __name__ == "__main__":
    main()
