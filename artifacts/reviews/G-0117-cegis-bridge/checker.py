#!/usr/bin/env python3
"""Independent exact controls for the G-0113 -> G-0117 CEGIS bridge."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from itertools import permutations, product
import json
import math
import os
from pathlib import Path
from typing import Iterable, Sequence


N = 11
DEGREE = 5
P1 = 1_000_000_007
P2 = 1_000_000_009
EXPECTED_INPUT_SHA256 = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8"
EXPECTED_ROWS_SHA256 = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c"
EXPECTED_5341_PANEL_SHA256 = "2edd9faf75a4960c4c1e03338710c46257fa57469a828aaa4a3831661bedba39"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def i128_digest(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def rank(rows: Sequence[Sequence[int | Fraction]]) -> int:
    matrix = [[Fraction(value) for value in row] for row in rows]
    if not matrix:
        return 0
    row = 0
    columns = len(matrix[0])
    for column in range(columns):
        pivot = next((candidate for candidate in range(row, len(matrix)) if matrix[candidate][column]), None)
        if pivot is None:
            continue
        matrix[row], matrix[pivot] = matrix[pivot], matrix[row]
        scale = matrix[row][column]
        matrix[row] = [value / scale for value in matrix[row]]
        for other in range(len(matrix)):
            if other == row or not matrix[other][column]:
                continue
            scale = matrix[other][column]
            matrix[other] = [
                value - scale * pivot_value
                for value, pivot_value in zip(matrix[other], matrix[row], strict=True)
            ]
        row += 1
        if row == len(matrix):
            break
    return row


def solve_any(rows: Sequence[Sequence[int]], target: Sequence[int]) -> list[Fraction] | None:
    if not rows:
        return [] if not target else None
    variables = len(rows[0])
    augmented = [
        [Fraction(value) for value in row] + [Fraction(rhs)]
        for row, rhs in zip(rows, target, strict=True)
    ]
    pivot_row = 0
    pivots: list[int] = []
    for column in range(variables):
        pivot = next(
            (candidate for candidate in range(pivot_row, len(augmented)) if augmented[candidate][column]),
            None,
        )
        if pivot is None:
            continue
        augmented[pivot_row], augmented[pivot] = augmented[pivot], augmented[pivot_row]
        scale = augmented[pivot_row][column]
        augmented[pivot_row] = [value / scale for value in augmented[pivot_row]]
        for other in range(len(augmented)):
            if other == pivot_row or not augmented[other][column]:
                continue
            scale = augmented[other][column]
            augmented[other] = [
                value - scale * pivot_value
                for value, pivot_value in zip(augmented[other], augmented[pivot_row], strict=True)
            ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(augmented):
            break
    for row in augmented:
        if all(value == 0 for value in row[:variables]) and row[-1] != 0:
            return None
    solution = [Fraction(0) for _ in range(variables)]
    for row_index, column in enumerate(pivots):
        solution[column] = augmented[row_index][-1]
    return solution


def replay(rows: Sequence[Sequence[int]], target: Sequence[int], coefficients: Sequence[Fraction]) -> bool:
    return all(
        sum(Fraction(value) * coefficient for value, coefficient in zip(row, coefficients, strict=True))
        == rhs
        for row, rhs in zip(rows, target, strict=True)
    )


def cegis_algebra_controls() -> dict[str, object]:
    # The first row admits the canonical free-zero seed (1,0).  The hidden row
    # falsifies it, but the complete two-column family has the exact solution
    # (-1,2).  Freezing the original one-column support would falsely fail.
    panel_rows = [[1, 1]]
    panel_target = [1]
    seed = solve_any(panel_rows, panel_target)
    assert seed == [Fraction(1), Fraction(0)]
    hidden_row = [0, 1]
    hidden_target = 2
    hidden_residual = sum(Fraction(value) * coefficient for value, coefficient in zip(hidden_row, seed, strict=True)) - hidden_target
    assert hidden_residual == -2
    complete_rows = panel_rows + [hidden_row]
    complete_target = panel_target + [hidden_target]
    repaired = solve_any(complete_rows, complete_target)
    assert repaired == [Fraction(-1), Fraction(2)]
    assert replay(complete_rows, complete_target, repaired)
    frozen_support_solution = solve_any([[row[0]] for row in complete_rows], complete_target)
    assert frozen_support_solution is None

    # A fresh residual constraint either raises the column-row rank or exposes
    # an inconsistent target pairing in the augmented system.
    before_augmented_rank = rank([panel_rows[0] + [panel_target[0]]])
    after_augmented_rank = rank(
        [panel_rows[0] + [panel_target[0]], hidden_row + [hidden_target]]
    )
    assert (before_augmented_rank, after_augmented_rank) == (1, 2)
    same_candidate_row = [[1, 0], [2, 0]]
    inconsistent_target = [0, 1]
    assert rank(same_candidate_row) == 1
    assert rank([row + [rhs] for row, rhs in zip(same_candidate_row, inconsistent_target, strict=True)]) == 2
    assert solve_any(same_candidate_row, inconsistent_target) is None

    # Exact all-column nonmembership and its primitive left separator.
    nonmember_rows = [[1, 0], [0, 0]]
    nonmember_target = [0, 1]
    separator = [0, 1]
    assert solve_any(nonmember_rows, nonmember_target) is None
    columns = list(zip(*nonmember_rows, strict=True))
    assert all(sum(y * value for y, value in zip(separator, column, strict=True)) == 0 for column in columns)
    assert sum(y * value for y, value in zip(separator, nonmember_target, strict=True)) == 1

    # Clearing denominators is safe for replay, but the next exact solve must
    # return to Q.  Fixing the old integer target scale can exclude a valid
    # rational solution.
    rational_rows = [[1, 0], [0, 2]]
    rational_target = [1, 1]
    rational_solution = solve_any(rational_rows, rational_target)
    assert rational_solution == [Fraction(1), Fraction(1, 2)]
    assert not all(value.denominator == 1 for value in rational_solution)

    return {
        "panel_seed": [str(value) for value in seed],
        "first_hidden_residual": str(hidden_residual),
        "full_family_repaired_solution": [str(value) for value in repaired],
        "frozen_support_would_falsely_fail": frozen_support_solution is None,
        "augmented_rank_progress": [before_augmented_rank, after_augmented_rank],
        "same_candidate_rank_inconsistent_target": True,
        "exact_full_column_separator": separator,
        "fresh_q_solve_needed": [str(value) for value in rational_solution],
    }


def modular_controls() -> dict[str, object]:
    modulus = P1 * P2
    exact_nonzero_but_two_prime_zero = modulus
    assert exact_nonzero_but_two_prime_zero != 0
    assert exact_nonzero_but_two_prime_zero % P1 == 0
    assert exact_nonzero_but_two_prime_zero % P2 == 0
    exact_nonzero_detected = P1
    assert exact_nonzero_detected % P1 == 0 and exact_nonzero_detected % P2 != 0
    # A denominator has no image in a field when divisible by its characteristic.
    denominator_gate = math.gcd(P1, P1) != 1
    assert denominator_gate
    return {
        "primes": [P1, P2],
        "product": modulus,
        "nonzero_integer_in_two_prime_kernel": exact_nonzero_but_two_prime_zero,
        "one_nonzero_residue_suffices_to_refute_exact_zero": exact_nonzero_detected % P2,
        "denominator_equal_to_prime_must_be_refused": denominator_gate,
        "zero_claim_rule": "zero residues require exact replay or a proved cleared-integer bound below the accumulated modulus",
    }


def signed_graph_value(record: dict[str, object], values: Sequence[int]) -> int:
    negative = sum(max(values[u], values[v]) for u, v in record["negative_edges"])
    positive = sum(max(values[u], values[v]) for u, v in record["positive_edges"])
    return DEGREE * max(values[0], values[1]) + max(0, positive - negative)


def formal_assignment_value(record: dict[str, object], row: dict[str, object]) -> int:
    levels = [int(value) for value in row["levels"]]
    profile = [int(value) for value in row["profile"]]
    active = int(record["active_vertices"])
    total = 0
    for colours in product(range(len(levels)), repeat=active):
        used = [0] * len(levels)
        for colour in colours:
            used[colour] += 1
        if any(used[index] > profile[index] for index in range(len(levels))):
            continue
        remaining = [profile[index] - used[index] for index in range(len(levels))]
        multiplicity = math.factorial(N - active)
        for count in remaining:
            multiplicity //= math.factorial(count)
        values = [levels[colour] for colour in colours]
        total += multiplicity * signed_graph_value(record, values)
    return total


def full_orbit_value(record: dict[str, object], row: dict[str, object]) -> int:
    x: list[int] = []
    for level, count in zip(row["levels"], row["profile"], strict=True):
        x.extend([int(level)] * int(count))
    assert len(x) == N and x == sorted(x)
    active = int(record["active_vertices"])
    base = 10 * math.factorial(N - 2) * sum(rank_index * value for rank_index, value in enumerate(x))
    correction = 0
    for ranks in permutations(range(N), active):
        values = [x[index] for index in ranks]
        negative = sum(max(values[u], values[v]) for u, v in record["negative_edges"])
        positive = sum(max(values[u], values[v]) for u, v in record["positive_edges"])
        correction += max(0, positive - negative)
    return base + math.factorial(N - active) * correction


def panel_normalization_controls(input_path: Path, rows_path: Path) -> dict[str, object]:
    assert sha256_path(input_path) == EXPECTED_INPUT_SHA256
    assert sha256_path(rows_path) == EXPECTED_ROWS_SHA256
    source = json.loads(input_path.read_text(encoding="utf-8"))
    rows_document = json.loads(rows_path.read_text(encoding="utf-8"))
    rows = rows_document["rows"]
    checks: dict[str, object] = {}
    for sequence in (5341, 73165):
        record = source["records"][sequence]
        assert int(record["sequence"]) == sequence
        formal_values: list[int] = []
        for row in rows:
            formal = formal_assignment_value(record, row)
            full = full_orbit_value(record, row)
            stabilizer = int(row["formal_stabilizer"])
            assert full % stabilizer == 0
            assert formal == full // stabilizer
            formal_values.append(formal)
        digest = i128_digest(formal_values)
        if sequence == 5341:
            assert digest == EXPECTED_5341_PANEL_SHA256
        checks[str(sequence)] = {
            "active_vertices": int(record["active_vertices"]),
            "signed_mass": int(record["signed_mass"]),
            "all_301_rows_match_full_orbit_divided_by_formal_stabilizer": True,
            "panel_i128_le_sha256": digest,
        }
    return checks


def normal_form_height_bounds() -> dict[str, int | str]:
    factorial_11 = math.factorial(N)
    hinge_per_atom = DEGREE * factorial_11
    base_linear = 10 * (N - 1) * math.factorial(N - 2)
    correction_linear = DEGREE * factorial_11
    linear_per_atom = base_linear + correction_linear
    assert hinge_per_atom == 199_584_000
    assert base_linear == 36_288_000
    assert linear_per_atom == 235_872_000
    return {
        "hinge_abs_per_atom_upper_bound": hinge_per_atom,
        "linear_abs_per_atom_upper_bound": linear_per_atom,
        "target_coefficient": factorial_11,
        "certificate_rule": (
            "For integer term weights a_j and positive target scale L, let S=sum|a_j|. "
            "Every hinge residual has abs <= 199584000*S; every nonfinal linear residual "
            "has abs <= 235872000*S; the final linear residual has abs <= "
            "235872000*S + 39916800*L. A product of checked primes larger than the relevant "
            "bound turns zero residues into exact zero."
        ),
    }


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--rows", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    result = {
        "schema": "max11-g0117-cegis-bridge-independent-controls-v1",
        "bindings": {
            "input": sha256_path(args.input),
            "rows": sha256_path(args.rows),
            "checker": sha256_path(Path(__file__)),
        },
        "cegis_algebra": cegis_algebra_controls(),
        "modular_logic": modular_controls(),
        "panel_global_normalization": panel_normalization_controls(args.input, args.rows),
        "height_bounds": normal_form_height_bounds(),
        "result": "PASS_INDEPENDENT_CONTROLS",
    }
    write_exclusive(args.output, result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
