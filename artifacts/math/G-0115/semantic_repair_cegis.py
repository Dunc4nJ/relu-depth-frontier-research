#!/usr/bin/env python3
"""Full-family row CEGIS and exact rational lift for G-0115."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import multiprocessing as mp
import os
from pathlib import Path
import resource
import sys
import time
from typing import Iterable, Sequence

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
SOLVER_PATH = HERE / "semantic_repair_solve.py"
PROTOCOL_PATH = HERE / "SEMANTIC_REPAIR_CEGIS_PROTOCOL.md"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    SOLVER_PATH: "5023f3364db318521b73d464fba04dbfdecad5719170e3e0e1600ca57968b0a0",
    PROTOCOL_PATH: "8e8f1a238d02085fa7f8dbe8210b7999f54d22626c4b0fa60cb30d764efbc182",
}
PREFIXES = (256, 512, 1024, 2048, 4096, 8192, 16384, 22338)
INITIAL_HINGE_ROWS = 255
RESIDUAL_BATCH = 256
COORDINATES = 20_686

_WORKER_KERNEL = None
_WORKER_DP = None
_WORKER_ROW_BY_DIRECTION = None


class CegisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CegisError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def raw_sha(array: np.ndarray, block_rows: int = 64) -> str:
    digest = hashlib.sha256()
    if array.ndim == 1:
        digest.update(memoryview(np.ascontiguousarray(array)).cast("B"))
        return digest.hexdigest()
    for start in range(0, array.shape[0], block_rows):
        block = np.ascontiguousarray(array[start : start + block_rows])
        digest.update(memoryview(block).cast("B"))
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(canonical(value))
            destination.flush()
            os.fsync(destination.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def bind_inputs() -> dict[str, str]:
    observed = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()}
    require(observed == expected, f"CEGIS binding drift: {observed}")
    return observed


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_bound_modules():
    bindings = bind_inputs()
    kernel = load_module("g0115_cegis_kernel", KERNEL_PATH)
    solver = load_module("g0115_cegis_solver", SOLVER_PATH)
    kernel.bind_inputs()
    return bindings, kernel, solver


def worker_initialize() -> None:
    global _WORKER_KERNEL, _WORKER_DP, _WORKER_ROW_BY_DIRECTION
    require(sha256(KERNEL_PATH) == EXPECTED[KERNEL_PATH], "worker kernel drift")
    _WORKER_KERNEL = load_module(f"g0115_cegis_worker_kernel_{os.getpid()}", KERNEL_PATH)
    _WORKER_DP = _WORKER_KERNEL.load_dp()
    universe = _WORKER_KERNEL.direction_universe()
    _WORKER_ROW_BY_DIRECTION = {direction: row for row, direction in enumerate(universe)}


def worker_column(task: tuple[int, object]):
    require(
        _WORKER_KERNEL is not None and _WORKER_DP is not None and _WORKER_ROW_BY_DIRECTION is not None,
        "worker is not initialized",
    )
    index, raw_pair = task
    pair = _WORKER_KERNEL.parse_pair(raw_pair)
    linear, hinges = _WORKER_KERNEL.normal_form(_WORKER_DP, pair)
    rows = np.fromiter(
        (_WORKER_ROW_BY_DIRECTION[direction] for direction in hinges),
        dtype=np.uint16,
        count=len(hinges),
    )
    values = np.fromiter((hinges[direction] for direction in hinges), dtype=np.int32, count=len(hinges))
    order = np.argsort(rows)
    linear_array = np.asarray(linear, dtype=np.int32)
    alternating = int(_WORKER_KERNEL.lambda_value(linear))
    require(-(1 << 31) <= alternating < (1 << 31), "Lambda exceeds int32")
    return index, rows[order], values[order], linear_array, alternating


def generate_cache(
    matrix_path: Path,
    linear_path: Path,
    metadata_path: Path,
    workers: int,
) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings, kernel, _solver = load_bound_modules()
    require(
        all(not path.exists() and not path.is_symlink() for path in (matrix_path, linear_path, metadata_path)),
        "cache outputs must be unused",
    )
    _retained, repair, _missing = kernel.load_map_and_targets()
    universe = kernel.direction_universe()
    require(len(repair) == kernel.EXPECTED_REPAIR and len(universe) + 1 == COORDINATES, "cache census drift")
    matrix = np.lib.format.open_memmap(
        matrix_path,
        mode="w+",
        dtype=np.dtype("<i4"),
        shape=(len(repair), COORDINATES),
    )
    linear = np.lib.format.open_memmap(
        linear_path,
        mode="w+",
        dtype=np.dtype("<i4"),
        shape=(len(repair), kernel.N),
    )
    seen = np.zeros(len(repair), dtype=np.bool_)
    nonzeros = np.zeros(len(repair), dtype=np.int32)
    tasks = ((index, record["representative"]["pair"]) for index, record in enumerate(repair))
    context = mp.get_context("spawn")
    with context.Pool(processes=workers, initializer=worker_initialize, maxtasksperchild=512) as pool:
        for completed, (index, rows, values, linear_values, alternating) in enumerate(
            pool.imap_unordered(worker_column, tasks, chunksize=4), start=1
        ):
            require(0 <= index < len(repair) and not seen[index], f"duplicate cache column {index}")
            matrix[index, :] = 0
            matrix[index, rows.astype(np.intp)] = values
            matrix[index, -1] = alternating
            linear[index, :] = linear_values
            seen[index] = True
            nonzeros[index] = len(rows) + int(bool(alternating))
            if completed % 256 == 0 or completed == len(repair):
                print(f"G0115_CACHE {completed}/{len(repair)}", flush=True)
    require(bool(np.all(seen)), "cache generation incomplete")
    matrix.flush()
    linear.flush()
    del matrix
    del linear
    for path in (matrix_path, linear_path):
        with path.open("rb") as source:
            os.fsync(source.fileno())
    matrix_read = np.load(matrix_path, mmap_mode="r", allow_pickle=False)
    linear_read = np.load(linear_path, mmap_mode="r", allow_pickle=False)
    require(matrix_read.shape == (len(repair), COORDINATES), "matrix cache shape drift")
    require(linear_read.shape == (len(repair), kernel.N), "linear cache shape drift")
    for index in (0, 127, len(repair) - 1):
        dp = kernel.load_dp()
        semantic = kernel.normal_form(dp, kernel.parse_pair(repair[index]["representative"]["pair"]))
        observed_rows = set(map(int, np.flatnonzero(matrix_read[index, :-1])))
        expected_rows = {universe.index(direction) for direction in semantic[1]}
        require(observed_rows == expected_rows, f"cache row support mismatch {index}")
        require(
            tuple(map(int, linear_read[index])) == semantic[0]
            and int(matrix_read[index, -1]) == kernel.lambda_value(semantic[0]),
            f"cache semantic replay mismatch {index}",
        )
    matrix_data_hash = raw_sha(matrix_read)
    linear_data_hash = raw_sha(linear_read)
    del matrix_read
    del linear_read
    metadata = {
        "schema": "max11-g0115-semantic-repair-matrix-cache-v1",
        "result": "PASS",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "matrix": {
            "path": str(matrix_path.relative_to(ROOT)),
            "file_sha256": sha256(matrix_path),
            "data_sha256": matrix_data_hash,
            "shape": [len(repair), COORDINATES],
            "dtype": "<i4",
            "orientation": "repair_columns_x_complete_hinge_plus_Lambda_coordinates",
        },
        "linear": {
            "path": str(linear_path.relative_to(ROOT)),
            "file_sha256": sha256(linear_path),
            "data_sha256": linear_data_hash,
            "shape": [len(repair), kernel.N],
            "dtype": "<i4",
        },
        "column_order_sha256": canonical_sha(
            [record["signed_certificate_sha256"] for record in repair]
        ),
        "direction_order_sha256": canonical_sha([list(direction) for direction in universe]),
        "nonzeros": {
            "minimum": int(nonzeros.min()),
            "median": int(np.median(nonzeros)),
            "maximum": int(nonzeros.max()),
            "total": int(nonzeros.sum()),
        },
        "workers": workers,
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claim_boundary": "Exact semantic cache only; no target membership was computed.",
    }
    require(sha256(SCRIPT) == script_hash, "CEGIS script changed during cache generation")
    write_exclusive(metadata_path, metadata)
    return metadata


def validate_cache(matrix_path: Path, linear_path: Path, metadata_path: Path, kernel, repair):
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    require(metadata.get("schema") == "max11-g0115-semantic-repair-matrix-cache-v1", "bad cache schema")
    require(metadata.get("result") == "PASS", "cache gate is not green")
    require(metadata["bindings"]["script_sha256_at_start"] == sha256(SCRIPT), "cache producer drift")
    require(metadata["matrix"]["file_sha256"] == sha256(matrix_path), "matrix file drift")
    require(metadata["linear"]["file_sha256"] == sha256(linear_path), "linear file drift")
    require(
        metadata["column_order_sha256"]
        == canonical_sha([record["signed_certificate_sha256"] for record in repair]),
        "cache column order drift",
    )
    matrix = np.load(matrix_path, mmap_mode="r", allow_pickle=False)
    linear = np.load(linear_path, mmap_mode="r", allow_pickle=False)
    require(matrix.shape == (kernel.EXPECTED_REPAIR, COORDINATES) and matrix.dtype == np.dtype("<i4"), "matrix cache contract drift")
    require(linear.shape == (kernel.EXPECTED_REPAIR, kernel.N) and linear.dtype == np.dtype("<i4"), "linear cache contract drift")
    return metadata, matrix, linear


def evenly_spaced(values: Sequence[int] | np.ndarray, limit: int) -> list[int]:
    checked = list(map(int, values))
    if len(checked) <= limit:
        return checked
    require(limit >= 2, "even sampling limit is too small")
    return [checked[index * (len(checked) - 1) // (limit - 1)] for index in range(limit)]


def target_vector(kernel, target) -> tuple[np.ndarray, int, dict[tuple[int, ...], Fraction], Fraction]:
    universe = kernel.direction_universe()
    row_by_direction = {direction: row for row, direction in enumerate(universe)}
    hinges = target["target_hinges"]
    alternating = target["target_lambda"]
    denominator = 1
    for coefficient in [*hinges.values(), alternating]:
        denominator = math.lcm(denominator, coefficient.denominator)
    vector = np.zeros(COORDINATES, dtype=np.int64)
    for direction, coefficient in hinges.items():
        value = int(coefficient * denominator)
        require(-(1 << 63) <= value < (1 << 63), "target hinge exceeds int64")
        vector[row_by_direction[direction]] = value
    vector[-1] = int(alternating * denominator)
    return vector, denominator, hinges, alternating


def projection_rref(matrix: np.ndarray, target: np.ndarray, prime: int, solver):
    begun = time.perf_counter()
    augmented = np.ascontiguousarray(np.column_stack((matrix, target)), dtype=np.int64)
    modular = nmod_mat(
        augmented.shape[0], augmented.shape[1], memoryview(augmented.ravel()), prime
    )
    reduced, augmented_rank = modular.rref()
    pivots = solver.pivot_columns(reduced, augmented_rank, augmented.shape[1])
    candidate_rank = sum(pivot < matrix.shape[1] for pivot in pivots)
    member = matrix.shape[1] not in pivots
    require(augmented_rank == candidate_rank + (not member), "projection rank drift")
    support = []
    coefficients = []
    if member:
        for row, pivot in enumerate(pivots):
            require(pivot < matrix.shape[1], "member RREF contains target pivot")
            support.append(pivot)
            coefficients.append(int(reduced[row, matrix.shape[1]]))
    return (
        {
            "prime": prime,
            "selected_rows": matrix.shape[0],
            "rank": candidate_rank,
            "augmented_rank": augmented_rank,
            "target_member": member,
            "seconds": time.perf_counter() - begun,
        },
        support,
        coefficients,
    )


def modular_full_replay(
    cache: np.ndarray,
    support: Sequence[int],
    coefficients: Sequence[int],
    target: np.ndarray,
    prime: int,
) -> np.ndarray:
    require(len(support) == len(coefficients), "modular support mismatch")
    observed = np.zeros(cache.shape[1], dtype=np.int64)
    block_size = 8
    for start in range(0, len(support), block_size):
        block_support = list(support[start : start + block_size])
        block_coefficients = np.asarray(coefficients[start : start + block_size], dtype=np.int64)
        block = np.asarray(cache[block_support, :], dtype=np.int64)
        contribution = ((block_coefficients[:, None] * block) % prime).sum(axis=0) % prime
        observed = (observed + contribution) % prime
    expected = np.remainder(target, prime)
    return np.flatnonzero(observed != expected)


def exact_full_replay(
    cache: np.ndarray,
    support: Sequence[int],
    coefficients: Sequence[Fraction],
    target: np.ndarray,
) -> tuple[list[int], int]:
    common_denominator = 1
    for coefficient in coefficients:
        common_denominator = math.lcm(common_denominator, coefficient.denominator)
    integer_coefficients = [
        coefficient.numerator * (common_denominator // coefficient.denominator)
        for coefficient in coefficients
    ]
    observed: dict[int, int] = {}
    for column, coefficient in zip(support, integer_coefficients, strict=True):
        if not coefficient:
            continue
        row = cache[column]
        for coordinate in map(int, np.flatnonzero(row)):
            observed[coordinate] = observed.get(coordinate, 0) + coefficient * int(row[coordinate])
    residual = [
        coordinate
        for coordinate in range(cache.shape[1])
        if observed.get(coordinate, 0) != int(target[coordinate]) * common_denominator
    ]
    return residual, common_denominator


def fraction_dot_rows(
    rows: np.ndarray, support: Sequence[int], coefficients: Sequence[Fraction]
) -> list[Fraction]:
    output = [Fraction() for _ in range(rows.shape[1])]
    for column, coefficient in zip(support, coefficients, strict=True):
        for coordinate, value in enumerate(rows[column]):
            output[coordinate] += coefficient * int(value)
    return output


def solve_cache(
    matrix_path: Path,
    linear_path: Path,
    metadata_path: Path,
    report_path: Path,
    certificate_path: Path,
) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings, kernel, solver = load_bound_modules()
    dp = kernel.load_dp()
    retained, repair, missing = kernel.load_map_and_targets()
    cache_metadata, cache, linear_cache = validate_cache(
        matrix_path, linear_path, metadata_path, kernel, repair
    )
    controls = {
        "known_MAX8": kernel.certificate_replay(dp, kernel.CERT8, 8, 3),
        "known_MAX9": kernel.certificate_replay(dp, kernel.CERT9, 9, 4),
        "planted_linear_system": solver.planted_controls(),
    }
    target = solver.target_system(kernel, dp, retained, missing)
    integer_target, target_denominator, target_hinges, target_lambda = target_vector(kernel, target)
    nonzero_hinge_rows = np.flatnonzero(integer_target[:-1])
    selected = set(evenly_spaced(nonzero_hinge_rows, INITIAL_HINGE_ROWS))
    selected.add(COORDINATES - 1)
    initial_rows = sorted(selected)
    prefix_records = []
    chosen = None

    for prefix in PREFIXES:
        prefix_record: dict[str, object] = {"prefix": prefix, "iterations": []}
        for iteration in range(1, COORDINATES + 1):
            selected_rows = sorted(selected)
            projection = np.ascontiguousarray(
                cache[:prefix, selected_rows].T, dtype=np.int64
            )
            projection_target = np.ascontiguousarray(integer_target[selected_rows], dtype=np.int64)
            modular_records = []
            guide = None
            guide_support = None
            guide_coefficients = None
            for prime in kernel.PRIMES:
                record, support, coefficients = projection_rref(
                    projection, projection_target, prime, solver
                )
                modular_records.append(record)
                if record["target_member"] and guide is None:
                    guide = prime
                    guide_support = support
                    guide_coefficients = coefficients
                if prime == kernel.PRIMES[0] and record["target_member"]:
                    break
            iteration_record: dict[str, object] = {
                "iteration": iteration,
                "selected_rows": len(selected_rows),
                "selected_rows_int64_sha256": solver.raw_sha256(
                    np.asarray(selected_rows, dtype=np.int64)
                ),
                "projection": modular_records,
            }
            prefix_record["iterations"].append(iteration_record)
            if guide is None:
                prefix_record["outcome"] = "MODULAR_PROJECTED_NONMEMBER"
                print(
                    f"G0115_CEGIS prefix={prefix} rows={len(selected_rows)} nonmember_all_primes",
                    flush=True,
                )
                break
            require(guide_support is not None and guide_coefficients is not None, "missing guide solution")
            residual = modular_full_replay(
                cache,
                guide_support,
                guide_coefficients,
                integer_target,
                guide,
            )
            iteration_record["guide_prime"] = guide
            iteration_record["guide_support"] = len(guide_support)
            iteration_record["complete_modular_residual_nonzeros"] = len(residual)
            if len(residual):
                new_rows = [row for row in map(int, residual) if row not in selected]
                require(new_rows, "modular residual contains no new row")
                added = evenly_spaced(new_rows, RESIDUAL_BATCH)
                selected.update(added)
                iteration_record["added_rows"] = len(added)
                iteration_record["added_rows_int64_sha256"] = solver.raw_sha256(
                    np.asarray(added, dtype=np.int64)
                )
                print(
                    f"G0115_CEGIS prefix={prefix} rows={len(selected_rows)} "
                    f"rank={len(guide_support)} residual={len(residual)} add={len(added)}",
                    flush=True,
                )
                continue

            pivot_positions = solver.pivot_coordinates(projection, guide_support, guide)
            exact_coefficients = solver.exact_minor_solution(
                projection,
                projection_target,
                guide_support,
                pivot_positions,
            )
            exact_residual, solution_denominator = exact_full_replay(
                cache, guide_support, exact_coefficients, integer_target
            )
            iteration_record["exact_attempt"] = {
                "basis_columns": len(guide_support),
                "pivot_rows": len(pivot_positions),
                "solution_common_denominator_digits": len(str(solution_denominator)),
                "complete_exact_residual_nonzeros": len(exact_residual),
            }
            if exact_residual:
                new_rows = [row for row in exact_residual if row not in selected]
                require(new_rows, "exact residual contains no new row")
                added = evenly_spaced(new_rows, RESIDUAL_BATCH)
                selected.update(added)
                iteration_record["exact_attempt"]["added_rows"] = len(added)
                print(
                    f"G0115_CEGIS_EXACT_MISS prefix={prefix} residual={len(exact_residual)}",
                    flush=True,
                )
                continue

            nonzero = [
                (column, coefficient)
                for column, coefficient in zip(guide_support, exact_coefficients, strict=True)
                if coefficient
            ]
            require(nonzero, "exact CEGIS solution is zero")
            mutation_column = nonzero[0][0]
            mutation_failure_rows = int(np.count_nonzero(cache[mutation_column]))
            require(mutation_failure_rows > 0, "coefficient mutation escaped complete replay")
            positive_prime_controls = []
            for prime in kernel.PRIMES:
                record, support, coefficients = projection_rref(
                    projection, projection_target, prime, solver
                )
                if record["target_member"]:
                    replay_residual = modular_full_replay(
                        cache, support, coefficients, integer_target, prime
                    )
                    record["complete_replay_residual_nonzeros"] = len(replay_residual)
                positive_prime_controls.append(record)
            chosen = {
                "prefix": prefix,
                "selected_rows": selected_rows,
                "support": guide_support,
                "coefficients": exact_coefficients,
                "nonzero": nonzero,
                "guide_prime": guide,
                "positive_prime_controls": positive_prime_controls,
                "mutation_failure_rows": mutation_failure_rows,
            }
            prefix_record["outcome"] = "EXACT_MEMBER"
            break
        prefix_records.append(prefix_record)
        if chosen is not None:
            break

    result = "EXACT_MEMBER" if chosen is not None else "MODULAR_FULL_FAMILY_GATE_ONLY"
    exact_summary = None
    if chosen is not None:
        repair_terms = []
        for column, integer_coefficient in chosen["nonzero"]:
            coefficient = integer_coefficient / target_denominator
            record = repair[column]
            repair_terms.append(
                {
                    "coefficient": str(coefficient),
                    "integer_system_coefficient": str(integer_coefficient),
                    "pair": record["representative"]["pair"],
                    "repair_order_index": column,
                    "representative_sequence": int(record["sequence"]),
                    "signed_certificate_sha256": record["signed_certificate_sha256"],
                    "topology_distance": record["topology_distance"],
                }
            )
        missing_terms = [
            {
                "public_term_index": public_index,
                "coefficient": str(coefficient),
                "pair": kernel.serialize_pair(pair),
            }
            for public_index, (coefficient, pair) in zip(
                target["missing_indices"], missing, strict=True
            )
        ]
        repair_linear_integer = fraction_dot_rows(
            linear_cache, chosen["support"], chosen["coefficients"]
        )
        repair_linear = [value / target_denominator for value in repair_linear_integer]
        retained_lift_linear = [Fraction() for _ in range(kernel.N)]
        retained_lift_hinges: dict[tuple[int, ...], Fraction] = {}
        for term in target["retained_lift_records"]:
            kernel.add_scaled(
                retained_lift_linear,
                retained_lift_hinges,
                kernel.normal_form(dp, kernel.parse_pair(term["pair"])),
                Fraction(term["coefficient"]),
            )
        require(
            retained_lift_hinges == target["retained_public_hinges"],
            "retained lift hinge replay drift",
        )
        combined_linear = [
            retained_lift_linear[index] + repair_linear[index]
            for index in range(kernel.N)
        ]
        require(kernel.lambda_value(combined_linear) == 1, "combined Lambda drift")
        certificate = {
            "schema": "max11-g0115-max9-coefficient-frozen-residual-certificate-v1",
            "n": kernel.N,
            "source_degree": 4,
            "target_denominator": target_denominator,
            "retained_fixed_terms": target["retained_lift_records"],
            "repair_terms": repair_terms,
            "missing_public_terms": missing_terms,
            "semantics": {
                "complete_hinge_direction_count": kernel.EXPECTED_DIRECTIONS,
                "repair_equals_missing_hinges": True,
                "repair_equals_missing_lambda": True,
                "retained_plus_repair_hinge_count": 0,
                "retained_plus_repair_lambda": "1",
                "retained_plus_repair_linear": [str(value) for value in combined_linear],
            },
            "claim_boundary": (
                "Exact coefficient-frozen MAX9 residual repair inside the G-0115 lift family; "
                "the lower-arity linear correction is not included in this artifact."
            ),
        }
        write_exclusive(certificate_path, certificate)
        exact_summary = {
            "positive_prefix": chosen["prefix"],
            "selected_rows": len(chosen["selected_rows"]),
            "basis_size": len(chosen["support"]),
            "nonzero_repair_coefficients": len(chosen["nonzero"]),
            "guide_prime": chosen["guide_prime"],
            "complete_hinge_rows_replayed": kernel.EXPECTED_DIRECTIONS,
            "complete_hinge_residual_nonzeros": 0,
            "lambda_replayed": True,
            "coefficient_mutation_failure_rows": chosen["mutation_failure_rows"],
            "positive_prime_controls": chosen["positive_prime_controls"],
            "retained_plus_repair_linear": [str(value) for value in combined_linear],
            "certificate_path": str(certificate_path.relative_to(ROOT)),
            "certificate_sha256": sha256(certificate_path),
            "certificate_canonical_sha256": canonical_sha(certificate),
        }

    report = {
        "schema": "max11-g0115-max9-semantic-repair-cegis-v1",
        "result": result,
        "bindings": {
            **bindings,
            "cache_metadata": sha256(metadata_path),
            "matrix_cache": cache_metadata["matrix"]["file_sha256"],
            "linear_cache": cache_metadata["linear"]["file_sha256"],
            "script_sha256_at_start": script_hash,
        },
        "target": {
            "missing_public_terms": len(missing),
            "hinge_nonzeros": len(target_hinges),
            "lambda": str(target_lambda),
            "integer_clear_denominator": target_denominator,
            "target_int64_c_sha256": solver.raw_sha256(integer_target),
            "negative_retained_public_residual_replayed": True,
        },
        "search": {
            "frozen_prefixes": list(PREFIXES),
            "initial_selected_rows": len(initial_rows),
            "initial_selected_rows_int64_sha256": solver.raw_sha256(
                np.asarray(initial_rows, dtype=np.int64)
            ),
            "residual_batch": RESIDUAL_BATCH,
            "prefixes": prefix_records,
        },
        "exact": exact_summary,
        "controls": controls,
        "claim_boundary": (
            "An exact positive is a MAX9 calibration, not MAX11 or an induction theorem. "
            "A modular full-family gate is not a characteristic-zero obstruction."
        ),
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    require(sha256(SCRIPT) == script_hash, "CEGIS script changed during solve")
    write_exclusive(report_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--generate-cache", action="store_true")
    mode.add_argument("--solve", action="store_true")
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--linear", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--certificate", type=Path)
    args = parser.parse_args(argv)
    if args.generate_cache:
        require(args.report is None and args.certificate is None, "cache mode does not take solve outputs")
        report = generate_cache(
            args.matrix.resolve(),
            args.linear.resolve(),
            args.metadata.resolve(),
            args.workers,
        )
        print(json.dumps(report, sort_keys=True))
        return 0
    require(args.report is not None and args.certificate is not None, "solve outputs are required")
    require(not args.report.exists() and not args.certificate.exists(), "solve outputs must be unused")
    report = solve_cache(
        args.matrix.resolve(),
        args.linear.resolve(),
        args.metadata.resolve(),
        args.report.resolve(),
        args.certificate.resolve(),
    )
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
