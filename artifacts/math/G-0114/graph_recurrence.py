#!/usr/bin/env python3
"""Exact graph-level recurrence census for two public degree-raising transitions."""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import combinations
import json
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence

import networkx as nx
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import degree_raising_identity as identity  # noqa: E402


SCRIPT = Path(__file__).resolve()
CERT6 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json"
CERT7 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_7_3.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
EXPECTED = {
    "certificate_6_2": "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    "certificate_7_3": "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    "certificate_8_3": "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    "certificate_9_4": "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
    "identity_script": "__SET_AFTER_FREEZE__",
}

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def read_pair(raw: Sequence[Sequence[Sequence[int]]], n: int) -> Pair:
    require(len(raw) == 2, "pair must have two branches")
    sides = []
    for raw_side in raw:
        side = tuple(sorted((int(edge[0]) - 1, int(edge[1]) - 1) for edge in raw_side))
        require(all(0 <= u <= v < n for u, v in side), "endpoint out of range")
        sides.append(side)
    require(len(sides[0]) == len(sides[1]), "branch degree mismatch")
    return sides[0], sides[1]


def incidence(pair: Pair, n: int) -> tuple[dict[int, set[int]], list[set[int]], dict[int, str]]:
    adjacency: dict[int, set[int]] = {index: set() for index in range(n + 2)}
    kinds = {index: "coordinate" for index in range(n)}
    branches = (n, n + 1)
    kinds[n] = kinds[n + 1] = "branch"
    occurrences: list[int] = []
    for branch, side in zip(branches, pair, strict=True):
        for u, v in side:
            occurrence = len(adjacency)
            adjacency[occurrence] = {branch, u}
            adjacency[branch].add(occurrence)
            adjacency[u].add(occurrence)
            if v != u:
                adjacency[occurrence].add(v)
                adjacency[v].add(occurrence)
            kinds[occurrence] = "edge-occurrence"
            occurrences.append(occurrence)
    coloring = [set(range(n)), set(branches)]
    if occurrences:
        coloring.append(set(occurrences))
    require(set().union(*coloring) == set(adjacency), "coloring partition drift")
    return adjacency, coloring, kinds


def certificate(pair: Pair, n: int) -> str:
    adjacency, coloring, _ = incidence(pair, n)
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={node: sorted(neighbours) for node, neighbours in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph).hex()


def nx_graph(pair: Pair, n: int) -> nx.Graph:
    adjacency, _coloring, kinds = incidence(pair, n)
    graph = nx.Graph()
    for node, kind in kinds.items():
        graph.add_node(node, kind=kind)
    for node, neighbours in adjacency.items():
        for neighbour in neighbours:
            if node < neighbour:
                graph.add_edge(node, neighbour)
    return graph


def relabel(pair: Pair, permutation: Sequence[int]) -> Pair:
    return tuple(
        tuple(sorted((min(permutation[u], permutation[v]), max(permutation[u], permutation[v]))
                     for u, v in side))
        for side in pair
    )  # type: ignore[return-value]


def relation(left: Edge, right: Edge) -> str:
    overlap = len(set(left) & set(right))
    require(overlap in (0, 1), "distinct nonloop relation drift")
    return "share_one_nonloop" if overlap == 1 else "disjoint_nonloop"


def target_classes(path: Path, n: int) -> tuple[dict[str, Fraction], int]:
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document["n"] == n, "target arity drift")
    output: dict[str, Fraction] = defaultdict(Fraction)
    for term in document["terms"]:
        output[certificate(read_pair(term["pair"], n), n)] += Fraction(term["coefficient"])
    return {key: value for key, value in output.items() if value}, len(document["terms"])


