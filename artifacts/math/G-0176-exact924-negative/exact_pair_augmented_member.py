#!/usr/bin/env python3
"""Provisional exact member after the dependency-rich 64-pair batch."""

from __future__ import annotations

from fractions import Fraction
import hashlib
import importlib.util
import json
import math
import mmap
from pathlib import Path
import sys

from flint import fmpq_mat, fmpz_mat
import numpy as np

ROOT = Path("/data/projects/relu-depth-frontier-research")
PRIOR = Path("/tmp/g0168-explore.kEmA87")
NEXT = Path("/tmp/g0168-next.yerj9c")
HERE = Path(__file__).parent
sys.path.insert(0, str(PRIOR))
from quotient_rank import inverse_mod, row_rank_and_pivot_columns  # noqa: E402

RECORDS = 163_740
BASE_ROWS = 540
PRIOR_ROWS = 128
NEXT_ROWS = 128
CURRENT_ROWS = 796
PAIR_ROWS = 128
CURRENT_RANK = 595
PRIME = 1_000_003
MATRIX_BYTES = RECORDS * PAIR_ROWS * 8
PRIOR_MEMBER_SHA256 = "bd7ee2a8a92c490805f4a13d451f340d0f53cd6e4698062e422d444a84e609c6"
PRIOR_MATRIX_SHA256 = "9de042920c07b811efa25df550cd8860bc6715f24893ec316360b0ff28d0570c"
NEXT_MATRIX_SHA256 = "7fdf3ccf7f764ba1637b6de29f1f4c90ba6ef0a60f4868dad2922711998f6cb4"


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_direction_digest(selection: dict[str, object]) -> str:
    items = selection["selected_residual_items"]
    assert isinstance(items, list) and len(items) == PAIR_ROWS
    digest = hashlib.sha256()
    for item in items:
        assert isinstance(item, dict)
        direction = item["direction"]
        assert isinstance(direction, list) and len(direction) == 11
        assert all(isinstance(value, int) and -128 <= value <= 127 for value in direction)
        digest.update(bytes(value & 0xFF for value in direction))
    return digest.hexdigest()


