#!/usr/bin/env python3
"""Attempt the adaptive 229-support exact lift selected by G-0077.

The G-0077 modular left dual has 229 nonzero coefficients among 6,876
canonical basis rows.  This program freezes that support, selects a canonical
229-column modularly nonsingular subsystem, solves it over Q, and delegates
the decisive all-column verification to G-0077's hostile-tested production
certificate verifier.

Sparse failure is inconclusive.  Coefficients that vanish modulo the selected
prime can be nonzero over Q, so failure returns to the full G-0077 route.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
import platform
import resource
import time
from types import ModuleType
from typing import Any

from flint import fmpq_mat
import flint
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
G0077 = ROOT / "artifacts/math/G-0077"
G0077_PRODUCER = G0077 / "exact_left_dual_lift.py"
G0077_PREFLIGHT = G0077 / "exact_left_dual_preflight_v1.json.gz"
G0077_MODULAR = G0077 / "canonical_modular_dual_v1.json.gz"
G0078_PREFLIGHT = HERE / "sparse_exact_preflight_v1.json.gz"

SCHEMA_PREFLIGHT = "max11-g0078-sparse-exact-left-dual-preflight-v1"
SCHEMA_EXACT = "max11-g0078-sparse-exact-left-dual-v1"

PRIME = 1_000_003
FULL_RANK = 6_876
SUPPORT_SIZE = 229
A_COLUMNS = 8_107

EXPECTED_G0077_PRODUCER_SHA256 = (
    "278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279"
)
EXPECTED_G0077_PREFLIGHT_SHA256 = (
    "49e6e9714ef427d461d2940f7ccc7751ebf0b3d06a4a29065779b251429602a6"
)
EXPECTED_G0077_MODULAR_SHA256 = (
    "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4"
)
EXPECTED_FULL_SHA256 = (
    "41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095"
)

# Filled after the adaptive branch is preflighted without an exact outcome.
EXPECTED_PREFLIGHT_SCIENCE_SHA256: str | None = (
    "2e055acf291460f793e6673c9df4d76441ee2d52eda59d49ddb9f809bc91ffec"
)


class SparseLiftError(RuntimeError):
    """A binding, support, algebraic, or exact-verification invariant failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise SparseLiftError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise SparseLiftError(f"expected JSON object: {path}")
    return value


def write_gzip_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(value))


def environment() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": np.__version__,
        "python_flint": flint.__version__,
        "platform": platform.platform(),
    }


def load_g0077() -> ModuleType:
    if not G0077_PRODUCER.is_file() or G0077_PRODUCER.is_symlink():
        raise SparseLiftError("G-0077 producer is not a regular file")
    source = G0077_PRODUCER.read_bytes()
    if hashlib.sha256(source).hexdigest() != EXPECTED_G0077_PRODUCER_SHA256:
        raise SparseLiftError("G-0077 producer drift")
    module = ModuleType("max11_g0077_frozen")
    module.__file__ = str(G0077_PRODUCER)
    compiled = compile(source, str(G0077_PRODUCER), "exec")
    exec(compiled, module.__dict__)
    return module


def custody_paths(g0077: ModuleType, *, include_preflight: bool) -> list[Path]:
    paths = [
        SCRIPT,
        *g0077.fixed_subject_paths(),
        G0077_PREFLIGHT,
        G0077_MODULAR,
    ]
    if include_preflight:
        paths.append(G0078_PREFLIGHT)
    return paths


def load_bound_support(
    g0077: ModuleType,
) -> tuple[dict[str, Any], np.ndarray, dict[str, np.ndarray]]:
    if (
        sha256_path(G0077_PREFLIGHT) != EXPECTED_G0077_PREFLIGHT_SHA256
        or sha256_path(G0077_MODULAR) != EXPECTED_G0077_MODULAR_SHA256
    ):
        raise SparseLiftError("G-0077 preflight/modular receipt drift")
    report, full, basis = g0077.load_modular_report(G0077_MODULAR)
    support = np.asarray(report.get("dual_support"), dtype=np.int64)
    if (
        report.get("dual_support_size") != SUPPORT_SIZE
        or support.shape != (SUPPORT_SIZE,)
        or np.any(support < 0)
        or np.any(support >= FULL_RANK)
        or support.astype(int).tolist() != sorted(set(map(int, support)))
        or g0077.canonical_sha256(support.astype(int).tolist())
        != report.get("dual_support_sha256")
        or report.get("full_input_int64_sha256") != EXPECTED_FULL_SHA256
    ):
        raise SparseLiftError("G-0077 sparse support binding drift")
    selected_rows = np.ascontiguousarray(basis["rows"][support])
    selected_divisors = np.ascontiguousarray(basis["divisors"][support])
    if len(set(map(int, selected_rows))) != SUPPORT_SIZE:
        raise SparseLiftError("sparse support selects duplicate raw rows")
    return report, full, {
        **basis,
        "support": support,
        "selected_rows": selected_rows,
        "selected_divisors": selected_divisors,
    }


