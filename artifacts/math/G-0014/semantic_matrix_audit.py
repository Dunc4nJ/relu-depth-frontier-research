#!/usr/bin/env python3
"""Independent semantic replay of the frozen G-0008 cut matrix.

This file deliberately does not import any G-0006/G-0008/G-0010/G-0011
module.  It reconstructs the finite candidate family from the pinned MAX10
JSON certificate, computes an exact coloured-graph quotient with a local
individualisation/refinement canonical labeller, and derives every cut-matrix
entry from the mathematical atom

    max(sum_{uv in A} max(x_u, x_v), sum_{uv in B} max(x_u, x_v)).

The dynamic program is checked against direct permutation enumeration on
synthetic n <= 7 instances before the subject is read for comparison.
"""

from __future__ import annotations

import argparse
import collections
import functools
import gzip
import hashlib
import itertools
import json
import math
import multiprocessing as mp
import os
import platform
import sys
import tempfile
import time
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


SCHEMA = "max11-semantic-matrix-cleanroom-audit-v1"
N = 11
EXPECTED_RAW = 16_000
EXPECTED_CLASSES = 9_804
EXPECTED_HINGES = 7_135
EXPECTED_ROWS = 7_146
TARGET_FACTOR = math.factorial(N)

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
CLASSES = ROOT / "artifacts/math/G-0006/isomorphism_classes_v2.json"
SELECTION = ROOT / "artifacts/math/G-0008/cut_selection_01_02_03_04.json"
MATRIX = ROOT / "artifacts/math/G-0008/cut_matrix_01_02_03_04.npz"
EXACT_DUAL = ROOT / "artifacts/math/G-0011/cut_only_exact_left_dual_v1.json.gz"
DEFAULT_REPORT = Path(__file__).resolve().with_name("semantic_matrix_audit_v1.json")

Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]
Direction = tuple[int, ...]


