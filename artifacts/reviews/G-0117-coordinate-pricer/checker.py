#!/usr/bin/env python3
"""Independent exact checker for the G-0117 coordinate pricer.

This file intentionally re-derives the recurrences from the raw signed edge
records.  It does not import or execute the G-0109/G-0117 implementations.

The expensive reference pass visits all 11! labelled permutations, in
factoradic order, in NumPy batches.  It simultaneously:

* obtains literal rank-signature multiplicities for four low-active records;
* evaluates every raw word of one active-11 cyclic record;
* accumulates its prefix-orientation linear correction; and
* counts all signed scales of one supported and two control directions.

All arithmetic used for the mathematical comparisons is integral and remains
well inside signed 64-bit range; the DP implementations themselves use Python
integers.
"""

from __future__ import annotations

import argparse
import gc
import hashlib
import itertools
import json
import math
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


N = 11
DEGREE = 5
FULL_MASK = (1 << N) - 1
SELECTED_SEQUENCES = (5341, 152715, 160213, 73165, 3)
LOW3_SEQUENCES = (5341, 152715, 160213)
LOW4_SEQUENCE = 73165
ACTIVE11_SEQUENCE = 3
ZERO, POSITIVE, NEGATIVE = 0, 1, 2

HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
DEFAULT_INPUT = PROJECT_ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
DEFAULT_RESULT = HERE / "results.json"


@dataclass(frozen=True)
class Record:
    sequence: int
    signed_mass: int
    active_vertices: int
    negative_edges: tuple[tuple[int, int], ...]
    positive_edges: tuple[tuple[int, int], ...]


@dataclass
class NormalForm:
    hinges: dict[tuple[int, ...], int]
    inactive_raw: dict[tuple[int, ...], int]
    correction: tuple[int, ...]
    negative_permutations: int
    zero_permutations: int
    total_permutations: int


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def edge_tuple(raw: Sequence[Sequence[int]]) -> tuple[tuple[int, int], ...]:
    return tuple((int(edge[0]), int(edge[1])) for edge in raw)


def record_from_json(raw: dict) -> Record:
    return Record(
        sequence=int(raw["sequence"]),
        signed_mass=int(raw["signed_mass"]),
        active_vertices=int(raw["active_vertices"]),
        negative_edges=edge_tuple(raw["negative_edges"]),
        positive_edges=edge_tuple(raw["positive_edges"]),
    )


def matrix_from_record(record: Record) -> tuple[tuple[int, ...], ...]:
    k = record.active_vertices
    matrix = [[0] * k for _ in range(k)]
    for sign, edges in ((-1, record.negative_edges), (1, record.positive_edges)):
        for u, v in edges:
            check(0 <= u <= v < k, f"sequence {record.sequence}: bad edge {(u, v)}")
            if u == v:
                matrix[u][u] += sign
            else:
                matrix[u][v] += sign
                matrix[v][u] += sign
    return tuple(tuple(row) for row in matrix)


def increment_table(matrix: Sequence[Sequence[int]]) -> tuple[tuple[int, ...], ...]:
    """q(v,S) = W[v,v] + sum_{u in S} W[v,u], computed directly."""
    k = len(matrix)
    table: list[tuple[int, ...]] = []
    for v in range(k):
        values = []
        for mask in range(1 << k):
            values.append(matrix[v][v] + sum(matrix[v][u] for u in range(k) if mask >> u & 1))
        table.append(tuple(values))
    return tuple(table)


def word_for_order(
    matrix: Sequence[Sequence[int]], order: Sequence[int], n: int = N
) -> tuple[int, ...]:
    table = increment_table(matrix)
    mask = 0
    word = [0] * n
    for rank, vertex in enumerate(order):
        if vertex < len(matrix):
            word[rank] = table[vertex][mask]
            mask |= 1 << vertex
    check(mask == (1 << len(matrix)) - 1, "order omitted an active vertex")
    return tuple(word)


def word_for_positions(
    matrix: Sequence[Sequence[int]], positions: Sequence[int], n: int = N
) -> tuple[int, ...]:
    check(len(positions) == len(matrix), "position/matrix size mismatch")
    check(len(set(positions)) == len(positions), "active positions are not injective")
    table = increment_table(matrix)
    mask = 0
    word = [0] * n
    for vertex in sorted(range(len(matrix)), key=lambda item: positions[item]):
        rank = positions[vertex]
        word[rank] = table[vertex][mask]
        mask |= 1 << vertex
    return tuple(word)


