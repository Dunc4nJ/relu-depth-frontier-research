#!/usr/bin/env python3
"""Exact bounded experiments for bead max11-root-gmp.5.

This program has three deliberately separate jobs:

1. build the complete loopless simple-pair column systems for n <= 8 and
   compute exact-Q right kernels for n=7,8;
2. test a precise vertex-collapse identity with a loop-aware column kernel;
3. reproduce two Burnside orbit counts, with direct small-n orbit controls.

The local-move experiment is intentionally narrow.  A candidate move gives a
two-term relation e_i-e_j only when the two complete integer columns are equal.
It does not claim to enumerate higher-support local syzygies.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import itertools
import json
import math
import os
import statistics
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, permutations
from pathlib import Path
from typing import Iterable, Iterator, Sequence

import flint
from pynauty import Graph, certificate


Edge = tuple[int, int]
Template = tuple[tuple[Edge, ...], tuple[Edge, ...]]
Column = tuple[tuple[int, ...], dict[tuple[int, ...], int]]

ROOT = Path(__file__).resolve().parents[3]
REFERENCE_DIR = ROOT / "handoff" / "2026-09-02-amberbluff"
REFERENCE_FILES = (
    REFERENCE_DIR / "probes" / "loopless_probe_par.py",
    REFERENCE_DIR / "probes" / "count_simple_pairs.py",
    REFERENCE_DIR / "systems" / "loopless_system_n9.jsonl.gz",
    REFERENCE_DIR / "systems" / "loopless_system_n10.jsonl.gz",
)
PRIMES = (1_000_003, 1_000_033)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def write_jsonl_gzip(path: Path, rows: Iterable[object]) -> None:
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            for row in rows:
                payload = json.dumps(row, sort_keys=True, separators=(",", ":"))
                zipped.write(payload.encode("utf-8") + b"\n")


def ordered_pair_certificate(
    first: Sequence[Edge],
    second: Sequence[Edge],
    n: int,
    vertex_marks: Sequence[int] | None = None,
) -> bytes:
    """Canonical colored incidence graph; branch colors remain ordered."""
    first = tuple(sorted((min(a, b), max(a, b)) for a, b in first))
    second = tuple(sorted((min(a, b), max(a, b)) for a, b in second))
    total = n + len(first) + len(second)
    adjacency = {v: [] for v in range(total)}
    cursor = n
    for a, b in first:
        adjacency[cursor] = [a] if a == b else [a, b]
        cursor += 1
    for a, b in second:
        adjacency[cursor] = [a] if a == b else [a, b]
        cursor += 1

    marks = tuple(vertex_marks) if vertex_marks is not None else (0,) * n
    if len(marks) != n:
        raise ValueError("vertex mark length mismatch")
    coloring: list[set[int]] = []
    for mark in sorted(set(marks)):
        block = {v for v, value in enumerate(marks) if value == mark}
        if block:
            coloring.append(block)
    first_nodes = set(range(n, n + len(first)))
    second_nodes = set(range(n + len(first), total))
    if first_nodes:
        coloring.append(first_nodes)
    if second_nodes:
        coloring.append(second_nodes)
    graph = Graph(
        total,
        directed=False,
        adjacency_dict=adjacency,
        vertex_coloring=coloring,
    )
    return certificate(graph)


def template_key(first: Sequence[Edge], second: Sequence[Edge], n: int) -> bytes:
    """S_n x branch-swap canonical key."""
    return min(
        ordered_pair_certificate(first, second, n),
        ordered_pair_certificate(second, first, n),
    )


def enumerate_loopless_templates(n: int, k: int) -> list[Template]:
    edges = list(combinations(range(n), 2))
    graphs = list(combinations(edges, k))
    representatives: dict[bytes, tuple[Edge, ...]] = {}
    for graph in graphs:
        representatives.setdefault(template_key(graph, (), n), graph)
    seen: dict[bytes, Template] = {}
    for first in representatives.values():
        for second in graphs:
            seen.setdefault(template_key(first, second, n), (first, second))
    return list(seen.values())


def nonpositive_on_sorted_cone(direction: Sequence[int]) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for coefficient in direction[:-1]:
        prefix += coefficient
        if prefix < 0:
            return False
    return True


def column_dp(first: Sequence[Edge], second: Sequence[Edge], n: int) -> Column:
    """Exact symmetrized sorted-cone normal form, including diagonal loops.

    A loop (v,v) contributes x_v once.  A non-loop edge contributes the
    coordinate of its later endpoint in the current vertex ordering.
    """
    nbr_first = [[0] * n for _ in range(n)]
    nbr_second = [[0] * n for _ in range(n)]
    loops_first = [0] * n
    loops_second = [0] * n
    for a, b in first:
        if a == b:
            loops_first[a] += 1
        else:
            nbr_first[a][b] += 1
            nbr_first[b][a] += 1
    for a, b in second:
        if a == b:
            loops_second[a] += 1
        else:
            nbr_second[a][b] += 1
            nbr_second[b][a] += 1

    states: dict[tuple[int, tuple[tuple[int, int], ...]], int] = {(0, ()): 1}
    for _position in range(n):
        nxt: defaultdict[tuple[int, tuple[tuple[int, int], ...]], int] = defaultdict(int)
        for (mask, prefix), multiplicity in states.items():
            placed = [u for u in range(n) if mask >> u & 1]
            for vertex in range(n):
                if mask >> vertex & 1:
                    continue
                first_vote = loops_first[vertex]
                second_vote = loops_second[vertex]
                for old in placed:
                    first_vote += nbr_first[vertex][old]
                    second_vote += nbr_second[vertex][old]
                state = (
                    mask | (1 << vertex),
                    prefix + ((first_vote, second_vote),),
                )
                nxt[state] += multiplicity
        states = dict(nxt)

    linear = [0] * n
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    for (_mask, prefix), multiplicity in states.items():
        first_word = tuple(pair[0] for pair in prefix)
        second_word = tuple(pair[1] for pair in prefix)
        base, other = sorted((first_word, second_word))
        direction = tuple(right - left for left, right in zip(base, other))
        for index, coefficient in enumerate(base):
            linear[index] += multiplicity * coefficient
        if nonpositive_on_sorted_cone(direction):
            continue
        divisor = math.gcd(*direction)
        primitive = tuple(coefficient // divisor for coefficient in direction)
        hinges[primitive] += multiplicity * divisor
    return tuple(linear), dict(hinges)


def column_brute(first: Sequence[Edge], second: Sequence[Edge], n: int) -> Column:
    linear = [0] * n
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    for ordering in permutations(range(n)):
        position = [0] * n
        for rank, vertex in enumerate(ordering):
            position[vertex] = rank
        first_word = [0] * n
        second_word = [0] * n
        for a, b in first:
            first_word[max(position[a], position[b])] += 1
        for a, b in second:
            second_word[max(position[a], position[b])] += 1
        base, other = sorted((tuple(first_word), tuple(second_word)))
        direction = tuple(right - left for left, right in zip(base, other))
        for index, coefficient in enumerate(base):
            linear[index] += coefficient
        if nonpositive_on_sorted_cone(direction):
            continue
        divisor = math.gcd(*direction)
        primitive = tuple(coefficient // divisor for coefficient in direction)
        hinges[primitive] += divisor
    return tuple(linear), dict(hinges)


def column_worker(task: tuple[Template, int]) -> Column:
    (first, second), n = task
    return column_dp(first, second, n)


@dataclass
class System:
    n: int
    k: int
    templates: list[Template]
    columns: list[Column]
    rows: list[tuple[int, ...]]
    matrix: flint.fmpz_mat


def build_system(n: int, workers: int) -> System:
    k = (n - 1) // 2
    templates = enumerate_loopless_templates(n, k)
    if workers == 1:
        columns = [column_dp(first, second, n) for first, second in templates]
    else:
        from multiprocessing import Pool

        with Pool(workers) as pool:
            columns = pool.map(column_worker, [(template, n) for template in templates], chunksize=8)
    row_set = {direction for _linear, hinges in columns for direction in hinges}
    rows = sorted(row_set)
    row_index = {direction: index for index, direction in enumerate(rows)}
    values = [[0] * len(columns) for _ in range(len(rows) + n)]
    for column_index, (linear, hinges) in enumerate(columns):
        for direction, coefficient in hinges.items():
            values[row_index[direction]][column_index] = coefficient
        for index, coefficient in enumerate(linear):
            values[len(rows) + index][column_index] = coefficient
    return System(n, k, templates, columns, rows, flint.fmpz_mat(values))


def column_signature(column: Column) -> tuple[tuple[int, ...], tuple[tuple[tuple[int, ...], int], ...]]:
    linear, hinges = column
    return linear, tuple(sorted(hinges.items()))


class UnionFind:
    def __init__(self, size: int) -> None:
        self.parent = list(range(size))
        self.size = [1] * size

    def find(self, item: int) -> int:
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, left: int, right: int) -> None:
        left_root = self.find(left)
        right_root = self.find(right)
        if left_root == right_root:
            return
        if self.size[left_root] < self.size[right_root]:
            left_root, right_root = right_root, left_root
        self.parent[right_root] = left_root
        self.size[left_root] += self.size[right_root]

    def relation_rank(self) -> int:
        return sum(size - 1 for size in Counter(self.find(i) for i in range(len(self.parent))).values())


def common_cancellation_key(template: Template, n: int) -> tuple[int, bytes]:
    first, second = map(set, template)
    common = first & second
    first_only = tuple(sorted(first - common))
    second_only = tuple(sorted(second - common))
    return len(common), template_key(first_only, second_only, n)


def single_edge_deletion_keys(template: Template, n: int) -> set[bytes]:
    first, second = template
    keys: set[bytes] = set()
    for edge in first:
        reduced = tuple(candidate for candidate in first if candidate != edge)
        keys.add(ordered_pair_certificate(reduced, second, n))
    for edge in second:
        reduced = tuple(candidate for candidate in second if candidate != edge)
        keys.add(ordered_pair_certificate(reduced, first, n))
    return keys


def two_edge_rewire_keys(template: Template, n: int) -> set[bytes]:
    first, second = template
    keys: set[bytes] = set()
    for changed, fixed in ((first, second), (second, first)):
        for removed in combinations(changed, 2):
            removed_set = set(removed)
            reduced = tuple(edge for edge in changed if edge not in removed_set)
            marks = [0] * n
            for a, b in removed:
                marks[a] += 1
                marks[b] += 1
            keys.add(ordered_pair_certificate(reduced, fixed, n, marks))
    return keys


def pairs_from_buckets(buckets: dict[object, list[int]]) -> set[tuple[int, int]]:
    pairs: set[tuple[int, int]] = set()
    for indices in buckets.values():
        unique = sorted(set(indices))
        pairs.update(combinations(unique, 2))
    return pairs


def build_move_pair_sets(system: System) -> dict[str, set[tuple[int, int]]]:
    bucket_builders = {
        "common_edge_cancellation": lambda template: {common_cancellation_key(template, system.n)},
        "single_edge_replacement": lambda template: single_edge_deletion_keys(template, system.n),
        "degree_preserving_two_edge_rewire": lambda template: two_edge_rewire_keys(template, system.n),
    }
    result: dict[str, set[tuple[int, int]]] = {}
    for name, key_builder in bucket_builders.items():
        buckets: defaultdict[object, list[int]] = defaultdict(list)
        for index, template in enumerate(system.templates):
            for key in key_builder(template):
                buckets[key].append(index)
        result[name] = pairs_from_buckets(buckets)
    return result


def first_column_difference(left: Column, right: Column) -> dict[str, object]:
    if left[0] != right[0]:
        for index, (a, b) in enumerate(zip(left[0], right[0])):
            if a != b:
                return {"kind": "linear", "index": index, "left": a, "right": b}
    directions = sorted(set(left[1]) | set(right[1]))
    for direction in directions:
        a = left[1].get(direction, 0)
        b = right[1].get(direction, 0)
        if a != b:
            return {
                "kind": "hinge",
                "direction": list(direction),
                "left": a,
                "right": b,
            }
    raise AssertionError("columns reported different but no difference found")


def analyze_local_moves(system: System) -> dict[str, object]:
    signatures = [column_signature(column) for column in system.columns]
    signature_groups: defaultdict[object, list[int]] = defaultdict(list)
    for index, signature in enumerate(signatures):
        signature_groups[signature].append(index)
    duplicate_span_rank = sum(len(indices) - 1 for indices in signature_groups.values())

    proposed_by_move = build_move_pair_sets(system)
    move_pairs: dict[str, set[tuple[int, int]]] = {}
    move_results: dict[str, object] = {}
    combined = UnionFind(len(system.columns))

    for name, proposed in proposed_by_move.items():
        valid = {pair for pair in proposed if signatures[pair[0]] == signatures[pair[1]]}
        invalid = proposed - valid
        local_union = UnionFind(len(system.columns))
        for left, right in valid:
            local_union.union(left, right)
            combined.union(left, right)
        hostile = None
        if invalid:
            left, right = min(invalid)
            hostile = {
                "left_template_index": left,
                "right_template_index": right,
                "first_exact_difference": first_column_difference(
                    system.columns[left], system.columns[right]
                ),
            }
        move_pairs[name] = valid
        move_results[name] = {
            "proposed_template_pairs": len(proposed),
            "exact_two_term_relations": len(valid),
            "rejected_nonrelations": len(invalid),
            "exact_relation_span_rank": local_union.relation_rank(),
            "hostile_nonrelation_control": hostile,
        }

    common_invalid = move_results["common_edge_cancellation"]["rejected_nonrelations"]
    if common_invalid:
        raise AssertionError("common-edge cancellation produced a nonrelation")
    combined_rank = combined.relation_rank()
    if combined_rank > duplicate_span_rank:
        raise AssertionError("local two-term span exceeds all duplicate relations")
    return {
        "definition": (
            "orbit-invariant two-term relations e_i-e_j: common-edge cancellation uses the "
            "canonical signed core; one-edge replacement shares a canonical one-edge-deleted "
            "template; degree-preserving rewiring shares a canonical two-edge-deleted template "
            "with the removed vertex-degree vector"
        ),
        "moves": move_results,
        "combined_exact_relation_span_rank": combined_rank,
        "all_exact_two_term_relation_span_rank": duplicate_span_rank,
        "distinct_complete_integer_columns": len(signature_groups),
    }


def normalized_relation(entries: Iterable[tuple[int, int]]) -> tuple[tuple[int, int], ...]:
    combined: defaultdict[int, int] = defaultdict(int)
    for index, coefficient in entries:
        combined[index] += coefficient
    sparse = sorted((index, coefficient) for index, coefficient in combined.items() if coefficient)
    if not sparse:
        return ()
    divisor = 0
    for _index, coefficient in sparse:
        divisor = math.gcd(divisor, abs(coefficient))
    sparse = [(index, coefficient // divisor) for index, coefficient in sparse]
    if sparse[0][1] < 0:
        sparse = [(index, -coefficient) for index, coefficient in sparse]
    return tuple(sparse)


def relation_rank_and_replay(
    system: System, relations: Sequence[tuple[tuple[int, int], ...]]
) -> int:
    if not relations:
        return 0
    relation_matrix = flint.fmpz_mat(system.matrix.ncols(), len(relations))
    for column, relation in enumerate(relations):
        for row, coefficient in relation:
            relation_matrix[row, column] = coefficient
    product = system.matrix * relation_matrix
    if product != flint.fmpz_mat(product.nrows(), product.ncols()):
        raise AssertionError("candidate relation failed exact full-row replay")
    return relation_matrix.rank()


def outside_relation_span(
    system: System,
    candidate_relations: Sequence[tuple[tuple[int, int], ...]],
    full_kernel_basis: Sequence[Sequence[tuple[int, int]]],
) -> dict[str, object]:
    base = flint.fmpz_mat(system.matrix.ncols(), len(candidate_relations))
    for column, relation in enumerate(candidate_relations):
        for row, coefficient in relation:
            base[row, column] = coefficient
    base_rank = base.rank()
    for basis_index, sparse in enumerate(full_kernel_basis):
        augmented = flint.fmpz_mat(system.matrix.ncols(), len(candidate_relations) + 1)
        for row in range(base.nrows()):
            for column in range(base.ncols()):
                augmented[row, column] = base[row, column]
        for row, coefficient in sparse:
            augmented[row, len(candidate_relations)] = coefficient
        augmented_rank = augmented.rank()
        if augmented_rank > base_rank:
            return {
                "basis_index": basis_index,
                "denominator": 1,
                "entries": [[row, str(coefficient)] for row, coefficient in sparse],
                "support": len(sparse),
                "candidate_span_rank": base_rank,
                "augmented_rank_with_counterexample": augmented_rank,
                "full_row_kernel_replay_passed": True,
            }
    raise AssertionError("candidate relations unexpectedly span the full kernel")


def pair_is_move(pair_set: set[tuple[int, int]], left: int, right: int) -> bool:
    return left != right and (min(left, right), max(left, right)) in pair_set


def square_move_classes(
    left_pair: tuple[int, int],
    right_pair: tuple[int, int],
    proposed_by_move: dict[str, set[tuple[int, int]]],
) -> list[str]:
    left, right = left_pair
    other_left, other_right = right_pair
    classes: list[str] = []
    for name, pair_set in proposed_by_move.items():
        straight = pair_is_move(pair_set, left, other_left) and pair_is_move(
            pair_set, right, other_right
        )
        crossed = pair_is_move(pair_set, left, other_right) and pair_is_move(
            pair_set, right, other_left
        )
        if straight or crossed:
            classes.append(f"{name}_square")
    return classes


def analyze_quadratic_relations(
    system: System,
    output_dir: Path,
    full_kernel_basis: Sequence[Sequence[tuple[int, int]]],
) -> dict[str, object]:
    """Enumerate exact c_i+c_j=c_k+c_l relations on distinct columns.

    Modular projections are a lossless prefilter: exact equality over Z implies
    equality in every projection.  Candidate collisions are then compared on
    every integer row before they are admitted.
    """
    signature_groups: defaultdict[object, list[int]] = defaultdict(list)
    for index, column in enumerate(system.columns):
        signature_groups[column_signature(column)].append(index)
    representatives = sorted(indices[0] for indices in signature_groups.values())

    duplicate_basis: list[tuple[tuple[int, int], ...]] = []
    for indices in signature_groups.values():
        anchor = indices[0]
        for other in indices[1:]:
            duplicate_basis.append(((anchor, 1), (other, -1)))

    projection_weights: list[tuple[int, list[int]]] = []
    for prime in PRIMES:
        for base in (37, 101):
            weights = [pow(base, row + 1, prime) for row in range(system.matrix.nrows())]
            projection_weights.append((prime, weights))
    fingerprints: dict[int, tuple[int, ...]] = {}
    for column in representatives:
        coordinates = []
        for prime, weights in projection_weights:
            value = sum(
                int(system.matrix[row, column]) * weights[row]
                for row in range(system.matrix.nrows())
            ) % prime
            coordinates.append(value)
        fingerprints[column] = tuple(coordinates)

    modular_buckets: defaultdict[tuple[int, ...], list[tuple[int, int]]] = defaultdict(list)
    for offset, left in enumerate(representatives):
        for right in representatives[offset:]:
            fingerprint = tuple(
                (a + b) % projection_weights[index][0]
                for index, (a, b) in enumerate(zip(fingerprints[left], fingerprints[right]))
            )
            modular_buckets[fingerprint].append((left, right))

    proposed_by_move = build_move_pair_sets(system)
    exact_relations: dict[tuple[tuple[int, int], ...], dict[str, object]] = {}
    exact_pair_sum_classes = 0
    modular_collision_pairs = 0
    for bucket in modular_buckets.values():
        if len(bucket) < 2:
            continue
        modular_collision_pairs += len(bucket)
        exact_buckets: defaultdict[tuple[int, ...], list[tuple[int, int]]] = defaultdict(list)
        for left, right in bucket:
            exact_sum = tuple(
                int(system.matrix[row, left]) + int(system.matrix[row, right])
                for row in range(system.matrix.nrows())
            )
            exact_buckets[exact_sum].append((left, right))
        for pair_sum_class in exact_buckets.values():
            if len(pair_sum_class) < 2:
                continue
            exact_pair_sum_classes += 1
            anchor = pair_sum_class[0]
            for other in pair_sum_class[1:]:
                relation = normalized_relation(
                    ((anchor[0], 1), (anchor[1], 1), (other[0], -1), (other[1], -1))
                )
                if not relation:
                    continue
                classes = square_move_classes(anchor, other, proposed_by_move)
                exact_relations.setdefault(
                    relation,
                    {
                        "entries": [[index, coefficient] for index, coefficient in relation],
                        "left_pair": list(anchor),
                        "right_pair": list(other),
                        "graph_local_classes": classes,
                    },
                )

    all_quadratic = sorted(exact_relations)
    graph_local_quadratic = sorted(
        relation
        for relation, record in exact_relations.items()
        if record["graph_local_classes"]
    )
    duplicate_rank = relation_rank_and_replay(system, duplicate_basis)
    quadratic_rank = relation_rank_and_replay(system, all_quadratic)
    graph_local_quadratic_rank = relation_rank_and_replay(system, graph_local_quadratic)
    all_combined = sorted(set(duplicate_basis) | set(all_quadratic))
    graph_local_combined = sorted(set(duplicate_basis) | set(graph_local_quadratic))
    combined_rank = relation_rank_and_replay(system, all_combined)
    graph_local_combined_rank = relation_rank_and_replay(system, graph_local_combined)
    full_nullity = system.matrix.ncols() - system.matrix.rank()

    named_outside = outside_relation_span(system, graph_local_combined, full_kernel_basis)
    named_outside_path = output_dir / f"named_local_move_counterexample_n{system.n}.json"
    write_json(
        named_outside_path,
        {
            "n": system.n,
            "candidate_family": (
                "common-cancellation equal-column relations plus exact quadratic squares "
                "whose opposite edits are one-edge replacements or degree-preserving rewires"
            ),
            **named_outside,
        },
    )
    quadratic_outside = outside_relation_span(system, all_combined, full_kernel_basis)
    quadratic_outside_path = output_dir / f"quadratic_generation_counterexample_n{system.n}.json"
    write_json(
        quadratic_outside_path,
        {
            "n": system.n,
            "candidate_family": (
                "all equal-column differences plus every exact integer pair-sum collision "
                "among distinct complete column classes"
            ),
            **quadratic_outside,
        },
    )

    mutation_rejected = False
    if all_quadratic:
        mutated = list(all_quadratic[0])
        first_index, first_coefficient = mutated[0]
        mutated[0] = (first_index, first_coefficient + 1)
        candidate = flint.fmpz_mat(system.matrix.ncols(), 1)
        for index, coefficient in mutated:
            candidate[index, 0] = coefficient
        mutation_rejected = system.matrix * candidate != flint.fmpz_mat(system.matrix.nrows(), 1)
        if not mutation_rejected:
            raise AssertionError("quadratic-relation mutation escaped full-row check")

    relations_path = output_dir / f"quadratic_relations_n{system.n}.jsonl.gz"
    write_jsonl_gzip(
        relations_path,
        (
            {"relation_index": index, **exact_relations[relation]}
            for index, relation in enumerate(all_quadratic)
        ),
    )
    class_counts = Counter(
        move_class
        for record in exact_relations.values()
        for move_class in record["graph_local_classes"]
    )
    return {
        "definition": (
            "quadratic relation c_i+c_j-c_k-c_l=0 between distinct complete column "
            "classes; a named graph-local square requires both opposite template edits to "
            "share the corresponding orbit-invariant deletion signature"
        ),
        "distinct_complete_columns": len(representatives),
        "unordered_pair_sums_denominator": len(representatives) * (len(representatives) + 1) // 2,
        "modular_prefilter": {
            "primes": list(PRIMES),
            "projections_per_prime": 2,
            "candidate_pairs_in_collision_buckets": modular_collision_pairs,
            "no_false_negative_reason": "exact integer pair-sum equality implies every modular projection equality",
        },
        "exact_pair_sum_classes_with_collision": exact_pair_sum_classes,
        "exact_quadratic_relations": len(all_quadratic),
        "exact_quadratic_relation_span_rank": quadratic_rank,
        "graph_local_quadratic_relations": len(graph_local_quadratic),
        "graph_local_class_counts_nonexclusive": dict(sorted(class_counts.items())),
        "graph_local_quadratic_relation_span_rank": graph_local_quadratic_rank,
        "duplicate_relation_span_rank": duplicate_rank,
        "all_quadratic_plus_duplicates_span_rank": combined_rank,
        "graph_local_quadratic_plus_duplicates_span_rank": graph_local_combined_rank,
        "full_kernel_nullity": full_nullity,
        "all_quadratic_generate_full_kernel": combined_rank == full_nullity,
        "named_graph_local_squares_generate_full_kernel": graph_local_combined_rank == full_nullity,
        "outside_named_graph_local_span_counterexample": {
            "path": str(named_outside_path.relative_to(ROOT)),
            "sha256": sha256_file(named_outside_path),
            "bytes": named_outside_path.stat().st_size,
            "basis_index": named_outside["basis_index"],
            "support": named_outside["support"],
            "candidate_span_rank": named_outside["candidate_span_rank"],
            "augmented_rank": named_outside["augmented_rank_with_counterexample"],
        },
        "outside_all_quadratic_span_counterexample": {
            "path": str(quadratic_outside_path.relative_to(ROOT)),
            "sha256": sha256_file(quadratic_outside_path),
            "bytes": quadratic_outside_path.stat().st_size,
            "basis_index": quadratic_outside["basis_index"],
            "support": quadratic_outside["support"],
            "candidate_span_rank": quadratic_outside["candidate_span_rank"],
            "augmented_rank": quadratic_outside["augmented_rank_with_counterexample"],
        },
        "equality_destroying_plus_one_mutation_rejected": mutation_rejected,
        "artifact": {
            "path": str(relations_path.relative_to(ROOT)),
            "sha256": sha256_file(relations_path),
            "bytes": relations_path.stat().st_size,
        },
    }


def outside_two_term_span_counterexample(
    system: System, sparse_basis: Sequence[Sequence[tuple[int, int]]]
) -> dict[str, object]:
    """Return a kernel vector excluded by every equal-column difference span.

    For each distinct complete column value, summing coefficients over its
    duplicate class defines a quotient map.  Every two-term relation between
    equal columns maps to zero.  A kernel vector with nonzero quotient image is
    therefore outside the span of all such relations, hence outside the three
    tested local-move subfamilies.
    """
    signatures = [column_signature(column) for column in system.columns]
    group_by_signature: dict[object, int] = {}
    groups: list[int] = []
    for signature in signatures:
        if signature not in group_by_signature:
            group_by_signature[signature] = len(group_by_signature)
        groups.append(group_by_signature[signature])
    for basis_index, sparse in enumerate(sparse_basis):
        quotient: defaultdict[int, int] = defaultdict(int)
        for column, coefficient in sparse:
            quotient[groups[column]] += coefficient
        nonzero_quotient = sorted(
            (group, coefficient)
            for group, coefficient in quotient.items()
            if coefficient
        )
        if nonzero_quotient:
            return {
                "basis_index": basis_index,
                "denominator": 1,
                "entries": [[column, str(coefficient)] for column, coefficient in sparse],
                "support": len(sparse),
                "nonzero_duplicate_class_sums": [
                    [group, str(coefficient)] for group, coefficient in nonzero_quotient
                ],
                "quotient_test": (
                    "nonzero class sums prove this exact kernel vector is outside the span "
                    "of all e_i-e_j relations between equal complete columns"
                ),
            }
    raise AssertionError("full kernel unexpectedly lies in equal-column difference span")


def matrix_to_nested_ints(matrix: flint.fmpz_mat) -> list[list[int]]:
    return [
        [int(matrix[row, column]) for column in range(matrix.ncols())]
        for row in range(matrix.nrows())
    ]


def modular_rank(matrix: flint.fmpz_mat, prime: int) -> int:
    return flint.nmod_mat(matrix_to_nested_ints(matrix), prime).rank()


def exact_target_solution(system: System) -> tuple[list[flint.fmpq], dict[str, object]]:
    rows = matrix_to_nested_ints(system.matrix)
    target = [0] * system.matrix.nrows()
    target[len(system.rows) + system.n - 1] = 1
    augmented = flint.fmpq_mat([row + [rhs] for row, rhs in zip(rows, target)])
    reduced, augmented_rank = augmented.rref()
    rank = system.matrix.rank()
    if augmented_rank != rank:
        raise AssertionError("known MAX target is not in exact-Q column span")
    solution = [flint.fmpq(0) for _ in range(system.matrix.ncols())]
    pivot_count = 0
    for row in range(reduced.nrows()):
        pivot = None
        for column in range(system.matrix.ncols()):
            if reduced[row, column] != 0:
                pivot = column
                break
        if pivot is None:
            if reduced[row, system.matrix.ncols()] != 0:
                raise AssertionError("inconsistent exact-Q target row")
            continue
        solution[pivot] = reduced[row, system.matrix.ncols()]
        pivot_count += 1
    if pivot_count != rank:
        raise AssertionError("unexpected exact-Q pivot count")
    matrix_q = flint.fmpq_mat(rows)
    vector_q = flint.fmpq_mat([[value] for value in solution])
    target_q = flint.fmpq_mat([[value] for value in target])
    if matrix_q * vector_q != target_q:
        raise AssertionError("exact-Q target witness failed full-row replay")

    nonzero = [index for index, value in enumerate(solution) if value != 0]
    if not nonzero:
        raise AssertionError("zero vector cannot represent MAX target")
    mutated = list(solution)
    mutated[nonzero[0]] += 1
    mutation_vector = flint.fmpq_mat([[value] for value in mutated])
    mutation_rejected = matrix_q * mutation_vector != target_q
    if not mutation_rejected:
        raise AssertionError("equality-destroying target-witness mutation passed")

    denominators = [int(value.denom()) for value in solution if value != 0]
    denominator_lcm = 1
    for denominator in denominators:
        denominator_lcm = math.lcm(denominator_lcm, denominator)
    return solution, {
        "rank_augmented": augmented_rank,
        "nonzero_coefficients": len(nonzero),
        "coefficient_count_denominator": len(solution),
        "common_denominator": denominator_lcm,
        "full_row_replay_passed": True,
        "rows_replayed": system.matrix.nrows(),
        "equality_destroying_plus_one_mutation_rejected": mutation_rejected,
        "mutated_coefficient_index": nonzero[0],
    }


def exact_right_kernel(system: System) -> tuple[list[list[tuple[int, int]]], dict[str, object]]:
    rank = system.matrix.rank()
    raw_kernel, nullity = system.matrix.nullspace()
    expected_nullity = system.matrix.ncols() - rank
    if nullity != expected_nullity:
        raise AssertionError("rank-nullity mismatch")
    basis = flint.fmpz_mat(system.matrix.ncols(), nullity)
    sparse_basis: list[list[tuple[int, int]]] = []
    supports: list[int] = []
    max_bits = 0
    for basis_index in range(nullity):
        coefficients = [int(raw_kernel[row, basis_index]) for row in range(raw_kernel.nrows())]
        divisor = 0
        for coefficient in coefficients:
            divisor = math.gcd(divisor, abs(coefficient))
        if divisor == 0:
            raise AssertionError("zero vector returned in kernel basis")
        coefficients = [coefficient // divisor for coefficient in coefficients]
        first_nonzero = next(coefficient for coefficient in coefficients if coefficient)
        if first_nonzero < 0:
            coefficients = [-coefficient for coefficient in coefficients]
        sparse = [(index, coefficient) for index, coefficient in enumerate(coefficients) if coefficient]
        sparse_basis.append(sparse)
        supports.append(len(sparse))
        for row, coefficient in enumerate(coefficients):
            basis[row, basis_index] = coefficient
            if coefficient:
                max_bits = max(max_bits, abs(coefficient).bit_length())
    product = system.matrix * basis
    zero = flint.fmpz_mat(product.nrows(), product.ncols())
    if product != zero:
        raise AssertionError("exact integer kernel replay failed")

    mutated = flint.fmpz_mat(system.matrix.ncols(), 1)
    for row, coefficient in sparse_basis[0]:
        mutated[row, 0] = coefficient
    mutation_index = next(
        column
        for column in range(system.matrix.ncols())
        if any(system.matrix[row, column] != 0 for row in range(system.matrix.nrows()))
    )
    mutated[mutation_index, 0] += 1
    mutation_rejected = system.matrix * mutated != flint.fmpz_mat(system.matrix.nrows(), 1)
    if not mutation_rejected:
        raise AssertionError("equality-destroying kernel mutation passed")

    return sparse_basis, {
        "rank_over_Q": rank,
        "nullity_over_Q": nullity,
        "basis_vectors": len(sparse_basis),
        "ambient_columns": system.matrix.ncols(),
        "rows": system.matrix.nrows(),
        "hinge_rows": len(system.rows),
        "linear_rows": system.n,
        "basis_denominator": 1,
        "support_min": min(supports),
        "support_median": statistics.median(supports),
        "support_max": max(supports),
        "max_abs_coefficient_bits": max_bits,
        "full_row_kernel_replay_passed": True,
        "equality_destroying_plus_one_mutation_rejected": mutation_rejected,
        "mutated_coefficient_index": mutation_index,
        "modular_ranks": {str(prime): modular_rank(system.matrix, prime) for prime in PRIMES},
    }


def template_json(template: Template) -> dict[str, object]:
    first, second = template
    return {"A": [list(edge) for edge in first], "B": [list(edge) for edge in second]}


def run_kernel_experiments(
    systems: dict[int, System], output_dir: Path
) -> dict[str, object]:
    expected = {
        7: {"columns": 357, "rank": 90, "nullity": 267},
        8: {"columns": 430, "rank": 140, "nullity": 290},
    }
    results: dict[str, object] = {}
    for n in (7, 8):
        system = systems[n]
        basis, kernel_summary = exact_right_kernel(system)
        solution, witness_summary = exact_target_solution(system)
        if system.matrix.ncols() != expected[n]["columns"]:
            raise AssertionError(f"n={n} known template count changed")
        if kernel_summary["rank_over_Q"] != expected[n]["rank"]:
            raise AssertionError(f"n={n} known exact rank changed")
        if kernel_summary["nullity_over_Q"] != expected[n]["nullity"]:
            raise AssertionError(f"n={n} known nullity changed")

        basis_path = output_dir / f"right_kernel_n{n}.jsonl.gz"
        write_jsonl_gzip(
            basis_path,
            (
                {
                    "basis_index": index,
                    "denominator": 1,
                    "entries": [[column, str(coefficient)] for column, coefficient in sparse],
                }
                for index, sparse in enumerate(basis)
            ),
        )
        templates_path = output_dir / f"templates_n{n}.json.gz"
        write_jsonl_gzip(
            templates_path,
            (
                {"column_index": index, **template_json(template)}
                for index, template in enumerate(system.templates)
            ),
        )
        witness_path = output_dir / f"max_target_witness_n{n}.json"
        write_json(
            witness_path,
            {
                "n": n,
                "coefficients": [
                    {"column_index": index, "coefficient": str(value)}
                    for index, value in enumerate(solution)
                    if value != 0
                ],
                "verification": witness_summary,
            },
        )
        local_moves = analyze_local_moves(system)
        quadratic_relations = analyze_quadratic_relations(system, output_dir, basis)
        counterexample = outside_two_term_span_counterexample(system, basis)
        counterexample_path = output_dir / f"local_move_counterexample_n{n}.json"
        write_json(
            counterexample_path,
            {
                "n": n,
                "full_kernel_replay_passed": True,
                **counterexample,
            },
        )
        local_moves["full_kernel_nullity"] = kernel_summary["nullity_over_Q"]
        local_moves["dimension_not_generated"] = (
            kernel_summary["nullity_over_Q"]
            - local_moves["combined_exact_relation_span_rank"]
        )
        local_moves["outside_span_counterexample"] = {
            "path": str(counterexample_path.relative_to(ROOT)),
            "sha256": sha256_file(counterexample_path),
            "bytes": counterexample_path.stat().st_size,
            "basis_index": counterexample["basis_index"],
            "support": counterexample["support"],
        }
        results[str(n)] = {
            "kernel": kernel_summary,
            "known_answer_target": witness_summary,
            "local_moves": local_moves,
            "quadratic_relations": quadratic_relations,
            "artifacts": {
                "right_kernel": {
                    "path": str(basis_path.relative_to(ROOT)),
                    "sha256": sha256_file(basis_path),
                    "bytes": basis_path.stat().st_size,
                },
                "templates": {
                    "path": str(templates_path.relative_to(ROOT)),
                    "sha256": sha256_file(templates_path),
                    "bytes": templates_path.stat().st_size,
                },
                "known_answer_witness": {
                    "path": str(witness_path.relative_to(ROOT)),
                    "sha256": sha256_file(witness_path),
                    "bytes": witness_path.stat().st_size,
                },
            },
        }
    return results


def collapse_template(template: Template, removed: int, n: int) -> Template:
    relabel = {}
    cursor = 0
    for vertex in range(n):
        if vertex == removed:
            continue
        relabel[vertex] = cursor
        cursor += 1

    def collapse_branch(branch: Sequence[Edge]) -> tuple[Edge, ...]:
        collapsed: list[Edge] = []
        for a, b in branch:
            if a == removed or b == removed:
                other = b if a == removed else a
                image = relabel[other]
                collapsed.append((image, image))
            else:
                left, right = relabel[a], relabel[b]
                collapsed.append((min(left, right), max(left, right)))
        return tuple(sorted(collapsed))

    return collapse_branch(template[0]), collapse_branch(template[1])


def add_column(total: Column, addition: Column, leading_zero: bool) -> Column:
    total_linear, total_hinges = total
    add_linear, add_hinges = addition
    if leading_zero:
        add_linear = (0,) + add_linear
        add_hinges = {(0,) + direction: value for direction, value in add_hinges.items()}
    if len(total_linear) != len(add_linear):
        raise ValueError("column dimension mismatch")
    linear = tuple(left + right for left, right in zip(total_linear, add_linear))
    hinges = dict(total_hinges)
    for direction, coefficient in add_hinges.items():
        hinges[direction] = hinges.get(direction, 0) + coefficient
        if hinges[direction] == 0:
            del hinges[direction]
    return linear, hinges


def zero_column(n: int) -> Column:
    return (0,) * n, {}


def run_collapse_experiment(systems: dict[int, System]) -> dict[str, object]:
    by_n: dict[str, object] = {}
    total_checks = 0
    collapsed_cache: dict[tuple[int, bytes], Column] = {}
    hostile_control = None
    brute_controls: list[dict[str, object]] = []

    for n in range(5, 9):
        system = systems[n]
        checked = 0
        for template_index, (template, left_column) in enumerate(
            zip(system.templates, system.columns)
        ):
            collapsed_columns: list[Column] = []
            total = zero_column(n)
            for removed in range(n):
                collapsed = collapse_template(template, removed, n)
                key = (n - 1, template_key(*collapsed, n - 1))
                if key not in collapsed_cache:
                    collapsed_cache[key] = column_dp(*collapsed, n - 1)
                term = collapsed_cache[key]
                collapsed_columns.append(term)
                total = add_column(total, term, leading_zero=True)
            if column_signature(total) != column_signature(left_column):
                raise AssertionError(
                    f"vertex-collapse identity failed at n={n}, template={template_index}"
                )
            checked += 1
            total_checks += 1

            if hostile_control is None:
                corrupted = zero_column(n)
                for term in collapsed_columns[1:]:
                    corrupted = add_column(corrupted, term, leading_zero=True)
                if column_signature(corrupted) != column_signature(left_column):
                    hostile_control = {
                        "mutation": "drop the removed-vertex v=0 summand",
                        "n": n,
                        "template_index": template_index,
                        "rejected": True,
                        "first_exact_difference": first_column_difference(left_column, corrupted),
                    }
        by_n[str(n)] = {
            "identities_passed": checked,
            "templates_denominator": len(system.templates),
        }

        sample_indices = sorted({0, len(system.templates) // 2, len(system.templates) - 1})
        for template_index in sample_indices:
            template = system.templates[template_index]
            dp = system.columns[template_index]
            brute = column_brute(*template, n)
            if column_signature(dp) != column_signature(brute):
                raise AssertionError("loopless DP/brute control mismatch")
            collapsed = collapse_template(template, 0, n)
            dp_loop = column_dp(*collapsed, n - 1)
            brute_loop = column_brute(*collapsed, n - 1)
            if column_signature(dp_loop) != column_signature(brute_loop):
                raise AssertionError("loop-aware DP/brute control mismatch")
            brute_controls.append(
                {
                    "n": n,
                    "template_index": template_index,
                    "loopless_dp_equals_brute": True,
                    "collapsed_loop_aware_dp_equals_brute": True,
                }
            )

    if hostile_control is None:
        raise AssertionError("failed to instantiate collapse hostile control")
    return {
        "statement": (
            "For a loopless n-vertex template (A,B), on x_0<=...<=x_(n-1), "
            "F_n(A,B)(x) equals the sum over original vertices v of "
            "F_(n-1)(collapse_v(A),collapse_v(B))(x_1,...,x_(n-1)); each edge "
            "incident to v becomes one diagonal loop at its other endpoint."
        ),
        "proof_partition": (
            "Partition the n! relabelings in F_n by the original vertex sent to sorted "
            "position 0.  Each part has (n-1)! relabelings.  Since x_0 is minimal, an "
            "incident edge max(x_0,x_j) contributes x_j, exactly the collapsed loop."
        ),
        "by_n": by_n,
        "total_identities_passed": total_checks,
        "total_identities_denominator": total_checks,
        "distinct_collapsed_columns_computed": len(collapsed_cache),
        "dp_vs_brute_controls": {
            "passed": len(brute_controls),
            "denominator": len(brute_controls),
            "cases": brute_controls,
        },
        "hostile_control": hostile_control,
    }


def partitions(n: int, minimum: int = 1) -> Iterator[tuple[int, ...]]:
    yield (n,)
    for first in range(minimum, n // 2 + 1):
        for suffix in partitions(n - first, first):
            yield (first,) + suffix


def cycle_type_count(partition: Sequence[int], n: int) -> int:
    counts = Counter(partition)
    denominator = 1
    for length, multiplicity in counts.items():
        denominator *= length**multiplicity * math.factorial(multiplicity)
    return math.factorial(n) // denominator


def edge_orbit_lengths(partition: Sequence[int], loops: bool) -> list[int]:
    cycles: list[list[int]] = []
    cursor = 0
    for length in partition:
        cycles.append(list(range(cursor, cursor + length)))
        cursor += length
    permutation = [0] * cursor
    for cycle in cycles:
        for index, vertex in enumerate(cycle):
            permutation[vertex] = cycle[(index + 1) % len(cycle)]
    pairs = [
        (left, right)
        for left in range(cursor)
        for right in range(left, cursor)
        if loops or left != right
    ]
    seen: set[Edge] = set()
    lengths: list[int] = []
    for pair in pairs:
        if pair in seen:
            continue
        current = pair
        length = 0
        while current not in seen:
            seen.add(current)
            length += 1
            left, right = permutation[current[0]], permutation[current[1]]
            current = min(left, right), max(left, right)
        lengths.append(length)
    return lengths


def polynomial_multiply(left: list[int], right: list[int], degree: int) -> list[int]:
    result = [0] * (degree + 1)
    for i, first in enumerate(left):
        if not first:
            continue
        for j, second in enumerate(right):
            if i + j > degree:
                break
            result[i + j] += first * second
    return result


def fixed_edge_sets(orbit_lengths: Sequence[int], k: int) -> int:
    polynomial = [1] + [0] * k
    for length in orbit_lengths:
        factor = [0] * (k + 1)
        factor[0] = 1
        if length <= k:
            factor[length] = 1
        polynomial = polynomial_multiply(polynomial, factor, k)
    return polynomial[k]


def squared_cycle_type(partition: Sequence[int]) -> tuple[int, ...]:
    result: list[int] = []
    for length in partition:
        if length % 2:
            result.append(length)
        else:
            result.extend((length // 2, length // 2))
    return tuple(sorted(result, reverse=True))


def burnside_simple_pair_count(n: int, k: int) -> dict[str, int]:
    fixed_both_numerator = 0
    swapped_numerator = 0
    for partition in partitions(n):
        permutations_of_type = cycle_type_count(partition, n)
        fixed = fixed_edge_sets(edge_orbit_lengths(partition, loops=False), k)
        fixed_both_numerator += permutations_of_type * fixed * fixed
        fixed_squared = fixed_edge_sets(
            edge_orbit_lengths(squared_cycle_type(partition), loops=False), k
        )
        swapped_numerator += permutations_of_type * fixed_squared
    numerator = fixed_both_numerator + swapped_numerator
    denominator = 2 * math.factorial(n)
    if numerator % denominator:
        raise AssertionError("nonintegral Burnside quotient")
    return {
        "orbits": numerator // denominator,
        "burnside_numerator": numerator,
        "group_order_denominator": denominator,
        "fixed_without_swap_numerator": fixed_both_numerator,
        "swap_coset_numerator": swapped_numerator,
    }


def brute_simple_pair_orbits(n: int, k: int) -> int:
    graphs = list(combinations(combinations(range(n), 2), k))
    keys = {
        template_key(first, second, n)
        for first in graphs
        for second in graphs
    }
    return len(keys)


def run_burnside_experiment() -> dict[str, object]:
    small_controls: dict[str, object] = {}
    for n, k, expected in ((5, 2, 19), (6, 2, 25)):
        burnside = burnside_simple_pair_count(n, k)
        brute = brute_simple_pair_orbits(n, k)
        if burnside["orbits"] != brute or brute != expected:
            raise AssertionError("Burnside/direct-orbit known-answer mismatch")
        wrong_without_swap = burnside["fixed_without_swap_numerator"]
        denominator = burnside["group_order_denominator"]
        hostile_detected = wrong_without_swap != expected * denominator
        if not hostile_detected:
            raise AssertionError("omitting branch-swap coset escaped control")
        small_controls[f"n{n}_k{k}"] = {
            "burnside_orbits": burnside["orbits"],
            "direct_pynauty_orbits": brute,
            "expected_orbits": expected,
            "complete_graph_pair_denominator": math.comb(math.comb(n, 2), k) ** 2,
            "omitted_swap_coset_mutation_rejected": hostile_detected,
        }
    return {
        "requested": {
            "n12_k5": burnside_simple_pair_count(12, 5),
            "n11_k6": burnside_simple_pair_count(11, 6),
        },
        "known_answer_controls": small_controls,
    }


def input_receipts() -> dict[str, object]:
    receipts: dict[str, object] = {}
    for path in REFERENCE_FILES:
        receipts[str(path.relative_to(ROOT))] = {
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
    script = Path(__file__).resolve()
    receipts[str(script.relative_to(ROOT))] = {
        "bytes": script.stat().st_size,
        "sha256": sha256_file(script),
    }
    return receipts


def inspect_saved_n9_system() -> dict[str, object]:
    """Inventory the saved n=9 system without pretending to compute its Q-rank."""
    path = REFERENCE_DIR / "systems" / "loopless_system_n9.jsonl.gz"
    columns = 0
    nonzeros = 0
    hinge_rows: set[str] = set()
    linear_widths: set[int] = set()
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            columns += 1
            hinges = row["h"]
            nonzeros += len(hinges) + sum(value != 0 for value in row["lin"])
            hinge_rows.update(hinges)
            linear_widths.add(len(row["lin"]))
    if linear_widths != {9}:
        raise AssertionError("unexpected n=9 linear width")
    total_rows = len(hinge_rows) + 9
    return {
        "status": "OPEN",
        "reason": (
            "No exact-Q n=9 kernel was attempted: this bead's dense FLINT path is calibrated "
            "only through n=8, while the saved n=9 matrix has 69,532,960 dense slots and an "
            "unprofiled exact-elimination/output footprint.  A sparse exact-rank/kernel path "
            "must be benchmarked before spending the shared 16 GiB ceiling."
        ),
        "saved_columns": columns,
        "hinge_rows": len(hinge_rows),
        "linear_rows": 9,
        "total_rows": total_rows,
        "stored_nonzero_entries_including_nonzero_linears": nonzeros,
        "dense_matrix_entry_denominator": total_rows * columns,
        "exact_rank_over_Q": None,
        "exact_nullity_over_Q": None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("all", "kernels", "collapse", "burnside"), nargs="?", default="all")
    parser.add_argument("--workers", type=int, default=6)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if not 1 <= args.workers <= 6:
        parser.error("--workers must be between 1 and 6 for the shared-machine budget")
    args.output_dir.mkdir(parents=True, exist_ok=True)

    started = time.time()
    summary: dict[str, object] = {
        "schema": "max11-span-structure-v1",
        "mode": args.mode,
        "workers": args.workers,
        "coefficient_field": "Q via exact integer matrices",
        "primes": list(PRIMES),
        "inputs": input_receipts(),
    }

    systems: dict[int, System] = {}
    required_n: set[int] = set()
    if args.mode in ("all", "kernels"):
        required_n.update((7, 8))
    if args.mode in ("all", "collapse"):
        required_n.update(range(5, 9))
    for n in sorted(required_n):
        before = time.time()
        systems[n] = build_system(n, args.workers)
        summary.setdefault("system_build_seconds", {})[str(n)] = round(time.time() - before, 3)

    if args.mode in ("all", "kernels"):
        summary["kernels_and_local_moves"] = run_kernel_experiments(systems, args.output_dir)
        summary["n9_exact_kernel"] = inspect_saved_n9_system()
    if args.mode in ("all", "collapse"):
        summary["vertex_collapse"] = run_collapse_experiment(systems)
    if args.mode in ("all", "burnside"):
        summary["burnside"] = run_burnside_experiment()
    summary["elapsed_seconds"] = round(time.time() - started, 3)
    output = args.output_dir / f"summary_{args.mode}.json"
    write_json(output, summary)
    print(json.dumps({"output": str(output), "elapsed_seconds": summary["elapsed_seconds"]}))


if __name__ == "__main__":
    main()
