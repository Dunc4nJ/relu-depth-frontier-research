#!/usr/bin/env python3
"""G-0115 CEGIS with native rank/replay and determinant-free exact lifting."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
V2_PATH = HERE / "semantic_repair_ffpack_cegis_v2.py"
EXPECTED_V2 = "dd71951e929d85a8312491691c58fe0463301f54dd16d43931cbc13a078d58ce"
PIVOT_RECORDS: list[dict[str, object]] = []
EXACT_RECORDS: list[dict[str, object]] = []
EXACT_CHECKPOINT_PATH: Path | None = None


class NativeExactError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NativeExactError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w") as destination:
        json.dump(payload, destination, indent=2, sort_keys=True)
        destination.write("\n")


def load_v2():
    require(sha256(V2_PATH) == EXPECTED_V2, "v2 accelerator binding drift")
    spec = importlib.util.spec_from_file_location("g0115_bound_native_v2", V2_PATH)
    require(spec is not None and spec.loader is not None, "cannot load v2 accelerator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def native_pivot_coordinates(
    matrix: np.ndarray,
    basis_columns: Sequence[int],
    prime: int,
    v2,
) -> list[int]:
    begun_script_hash = sha256(SCRIPT)
    begun = time.perf_counter()
    basis64 = np.ascontiguousarray(matrix[:, list(basis_columns)].T, dtype=np.int64)
    require(
        int(basis64.min(initial=0)) >= -(1 << 31)
        and int(basis64.max(initial=0)) < (1 << 31),
        "pivot matrix exceeds int32 transport",
    )
    augmented = np.ascontiguousarray(
        np.column_stack((basis64, np.zeros(basis64.shape[0], dtype=np.int64))),
        dtype=np.int32,
    )
    with tempfile.TemporaryDirectory(prefix="g0115-pivot-") as directory_raw:
        directory = Path(directory_raw)
        input_path = directory / "basis-transpose.i32"
        output_path = directory / "pivot-rows.u32"
        augmented.tofile(input_path)
        environment = os.environ.copy()
        environment.update(
            {
                "OMP_NUM_THREADS": str(v2.THREADS),
                "OPENBLAS_NUM_THREADS": str(v2.THREADS),
                "GOTO_NUM_THREADS": str(v2.THREADS),
            }
        )
        completed = subprocess.run(
            [
                str(v2.SOLVER_BINARY),
                str(input_path),
                str(output_path),
                str(basis64.shape[0]),
                str(basis64.shape[1]),
                str(prime),
                str(v2.THREADS),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        native = json.loads(completed.stdout)
        serialized = np.fromfile(output_path, dtype=np.uint32)
        rank = int(native["rank"])
        require(native.get("schema") == "g0115-ffpack-modular-solve-v1", "pivot schema drift")
        require(bool(native["target_member"]), "zero pivot target is not a member")
        require(rank == len(basis_columns), "basis lost modular row rank")
        require(len(serialized) == basis64.shape[1] + rank, "pivot output census drift")
        pivots = list(map(int, serialized[basis64.shape[1] :]))
        require(
            len(pivots) == len(set(pivots))
            and all(0 <= coordinate < matrix.shape[0] for coordinate in pivots),
            "pivot coordinate contract failed",
        )
        PIVOT_RECORDS.append(
            {
                **native,
                "basis_columns": len(basis_columns),
                "basis_transpose_int32_sha256": v2.raw_sha(augmented),
                "pivot_coordinates_u32_sha256": v2.raw_sha(
                    np.asarray(pivots, dtype=np.uint32)
                ),
                "wall_seconds": time.perf_counter() - begun,
                "wrapper_sha256_at_call": begun_script_hash,
            }
        )
    require(sha256(SCRIPT) == begun_script_hash, "v3 wrapper changed during pivot selection")
    return pivots


def determinant_free_exact_minor_solution(
    matrix: np.ndarray,
    target: np.ndarray,
    basis_columns: Sequence[int],
    coordinate_rows: Sequence[int],
    solver,
) -> list[Fraction]:
    begun_script_hash = sha256(SCRIPT)
    begun = time.perf_counter()
    require(len(basis_columns) == len(coordinate_rows), "minor is not square")
    size = len(basis_columns)
    minor_array = np.ascontiguousarray(
        matrix[np.ix_(list(coordinate_rows), list(basis_columns))], dtype=np.int64
    )
    rhs_array = np.ascontiguousarray(
        target[list(coordinate_rows)].reshape(size, 1), dtype=np.int64
    )
    minor_integer = solver.fmpz_mat(size, size, memoryview(minor_array.ravel()))
    rhs_integer = solver.fmpz_mat(size, 1, memoryview(rhs_array.ravel()))
    solution = minor_integer.solve(rhs_integer)
    coefficients = [Fraction(str(solution[index, 0])) for index in range(size)]
    record = {
        "size": size,
        "minor_int64_sha256": solver.raw_sha256(minor_array),
        "rhs_int64_sha256": solver.raw_sha256(rhs_array),
        "basis_columns_int64_sha256": solver.raw_sha256(
            np.asarray(basis_columns, dtype=np.int64)
        ),
        "coordinate_rows_int64_sha256": solver.raw_sha256(
            np.asarray(coordinate_rows, dtype=np.int64)
        ),
        "nonzero_coefficients": sum(bool(value) for value in coefficients),
        "maximum_numerator_bits": max(abs(value.numerator).bit_length() for value in coefficients),
        "maximum_denominator_bits": max(value.denominator.bit_length() for value in coefficients),
        "seconds": time.perf_counter() - begun,
        "backend": "python-flint-fmpz_mat.solve-no-explicit-determinant",
        "wrapper_sha256_at_call": begun_script_hash,
    }
    EXACT_RECORDS.append(record)
    if EXACT_CHECKPOINT_PATH is not None:
        write_exclusive(
            EXACT_CHECKPOINT_PATH,
            {
                "schema": "g0115-exact-minor-checkpoint-v1",
                "record": record,
                "basis_columns": list(map(int, basis_columns)),
                "coordinate_rows": list(map(int, coordinate_rows)),
                "coefficients": [str(value) for value in coefficients],
            },
        )
    require(sha256(SCRIPT) == begun_script_hash, "v3 wrapper changed during exact solve")
    return coefficients


def main(argv: Sequence[str] | None = None) -> int:
    global EXACT_CHECKPOINT_PATH
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--linear", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--exact-checkpoint", type=Path, required=True)
    args = parser.parse_args(argv)
    require(
        not args.report.exists()
        and not args.certificate.exists()
        and not args.exact_checkpoint.exists(),
        "outputs must be unused",
    )
    EXACT_CHECKPOINT_PATH = args.exact_checkpoint.resolve()
    script_hash = sha256(SCRIPT)
    v2 = load_v2()
    cegis = v2.load_cegis()
    original_load_bound_modules = cegis.load_bound_modules

    def accelerated_bound_modules():
        bindings, kernel, solver = original_load_bound_modules()
        solver.pivot_coordinates = lambda matrix, columns, prime: native_pivot_coordinates(
            matrix, columns, prime, v2
        )
        solver.exact_minor_solution = lambda matrix, target, columns, rows: (
            determinant_free_exact_minor_solution(matrix, target, columns, rows, solver)
        )
        return bindings, kernel, solver

    cegis.load_bound_modules = accelerated_bound_modules
    cegis.projection_rref = v2.native_projection_rref
    cegis.modular_full_replay = v2.native_modular_full_replay
    with tempfile.TemporaryDirectory(prefix="g0115-v3-report-") as directory_raw:
        temporary_report = Path(directory_raw) / "inner-report.json"
        report = cegis.solve_cache(
            args.matrix.resolve(),
            args.linear.resolve(),
            args.metadata.resolve(),
            temporary_report,
            args.certificate.resolve(),
        )
    require(sha256(SCRIPT) == script_hash, "v3 wrapper changed during solve")
    report["native_acceleration"] = {
        "v3_wrapper_sha256": script_hash,
        "v2_wrapper_sha256": EXPECTED_V2,
        "projection_source_sha256": v2.EXPECTED[v2.SOLVER_SOURCE],
        "projection_binary_sha256": v2.EXPECTED[v2.SOLVER_BINARY],
        "replay_source_sha256": v2.EXPECTED[v2.REPLAY_SOURCE],
        "replay_binary_sha256": v2.EXPECTED[v2.REPLAY_BINARY],
        "threads": v2.THREADS,
        "complete_replay_calls": v2.REPLAY_RECORDS,
        "pivot_calls": PIVOT_RECORDS,
        "exact_calls": EXACT_RECORDS,
    }
    write_exclusive(args.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
