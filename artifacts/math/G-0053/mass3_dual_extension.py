#!/usr/bin/env python3
"""Extend the exact mass<=3 hinge dual to signed-mass-4 atoms and map failure."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import combinations
import json
from math import factorial, gcd, lcm
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Hashable

from flint import fmpq_mat, fmpz_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0050_SCRIPT = ROOT / "artifacts/math/G-0050/exact_q_bridge.py"
G0050_REPORT = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"
G0052_SCRIPT = ROOT / "artifacts/math/G-0052/mass4_full_core_census.py"
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
EXPECTED_G0050_SCRIPT_HASH = "b82fbb6df487b0e76a4bbefc695960b9f1a87ef25a9e8e33b26f07d02433f27b"
EXPECTED_G0050_REPORT_HASH = "64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b"
EXPECTED_G0052_SCRIPT_HASH = "435832fb62ca75981a11f3193f4546c0ca817ad7752a0636bbaeb8730cc23d51"
EXPECTED_G0052_REPORT_HASH = "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37"
DEFAULT_OUTPUT = HERE / "mass3_dual_extension_v1.json.gz"
SCHEMA = "max11-g0053-mass3-dual-extension-v1"
N = 11
LAMBDA_SEED = 239_500_800

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

THEOREM: Any = None
Y_INTEGER: dict[Direction, int] = {}
Y_DENOMINATOR = 1


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


def import_bound(name: str, path: Path, expected_hash: str) -> Any:
    if sha256_path(path) != expected_hash:
        raise ValueError(f"bound script drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def q_pair(value: Any) -> tuple[int, int]:
    return int(value.numerator), int(value.denominator)


def fraction_string(numerator: int, denominator: int) -> str:
    value = Fraction(numerator, denominator)
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


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


def init_mass4_worker(
    y_entries: list[tuple[Direction, int]], denominator: int
) -> None:
    global THEOREM, Y_INTEGER, Y_DENOMINATOR
    g0052 = import_bound("g0053_worker_g0052", G0052_SCRIPT, EXPECTED_G0052_SCRIPT_HASH)
    THEOREM = g0052.load_theorem()
    Y_INTEGER = dict(y_entries)
    Y_DENOMINATOR = denominator


def mass4_worker(payload: tuple[str, dict[str, object]]) -> dict[str, object]:
    kind, record = payload
    pair, active = compact_pair(record)
    counter = THEOREM.permutation_t_counter_dp(pair, active)
    _linear, local_hinges_counter = THEOREM.primitive_normal_form(counter, active)
    local_hinges = {direction: value for direction, value in local_hinges_counter.items() if value}
    pairing_numerator = 0
    if active == N:
        for direction, value in local_hinges.items():
            pairing_numerator += Y_INTEGER.get(direction, 0) * value
        hinge_payload = [
            [list(direction), value] for direction, value in sorted(local_hinges.items())
        ]
        hinge_fingerprint = canonical_sha256(hinge_payload)
    else:
        multiplier = factorial(N - active)
        for positions in combinations(range(N), active):
            for local_direction, value in local_hinges.items():
                embedded = [0] * N
                for index, coordinate in enumerate(local_direction):
                    embedded[positions[index]] = coordinate
                pairing_numerator += (
                    Y_INTEGER.get(tuple(embedded), 0) * multiplier * value
                )
        hinge_fingerprint = None

    full_pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    binary = THEOREM.binary_chamber_vector_from_full_symmetry(full_pair, N)
    invariant = THEOREM.dot(THEOREM.alternating_invariant(N), binary)
    delta_numerator = invariant * Y_DENOMINATOR - pairing_numerator
    return {
        "kind": kind,
        "sequence": int(record["sequence"]),
        "active_vertices": active,
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "abs_components": int(record["abs_components"]),
        "invariant": invariant,
        "pairing_numerator": pairing_numerator,
        "delta_numerator": delta_numerator,
        "local_hinge_support_size": len(local_hinges),
        "hinge_fingerprint_sha256": hinge_fingerprint,
        "distinct_subset_DP_T_keys": len(counter),
    }


def read_mass4_records(theorem: Any) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    full: list[dict[str, object]] = []
    proper_groups: dict[tuple[int, int, int], list[dict[str, object]]] = defaultdict(list)
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        next(source)
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            active = int(record["active_vertices"])
            if active == N:
                full.append(record)
            else:
                key = (
                    active,
                    int(record["negative_loop_count"])
                    + int(record["positive_loop_count"]),
                    int(record["abs_beta"]),
                )
                proper_groups[key].append(record)
    sample: list[dict[str, object]] = []
    for key in sorted(proper_groups):
        records = proper_groups[key]
        indices = sorted({0, (len(records) - 1) // 2, len(records) - 1})
        sample.extend(records[index] for index in indices)
    sample.sort(key=lambda record: int(record["sequence"]))
    if len(full) != 1_465 or len(proper_groups) != 167 or len(sample) != 470:
        raise AssertionError(
            f"mass4 sample census drift: full={len(full)}, strata={len(proper_groups)}, sample={len(sample)}"
        )
    return full, sample


def group_delta_reports(
    results: list[dict[str, object]], key_name: str, key_function: Any, denominator: int
) -> list[dict[str, object]]:
    groups: dict[Hashable, list[dict[str, object]]] = defaultdict(list)
    for result in results:
        groups[key_function(result)].append(result)
    reports = []
    for key, members in sorted(groups.items(), key=lambda item: str(item[0])):
        deltas = [int(member["delta_numerator"]) for member in members]
        reports.append(
            {
                key_name: list(key) if isinstance(key, tuple) else key,
                "count": len(members),
                "zero_discrepancy_count": sum(value == 0 for value in deltas),
                "nonzero_discrepancy_count": sum(value != 0 for value in deltas),
                "discrepancy_histogram": {
                    fraction_string(value, denominator): count
                    for value, count in sorted(Counter(deltas).items())
                },
            }
        )
    return reports


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    if sha256_path(G0050_REPORT) != EXPECTED_G0050_REPORT_HASH:
        raise ValueError("G0050 report drift")
    if sha256_path(G0052_REPORT) != EXPECTED_G0052_REPORT_HASH:
        raise ValueError("G0052 report drift")
    g0050 = import_bound("g0053_g0050", G0050_SCRIPT, EXPECTED_G0050_SCRIPT_HASH)
    g0052 = import_bound("g0053_g0052", G0052_SCRIPT, EXPECTED_G0052_SCRIPT_HASH)
    bridge_report = load_json_gz(G0050_REPORT)
    census_report = load_json_gz(G0052_REPORT)
    extract = g0050.import_extract()
    search = extract.load_search()

    matrix, _records, degree3_rows = g0050.build_complete_matrix(search, workers)
    if canonical_sha256([list(direction) for direction in degree3_rows]) != bridge_report[
        "complete_integer_matrix"
    ]["row_order_sha256"]:
        raise AssertionError("degree3 row order drift")
    basis_columns = list(
        map(int, bridge_report["fixed_exact_basis"]["proper_basis_column_indices"])
    )
    solve_rows = list(map(int, bridge_report["fixed_exact_basis"]["solve_row_indices"]))
    witness_rows = list(
        map(int, bridge_report["seed_quotient_certificate"]["witness_row_indices"])
    )
    support_rows = solve_rows + witness_rows
    support_columns = basis_columns + [3307, 3308, 3309]
    if len(support_rows) != 491 or len(set(support_rows)) != 491:
        raise AssertionError("dual support row census drift")
    square = fmpz_mat(matrix[np.ix_(support_rows, support_columns)].tolist())
    if int(square.rank()) != 491:
        raise AssertionError("dual square matrix is singular")
    rhs = fmpz_mat([[0]] * 488 + [[LAMBDA_SEED]] * 3)
    y = square.transpose().solve(rhs)
    prices = y.transpose() * fmpz_mat(matrix[support_rows, :].tolist())
    expected_prices = [0] * 3307 + [LAMBDA_SEED] * 3
    if any(prices[0, column] != expected_prices[column] for column in range(3310)):
        first = next(
            column
            for column in range(3310)
            if prices[0, column] != expected_prices[column]
        )
        raise AssertionError(f"exact dual pricing failed at column {first}")

    denominator = 1
    for row in range(y.nrows()):
        denominator = lcm(denominator, q_pair(y[row, 0])[1])
    integer_coefficients = []
    for row in range(y.nrows()):
        numerator, local_denominator = q_pair(y[row, 0])
        integer_coefficients.append(numerator * (denominator // local_denominator))
    common_divisor = denominator
    for coefficient in integer_coefficients:
        common_divisor = gcd(common_divisor, abs(coefficient))
    if common_divisor > 1:
        denominator //= common_divisor
        integer_coefficients = [value // common_divisor for value in integer_coefficients]
    sparse_entries = [
        {
            "degree3_seed_first_row_index": row_index,
            "direction": list(degree3_rows[row_index]),
            "numerator": coefficient,
            "denominator": denominator,
        }
        for row_index, coefficient in zip(support_rows, integer_coefficients, strict=True)
        if coefficient
    ]
    y_integer = {
        degree3_rows[row_index]: coefficient
        for row_index, coefficient in zip(support_rows, integer_coefficients, strict=True)
        if coefficient
    }
    if len(y_integer) != len(sparse_entries):
        raise AssertionError("dual support direction collision")

    degree4_rows = g0052.degree4_direction_universe()
    degree4_payload = [list(direction) for direction in degree4_rows]
    degree4_hash = canonical_sha256(degree4_payload)
    if degree4_hash != census_report["complete_degree4_hinge_semantics"][
        "primitive_directions_sha256"
    ]:
        raise AssertionError("degree4 universe hash drift")
    degree4_set = set(degree4_rows)
    escaped = sorted(set(y_integer) - degree4_set)
    if escaped:
        raise AssertionError(f"dual direction does not embed in degree4 universe: {escaped[0]}")
    dense_embedding_hash = hashlib.sha256()
    dense_embedding_hash.update(
        f"degree4-lex-fmpq;rows={len(degree4_rows)}\n".encode()
    )
    for direction in degree4_rows:
        dense_embedding_hash.update(
            f"{y_integer.get(direction, 0)}/{denominator};".encode()
        )

    mutant_y = fmpq_mat(y)
    mutant_y[0, 0] += 1
    mutant_prices = mutant_y.transpose() * fmpz_mat(matrix[support_rows, :].tolist())
    mutant_first_column = next(
        column
        for column in range(3310)
        if mutant_prices[0, column] != expected_prices[column]
    )

    theorem = g0052.load_theorem()
    full_records, proper_sample = read_mass4_records(theorem)
    payloads = [("full", record) for record in full_records] + [
        ("proper_sample", record) for record in proper_sample
    ]
    mass4_results: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_mass4_worker,
        initargs=(list(y_integer.items()), denominator),
        maxtasksperchild=32,
    ) as pool:
        for result in pool.imap_unordered(mass4_worker, payloads, chunksize=1):
            mass4_results.append(result)
            if len(mass4_results) % 100 == 0 or len(mass4_results) == len(payloads):
                print(
                    f"G0053_DUAL mass4={len(mass4_results)}/{len(payloads)}",
                    file=sys.stderr,
                    flush=True,
                )
    mass4_results.sort(key=lambda result: (str(result["kind"]), int(result["sequence"])))
    full_results = [result for result in mass4_results if result["kind"] == "full"]
    sample_results = [
        result for result in mass4_results if result["kind"] == "proper_sample"
    ]
    if len(full_results) != 1465 or len(sample_results) != 470:
        raise AssertionError("mass4 result census drift")

    census_by_sequence = {
        int(item["sequence"]): item for item in census_report["per_record_summaries"]
    }
    for result in full_results:
        frozen = census_by_sequence[int(result["sequence"])]
        if int(result["invariant"]) != int(frozen["invariant"]):
            raise AssertionError("mass4 invariant disagrees with G0052")
        if result["hinge_fingerprint_sha256"] != frozen["hinge_fingerprint_sha256"]:
            raise AssertionError("mass4 hinge fingerprint disagrees with G0052")
    if any(int(result["invariant"]) for result in sample_results):
        raise AssertionError("proper sample escaped the exact finite-difference kernel")

    full_delta_histogram = Counter(int(result["delta_numerator"]) for result in full_results)
    sample_delta_histogram = Counter(
        int(result["delta_numerator"]) for result in sample_results
    )
    full_first_failure = next(
        (result for result in full_results if int(result["delta_numerator"])), None
    )
    sample_first_failure = next(
        (result for result in sample_results if int(result["delta_numerator"])), None
    )
    per_record = [
        {
            "kind": result["kind"],
            "sequence": int(result["sequence"]),
            "active_vertices": int(result["active_vertices"]),
            "topology": [
                int(result["negative_loop_count"]),
                int(result["positive_loop_count"]),
                int(result["abs_beta"]),
                int(result["abs_components"]),
            ],
            "lambda": int(result["invariant"]),
            "dual_pairing": fraction_string(
                int(result["pairing_numerator"]), denominator
            ),
            "discrepancy_lambda_minus_dual": fraction_string(
                int(result["delta_numerator"]), denominator
            ),
            "local_hinge_support_size": int(result["local_hinge_support_size"]),
        }
        for result in mass4_results
    ]

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("dual extension script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": (
            "MASS3_DUAL_EXTENDS_ON_TESTED_MASS4_ATOMS"
            if not any(full_delta_histogram) and not any(sample_delta_histogram)
            else "MASS4_EXACTLY_ESCAPES_MASS3_DUAL"
        ),
        "script_sha256": script_hash_before,
        "bindings": {
            "g0050_exact_bridge_script_sha256": EXPECTED_G0050_SCRIPT_HASH,
            "g0050_exact_bridge_report_sha256": EXPECTED_G0050_REPORT_HASH,
            "g0052_mass4_census_script_sha256": EXPECTED_G0052_SCRIPT_HASH,
            "g0052_mass4_census_report_sha256": EXPECTED_G0052_REPORT_HASH,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "exact_mass3_dual": {
            "equations_verified": 3310,
            "proper_column_prices": 0,
            "three_seed_prices": LAMBDA_SEED,
            "candidate_support_rows": len(support_rows),
            "nonzero_support_size": len(sparse_entries),
            "common_denominator": denominator,
            "sparse_entries": sparse_entries,
            "sparse_entries_sha256": canonical_sha256(sparse_entries),
            "degree4_dense_embedding_sha256": dense_embedding_hash.hexdigest(),
            "all_dual_directions_embed_in_degree4_universe": True,
            "degree4_universe_sha256": degree4_hash,
        },
        "dual_controls": {
            "first_dual_coefficient_plus_one_mutant": {
                "rejected": True,
                "lex_first_mispriced_mass3_column": mutant_first_column,
                "observed_price": str(mutant_prices[0, mutant_first_column]),
                "expected_price": expected_prices[mutant_first_column],
            },
            "all_full_mass4_invariants_and_hinge_hashes_match_G0052": True,
            "all_470_sampled_proper_mass4_invariants_are_zero": True,
        },
        "full_core_mass4_discrepancy": {
            "tested_records": len(full_results),
            "zero_count": full_delta_histogram.get(0, 0),
            "nonzero_count": len(full_results) - full_delta_histogram.get(0, 0),
            "histogram": {
                fraction_string(value, denominator): count
                for value, count in sorted(full_delta_histogram.items())
            },
            "lex_first_nonzero": (
                {
                    "sequence": int(full_first_failure["sequence"]),
                    "lambda": int(full_first_failure["invariant"]),
                    "dual_pairing": fraction_string(
                        int(full_first_failure["pairing_numerator"]), denominator
                    ),
                    "discrepancy": fraction_string(
                        int(full_first_failure["delta_numerator"]), denominator
                    ),
                }
                if full_first_failure is not None
                else None
            ),
        },
        "proper_core_mass4_stratified_sample": {
            "stratification": (
                "For each of 167 nonempty (active_vertices,total_loops,abs_beta) strata, select "
                "the first, middle, and last stream records, deduplicating strata of size <3."
            ),
            "tested_records": len(sample_results),
            "sample_sequences_sha256": canonical_sha256(
                [int(result["sequence"]) for result in sample_results]
            ),
            "zero_count": sample_delta_histogram.get(0, 0),
            "nonzero_count": len(sample_results) - sample_delta_histogram.get(0, 0),
            "histogram": {
                fraction_string(value, denominator): count
                for value, count in sorted(sample_delta_histogram.items())
            },
            "lex_first_nonzero": (
                {
                    "sequence": int(sample_first_failure["sequence"]),
                    "active_vertices": int(sample_first_failure["active_vertices"]),
                    "dual_pairing": fraction_string(
                        int(sample_first_failure["pairing_numerator"]), denominator
                    ),
                    "discrepancy": fraction_string(
                        int(sample_first_failure["delta_numerator"]), denominator
                    ),
                }
                if sample_first_failure is not None
                else None
            ),
        },
        "discrepancy_by_topology": group_delta_reports(
            full_results,
            "topology",
            lambda result: (
                int(result["negative_loop_count"]),
                int(result["positive_loop_count"]),
                int(result["abs_beta"]),
                int(result["abs_components"]),
            ),
            denominator,
        ),
        "discrepancy_by_lambda": group_delta_reports(
            full_results,
            "lambda",
            lambda result: int(result["invariant"]),
            denominator,
        ),
        "per_record_discrepancies": per_record,
        "per_record_discrepancies_sha256": canonical_sha256(per_record),
        "claim_boundary": (
            "The dual is exact on all frozen signed-mass<=3 columns. Its mass-4 evaluation is "
            "exact on all 1,465 full-core atoms but only on a deterministic 470-record sample "
            "of the 132,728 proper-core atoms. Nonzero discrepancy diagnoses failure of this "
            "particular dual extension; zero discrepancy would not prove a full mass-4 no-go "
            "without checking every proper-core column and the complete mass-4 span."
        ),
        "wall_seconds": time.perf_counter() - started,
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
