#!/usr/bin/env python3
"""Exact-Q postprocessing for the frozen G-0113 finite-panel scan."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import resource
import struct
import time
from typing import Iterable, Sequence

from flint import fmpq_mat, fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
INPUT = HERE / "panel_solver_input_v1.json"
ROWS = ROOT / "artifacts/math/G-0111/dual_rows_v1.json"
PREREGISTRATION = HERE / "PANEL_EXACT_POSTPROCESS_PREREGISTRATION.md"
SCANNER_SHA256 = "8be4583119a49d63ef41ab4c86d2f9eb1ee473c99578047c8c62bdcaa01ed47f"
INPUT_SHA256 = "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8"
ROWS_SHA256 = "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c"
TARGET_I64_LE_SHA256 = "19beb89b85e3a95989be9a97d749a48609cb4912897bc20da60bfcd1690bf260"
PRIMES = (2_000_081, 3_000_017)


class ExactError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExactError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_i128(values: Sequence[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_i64(values: Sequence[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<q", int(value)))
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def pivot_columns(reduced: fmpq_mat, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    cursor = 0
    for row in range(rank):
        while cursor < columns and not reduced[row, cursor]:
            cursor += 1
        require(cursor < columns, "RREF pivot extraction failed")
        pivots.append(cursor)
        cursor += 1
    return pivots


def qmatrix(integer_rows: Sequence[Sequence[int]]) -> fmpq_mat:
    return fmpq_mat(fmpz_mat([[int(value) for value in row] for row in integer_rows]))


def matrix_rows(columns: Sequence[dict[str, object]], dimension: int = 301) -> list[list[int]]:
    require(all(len(column["vector"]) == dimension for column in columns), "vector dimension drift")
    return [
        [int(column["vector"][row]) for column in columns]
        for row in range(dimension)
    ]


def primitive_integer(values: Sequence[Fraction]) -> list[int]:
    denominator = 1
    for value in values:
        denominator = math.lcm(denominator, value.denominator)
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    divisor = 0
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    require(divisor > 0, "zero vector cannot be primitive")
    integers = [value // divisor for value in integers]
    first = next(value for value in integers if value)
    if first < 0:
        integers = [-value for value in integers]
    return integers


def first_target_separating_left_null(
    candidate: fmpq_mat,
    integer_rows: Sequence[Sequence[int]],
    target: Sequence[int],
) -> tuple[list[int], int, int]:
    reduced, rank = candidate.transpose().rref()
    rank = int(rank)
    pivots = pivot_columns(reduced, rank, len(target))
    pivot_set = set(pivots)
    for free in range(len(target)):
        if free in pivot_set:
            continue
        rational = [Fraction() for _ in target]
        rational[free] = Fraction(1)
        for row, pivot in enumerate(pivots):
            rational[pivot] = -Fraction(str(reduced[row, free]))
        pairing = sum(value * rhs for value, rhs in zip(rational, target, strict=True))
        if not pairing:
            continue
        integer = primitive_integer(rational)
        for column in range(candidate.ncols()):
            require(
                sum(integer[row] * int(integer_rows[row][column]) for row in range(len(target)))
                == 0,
                "primitive separator failed exact candidate replay",
            )
        integer_pairing = sum(value * rhs for value, rhs in zip(integer, target, strict=True))
        require(integer_pairing != 0, "integer separator lost target pairing")
        return integer, integer_pairing, free
    raise ExactError("augmented-rank witness did not yield a target-separating left null")


def planted_controls() -> dict[str, bool]:
    member_rows = [[1, 0], [0, 1], [1, 1]]
    member_target = [3, 5, 8]
    member = qmatrix(member_rows)
    member_augmented = qmatrix(
        [row + [member_target[index]] for index, row in enumerate(member_rows)]
    )
    member_pass = int(member.rank()) == int(member_augmented.rank())
    member_solution = qmatrix([[1, 0], [0, 1]]).solve(qmatrix([[3], [5]]))
    member_replay = member * member_solution == qmatrix([[3], [5], [8]])
    member_mutant = fmpq_mat(member_solution)
    member_mutant[0, 0] += 1
    coefficient_mutant_rejected = member * member_mutant != qmatrix([[3], [5], [8]])
    nonmember_rows = [[1], [0], [0]]
    nonmember_target = [0, 1, 0]
    nonmember = qmatrix(nonmember_rows)
    separator, pairing, _ = first_target_separating_left_null(
        nonmember, nonmember_rows, nonmember_target
    )
    nonmember_pass = pairing != 0 and sum(separator[row] * nonmember_rows[row][0] for row in range(3)) == 0
    require(
        member_pass and member_replay and coefficient_mutant_rejected and nonmember_pass,
        "planted exact controls failed",
    )
    return {
        "member": member_pass and member_replay,
        "coefficient_plus_one_mutant_rejected": coefficient_mutant_rejected,
        "nonmember_separator": nonmember_pass,
    }


def postprocess(report_path: Path, retained_path: Path, output_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    bindings = {
        "input": sha256_path(INPUT),
        "rows": sha256_path(ROWS),
        "report": sha256_path(report_path),
        "retained": sha256_path(retained_path),
        "producer": sha256_path(SCRIPT),
        "preregistration": sha256_path(PREREGISTRATION),
    }
    require(bindings["input"] == INPUT_SHA256, "input binding drift")
    require(bindings["rows"] == ROWS_SHA256, "row binding drift")
    report = json.loads(report_path.read_text(encoding="utf-8"))
    retained = json.loads(retained_path.read_text(encoding="utf-8"))
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    require(report["schema"] == "max11-g0113-panel-scan-v1", "scan schema drift")
    require(
        retained["schema"] == "max11-g0113-panel-retained-columns-v1",
        "retained schema drift",
    )
    require(report["bindings"]["producer"] == SCANNER_SHA256, "scanner source drift")
    require(report["bindings"]["input"] == INPUT_SHA256, "report input drift")
    require(report["bindings"]["rows"] == ROWS_SHA256, "report row drift")
    require(report["bindings"]["retained"] == bindings["retained"], "retained hash drift")
    require(
        all(
            bool(report[field])
            for field in (
                "disjoint_modular_ranks_agree",
                "disjoint_modular_target_decisions_agree",
                "union_modular_ranks_agree",
                "union_modular_target_decisions_agree",
                "modular_ranks_agree",
                "modular_target_decisions_agree",
            )
        ),
        "modular disagreement forbids exact postprocessing",
    )
    prime_reports = report["primes"]
    require(tuple(int(item["prime"]) for item in prime_reports) == PRIMES, "prime order drift")
    require(
        int(prime_reports[0]["union_rank"]) == int(prime_reports[1]["union_rank"]),
        "union rank disagreement",
    )
    target = [int(value) for value in source["target"]]
    require(len(target) == 301, "target dimension drift")
    require(digest_i64(target) == TARGET_I64_LE_SHA256, "target hash drift")

    columns = retained["columns"]
    sequences = [int(column["sequence"]) for column in columns]
    require(sequences == sorted(set(sequences)), "retained sequence order/uniqueness drift")
    for column in columns:
        vector = [int(value) for value in column["vector"]]
        require(digest_i128(vector) == column["panel_vector_sha256"], "retained vector hash drift")
    p1_sequences = [int(value) for value in prime_reports[0]["selected_sequences"]]
    p2_sequences = [int(value) for value in prime_reports[1]["selected_sequences"]]
    require(
        p1_sequences == [int(column["sequence"]) for column in columns if column["selected_p1"]],
        "p1 support drift",
    )
    require(
        p2_sequences == [int(column["sequence"]) for column in columns if column["selected_p2"]],
        "p2 support drift",
    )
    union_columns = [
        column for column in columns if bool(column["selected_p1"]) or bool(column["selected_p2"])
    ]
    union_rows = matrix_rows(union_columns)
    candidate = qmatrix(union_rows)
    rhs = qmatrix([[value] for value in target])
    augmented = qmatrix([row + [target[index]] for index, row in enumerate(union_rows)])
    exact_rank = int(candidate.rank())
    augmented_rank = int(augmented.rank())
    exact_member = exact_rank == augmented_rank
    modular_rank = int(prime_reports[0]["union_rank"])
    require(exact_rank >= modular_rank, "exact rank fell below modular lower bound")
    controls = planted_controls()

    payload: dict[str, object]
    if exact_member:
        if modular_rank == 301:
            support = [column for column in columns if bool(column["selected_p1"])]
            require(len(support) == 301, "full-rank p1 support census drift")
            basis_rows = matrix_rows(support)
            basis = qmatrix(basis_rows)
            require(int(basis.rank()) == 301, "p1 exact support lost rank")
            coordinate_rows = list(range(301))
        else:
            reduced, reduced_rank = candidate.rref()
            require(int(reduced_rank) == exact_rank, "exact RREF rank drift")
            pivot_indices = pivot_columns(reduced, exact_rank, len(union_columns))
            support = [union_columns[index] for index in pivot_indices]
            basis_rows = matrix_rows(support)
            basis = qmatrix(basis_rows)
            transposed_reduced, transposed_rank = basis.transpose().rref()
            require(int(transposed_rank) == exact_rank, "coordinate RREF rank drift")
            coordinate_rows = pivot_columns(transposed_reduced, exact_rank, 301)
        square = qmatrix(
            [[basis_rows[row][column] for column in range(exact_rank)] for row in coordinate_rows]
        )
        square_rhs = qmatrix([[target[row]] for row in coordinate_rows])
        coefficients = square.solve(square_rhs)
        require(basis * coefficients == rhs, "exact rational all-row replay failed")
        coefficient_fractions = [Fraction(str(coefficients[index, 0])) for index in range(exact_rank)]
        first_nonzero = next(
            (index for index, value in enumerate(coefficient_fractions) if value),
            None,
        )
        require(first_nonzero is not None, "member solve unexpectedly has only zero coefficients")
        mutant_coefficients = fmpq_mat(coefficients)
        mutant_coefficients[first_nonzero, 0] += 1
        coefficient_mutant_rejected = basis * mutant_coefficients != rhs
        require(coefficient_mutant_rejected, "coefficient +1 mutant escaped all-row replay")
        denominator_lcm = 1
        for coefficient in coefficient_fractions:
            denominator_lcm = math.lcm(denominator_lcm, coefficient.denominator)
        payload = {
            "result": "EXACT_Q_MEMBER_FINITE_PANEL",
            "support_sequences": [int(column["sequence"]) for column in support],
            "coordinate_rows": coordinate_rows,
            "coefficients": [str(value) for value in coefficient_fractions],
            "coefficient_denominator_lcm": denominator_lcm,
            "all_301_rows_replayed": True,
            "coefficient_mutant_index": first_nonzero,
            "coefficient_plus_one_mutant_rejected": coefficient_mutant_rejected,
        }
    else:
        separator, pairing, free_coordinate = first_target_separating_left_null(
            candidate, union_rows, target
        )
        payload = {
            "result": "EXACT_Q_NONMEMBER_RETAINED_SPAN_PENDING_ALL_COLUMN_REPLAY",
            "primitive_integer_separator": [str(value) for value in separator],
            "target_pairing": str(pairing),
            "selected_free_coordinate": free_coordinate,
            "retained_union_annihilated": True,
            "all_163740_columns_replayed": False,
        }

    output = {
        "schema": "max11-g0113-panel-exact-postprocess-v1",
        "claim_boundary": (
            "Exact arithmetic on the retained finite-panel span only. A member is a CEGIS seed, "
            "not a global identity; a nonmember separator requires a fresh all-column exact replay."
        ),
        "bindings": bindings,
        "records": int(report["records"]),
        "retained_columns": len(columns),
        "retained_union_columns": len(union_columns),
        "agreed_modular_rank": modular_rank,
        "exact_union_rank": exact_rank,
        "exact_augmented_rank": augmented_rank,
        "exact_target_member": exact_member,
        "exact_rank_exceeds_modular_rank": exact_rank > modular_rank,
        "planted_controls": controls,
        "payload": payload,
        "wall_seconds": time.perf_counter() - started,
        "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    write_exclusive(output_path, output)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("report", type=Path)
    parser.add_argument("retained", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(postprocess(args.report, args.retained, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
