#!/usr/bin/env python3
"""Exact-Q rank bridge for all signed-mass <=3 MAX11 hinge columns.

The program uses a frozen modularly selected 488x488 minor only to choose a
candidate basis.  It then solves and replays every one of the 3,307 proper-core
columns over Q on all 10,065 rows, and tests the three full-core seeds modulo
that certified rational span.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Iterator

from flint import fmpq_mat, fmpz_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0047 = ROOT / "artifacts/math/G-0047"
EXTRACT_SCRIPT = G0047 / "low_mass_quotient_extract.py"
EXTRACT_REPORT = G0047 / "low_mass_quotient_extract_v1.json.gz"
RAW_RANK_REPORT = HERE / "full_row_rank_raw_v1.json.gz"
RANK_AUDIT_REPORT = HERE / "full_row_rank_audit_v1.json.gz"

EXPECTED_EXTRACT_SCRIPT_HASH = "55077ec87d8e49f71c93c484dd7fc0ad75962d25baa05af93d61e0e0e3d3c9d6"
EXPECTED_EXTRACT_REPORT_HASH = "ed4831af259606018b1807081d01451cad26bc14a97414bfbfd50cb41fe67fb9"
EXPECTED_RAW_RANK_REPORT_HASH = "c588e92b236dd1bbdfefda9304e936d4ded72bc46e030346dc9548b24ad03251"
EXPECTED_RANK_AUDIT_REPORT_HASH = "ef83f4d1d29679554e3e7b246089402e8f60dbd18adfd22a20bebf4488da8f64"
DEFAULT_OUTPUT = HERE / "exact_q_bridge_v1.json.gz"
SCHEMA = "max11-g0050-exact-q-bridge-v1"
N_ROWS = 10_065
N_PROPER = 3_307
N_ALL = 3_310
N_BASIS = 488
SEED_COLUMNS = (3307, 3308, 3309)
PRIMES = (1_000_003, 1_000_033)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def import_extract() -> Any:
    if sha256_path(EXTRACT_SCRIPT) != EXPECTED_EXTRACT_SCRIPT_HASH:
        raise ValueError("quotient extractor drift")
    spec = importlib.util.spec_from_file_location("g0050_extract", EXTRACT_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import quotient extractor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def batches(values: list[int], size: int) -> Iterator[list[int]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def q_pair(value: Any) -> tuple[int, int]:
    return int(value.numerator), int(value.denominator)


def q_string(value: Any) -> str:
    numerator, denominator = q_pair(value)
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def update_q_matrix_hash_column_major(digest: Any, matrix: Any) -> tuple[int, int, int]:
    max_numerator_bits = 0
    max_denominator_bits = 0
    nonunit_denominators = 0
    for column in range(matrix.ncols()):
        for row in range(matrix.nrows()):
            numerator, denominator = q_pair(matrix[row, column])
            digest.update(f"{numerator}/{denominator};".encode())
            max_numerator_bits = max(max_numerator_bits, abs(numerator).bit_length())
            max_denominator_bits = max(max_denominator_bits, denominator.bit_length())
            nonunit_denominators += denominator != 1
        digest.update(b"\n")
    return max_numerator_bits, max_denominator_bits, nonunit_denominators


def pivot_columns_generic(rref_matrix: Any, rank: int) -> list[int]:
    pivots = []
    for row in range(rank):
        pivot = next(
            (column for column in range(rref_matrix.ncols()) if rref_matrix[row, column]),
            None,
        )
        if pivot is None:
            raise AssertionError("RREF row lacks pivot")
        pivots.append(pivot)
    return pivots


def build_complete_matrix(search: Any, workers: int) -> tuple[np.ndarray, list[dict[str, object]], tuple[tuple[int, ...], ...]]:
    theorem = search.load_g47()
    records = search.load_records(theorem)
    universe = search.direction_universe()
    seed_directions = set()
    for record in records[-3:]:
        pair, active = search.compact_pair(record)
        _linear, hinges = theorem.primitive_normal_form(
            theorem.permutation_t_counter_dp(pair, active), active
        )
        seed_directions.update(hinges)
    selected = tuple(sorted(seed_directions)) + tuple(
        direction for direction in universe if direction not in seed_directions
    )
    if len(selected) != N_ROWS:
        raise AssertionError("complete row count drift")
    selected_index = {direction: index for index, direction in enumerate(selected)}
    matrix = np.zeros((N_ROWS, N_ALL), dtype=np.int64)
    invariant_histogram: Counter[int] = Counter()
    context = mp.get_context("fork")
    completed = 0
    with context.Pool(
        processes=workers,
        initializer=search.init_worker,
        initargs=(selected_index,),
        maxtasksperchild=64,
    ) as pool:
        for sequence, _active, sparse, invariant in pool.imap_unordered(
            search.column_worker, records, chunksize=1
        ):
            for row, value in sparse:
                matrix[row, sequence - 1] = value
            invariant_histogram[invariant] += 1
            completed += 1
            if completed % 500 == 0 or completed == N_ALL:
                print(f"G0050_EXACT columns={completed}/{N_ALL}", file=sys.stderr, flush=True)
    if completed != N_ALL:
        raise AssertionError("matrix generation incomplete")
    if invariant_histogram != Counter({0: N_PROPER, 239_500_800: 3}):
        raise AssertionError("binary invariant census drift")
    return matrix, records, selected


def run(workers: int, batch_size: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    bindings = {
        "extract_script": sha256_path(EXTRACT_SCRIPT),
        "extract_report": sha256_path(EXTRACT_REPORT),
        "raw_rank_report": sha256_path(RAW_RANK_REPORT),
        "rank_audit_report": sha256_path(RANK_AUDIT_REPORT),
    }
    expected_bindings = {
        "extract_script": EXPECTED_EXTRACT_SCRIPT_HASH,
        "extract_report": EXPECTED_EXTRACT_REPORT_HASH,
        "raw_rank_report": EXPECTED_RAW_RANK_REPORT_HASH,
        "rank_audit_report": EXPECTED_RANK_AUDIT_REPORT_HASH,
    }
    if bindings != expected_bindings:
        raise ValueError(f"input binding drift: {bindings}")
    extract = import_extract()
    search = extract.load_search()
    with gzip.open(EXTRACT_REPORT, "rt", encoding="utf-8") as source:
        discovery = json.load(source)
    raw_rank = load_json_gz(RAW_RANK_REPORT)
    rank_audit = load_json_gz(RANK_AUDIT_REPORT)
    if rank_audit.get("result") != "AUDITED_TWO_FIELD_FULL_ROW_SEED_QUOTIENT_GAIN_THREE":
        raise ValueError("rank audit is not favorable")

    matrix_started = time.perf_counter()
    matrix, _records, selected = build_complete_matrix(search, workers)
    matrix_seconds = time.perf_counter() - matrix_started
    selected_hash = canonical_sha256([list(direction) for direction in selected])
    if selected_hash != raw_rank["rows"]["selected_directions_sha256"]:
        raise AssertionError("complete row order hash drift")
    matrix_hash = hashlib.sha256()
    matrix_hash.update(b"int64-little-row-major;shape=10065x3310\n")
    matrix_hash.update(matrix.astype("<i8", copy=False).tobytes(order="C"))

    modular = discovery["modular_results"][0]
    pivot_rows_489 = list(map(int, modular["pivot_rows"]))
    basis_columns = list(map(int, modular["basis_columns"]))
    if len(pivot_rows_489) != 489 or len(basis_columns) != N_BASIS:
        raise AssertionError("discovery pivot census drift")
    candidate = matrix[np.ix_(pivot_rows_489, basis_columns)]
    candidate_transpose_rref, candidate_rank = extract.to_nmod(
        candidate, PRIMES[0]
    ).transpose().rref()
    if int(candidate_rank) != N_BASIS:
        raise AssertionError("candidate basis rank drift")
    local_rows = extract.pivot_columns(candidate_transpose_rref, N_BASIS)
    solve_rows = [pivot_rows_489[index] for index in local_rows]
    minor_array = matrix[np.ix_(solve_rows, basis_columns)]
    modular_minor_ranks = {
        str(prime): int(extract.to_nmod(minor_array, prime).rank()) for prime in PRIMES
    }
    if modular_minor_ranks != {str(prime): N_BASIS for prime in PRIMES}:
        raise AssertionError("fixed minor is not invertible at both primes")

    exact_started = time.perf_counter()
    minor = fmpz_mat(minor_array.tolist())
    determinant = minor.det()
    determinant_int = int(determinant)
    if determinant_int == 0:
        raise AssertionError("fixed exact minor is singular")
    basis_full = fmpz_mat(matrix[:, basis_columns].tolist())

    coefficient_digest = hashlib.sha256()
    coefficient_digest.update(b"column-major-fmpq;shape=488x3307\n")
    max_numerator_bits = 0
    max_denominator_bits = 0
    nonunit_denominators = 0
    verified_columns = 0
    proper_columns = list(range(N_PROPER))
    for batch_index, column_batch in enumerate(batches(proper_columns, batch_size), start=1):
        rhs_minor = fmpz_mat(matrix[np.ix_(solve_rows, column_batch)].tolist())
        coordinates = minor.solve(rhs_minor)
        reconstructed = basis_full * coordinates
        rhs_full = fmpz_mat(matrix[:, column_batch].tolist())
        if reconstructed != rhs_full:
            raise AssertionError(f"exact proper replay failed in batch {batch_index}")
        num_bits, den_bits, nonunit = update_q_matrix_hash_column_major(
            coefficient_digest, coordinates
        )
        max_numerator_bits = max(max_numerator_bits, num_bits)
        max_denominator_bits = max(max_denominator_bits, den_bits)
        nonunit_denominators += nonunit
        verified_columns += len(column_batch)
        print(
            f"G0050_EXACT proper={verified_columns}/{N_PROPER}",
            file=sys.stderr,
            flush=True,
        )
    if verified_columns != N_PROPER:
        raise AssertionError("not all proper columns were replayed")

    seed_minor = fmpz_mat(matrix[np.ix_(solve_rows, list(SEED_COLUMNS))].tolist())
    seed_coordinates = minor.solve(seed_minor)
    seed_full = fmpz_mat(matrix[:, list(SEED_COLUMNS)].tolist())
    seed_residual = fmpq_mat(seed_full) - basis_full * seed_coordinates
    seed_residual_rank = int(seed_residual.rank())
    if seed_residual_rank != 3:
        raise AssertionError(f"exact seed quotient rank {seed_residual_rank}")
    residual_transpose_rref, residual_rank = seed_residual.transpose().rref()
    seed_witness_rows = pivot_columns_generic(residual_transpose_rref, int(residual_rank))
    witness_minor = fmpq_mat(
        [
            [seed_residual[row, column] for column in range(3)]
            for row in seed_witness_rows
        ]
    )
    witness_determinant = witness_minor.det()
    if not witness_determinant:
        raise AssertionError("seed residual witness minor is singular")

    seed_coordinate_payload = [
        [q_string(seed_coordinates[row, column]) for column in range(3)]
        for row in range(seed_coordinates.nrows())
    ]
    seed_residual_digest = hashlib.sha256()
    seed_residual_digest.update(b"column-major-fmpq;shape=10065x3\n")
    seed_residual_nonzeros = [0, 0, 0]
    seed_first_residual: list[dict[str, object] | None] = [None, None, None]
    for column in range(3):
        for row in range(N_ROWS):
            value = seed_residual[row, column]
            numerator, denominator = q_pair(value)
            seed_residual_digest.update(f"{numerator}/{denominator};".encode())
            if numerator:
                seed_residual_nonzeros[column] += 1
                if seed_first_residual[column] is None:
                    seed_first_residual[column] = {
                        "row_index": row,
                        "direction": list(selected[row]),
                        "value": q_string(value),
                    }
        seed_residual_digest.update(b"\n")

    test_column = next(
        column
        for column in range(N_PROPER)
        if column not in set(basis_columns) and np.count_nonzero(matrix[:, column])
    )
    test_rhs_minor = fmpz_mat(matrix[np.ix_(solve_rows, [test_column])].tolist())
    test_coordinates = minor.solve(test_rhs_minor)
    test_coordinates[0, 0] += 1
    coefficient_mutant_residual = basis_full * test_coordinates - fmpz_mat(
        matrix[:, [test_column]].tolist()
    )
    mutant_first_row = next(
        row for row in range(N_ROWS) if coefficient_mutant_residual[row, 0]
    )
    target_first_row_plus_one_residual = -1

    exact_seconds = time.perf_counter() - exact_started
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("exact bridge script changed during run")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "EXACT_Q_PROPER_RANK_488_AND_THREE_SEED_QUOTIENT_RANK_3",
        "script_sha256": script_hash_before,
        "bindings": expected_bindings,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
            "batch_size": batch_size,
        },
        "complete_integer_matrix": {
            "shape": [N_ROWS, N_ALL],
            "row_order_sha256": selected_hash,
            "matrix_encoding": "int64 little-endian row-major with bound header",
            "matrix_sha256": matrix_hash.hexdigest(),
        },
        "fixed_exact_basis": {
            "proper_basis_column_indices": basis_columns,
            "proper_basis_columns_sha256": canonical_sha256(basis_columns),
            "solve_row_indices": solve_rows,
            "solve_rows_sha256": canonical_sha256(solve_rows),
            "minor_shape": [N_BASIS, N_BASIS],
            "minor_entries_sha256": canonical_sha256(minor_array.tolist()),
            "minor_modular_ranks": modular_minor_ranks,
            "exact_determinant_nonzero": True,
            "exact_determinant_sign": 1 if determinant_int > 0 else -1,
            "exact_determinant_bit_length": abs(determinant_int).bit_length(),
            "exact_determinant_decimal_sha256": hashlib.sha256(
                str(determinant_int).encode()
            ).hexdigest(),
        },
        "proper_span_certificate": {
            "verified_columns": verified_columns,
            "verified_rows_per_column": N_ROWS,
            "all_3307_proper_columns_exactly_replayed_over_Q": True,
            "coordinate_matrix_shape": [N_BASIS, N_PROPER],
            "coordinate_matrix_column_major_sha256": coefficient_digest.hexdigest(),
            "maximum_numerator_bit_length": max_numerator_bits,
            "maximum_denominator_bit_length": max_denominator_bits,
            "nonunit_denominator_entry_count": nonunit_denominators,
            "exact_rank_Q_proper": N_BASIS,
        },
        "seed_quotient_certificate": {
            "seed_zero_based_columns": list(SEED_COLUMNS),
            "seed_coordinate_matrix_rows": seed_coordinate_payload,
            "seed_coordinate_matrix_sha256": canonical_sha256(seed_coordinate_payload),
            "residual_matrix_shape": [N_ROWS, 3],
            "residual_matrix_column_major_sha256": seed_residual_digest.hexdigest(),
            "residual_nonzero_counts_by_seed": seed_residual_nonzeros,
            "first_residual_by_seed": seed_first_residual,
            "exact_residual_rank": seed_residual_rank,
            "witness_row_indices": seed_witness_rows,
            "witness_directions": [list(selected[row]) for row in seed_witness_rows],
            "witness_minor": [
                [q_string(witness_minor[row, column]) for column in range(3)]
                for row in range(3)
            ],
            "witness_minor_determinant": q_string(witness_determinant),
            "exact_seed_quotient_rank": 3,
            "exact_rank_Q_all_3310": 491,
        },
        "mutation_controls": {
            "basis_coordinate_plus_one": {
                "proper_target_column": test_column,
                "mutated_basis_coordinate": 0,
                "rejected": True,
                "lex_first_residual_row": mutant_first_row,
                "lex_first_residual_direction": list(selected[mutant_first_row]),
                "lex_first_residual_value": q_string(
                    coefficient_mutant_residual[mutant_first_row, 0]
                ),
            },
            "target_first_row_plus_one": {
                "mutated_row": 0,
                "rejected": True,
                "residual_value": target_first_row_plus_one_residual,
            },
        },
        "exact_bounded_conclusion": (
            "Over Q, within the frozen fully symmetrized signed-mass-1-through-3 degree-five "
            "pair-atom census, every hinge-free combination has zero coefficients on all three "
            "full-core seeds and therefore zero eleventh finite difference. Hence this bounded "
            "family cannot represent MAX11."
        ),
        "claim_boundary": (
            "This is an exact rational statement only for the frozen 3,310 low-mass orbit "
            "columns and frozen 10,065 primitive degree-three hinge semantics. It does not cover "
            "signed mass >=4, atoms outside the frozen pair-orbit model, nonsymmetric networks, "
            "arbitrary weights, or unrestricted MAX11 representations."
        ),
        "timing": {
            "matrix_generation_seconds": matrix_seconds,
            "exact_certificate_seconds": exact_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1 or args.batch_size < 1:
        raise SystemExit("workers and batch size must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.batch_size)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
