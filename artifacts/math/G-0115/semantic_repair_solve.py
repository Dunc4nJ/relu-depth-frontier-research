#!/usr/bin/env python3
"""Solve the preregistered G-0115 coefficient-frozen MAX9 residual exactly."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import sys
import time
from typing import Iterable, Sequence

from flint import fmpq_mat, fmpz_mat, nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
BENCHMARK_PATH = HERE / "semantic_repair_benchmark_v1.json"
PREREGISTRATION_PATH = HERE / "SEMANTIC_REPAIR_PREREGISTRATION.md"
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    BENCHMARK_PATH: "89fd008dd4b3df489f4335803134233d0a5341e01e1cd8f728e3714b5996b497",
    PREREGISTRATION_PATH: "53ac0decc4252cf0649e5ab40e51834fb7ab0c90ed153197c0bffcc3256add9f",
}
PREFIXES = (256, 512, 1024, 2048, 4096, 8192, 16384, 22338)


class SolveError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SolveError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(canonical(value))
            destination.flush()
            os.fsync(destination.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def bind_inputs() -> dict[str, str]:
    observed = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()}
    require(observed == expected, f"solver binding drift: {observed}")
    benchmark = json.loads(BENCHMARK_PATH.read_text(encoding="utf-8"))
    require(benchmark.get("result") == "PASS_RESOURCE_GATE", "resource gate is not green")
    return observed


def load_kernel():
    require(sha256(KERNEL_PATH) == EXPECTED[KERNEL_PATH], "semantic kernel drift")
    spec = importlib.util.spec_from_file_location("g0115_frozen_semantic_kernel", KERNEL_PATH)
    require(spec is not None and spec.loader is not None, "cannot load semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def fraction_vector_denominator(values: Iterable[Fraction]) -> int:
    denominator = 1
    for value in values:
        denominator = math.lcm(denominator, value.denominator)
    return denominator


def pivot_columns(reduced: nmod_mat, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    cursor = 0
    for row in range(rank):
        while cursor < columns and not reduced[row, cursor]:
            cursor += 1
        require(cursor < columns, "RREF pivot extraction failed")
        pivots.append(cursor)
        cursor += 1
    return pivots


def modular_record(matrix: np.ndarray, target: np.ndarray, prime: int) -> tuple[dict[str, object], list[int]]:
    begun = time.perf_counter()
    augmented = np.ascontiguousarray(np.column_stack((matrix, target)), dtype=np.int64)
    modular = nmod_mat(
        augmented.shape[0],
        augmented.shape[1],
        memoryview(augmented.ravel()),
        prime,
    )
    reduced, augmented_rank = modular.rref()
    pivots = pivot_columns(reduced, augmented_rank, augmented.shape[1])
    candidate_rank = sum(pivot < matrix.shape[1] for pivot in pivots)
    member = matrix.shape[1] not in pivots
    require(augmented_rank == candidate_rank + (not member), "modular rank reconciliation failed")
    record = {
        "prime": prime,
        "rank": candidate_rank,
        "augmented_rank": augmented_rank,
        "target_member": member,
        "seconds": time.perf_counter() - begun,
    }
    return record, [pivot for pivot in pivots if pivot < matrix.shape[1]]


def pivot_coordinates(matrix: np.ndarray, basis_columns: Sequence[int], prime: int) -> list[int]:
    basis = np.ascontiguousarray(matrix[:, list(basis_columns)].T, dtype=np.int64)
    modular = nmod_mat(basis.shape[0], basis.shape[1], memoryview(basis.ravel()), prime)
    reduced, rank = modular.rref()
    require(rank == len(basis_columns), "selected modular column basis lost rank")
    return pivot_columns(reduced, rank, basis.shape[1])


def exact_minor_solution(
    matrix: np.ndarray,
    target: np.ndarray,
    basis_columns: Sequence[int],
    coordinate_rows: Sequence[int],
) -> list[Fraction]:
    require(len(basis_columns) == len(coordinate_rows), "minor is not square")
    size = len(basis_columns)
    minor_array = np.ascontiguousarray(
        matrix[np.ix_(list(coordinate_rows), list(basis_columns))], dtype=np.int64
    )
    rhs_array = np.ascontiguousarray(target[list(coordinate_rows)].reshape(size, 1), dtype=np.int64)
    minor_integer = fmpz_mat(size, size, memoryview(minor_array.ravel()))
    rhs_integer = fmpz_mat(size, 1, memoryview(rhs_array.ravel()))
    minor = fmpq_mat(minor_integer)
    require(bool(minor.det()), "modularly selected exact minor vanished")
    solution = minor.solve(fmpq_mat(rhs_integer))
    return [Fraction(str(solution[index, 0])) for index in range(size)]


def add_fraction_semantic(
    linear: list[Fraction],
    hinges: dict[tuple[int, ...], Fraction],
    semantic,
    coefficient: Fraction,
) -> None:
    for index, value in enumerate(semantic[0]):
        linear[index] += coefficient * int(value)
    for direction, value in semantic[1].items():
        hinges[direction] = hinges.get(direction, Fraction()) + coefficient * int(value)
        if not hinges[direction]:
            del hinges[direction]


def replay_integer_target(
    kernel,
    semantics: Sequence[object],
    basis_columns: Sequence[int],
    coefficients: Sequence[Fraction],
    target_hinges_integer: dict[tuple[int, ...], int],
    target_lambda_integer: int,
    universe: Sequence[tuple[int, ...]],
) -> tuple[bool, list[Fraction], dict[tuple[int, ...], Fraction], Fraction]:
    linear = [Fraction() for _ in range(kernel.N)]
    hinges: dict[tuple[int, ...], Fraction] = {}
    for column, coefficient in zip(basis_columns, coefficients, strict=True):
        add_fraction_semantic(linear, hinges, semantics[column], coefficient)
    observed_lambda = Fraction(kernel.lambda_value(linear))
    all_rows_equal = all(
        hinges.get(direction, Fraction()) == target_hinges_integer.get(direction, 0)
        for direction in universe
    )
    no_outside_rows = set(hinges) <= set(universe)
    return (
        all_rows_equal and no_outside_rows and observed_lambda == target_lambda_integer,
        linear,
        hinges,
        observed_lambda,
    )


def relabel_pair(pair, permutation: Sequence[int]):
    return tuple(
        tuple(sorted(tuple(sorted((permutation[u], permutation[v]))) for u, v in side))
        for side in pair
    )


def planted_controls() -> dict[str, bool]:
    member_matrix = fmpq_mat([[1, 0], [0, 1]])
    member_rhs = fmpq_mat([[1], [1]])
    member_solution = member_matrix.solve(member_rhs)
    member_pass = member_matrix * member_solution == member_rhs
    augmented = fmpq_mat([[1, 0, 0], [0, 1, 0], [0, 0, 1]])
    candidate = fmpq_mat([[1, 0], [0, 1], [0, 0]])
    nonmember_pass = int(augmented.rank()) == int(candidate.rank()) + 1
    require(member_pass and nonmember_pass, "planted solve controls failed")
    return {"member_branch": member_pass, "nonmember_branch": nonmember_pass}


def target_system(kernel, dp, retained, missing):
    public_terms = kernel.load_certificate(kernel.CERT9, kernel.N, 4)
    present_indices = {int(record["public_term_indices"][0]) for record in retained}
    missing_indices = [index for index in range(len(public_terms)) if index not in present_indices]
    require(len(missing_indices) == kernel.EXPECTED_MISSING, "missing index census drift")
    require(
        [public_terms[index] for index in missing_indices] == missing,
        "missing term order drift",
    )

    target_linear = [Fraction() for _ in range(kernel.N)]
    target_hinges: dict[tuple[int, ...], Fraction] = {}
    for coefficient, pair in missing:
        kernel.add_scaled(target_linear, target_hinges, kernel.normal_form(dp, pair), coefficient)
    target_lambda = Fraction(kernel.lambda_value(target_linear))

    retained_public_linear = [Fraction() for _ in range(kernel.N)]
    retained_public_hinges: dict[tuple[int, ...], Fraction] = {}
    retained_lift_records = []
    for position, record in enumerate(retained, start=1):
        public_index = int(record["public_term_indices"][0])
        coefficient, public_pair = public_terms[public_index]
        public_semantic = kernel.normal_form(dp, public_pair)
        lift_pair = kernel.parse_pair(record["representative"]["pair"])
        lift_semantic = kernel.normal_form(dp, lift_pair)
        require(
            public_semantic[1] == lift_semantic[1]
            and kernel.lambda_value(public_semantic[0]) == kernel.lambda_value(lift_semantic[0]),
            f"retained signed-W semantic mismatch at public term {public_index}",
        )
        kernel.add_scaled(retained_public_linear, retained_public_hinges, public_semantic, coefficient)
        retained_lift_records.append(
            {
                "coefficient": str(coefficient),
                "pair": kernel.serialize_pair(lift_pair),
                "public_term_index": public_index,
                "representative_sequence": int(record["sequence"]),
                "signed_certificate_sha256": record["signed_certificate_sha256"],
            }
        )
        if position % 64 == 0:
            print(f"G0115_RETAINED_VALIDATED {position}/{len(retained)}", flush=True)

    retained_public_lambda = Fraction(kernel.lambda_value(retained_public_linear))
    require(
        all(retained_public_hinges.get(direction, Fraction()) == -coefficient for direction, coefficient in target_hinges.items())
        and all(direction in target_hinges for direction in retained_public_hinges),
        "missing hinge residual disagrees with negative retained-public residual",
    )
    require(retained_public_lambda + target_lambda == 1, "public Lambda residual disagreement")
    return {
        "public_terms": public_terms,
        "missing_indices": missing_indices,
        "target_linear": target_linear,
        "target_hinges": target_hinges,
        "target_lambda": target_lambda,
        "retained_public_linear": retained_public_linear,
        "retained_public_hinges": retained_public_hinges,
        "retained_public_lambda": retained_public_lambda,
        "retained_lift_records": retained_lift_records,
    }


def solve(report_path: Path, certificate_path: Path, maximum_prefix: int) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = bind_inputs()
    kernel = load_kernel()
    kernel.bind_inputs()
    dp = kernel.load_dp()
    retained, repair, missing = kernel.load_map_and_targets()
    universe = kernel.direction_universe()
    row_by_direction = {direction: row for row, direction in enumerate(universe)}
    require(len(row_by_direction) == kernel.EXPECTED_DIRECTIONS, "direction universe duplicate")
    controls = {
        "planted_linear_system": planted_controls(),
        "known_MAX8": kernel.certificate_replay(dp, kernel.CERT8, 8, 3),
        "known_MAX9": kernel.certificate_replay(dp, kernel.CERT9, 9, 4),
    }
    target = target_system(kernel, dp, retained, missing)
    target_hinges = target["target_hinges"]
    target_lambda = target["target_lambda"]
    denominator = fraction_vector_denominator([*target_hinges.values(), target_lambda])
    target_hinges_integer = {
        direction: int(coefficient * denominator) for direction, coefficient in target_hinges.items()
    }
    target_lambda_integer = int(target_lambda * denominator)
    target_vector = np.zeros(len(universe) + 1, dtype=np.int64)
    for direction, coefficient in target_hinges_integer.items():
        target_vector[row_by_direction[direction]] = coefficient
    target_vector[-1] = target_lambda_integer

    first_pair = kernel.parse_pair(repair[0]["representative"]["pair"])
    first_semantic = kernel.normal_form(dp, first_pair)
    branch_swap = (first_pair[1], first_pair[0])
    cyclic = tuple((index + 1) % kernel.N for index in range(kernel.N))
    common_padded = (
        tuple(sorted(first_pair[0] + ((0, 0),))),
        tuple(sorted(first_pair[1] + ((0, 0),))),
    )
    padded_semantic = kernel.normal_form(dp, common_padded)
    metamorphic = {
        "branch_swap": kernel.normal_form(dp, branch_swap) == first_semantic,
        "relabel": kernel.normal_form(dp, relabel_pair(first_pair, cyclic)) == first_semantic,
        "common_padding_hinges": padded_semantic[1] == first_semantic[1],
        "common_padding_lambda": kernel.lambda_value(padded_semantic[0]) == kernel.lambda_value(first_semantic[0]),
    }
    require(all(metamorphic.values()), f"metamorphic controls failed: {metamorphic}")
    controls["metamorphic"] = metamorphic

    chosen = None
    prefix_records: list[dict[str, object]] = []
    semantics = []
    generation_seconds = 0.0
    prefixes = [prefix for prefix in PREFIXES if prefix <= maximum_prefix]
    require(prefixes and maximum_prefix <= len(repair), "invalid maximum prefix")
    for prefix in prefixes:
        generation_begun = time.perf_counter()
        for column in range(len(semantics), prefix):
            pair = kernel.parse_pair(repair[column]["representative"]["pair"])
            semantic = kernel.normal_form(dp, pair)
            require(set(semantic[1]) <= set(row_by_direction), f"column {column} outside direction universe")
            semantics.append(semantic)
            if (column + 1) % 64 == 0:
                print(f"G0115_SEMANTICS {column + 1}/{prefix}", flush=True)
        generation_seconds += time.perf_counter() - generation_begun

        matrix = np.zeros((len(universe) + 1, prefix), dtype=np.int64)
        for column, semantic in enumerate(semantics):
            for direction, coefficient in semantic[1].items():
                matrix[row_by_direction[direction], column] = int(coefficient)
            matrix[-1, column] = kernel.lambda_value(semantic[0])
        modular = []
        bases: dict[int, list[int]] = {}
        for prime in kernel.PRIMES:
            record, basis = modular_record(matrix, target_vector, prime)
            modular.append(record)
            bases[prime] = basis
            print(
                f"G0115_PREFIX {prefix} p={prime} rank={record['rank']} "
                f"aug={record['augmented_rank']} member={record['target_member']}",
                flush=True,
            )
        prefix_record = {
            "prefix": prefix,
            "matrix_int64_c_sha256": raw_sha256(matrix),
            "modular": modular,
        }
        prefix_records.append(prefix_record)
        member_records = [record for record in modular if record["target_member"]]
        if not member_records:
            continue

        guide = int(member_records[0]["prime"])
        basis_columns = bases[guide]
        coordinates = pivot_coordinates(matrix, basis_columns, guide)
        exact_begun = time.perf_counter()
        exact_coefficients = exact_minor_solution(matrix, target_vector, basis_columns, coordinates)
        exact_replay, repair_linear_integer, repair_hinges_integer_observed, repair_lambda_integer_observed = replay_integer_target(
            kernel,
            semantics,
            basis_columns,
            exact_coefficients,
            target_hinges_integer,
            target_lambda_integer,
            universe,
        )
        prefix_record["exact_attempt"] = {
            "guide_prime": guide,
            "basis_columns": len(basis_columns),
            "pivot_coordinates": len(coordinates),
            "minor_matrix_int64_c_sha256": raw_sha256(
                matrix[np.ix_(coordinates, basis_columns)]
            ),
            "basis_columns_int64_sha256": raw_sha256(np.asarray(basis_columns, dtype=np.int64)),
            "pivot_coordinates_int64_sha256": raw_sha256(np.asarray(coordinates, dtype=np.int64)),
            "target_replayed_exactly": exact_replay,
            "seconds": time.perf_counter() - exact_begun,
        }
        if not exact_replay:
            print(f"G0115_EXACT_MISS prefix={prefix}", flush=True)
            continue
        nonzero = [
            (column, coefficient)
            for column, coefficient in zip(basis_columns, exact_coefficients, strict=True)
            if coefficient
        ]
        require(nonzero, "exact repair is unexpectedly zero")
        mutated = list(exact_coefficients)
        first_nonzero = next(index for index, coefficient in enumerate(mutated) if coefficient)
        mutated[first_nonzero] += 1
        mutation_replay = replay_integer_target(
            kernel,
            semantics,
            basis_columns,
            mutated,
            target_hinges_integer,
            target_lambda_integer,
            universe,
        )[0]
        require(not mutation_replay, "coefficient mutation escaped complete replay")
        chosen = {
            "prefix": prefix,
            "matrix": matrix,
            "basis_columns": basis_columns,
            "pivot_coordinates": coordinates,
            "integer_coefficients": exact_coefficients,
            "nonzero": nonzero,
            "repair_linear_integer": repair_linear_integer,
            "repair_hinges_integer": repair_hinges_integer_observed,
            "repair_lambda_integer": repair_lambda_integer_observed,
        }
        break

    result = "EXACT_MEMBER" if chosen is not None else "NO_EXACT_MEMBER_IN_TESTED_PREFIXES"
    certificate = None
    certificate_hash = None
    exact_summary = None
    if chosen is not None:
        repair_terms = []
        for column, integer_coefficient in chosen["nonzero"]:
            coefficient = integer_coefficient / denominator
            record = repair[column]
            repair_terms.append(
                {
                    "coefficient": str(coefficient),
                    "integer_system_coefficient": str(integer_coefficient),
                    "pair": record["representative"]["pair"],
                    "repair_order_index": column,
                    "representative_sequence": int(record["sequence"]),
                    "signed_certificate_sha256": record["signed_certificate_sha256"],
                    "topology_distance": record["topology_distance"],
                }
            )
        missing_terms = []
        for public_index, (coefficient, pair) in zip(target["missing_indices"], missing, strict=True):
            missing_terms.append(
                {
                    "public_term_index": public_index,
                    "coefficient": str(coefficient),
                    "pair": kernel.serialize_pair(pair),
                }
            )
        certificate = {
            "schema": "max11-g0115-max9-coefficient-frozen-residual-certificate-v1",
            "n": kernel.N,
            "source_degree": 4,
            "target_denominator": denominator,
            "retained_fixed_terms": target["retained_lift_records"],
            "repair_terms": repair_terms,
            "missing_public_terms": missing_terms,
            "semantics": {
                "complete_hinge_direction_count": len(universe),
                "repair_equals_missing_hinges": True,
                "repair_equals_missing_lambda": True,
                "retained_plus_repair_hinge_count": 0,
                "retained_plus_repair_lambda": "1",
            },
            "claim_boundary": (
                "This is an exact coefficient-frozen MAX9 residual repair inside the G-0115 "
                "source-derived lift family. Lower-arity linear correction is not included here."
            ),
        }
        write_exclusive(certificate_path, certificate)
        certificate_hash = sha256(certificate_path)
        actual_repair_linear = [value / denominator for value in chosen["repair_linear_integer"]]
        retained_lift_linear = [Fraction() for _ in range(kernel.N)]
        retained_lift_hinges: dict[tuple[int, ...], Fraction] = {}
        for term in certificate["retained_fixed_terms"]:
            kernel.add_scaled(
                retained_lift_linear,
                retained_lift_hinges,
                kernel.normal_form(dp, kernel.parse_pair(term["pair"])),
                Fraction(term["coefficient"]),
            )
        require(not retained_lift_hinges or retained_lift_hinges == target["retained_public_hinges"], "retained lift hinge replay drift")
        combined_linear = [
            retained_lift_linear[index] + actual_repair_linear[index]
            for index in range(kernel.N)
        ]
        require(kernel.lambda_value(combined_linear) == 1, "combined alternating invariant drift")
        exact_summary = {
            "positive_prefix": chosen["prefix"],
            "basis_size": len(chosen["basis_columns"]),
            "nonzero_repair_coefficients": len(chosen["nonzero"]),
            "complete_hinge_rows_replayed": len(universe),
            "complete_hinge_residual_nonzeros": 0,
            "lambda_replayed": True,
            "coefficient_mutation_rejected": True,
            "retained_plus_repair_linear": [str(value) for value in combined_linear],
            "retained_plus_repair_lambda": "1",
            "certificate_path": str(certificate_path.relative_to(ROOT)),
            "certificate_sha256": certificate_hash,
            "certificate_canonical_sha256": canonical_sha(certificate),
        }

    report = {
        "schema": "max11-g0115-max9-semantic-repair-solve-v1",
        "result": result,
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "target": {
            "missing_public_terms": len(missing),
            "hinge_nonzeros": len(target_hinges),
            "lambda": str(target_lambda),
            "integer_clear_denominator": denominator,
            "target_int64_c_sha256": raw_sha256(target_vector),
            "negative_retained_public_residual_replayed": True,
        },
        "search": {
            "frozen_prefixes": list(PREFIXES),
            "maximum_prefix": maximum_prefix,
            "tested": prefix_records,
            "generation_seconds": generation_seconds,
        },
        "exact": exact_summary,
        "controls": controls,
        "claim_boundary": (
            "A positive is an exact MAX9 residual repair, not yet the compiled full MAX9 "
            "identity and not a MAX11 result. A tested-prefix miss is not a Q obstruction."
        ),
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    require(sha256(SCRIPT) == script_hash, "solver changed during execution")
    write_exclusive(report_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--maximum-prefix", type=int, default=22338)
    args = parser.parse_args(argv)
    require(not args.report.exists() and not args.certificate.exists(), "outputs must be unused")
    report = solve(args.report.resolve(), args.certificate.resolve(), args.maximum_prefix)
    print(json.dumps(report, sort_keys=True))
    return 0 if report["result"] == "EXACT_MEMBER" else 2


if __name__ == "__main__":
    raise SystemExit(main())
