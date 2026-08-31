#!/usr/bin/env python3
"""Run G-0115 CEGIS with the bound parallel FFLAS-FFPACK projection solver."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
CEGIS_PATH = HERE / "semantic_repair_cegis.py"
NATIVE_SOURCE = HERE / "ffpack_modular_solve.cpp"
NATIVE_BINARY = HERE / "ffpack_modular_solve"
EXPECTED = {
    CEGIS_PATH: "2ca5bf0ced2e5166abb6413c96a6c91d7d71674190de802166d648401342c71b",
    NATIVE_SOURCE: "c8e6c0106930b2046a873de0bc1d4879914652ba4f2076163bcc9708ca96d2e0",
    NATIVE_BINARY: "8c5f71a8089f0ce9ad712de215043d3e076aae14187794072f79fc5271d907a9",
}
THREADS = 8


class NativeCegisError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise NativeCegisError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_sha(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast("B")).hexdigest()


def load_cegis():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"native CEGIS binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_ffpack_bound_cegis", CEGIS_PATH)
    require(spec is not None and spec.loader is not None, "cannot load CEGIS module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def native_projection_rref(matrix: np.ndarray, target: np.ndarray, prime: int, solver):
    begun_script_hash = sha256(SCRIPT)
    augmented64 = np.ascontiguousarray(np.column_stack((matrix, target)), dtype=np.int64)
    require(
        int(augmented64.min(initial=0)) >= -(1 << 31)
        and int(augmented64.max(initial=0)) < (1 << 31),
        "projection exceeds native int32 transport",
    )
    augmented = np.ascontiguousarray(augmented64, dtype=np.int32)
    with tempfile.TemporaryDirectory(prefix="g0115-ffpack-") as directory_raw:
        directory = Path(directory_raw)
        input_path = directory / "projection.i32"
        output_path = directory / "solution.u32"
        augmented.tofile(input_path)
        environment = os.environ.copy()
        environment.update(
            {
                "OMP_NUM_THREADS": str(THREADS),
                "OPENBLAS_NUM_THREADS": str(THREADS),
                "GOTO_NUM_THREADS": str(THREADS),
            }
        )
        completed = subprocess.run(
            [
                str(NATIVE_BINARY),
                str(input_path),
                str(output_path),
                str(matrix.shape[0]),
                str(matrix.shape[1]),
                str(prime),
                str(THREADS),
            ],
            check=True,
            capture_output=True,
            text=True,
            env=environment,
        )
        native = json.loads(completed.stdout)
        require(native.get("schema") == "g0115-ffpack-modular-solve-v1", "native schema drift")
        rank = int(native["rank"])
        serialized = np.fromfile(output_path, dtype=np.uint32)
        require(len(serialized) == matrix.shape[1] + rank, "native output census drift")
        solution = serialized[: matrix.shape[1]]
        pivots = list(map(int, serialized[matrix.shape[1] :]))
        require(len(set(pivots)) == rank and all(0 <= value < matrix.shape[1] for value in pivots), "native pivot profile drift")
        coefficients = [int(solution[column]) for column in pivots]
        if native["target_member"]:
            require(native["selected_replay_residual_rows"] == 0, "native selected replay failed")
        record = {
            "prime": prime,
            "selected_rows": matrix.shape[0],
            "rank": rank,
            "augmented_rank": rank if native["target_member"] else rank + 1,
            "target_member": bool(native["target_member"]),
            "seconds": float(native["factor_seconds"]) + float(native["solve_seconds"]),
            "backend": "FFLAS-FFPACK-2.5.0-parallel-PLUQ-plus-fgetrs",
            "threads": THREADS,
            "native_nonzero_solution_coefficients": int(native["support"]),
            "native_selected_replay_residual_rows": int(native["selected_replay_residual_rows"]),
            "transport_int32_c_sha256": raw_sha(augmented),
            "native_output_u32_sha256": raw_sha(serialized),
            "native_source_sha256": EXPECTED[NATIVE_SOURCE],
            "native_binary_sha256": EXPECTED[NATIVE_BINARY],
            "wrapper_sha256_at_call": begun_script_hash,
        }
    require(sha256(SCRIPT) == begun_script_hash, "native wrapper changed during projection solve")
    return record, pivots if record["target_member"] else [], coefficients if record["target_member"] else []


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--linear", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    args = parser.parse_args(argv)
    require(not args.report.exists() and not args.certificate.exists(), "outputs must be unused")
    script_hash = sha256(SCRIPT)
    cegis = load_cegis()
    cegis.projection_rref = native_projection_rref
    report = cegis.solve_cache(
        args.matrix.resolve(),
        args.linear.resolve(),
        args.metadata.resolve(),
        args.report.resolve(),
        args.certificate.resolve(),
    )
    require(sha256(SCRIPT) == script_hash, "native wrapper changed during solve")
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
