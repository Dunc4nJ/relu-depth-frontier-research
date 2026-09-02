#!/usr/bin/env python3
"""Lift and verify an exact separator from a NON_MEMBER row sketch.

The consumer replays the named CountSketch exactly on the finite saved-system
family, selects an augmented real-row basis in sketch-bucket space, solves for
a rational left separator, composes it with the sketch map, and checks the
resulting functional on every exact source column.
"""

from __future__ import annotations

import argparse
import gc
import json
import math
import resource
import time
from collections import defaultdict
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence

import flint

import exactlift
from support_lift import ExactColumn


MASK64 = (1 << 64) - 1
ALGORITHM = "splitmix64-chain-v1-one-bucket-random-sign"


def splitmix64(value: int) -> int:
    value = (value + 0x9E3779B97F4A7C15) & MASK64
    value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
    value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
    return (value ^ (value >> 31)) & MASK64


def finish(state: int, buckets: int) -> tuple[int, int]:
    bucket_hash = splitmix64(state ^ 0xA0761D6478BD642F)
    sign_hash = splitmix64(state ^ 0xE7037ED1A0B428DB)
    return bucket_hash % buckets, 1 if sign_hash & 1 == 0 else -1


def linear_bucket(seed: int, buckets: int, n: int, rank: int) -> tuple[int, int]:
    state = splitmix64(
        seed
        ^ 0x6C696E6561720001
        ^ ((n * 0x9E3779B9) & MASK64)
        ^ rank
    )
    return finish(state, buckets)


def hinge_bucket(seed: int, buckets: int, direction: Sequence[int]) -> tuple[int, int]:
    state = splitmix64(
        seed
        ^ 0x68696E6765000001
        ^ ((len(direction) * 0x9E3779B9) & MASK64)
    )
    for index, coordinate in enumerate(direction):
        encoded = coordinate & 0xFFFF
        state = splitmix64(
            state ^ encoded ^ ((index * 0xD6E8FEB86659FD93) & MASK64)
        )
    return finish(state, buckets)


def sketch_column(column: ExactColumn, seed: int, buckets: int) -> list[int]:
    output = [0] * buckets
    n = len(column.linear)
    for rank, coefficient in enumerate(column.linear):
        if coefficient:
            bucket, sign = linear_bucket(seed, buckets, n, rank)
            output[bucket] += sign * coefficient
    for raw_direction, coefficient in column.hinges.items():
        if coefficient:
            direction = tuple(map(int, raw_direction.split(",")))
            bucket, sign = hinge_bucket(seed, buckets, direction)
            output[bucket] += sign * coefficient
    return output


def target_sketch(n: int, seed: int, buckets: int) -> list[int]:
    output = [0] * buckets
    bucket, sign = linear_bucket(seed, buckets, n, n - 1)
    output[bucket] = sign
    return output


def load_filtered(system: Path, n: int, subject: str) -> tuple[list[ExactColumn], int]:
    columns = []
    total = 0
    for source_index, raw in enumerate(exactlift.iter_columns(system)):
        include = subject == "saved-system:all" or (
            subject == "saved-system:union-trees"
            and exactlift.is_union_spanning_tree(raw, n)
        )
        if not include:
            continue
        total += 1
        columns.append(
            ExactColumn(
                source_index=source_index,
                linear=list(map(int, raw["lin"])),
                hinges={key: int(value) for key, value in raw["h"].items()},
                left=raw["A"],
                right=raw["B"],
            )
        )
    return columns, total


def modular_fraction(value: Fraction, prime: int) -> int:
    return value.numerator % prime * pow(value.denominator % prime, -1, prime) % prime


def verify_real_separator(
    columns: Sequence[ExactColumn], separator: dict[str, Any], n: int
) -> dict[str, Any]:
    linear_weights = [exactlift.parse_fraction(value) for value in separator["linear_weights"]]
    hinge_weights = {
        direction: exactlift.parse_fraction(value)
        for direction, value in separator["hinge_weights"].items()
    }
    bad = []
    for column in columns:
        pairing = sum(
            weight * coefficient
            for weight, coefficient in zip(linear_weights, column.linear)
        )
        pairing += sum(
            hinge_weights.get(direction, Fraction()) * coefficient
            for direction, coefficient in column.hinges.items()
        )
        if pairing:
            bad.append((column.source_index, pairing))
    target_pairing = linear_weights[n - 1]
    return {
        "verdict": "PASS" if not bad and target_pairing == 1 else "FAIL",
        "columns_checked_denominator": len(columns),
        "annihilated_columns_numerator": len(columns) - len(bad),
        "nonzero_column_pairings": len(bad),
        "nonzero_column_pairing_examples": [
            {"source_index": index, "value": exactlift.fraction_text(value)}
            for index, value in bad[:10]
        ],
        "target_pairing": exactlift.fraction_text(target_pairing),
    }


