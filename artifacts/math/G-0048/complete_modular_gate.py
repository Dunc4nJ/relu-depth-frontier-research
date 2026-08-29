#!/usr/bin/env python3
"""Frozen complete modular gate for the 35-term low-mass MAX11 candidate.

This program binds the discovery inputs by SHA-256, regenerates every support
atom from the frozen G-0038 stream, and evaluates the candidate on the entire
10,065-row primitive degree-three hinge universe and all eleven ordered-cone
linear coordinates over two primes.  Positive output is still only a modular
candidate; exact reconstruction and an independent verifier remain mandatory.
"""

from __future__ import annotations

import argparse
from collections import Counter
from itertools import combinations
import gzip
import hashlib
import importlib.util
import json
from math import comb, factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0047 = ROOT / "artifacts/math/G-0047"
EXTRACT_SCRIPT = G0047 / "low_mass_quotient_extract.py"
EXTRACT_REPORT = G0047 / "low_mass_quotient_extract_v1.json.gz"
SEARCH_SCRIPT = G0047 / "low_mass_circuit_search.py"
SEARCH_REPORT = G0047 / "low_mass_circuit_search_v1.json.gz"
THEOREM_SCRIPT = G0047 / "induction_span_obstruction.py"
THEOREM_REPORT = G0047 / "induction_span_obstruction_v1.json.gz"

EXPECTED_HASHES = {
    "extract_script": "55077ec87d8e49f71c93c484dd7fc0ad75962d25baa05af93d61e0e0e3d3c9d6",
    "extract_report": "ed4831af259606018b1807081d01451cad26bc14a97414bfbfd50cb41fe67fb9",
    "search_script": "2c28663459755f631c44e2444be4c2540ae9772c26c542c7c9807e63eeee10fd",
    "search_report": "215b0d5320d4c76ffd4cf5c351bcb8722e715dde74a0e295d8d4715b83fcaa43",
    "theorem_script": "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d",
    "theorem_report": "47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a",
}
SOURCE_PATHS = {
    "extract_script": EXTRACT_SCRIPT,
    "extract_report": EXTRACT_REPORT,
    "search_script": SEARCH_SCRIPT,
    "search_report": SEARCH_REPORT,
    "theorem_script": THEOREM_SCRIPT,
    "theorem_report": THEOREM_REPORT,
}
DEFAULT_OUTPUT = HERE / "complete_modular_gate_v1.json.gz"
SCHEMA = "max11-g0048-complete-modular-gate-v1"
N = 11
EXPECTED_ROWS = 10_065
EXPECTED_SUPPORT = 35

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

SEARCH: Any = None
THEOREM: Any = None


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


def import_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_inputs() -> tuple[Any, Any, dict[str, object]]:
    observed = {name: sha256_path(path) for name, path in SOURCE_PATHS.items()}
    if observed != EXPECTED_HASHES:
        raise ValueError(f"frozen input hash drift: {observed}")
    extract = import_module("g0048_extract", EXTRACT_SCRIPT)
    search = extract.load_search()
    theorem = search.load_g47()
    with gzip.open(EXTRACT_REPORT, "rt", encoding="utf-8") as source:
        report = json.load(source)
    if report.get("result") != "TWO_PRIME_NONZERO_INVARIANT_LOW_MASS_RELATION_ON_5000_ROWS":
        raise ValueError("frozen extract report is not the favorable discovery output")
    return search, theorem, report


def init_worker() -> None:
    global SEARCH, THEOREM
    SEARCH, THEOREM, _report = load_inputs()


def padded_binary_vector(record: dict[str, object], theorem: Any) -> tuple[int, ...]:
    full_pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    core = theorem.binary_chamber_vector_from_full_symmetry(full_pair, N)
    signed_mass = int(record["signed_mass"])
    common_nonloops = 5 - signed_mass
    if not (0 <= common_nonloops <= 4):
        raise AssertionError("invalid degree-five padding count")
    carry_scale = 2 * common_nonloops * factorial(N - 2)
    f2 = theorem.subset_max_vector(N, 2)
    return tuple(core[index] + carry_scale * f2[index] for index in range(N))


