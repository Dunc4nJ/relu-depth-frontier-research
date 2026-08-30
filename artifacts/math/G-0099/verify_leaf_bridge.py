#!/usr/bin/env python3
"""Independent exact verifier for the G-0099 leaf/bridge artifacts.

Independence boundaries:

* lower semantic replay literally enumerates all 7! vertex orders for only
  the exported sparse support; it does not import the producer or G-0090's
  subset dynamic program;
* lower quotient/stabilizer/incidence replay uses exhaustive permutations;
* the n=10 -> 11 selected minor is rebuilt from the exported sparse matrix and
  ranked by python-flint, rather than by the producer's Python sparse echelon;
* direct/reverse weighted incidence is replayed entry by entry from both
  exported sparse orientations.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from functools import reduce
import hashlib
import itertools
import json
from math import factorial, gcd
import os
from pathlib import Path
import platform
import time
from typing import Iterable, Sequence

import numpy as np
from flint import nmod_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
LOWER_REPORT = HERE / "leaf_bridge_complete_v1.json"
SCALE_REPORT = HERE / "leaf_bridge_n10_n11_v1.json"
LOWER_PRODUCER = HERE / "leaf_bridge_n6_n7.py"
SCALE_PRODUCER = HERE / "leaf_bridge_n10_n11.py"
SCHEMA = "max11-g0099-independent-leaf-bridge-verifier-v1"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class VerifyError(RuntimeError):
    """An exact replay or mutation control failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerifyError(message)


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
        side: list[Edge] = []
        for raw_edge in raw_side:
            u, v = map(int, raw_edge)
            side.append((min(u, v), max(u, v)))
        sides.append(tuple(sorted(side)))
    require(len(sides) == 2, "pair must have two branches")
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


def brute_key_and_stabilizer(pair: Pair, n: int) -> tuple[Pair, int]:
    pair = normalize_pair(pair)
    swapped = (pair[1], pair[0])
    best: Pair | None = None
    stabilizer = 0
    for permutation in itertools.permutations(range(n)):
        transformed = relabel_pair(pair, permutation)
        if transformed in (pair, swapped):
            stabilizer += 1
        candidate = min(transformed, (transformed[1], transformed[0]))
        if best is None or candidate < best:
            best = candidate
    require(best is not None, "empty permutation group")
    return best, stabilizer


def graph_components(pair: Pair, n: int) -> int:
    adjacency = [set() for _ in range(n)]
    for side in pair:
        for u, v in side:
            require(u != v, "component replay received loop")
            adjacency[u].add(v)
            adjacency[v].add(u)
    unseen = set(range(n))
    count = 0
    while unseen:
        count += 1
        stack = [min(unseen)]
        component: set[int] = set()
        while stack:
            vertex = stack.pop()
            if vertex in component:
                continue
            component.add(vertex)
            stack.extend(adjacency[vertex] - component)
        unseen -= component
    return count


def delete_leaf_and_edge(pair: Pair, leaf: int, removed: Edge) -> Pair:
    remaining = [vertex for vertex in range(7) if vertex != leaf]
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
    require(removed_once, "deletion replay missed opposite edge")
    return sides[0], sides[1]