def lift_separator(
    pivot_report: Path,
    sketch_index: int,
    system: Path,
    output: Path,
    report_path: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    document = json.loads(pivot_report.read_text(encoding="utf-8"))
    if document.get("schema") != "max11-streamrank-pivots-v1":
        raise ValueError("unsupported pivot report schema")
    if document["input_sha256"] != exactlift.sha256_file(system):
        raise ValueError("pivot report input digest does not match saved system")
    sketch_record = document["sketches"][sketch_index]
    if sketch_record["verdict"] != "NON_MEMBER":
        raise ValueError("separator lifting requires a NON_MEMBER sketch")
    sketch = sketch_record["sketch"]
    if sketch["algorithm"] != ALGORITHM:
        raise ValueError(f"unsupported sketch algorithm {sketch['algorithm']}")
    n = int(document["n"])
    prime = int(document["modulus"])
    seed = int(sketch["seed"])
    buckets = int(sketch["buckets"])
    columns, source_count = load_filtered(system, n, document["subject"])
    expected_count = int(document["source_columns_denominator"])
    if source_count != expected_count:
        raise ValueError(f"source denominator {source_count} != report {expected_count}")

    phase = time.monotonic()
    sketched = [sketch_column(column, seed, buckets) for column in columns]
    target = target_sketch(n, seed, buckets)
    timings = {"exact_sketch_replay_seconds": time.monotonic() - phase}

    phase = time.monotonic()
    matrix = flint.nmod_mat(buckets, source_count, prime)
    augmented = flint.nmod_mat(buckets, source_count + 1, prime)
    for column_position, values in enumerate(sketched):
        for bucket, value in enumerate(values):
            if value:
                residue = value % prime
                matrix[bucket, column_position] = residue
                augmented[bucket, column_position] = residue
    for bucket, value in enumerate(target):
        if value:
            augmented[bucket, source_count] = value % prime
    rank_a = matrix.rank()
    rank_augmented = augmented.rank()
    if (rank_a, rank_augmented) != (
        int(sketch_record["rank_a"]),
        int(sketch_record["rank_augmented"]),
    ):
        raise RuntimeError("Python exact sketch replay does not reproduce reported ranks")
    timings["modular_rank_replay_seconds"] = time.monotonic() - phase

    phase = time.monotonic()
    augmented_transpose = augmented.transpose()
    augmented_transpose_rref, augmented_row_rank = augmented_transpose.rref(inplace=True)
    if augmented_row_rank != rank_augmented:
        raise RuntimeError("augmented transpose rank mismatch")
    bucket_support = exactlift.pivot_columns(augmented_transpose_rref, rank_augmented)
    del augmented_transpose, augmented_transpose_rref, matrix, augmented
    gc.collect()

    supported_rows = flint.nmod_mat(rank_augmented, source_count + 1, prime)
    for row_position, bucket in enumerate(bucket_support):
        for column_position, values in enumerate(sketched):
            supported_rows[row_position, column_position] = values[bucket] % prime
        supported_rows[row_position, source_count] = target[bucket] % prime
    supported_rref, supported_rank = supported_rows.rref(inplace=True)
    if supported_rank != rank_augmented:
        raise RuntimeError("supported augmented rows lost rank")
    equation_support = exactlift.pivot_columns(supported_rref, rank_augmented)
    if source_count not in equation_support:
        raise RuntimeError("augmented target column is not in the exact separator minor")
    timings["separator_support_selection_seconds"] = time.monotonic() - phase
    del supported_rows, supported_rref
    gc.collect()

    phase = time.monotonic()
    square_rows = []
    for bucket in bucket_support:
        row = [
            target[bucket] if equation == source_count else sketched[equation][bucket]
            for equation in equation_support
        ]
        square_rows.append(row)
    rhs = [1 if equation == source_count else 0 for equation in equation_support]
    solution = flint.fmpq_mat(flint.fmpz_mat(square_rows).transpose()).solve(
        flint.fmpq_mat(flint.fmpz_mat(rank_augmented, 1, rhs)),
        algorithm="dixon",
    )
    bucket_coefficients = [Fraction(str(solution[row, 0])) for row in range(rank_augmented)]
    timings["exact_separator_solve_seconds"] = time.monotonic() - phase

    bucket_weights = {
        bucket: coefficient
        for bucket, coefficient in zip(bucket_support, bucket_coefficients)
        if coefficient
    }
    bad_sketch_columns = []
    for column, values in zip(columns, sketched):
        pairing = sum(coefficient * values[bucket] for bucket, coefficient in bucket_weights.items())
        if pairing:
            bad_sketch_columns.append((column.source_index, pairing))
    target_pairing = sum(coefficient * target[bucket] for bucket, coefficient in bucket_weights.items())
    if bad_sketch_columns or target_pairing != 1:
        raise RuntimeError("exact sketch-bucket separator failed its defining equations")

    linear_weights = []
    for rank in range(n):
        bucket, sign = linear_bucket(seed, buckets, n, rank)
        linear_weights.append(sign * bucket_weights.get(bucket, Fraction()))
    hinge_directions = sorted({direction for column in columns for direction in column.hinges})
    hinge_weights: dict[str, Fraction] = {}
    for raw_direction in hinge_directions:
        direction = tuple(map(int, raw_direction.split(",")))
        bucket, sign = hinge_bucket(seed, buckets, direction)
        value = sign * bucket_weights.get(bucket, Fraction())
        if value:
            hinge_weights[raw_direction] = value

    denominator_lcm = math.lcm(
        *(value.denominator for value in bucket_weights.values()),
        *(value.denominator for value in linear_weights if value),
        *(value.denominator for value in hinge_weights.values()),
    )
    separator = {
        "schema": "max11-exact-sketch-separator-v1",
        "method": "exact rational left separator on sketch buckets, composed with CountSketch",
        "pivot_report": str(pivot_report),
        "pivot_report_sha256": exactlift.sha256_file(pivot_report),
        "sketch_index": sketch_index,
        "system": str(system),
        "system_sha256": exactlift.sha256_file(system),
        "subject": document["subject"],
        "n": n,
        "prime": prime,
        "sketch": sketch,
        "bucket_weights": {
            str(bucket): exactlift.fraction_text(value)
            for bucket, value in sorted(bucket_weights.items())
        },
        "linear_weights": [exactlift.fraction_text(value) for value in linear_weights],
        "hinge_weights": {
            direction: exactlift.fraction_text(value)
            for direction, value in hinge_weights.items()
        },
        "coefficient_denominator_lcm": denominator_lcm,
    }
    exact_verification = verify_real_separator(columns, separator, n)
    if exact_verification["verdict"] != "PASS" or exact_verification["target_pairing"] != "1":
        raise RuntimeError("composed real-row separator failed exact all-column verification")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(separator, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    timings["total_seconds"] = time.monotonic() - started
    report = {
        "verdict": "PASS",
        "subject": document["subject"],
        "prime": prime,
        "source_columns_denominator": source_count,
        "rank_a": rank_a,
        "rank_augmented": rank_augmented,
        "sketch_buckets_denominator": buckets,
        "nonzero_bucket_weights_numerator": len(bucket_weights),
        "real_hinge_union_denominator": len(hinge_directions),
        "nonzero_real_hinge_weights_numerator": len(hinge_weights),
        "coefficient_denominator_lcm": denominator_lcm,
        "exact_verification": exact_verification,
        "timings_seconds": timings,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "separator": str(output),
        "separator_sha256": exactlift.sha256_file(output),
        "no_claim": "This separator concerns only the named finite sketched source family; it is not a MAX11 or unrestricted depth lower bound.",
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def mutate_separator(separator_path: Path, output: Path, delta: Fraction) -> dict[str, Any]:
    separator = json.loads(separator_path.read_text(encoding="utf-8"))
    weights = separator["linear_weights"]
    for index, raw in enumerate(weights):
        value = exactlift.parse_fraction(raw)
        if value:
            weights[index] = exactlift.fraction_text(value + delta)
            separator["mutation"] = {
                "source_separator": str(separator_path),
                "source_separator_sha256": exactlift.sha256_file(separator_path),
                "coordinate": f"linear:{index}",
                "delta": exactlift.fraction_text(delta),
            }
            break
    else:
        raise ValueError("separator has no nonzero linear weight to mutate")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(separator, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return separator


def verify_file(system: Path, separator_path: Path, output: Path) -> dict[str, Any]:
    separator = json.loads(separator_path.read_text(encoding="utf-8"))
    columns, count = load_filtered(system, int(separator["n"]), separator["subject"])
    verification = verify_real_separator(columns, separator, int(separator["n"]))
    report = {
        **verification,
        "system": str(system),
        "system_sha256": exactlift.sha256_file(system),
        "separator": str(separator_path),
        "separator_sha256": exactlift.sha256_file(separator_path),
        "source_columns_denominator": count,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    lift = commands.add_parser("lift")
    lift.add_argument("--pivot-report", type=Path, required=True)
    lift.add_argument("--sketch-index", type=int, default=0)
    lift.add_argument("--system", type=Path, required=True)
    lift.add_argument("--output", type=Path, required=True)
    lift.add_argument("--report", type=Path, required=True)
    mutate = commands.add_parser("mutate")
    mutate.add_argument("--separator", type=Path, required=True)
    mutate.add_argument("--delta", default="1")
    mutate.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("--system", type=Path, required=True)
    verify.add_argument("--separator", type=Path, required=True)
    verify.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "lift":
        report = lift_separator(args.pivot_report, args.sketch_index, args.system, args.output, args.report)
    elif args.command == "mutate":
        mutated = mutate_separator(args.separator, args.output, exactlift.parse_fraction(args.delta))
        report = {"verdict": "PASS", "output": str(args.output), "mutation": mutated["mutation"]}
    else:
        report = verify_file(args.system, args.separator, args.output)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