def build_transition(source_path: Path, target_path: Path, n: int, label: str) -> dict[str, object]:
    source = json.loads(source_path.read_text(encoding="utf-8"))
    require(source["n"] == n, "source arity drift")
    target, target_terms = target_classes(target_path, n + 1)
    edges = tuple(combinations(range(n + 1), 2))
    expected_share_per_edge = 2 * (n - 1)
    expected_disjoint_per_edge = math_comb(n - 1, 2)
    classes: dict[str, dict[str, int]] = {
        "share_one_nonloop": defaultdict(int),
        "disjoint_nonloop": defaultdict(int),
        "unequal_nonloop": defaultdict(int),
    }
    columns: dict[str, dict[str, identity.SparseVector]] = {
        "share_one_nonloop": {},
        "disjoint_nonloop": {},
        "unequal_nonloop": {},
    }
    raw_counts = {key: 0 for key in classes}
    last_plant: dict[str, str] = {}
    duplicate_samples: list[tuple[str, Pair, Pair]] = []
    representative: dict[str, Pair] = {}
    for term_index, term in enumerate(source["terms"]):
        pair = read_pair(term["pair"], n)
        source_coefficient = Fraction(term["coefficient"])
        for left in edges:
            for right in edges:
                if left == right:
                    continue
                kind = relation(left, right)
                lifted = (
                    tuple(sorted(pair[0] + (left,))),
                    tuple(sorted(pair[1] + (right,))),
                )
                full_class = certificate(lifted, n + 1)
                signature = identity.local_signature(pair, left, right, n + 1)
                for family in (kind, "unequal_nonloop"):
                    classes[family][full_class] += 1
                    if signature not in columns[family]:
                        columns[family][signature] = defaultdict(Fraction)
                    columns[family][signature][(label, "class", full_class)] += source_coefficient
                    raw_counts[family] += 1
                    last_plant[family] = full_class
                previous = representative.setdefault(full_class, lifted)
                if previous != lifted and len(duplicate_samples) < 8:
                    duplicate_samples.append((full_class, previous, lifted))
    term_count = len(source["terms"])
    expected = {
        "share_one_nonloop": term_count * len(edges) * expected_share_per_edge,
        "disjoint_nonloop": term_count * len(edges) * expected_disjoint_per_edge,
    }
    expected["unequal_nonloop"] = expected["share_one_nonloop"] + expected["disjoint_nonloop"]
    require(raw_counts == expected, "raw census does not match independent combinatorial count")
    for family in classes:
        require(sum(classes[family].values()) == raw_counts[family], "class census reconciliation")
        require(last_plant[family] in classes[family], "far-end plant missing")

    vf2_checked = 0
    matcher = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    for full_class, first, second in duplicate_samples:
        require(certificate(first, n + 1) == full_class, "representative certificate drift")
        require(certificate(second, n + 1) == full_class, "duplicate certificate drift")
        require(nx.is_isomorphic(nx_graph(first, n + 1), nx_graph(second, n + 1), node_match=matcher),
                "pynauty duplicate failed typed VF2")
        vf2_checked += 1

    target_rows = {(label, "class", key): value for key, value in target.items()}
    coverage = {}
    decisions = {}
    for family in classes:
        generated = set(classes[family])
        missing = sorted(set(target) - generated)
        covered = sorted(set(target) & generated)
        extra = sorted(generated - set(target))
        coverage[family] = {
            "target_nonzero_classes": len(target),
            "covered_target_classes": len(covered),
            "missing_target_classes": len(missing),
            "generated_zero_target_classes": len(extra),
            "covered_target_coefficient_l1": str(sum(abs(target[key]) for key in covered)),
            "total_target_coefficient_l1": str(sum(abs(value) for value in target.values())),
            "first_missing": None if not missing else {
                "class_sha256": hashlib.sha256(bytes.fromhex(missing[0])).hexdigest(),
                "target_coefficient": str(target[missing[0]]),
                "all_source_signature_columns_zero": True,
            },
        }
        if missing:
            decisions[family] = {
                "result": "EXACT_GRAPH_CLASS_NONMEMBERSHIP",
                "witness": coverage[family]["first_missing"],
                "does_not_show": "Does not reject function-level span membership.",
            }
        else:
            decisions[family] = identity.exact_decide(
                {key: dict(value) for key, value in columns[family].items()},
                target_rows,
                f"{label}-{family}-graph-coefficients",
            )
    return {
        "label": label,
        "source_terms": term_count,
        "target_terms": target_terms,
        "target_nonzero_full_atom_classes": len(target),
        "nonloop_edges": len(edges),
        "raw_counts": raw_counts,
        "unique_generated_classes": {key: len(value) for key, value in classes.items()},
        "signature_counts": {key: len(value) for key, value in columns.items()},
        "coverage": coverage,
        "coefficient_decisions": decisions,
        "vf2_duplicate_samples_checked": vf2_checked,
        "columns": columns,
        "target_rows": target_rows,
    }


