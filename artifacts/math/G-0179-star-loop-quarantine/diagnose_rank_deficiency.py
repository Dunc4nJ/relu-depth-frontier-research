#!/usr/bin/env python3
"""Diagnose the frozen G-0179 rank-5291 branch without target information."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
from typing import Any

import numpy as np


N = 5_771
RANK = 5_291
EXPECTED = {
    "matrix": "0e7236e06adc906f2859338b12848e6fc04156963d1567de84dd1e83784162ad",
    "records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "directions": "231752384d357be45a9d2513a9185539bf0df970640c28e4f259da37fc8a982f",
    "rank_1000003": "c368c31700b498847256337973d51d9804351704f44cbb74da163aea750bf5d5",
    "rank_1000033": "1b20292d0e297ed7bdceccd53d637abed5836d07d78b9976c7f5c8d7d64c4e51",
    "transpose_rank_1000003": "850f4953f266888139b97d2bac552fa35e83a0ff209fbad3286b32d999258222",
    "transpose_rank_1000033": "0f815c8b779688d11301025f3a9f74784ee97c052995a84bb7c4359e34eb24f3",
    "harvester": "506f251dff9ee30840dffe81e5112ca2713b136c634e07a36d3fca4c4c92e3ce",
}
TRANSPOSE_MATRIX_SHA256 = (
    "b9be374a58d133eba6255fd90ecbad91d62dc4ced05016d53afa6a9bebca1216"
)
REMOVED_SEQUENCES = {1548, 4259}
HASH_FILL_DOMAIN = b"G-0179-unused-direction-order-v1\0"


class DiagnosticError(RuntimeError):
    """A frozen result or diagnostic invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_harvester(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("g0179_frozen_harvester", path)
    if spec is None or spec.loader is None:
        raise DiagnosticError("could not import frozen structural harvester")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def direction_digest(directions: list[tuple[int, ...]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        if len(direction) != 11 or any(not -128 <= value <= 127 for value in direction):
            raise DiagnosticError("malformed signed-i8 direction")
        digest.update(bytes(value & 0xFF for value in direction))
    return digest.hexdigest()


def direction_bytes(direction: tuple[int, ...]) -> bytes:
    if len(direction) != 11 or any(not -128 <= value <= 127 for value in direction):
        raise DiagnosticError("malformed signed-i8 direction")
    return bytes(value & 0xFF for value in direction)


def hash_fill_key(direction: tuple[int, ...]) -> tuple[bytes, bytes]:
    raw = direction_bytes(direction)
    return hashlib.sha256(HASH_FILL_DOMAIN + raw).digest(), raw


def duplicate_pairs(hashes: list[bytes]) -> list[list[int]]:
    first: dict[bytes, int] = {}
    duplicates: list[list[int]] = []
    for index, digest in enumerate(hashes):
        if digest in first:
            duplicates.append([index, first[digest]])
        else:
            first[digest] = index
    return duplicates


def validate_rank_receipt(
    receipt: dict[str, Any], prime: int, raw_sha256: str
) -> list[int]:
    required = {
        "schema": "g0181.flint-signed-le-rank-certificate.v2",
        "prime": prime,
        "input_rows": N,
        "input_columns": N,
        "selected_rows": N,
        "selected_columns": N,
        "selected_cells": N * N,
        "reduction_crosscheck_cells": N * N,
        "selected_raw_cells_sha256": raw_sha256,
        "rank_mod_prime": RANK,
        "determinant_mod_prime": 0,
        "full_rank_mod_prime": False,
    }
    for key, value in required.items():
        if receipt.get(key) != value:
            raise DiagnosticError(
                f"rank receipt p={prime} field {key}: {receipt.get(key)!r} != {value!r}"
            )
    pivots = receipt.get("pivot_columns")
    if not isinstance(pivots, list) or len(pivots) != RANK:
        raise DiagnosticError(f"rank receipt p={prime} pivot census drift")
    if pivots != sorted(set(pivots)) or not all(0 <= value < N for value in pivots):
        raise DiagnosticError(f"rank receipt p={prime} malformed pivots")
    return pivots


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix", required=True, type=Path)
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--directions", required=True, type=Path)
    parser.add_argument("--rank-1000003", required=True, type=Path)
    parser.add_argument("--rank-1000033", required=True, type=Path)
    parser.add_argument("--transpose-rank-1000003", required=True, type=Path)
    parser.add_argument("--transpose-rank-1000033", required=True, type=Path)
    parser.add_argument("--harvester", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise DiagnosticError(f"refusing to overwrite {arguments.output}")

    paths = {
        "matrix": arguments.matrix.resolve(strict=True),
        "records": arguments.records.resolve(strict=True),
        "directions": arguments.directions.resolve(strict=True),
        "rank_1000003": arguments.rank_1000003.resolve(strict=True),
        "rank_1000033": arguments.rank_1000033.resolve(strict=True),
        "transpose_rank_1000003": arguments.transpose_rank_1000003.resolve(strict=True),
        "transpose_rank_1000033": arguments.transpose_rank_1000033.resolve(strict=True),
        "harvester": arguments.harvester.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    if opening != EXPECTED:
        raise DiagnosticError(f"frozen input hash drift: {opening}")
    if paths["matrix"].stat().st_size != N * N * 8:
        raise DiagnosticError("matrix byte-size drift")

    rank_a = json.loads(paths["rank_1000003"].read_bytes())
    rank_b = json.loads(paths["rank_1000033"].read_bytes())
    direction_pivots_a = validate_rank_receipt(rank_a, 1_000_003, EXPECTED["matrix"])
    direction_pivots_b = validate_rank_receipt(rank_b, 1_000_033, EXPECTED["matrix"])
    if direction_pivots_a != direction_pivots_b:
        raise DiagnosticError("direction pivots disagree across primes")

    transpose_a = json.loads(paths["transpose_rank_1000003"].read_bytes())
    transpose_b = json.loads(paths["transpose_rank_1000033"].read_bytes())
    record_pivots_a = validate_rank_receipt(
        transpose_a, 1_000_003, TRANSPOSE_MATRIX_SHA256
    )
    record_pivots_b = validate_rank_receipt(
        transpose_b, 1_000_033, TRANSPOSE_MATRIX_SHA256
    )
    if record_pivots_a != record_pivots_b:
        raise DiagnosticError("record pivots disagree across primes")

    records_document = json.loads(paths["records"].read_bytes())
    all_records = records_document.get("records")
    if not isinstance(all_records, list) or len(all_records) != 5_773:
        raise DiagnosticError("record census drift")
    records = [
        record for record in all_records if record.get("sequence") not in REMOVED_SEQUENCES
    ]
    if len(records) != N:
        raise DiagnosticError("retained-record census drift")
    directions_document = json.loads(paths["directions"].read_bytes())
    selected = [tuple(map(int, direction)) for direction in directions_document["directions"]]
    if len(selected) != N or len(set(selected)) != N:
        raise DiagnosticError("selected-direction census/uniqueness drift")

    matrix = np.memmap(paths["matrix"], dtype="<i8", mode="r", shape=(N, N))
    row_nonzero = np.count_nonzero(matrix, axis=1)
    column_nonzero = np.count_nonzero(matrix, axis=0)
    row_hashes = [
        hashlib.sha256(np.ascontiguousarray(matrix[index, :]).view(np.uint8)).digest()
        for index in range(N)
    ]
    column_hashes = [
        hashlib.sha256(np.ascontiguousarray(matrix[:, index]).view(np.uint8)).digest()
        for index in range(N)
    ]
    duplicate_rows = duplicate_pairs(row_hashes)
    duplicate_columns = duplicate_pairs(column_hashes)

    harvester = load_harvester(paths["harvester"])
    prepared = [harvester.prepare_record(record) for record in records]
    adjacency = [
        harvester.candidate_directions(record, item)
        for record, item in zip(records, prepared, strict=True)
    ]
    universe = set().union(*(set(row) for row in adjacency))
    selected_set = set(selected)
    unpriced = universe - selected_set
    if len(universe) != 16_661 or len(unpriced) != 10_890:
        raise DiagnosticError("candidate universe/unpriced census drift")

    dependent_indices = sorted(set(range(N)) - set(record_pivots_a))
    if len(dependent_indices) != N - RANK:
        raise DiagnosticError("dependent-record census drift")
    residual_adjacency = [
        [direction for direction in adjacency[index] if direction in unpriced]
        for index in dependent_indices
    ]
    nullable_matching, reverse = harvester.hopcroft_karp(residual_adjacency)
    dependent_matching = [
        direction for direction in nullable_matching if direction is not None
    ]
    if len(dependent_matching) != 466 or len(reverse) != 466:
        raise DiagnosticError("dependent-row expansion matching drift")
    hash_ranked_unpriced = sorted(unpriced, key=hash_fill_key)
    minimal_prefix = hash_ranked_unpriced[:480]
    minimal_prefix_set = set(minimal_prefix)
    support_supplement = [
        direction
        for direction in dependent_matching
        if direction not in minimal_prefix_set
    ]
    first_batch = minimal_prefix + support_supplement
    first_batch_set = set(first_batch)
    for direction in hash_ranked_unpriced:
        if len(first_batch) == 1_024:
            break
        if direction not in first_batch_set:
            first_batch.append(direction)
            first_batch_set.add(direction)
    expansion_order = first_batch + [
        direction for direction in hash_ranked_unpriced if direction not in first_batch_set
    ]
    if len(expansion_order) != 10_890 or len(set(expansion_order)) != 10_890:
        raise DiagnosticError("expansion-order census/uniqueness drift")

    dependent_records = []
    for local_index, record_index in enumerate(dependent_indices):
        record = records[record_index]
        matched = nullable_matching[local_index]
        dependent_records.append(
            {
                "retained_record_index": record_index,
                "record_sequence": record["sequence"],
                "signed_class_sha256": record["signed_class_sha256"],
                "signed_mass": record["signed_mass"],
                "active_vertices": record["active_vertices"],
                "unpriced_own_candidate_count": len(residual_adjacency[local_index]),
                "matched_expansion_direction": list(matched) if matched is not None else None,
            }
        )

    closing = {name: sha256_file(path) for name, path in paths.items()}
    if closing != opening:
        raise DiagnosticError("input changed during diagnostic")
    result = {
        "schema": "g0179.rank-5291-deficiency-diagnostic.v1",
        "result": "STABLE_TWO_PRIME_RANK_5291_WITH_480_UNRESOLVED_RECORD_DIRECTIONS",
        "claim_boundary": (
            "Exact finite diagnostics of the frozen G-0179 matrix and its two modular "
            "RREFs. Equal rank at two primes is strong evidence but does not prove the "
            "rank over Q is 5291. The post-outcome expansion order is target-blind but "
            "rank-outcome-aware; it is not a preregistered rank result or theorem."
        ),
        "matrix": {
            "shape": [N, N],
            "encoding": "record-major signed-i64 little-endian",
            "bytes": N * N * 8,
            "sha256": EXPECTED["matrix"],
            "zero_rows": np.flatnonzero(row_nonzero == 0).tolist(),
            "zero_columns": np.flatnonzero(column_nonzero == 0).tolist(),
            "unique_exact_rows": N - len(duplicate_rows),
            "duplicate_exact_row_pairs": duplicate_rows,
            "unique_exact_columns": N - len(duplicate_columns),
            "duplicate_exact_column_pairs": duplicate_columns,
        },
        "modular_result": {
            "primes": [1_000_003, 1_000_033],
            "ranks": [RANK, RANK],
            "deficiency": N - RANK,
            "direction_pivots_identical_across_primes": True,
            "record_pivots_from_transpose_identical_across_primes": True,
            "direction_pivot_count": len(direction_pivots_a),
            "record_pivot_count": len(record_pivots_a),
        },
        "dependent_records": dependent_records,
        "dependent_record_sequence_u64le_sha256": hashlib.sha256(
            b"".join(
                int(item["record_sequence"]).to_bytes(8, "little")
                for item in dependent_records
            )
        ).hexdigest(),
        "dependent_mass_histogram": {
            str(key): value
            for key, value in sorted(
                Counter(item["signed_mass"] for item in dependent_records).items()
            )
        },
        "candidate_expansion": {
            "candidate_universe": len(universe),
            "already_priced": len(selected_set),
            "unpriced": len(unpriced),
            "dependent_rows": len(dependent_indices),
            "dependent_rows_with_no_unpriced_own_candidate": sum(
                not row for row in residual_adjacency
            ),
            "dependent_row_structural_matching_size": len(dependent_matching),
            "expansion_order_rule": (
                "first the 480 smallest unpriced directions by "
                "SHA256(domain || raw_i8(direction)), breaking hash ties by raw_i8; "
                "then every deterministic dependent-record Hopcroft-Karp match absent "
                "from that prefix, in increasing retained-record index; then hash-ranked "
                "directions absent from the prefix until 1024 columns; finally the "
                "remaining hash-ranked unpriced directions"
            ),
            "hash_fill_domain_utf8_with_terminal_nul": (
                HASH_FILL_DOMAIN[:-1].decode("ascii") + "\\0"
            ),
            "hash_ranked_unpriced_count": len(hash_ranked_unpriced),
            "hash_ranked_unpriced_i8_sha256": direction_digest(hash_ranked_unpriced),
            "minimal_prefix_count": len(minimal_prefix),
            "minimal_prefix_i8_sha256": direction_digest(minimal_prefix),
            "dependent_matching_count": len(dependent_matching),
            "dependent_matching_i8_sha256": direction_digest(dependent_matching),
            "support_supplement_count": len(support_supplement),
            "support_supplement_i8_sha256": direction_digest(support_supplement),
            "expansion_order_count": len(expansion_order),
            "expansion_order_i8_sha256": direction_digest(expansion_order),
            "first_batch_count": 1_024,
            "first_batch_i8_sha256": direction_digest(first_batch),
        },
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
        },
        "bindings": {
            "diagnostic_source": str(Path(__file__).resolve()),
            "diagnostic_source_sha256": sha256_file(Path(__file__).resolve()),
            "inputs_opening_sha256": opening,
        },
        "all_inputs_rehashed_unchanged_at_end": True,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(arguments.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_json(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(
        json.dumps(
            {
                "result": result["result"],
                "output": str(arguments.output.resolve()),
                "output_sha256": sha256_file(arguments.output),
                "expansion_order_i8_sha256": result["candidate_expansion"][
                    "expansion_order_i8_sha256"
                ],
                "first_batch_i8_sha256": result["candidate_expansion"][
                    "first_batch_i8_sha256"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"diagnose_rank_deficiency: {error}", file=sys.stderr)
        raise SystemExit(1)
