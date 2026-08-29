#!/usr/bin/env python3
"""Exact-Q lift of the frozen 1,358-column G-0057/G-0059 S1 baseline.

G-0059 preserved two free-coordinate-normalized 70-vector nullspace bases at
the primes 1,000,003 and 1,000,033.  This executable CRT-combines every aligned
coefficient, uniquely rationally reconstructs it, clears denominators, and
replays all 70 resulting integer relations on all 99,858 degree-four hinge
rows and on the exact Lambda functional.

A common 1,288-square integer minor that is nonzero modulo the frozen primes
gives rank_Q >= 1,288.  Seventy exact relations with distinct unit free
coordinates give rank_Q <= 1,288.  The claim remains confined to the frozen
finite orbit-column baseline and is not an unrestricted MAX11 lower bound.
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
import subprocess
import sys
import time
from types import ModuleType
from typing import Any, Sequence

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0050_SCRIPT = ROOT / "artifacts/math/G-0050/exact_q_bridge.py"
G0050_REPORT = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"
G0054_SCRIPT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py"
G0054_REPORT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate_v1.json.gz"
G0055_SCRIPT = ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule.py"
G0055_REPORT = ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule_v1.json.gz"
G0056_SCRIPT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift.py"
G0056_REPORT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift_v1.json.gz"
G0057_SCRIPT = ROOT / "artifacts/math/G-0057/s1_high_active_extension_gate.py"
G0057_REPORT = ROOT / "artifacts/math/G-0057/s1_baseline_gate_v1.json.gz"
G0059_SCRIPT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle.py"
G0059_REPORT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz"

EXPECTED_G0059_COMMIT = "0d2d1a4cbb44d326a4984333cffd1a2aa6ea8c1d"
EXPECTED_HASHES = {
    "g0050_script_sha256": "b82fbb6df487b0e76a4bbefc695960b9f1a87ef25a9e8e33b26f07d02433f27b",
    "g0050_report_sha256": "64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b",
    "g0054_script_sha256": "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2",
    "g0054_report_sha256": "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053",
    "g0055_script_sha256": "5f78397925e0873b696dc9d4b6c0562b9af58a0198e74ca636049f932fbade17",
    "g0055_report_sha256": "f6e6c824cbebab126f7452bc922859f5b53fa54f1af91cfb71dfefca41ba5cdc",
    "g0056_script_sha256": "484d86ccc494019c802f3f793c8f40c4deda2e7e86913191888a2188fef527c7",
    "g0056_report_sha256": "131312761477dc3ae47167caa83aabdde1d7dc6da40b71e33c40c8b5401088d4",
    "g0057_script_sha256": "2555f4f683f4aee768b337bdb62c8fbf9f569ff6a9bff9f14de368140ea2920d",
    "g0057_report_sha256": "1e2f992254d977dce0551ff8b003147edf042b07cf5d015477d30594d2027f38",
    "g0059_script_sha256": "dd743b702a99541e835b52bbdf5ec4c50c9650344bdf2ea0d4f81d22a7678ecd",
    "g0059_report_sha256": "72ade3d6c9c507d6843f161419dc92b7b1273a299a7eff7c9def6a7d3e0ddb37",
}
EXPECTED_G0057_PAYLOAD_SHA256 = "093a80a38c777678ddda0a76184650b75865784eb2eda7a0a91e5c653021af11"
EXPECTED_G0059_PAYLOAD_SHA256 = "9f5d1dfde5a8ccaa4e0e02d98a588e41025c1a973211a7829f14af9ab74c5d6b"
EXPECTED_UNIVERSE_SHA256 = "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
EXPECTED_BASELINE_STREAM_SHA256 = "b24a0a63100839f9661377b5ffa2c266752b139592b13eed27cfb553ffaf6ce8"
EXPECTED_BASELINE_MATRIX_SHA256 = "1a2fd2a5fcb702ffe747c9e20f1234d4d43316975eff1b4669337e945f2f467d"
EXPECTED_BASELINE_UNION_ROWS_SHA256 = "b5e032829ce5a28ee24eab75a03983593f3eb405812938ba55960a501fa5cd82"
EXPECTED_LAMBDA_ROW_SHA256 = "8099a522ff5d56e27fc120e285ad5446347b72c0c69f7d25f4728eddafab1600"

PRIMES = (1_000_003, 1_000_033)
EXPECTED_ROWS = 99_858
EXPECTED_COLUMNS = 1_358
EXPECTED_RANK = 1_288
EXPECTED_NULLITY = 70
EXPECTED_COEFFICIENTS = 372
DEFAULT_OUTPUT = HERE / "exact_s1_kernel_lift_v1.json.gz"
SCHEMA = "max11-g0061-exact-s1-kernel-lift-v1"


class LiftError(RuntimeError):
    """Fail-closed exact-lift error."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def deterministic_scientific_view(value: object) -> object:
    dynamic = {
        "seconds",
        "wall_seconds",
        "semantic_seconds",
        "available_gib",
        "memory_available_bytes",
        "minimum_required_gib",
    }
    if isinstance(value, dict):
        return {
            key: deterministic_scientific_view(item)
            for key, item in value.items()
            if key not in dynamic
        }
    if isinstance(value, list):
        return [deterministic_scientific_view(item) for item in value]
    return value


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise LiftError(f"top-level object required: {path}")
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise LiftError(f"bound script drift: {path}: {observed} != {expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise LiftError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def upstream_paths() -> dict[str, Path]:
    return {
        "g0050_script_sha256": G0050_SCRIPT,
        "g0050_report_sha256": G0050_REPORT,
        "g0054_script_sha256": G0054_SCRIPT,
        "g0054_report_sha256": G0054_REPORT,
        "g0055_script_sha256": G0055_SCRIPT,
        "g0055_report_sha256": G0055_REPORT,
        "g0056_script_sha256": G0056_SCRIPT,
        "g0056_report_sha256": G0056_REPORT,
        "g0057_script_sha256": G0057_SCRIPT,
        "g0057_report_sha256": G0057_REPORT,
        "g0059_script_sha256": G0059_SCRIPT,
        "g0059_report_sha256": G0059_REPORT,
    }


def verify_committed_g0059_bytes() -> dict[str, Any]:
    observed_commit = subprocess.run(
        ["git", "rev-parse", f"{EXPECTED_G0059_COMMIT}^{{commit}}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if observed_commit != EXPECTED_G0059_COMMIT:
        raise LiftError(f"G-0059 commit drift: {observed_commit}")
    committed = {}
    for label, relative, expected in (
        (
            "g0059_script",
            "artifacts/math/G-0059/modular_quotient_oracle.py",
            EXPECTED_HASHES["g0059_script_sha256"],
        ),
        (
            "g0059_report",
            "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz",
            EXPECTED_HASHES["g0059_report_sha256"],
        ),
    ):
        payload = subprocess.run(
            ["git", "show", f"{EXPECTED_G0059_COMMIT}:{relative}"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        ).stdout
        digest = hashlib.sha256(payload).hexdigest()
        if digest != expected:
            raise LiftError(f"committed {label} bytes drift: {digest}")
        committed[f"{label}_committed_sha256"] = digest
    return {
        "producer_commit": observed_commit,
        **committed,
        "working_bytes_equal_committed_bytes": True,
    }


def checked_bindings() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], ModuleType]:
    observed = {label: sha256_path(path) for label, path in upstream_paths().items()}
    if observed != EXPECTED_HASHES:
        raise LiftError(f"upstream byte drift: observed={observed}, expected={EXPECTED_HASHES}")
    commit_binding = verify_committed_g0059_bytes()
    g0057_report = load_json_gz(G0057_REPORT)
    g0059_report = load_json_gz(G0059_REPORT)
    g0059 = import_bound(
        "g0061_bound_g0059", G0059_SCRIPT, EXPECTED_HASHES["g0059_script_sha256"]
    )
    g0057 = import_bound(
        "g0061_bound_g0057", G0057_SCRIPT, EXPECTED_HASHES["g0057_script_sha256"]
    )
    g0057_keys = (
        "schema",
        "result",
        "bindings",
        "baseline_scope",
        "candidate_scope",
        "complete_integer_semantics",
        "modular_results",
        "controls",
        "claim_boundary",
    )
    g0057_payload = {key: g0057_report[key] for key in g0057_keys}
    if (
        g0057_report.get("canonical_scientific_payload_sha256")
        != EXPECTED_G0057_PAYLOAD_SHA256
        or g0057.canonical_sha256(g0057_payload) != EXPECTED_G0057_PAYLOAD_SHA256
        or g0057_report.get("bindings")
        != {key: observed[key] for key in observed if key.startswith(("g0050", "g0054", "g0055", "g0056"))}
    ):
        raise LiftError("G-0057 scientific payload/upstream binding drift")
    g0059_keys = (
        "schema",
        "result",
        "bindings",
        "max10_induced_block_reconstruction",
        "baseline",
        "candidate_semantics",
        "prime_results",
        "cross_prime_comparison",
        "controls",
        "epistemic_status",
        "claim_boundary",
    )
    g0059_payload = {key: g0059_report[key] for key in g0059_keys}
    if (
        g0059_report.get("result")
        != "NO_JOINT_329_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME"
        or g0059_report.get("canonical_scientific_payload_sha256")
        != EXPECTED_G0059_PAYLOAD_SHA256
        or g0059.canonical_sha256(g0059.deterministic_scientific_view(g0059_payload))
        != EXPECTED_G0059_PAYLOAD_SHA256
    ):
        raise LiftError("G-0059 scientific payload drift")
    bindings = {
        **observed,
        **commit_binding,
        "g0057_scientific_payload_sha256": EXPECTED_G0057_PAYLOAD_SHA256,
        "g0059_scientific_payload_sha256": EXPECTED_G0059_PAYLOAD_SHA256,
        "complete_degree4_universe_sha256": EXPECTED_UNIVERSE_SHA256,
        "baseline_ordered_sparse_stream_sha256": EXPECTED_BASELINE_STREAM_SHA256,
        "baseline_integer_matrix_sha256": EXPECTED_BASELINE_MATRIX_SHA256,
        "baseline_union_row_indices_sha256": EXPECTED_BASELINE_UNION_ROWS_SHA256,
        "baseline_lambda_row_sha256": EXPECTED_LAMBDA_ROW_SHA256,
    }
    return bindings, g0057_report, g0059_report, g0057


def crt_pair(a: int, p: int, b: int, q: int) -> int:
    if gcd(p, q) != 1:
        raise LiftError("CRT moduli are not coprime")
    return (a + p * (((b - a) * pow(p, -1, q)) % q)) % (p * q)


def rational_reconstruct(residue: int, modulus: int, bound: int) -> Fraction:
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
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def modular_kernel_data(
    report: dict[str, Any],
) -> tuple[list[int], list[int], list[list[dict[str, Any]]], dict[str, Any]]:
    baseline = report.get("baseline", {})
    profiles = baseline.get("per_prime_rank_profiles_and_preserved_nullspaces")
    if not isinstance(profiles, list) or len(profiles) != 2:
        raise LiftError("G-0059 modular profile census drift")
    if [int(item["prime"]) for item in profiles] != list(PRIMES):
        raise LiftError("G-0059 prime order drift")
    if [int(item["rank"]) for item in profiles] != [EXPECTED_RANK] * 2:
        raise LiftError("G-0059 baseline rank drift")
    if [int(item["nullity"]) for item in profiles] != [EXPECTED_NULLITY] * 2:
        raise LiftError("G-0059 baseline nullity drift")
    pivot_columns = list(map(int, profiles[0]["pivot_columns"]))
    pivot_rows = list(map(int, report["cross_prime_comparison"]["common_pivot_complete_rows"]))
    if (
        profiles[1]["pivot_columns"] != pivot_columns
        or report["cross_prime_comparison"]["common_pivot_columns"] != pivot_columns
        or len(pivot_columns) != EXPECTED_RANK
        or len(pivot_rows) != EXPECTED_RANK
        or len(set(pivot_columns)) != EXPECTED_RANK
        or len(set(pivot_rows)) != EXPECTED_RANK
    ):
        raise LiftError("common pivot manifest drift")
    bases = [list(item["kernel_basis"]) for item in profiles]
    if [len(item) for item in bases] != [EXPECTED_NULLITY] * 2:
        raise LiftError("kernel basis census drift")
    pivot_set = set(pivot_columns)
    nonpivots = [column for column in range(EXPECTED_COLUMNS) if column not in pivot_set]
    if len(nonpivots) != EXPECTED_NULLITY:
        raise LiftError("nonpivot census drift")
    total_coefficients = 0
    for basis_index, (left, right) in enumerate(zip(bases[0], bases[1], strict=True)):
        if int(left["distinguished_nonpivot_column"]) != nonpivots[basis_index]:
            raise LiftError(f"left distinguished coordinate drift at {basis_index}")
        if int(right["distinguished_nonpivot_column"]) != nonpivots[basis_index]:
            raise LiftError(f"right distinguished coordinate drift at {basis_index}")
        left_support = [[int(a), int(b)] for a, b in left["support"]]
        right_support = [[int(a), int(b)] for a, b in right["support"]]
        left_columns = [item[0] for item in left_support]
        right_columns = [item[0] for item in right_support]
        if (
            len(left_columns) != len(set(left_columns))
            or len(right_columns) != len(set(right_columns))
            or any(not 0 <= column < EXPECTED_COLUMNS for column in left_columns)
            or any(not 0 <= column < EXPECTED_COLUMNS for column in right_columns)
        ):
            raise LiftError(f"malformed modular support at {basis_index}")
        if left_columns != right_columns:
            raise LiftError(f"cross-prime support mismatch at {basis_index}")
        free_support = [column for column, _value in left_support if column in nonpivots]
        if free_support != [nonpivots[basis_index]]:
            raise LiftError(f"free-coordinate support drift at {basis_index}")
        if dict(left_support)[nonpivots[basis_index]] != 1 or dict(right_support)[nonpivots[basis_index]] != 1:
            raise LiftError(f"unit free-coordinate drift at {basis_index}")
        total_coefficients += len(left_support)
    if (
        total_coefficients != EXPECTED_COEFFICIENTS
        or not all(item["all_70_normalized_kernel_vectors_replay_to_zero"] for item in profiles)
        or not report["cross_prime_comparison"]["kernel_basis_supports_identical_in_order"]
        or not report["cross_prime_comparison"]["distinguished_free_coordinates_identical_in_order"]
    ):
        raise LiftError("normalized modular kernel control drift")
    controls = {
        "pivot_columns": len(pivot_columns),
        "pivot_complete_rows": len(pivot_rows),
        "nullspace_vectors_per_prime": [len(item) for item in bases],
        "aligned_sparse_coefficients": total_coefficients,
        "supports_identical_across_primes": True,
        "distinct_unit_free_coordinates": True,
    }
    return pivot_rows, pivot_columns, bases, controls


def lift_relations(
    bases: list[list[dict[str, Any]]], pivot_columns: list[int]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    modulus = PRIMES[0] * PRIMES[1]
    bound = isqrt(modulus // 2)
    if not 2 * bound * bound < modulus:
        raise LiftError("CRT reconstruction uniqueness inequality failed")
    pivot_set = set(pivot_columns)
    nonpivots = [column for column in range(EXPECTED_COLUMNS) if column not in pivot_set]
    numerator_histogram: Counter[int] = Counter()
    denominator_histogram: Counter[int] = Counter()
    support_histogram: Counter[int] = Counter()
    lcm_histogram: Counter[int] = Counter()
    lifted: list[dict[str, Any]] = []
    maximum_numerator = maximum_denominator = maximum_integer = total = 0
    for basis_index, (left, right) in enumerate(zip(bases[0], bases[1], strict=True)):
        support_left = [[int(a), int(b)] for a, b in left["support"]]
        support_right = [[int(a), int(b)] for a, b in right["support"]]
        support = [item[0] for item in support_left]
        if [item[0] for item in support_right] != support:
            raise LiftError(f"support mismatch during lift at {basis_index}")
        rationals: list[Fraction] = []
        for (_column, residue_left), (_same_column, residue_right) in zip(
            support_left, support_right, strict=True
        ):
            residue = crt_pair(residue_left, PRIMES[0], residue_right, PRIMES[1])
            value = rational_reconstruct(residue, modulus, bound)
            for prime, modular in zip(PRIMES, (residue_left, residue_right), strict=True):
                if value.numerator * pow(value.denominator, -1, prime) % prime != modular:
                    raise LiftError(f"prime roundtrip failed at relation {basis_index}")
            rationals.append(value)
            numerator_histogram[value.numerator] += 1
            denominator_histogram[value.denominator] += 1
            maximum_numerator = max(maximum_numerator, abs(value.numerator))
            maximum_denominator = max(maximum_denominator, value.denominator)
        distinguished = nonpivots[basis_index]
        if rationals[support.index(distinguished)] != 1:
            raise LiftError(f"rational unit free coordinate failed at {basis_index}")
        denominator_lcm = 1
        for value in rationals:
            denominator_lcm = lcm(denominator_lcm, value.denominator)
        integers = [
            value.numerator * (denominator_lcm // value.denominator)
            for value in rationals
        ]
        for prime, source in zip(PRIMES, (support_left, support_right), strict=True):
            modular_coefficients = [item[1] for item in source]
            if [value % prime for value in integers] != [
                denominator_lcm * value % prime for value in modular_coefficients
            ]:
                raise LiftError(f"cleared-integer roundtrip failed at {basis_index}")
        maximum_integer = max(maximum_integer, max(map(abs, integers)))
        total += len(support)
        support_histogram[len(support)] += 1
        lcm_histogram[denominator_lcm] += 1
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
    if total != EXPECTED_COEFFICIENTS:
        raise LiftError(f"lifted coefficient census drift: {total}")
    return lifted, {
        "crt_modulus": modulus,
        "global_numerator_denominator_bound": bound,
        "strict_uniqueness_inequality": f"2*{bound}^2 < {modulus}",
        "all_coefficients_reconstructed_uniquely": True,
        "all_coefficients_roundtrip_at_both_primes": True,
        "total_coefficients": total,
        "maximum_absolute_numerator": maximum_numerator,
        "maximum_denominator": maximum_denominator,
        "maximum_absolute_cleared_integer_coefficient": maximum_integer,
        "numerator_histogram": {str(k): v for k, v in sorted(numerator_histogram.items())},
        "denominator_histogram": {str(k): v for k, v in sorted(denominator_histogram.items())},
        "support_size_histogram": {str(k): v for k, v in sorted(support_histogram.items())},
        "cleared_denominator_lcm_histogram": {str(k): v for k, v in sorted(lcm_histogram.items())},
        "lifted_relations_sha256": canonical_sha256(lifted),
    }


def regenerate_semantics(
    g0057: ModuleType,
    g0057_report: dict[str, Any],
    g0059_report: dict[str, Any],
    workers: int,
) -> tuple[
    tuple[tuple[int, ...], ...],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
]:
    g0057.G0054 = g0057.import_bound(
        "g0061_g0054", g0057.G0054_SCRIPT, g0057.EXPECTED_G0054_SCRIPT_SHA256
    )
    g0057.THEOREM = g0057.G0054.load_theorem("g0061_theorem")
    universe = g0057.G0054.direction_universe()
    if (
        len(universe) != EXPECTED_ROWS
        or canonical_sha256([list(direction) for direction in universe]) != EXPECTED_UNIVERSE_SHA256
    ):
        raise LiftError("complete degree-four universe drift")
    g0057.ROW_INDEX = {direction: index for index, direction in enumerate(universe)}
    (
        s0_sequences,
        proper_indices,
        seed_indices,
        selected_candidates,
        _prices,
        exact_manifest,
        _manifest_metadata,
    ) = g0057.load_frozen_manifests("baseline-only")
    if selected_candidates:
        raise LiftError("baseline-only manifest unexpectedly selected candidates")
    g0050 = g0057.import_bound(
        "g0061_g0050", g0057.G0050_SCRIPT, g0057.EXPECTED_G0050_SCRIPT_SHA256
    )
    extract = g0050.import_extract()
    search = extract.load_search()
    lowmass_records = search.load_records(search.load_g47())
    if len(lowmass_records) != 3_310:
        raise LiftError("low-mass census drift")
    mass4_records = g0057.read_mass4_records(g0057.THEOREM, set(s0_sequences))
    payloads: list[tuple[int, str, int, dict[str, Any]]] = []
    for pivot_position, sequence in enumerate(s0_sequences):
        payloads.append(
            (len(payloads), "s0_mass4_pivot", pivot_position, mass4_records[sequence])
        )
    for column_index in proper_indices:
        payloads.append(
            (len(payloads), "lowmass_proper_basis", column_index, lowmass_records[column_index])
        )
    for column_index in seed_indices:
        payloads.append(
            (len(payloads), "lowmass_full_seed", column_index, lowmass_records[column_index])
        )
    if len(payloads) != EXPECTED_COLUMNS:
        raise LiftError("baseline payload census drift")
    results, semantic_seconds = g0057.generate_semantics(
        payloads, g0057.ROW_INDEX, workers, "G0061_EXACT_SEMANTIC"
    )
    exact_s0 = g0057.verify_exact_s0_basis_semantics(
        results[: g0057.EXPECTED_S0_PIVOTS], exact_manifest
    )
    lowmass = g0057.verify_lowmass_semantics_independently(
        search,
        [lowmass_records[index] for index in proper_indices + seed_indices],
        results[g0057.EXPECTED_S0_PIVOTS :],
        g0057.ROW_INDEX,
        workers,
    )
    union_rows, matrix, lambda_row, metadata = g0057.build_union_matrix(universe, results)
    lambda_hash = hashlib.sha256(
        lambda_row.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    if (
        g0057.ordered_sparse_stream_hash(results) != EXPECTED_BASELINE_STREAM_SHA256
        or metadata["matrix_sha256"] != EXPECTED_BASELINE_MATRIX_SHA256
        or metadata["union_row_indices_sha256"] != EXPECTED_BASELINE_UNION_ROWS_SHA256
        or lambda_hash != EXPECTED_LAMBDA_ROW_SHA256
        or metadata != g0057_report["complete_integer_semantics"]["exact_union"]
        or g0059_report["baseline"]["integer_matrix_sha256"] != metadata["matrix_sha256"]
    ):
        raise LiftError("independently regenerated baseline semantic matrix drift")
    controls = {
        "semantic_seconds": semantic_seconds,
        "ordered_column_count": len(results),
        "ordered_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(results),
        "integer_matrix_shape": list(matrix.shape),
        "integer_matrix_sha256": metadata["matrix_sha256"],
        "union_row_indices_sha256": metadata["union_row_indices_sha256"],
        "lambda_row_sha256": lambda_hash,
        "exact_s0_basis_crosscheck": exact_s0,
        "independent_lowmass_crosscheck": lowmass,
        "all_bytes_match_frozen_g0057_and_g0059_baseline": True,
    }
    return universe, results, union_rows, matrix, lambda_row, controls


def replay_exact_relations(
    lifted: list[dict[str, Any]],
    semantics: list[dict[str, Any]],
    lambda_row: np.ndarray,
    universe: tuple[tuple[int, ...], ...],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    maximum_entry = max(
        abs(int(value)) for column in semantics for value in column["values"]
    )
    lambda_gcd = 0
    for value in lambda_row:
        lambda_gcd = gcd(lambda_gcd, abs(int(value)))
    if not lambda_gcd:
        raise LiftError("lambda row is identically zero")
    normalized_lambda = lambda_row // lambda_gcd
    if not np.array_equal(normalized_lambda * lambda_gcd, lambda_row):
        raise LiftError("lambda gcd normalization failed")
    maximum_normalized_lambda = int(np.max(np.abs(normalized_lambda)))
    maximum_support = max(len(item["support_zero_based_columns"]) for item in lifted)
    maximum_coefficient = max(
        abs(int(value))
        for item in lifted
        for value in item["cleared_integer_coefficients"]
    )
    modulus = PRIMES[0] * PRIMES[1]
    hinge_height_bound = maximum_support * maximum_coefficient * maximum_entry
    lambda_height_bound = (
        maximum_support * maximum_coefficient * maximum_normalized_lambda
    )
    if not hinge_height_bound < modulus or not lambda_height_bound < modulus:
        raise LiftError("deterministic replay height bound is not strict")

    replayed_terms = 0
    maximum_intermediate = 0
    lambda_residuals: list[int] = []
    for relation_index, relation in enumerate(lifted):
        residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
        for column, coefficient in zip(
            relation["support_zero_based_columns"],
            relation["cleared_integer_coefficients"],
            strict=True,
        ):
            semantic = semantics[int(column)]
            rows = semantic["rows"]
            residual[rows] += int(coefficient) * semantic["values"]
            replayed_terms += len(rows)
            if len(rows):
                maximum_intermediate = max(
                    maximum_intermediate, int(np.max(np.abs(residual[rows])))
                )
        bad = np.flatnonzero(residual)
        if len(bad):
            row = int(bad[0])
            raise LiftError(
                f"exact hinge replay failed at relation={relation_index}, row={row}, "
                f"direction={universe[row]}, residual={int(residual[row])}"
            )
        lambda_residual = sum(
            int(coefficient) * int(lambda_row[int(column)])
            for column, coefficient in zip(
                relation["support_zero_based_columns"],
                relation["cleared_integer_coefficients"],
                strict=True,
            )
        )
        if lambda_residual:
            raise LiftError(
                f"exact Lambda replay failed at relation {relation_index}: {lambda_residual}"
            )
        lambda_residuals.append(lambda_residual)
        if (relation_index + 1) % 10 == 0 or relation_index + 1 == len(lifted):
            print(
                f"G0061_REPLAY relations={relation_index + 1}/{len(lifted)}",
                file=sys.stderr,
                flush=True,
            )

    first = lifted[0]
    mutant_coefficients = list(first["cleared_integer_coefficients"])
    mutant_coefficients[0] += 1
    mutant_residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
    for column, coefficient in zip(
        first["support_zero_based_columns"], mutant_coefficients, strict=True
    ):
        semantic = semantics[int(column)]
        mutant_residual[semantic["rows"]] += int(coefficient) * semantic["values"]
    mutant_bad = np.flatnonzero(mutant_residual)
    if not len(mutant_bad):
        raise LiftError("coefficient +1 mutant was not rejected")
    mutant_row = int(mutant_bad[0])
    replay = {
        "relations_replayed": len(lifted),
        "complete_degree4_rows_per_relation": EXPECTED_ROWS,
        "all_exact_integer_hinge_residuals_zero": True,
        "all_exact_lambda_residuals_zero": True,
        "lambda_residuals_sha256": canonical_sha256(lambda_residuals),
        "replayed_sparse_nonzero_terms": replayed_terms,
        "maximum_observed_absolute_intermediate": maximum_intermediate,
    }
    height = {
        "crt_modulus": modulus,
        "maximum_support_size": maximum_support,
        "maximum_absolute_integer_coefficient": maximum_coefficient,
        "maximum_absolute_hinge_entry": maximum_entry,
        "exact_lambda_gcd": lambda_gcd,
        "maximum_absolute_normalized_lambda_entry": maximum_normalized_lambda,
        "uniform_hinge_residual_height_bound": hinge_height_bound,
        "uniform_normalized_lambda_residual_height_bound": lambda_height_bound,
        "both_uniform_bounds_strictly_below_crt_modulus": True,
    }
    mutation = {
        "relation_index": 0,
        "support_local_index": 0,
        "coefficient_plus_one_rejected": True,
        "first_nonzero_complete_row": mutant_row,
        "first_nonzero_direction": list(universe[mutant_row]),
        "residual_value": int(mutant_residual[mutant_row]),
    }
    return replay, height, mutation


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.int64)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def exact_rank_certificate(
    pivot_complete_rows: list[int],
    pivot_columns: list[int],
    union_rows: np.ndarray,
    matrix: np.ndarray,
    g0059_report: dict[str, Any],
) -> tuple[dict[str, Any], np.ndarray]:
    complete_to_union = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    complete_to_union[union_rows] = np.arange(len(union_rows), dtype=np.int32)
    local_rows = complete_to_union[pivot_complete_rows]
    if np.any(local_rows < 0):
        raise LiftError("pivot complete row escaped exact baseline union")
    minor = np.ascontiguousarray(
        matrix[np.ix_(local_rows, pivot_columns)], dtype=np.int64
    )
    if minor.shape != (EXPECTED_RANK, EXPECTED_RANK):
        raise LiftError("exact minor shape drift")
    minor_sha256 = hashlib.sha256(
        minor.astype("<i8", copy=False).tobytes(order="C")
    ).hexdigest()
    pivot_rows_sha256 = canonical_sha256(pivot_complete_rows)
    pivot_columns_sha256 = canonical_sha256(pivot_columns)
    determinant_residues = []
    for prime, modular in zip(PRIMES, g0059_report["prime_results"], strict=True):
        frozen_minor = modular["pivot_minor"]
        if (
            int(modular["prime"]) != prime
            or int(frozen_minor["rank"]) != EXPECTED_RANK
            or list(map(int, frozen_minor["pivot_complete_rows"]))
            != pivot_complete_rows
            or list(map(int, frozen_minor["pivot_columns"])) != pivot_columns
            or frozen_minor["pivot_complete_rows_sha256"] != pivot_rows_sha256
            or frozen_minor["pivot_columns_sha256"] != pivot_columns_sha256
            or frozen_minor["minor_int64_sha256"] != minor_sha256
        ):
            raise LiftError(f"frozen pivot-minor manifest drift at {prime}")
        determinant = int(to_nmod(minor, prime).det())
        if not determinant or determinant != int(frozen_minor["determinant_mod_prime"]):
            raise LiftError(f"minor determinant replay failed at {prime}")
        determinant_residues.append({"prime": prime, "determinant": determinant})
    return {
        "pivot_complete_rows": pivot_complete_rows,
        "pivot_complete_rows_sha256": pivot_rows_sha256,
        "pivot_columns": pivot_columns,
        "pivot_columns_sha256": pivot_columns_sha256,
        "minor_shape": list(minor.shape),
        "minor_int64_row_major_sha256": minor_sha256,
        "minor_determinant_residues": determinant_residues,
        "nonzero_integer_minor_from_nonzero_modular_determinant": True,
        "rank_Q_lower_bound": EXPECTED_RANK,
        "rank_Q_upper_bound_from_70_independent_kernel_vectors": (
            EXPECTED_COLUMNS - EXPECTED_NULLITY
        ),
        "exact_rank_Q": EXPECTED_RANK,
    }, minor


def self_test() -> dict[str, Any]:
    modulus = PRIMES[0] * PRIMES[1]
    bound = isqrt(modulus // 2)
    probes = (Fraction(1, 2), Fraction(-1, 2), Fraction(5, 4), Fraction(-5, 4))
    for expected in probes:
        residues = [
            expected.numerator * pow(expected.denominator, -1, prime) % prime
            for prime in PRIMES
        ]
        combined = crt_pair(residues[0], PRIMES[0], residues[1], PRIMES[1])
        if rational_reconstruct(combined, modulus, bound) != expected:
            raise LiftError(f"rational reconstruction control failed: {expected}")
    sparse_columns = (
        (np.array([0, 2], dtype=np.uint32), np.array([1, 2], dtype=np.int64)),
        (np.array([1, 2], dtype=np.uint32), np.array([1, 3], dtype=np.int64)),
        (np.array([0, 1, 2], dtype=np.uint32), np.array([1, 1, 5], dtype=np.int64)),
    )
    residual = np.zeros(3, dtype=np.int64)
    for coefficient, (rows, values) in zip((-1, -1, 1), sparse_columns, strict=True):
        residual[rows] += coefficient * values
    if np.any(residual):
        raise LiftError("synthetic exact relation failed")
    rows, values = sparse_columns[0]
    residual[rows] += values
    if not np.any(residual):
        raise LiftError("synthetic coefficient mutation was not rejected")
    dynamic_left = {
        "rank": 2,
        "seconds": 1.0,
        "nested": {"available_gib": 10.0, "minimum_required_gib": 12.0},
    }
    dynamic_right = {
        "rank": 2,
        "seconds": 9.0,
        "nested": {"available_gib": 99.0, "minimum_required_gib": 24.0},
    }
    if canonical_sha256(deterministic_scientific_view(dynamic_left)) != canonical_sha256(
        deterministic_scientific_view(dynamic_right)
    ):
        raise LiftError("deterministic scientific projection control failed")
    return {
        "crt_rational_reconstruction_known_answers": True,
        "exact_sparse_relation_positive_control": True,
        "coefficient_plus_one_mutation_rejected": True,
        "deterministic_scientific_projection_ignores_runtime_fields": True,
    }


def memory_available_bytes() -> int:
    with Path("/proc/meminfo").open("rt", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise LiftError("cannot read MemAvailable")


def preflight() -> dict[str, Any]:
    started = time.perf_counter()
    bindings, _g0057_report, g0059_report, _g0057 = checked_bindings()
    _rows, columns, bases, controls = modular_kernel_data(g0059_report)
    lifted, reconstruction = lift_relations(bases, columns)
    return {
        "result": "PASS",
        "bindings": bindings,
        "kernel_controls": controls,
        "relations": len(lifted),
        "reconstruction": reconstruction,
        "memory_available_bytes": memory_available_bytes(),
        "seconds": time.perf_counter() - started,
    }


def run(workers: int, minimum_available_gib: float) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    bindings, g0057_report, g0059_report, g0057 = checked_bindings()
    ready = g0057.resource_preflight(minimum_available_gib)
    synthetic = self_test()
    pivot_rows, pivot_columns, bases, kernel_controls = modular_kernel_data(
        g0059_report
    )
    lift_started = time.perf_counter()
    lifted, reconstruction = lift_relations(bases, pivot_columns)
    lift_seconds = time.perf_counter() - lift_started
    (
        universe,
        semantics,
        union_rows,
        matrix,
        lambda_row,
        semantic_controls,
    ) = regenerate_semantics(g0057, g0057_report, g0059_report, workers)
    replay_started = time.perf_counter()
    replay, height, mutation = replay_exact_relations(
        lifted, semantics, lambda_row, universe
    )
    replay_seconds = time.perf_counter() - replay_started
    rank_certificate, _minor = exact_rank_certificate(
        pivot_rows, pivot_columns, union_rows, matrix, g0059_report
    )

    pivot_set = set(pivot_columns)
    distinguished = [
        int(item["distinguished_nonpivot_column"]) for item in lifted
    ]
    if (
        sorted(pivot_columns + distinguished) != list(range(EXPECTED_COLUMNS))
        or len(set(distinguished)) != EXPECTED_NULLITY
        or any(
            [column for column in relation["support_zero_based_columns"] if column not in pivot_set]
            != [relation["distinguished_nonpivot_column"]]
            for relation in lifted
        )
    ):
        raise LiftError("exact basis/free-coordinate partition drift")

    basis_manifest = []
    for basis_index, column in enumerate(pivot_columns):
        semantic = semantics[column]
        basis_manifest.append(
            {
                "basis_index": basis_index,
                "source_zero_based_column": column,
                "namespace": semantic["namespace"],
                "source_id": int(semantic["source_id"]),
                "source_sequence": int(semantic["sequence"]),
                "active_vertices": int(semantic["active_vertices"]),
                "lambda": int(semantic["lambda"]),
                "support_size": len(semantic["rows"]),
                "semantic_sha256": semantic["semantic_sha256"],
            }
        )

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "EXACT_Q_S1_BASELINE_RANK_1288_KERNEL_70_ALL_LAMBDA_ZERO",
        "epistemic_status": "COMPUTED_BOUNDED_PENDING_INDEPENDENT_REPLAY",
        "script_sha256": script_hash_before,
        "bindings": bindings,
        "controls": {
            "resource_preflight": ready,
            "synthetic": synthetic,
            "modular_kernel_input": kernel_controls,
            "semantic_regeneration": semantic_controls,
            "semantic_regeneration_implementation_independent": False,
            "coefficient_mutation": mutation,
        },
        "two_prime_rational_reconstruction": reconstruction,
        "exact_kernel_basis": {
            "relation_count": len(lifted),
            "ambient_column_count": EXPECTED_COLUMNS,
            "pivot_column_count": len(pivot_columns),
            "pivot_columns": pivot_columns,
            "pivot_columns_sha256": canonical_sha256(pivot_columns),
            "distinguished_nonpivot_columns": distinguished,
            "distinguished_nonpivot_columns_sha256": canonical_sha256(distinguished),
            "each_relation_has_one_distinct_nonpivot_coefficient_equal_to_one_before_denominator_clearing": True,
            "relations_are_Q_linearly_independent": True,
            "relations": lifted,
            "relations_sha256": canonical_sha256(lifted),
        },
        "exact_complete_replay": replay,
        "deterministic_height_certificate": height,
        "exact_rank_certificate": rank_certificate,
        "canonical_exact_s1_basis": {
            "basis_column_count": len(basis_manifest),
            "basis_manifest": basis_manifest,
            "basis_manifest_sha256": canonical_sha256(basis_manifest),
            "ordered_basis_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(
                [semantics[column] for column in pivot_columns]
            ),
            "basis_total_nonzeros": sum(item["support_size"] for item in basis_manifest),
        },
        "exact_bounded_conclusion": (
            "Over Q, the frozen 1,358-column S1 baseline hinge matrix has exact rank "
            "1,288 and a 70-dimensional kernel. The 70 displayed rational relations "
            "form a basis of that kernel, and every one has exact Lambda zero. Hence "
            "no hinge-free rational combination of only these frozen columns has a "
            "nonzero MAX11 finite-difference invariant."
        ),
        "claim_boundary": [
            "This exact statement concerns only the frozen 1,358-column S1 baseline on the complete 99,858-row degree-four primitive hinge universe.",
            "The fresh semantic regeneration reuses the hash-bound G-0057 producer implementation; it is not a clean-room semantic replay, so the result remains pending independent replay.",
            "It does not include sequence 92,489, the 328 MAX10-induced G-0059 columns, the remaining proper mass-four atoms, higher signed masses, arbitrary weights, or nonsymmetric models.",
            "It is not an unrestricted two-hidden-layer lower bound for MAX11.",
        ],
        "mandatory_next_gate": (
            "Use the canonical exact 1,288-column S1 basis as the baseline for any "
            "future quotient extension; retain the separately certified modular Schur "
            "oracle and exact-lift any future Lambda-potent circuit before interpretation."
        ),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
        },
        "timing": {
            "rational_reconstruction_seconds": lift_seconds,
            "semantic_regeneration_seconds": semantic_controls["semantic_seconds"],
            "exact_replay_seconds": replay_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
    }
    scientific_keys = (
        "schema",
        "result",
        "epistemic_status",
        "bindings",
        "controls",
        "two_prime_rational_reconstruction",
        "exact_kernel_basis",
        "exact_complete_replay",
        "deterministic_height_certificate",
        "exact_rank_certificate",
        "canonical_exact_s1_basis",
        "exact_bounded_conclusion",
        "claim_boundary",
        "mandatory_next_gate",
    )
    scientific_payload = {key: report[key] for key in scientific_keys}
    report["canonical_scientific_payload_sha256"] = canonical_sha256(
        deterministic_scientific_view(scientific_payload)
    )
    report["canonical_scientific_payload_projection"] = (
        "recursive projection excluding runtime seconds, wall_seconds, semantic_seconds, "
        "available_gib, memory_available_bytes, and minimum_required_gib"
    )
    if sha256_path(Path(__file__)) != script_hash_before:
        raise LiftError("script changed during exact lift")
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
        print(json.dumps({"result": "SELF_TEST_PASS", **self_test()}, sort_keys=True))
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
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