def math_comb(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    numerator = 1
    denominator = 1
    for index in range(1, k + 1):
        numerator *= n - index + 1
        denominator *= index
    return numerator // denominator


def invariant_controls() -> dict[str, object]:
    source = json.loads(CERT8.read_text(encoding="utf-8"))
    pair = read_pair(source["terms"][0]["pair"], 8)
    lifted = (tuple(sorted(pair[0] + ((0, 8),))), tuple(sorted(pair[1] + ((1, 2),))))
    base = certificate(lifted, 9)
    permutation = tuple(reversed(range(9)))
    require(certificate(relabel(lifted, permutation), 9) == base, "relabel changed certificate")
    require(certificate((lifted[1], lifted[0]), 9) == base, "branch swap changed certificate")
    mutant = (tuple(sorted(lifted[0] + (lifted[0][0],))), lifted[1] + (lifted[1][0],))
    require(certificate(mutant, 9) != base, "multiplicity mutant escaped")
    matcher = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    require(nx.is_isomorphic(nx_graph(lifted, 9), nx_graph(relabel(lifted, permutation), 9),
                             node_match=matcher), "explicit relabel failed VF2")
    return {
        "coordinate_relabel_invariant": True,
        "global_branch_swap_invariant": True,
        "edge_multiplicity_mutant_rejected": True,
        "typed_VF2_relabel_crosscheck": True,
        "witness_certificate_sha256": hashlib.sha256(bytes.fromhex(base)).hexdigest(),
    }


def strip_private(transition: dict[str, object]) -> dict[str, object]:
    return {key: value for key, value in transition.items() if key not in ("columns", "target_rows")}


def run(output: Path) -> None:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {
        "certificate_6_2": sha256(CERT6),
        "certificate_7_3": sha256(CERT7),
        "certificate_8_3": sha256(CERT8),
        "certificate_9_4": sha256(CERT9),
        "identity_script": sha256(HERE / "degree_raising_identity.py"),
    }
    expected = dict(EXPECTED)
    expected["identity_script"] = bindings["identity_script"]
    require(bindings == expected, "bound input drift")
    transition67 = build_transition(CERT6, CERT7, 6, "n7")
    transition89 = build_transition(CERT8, CERT9, 8, "n9")
    joint = {}
    for family in ("share_one_nonloop", "disjoint_nonloop", "unequal_nonloop"):
        if (
            transition67["coverage"][family]["missing_target_classes"]
            or transition89["coverage"][family]["missing_target_classes"]
        ):
            joint[family] = {
                "result": "EXACT_GRAPH_CLASS_NONMEMBERSHIP",
                "reason": "At least one transition has a nonzero target class absent from every source lift.",
            }
            continue
        columns = identity.stacked_columns(
            transition67["columns"][family], transition89["columns"][family]
        )
        target = identity.combine_vectors([
            (transition67["target_rows"], Fraction(1)),
            (transition89["target_rows"], Fraction(1)),
        ])
        joint[family] = identity.exact_decide(columns, target, f"joint-{family}-graph-coefficients")
    report = {
        "schema": "max11-g0114-graph-recurrence-v1",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "claim_boundary": (
            "Exact full-atom graph-class coverage for public MAX6->MAX7 and MAX8->MAX9 "
            "one-edge lifts. Noncoverage rejects atomwise certificate recurrence only, not "
            "function-level span membership or MAX11."
        ),
        "transitions": [strip_private(transition67), strip_private(transition89)],
        "joint_shared_signature_decisions": joint,
        "controls": invariant_controls(),
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during run")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as destination:
        destination.write(canonical(report))
        destination.flush()
        os.fsync(destination.fileno())
    print(json.dumps({
        "output": str(output),
        "coverage": [
            [item["label"], {
                family: [
                    item["coverage"][family]["covered_target_classes"],
                    item["coverage"][family]["target_nonzero_classes"],
                ]
                for family in item["coverage"]
            }]
            for item in report["transitions"]
        ],
        "wall_seconds": report["wall_seconds"],
    }, sort_keys=True))


def self_test() -> dict[str, object]:
    pair: Pair = (((0, 1), (0, 1)), ((2, 3), (2, 3)))
    base = certificate(pair, 5)
    require(certificate(relabel(pair, (4, 3, 2, 1, 0)), 5) == base, "self-test relabel")
    require(certificate((pair[1], pair[0]), 5) == base, "self-test branch swap")
    require(relation((0, 1), (1, 2)) == "share_one_nonloop", "self-test share")
    require(relation((0, 1), (2, 3)) == "disjoint_nonloop", "self-test disjoint")
    return {"canonical_invariance": True, "relation_classifier": True}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        require(args.output is None, "self-test refuses output")
        print(json.dumps(self_test(), sort_keys=True))
        return
    require(args.output is not None and not args.output.exists(), "unused output required")
    run(args.output)


if __name__ == "__main__":
    main()
