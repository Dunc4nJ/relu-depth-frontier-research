#!/usr/bin/env python3
"""Lift the frozen G-0054 two-prime S0 kernel to an exact-Q certificate.

The 598 modular nullspace vectors have identical sparse supports at both
primes.  This program combines their coefficients by CRT, performs unique
rational reconstruction, clears denominators, and replays every resulting
integer relation on the complete 99,858-row degree-four hinge universe and on
the normalized lambda functional.  A common nonzero 867-square modular minor
then supplies the exact rank lower bound.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
from math import gcd, isqrt, lcm
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Any, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0054_DIR = ROOT / "artifacts/math/G-0054"
G0054_SCRIPT = G0054_DIR / "s0_union_rank_gate.py"
G0054_REPORT = G0054_DIR / "s0_union_rank_gate_v1.json.gz"
DEFAULT_OUTPUT = HERE / "exact_s0_kernel_lift_v1.json.gz"

EXPECTED_G0054_SCRIPT_SHA256 = (
    "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2"
)
EXPECTED_G0054_REPORT_SHA256 = (
    "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053"
)
EXPECTED_G0054_PAYLOAD_SHA256 = (
    "a7a8082393ef709b6ffe372f142688e3ff47182e11967a0a97cb5698fa772f71"
)
EXPECTED_UNIVERSE_SHA256 = (
    "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
)
EXPECTED_DESCRIPTOR_SHA256 = (
    "c0e49bda15e0ed17b821ba5a20bc0088a4aeab9ba5ab36da2ed63ac30843053e"
)
EXPECTED_STREAM_SHA256 = (
    "2d56d040cb7567dd0c5f86c53a0472ba559d80d90818436b2c7008c1bb5bcf72"
)
EXPECTED_UNION_ROW_INDICES_SHA256 = (
    "511c40767d44d3309bd5901caa188cb04ef3c2babe096efcdc2b4458c268c423"
)
EXPECTED_MATRIX_SHA256 = (
    "a5002c64af1307dfa289e43b39d6faaca75e97c0a3e4cdb14a949b721109cb8c"
)
EXPECTED_PIVOT_ROWS_SHA256 = (
    "9c3ec7192348b938f4ce241d9042ed06c8fc2303bc2b4bf3b6bf8e98a3a4beb1"
)
EXPECTED_PIVOT_COLUMNS_SHA256 = (
    "fed7aeab65a3b641ffbaceb401779e1293b1988024bc9f71366740ba4b4f4804"
)
PRIMES = (1_000_003, 1_000_033)
EXPECTED_ROWS = 99_858
EXPECTED_COLUMNS = 1_465
EXPECTED_RANK = 867
EXPECTED_NULLITY = 598
EXPECTED_COEFFICIENTS = 7_764
EXPECTED_MAX_MATRIX_ENTRY = 774_144
EXPECTED_LAMBDA_GCD = 79_833_600
SCHEMA = "max11-g0056-exact-s0-kernel-lift-v1"


class LiftError(RuntimeError):
    """Fail-closed exact-lift error."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise LiftError(f"expected JSON object in {path}")
    return value


def load_g0054() -> ModuleType:
    if sha256_path(G0054_SCRIPT) != EXPECTED_G0054_SCRIPT_SHA256:
        raise LiftError("G-0054 script hash drift")
    if sha256_path(G0054_REPORT) != EXPECTED_G0054_REPORT_SHA256:
        raise LiftError("G-0054 report hash drift")
    spec = importlib.util.spec_from_file_location("g0056_frozen_g0054", G0054_SCRIPT)
    if spec is None or spec.loader is None:
        raise LiftError("cannot import frozen G-0054 program")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def verify_report_payload(report: dict[str, object], g0054: ModuleType) -> None:
    observed = report.get("canonical_payload_sha256")
    if observed != EXPECTED_G0054_PAYLOAD_SHA256:
        raise LiftError(f"G-0054 canonical payload drift: {observed}")
    payload = dict(report)
    payload.pop("canonical_payload_sha256", None)
    if g0054.canonical_sha256(payload) != observed:
        raise LiftError("G-0054 canonical payload does not replay")


def memory_available_bytes() -> int:
    with Path("/proc/meminfo").open("rt", encoding="ascii") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise LiftError("cannot read MemAvailable")


