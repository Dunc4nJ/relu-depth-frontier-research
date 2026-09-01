#!/usr/bin/env python3
"""Independent exact-integer replay of a serialized sparse left-kernel basis."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


ROWS = 5769
COLS = 6795
NULLITY = 478
MATRIX_BYTES = ROWS * COLS * 8
MATRIX_SHA256 = "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd"
RANK_RECEIPT_SHA256 = "61925993c97c40fac1ced04f374ffa05144026f2c2c8d3a579fa483d2219178a"


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--expected-basis-sha256", required=True)
    parser.add_argument("--rank-receipt", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    if args.receipt_out.exists():
        raise RuntimeError(f"refusing to overwrite {args.receipt_out}")
    if args.matrix.stat().st_size != MATRIX_BYTES or sha256_path(args.matrix) != MATRIX_SHA256:
        raise RuntimeError("matrix custody drift")
    basis_sha256 = sha256_path(args.basis)
    if basis_sha256 != args.expected_basis_sha256:
        raise RuntimeError("basis custody drift")
    rank_receipt_sha256 = sha256_path(args.rank_receipt)
    if rank_receipt_sha256 != RANK_RECEIPT_SHA256:
        raise RuntimeError("modular rank receipt custody drift")
    rank_receipt = json.loads(args.rank_receipt.read_text())
    expected_rank_fields = {
        "prime": 1000003,
        "rank_mod_prime": 5291,
        "selected_rows": ROWS,
        "selected_columns": COLS,
        "input_rows": ROWS,
        "input_columns": COLS,
        "coordinate_start_inclusive": 0,
        "coordinate_end_exclusive": COLS,
    }
    for key, expected in expected_rank_fields.items():
        if rank_receipt.get(key) != expected:
            raise RuntimeError(f"rank receipt field drift: {key}")

    with args.basis.open() as stream:
        header = json.loads(next(stream))
        relations = [json.loads(line) for line in stream]
    if header.get("schema") != "g0189.exact-primitive-left-kernel-basis.v1":
        raise RuntimeError("basis schema drift")
    if header.get("matrix_shape") != [ROWS, COLS] or header.get("basis_shape") != [ROWS, NULLITY]:
        raise RuntimeError("basis shape drift")
    if len(relations) != NULLITY or [relation["basis_column"] for relation in relations] != list(range(NULLITY)):
        raise RuntimeError("basis column census/order drift")
    free_rows = header["free_rows"]
    if len(free_rows) != NULLITY:
        raise RuntimeError("free-row census drift")

    matrix = np.memmap(args.matrix, dtype="<i8", mode="r", shape=(ROWS, COLS))
    matrix_minimum = int(matrix.min())
    matrix_maximum = int(matrix.max())
    residual_digest = hashlib.sha256()
    maximum_residual_abs = 0
    nonzero_residual_cells = 0
    maximum_arithmetic_bound = 0
    support_values = []
    free_coefficients = []

    for column, relation in enumerate(relations):
        terms = relation["terms"]
        rows = np.asarray([term[0] for term in terms], dtype=np.int64)
        coefficients = np.asarray([int(term[2]) for term in terms], dtype=np.int64)
        if len(rows) != relation["support"] or len(set(map(int, rows))) != len(rows):
            raise RuntimeError(f"support drift in relation {column}")
        if np.any(rows < 0) or np.any(rows >= ROWS) or np.any(rows[1:] <= rows[:-1]):
            raise RuntimeError(f"row-order drift in relation {column}")
        primitive_gcd = 0
        for coefficient in coefficients:
            primitive_gcd = math.gcd(primitive_gcd, abs(int(coefficient)))
        if primitive_gcd != 1:
            raise RuntimeError(f"nonprimitive relation {column}")
        free_row = free_rows[column]
        matches = np.flatnonzero(rows == free_row)
        if len(matches) != 1:
            raise RuntimeError(f"free row missing in relation {column}")
        free_coefficient = int(coefficients[int(matches[0])])
        if free_coefficient != int(relation["primitive_free_coefficient"]) or free_coefficient <= 0:
            raise RuntimeError(f"free coefficient drift in relation {column}")
        other_free_rows = set(free_rows) - {free_row}
        if any(int(row) in other_free_rows for row in rows):
            raise RuntimeError(f"off-diagonal free-row coefficient in relation {column}")

        sum_abs = sum(abs(int(coefficient)) for coefficient in coefficients)
        arithmetic_bound = sum_abs * max(abs(matrix_minimum), abs(matrix_maximum))
        maximum_arithmetic_bound = max(maximum_arithmetic_bound, arithmetic_bound)
        if arithmetic_bound > np.iinfo(np.int64).max:
            raise RuntimeError(f"int64 safety bound failed in relation {column}")
        residual = (matrix[rows, :] * coefficients[:, None]).sum(axis=0, dtype=np.int64)
        residual_le = np.asarray(residual, dtype="<i8")
        residual_digest.update(residual_le.tobytes(order="C"))
        maximum_residual_abs = max(maximum_residual_abs, int(np.max(np.abs(residual))))
        nonzero_residual_cells += int(np.count_nonzero(residual))
        support_values.append(len(rows))
        free_coefficients.append(free_coefficient)

    if maximum_residual_abs != 0 or nonzero_residual_cells != 0:
        raise RuntimeError("exact integer replay found a nonzero residual")
    if maximum_arithmetic_bound > np.iinfo(np.int64).max:
        raise RuntimeError("global arithmetic safety drift")
    source_path = Path(__file__)
    receipt = {
        "schema": "g0189.exact-left-kernel-replay.v1",
        "result": "EXACT_Q_RANK_5291_AND_LEFT_NULLITY_478_CERTIFIED",
        "inputs": {
            "matrix": {"path": str(args.matrix.resolve()), "bytes": MATRIX_BYTES, "sha256": MATRIX_SHA256},
            "basis": {"path": str(args.basis.resolve()), "bytes": args.basis.stat().st_size, "sha256": basis_sha256},
            "modular_rank_receipt": {"path": str(args.rank_receipt.resolve()), "bytes": args.rank_receipt.stat().st_size, "sha256": rank_receipt_sha256},
        },
        "producer": {
            "path": str(source_path.resolve()),
            "bytes": source_path.stat().st_size,
            "sha256": sha256_path(source_path),
            "python": os.sys.version,
            "numpy": np.__version__,
        },
        "exact_replay": {
            "relations": NULLITY,
            "matrix_columns_checked_per_relation": COLS,
            "residual_cells": NULLITY * COLS,
            "residual_i64le_bytes": NULLITY * COLS * 8,
            "residual_i64le_sha256": residual_digest.hexdigest(),
            "nonzero_residual_cells": nonzero_residual_cells,
            "maximum_residual_abs": maximum_residual_abs,
            "matrix_minimum": matrix_minimum,
            "matrix_maximum": matrix_maximum,
            "maximum_proved_int64_arithmetic_bound": maximum_arithmetic_bound,
            "int64_maximum": int(np.iinfo(np.int64).max),
            "all_relations_primitive": True,
            "free_coordinate_submatrix_diagonal_nonzero": True,
        },
        "rank_sandwich": {
            "upper_bound_over_Q": ROWS - NULLITY,
            "upper_bound_reason": "478 exact independent left-kernel vectors, certified by the nonzero diagonal free-coordinate submatrix",
            "lower_bound_over_Q": rank_receipt["rank_mod_prime"],
            "lower_bound_reason": "rank over F_1000003 is 5291, and reduction modulo a prime cannot exceed rational rank",
            "exact_rank_over_Q": 5291,
            "exact_left_nullity_over_Q": NULLITY,
        },
        "claim_boundary": "This certifies the characteristic-zero rank and a complete exact basis of the left kernel of the frozen 5769x6795 restriction matrix. It does not show that the corresponding 478 STAR combinations lie in O, nor settle MAX11 membership or an unrestricted neural-network lower bound.",
    }
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
