#!/usr/bin/env python3
"""Lift the G-0076 modular separation to an exact left-dual certificate.

G-0076 found rank([A|b]) - rank(A) = 1 modulo 1,000,003 for the
complete frozen 16,738 by 8,108 augmented system.  This program selects a
canonical modular column/row basis, finds the first target-mismatch row, and
then solves the corresponding square transpose system over Q.

Only an exact all-column replay is theorem-bearing.  The modular result,
basis selection, sparse support, benchmarks, or successful Dixon solve are
never promoted on their own.
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
import sys
import time
from typing import Any, Iterable

from flint import fmpq_mat, fmpz_mat, nmod_mat
import flint
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
G0076 = ROOT / "artifacts/math/G-0076"
G0076_PRODUCER = G0076 / "target_aware_kernel_resolver.py"
G0076_PREFLIGHT = G0076 / "target_aware_kernel_preflight_v1.json.gz"
G0076_OUTCOME = G0076 / "target_aware_kernel_resolver_v1.json.gz"
G0076_KERNEL = G0076 / "target_aware_kernel_p1000003_v1.npy.gz"
G0076_CACHE_MANIFEST = G0076 / "cache/manifest.json"
FULL_CACHE = G0076 / "cache/full-N.npy"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"
G0077_PREFLIGHT = HERE / "exact_left_dual_preflight_v1.json.gz"

SCHEMA_PREFLIGHT = "max11-g0077-exact-left-dual-preflight-v1"
SCHEMA_MODULAR = "max11-g0077-canonical-modular-dual-v1"
SCHEMA_BENCHMARK = "max11-g0077-dixon-benchmark-v1"
SCHEMA_EXACT = "max11-g0077-exact-left-dual-v1"

PRIME = 1_000_003
ROWS = 16_738
A_COLUMNS = 8_107
AUGMENTED_COLUMNS = 8_108
RANK_A = 6_876
NULLITY = 1_231
MIN_AVAILABLE_GIB = 24.0

EXPECTED_G0076_PRODUCER_SHA256 = (
    "1499b96abb926d54d96f2b3163748f40dfd5810325424dbb41409a829213c4e2"
)
EXPECTED_G0076_PREFLIGHT_SHA256 = (
    "32970ecc3a6bd8ebe26169eeaad5120930e78c00be2bf204d4b21bdb86f4ce14"
)
EXPECTED_G0076_OUTCOME_SHA256 = (
    "374d684459c12e76184dfc1da50e8993b1d4dbda474c13ea4319665997570bfb"
)
EXPECTED_G0076_OUTCOME_SCIENCE_SHA256 = (
    "e074cdbf1818f0eaa0f8d649371bf5f669207e3e9590d7d9a834618ae1e76e15"
)
EXPECTED_G0076_KERNEL_GZIP_SHA256 = (
    "53b2e58fb6737132d2da4fab8980f98977e04f06f57853234e55f915fd277170"
)
EXPECTED_G0076_KERNEL_RAW_SHA256 = (
    "48285ef0851adf4035439c27eb68a90de8a97c1b9b2ceac5a6b8b63e91f9563d"
)
EXPECTED_HA_RAW_SHA256 = (
    "2cacedf021fe291dd0f19ba66f49f4c1d98dba6b922311a904654b66bb9c269d"
)
EXPECTED_KERNEL_PIVOTS_SHA256 = (
    "d64f759043785cebd3295c74ca5db8ccb72acc1ca21756dc9f57c55220cd8aac"
)
EXPECTED_FULL_SHA256 = (
    "41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095"
)
EXPECTED_CACHE_MANIFEST_SHA256 = (
    "48cfaaaab042ba93adebdcb0b964eec572c32e11906081c5c2cfdd67a89b17f0"
)
EXPECTED_ENVIRONMENT_SHA256 = (
    "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c"
)

# Filled after the outcome-blind exact-lift preflight is frozen and reviewed.
EXPECTED_PREFLIGHT_SCIENCE_SHA256: str | None = (
    "de58fc800430dcaaf151ca20bc37e6f379d942057b2dcf045162002b35073217"
)


class LiftError(RuntimeError):
    """A frozen binding, algebraic invariant, or exact replay failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise LiftError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray) -> str:
    value = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(value).cast("B")).hexdigest()


def stream_sha256(array: np.ndarray, row_block: int = 256) -> str:
    if array.ndim != 2:
        raise LiftError("stream hash requires a matrix")
    digest = hashlib.sha256()
    for start in range(0, array.shape[0], row_block):
        value = np.ascontiguousarray(array[start : start + row_block])
        digest.update(memoryview(value).cast("B"))
    return digest.hexdigest()


def capture_custody(paths: Iterable[Path]) -> dict[str, str]:
    return {str(path): sha256_path(path) for path in paths}


def require_custody(snapshot: dict[str, str]) -> None:
    observed = {path: sha256_path(Path(path)) for path in snapshot}
    if observed != snapshot:
        raise LiftError(
            f"input custody changed during execution: start={snapshot}, end={observed}"
        )


def fixed_subject_paths() -> list[Path]:
    return [
        SCRIPT,
        G0076_PRODUCER,
        G0076_PREFLIGHT,
        G0076_OUTCOME,
        G0076_KERNEL,
        G0076_CACHE_MANIFEST,
        ENVIRONMENT_MANIFEST,
    ]


def read_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise LiftError(f"expected JSON object: {path}")
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


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    raise LiftError("MemAvailable missing from /proc/meminfo")