def sha256_path(path: Path, block: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(block):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def semantic_pair_payload(pairs: Sequence[Pair]) -> list[list[list[list[int]]]]:
    return [
        [
            [[u + 1, v + 1] for u, v in colour]
            for colour in pair
        ]
        for pair in pairs
    ]


def components(n: int, edges: Iterable[tuple[int, int]]) -> list[tuple[int, ...]]:
    adjacency = [set() for _ in range(n)]
    for u, v in edges:
        if u == v:
            raise ValueError("loop found")
        adjacency[u].add(v)
        adjacency[v].add(u)
    seen: set[int] = set()
    result: list[tuple[int, ...]] = []
    for start in range(n):
        if start in seen:
            continue
        stack = [start]
        seen.add(start)
        part: list[int] = []
        while stack:
            vertex = stack.pop()
            part.append(vertex)
            for other in sorted(adjacency[vertex], reverse=True):
                if other not in seen:
                    seen.add(other)
                    stack.append(other)
        result.append(tuple(sorted(part)))
    return result


def reconstruct_raw_lifts(source: dict[str, object]) -> tuple[list[Pair], dict[str, object]]:
    if set(source) != {"n", "terms"} or source["n"] != 10 or not isinstance(source["terms"], list):
        raise ValueError("unexpected pinned MAX10 certificate schema")
    raw: list[Pair] = []
    accepted_source_indices: list[int] = []
    component_size_counts: collections.Counter[tuple[int, int]] = collections.Counter()
    choice_counts: collections.Counter[int] = collections.Counter()
    for term_index, term_obj in enumerate(source["terms"]):
        if not isinstance(term_obj, dict) or "pair" not in term_obj:
            raise ValueError(f"malformed source term {term_index}")
        pair_obj = term_obj["pair"]
        if not isinstance(pair_obj, list) or len(pair_obj) != 2:
            raise ValueError(f"malformed source pair {term_index}")
        colours: list[tuple[tuple[int, int], ...]] = []
        for edge_list in pair_obj:
            if not isinstance(edge_list, list) or len(edge_list) != 4:
                raise ValueError(f"source term {term_index} does not have four edges per colour")
            edges: list[tuple[int, int]] = []
            for edge in edge_list:
                if not isinstance(edge, list) or len(edge) != 2:
                    raise ValueError(f"malformed edge in source term {term_index}")
                u, v = (int(edge[0]) - 1, int(edge[1]) - 1)
                if not (0 <= u < v < 10):
                    raise ValueError(f"noncanonical or out-of-range edge in source term {term_index}")
                edges.append((u, v))
            colours.append(tuple(edges))
        a_edges, b_edges = colours
        union = a_edges + b_edges
        if len(set(union)) != 8:
            continue
        parts = components(10, union)
        if len(parts) != 2 or any(len(part) < 2 for part in parts):
            continue
        # Eight distinct edges on ten vertices with two components is a forest
        # precisely when each component has |V|-1 edges.
        if any(
            sum(u in part and v in part for u, v in union) != len(part) - 1
            for part in parts
        ):
            continue
        accepted_source_indices.append(term_index)
        sizes = tuple(sorted((len(parts[0]), len(parts[1]))))
        component_size_counts[sizes] += 1
        local_choices = 0
        # The raw-family order is part of the frozen class binding: components
        # are ordered by their least vertex, then both endpoint loops run in
        # increasing order inside that component.
        for part in parts:
            for a_endpoint in part:
                for b_endpoint in part:
                    raw.append(
                        (
                            a_edges + ((a_endpoint, 10),),
                            b_edges + ((b_endpoint, 10),),
                        )
                    )
                    local_choices += 1
        choice_counts[local_choices] += 1
    semantic_payload = canonical_json_bytes(semantic_pair_payload(raw))
    stats = {
        "accepted_source_term_count": len(accepted_source_indices),
        "accepted_source_indices_sha256": hashlib.sha256(
            canonical_json_bytes(accepted_source_indices)
        ).hexdigest(),
        "component_size_pair_counts": {
            f"{a}+{b}": count for (a, b), count in sorted(component_size_counts.items())
        },
        "per_source_raw_choice_counts": {
            str(choices): count for choices, count in sorted(choice_counts.items())
        },
        "raw_candidate_count": len(raw),
        "semantic_raw_pair_list_sha256_without_newline": hashlib.sha256(
            semantic_payload
        ).hexdigest(),
        "frozen_serialization_raw_pair_list_sha256_with_newline": hashlib.sha256(
            semantic_payload + b"\n"
        ).hexdigest(),
    }
    if len(raw) != EXPECTED_RAW:
        raise ValueError(f"raw lift census mismatch: {len(raw)} != {EXPECTED_RAW}")
    return raw, stats


def edge_type_matrix(pair: Pair, swap: bool) -> tuple[tuple[int, ...], ...]:
    n = 1 + max(v for colour in pair for edge in colour for v in edge)
    matrix = [[0] * n for _ in range(n)]
    for colour_index, edges in enumerate(pair):
        bit = 2 if (colour_index == 0) == swap else 1
        for u, v in edges:
            matrix[u][v] |= bit
            matrix[v][u] |= bit
    return tuple(tuple(row) for row in matrix)


def canonical_fixed_colour(matrix: tuple[tuple[int, ...], ...]) -> bytes:
    """Exact canonical code under vertex relabelling by IR search.

    Edge values are 0 (absent), 1 (A), 2 (B), or 3 (common).  Refinement is
    equitable with respect to counts of all three nonzero edge types into
    every ordered cell.  Individualisation explores every unresolved vertex,
    so refinement affects speed but not exactness.
    """

    n = len(matrix)

    def refine(partition: tuple[tuple[int, ...], ...]) -> tuple[tuple[int, ...], ...]:
        while True:
            refined: list[tuple[int, ...]] = []
            for cell in partition:
                buckets: dict[tuple[int, ...], list[int]] = {}
                for vertex in cell:
                    signature: list[int] = []
                    for target_cell in partition:
                        counts = [0, 0, 0]
                        for other in target_cell:
                            kind = matrix[vertex][other]
                            if kind:
                                counts[kind - 1] += 1
                        signature.extend(counts)
                    buckets.setdefault(tuple(signature), []).append(vertex)
                for signature in sorted(buckets):
                    refined.append(tuple(buckets[signature]))
            next_partition = tuple(refined)
            if next_partition == partition:
                return partition
            partition = next_partition

    @functools.lru_cache(maxsize=None)
    def search(partition: tuple[tuple[int, ...], ...]) -> bytes:
        partition = refine(partition)
        if all(len(cell) == 1 for cell in partition):
            order = [cell[0] for cell in partition]
            return bytes(
                matrix[order[i]][order[j]]
                for i in range(n)
                for j in range(i + 1, n)
            )
        cell_index = next(i for i, cell in enumerate(partition) if len(cell) > 1)
        cell = partition[cell_index]
        candidates: list[bytes] = []
        for vertex in cell:
            remainder = tuple(other for other in cell if other != vertex)
            child = (
                partition[:cell_index]
                + ((vertex,), remainder)
                + partition[cell_index + 1 :]
            )
            candidates.append(search(child))
        return min(candidates)

    return search((tuple(range(n)),))


def canonical_pair_key(pair: Pair) -> bytes:
    fixed = canonical_fixed_colour(edge_type_matrix(pair, swap=False))
    swapped = canonical_fixed_colour(edge_type_matrix(pair, swap=True))
    return min(fixed, swapped)


def independently_quotient(raw: Sequence[Pair]) -> tuple[list[int], list[int], list[int], str]:
    key_to_class: dict[bytes, int] = {}
    raw_to_class: list[int] = []
    representatives: list[int] = []
    class_sizes: list[int] = []
    ordered_keys: list[bytes] = []
    for raw_index, pair in enumerate(raw):
        key = canonical_pair_key(pair)
        class_index = key_to_class.get(key)
        if class_index is None:
            class_index = len(representatives)
            key_to_class[key] = class_index
            representatives.append(raw_index)
            class_sizes.append(0)
            ordered_keys.append(key)
        raw_to_class.append(class_index)
        class_sizes[class_index] += 1
    key_hash = hashlib.sha256(b"".join(ordered_keys)).hexdigest()
    return raw_to_class, representatives, class_sizes, key_hash


def signed_adjacency(pair: Pair, n: int) -> tuple[tuple[int, ...], ...]:
    result = [[0] * n for _ in range(n)]
    for u, v in pair[0]:
        result[u][v] += 1
        result[v][u] += 1
    for u, v in pair[1]:
        result[u][v] -= 1
        result[v][u] -= 1
    return tuple(tuple(row) for row in result)


def dp_direction_words(pair: Pair, n: int) -> collections.Counter[Direction]:
    adjacency = signed_adjacency(pair, n)
    full = (1 << n) - 1

    @functools.lru_cache(maxsize=None)
    def suffixes(mask: int) -> dict[Direction, int]:
        if mask == full:
            return {(): 1}
        result: collections.Counter[Direction] = collections.Counter()
        for vertex in range(n):
            if mask & (1 << vertex):
                continue
            increment = sum(
                adjacency[vertex][other]
                for other in range(n)
                if mask & (1 << other)
            )
            for suffix, count in suffixes(mask | (1 << vertex)).items():
                result[(increment,) + suffix] += count
        return result

    return collections.Counter(suffixes(0))


def brute_direction_words(pair: Pair, n: int) -> collections.Counter[Direction]:
    adjacency = signed_adjacency(pair, n)
    result: collections.Counter[Direction] = collections.Counter()
    for order in itertools.permutations(range(n)):
        earlier: list[int] = []
        word: list[int] = []
        for vertex in order:
            word.append(sum(adjacency[vertex][other] for other in earlier))
            earlier.append(vertex)
        result[tuple(word)] += 1
    return result


def orient_and_primitive(word: Direction) -> tuple[Direction | None, int]:
    first = next((entry for entry in word if entry), 0)
    if first == 0:
        return None, 0
    oriented = word if first > 0 else tuple(-entry for entry in word)
    divisor = math.gcd(*(abs(entry) for entry in oriented))
    if divisor <= 0:
        raise AssertionError("nonzero direction has nonpositive gcd")
    return tuple(entry // divisor for entry in oriented), divisor


def hinge_histogram(words: collections.Counter[Direction]) -> collections.Counter[Direction]:
    result: collections.Counter[Direction] = collections.Counter()
    for word, multiplicity in words.items():
        primitive, divisor = orient_and_primitive(word)
        if primitive is not None:
            result[primitive] += divisor * multiplicity
    return result


def subset_step_values(pair: Pair, n: int) -> list[int]:
    """Symmetrised atom values at (0^k,1^(n-k)), k=0,...,n."""

    edge_count = len(pair[0])
    if len(pair[1]) != edge_count:
        raise ValueError("branches have unequal edge counts")
    values: list[int] = []
    vertices = range(n)
    for zero_count in range(n + 1):
        subset_sum = 0
        for zero_vertices in itertools.combinations(vertices, zero_count):
            zero_set = set(zero_vertices)
            internal_a = sum(u in zero_set and v in zero_set for u, v in pair[0])
            internal_b = sum(u in zero_set and v in zero_set for u, v in pair[1])
            # Each edge contributes max(x_u,x_v), so it vanishes exactly when
            # both endpoints lie in the zero set.
            subset_sum += edge_count - min(internal_a, internal_b)
        values.append(
            math.factorial(zero_count)
            * math.factorial(n - zero_count)
            * subset_sum
        )
    return values


def linear_coefficients(pair: Pair, n: int, hinges: collections.Counter[Direction]) -> tuple[int, ...]:
    function_steps = subset_step_values(pair, n)
    linear_tail: list[int] = []
    for zero_count in range(n + 1):
        hinge_value = sum(
            coefficient * max(0, sum(direction[zero_count:]))
            for direction, coefficient in hinges.items()
        )
        linear_tail.append(function_steps[zero_count] - hinge_value)
    if linear_tail[-1] != 0:
        raise AssertionError("zero input must give zero")
    return tuple(linear_tail[index] - linear_tail[index + 1] for index in range(n))


def direct_decomposition(pair: Pair, n: int) -> tuple[collections.Counter[Direction], tuple[int, ...]]:
    result: collections.Counter[Direction] = collections.Counter()
    linear = [0] * n
    a_neighbours = [set() for _ in range(n)]
    b_neighbours = [set() for _ in range(n)]
    for u, v in pair[0]:
        a_neighbours[u].add(v)
        a_neighbours[v].add(u)
    for u, v in pair[1]:
        b_neighbours[u].add(v)
        b_neighbours[v].add(u)
    for order in itertools.permutations(range(n)):
        earlier: set[int] = set()
        a_vector: list[int] = []
        b_vector: list[int] = []
        for vertex in order:
            a_vector.append(len(a_neighbours[vertex] & earlier))
            b_vector.append(len(b_neighbours[vertex] & earlier))
            earlier.add(vertex)
        word = tuple(a - b for a, b in zip(a_vector, b_vector))
        primitive, divisor = orient_and_primitive(word)
        if primitive is None:
            base = a_vector
        elif next(entry for entry in word if entry) > 0:
            base = b_vector
            result[primitive] += divisor
        else:
            base = a_vector
            result[primitive] += divisor
        for index, value in enumerate(base):
            linear[index] += value
    return result, tuple(linear)


def symmetrised_pairwise_max_atom(pair: Pair, x: Sequence[int]) -> int:
    n = len(x)
    total = 0
    for order in itertools.permutations(range(n)):
        position = {vertex: rank for rank, vertex in enumerate(order)}
        branch_a = sum(max(x[position[u]], x[position[v]]) for u, v in pair[0])
        branch_b = sum(max(x[position[u]], x[position[v]]) for u, v in pair[1])
        total += max(branch_a, branch_b)
    return total


def evaluate_normal_form(
    hinges: collections.Counter[Direction], linear: Sequence[int], x: Sequence[int]
) -> int:
    return sum(a * b for a, b in zip(linear, x)) + sum(
        coefficient * max(0, sum(a * b for a, b in zip(direction, x)))
        for direction, coefficient in hinges.items()
    )


def run_controls() -> list[dict[str, object]]:
    cases: list[tuple[str, int, Pair]] = [
        (
            "n4_common_edge",
            4,
            (((0, 1), (0, 3)), ((1, 2), (0, 3))),
        ),
        (
            "n5_path_vs_fork",
            5,
            (((0, 1), (1, 2), (3, 4)), ((0, 2), (1, 3), (3, 4))),
        ),
        (
            "n6_two_components",
            6,
            (((0, 1), (1, 2), (3, 4), (4, 5)), ((0, 2), (1, 3), (3, 5), (4, 5))),
        ),
        (
            "n7_sparse_cycle",
            7,
            (((0, 1), (1, 2), (2, 3), (4, 5), (5, 6)), ((0, 2), (1, 3), (3, 4), (4, 6), (5, 6))),
        ),
    ]
    reports: list[dict[str, object]] = []
    endpoint_mutant_rejected = False
    for label, n, pair in cases:
        started = time.perf_counter()
        dp_words = dp_direction_words(pair, n)
        brute_words = brute_direction_words(pair, n)
        dp_hinges = hinge_histogram(dp_words)
        brute_hinges, brute_linear = direct_decomposition(pair, n)
        dp_linear = linear_coefficients(pair, n, dp_hinges)
        ordered_points = list(itertools.combinations_with_replacement((-2, 0, 3), n))
        direct_values = [symmetrised_pairwise_max_atom(pair, point) for point in ordered_points]
        normal_values = [evaluate_normal_form(dp_hinges, dp_linear, point) for point in ordered_points]
        if dp_words != brute_words:
            raise AssertionError(f"{label}: DP word histogram differs from direct permutations")
        if dp_hinges != brute_hinges:
            raise AssertionError(f"{label}: hinge histogram differs from direct decomposition")
        if dp_linear != brute_linear:
            raise AssertionError(f"{label}: linear coefficients differ from direct decomposition")
        if direct_values != normal_values:
            raise AssertionError(f"{label}: normal form differs from direct pairwise-max atom")
        # A deliberately wrong endpoint-sum reading replaces max(x_u,x_v) by
        # x_u+x_v.  It must disagree on at least one direct control point.
        for point, pairwise_value in zip(ordered_points, direct_values):
            endpoint_total = 0
            for order in itertools.permutations(range(n)):
                position = {vertex: rank for rank, vertex in enumerate(order)}
                branch_a = sum(point[position[u]] + point[position[v]] for u, v in pair[0])
                branch_b = sum(point[position[u]] + point[position[v]] for u, v in pair[1])
                endpoint_total += max(branch_a, branch_b)
            if endpoint_total != pairwise_value:
                endpoint_mutant_rejected = True
                break
        reports.append(
            {
                "label": label,
                "n": n,
                "permutations": math.factorial(n),
                "distinct_signed_direction_words": len(dp_words),
                "primitive_hinge_directions": len(dp_hinges),
                "ordered_direct_evaluation_points": len(ordered_points),
                "dp_equals_direct_words": True,
                "dp_equals_direct_hinges": True,
                "dp_equals_direct_linear": True,
                "normal_form_equals_direct_pairwise_max_atom": True,
                "seconds": round(time.perf_counter() - started, 6),
            }
        )
    if not endpoint_mutant_rejected:
        raise AssertionError("endpoint-sum mutant was not rejected by controls")
    reports.append(
        {
            "label": "endpoint_sum_semantic_mutant",
            "expected": "REJECTED",
            "result": "REJECTED",
            "meaning": "the audited atom uses a sum of pairwise maxima, not sums of endpoints",
        }
    )
    return reports


_WORKER_DIRECTIONS: dict[Direction, int] = {}
_WORKER_ROW_COUNT = 0


def init_worker(directions: Sequence[Sequence[int]]) -> None:
    global _WORKER_DIRECTIONS, _WORKER_ROW_COUNT
    _WORKER_DIRECTIONS = {tuple(map(int, direction)): row for row, direction in enumerate(directions)}
    _WORKER_ROW_COUNT = len(directions) + N


def generate_column(task: tuple[int, Pair]) -> tuple[int, np.ndarray, dict[str, int | float]]:
    column_index, pair = task
    started = time.perf_counter()
    words = dp_direction_words(pair, N)
    hinges = hinge_histogram(words)
    linear = linear_coefficients(pair, N, hinges)
    column = np.zeros(_WORKER_ROW_COUNT, dtype=np.int64)
    for direction, coefficient in hinges.items():
        row = _WORKER_DIRECTIONS.get(direction)
        if row is not None:
            column[row] = coefficient
    column[-N:] = np.asarray(linear, dtype=np.int64)
    return (
        column_index,
        column,
        {
            "distinct_words": len(words),
            "all_hinges": len(hinges),
            "selected_nonzero": int(np.count_nonzero(column[:-N])),
            "seconds": round(time.perf_counter() - started, 6),
        },
    )


def validate_selection(selection: dict[str, object]) -> list[list[int]]:
    if selection.get("n") != N or selection.get("selected_count") != EXPECTED_HINGES:
        raise ValueError("selection n/count mismatch")
    raw_directions = selection.get("directions")
    if not isinstance(raw_directions, list) or len(raw_directions) != EXPECTED_HINGES:
        raise ValueError("selection directions malformed")
    directions: list[list[int]] = []
    for index, value in enumerate(raw_directions):
        if not isinstance(value, list) or len(value) != N:
            raise ValueError(f"selection direction {index} has wrong length")
        direction = [int(entry) for entry in value]
        if any(not isinstance(entry, int) for entry in value):
            raise ValueError(f"selection direction {index} is not integral")
        if sum(direction) != 0 or not any(direction):
            raise ValueError(f"selection direction {index} violates zero-sum/nonzero condition")
        if next(entry for entry in direction if entry) < 0:
            raise ValueError(f"selection direction {index} violates orientation")
        if math.gcd(*(abs(entry) for entry in direction)) != 1:
            raise ValueError(f"selection direction {index} is not primitive")
        proper_prefix_sums = list(itertools.accumulate(direction))[:-1]
        # With zero total and first nonzero positive, a positive proper prefix
        # is automatic.  A negative proper prefix is also required: otherwise
        # d.x has one fixed sign throughout x_1<=...<=x_n and its ReLU is
        # linear (or identically zero) rather than an active chamber cut.
        if not any(value < 0 for value in proper_prefix_sums):
            raise ValueError(f"selection direction {index} is inactive on the ordered cone")
        directions.append(direction)
    if directions != sorted(directions) or len({tuple(direction) for direction in directions}) != len(directions):
        raise ValueError("selection directions are not a unique lexicographically sorted list")
    return directions


def load_dual_support(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        dual = json.load(fh)
    pivot_rows = [int(value) for value in dual.get("pivot_cut_rows", [])]
    failing_row = int(dual.get("failing_cut_row", -1))
    support = pivot_rows + [failing_row]
    if len(pivot_rows) != 5269 or len(set(support)) != 5270:
        raise ValueError("exact-dual support row census mismatch")
    if failing_row != EXPECTED_ROWS - 1:
        raise ValueError("exact-dual failing row is not final linear row")
    if any(row < 0 or row >= EXPECTED_ROWS for row in support):
        raise ValueError("exact-dual support row out of range")
    return {
        "pivot_row_count": len(pivot_rows),
        "support_row_count": len(support),
        "failing_row": failing_row,
        "support_rows_sha256": hashlib.sha256(
            np.asarray(support, dtype=np.int64).tobytes(order="C")
        ).hexdigest(),
        "support": support,
    }


def compare_full_matrix(
    representatives: Sequence[Pair],
    directions: Sequence[Sequence[int]],
    expected: np.ndarray,
    support_rows: set[int],
    workers: int,
    max_tasks_per_child: int,
    progress_every: int,
) -> dict[str, object]:
    if expected.shape != (EXPECTED_ROWS, EXPECTED_CLASSES) or expected.dtype != np.int64:
        raise ValueError(f"unexpected matrix array {expected.shape} {expected.dtype}")
    temporary = tempfile.NamedTemporaryFile(prefix="g0014-regenerated-", suffix=".i64", delete=False)
    temporary_path = Path(temporary.name)
    temporary.close()
    regenerated = np.memmap(
        temporary_path, dtype=np.int64, mode="w+", shape=expected.shape, order="C"
    )
    first_mismatches: list[dict[str, int]] = []
    mismatched_columns = 0
    mismatched_entries = 0
    support_mismatched_entries = 0
    column_seconds: list[float] = []
    distinct_word_min: int | None = None
    distinct_word_max = 0
    hinge_min: int | None = None
    hinge_max = 0
    selected_nonzero_total = 0
    started = time.perf_counter()
    context = mp.get_context("fork")
    try:
        with context.Pool(
            processes=workers,
            initializer=init_worker,
            initargs=(directions,),
            maxtasksperchild=max_tasks_per_child,
        ) as pool:
            tasks = enumerate(representatives)
            for completed, (column_index, column, stats) in enumerate(
                pool.imap_unordered(generate_column, tasks, chunksize=1), start=1
            ):
                regenerated[:, column_index] = column
                differing = np.flatnonzero(column != expected[:, column_index])
                if differing.size:
                    mismatched_columns += 1
                    mismatched_entries += int(differing.size)
                    support_mismatched_entries += sum(int(row) in support_rows for row in differing)
                    for row in differing[: max(0, 20 - len(first_mismatches))]:
                        first_mismatches.append(
                            {
                                "row": int(row),
                                "column": column_index,
                                "expected": int(expected[row, column_index]),
                                "regenerated": int(column[row]),
                            }
                        )
                seconds = float(stats["seconds"])
                column_seconds.append(seconds)
                words = int(stats["distinct_words"])
                hinges = int(stats["all_hinges"])
                distinct_word_min = words if distinct_word_min is None else min(distinct_word_min, words)
                distinct_word_max = max(distinct_word_max, words)
                hinge_min = hinges if hinge_min is None else min(hinge_min, hinges)
                hinge_max = max(hinge_max, hinges)
                selected_nonzero_total += int(stats["selected_nonzero"])
                if completed % progress_every == 0 or completed == len(representatives):
                    elapsed = time.perf_counter() - started
                    print(
                        f"G0014_PROGRESS completed={completed}/{len(representatives)} "
                        f"elapsed={elapsed:.1f}s mismatched_entries={mismatched_entries}",
                        flush=True,
                    )
        regenerated.flush()
        regenerated_hash = sha256_path(temporary_path)
    finally:
        del regenerated
        temporary_path.unlink(missing_ok=True)
    elapsed = time.perf_counter() - started
    return {
        "rows_compared": EXPECTED_ROWS,
        "columns_compared": EXPECTED_CLASSES,
        "entries_compared": EXPECTED_ROWS * EXPECTED_CLASSES,
        "dual_support_rows_compared": len(support_rows),
        "dual_support_entries_compared": len(support_rows) * EXPECTED_CLASSES,
        "mismatched_columns": mismatched_columns,
        "mismatched_entries": mismatched_entries,
        "dual_support_mismatched_entries": support_mismatched_entries,
        "first_mismatches": first_mismatches,
        "regenerated_matrix_int64_c_sha256": regenerated_hash,
        "selected_hinge_nonzero_entries": selected_nonzero_total,
        "distinct_word_count_min": distinct_word_min,
        "distinct_word_count_max": distinct_word_max,
        "all_hinge_count_min": hinge_min,
        "all_hinge_count_max": hinge_max,
        "worker_column_seconds_sum": round(sum(column_seconds), 6),
        "worker_column_seconds_mean": round(sum(column_seconds) / len(column_seconds), 6),
        "wall_seconds": round(elapsed, 6),
        "workers": workers,
        "max_tasks_per_child": max_tasks_per_child,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--max-tasks-per-child", type=int, default=8)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    if args.workers < 1 or args.workers > 16:
        parser.error("--workers must be in [1,16]")
    if args.max_tasks_per_child < 1 or args.max_tasks_per_child > 100:
        parser.error("--max-tasks-per-child must be in [1,100]")
    if args.progress_every < 1:
        parser.error("--progress-every must be positive")

    controls_started = time.perf_counter()
    controls = run_controls()
    print(
        f"G0014_CONTROLS PASS cases={len(controls)} seconds={time.perf_counter()-controls_started:.3f}",
        flush=True,
    )
    if args.controls_only:
        print(json.dumps({"schema": SCHEMA, "result": "PASS", "controls": controls}, sort_keys=True))
        return 0

    input_paths = {
        "producer_script": Path(__file__).resolve(),
        "source_certificate": SOURCE,
        "classes": CLASSES,
        "selection": SELECTION,
        "cut_matrix": MATRIX,
        "exact_dual": EXACT_DUAL,
    }
    for label, path in input_paths.items():
        if not path.is_file() or path.is_symlink():
            raise FileNotFoundError(f"{label} is not a contained regular file: {path}")
    input_hashes_before = {label: sha256_path(path) for label, path in input_paths.items()}

    with SOURCE.open("r", encoding="utf-8") as fh:
        source = json.load(fh)
    raw, raw_stats = reconstruct_raw_lifts(source)
    print(
        f"G0014_RAW PASS source_terms={raw_stats['accepted_source_term_count']} raw={len(raw)}",
        flush=True,
    )

    quotient_started = time.perf_counter()
    independent_raw_to_class, independent_representatives, independent_class_sizes, class_key_hash = independently_quotient(raw)
    with CLASSES.open("r", encoding="utf-8") as fh:
        frozen_classes = json.load(fh)
    recorded_raw_hash_match = (
        raw_stats["frozen_serialization_raw_pair_list_sha256_with_newline"]
        == frozen_classes.get("raw_pair_list_sha256")
    )
    frozen_raw_to_class = [int(value) for value in frozen_classes.get("raw_to_class", [])]
    frozen_representatives = [
        int(value) for value in frozen_classes.get("representative_raw_indices", [])
    ]
    frozen_class_sizes = [int(value) for value in frozen_classes.get("class_sizes", [])]
    if not (
        len(frozen_raw_to_class) == EXPECTED_RAW
        and len(frozen_representatives) == EXPECTED_CLASSES
        and len(frozen_class_sizes) == EXPECTED_CLASSES
    ):
        raise AssertionError("frozen quotient arrays have unexpected lengths")

    independent_to_frozen: dict[int, int] = {}
    frozen_to_independent: dict[int, int] = {}
    partition_conflicts: list[dict[str, int]] = []
    for raw_index, (independent_class, frozen_class) in enumerate(
        zip(independent_raw_to_class, frozen_raw_to_class)
    ):
        prior_frozen = independent_to_frozen.setdefault(independent_class, frozen_class)
        prior_independent = frozen_to_independent.setdefault(frozen_class, independent_class)
        if prior_frozen != frozen_class or prior_independent != independent_class:
            if len(partition_conflicts) < 20:
                partition_conflicts.append(
                    {
                        "raw_index": raw_index,
                        "independent_class": independent_class,
                        "frozen_class": frozen_class,
                        "independent_class_previously_mapped_to": prior_frozen,
                        "frozen_class_previously_mapped_from": prior_independent,
                    }
                )
    partition_bijection = (
        not partition_conflicts
        and len(independent_to_frozen) == EXPECTED_CLASSES
        and len(frozen_to_independent) == EXPECTED_CLASSES
    )
    mapped_sizes_match = partition_bijection and all(
        independent_class_sizes[independent_class] == frozen_class_sizes[frozen_class]
        for independent_class, frozen_class in independent_to_frozen.items()
    )
    frozen_representatives_bound = partition_bijection and all(
        0 <= raw_index < EXPECTED_RAW
        and frozen_raw_to_class[raw_index] == frozen_class
        and independent_to_frozen[independent_raw_to_class[raw_index]] == frozen_class
        for frozen_class, raw_index in enumerate(frozen_representatives)
    )
    quotient_checks = {
        "class_count": len(independent_representatives),
        "raw_pair_list_recorded_sha256_exact_match": recorded_raw_hash_match,
        "partition_exact_match_up_to_class_label_bijection": partition_bijection,
        "partition_conflicts": partition_conflicts,
        "mapped_class_sizes_exact_match": mapped_sizes_match,
        "every_frozen_representative_bound_to_claimed_block": frozen_representatives_bound,
        "frozen_representative_count": len(frozen_representatives),
        "independent_first_representatives_equal_frozen_representatives": independent_representatives
        == frozen_representatives,
        "independent_class_ids_equal_frozen_class_ids": independent_raw_to_class
        == frozen_raw_to_class,
        "independent_canonical_class_keys_sha256": class_key_hash,
        "seconds": round(time.perf_counter() - quotient_started, 6),
    }
    if len(independent_representatives) != EXPECTED_CLASSES or not all(
        quotient_checks[key]
        for key in (
            "partition_exact_match_up_to_class_label_bijection",
            "raw_pair_list_recorded_sha256_exact_match",
            "mapped_class_sizes_exact_match",
            "every_frozen_representative_bound_to_claimed_block",
        )
    ):
        raise AssertionError(f"independent class quotient mismatch: {quotient_checks}")
    print(
        f"G0014_QUOTIENT PASS classes={len(independent_representatives)} "
        f"seconds={quotient_checks['seconds']}",
        flush=True,
    )

    with SELECTION.open("r", encoding="utf-8") as fh:
        selection = json.load(fh)
    directions = validate_selection(selection)
    dual_support = load_dual_support(EXACT_DUAL)
    with np.load(MATRIX, allow_pickle=False) as archive:
        archive_checks = {
            "keys": sorted(archive.files),
            "schema": str(archive["schema"][0]),
            "selection_sha256": str(archive["selection_sha256"][0]),
            "classes_sha256": str(archive["classes_sha256"][0]),
            "class_indices_identity": np.array_equal(
                archive["class_indices"], np.arange(EXPECTED_CLASSES, dtype=np.int64)
            ),
        }
        expected_matrix = archive["matrix"]
    if archive_checks != {
        "keys": ["class_indices", "classes_sha256", "matrix", "schema", "selection_sha256", "source_manifest_json"],
        "schema": "max11-exact-hinge-cut-matrix-v1",
        "selection_sha256": input_hashes_before["selection"],
        "classes_sha256": input_hashes_before["classes"],
        "class_indices_identity": True,
    }:
        raise AssertionError(f"matrix archive binding mismatch: {archive_checks}")
    frozen_array_hash = hashlib.sha256(expected_matrix.tobytes(order="C")).hexdigest()
    # Matrix column j is explicitly bound to the frozen representative for
    # frozen class j, after the independent partition-bijection check above.
    representatives = [raw[index] for index in frozen_representatives]
    matrix_checks = compare_full_matrix(
        representatives,
        directions,
        expected_matrix,
        set(dual_support.pop("support")),
        args.workers,
        args.max_tasks_per_child,
        args.progress_every,
    )
    input_hashes_after = {label: sha256_path(path) for label, path in input_paths.items()}
    stable_inputs = input_hashes_before == input_hashes_after
    target = np.zeros(EXPECTED_ROWS, dtype=np.int64)
    target[-1] = TARGET_FACTOR
    target_checks = {
        "hinge_target_nonzero_count": int(np.count_nonzero(target[:EXPECTED_HINGES])),
        "linear_target": target[-N:].tolist(),
        "nonzero_rows": np.flatnonzero(target).astype(int).tolist(),
        "final_linear_row": EXPECTED_ROWS - 1,
        "final_linear_value": int(target[-1]),
        "target_int64_c_sha256": hashlib.sha256(target.tobytes(order="C")).hexdigest(),
        "matches_exact_dual_failing_row": dual_support["failing_row"] == EXPECTED_ROWS - 1,
    }
    passed = (
        stable_inputs
        and matrix_checks["mismatched_entries"] == 0
        and matrix_checks["regenerated_matrix_int64_c_sha256"] == frozen_array_hash
        and target_checks["hinge_target_nonzero_count"] == 0
        and target_checks["nonzero_rows"] == [EXPECTED_ROWS - 1]
        and target_checks["final_linear_value"] == TARGET_FACTOR
    )
    report = {
        "schema": SCHEMA,
        "result": "PASS" if passed else "FAIL",
        "mode": "clean-room semantic regeneration; no import of prior generators or exact solvers",
        "claim_boundary": (
            "Audits the semantics and bytes of the frozen 7146 x 9804 finite cut matrix and its "
            "target vector. It does not audit the exact dual arithmetic, prove the 9804-class family "
            "complete, or imply an unrestricted two-hidden-layer MAX11 lower bound."
        ),
        "atom": "max(sum_{uv in A} max(x_u,x_v), sum_{uv in B} max(x_u,x_v))",
        "normal_form": (
            "On x_1<=...<=x_11, each vertex order yields branch coefficient vectors a,b; "
            "delta=a-b is oriented by its first nonzero entry, divided by gcd, and contributes "
            "gcd*ReLU(primitive_delta dot x) plus the opposite branch as the linear base."
        ),
        "inputs_sha256_before": input_hashes_before,
        "inputs_sha256_after": input_hashes_after,
        "inputs_stable_during_run": stable_inputs,
        "controls": controls,
        "raw_family": raw_stats,
        "quotient": quotient_checks,
        "selection": {
            "direction_count": len(directions),
            "all_integer_nonzero_zero_sum_primitive_first_nonzero_positive": True,
            "all_ordered_cone_active_via_negative_proper_prefix": True,
            "unique_lexicographically_sorted": True,
            "directions_canonical_json_sha256": hashlib.sha256(
                canonical_json_bytes(directions)
            ).hexdigest(),
        },
        "matrix_archive": archive_checks,
        "frozen_matrix_int64_c_sha256": frozen_array_hash,
        "matrix_semantic_replay": matrix_checks,
        "exact_dual_support_binding": dual_support,
        "target_semantics": target_checks,
        "environment": {
            "python": sys.version,
            "numpy": np.__version__,
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
        },
        "residual_lineage_risks": [
            "Both the frozen matrix and this replay run on the same host and CPython/NumPy stack.",
            "The replay validates a finite registered family; the completeness bridge to arbitrary two-hidden-layer networks is absent.",
            "The exact rational left-dual arithmetic is a separate audit object and is not regenerated here.",
            "The target normalization 11!*MAX11 is checked against the registered cut-system convention, not derived from an unrestricted symmetrization theorem here.",
        ],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_bytes(canonical_json_bytes(report) + b"\n")
    print(
        f"G0014_RESULT {report['result']} mismatches={matrix_checks['mismatched_entries']} "
        f"report={args.report} sha256={sha256_path(args.report)}",
        flush=True,
    )
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
