#!/usr/bin/env python3
"""Outcome-blind clean-room verifier for the frozen G-0079 price receipt.

This verifier deliberately does not import or execute the G-0079 producer,
the G-0079 preflight producer, or the G-0073/G-0074/G-0075 producers.  It
parses the frozen MAX10 certificate directly, reconstructs the same-component
family with an independently written NetworkX-VF2 orbit classifier, uses
pynauty only to recover the pinned orbit ordering, and evaluates the original
nested-max expression rather than the producer's flattened identity.

The default self-test is synthetic and evaluates zero registered columns.  A
registered receipt can be opened only with the explicit outcome-read token;
this makes accidental pre-release inspection fail closed.

No-claim boundary: CONSISTENT means that this independent implementation
replayed the finite exact price receipt.  A nonzero price vector proves
neither membership nor nonmembership.  An all-zero vector is at most support
for the frozen 26,689-column/16,738-row bounded separator, and is not a global
CPWL identity theorem or an unrestricted ReLU-network lower bound.  This
verifier does not independently replay all 8,107 old columns.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache
import gzip
import hashlib
from itertools import combinations
import json
import math
import os
from pathlib import Path
import sys
from typing import Iterable, Sequence

import networkx as nx
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

RUNNER = ROOT / "artifacts/math/G-0079/same_component_y_spoke_cegis.py"
PREREGISTRATION = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_preregistration_v2.json"
)
REGISTERED_RECEIPT = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_prices_v2.json.gz"
)
CLEANROOM_RECEIPT = ROOT / "artifacts/cleanroom/G-0079/g0079_price_replay_v2.json.gz"
PREFLIGHT_SOURCE = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_closure.py"
)
PREFLIGHT_RECEIPT = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_preflight_v1.json.gz"
)
G0073_SOURCE = ROOT / "artifacts/math/G-0073/y_spoke_profile_gate.py"
G0074_SOURCE = ROOT / "artifacts/math/G-0074/farey_three_level_gate.py"
G0075_SOURCE = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate.py"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
G0078_EXACT = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz"
FULL_OLD_MATRIX = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"
MAX10_CERTIFICATE = (
    ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
)

SCHEMA_PRICE = "max11-g0079-complete-exact-price-vector-v2"
SCHEMA_PREREGISTRATION = "max11-g0079-preregistration-v2"
OUTCOME_READ_TOKEN = "G0079_PRICE_RECEIPT_RELEASED"

N = 11
OLD_N = 10
BASE_COUNT = 252
RAW_SEED_COUNT = 26_960
NEW_COLUMN_COUNT = 18_582
OLD_COLUMN_COUNT = 8_107
COMBINED_COLUMN_COUNT = 26_689
GLOBAL_NEW_START = 8_107
GLOBAL_NEW_STOP = 26_688
GLOBAL_TARGET_ID = 26_689
TOTAL_ROWS = 16_738
SUPPORT_ROWS = 230
PRIME = 1_000_003
PANEL_COUNT = 128
PANEL_DENOMINATOR = 257
PANEL_SEED = "max11-g0075-genuinely-four-valued-panels-v1"
EVALUATION_BATCH_SIZE = 24
SCALAR_REPLAY_CHECKS = 64

FAREY_F6 = (
    (0, 1),
    (1, 6),
    (1, 5),
    (1, 4),
    (1, 3),
    (2, 5),
    (1, 2),
    (3, 5),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (1, 1),
)

EXPECTED_HASHES = {
    "runner": "7539515641c241a28be45cea88445bd4f598f7c0693ab521c31805530c9f67da",
    "preregistration": "c3da38c06f6d8b9b5ab9e89322f50ca9c797ea5bcfe5c9ea4dc8d618464e5b05",
    "preflight_source": "3b4626f36c8c505274b108b3cd80a17127de6e911c16962cbdbcff557a22b5da",
    "preflight_receipt": "12ea9a384a064c4cd9e17e37688384f4241b2fbe85cea501b892ad1ab2b4fd91",
    "g0073_source": "333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67",
    "g0074_source": "269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d",
    "g0075_source": "ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab",
    "g0077_modular": "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4",
    "g0078_exact": "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96",
    "full_old_matrix": "5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f",
    "environment_manifest": "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c",
    "max10_certificate": "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
}

EXPECTED_PREFLIGHT_SCIENCE = (
    "2774dfa1b49de1e661633c3176e091519b25f479a68041cc2d08887ada38f73b"
)
EXPECTED_G0078_SCIENCE = (
    "0bb1a524503359529bb592030f220be86d88756b797e55c4be04c031852bd573"
)
EXPECTED_ORBIT_MANIFEST = (
    "412fb195a6017d2e5c55a42726514e27e210bee52fd8df555d5804fc06f5f58c"
)
EXPECTED_REPRESENTATIVE_MANIFEST = (
    "b5782585f158ff81ef8e2778c8ac24b7da0cc3e180de66bac496bff1a54f6d02"
)

RESULT_ALL_ZERO = "EXACT_BOUNDED_NONMEMBERSHIP_CANDIDATE_COMPLETE_FROZEN_DICTIONARY"
RESULT_NONZERO = "EXACT_PRICE_SEED_CONTINUE_WITH_FULL_DICTIONARY"


class VerificationError(RuntimeError):
    """A binding, reconstruction, semantic, receipt, or claim invariant failed."""


Edge = tuple[int, int]
Side = tuple[Edge, ...]


@dataclass(frozen=True)
class Base:
    position: int
    term_index: int
    left: Side
    right: Side
    components: tuple[tuple[int, ...], tuple[int, ...]]


@dataclass(frozen=True)
class Expression:
    left: Side
    right: Side
    anchor: int
    auxiliary: int
    new_label: int
    orientation: int


@dataclass(frozen=True)
class Seed:
    raw_index: int
    base_position: int
    base_term_index: int
    expression: Expression


@dataclass(frozen=True)
class OrbitReconstruction:
    representatives: tuple[Seed, ...]
    class_sizes: tuple[int, ...]
    certificate_sha256s: tuple[str, ...]
    orbit_manifest_sha256: str
    representative_manifest_sha256: str
    vf2_nonrepresentative_checks: int


@dataclass(frozen=True)
class ExactFunctional:
    rows: tuple[int, ...]
    weights: tuple[int, ...]
    denominator_lcm: int
    global_gcd: int
    expected_target: int
    g0078_scientific_payload_sha256: str


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def read_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"not a regular JSON file: {path}")
    with path.open("rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise VerificationError(f"JSON root is not an object: {path}")
    return document


def read_gzip_json(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"not a regular gzip JSON file: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise VerificationError(f"gzip JSON root is not an object: {path}")
    return document


def write_gzip_exclusive(path: Path, document: object) -> None:
    if path.resolve(strict=False) != CLEANROOM_RECEIPT.resolve(strict=False):
        raise VerificationError("clean-room output path differs from the frozen v2 path")
    if path.exists() or path.is_symlink():
        raise VerificationError(f"refusing to overwrite clean-room receipt: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                zipped.write(canonical_bytes(document))
            raw.flush()
            os.fsync(raw.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def binding_paths() -> dict[str, Path]:
    return {
        "runner": RUNNER,
        "preregistration": PREREGISTRATION,
        "preflight_source": PREFLIGHT_SOURCE,
        "preflight_receipt": PREFLIGHT_RECEIPT,
        "g0073_source": G0073_SOURCE,
        "g0074_source": G0074_SOURCE,
        "g0075_source": G0075_SOURCE,
        "g0077_modular": G0077_MODULAR,
        "g0078_exact": G0078_EXACT,
        "full_old_matrix": FULL_OLD_MATRIX,
        "environment_manifest": ENVIRONMENT_MANIFEST,
        "max10_certificate": MAX10_CERTIFICATE,
    }


def replay_bindings() -> dict[str, str]:
    observed = {label: sha256_path(path) for label, path in binding_paths().items()}
    if observed != EXPECTED_HASHES:
        failures = {
            label: {"expected": EXPECTED_HASHES[label], "observed": digest}
            for label, digest in observed.items()
            if digest != EXPECTED_HASHES[label]
        }
        raise VerificationError(f"frozen binding drift: {failures}")
    return observed


def canonical_side(edges: Iterable[Edge]) -> Side:
    return tuple(sorted((min(a, b), max(a, b)) for a, b in edges))


def serialize_side(side: Side) -> list[list[int]]:
    return [[int(a), int(b)] for a, b in side]


def seed_record(seed: Seed) -> dict[str, object]:
    expression = seed.expression
    return {
        "raw_index": seed.raw_index,
        "base_position": seed.base_position,
        "base_term_index": seed.base_term_index,
        "expression": {
            "left": serialize_side(expression.left),
            "right": serialize_side(expression.right),
            "anchor": expression.anchor,
            "auxiliary": expression.auxiliary,
            "new_label": expression.new_label,
            "orientation": expression.orientation,
        },
    }


def connected_components(left: Side, right: Side) -> tuple[tuple[int, ...], tuple[int, ...]]:
    edges = left + right
    if len(edges) != 8 or len(set(edges)) != 8 or any(a == b for a, b in edges):
        raise VerificationError("base union is not eight distinct nonloops")
    graph = nx.Graph()
    graph.add_nodes_from(range(1, OLD_N + 1))
    graph.add_edges_from(edges)
    components = tuple(sorted(tuple(sorted(part)) for part in nx.connected_components(graph)))
    if len(components) != 2 or set().union(*map(set, components)) != set(range(1, 11)):
        raise VerificationError("base union is not a two-component full-support forest")
    if not nx.is_forest(graph):
        raise VerificationError("base union unexpectedly contains a cycle")
    return components  # type: ignore[return-value]


def load_bases_independently() -> list[Base]:
    document = read_json(MAX10_CERTIFICATE)
    terms = document.get("terms")
    if document.get("n") != OLD_N or not isinstance(terms, list):
        raise VerificationError("malformed frozen MAX10 certificate")
    bases: list[Base] = []
    for term_index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise VerificationError(f"malformed term {term_index}")
        pair = term.get("pair")
        if not isinstance(pair, list) or len(pair) != 2:
            raise VerificationError(f"malformed pair at term {term_index}")
        parsed_sides: list[Side] = []
        for raw_side in pair:
            if not isinstance(raw_side, list):
                raise VerificationError(f"malformed side at term {term_index}")
            edges: list[Edge] = []
            for raw_edge in raw_side:
                if (
                    not isinstance(raw_edge, list)
                    or len(raw_edge) != 2
                    or any(type(value) is not int for value in raw_edge)
                ):
                    raise VerificationError(f"malformed edge at term {term_index}")
                a, b = sorted(map(int, raw_edge))
                if not (1 <= a <= b <= OLD_N):
                    raise VerificationError(f"edge outside 1..10 at term {term_index}")
                edges.append((a, b))
            parsed_sides.append(canonical_side(edges))
        left, right = parsed_sides
        if len(left) != 4 or len(right) != 4:
            continue
        try:
            components = connected_components(left, right)
        except VerificationError:
            continue
        bases.append(Base(len(bases), term_index, left, right, components))
    if len(bases) != BASE_COUNT:
        raise VerificationError(f"base census drift: {len(bases)} != {BASE_COUNT}")
    return bases


def enumerate_same_component_seeds(bases: Sequence[Base]) -> list[Seed]:
    seeds: list[Seed] = []
    for base in bases:
        component_for = {
            vertex: component
            for component in base.components
            for vertex in component
        }
        for anchor in range(1, OLD_N + 1):
            for auxiliary in component_for[anchor]:
                if auxiliary == anchor:
                    continue
                for orientation in (0, 1):
                    seeds.append(
                        Seed(
                            raw_index=len(seeds),
                            base_position=base.position,
                            base_term_index=base.term_index,
                            expression=Expression(
                                left=base.left,
                                right=base.right,
                                anchor=anchor,
                                auxiliary=auxiliary,
                                new_label=N,
                                orientation=orientation,
                            ),
                        )
                    )
    keys = {
        (
            seed.base_term_index,
            seed.expression.anchor,
            seed.expression.auxiliary,
            seed.expression.orientation,
        )
        for seed in seeds
    }
    if len(seeds) != RAW_SEED_COUNT or len(keys) != RAW_SEED_COUNT:
        raise VerificationError(f"same-component raw census drift: {len(seeds)}")
    return seeds


def typed_occurrence_graph(expression: Expression) -> nx.Graph:
    """Build the orbit graph independently from the frozen producer modules."""

    labels = {
        *[vertex for edge in expression.left + expression.right for vertex in edge],
        expression.anchor,
        expression.auxiliary,
        expression.new_label,
    }
    if labels != set(range(1, N + 1)):
        raise VerificationError("expression lost exact full support")
    if expression.orientation not in (0, 1):
        raise VerificationError("orientation outside {0,1}")
    if len({expression.anchor, expression.auxiliary, expression.new_label}) != 3:
        raise VerificationError("Y-spoke labels are not distinct")

    graph = nx.Graph()

    def node(kind: str) -> int:
        index = graph.number_of_nodes()
        graph.add_node(index, kind=kind)
        return index

    coordinates = [node("coordinate") for _ in range(N)]
    outer = node("outer-max")
    branches = [node("branch-sum"), node("branch-sum")]
    graph.add_edge(outer, branches[0])
    graph.add_edge(outer, branches[1])

    for branch, side in enumerate((expression.left, expression.right)):
        for a, b in side:
            graphical_max = node("graphical-max")
            graph.add_edge(graphical_max, branches[branch])
            graph.add_edge(graphical_max, coordinates[a - 1])
            graph.add_edge(graphical_max, coordinates[b - 1])

    simple_form = node("linear-form")
    graph.add_edge(simple_form, branches[expression.orientation])
    for _ in range(2):
        incidence = node("unit-incidence")
        graph.add_edge(simple_form, incidence)
        graph.add_edge(incidence, coordinates[expression.anchor - 1])

    y_max = node("y-max")
    graph.add_edge(y_max, branches[1 - expression.orientation])
    doubled_arm = node("linear-form")
    leaf_arm = node("linear-form")
    graph.add_edge(y_max, doubled_arm)
    graph.add_edge(y_max, leaf_arm)
    for _ in range(2):
        incidence = node("unit-incidence")
        graph.add_edge(doubled_arm, incidence)
        graph.add_edge(incidence, coordinates[expression.anchor - 1])
    for label in (expression.auxiliary, expression.new_label):
        incidence = node("unit-incidence")
        graph.add_edge(leaf_arm, incidence)
        graph.add_edge(incidence, coordinates[label - 1])
    return graph


COLOR_ORDER = (
    "coordinate",
    "outer-max",
    "branch-sum",
    "graphical-max",
    "linear-form",
    "y-max",
    "unit-incidence",
)


def pynauty_certificate_from_graph(graph: nx.Graph) -> bytes:
    coloring = [
        {node for node, data in graph.nodes(data=True) if data.get("kind") == kind}
        for kind in COLOR_ORDER
    ]
    if any(not block for block in coloring):
        raise VerificationError("typed graph lost a required color class")
    adjacency = {
        int(node): sorted(map(int, graph.neighbors(node))) for node in graph.nodes
    }
    return pynauty.certificate(
        pynauty.Graph(
            number_of_vertices=graph.number_of_nodes(),
            directed=False,
            adjacency_dict=adjacency,
            vertex_coloring=coloring,
        )
    )


def wl_bucket(graph: nx.Graph) -> str:
    return nx.weisfeiler_lehman_graph_hash(graph, node_attr="kind", iterations=5)


def reconstruct_orbits_independently(seeds: Sequence[Seed]) -> OrbitReconstruction:
    """Classify with WL+VF2; use pynauty only for the registered order."""

    buckets: dict[str, list[Seed]] = defaultdict(list)
    for seed in seeds:
        buckets[wl_bucket(typed_occurrence_graph(seed.expression))].append(seed)

    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    orbit_groups: list[list[Seed]] = []
    vf2_checks = 0
    for bucket_key in sorted(buckets):
        local_groups: list[tuple[nx.Graph, list[Seed]]] = []
        for seed in buckets[bucket_key]:
            graph = typed_occurrence_graph(seed.expression)
            matched = False
            for reference, members in local_groups:
                if nx.is_isomorphic(reference, graph, node_match=node_match):
                    members.append(seed)
                    vf2_checks += 1
                    matched = True
                    break
            if not matched:
                local_groups.append((graph, [seed]))
        orbit_groups.extend(members for _reference, members in local_groups)

    if len(orbit_groups) != NEW_COLUMN_COUNT:
        raise VerificationError(
            f"independent VF2 orbit census drift: {len(orbit_groups)} != {NEW_COLUMN_COUNT}"
        )

    ordered: list[tuple[str, bytes, Seed, list[Seed]]] = []
    for members in orbit_groups:
        representative = min(members, key=lambda item: canonical_bytes(seed_record(item)))
        certificate = pynauty_certificate_from_graph(
            typed_occurrence_graph(representative.expression)
        )
        for member in members:
            member_certificate = pynauty_certificate_from_graph(
                typed_occurrence_graph(member.expression)
            )
            if member_certificate != certificate:
                raise VerificationError(
                    "independent VF2 class disagrees with pinned pynauty invariant"
                )
        ordered.append((hashlib.sha256(certificate).hexdigest(), certificate, representative, members))

    ordered.sort(key=lambda item: item[0])
    certificate_hashes = [item[0] for item in ordered]
    if len(set(certificate_hashes)) != NEW_COLUMN_COUNT:
        raise VerificationError("registered orbit ordering keys are not unique")
    representatives = [item[2] for item in ordered]
    class_sizes = [len(item[3]) for item in ordered]
    manifest = [
        {
            "certificate_sha256": certificate_hash,
            "raw_seed_count": class_size,
            "representative": seed_record(representative),
        }
        for certificate_hash, representative, class_size in zip(
            certificate_hashes, representatives, class_sizes, strict=True
        )
    ]
    orbit_manifest_sha256 = canonical_sha256(manifest)
    representative_manifest_sha256 = canonical_sha256(
        [seed_record(seed) for seed in representatives]
    )
    if orbit_manifest_sha256 != EXPECTED_ORBIT_MANIFEST:
        raise VerificationError(
            f"orbit manifest drift: {orbit_manifest_sha256} != {EXPECTED_ORBIT_MANIFEST}"
        )
    if representative_manifest_sha256 != EXPECTED_REPRESENTATIVE_MANIFEST:
        raise VerificationError(
            "representative manifest drift: "
            f"{representative_manifest_sha256} != {EXPECTED_REPRESENTATIVE_MANIFEST}"
        )
    return OrbitReconstruction(
        representatives=tuple(representatives),
        class_sizes=tuple(class_sizes),
        certificate_sha256s=tuple(certificate_hashes),
        orbit_manifest_sha256=orbit_manifest_sha256,
        representative_manifest_sha256=representative_manifest_sha256,
        vf2_nonrepresentative_checks=vf2_checks,
    )


def positive_four_profiles() -> list[tuple[int, int, int, int]]:
    return [
        (c0, c1, c2, N - c0 - c1 - c2)
        for c0 in range(1, N - 2)
        for c1 in range(1, N - c0 - 1)
        for c2 in range(1, N - c0 - c1)
        if N - c0 - c1 - c2 >= 1
    ]


def all_four_profiles() -> list[tuple[int, int, int, int]]:
    return [
        (c0, c1, c2, N - c0 - c1 - c2)
        for c0 in range(N + 1)
        for c1 in range(N + 1 - c0)
        for c2 in range(N + 1 - c0 - c1)
    ]


def all_three_profiles() -> list[tuple[int, int, int]]:
    return [
        (zero, middle, N - zero - middle)
        for zero in range(N + 1)
        for middle in range(N + 1 - zero)
    ]


@lru_cache(maxsize=None)
def panel_ratios() -> tuple[tuple[int, int], ...]:
    ratios: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    counter = 0
    while len(ratios) < PANEL_COUNT:
        digest = hashlib.sha256(f"{PANEL_SEED};panel={counter}\n".encode()).digest()
        first = 1 + int.from_bytes(digest[:8], "big") % (PANEL_DENOMINATOR - 1)
        second = 1 + int.from_bytes(digest[8:16], "big") % (PANEL_DENOMINATOR - 1)
        counter += 1
        if first == second:
            continue
        ratio = tuple(sorted((first, second)))
        if ratio in seen:
            continue
        seen.add(ratio)
        ratios.append(ratio)
    return tuple(ratios)


@lru_cache(maxsize=None)
def four_assignment_codes(profile: tuple[int, int, int, int]) -> np.ndarray:
    if sum(profile) != N:
        raise VerificationError(f"invalid four-profile: {profile}")
    _zero_count, one_count, two_count, three_count = profile
    vertices = tuple(range(N))
    assignments: list[list[int]] = []
    for threes in combinations(vertices, three_count):
        three_set = set(threes)
        without_three = tuple(v for v in vertices if v not in three_set)
        for twos in combinations(without_three, two_count):
            two_set = set(twos)
            without_two = tuple(v for v in without_three if v not in two_set)
            for ones in combinations(without_two, one_count):
                point = [0] * N
                for vertex in ones:
                    point[vertex] = 1
                for vertex in twos:
                    point[vertex] = 2
                for vertex in threes:
                    point[vertex] = 3
                assignments.append(point)
    return np.asarray(assignments, dtype=np.int16).T


@lru_cache(maxsize=None)
def three_assignment_levels(
    profile: tuple[int, int, int], numerator: int, denominator: int
) -> np.ndarray:
    if sum(profile) != N:
        raise VerificationError(f"invalid three-profile: {profile}")
    _zero_count, middle_count, top_count = profile
    vertices = tuple(range(N))
    assignments: list[list[int]] = []
    for tops in combinations(vertices, top_count):
        top_set = set(tops)
        without_top = tuple(v for v in vertices if v not in top_set)
        for middles in combinations(without_top, middle_count):
            point = [0] * N
            for vertex in middles:
                point[vertex] = numerator
            for vertex in tops:
                point[vertex] = denominator
            assignments.append(point)
    return np.asarray(assignments, dtype=np.int16).T


def raw_row_levels(raw_row: int) -> np.ndarray:
    if not 0 <= raw_row < TOTAL_ROWS:
        raise VerificationError(f"raw row outside 0..{TOTAL_ROWS - 1}: {raw_row}")
    positive = positive_four_profiles()
    panel_rows = PANEL_COUNT * len(positive)
    if raw_row < panel_rows:
        panel, offset = divmod(raw_row, len(positive))
        ratio = panel_ratios()[panel]
        lookup = np.asarray((0, ratio[0], ratio[1], PANEL_DENOMINATOR), dtype=np.int16)
        return lookup[four_assignment_codes(positive[offset])]
    offset = raw_row - panel_rows
    all_four = all_four_profiles()
    if offset < len(all_four):
        return four_assignment_codes(all_four[offset])
    farey_offset = offset - len(all_four)
    profiles = all_three_profiles()
    ratio_index, profile_index = divmod(farey_offset, len(profiles))
    if ratio_index >= len(FAREY_F6):
        raise VerificationError("Farey row decomposition overflow")
    numerator, denominator = FAREY_F6[ratio_index]
    return three_assignment_levels(profiles[profile_index], numerator, denominator)


def literal_scalar_value(expression: Expression, point: Sequence[int]) -> int:
    left = sum(max(int(point[a - 1]), int(point[b - 1])) for a, b in expression.left)
    right = sum(max(int(point[a - 1]), int(point[b - 1])) for a, b in expression.right)
    anchor = int(point[expression.anchor - 1])
    simple = anchor + anchor
    leaf = int(point[expression.auxiliary - 1]) + int(point[expression.new_label - 1])
    y_value = max(simple, leaf)
    if expression.orientation == 0:
        return max(left + simple, right + y_value)
    return max(left + y_value, right + simple)


def literal_scalar_orbit_sum(expression: Expression, levels: np.ndarray) -> int:
    return sum(
        literal_scalar_value(expression, levels[:, column])
        for column in range(levels.shape[1])
    )


def grouped_representatives(
    representatives: Sequence[Seed], base_count: int
) -> list[list[tuple[int, Seed]]]:
    grouped: list[list[tuple[int, Seed]]] = [[] for _ in range(base_count)]
    for column, seed in enumerate(representatives):
        grouped[seed.base_position].append((column, seed))
    return grouped


def literal_nested_support_matrix(
    bases: Sequence[Base], representatives: Sequence[Seed], rows: Sequence[int]
) -> tuple[np.ndarray, np.ndarray, int]:
    """Evaluate literal nested semantics in bounded batches, never flattened."""

    grouped = grouped_representatives(representatives, len(bases))
    matrix = np.zeros((len(rows), len(representatives)), dtype=np.int64)
    targets = np.zeros(len(rows), dtype=np.int64)
    scalar_candidates: list[tuple[int, int]] = []

    for output_row, raw_row in enumerate(rows):
        levels = raw_row_levels(int(raw_row)).astype(np.int64, copy=False)
        targets[output_row] = np.max(levels, axis=0).sum(dtype=np.int64)
        for base in bases:
            entries = grouped[base.position]
            if not entries:
                continue
            left = np.zeros(levels.shape[1], dtype=np.int64)
            right = np.zeros(levels.shape[1], dtype=np.int64)
            for a, b in base.left:
                left += np.maximum(levels[a - 1], levels[b - 1])
            for a, b in base.right:
                right += np.maximum(levels[a - 1], levels[b - 1])
            for start in range(0, len(entries), EVALUATION_BATCH_SIZE):
                batch = entries[start : start + EVALUATION_BATCH_SIZE]
                columns = np.asarray([column for column, _seed in batch], dtype=np.intp)
                anchors = np.asarray(
                    [seed.expression.anchor - 1 for _column, seed in batch], dtype=np.intp
                )
                auxiliaries = np.asarray(
                    [seed.expression.auxiliary - 1 for _column, seed in batch], dtype=np.intp
                )
                orientations = np.asarray(
                    [seed.expression.orientation for _column, seed in batch], dtype=np.int8
                )
                anchor_values = levels[anchors]
                simple = anchor_values + anchor_values
                leaf = levels[auxiliaries] + levels[N - 1]
                y_value = np.maximum(simple, leaf)
                first_branch = np.where(
                    orientations[:, None] == 0,
                    left[None, :] + simple,
                    left[None, :] + y_value,
                )
                second_branch = np.where(
                    orientations[:, None] == 0,
                    right[None, :] + y_value,
                    right[None, :] + simple,
                )
                literal = np.maximum(first_branch, second_branch)
                matrix[output_row, columns] = literal.sum(axis=1, dtype=np.int64)
        scalar_column = int.from_bytes(
            hashlib.sha256(f"g0079-cleanroom-scalar;{raw_row}\n".encode()).digest()[:8],
            "big",
        ) % len(representatives)
        scalar_candidates.append((output_row, scalar_column))
        if (output_row + 1) % 10 == 0 or output_row + 1 == len(rows):
            print(
                f"CLEANROOM_G0079 nested_rows={output_row + 1}/{len(rows)}",
                file=sys.stderr,
                flush=True,
            )

    selected = scalar_candidates[:SCALAR_REPLAY_CHECKS]
    for row_index, column in selected:
        levels = raw_row_levels(int(rows[row_index]))
        scalar = literal_scalar_orbit_sum(representatives[column].expression, levels)
        if scalar != int(matrix[row_index, column]):
            raise VerificationError(
                f"scalar/nested-batch mismatch at support row {row_index}, column {column}"
            )
    return matrix, targets, len(selected)


def load_exact_functional() -> ExactFunctional:
    report = read_gzip_json(G0078_EXACT)
    payload = report.get("scientific_payload")
    if not isinstance(payload, dict):
        raise VerificationError("G-0078 scientific payload missing")
    if (
        report.get("scientific_payload_sha256") != EXPECTED_G0078_SCIENCE
        or canonical_sha256(payload) != EXPECTED_G0078_SCIENCE
    ):
        raise VerificationError("G-0078 scientific payload digest drift")
    selected_rows = list(map(int, payload.get("selected_raw_rows", [])))
    selected_divisors = list(map(int, payload.get("selected_raw_row_divisors", [])))
    selected_numerators = list(map(int, payload.get("integer_dual_numerators", [])))
    failing_row = int(payload.get("failing_raw_row", -1))
    failing_divisor = int(payload.get("failing_raw_row_divisor", 0))
    failing_weight = int(payload.get("integer_failing_row_weight", 0))
    if (
        len(selected_rows) != SUPPORT_ROWS - 1
        or len(selected_divisors) != SUPPORT_ROWS - 1
        or len(selected_numerators) != SUPPORT_ROWS - 1
        or len(set(selected_rows)) != SUPPORT_ROWS - 1
        or failing_row in selected_rows
        or min(selected_divisors, default=0) <= 0
        or failing_divisor <= 0
        or payload.get("all_A_columns_annihilated_exactly") is not True
        or payload.get("exact_target_pairing_nonzero") is not True
    ):
        raise VerificationError("malformed G-0078 exact functional")
    denominators = selected_divisors + [failing_divisor]
    numerators = selected_numerators + [failing_weight]
    denominator_lcm = math.lcm(*denominators)
    cleared = [
        numerator * (denominator_lcm // denominator)
        for numerator, denominator in zip(numerators, denominators, strict=True)
    ]
    global_gcd = math.gcd(*map(abs, cleared))
    if global_gcd <= 0:
        raise VerificationError("zero common gcd in G-0078 functional")
    weights = tuple(value // global_gcd for value in cleared)
    if math.gcd(*map(abs, weights)) != 1:
        raise VerificationError("G-0078 integer functional is not globally primitive")
    for numerator, denominator, weight in zip(
        numerators, denominators, weights, strict=True
    ):
        if Fraction(weight * global_gcd, denominator_lcm) != Fraction(
            numerator, denominator
        ):
            raise VerificationError("G-0078 LCM clearing failed exact replay")
    target = Fraction(str(payload.get("exact_target_pairing")))
    scaled_target = target * denominator_lcm / global_gcd
    if scaled_target.denominator != 1 or scaled_target.numerator == 0:
        raise VerificationError("G-0078 target does not clear to a nonzero integer")
    return ExactFunctional(
        rows=tuple(selected_rows + [failing_row]),
        weights=weights,
        denominator_lcm=denominator_lcm,
        global_gcd=global_gcd,
        expected_target=scaled_target.numerator,
        g0078_scientific_payload_sha256=EXPECTED_G0078_SCIENCE,
    )


def integer_pairings(weights: Sequence[int], values: np.ndarray) -> list[int]:
    if values.shape[0] != len(weights):
        raise VerificationError("pairing matrix/support shape mismatch")
    prices = [0] * values.shape[1]
    for row, weight in enumerate(weights):
        prices = [
            current + int(weight) * int(value)
            for current, value in zip(prices, values[row], strict=True)
        ]
    return prices


def expected_price_records(
    bases: Sequence[Base], orbits: OrbitReconstruction, prices: Sequence[int]
) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for local_index, (seed, class_size, price) in enumerate(
        zip(orbits.representatives, orbits.class_sizes, prices, strict=True)
    ):
        expression = seed.expression
        base = bases[seed.base_position]
        topology = sorted(map(len, base.components))
        anchor_component_size = next(
            len(component) for component in base.components if expression.anchor in component
        )
        records.append(
            {
                "local_index": local_index,
                "global_id": GLOBAL_NEW_START + local_index,
                "price": str(price),
                "representative_sha256": canonical_sha256(seed_record(seed)),
                "base_position": seed.base_position,
                "base_term_index": seed.base_term_index,
                "component_topology": f"{topology[0]}+{topology[1]}",
                "anchor_component_size": anchor_component_size,
                "anchor": expression.anchor,
                "auxiliary": expression.auxiliary,
                "orientation": expression.orientation,
                "orbit_class_size": class_size,
            }
        )
    return records


def validate_preregistration() -> dict[str, object]:
    preregistration = read_json(PREREGISTRATION)
    price_stage = preregistration.get("price_stage")
    claim_contract = preregistration.get("claim_contract")
    semantic_sources = preregistration.get("semantic_source_sha256")
    superseded = preregistration.get("supersedes_aborted_registration")
    if (
        preregistration.get("schema") != SCHEMA_PREREGISTRATION
        or preregistration.get("experiment_status") != "planned"
        or preregistration.get("trial_id") != "G-0079-PRICE-0002"
        or preregistration.get("new_columns") != NEW_COLUMN_COUNT
        or preregistration.get("registered_source_sha256") != EXPECTED_HASHES["runner"]
        or preregistration.get("preflight_receipt_sha256")
        != EXPECTED_HASHES["preflight_receipt"]
        or preregistration.get("preflight_scientific_payload_sha256")
        != EXPECTED_PREFLIGHT_SCIENCE
        or preregistration.get("all_new_columns_retained_after_nonzero_price") is not True
        or preregistration.get("semantic_execution_from_single_read_expected_hash_bytes")
        is not True
        or preregistration.get("project_semantic_bytecode_cache_execution_allowed")
        is not False
        or semantic_sources
        != {
            "g0073": EXPECTED_HASHES["g0073_source"],
            "g0074": EXPECTED_HASHES["g0074_source"],
            "g0075": EXPECTED_HASHES["g0075_source"],
        }
        or not isinstance(price_stage, dict)
        or price_stage.get("output") != str(REGISTERED_RECEIPT.relative_to(ROOT))
        or price_stage.get("new_columns") != NEW_COLUMN_COUNT
        or price_stage.get("serialize_all_prices") is not True
        or price_stage.get("quotient_execution_in_this_source") is not False
        or price_stage.get("transitive_semantic_source_custody_bound") is not True
        or not isinstance(claim_contract, dict)
        or "proves neither membership nor nonmembership"
        not in str(claim_contract.get("some_nonzero"))
        or not isinstance(superseded, dict)
        or superseded.get("preregistration_sha256")
        != "8a55dcc16bd965cf6b121b57cb9defcd8bec635e793eea04aaedbd4451f4d7f1"
        or "No v1 price output exists" not in str(superseded.get("reason"))
    ):
        raise VerificationError("preregistration contract drift")
    return preregistration


def validate_preflight_receipt() -> dict[str, object]:
    preflight = read_gzip_json(PREFLIGHT_RECEIPT)
    subject = preflight.get("subject")
    controls = preflight.get("controls")
    if not isinstance(subject, dict) or not isinstance(controls, dict):
        raise VerificationError("malformed G-0079 preflight receipt")
    new_family = subject.get("new_family")
    prices = controls.get("exact_separator_prices")
    if (
        preflight.get("scientific_payload_sha256") != EXPECTED_PREFLIGHT_SCIENCE
        or preflight.get("script_sha256") != EXPECTED_HASHES["preflight_source"]
        or not isinstance(new_family, dict)
        or new_family.get("raw_seed_count") != RAW_SEED_COUNT
        or new_family.get("orbit_count") != NEW_COLUMN_COUNT
        or new_family.get("orbit_manifest_sha256") != EXPECTED_ORBIT_MANIFEST
        or new_family.get("representative_manifest_sha256")
        != EXPECTED_REPRESENTATIVE_MANIFEST
        or not isinstance(prices, dict)
        or prices.get("actual_new_family_columns_priced") != 0
    ):
        raise VerificationError("G-0079 preflight binding/manifest drift")
    return preflight


def expected_semantic_source_execution() -> dict[str, object]:
    return {
        "sources": {
            "g0075": {
                "path": str(G0075_SOURCE.relative_to(ROOT)),
                "sha256": EXPECTED_HASHES["g0075_source"],
                "bytes": G0075_SOURCE.stat().st_size,
                "cached": None,
                "loader": "OwnedBytesLoader",
            },
            "g0074": {
                "path": str(G0074_SOURCE.relative_to(ROOT)),
                "sha256": EXPECTED_HASHES["g0074_source"],
                "bytes": G0074_SOURCE.stat().st_size,
                "cached": None,
                "loader": "OwnedBytesLoader",
            },
            "g0073": {
                "path": str(G0073_SOURCE.relative_to(ROOT)),
                "sha256": EXPECTED_HASHES["g0073_source"],
                "bytes": G0073_SOURCE.stat().st_size,
                "cached": None,
                "loader": "OwnedBytesLoader",
            },
        },
        "execution_order": ["g0075", "g0074", "g0073"],
        "intercepted_legacy_file_imports": [
            "g0074_frozen_for_g0075",
            "g0073_frozen_for_g0074",
        ],
        "single_read_expected_hash_execution_bytes": True,
        "project_semantic_bytecode_cache_execution_allowed": False,
        "bytecode_policy_scope": "G-0075/G-0074/G-0073 project-semantic sources",
        "shared_g0073_module_identity": True,
    }


def validate_receipt_structure(
    report: dict[str, object],
    bindings: dict[str, str],
    functional: ExactFunctional,
    matrix: np.ndarray,
    targets: np.ndarray,
    prices: Sequence[int],
    records: list[dict[str, object]],
) -> tuple[dict[str, object], str]:
    scientific = report.get("scientific_payload")
    if not isinstance(scientific, dict):
        raise VerificationError("registered receipt scientific payload missing")
    if report.get("schema") != SCHEMA_PRICE or scientific.get("schema") != SCHEMA_PRICE:
        raise VerificationError("registered receipt schema drift")
    if report.get("scientific_payload_sha256") != canonical_sha256(scientific):
        raise VerificationError("registered scientific-payload digest mismatch")
    if (
        report.get("runner_sha256") != EXPECTED_HASHES["runner"]
        or report.get("preregistration_sha256") != EXPECTED_HASHES["preregistration"]
        or report.get("preflight_receipt_sha256") != EXPECTED_HASHES["preflight_receipt"]
    ):
        raise VerificationError("registered outer binding drift")

    custody = report.get("custody")
    expected_custody = {
        "environment_manifest": bindings["environment_manifest"],
        "full_old_matrix": bindings["full_old_matrix"],
        "g0073_semantic_source": bindings["g0073_source"],
        "g0074_semantic_source": bindings["g0074_source"],
        "g0075_semantic_source": bindings["g0075_source"],
        "g0077_modular": bindings["g0077_modular"],
        "g0078_exact": bindings["g0078_exact"],
        "preflight_receipt": bindings["preflight_receipt"],
        "preflight_source": bindings["preflight_source"],
        "preregistration": bindings["preregistration"],
        "runner": bindings["runner"],
    }
    if (
        not isinstance(custody, dict)
        or custody.get("identical") is not True
        or custody.get("start") != expected_custody
        or custody.get("end") != expected_custody
    ):
        raise VerificationError("registered custody is not identical to frozen inputs")

    dictionary = scientific.get("registered_dictionary")
    semantic_execution = scientific.get("semantic_source_execution")
    exact = scientific.get("exact_functional")
    complete = scientific.get("complete_price_vector")
    branch = scientific.get("branch_contract")
    if not all(
        isinstance(value, dict)
        for value in (dictionary, semantic_execution, exact, complete, branch)
    ):
        raise VerificationError("registered scientific subobject missing")
    assert isinstance(dictionary, dict)
    assert isinstance(semantic_execution, dict)
    assert isinstance(exact, dict)
    assert isinstance(complete, dict)
    assert isinstance(branch, dict)

    expected_ids = list(range(GLOBAL_NEW_START, GLOBAL_NEW_STOP + 1))
    if dictionary != {
        "old_columns_including_carriers": OLD_COLUMN_COUNT,
        "new_columns": NEW_COLUMN_COUNT,
        "total_columns": COMBINED_COLUMN_COUNT,
        "new_global_ids": [GLOBAL_NEW_START, GLOBAL_NEW_STOP],
        "target_global_id": GLOBAL_TARGET_ID,
        "new_representative_manifest_sha256": EXPECTED_REPRESENTATIVE_MANIFEST,
    }:
        raise VerificationError("registered dictionary descriptor drift")
    if semantic_execution != expected_semantic_source_execution():
        raise VerificationError("registered semantic-source execution receipt drift")

    expected_target = sum(
        weight * int(value)
        for weight, value in zip(functional.weights, targets, strict=True)
    )
    if expected_target != functional.expected_target:
        raise VerificationError("independent MAX11 target pairing disagrees with G-0078")
    weight_strings = list(map(str, functional.weights))
    expected_exact = {
        "source": str(G0078_EXACT.relative_to(ROOT)),
        "source_scientific_payload_sha256": EXPECTED_G0078_SCIENCE,
        "support_rows": list(functional.rows),
        "support_rows_sha256": canonical_sha256(list(functional.rows)),
        "common_denominator_lcm": functional.denominator_lcm,
        "single_global_primitive_gcd": functional.global_gcd,
        "primitive_integer_weights": weight_strings,
        "primitive_integer_weights_sha256": canonical_sha256(weight_strings),
        "coordinatewise_row_gcd_or_modular_division_used": False,
        "exact_target_pairing": str(expected_target),
        "exact_target_pairing_nonzero": True,
        "target_pairing_mod_prime": expected_target % PRIME,
    }
    if exact != expected_exact:
        raise VerificationError("serialized exact functional differs from clean-room replay")
    if expected_target % PRIME == 0:
        raise VerificationError("independent target pairing vanishes at registered prime")

    price_strings = list(map(str, prices))
    prices_mod_prime = [price % PRIME for price in prices]
    zero_count = sum(price == 0 for price in prices)
    nonzero_count = NEW_COLUMN_COUNT - zero_count
    first_nonzero = next((index for index, price in enumerate(prices) if price), None)
    first_modular_nonzero = next(
        (index for index, price in enumerate(prices_mod_prime) if price), None
    )
    vector_gcd = math.gcd(*map(abs, prices))
    vector_target_gcd = math.gcd(vector_gcd, abs(expected_target))
    expected_complete_fields = {
        "column_order": "local new representative order 0..18581; global=8107+local",
        "global_column_ids": expected_ids,
        "prices": price_strings,
        "prices_sha256": canonical_sha256(price_strings),
        "price_records": records,
        "price_records_sha256": canonical_sha256(records),
        "zero_count": zero_count,
        "nonzero_count": nonzero_count,
        "price_vector_gcd": str(vector_gcd),
        "price_vector_with_target_gcd": str(vector_target_gcd),
        "first_nonzero_local_index": first_nonzero,
        "prices_mod_prime": prices_mod_prime,
        "prices_mod_prime_sha256": canonical_sha256(prices_mod_prime),
        "modular_nonzero_count": sum(price != 0 for price in prices_mod_prime),
        "first_modular_nonzero_local_index": first_modular_nonzero,
        "all_18582_columns_serialized": True,
        "support_values_int64_c_sha256": raw_sha256(matrix),
        "independent_nested_support_values_int64_c_sha256": raw_sha256(matrix),
        "all_4273860_entries_match_independent_nested_evaluator": True,
        "target_values_int64_sha256": raw_sha256(targets),
        "independent_target_values_int64_sha256": raw_sha256(targets),
    }
    if complete != expected_complete_fields:
        differing = sorted(
            key
            for key in set(complete) | set(expected_complete_fields)
            if complete.get(key) != expected_complete_fields.get(key)
        )
        raise VerificationError(f"complete price receipt differs at fields: {differing}")

    expected_result = RESULT_ALL_ZERO if nonzero_count == 0 else RESULT_NONZERO
    if scientific.get("result") != expected_result:
        raise VerificationError("registered result label disagrees with exact prices")
    claim_boundary = str(scientific.get("claim_boundary", ""))
    if (
        branch.get("all_new_columns_retained_if_nonzero") is not True
        or branch.get("price_filtering_allowed") is not False
        or branch.get("quotient_execution_in_this_source") is not False
        or branch.get("independent_external_replay_required_for_promotion") is not True
        or "not an unrestricted network lower bound" not in claim_boundary
        or "proves neither membership nor nonmembership" not in claim_boundary
    ):
        raise VerificationError("registered branch/claim boundary weakened")
    return scientific, expected_result


def verify_registered_receipt(receipt_path: Path) -> dict[str, object]:
    if receipt_path.resolve(strict=False) != REGISTERED_RECEIPT.resolve(strict=False):
        raise VerificationError("verifier accepts only the preregistered G-0079 output path")
    bindings = replay_bindings()
    validate_preregistration()
    validate_preflight_receipt()
    functional = load_exact_functional()
    bases = load_bases_independently()
    seeds = enumerate_same_component_seeds(bases)
    orbits = reconstruct_orbits_independently(seeds)
    matrix, targets, scalar_checks = literal_nested_support_matrix(
        bases, orbits.representatives, functional.rows
    )
    if matrix.shape != (SUPPORT_ROWS, NEW_COLUMN_COUNT):
        raise VerificationError(f"clean-room matrix shape drift: {matrix.shape}")
    prices = integer_pairings(functional.weights, matrix)
    records = expected_price_records(bases, orbits, prices)

    # The outcome-bearing file is opened only after all independent values exist.
    report = read_gzip_json(receipt_path)
    scientific, expected_result = validate_receipt_structure(
        report, bindings, functional, matrix, targets, prices, records
    )
    nonzero_count = sum(price != 0 for price in prices)
    interpretation = (
        "CONSISTENT_BOUNDED_NEW_FAMILY_PRICE_REPLAY; the all-zero branch still "
        "depends on the separately frozen G-0078 old-column replay"
        if nonzero_count == 0
        else "CONSISTENT_EXACT_PRICE_VECTOR_ONLY; proves neither membership nor nonmembership"
    )
    return {
        "schema": "max11-g0079-cleanroom-price-replay-v2",
        "result": "CONSISTENT",
        "cleanroom_verifier": str(Path(__file__).resolve().relative_to(ROOT)),
        "cleanroom_verifier_sha256": sha256_path(Path(__file__).resolve()),
        "registered_result": expected_result,
        "interpretation": interpretation,
        "receipt_path": str(receipt_path.resolve().relative_to(ROOT)),
        "receipt_sha256": sha256_path(receipt_path),
        "receipt_scientific_payload_sha256": report.get("scientific_payload_sha256"),
        "new_columns_reconstructed": len(orbits.representatives),
        "raw_seeds_reconstructed": len(seeds),
        "orbit_manifest_sha256": orbits.orbit_manifest_sha256,
        "representative_manifest_sha256": orbits.representative_manifest_sha256,
        "vf2_nonrepresentative_checks": orbits.vf2_nonrepresentative_checks,
        "support_rows": len(functional.rows),
        "literal_nested_entries": int(matrix.size),
        "literal_nested_matrix_sha256": raw_sha256(matrix),
        "scalar_literal_replay_checks": scalar_checks,
        "prices_sha256": scientific["complete_price_vector"]["prices_sha256"],
        "zero_count": NEW_COLUMN_COUNT - nonzero_count,
        "nonzero_count": nonzero_count,
        "target_pairing": str(functional.expected_target),
        "independence": {
            "producer_modules_imported_or_executed": False,
            "orbit_membership_primary_method": "NetworkX WL buckets plus exact colored VF2",
            "pynauty_use": "registered orbit ordering and cross-check only",
            "column_semantics": "literal inner Y-max then literal outer max; no flattened identity",
            "assignment_generation": "independent combinations enumeration",
            "target_generation": "independent MAX11 over each assignment",
            "remaining_limitation": (
                "shares Python/NumPy, NetworkX, pynauty, the frozen MAX10 certificate, and "
                "the G-0078 functional artifact with the producer; it does not replay all "
                "8,107 old columns and is same-model-family T1 evidence"
            ),
        },
        "claim_boundary": (
            "A nonzero vector proves neither membership nor nonmembership. An all-zero "
            "vector is bounded to the frozen 26,689-column dictionary on 16,738 rows and "
            "is not a global identity or unrestricted ReLU lower bound."
        ),
    }


def synthetic_self_test() -> dict[str, object]:
    left = canonical_side(((1, 2), (2, 3), (3, 4), (4, 5)))
    right = canonical_side(((6, 7), (7, 8), (8, 9), (9, 10)))
    components = connected_components(left, right)
    if components != ((1, 2, 3, 4, 5), (6, 7, 8, 9, 10)):
        raise VerificationError("synthetic component reconstruction failed")
    expression = Expression(left, right, 1, 2, 11, 0)
    graph = typed_occurrence_graph(expression)
    relabel = {1: 3, 3: 1, 6: 8, 8: 6, **{v: v for v in (2, 4, 5, 7, 9, 10, 11)}}
    relabeled = Expression(
        canonical_side((relabel[a], relabel[b]) for a, b in left),
        canonical_side((relabel[a], relabel[b]) for a, b in right),
        relabel[1],
        relabel[2],
        relabel[11],
        0,
    )
    relabeled_graph = typed_occurrence_graph(relabeled)
    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    if not nx.is_isomorphic(graph, relabeled_graph, node_match=node_match):
        raise VerificationError("synthetic relabeling was not recognized")
    if pynauty_certificate_from_graph(graph) != pynauty_certificate_from_graph(relabeled_graph):
        raise VerificationError("synthetic pynauty ordering invariant failed")
    mutant = graph.copy()
    first_edge = next(iter(mutant.edges))
    mutant.remove_edge(*first_edge)
    if nx.is_isomorphic(graph, mutant, node_match=node_match):
        raise VerificationError("synthetic one-edge graph mutant escaped")

    rng = np.random.default_rng(0x70079)
    levels = rng.integers(0, 19, size=(N, 37), dtype=np.int64)
    scalar = literal_scalar_orbit_sum(expression, levels)
    left_values = sum(
        (np.maximum(levels[a - 1], levels[b - 1]) for a, b in expression.left),
        start=np.zeros(levels.shape[1], dtype=np.int64),
    )
    right_values = sum(
        (np.maximum(levels[a - 1], levels[b - 1]) for a, b in expression.right),
        start=np.zeros(levels.shape[1], dtype=np.int64),
    )
    simple = levels[expression.anchor - 1] + levels[expression.anchor - 1]
    y_value = np.maximum(
        simple, levels[expression.auxiliary - 1] + levels[expression.new_label - 1]
    )
    nested = np.maximum(left_values + simple, right_values + y_value).sum(dtype=np.int64)
    if scalar != int(nested):
        raise VerificationError("synthetic scalar/nested vector evaluation failed")
    flattened_mutant = np.maximum(left_values + simple, right_values + y_value + 1).sum(
        dtype=np.int64
    )
    if scalar == int(flattened_mutant):
        raise VerificationError("synthetic one-unit semantic mutant escaped")

    values = np.asarray([[2, 0, -1], [3, 6, 2], [4, 8, 5]], dtype=np.int64)
    weights = (3, -4, 5)
    prices = integer_pairings(weights, values)
    direct = [
        sum(weights[row] * int(values[row, column]) for row in range(3))
        for column in range(3)
    ]
    if prices != direct:
        raise VerificationError("synthetic exact pairings failed")
    return {
        "schema": "max11-g0079-cleanroom-price-verifier-self-test-v2",
        "result": "PASS",
        "synthetic_colored_vf2_positive": True,
        "synthetic_colored_vf2_mutant_rejected": True,
        "synthetic_pynauty_order_invariant": True,
        "synthetic_literal_nested_scalar_replay": True,
        "synthetic_one_unit_semantic_mutant_rejected": True,
        "synthetic_integer_pairing_replay": True,
        "actual_new_family_values_evaluated": 0,
        "registered_price_receipt_opened": False,
        "no_claim": "Synthetic controls only; no registered G-0079 outcome was read or evaluated.",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--verify-receipt", type=Path)
    parser.add_argument("--authorize-outcome-read")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        if arguments.authorize_outcome_read is not None or arguments.output is not None:
            raise VerificationError("--self-test refuses registered-run arguments")
        print(json.dumps(synthetic_self_test(), sort_keys=True))
        return
    if arguments.authorize_outcome_read != OUTCOME_READ_TOKEN:
        raise VerificationError(
            "registered verification is locked until the research lead releases the receipt; "
            f"then pass --authorize-outcome-read {OUTCOME_READ_TOKEN}"
        )
    assert arguments.verify_receipt is not None
    if arguments.output is None:
        raise VerificationError("registered verification requires --output")
    report = verify_registered_receipt(arguments.verify_receipt)
    write_gzip_exclusive(arguments.output, report)
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "result": report["result"],
                "registered_result": report["registered_result"],
                "output": str(arguments.output.resolve().relative_to(ROOT)),
                "output_sha256": sha256_path(arguments.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
