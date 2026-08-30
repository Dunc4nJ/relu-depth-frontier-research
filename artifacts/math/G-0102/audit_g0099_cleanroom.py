#!/usr/bin/env python3
"""Clean-room hostile audit of the G-0099 n=6 -> n=7 potency gate.

This file deliberately imports no producer module.  It independently:

* counts signed multigraph orbits through mass three by Burnside's lemma;
* canonicalizes the corresponding G-0038 records and proves the slice has
  neither duplicates nor omissions;
* constructs the n=6 forest quotient and n=7 balanced-tree quotient;
* constructs direct and reverse leaf/opposite-colour-edge incidence;
* evaluates every n=7 Rueß atom by literal enumeration of all 7! vertex
  permutations, rather than the producer's subset dynamic program; and
* replays the delivered sparse rational solution on every functional and
  incidence row, with sign, incidence, coefficient, and target mutations.

The result is only a lower-dimensional potency audit.  It does not establish
that the incidence constraint follows from MAX semantics, does not construct
MAX11, and does not prove an unrestricted lower bound.
"""

from __future__ import annotations

import argparse
from array import array
from collections import Counter, defaultdict
from fractions import Fraction
from functools import reduce
import gzip
import hashlib
import itertools
import json
from math import factorial, gcd, lcm
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Sequence

import numpy as np
from flint import fmpz_mat, nmod_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_PRODUCER_REPORT = ROOT / "artifacts/math/G-0099/leaf_bridge_complete_v1.json"
DEFAULT_PRODUCER_SCRIPT = ROOT / "artifacts/math/G-0099/leaf_bridge_n6_n7.py"
DEFAULT_MANIFEST = ROOT / "artifacts/math/G-0099/MANIFEST.json"
DEFAULT_STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
DEFAULT_CERT6 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json"
DEFAULT_CERT7 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_7_3.json"
DEFAULT_OUTPUT = HERE / "cleanroom_audit_v1.json"
PRIMES = (1_000_003, 1_000_033, 1_000_081)

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


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
        sides.append(
            tuple(sorted((min(int(e[0]), int(e[1])), max(int(e[0]), int(e[1]))) for e in raw_side))
        )
    require(len(sides) == 2, "pair must have two branches")
    return sides[0], sides[1]


def pair_payload(pair: Pair) -> list[list[list[int]]]:
    return [[[u, v] for u, v in side] for side in pair]


def permute_pair(pair: Pair, permutation: Sequence[int]) -> Pair:
    return tuple(
        tuple(
            sorted(
                (min(permutation[u], permutation[v]), max(permutation[u], permutation[v]))
                for u, v in side
            )
        )
        for side in pair
    )  # type: ignore[return-value]


_PERMUTATIONS: dict[int, tuple[tuple[int, ...], ...]] = {}


def permutations_n(n: int) -> tuple[tuple[int, ...], ...]:
    if n not in _PERMUTATIONS:
        _PERMUTATIONS[n] = tuple(itertools.permutations(range(n)))
    return _PERMUTATIONS[n]


def canonical_pair(pair: Pair, n: int) -> Pair:
    pair = normalize_pair(pair)
    best: Pair | None = None
    for permutation in permutations_n(n):
        transformed = permute_pair(pair, permutation)
        candidate = min(transformed, (transformed[1], transformed[0]))
        if best is None or candidate < best:
            best = candidate
    assert best is not None
    return best


def canonical_signed_active(negative: Side, positive: Side) -> Pair:
    """Canonical signed graph using only active labels.

    Inactive labels never occur in an edge.  A lexicographically minimal
    relabelling maps the active set to 0..a-1, so enumerating a! bijections is
    equivalent to enumerating all ambient S7 relabellings, without redundant
    placements of inert vertices.
    """

    vertices = sorted({v for edge in negative + positive for v in edge})
    if not vertices:
        return (), ()
    relabelled_best: Pair | None = None
    for targets in itertools.permutations(range(len(vertices))):
        mapping = dict(zip(vertices, targets, strict=True))
        transformed: Pair = (
            tuple(sorted((min(mapping[u], mapping[v]), max(mapping[u], mapping[v])) for u, v in negative)),
            tuple(sorted((min(mapping[u], mapping[v]), max(mapping[u], mapping[v])) for u, v in positive)),
        )
        candidate = min(transformed, (transformed[1], transformed[0]))
        if relabelled_best is None or candidate < relabelled_best:
            relabelled_best = candidate
    assert relabelled_best is not None
    return relabelled_best


def components(pair: Pair, n: int) -> tuple[tuple[int, ...], ...]:
    adjacency = [set() for _ in range(n)]
    for side in pair:
        for u, v in side:
            require(u != v, "component routine received a loop")
            adjacency[u].add(v)
            adjacency[v].add(u)
    unseen = set(range(n))
    output: list[tuple[int, ...]] = []
    while unseen:
        root = min(unseen)
        stack = [root]
        found: set[int] = set()
        while stack:
            vertex = stack.pop()
            if vertex in found:
                continue
            found.add(vertex)
            stack.extend(adjacency[vertex] - found)
        unseen -= found
        output.append(tuple(sorted(found)))
    return tuple(sorted(output))


def simple_disjoint(pair: Pair) -> bool:
    edges = pair[0] + pair[1]
    return all(u != v for u, v in edges) and len(set(edges)) == len(edges)


def is_tree_pair(pair: Pair) -> bool:
    return (
        len(pair[0]) == len(pair[1]) == 3
        and simple_disjoint(pair)
        and len(components(pair, 7)) == 1
    )