def first_nonzero(word: Sequence[int]) -> int:
    return next((value for value in word if value), 0)


def canonicalize(word: Sequence[int]) -> tuple[tuple[int, ...], int, bool] | None:
    first = first_nonzero(word)
    if first == 0:
        return None
    scale = math.gcd(*map(abs, word))
    check(scale > 0, "nonzero word had zero gcd")
    sign = 1 if first > 0 else -1
    direction = tuple(sign * value // scale for value in word)
    check(sum(direction) == 0, f"non-zero-sum direction {direction}")
    check(math.gcd(*map(abs, direction)) == 1, "direction is not primitive")
    check(first_nonzero(direction) > 0, "direction is not first-positive")
    return direction, scale, first < 0


def active_direction(direction: Sequence[int]) -> bool:
    """Whether d.x changes sign in the interior of x_0 <= ... <= x_10."""
    check(len(direction) == N, "direction length drift")
    check(sum(direction) == 0, "direction is not zero-sum")
    check(first_nonzero(direction) > 0, "direction is not first-positive")
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def raw_coordinate_price(
    matrix: Sequence[Sequence[int]],
    direction: Sequence[int],
    *,
    restore_inactive_labels: bool = True,
    scale_bound: int = DEGREE,
) -> tuple[int, dict[int, int]]:
    """Subset DP for sum_s |s| count(W word = s*d).

    Counts inside the recurrence are active-rank injections.  Exactly one
    transition represents an inactive rank.  The (N-k)! labelled-inactive
    multiplicity is restored only at the end.
    """
    k = len(matrix)
    table = increment_table(matrix)
    full = (1 << k) - 1
    scale_counts: dict[int, int] = {}
    for scale in tuple(range(-scale_bound, 0)) + tuple(range(1, scale_bound + 1)):
        target = tuple(scale * value for value in direction)
        states: dict[int, int] = {0: 1}
        for rank in range(N):
            nxt: defaultdict[int, int] = defaultdict(int)
            expected = target[rank]
            for mask, count in states.items():
                inactive_used = rank - mask.bit_count()
                if inactive_used < N - k and expected == 0:
                    nxt[mask] += count
                for vertex in range(k):
                    bit = 1 << vertex
                    if not mask & bit and table[vertex][mask] == expected:
                        nxt[mask | bit] += count
            states = dict(nxt)
        scale_counts[scale] = states.get(full, 0)
    injection_price = sum(abs(scale) * count for scale, count in scale_counts.items())
    factor = math.factorial(N - k) if restore_inactive_labels else 1
    return factor * injection_price, scale_counts


def hinge_coordinate_price(
    matrix: Sequence[Sequence[int]], direction: Sequence[int]
) -> tuple[int, dict[int, int]]:
    """Normal-form hinge price; canonically inactive directions are omitted."""
    if not active_direction(direction):
        return 0, {scale: 0 for scale in range(-DEGREE, DEGREE + 1) if scale}
    return raw_coordinate_price(matrix, direction)


def three_state_linear_correction(matrix: Sequence[Sequence[int]]) -> tuple[int, ...]:
    """Exact prefix-sign DP with a vector-sum payload.

    State identity is (placed-active mask, first-nonzero sign in {0,+,-}).
    Each payload is (prefix count, sums of already accepted word coordinates).
    Carrying the sums is essential: adding a coordinate to a global counter at
    transition time would fail to multiply it by later suffix completions.
    """
    k = len(matrix)
    table = increment_table(matrix)
    # (mask, sign) -> [count, coordinate-sum list]
    states: dict[tuple[int, int], tuple[int, list[int]]] = {(0, ZERO): (1, [0] * N)}
    for rank in range(N):
        nxt_counts: defaultdict[tuple[int, int], int] = defaultdict(int)
        nxt_sums: dict[tuple[int, int], list[int]] = {}

        def extend(mask: int, state: int, count: int, sums: list[int], value: int, new_mask: int) -> None:
            if state == ZERO:
                new_state = NEGATIVE if value < 0 else POSITIVE if value > 0 else ZERO
            else:
                new_state = state
            key = (new_mask, new_state)
            nxt_counts[key] += count
            aggregate = nxt_sums.setdefault(key, [0] * N)
            for coordinate, total in enumerate(sums):
                aggregate[coordinate] += total
            if new_state == NEGATIVE:
                aggregate[rank] += value * count

        for (mask, state), (count, sums) in states.items():
            inactive_used = rank - mask.bit_count()
            if inactive_used < N - k:
                extend(mask, state, count, sums, 0, mask)
            for vertex in range(k):
                bit = 1 << vertex
                if not mask & bit:
                    extend(mask, state, count, sums, table[vertex][mask], mask | bit)
        states = {key: (nxt_counts[key], nxt_sums[key]) for key in nxt_counts}

    full = (1 << k) - 1
    injection_count = sum(states.get((full, state), (0, []))[0] for state in (ZERO, POSITIVE, NEGATIVE))
    check(injection_count == math.factorial(N) // math.factorial(N - k), "rank-injection census drift")
    correction = states.get((full, NEGATIVE), (0, [0] * N))[1]
    factor = math.factorial(N - k)
    return tuple(factor * value for value in correction)


def aggregate_words(weighted_words: Iterable[tuple[Sequence[int], int]]) -> NormalForm:
    hinges: defaultdict[tuple[int, ...], int] = defaultdict(int)
    inactive: defaultdict[tuple[int, ...], int] = defaultdict(int)
    correction = [0] * N
    negative_permutations = 0
    zero_permutations = 0
    total = 0
    for word, multiplicity in weighted_words:
        total += multiplicity
        canonical = canonicalize(word)
        if canonical is None:
            zero_permutations += multiplicity
            continue
        direction, scale, negative = canonical
        if negative:
            negative_permutations += multiplicity
            for rank, value in enumerate(word):
                correction[rank] += multiplicity * value
        target = hinges if active_direction(direction) else inactive
        target[direction] += scale * multiplicity
    return NormalForm(
        hinges=dict(sorted(hinges.items())),
        inactive_raw=dict(sorted(inactive.items())),
        correction=tuple(correction),
        negative_permutations=negative_permutations,
        zero_permutations=zero_permutations,
        total_permutations=total,
    )


def decode_positions(code: int, k: int) -> tuple[int, ...]:
    positions = [0] * k
    for vertex in range(k - 1, -1, -1):
        positions[vertex] = code % N
        code //= N
    return tuple(positions)


def normal_form_from_literal_signatures(
    matrix: Sequence[Sequence[int]], counts: np.ndarray, k: int
) -> NormalForm:
    weighted = []
    for raw_code in np.flatnonzero(counts):
        code = int(raw_code)
        positions = decode_positions(code, k)
        weighted.append((word_for_positions(matrix, positions), int(counts[code])))
    return aggregate_words(weighted)


def factoradic_permutation_block(start: int, stop: int, n: int) -> np.ndarray:
    """Lexicographic permutations with ranks in [start, stop)."""
    check(0 <= start <= stop <= math.factorial(n), "factoradic block out of range")
    size = stop - start
    residual = np.arange(start, stop, dtype=np.int64)
    available = np.broadcast_to(np.arange(n, dtype=np.int8), (size, n)).copy()
    output = np.empty((size, n), dtype=np.int8)
    rows = np.arange(size, dtype=np.intp)
    for position in range(n):
        remaining = n - position
        place = math.factorial(remaining - 1)
        digit = residual // place
        residual %= place
        output[:, position] = available[rows, digit.astype(np.intp)]
        if remaining > 1:
            keep = np.ones((size, remaining), dtype=bool)
            keep[rows, digit.astype(np.intp)] = False
            available = available[keep].reshape(size, remaining - 1)
    return output


def validate_factoradic_generator() -> None:
    expected = np.asarray(list(itertools.permutations(range(7))), dtype=np.int8)
    observed = factoradic_permutation_block(0, math.factorial(7), 7)
    check(np.array_equal(observed, expected), "factoradic generator disagrees with itertools at n=7")


def numpy_increment_table(matrix: Sequence[Sequence[int]]) -> np.ndarray:
    return np.asarray(increment_table(matrix), dtype=np.int16)


def scale_histogram(words: np.ndarray, direction: Sequence[int]) -> np.ndarray:
    direction_array = np.asarray(direction, dtype=np.int16)
    pivot = int(np.flatnonzero(direction_array)[0])
    pivot_value = int(direction_array[pivot])
    values = words[:, pivot].astype(np.int16)
    divisible = values % pivot_value == 0
    scales = np.where(divisible, values // pivot_value, 0)
    matches = divisible & np.all(words.astype(np.int16) == scales[:, None] * direction_array[None, :], axis=1)
    accepted = scales[matches]
    return np.bincount(accepted + DEGREE, minlength=2 * DEGREE + 1).astype(np.int64)


def literal_full_permutation_scan(
    active11_matrix: Sequence[Sequence[int]],
    supported_direction: Sequence[int],
    outside_direction: Sequence[int],
    inactive_direction: Sequence[int],
    batch_size: int,
) -> dict:
    """Visit every one of the 11! labelled permutations exactly once."""
    validate_factoradic_generator()
    total_expected = math.factorial(N)
    counts3 = np.zeros(N**3, dtype=np.int64)
    counts4 = np.zeros(N**4, dtype=np.int64)
    supported_hist = np.zeros(2 * DEGREE + 1, dtype=np.int64)
    outside_hist = np.zeros(2 * DEGREE + 1, dtype=np.int64)
    inactive_hist = np.zeros(2 * DEGREE + 1, dtype=np.int64)
    correction = np.zeros(N, dtype=np.int64)
    swapped_correction = np.zeros(N, dtype=np.int64)
    raw_sum = np.zeros(N, dtype=np.int64)
    increment = numpy_increment_table(active11_matrix)
    started = time.monotonic()
    next_report = 2_000_000

    for start in range(0, total_expected, batch_size):
        stop = min(total_expected, start + batch_size)
        permutations = factoradic_permutation_block(start, stop, N)
        size = stop - start
        positions = []
        for vertex in range(4):
            positions.append(np.argmax(permutations == vertex, axis=1).astype(np.int64))
        code3 = (positions[0] * N + positions[1]) * N + positions[2]
        code4 = code3 * N + positions[3]
        counts3 += np.bincount(code3, minlength=N**3)
        counts4 += np.bincount(code4, minlength=N**4)

        masks = np.zeros(size, dtype=np.int16)
        words = np.zeros((size, N), dtype=np.int16)
        rows = np.arange(size, dtype=np.intp)
        for rank in range(N):
            vertices = permutations[:, rank].astype(np.intp)
            values = increment[vertices, masks.astype(np.intp)]
            words[:, rank] = values
            masks |= (1 << vertices).astype(np.int16)
        check(bool(np.all(masks == FULL_MASK)), "literal permutation mask census drift")

        nonzero = words != 0
        has_nonzero = np.any(nonzero, axis=1)
        first_indices = np.argmax(nonzero, axis=1)
        first_values = words[rows, first_indices]
        negative = has_nonzero & (first_values < 0)
        positive = has_nonzero & (first_values > 0)
        correction += np.sum(words[negative], axis=0, dtype=np.int64)
        swapped_correction -= np.sum(words[positive], axis=0, dtype=np.int64)
        raw_sum += np.sum(words, axis=0, dtype=np.int64)
        supported_hist += scale_histogram(words, supported_direction)
        outside_hist += scale_histogram(words, outside_direction)
        inactive_hist += scale_histogram(words, inactive_direction)

        if stop >= next_report or stop == total_expected:
            elapsed = time.monotonic() - started
            print(
                f"literal 11! scan: {stop:,}/{total_expected:,} permutations "
                f"({elapsed:.1f}s)",
                flush=True,
            )
            next_report += 2_000_000

    elapsed = time.monotonic() - started
    return {
        "counts3": counts3,
        "counts4": counts4,
        "supported_hist": supported_hist,
        "outside_hist": outside_hist,
        "inactive_hist": inactive_hist,
        "correction": correction,
        "swapped_correction": swapped_correction,
        "raw_sum": raw_sum,
        "elapsed_seconds": elapsed,
    }


def base_linear() -> tuple[int, ...]:
    return tuple(2 * DEGREE * rank * math.factorial(N - 2) for rank in range(N))


def normal_form_value(form: NormalForm, point: Sequence[int], include_correction: bool = True) -> int:
    total = sum(coefficient * value for coefficient, value in zip(base_linear(), point))
    if include_correction:
        total += sum(coefficient * value for coefficient, value in zip(form.correction, point))
    for direction, coefficient in form.hinges.items():
        argument = sum(a * b for a, b in zip(direction, point))
        total += coefficient * max(argument, 0)
    return total


def graph_value(edges: Sequence[tuple[int, int]], positions: Sequence[int], point: Sequence[int]) -> int:
    return sum(point[max(positions[u], positions[v])] for u, v in edges)


def literal_atom_value_from_signatures(
    record: Record,
    counts4: np.ndarray,
    point: Sequence[int],
    padding: Sequence[tuple[int, int]],
    *,
    swap_branches: bool = False,
) -> int:
    check(record.active_vertices == 3, "common-padding control expects active=3")
    check(len(record.negative_edges) + len(padding) == DEGREE, "left branch degree drift")
    check(len(record.positive_edges) + len(padding) == DEGREE, "right branch degree drift")
    left = record.negative_edges + tuple(padding)
    right = record.positive_edges + tuple(padding)
    if swap_branches:
        left, right = right, left
    total = 0
    for raw_code in np.flatnonzero(counts4):
        code = int(raw_code)
        positions = decode_positions(code, 4)
        atom = max(graph_value(left, positions, point), graph_value(right, positions, point))
        total += int(counts4[code]) * atom
    return total


def relabel_matrix(matrix: Sequence[Sequence[int]], old_to_new: Sequence[int]) -> tuple[tuple[int, ...], ...]:
    k = len(matrix)
    check(sorted(old_to_new) == list(range(k)), "not a vertex permutation")
    output = [[0] * k for _ in range(k)]
    for old_u in range(k):
        for old_v in range(k):
            output[old_to_new[old_u]][old_to_new[old_v]] = matrix[old_u][old_v]
    return tuple(tuple(row) for row in output)


def has_cycle(record: Record) -> bool:
    parent = list(range(record.active_vertices))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for u, v in record.negative_edges + record.positive_edges:
        root_u, root_v = find(u), find(v)
        if root_u == root_v:
            return True
        parent[root_u] = root_v
    return False


def direction_digest(hinges: dict[tuple[int, ...], int]) -> str:
    payload = json.dumps(
        [[list(direction), coefficient] for direction, coefficient in sorted(hinges.items())],
        separators=(",", ":"),
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def load_records(path: Path) -> tuple[dict[int, Record], dict]:
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    check(payload["schema"] == "max11-g0113-panel-solver-input-v1", "G-0113 schema drift")
    records = payload["records"]
    check(len(records) == 163_740, "G-0113 record census drift")
    selected: dict[int, Record] = {}
    active_histogram: Counter[int] = Counter()
    loop_records = 0
    multiedge_records = 0
    overlap_records = 0
    for raw in records:
        signed_mass = int(raw["signed_mass"])
        active = int(raw["active_vertices"])
        negative = edge_tuple(raw["negative_edges"])
        positive = edge_tuple(raw["positive_edges"])
        check(0 <= signed_mass <= DEGREE, "signed mass outside degree-five bound")
        check(len(negative) == signed_mass == len(positive), "signed edge census drift")
        active_histogram[active] += 1
        if any(u == v for u, v in negative + positive):
            loop_records += 1
        if len(set(negative)) < len(negative) or len(set(positive)) < len(positive):
            multiedge_records += 1
        if Counter(negative) & Counter(positive):
            overlap_records += 1
        endpoints = {vertex for edge in negative + positive for vertex in edge}
        if active == 0:
            check(not endpoints, "active=0 record has endpoints")
        else:
            check(endpoints == set(range(active)), "active support is not exact/contiguous")
        sequence = int(raw["sequence"])
        if sequence in SELECTED_SEQUENCES:
            selected[sequence] = record_from_json(raw)
    check(set(selected) == set(SELECTED_SEQUENCES), "selected sequence missing from panel input")
    census = {
        "record_count": len(records),
        "active_histogram": {str(key): value for key, value in sorted(active_histogram.items())},
        "loop_records": loop_records,
        "multiedge_records": multiedge_records,
        "opposite_sign_overlap_records": overlap_records,
    }
    del payload, records
    gc.collect()
    return selected, census


def histogram_to_dict(histogram: np.ndarray) -> dict[str, int]:
    return {
        str(scale - DEGREE): int(count)
        for scale, count in enumerate(histogram)
        if scale != DEGREE and int(count) != 0
    }


def find_valid_edge_sign_mutant(
    record: Record,
    original_correction: tuple[int, ...],
    direction: tuple[int, ...],
    original_price: int,
) -> dict:
    for negative_index in range(len(record.negative_edges)):
        for positive_index in range(len(record.positive_edges)):
            negative = list(record.negative_edges)
            positive = list(record.positive_edges)
            negative[negative_index], positive[positive_index] = positive[positive_index], negative[negative_index]
            mutant = Record(
                sequence=record.sequence,
                signed_mass=record.signed_mass,
                active_vertices=record.active_vertices,
                negative_edges=tuple(sorted(negative)),
                positive_edges=tuple(sorted(positive)),
            )
            matrix = matrix_from_record(mutant)
            correction = three_state_linear_correction(matrix)
            price, _ = hinge_coordinate_price(matrix, direction)
            if correction != original_correction or price != original_price:
                return {
                    "swapped_negative_edge_index": negative_index,
                    "swapped_positive_edge_index": positive_index,
                    "negative_edges": [list(edge) for edge in mutant.negative_edges],
                    "positive_edges": [list(edge) for edge in mutant.positive_edges],
                    "supported_price": price,
                    "correction": list(correction),
                }
    raise AssertionError("every valid edge-sign mutant escaped both exact controls")


def run(input_path: Path, result_path: Path, batch_size: int) -> dict:
    with input_path.open("rb") as handle:
        input_sha256 = hashlib.file_digest(handle, "sha256").hexdigest()
    selected, census = load_records(input_path)
    check(census["loop_records"] == 0, "G-0113 loopless-family assumption failed")
    check(census["opposite_sign_overlap_records"] == 0, "uncancelled common signed edge found")
    for sequence in LOW3_SEQUENCES:
        check(selected[sequence].active_vertices == 3, f"sequence {sequence} active count drift")
    check(selected[LOW4_SEQUENCE].active_vertices == 4, "active-4 sequence drift")
    active11 = selected[ACTIVE11_SEQUENCE]
    check(active11.active_vertices == N, "active-11 sequence drift")
    check(has_cycle(active11), "selected active-11 record is no longer cyclic")

    matrices = {sequence: matrix_from_record(record) for sequence, record in selected.items()}
    identity_word = word_for_order(matrices[ACTIVE11_SEQUENCE], tuple(range(N)))
    canonical = canonicalize(identity_word)
    check(canonical is not None, "active-11 identity word vanished")
    supported_direction, identity_scale, identity_negative = canonical
    check(active_direction(supported_direction), "identity direction is not chamber-active")
    check(identity_scale <= DEGREE and identity_negative, "identity-word sign/scale control drift")
    outside_direction = (0, 1, -6, 5, 0, 0, 0, 0, 0, 0, 0)
    inactive_direction = (0, 1, -1, 0, 0, 0, 0, 0, 0, 0, 0)
    check(active_direction(outside_direction), "outside control must be active")
    check(not active_direction(inactive_direction), "inactive-direction control became active")

    literal = literal_full_permutation_scan(
        matrices[ACTIVE11_SEQUENCE],
        supported_direction,
        outside_direction,
        inactive_direction,
        batch_size,
    )
    counts3 = literal["counts3"]
    counts4 = literal["counts4"]
    total = math.factorial(N)
    check(int(counts3.sum()) == total == int(counts4.sum()), "literal signature total drift")
    valid3 = counts3[counts3 != 0]
    valid4 = counts4[counts4 != 0]
    check(len(valid3) == math.factorial(N) // math.factorial(N - 3), "3-injection census drift")
    check(len(valid4) == math.factorial(N) // math.factorial(N - 4), "4-injection census drift")
    check(np.all(valid3 == math.factorial(N - 3)), "inactive 8! multiplicity failed literally")
    check(np.all(valid4 == math.factorial(N - 4)), "inactive 7! multiplicity failed literally")

    low_results = []
    low_forms: dict[int, NormalForm] = {}
    for sequence in LOW3_SEQUENCES + (LOW4_SEQUENCE,):
        record = selected[sequence]
        matrix = matrices[sequence]
        counts = counts3 if record.active_vertices == 3 else counts4
        form = normal_form_from_literal_signatures(matrix, counts, record.active_vertices)
        low_forms[sequence] = form
        check(form.total_permutations == total, f"sequence {sequence}: literal total drift")
        dp_correction = three_state_linear_correction(matrix)
        check(dp_correction == form.correction, f"sequence {sequence}: three-state correction mismatch")
        for direction, expected in form.hinges.items():
            observed, _ = hinge_coordinate_price(matrix, direction)
            check(observed == expected, f"sequence {sequence}: coordinate price mismatch at {direction}")
            injection_only, _ = raw_coordinate_price(matrix, direction, restore_inactive_labels=False)
            check(
                injection_only * math.factorial(N - record.active_vertices) == expected,
                f"sequence {sequence}: inactive factorial mismatch",
            )
            check(injection_only != expected, f"sequence {sequence}: missing-factorial mutant escaped")
        inactive_control = None
        if form.inactive_raw:
            inactive_direction_low, inactive_expected = next(iter(form.inactive_raw.items()))
            inactive_raw_price, _ = raw_coordinate_price(matrix, inactive_direction_low)
            inactive_filtered_price, _ = hinge_coordinate_price(matrix, inactive_direction_low)
            inactive_injection_only, _ = raw_coordinate_price(
                matrix, inactive_direction_low, restore_inactive_labels=False
            )
            check(
                inactive_raw_price == inactive_expected,
                f"sequence {sequence}: inactive raw-coordinate mismatch",
            )
            check(
                inactive_filtered_price == 0,
                f"sequence {sequence}: chamber-inactive coordinate survived",
            )
            check(
                inactive_injection_only * math.factorial(N - record.active_vertices)
                == inactive_expected,
                f"sequence {sequence}: inactive raw factorial mismatch",
            )
            inactive_control = {
                "direction": list(inactive_direction_low),
                "raw_coordinate": inactive_raw_price,
                "hinge_coordinate": inactive_filtered_price,
            }
        negated = tuple(tuple(-value for value in row) for row in matrix)
        check(
            three_state_linear_correction(negated) == form.correction,
            f"sequence {sequence}: loopless branch-swap correction mismatch",
        )
        for direction, expected in form.hinges.items():
            swapped, _ = hinge_coordinate_price(negated, direction)
            check(swapped == expected, f"sequence {sequence}: branch-swap hinge mismatch")
        relabel = tuple(reversed(range(record.active_vertices)))
        relabelled = relabel_matrix(matrix, relabel)
        check(
            three_state_linear_correction(relabelled) == form.correction,
            f"sequence {sequence}: vertex-relabel correction mismatch",
        )
        for direction, expected in form.hinges.items():
            relabelled_price, _ = hinge_coordinate_price(relabelled, direction)
            check(relabelled_price == expected, f"sequence {sequence}: relabel hinge mismatch")
        low_results.append(
            {
                "sequence": sequence,
                "active_vertices": record.active_vertices,
                "signed_mass": record.signed_mass,
                "hinge_direction_count": len(form.hinges),
                "inactive_direction_count": len(form.inactive_raw),
                "hinge_sha256": direction_digest(form.hinges),
                "correction": list(form.correction),
                "negative_permutations": form.negative_permutations,
                "zero_permutations": form.zero_permutations,
                "multiedge": any(abs(value) > 1 for row in matrix for value in row),
                "inactive_filter_control": inactive_control,
            }
        )

    check(low_results[1]["multiedge"] and low_results[2]["multiedge"], "multiedge controls drifted")

    # Common loopless padding is absent from W but contributes a universal
    # five-edge base after full orbit symmetrization.  Compare two concretely
    # different paddings, one involving a residual-inactive vertex.
    padding_record = selected[5341]
    padding_form = low_forms[5341]
    point = (-7, -4, -2, -1, 0, 2, 3, 5, 8, 13, 21)
    padding_a = ((0, 1), (0, 1), (0, 1), (0, 1))
    padding_b = ((0, 3), (1, 3), (2, 3), (0, 2))
    literal_padding_a = literal_atom_value_from_signatures(padding_record, counts4, point, padding_a)
    literal_padding_b = literal_atom_value_from_signatures(padding_record, counts4, point, padding_b)
    literal_padding_swap = literal_atom_value_from_signatures(
        padding_record, counts4, point, padding_b, swap_branches=True
    )
    normal_value = normal_form_value(padding_form, point)
    check(literal_padding_a == normal_value, "common padding A disagrees with normal form")
    check(literal_padding_b == normal_value, "common padding B disagrees with normal form")
    check(literal_padding_swap == normal_value, "literal branch swap changed atom")
    check(
        normal_form_value(padding_form, point, include_correction=False) != normal_value,
        "orientation-correction omission mutant escaped",
    )

    active11_price, active11_dp_scales = hinge_coordinate_price(
        matrices[ACTIVE11_SEQUENCE], supported_direction
    )
    literal_supported_scales = histogram_to_dict(literal["supported_hist"])
    literal_active11_price = sum(abs(int(scale)) * count for scale, count in literal_supported_scales.items())
    check(active11_price == literal_active11_price, "active-11 supported coordinate mismatch")
    for scale in range(-DEGREE, DEGREE + 1):
        if scale:
            check(
                active11_dp_scales[scale] * math.factorial(N - N)
                == literal_supported_scales.get(str(scale), 0),
                f"active-11 signed-scale mismatch at {scale}",
            )
    active11_correction = three_state_linear_correction(matrices[ACTIVE11_SEQUENCE])
    literal_correction = tuple(int(value) for value in literal["correction"])
    literal_swapped_correction = tuple(int(value) for value in literal["swapped_correction"])
    check(active11_correction == literal_correction, "active-11 three-state correction mismatch")
    check(literal_swapped_correction == literal_correction, "active-11 literal branch swap mismatch")
    check(tuple(int(value) for value in literal["raw_sum"]) == (0,) * N, "full raw orbit is not zero")
    outside_price, outside_dp_scales = hinge_coordinate_price(
        matrices[ACTIVE11_SEQUENCE], outside_direction
    )
    check(outside_price == 0, "outside-support DP direction was nonzero")
    check(not histogram_to_dict(literal["outside_hist"]), "outside-support literal direction was nonzero")
    check(not any(outside_dp_scales.values()), "outside-support signed scale was nonzero")
    inactive_hinge_price, _ = hinge_coordinate_price(matrices[ACTIVE11_SEQUENCE], inactive_direction)
    check(inactive_hinge_price == 0, "inactive direction survived hinge filtering")

    active11_relabelled = relabel_matrix(matrices[ACTIVE11_SEQUENCE], tuple((7 * v) % N for v in range(N)))
    relabelled_price, _ = hinge_coordinate_price(active11_relabelled, supported_direction)
    check(relabelled_price == active11_price, "active-11 vertex relabel changed coordinate")
    check(
        three_state_linear_correction(active11_relabelled) == active11_correction,
        "active-11 vertex relabel changed correction",
    )
    active11_negated = tuple(tuple(-value for value in row) for row in matrices[ACTIVE11_SEQUENCE])
    negated_price, _ = hinge_coordinate_price(active11_negated, supported_direction)
    check(negated_price == active11_price, "active-11 branch swap changed coordinate")
    check(
        three_state_linear_correction(active11_negated) == active11_correction,
        "active-11 branch swap changed loopless correction",
    )
    mutant = find_valid_edge_sign_mutant(
        active11, active11_correction, supported_direction, active11_price
    )

    result = {
        "schema": "g0117-independent-coordinate-pricer-review-v1",
        "verdict": "PASS_BOUNDED",
        "input": str(input_path.relative_to(PROJECT_ROOT)),
        "input_sha256": input_sha256,
        "census": census,
        "derivation_guards": {
            "inactive_factorial": "literal 8! and 7! signature multiplicities",
            "scale_range": [-DEGREE, DEGREE],
            "orientation": "first-nonzero canonicalization plus full-word linear correction",
            "active_condition": "some proper prefix sum of first-positive d is negative",
            "linear_dp_payload": "(count, 11-coordinate prefix sums) for each mask/sign state",
        },
        "low_active_literal_checks": low_results,
        "common_padding_control": {
            "sequence": 5341,
            "point": list(point),
            "padding_a_value": literal_padding_a,
            "padding_b_value": literal_padding_b,
            "branch_swap_value": literal_padding_swap,
            "normal_form_value": normal_value,
        },
        "active11_literal_check": {
            "sequence": ACTIVE11_SEQUENCE,
            "cyclic": True,
            "identity_word": list(identity_word),
            "supported_direction": list(supported_direction),
            "literal_signed_scale_counts": literal_supported_scales,
            "coordinate": active11_price,
            "correction": list(active11_correction),
            "outside_direction": list(outside_direction),
            "outside_coordinate": outside_price,
            "inactive_direction": list(inactive_direction),
            "inactive_raw_signed_scale_counts": histogram_to_dict(literal["inactive_hist"]),
            "inactive_hinge_coordinate": inactive_hinge_price,
        },
        "edge_sign_mutant_rejected": mutant,
        "literal_permutations_visited": total,
        "literal_scan_elapsed_seconds": round(float(literal["elapsed_seconds"]), 3),
        "residual_doubts": [
            "This validates the recurrence and selected real records, not an unseen G-0117 implementation.",
            "The review does not price all directions of all 163,740 records.",
            "A count-only three-state DP would be wrong; the vector-sum payload is load-bearing.",
        ],
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    with result_path.open("x", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2, sort_keys=True)
        handle.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--batch-size", type=int, default=250_000)
    args = parser.parse_args()
    check(args.batch_size > 0, "batch size must be positive")
    check(args.result.resolve().parent == HERE, "result must stay in the reserved review directory")
    started = time.monotonic()
    result = run(args.input.resolve(), args.result.resolve(), args.batch_size)
    elapsed = time.monotonic() - started
    print(
        f"PASS_BOUNDED: {result['literal_permutations_visited']:,} literal permutations; "
        f"wall {elapsed:.1f}s; wrote {args.result}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:  # fail closed and leave a useful terminal diagnosis
        print(f"FAIL: {type(error).__name__}: {error}", file=sys.stderr, flush=True)
        raise
