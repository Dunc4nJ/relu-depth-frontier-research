#!/usr/bin/env python3
"""Exact combinatorial n=10 -> n=11 leaf/bridge compression.

This producer never builds an n=11 semantic column.  It constructs the sparse
equivariant incidence D from every balanced bicoloured spanning-tree orbit on
11 vertices to every balanced bicoloured two-component spanning-forest orbit
on 10 vertices:

    D(F,T) = 11 * #{(leaf, opposite-colour edge) of T deleting to F}.

Coloured forests are canonically labelled by the AHU centre code, with a final
minimum over the global colour swap.  The same recursion computes exact
fixed-colour automorphism counts.  Reverse extensions are enumerated
separately, giving a stabilizer-weighted double-count audit.

The sparse modular echelon calculation is used only as an integer-minor
witness: full row rank modulo p implies that the selected integer minor has
determinant not divisible by p, hence is nonsingular over Q.  In that event,
membership of any rational target in the incidence image is an exact
characteristic-zero conclusion, not merely a modular heuristic.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache, reduce
import hashlib
import json
from math import factorial, lcm
import os
from pathlib import Path
import platform
import time
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TREE_UNIVERSE = ROOT / "artifacts/math/G-0023/all_tree_universe_v1.json"
MAX10_CERTIFICATE = (
    ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
)
G0090_MAX10_REPLAY = ROOT / "artifacts/math/G-0090/known_certificate_normal_form_n10_v1.json"
LOWER_GATE = HERE / "leaf_bridge_complete_v1.json"
SCHEMA = "max11-g0099-leaf-bridge-n10-n11-v1"
PRIMES = (1_000_003, 1_000_033)

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class GateError(RuntimeError):
    """A required exact check or planted control failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def normalize_pair(raw: Iterable[Iterable[Sequence[int]]]) -> Pair:
    sides: list[Side] = []
    for raw_side in raw:
        side = []
        for edge in raw_side:
            u, v = map(int, edge)
            side.append((min(u, v), max(u, v)))
        sides.append(tuple(sorted(side)))
    require(len(sides) == 2, "pair must have two branches")
    return sides[0], sides[1]


def pair_payload(pair: Pair) -> list[list[list[int]]]:
    return [[[u, v] for u, v in side] for side in pair]


def adjacency(pair: Pair, n: int, *, swap: int = 0) -> list[list[tuple[int, int]]]:
    output: list[list[tuple[int, int]]] = [[] for _ in range(n)]
    seen: set[Edge] = set()
    for colour, side in enumerate(pair):
        for u, v in side:
            require(0 <= u < v < n, "forest code requires simple in-range nonloops")
            require((u, v) not in seen, "forest code requires disjoint colour edges")
            seen.add((u, v))
            output[u].append((v, colour ^ swap))
            output[v].append((u, colour ^ swap))
    return output


def components_from_adjacency(graph: Sequence[Sequence[tuple[int, int]]]) -> list[tuple[int, ...]]:
    unseen = set(range(len(graph)))
    components: list[tuple[int, ...]] = []
    while unseen:
        root = min(unseen)
        stack = [root]
        component: set[int] = set()
        while stack:
            vertex = stack.pop()
            if vertex in component:
                continue
            component.add(vertex)
            stack.extend(neighbour for neighbour, _colour in graph[vertex] if neighbour not in component)
        unseen -= component
        components.append(tuple(sorted(component)))
    return sorted(components)


def tree_centres(
    graph: Sequence[Sequence[tuple[int, int]]], component: Sequence[int]
) -> tuple[int, ...]:
    if len(component) <= 2:
        return tuple(sorted(component))
    component_set = set(component)
    degree = {
        vertex: sum(neighbour in component_set for neighbour, _colour in graph[vertex])
        for vertex in component
    }
    leaves = [vertex for vertex in component if degree[vertex] <= 1]
    remaining = len(component)
    while remaining > 2:
        remaining -= len(leaves)
        next_leaves: list[int] = []
        for vertex in leaves:
            for neighbour, _colour in graph[vertex]:
                if neighbour in component_set and degree[neighbour] > 0:
                    degree[neighbour] -= 1
                    if degree[neighbour] == 1:
                        next_leaves.append(neighbour)
            degree[vertex] = 0
        leaves = next_leaves
    return tuple(sorted(leaves))


