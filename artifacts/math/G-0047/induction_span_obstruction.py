#!/usr/bin/env python3
"""Exact obstruction to building MAX_N only from lower-MAX induction.

Let

    F_m^(N)(x) = sum_{|S|=m} max_{i in S} x_i.

Inducing any fully symmetric exact MAX_m identity from S_m to S_N produces a
scalar multiple of F_m^(N).  Adding the same pairwise-max edge to both branches
of an atom contributes only F_2^(N); a common loop contributes only F_1^(N).
This program proves over Q that MAX_N is not in the span of F_1,...,F_{N-1}.

It also supplies two machinery controls:

* an independent subset-DP normal-form replay of the frozen MAX5, MAX6, and
  MAX10 certificates (with a one-coefficient mutant required to fail); and
* an exhaustive exact test of all 12,459 balanced full-support coloured-tree
  atoms at N=11 for the much stronger property that a *single* orbit atom has
  no non-braid kink on the ordered chamber.

No-claim: this rules out lower-subset induction/common-padding mechanisms and
single all-tree orbit shortcuts.  It does not rule out signed cancellation
between topology-changing atoms, the full degree-five ansatz, or arbitrary
two-hidden-layer ReLU representations.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations, permutations
import json
from math import comb, factorial, gcd, lcm
import os
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CERTIFICATES = {
    5: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_5_2.json",
    6: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json",
    10: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json",
}
EXPECTED_CERTIFICATE_HASHES = {
    5: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    6: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    10: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
}
TREE_UNIVERSE = ROOT / "artifacts/math/G-0023/all_tree_universe_v1.json"
EXPECTED_TREE_UNIVERSE_HASH = (
    "7dc597d7cefd514ca3d0b49887846cc7bb53a3fc12096217f70887ad12c4dfa3"
)
SIGNED_STREAM = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
EXPECTED_SIGNED_STREAM_HASH = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
DEFAULT_OUTPUT = HERE / "induction_span_obstruction_v1.json.gz"
SCHEMA = "max11-g0047-induction-span-obstruction-v1"

Edge = tuple[int, int]
Branch = tuple[Edge, ...]
Pair = tuple[Branch, Branch]
Vector = tuple[int, ...]
TKey = tuple[Vector, Vector]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def parse_pair(raw: object, n: int) -> Pair:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("pair must contain exactly two branches")
    branches: list[Branch] = []
    for raw_branch in raw:
        if not isinstance(raw_branch, list):
            raise ValueError("branch must be a list")
        branch: list[Edge] = []
        for raw_edge in raw_branch:
            if not isinstance(raw_edge, list) or len(raw_edge) != 2:
                raise ValueError("edge must contain two endpoints")
            u, v = (int(raw_edge[0]) - 1, int(raw_edge[1]) - 1)
            if not (0 <= u <= v < n):
                raise ValueError(f"invalid one-based certificate edge {raw_edge}")
            branch.append((u, v))
        branches.append(tuple(branch))
    if len(branches[0]) != len(branches[1]):
        raise ValueError("branches have different degrees")
    return branches[0], branches[1]


def load_certificate(n: int) -> tuple[int, list[tuple[Pair, Fraction]], dict[str, object]]:
    path = CERTIFICATES[n]
    observed_hash = sha256_path(path)
    if observed_hash != EXPECTED_CERTIFICATE_HASHES[n]:
        raise ValueError(f"certificate {n} hash drift: {observed_hash}")
    document = json.loads(path.read_text(encoding="utf-8"))
    if int(document.get("n", -1)) != n or not isinstance(document.get("terms"), list):
        raise ValueError(f"malformed MAX{n} certificate")
    terms: list[tuple[Pair, Fraction]] = []
    degree: int | None = None
    for raw_term in document["terms"]:
        pair = parse_pair(raw_term["pair"], n)
        if degree is None:
            degree = len(pair[0])
        if len(pair[0]) != degree:
            raise ValueError("mixed atom degrees")
        terms.append((pair, Fraction(raw_term["coefficient"])))
    if degree is None:
        raise ValueError("empty certificate")
    coefficient_sum = sum((coefficient for _, coefficient in terms), Fraction())
    expected_sum = Fraction(1, degree * factorial(n))
    if coefficient_sum != expected_sum:
        raise AssertionError((n, coefficient_sum, expected_sum))
    return degree, terms, {
        "path": str(path.relative_to(ROOT)),
        "sha256": observed_hash,
        "n": n,
        "degree": degree,
        "term_count": len(terms),
        "coefficient_sum": str(coefficient_sum),
        "coefficient_sum_expected_from_all_equal_input": str(expected_sum),
    }


def branch_data(branch: Branch, n: int) -> tuple[list[int], list[list[int]]]:
    loops = [0] * n
    adjacency = [[0] * n for _ in range(n)]
    for u, v in branch:
        if u == v:
            loops[u] += 1
        else:
            adjacency[u][v] += 1
            adjacency[v][u] += 1
    return loops, adjacency


def permutation_t_counter_dp(pair: Pair, n: int) -> Counter[TKey]:
    """Count every ordered-cone branch-vector pair without enumerating n! orders.

    At a subset S of already placed labels, adding v appends the number of
    branch edges whose later endpoint is v.  Equal prefix words coalesce.
    """

    prepared = [branch_data(branch, n) for branch in pair]
    layers: dict[int, dict[int, Counter[tuple[Vector, Vector]]]] = {
        0: {0: Counter({((), ()): 1})}
    }
    full_mask = (1 << n) - 1
    for rank in range(n):
        current = layers.pop(rank)
        following: dict[int, Counter[tuple[Vector, Vector]]] = {}
        for subset, prefixes in current.items():
            remaining = full_mask ^ subset
            for vertex in range(n):
                if not ((remaining >> vertex) & 1):
                    continue
                values = []
                for loops, adjacency in prepared:
                    value = loops[vertex]
                    value += sum(
                        adjacency[vertex][other]
                        for other in range(n)
                        if (subset >> other) & 1
                    )
                    values.append(value)
                extended = following.setdefault(subset | (1 << vertex), Counter())
                for (left, right), multiplicity in prefixes.items():
                    extended[(left + (values[0],), right + (values[1],))] += multiplicity
        layers[rank + 1] = following
    final = layers[n].get(full_mask)
    if final is None:
        raise AssertionError("subset DP did not reach the full label set")
    result: Counter[TKey] = Counter()
    for (left, right), multiplicity in final.items():
        key = (left, right) if left <= right else (right, left)
        result[key] += multiplicity
    if sum(result.values()) != factorial(n):
        raise AssertionError("subset DP permutation census mismatch")
    return result


def permutation_t_counter_bruteforce(pair: Pair, n: int) -> Counter[TKey]:
    result: Counter[TKey] = Counter()
    for order in permutations(range(n)):
        position = [0] * n
        for rank, label in enumerate(order):
            position[label] = rank
        vectors = []
        for branch in pair:
            vector = [0] * n
            for u, v in branch:
                vector[max(position[u], position[v])] += 1
            vectors.append(tuple(vector))
        left, right = vectors
        result[(left, right) if left <= right else (right, left)] += 1
    return result


def primitive_normal_form(counter: Counter[TKey], n: int) -> tuple[Vector, Counter[Vector]]:
    linear = [0] * n
    hinges: Counter[Vector] = Counter()
    for (base, other), multiplicity in counter.items():
        if base == other:
            for index, value in enumerate(base):
                linear[index] += multiplicity * value
            continue
        direction = tuple(b - a for a, b in zip(base, other, strict=True))
        if sum(direction):
            raise AssertionError("equal-degree branch direction does not sum to zero")
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            # direction.x <= 0 on x_1<=...<=x_n, so base dominates.
            for index, value in enumerate(base):
                linear[index] += multiplicity * value
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        if divisor == 0:
            raise AssertionError("zero direction escaped equality branch")
        primitive = tuple(value // divisor for value in direction)
        for index, value in enumerate(base):
            linear[index] += multiplicity * value
        hinges[primitive] += multiplicity * divisor
    return tuple(linear), hinges


def atom_form_worker(payload: tuple[int, Pair, int]) -> tuple[int, Vector, dict[Vector, int], int]:
    index, pair, n = payload
    counter = permutation_t_counter_dp(pair, n)
    linear, hinges = primitive_normal_form(counter, n)
    return index, linear, dict(hinges), len(counter)


def certificate_replay(n: int, workers: int) -> dict[str, object]:
    degree, terms, metadata = load_certificate(n)
    denominators = [coefficient.denominator for _, coefficient in terms]
    common_denominator = 1
    for denominator in denominators:
        common_denominator = lcm(common_denominator, denominator)
    integer_coefficients = [
        coefficient.numerator * (common_denominator // coefficient.denominator)
        for _, coefficient in terms
    ]

    brute_force_match = None
    if n in (5, 6):
        brute_force_match = True
        for pair, _ in terms:
            if permutation_t_counter_dp(pair, n) != permutation_t_counter_bruteforce(pair, n):
                brute_force_match = False
                break
        if not brute_force_match:
            raise AssertionError(f"MAX{n} subset DP disagrees with direct n! enumeration")

    payloads = [(index, pair, n) for index, (pair, _) in enumerate(terms)]
    forms: list[tuple[Vector, dict[Vector, int], int] | None] = [None] * len(terms)
    if workers > 1 and len(payloads) > 8:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            futures = [pool.submit(atom_form_worker, payload) for payload in payloads]
            completed = 0
            for future in as_completed(futures):
                index, linear, hinges, t_count = future.result()
                forms[index] = (linear, hinges, t_count)
                completed += 1
                if completed % 50 == 0 or completed == len(payloads):
                    print(
                        f"G0047_CERT MAX{n} terms={completed}/{len(payloads)}",
                        file=sys.stderr,
                        flush=True,
                    )
    else:
        for payload in payloads:
            index, linear, hinges, t_count = atom_form_worker(payload)
            forms[index] = (linear, hinges, t_count)

    total_linear = [0] * n
    total_hinges: dict[Vector, int] = {}
    union_hinges: set[Vector] = set()
    t_key_counts: list[int] = []
    for coefficient, form in zip(integer_coefficients, forms, strict=True):
        if form is None:
            raise AssertionError("missing worker result")
        linear, hinges, t_count = form
        t_key_counts.append(t_count)
        for index, value in enumerate(linear):
            total_linear[index] += coefficient * value
        union_hinges.update(hinges)
        for direction, value in hinges.items():
            updated = total_hinges.get(direction, 0) + coefficient * value
            if updated:
                total_hinges[direction] = updated
            else:
                total_hinges.pop(direction, None)
    target = [0] * (n - 1) + [common_denominator]
    verified = total_linear == target and not total_hinges
    if not verified:
        raise AssertionError(
            f"MAX{n} exact replay failed: linear={total_linear}, hinges={len(total_hinges)}"
        )

    first_form = forms[0]
    if first_form is None:
        raise AssertionError("missing first term form")
    mutation_linear = list(first_form[0])
    mutation_hinges = first_form[1]
    mutation_rejected = any(mutation_linear) or bool(mutation_hinges)
    if not mutation_rejected:
        raise AssertionError("one-coefficient mutation was not detected")

    return {
        **metadata,
        "normalization": f"integer numerator over common denominator {common_denominator}",
        "exact_subset_dp_replay": "PASS",
        "direct_n_factorial_enumeration_matches_dp": brute_force_match,
        "combined_linear_vector": [str(Fraction(value, common_denominator)) for value in total_linear],
        "combined_nonzero_hinge_count": len(total_hinges),
        "union_hinge_direction_count_before_signed_cancellation": len(union_hinges),
        "per_term_distinct_T_key_min": min(t_key_counts),
        "per_term_distinct_T_key_max": max(t_key_counts),
        "one_coefficient_plus_1_over_common_denominator_mutant_rejected": mutation_rejected,
        "mutant_nonzero_linear_count": sum(value != 0 for value in mutation_linear),
        "mutant_nonzero_hinge_count": len(mutation_hinges),
    }


def subset_max_vector(n: int, m: int) -> Vector:
    # Rank r is one-based on x_(1)<=...<=x_(n).
    return tuple(comb(rank - 1, m - 1) if rank >= m else 0 for rank in range(1, n + 1))


def alternating_invariant(n: int) -> Vector:
    return tuple((-1) ** (n - rank) * comb(n - 1, rank - 1) for rank in range(1, n + 1))


def dot(left: Iterable[int], right: Iterable[int]) -> int:
    return sum(a * b for a, b in zip(left, right, strict=True))


def rank_over_q(columns: Sequence[Sequence[int]]) -> int:
    if not columns:
        return 0
    matrix = [[Fraction(value) for value in row] for row in zip(*columns, strict=True)]
    row_count = len(matrix)
    column_count = len(matrix[0])
    rank = 0
    for column in range(column_count):
        pivot = next((row for row in range(rank, row_count) if matrix[row][column]), None)
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        scale = matrix[rank][column]
        matrix[rank] = [value / scale for value in matrix[rank]]
        for row in range(row_count):
            if row == rank or matrix[row][column] == 0:
                continue
            scale = matrix[row][column]
            matrix[row] = [
                value - scale * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[rank], strict=True)
            ]
        rank += 1
    return rank


def induction_obstruction(n: int = 11) -> dict[str, object]:
    vectors = [subset_max_vector(n, m) for m in range(1, n)]
    target = (0,) * (n - 1) + (1,)
    witness = alternating_invariant(n)
    pairings = [dot(witness, vector) for vector in vectors]
    if any(pairings) or dot(witness, target) != 1:
        raise AssertionError("alternating-binomial annihilator identity failed")
    rank = rank_over_q(vectors)
    augmented_rank = rank_over_q(vectors + [target])
    if rank != n - 1 or augmented_rank != n:
        raise AssertionError("subset-max span rank mismatch")

    five_common_loops = tuple(5 * factorial(n - 1) * value for value in vectors[0])
    five_common_nonloops = tuple(10 * factorial(n - 2) * value for value in vectors[1])
    if dot(witness, five_common_loops) or dot(witness, five_common_nonloops):
        raise AssertionError("zero-signed common bases escaped the invariant")

    general_checks = []
    for size in range(2, n + 1):
        local_witness = alternating_invariant(size)
        local_pairings = [
            dot(local_witness, subset_max_vector(size, m))
            for m in range(1, size)
        ]
        target_pairing = dot(local_witness, (0,) * (size - 1) + (1,))
        if any(local_pairings) or target_pairing != 1:
            raise AssertionError(f"general binomial check failed at N={size}")
        general_checks.append(
            {"N": size, "annihilated_F_count": size - 1, "MAX_N_pairing": 1}
        )

    return {
        "N": n,
        "ordered_chamber": "x_(1)<=...<=x_(N)",
        "F_m_vectors": [
            {"m": m, "coefficients": list(vector), "invariant_pairing": pairing}
            for m, vector, pairing in zip(range(1, n), vectors, pairings, strict=True)
        ],
        "alternating_binomial_invariant": list(witness),
        "formula": "Lambda_r=(-1)^(N-r)*binom(N-1,r-1)",
        "binomial_identity": (
            "sum_{r=m}^N (-1)^(N-r) binom(N-1,r-1) binom(r-1,m-1)=0 for m<N"
        ),
        "subset_max_span_rank_over_Q": rank,
        "rank_after_adjoining_MAX_N": augmented_rank,
        "MAX_N_in_subset_max_span": False,
        "MAX_N_invariant_pairing": dot(witness, target),
        "induction_identity": (
            "Ind_{S_m}^{S_N}(MAX_m)=(N-m)! F_m^(N) under unnormalised full symmetrisation"
        ),
        "common_padding_identity": (
            "common loops contribute (N-1)! F_1 per occurrence; common nonloops contribute "
            "2(N-2)! F_2 per occurrence"
        ),
        "five_common_loop_base_vector": list(five_common_loops),
        "five_common_nonloop_base_vector": list(five_common_nonloops),
        "both_G0038_zero_signed_bases_annihilated": True,
        "general_exact_checks": general_checks,
        "conclusion": (
            "No linear combination of induced lower-MAX identities, including arbitrary "
            "Möbius/inclusion-exclusion coefficients and common loop/nonloop padding, equals MAX_N."
        ),
    }


def comparable_opposite_witness(pair: Pair, n: int) -> tuple[int, int, int, int] | None:
    signed_edges: list[tuple[int, int, int]] = []
    for sign, branch in ((-1, pair[0]), (1, pair[1])):
        signed_edges.extend((u, v, sign) for u, v in branch)
    values = []
    for subset in range(1 << n):
        total = 0
        for u, v, sign in signed_edges:
            if ((subset >> u) & 1) and ((subset >> v) & 1):
                total += sign
        values.append(total)
    for subset, first in enumerate(values):
        if not first:
            continue
        remaining = ((1 << n) - 1) ^ subset
        extra = remaining
        while True:
            superset = subset | extra
            second = values[superset]
            if first * second < 0:
                return subset, superset, first, second
            if extra == 0:
                break
            extra = (extra - 1) & remaining
    return None


def classify_all_tree_atoms() -> dict[str, object]:
    observed_hash = sha256_path(TREE_UNIVERSE)
    if observed_hash != EXPECTED_TREE_UNIVERSE_HASH:
        raise ValueError(f"all-tree universe hash drift: {observed_hash}")
    universe = json.loads(TREE_UNIVERSE.read_text(encoding="utf-8"))
    subject = universe.get("n11_subject")
    if (
        universe.get("schema") != "max11-g0023-all-balanced-coloured-trees-v1"
        or universe.get("result") != "PASS"
        or not isinstance(subject, dict)
        or int(subject.get("quotient_class_count", -1)) != 12_459
    ):
        raise ValueError("malformed frozen all-tree universe")
    raw_representatives = subject.get("representatives")
    if not isinstance(raw_representatives, list) or len(raw_representatives) != 12_459:
        raise ValueError("all-tree representative count mismatch")
    n = 11
    representatives: list[Pair] = []
    for raw_pair in raw_representatives:
        branches = []
        for raw_branch in raw_pair:
            branch = tuple((int(edge[0]), int(edge[1])) for edge in raw_branch)
            if len(branch) != 5 or any(not (0 <= u < v < n) for u, v in branch):
                raise ValueError("malformed all-tree representative")
            branches.append(branch)
        representatives.append((branches[0], branches[1]))

    edges = list(combinations(range(n), 2))
    edge_index = {edge: index for index, edge in enumerate(edges)}
    signed = np.zeros((len(representatives), len(edges)), dtype=np.int8)
    for row, pair in enumerate(representatives):
        for edge in pair[0]:
            signed[row, edge_index[edge]] -= 1
        for edge in pair[1]:
            signed[row, edge_index[edge]] += 1
    subsets = np.arange(1 << n, dtype=np.uint16)
    internal = np.zeros((len(edges), 1 << n), dtype=np.int8)
    for row, (u, v) in enumerate(edges):
        internal[row] = (((subsets >> u) & 1) & ((subsets >> v) & 1)).astype(np.int8)
    internal_signed_weights = signed @ internal
    positive = internal_signed_weights > 0
    negative = internal_signed_weights < 0
    positive_supersets = positive.astype(np.uint16)
    negative_supersets = negative.astype(np.uint16)
    for bit in range(n):
        half = 1 << bit
        block = half << 1
        positive_view = positive_supersets.reshape(len(representatives), -1, block)
        negative_view = negative_supersets.reshape(len(representatives), -1, block)
        positive_view[:, :, :half] += positive_view[:, :, half:]
        negative_view[:, :, :half] += negative_view[:, :, half:]
    violation_counts = (
        positive * negative_supersets + negative * positive_supersets
    ).sum(axis=1, dtype=np.uint64)
    unambiguous = np.flatnonzero(violation_counts == 0)
    ordering = np.argsort(violation_counts, kind="stable")
    if len(unambiguous):
        raise AssertionError("unexpected globally braid-linear full-tree atom")

    nearest = []
    for raw_index in ordering[:20]:
        index = int(raw_index)
        witness = comparable_opposite_witness(representatives[index], n)
        if witness is None:
            raise AssertionError("positive violation count lacked an exact witness")
        subset, superset, first, second = witness
        nearest.append(
            {
                "class_index": index,
                "comparable_opposite_pair_count": int(violation_counts[index]),
                "representative": raw_representatives[index],
                "witness": {
                    "subset": [vertex for vertex in range(n) if (subset >> vertex) & 1],
                    "superset": [vertex for vertex in range(n) if (superset >> vertex) & 1],
                    "internal_signed_weight_subset": first,
                    "internal_signed_weight_superset": second,
                },
            }
        )

    max3_pair: Pair = (((0, 1),), ((0, 2),))
    ambiguous_control: Pair = (((0, 1), (0, 1)), ((0, 2), (0, 3)))
    if comparable_opposite_witness(max3_pair, 3) is not None:
        raise AssertionError("MAX3 path positive control was misclassified")
    ambiguous_witness = comparable_opposite_witness(ambiguous_control, 4)
    if ambiguous_witness is None:
        raise AssertionError("planted ambiguous graph was not detected")

    return {
        "universe_path": str(TREE_UNIVERSE.relative_to(ROOT)),
        "universe_sha256": observed_hash,
        "N": n,
        "degree_per_colour": 5,
        "quotient_classes_checked": len(representatives),
        "criterion": (
            "For W=B-A and q(S)=signed weight of edges internal to S, an ordered vertex chain "
            "has an ambiguous hinge iff two nested prefixes S subset T have q(S)q(T)<0."
        ),
        "globally_braid_linear_single_orbit_atoms": 0,
        "minimum_comparable_opposite_pair_count": int(violation_counts[ordering[0]]),
        "maximum_comparable_opposite_pair_count": int(violation_counts[ordering[-1]]),
        "nearest_twenty": nearest,
        "controls": {
            "MAX3_path_atom_has_no_comparable_opposite_pair": True,
            "planted_ambiguous_graph_detected": True,
            "planted_ambiguous_witness": list(ambiguous_witness),
            "class_count_and_universe_hash_reconciled": True,
        },
        "conclusion": (
            "No single balanced full-support coloured-tree orbit is linear on every braid chamber; "
            "any all-tree construction needs signed cancellation between at least two orbit atoms."
        ),
        "no_claim": (
            "This exhaustive statement concerns the 12,459 frozen loopless balanced full-tree "
            "orbits only. It is not a lower bound for their signed span, other degree-five atoms, "
            "or unrestricted networks."
        ),
    }


def falling_factorial(total: int, chosen: int) -> int:
    if not (0 <= chosen <= total):
        return 0
    return factorial(total) // factorial(total - chosen)


def binary_chamber_vector_from_full_symmetry(pair: Pair, n: int) -> Vector:
    """Recover an order-linear orbit's chamber vector from binary evaluations.

    The formula itself is valid whether or not the orbit is order-linear; the
    caller uses it only after the comparable-prefix criterion proves linearity
    on the full ordered chamber.
    """

    used = sorted({vertex for branch in pair for edge in branch for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    reduced: Pair = tuple(
        tuple((relabel[u], relabel[v]) for u, v in branch) for branch in pair
    )  # type: ignore[assignment]
    active = len(used)
    binary_values = [0]
    for top_count in range(1, n + 1):
        total = 0
        for mask in range(1 << active):
            active_top = mask.bit_count()
            multiplicity = (
                falling_factorial(top_count, active_top)
                * falling_factorial(n - top_count, active - active_top)
                * factorial(n - active)
            )
            if not multiplicity:
                continue
            branch_values = []
            for branch in reduced:
                branch_values.append(
                    sum(max((mask >> u) & 1, (mask >> v) & 1) for u, v in branch)
                )
            total += multiplicity * max(branch_values)
        binary_values.append(total)
    coefficients = [0] * n
    for top_count in range(1, n + 1):
        coefficients[n - top_count] = (
            binary_values[top_count] - binary_values[top_count - 1]
        )
    return tuple(coefficients)


def decompose_in_subset_max_basis(vector: Vector) -> tuple[Vector, int]:
    """Return primitive coefficients in F_1,...,F_(N-1), plus their gcd scale."""

    n = len(vector)
    coefficients: list[int] = []
    for rank in range(1, n):
        value = vector[rank - 1] - sum(
            coefficients[m - 1] * comb(rank - 1, m - 1)
            for m in range(1, rank)
        )
        coefficients.append(value)
    reconstructed_last = sum(
        coefficients[m - 1] * comb(n - 1, m - 1) for m in range(1, n)
    )
    if reconstructed_last != vector[-1]:
        raise AssertionError("vector is outside the lower subset-max hyperplane")
    divisor = 0
    for value in coefficients:
        divisor = gcd(divisor, abs(value))
    if divisor == 0:
        return tuple(coefficients), 1
    return tuple(value // divisor for value in coefficients), divisor


def low_signed_mass_triangular_audit() -> dict[str, object]:
    observed_hash = sha256_path(SIGNED_STREAM)
    if observed_hash != EXPECTED_SIGNED_STREAM_HASH:
        raise ValueError(f"G-0038 signed stream hash drift: {observed_hash}")
    records: list[dict[str, object]] = []
    with gzip.open(SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if (
            header.get("schema") != "max11-loop-inclusive-signed-degree5-universe-v1"
            or header.get("record_type") != "header"
            or int(header.get("expected_record_count", -1)) != 7_015_841
            or header.get("padding_convention")
            != "zero common loops; remaining common padding nonloop"
        ):
            raise ValueError("malformed G-0038 signed stream header")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass > 3:
                break
            if signed_mass:
                records.append(record)
    expected_counts = {1: 5, 2: 107, 3: 3_198}
    observed_counts = {
        signed_mass: sum(int(record["signed_mass"]) == signed_mass for record in records)
        for signed_mass in expected_counts
    }
    if observed_counts != expected_counts or len(records) != sum(expected_counts.values()):
        raise AssertionError("low-signed-mass prefix census mismatch")

    n = 11
    edges = list(combinations(range(n), 2))
    loops = [(vertex, vertex) for vertex in range(n)]
    edge_types = loops + edges
    edge_index = {edge: index for index, edge in enumerate(edge_types)}
    signed = np.zeros((len(records), len(edge_types)), dtype=np.int8)
    pairs: list[Pair] = []
    for row, record in enumerate(records):
        negative = tuple(tuple(map(int, edge)) for edge in record["negative_edges"])
        positive = tuple(tuple(map(int, edge)) for edge in record["positive_edges"])
        pair = (negative, positive)
        pairs.append(pair)
        for edge in negative:
            signed[row, edge_index[edge]] -= 1
        for edge in positive:
            signed[row, edge_index[edge]] += 1
    subsets = np.arange(1 << n, dtype=np.uint16)
    internal = np.zeros((len(edge_types), 1 << n), dtype=np.int8)
    for row, (u, v) in enumerate(edge_types):
        if u == v:
            internal[row] = ((subsets >> u) & 1).astype(np.int8)
        else:
            internal[row] = (
                ((subsets >> u) & 1) & ((subsets >> v) & 1)
            ).astype(np.int8)
    weights = signed @ internal
    positive = weights > 0
    negative = weights < 0
    positive_supersets = positive.astype(np.uint16)
    negative_supersets = negative.astype(np.uint16)
    for bit in range(n):
        half = 1 << bit
        block = half << 1
        positive_view = positive_supersets.reshape(len(records), -1, block)
        negative_view = negative_supersets.reshape(len(records), -1, block)
        positive_view[:, :, :half] += positive_view[:, :, half:]
        negative_view[:, :, :half] += negative_view[:, :, half:]
    violation_counts = (
        positive * negative_supersets + negative * positive_supersets
    ).sum(axis=1, dtype=np.uint64)
    unambiguous_indices = [int(index) for index in np.flatnonzero(violation_counts == 0)]
    unambiguous_counts = {
        signed_mass: sum(
            int(records[index]["signed_mass"]) == signed_mass
            for index in unambiguous_indices
        )
        for signed_mass in expected_counts
    }
    if unambiguous_counts != {1: 5, 2: 23, 3: 65}:
        raise AssertionError("low-mass unambiguous-orbit census drift")

    witness = alternating_invariant(n)
    pattern_counts: Counter[Vector] = Counter()
    pattern_mass_counts: dict[Vector, Counter[int]] = {}
    pattern_examples: dict[Vector, dict[str, object]] = {}
    nonzero_invariant = []
    maximum_basis_index = 0
    for index in unambiguous_indices:
        vector = binary_chamber_vector_from_full_symmetry(pairs[index], n)
        pairing = dot(witness, vector)
        if pairing:
            nonzero_invariant.append(
                {"sequence": records[index]["sequence"], "pairing": pairing}
            )
            continue
        primitive, scale = decompose_in_subset_max_basis(vector)
        support = [position + 1 for position, value in enumerate(primitive) if value]
        maximum_basis_index = max(maximum_basis_index, max(support, default=0))
        pattern_counts[primitive] += 1
        pattern_mass_counts.setdefault(primitive, Counter())[
            int(records[index]["signed_mass"])
        ] += 1
        pattern_examples.setdefault(
            primitive,
            {
                "sequence": int(records[index]["sequence"]),
                "scale": scale,
                "negative_edges": records[index]["negative_edges"],
                "positive_edges": records[index]["positive_edges"],
            },
        )
    if nonzero_invariant or maximum_basis_index > 4:
        raise AssertionError("low-mass triangular audit found an invariant escape")

    patterns = []
    for primitive, count in sorted(
        pattern_counts.items(), key=lambda item: (-item[1], item[0])
    ):
        patterns.append(
            {
                "primitive_F1_through_F10_coefficients": list(primitive),
                "orbit_count": count,
                "counts_by_signed_mass": {
                    str(mass): pattern_mass_counts[primitive][mass]
                    for mass in sorted(pattern_mass_counts[primitive])
                },
                "example": pattern_examples[primitive],
            }
        )

    return {
        "stream_path": str(SIGNED_STREAM.relative_to(ROOT)),
        "stream_sha256": observed_hash,
        "signed_masses_checked": [1, 2, 3],
        "records_checked": len(records),
        "records_by_signed_mass": {str(key): value for key, value in observed_counts.items()},
        "globally_braid_linear_single_core_orbits": len(unambiguous_indices),
        "globally_braid_linear_by_signed_mass": {
            str(key): value for key, value in unambiguous_counts.items()
        },
        "ambiguous_single_core_orbits": len(records) - len(unambiguous_indices),
        "braid_linear_orbits_with_nonzero_alternating_invariant": len(nonzero_invariant),
        "largest_F_index_in_any_braid_linear_decomposition": maximum_basis_index,
        "distinct_primitive_decomposition_patterns": len(patterns),
        "decomposition_patterns": patterns,
        "common_carry_effect": (
            "The canonical 5-s common nonloop occurrences add only 2(5-s)(N-2)! F_2, "
            "so they cannot change the alternating invariant or introduce F_5 and above."
        ),
        "conclusion": (
            "Every single signed-mass 1..3 core that is already order-statistic-linear lies in "
            "span(F_2,F_3,F_4); none supplies the missing MAX11 direction. Every other low-mass "
            "core has a non-braid kink and requires signed multi-orbit cancellation before it can "
            "participate in a triangular order-statistic construction."
        ),
        "no_claim": (
            "This is a complete finite audit only for individual G-0038 signed-mass 1..3 orbit "
            "cores. It does not exclude cancellation among two or more such cores."
        ),
    }


def self_test() -> dict[str, object]:
    obstruction = induction_obstruction(7)
    if obstruction["MAX_N_in_subset_max_span"] is not False:
        raise AssertionError("small-N obstruction self-test failed")
    unambiguous: Pair = (((0, 1),), ((0, 2),))
    ambiguous: Pair = (((0, 1), (0, 1)), ((0, 2), (0, 3)))
    if comparable_opposite_witness(unambiguous, 3) is not None:
        raise AssertionError("unambiguous control failed")
    if comparable_opposite_witness(ambiguous, 4) is None:
        raise AssertionError("ambiguous control failed")
    dp = permutation_t_counter_dp(ambiguous, 4)
    brute = permutation_t_counter_bruteforce(ambiguous, 4)
    if dp != brute:
        raise AssertionError("subset-DP self-test disagrees with brute force")
    # The unambiguous path atom is MAX3 on its active labels.  Each 3-subset
    # receives 3!*2! full-permutation preimages.
    binary_vector = binary_chamber_vector_from_full_symmetry(unambiguous, 5)
    expected_vector = tuple(12 * value for value in subset_max_vector(5, 3))
    if binary_vector != expected_vector:
        raise AssertionError("binary full-symmetry chamber recovery failed")
    return {
        "result": "PASS",
        "small_N_binomial_obstruction": True,
        "unambiguous_positive_control": True,
        "ambiguous_negative_control": True,
        "subset_DP_equals_direct_permutation_enumeration": True,
        "binary_chamber_recovery_known_MAX3_orbit": True,
    }


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    obstruction = induction_obstruction(11)
    certificate_controls = [certificate_replay(n, workers) for n in (5, 6, 10)]
    low_signed_mass = low_signed_mass_triangular_audit()
    all_tree = classify_all_tree_atoms()
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("script changed during execution")
    report = {
        "schema": SCHEMA,
        "result": "LOWER_MAX_INDUCTION_AND_COMMON_PADDING_EXACTLY_OBSTRUCTED",
        "script_sha256": script_hash_before,
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
        },
        "self_test": controls,
        "certificate_controls": certificate_controls,
        "induction_span_obstruction": obstruction,
        "low_signed_mass_triangular_audit": low_signed_mass,
        "single_orbit_all_tree_search": all_tree,
        "sharp_retry_predicate": (
            "Retry construction only with at least one topology-changing non-common branch "
            "perturbation, or a signed combination of at least two orbit atoms whose complete "
            "non-braid hinge fingerprints cancel and whose remaining ordered-chamber linear "
            "vector has nonzero alternating-binomial pairing."
        ),
        "no_claim": (
            "The exact theorem kills lower-subset induction, arbitrary linear/Möbius aggregation "
            "of those induced identities, and common loop/nonloop padding. The finite census also "
            "kills single full-tree orbit shortcuts. Neither result settles the full degree-five "
            "pairwise-comparison span or unrestricted exact MAX11 representability."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside the project") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