def complete_column_worker(
    record: dict[str, object],
) -> tuple[int, dict[Direction, int], tuple[int, ...], int, int]:
    pair, active = SEARCH.compact_pair(record)
    counter = THEOREM.permutation_t_counter_dp(pair, active)
    _local_linear, local_hinges = THEOREM.primitive_normal_form(counter, active)
    multiplier = factorial(N - active)
    hinges: dict[Direction, int] = {}
    for positions in combinations(range(N), active):
        for local_direction, weight in local_hinges.items():
            embedded = [0] * N
            for index, value in enumerate(local_direction):
                embedded[positions[index]] = value
            direction = tuple(embedded)
            hinges[direction] = hinges.get(direction, 0) + multiplier * weight
    hinges = {direction: value for direction, value in hinges.items() if value}
    return (
        int(record["sequence"]) - 1,
        hinges,
        padded_binary_vector(record, THEOREM),
        active,
        len(counter),
    )


def lower_f_decomposition_mod(vector: list[int], prime: int) -> list[int]:
    coefficients: list[int] = []
    for rank in range(1, N):
        value = vector[rank - 1]
        value -= sum(
            coefficients[m - 1] * comb(rank - 1, m - 1)
            for m in range(1, rank)
        )
        coefficients.append(value % prime)
    last = sum(
        coefficients[m - 1] * comb(N - 1, m - 1) for m in range(1, N)
    ) % prime
    if last != vector[-1] % prime:
        raise AssertionError("correction escaped the lower-F hyperplane")
    return coefficients


def add_scaled_hinges(
    residual: dict[Direction, int],
    hinges: dict[Direction, int],
    coefficient: int,
    prime: int,
) -> None:
    for direction, value in hinges.items():
        updated = (residual.get(direction, 0) + coefficient * value) % prime
        if updated:
            residual[direction] = updated
        else:
            residual.pop(direction, None)


def first_nonzero_coordinate(vector: list[int]) -> dict[str, int] | None:
    for index, value in enumerate(vector):
        if value:
            return {"zero_based_coordinate": index, "value": value}
    return None


