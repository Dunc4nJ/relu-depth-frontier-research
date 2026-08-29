#!/usr/bin/env python3
"""Extract and replay the frozen G-0008 cut-only modular dual.

The row set is fixed before probing additional primes: the 5,269 pivot cut
rows found in the p=1,000,003 G-0005-anchored solve, together with cut row
7,145 (ordered-cone linear index 10).  At each requested prime this script
solves only on the frozen 5,269-by-5,269 pivot minor, then replays the resulting
left-dual against all 9,804 candidate columns.

Every result is finite-field evidence.  Agreement at several primes is not a
characteristic-zero proof; rational reconstruction and exact integer replay
are separate gates.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import factorial, gcd
from pathlib import Path
import platform
import sys
import time

import numpy as np


N = 11
PIVOT_ROW_COUNT = 5269
FAILING_LINEAR_INDEX = 10
SCHEMA = "max11-cut-only-modular-dual-probes-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")


def write_json(path: Path, value: object) -> None:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    print(f"{path} bytes={len(raw)} sha256={sha256_bytes(raw)}", flush=True)


def require_prime(prime: int) -> None:
    from flint import fmpz

    if type(prime) is not int or prime <= N or not fmpz(prime).is_prime():
        raise ValueError(f"invalid probe prime: {prime}")
    if gcd(prime, factorial(N)) != 1:
        raise ValueError(f"probe prime divides 11!: {prime}")


def probe_prime(
    prime: int,
    square_list: list[list[int]],
    support_matrix: np.ndarray,
    failing_pivot_row: np.ndarray,
    failing_full_row: np.ndarray,
) -> dict[str, object]:
    from flint import nmod_mat

    require_prime(prime)
    begun = time.time()
    square = nmod_mat(square_list, prime)
    rhs = nmod_mat(
        [[(-int(value)) % prime] for value in failing_pivot_row], prime
    )
    coefficients = square.transpose().solve(rhs)
    coefficient_array = np.asarray(
        [int(coefficients[index, 0]) for index in range(PIVOT_ROW_COUNT)],
        dtype=np.int64,
    )
    del coefficients, square

    worst_case = (
        int(np.max(np.abs(support_matrix)))
        * (prime - 1)
        * PIVOT_ROW_COUNT
    )
    if worst_case >= np.iinfo(np.int64).max:
        raise OverflowError(f"int64 replay bound exceeded at prime {prime}")
    replay = (coefficient_array @ support_matrix + failing_full_row) % prime
    if np.any(replay):
        column = int(np.flatnonzero(replay)[0])
        raise AssertionError(
            f"complete cut-only replay failed at prime={prime} column={column}"
        )
    nonzero = int(np.count_nonzero(coefficient_array))
    return {
        "prime": prime,
        "pivot_minor_invertible_mod_prime": True,
        "pivot_coefficient_count": PIVOT_ROW_COUNT,
        "nonzero_pivot_coefficient_count": nonzero,
        "same_5270_row_support": nonzero == PIVOT_ROW_COUNT,
        "pivot_coefficients_mod_prime": list(map(int, coefficient_array)),
        "failing_row_coefficient_mod_prime": 1,
        "all_9804_candidate_columns_annihilated_mod_prime": True,
        "target_pairing_mod_prime": factorial(N) % prime,
        "seconds": time.time() - begun,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cut-matrix", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--obstruction", type=Path, required=True)
    parser.add_argument("--anchor", type=Path, required=True)
    parser.add_argument("--primes", type=int, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if len(set(args.primes)) != len(args.primes):
        raise SystemExit("probe primes must be unique")

    begun = time.time()
    obstruction = json.loads(args.obstruction.read_text(encoding="utf-8"))
    anchor = json.loads(args.anchor.read_text(encoding="utf-8"))
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    if obstruction.get("prime") != 1_000_003 or anchor.get("prime") != 1_000_003:
        raise ValueError("frozen basis was not derived at p=1,000,003")
    if anchor.get("obstruction_sha256") != sha256_path(args.obstruction):
        raise ValueError("anchor/obstruction hash mismatch")
    if anchor.get("cut_matrix_sha256") != sha256_path(args.cut_matrix):
        raise ValueError("anchor/cut-matrix hash mismatch")
    if anchor.get("selection_sha256") != sha256_path(args.selection):
        raise ValueError("anchor/selection hash mismatch")

    pivot_columns = np.asarray(obstruction["pivot_columns"], dtype=np.int64)
    pivot_cut_rows = np.asarray(anchor["pivot_cut_rows"], dtype=np.int64)
    if pivot_columns.shape != (PIVOT_ROW_COUNT,) or pivot_cut_rows.shape != (
        PIVOT_ROW_COUNT,
    ):
        raise ValueError("frozen pivot basis shape mismatch")
    if not np.array_equal(pivot_columns, np.unique(pivot_columns)):
        raise ValueError("pivot columns are not sorted and unique")
    if not np.array_equal(pivot_cut_rows, np.unique(pivot_cut_rows)):
        raise ValueError("pivot cut rows are not sorted and unique")

    directions = selection.get("directions")
    if not isinstance(directions, list) or selection.get("selected_count") != len(
        directions
    ):
        raise ValueError("selection direction census mismatch")
    hinge_count = len(directions)
    failing_row_index = hinge_count + FAILING_LINEAR_INDEX
    if failing_row_index != 7145:
        raise AssertionError(f"unexpected failing row index: {failing_row_index}")
    if failing_row_index in set(map(int, pivot_cut_rows)):
        raise ValueError("failing row unexpectedly belongs to pivot cut basis")

    with np.load(args.cut_matrix, allow_pickle=False) as data:
        cut_matrix = np.asarray(data["matrix"], dtype=np.int64)
        class_indices = np.asarray(data["class_indices"], dtype=np.int64)
        stored_selection_sha256 = str(data["selection_sha256"][0])
    if stored_selection_sha256 != sha256_path(args.selection):
        raise ValueError("cut-matrix selection mismatch")
    if cut_matrix.shape != (hinge_count + N, 9804):
        raise ValueError(f"unexpected cut-matrix shape: {cut_matrix.shape}")
    if not np.array_equal(class_indices, np.arange(9804, dtype=np.int64)):
        raise ValueError("cut-matrix class order mismatch")

    support_matrix = cut_matrix[pivot_cut_rows, :]
    failing_full_row = cut_matrix[failing_row_index, :]
    square_integer = support_matrix[:, pivot_columns]
    failing_pivot_row = failing_full_row[pivot_columns]
    square_list = square_integer.tolist()
    probes = []
    for prime in args.primes:
        print(f"probing fixed support at prime={prime}", flush=True)
        probes.append(
            probe_prime(
                prime,
                square_list,
                support_matrix,
                failing_pivot_row,
                failing_full_row,
            )
        )

    fixed_support_rows = list(map(int, pivot_cut_rows)) + [failing_row_index]
    result = {
        "schema": SCHEMA,
        "n": N,
        "family": "all 9804 minimally cyclic same-component MAX10 lifts",
        "claim_boundary": (
            "finite-field cut-only left-duals on one frozen 5270-row support; "
            "multi-prime agreement alone is not a rational or real obstruction"
        ),
        "cut_matrix_sha256": sha256_path(args.cut_matrix),
        "cut_matrix_int64_c_sha256": sha256_bytes(
            cut_matrix.tobytes(order="C")
        ),
        "selection_sha256": sha256_path(args.selection),
        "obstruction_sha256": sha256_path(args.obstruction),
        "anchor_sha256": sha256_path(args.anchor),
        "pivot_column_count": len(pivot_columns),
        "pivot_columns": list(map(int, pivot_columns)),
        "pivot_cut_row_count": len(pivot_cut_rows),
        "pivot_cut_rows": list(map(int, pivot_cut_rows)),
        "failing_row_index": failing_row_index,
        "failing_row_kind": "linear",
        "failing_linear_index": FAILING_LINEAR_INDEX,
        "fixed_support_count": len(fixed_support_rows),
        "fixed_support_rows_sha256": sha256_bytes(
            np.asarray(fixed_support_rows, dtype=np.int64).tobytes(order="C")
        ),
        "integer_target_pairing": factorial(N),
        "cut_rank_mod_1000003": PIVOT_ROW_COUNT,
        "cut_augmented_rank_mod_1000003": PIVOT_ROW_COUNT + 1,
        "probes": probes,
        "all_probes_same_5270_row_support": all(
            probe["same_5270_row_support"] for probe in probes
        ),
        "all_probes_complete_9804_column_replay": all(
            probe["all_9804_candidate_columns_annihilated_mod_prime"]
            for probe in probes
        ),
        "seconds": time.time() - begun,
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
        },
    }
    write_json(args.output, result)


if __name__ == "__main__":
    main()
