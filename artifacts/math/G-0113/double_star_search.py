#!/usr/bin/env python3
"""Exact incidence-slot double-star search for G-0113.

The lower-arity stage is a complete ordered-cone calculation.  The MAX11
stage uses only the frozen 66 profile rows unless a canonical finite-row
candidate is produced; only that candidate is then expanded into a complete
ordered-cone normal form.  See PREREGISTRATION.md for the claim boundaries.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence

from flint import fmpz_mat, fmpq_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREREGISTRATION.md"
CERTIFICATES = ROOT / "subjects/max-relu-known/certificates"

CERTIFICATE_PINS = {
    6: (CERTIFICATES / "certificate_6_2.json", "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83", 2, 4),
    7: (CERTIFICATES / "certificate_7_3.json", "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be", 3, 57),
    10: (CERTIFICATES / "certificate_10_4.json", "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4", 4, 402),
}

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Semantic = tuple[tuple[int, ...], dict[tuple[int, ...], int]]


class SearchError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SearchError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_pair(raw: object, n: int, degree: int) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[Side] = []
    for side_index, raw_side in enumerate(raw):
        require(isinstance(raw_side, list) and len(raw_side) == degree, f"bad side {side_index}")
        edges: list[Edge] = []
        for raw_edge in raw_side:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            u, v = map(int, raw_edge)
            require(1 <= u <= v <= n, f"edge outside 1..{n}")
            edges.append((u - 1, v - 1))
        sides.append(tuple(edges))
    return sides[0], sides[1]


def load_certificate(n: int) -> dict[str, object]:
    path, expected_hash, degree, expected_terms = CERTIFICATE_PINS[n]
    require(sha256(path) == expected_hash, f"MAX{n} certificate hash drift")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n, f"MAX{n} dimension drift")
    terms = document.get("terms")
    require(isinstance(terms, list) and len(terms) == expected_terms, f"MAX{n} term census drift")
    parsed = []
    for index, term in enumerate(terms):
        require(isinstance(term, dict), f"MAX{n} term {index} malformed")
        coefficient = Fraction(str(term.get("coefficient")))
        require(coefficient != 0, "zero source coefficient")
        parsed.append({"coefficient": coefficient, "pair": parse_pair(term.get("pair"), n, degree)})
    return {"n": n, "degree": degree, "terms": parsed, "sha256": expected_hash, "path": str(path.relative_to(ROOT))}


def signed_weights(pair: Pair, n: int) -> list[list[int]]:
    weights = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for u, v in side:
            weights[u][v] += sign
            if u != v:
                weights[v][u] += sign
    return weights


def coefficient_word_histogram(pair: Pair, n: int) -> dict[tuple[int, ...], int]:
    """Histogram of right-minus-left coefficient words over all label orders."""

    weights = signed_weights(pair, n)
    by_size: list[list[int]] = [[] for _ in range(n + 1)]
    by_size[0].append(0)
    for mask in range(1, 1 << n):
        by_size[mask.bit_count()].append(mask)
    cache: dict[int, dict[tuple[int, ...], int]] = {0: {(): 1}}
    for size in range(1, n + 1):
        for mask in by_size[size]:
            output: dict[tuple[int, ...], int] = defaultdict(int)
            bits = mask
            while bits:
                bit = bits & -bits
                bits ^= bit
                vertex = bit.bit_length() - 1
                lower = mask ^ bit
                increment = weights[vertex][vertex]
                lower_bits = lower
                while lower_bits:
                    lower_bit = lower_bits & -lower_bits
                    lower_bits ^= lower_bit
                    increment += weights[vertex][lower_bit.bit_length() - 1]
                for prefix, multiplicity in cache[lower].items():
                    output[prefix + (increment,)] += multiplicity
            cache[mask] = dict(output)
        if size >= 2:
            for stale in by_size[size - 2]:
                cache.pop(stale, None)
    result = cache[(1 << n) - 1]
    require(sum(result.values()) == math.factorial(n), "permutation histogram census drift")
    return result


def vanishes_on_ordered_cone(direction: Sequence[int]) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


_SEMANTIC_CACHE: dict[tuple[int, Pair], Semantic] = {}


def canonical_pair(pair: Pair) -> Pair:
    left = tuple(sorted(pair[0]))
    right = tuple(sorted(pair[1]))
    return (left, right) if left <= right else (right, left)


def ordered_normal_form(pair: Pair, n: int) -> Semantic:
    pair = canonical_pair(pair)
    key = (n, pair)
    cached = _SEMANTIC_CACHE.get(key)
    if cached is not None:
        return cached

    histogram = coefficient_word_histogram(pair, n)
    left_loops = sum(u == v for u, v in pair[0])
    left_nonloops = len(pair[0]) - left_loops
    loop_factor = math.factorial(n - 1)
    edge_factor = math.factorial(n - 2)
    linear = [
        left_loops * loop_factor + left_nonloops * 2 * rank * edge_factor
        for rank in range(n)
    ]
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    for raw, multiplicity in histogram.items():
        if not any(raw):
            continue
        divisor = math.gcd(*(abs(value) for value in raw))
        first = next(value for value in raw if value)
        if first < 0:
            for rank, value in enumerate(raw):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // divisor for value in raw)
        else:
            primitive = tuple(value // divisor for value in raw)
        if not vanishes_on_ordered_cone(primitive):
            hinges[primitive] += multiplicity * divisor
    result = (tuple(linear), {direction: value for direction, value in hinges.items() if value})
    _SEMANTIC_CACHE[key] = result
    return result


def evaluate_normal_form(semantic: Semantic, x_sorted: Sequence[int]) -> int:
    linear, hinges = semantic
    value = sum(a * b for a, b in zip(linear, x_sorted, strict=True))
    for direction, coefficient in hinges.items():
        argument = sum(a * b for a, b in zip(direction, x_sorted, strict=True))
        if argument > 0:
            value += coefficient * argument
    return value


def pair_value(pair: Pair, x: Sequence[int]) -> int:
    def side_value(side: Side) -> int:
        return sum(max(x[u], x[v]) for u, v in side)

    return max(side_value(pair[0]), side_value(pair[1]))


def literal_orbit_value(pair: Pair, x_sorted: Sequence[int]) -> int:
    return sum(pair_value(pair, assignment) for assignment in itertools.permutations(x_sorted))


def attachment_choices(side: Side, new_vertex: int) -> tuple[tuple[Edge, Edge], ...]:
    choices: list[tuple[Edge, Edge]] = []
    for u, v in side:
        choices.append(((u, new_vertex), (u, new_vertex)))
        choices.append(((v, new_vertex), (v, new_vertex)))
        choices.append(((u, new_vertex), (v, new_vertex)))
    choices.append(((new_vertex, new_vertex), (new_vertex, new_vertex)))
    return tuple(choices)


def lifted_pair(pair: Pair, left_choice: int, right_choice: int, new_vertex: int) -> Pair:
    left_attachments = attachment_choices(pair[0], new_vertex)
    right_attachments = attachment_choices(pair[1], new_vertex)
    return pair[0] + left_attachments[left_choice], pair[1] + right_attachments[right_choice]


def add_semantic(accumulator: tuple[list[int], dict[tuple[int, ...], int]], semantic: Semantic, weight: int) -> None:
    linear, hinges = semantic
    target_linear, target_hinges = accumulator
    for index, value in enumerate(linear):
        target_linear[index] += weight * value
    for direction, value in hinges.items():
        updated = target_hinges.get(direction, 0) + weight * value
        if updated:
            target_hinges[direction] = updated
        else:
            target_hinges.pop(direction, None)


def certificate_control(certificate: dict[str, object]) -> dict[str, object]:
    n = int(certificate["n"])
    denominator = math.lcm(*(term["coefficient"].denominator for term in certificate["terms"]))
    total: tuple[list[int], dict[tuple[int, ...], int]] = ([0] * n, {})
    first_semantic: Semantic | None = None
    for term in certificate["terms"]:
        coefficient: Fraction = term["coefficient"]
        weight = coefficient.numerator * (denominator // coefficient.denominator)
        semantic = ordered_normal_form(term["pair"], n)
        first_semantic = semantic if first_semantic is None else first_semantic
        add_semantic(total, semantic, weight)
    expected = [0] * (n - 1) + [denominator]
    require(total[0] == expected and not total[1], f"MAX{n} certificate replay failed")
    require(first_semantic is not None, "empty certificate")
    mutation_residual = (list(first_semantic[0]), dict(first_semantic[1]))
    require(mutation_residual[0] != [0] * (n - 1) + [1] or mutation_residual[1], "coefficient mutation escaped")
    return {
        "n": n,
        "terms": len(certificate["terms"]),
        "degree": certificate["degree"],
        "coefficient_lcm": denominator,
        "identity_replayed": True,
        "one_unit_first_coefficient_mutation_rejected": True,
        "certificate_sha256": certificate["sha256"],
    }


def columns_to_rows(columns: Sequence[Semantic], n: int) -> tuple[list[list[int]], list[object]]:
    directions = sorted({direction for _linear, hinges in columns for direction in hinges})
    labels: list[object] = [("linear", index) for index in range(n)] + [("hinge", list(direction)) for direction in directions]
    rows = [[linear[index] for linear, _hinges in columns] for index in range(n)]
    rows.extend([[hinges.get(direction, 0) for _linear, hinges in columns] for direction in directions])
    return rows, labels


def pivot_columns_from_rref(matrix: fmpz_mat, rank: int) -> list[int]:
    reduced, _denominator, observed_rank = matrix.rref()
    require(observed_rank == rank, "RREF rank drift")
    pivots: list[int] = []
    for row in range(rank):
        pivot = next((column for column in range(matrix.ncols()) if reduced[row, column] != 0), None)
        require(pivot is not None, "RREF row lacks pivot")
        pivots.append(int(pivot))
    require(pivots == sorted(set(pivots)), "pivot columns malformed")
    return pivots


def fraction_from_flint(value: object) -> Fraction:
    return Fraction(str(value))


def primitive(values: Sequence[int]) -> list[int]:
    divisor = math.gcd(*(abs(value) for value in values))
    require(divisor > 0, "zero vector cannot be primitive")
    result = [value // divisor for value in values]
    if next(value for value in result if value) < 0:
        result = [-value for value in result]
    return result


def exact_rank_decision(rows: list[list[int]], target: list[int], labels: Sequence[object]) -> dict[str, object]:
    require(len(rows) == len(target) == len(labels), "rank subject row mismatch")
    require(rows and rows[0], "empty rank subject")
    matrix = fmpz_mat(rows)
    augmented = fmpz_mat([row + [target[index]] for index, row in enumerate(rows)])
    rank = int(matrix.rank())
    augmented_rank = int(augmented.rank())
    require(augmented_rank in (rank, rank + 1), "target changed rank by more than one")
    pivots = pivot_columns_from_rref(matrix, rank)
    report: dict[str, object] = {
        "rows": len(rows),
        "columns": len(rows[0]),
        "rank_Q": rank,
        "augmented_rank_Q": augmented_rank,
        "target_in_span": rank == augmented_rank,
        "pivot_columns": pivots,
    }

    if rank == augmented_rank:
        transposed_basis = fmpz_mat([[rows[row][column] for row in range(len(rows))] for column in pivots])
        _row_reduced, _den, row_rank = transposed_basis.rref()
        require(row_rank == rank, "basis transpose rank drift")
        row_pivots = pivot_columns_from_rref(transposed_basis, rank)
        square = fmpq_mat([[rows[row][column] for column in pivots] for row in row_pivots])
        rhs = fmpq_mat([[target[row]] for row in row_pivots])
        solution = square.solve(rhs)
        coefficients = [fraction_from_flint(solution[index, 0]) for index in range(rank)]
        for row_index, row in enumerate(rows):
            observed = sum(coefficients[index] * row[column] for index, column in enumerate(pivots))
            require(observed == target[row_index], f"basic solution failed row {row_index}")
        report["basic_solution"] = [
            {"column": column, "coefficient": str(coefficient)}
            for column, coefficient in zip(pivots, coefficients, strict=True)
            if coefficient
        ]
        report["solution_support"] = sum(bool(value) for value in coefficients)
    else:
        basis_transpose = fmpz_mat([[rows[row][column] for row in range(len(rows))] for column in pivots])
        nullspace, nullity = basis_transpose.nullspace()
        require(nullity == len(rows) - rank and nullity > 0, "left-nullity drift")
        selected: list[int] | None = None
        for basis_column in range(nullity):
            candidate = [int(nullspace[row, basis_column]) for row in range(len(rows))]
            if sum(candidate[row] * target[row] for row in range(len(rows))) != 0:
                selected = primitive(candidate)
                break
        require(selected is not None, "no target-separating null vector found")
        annihilations = [sum(selected[row] * rows[row][column] for row in range(len(rows))) for column in range(len(rows[0]))]
        pairing = sum(selected[row] * target[row] for row in range(len(rows)))
        require(not any(annihilations) and pairing != 0, "dual replay failed")
        support = [
            {"row": row, "label": labels[row], "weight": selected[row]}
            for row in range(len(rows)) if selected[row]
        ]
        report["separator"] = {
            "primitive_integer_support": support,
            "support_size": len(support),
            "target_pairing": str(pairing),
            "all_columns_annihilated": True,
        }

    first_separating_prefix = None
    for stop in range(1, len(rows) + 1):
        prefix_rank = int(fmpz_mat(rows[:stop]).rank())
        prefix_augmented = int(fmpz_mat([row + [target[index]] for index, row in enumerate(rows[:stop])]).rank())
        if prefix_augmented > prefix_rank:
            first_separating_prefix = {
                "rows": stop,
                "last_row": labels[stop - 1],
                "rank_Q": prefix_rank,
                "augmented_rank_Q": prefix_augmented,
            }
            break
    report["first_separating_prefix"] = first_separating_prefix
    return report


def lower_families(source: dict[str, object]) -> tuple[list[Semantic], list[Semantic], list[dict[str, int]]]:
    n = int(source["n"])
    degree = int(source["degree"])
    choices = 3 * degree + 1
    denominator = math.lcm(*(term["coefficient"].denominator for term in source["terms"]))
    raw: list[Semantic] = []
    descriptors: list[dict[str, int]] = []
    tied_accumulators: list[tuple[list[int], dict[tuple[int, ...], int]]] = [([0] * (n + 1), {}) for _ in range(choices * choices)]
    for term_index, term in enumerate(source["terms"]):
        coefficient: Fraction = term["coefficient"]
        weight = coefficient.numerator * (denominator // coefficient.denominator)
        pair: Pair = term["pair"]
        for left_choice in range(choices):
            for right_choice in range(choices):
                lifted = lifted_pair(pair, left_choice, right_choice, n)
                semantic = ordered_normal_form(lifted, n + 1)
                raw.append(semantic)
                descriptors.append({"term": term_index, "left_choice": left_choice, "right_choice": right_choice})
                add_semantic(tied_accumulators[left_choice * choices + right_choice], semantic, weight)
    tied = [(tuple(linear), dict(hinges)) for linear, hinges in tied_accumulators]
    require(len(raw) == len(source["terms"]) * choices * choices, "lower RAW census drift")
    require(len(tied) == choices * choices, "lower TIED census drift")
    return raw, tied, descriptors


def star_control(source: dict[str, object]) -> dict[str, object]:
    require(source["n"] == 6 and source["degree"] == 2, "star control source drift")
    columns: list[Semantic] = []
    for term in source["terms"]:
        pair: Pair = term["pair"]
        for left_endpoint in range(7):
            for right_endpoint in range(7):
                lifted = pair[0] + ((left_endpoint, 6),), pair[1] + ((right_endpoint, 6),)
                columns.append(ordered_normal_form(lifted, 7))
    rows, labels = columns_to_rows(columns, 7)
    target = [0] * len(rows)
    target[6] = 1
    decision = exact_rank_decision(rows, target, labels)
    require(decision["rank_Q"] == 64 and decision["augmented_rank_Q"] == 65, "known one-edge null did not reproduce")
    return {
        "raw_columns": len(columns),
        "rank_Q": 64,
        "augmented_rank_Q": 65,
        "known_failure_reproduced": True,
    }


def run_lower(output: Path) -> None:
    begun = time.perf_counter()
    script_hash_start = sha256(SCRIPT)
    prereg_hash_start = sha256(PREREGISTRATION)
    cert6 = load_certificate(6)
    cert7 = load_certificate(7)
    cert10 = load_certificate(10)
    controls_started = time.perf_counter()
    controls = {
        "MAX6": certificate_control(cert6),
        "MAX7": certificate_control(cert7),
        "MAX10": certificate_control(cert10),
        "branch_swap": None,
        "one_edge_MAX6_to_MAX7": None,
    }
    control_pair = cert6["terms"][1]["pair"]
    control_semantic = ordered_normal_form(control_pair, 6)
    swapped_semantic = ordered_normal_form((control_pair[1], control_pair[0]), 6)
    require(control_semantic == swapped_semantic, "branch-swap invariant failed")
    controls["branch_swap"] = "PASS"
    controls["one_edge_MAX6_to_MAX7"] = star_control(cert6)
    controls_seconds = time.perf_counter() - controls_started

    family_started = time.perf_counter()
    raw, tied, descriptors = lower_families(cert6)
    raw_rows, raw_labels = columns_to_rows(raw, 7)
    tied_rows, tied_labels = columns_to_rows(tied, 7)
    raw_target = [0] * len(raw_rows)
    raw_target[6] = 1
    tied_target = [0] * len(tied_rows)
    tied_target[6] = 1
    raw_decision = exact_rank_decision(raw_rows, raw_target, raw_labels)
    tied_decision = exact_rank_decision(tied_rows, tied_target, tied_labels)
    family_seconds = time.perf_counter() - family_started

    # A second literal orbit path on predeclared small examples.
    literal_controls = []
    for raw_index, point in ((0, (0, 0, 0, 1, 2, 3, 5)), (len(raw) - 1, (0, 0, 1, 1, 2, 3, 4))):
        descriptor = descriptors[raw_index]
        term = cert6["terms"][descriptor["term"]]
        pair = lifted_pair(term["pair"], descriptor["left_choice"], descriptor["right_choice"], 6)
        direct = literal_orbit_value(pair, point)
        normal = evaluate_normal_form(raw[raw_index], point)
        require(direct == normal, f"literal control mismatch at raw {raw_index}")
        literal_controls.append({"raw_column": raw_index, "point": list(point), "value": direct, "match": True})

    potency = bool(raw_decision["target_in_span"])
    result = {
        "schema": "max11-g0113-incidence-slot-double-star-lower-v1",
        "result": "LOWER_RAW_POTENCY_PASS" if potency else "LOWER_RAW_POTENCY_FAIL_STOP",
        "bindings": {
            "script_sha256_start": script_hash_start,
            "preregistration_sha256_start": prereg_hash_start,
            "certificates": {str(n): CERTIFICATE_PINS[n][1] for n in (6, 7, 10)},
        },
        "family": {
            "definition": "incidence-slot parallel/edge-supported double-star",
            "source": "MAX6 degree-2",
            "attachment_choices_per_branch": 7,
            "RAW_columns": len(raw),
            "TIED_columns": len(tied),
            "raw_descriptor_sha256": object_sha256(descriptors),
            "raw_complete_row_matrix_sha256": object_sha256(raw_rows),
            "tied_complete_row_matrix_sha256": object_sha256(tied_rows),
        },
        "controls": {**controls, "literal_orbit_replays": literal_controls},
        "RAW": raw_decision,
        "TIED": tied_decision,
        "timing": {
            "controls_seconds": controls_seconds,
            "family_seconds": family_seconds,
            "wall_seconds": time.perf_counter() - begun,
        },
        "claim_boundary": (
            "Complete exact characteristic-zero decision for the displayed MAX6-to-MAX7 "
            "196-column RAW and 49-column TIED incidence-slot double-star families only. "
            "A miss is not a MAX11 or unrestricted-network result; a pass is a potency "
            "control and not transport evidence."
        ),
    }
    require(sha256(SCRIPT) == script_hash_start, "script changed during execution")
    require(sha256(PREREGISTRATION) == prereg_hash_start, "preregistration changed during execution")
    descriptor = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as target_file:
        target_file.write(canonical_bytes(result))
        target_file.flush()
        os.fsync(target_file.fileno())
    print(json.dumps({"output": str(output), "result": result["result"], "wall_seconds": result["timing"]["wall_seconds"]}, sort_keys=True))


def self_test() -> dict[str, object]:
    pair: Pair = (((0, 1), (0, 2)), ((1, 2), (2, 3)))
    semantic = ordered_normal_form(pair, 4)
    point = (0, 1, 2, 4)
    direct = literal_orbit_value(pair, point)
    normal = evaluate_normal_form(semantic, point)
    require(direct == normal, "small literal/normal-form control failed")
    swapped = ordered_normal_form((pair[1], pair[0]), 4)
    require(swapped == semantic, "small branch swap failed")
    choices = attachment_choices(pair[0], 4)
    require(len(choices) == 7, "attachment census control failed")
    matrix = [[1, 0], [0, 1], [1, 1]]
    target = [1, 1, 3]
    decision = exact_rank_decision(matrix, target, [("r", i) for i in range(3)])
    require(not decision["target_in_span"], "rank negative control failed")
    return {
        "literal_equals_normal": True,
        "branch_swap": True,
        "attachment_census": True,
        "rank_negative_control": True,
        "value": direct,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--lower", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.output is None, "self-test refuses output")
        print(json.dumps(self_test(), sort_keys=True))
        return
    require(args.output is not None and not args.output.exists(), "unused output path required")
    run_lower(args.output)


if __name__ == "__main__":
    main()
