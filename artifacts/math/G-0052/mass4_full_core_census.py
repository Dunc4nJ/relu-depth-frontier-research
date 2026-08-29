#!/usr/bin/env python3
"""Exact census of all 1,465 full-core signed-mass-4 MAX11 orbit atoms."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import combinations_with_replacement
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Hashable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
THEOREM_SCRIPT = ROOT / "artifacts/math/G-0047/induction_span_obstruction.py"
THEOREM_REPORT = ROOT / "artifacts/math/G-0047/induction_span_obstruction_v1.json.gz"
EXPECTED_THEOREM_SCRIPT_HASH = "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d"
EXPECTED_THEOREM_REPORT_HASH = "47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a"
EXPECTED_STREAM_HASH = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
DEFAULT_OUTPUT = HERE / "mass4_full_core_census_v1.json.gz"
SCHEMA = "max11-g0052-mass4-full-core-census-v1"
N = 11
EXPECTED_MASS4 = 134_193
EXPECTED_FULL = 1_465
EXPECTED_DEGREE4_DIRECTIONS = 99_858

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

THEOREM: Any = None


def weak_compositions(
    total: int, parts: int, prefix: Direction = ()
) -> Any:
    if parts == 1:
        yield prefix + (total,)
        return
    for first in range(total + 1):
        yield from weak_compositions(total - first, parts - 1, prefix + (first,))


def degree4_direction_universe() -> tuple[Direction, ...]:
    compositions = tuple(weak_compositions(4, N))
    directions: set[Direction] = set()
    for left, right in combinations_with_replacement(compositions, 2):
        if left == right:
            continue
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        directions.add(tuple(value // divisor for value in direction))
    result = tuple(sorted(directions))
    if len(result) != EXPECTED_DEGREE4_DIRECTIONS:
        raise AssertionError(f"degree-4 direction census drift: {len(result)}")
    return result


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


def load_theorem() -> Any:
    if sha256_path(THEOREM_SCRIPT) != EXPECTED_THEOREM_SCRIPT_HASH:
        raise ValueError("G-0047 theorem script drift")
    if sha256_path(THEOREM_REPORT) != EXPECTED_THEOREM_REPORT_HASH:
        raise ValueError("G-0047 theorem report drift")
    spec = importlib.util.spec_from_file_location("g0052_theorem", THEOREM_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import G-0047 theorem")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    if sha256_path(module.SIGNED_STREAM) != EXPECTED_STREAM_HASH:
        raise ValueError("G-0038 stream drift")
    return module


def read_mass4(theorem: Any) -> tuple[dict[str, object], list[dict[str, object]], Counter[int]]:
    full: list[dict[str, object]] = []
    active_histogram: Counter[int] = Counter()
    mass4_count = 0
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise ValueError("missing G-0038 stream header")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            mass4_count += 1
            active = int(record["active_vertices"])
            active_histogram[active] += 1
            if active == N:
                full.append(record)
    if mass4_count != EXPECTED_MASS4 or len(full) != EXPECTED_FULL:
        raise AssertionError(f"mass-4 census drift: {mass4_count}, {len(full)}")
    sequences = [int(record["sequence"]) for record in full]
    if sequences != list(range(136_039, 137_504)):
        raise AssertionError("full-core sequence block is not the frozen contiguous interval")
    return header, full, active_histogram


def init_worker() -> None:
    global THEOREM
    THEOREM = load_theorem()


def padded_linear_and_binary(
    pair: Pair, core_linear: tuple[int, ...]
) -> tuple[tuple[int, ...], tuple[int, ...]]:
    core_binary = THEOREM.binary_chamber_vector_from_full_symmetry(pair, N)
    carry_scale = 2 * factorial(N - 2)
    f2 = THEOREM.subset_max_vector(N, 2)
    padded_linear = tuple(
        core_linear[index] + carry_scale * f2[index] for index in range(N)
    )
    padded_binary = tuple(
        core_binary[index] + carry_scale * f2[index] for index in range(N)
    )
    return padded_linear, padded_binary


def binary_vector_from_normal_form(
    linear: tuple[int, ...], hinges: dict[Direction, int]
) -> tuple[int, ...]:
    values = [0]
    for top_count in range(1, N + 1):
        start = N - top_count
        value = sum(linear[start:])
        for direction, weight in hinges.items():
            argument = sum(direction[start:])
            if argument > 0:
                value += weight * argument
        values.append(value)
    coefficients = [0] * N
    for top_count in range(1, N + 1):
        coefficients[N - top_count] = values[top_count] - values[top_count - 1]
    return tuple(coefficients)


def worker(record: dict[str, object]) -> dict[str, object]:
    pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    counter = THEOREM.permutation_t_counter_dp(pair, N)
    core_linear, hinge_counter = THEOREM.primitive_normal_form(counter, N)
    hinges = {direction: value for direction, value in hinge_counter.items() if value}
    padded_linear, padded_binary = padded_linear_and_binary(pair, core_linear)
    reconstructed_binary = binary_vector_from_normal_form(padded_linear, hinges)
    if reconstructed_binary != padded_binary:
        raise AssertionError(f"binary/normal-form mismatch at sequence {record['sequence']}")
    invariant = THEOREM.dot(THEOREM.alternating_invariant(N), padded_binary)
    return {
        "sequence": int(record["sequence"]),
        "linear": padded_linear,
        "binary": padded_binary,
        "invariant": invariant,
        "hinges": hinges,
        "t_key_count": len(counter),
    }


def normalize_form(
    linear: tuple[int, ...], hinges: tuple[tuple[Direction, int], ...]
) -> tuple[tuple[int, ...], tuple[tuple[Direction, int], ...]]:
    divisor = 0
    for value in linear:
        divisor = gcd(divisor, abs(value))
    for _direction, value in hinges:
        divisor = gcd(divisor, abs(value))
    if divisor == 0:
        return linear, hinges
    first = next(
        (value for value in linear if value),
        next((value for _direction, value in hinges if value), 1),
    )
    sign = 1 if first > 0 else -1
    return (
        tuple(sign * value // divisor for value in linear),
        tuple((direction, sign * value // divisor) for direction, value in hinges),
    )


def normalize_hinges(
    hinges: tuple[tuple[Direction, int], ...]
) -> tuple[tuple[Direction, int], ...]:
    divisor = 0
    for _direction, value in hinges:
        divisor = gcd(divisor, abs(value))
    if divisor == 0:
        return hinges
    first = next(value for _direction, value in hinges if value)
    sign = 1 if first > 0 else -1
    return tuple((direction, sign * value // divisor) for direction, value in hinges)


def distribution_summary(values: list[int]) -> dict[str, object]:
    ordered = sorted(values)
    count = len(ordered)
    return {
        "count": count,
        "minimum": ordered[0],
        "lower_quartile": ordered[(count - 1) // 4],
        "median": ordered[(count - 1) // 2],
        "upper_quartile": ordered[(3 * (count - 1)) // 4],
        "maximum": ordered[-1],
        "mean": str(Fraction(sum(ordered), count)),
        "histogram": {str(key): value for key, value in sorted(Counter(ordered).items())},
    }


def class_summary(classes: dict[Hashable, list[int]]) -> dict[str, object]:
    sizes = Counter(len(sequences) for sequences in classes.values())
    nontrivial = sorted(
        (sorted(sequences) for sequences in classes.values() if len(sequences) > 1),
        key=lambda sequences: (len(sequences), sequences),
    )
    return {
        "class_count": len(classes),
        "class_size_histogram": {str(key): value for key, value in sorted(sizes.items())},
        "nontrivial_class_count": len(nontrivial),
        "nontrivial_sequence_classes": nontrivial,
    }


def topology_key(record: dict[str, object]) -> tuple[int, int, int, int]:
    return (
        int(record["negative_loop_count"]),
        int(record["positive_loop_count"]),
        int(record["abs_beta"]),
        int(record["abs_components"]),
    )


def grouped_reports(
    records_by_sequence: dict[int, dict[str, object]],
    results: list[dict[str, object]],
    key_name: str,
    key_function: Any,
) -> list[dict[str, object]]:
    groups: dict[Hashable, list[dict[str, object]]] = defaultdict(list)
    for result in results:
        record = records_by_sequence[int(result["sequence"])]
        groups[key_function(record)].append(result)
    reports = []
    for key, members in sorted(groups.items(), key=lambda item: str(item[0])):
        invariants = [int(member["invariant"]) for member in members]
        hinge_sizes = [len(member["hinges"]) for member in members]
        reports.append(
            {
                key_name: list(key) if isinstance(key, tuple) else key,
                "record_count": len(members),
                "zero_invariant_count": sum(value == 0 for value in invariants),
                "nonzero_invariant_count": sum(value != 0 for value in invariants),
                "invariant_histogram": {
                    str(value): count for value, count in sorted(Counter(invariants).items())
                },
                "hinge_support_minimum": min(hinge_sizes),
                "hinge_support_median": sorted(hinge_sizes)[(len(hinge_sizes) - 1) // 2],
                "hinge_support_maximum": max(hinge_sizes),
            }
        )
    return reports


def descriptor(record: dict[str, object]) -> dict[str, object]:
    return {
        "sequence": int(record["sequence"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "abs_components": int(record["abs_components"]),
    }


def self_test(theorem: Any) -> dict[str, object]:
    loop_pair: Pair = (((0, 0), (0, 1)), ((1, 1), (1, 2)))
    dp = theorem.permutation_t_counter_dp(loop_pair, 3)
    brute = theorem.permutation_t_counter_bruteforce(loop_pair, 3)
    if dp != brute:
        raise AssertionError("loop-sensitive subset DP disagrees with direct enumeration")
    planted = [0] * N
    planted[-1] = 1
    witness = theorem.alternating_invariant(N)
    if theorem.dot(witness, planted) != 1:
        raise AssertionError("invariant target mutant control failed")
    return {
        "loop_sensitive_n3_subset_DP_matches_direct_3_factorial_enumeration": True,
        "MAX11_last_binary_coefficient_plus_one_pairs_to_one": True,
    }


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    theorem = load_theorem()
    controls = self_test(theorem)
    header, records, active_histogram = read_mass4(theorem)
    direction_universe = degree4_direction_universe()
    direction_set = set(direction_universe)
    direction_payload = [list(direction) for direction in direction_universe]
    descriptors = [descriptor(record) for record in records]
    records_by_sequence = {int(record["sequence"]): record for record in records}

    results: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(processes=workers, initializer=init_worker, maxtasksperchild=32) as pool:
        for result in pool.imap_unordered(worker, records, chunksize=1):
            results.append(result)
            if len(results) % 100 == 0 or len(results) == len(records):
                print(
                    f"G0052_MASS4 full={len(results)}/{len(records)}",
                    file=sys.stderr,
                    flush=True,
                )
    results.sort(key=lambda result: int(result["sequence"]))

    exact_full_classes: dict[Hashable, list[int]] = defaultdict(list)
    proportional_full_classes: dict[Hashable, list[int]] = defaultdict(list)
    exact_hinge_classes: dict[Hashable, list[int]] = defaultdict(list)
    proportional_hinge_classes: dict[Hashable, list[int]] = defaultdict(list)
    per_record = []
    invariants = []
    hinge_sizes = []
    hinge_masses = []
    for result in results:
        sequence = int(result["sequence"])
        linear = tuple(map(int, result["linear"]))
        hinges = tuple(sorted(result["hinges"].items()))
        invariant = int(result["invariant"])
        invariants.append(invariant)
        hinge_sizes.append(len(hinges))
        hinge_mass = sum(abs(value) for _direction, value in hinges)
        hinge_masses.append(hinge_mass)
        full_key = (linear, hinges)
        proportional_full_key = normalize_form(linear, hinges)
        exact_full_classes[full_key].append(sequence)
        proportional_full_classes[proportional_full_key].append(sequence)
        exact_hinge_classes[hinges].append(sequence)
        proportional_hinge_classes[normalize_hinges(hinges)].append(sequence)
        hinge_payload = [[list(direction), value] for direction, value in hinges]
        per_record.append(
            {
                "sequence": sequence,
                "topology": list(topology_key(records_by_sequence[sequence])),
                "invariant": invariant,
                "padded_binary_vector": list(result["binary"]),
                "hinge_support_size": len(hinges),
                "total_absolute_hinge_weight": hinge_mass,
                "distinct_subset_DP_T_keys": int(result["t_key_count"]),
                "hinge_fingerprint_sha256": canonical_sha256(hinge_payload),
                "padded_full_normal_form_sha256": canonical_sha256(
                    {"linear": list(linear), "hinges": hinge_payload}
                ),
            }
        )

    invariant_histogram = Counter(invariants)
    if not invariant_histogram:
        raise AssertionError("empty invariant census")
    global_hinge_union = set().union(*(set(result["hinges"]) for result in results))
    escaped_directions = sorted(global_hinge_union - direction_set)
    if escaped_directions:
        raise AssertionError(
            f"full-core hinge escaped degree-4 universe: {escaped_directions[0]}"
        )
    first_result = results[0]
    first_mutant = list(map(int, first_result["binary"]))
    first_mutant[-1] += 1
    original_pairing = int(first_result["invariant"])
    mutant_pairing = theorem.dot(theorem.alternating_invariant(N), first_mutant)
    if mutant_pairing != original_pairing + 1:
        raise AssertionError("binary coefficient +1 mutant was not detected")

    topology_reports = grouped_reports(
        records_by_sequence, results, "topology_signature", topology_key
    )
    total_loop_reports = grouped_reports(
        records_by_sequence,
        results,
        "total_loop_count",
        lambda record: int(record["negative_loop_count"])
        + int(record["positive_loop_count"]),
    )
    branch_loop_reports = grouped_reports(
        records_by_sequence,
        results,
        "branch_loop_pair",
        lambda record: (
            int(record["negative_loop_count"]),
            int(record["positive_loop_count"]),
        ),
    )
    beta_reports = grouped_reports(
        records_by_sequence,
        results,
        "abs_beta",
        lambda record: int(record["abs_beta"]),
    )

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("census script changed during execution")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "EXACT_FULL_CORE_SIGNED_MASS4_CENSUS_COMPLETE",
        "script_sha256": script_hash_before,
        "bindings": {
            "g0047_theorem_script_sha256": EXPECTED_THEOREM_SCRIPT_HASH,
            "g0047_theorem_report_sha256": EXPECTED_THEOREM_REPORT_HASH,
            "g0038_signed_stream_sha256": EXPECTED_STREAM_HASH,
            "g0038_census_report_sha256": header["census_report_sha256"],
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "controls": {
            **controls,
            "all_1465_direct_binary_profiles_match_exact_normal_form_evaluations": True,
            "first_record_last_binary_coefficient_plus_one_mutant": {
                "sequence": int(first_result["sequence"]),
                "original_pairing": original_pairing,
                "mutant_pairing": mutant_pairing,
                "rejected": True,
            },
        },
        "denominator_feasibility": {
            "mass4_total_records": EXPECTED_MASS4,
            "mass4_proper_core_records": EXPECTED_MASS4 - EXPECTED_FULL,
            "mass4_full_core_records": EXPECTED_FULL,
            "active_vertex_histogram": {
                str(key): value for key, value in sorted(active_histogram.items())
            },
            "naive_dense_complete_hinge_matrix_columns_through_mass4": 137_503,
            "naive_10065_by_137503_int64_bytes_if_degree3_rows_applied": (
                10_065 * 137_503 * 8
            ),
            "warning": (
                "Mass-4 hinge directions arise from degree-4 branch differences, so the true "
                "row universe is larger than the old 10,065 degree-3 universe; this byte count "
                "is only a lower-bound feasibility illustration, not a proposed matrix shape."
            ),
        },
        "complete_degree4_hinge_semantics": {
            "definition": (
                "lex-sorted primitive differences of distinct weak compositions of 4 into 11 "
                "parts, excluding directions sign-definite on the ordered cone"
            ),
            "primitive_direction_count": len(direction_universe),
            "primitive_directions_sha256": canonical_sha256(direction_payload),
            "lex_first_direction": direction_payload[0],
            "lex_last_direction": direction_payload[-1],
            "all_1465_full_core_hinges_belong_to_universe": True,
        },
        "full_core_descriptors": descriptors,
        "full_core_descriptors_sha256": canonical_sha256(descriptors),
        "invariant_census": {
            "zero_count": invariant_histogram.get(0, 0),
            "nonzero_count": EXPECTED_FULL - invariant_histogram.get(0, 0),
            "distinct_value_count": len(invariant_histogram),
            "value_histogram": {
                str(key): value for key, value in sorted(invariant_histogram.items())
            },
            "greatest_common_divisor_of_nonzero_values": (
                __import__("functools").reduce(
                    gcd, (abs(value) for value in invariants if value), 0
                )
            ),
        },
        "hinge_geometry": {
            "support_size": distribution_summary(hinge_sizes),
            "total_absolute_weight": distribution_summary(hinge_masses),
            "global_union_direction_count": len(global_hinge_union),
            "global_union_fraction_of_complete_degree4_universe": str(
                Fraction(len(global_hinge_union), len(direction_universe))
            ),
        },
        "functional_equivalence_classes": {
            "exact_padded_full_normal_form": class_summary(exact_full_classes),
            "rational_proportional_padded_full_normal_form": class_summary(
                proportional_full_classes
            ),
            "exact_hinge_column": class_summary(exact_hinge_classes),
            "rational_proportional_hinge_column": class_summary(
                proportional_hinge_classes
            ),
        },
        "topology_correlations": {
            "combined_loop_beta_component_signature": topology_reports,
            "total_loop_count": total_loop_reports,
            "ordered_branch_loop_pair": branch_loop_reports,
            "absolute_cycle_rank_beta": beta_reports,
        },
        "per_record_summaries": per_record,
        "per_record_summaries_sha256": canonical_sha256(per_record),
        "claim_boundary": (
            "This is an exact census of invariant values and ordered-cone normal forms for the "
            "1,465 frozen full-core signed-mass-4 orbit atoms, with one common nonloop padding "
            "edge. It neither computes the span with 132,728 proper-core mass-4 atoms nor proves "
            "a construction or obstruction for mass 4, mass 5, or unrestricted networks."
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
