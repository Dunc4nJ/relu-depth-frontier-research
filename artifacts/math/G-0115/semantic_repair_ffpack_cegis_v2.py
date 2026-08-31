#!/usr/bin/env python3
"""Run G-0115 CEGIS with native projection solving and full-coordinate replay."""

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
SOLVER_SOURCE = HERE / "ffpack_modular_solve.cpp"
SOLVER_BINARY = HERE / "ffpack_modular_solve"
REPLAY_SOURCE = HERE / "modular_full_replay.cpp"
REPLAY_BINARY = HERE / "modular_full_replay"
EXPECTED = {
    CEGIS_PATH: "2ca5bf0ced2e5166abb6413c96a6c91d7d71674190de802166d648401342c71b",
    SOLVER_SOURCE: "c8e6c0106930b2046a873de0bc1d4879914652ba4f2076163bcc9708ca96d2e0",
    SOLVER_BINARY: "8c5f71a8089f0ce9ad712de215043d3e076aae14187794072f79fc5271d907a9",
    REPLAY_SOURCE: "7f96e22cc2dae5c8c4a1a6665c0cc1ef35e78069210087bc81b22359ca658b16",
    REPLAY_BINARY: "0725a2cb305f89fc92f98b1ac45e59f6feafa684b26a3bd0e3765168c8ee9f31",
}
THREADS = 8
REPLAY_RECORDS: list[dict[str, object]] = []


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


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w") as destination:
        json.dump(payload, destination, indent=2, sort_keys=True)
        destination.write("\n")


def load_cegis():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"native CEGIS binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_ffpack_replay_bound_cegis", CEGIS_PATH)
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
                str(SOLVER_BINARY),
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
        require(
            len(set(pivots)) == rank and all(0 <= value < matrix.shape[1] for value in pivots),
            "native pivot profile drift",
        )
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
            "native_source_sha256": EXPECTED[SOLVER_SOURCE],
            "native_binary_sha256": EXPECTED[SOLVER_BINARY],
            "wrapper_sha256_at_call": begun_script_hash,
        }
    require(sha256(SCRIPT) == begun_script_hash, "native wrapper changed during projection solve")
    return record, pivots if record["target_member"] else [], coefficients if record["target_member"] else []


def native_modular_full_replay(
    cache: np.ndarray,
    support: Sequence[int],
    coefficients: Sequence[int],
    target: np.ndarray,
    prime: int,
):
    begun_script_hash = sha256(SCRIPT)
    require(len(support) == len(coefficients), "support/coefficient census drift")
    require(isinstance(cache, np.memmap), "native replay requires the certified memmap cache")
    filtered = [
        (int(column), int(coefficient) % prime)
        for column, coefficient in zip(support, coefficients, strict=True)
        if int(coefficient) % prime
    ]
    require(all(0 <= column < cache.shape[0] for column, _ in filtered), "support outside cache")
    pairs = np.asarray(filtered, dtype=np.uint32).reshape((-1, 2))
    target_mod = np.ascontiguousarray(np.remainder(target, prime), dtype=np.uint32)
    with tempfile.TemporaryDirectory(prefix="g0115-replay-") as directory_raw:
        directory = Path(directory_raw)
        support_path = directory / "support.u32"
        target_path = directory / "target.u32"
        output_path = directory / "residual.u32"
        pairs.tofile(support_path)
        target_mod.tofile(target_path)
        completed = subprocess.run(
            [
                str(REPLAY_BINARY),
                str(Path(cache.filename).resolve()),
                str(cache.offset),
                str(cache.shape[0]),
                str(cache.shape[1]),
                str(support_path),
                str(target_path),
                str(output_path),
                str(prime),
                str(THREADS),
                str(len(filtered)),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        native = json.loads(completed.stdout)
        require(native.get("schema") == "g0115-modular-full-replay-v1", "replay schema drift")
        residual = np.fromfile(output_path, dtype=np.uint32)
        require(
            len(residual) == int(native["residual_coordinates"]),
            "native residual census drift",
        )
        require(
            len(residual) == len(set(map(int, residual)))
            and all(0 <= int(value) < cache.shape[1] for value in residual),
            "native residual coordinate contract failed",
        )
        residual_set = set(map(int, residual))
        sample = set(np.linspace(0, cache.shape[1] - 1, num=41, dtype=np.int64).tolist())
        if len(residual):
            sample.update([int(residual[0]), int(residual[len(residual) // 2]), int(residual[-1])])
        for coordinate in sorted(sample):
            observed = sum(
                coefficient * int(cache[column, coordinate])
                for column, coefficient in filtered
            ) % prime
            require(
                ((observed != int(target_mod[coordinate])) == (coordinate in residual_set)),
                f"sampled native replay mismatch at coordinate {coordinate}",
            )
        REPLAY_RECORDS.append(
            {
                **native,
                "support_u32_sha256": raw_sha(pairs),
                "target_u32_sha256": raw_sha(target_mod),
                "residual_u32_sha256": raw_sha(residual),
                "sampled_python_replay_coordinates": len(sample),
                "native_source_sha256": EXPECTED[REPLAY_SOURCE],
                "native_binary_sha256": EXPECTED[REPLAY_BINARY],
                "wrapper_sha256_at_call": begun_script_hash,
            }
        )
    require(sha256(SCRIPT) == begun_script_hash, "native wrapper changed during full replay")
    return residual.astype(np.int64, copy=False)


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
    cegis.modular_full_replay = native_modular_full_replay
    with tempfile.TemporaryDirectory(prefix="g0115-native-report-") as directory_raw:
        temporary_report = Path(directory_raw) / "inner-report.json"
        report = cegis.solve_cache(
            args.matrix.resolve(),
            args.linear.resolve(),
            args.metadata.resolve(),
            temporary_report,
            args.certificate.resolve(),
        )
    require(sha256(SCRIPT) == script_hash, "native wrapper changed during solve")
    report["native_acceleration"] = {
        "wrapper_sha256": script_hash,
        "projection_source_sha256": EXPECTED[SOLVER_SOURCE],
        "projection_binary_sha256": EXPECTED[SOLVER_BINARY],
        "replay_source_sha256": EXPECTED[REPLAY_SOURCE],
        "replay_binary_sha256": EXPECTED[REPLAY_BINARY],
        "threads": THREADS,
        "complete_replay_calls": REPLAY_RECORDS,
    }
    write_exclusive(args.report, report)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
