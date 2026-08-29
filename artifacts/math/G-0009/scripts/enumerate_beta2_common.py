#!/usr/bin/env python3
"""Exactly quotient the preregistered next beta=2 lift family.

Start from each of the 252 full-support two-forest terms in the pinned MAX10
certificate.  Choose one loopless edge wholly inside either forest component
and append that *same* edge to both colours.  The common-edge algebra is exact
pointwise, the degree becomes five per branch, vertex 11 remains ambient and
isolated, and the coloured multigraph has e=10, r=10, c=2, hence beta=2.

This is the smallest algebraically privileged beta=2 slice after the beta=0
cross-component test.  It is not asserted to be a complete beta=2 census.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations
import hashlib
import json
from pathlib import Path
import sys
import time
from typing import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G6 = ROOT / "artifacts/math/G-0006"
sys.path.insert(0, str(G6))

import exact_lift_search as g6  # noqa: E402


N = 11
SCHEMA = "max11-beta2-common-internal-lifts-isomorphism-v1"
Pair = g6.Pair


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pair_list_sha256(pairs: Sequence[Pair]) -> str:
    return sha256_bytes(
        canonical_bytes(
            [
                [[[a, b] for a, b in left], [[a, b] for a, b in right]]
                for left, right in pairs
            ]
        )
    )


def build_family() -> tuple[list[Pair], list[tuple[int, ...]], str, Counter]:
    bases, _same_metadata, _same_digest = g6.build_bases()
    pairs = []
    metadata = []
    component_sizes = Counter()
    for base_index, (term_index, left, right, components) in enumerate(bases):
        component_sizes[tuple(sorted(map(len, components)))] += 1
        for component_index, component in enumerate(components):
            for a, b in combinations(sorted(component), 2):
                edge = (a, b)
                pairs.append((tuple(left) + (edge,), tuple(right) + (edge,)))
                metadata.append((base_index, term_index, component_index, a, b))
    if len(pairs) != 6_740:
        raise AssertionError(len(pairs))
    return pairs, metadata, sha256_bytes(canonical_bytes(metadata)), component_sizes


def validate(pairs: Sequence[Pair]) -> None:
    import networkx as nx

    for raw_index, pair in enumerate(pairs):
        edges = tuple(pair[0]) + tuple(pair[1])
        if len(edges) != 10 or any(a == b for a, b in edges):
            raise AssertionError((raw_index, edges))
        graph = nx.MultiGraph()
        graph.add_edges_from(edges)
        active = graph.number_of_nodes()
        components = nx.number_connected_components(graph)
        beta = graph.number_of_edges() - active + components
        if active != 10 or components != 2 or beta != 2:
            raise AssertionError((raw_index, active, components, beta))


def build_classes() -> dict[str, object]:
    import networkx as nx

    pairs, metadata, metadata_digest, component_sizes = build_family()
    validate(pairs)
    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    buckets: dict[str, list[int]] = defaultdict(list)
    representative_graphs = []
    representatives = []
    raw_to_class = []
    begun = time.time()
    for raw_index, pair in enumerate(pairs):
        graph = g6.incidence_graph(pair)
        wl_hash = nx.weisfeiler_lehman_graph_hash(
            graph, node_attr="kind", iterations=16, digest_size=32
        )
        class_index = None
        for possible_class in buckets[wl_hash]:
            if nx.is_isomorphic(
                graph, representative_graphs[possible_class], node_match=node_match
            ):
                class_index = possible_class
                break
        if class_index is None:
            class_index = len(representatives)
            representatives.append(raw_index)
            representative_graphs.append(graph)
            buckets[wl_hash].append(class_index)
        raw_to_class.append(class_index)
        if (raw_index + 1) % 1000 == 0:
            print(
                f"beta2 quotient raw={raw_index+1}/{len(pairs)} "
                f"classes={len(representatives)} seconds={time.time()-begun:.1f}",
                flush=True,
            )
    class_sizes = [0] * len(representatives)
    for class_index in raw_to_class:
        class_sizes[class_index] += 1
    if sum(class_sizes) != len(pairs):
        raise AssertionError("class census mismatch")
    asymmetric_raw_count = sum(
        count
        * (
            sum(size * (size - 1) // 2 for size in sizes)
            ** 2
        )
        for sizes, count in component_sizes.items()
    )
    if asymmetric_raw_count != 183_064:
        raise AssertionError(asymmetric_raw_count)
    return {
        "schema": SCHEMA,
        "n": N,
        "family": (
            "append one common loopless within-component edge to both colours of each of the "
            "252 full-support MAX10 two-forest terms"
        ),
        "source_certificate_path": str(g6.CERTIFICATE.resolve().relative_to(ROOT)),
        "source_certificate_sha256": sha256_path(g6.CERTIFICATE),
        "base_count": 252,
        "base_component_size_histogram": {
            str(list(sizes)): count for sizes, count in sorted(component_sizes.items())
        },
        "raw_candidate_count": len(pairs),
        "candidate_metadata_sha256": metadata_digest,
        "raw_pair_list_sha256": pair_list_sha256(pairs),
        "topology": {
            "ambient_vertices": 11,
            "active_vertices": 10,
            "ambient_isolates": 1,
            "colored_edges_with_multiplicity": 10,
            "active_components": 2,
            "colored_multigraph_beta": 2,
            "loopless": True,
        },
        "disjointness": (
            "beta=2 distinguishes this family from G-0008 beta=1 and the G-0009 cross family beta=0"
        ),
        "equivalence": "all 11 vertex relabellings and one global A/B colour swap",
        "authority": "NetworkX exact VF2 typed-incidence-graph isomorphism within WL buckets",
        "accelerator": "NetworkX Weisfeiler-Lehman node-attribute hash, 16 iterations",
        "networkx_version": nx.__version__,
        "class_count": len(representatives),
        "representative_raw_indices": representatives,
        "raw_to_class": raw_to_class,
        "class_sizes": class_sizes,
        "next_widening_if_needed": {
            "family": (
                "independent ordered A/B choices of loopless within-component added edges on "
                "the same 252 bases"
            ),
            "raw_candidate_count_before_quotient": asymmetric_raw_count,
        },
        "motivation": (
            "The beta=0 cross family added zero orbit-grid rank to G-0008, while the audited "
            "MAX9 calibration required non-tree corrections. A common internal edge is the "
            "smallest beta=2 topology change enjoying max(U+h,V+h)=h+max(U,V)."
        ),
        "claim_boundary": (
            "This is an exact quotient of a pinned certificate-derived beta=2 slice, not all "
            "abstract beta=2 MAX11 atoms. The common-edge pointwise identity motivates the "
            "operator but does not make this forest-only subset a MAX11 identity."
        ),
    }


def load_classes(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SCHEMA or document.get("n") != N:
        raise ValueError("wrong beta2 class schema")
    pairs, _metadata, metadata_digest, _component_sizes = build_family()
    if document.get("raw_candidate_count") != len(pairs):
        raise ValueError("beta2 raw candidate census mismatch")
    if document.get("candidate_metadata_sha256") != metadata_digest:
        raise ValueError("beta2 metadata digest mismatch")
    if document.get("raw_pair_list_sha256") != pair_list_sha256(pairs):
        raise ValueError("beta2 raw pair digest mismatch")
    if document.get("source_certificate_sha256") != sha256_path(g6.CERTIFICATE):
        raise ValueError("beta2 source certificate digest mismatch")
    representatives = document.get("representative_raw_indices")
    raw_to_class = document.get("raw_to_class")
    if not isinstance(representatives, list) or not isinstance(raw_to_class, list):
        raise ValueError("malformed beta2 quotient maps")
    if len(representatives) != document.get("class_count") or len(raw_to_class) != len(pairs):
        raise ValueError("beta2 quotient map length mismatch")
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = build_classes()
    raw = canonical_bytes(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(
        f"{args.output} bytes={len(raw)} sha256={sha256_bytes(raw)} "
        f"classes={document['class_count']}",
        flush=True,
    )


if __name__ == "__main__":
    main()
