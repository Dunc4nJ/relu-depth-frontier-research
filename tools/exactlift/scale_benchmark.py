#!/usr/bin/env python3
"""Synthetic sparse exact-solve benchmark at n=11-scale ranks.

The matrix is block diagonal.  Each block is ``30*T`` for a deterministic
positive-definite tridiagonal integer matrix ``T``.  The planted solution is
``numerator/30`` and the integer right-hand side is ``T*numerator``.  Every
block is solved independently with FLINT Dixon arithmetic and then checked
against both the planted rational vector and every exact row equation.

This measures a sparse block fallback, not a dense MAX11 pivot minor.
"""

from __future__ import annotations

import argparse
import json
import math
import resource
import time
from fractions import Fraction
from pathlib import Path
from typing import Sequence

import flint


def tridiagonal(size: int) -> list[list[int]]:
    matrix = [[0] * size for _ in range(size)]
    for row in range(size):
        matrix[row][row] = 5 + (row % 3)
        if row:
            matrix[row][row - 1] = 1
            matrix[row - 1][row] = 1
    return matrix


def planted_numerators(offset: int, size: int) -> list[int]:
    return [((17 * (offset + row) + 11) % 29) - 14 for row in range(size)]


def matrix_vector(matrix: list[list[int]], vector: list[int]) -> list[int]:
    return [sum(value * vector[col] for col, value in enumerate(row)) for row in matrix]


def run(rank: int, block_size: int, output: Path) -> dict:
    if rank < 1:
        raise ValueError("rank must be positive")
    if not 2 <= block_size <= 512:
        raise ValueError("block size must be in 2..512")

    started = time.monotonic()
    solve_seconds = 0.0
    verified_rows = 0
    nonzeros = 0
    mutant_nonzero_rows = 0
    blocks = math.ceil(rank / block_size)

    for block in range(blocks):
        offset = block * block_size
        size = min(block_size, rank - offset)
        base = tridiagonal(size)
        numerators = planted_numerators(offset, size)
        rhs_values = matrix_vector(base, numerators)
        exact_matrix_rows = [[30 * value for value in row] for row in base]
        nonzeros += sum(value != 0 for row in exact_matrix_rows for value in row)

        matrix = flint.fmpq_mat(flint.fmpz_mat(exact_matrix_rows))
        rhs = flint.fmpq_mat(flint.fmpz_mat(size, 1, rhs_values))
        solve_started = time.monotonic()
        solution = matrix.solve(rhs, algorithm="dixon")
        solve_seconds += time.monotonic() - solve_started

        expected = [Fraction(value, 30) for value in numerators]
        actual = [Fraction(str(solution[row, 0])) for row in range(size)]
        if actual != expected:
            raise RuntimeError(f"planted solution mismatch in block {block}")
        for row in range(size):
            residual = sum(
                Fraction(exact_matrix_rows[row][col]) * actual[col]
                for col in range(size)
            ) - rhs_values[row]
            if residual:
                raise RuntimeError(f"nonzero residual in block {block}, row {row}")
            verified_rows += 1

        if block == 0:
            mutant = actual.copy()
            mutant[0] += Fraction(1, 30)
            mutant_nonzero_rows = sum(
                sum(
                    Fraction(exact_matrix_rows[row][col]) * mutant[col]
                    for col in range(size)
                )
                != rhs_values[row]
                for row in range(size)
            )

    elapsed = time.monotonic() - started
    report = {
        "verdict": "PASS" if verified_rows == rank and mutant_nonzero_rows else "FAIL",
        "subject": "synthetic block-diagonal sparse full-rank integer system",
        "honest_boundary": "not a dense MAX11 pivot minor and not evidence of n=11 membership",
        "rank": rank,
        "block_size": block_size,
        "blocks": blocks,
        "matrix_nonzeros": nonzeros,
        "matrix_entries": rank * rank,
        "sparsity_denominator": rank * rank,
        "planted_solution_denominator": 30,
        "rows_verified": verified_rows,
        "solve_seconds": solve_seconds,
        "total_seconds": elapsed,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "mutant_delta": "1/30 at coordinate 0",
        "mutant_nonzero_rows_in_first_block": mutant_nonzero_rows,
        "projection": {
            "model": "linear in rank at fixed block size; synthetic structure only",
            "rank_35000_seconds": elapsed * 35_000 / rank,
            "rank_60000_seconds": elapsed * 60_000 / rank,
            "rank_35000_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
            "rank_60000_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--rank", type=int, required=True)
    parser.add_argument("--block-size", type=int, default=64)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    report = run(args.rank, args.block_size, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
