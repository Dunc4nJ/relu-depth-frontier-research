#!/usr/bin/env python3
"""Finite-field CEGIS for the frozen 9,804-class MAX11 lift family.

This is a discovery accelerator, not a characteristic-zero certificate.  It
solves an accumulated cut system over one explicitly recorded prime, evaluates
the complete ordered-cone hinge residual modulo that prime, and chooses fresh
nonzero residual rows.  Any terminal positive or negative result must still be
reconstructed over the rationals and independently replayed.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from math import factorial, gcd
import gzip
import hashlib
import json
from pathlib import Path
import platform
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

import build_cut_matrix as g8  # noqa: E402


MOD_SOLUTION_SCHEMA = "max11-modular-cegis-solution-v3"
MOD_RESIDUAL_SCHEMA = "max11-modular-cegis-residual-v3"
N = 11


def runtime_source_hashes() -> dict[str, str]:
    """Bind every project source that executes in the modular pipeline.

    The path checks prevent an import-path wrapper from being blessed merely
    because the solution copied that wrapper's hash into its own metadata.
    """

    evaluate_module = sys.modules.get("evaluate_minimal_lifts")
    if evaluate_module is None or not getattr(evaluate_module, "__file__", None):
        raise ValueError("evaluate_minimal_lifts runtime module is unavailable")
    expected_paths = {
        "modular_cegis_sha256": Path(__file__).resolve(),
        "build_cut_matrix_sha256": (HERE / "build_cut_matrix.py").resolve(),
        "exact_lift_search_sha256": (
            ROOT / "artifacts/math/G-0006/exact_lift_search.py"
        ).resolve(),
        "evaluate_minimal_lifts_sha256": (
            ROOT / "artifacts/math/G-0006/evaluate_minimal_lifts.py"
        ).resolve(),
    }
    runtime_paths = {
        "modular_cegis_sha256": Path(__file__).resolve(),
        "build_cut_matrix_sha256": Path(g8.__file__).resolve(),
        "exact_lift_search_sha256": Path(g8.g6.__file__).resolve(),
        "evaluate_minimal_lifts_sha256": Path(evaluate_module.__file__).resolve(),
    }
    for label, expected_path in expected_paths.items():
        if runtime_paths[label] != expected_path:
            raise ValueError(
                f"runtime source path mismatch for {label}: "
                f"{runtime_paths[label]} != {expected_path}"
            )
    return {label: g8.sha256_path(path) for label, path in runtime_paths.items()}


def write_json(path: Path, value: object) -> None:
    g8.write_json(path, value)


def require_prime(prime: int) -> None:
    from flint import fmpz

    if type(prime) is not int or prime <= 2 or not fmpz(prime).is_prime():
        raise ValueError("modulus must be a positive prime")
    if gcd(prime, factorial(N)) != 1:
        raise ValueError("prime must be coprime to 11! so normalization is invertible")


def load_system(
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
) -> tuple[np.ndarray, np.ndarray, dict[str, object], np.ndarray, list[dict[str, object]]]:
    _selection, directions = g8.load_selection(selection_path)
    classes = g8.g6.load_classes(classes_path)
    representatives = np.asarray(classes["representative_raw_indices"], dtype=np.int64)
    raw_orbits, orbit_target, _profiles, orbit_files = g8.g6.load_orbit_matrix(
        orbit_directory, str(classes["candidate_metadata_sha256"])
    )
    orbit_matrix = raw_orbits[:, representatives]
    with np.load(cut_matrix_path, allow_pickle=False) as data:
        if str(data["schema"][0]) != g8.MATRIX_SCHEMA:
            raise ValueError("cut matrix schema mismatch")
        if str(data["selection_sha256"][0]) != g8.sha256_path(selection_path):
            raise ValueError("cut matrix selection mismatch")
        if str(data["classes_sha256"][0]) != g8.sha256_path(classes_path):
            raise ValueError("cut matrix classes mismatch")
        class_indices = np.asarray(data["class_indices"], dtype=np.int64)
        cut_matrix = np.asarray(data["matrix"], dtype=np.int64)
    if not np.array_equal(class_indices, np.arange(len(representatives), dtype=np.int64)):
        raise ValueError("cut matrix class order mismatch")
    if cut_matrix.shape != (len(directions) + N, len(representatives)):
        raise ValueError(f"cut matrix shape mismatch: {cut_matrix.shape}")

    cut_target = np.zeros(len(directions) + N, dtype=np.int64)
    cut_target[-1] = factorial(N)
    system = np.concatenate((orbit_matrix, cut_matrix), axis=0)
    target = np.concatenate((orbit_target, cut_target), axis=0)
    return system, target, classes, representatives, orbit_files


def solve_modular(
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
    prime: int,
) -> dict[str, object]:
    from flint import nmod_mat

    require_prime(prime)
    source_hashes = runtime_source_hashes()
    system, target, classes, representatives, orbit_files = load_system(
        selection_path, classes_path, cut_matrix_path, orbit_directory
    )
    print(f"modular system shape={system.shape} prime={prime}", flush=True)
    begun = time.time()
    modular = nmod_mat(system.tolist(), prime)
    rref, rank = modular.rref()
    augmented = nmod_mat(np.column_stack((system, target)).tolist(), prime)
    augmented_rank = augmented.rank()
    member = rank == augmented_rank
    print(
        f"rank={rank} augmented_rank={augmented_rank} member={member} "
        f"seconds={time.time()-begun:.1f}",
        flush=True,
    )
    result: dict[str, object] = {
        "schema": MOD_SOLUTION_SCHEMA,
        "n": N,
        "family": "all 9804 minimally cyclic same-component MAX10 lifts",
        "prime": prime,
        "selection_sha256": g8.sha256_path(selection_path),
        "classes_sha256": g8.sha256_path(classes_path),
        "cut_matrix_sha256": g8.sha256_path(cut_matrix_path),
        "cut_matrix_int64_c_sha256": g8.sha256_bytes(
            load_cut_matrix_array(cut_matrix_path).tobytes(order="C")
        ),
        "orbit_input_files": orbit_files,
        "system_int64_c_sha256": g8.sha256_bytes(system.tobytes(order="C")),
        "target_int64_c_sha256": g8.sha256_bytes(target.tobytes(order="C")),
        "system_rows": int(system.shape[0]),
        "candidate_columns": int(system.shape[1]),
        "rank_mod_prime": int(rank),
        "augmented_rank_mod_prime": int(augmented_rank),
        "target_member_mod_prime": member,
        "claim_boundary": (
            "finite-field discovery only; neither membership nor nonmembership is a "
            "characteristic-zero MAX11 result"
        ),
        **source_hashes,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
        },
    }
    if not member:
        return result

    basis_columns = g8.pivot_columns(rref, rank, system.shape[1])
    basis = nmod_mat(system[:, basis_columns].tolist(), prime)
    transposed_rref, row_rank = basis.transpose().rref()
    pivot_rows = g8.pivot_columns(transposed_rref, row_rank, system.shape[0])
    if row_rank != rank or len(pivot_rows) != rank:
        raise AssertionError("modular row-basis extraction failed")
    square = nmod_mat(system[np.ix_(pivot_rows, basis_columns)].tolist(), prime)
    rhs = nmod_mat([[int(target[row]) % prime] for row in pivot_rows], prime)
    coefficients = square.solve(rhs)
    target_mod = nmod_mat([[int(value) % prime] for value in target], prime)
    if basis * coefficients != target_mod:
        raise AssertionError("complete modular constraint replay failed")

    inverse_factorial = pow(factorial(N), -1, prime)
    pairs, _candidate_digest = g8.g6.raw_candidate_pairs()
    terms = []
    for position, class_index in enumerate(basis_columns):
        internal = int(coefficients[position, 0])
        if not internal:
            continue
        certificate = internal * inverse_factorial % prime
        raw_index = int(representatives[class_index])
        left, right = pairs[raw_index]
        terms.append(
            {
                "class_index": int(class_index),
                "representative_raw_index": raw_index,
                "internal_coefficient_mod_prime": internal,
                "certificate_coefficient_mod_prime": certificate,
                "pair": [
                    [list(edge) for edge in left],
                    [list(edge) for edge in right],
                ],
            }
        )
    result.update(
        {
            "basis_column_count": len(basis_columns),
            "nonzero_term_count": len(terms),
            "complete_modular_constraint_replay": True,
            "normalization": (
                "internal a=11!*certificate coefficient; inverse exists modulo prime"
            ),
            "terms": terms,
        }
    )
    return result


def load_cut_matrix_array(path: Path) -> np.ndarray:
    with np.load(path, allow_pickle=False) as data:
        return np.asarray(data["matrix"], dtype=np.int64)


def strict_modular_terms(
    solution_path: Path,
    classes_path: Path,
    selection_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
) -> tuple[list[g8.g6.Pair], list[int], int, dict[str, object]]:
    from flint import nmod_mat

    solution = json.loads(solution_path.read_text(encoding="utf-8"))
    if solution.get("schema") != MOD_SOLUTION_SCHEMA or solution.get("n") != N:
        raise ValueError("wrong modular-solution schema")
    if solution.get("complete_modular_constraint_replay") is not True:
        raise ValueError("modular solution lacks complete replay")
    prime_value = solution.get("prime")
    if type(prime_value) is not int:
        raise ValueError("modular solution prime is not an integer")
    prime = prime_value
    require_prime(prime)
    source_hashes = runtime_source_hashes()
    for label, expected_hash in source_hashes.items():
        if solution.get(label) != expected_hash:
            raise ValueError(f"modular solution source mismatch: {label}")
    expected_environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "python_flint": __import__("flint").__version__,
    }
    if solution.get("environment") != expected_environment:
        raise ValueError("modular solution environment mismatch")
    system, target, classes, representatives_array, orbit_files = load_system(
        selection_path, classes_path, cut_matrix_path, orbit_directory
    )
    if solution.get("orbit_input_files") != orbit_files:
        raise ValueError("modular solution orbit-input manifest mismatch")
    if solution.get("classes_sha256") != g8.sha256_path(classes_path):
        raise ValueError("modular solution classes mismatch")
    if solution.get("selection_sha256") != g8.sha256_path(selection_path):
        raise ValueError("modular solution selection mismatch")
    if solution.get("cut_matrix_sha256") != g8.sha256_path(cut_matrix_path):
        raise ValueError("modular solution cut-matrix mismatch")
    if solution.get("cut_matrix_int64_c_sha256") != g8.sha256_bytes(
        load_cut_matrix_array(cut_matrix_path).tobytes(order="C")
    ):
        raise ValueError("modular solution cut-matrix array mismatch")
    if solution.get("system_int64_c_sha256") != g8.sha256_bytes(
        system.tobytes(order="C")
    ):
        raise ValueError("modular solution system mismatch")
    if solution.get("target_int64_c_sha256") != g8.sha256_bytes(
        target.tobytes(order="C")
    ):
        raise ValueError("modular solution target mismatch")
    if solution.get("system_rows") != system.shape[0] or solution.get(
        "candidate_columns"
    ) != system.shape[1]:
        raise ValueError("modular solution system shape mismatch")

    # Do not trust the serialized rank or membership metadata.  Recompute both
    # ranks from the frozen integer arrays before accepting any coefficient.
    modular_rank = nmod_mat(system.tolist(), prime).rank()
    augmented_rank = nmod_mat(
        np.column_stack((system, target)).tolist(), prime
    ).rank()
    if solution.get("rank_mod_prime") != modular_rank:
        raise ValueError("modular solution rank metadata mismatch")
    if solution.get("augmented_rank_mod_prime") != augmented_rank:
        raise ValueError("modular solution augmented-rank metadata mismatch")
    if solution.get("target_member_mod_prime") is not True:
        raise ValueError("modular solution does not assert target membership")
    if modular_rank != augmented_rank:
        raise ValueError("recomputed modular system excludes the target")

    representatives = list(map(int, representatives_array))
    raw_pairs, _ = g8.g6.raw_candidate_pairs()
    pairs: list[g8.g6.Pair] = []
    coefficients: list[int] = []
    internal_coefficients: list[int] = []
    support_class_indices: list[int] = []
    class_indices_seen: set[int] = set()
    inverse_factorial = pow(factorial(N), -1, prime)
    terms = solution.get("terms")
    if not isinstance(terms, list):
        raise ValueError("modular solution terms are not a list")
    for term_index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise ValueError(f"term {term_index} is not an object")
        class_index = term.get("class_index")
        raw_index = term.get("representative_raw_index")
        if type(class_index) is not int or not (0 <= class_index < len(representatives)):
            raise ValueError(f"term {term_index} class index out of range")
        if class_index in class_indices_seen:
            raise ValueError(f"term {term_index} duplicates a class index")
        class_indices_seen.add(class_index)
        if type(raw_index) is not int:
            raise ValueError(f"term {term_index} raw index is not an integer")
        if raw_index != representatives[class_index]:
            raise ValueError(f"term {term_index} representative mismatch")
        pair = raw_pairs[raw_index]
        serialized_pair = [
            [list(edge) for edge in pair[0]],
            [list(edge) for edge in pair[1]],
        ]
        if term.get("pair") != serialized_pair:
            raise ValueError(f"term {term_index} pair mismatch")
        internal = term.get("internal_coefficient_mod_prime")
        coefficient = term.get("certificate_coefficient_mod_prime")
        if type(internal) is not int or not (0 < internal < prime):
            raise ValueError(f"term {term_index} internal coefficient out of range")
        if type(coefficient) is not int:
            raise ValueError(f"term {term_index} certificate coefficient is not an integer")
        if not (0 < coefficient < prime):
            raise ValueError(f"term {term_index} coefficient out of range")
        if coefficient != internal * inverse_factorial % prime:
            raise ValueError(f"term {term_index} normalization mismatch")
        pairs.append(pair)
        coefficients.append(coefficient)
        internal_coefficients.append(internal)
        support_class_indices.append(class_index)
    if len(pairs) != solution.get("nonzero_term_count"):
        raise ValueError("modular term census mismatch")
    if solution.get("basis_column_count") != modular_rank:
        raise ValueError("modular basis/rank census mismatch")
    if len(pairs) > int(solution["basis_column_count"]):
        raise ValueError("modular nonzero support exceeds basis")

    # Replay the complete accumulated system from the serialized support and
    # internal coefficients.  This rejects a mutually renormalized but false
    # (internal, certificate) coefficient pair as well as any fabricated terms.
    if not support_class_indices:
        raise ValueError("modular solution has empty support")
    support = nmod_mat(system[:, support_class_indices].tolist(), prime)
    coefficient_vector = nmod_mat([[value] for value in internal_coefficients], prime)
    target_vector = nmod_mat([[int(value) % prime] for value in target], prime)
    if support * coefficient_vector != target_vector:
        raise ValueError("serialized modular coefficients fail complete system replay")
    return pairs, coefficients, prime, solution


def complete_modular_residual(
    solution_path: Path,
    classes_path: Path,
    selection_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
    workers: int,
) -> dict[str, object]:
    pairs, coefficients, prime, solution = strict_modular_terms(
        solution_path,
        classes_path,
        selection_path,
        cut_matrix_path,
        orbit_directory,
    )
    linear = [0] * N
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    raw_counts = [0] * len(pairs)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for index, column in executor.map(
            g8.g6._column_worker, list(enumerate(pairs)), chunksize=1
        ):
            coefficient = coefficients[index]
            raw_counts[index] = column.raw_direction_count
            for rank, value in enumerate(column.linear):
                linear[rank] = (linear[rank] + coefficient * value) % prime
            for direction, value in column.hinges.items():
                hinges[direction] = (hinges[direction] + coefficient * value) % prime
    linear[-1] = (linear[-1] - 1) % prime
    nonzero = sorted((direction, value) for direction, value in hinges.items() if value)

    def signed(value: int) -> int:
        return value if value <= prime // 2 else value - prime

    return {
        "schema": MOD_RESIDUAL_SCHEMA,
        "n": N,
        "prime": prime,
        "solution_sha256": g8.sha256_path(solution_path),
        "classes_sha256": g8.sha256_path(classes_path),
        "term_count": len(pairs),
        "linear_residual_mod_prime": [signed(value) for value in linear],
        "nonzero_hinge_count": len(nonzero),
        "raw_direction_count_min": min(raw_counts, default=0),
        "raw_direction_count_max": max(raw_counts, default=0),
        "global_identity_mod_prime": not any(linear) and not nonzero,
        "hinges": [
            {"direction": list(direction), "coefficient": signed(value)}
            for direction, value in nonzero
        ],
        "claim_boundary": (
            "complete residual only over the recorded finite field and frozen family; "
            "not a characteristic-zero or unrestricted-network result"
        ),
        "source_system_int64_c_sha256": solution["system_int64_c_sha256"],
        "modular_cegis_sha256": solution["modular_cegis_sha256"],
        "build_cut_matrix_sha256": solution["build_cut_matrix_sha256"],
        "exact_lift_search_sha256": solution["exact_lift_search_sha256"],
        "evaluate_minimal_lifts_sha256": solution[
            "evaluate_minimal_lifts_sha256"
        ],
        "environment": solution["environment"],
    }


def select_modular_cuts(
    residual_path: Path, hash_count: int, magnitude_count: int
) -> dict[str, object]:
    if hash_count <= 0 or magnitude_count <= 0:
        raise ValueError("selection counts must be positive")
    with gzip.open(residual_path, "rt", encoding="utf-8") as source:
        residual = json.load(source)
    if residual.get("schema") != MOD_RESIDUAL_SCHEMA or residual.get("n") != N:
        raise ValueError("wrong modular residual schema")
    if residual.get("global_identity_mod_prime") is not False:
        raise ValueError("selection requires a nonzero modular residual")
    prime = residual.get("prime")
    if type(prime) is not int:
        raise ValueError("modular residual prime is not an integer")
    require_prime(prime)
    raw_hinges = residual.get("hinges")
    if not isinstance(raw_hinges, list):
        raise ValueError("modular residual hinges are not a list")
    hinges: list[tuple[tuple[int, ...], int]] = []
    for item_index, item in enumerate(raw_hinges):
        if not isinstance(item, dict):
            raise ValueError(f"modular residual hinge {item_index} is not an object")
        raw_direction = item.get("direction")
        coefficient = item.get("coefficient")
        if not isinstance(raw_direction, list) or any(
            type(entry) is not int for entry in raw_direction
        ):
            raise ValueError(
                f"modular residual hinge {item_index} direction is not an integer list"
            )
        if type(coefficient) is not int:
            raise ValueError(
                f"modular residual hinge {item_index} coefficient is not an integer"
            )
        hinges.append((tuple(raw_direction), coefficient))
    nonzero_count = residual.get("nonzero_hinge_count")
    if type(nonzero_count) is not int or len(hinges) != nonzero_count:
        raise ValueError("modular residual hinge census mismatch")
    seen: set[tuple[int, ...]] = set()
    for direction, coefficient in hinges:
        if direction in seen:
            raise ValueError("duplicate modular residual direction")
        seen.add(direction)
        if (
            len(direction) != N
            or sum(direction) != 0
            or coefficient == 0
            or not (-(prime // 2) <= coefficient <= prime // 2)
            or coefficient % prime == 0
        ):
            raise ValueError("invalid modular residual hinge entry")
        magnitude = 0
        for value in direction:
            magnitude = gcd(magnitude, abs(value))
        if magnitude != 1:
            raise ValueError("nonprimitive modular residual direction")
        if g8.g6.nonpositive_on_ordered_cone(direction):
            raise ValueError("inactive modular residual direction")
    by_hash = sorted(
        hinges,
        key=lambda item: (
            hashlib.sha256(bytes(value + 5 for value in item[0])).digest(),
            item[0],
        ),
    )[:hash_count]
    by_magnitude = sorted(
        hinges, key=lambda item: (-abs(item[1]), item[0])
    )[:magnitude_count]
    directions = sorted({direction for direction, _ in by_hash + by_magnitude})
    return {
        "schema": g8.SELECTION_SCHEMA,
        "n": N,
        "source_residual": str(residual_path.resolve().relative_to(ROOT)),
        "source_residual_sha256": g8.sha256_path(residual_path),
        "source_solution_sha256": residual["solution_sha256"],
        "source_nonzero_hinge_count": len(hinges),
        "source_prime": prime,
        "selection_rule": (
            "union of smallest SHA256(direction entries shifted by +5) and largest "
            "absolute balanced modular residues; final rows lexicographically sorted"
        ),
        "hash_count_requested": hash_count,
        "magnitude_count_requested": magnitude_count,
        "selected_count": len(directions),
        "directions": [list(direction) for direction in directions],
        "claim_boundary": "finite-field discovery cuts only",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    solve_parser = sub.add_parser("solve")
    solve_parser.add_argument("--selection", type=Path, required=True)
    solve_parser.add_argument("--classes", type=Path, required=True)
    solve_parser.add_argument("--cut-matrix", type=Path, required=True)
    solve_parser.add_argument("--orbit-directory", type=Path, required=True)
    solve_parser.add_argument("--prime", type=int, default=1_000_003)
    solve_parser.add_argument("--output", type=Path, required=True)
    residual_parser = sub.add_parser("residual")
    residual_parser.add_argument("--solution", type=Path, required=True)
    residual_parser.add_argument("--classes", type=Path, required=True)
    residual_parser.add_argument("--selection", type=Path, required=True)
    residual_parser.add_argument("--cut-matrix", type=Path, required=True)
    residual_parser.add_argument("--orbit-directory", type=Path, required=True)
    residual_parser.add_argument("--workers", type=int, default=8)
    residual_parser.add_argument("--output", type=Path, required=True)
    select_parser = sub.add_parser("select")
    select_parser.add_argument("--residual", type=Path, required=True)
    select_parser.add_argument("--hash-count", type=int, default=1024)
    select_parser.add_argument("--magnitude-count", type=int, default=1024)
    select_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "solve":
        write_json(
            args.output,
            solve_modular(
                args.selection,
                args.classes,
                args.cut_matrix,
                args.orbit_directory,
                args.prime,
            ),
        )
    elif args.command == "residual":
        g8.write_gzip_json(
            args.output,
            complete_modular_residual(
                args.solution,
                args.classes,
                args.selection,
                args.cut_matrix,
                args.orbit_directory,
                args.workers,
            ),
        )
    else:
        write_json(
            args.output,
            select_modular_cuts(
                args.residual, args.hash_count, args.magnitude_count
            ),
        )


if __name__ == "__main__":
    main()
