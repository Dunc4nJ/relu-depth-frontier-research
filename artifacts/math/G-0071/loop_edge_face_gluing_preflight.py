#!/usr/bin/env python3
"""Bounded exact audit of the G-0071 asymmetric loop--edge lift family.

This program deliberately stops before semantic-column generation, rank work,
or any MAX11 feasibility claim.  It audits the combinatorial construction and
its exposed-face compatibility only.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any, Iterable, Sequence

import pynauty


ROOT = Path(__file__).resolve().parents[3]
N = 11
OLD_N = 10
EXPECTED_BASES = 252
EXPECTED_SEEDS = EXPECTED_BASES * OLD_N * 2

FROZEN_OUTPUTS = {
    "raw_seed_manifest_sha256": "9cf4430a67623e7ba0698cd90cff271f69a30230d6b4d12da400c99b2594b5b9",
    "orbit_count": 3754,
    "orbit_class_manifest_sha256": "aeebb03311dcf7b6862c1444b5eb4df240f0b2dfc544a30d1ca1f6e67200e02a",
    "facet_11_descriptor_stream_sha256": "7e638def14d35a8c2644de237eb2b61145f50e5e6b261bc2a24b4a300fe1c644",
    "codim2_comparison_stream_sha256": "63f0c2d984a23f07249eda6da2d5961ff3c43e020887e2efe13cc38876811b62",
    "codim2_support_witness_stream_sha256": "42b2c93e8e5a669e5a03d7b4e63ef2d89d59aebbc52627bbf3c5f4bddec880bc",
    "orbit_transposition_pairing_sha256": "86271e83e2ec0500ce746a3c2a1a06bbac4d09168ceaea5a27351fda9f34a924",
    "scientific_payload_sha256": "2afdc471e6afdb717e2eb1a5181f43254a424621cc4eb19e49da297d7306e3ef",
}

CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
G0006_SELECTOR = ROOT / "artifacts/math/G-0006/evaluate_minimal_lifts.py"
G0038_CENSUS_SCRIPT = ROOT / "artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py"
G0038_CENSUS_REPORT = ROOT / "artifacts/cleanroom/G-0038/independent_loop_inclusive_census_v1.json"
G0038_MANIFEST = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json"
G0038_STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
G0049_ENGINE = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"

EXPECTED_BINDINGS = {
    "certificate_10_4": (
        CERTIFICATE,
        "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    ),
    "g0006_selector": (
        G0006_SELECTOR,
        "a2ed2e6d8749770fb5a0732ab65f84b592d0562c68947f5ae35676237e1f2862",
    ),
    "g0038_census_script": (
        G0038_CENSUS_SCRIPT,
        "16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb",
    ),
    "g0038_census_report": (
        G0038_CENSUS_REPORT,
        "98469e1cdaaaeac411db16439bbc7f2226b9416ee32d9df1e78f214c2cda0078",
    ),
    "g0038_manifest": (
        G0038_MANIFEST,
        "1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640",
    ),
    "g0038_stream": (
        G0038_STREAM,
        "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    ),
    "g0049_engine": (
        G0049_ENGINE,
        "0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04",
    ),
}

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class AuditError(RuntimeError):
    """A frozen input or exact control failed."""


@dataclass(frozen=True)
class Base:
    term_index: int
    coefficient: str
    left: Side
    right: Side


@dataclass(frozen=True)
class Seed:
    base_term_index: int
    coefficient: str
    anchor: int
    orientation: int
    pair: Pair

    @property
    def key(self) -> tuple[int, int, int]:
        return self.base_term_index, self.anchor, self.orientation


@dataclass(frozen=True)
class FaceState:
    """An ordered exposed-face path, retaining one or two outer branches."""

    labels: tuple[int, ...]
    branches: tuple[Side, ...]

    def geometry_pair(self) -> Pair:
        if len(self.branches) == 1:
            return self.branches[0], self.branches[0]
        if len(self.branches) == 2:
            return canonical_pair((self.branches[0], self.branches[1]))
        raise AuditError("face state must retain one or two branches")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise AuditError(f"not a regular frozen input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def verify_bindings() -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for name, (path, expected) in EXPECTED_BINDINGS.items():
        observed = sha256_path(path)
        if observed != expected:
            raise AuditError(f"binding mismatch for {name}: {observed} != {expected}")
        output[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    module_path = Path(pynauty.__file__).resolve()
    output["pynauty"] = {
        "path": str(module_path),
        "sha256": sha256_path(module_path),
        "version": getattr(pynauty, "__version__", "unknown"),
    }
    return output


def load_module(path: Path, name: str) -> Any:
    specification = importlib.util.spec_from_file_location(name, path)
    if specification is None or specification.loader is None:
        raise AuditError(f"could not load frozen module {path}")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


def edge(raw: Sequence[int]) -> Edge:
    if len(raw) != 2 or any(type(value) is not int for value in raw):
        raise AuditError(f"malformed edge: {raw!r}")
    a, b = sorted((int(raw[0]), int(raw[1])))
    if not (1 <= a <= b <= OLD_N):
        raise AuditError(f"MAX10 edge outside 1..10: {(a, b)}")
    return a, b


def canonical_side(side: Iterable[Edge]) -> Side:
    return tuple(sorted((min(a, b), max(a, b)) for a, b in side))


def canonical_pair(pair: Pair) -> Pair:
    first, second = canonical_side(pair[0]), canonical_side(pair[1])
    return (first, second) if first <= second else (second, first)


def serialize_side(side: Side) -> list[list[int]]:
    return [[a, b] for a, b in side]


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [serialize_side(side) for side in pair]


def two_component_full_support(left: Side, right: Side) -> bool:
    all_edges = left + right
    if any(a == b for a, b in all_edges) or len(set(all_edges)) != 8:
        return False
    vertices = {vertex for item in all_edges for vertex in item}
    if vertices != set(range(1, OLD_N + 1)):
        return False
    parent = {vertex: vertex for vertex in vertices}

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for a, b in all_edges:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a
    return len({find(vertex) for vertex in vertices}) == 2


def load_bases() -> tuple[list[Base], dict[str, object]]:
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    if document.get("n") != OLD_N or not isinstance(document.get("terms"), list):
        raise AuditError("malformed pinned MAX10 certificate")
    bases: list[Base] = []
    for term_index, term in enumerate(document["terms"]):
        raw_pair = term.get("pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise AuditError(f"malformed certificate pair at term {term_index}")
        left = canonical_side(edge(item) for item in raw_pair[0])
        right = canonical_side(edge(item) for item in raw_pair[1])
        if len(left) != 4 or len(right) != 4:
            raise AuditError(f"wrong branch mass at term {term_index}")
        if two_component_full_support(left, right):
            bases.append(Base(term_index, str(term["coefficient"]), left, right))
    if len(bases) != EXPECTED_BASES:
        raise AuditError(f"base selector returned {len(bases)}, expected {EXPECTED_BASES}")

    # Exact cross-check against the hash-bound G-0006 selector.  This calls
    # build_bases only; no semantic matrix or rank subject is constructed.
    frozen = load_module(G0006_SELECTOR, "g0071_frozen_g0006_selector")
    frozen_bases, frozen_metadata, frozen_metadata_sha256 = frozen.build_bases()
    frozen_descriptors = [
        (int(term_index), canonical_side(left), canonical_side(right))
        for term_index, left, right, _components in frozen_bases
    ]
    local_descriptors = [(base.term_index, base.left, base.right) for base in bases]
    if local_descriptors != frozen_descriptors:
        raise AuditError("independent base selector disagrees with frozen G-0006")
    return bases, {
        "base_count": len(bases),
        "base_descriptors_sha256": canonical_sha256(
            [
                {
                    "term_index": base.term_index,
                    "coefficient": base.coefficient,
                    "pair": serialize_pair((base.left, base.right)),
                }
                for base in bases
            ]
        ),
        "g0006_candidate_metadata_count": len(frozen_metadata),
        "g0006_candidate_metadata_sha256": frozen_metadata_sha256,
    }


def enumerate_seeds(bases: Sequence[Base]) -> list[Seed]:
    seeds: list[Seed] = []
    for base in bases:
        for anchor in range(1, OLD_N + 1):
            loop = (anchor, anchor)
            spoke = (anchor, N)
            seeds.append(
                Seed(
                    base.term_index,
                    base.coefficient,
                    anchor,
                    0,
                    (canonical_side(base.left + (loop,)), canonical_side(base.right + (spoke,))),
                )
            )
            seeds.append(
                Seed(
                    base.term_index,
                    base.coefficient,
                    anchor,
                    1,
                    (canonical_side(base.left + (spoke,)), canonical_side(base.right + (loop,))),
                )
            )
    if len(seeds) != EXPECTED_SEEDS or len({seed.key for seed in seeds}) != EXPECTED_SEEDS:
        raise AuditError("seed enumeration is not exactly 252*10*2")
    return seeds


def seed_record(seed: Seed) -> dict[str, object]:
    return {
        "base_term_index": seed.base_term_index,
        "coefficient": seed.coefficient,
        "anchor": seed.anchor,
        "orientation": seed.orientation,
        "pair": serialize_pair(seed.pair),
    }


def seed_manifest_sha256(seeds: Sequence[Seed]) -> str:
    return canonical_sha256([seed_record(seed) for seed in sorted(seeds, key=lambda item: item.key)])


def signed_exact_label_key(pair: Pair, n: int = N) -> tuple[int, ...]:
    matrix = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_a, one_b in side:
            a, b = one_a - 1, one_b - 1
            if not (0 <= a <= b < n):
                raise AuditError("edge outside signed-key dimension")
            matrix[a][b] += sign
            if a != b:
                matrix[b][a] += sign
    flat = tuple(value for row in matrix for value in row)
    return min(flat, tuple(-value for value in flat))


def orbit_certificate(pair: Pair, n: int = N) -> bytes:
    """Exact coordinate-relabeling/global-branch-swap certificate via nauty.

    Vertex, branch, and edge-occurrence nodes form three colour classes.
    Edge occurrences retain multiplicity; a loop occurrence has one vertex
    neighbour while a nonloop occurrence has two.
    """

    if len(pair) != 2 or len(pair[0]) != len(pair[1]):
        raise AuditError("orbit pair must have two equal-mass branches")
    mass = len(pair[0])
    vertex_start = 0
    branch_start = n
    occurrence_start = n + 2
    number_of_vertices = n + 2 + 2 * mass
    adjacency = {index: set() for index in range(number_of_vertices)}

    def connect(first: int, second: int) -> None:
        adjacency[first].add(second)
        adjacency[second].add(first)

    occurrence = occurrence_start
    for branch, side in enumerate(pair):
        branch_node = branch_start + branch
        for a, b in side:
            if not (1 <= a <= b <= n):
                raise AuditError("orbit edge outside ambient labels")
            connect(occurrence, branch_node)
            connect(occurrence, vertex_start + a - 1)
            if a != b:
                connect(occurrence, vertex_start + b - 1)
            occurrence += 1
    graph = pynauty.Graph(
        number_of_vertices=number_of_vertices,
        directed=False,
        adjacency_dict={node: sorted(neighbours) for node, neighbours in adjacency.items()},
        vertex_coloring=[
            set(range(vertex_start, branch_start)),
            set(range(branch_start, occurrence_start)),
            set(range(occurrence_start, number_of_vertices)),
        ],
    )
    return pynauty.certificate(graph)


def relabel_pair(pair: Pair, permutation: dict[int, int]) -> Pair:
    return tuple(
        canonical_side(
            (min(permutation[a], permutation[b]), max(permutation[a], permutation[b]))
            for a, b in side
        )
        for side in pair
    )  # type: ignore[return-value]


def project_edge(item: Edge, deleted: frozenset[int]) -> Edge | None:
    a, b = item
    kept = [vertex for vertex in (a, b) if vertex not in deleted]
    if not kept:
        return None
    if len(kept) == 1:
        return kept[0], kept[0]
    return min(kept), max(kept)


def project_side(side: Side, deleted: frozenset[int]) -> Side:
    return canonical_side(
        projected
        for item in side
        if (projected := project_edge(item, deleted)) is not None
    )


def deleted_support_numerator(side: Side, deleted: frozenset[int], ambient_n: int) -> int:
    """N times support in direction |D|*mu-sum_{i in D}e_i."""

    internal = sum(a in deleted and b in deleted for a, b in side)
    return len(side) * len(deleted) - ambient_n * internal


def explicit_deleted_support_numerator(
    side: Side, deleted: frozenset[int], ambient_n: int
) -> int:
    size = len(deleted)
    return sum(
        max(size - ambient_n * int(a in deleted), size - ambient_n * int(b in deleted))
        for a, b in side
    )


def direct_deleted_face(pair: Pair, deleted: frozenset[int], ambient_n: int = N) -> FaceState:
    if not deleted or any(not 1 <= label <= ambient_n for label in deleted):
        raise AuditError("deleted set must be a nonempty subset of ambient labels")
    heights = tuple(deleted_support_numerator(side, deleted, ambient_n) for side in pair)
    projected = tuple(project_side(side, deleted) for side in pair)
    if heights[0] == heights[1]:
        branches = tuple(sorted(projected))
    else:
        winner = 0 if heights[0] > heights[1] else 1
        branches = (projected[winner],)
    labels = tuple(label for label in range(1, ambient_n + 1) if label not in deleted)
    return FaceState(labels, branches)


def local_support_numerator(side: Side, deleted_label: int, ambient_size: int) -> int:
    """ambient_size times support in the current simplex facet normal."""

    return len(side) - ambient_size * sum(a == deleted_label and b == deleted_label for a, b in side)


def restrict_step(state: FaceState, deleted_label: int) -> tuple[FaceState, dict[str, object]]:
    if deleted_label not in state.labels:
        raise AuditError(f"label {deleted_label} is not available in face state")
    ambient_size = len(state.labels)
    heights = tuple(
        local_support_numerator(side, deleted_label, ambient_size) for side in state.branches
    )
    maximum = max(heights)
    winners = tuple(index for index, height in enumerate(heights) if height == maximum)
    projected = tuple(project_side(state.branches[index], frozenset({deleted_label})) for index in winners)
    next_state = FaceState(
        tuple(label for label in state.labels if label != deleted_label),
        tuple(sorted(projected)),
    )
    trace = {
        "deleted": deleted_label,
        "ambient_size": ambient_size,
        "support_numerators": list(heights),
        "retained_branches": len(next_state.branches),
    }
    return next_state, trace


def restrict_path(pair: Pair, path: Sequence[int]) -> tuple[FaceState, list[dict[str, object]]]:
    state = FaceState(tuple(range(1, N + 1)), tuple(sorted(pair)))
    trace: list[dict[str, object]] = []
    for label in path:
        state, step = restrict_step(state, label)
        trace.append(step)
    return state, trace


def side_support(side: Side, direction: dict[int, int]) -> int:
    return sum(max(direction.get(a, 0), direction.get(b, 0)) for a, b in side)


def block_support(pair: Pair, direction: dict[int, int]) -> int:
    return max(side_support(pair[0], direction), side_support(pair[1], direction))


def first_support_witness(
    first: Pair, second: Pair, labels: tuple[int, ...]
) -> dict[str, object] | None:
    candidates: list[dict[int, int]] = []
    for label in labels:
        candidates.append({label: 1})
        candidates.append({label: -1})
    for first_label in labels:
        for second_label in labels:
            if first_label != second_label:
                candidates.append({first_label: 1, second_label: -1})
    # Binary cuts are a strong exact witness family, but absence of a witness
    # is not promoted to equality.
    for mask in range(1, (1 << len(labels)) - 1):
        candidates.append(
            {label: 1 for index, label in enumerate(labels) if mask & (1 << index)}
        )
    seen: set[tuple[tuple[int, int], ...]] = set()
    for direction in candidates:
        key = tuple(sorted(direction.items()))
        if key in seen:
            continue
        seen.add(key)
        first_value = block_support(first, direction)
        second_value = block_support(second, direction)
        if first_value != second_value:
            return {
                "direction": [[label, value] for label, value in key],
                "first_support": first_value,
                "second_support": second_value,
            }
    return None


def facet_11_audit(seeds: Sequence[Seed], bases_by_term: dict[int, Base]) -> dict[str, object]:
    digest = hashlib.sha256()
    tied = 0
    for seed in seeds:
        base = bases_by_term[seed.base_term_index]
        state, trace = restrict_path(seed.pair, (N,))
        expected = canonical_pair(
            (
                canonical_side(base.left + ((seed.anchor, seed.anchor),)),
                canonical_side(base.right + ((seed.anchor, seed.anchor),)),
            )
        )
        if len(state.branches) != 2 or state.geometry_pair() != expected:
            raise AuditError(f"facet-11 loop--edge lift identity failed at seed {seed.key}")
        tied += 1
        digest.update(
            canonical_bytes(
                {
                    "seed": list(seed.key),
                    "trace": trace,
                    "restricted_pair": serialize_pair(state.geometry_pair()),
                }
            )
        )
    return {
        "checks": len(seeds),
        "tied_outer_faces": tied,
        "strict_outer_faces": 0,
        "identity": "F_11(loop(k,k))=F_11(edge(k,11))=point(e_k)",
        "restricted_descriptor_stream_sha256": digest.hexdigest(),
    }


def relation_name(seed: Seed, deleted: frozenset[int]) -> str:
    if deleted == frozenset({seed.anchor, N}):
        return "anchor_and_new_vertex"
    if seed.anchor in deleted:
        return "anchor_and_other_old_vertex"
    if N in deleted:
        return "new_vertex_and_other_old_vertex"
    return "two_nonanchor_old_vertices"


def codimension_two_audit(seeds: Sequence[Seed]) -> dict[str, object]:
    total = 0
    projection_checks = 0
    representation_commuting = 0
    direct_status = Counter()
    path_status = Counter()
    mismatches_by_relation = Counter()
    mismatches_by_deleted_pair = Counter()
    path_first_matches_direct = 0
    path_second_matches_direct = 0
    witnessed_geometric_mismatches = 0
    unwitnessed_representation_mismatches = 0
    orbit_transposition_checks = 0
    witness_cache: dict[tuple[Pair, Pair, tuple[int, ...]], dict[str, object] | None] = {}
    examples: list[dict[str, object]] = []
    stream = hashlib.sha256()
    witness_stream = hashlib.sha256()
    orbit_involution_stream = hashlib.sha256()

    for seed in seeds:
        for first in range(1, N + 1):
            for second in range(first + 1, N + 1):
                deleted = frozenset({first, second})
                for side in seed.pair:
                    direct_projection = project_side(side, deleted)
                    first_then_second = project_side(
                        project_side(side, frozenset({first})), frozenset({second})
                    )
                    second_then_first = project_side(
                        project_side(side, frozenset({second})), frozenset({first})
                    )
                    if not (direct_projection == first_then_second == second_then_first):
                        raise AuditError("generator projection failed codimension-two commutation")
                    if deleted_support_numerator(side, deleted, N) != explicit_deleted_support_numerator(
                        side, deleted, N
                    ):
                        raise AuditError("deleted-set support formula disagrees with endpoint maximum")
                    projection_checks += 1

                direct = direct_deleted_face(seed.pair, deleted)
                path_12, trace_12 = restrict_path(seed.pair, (first, second))
                path_21, trace_21 = restrict_path(seed.pair, (second, first))

                # In a full S_11 orbit sum, the coordinate transposition
                # (first second) pairs every ordered-face residual with its
                # negative.  Verify the involution at the exact descriptor
                # level; this is distinct from raw-seed commutation.
                transposition = {label: label for label in range(1, N + 1)}
                transposition[first], transposition[second] = second, first
                transposed_pair = relabel_pair(seed.pair, transposition)
                transposed_12, _ = restrict_path(transposed_pair, (first, second))
                transposed_21, _ = restrict_path(transposed_pair, (second, first))
                if (
                    path_12.geometry_pair() != transposed_21.geometry_pair()
                    or path_21.geometry_pair() != transposed_12.geometry_pair()
                ):
                    raise AuditError("coordinate-transposition orbit involution failed")
                orbit_transposition_checks += 1
                orbit_involution_stream.update(
                    canonical_bytes(
                        {
                            "seed": list(seed.key),
                            "deleted": [first, second],
                            "path_12_sha256": canonical_sha256(
                                serialize_pair(path_12.geometry_pair())
                            ),
                            "path_21_sha256": canonical_sha256(
                                serialize_pair(path_21.geometry_pair())
                            ),
                        }
                    )
                )
                direct_pair = direct.geometry_pair()
                pair_12 = path_12.geometry_pair()
                pair_21 = path_21.geometry_pair()
                direct_status["tied" if len(direct.branches) == 2 else "strict"] += 1
                path_status[f"{len(path_12.branches)}->{len(path_21.branches)}"] += 1
                path_first_matches_direct += int(pair_12 == direct_pair)
                path_second_matches_direct += int(pair_21 == direct_pair)
                commute = pair_12 == pair_21
                representation_commuting += int(commute)
                total += 1

                record: dict[str, object] = {
                    "seed": list(seed.key),
                    "deleted": [first, second],
                    "commutes": commute,
                    "path_branch_counts": [len(path_12.branches), len(path_21.branches)],
                    "direct_branch_count": len(direct.branches),
                }
                if not commute:
                    relation = relation_name(seed, deleted)
                    mismatches_by_relation[relation] += 1
                    mismatches_by_deleted_pair[f"{first},{second}"] += 1
                    ordered_pair = (pair_12, pair_21) if pair_12 <= pair_21 else (pair_21, pair_12)
                    cache_key = (ordered_pair[0], ordered_pair[1], path_12.labels)
                    if cache_key not in witness_cache:
                        witness_cache[cache_key] = first_support_witness(
                            ordered_pair[0], ordered_pair[1], path_12.labels
                        )
                    witness = witness_cache[cache_key]
                    if witness is None:
                        unwitnessed_representation_mismatches += 1
                    else:
                        witnessed_geometric_mismatches += 1
                    witness_stream.update(
                        canonical_bytes(
                            {
                                "seed": list(seed.key),
                                "deleted": [first, second],
                                "witness": witness,
                            }
                        )
                    )
                    record["relation"] = relation
                    record["support_witness_found"] = witness is not None
                    if len(examples) < 12:
                        examples.append(
                            {
                                **record,
                                "path_first_second": {
                                    "trace": trace_12,
                                    "pair": serialize_pair(pair_12),
                                },
                                "path_second_first": {
                                    "trace": trace_21,
                                    "pair": serialize_pair(pair_21),
                                },
                                "direct_equal_weight_face": serialize_pair(direct_pair),
                                "support_witness": witness,
                            }
                        )
                stream.update(canonical_bytes(record))

    expected_total = len(seeds) * (N * (N - 1) // 2)
    if total != expected_total or projection_checks != 2 * expected_total:
        raise AuditError("codimension-two census was incomplete")
    if orbit_transposition_checks != expected_total:
        raise AuditError("coordinate-transposition orbit audit was incomplete")
    return {
        "unordered_deleted_sets_checked": total,
        "generator_projection_checks": projection_checks,
        "generator_projection_commuting": projection_checks,
        "outer_face_representation_commuting": representation_commuting,
        "outer_face_representation_noncommuting": total - representation_commuting,
        "noncommuting_with_exact_support_witness": witnessed_geometric_mismatches,
        "noncommuting_without_witness_in_frozen_direction_family": unwitnessed_representation_mismatches,
        "support_witness_stream_sha256": witness_stream.hexdigest(),
        "mismatches_by_relation": dict(sorted(mismatches_by_relation.items())),
        "mismatches_by_deleted_pair": dict(sorted(mismatches_by_deleted_pair.items())),
        "direct_equal_weight_status": dict(sorted(direct_status.items())),
        "ordered_path_terminal_branch_counts": dict(sorted(path_status.items())),
        "first_then_second_matches_direct_descriptor": path_first_matches_direct,
        "second_then_first_matches_direct_descriptor": path_second_matches_direct,
        "comparison_stream_sha256": stream.hexdigest(),
        "full_s11_orbit_transposition_involution": {
            "checks": orbit_transposition_checks,
            "descriptor_pairing_sha256": orbit_involution_stream.hexdigest(),
            "ordered_face_residual": "EXACT_ZERO_PER_ORBIT",
            "weighted_252_term_residual": (
                "EXACT_ZERO_FOR_ANY_COEFFICIENTS_IF_EACH_SEED_IS FULLY_S11_ORBIT_SUMMED"
            ),
            "reason": (
                "the transposition of the two deleted coordinates exchanges the two ordered "
                "face paths and fixes every surviving coordinate"
            ),
        },
        "examples": examples,
        "interpretation_boundary": (
            "Descriptor inequality is an exact representation-level mismatch. A listed support "
            "witness additionally proves geometric inequality. Failure to find a witness in the "
            "frozen finite direction family is not evidence of equality."
        ),
    }


def singleton_deleted_set_census(seeds: Sequence[Seed]) -> dict[str, object]:
    status = Counter()
    by_label = Counter()
    checks = 0
    for seed in seeds:
        for label in range(1, N + 1):
            deleted = frozenset({label})
            for side in seed.pair:
                if deleted_support_numerator(side, deleted, N) != explicit_deleted_support_numerator(
                    side, deleted, N
                ):
                    raise AuditError("singleton support formula failed")
            face = direct_deleted_face(seed.pair, deleted)
            name = "tied" if len(face.branches) == 2 else "strict"
            status[name] += 1
            by_label[f"{label}:{name}"] += 1
            checks += 1
    return {
        "checks": checks,
        "status": dict(sorted(status.items())),
        "by_label_and_status": dict(sorted(by_label.items())),
    }


def orbit_audit(seeds: Sequence[Seed]) -> dict[str, object]:
    g0049 = load_module(G0049_ENGINE, "g0071_frozen_g0049_engine")
    orbit_counts: Counter[str] = Counter()
    orbit_sequence: list[str] = []
    signed_keys: list[tuple[int, ...]] = []
    unordered_descriptors: list[Pair] = []
    for seed in seeds:
        local_key = signed_exact_label_key(seed.pair)
        frozen_key = tuple(g0049.signed_cache_key(seed.pair, N))
        if local_key != frozen_key:
            raise AuditError(f"G-0049 signed-key cross-check failed at seed {seed.key}")
        signed_keys.append(local_key)
        unordered_descriptors.append(canonical_pair(seed.pair))
        descriptor = hashlib.sha256(orbit_certificate(seed.pair)).hexdigest()
        orbit_sequence.append(descriptor)
        orbit_counts[descriptor] += 1
    class_manifest = [
        {"orbit_certificate_sha256": descriptor, "raw_seed_count": count}
        for descriptor, count in sorted(orbit_counts.items())
    ]
    return {
        "raw_seeds": len(seeds),
        "coordinate_relabeling_global_branch_swap_orbits": len(orbit_counts),
        "orbit_class_size_histogram": dict(sorted(Counter(orbit_counts.values()).items())),
        "orbit_sequence_sha256": canonical_sha256(orbit_sequence),
        "orbit_class_manifest_sha256": canonical_sha256(class_manifest),
        "exact_label_unordered_descriptor_sha256": canonical_sha256(
            [serialize_pair(pair) for pair in unordered_descriptors]
        ),
        "g0049_signed_exact_label_key_sha256": canonical_sha256(signed_keys),
        "authority": (
            "pynauty canonical certificate of a three-colour vertex/branch/occurrence "
            "incidence graph; G-0049 exact-labelled signed keys cross-checked independently"
        ),
    }


def replace_spoke_with_new_loop(pair: Pair) -> Pair:
    output: list[Side] = []
    replaced = False
    for side in pair:
        items: list[Edge] = []
        for item in side:
            if not replaced and item[1] == N and item[0] != N:
                items.append((N, N))
                replaced = True
            else:
                items.append(item)
        output.append(canonical_side(items))
    if not replaced:
        raise AuditError("hostile orbit fixture had no spoke")
    return output[0], output[1]


def hostile_controls(seeds: Sequence[Seed], bases_by_term: dict[int, Base]) -> dict[str, object]:
    seed = seeds[0]
    base = bases_by_term[seed.base_term_index]
    correct, _trace = restrict_path(seed.pair, (N,))
    expected = canonical_pair(
        (
            canonical_side(base.left + ((seed.anchor, seed.anchor),)),
            canonical_side(base.right + ((seed.anchor, seed.anchor),)),
        )
    )

    # Mutant 1: delete an entire incident segment rather than retaining its
    # old endpoint as a point.  This destroys the facet-11 carrier identity.
    def drop_incident(side: Side) -> Side:
        return canonical_side(item for item in side if N not in item)

    incident_drop_mutant = canonical_pair((drop_incident(seed.pair[0]), drop_incident(seed.pair[1])))
    if incident_drop_mutant == expected:
        raise AuditError("incident-edge deletion mutant escaped")

    # Mutant 2: use >= as a strict choice and discard the second branch on a
    # support tie.  The first seed has distinct restricted branches.
    tie_discard_mutant = canonical_pair((correct.branches[0], correct.branches[0]))
    if tie_discard_mutant == expected:
        raise AuditError("tie-as-strict mutant escaped")

    # A planted strict branch: the deleted loop loses one full unit of support,
    # whereas the incident segment exposes its retained endpoint.
    strict_fixture: Pair = (((N, N),), ((1, N),))
    strict_face = direct_deleted_face(strict_fixture, frozenset({N}))
    if len(strict_face.branches) != 1 or strict_face.branches[0] != ((1, 1),):
        raise AuditError("planted strict-branch fixture failed")

    # Mutant 3: a segment whose two endpoints are deleted must become zero.
    # Retaining either endpoint as a loop is caught directly.
    codim_fixture: Side = ((1, 2),)
    if project_side(codim_fixture, frozenset({1, 2})) != ():
        raise AuditError("deleted-deleted segment did not vanish")
    deleted_deleted_mutant = ((1, 1),)
    if deleted_deleted_mutant == project_side(codim_fixture, frozenset({1, 2})):
        raise AuditError("deleted-deleted mutant escaped")

    # Nauty certificate invariances and a loop-count-changing hostile mutant.
    certificate = orbit_certificate(seed.pair)
    cyclic = {label: (label % N) + 1 for label in range(1, N + 1)}
    if orbit_certificate(relabel_pair(seed.pair, cyclic)) != certificate:
        raise AuditError("orbit certificate is not coordinate-relabeling invariant")
    if orbit_certificate((seed.pair[1], seed.pair[0])) != certificate:
        raise AuditError("orbit certificate is not branch-swap invariant")
    if orbit_certificate(replace_spoke_with_new_loop(seed.pair)) == certificate:
        raise AuditError("loop-count-changing orbit mutant escaped")

    # Enumeration framing must be stable under input order and sensitive to a
    # missing seed.
    manifest = seed_manifest_sha256(seeds)
    if seed_manifest_sha256(tuple(reversed(seeds))) != manifest:
        raise AuditError("sorted seed manifest depends on enumeration order")
    if seed_manifest_sha256(seeds[:-1]) == manifest:
        raise AuditError("missing-seed manifest mutant escaped")

    return {
        "incident_edge_deleted_instead_of_point_rejected": True,
        "tie_treated_as_strict_rejected": True,
        "planted_strict_branch_selected_correctly": True,
        "deleted_deleted_segment_retained_as_loop_rejected": True,
        "orbit_coordinate_relabeling_invariant": True,
        "orbit_global_branch_swap_invariant": True,
        "orbit_loop_count_mutant_rejected": True,
        "seed_order_invariance": True,
        "missing_seed_mutant_rejected": True,
    }


def analyze(mode: str) -> dict[str, object]:
    bindings = verify_bindings()
    bases, base_report = load_bases()
    seeds = enumerate_seeds(bases)
    bases_by_term = {base.term_index: base for base in bases}
    manifest = seed_manifest_sha256(seeds)
    if manifest != seed_manifest_sha256(enumerate_seeds(bases)):
        raise AuditError("repeat enumeration changed the seed manifest")

    orbit_report = orbit_audit(seeds)
    facet_report = facet_11_audit(seeds, bases_by_term)
    codim2_report = codimension_two_audit(seeds)
    observed_frozen = {
        "raw_seed_manifest_sha256": manifest,
        "orbit_count": orbit_report["coordinate_relabeling_global_branch_swap_orbits"],
        "orbit_class_manifest_sha256": orbit_report["orbit_class_manifest_sha256"],
        "facet_11_descriptor_stream_sha256": facet_report[
            "restricted_descriptor_stream_sha256"
        ],
        "codim2_comparison_stream_sha256": codim2_report["comparison_stream_sha256"],
        "codim2_support_witness_stream_sha256": codim2_report[
            "support_witness_stream_sha256"
        ],
        "orbit_transposition_pairing_sha256": codim2_report[
            "full_s11_orbit_transposition_involution"
        ]["descriptor_pairing_sha256"],
    }
    for name, observed in observed_frozen.items():
        if observed != FROZEN_OUTPUTS[name]:
            raise AuditError(f"frozen output mismatch for {name}: {observed}")

    report: dict[str, object] = {
        "schema": "max11-g0071-loop-edge-face-gluing-preflight-v1",
        "mode": mode,
        "result": "BOUNDED_STRUCTURAL_AUDIT_COMPLETE",
        "bindings": bindings,
        "base_selection": base_report,
        "family": {
            "definition": (
                "for each pinned base (A,B), anchor k, and orientation, put loop(k,k) "
                "on one branch and edge(k,11) on the other"
            ),
            "expected_arithmetic": "252*10*2=5040",
            "raw_seed_count": len(seeds),
            "raw_seed_manifest_sha256": manifest,
        },
        "orbit_descriptors": orbit_report,
        "facet_11": facet_report,
        "singleton_deleted_sets": singleton_deleted_set_census(seeds),
        "codimension_two": codim2_report,
        "hostile_controls": hostile_controls(seeds, bases_by_term),
        "claim_boundary": (
            "No semantic column, rank subject, coefficient solve, network compilation, "
            "MAX11 feasibility result, or unrestricted lower bound is constructed here."
        ),
    }
    payload = dict(report)
    payload.pop("mode")
    report["scientific_payload_sha256"] = canonical_sha256(payload)
    if report["scientific_payload_sha256"] != FROZEN_OUTPUTS["scientific_payload_sha256"]:
        raise AuditError(
            "frozen output mismatch for scientific_payload_sha256: "
            f"{report['scientific_payload_sha256']}"
        )
    return report


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    mode = "self-test" if arguments.self_test else "preflight-only"
    print(json.dumps(analyze(mode), sort_keys=True))


if __name__ == "__main__":
    main()
