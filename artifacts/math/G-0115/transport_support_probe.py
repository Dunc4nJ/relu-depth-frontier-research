#!/usr/bin/env python3
"""Preregistered source-local support probe for the 395-term G-0115 identity."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations_with_replacement
import json
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Mapping, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(HERE))
import parity_lift_census as census  # noqa: E402
import semantic_repair as kernel  # noqa: E402


CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
MAP = HERE / "parity_lift_representatives_v1.jsonl.gz"
CENSUS = HERE / "parity_lift_census_v1.json"
CERTIFICATE = HERE / "unrestricted_full_semantic_certificate_v1.json"
REPLAY = HERE / "independent_unrestricted_degree4_replay_v1.json"
PREREG = HERE / "TRANSPORT_LAW_PREREGISTRATION.md"
ADDENDUM = HERE / "TRANSPORT_LAW_CONTROL_ADDENDUM.md"
EXPECTED = {
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT9: "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
    MAP: "2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148",
    CENSUS: "844dba5cf023f68a083261dd1612503c16309297f21ca57e26497f7a6df28d7a",
    CERTIFICATE: "628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e",
    REPLAY: "865f7728f26f56953dbe9a3dc8d3c3bbf3c32de4d3c992eb13c73d20bd0f2413",
    PREREG: "1c276c26e16227fb0cef37910363a2db7364db24d2b8586a4c185ae07c531e49",
    ADDENDUM: "a6472ae3aa0d146ac42d8479ef3b06a50b3ca0ceaf4dedb3896e4df93f223439",
    HERE / "parity_lift_census.py": "4ea2109ada7a30faaea224f3c0e7da46ccccfb6ca0c8bbaf70746c97b1d6ab1a",
    HERE / "semantic_repair.py": "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
}
N = 9
FAMILIES = ("coarse", "incidence", "radius1")
Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class SupportProbeError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SupportProbeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def atomic_json(path: Path, value: object) -> None:
    require(not path.exists(), f"output exists: {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def class_hash(certificate: bytes) -> str:
    return hashlib.sha256(certificate).hexdigest()


def relation(left: Edge, right: Edge) -> str:
    if left[0] == left[1] or right[0] == right[1]:
        return "HAS_LOOP"
    if left == right:
        return "COMMON_NONLOOP"
    if set(left) & set(right):
        return "SHARE_DISTINCT"
    return "DISJOINT"


def relabel_edge(edge: Edge, permutation: Mapping[int, int]) -> Edge:
    return tuple(sorted((permutation[edge[0]], permutation[edge[1]])))  # type: ignore[return-value]


def oriented_candidates(pair: Pair, left: Edge, right: Edge) -> Iterable[tuple[Pair, tuple[int, ...]]]:
    for branch_swap in (False, True):
        sides = (pair[1], pair[0]) if branch_swap else pair
        first, second = (right, left) if branch_swap else (left, right)
        for first_swap in (False, True):
            a = (first[1], first[0]) if first_swap else first
            for second_swap in (False, True):
                b = (second[1], second[0]) if second_swap else second
                yield sides, a + b


def source_graph(sides: Pair) -> dict[str, object]:
    degrees = [[0] * (N + 1), [0] * (N + 1)]
    adjacency: Counter[tuple[int, int]] = Counter()
    parent = list(range(N + 1))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    def union(first: int, second: int) -> None:
        first, second = find(first), find(second)
        if first != second:
            parent[second] = first

    for branch, side in enumerate(sides):
        for u, v in side:
            degrees[branch][u] += 1
            if v != u:
                degrees[branch][v] += 1
                union(u, v)
            adjacency[(min(u, v), max(u, v))] += 1
    components = [find(value) for value in range(N + 1)]
    return {"degrees": degrees, "adjacency": adjacency, "components": components}


def one_descriptor(sides: Pair, slots: tuple[int, ...], family: str) -> tuple[object, ...]:
    graph = source_graph(sides)
    degrees = graph["degrees"]
    adjacency = graph["adjacency"]
    components = graph["components"]
    require(isinstance(degrees, list) and isinstance(adjacency, Counter), "source graph drift")
    block_by_vertex: dict[int, int] = {}
    partition: list[int] = []
    vertices: list[int] = []
    for vertex in slots:
        if vertex not in block_by_vertex:
            block_by_vertex[vertex] = len(vertices)
            vertices.append(vertex)
        partition.append(block_by_vertex[vertex])
    profiles = tuple(
        (
            degrees[0][vertex],
            degrees[1][vertex],
            degrees[0][vertex] + degrees[1][vertex],
            int(degrees[0][vertex] == 0 and degrees[1][vertex] == 0),
        )
        for vertex in vertices
    )
    base: tuple[object, ...] = (tuple(partition), profiles)
    if family == "coarse":
        return base
    incidence = tuple(
        (
            int(adjacency.get((min(first, second), max(first, second)), 0)),
            int(components[first] == components[second]),
        )
        for position, first in enumerate(vertices)
        for second in vertices[position:]
    )
    if family == "incidence":
        return base + (incidence,)
    require(family == "radius1", f"unknown family: {family}")
    root = set(vertices)
    root_occurrences: list[tuple[int, int, int]] = []
    external: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for branch, side in enumerate(sides):
        for u, v in side:
            if u not in root and v not in root:
                continue
            if u in root and v in root:
                first, second = block_by_vertex[u], block_by_vertex[v]
                root_occurrences.append((branch, min(first, second), max(first, second)))
            else:
                inside, outside = (u, v) if u in root else (v, u)
                external[outside].append((branch, block_by_vertex[inside]))
    external_fingerprints = []
    for vertex, incidents in external.items():
        profile = (
            degrees[0][vertex],
            degrees[1][vertex],
            degrees[0][vertex] + degrees[1][vertex],
        )
        external_fingerprints.append((profile, tuple(sorted(incidents))))
    return base + (incidence, tuple(sorted(root_occurrences)), tuple(sorted(external_fingerprints)))


def signature_bundle(pair: Pair, left: Edge, right: Edge) -> dict[str, str]:
    cancelled = census.cancelled(pair)
    kind = relation(left, right)
    candidates: dict[str, list[tuple[object, ...]]] = {name: [] for name in FAMILIES}
    for sides, slots in oriented_candidates(cancelled, left, right):
        for family in FAMILIES:
            candidates[family].append((kind,) + one_descriptor(sides, slots, family))
    return {
        family: json.dumps(min(values), separators=(",", ":"))
        for family, values in candidates.items()
    }


def parse_pair(raw: object) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed certificate pair")
    return census.canonical_side(raw[0]), census.canonical_side(raw[1])


def fraction_histogram(values: Iterable[Fraction]) -> dict[str, object]:
    counter = Counter(map(str, values))
    digest = hashlib.sha256()
    for value, count in sorted(counter.items()):
        digest.update(canonical({"value": value, "count": count}))
    return {
        "distinct": len(counter),
        "most_common": [{"value": value, "count": count} for value, count in counter.most_common(20)],
        "full_histogram_sha256": digest.hexdigest(),
    }


def matrix_summary(
    hits: Mapping[str, set[str]],
    contributions: Mapping[str, Mapping[str, Fraction]],
    selected: set[str],
) -> dict[str, object]:
    active = {
        signature: {class_id: value for class_id, value in rows.items() if value}
        for signature, rows in contributions.items()
    }
    active = {signature: rows for signature, rows in active.items() if rows}
    raw_pure = {
        signature for signature, classes in hits.items()
        if classes and set(classes) <= selected
    }
    active_pure = {
        signature for signature, rows in active.items()
        if rows and set(rows) <= selected
    }
    raw_covered = set().union(*(hits[signature] for signature in raw_pure)) if raw_pure else set()
    active_covered = set().union(*(active[signature] for signature in active_pure)) if active_pure else set()
    digest = hashlib.sha256()
    entries = 0
    for signature in sorted(active):
        for class_id, value in sorted(active[signature].items()):
            digest.update(canonical({"signature": signature, "class": class_id, "value": str(value)}))
            entries += 1
    return {
        "signatures": len(hits),
        "active_source_weighted_signatures": len(active),
        "raw_signature_class_incidences": sum(len(classes) for classes in hits.values()),
        "active_source_weighted_incidences": entries,
        "raw_pure_selected_signatures": len(raw_pure),
        "raw_selected_classes_covered_by_pure_signatures": len(raw_covered & selected),
        "raw_exact_support_predicate_exists": raw_covered >= selected,
        "source_weighted_pure_selected_signatures": len(active_pure),
        "source_weighted_selected_classes_covered_by_pure_signatures": len(active_covered & selected),
        "source_weighted_exact_support_predicate_exists": active_covered >= selected,
        "source_weighted_matrix_sha256": digest.hexdigest(),
    }


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()}
    require(bindings == expected, f"input drift: {bindings}")
    source = census.load_certificate(CERT8, 8, 3, 69)
    public9 = census.load_certificate(CERT9, 9, 4, 337)
    certificate = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    require(replay.get("result") == "PASS", "independent replay did not pass")
    terms = certificate.get("terms")
    require(isinstance(terms, list) and len(terms) == 395, "certificate support drift")
    selected_coefficients = {
        str(term["signed_certificate_sha256"]): Fraction(str(term["coefficient"]))
        for term in terms
    }
    require(len(selected_coefficients) == 395, "selected signed classes are not unique")
    selected = set(selected_coefficients)

    retained, repair, _missing = kernel.load_map_and_targets()
    records = retained + repair
    require(len(records) == 22_666, "ordered record census drift")
    record_by_hash = {str(record["signed_certificate_sha256"]): record for record in records}
    require(len(record_by_hash) == 22_666 and selected <= set(record_by_hash), "record map drift")
    for term in terms:
        column = int(term["column_index"])
        record = records[column]
        require(record["signed_certificate_sha256"] == term["signed_certificate_sha256"], "column/hash drift")
        require(class_hash(census.signed_certificate(parse_pair(term["pair"]))) == term["signed_certificate_sha256"], "term pair/hash drift")

    edges = tuple(combinations_with_replacement(range(1, N + 1), 2))
    require(len(edges) == 45, "edge census drift")
    hits: dict[str, dict[str, set[str]]] = {family: defaultdict(set) for family in FAMILIES}
    contributions: dict[str, dict[str, dict[str, Fraction]]] = {
        family: defaultdict(lambda: defaultdict(Fraction)) for family in FAMILIES
    }
    signature_raw_counts: dict[str, Counter[str]] = {family: Counter() for family in FAMILIES}
    signed_multiplicity: Counter[str] = Counter()
    pair_classes: set[str] = set()
    full_by_signed: dict[str, set[str]] = defaultdict(set)
    source_sum: dict[str, Fraction] = defaultdict(Fraction)
    raw_digest = hashlib.sha256()
    raw_count = 0
    pi = {index: (index % N) + 1 for index in range(1, N + 1)}
    tau = {index: N + 1 - index for index in range(1, N + 1)}
    relabel_checks = 0
    branch_swap_checks = 0
    broken_witness: tuple[int, Pair, Edge, Edge, dict[str, str]] | None = None

    for source_term in source:
        coefficient = source_term.coefficient
        active = {vertex for side in census.cancelled(source_term.pair) for edge in side for vertex in edge}
        pi_pair = census.relabel_pair(source_term.pair, pi)
        tau_pair = census.relabel_pair(source_term.pair, tau)
        for left in edges:
            for right in edges:
                pair: Pair = (
                    tuple(sorted(source_term.pair[0] + (left,))),
                    tuple(sorted(source_term.pair[1] + (right,))),
                )
                descriptor = {
                    "source_term": source_term.index,
                    "left_added_edge": list(left),
                    "right_added_edge": list(right),
                    "relation": relation(left, right),
                }
                raw_digest.update(canonical(descriptor))
                signed_id = class_hash(census.signed_certificate(pair))
                pair_id = class_hash(census.pair_certificate(pair))
                bundle = signature_bundle(source_term.pair, left, right)
                for permutation, permuted_pair in ((pi, pi_pair), (tau, tau_pair)):
                    permuted = signature_bundle(
                        permuted_pair,
                        relabel_edge(left, permutation),
                        relabel_edge(right, permutation),
                    )
                    require(permuted == bundle, "simultaneous relabel changed a signature")
                    relabel_checks += len(FAMILIES)
                swapped = signature_bundle((source_term.pair[1], source_term.pair[0]), right, left)
                require(swapped == bundle, "global branch swap changed a signature")
                branch_swap_checks += len(FAMILIES)
                if broken_witness is None:
                    nonloop_distinct = left[0] != left[1] and right[0] != right[1] and left != right
                    both_meet = bool(set(left) & active) and bool(set(right) & active)
                    moved_outside = any(pi[vertex] not in set(left) | set(right) for vertex in (set(left) | set(right)) & active)
                    if nonloop_distinct and both_meet and moved_outside:
                        broken_witness = (source_term.index, source_term.pair, left, right, bundle)
                for family, signature in bundle.items():
                    hits[family][signature].add(signed_id)
                    contributions[family][signature][signed_id] += coefficient
                    signature_raw_counts[family][signature] += 1
                signed_multiplicity[signed_id] += 1
                pair_classes.add(pair_id)
                full_by_signed[signed_id].add(pair_id)
                source_sum[signed_id] += coefficient
                raw_count += 1
        print(f"G0115_TRANSPORT_SUPPORT_SOURCE {source_term.index + 1}/{len(source)}", flush=True)

    require(raw_count == 139_725, "raw count drift")
    require(len(signed_multiplicity) == 22_666 and len(pair_classes) == 28_378, "orbit census drift")
    census_report = json.loads(CENSUS.read_text(encoding="utf-8"))
    require(raw_digest.hexdigest() == census_report["lift"]["raw_descriptor_sha256"], "raw descriptor digest drift")
    require(all(signed_multiplicity[class_id] == int(record_by_hash[class_id]["raw_multiplicity"]) for class_id in signed_multiplicity), "signed multiplicity drift")

    require(broken_witness is not None, "no broken-control witness")
    witness_index, witness_pair, witness_left, witness_right, witness_bundle = broken_witness
    broken_source = signature_bundle(census.relabel_pair(witness_pair, pi), witness_left, witness_right)
    broken_left = signature_bundle(witness_pair, relabel_edge(witness_left, pi), witness_right)
    require(broken_source["radius1"] != witness_bundle["radius1"], "source-only relabel mutant escaped")
    require(broken_left["radius1"] != witness_bundle["radius1"], "one-edge relabel mutant escaped")

    public9_coefficients = {term.index: term.coefficient for term in public9}
    retained_ratios: list[Fraction] = []
    retained_equal = 0
    representative_ratios: list[Fraction] = []
    source_sum_ratios: list[Fraction] = []
    source_average_ratios: list[Fraction] = []
    zero_source_sum = 0
    for class_id, value in selected_coefficients.items():
        record = record_by_hash[class_id]
        representative_source = int(record["representative"]["source_term"])
        representative_ratios.append(value / source[representative_source].coefficient)
        total = source_sum[class_id]
        if total:
            source_sum_ratios.append(value / total)
            source_average_ratios.append(value * signed_multiplicity[class_id] / total)
        else:
            zero_source_sum += 1
        indices = list(map(int, record["public_term_indices"]))
        if indices:
            require(len(indices) == 1, "public class multiplicity drift")
            public_value = public9_coefficients[indices[0]]
            retained_ratios.append(value / public_value)
            retained_equal += int(value == public_value)

    selected_repairs = [records[int(term["column_index"])] for term in terms if term["group"] == "repair"]
    require(len(selected_repairs) == 67, "repair support drift")
    topology = Counter(json.dumps(record["topology_distance"], separators=(",", ":")) for record in selected_repairs)
    representative_relations = Counter(str(record["representative"]["relation"]) for record in selected_repairs)
    relation_sets = Counter(json.dumps(record["relations"], separators=(",", ":")) for record in selected_repairs)
    source_terms = Counter(int(record["representative"]["source_term"]) for record in selected_repairs)

    result = {
        "schema": "max11-g0115-transport-support-probe-v1",
        "result": "EXACT_SOURCE_LOCAL_SUPPORT_PROFILE",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "census": {
            "raw_descriptors": raw_count,
            "full_atom_orbits": len(pair_classes),
            "signed_W_orbits": len(signed_multiplicity),
            "raw_descriptor_sha256": raw_digest.hexdigest(),
            "selected_signed_classes": len(selected),
            "selected_full_atom_fibers": sum(len(full_by_signed[class_id]) for class_id in selected),
        },
        "signature_families": {
            family: {
                **matrix_summary(hits[family], contributions[family], selected),
                "minimum_raw_multiplicity": min(signature_raw_counts[family].values()),
                "maximum_raw_multiplicity": max(signature_raw_counts[family].values()),
            }
            for family in FAMILIES
        },
        "coefficient_diagnostics": {
            "retained_output_over_public_MAX9": fraction_histogram(retained_ratios),
            "retained_coefficients_exactly_equal_public_MAX9": retained_equal,
            "output_over_representative_source_coefficient": fraction_histogram(representative_ratios),
            "output_over_raw_fiber_source_sum": fraction_histogram(source_sum_ratios),
            "output_over_raw_fiber_source_average": fraction_histogram(source_average_ratios),
            "selected_classes_with_zero_raw_fiber_source_sum": zero_source_sum,
        },
        "selected_repair_profile": {
            "terms": len(selected_repairs),
            "topology_distance_histogram": dict(sorted(topology.items())),
            "representative_relation_histogram": dict(sorted(representative_relations.items())),
            "relation_set_histogram": dict(sorted(relation_sets.items())),
            "representative_source_terms": len(source_terms),
            "maximum_repairs_from_one_representative_source": max(source_terms.values()),
        },
        "controls": {
            "simultaneous_relabel_signature_checks": relabel_checks,
            "global_branch_swap_signature_checks": branch_swap_checks,
            "full_and_signed_orbit_censuses_reconciled": True,
            "signed_raw_multiplicities_reconciled": True,
            "selected_serialized_pairs_match_signed_hashes": True,
            "broken_witness": {
                "source_term": witness_index,
                "left_edge": list(witness_left),
                "right_edge": list(witness_right),
            },
            "source_only_relabel_mutant_rejected": True,
            "one_edge_only_relabel_mutant_rejected": True,
        },
        "interpretation_boundary": (
            "Exact source-local support and coefficient diagnostics only. Signature purity is not "
            "a functional identity, a fitted transport law, a MAX10-to-MAX11 replay, or induction."
        ),
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during run")
    atomic_json(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output.resolve())
    print(json.dumps({
        "result": result["result"],
        "signature_families": result["signature_families"],
        "selected_repair_profile": result["selected_repair_profile"],
        "wall_seconds": result["wall_seconds"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
