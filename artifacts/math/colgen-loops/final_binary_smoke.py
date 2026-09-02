#!/usr/bin/env python3
"""Fast independent smoke test for the final Rust binary and G-0038 adapter."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType


SCHEMA = "max11-gmp13-final-binary-smoke-v1"
UNIVERSE_SHA256 = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def emit(binary: Path, arguments: list[str]) -> None:
    subprocess.run(
        [str(binary), *arguments],
        check=True,
        text=True,
        capture_output=True,
    )


def write_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-binary", type=Path, required=True)
    parser.add_argument("--rust-lib", type=Path, required=True)
    parser.add_argument("--rust-main", type=Path, required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--python-dp", type=Path, required=True)
    parser.add_argument("--cross-module", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--records", type=int, default=8)
    parser.add_argument("--prime", type=int, default=1_000_003)
    parser.add_argument("--threads", type=int, default=4)
    args = parser.parse_args()
    if not 1 <= args.threads <= 4:
        raise SystemExit("--threads must lie in 1..4")
    if args.records <= 0:
        raise SystemExit("--records must be positive")
    if sha256_path(args.universe) != UNIVERSE_SHA256:
        raise AssertionError("G-0038 compressed hash mismatch")

    python_dp = load_module(args.python_dp, "gmp13_final_span_structure")
    cross = load_module(args.cross_module, "gmp13_final_cross_helpers")
    with gzip.open(args.universe, "rt", encoding="utf-8") as handle:
        header = json.loads(next(handle))
        records = [json.loads(next(handle)) for _ in range(args.records)]
    if header.get("expected_record_count") != 7_015_841:
        raise AssertionError("G-0038 header count mismatch")
    if [row.get("sequence") for row in records] != list(range(args.records)):
        raise AssertionError("G-0038 prefix sequence mismatch")

    with tempfile.TemporaryDirectory(prefix="gmp13-final-smoke-") as raw_temporary:
        temporary = Path(raw_temporary)
        sample = temporary / "records.jsonl"
        sample.write_text(
            "".join(
                json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
                for row in records
            )
        )
        stream_exact = temporary / "stream-exact.jsonl"
        direct_exact = temporary / "direct-exact.jsonl"
        stream_modular = temporary / "stream-modular.bin"
        common = [
            "--input",
            str(args.universe),
            "--threads",
            str(args.threads),
            "--start",
            "0",
            "--limit",
            str(args.records),
        ]
        emit(
            args.rust_binary,
            ["emit-universe", *common, "--format", "jsonl", "--output", str(stream_exact)],
        )
        emit(
            args.rust_binary,
            [
                "emit-records",
                "--input",
                str(sample),
                "--n",
                "11",
                "--branch-edges",
                "5",
                "--threads",
                str(args.threads),
                "--format",
                "jsonl",
                "--output",
                str(direct_exact),
            ],
        )
        if stream_exact.read_bytes() != direct_exact.read_bytes():
            raise AssertionError("streaming/direct exact bytes differ")
        exact_columns = cross.parse_json_columns(stream_exact)

        python_matches = 0
        for record, column in zip(records, exact_columns, strict=True):
            first, second = cross.branches(record, 5)
            expected = python_dp.column_dp(first, second, 11)
            if cross.column_signature(column) != expected:
                raise AssertionError(f"Python mismatch at sequence {record['sequence']}")
            python_matches += 1

        emit(
            args.rust_binary,
            [
                "emit-universe",
                *common,
                "--format",
                "binary",
                "--modulus",
                str(args.prime),
                "--output",
                str(stream_modular),
            ],
        )
        binary_header, modular_columns = cross.parse_binary_columns(stream_modular)
        expected_header = {
            "n": 11,
            "branch_edges": 5,
            "modulus": args.prime,
            "count": args.records,
        }
        if binary_header != expected_header:
            raise AssertionError("MCOLGEN1 header mismatch")
        modular_matches = cross.compare_modular(exact_columns, modular_columns, args.prime)
        mutant = json.loads(json.dumps(modular_columns))
        mutant[0]["linear"][0] = (int(mutant[0]["linear"][0]) + 1) % args.prime
        try:
            cross.compare_modular(exact_columns, mutant, args.prime)
        except AssertionError:
            mutant_rejected = 1
        else:
            raise AssertionError("planted modular coefficient mutant survived")

    report = {
        "schema": SCHEMA,
        "result": "PASS",
        "rust_binary": str(args.rust_binary),
        "rust_binary_sha256": sha256_path(args.rust_binary),
        "rust_lib_sha256": sha256_path(args.rust_lib),
        "rust_main_sha256": sha256_path(args.rust_main),
        "universe": str(args.universe),
        "universe_compressed_sha256": UNIVERSE_SHA256,
        "python_dp": str(args.python_dp),
        "python_dp_sha256": sha256_path(args.python_dp),
        "prefix_records_checked": args.records,
        "prefix_record_denominator": args.records,
        "stream_direct_exact_matches": args.records,
        "stream_direct_exact_denominator": args.records,
        "python_dp_matches": python_matches,
        "python_dp_denominator": args.records,
        "modular_matches": modular_matches,
        "modular_denominator": args.records,
        "modulus": args.prime,
        "mcolgen_magic": "MCOLGEN1",
        "planted_modular_mutants_rejected": mutant_rejected,
        "planted_modular_mutant_denominator": 1,
        "threads": args.threads,
        "no_claim": (
            "This is a fast current-binary control on the first eight frozen G-0038 records. "
            "It is not the 2,000-record random cross-check, a full column pass, a rank result, "
            "or a MAX11 membership result."
        ),
    }
    write_json(args.output, report)
    print(
        "GMP13_FINAL_BINARY_SMOKE_PASS "
        f"python={python_matches}/{args.records} modular={modular_matches}/{args.records} "
        f"stream_direct={args.records}/{args.records} mutant=1/1",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
