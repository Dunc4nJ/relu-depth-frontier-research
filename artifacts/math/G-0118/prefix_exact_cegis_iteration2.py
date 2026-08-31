#!/usr/bin/env python3
"""Exact 314-row CEGIS after appending the first global counterexample."""

from __future__ import annotations

import argparse
from fractions import Fraction
import importlib.util
import json
import math
import mmap
import os
from pathlib import Path
import resource
import time
from typing import Sequence

from flint import fmpq_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
BASE_PATH = HERE / "prefix_exact_cegis.py"
PREREGISTRATION = HERE / "ITERATION2_PREFIX_PREREGISTRATION.md"
HELPER_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"
INPUT_PATH = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
SCAN_PATH = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
RETAINED_PATH = ROOT / "artifacts/math/G-0113/panel_retained_columns_v1.json"
COORDINATE1_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json"
COORDINATE2_PATH = HERE / "iteration2_residual_coordinate_v1.json"
CACHE_PATH = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"
PREVIOUS_RESULT_PATH = HERE / "prefix_exact_cegis_v1.json"
PREVIOUS_REPLAY_PATH = HERE / "prefix_global_modular_replay_v1.json"

PREFIX_RECORDS = 40_000
PANEL_ROWS = 301
N = 11
ROWS = 314
COLUMN_BYTES = PANEL_ROWS * 16
PREFIX_BYTES = PREFIX_RECORDS * COLUMN_BYTES
PREFIX_SHA256 = "d88dc897dbbfd77b98dd4edf2cecfd9696c5760e7c0dd3f2184b626659af7cde"
DIRECTION1 = [0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4]
DIRECTION2 = [0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3]
EXPECTED = {
    BASE_PATH: "6a152c1fbfe72101affeff05aea35367a0ae14d293c633c13f51ec7b260d14bf",
    HELPER_PATH: "ee422e6e36085e26ddd83a75f8901c6a6efbe3fd2a99e80e280f9449d0ed8281",
    INPUT_PATH: "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    SCAN_PATH: "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e",
    RETAINED_PATH: "615e264dd64e43c8374131e6934e9728ee4c043a8b15f19ed50ec8d676fe1393",
    COORDINATE1_PATH: "c9acf62ea84d7e3d0405f2a5f778f431f8c3a1b16c8b9aefa453b62cfc929071",
    COORDINATE2_PATH: "41255b1176ca95ac8f2d43e35c8396266cf9d2c71fcae77c14dffb54ffc58a3f",
    PREVIOUS_RESULT_PATH: "bad55cb45134cfdab3be86b3d3c676807acb402d69b6d37d0af59767152e531c",
    PREVIOUS_REPLAY_PATH: "ee7ccc77c34454845b59e709507b901d814263242d8ff9b66e4257f06e0e90d4",
}


