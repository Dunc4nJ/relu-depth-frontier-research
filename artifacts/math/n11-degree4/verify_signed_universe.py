#!/usr/bin/env python3
"""Independent structural verifier for the KWA degree-four universes."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import functools
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import random
import sys
import time
from typing import Iterable, Sequence


SCHEMA = "max11-kwa-loopless-signed-degree4-universe-v1"
EXPECTED_TOTALS = {9: 16_311, 10: 17_775}
RECORD_FIELDS = {
    "active_vertices",
    "signed_mass",
    "negative_edges",
    "positive_edges",
    "abs_components",
    "abs_beta",
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_records(records: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_bytes(record))
    return digest.hexdigest()


def connected_components(edges: Sequence[tuple[int, int]], vertices: int) -> int:
    if vertices == 0:
        return 0
    parent = list(range(vertices))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for first, second in edges:
        a, b = find(first), find(second)
        if a != b:
            parent[b] = a
    return len({find(value) for value in range(vertices)})


def literal_key(record: dict[str, object]) -> tuple[int, tuple[int, ...]]:
    vertices = int(record["active_vertices"])
    negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]  # type: ignore[arg-type]
    positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]  # type: ignore[arg-type]
    best: tuple[int, ...] | None = None
    for permutation in itertools.permutations(range(vertices)):
        for first, second in ((negative, positive), (positive, negative)):
            encoded: list[int] = []
            for side in (first, second):
                mapped = sorted(tuple(sorted((permutation[u], permutation[v]))) for u, v in side)
                for u, v in mapped:
                    encoded.extend((u, v))
            candidate = tuple(encoded)
            if best is None or candidate < best:
                best = candidate
    assert best is not None
    return vertices, best


def signed_matrix(record: dict[str, object]) -> tuple[tuple[int, ...], ...]:
    vertices = int(record["active_vertices"])
    matrix = [[0] * vertices for _ in range(vertices)]
    for sign, field in ((-1, "negative_edges"), (1, "positive_edges")):
        for raw in record[field]:  # type: ignore[index]
            first, second = map(int, raw)
            matrix[first][second] += sign
            matrix[second][first] += sign
    return tuple(tuple(row) for row in matrix)


def canonical_signed_matrix(matrix: tuple[tuple[int, ...], ...]) -> bytes:
    def fixed(subject: tuple[tuple[int, ...], ...]) -> bytes:
        vertices = len(subject)

        def refine(partition: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
            while True:
                refined: list[tuple[int, ...]] = []
                for cell in partition:
                    buckets: dict[tuple[int, ...], list[int]] = {}
                    for vertex in cell:
                        signature: list[int] = []
                        for target in partition:
                            counts = Counter(subject[vertex][other] for other in target)
                            for value in range(-4, 5):
                                signature.append(counts[value])
                        buckets.setdefault(tuple(signature), []).append(vertex)
                    for signature in sorted(buckets):
                        refined.append(tuple(buckets[signature]))
                next_partition = tuple(refined)
                if next_partition == partition:
                    return partition
                partition = next_partition

        @functools.lru_cache(maxsize=None)
        def search(partition: tuple[tuple[int, ...], ...]) -> bytes:
            partition = refine(partition)
            if all(len(cell) == 1 for cell in partition):
                order = [cell[0] for cell in partition]
                return bytes(
                    subject[order[row]][order[column]] + 4
                    for row in range(vertices)
                    for column in range(row + 1, vertices)
                )
            cell_index = next(index for index, cell in enumerate(partition) if len(cell) > 1)
            cell = partition[cell_index]
            candidates = []
            for vertex in cell:
                remainder = tuple(other for other in cell if other != vertex)
                child = partition[:cell_index] + ((vertex,), remainder) + partition[cell_index + 1 :]
                candidates.append(search(child))
            return min(candidates)

        return search((tuple(range(vertices)),))

    negated = tuple(tuple(-value for value in row) for row in matrix)
    return min(fixed(matrix), fixed(negated))


def relabel_record(record: dict[str, object], permutation: Sequence[int], swap: bool) -> dict[str, object]:
    negative_field, positive_field = (
        ("positive_edges", "negative_edges") if swap else ("negative_edges", "positive_edges")
    )

    def mapped(field: str) -> list[list[int]]:
        return [
            list(sorted((int(permutation[int(raw[0])]), int(permutation[int(raw[1])]))) )
            for raw in record[field]  # type: ignore[index]
        ]

    result = dict(record)
    result["negative_edges"] = mapped(negative_field)
    result["positive_edges"] = mapped(positive_field)
    return result


def validate_record(record: dict[str, object], position: int, n: int) -> tuple[int, int, int, int]:
    if set(record) != RECORD_FIELDS:
        raise ValueError(f"record {position} schema mismatch: {sorted(record)}")
    vertices = int(record["active_vertices"])
    mass = int(record["signed_mass"])
    negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]  # type: ignore[arg-type]
    positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]  # type: ignore[arg-type]
    if position == 0:
        if (vertices, mass, negative, positive) != (0, 0, [], []):
            raise ValueError("4E/zero signed graph sentinel mismatch")
        if int(record["abs_components"]) != 0 or int(record["abs_beta"]) != 0:
            raise ValueError("4E topology metadata mismatch")
        return 0, 0, 0, 0
    if not (1 <= mass <= 4) or len(negative) != mass or len(positive) != mass:
        raise ValueError(f"record {position} signed-mass mismatch")
    if not (2 <= vertices <= n):
        raise ValueError(f"record {position} active-vertex census invalid")
    all_edges = negative + positive
    if any(not (0 <= first < second < vertices) for first, second in all_edges):
        raise ValueError(f"record {position} has noncanonical/nonloopless edge")
    if set(negative) & set(positive):
        raise ValueError(f"record {position} is not occurrence-cancelled")
    if {value for edge in all_edges for value in edge} != set(range(vertices)):
        raise ValueError(f"record {position} has inactive or missing coordinate labels")
    components = connected_components(all_edges, vertices)
    beta = 2 * mass - vertices + components
    if int(record["abs_components"]) != components or int(record["abs_beta"]) != beta:
        raise ValueError(f"record {position} topology metadata mismatch")
    return mass, vertices, components, beta


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--producer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    begun = time.monotonic()
    raw = gzip.decompress(args.universe.read_bytes())
    document = json.loads(raw)
    if raw != canonical_bytes(document):
        raise ValueError("universe gzip payload is not canonical JSON")
    if document.get("schema") != SCHEMA or document.get("result") != "PASS":
        raise ValueError("universe schema/result mismatch")
    if document.get("script_sha256") != sha256_path(args.producer):
        raise ValueError("universe is stale relative to its producer")
    n = int(document["n"])
    if not 2 <= n <= 16 or int(document["branch_edge_occurrences"]) != 4:
        raise ValueError("universe dimension/branch-size mismatch")
    if document.get("loopless") is not True:
        raise ValueError("universe is not declared loopless")
    records = document.get("records")
    census = document.get("census")
    if not isinstance(records, list) or not isinstance(census, dict):
        raise ValueError("universe census/records absent")
    if int(census["signed_graph_orbits"]) != len(records):
        raise ValueError("record/census denominator mismatch")
    expected = EXPECTED_TOTALS.get(n)
    if expected is not None and len(records) != expected:
        raise ValueError(f"n={n} known orbit denominator mismatch")
    if document.get("records_sha256") != sha256_records(records):
        raise ValueError("record-stream hash mismatch")

    observed_topology: Counter[tuple[int, int, int, int]] = Counter()
    observed_strata: Counter[tuple[int, int]] = Counter()
    for position, record in enumerate(records):
        if not isinstance(record, dict):
            raise ValueError(f"record {position} is not an object")
        topology = validate_record(record, position, n)
        if position:
            observed_topology[topology] += 1
            observed_strata[topology[:2]] += 1
    declared_topology = Counter(
        {
            (
                int(item["signed_mass"]),
                int(item["active_vertices"]),
                int(item["abs_components"]),
                int(item["abs_beta"]),
            ): int(item["signed_graph_orbits"])
            for item in document["topology_histogram"]
        }
    )
    if observed_topology != declared_topology:
        raise ValueError("topology histogram does not replay from records")
    declared_strata = Counter(
        {
            (int(item["signed_mass"]), int(item["active_vertices"])): int(item["signed_graph_orbits"])
            for item in census["strata"]
            if int(item["signed_mass"]) != 0
        }
    )
    if observed_strata != declared_strata:
        raise ValueError("stratum census does not replay from records")
    if any(int(item["signed_graph_orbits"]) != int(item["burnside_orbits"]) for item in census["strata"]):
        raise ValueError("producer's traversal/Burnside census disagrees")

    literal_positions = [
        position
        for position, record in enumerate(records)
        if position and int(record["signed_mass"]) <= 2
    ]
    literal_keys = [literal_key(records[position]) for position in literal_positions]
    if len(literal_keys) != len(set(literal_keys)):
        raise ValueError("literal low-stratum canonical quotient collision")

    rng = random.Random(0x4_11_2026)
    sample_positions = sorted(
        {len(records) - 1} | {rng.randrange(1, len(records)) for _ in range(64)}
    )
    ir_keys: set[tuple[int, bytes]] = set()
    for position in sample_positions:
        record = records[position]
        matrix = signed_matrix(record)
        key = canonical_signed_matrix(matrix)
        vertices = int(record["active_vertices"])
        permutation = list(range(vertices))
        rng.shuffle(permutation)
        mutant = relabel_record(record, permutation, swap=bool(position & 1))
        if canonical_signed_matrix(signed_matrix(mutant)) != key:
            raise ValueError(f"IR relabel/sign invariance failed at record {position}")
        labelled = (vertices, key)
        if labelled in ir_keys:
            raise ValueError("deterministic IR sample contains a canonical collision")
        ir_keys.add(labelled)

    hostile = copy.deepcopy(records[1])
    hostile["negative_edges"][0] = [0, 0]
    try:
        validate_record(hostile, 1, n)
    except ValueError:
        loop_mutant_rejected = True
    else:
        raise AssertionError("planted loop mutation was accepted")

    output = {
        "schema": "max11-kwa-loopless-signed-degree4-universe-verification-v1",
        "result": "PASS",
        "n": n,
        "branch_edge_occurrences": 4,
        "universe_sha256": sha256_path(args.universe),
        "producer_sha256": sha256_path(args.producer),
        "verifier_sha256": sha256_path(Path(__file__).resolve()),
        "canonical_uncompressed_bytes": len(raw),
        "signed_graph_orbits": len(records),
        "uncoloured_abs_multigraphs": int(census["uncoloured_abs_multigraphs"]),
        "record_stream_hash_replayed": True,
        "all_record_invariants_and_topologies_replayed": True,
        "traversal_equals_burnside_for_every_stratum": True,
        "literal_permutation_records": len(literal_positions),
        "literal_permutation_keys_unique": True,
        "ir_sample_records": len(sample_positions),
        "ir_relabel_and_global_sign_invariance": True,
        "planted_loop_mutation_rejected": loop_mutant_rejected,
        "record_zero_carrier": "4E",
        "external_linear_carrier": "4L",
        "python": sys.version,
        "wall_seconds": time.monotonic() - begun,
        "claim_boundary": (
            "Same-context invariant and independent-canonicalisation checks of the serialized "
            "degree-four signed-graph quotient. Not T2 review, a semantic span result, a "
            "characteristic-zero identity, or an unrestricted MAX11 claim."
        ),
    }
    if args.output.exists():
        raise FileExistsError(f"refusing to overwrite {args.output}")
    args.output.write_bytes(canonical_bytes(output))
    print(f"PASS {args.output} sha256={sha256_path(args.output)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