def rooted_code_and_aut(
    graph: Sequence[Sequence[tuple[int, int]]], vertex: int, parent: int | None
) -> tuple[str, int]:
    children: list[tuple[str, int]] = []
    for neighbour, colour in graph[vertex]:
        if neighbour == parent:
            continue
        child_code, child_aut = rooted_code_and_aut(graph, neighbour, vertex)
        children.append((f"{colour}{child_code}", child_aut))
    children.sort()
    multiplicities = Counter(code for code, _aut in children)
    automorphisms = 1
    for _code, child_aut in children:
        automorphisms *= child_aut
    for count in multiplicities.values():
        automorphisms *= factorial(count)
    return "(" + "".join(code for code, _aut in children) + ")", automorphisms


def component_code_and_aut(
    graph: Sequence[Sequence[tuple[int, int]]], component: Sequence[int]
) -> tuple[str, int]:
    centres = tree_centres(graph, component)
    if len(centres) == 1:
        rooted, automorphisms = rooted_code_and_aut(graph, centres[0], None)
        return "V" + rooted, automorphisms
    require(len(centres) == 2, "tree centre census must be one or two")
    left, right = centres
    central_colours = [colour for neighbour, colour in graph[left] if neighbour == right]
    require(len(central_colours) == 1, "bicentre edge missing")
    left_code, left_aut = rooted_code_and_aut(graph, left, right)
    right_code, right_aut = rooted_code_and_aut(graph, right, left)
    halves = sorted((left_code, right_code))
    automorphisms = left_aut * right_aut * (2 if left_code == right_code else 1)
    return f"E{central_colours[0]}{halves[0]}{halves[1]}", automorphisms


def fixed_forest_code_and_aut(pair: Pair, n: int, *, swap: int) -> tuple[str, int]:
    graph = adjacency(pair, n, swap=swap)
    components = components_from_adjacency(graph)
    # Every component must be a tree, including a possible isolated vertex.
    for component in components:
        component_set = set(component)
        edges = sum(
            neighbour in component_set
            for vertex in component
            for neighbour, _colour in graph[vertex]
        ) // 2
        require(edges == len(component) - 1, "AHU input is not a forest")
    coded = [component_code_and_aut(graph, component) for component in components]
    coded.sort()
    multiplicities = Counter(code for code, _aut in coded)
    automorphisms = 1
    for _code, component_aut in coded:
        automorphisms *= component_aut
    for count in multiplicities.values():
        automorphisms *= factorial(count)
    return "|".join(code for code, _aut in coded), automorphisms


@lru_cache(maxsize=None)
def forest_key_and_stabilizer(pair: Pair, n: int) -> tuple[str, int]:
    fixed, fixed_aut = fixed_forest_code_and_aut(pair, n, swap=0)
    swapped, swapped_aut = fixed_forest_code_and_aut(pair, n, swap=1)
    require(fixed_aut == swapped_aut, "colour swap changed fixed automorphism count")
    # If the swapped colouring is isomorphic, its isomorphism torsor has the
    # same cardinality as the fixed-colour automorphism group.
    stabilizer = fixed_aut * (2 if fixed == swapped else 1)
    return min(fixed, swapped), stabilizer


def forest_key(pair: Pair, n: int) -> str:
    return forest_key_and_stabilizer(normalize_pair(pair), n)[0]


def is_balanced_tree(pair: Pair, n: int) -> bool:
    if len(pair[0]) != len(pair[1]) or len(pair[0]) + len(pair[1]) != n - 1:
        return False
    try:
        graph = adjacency(pair, n)
    except GateError:
        return False
    return len(components_from_adjacency(graph)) == 1


def is_balanced_c2_forest(pair: Pair, n: int) -> bool:
    if len(pair[0]) != len(pair[1]) or len(pair[0]) + len(pair[1]) != n - 2:
        return False
    try:
        graph = adjacency(pair, n)
    except GateError:
        return False
    return len(components_from_adjacency(graph)) == 2