def is_forest_pair(pair: Pair) -> bool:
    return (
        len(pair[0]) == len(pair[1]) == 2
        and simple_disjoint(pair)
        and len(components(pair, 6)) == 2
    )


def stabilizer(pair: Pair, n: int) -> int:
    pair = normalize_pair(pair)
    swapped = (pair[1], pair[0])
    return sum(permute_pair(pair, p) in (pair, swapped) for p in permutations_n(n))


def induced_edge_cycles(permutation: Sequence[int]) -> list[int]:
    edges = tuple((u, v) for u in range(7) for v in range(u, 7))
    index = {edge: i for i, edge in enumerate(edges)}
    induced = []
    for u, v in edges:
        a, b = permutation[u], permutation[v]
        induced.append(index[(min(a, b), max(a, b))])
    unseen = set(range(len(edges)))
    lengths: list[int] = []
    while unseen:
        cursor = min(unseen)
        length = 0
        while cursor in unseen:
            unseen.remove(cursor)
            cursor = induced[cursor]
            length += 1
        lengths.append(length)
    return lengths


def fixed_signed_assignments(cycle_lengths: Sequence[int], mass: int, sign_swap: bool) -> int:
    # dp[(positive mass, negative mass)] = assignments on processed cycles.
    dp: dict[tuple[int, int], int] = {(0, 0): 1}
    for length in cycle_lengths:
        options: list[tuple[int, int, int]] = [(0, 0, 1)]
        if sign_swap:
            if length % 2 == 0:
                half = length // 2
                for magnitude in range(1, mass // half + 1):
                    options.append((half * magnitude, half * magnitude, 2))
        else:
            for magnitude in range(1, mass // length + 1):
                options.append((length * magnitude, 0, 1))
                options.append((0, length * magnitude, 1))
        updated: dict[tuple[int, int], int] = defaultdict(int)
        for (positive, negative), count in dp.items():
            for add_positive, add_negative, multiplicity in options:
                key = (positive + add_positive, negative + add_negative)
                if key[0] <= mass and key[1] <= mass:
                    updated[key] += count * multiplicity
        dp = dict(updated)
    return dp.get((mass, mass), 0)


def burnside_orbit_counts() -> dict[int, int]:
    totals = [0, 0, 0, 0]
    for permutation in permutations_n(7):
        cycles = induced_edge_cycles(permutation)
        for mass in range(4):
            totals[mass] += fixed_signed_assignments(cycles, mass, False)
            totals[mass] += fixed_signed_assignments(cycles, mass, True)
    group_size = 2 * factorial(7)
    require(all(value % group_size == 0 for value in totals), "Burnside average is nonintegral")
    return {mass: value // group_size for mass, value in enumerate(totals)}


def read_dictionary(stream_path: Path) -> tuple[list[Pair], list[dict[str, object]], list[Pair | None], dict[str, object]]:
    pairs: list[Pair] = []
    descriptors: list[dict[str, object]] = []
    signed_keys: set[Pair] = set()
    signed_key_by_column: list[Pair | None] = []
    counts: Counter[int] = Counter()
    seen_sequences: list[int] = []
    header: dict[str, object] | None = None
    with gzip.open(stream_path, "rt", encoding="utf-8") as source:
        for line in source:
            record = json.loads(line)
            if record.get("record_type") == "header":
                require(header is None, "multiple stream headers")
                header = record
                continue
            mass = int(record["signed_mass"])
            if mass > 3:
                break
            active = int(record["active_vertices"])
            if active > 7:
                continue
            negative = tuple(sorted((min(map(int, e)), max(map(int, e))) for e in record["negative_edges"]))
            positive = tuple(sorted((min(map(int, e)), max(map(int, e))) for e in record["positive_edges"]))
            require(len(negative) == len(positive) == mass, "signed mass disagrees with edge lists")
            require(not (Counter(negative) & Counter(positive)), "signed record was not cancellation-reduced")
            actual_active = len({v for edge in negative + positive for v in edge})
            require(actual_active == active, "active-vertex count disagrees with edge lists")
            key = canonical_signed_active(negative, positive)
            require(key not in signed_keys, "duplicate signed orbit in selected stream slice")
            signed_keys.add(key)
            padding = ((0, 1),) * (3 - mass)
            pair: Pair = (tuple(sorted(negative + padding)), tuple(sorted(positive + padding)))
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
            signed_key_by_column.append(key)
            counts[mass] += 1
            seen_sequences.append(int(record["sequence"]))
    require(header is not None, "missing stream header")
    require(seen_sequences == sorted(seen_sequences), "selected stream sequences not increasing")
    loop_pair: Pair = (((0, 0),) * 3, ((0, 0),) * 3)
    pairs.append(loop_pair)
    descriptors.append({"kind": "three_common_loops", "pair_zero_based": pair_payload(loop_pair)})
    signed_key_by_column.append(None)
    return pairs, descriptors, signed_key_by_column, {
        "stream_header_expected_records": int(header["expected_record_count"]),
        "selected_by_mass": {mass: counts[mass] for mass in range(4)},
        "selected_signed_key_count": len(signed_keys),
        "compressed_columns": len(pairs),
        "stream_sha256": sha256_path(stream_path),
    }


def enumerate_forests() -> list[Pair]:
    keys: set[Pair] = set()
    complete_edges = tuple(itertools.combinations(range(6), 2))
    for union in itertools.combinations(complete_edges, 4):
        probe: Pair = (tuple(union[:2]), tuple(union[2:]))
        if len(components(probe, 6)) != 2:
            continue
        for chosen in itertools.combinations(range(4), 2):
            chosen_set = set(chosen)
            pair: Pair = (
                tuple(union[i] for i in range(4) if i in chosen_set),
                tuple(union[i] for i in range(4) if i not in chosen_set),
            )
            keys.add(canonical_pair(pair, 6))
    result = sorted(keys)
    require(all(is_forest_pair(pair) for pair in result), "invalid forest orbit")
    return result


def tree_orbits_from_dictionary(pairs: Sequence[Pair], descriptors: Sequence[dict[str, object]]) -> tuple[list[Pair], dict[int, int]]:
    keys: set[Pair] = set()
    candidate_columns: dict[Pair, int] = {}
    for index, (pair, descriptor) in enumerate(zip(pairs, descriptors, strict=True)):
        if descriptor.get("signed_mass") == 3 and descriptor.get("active_vertices") == 7 and is_tree_pair(pair):
            key = canonical_pair(pair, 7)
            require(key not in keys, "duplicate tree orbit in dictionary")
            keys.add(key)
            candidate_columns[key] = index
    trees = sorted(keys)
    key_to_index = {key: i for i, key in enumerate(trees)}
    column_to_tree = {column: key_to_index[key] for key, column in candidate_columns.items()}
    return trees, column_to_tree


def delete_leaf_and_edge(tree: Pair, leaf: int, removed_colour: int, removed_index: int) -> Pair:
    remaining = [v for v in range(7) if v != leaf]
    relabel = {old: new for new, old in enumerate(remaining)}
    output: list[Side] = []
    for colour, side in enumerate(tree):
        new_side: list[Edge] = []
        for index, edge in enumerate(side):
            if colour == removed_colour and index == removed_index:
                continue
            if leaf in edge:
                continue
            u, v = edge
            new_side.append((min(relabel[u], relabel[v]), max(relabel[u], relabel[v])))
        output.append(tuple(sorted(new_side)))
    return output[0], output[1]


def direct_incidence(trees: Sequence[Pair], forests: Sequence[Pair]) -> np.ndarray:
    forest_index = {key: i for i, key in enumerate(forests)}
    result = np.zeros((len(forests), len(trees)), dtype=np.int64)
    for tree_index, tree in enumerate(trees):
        degree = Counter(v for side in tree for edge in side for v in edge)
        leaves = [v for v in range(7) if degree[v] == 1]
        for leaf in leaves:
            leaf_colour = next(c for c, side in enumerate(tree) if any(leaf in edge for edge in side))
            opposite = 1 - leaf_colour
            for removed_index in range(3):
                forest = delete_leaf_and_edge(tree, leaf, opposite, removed_index)
                require(is_forest_pair(forest), "direct deletion failed to make c2 forest")
                result[forest_index[canonical_pair(forest, 6)], tree_index] += 1
        require(int(result[:, tree_index].sum()) == 3 * len(leaves), "direct event count mismatch")
    return result


def reverse_incidence(trees: Sequence[Pair], forests: Sequence[Pair]) -> np.ndarray:
    tree_index = {key: i for i, key in enumerate(trees)}
    result = np.zeros((len(forests), len(trees)), dtype=np.int64)
    for forest_index, forest in enumerate(forests):
        comps = components(forest, 6)
        require(len(comps) == 2, "reverse input not c2")
        bridges = [(u, v) for u in comps[0] for v in comps[1]]
        event_count = 0
        for leaf_colour in (0, 1):
            for endpoint in range(6):
                for bridge in bridges:
                    branches = [list(forest[0]), list(forest[1])]
                    branches[leaf_colour].append((endpoint, 6))
                    branches[1 - leaf_colour].append(tuple(sorted(bridge)))
                    tree: Pair = tuple(tuple(sorted(side)) for side in branches)  # type: ignore[assignment]
                    require(is_tree_pair(tree), "reverse extension failed to make tree")
                    result[forest_index, tree_index[canonical_pair(tree, 7)]] += 1
                    event_count += 1
        require(event_count == 12 * len(comps[0]) * len(comps[1]), "reverse event count mismatch")
    return result


def ordered_positions(n: int) -> tuple[tuple[int, ...], ...]:
    output = []
    for order in permutations_n(n):
        position = [0] * n
        for rank, vertex in enumerate(order):
            position[vertex] = rank
        output.append(tuple(position))
    return tuple(output)


_POSITIONS: dict[int, tuple[tuple[int, ...], ...]] = {}


def positions_n(n: int) -> tuple[tuple[int, ...], ...]:
    if n not in _POSITIONS:
        _POSITIONS[n] = ordered_positions(n)
    return _POSITIONS[n]


def nonpositive_on_sorted_cone(direction: Direction) -> bool:
    if sum(direction):
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


def literal_semantic(pair: Pair, n: int, *, bad_sign_correction: bool = False) -> tuple[tuple[int, ...], dict[Direction, int]]:
    """Literal n! symmetrization; no subset-DP or producer code."""

    require(len(pair[0]) == len(pair[1]) and pair[0], "unequal or empty branches")
    linear = [0] * n
    hinges: dict[Direction, int] = defaultdict(int)
    for position in positions_n(n):
        left = [0] * n
        right = [0] * n
        for u, v in pair[0]:
            left[max(position[u], position[v])] += 1
        for u, v in pair[1]:
            right[max(position[u], position[v])] += 1
        for rank, value in enumerate(left):
            linear[rank] += value
        raw = tuple(right[i] - left[i] for i in range(n))
        if not any(raw):
            continue
        first = next(value for value in raw if value)
        magnitude = reduce(gcd, (abs(value) for value in raw), 0)
        if first < 0:
            # Correct identity: rho(raw)=rho(-raw)+raw.  The planted mutant
            # applies the opposite correction and must destroy the replay.
            correction_sign = -1 if bad_sign_correction else 1
            for rank, value in enumerate(raw):
                linear[rank] += correction_sign * value
            primitive = tuple(-value // magnitude for value in raw)
        else:
            primitive = tuple(value // magnitude for value in raw)
        if not nonpositive_on_sorted_cone(primitive):
            hinges[primitive] += magnitude
    return tuple(linear), dict(hinges)


def load_certificate(path: Path) -> tuple[int, list[tuple[Fraction, Pair]]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    n = int(raw["n"])
    terms = []
    for item in raw["terms"]:
        pair = normalize_pair(
            tuple(tuple((int(e[0]) - 1, int(e[1]) - 1) for e in side) for side in item["pair"])
        )
        terms.append((Fraction(item["coefficient"]), pair))
    return n, terms


def replay_public_certificate(path: Path) -> dict[str, object]:
    n, terms = load_certificate(path)
    linear = [Fraction(0) for _ in range(n)]
    hinges: dict[Direction, Fraction] = defaultdict(Fraction)
    cached: dict[Pair, tuple[tuple[int, ...], dict[Direction, int]]] = {}
    for coefficient, pair in terms:
        key = canonical_pair(pair, n)
        if key not in cached:
            cached[key] = literal_semantic(pair, n)
        column_linear, column_hinges = cached[key]
        for rank, value in enumerate(column_linear):
            linear[rank] += coefficient * value
        for direction, value in column_hinges.items():
            hinges[direction] += coefficient * value
    residual = {key: value for key, value in hinges.items() if value}
    expected = [Fraction(0)] * (n - 1) + [Fraction(1)]
    return {
        "n": n,
        "terms": len(terms),
        "file_sha256": sha256_path(path),
        "exact_identity": not residual and linear == expected,
        "residual_hinges": len(residual),
        "linear": [str(value) for value in linear],
        "implementation": "literal enumeration of all n! vertex orders",
    }


def forest_target_from_max6(cert6_path: Path, forests: Sequence[Pair]) -> tuple[list[Fraction], list[dict[str, object]]]:
    n, terms = load_certificate(cert6_path)
    require(n == 6, "wrong MAX6 certificate")
    forest_index = {key: i for i, key in enumerate(forests)}
    target = [Fraction(0) for _ in forests]
    selected = []
    for term_index, (coefficient, pair) in enumerate(terms):
        if not is_forest_pair(pair):
            continue
        index = forest_index[canonical_pair(pair, 6)]
        target[index] += coefficient
        selected.append({"term_index": term_index, "forest_orbit_index": index, "coefficient": str(coefficient)})
    return target, selected


def max7_tree_projection(cert7_path: Path) -> list[dict[str, object]]:
    n, terms = load_certificate(cert7_path)
    require(n == 7, "wrong MAX7 certificate")
    return [
        {"term_index": i, "coefficient": str(coefficient), "pair": pair_payload(pair)}
        for i, (coefficient, pair) in enumerate(terms)
        if is_tree_pair(pair)
    ]


def build_matrix(
    pairs: Sequence[Pair],
    column_to_tree: dict[int, int],
    direct: np.ndarray,
    forest_target: Sequence[Fraction],
) -> tuple[np.ndarray, np.ndarray, list[Direction], list[tuple[tuple[int, ...], dict[Direction, int]]]]:
    columns = []
    directions: set[Direction] = set()
    for index, pair in enumerate(pairs):
        if index and index % 250 == 0:
            print(f"literal semantics {index}/{len(pairs)}", flush=True)
        column = literal_semantic(pair, 7)
        columns.append(column)
        directions.update(column[1])
    ordered = sorted(directions)
    direction_index = {direction: i for i, direction in enumerate(ordered)}
    functional_rows = len(ordered) + 7
    matrix = np.zeros((functional_rows + len(forest_target), len(pairs)), dtype=np.int64)
    for column_index, (linear, hinges) in enumerate(columns):
        for direction, value in hinges.items():
            matrix[direction_index[direction], column_index] = value
        matrix[len(ordered):functional_rows, column_index] = linear
        if column_index in column_to_tree:
            matrix[functional_rows:, column_index] = 7 * direct[:, column_to_tree[column_index]]
    denominator = reduce(lcm, (value.denominator for value in forest_target), 1)
    target = np.zeros(matrix.shape[0], dtype=np.int64)
    target[functional_rows - 1] = denominator
    target[functional_rows:] = [
        value.numerator * (denominator // value.denominator) for value in forest_target
    ]
    return matrix, target, ordered, columns


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.uint32)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def pivot_columns(rref: nmod_mat, rank: int) -> list[int]:
    output = []
    for row in range(rank):
        pivot = next((column for column in range(rref.ncols()) if int(rref[row, column])), None)
        require(pivot is not None, "pivotless nonzero RREF row")
        output.append(int(pivot))
    return output


def modular_pivots(matrix: np.ndarray, prime: int) -> tuple[int, list[int], list[int]]:
    rref, rank_obj = to_nmod(matrix, prime).rref()
    rank = int(rank_obj)
    columns = pivot_columns(rref, rank)
    basis = matrix[:, columns]
    transposed, transposed_rank_obj = to_nmod(basis.T, prime).rref()
    require(int(transposed_rank_obj) == rank, "transpose rank mismatch")
    rows = pivot_columns(transposed, rank)
    return rank, columns, rows


def sparse_solution(report: dict[str, object], descriptors: Sequence[dict[str, object]], denominator: int) -> tuple[dict[int, Fraction], dict[str, object]]:
    solution = report["solution"]
    require(isinstance(solution, dict), "producer solution is not an object")
    entries = solution["sparse_solution"]
    require(isinstance(entries, list), "producer sparse solution is not a list")
    coefficients: dict[int, Fraction] = {}
    for item in entries:
        require(isinstance(item, dict), "malformed sparse item")
        index = int(item["column_index"])
        coefficient = Fraction(str(item["coefficient_numerator_over_scaled_target"]))
        require(index not in coefficients and coefficient, "duplicate or zero sparse coefficient")
        require(item["descriptor"] == descriptors[index], f"descriptor mismatch at column {index}")
        require(
            Fraction(str(item["ruess_full_permutation_sum_coefficient"])) == coefficient / denominator,
            f"scaled coefficient mismatch at column {index}",
        )
        coefficients[index] = coefficient
    return coefficients, {
        "support_size": len(coefficients),
        "sparse_solution_canonical_sha256": canonical_sha256(entries),
        "reported_sparse_solution_sha256": solution["sparse_solution_sha256"],
    }


def replay_rows(matrix: np.ndarray, target: np.ndarray, coefficients: dict[int, Fraction]) -> tuple[bool, list[tuple[int, str]]]:
    residuals: list[tuple[int, str]] = []
    for row in range(matrix.shape[0]):
        observed = sum(Fraction(int(matrix[row, column])) * value for column, value in coefficients.items())
        difference = observed - int(target[row])
        if difference:
            residuals.append((row, str(difference)))
    return not residuals, residuals[:20]


def direct_value(pair: Pair, point: Sequence[int]) -> int:
    total = 0
    for permutation in permutations_n(len(point)):
        left = sum(max(point[permutation[u]], point[permutation[v]]) for u, v in pair[0])
        right = sum(max(point[permutation[u]], point[permutation[v]]) for u, v in pair[1])
        total += max(left, right)
    return total


def direct_point_replay(pairs: Sequence[Pair], coefficients: dict[int, Fraction]) -> list[dict[str, object]]:
    points = [
        (-3, -1, 0, 2, 4, 7, 11),
        (-5, -5, -2, 0, 0, 3, 9),
        (0, 0, 0, 0, 0, 0, 0),
        (1, 2, 3, 4, 5, 6, 7),
    ]
    output = []
    for point in points:
        observed = sum((coefficient / 1440) * direct_value(pairs[index], point) for index, coefficient in coefficients.items())
        expected = Fraction(max(point))
        output.append({"point": list(point), "observed": str(observed), "expected": str(expected), "matches": observed == expected})
    return output


def mutation_controls(
    pairs: Sequence[Pair],
    matrix: np.ndarray,
    target: np.ndarray,
    directions: Sequence[Direction],
    columns: Sequence[tuple[tuple[int, ...], dict[Direction, int]]],
    column_to_tree: dict[int, int],
    direct: np.ndarray,
    trees: Sequence[Pair],
    forests: Sequence[Pair],
    reverse: np.ndarray,
    coefficients: dict[int, Fraction],
) -> dict[str, object]:
    direction_index = {direction: i for i, direction in enumerate(directions)}
    hinge_rows = len(directions)

    sign_control: dict[str, object] | None = None
    for column_index, coefficient in coefficients.items():
        mutant_linear, mutant_hinges = literal_semantic(pairs[column_index], 7, bad_sign_correction=True)
        original_linear, original_hinges = columns[column_index]
        if mutant_linear == original_linear and mutant_hinges == original_hinges:
            continue
        residual: dict[str, Fraction] = {}
        for rank in range(7):
            value = coefficient * (mutant_linear[rank] - original_linear[rank])
            if value:
                residual[f"linear:{rank}"] = value
        for direction in set(original_hinges) | set(mutant_hinges):
            value = coefficient * (mutant_hinges.get(direction, 0) - original_hinges.get(direction, 0))
            if value:
                label = f"hinge:{direction_index.get(direction, 'new')}"
                residual[label] = value
        require(residual, "semantic sign mutation did not alter replay")
        sign_control = {
            "mutation": "use rho(u)=rho(-u)-u instead of rho(u)=rho(-u)+u when orienting a negative direction",
            "column_index": column_index,
            "rejected": True,
            "nonzero_residual_coordinates": len(residual),
            "first_residual": next(iter(residual.items()))[0] + "=" + str(next(iter(residual.values()))),
        }
        break
    require(sign_control is not None, "no supported coefficient exercised sign correction")

    incidence_control: dict[str, object] | None = None
    tree_column_by_index = {tree_index: column for column, tree_index in column_to_tree.items()}
    for tree_index, column_index in tree_column_by_index.items():
        coefficient = coefficients.get(column_index)
        if not coefficient:
            continue
        forest_indices = np.flatnonzero(direct[:, tree_index])
        if not len(forest_indices):
            continue
        forest_index = int(forest_indices[0])
        old_r = int(direct[forest_index, tree_index])
        q = int(reverse[forest_index, tree_index])
        tree_size = factorial(7) // stabilizer(trees[tree_index], 7)
        forest_size = factorial(6) // stabilizer(forests[forest_index], 6)
        original_left = tree_size * old_r
        original_right = 7 * forest_size * q
        mutated_left = tree_size * (old_r + 1)
        require(original_left == original_right and mutated_left != original_right, "incidence plant escaped double count")
        residual = 7 * coefficient
        require(residual, "incidence plant escaped constrained replay")
        incidence_control = {
            "mutation": "increment one direct incidence count r(F,T) by one",
            "forest_index": forest_index,
            "tree_index": tree_index,
            "column_index": column_index,
            "double_count_before": original_left,
            "double_count_after_left": mutated_left,
            "unchanged_right": original_right,
            "constrained_row_residual": str(residual),
            "rejected": True,
        }
        break
    require(incidence_control is not None, "no supported tree column available for incidence plant")

    first_column, first_coefficient = next(iter(coefficients.items()))
    changed_coefficient_residuals = int(np.count_nonzero(matrix[:, first_column]))
    require(changed_coefficient_residuals > 0, "coefficient mutation used zero column")
    coefficient_control = {
        "mutation": "add one to the first reported scaled coefficient",
        "column_index": first_column,
        "old_coefficient": str(first_coefficient),
        "new_coefficient": str(first_coefficient + 1),
        "nonzero_residual_rows": changed_coefficient_residuals,
        "rejected": True,
    }

    target_row = hinge_rows + 6
    require(int(target[target_row]) == 1440, "unexpected target scale")
    target_control = {
        "mutation": "increment the MAX7 linear target coefficient at rank seven by one",
        "row": target_row,
        "old_target": int(target[target_row]),
        "new_target": int(target[target_row]) + 1,
        "residual": "-1",
        "rejected": True,
    }
    return {
        "semantic_sign_mutation": sign_control,
        "incidence_mutation": incidence_control,
        "coefficient_mutation": coefficient_control,
        "target_mutation": target_control,
    }


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--producer-report", type=Path, default=DEFAULT_PRODUCER_REPORT)
    parser.add_argument("--producer-script", type=Path, default=DEFAULT_PRODUCER_SCRIPT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--stream", type=Path, default=DEFAULT_STREAM)
    parser.add_argument("--cert6", type=Path, default=DEFAULT_CERT6)
    parser.add_argument("--cert7", type=Path, default=DEFAULT_CERT7)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(argv)
    begun = time.perf_counter()

    input_hashes_at_start = {
        "producer_report": sha256_path(args.producer_report),
        "producer_script": sha256_path(args.producer_script),
        "manifest": sha256_path(args.manifest),
        "stream": sha256_path(args.stream),
        "cert6": sha256_path(args.cert6),
        "cert7": sha256_path(args.cert7),
        "auditor_source": sha256_path(Path(__file__).resolve()),
    }
    producer = json.loads(args.producer_report.read_text(encoding="utf-8"))
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    require(manifest.get("frozen") is True, "G-0099 manifest is not frozen")
    producer_relative = str(args.producer_report.resolve().relative_to(ROOT))
    require(
        manifest.get("outputs", {}).get(producer_relative) == input_hashes_at_start["producer_report"],
        "frozen manifest does not bind the producer report under audit",
    )
    producer_script_relative = str(args.producer_script.resolve().relative_to(ROOT))
    require(
        manifest.get("outputs", {}).get(producer_script_relative) == input_hashes_at_start["producer_script"],
        "frozen manifest does not bind the producer script",
    )
    for label, path in (("stream", args.stream), ("cert6", args.cert6), ("cert7", args.cert7)):
        relative = str(path.resolve().relative_to(ROOT))
        require(
            manifest.get("sources", {}).get(relative) == input_hashes_at_start[label],
            f"frozen manifest does not bind source {label}",
        )

    burnside = burnside_orbit_counts()
    pairs, descriptors, _signed_keys, dictionary = read_dictionary(args.stream)
    require(dictionary["selected_by_mass"] == burnside, "stream slice count disagrees with Burnside")
    require(dictionary["selected_signed_key_count"] == sum(burnside.values()), "signed orbit keys not exhaustive")
    require(len(pairs) == 3010, "compressed dictionary does not have 3010 columns")

    forests = enumerate_forests()
    trees, column_to_tree = tree_orbits_from_dictionary(pairs, descriptors)
    require(len(forests) == 11, "forest orbit census is not 11")
    require(len(trees) == 53, "tree orbit census is not 53")
    tree_stabilizers = [stabilizer(tree, 7) for tree in trees]
    forest_stabilizers = [stabilizer(forest, 6) for forest in forests]
    tree_sizes = [factorial(7) // value for value in tree_stabilizers]
    forest_sizes = [factorial(6) // value for value in forest_stabilizers]
    labelled_tree_total = 7**5 * (20 // 2)
    require(sum(tree_sizes) == labelled_tree_total, "tree orbit-stabilizer census does not close")

    # Independent labelled forest denominator: enumerate every union and its
    # unordered 2+2 edge colouring directly, with no orbit data involved.
    labelled_forest_keys: set[Pair] = set()
    complete_edges = tuple(itertools.combinations(range(6), 2))
    for union in itertools.combinations(complete_edges, 4):
        probe: Pair = (tuple(union[:2]), tuple(union[2:]))
        if len(components(probe, 6)) != 2:
            continue
        for chosen in itertools.combinations(range(4), 2):
            chosen_set = set(chosen)
            a = tuple(union[i] for i in range(4) if i in chosen_set)
            b = tuple(union[i] for i in range(4) if i not in chosen_set)
            labelled_forest_keys.add(min((a, b), (b, a)))
    require(sum(forest_sizes) == len(labelled_forest_keys), "forest orbit-stabilizer census does not close")

    direct = direct_incidence(trees, forests)
    reverse = reverse_incidence(trees, forests)
    nonzero_entries = 0
    for forest_index in range(len(forests)):
        for tree_index in range(len(trees)):
            r = int(direct[forest_index, tree_index])
            q = int(reverse[forest_index, tree_index])
            if r or q:
                nonzero_entries += 1
                require(tree_sizes[tree_index] * r == 7 * forest_sizes[forest_index] * q, "labelled double count failed")
                require(forest_stabilizers[forest_index] * r == tree_stabilizers[tree_index] * q, "stabilizer double count failed")

    forest_target, max6_selected = forest_target_from_max6(args.cert6, forests)
    max7_trees = max7_tree_projection(args.cert7)
    require(len(max6_selected) == 3 and any(forest_target), "MAX6 dominant projection control failed")
    require(not max7_trees, "published MAX7 certificate unexpectedly has tree terms")
    public6 = replay_public_certificate(args.cert6)
    public7 = replay_public_certificate(args.cert7)
    require(bool(public6["exact_identity"]) and bool(public7["exact_identity"]), "public certificate positive control failed")

    matrix, target, directions, semantic_columns = build_matrix(pairs, column_to_tree, direct, forest_target)
    require(matrix.shape == (648, 3010), f"unexpected augmented shape {matrix.shape}")
    denominator = reduce(lcm, (value.denominator for value in forest_target), 1)
    require(denominator == 1440, "unexpected target denominator")
    coefficients, solution_receipt = sparse_solution(producer, descriptors, denominator)
    replay_ok, residuals = replay_rows(matrix, target, coefficients)
    require(replay_ok, f"delivered sparse solution has residuals: {residuals[:3]}")

    matrix_hash = hashlib.sha256(matrix.tobytes(order="C")).hexdigest()
    target_hash = hashlib.sha256(target.tobytes(order="C")).hexdigest()
    direction_hash = canonical_sha256(directions)
    descriptor_hash = canonical_sha256(descriptors)
    reported_system = producer["augmented_system"]
    require(isinstance(reported_system, dict), "malformed producer system receipt")
    receipt_matches = {
        "matrix": matrix_hash == reported_system["matrix_int64_c_sha256"],
        "target": target_hash == reported_system["target_int64_c_sha256"],
        "directions": direction_hash == reported_system["direction_list_sha256"],
        "descriptors": descriptor_hash == reported_system["column_descriptors_sha256"],
        "sparse_solution": solution_receipt["sparse_solution_canonical_sha256"] == solution_receipt["reported_sparse_solution_sha256"],
    }
    require(all(receipt_matches.values()), f"producer receipt mismatch: {receipt_matches}")

    modular = {}
    pivot_columns_at_gate: list[int] | None = None
    pivot_rows_at_gate: list[int] | None = None
    for prime in PRIMES:
        rank, pivot_columns_here, pivot_rows_here = modular_pivots(matrix, prime)
        augmented_rank = int(to_nmod(np.column_stack((matrix, target)), prime).rank())
        modular[str(prime)] = {"rank": rank, "augmented_rank": augmented_rank}
        require(rank == augmented_rank, f"membership failed modulo {prime}")
        if prime == 1_000_003:
            pivot_columns_at_gate = pivot_columns_here
            pivot_rows_at_gate = pivot_rows_here
    assert pivot_columns_at_gate is not None and pivot_rows_at_gate is not None
    exact_q_rank = int(fmpz_mat(matrix.tolist()).rank())
    require(exact_q_rank == 327, f"exact Q rank is {exact_q_rank}, not 327")

    reported_solution = producer["solution"]
    assert isinstance(reported_solution, dict)
    pivot_receipts = {
        "pivot_columns": canonical_sha256(pivot_columns_at_gate) == reported_solution["pivot_columns_sha256"],
        "pivot_rows": canonical_sha256(pivot_rows_at_gate) == reported_solution["pivot_rows_sha256"],
        "rank_over_Q": exact_q_rank == int(reported_solution["rank_over_Q"]),
    }
    require(all(pivot_receipts.values()), f"pivot/rank receipt mismatch: {pivot_receipts}")

    point_replays = direct_point_replay(pairs, coefficients)
    require(all(bool(item["matches"]) for item in point_replays), "direct point replay failed")
    mutations = mutation_controls(
        pairs, matrix, target, directions, semantic_columns, column_to_tree,
        direct, trees, forests, reverse, coefficients,
    )

    input_hashes_at_end = {
        "producer_report": sha256_path(args.producer_report),
        "producer_script": sha256_path(args.producer_script),
        "manifest": sha256_path(args.manifest),
        "stream": sha256_path(args.stream),
        "cert6": sha256_path(args.cert6),
        "cert7": sha256_path(args.cert7),
        "auditor_source": sha256_path(Path(__file__).resolve()),
    }
    require(input_hashes_at_start == input_hashes_at_end, "an audited input changed during execution")

    producer_combinatorics = producer["combinatorics"]
    assert isinstance(producer_combinatorics, dict)
    producer_target = [Fraction(value) for value in producer["forest_target_coefficients"]]
    exact_receipt_comparisons = {
        "tree_stabilizers": tree_stabilizers == producer_combinatorics["tree_stabilizers"],
        "forest_stabilizers": forest_stabilizers == producer_combinatorics["forest_stabilizers"],
        "tree_labelled_orbit_sizes": tree_sizes == producer_combinatorics["tree_labelled_orbit_sizes"],
        "forest_labelled_orbit_sizes": forest_sizes == producer_combinatorics["forest_labelled_orbit_sizes"],
        "direct_incidence_hash": hashlib.sha256(direct.tobytes(order="C")).hexdigest() == producer_combinatorics["direct_incidence_int64_c_sha256"],
        "reverse_incidence_hash": hashlib.sha256(reverse.tobytes(order="C")).hexdigest() == producer_combinatorics["reverse_incidence_int64_c_sha256"],
        "direct_nonzeros": int(np.count_nonzero(direct)) == int(producer_combinatorics["direct_incidence_nonzeros"]),
        "direct_sum": int(direct.sum()) == int(producer_combinatorics["direct_incidence_sum"]),
        "reverse_sum": int(reverse.sum()) == int(producer_combinatorics["reverse_incidence_sum"]),
        "forest_target": forest_target == producer_target,
    }
    require(all(exact_receipt_comparisons.values()), f"combinatorial receipt mismatch: {exact_receipt_comparisons}")

    report = {
        "schema": "max11-g0102-cleanroom-audit-g0099-v1",
        "verdict": "PASS",
        "reviewed_producer_report_sha256": input_hashes_at_start["producer_report"],
        "input_hashes": input_hashes_at_start,
        "independence": {
            "producer_modules_imported": [],
            "semantic_method": "literal enumeration of every vertex order and direct branch linear forms",
            "orbit_count_method": "Burnside over S7 x global-sign-swap plus independent canonicalization",
            "linear_algebra": "exact Fraction certificate replay; FLINT only for independent whole-matrix Q rank and modular pivot receipts",
            "same_model_family_boundary": "T1 clean-room computational replay, not T2 review",
        },
        "dictionary": {
            **dictionary,
            "burnside_orbits_by_mass": burnside,
            "burnside_total_signed_orbits": sum(burnside.values()),
            "extra_common_loop_basis_columns": 1,
            "completeness_argument": (
                "Every degree-three pair cancels to a signed loop-inclusive multigraph of balanced mass s<=3. "
                "Burnside gives exactly the independently canonicalized stream counts.  Common padding changes "
                "only the symmetrized common-edge component; the all-nonloop padding plus the separate all-loop "
                "atom spans its two edge orbits over Q."
            ),
        },
        "orbits_and_incidence": {
            "tree_orbits": len(trees),
            "forest_orbits": len(forests),
            "labelled_tree_universe": labelled_tree_total,
            "tree_orbit_sizes_sum": sum(tree_sizes),
            "labelled_forest_universe": len(labelled_forest_keys),
            "forest_orbit_sizes_sum": sum(forest_sizes),
            "tree_stabilizers": tree_stabilizers,
            "forest_stabilizers": forest_stabilizers,
            "direct_incidence_nonzeros": int(np.count_nonzero(direct)),
            "direct_incidence_sum": int(direct.sum()),
            "reverse_incidence_sum": int(reverse.sum()),
            "all_weighted_nonzeros_checked": nonzero_entries,
            "D_convention": "D(F,T)=7*r(T,F) for full permutation-sum Rueß basis coefficients",
            "double_count": "N_T*r(T,F)=7*N_F*q(F,T), equivalently a_F*r(T,F)=a_T*q(F,T)",
            "receipt_comparisons": exact_receipt_comparisons,
        },
        "public_controls": {
            "max6_identity": public6,
            "max7_identity": public7,
            "max6_dominant_c2_terms": max6_selected,
            "max6_dominant_c2_projection": [str(value) for value in forest_target],
            "published_max7_tree_projection": max7_trees,
            "published_vector_transfer": "FAILS because its tree projection is zero; this says nothing about other MAX7 coefficient vectors",
        },
        "augmented_system": {
            "shape": list(matrix.shape),
            "hinge_rows": len(directions),
            "linear_rows": 7,
            "incidence_rows": len(forests),
            "target_denominator": denominator,
            "matrix_int64_c_sha256": matrix_hash,
            "target_int64_c_sha256": target_hash,
            "direction_list_sha256": direction_hash,
            "column_descriptors_sha256": descriptor_hash,
            "receipt_matches": receipt_matches,
            "modular_ranks": modular,
            "exact_rank_over_Q": exact_q_rank,
            "exact_nullity_over_Q": matrix.shape[1] - exact_q_rank,
            "pivot_receipts": pivot_receipts,
            "row_completeness": (
                "All primitive hinge directions occurring in all 3010 columns were included.  Literal n! "
                "enumeration supplies each column's full linear-plus-hinge normal form on the sorted cone; "
                "distinct retained primitive directions have distinct interior bend hyperplanes."
            ),
        },
        "solution": {
            **solution_receipt,
            "all_648_rows_exact_fraction_replay": replay_ok,
            "residuals": residuals,
            "direct_function_value_replays": point_replays,
            "constrained_solution_exists": True,
            "nonuniqueness": (
                f"The constrained system has exact nullity {matrix.shape[1] - exact_q_rank}; therefore the "
                "published MAX7 vector's failed tree projection cannot decide existence of a different vector."
            ),
        },
        "planted_mutations": mutations,
        "claim_boundary": {
            "established": (
                "For the complete compressed n=7 degree-three pairwise Rueß dictionary and the imposed "
                "D=7r constraint, an exact rational MAX7 coefficient vector exists whose D-image equals "
                "the dominant c2 projection of the public MAX6 certificate."
            ),
            "not_established": [
                "that D is a semantic consequence of restriction from MAX7 to MAX6",
                "that the analogous n=10 -> n=11 constrained system is feasible",
                "any MAX11 functional identity",
                "any unrestricted two-hidden-layer ReLU lower bound",
                "novelty, external refereeing, or T2 independence",
            ],
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
            "byteorder": sys.byteorder,
        },
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }
    write_json(args.output, report)
    print(
        f"G0102 PASS shape={matrix.shape[0]}x{matrix.shape[1]} rankQ={exact_q_rank} "
        f"support={len(coefficients)} wall={report['wall_seconds']} output={args.output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
