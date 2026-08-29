#!/usr/bin/env python3
"""Independent adversarial replay of the G-0050 exact-Q bridge.

The script reimplements the complete degree-three direction universe, fails on
any generated hinge outside it, rebuilds all 3,310 columns, independently
extracts the fixed solve rows modulo p, and replays every proper column and
the three seed residuals over Q.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from itertools import combinations
import gzip
import hashlib
import importlib.util
import json
from math import factorial, gcd
import multiprocessing as mp
from pathlib import Path
import sys
from typing import Any, Iterator

from flint import fmpq_mat, fmpz_mat
import numpy as np


ROOT = Path(__file__).resolve().parents[3]
SUBJECT = ROOT / "artifacts/math/G-0050/exact_q_bridge.py"
SUBJECT_REPORT = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"
EXTRACT_SCRIPT = ROOT / "artifacts/math/G-0047/low_mass_quotient_extract.py"
EXTRACT_REPORT = ROOT / "artifacts/math/G-0047/low_mass_quotient_extract_v1.json.gz"
SEARCH_SCRIPT = ROOT / "artifacts/math/G-0047/low_mass_circuit_search.py"
G47_SCRIPT = ROOT / "artifacts/math/G-0047/induction_span_obstruction.py"

EXPECTED = {
    SUBJECT: "b82fbb6df487b0e76a4bbefc695960b9f1a87ef25a9e8e33b26f07d02433f27b",
    EXTRACT_SCRIPT: "55077ec87d8e49f71c93c484dd7fc0ad75962d25baa05af93d61e0e0e3d3c9d6",
    SEARCH_SCRIPT: "2c28663459755f631c44e2444be4c2540ae9772c26c542c7c9807e63eeee10fd",
    G47_SCRIPT: "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d",
}
N_ROWS = 10_065
N_PROPER = 3_307
N_ALL = 3_310
N_BASIS = 488
PRIMES = (1_000_003, 1_000_033)

AUDIT_G47: Any = None
AUDIT_ROW_INDEX: dict[tuple[int, ...], int] = {}


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


def load_module(name: str, path: Path) -> Any:
    expected = EXPECTED.get(path)
    if expected is not None and sha256_path(path) != expected:
        raise ValueError(f"input drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def load_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def bar_compositions(total: int, parts: int) -> Iterator[tuple[int, ...]]:
    """Stars-and-bars implementation independent of the producer recursion."""

    slots = total + parts - 1
    for bars in combinations(range(slots), parts - 1):
        previous = -1
        values = []
        for bar in bars:
            values.append(bar - previous - 1)
            previous = bar
        values.append(slots - previous - 1)
        yield tuple(values)


def independent_direction_universe(n: int = 11, degree: int = 3) -> tuple[tuple[int, ...], ...]:
    compositions = tuple(bar_compositions(degree, n))
    directions: set[tuple[int, ...]] = set()
    for index, left in enumerate(compositions):
        for right in compositions[index + 1 :]:
            direction = tuple(b - a for a, b in zip(left, right, strict=True))
            first = next(value for value in direction if value)
            if first < 0:
                direction = tuple(-value for value in direction)
            divisor = gcd(*(abs(value) for value in direction))
            primitive = tuple(value // divisor for value in direction)
            prefix = 0
            nonpositive = True
            for value in primitive[:-1]:
                prefix += value
                if prefix < 0:
                    nonpositive = False
                    break
            if not nonpositive:
                directions.add(primitive)
    result = tuple(sorted(directions))
    if len(result) != N_ROWS:
        raise AssertionError(f"independent row universe has {len(result)} rows")
    return result


def independent_records(g47: Any) -> list[dict[str, Any]]:
    records = []
    if sha256_path(g47.SIGNED_STREAM) != g47.EXPECTED_SIGNED_STREAM_HASH:
        raise ValueError("signed stream drift")
    with gzip.open(g47.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise ValueError("signed stream header missing")
        for line in source:
            record = json.loads(line)
            mass = int(record["signed_mass"])
            if mass > 3:
                break
            if mass:
                records.append(record)
    if len(records) != N_ALL:
        raise AssertionError("record census")
    active = [int(record["active_vertices"]) for record in records]
    if any(value >= 11 for value in active[:-3]) or active[-3:] != [11, 11, 11]:
        raise AssertionError("proper/full-core partition")
    if [int(record["sequence"]) for record in records[-3:]] != [3308, 3309, 3310]:
        raise AssertionError("seed sequence partition")
    return records


def compact_pair(record: dict[str, Any]) -> tuple[Any, int]:
    pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    used = sorted({vertex for side in pair for edge in side for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact = tuple(
        tuple((relabel[u], relabel[v]) for u, v in side) for side in pair
    )
    return compact, len(used)


def init_column_worker(row_index: dict[tuple[int, ...], int]) -> None:
    global AUDIT_G47, AUDIT_ROW_INDEX
    AUDIT_G47 = load_module("g0050_audit_g47_worker", G47_SCRIPT)
    AUDIT_ROW_INDEX = row_index


def complete_column_worker(record: dict[str, Any]) -> tuple[int, list[tuple[int, int]], int, int]:
    pair, active = compact_pair(record)
    _linear, local_hinges = AUDIT_G47.primitive_normal_form(
        AUDIT_G47.permutation_t_counter_dp(pair, active), active
    )
    multiplier = factorial(11 - active)
    column: dict[int, int] = defaultdict(int)
    for positions in combinations(range(11), active):
        for local_direction, weight in local_hinges.items():
            embedded = [0] * 11
            for index, value in enumerate(local_direction):
                embedded[positions[index]] = value
            direction = tuple(embedded)
            if direction not in AUDIT_ROW_INDEX:
                raise AssertionError(f"HINGE_OUTSIDE_ROW_UNIVERSE {direction}")
            column[AUDIT_ROW_INDEX[direction]] += multiplier * weight
    full_pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    binary = AUDIT_G47.binary_chamber_vector_from_full_symmetry(full_pair, 11)
    invariant = AUDIT_G47.dot(AUDIT_G47.alternating_invariant(11), binary)
    return int(record["sequence"]), sorted(column.items()), invariant, len(local_hinges)


def build_matrix(g47: Any, records: list[dict[str, Any]], universe: tuple[tuple[int, ...], ...], workers: int):
    seed_directions = set()
    for record in records[-3:]:
        pair, active = compact_pair(record)
        _linear, hinges = g47.primitive_normal_form(
            g47.permutation_t_counter_dp(pair, active), active
        )
        seed_directions.update(hinges)
    selected = tuple(sorted(seed_directions)) + tuple(
        direction for direction in universe if direction not in seed_directions
    )
    if len(selected) != N_ROWS or len(set(selected)) != N_ROWS:
        raise AssertionError("row order census")
    row_index = {direction: index for index, direction in enumerate(selected)}
    matrix = np.zeros((N_ROWS, N_ALL), dtype=np.int64)
    invariants: Counter[int] = Counter()
    local_hinge_counts = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_column_worker,
        initargs=(row_index,),
        maxtasksperchild=64,
    ) as pool:
        for completed, (sequence, sparse, invariant, local_count) in enumerate(
            pool.imap_unordered(complete_column_worker, records, chunksize=1), start=1
        ):
            for row, value in sparse:
                matrix[row, sequence - 1] = value
            invariants[invariant] += 1
            local_hinge_counts.append(local_count)
            if completed % 500 == 0 or completed == N_ALL:
                print(f"G0050_AUDIT columns={completed}/{N_ALL}", file=sys.stderr, flush=True)
    if invariants != Counter({0: N_PROPER, 239_500_800: 3}):
        raise AssertionError(f"invariant partition: {invariants}")
    return matrix, selected, invariants, (min(local_hinge_counts), max(local_hinge_counts))


def modular_pivot_columns(matrix: np.ndarray, prime: int) -> tuple[list[int], int]:
    """Independent forward elimination; returns row-space pivot columns."""

    value = np.remainder(matrix, prime).astype(np.int64, copy=True)
    rows, columns = value.shape
    pivot_columns = []
    pivot_row = 0
    for column in range(columns):
        candidates = np.flatnonzero(value[pivot_row:, column])
        if not len(candidates):
            continue
        source = pivot_row + int(candidates[0])
        if source != pivot_row:
            value[[pivot_row, source]] = value[[source, pivot_row]]
        inverse = pow(int(value[pivot_row, column]), -1, prime)
        value[pivot_row, column:] = np.remainder(
            value[pivot_row, column:] * inverse, prime
        )
        if pivot_row + 1 < rows:
            factors = value[pivot_row + 1 :, column].copy()
            block = factors[:, None] * value[pivot_row, column:][None, :]
            value[pivot_row + 1 :, column:] = np.remainder(
                value[pivot_row + 1 :, column:] - block, prime
            )
        pivot_columns.append(column)
        pivot_row += 1
        if pivot_row == rows:
            break
    return pivot_columns, pivot_row


def q_pair(value: Any) -> tuple[int, int]:
    return int(value.numerator), int(value.denominator)


def q_string(value: Any) -> str:
    numerator, denominator = q_pair(value)
    return str(numerator) if denominator == 1 else f"{numerator}/{denominator}"


def update_coordinate_digest(digest: Any, matrix: Any) -> tuple[int, int, int]:
    numerator_bits = denominator_bits = nonunit = 0
    for column in range(matrix.ncols()):
        for row in range(matrix.nrows()):
            numerator, denominator = q_pair(matrix[row, column])
            digest.update(f"{numerator}/{denominator};".encode())
            numerator_bits = max(numerator_bits, abs(numerator).bit_length())
            denominator_bits = max(denominator_bits, denominator.bit_length())
            nonunit += denominator != 1
        digest.update(b"\n")
    return numerator_bits, denominator_bits, nonunit


def run(workers: int = 8, batch_size: int = 79) -> dict[str, Any]:
    for path, expected in EXPECTED.items():
        if sha256_path(path) != expected:
            raise ValueError(f"hash drift: {path}")
    report = load_gzip(SUBJECT_REPORT)
    payload = dict(report)
    recorded_payload_hash = payload.pop("canonical_payload_sha256")
    if canonical_sha256(payload) != recorded_payload_hash:
        raise AssertionError("report canonical payload hash")
    if report["script_sha256"] != EXPECTED[SUBJECT]:
        raise AssertionError("report/script binding")

    g47 = load_module("g0050_audit_g47_main", G47_SCRIPT)
    records = independent_records(g47)
    universe = independent_direction_universe()
    search = load_module("g0050_audit_search", SEARCH_SCRIPT)
    producer_universe = search.direction_universe()
    if universe != producer_universe:
        raise AssertionError("independent and producer row universes differ")
    matrix, selected, invariants, local_range = build_matrix(
        g47, records, universe, workers
    )

    row_hash = canonical_sha256([list(direction) for direction in selected])
    if row_hash != report["complete_integer_matrix"]["row_order_sha256"]:
        raise AssertionError("row order/report mismatch")
    matrix_hash = hashlib.sha256()
    matrix_hash.update(b"int64-little-row-major;shape=10065x3310\n")
    matrix_hash.update(matrix.astype("<i8", copy=False).tobytes(order="C"))
    if matrix_hash.hexdigest() != report["complete_integer_matrix"]["matrix_sha256"]:
        raise AssertionError("matrix/report mismatch")

    extraction = load_gzip(EXTRACT_REPORT)
    discovery = extraction["modular_results"][0]
    basis_columns = list(map(int, report["fixed_exact_basis"]["proper_basis_column_indices"]))
    pivot_rows = list(map(int, discovery["pivot_rows"]))
    if basis_columns != list(map(int, discovery["basis_columns"])):
        raise AssertionError("basis columns are not bound to discovery")
    if canonical_sha256(basis_columns) != report["fixed_exact_basis"]["proper_basis_columns_sha256"]:
        raise AssertionError("basis column digest")
    if len(basis_columns) != N_BASIS or len(set(basis_columns)) != N_BASIS:
        raise AssertionError("basis column census")

    candidate = matrix[np.ix_(pivot_rows, basis_columns)]
    local_rows, candidate_rank = modular_pivot_columns(candidate.transpose(), PRIMES[0])
    if candidate_rank != N_BASIS:
        raise AssertionError("candidate rank")
    solve_rows = [pivot_rows[index] for index in local_rows]
    if solve_rows != list(map(int, report["fixed_exact_basis"]["solve_row_indices"])):
        raise AssertionError("independent pivot extraction differs")
    if canonical_sha256(solve_rows) != report["fixed_exact_basis"]["solve_rows_sha256"]:
        raise AssertionError("solve row digest")

    minor_array = matrix[np.ix_(solve_rows, basis_columns)]
    if canonical_sha256(minor_array.tolist()) != report["fixed_exact_basis"]["minor_entries_sha256"]:
        raise AssertionError("minor entry digest")
    fresh_modular_ranks = {}
    for prime in PRIMES:
        _pivots, rank = modular_pivot_columns(minor_array, prime)
        fresh_modular_ranks[str(prime)] = rank
    if fresh_modular_ranks != {str(prime): N_BASIS for prime in PRIMES}:
        raise AssertionError("minor modular singularity")

    minor = fmpz_mat(minor_array.tolist())
    basis_full = fmpz_mat(matrix[:, basis_columns].tolist())
    digest = hashlib.sha256()
    digest.update(b"column-major-fmpq;shape=488x3307\n")
    max_num = max_den = nonunit = verified = 0
    for start in range(0, N_PROPER, batch_size):
        columns = list(range(start, min(start + batch_size, N_PROPER)))
        rhs_minor = fmpz_mat(matrix[np.ix_(solve_rows, columns)].tolist())
        coordinates = minor.solve(rhs_minor)
        if basis_full * coordinates != fmpz_mat(matrix[:, columns].tolist()):
            raise AssertionError(f"proper replay at {start}")
        num, den, non = update_coordinate_digest(digest, coordinates)
        max_num = max(max_num, num)
        max_den = max(max_den, den)
        nonunit += non
        verified += len(columns)
        if verified % (batch_size * 10) == 0 or verified == N_PROPER:
            print(f"G0050_AUDIT proper={verified}/{N_PROPER}", file=sys.stderr, flush=True)
    proper_report = report["proper_span_certificate"]
    observed_proper = {
        "coordinate_matrix_column_major_sha256": digest.hexdigest(),
        "maximum_numerator_bit_length": max_num,
        "maximum_denominator_bit_length": max_den,
        "nonunit_denominator_entry_count": nonunit,
    }
    for key, value in observed_proper.items():
        if proper_report[key] != value:
            raise AssertionError(f"proper certificate field {key}")

    seeds = [3307, 3308, 3309]
    seed_coordinates = minor.solve(fmpz_mat(matrix[np.ix_(solve_rows, seeds)].tolist()))
    seed_payload = [
        [q_string(seed_coordinates[row, column]) for column in range(3)]
        for row in range(N_BASIS)
    ]
    seed_report = report["seed_quotient_certificate"]
    if seed_payload != seed_report["seed_coordinate_matrix_rows"]:
        raise AssertionError("seed coordinate payload")
    residual = fmpq_mat(fmpz_mat(matrix[:, seeds].tolist())) - basis_full * seed_coordinates
    if any(residual[row, column] for row in solve_rows for column in range(3)):
        raise AssertionError("seed residual does not vanish on solve rows")

    residual_digest = hashlib.sha256()
    residual_digest.update(b"column-major-fmpq;shape=10065x3\n")
    nonzero_counts = [0, 0, 0]
    first_residual = [None, None, None]
    for column in range(3):
        for row in range(N_ROWS):
            numerator, denominator = q_pair(residual[row, column])
            residual_digest.update(f"{numerator}/{denominator};".encode())
            if numerator:
                nonzero_counts[column] += 1
                if first_residual[column] is None:
                    first_residual[column] = {
                        "row_index": row,
                        "direction": list(selected[row]),
                        "value": q_string(residual[row, column]),
                    }
        residual_digest.update(b"\n")
    if residual_digest.hexdigest() != seed_report["residual_matrix_column_major_sha256"]:
        raise AssertionError("seed residual digest")
    if nonzero_counts != seed_report["residual_nonzero_counts_by_seed"]:
        raise AssertionError("seed residual nonzero counts")
    if first_residual != seed_report["first_residual_by_seed"]:
        raise AssertionError("seed first residuals")

    witness_rows = list(map(int, seed_report["witness_row_indices"]))
    witness = fmpq_mat(
        [[residual[row, column] for column in range(3)] for row in witness_rows]
    )
    witness_payload = [
        [q_string(witness[row, column]) for column in range(3)] for row in range(3)
    ]
    determinant = witness.det()
    if witness_payload != seed_report["witness_minor"]:
        raise AssertionError("seed witness entries")
    if q_string(determinant) != seed_report["witness_minor_determinant"] or not determinant:
        raise AssertionError("seed witness determinant")

    return {
        "result": "PASS_EXACT_Q_BRIDGE_WITH_BOUNDED_SCOPE",
        "subject_sha256": sha256_path(SUBJECT),
        "subject_report_sha256": sha256_path(SUBJECT_REPORT),
        "row_universe": {
            "count": len(universe),
            "sha256": row_hash,
            "all_generated_hinges_covered": True,
        },
        "matrix_sha256": matrix_hash.hexdigest(),
        "record_invariant_histogram": {str(k): v for k, v in sorted(invariants.items())},
        "local_hinge_count_range": list(local_range),
        "basis": {
            "columns": N_BASIS,
            "solve_rows": N_BASIS,
            "independent_modular_pivot_extraction_matches": True,
            "minor_ranks": fresh_modular_ranks,
        },
        "proper_span": {
            "columns_replayed": verified,
            "rows_per_column": N_ROWS,
            **observed_proper,
        },
        "seed_quotient": {
            "residual_nonzero_counts": nonzero_counts,
            "witness_determinant": q_string(determinant),
            "rank": 3,
        },
        "scope": (
            "Exact over Q for the frozen 3,310 signed-mass<=3 orbit records and their "
            "complete 10,065-row primitive hinge semantics; not signed mass>=4 or unrestricted MAX11."
        ),
    }


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True))
