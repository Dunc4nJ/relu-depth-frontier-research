#!/usr/bin/env python3
"""Independent production-path tests for the G-0179 square rank certificate."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import subprocess
import sys
from pathlib import Path
from typing import Any


PRIMES = (1_000_003, 1_000_033)
I64_MIN = -(1 << 63)
I64_MAX = (1 << 63) - 1


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_i64_matrix(path: Path, rows: list[list[int]]) -> None:
    if not rows or any(len(row) != len(rows) for row in rows):
        raise ValueError("fixture must be a nonempty square matrix")
    payload = bytearray()
    for row in rows:
        for value in row:
            if not I64_MIN <= value <= I64_MAX:
                raise ValueError("fixture value is outside signed i64")
            payload.extend(value.to_bytes(8, "little", signed=True))
    write_new(path, bytes(payload))


def invoke(command: list[str], success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if success and result.returncode != 0:
        raise AssertionError(
            f"unexpected failure {result.returncode}: {command}\n{result.stdout}\n{result.stderr}"
        )
    if not success and result.returncode == 0:
        raise AssertionError(f"command unexpectedly succeeded: {command}")
    return result


def determinant_3(rows: list[list[int]]) -> int:
    (a, b, c), (d, e, f), (g, h, i) = rows
    return a * (e * i - f * h) - b * (d * i - f * g) + c * (d * h - e * g)


def modp_digest(rows: list[list[int]], prime: int) -> str:
    return hashlib.sha256(
        b"".join(struct.pack("<Q", value % prime) for row in rows for value in row)
    ).hexdigest()


def identity_digest(size: int) -> str:
    return hashlib.sha256(
        b"".join(
            struct.pack("<Q", int(row == column))
            for row in range(size)
            for column in range(size)
        )
    ).hexdigest()


def run_square(
    root: Path,
    name: str,
    rows: list[list[int]],
    ranker: Path,
    source: Path,
    wrapper: Path,
    build_source: Path,
    self_source: Path,
) -> tuple[dict[str, Any], Path]:
    case = root / name
    case.mkdir()
    matrix = case / "matrix.i64le"
    write_i64_matrix(matrix, rows)
    output = case / "certificate"
    command = [
        sys.executable,
        str(wrapper),
        "--matrix",
        str(matrix),
        "--dimension",
        str(len(rows)),
        "--encoding",
        "i64le",
        "--ranker",
        str(ranker),
        "--ranker-source",
        str(source),
        "--out-dir",
        str(output),
        "--expected-matrix-sha256",
        sha256_file(matrix),
        "--binding-file",
        f"build_script={build_source}",
        "--binding-file",
        f"self_test_source={self_source}",
    ]
    result = invoke(command)
    if result.stderr:
        raise AssertionError(f"wrapper emitted stderr: {result.stderr}")
    summary = json.loads(result.stdout)
    bundle_path = output / "certificate_bundle.json"
    bundle = json.loads(bundle_path.read_bytes())
    if summary["bundle_sha256"] != sha256_file(bundle_path):
        raise AssertionError("bundle stdout hash mismatch")
    if (output / "certificate_bundle.json.sha256").read_text().split()[0] != summary[
        "bundle_sha256"
    ]:
        raise AssertionError("detached bundle hash mismatch")
    return bundle, matrix


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ranker", required=True, type=Path)
    parser.add_argument("--ranker-source", required=True, type=Path)
    parser.add_argument("--square-wrapper", required=True, type=Path)
    parser.add_argument("--build-source", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    arguments = parser.parse_args()

    ranker = arguments.ranker.resolve(strict=True)
    source = arguments.ranker_source.resolve(strict=True)
    wrapper = arguments.square_wrapper.resolve(strict=True)
    build_source = arguments.build_source.resolve(strict=True)
    self_source = Path(__file__).resolve(strict=True)
    root = arguments.out_dir.resolve()
    root.mkdir(parents=True, exist_ok=False)

    full_rows = [
        [I64_MIN, (1 << 62) + 7, -5],
        [-(1 << 61), I64_MAX, 13],
        [17, -19, 23],
    ]
    full_bundle, full_matrix = run_square(
        root, "full_rank", full_rows, ranker, source, wrapper, build_source, self_source
    )
    if full_bundle["q_full_rank_certified_by_nonzero_modular_determinant"] is not True:
        raise AssertionError("nonsingular fixture did not certify rational full rank")
    if full_bundle["all_two_fixed_primes_full_rank"] is not True:
        raise AssertionError("nonsingular fixture did not pass both fixed primes")
    exact_det = determinant_3(full_rows)
    for prime in PRIMES:
        receipt = json.loads(
            (root / "full_rank" / "certificate" / f"rank_mod_{prime}.json").read_bytes()
        )
        if exact_det % prime == 0:
            raise AssertionError("bad fixture: determinant vanishes at a fixed prime")
        if receipt["determinant_mod_prime"] != exact_det % prime:
            raise AssertionError(f"determinant mismatch modulo {prime}")
        if receipt["rank_mod_prime"] != 3 or receipt["rref_identity"] is not True:
            raise AssertionError(f"full-rank receipt mismatch modulo {prime}")
        if receipt["selected_raw_cells_sha256"] != sha256_file(full_matrix):
            raise AssertionError("raw signed-i64 digest mismatch")
        if receipt["selected_modp_u64le_sha256"] != modp_digest(full_rows, prime):
            raise AssertionError(f"signed reduction mismatch modulo {prime}")
        if receipt["rref_modp_u64le_sha256"] != identity_digest(3):
            raise AssertionError(f"RREF identity digest mismatch modulo {prime}")
        if receipt["selected_sign_counts"] != {"negative": 4, "zero": 0, "positive": 5}:
            raise AssertionError("signed-value census mismatch")

    singular_rows = [[2, -3, 5], [7, 11, -13], [9, 8, -8]]
    if singular_rows[2] != [
        singular_rows[0][column] + singular_rows[1][column] for column in range(3)
    ]:
        raise AssertionError("singular fixture construction drift")
    singular_bundle, _ = run_square(
        root, "singular", singular_rows, ranker, source, wrapper, build_source, self_source
    )
    if singular_bundle["q_full_rank_certified_by_nonzero_modular_determinant"] is not False:
        raise AssertionError("singular fixture was incorrectly certified")
    for prime in PRIMES:
        receipt = json.loads(
            (root / "singular" / "certificate" / f"rank_mod_{prime}.json").read_bytes()
        )
        if receipt["determinant_mod_prime"] != 0 or receipt["rank_mod_prime"] != 2:
            raise AssertionError(f"singular receipt mismatch modulo {prime}")

    failures = root / "failure_modes"
    failures.mkdir()
    truncated = failures / "truncated.i64le"
    write_new(truncated, full_matrix.read_bytes()[:-1])
    bad_size = invoke(
        [
            sys.executable,
            str(wrapper),
            "--matrix",
            str(truncated),
            "--dimension",
            "3",
            "--ranker",
            str(ranker),
            "--ranker-source",
            str(source),
            "--out-dir",
            str(failures / "bad_size"),
        ],
        success=False,
    )
    if "matrix size mismatch" not in bad_size.stderr:
        raise AssertionError("truncated matrix failed for the wrong reason")

    direct_prefix = [str(ranker), str(full_matrix), "i64le", "3", "3", "0", "3", "-"]
    composite = invoke(
        direct_prefix + ["1000000", str(failures / "composite.json")], success=False
    )
    if "modulus is not prime" not in composite.stderr:
        raise AssertionError("composite modulus failed for the wrong reason")
    wrong_prime = invoke(
        direct_prefix + ["1000037", str(failures / "wrong_prime.json")], success=False
    )
    if "permits only primes" not in wrong_prime.stderr:
        raise AssertionError("unregistered prime failed for the wrong reason")
    existing = root / "full_rank" / "certificate" / f"rank_mod_{PRIMES[0]}.json"
    overwrite = invoke(direct_prefix + [str(PRIMES[0]), str(existing)], success=False)
    if "refusing to overwrite" not in overwrite.stderr:
        raise AssertionError("overwrite attempt failed for the wrong reason")

    artifacts: dict[str, dict[str, Any]] = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            relative = str(path.relative_to(root))
            artifacts[relative] = {"bytes": path.stat().st_size, "sha256": sha256_file(path)}
    report = {
        "schema": "g0179.direct-square-rank-certificate-self-test.v1",
        "status": "PASS",
        "assertions": [
            "signed-i64 minimum, maximum, and large mixed signs reduced exactly at both fixed primes",
            "Python integer determinant agreed with FLINT at both fixed primes",
            "nonsingular and singular fixtures followed the correct proof branches",
            "raw, modular, and identity-RREF digests agreed with independent Python computations",
            "truncated input, composite modulus, unregistered prime, and overwrite were rejected",
        ],
        "sources": {
            "ranker": {"path": str(ranker), "sha256": sha256_file(ranker)},
            "ranker_source": {"path": str(source), "sha256": sha256_file(source)},
            "square_wrapper": {"path": str(wrapper), "sha256": sha256_file(wrapper)},
            "build_source": {"path": str(build_source), "sha256": sha256_file(build_source)},
            "self_test": {"path": str(self_source), "sha256": sha256_file(self_source)},
        },
        "artifacts_before_report": artifacts,
    }
    report_path = root / "selftest_report.json"
    write_new(report_path, canonical_json(report))
    report_sha = sha256_file(report_path)
    write_new(root / "selftest_report.json.sha256", f"{report_sha}  {report_path.name}\n".encode())
    print(json.dumps({"status": "PASS", "report": str(report_path), "report_sha256": report_sha}, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"self_test: {error}", file=sys.stderr)
        raise SystemExit(1)
