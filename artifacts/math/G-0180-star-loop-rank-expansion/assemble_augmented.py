#!/usr/bin/env python3
"""Assemble the quotient base-plus-expansion matrix with exact row custody."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any


BASE_ROWS = 5_771
BASE_COLUMNS = 5_771
EXPANSION_ROWS = 5_769
EXPANSION_COLUMNS = 1_024
OUTPUT_COLUMNS = BASE_COLUMNS + EXPANSION_COLUMNS
BASE_SHA256 = "0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad"
RECORDS_SHA256 = "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4"
RELATIONS_SHA256 = "c2fe511b628169929cce87fc116ab7fde09defc5746d1e40663660502d2ad6fa"
REMOVED_INITIAL = {1548, 4259}
REMOVED_QUOTIENT = {3140, 5656}


class AssemblyError(RuntimeError):
    """An input, layout, or custody invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def open_new(path: Path) -> tuple[int, Any]:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    return descriptor, os.fdopen(descriptor, "wb")


def write_new(path: Path, payload: bytes) -> None:
    _descriptor, stream = open_new(path)
    try:
        with stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", required=True, type=Path)
    parser.add_argument("--expansion", required=True, type=Path)
    parser.add_argument("--expansion-receipt", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--relations", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output == arguments.receipt:
        raise AssemblyError("output and receipt collide")
    if arguments.output.exists() or arguments.receipt.exists():
        raise AssemblyError("refusing overwrite")

    paths = {
        "base": arguments.base.resolve(strict=True),
        "expansion": arguments.expansion.resolve(strict=True),
        "expansion_receipt": arguments.expansion_receipt.resolve(strict=True),
        "records": arguments.records.resolve(strict=True),
        "relations": arguments.relations.resolve(strict=True),
        "assembler_source": Path(__file__).resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    if opening["base"] != BASE_SHA256:
        raise AssemblyError("base matrix hash drift")
    if opening["records"] != RECORDS_SHA256:
        raise AssemblyError("record hash drift")
    if opening["relations"] != RELATIONS_SHA256:
        raise AssemblyError("intrinsic-relation hash drift")
    if paths["base"].stat().st_size != BASE_ROWS * BASE_COLUMNS * 8:
        raise AssemblyError("base matrix size drift")
    if paths["expansion"].stat().st_size != EXPANSION_ROWS * EXPANSION_COLUMNS * 8:
        raise AssemblyError("expansion matrix size drift")

    expansion_receipt = json.loads(paths["expansion_receipt"].read_bytes())
    if expansion_receipt.get("schema") != "g0180.quotient-expansion-price-matrix.v1":
        raise AssemblyError("expansion receipt schema drift")
    matrix_receipt = expansion_receipt.get("matrix", {})
    if (
        matrix_receipt.get("shape") != [EXPANSION_ROWS, EXPANSION_COLUMNS]
        or matrix_receipt.get("bytes") != EXPANSION_ROWS * EXPANSION_COLUMNS * 8
        or matrix_receipt.get("sha256") != opening["expansion"]
    ):
        raise AssemblyError("expansion matrix receipt drift")
    quotient = expansion_receipt.get("quotient_records", {})
    if quotient.get("excluded_sequences_exactly") != [1548, 3140, 4259, 5656]:
        raise AssemblyError("expansion quotient exclusion drift")

    records_document = json.loads(paths["records"].read_bytes())
    records = records_document.get("records")
    if not isinstance(records, list) or len(records) != 5_773:
        raise AssemblyError("record census drift")
    if [record.get("sequence") for record in records] != list(range(5_773)):
        raise AssemblyError("record sequence/index drift")
    base_sequences = [
        sequence for sequence in range(5_773) if sequence not in REMOVED_INITIAL
    ]
    output_sequences = [
        sequence for sequence in base_sequences if sequence not in REMOVED_QUOTIENT
    ]
    if len(base_sequences) != BASE_ROWS or len(output_sequences) != EXPANSION_ROWS:
        raise AssemblyError("row-order census drift")
    skipped_base_rows = [
        index for index, sequence in enumerate(base_sequences) if sequence in REMOVED_QUOTIENT
    ]
    if skipped_base_rows != [3139, 5654]:
        raise AssemblyError("quotient base-row positions drift")

    base_row_bytes = BASE_COLUMNS * 8
    expansion_row_bytes = EXPANSION_COLUMNS * 8
    digest = hashlib.sha256()
    raw_descriptor, output_stream = open_new(arguments.output)
    del raw_descriptor
    output_rows = 0
    try:
        with output_stream, paths["base"].open("rb") as base, paths["expansion"].open("rb") as expansion:
            for base_index, sequence in enumerate(base_sequences):
                base_row = base.read(base_row_bytes)
                if len(base_row) != base_row_bytes:
                    raise AssemblyError("short base-matrix row")
                if sequence in REMOVED_QUOTIENT:
                    continue
                expansion_row = expansion.read(expansion_row_bytes)
                if len(expansion_row) != expansion_row_bytes:
                    raise AssemblyError("short expansion-matrix row")
                output_stream.write(base_row)
                output_stream.write(expansion_row)
                digest.update(base_row)
                digest.update(expansion_row)
                output_rows += 1
            if base.read(1) or expansion.read(1):
                raise AssemblyError("trailing input matrix bytes")
            output_stream.flush()
            os.fsync(output_stream.fileno())
    except BaseException:
        try:
            arguments.output.unlink()
        except FileNotFoundError:
            pass
        raise
    if output_rows != EXPANSION_ROWS:
        raise AssemblyError("output row census drift")
    expected_bytes = EXPANSION_ROWS * OUTPUT_COLUMNS * 8
    if arguments.output.stat().st_size != expected_bytes:
        raise AssemblyError("augmented matrix byte census drift")
    streaming_sha256 = digest.hexdigest()
    if sha256_file(arguments.output) != streaming_sha256:
        raise AssemblyError("augmented matrix end-rehash drift")

    closing = {name: sha256_file(path) for name, path in paths.items()}
    if closing != opening:
        raise AssemblyError("input or source changed during assembly")
    receipt = {
        "schema": "g0180.quotient-augmented-matrix.v1",
        "result": "EXACT_QUOTIENT_BASE_PLUS_1024_EXPANSION_ASSEMBLED_AWAITING_RANK",
        "claim_boundary": (
            "Exact row-custody assembly only. The base and expansion rows are interleaved "
            "record by record after removing the two certified quotient representatives. "
            "No rank, kernel, target-membership, representability, or lower-bound claim is made."
        ),
        "bindings": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": opening[name]}
            for name, path in paths.items()
        },
        "row_custody": {
            "base_input_rows": BASE_ROWS,
            "skipped_base_row_indices_zero_based": skipped_base_rows,
            "skipped_record_sequences": sorted(REMOVED_QUOTIENT),
            "output_rows": output_rows,
            "output_record_sequence_first": output_sequences[0],
            "output_record_sequence_last": output_sequences[-1],
            "layout_check": "each output row is its complete 5771-cell base row followed by its 1024-cell expansion row",
        },
        "matrix": {
            "path": str(arguments.output.resolve()),
            "shape": [EXPANSION_ROWS, OUTPUT_COLUMNS],
            "base_columns": BASE_COLUMNS,
            "expansion_columns": EXPANSION_COLUMNS,
            "bytes": expected_bytes,
            "sha256": streaming_sha256,
            "encoding": "record-major signed-i64 little-endian",
            "rehashed_after_sync": True,
        },
        "rank_prefixes": [
            {"name": "quotient-base", "column_end_exclusive": BASE_COLUMNS},
            {"name": "hash-prefix-480", "column_end_exclusive": BASE_COLUMNS + 480},
            {"name": "rank-directed-1024", "column_end_exclusive": OUTPUT_COLUMNS},
        ],
        "all_inputs_and_source_rehashed_unchanged_at_end": True,
    }
    write_new(arguments.receipt, canonical_json(receipt))
    print(
        json.dumps(
            {
                "output": str(arguments.output.resolve()),
                "output_sha256": streaming_sha256,
                "receipt": str(arguments.receipt.resolve()),
                "receipt_sha256": sha256_file(arguments.receipt),
                "shape": [EXPANSION_ROWS, OUTPUT_COLUMNS],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"assemble_augmented: {error}", file=sys.stderr)
        raise SystemExit(1)
