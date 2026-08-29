#!/usr/bin/env python3
"""Complete all-10,065-row replay of the sparse G-0047 low-mass candidates.

The input coefficient vectors were fitted on 5,000 hinge directions.  This
gate regenerates the complete primitive degree-three hinge normal form for
their common 35-column support.  If hinges vanish, it computes the exact
modular F_1,...,F_10 correction needed to obtain MAX11, including canonical
degree-five common-nonloop padding.

Zero residual remains a finite-field identity.  Rational reconstruction and
an exact-Q replay are mandatory before any MAX11 construction claim.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
EXTRACT_SCRIPT = HERE / "low_mass_quotient_extract.py"
EXTRACT_REPORT = HERE / "low_mass_quotient_extract_v1.json.gz"
EXPECTED_EXTRACT_SCRIPT_HASH = (
    "55077ec87d8e49f71c93c484dd7fc0ad75962d25baa05af93d61e0e0e3d3c9d6"
)
EXPECTED_EXTRACT_REPORT_HASH = (
    "ed4831af259606018b1807081d01451cad26bc14a97414bfbfd50cb41fe67fb9"
)
DEFAULT_OUTPUT = HERE / "low_mass_complete_replay_v1.json.gz"
SCHEMA = "max11-g0047-low-mass-complete-replay-v1"
N = 11

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

SEARCH: Any = None
G47: Any = None


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_extract() -> tuple[Any, dict[str, object]]:
    if sha256_path(EXTRACT_SCRIPT) != EXPECTED_EXTRACT_SCRIPT_HASH:
        raise ValueError("quotient extract script drift")
    if sha256_path(EXTRACT_REPORT) != EXPECTED_EXTRACT_REPORT_HASH:
        raise ValueError("quotient extract report drift")
    spec = importlib.util.spec_from_file_location("g0047_quotient_extract", EXTRACT_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import quotient extractor")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    with gzip.open(EXTRACT_REPORT, "rt", encoding="utf-8") as source:
        report = json.load(source)
    if report.get("result") != "TWO_PRIME_NONZERO_INVARIANT_LOW_MASS_RELATION_ON_5000_ROWS":
        raise ValueError("quotient report is not favorable")
    return module, report


def init_worker() -> None:
    global SEARCH, G47
    extract, _report = load_extract()
    SEARCH = extract.load_search()
    G47 = SEARCH.load_g47()


def complete_column_worker(record: dict[str, object]) -> tuple[int, dict[Direction, int], tuple[int, ...]]:
    pair, active = SEARCH.compact_pair(record)
    _linear, local_hinges = G47.primitive_normal_form(
        G47.permutation_t_counter_dp(pair, active), active
    )
    multiplier = factorial(N - active)
    hinges: dict[Direction, int] = {}
    for positions in combinations(range(N), active):
        for local_direction, weight in local_hinges.items():
            embedded = [0] * N
            for index, value in enumerate(local_direction):
                embedded[positions[index]] = value
            direction = tuple(embedded)
            hinges[direction] = hinges.get(direction, 0) + multiplier * weight

    full_pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    core_vector = list(G47.binary_chamber_vector_from_full_symmetry(full_pair, N))
    signed_mass = int(record["signed_mass"])
    carry_scale = 2 * (5 - signed_mass) * factorial(N - 2)
    f2 = G47.subset_max_vector(N, 2)
    padded_vector = tuple(
        core_vector[index] + carry_scale * f2[index] for index in range(N)
    )
    return int(record["sequence"]) - 1, hinges, padded_vector


def modular_subset_basis_decomposition(vector: list[int], prime: int) -> list[int]:
    coefficients = []
    for rank in range(1, N):
        value = vector[rank - 1]
        value -= sum(
            coefficients[m - 1] * G47.comb(rank - 1, m - 1)
            for m in range(1, rank)
        )
        coefficients.append(value % prime)
    reconstructed_last = sum(
        coefficients[m - 1] * G47.comb(N - 1, m - 1) for m in range(1, N)
    ) % prime
    if reconstructed_last != vector[-1] % prime:
        raise AssertionError("correction vector is outside lower-F span")
    return coefficients


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    extract, extract_report = load_extract()
    search = extract.load_search()
    module = search.load_g47()
    records = search.load_records(module)
    universe = search.direction_universe()
    direction_set = set(universe)

    prime_inputs = []
    support: list[int] | None = None
    for result in extract_report["modular_results"]:
        relation = result.get("nonzero_binary_invariant_relation")
        if not isinstance(relation, dict):
            raise ValueError("missing favorable modular relation")
        indices = list(map(int, relation["normalized_support_indices"]))
        coefficients = list(map(int, relation["normalized_coefficients"]))
        if support is None:
            support = indices
        if indices != support or len(coefficients) != len(indices):
            raise ValueError("two-prime support mismatch")
        prime_inputs.append(
            {
                "prime": int(result["prime"]),
                "coefficients": coefficients,
            }
        )
    if support is None or len(support) != 35:
        raise ValueError("expected common 35-column support")

    payloads = [records[index] for index in support]
    columns: dict[int, tuple[dict[Direction, int], tuple[int, ...]]] = {}
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers, initializer=init_worker, maxtasksperchild=32
    ) as pool:
        for index, hinges, padded_vector in pool.imap_unordered(
            complete_column_worker, payloads, chunksize=1
        ):
            if index in columns:
                raise AssertionError("duplicate support column")
            if any(direction not in direction_set for direction in hinges):
                raise AssertionError("column hinge escaped complete degree-three universe")
            columns[index] = hinges, padded_vector
    if set(columns) != set(support):
        raise AssertionError("complete support generation mismatch")

    complete_union = set().union(*(set(columns[index][0]) for index in support))
    prime_results = []
    for item in prime_inputs:
        prime = item["prime"]
        coefficients = item["coefficients"]
        residual: dict[Direction, int] = {}
        vector = [0] * N
        for index, coefficient in zip(support, coefficients, strict=True):
            hinges, padded = columns[index]
            for direction, value in hinges.items():
                updated = (residual.get(direction, 0) + coefficient * value) % prime
                if updated:
                    residual[direction] = updated
                else:
                    residual.pop(direction, None)
            for rank, value in enumerate(padded):
                vector[rank] = (vector[rank] + coefficient * value) % prime
        target = [0] * (N - 1) + [1]
        correction = [(target[index] - vector[index]) % prime for index in range(N)]
        f_coefficients = modular_subset_basis_decomposition(correction, prime)
        invariant = module.dot(module.alternating_invariant(N), vector) % prime
        if invariant != 1:
            raise AssertionError(f"binary invariant normalization failed mod {prime}")
        prime_results.append(
            {
                "prime": prime,
                "complete_nonzero_hinge_count": len(residual),
                "complete_hinge_identity_mod_prime": not residual,
                "lex_first_residual": (
                    {"direction": list(min(residual)), "value": residual[min(residual)]}
                    if residual
                    else None
                ),
                "padded_core_ordered_binary_difference_vector": vector,
                "binary_invariant_pairing": invariant,
                "F1_through_F10_correction_coefficients": f_coefficients,
                "corrected_ordered_vector_is_MAX11": True,
            }
        )
    all_zero = all(result["complete_hinge_identity_mod_prime"] for result in prime_results)
    result = (
        "TWO_PRIME_COMPLETE_LOW_MASS_MAX11_IDENTITIES"
        if all_zero
        else "LOW_MASS_SELECTED_ROW_CANDIDATES_REFUTED_BY_COMPLETE_REPLAY"
    )
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("script changed during execution")
    report = {
        "schema": SCHEMA,
        "result": result,
        "script_sha256": script_hash_before,
        "bindings": {
            "extract_script_sha256": EXPECTED_EXTRACT_SCRIPT_HASH,
            "extract_report_sha256": EXPECTED_EXTRACT_REPORT_HASH,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "support": {
            "column_count": len(support),
            "zero_based_record_indices": support,
            "one_based_stream_sequences": [index + 1 for index in support],
            "complete_hinge_union_count": len(complete_union),
        },
        "complete_row_universe": {
            "primitive_degree_three_hinge_directions": len(universe),
            "all_complete_support_hinges_belong_to_universe": True,
        },
        "modular_results": prime_results,
        "mandatory_next_gate": (
            "If both complete residuals vanish, CRT/rationally reconstruct the shared 35 atom "
            "coefficients and ten F_m corrections, then replay every hinge and linear coefficient "
            "over exact Q with an independently transcribed checker."
        ),
        "no_claim": (
            "A two-prime complete modular identity is not a rational identity. It does not become "
            "a MAX11 network until exact rational coefficients and complete exact-Q semantics are "
            "verified; it says nothing complete about arbitrary unrestricted weights."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
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
        raise SystemExit("--workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside the project") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
