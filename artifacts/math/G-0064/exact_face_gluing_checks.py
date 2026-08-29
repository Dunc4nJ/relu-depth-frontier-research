#!/usr/bin/env python3
"""Exact controls for the G-0064 face-gluing theorem.

These finite examples do not prove the general theorem in README.md.  They
exercise its load-bearing alternatives on the exact MAX3 primitive block and
plant the standard counterexample to the stronger, false summand shortcut.
"""

from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from typing import Iterable, Sequence


Q = Fraction
Point = tuple[Q, ...]


def add(left: Point, right: Point) -> Point:
    return tuple(a + b for a, b in zip(left, right, strict=True))


def scale(value: Q, point: Point) -> Point:
    return tuple(value * coordinate for coordinate in point)


def dot(left: Point, right: Point) -> Q:
    return sum((a * b for a, b in zip(left, right, strict=True)), Q(0))


def support(vertices: Sequence[Point], direction: Point) -> Q:
    return max(dot(vertex, direction) for vertex in vertices)


def exposed(vertices: Sequence[Point], direction: Point) -> tuple[Point, ...]:
    height = support(vertices, direction)
    return tuple(vertex for vertex in vertices if dot(vertex, direction) == height)


def minkowski_vertices(left: Sequence[Point], right: Sequence[Point]) -> tuple[Point, ...]:
    # The caller supplies examples whose redundant sums do not matter for the
    # central-symmetry check: invariance of the complete finite sum set is enough.
    return tuple(sorted(set(add(a, b) for a in left for b in right)))


def centrally_symmetric_vertex_set(vertices: Iterable[Point]) -> bool:
    points = tuple(sorted(set(vertices)))
    if not points:
        raise ValueError("nonempty vertex set required")
    dimension = len(points[0])
    if any(len(point) != dimension for point in points):
        raise ValueError("dimension mismatch")
    center = tuple(
        sum((point[index] for point in points), Q(0)) / len(points)
        for index in range(dimension)
    )
    point_set = set(points)
    return all(add(scale(Q(2), center), scale(Q(-1), point)) in point_set for point in points)


def canonical_sha256(value: object) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def main() -> None:
    zero = (Q(0), Q(0))
    u = (Q(1), Q(0))
    v = (Q(0), Q(1))
    p_segment = (zero, u)
    q_segment = (zero, v)
    primitive_triangle = (zero, u, v)

    # At the triple tie of MAX3, the dual input is zero.  Both zonotope
    # branches tie, and their hull is the non-centrally-symmetric triangle.
    triple_direction = zero
    triple_p = support(p_segment, triple_direction)
    triple_q = support(q_segment, triple_direction)
    if triple_p != triple_q or centrally_symmetric_vertex_set(primitive_triangle):
        raise AssertionError("MAX3 triple-tie positive control failed")

    # At a two-way top tie, the same primitive exposes only the segment [u,v].
    # It is centrally symmetric, showing why G-0064 begins with three maxima.
    pair_direction = (Q(1), Q(1))
    pair_p_face = exposed(p_segment, pair_direction)
    pair_q_face = exposed(q_segment, pair_direction)
    pair_hull = tuple(sorted(set(pair_p_face + pair_q_face)))
    if support(p_segment, pair_direction) != support(q_segment, pair_direction):
        raise AssertionError("pair-tie branch equality failed")
    if not centrally_symmetric_vertex_set(pair_hull):
        raise AssertionError("two-way exposed segment should be centrally symmetric")

    # A strict branch exposes a zonotope face (here a point), never the
    # noncentral triangle.
    strict_direction = (Q(1), Q(-1))
    if support(p_segment, strict_direction) <= support(q_segment, strict_direction):
        raise AssertionError("strict-branch control did not choose P")
    strict_face = exposed(primitive_triangle, strict_direction)
    if strict_face != (u,) or not centrally_symmetric_vertex_set(strict_face):
        raise AssertionError("strict primitive face control failed")

    # Load-bearing hostile control: a triangle plus its reflection has a
    # centrally symmetric finite sum set.  Thus the tempting statement that a
    # summand of a centrally symmetric polytope must be centrally symmetric is
    # false; Lemma 2 correctly requires every *other* term on both sides to be
    # centrally symmetric.
    reflected_triangle = tuple(scale(Q(-1), point) for point in primitive_triangle)
    difference_sum = minkowski_vertices(primitive_triangle, reflected_triangle)
    if centrally_symmetric_vertex_set(primitive_triangle):
        raise AssertionError("triangle mutant unexpectedly centrally symmetric")
    if centrally_symmetric_vertex_set(reflected_triangle):
        raise AssertionError("reflected triangle mutant unexpectedly centrally symmetric")
    if not centrally_symmetric_vertex_set(difference_sum):
        raise AssertionError("triangle difference-body control should be centrally symmetric")

    # Generator restriction in the centered MAX11 space: for d_i=mu-e_i and
    # sum(g)=0, <g,d_i>=-g_i.  Check every coordinate on exact sample vectors.
    generators = (
        tuple(Q(1 if index == 0 else -1 if index == 1 else 0) for index in range(11)),
        tuple(Q(index - 5) for index in range(11)),
    )
    mu = tuple(Q(1, 11) for _ in range(11))
    restriction_checks = 0
    for generator in generators:
        if sum(generator, Q(0)) != 0:
            raise AssertionError("sample generator must lie in centered space")
        for index in range(11):
            direction = tuple(mu[j] - Q(1 if j == index else 0) for j in range(11))
            if dot(generator, direction) != -generator[index]:
                raise AssertionError("facet generator restriction identity failed")
            restriction_checks += 1

    report = {
        "schema": "max11-g0064-exact-face-gluing-controls-v1",
        "result": "PASS",
        "max3_triple_tie": {
            "branch_supports_equal": triple_p == triple_q,
            "primitive_face_vertices": len(primitive_triangle),
            "primitive_face_centrally_symmetric": False,
        },
        "max3_two_way_tie": {
            "branch_supports_equal": True,
            "exposed_vertices": len(pair_hull),
            "exposed_face_centrally_symmetric": True,
        },
        "strict_branch": {
            "selected": "P",
            "exposed_vertices": len(strict_face),
            "exposed_face_centrally_symmetric": True,
        },
        "hostile_false_summand_shortcut": {
            "triangle_centrally_symmetric": False,
            "reflected_triangle_centrally_symmetric": False,
            "finite_difference_sum_set_centrally_symmetric": True,
        },
        "facet_generator_restriction": {
            "exact_checks": restriction_checks,
            "identity": "<g,mu-e_i>=-g_i when sum(g)=0",
        },
    }
    report["scientific_payload_sha256"] = canonical_sha256(report)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
