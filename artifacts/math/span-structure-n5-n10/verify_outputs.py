#!/usr/bin/env python3
"""Independent full-row verifier for span_structure.py artifacts.

Unlike the producer's subset-DP, this verifier enumerates every vertex
permutation directly for every n=7 and n=8 template.  It then checks the saved
integer kernel bases and rational MAX witnesses without calling the producer's
column routine.
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import statistics
import time
from collections import defaultdict
from itertools import permutations
from pathlib import Path
from typing import Sequence

import flint


Edge = tuple[int, int]
Template = tuple[tuple[Edge, ...], tuple[Edge, ...]]
Column = tuple[tuple[int, ...], dict[tuple[int, ...], int]]


def read_jsonl_gzip(path: Path) -> list[dict[str, object]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle]


def nonpositive_on_sorted_cone(direction: Sequence[int]) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for coefficient in direction[:-1]:
        prefix += coefficient
        if prefix < 0:
            return False
    return True


def brute_column(template: Template, n: int) -> Column:
    first, second = template
    linear = [0] * n
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    for ordering in permutations(range(n)):
        position = [0] * n
        for rank, vertex in enumerate(ordering):
            position[vertex] = rank
        first_word = [0] * n
        second_word = [0] * n
        for a, b in first:
            first_word[max(position[a], position[b])] += 1
        for a, b in second:
            second_word[max(position[a], position[b])] += 1
        base, other = sorted((tuple(first_word), tuple(second_word)))
        direction = tuple(right - left for left, right in zip(base, other))
        for index, coefficient in enumerate(base):
            linear[index] += coefficient
        if nonpositive_on_sorted_cone(direction):
            continue
        divisor = math.gcd(*direction)
        primitive = tuple(coefficient // divisor for coefficient in direction)
        hinges[primitive] += divisor
    return tuple(linear), dict(hinges)


def worker(task: tuple[Template, int]) -> Column:
    return brute_column(*task)


def signature(column: Column) -> tuple[object, ...]:
    return column[0], tuple(sorted(column[1].items()))


def scale_add(
    total_linear: list[flint.fmpq],
    total_hinges: defaultdict[tuple[int, ...], flint.fmpq],
    column: Column,
    coefficient: flint.fmpq,
) -> None:
    linear, hinges = column
    for index, value in enumerate(linear):
        total_linear[index] += coefficient * value
    for direction, value in hinges.items():
        total_hinges[direction] += coefficient * value


def is_zero_combination(
    columns: Sequence[Column], entries: Sequence[tuple[int, flint.fmpq]], n: int
) -> bool:
    linear = [flint.fmpq(0) for _ in range(n)]
    hinges: defaultdict[tuple[int, ...], flint.fmpq] = defaultdict(flint.fmpq)
    for index, coefficient in entries:
        scale_add(linear, hinges, columns[index], coefficient)
    return all(value == 0 for value in linear) and all(value == 0 for value in hinges.values())


def verify_n(directory: Path, n: int, workers: int) -> dict[str, object]:
    template_rows = read_jsonl_gzip(directory / f"templates_n{n}.json.gz")
    template_rows.sort(key=lambda row: int(row["column_index"]))
    templates: list[Template] = []
    for row in template_rows:
        first = tuple(tuple(map(int, edge)) for edge in row["A"])
        second = tuple(tuple(map(int, edge)) for edge in row["B"])
        templates.append((first, second))

    if workers == 1:
        columns = [brute_column(template, n) for template in templates]
    else:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            columns = pool.map(worker, [(template, n) for template in templates], chunksize=4)

    hinge_rows = sorted({direction for _linear, hinges in columns for direction in hinges})
    row_index = {direction: index for index, direction in enumerate(hinge_rows)}
    values = [[0] * len(columns) for _ in range(len(hinge_rows) + n)]
    for column_index, (linear, hinges) in enumerate(columns):
        for direction, coefficient in hinges.items():
            values[row_index[direction]][column_index] = coefficient
        for index, coefficient in enumerate(linear):
            values[len(hinge_rows) + index][column_index] = coefficient
    matrix = flint.fmpz_mat(values)
    rank = matrix.rank()

    basis_rows = read_jsonl_gzip(directory / f"right_kernel_n{n}.jsonl.gz")
    basis_rows.sort(key=lambda row: int(row["basis_index"]))
    coefficient_matrix = flint.fmpz_mat(len(columns), len(basis_rows))
    support_sizes: list[int] = []
    for basis_index, row in enumerate(basis_rows):
        if int(row["denominator"]) != 1:
            raise AssertionError("kernel artifact is not the promised integer basis")
        entries = [(int(index), flint.fmpq(value)) for index, value in row["entries"]]
        if not is_zero_combination(columns, entries, n):
            raise AssertionError(f"kernel vector {basis_index} fails brute full-row replay")
        support_sizes.append(len(entries))
        for index, coefficient in entries:
            if coefficient.denom() != 1:
                raise AssertionError("kernel coefficient unexpectedly nonintegral")
            coefficient_matrix[index, basis_index] = int(coefficient.numer())
    basis_rank = coefficient_matrix.rank()
    if basis_rank != len(basis_rows) or rank + basis_rank != len(columns):
        raise AssertionError("saved vectors are not a full independent right-kernel basis")

    first_entries = [
        (int(index), flint.fmpq(value))
        for index, value in basis_rows[0]["entries"]
    ]
    mutated_kernel = list(first_entries)
    mutation_index = 0
    found = False
    for position, (index, coefficient) in enumerate(mutated_kernel):
        if index == mutation_index:
            mutated_kernel[position] = (index, coefficient + 1)
            found = True
            break
    if not found:
        mutated_kernel.append((mutation_index, flint.fmpq(1)))
    if is_zero_combination(columns, mutated_kernel, n):
        raise AssertionError("mutated kernel vector escaped brute verifier")

    witness = json.loads((directory / f"max_target_witness_n{n}.json").read_text())
    witness_entries = [
        (int(row["column_index"]), flint.fmpq(row["coefficient"]))
        for row in witness["coefficients"]
    ]
    linear = [flint.fmpq(0) for _ in range(n)]
    hinges: defaultdict[tuple[int, ...], flint.fmpq] = defaultdict(flint.fmpq)
    for index, coefficient in witness_entries:
        scale_add(linear, hinges, columns[index], coefficient)
    expected_linear = [flint.fmpq(0) for _ in range(n)]
    expected_linear[-1] = 1
    if linear != expected_linear or any(value != 0 for value in hinges.values()):
        raise AssertionError("MAX known-answer witness fails brute full-row replay")
    mutated_witness = list(witness_entries)
    mutated_witness[0] = (mutated_witness[0][0], mutated_witness[0][1] + 1)
    bad_linear = [flint.fmpq(0) for _ in range(n)]
    bad_hinges: defaultdict[tuple[int, ...], flint.fmpq] = defaultdict(flint.fmpq)
    for index, coefficient in mutated_witness:
        scale_add(bad_linear, bad_hinges, columns[index], coefficient)
    witness_mutation_rejected = bad_linear != expected_linear or any(
        value != 0 for value in bad_hinges.values()
    )
    if not witness_mutation_rejected:
        raise AssertionError("mutated MAX witness escaped brute verifier")

    counterexample = json.loads((directory / f"local_move_counterexample_n{n}.json").read_text())
    counterexample_entries = [
        (int(index), flint.fmpq(value)) for index, value in counterexample["entries"]
    ]
    if not is_zero_combination(columns, counterexample_entries, n):
        raise AssertionError("local-move counterexample is not an exact kernel vector")
    duplicate_groups: dict[object, int] = {}
    class_sums: defaultdict[int, flint.fmpq] = defaultdict(flint.fmpq)
    for index, coefficient in counterexample_entries:
        key = signature(columns[index])
        if key not in duplicate_groups:
            duplicate_groups[key] = len(duplicate_groups)
        class_sums[duplicate_groups[key]] += coefficient
    if not any(value != 0 for value in class_sums.values()):
        raise AssertionError("local-move counterexample has zero duplicate-class quotient")

    signature_groups: defaultdict[object, list[int]] = defaultdict(list)
    for index, column in enumerate(columns):
        signature_groups[signature(column)].append(index)
    named_relations: list[list[tuple[int, int]]] = []
    all_relations: list[list[tuple[int, int]]] = []
    for indices in signature_groups.values():
        for other in indices[1:]:
            relation = [(indices[0], 1), (other, -1)]
            named_relations.append(relation)
            all_relations.append(relation)
    quadratic_rows = read_jsonl_gzip(directory / f"quadratic_relations_n{n}.jsonl.gz")
    quadratic_replayed = 0
    for row in quadratic_rows:
        entries = [(int(index), int(coefficient)) for index, coefficient in row["entries"]]
        if not is_zero_combination(
            columns, [(index, flint.fmpq(coefficient)) for index, coefficient in entries], n
        ):
            raise AssertionError("quadratic relation fails brute full-row replay")
        quadratic_replayed += 1
        all_relations.append(entries)
        if row["graph_local_classes"]:
            named_relations.append(entries)
    named_matrix = flint.fmpz_mat(len(columns), len(named_relations))
    for relation_index, relation in enumerate(named_relations):
        for index, coefficient in relation:
            named_matrix[index, relation_index] = coefficient
    named_rank = named_matrix.rank()
    named_counterexample = json.loads(
        (directory / f"named_local_move_counterexample_n{n}.json").read_text()
    )
    named_entries = [
        (int(index), int(coefficient)) for index, coefficient in named_counterexample["entries"]
    ]
    if not is_zero_combination(
        columns, [(index, flint.fmpq(coefficient)) for index, coefficient in named_entries], n
    ):
        raise AssertionError("named-local-span counterexample is not an exact kernel vector")
    named_augmented = flint.fmpz_mat(len(columns), len(named_relations) + 1)
    for row in range(named_matrix.nrows()):
        for column in range(named_matrix.ncols()):
            named_augmented[row, column] = named_matrix[row, column]
    for index, coefficient in named_entries:
        named_augmented[index, len(named_relations)] = coefficient
    named_augmented_rank = named_augmented.rank()
    if named_augmented_rank != named_rank + 1:
        raise AssertionError("named-local-span counterexample does not raise exact span rank")
    all_matrix = flint.fmpz_mat(len(columns), len(all_relations))
    for relation_index, relation in enumerate(all_relations):
        for index, coefficient in relation:
            all_matrix[index, relation_index] = coefficient
    all_rank = all_matrix.rank()
    quadratic_counterexample = json.loads(
        (directory / f"quadratic_generation_counterexample_n{n}.json").read_text()
    )
    quadratic_entries = [
        (int(index), int(coefficient))
        for index, coefficient in quadratic_counterexample["entries"]
    ]
    if not is_zero_combination(
        columns, [(index, flint.fmpq(coefficient)) for index, coefficient in quadratic_entries], n
    ):
        raise AssertionError("all-quadratic-span counterexample is not an exact kernel vector")
    all_augmented = flint.fmpz_mat(len(columns), len(all_relations) + 1)
    for row in range(all_matrix.nrows()):
        for column in range(all_matrix.ncols()):
            all_augmented[row, column] = all_matrix[row, column]
    for index, coefficient in quadratic_entries:
        all_augmented[index, len(all_relations)] = coefficient
    all_augmented_rank = all_augmented.rank()
    if all_augmented_rank != all_rank + 1:
        raise AssertionError("all-quadratic-span counterexample does not raise exact span rank")

    return {
        "n": n,
        "templates_recomputed_by_brute_force": len(templates),
        "templates_denominator": len(templates),
        "permutations_per_template": math.factorial(n),
        "hinge_rows": len(hinge_rows),
        "linear_rows": n,
        "rank_over_Q": rank,
        "kernel_basis_vectors_replayed": len(basis_rows),
        "kernel_basis_denominator": len(basis_rows),
        "kernel_basis_rank_over_Q": basis_rank,
        "kernel_support_median": statistics.median(support_sizes),
        "kernel_plus_one_mutation_rejected": True,
        "max_witness_nonzero_coefficients": len(witness_entries),
        "max_witness_rows_replayed": len(hinge_rows) + n,
        "max_witness_full_row_exact_Q_passed": True,
        "max_witness_plus_one_mutation_rejected": witness_mutation_rejected,
        "outside_local_span_kernel_counterexample_passed": True,
        "quadratic_relations_full_row_replayed": quadratic_replayed,
        "named_graph_local_candidate_span_rank": named_rank,
        "named_local_counterexample_augmented_rank": named_augmented_rank,
        "named_local_counterexample_exact_exclusion_passed": True,
        "all_quadratic_candidate_span_rank": all_rank,
        "all_quadratic_counterexample_augmented_rank": all_augmented_rank,
        "all_quadratic_counterexample_exact_exclusion_passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--directory", type=Path, default=Path(__file__).resolve().parent
    )
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6")
    started = time.time()
    results = [verify_n(args.directory, n, args.workers) for n in (7, 8)]
    output = {
        "schema": "max11-span-structure-independent-replay-v1",
        "method": "all permutations for every saved template; no subset-DP calls",
        "workers": args.workers,
        "results": results,
        "elapsed_seconds": round(time.time() - started, 3),
    }
    path = args.directory / "verification.json"
    path.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(path), "elapsed_seconds": output["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
