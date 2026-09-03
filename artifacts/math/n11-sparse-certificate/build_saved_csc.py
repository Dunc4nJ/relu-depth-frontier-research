#!/usr/bin/env python3
"""Build a deterministic exact-integer CSC matrix from a saved JSONL system."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import time
from pathlib import Path

import numpy as np


SCHEMA = "max11-sparse-lp-csc-v1"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def columns(path: Path):
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            yield json.loads(line)


def raw_paths(output: Path) -> dict[str, Path]:
    return {
        "start": output / "start.u64le",
        "index": output / "index.u32le",
        "value": output / "value.i64le",
        "source": output / "source.u64le",
        "target": output / "target.i64le",
    }


def build(system: Path, output: Path) -> dict:
    started = time.monotonic()
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.mkdir(parents=True)

    hinge_rows: set[str] = set()
    n = None
    column_count = 0
    expected_nnz = 0
    for column in columns(system):
        if n is None:
            n = len(column["lin"])
        if len(column["lin"]) != n:
            raise ValueError("inconsistent linear row count")
        hinge_rows.update(column["h"])
        expected_nnz += sum(int(value) != 0 for value in column["h"].values())
        expected_nnz += sum(int(value) != 0 for value in column["lin"])
        column_count += 1
    if not column_count or n is None:
        raise ValueError("empty system")
    ordered_hinges = sorted(hinge_rows)
    row_of = {key: row for row, key in enumerate(ordered_hinges)}
    row_count = len(ordered_hinges) + n

    paths = raw_paths(output)
    start = np.memmap(paths["start"], mode="w+", dtype="<u8", shape=(column_count + 1,))
    index = np.memmap(paths["index"], mode="w+", dtype="<u4", shape=(expected_nnz,))
    value = np.memmap(paths["value"], mode="w+", dtype="<i8", shape=(expected_nnz,))
    source = np.memmap(paths["source"], mode="w+", dtype="<u8", shape=(column_count,))
    target = np.memmap(paths["target"], mode="w+", dtype="<i8", shape=(row_count,))
    target[:] = 0
    target[row_count - 1] = 1
    start[0] = 0

    cursor = 0
    for column_number, column in enumerate(columns(system)):
        entries = [(row_of[key], int(raw)) for key, raw in column["h"].items() if int(raw)]
        entries.extend(
            (len(ordered_hinges) + row, int(raw))
            for row, raw in enumerate(column["lin"])
            if int(raw)
        )
        entries.sort()
        stop = cursor + len(entries)
        if stop > expected_nnz:
            raise RuntimeError("second pass contains more nonzeros than first pass")
        if entries:
            index[cursor:stop] = [item[0] for item in entries]
            value[cursor:stop] = [item[1] for item in entries]
        source[column_number] = column_number
        cursor = stop
        start[column_number + 1] = cursor
        if (column_number + 1) % 256 == 0 or column_number + 1 == column_count:
            print(
                f"SAVED_CSC columns={column_number + 1}/{column_count} "
                f"nnz={cursor}/{expected_nnz} seconds={time.monotonic() - started:.3f}",
                flush=True,
            )
    if cursor != expected_nnz:
        raise RuntimeError(f"second-pass nnz {cursor} != first-pass {expected_nnz}")
    for array in (start, index, value, source, target):
        array.flush()
    del start, index, value, source, target

    files = {
        name: {"path": path.name, "bytes": path.stat().st_size, "sha256": sha256(path)}
        for name, path in paths.items()
    }
    report = {
        "schema": SCHEMA,
        "verdict": "PASS",
        "method": "two-pass exact saved-system CSC construction",
        "system": str(system),
        "system_bytes": system.stat().st_size,
        "system_sha256": sha256(system),
        "n": n,
        "rows_numerator": row_count,
        "rows_denominator": row_count,
        "hinge_rows_denominator": len(ordered_hinges),
        "linear_rows_denominator": n,
        "columns_numerator": column_count,
        "columns_denominator": column_count,
        "nonzeros_numerator": expected_nnz,
        "nonzeros_denominator": expected_nnz,
        "files": files,
        "build_seconds": time.monotonic() - started,
        "max_rss_kib": __import__("resource").getrusage(__import__("resource").RUSAGE_SELF).ru_maxrss,
        "no_claim": "This is an exact matrix construction, not a span identity or a MAX certificate.",
    }
    (output / "matrix.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(build(args.system, args.output_dir), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
