#!/usr/bin/env python3
"""Exact prefix CEGIS for a manifest-bound list of accumulated hinge rows."""

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
import time
from typing import Iterable, Sequence

from flint import fmpq_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
CACHE_PATH = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"
INPUT_PATH = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
SCAN_PATH = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
RETAINED_PATH = ROOT / "artifacts/math/G-0113/panel_retained_columns_v1.json"
HELPER_PATH = ROOT / "artifacts/math/G-0117/fresh_q_cegis_exact.py"
N = 11
RECORDS = 163_740
I128_BYTES = 16


class AccumulatedCegisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AccumulatedCegisError(message)


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


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(I128_BYTES, "little", signed=True))
    return digest.hexdigest()


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def root_path(value: str) -> Path:
    result = (ROOT / value).resolve()
    try:
        result.relative_to(ROOT)
    except ValueError as error:
        raise AccumulatedCegisError(f"manifest path escapes root: {value}") from error
    return result


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def panel_from_prefix(cache: mmap.mmap, sequence: int, panel_rows: int) -> list[int]:
    require(sequence >= 0, "negative sequence")
    column_bytes = panel_rows * I128_BYTES
    offset = sequence * column_bytes
    return [
        int.from_bytes(
            cache[offset + I128_BYTES * row : offset + I128_BYTES * (row + 1)],
            "little",
            signed=True,
        )
        for row in range(panel_rows)
    ]


def panel_column(
    cache: mmap.mmap,
    retained: dict[int, list[int]],
    sequence: int,
    prefix_records: int,
    panel_rows: int,
) -> list[int]:
    if sequence < prefix_records:
        panel = panel_from_prefix(cache, sequence, panel_rows)
        if sequence in retained:
            require(panel == retained[sequence], "retained/cache vector mismatch")
        return panel
    require(sequence in retained, "out-of-prefix sequence lacks retained vector")
    return retained[sequence]


def full_column(
    cache: mmap.mmap,
    coordinates: Sequence[dict[str, object]],
    retained: dict[int, list[int]],
    sequence: int,
    prefix_records: int,
    panel_rows: int,
    rows: int,
) -> list[int]:
    linear = [int(value) for value in coordinates[0]["linear_vectors"][sequence]]
    result = panel_column(cache, retained, sequence, prefix_records, panel_rows) + linear
    result.extend(int(coordinate["hinge_coefficients"][sequence]) for coordinate in coordinates)
    require(len(result) == rows, "column dimension drift")
    return result


def matrix_rows(columns: Sequence[Sequence[int]], rows: int) -> list[list[int]]:
    require(columns and all(len(column) == rows for column in columns), "ragged columns")
    return [[int(column[row]) for column in columns] for row in range(rows)]


def first_violation(
    cache: mmap.mmap,
    coordinates: Sequence[dict[str, object]],
    retained: dict[int, list[int]],
    family: Sequence[int],
    separator: Sequence[int],
    prefix_records: int,
    panel_rows: int,
    rows: int,
) -> tuple[int, int] | None:
    nonzero = [(row, int(value)) for row, value in enumerate(separator) if value]
    for sequence in family:
        column = full_column(
            cache, coordinates, retained, sequence, prefix_records, panel_rows, rows
        )
        price = sum(value * column[row] for row, value in nonzero)
        if price:
            return sequence, price
    return None


def load_bound_inputs(manifest_path: Path):
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    require(manifest["schema"] == "max11-g0118-prefix-accumulated-manifest-v1", "manifest schema drift")
    require(int(manifest["iteration"]) >= 3, "iteration must be at least three")
    require(int(manifest["panel_rows"]) == 301, "panel row count drift")
    require(int(manifest["linear_rows"]) == N, "linear row count drift")
    require(int(manifest["prefix_records"]) == 40_000, "prefix record count drift")
    require(int(manifest["prefix_bytes"]) == 192_640_000, "prefix byte count drift")
    require(1 <= int(manifest["max_rank_increases"]) <= 64, "rank-increase bound invalid")
    preregistration_path = root_path(str(manifest["preregistration"]))
    require(preregistration_path.is_file(), "preregistration does not exist")

    bindings: dict[str, str] = {}
    required = {INPUT_PATH, SCAN_PATH, RETAINED_PATH, HELPER_PATH}
    seen: set[Path] = set()
    for record in manifest["expected_inputs"]:
        path = root_path(str(record["path"]))
        require(path not in seen, "duplicate expected input")
        seen.add(path)
        expected = str(record["sha256"])
        actual = sha256_path(path)
        require(actual == expected, f"input drift: {record['path']}")
        bindings[str(path.relative_to(ROOT))] = actual
    require(required <= seen, "required input absent from manifest")

    coordinates: list[dict[str, object]] = []
    directions: list[list[int]] = []
    coordinate_paths: set[Path] = set()
    for record in manifest["coordinates"]:
        path = root_path(str(record["path"]))
        require(path not in coordinate_paths, "duplicate coordinate input")
        coordinate_paths.add(path)
        expected = str(record["sha256"])
        actual = sha256_path(path)
        require(actual == expected, f"coordinate input drift: {record['path']}")
        document = json.loads(path.read_text(encoding="utf-8"))
        direction = [int(value) for value in record["direction"]]
        require(len(direction) == N and sum(direction) == 0, "invalid hinge direction")
        require([int(value) for value in document["direction"]] == direction, "coordinate direction drift")
        require(int(document["records"]) == RECORDS, "coordinate census drift")
        require(len(document["hinge_coefficients"]) == RECORDS, "hinge stream length drift")
        require(len(document["linear_vectors"]) == RECORDS, "linear stream length drift")
        coordinates.append(document)
        directions.append(direction)
        bindings[str(path.relative_to(ROOT))] = actual
    require(len(coordinates) == int(manifest["iteration"]), "coordinate/iteration mismatch")
    first_linear_digest = coordinates[0]["linear_vectors_i64_le_sha256"]
    first_linear_vectors = coordinates[0]["linear_vectors"]
    for coordinate in coordinates[1:]:
        require(coordinate["linear_vectors_i64_le_sha256"] == first_linear_digest, "linear digest drift")
        require(coordinate["linear_vectors"] == first_linear_vectors, "linear vectors disagree")
    return manifest, bindings, coordinates, directions, preregistration_path


