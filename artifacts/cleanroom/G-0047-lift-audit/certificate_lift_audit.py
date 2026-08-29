#!/usr/bin/env python3
"""Independent exact decoder and bounded lift audit for the public MAX certificates.

This program deliberately does not import the public verifier.  It has two jobs:

1. decode the MAX5 and MAX6 certificates into an exact ordered-cone normal
   form, with a one-coefficient mutation as a must-fail control; and
2. test explicitly defined, orbit-level ways of building the coefficient
   vector of the public degree-four MAX10 certificate from the degree-two
   MAX5/MAX6 support.

The structural tests concern the frozen public coefficient vector, not every
possible MAX10 certificate.  They do not prove or refute MAX11.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import platform
from collections import Counter
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

import networkx as nx
import pynauty
import sympy
from networkx.algorithms.isomorphism import GraphMatcher, categorical_node_match
from sympy import Matrix, Rational


ROOT = Path(__file__).resolve().parents[3]
CERT_DIR = ROOT / "subjects/max-relu-known/certificates"
PUBLIC_VERIFIER = ROOT / "literature/repos/max-relu-certificates/verify_certificate.py"
SELF_DIR = Path(__file__).resolve().parent

PINNED_SHA256 = {
    "certificate_5_2.json": "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    "certificate_6_2.json": "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    "certificate_10_4.json": "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    "verify_certificate.py": "d6da3030b719735b10a197dc79d7e311ecc90f70314ed748de81087f94f039a7",
}

Pair = tuple[int, int]
Side = tuple[Pair, ...]
Template = tuple[Side, Side]
Vector = tuple[int, ...]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_json_sha256(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()


def fraction_text(value: Fraction | Rational) -> str:
    return str(value.p) + "/" + str(value.q) if isinstance(value, Rational) and value.q != 1 else (
        str(value.p) if isinstance(value, Rational) else (
            f"{value.numerator}/{value.denominator}" if value.denominator != 1 else str(value.numerator)
        )
    )


def read_certificate(path: Path, expected_n: int, expected_k: int) -> dict:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        raise ValueError(f"unparseable JSON: {path}: {exc}") from exc
    if not isinstance(raw, dict) or set(raw) != {"n", "terms"}:
        raise ValueError(f"certificate must have exactly n and terms: {path}")
    if raw["n"] != expected_n or not isinstance(raw["n"], int):
        raise ValueError(f"unexpected n in {path}: {raw['n']!r}")
    if not isinstance(raw["terms"], list) or not raw["terms"]:
        raise ValueError(f"terms must be a nonempty list: {path}")

    parsed_terms = []
    for term_index, term in enumerate(raw["terms"]):
        if not isinstance(term, dict) or set(term) != {"coefficient", "pair"}:
            raise ValueError(f"bad term schema at {term_index}")
        try:
            coefficient = Fraction(term["coefficient"])
        except Exception as exc:
            raise ValueError(f"bad rational coefficient at {term_index}") from exc
        if coefficient == 0:
            raise ValueError(f"zero coefficient at {term_index}")
        pair_raw = term["pair"]
        if not isinstance(pair_raw, list) or len(pair_raw) != 2:
            raise ValueError(f"term {term_index} must have two sides")
        sides: list[Side] = []
        for side_index, side_raw in enumerate(pair_raw):
            if not isinstance(side_raw, list) or len(side_raw) != expected_k:
                raise ValueError(
                    f"term {term_index} side {side_index} must have {expected_k} edges"
                )
            side: list[Pair] = []
            for edge_index, edge_raw in enumerate(side_raw):
                if (
                    not isinstance(edge_raw, list)
                    or len(edge_raw) != 2
                    or not all(isinstance(v, int) and not isinstance(v, bool) for v in edge_raw)
                ):
                    raise ValueError(
                        f"term {term_index} side {side_index} edge {edge_index} is malformed"
                    )
                a, b = edge_raw
                if not (1 <= a <= b <= expected_n):
                    raise ValueError(
                        f"term {term_index} side {side_index} edge {edge_index} is out of range"
                    )
                side.append((a, b))
            sides.append(tuple(side))
        parsed_terms.append({"coefficient": coefficient, "pair": (sides[0], sides[1])})
    return {"n": expected_n, "k": expected_k, "terms": parsed_terms}


def input_paths() -> dict[str, Path]:
    return {
        "certificate_5_2.json": CERT_DIR / "certificate_5_2.json",
        "certificate_6_2.json": CERT_DIR / "certificate_6_2.json",
        "certificate_10_4.json": CERT_DIR / "certificate_10_4.json",
        "verify_certificate.py": PUBLIC_VERIFIER,
    }


def verify_pins() -> dict[str, str]:
    observed = {name: sha256_file(path) for name, path in input_paths().items()}
    if observed != PINNED_SHA256:
        raise RuntimeError(
            "input pin mismatch: "
            + json.dumps({"expected": PINNED_SHA256, "observed": observed}, sort_keys=True)
        )
    return observed


def side_form(side: Side, rank_of_label: Sequence[int], n: int) -> Vector:
    result = [0] * n
    for a, b in side:
        result[max(rank_of_label[a - 1], rank_of_label[b - 1])] += 1
    return tuple(result)


def cone_sign(direction: Vector) -> str:
    """Classify d.x on x_1 <= ... <= x_n using exact prefix sums."""
    if sum(direction) != 0:
        raise ValueError("pair-atom direction is not translation invariant")
    prefixes = []
    running = 0
    for value in direction[:-1]:
        running += value
        prefixes.append(running)
    if all(value >= 0 for value in prefixes):
        return "nonpositive"
    if all(value <= 0 for value in prefixes):
        return "nonnegative"
    return "variable"


def add_vector(target: list[int], source: Vector) -> None:
    for index, value in enumerate(source):
        target[index] += value


def atom_normal_form(pair: Template, n: int) -> tuple[Vector, dict[Vector, int]]:
    """Return an exact linear-plus-oriented-hinges form on the sorted cone.

    This implementation is independent of the public verifier: it starts from
    max(l,r)=l+ReLU(r-l), classifies fixed signs by prefix sums, and uses
    ReLU(-u)=ReLU(u)-u when orienting variable primitive directions.
    """
    linear = [0] * n
    hinges: dict[Vector, int] = {}
    left, right = pair
    for rank_of_label in itertools.permutations(range(n)):
        left_form = side_form(left, rank_of_label, n)
        right_form = side_form(right, rank_of_label, n)
        direction = tuple(b - a for a, b in zip(left_form, right_form))
        sign = cone_sign(direction)
        if sign == "nonpositive":
            add_vector(linear, left_form)
            continue
        if sign == "nonnegative":
            add_vector(linear, right_form)
            continue

        scale = math.gcd(*(abs(value) for value in direction))
        if scale <= 0:
            raise AssertionError("a variable direction cannot be zero")
        primitive = tuple(value // scale for value in direction)
        first = next(value for value in primitive if value)
        if first < 0:
            primitive = tuple(-value for value in primitive)
            # l + ReLU(r-l) = r + scale*ReLU(-(r-l)/scale).
            add_vector(linear, right_form)
        else:
            add_vector(linear, left_form)
        hinges[primitive] = hinges.get(primitive, 0) + scale
    return tuple(linear), hinges


def residual_for_certificate(certificate: dict, coefficient_override: dict[int, Fraction] | None = None) -> dict:
    n = certificate["n"]
    total_linear = [Fraction(0) for _ in range(n)]
    total_hinges: dict[Vector, Fraction] = {}
    atom_stats = []
    for index, term in enumerate(certificate["terms"]):
        coefficient = (
            coefficient_override[index]
            if coefficient_override is not None and index in coefficient_override
            else term["coefficient"]
        )
        linear, hinges = atom_normal_form(term["pair"], n)
        for rank, value in enumerate(linear):
            total_linear[rank] += coefficient * value
        for direction, value in hinges.items():
            total_hinges[direction] = total_hinges.get(direction, Fraction(0)) + coefficient * value
        atom_stats.append({"linear": list(linear), "variable_hinges": len(hinges)})
    total_linear[-1] -= 1
    bad_linear = [(index + 1, value) for index, value in enumerate(total_linear) if value]
    bad_hinges = [(direction, value) for direction, value in sorted(total_hinges.items()) if value]
    serial_residual = {
        "linear": [[index, fraction_text(value)] for index, value in bad_linear],
        "hinges": [[list(direction), fraction_text(value)] for direction, value in bad_hinges],
    }
    return {
        "passes": not bad_linear and not bad_hinges,
        "bad_linear_count": len(bad_linear),
        "bad_hinge_count": len(bad_hinges),
        "residual_sha256": canonical_json_sha256(serial_residual),
        "first_bad_linear": serial_residual["linear"][:3],
        "first_bad_hinges": serial_residual["hinges"][:3],
        "atom_stats": atom_stats,
    }


def direct_atom_value(pair: Template, point: Sequence[int], permutations: Sequence[tuple[int, ...]]) -> int:
    total = 0
    left, right = pair
    for rank_of_label in permutations:
        left_value = sum(point[max(rank_of_label[a - 1], rank_of_label[b - 1])] for a, b in left)
        right_value = sum(point[max(rank_of_label[a - 1], rank_of_label[b - 1])] for a, b in right)
        total += max(left_value, right_value)
    return total


def direct_grid_control(certificate: dict, mutation_index: int) -> dict:
    """Independent direct-value potency check on a declared finite grid.

    This is a control, not the proof of the identity; the exact normal-form
    cancellation above is the universal ordered-cone check.
    """
    n = certificate["n"]
    permutations = list(itertools.permutations(range(n)))
    points = list(itertools.combinations_with_replacement(range(-2, 3), n))
    original = certificate["terms"][mutation_index]["coefficient"]
    mutated = original + Fraction(1, 2 * original.denominator)
    mutant_nonzero = 0
    for point in points:
        values = [direct_atom_value(term["pair"], point, permutations) for term in certificate["terms"]]
        target = Fraction(point[-1])
        observed = sum(term["coefficient"] * value for term, value in zip(certificate["terms"], values))
        if observed != target:
            raise AssertionError(f"direct grid rejected known MAX{n} certificate at {point}")
        mutant = observed + (mutated - original) * values[mutation_index]
        if mutant != target:
            mutant_nonzero += 1
    if mutant_nonzero == 0:
        raise AssertionError("direct grid did not detect the coefficient mutant")
    return {
        "value_alphabet": [-2, -1, 0, 1, 2],
        "sorted_points": len(points),
        "known_certificate": "PASS",
        "mutant_nonzero_points": mutant_nonzero,
        "scope": "potency control only; finite grid is not a universal identity proof",
    }


NODE_MATCH = categorical_node_match("kind", None)


def incidence_gadget(pair: Template, swap: bool = False, ambient_n: int | None = None) -> nx.Graph:
    """Encode a two-coloured multigraph as a vertex/edge incidence graph.

    A loop edge-node has degree one; parallel edges remain distinct edge-nodes.
    This avoids MultiGraphMatcher's loop-degree and edge-bijection ambiguities.
    """
    result = nx.Graph()
    sides = pair[::-1] if swap else pair
    active = {v for side in sides for edge in side for v in edge}
    vertices: Iterable[int] = range(1, ambient_n + 1) if ambient_n is not None else sorted(active)
    for vertex in vertices:
        result.add_node(("v", vertex), kind="V")
    for colour, side in enumerate(sides):
        for edge_index, (a, b) in enumerate(side):
            edge_node = ("e", colour, edge_index)
            result.add_node(edge_node, kind=f"E{colour}")
            result.add_edge(edge_node, ("v", a))
            result.add_edge(edge_node, ("v", b))
    return result


def same_template(first: Template, second: Template) -> bool:
    first_graph = incidence_gadget(first)
    return GraphMatcher(first_graph, incidence_gadget(second), node_match=NODE_MATCH).is_isomorphic() or GraphMatcher(
        first_graph, incidence_gadget(second, swap=True), node_match=NODE_MATCH
    ).is_isomorphic()


def swap_isomorphic(pair: Template) -> bool:
    return GraphMatcher(
        incidence_gadget(pair), incidence_gadget(pair, swap=True), node_match=NODE_MATCH
    ).is_isomorphic()


def vertex_automorphism_count(pair: Template, n: int) -> int:
    """Count coordinate permutations fixing the ordered colour pair.

    Pynauty also permutes indistinguishable parallel edge-nodes.  Dividing by
    the factorial of each within-colour edge multiplicity removes exactly that
    incidence-gadget nuisance factor.
    """
    graph = incidence_gadget(pair, ambient_n=n)
    nodes = list(graph.nodes)
    index = {node: i for i, node in enumerate(nodes)}
    adjacency = {index[node]: {index[nbr] for nbr in graph.neighbors(node)} for node in nodes}
    colour_classes: dict[str, set[int]] = {}
    for node in nodes:
        colour_classes.setdefault(graph.nodes[node]["kind"], set()).add(index[node])
    nauty_graph = pynauty.Graph(
        len(nodes), adjacency_dict=adjacency, vertex_coloring=list(colour_classes.values())
    )
    _, mantissa, exponent, _, _ = pynauty.autgrp(nauty_graph)
    gadget_count = int(round(mantissa)) * (10 ** int(exponent))
    nuisance = 1
    for side in pair:
        for multiplicity in Counter(side).values():
            nuisance *= math.factorial(multiplicity)
    if gadget_count % nuisance:
        raise AssertionError("incidence automorphism count has an unexpected nuisance factor")
    return gadget_count // nuisance


def certificate_basis_multiplicity(pair: Template, n: int) -> int:
    """Multiplicity of each distinct unordered labelled atom in F_{A,B}."""
    automorphisms = vertex_automorphism_count(pair, n)
    same_sides = tuple(sorted(pair[0])) == tuple(sorted(pair[1]))
    return automorphisms * (2 if swap_isomorphic(pair) and not same_sides else 1)


def matched_base_indices(pair: Template, base: Sequence[dict]) -> tuple[int, ...]:
    return tuple(index for index, term in enumerate(base) if same_template(pair, term["pair"]))


def deleted_edge_operator_matrices(base: Sequence[dict], target: dict) -> dict[str, list[list[int]]]:
    names = ("uniform_edge_extension", "common_edge_padding", "strict_leaf_padding", "general_leaf_padding")
    matrices = {name: [] for name in names}
    class_cache: dict[Template, tuple[int, ...]] = {}

    def classes(pair: Template) -> tuple[int, ...]:
        key = (tuple(sorted(pair[0])), tuple(sorted(pair[1])))
        if key not in class_cache:
            class_cache[key] = matched_base_indices(key, base)
        return class_cache[key]

    for term in target["terms"]:
        pair = term["pair"]
        left, right = pair
        rows = {name: [0] * len(base) for name in names}
        for keep_left_indices in itertools.combinations(range(4), 2):
            keep_left_set = set(keep_left_indices)
            kept_left = tuple(left[index] for index in keep_left_indices)
            deleted_left = tuple(left[index] for index in range(4) if index not in keep_left_set)
            for keep_right_indices in itertools.combinations(range(4), 2):
                keep_right_set = set(keep_right_indices)
                kept_right = tuple(right[index] for index in keep_right_indices)
                deleted_right = tuple(right[index] for index in range(4) if index not in keep_right_set)
                reduced = (kept_left, kept_right)
                base_indices = classes(reduced)
                if not base_indices:
                    continue
                for base_index in base_indices:
                    rows["uniform_edge_extension"][base_index] += 1
                if tuple(sorted(deleted_left)) == tuple(sorted(deleted_right)):
                    for base_index in base_indices:
                        rows["common_edge_padding"][base_index] += 1

                base_vertices = {v for side in reduced for edge in side for v in edge}
                deleted = deleted_left + deleted_right
                if all(any(v not in base_vertices for v in edge) for edge in deleted):
                    outside_occurrences = [v for edge in deleted for v in edge if v not in base_vertices]
                    counts = Counter(outside_occurrences)
                    if counts and all(value == 1 for value in counts.values()):
                        for base_index in base_indices:
                            rows["general_leaf_padding"][base_index] += 1
                    if (
                        len(outside_occurrences) == 4
                        and len(set(outside_occurrences)) == 4
                        and all(sum(v not in base_vertices for v in edge) == 1 for edge in deleted)
                    ):
                        for base_index in base_indices:
                            rows["strict_leaf_padding"][base_index] += 1
        for name in names:
            matrices[name].append(rows[name])
    return matrices


def suppress_vertex(side: Side, vertex: int) -> Side | None:
    incident: list[tuple[int, int]] = []
    for index, (a, b) in enumerate(side):
        if a == vertex and b == vertex:
            return None
        if a == vertex:
            incident.append((index, b))
        elif b == vertex:
            incident.append((index, a))
    if len(incident) != 2:
        return None
    removed = {index for index, _ in incident}
    result = [edge for index, edge in enumerate(side) if index not in removed]
    result.append(tuple(sorted((incident[0][1], incident[1][1]))))
    return tuple(sorted(result))


def two_subdivision_reductions(side: Side, other: Side) -> set[Side]:
    side_vertices = {v for edge in side for v in edge}
    other_vertices = {v for edge in other for v in edge}
    exclusive = side_vertices - other_vertices
    reductions: set[Side] = set()
    for first, second in itertools.permutations(exclusive, 2):
        after_first = suppress_vertex(side, first)
        if after_first is None:
            continue
        after_second = suppress_vertex(after_first, second)
        if after_second is not None:
            reductions.add(after_second)
    return reductions


def subdivision_matrix(base: Sequence[dict], target: dict) -> list[list[int]]:
    rows = []
    for term in target["terms"]:
        left, right = term["pair"]
        left_reductions = two_subdivision_reductions(left, right)
        right_reductions = two_subdivision_reductions(right, left)
        row = [0] * len(base)
        for reduced_left in left_reductions:
            for reduced_right in right_reductions:
                for base_index in matched_base_indices((reduced_left, reduced_right), base):
                    row[base_index] += 1
        rows.append(row)
    return rows


def convolution_matrix(base: Sequence[dict], target: dict) -> tuple[list[list[int]], list[tuple[int, int]]]:
    columns = [(i, j) for i in range(len(base)) for j in range(i, len(base))]
    column_index = {pair: index for index, pair in enumerate(columns)}
    class_cache: dict[Template, tuple[int, ...]] = {}

    def classes(pair: Template) -> tuple[int, ...]:
        key = (tuple(sorted(pair[0])), tuple(sorted(pair[1])))
        if key not in class_cache:
            class_cache[key] = matched_base_indices(key, base)
        return class_cache[key]

    matrix = []
    for term in target["terms"]:
        left, right = term["pair"]
        row = [0] * len(columns)
        for first_left_indices in itertools.combinations(range(4), 2):
            first_left_set = set(first_left_indices)
            second_left_indices = tuple(index for index in range(4) if index not in first_left_set)
            for first_right_indices in itertools.combinations(range(4), 2):
                first_right_set = set(first_right_indices)
                second_right_indices = tuple(index for index in range(4) if index not in first_right_set)
                first = (
                    tuple(left[index] for index in first_left_indices),
                    tuple(right[index] for index in first_right_indices),
                )
                second = (
                    tuple(left[index] for index in second_left_indices),
                    tuple(right[index] for index in second_right_indices),
                )
                for first_class in classes(first):
                    for second_class in classes(second):
                        key = tuple(sorted((first_class, second_class)))
                        row[column_index[key]] += 1
        matrix.append(row)
    return matrix, columns


def exact_rank_result(matrix: list[list[int]], coefficients: Sequence[Fraction]) -> dict:
    if len(matrix) != len(coefficients):
        raise ValueError("matrix/target row mismatch")
    candidate = Matrix(matrix)
    target = Matrix([Rational(value.numerator, value.denominator) for value in coefficients])
    candidate_rank = candidate.rank()
    augmented_rank = candidate.row_join(target).rank()
    return {
        "rows": candidate.rows,
        "columns": candidate.cols,
        "support_rows_covered": sum(any(value for value in row) for row in matrix),
        "candidate_rank_Q": candidate_rank,
        "augmented_rank_Q": augmented_rank,
        "target_in_column_span": candidate_rank == augmented_rank,
    }


def two_row_uniform_separator(matrix: list[list[int]], coefficients: Sequence[Fraction]) -> dict:
    if matrix[1] != [2 * value for value in matrix[0]]:
        raise AssertionError("predeclared two-row uniform-extension separator no longer applies")
    residual = coefficients[1] - 2 * coefficients[0]
    if residual == 0:
        raise AssertionError("predeclared coefficient mutation/control lost potency")
    return {
        "row_indices_zero_based": [0, 1],
        "matrix_relation": "row_1 - 2*row_0 = 0",
        "target_residual": fraction_text(residual),
        "row_0": matrix[0],
        "row_1": matrix[1],
    }


def template_stats(certificate: dict) -> dict:
    active_histogram: Counter[int] = Counter()
    common_edge_histogram: Counter[int] = Counter()
    coefficient_signs: Counter[str] = Counter()
    coefficients = []
    for term in certificate["terms"]:
        left, right = term["pair"]
        active_histogram[len({v for side in term["pair"] for edge in side for v in edge})] += 1
        left_counter, right_counter = Counter(left), Counter(right)
        common_edge_histogram[sum((left_counter & right_counter).values())] += 1
        coefficient = term["coefficient"]
        coefficient_signs["positive" if coefficient > 0 else "negative"] += 1
        coefficients.append(coefficient)
    denominator_lcm = math.lcm(*(value.denominator for value in coefficients))
    return {
        "terms": len(certificate["terms"]),
        "active_vertex_histogram": {str(k): v for k, v in sorted(active_histogram.items())},
        "common_edge_multiplicity_histogram": {
            str(k): v for k, v in sorted(common_edge_histogram.items())
        },
        "coefficient_signs": dict(sorted(coefficient_signs.items())),
        "distinct_coefficients": len(set(coefficients)),
        "coefficient_denominator_lcm": denominator_lcm,
    }


def compact_side(side: Side) -> str:
    return "{" + ", ".join(f"m_{{{a},{b}}}" for a, b in side) + "}"


def render_identities(certificates: Sequence[dict], observed_hashes: dict[str, str]) -> str:
    lines = [
        "# Exact symbolic decoding of the public MAX certificates",
        "",
        "For `m_{ab}(x) = max(x_a,x_b)`, put",
        "",
        "```text",
        "Phi[A,B](x) = max(sum_{e in A} m_e(x), sum_{e in B} m_e(x))",
        "F_n[A,B](x) = sum_{sigma in S_n} Phi[A,B](sigma x).",
        "```",
        "",
        "The symmetrization is an **unnormalized** sum over all `n!` permutations.  The exact",
        "identity encoded by each file is `MAX_n = sum_t coefficient_t * F_n[A_t,B_t]`.",
        "Repeated pairs are multiset occurrences; `(a,a)` means `x_a`.",
        "",
    ]
    for certificate in certificates:
        n, k = certificate["n"], certificate["k"]
        filename = f"certificate_{n}_{k}.json"
        lines.extend(
            [
                f"## MAX{n} (k={k})",
                "",
                f"Source SHA-256: `{observed_hashes[filename]}`",
                "",
                f"`MAX_{n}(x) =`",
                "",
            ]
        )
        for index, term in enumerate(certificate["terms"]):
            prefix = "+" if term["coefficient"] > 0 and index else ""
            left, right = term["pair"]
            lines.append(
                f"- `{prefix}{fraction_text(term['coefficient'])}` · "
                f"`F_{n}[{compact_side(left)}, {compact_side(right)}]`"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def self_test(cert5: dict, cert6: dict) -> dict:
    five = residual_for_certificate(cert5)
    six = residual_for_certificate(cert6)
    if not five["passes"] or not six["passes"]:
        raise AssertionError("known MAX5/MAX6 certificate did not decode to the target")

    mutants = []
    for certificate in (cert5, cert6):
        # Mutate a genuinely nonlinear atom so this control exercises hinge
        # cancellation, not only the final linear-vector comparison.
        mutation_index = 1
        original = certificate["terms"][mutation_index]["coefficient"]
        mutated = original + Fraction(1, 2 * original.denominator)
        result = residual_for_certificate(certificate, {mutation_index: mutated})
        if result["passes"]:
            raise AssertionError("one-coefficient mutant was accepted")
        mutants.append(
            {
                "n": certificate["n"],
                "term_index": mutation_index,
                "original": fraction_text(original),
                "mutated": fraction_text(mutated),
                "result": "REJECTED",
                "bad_linear_count": result["bad_linear_count"],
                "bad_hinge_count": result["bad_hinge_count"],
                "residual_sha256": result["residual_sha256"],
            }
        )

    # Parser must fail closed on an out-of-range endpoint.
    malformed = json.loads((CERT_DIR / "certificate_5_2.json").read_text(encoding="utf-8"))
    malformed["terms"][0]["pair"][0][0][0] = 0
    temporary = SELF_DIR / ".self-test-malformed.json"
    try:
        temporary.write_text(json.dumps(malformed), encoding="utf-8")
        try:
            read_certificate(temporary, 5, 2)
        except ValueError:
            parser_control = "REJECTED"
        else:
            raise AssertionError("malformed endpoint control was accepted")
    finally:
        temporary.unlink(missing_ok=True)

    # Cross-check the nauty incidence quotient against direct coordinate
    # permutations on all seven small base templates.
    for n, terms in ((cert5["n"], cert5["terms"]), (cert6["n"], cert6["terms"])):
        for term in terms:
            pair = term["pair"]
            expected = vertex_automorphism_count(pair, n)
            actual = 0
            for permutation in itertools.permutations(range(1, n + 1)):
                relabel = {index + 1: permutation[index] for index in range(n)}
                mapped = tuple(
                    tuple(tuple(sorted((relabel[a], relabel[b]))) for a, b in side)
                    for side in pair
                )
                if tuple(sorted(mapped[0])) == tuple(sorted(pair[0])) and tuple(sorted(mapped[1])) == tuple(
                    sorted(pair[1])
                ):
                    actual += 1
            if actual != expected:
                raise AssertionError(f"nauty automorphism mismatch: {actual} != {expected}")

    return {
        "known_answer_MAX5": "PASS",
        "known_answer_MAX6": "PASS",
        "direct_value_grid_MAX5": direct_grid_control(cert5, 1),
        "direct_value_grid_MAX6": direct_grid_control(cert6, 1),
        "one_coefficient_mutants": mutants,
        "malformed_endpoint_parser_control": parser_control,
        "small_template_automorphism_crosscheck": "PASS",
    }


def run_full(output_report: Path, output_identities: Path) -> dict:
    observed_hashes = verify_pins()
    cert5 = read_certificate(CERT_DIR / "certificate_5_2.json", 5, 2)
    cert6 = read_certificate(CERT_DIR / "certificate_6_2.json", 6, 2)
    cert10 = read_certificate(CERT_DIR / "certificate_10_4.json", 10, 4)
    controls = self_test(cert5, cert6)

    exact_decodes = {}
    for certificate in (cert5, cert6):
        residual = residual_for_certificate(certificate)
        exact_decodes[f"MAX{certificate['n']}"] = {
            "terms": len(certificate["terms"]),
            "permutations_per_term": math.factorial(certificate["n"]),
            "result": "EXACT_IDENTITY" if residual["passes"] else "REJECTED",
            "bad_linear_count": residual["bad_linear_count"],
            "bad_hinge_count": residual["bad_hinge_count"],
            "residual_sha256": residual["residual_sha256"],
            "atom_variable_hinge_counts": [item["variable_hinges"] for item in residual["atom_stats"]],
        }
        if not residual["passes"]:
            raise AssertionError(f"MAX{certificate['n']} failed exact decoding")

    base = cert5["terms"] + cert6["terms"]
    base_labels = [f"MAX5-term-{i}" for i in range(len(cert5["terms"]))] + [
        f"MAX6-term-{i}" for i in range(len(cert6["terms"]))
    ]
    for i in range(len(base)):
        for j in range(i):
            if same_template(base[i]["pair"], base[j]["pair"]):
                raise AssertionError(f"base certificate templates {i} and {j} unexpectedly coincide")

    coefficients = [term["coefficient"] for term in cert10["terms"]]
    deletion_matrices = deleted_edge_operator_matrices(base, cert10)
    subdivision = subdivision_matrix(base, cert10)
    convolution, convolution_columns = convolution_matrix(base, cert10)
    matrices = {**deletion_matrices, "strict_edge_subdivision": subdivision, "lower_atom_convolution": convolution}
    operator_results = {name: exact_rank_result(matrix, coefficients) for name, matrix in matrices.items()}

    uniform = deletion_matrices["uniform_edge_extension"]
    uniform_separator = two_row_uniform_separator(uniform, coefficients)
    multiplicities = [certificate_basis_multiplicity(term["pair"], 10) for term in cert10["terms"]]
    normalization_tests = {}
    for label, normalized in (
        ("raw_certificate_coefficients", coefficients),
        ("times_F_basis_multiplicity", [c * w for c, w in zip(coefficients, multiplicities)]),
        ("divided_by_F_basis_multiplicity", [c / w for c, w in zip(coefficients, multiplicities)]),
    ):
        normalization_tests[label] = exact_rank_result(uniform, normalized)

    combined_names = [
        "common_edge_padding",
        "strict_leaf_padding",
        "general_leaf_padding",
        "strict_edge_subdivision",
        "lower_atom_convolution",
        "uniform_edge_extension",
    ]
    combined_matrix = [
        sum((matrices[name][row_index] for name in combined_names), [])
        for row_index in range(len(coefficients))
    ]
    combined_result = exact_rank_result(combined_matrix, coefficients)

    symbolic_text = render_identities((cert5, cert6, cert10), observed_hashes)
    output_identities.parent.mkdir(parents=True, exist_ok=True)
    output_identities.write_text(symbolic_text, encoding="utf-8")

    report = {
        "schema": "max11-g0047-lower-certificate-lift-audit-v1",
        "result": "NO_EXACT_RECURRENCE_IN_TESTED_OPERATOR_LANGUAGE",
        "mode": "independent bounded structural audit; no import of public verifier",
        "inputs_sha256": observed_hashes,
        "audit_script_sha256": sha256_file(Path(__file__)),
        "symbolic_identities": {
            "path": str(output_identities.relative_to(ROOT)),
            "sha256": sha256_file(output_identities),
            "definition": "MAX_n = sum_t coefficient_t * sum_{sigma in S_n} Phi[A_t,B_t](sigma x)",
            "MAX10_terms_rendered": len(cert10["terms"]),
        },
        "environment": {
            "python": platform.python_version(),
            "networkx": nx.__version__,
            "pynauty": getattr(pynauty, "__version__", "unknown"),
            "sympy": sympy.__version__,
            "platform": platform.platform(),
        },
        "controls": controls,
        "exact_decodes": exact_decodes,
        "MAX10_structure": template_stats(cert10),
        "base_template_order": base_labels,
        "operator_definitions": {
            "uniform_edge_extension": "choose two retained edge occurrences on each colour; the retained 2+2 template must be one of the seven lower-certificate atoms; all completions have one coefficient per source atom",
            "common_edge_padding": "uniform edge extension restricted to identical deleted two-edge multisets on both colours",
            "strict_leaf_padding": "each of four deleted edges attaches exactly one distinct new degree-one vertex to the retained base",
            "general_leaf_padding": "every deleted edge contains a vertex outside the retained base and every such outside vertex has total deleted-edge degree one",
            "strict_edge_subdivision": "reverse two subdivisions per colour by suppressing four distinct vertices, each exclusive to one colour and of degree two there",
            "lower_atom_convolution": "partition both four-edge colour multisets into two 2+2 templates, each isomorphic up to its own global colour swap to a lower-certificate support atom",
        },
        "operator_results": operator_results,
        "uniform_extension_normalization_sensitivity": normalization_tests,
        "uniform_extension_exact_separator": uniform_separator,
        "combined_operator_columns": combined_names,
        "combined_operator_result": combined_result,
        "functional_obstruction": {
            "statement": "isolated-variable orbit sums of lower MAX identities, even with common-edge padding, lie in the linear span of proper-subset maxima and cannot equal MAX10",
            "proof_file": "artifacts/cleanroom/G-0047-lift-audit/OBSTRUCTION.md",
        },
        "positive_observable": {
            "required": "an explicit coefficient-level recurrence reconstructing every MAX10 term and inducing an exact arbitrary-chamber MAX11 identity",
            "observed": False,
        },
        "retry_predicate": "Retry this route only after specifying an equivariant operator outside the tested language (for example topology-dependent extension weights or a nonlinear identity), producing its complete orbit-incidence matrix including absent MAX10 templates, and passing exact Q span plus complete hinge replay. A support-only match or finite chamber sample does not fire the predicate.",
        "no_claim": "This audit rejects only the explicitly defined recurrence language for the frozen 402-term public MAX10 coefficient vector. It does not prove that no other MAX10 certificate has an inductive form, does not prove that no exact MAX11 pair-atom certificate exists, and says nothing by itself about unrestricted arbitrary-real-weight two-hidden-layer ReLU representations. Agreement on sampled chambers or quotient rows would not prove MAX11; none is used here.",
    }
    if any(value["target_in_column_span"] for value in operator_results.values()) or combined_result[
        "target_in_column_span"
    ]:
        raise AssertionError("a tested recurrence unexpectedly succeeded; adjudicate before emitting the negative verdict")
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output-report", type=Path, default=SELF_DIR / "audit_report_v1.json")
    parser.add_argument("--output-identities", type=Path, default=SELF_DIR / "DECODED_IDENTITIES.md")
    args = parser.parse_args()

    verify_pins()
    cert5 = read_certificate(CERT_DIR / "certificate_5_2.json", 5, 2)
    cert6 = read_certificate(CERT_DIR / "certificate_6_2.json", 6, 2)
    if args.self_test:
        print(json.dumps(self_test(cert5, cert6), sort_keys=True, indent=2))
        return

    for output in (args.output_report.resolve(), args.output_identities.resolve()):
        try:
            output.relative_to(ROOT.resolve())
        except ValueError as exc:
            raise SystemExit(f"refusing output outside workspace: {output}") from exc
    report = run_full(args.output_report.resolve(), args.output_identities.resolve())
    print(json.dumps({"result": report["result"], "report": str(args.output_report)}, sort_keys=True))


if __name__ == "__main__":
    main()
