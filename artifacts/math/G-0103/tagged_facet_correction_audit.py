#!/usr/bin/env python3
"""Test the honest selected-endpoint correction to leaf/bridge deletion.

For each deletion event there is one open sign chamber in which the residual
two-branch face is a facet.  The leaf endpoint is selected and vanishes after
deleting the leaf coordinate; the opposite-colour edge selects one surviving
endpoint q.  Thus the projected facet is represented by the residual pair
with one branch-specific loop (q,q), not by the unshifted forest atom.

This script constructs that corrected event sum exactly and asks whether it
descends through functional relations among the balanced tree atoms.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import reduce
import importlib.util
import json
from math import gcd
from pathlib import Path
import sys

from sympy import Matrix


HERE = Path(__file__).resolve().parent
SEMANTIC_PATH = HERE / "semantic_descent_audit.py"


def load_semantics():
    spec = importlib.util.spec_from_file_location("g0103_tagged_semantics", SEMANTIC_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(SEMANTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def branch_support(pair, branch: int, normal: tuple[int, ...]) -> int:
    return sum(max(normal[u], normal[v]) for u, v in pair[branch])


def residual_components(pair, n: int, leaf: int, leaf_edge, removed):
    residual_edges = [
        edge
        for side in pair
        for edge in side
        if edge != leaf_edge and edge != removed
    ]
    adjacency = [set() for _ in range(n)]
    for u, v in residual_edges:
        adjacency[u].add(v)
        adjacency[v].add(u)
    unseen = set(range(n)) - {leaf}
    components = []
    while unseen:
        stack = [min(unseen)]
        component = set()
        while stack:
            vertex = stack.pop()
            if vertex in component:
                continue
            component.add(vertex)
            stack.extend(adjacency[vertex] - component)
        unseen -= component
        components.append(tuple(sorted(component)))
    if len(components) != 2:
        raise AssertionError("event residual does not have two nonleaf components")
    return tuple(sorted(components))


def corrected_facet_event(sem, pair, n: int, leaf: int, removed):
    leaf_colour = next(
        colour
        for colour, side in enumerate(pair)
        if any(leaf in edge for edge in side)
    )
    leaf_edge = next(edge for edge in pair[leaf_colour] if leaf in edge)
    opposite_colour = 1 - leaf_colour
    if removed not in pair[opposite_colour]:
        raise AssertionError("removed edge is not opposite-coloured")
    neighbour = leaf_edge[0] if leaf_edge[1] == leaf else leaf_edge[1]
    components = residual_components(pair, n, leaf, leaf_edge, removed)
    core = next(component for component in components if neighbour in component)
    other = next(component for component in components if component != core)
    if sum(endpoint in core for endpoint in removed) != 1:
        raise AssertionError("removed edge does not bridge residual components")

    # d is the B-minus-A colour imbalance internal to the neighbour component;
    # s is the sign of the leaf edge in B-A.
    d = 0
    for colour, side in enumerate(pair):
        sign = 1 if colour == 1 else -1
        for edge in side:
            if edge in (leaf_edge, removed):
                continue
            if edge[0] in core and edge[1] in core:
                d += sign
    s = 1 if leaf_colour == 1 else -1
    signed_imbalance = s * d

    # Solve the exact tie equation with core level 0 and leaf level >0.
    # If s*d >= 0, the other component has level +1 and f selects its
    # endpoint; otherwise it has level -1 and f selects the core endpoint.
    if signed_imbalance >= 0:
        other_level = 1
        leaf_level = signed_imbalance + 1
        selected = next(endpoint for endpoint in removed if endpoint in other)
    else:
        other_level = -1
        leaf_level = -signed_imbalance
        selected = next(endpoint for endpoint in removed if endpoint in core)
    normal = [0] * n
    normal[leaf] = leaf_level
    for vertex in other:
        normal[vertex] = other_level
    normal_tuple = tuple(normal)
    supports = (branch_support(pair, 0, normal_tuple), branch_support(pair, 1, normal_tuple))
    if supports[0] != supports[1]:
        raise AssertionError("derived facet normal does not tie the branches")

    remaining = [vertex for vertex in range(n) if vertex != leaf]
    renumber = {old: new for new, old in enumerate(remaining)}
    output = []
    for colour, side in enumerate(pair):
        new_side = []
        for edge in side:
            if edge in (leaf_edge, removed):
                continue
            new_side.append(tuple(sorted((renumber[edge[0]], renumber[edge[1]]))))
        if colour == opposite_colour:
            q = renumber[selected]
            new_side.append((q, q))
        output.append(tuple(sorted(new_side)))
    corrected = output[0], output[1]

    # Potency mutation: increasing the selected leaf level by one changes only
    # the leaf-edge branch support and must destroy the tie.
    mutated = list(normal_tuple)
    mutated[leaf] += 1
    mutated_supports = (branch_support(pair, 0, tuple(mutated)), branch_support(pair, 1, tuple(mutated)))
    if mutated_supports[0] == mutated_supports[1]:
        raise AssertionError("leaf-level tie mutation escaped")

    return corrected, {
        "leaf": leaf,
        "leaf_colour": leaf_colour,
        "leaf_edge": list(leaf_edge),
        "removed_opposite_edge": list(removed),
        "core_component": list(core),
        "other_component": list(other),
        "B_minus_A_core_imbalance": d,
        "leaf_edge_sign_in_B_minus_A": s,
        "signed_imbalance": signed_imbalance,
        "selected_opposite_endpoint": selected,
        "normal": list(normal_tuple),
        "tied_branch_supports": list(supports),
        "corrected_projected_pair": sem.pair_payload(corrected),
        "tie_mutation": {
            "mutation": "increase the leaf normal level by one",
            "mutated_normal": mutated,
            "mutated_branch_supports": list(mutated_supports),
            "expected": "tie destroyed",
            "result": "REJECTED",
        },
    }


def aggregate_corrected_columns(sem, trees, n: int):
    forms = []
    event_records = []
    signed_imbalance_histogram = Counter()
    for tree_index, tree in enumerate(trees):
        linear = [0] * (n - 1)
        hinges = defaultdict(int)
        records = []
        degrees = Counter(v for side in tree.representative for edge in side for v in edge)
        leaves = [v for v in range(n) if degrees[v] == 1]
        for leaf in leaves:
            leaf_colour = next(
                colour
                for colour, side in enumerate(tree.representative)
                if any(leaf in edge for edge in side)
            )
            for removed in tree.representative[1 - leaf_colour]:
                corrected, record = corrected_facet_event(
                    sem, tree.representative, n, leaf, removed
                )
                form = sem.literal_normal_form(corrected, n - 1)
                for rank, value in enumerate(form.linear):
                    linear[rank] += n * value
                for direction, value in form.hinges.items():
                    hinges[direction] += n * value
                signed_imbalance_histogram[record["signed_imbalance"]] += 1
                records.append(record)
        forms.append(sem.NormalForm(tuple(linear), dict(hinges)))
        event_records.append({"tree_index": tree_index, "events": records})
    directions = sorted(set().union(*(set(form.hinges) for form in forms)))
    rows = [[form.hinges.get(direction, 0) for form in forms] for direction in directions]
    rows.extend([[form.linear[rank] for form in forms] for rank in range(n - 1)])
    return Matrix(rows), directions, forms, event_records, dict(sorted(signed_imbalance_histogram.items()))


def primitive_relation(relation: Matrix) -> Matrix:
    denominator = 1
    for value in relation:
        denominator = denominator * int(value.q) // gcd(denominator, int(value.q))
    values = [int(value * denominator) for value in relation]
    divisor = reduce(gcd, (abs(value) for value in values), 0)
    if divisor:
        values = [value // divisor for value in values]
    first = next((value for value in values if value), 1)
    if first < 0:
        values = [-value for value in values]
    return Matrix(values)


def vector_payload(vector: Matrix) -> list[str]:
    return [str(Fraction(int(value.p), int(value.q))) for value in vector]


def audit(n: int, sem):
    trees = sem.tree_orbits(n)
    upper, upper_directions, _ = sem.semantic_matrix(trees, n)
    corrected, corrected_directions, _, event_records, imbalance_histogram = aggregate_corrected_columns(sem, trees, n)
    upper_rank = upper.rank()
    stacked_rank = upper.col_join(corrected).rank()
    witness = None
    for relation in upper.nullspace():
        residual = corrected * relation
        if not any(residual):
            continue
        integral = primitive_relation(relation)
        residual = corrected * integral
        witness = {
            "tree_relation": vector_payload(integral),
            "upper_semantic_residual": vector_payload(upper * integral),
            "corrected_facet_residual": vector_payload(residual),
            "first_nonzero_corrected_row": next(i for i, value in enumerate(residual) if value),
            "first_nonzero_corrected_value": str(next(value for value in residual if value)),
        }
        break
    descends = stacked_rank == upper_rank
    if descends != (witness is None):
        raise AssertionError("rank and kernel-witness verdicts disagree")
    return {
        "n": n,
        "tree_orbit_count": len(trees),
        "tree_semantic_shape": list(upper.shape),
        "tree_semantic_rank": upper_rank,
        "tree_kernel_dimension": len(trees) - upper_rank,
        "corrected_facet_shape": list(corrected.shape),
        "stacked_rank": stacked_rank,
        "corrected_facet_map_descends": descends,
        "kernel_violation": witness,
        "event_count": sum(len(record["events"]) for record in event_records),
        "signed_imbalance_histogram": {str(key): value for key, value in imbalance_histogram.items()},
        "first_event": event_records[0]["events"][0],
        "upper_hinge_direction_count": len(upper_directions),
        "corrected_hinge_direction_count": len(corrected_directions),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-n", type=int, default=5, choices=(5, 7))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sem = load_semantics()
    dimensions = [audit(n, sem) for n in range(5, args.max_n + 1, 2)]
    first_failure = next((item for item in dimensions if not item["corrected_facet_map_descends"]), None)
    report = {
        "schema": "max11-g0103-tagged-facet-correction-audit-v1",
        "result": "CORRECTED_FACET_MAP_NOT_SEMANTIC" if first_failure else "NO_COUNTEREXAMPLE_IN_TESTED_DIMENSIONS",
        "dimensions": dimensions,
        "smallest_failure_n": first_failure["n"] if first_failure else None,
        "claim_boundary": (
            "This exact test concerns the canonical event sum of the unique full-dimensional tied facet for "
            "each leaf/opposite-edge deletion, retaining the selected surviving endpoint as a branch-specific "
            "loop after leaf-coordinate deletion. Failure means that this corrected combinatorial event map "
            "still does not define a linear operation on the balanced-tree support-function quotient. It does "
            "not rule out a fixed-normal face operator, a differently weighted flag valuation, or MAX11."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "smallest_failure_n": report["smallest_failure_n"],
        "summary": [
            {
                "n": item["n"],
                "tree_rank": item["tree_semantic_rank"],
                "stacked_rank": item["stacked_rank"],
                "descends": item["corrected_facet_map_descends"],
            }
            for item in dimensions
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
