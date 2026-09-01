#!/usr/bin/env python3
"""Two-prime custody wrapper for an already-extracted square i64LE/i128LE matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


PRIMES = (1_000_003, 1_000_033)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def regular(path: Path, label: str) -> Path:
    resolved = path.resolve(strict=True)
    if not resolved.is_file():
        raise ValueError(f"{label} is not a regular file: {resolved}")
    return resolved


def checked_digest(expected: str | None, actual: str) -> dict[str, Any]:
    if expected is not None:
        expected = expected.lower()
        if len(expected) != 64 or any(c not in "0123456789abcdef" for c in expected):
            raise ValueError("expected matrix SHA-256 is malformed")
        if expected != actual:
            raise ValueError(f"matrix SHA-256 mismatch: expected {expected}, found {actual}")
    return {"actual_sha256": actual, "expected_sha256": expected, "externally_pinned": expected is not None}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--dimension", required=True, type=int)
    parser.add_argument("--encoding", choices=("i64le", "i128le"), default="i64le")
    parser.add_argument("--ranker", required=True, type=Path)
    parser.add_argument("--ranker-source", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    parser.add_argument("--expected-matrix-sha256")
    parser.add_argument("--binding-file", action="append", default=[], metavar="NAME=PATH")
    args = parser.parse_args()

    matrix = regular(args.matrix, "matrix")
    ranker = regular(args.ranker, "ranker")
    ranker_source = regular(args.ranker_source, "ranker source")
    wrapper_source = Path(__file__).resolve(strict=True)
    if not os.access(ranker, os.X_OK):
        raise ValueError("ranker is not executable")
    if args.dimension <= 0:
        raise ValueError("dimension must be positive")
    bytes_per_cell = 8 if args.encoding == "i64le" else 16
    expected_bytes = args.dimension * args.dimension * bytes_per_cell
    if expected_bytes > (1 << 63) - 1:
        raise ValueError("matrix size exceeds custody limit")
    if matrix.stat().st_size != expected_bytes:
        raise ValueError(f"matrix size mismatch: expected {expected_bytes}, found {matrix.stat().st_size}")

    bindings: dict[str, Path] = {}
    for item in args.binding_file:
        if "=" not in item:
            raise ValueError("binding-file must use NAME=PATH")
        name, path_text = item.split("=", 1)
        if not name or "/" in name or name in bindings:
            raise ValueError(f"invalid or duplicate binding name: {name!r}")
        bindings[name] = regular(Path(path_text), f"binding {name}")

    output = args.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    primary_paths = {
        "matrix": matrix,
        "ranker": ranker,
        "ranker_source": ranker_source,
        "wrapper_source": wrapper_source,
    }
    primary_before = {name: sha256_file(path) for name, path in primary_paths.items()}
    matrix_pin = checked_digest(args.expected_matrix_sha256, primary_before["matrix"])
    bindings_before = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in sorted(bindings.items())
    }

    commands: list[list[str]] = []
    results: list[dict[str, Any]] = []
    for prime in PRIMES:
        receipt_path = output / f"rank_mod_{prime}.json"
        command = [
            str(ranker),
            str(matrix),
            args.encoding,
            str(args.dimension),
            str(args.dimension),
            "0",
            str(args.dimension),
            "-",
            str(prime),
            str(receipt_path),
        ]
        commands.append(command)
        process = subprocess.run(command, text=True, capture_output=True, check=False)
        if process.returncode != 0:
            raise RuntimeError(
                f"ranker failed at p={prime} with exit {process.returncode}\n"
                f"stdout:\n{process.stdout}\nstderr:\n{process.stderr}"
            )
        if process.stdout or process.stderr:
            raise RuntimeError("ranker emitted unexpected output on a successful run")
        with receipt_path.open("rb") as stream:
            receipt = json.load(stream)
        expected = {
            "schema": "g0181.flint-signed-le-rank-certificate.v2",
            "matrix_path": str(matrix),
            "encoding": args.encoding,
            "bytes_per_cell": bytes_per_cell,
            "input_rows": args.dimension,
            "input_columns": args.dimension,
            "input_bytes": expected_bytes,
            "coordinate_start_inclusive": 0,
            "coordinate_end_exclusive": args.dimension,
            "excluded_source_rows": [],
            "selected_rows": args.dimension,
            "selected_columns": args.dimension,
            "selected_cells": args.dimension * args.dimension,
            "reduction_crosscheck_cells": args.dimension * args.dimension,
            "selected_raw_cells_sha256": primary_before["matrix"],
            "prime": prime,
        }
        for key, value in expected.items():
            if receipt.get(key) != value:
                raise ValueError(f"receipt {receipt_path.name} field {key}: expected {value!r}, found {receipt.get(key)!r}")
        rank = receipt.get("rank_mod_prime")
        determinant = receipt.get("determinant_mod_prime")
        full = receipt.get("full_rank_mod_prime")
        pivots = receipt.get("pivot_columns")
        if isinstance(rank, bool) or not isinstance(rank, int) or not 0 <= rank <= args.dimension:
            raise ValueError("invalid modular rank")
        if isinstance(determinant, bool) or not isinstance(determinant, int) or not 0 <= determinant < prime:
            raise ValueError("invalid modular determinant")
        if full is not (rank == args.dimension) or (determinant != 0) != full:
            raise ValueError("determinant/rank/full-rank receipt inconsistency")
        if not isinstance(pivots, list) or len(pivots) != rank or pivots != sorted(set(pivots)):
            raise ValueError("invalid pivot receipt")
        if full and (pivots != list(range(args.dimension)) or receipt.get("rref_identity") is not True):
            raise ValueError("invalid full-rank RREF receipt")
        results.append(
            {
                "prime": prime,
                "receipt_path": str(receipt_path),
                "receipt_bytes": receipt_path.stat().st_size,
                "receipt_sha256": sha256_file(receipt_path),
                "rank_mod_prime": rank,
                "determinant_mod_prime": determinant,
                "full_rank_mod_prime": full,
                "selected_modp_u64le_sha256": receipt["selected_modp_u64le_sha256"],
                "rref_modp_u64le_sha256": receipt["rref_modp_u64le_sha256"],
            }
        )

    primary_after = {name: sha256_file(path) for name, path in primary_paths.items()}
    if primary_after != primary_before:
        raise ValueError("matrix, ranker, or source changed during the run")
    bindings_after = {
        name: {"path": str(path), "bytes": path.stat().st_size, "sha256": sha256_file(path)}
        for name, path in sorted(bindings.items())
    }
    if bindings_after != bindings_before:
        raise ValueError("a bound producer artifact changed during the run")

    any_full = any(item["full_rank_mod_prime"] for item in results)
    all_full = all(item["full_rank_mod_prime"] for item in results)
    bundle = {
        "schema": "g0181.direct-square-two-prime-certificate.v1",
        "claim_boundary": (
            "This certificate concerns only the exact bound square integer matrix. A nonzero determinant "
            "modulo either fixed prime proves full rank over Q. A zero modular determinant does not prove "
            "singularity over Q. Upstream evaluator semantics and broader representability claims remain separate."
        ),
        "proof_logic": (
            "The determinant of an integer matrix is an integer. Nonzero reduction modulo a prime implies "
            "the integer determinant is nonzero, hence the matrix is nonsingular over Q."
        ),
        "fixed_primes": list(PRIMES),
        "q_full_rank_certified_by_nonzero_modular_determinant": any_full,
        "all_two_fixed_primes_full_rank": all_full,
        "dimension": args.dimension,
        "encoding": args.encoding,
        "matrix_external_hash_pin": matrix_pin,
        "inputs_and_sources": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": primary_before[name]}
            for name, path in primary_paths.items()
        },
        "producer_bindings": bindings_before,
        "all_inputs_rehashed_unchanged_after_both_runs": True,
        "commands": commands,
        "prime_receipts": results,
    }
    bundle_path = output / "certificate_bundle.json"
    write_new(bundle_path, canonical_json(bundle))
    bundle_sha = sha256_file(bundle_path)
    detached = output / "certificate_bundle.json.sha256"
    write_new(detached, f"{bundle_sha}  {bundle_path.name}\n".encode())
    print(
        json.dumps(
            {
                "bundle": str(bundle_path),
                "bundle_sha256": bundle_sha,
                "q_full_rank_certified": any_full,
                "all_two_fixed_primes_full_rank": all_full,
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"certify_square: {error}", file=sys.stderr)
        raise SystemExit(1)
