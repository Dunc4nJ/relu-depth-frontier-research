#!/usr/bin/env python3
"""Extract modular low-mass seed relations from the G-0047 rank signal.

This replays the deterministic 5,000-row matrix, obtains a one-dimensional
quotient of the three full-support seeds modulo 3,307 proper-support columns,
and constructs a sparse basis relation when its binary finite-difference is
nonzero.  Output remains a modular selected-row candidate, never a theorem.
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
from typing import Any

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SEARCH_SCRIPT = HERE / "low_mass_circuit_search.py"
SEARCH_REPORT = HERE / "low_mass_circuit_search_v1.json.gz"
EXPECTED_SEARCH_SCRIPT_HASH = (
    "2c28663459755f631c44e2444be4c2540ae9772c26c542c7c9807e63eeee10fd"
)
EXPECTED_SEARCH_REPORT_HASH = (
    "215b0d5320d4c76ffd4cf5c351bcb8722e715dde74a0e295d8d4715b83fcaa43"
)
DEFAULT_OUTPUT = HERE / "low_mass_quotient_extract_v1.json.gz"
SCHEMA = "max11-g0047-low-mass-quotient-extract-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_search() -> Any:
    if sha256_path(SEARCH_SCRIPT) != EXPECTED_SEARCH_SCRIPT_HASH:
        raise ValueError("low-mass search script drift")
    if sha256_path(SEARCH_REPORT) != EXPECTED_SEARCH_REPORT_HASH:
        raise ValueError("low-mass search report drift")
    spec = importlib.util.spec_from_file_location("g0047_low_mass_search", SEARCH_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import low-mass search")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.remainder(matrix, prime).astype(np.int64, copy=False)
    flat = reduced.ravel(order="C").tolist()
    result = nmod_mat(matrix.shape[0], matrix.shape[1], flat, prime)
    del flat, reduced
    return result


def pivot_columns(rref_matrix: nmod_mat, rank: int) -> list[int]:
    pivots = []
    for row in range(rank):
        pivot = next(
            (column for column in range(rref_matrix.ncols()) if int(rref_matrix[row, column])),
            None,
        )
        if pivot is None:
            raise AssertionError("nonzero RREF row lacks a pivot")
        pivots.append(pivot)
    if len(set(pivots)) != rank:
        raise AssertionError("RREF pivot duplication")
    return pivots


def build_matrix(search: Any, workers: int) -> tuple[np.ndarray, list[dict[str, object]], tuple[tuple[int, ...], ...]]:
    module = search.load_g47()
    records = search.load_records(module)
    universe = search.direction_universe()
    seed_directions = set()
    for record in records[-3:]:
        pair, active = search.compact_pair(record)
        _linear, hinges = module.primitive_normal_form(
            module.permutation_t_counter_dp(pair, active), active
        )
        seed_directions.update(hinges)
    complement = [direction for direction in universe if direction not in seed_directions]
    selected = tuple(sorted(seed_directions)) + tuple(
        complement[: search.DEFAULT_ROWS - len(seed_directions)]
    )
    selected_index = {direction: index for index, direction in enumerate(selected)}
    matrix = np.zeros((len(selected), len(records)), dtype=np.int64)
    completed = 0
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=search.init_worker,
        initargs=(selected_index,),
        maxtasksperchild=64,
    ) as pool:
        for sequence, _active, sparse, _invariant in pool.imap_unordered(
            search.column_worker, records, chunksize=1
        ):
            for row, value in sparse:
                matrix[row, sequence - 1] = value
            completed += 1
            if completed % 500 == 0 or completed == len(records):
                print(
                    f"G0047_QUOTIENT columns={completed}/{len(records)}",
                    file=sys.stderr,
                    flush=True,
                )
    if completed != len(records):
        raise AssertionError("matrix generation incomplete")
    return matrix, records, selected


def extract_for_prime(matrix: np.ndarray, prime: int) -> dict[str, object]:
    begun = time.perf_counter()
    full = to_nmod(matrix, prime)
    full_transpose_rref, full_rank = full.transpose().rref()
    if int(full_rank) != 489:
        raise AssertionError(f"unexpected full rank {full_rank} mod {prime}")
    pivot_rows = pivot_columns(full_transpose_rref, int(full_rank))
    del full_transpose_rref, full

    small = to_nmod(matrix[pivot_rows, :3307], prime)
    small_rref, proper_rank = small.rref()
    if int(proper_rank) != 488:
        raise AssertionError(f"unexpected proper rank {proper_rank} mod {prime}")
    basis_columns = pivot_columns(small_rref, int(proper_rank))
    del small_rref

    left_kernel, nullity = small.transpose().nullspace()
    if int(nullity) != 1:
        raise AssertionError(f"proper left-kernel nullity {nullity}")
    dual = [int(left_kernel[index, 0]) for index in range(len(pivot_rows))]
    if not any(dual):
        raise AssertionError("zero quotient dual")
    first = next(value for value in dual if value)
    scale = pow(first, -1, prime)
    dual = [(value * scale) % prime for value in dual]
    seed_prices = [
        sum(
            dual[row] * int(matrix[pivot_rows[row], sequence - 1])
            for row in range(len(pivot_rows))
        )
        % prime
        for sequence in (3308, 3309, 3310)
    ]
    if not any(seed_prices):
        raise AssertionError("quotient dual prices no seed")

    seed_relation = None
    for first_index in range(3):
        for second_index in range(first_index + 1, 3):
            candidate = [0, 0, 0]
            candidate[first_index] = seed_prices[second_index]
            candidate[second_index] = (-seed_prices[first_index]) % prime
            total = sum(candidate) % prime
            if total:
                seed_relation = candidate
                break
        if seed_relation is not None:
            break
    quotient_proportional_to_binary_invariant = seed_relation is None
    if seed_relation is None:
        return {
            "prime": prime,
            "proper_rank": int(proper_rank),
            "full_rank": int(full_rank),
            "pivot_rows": pivot_rows,
            "basis_columns": basis_columns,
            "normalized_seed_quotient_prices": seed_prices,
            "quotient_proportional_to_seed_coefficient_sum": True,
            "nonzero_binary_invariant_relation": None,
            "seconds": time.perf_counter() - begun,
        }

    # Select 488 rows making the proper basis square and solve there.
    proper_basis_on_pivots = matrix[np.ix_(pivot_rows, basis_columns)]
    basis_transpose_rref, basis_rank = to_nmod(
        proper_basis_on_pivots, prime
    ).transpose().rref()
    if int(basis_rank) != 488:
        raise AssertionError("proper basis lost rank")
    local_basis_rows = pivot_columns(basis_transpose_rref, int(basis_rank))
    solve_rows = [pivot_rows[index] for index in local_basis_rows]
    square = to_nmod(matrix[np.ix_(solve_rows, basis_columns)], prime)
    seed_block = matrix[np.ix_(solve_rows, [3307, 3308, 3309])]
    rhs_values = [
        int(-sum(int(seed_block[row, index]) * seed_relation[index] for index in range(3)))
        % prime
        for row in range(len(solve_rows))
    ]
    rhs = nmod_mat(len(solve_rows), 1, rhs_values, prime)
    solution = square.solve(rhs)
    basis_coefficients = [int(solution[index, 0]) for index in range(len(basis_columns))]

    full_coefficients = np.zeros(matrix.shape[1], dtype=np.int64)
    for column, coefficient in zip(basis_columns, basis_coefficients, strict=True):
        full_coefficients[column] = coefficient
    full_coefficients[-3:] = seed_relation
    residual = np.remainder(matrix @ full_coefficients, prime)
    if np.any(residual):
        first_bad = int(np.flatnonzero(residual)[0])
        raise AssertionError(f"selected-row relation replay failed at row {first_bad}")
    seed_sum = sum(seed_relation) % prime
    binary_invariant = (239_500_800 % prime) * seed_sum % prime
    if not binary_invariant:
        raise AssertionError("constructed relation has zero binary invariant")
    normalization = pow(binary_invariant, -1, prime)
    normalized = np.remainder(full_coefficients * normalization, prime)
    normalized_seed = [int(value) for value in normalized[-3:]]
    nonzero_positions = np.flatnonzero(normalized)

    return {
        "prime": prime,
        "proper_rank": int(proper_rank),
        "full_rank": int(full_rank),
        "pivot_rows": pivot_rows,
        "basis_columns": basis_columns,
        "normalized_seed_quotient_prices": seed_prices,
        "quotient_proportional_to_seed_coefficient_sum": (
            quotient_proportional_to_binary_invariant
        ),
        "nonzero_binary_invariant_relation": {
            "seed_coefficients_before_invariant_normalization": seed_relation,
            "seed_coefficient_sum": seed_sum,
            "binary_invariant_before_normalization": binary_invariant,
            "normalization_to_binary_invariant_one": normalization,
            "normalized_seed_coefficients": normalized_seed,
            "normalized_nonzero_coefficient_count": int(len(nonzero_positions)),
            "normalized_support_indices": [int(index) for index in nonzero_positions],
            "normalized_coefficients": [int(normalized[index]) for index in nonzero_positions],
            "selected_5000_hinge_rows_replay_zero": True,
        },
        "seconds": time.perf_counter() - begun,
    }


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    search = load_search()
    matrix, records, selected = build_matrix(search, workers)
    prime_results = [extract_for_prime(matrix, prime) for prime in search.PRIMES]
    relation_exists = all(
        result["nonzero_binary_invariant_relation"] is not None
        for result in prime_results
    )
    result = (
        "TWO_PRIME_NONZERO_INVARIANT_LOW_MASS_RELATION_ON_5000_ROWS"
        if relation_exists
        else "LOW_MASS_QUOTIENT_EQUALS_BINARY_INVARIANT_ON_5000_ROWS"
    )
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("script changed during execution")
    report = {
        "schema": SCHEMA,
        "result": result,
        "script_sha256": script_hash_before,
        "bindings": {
            "search_script_sha256": EXPECTED_SEARCH_SCRIPT_HASH,
            "search_report_sha256": EXPECTED_SEARCH_REPORT_HASH,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
        },
        "matrix": {
            "rows": matrix.shape[0],
            "columns": matrix.shape[1],
            "proper_columns": 3307,
            "seed_sequences": [3308, 3309, 3310],
            "selected_directions_sha256": hashlib.sha256(
                canonical_bytes([list(direction) for direction in selected])
            ).hexdigest(),
        },
        "modular_results": prime_results,
        "mandatory_next_gate": (
            "Replay each displayed coefficient vector on all 10,065 degree-three primitive "
            "hinge directions. Only if both are zero, reconstruct a shared rational relation, "
            "add the exact F_1..F_10 chamber correction, and verify the resulting identity over Q."
        ),
        "no_claim": (
            "These are finite-field relations on 5,000 of 10,065 hinge rows. They are not global "
            "modular identities, rational identities, MAX11 networks, or unrestricted results."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside the project") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
