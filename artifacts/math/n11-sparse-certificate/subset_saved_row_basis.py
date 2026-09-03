#!/usr/bin/env python3
"""Restrict a saved-system CSC to the named modular row basis, with custody."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import time
from pathlib import Path

import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def hinge_orders(system: Path):
    insertion = []
    seen = set()
    n = None
    with gzip.open(system, "rt", encoding="utf-8") as stream:
        for line in stream:
            column = json.loads(line)
            n = len(column["lin"]) if n is None else n
            for key in column["h"]:
                if key not in seen:
                    seen.add(key)
                    insertion.append(key)
    return n, insertion, sorted(insertion)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--basis", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    started = time.monotonic()
    if args.output_dir.exists():
        raise FileExistsError(f"refusing to overwrite {args.output_dir}")
    args.output_dir.mkdir(parents=True)
    meta_path = args.matrix_dir / "matrix.json"
    meta = json.loads(meta_path.read_text())
    basis = json.loads(args.basis.read_text())
    if meta["system_sha256"] != basis["system_sha256"]:
        raise ValueError("basis/system hash mismatch")
    system = Path(meta["system"])
    n, insertion, ordered = hinge_orders(system)
    if len(ordered) != int(meta["hinge_rows_denominator"]) or n != int(meta["n"]):
        raise ValueError("reconstructed row ordering mismatch")
    sorted_position = {key: position for position, key in enumerate(ordered)}
    selected_old = list(map(int, basis["row_pivots"]))
    if len(selected_old) != int(basis["rank"]) or len(set(selected_old)) != len(selected_old):
        raise ValueError("invalid basis row pivots")
    selected_new = []
    for row in selected_old:
        if row < len(insertion):
            selected_new.append(sorted_position[insertion[row]])
        else:
            linear = row - len(insertion)
            if not 0 <= linear < n:
                raise ValueError("basis row out of range")
            selected_new.append(len(ordered) + linear)
    rows = int(meta["rows_denominator"])
    columns = int(meta["columns_denominator"])
    files = meta["files"]
    start = np.memmap(args.matrix_dir / files["start"]["path"], mode="r", dtype="<u8")
    index = np.memmap(args.matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    value = np.memmap(args.matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    source = np.memmap(args.matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    target = np.memmap(args.matrix_dir / files["target"]["path"], mode="r", dtype="<i8")
    remap = np.full(rows, -1, dtype=np.int32)
    remap[np.asarray(selected_new, dtype=np.int32)] = np.arange(len(selected_new), dtype=np.int32)
    new_target_values = target[np.asarray(selected_new, dtype=np.int32)]
    if np.count_nonzero(new_target_values) != 1:
        raise ValueError("row basis does not retain the one-sparse target")

    new_start_values = np.zeros(columns + 1, dtype=np.uint64)
    for column in range(columns):
        begin, end = int(start[column]), int(start[column + 1])
        new_start_values[column + 1] = new_start_values[column] + np.count_nonzero(remap[index[begin:end]] >= 0)
    nnz = int(new_start_values[-1])
    out_start = np.memmap(args.output_dir / "start.u64le", mode="w+", dtype="<u8", shape=(columns + 1,))
    out_index = np.memmap(args.output_dir / "index.u32le", mode="w+", dtype="<u4", shape=(nnz,))
    out_value = np.memmap(args.output_dir / "value.i64le", mode="w+", dtype="<i8", shape=(nnz,))
    out_source = np.memmap(args.output_dir / "source.u64le", mode="w+", dtype="<u8", shape=(columns,))
    out_target = np.memmap(args.output_dir / "target.i64le", mode="w+", dtype="<i8", shape=(len(selected_new),))
    out_start[:] = new_start_values
    out_source[:] = source
    out_target[:] = new_target_values
    for column in range(columns):
        begin, end = int(start[column]), int(start[column + 1])
        mapped = remap[index[begin:end]]
        keep = mapped >= 0
        left, right = int(new_start_values[column]), int(new_start_values[column + 1])
        out_index[left:right] = mapped[keep]
        out_value[left:right] = value[begin:end][keep]
    for array in (out_start, out_index, out_value, out_source, out_target):
        array.flush()
    del out_start, out_index, out_value, out_source, out_target
    raw = {}
    for label, name in (("start", "start.u64le"), ("index", "index.u32le"), ("value", "value.i64le"), ("source", "source.u64le"), ("target", "target.i64le")):
        path = args.output_dir / name
        raw[label] = {"path": name, "bytes": path.stat().st_size, "sha256": sha256(path)}
    report = {
        "schema": "max11-sparse-lp-csc-v1",
        "verdict": "PASS",
        "method": "exact saved CSC restricted to named modular independent-row basis",
        "system": str(system),
        "system_sha256": meta["system_sha256"],
        "n": n,
        "source_matrix_report": str(meta_path),
        "source_matrix_report_sha256": sha256(meta_path),
        "basis": str(args.basis),
        "basis_sha256": sha256(args.basis),
        "prime": int(basis["prime"]),
        "rows_numerator": len(selected_new),
        "rows_denominator": len(selected_new),
        "source_rows_denominator": rows,
        "columns_numerator": columns,
        "columns_denominator": columns,
        "nonzeros_numerator": nnz,
        "nonzeros_denominator": nnz,
        "files": raw,
        "build_seconds": time.monotonic() - started,
        "no_claim": "A modular row-basis restriction is a search system; exact all-row replay is required for any identity claim.",
    }
    (args.output_dir / "matrix.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
