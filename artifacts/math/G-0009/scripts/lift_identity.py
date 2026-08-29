#!/usr/bin/env python3
"""Derive and exactly test the common-edge lift identity.

For an unnormalised symmetrised degree-k pair atom

    Phi_N(A,B) = sum_{sigma in S_N} max(sum_{e in A} h_{sigma(e)},
                                        sum_{e in B} h_{sigma(e)})

with h_{ij}=max(x_i,x_j), append one fixed edge e to both A and B.  If
``sum_t c_t Phi_m(A_t,B_t)=MAX_m`` then the exact identity is

    sum_t c_t Phi_N(A_t+e,B_t+e)
      = (N-m)! F_m^(N) + 2 (N-2)!/(k m!) F_2^(N),

where F_r^(N)=sum_{|S|=r} max_{i in S} x_i.  The location of e and any
incidences it shares with the source labels do not affect this aggregate
identity.  The proof is pointwise cancellation followed by permutation
counting; the executable check below uses exact Fractions only.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
from itertools import combinations, combinations_with_replacement, permutations
import json
from math import comb, factorial
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G7_CERT = ROOT / "artifacts/math/G-0007/data/n9_hybrid_certificate.json"
MAX10_CERT = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
SMALL_CERT = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_5_2.json"
SCHEMA = "max-common-edge-lift-identity-attestation-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_certificate(path: Path) -> tuple[int, int, list[tuple[object, Fraction]]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    n = int(document["n"])
    terms = []
    degree = None
    for term in document["terms"]:
        pair = tuple(
            tuple(tuple(map(int, edge)) for edge in side) for side in term["pair"]
        )
        if len(pair) != 2 or len(pair[0]) != len(pair[1]):
            raise ValueError(f"malformed pair in {path}")
        if degree is None:
            degree = len(pair[0])
        if len(pair[0]) != degree:
            raise ValueError(f"mixed degrees in {path}")
        terms.append((pair, Fraction(term["coefficient"])))
    if degree is None:
        raise ValueError(f"empty certificate: {path}")
    expected_sum = Fraction(1, degree * factorial(n))
    observed_sum = sum((coefficient for _, coefficient in terms), Fraction())
    if observed_sum != expected_sum:
        raise AssertionError((path, observed_sum, expected_sum))
    return n, degree, terms


def edge_relu(values: tuple[Fraction, ...], edge: tuple[int, int]) -> Fraction:
    a, b = edge
    return max(values[a - 1], values[b - 1])


def atom(values: tuple[Fraction, ...], pair: object) -> Fraction:
    left, right = pair  # type: ignore[misc]
    return max(
        sum((edge_relu(values, edge) for edge in left), Fraction()),
        sum((edge_relu(values, edge) for edge in right), Fraction()),
    )


def permute_pair(pair: object, permutation: tuple[int, ...]) -> object:
    left, right = pair  # type: ignore[misc]
    return tuple(
        tuple(
            tuple(sorted((permutation[a - 1], permutation[b - 1])))
            for a, b in side
        )
        for side in (left, right)
    )


def append_common_edge(pair: object, edge: tuple[int, int]) -> object:
    left, right = pair  # type: ignore[misc]
    canonical = tuple(sorted(edge))
    return (tuple(left) + (canonical,), tuple(right) + (canonical,))


def lifted_lhs(
    values: tuple[Fraction, ...],
    terms: list[tuple[object, Fraction]],
    edge: tuple[int, int],
) -> Fraction:
    total = Fraction()
    for raw_permutation in permutations(range(1, len(values) + 1)):
        for pair, coefficient in terms:
            lifted = append_common_edge(pair, edge)
            total += coefficient * atom(values, permute_pair(lifted, raw_permutation))
    return total


def subset_max_sum(values: tuple[Fraction, ...], size: int) -> Fraction:
    return sum((max(values[index] for index in subset) for subset in combinations(range(len(values)), size)), Fraction())


def lifted_rhs(values: tuple[Fraction, ...], m: int, k: int) -> Fraction:
    n = len(values)
    alpha = Fraction(2 * factorial(n - 2), k * factorial(m))
    return factorial(n - m) * subset_max_sum(values, m) + alpha * subset_max_sum(values, 2)


def chamber_coefficients(m: int, n: int, k: int) -> list[Fraction]:
    """Coefficients on x_1<=...<=x_N for the identity's right side."""

    alpha = Fraction(2 * factorial(n - 2), k * factorial(m))
    return [
        factorial(n - m) * (comb(rank, m - 1) if rank >= m - 1 else 0)
        + alpha * rank
        for rank in range(n)
    ]


def dot(coefficients: Iterable[Fraction], values: Iterable[Fraction]) -> Fraction:
    return sum((a * b for a, b in zip(coefficients, values)), Fraction())


def vector_strings(values: Iterable[Fraction]) -> list[str]:
    return [str(value) for value in values]


def rank_fraction_columns(columns: list[list[Fraction]]) -> int:
    if not columns:
        return 0
    matrix = [list(row) for row in zip(*columns)]
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
            if row == rank or not matrix[row][column]:
                continue
            scale = matrix[row][column]
            matrix[row] = [
                value - scale * pivot_value
                for value, pivot_value in zip(matrix[row], matrix[rank])
            ]
        rank += 1
    return rank


