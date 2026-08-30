#!/usr/bin/env python3
"""Exact n=6 -> n=7 leaf/bridge incidence potency gate.

This is a deliberately small analogue of the proposed n=10 -> n=11
compression.  Its domain is the quotient of balanced two-coloured spanning
trees by simultaneous vertex relabelling and one global colour swap.  Its
codomain is the analogous quotient of full-active two-coloured two-component
forests.  For every tree it counts the choices

    (leaf, opposite-colour edge)

whose deletion gives a forest.  A separately enumerated reverse map attaches
a new coloured leaf and an opposite-colour bridge across the old components.

The semantic part imports the independently tested subset-DP normal form from
G-0090.  That dependency is hashed and is stated explicitly in the report;
this producer is therefore not an independent semantic implementation.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from functools import lru_cache, reduce
import gzip
import hashlib
import importlib.util
import itertools
import json
from math import factorial, lcm
import os
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Iterator, Sequence

import networkx as nx
import numpy as np
from flint import fmpq_mat, fmpz_mat, nmod_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0090_PATH = ROOT / "artifacts/math/G-0090/known_certificate_normal_form.py"
UNIVERSE_PATH = (
    ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
CERTIFICATE_DIR = ROOT / "literature/repos/max-relu-certificates/certificates"
SCHEMA = "max11-g0099-leaf-bridge-n6-n7-v1"
PRIMES = (1_000_003, 1_000_033)

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
PairKey = Pair
Direction = tuple[int, ...]


class GateError(RuntimeError):
    """A required exact or planted-control check failed."""


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def normalize_pair(pair: Iterable[Iterable[Sequence[int]]]) -> Pair:
    sides: list[Side] = []
    for raw_side in pair:
        sides.append(
            tuple(sorted((min(map(int, edge)), max(map(int, edge))) for edge in raw_side))
        )
    require(len(sides) == 2, "a pair needs exactly two branches")
    return sides[0], sides[1]


def pair_payload(pair: Pair) -> list[list[list[int]]]:
    return [[[u, v] for u, v in side] for side in pair]


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
def all_permutations(n: int) -> tuple[tuple[int, ...], ...]:
    return tuple(itertools.permutations(range(n)))


@lru_cache(maxsize=None)
def canonical_pair_key_cached(pair: Pair, n: int) -> PairKey:
    best: PairKey | None = None
    for permutation in all_permutations(n):
        transformed = relabel_pair(pair, permutation)
        candidate = min(transformed, (transformed[1], transformed[0]))
        if best is None or candidate < best:
            best = candidate
    if best is None:
        raise AssertionError("empty permutation group")
    return best


def canonical_pair_key(pair: Pair, n: int) -> PairKey:
    return canonical_pair_key_cached(normalize_pair(pair), n)


def unordered_colour_stabilizer(pair: Pair, n: int) -> int:
    pair = normalize_pair(pair)
    swapped = (pair[1], pair[0])
    return sum(
        relabel_pair(pair, permutation) in (pair, swapped)
        for permutation in all_permutations(n)
    )


def graph_components(pair: Pair, n: int) -> tuple[tuple[int, ...], ...]:
    adjacency = [set() for _ in range(n)]
    for side in pair:
        for u, v in side:
            require(u != v, "component helper received a loop")
            adjacency[u].add(v)
            adjacency[v].add(u)
    unseen = set(range(n))
    result: list[tuple[int, ...]] = []
    while unseen:
        root = min(unseen)
        stack = [root]
        component: set[int] = set()
        while stack:
            vertex = stack.pop()
            if vertex in component:
                continue
            component.add(vertex)
            stack.extend(adjacency[vertex] - component)
        unseen -= component
        result.append(tuple(sorted(component)))
    return tuple(sorted(result))


def is_simple_disjoint(pair: Pair) -> bool:
    flat = pair[0] + pair[1]
    return all(u != v for u, v in flat) and len(set(flat)) == len(flat)


def is_balanced_spanning_tree(pair: Pair, n: int) -> bool:
    k = (n - 1) // 2
    return (
        len(pair[0]) == len(pair[1]) == k
        and is_simple_disjoint(pair)
        and len(pair[0]) + len(pair[1]) == n - 1
        and len(graph_components(pair, n)) == 1
    )


def is_balanced_spanning_c2_forest(pair: Pair, n: int) -> bool:
    k = (n - 2) // 2
    return (
        len(pair[0]) == len(pair[1]) == k
        and is_simple_disjoint(pair)
        and len(pair[0]) + len(pair[1]) == n - 2
        and len(graph_components(pair, n)) == 2
    )


@dataclass(frozen=True)
class Orbit:
    index: int
    representative: Pair
    key: PairKey
    stabilizer: int
    labelled_orbit_size: int


def enumerate_tree_orbits(n: int) -> list[Orbit]:
    require(n % 2 == 1, "tree side degree requires odd n")
    k = (n - 1) // 2
    representatives: dict[PairKey, Pair] = {}
    for topology in nx.generators.nonisomorphic_trees(n):
        edges = tuple(sorted((min(int(u), int(v)), max(int(u), int(v))) for u, v in topology.edges()))
        for chosen in itertools.combinations(range(n - 1), k):
            selected = set(chosen)
            pair: Pair = (
                tuple(edges[index] for index in range(n - 1) if index in selected),
                tuple(edges[index] for index in range(n - 1) if index not in selected),
            )
            key = canonical_pair_key(pair, n)
            representatives.setdefault(key, pair)
    output: list[Orbit] = []
    for index, key in enumerate(sorted(representatives)):
        representative = representatives[key]
        stabilizer = unordered_colour_stabilizer(representative, n)
        require(factorial(n) % stabilizer == 0, "nonintegral tree orbit size")
        output.append(
            Orbit(index, representative, key, stabilizer, factorial(n) // stabilizer)
        )
    return output


def enumerate_forest_orbits(n: int) -> list[Orbit]:
    require(n % 2 == 0, "balanced c2 forest side degree requires even n")
    k = (n - 2) // 2
    complete_edges = tuple(itertools.combinations(range(n), 2))
    representatives: dict[PairKey, Pair] = {}
    for union in itertools.combinations(complete_edges, 2 * k):
        # A simple graph with n vertices and n-2 edges is a two-component
        # forest exactly when it has two components.
        probe: Pair = (tuple(union[:k]), tuple(union[k:]))
        if len(graph_components(probe, n)) != 2:
            continue
        for chosen in itertools.combinations(range(2 * k), k):
            selected = set(chosen)
            pair: Pair = (
                tuple(union[index] for index in range(2 * k) if index in selected),
                tuple(union[index] for index in range(2 * k) if index not in selected),
            )
            key = canonical_pair_key(pair, n)
            representatives.setdefault(key, pair)
    output: list[Orbit] = []
    for index, key in enumerate(sorted(representatives)):
        representative = representatives[key]
        require(is_balanced_spanning_c2_forest(representative, n), "bad forest representative")
        stabilizer = unordered_colour_stabilizer(representative, n)
        require(factorial(n) % stabilizer == 0, "nonintegral forest orbit size")
        output.append(
            Orbit(index, representative, key, stabilizer, factorial(n) // stabilizer)
        )
    return output


def delete_vertex_and_edge(pair: Pair, vertex: int, removed: Edge) -> Pair:
    remaining = [old for old in range(7) if old != vertex]
    relabelling = {old: new for new, old in enumerate(remaining)}
    sides: list[Side] = []
    removed_once = False
    for side in pair:
        output: list[Edge] = []
        for edge in side:
            if edge == removed and not removed_once:
                removed_once = True
                continue
            if vertex in edge:
                continue
            u, v = edge
            output.append(tuple(sorted((relabelling[u], relabelling[v]))))
        sides.append(tuple(sorted(output)))
    require(removed_once, "requested opposite-colour edge was not removed")
    return sides[0], sides[1]


def direct_incidence(trees: Sequence[Orbit], forests: Sequence[Orbit]) -> np.ndarray:
    forest_index = {orbit.key: orbit.index for orbit in forests}
    result = np.zeros((len(forests), len(trees)), dtype=np.int64)
    for tree in trees:
        degree = Counter(vertex for side in tree.representative for edge in side for vertex in edge)
        leaves = sorted(vertex for vertex in range(7) if degree[vertex] == 1)
        for leaf in leaves:
            leaf_colour = next(
                colour
                for colour, side in enumerate(tree.representative)
                if any(leaf in edge for edge in side)
            )
            for removed in tree.representative[1 - leaf_colour]:
                forest = delete_vertex_and_edge(tree.representative, leaf, removed)
                require(is_balanced_spanning_c2_forest(forest, 6), "deletion did not yield c2 forest")
                key = canonical_pair_key(forest, 6)
                require(key in forest_index, "deletion left exhaustive forest quotient")
                result[forest_index[key], tree.index] += 1
        require(int(result[:, tree.index].sum()) == 3 * len(leaves), "tree incidence row sum drift")
    return result


def reverse_incidence(trees: Sequence[Orbit], forests: Sequence[Orbit]) -> np.ndarray:
    tree_index = {orbit.key: orbit.index for orbit in trees}
    result = np.zeros((len(forests), len(trees)), dtype=np.int64)
    for forest in forests:
        components = graph_components(forest.representative, 6)
        require(len(components) == 2, "reverse incidence received non-c2 forest")
        bridges = tuple((u, v) for u in components[0] for v in components[1])
        for leaf_colour in (0, 1):
            bridge_colour = 1 - leaf_colour
            for endpoint in range(6):
                for bridge in bridges:
                    sides = [list(forest.representative[0]), list(forest.representative[1])]
                    sides[leaf_colour].append(tuple(sorted((endpoint, 6))))
                    sides[bridge_colour].append(tuple(sorted(bridge)))
                    tree: Pair = tuple(tuple(sorted(side)) for side in sides)  # type: ignore[assignment]
                    require(is_balanced_spanning_tree(tree, 7), "reverse extension did not yield tree")
                    key = canonical_pair_key(tree, 7)
                    require(key in tree_index, "reverse extension left exhaustive tree quotient")
                    result[forest.index, tree_index[key]] += 1
        expected = 12 * len(components[0]) * len(components[1])
        require(int(result[forest.index].sum()) == expected, "forest reverse-incidence row sum drift")
    return result


def certificate_pair(raw_pair: object) -> Pair:
    require(isinstance(raw_pair, list) and len(raw_pair) == 2, "malformed certificate pair")
    zero_based = []
    for raw_side in raw_pair:
        require(isinstance(raw_side, list), "malformed certificate side")
        zero_based.append(tuple((int(edge[0]) - 1, int(edge[1]) - 1) for edge in raw_side))
    return normalize_pair(zero_based)


def load_certificate_terms(n: int) -> list[tuple[Fraction, Pair]]:
    k = (n - 1) // 2
    path = CERTIFICATE_DIR / f"certificate_{n}_{k}.json"
    raw = json.loads(path.read_text(encoding="utf-8"))
    require(raw.get("n") == n and isinstance(raw.get("terms"), list), "bad certificate header")
    return [
        (Fraction(item["coefficient"]), certificate_pair(item["pair"]))
        for item in raw["terms"]
    ]


def to_semantic_pair(pair: Pair) -> Pair:
    return tuple(tuple((u + 1, v + 1) for u, v in side) for side in pair)  # type: ignore[return-value]


def orbit_descriptor(kind: str, pair: Pair, index: int) -> dict[str, object]:
    return {"kind": kind, "index": index, "pair_zero_based": pair_payload(pair)}


def known_certificate_plus_trees(
    trees: Sequence[Orbit], semantic: object
) -> tuple[list[Pair], list[dict[str, object]], list[int | None]]:
    known = load_certificate_terms(7)
    pairs: list[Pair] = []
    descriptors: list[dict[str, object]] = []
    tree_indices: list[int | None] = []
    seen: dict[PairKey, int] = {}
    tree_by_key = {tree.key: tree.index for tree in trees}
    for index, (_coefficient, pair) in enumerate(known):
        key = canonical_pair_key(pair, 7)
        if key in seen:
            continue
        seen[key] = len(pairs)
        pairs.append(pair)
        descriptors.append(orbit_descriptor("public_MAX7_atom", pair, index))
        tree_indices.append(tree_by_key.get(key))
    for tree in trees:
        if tree.key in seen:
            continue
        seen[tree.key] = len(pairs)
        pairs.append(tree.representative)
        descriptors.append(orbit_descriptor("balanced_tree", tree.representative, tree.index))
        tree_indices.append(tree.index)
    return pairs, descriptors, tree_indices


def stream_complete_n7_dictionary(
    trees: Sequence[Orbit], *, progress_every: int = 1_000_000
) -> tuple[list[Pair], list[dict[str, object]], list[int | None], dict[str, object]]:
    pairs: list[Pair] = []
    descriptors: list[dict[str, object]] = []
    tree_indices: list[int | None] = []
    tree_by_key = {tree.key: tree.index for tree in trees}
    selected_by_mass: Counter[int] = Counter()
    records_seen = 0
    header: dict[str, object] | None = None
    begun = time.perf_counter()
    with gzip.open(UNIVERSE_PATH, "rt", encoding="utf-8") as source:
        for line in source:
            record = json.loads(line)
            if record.get("record_type") == "header":
                header = record
                continue
            records_seen += 1
            if progress_every and records_seen % progress_every == 0:
                print(f"STREAM records={records_seen} selected={len(pairs)}", flush=True)
            mass = int(record["signed_mass"])
            active = int(record["active_vertices"])
            # G0038 binds its order as signed_mass then active_vertices.  Once
            # mass four begins, no later record can enter the n=7,k=3 slice.
            if mass > 3:
                break
            if active > 7:
                continue
            negative = normalize_pair((record["negative_edges"], record["positive_edges"]))[0]
            positive = normalize_pair((record["negative_edges"], record["positive_edges"]))[1]
            padding = ((0, 1),) * (3 - mass)
            pair: Pair = (tuple(sorted(negative + padding)), tuple(sorted(positive + padding)))
            tree_index: int | None = None
            if mass == 3 and active == 7 and is_balanced_spanning_tree(pair, 7):
                key = canonical_pair_key(pair, 7)
                require(key in tree_by_key, "G0038 tree record left independent tree quotient")
                tree_index = tree_by_key[key]
            pairs.append(pair)
            descriptors.append(
                {
                    "kind": "G0038_signed_W_orbit",
                    "sequence": int(record["sequence"]),
                    "signed_mass": mass,
                    "active_vertices": active,
                    "pair_zero_based": pair_payload(pair),
                }
            )
            tree_indices.append(tree_index)
            selected_by_mass[mass] += 1
    require(header is not None, "G0038 header missing")
    # The signed-zero record above supplies 3E.  A second s=0 basis atom, 3L,
    # is required because common padding changes only the invariant linear part.
    loop_pair: Pair = (((0, 0),) * 3, ((0, 0),) * 3)
    pairs.append(loop_pair)
    descriptors.append({"kind": "three_common_loops", "pair_zero_based": pair_payload(loop_pair)})
    tree_indices.append(None)
    require(dict(selected_by_mass) == {0: 1, 1: 5, 2: 106, 3: 2897}, "n7 dictionary census drift")
    require(len(pairs) == 3010, "complete n7 compressed dictionary size drift")
    tree_hits = [index for index in tree_indices if index is not None]
    require(len(tree_hits) == len(trees), "G0038 n7 tree census drift")
    require(sorted(tree_hits) == list(range(len(trees))), "G0038 n7 tree quotient is not bijective")
    return pairs, descriptors, tree_indices, {
        "source": str(UNIVERSE_PATH.relative_to(ROOT)),
        "source_sha256": sha256_path(UNIVERSE_PATH),
        "records_scanned_through_first_mass4": records_seen,
        "source_total_orbit_records_from_header": int(header["expected_record_count"]),
        "selected_signed_W_records_by_mass": dict(sorted(selected_by_mass.items())),
        "base_atoms": ["three_common_nonloops", "three_common_loops"],
        "compressed_column_count": len(pairs),
        "tree_column_count": len(tree_hits),
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }


def build_augmented_system(
    pairs: Sequence[Pair],
    descriptors: Sequence[dict[str, object]],
    tree_indices: Sequence[int | None],
    incidence: np.ndarray,
    forest_target: Sequence[Fraction],
    semantic: object,
) -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    begun = time.perf_counter()
    columns = []
    directions: set[Direction] = set()
    for index, pair in enumerate(pairs):
        if index and index % 250 == 0:
            print(f"SEMANTICS columns={index}/{len(pairs)}", flush=True)
        column = semantic.exact_semantic_column(to_semantic_pair(pair), 7)
        columns.append(column)
        directions.update(column.hinges)
    ordered_directions = sorted(directions)
    direction_index = {direction: index for index, direction in enumerate(ordered_directions)}
    functional_rows = len(ordered_directions) + 7
    matrix = np.zeros((functional_rows + len(forest_target), len(pairs)), dtype=np.int64)
    for column_index, column in enumerate(columns):
        for direction, value in column.hinges.items():
            matrix[direction_index[direction], column_index] = int(value)
        matrix[len(ordered_directions) : functional_rows, column_index] = column.linear
        tree_index = tree_indices[column_index]
        if tree_index is not None:
            matrix[functional_rows:, column_index] = 7 * incidence[:, tree_index]

    denominator = reduce(lcm, (value.denominator for value in forest_target), 1)
    target = np.zeros(matrix.shape[0], dtype=np.int64)
    target[functional_rows - 1] = denominator
    target[functional_rows:] = [
        value.numerator * (denominator // value.denominator) for value in forest_target
    ]
    report = {
        "columns": len(pairs),
        "rows": int(matrix.shape[0]),
        "hinge_rows": len(ordered_directions),
        "linear_rows": 7,
        "incidence_rows": len(forest_target),
        "target_denominator": denominator,
        "matrix_int64_c_sha256": hashlib.sha256(matrix.tobytes(order="C")).hexdigest(),
        "target_int64_c_sha256": hashlib.sha256(target.tobytes(order="C")).hexdigest(),
        "direction_list_sha256": canonical_sha256(ordered_directions),
        "semantic_seconds": round(time.perf_counter() - begun, 6),
        "semantic_dependency": str(G0090_PATH.relative_to(ROOT)),
        "semantic_dependency_sha256": sha256_path(G0090_PATH),
        "semantic_independence_boundary": (
            "Same-code dependency on G0090 exact_semantic_column; combinatorial incidence is "
            "independent, but this is not an independent semantic implementation."
        ),
        "column_descriptors_sha256": canonical_sha256(list(descriptors)),
    }
    return matrix, target, report


def to_nmod(array: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(array, prime), dtype=np.uint32)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def pivot_columns_from_rref(rref: nmod_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    for row in range(rank):
        pivot = next((column for column in range(rref.ncols()) if int(rref[row, column])), None)
        if pivot is None:
            raise GateError("RREF row lacks pivot")
        pivots.append(pivot)
    require(pivots == sorted(set(pivots)), "invalid RREF pivot sequence")
    return pivots


def exact_positive_solution(
    matrix: np.ndarray,
    target: np.ndarray,
    descriptors: Sequence[dict[str, object]],
    prime: int,
    target_denominator: int,
) -> dict[str, object] | None:
    begun = time.perf_counter()
    field = to_nmod(matrix, prime)
    rref, rank_obj = field.rref()
    rank = int(rank_obj)
    augmented_rank = int(to_nmod(np.column_stack((matrix, target)), prime).rank())
    modular = {"prime": prime, "rank": rank, "augmented_rank": augmented_rank}
    if augmented_rank != rank:
        return {
            "result": "MODULAR_NONMEMBERSHIP_ONLY",
            "claim_class": "modular",
            "modular": modular,
            "wall_seconds": round(time.perf_counter() - begun, 6),
            "warning": "A modular rank gap alone is not promoted to a rational obstruction here.",
        }
    pivot_columns = pivot_columns_from_rref(rref, rank)
    basis = matrix[:, pivot_columns]
    transposed_rref, transposed_rank_obj = to_nmod(basis.T, prime).rref()
    transposed_rank = int(transposed_rank_obj)
    require(transposed_rank == rank, "basis transpose rank drift")
    pivot_rows = pivot_columns_from_rref(transposed_rref, rank)
    square_array = matrix[np.ix_(pivot_rows, pivot_columns)]
    square = fmpq_mat(fmpz_mat(square_array.tolist()))
    require(int(square.rank()) == rank, "modular pivot minor is singular over Q")
    rhs = fmpq_mat(fmpz_mat([[int(target[row])] for row in pivot_rows]))
    solution = square.solve(rhs)
    coefficients = [Fraction(str(solution[index, 0])) for index in range(rank)]
    # Method-disjoint replay in stdlib Fraction arithmetic over every row.
    for row in range(matrix.shape[0]):
        observed = sum(
            int(matrix[row, column]) * coefficients[position]
            for position, column in enumerate(pivot_columns)
        )
        require(observed == Fraction(int(target[row])), f"exact replay failed at row {row}")
    sparse = [
        {
            "column_index": int(column),
            "coefficient_numerator_over_scaled_target": str(coefficients[position]),
            "ruess_full_permutation_sum_coefficient": str(
                coefficients[position] / target_denominator
            ),
            "descriptor": descriptors[column],
        }
        for position, column in enumerate(pivot_columns)
        if coefficients[position]
    ]
    return {
        "result": "EXACT_MEMBERSHIP",
        "claim_class": "exact",
        "modular": modular,
        "rank_over_Q": rank,
        "pivot_rows_sha256": canonical_sha256(pivot_rows),
        "pivot_columns_sha256": canonical_sha256(pivot_columns),
        "support_size": len(sparse),
        "sparse_solution": sparse,
        "sparse_solution_sha256": canonical_sha256(sparse),
        "all_rows_fraction_replay": True,
        "rows_replayed": int(matrix.shape[0]),
        "coefficient_note": (
            "coefficient_numerator_over_scaled_target solves the integer target; the adjacent "
            "ruess_full_permutation_sum_coefficient is already divided by target_denominator."
        ),
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }


def public_certificate_controls(
    trees: Sequence[Orbit], forests: Sequence[Orbit]
) -> tuple[list[Fraction], dict[str, object]]:
    forest_by_key = {forest.key: forest.index for forest in forests}
    max6 = load_certificate_terms(6)
    target = [Fraction(0) for _ in forests]
    max6_forest_terms: list[dict[str, object]] = []
    for term_index, (coefficient, pair) in enumerate(max6):
        if not is_balanced_spanning_c2_forest(pair, 6):
            continue
        key = canonical_pair_key(pair, 6)
        require(key in forest_by_key, "public MAX6 forest term left exhaustive quotient")
        index = forest_by_key[key]
        target[index] += coefficient
        max6_forest_terms.append(
            {
                "term_index": term_index,
                "forest_orbit_index": index,
                "coefficient": str(coefficient),
                "pair_zero_based": pair_payload(pair),
            }
        )
    max7 = load_certificate_terms(7)
    max7_tree_terms = [
        {
            "term_index": index,
            "coefficient": str(coefficient),
            "pair_zero_based": pair_payload(pair),
        }
        for index, (coefficient, pair) in enumerate(max7)
        if is_balanced_spanning_tree(pair, 7)
    ]
    require(len(max6_forest_terms) == 3, "MAX6 dominant forest term count drift")
    require(any(target), "MAX6 dominant forest projection unexpectedly vanished")
    require(not max7_tree_terms, "published MAX7 tree projection is no longer zero")
    return target, {
        "max6_certificate": str((CERTIFICATE_DIR / "certificate_6_2.json").relative_to(ROOT)),
        "max6_certificate_sha256": sha256_path(CERTIFICATE_DIR / "certificate_6_2.json"),
        "max6_total_terms": len(max6),
        "max6_dominant_c2_forest_terms": max6_forest_terms,
        "max6_dominant_c2_projection_nonzero": True,
        "max7_certificate": str((CERTIFICATE_DIR / "certificate_7_3.json").relative_to(ROOT)),
        "max7_certificate_sha256": sha256_path(CERTIFICATE_DIR / "certificate_7_3.json"),
        "max7_total_terms": len(max7),
        "max7_balanced_spanning_tree_terms": max7_tree_terms,
        "published_coefficient_transfer_result": "EXACT_NEGATIVE",
        "published_coefficient_transfer_reason": (
            "The published MAX7 tree projection is zero, hence its incidence image is zero, "
            "while the published MAX6 dominant c2 projection is nonzero."
        ),
        "claim_boundary": (
            "This is a statement about these public certificate coefficient vectors, not about "
            "all MAX7 solutions and not about functional necessity of the incidence constraint."
        ),
    }


def incidence_report(
    trees: Sequence[Orbit], forests: Sequence[Orbit], direct: np.ndarray, reverse: np.ndarray
) -> dict[str, object]:
    nonzero: list[dict[str, int]] = []
    for forest in forests:
        for tree in trees:
            r = int(direct[forest.index, tree.index])
            q = int(reverse[forest.index, tree.index])
            if not r and not q:
                continue
            left = tree.labelled_orbit_size * r
            right = 7 * forest.labelled_orbit_size * q
            require(left == right, "orbit-weighted incidence double count failed")
            require(forest.stabilizer * r == tree.stabilizer * q, "stabilizer form failed")
            nonzero.append(
                {
                    "forest": forest.index,
                    "tree": tree.index,
                    "direct_r": r,
                    "reverse_q": q,
                    "tree_stabilizer": tree.stabilizer,
                    "forest_stabilizer": forest.stabilizer,
                    "tree_labelled_orbit_size": tree.labelled_orbit_size,
                    "forest_labelled_orbit_size": forest.labelled_orbit_size,
                }
            )
    require(nonzero, "incidence matrix is zero")
    mutant = direct.copy()
    first = nonzero[0]
    mutant[first["forest"], first["tree"]] += 1
    mutated_left = trees[first["tree"]].labelled_orbit_size * int(
        mutant[first["forest"], first["tree"]]
    )
    mutated_right = 7 * forests[first["forest"]].labelled_orbit_size * int(
        reverse[first["forest"], first["tree"]]
    )
    require(mutated_left != mutated_right, "one-incidence mutation escaped double count")
    return {
        "tree_orbit_count": len(trees),
        "forest_orbit_count": len(forests),
        "direct_incidence_nonzeros": int(np.count_nonzero(direct)),
        "direct_incidence_sum": int(direct.sum()),
        "reverse_incidence_sum": int(reverse.sum()),
        "direct_incidence_int64_c_sha256": hashlib.sha256(direct.tobytes(order="C")).hexdigest(),
        "reverse_incidence_int64_c_sha256": hashlib.sha256(reverse.tobytes(order="C")).hexdigest(),
        "direct_r_matrix": direct.tolist(),
        "reverse_q_matrix": reverse.tolist(),
        "tree_stabilizers": [tree.stabilizer for tree in trees],
        "forest_stabilizers": [forest.stabilizer for forest in forests],
        "tree_labelled_orbit_sizes": [tree.labelled_orbit_size for tree in trees],
        "forest_labelled_orbit_sizes": [forest.labelled_orbit_size for forest in forests],
        "weighted_double_count": "N_T*r(T,F) = 7*N_F*q(F,T)",
        "stabilizer_double_count": "a_F*r(T,F) = a_T*q(F,T)",
        "all_nonzero_entries_checked": len(nonzero),
        "all_weighted_equalities_hold": True,
        "ruess_incidence_matrix": "D(F,T)=7*r(T,F)",
        "ruess_basis_derivation": (
            "For F_T=sum_{sigma in S7} Phi_{sigma T}, each distinct labelled unordered-colour "
            "tree occurs a_T times. Summing deletion events and regrouping by forest orbit gives "
            "coefficient 7*r(T,F) against F_F=sum_{tau in S6} Phi_{tau F}."
        ),
        "one_incidence_mutation": {
            "forest": first["forest"],
            "tree": first["tree"],
            "mutation": "direct_r += 1",
            "mutated_left": mutated_left,
            "unchanged_right": mutated_right,
            "rejected": True,
        },
        "nonzero_entries_sha256": canonical_sha256(nonzero),
    }


def exact_incidence_image_solution(
    direct: np.ndarray, target: Sequence[Fraction], prime: int
) -> dict[str, object]:
    """Construct and replay an exact tree-vector preimage under D=7r."""

    matrix = 7 * direct
    denominator = reduce(lcm, (value.denominator for value in target), 1)
    rhs_array = np.asarray(
        [value.numerator * (denominator // value.denominator) for value in target],
        dtype=np.int64,
    )
    field = to_nmod(matrix, prime)
    rref, rank_obj = field.rref()
    rank = int(rank_obj)
    augmented_rank = int(to_nmod(np.column_stack((matrix, rhs_array)), prime).rank())
    require(rank == matrix.shape[0] == augmented_rank, "incidence map is not full-row-rank at gate prime")
    pivot_columns = pivot_columns_from_rref(rref, rank)
    square = fmpq_mat(fmpz_mat(matrix[:, pivot_columns].tolist()))
    require(int(square.rank()) == rank, "incidence pivot minor singular over Q")
    solution = square.solve(fmpq_mat(fmpz_mat([[int(value)] for value in rhs_array])))
    scaled = [Fraction(str(solution[index, 0])) for index in range(rank)]
    for row in range(matrix.shape[0]):
        observed = sum(
            int(matrix[row, column]) * scaled[position]
            for position, column in enumerate(pivot_columns)
        )
        require(observed == Fraction(int(rhs_array[row])), "incidence solution replay failed")
    sparse = [
        {
            "tree_orbit_index": int(column),
            "scaled_integer_target_coefficient": str(scaled[position]),
            "ruess_tree_coefficient": str(scaled[position] / denominator),
        }
        for position, column in enumerate(pivot_columns)
        if scaled[position]
    ]
    return {
        "claim_class": "exact",
        "outcome": "positive",
        "D_definition": "D=7*r",
        "rank_mod_p": rank,
        "rank_over_Q": rank,
        "target_denominator": denominator,
        "support_size": len(sparse),
        "sparse_tree_preimage": sparse,
        "sparse_tree_preimage_sha256": canonical_sha256(sparse),
        "all_rows_fraction_replay": True,
    }


def serialize_orbits(orbits: Sequence[Orbit]) -> list[dict[str, object]]:
    return [
        {
            "index": orbit.index,
            "representative_zero_based": pair_payload(orbit.representative),
            "canonical_key_zero_based": pair_payload(orbit.key),
            "stabilizer": orbit.stabilizer,
            "labelled_orbit_size": orbit.labelled_orbit_size,
        }
        for orbit in orbits
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
    parser.add_argument("--complete", action="store_true", help="use all 3,010 compressed n7 columns")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prime", type=int, default=PRIMES[0], choices=PRIMES)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    begun = time.perf_counter()
    semantic = load_module("g0099_g0090_semantics", G0090_PATH)
    require(semantic.self_test()["subset_DP_equals_literal_S4"], "G0090 semantic self-test failed")

    trees = enumerate_tree_orbits(7)
    forests = enumerate_forest_orbits(6)
    direct = direct_incidence(trees, forests)
    reverse = reverse_incidence(trees, forests)
    combinatorics = incidence_report(trees, forests, direct, reverse)
    forest_target, public_controls = public_certificate_controls(trees, forests)
    incidence_image = exact_incidence_image_solution(direct, forest_target, args.prime)

    if args.complete:
        pairs, descriptors, tree_indices, dictionary = stream_complete_n7_dictionary(trees)
        scope = "complete_compressed_degree3_pairwise_Ruess_family"
    else:
        pairs, descriptors, tree_indices = known_certificate_plus_trees(trees, semantic)
        dictionary = {
            "scope": "public_MAX7_atoms_plus_all_balanced_tree_orbits",
            "column_count": len(pairs),
            "complete_family": False,
        }
        scope = "public_MAX7_atoms_plus_all_balanced_tree_orbits"

    matrix, target, system = build_augmented_system(
        pairs, descriptors, tree_indices, direct, forest_target, semantic
    )
    # Exact positive control: the public MAX7 certificate (which has zero tree
    # projection) must hit the semantic target before incidence rows are imposed.
    functional_rows = int(system["hinge_rows"]) + 7
    public_pairs = [pair for _coefficient, pair in load_certificate_terms(7)]
    public_coefficients = [coefficient for coefficient, _pair in load_certificate_terms(7)]
    public_semantic = [semantic.exact_semantic_column(to_semantic_pair(pair), 7) for pair in public_pairs]
    hinge_residual: dict[Direction, Fraction] = defaultdict(Fraction)
    linear_residual = [Fraction(0) for _ in range(7)]
    for coefficient, column in zip(public_coefficients, public_semantic, strict=True):
        for direction, value in column.hinges.items():
            hinge_residual[direction] += coefficient * value
        for index, value in enumerate(column.linear):
            linear_residual[index] += coefficient * value
    hinge_residual = {key: value for key, value in hinge_residual.items() if value}
    require(not hinge_residual, "public MAX7 semantic positive control has hinge residual")
    require(linear_residual == [Fraction(0)] * 6 + [Fraction(1)], "public MAX7 identity drift")

    solution = exact_positive_solution(
        matrix, target, descriptors, args.prime, int(system["target_denominator"])
    )
    report = {
        "schema": SCHEMA,
        "result": solution["result"],
        "claim_class": solution["claim_class"],
        "scope": scope,
        "outcome_interpretation": (
            "EXACT_POSITIVE for existence of a MAX7 degree-three Rueß coefficient vector obeying "
            "the imposed leaf/bridge incidence constraint. This does not prove that the incidence "
            "constraint is functionally necessary and does not imply a MAX11 identity."
            if solution["result"] == "EXACT_MEMBERSHIP"
            else "NO RATIONAL CLAIM: only a modular result was obtained."
        ),
        "combinatorics": combinatorics,
        "incidence_target_image": incidence_image,
        "public_certificate_controls": public_controls,
        "public_MAX7_semantic_positive_control": {
            "exact_identity_replayed": True,
            "residual_hinges": 0,
            "linear": [str(value) for value in linear_residual],
            "implementation": "same G0090 subset-DP normal form used by the solve",
        },
        "excluded_tree_columns_negative_control": {
            "exact_negative": True,
            "reason": (
                "Every incidence row is identically zero after all tree columns are excluded, "
                "whereas the MAX6 c2 incidence target has nonzero entries."
            ),
        },
        "dictionary": dictionary,
        "augmented_system": system,
        "solution": solution,
        "tree_orbits": serialize_orbits(trees),
        "forest_orbits": serialize_orbits(forests),
        "forest_target_coefficients": [str(value) for value in forest_target],
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "networkx": nx.__version__,
            "python_flint": __import__("flint").__version__,
            "pid": os.getpid(),
        },
        "producer_sha256_before_output": sha256_path(Path(__file__).resolve()),
        "wall_seconds": round(time.perf_counter() - begun, 6),
        "claim_boundary": (
            "The orbit census, stabilizers, direct/reverse double count, certificate projections, "
            "and any successful all-row rational replay are exact. A modular rank result is only "
            "modular. The deletion constraint is an investigated equivariant compression, not an "
            "established consequence of MAXn semantics. No statement here is an unrestricted-depth "
            "lower bound or a MAX11 construction."
        ),
    }
    write_json_atomic(args.output.resolve(), report)
    print(
        f"G0099_{report['result']} scope={scope} trees={len(trees)} forests={len(forests)} "
        f"shape={matrix.shape[0]}x{matrix.shape[1]} wall={report['wall_seconds']} "
        f"output={args.output}",
        flush=True,
    )
    return 0 if solution["result"] == "EXACT_MEMBERSHIP" else 2


if __name__ == "__main__":
    raise SystemExit(main())