def select_sparse_square(
    g0077: ModuleType,
    full: np.ndarray,
    basis_columns: np.ndarray,
    selected_rows: np.ndarray,
    selected_divisors: np.ndarray,
    failing_row: int,
    failing_divisor: int,
) -> dict[str, np.ndarray]:
    primitive_support = np.ascontiguousarray(
        full[np.ix_(selected_rows, basis_columns)]
        // selected_divisors[:, None]
    )
    field, reduced = g0077.to_nmod(primitive_support, PRIME)
    rref, rank_object = field.rref()
    del field, reduced
    rank = int(rank_object)
    if rank != SUPPORT_SIZE:
        raise SparseLiftError(
            f"229-support primitive rows have modular rank only {rank}"
        )
    local_columns = np.asarray(
        g0077.pivot_columns_from_field_rref(rref, rank), dtype=np.int64
    )
    del rref
    selected_columns = np.ascontiguousarray(basis_columns[local_columns])
    square = np.ascontiguousarray(primitive_support[:, local_columns].T)
    rhs = np.ascontiguousarray(
        -(full[failing_row, selected_columns] // failing_divisor)
    )
    return {
        "primitive_support": primitive_support,
        "local_columns": local_columns,
        "selected_columns": selected_columns,
        "coefficient_square": square,
        "rhs": rhs,
    }


def reconstruct_modular_dual(
    g0077: ModuleType,
    report: dict[str, Any],
    sparse: dict[str, np.ndarray],
    support: np.ndarray,
) -> np.ndarray:
    field, reduced = g0077.to_nmod(sparse["coefficient_square"], PRIME)
    rhs_field, rhs_reduced = g0077.to_nmod(sparse["rhs"].reshape(-1, 1), PRIME)
    solution = field.solve(rhs_field)
    support_coefficients = g0077.nmod_column_to_numpy(solution)
    del field, reduced, rhs_field, rhs_reduced, solution
    if np.any(support_coefficients == 0):
        raise SparseLiftError("reconstructed sparse modular support contains zero")
    full_dual = np.zeros(FULL_RANK, dtype=np.int64)
    full_dual[support] = support_coefficients
    if g0077.raw_sha256(full_dual) != report.get(
        "dual_coefficients_mod_prime_sha256"
    ):
        raise SparseLiftError("reconstructed sparse modular dual hash drift")
    return support_coefficients


def run_controls(g0077: ModuleType) -> dict[str, Any]:
    inherited = g0077.run_controls()
    required = {
        "planted_exact_dual_all_columns_zero",
        "exceptional_prime_false_separation_detected_by_exact_replay",
        "false_primitive_divisor_rejected",
        "coefficient_plus_one_mutant_rejected",
        "production_certificate_verifier_exercised",
    }
    if not required.issubset({key for key, value in inherited.items() if value}):
        raise SparseLiftError("inherited production-verifier controls drift")

    # A two-row planted sparse certificate through the same verifier.
    fixture = np.asarray(
        [[1, 0, 0], [0, 1, 0], [1, 1, 1]], dtype=np.int64
    )
    accepted = g0077.verify_integer_certificate(
        fixture,
        np.asarray([0, 1]),
        np.asarray([1, 1]),
        2,
        1,
        [-1, -1],
        1,
        a_columns=2,
        column_block=2,
    )
    if not accepted["accepted"]:
        raise SparseLiftError(f"planted sparse certificate failed: {accepted}")
    return {
        "inherited_production_verifier_controls": True,
        "planted_sparse_exact_certificate_accepted": True,
        "sparse_failure_never_promoted": True,
        "modular_support_never_promoted": True,
    }


def build_preflight() -> dict[str, Any]:
    begun = time.time()
    g0077 = load_g0077()
    custody = g0077.capture_custody(custody_paths(g0077, include_preflight=False))
    report, full, basis = load_bound_support(g0077)
    controls = run_controls(g0077)
    science = {
        "adaptive_parent": "committed G-0077 modular receipt",
        "prime": PRIME,
        "support_size": SUPPORT_SIZE,
        "full_rank": FULL_RANK,
        "A_columns": A_COLUMNS,
        "first_mismatch_row": report["first_mismatch_row"],
        "support_sha256": report["dual_support_sha256"],
        "basis_policy": (
            "freeze the 229 nonzero modular coefficient positions, use their primitive raw "
            "rows, and select canonical pivot columns from their restriction to G-0077 P"
        ),
        "exact_acceptance": (
            "solve the 229-square transpose system over Q and accept only through G-0077's "
            "production verifier on all 8107 columns plus nonzero exact target pairing"
        ),
        "failure_semantics": (
            "any sparse exact failure is inconclusive and falls back to full G-0077; modular "
            "zeros can conceal rationally nonzero dense coefficients"
        ),
        "claim_boundary": (
            "success proves rational/real nonmembership only for the frozen 8107-column, "
            "16738-row family; not an unrestricted ReLU lower bound"
        ),
        "controls": controls,
        "bindings": {
            "g0077_producer_sha256": EXPECTED_G0077_PRODUCER_SHA256,
            "g0077_preflight_sha256": EXPECTED_G0077_PREFLIGHT_SHA256,
            "g0077_modular_sha256": EXPECTED_G0077_MODULAR_SHA256,
            "full_matrix_raw_sha256": EXPECTED_FULL_SHA256,
        },
        "selected_rows_count": len(basis["selected_rows"]),
        "full_snapshot_read_only": not full.flags.writeable,
    }
    g0077.require_custody(custody)
    return {
        "schema": SCHEMA_PREFLIGHT,
        "scientific_payload": science,
        "scientific_payload_sha256": canonical_sha256(science),
        "script_sha256": custody[str(SCRIPT)],
        "environment": environment(),
        "seconds": time.time() - begun,
    }


def enforce_preflight() -> dict[str, Any]:
    report = read_gzip_json(G0078_PREFLIGHT)
    if (
        report.get("schema") != SCHEMA_PREFLIGHT
        or EXPECTED_PREFLIGHT_SCIENCE_SHA256 is None
        or report.get("scientific_payload_sha256")
        != EXPECTED_PREFLIGHT_SCIENCE_SHA256
        or canonical_sha256(report.get("scientific_payload"))
        != EXPECTED_PREFLIGHT_SCIENCE_SHA256
        or report.get("script_sha256") != sha256_path(SCRIPT)
    ):
        raise SparseLiftError("G-0078 preflight binding drift")
    return report


def exact_sparse_lift(output: Path, verify_block_columns: int) -> dict[str, Any]:
    begun = time.time()
    g0077 = load_g0077()
    custody = g0077.capture_custody(custody_paths(g0077, include_preflight=True))
    preflight = enforce_preflight()
    report, full, basis = load_bound_support(g0077)
    failing_row = int(report["first_mismatch_row"])
    failing_divisor = int(report["failing_row_primitive_divisor"])
    selection_started = time.time()
    sparse = select_sparse_square(
        g0077,
        full,
        basis["columns"],
        basis["selected_rows"],
        basis["selected_divisors"],
        failing_row,
        failing_divisor,
    )
    modular_coefficients = reconstruct_modular_dual(
        g0077, report, sparse, basis["support"]
    )
    selection_seconds = time.time() - selection_started

    conversion_started = time.time()
    square = fmpq_mat(
        SUPPORT_SIZE,
        SUPPORT_SIZE,
        memoryview(sparse["coefficient_square"].ravel()),
    )
    rhs = fmpq_mat(SUPPORT_SIZE, 1, memoryview(sparse["rhs"].ravel()))
    conversion_seconds = time.time() - conversion_started
    solve_started = time.time()
    solution = square.solve(rhs, algorithm="dixon")
    solve_seconds = time.time() - solve_started
    square_replay_started = time.time()
    if square * solution != rhs:
        raise SparseLiftError("229-square exact Dixon replay failed")
    square_replay_seconds = time.time() - square_replay_started
    numerator, denominator = solution.numer_denom()
    denominator_integer = int(denominator)
    if denominator_integer <= 0:
        raise SparseLiftError("nonpositive sparse common denominator")
    numerator_strings = [
        str(numerator[index, 0]) for index in range(SUPPORT_SIZE)
    ]

    verification_started = time.time()
    verification = g0077.verify_integer_certificate(
        full,
        basis["selected_rows"],
        basis["selected_divisors"],
        failing_row,
        failing_divisor,
        numerator_strings,
        denominator_integer,
        a_columns=A_COLUMNS,
        column_block=verify_block_columns,
    )
    verification_seconds = time.time() - verification_started
    mutant_index = next(
        (index for index, value in enumerate(numerator_strings) if int(value) != 0),
        0,
    )
    mutant_numerators = list(numerator_strings)
    mutant_numerators[mutant_index] = str(int(mutant_numerators[mutant_index]) + 1)
    mutant = g0077.verify_integer_certificate(
        full,
        basis["selected_rows"],
        basis["selected_divisors"],
        failing_row,
        failing_divisor,
        mutant_numerators,
        denominator_integer,
        a_columns=A_COLUMNS,
        column_block=verify_block_columns,
    )
    if mutant["accepted"]:
        raise SparseLiftError("one-unit sparse certificate mutant escaped verifier")

    certificate_gcd = denominator_integer
    for value in numerator_strings:
        certificate_gcd = math.gcd(certificate_gcd, abs(int(value)))
    if certificate_gcd != 1:
        raise SparseLiftError("sparse numerator/denominator certificate is not primitive")
    success = bool(verification["accepted"])
    scientific_payload = {
        "result": (
            "EXACT_SPARSE_LEFT_DUAL_FROZEN_FAMILY_OBSTRUCTION"
            if success
            else "INCONCLUSIVE_SPARSE_SUPPORT_LIFT_FAILED_EXACT_REPLAY"
        ),
        "theorem": (
            "MAX11 is not in the rational or real span of the frozen 8107-column Y-spoke "
            "family on the bound 16738-row system."
            if success
            else None
        ),
        "claim_boundary": (
            "success concerns only the frozen finite construction family; it is not an "
            "unrestricted two-hidden-layer ReLU lower bound"
        ),
        "failure_semantics": (
            None
            if success
            else "This sparse-support failure proves neither membership nor nonmembership; "
            "coefficients zero modulo the selected prime may be nonzero over Q, so the "
            "registered full G-0077 exact lift remains required."
        ),
        "support_size": SUPPORT_SIZE,
        "selected_support_positions": basis["support"].astype(int).tolist(),
        "selected_raw_rows": basis["selected_rows"].astype(int).tolist(),
        "selected_raw_row_divisors": basis["selected_divisors"].astype(int).tolist(),
        "failing_raw_row": failing_row,
        "failing_raw_row_divisor": failing_divisor,
        "selected_A_columns": sparse["selected_columns"].astype(int).tolist(),
        "integer_dual_numerators": numerator_strings,
        "integer_failing_row_weight": str(denominator_integer),
        "raw_row_weight_rule": (
            "selected raw-row weight i is numerator[i]/selected_raw_row_divisors[i]; "
            "failing raw-row weight is integer_failing_row_weight/failing_raw_row_divisor"
        ),
        "all_A_columns_annihilated_exactly": verification.get(
            "all_A_columns_annihilated_exactly", False
        ),
        "verified_A_columns": verification.get("verified_A_columns", 0),
        "first_exact_failure": verification.get("first_nonzero_A_column"),
        "exact_verifier_failure": verification.get("failure"),
        "exact_target_pairing": verification.get("exact_target_pairing"),
        "exact_target_pairing_nonzero": verification.get(
            "exact_target_pairing_nonzero", False
        ),
        "one_unit_mutant_rejected": not mutant["accepted"],
        "one_unit_mutant_failure": mutant.get("failure"),
        "certificate_gcd": certificate_gcd,
        "common_denominator_bits": denominator_integer.bit_length(),
        "max_abs_numerator_bits": max(
            abs(int(value)).bit_length() for value in numerator_strings
        ),
        "nonzero_numerator_weights": sum(
            int(value) != 0 for value in numerator_strings
        ),
    }
    result = {
        "schema": SCHEMA_EXACT,
        "scientific_payload": scientific_payload,
        "scientific_payload_sha256": canonical_sha256(scientific_payload),
        "modular_support_coefficients_sha256": g0077.raw_sha256(
            modular_coefficients
        ),
        "coefficient_square_int64_sha256": g0077.raw_sha256(
            sparse["coefficient_square"]
        ),
        "rhs_int64_sha256": g0077.raw_sha256(sparse["rhs"]),
        "g0077_modular_sha256": EXPECTED_G0077_MODULAR_SHA256,
        "preflight_sha256": custody[str(G0078_PREFLIGHT)],
        "preflight_science_sha256": preflight["scientific_payload_sha256"],
        "full_input_int64_sha256": EXPECTED_FULL_SHA256,
        "selection_seconds": selection_seconds,
        "conversion_seconds": conversion_seconds,
        "dixon_solve_seconds": solve_seconds,
        "square_replay_seconds": square_replay_seconds,
        "all_column_replay_seconds": verification_seconds,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "script_sha256": custody[str(SCRIPT)],
        "environment": environment(),
        "wall_seconds": time.time() - begun,
    }
    g0077.require_custody(custody)
    write_gzip_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--output", type=Path, required=True)
    exact = commands.add_parser("exact")
    exact.add_argument("--output", type=Path, required=True)
    exact.add_argument("--verify-block-columns", type=int, default=64)
    arguments = parser.parse_args()
    if arguments.command == "preflight":
        write_gzip_json(arguments.output, build_preflight())
    else:
        if not 1 <= arguments.verify_block_columns <= 256:
            parser.error("--verify-block-columns must lie in [1,256]")
        exact_sparse_lift(arguments.output, arguments.verify_block_columns)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
