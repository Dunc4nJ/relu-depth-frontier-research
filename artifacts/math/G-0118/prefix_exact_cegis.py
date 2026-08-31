#!/usr/bin/env python3
"""Exact 313-row CEGIS on a frozen early prefix plus the panel basis."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import mmap
import os
from pathlib import Path
import resource
import sys
import time
from typing import Iterable, Sequence

from flint import fmpq_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREFIX_EXACT_CEGIS_PREREGISTRATION.md"
HELPER_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"
INPUT_PATH = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
SCAN_PATH = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
RETAINED_PATH = ROOT / "artifacts/math/G-0113/panel_retained_columns_v1.json"
COORDINATE_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json"
CACHE_PATH = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"

PREFIX_RECORDS = 40_000
PANEL_ROWS = 301
ROWS = 313
N = 11
COLUMN_BYTES = PANEL_ROWS * 16
PREFIX_BYTES = PREFIX_RECORDS * COLUMN_BYTES
PREFIX_SHA256 = "d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde"
EXPECTED = {
    INPUT_PATH: "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    SCAN_PATH: "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e",
    RETAINED_PATH: "615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393",
    COORDINATE_PATH: "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071",
    HELPER_PATH: "e4cc1d565b0e3bb7adf547a0ddc5265bc26a8ea36dbe56c82868cf0b51a581cd",
}
DIRECTION = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4]


class PrefixError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PrefixError(message)


def sha256_path(path: Path, limit: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = limit
    with path.open("rb") as source:
        while remaining is None or remaining:
            size = 1 << 20 if remaining is None else min(1 << 20, remaining)
            block = source.read(size)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    require(remaining in (None, 0), f"short file while hashing {path}")
    return digest.hexdigest()


def load_helper():
    spec = importlib.util.spec_from_file_location("g0117_fresh_q_helper", HELPER_PATH)
    require(spec is not None and spec.loader is not None, "cannot load exact helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def panel_from_prefix(cache: mmap.mmap, sequence: int) -> list[int]:
    require(0 <= sequence < PREFIX_RECORDS, "sequence outside frozen prefix")
    offset = sequence * COLUMN_BYTES
    return [
        int.from_bytes(cache[offset + 16 * row : offset + 16 * (row + 1)], "little", signed=True)
        for row in range(PANEL_ROWS)
    ]


def appended(coordinate: dict[str, object], sequence: int) -> list[int]:
    linear = [int(value) for value in coordinate["linear_vectors"][sequence]]
    hinge = int(coordinate["hinge_coefficients"][sequence])
    return linear + [hinge]


def full_column(
    cache: mmap.mmap,
    coordinate: dict[str, object],
    retained: dict[int, list[int]],
    sequence: int,
) -> list[int]:
    if sequence < PREFIX_RECORDS:
        panel = panel_from_prefix(cache, sequence)
        if sequence in retained:
            require(panel == retained[sequence], "retained/cache vector mismatch")
    else:
        require(sequence in retained, "out-of-prefix sequence lacks retained vector")
        panel = retained[sequence]
    column = panel + appended(coordinate, sequence)
    require(len(column) == ROWS, "column dimension drift")
    return column


def matrix_rows(columns: Sequence[Sequence[int]]) -> list[list[int]]:
    require(columns and all(len(column) == ROWS for column in columns), "ragged columns")
    return [[int(column[row]) for column in columns] for row in range(ROWS)]


def first_violation(
    cache: mmap.mmap,
    coordinate: dict[str, object],
    retained: dict[int, list[int]],
    family: Sequence[int],
    separator: Sequence[int],
) -> tuple[int, int] | None:
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    for sequence in family:
        column = full_column(cache, coordinate, retained, sequence)
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price
    return None


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    require(not output.exists(), "refusing to overwrite output")
    start_script_hash = sha256_path(SCRIPT)
    bindings = {str(path.relative_to(ROOT)): sha256_path(path) for path in EXPECTED}
    require(bindings == {str(path.relative_to(ROOT)): value for path, value in EXPECTED.items()}, "input drift")
    require(CACHE_PATH.stat().st_size >= PREFIX_BYTES, "live cache has not completed frozen prefix")
    require(sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "frozen prefix hash drift")

    helper = load_helper()
    source = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    scan = json.loads(SCAN_PATH.read_text(encoding="utf-8"))
    retained_document = json.loads(RETAINED_PATH.read_text(encoding="utf-8"))
    coordinate = json.loads(COORDINATE_PATH.read_text(encoding="utf-8"))
    require(source["schema"] == "max11-g0113-panel-solver-input-v1", "input schema drift")
    require(coordinate["direction"] == DIRECTION, "hinge direction drift")
    require(len(coordinate["linear_vectors"]) == 163_740, "coordinate census drift")
    require(len(scan["primes"]) == 2, "prime census drift")
    initial = [int(value) for value in scan["primes"][0]["selected_sequences"]]
    require(initial == [int(value) for value in scan["primes"][1]["selected_sequences"]], "prime bases differ")
    require(len(initial) == len(set(initial)) == 115, "panel basis census drift")
    retained = {
        int(record["sequence"]): [int(value) for value in record["vector"]]
        for record in retained_document["columns"]
    }
    require(set(initial) <= set(retained), "panel basis missing retained vectors")

    family = list(range(PREFIX_RECORDS)) + sorted(set(initial) - set(range(PREFIX_RECORDS)))
    require(len(family) == len(set(family)), "family sequence duplication")
    target = [int(value) for value in source["target"]] + [0] * N + [0]
    target[PANEL_ROWS + N - 1] = math.factorial(N)
    require(len(target) == ROWS, "target dimension drift")
    rhs = helper.qmatrix([[value] for value in target])
    selected = sorted(initial)
    trials: list[dict[str, object]] = []

    with CACHE_PATH.open("rb") as cache_file, mmap.mmap(
        cache_file.fileno(), PREFIX_BYTES, access=mmap.ACCESS_READ
    ) as cache:
        previous_rank = -1
        for iteration in range(20):
            require(selected == sorted(set(selected)), "selected sequence drift")
            columns = [full_column(cache, coordinate, retained, sequence) for sequence in selected]
            rows = matrix_rows(columns)
            candidate = helper.qmatrix(rows)
            augmented = helper.qmatrix([row + [target[index]] for index, row in enumerate(rows)])
            rank = int(candidate.rank())
            augmented_rank = int(augmented.rank())
            require(rank > previous_rank, "added column did not increase exact rank")
            previous_rank = rank
            if rank == augmented_rank:
                reduced, reduced_rank = candidate.rref()
                require(int(reduced_rank) == rank, "RREF rank drift")
                pivot_indices = helper.pivot_columns(reduced, rank, len(selected))
                support_sequences = [selected[index] for index in pivot_indices]
                support_columns = [columns[index] for index in pivot_indices]
                basis_rows = matrix_rows(support_columns)
                basis = helper.qmatrix(basis_rows)
                transposed, transposed_rank = basis.transpose().rref()
                require(int(transposed_rank) == rank, "basis rank drift")
                coordinate_rows = helper.pivot_columns(transposed, rank, ROWS)
                square = helper.qmatrix(
                    [[basis_rows[row][column] for column in range(rank)] for row in coordinate_rows]
                )
                coefficients = square.solve(helper.qmatrix([[target[row]] for row in coordinate_rows]))
                require(basis * coefficients == rhs, "all-row exact replay failed")
                fractions = [Fraction(str(coefficients[index, 0])) for index in range(rank)]
                scale = math.lcm(*(value.denominator for value in fractions))
                integers = [int(value * scale) for value in fractions]
                first_nonzero = next(index for index, value in enumerate(integers) if value)
                mutant = integers[:]
                mutant[first_nonzero] += 1
                mutant_rejected = any(
                    sum(mutant[column] * basis_rows[row][column] for column in range(rank))
                    != scale * target[row]
                    for row in range(ROWS)
                )
                require(mutant_rejected, "coefficient mutant escaped")
                trials.append({"iteration": iteration, "rank": rank, "augmented_rank": augmented_rank, "result": "EXACT_Q_MEMBER"})
                result: dict[str, object] = {
                    "schema": "max11-g0118-prefix-exact-cegis-v1",
                    "result": "PREFIX_EXACT_Q_MEMBER_ALL_313_ROWS",
                    "claim_boundary": "Exact 313-row membership in the frozen prefix-plus-panel-basis subset; not a global identity, full-family decision, or MAX11 result.",
                    "bindings": bindings,
                    "preregistration_sha256": sha256_path(PREREGISTRATION),
                    "runner_sha256": start_script_hash,
                    "prefix_records": PREFIX_RECORDS,
                    "prefix_sha256": PREFIX_SHA256,
                    "family_sequences": len(family),
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_sha256": digest_i128(
                        basis_rows[row][column] for row in range(ROWS) for column in range(rank)
                    ),
                    "target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "terms": [
                        {"sequence": sequence, "coefficient": str(coefficient)}
                        for sequence, coefficient in zip(support_sequences, integers, strict=True)
                        if coefficient
                    ],
                    "all_313_rows_replayed": True,
                    "coefficient_plus_one_mutant_rejected": mutant_rejected,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "prefix changed during execution")
                write_exclusive(output, result)
                return result

            separator, pairing, free_row = helper.first_target_separator(candidate, rows, target)
            violation = first_violation(cache, coordinate, retained, family, separator)
            trials.append({
                "iteration": iteration,
                "rank": rank,
                "augmented_rank": augmented_rank,
                "separator_target_pairing": str(pairing),
                "separator_free_row": free_row,
                "first_violating_sequence": None if violation is None else violation[0],
                "first_violating_price": None if violation is None else str(violation[1]),
                "result": "PREFIX_EXACT_Q_NONMEMBER" if violation is None else "SEPARATOR_VIOLATED",
            })
            if violation is None:
                result = {
                    "schema": "max11-g0118-prefix-exact-cegis-v1",
                    "result": "PREFIX_EXACT_Q_NONMEMBER",
                    "claim_boundary": "Exact nonmembership only in the frozen prefix-plus-panel-basis subset; not a full-family or unrestricted lower bound.",
                    "bindings": bindings,
                    "preregistration_sha256": sha256_path(PREREGISTRATION),
                    "runner_sha256": start_script_hash,
                    "prefix_records": PREFIX_RECORDS,
                    "prefix_sha256": PREFIX_SHA256,
                    "family_sequences": len(family),
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_subset_columns_exactly_annihilated": True,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "prefix changed during execution")
                write_exclusive(output, result)
                return result
            require(violation[0] not in selected, "separator selected an existing column")
            selected.append(violation[0])
            selected.sort()
    raise PrefixError("prefix CEGIS exceeded the preregistered iteration bound")


def self_test() -> None:
    helper = load_helper()
    member = helper.qmatrix([[1, 0], [0, 1], [1, 1]])
    rhs = helper.qmatrix([[2], [3], [5]])
    solution = helper.qmatrix([[1, 0], [0, 1]]).solve(helper.qmatrix([[2], [3]]))
    require(member * solution == rhs, "member control failed")
    mutant = fmpq_mat(solution)
    mutant[0, 0] += 1
    require(member * mutant != rhs, "mutation control failed")
    nonmember = helper.qmatrix([[1], [0]])
    require(int(nonmember.rank()) != int(helper.qmatrix([[1, 1], [0, 1]]).rank()), "nonmember control failed")
    print("prefix-exact-cegis-self-test: PASS")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        require(args.output is None, "self-test takes no output")
        self_test()
        return 0
    require(args.output is not None, "--output is required")
    result = run(args.output.resolve())
    print(json.dumps({"result": result["result"], "trials": result["trials"], "wall_seconds": result["wall_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