def support_descriptor(record: dict[str, object]) -> dict[str, object]:
    signed_mass = int(record["signed_mass"])
    return {
        "zero_based_record_index": int(record["sequence"]) - 1,
        "one_based_stream_sequence": int(record["sequence"]),
        "signed_mass": signed_mass,
        "active_vertices": int(record["active_vertices"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "canonical_common_nonloop_padding_edge": [0, 1],
        "canonical_common_nonloop_padding_multiplicity_per_branch": 5 - signed_mass,
    }


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    search, theorem, extract_report = load_inputs()
    records = search.load_records(theorem)
    universe = search.direction_universe()
    if len(universe) != EXPECTED_ROWS or len(set(universe)) != EXPECTED_ROWS:
        raise AssertionError("complete row universe census drift")
    direction_set = set(universe)

    support: list[int] | None = None
    prime_inputs: list[dict[str, object]] = []
    for result in extract_report["modular_results"]:
        relation = result.get("nonzero_binary_invariant_relation")
        if not isinstance(relation, dict):
            raise ValueError("missing modular candidate vector")
        indices = list(map(int, relation["normalized_support_indices"]))
        coefficients = list(map(int, relation["normalized_coefficients"]))
        if support is None:
            support = indices
        if indices != support or len(indices) != len(coefficients):
            raise ValueError("candidate supports disagree across primes")
        prime_inputs.append(
            {
                "prime": int(result["prime"]),
                "support_coefficients": coefficients,
                "coefficient_vector_sha256": canonical_sha256(coefficients),
            }
        )
    if support is None or len(support) != EXPECTED_SUPPORT:
        raise AssertionError("expected a common 35-record support")

    descriptors = [support_descriptor(records[index]) for index in support]
    payloads = [records[index] for index in support]
    columns: dict[int, dict[str, object]] = {}
    context = mp.get_context("fork")
    with context.Pool(processes=workers, initializer=init_worker, maxtasksperchild=32) as pool:
        for index, hinges, vector, active, t_count in pool.imap_unordered(
            complete_column_worker, payloads, chunksize=1
        ):
            if index in columns:
                raise AssertionError("duplicate support column")
            escaped = sorted(set(hinges) - direction_set)
            if escaped:
                raise AssertionError(f"support hinge escaped universe: {escaped[0]}")
            columns[index] = {
                "hinges": hinges,
                "padded_binary_vector": vector,
                "active": active,
                "t_key_count": t_count,
            }
    if set(columns) != set(support):
        raise AssertionError("support regeneration incomplete")

    subset_vectors = [theorem.subset_max_vector(N, m) for m in range(1, N)]
    target = [0] * (N - 1) + [1]
    witness = theorem.alternating_invariant(N)
    prime_results: list[dict[str, object]] = []
    for candidate in prime_inputs:
        prime = int(candidate["prime"])
        coefficients = list(map(int, candidate["support_coefficients"]))
        hinge_residual: dict[Direction, int] = {}
        atom_vector = [0] * N
        for index, coefficient in zip(support, coefficients, strict=True):
            column = columns[index]
            add_scaled_hinges(
                hinge_residual,
                column["hinges"],  # type: ignore[arg-type]
                coefficient,
                prime,
            )
            for rank, value in enumerate(column["padded_binary_vector"]):  # type: ignore[union-attr]
                atom_vector[rank] = (atom_vector[rank] + coefficient * value) % prime

        correction_vector = [
            (target[index] - atom_vector[index]) % prime for index in range(N)
        ]
        f_coefficients = lower_f_decomposition_mod(correction_vector, prime)
        corrected = atom_vector[:]
        for coefficient, f_vector in zip(f_coefficients, subset_vectors, strict=True):
            for rank, value in enumerate(f_vector):
                corrected[rank] = (corrected[rank] + coefficient * value) % prime
        linear_residual = [
            (corrected[index] - target[index]) % prime for index in range(N)
        ]
        dense_hinge_residual = [hinge_residual.get(direction, 0) for direction in universe]

        mutation_index = support[0]
        mutation_column = columns[mutation_index]
        mutant_hinges = dict(hinge_residual)
        add_scaled_hinges(
            mutant_hinges,
            mutation_column["hinges"],  # type: ignore[arg-type]
            1,
            prime,
        )
        mutant_linear = corrected[:]
        for rank, value in enumerate(mutation_column["padded_binary_vector"]):  # type: ignore[union-attr]
            mutant_linear[rank] = (mutant_linear[rank] + value) % prime
        mutant_linear_residual = [
            (mutant_linear[index] - target[index]) % prime for index in range(N)
        ]
        mutant_first_hinge = min(mutant_hinges) if mutant_hinges else None

        target_mutant = target[:]
        target_mutant[-1] = (target_mutant[-1] + 1) % prime
        target_mutant_residual = [
            (corrected[index] - target_mutant[index]) % prime for index in range(N)
        ]

        hinge_first = min(hinge_residual) if hinge_residual else None
        invariant = theorem.dot(witness, atom_vector) % prime
        if invariant != 1:
            raise AssertionError(f"candidate invariant is not normalized mod {prime}")
        coefficient_mutant_rejected = bool(mutant_hinges) or any(mutant_linear_residual)
        target_mutant_rejected = any(target_mutant_residual)
        if not coefficient_mutant_rejected or not target_mutant_rejected:
            raise AssertionError("mutation control was not rejected")
        prime_results.append(
            {
                "prime": prime,
                "tested_primitive_hinge_rows": len(dense_hinge_residual),
                "complete_hinge_residual_vector_in_frozen_row_order": dense_hinge_residual,
                "complete_hinge_residual_vector_sha256": canonical_sha256(dense_hinge_residual),
                "complete_nonzero_hinge_count": len(hinge_residual),
                "complete_hinge_identity": not hinge_residual,
                "lex_first_hinge_residual": (
                    {"direction": list(hinge_first), "value": hinge_residual[hinge_first]}
                    if hinge_first is not None
                    else None
                ),
                "padded_atom_ordered_binary_vector": atom_vector,
                "binary_invariant_pairing": invariant,
                "F1_through_F10_correction_coefficients": f_coefficients,
                "corrected_ordered_linear_vector": corrected,
                "target_MAX11_ordered_linear_vector": target,
                "all_eleven_linear_coordinate_residuals": linear_residual,
                "all_eleven_linear_coordinates_match": not any(linear_residual),
                "coefficient_plus_one_mutant": {
                    "mutated_zero_based_record_index": mutation_index,
                    "rejected": coefficient_mutant_rejected,
                    "nonzero_hinge_count": len(mutant_hinges),
                    "lex_first_hinge_residual": (
                        {
                            "direction": list(mutant_first_hinge),
                            "value": mutant_hinges[mutant_first_hinge],
                        }
                        if mutant_first_hinge is not None
                        else None
                    ),
                    "linear_coordinate_residuals": mutant_linear_residual,
                    "lex_first_linear_residual": first_nonzero_coordinate(mutant_linear_residual),
                },
                "target_plus_one_mutant": {
                    "mutated_zero_based_coordinate": N - 1,
                    "rejected": target_mutant_rejected,
                    "linear_coordinate_residuals": target_mutant_residual,
                    "lex_first_linear_residual": first_nonzero_coordinate(target_mutant_residual),
                },
            }
        )

    survived = all(
        result["complete_hinge_identity"]
        and result["all_eleven_linear_coordinates_match"]
        for result in prime_results
    )
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("gate script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": (
            "TWO_PRIME_ALL_10065_HINGES_AND_11_LINEAR_COORDINATES_PASS"
            if survived
            else "COMPLETE_REPLAY_REFUTES_SELECTED_ROW_CANDIDATE"
        ),
        "script_sha256": script_hash_before,
        "frozen_source_sha256": EXPECTED_HASHES,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "frozen_row_universe": {
            "definition": (
                "lex-sorted primitive differences of distinct weak compositions of 3 into 11 "
                "parts, excluding directions sign-definite on the ordered cone"
            ),
            "row_count": len(universe),
            "directions": [list(direction) for direction in universe],
            "directions_sha256": canonical_sha256([list(direction) for direction in universe]),
        },
        "frozen_support": {
            "column_count": len(support),
            "zero_based_record_indices": support,
            "descriptors": descriptors,
            "descriptors_sha256": canonical_sha256(descriptors),
            "regenerated_column_metadata": [
                {
                    "zero_based_record_index": index,
                    "active_vertices": columns[index]["active"],
                    "distinct_subset_DP_T_keys": columns[index]["t_key_count"],
                    "nonzero_hinge_count": len(columns[index]["hinges"]),  # type: ignore[arg-type]
                    "hinge_fingerprint_sha256": canonical_sha256(
                        [
                            [list(direction), value]
                            for direction, value in sorted(columns[index]["hinges"].items())  # type: ignore[union-attr]
                        ]
                    ),
                    "padded_binary_vector": columns[index]["padded_binary_vector"],
                }
                for index in support
            ],
        },
        "frozen_two_prime_candidate_vectors": prime_inputs,
        "modular_results": prime_results,
        "mutation_controls": {
            "coefficient_plus_one_rejected_at_both_primes": all(
                result["coefficient_plus_one_mutant"]["rejected"]  # type: ignore[index]
                for result in prime_results
            ),
            "target_plus_one_rejected_at_both_primes": all(
                result["target_plus_one_mutant"]["rejected"]  # type: ignore[index]
                for result in prime_results
            ),
        },
        "claim_boundary": (
            "PASS means only that the two frozen finite-field vectors define identities on the "
            "complete frozen primitive degree-three hinge universe and eleven ordered-cone "
            "coordinates. It is not a rational identity or a MAX11 theorem. Exact coefficient "
            "lifting and an independently implemented atom reconstruction/replay are required."
        ),
        "mandatory_next_gate": (
            "On PASS, independently reconstruct every one of the 35 support atoms by a fresh "
            "subset DP, compare exact fingerprints, then recover common integer weights and "
            "verify the complete identity over Z/Q."
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
