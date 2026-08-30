#!/usr/bin/env python3
"""Exact smallest counterexample to the unshifted tied-ridge reading of D.

For P(A,B)=conv(Z_A union Z_B), an exposed face that deletes one segment
from each branch retains *selected endpoints*.  After the leaf coordinate is
removed, the honest face is generally

    conv(e_a + Z_{A-e}, e_b + Z_{B-f}),

not conv(Z_{A-e}, Z_{B-f}).  Loops encode the two endpoint translations.
This script verifies a positive common-translation case and a non-linear
relative-translation counterexample using integer support values only.
"""

from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path
from typing import Iterable, Sequence


Edge = tuple[int, int]
Pair = tuple[tuple[Edge, ...], tuple[Edge, ...]]
Point = tuple[int, ...]


def unit(n: int, index: int) -> Point:
    return tuple(int(i == index) for i in range(n))


def add(left: Sequence[int], right: Sequence[int]) -> Point:
    return tuple(a + b for a, b in zip(left, right, strict=True))


def dot(left: Sequence[int], right: Sequence[int]) -> int:
    return sum(a * b for a, b in zip(left, right, strict=True))


def zonotope_points(edges: Iterable[Edge], n: int) -> tuple[Point, ...]:
    points = {tuple(0 for _ in range(n))}
    for u, v in edges:
        points = {
            add(point, endpoint)
            for point in points
            for endpoint in (unit(n, u), unit(n, v))
        }
    return tuple(sorted(points))


def exposed(points: Sequence[Point], normal: Sequence[int]) -> tuple[Point, ...]:
    optimum = max(dot(point, normal) for point in points)
    return tuple(point for point in points if dot(point, normal) == optimum)


def project_delete(point: Sequence[int], deleted: int) -> Point:
    return tuple(value for index, value in enumerate(point) if index != deleted)


def support(points: Sequence[Point], covector: Sequence[int]) -> int:
    return max(dot(point, covector) for point in points)


def face_of_pair(pair: Pair, normal: Sequence[int], n: int) -> dict[str, object]:
    branch_points = [zonotope_points(side, n) for side in pair]
    branch_supports = [max(dot(point, normal) for point in points) for points in branch_points]
    if branch_supports[0] > branch_supports[1]:
        winners = (0,)
    elif branch_supports[1] > branch_supports[0]:
        winners = (1,)
    else:
        winners = (0, 1)
    faces = [exposed(branch_points[index], normal) for index in winners]
    return {
        "branch_supports": branch_supports,
        "winning_branches": list(winners),
        "branch_faces": [[list(point) for point in face] for face in faces],
        "face_points": tuple(sorted(set(itertools.chain.from_iterable(faces)))),
    }


