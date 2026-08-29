#!/usr/bin/env python3
"""Independent tiny-n adversarial checks for the read-only G-0049 audit.

This intentionally evaluates pair atoms by literal coordinate permutations.
It imports G-0049 only for the implementation under test.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations_with_replacement, permutations, product
import importlib.util
import json
from math import factorial, gcd
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[3]
SUBJECT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
SPEC = importlib.util.spec_from_file_location("g0049_subject", SUBJECT)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("cannot load G-0049 subject")
G = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = G
SPEC.loader.exec_module(G)


def independent_signed_word(pair, ordering, n):
    """Right-minus-left word, with ordering listing labels by increasing rank."""

    rank = {vertex: r for r, vertex in enumerate(ordering)}
    word = [0] * n
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_u, one_v in side:
            u, v = one_u - 1, one_v - 1
            high = u if rank[u] >= rank[v] else v
            word[rank[high]] += sign
    return tuple(word)


def independent_histogram(pair, n):
    output = defaultdict(int)
    for ordering in permutations(range(n)):
        output[independent_signed_word(pair, ordering, n)] += 1
    return dict(output)


def direct_atom(pair, ordered_x):
    """Literal unnormalised S_n symmetrisation on an ordered input."""

    n = len(ordered_x)
    total = 0
    for label_to_rank in permutations(range(n)):
        branches = []
        for side in pair:
            branch = 0
            for one_u, one_v in side:
                u, v = one_u - 1, one_v - 1
                branch += max(ordered_x[label_to_rank[u]], ordered_x[label_to_rank[v]])
            branches.append(branch)
        total += max(branches)
    return total


def normal_form_value(column, ordered_x):
    total = sum(a * x for a, x in zip(column.linear, ordered_x, strict=True))
    for direction, coefficient in column.hinges.items():
        total += coefficient * max(
            0, sum(a * x for a, x in zip(direction, ordered_x, strict=True))
        )
    return total


def independent_signed_key(pair, n):
    weights = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_u, one_v in side:
            u, v = one_u - 1, one_v - 1
            weights[u][v] += sign
            if u != v:
                weights[v][u] += sign
    flat = tuple(value for row in weights for value in row)
    return min(flat, tuple(-value for value in flat))


def loopless_multisets(n, k):
    edges = [(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1)]
    return list(combinations_with_replacement(edges, k))


def assert_loopless_semantics():
    cases = 0
    cache_groups = defaultdict(list)
    cache_columns = defaultdict(list)
    probes = {
        2: [(-3, 4), (0, 1)],
        3: [(-4, 1, 7), (0, 2, 3), (-2, -2, 5)],
        4: [(-5, -1, 2, 8), (0, 1, 3, 4), (-3, -3, 1, 6)],
    }
    for n, k in ((2, 1), (3, 1), (3, 2), (4, 1), (4, 2)):
        branches = loopless_multisets(n, k)
        for left in branches:
            for right in branches:
                pair = (left, right)
                observed_histogram = G.direction_histogram(pair, n)
                expected_histogram = independent_histogram(pair, n)
                if observed_histogram != expected_histogram:
                    raise AssertionError(("loopless_histogram", n, pair))
                column = G.exact_semantic_column(pair, n)
                for x in probes[n]:
                    observed = normal_form_value(column, x)
                    expected = direct_atom(pair, x)
                    if observed != expected:
                        raise AssertionError(("loopless_normal_form", n, pair, x, observed, expected))
                cache_groups[(n, k, independent_signed_key(pair, n))].append(
                    tuple(direct_atom(pair, x) for x in probes[n])
                )
                cache_columns[(n, k, independent_signed_key(pair, n))].append(
                    (column.linear, tuple(sorted(column.hinges.items())))
                )
                cases += 1
    for key, profiles in cache_groups.items():
        if len(set(profiles)) != 1:
            raise AssertionError(("loopless_signed_W_cache", key))
        if len(set(cache_columns[key])) != 1:
            raise AssertionError(("loopless_signed_W_normal_form_cache", key))
    return cases, len(cache_groups)


def assert_random_larger_n_semantics(seed=20260829):
    rng = random.Random(seed)
    counts = {5: 120, 6: 40, 7: 12}
    for n, count in counts.items():
        edges = [(u, v) for u in range(1, n + 1) for v in range(u + 1, n + 1)]
        probes = [tuple(range(-n, n, 2))[:n], tuple(range(n))]
        for _ in range(count):
            k = rng.randrange(1, min(5, len(edges)) + 1)
            pair = (
                tuple(rng.choice(edges) for _ in range(k)),
                tuple(rng.choice(edges) for _ in range(k)),
            )
            if G.direction_histogram(pair, n) != independent_histogram(pair, n):
                raise AssertionError(("random_larger_n_histogram", n, pair))
            column = G.exact_semantic_column(pair, n)
            for x in probes:
                if normal_form_value(column, x) != direct_atom(pair, x):
                    raise AssertionError(("random_larger_n_normal_form", n, pair, x))
    return counts


def assert_orientation_criterion():
    checked = 0
    for direction in product(range(-3, 4), repeat=4):
        if not any(direction) or sum(direction) != 0:
            continue
        scale = gcd(*(abs(value) for value in direction))
        primitive = tuple(value // scale for value in direction)
        first = next(value for value in primitive if value)
        if first < 0:
            primitive = tuple(-value for value in primitive)
        predicted_nonpositive = G.nonpositive_on_ordered_cone(primitive)
        # Gap vectors generate the ordered cone modulo its all-ones line.
        prefix = 0
        prefixes = []
        for value in primitive[:-1]:
            prefix += value
            prefixes.append(prefix)
        independently_nonpositive = all(value >= 0 for value in prefixes)
        if predicted_nonpositive != independently_nonpositive:
            raise AssertionError(("orientation_criterion", primitive))
        checked += 1
    return checked


def assert_crt_projection(seed=49049, count=10_000):
    rng = random.Random(seed)
    p1, p2 = G.PRIMES
    modulus = p1 * p2
    aggregate = 0
    sum1 = 0
    sum2 = 0
    for _ in range(count):
        a = rng.randrange(p1)
        b = rng.randrange(p2)
        weight = rng.randrange(-10**8, 10**8)
        combined = G.crt_pair(a, b)
        if combined % p1 != a or combined % p2 != b:
            raise AssertionError("CRT coordinate roundtrip")
        aggregate = (aggregate + combined * weight) % modulus
        sum1 = (sum1 + a * weight) % p1
        sum2 = (sum2 + b * weight) % p2
    if aggregate % p1 != sum1 or aggregate % p2 != sum2:
        raise AssertionError("CRT aggregation/projection")
    return count


def loop_scope_counterexamples():
    # The DP-under-test omits diagonal W[v,v] from every emitted rank word.
    pair = (((1, 1),), ((2, 2),))
    observed = G.direction_histogram(pair, 3)
    expected = independent_histogram(pair, 3)
    x = (0, 1, 3)
    column = G.exact_semantic_column(pair, 3)
    observed_value = normal_form_value(column, x)
    expected_value = direct_atom(pair, x)
    if observed == expected or observed_value == expected_value:
        raise AssertionError("expected diagonal-DP counterexample did not fire")

    # Same signed W=0, equal branch size, but differing loop/nonloop common base.
    common_loop = (((1, 1),), ((1, 1),))
    common_edge = (((1, 2),), ((1, 2),))
    if independent_signed_key(common_loop, 3) != independent_signed_key(common_edge, 3):
        raise AssertionError("zero-W cache setup failed")
    loop_value = direct_atom(common_loop, x)
    edge_value = direct_atom(common_edge, x)
    if loop_value == edge_value:
        raise AssertionError("expected signed-W loop-base counterexample did not fire")
    return {
        "diagonal_pair": pair,
        "subject_histogram": {str(key): value for key, value in sorted(observed.items())},
        "reference_histogram": {str(key): value for key, value in sorted(expected.items())},
        "probe": x,
        "subject_normal_form_value": observed_value,
        "literal_atom_value": expected_value,
        "zero_W_common_loop_value": loop_value,
        "zero_W_common_nonloop_value": edge_value,
    }


def main():
    loopless_cases, cache_groups = assert_loopless_semantics()
    random_larger_n_cases = assert_random_larger_n_semantics()
    orientation_cases = assert_orientation_criterion()
    crt_cases = assert_crt_projection()
    result = {
        "result": "PASS_FOR_FROZEN_LOOPLESS_SCOPE_WITH_EXPECTED_GENERIC_LOOP_FAILURE",
        "subject": str(SUBJECT.relative_to(ROOT)),
        "loopless_pair_cases_exact": loopless_cases,
        "loopless_signed_W_cache_groups": cache_groups,
        "random_larger_n_pair_cases": random_larger_n_cases,
        "orientation_directions_checked": orientation_cases,
        "CRT_coordinates_aggregated": crt_cases,
        "loop_scope_counterexamples": loop_scope_counterexamples(),
    }
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
