#!/usr/bin/env python3
"""Materialize the preregistered all-22,666 full-semantic G-0115 matrix."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import resource
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
PREREGISTRATION = HERE / "UNRESTRICTED_FULL_SEMANTIC_PREREGISTRATION.md"
REPAIR_MATRIX = HERE / "semantic_repair_matrix_v1.npy"
REPAIR_LINEAR = HERE / "semantic_repair_linear_v1.npy"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    PREREGISTRATION: "61e39e655912e0f967ae76c90676012c06d506305d64267533ebf73ee50ec017",
    REPAIR_MATRIX: "9342b7cd7b8e048b5ae38a3626766827e196c076be5fddaa94e0cb008ade49e5",
    REPAIR_LINEAR: "4d98c6e6c2aa1a3317c13c541c50d25a025b6211ece448803462371a45a56100",
}
HINGES = 20_685
LINEAR = 9
COLUMNS = 22_666


class MatrixBuildError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MatrixBuildError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_sha(array: np.ndarray, block_rows: int = 64) -> str:
    digest = hashlib.sha256()
    for start in range(0, array.shape[0], block_rows):
        block = np.ascontiguousarray(array[start : start + block_rows])
        digest.update(memoryview(block).cast("B"))
    return digest.hexdigest()


def canonical_sha(value: object) -> str:
    raw = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(raw).hexdigest()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w") as destination:
        json.dump(payload, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def load_kernel():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"unrestricted matrix binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_unrestricted_matrix_kernel", KERNEL_PATH)
    require(spec is not None and spec.loader is not None, "cannot load semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.bind_inputs()
    return module


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--metadata", type=Path, required=True)
    args = parser.parse_args()
    require(not args.matrix.exists() and not args.metadata.exists(), "outputs must be unused")
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    kernel = load_kernel()
    dp = kernel.load_dp()
    retained, repair, _missing = kernel.load_map_and_targets()
    require(
        len(retained) == kernel.EXPECTED_RETAINED
        and len(repair) == kernel.EXPECTED_REPAIR
        and len(retained) + len(repair) == COLUMNS,
        "all-class census drift",
    )
    universe = kernel.direction_universe()
    require(len(universe) == HINGES, "hinge universe drift")
    row_by_direction = {direction: row for row, direction in enumerate(universe)}
    output = np.lib.format.open_memmap(
        args.matrix.resolve(), mode="w+", dtype=np.dtype("<i4"), shape=(COLUMNS, HINGES + LINEAR)
    )
    output[:] = 0

    retained_nonzeros = []
    for index, record in enumerate(retained):
        pair = kernel.parse_pair(record["representative"]["pair"])
        linear, hinges = kernel.normal_form(dp, pair)
        for direction, value in hinges.items():
            output[index, row_by_direction[direction]] = int(value)
        output[index, HINGES:] = np.asarray(linear, dtype=np.int32)
        retained_nonzeros.append(len(hinges) + sum(bool(value) for value in linear))
        if (index + 1) % 64 == 0 or index + 1 == len(retained):
            print(f"G0115_UNRESTRICTED_RETAINED {index + 1}/{len(retained)}", flush=True)

    repair_matrix = np.load(REPAIR_MATRIX, mmap_mode="r", allow_pickle=False)
    repair_linear = np.load(REPAIR_LINEAR, mmap_mode="r", allow_pickle=False)
    require(
        repair_matrix.shape == (len(repair), HINGES + 1)
        and repair_linear.shape == (len(repair), LINEAR),
        "repair cache shape drift",
    )
    block_rows = 64
    offset = len(retained)
    for start in range(0, len(repair), block_rows):
        stop = min(start + block_rows, len(repair))
        output[offset + start : offset + stop, :HINGES] = repair_matrix[start:stop, :HINGES]
        output[offset + start : offset + stop, HINGES:] = repair_linear[start:stop, :]
        if stop % 1024 == 0 or stop == len(repair):
            print(f"G0115_UNRESTRICTED_REPAIR {stop}/{len(repair)}", flush=True)
    output.flush()
    del output
    with args.matrix.resolve().open("rb") as source:
        os.fsync(source.fileno())

    matrix = np.load(args.matrix.resolve(), mmap_mode="r", allow_pickle=False)
    require(matrix.shape == (COLUMNS, HINGES + LINEAR) and matrix.dtype == np.dtype("<i4"), "full matrix contract drift")
    for index in (0, 127, len(retained) - 1):
        semantic = kernel.normal_form(dp, kernel.parse_pair(retained[index]["representative"]["pair"]))
        observed_rows = set(map(int, np.flatnonzero(matrix[index, :HINGES])))
        expected_rows = {row_by_direction[direction] for direction in semantic[1]}
        require(
            observed_rows == expected_rows
            and tuple(map(int, matrix[index, HINGES:])) == semantic[0],
            f"retained full-semantic replay mismatch {index}",
        )
    for repair_index in (0, 127, len(repair) - 1):
        full_index = offset + repair_index
        require(
            np.array_equal(matrix[full_index, :HINGES], repair_matrix[repair_index, :HINGES])
            and np.array_equal(matrix[full_index, HINGES:], repair_linear[repair_index]),
            f"repair cache copy mismatch {repair_index}",
        )
    target = np.zeros(HINGES + LINEAR, dtype=np.int64)
    target[-1] = 1
    order = [
        {"group": "retained", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in retained
    ] + [
        {"group": "repair", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in repair
    ]
    matrix_data_sha = raw_sha(matrix)
    metadata = {
        "schema": "g0115-unrestricted-full-semantic-matrix-v1",
        "result": "PASS",
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {"script_sha256_at_start": script_hash},
        "matrix": {
            "path": str(args.matrix.resolve().relative_to(ROOT)),
            "file_sha256": sha256(args.matrix.resolve()),
            "data_sha256": matrix_data_sha,
            "shape": [COLUMNS, HINGES + LINEAR],
            "dtype": "<i4",
            "orientation": "candidate_classes_x_complete_hinges_plus_nine_linear_coordinates",
        },
        "column_order": {
            "retained_first": len(retained),
            "repair_second": len(repair),
            "canonical_sha256": canonical_sha(order),
        },
        "target": {
            "hinges": HINGES,
            "linear": [0] * 8 + [1],
            "int64_sha256": hashlib.sha256(target.tobytes()).hexdigest(),
        },
        "controls": {
            "all_retained_generated_from_serialized_pairs": True,
            "all_repair_rows_copied_from_bound_exact_caches": True,
            "retained_sample_replayed": [0, 127, len(retained) - 1],
            "repair_sample_replayed": [0, 127, len(repair) - 1],
            "retained_nonzeros": {
                "minimum": min(retained_nonzeros),
                "maximum": max(retained_nonzeros),
                "total": sum(retained_nonzeros),
            },
        },
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "claim_boundary": "Certified exact input matrix only; no unrestricted membership outcome was computed.",
    }
    require(sha256(SCRIPT) == script_hash, "matrix builder changed during execution")
    write_exclusive(args.metadata.resolve(), metadata)
    print(json.dumps(metadata, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