class Iteration2Error(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise Iteration2Error(message)


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def panel_column(base, cache: mmap.mmap, retained: dict[int, list[int]], sequence: int) -> list[int]:
    if sequence < PREFIX_RECORDS:
        panel = base.panel_from_prefix(cache, sequence)
        if sequence in retained:
            require(panel == retained[sequence], "retained/cache vector mismatch")
        return panel
    require(sequence in retained, "out-of-prefix sequence lacks retained vector")
    return retained[sequence]


def full_column(
    base,
    cache: mmap.mmap,
    coordinate1: dict[str, object],
    coordinate2: dict[str, object],
    retained: dict[int, list[int]],
    sequence: int,
) -> list[int]:
    linear1 = [int(value) for value in coordinate1["linear_vectors"][sequence]]
    linear2 = [int(value) for value in coordinate2["linear_vectors"][sequence]]
    require(linear1 == linear2, "linear coordinate streams disagree")
    result = panel_column(base, cache, retained, sequence) + linear1 + [
        int(coordinate1["hinge_coefficients"][sequence]),
        int(coordinate2["hinge_coefficients"][sequence]),
    ]
    require(len(result) == ROWS, "column dimension drift")
    return result


def matrix_rows(columns: Sequence[Sequence[int]]) -> list[list[int]]:
    require(columns and all(len(column) == ROWS for column in columns), "ragged columns")
    return [[int(column[row]) for column in columns] for row in range(ROWS)]


def first_violation(
    base,
    cache: mmap.mmap,
    coordinate1: dict[str, object],
    coordinate2: dict[str, object],
    retained: dict[int, list[int]],
    family: Sequence[int],
    separator: Sequence[int],
) -> tuple[int, int] | None:
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    for sequence in family:
        column = full_column(base, cache, coordinate1, coordinate2, retained, sequence)
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price
    return None


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    require(not output.exists(), "refusing to overwrite output")
    base = load_module(BASE_PATH, "g0118_iteration1_base")
    helper = load_module(HELPER_PATH, "g0117_fresh_q_helper_iteration2")
    start_script_hash = base.sha256_path(SCRIPT)
    bindings = {str(path.relative_to(ROOT)): base.sha256_path(path) for path in EXPECTED}
    require(
        bindings == {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()},
        "input drift",
    )
    require(CACHE_PATH.stat().st_size >= PREFIX_BYTES, "live cache has not completed frozen prefix")
    require(base.sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "frozen prefix hash drift")

    source = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    scan = json.loads(SCAN_PATH.read_text(encoding="utf-8"))
    retained_document = json.loads(RETAINED_PATH.read_text(encoding="utf-8"))
    coordinate1 = json.loads(COORDINATE1_PATH.read_text(encoding="utf-8"))
    coordinate2 = json.loads(COORDINATE2_PATH.read_text(encoding="utf-8"))
    require(source["schema"] == "max11-g0113-panel-solver-input-v1", "input schema drift")
    require(coordinate1["direction"] == DIRECTION1, "first hinge direction drift")
    require(coordinate2["direction"] == DIRECTION2, "second hinge direction drift")
    require(coordinate1["records"] == coordinate2["records"] == 163_740, "coordinate census drift")
    require(
        coordinate1["linear_vectors_i64_le_sha256"] == coordinate2["linear_vectors_i64_le_sha256"],
        "linear stream digest drift",
    )
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
    target = [int(value) for value in source["target"]] + [0] * N + [0, 0]
    target[PANEL_ROWS + N - 1] = math.factorial(N)
    require(len(target) == ROWS, "target dimension drift")
    rhs = helper.qmatrix([[value] for value in target])
    selected = sorted(initial)
    trials: list[dict[str, object]] = []

    with CACHE_PATH.open("rb") as cache_file, mmap.mmap(
        cache_file.fileno(), PREFIX_BYTES, access=mmap.ACCESS_READ
    ) as cache:
        previous_rank = -1
        for iteration in range(25):
            require(selected == sorted(set(selected)), "selected sequence drift")
            columns = [
                full_column(base, cache, coordinate1, coordinate2, retained, sequence)
                for sequence in selected
            ]
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
                trials.append(
                    {"iteration": iteration, "rank": rank, "augmented_rank": augmented_rank, "result": "EXACT_Q_MEMBER"}
                )
                result: dict[str, object] = {
                    "schema": "max11-g0118-prefix-exact-cegis-iteration2-v1",
                    "result": "PREFIX_EXACT_Q_MEMBER_ALL_314_ROWS",
                    "claim_boundary": "Exact 314-row membership in the frozen prefix-plus-panel-basis subset; not a global identity, full-family decision, family-completeness result, or MAX11 theorem.",
                    "bindings": bindings,
                    "preregistration_sha256": base.sha256_path(PREREGISTRATION),
                    "runner_sha256": start_script_hash,
                    "prefix_records": PREFIX_RECORDS,
                    "prefix_sha256": PREFIX_SHA256,
                    "family_sequences": len(family),
                    "hinge_directions": [DIRECTION1, DIRECTION2],
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_sha256": base.digest_i128(
                        basis_rows[row][column] for row in range(ROWS) for column in range(rank)
                    ),
                    "target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "terms": [
                        {"sequence": sequence, "coefficient": str(coefficient)}
                        for sequence, coefficient in zip(support_sequences, integers, strict=True)
                        if coefficient
                    ],
                    "all_314_rows_replayed": True,
                    "coefficient_plus_one_mutant_rejected": mutant_rejected,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(base.sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(base.sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "prefix changed during execution")
                write_exclusive(output, result)
                return result

            separator, pairing, free_row = helper.first_target_separator(candidate, rows, target)
            violation = first_violation(
                base, cache, coordinate1, coordinate2, retained, family, separator
            )
            trials.append(
                {
                    "iteration": iteration,
                    "rank": rank,
                    "augmented_rank": augmented_rank,
                    "separator_target_pairing": str(pairing),
                    "separator_free_row": free_row,
                    "first_violating_sequence": None if violation is None else violation[0],
                    "first_violating_price": None if violation is None else str(violation[1]),
                    "result": "PREFIX_EXACT_Q_NONMEMBER" if violation is None else "SEPARATOR_VIOLATED",
                }
            )
            if violation is None:
                result = {
                    "schema": "max11-g0118-prefix-exact-cegis-iteration2-v1",
                    "result": "PREFIX_EXACT_Q_NONMEMBER",
                    "claim_boundary": "Exact nonmembership only in the frozen prefix-plus-panel-basis subset; not a full-family or unrestricted lower bound.",
                    "bindings": bindings,
                    "preregistration_sha256": base.sha256_path(PREREGISTRATION),
                    "runner_sha256": start_script_hash,
                    "prefix_records": PREFIX_RECORDS,
                    "prefix_sha256": PREFIX_SHA256,
                    "family_sequences": len(family),
                    "hinge_directions": [DIRECTION1, DIRECTION2],
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_subset_columns_exactly_annihilated": True,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(base.sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(base.sha256_path(CACHE_PATH, PREFIX_BYTES) == PREFIX_SHA256, "prefix changed during execution")
                write_exclusive(output, result)
                return result
            require(violation[0] not in selected, "separator selected an existing column")
            selected.append(violation[0])
            selected.sort()
    raise Iteration2Error("prefix CEGIS exceeded the preregistered iteration bound")


def self_test() -> None:
    helper = load_module(HELPER_PATH, "g0117_fresh_q_helper_iteration2_test")
    member = helper.qmatrix([[1, 0], [0, 1], [1, 1]])
    rhs = helper.qmatrix([[2], [3], [5]])
    solution = helper.qmatrix([[1, 0], [0, 1]]).solve(helper.qmatrix([[2], [3]]))
    require(member * solution == rhs, "member control failed")
    mutant = fmpq_mat(solution)
    mutant[0, 0] += 1
    require(member * mutant != rhs, "mutation control failed")
    nonmember = helper.qmatrix([[1], [0]])
    require(
        int(nonmember.rank()) != int(helper.qmatrix([[1, 1], [0, 1]]).rank()),
        "nonmember control failed",
    )
    print("prefix-exact-cegis-iteration2-self-test: PASS")


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
    print(
        json.dumps(
            {"result": result["result"], "trials": result["trials"], "wall_seconds": result["wall_seconds"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
