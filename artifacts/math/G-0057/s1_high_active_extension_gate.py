#!/usr/bin/env python3
"""Two-prime S1 extension gate for prioritized proper mass-4 columns.

The baseline is the common 867-column G-0054 modular pivot core followed by
the frozen G-0050 488-column proper basis and its three full low-mass seeds.
Every column is regenerated as an exact integer sparse vector on the complete
99,858-row degree-four hinge universe.  Any augmented-rank gain is accompanied
by an explicit modular null vector replayed on all 99,858 rows.

This is a modular discovery gate.  It does not turn the common two-prime pivot
set into a rational basis, and a modular circuit is not a real identity until
it is lifted over Q and its full piecewise-linear semantics are replayed.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import gzip
import hashlib
import importlib.util
from itertools import combinations
import json
from math import factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Any

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

EXPECTED_G0050_SCRIPT_SHA256 = "b82fbb6df487b0e76a4bbefc695960b9f1a87ef25a9e8e33b26f07d02433f27b"
EXPECTED_G0050_REPORT_SHA256 = "64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b"
EXPECTED_G0054_SCRIPT_SHA256 = "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2"
EXPECTED_G0054_REPORT_SHA256 = "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053"
EXPECTED_G0055_SCRIPT_SHA256 = "5f78397925e0873b696dc9d4b6c0562b9af58a0198e74ca636049f932fbade17"
EXPECTED_G0055_REPORT_SHA256 = "f6e6c824cbebab126f7452bc922859f5b53fa54f1af91cfb71dfefca41ba5cdc"
EXPECTED_G0056_SCRIPT_SHA256 = "484d86ccc494019c802f3f793c8f40c4deda2e7e86913191888a2188fef527c7"
EXPECTED_G0056_REPORT_SHA256 = "131312761477dc3ae47167caa83aabdde1d7dc6da40b71e33c40c8b5401088d4"
EXPECTED_G0054_PAYLOAD_SHA256 = "a7a8082393ef709b6ffe372f142688e3ff47182e11967a0a97cb5698fa772f71"
EXPECTED_G0054_PIVOT_COLUMNS_SHA256 = "fed7aeab65a3b641ffbaceb401779e1293b1988024bc9f71366740ba4b4f4804"
EXPECTED_G0055_SCIENTIFIC_PAYLOAD_SHA256 = "c52b164b769325a3662b1ae273fe3b9db44b4ffc54a053b6a105363feb6f965f"
EXPECTED_G0056_PAYLOAD_SHA256 = "3d91bc9d6bc869b8e31a8adf6d15c42752f7e3d90674a343d772a99793e26837"
EXPECTED_EXACT_S0_BASIS_MANIFEST_SHA256 = "c608b393ff49a9f958d7017a9d5229cd16fca2817cee4d8493cfb51be94486dc"
EXPECTED_EXACT_S0_BASIS_STREAM_SHA256 = "4918538dad89020784645c3cfd25c12b88b2b63857a4703a8ca4f5f522516f5c"
EXPECTED_UNIVERSE_SHA256 = "500f354a2856984a518f37d2e5f48f0a380249e2653459049da243a5c17e8eb2"
EXPECTED_ROWS = 99_858
EXPECTED_S0_PIVOTS = 867
EXPECTED_LOWMASS_PROPER = 488
EXPECTED_LOWMASS_SEEDS = 3
EXPECTED_BASELINE = 1_358
EXPECTED_PRICED_CANDIDATES = 2_058
EXPECTED_NONZERO_PRICE_CANDIDATES = 524
S0_SEQUENCE_FIRST = 136_039
PRIMES = (1_000_003, 1_000_033)
DEFAULT_OUTPUT = HERE / "s1_high_active_extension_gate_v1.json.gz"
SCHEMA = "max11-g0057-s1-high-active-extension-gate-v1"

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

G0054: ModuleType | None = None
THEOREM: ModuleType | None = None
ROW_INDEX: dict[Direction, int] = {}


class GateError(RuntimeError):
    """Fail-closed semantic or certificate error."""


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


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise GateError(f"bound script drift: {path}: {observed} != {expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def file_bindings() -> dict[str, str]:
    observed = {
        "g0050_script_sha256": sha256_path(G0050_SCRIPT),
        "g0050_report_sha256": sha256_path(G0050_REPORT),
        "g0054_script_sha256": sha256_path(G0054_SCRIPT),
        "g0054_report_sha256": sha256_path(G0054_REPORT),
        "g0055_script_sha256": sha256_path(G0055_SCRIPT),
        "g0055_report_sha256": sha256_path(G0055_REPORT),
        "g0056_script_sha256": sha256_path(G0056_SCRIPT),
        "g0056_report_sha256": sha256_path(G0056_REPORT),
    }
    expected = {
        "g0050_script_sha256": EXPECTED_G0050_SCRIPT_SHA256,
        "g0050_report_sha256": EXPECTED_G0050_REPORT_SHA256,
        "g0054_script_sha256": EXPECTED_G0054_SCRIPT_SHA256,
        "g0054_report_sha256": EXPECTED_G0054_REPORT_SHA256,
        "g0055_script_sha256": EXPECTED_G0055_SCRIPT_SHA256,
        "g0055_report_sha256": EXPECTED_G0055_REPORT_SHA256,
        "g0056_script_sha256": EXPECTED_G0056_SCRIPT_SHA256,
        "g0056_report_sha256": EXPECTED_G0056_REPORT_SHA256,
    }
    if observed != expected:
        raise GateError(f"input binding drift: observed={observed}, expected={expected}")
    return observed


def record_descriptor(record: dict[str, object]) -> dict[str, object]:
    return {
        "sequence": int(record["sequence"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "abs_components": int(record["abs_components"]),
    }


def compact_pair(record: dict[str, object]) -> tuple[Pair, int]:
    pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    used = sorted({vertex for branch in pair for edge in branch for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact: Pair = tuple(
        tuple((relabel[u], relabel[v]) for u, v in branch) for branch in pair
    )  # type: ignore[assignment]
    return compact, len(used)


def load_frozen_manifests(
    candidate_scope: str,
) -> tuple[
    list[int],
    list[int],
    list[int],
    list[int],
    dict[int, int],
    list[dict[str, object]],
    dict[str, object],
]:
    g0050 = load_json_gz(G0050_REPORT)
    g0054 = load_json_gz(G0054_REPORT)
    g0055 = load_json_gz(G0055_REPORT)
    g0056 = load_json_gz(G0056_REPORT)
    if g0054.get("canonical_payload_sha256") != EXPECTED_G0054_PAYLOAD_SHA256:
        raise GateError("G-0054 canonical payload drift")
    if g0055.get("canonical_scientific_payload_sha256") != EXPECTED_G0055_SCIENTIFIC_PAYLOAD_SHA256:
        raise GateError("G-0055 canonical scientific payload drift")
    if g0056.get("canonical_payload_sha256") != EXPECTED_G0056_PAYLOAD_SHA256:
        raise GateError("G-0056 canonical payload drift")

    pivot_lists = [
        list(map(int, result["rank_lower_certificate"]["pivot_columns"]))
        for result in g0054["modular_results"]
    ]
    pivot_hashes = [
        result["rank_lower_certificate"]["pivot_columns_sha256"]
        for result in g0054["modular_results"]
    ]
    if (
        len(pivot_lists) != 2
        or pivot_lists[0] != pivot_lists[1]
        or len(pivot_lists[0]) != EXPECTED_S0_PIVOTS
        or pivot_hashes != [EXPECTED_G0054_PIVOT_COLUMNS_SHA256] * 2
    ):
        raise GateError("G-0054 common pivot manifest drift")
    s0_sequences = [S0_SEQUENCE_FIRST + column for column in pivot_lists[0]]
    exact_basis = g0056["canonical_exact_s0_basis"]
    exact_manifest = exact_basis["basis_manifest"]
    exact_sequences = [int(item["source_sequence"]) for item in exact_manifest]
    exact_source_columns = [int(item["source_zero_based_column"]) for item in exact_manifest]
    if (
        exact_basis["basis_manifest_sha256"] != EXPECTED_EXACT_S0_BASIS_MANIFEST_SHA256
        or exact_basis["ordered_basis_sparse_stream_sha256"]
        != EXPECTED_EXACT_S0_BASIS_STREAM_SHA256
        or int(exact_basis["basis_column_count"]) != EXPECTED_S0_PIVOTS
        or exact_sequences != s0_sequences
        or exact_source_columns != pivot_lists[0]
        or int(g0056["exact_rank_certificate"]["exact_rank_Q"]) != EXPECTED_S0_PIVOTS
    ):
        raise GateError("G-0056 exact S0 basis manifest drift")

    proper_indices = list(map(int, g0050["fixed_exact_basis"]["proper_basis_column_indices"]))
    seed_indices = [3307, 3308, 3309]
    if len(proper_indices) != EXPECTED_LOWMASS_PROPER or len(set(proper_indices)) != len(proper_indices):
        raise GateError("G-0050 proper basis manifest drift")

    prices = {
        int(item["sequence"]): int(item["pairing_numerator"])
        for item in g0055["exact_first_block_pricing"]["per_record"]
    }
    ordered_candidates: list[int] = []
    seen: set[int] = set()
    for block in g0055["priority_blocks"]:
        for raw_sequence in block["sequences"]:
            sequence = int(raw_sequence)
            if sequence in seen:
                raise GateError(f"duplicate G-0055 candidate sequence {sequence}")
            seen.add(sequence)
            ordered_candidates.append(sequence)
    if len(ordered_candidates) != EXPECTED_PRICED_CANDIDATES or set(ordered_candidates) != set(prices):
        raise GateError("G-0055 candidate order/census drift")
    nonzero_candidates = [sequence for sequence in ordered_candidates if prices[sequence]]
    if len(nonzero_candidates) != EXPECTED_NONZERO_PRICE_CANDIDATES:
        raise GateError("G-0055 nonzero-price candidate census drift")
    if candidate_scope == "baseline-only":
        candidates = []
    elif candidate_scope == "nonzero-price":
        candidates = nonzero_candidates
    else:
        candidates = ordered_candidates
    metadata = {
        "g0054_common_pivot_column_indices_sha256": canonical_sha256(pivot_lists[0]),
        "g0056_exact_s0_basis_manifest_sha256": EXPECTED_EXACT_S0_BASIS_MANIFEST_SHA256,
        "g0056_exact_s0_basis_sparse_stream_sha256": EXPECTED_EXACT_S0_BASIS_STREAM_SHA256,
        "s0_sequence_manifest_sha256": canonical_sha256(s0_sequences),
        "g0050_proper_basis_indices_sha256": canonical_sha256(proper_indices),
        "g0050_seed_indices": seed_indices,
        "all_g0055_candidate_order_sha256": canonical_sha256(ordered_candidates),
        "nonzero_price_candidate_order_sha256": canonical_sha256(nonzero_candidates),
        "selected_candidate_scope": candidate_scope,
        "selected_candidate_order_sha256": canonical_sha256(candidates),
    }
    return (
        s0_sequences,
        proper_indices,
        seed_indices,
        candidates,
        prices,
        exact_manifest,
        metadata,
    )


def read_mass4_records(theorem: ModuleType, sequences: set[int]) -> dict[int, dict[str, object]]:
    records: dict[int, dict[str, object]] = {}
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise GateError("G-0038 stream header missing")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            sequence = int(record["sequence"])
            if sequence in sequences:
                records[sequence] = record
    missing = sorted(sequences - set(records))
    if missing:
        raise GateError(f"mass-4 manifest records missing: {missing[:3]}")
    return records


def init_semantic_worker(row_index: dict[Direction, int]) -> None:
    global G0054, THEOREM, ROW_INDEX
    G0054 = import_bound(
        f"g0057_worker_g0054_{os.getpid()}", G0054_SCRIPT, EXPECTED_G0054_SCRIPT_SHA256
    )
    THEOREM = G0054.load_theorem(f"g0057_worker_theorem_{os.getpid()}")
    ROW_INDEX = row_index


def sparse_column_hash(
    namespace: str,
    source_id: int,
    rows: np.ndarray,
    values: np.ndarray,
    invariant: int,
) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0057-complete-row-sparse-column-v1\n")
    digest.update(namespace.encode("ascii") + b"\n")
    digest.update(int(source_id).to_bytes(8, "little", signed=False))
    digest.update(int(invariant).to_bytes(8, "little", signed=True))
    digest.update(int(len(rows)).to_bytes(8, "little", signed=False))
    digest.update(rows.astype("<u4", copy=False).tobytes(order="C"))
    digest.update(values.astype("<i8", copy=False).tobytes(order="C"))
    return digest.hexdigest()


def semantic_worker(payload: tuple[int, str, int, dict[str, object]]) -> dict[str, object]:
    order, namespace, source_id, record = payload
    if THEOREM is None or not ROW_INDEX:
        raise GateError("semantic worker not initialized")
    pair, active = compact_pair(record)
    counter = THEOREM.permutation_t_counter_dp(pair, active)
    _linear, local_hinges = THEOREM.primitive_normal_form(counter, active)
    multiplier = factorial(11 - active)
    selected: Counter[int] = Counter()
    escaped: list[Direction] = []
    for positions in combinations(range(11), active):
        for local_direction, raw_weight in local_hinges.items():
            weight = int(raw_weight)
            if not weight:
                continue
            embedded = [0] * 11
            for local_index, value in enumerate(local_direction):
                embedded[positions[local_index]] = value
            direction = tuple(embedded)
            row = ROW_INDEX.get(direction)
            if row is None:
                escaped.append(direction)
            else:
                selected[row] += multiplier * weight
    if escaped:
        raise GateError(f"hinge escaped degree-four universe: {min(escaped)}")
    sparse = sorted((row, value) for row, value in selected.items() if value)
    rows = np.fromiter((row for row, _value in sparse), dtype=np.uint32)
    values = np.fromiter((value for _row, value in sparse), dtype=np.int64)
    if len(rows) != len(set(map(int, rows))) or np.any(values == 0):
        raise GateError("malformed sparse column")
    full_pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    binary = THEOREM.binary_chamber_vector_from_full_symmetry(full_pair, 11)
    invariant = int(THEOREM.dot(THEOREM.alternating_invariant(11), binary))
    return {
        "order": order,
        "namespace": namespace,
        "source_id": source_id,
        "sequence": int(record["sequence"]),
        "active_vertices": active,
        "rows": rows,
        "values": values,
        "lambda": invariant,
        "semantic_sha256": sparse_column_hash(namespace, source_id, rows, values, invariant),
    }


def generate_semantics(
    payloads: list[tuple[int, str, int, dict[str, object]]],
    row_index: dict[Direction, int],
    workers: int,
    label: str,
) -> tuple[list[dict[str, object]], float]:
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_semantic_worker,
        initargs=(row_index,),
        maxtasksperchild=32,
    ) as pool:
        for result in pool.imap_unordered(semantic_worker, payloads, chunksize=1):
            results.append(result)
            if len(results) % 100 == 0 or len(results) == len(payloads):
                print(
                    f"G0057_{label} columns={len(results)}/{len(payloads)}",
                    file=sys.stderr,
                    flush=True,
                )
    results.sort(key=lambda item: int(item["order"]))
    if [int(item["order"]) for item in results] != list(range(len(payloads))):
        raise GateError(f"{label} output order drift")
    return results, time.perf_counter() - started


def ordered_sparse_stream_hash(results: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    digest.update(b"max11-g0057-ordered-complete-row-sparse-stream-v1\n")
    for result in results:
        digest.update(bytes.fromhex(str(result["semantic_sha256"])))
    return digest.hexdigest()


def verify_exact_s0_basis_semantics(
    results: list[dict[str, object]], exact_manifest: list[dict[str, object]]
) -> dict[str, object]:
    if len(results) != EXPECTED_S0_PIVOTS or len(exact_manifest) != EXPECTED_S0_PIVOTS:
        raise GateError("exact S0 semantic comparison census drift")
    g0054_hashes = []
    for index, (result, expected) in enumerate(zip(results, exact_manifest, strict=True)):
        observed_hash = G0054.semantic_column_hash(
            int(result["sequence"]),
            result["rows"],
            result["values"],
            int(result["lambda"]),
        )
        if (
            int(expected["basis_index"]) != index
            or int(expected["source_sequence"]) != int(result["sequence"])
            or int(expected["support_size"]) != len(result["rows"])
            or int(expected["lambda"]) != int(result["lambda"])
            or str(expected["semantic_sha256"]) != observed_hash
        ):
            raise GateError(f"G-0056 exact S0 basis semantic mismatch at basis index {index}")
        g0054_hashes.append(observed_hash)
    return {
        "columns_compared": len(results),
        "all_sequence_support_lambda_and_semantic_hashes_match_g0056": True,
        "ordered_g0054_semantic_hashes_sha256": canonical_sha256(g0054_hashes),
    }


def verify_lowmass_semantics_independently(
    search: ModuleType,
    selected_records: list[dict[str, object]],
    observed: list[dict[str, object]],
    row_index: dict[Direction, int],
    workers: int,
) -> dict[str, object]:
    if len(selected_records) != 491 or len(observed) != 491:
        raise GateError("low-mass independent replay census drift")
    replayed: dict[int, tuple[int, list[tuple[int, int]], int]] = {}
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=search.init_worker,
        initargs=(row_index,),
        maxtasksperchild=64,
    ) as pool:
        for sequence, active, sparse, invariant in pool.imap_unordered(
            search.column_worker, selected_records, chunksize=1
        ):
            replayed[int(sequence)] = (int(active), sparse, int(invariant))
    payload = []
    for result in observed:
        sequence = int(result["sequence"])
        if sequence not in replayed:
            raise GateError(f"low-mass independent replay missing sequence {sequence}")
        active, sparse, invariant = replayed[sequence]
        expected_rows = [int(row) for row, _value in sparse]
        expected_values = [int(value) for _row, value in sparse]
        if (
            active != int(result["active_vertices"])
            or expected_rows != list(map(int, result["rows"]))
            or expected_values != list(map(int, result["values"]))
            or invariant != int(result["lambda"])
        ):
            raise GateError(f"low-mass independent semantic mismatch at sequence {sequence}")
        payload.append([sequence, active, sparse, invariant])
    return {
        "columns_compared": len(observed),
        "all_rows_values_active_supports_and_lambdas_match_frozen_g0050_generator": True,
        "ordered_independent_replay_sha256": canonical_sha256(payload),
    }


def build_union_matrix(
    universe: tuple[Direction, ...], results: list[dict[str, object]]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    union_mask = np.zeros(len(universe), dtype=np.bool_)
    total_nonzeros = 0
    support_sizes = []
    lambdas = []
    for result in results:
        rows = result["rows"]
        values = result["values"]
        if not isinstance(rows, np.ndarray) or not isinstance(values, np.ndarray):
            raise GateError("semantic column lost typed sparse arrays")
        union_mask[rows] = True
        total_nonzeros += len(rows)
        support_sizes.append(len(rows))
        lambdas.append(int(result["lambda"]))
    union_rows = np.flatnonzero(union_mask).astype(np.uint32)
    compressed = np.full(len(universe), -1, dtype=np.int32)
    compressed[union_rows] = np.arange(len(union_rows), dtype=np.int32)
    matrix = np.zeros((len(union_rows), len(results)), dtype=np.int64)
    for column, result in enumerate(results):
        local = compressed[result["rows"]]
        if np.any(local < 0):
            raise GateError("column entry escaped its exact union")
        matrix[local, column] = result["values"]
    if int(np.count_nonzero(matrix)) != total_nonzeros:
        raise GateError("dense union matrix lost or duplicated sparse entries")
    lambda_row = np.array(lambdas, dtype=np.int64)
    union_directions = [list(universe[int(row)]) for row in union_rows]
    metadata = {
        "complete_row_count": len(universe),
        "union_row_count": len(union_rows),
        "omitted_zero_row_count": len(universe) - len(union_rows),
        "union_row_indices_sha256": hashlib.sha256(
            union_rows.astype("<u4", copy=False).tobytes(order="C")
        ).hexdigest(),
        "union_directions_sha256": canonical_sha256(union_directions),
        "total_nonzeros": total_nonzeros,
        "support_minimum": min(support_sizes),
        "support_median": sorted(support_sizes)[(len(support_sizes) - 1) // 2],
        "support_maximum": max(support_sizes),
        "lambda_histogram": {
            str(value): count for value, count in sorted(Counter(lambdas).items())
        },
        "matrix_shape": list(matrix.shape),
        "matrix_sha256": G0054.hash_dense_matrix(matrix),
    }
    return union_rows, matrix, lambda_row, metadata


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.remainder(matrix, prime).astype(np.int64, copy=False)
    flat = reduced.ravel(order="C").tolist()
    field = nmod_mat(matrix.shape[0], matrix.shape[1], flat, prime)
    del flat, reduced
    return field


def first_potent_null_vector(
    field: nmod_mat, lambda_row: np.ndarray, prime: int, rank: int
) -> tuple[int, list[int] | None, int]:
    kernel, raw_nullity = field.nullspace()
    nullity = int(raw_nullity)
    expected = field.ncols() - rank
    if nullity != expected:
        raise GateError(f"nullity drift: {nullity}/{expected}")
    for basis_column in range(nullity):
        potency = 0
        for row in range(field.ncols()):
            potency = (potency + int(lambda_row[row]) * int(kernel[row, basis_column])) % prime
        if potency:
            scale = pow(potency, -1, prime)
            coefficients = [
                int(kernel[row, basis_column]) * scale % prime for row in range(field.ncols())
            ]
            return nullity, coefficients, basis_column
    return nullity, None, -1


def replay_witness(
    results: list[dict[str, object]], coefficients: list[int], prime: int
) -> dict[str, object]:
    if len(results) != len(coefficients):
        raise GateError("witness coefficient length mismatch")
    residual = np.zeros(EXPECTED_ROWS, dtype=np.int64)
    potency = 0
    support = []
    for column, (result, coefficient) in enumerate(zip(results, coefficients, strict=True)):
        coefficient %= prime
        if not coefficient:
            continue
        support.append(
            {
                "column": column,
                "namespace": result["namespace"],
                "source_id": int(result["source_id"]),
                "sequence": int(result["sequence"]),
                "coefficient": coefficient,
            }
        )
        rows = result["rows"]
        values = result["values"]
        residual[rows] = (residual[rows] + np.remainder(values, prime) * coefficient) % prime
        potency = (potency + int(result["lambda"]) * coefficient) % prime
    nonzero_rows = np.flatnonzero(residual)
    if len(nonzero_rows) or potency != 1:
        raise GateError(
            f"full-row witness replay failed: residual={len(nonzero_rows)}, potency={potency}"
        )
    return {
        "normalization": "lambda_dot_coefficients_mod_prime_equals_one",
        "support_size": len(support),
        "support": support,
        "support_sha256": canonical_sha256(support),
        "all_99858_hinge_rows_zero_mod_prime": True,
        "lambda_mod_prime": potency,
        "residual_vector_sha256": hashlib.sha256(
            residual.astype("<u4", copy=False).tobytes(order="C")
        ).hexdigest(),
    }


def analyze_matrix(
    matrix: np.ndarray,
    lambda_row: np.ndarray,
    results: list[dict[str, object]],
    prime: int,
    label: str,
) -> tuple[dict[str, object], bool]:
    started = time.perf_counter()
    field = to_nmod(matrix, prime)
    rank = int(field.rank())
    nullity, coefficients, kernel_column = first_potent_null_vector(
        field, lambda_row, prime, rank
    )
    augmented_gain = int(coefficients is not None)
    report: dict[str, object] = {
        "label": label,
        "prime": prime,
        "column_count": matrix.shape[1],
        "hinge_rank": rank,
        "nullity": nullity,
        "augmented_hinge_plus_lambda_rank": rank + augmented_gain,
        "augmented_rank_gain": augmented_gain,
        "kernel_basis_column_used": kernel_column if coefficients is not None else None,
        "seconds": time.perf_counter() - started,
    }
    if coefficients is not None:
        report["potent_modular_witness"] = replay_witness(results, coefficients, prime)
    else:
        report["potent_modular_witness"] = None
    del field
    gc.collect()
    return report, coefficients is not None


def replay_semantics(
    first: list[dict[str, object]], replay: list[dict[str, object]], union_mask: np.ndarray
) -> dict[str, object]:
    if len(first) != len(replay):
        raise GateError("semantic replay column count mismatch")
    mismatches = []
    escaped = []
    for index, (expected, observed) in enumerate(zip(first, replay, strict=True)):
        if expected["semantic_sha256"] != observed["semantic_sha256"]:
            mismatches.append(index)
        if np.any(~union_mask[observed["rows"]]):
            escaped.append(index)
    if mismatches or escaped:
        raise GateError(f"semantic replay failed: mismatches={mismatches[:3]}, escaped={escaped[:3]}")
    return {
        "all_column_semantic_hashes_match": True,
        "every_replayed_nonzero_belongs_to_frozen_union": True,
        "replayed_ordered_sparse_stream_sha256": ordered_sparse_stream_hash(replay),
        "verified_zero_off_union_entries": int(np.count_nonzero(~union_mask)) * len(first),
    }


def resource_preflight(minimum_available_gib: float) -> dict[str, object]:
    fields: dict[str, int] = {}
    with Path("/proc/meminfo").open("rt", encoding="utf-8") as source:
        for line in source:
            key, value = line.split(":", 1)
            fields[key] = int(value.strip().split()[0])
    available_gib = fields["MemAvailable"] / (1024**2)
    if available_gib < minimum_available_gib:
        raise GateError(
            f"resource preflight failed: {available_gib:.2f} GiB available < {minimum_available_gib:.2f}"
        )
    return {
        "available_gib": available_gib,
        "minimum_required_gib": minimum_available_gib,
        "passed": True,
    }


def synthetic_augmented_control() -> dict[str, object]:
    prime = PRIMES[0]
    matrix = np.array([[1, 1], [0, 0]], dtype=np.int64)
    lambdas = np.array([0, 1], dtype=np.int64)
    fake_results = [
        {
            "namespace": "control",
            "source_id": index,
            "sequence": index,
            "rows": np.array([0], dtype=np.uint32),
            "values": np.array([1], dtype=np.int64),
            "lambda": int(lambdas[index]),
        }
        for index in range(2)
    ]
    field = to_nmod(matrix, prime)
    rank = int(field.rank())
    nullity, coefficients, _column = first_potent_null_vector(
        field, lambdas, prime, rank
    )
    if rank != 1 or nullity != 1 or coefficients is None:
        raise GateError("synthetic augmented-gain control failed")
    replay = replay_witness(fake_results, coefficients, prime)
    del field
    return {
        "rank": rank,
        "nullity": nullity,
        "augmented_gain": 1,
        "witness_support_size": replay["support_size"],
        "passed": True,
    }


def run(
    workers: int,
    candidate_scope: str,
    minimum_available_gib: float,
) -> dict[str, object]:
    global G0054, THEOREM, ROW_INDEX
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    bindings = file_bindings()
    preflight = resource_preflight(minimum_available_gib)
    synthetic_control = synthetic_augmented_control()

    G0054 = import_bound("g0057_g0054", G0054_SCRIPT, EXPECTED_G0054_SCRIPT_SHA256)
    THEOREM = G0054.load_theorem("g0057_theorem")
    universe = G0054.direction_universe()
    if len(universe) != EXPECTED_ROWS or canonical_sha256([list(row) for row in universe]) != EXPECTED_UNIVERSE_SHA256:
        raise GateError("complete degree-four universe drift")
    ROW_INDEX = {direction: index for index, direction in enumerate(universe)}

    (
        s0_sequences,
        proper_indices,
        seed_indices,
        candidate_sequences,
        prices,
        exact_s0_manifest,
        manifest_metadata,
    ) = load_frozen_manifests(candidate_scope)

    g0050 = import_bound("g0057_g0050", G0050_SCRIPT, EXPECTED_G0050_SCRIPT_SHA256)
    extract = g0050.import_extract()
    search = extract.load_search()
    lowmass_records = search.load_records(search.load_g47())
    if len(lowmass_records) != 3310:
        raise GateError("low-mass record census drift")

    mass4_needed = set(s0_sequences) | set(candidate_sequences)
    mass4_records = read_mass4_records(THEOREM, mass4_needed)
    payloads: list[tuple[int, str, int, dict[str, object]]] = []
    descriptors: list[dict[str, object]] = []

    for pivot_position, sequence in enumerate(s0_sequences):
        record = mass4_records[sequence]
        payloads.append((len(payloads), "s0_mass4_pivot", pivot_position, record))
        descriptors.append(
            {
                "namespace": "s0_mass4_pivot",
                "pivot_position": pivot_position,
                "record": record_descriptor(record),
            }
        )
    for column_index in proper_indices:
        record = lowmass_records[column_index]
        payloads.append((len(payloads), "lowmass_proper_basis", column_index, record))
        descriptors.append(
            {
                "namespace": "lowmass_proper_basis",
                "column_index": column_index,
                "record": record_descriptor(record),
            }
        )
    for column_index in seed_indices:
        record = lowmass_records[column_index]
        payloads.append((len(payloads), "lowmass_full_seed", column_index, record))
        descriptors.append(
            {
                "namespace": "lowmass_full_seed",
                "column_index": column_index,
                "record": record_descriptor(record),
            }
        )
    baseline_count = len(payloads)
    if baseline_count != EXPECTED_BASELINE:
        raise GateError(f"baseline column census drift: {baseline_count}")
    for priority_position, sequence in enumerate(candidate_sequences):
        record = mass4_records[sequence]
        if int(record["active_vertices"]) >= 11:
            raise GateError(f"candidate is not proper: {sequence}")
        payloads.append((len(payloads), "g0055_proper_mass4_candidate", priority_position, record))
        descriptors.append(
            {
                "namespace": "g0055_proper_mass4_candidate",
                "priority_position": priority_position,
                "old_g0053_price_numerator": prices[sequence],
                "record": record_descriptor(record),
            }
        )

    results, semantic_seconds = generate_semantics(payloads, ROW_INDEX, workers, "SEMANTIC")
    exact_s0_semantic_check = verify_exact_s0_basis_semantics(
        results[:EXPECTED_S0_PIVOTS], exact_s0_manifest
    )
    selected_lowmass_records = [lowmass_records[index] for index in proper_indices + seed_indices]
    lowmass_semantic_check = verify_lowmass_semantics_independently(
        search,
        selected_lowmass_records,
        results[EXPECTED_S0_PIVOTS:baseline_count],
        ROW_INDEX,
        workers,
    )
    if any(int(result["lambda"]) for result in results[baseline_count:]):
        raise GateError("proper candidate has nonzero alternating invariant")
    union_rows, matrix, lambda_row, union_metadata = build_union_matrix(universe, results)
    union_mask = np.zeros(EXPECTED_ROWS, dtype=np.bool_)
    union_mask[union_rows] = True

    modular_results = []
    any_gain = False
    for prime in PRIMES:
        baseline_report, baseline_gain = analyze_matrix(
            matrix[:, :baseline_count],
            lambda_row[:baseline_count],
            results[:baseline_count],
            prime,
            "modular_s1_baseline",
        )
        extended_report = None
        extended_gain = False
        if candidate_sequences:
            extended_report, extended_gain = analyze_matrix(
                matrix,
                lambda_row,
                results,
                prime,
                f"s1_plus_{candidate_scope}_g0055_candidates",
            )
        modular_results.append(
            {
                "prime": prime,
                "baseline": baseline_report,
                "extended": extended_report,
                "hinge_rank_growth": (
                    int(extended_report["hinge_rank"])
                    - int(baseline_report["hinge_rank"])
                    if extended_report is not None
                    else None
                ),
            }
        )
        any_gain = any_gain or baseline_gain or extended_gain

    semantic_replay = None
    if any_gain:
        replay, replay_seconds = generate_semantics(payloads, ROW_INDEX, workers, "REPLAY")
        semantic_replay = replay_semantics(results, replay, union_mask)
        semantic_replay["seconds"] = replay_seconds

    result_key = "baseline" if not candidate_sequences else "extended"
    gains = [int(item[result_key]["augmented_rank_gain"]) for item in modular_results]
    if gains == [1, 1]:
        result_label = (
            "BOTH_PRIMES_HAVE_REPLAYED_BASELINE_AUGMENTED_GAIN"
            if not candidate_sequences
            else "BOTH_PRIMES_HAVE_REPLAYED_EXTENDED_AUGMENTED_GAIN"
        )
    elif gains == [0, 0]:
        result_label = (
            "NO_BASELINE_AUGMENTED_GAIN_AT_EITHER_FROZEN_PRIME"
            if not candidate_sequences
            else "NO_EXTENDED_AUGMENTED_GAIN_AT_EITHER_FROZEN_PRIME"
        )
    else:
        result_label = "MIXED_PRIME_EXTENDED_AUGMENTED_OUTCOME"

    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": result_label,
        "bindings": bindings,
        "baseline_scope": {
            "kind": "prime-specific span-equivalent modular S1 baseline",
            "ordered_composition": [
                {"namespace": "g0054_common_s0_pivots", "count": EXPECTED_S0_PIVOTS},
                {"namespace": "g0050_proper_basis", "count": EXPECTED_LOWMASS_PROPER},
                {"namespace": "g0050_full_seeds", "count": EXPECTED_LOWMASS_SEEDS},
            ],
            "column_count": baseline_count,
            "manifest": manifest_metadata,
            "descriptor_sha256": canonical_sha256(descriptors[:baseline_count]),
            "ordered_sparse_stream_sha256": ordered_sparse_stream_hash(
                results[:baseline_count]
            ),
        },
        "candidate_scope": {
            "kind": candidate_scope,
            "column_count": len(candidate_sequences),
            "sequence_order_sha256": canonical_sha256(candidate_sequences),
            "descriptor_sha256": canonical_sha256(descriptors[baseline_count:]),
        },
        "complete_integer_semantics": {
            "complete_row_count": EXPECTED_ROWS,
            "complete_row_universe_sha256": EXPECTED_UNIVERSE_SHA256,
            "ordered_column_count": len(results),
            "ordered_descriptor_sha256": canonical_sha256(descriptors),
            "ordered_sparse_stream_sha256": ordered_sparse_stream_hash(results),
            "exact_union": union_metadata,
            "semantic_replay_if_gain": semantic_replay,
        },
        "modular_results": modular_results,
        "controls": {
            "resource_preflight": preflight,
            "synthetic_augmented_gain": synthetic_control,
            "exact_s0_basis_semantic_crosscheck": exact_s0_semantic_check,
            "independent_lowmass_semantic_crosscheck": lowmass_semantic_check,
            "all_candidate_lambdas_zero": True,
            "all_sparse_rows_belong_to_complete_universe": True,
            "dense_union_nonzero_count_matches_sparse_stream": True,
        },
        "claim_boundary": [
            "All ranks, null vectors, and augmented gains in this artifact are over the two stated finite fields.",
            "The common 867-column G-0054 core is span-equivalent at those primes; this artifact does not claim it is a Q basis.",
            "The G-0053 price is used only for candidate scheduling and is not a construction criterion.",
            "A replayed modular augmented gain is a lift target, not a real identity; exact-Q coefficient reconstruction and full functional replay remain mandatory.",
            "The experiment covers only the frozen selected proper mass-4 blocks, not all 132,728 proper mass-4 atoms or unrestricted networks.",
        ],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "timing": {
            "semantic_seconds": semantic_seconds,
            "wall_seconds": time.perf_counter() - started,
        },
        "script_sha256": script_hash_before,
    }
    scientific_payload = {
        key: report[key]
        for key in (
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
    }
    report["canonical_scientific_payload_sha256"] = canonical_sha256(scientific_payload)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise GateError("script changed during execution")
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument(
        "--candidate-scope",
        choices=("baseline-only", "nonzero-price", "all-priced"),
        default="nonzero-price",
    )
    parser.add_argument("--minimum-available-gib", type=float, default=16.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.candidate_scope, args.minimum_available_gib)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