def literal_semantic_column(pair: Pair, n: int) -> tuple[tuple[int, ...], dict[Direction, int]]:
    """Literal S_n normal form, independent of the producer's subset DP."""

    weights = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for u, v in side:
            if u == v:
                weights[u][u] += sign
            else:
                weights[u][v] += sign
                weights[v][u] += sign
    linear = [0] * n
    raw_histogram: Counter[Direction] = Counter()
    for ordering in itertools.permutations(range(n)):
        rank_of = {vertex: rank for rank, vertex in enumerate(ordering)}
        # Literal left branch on the ascending chamber.
        for u, v in pair[0]:
            linear[max(rank_of[u], rank_of[v])] += 1
        lower: list[int] = []
        word: list[int] = []
        for vertex in ordering:
            word.append(weights[vertex][vertex] + sum(weights[vertex][other] for other in lower))
            lower.append(vertex)
        raw_histogram[tuple(word)] += 1

    hinges: dict[Direction, int] = defaultdict(int)
    for raw_direction, multiplicity in raw_histogram.items():
        if not any(raw_direction):
            continue
        magnitude = reduce(gcd, (abs(value) for value in raw_direction), 0)
        first = next(value for value in raw_direction if value)
        if first < 0:
            for rank, value in enumerate(raw_direction):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // magnitude for value in raw_direction)
        else:
            primitive = tuple(value // magnitude for value in raw_direction)
        require(sum(primitive) == 0, "literal direction is not balanced")
        prefix = 0
        nonpositive = True
        for value in primitive[:-1]:
            prefix += value
            if prefix < 0:
                nonpositive = False
                break
        if not nonpositive:
            hinges[primitive] += multiplicity * magnitude
    return tuple(linear), dict(hinges)


def verify_lower(report: dict[str, object]) -> dict[str, object]:
    begun = time.perf_counter()
    require(report["result"] == "EXACT_MEMBERSHIP", "lower report is not exact membership")
    require(report["producer_sha256_before_output"] == sha256_path(LOWER_PRODUCER), "lower producer hash drift")
    trees_raw = report["tree_orbits"]
    forests_raw = report["forest_orbits"]
    require(len(trees_raw) == 53 and len(forests_raw) == 11, "lower orbit census drift")

    tree_pairs = [normalize_pair(item["representative_zero_based"]) for item in trees_raw]
    forest_pairs = [normalize_pair(item["representative_zero_based"]) for item in forests_raw]
    tree_keys: list[Pair] = []
    forest_keys: list[Pair] = []
    for item, pair in zip(trees_raw, tree_pairs, strict=True):
        key, stabilizer = brute_key_and_stabilizer(pair, 7)
        require(stabilizer == int(item["stabilizer"]), "lower tree stabilizer replay failed")
        tree_keys.append(key)
    for item, pair in zip(forests_raw, forest_pairs, strict=True):
        key, stabilizer = brute_key_and_stabilizer(pair, 6)
        require(stabilizer == int(item["stabilizer"]), "lower forest stabilizer replay failed")
        forest_keys.append(key)
    require(len(set(tree_keys)) == 53 and len(set(forest_keys)) == 11, "lower brute quotient collision")
    forest_index = {key: index for index, key in enumerate(forest_keys)}

    direct = [[0] * 53 for _ in range(11)]
    for tree_index, pair in enumerate(tree_pairs):
        degree = Counter(vertex for side in pair for edge in side for vertex in edge)
        for leaf in (vertex for vertex in range(7) if degree[vertex] == 1):
            leaf_colour = next(
                colour for colour, side in enumerate(pair) if any(leaf in edge for edge in side)
            )
            for removed in pair[1 - leaf_colour]:
                forest = delete_leaf_and_edge(pair, leaf, removed)
                require(graph_components(forest, 6) == 2, "lower deletion component drift")
                key, _stabilizer = brute_key_and_stabilizer(forest, 6)
                direct[forest_index[key]][tree_index] += 1
    exported_direct = report["combinatorics"]["direct_r_matrix"]
    require(direct == exported_direct, "independent lower direct-incidence matrix mismatch")
    direct_array = np.asarray(direct, dtype=np.int64)
    require(
        hashlib.sha256(direct_array.tobytes(order="C")).hexdigest()
        == report["combinatorics"]["direct_incidence_int64_c_sha256"],
        "lower direct matrix byte hash mismatch",
    )

    denominator = int(report["augmented_system"]["target_denominator"])
    solution = report["solution"]["sparse_solution"]
    require(canonical_sha256(solution) == report["solution"]["sparse_solution_sha256"], "lower solution hash mismatch")
    linear = [Fraction(0) for _ in range(7)]
    hinges: dict[Direction, Fraction] = defaultdict(Fraction)
    incidence = [Fraction(0) for _ in range(11)]
    literal_cache: dict[Pair, tuple[tuple[int, ...], dict[Direction, int]]] = {}
    first_mutation: tuple[Fraction, tuple[int, ...], dict[Direction, int], list[int]] | None = None
    for item in solution:
        coefficient = Fraction(item["ruess_full_permutation_sum_coefficient"])
        scaled = Fraction(item["coefficient_numerator_over_scaled_target"])
        require(coefficient == scaled / denominator, "lower coefficient scaling mismatch")
        pair = normalize_pair(item["descriptor"]["pair_zero_based"])
        column = literal_cache.setdefault(pair, literal_semantic_column(pair, 7))
        column_linear, column_hinges = column
        for index, value in enumerate(column_linear):
            linear[index] += coefficient * value
        for direction, value in column_hinges.items():
            hinges[direction] += coefficient * value
        key, _stabilizer = brute_key_and_stabilizer(pair, 7)
        column_incidence = [0] * 11
        if key in set(tree_keys):
            tree_index = tree_keys.index(key)
            column_incidence = [7 * direct[row][tree_index] for row in range(11)]
            for row, value in enumerate(column_incidence):
                incidence[row] += coefficient * value
        if first_mutation is None:
            first_mutation = (Fraction(1, denominator), column_linear, column_hinges, column_incidence)
    hinges = {direction: value for direction, value in hinges.items() if value}
    require(not hinges, "independent literal replay left lower hinge residual")
    require(linear == [Fraction(0)] * 6 + [Fraction(1)], "independent literal replay linear mismatch")
    expected_incidence = [Fraction(value) for value in report["forest_target_coefficients"]]
    require(incidence == expected_incidence, "independent lower incidence target mismatch")

    require(first_mutation is not None, "empty lower support")
    delta, mutation_linear, mutation_hinges, mutation_incidence = first_mutation
    mutation_nonzero = any(delta * value for value in mutation_linear) or any(
        delta * value for value in mutation_hinges.values()
    ) or any(delta * value for value in mutation_incidence)
    require(bool(mutation_nonzero), "one-coefficient mutation escaped literal replay")
    return {
        "claim_class": "exact",
        "outcome": "positive",
        "report_sha256": sha256_path(LOWER_REPORT),
        "producer_sha256": sha256_path(LOWER_PRODUCER),
        "bruteforce_tree_orbits": len(set(tree_keys)),
        "bruteforce_forest_orbits": len(set(forest_keys)),
        "direct_matrix_entries_checked": int(direct_array.size),
        "literal_permutations_per_support_atom": factorial(7),
        "literal_support_atoms": len(solution),
        "literal_hinge_residual_count": len(hinges),
        "literal_linear_replay": [str(value) for value in linear],
        "literal_incidence_replay": [str(value) for value in incidence],
        "one_coefficient_mutation_rejected": True,
        "seconds": round(time.perf_counter() - begun, 6),
    }


def sparse_payload_sha(payload: object) -> str:
    return canonical_sha256(payload)


def verify_scale(report: dict[str, object]) -> dict[str, object]:
    begun = time.perf_counter()
    require(report["result"] == "EXACT_INCIDENCE_SURJECTION", "scale report is not exact surjection")
    require(report["producer_sha256_before_output"] == sha256_path(SCALE_PRODUCER), "scale producer hash drift")
    columns = report["sparse_direct_r_columns"]
    reverse_rows = report["sparse_reverse_q_rows"]
    forests = report["forest_orbits"]
    tree_stabilizers = list(map(int, report["tree_stabilizers"]))
    require(len(columns) == 12_459 and len(reverse_rows) == len(forests) == 1_387, "scale shape drift")
    require(sparse_payload_sha(columns) == report["sparse_direct_r_columns_sha256"], "direct sparse hash mismatch")
    require(sparse_payload_sha(reverse_rows) == report["sparse_reverse_q_rows_sha256"], "reverse sparse hash mismatch")
    reverse_lookup = [dict((int(tree), int(value)) for tree, value in row) for row in reverse_rows]
    weighted_checked = 0
    for tree, column in enumerate(columns):
        for forest, r in column:
            forest = int(forest)
            r = int(r)
            q = reverse_lookup[forest].get(tree, 0)
            require(q != 0, "scale reverse support missing direct entry")
            require(
                int(forests[forest]["stabilizer"]) * r == tree_stabilizers[tree] * q,
                "scale stabilizer identity failed",
            )
            weighted_checked += 1
    require(weighted_checked == 171_131, "scale weighted-check census drift")
    require(sum(len(row) for row in reverse_rows) == weighted_checked, "scale reverse has extra support")

    prime = int(report["rank_and_image"]["prime"])
    selected = list(map(int, report["rank_and_image"]["selected_columns"]))
    require(len(selected) == len(forests), "selected minor is not square")
    minor = np.zeros((len(forests), len(selected)), dtype=np.uint32)
    for position, tree in enumerate(selected):
        for forest, r in columns[tree]:
            minor[int(forest), position] = (11 * int(r)) % prime
    field = nmod_mat(minor.shape[0], minor.shape[1], memoryview(minor.ravel()), prime)
    independent_rank = int(field.rank())
    require(independent_rank == len(forests), "FLINT selected-minor rank replay failed")

    first_forest, first_r = columns[0][0]
    first_q = reverse_lookup[int(first_forest)][0]
    require(
        int(forests[int(first_forest)]["stabilizer"]) * (int(first_r) + 1)
        != tree_stabilizers[0] * first_q,
        "scale one-incidence mutation escaped independent check",
    )
    require(report["rank_and_image"]["target_reduces_to_zero_mod_p"] is True, "scale target reduction is not zero")
    require(not report["rank_and_image"]["target_remainder_mod_p"], "scale target remainder payload nonempty")
    return {
        "claim_class": "exact",
        "outcome": "positive",
        "report_sha256": sha256_path(SCALE_REPORT),
        "producer_sha256": sha256_path(SCALE_PRODUCER),
        "sparse_shape": [len(forests), len(columns)],
        "direct_reverse_nonzeros_checked": weighted_checked,
        "independent_backend": "python-flint nmod_mat.rank on reconstructed selected minor",
        "selected_minor_shape": list(minor.shape),
        "selected_minor_uint32_c_sha256": hashlib.sha256(minor.tobytes(order="C")).hexdigest(),
        "selected_minor_rank_mod_p": independent_rank,
        "exact_Q_implication": (
            "The reconstructed integer minor is nonsingular modulo p, hence its determinant is "
            "a nonzero integer and D is surjective over Q."
        ),
        "one_incidence_mutation_rejected": True,
        "seconds": round(time.perf_counter() - begun, 6),
    }


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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    begun = time.perf_counter()
    lower = json.loads(LOWER_REPORT.read_text(encoding="utf-8"))
    scale = json.loads(SCALE_REPORT.read_text(encoding="utf-8"))
    lower_result = verify_lower(lower)
    scale_result = verify_scale(scale)
    report = {
        "schema": SCHEMA,
        "result": "PASS",
        "claim_class": "exact",
        "outcome": "positive",
        "lower_complete_semantic_gate": lower_result,
        "scale_combinatorial_incidence_gate": scale_result,
        "producer_sha256_before_output": sha256_path(Path(__file__).resolve()),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
            "pid": os.getpid(),
        },
        "wall_seconds": round(time.perf_counter() - begun, 6),
        "claim_boundary": (
            "This independently verifies the exact n6->n7 sparse global normal-form identity "
            "with its incidence constraint, and exact n10->n11 combinatorial D surjectivity. "
            "It does not build or verify an n11 semantic solution, does not prove that D is a "
            "necessary semantic constraint, and makes no global-wall or unrestricted-depth claim."
        ),
    }
    write_json_atomic(args.output.resolve(), report)
    print(
        f"G0099_VERIFY_PASS lower_support={lower_result['literal_support_atoms']} "
        f"minor={scale_result['selected_minor_shape'][0]} "
        f"wall={report['wall_seconds']} output={args.output}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
