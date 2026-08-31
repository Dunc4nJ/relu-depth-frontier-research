#!/usr/bin/env python3
"""Fresh-Q solve and exact accumulated-row replay for G-0117 iteration 1."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import mmap
import os
from pathlib import Path
import resource
import struct
import sys
import time
from typing import Iterable, Sequence

from flint import fmpq_mat, fmpz_mat


HERE = Path(__file__).absolute().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).absolute()
RECORDS = 163_740
PANEL_ROWS = 301
ROWS = 313
N = 11
COLUMN_BYTES = PANEL_ROWS * 16
CACHE_BYTES = RECORDS * COLUMN_BYTES
TARGET_FACTORIAL = math.factorial(N)
INPUT_SHA256 = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8"
PANEL_ROWS_SHA256 = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c"
CACHE_SHA256 = "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b"
COORDINATE_SHA256 = "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071"
PREREGISTRATION_SHA256 = "57c43026da21ead61e9fc0a7330e763809e9bd565ce7854eef03ef14803a2c46"
PATH_ADDENDUM_SHA256 = "10756e6f9fd36d797dd52917523605ff4807fb13780164ed04547f83f75c9a4b"
DIRECTION = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4]
CERTIFICATE_SCHEMA = "max11-g0117-global-replay-certificate-v3"
CERTIFICATE_BOUNDARY = (
    "Denominator-cleared fresh-Q member of the exact accumulated G-0117 CEGIS rows for "
    "complete global replay; not a global identity, family-completeness theorem, or MAX11 result."
)


class ExactError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExactError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_u64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<Q", int(value)))
    return digest.hexdigest()


def digest_strings(values: Iterable[str]) -> str:
    digest = hashlib.sha256()
    for value in values:
        encoded = value.encode("utf-8")
        digest.update(struct.pack("<Q", len(encoded)))
        digest.update(encoded)
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def workspace_relative(path: Path) -> str:
    absolute = path.absolute()
    try:
        relative = absolute.relative_to(ROOT)
    except ValueError as error:
        raise ExactError(f"path is outside workspace: {path}") from error
    require(".." not in relative.parts, "path traversal refused")
    return relative.as_posix()


def qmatrix(integer_rows: Sequence[Sequence[int]]) -> fmpq_mat:
    return fmpq_mat(fmpz_mat([[int(value) for value in row] for row in integer_rows]))


def pivot_columns(reduced: fmpq_mat, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    cursor = 0
    for row in range(rank):
        while cursor < columns and not reduced[row, cursor]:
            cursor += 1
        require(cursor < columns, "RREF pivot extraction failed")
        pivots.append(cursor)
        cursor += 1
    return pivots


def primitive_integer(values: Sequence[Fraction]) -> list[int]:
    denominator = 1
    for value in values:
        denominator = math.lcm(denominator, value.denominator)
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "zero vector cannot be primitive")
    integers = [value // divisor for value in integers]
    first = next(value for value in integers if value)
    if first < 0:
        integers = [-value for value in integers]
    return integers


def first_target_separator(
    candidate: fmpq_mat,
    integer_rows: Sequence[Sequence[int]],
    target: Sequence[int],
) -> tuple[list[int], int, int]:
    reduced, rank = candidate.transpose().rref()
    rank = int(rank)
    pivots = pivot_columns(reduced, rank, len(target))
    pivot_set = set(pivots)
    for free in range(len(target)):
        if free in pivot_set:
            continue
        rational = [Fraction() for _ in target]
        rational[free] = Fraction(1)
        for row, pivot in enumerate(pivots):
            rational[pivot] = -Fraction(str(reduced[row, free]))
        if not sum(value * rhs for value, rhs in zip(rational, target, strict=True)):
            continue
        integer = primitive_integer(rational)
        for column in range(candidate.ncols()):
            require(
                sum(integer[row] * int(integer_rows[row][column]) for row in range(len(target)))
                == 0,
                "separator failed selected-support replay",
            )
        pairing = sum(value * rhs for value, rhs in zip(integer, target, strict=True))
        require(pairing != 0, "separator lost target pairing")
        return integer, pairing, free
    raise ExactError("augmented rank did not yield a target-separating left null")


def load_column(
    cache: mmap.mmap,
    coordinate: dict[str, object],
    sequence: int,
) -> list[int]:
    require(0 <= sequence < RECORDS, "sequence outside family")
    offset = sequence * COLUMN_BYTES
    panel = [
        int.from_bytes(cache[offset + 16 * row : offset + 16 * (row + 1)], "little", signed=True)
        for row in range(PANEL_ROWS)
    ]
    linear = [int(value) for value in coordinate["linear_vectors"][sequence]]
    hinge = int(coordinate["hinge_coefficients"][sequence])
    output = panel + linear + [hinge]
    require(len(output) == ROWS, "column dimension drift")
    return output


def matrix_rows(columns: Sequence[Sequence[int]]) -> list[list[int]]:
    require(columns and all(len(column) == ROWS for column in columns), "column shape drift")
    return [[int(column[row]) for column in columns] for row in range(ROWS)]


def first_separator_violation(
    cache: mmap.mmap,
    coordinate: dict[str, object],
    separator: Sequence[int],
) -> tuple[int, int] | None:
    # This exact scan is intentionally simple: it runs only on an exact-Q miss,
    # and it is the gate before any all-family nonmembership statement.
    nonzero = [(row, value) for row, value in enumerate(separator) if value]
    for sequence in range(RECORDS):
        column = load_column(cache, coordinate, sequence)
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price
    return None


def selected_basis_digest(integer_rows: Sequence[Sequence[int]]) -> str:
    return digest_i128(
        integer_rows[row][column]
        for row in range(len(integer_rows))
        for column in range(len(integer_rows[0]))
    )


def exact_replay_digest(lhs: Sequence[Fraction]) -> str:
    return digest_strings(str(value) for value in lhs)


def planted_controls() -> dict[str, bool]:
    # Reopening the family supplies column 1, which the frozen support omits.
    old = qmatrix([[1], [0]])
    target = qmatrix([[1], [1]])
    frozen_miss = int(old.rank()) != int(qmatrix([[1, 1], [0, 1]]).rank())
    reopened = qmatrix([[1, 0], [0, 1]])
    reopened_member = int(reopened.rank()) == int(
        qmatrix([[1, 0, 1], [0, 1, 1]]).rank()
    )

    # A previous denominator 2 must not be reused when the new solve needs 3.
    coefficients = [Fraction(1, 3), Fraction(2, 3)]
    fresh_scale = math.lcm(*(value.denominator for value in coefficients))
    stale_scale_rejected = fresh_scale == 3 and any(
        (2 * value).denominator != 1 for value in coefficients
    )
    require(
        frozen_miss and reopened_member and stale_scale_rejected,
        "planted CEGIS controls failed",
    )
    return {
        "old_support_freeze_rejected": frozen_miss and reopened_member,
        "stale_target_scale_rejected": stale_scale_rejected,
    }


def solve(
    input_path: Path,
    panel_rows_path: Path,
    cache_path: Path,
    manifest_path: Path,
    coordinate_path: Path,
    accumulated_rows_path: Path,
    modular_scan_path: Path,
    output_path: Path,
    certificate_path: Path,
) -> dict[str, object]:
    started = time.perf_counter()
    require(output_path != certificate_path, "output paths alias")
    require(not output_path.exists() and not certificate_path.exists(), "refusing overwrite")
    result_path = workspace_relative(output_path)
    python_executable = Path(sys.executable).absolute()
    paths = {
        "panel_input": workspace_relative(input_path),
        "panel_rows": workspace_relative(panel_rows_path),
        "cache_manifest": workspace_relative(manifest_path),
        "cache_payload": workspace_relative(cache_path),
        "accumulated_rows": workspace_relative(accumulated_rows_path),
        "modular_scan": workspace_relative(modular_scan_path),
        "solver_source": workspace_relative(SCRIPT),
        "solver_executable": workspace_relative(python_executable),
    }
    bindings = {
        name: sha256_path(ROOT / relative)
        for name, relative in paths.items()
    }
    require(bindings["panel_input"] == INPUT_SHA256, "panel input drift")
    require(bindings["panel_rows"] == PANEL_ROWS_SHA256, "panel rows drift")
    require(bindings["cache_payload"] == CACHE_SHA256, "cache payload drift")
    require(sha256_path(coordinate_path) == COORDINATE_SHA256, "coordinate output drift")
    require(
        sha256_path(HERE / "ITERATION1_V3_CERTIFICATE_PREREGISTRATION.md")
        == PREREGISTRATION_SHA256,
        "v3 preregistration drift",
    )
    require(
        sha256_path(HERE / "ITERATION1_V3_CERTIFICATE_PATH_ADDENDUM.md")
        == PATH_ADDENDUM_SHA256,
        "v3 path addendum drift",
    )

    source = json.loads(input_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    coordinate = json.loads(coordinate_path.read_text(encoding="utf-8"))
    row_document = json.loads(accumulated_rows_path.read_text(encoding="utf-8"))
    modular_scan = json.loads(modular_scan_path.read_text(encoding="utf-8"))
    require(
        source["schema"] == "max11-g0113-panel-solver-input-v1"
        and len(source["target"]) == PANEL_ROWS,
        "input schema/target drift",
    )
    require(
        manifest["schema"] == "max11-g0117-full-family-panel-cache-v1"
        and manifest["result"] == "EXACT_PANEL_CACHE_REPRODUCED"
        and int(manifest["payload_bytes"]) == CACHE_BYTES
        and manifest["data_sha256"] == CACHE_SHA256,
        "cache manifest drift",
    )
    require(cache_path.stat().st_size == CACHE_BYTES, "cache size drift")
    require(
        coordinate["schema"] == "max11-g0117-coordinate-price-v1"
        and coordinate["result"] == "EXACT_COORDINATE_PRICES"
        and coordinate["direction"] == DIRECTION
        and int(coordinate["records"]) == RECORDS
        and len(coordinate["linear_vectors"]) == RECORDS
        and len(coordinate["hinge_coefficients"]) == RECORDS,
        "coordinate result drift",
    )
    descriptors = [f"panel:{row}" for row in range(PANEL_ROWS)]
    descriptors.extend(f"linear:{row}" for row in range(N))
    descriptors.append("hinge:0,0,0,0,0,0,0,0,1,-5,4")
    target = [int(value) for value in source["target"]] + [0] * N + [0]
    target[PANEL_ROWS + N - 1] = TARGET_FACTORIAL
    require(len(target) == ROWS, "target dimension drift")
    require(
        row_document["schema"] == "max11-g0117-accumulated-rows-v1"
        and row_document["result"] == "EXACT_ORDERED_ROWS_BOUND"
        and int(row_document["rows"]) == ROWS
        and int(row_document["columns"]) == RECORDS
        and [row["descriptor"] for row in row_document["ordered_rows"]] == descriptors
        and [int(row["target"]) for row in row_document["ordered_rows"]] == target
        and row_document["descriptors_sha256"] == digest_strings(descriptors)
        and row_document["targets_i128_le_sha256"] == digest_i128(target),
        "accumulated row order/target drift",
    )
    require(
        modular_scan["schema"] == "max11-g0117-fresh-modular-scan-v1"
        and modular_scan["result"] != "MODULAR_DISAGREEMENT"
        and int(modular_scan["records_scanned"]) == RECORDS
        and int(modular_scan["rows"]) == ROWS
        and modular_scan["all_columns_reopened"] is True
        and modular_scan["old_support_only"] is False
        and modular_scan["bindings"]["accumulated_rows"]
        == bindings["accumulated_rows"],
        "fresh modular scan drift",
    )
    initial_sequences = sorted(
        {
            int(sequence)
            for prime in modular_scan["primes"]
            for sequence in prime["selected_sequences"]
        }
    )
    require(initial_sequences, "empty modular support")
    controls = planted_controls()
    trials: list[dict[str, object]] = []
    selected_sequences = initial_sequences[:]

    with cache_path.open("rb") as cache_file, mmap.mmap(
        cache_file.fileno(), 0, access=mmap.ACCESS_READ
    ) as cache:
        for iteration in range(ROWS + 1):
            require(
                selected_sequences == sorted(set(selected_sequences)),
                "selected sequence order/uniqueness drift",
            )
            selected_columns = [
                load_column(cache, coordinate, sequence) for sequence in selected_sequences
            ]
            integer_rows = matrix_rows(selected_columns)
            candidate = qmatrix(integer_rows)
            rhs = qmatrix([[value] for value in target])
            augmented = qmatrix(
                [row + [target[index]] for index, row in enumerate(integer_rows)]
            )
            exact_rank = int(candidate.rank())
            augmented_rank = int(augmented.rank())
            if exact_rank == augmented_rank:
                reduced, reduced_rank = candidate.rref()
                require(int(reduced_rank) == exact_rank, "candidate RREF rank drift")
                pivot_indices = pivot_columns(reduced, exact_rank, len(selected_sequences))
                support_sequences = [selected_sequences[index] for index in pivot_indices]
                support_columns = [selected_columns[index] for index in pivot_indices]
                basis_rows = matrix_rows(support_columns)
                basis = qmatrix(basis_rows)
                transposed, transposed_rank = basis.transpose().rref()
                require(int(transposed_rank) == exact_rank, "basis rank drift")
                coordinate_rows = pivot_columns(transposed, exact_rank, ROWS)
                square = qmatrix(
                    [
                        [basis_rows[row][column] for column in range(exact_rank)]
                        for row in coordinate_rows
                    ]
                )
                square_rhs = qmatrix([[target[row]] for row in coordinate_rows])
                coefficients = square.solve(square_rhs)
                require(basis * coefficients == rhs, "exact all-row replay failed")
                fractions = [
                    Fraction(str(coefficients[index, 0])) for index in range(exact_rank)
                ]
                scale = 1
                for coefficient in fractions:
                    scale = math.lcm(scale, coefficient.denominator)
                integers = [int(coefficient * scale) for coefficient in fractions]
                require(scale > 0 and any(integers), "invalid denominator clearing")
                lhs = [
                    sum(
                        fractions[column] * basis_rows[row][column]
                        for column in range(exact_rank)
                    )
                    for row in range(ROWS)
                ]
                require(
                    lhs == [Fraction(value) for value in target],
                    "independent rational row replay failed",
                )
                first_nonzero = next(index for index, value in enumerate(integers) if value)
                mutant = integers[:]
                mutant[first_nonzero] += 1
                mutant_residuals = [
                    sum(
                        mutant[column] * basis_rows[row][column]
                        for column in range(exact_rank)
                    )
                    - scale * target[row]
                    for row in range(ROWS)
                ]
                coefficient_mutant_rejected = any(mutant_residuals)
                require(coefficient_mutant_rejected, "integer coefficient mutant escaped")
                trials.append(
                    {
                        "iteration": iteration,
                        "selected_columns": len(selected_sequences),
                        "exact_rank": exact_rank,
                        "exact_augmented_rank": augmented_rank,
                        "result": "EXACT_Q_MEMBER",
                    }
                )
                receipt = {
                    "rows": ROWS,
                    "columns": RECORDS,
                    "descriptors_sha256": row_document["descriptors_sha256"],
                    "targets_sha256": row_document["targets_i128_le_sha256"],
                    "selected_sequences_sha256": digest_u64(support_sequences),
                    "selected_basis_sha256": selected_basis_digest(basis_rows),
                    "exact_replay_sha256": exact_replay_digest(lhs),
                    "all_rows_replayed": True,
                    "coefficient_mutant_rejected": coefficient_mutant_rejected,
                }
                result: dict[str, object] = {
                    "schema": "max11-g0117-fresh-q-cegis-result-v1",
                    "result": "FRESH_Q_MEMBER_ALL_ROWS_REPLAYED",
                    "claim_boundary": (
                        "Exact-Q membership on the complete accumulated 313-row iteration-1 "
                        "system only; not a global identity, family-completeness theorem, or MAX11 result."
                    ),
                    "paths": paths,
                    "bindings": bindings,
                    "receipt": receipt,
                    "modular_scan_result": modular_scan["result"],
                    "initial_selected_sequences": initial_sequences,
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_columns": support_columns,
                    "coefficients": [str(value) for value in fractions],
                    "fresh_target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "trials": trials,
                    "planted_controls": controls,
                    "wall_seconds": time.perf_counter() - started,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                write_exclusive(output_path, result)
                result_sha256 = sha256_path(output_path)
                nonzero_terms = [
                    {"sequence": sequence, "coefficient": str(coefficient)}
                    for sequence, coefficient in zip(
                        support_sequences, integers, strict=True
                    )
                    if coefficient
                ]
                certificate = {
                    "schema": CERTIFICATE_SCHEMA,
                    "claim_boundary": CERTIFICATE_BOUNDARY,
                    "source_cegis": {
                        "sha256": result_sha256,
                        "result_path": result_path,
                        "schema": result["schema"],
                        "result": result["result"],
                        "paths": paths,
                        "bindings": bindings,
                        "receipt": receipt,
                    },
                    "target_scale": str(scale),
                    "terms": nonzero_terms,
                }
                write_exclusive(certificate_path, certificate)
                return result

            separator, pairing, free_row = first_target_separator(
                candidate, integer_rows, target
            )
            violation = first_separator_violation(cache, coordinate, separator)
            trials.append(
                {
                    "iteration": iteration,
                    "selected_columns": len(selected_sequences),
                    "exact_rank": exact_rank,
                    "exact_augmented_rank": augmented_rank,
                    "result": (
                        "SEPARATOR_VIOLATED_BY_FULL_FAMILY_COLUMN"
                        if violation is not None
                        else "EXACT_Q_NONMEMBER_FULL_FAMILY"
                    ),
                    "separator_target_pairing": str(pairing),
                    "separator_free_row": free_row,
                    "first_violating_sequence": None if violation is None else violation[0],
                    "first_violating_price": None if violation is None else str(violation[1]),
                }
            )
            if violation is None:
                result = {
                    "schema": "max11-g0117-fresh-q-cegis-result-v1",
                    "result": "EXACT_Q_NONMEMBER_FULL_FAMILY",
                    "claim_boundary": (
                        "Exact nonmembership in the fixed 163,740-column family on the accumulated "
                        "313 rows; not an unrestricted two-hidden-layer lower bound."
                    ),
                    "paths": paths,
                    "bindings": bindings,
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_columns_exactly_annihilated": True,
                    "trials": trials,
                    "planted_controls": controls,
                    "wall_seconds": time.perf_counter() - started,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                write_exclusive(output_path, result)
                return result
            selected_sequences.append(violation[0])
            selected_sequences.sort()

    raise ExactError("column generation exceeded the finite row bound")


def self_test() -> None:
    controls = planted_controls()
    require(all(controls.values()), "planted controls failed")
    require(digest_strings(["a", "b"]) != digest_strings(["b", "a"]), "reorder escaped")
    member = qmatrix([[1, 0], [0, 1], [1, 1]])
    rhs = qmatrix([[2], [3], [5]])
    solution = qmatrix([[1, 0], [0, 1]]).solve(qmatrix([[2], [3]]))
    require(member * solution == rhs, "exact member control failed")
    mutant = fmpq_mat(solution)
    mutant[0, 0] += 1
    require(member * mutant != rhs, "coefficient mutant escaped")
    print("fresh-q-cegis-exact-self-test: PASS")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    if args.self_test:
        require(not args.paths, "--self-test takes no paths")
        self_test()
        return
    require(len(args.paths) == 9, "expected 9 paths")
    result = solve(*(Path(value) for value in args.paths))
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