def normalize(values: list[Fraction]) -> tuple[list[int], int]:
    scale = math.lcm(*(value.denominator for value in values))
    integers = [value.numerator * (scale // value.denominator) for value in values]
    divisor = scale
    for value in integers:
        divisor = math.gcd(divisor, abs(value))
    return [value // divisor for value in integers], scale // divisor


def decimal_digest(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(str(value).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def main() -> None:
    if sys.flags.optimize != 0:
        raise RuntimeError("optimized Python prohibited")
    quotient_path = Path(sys.argv[1])
    pair_matrix_path = Path(sys.argv[2])
    output_path = Path(sys.argv[3])
    assert not output_path.exists()
    receipt_path = HERE / "duplicate_pairs128_full_price_receipt.json"
    selection_path = HERE / "selected_duplicate_pairs_128.json"
    current_path = NEXT / "exact_796_member.json"
    prior_member_path = PRIOR / "exact_augmented_member.json"
    quotient_opening_sha256 = file_sha256(quotient_path)
    receipt_opening_sha256 = file_sha256(receipt_path)
    selection_opening_sha256 = file_sha256(selection_path)
    current_opening_sha256 = file_sha256(current_path)
    prior_member_opening_sha256 = file_sha256(prior_member_path)
    with quotient_path.open() as source:
        quotient = json.load(source)
    with receipt_path.open() as source:
        receipt = json.load(source)
    with selection_path.open() as source:
        selection = json.load(source)
    with current_path.open() as source:
        current = json.load(source)
    with prior_member_path.open() as source:
        prior_member = json.load(source)
    assert quotient["prime"] == PRIME
    assert quotient["records_scanned"] == RECORDS
    assert quotient["current_selected_minor_rank"] == CURRENT_RANK
    assert quotient["directions"] == PAIR_ROWS
    assert quotient["residual_compatible_mod_prime"] is True
    assert quotient["matrix_sha256"] == receipt["matrix_sha256"]
    assert quotient["selection_sha256"] == selection_opening_sha256
    assert quotient["receipt_sha256"] == receipt_opening_sha256
    assert receipt["schema"] == "g0168.duplicate_pairs128_provisional_full_family_coordinates.v1"
    assert receipt["records"] == RECORDS
    assert receipt["directions"] == PAIR_ROWS
    assert receipt["global_direct_exact_dot_bridge"] is True
    assert receipt["matrix_path"] == str(pair_matrix_path)
    assert receipt["matrix_bytes"] == MATRIX_BYTES
    assert pair_matrix_path.stat().st_size == receipt["matrix_bytes"]
    assert file_sha256(pair_matrix_path) == receipt["matrix_sha256"]
    assert selection_opening_sha256 == receipt["inputs"]["selection_sha256"]
    assert current_opening_sha256 == receipt["inputs"]["member_sha256"]
    assert prior_member_opening_sha256 == PRIOR_MEMBER_SHA256
    assert selection["schema"] == "g0168.provisional_duplicate_pair_batch128.v1"
    assert selection["directions"] == PAIR_ROWS
    assert selection["predicted_pair_relations"] == PAIR_ROWS // 2
    assert selection["exact_residual_equality_within_every_pair"] is True
    assert selection["fingerprint_equality_under_both_primes"] is True
    directions_sha256 = selected_direction_digest(selection)
    assert directions_sha256 == selection["selected_directions_i8_sha256"]
    assert directions_sha256 == receipt["directions_i8_sha256"]
    assert quotient["selected_directions_i8_sha256"] == directions_sha256
    quotient_rank = int(quotient["quotient_rank_relative_to_selected_595_coordinates"])
    witness_sequences = [int(value) for value in quotient["pivot_sequences"]]
    assert quotient_rank == len(witness_sequences) > 0

    prior_matrix_path = PRIOR / "fresh128.record-major.i64le"
    next_matrix_path = NEXT / "next128.record-major.i64le"
    assert prior_matrix_path.stat().st_size == next_matrix_path.stat().st_size == MATRIX_BYTES
    assert file_sha256(prior_matrix_path) == PRIOR_MATRIX_SHA256
    assert file_sha256(next_matrix_path) == NEXT_MATRIX_SHA256
    prior_matrix = np.memmap(
        prior_matrix_path,
        dtype="<i8",
        mode="r",
        shape=(RECORDS, PRIOR_ROWS),
    )
    next_matrix = np.memmap(
        next_matrix_path,
        dtype="<i8",
        mode="r",
        shape=(RECORDS, NEXT_ROWS),
    )
    pair_matrix = np.memmap(
        pair_matrix_path,
        dtype="<i8",
        mode="r",
        shape=(RECORDS, PAIR_ROWS),
    )
    current_basis = [int(value) for value in current["basis_sequences"]]
    current_coordinate_rows = [int(value) for value in current["coordinate_rows"]]
    assert len(current_basis) == len(current_coordinate_rows) == CURRENT_RANK
    prior_indices = [int(value) for value in prior_member["fresh_coordinate_direction_indices"]]
    next_indices = [int(value) for value in current["next_coordinate_direction_indices"]]
    assert len(prior_indices) == 119 and len(next_indices) == 127
    assert prior_member["result"] == "EXACT_668_ROW_FRESH128_MEMBER_PROVISIONAL"
    assert prior_member["rows"] == 668
    assert len(prior_member["basis_sequences"]) == len(prior_member["coordinate_rows"]) == 468
    assert current["result"] == "EXACT_796_ROW_SECOND_FRESH128_MEMBER_PROVISIONAL"
    assert current["rows"] == CURRENT_ROWS
    assert current_basis[:468] == prior_member["basis_sequences"]
    selected_sequences = current_basis + witness_sequences
    assert len(set(selected_sequences)) == CURRENT_RANK + quotient_rank

    solver_path = ROOT / "artifacts/math/G-0164/all128_direct_basis_master_v1.py"
    spec = importlib.util.spec_from_file_location("g0168_exact_pair_g0164", solver_path)
    assert spec is not None and spec.loader is not None
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)
    state = solver.validate_sealed_inputs()
    old_coordinate_rows = state["coordinate_rows"]
    assert len(old_coordinate_rows) == 349
    assert prior_member["coordinate_rows"] == old_coordinate_rows + [BASE_ROWS + index for index in prior_indices]
    assert current_coordinate_rows == (
        old_coordinate_rows
        + [BASE_ROWS + index for index in prior_indices]
        + [BASE_ROWS + PRIOR_ROWS + index for index in next_indices]
    )
    prepared = state["g0135_prepared"]
    producer = state["g0135_producer"]
    ancestor = prepared["ancestor"]
    old_columns: list[list[int]] = []
    with (
        ancestor.AUDITED.CACHE_PATH.open("rb") as cache_file,
        mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ) as cache,
    ):
        warm_receipt, inherited_loader = producer.validate_warm_start(prepared, cache)
        assert warm_receipt == state["warm_receipt"]
        for sequence in selected_sequences:
            column = [int(value) for value in inherited_loader(sequence)]
            column.extend(int(row[sequence]) for row in state["all_pool_rows"])
            assert len(column) == BASE_ROWS
            old_columns.append(column)
    old_rows = np.asarray(old_columns, dtype=np.int64).T
    prior_rows = np.asarray(prior_matrix[np.asarray(selected_sequences)], dtype=np.int64).T
    next_rows = np.asarray(next_matrix[np.asarray(selected_sequences)], dtype=np.int64).T
    pair_rows = np.asarray(pair_matrix[np.asarray(selected_sequences)], dtype=np.int64).T
    all_rows = np.concatenate([old_rows, prior_rows, next_rows, pair_rows], axis=0)
    new_rank = CURRENT_RANK + quotient_rank
    assert all_rows.shape == (CURRENT_ROWS + PAIR_ROWS, new_rank)

    current_square = np.asarray(
        all_rows[current_coordinate_rows, :CURRENT_RANK], dtype=np.int64
    )
    current_square_rank, _ = row_rank_and_pivot_columns(current_square, PRIME)
    assert current_square_rank == CURRENT_RANK
    current_inverse = inverse_mod(current_square, PRIME)
    current_coordinates_on_witness = np.asarray(
        all_rows[current_coordinate_rows, CURRENT_RANK:], dtype=np.int64
    )
    pair_on_current_basis = np.asarray(all_rows[CURRENT_ROWS:, :CURRENT_RANK], dtype=np.int64)
    pair_on_witness = np.asarray(all_rows[CURRENT_ROWS:, CURRENT_RANK:], dtype=np.int64)
    pair_lambdas = ((pair_on_current_basis % PRIME) @ current_inverse) % PRIME
    predicted_on_witness = (
        pair_lambdas @ (current_coordinates_on_witness % PRIME)
    ) % PRIME
    quotient_witness = (pair_on_witness - predicted_on_witness) % PRIME
    verified_rank, direction_pivots = row_rank_and_pivot_columns(
        quotient_witness.T, PRIME
    )
    assert verified_rank == quotient_rank
    coordinate_rows = current_coordinate_rows + [CURRENT_ROWS + index for index in direction_pivots]
    assert len(coordinate_rows) == new_rank
    square_rows = np.asarray(all_rows[coordinate_rows], dtype=np.int64)
    square_rank, _ = row_rank_and_pivot_columns(square_rows, PRIME)
    assert square_rank == new_rank

    target = [int(value) for value in state["target"]] + [0] * (
        PRIOR_ROWS + NEXT_ROWS + PAIR_ROWS
    )
    exact_square = fmpq_mat(fmpz_mat(square_rows.tolist()))
    rhs = fmpq_mat(fmpz_mat([[target[row]] for row in coordinate_rows]))
    solution = exact_square.solve(rhs)
    rationals = [
        Fraction(int(solution[index, 0].numerator), int(solution[index, 0].denominator))
        for index in range(new_rank)
    ]
    coefficients, scale = normalize(rationals)
    residual = fmpz_mat(all_rows.tolist()) * fmpz_mat([[value] for value in coefficients])
    residual -= fmpz_mat([[scale * value] for value in target])
    residual_values = [int(residual[row, 0]) for row in range(len(target))]
    assert not any(residual_values)
    terms = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in sorted(zip(selected_sequences, coefficients, strict=True))
        if coefficient
    ]
    output = {
        "provisional_only": True,
        "result": "EXACT_924_ROW_DUPLICATE_PAIR_BATCH_MEMBER_PROVISIONAL",
        "records": RECORDS,
        "rows": len(target),
        "current_selected_minor_rank": CURRENT_RANK,
        "pair_batch_quotient_rank_mod_1000003_relative_to_selected_595_coordinates": quotient_rank,
        "selected_minor_rank_over_Q": new_rank,
        "basis_sequences": selected_sequences,
        "pair_witness_sequences": witness_sequences,
        "pair_coordinate_direction_indices": direction_pivots,
        "coordinate_rows": coordinate_rows,
        "integer_coefficients": [str(value) for value in coefficients],
        "integer_coefficients_decimal_lf_sha256": decimal_digest(coefficients),
        "target_scale": str(scale),
        "support_columns": len(terms),
        "terms": terms,
        "all_924_rows_exactly_replayed": True,
        "residuals_decimal_lf_sha256": decimal_digest(residual_values),
        "inputs": {
            "quotient_sha256": quotient_opening_sha256,
            "pair_matrix_sha256": receipt["matrix_sha256"],
            "prior_matrix_sha256": PRIOR_MATRIX_SHA256,
            "next_matrix_sha256": NEXT_MATRIX_SHA256,
            "selection_sha256": selection_opening_sha256,
            "receipt_sha256": receipt_opening_sha256,
            "current_member_sha256": receipt["inputs"]["member_sha256"],
            "prior_member_sha256": PRIOR_MEMBER_SHA256,
        },
    }
    assert file_sha256(pair_matrix_path) == output["inputs"]["pair_matrix_sha256"]
    assert file_sha256(prior_matrix_path) == output["inputs"]["prior_matrix_sha256"]
    assert file_sha256(next_matrix_path) == output["inputs"]["next_matrix_sha256"]
    assert file_sha256(selection_path) == output["inputs"]["selection_sha256"]
    assert file_sha256(receipt_path) == output["inputs"]["receipt_sha256"]
    assert file_sha256(quotient_path) == quotient_opening_sha256
    assert file_sha256(current_path) == current_opening_sha256
    assert file_sha256(prior_member_path) == prior_member_opening_sha256
    output_path.write_text(
        json.dumps(output, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "provisional_only": True,
                "result": output["result"],
                "selected_minor_rank_over_Q": output["selected_minor_rank_over_Q"],
                "support_columns": output["support_columns"],
                "target_scale_digits": len(str(scale)),
                "coefficient_digest": output["integer_coefficients_decimal_lf_sha256"],
                "output": str(output_path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
