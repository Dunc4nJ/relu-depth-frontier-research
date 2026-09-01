#!/usr/bin/env python3
"""Deterministically lift the four canonical modular left-kernel bases."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path

import numpy as np


ROWS = 5769
COLS = 6795
NULLITY = 478
EXCLUDED_SEQUENCES = {1548, 3140, 4259, 5656}
PRIMES = (1000003, 1000033, 1000099, 1000037)
EXPECTED = {
    "matrix": (313602840, "d57ec8abb9a843dc68327d88d0fe9c5843a055762cd3ae9f53ac45fb9eb50efd"),
    "diagnostics": (134056, "95eb3e24cb6b867c99e310bdbed40c2f4c6087e71d2867b4d441b677d9d7b69f"),
    "kernel_1000003": (11030328, "ee927f0fc50017cd79738864a95d2e6470f9215befce6b9dddd57ca2dddae0a1"),
    "kernel_1000033": (11030328, "d9aed91e2bcffdc5b327d9246c07105df5e3f3f824163b7bda59f6ac8225933b"),
    "kernel_1000099": (11030328, "9a64469b4e440976409d4ca89f45ab5cf336f0f44b40ff13757762efce155481"),
    "kernel_1000037": (11030328, "f9b27149a7119e1fec6abc51529c8709005264267c49863e33c89f151307a0a2"),
}


def sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def pin(name: str, path: Path) -> dict[str, object]:
    size = path.stat().st_size
    digest = sha256_path(path)
    expected_size, expected_digest = EXPECTED[name]
    if (size, digest) != (expected_size, expected_digest):
        raise RuntimeError(f"{name} custody drift: {(size, digest)}")
    return {"path": str(path.resolve()), "bytes": size, "sha256": digest}


def rational_reconstruct(residues: list[int], mod_steps: list[tuple[int, int, int]], modulus: int, bound: int) -> tuple[int, int]:
    residue = 0
    for value, (prior_modulus, prime, inverse) in zip(residues, mod_steps, strict=True):
        residue += prior_modulus * (((value - residue) % prime) * inverse % prime)
    r0, r1 = modulus, residue
    t0, t1 = 0, 1
    while r1 > bound:
        quotient = r0 // r1
        r0, r1 = r1, r0 - quotient * r1
        t0, t1 = t1, t0 - quotient * t1
    if t1 == 0 or abs(t1) > bound or math.gcd(r1, t1) != 1:
        raise RuntimeError("rational reconstruction failed its size/coprimality gate")
    if t1 < 0:
        r1, t1 = -r1, -t1
    if abs(r1) > bound or (residue * t1 - r1) % modulus != 0 or math.gcd(t1, modulus) != 1:
        raise RuntimeError("rational reconstruction failed its congruence gate")
    return r1, t1


def compact_histogram(values: list[int]) -> dict[str, int]:
    result: dict[str, int] = {}
    for value in values:
        key = str(value)
        result[key] = result.get(key, 0) + 1
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", type=Path, required=True)
    parser.add_argument("--diagnostics", type=Path, required=True)
    for prime in PRIMES:
        parser.add_argument(f"--kernel-{prime}", dest=f"kernel_{prime}", type=Path, required=True)
    parser.add_argument("--basis-out", type=Path, required=True)
    parser.add_argument("--receipt-out", type=Path, required=True)
    args = parser.parse_args()
    for output in (args.basis_out, args.receipt_out):
        if output.exists():
            raise RuntimeError(f"refusing to overwrite {output}")

    inputs = {
        "matrix": pin("matrix", args.matrix),
        "diagnostics": pin("diagnostics", args.diagnostics),
    }
    kernel_paths = [getattr(args, f"kernel_{prime}") for prime in PRIMES]
    kernels = []
    for prime, path in zip(PRIMES, kernel_paths, strict=True):
        inputs[f"kernel_{prime}"] = pin(f"kernel_{prime}", path)
        kernels.append(np.memmap(path, dtype="<u4", mode="r", shape=(ROWS, NULLITY)))

    reference_support = kernels[0] != 0
    if any(np.any(reference_support != (kernel != 0)) for kernel in kernels[1:]):
        raise RuntimeError("four-prime support-pattern disagreement")

    diagnostics = json.loads(args.diagnostics.read_text())
    dependent_sequences = [item["record_sequence"] for item in diagnostics["dependent_records"]]
    if len(dependent_sequences) != 480 or not {3140, 5656}.issubset(dependent_sequences):
        raise RuntimeError("dependent-record census drift")
    retained_sequences = [sequence for sequence in range(5773) if sequence not in EXCLUDED_SEQUENCES]
    sequence_to_row = {sequence: row for row, sequence in enumerate(retained_sequences)}
    free_sequences = [sequence for sequence in dependent_sequences if sequence not in {3140, 5656}]
    free_rows = [sequence_to_row[sequence] for sequence in free_sequences]
    if free_rows != sorted(free_rows) or len(free_rows) != NULLITY:
        raise RuntimeError("free-row order drift")
    identity = np.eye(NULLITY, dtype=np.uint32)
    if any(not np.array_equal(kernel[free_rows, :], identity) for kernel in kernels):
        raise RuntimeError("canonical free-coordinate identity failed")

    modulus = math.prod(PRIMES)
    bound = math.isqrt(modulus // 2)
    if not 2 * bound * bound < modulus:
        raise RuntimeError("uniqueness inequality failed")
    mod_steps = []
    prior_modulus = 1
    for prime in PRIMES:
        mod_steps.append((prior_modulus, prime, pow(prior_modulus, -1, prime)))
        prior_modulus *= prime

    header = {
        "schema": "g0189.exact-primitive-left-kernel-basis.v1",
        "matrix_shape": [ROWS, COLS],
        "basis_shape": [ROWS, NULLITY],
        "primes": list(PRIMES),
        "crt_modulus": str(modulus),
        "rational_reconstruction_bound": bound,
        "excluded_record_sequences": sorted(EXCLUDED_SEQUENCES),
        "free_rows": free_rows,
        "free_record_sequences": free_sequences,
        "term_encoding": "[output_row, record_sequence, primitive_integer_coefficient_as_decimal_string]",
    }
    lines = [json.dumps(header, sort_keys=True, separators=(",", ":"))]
    supports: list[int] = []
    free_coefficients: list[int] = []
    maximum_reconstructed_numerator = 0
    maximum_reconstructed_denominator = 0
    maximum_primitive_coefficient = 0
    maximum_sum_abs = 0
    total_nonzero = 0

    for column in range(NULLITY):
        rows = np.flatnonzero(reference_support[:, column]).tolist()
        rationals: list[tuple[int, int]] = []
        for row in rows:
            numerator, denominator = rational_reconstruct(
                [int(kernel[row, column]) for kernel in kernels], mod_steps, modulus, bound
            )
            maximum_reconstructed_numerator = max(maximum_reconstructed_numerator, abs(numerator))
            maximum_reconstructed_denominator = max(maximum_reconstructed_denominator, denominator)
            rationals.append((numerator, denominator))
        common_denominator = 1
        for _, denominator in rationals:
            common_denominator = math.lcm(common_denominator, denominator)
        coefficients = [numerator * (common_denominator // denominator) for numerator, denominator in rationals]
        primitive_gcd = 0
        for coefficient in coefficients:
            primitive_gcd = math.gcd(primitive_gcd, abs(coefficient))
        if primitive_gcd == 0:
            raise RuntimeError("zero reconstructed relation")
        coefficients = [coefficient // primitive_gcd for coefficient in coefficients]
        primitive_free_coefficient = common_denominator // primitive_gcd
        if rows.count(free_rows[column]) != 1:
            raise RuntimeError("free row missing from its basis column")
        free_position = rows.index(free_rows[column])
        if coefficients[free_position] != primitive_free_coefficient or primitive_free_coefficient <= 0:
            raise RuntimeError("primitive free-coordinate normalization drift")
        if math.gcd(*[abs(coefficient) for coefficient in coefficients]) != 1:
            raise RuntimeError("relation is not primitive")
        dense = np.zeros(ROWS, dtype=np.int64)
        dense[rows] = np.asarray(coefficients, dtype=np.int64)
        for prime, kernel in zip(PRIMES, kernels, strict=True):
            expected_column = (np.asarray(kernel[:, column], dtype=np.uint64) * (primitive_free_coefficient % prime)) % prime
            if not np.array_equal(np.mod(dense, prime).astype(np.uint64), expected_column):
                raise RuntimeError(f"primitive relation does not reduce to canonical basis at {prime}, column {column}")

        support = len(rows)
        sum_abs = sum(abs(coefficient) for coefficient in coefficients)
        maximum = max(abs(coefficient) for coefficient in coefficients)
        supports.append(support)
        free_coefficients.append(primitive_free_coefficient)
        maximum_primitive_coefficient = max(maximum_primitive_coefficient, maximum)
        maximum_sum_abs = max(maximum_sum_abs, sum_abs)
        total_nonzero += support
        relation = {
            "basis_column": column,
            "free_row": free_rows[column],
            "free_record_sequence": free_sequences[column],
            "primitive_free_coefficient": str(primitive_free_coefficient),
            "support": support,
            "max_abs_coefficient": str(maximum),
            "sum_abs_coefficients": str(sum_abs),
            "terms": [
                [row, retained_sequences[row], str(coefficient)]
                for row, coefficient in zip(rows, coefficients, strict=True)
            ],
        }
        lines.append(json.dumps(relation, sort_keys=True, separators=(",", ":")))

    payload = ("\n".join(lines) + "\n").encode()
    args.basis_out.write_bytes(payload)
    basis_sha256 = hashlib.sha256(payload).hexdigest()
    sorted_supports = sorted(supports)
    source_path = Path(__file__)
    receipt = {
        "schema": "g0189.four-prime-rational-reconstruction.v1",
        "result": "ALL_478_CANONICAL_LEFT_KERNEL_VECTORS_UNIQUELY_RECONSTRUCTED_AWAITING_INTEGER_MATRIX_REPLAY",
        "inputs": inputs,
        "producer": {
            "path": str(source_path.resolve()),
            "bytes": source_path.stat().st_size,
            "sha256": sha256_path(source_path),
            "python": os.sys.version,
            "numpy": np.__version__,
        },
        "reconstruction": {
            "primes": list(PRIMES),
            "crt_modulus": str(modulus),
            "coefficient_bound": bound,
            "strict_uniqueness_check": f"2*{bound}^2={2 * bound * bound} < M={modulus}",
            "maximum_reconstructed_numerator_abs": maximum_reconstructed_numerator,
            "maximum_reconstructed_denominator": maximum_reconstructed_denominator,
            "all_denominators_coprime_to_modulus": True,
            "all_four_support_patterns_identical": True,
            "all_478_free_coordinate_blocks_identity": True,
            "all_478_primitive_vectors_reduce_to_each_modular_basis": True,
        },
        "basis": {
            "path": str(args.basis_out.resolve()),
            "bytes": len(payload),
            "sha256": basis_sha256,
            "shape": [ROWS, NULLITY],
            "nonzero_coefficients": total_nonzero,
            "support_min": sorted_supports[0],
            "support_median_lower": sorted_supports[(NULLITY - 1) // 2],
            "support_median_upper": sorted_supports[NULLITY // 2],
            "support_max": sorted_supports[-1],
            "support_histogram": compact_histogram(supports),
            "primitive_free_coefficient_histogram": compact_histogram(free_coefficients),
            "maximum_primitive_coefficient_abs": maximum_primitive_coefficient,
            "maximum_sum_abs_coefficients": maximum_sum_abs,
            "independence_certificate": "The 478x478 submatrix on the listed free rows is diagonal with the nonzero primitive_free_coefficient entries.",
        },
        "claim_boundary": "This receipt uniquely reconstructs and serializes 478 independent rational candidates from four modular bases. Exact annihilation of the integer matrix and the resulting characteristic-zero rank require the separate exact replay receipt.",
    }
    args.receipt_out.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    main()
