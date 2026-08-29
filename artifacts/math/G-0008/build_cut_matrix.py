#!/usr/bin/env python3
"""Exact cutting-plane search over all 9,804 minimally cyclic MAX11 classes.

The system uses internal coefficients ``a = 11! * c``.  Thus the 364
distinct-assignment orbit equations retain their integer targets, while the
complete hinge/linear target is ``11! * MAX11``.  Any serialized certificate
coefficient is divided by ``11!``.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import gzip
import hashlib
import json
from math import factorial, gcd, lcm
from pathlib import Path
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G6 = ROOT / "artifacts/math/G-0006"
sys.path.insert(0, str(G6))

import exact_lift_search as g6  # noqa: E402


SELECTION_SCHEMA = "max11-exact-hinge-cut-selection-v1"
SHARD_SCHEMA = "max11-exact-hinge-cut-shard-v1"
MATRIX_SCHEMA = "max11-exact-hinge-cut-matrix-v1"
SOLUTION_SCHEMA = "max11-exact-hinge-cut-solution-v1"
CUT_RESIDUAL_SCHEMA = "max11-exact-hinge-cut-residual-v1"
N = 11


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    print(f"{path} bytes={len(raw)} sha256={sha256_bytes(raw)}", flush=True)


def load_residual(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if value.get("schema") not in {g6.HINGE_RESIDUAL_SCHEMA, CUT_RESIDUAL_SCHEMA}:
        raise ValueError("wrong residual schema")
    if value.get("global_identity") is not False:
        raise ValueError("cut selection requires a nonzero residual")
    return value


def make_selection(
    residual_path: Path, hash_count: int, magnitude_count: int
) -> dict[str, object]:
    residual = load_residual(residual_path)
    hinges = [
        (tuple(map(int, item["direction"])), int(item["coefficient"]))
        for item in residual["hinges"]
    ]
    if len(hinges) != residual["nonzero_hinge_count"]:
        raise AssertionError("residual hinge census mismatch")
    if hash_count <= 0 or magnitude_count <= 0:
        raise ValueError("selection counts must be positive")

    by_hash = sorted(
        hinges,
        key=lambda item: (
            hashlib.sha256(bytes(value + 5 for value in item[0])).digest(),
            item[0],
        ),
    )[:hash_count]
    by_magnitude = sorted(
        hinges, key=lambda item: (-abs(item[1]), item[0])
    )[:magnitude_count]
    chosen = sorted({direction for direction, _ in by_hash + by_magnitude})
    if not chosen:
        raise AssertionError("empty cut selection")
    return {
        "schema": SELECTION_SCHEMA,
        "n": N,
        "source_residual": str(residual_path.resolve().relative_to(ROOT)),
        "source_residual_sha256": sha256_path(residual_path),
        "source_solution_sha256": residual.get(
            "solution_file_sha256", residual.get("solution_sha256")
        ),
        "source_nonzero_hinge_count": len(hinges),
        "selection_rule": (
            "union of smallest SHA256(direction entries shifted by +5) and largest "
            "absolute seed-residual coefficients; final rows lexicographically sorted"
        ),
        "hash_count_requested": hash_count,
        "magnitude_count_requested": magnitude_count,
        "selected_count": len(chosen),
        "directions": [list(direction) for direction in chosen],
    }


def load_selection(path: Path) -> tuple[dict[str, object], tuple[tuple[int, ...], ...]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != SELECTION_SCHEMA or value.get("n") != N:
        raise ValueError("wrong cut-selection schema")
    raw_directions = value.get("directions")
    if not isinstance(raw_directions, list):
        raise ValueError("cut directions are not a list")
    selected_count = value.get("selected_count")
    if type(selected_count) is not int:
        raise ValueError("selected cut count is not an integer")
    directions_list: list[tuple[int, ...]] = []
    for row_index, row in enumerate(raw_directions):
        if not isinstance(row, list) or any(type(entry) is not int for entry in row):
            raise ValueError(f"cut direction {row_index} is not an integer list")
        directions_list.append(tuple(row))
    directions = tuple(directions_list)
    if len(directions) != selected_count or list(directions) != sorted(
        set(directions)
    ):
        raise ValueError("cut direction order/census mismatch")
    for direction in directions:
        if len(direction) != N or sum(direction) != 0:
            raise ValueError("invalid hinge cut direction")
        magnitude = 0
        for entry in direction:
            magnitude = gcd(magnitude, abs(entry))
        if magnitude != 1:
            raise ValueError("hinge cut direction is not primitive")
        if g6.nonpositive_on_ordered_cone(direction):
            raise ValueError("inactive direction admitted as a hinge cut")
    return value, directions


def restricted_column(
    pair: g6.Pair, row_index: dict[tuple[int, ...], int], row_count: int
) -> np.ndarray:
    histogram = g6.direction_histogram(pair)
    linear = [5 * 2 * rank * factorial(N - 2) for rank in range(N)]
    selected = [0] * row_count
    for raw_direction, multiplicity in histogram.items():
        if not any(raw_direction):
            continue
        magnitude = 0
        for value in raw_direction:
            magnitude = gcd(magnitude, abs(value))
        first = next(value for value in raw_direction if value)
        if first < 0:
            for rank, value in enumerate(raw_direction):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // magnitude for value in raw_direction)
        else:
            primitive = tuple(value // magnitude for value in raw_direction)
        if g6.nonpositive_on_ordered_cone(primitive):
            continue
        position = row_index.get(primitive)
        if position is not None:
            selected[position] += multiplicity * magnitude
    result = np.asarray(selected + linear, dtype=np.int64)
    if result.shape != (row_count + N,):
        raise AssertionError(result.shape)
    return result


def build_shard(
    selection_path: Path,
    classes_path: Path,
    shard_index: int,
    shard_count: int,
    output_directory: Path,
) -> Path:
    if not (0 <= shard_index < shard_count):
        raise ValueError("invalid shard index/count")
    _selection, directions = load_selection(selection_path)
    classes = g6.load_classes(classes_path)
    pairs, _ = g6.raw_candidate_pairs()
    representatives = list(map(int, classes["representative_raw_indices"]))
    total = len(representatives)
    start = total * shard_index // shard_count
    stop = total * (shard_index + 1) // shard_count
    class_indices = np.arange(start, stop, dtype=np.int64)
    matrix = np.empty((len(directions) + N, stop - start), dtype=np.int64)
    row_index = {direction: index for index, direction in enumerate(directions)}
    begun = time.time()
    for local_index, class_index in enumerate(range(start, stop)):
        pair = pairs[representatives[class_index]]
        if any(a == b for side in pair for a, b in side):
            raise AssertionError("delivered minimally cyclic family is not loopless")
        matrix[:, local_index] = restricted_column(pair, row_index, len(directions))
        if (local_index + 1) % 100 == 0:
            print(
                f"shard={shard_index}/{shard_count} columns={local_index + 1}/{stop - start} "
                f"seconds={time.time() - begun:.1f}",
                flush=True,
            )

    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"shard-{shard_index:02d}-of-{shard_count:02d}.npz"
    np.savez_compressed(
        destination,
        schema=np.asarray([SHARD_SCHEMA]),
        selection_sha256=np.asarray([sha256_path(selection_path)]),
        classes_sha256=np.asarray([sha256_path(classes_path)]),
        raw_pair_list_sha256=np.asarray([classes["raw_pair_list_sha256"]]),
        shard_index=np.asarray([shard_index], dtype=np.int64),
        shard_count=np.asarray([shard_count], dtype=np.int64),
        class_indices=class_indices,
        matrix=matrix,
    )
    print(
        f"{destination} columns={stop-start} matrix_sha256={sha256_bytes(matrix.tobytes(order='C'))} "
        f"file_sha256={sha256_path(destination)} seconds={time.time()-begun:.1f}",
        flush=True,
    )
    return destination


def assemble(
    selection_path: Path,
    classes_path: Path,
    shard_directory: Path,
    shard_count: int,
    output: Path,
) -> None:
    _selection, directions = load_selection(selection_path)
    classes = g6.load_classes(classes_path)
    matrices = []
    indices = []
    shard_files = []
    for shard_index in range(shard_count):
        path = shard_directory / f"shard-{shard_index:02d}-of-{shard_count:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != SHARD_SCHEMA:
                raise ValueError(f"shard schema mismatch: {path}")
            if str(data["selection_sha256"][0]) != sha256_path(selection_path):
                raise ValueError(f"shard selection mismatch: {path}")
            if str(data["classes_sha256"][0]) != sha256_path(classes_path):
                raise ValueError(f"shard class mismatch: {path}")
            if int(data["shard_index"][0]) != shard_index:
                raise ValueError(f"shard index mismatch: {path}")
            if int(data["shard_count"][0]) != shard_count:
                raise ValueError(f"shard count mismatch: {path}")
            matrices.append(data["matrix"])
            indices.append(data["class_indices"])
        shard_files.append(
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)}
        )
    matrix = np.concatenate(matrices, axis=1)
    class_indices = np.concatenate(indices)
    expected = np.arange(int(classes["class_count"]), dtype=np.int64)
    if not np.array_equal(class_indices, expected):
        raise AssertionError("shard class coverage/order mismatch")
    if matrix.shape != (len(directions) + N, len(expected)):
        raise AssertionError(matrix.shape)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        schema=np.asarray([MATRIX_SCHEMA]),
        selection_sha256=np.asarray([sha256_path(selection_path)]),
        classes_sha256=np.asarray([sha256_path(classes_path)]),
        class_indices=class_indices,
        matrix=matrix,
        shard_manifest_json=np.asarray(
            [json.dumps(shard_files, sort_keys=True, separators=(",", ":"))]
        ),
    )
    print(
        f"{output} shape={matrix.shape} matrix_sha256={sha256_bytes(matrix.tobytes(order='C'))} "
        f"file_sha256={sha256_path(output)}",
        flush=True,
    )


def merge_cut_matrices(
    selection_paths: list[Path],
    matrix_paths: list[Path],
    classes_path: Path,
    output_selection: Path,
    output_matrix: Path,
) -> None:
    """Merge independently built cut batches without recomputing any column.

    Each input matrix carries one copy of the eleven linear rows.  They must be
    byte-identical.  Hinge directions are deduplicated by their canonical
    tuple; an overlapping row is accepted only if its complete 9,804-entry
    column-family vector agrees exactly in every input.
    """
    if len(selection_paths) != len(matrix_paths) or len(selection_paths) < 2:
        raise ValueError("merge requires matching lists of at least two inputs")
    classes = g6.load_classes(classes_path)
    class_count = int(classes["class_count"])
    expected_indices = np.arange(class_count, dtype=np.int64)
    rows: dict[tuple[int, ...], np.ndarray] = {}
    linear_block: np.ndarray | None = None
    source_manifest = []

    for selection_path, matrix_path in zip(selection_paths, matrix_paths):
        _selection, directions = load_selection(selection_path)
        with np.load(matrix_path, allow_pickle=False) as data:
            if str(data["schema"][0]) != MATRIX_SCHEMA:
                raise ValueError(f"cut matrix schema mismatch: {matrix_path}")
            if str(data["selection_sha256"][0]) != sha256_path(selection_path):
                raise ValueError(f"cut matrix selection mismatch: {matrix_path}")
            if str(data["classes_sha256"][0]) != sha256_path(classes_path):
                raise ValueError(f"cut matrix classes mismatch: {matrix_path}")
            indices = np.asarray(data["class_indices"], dtype=np.int64)
            matrix = np.asarray(data["matrix"], dtype=np.int64)
        if not np.array_equal(indices, expected_indices):
            raise ValueError(f"cut matrix class order mismatch: {matrix_path}")
        if matrix.shape != (len(directions) + N, class_count):
            raise ValueError(f"cut matrix shape mismatch: {matrix_path}: {matrix.shape}")

        current_linear = matrix[-N:, :]
        if linear_block is None:
            linear_block = current_linear.copy()
        elif not np.array_equal(linear_block, current_linear):
            raise ValueError(f"linear-row disagreement: {matrix_path}")
        for row_index, direction in enumerate(directions):
            current = matrix[row_index, :]
            previous = rows.get(direction)
            if previous is None:
                rows[direction] = current.copy()
            elif not np.array_equal(previous, current):
                raise ValueError(
                    f"overlapping hinge-row disagreement at direction {direction}"
                )
        source_manifest.append(
            {
                "selection": str(selection_path.resolve().relative_to(ROOT)),
                "selection_sha256": sha256_path(selection_path),
                "cut_matrix": str(matrix_path.resolve().relative_to(ROOT)),
                "cut_matrix_sha256": sha256_path(matrix_path),
                "cut_matrix_int64_c_sha256": sha256_bytes(
                    matrix.tobytes(order="C")
                ),
                "selected_count": len(directions),
            }
        )

    assert linear_block is not None
    directions = tuple(sorted(rows))
    merged = np.empty((len(directions) + N, class_count), dtype=np.int64)
    for row_index, direction in enumerate(directions):
        merged[row_index, :] = rows[direction]
    merged[-N:, :] = linear_block
    selection = {
        "schema": SELECTION_SCHEMA,
        "n": N,
        "selection_rule": (
            "lexicographically sorted exact union of independently selected cut batches"
        ),
        "selected_count": len(directions),
        "directions": [list(direction) for direction in directions],
        "source_selections": source_manifest,
    }
    write_json(output_selection, selection)
    output_matrix.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output_matrix,
        schema=np.asarray([MATRIX_SCHEMA]),
        selection_sha256=np.asarray([sha256_path(output_selection)]),
        classes_sha256=np.asarray([sha256_path(classes_path)]),
        class_indices=expected_indices,
        matrix=merged,
        source_manifest_json=np.asarray(
            [json.dumps(source_manifest, sort_keys=True, separators=(",", ":"))]
        ),
    )
    print(
        f"{output_matrix} shape={merged.shape} "
        f"matrix_sha256={sha256_bytes(merged.tobytes(order='C'))} "
        f"file_sha256={sha256_path(output_matrix)}",
        flush=True,
    )


def pivot_columns(rref_matrix, row_count: int, column_count: int) -> list[int]:
    pivots = []
    for row in range(row_count):
        for column in range(column_count):
            if rref_matrix[row, column]:
                pivots.append(column)
                break
    return pivots


def solve(
    selection_path: Path,
    classes_path: Path,
    cut_matrix_path: Path,
    orbit_directory: Path,
    prime: int,
    output: Path,
) -> None:
    from flint import fmpq, fmpq_mat, nmod_mat

    _selection, directions = load_selection(selection_path)
    classes = g6.load_classes(classes_path)
    representatives = np.asarray(classes["representative_raw_indices"], dtype=np.int64)
    raw_orbits, orbit_target, _profiles, orbit_files = g6.load_orbit_matrix(
        orbit_directory, str(classes["candidate_metadata_sha256"])
    )
    orbit_matrix = raw_orbits[:, representatives]
    with np.load(cut_matrix_path, allow_pickle=False) as data:
        if str(data["schema"][0]) != MATRIX_SCHEMA:
            raise ValueError("cut matrix schema mismatch")
        if str(data["selection_sha256"][0]) != sha256_path(selection_path):
            raise ValueError("cut matrix selection mismatch")
        if str(data["classes_sha256"][0]) != sha256_path(classes_path):
            raise ValueError("cut matrix classes mismatch")
        cut_matrix = data["matrix"]
        class_indices = data["class_indices"]
    if not np.array_equal(
        class_indices, np.arange(int(classes["class_count"]), dtype=np.int64)
    ):
        raise ValueError("cut matrix class order mismatch")
    if cut_matrix.shape != (len(directions) + N, len(representatives)):
        raise ValueError("cut matrix shape mismatch")

    cut_target = np.zeros(len(directions) + N, dtype=np.int64)
    cut_target[-1] = factorial(N)
    system = np.concatenate((orbit_matrix, cut_matrix), axis=0)
    target = np.concatenate((orbit_target, cut_target), axis=0)
    if system.shape[0] != target.shape[0]:
        raise AssertionError("system target length mismatch")
    print(f"system shape={system.shape} prime={prime}", flush=True)

    begun = time.time()
    modular = nmod_mat(system.tolist(), prime)
    rref, rank = modular.rref()
    print(f"candidate rank mod {prime} = {rank} seconds={time.time()-begun:.1f}", flush=True)
    augmented = np.column_stack((system, target))
    augmented_rank = nmod_mat(augmented.tolist(), prime).rank()
    member = augmented_rank == rank
    print(
        f"augmented rank mod {prime} = {augmented_rank} member={member} "
        f"seconds={time.time()-begun:.1f}",
        flush=True,
    )

    base_output = {
        "schema": SOLUTION_SCHEMA,
        "n": N,
        "family": "all 9804 minimally cyclic same-component MAX10 lifts",
        "selection_sha256": sha256_path(selection_path),
        "classes_sha256": sha256_path(classes_path),
        "cut_matrix_sha256": sha256_path(cut_matrix_path),
        "cut_matrix_int64_c_sha256": sha256_bytes(cut_matrix.tobytes(order="C")),
        "orbit_input_files": orbit_files,
        "system_int64_c_sha256": sha256_bytes(system.tobytes(order="C")),
        "target_int64_c_sha256": sha256_bytes(target.tobytes(order="C")),
        "system_rows": system.shape[0],
        "candidate_columns": system.shape[1],
        "prime": prime,
        "rank_mod_prime": rank,
        "augmented_rank_mod_prime": augmented_rank,
        "target_member_mod_prime": member,
        "normalization": "internal a=11!*certificate coefficient; linear target is 11!*e_11",
    }
    if not member:
        base_output["claim_boundary"] = (
            "modular nonmembership only; a rational solution with denominator divisible by the "
            "prime is not excluded"
        )
        write_json(output, base_output)
        return

    basis_columns = pivot_columns(rref, rank, system.shape[1])
    if len(basis_columns) != rank:
        raise AssertionError("basis-column extraction failed")
    basis_modular = nmod_mat(system[:, basis_columns].tolist(), prime)
    transposed_rref, row_rank = basis_modular.transpose().rref()
    pivot_rows = pivot_columns(transposed_rref, row_rank, system.shape[0])
    if row_rank != rank or len(pivot_rows) != rank:
        raise AssertionError("pivot-row extraction failed")

    exact = fmpq_mat(rank, rank)
    rhs = fmpq_mat(rank, 1)
    for rr, source_row in enumerate(pivot_rows):
        for cc, source_column in enumerate(basis_columns):
            value = int(system[source_row, source_column])
            if value:
                exact[rr, cc] = value
        if target[source_row]:
            rhs[rr, 0] = int(target[source_row])
    exact_begun = time.time()
    coefficients = exact.solve(rhs)
    print(f"exact square solve rank={rank} seconds={time.time()-exact_begun:.1f}", flush=True)
    for source_row in range(system.shape[0]):
        value = fmpq(0)
        for cc, source_column in enumerate(basis_columns):
            entry = int(system[source_row, source_column])
            if entry:
                value += coefficients[cc, 0] * entry
        if value != int(target[source_row]):
            raise AssertionError(f"exact constraint replay failed at row {source_row}")

    pairs, _ = g6.raw_candidate_pairs()
    terms = []
    for cc, class_index in enumerate(basis_columns):
        internal = coefficients[cc, 0]
        if not internal:
            continue
        certificate_coefficient = internal / factorial(N)
        raw_index = int(representatives[class_index])
        left, right = pairs[raw_index]
        terms.append(
            {
                "coefficient": str(certificate_coefficient),
                "internal_coefficient": str(internal),
                "class_index": class_index,
                "representative_raw_index": raw_index,
                "pair": [[list(edge) for edge in left], [list(edge) for edge in right]],
            }
        )
    base_output.update(
        {
            "exact_constraint_replay": True,
            "basis_column_count": len(basis_columns),
            "nonzero_term_count": len(terms),
            "terms": terms,
            "warning": "restricted cut-system solution only; complete hinge replay required",
        }
    )
    write_json(output, base_output)


def strict_solution_terms(path: Path) -> tuple[list[g6.Pair], list[Fraction]]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != SOLUTION_SCHEMA or value.get("n") != N:
        raise ValueError("wrong cut-solution schema")
    if value.get("exact_constraint_replay") is not True:
        raise ValueError("cut solution lacks exact constraint replay")
    pairs: list[g6.Pair] = []
    coefficients: list[Fraction] = []
    for term_index, term in enumerate(value["terms"]):
        sides = term.get("pair")
        if type(sides) is not list or len(sides) != 2:
            raise ValueError(f"term {term_index} pair shape mismatch")
        parsed_sides = []
        for side_index, side in enumerate(sides):
            if type(side) is not list or len(side) != 5:
                raise ValueError(f"term {term_index} side {side_index} shape mismatch")
            parsed_edges = []
            for edge in side:
                if (
                    type(edge) is not list
                    or len(edge) != 2
                    or any(type(endpoint) is not int for endpoint in edge)
                ):
                    raise ValueError(f"term {term_index} endpoint shape mismatch")
                a, b = edge
                if not (1 <= a < b <= N):
                    raise ValueError(f"term {term_index} is not loopless/canonical")
                parsed_edges.append((a, b))
            parsed_sides.append(tuple(parsed_edges))
        coefficient = Fraction(term["coefficient"])
        if not coefficient:
            raise ValueError(f"term {term_index} has zero coefficient")
        pairs.append((parsed_sides[0], parsed_sides[1]))
        coefficients.append(coefficient)
    if len(pairs) != value.get("nonzero_term_count"):
        raise ValueError("cut-solution term census mismatch")
    return pairs, coefficients


def complete_residual(solution_path: Path, workers: int) -> dict[str, object]:
    pairs, coefficients = strict_solution_terms(solution_path)
    denominator_scale = 1
    for coefficient in coefficients:
        denominator_scale = lcm(denominator_scale, coefficient.denominator)
    integer_coefficients = [
        coefficient.numerator * (denominator_scale // coefficient.denominator)
        for coefficient in coefficients
    ]
    linear = [0] * N
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    raw_counts = [0] * len(pairs)
    with ProcessPoolExecutor(max_workers=workers) as executor:
        payloads = list(enumerate(pairs))
        for index, column in executor.map(g6._column_worker, payloads, chunksize=1):
            coefficient = integer_coefficients[index]
            raw_counts[index] = column.raw_direction_count
            for rank, value in enumerate(column.linear):
                linear[rank] += coefficient * value
            for direction, value in column.hinges.items():
                hinges[direction] += coefficient * value
    linear[-1] -= denominator_scale
    nonzero = sorted((direction, value) for direction, value in hinges.items() if value)
    return {
        "schema": CUT_RESIDUAL_SCHEMA,
        "n": N,
        "solution_sha256": sha256_path(solution_path),
        "term_count": len(pairs),
        "denominator_scale": str(denominator_scale),
        "linear_residual": [str(value) for value in linear],
        "nonzero_hinge_count": len(nonzero),
        "raw_direction_count_min": min(raw_counts, default=0),
        "raw_direction_count_max": max(raw_counts, default=0),
        "global_identity": not any(linear) and not nonzero,
        "hinges": [
            {"direction": list(direction), "coefficient": str(value)}
            for direction, value in nonzero
        ],
        "claim_boundary": (
            "zero would certify this finite restricted-family combination only; nonzero refutes "
            "only this cut-system solution"
        ),
    }


def write_gzip_json(path: Path, value: object) -> None:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            compressed.write(raw)
    print(
        f"{path} uncompressed_bytes={len(raw)} compressed_bytes={path.stat().st_size} "
        f"sha256={sha256_path(path)}",
        flush=True,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    select_parser = sub.add_parser("select")
    select_parser.add_argument("--residual", type=Path, required=True)
    select_parser.add_argument("--hash-count", type=int, default=256)
    select_parser.add_argument("--magnitude-count", type=int, default=256)
    select_parser.add_argument("--output", type=Path, required=True)
    shard_parser = sub.add_parser("shard")
    shard_parser.add_argument("--selection", type=Path, required=True)
    shard_parser.add_argument("--classes", type=Path, required=True)
    shard_parser.add_argument("--shard-index", type=int, required=True)
    shard_parser.add_argument("--shard-count", type=int, required=True)
    shard_parser.add_argument("--output-directory", type=Path, required=True)
    assemble_parser = sub.add_parser("assemble")
    assemble_parser.add_argument("--selection", type=Path, required=True)
    assemble_parser.add_argument("--classes", type=Path, required=True)
    assemble_parser.add_argument("--shard-directory", type=Path, required=True)
    assemble_parser.add_argument("--shard-count", type=int, required=True)
    assemble_parser.add_argument("--output", type=Path, required=True)
    merge_parser = sub.add_parser("merge")
    merge_parser.add_argument("--selection", type=Path, action="append", required=True)
    merge_parser.add_argument("--cut-matrix", type=Path, action="append", required=True)
    merge_parser.add_argument("--classes", type=Path, required=True)
    merge_parser.add_argument("--output-selection", type=Path, required=True)
    merge_parser.add_argument("--output-matrix", type=Path, required=True)
    solve_parser = sub.add_parser("solve")
    solve_parser.add_argument("--selection", type=Path, required=True)
    solve_parser.add_argument("--classes", type=Path, required=True)
    solve_parser.add_argument("--cut-matrix", type=Path, required=True)
    solve_parser.add_argument("--orbit-directory", type=Path, required=True)
    solve_parser.add_argument("--prime", type=int, default=1_000_003)
    solve_parser.add_argument("--output", type=Path, required=True)
    residual_parser = sub.add_parser("residual")
    residual_parser.add_argument("--solution", type=Path, required=True)
    residual_parser.add_argument("--workers", type=int, default=8)
    residual_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "select":
        write_json(
            args.output,
            make_selection(args.residual, args.hash_count, args.magnitude_count),
        )
    elif args.command == "shard":
        build_shard(
            args.selection,
            args.classes,
            args.shard_index,
            args.shard_count,
            args.output_directory,
        )
    elif args.command == "assemble":
        assemble(
            args.selection,
            args.classes,
            args.shard_directory,
            args.shard_count,
            args.output,
        )
    elif args.command == "merge":
        merge_cut_matrices(
            args.selection,
            args.cut_matrix,
            args.classes,
            args.output_selection,
            args.output_matrix,
        )
    elif args.command == "solve":
        solve(
            args.selection,
            args.classes,
            args.cut_matrix,
            args.orbit_directory,
            args.prime,
            args.output,
        )
    else:
        write_gzip_json(
            args.output, complete_residual(args.solution, args.workers)
        )


if __name__ == "__main__":
    main()
