#!/usr/bin/env python3
"""Exact joint gate for the preregistered rooted Reynolds gap recurrence."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import hashlib
import importlib.util
from itertools import combinations_with_replacement, permutations
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence

from flint import fmpz_mat
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREREGISTRATION.md"
CERTIFICATES = ROOT / "literature/repos/max-relu-certificates/certificates"
CERT5 = CERTIFICATES / "certificate_5_2.json"
CERT6 = CERTIFICATES / "certificate_6_2.json"
CERT7 = CERTIFICATES / "certificate_7_3.json"
CERT8 = CERTIFICATES / "certificate_8_3.json"
CERT10 = CERTIFICATES / "certificate_10_4.json"
CERT9_395 = ROOT / "artifacts/math/G-0115/unrestricted_full_semantic_certificate_v1.json"
DP_PATH = ROOT / "artifacts/math/G-0094/cleanroom_star_quotient.py"

EXPECTED = {
    PREREGISTRATION: "1f43bc85f8124e3147499527e6bd522e901c91d391b14d1d9c4fe12416ef8b79",
    CERT5: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    CERT6: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    CERT7: "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT10: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    CERT9_395: "628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e",
    DP_PATH: "d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71",
}

ORBIT_NAMES = (
    "RR",
    "RS",
    "RL",
    "RE",
    "SS_same",
    "SS_distinct",
    "SL_hit",
    "SL_miss",
    "SE_hit",
    "SE_miss",
    "LL_same",
    "LL_distinct",
    "LE_hit",
    "LE_miss",
    "EE_same",
    "EE_share",
    "EE_disjoint",
)
ORBIT_INDEX = {name: index for index, name in enumerate(ORBIT_NAMES)}
INT64_SAFE_BOUND = 1 << 62

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]
Semantic = tuple[tuple[int, ...], dict[Direction, int]]


class GapError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GapError(message)


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


def array_sha(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast("B")).hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def bind_inputs() -> dict[str, str]:
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"input drift: {observed}")
    return {str(path.relative_to(ROOT)): digest for path, digest in observed.items()}


def load_dp(name: str):
    require(sha256(DP_PATH) == EXPECTED[DP_PATH], "DP drift")
    spec = importlib.util.spec_from_file_location(name, DP_PATH)
    require(spec is not None and spec.loader is not None, "cannot load DP")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_pair(raw: object, n: int) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[Side] = []
    for raw_side in raw:
        require(isinstance(raw_side, list), "malformed side")
        side = []
        for raw_edge in raw_side:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            u, v = map(int, raw_edge)
            require(1 <= u <= v <= n, "edge outside arity")
            side.append((u - 1, v - 1))
        sides.append(tuple(sorted(side)))
    require(len(sides[0]) == len(sides[1]), "unequal branch degree")
    return sides[0], sides[1]


@dataclass(frozen=True)
class Term:
    coefficient: Fraction
    pair: Pair


def load_certificate(path: Path, n: int, degree: int) -> list[Term]:
    require(sha256(path) == EXPECTED[path], f"certificate drift: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n and isinstance(document.get("terms"), list), "bad certificate")
    output = []
    for raw in document["terms"]:
        pair = parse_pair(raw["pair"], n)
        require(len(pair[0]) == degree, "certificate degree drift")
        output.append(Term(Fraction(raw["coefficient"]), pair))
    return output


def gap_terms(high: Sequence[Term], low: Sequence[Term], n: int) -> list[Term]:
    return [Term(n * term.coefficient, term.pair) for term in high] + [
        Term(-term.coefficient, term.pair) for term in low
    ]


def coefficient_lcm(terms: Sequence[Term]) -> int:
    value = 1
    for term in terms:
        value = math.lcm(value, term.coefficient.denominator)
    return value


def normal_form(dp, pair: Pair, n: int) -> Semantic:
    linear, directions, coefficients = dp.ordered_normal_form(pair, n)
    hinges = {
        tuple(map(int, direction)): int(coefficient)
        for direction, coefficient in zip(directions, coefficients, strict=True)
        if int(coefficient)
    }
    return tuple(map(int, linear)), hinges


def literal_normal_form(pair: Pair, n: int) -> Semantic:
    linear = [0] * n
    hinges: Counter[Direction] = Counter()
    for order in permutations(range(n)):
        position = [0] * n
        for rank, label in enumerate(order):
            position[label] = rank
        forms = []
        for side in pair:
            vector = [0] * n
            for u, v in side:
                vector[max(position[u], position[v])] += 1
            forms.append(tuple(vector))
        base, other = sorted(forms)
        direction = tuple(y - x for x, y in zip(base, other, strict=True))
        prefix = 0
        sign_definite = True
        for value in direction[:-1]:
            prefix += value
            if prefix < 0:
                sign_definite = False
        for index, value in enumerate(base):
            linear[index] += value
        if sign_definite:
            continue
        divisor = math.gcd(*(abs(value) for value in direction))
        primitive = tuple(value // divisor for value in direction)
        hinges[primitive] += divisor
    return tuple(linear), dict(hinges)


def add_semantic(
    linear: list[Fraction], hinges: dict[Direction, Fraction], semantic: Semantic, coefficient: Fraction
) -> None:
    for index, value in enumerate(semantic[0]):
        linear[index] += coefficient * value
    for direction, value in semantic[1].items():
        updated = hinges.get(direction, Fraction()) + coefficient * value
        if updated:
            hinges[direction] = updated
        else:
            hinges.pop(direction, None)


def replay_terms(dp, terms: Sequence[Term], n: int, target: Sequence[Fraction]) -> tuple[list[Fraction], dict[Direction, Fraction], Semantic]:
    linear = [Fraction() for _ in range(n)]
    hinges: dict[Direction, Fraction] = {}
    first_semantic: Semantic | None = None
    for term in terms:
        semantic = normal_form(dp, term.pair, n)
        if first_semantic is None and term.coefficient:
            first_semantic = semantic
        add_semantic(linear, hinges, semantic, term.coefficient)
    require(first_semantic is not None, "missing nonzero control term")
    require(not hinges and linear == list(target), f"exact replay failed at n={n}")
    return linear, hinges, first_semantic


def replay_certificate(dp, terms: Sequence[Term], n: int, degree: int, label: str) -> dict[str, object]:
    target = [Fraction() for _ in range(n - 1)] + [Fraction(1)]
    linear, hinges, first = replay_terms(dp, terms, n, target)
    denominator = coefficient_lcm(terms)
    mutated_linear = linear.copy()
    mutated_hinges = dict(hinges)
    add_semantic(mutated_linear, mutated_hinges, first, Fraction(1, denominator))
    require(mutated_hinges or mutated_linear != target, f"{label} mutation escaped")
    return {
        "label": label,
        "n": n,
        "degree": degree,
        "terms": len(terms),
        "coefficient_lcm": denominator,
        "linear": [str(value) for value in linear],
        "hinge_residual_nonzeros": 0,
        "one_unit_first_coefficient_mutation_rejected": True,
    }


def replay_gap(dp, high: Sequence[Term], low: Sequence[Term], n: int, degree: int) -> dict[str, object]:
    gap = gap_terms(high, low, n)
    target = [Fraction() for _ in range(n)]
    target[-2] = -1
    target[-1] = 1
    linear, _hinges, _first = replay_terms(dp, gap, n, target)
    induced_target = [Fraction() for _ in range(n)]
    induced_target[-2] = 1
    induced_target[-1] = n - 1
    induced_linear, _induced_hinges, _ = replay_terms(dp, low, n, induced_target)
    return {
        "n": n,
        "degree": degree,
        "terms": len(gap),
        "coefficient_lcm": coefficient_lcm(gap),
        "gap_linear": [str(value) for value in linear],
        "induced_lower_linear": [str(value) for value in induced_linear],
        "hinge_residual_nonzeros": 0,
        "termwise_induction_replayed": True,
    }


def edge_kind(edge: Edge, root: int) -> tuple[str, tuple[int, ...]]:
    u, v = edge
    if u == root and v == root:
        return "R", ()
    if u == root or v == root:
        old = v if u == root else u
        return "S", (old,)
    if u == v:
        return "L", (u,)
    return "E", tuple(sorted((u, v)))


def rooted_orbit(left: Edge, right: Edge, root: int) -> str:
    first = edge_kind(left, root)
    second = edge_kind(right, root)
    order = {"R": 0, "S": 1, "L": 2, "E": 3}
    if order[first[0]] > order[second[0]]:
        first, second = second, first
    kinds = first[0] + second[0]
    a, b = first[1], second[1]
    if kinds in {"RR", "RS", "RL", "RE"}:
        return kinds
    if kinds == "SS":
        return "SS_same" if a == b else "SS_distinct"
    if kinds == "SL":
        return "SL_hit" if a[0] == b[0] else "SL_miss"
    if kinds == "SE":
        return "SE_hit" if a[0] in b else "SE_miss"
    if kinds == "LL":
        return "LL_same" if a == b else "LL_distinct"
    if kinds == "LE":
        return "LE_hit" if a[0] in b else "LE_miss"
    require(kinds == "EE", f"unknown rooted edge kinds: {kinds}")
    if a == b:
        return "EE_same"
    return "EE_share" if set(a) & set(b) else "EE_disjoint"


def relabel_edge(edge: Edge, permutation: Sequence[int]) -> Edge:
    return tuple(sorted((permutation[edge[0]], permutation[edge[1]])))  # type: ignore[return-value]


def classifier_census(n: int) -> dict[str, int]:
    root = n - 1
    edges = tuple(combinations_with_replacement(range(n), 2))
    counts = Counter(rooted_orbit(left, right, root) for left in edges for right in edges)
    require(tuple(sorted(counts)) == tuple(sorted(ORBIT_NAMES)), f"rooted orbit census drift at n={n}")
    require(sum(counts.values()) == len(edges) ** 2, f"rooted raw count drift at n={n}")
    return {name: counts[name] for name in ORBIT_NAMES}


def classifier_controls(dp) -> dict[str, object]:
    n = 7
    root = n - 1
    pairs = (
        ((root, root), (root, 0)),
        ((root, 0), (root, 1)),
        ((root, 0), (0, 1)),
        ((0, 0), (0, 1)),
        ((0, 1), (2, 3)),
    )
    permutations_to_check = (
        (2, 3, 4, 5, 0, 1, root),
        (1, 0, 2, 3, 5, 4, root),
    )
    for left, right in pairs:
        baseline = rooted_orbit(left, right, root)
        require(rooted_orbit(right, left, root) == baseline, "edge swap changed rooted orbit")
        for permutation in permutations_to_check:
            require(
                rooted_orbit(relabel_edge(left, permutation), relabel_edge(right, permutation), root)
                == baseline,
                "old-label relabelling changed rooted orbit",
            )
    planted = ((root, 0), (root, 1))
    require(rooted_orbit(*planted, root) == "SS_distinct", "planted spoke orbit drift")
    require(rooted_orbit(*planted, 2) != "SS_distinct", "moving-root mutant escaped")
    unrooted_relation = "SHARE" if set(planted[0]) & set(planted[1]) else "DISJOINT"
    require(unrooted_relation != rooted_orbit(*planted, root), "root-collapse mutant escaped")
    literal_pairs: tuple[Pair, ...] = (
        (((0, root), (0, 1)), ((1, root), (2, 3))),
        (((0, root), (0, 1), (3, 3)), ((1, root), (2, 3), (4, 5))),
    )
    for literal_pair in literal_pairs:
        require(
            literal_normal_form(literal_pair, n) == normal_form(dp, literal_pair, n),
            f"literal/DP rooted degree-{len(literal_pair[0])} atom mismatch",
        )
    mutant_pair: Pair = (((0, root), (0, 2)), literal_pairs[0][1])
    require(
        normal_form(dp, mutant_pair, n) != normal_form(dp, literal_pairs[0], n),
        "branch-edge semantic mutant escaped",
    )
    censuses = {str(value): classifier_census(value) for value in (7, 9, 11)}
    return {
        "orbit_names": list(ORBIT_NAMES),
        "old_label_relabellings_checked": len(permutations_to_check),
        "edge_swap_preserved": True,
        "moving_root_mutant_rejected": True,
        "unrooted_classifier_mutant_rejected": True,
        "literal_permutation_equals_dp_degrees": [2, 3],
        "branch_edge_semantic_mutant_rejected": True,
        "ordered_edge_pair_censuses": censuses,
    }


def cancel_with_common(pair: Pair) -> tuple[Pair, Counter[Edge]]:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    return (tuple(sorted(left.elements())), tuple(sorted(right.elements()))), common


def occurrence_certificate(first: Side, second: Side, n: int) -> bytes:
    adjacency: dict[int, set[int]] = {index: set() for index in range(n)}
    first_nodes: list[int] = []
    second_nodes: list[int] = []
    for bucket, side in ((first_nodes, first), (second_nodes, second)):
        for u, v in side:
            node = len(adjacency)
            adjacency[node] = set()
            bucket.append(node)
            for coordinate in {u, v}:
                adjacency[node].add(coordinate)
                adjacency[coordinate].add(node)
    coloring = [set(range(n))]
    if first_nodes:
        coloring.append(set(first_nodes))
    if second_nodes:
        coloring.append(set(second_nodes))
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={node: sorted(neighbors) for node, neighbors in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph)


def signed_key(pair: Pair, n: int) -> bytes:
    """Return the exact canonical signed-W certificate, not a digest of it."""

    residual, _common = cancel_with_common(pair)
    direct = occurrence_certificate(residual[0], residual[1], n)
    swapped = occurrence_certificate(residual[1], residual[0], n)
    return min(direct, swapped)


def common_counts(common: Counter[Edge]) -> tuple[int, int]:
    loops = sum(value for (u, v), value in common.items() if u == v)
    nonloops = sum(value for (u, v), value in common.items() if u != v)
    return loops, nonloops


def direction_universe(n: int, degree: int) -> tuple[Direction, ...]:
    def weak(total: int, parts: int, prefix: tuple[int, ...] = ()) -> Iterable[tuple[int, ...]]:
        if parts == 1:
            yield prefix + (total,)
            return
        for first in range(total + 1):
            yield from weak(total - first, parts - 1, prefix + (first,))

    compositions = tuple(weak(degree, n))
    directions: set[Direction] = set()
    for left, right in combinations_with_replacement(compositions, 2):
        if left == right:
            continue
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = math.gcd(*(abs(value) for value in direction))
        directions.add(tuple(value // divisor for value in direction))
    return tuple(sorted(directions))


@dataclass
class Aggregate:
    transition: str
    source_n: int
    target_n: int
    degree: int
    denominator: int
    raw_count: int
    signed_classes: int
    directions: tuple[Direction, ...]
    matrix: np.ndarray
    row_labels: list[dict[str, object]]
    orbit_raw_counts: dict[str, int]
    overflow_bounds: list[int]
    reconciliation: dict[str, object]


def aggregate_rooted(
    dp,
    source: Sequence[Term],
    source_n: int,
    degree: int,
    transition: str,
    *,
    progress: bool = True,
) -> Aggregate:
    target_n = source_n + 1
    root = target_n - 1
    edges = tuple(combinations_with_replacement(range(target_n), 2))
    denominator = coefficient_lcm(source)
    source_integer = [int(term.coefficient * denominator) for term in source]
    expected_raw = len(source) * len(edges) ** 2
    buckets: dict[bytes, dict[str, object]] = {}
    common_loop = np.zeros(len(ORBIT_NAMES), dtype=np.int64)
    common_nonloop = np.zeros(len(ORBIT_NAMES), dtype=np.int64)
    orbit_raw = Counter()
    raw_count = 0
    for term_index, term in enumerate(source):
        coefficient = source_integer[term_index]
        for left_edge in edges:
            for right_edge in edges:
                orbit = rooted_orbit(left_edge, right_edge, root)
                orbit_index = ORBIT_INDEX[orbit]
                pair: Pair = (
                    tuple(sorted(term.pair[0] + (left_edge,))),
                    tuple(sorted(term.pair[1] + (right_edge,))),
                )
                residual, common = cancel_with_common(pair)
                key = signed_key(residual, target_n)
                bucket = buckets.setdefault(
                    key,
                    {"representative": residual, "weights": [0] * len(ORBIT_NAMES), "raw": 0},
                )
                weights = bucket["weights"]
                require(isinstance(weights, list), "bucket weight shape drift")
                weights[orbit_index] += coefficient
                bucket["raw"] = int(bucket["raw"]) + 1
                loops, nonloops = common_counts(common)
                common_loop[orbit_index] += coefficient * loops
                common_nonloop[orbit_index] += coefficient * nonloops
                orbit_raw[orbit] += 1
                raw_count += 1
        if progress:
            print(f"G0120_RAW_{transition} {term_index + 1}/{len(source)}", flush=True)
    require(raw_count == expected_raw, f"{transition}: raw count drift")
    require(sum(orbit_raw.values()) == expected_raw, f"{transition}: orbit count drift")
    require(tuple(sorted(orbit_raw)) == tuple(sorted(ORBIT_NAMES)), f"{transition}: missing orbit")
    require(sum(int(bucket["raw"]) for bucket in buckets.values()) == expected_raw, f"{transition}: fiber count drift")

    directions = direction_universe(target_n, degree + 1)
    row_by_direction = {direction: index for index, direction in enumerate(directions)}
    matrix = np.zeros((len(directions) + target_n, len(ORBIT_NAMES)), dtype=np.int64)
    semantic_bound = math.factorial(target_n) * (degree + 1)
    sum_abs_weights = [0] * len(ORBIT_NAMES)
    for bucket in buckets.values():
        weights = np.asarray(bucket["weights"], dtype=np.int64)
        for index, value in enumerate(weights):
            sum_abs_weights[index] += abs(int(value))
    loop_semantic = normal_form(dp, (((0, 0),), ((0, 0),)), target_n)
    nonloop_semantic = normal_form(dp, (((0, 1),), ((0, 1),)), target_n)
    require(not loop_semantic[1] and not nonloop_semantic[1], "common edge acquired hinge")
    overflow_bounds = []
    for orbit_index in range(len(ORBIT_NAMES)):
        bound = (
            sum_abs_weights[orbit_index] * semantic_bound
            + abs(int(common_loop[orbit_index])) * max(map(abs, loop_semantic[0]))
            + abs(int(common_nonloop[orbit_index])) * max(map(abs, nonloop_semantic[0]))
        )
        require(bound < INT64_SAFE_BOUND, f"{transition}: int64 bound exceeded for {ORBIT_NAMES[orbit_index]}")
        overflow_bounds.append(bound)

    for index, key in enumerate(sorted(buckets), start=1):
        bucket = buckets[key]
        weights = np.asarray(bucket["weights"], dtype=np.int64)
        if np.any(weights):
            semantic = normal_form(dp, bucket["representative"], target_n)  # type: ignore[arg-type]
            if semantic[1]:
                indices = np.asarray([row_by_direction[direction] for direction in semantic[1]], dtype=np.int64)
                values = np.asarray(list(semantic[1].values()), dtype=np.int64)
                matrix[np.ix_(indices, np.flatnonzero(weights))] += (
                    values[:, None] * weights[np.flatnonzero(weights)][None, :]
                )
            matrix[len(directions) :, :] += np.asarray(semantic[0], dtype=np.int64)[:, None] * weights[None, :]
        if progress and (index % 1000 == 0 or index == len(buckets)):
            print(f"G0120_SEMANTIC_{transition} {index}/{len(buckets)}", flush=True)
    matrix[len(directions) :, :] += np.asarray(loop_semantic[0], dtype=np.int64)[:, None] * common_loop[None, :]
    matrix[len(directions) :, :] += np.asarray(nonloop_semantic[0], dtype=np.int64)[:, None] * common_nonloop[None, :]
    row_labels = [
        {"kind": "hinge", "direction": list(direction)} for direction in directions
    ] + [{"kind": "linear", "rank": rank + 1} for rank in range(target_n)]
    return Aggregate(
        transition=transition,
        source_n=source_n,
        target_n=target_n,
        degree=degree,
        denominator=denominator,
        raw_count=raw_count,
        signed_classes=len(buckets),
        directions=directions,
        matrix=matrix,
        row_labels=row_labels,
        orbit_raw_counts={name: orbit_raw[name] for name in ORBIT_NAMES},
        overflow_bounds=overflow_bounds,
        reconciliation={
            "raw_descriptors": raw_count,
            "fiber_raw_sum": sum(int(bucket["raw"]) for bucket in buckets.values()),
            "orbit_raw_sum": sum(orbit_raw.values()),
            "common_loop_weight_sums": list(map(int, common_loop)),
            "common_nonloop_weight_sums": list(map(int, common_nonloop)),
        },
    )


def quotient_reconciliation_control(dp) -> dict[str, object]:
    """Cross-check signed-W aggregation against an unquotiented raw sum."""

    source_n = 4
    target_n = source_n + 1
    degree = 2
    source = [Term(Fraction(1), (((0, 1), (2, 3)), ((0, 2), (1, 3))))]
    aggregate = aggregate_rooted(
        dp,
        source,
        source_n,
        degree,
        "synthetic_quotient_control",
        progress=False,
    )
    direct = np.zeros_like(aggregate.matrix)
    row_by_direction = {direction: index for index, direction in enumerate(aggregate.directions)}
    edges = tuple(combinations_with_replacement(range(target_n), 2))
    for left_edge in edges:
        for right_edge in edges:
            orbit_index = ORBIT_INDEX[rooted_orbit(left_edge, right_edge, target_n - 1)]
            pair: Pair = (
                tuple(sorted(source[0].pair[0] + (left_edge,))),
                tuple(sorted(source[0].pair[1] + (right_edge,))),
            )
            linear, hinges = normal_form(dp, pair, target_n)
            for direction, value in hinges.items():
                direct[row_by_direction[direction], orbit_index] += value
            direct[len(aggregate.directions) :, orbit_index] += np.asarray(linear, dtype=np.int64)
    require(np.array_equal(direct, aggregate.matrix), "signed-W quotient/raw semantic mismatch")
    require(
        any(aggregate.reconciliation["common_loop_weight_sums"])
        and any(aggregate.reconciliation["common_nonloop_weight_sums"]),
        "synthetic quotient control did not exercise common padding",
    )
    return {
        "source_n": source_n,
        "target_n": target_n,
        "raw_descriptors": aggregate.raw_count,
        "signed_W_classes": aggregate.signed_classes,
        "matrix_sha256": array_sha(aggregate.matrix),
        "unquotiented_matrix_sha256": array_sha(direct),
        "common_loop_and_nonloop_padding_exercised": True,
        "exact_matrix_equality": True,
    }


def rank_exact(matrix: np.ndarray) -> int:
    return int(fmpz_mat([[int(value) for value in row] for row in matrix]).rank())


def independent_row_indices(matrix: np.ndarray, target_rank: int) -> list[int]:
    basis: dict[int, list[Fraction]] = {}
    selected = []
    for index, raw in enumerate(matrix):
        row = [Fraction(int(value)) for value in raw]
        for pivot in sorted(basis):
            if row[pivot]:
                factor = row[pivot]
                row = [x - factor * y for x, y in zip(row, basis[pivot], strict=True)]
        pivot = next((column for column, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        scale = row[pivot]
        basis[pivot] = [value / scale for value in row]
        selected.append(index)
        if len(selected) == target_rank:
            return selected
    raise GapError(f"could not find {target_rank} independent rows")


def joint_decision(first: Aggregate, second: Aggregate) -> dict[str, object]:
    matrix = np.concatenate((first.matrix, second.matrix), axis=0)
    target_first = np.zeros(first.matrix.shape[0], dtype=np.int64)
    target_first[-2] = -first.denominator
    target_first[-1] = first.denominator
    target_second = np.zeros(second.matrix.shape[0], dtype=np.int64)
    target_second[-2] = -second.denominator
    target_second[-1] = second.denominator
    target = np.concatenate((target_first, target_second))
    augmented = np.column_stack((matrix, target))
    rank = rank_exact(matrix)
    augmented_rank = rank_exact(augmented)
    require(augmented_rank in (rank, rank + 1), "augmented rank jump exceeded one")
    labels = [
        {"transition": first.transition, **label} for label in first.row_labels
    ] + [{"transition": second.transition, **label} for label in second.row_labels]
    output: dict[str, object] = {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank_over_Q": rank,
        "augmented_rank_over_Q": augmented_rank,
        "matrix_sha256": array_sha(matrix),
        "target_sha256": array_sha(target),
    }
    if augmented_rank > rank:
        selected = independent_row_indices(augmented, augmented_rank)
        small_matrix = matrix[selected]
        small_target = target[selected]
        small_augmented = augmented[selected]
        small_rank = rank_exact(small_matrix)
        small_augmented_rank = rank_exact(small_augmented)
        require(small_rank < small_augmented_rank, "small rows are not an inconsistency witness")
        witness_payload = {"matrix": small_matrix.tolist(), "target": small_target.tolist()}
        output.update(
            {
                "result": "EXACT_Q_NONMEMBERSHIP",
                "witness": {
                    "row_indices": selected,
                    "row_labels": [labels[index] for index in selected],
                    "coefficient_matrix": [[str(int(value)) for value in row] for row in small_matrix],
                    "target": [str(int(value)) for value in small_target],
                    "rank_over_Q": small_rank,
                    "augmented_rank_over_Q": small_augmented_rank,
                    "canonical_sha256": canonical_sha(witness_payload),
                },
            }
        )
        return output

    selected = independent_row_indices(matrix, rank)
    rows = [[Fraction(int(value)) for value in matrix[index]] + [Fraction(int(target[index]))] for index in selected]
    pivots: dict[int, list[Fraction]] = {}
    for row in rows:
        for pivot in sorted(pivots):
            if row[pivot]:
                factor = row[pivot]
                row = [x - factor * y for x, y in zip(row, pivots[pivot], strict=True)]
        pivot = next((column for column, value in enumerate(row[:-1]) if value), None)
        require(pivot is not None, "solution pivot vanished")
        scale = row[pivot]
        pivots[pivot] = [value / scale for value in row]
    for pivot in sorted(pivots, reverse=True):
        for earlier in sorted(value for value in pivots if value < pivot):
            if pivots[earlier][pivot]:
                factor = pivots[earlier][pivot]
                pivots[earlier] = [
                    x - factor * y for x, y in zip(pivots[earlier], pivots[pivot], strict=True)
                ]
    solution = [Fraction() for _ in ORBIT_NAMES]
    for pivot, row in pivots.items():
        solution[pivot] = row[-1]
    for row, rhs in zip(matrix, target, strict=True):
        require(
            sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, solution, strict=True))
            == int(rhs),
            "solution replay failed",
        )
    active = next((index for index, value in enumerate(solution) if value and np.any(matrix[:, index])), None)
    require(active is not None, "membership solution has no active nonzero weight")
    deleted = solution.copy()
    deleted[active] = Fraction()
    require(
        any(
            sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, deleted, strict=True))
            != int(rhs)
            for row, rhs in zip(matrix, target, strict=True)
        ),
        "deleted-weight mutant escaped",
    )
    output.update(
        {
            "result": "EXACT_Q_MEMBERSHIP",
            "solution": {name: str(value) for name, value in zip(ORBIT_NAMES, solution, strict=True)},
            "support": sum(bool(value) for value in solution),
            "free_variables_set_to_zero": len(ORBIT_NAMES) - rank,
            "deleted_first_active_weight_mutant_rejected": ORBIT_NAMES[active],
        }
    )
    return output


def self_test() -> dict[str, object]:
    require(len(ORBIT_NAMES) == len(set(ORBIT_NAMES)) == 17, "orbit schema drift")
    require(int(fmpz_mat([[1, 2], [2, 4]]).rank()) == 1, "flint rank control failed")
    dp = load_dp("g0120_selftest_dp")
    return {
        "flint_exact_rank": True,
        **classifier_controls(dp),
        "signed_W_quotient_reconciliation": quotient_reconciliation_control(dp),
    }


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = bind_inputs()
    dp = load_dp("g0120_bound_dp")
    controls = classifier_controls(dp)

    c5 = load_certificate(CERT5, 5, 2)
    c6 = load_certificate(CERT6, 6, 2)
    c7 = load_certificate(CERT7, 7, 3)
    c8 = load_certificate(CERT8, 8, 3)
    c9 = load_certificate(CERT9_395, 9, 4)
    c10 = load_certificate(CERT10, 10, 4)
    controls["public_certificate_replays"] = {
        "C5": replay_certificate(dp, c5, 5, 2, "public-C5"),
        "C6": replay_certificate(dp, c6, 6, 2, "public-C6"),
        "C7": replay_certificate(dp, c7, 7, 3, "public-C7"),
        "C8": replay_certificate(dp, c8, 8, 3, "public-C8"),
        "C9_G0115_395": replay_certificate(dp, c9, 9, 4, "G0115-395-C9"),
        "C10": replay_certificate(dp, c10, 10, 4, "public-C10"),
    }
    controls["source_gap_replays"] = {
        "Gap6": replay_gap(dp, c6, c5, 6, 2),
        "Gap8": replay_gap(dp, c8, c7, 8, 3),
        "Gap10": replay_gap(dp, c10, c9, 10, 4),
    }

    gap6 = gap_terms(c6, c5, 6)
    gap8 = gap_terms(c8, c7, 8)
    first = aggregate_rooted(dp, gap6, 6, 2, "Gap6_to_Gap7")
    second = aggregate_rooted(dp, gap8, 8, 3, "Gap8_to_Gap9")
    joint = joint_decision(first, second)

    transition_reports = {}
    for aggregate in (first, second):
        transition_reports[aggregate.transition] = {
            "source_n": aggregate.source_n,
            "target_n": aggregate.target_n,
            "source_degree": aggregate.degree,
            "target_degree": aggregate.degree + 1,
            "source_coefficient_lcm": aggregate.denominator,
            "raw_descriptors": aggregate.raw_count,
            "signed_W_classes": aggregate.signed_classes,
            "complete_hinge_rows": len(aggregate.directions),
            "linear_rows": aggregate.target_n,
            "orbit_raw_counts": aggregate.orbit_raw_counts,
            "matrix_sha256": array_sha(aggregate.matrix),
            "row_order_sha256": canonical_sha(aggregate.row_labels),
            "int64_absolute_bounds": aggregate.overflow_bounds,
            "reconciliation": aggregate.reconciliation,
        }
    result = {
        "schema": "g0120-rooted-reynolds-gap-v1",
        "result": joint["result"],
        "bindings": bindings | {"artifacts/math/G-0120/rooted_reynolds_gap.py": script_hash},
        "operator": {
            "semantic_object": "G_n=n*MAX_n-Ind_n(MAX_(n-1))=top_gap",
            "orbit_order": list(ORBIT_NAMES),
            "parameters": 17,
            "arity_dependence": "none",
            "aggregation": "raw_sum",
        },
        "controls": controls,
        "transitions": transition_reports,
        "joint_exact_Q_decision": joint,
        "MAX10_to_MAX11": {
            "evaluated": False,
            "reason": (
                "Preregistered stop: lower-transition joint system is inconsistent."
                if joint["result"] == "EXACT_Q_NONMEMBERSHIP"
                else "Shared lower law passed and is frozen; exact target replay must consume the serialized weights without refitting."
            ),
        },
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Exact decision only for the frozen 17-orbit arity-independent rooted raw-sum gap "
            "kernel. A null does not decide other Reynolds operators, gap representations, "
            "MAX10 lift-span membership, or MAX11 representability."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    write_exclusive(output, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    require(args.self_test ^ args.run, "choose exactly one of --self-test or --run")
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(args.output is not None, "--run requires --output")
    value = run(args.output.resolve())
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