def crt_pair(a: int, p: int, b: int, q: int) -> int:
    """Return the unique residue modulo p*q matching a mod p and b mod q."""
    if gcd(p, q) != 1:
        raise LiftError("CRT moduli are not coprime")
    return (a + p * (((b - a) * pow(p, -1, q)) % q)) % (p * q)


def rational_reconstruct(residue: int, modulus: int, bound: int) -> Fraction:
    """Uniquely reconstruct a/b with |a|, b <= bound and b positive."""
    residue %= modulus
    old_r, r = modulus, residue
    old_t, t = 0, 1
    while abs(r) > bound:
        quotient = old_r // r
        old_r, r = r, old_r - quotient * r
        old_t, t = t, old_t - quotient * t
    numerator, denominator = r, t
    if denominator < 0:
        numerator, denominator = -numerator, -denominator
    common = gcd(abs(numerator), denominator)
    numerator //= common
    denominator //= common
    if not (
        abs(numerator) <= bound
        and 1 <= denominator <= bound
        and gcd(denominator, modulus) == 1
        and (denominator * residue - numerator) % modulus == 0
    ):
        raise LiftError(f"rational reconstruction failed for residue {residue}")
    return Fraction(numerator, denominator)


def fraction_string(value: Fraction) -> str:
    return (
        str(value.numerator)
        if value.denominator == 1
        else f"{value.numerator}/{value.denominator}"
    )


def frozen_modular_data(
    report: dict[str, object], g0054: ModuleType
) -> tuple[list[int], list[int], list[list[dict[str, object]]]]:
    modular = report.get("modular_results")
    if not isinstance(modular, list) or len(modular) != 2:
        raise LiftError("G-0054 modular result census drift")
    if [int(item["prime"]) for item in modular] != list(PRIMES):
        raise LiftError("G-0054 prime order drift")
    if [int(item["complete_hinge_rank"]) for item in modular] != [
        EXPECTED_RANK,
        EXPECTED_RANK,
    ]:
        raise LiftError("G-0054 rank drift")
    if [int(item["augmented_rank_gain"]) for item in modular] != [0, 0]:
        raise LiftError("G-0054 augmented-rank drift")

    lower = [item["rank_lower_certificate"] for item in modular]
    pivot_rows = [int(value) for value in lower[0]["pivot_labeled_rows"]]
    pivot_columns = [int(value) for value in lower[0]["pivot_columns"]]
    if lower[1]["pivot_labeled_rows"] != pivot_rows:
        raise LiftError("pivot rows differ across primes")
    if lower[1]["pivot_columns"] != pivot_columns:
        raise LiftError("pivot columns differ across primes")
    if len(pivot_rows) != EXPECTED_RANK or len(pivot_columns) != EXPECTED_RANK:
        raise LiftError("pivot size drift")
    if g0054.canonical_sha256(pivot_rows) != EXPECTED_PIVOT_ROWS_SHA256:
        raise LiftError("pivot row hash drift")
    if g0054.canonical_sha256(pivot_columns) != EXPECTED_PIVOT_COLUMNS_SHA256:
        raise LiftError("pivot column hash drift")

    upper = [item["rank_upper_certificate"] for item in modular]
    bases = [item["basis_columns"] for item in upper]
    if [int(item["nullity"]) for item in upper] != [
        EXPECTED_NULLITY,
        EXPECTED_NULLITY,
    ]:
        raise LiftError("nullity drift")
    if len(bases[0]) != EXPECTED_NULLITY or len(bases[1]) != EXPECTED_NULLITY:
        raise LiftError("nullspace basis census drift")
    return pivot_rows, pivot_columns, bases


