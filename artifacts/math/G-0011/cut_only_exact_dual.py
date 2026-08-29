#!/usr/bin/env python3
"""Lift or falsify the fixed round-four cut-only modular circuit over Q.

The object is deliberately bounded to the frozen 9,804 candidate columns.  A
successful exact left dual proves nonmembership only for that finite family;
it is not an unrestricted MAX11 lower bound.  Multi-prime agreement is a
falsification probe and never a characteristic-zero certificate.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import platform
import resource
import sys
import time

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
G8 = ROOT / "artifacts/math/G-0008"
G10 = ROOT / "artifacts/math/G-0010"
CLASSES = ROOT / "artifacts/math/G-0006/isomorphism_classes_v2.json"
CUT_MATRIX = G8 / "cut_matrix_01_02_03_04.npz"
SELECTION = G8 / "cut_selection_01_02_03_04.json"
OBSTRUCTION = G8 / "mod_obstruction_01_02_03_04_p1000003_v1.json"
COMPACT = G10 / "g0005_anchored_dual_p1000003_v1.json"

N = 11
TARGET_VALUE = 39_916_800
MODULAR_SCHEMA = "max11-cut-only-same-pivot-replay-v1"
BENCHMARK_SCHEMA = "max11-cut-only-dixon-benchmark-v1"
EXACT_SCHEMA = "max11-cut-only-exact-left-dual-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json_exclusive(path: Path, value: object, *, compress: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            if compress:
                with gzip.GzipFile(fileobj=destination, mode="wb", mtime=0) as stream:
                    stream.write(raw)
            else:
                destination.write(raw)
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise
    print(f"wrote {path} bytes={path.stat().st_size} sha256={sha256_path(path)}", flush=True)


def row_gcds(matrix: np.ndarray, rows: np.ndarray, block_rows: int = 128) -> np.ndarray:
    result = np.empty(len(rows), dtype=np.int64)
    for start in range(0, len(rows), block_rows):
        stop = min(start + block_rows, len(rows))
        block = np.abs(matrix[rows[start:stop], :])
        result[start:stop] = np.gcd.reduce(block, axis=1)
    if np.any(result <= 0):
        raise ValueError("zero support row has no primitive normalization")
    return result


def load_cut_object() -> dict[str, object]:
    obstruction = json.loads(OBSTRUCTION.read_text(encoding="utf-8"))
    compact = json.loads(COMPACT.read_text(encoding="utf-8"))
    if obstruction.get("candidate_columns") != 9804:
        raise ValueError("obstruction column census changed")
    pivot_columns = np.asarray(obstruction.get("pivot_columns"), dtype=np.int64)
    pivot_rows = np.asarray(compact.get("pivot_cut_rows"), dtype=np.int64)
    rank = int(obstruction.get("rank_mod_prime"))
    if pivot_columns.shape != (rank,) or pivot_rows.shape != (rank,):
        raise ValueError("fixed pivot shape mismatch")
    if not np.array_equal(pivot_columns, np.unique(pivot_columns)):
        raise ValueError("pivot columns are not unique and sorted")
    if not np.array_equal(pivot_rows, np.unique(pivot_rows)):
        raise ValueError("pivot cut rows are not unique and sorted")

    with np.load(CUT_MATRIX, allow_pickle=False) as data:
        cut = np.asarray(data["matrix"], dtype=np.int64)
        class_indices = np.asarray(data["class_indices"], dtype=np.int64)
        stored_selection = str(data["selection_sha256"][0])
        stored_classes = str(data["classes_sha256"][0])
    if cut.shape != (7146, 9804):
        raise ValueError(f"cut matrix shape changed: {cut.shape}")
    if not np.array_equal(class_indices, np.arange(9804, dtype=np.int64)):
        raise ValueError("cut matrix class order changed")
    if stored_selection != sha256_path(SELECTION) or stored_classes != sha256_path(CLASSES):
        raise ValueError("cut matrix input manifest mismatch")
    if obstruction.get("cut_matrix_sha256") != sha256_path(CUT_MATRIX):
        raise ValueError("obstruction/cut matrix mismatch")
    if compact.get("cut_matrix_sha256") != sha256_path(CUT_MATRIX):
        raise ValueError("compact witness/cut matrix mismatch")
    if compact.get("obstruction_sha256") != sha256_path(OBSTRUCTION):
        raise ValueError("compact witness/obstruction mismatch")

    failing_row = cut.shape[0] - 1
    if failing_row in set(map(int, pivot_rows)):
        raise ValueError("last linear row unexpectedly lies in pivot support")
    if int(pivot_rows.max()) >= failing_row:
        raise ValueError("pivot row outside the pre-failure cut block")
    row_divisors = row_gcds(cut, pivot_rows)
    failing_divisor = int(np.gcd.reduce(np.abs(cut[failing_row, :])))
    if failing_divisor <= 0 or TARGET_VALUE % failing_divisor:
        raise ValueError("failing-row normalization does not divide its target")

    raw_square = cut[np.ix_(pivot_rows, pivot_columns)]
    raw_failing = cut[failing_row, pivot_columns]
    primitive_square = raw_square // row_divisors[:, None]
    primitive_failing = raw_failing // failing_divisor
    if not np.array_equal(primitive_square * row_divisors[:, None], raw_square):
        raise AssertionError("pivot-row normalization is not exact")
    if not np.array_equal(primitive_failing * failing_divisor, raw_failing):
        raise AssertionError("failing-row normalization is not exact")

    return {
        "cut": cut,
        "pivot_rows": pivot_rows,
        "pivot_columns": pivot_columns,
        "failing_row": failing_row,
        "row_divisors": row_divisors,
        "failing_divisor": failing_divisor,
        "raw_coefficient_matrix": np.ascontiguousarray(raw_square.T),
        "raw_rhs": np.ascontiguousarray(-raw_failing),
        "primitive_coefficient_matrix": np.ascontiguousarray(primitive_square.T),
        "primitive_rhs": np.ascontiguousarray(-primitive_failing),
        "input_hashes": {
            "cut_matrix_sha256": sha256_path(CUT_MATRIX),
            "selection_sha256": sha256_path(SELECTION),
            "classes_sha256": sha256_path(CLASSES),
            "obstruction_sha256": sha256_path(OBSTRUCTION),
            "compact_witness_sha256": sha256_path(COMPACT),
        },
    }


def environment() -> dict[str, str]:
    import flint

    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "python_flint": flint.__version__,
    }


def pivot_columns_fast(rref, rank: int, column_count: int) -> list[int]:
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
    return pivots


def modular_replay(primes: list[int]) -> dict[str, object]:
    from flint import fmpz, nmod_mat

    begun = time.time()
    obj = load_cut_object()
    matrix = obj["raw_coefficient_matrix"]
    rhs = obj["raw_rhs"]
    cut = obj["cut"]
    pivot_rows = obj["pivot_rows"]
    failing_row = obj["failing_row"]
    records: list[dict[str, object]] = []
    for prime in primes:
        if prime <= 2 or not fmpz(prime).is_prime():
            raise ValueError(f"not an odd prime: {prime}")
        started = time.time()
        modular = nmod_mat(matrix.tolist(), prime)
        determinant = int(modular.det())
        if not determinant:
            records.append(
                {
                    "prime": prime,
                    "pivot_minor_determinant_mod_prime": 0,
                    "status": "singular-skip",
                    "seconds": time.time() - started,
                }
            )
            continue
        solution = modular.solve(nmod_mat([[int(value) % prime] for value in rhs], prime))
        coefficients = np.asarray(
            [int(solution[index, 0]) for index in range(matrix.shape[0])],
            dtype=np.int64,
        )
        overflow_bound = (
            int(np.max(np.abs(cut))) * int(coefficients.max()) * len(coefficients)
            + int(np.max(np.abs(cut[failing_row, :])))
        )
        if overflow_bound >= np.iinfo(np.int64).max:
            raise OverflowError(f"int64 replay bound exceeded at prime {prime}")
        residual = (coefficients @ cut[pivot_rows, :] + cut[failing_row, :]) % prime
        nonzero = np.flatnonzero(residual)
        records.append(
            {
                "prime": prime,
                "pivot_minor_determinant_mod_prime": determinant,
                "nonzero_candidate_columns": int(len(nonzero)),
                "first_nonzero_candidate_column": int(nonzero[0]) if len(nonzero) else None,
                "target_pairing_mod_prime": TARGET_VALUE % prime,
                "int64_replay_absolute_bound": overflow_bound,
                "status": "mismatch" if len(nonzero) else "all-columns-annihilated",
                "seconds": time.time() - started,
            }
        )
        print(records[-1], flush=True)
    return {
        "schema": MODULAR_SCHEMA,
        "claim_boundary": (
            "same-pivot finite-field falsification probe on the frozen 9804 columns; "
            "agreement at any number of primes is not a Q/R certificate"
        ),
        "rank": int(matrix.shape[0]),
        "candidate_columns": int(cut.shape[1]),
        "failing_cut_row": int(failing_row),
        "raw_target_pairing_integer_if_lifted": TARGET_VALUE,
        "records": records,
        **obj["input_hashes"],
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "environment": environment(),
        "seconds": time.time() - begun,
    }


def benchmark_dixon(size: int, prime: int) -> dict[str, object]:
    from flint import fmpq_mat, nmod_mat

    begun = time.time()
    obj = load_cut_object()
    coefficient_matrix = obj["primitive_coefficient_matrix"]
    rhs = obj["primitive_rhs"]
    if not 1 <= size <= coefficient_matrix.shape[0]:
        raise ValueError(f"benchmark size outside 1..{coefficient_matrix.shape[0]}")

    selection_started = time.time()
    rref, row_rank = nmod_mat(coefficient_matrix[:size, :].tolist(), prime).rref()
    if row_rank != size:
        raise ValueError(f"first {size} equations have rank only {row_rank} modulo {prime}")
    variable_indices = pivot_columns_fast(rref, row_rank, coefficient_matrix.shape[1])
    del rref
    square_integer = np.ascontiguousarray(coefficient_matrix[:size, variable_indices])
    rhs_integer = np.ascontiguousarray(rhs[:size])
    selection_seconds = time.time() - selection_started

    conversion_started = time.time()
    square = fmpq_mat(square_integer.tolist())
    rhs_matrix = fmpq_mat([[int(value)] for value in rhs_integer])
    conversion_seconds = time.time() - conversion_started

    solve_started = time.time()
    solution = square.solve(rhs_matrix, algorithm="dixon")
    solve_seconds = time.time() - solve_started
    verify_started = time.time()
    if square * solution != rhs_matrix:
        raise AssertionError("Dixon benchmark solution failed exact replay")
    verify_seconds = time.time() - verify_started
    numerator, denominator = solution.numer_denom()
    numerator_bits = max(abs(int(numerator[index, 0])).bit_length() for index in range(size))
    denominator_bits = abs(int(denominator)).bit_length()
    return {
        "schema": BENCHMARK_SCHEMA,
        "claim_boundary": (
            "exact solve of a nested square subproblem for resource extrapolation only; "
            "it is not a certificate for the full 5269-dimensional circuit"
        ),
        "size": size,
        "full_size": int(coefficient_matrix.shape[0]),
        "pivot_selection_prime": prime,
        "submatrix_int64_c_sha256": sha256_bytes(square_integer.tobytes(order="C")),
        "submatrix_density": float(np.count_nonzero(square_integer) / square_integer.size),
        "submatrix_max_abs_entry": int(np.max(np.abs(square_integer))),
        "rhs_max_abs_entry": int(np.max(np.abs(rhs_integer))),
        "solution_common_denominator_bits": denominator_bits,
        "solution_max_abs_numerator_bits": numerator_bits,
        "exact_replay": True,
        "pivot_selection_seconds": selection_seconds,
        "flint_conversion_seconds": conversion_seconds,
        "dixon_solve_seconds": solve_seconds,
        "exact_replay_seconds": verify_seconds,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        **obj["input_hashes"],
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "environment": environment(),
        "seconds": time.time() - begun,
    }


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    raise RuntimeError("MemAvailable absent from /proc/meminfo")


def exact_dixon(min_available_gib: float, verify_block_columns: int) -> dict[str, object]:
    from flint import fmpq_mat, fmpz_mat

    available = mem_available_gib()
    if available < min_available_gib:
        raise MemoryError(
            f"refusing full Dixon solve with only {available:.2f} GiB available; "
            f"minimum is {min_available_gib:.2f} GiB"
        )
    begun = time.time()
    obj = load_cut_object()
    coefficient_matrix = obj["primitive_coefficient_matrix"]
    rhs = obj["primitive_rhs"]
    conversion_started = time.time()
    square = fmpq_mat(coefficient_matrix.tolist())
    rhs_matrix = fmpq_mat([[int(value)] for value in rhs])
    conversion_seconds = time.time() - conversion_started
    solve_started = time.time()
    solution = square.solve(rhs_matrix, algorithm="dixon")
    solve_seconds = time.time() - solve_started
    if square * solution != rhs_matrix:
        raise AssertionError("full Dixon solution failed its square subsystem")
    numerator, denominator = solution.numer_denom()
    denominator_integer = int(denominator)

    cut = obj["cut"]
    pivot_rows = obj["pivot_rows"]
    failing_row = obj["failing_row"]
    row_divisors = obj["row_divisors"]
    failing_divisor = obj["failing_divisor"]
    numerator_row = numerator.transpose()
    verified_columns = 0
    verification_started = time.time()
    for start in range(0, cut.shape[1], verify_block_columns):
        stop = min(start + verify_block_columns, cut.shape[1])
        primitive_block = cut[np.ix_(pivot_rows, np.arange(start, stop))]
        primitive_block //= row_divisors[:, None]
        failing_block = cut[failing_row, start:stop] // failing_divisor
        exact_residual = numerator_row * fmpz_mat(primitive_block.tolist())
        for local in range(stop - start):
            if exact_residual[0, local] + denominator * int(failing_block[local]):
                column = start + local
                value = exact_residual[0, local] + denominator * int(failing_block[local])
                return {
                    "schema": EXACT_SCHEMA,
                    "result": "exact-nonzero-residual",
                    "claim_boundary": (
                        "the fixed rational pivot solution fails one frozen candidate column; "
                        "this says nothing about other pivot choices or unrestricted MAX11 networks"
                    ),
                    "first_nonzero_candidate_column": column,
                    "residual_numerator_over_solution_denominator": str(value),
                    "solution_common_denominator": str(denominator_integer),
                    "verified_prefix_columns": column,
                    **obj["input_hashes"],
                    "script_sha256": sha256_path(Path(__file__).resolve()),
                    "environment": environment(),
                    "seconds": time.time() - begun,
                }
        verified_columns = stop
        print(f"verified exact columns {verified_columns}/{cut.shape[1]}", flush=True)

    numerator_strings = [str(numerator[index, 0]) for index in range(numerator.nrows())]
    return {
        "schema": EXACT_SCHEMA,
        "result": "exact-left-dual",
        "claim_boundary": (
            "exact nonmembership certificate only for the frozen 9804 candidate columns; "
            "not an unrestricted two-hidden-layer MAX11 lower bound"
        ),
        "rank": int(coefficient_matrix.shape[0]),
        "candidate_columns": int(cut.shape[1]),
        "pivot_cut_rows": list(map(int, pivot_rows)),
        "pivot_columns": list(map(int, obj["pivot_columns"])),
        "failing_cut_row": int(failing_row),
        "primitive_pivot_row_divisors": list(map(int, row_divisors)),
        "primitive_failing_row_divisor": int(failing_divisor),
        "primitive_solution_common_denominator": str(denominator_integer),
        "primitive_solution_numerators": numerator_strings,
        "all_candidate_columns_annihilated_exactly": True,
        "verified_candidate_columns": verified_columns,
        "normalized_target_pairing_integer": TARGET_VALUE // failing_divisor,
        "raw_target_pairing_with_failing_coefficient_one": TARGET_VALUE,
        "flint_conversion_seconds": conversion_seconds,
        "dixon_solve_seconds": solve_seconds,
        "full_verification_seconds": time.time() - verification_started,
        "solution_common_denominator_bits": denominator_integer.bit_length(),
        "solution_max_abs_numerator_bits": max(abs(int(value)).bit_length() for value in numerator_strings),
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        **obj["input_hashes"],
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "environment": environment(),
        "seconds": time.time() - begun,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    modular = subparsers.add_parser("modular-replay")
    modular.add_argument("--prime", type=int, action="append", required=True)
    modular.add_argument("--output", type=Path, required=True)
    benchmark = subparsers.add_parser("benchmark-dixon")
    benchmark.add_argument("--size", type=int, required=True)
    benchmark.add_argument("--prime", type=int, default=1_000_003)
    benchmark.add_argument("--output", type=Path, required=True)
    exact = subparsers.add_parser("exact-dixon")
    exact.add_argument("--minimum-available-gib", type=float, default=24.0)
    exact.add_argument("--verify-block-columns", type=int, default=64)
    exact.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "modular-replay":
        result = modular_replay(args.prime)
        write_json_exclusive(args.output, result)
    elif args.command == "benchmark-dixon":
        result = benchmark_dixon(args.size, args.prime)
        write_json_exclusive(args.output, result)
    else:
        result = exact_dixon(args.minimum_available_gib, args.verify_block_columns)
        write_json_exclusive(args.output, result, compress=args.output.suffix == ".gz")


if __name__ == "__main__":
    main()