def translation_match(actual: Sequence[Point], target: Sequence[Point], translation: Point) -> bool:
    shifted = {add(point, translation) for point in target}
    return set(actual) == shifted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    # Positive control: both removed edges meet the same surviving vertex.
    star: Pair = (((0, 1), (0, 2)), ((0, 3), (0, 4)))
    star_normal = (0, -1, 0, -1, 0)
    star_face = face_of_pair(star, star_normal, 5)
    if star_face["winning_branches"] != [0, 1]:
        raise AssertionError("positive-control branches did not tie")
    star_actual = tuple(project_delete(point, 1) for point in star_face["face_points"])
    star_target = tuple(sorted(set(zonotope_points(((0, 2),), 5) + zonotope_points(((0, 4),), 5))))
    star_target = tuple(project_delete(point, 1) for point in star_target)
    star_translation = unit(4, 0)
    if not translation_match(star_actual, star_target, star_translation):
        raise AssertionError("common-endpoint positive control is not a translation")

    # Negative control/counterexample.  Leaf 4 has blue edge (0,4); delete it
    # and the opposite red edge (0,1).  The residual forest has disjoint red
    # (0,3) and blue (1,2) edges.  The displayed normal keeps those segments,
    # makes both outer branches tie, selects endpoint 0 on the red deleted
    # edge, and endpoint 4 on the blue leaf edge.
    path: Pair = (((0, 1), (0, 3)), ((0, 4), (1, 2)))
    path_normal = (0, -1, -1, 0, 1)
    path_face = face_of_pair(path, path_normal, 5)
    if path_face["winning_branches"] != [0, 1]:
        raise AssertionError("counterexample branches did not tie")
    actual = tuple(project_delete(point, 4) for point in path_face["face_points"])
    target = tuple(sorted(set(zonotope_points(((0, 3),), 4) + zonotope_points(((1, 2),), 4))))
    expected_actual = ((0, 0, 1, 0), (0, 1, 0, 0), (1, 0, 0, 1), (2, 0, 0, 0))
    expected_target = (unit(4, 0), unit(4, 1), unit(4, 2), unit(4, 3))
    if tuple(sorted(actual)) != tuple(sorted(expected_actual)):
        raise AssertionError(f"counterexample face drift: {actual}")
    if tuple(sorted(target)) != tuple(sorted(expected_target)):
        raise AssertionError("unshifted forest target drift")

    covectors = (unit(4, 0), tuple(-value for value in unit(4, 0)))
    differences = [support(actual, x) - support(target, x) for x in covectors]
    if differences != [1, 0]:
        raise AssertionError("support discriminator drift")
    # A translation would produce a linear support difference, hence opposite
    # values at x and -x.  Here 1 + 0 != 0.
    if sum(differences) == 0:
        raise AssertionError("relative-translation counterexample became a global translation")
    actual_sums = sorted({sum(point) for point in actual})
    target_sums = sorted({sum(point) for point in target})
    if actual_sums == target_sums:
        raise AssertionError("constant-sum discriminator lost potency")

    # Mutation: lowering the leaf-normal value from +1 to 0 destroys the tie;
    # a face routine that still returned the two-branch hull would be broken.
    mutated_normal = (0, -1, -1, 0, 0)
    mutated_face = face_of_pair(path, mutated_normal, 5)
    if mutated_face["winning_branches"] == [0, 1]:
        raise AssertionError("tie-destroying normal mutation escaped")

    report = {
        "schema": "max11-g0103-ridge-face-counterexample-v1",
        "result": "UNSHIFTED_RIDGE_FORMULA_FALSE",
        "exact_face_formula": (
            "If u is constant on the components after deleting e and f, then "
            "face_u(Z_A)=e_p+Z_(A-e) and face_u(Z_B)=e_q+Z_(B-f), where p and q are "
            "the u-maximal endpoints of e and f. On a branch tie, face_u(conv(Z_A,Z_B)) "
            "=conv(e_p+Z_(A-e),e_q+Z_(B-f))."
        ),
        "formal_correction": (
            "After deleting the leaf coordinate, add a loop at p to the first residual branch "
            "and a loop at q to the second. Dropping those loops gives D but is not semantic "
            "unless their relative translation contributes only a common affine term."
        ),
        "positive_common_translation_control": {
            "pair": [[list(edge) for edge in side] for side in star],
            "normal": list(star_normal),
            "branch_supports": star_face["branch_supports"],
            "projected_actual_face_points": [list(point) for point in sorted(star_actual)],
            "unshifted_target_points": [list(point) for point in sorted(star_target)],
            "translation": list(star_translation),
            "exact_translation_match": True,
        },
        "smallest_counterexample": {
            "n": 5,
            "pair": [[list(edge) for edge in side] for side in path],
            "leaf": 4,
            "leaf_edge_branch": 1,
            "leaf_edge": [0, 4],
            "opposite_colour_edge": [0, 1],
            "normal": list(path_normal),
            "branch_supports": path_face["branch_supports"],
            "exposed_branch_faces": path_face["branch_faces"],
            "projected_actual_face_points": [list(point) for point in sorted(actual)],
            "unshifted_D_forest_points": [list(point) for point in sorted(target)],
            "actual_coordinate_sum_levels": actual_sums,
            "target_coordinate_sum_levels": target_sums,
            "support_covectors": [list(point) for point in covectors],
            "actual_minus_target_support": differences,
            "not_translation_equivalent": True,
            "missing_term": (
                "The red branch retains endpoint e_0 while the blue branch retains the deleted "
                "leaf endpoint e_4, which projects to zero. The honest projected face is "
                "conv(e_0+[e_0,e_3], [e_1,e_2]); D replaces it by "
                "conv([e_0,e_3],[e_1,e_2])."
            ),
        },
        "tie_mutation_control": {
            "mutation": "replace leaf-normal value +1 by 0",
            "mutated_normal": list(mutated_normal),
            "mutated_branch_supports": mutated_face["branch_supports"],
            "mutated_winning_branches": mutated_face["winning_branches"],
            "expected": "tie destroyed",
            "result": "REJECTED",
        },
        "claim_boundary": (
            "This refutes the eventwise claim that the codimension-two tied face is the unshifted "
            "D forest atom, even modulo global translations. It does not rule out a signed sum of "
            "shifted ridge faces whose correction terms later cancel, nor an abstract linear map "
            "on the balanced-tree semantic quotient."
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({
        "result": report["result"],
        "actual_sum_levels": actual_sums,
        "target_sum_levels": target_sums,
        "support_differences_at_x_and_minus_x": differences,
        "tie_mutant_winners": mutated_face["winning_branches"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
