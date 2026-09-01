#!/usr/bin/env python3
"""Full-family quotient/compatibility scan for the 64 duplicate-pair batch."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import mmap
from pathlib import Path
import sys

import numpy as np

ROOT = Path("/data/projects/relu-depth-frontier-research")
PRIOR = Path("/tmp/g0168-explore.kEmA87")
NEXT = Path("/tmp/g0168-next.yerj9c")
HERE = Path(__file__).parent
sys.path.insert(0, str(PRIOR))
from quotient_rank import inverse_mod, row_rank_and_pivot_columns  # noqa: E402

RECORDS = 163_740
K = 128
CURRENT_RANK = 595
OLD_RANK = 349
CHUNK = 4096
ALLOWED_PRIMES = {1_000_003, 1_000_033}
PRIOR_MEMBER_SHA256 = "bd7ee2a8a92c490805f4a13d451f340d0f53cd6e4698062e422d444a84e609c6"
PRIOR_MATRIX_SHA256 = "9de042920c07b811efa25df550cd8860bc6715f24893ec316360b0ff28d0570c"
NEXT_MATRIX_SHA256 = "7fdf3ccf7f764ba1637b6de29f1f4c90ba6ef0a60f4868dad2922711998f6cb4"
MATRIX_BYTES = RECORDS * K * 8


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def selected_direction_digest(selection: dict[str, object]) -> str:
    items = selection["selected_residual_items"]
    assert isinstance(items, list) and len(items) == K
    digest = hashlib.sha256()
    for item in items:
        assert isinstance(item, dict)
        direction = item["direction"]
        assert isinstance(direction, list) and len(direction) == 11
        assert all(isinstance(value, int) and -128 <= value <= 127 for value in direction)
        digest.update(bytes(value & 0xFF for value in direction))
    return digest.hexdigest()


def main() -> None:
    if sys.flags.optimize != 0:
        raise RuntimeError("optimized Python prohibited")
    matrix_path = Path(sys.argv[1])
    prime = int(sys.argv[2])
    assert prime in ALLOWED_PRIMES
    assert CURRENT_RANK * (prime - 1) ** 2 < 2**63
    output_path = Path(sys.argv[3])
    assert not output_path.exists()
    receipt_path = HERE / "duplicate_pairs128_full_price_receipt.json"
    selection_path = HERE / "selected_duplicate_pairs_128.json"
    current_path = NEXT / "exact_796_member.json"
    prior_member_path = PRIOR / "exact_augmented_member.json"
    receipt_opening_sha256 = file_sha256(receipt_path)
    selection_opening_sha256 = file_sha256(selection_path)
    current_opening_sha256 = file_sha256(current_path)
    prior_member_opening_sha256 = file_sha256(prior_member_path)
    with receipt_path.open() as source:
        receipt = json.load(source)
    with selection_path.open() as source:
        selection = json.load(source)
    with current_path.open() as source:
        current = json.load(source)
    with prior_member_path.open() as source:
        prior_member = json.load(source)
    assert receipt["schema"] == "g0168.duplicate_pairs128_provisional_full_family_coordinates.v1"
    assert receipt["records"] == RECORDS
    assert receipt["directions"] == K
    assert receipt["global_direct_exact_dot_bridge"] is True
    assert receipt["matrix_path"] == str(matrix_path)
    assert receipt["matrix_bytes"] == MATRIX_BYTES
    assert matrix_path.stat().st_size == receipt["matrix_bytes"]
    matrix_sha256 = file_sha256(matrix_path)
    assert matrix_sha256 == receipt["matrix_sha256"]
    assert selection_opening_sha256 == receipt["inputs"]["selection_sha256"]
    assert current_opening_sha256 == receipt["inputs"]["member_sha256"]
    assert prior_member_opening_sha256 == PRIOR_MEMBER_SHA256
    assert selection["schema"] == "g0168.provisional_duplicate_pair_batch128.v1"
    assert selection["directions"] == K
    assert selection["predicted_pair_relations"] == K // 2
    assert selection["exact_residual_equality_within_every_pair"] is True
    assert selection["fingerprint_equality_under_both_primes"] is True
    directions_sha256 = selected_direction_digest(selection)
    assert directions_sha256 == selection["selected_directions_i8_sha256"]
    assert directions_sha256 == receipt["directions_i8_sha256"]
    selected_prices = np.memmap(matrix_path, dtype="<i8", mode="r", shape=(RECORDS, K))

    prior_path = PRIOR / "fresh128.record-major.i64le"
    next_path = NEXT / "next128.record-major.i64le"
    assert prior_path.stat().st_size == next_path.stat().st_size == MATRIX_BYTES
    assert file_sha256(prior_path) == PRIOR_MATRIX_SHA256
    assert file_sha256(next_path) == NEXT_MATRIX_SHA256
    prior_prices = np.memmap(prior_path, dtype="<i8", mode="r", shape=(RECORDS, K))
    next_prices = np.memmap(next_path, dtype="<i8", mode="r", shape=(RECORDS, K))
    prior_indices = [int(value) for value in prior_member["fresh_coordinate_direction_indices"]]
    next_indices = [int(value) for value in current["next_coordinate_direction_indices"]]
    assert len(prior_indices) == 119
    assert len(next_indices) == 127
    basis = np.asarray(current["basis_sequences"], dtype=np.int64)
    assert basis.shape == (CURRENT_RANK,)
    assert prior_member["result"] == "EXACT_668_ROW_FRESH128_MEMBER_PROVISIONAL"
    assert prior_member["rows"] == 668
    assert len(prior_member["basis_sequences"]) == len(prior_member["coordinate_rows"]) == 468
    assert current["result"] == "EXACT_796_ROW_SECOND_FRESH128_MEMBER_PROVISIONAL"
    assert current["rows"] == 796
    assert len(current["coordinate_rows"]) == CURRENT_RANK
    assert current["basis_sequences"][:468] == prior_member["basis_sequences"]

    solver_path = ROOT / "artifacts/math/G-0164/all128_direct_basis_master_v1.py"
    spec = importlib.util.spec_from_file_location("g0168_pair_scan_g0164", solver_path)
    assert spec is not None and spec.loader is not None
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)
    state = solver.validate_sealed_inputs()
    old_coordinate_rows = state["coordinate_rows"]
    assert len(old_coordinate_rows) == OLD_RANK
    assert prior_member["coordinate_rows"] == old_coordinate_rows + [540 + index for index in prior_indices]
    assert current["coordinate_rows"] == (
        old_coordinate_rows
        + [540 + index for index in prior_indices]
        + [668 + index for index in next_indices]
    )
    prepared = state["g0135_prepared"]
    components = prepared["components"]
    panel_rows = [row for row in old_coordinate_rows if row < 301]
    linear_rows = [row - 301 for row in old_coordinate_rows if 301 <= row < 312]
    hinge_sources: list[list[int]] = []
    hinge_sources.extend(components["accumulated"])
    hinge_sources.extend(components["old_batch_block"]["rows"])
    hinge_sources.extend(components["new_batch_block"]["rows"])
    hinge_sources.extend(prepared["stage_b_rows"])
    hinge_sources.extend(state["all_pool_rows"])
    hinge_indices = [row - 312 for row in old_coordinate_rows if row >= 312]
    assert len(panel_rows) + len(linear_rows) + len(hinge_indices) == OLD_RANK
    ancestor = prepared["ancestor"]
    cache_file = ancestor.AUDITED.CACHE_PATH.open("rb")
    cache_map = mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ)
    cache = np.ndarray(
        shape=(RECORDS, 301),
        dtype=np.dtype([("lo", "<i8"), ("hi", "<i8")]),
        buffer=cache_map,
    )

    def old_coordinate_chunk(start: int, stop: int) -> np.ndarray:
        parts: list[np.ndarray] = []
        panel = np.asarray(cache["lo"][start:stop, panel_rows], dtype=np.int64)
        panel_hi = np.asarray(cache["hi"][start:stop, panel_rows], dtype=np.int64)
        assert np.array_equal(panel_hi, np.where(panel < 0, -1, 0))
        parts.append(panel)
        linear = np.asarray(components["linear"][start:stop], dtype=np.int64)
        parts.append(linear[:, linear_rows])
        parts.append(
            np.asarray(
                [hinge_sources[index][start:stop] for index in hinge_indices],
                dtype=np.int64,
            ).T
        )
        result = np.concatenate(parts, axis=1)
        assert result.shape == (stop - start, OLD_RANK)
        return result

    def current_coordinate_chunk(start: int, stop: int) -> np.ndarray:
        result = np.concatenate(
            [
                old_coordinate_chunk(start, stop),
                np.asarray(prior_prices[start:stop][:, prior_indices], dtype=np.int64),
                np.asarray(next_prices[start:stop][:, next_indices], dtype=np.int64),
            ],
            axis=1,
        )
        assert result.shape == (stop - start, CURRENT_RANK)
        return result

    square_columns = [current_coordinate_chunk(int(seq), int(seq) + 1)[0] for seq in basis]
    square = np.asarray(square_columns, dtype=np.int64).T
    square_rank, _ = row_rank_and_pivot_columns(square, prime)
    assert square_rank == CURRENT_RANK
    inverse = inverse_mod(square, prime)
    selected_on_basis = np.asarray(selected_prices[basis], dtype=np.int64).T
    lambdas = (selected_on_basis % prime) @ inverse % prime

    quotient_basis = np.empty((0, K), dtype=np.int64)
    pivot_sequences: list[int] = []
    for start in range(0, RECORDS, CHUNK):
        stop = min(RECORDS, start + CHUNK)
        coordinates = current_coordinate_chunk(start, stop)
        predicted = (coordinates % prime) @ lambdas.T % prime
        quotient = (np.asarray(selected_prices[start:stop], dtype=np.int64) - predicted) % prime
        combined = np.concatenate([quotient_basis, quotient], axis=0)
        rank, pivots = row_rank_and_pivot_columns(combined.T, prime)
        prior_rank = len(quotient_basis)
        assert pivots[:prior_rank] == list(range(prior_rank))
        new_positions = [index - prior_rank for index in pivots[prior_rank:]]
        pivot_sequences.extend(start + position for position in new_positions)
        quotient_basis = combined[pivots]
        print(
            json.dumps(
                {
                    "provisional_only": True,
                    "prime": prime,
                    "scanned": stop,
                    "quotient_rank": rank,
                    "new_pivots": [start + position for position in new_positions],
                },
                sort_keys=True,
            ),
            flush=True,
        )
        if rank == K:
            break

    residual = np.asarray(
        [int(item["coefficient"]) % prime for item in selection["selected_residual_items"]],
        dtype=np.int64,
    )
    augmented = np.concatenate([quotient_basis.T, residual[:, None]], axis=1)
    augmented_rank, _ = row_rank_and_pivot_columns(augmented, prime)
    result = {
        "provisional_only": True,
        "prime": prime,
        "records_scanned": min(RECORDS, stop),
        "current_selected_minor_rank": CURRENT_RANK,
        "directions": K,
        "predicted_pair_relations": K // 2,
        "quotient_rank_relative_to_selected_595_coordinates": len(quotient_basis),
        "augmented_with_residual_rank": augmented_rank,
        "residual_compatible_mod_prime": augmented_rank == len(quotient_basis),
        "pivot_sequences": pivot_sequences,
        "matrix_sha256": matrix_sha256,
        "selection_sha256": selection_opening_sha256,
        "receipt_sha256": receipt_opening_sha256,
        "selected_directions_i8_sha256": directions_sha256,
    }
    assert file_sha256(matrix_path) == matrix_sha256
    assert file_sha256(prior_path) == PRIOR_MATRIX_SHA256
    assert file_sha256(next_path) == NEXT_MATRIX_SHA256
    assert file_sha256(selection_path) == result["selection_sha256"]
    assert file_sha256(receipt_path) == result["receipt_sha256"]
    assert file_sha256(current_path) == current_opening_sha256
    assert file_sha256(prior_member_path) == prior_member_opening_sha256
    print(json.dumps(result, sort_keys=True), flush=True)
    output_path.write_text(
        json.dumps(result, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    cache_map.close()
    cache_file.close()


if __name__ == "__main__":
    main()
