#!/usr/bin/env python3
"""Exact orbit/support census for the MAX8(k=3)->MAX9(k=4) edge lift."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
import os
from pathlib import Path
import sys
from typing import Iterable, Sequence

import networkx as nx
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
EXPECTED_HASHES = {
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT9: "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
}
N = 9
SOURCE_N = 8
EXPECTED_SOURCE_TERMS = 69
EXPECTED_TARGET_TERMS = 337
EXPECTED_RAW = EXPECTED_SOURCE_TERMS * 45 * 45
SCHEMA = "max11-g0115-max8-max9-parity-lift-census-v1"
MAP_SCHEMA = "max11-g0115-max8-max9-parity-lift-representatives-v1"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class CensusError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CensusError(message)


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_side(raw: Iterable[Sequence[int]]) -> Side:
    return tuple(sorted((min(map(int, edge)), max(map(int, edge))) for edge in raw))


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[u, v] for u, v in side] for side in pair]


@dataclass(frozen=True)
class Term:
    index: int
    coefficient: Fraction
    pair: Pair


def load_certificate(path: Path, n: int, degree: int, expected_terms: int) -> list[Term]:
    observed = sha256(path)
    require(observed == EXPECTED_HASHES[path], f"certificate drift: {path}: {observed}")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n and isinstance(document.get("terms"), list), "malformed certificate")
    terms: list[Term] = []
    for index, raw in enumerate(document["terms"]):
        pair_raw = raw.get("pair")
        require(isinstance(pair_raw, list) and len(pair_raw) == 2, f"bad pair {index}")
        pair = (canonical_side(pair_raw[0]), canonical_side(pair_raw[1]))
        require(len(pair[0]) == len(pair[1]) == degree, f"degree drift {index}")
        require(all(1 <= u <= v <= n for side in pair for u, v in side), f"endpoint drift {index}")
        terms.append(Term(index, Fraction(raw["coefficient"]), pair))
    require(len(terms) == expected_terms, f"term count drift: {len(terms)}")
    return terms


def cancelled(pair: Pair) -> Pair:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    return tuple(sorted(left.elements())), tuple(sorted(right.elements()))


def occurrence_certificate(first: Side, second: Side, global_swap: bool) -> bytes:
    def one(a: Side, b: Side) -> bytes:
        adjacency: dict[int, set[int]] = {i: set() for i in range(N)}
        first_nodes: list[int] = []
        second_nodes: list[int] = []
        for bucket, side in ((first_nodes, a), (second_nodes, b)):
            for u, v in side:
                node = len(adjacency)
                adjacency[node] = set()
                bucket.append(node)
                for coordinate in {u - 1, v - 1}:
                    adjacency[node].add(coordinate)
                    adjacency[coordinate].add(node)
        coloring = [set(range(N))]
        if first_nodes:
            coloring.append(set(first_nodes))
        if second_nodes:
            coloring.append(set(second_nodes))
        graph = pynauty.Graph(
            number_of_vertices=len(adjacency),
            directed=False,
            adjacency_dict={node: sorted(neighbors) for node, neighbors in adjacency.items()},
            vertex_coloring=coloring,
        )
        return pynauty.certificate(graph)

    direct = one(first, second)
    return min(direct, one(second, first)) if global_swap else direct


def pair_certificate(pair: Pair) -> bytes:
    return min(
        occurrence_certificate(pair[0], pair[1], False),
        occurrence_certificate(pair[1], pair[0], False),
    )


def signed_certificate(pair: Pair) -> bytes:
    negative, positive = cancelled(pair)
    require(len(negative) == len(positive), "unbalanced cancellation")
    return occurrence_certificate(negative, positive, True)


def relation(left: Edge, right: Edge) -> str:
    if left[0] == left[1] or right[0] == right[1]:
        return "HAS_LOOP"
    if left == right:
        return "COMMON_NONLOOP"
    if set(left) & set(right):
        return "SHARE_DISTINCT"
    return "DISJOINT"


def typed_graph(pair: Pair, swap: bool = False) -> nx.Graph:
    first, second = (pair[1], pair[0]) if swap else pair
    graph = nx.Graph()
    for coordinate in range(1, N + 1):
        graph.add_node(("c", coordinate), color="coordinate")
    for side_name, side in (("negative", first), ("positive", second)):
        for occurrence, (u, v) in enumerate(side):
            node = (side_name, occurrence)
            graph.add_node(node, color=side_name)
            graph.add_edge(node, ("c", u))
            if v != u:
                graph.add_edge(node, ("c", v))
    return graph


def vf2_equivalent(first: Pair, second: Pair, allow_swap: bool) -> bool:
    match = nx.algorithms.isomorphism.categorical_node_match("color", "")
    direct = nx.is_isomorphic(typed_graph(first), typed_graph(second), node_match=match)
    return direct or (allow_swap and nx.is_isomorphic(typed_graph(first), typed_graph(second, True), node_match=match))


def signed_pair(pair: Pair) -> Pair:
    return cancelled(pair)


def relabel_pair(pair: Pair, permutation: dict[int, int]) -> Pair:
    return tuple(
        tuple(sorted((min(permutation[u], permutation[v]), max(permutation[u], permutation[v])) for u, v in side))
        for side in pair
    )  # type: ignore[return-value]


def atomic_gzip_jsonl(path: Path, records: Iterable[dict[str, object]]) -> str:
    temporary = path.with_name(path.name + ".partial")
    require(not path.exists() and not temporary.exists(), f"output exists: {path}")
    digest = hashlib.sha256()
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            for record in records:
                line = canonical(record)
                compressed.write(line)
                digest.update(line)
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)
    return digest.hexdigest()


def atomic_json(path: Path, value: object) -> None:
    require(not path.exists(), f"output exists: {path}")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def self_test() -> dict[str, object]:
    pair: Pair = (((1, 2), (1, 2), (3, 4), (5, 5)), ((2, 3), (4, 5), (6, 7), (8, 9)))
    permutation = {index: ((index + 3) % N) + 1 for index in range(1, N + 1)}
    relabelled = relabel_pair(pair, permutation)
    require(pair_certificate(pair) == pair_certificate(relabelled), "pair relabelling failed")
    require(pair_certificate(pair) == pair_certificate((pair[1], pair[0])), "pair swap failed")
    require(signed_certificate(pair) == signed_certificate(relabelled), "signed relabelling failed")
    require(signed_certificate(pair) == signed_certificate((pair[1], pair[0])), "signed swap failed")
    require(vf2_equivalent(pair, relabelled, True), "VF2 relabelling failed")
    loop_mutant: Pair = (tuple(sorted(pair[0][:-1] + ((5, 6),))), pair[1])
    require(pair_certificate(pair) != pair_certificate(loop_mutant), "loop/nonloop mutation missed")
    require(relation((1, 2), (2, 3)) == "SHARE_DISTINCT", "share classifier")
    require(relation((1, 2), (3, 4)) == "DISJOINT", "disjoint classifier")
    return {
        "pair_relabelling_and_swap": True,
        "signed_relabelling_and_swap": True,
        "vf2_relabelling": True,
        "loop_nonloop_mutation_rejected": True,
        "relation_classifier": True,
    }


def generate(map_path: Path, output_path: Path) -> dict[str, object]:
    script_hash = sha256(SCRIPT)
    controls = self_test()
    source = load_certificate(CERT8, SOURCE_N, 3, EXPECTED_SOURCE_TERMS)
    target = load_certificate(CERT9, N, 4, EXPECTED_TARGET_TERMS)
    edges = tuple(combinations_with_replacement(range(1, N + 1), 2))
    require(len(edges) == 45, "edge count drift")

    target_pair: dict[bytes, list[int]] = {}
    target_signed: dict[bytes, list[int]] = {}
    for term in target:
        target_pair.setdefault(pair_certificate(term.pair), []).append(term.index)
        target_signed.setdefault(signed_certificate(term.pair), []).append(term.index)

    pair_classes: set[bytes] = set()
    signed_reps: dict[bytes, dict[str, object]] = {}
    signed_pair_reps: dict[bytes, Pair] = {}
    signed_multiplicity: Counter[bytes] = Counter()
    pair_multiplicity: Counter[bytes] = Counter()
    relation_raw: Counter[str] = Counter()
    relation_signed: dict[str, set[bytes]] = {
        name: set() for name in ("SHARE_DISTINCT", "DISJOINT", "COMMON_NONLOOP", "HAS_LOOP")
    }
    collision_checks = 0
    collision_failures = 0
    raw_digest = hashlib.sha256()
    raw_count = 0

    for term in source:
        for left in edges:
            for right in edges:
                pair: Pair = (
                    tuple(sorted(term.pair[0] + (left,))),
                    tuple(sorted(term.pair[1] + (right,))),
                )
                kind = relation(left, right)
                descriptor = {
                    "source_term": term.index,
                    "left_added_edge": list(left),
                    "right_added_edge": list(right),
                    "relation": kind,
                }
                raw_digest.update(canonical(descriptor))
                pcert = pair_certificate(pair)
                scert = signed_certificate(pair)
                pair_classes.add(pcert)
                relation_signed[kind].add(scert)
                relation_raw[kind] += 1
                pair_multiplicity[pcert] += 1
                signed_multiplicity[scert] += 1
                if scert not in signed_reps:
                    signed_reps[scert] = {**descriptor, "pair": serialize_pair(pair)}
                    signed_pair_reps[scert] = signed_pair(pair)
                elif collision_checks < 128:
                    collision_checks += 1
                    if not vf2_equivalent(signed_pair_reps[scert], signed_pair(pair), True):
                        collision_failures += 1
                raw_count += 1

    require(raw_count == EXPECTED_RAW, f"raw count drift: {raw_count}")
    require(sum(relation_raw.values()) == raw_count, "relation raw reconciliation failed")
    require(sum(signed_multiplicity.values()) == raw_count, "signed multiplicity reconciliation failed")
    require(sum(pair_multiplicity.values()) == raw_count, "pair multiplicity reconciliation failed")
    require(collision_checks == 128 and collision_failures == 0, "VF2 collision control failed")

    lift_pair = pair_classes
    lift_signed = set(signed_reps)
    public_pair = set(target_pair)
    public_signed = set(target_signed)
    pair_missing = sorted(public_pair - lift_pair)
    signed_missing = sorted(public_signed - lift_signed)

    records = [
        {
            "schema": MAP_SCHEMA,
            "record_type": "header",
            "source_certificate_sha256": EXPECTED_HASHES[CERT8],
            "raw_extensions": raw_count,
            "signed_W_orbits": len(signed_reps),
        }
    ]
    for sequence, certificate in enumerate(sorted(signed_reps)):
        records.append({
            "schema": MAP_SCHEMA,
            "record_type": "signed_W_representative",
            "sequence": sequence,
            "signed_certificate_sha256": hashlib.sha256(certificate).hexdigest(),
            "raw_multiplicity": signed_multiplicity[certificate],
            "relations": sorted(name for name, values in relation_signed.items() if certificate in values),
            "representative": signed_reps[certificate],
            "in_public_MAX9_signed_support": certificate in public_signed,
            "public_term_indices": target_signed.get(certificate, []),
        })
    map_digest = atomic_gzip_jsonl(map_path, records)

    pair_containment = not pair_missing
    signed_containment = not signed_missing
    result = (
        "COMPLETE_PUBLIC_PAIR_SUPPORT_CONTAINMENT"
        if pair_containment
        else "COMPLETE_PUBLIC_SIGNED_W_SUPPORT_CONTAINMENT"
        if signed_containment
        else "PARTIAL_PUBLIC_SUPPORT_OVERLAP"
    )
    report = {
        "schema": SCHEMA,
        "result": result,
        "claim_boundary": (
            "Exact finite MAX8-to-MAX9 arbitrary-edge lift census only. Complete signed-W "
            "support containment would still require an explicit common-padding correction "
            "and global replay; partial overlap is not target membership. No MAX11 or "
            "unrestricted-network claim follows."
        ),
        "bindings": {
            "script_sha256_at_start": script_hash,
            "max8_sha256": EXPECTED_HASHES[CERT8],
            "max9_sha256": EXPECTED_HASHES[CERT9],
        },
        "source": {"n": SOURCE_N, "degree": 3, "terms": len(source)},
        "target_comparison": {
            "n": N,
            "degree": 4,
            "terms": len(target),
            "unique_pair_template_orbits": len(public_pair),
            "unique_signed_W_orbits": len(public_signed),
        },
        "lift": {
            "edge_choices_per_branch": len(edges),
            "raw_extensions": raw_count,
            "raw_descriptor_sha256": raw_digest.hexdigest(),
            "pair_template_orbits": len(lift_pair),
            "signed_W_orbits": len(lift_signed),
            "pair_class_size_histogram": dict(sorted(Counter(pair_multiplicity.values()).items())),
            "signed_class_size_histogram": dict(sorted(Counter(signed_multiplicity.values()).items())),
            "relation_raw_counts": dict(sorted(relation_raw.items())),
            "relation_signed_W_orbits": {name: len(values) for name, values in sorted(relation_signed.items())},
            "share_disjoint_signed_intersection": len(relation_signed["SHARE_DISTINCT"] & relation_signed["DISJOINT"]),
        },
        "overlap": {
            "public_pair_orbits_in_lift": len(public_pair & lift_pair),
            "public_pair_orbits_missing": len(pair_missing),
            "public_pair_missing_certificate_sha256s": [hashlib.sha256(value).hexdigest() for value in pair_missing],
            "lift_pair_orbits_outside_public": len(lift_pair - public_pair),
            "public_signed_W_orbits_in_lift": len(public_signed & lift_signed),
            "public_signed_W_orbits_missing": len(signed_missing),
            "public_signed_missing_certificate_sha256s": [hashlib.sha256(value).hexdigest() for value in signed_missing],
            "lift_signed_W_orbits_outside_public": len(lift_signed - public_signed),
            "complete_pair_support_containment": pair_containment,
            "complete_signed_W_support_containment": signed_containment,
            "public_terms_whose_signed_W_occurs": sum(
                len(indices) for certificate, indices in target_signed.items() if certificate in lift_signed
            ),
        },
        "representative_map": {
            "path": str(map_path.relative_to(ROOT)),
            "compressed_sha256": sha256(map_path),
            "canonical_jsonl_sha256": map_digest,
        },
        "controls": {
            **controls,
            "raw_reconciliation": True,
            "class_multiplicity_reconciliation": True,
            "vf2_collision_checks": collision_checks,
            "vf2_collision_failures": collision_failures,
        },
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    atomic_json(output_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--map", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    require(args.self_test != args.run, "choose exactly one mode")
    if args.self_test:
        require(args.map is None and args.output is None, "self-test refuses outputs")
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(args.map is not None and args.output is not None, "run requires map and output")
    report = generate(args.map.resolve(), args.output.resolve())
    print(json.dumps({
        "result": report["result"],
        "raw": report["lift"]["raw_extensions"],
        "pair_orbits": report["lift"]["pair_template_orbits"],
        "signed_orbits": report["lift"]["signed_W_orbits"],
        "overlap": report["overlap"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
