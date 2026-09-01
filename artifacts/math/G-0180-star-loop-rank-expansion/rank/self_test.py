#!/usr/bin/env python3
"""Production-path tests for the rectangular signed-i64 FLINT ranker."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import tempfile


def raw_matrix(rows: list[list[int]]) -> bytes:
    return b"".join(struct.pack("<q", value) for row in rows for value in row)


def selected_raw(rows: list[list[int]], end: int) -> bytes:
    return b"".join(struct.pack("<q", value) for row in rows for value in row[:end])


def invoke(
    ranker: Path,
    matrix: Path,
    rows: int,
    columns: int,
    end: int,
    prime: int,
    output: Path,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            str(ranker),
            str(matrix),
            "i64le",
            str(rows),
            str(columns),
            "0",
            str(end),
            "-",
            str(prime),
            str(output),
        ],
        text=True,
        capture_output=True,
        check=False,
    )


def checked_run(
    ranker: Path,
    matrix: Path,
    values: list[list[int]],
    end: int,
    prime: int,
    output: Path,
    expected_rank: int,
    expected_pivots: list[int],
) -> dict[str, object]:
    process = invoke(ranker, matrix, len(values), len(values[0]), end, prime, output)
    if process.returncode != 0 or process.stdout or process.stderr:
        raise RuntimeError(
            f"ranker failure: exit={process.returncode}\n"
            f"stdout={process.stdout!r}\nstderr={process.stderr!r}"
        )
    receipt = json.loads(output.read_bytes())
    expected = {
        "schema": "g0180.flint-signed-le-rectangular-rank-certificate.v1",
        "input_rows": len(values),
        "input_columns": len(values[0]),
        "selected_rows": len(values),
        "selected_columns": end,
        "selected_cells": len(values) * end,
        "reduction_crosscheck_cells": len(values) * end,
        "selected_raw_cells_sha256": hashlib.sha256(selected_raw(values, end)).hexdigest(),
        "prime": prime,
        "rank_mod_prime": expected_rank,
        "full_row_rank_mod_prime": expected_rank == len(values),
        "pivot_columns": expected_pivots,
        "pivot_columns_reduced": True,
    }
    for key, value in expected.items():
        if receipt.get(key) != value:
            raise RuntimeError(f"receipt field {key}: {receipt.get(key)!r} != {value!r}")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranker", required=True, type=Path)
    arguments = parser.parse_args()
    ranker = arguments.ranker.resolve(strict=True)
    values = [
        [1, 0, 1, -7, -(1 << 63)],
        [0, 1, 1, 11, (1 << 63) - 1],
        [1, 1, 2, 5, -1],
    ]
    with tempfile.TemporaryDirectory(prefix="g0180-rank-selftest-") as raw_temp:
        temp = Path(raw_temp)
        matrix = temp / "matrix.i64le"
        matrix.write_bytes(raw_matrix(values))
        prefix = checked_run(
            ranker,
            matrix,
            values,
            3,
            1_000_003,
            temp / "prefix.json",
            2,
            [0, 1],
        )
        full_a = checked_run(
            ranker,
            matrix,
            values,
            5,
            1_000_003,
            temp / "full-a.json",
            3,
            [0, 1, 3],
        )
        full_b = checked_run(
            ranker,
            matrix,
            values,
            5,
            1_000_033,
            temp / "full-b.json",
            3,
            [0, 1, 3],
        )
        bad_prime = invoke(
            ranker, matrix, len(values), len(values[0]), 5, 1_000_099, temp / "bad-prime.json"
        )
        if bad_prime.returncode == 0 or (temp / "bad-prime.json").exists():
            raise RuntimeError("unfrozen prime was accepted")
        truncated = temp / "truncated.i64le"
        truncated.write_bytes(raw_matrix(values)[:-1])
        truncated_run = invoke(
            ranker,
            truncated,
            len(values),
            len(values[0]),
            5,
            1_000_003,
            temp / "truncated.json",
        )
        if truncated_run.returncode == 0 or (temp / "truncated.json").exists():
            raise RuntimeError("truncated matrix was accepted")
        overwrite = invoke(
            ranker,
            matrix,
            len(values),
            len(values[0]),
            5,
            1_000_003,
            temp / "full-a.json",
        )
        if overwrite.returncode == 0:
            raise RuntimeError("receipt overwrite was accepted")
    print(
        json.dumps(
            {
                "result": "PASS",
                "prefix_rank": prefix["rank_mod_prime"],
                "full_ranks": [full_a["rank_mod_prime"], full_b["rank_mod_prime"]],
                "signed_extremes_exercised": True,
                "bad_prime_rejected": True,
                "truncation_rejected": True,
                "overwrite_rejected": True,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
