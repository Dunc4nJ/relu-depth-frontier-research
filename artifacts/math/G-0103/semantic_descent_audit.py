#!/usr/bin/env python3
"""Exact semantic-descent audit for the G-0099 leaf/bridge incidence.

The formal coefficient map sends a balanced bicoloured spanning tree on an
odd number ``n`` of vertices to the sum of the balanced bicoloured
two-component forests obtained by deleting a leaf and one edge of the
opposite colour.  This file asks the prior question that a semantic
interpretation must pass:

    does the formal map descend through the symmetrised support functions?

All orbit enumeration, stabilisers, deletion counts, and support-function
normal forms below are transcribed independently of the G-0099 producers.
Only NetworkX supplies unlabelled tree topologies; every semantic column is
then reconstructed literally over all vertex permutations.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache, reduce
import hashlib
import itertools
import json
from math import factorial, gcd
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx
from sympy import Matrix


Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class AuditError(RuntimeError):
    """Raised when an exact audit obligation fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def normalize_pair(pair: Iterable[Iterable[Sequence[int]]]) -> Pair:
    sides = []
    for raw_side in pair:
        sides.append(tuple(sorted((min(map(int, e)), max(map(int, e))) for e in raw_side)))
    require(len(sides) == 2, "a pair must have two branches")
    return sides[0], sides[1]


def relabel_pair(pair: Pair, permutation: Sequence[int]) -> Pair:
    return tuple(
        tuple(
            sorted(
                (min(permutation[u], permutation[v]), max(permutation[u], permutation[v]))
                for u, v in side
            )
        )
        for side in pair
    )  # type: ignore[return-value]


@lru_cache(maxsize=None)
def canonical_key(pair: Pair, n: int) -> Pair:
    pair = normalize_pair(pair)
    best: Pair | None = None
    for permutation in itertools.permutations(range(n)):
        labelled = relabel_pair(pair, permutation)
        candidate = min(labelled, (labelled[1], labelled[0]))
        if best is None or candidate < best:
            best = candidate
    require(best is not None, "empty relabelling group")
    return best


def stabilizer(pair: Pair, n: int) -> int:
    pair = normalize_pair(pair)
    swapped = pair[1], pair[0]
    return sum(
        relabel_pair(pair, permutation) in (pair, swapped)
        for permutation in itertools.permutations(range(n))
    )


def components(pair: Pair, n: int) -> tuple[tuple[int, ...], ...]:
    adjacency = [set() for _ in range(n)]
    for side in pair:
        for u, v in side:
            require(u != v, "loops are outside this audit")
            adjacency[u].add(v)
            adjacency[v].add(u)
    unseen = set(range(n))
    answer = []
    while unseen:
        stack = [min(unseen)]
        component: set[int] = set()
        while stack:
            vertex = stack.pop()
            if vertex in component:
                continue
            component.add(vertex)
            stack.extend(adjacency[vertex] - component)
        unseen -= component
        answer.append(tuple(sorted(component)))
    return tuple(sorted(answer))


def valid_tree(pair: Pair, n: int) -> bool:
    k = (n - 1) // 2
    flat = pair[0] + pair[1]
    return (
        n % 2 == 1
        and len(pair[0]) == len(pair[1]) == k
        and len(flat) == len(set(flat)) == n - 1
        and all(u != v for u, v in flat)
        and len(components(pair, n)) == 1
    )


def valid_forest(pair: Pair, n: int) -> bool:
    k = (n - 2) // 2
    flat = pair[0] + pair[1]
    return (
        n % 2 == 0
        and len(pair[0]) == len(pair[1]) == k
        and len(flat) == len(set(flat)) == n - 2
        and all(u != v for u, v in flat)
        and len(components(pair, n)) == 2
    )


@dataclass(frozen=True)
class Orbit:
    representative: Pair
    key: Pair
    stabilizer: int
    labelled_orbit_size: int