def derive_attestation() -> dict[str, object]:
    m, k, small_terms = load_certificate(SMALL_CERT)
    if (m, k) != (5, 2):
        raise AssertionError((m, k))
    n = 6
    common_edge = (m, n)  # Shares one source label: a non-disjoint control.
    values_tested = 0
    chamber = chamber_coefficients(m, n, k)
    for raw_values in combinations_with_replacement((-2, 0, 3), n):
        values = tuple(map(Fraction, raw_values))
        lhs = lifted_lhs(values, small_terms, common_edge)
        rhs = lifted_rhs(values, m, k)
        if lhs != rhs:
            raise AssertionError((values, lhs, rhs))
        if rhs != dot(chamber, values):
            raise AssertionError((values, rhs, chamber))
        values_tested += 1

    source_records = []
    lift_vectors = []
    for path, expected in ((G7_CERT, (9, 4)), (MAX10_CERT, (10, 4))):
        source_n, source_k, terms = load_certificate(path)
        if (source_n, source_k) != expected:
            raise AssertionError((path, source_n, source_k, expected))
        coefficient_sum = sum((coefficient for _, coefficient in terms), Fraction())
        coefficients = chamber_coefficients(source_n, 11, source_k)
        lift_vectors.append(coefficients)
        source_records.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_path(path),
                "n": source_n,
                "degree": source_k,
                "term_count": len(terms),
                "coefficient_sum": str(coefficient_sum),
                "max11_ordered_chamber_coefficients": vector_strings(coefficients),
            }
        )

    max11 = [Fraction(0)] * 10 + [Fraction(1)]
    lift_rank = rank_fraction_columns(lift_vectors)
    augmented_rank = rank_fraction_columns(lift_vectors + [max11])
    if augmented_rank == lift_rank:
        raise AssertionError("two common-edge aggregates unexpectedly span MAX11")

    document = {
        "schema": SCHEMA,
        "identity": (
            "sum_t c_t Phi_N(A_t+e,B_t+e) = (N-m)! F_m^(N) "
            "+ 2(N-2)!/(k m!) F_2^(N)"
        ),
        "single_atom_identity": (
            "Phi_N(A+e,B+e) = Phi_N(A,B) + 2(N-2)! F_2^(N); consequently the "
            "fully symmetrized function is independent of the location of the fixed loopless edge e"
        ),
        "definitions": {
            "Phi": "unnormalized sum over all N! coordinate permutations",
            "F_r": "sum over all r-subsets S of max_{i in S} x_i",
            "h_ij": "max(x_i,x_j)",
        },
        "proof_obligations": [
            {
                "claim": "pointwise common-edge cancellation",
                "case_U_ge_V": "max(U+h,V+h)=U+h=h+max(U,V)",
                "case_V_ge_U": "max(U+h,V+h)=V+h=h+max(U,V)",
            },
            {
                "claim": "source-term permutation count",
                "count": "each m-subset receives (N-m)! completions of every S_m permutation",
            },
            {
                "claim": "common-edge permutation count",
                "count": "each unordered target edge receives 2(N-2)! permutations",
            },
            {
                "claim": "edge-placement invariance for each source atom",
                "count": (
                    "the source part does not contain e, while the common part sums to the same "
                    "2(N-2)! F_2 term for every fixed loopless e"
                ),
            },
            {
                "claim": "certificate coefficient sum",
                "count": "sum_t c_t=1/(k m!), forced by evaluating all coordinates at one",
            },
        ],
        "small_n_exact_test": {
            "source": str(SMALL_CERT.relative_to(ROOT)),
            "source_sha256": sha256_path(SMALL_CERT),
            "m": m,
            "N": n,
            "degree": k,
            "common_edge": list(common_edge),
            "ordered_grid": "all nondecreasing 6-tuples over {-2,0,3}",
            "points_tested": values_tested,
            "arithmetic": "fractions.Fraction; exhaustive S_6 symmetrization",
            "lhs_equals_combinatorial_rhs": True,
            "rhs_equals_symbolic_chamber_vector": True,
            "ordered_chamber_coefficients": vector_strings(chamber),
        },
        "max11_sources": source_records,
        "two_source_common_edge_span": {
            "rank_over_Q": lift_rank,
            "rank_with_MAX11_over_Q": augmented_rank,
            "contains_MAX11": False,
            "interpretation": (
                "the two principled aggregate lifts are exact controls but cannot by themselves "
                "produce MAX11; topology-changing atom directions remain necessary"
            ),
        },
        "compilability": (
            "Every lifted summand remains max(sum of five pairwise ReLUs, sum of five "
            "pairwise ReLUs). Pairwise ReLUs form hidden layer 1, the branch maximum is hidden "
            "layer 2, and rational certificate weights are applied only at the linear output."
        ),
        "claim_boundary": (
            "The formula certifies this common-edge aggregate identity. It does not assert that "
            "MAX11 lies in the span of the two aggregates or in any tested finite topology family."
        ),
    }
    document["canonical_payload_sha256"] = hashlib.sha256(canonical_bytes(document)).hexdigest()
    return document


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = derive_attestation()
    raw = canonical_bytes(document)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(raw)
    print(
        f"{args.output} bytes={len(raw)} sha256={hashlib.sha256(raw).hexdigest()} "
        f"small_n_points={document['small_n_exact_test']['points_tested']}"
    )


if __name__ == "__main__":
    main()
