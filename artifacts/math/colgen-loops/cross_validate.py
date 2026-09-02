#!/usr/bin/env python3
"""Cross-check Rust loop columns against the prior Python DP and wire formats."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from math import factorial
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time
from types import ModuleType


PRIME = 1_000_003
REPORT_SCHEMA = "max11-gmp13-cross-validation-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_module(path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location("gmp5_span_structure", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import Python DP from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_records(path: Path) -> list[dict[str, object]]:
    records = [json.loads(line) for line in path.read_text().splitlines() if line]
    if not records:
        raise AssertionError(f"empty sample {path}")
    return records


def branches(record: dict[str, object], branch_edges: int) -> tuple[list[tuple[int, int]], list[tuple[int, int]]]:
    signed_mass = int(record["signed_mass"])
    if signed_mass > branch_edges:
        raise AssertionError("sample signed mass exceeds branch size")
    common = [(0, 1)] * (branch_edges - signed_mass)
    negative = [tuple(edge) for edge in record["negative_edges"]]
    positive = [tuple(edge) for edge in record["positive_edges"]]
    return negative + common, positive + common


def run_emit(
    binary: Path,
    sample: Path,
    output: Path,
    n: int,
    branch_edges: int,
    threads: int,
    format_name: str,
    modulus: int | None = None,
) -> str:
    command = [
        str(binary),
        "emit-records",
        "--input",
        str(sample),
        "--n",
        str(n),
        "--branch-edges",
        str(branch_edges),
        "--threads",
        str(threads),
        "--format",
        format_name,
        "--output",
        str(output),
    ]
    if modulus is not None:
        command.extend(["--modulus", str(modulus)])
    completed = subprocess.run(command, check=True, text=True, capture_output=True)
    return completed.stderr.strip()


def parse_json_columns(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def parse_binary_columns(path: Path) -> tuple[dict[str, int], list[dict[str, object]]]:
    payload = memoryview(path.read_bytes())
    cursor = 0

    def take(size: int) -> memoryview:
        nonlocal cursor
        if cursor + size > len(payload):
            raise AssertionError("truncated MCOLGEN1 payload")
        result = payload[cursor : cursor + size]
        cursor += size
        return result

    if bytes(take(8)) != b"MCOLGEN1":
        raise AssertionError("wrong MCOLGEN1 magic")
    n, branch_edges = struct.unpack("<HH", take(4))
    modulus, count = struct.unpack("<QQ", take(16))
    columns = []
    for _ in range(count):
        (record_index,) = struct.unpack("<Q", take(8))
        linear = list(struct.unpack(f"<{n}q", take(8 * n)))
        (hinge_count,) = struct.unpack("<Q", take(8))
        hinges = []
        for _ in range(hinge_count):
            direction = list(struct.unpack(f"<{n}h", take(2 * n)))
            (coefficient,) = struct.unpack("<q", take(8))
            hinges.append({"direction": direction, "coefficient": coefficient})
        columns.append(
            {
                "record_index": record_index,
                "modulus": modulus or None,
                "linear": linear,
                "hinges": hinges,
            }
        )
    if cursor != len(payload):
        raise AssertionError("trailing bytes after MCOLGEN1 columns")
    return {"n": n, "branch_edges": branch_edges, "modulus": modulus, "count": count}, columns


def column_signature(column: dict[str, object]) -> tuple[tuple[int, ...], dict[tuple[int, ...], int]]:
    linear = tuple(map(int, column["linear"]))
    hinges = {
        tuple(map(int, item["direction"])): int(item["coefficient"])
        for item in column["hinges"]
    }
    if len(hinges) != len(column["hinges"]):
        raise AssertionError("duplicate hinge direction in Rust output")
    return linear, hinges


def compare_python_stream(
    module: ModuleType,
    sample: Path,
    rust_output: Path,
    n: int,
    branch_edges: int,
    keep_for_modular: int = 0,
) -> tuple[dict[str, int], list[dict[str, object]], list[dict[str, object]]]:
    records = load_records(sample)
    matches = 0
    loop_bearing = 0
    minimum_coordinate_nonzero = 0
    retained_records: list[dict[str, object]] = []
    retained_columns: list[dict[str, object]] = []
    with rust_output.open("r", encoding="utf-8") as rust_handle:
        for index, record in enumerate(records):
            line = rust_handle.readline()
            if not line:
                raise AssertionError("Rust output ended before sample")
            rust_column = json.loads(line)
            if int(rust_column["record_index"]) != int(record["sequence"]):
                raise AssertionError("sample sequence/column index mismatch")
            left, right = branches(record, branch_edges)
            python_column = module.column_dp(left, right, n)
            rust_column_signature = column_signature(rust_column)
            if python_column != rust_column_signature:
                raise AssertionError(f"Rust/Python mismatch at sequence {record['sequence']}")
            matches += 1
            loops = int(record["negative_loop_count"]) + int(record["positive_loop_count"])
            loop_bearing += int(loops > 0)
            minimum_coordinate_nonzero += int(rust_column_signature[0][0] != 0)
            if index < keep_for_modular:
                retained_records.append(record)
                retained_columns.append(rust_column)
            if matches % 100 == 0:
                print(
                    f"GMP13_CROSS_PROGRESS n={n} matches={matches}/{len(records)}",
                    flush=True,
                )
        if rust_handle.readline():
            raise AssertionError("Rust output contains more columns than sample")
    return (
        {
            "matches": matches,
            "denominator": len(records),
            "loop_bearing_records": loop_bearing,
            "minimum_coordinate_nonzero_records": minimum_coordinate_nonzero,
        },
        retained_records,
        retained_columns,
    )


def compare_modular(
    exact_columns: list[dict[str, object]],
    modular_columns: list[dict[str, object]],
    modulus: int,
) -> int:
    if len(exact_columns) != len(modular_columns):
        raise AssertionError("exact/modular column count mismatch")
    matches = 0
    for exact, modular in zip(exact_columns, modular_columns, strict=True):
        if exact["record_index"] != modular["record_index"]:
            raise AssertionError("exact/modular record index mismatch")
        exact_linear, exact_hinges = column_signature(exact)
        modular_linear, modular_hinges = column_signature(modular)
        expected_linear = tuple(value % modulus for value in exact_linear)
        expected_hinges = {
            direction: value % modulus for direction, value in exact_hinges.items()
        }
        if modular_linear != expected_linear or modular_hinges != expected_hinges:
            raise AssertionError(f"modular mismatch at record {exact['record_index']}")
        matches += 1
    return matches


def carrier_controls(binary: Path, temporary: Path, n: int, branch_edges: int) -> dict[str, object]:
    exact_path = temporary / "base-atoms-exact.jsonl"
    modular_path = temporary / "base-atoms-modular.bin"
    subprocess.run(
        [
            str(binary),
            "emit-base-atoms",
            "--n",
            str(n),
            "--branch-edges",
            str(branch_edges),
            "--format",
            "jsonl",
            "--output",
            str(exact_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [
            str(binary),
            "emit-base-atoms",
            "--n",
            str(n),
            "--branch-edges",
            str(branch_edges),
            "--format",
            "binary",
            "--modulus",
            str(PRIME),
            "--output",
            str(modular_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    exact = parse_json_columns(exact_path)
    header, modular = parse_binary_columns(modular_path)
    if len(exact) != 2 or header != {
        "n": n,
        "branch_edges": branch_edges,
        "modulus": PRIME,
        "count": 2,
    }:
        raise AssertionError("base atom format header/count mismatch")
    edge_factor = 2 * factorial(n - 2) * branch_edges
    expected_nonloops = [edge_factor * rank for rank in range(n)]
    expected_loops = [branch_edges * factorial(n - 1)] * n
    if exact[0]["linear"] != expected_nonloops or exact[1]["linear"] != expected_loops:
        raise AssertionError("5E/5L exact base coefficients mismatch")
    if exact[0]["hinges"] or exact[1]["hinges"]:
        raise AssertionError("base atom unexpectedly has hinges")
    modular_matches = compare_modular(exact, modular, PRIME)
    return {
        "exact_base_atoms": 2,
        "exact_base_atom_denominator": 2,
        "modular_base_atoms": modular_matches,
        "modular_base_atom_denominator": 2,
        "five_nonloops_minimum_coordinate": expected_nonloops[0],
        "five_loops_minimum_coordinate": expected_loops[0],
        "modulus": PRIME,
        "binary_magic": "MCOLGEN1",
    }


def create_json(path: Path, value: object) -> None:
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def create_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("x", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")


def self_test() -> None:
    exact = [
        {
            "record_index": 3,
            "linear": [-2, 4],
            "hinges": [{"direction": [1, -1], "coefficient": -5}],
        }
    ]
    modular = [
        {
            "record_index": 3,
            "linear": [PRIME - 2, 4],
            "hinges": [{"direction": [1, -1], "coefficient": PRIME - 5}],
        }
    ]
    assert compare_modular(exact, modular, PRIME) == 1
    mutant = json.loads(json.dumps(modular))
    mutant[0]["linear"][0] -= 1
    try:
        compare_modular(exact, mutant, PRIME)
    except AssertionError:
        pass
    else:
        raise AssertionError("modular mutation survived")
    print("GMP13_CROSS_SELF_TEST_PASS positive=1 mutant=1/1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rust-binary", type=Path)
    parser.add_argument("--python-dp", type=Path)
    parser.add_argument("--sample-n9", type=Path)
    parser.add_argument("--sample-n10", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    required = (
        args.rust_binary,
        args.python_dp,
        args.sample_n9,
        args.sample_n10,
        args.output,
    )
    if any(value is None for value in required):
        raise SystemExit("all path arguments are required")
    if not 1 <= args.threads <= 4:
        raise SystemExit("--threads must lie in 1..4")
    started = time.monotonic()
    module = load_module(args.python_dp)
    with tempfile.TemporaryDirectory(prefix="gmp13-cross-") as raw_temporary:
        temporary = Path(raw_temporary)
        results: dict[str, object] = {}
        modular_records: list[dict[str, object]] = []
        modular_exact: list[dict[str, object]] = []
        for n, sample in ((9, args.sample_n9), (10, args.sample_n10)):
            exact_path = temporary / f"n{n}-exact.jsonl"
            stderr = run_emit(
                args.rust_binary,
                sample,
                exact_path,
                n,
                5,
                args.threads,
                "jsonl",
            )
            comparison, retained_records, retained_columns = compare_python_stream(
                module,
                sample,
                exact_path,
                n,
                5,
                keep_for_modular=16 if n == 9 else 0,
            )
            results[f"n{n}"] = {
                **comparison,
                "sample": str(sample),
                "sample_sha256": sha256_path(sample),
                "rust_stderr": stderr,
            }
            if n == 9:
                modular_records = retained_records
                modular_exact = retained_columns
            exact_path.unlink()

        modular_sample = temporary / "n9-modular-sample.jsonl"
        create_jsonl(modular_sample, modular_records)
        modular_path = temporary / "n9-modular.bin"
        modular_stderr = run_emit(
            args.rust_binary,
            modular_sample,
            modular_path,
            9,
            5,
            args.threads,
            "binary",
            PRIME,
        )
        header, modular_columns = parse_binary_columns(modular_path)
        if header != {
            "n": 9,
            "branch_edges": 5,
            "modulus": PRIME,
            "count": len(modular_exact),
        }:
            raise AssertionError("n=9 binary header mismatch")
        modular_matches = compare_modular(modular_exact, modular_columns, PRIME)
        carriers = carrier_controls(args.rust_binary, temporary, 11, 5)

    report = {
        "schema": REPORT_SCHEMA,
        "result": "PASS",
        "rust_binary": str(args.rust_binary),
        "rust_binary_sha256": sha256_path(args.rust_binary),
        "python_dp": str(args.python_dp),
        "python_dp_sha256": sha256_path(args.python_dp),
        "threads": args.threads,
        "python_dp_samples": results,
        "python_dp_matches": sum(int(row["matches"]) for row in results.values()),
        "python_dp_denominator": sum(int(row["denominator"]) for row in results.values()),
        "modular_binary_matches": modular_matches,
        "modular_binary_denominator": len(modular_exact),
        "modular_binary_modulus": PRIME,
        "modular_rust_stderr": modular_stderr,
        "carrier_controls": carriers,
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "These are exact cross-implementation checks on two named random samples "
            "and exact/modular format controls. They are not a complete G-0038 column "
            "generation, rank computation, or MAX11 membership result."
        ),
    }
    create_json(args.output, report)
    print(
        "GMP13_CROSS_VALIDATE_PASS "
        f"python={report['python_dp_matches']}/{report['python_dp_denominator']} "
        f"modular={modular_matches}/{len(modular_exact)} carriers=2/2",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
