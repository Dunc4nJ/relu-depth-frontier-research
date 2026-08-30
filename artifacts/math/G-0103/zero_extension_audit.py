#!/usr/bin/env python3
"""Refute or validate the zero-extension used by the G-0099 constraint.

The restricted deletion map D may descend on the span of balanced tree atoms
without making ``D on trees, zero on every other Rueß atom`` a semantic
operation.  This script decides that stronger statement in the first
nondegenerate complete family: every unordered pair of two edge-multisets on
five coordinates, with loops and common occurrences allowed.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import importlib.util
import itertools
import json
from math import gcd
from pathlib import Path
import sys

from sympy import Matrix


HERE = Path(__file__).resolve().parent
SEMANTIC_PATH = HERE / "semantic_descent_audit.py"


def load_semantics():
    spec = importlib.util.spec_from_file_location("g0103_semantics", SEMANTIC_PATH)
    if spec is None or spec.loader is None:
        raise ImportError(SEMANTIC_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def complete_pair_orbits(sem, n: int, k: int):
    edges = tuple(itertools.combinations_with_replacement(range(n), 2))
    sides = tuple(itertools.combinations_with_replacement(edges, k))
    representatives = {}
    raw = 0
    for left_index, left in enumerate(sides):
        for right in sides[left_index:]:
            raw += 1
            pair = sem.normalize_pair((left, right))
            key = sem.canonical_key(pair, n)
            representatives.setdefault(key, pair)
    return [representatives[key] for key in sorted(representatives)], {
        "edge_types": len(edges),
        "branch_multisets": len(sides),
        "raw_unordered_branch_pairs": raw,
        "orbit_count": len(representatives),
    }


def matrix_payload(matrix: Matrix) -> list[list[str]]:
    return [[str(Fraction(int(value.p), int(value.q))) for value in matrix.row(row)] for row in range(matrix.rows)]


def vector_payload(vector: Matrix) -> list[str]:
    return [str(Fraction(int(value.p), int(value.q))) for value in vector]


def primitive_integer_relation(coefficients: list[object]) -> list[int]:
    denominator = 1
    for value in coefficients:
        q = int(getattr(value, "q", 1))
        denominator = denominator * q // gcd(denominator, q)
    answer = [int(value * denominator) for value in coefficients]
    divisor = 0
    for value in answer:
        divisor = gcd(divisor, abs(value))
    if divisor:
        answer = [value // divisor for value in answer]
    first = next((value for value in answer if value), 1)
    if first < 0:
        answer = [-value for value in answer]
    return answer


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    sem = load_semantics()

    n = 5
    k = 2
    pairs, census = complete_pair_orbits(sem, n, k)
    # semantic_matrix reads only representatives; stabilisers are irrelevant
    # to this complete-family span audit.
    full_orbits = [sem.Orbit(pair, sem.canonical_key(pair, n), 1, 1) for pair in pairs]
    upper, upper_directions, _forms = sem.semantic_matrix(full_orbits, n)

    trees = sem.tree_orbits(n)
    forests = sem.forest_orbits(n - 1)
    D = sem.deletion_incidence(trees, forests, n)
    lower, lower_directions, _lower_forms = sem.semantic_matrix(forests, n - 1)
    tree_index = {tree.key: index for index, tree in enumerate(trees)}
    full_tree_indices = [index for index, pair in enumerate(pairs) if sem.valid_tree(pair, n)]
    non_tree_indices = [index for index in range(len(pairs)) if index not in set(full_tree_indices)]
    sem.require(len(full_tree_indices) == len(trees), "complete family did not contain each tree orbit once")

    zero_extension = Matrix.zeros(lower.rows, len(pairs))
    for full_index in full_tree_indices:
        zero_extension[:, full_index] = lower * D[:, tree_index[sem.canonical_key(pairs[full_index], n)]]

    upper_rank = upper.rank()
    stacked_rank = upper.col_join(zero_extension).rank()
    descends = stacked_rank == upper_rank

    # Seek the sharpest witness: one tree function represented entirely by
    # non-tree atoms.  Then zero-extension sends the two representations to
    # different lower functions.
    non_tree_matrix = upper[:, non_tree_indices]
    non_tree_rref, non_tree_pivots = non_tree_matrix.rref()
    non_tree_basis_indices = [non_tree_indices[index] for index in non_tree_pivots]
    non_tree_basis = upper[:, non_tree_basis_indices]
    witness = None
    for full_tree_index in full_tree_indices:
        target = upper[:, full_tree_index]
        if non_tree_basis.row_join(target).rank() != non_tree_basis.rank():
            continue
        solution, parameters = non_tree_basis.gauss_jordan_solve(target)
        sem.require(parameters.rows == 0, "non-tree pivot basis solve was not unique")
        raw_coefficients = [0 for _ in pairs]
        raw_coefficients[full_tree_index] = -1
        for basis_index, coefficient in zip(non_tree_basis_indices, solution, strict=True):
            raw_coefficients[basis_index] = coefficient
        integral = primitive_integer_relation(raw_coefficients)
        relation = Matrix(integral)
        upper_residual = upper * relation
        lower_residual = zero_extension * relation
        if not any(lower_residual):
            continue
        sem.require(not any(upper_residual), "constructed semantic relation is not exact")

        sparse = [
            {
                "column_index": index,
                "coefficient": coefficient,
                "kind": "balanced_tree" if index in full_tree_indices else "non_tree",
                "pair": sem.pair_payload(pairs[index]),
            }
            for index, coefficient in enumerate(integral)
            if coefficient
        ]

        # Mutation control: changing the first coefficient by +1 must destroy
        # the upper semantic identity.
        mutated = relation.copy()
        mutation_index = next(index for index, value in enumerate(integral) if value)
        mutated[mutation_index] += 1
        mutated_upper = upper * mutated
        sem.require(any(mutated_upper), "one-coefficient relation mutant escaped")
        witness = {
            "tree_column_index": full_tree_index,
            "relation_support_size": len(sparse),
            "sparse_relation": sparse,
            "upper_semantic_residual": vector_payload(upper_residual),
            "zero_extension_lower_residual": vector_payload(lower_residual),
            "first_nonzero_lower_row": next(i for i, value in enumerate(lower_residual) if value),
            "first_nonzero_lower_value": str(next(value for value in lower_residual if value)),
            "mutation_control": {
                "mutation": f"add one to relation coefficient at column {mutation_index}",
                "expected": "upper identity breaks",
                "result": "REJECTED",
                "first_nonzero_upper_row": next(i for i, value in enumerate(mutated_upper) if value),
                "first_nonzero_upper_value": str(next(value for value in mutated_upper if value)),
            },
        }
        break

    sem.require(descends == (witness is None), "rank verdict and explicit witness disagree")
    report = {
        "schema": "max11-g0103-zero-extension-audit-v1",
        "result": "ZERO_EXTENSION_NOT_SEMANTIC" if not descends else "NO_COUNTEREXAMPLE",
        "n": n,
        "branch_degree": k,
        "complete_family_census": census,
        "balanced_tree_orbits": len(trees),
        "non_tree_orbits": len(non_tree_indices),
        "upper_semantic_shape": list(upper.shape),
        "upper_semantic_rank": upper_rank,
        "non_tree_semantic_rank": non_tree_matrix.rank(),
        "lower_forest_semantic_shape": list(lower.shape),
        "lower_forest_semantic_rank": lower.rank(),
        "stacked_rank_with_zero_extension": stacked_rank,
        "zero_extension_descends": descends,
        "witness": witness,
        "upper_hinge_directions": [list(direction) for direction in upper_directions],
        "lower_hinge_directions": [list(direction) for direction in lower_directions],
        "claim_boundary": (
            "This is an exact statement about the zero-extension of the balanced-tree deletion map to the "
            "complete fixed-degree-two symmetrised pairwise-max family on five coordinates. It proves that "
            "setting every non-tree atom's lower image to zero is representation-dependent already at n=5. "
            "It does not refute the restricted quotient map on the tree span, does not rule out a corrected "
            "extension with non-tree terms, and makes no n=11 nonrepresentability claim."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "orbits": census["orbit_count"],
        "upper_rank": upper_rank,
        "non_tree_rank": report["non_tree_semantic_rank"],
        "stacked_rank": stacked_rank,
        "witness_support": witness["relation_support_size"] if witness else None,
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
