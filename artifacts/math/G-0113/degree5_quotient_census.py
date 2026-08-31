#!/usr/bin/env python3
"""Target-blind exact quotient census for arbitrary-edge MAX10 lifts.

The primary dictionary appends one distinct nonloop edge to each branch of
each public MAX10 degree-four certificate term.  It is partitioned according
to whether the two added edges are disjoint or share exactly one endpoint.
No MAX11 target values or ranks are computed here.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Iterator, Sequence

import networkx as nx
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "DEGREE5_QUOTIENT_PREREGISTRATION.md"
FIBER_ADDENDUM = HERE / "DEGREE5_FIBER_ADDENDUM.md"
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"

EXPECTED_PREREGISTRATION_SHA256 = (
    "9b57dc419e7ab54de621e84a0e3d713b1a78a13572517b9e50af99bf3b023141"
)
EXPECTED_FIBER_ADDENDUM_SHA256 = (
    "23e657b646581ef81c61654e2a966d0f73ad23618b15de27e15f40b6926e3822"
)
EXPECTED_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
EXPECTED_SOURCE_TERMS = 402
EXPECTED_STAR_RAW = 48_642
EXPECTED_STAR_ORBITS = 23_147
EXPECTED_DISJOINT_RAW = 795_960
EXPECTED_SHARED_RAW = 397_980
EXPECTED_PRIMARY_RAW = EXPECTED_DISJOINT_RAW + EXPECTED_SHARED_RAW
TRACTABLE_ORBIT_LIMIT = 400_000
TRACTABLE_MAP_BYTE_LIMIT = 250 * 1024 * 1024
VF2_SAMPLES_PER_FAMILY = 64

N = 11
OLD_N = 10
SCHEMA = "max11-g0113-degree5-arbitrary-edge-quotient-census-v1"
MAP_SCHEMA = "max11-g0113-degree5-signed-orbit-representatives-v1"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Descriptor = tuple[int, Edge, Edge]
FiberEntry = tuple[int, int, Edge, Edge]


class CensusError(RuntimeError):
    """A frozen binding, exact control, or census invariant failed."""


@dataclass(frozen=True)
class SourceTerm:
    index: int
    coefficient: Fraction
    pair: Pair


@dataclass
class LocalClass:
    count: int
    left_edge: Edge
    right_edge: Edge


@dataclass
class SliceResult:
    term_index: int
    disjoint: dict[bytes, LocalClass]
    shared: dict[bytes, LocalClass]
    disjoint_duplicate_samples: list[tuple[bytes, Edge, Edge, Edge, Edge]]
    shared_duplicate_samples: list[tuple[bytes, Edge, Edge, Edge, Edge]]
    disjoint_raw: int
    shared_raw: int


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def canonical_side(raw: Iterable[Sequence[int]]) -> Side:
    return tuple(sorted((min(map(int, edge)), max(map(int, edge))) for edge in raw))


def serialize_side(side: Side) -> list[list[int]]:
    return [[u, v] for u, v in side]


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [serialize_side(pair[0]), serialize_side(pair[1])]


def load_terms() -> list[SourceTerm]:
    prereg_hash = sha256_path(PREREGISTRATION)
    if prereg_hash != EXPECTED_PREREGISTRATION_SHA256:
        raise CensusError(f"preregistration drift: {prereg_hash}")
    fiber_addendum_hash = sha256_path(FIBER_ADDENDUM)
    if fiber_addendum_hash != EXPECTED_FIBER_ADDENDUM_SHA256:
        raise CensusError(f"fiber addendum drift: {fiber_addendum_hash}")
    certificate_hash = sha256_path(CERTIFICATE)
    if certificate_hash != EXPECTED_CERTIFICATE_SHA256:
        raise CensusError(f"source certificate drift: {certificate_hash}")
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    if document.get("n") != OLD_N:
        raise CensusError("source certificate arity drift")
    raw_terms = document.get("terms")
    if not isinstance(raw_terms, list) or len(raw_terms) != EXPECTED_SOURCE_TERMS:
        raise CensusError("source term census drift")
    terms: list[SourceTerm] = []
    for index, raw in enumerate(raw_terms):
        pair_raw = raw.get("pair")
        if not isinstance(pair_raw, list) or len(pair_raw) != 2:
            raise CensusError(f"malformed pair at source term {index}")
        pair = (canonical_side(pair_raw[0]), canonical_side(pair_raw[1]))
        if len(pair[0]) != 4 or len(pair[1]) != 4:
            raise CensusError(f"source degree drift at term {index}")
        if any(not (1 <= u <= v <= OLD_N) for side in pair for u, v in side):
            raise CensusError(f"source label drift at term {index}")
        terms.append(SourceTerm(index, Fraction(raw["coefficient"]), pair))
    return terms


def cancelled_pair(pair: Pair) -> Pair:
    left = Counter(pair[0])
    right = Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    negative = tuple(sorted(left.elements()))
    positive = tuple(sorted(right.elements()))
    if len(negative) != len(positive):
        raise CensusError("common-edge cancellation unbalanced signed masses")
    return negative, positive


def extension_pair(term: SourceTerm, left_edge: Edge, right_edge: Edge) -> Pair:
    return (
        tuple(sorted(term.pair[0] + (left_edge,))),
        tuple(sorted(term.pair[1] + (right_edge,))),
    )


def incidence_data(pair: Pair) -> tuple[dict[int, set[int]], list[set[int]], dict[int, str]]:
    """Return a lossless typed incidence graph for the cancelled signed pair."""

    negative, positive = cancelled_pair(pair)
    adjacency: dict[int, set[int]] = {index: set() for index in range(N + 2)}
    kinds: dict[int, str] = {index: "coordinate" for index in range(N)}
    negative_branch = N
    positive_branch = N + 1
    kinds[negative_branch] = "branch"
    kinds[positive_branch] = "branch"
    occurrences: list[int] = []
    for branch, side in ((negative_branch, negative), (positive_branch, positive)):
        for u, v in side:
            occurrence = len(adjacency)
            adjacency[occurrence] = {branch, u - 1}
            adjacency[branch].add(occurrence)
            adjacency[u - 1].add(occurrence)
            if v != u:
                adjacency[occurrence].add(v - 1)
                adjacency[v - 1].add(occurrence)
            kinds[occurrence] = "edge-occurrence"
            occurrences.append(occurrence)
    coloring = [set(range(N)), {negative_branch, positive_branch}]
    if occurrences:
        coloring.append(set(occurrences))
    if set().union(*coloring) != set(adjacency):
        raise CensusError("incidence coloring is not a partition")
    return adjacency, coloring, kinds


def signed_certificate(pair: Pair) -> bytes:
    adjacency, coloring, _kinds = incidence_data(pair)
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={node: sorted(neighbours) for node, neighbours in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph)


def networkx_graph(pair: Pair) -> nx.Graph:
    adjacency, _coloring, kinds = incidence_data(pair)
    graph = nx.Graph()
    for node, kind in kinds.items():
        graph.add_node(node, kind=kind)
    for node, neighbours in adjacency.items():
        for neighbour in neighbours:
            if node < neighbour:
                graph.add_edge(node, neighbour)
    return graph


def relabel_pair(pair: Pair, permutation: dict[int, int]) -> Pair:
    return tuple(
        canonical_side((permutation[u], permutation[v]) for u, v in side)
        for side in pair
    )  # type: ignore[return-value]


def all_nonloop_edges() -> tuple[Edge, ...]:
    return tuple(combinations(range(1, N + 1), 2))


NONLOOP_EDGES = all_nonloop_edges()
DISJOINT_EDGE_PAIRS = tuple(
    (left, right)
    for left in NONLOOP_EDGES
    for right in NONLOOP_EDGES
    if not set(left).intersection(right)
)
SHARED_DISTINCT_EDGE_PAIRS = tuple(
    (left, right)
    for left in NONLOOP_EDGES
    for right in NONLOOP_EDGES
    if left != right and len(set(left).intersection(right)) == 1
)


def add_local(
    classes: dict[bytes, LocalClass],
    samples: list[tuple[bytes, Edge, Edge, Edge, Edge]],
    certificate: bytes,
    left_edge: Edge,
    right_edge: Edge,
) -> None:
    existing = classes.get(certificate)
    if existing is None:
        classes[certificate] = LocalClass(1, left_edge, right_edge)
        return
    existing.count += 1
    if len(samples) < VF2_SAMPLES_PER_FAMILY:
        samples.append(
            (
                certificate,
                existing.left_edge,
                existing.right_edge,
                left_edge,
                right_edge,
            )
        )


def census_source_term(term: SourceTerm) -> SliceResult:
    disjoint: dict[bytes, LocalClass] = {}
    shared: dict[bytes, LocalClass] = {}
    disjoint_samples: list[tuple[bytes, Edge, Edge, Edge, Edge]] = []
    shared_samples: list[tuple[bytes, Edge, Edge, Edge, Edge]] = []
    for left_edge, right_edge in DISJOINT_EDGE_PAIRS:
        certificate = signed_certificate(extension_pair(term, left_edge, right_edge))
        add_local(disjoint, disjoint_samples, certificate, left_edge, right_edge)
    for left_edge, right_edge in SHARED_DISTINCT_EDGE_PAIRS:
        certificate = signed_certificate(extension_pair(term, left_edge, right_edge))
        add_local(shared, shared_samples, certificate, left_edge, right_edge)
    return SliceResult(
        term_index=term.index,
        disjoint=disjoint,
        shared=shared,
        disjoint_duplicate_samples=disjoint_samples,
        shared_duplicate_samples=shared_samples,
        disjoint_raw=len(DISJOINT_EDGE_PAIRS),
        shared_raw=len(SHARED_DISTINCT_EDGE_PAIRS),
    )


def merge_local_classes(
    global_counts: dict[bytes, int],
    global_representatives: dict[bytes, Descriptor],
    global_fibers: dict[bytes, list[FiberEntry]],
    vf2_samples: list[tuple[bytes, Descriptor, Descriptor]],
    term_index: int,
    local: dict[bytes, LocalClass],
    local_samples: list[tuple[bytes, Edge, Edge, Edge, Edge]],
) -> None:
    for certificate, item in local.items():
        candidate = (term_index, item.left_edge, item.right_edge)
        representative = global_representatives.get(certificate)
        if representative is None:
            global_representatives[certificate] = candidate
        elif len(vf2_samples) < VF2_SAMPLES_PER_FAMILY:
            vf2_samples.append((certificate, representative, candidate))
        global_counts[certificate] = global_counts.get(certificate, 0) + item.count
        global_fibers.setdefault(certificate, []).append(
            (term_index, item.count, item.left_edge, item.right_edge)
        )
    for certificate, rep_left, rep_right, candidate_left, candidate_right in local_samples:
        if len(vf2_samples) >= VF2_SAMPLES_PER_FAMILY:
            break
        vf2_samples.append(
            (
                certificate,
                (term_index, rep_left, rep_right),
                (term_index, candidate_left, candidate_right),
            )
        )


def star_census(
    terms: Sequence[SourceTerm],
) -> tuple[dict[bytes, int], dict[bytes, Descriptor], list[tuple[bytes, Descriptor, Descriptor]]]:
    counts: dict[bytes, int] = {}
    representatives: dict[bytes, Descriptor] = {}
    samples: list[tuple[bytes, Descriptor, Descriptor]] = []
    for term in terms:
        for left_endpoint in range(1, N + 1):
            left_edge = (min(left_endpoint, N), max(left_endpoint, N))
            for right_endpoint in range(1, N + 1):
                right_edge = (min(right_endpoint, N), max(right_endpoint, N))
                certificate = signed_certificate(
                    extension_pair(term, left_edge, right_edge)
                )
                candidate = (term.index, left_edge, right_edge)
                representative = representatives.get(certificate)
                if representative is None:
                    representatives[certificate] = candidate
                elif len(samples) < VF2_SAMPLES_PER_FAMILY:
                    samples.append((certificate, representative, candidate))
                counts[certificate] = counts.get(certificate, 0) + 1
    return counts, representatives, samples


def pair_from_descriptor(terms: Sequence[SourceTerm], descriptor: Descriptor) -> Pair:
    term_index, left_edge, right_edge = descriptor
    return extension_pair(terms[term_index], left_edge, right_edge)


def metamorphic_controls(terms: Sequence[SourceTerm]) -> dict[str, object]:
    witness = extension_pair(terms[137], (7, 8), (9, 10))
    certificate = signed_certificate(witness)
    permutation = {label: N + 1 - label for label in range(1, N + 1)}
    if signed_certificate(relabel_pair(witness, permutation)) != certificate:
        raise CensusError("S11 relabeling changed a signed certificate")
    if signed_certificate((witness[1], witness[0])) != certificate:
        raise CensusError("global branch swap changed a signed certificate")

    multiplicity_base = extension_pair(terms[137], (7, 8), (9, 10))
    multiplicity_mutant = extension_pair(
        terms[137], terms[137].pair[0][0], (9, 10)
    )
    if signed_certificate(multiplicity_mutant) == signed_certificate(multiplicity_base):
        raise CensusError("edge-multiplicity mutant escaped the incidence certificate")

    loop_witness = extension_pair(terms[137], (7, 7), (9, 10))
    nonloop_witness = extension_pair(terms[137], (7, 8), (9, 10))
    if signed_certificate(loop_witness) == signed_certificate(nonloop_witness):
        raise CensusError("loop/nonloop mutant escaped the incidence certificate")

    return {
        "source_term": 137,
        "relabel_permutation": [permutation[label] for label in range(1, N + 1)],
        "relabel_invariant": True,
        "branch_swap_invariant": True,
        "edge_multiplicity_mutant_rejected": True,
        "loop_nonloop_mutant_rejected": True,
        "witness_certificate_sha256": hashlib.sha256(certificate).hexdigest(),
    }


def verify_vf2_samples(
    terms: Sequence[SourceTerm],
    family: str,
    samples: Sequence[tuple[bytes, Descriptor, Descriptor]],
) -> dict[str, object]:
    if len(samples) != VF2_SAMPLES_PER_FAMILY:
        raise CensusError(
            f"{family} produced {len(samples)} VF2 samples; expected "
            f"{VF2_SAMPLES_PER_FAMILY}"
        )
    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    digest = hashlib.sha256()
    for certificate, representative, candidate in samples:
        representative_pair = pair_from_descriptor(terms, representative)
        candidate_pair = pair_from_descriptor(terms, candidate)
        if signed_certificate(representative_pair) != certificate:
            raise CensusError(f"{family} representative certificate drift")
        if signed_certificate(candidate_pair) != certificate:
            raise CensusError(f"{family} candidate certificate drift")
        if not nx.is_isomorphic(
            networkx_graph(representative_pair),
            networkx_graph(candidate_pair),
            node_match=node_match,
        ):
            raise CensusError(f"{family} pynauty class failed typed-incidence VF2")
        digest.update(
            canonical_bytes(
                {
                    "certificate_sha256": hashlib.sha256(certificate).hexdigest(),
                    "representative": serialize_descriptor(representative),
                    "candidate": serialize_descriptor(candidate),
                }
            )
        )
    return {
        "family": family,
        "checks": len(samples),
        "sample_manifest_sha256": digest.hexdigest(),
        "all_isomorphic": True,
    }


def component_count(edges: Iterable[Edge], support: Iterable[int]) -> int:
    vertices = set(support)
    if not vertices:
        return 0
    parent = {vertex: vertex for vertex in vertices}

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for u, v in edges:
        if u == v:
            continue
        root_u = find(u)
        root_v = find(v)
        if root_u != root_v:
            parent[root_v] = root_u
    return len({find(vertex) for vertex in vertices})


def topology_record(pair: Pair) -> dict[str, int]:
    negative, positive = cancelled_pair(pair)
    mass = len(negative)
    support = {vertex for edge in negative + positive for vertex in edge}
    components = component_count(negative + positive, support)
    loop_counts = sorted(
        [
            sum(u == v for u, v in negative),
            sum(u == v for u, v in positive),
        ]
    )
    return {
        "signed_mass": mass,
        "active_vertices": len(support),
        "min_branch_loops": loop_counts[0],
        "max_branch_loops": loop_counts[1],
        "abs_components": components,
        "abs_beta": 2 * mass - len(support) + components,
    }


def topology_key(record: dict[str, int]) -> tuple[int, ...]:
    return tuple(
        record[key]
        for key in (
            "signed_mass",
            "active_vertices",
            "min_branch_loops",
            "max_branch_loops",
            "abs_components",
            "abs_beta",
        )
    )


def topology_from_key(key: tuple[int, ...]) -> dict[str, int]:
    names = (
        "signed_mass",
        "active_vertices",
        "min_branch_loops",
        "max_branch_loops",
        "abs_components",
        "abs_beta",
    )
    return dict(zip(names, key, strict=True))


def serialize_descriptor(descriptor: Descriptor) -> dict[str, object]:
    term_index, left_edge, right_edge = descriptor
    return {
        "source_term": term_index,
        "left_added_edge": list(left_edge),
        "right_added_edge": list(right_edge),
    }


def serialize_source_fiber(
    certificate: bytes,
    fibers: dict[bytes, list[FiberEntry]],
    counts: dict[bytes, int],
    terms: Sequence[SourceTerm],
) -> tuple[dict[str, object], str]:
    entries: list[dict[str, object]] = []
    coefficient_sum = Fraction(0)
    raw_sum = 0
    previous_term = -1
    for term_index, raw_multiplicity, left_edge, right_edge in fibers.get(
        certificate, []
    ):
        if term_index <= previous_term:
            raise CensusError("source fiber order or uniqueness drift")
        previous_term = term_index
        coefficient = terms[term_index].coefficient
        coefficient_weight = coefficient * raw_multiplicity
        coefficient_sum += coefficient_weight
        raw_sum += raw_multiplicity
        entries.append(
            {
                "source_term": term_index,
                "source_coefficient": str(coefficient),
                "raw_multiplicity": raw_multiplicity,
                "representative_left_added_edge": list(left_edge),
                "representative_right_added_edge": list(right_edge),
                "coefficient_times_multiplicity": str(coefficient_weight),
            }
        )
    if raw_sum != counts.get(certificate, 0):
        raise CensusError("source fiber multiplicities do not recover orbit count")
    payload: dict[str, object] = {
        "entries": entries,
        "raw_multiplicity_sum": raw_sum,
        "coefficient_weight_sum": str(coefficient_sum),
    }
    return payload, hashlib.sha256(canonical_bytes(payload)).hexdigest()


def class_size_histogram(counts: dict[bytes, int]) -> dict[str, int]:
    return {str(size): number for size, number in sorted(Counter(counts.values()).items())}


def merge_union_counts(
    disjoint_counts: dict[bytes, int], shared_counts: dict[bytes, int]
) -> dict[bytes, int]:
    union = dict(disjoint_counts)
    for certificate, count in shared_counts.items():
        union[certificate] = union.get(certificate, 0) + count
    return union


def orbit_sort_key(certificate: bytes) -> tuple[bytes, bytes]:
    return hashlib.sha256(certificate).digest(), certificate


def descriptor_for_primary(
    certificate: bytes,
    disjoint_representatives: dict[bytes, Descriptor],
    shared_representatives: dict[bytes, Descriptor],
) -> tuple[str, Descriptor]:
    if certificate in disjoint_representatives:
        return "DISJOINT", disjoint_representatives[certificate]
    return "SHARED_DISTINCT", shared_representatives[certificate]


def write_representative_map(
    path: Path,
    terms: Sequence[SourceTerm],
    disjoint_counts: dict[bytes, int],
    disjoint_representatives: dict[bytes, Descriptor],
    disjoint_fibers: dict[bytes, list[FiberEntry]],
    shared_counts: dict[bytes, int],
    shared_representatives: dict[bytes, Descriptor],
    shared_fibers: dict[bytes, list[FiberEntry]],
    star_counts: dict[bytes, int],
    star_representatives: dict[bytes, Descriptor],
) -> tuple[
    str,
    int,
    str,
    str,
    dict[str, int],
    Counter[tuple[int, ...]],
    Counter[tuple[int, ...]],
]:
    if path.exists():
        raise CensusError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    primary_keys = set(disjoint_counts) | set(shared_counts)
    manifest_digest = hashlib.sha256()
    fiber_manifest_digest = hashlib.sha256()
    fiber_raw_totals = {"DISJOINT": 0, "SHARED_DISTINCT": 0}
    orbit_topology: Counter[tuple[int, ...]] = Counter()
    raw_topology: Counter[tuple[int, ...]] = Counter()
    seen_hashes: set[str] = set()
    try:
        with temporary.open("wb") as raw_handle:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw_handle, mtime=0) as stream:
                header = {
                    "schema": MAP_SCHEMA,
                    "record_type": "header",
                    "source_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
                    "producer_sha256": sha256_path(SCRIPT),
                    "primary_signed_W_orbits": len(primary_keys),
                }
                stream.write(canonical_bytes(header))
                for orbit_index, certificate in enumerate(sorted(primary_keys, key=orbit_sort_key)):
                    class_hash = hashlib.sha256(certificate).hexdigest()
                    if class_hash in seen_hashes:
                        raise CensusError("SHA-256 collision between distinct orbit certificates")
                    seen_hashes.add(class_hash)
                    family, representative = descriptor_for_primary(
                        certificate, disjoint_representatives, shared_representatives
                    )
                    pair = pair_from_descriptor(terms, representative)
                    topology = topology_record(pair)
                    key = topology_key(topology)
                    raw_multiplicity = disjoint_counts.get(certificate, 0) + shared_counts.get(
                        certificate, 0
                    )
                    orbit_topology[key] += 1
                    raw_topology[key] += raw_multiplicity
                    disjoint_fiber, disjoint_fiber_hash = serialize_source_fiber(
                        certificate, disjoint_fibers, disjoint_counts, terms
                    )
                    shared_fiber, shared_fiber_hash = serialize_source_fiber(
                        certificate, shared_fibers, shared_counts, terms
                    )
                    fiber_raw_totals["DISJOINT"] += int(
                        disjoint_fiber["raw_multiplicity_sum"]
                    )
                    fiber_raw_totals["SHARED_DISTINCT"] += int(
                        shared_fiber["raw_multiplicity_sum"]
                    )
                    fiber_manifest_digest.update(
                        canonical_bytes(
                            {
                                "signed_class_sha256": class_hash,
                                "DISJOINT_fiber_sha256": disjoint_fiber_hash,
                                "SHARED_DISTINCT_fiber_sha256": shared_fiber_hash,
                            }
                        )
                    )
                    record: dict[str, object] = {
                        "schema": MAP_SCHEMA,
                        "record_type": "signed_W_orbit",
                        "orbit_index": orbit_index,
                        "signed_class_sha256": class_hash,
                        "memberships": {
                            "DISJOINT": certificate in disjoint_counts,
                            "SHARED_DISTINCT": certificate in shared_counts,
                            "STAR": certificate in star_counts,
                        },
                        "raw_multiplicities": {
                            "DISJOINT": disjoint_counts.get(certificate, 0),
                            "SHARED_DISTINCT": shared_counts.get(certificate, 0),
                            "PRIMARY_UNION": raw_multiplicity,
                            "STAR": star_counts.get(certificate, 0),
                        },
                        "primary_representative_family": family,
                        "primary_representative": serialize_descriptor(representative),
                        "source_coefficient": str(terms[representative[0]].coefficient),
                        "representative_pair": serialize_pair(pair),
                        "source_fibers": {
                            "DISJOINT": disjoint_fiber,
                            "SHARED_DISTINCT": shared_fiber,
                        },
                        "source_fiber_sha256": {
                            "DISJOINT": disjoint_fiber_hash,
                            "SHARED_DISTINCT": shared_fiber_hash,
                        },
                        "topology": topology,
                    }
                    if certificate in star_representatives:
                        record["star_representative"] = serialize_descriptor(
                            star_representatives[certificate]
                        )
                    line = canonical_bytes(record)
                    stream.write(line)
                    manifest_digest.update(line)
            raw_handle.flush()
            os.fsync(raw_handle.fileno())
        temporary.replace(path)
    except BaseException:
        if temporary.exists():
            temporary.unlink()
        raise
    return (
        sha256_path(path),
        path.stat().st_size,
        manifest_digest.hexdigest(),
        fiber_manifest_digest.hexdigest(),
        fiber_raw_totals,
        orbit_topology,
        raw_topology,
    )


def strata_records(
    orbit_topology: Counter[tuple[int, ...]], raw_topology: Counter[tuple[int, ...]]
) -> list[dict[str, int]]:
    records: list[dict[str, int]] = []
    for key in sorted(orbit_topology):
        record = topology_from_key(key)
        record["signed_W_orbits"] = orbit_topology[key]
        record["raw_extensions"] = raw_topology[key]
        records.append(record)
    return records


def portable_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT))
    except ValueError:
        return str(path.resolve())


def generate(map_path: Path, output_path: Path, workers: int) -> dict[str, object]:
    if output_path.exists():
        raise CensusError(f"refusing to overwrite {output_path}")
    started = time.monotonic()
    terms = load_terms()
    controls = metamorphic_controls(terms)

    star_started = time.monotonic()
    star_counts, star_representatives, star_samples = star_census(terms)
    star_seconds = time.monotonic() - star_started
    if sum(star_counts.values()) != EXPECTED_STAR_RAW:
        raise CensusError("STAR raw count drift")
    if len(star_counts) != EXPECTED_STAR_ORBITS:
        raise CensusError(
            f"G-0090 STAR known answer drift: {len(star_counts)} != {EXPECTED_STAR_ORBITS}"
        )

    disjoint_counts: dict[bytes, int] = {}
    shared_counts: dict[bytes, int] = {}
    disjoint_representatives: dict[bytes, Descriptor] = {}
    shared_representatives: dict[bytes, Descriptor] = {}
    disjoint_fibers: dict[bytes, list[FiberEntry]] = {}
    shared_fibers: dict[bytes, list[FiberEntry]] = {}
    disjoint_samples: list[tuple[bytes, Descriptor, Descriptor]] = []
    shared_samples: list[tuple[bytes, Descriptor, Descriptor]] = []
    disjoint_raw = 0
    shared_raw = 0

    primary_started = time.monotonic()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for position, result in enumerate(executor.map(census_source_term, terms, chunksize=1)):
            if result.term_index != position:
                raise CensusError("parallel source order drift")
            merge_local_classes(
                disjoint_counts,
                disjoint_representatives,
                disjoint_fibers,
                disjoint_samples,
                result.term_index,
                result.disjoint,
                result.disjoint_duplicate_samples,
            )
            merge_local_classes(
                shared_counts,
                shared_representatives,
                shared_fibers,
                shared_samples,
                result.term_index,
                result.shared,
                result.shared_duplicate_samples,
            )
            disjoint_raw += result.disjoint_raw
            shared_raw += result.shared_raw
            if (position + 1) % 25 == 0 or position + 1 == len(terms):
                print(
                    f"merged {position + 1}/{len(terms)} source terms; "
                    f"D={len(disjoint_counts):,}, H={len(shared_counts):,}",
                    flush=True,
                )
    primary_seconds = time.monotonic() - primary_started

    if disjoint_raw != EXPECTED_DISJOINT_RAW:
        raise CensusError(f"DISJOINT raw drift: {disjoint_raw}")
    if shared_raw != EXPECTED_SHARED_RAW:
        raise CensusError(f"SHARED_DISTINCT raw drift: {shared_raw}")
    if disjoint_raw + shared_raw != EXPECTED_PRIMARY_RAW:
        raise CensusError("primary raw union drift")

    vf2 = [
        verify_vf2_samples(terms, "STAR", star_samples),
        verify_vf2_samples(terms, "DISJOINT", disjoint_samples),
        verify_vf2_samples(terms, "SHARED_DISTINCT", shared_samples),
    ]

    union_counts = merge_union_counts(disjoint_counts, shared_counts)
    disjoint_keys = set(disjoint_counts)
    shared_keys = set(shared_counts)
    primary_keys = set(union_counts)
    star_keys = set(star_counts)

    map_started = time.monotonic()
    (
        map_hash,
        map_size,
        manifest_hash,
        fiber_manifest_hash,
        fiber_raw_totals,
        orbit_topology,
        raw_topology,
    ) = write_representative_map(
        map_path,
        terms,
        disjoint_counts,
        disjoint_representatives,
        disjoint_fibers,
        shared_counts,
        shared_representatives,
        shared_fibers,
        star_counts,
        star_representatives,
    )
    map_seconds = time.monotonic() - map_started
    if fiber_raw_totals != {
        "DISJOINT": EXPECTED_DISJOINT_RAW,
        "SHARED_DISTINCT": EXPECTED_SHARED_RAW,
    }:
        raise CensusError(f"global source-fiber raw replay failed: {fiber_raw_totals}")

    tractable = (
        len(primary_keys) <= TRACTABLE_ORBIT_LIMIT
        and map_size <= TRACTABLE_MAP_BYTE_LIMIT
    )
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "PASS_TRACTABLE" if tractable else "PASS_LARGE",
        "claim_boundary": (
            "Exact finite signed-W orbit census and overlap gate only. No MAX11 "
            "target value, target rank, fit, coefficient, identity, or obstruction "
            "was computed."
        ),
        "bindings": {
            "source_certificate": portable_path(CERTIFICATE),
            "source_certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
            "preregistration": portable_path(PREREGISTRATION),
            "preregistration_sha256": EXPECTED_PREREGISTRATION_SHA256,
            "fiber_addendum": portable_path(FIBER_ADDENDUM),
            "fiber_addendum_sha256": EXPECTED_FIBER_ADDENDUM_SHA256,
            "producer": portable_path(SCRIPT),
            "producer_sha256": sha256_path(SCRIPT),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "pynauty": getattr(pynauty, "__version__", "unknown"),
            "networkx": nx.__version__,
            "workers": workers,
        },
        "source_terms": len(terms),
        "certificate_semantics": {
            "quotient": "S11 coordinate relabeling and global branch/sign swap",
            "common_edge_occurrences_cancelled": True,
            "inactive_coordinates_retained": N,
            "multiplicity_preserved_by_occurrence_vertices": True,
        },
        "metamorphic_controls": controls,
        "vf2_controls": vf2,
        "star_known_answer_control": {
            "raw_extensions": sum(star_counts.values()),
            "signed_W_orbits": len(star_counts),
            "expected_raw_extensions": EXPECTED_STAR_RAW,
            "expected_signed_W_orbits": EXPECTED_STAR_ORBITS,
            "replayed": True,
            "class_size_histogram": class_size_histogram(star_counts),
        },
        "primary": {
            "raw_extensions": disjoint_raw + shared_raw,
            "signed_W_orbits": len(primary_keys),
            "class_size_histogram": class_size_histogram(union_counts),
            "DISJOINT": {
                "raw_extensions": disjoint_raw,
                "signed_W_orbits": len(disjoint_keys),
                "class_size_histogram": class_size_histogram(disjoint_counts),
            },
            "SHARED_DISTINCT": {
                "raw_extensions": shared_raw,
                "signed_W_orbits": len(shared_keys),
                "class_size_histogram": class_size_histogram(shared_counts),
            },
            "slice_overlap": {
                "both": len(disjoint_keys & shared_keys),
                "DISJOINT_only": len(disjoint_keys - shared_keys),
                "SHARED_DISTINCT_only": len(shared_keys - disjoint_keys),
            },
            "star_overlap": {
                "primary_and_STAR": len(primary_keys & star_keys),
                "primary_outside_STAR": len(primary_keys - star_keys),
                "STAR_outside_primary": len(star_keys - primary_keys),
                "DISJOINT_and_STAR": len(disjoint_keys & star_keys),
                "SHARED_DISTINCT_and_STAR": len(shared_keys & star_keys),
                "DISJOINT_outside_STAR": len(disjoint_keys - star_keys),
                "SHARED_DISTINCT_outside_STAR": len(shared_keys - star_keys),
                "triple_intersection": len(disjoint_keys & shared_keys & star_keys),
            },
            "topology_strata": strata_records(orbit_topology, raw_topology),
        },
        "representative_map": {
            "path": portable_path(map_path),
            "compressed_sha256": map_hash,
            "compressed_bytes": map_size,
            "canonical_record_manifest_sha256": manifest_hash,
            "canonical_source_fiber_manifest_sha256": fiber_manifest_hash,
            "source_fiber_raw_replay": fiber_raw_totals,
            "records": len(primary_keys),
        },
        "tractability_gate": {
            "orbit_limit": TRACTABLE_ORBIT_LIMIT,
            "map_byte_limit": TRACTABLE_MAP_BYTE_LIMIT,
            "observed_orbits": len(primary_keys),
            "observed_map_bytes": map_size,
            "classification": "TRACTABLE" if tractable else "LARGE",
            "registered_next_priority": (
                "DISJOINT outside STAR, then SHARED_DISTINCT outside STAR"
                if tractable
                else "topology-first column generation; no monolithic exact rank"
            ),
        },
        "timing_seconds": {
            "star_control": star_seconds,
            "primary_census": primary_seconds,
            "representative_map": map_seconds,
            "total": time.monotonic() - started,
        },
    }
    output_path.write_bytes(canonical_bytes(report))
    return report


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--map",
        type=Path,
        default=HERE / "degree5_signed_orbit_representatives_v1.jsonl.gz",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "degree5_quotient_census_v1.json",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(8, os.cpu_count() or 1)),
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    if args.workers < 1:
        raise CensusError("workers must be positive")
    report = generate(args.map.resolve(), args.output.resolve(), args.workers)
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