def delete_leaf_and_edge(pair: Pair, leaf: int, removed: Edge, n: int) -> Pair:
    remaining = [vertex for vertex in range(n) if vertex != leaf]
    relabel = {old: new for new, old in enumerate(remaining)}
    removed_once = False
    sides: list[Side] = []
    for side in pair:
        output: list[Edge] = []
        for edge in side:
            if edge == removed and not removed_once:
                removed_once = True
                continue
            if leaf in edge:
                continue
            u, v = edge
            output.append(tuple(sorted((relabel[u], relabel[v]))))
        sides.append(tuple(sorted(output)))
    require(removed_once, "opposite-colour edge removal failed")
    return sides[0], sides[1]


@dataclass(frozen=True)
class TreeOrbit:
    index: int
    representative: Pair
    key: str
    stabilizer: int
    labelled_orbit_size: int


@dataclass(frozen=True)
class ForestOrbit:
    index: int
    representative: Pair
    key: str
    stabilizer: int
    labelled_orbit_size: int


def load_tree_orbits() -> tuple[list[TreeOrbit], dict[str, object]]:
    raw = json.loads(TREE_UNIVERSE.read_text(encoding="utf-8"))
    subject = raw.get("n11_subject")
    require(isinstance(subject, dict), "G0023 n11 subject missing")
    representatives_raw = subject.get("representatives")
    require(isinstance(representatives_raw, list) and len(representatives_raw) == 12_459, "tree census drift")
    trees: list[TreeOrbit] = []
    keys: set[str] = set()
    for index, raw_pair in enumerate(representatives_raw):
        pair = normalize_pair(raw_pair)
        require(is_balanced_tree(pair, 11), "G0023 representative is not a spanning tree")
        key, stabilizer = forest_key_and_stabilizer(pair, 11)
        require(key not in keys, "AHU code merged distinct G0023 tree representatives")
        keys.add(key)
        require(factorial(11) % stabilizer == 0, "nonintegral labelled tree orbit")
        trees.append(TreeOrbit(index, pair, key, stabilizer, factorial(11) // stabilizer))
    return trees, {
        "source": str(TREE_UNIVERSE.relative_to(ROOT)),
        "source_sha256": sha256_path(TREE_UNIVERSE),
        "source_representative_pairs_sha256": subject.get("representative_pairs_sha256"),
        "tree_orbit_count": len(trees),
        "AHU_key_list_sha256": canonical_sha256([tree.key for tree in trees]),
    }


def direct_incidence(
    trees: Sequence[TreeOrbit],
) -> tuple[list[ForestOrbit], list[dict[int, int]], dict[str, object]]:
    begun = time.perf_counter()
    columns_by_key: list[Counter[str]] = []
    forest_representatives: dict[str, Pair] = {}
    leaf_histogram: Counter[int] = Counter()
    for tree in trees:
        if tree.index and tree.index % 2_000 == 0:
            print(f"DIRECT trees={tree.index}/{len(trees)} forests={len(forest_representatives)}", flush=True)
        degrees = Counter(vertex for side in tree.representative for edge in side for vertex in edge)
        leaves = sorted(vertex for vertex in range(11) if degrees[vertex] == 1)
        leaf_histogram[len(leaves)] += 1
        column: Counter[str] = Counter()
        for leaf in leaves:
            leaf_colour = next(
                colour
                for colour, side in enumerate(tree.representative)
                if any(leaf in edge for edge in side)
            )
            for removed in tree.representative[1 - leaf_colour]:
                forest = delete_leaf_and_edge(tree.representative, leaf, removed, 11)
                require(is_balanced_c2_forest(forest, 10), "deletion failed to produce c2 forest")
                key = forest_key(forest, 10)
                forest_representatives.setdefault(key, forest)
                column[key] += 1
        require(sum(column.values()) == 5 * len(leaves), "direct incidence column sum drift")
        columns_by_key.append(column)

    sorted_keys = sorted(forest_representatives)
    key_to_index = {key: index for index, key in enumerate(sorted_keys)}
    forests: list[ForestOrbit] = []
    for index, key in enumerate(sorted_keys):
        pair = forest_representatives[key]
        checked_key, stabilizer = forest_key_and_stabilizer(pair, 10)
        require(checked_key == key, "forest key replay drift")
        require(factorial(10) % stabilizer == 0, "nonintegral labelled forest orbit")
        forests.append(ForestOrbit(index, pair, key, stabilizer, factorial(10) // stabilizer))
    columns = [
        {key_to_index[key]: count for key, count in column.items()}
        for column in columns_by_key
    ]
    return forests, columns, {
        "forest_orbit_count": len(forests),
        "incidence_nonzeros": sum(len(column) for column in columns),
        "incidence_sum": sum(sum(column.values()) for column in columns),
        "leaf_count_histogram": dict(sorted(leaf_histogram.items())),
        "forest_AHU_key_list_sha256": canonical_sha256(sorted_keys),
        "seconds": round(time.perf_counter() - begun, 6),
    }


def reverse_incidence(
    trees: Sequence[TreeOrbit], forests: Sequence[ForestOrbit]
) -> tuple[list[dict[int, int]], dict[str, object]]:
    begun = time.perf_counter()
    tree_by_key = {tree.key: tree.index for tree in trees}
    rows: list[dict[int, int]] = []
    for forest in forests:
        if forest.index and forest.index % 500 == 0:
            print(f"REVERSE forests={forest.index}/{len(forests)}", flush=True)
        graph = adjacency(forest.representative, 10)
        components = components_from_adjacency(graph)
        require(len(components) == 2, "reverse incidence received non-c2 forest")
        bridges = tuple((u, v) for u in components[0] for v in components[1])
        row: Counter[int] = Counter()
        for leaf_colour in (0, 1):
            bridge_colour = 1 - leaf_colour
            for endpoint in range(10):
                for bridge in bridges:
                    sides = [list(forest.representative[0]), list(forest.representative[1])]
                    sides[leaf_colour].append(tuple(sorted((endpoint, 10))))
                    sides[bridge_colour].append(tuple(sorted(bridge)))
                    tree: Pair = tuple(tuple(sorted(side)) for side in sides)  # type: ignore[assignment]
                    require(is_balanced_tree(tree, 11), "reverse extension failed to produce tree")
                    key = forest_key(tree, 11)
                    require(key in tree_by_key, "reverse extension left G0023 tree quotient")
                    row[tree_by_key[key]] += 1
        expected = 20 * len(components[0]) * len(components[1])
        require(sum(row.values()) == expected, "reverse incidence row sum drift")
        rows.append(dict(row))
    return rows, {
        "reverse_nonzeros": sum(len(row) for row in rows),
        "reverse_sum": sum(sum(row.values()) for row in rows),
        "seconds": round(time.perf_counter() - begun, 6),
    }


def audit_double_count(
    trees: Sequence[TreeOrbit],
    forests: Sequence[ForestOrbit],
    direct_columns: Sequence[dict[int, int]],
    reverse_rows: Sequence[dict[int, int]],
) -> dict[str, object]:
    checked = 0
    digest_records: list[tuple[int, int, int, int]] = []
    first: tuple[int, int, int, int] | None = None
    for tree in trees:
        direct = direct_columns[tree.index]
        for forest_index in sorted(set(direct) | {i for i, row in enumerate(reverse_rows) if tree.index in row}):
            r = int(direct.get(forest_index, 0))
            q = int(reverse_rows[forest_index].get(tree.index, 0))
            forest = forests[forest_index]
            require(
                tree.labelled_orbit_size * r == 11 * forest.labelled_orbit_size * q,
                "labelled-orbit double count failed",
            )
            require(forest.stabilizer * r == tree.stabilizer * q, "stabilizer double count failed")
            require((r == 0) == (q == 0), "direct/reverse support mismatch")
            if r:
                record = (forest_index, tree.index, r, q)
                digest_records.append(record)
                first = record if first is None else first
                checked += 1
    require(first is not None, "incidence is empty")
    forest_index, tree_index, r, q = first
    mutated_left = trees[tree_index].labelled_orbit_size * (r + 1)
    unchanged_right = 11 * forests[forest_index].labelled_orbit_size * q
    require(mutated_left != unchanged_right, "one-incidence mutation escaped")
    return {
        "nonzero_pairs_checked": checked,
        "all_weighted_equalities_hold": True,
        "weighted_identity": "N_T*r(T,F)=11*N_F*q(F,T)",
        "stabilizer_identity": "a_F*r(T,F)=a_T*q(F,T)",
        "ruess_basis_incidence": "D(F,T)=11*r(T,F)",
        "nonzero_records_sha256": canonical_sha256(digest_records),
        "one_incidence_mutation": {
            "forest": forest_index,
            "tree": tree_index,
            "mutation": "r += 1",
            "mutated_left": mutated_left,
            "unchanged_right": unchanged_right,
            "rejected": True,
        },
    }


def load_max10_target(forests: Sequence[ForestOrbit]) -> tuple[list[Fraction], dict[str, object]]:
    raw = json.loads(MAX10_CERTIFICATE.read_text(encoding="utf-8"))
    require(raw.get("n") == 10 and isinstance(raw.get("terms"), list), "MAX10 certificate malformed")
    forest_by_key = {forest.key: forest.index for forest in forests}
    target = [Fraction(0) for _ in forests]
    accepted: list[dict[str, object]] = []
    for term_index, item in enumerate(raw["terms"]):
        pair = normalize_pair(
            tuple(tuple((int(u) - 1, int(v) - 1) for u, v in side) for side in item["pair"])
        )
        if not is_balanced_c2_forest(pair, 10):
            continue
        key = forest_key(pair, 10)
        require(key in forest_by_key, "MAX10 c2 term left complete deletion quotient")
        forest_index = forest_by_key[key]
        coefficient = Fraction(item["coefficient"])
        target[forest_index] += coefficient
        accepted.append(
            {
                "term_index": term_index,
                "forest_index": forest_index,
                "coefficient": str(coefficient),
            }
        )
    require(len(accepted) == 252, "MAX10 dominant c2 term count drift")
    require(sum(value != 0 for value in target) == 252, "MAX10 c2 orbit coefficients collided/cancelled")
    replay = json.loads(G0090_MAX10_REPLAY.read_text(encoding="utf-8"))
    n10 = next(item for item in replay["certificates"] if item["n"] == 10)
    require(n10["exact_identity_replayed"] is True, "pinned MAX10 semantic replay not PASS")
    return target, {
        "certificate": str(MAX10_CERTIFICATE.relative_to(ROOT)),
        "certificate_sha256": sha256_path(MAX10_CERTIFICATE),
        "certificate_terms": len(raw["terms"]),
        "dominant_c2_terms": len(accepted),
        "dominant_c2_distinct_nonzero_orbits": sum(value != 0 for value in target),
        "dominant_c2_support_sha256": canonical_sha256(accepted),
        "semantic_positive_control": {
            "source": str(G0090_MAX10_REPLAY.relative_to(ROOT)),
            "source_sha256": sha256_path(G0090_MAX10_REPLAY),
            "exact_identity_replayed": True,
            "terms": n10["terms"],
            "residual_hinge_count": n10["residual_hinge_count"],
            "linear_numerators_over_lcm": n10["linear_numerators_over_lcm"],
        },
    }


def sparse_full_row_rank_witness(
    columns: Sequence[dict[int, int]], row_count: int, prime: int, target: Sequence[Fraction]
) -> dict[str, object]:
    begun = time.perf_counter()
    basis: dict[int, dict[int, int]] = {}
    selected_columns: list[int] = []
    pivot_rows: list[int] = []
    pivot_values: list[int] = []
    for column_index, raw in enumerate(columns):
        vector = {row: (11 * value) % prime for row, value in raw.items() if value % prime}
        while vector:
            pivot = min(vector)
            existing = basis.get(pivot)
            if existing is None:
                pivot_value = vector[pivot]
                inverse = pow(pivot_value, -1, prime)
                vector = {row: (value * inverse) % prime for row, value in vector.items() if value % prime}
                basis[pivot] = vector
                selected_columns.append(column_index)
                pivot_rows.append(pivot)
                pivot_values.append(pivot_value)
                break
            factor = vector[pivot]
            for row, value in existing.items():
                updated = (vector.get(row, 0) - factor * value) % prime
                if updated:
                    vector[row] = updated
                else:
                    vector.pop(row, None)
        if len(basis) == row_count:
            break

    denominator = reduce(lcm, (value.denominator for value in target), 1)
    target_mod = {
        row: (
            value.numerator
            * pow(value.denominator, -1, prime)
        ) % prime
        for row, value in enumerate(target)
        if value
    }
    reduced_target = dict(target_mod)
    # Every normalized basis vector has its pivot at its least row.  Reducing
    # in increasing pivot-row order is therefore triangular; insertion order
    # is not, because a later independent column may introduce a smaller pivot.
    for pivot in sorted(pivot_rows):
        factor = reduced_target.get(pivot, 0)
        if not factor:
            continue
        for row, value in basis[pivot].items():
            updated = (reduced_target.get(row, 0) - factor * value) % prime
            if updated:
                reduced_target[row] = updated
            else:
                reduced_target.pop(row, None)

    full_row_rank = len(basis) == row_count
    exact_image = full_row_rank
    # If full row rank holds modulo p, the selected square integer minor has
    # determinant nonzero modulo p and therefore nonzero over Z/Q.  No rational
    # solve or reconstruction assumption is involved.
    return {
        "prime": prime,
        "rows": row_count,
        "columns": len(columns),
        "rank_mod_p": len(basis),
        "full_row_rank_mod_p": full_row_rank,
        "selected_integer_minor_size": len(selected_columns),
        "selected_columns": selected_columns,
        "pivot_rows": pivot_rows,
        "nonzero_pivot_values_mod_p": pivot_values,
        "selected_columns_sha256": canonical_sha256(selected_columns),
        "pivot_rows_sha256": canonical_sha256(pivot_rows),
        "pivot_values_sha256": canonical_sha256(pivot_values),
        "target_denominator": denominator,
        "target_reduces_to_zero_mod_p": not reduced_target,
        "target_remainder_mod_p": sorted(reduced_target.items()),
        "exact_Q_full_row_rank": full_row_rank,
        "exact_Q_target_in_image": exact_image,
        "exact_implication": (
            "The sparse elimination selects a square integer minor with determinant nonzero "
            "modulo p. Its determinant is therefore a nonzero integer, so D is surjective over Q "
            "and the rational MAX10 c2 target has a rational preimage."
            if full_row_rank
            else "No characteristic-zero claim from this rank calculation."
        ),
        "seconds": round(time.perf_counter() - begun, 6),
    }


def lower_AHU_crosscheck() -> dict[str, object]:
    lower = json.loads(LOWER_GATE.read_text(encoding="utf-8"))
    require(lower.get("result") == "EXACT_MEMBERSHIP", "lower gate is not exact-positive")
    tree_keys: set[str] = set()
    forest_keys: set[str] = set()
    for item in lower["tree_orbits"]:
        pair = normalize_pair(item["representative_zero_based"])
        key, stabilizer = forest_key_and_stabilizer(pair, 7)
        require(stabilizer == int(item["stabilizer"]), "AHU/brute tree stabilizer disagreement")
        tree_keys.add(key)
    for item in lower["forest_orbits"]:
        pair = normalize_pair(item["representative_zero_based"])
        key, stabilizer = forest_key_and_stabilizer(pair, 6)
        require(stabilizer == int(item["stabilizer"]), "AHU/brute forest stabilizer disagreement")
        forest_keys.add(key)
    require(len(tree_keys) == 53 and len(forest_keys) == 11, "AHU lower quotient census disagreement")
    return {
        "source": str(LOWER_GATE.relative_to(ROOT)),
        "source_sha256": sha256_path(LOWER_GATE),
        "AHU_vs_bruteforce_tree_partition_count": len(tree_keys),
        "AHU_vs_bruteforce_forest_partition_count": len(forest_keys),
        "all_stabilizers_agree": True,
        "lower_complete_semantic_incidence_gate": lower["result"],
    }


def sparse_payload(columns: Sequence[dict[int, int]]) -> list[list[list[int]]]:
    return [
        [[row, int(value)] for row, value in sorted(column.items())]
        for column in columns
    ]


def sparse_reverse_payload(rows: Sequence[dict[int, int]]) -> list[list[list[int]]]:
    return [
        [[tree, int(value)] for tree, value in sorted(row.items())]
        for row in rows
    ]


def write_json_atomic(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prime", type=int, default=PRIMES[0], choices=PRIMES)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    begun = time.perf_counter()
    lower_control = lower_AHU_crosscheck()
    trees, tree_source = load_tree_orbits()
    forests, direct_columns, direct_report = direct_incidence(trees)
    reverse_rows, reverse_report = reverse_incidence(trees, forests)
    double_count = audit_double_count(trees, forests, direct_columns, reverse_rows)
    target, target_report = load_max10_target(forests)
    rank = sparse_full_row_rank_witness(direct_columns, len(forests), args.prime, target)
    sparse = sparse_payload(direct_columns)
    reverse_sparse = sparse_reverse_payload(reverse_rows)

    exact_positive = bool(rank["exact_Q_target_in_image"])
    report = {
        "schema": SCHEMA,
        "result": "EXACT_INCIDENCE_SURJECTION" if exact_positive else "NO_Q_CLAIM",
        "claim_class": "exact" if exact_positive else "modular",
        "outcome": "positive" if exact_positive else "no-claim",
        "tree_source": tree_source,
        "direct_incidence": direct_report,
        "reverse_incidence": reverse_report,
        "double_count": double_count,
        "max10_target": target_report,
        "rank_and_image": rank,
        "lower_analogue_control": lower_control,
        "forest_orbits": [
            {
                "index": forest.index,
                "representative_zero_based": pair_payload(forest.representative),
                "AHU_key": forest.key,
                "stabilizer": forest.stabilizer,
                "labelled_orbit_size": forest.labelled_orbit_size,
                "target_coefficient": str(target[forest.index]),
            }
            for forest in forests
        ],
        "tree_stabilizers": [tree.stabilizer for tree in trees],
        "tree_labelled_orbit_sizes": [tree.labelled_orbit_size for tree in trees],
        "sparse_direct_r_columns": sparse,
        "sparse_direct_r_columns_sha256": canonical_sha256(sparse),
        "sparse_reverse_q_rows": reverse_sparse,
        "sparse_reverse_q_rows_sha256": canonical_sha256(reverse_sparse),
        "excluded_tree_columns_negative_control": {
            "claim_class": "exact",
            "outcome": "negative",
            "reason": (
                "After excluding every tree column, D has no columns and its image is zero; "
                "the MAX10 c2 target has 252 nonzero coordinates."
            ),
        },
        "compression": {
            "dense_entries_avoided": len(forests) * len(trees),
            "stored_nonzeros": direct_report["incidence_nonzeros"],
            "sparsity_fraction": direct_report["incidence_nonzeros"] / (len(forests) * len(trees)),
            "semantic_columns_built": 0,
            "meaning": (
                "This tests the proposed equivariant coefficient-transfer compression only. "
                "It does not test whether a MAX11 semantic solution can meet the constraint."
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "pid": os.getpid(),
        },
        "producer_sha256_before_output": sha256_path(Path(__file__).resolve()),
        "wall_seconds": round(time.perf_counter() - begun, 6),
        "claim_boundary": (
            "Exact: quotient/stabilizer census, direct/reverse incidence, weighted double count, "
            "one-entry mutation rejection, MAX10 certificate projection, and characteristic-zero "
            "surjectivity if a full-row-rank modular minor is found. No-claim: the incidence "
            "condition is not known to be semantically necessary, no n11 semantic columns are "
            "built, and no MAX11 representation or obstruction follows."
        ),
    }
    write_json_atomic(args.output.resolve(), report)
    print(
        f"G0099_{report['result']} trees={len(trees)} forests={len(forests)} "
        f"nnz={direct_report['incidence_nonzeros']} rank={rank['rank_mod_p']} "
        f"wall={report['wall_seconds']} output={args.output}",
        flush=True,
    )
    return 0 if exact_positive else 2


if __name__ == "__main__":
    raise SystemExit(main())
