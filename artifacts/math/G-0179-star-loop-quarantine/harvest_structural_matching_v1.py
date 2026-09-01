#!/usr/bin/env python3
"""Freeze the target-blind STAR loop structural matching and 256-row pilot.

This is a source-frozen form of the 2026-09-01 inline harvester.  It reads
only the canonical STAR-outside-primary record census.  It does not read a
priced matrix, target, rank, residual, or theorem outcome.

The output matching is a matching in the *candidate support graph*.  It is
not a determinant or rank certificate: cross-pricing can introduce many
off-matching nonzeros, and a structurally matched square matrix can still be
singular.
"""

from __future__ import annotations

import argparse
from collections import deque
import hashlib
import json
from pathlib import Path
import platform
import random
import sys
from typing import Any


N = 11
CANDIDATES_PER_RECORD = 8
SEED_XOR = 0x9E3779B97F4A7C15
SAMPLE_COUNT = 256

EXPECTED_RECORDS_SHA256 = (
    "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4"
)
EXPECTED_RECORD_COUNT = 5_773
EXPECTED_MATCHED_COUNT = 5_771
EXPECTED_CANDIDATE_EDGE_COUNT = 46_168
EXPECTED_CANDIDATE_DIRECTION_COUNT = 16_661
EXPECTED_MATCHED_DIRECTIONS_I8_SHA256 = (
    "858c182304ae5256dfa85e720803b54013afb70b7b67383aa6680ecbc0d8336d"
)
EXPECTED_SAMPLE_DIRECTIONS_I8_SHA256 = (
    "fae62eb868b2bd287270489af61b60a00d1262662576f6de8631d5ec0ae504c8"
)

# These two columns were removed before matching because independent exact
# semantic controls identify them as old-span columns.  Those semantic claims
# are inputs to this structural experiment, not proved by this script.
REMOVED_SEQUENCES = {
    1548: "exactly 5E in complete ordered-chamber normal form",
    4259: "exactly 2*old_sequence_5341-old_sequence_66223 in complete ordered-chamber normal form",
}


