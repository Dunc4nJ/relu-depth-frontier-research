#!/usr/bin/env python3
"""Independent exact audit of the beta2-common -> G-0008 function map.

This script deliberately imports no G-0006/G-0008/G-0009 evaluator or
enumerator.  It reconstructs both raw families from the pinned MAX10
certificate, binds the reconstructions to the frozen quotient artifacts,
checks a deterministic common-edge witness for every beta2 item, and directly
tests the common-edge symmetrisation identity at n <= 7.

It does not run the eleven-variable direction-histogram DP and does not claim
anything about the cross-component family or unrestricted MAX11 atoms.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from itertools import combinations, permutations
import hashlib
import json
from math import factorial
from pathlib import Path
from typing import Callable, Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
G8_CLASSES = ROOT / "artifacts/math/G-0006/isomorphism_classes_v2.json"
BETA2_CLASSES = ROOT / "artifacts/math/G-0009/beta2_common_classes.json"
DEFAULT_OUTPUT = HERE / "beta2_union_mapping_audit_v1.json"

N = 11
EXPECTED_BASES = 252
EXPECTED_G8_RAW = 16_000
EXPECTED_G8_CLASSES = 9_804
EXPECTED_BETA2_RAW = 6_740
EXPECTED_BETA2_CLASSES = 4_916

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class AuditError(AssertionError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def load_json(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AuditError(f"expected JSON object: {path}")
    return value


def normalize_edge(raw: Sequence[object]) -> Edge:
    if len(raw) != 2 or any(type(value) is not int for value in raw):
        raise AuditError(f"malformed edge: {raw!r}")
    a, b = map(int, raw)
    return (a, b) if a <= b else (b, a)


def components(vertices: Iterable[int], edges: Sequence[Edge]) -> tuple[tuple[int, ...], ...]:
    vertex_set = set(vertices)
    adjacency = {vertex: set() for vertex in vertex_set}
    for a, b in edges:
        if a not in adjacency or b not in adjacency:
            raise AuditError("edge endpoint lies outside active vertex set")
        adjacency[a].add(b)
        adjacency[b].add(a)
    unseen = set(vertex_set)
    result: list[tuple[int, ...]] = []
    while unseen:
        root = min(unseen)
        stack = [root]
        found = set()
        while stack:
            vertex = stack.pop()
            if vertex in found:
                continue
            found.add(vertex)
            stack.extend(adjacency[vertex] - found)
        unseen -= found
        result.append(tuple(sorted(found)))
    return tuple(sorted(result, key=lambda component: (component[0], component)))


def reconstruct_bases(document: dict[str, object]):
    terms = document.get("terms")
    if not isinstance(terms, list):
        raise AuditError("certificate terms are not a list")
    bases = []
    rejected = Counter()
    for term_index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise AuditError(f"certificate term {term_index} is not an object")
        raw_pair = term.get("pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise AuditError(f"certificate term {term_index} has malformed pair")
        left = tuple(normalize_edge(edge) for edge in raw_pair[0])
        right = tuple(normalize_edge(edge) for edge in raw_pair[1])
        all_edges = left + right
        if len(left) != 4 or len(right) != 4:
            rejected["not_four_edges_per_branch"] += 1
            continue
        if any(a == b for a, b in all_edges):
            rejected["loop"] += 1
            continue
        if len(set(all_edges)) != 8:
            rejected["repeated_union_edge"] += 1
            continue
        active = {vertex for edge in all_edges for vertex in edge}
        if len(active) != 10:
            rejected["not_ten_active_vertices"] += 1
            continue
        found_components = components(active, all_edges)
        if len(found_components) != 2:
            rejected["not_two_components"] += 1
            continue
        if len(all_edges) - len(active) + len(found_components) != 0:
            raise AuditError("selected source union is not a forest")
        if active != set(range(1, 11)):
            raise AuditError("selected source labels are not exactly 1..10")
        bases.append(
            {
                "base_index": len(bases),
                "term_index": term_index,
                "left": left,
                "right": right,
                "components": found_components,
            }
        )
    if len(bases) != EXPECTED_BASES:
        raise AuditError(f"expected {EXPECTED_BASES} bases, reconstructed {len(bases)}")
    return bases, rejected, len(terms)


def reconstruct_g8(bases: Sequence[dict[str, object]]):
    pairs: list[Pair] = []
    metadata: list[tuple[int, int, int, int, int]] = []
    lookup: dict[tuple[int, int, int, int], int] = {}
    equal_counts = Counter()
    for base in bases:
        base_index = int(base["base_index"])
        term_index = int(base["term_index"])
        left = base["left"]
        right = base["right"]
        for component_index, component in enumerate(base["components"]):
            for left_endpoint in component:
                for right_endpoint in component:
                    key = (base_index, component_index, left_endpoint, right_endpoint)
                    if key in lookup:
                        raise AuditError("duplicate G8 metadata key")
                    lookup[key] = len(pairs)
                    metadata.append(
                        (
                            base_index,
                            term_index,
                            component_index,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
                    pairs.append(
                        (
                            tuple(left) + ((left_endpoint, N),),
                            tuple(right) + ((right_endpoint, N),),
                        )
                    )
                    if left_endpoint == right_endpoint:
                        equal_counts[base_index] += 1
    if len(pairs) != EXPECTED_G8_RAW:
        raise AuditError(f"expected {EXPECTED_G8_RAW} G8 raw items, got {len(pairs)}")
    if set(equal_counts) != set(range(EXPECTED_BASES)):
        raise AuditError("not every source base has a coincident-endpoint lift")
    if set(equal_counts.values()) != {10}:
        raise AuditError(f"unexpected coincident-endpoint census: {Counter(equal_counts.values())}")
    return pairs, metadata, lookup, equal_counts


def reconstruct_beta2(bases: Sequence[dict[str, object]]):
    pairs: list[Pair] = []
    metadata: list[tuple[int, int, int, int, int]] = []
    per_base = Counter()
    for base in bases:
        base_index = int(base["base_index"])
        term_index = int(base["term_index"])
        left = base["left"]
        right = base["right"]
        for component_index, component in enumerate(base["components"]):
            for a, b in combinations(component, 2):
                edge = (a, b)
                pairs.append((tuple(left) + (edge,), tuple(right) + (edge,)))
                metadata.append((base_index, term_index, component_index, a, b))
                per_base[base_index] += 1
    if len(pairs) != EXPECTED_BETA2_RAW:
        raise AuditError(
            f"expected {EXPECTED_BETA2_RAW} beta2 raw items, got {len(pairs)}"
        )
    if set(per_base) != set(range(EXPECTED_BASES)):
        raise AuditError("beta2 raw family does not cover all source bases")
    return pairs, metadata, per_base


def pair_payload(pairs: Sequence[Pair]):
    return [
        [
            [[a, b] for a, b in pair[0]],
            [[a, b] for a, b in pair[1]],
        ]
        for pair in pairs
    ]


def g8_metadata_sha256(metadata: Sequence[tuple[int, ...]]) -> str:
    # This exactly replays the older generator's deliberately non-newline JSON digest.
    raw = json.dumps(metadata, separators=(",", ":")).encode("ascii")
    return sha256_bytes(raw)


def signed_adjacency(pair: Pair, n: int = N) -> tuple[tuple[int, ...], ...]:
    result = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for a, b in side:
            if not (1 <= a <= n and 1 <= b <= n):
                raise AuditError(f"edge outside 1..{n}: {(a, b)}")
            if a == b:
                result[a - 1][a - 1] += sign
            else:
                result[a - 1][b - 1] += sign
                result[b - 1][a - 1] += sign
    return tuple(tuple(row) for row in result)


def validate_common_lift(pair: Pair, base: dict[str, object], *, witness: bool) -> Edge:
    left, right = pair
    base_left = tuple(base["left"])
    base_right = tuple(base["right"])
    if len(left) != 5 or len(right) != 5:
        raise AuditError("common lift does not have five edge occurrences per branch")
    if left[:-1] != base_left or right[:-1] != base_right:
        raise AuditError("common lift does not preserve the declared source base")
    if left[-1] != right[-1]:
        raise AuditError("the added edge was not appended to both branches")
    edge = left[-1]
    if edge[0] == edge[1]:
        raise AuditError("the added common edge is not loopless")
    component_sets = [set(component) for component in base["components"]]
    if witness:
        if N not in edge:
            raise AuditError("G8 witness common edge does not use vertex 11")
        old_endpoint = edge[0] if edge[1] == N else edge[1]
        if not any(old_endpoint in component for component in component_sets):
            raise AuditError("G8 witness old endpoint is outside the source components")
    else:
        if not any(set(edge) <= component for component in component_sets):
            raise AuditError("beta2 edge is not internal to one source component")
    return edge


def validate_class_document(
    document: dict[str, object],
    *,
    schema: str,
    raw_count: int,
    class_count: int,
    certificate_sha256: str,
    metadata_sha256: str,
    pair_sha256: str,
) -> tuple[list[int], list[int]]:
    if document.get("schema") != schema or document.get("n") != N:
        raise AuditError(f"wrong quotient schema: {document.get('schema')!r}")
    expected = {
        "raw_candidate_count": raw_count,
        "class_count": class_count,
        "source_certificate_sha256": certificate_sha256,
        "candidate_metadata_sha256": metadata_sha256,
        "raw_pair_list_sha256": pair_sha256,
    }
    for key, value in expected.items():
        if document.get(key) != value:
            raise AuditError(f"quotient binding mismatch for {key}")
    representatives = document.get("representative_raw_indices")
    raw_to_class = document.get("raw_to_class")
    class_sizes = document.get("class_sizes")
    if not all(isinstance(value, list) for value in (representatives, raw_to_class, class_sizes)):
        raise AuditError("malformed quotient arrays")
    if len(representatives) != class_count or len(class_sizes) != class_count:
        raise AuditError("quotient class array length mismatch")
    if len(raw_to_class) != raw_count:
        raise AuditError("quotient raw map length mismatch")
    if any(type(value) is not int or not 0 <= value < class_count for value in raw_to_class):
        raise AuditError("quotient raw map has an invalid class index")
    if any(raw_to_class[raw] != cls for cls, raw in enumerate(representatives)):
        raise AuditError("quotient representative does not map back to its class")
    replayed_sizes = [0] * class_count
    for cls in raw_to_class:
        replayed_sizes[cls] += 1
    if replayed_sizes != class_sizes:
        raise AuditError("quotient class-size census does not replay")
    return list(map(int, representatives)), list(map(int, raw_to_class))


def incidence_graph(pair: Pair):
    import networkx as nx

    graph = nx.Graph()
    for vertex in range(1, N + 1):
        graph.add_node(("v", vertex), kind="vertex")
    for colour in range(2):
        graph.add_node(("c", colour), kind="colour")
    edge_index = 0
    for colour, side in enumerate(pair):
        for a, b in side:
            edge_node = ("e", edge_index)
            edge_index += 1
            graph.add_node(edge_node, kind="edge")
            graph.add_edge(edge_node, ("c", colour))
            graph.add_edge(edge_node, ("v", a))
            graph.add_edge(edge_node, ("v", b))
    if edge_index != 10:
        raise AuditError("witness incidence graph does not have ten edge occurrences")
    return graph


def independent_witness_class_count(witness_pairs: Sequence[Pair]) -> tuple[int, dict[str, int]]:
    import networkx as nx

    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    buckets: dict[str, list[object]] = defaultdict(list)
    class_count = 0
    exact_comparisons = 0
    bucket_sizes = Counter()
    for pair in witness_pairs:
        graph = incidence_graph(pair)
        digest = nx.weisfeiler_lehman_graph_hash(
            graph, node_attr="kind", iterations=16, digest_size=32
        )
        found = False
        for prior in buckets[digest]:
            exact_comparisons += 1
            if nx.is_isomorphic(graph, prior, node_match=node_match):
                found = True
                break
        if not found:
            buckets[digest].append(graph)
            class_count += 1
        bucket_sizes[digest] += 1
    return class_count, {
        "networkx_version": nx.__version__,
        "wl_bucket_count": len(buckets),
        "largest_wl_bucket": max(bucket_sizes.values(), default=0),
        "exact_vf2_comparisons_within_wl_buckets": exact_comparisons,
    }


def atom_value(pair: Pair, values: Sequence[int]) -> int:
    branches = []
    for side in pair:
        branches.append(sum(max(values[a - 1], values[b - 1]) for a, b in side))
    return max(branches)


def symmetrised_value(pair: Pair, values: Sequence[int]) -> int:
    n = len(values)
    total = 0
    for order in permutations(range(n)):
        permuted = tuple(values[order[vertex]] for vertex in range(n))
        total += atom_value(pair, permuted)
    return total


def f2_value(values: Sequence[int]) -> int:
    return sum(max(values[a], values[b]) for a, b in combinations(range(len(values)), 2))


def small_n_controls() -> list[dict[str, object]]:
    controls = []
    for n in range(4, 8):
        base: Pair = (
            ((1, 2), (3, 4)),
            ((1, 3), (2, 4)),
        )
        edge = (n - 1, n)
        alternate = (1, n)
        first = (base[0] + (edge,), base[1] + (edge,))
        second = (base[0] + (alternate,), base[1] + (alternate,))
        vectors = [
            tuple((index * index * 3 - 7 * index + 2) for index in range(n)),
            tuple((index + 1) * (-1 if index % 2 else 1) for index in range(n)),
        ]
        vector_records = []
        for values in vectors:
            base_value = symmetrised_value(base, values)
            expected_added = 2 * factorial(n - 2) * f2_value(values)
            first_value = symmetrised_value(first, values)
            second_value = symmetrised_value(second, values)
            if first_value != base_value + expected_added or second_value != first_value:
                raise AuditError(f"small-n common-edge identity failed at n={n}")
            vector_records.append(
                {
                    "values": list(values),
                    "base_phi": base_value,
                    "expected_common_edge_term": expected_added,
                    "lifted_phi": first_value,
                    "alternate_edge_phi": second_value,
                }
            )
        controls.append(
            {
                "n": n,
                "permutations_per_evaluation": factorial(n),
                "base": pair_payload([base])[0],
                "edge": list(edge),
                "alternate_edge": list(alternate),
                "vectors": vector_records,
                "identity_holds_exactly": True,
                "edge_placement_independence_holds_exactly": True,
            }
        )
    return controls


def expect_rejected(label: str, operation: Callable[[], object]) -> dict[str, object]:
    try:
        operation()
    except (AuditError, ValueError) as error:
        return {"mutant": label, "rejected": True, "reason": str(error)}
    raise AuditError(f"hostile mutant was accepted: {label}")


def hostile_controls(bases: Sequence[dict[str, object]], beta_pairs: Sequence[Pair], witness_pairs: Sequence[Pair]):
    base = bases[0]
    beta = beta_pairs[0]
    witness = witness_pairs[0]
    edge = beta[0][-1]
    one_branch: Pair = (tuple(base["left"]) + (edge,), tuple(base["right"]))
    loop_edge = (1, 1)
    loop_pair: Pair = (
        tuple(base["left"]) + (loop_edge,),
        tuple(base["right"]) + (loop_edge,),
    )
    records = [
        expect_rejected(
            "edge_added_only_to_A_branch",
            lambda: validate_common_lift(one_branch, base, witness=False),
        ),
        expect_rejected(
            "nonloopless_common_edge",
            lambda: validate_common_lift(loop_pair, base, witness=False),
        ),
        expect_rejected(
            "mismatched_source_base",
            lambda: validate_common_lift(witness, bases[1], witness=True),
        ),
    ]
    values = (-5, -2, 0, 1, 3, 6)
    base_small: Pair = (((1, 2), (3, 4)), ((1, 3), (2, 4)))
    e_small = (5, 6)
    bad_small: Pair = (base_small[0] + (e_small,), base_small[1])
    claimed = symmetrised_value(base_small, values) + 2 * factorial(4) * f2_value(values)
    observed = symmetrised_value(bad_small, values)
    if observed == claimed:
        raise AuditError("one-branch numeric mutant accidentally satisfies the claimed identity")
    records[0]["numeric_control_n"] = 6
    records[0]["numeric_observed"] = observed
    records[0]["numeric_false_formula_value"] = claimed
    records[0]["numeric_formula_rejected"] = True
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    certificate_sha = sha256_path(CERTIFICATE)
    certificate = load_json(CERTIFICATE)
    bases, rejected_terms, certificate_term_count = reconstruct_bases(certificate)

    g8_pairs, g8_metadata, g8_lookup, equal_counts = reconstruct_g8(bases)
    beta_pairs, beta_metadata, beta_per_base = reconstruct_beta2(bases)
    g8_metadata_sha = g8_metadata_sha256(g8_metadata)
    g8_pair_sha = sha256_bytes(canonical_bytes(pair_payload(g8_pairs)))
    beta_metadata_sha = sha256_bytes(canonical_bytes(beta_metadata))
    beta_pair_sha = sha256_bytes(canonical_bytes(pair_payload(beta_pairs)))

    g8_classes_document = load_json(G8_CLASSES)
    beta_classes_document = load_json(BETA2_CLASSES)
    g8_representatives, g8_raw_to_class = validate_class_document(
        g8_classes_document,
        schema="max11-minimal-lifts-isomorphism-v2",
        raw_count=EXPECTED_G8_RAW,
        class_count=EXPECTED_G8_CLASSES,
        certificate_sha256=certificate_sha,
        metadata_sha256=g8_metadata_sha,
        pair_sha256=g8_pair_sha,
    )
    beta_representatives, beta_raw_to_class = validate_class_document(
        beta_classes_document,
        schema="max11-beta2-common-internal-lifts-isomorphism-v1",
        raw_count=EXPECTED_BETA2_RAW,
        class_count=EXPECTED_BETA2_CLASSES,
        certificate_sha256=certificate_sha,
        metadata_sha256=beta_metadata_sha,
        pair_sha256=beta_pair_sha,
    )

    witness_by_base: dict[int, dict[str, object]] = {}
    witness_pairs: list[Pair] = []
    for base in bases:
        base_index = int(base["base_index"])
        component_index = 0
        endpoint = min(base["components"][component_index])
        raw_index = g8_lookup[(base_index, component_index, endpoint, endpoint)]
        pair = g8_pairs[raw_index]
        common_edge = validate_common_lift(pair, base, witness=True)
        class_index = g8_raw_to_class[raw_index]
        witness_by_base[base_index] = {
            "raw_index": raw_index,
            "class_index": class_index,
            "component_index": component_index,
            "endpoint": endpoint,
            "edge": common_edge,
            "pair": pair,
        }
        witness_pairs.append(pair)

    witness_raw_indices = [int(value["raw_index"]) for value in witness_by_base.values()]
    witness_class_indices = [int(value["class_index"]) for value in witness_by_base.values()]
    if len(set(witness_raw_indices)) != EXPECTED_BASES:
        raise AuditError("deterministic witnesses are not 252 distinct G8 raw atoms")
    if len(set(witness_class_indices)) != EXPECTED_BASES:
        raise AuditError("deterministic witnesses are not 252 distinct frozen G8 classes")
    independent_class_count, independent_class_details = independent_witness_class_count(
        witness_pairs
    )
    if independent_class_count != EXPECTED_BASES:
        raise AuditError(
            f"independent witness quotient has {independent_class_count}, expected 252"
        )

    mapping_records = []
    for beta_raw_index, (pair, metadata) in enumerate(zip(beta_pairs, beta_metadata)):
        base_index, term_index, component_index, a, b = metadata
        base = bases[base_index]
        beta_edge = validate_common_lift(pair, base, witness=False)
        witness = witness_by_base[base_index]
        witness_pair = witness["pair"]
        witness_edge = validate_common_lift(witness_pair, base, witness=True)
        if pair[0][:-1] != witness_pair[0][:-1] or pair[1][:-1] != witness_pair[1][:-1]:
            raise AuditError("mapped beta2 and G8 witness do not share their source base")
        if signed_adjacency(pair) != signed_adjacency(witness_pair):
            raise AuditError("mapped beta2 and G8 witness signed adjacencies differ")
        mapping_records.append(
            {
                "beta_raw_index": beta_raw_index,
                "beta_class_index": beta_raw_to_class[beta_raw_index],
                "source_base_index": base_index,
                "source_term_index": term_index,
                "beta_component_index": component_index,
                "beta_common_edge": list(beta_edge),
                "g8_witness_raw_index": int(witness["raw_index"]),
                "g8_witness_class_index": int(witness["class_index"]),
                "g8_witness_component_index": int(witness["component_index"]),
                "g8_witness_common_edge": list(witness_edge),
            }
        )

    if {record["source_base_index"] for record in mapping_records} != set(
        range(EXPECTED_BASES)
    ):
        raise AuditError("mapping records do not cover every source base")
    representative_mappings = [mapping_records[index] for index in beta_representatives]
    if len(representative_mappings) != EXPECTED_BETA2_CLASSES:
        raise AuditError("beta2 representative mapping census changed")
    if len({record["g8_witness_class_index"] for record in representative_mappings}) != EXPECTED_BASES:
        raise AuditError("beta2 quotient representatives do not cover all 252 witness classes")

    small_controls = small_n_controls()
    mutants = hostile_controls(bases, beta_pairs, witness_pairs)
    if not all(record["rejected"] for record in mutants):
        raise AuditError("a hostile control was not rejected")

    mapping_sha = sha256_bytes(canonical_bytes(mapping_records))
    result = {
        "schema": "max11-beta2-to-g8-exact-function-mapping-audit-v1",
        "result": "PASS",
        "script": relative(Path(__file__)),
        "script_sha256": sha256_path(Path(__file__)),
        "inputs": [
            {
                "path": relative(CERTIFICATE),
                "bytes": CERTIFICATE.stat().st_size,
                "sha256": certificate_sha,
                "role": "pinned MAX10 certificate and sole family-generation source",
            },
            {
                "path": relative(G8_CLASSES),
                "bytes": G8_CLASSES.stat().st_size,
                "sha256": sha256_path(G8_CLASSES),
                "role": "frozen G8 raw-to-class binding; not used to generate the raw family",
            },
            {
                "path": relative(BETA2_CLASSES),
                "bytes": BETA2_CLASSES.stat().st_size,
                "sha256": sha256_path(BETA2_CLASSES),
                "role": "frozen beta2 raw-to-class binding; not used to generate the raw family",
            },
        ],
        "independence": {
            "local_evaluator_or_enumerator_imports": 0,
            "heavy_n11_direction_dp_used": False,
            "raw_families_reconstructed_directly_from_certificate": True,
            "witness_graph_classes_rechecked_with_independent_networkx_route": True,
            "frozen_quotients_used_only_after_raw_digest_binding": True,
        },
        "source_bases": {
            "certificate_term_count": certificate_term_count,
            "filtered_base_count": len(bases),
            "rejected_term_reasons": dict(sorted(rejected_terms.items())),
            "branch_edge_counts": [4, 4],
            "distinct_loopless_union_edges_per_base": 8,
            "active_vertices": list(range(1, 11)),
            "component_count": 2,
            "forest_cycle_rank": 0,
        },
        "g8_reconstruction": {
            "raw_candidate_count": len(g8_pairs),
            "candidate_metadata_sha256": g8_metadata_sha,
            "raw_pair_list_sha256": g8_pair_sha,
            "frozen_class_count": len(g8_representatives),
            "coincident_endpoint_raw_count": sum(equal_counts.values()),
            "coincident_endpoint_count_per_base": 10,
            "deterministic_witness_raw_count": len(set(witness_raw_indices)),
            "deterministic_witness_frozen_class_count": len(set(witness_class_indices)),
            "deterministic_witness_independent_class_count": independent_class_count,
            "independent_classification": independent_class_details,
        },
        "beta2_reconstruction": {
            "raw_candidate_count": len(beta_pairs),
            "candidate_metadata_sha256": beta_metadata_sha,
            "raw_pair_list_sha256": beta_pair_sha,
            "frozen_class_count": len(beta_representatives),
            "source_base_count": len(beta_per_base),
            "raw_candidates_per_base_min": min(beta_per_base.values()),
            "raw_candidates_per_base_max": max(beta_per_base.values()),
            "every_added_edge_loopless_internal_and_common": True,
            "every_branch_has_five_edge_occurrences": True,
        },
        "mapping": {
            "record_count": len(mapping_records),
            "records_canonical_sha256": mapping_sha,
            "source_base_count": len(
                {record["source_base_index"] for record in mapping_records}
            ),
            "target_g8_raw_count": len(
                {record["g8_witness_raw_index"] for record in mapping_records}
            ),
            "target_g8_class_count": len(
                {record["g8_witness_class_index"] for record in mapping_records}
            ),
            "beta2_representative_count": len(representative_mappings),
            "mapped_source_base_and_signed_adjacency_equal_for_every_record": True,
            "records": mapping_records,
        },
        "common_edge_lemma": {
            "atom": "phi_(A,B)=max(sum_(e in A) h_e, sum_(e in B) h_e), h_ij=max(x_i,x_j)",
            "symmetrisation": "Phi_n(A,B)=sum_(sigma in S_n) phi_(sigma A,sigma B)",
            "pointwise_step": "phi_(A+e,B+e)=h_e+phi_(A,B)",
            "permutation_count": "sum_(sigma in S_n) h_(sigma e)=2*(n-2)!*F_2^(n) for loopless e",
            "n11_identity": "Phi_11(A+e,B+e)=Phi_11(A,B)+2*9!*F_2^(11)",
            "edge_placement_independent": True,
            "edge_multisets_allowed": True,
            "small_n_direct_permutation_controls": small_controls,
        },
        "hostile_controls": mutants,
        "certified_corollary": {
            "every_beta2_raw_function_pointwise_equals_its_mapped_g8_witness": True,
            "every_beta2_quotient_function_is_in_the_g8_function_set": True,
            "span_Q_G8_union_beta2_equals_span_Q_G8": True,
            "span_R_G8_union_beta2_equals_span_R_G8": True,
            "g0011_dual_annihilates_G8_union_beta2": True,
            "g0011_target_pairing_unchanged_and_nonzero": True,
            "union_no_go_certified": True,
        },
        "claim_boundary": (
            "This audit certifies the exact pointwise inclusion of the named G-0009 "
            "beta2-common family in the named G-0008 symmetrised function family, and "
            "therefore the G-0011 no-go for their union. It says nothing about the G-0009 "
            "cross family, independent A/B chords, all pair atoms, unrestricted MAX11, or "
            "unrestricted two-hidden-layer ReLU networks."
        ),
    }

    raw = canonical_bytes(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("xb") as destination:
        destination.write(raw)
    print(
        f"PASS output={args.output} bytes={len(raw)} sha256={sha256_bytes(raw)} "
        f"bases={len(bases)} g8={len(g8_pairs)} beta2={len(beta_pairs)} "
        f"mapping={len(mapping_records)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