def tree_orbits(n: int) -> list[Orbit]:
    require(n % 2 == 1, "tree dimension must be odd")
    k = (n - 1) // 2
    representatives: dict[Pair, Pair] = {}
    for topology in nx.generators.nonisomorphic_trees(n):
        edges = tuple(sorted(tuple(sorted(map(int, e))) for e in topology.edges()))
        for chosen_tuple in itertools.combinations(range(n - 1), k):
            chosen = set(chosen_tuple)
            pair: Pair = (
                tuple(edges[i] for i in range(n - 1) if i in chosen),
                tuple(edges[i] for i in range(n - 1) if i not in chosen),
            )
            key = canonical_key(pair, n)
            representatives.setdefault(key, pair)
    answer = []
    for key in sorted(representatives):
        pair = representatives[key]
        require(valid_tree(pair, n), "invalid tree representative")
        a = stabilizer(pair, n)
        require(factorial(n) % a == 0, "nonintegral tree orbit size")
        answer.append(Orbit(pair, key, a, factorial(n) // a))
    return answer


def forest_orbits(n: int) -> list[Orbit]:
    require(n % 2 == 0, "forest dimension must be even")
    k = (n - 2) // 2
    all_edges = tuple(itertools.combinations(range(n), 2))
    representatives: dict[Pair, Pair] = {}
    for union in itertools.combinations(all_edges, 2 * k):
        for chosen_tuple in itertools.combinations(range(2 * k), k):
            chosen = set(chosen_tuple)
            pair: Pair = (
                tuple(union[i] for i in range(2 * k) if i in chosen),
                tuple(union[i] for i in range(2 * k) if i not in chosen),
            )
            if not valid_forest(pair, n):
                continue
            key = canonical_key(pair, n)
            representatives.setdefault(key, pair)
    answer = []
    for key in sorted(representatives):
        pair = representatives[key]
        a = stabilizer(pair, n)
        require(factorial(n) % a == 0, "nonintegral forest orbit size")
        answer.append(Orbit(pair, key, a, factorial(n) // a))
    return answer


def delete_event(pair: Pair, n: int, leaf: int, removed: Edge) -> Pair:
    remaining = [vertex for vertex in range(n) if vertex != leaf]
    renumber = {old: new for new, old in enumerate(remaining)}
    deleted = False
    output: list[Side] = []
    for side in pair:
        new_side = []
        for edge in side:
            if edge == removed and not deleted:
                deleted = True
                continue
            if leaf in edge:
                continue
            u, v = edge
            new_side.append(tuple(sorted((renumber[u], renumber[v]))))
        output.append(tuple(sorted(new_side)))
    require(deleted, "opposite-colour edge was not deleted")
    result = output[0], output[1]
    require(valid_forest(result, n - 1), "deletion did not produce a balanced c2 forest")
    return result


def deletion_incidence(trees: Sequence[Orbit], forests: Sequence[Orbit], n: int) -> Matrix:
    lookup = {orbit.key: row for row, orbit in enumerate(forests)}
    entries = [[0 for _ in trees] for _ in forests]
    for column, tree in enumerate(trees):
        degrees = Counter(v for side in tree.representative for edge in side for v in edge)
        leaves = [v for v in range(n) if degrees[v] == 1]
        for leaf in leaves:
            leaf_colour = next(
                colour
                for colour, side in enumerate(tree.representative)
                if any(leaf in edge for edge in side)
            )
            for removed in tree.representative[1 - leaf_colour]:
                key = canonical_key(delete_event(tree.representative, n, leaf, removed), n - 1)
                entries[lookup[key]][column] += n
        require(sum(row[column] for row in entries) == n * ((n - 1) // 2) * len(leaves), "column sum drift")
    return Matrix(entries)


@dataclass(frozen=True)
class NormalForm:
    linear: tuple[int, ...]
    hinges: dict[Direction, int]


def is_nonpositive_on_ascending_cone(direction: Direction) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


def literal_normal_form(pair: Pair, n: int) -> NormalForm:
    """Normal form of sum_sigma max(S_{sigma A},S_{sigma B})."""

    linear = [0] * n
    hinges: dict[Direction, int] = defaultdict(int)
    for order in itertools.permutations(range(n)):
        earlier: set[int] = set()
        left_word = []
        right_word = []
        for vertex in order:
            def receives(edge: Edge) -> bool:
                u, v = edge
                if u == v:
                    return vertex == u
                if vertex == u:
                    return v in earlier
                if vertex == v:
                    return u in earlier
                return False

            left_word.append(sum(receives(edge) for edge in pair[0]))
            right_word.append(sum(receives(edge) for edge in pair[1]))
            earlier.add(vertex)
        for rank, value in enumerate(left_word):
            linear[rank] += value
        raw = tuple(b - a for a, b in zip(left_word, right_word, strict=True))
        if not any(raw):
            continue
        magnitude = reduce(gcd, (abs(value) for value in raw), 0)
        first = next(value for value in raw if value)
        if first < 0:
            for rank, value in enumerate(raw):
                linear[rank] += value
            primitive = tuple(-value // magnitude for value in raw)
        else:
            primitive = tuple(value // magnitude for value in raw)
        if not is_nonpositive_on_ascending_cone(primitive):
            hinges[primitive] += magnitude
    return NormalForm(tuple(linear), dict(hinges))


def semantic_matrix(orbits: Sequence[Orbit], n: int) -> tuple[Matrix, list[Direction], list[NormalForm]]:
    columns = [literal_normal_form(orbit.representative, n) for orbit in orbits]
    directions = sorted(set().union(*(set(column.hinges) for column in columns)))
    rows = [[column.hinges.get(direction, 0) for column in columns] for direction in directions]
    rows.extend([[column.linear[rank] for column in columns] for rank in range(n)])
    return Matrix(rows), directions, columns


def q(value: object) -> str:
    return str(Fraction(int(value.p), int(value.q))) if hasattr(value, "q") else str(value)


def vector_payload(vector: Matrix) -> list[str]:
    return [q(value) for value in vector]


def pair_payload(pair: Pair) -> list[list[list[int]]]:
    return [[[u, v] for u, v in side] for side in pair]


def sha256_json(value: object) -> str:
    encoded = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(encoded).hexdigest()


def audit_dimension(n: int) -> dict[str, object]:
    trees = tree_orbits(n)
    forests = forest_orbits(n - 1)
    incidence = deletion_incidence(trees, forests, n)
    upper_semantics, upper_directions, upper_forms = semantic_matrix(trees, n)
    lower_semantics, lower_directions, lower_forms = semantic_matrix(forests, n - 1)
    lower_after_incidence = lower_semantics * incidence
    stacked = upper_semantics.col_join(lower_after_incidence)
    descends = stacked.rank() == upper_semantics.rank()

    def first_kernel_violation(lower_map: Matrix) -> dict[str, object] | None:
        for relation in upper_semantics.nullspace():
            defect = lower_map * relation
            if not any(value != 0 for value in defect):
                continue
            common_denominator = 1
            for value in relation:
                common_denominator = common_denominator * int(value.q) // gcd(common_denominator, int(value.q))
            scaled = [int(value * common_denominator) for value in relation]
            divisor = reduce(gcd, (abs(value) for value in scaled), 0)
            if divisor:
                scaled = [value // divisor for value in scaled]
            integral = Matrix(scaled)
            defect = lower_map * integral
            return {
                "upper_tree_relation": vector_payload(integral),
                "upper_semantic_residual": vector_payload(upper_semantics * integral),
                "lower_semantic_residual": vector_payload(defect),
                "first_nonzero_lower_row": next(i for i, value in enumerate(defect) if value != 0),
                "first_nonzero_lower_value": q(next(value for value in defect if value != 0)),
            }
        return None

    kernel_witness = first_kernel_violation(lower_after_incidence)

    # Predeclared potency mutation: increment the lexicographically first
    # nonzero coefficient of D.  A descent audit that still accepted this
    # one-event counting defect would not be discriminative.
    first_nonzero = next(
        (row, column)
        for row in range(incidence.rows)
        for column in range(incidence.cols)
        if incidence[row, column] != 0
    )
    mutated_incidence = incidence.copy()
    mutated_incidence[first_nonzero] += 1
    mutated_lower_map = lower_semantics * mutated_incidence
    mutated_stacked_rank = upper_semantics.col_join(mutated_lower_map).rank()
    mutation_witness = first_kernel_violation(mutated_lower_map)
    require(mutated_stacked_rank > upper_semantics.rank(), "first-entry incidence mutant escaped rank audit")
    require(mutation_witness is not None, "first-entry incidence mutant lacks a kernel witness")

    # The exact double-count identity that fixes the n factor in D.
    reverse = [[0 for _ in trees] for _ in forests]
    for forest_index, forest in enumerate(forests):
        comps = components(forest.representative, n - 1)
        bridges = tuple((u, v) for u in comps[0] for v in comps[1])
        tree_lookup = {tree.key: column for column, tree in enumerate(trees)}
        for leaf_colour in (0, 1):
            bridge_colour = 1 - leaf_colour
            for endpoint in range(n - 1):
                for bridge in bridges:
                    sides = [list(forest.representative[0]), list(forest.representative[1])]
                    sides[leaf_colour].append(tuple(sorted((endpoint, n - 1))))
                    sides[bridge_colour].append(tuple(sorted(bridge)))
                    pair: Pair = tuple(tuple(sorted(side)) for side in sides)  # type: ignore[assignment]
                    require(valid_tree(pair, n), "reverse extension did not produce a tree")
                    reverse[forest_index][tree_lookup[canonical_key(pair, n)]] += 1
    weighted_checks = 0
    for f, forest in enumerate(forests):
        for t, tree in enumerate(trees):
            direct_r = int(incidence[f, t]) // n
            reverse_q = reverse[f][t]
            require(
                tree.labelled_orbit_size * direct_r
                == n * forest.labelled_orbit_size * reverse_q,
                "orbit-weighted double count failed",
            )
            require(forest.stabilizer * direct_r == tree.stabilizer * reverse_q, "stabilizer double count failed")
            weighted_checks += direct_r != 0 or reverse_q != 0

    report = {
        "n": n,
        "tree_orbit_count": len(trees),
        "forest_orbit_count": len(forests),
        "upper_semantic_shape": list(upper_semantics.shape),
        "upper_semantic_rank": upper_semantics.rank(),
        "upper_kernel_dimension": len(trees) - upper_semantics.rank(),
        "lower_semantic_shape": list(lower_semantics.shape),
        "lower_semantic_rank": lower_semantics.rank(),
        "incidence_shape": list(incidence.shape),
        "incidence_rank": incidence.rank(),
        "stacked_rank": stacked.rank(),
        "semantic_descent_holds": descends,
        "kernel_violation": kernel_witness,
        "one_incidence_mutation": {
            "mutation": "increment the lexicographically first nonzero D entry by one",
            "entry": list(first_nonzero),
            "original_value": int(incidence[first_nonzero]),
            "mutated_value": int(mutated_incidence[first_nonzero]),
            "mutated_stacked_rank": mutated_stacked_rank,
            "expected": "REJECTED",
            "result": "REJECTED",
            "kernel_witness": mutation_witness,
        },
        "orbit_weighted_double_count": "N_T r(T,F) = n N_F q(F,T)",
        "stabilizer_double_count": "a_F r(T,F) = a_T q(F,T)",
        "weighted_nonzero_entries_checked": weighted_checks,
        "tree_orbits": [
            {
                "index": index,
                "representative": pair_payload(orbit.representative),
                "stabilizer": orbit.stabilizer,
                "labelled_orbit_size": orbit.labelled_orbit_size,
            }
            for index, orbit in enumerate(trees)
        ],
        "forest_orbits": [
            {
                "index": index,
                "representative": pair_payload(orbit.representative),
                "stabilizer": orbit.stabilizer,
                "labelled_orbit_size": orbit.labelled_orbit_size,
            }
            for index, orbit in enumerate(forests)
        ],
        "D_matrix": [[int(incidence[row, column]) for column in range(incidence.cols)] for row in range(incidence.rows)],
        "upper_hinge_directions": [list(direction) for direction in upper_directions],
        "lower_hinge_directions": [list(direction) for direction in lower_directions],
        "upper_normal_forms_sha256": sha256_json([
            {"linear": list(form.linear), "hinges": sorted((list(k), v) for k, v in form.hinges.items())}
            for form in upper_forms
        ]),
        "lower_normal_forms_sha256": sha256_json([
            {"linear": list(form.linear), "hinges": sorted((list(k), v) for k, v in form.hinges.items())}
            for form in lower_forms
        ]),
    }
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-n", type=int, default=7, choices=(5, 7))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    # n=3 has the degenerate zero-edge lower atom.  Its two branch colours
    # coincide, so the ordinary unordered-colour stabilizer convention has an
    # extra factor two and its support function is identically zero.  The
    # first nondegenerate leaf/bridge diagram is therefore n=5 -> 4.
    dimensions = [audit_dimension(n) for n in range(5, args.max_n + 1, 2)]
    first_failure = next((item for item in dimensions if not item["semantic_descent_holds"]), None)
    report = {
        "schema": "max11-g0103-semantic-descent-audit-v1",
        "result": "SEMANTIC_DESCENT_COUNTEREXAMPLE" if first_failure else "NO_COUNTEREXAMPLE_IN_TESTED_DIMENSIONS",
        "dimensions": dimensions,
        "smallest_tested_failure_n": first_failure["n"] if first_failure else None,
        "mutation_control": "Each tested dimension increments the first nonzero D entry; see dimensions[].one_incidence_mutation.",
        "claim_boundary": (
            "This exact finite audit decides whether the specific formal leaf/opposite-colour-edge deletion map "
            "D descends to a linear map on the spans of the symmetrised balanced-tree support functions in the "
            "tested dimensions. A failure rules out every support-function operation whose restriction to those "
            "atoms is exactly D. It does not rule out a corrected map with additional semantic terms, a nonlinear "
            "operation, or an unrelated MAX11 construction."
        ),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "smallest_tested_failure_n": report["smallest_tested_failure_n"],
        "summary": [
            {
                "n": item["n"],
                "tree_orbits": item["tree_orbit_count"],
                "upper_rank": item["upper_semantic_rank"],
                "stacked_rank": item["stacked_rank"],
                "descends": item["semantic_descent_holds"],
            }
            for item in dimensions
        ],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