class FreezeError(RuntimeError):
    """A frozen input, algorithm, census, or output invariant failed."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def write_exclusive(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()


def raw_direction(direction: tuple[int, ...] | list[int]) -> bytes:
    if len(direction) != N:
        raise FreezeError(f"direction width drift: {len(direction)}")
    if any(value < -128 or value > 127 for value in direction):
        raise FreezeError(f"direction does not fit signed i8: {direction}")
    return bytes(value & 0xFF for value in direction)


def directions_digest(directions: list[tuple[int, ...]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        digest.update(raw_direction(direction))
    return digest.hexdigest()


def load_records(path: Path) -> list[dict[str, Any]]:
    observed_hash = sha256_path(path)
    if observed_hash != EXPECTED_RECORDS_SHA256:
        raise FreezeError(
            f"record SHA-256 drift: {observed_hash} != {EXPECTED_RECORDS_SHA256}"
        )
    document = json.loads(path.read_bytes())
    records = document.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_RECORD_COUNT:
        raise FreezeError("record census drift")
    if [record.get("sequence") for record in records] != list(
        range(EXPECTED_RECORD_COUNT)
    ):
        raise FreezeError("record sequence/order drift")
    hashes = [record.get("signed_class_sha256") for record in records]
    if hashes != sorted(hashes) or len(set(hashes)) != len(hashes):
        raise FreezeError("canonical signed-class ordering drift")
    return records


def prepare_record(
    record: dict[str, Any],
) -> tuple[int, int, list[int], list[list[int]]]:
    """Build the loop vector and symmetric nonloop matrix used inline."""
    active = record["active_vertices"]
    if not isinstance(active, int) or not 1 <= active <= N:
        raise FreezeError(f"invalid active_vertices at {record['sequence']}")
    loops = [0] * active
    matrix = [[0] * active for _ in range(active)]
    for sign, key in ((-1, "negative_edges"), (1, "positive_edges")):
        for edge in record[key]:
            if not isinstance(edge, list) or len(edge) != 2:
                raise FreezeError(f"invalid edge at {record['sequence']}: {edge}")
            u, v = edge
            if not 0 <= u <= v < active:
                raise FreezeError(f"noncanonical edge at {record['sequence']}: {edge}")
            if u == v:
                loops[u] += sign
            else:
                matrix[u][v] += sign
                matrix[v][u] += sign
    nonzero_loops = [index for index, value in enumerate(loops) if value]
    if len(nonzero_loops) != 1:
        raise FreezeError(
            f"record {record['sequence']} has {len(nonzero_loops)} signed loops"
        )
    loop = nonzero_loops[0]
    if abs(loops[loop]) != 1:
        raise FreezeError(f"record {record['sequence']} has nonunit signed loop")
    if loops[loop] < 0:
        loops = [-value for value in loops]
        matrix = [[-value for value in row] for row in matrix]
    return active, loop, loops, matrix


def candidate_directions(
    record: dict[str, Any],
    prepared: tuple[int, int, list[int], list[list[int]]],
    need: int = CANDIDATES_PER_RECORD,
) -> list[tuple[int, ...]]:
    """Reproduce the exact target-blind inline candidate sampler.

    Inactive sentinels are repeated -1 values.  ``shuffle`` mutates the same
    token list between attempts.  A direction is retained only if an internal
    prefix sum is negative, the activation condition used by the inline run.
    The final set is sorted before matching, removing set-iteration ambiguity.
    """
    active, loop, loops, matrix = prepared
    tokens = [vertex for vertex in range(active) if vertex != loop]
    tokens.extend([-1] * (N - active))
    if len(tokens) != N - 1:
        raise FreezeError(f"token width drift at record {record['sequence']}")

    seed = int(record["signed_class_sha256"][:16], 16) ^ SEED_XOR
    rng = random.Random(seed)
    output: set[tuple[int, ...]] = set()
    attempts = 0
    maximum_attempts = need * 40 + 100
    while len(output) < need and attempts < maximum_attempts:
        attempts += 1
        rng.shuffle(tokens)
        used = [loop]
        word = [1]
        prefix = 1
        active_hinge = False
        for position, vertex in enumerate(tokens, 1):
            if vertex < 0:
                value = 0
            else:
                value = loops[vertex] + sum(
                    matrix[vertex][earlier] for earlier in used
                )
                used.append(vertex)
            word.append(value)
            prefix += value
            if position < N - 1 and prefix < 0:
                active_hinge = True
        if active_hinge:
            output.add(tuple(word))
    if len(output) < need:
        raise FreezeError(
            f"record {record['sequence']} yielded {len(output)} < {need} candidates"
        )
    return sorted(output)


def hopcroft_karp(
    adjacency: list[list[tuple[int, ...]]],
) -> tuple[list[tuple[int, ...] | None], dict[tuple[int, ...], int]]:
    """Reproduce the exact deterministic inline Hopcroft--Karp traversal."""
    left_match: list[tuple[int, ...] | None] = [None] * len(adjacency)
    right_match: dict[tuple[int, ...], int] = {}
    distance = [0] * len(adjacency)
    while True:
        queue: deque[int] = deque()
        found = False
        for left in range(len(adjacency)):
            if left_match[left] is None:
                distance[left] = 0
                queue.append(left)
            else:
                distance[left] = -1
        while queue:
            left = queue.popleft()
            for right in adjacency[left]:
                next_left = right_match.get(right)
                if next_left is None:
                    found = True
                elif distance[next_left] < 0:
                    distance[next_left] = distance[left] + 1
                    queue.append(next_left)
        if not found:
            break

        def augment(left: int) -> bool:
            for right in adjacency[left]:
                next_left = right_match.get(right)
                if next_left is None or (
                    distance[next_left] == distance[left] + 1
                    and augment(next_left)
                ):
                    left_match[left] = right
                    right_match[right] = left
                    return True
            distance[left] = -1
            return False

        augmented = sum(
            left_match[left] is None and augment(left)
            for left in range(len(adjacency))
        )
        if not augmented:
            break
    return left_match, right_match


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("records", type=Path)
    parser.add_argument("full_directions", type=Path)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("sample_directions", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    outputs = [
        arguments.full_directions,
        arguments.manifest,
        arguments.sample_directions,
    ]
    if len({path.resolve() for path in outputs}) != len(outputs):
        raise FreezeError("output paths must be distinct")
    existing = [str(path) for path in outputs if path.exists()]
    if existing:
        raise FreezeError(f"refusing to overwrite output(s): {existing}")

    records_path = arguments.records.resolve()
    records_all = load_records(records_path)
    records = [
        record
        for record in records_all
        if record["sequence"] not in REMOVED_SEQUENCES
    ]
    if len(records) != EXPECTED_MATCHED_COUNT:
        raise FreezeError("nonredundant record census drift")

    prepared = [prepare_record(record) for record in records]
    adjacency = [
        candidate_directions(record, item)
        for record, item in zip(records, prepared, strict=True)
    ]
    candidate_edges = sum(map(len, adjacency))
    candidate_universe = len(set().union(*map(set, adjacency)))
    if candidate_edges != EXPECTED_CANDIDATE_EDGE_COUNT:
        raise FreezeError(f"candidate edge census drift: {candidate_edges}")
    if candidate_universe != EXPECTED_CANDIDATE_DIRECTION_COUNT:
        raise FreezeError(f"candidate direction census drift: {candidate_universe}")

    nullable_matching, reverse_matching = hopcroft_karp(adjacency)
    if any(direction is None for direction in nullable_matching):
        raise FreezeError(f"matching is not complete: {len(reverse_matching)}")
    matching = [
        direction
        for direction in nullable_matching
        if direction is not None
    ]
    if len(matching) != EXPECTED_MATCHED_COUNT or len(set(matching)) != len(matching):
        raise FreezeError("matching size/uniqueness drift")
    matched_digest = directions_digest(matching)
    if matched_digest != EXPECTED_MATCHED_DIRECTIONS_I8_SHA256:
        raise FreezeError(
            f"matching digest drift: {matched_digest} != "
            f"{EXPECTED_MATCHED_DIRECTIONS_I8_SHA256}"
        )

    sample_indices = [
        (index * len(matching)) // SAMPLE_COUNT
        for index in range(SAMPLE_COUNT)
    ]
    if len(set(sample_indices)) != SAMPLE_COUNT:
        raise FreezeError("sample index duplication")
    sample = [matching[index] for index in sample_indices]
    if len(set(sample)) != SAMPLE_COUNT:
        raise FreezeError("sample direction duplication")
    sample_digest = directions_digest(sample)
    if sample_digest != EXPECTED_SAMPLE_DIRECTIONS_I8_SHA256:
        raise FreezeError(
            f"sample digest drift: {sample_digest} != "
            f"{EXPECTED_SAMPLE_DIRECTIONS_I8_SHA256}"
        )

    source_path = Path(__file__).resolve()
    source_hash = sha256_path(source_path)
    bindings = {
        "harvester_source": str(source_path),
        "harvester_source_sha256": source_hash,
        "records": str(records_path),
        "records_sha256": EXPECTED_RECORDS_SHA256,
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "python_executable": str(Path(sys.executable).resolve()),
        "random_engine": "CPython random.Random(seed) and in-place shuffle",
    }
    generation = (
        "loop-positive first; mutate one active/inactive token list with 8 "
        "deterministic retained shuffled directions per nonredundant column; "
        "retain only directions with a negative internal prefix; sort each "
        "candidate set; deterministic Hopcroft-Karp"
    )
    removed = {str(key): value for key, value in REMOVED_SEQUENCES.items()}
    claim_boundary = (
        "Target-blind structural support matching only. It is not a priced "
        "minor, determinant, modular-rank, kernel, span, or theorem certificate."
    )

    full_document = {
        "schema": "g0179.hinge-direction-batch.v1",
        "result": "TARGET_BLIND_STRUCTURAL_MATCHING_ROWS",
        "batch_kind": "STAR_LOOP_D0_EQ_1_MATCHING_5771",
        "claim_boundary": claim_boundary,
        "count": len(matching),
        "directions_i8_sha256": matched_digest,
        "directions": [list(direction) for direction in matching],
        "bindings": bindings,
        "sources": [
            {
                "records": str(records_path),
                "generation": generation,
                "seed_xor": f"0x{SEED_XOR:016x}",
                "removed_sequences": removed,
            }
        ],
    }
    manifest = {
        "schema": "g0179.target-blind-structural-matching.v1",
        "result": "COMPLETE_STRUCTURAL_MATCHING_REPRODUCED_FROM_FROZEN_SOURCE",
        "claim_boundary": claim_boundary,
        "bindings": bindings,
        "records": len(records),
        "records_sha256": EXPECTED_RECORDS_SHA256,
        "removed_sequences": removed,
        "candidate_generation": {
            "candidates_per_record": CANDIDATES_PER_RECORD,
            "maximum_attempts_per_record": CANDIDATES_PER_RECORD * 40 + 100,
            "seed_xor": f"0x{SEED_XOR:016x}",
            "candidate_edges": candidate_edges,
            "candidate_direction_universe": candidate_universe,
            "generation": generation,
        },
        "matching_size": len(reverse_matching),
        "directions_i8_sha256": matched_digest,
        "sample": {
            "count": SAMPLE_COUNT,
            "selection_rule": "index[k]=floor(k*5771/256), k=0..255",
            "canonical_order": (
                "records in input sequence order after removing sequences 1548 and 4259"
            ),
            "indices_zero_based": sample_indices,
            "record_sequences": [records[index]["sequence"] for index in sample_indices],
            "directions_i8_sha256": sample_digest,
            "statistical_boundary": (
                "deterministic evenly spaced canonical-order pilot, not a random, "
                "mass-stratified, active-vertex-stratified, or representative sample"
            ),
        },
        "matched": [
            {
                "record_sequence": record["sequence"],
                "signed_class_sha256": record["signed_class_sha256"],
                "signed_mass": record["signed_mass"],
                "active_vertices": record["active_vertices"],
                "direction": list(direction),
            }
            for record, direction in zip(records, matching, strict=True)
        ],
    }
    sample_document = {
        "schema": "g0179.hinge-direction-batch.v1",
        "result": "TARGET_BLIND_STRUCTURAL_MATCHING_ROWS",
        "batch_kind": "STAR_LOOP_MATCHING_CANONICAL_ORDER_SAMPLE_256",
        "claim_boundary": claim_boundary,
        "count": len(sample),
        "directions_i8_sha256": sample_digest,
        "directions": [list(direction) for direction in sample],
        "bindings": bindings,
        "selection": {
            "rule": "index[k]=floor(k*5771/256), k=0..255",
            "indices_zero_based": sample_indices,
            "record_sequences": [records[index]["sequence"] for index in sample_indices],
            "statistical_boundary": (
                "deterministic evenly spaced canonical-order pilot, not a random, "
                "mass-stratified, active-vertex-stratified, or representative sample"
            ),
        },
        "sources": [
            {
                "records": str(records_path),
                "generation": generation,
                "seed_xor": f"0x{SEED_XOR:016x}",
                "removed_sequences": removed,
            }
        ],
    }

    write_exclusive(arguments.full_directions, full_document)
    write_exclusive(arguments.manifest, manifest)
    write_exclusive(arguments.sample_directions, sample_document)
    print(
        json.dumps(
            {
                "source_sha256": source_hash,
                "records_sha256": EXPECTED_RECORDS_SHA256,
                "matching_size": len(matching),
                "candidate_edges": candidate_edges,
                "candidate_direction_universe": candidate_universe,
                "directions_i8_sha256": matched_digest,
                "sample_directions_i8_sha256": sample_digest,
                "full_document_sha256": sha256_path(arguments.full_directions),
                "manifest_document_sha256": sha256_path(arguments.manifest),
                "sample_document_sha256": sha256_path(arguments.sample_directions),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
