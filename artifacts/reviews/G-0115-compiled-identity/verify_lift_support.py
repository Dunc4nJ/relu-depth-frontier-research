#!/usr/bin/env python3
"""Fresh-context structural audit of the 395-term G-0115 degree-four support."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import json
import os
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
MAP = ROOT / "artifacts/math/G-0115/parity_lift_representatives_v1.jsonl.gz"
CERTIFICATE = ROOT / "artifacts/math/G-0115/unrestricted_full_semantic_certificate_v1.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
EXPECTED = {
    MAP: "2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148",
    CERTIFICATE: "628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e",
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT9: "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
}
EXPECTED_COLUMN_ORDER = "a8563f4c2d187dd2a4a6714d5f6fb00c12c738ff7cf025f77e4b0898a46e9a82"
N = 9

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class SupportError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SupportError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(payload))
        destination.flush()
        os.fsync(destination.fileno())


def parse_pair(raw: object, n: int = N) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[Side] = []
    for raw_side in raw:
        require(isinstance(raw_side, list), "malformed side")
        side: list[Edge] = []
        for raw_edge in raw_side:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            require(
                all(isinstance(value, int) and not isinstance(value, bool) for value in raw_edge),
                "noninteger endpoint",
            )
            first, second = raw_edge
            require(1 <= first <= second <= n, "endpoint/order outside arity")
            side.append((first, second))
        sides.append(tuple(sorted(side)))
    require(len(sides[0]) == len(sides[1]), "unbalanced branch degree")
    return sides[0], sides[1]


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[first, second] for first, second in side] for side in pair]


def load_terms(path: Path, n: int, degree: int) -> list[tuple[Fraction, Pair]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n and isinstance(document.get("terms"), list), "certificate schema drift")
    terms = []
    for raw in document["terms"]:
        coefficient = Fraction(raw["coefficient"])
        pair = parse_pair(raw["pair"], n)
        require(len(pair[0]) == degree, "certificate degree drift")
        terms.append((coefficient, pair))
    return terms


def cancel(pair: Pair) -> Pair:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    return tuple(sorted(left.elements())), tuple(sorted(right.elements()))


def signed_graph(pair: Pair, *, swap: bool = False) -> nx.Graph:
    negative, positive = cancel(pair)
    if swap:
        negative, positive = positive, negative
    graph = nx.Graph()
    for coordinate in range(1, N + 1):
        graph.add_node(("coordinate", coordinate), color="coordinate")
    for color, side in (("negative", negative), ("positive", positive)):
        for occurrence, (first, second) in enumerate(side):
            node = (color, occurrence)
            graph.add_node(node, color=color)
            graph.add_edge(node, ("coordinate", first))
            if second != first:
                graph.add_edge(node, ("coordinate", second))
    return graph


def graph_invariant(graph: nx.Graph) -> tuple[tuple[str, int], ...]:
    return tuple(sorted((str(data["color"]), int(graph.degree(node))) for node, data in graph.nodes(data=True)))


def signed_invariant(pair: Pair) -> tuple[tuple[str, int], ...]:
    return min(graph_invariant(signed_graph(pair)), graph_invariant(signed_graph(pair, swap=True)))


NODE_MATCH = nx.algorithms.isomorphism.categorical_node_match("color", "")


def public_matches(pair: Pair, candidates: Sequence[tuple[int, nx.Graph, nx.Graph]]) -> list[int]:
    graph = signed_graph(pair)
    matches = []
    for index, direct, swapped in candidates:
        if nx.is_isomorphic(graph, direct, node_match=NODE_MATCH) or nx.is_isomorphic(
            graph, swapped, node_match=NODE_MATCH
        ):
            matches.append(index)
    return matches


def graph_features(pair: Pair) -> tuple[object, ...]:
    negative, positive = cancel(pair)
    active = sorted({vertex for side in (negative, positive) for edge in side for vertex in edge})
    absolute_degrees: Counter[int] = Counter()
    branch_degrees = [Counter(), Counter()]
    for branch_index, side in enumerate((negative, positive)):
        for first, second in side:
            absolute_degrees[first] += 1
            branch_degrees[branch_index][first] += 1
            if second != first:
                absolute_degrees[second] += 1
                branch_degrees[branch_index][second] += 1
    parent = {vertex: vertex for vertex in active}

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for side in (negative, positive):
        for first, second in side:
            if first != second:
                root_first, root_second = find(first), find(second)
                if root_first != root_second:
                    parent[root_second] = root_first
    components = len({find(vertex) for vertex in active}) if active else 0
    mass = len(negative)
    beta = 2 * mass - len(active) + components
    absolute = tuple(sorted(absolute_degrees.values(), reverse=True))
    signed = tuple(
        sorted(tuple(sorted(branch_degrees[index].values(), reverse=True)) for index in range(2))
    )
    loops = tuple(sorted(sum(first == second for first, second in side) for side in (negative, positive)))
    return mass, len(active), components, beta, absolute, signed, loops


def padded_l1(first: Sequence[int], second: Sequence[int]) -> int:
    size = max(len(first), len(second))
    return sum(
        abs((first[index] if index < len(first) else 0) - (second[index] if index < len(second) else 0))
        for index in range(size)
    )


def feature_distance(first: tuple[object, ...], second: tuple[object, ...]) -> tuple[int, ...]:
    f_mass, f_active, f_components, f_beta, f_abs, f_signed, f_loops = first
    s_mass, s_active, s_components, s_beta, s_abs, s_signed, s_loops = second
    direct = padded_l1(f_signed[0], s_signed[0]) + padded_l1(f_signed[1], s_signed[1])
    swapped = padded_l1(f_signed[0], s_signed[1]) + padded_l1(f_signed[1], s_signed[0])
    return (
        abs(f_mass - s_mass),
        abs(f_active - s_active),
        abs(f_components - s_components),
        abs(f_beta - s_beta),
        padded_l1(f_abs, s_abs),
        min(direct, swapped),
        padded_l1(f_loops, s_loops),
    )


def load_map() -> tuple[dict[str, object], list[dict[str, object]]]:
    with gzip.open(MAP, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        records = [json.loads(line) for line in source]
    require(header.get("signed_W_orbits") == 22_666 and len(records) == 22_666, "map census drift")
    require([record.get("sequence") for record in records] == list(range(22_666)), "map sequence drift")
    return header, records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    script_hash = sha256(SCRIPT)
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"input binding drift: {observed}")
    source_terms = load_terms(CERT8, 8, 3)
    public_terms = load_terms(CERT9, 9, 4)
    header, records = load_map()
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    certificate_terms = document.get("terms")
    require(isinstance(certificate_terms, list) and len(certificate_terms) == 395, "support census drift")

    by_hash: dict[str, dict[str, object]] = {}
    raw_reconstruction_count = 0
    for record in records:
        digest = str(record["signed_certificate_sha256"])
        require(digest not in by_hash, "duplicate signed-class hash in map")
        by_hash[digest] = record
        representative = record["representative"]
        source_index = int(representative["source_term"])
        require(0 <= source_index < len(source_terms), "source-term index outside MAX8 certificate")
        source_pair = source_terms[source_index][1]
        left_edge = tuple(map(int, representative["left_added_edge"]))
        right_edge = tuple(map(int, representative["right_added_edge"]))
        reconstructed: Pair = (
            tuple(sorted(source_pair[0] + (left_edge,))),
            tuple(sorted(source_pair[1] + (right_edge,))),
        )
        require(reconstructed == parse_pair(representative["pair"]), "representative is not its claimed raw lift")
        raw_reconstruction_count += 1

    public_buckets: dict[tuple[tuple[str, int], ...], list[tuple[int, nx.Graph, nx.Graph]]] = defaultdict(list)
    for index, (_coefficient, pair) in enumerate(public_terms):
        public_buckets[signed_invariant(pair)].append((index, signed_graph(pair), signed_graph(pair, swap=True)))

    group_counts: Counter[str] = Counter()
    retained_matches = 0
    repair_nonmatches = 0
    supported_sequences: set[int] = set()
    supported_hashes: set[str] = set()
    supported_columns: set[int] = set()
    for position, term in enumerate(certificate_terms):
        require(isinstance(term, dict), f"support term {position} malformed")
        pair = parse_pair(term["pair"])
        require(len(pair[0]) == 4, "support term is not degree four")
        digest = str(term["signed_certificate_sha256"])
        record = by_hash.get(digest)
        require(record is not None, "support signed class absent from lift map")
        require(parse_pair(record["representative"]["pair"]) == pair, "support pair differs from map representative")
        require(int(record["sequence"]) == int(term["representative_sequence"]), "support sequence mismatch")
        group = str(term["group"])
        group_counts[group] += 1
        matches = public_matches(pair, public_buckets.get(signed_invariant(pair), []))
        if group == "retained":
            require(matches, "retained support term is not in public signed-W support")
            require(matches == list(map(int, record["public_term_indices"])), "retained public-index set mismatch")
            retained_matches += 1
        elif group == "repair":
            require(not matches, "repair support term is actually in public signed-W support")
            require(not record["public_term_indices"], "repair record carries public term index")
            repair_nonmatches += 1
        else:
            fail_message = f"unknown support group {group}"
            raise SupportError(fail_message)
        sequence = int(term["representative_sequence"])
        column = int(term["column_index"])
        require(sequence not in supported_sequences and digest not in supported_hashes and column not in supported_columns,
                "duplicate support identity")
        supported_sequences.add(sequence)
        supported_hashes.add(digest)
        supported_columns.add(column)

    require(group_counts == Counter({"retained": 328, "repair": 67}), "support group counts drift")
    retained = [record for record in records if record["public_term_indices"]]
    repair = [record for record in records if not record["public_term_indices"]]
    require(len(retained) == 328 and len(repair) == 22_338, "full map partition drift")
    present_public = {int(index) for record in retained for index in record["public_term_indices"]}
    missing_public = [pair for index, (_coefficient, pair) in enumerate(public_terms) if index not in present_public]
    require(len(missing_public) == 9, "missing public support count drift")
    missing_features = [graph_features(pair) for pair in missing_public]
    for record in repair:
        feature = graph_features(parse_pair(record["representative"]["pair"]))
        record["audit_topology_distance"] = min(
            feature_distance(feature, target_feature) for target_feature in missing_features
        )
    repair.sort(
        key=lambda record: (
            tuple(record["audit_topology_distance"]),
            str(record["signed_certificate_sha256"]),
        )
    )
    order = [
        {"group": "retained", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in retained
    ] + [
        {"group": "repair", "signed_certificate_sha256": record["signed_certificate_sha256"]}
        for record in repair
    ]
    observed_order_hash = canonical_sha(order)
    require(observed_order_hash == EXPECTED_COLUMN_ORDER, "independent column order hash mismatch")
    for term in certificate_terms:
        column = int(term["column_index"])
        require(0 <= column < len(order), "support column outside complete family")
        require(
            order[column]
            == {
                "group": term["group"],
                "signed_certificate_sha256": term["signed_certificate_sha256"],
            },
            "support term does not occupy claimed complete-family column",
        )

    # Potency: a one-edge corruption of the first supported raw lift must cease
    # to equal the exact representative stored in the map.
    first_record = by_hash[str(certificate_terms[0]["signed_certificate_sha256"])]
    first_rep = first_record["representative"]
    bad_edge = list(map(int, first_rep["left_added_edge"]))
    bad_edge[1] = bad_edge[1] % N + 1
    bad_edge.sort()
    if bad_edge == list(map(int, first_rep["left_added_edge"])):
        bad_edge = [1, N]
    source_pair = source_terms[int(first_rep["source_term"])][1]
    mutant_pair: Pair = (
        tuple(sorted(source_pair[0] + (tuple(bad_edge),))),
        tuple(sorted(source_pair[1] + (tuple(map(int, first_rep["right_added_edge"])),))),
    )
    require(mutant_pair != parse_pair(first_rep["pair"]), "raw-lift edge mutation escaped")

    report = {
        "schema": "g0115-fresh-context-lift-support-audit-v1",
        "result": "PASS",
        "bindings": {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()}
        | {str(SCRIPT.relative_to(ROOT)): script_hash},
        "full_family": {
            "raw_extensions_reconstructed_from_MAX8_plus_one_edge_per_branch": raw_reconstruction_count,
            "signed_class_records": len(records),
            "retained_records": len(retained),
            "repair_records": len(repair),
            "missing_public_signed_classes": len(missing_public),
            "independent_column_order_sha256": observed_order_hash,
        },
        "certificate_support": {
            "terms": len(certificate_terms),
            "group_counts": dict(sorted(group_counts.items())),
            "unique_sequences": len(supported_sequences),
            "unique_signed_hashes": len(supported_hashes),
            "unique_columns": len(supported_columns),
            "retained_terms_with_exact_public_signed_graph_match": retained_matches,
            "repair_terms_with_no_public_signed_graph_match": repair_nonmatches,
            "minimum_column": min(supported_columns),
            "maximum_column": max(supported_columns),
        },
        "controls": {"raw_lift_edge_mutation_rejected": True},
        "method_boundary": (
            "Raw lift membership was reconstructed directly from each record's MAX8 source term and "
            "added edge pair. Public-versus-repair status was checked with NetworkX colored-incidence "
            "graph isomorphism after signed common-edge cancellation, not with the producer's pynauty "
            "certificate. The full frozen column order was independently rebuilt."
        ),
        "claim_boundary": (
            "The 395 serialized terms occupy genuine columns of the frozen 22,666-class MAX8-to-MAX9 "
            "one-edge-per-branch lift family. This does not prove the family is complete for arbitrary "
            "degree-four identities, nor any MAX10/MAX11 or induction statement."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "support verifier changed during execution")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