def self_test() -> dict[str, object]:
    modulus = PRIMES[0] * PRIMES[1]
    bound = isqrt(modulus // 2)
    probes = [Fraction(1, 2), Fraction(-1, 2), Fraction(13, 4), Fraction(-13, 4)]
    for expected in probes:
        residue = (
            expected.numerator * pow(expected.denominator, -1, modulus)
        ) % modulus
        if rational_reconstruct(residue, modulus, bound) != expected:
            raise AssertionError(f"rational reconstruction control failed: {expected}")

    columns = [
        (np.array([0, 2], dtype=np.uint32), np.array([1, 2], dtype=np.int64)),
        (np.array([1, 2], dtype=np.uint32), np.array([1, 3], dtype=np.int64)),
        (np.array([0, 1, 2], dtype=np.uint32), np.array([1, 1, 5], dtype=np.int64)),
    ]
    coefficients = (-1, -1, 1)
    residual = np.zeros(3, dtype=np.int64)
    for coefficient, (rows, values) in zip(coefficients, columns, strict=True):
        residual[rows] += coefficient * values
    if np.any(residual):
        raise AssertionError("exact sparse replay positive control failed")
    mutant = residual.copy()
    rows, values = columns[0]
    mutant[rows] += values
    if not np.any(mutant):
        raise AssertionError("exact sparse replay mutation control failed")
    return {
        "crt_rational_reconstruction_known_answers": True,
        "exact_sparse_relation_positive_control": True,
        "coefficient_plus_one_mutation_rejected": True,
    }


def preflight() -> dict[str, object]:
    started = time.perf_counter()
    g0054 = load_g0054()
    report = load_json_gz(G0054_REPORT)
    verify_report_payload(report, g0054)
    pivot_rows, pivot_columns, bases = frozen_modular_data(report, g0054)
    supports_match = all(
        left["support_zero_based_columns"] == right["support_zero_based_columns"]
        for left, right in zip(bases[0], bases[1], strict=True)
    )
    coefficient_count = sum(
        len(item["support_zero_based_columns"]) for item in bases[0]
    )
    if not supports_match or coefficient_count != EXPECTED_COEFFICIENTS:
        raise LiftError("two-prime sparse support census drift")
    return {
        "result": "PASS",
        "g0054_script_sha256": sha256_path(G0054_SCRIPT),
        "g0054_report_sha256": sha256_path(G0054_REPORT),
        "g0054_payload_sha256": report["canonical_payload_sha256"],
        "pivot_rows": len(pivot_rows),
        "pivot_columns": len(pivot_columns),
        "nullspace_vectors": len(bases[0]),
        "sparse_coefficients": coefficient_count,
        "supports_identical_across_primes": supports_match,
        "memory_available_bytes": memory_available_bytes(),
        "seconds": time.perf_counter() - started,
    }


def lift_relations(
    bases: list[list[dict[str, object]]], pivot_columns: list[int]
) -> tuple[list[dict[str, object]], dict[str, object]]:
    modulus = PRIMES[0] * PRIMES[1]
    bound = isqrt(modulus // 2)
    if not 2 * bound * bound < modulus:
        raise LiftError("global rational reconstruction uniqueness inequality failed")
    pivot_set = set(pivot_columns)
    nonpivot_columns = [
        column for column in range(EXPECTED_COLUMNS) if column not in pivot_set
    ]
    if len(nonpivot_columns) != EXPECTED_NULLITY:
        raise LiftError("nonpivot column census drift")

    numerator_histogram: Counter[int] = Counter()
    denominator_histogram: Counter[int] = Counter()
    support_histogram: Counter[int] = Counter()
    cleared_lcm_histogram: Counter[int] = Counter()
    lifted: list[dict[str, object]] = []
    maximum_numerator = 0
    maximum_denominator = 0
    maximum_cleared_integer = 0
    total_coefficients = 0

    for basis_index, (left, right) in enumerate(
        zip(bases[0], bases[1], strict=True)
    ):
        support = [int(value) for value in left["support_zero_based_columns"]]
        if right["support_zero_based_columns"] != support:
            raise LiftError(f"support mismatch at null vector {basis_index}")
        coefficients_left = [int(value) for value in left["coefficients"]]
        coefficients_right = [int(value) for value in right["coefficients"]]
        if not (len(support) == len(coefficients_left) == len(coefficients_right)):
            raise LiftError(f"coefficient census mismatch at null vector {basis_index}")
        distinguished = nonpivot_columns[basis_index]
        if [column for column in support if column not in pivot_set] != [distinguished]:
            raise LiftError(f"nonpivot normalization drift at null vector {basis_index}")

        rationals = []
        for residue_left, residue_right in zip(
            coefficients_left, coefficients_right, strict=True
        ):
            residue = crt_pair(
                residue_left, PRIMES[0], residue_right, PRIMES[1]
            )
            value = rational_reconstruct(residue, modulus, bound)
            if value.numerator * pow(value.denominator, -1, PRIMES[0]) % PRIMES[0] != residue_left:
                raise LiftError(f"prime-one roundtrip failed at null vector {basis_index}")
            if value.numerator * pow(value.denominator, -1, PRIMES[1]) % PRIMES[1] != residue_right:
                raise LiftError(f"prime-two roundtrip failed at null vector {basis_index}")
            rationals.append(value)
            numerator_histogram[value.numerator] += 1
            denominator_histogram[value.denominator] += 1
            maximum_numerator = max(maximum_numerator, abs(value.numerator))
            maximum_denominator = max(maximum_denominator, value.denominator)
        distinguished_local = support.index(distinguished)
        if rationals[distinguished_local] != 1:
            raise LiftError(f"distinguished coefficient is not one at {basis_index}")
        denominator_lcm = 1
        for value in rationals:
            denominator_lcm = lcm(denominator_lcm, value.denominator)
        integers = [
            value.numerator * (denominator_lcm // value.denominator)
            for value in rationals
        ]
        for prime, modular_coefficients in zip(PRIMES, (coefficients_left, coefficients_right), strict=True):
            if [value % prime for value in integers] != [
                denominator_lcm * value % prime for value in modular_coefficients
            ]:
                raise LiftError(f"cleared-integer modular roundtrip failed at {basis_index}")
        maximum_cleared_integer = max(
            maximum_cleared_integer, max(map(abs, integers))
        )
        support_histogram[len(support)] += 1
        cleared_lcm_histogram[denominator_lcm] += 1
        total_coefficients += len(support)
        lifted.append(
            {
                "basis_index": basis_index,
                "distinguished_nonpivot_column": distinguished,
                "support_zero_based_columns": support,
                "rational_coefficients": [fraction_string(value) for value in rationals],
                "denominator_lcm": denominator_lcm,
                "cleared_integer_coefficients": integers,
            }
        )
    if total_coefficients != EXPECTED_COEFFICIENTS:
        raise LiftError(f"lifted coefficient census drift: {total_coefficients}")
    return lifted, {
        "crt_modulus": modulus,
        "global_numerator_denominator_bound": bound,
        "strict_uniqueness_inequality": f"2*{bound}^2 < {modulus}",
        "all_coefficients_reconstructed_uniquely": True,
        "total_coefficients": total_coefficients,
        "maximum_absolute_numerator": maximum_numerator,
        "maximum_denominator": maximum_denominator,
        "maximum_absolute_cleared_integer_coefficient": maximum_cleared_integer,
        "numerator_histogram": {
            str(key): value for key, value in sorted(numerator_histogram.items())
        },
        "denominator_histogram": {
            str(key): value for key, value in sorted(denominator_histogram.items())
        },
        "support_size_histogram": {
            str(key): value for key, value in sorted(support_histogram.items())
        },
        "cleared_denominator_lcm_histogram": {
            str(key): value for key, value in sorted(cleared_lcm_histogram.items())
        },
        "lifted_relations_sha256": canonical_sha256(lifted),
    }


def replay_relations(
    lifted: list[dict[str, object]],
    semantic_columns: list[dict[str, object]],
    lambda_row: np.ndarray,
    universe: tuple[tuple[int, ...], ...],
) -> tuple[dict[str, object], dict[str, object]]:
    maximum_entry = max(
        abs(int(value))
        for column in semantic_columns
        for value in column["values"]
    )
    if maximum_entry != EXPECTED_MAX_MATRIX_ENTRY:
        raise LiftError(f"maximum hinge entry drift: {maximum_entry}")
    normalized_lambda = lambda_row // EXPECTED_LAMBDA_GCD
    if not np.array_equal(
        normalized_lambda * EXPECTED_LAMBDA_GCD, lambda_row
    ):
        raise LiftError("lambda normalization is not exact")
    maximum_normalized_lambda = int(np.max(np.abs(normalized_lambda)))

    max_support = max(len(item["support_zero_based_columns"]) for item in lifted)
    max_integer = max(
        abs(value)
        for item in lifted
        for value in item["cleared_integer_coefficients"]
    )
    modulus = PRIMES[0] * PRIMES[1]
    hinge_height_bound = max_support * max_integer * maximum_entry
    lambda_height_bound = max_support * max_integer * maximum_normalized_lambda
    if not hinge_height_bound < modulus or not lambda_height_bound < modulus:
        raise LiftError("deterministic CRT height bound is not strict")

    maximum_observed_intermediate = 0
    replayed_nonzero_terms = 0
    for relation_index, relation in enumerate(lifted):
        residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
        for column, coefficient in zip(
            relation["support_zero_based_columns"],
            relation["cleared_integer_coefficients"],
            strict=True,
        ):
            semantic = semantic_columns[column]
            rows = semantic["rows"]
            values = semantic["values"]
            residual[rows] += int(coefficient) * values
            replayed_nonzero_terms += len(rows)
            if len(rows):
                maximum_observed_intermediate = max(
                    maximum_observed_intermediate,
                    int(np.max(np.abs(residual[rows]))),
                )
        bad = np.flatnonzero(residual)
        if len(bad):
            row = int(bad[0])
            raise LiftError(
                f"exact 99,858-row replay failed at relation {relation_index}, "
                f"row {row}, direction {universe[row]}, residual {int(residual[row])}"
            )
        lambda_residual = sum(
            int(coefficient) * int(normalized_lambda[column])
            for column, coefficient in zip(
                relation["support_zero_based_columns"],
                relation["cleared_integer_coefficients"],
                strict=True,
            )
        )
        if lambda_residual:
            raise LiftError(
                f"exact normalized-lambda replay failed at relation {relation_index}: "
                f"{lambda_residual}"
            )
        if (relation_index + 1) % 50 == 0 or relation_index + 1 == len(lifted):
            print(
                f"G0056_REPLAY relations={relation_index + 1}/{len(lifted)}",
                file=sys.stderr,
                flush=True,
            )

    first = lifted[0]
    mutant_residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
    mutant_coefficients = list(first["cleared_integer_coefficients"])
    mutant_coefficients[0] += 1
    for column, coefficient in zip(
        first["support_zero_based_columns"], mutant_coefficients, strict=True
    ):
        semantic = semantic_columns[column]
        mutant_residual[semantic["rows"]] += int(coefficient) * semantic["values"]
    mutant_bad = np.flatnonzero(mutant_residual)
    if not len(mutant_bad):
        raise LiftError("real coefficient +1 mutation was not rejected")
    mutant_row = int(mutant_bad[0])
    return {
        "relations_replayed": len(lifted),
        "complete_degree4_rows_per_relation": EXPECTED_ROWS,
        "all_exact_integer_hinge_residuals_zero": True,
        "all_exact_normalized_lambda_residuals_zero": True,
        "replayed_sparse_nonzero_terms": replayed_nonzero_terms,
        "maximum_observed_absolute_intermediate": maximum_observed_intermediate,
    }, {
        "crt_modulus": modulus,
        "maximum_support_size": max_support,
        "maximum_absolute_integer_coefficient": max_integer,
        "maximum_absolute_hinge_entry": maximum_entry,
        "maximum_absolute_normalized_lambda_entry": maximum_normalized_lambda,
        "uniform_hinge_residual_height_bound": hinge_height_bound,
        "uniform_normalized_lambda_residual_height_bound": lambda_height_bound,
        "both_uniform_bounds_strictly_below_crt_modulus": True,
        "height_argument_proves_two-prime_zeros_are_integer_zeros": True,
        "coefficient_plus_one_mutation": {
            "relation_index": 0,
            "support_local_index": 0,
            "rejected": True,
            "first_nonzero_complete_row": mutant_row,
            "first_nonzero_direction": list(universe[mutant_row]),
            "residual_value": int(mutant_residual[mutant_row]),
        },
    }


def run(workers: int, minimum_available_gib: float) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    ready = preflight()
    if memory_available_bytes() < int(minimum_available_gib * (1 << 30)):
        raise LiftError("available memory below launch guard")
    g0054 = load_g0054()
    g0054_report = load_json_gz(G0054_REPORT)
    verify_report_payload(g0054_report, g0054)
    pivot_rows, pivot_columns, bases = frozen_modular_data(g0054_report, g0054)

    lift_started = time.perf_counter()
    lifted, reconstruction = lift_relations(bases, pivot_columns)
    lift_seconds = time.perf_counter() - lift_started

    semantic_started = time.perf_counter()
    universe = g0054.direction_universe()
    universe_hash = g0054.canonical_sha256([list(value) for value in universe])
    if universe_hash != EXPECTED_UNIVERSE_SHA256:
        raise LiftError("complete row universe hash drift")
    g0054.ROW_INDEX = {direction: row for row, direction in enumerate(universe)}
    _header, records, descriptor_hash = g0054.read_records()
    if descriptor_hash != EXPECTED_DESCRIPTOR_SHA256:
        raise LiftError("descriptor hash drift")
    semantic_columns = g0054.generate_pass(records, workers, "EXACT_LIFT")
    stream_hash = g0054.sparse_stream_hash(semantic_columns)
    if stream_hash != EXPECTED_STREAM_SHA256:
        raise LiftError("semantic stream hash drift")
    union_rows, matrix, lambda_row, union_metadata = g0054.build_union_matrix(
        universe, semantic_columns
    )
    if union_metadata["union_row_indices_sha256"] != EXPECTED_UNION_ROW_INDICES_SHA256:
        raise LiftError("union-row hash drift")
    if union_metadata["matrix_sha256"] != EXPECTED_MATRIX_SHA256:
        raise LiftError("union matrix hash drift")
    semantic_seconds = time.perf_counter() - semantic_started

    pivot_local_lookup = {int(row): local for local, row in enumerate(union_rows)}
    try:
        pivot_local_rows = [pivot_local_lookup[row] for row in pivot_rows]
    except KeyError as error:
        raise LiftError(f"pivot row is outside exact union: {error}") from error
    minor_array = matrix[np.ix_(pivot_local_rows, pivot_columns)]
    determinant_residues = {}
    modular_minor_hashes = {}
    for prime, modular_result in zip(PRIMES, g0054_report["modular_results"], strict=True):
        determinant = int(g0054.to_nmod(minor_array, prime).det()) % prime
        expected_determinant = int(
            modular_result["rank_lower_certificate"]["minor_determinant_mod_prime"]
        )
        if not determinant or determinant != expected_determinant:
            raise LiftError(f"pivot minor determinant drift modulo {prime}")
        determinant_residues[str(prime)] = determinant
        observed_hash = g0054.hash_modular_matrix(
            minor_array, prime, "max11-g0054-rank-minor-v1"
        )
        expected_hash = modular_result["rank_lower_certificate"][
            "minor_matrix_sha256"
        ]
        if observed_hash != expected_hash:
            raise LiftError(f"pivot minor matrix hash drift modulo {prime}")
        modular_minor_hashes[str(prime)] = observed_hash

    replay_started = time.perf_counter()
    replay, height = replay_relations(
        lifted, semantic_columns, lambda_row, universe
    )
    replay_seconds = time.perf_counter() - replay_started

    pivot_set = set(pivot_columns)
    basis_manifest = []
    basis_stream_digest = hashlib.sha256()
    basis_stream_digest.update(b"max11-g0056-ordered-exact-s0-basis-stream-v1\n")
    for basis_index, column in enumerate(pivot_columns):
        record = records[column]
        semantic = semantic_columns[column]
        basis_stream_digest.update(bytes.fromhex(str(semantic["semantic_sha256"])))
        basis_manifest.append(
            {
                "basis_index": basis_index,
                "source_zero_based_column": column,
                "source_sequence": int(record["sequence"]),
                "descriptor": g0054.descriptor(record),
                "lambda": int(lambda_row[column]),
                "semantic_sha256": semantic["semantic_sha256"],
                "support_size": len(semantic["rows"]),
            }
        )
    distinguished = [
        int(item["distinguished_nonpivot_column"]) for item in lifted
    ]
    if sorted(pivot_columns + distinguished) != list(range(EXPECTED_COLUMNS)):
        raise LiftError("basis/nonpivot partition is not complete")
    if len(pivot_set) != EXPECTED_RANK:
        raise LiftError("pivot columns are not unique")

    if sha256_path(Path(__file__)) != script_hash_before:
        raise RuntimeError("G-0056 script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "EXACT_Q_S0_RANK_867_KERNEL_598_ALL_LAMBDA_ZERO",
        "epistemic_status": "COMPUTED_BOUNDED_PENDING_INDEPENDENT_REPLAY",
        "script_sha256": script_hash_before,
        "bindings": {
            "g0054_script_sha256": EXPECTED_G0054_SCRIPT_SHA256,
            "g0054_report_sha256": EXPECTED_G0054_REPORT_SHA256,
            "g0054_payload_sha256": EXPECTED_G0054_PAYLOAD_SHA256,
            "complete_degree4_universe_sha256": EXPECTED_UNIVERSE_SHA256,
            "selected_s0_descriptors_sha256": EXPECTED_DESCRIPTOR_SHA256,
            "ordered_sparse_stream_sha256": EXPECTED_STREAM_SHA256,
            "exact_union_row_indices_sha256": EXPECTED_UNION_ROW_INDICES_SHA256,
            "exact_union_matrix_sha256": EXPECTED_MATRIX_SHA256,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
            "minimum_available_gib": minimum_available_gib,
        },
        "controls": {**controls, "preflight": ready},
        "two_prime_rational_reconstruction": reconstruction,
        "exact_kernel_basis": {
            "relation_count": len(lifted),
            "ambient_column_count": EXPECTED_COLUMNS,
            "pivot_column_count": len(pivot_columns),
            "pivot_columns": pivot_columns,
            "pivot_columns_sha256": g0054.canonical_sha256(pivot_columns),
            "distinguished_nonpivot_columns": distinguished,
            "distinguished_nonpivot_columns_sha256": canonical_sha256(distinguished),
            "each_relation_has_one_distinct_nonpivot_coefficient_equal_to_one": True,
            "relations_are_Q_linearly_independent": True,
            "relations": lifted,
            "relations_sha256": canonical_sha256(lifted),
        },
        "exact_complete_replay": replay,
        "deterministic_height_certificate": height,
        "exact_rank_certificate": {
            "pivot_complete_row_indices": pivot_rows,
            "pivot_complete_rows_sha256": g0054.canonical_sha256(pivot_rows),
            "pivot_columns_sha256": g0054.canonical_sha256(pivot_columns),
            "minor_shape": [EXPECTED_RANK, EXPECTED_RANK],
            "minor_int64_row_major_sha256": g0054.hash_dense_matrix(minor_array),
            "minor_modular_matrix_sha256": modular_minor_hashes,
            "minor_determinant_residues": determinant_residues,
            "nonzero_integer_minor_from_nonzero_modular_determinant": True,
            "rank_Q_lower_bound": EXPECTED_RANK,
            "rank_Q_upper_bound_from_independent_kernel_vectors": (
                EXPECTED_COLUMNS - EXPECTED_NULLITY
            ),
            "exact_rank_Q": EXPECTED_RANK,
        },
        "canonical_exact_s0_basis": {
            "basis_column_count": len(basis_manifest),
            "basis_manifest": basis_manifest,
            "basis_manifest_sha256": canonical_sha256(basis_manifest),
            "ordered_basis_sparse_stream_sha256": basis_stream_digest.hexdigest(),
            "basis_total_nonzeros": sum(
                int(item["support_size"]) for item in basis_manifest
            ),
        },
        "exact_bounded_conclusion": (
            "Over Q, the frozen 1,465 full-core signed-mass-4 hinge matrix has exact "
            "rank 867 and a 598-dimensional kernel. Every vector in that kernel has zero "
            "eleventh binary finite-difference functional. Therefore no hinge-free rational "
            "combination of only these 1,465 seeds can have nonzero MAX11 invariant."
        ),
        "claim_boundary": (
            "This exact statement concerns only the frozen 1,465 full-core signed-mass-4 "
            "orbit columns on the complete 99,858-row degree-four primitive hinge universe. "
            "It omits 132,728 proper-core mass-four columns and all higher signed masses, and "
            "is not an unrestricted two-hidden-layer lower bound for MAX11."
        ),
        "mandatory_next_gate": (
            "Use only the frozen 867-column exact S0 basis in the canonical S1 baseline, "
            "append the separately certified 488-column low-mass proper basis and three old "
            "full seeds, then bind all descriptors, sparse rows, values, lambda entries, and "
            "ordering before any G-0055 discovery columns are tested."
        ),
        "timing": {
            "rational_reconstruction_seconds": lift_seconds,
            "semantic_matrix_reconstruction_seconds": semantic_seconds,
            "exact_complete_replay_seconds": replay_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--minimum-available-gib", type=float, default=12.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1 or args.minimum_available_gib <= 0:
        raise SystemExit("workers and memory guard must be positive")
    if args.self_test:
        print(json.dumps({**self_test(), "result": "PASS"}, sort_keys=True))
        return
    if args.preflight_only:
        print(json.dumps(preflight(), sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.minimum_available_gib)
    write_gzip_atomic(output, report)
    print(json.dumps({"output": str(output), "result": report["result"]}, sort_keys=True))


if __name__ == "__main__":
    main()