def run(manifest_path: Path, output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    require(not output.exists(), "refusing to overwrite output")
    require(manifest_path.is_file(), "manifest does not exist")
    manifest_path = manifest_path.resolve()
    try:
        manifest_path.relative_to(ROOT)
    except ValueError as error:
        raise AccumulatedCegisError("manifest escapes project root") from error
    start_script_hash = sha256_path(SCRIPT)
    manifest_hash = sha256_path(manifest_path)
    manifest, bindings, coordinates, directions, preregistration_path = load_bound_inputs(
        manifest_path
    )
    helper = load_module(HELPER_PATH, "g0117_fresh_q_helper_accumulated")

    prefix_records = int(manifest["prefix_records"])
    prefix_bytes = int(manifest["prefix_bytes"])
    prefix_hash = str(manifest["prefix_sha256"])
    panel_rows = int(manifest["panel_rows"])
    rows = panel_rows + N + len(coordinates)
    require(CACHE_PATH.stat().st_size >= prefix_bytes, "live cache has not completed frozen prefix")
    require(sha256_path(CACHE_PATH, prefix_bytes) == prefix_hash, "frozen prefix hash drift")

    source = json.loads(INPUT_PATH.read_text(encoding="utf-8"))
    scan = json.loads(SCAN_PATH.read_text(encoding="utf-8"))
    retained_document = json.loads(RETAINED_PATH.read_text(encoding="utf-8"))
    require(source["schema"] == "max11-g0113-panel-solver-input-v1", "input schema drift")
    require(len(scan["primes"]) == 2, "prime census drift")
    initial = [int(value) for value in scan["primes"][0]["selected_sequences"]]
    require(initial == [int(value) for value in scan["primes"][1]["selected_sequences"]], "prime bases differ")
    require(len(initial) == len(set(initial)) == 115, "panel basis census drift")
    retained = {
        int(record["sequence"]): [int(value) for value in record["vector"]]
        for record in retained_document["columns"]
    }
    require(set(initial) <= set(retained), "panel basis missing retained vectors")

    family = list(range(prefix_records)) + sorted(set(initial) - set(range(prefix_records)))
    require(len(family) == len(set(family)), "family sequence duplication")
    target = [int(value) for value in source["target"]] + [0] * N + [0] * len(coordinates)
    target[panel_rows + N - 1] = math.factorial(N)
    require(len(target) == rows, "target dimension drift")
    rhs = helper.qmatrix([[value] for value in target])
    selected = sorted(initial)
    trials: list[dict[str, object]] = []

    with CACHE_PATH.open("rb") as cache_file, mmap.mmap(
        cache_file.fileno(), prefix_bytes, access=mmap.ACCESS_READ
    ) as cache:
        previous_rank = -1
        for iteration in range(int(manifest["max_rank_increases"]) + 1):
            require(selected == sorted(set(selected)), "selected sequence drift")
            columns = [
                full_column(cache, coordinates, retained, sequence, prefix_records, panel_rows, rows)
                for sequence in selected
            ]
            row_matrix = matrix_rows(columns, rows)
            candidate = helper.qmatrix(row_matrix)
            augmented = helper.qmatrix(
                [row + [target[index]] for index, row in enumerate(row_matrix)]
            )
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
                basis_rows = matrix_rows(support_columns, rows)
                basis = helper.qmatrix(basis_rows)
                transposed, transposed_rank = basis.transpose().rref()
                require(int(transposed_rank) == rank, "basis rank drift")
                coordinate_rows = helper.pivot_columns(transposed, rank, rows)
                square = helper.qmatrix(
                    [[basis_rows[row][column] for column in range(rank)] for row in coordinate_rows]
                )
                coefficients = square.solve(
                    helper.qmatrix([[target[row]] for row in coordinate_rows])
                )
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
                    for row in range(rows)
                )
                require(mutant_rejected, "coefficient mutant escaped")
                trials.append(
                    {"iteration": iteration, "rank": rank, "augmented_rank": augmented_rank, "result": "EXACT_Q_MEMBER"}
                )
                result: dict[str, object] = {
                    "schema": "max11-g0118-prefix-exact-cegis-accumulated-v1",
                    "iteration": int(manifest["iteration"]),
                    "result": f"PREFIX_EXACT_Q_MEMBER_ALL_{rows}_ROWS",
                    "claim_boundary": f"Exact {rows}-row membership in the frozen prefix-plus-panel-basis subset; not a global identity, full-family decision, family-completeness result, or MAX11 theorem.",
                    "bindings": bindings,
                    "manifest_path": str(manifest_path.relative_to(ROOT)),
                    "manifest_sha256": manifest_hash,
                    "preregistration_path": str(preregistration_path.relative_to(ROOT)),
                    "preregistration_sha256": sha256_path(preregistration_path),
                    "runner_sha256": start_script_hash,
                    "prefix_records": prefix_records,
                    "prefix_sha256": prefix_hash,
                    "family_sequences": len(family),
                    "hinge_directions": directions,
                    "support_sequences": support_sequences,
                    "coordinate_rows": coordinate_rows,
                    "selected_basis_sha256": digest_i128(
                        basis_rows[row][column] for row in range(rows) for column in range(rank)
                    ),
                    "target_scale": str(scale),
                    "integer_coefficients": [str(value) for value in integers],
                    "terms": [
                        {"sequence": sequence, "coefficient": str(coefficient)}
                        for sequence, coefficient in zip(support_sequences, integers, strict=True)
                        if coefficient
                    ],
                    "all_rows_replayed": True,
                    "coefficient_plus_one_mutant_rejected": mutant_rejected,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(sha256_path(manifest_path) == manifest_hash, "manifest changed during execution")
                require(sha256_path(CACHE_PATH, prefix_bytes) == prefix_hash, "prefix changed during execution")
                write_exclusive(output, result)
                return result

            separator, pairing, free_row = helper.first_target_separator(
                candidate, row_matrix, target
            )
            violation = first_violation(
                cache,
                coordinates,
                retained,
                family,
                separator,
                prefix_records,
                panel_rows,
                rows,
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
                    "schema": "max11-g0118-prefix-exact-cegis-accumulated-v1",
                    "iteration": int(manifest["iteration"]),
                    "result": "PREFIX_EXACT_Q_NONMEMBER",
                    "claim_boundary": "Exact nonmembership only in the frozen prefix-plus-panel-basis subset; not a full-family or unrestricted lower bound.",
                    "bindings": bindings,
                    "manifest_path": str(manifest_path.relative_to(ROOT)),
                    "manifest_sha256": manifest_hash,
                    "preregistration_path": str(preregistration_path.relative_to(ROOT)),
                    "preregistration_sha256": sha256_path(preregistration_path),
                    "runner_sha256": start_script_hash,
                    "prefix_records": prefix_records,
                    "prefix_sha256": prefix_hash,
                    "family_sequences": len(family),
                    "hinge_directions": directions,
                    "primitive_integer_separator": [str(value) for value in separator],
                    "separator_target_pairing": str(pairing),
                    "all_subset_columns_exactly_annihilated": True,
                    "trials": trials,
                    "wall_seconds": time.perf_counter() - begun,
                    "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                }
                require(sha256_path(SCRIPT) == start_script_hash, "runner changed during execution")
                require(sha256_path(manifest_path) == manifest_hash, "manifest changed during execution")
                require(sha256_path(CACHE_PATH, prefix_bytes) == prefix_hash, "prefix changed during execution")
                write_exclusive(output, result)
                return result
            require(violation[0] not in selected, "separator selected an existing column")
            selected.append(violation[0])
            selected.sort()
    raise AccumulatedCegisError("prefix CEGIS exceeded the manifest rank-increase bound")


def self_test() -> None:
    helper = load_module(HELPER_PATH, "g0117_fresh_q_helper_accumulated_test")
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
    escaped = False
    try:
        root_path("../outside")
    except AccumulatedCegisError:
        escaped = True
    require(escaped, "path containment control failed")
    print("prefix-exact-cegis-accumulated-self-test: PASS")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    if args.self_test:
        require(args.manifest is None and args.output is None, "self-test takes no paths")
        self_test()
        return 0
    require(args.manifest is not None and args.output is not None, "--manifest and --output are required")
    result = run(args.manifest.resolve(), args.output.resolve())
    print(
        json.dumps(
            {"result": result["result"], "trials": result["trials"], "wall_seconds": result["wall_seconds"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
