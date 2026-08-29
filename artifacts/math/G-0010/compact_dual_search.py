#!/usr/bin/env python3
"""Search for a compact modular dual anchored at the G-0005 four-point row.

The search is deliberately bounded.  It works only with the frozen G-0008
round-four integer matrix and reports identities over one finite field.  A
finite-field identity is a discovery object, not a characteristic-zero proof.

The first pass uses the 5,269 column-basis indices already replayed by the
G-0008 obstruction extractor.  It finds a basis of the cut rows on those
columns, solves for the fixed four-orbit functional, and then replays the
result against all 9,804 columns.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import factorial
from pathlib import Path
import platform
import sys
import time

import numpy as np


N = 11
ORBIT_PROFILES = (
    (2, 2, 7, 0),
    (4, 0, 7, 0),
    (3, 0, 8, 0),
    (2, 0, 9, 0),
)
# These are the G-0005 coefficients after multiplying by the stabilizer of
# each profile and dividing their gcd 725,760.  They act on the distinct-
# assignment orbit sums stored by G-0006.
ORBIT_WEIGHTS = (22, -55, -77, -230)
SCHEMA = "max11-g0005-anchored-modular-dual-search-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def write_json(path: Path, value: object) -> None:
    raw = (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    print(f"{path} bytes={len(raw)} sha256={sha256_bytes(raw)}", flush=True)


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
    if len(pivots) != rank or pivots != sorted(set(pivots)):
        raise AssertionError("invalid pivot-column census")
    return pivots


def load_four_orbit_rows(
    classes_path: Path, orbit_directory: Path
) -> tuple[np.ndarray, np.ndarray, list[int]]:
    classes = json.loads(classes_path.read_text(encoding="utf-8"))
    representatives = np.asarray(
        classes["representative_raw_indices"], dtype=np.int64
    )
    if representatives.shape != (9804,):
        raise ValueError("unexpected isomorphism-class census")

    by_profile: dict[tuple[int, ...], tuple[np.ndarray, int]] = {}
    all_profiles: list[tuple[int, ...]] = []
    for path in sorted(orbit_directory.glob("group-*.npz")):
        with np.load(path, allow_pickle=False) as data:
            profiles = [tuple(map(int, row)) for row in data["profiles"].tolist()]
            rows = np.asarray(data["rows"], dtype=np.int64)
            targets = np.asarray(data["targets"], dtype=np.int64)
        all_profiles.extend(profiles)
        for local_index, profile in enumerate(profiles):
            if profile in ORBIT_PROFILES:
                by_profile[profile] = (
                    rows[local_index, representatives],
                    int(targets[local_index]),
                )
    if len(all_profiles) != 364 or len(set(all_profiles)) != 364:
        raise ValueError("orbit profile coverage/census mismatch")
    if set(by_profile) != set(ORBIT_PROFILES):
        raise ValueError("one or more G-0005 profiles are absent")

    orbit_rows = np.asarray(
        [by_profile[profile][0] for profile in ORBIT_PROFILES], dtype=np.int64
    )
    orbit_targets = np.asarray(
        [by_profile[profile][1] for profile in ORBIT_PROFILES], dtype=np.int64
    )
    profile_indices = [all_profiles.index(profile) for profile in ORBIT_PROFILES]
    return orbit_rows, orbit_targets, profile_indices


def analyze(
    classes_path: Path,
    orbit_directory: Path,
    selection_path: Path,
    cut_matrix_path: Path,
    obstruction_path: Path,
) -> dict[str, object]:
    from flint import nmod_mat

    begun = time.time()
    obstruction = json.loads(obstruction_path.read_text(encoding="utf-8"))
    prime = obstruction.get("prime")
    if type(prime) is not int or prime <= 2:
        raise ValueError("invalid obstruction prime")
    if obstruction.get("candidate_columns") != 9804:
        raise ValueError("obstruction column census mismatch")
    raw_pivot_columns = obstruction.get("pivot_columns")
    if not isinstance(raw_pivot_columns, list) or any(
        type(value) is not int for value in raw_pivot_columns
    ):
        raise ValueError("invalid obstruction pivot columns")
    pivot_columns = np.asarray(raw_pivot_columns, dtype=np.int64)
    if len(pivot_columns) != obstruction.get("rank_mod_prime"):
        raise ValueError("obstruction pivot-column/rank mismatch")
    if not np.array_equal(pivot_columns, np.unique(pivot_columns)):
        raise ValueError("obstruction pivot columns are not unique and sorted")

    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    directions = selection.get("directions")
    if not isinstance(directions, list) or selection.get("selected_count") != len(
        directions
    ):
        raise ValueError("cut selection census mismatch")
    hinge_count = len(directions)

    orbit_rows, orbit_targets, profile_indices = load_four_orbit_rows(
        classes_path, orbit_directory
    )
    orbit_weights = np.asarray(ORBIT_WEIGHTS, dtype=np.int64)
    four_point_row = orbit_weights @ orbit_rows
    four_point_target = int(orbit_weights @ orbit_targets)
    if four_point_target != 110:
        raise AssertionError("G-0005 target normalization changed")

    with np.load(cut_matrix_path, allow_pickle=False) as data:
        cut_matrix = np.asarray(data["matrix"], dtype=np.int64)
        class_indices = np.asarray(data["class_indices"], dtype=np.int64)
        stored_selection_sha256 = str(data["selection_sha256"][0])
        stored_classes_sha256 = str(data["classes_sha256"][0])
    if stored_selection_sha256 != sha256_path(selection_path):
        raise ValueError("cut matrix selection mismatch")
    if stored_classes_sha256 != sha256_path(classes_path):
        raise ValueError("cut matrix classes mismatch")
    if not np.array_equal(class_indices, np.arange(9804, dtype=np.int64)):
        raise ValueError("cut matrix class order mismatch")
    if cut_matrix.shape != (hinge_count + N, 9804):
        raise ValueError(f"unexpected cut-matrix shape: {cut_matrix.shape}")

    restricted_cut = np.asarray(cut_matrix[:, pivot_columns], dtype=np.int64)
    print(
        f"restricted cut transpose shape={restricted_cut.T.shape} prime={prime}",
        flush=True,
    )
    transposed_rref, cut_rank = nmod_mat(
        restricted_cut.T.tolist(), prime
    ).rref()
    pivot_cut_rows = pivot_columns_fast(
        transposed_rref, cut_rank, restricted_cut.shape[0]
    )
    del transposed_rref
    if cut_rank != len(pivot_columns):
        raise AssertionError(
            f"cut block rank {cut_rank} does not preserve full rank {len(pivot_columns)}"
        )

    square_integer = restricted_cut[np.asarray(pivot_cut_rows, dtype=np.int64), :]
    square = nmod_mat(square_integer.tolist(), prime)
    rhs = nmod_mat(
        [[(-int(four_point_row[column])) % prime] for column in pivot_columns],
        prime,
    )
    cut_coefficients = square.transpose().solve(rhs)
    coefficient_array = np.asarray(
        [int(cut_coefficients[index, 0]) for index in range(cut_rank)],
        dtype=np.int64,
    )

    # Replay against every class, not merely the square solve core.  The
    # conservative bound below ensures this int64 multiplication cannot wrap.
    support_matrix = cut_matrix[np.asarray(pivot_cut_rows, dtype=np.int64), :]
    worst_case = (
        int(np.max(np.abs(support_matrix)))
        * (prime - 1)
        * len(pivot_cut_rows)
    )
    if worst_case >= np.iinfo(np.int64).max:
        raise OverflowError("int64 replay bound exceeded")
    replay = (coefficient_array @ support_matrix + four_point_row) % prime
    if np.any(replay):
        first = int(np.flatnonzero(replay)[0])
        raise AssertionError(f"complete replay failed at class {first}")

    cut_target = np.zeros(cut_matrix.shape[0], dtype=np.int64)
    cut_target[-1] = factorial(N)
    target_pairing = (
        four_point_target
        + sum(
            int(coefficient_array[position]) * int(cut_target[row])
            for position, row in enumerate(pivot_cut_rows)
        )
    ) % prime
    nonzero_positions = np.flatnonzero(coefficient_array)
    support = [
        {
            "row_index": int(pivot_cut_rows[position]),
            "coefficient_mod_prime": int(coefficient_array[position]),
        }
        for position in nonzero_positions
    ]
    support_kinds = {
        "hinge": sum(item["row_index"] < hinge_count for item in support),
        "linear": sum(item["row_index"] >= hinge_count for item in support),
    }
    return {
        "schema": SCHEMA,
        "n": N,
        "prime": prime,
        "claim_boundary": (
            "finite-field identity for the frozen 9804-class G-0008 family only; "
            "not a characteristic-zero or unrestricted MAX11 lower bound"
        ),
        "classes_sha256": sha256_path(classes_path),
        "selection_sha256": sha256_path(selection_path),
        "cut_matrix_sha256": sha256_path(cut_matrix_path),
        "cut_matrix_int64_c_sha256": sha256_bytes(
            cut_matrix.tobytes(order="C")
        ),
        "obstruction_sha256": sha256_path(obstruction_path),
        "obstruction_system_int64_c_sha256": obstruction.get(
            "system_int64_c_sha256"
        ),
        "candidate_columns": 9804,
        "cut_rows": int(cut_matrix.shape[0]),
        "hinge_rows": hinge_count,
        "linear_rows": N,
        "column_basis_count": len(pivot_columns),
        "cut_rank_on_column_basis_mod_prime": int(cut_rank),
        "orbit_profiles": [list(profile) for profile in ORBIT_PROFILES],
        "orbit_profile_indices": profile_indices,
        "orbit_weights_on_distinct_assignment_sums": list(ORBIT_WEIGHTS),
        "four_point_row_nonzero_columns": int(np.count_nonzero(four_point_row)),
        "four_point_row_unique_values": sorted(
            map(int, np.unique(four_point_row).tolist())
        ),
        "four_point_target_pairing_integer": four_point_target,
        "pivot_cut_row_count": len(pivot_cut_rows),
        "pivot_cut_rows": pivot_cut_rows,
        "cut_support_count": len(support),
        "cut_support_kind_counts": support_kinds,
        "cut_support": support,
        "all_candidate_columns_annihilated_mod_prime": True,
        "target_pairing_mod_prime": int(target_pairing),
        "is_modular_obstruction": bool(target_pairing),
        "seconds": time.time() - begun,
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--classes", type=Path, required=True)
    parser.add_argument("--orbit-directory", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--cut-matrix", type=Path, required=True)
    parser.add_argument("--obstruction", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    write_json(
        args.output,
        analyze(
            args.classes,
            args.orbit_directory,
            args.selection,
            args.cut_matrix,
            args.obstruction,
        ),
    )


if __name__ == "__main__":
    main()