def load_kernel() -> np.ndarray:
    if sha256_path(G0076_KERNEL) != EXPECTED_G0076_KERNEL_GZIP_SHA256:
        raise LiftError("archived G-0076 kernel gzip drift")
    with gzip.open(G0076_KERNEL, "rb") as source:
        kernel = np.load(source, allow_pickle=False)
    if kernel.shape != (NULLITY, AUGMENTED_COLUMNS) or kernel.dtype != np.uint32:
        raise LiftError("archived G-0076 kernel shape/dtype drift")
    if raw_sha256(kernel) != EXPECTED_G0076_KERNEL_RAW_SHA256:
        raise LiftError("archived G-0076 kernel raw hash drift")
    if np.any(kernel[:, -1]):
        raise LiftError("G-0076 target projection is unexpectedly nonzero")
    if raw_sha256(kernel[:, :-1]) != EXPECTED_HA_RAW_SHA256:
        raise LiftError("derived H_A hash drift")
    return kernel


def pivot_coordinates(rref: np.ndarray) -> list[int]:
    pivots: list[int] = []
    search = 0
    for row in rref:
        support = np.flatnonzero(row[search:])
        if support.size == 0:
            raise LiftError("RREF row has no pivot")
        pivot = search + int(support[0])
        pivots.append(pivot)
        search = pivot + 1
    if pivots != sorted(set(pivots)):
        raise LiftError("invalid RREF pivot order")
    return pivots


def load_bound_subject(*, verify_full_hash: bool = True) -> tuple[np.ndarray, dict[str, Any]]:
    bindings = {
        "g0076_producer_sha256": sha256_path(G0076_PRODUCER),
        "g0076_preflight_sha256": sha256_path(G0076_PREFLIGHT),
        "g0076_outcome_sha256": sha256_path(G0076_OUTCOME),
        "g0076_kernel_gzip_sha256": sha256_path(G0076_KERNEL),
        "g0076_cache_manifest_sha256": sha256_path(G0076_CACHE_MANIFEST),
        "environment_manifest_sha256": sha256_path(ENVIRONMENT_MANIFEST),
    }
    expected = {
        "g0076_producer_sha256": EXPECTED_G0076_PRODUCER_SHA256,
        "g0076_preflight_sha256": EXPECTED_G0076_PREFLIGHT_SHA256,
        "g0076_outcome_sha256": EXPECTED_G0076_OUTCOME_SHA256,
        "g0076_kernel_gzip_sha256": EXPECTED_G0076_KERNEL_GZIP_SHA256,
        "g0076_cache_manifest_sha256": EXPECTED_CACHE_MANIFEST_SHA256,
        "environment_manifest_sha256": EXPECTED_ENVIRONMENT_SHA256,
    }
    if bindings != expected:
        raise LiftError(f"frozen binding drift: observed={bindings}")
    outcome = read_gzip_json(G0076_OUTCOME)
    resolution = outcome.get("modular_resolution", {})
    if (
        outcome.get("scientific_payload_sha256") != EXPECTED_G0076_OUTCOME_SCIENCE_SHA256
        or outcome.get("decision") != "MODULAR_TARGET_SEPARATED_EXACT_STATUS_UNRESOLVED"
        or resolution.get("epsilon") != 1
        or resolution.get("rank_A") != RANK_A
        or resolution.get("rank_N") != RANK_A + 1
        or resolution.get("nullity_A") != NULLITY
        or resolution.get("nullity_N") != NULLITY
        or resolution.get("prime") != PRIME
        or resolution.get("full_input_augmented_int64_c_sha256") != EXPECTED_FULL_SHA256
    ):
        raise LiftError("G-0076 decision/science binding drift")
    kernel = load_kernel()
    pivots = pivot_coordinates(kernel[:, :-1])
    if (
        canonical_sha256(pivots) != EXPECTED_KERNEL_PIVOTS_SHA256
        or resolution.get("H_A", {}).get("rref_pivot_coordinates") != pivots
        or resolution.get("H_N", {}).get("rref_pivot_coordinates") != pivots
    ):
        raise LiftError("G-0076 kernel pivot drift")
    # Own an immutable in-memory snapshot.  A long exact run must not observe
    # a mixture of cache bytes if the ignored cache file changes concurrently.
    full = np.load(FULL_CACHE, allow_pickle=False)
    if full.shape != (ROWS, AUGMENTED_COLUMNS) or full.dtype != np.dtype("<i8"):
        raise LiftError("full G-0076 cache shape/dtype drift")
    if verify_full_hash and stream_sha256(full) != EXPECTED_FULL_SHA256:
        raise LiftError("full G-0076 cache raw hash drift")
    full.setflags(write=False)
    return full, {"bindings": bindings, "kernel_pivots": pivots}


def to_nmod(array: np.ndarray, prime: int = PRIME) -> tuple[nmod_mat, np.ndarray]:
    reduced = np.empty(array.shape, dtype=np.uint32)
    np.remainder(array, prime, out=reduced, casting="unsafe")
    field = nmod_mat(
        reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime
    )
    return field, reduced


def nmod_column_to_numpy(column: nmod_mat) -> np.ndarray:
    if column.ncols() != 1:
        raise LiftError("expected modular column vector")
    return np.fromiter(
        (int(column[index, 0]) for index in range(column.nrows())),
        dtype=np.int64,
        count=column.nrows(),
    )


def pivot_columns_from_field_rref(rref: nmod_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    search = 0
    for row in range(rank):
        while search < rref.ncols() and not int(rref[row, search]):
            search += 1
        if search == rref.ncols() or int(rref[row, search]) != 1:
            raise LiftError("field RREF pivot scan failed")
        pivots.append(search)
        search += 1
    return pivots


def primitive_divisors(full: np.ndarray, rows: np.ndarray, block: int = 64) -> np.ndarray:
    divisors = np.empty(len(rows), dtype=np.int64)
    for start in range(0, len(rows), block):
        stop = min(start + block, len(rows))
        values = np.ascontiguousarray(full[rows[start:stop], :])
        gcds = np.gcd.reduce(np.abs(values), axis=1)
        if np.any(gcds <= 0):
            raise LiftError("zero selected augmented row")
        if np.any(values % gcds[:, None]):
            raise LiftError("primitive row divisor failed exact division")
        divisors[start:stop] = gcds
    return divisors


def verify_integer_certificate(
    full: np.ndarray,
    rows: np.ndarray,
    divisors: np.ndarray,
    failing_row: int,
    failing_divisor: int,
    numerators: Iterable[int | str],
    denominator: int | str,
    *,
    a_columns: int | None = None,
    column_block: int = 64,
) -> dict[str, Any]:
    """Verify a serialized primitive-row dual using exact integer arithmetic.

    This is the single acceptance path used by production and hostile
    controls.  It recomputes every divisor from the raw augmented matrix
    before performing any division.
    """
    if full.ndim != 2 or full.shape[1] < 2:
        return {"accepted": False, "failure": "invalid-augmented-matrix"}
    candidate_columns = full.shape[1] - 1 if a_columns is None else a_columns
    if not 1 <= candidate_columns < full.shape[1]:
        return {"accepted": False, "failure": "invalid-column-census"}
    rows = np.asarray(rows, dtype=np.int64)
    divisors = np.asarray(divisors, dtype=np.int64)
    numerator_values = [int(value) for value in numerators]
    denominator_value = int(denominator)
    if (
        rows.ndim != 1
        or divisors.shape != rows.shape
        or len(numerator_values) != len(rows)
        or np.any(rows < 0)
        or np.any(rows >= full.shape[0])
        or len(set(map(int, rows))) != len(rows)
        or not isinstance(failing_row, int)
        or not 0 <= failing_row < full.shape[0]
        or failing_row in set(map(int, rows))
        or denominator_value <= 0
        or failing_divisor <= 0
        or column_block < 1
    ):
        return {"accepted": False, "failure": "invalid-certificate-census"}
    try:
        actual_divisors = primitive_divisors(full, rows)
        actual_failing_divisor = int(
            primitive_divisors(
                full, np.asarray([failing_row], dtype=np.int64)
            )[0]
        )
    except (LiftError, ValueError, OverflowError) as error:
        return {
            "accepted": False,
            "failure": "primitive-divisor-recomputation-failed",
            "detail": str(error),
        }
    if not np.array_equal(divisors, actual_divisors):
        return {"accepted": False, "failure": "basis-divisor-mismatch"}
    if failing_divisor != actual_failing_divisor:
        return {"accepted": False, "failure": "failing-divisor-mismatch"}

    numerator_column = fmpz_mat(len(rows), 1, numerator_values)
    numerator_row = numerator_column.transpose()
    verified_columns = 0
    first_nonzero: dict[str, Any] | None = None
    for start in range(0, candidate_columns, column_block):
        stop = min(start + column_block, candidate_columns)
        selected = np.arange(start, stop, dtype=np.int64)
        raw_block = np.ascontiguousarray(full[np.ix_(rows, selected)])
        primitive_block = np.ascontiguousarray(raw_block // divisors[:, None])
        failing_block = np.ascontiguousarray(
            full[failing_row, start:stop] // failing_divisor
        )
        residual = numerator_row * fmpz_mat(
            len(rows), stop - start, memoryview(primitive_block.ravel())
        )
        for local in range(stop - start):
            value = residual[0, local] + denominator_value * int(
                failing_block[local]
            )
            if value:
                first_nonzero = {
                    "column": start + local,
                    "residual_numerator": str(value),
                }
                break
        if first_nonzero is not None:
            break
        verified_columns = stop

    primitive_target = np.ascontiguousarray(
        full[rows, candidate_columns] // divisors
    )
    failing_target = int(full[failing_row, candidate_columns] // failing_divisor)
    target_pairing = sum(
        numerator_values[index] * int(primitive_target[index])
        for index in range(len(rows))
    ) + denominator_value * failing_target
    all_columns_zero = first_nonzero is None
    return {
        "accepted": all_columns_zero and target_pairing != 0,
        "failure": (
            None
            if all_columns_zero and target_pairing != 0
            else "nonzero-A-column-residual"
            if first_nonzero is not None
            else "zero-target-pairing"
        ),
        "all_A_columns_annihilated_exactly": all_columns_zero,
        "verified_A_columns": verified_columns,
        "first_nonzero_A_column": first_nonzero,
        "exact_target_pairing": str(target_pairing),
        "exact_target_pairing_nonzero": target_pairing != 0,
    }


def modular_vector_replay(
    full: np.ndarray,
    rows: np.ndarray,
    divisors: np.ndarray,
    failing_row: int,
    failing_divisor: int,
    coefficients: np.ndarray,
    *,
    column_block: int = 64,
) -> tuple[bool, int | None]:
    for start in range(0, A_COLUMNS, column_block):
        stop = min(start + column_block, A_COLUMNS)
        columns = np.arange(start, stop, dtype=np.intp)
        raw = np.ascontiguousarray(full[np.ix_(rows, columns)])
        primitive = raw // divisors[:, None]
        reduced = np.remainder(primitive, PRIME).astype(np.int64, copy=False)
        failing = np.remainder(
            np.ascontiguousarray(full[failing_row, start:stop]) // failing_divisor,
            PRIME,
        ).astype(np.int64, copy=False)
        residual = (coefficients @ reduced + failing) % PRIME
        support = np.flatnonzero(residual)
        if support.size:
            return False, start + int(support[0])
    return True, None


def run_controls() -> dict[str, Any]:
    # A genuinely exact planted certificate, checked by the production verifier.
    valid_full = np.asarray([[1, 0], [1, 1]], dtype=np.int64)
    valid = verify_integer_certificate(
        valid_full,
        np.asarray([0]),
        np.asarray([1]),
        1,
        1,
        [-1],
        1,
    )
    if not valid["accepted"]:
        raise LiftError(f"planted exact left-dual control failed: {valid}")

    # Here b is in span_Q(A), but modulo p the target adds rank because the
    # first A column vanishes.  The modular dual must fail exact replay.
    exceptional_full = np.asarray(
        [[PRIME, 0, 1], [0, 1, 0]], dtype=np.int64
    )
    exceptional_a = exceptional_full[:, :2]
    exceptional_n = exceptional_full
    modular_rank_a = int(nmod_mat(exceptional_a.tolist(), PRIME).rank())
    modular_rank_n = int(nmod_mat(exceptional_n.tolist(), PRIME).rank())
    exceptional = verify_integer_certificate(
        exceptional_full,
        np.asarray([1]),
        np.asarray([1]),
        0,
        1,
        [0],
        1,
    )
    if modular_rank_n - modular_rank_a != 1 or exceptional["accepted"]:
        raise LiftError(
            f"exceptional-prime false-separation control failed: {exceptional}"
        )

    nondivisor = verify_integer_certificate(
        valid_full,
        np.asarray([0]),
        np.asarray([2]),
        1,
        1,
        [-1],
        1,
    )
    if nondivisor["accepted"] or nondivisor["failure"] != "basis-divisor-mismatch":
        raise LiftError(f"false primitive divisor escaped control: {nondivisor}")

    mutated = verify_integer_certificate(
        valid_full,
        np.asarray([0]),
        np.asarray([1]),
        1,
        1,
        [0],
        1,
    )
    if mutated["accepted"]:
        raise LiftError(f"coefficient mutant escaped control: {mutated}")
    return {
        "planted_exact_dual_all_columns_zero": True,
        "planted_exact_dual_target_pairing_nonzero": True,
        "exceptional_prime_false_separation_detected_by_exact_replay": True,
        "false_primitive_divisor_rejected": True,
        "coefficient_plus_one_mutant_rejected": True,
        "modular_results_never_promoted": True,
        "production_certificate_verifier_exercised": True,
    }


def build_preflight() -> dict[str, Any]:
    begun = time.time()
    custody = capture_custody(fixed_subject_paths())
    full, subject = load_bound_subject(verify_full_hash=True)
    controls = run_controls()
    science = {
        "branch": "G-0076 epsilon=1 exact left-dual branch",
        "subject_shape": list(full.shape),
        "A_columns": A_COLUMNS,
        "rank_A_mod_registered_prime": RANK_A,
        "prime": PRIME,
        "basis_policy": (
            "P is the complement of canonical H_A pivots; R is the canonical pivot-column "
            "set of RREF(A[:,P]^T mod p); s is the first target mismatch in row order"
        ),
        "normalization": "divide every selected augmented row by its exact positive row gcd",
        "exact_acceptance": (
            "serialize integer numerator weights U and denominator weight d; require "
            "U^T A'_R + d A'_s = 0 on all 8107 columns and nonzero exact target pairing"
        ),
        "claim_boundary": (
            "success rejects only the frozen 8107-column family on the bound finite row system; "
            "it is not an unrestricted ReLU lower bound"
        ),
        "fallback": (
            "any exact replay failure classifies the registered prime as exceptional for this "
            "lift and leaves characteristic-zero status unresolved"
        ),
        "controls": controls,
        "bindings": subject["bindings"],
    }
    require_custody(custody)
    return {
        "schema": SCHEMA_PREFLIGHT,
        "scientific_payload": science,
        "scientific_payload_sha256": canonical_sha256(science),
        "script_sha256": custody[str(SCRIPT)],
        "environment": environment(),
        "seconds": time.time() - begun,
    }


def enforce_preflight(path: Path) -> dict[str, Any]:
    report = read_gzip_json(path)
    if report.get("schema") != SCHEMA_PREFLIGHT:
        raise LiftError("G-0077 preflight schema drift")
    observed = report.get("scientific_payload_sha256")
    if EXPECTED_PREFLIGHT_SCIENCE_SHA256 is None:
        raise LiftError("producer is not frozen to an outcome-blind preflight")
    if observed != EXPECTED_PREFLIGHT_SCIENCE_SHA256:
        raise LiftError(f"G-0077 preflight science drift: {observed}")
    if canonical_sha256(report.get("scientific_payload")) != observed:
        raise LiftError("G-0077 preflight payload is not self-authenticating")
    if report.get("script_sha256") != sha256_path(SCRIPT):
        raise LiftError("G-0077 preflight was not produced by the executing script")
    return report


def canonical_modular_dual(preflight_path: Path, output: Path) -> dict[str, Any]:
    begun = time.time()
    custody = capture_custody([*fixed_subject_paths(), preflight_path])
    preflight = enforce_preflight(preflight_path)
    full, subject = load_bound_subject(verify_full_hash=True)
    kernel = load_kernel()
    kernel_pivots = pivot_coordinates(kernel[:, :-1])
    pivot_set = set(kernel_pivots)
    basis_columns = np.asarray(
        [column for column in range(A_COLUMNS) if column not in pivot_set],
        dtype=np.int64,
    )
    if basis_columns.shape != (RANK_A,):
        raise LiftError("canonical A-column basis census drift")

    print("G0077_ROW_BASIS_RREF begin", file=sys.stderr, flush=True)
    selection_started = time.time()
    transposed = np.empty((RANK_A, ROWS), dtype=np.uint32)
    for start in range(0, ROWS, 64):
        stop = min(start + 64, ROWS)
        raw = np.ascontiguousarray(full[start:stop, :A_COLUMNS][:, basis_columns])
        transposed[:, start:stop] = np.remainder(raw, PRIME).astype(
            np.uint32, copy=False
        ).T
    field = nmod_mat(RANK_A, ROWS, memoryview(transposed.ravel()), PRIME)
    del transposed
    reduced, rank_object = field.rref()
    del field
    rank = int(rank_object)
    if rank != RANK_A:
        raise LiftError(f"canonical column basis has row rank only {rank}")
    basis_rows = np.asarray(
        pivot_columns_from_field_rref(reduced, rank), dtype=np.int64
    )
    del reduced
    if basis_rows.shape != (RANK_A,) or len(set(map(int, basis_rows))) != RANK_A:
        raise LiftError("canonical row basis census drift")
    selection_seconds = time.time() - selection_started

    divisors = primitive_divisors(full, basis_rows)
    raw_square = np.ascontiguousarray(
        full[np.ix_(basis_rows, basis_columns)]
    )
    primitive_square = np.ascontiguousarray(raw_square // divisors[:, None])
    raw_rhs = np.ascontiguousarray(full[basis_rows, A_COLUMNS])
    primitive_rhs = np.ascontiguousarray(raw_rhs // divisors)
    square_field, square_reduced = to_nmod(primitive_square)
    if int(square_field.rank()) != RANK_A:
        raise LiftError("primitive square lost modular rank")
    rhs_field, rhs_reduced = to_nmod(primitive_rhs.reshape(-1, 1))
    coordinates_field = square_field.solve(rhs_field)
    coordinates = nmod_column_to_numpy(coordinates_field)
    del rhs_field, rhs_reduced, coordinates_field

    mismatch_row: int | None = None
    mismatch_residual: int | None = None
    for start in range(0, ROWS, 64):
        stop = min(start + 64, ROWS)
        raw = np.ascontiguousarray(full[start:stop, :A_COLUMNS][:, basis_columns])
        reduced_block = np.remainder(raw, PRIME).astype(np.int64, copy=False)
        predicted = (reduced_block @ coordinates) % PRIME
        target = np.remainder(
            np.ascontiguousarray(full[start:stop, A_COLUMNS]), PRIME
        ).astype(np.int64, copy=False)
        residual = (predicted - target) % PRIME
        support = np.flatnonzero(residual)
        if support.size:
            mismatch_row = start + int(support[0])
            mismatch_residual = int(residual[int(support[0])])
            break
    if mismatch_row is None or mismatch_residual in (None, 0):
        raise LiftError("epsilon=1 branch did not expose a target mismatch")
    if mismatch_row in set(map(int, basis_rows)):
        raise LiftError("square-basis row is a target mismatch")

    failing_divisor = int(primitive_divisors(full, np.asarray([mismatch_row]))[0])
    failing_basis = np.ascontiguousarray(
        full[mismatch_row, basis_columns] // failing_divisor
    )
    negative_field, negative_reduced = to_nmod((-failing_basis).reshape(-1, 1))
    dual_field = square_field.transpose().solve(negative_field)
    dual = nmod_column_to_numpy(dual_field)
    del negative_field, negative_reduced, dual_field
    modular_zero, first_bad_column = modular_vector_replay(
        full,
        basis_rows,
        divisors,
        mismatch_row,
        failing_divisor,
        dual,
    )
    if not modular_zero:
        raise LiftError(f"canonical modular dual fails column {first_bad_column}")
    primitive_target = primitive_rhs
    failing_target = int(full[mismatch_row, A_COLUMNS] // failing_divisor)
    replay_bound = (
        RANK_A * (PRIME - 1) * (PRIME - 1) + (PRIME - 1)
    )
    if replay_bound >= np.iinfo(np.int64).max:
        raise LiftError("modular int64 replay bound is unsafe")
    target_dot = int(dual @ np.remainder(primitive_target, PRIME))
    if not 0 <= target_dot <= RANK_A * (PRIME - 1) * (PRIME - 1):
        raise LiftError("observed modular target dot product violates overflow bound")
    failing_target_mod = failing_target % PRIME
    target_pairing_mod = (target_dot + failing_target_mod) % PRIME
    if target_pairing_mod == 0:
        raise LiftError("canonical modular dual has zero target pairing")
    support = np.flatnonzero(dual).astype(int).tolist()
    if not support:
        raise LiftError("empty modular dual support")

    del square_field, square_reduced, raw_square
    report = {
        "schema": SCHEMA_MODULAR,
        "result": "MODULAR_LEFT_DUAL_EXACT_STATUS_UNRESOLVED",
        "claim_boundary": (
            "finite-field discovery object only; exact all-column replay is required"
        ),
        "prime": PRIME,
        "rank_A": RANK_A,
        "rows": ROWS,
        "A_columns": A_COLUMNS,
        "basis_columns": basis_columns.astype(int).tolist(),
        "basis_rows": basis_rows.astype(int).tolist(),
        "basis_columns_sha256": raw_sha256(basis_columns),
        "basis_rows_sha256": raw_sha256(basis_rows),
        "primitive_row_divisors": divisors.astype(int).tolist(),
        "primitive_row_divisors_sha256": raw_sha256(divisors),
        "primitive_square_int64_sha256": raw_sha256(primitive_square),
        "primitive_square_max_abs_entry": int(np.max(np.abs(primitive_square))),
        "primitive_square_density": float(np.count_nonzero(primitive_square) / primitive_square.size),
        "primitive_rhs_int64_sha256": raw_sha256(primitive_rhs),
        "target_coordinates_mod_prime_sha256": raw_sha256(coordinates),
        "first_mismatch_row": mismatch_row,
        "first_mismatch_residual_mod_prime": mismatch_residual,
        "failing_row_primitive_divisor": failing_divisor,
        "failing_basis_row_int64_sha256": raw_sha256(failing_basis),
        "dual_coefficients_mod_prime_sha256": raw_sha256(dual),
        "dual_support": support,
        "dual_support_size": len(support),
        "dual_support_sha256": canonical_sha256(support),
        "all_A_columns_annihilated_mod_prime": True,
        "target_pairing_mod_prime": target_pairing_mod,
        "int64_replay_absolute_bound": replay_bound,
        "selection_seconds": selection_seconds,
        "preflight_sha256": sha256_path(preflight_path),
        "preflight_science_sha256": preflight["scientific_payload_sha256"],
        "full_input_int64_sha256": EXPECTED_FULL_SHA256,
        **subject,
        "script_sha256": custody[str(SCRIPT)],
        "environment": environment(),
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "wall_seconds": time.time() - begun,
    }
    require_custody(custody)
    write_gzip_json(output, report)
    return report


def load_modular_report(path: Path) -> tuple[dict[str, Any], np.ndarray, dict[str, Any]]:
    report = read_gzip_json(path)
    preflight = enforce_preflight(G0077_PREFLIGHT)
    live_script_sha256 = sha256_path(SCRIPT)
    live_preflight_sha256 = sha256_path(G0077_PREFLIGHT)
    if (
        report.get("schema") != SCHEMA_MODULAR
        or report.get("result") != "MODULAR_LEFT_DUAL_EXACT_STATUS_UNRESOLVED"
        or report.get("prime") != PRIME
        or report.get("rank_A") != RANK_A
        or report.get("all_A_columns_annihilated_mod_prime") is not True
        or not report.get("target_pairing_mod_prime")
        or report.get("script_sha256") != live_script_sha256
        or report.get("preflight_sha256") != live_preflight_sha256
        or report.get("preflight_science_sha256")
        != EXPECTED_PREFLIGHT_SCIENCE_SHA256
        or preflight.get("scientific_payload_sha256")
        != EXPECTED_PREFLIGHT_SCIENCE_SHA256
        or report.get("full_input_int64_sha256") != EXPECTED_FULL_SHA256
    ):
        raise LiftError("modular-dual report decision drift")
    full, subject = load_bound_subject(verify_full_hash=True)
    if report.get("bindings") != subject["bindings"]:
        raise LiftError("modular-dual subject binding drift")
    rows = np.asarray(report.get("basis_rows"), dtype=np.int64)
    columns = np.asarray(report.get("basis_columns"), dtype=np.int64)
    divisors = np.asarray(report.get("primitive_row_divisors"), dtype=np.int64)
    if rows.shape != (RANK_A,) or columns.shape != (RANK_A,) or divisors.shape != (RANK_A,):
        raise LiftError("modular-dual basis census drift")
    if (
        np.any(rows < 0)
        or np.any(rows >= ROWS)
        or len(set(map(int, rows))) != RANK_A
        or rows.astype(int).tolist() != sorted(map(int, rows))
        or np.any(columns < 0)
        or np.any(columns >= A_COLUMNS)
        or len(set(map(int, columns))) != RANK_A
        or columns.astype(int).tolist() != sorted(map(int, columns))
    ):
        raise LiftError("modular-dual basis indices are invalid or noncanonical")
    expected_columns = [
        column
        for column in range(A_COLUMNS)
        if column not in set(subject["kernel_pivots"])
    ]
    if columns.astype(int).tolist() != expected_columns:
        raise LiftError("modular-dual A-column basis is not bound to the live kernel")
    if (
        raw_sha256(rows) != report.get("basis_rows_sha256")
        or raw_sha256(columns) != report.get("basis_columns_sha256")
        or raw_sha256(divisors) != report.get("primitive_row_divisors_sha256")
    ):
        raise LiftError("modular-dual basis hash drift")
    recomputed_divisors = primitive_divisors(full, rows)
    if not np.array_equal(divisors, recomputed_divisors):
        raise LiftError("reported primitive row divisors differ from frozen raw rows")
    failing_row = report.get("first_mismatch_row")
    if (
        not isinstance(failing_row, int)
        or not 0 <= failing_row < ROWS
        or failing_row in set(map(int, rows))
    ):
        raise LiftError("invalid modular-dual failing row")
    recomputed_failing_divisor = int(
        primitive_divisors(full, np.asarray([failing_row], dtype=np.int64))[0]
    )
    if report.get("failing_row_primitive_divisor") != recomputed_failing_divisor:
        raise LiftError("reported failing-row divisor differs from frozen raw row")
    primitive_square = np.ascontiguousarray(
        full[np.ix_(rows, columns)] // recomputed_divisors[:, None]
    )
    primitive_rhs = np.ascontiguousarray(
        full[rows, A_COLUMNS] // recomputed_divisors
    )
    failing_basis = np.ascontiguousarray(
        full[failing_row, columns] // recomputed_failing_divisor
    )
    if (
        raw_sha256(primitive_square) != report.get("primitive_square_int64_sha256")
        or raw_sha256(primitive_rhs) != report.get("primitive_rhs_int64_sha256")
        or raw_sha256(failing_basis) != report.get("failing_basis_row_int64_sha256")
    ):
        raise LiftError("reported primitive square/RHS/failing-row hash drift")
    return report, full, {"rows": rows, "columns": columns, "divisors": divisors}


def select_benchmark_square(
    full: np.ndarray,
    rows: np.ndarray,
    basis_columns: np.ndarray,
    divisors: np.ndarray,
    failing_row: int,
    failing_divisor: int,
    size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    selected_rows = rows[:size]
    raw = np.ascontiguousarray(full[np.ix_(selected_rows, basis_columns)])
    primitive = np.ascontiguousarray(raw // divisors[:size, None])
    field, reduced = to_nmod(primitive)
    rref, rank_object = field.rref()
    del field, reduced
    rank = int(rank_object)
    if rank != size:
        raise LiftError(f"first {size} selected primitive rows have rank {rank}")
    local_columns = np.asarray(
        pivot_columns_from_field_rref(rref, rank), dtype=np.int64
    )
    del rref
    columns = np.ascontiguousarray(basis_columns[local_columns])
    square = np.ascontiguousarray(primitive[:, local_columns].T)
    rhs = np.ascontiguousarray(
        -(full[failing_row, columns] // failing_divisor)
    )
    return square, rhs, columns


def benchmark_dixon(modular_path: Path, size: int, output: Path) -> dict[str, Any]:
    begun = time.time()
    custody = capture_custody(
        [*fixed_subject_paths(), G0077_PREFLIGHT, modular_path]
    )
    available_at_start = mem_available_gib()
    report, full, basis = load_modular_report(modular_path)
    if not 1 <= size <= RANK_A:
        raise LiftError(f"benchmark size outside 1..{RANK_A}")
    failing_row = int(report["first_mismatch_row"])
    failing_divisor = int(report["failing_row_primitive_divisor"])
    selection_started = time.time()
    square_integer, rhs_integer, columns = select_benchmark_square(
        full,
        basis["rows"],
        basis["columns"],
        basis["divisors"],
        failing_row,
        failing_divisor,
        size,
    )
    selection_seconds = time.time() - selection_started
    conversion_started = time.time()
    square = fmpq_mat(size, size, memoryview(square_integer.ravel()))
    rhs = fmpq_mat(size, 1, memoryview(rhs_integer.ravel()))
    conversion_seconds = time.time() - conversion_started
    solve_started = time.time()
    solution = square.solve(rhs, algorithm="dixon")
    solve_seconds = time.time() - solve_started
    replay_started = time.time()
    if square * solution != rhs:
        raise LiftError("Dixon benchmark square replay failed")
    replay_seconds = time.time() - replay_started
    numerator, denominator = solution.numer_denom()
    result = {
        "schema": SCHEMA_BENCHMARK,
        "result": "EXACT_SUBSYSTEM_RESOURCE_BENCHMARK_ONLY",
        "claim_boundary": "resource forecast only; not a full-system certificate",
        "size": size,
        "full_size": RANK_A,
        "benchmark_columns": columns.astype(int).tolist(),
        "square_int64_sha256": raw_sha256(square_integer),
        "rhs_int64_sha256": raw_sha256(rhs_integer),
        "solution_common_denominator_bits": abs(int(denominator)).bit_length(),
        "solution_max_abs_numerator_bits": max(
            abs(int(numerator[index, 0])).bit_length() for index in range(size)
        ),
        "selection_seconds": selection_seconds,
        "conversion_seconds": conversion_seconds,
        "dixon_solve_seconds": solve_seconds,
        "square_replay_seconds": replay_seconds,
        "modular_report_sha256": custody[str(modular_path)],
        "script_sha256": custody[str(SCRIPT)],
        "available_gib_at_start": available_at_start,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "wall_seconds": time.time() - begun,
    }
    require_custody(custody)
    write_gzip_json(output, result)
    return result


def exact_left_dual(
    modular_path: Path,
    output: Path,
    minimum_available_gib: float,
    verify_block_columns: int,
) -> dict[str, Any]:
    custody = capture_custody(
        [*fixed_subject_paths(), G0077_PREFLIGHT, modular_path]
    )
    if (
        not math.isfinite(minimum_available_gib)
        or minimum_available_gib < MIN_AVAILABLE_GIB
    ):
        raise LiftError(
            f"minimum available memory must be finite and at least {MIN_AVAILABLE_GIB:.1f} GiB"
        )
    available = mem_available_gib()
    if available < minimum_available_gib:
        raise MemoryError(
            f"refusing exact lift with {available:.2f} GiB available; "
            f"minimum is {minimum_available_gib:.2f} GiB"
        )
    begun = time.time()
    report, full, basis = load_modular_report(modular_path)
    rows = basis["rows"]
    columns = basis["columns"]
    divisors = basis["divisors"]
    failing_row = int(report["first_mismatch_row"])
    failing_divisor = int(report["failing_row_primitive_divisor"])
    primitive_square = np.ascontiguousarray(
        full[np.ix_(rows, columns)] // divisors[:, None]
    )
    failing_basis = np.ascontiguousarray(
        full[failing_row, columns] // failing_divisor
    )
    if (
        raw_sha256(primitive_square) != report.get("primitive_square_int64_sha256")
        or raw_sha256(failing_basis) != report.get("failing_basis_row_int64_sha256")
    ):
        raise LiftError("exact-lift square/failing-row binding drift")
    coefficient_integer = np.ascontiguousarray(primitive_square.T)
    rhs_integer = np.ascontiguousarray(-failing_basis)
    conversion_started = time.time()
    square = fmpq_mat(
        RANK_A, RANK_A, memoryview(coefficient_integer.ravel())
    )
    rhs = fmpq_mat(RANK_A, 1, memoryview(rhs_integer.ravel()))
    conversion_seconds = time.time() - conversion_started
    print(
        f"G0077_DIXON begin size={RANK_A} available_gib={available:.2f}",
        file=sys.stderr,
        flush=True,
    )
    solve_started = time.time()
    solution = square.solve(rhs, algorithm="dixon")
    solve_seconds = time.time() - solve_started
    square_replay_started = time.time()
    if square * solution != rhs:
        raise LiftError("exact Dixon solution failed square replay")
    square_replay_seconds = time.time() - square_replay_started
    numerator, denominator = solution.numer_denom()
    denominator_integer = int(denominator)
    if denominator_integer <= 0:
        raise LiftError("nonpositive common denominator")

    verification_started = time.time()
    numerator_strings = [str(numerator[index, 0]) for index in range(RANK_A)]
    verification = verify_integer_certificate(
        full,
        rows,
        divisors,
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
    mutant_verification = verify_integer_certificate(
        full,
        rows,
        divisors,
        failing_row,
        failing_divisor,
        mutant_numerators,
        denominator_integer,
        a_columns=A_COLUMNS,
        column_block=verify_block_columns,
    )
    mutant_rejected = not mutant_verification["accepted"]
    if not mutant_rejected:
        raise LiftError("one-unit serialized certificate mutant escaped full verifier")

    certificate_gcd = abs(denominator_integer)
    for value in numerator_strings:
        certificate_gcd = math.gcd(certificate_gcd, abs(int(value)))
    if certificate_gcd != 1:
        raise LiftError("FLINT numerator/denominator certificate is not primitive")

    success = bool(verification["accepted"])
    result = {
        "schema": SCHEMA_EXACT,
        "result": (
            "EXACT_LEFT_DUAL_FROZEN_FAMILY_OBSTRUCTION"
            if success
            else "MODULAR_SEPARATION_FAILED_EXACT_REPLAY"
        ),
        "theorem": (
            "The MAX11 target is not in the rational or real span of the frozen 8107-column "
            "Y-spoke construction family on the bound 16738-row system."
            if success
            else None
        ),
        "claim_boundary": (
            "Even on success this rejects only the frozen finite construction family; it is "
            "not an unrestricted two-hidden-layer ReLU lower bound."
        ),
        "rank": RANK_A,
        "rows": ROWS,
        "A_columns": A_COLUMNS,
        "basis_rows": rows.astype(int).tolist(),
        "failing_row": failing_row,
        "primitive_basis_row_divisors": divisors.astype(int).tolist(),
        "primitive_failing_row_divisor": failing_divisor,
        "raw_row_weight_rule": (
            "basis raw-row weight i is integer_dual_numerators[i] / "
            "primitive_basis_row_divisors[i]; failing raw-row weight is "
            "integer_failing_row_weight / primitive_failing_row_divisor"
        ),
        "integer_dual_numerators": numerator_strings,
        "integer_failing_row_weight": str(denominator_integer),
        "certificate_gcd": certificate_gcd,
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
        "coefficient_plus_one_mutant_rejected": bool(mutant_rejected),
        "coefficient_plus_one_mutant_verifier_failure": mutant_verification.get(
            "failure"
        ),
        "common_denominator_bits": denominator_integer.bit_length(),
        "max_abs_numerator_bits": max(abs(int(value)).bit_length() for value in numerator_strings),
        "nonzero_numerator_weights": sum(int(value) != 0 for value in numerator_strings),
        "modular_report_sha256": custody[str(modular_path)],
        "preflight_sha256": report["preflight_sha256"],
        "preflight_science_sha256": report["preflight_science_sha256"],
        "full_input_int64_sha256": EXPECTED_FULL_SHA256,
        "conversion_seconds": conversion_seconds,
        "dixon_solve_seconds": solve_seconds,
        "square_replay_seconds": square_replay_seconds,
        "all_column_replay_seconds": verification_seconds,
        "available_gib_at_start": available,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "script_sha256": custody[str(SCRIPT)],
        "environment": environment(),
        "wall_seconds": time.time() - begun,
    }
    require_custody(custody)
    write_gzip_json(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight")
    preflight.add_argument("--output", type=Path, required=True)
    modular = commands.add_parser("modular")
    modular.add_argument("--preflight", type=Path, required=True)
    modular.add_argument("--output", type=Path, required=True)
    benchmark = commands.add_parser("benchmark")
    benchmark.add_argument("--modular-report", type=Path, required=True)
    benchmark.add_argument("--size", type=int, required=True)
    benchmark.add_argument("--output", type=Path, required=True)
    exact = commands.add_parser("exact")
    exact.add_argument("--modular-report", type=Path, required=True)
    exact.add_argument("--output", type=Path, required=True)
    exact.add_argument("--minimum-available-gib", type=float, default=MIN_AVAILABLE_GIB)
    exact.add_argument("--verify-block-columns", type=int, default=32)
    args = parser.parse_args()

    if args.command == "preflight":
        write_gzip_json(args.output, build_preflight())
    elif args.command == "modular":
        canonical_modular_dual(args.preflight, args.output)
    elif args.command == "benchmark":
        benchmark_dixon(args.modular_report, args.size, args.output)
    else:
        if not 1 <= args.verify_block_columns <= 256:
            parser.error("--verify-block-columns must lie in [1,256]")
        exact_left_dual(
            args.modular_report,
            args.output,
            args.minimum_available_gib,
            args.verify_block_columns,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
