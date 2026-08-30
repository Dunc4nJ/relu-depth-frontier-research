#!/usr/bin/env python3
"""Independent exact audit of the G-0075 universal four-level arrangement."""

from __future__ import annotations

from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, product
import json
from math import gcd, lcm


PANEL_SEED = "max11-g0075-genuinely-four-valued-panels-v1"
DENOMINATOR = 257


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def primitive(vector: tuple[int, ...]) -> tuple[int, ...]:
    divisor = 0
    for value in vector:
        divisor = gcd(divisor, abs(value))
    if divisor == 0:
        raise ValueError("zero vector")
    result = tuple(value // divisor for value in vector)
    if next(value for value in result if value) < 0:
        result = tuple(-value for value in result)
    return result


def universal_lines() -> list[tuple[int, int, int, int]]:
    result: set[tuple[int, int, int, int]] = set()
    for d0, d1, d2 in product(range(-6, 7), repeat=3):
        d3 = -d0 - d1 - d2
        raw = (d0, d1, d2, d3)
        if not any(raw) or sum(max(value, 0) for value in raw) > 6:
            continue
        line = primitive(raw)
        vertex_values = (
            line[3],
            line[2] + line[3],
            line[1] + line[2] + line[3],
        )
        if min(vertex_values) < 0 < max(vertex_values):
            result.add(line)
    return sorted(result)


def structural_switch_lines() -> tuple[list[tuple[int, int, int, int]], dict[str, int]]:
    """Second derivation from p, q, p-q, p+q after flattening the nested max."""
    levels = ((0, 0, 0), (0, 1, 0), (0, 0, 1), (1, 0, 0))  # constant, a, b
    four_sums = {
        tuple(sum(items[index][coordinate] for index in range(4)) for coordinate in range(3))
        for items in product(levels, repeat=4)
    }
    p_forms = {
        tuple(first[index] - second[index] for index in range(3))
        for first in four_sums for second in four_sums
    }
    q_forms = {
        tuple(first[index] + second[index] - 2 * anchor[index] for index in range(3))
        for first, second, anchor in product(levels, repeat=3)
    }
    switch_forms = p_forms | q_forms | {
        tuple(p[index] + sign * q[index] for index in range(3))
        for p in p_forms for q in q_forms for sign in (-1, 1)
    }
    primitive_forms = {primitive(form) for form in switch_forms if any(form)}
    vertices = ((0, 0), (0, 1), (1, 1))
    cutting = {
        form for form in primitive_forms
        if min(form[0] + form[1] * x + form[2] * y for x, y in vertices) < 0
        < max(form[0] + form[1] * x + form[2] * y for x, y in vertices)
    }
    lines = sorted({primitive((-constant - a - b, a, b, constant))
                    for constant, a, b in cutting})
    return lines, {
        "four_edge_sum_forms": len(four_sums),
        "p_forms": len(p_forms),
        "q_forms": len(q_forms),
        "switch_forms": len(switch_forms),
        "primitive_lines_before_domain_clip": len(primitive_forms),
        "cutting_lines": len(lines),
    }


def line_value(line: tuple[int, int, int, int], point: tuple[Fraction, Fraction]) -> Fraction:
    return line[1] * point[0] + line[2] * point[1] + line[3]


def interior_intersections(lines: list[tuple[int, int, int, int]]):
    incidences: dict[tuple[Fraction, Fraction], set[int]] = defaultdict(set)
    for first, second in combinations(range(len(lines)), 2):
        _, b, c, a = lines[first]
        _, e, f, d = lines[second]
        determinant = b * f - c * e
        if determinant == 0:
            continue
        x = Fraction(c * d - a * f, determinant)
        y = Fraction(a * e - b * d, determinant)
        if 0 < x < y < 1:
            incidences[(x, y)].update((first, second))
    return incidences


def clean_polygon(polygon: list[tuple[Fraction, Fraction]]):
    result: list[tuple[Fraction, Fraction]] = []
    for point in polygon:
        if not result or point != result[-1]:
            result.append(point)
    if len(result) > 1 and result[0] == result[-1]:
        result.pop()
    while len(result) >= 3:
        kept = []
        for index, point in enumerate(result):
            before = result[index - 1]
            after = result[(index + 1) % len(result)]
            cross = ((point[0] - before[0]) * (after[1] - point[1])
                     - (point[1] - before[1]) * (after[0] - point[0]))
            if cross:
                kept.append(point)
        if len(kept) == len(result):
            break
        result = kept
    return result


def clip(polygon, line, side):
    result = []
    for first, second in zip(polygon, polygon[1:] + polygon[:1]):
        left = side * line_value(line, first)
        right = side * line_value(line, second)
        if left >= 0:
            result.append(first)
        if (left >= 0) != (right >= 0):
            fraction = left / (left - right)
            result.append((
                first[0] + fraction * (second[0] - first[0]),
                first[1] + fraction * (second[1] - first[1]),
            ))
    return clean_polygon(result)


def exact_cells(lines):
    cells = [(
        [(Fraction(0), Fraction(0)), (Fraction(0), Fraction(1)),
         (Fraction(1), Fraction(1))],
        (),
    )]
    for line in lines:
        next_cells = []
        for polygon, signature in cells:
            values = [line_value(line, point) for point in polygon]
            positive = any(value > 0 for value in values)
            negative = any(value < 0 for value in values)
            if positive and negative:
                next_cells.append((clip(polygon, line, -1), signature + (-1,)))
                next_cells.append((clip(polygon, line, +1), signature + (+1,)))
            else:
                next_cells.append((polygon, signature + ((+1 if positive else -1),)))
        cells = next_cells
    return cells


def panel_ratios():
    ratios = []
    seen = set()
    counter = 0
    while len(ratios) < 128:
        digest = sha256(f"{PANEL_SEED};panel={counter}\n".encode()).digest()
        first = 1 + int.from_bytes(digest[:8], "big") % 256
        second = 1 + int.from_bytes(digest[8:16], "big") % 256
        counter += 1
        if first == second:
            continue
        ratio = tuple(sorted((first, second)))
        if ratio not in seen:
            seen.add(ratio)
            ratios.append(ratio)
    return ratios


def main() -> None:
    lines = universal_lines()
    structural_lines, structural_counts = structural_switch_lines()
    assert structural_lines == lines
    intersections = interior_intersections(lines)
    cells = exact_cells(lines)
    line_manifest = [list(line) for line in lines]
    incidence_manifest = [
        [[x.numerator, x.denominator], [y.numerator, y.denominator], sorted(indices)]
        for (x, y), indices in sorted(intersections.items())
    ]
    signature_manifest = [
        list(signature) for _polygon, signature in sorted(cells, key=lambda item: item[1])
    ]
    polygon_manifest = []
    for polygon, signature in sorted(cells, key=lambda item: item[1]):
        start = min(range(len(polygon)), key=lambda index: polygon[index])
        polygon = polygon[start:] + polygon[:start]
        polygon_manifest.append({
            "signature": list(signature),
            "vertices": [
                [[x.numerator, x.denominator], [y.numerator, y.denominator]]
                for x, y in polygon
            ],
        })
    memberships = []
    for panel, (a, b) in enumerate(panel_ratios()):
        values = [line[1] * a + line[2] * b + line[3] * DENOMINATOR for line in lines]
        memberships.append({
            "panel": panel,
            "levels": [0, a, b, DENOMINATOR],
            "strong_signature": [(value > 0) - (value < 0) for value in values],
            "weak_signature": [int(value > 0) for value in values],
            "zero_wall_indices": [index for index, value in enumerate(values) if value == 0],
        })
    panel_manifest = [
        {"panel": index, "levels": [0, a, b, DENOMINATOR]}
        for index, (a, b) in enumerate(panel_ratios())
    ]
    weak64 = sorted({tuple(row["weak_signature"]) for row in memberships[:64]})
    weak128 = sorted({tuple(row["weak_signature"]) for row in memberships})
    all_vertices = set(intersections)
    for line in lines:
        _d0, d1, d2, d3 = line
        if d2:
            y = Fraction(-d3, d2)
            if 0 <= y <= 1:
                all_vertices.add((Fraction(0), y))
        if d1:
            x = Fraction(-d2 - d3, d1)
            if 0 <= x <= 1:
                all_vertices.add((x, Fraction(1)))
        if d1 + d2:
            x = Fraction(-d3, d1 + d2)
            if 0 <= x <= 1:
                all_vertices.add((x, x))
    all_vertices.update(((Fraction(0), Fraction(0)), (Fraction(0), Fraction(1)),
                         (Fraction(1), Fraction(1))))
    polygon_vertices = {
        point for polygon, _signature in cells for point in polygon
    }
    assert polygon_vertices == all_vertices
    interior_integer_levels = []
    for x, y in sorted(intersections):
        denominator = lcm(x.denominator, y.denominator)
        a = x.numerator * (denominator // x.denominator)
        b = y.numerator * (denominator // y.denominator)
        divisor = gcd(gcd(a, b), denominator)
        interior_integer_levels.append([a // divisor, b // divisor, denominator // divisor])
    report = {
        "structural_derivation": structural_counts,
        "lines": len(lines),
        "panel_manifest_sha256": sha256(canonical_bytes(panel_manifest)).hexdigest(),
        "line_manifest_sha256": sha256(canonical_bytes(line_manifest)).hexdigest(),
        "interior_vertices": len(intersections),
        "incidence_histogram": dict(sorted(Counter(map(len, intersections.values())).items())),
        "incidence_manifest_sha256": sha256(canonical_bytes(incidence_manifest)).hexdigest(),
        "sum_incidence_minus_one": sum(len(item) - 1 for item in intersections.values()),
        "cells_by_incidence": 1 + len(lines) + sum(len(item) - 1 for item in intersections.values()),
        "cells_by_exact_polygon_split": len(cells),
        "unique_cell_signatures": len({signature for _polygon, signature in cells}),
        "cell_signature_manifest_sha256": sha256(canonical_bytes(signature_manifest)).hexdigest(),
        "cell_polygon_manifest_sha256": sha256(canonical_bytes(polygon_manifest)).hexdigest(),
        "first_64_weak_signatures": len({tuple(row["weak_signature"]) for row in memberships[:64]}),
        "all_128_weak_signatures": len({tuple(row["weak_signature"]) for row in memberships}),
        "first_64_weak_signature_set_sha256": sha256(canonical_bytes([list(row) for row in weak64])).hexdigest(),
        "all_128_weak_signature_set_sha256": sha256(canonical_bytes([list(row) for row in weak128])).hexdigest(),
        "first_64_off_wall_panels": sum(not row["zero_wall_indices"] for row in memberships[:64]),
        "all_128_off_wall_panels": sum(not row["zero_wall_indices"] for row in memberships),
        "first_64_open_cells_hit": len({tuple(row["strong_signature"]) for row in memberships[:64] if not row["zero_wall_indices"]}),
        "all_128_open_cells_hit": len({tuple(row["strong_signature"]) for row in memberships if not row["zero_wall_indices"]}),
        "boundary_panels_first_64": sum(bool(row["zero_wall_indices"]) for row in memberships[:64]),
        "boundary_panels_all_128": sum(bool(row["zero_wall_indices"]) for row in memberships),
        "all_arrangement_vertices": len(all_vertices),
        "boundary_arrangement_vertices": len(all_vertices) - len(intersections),
        "polygon_vertex_set_equals_arrangement_vertex_set": True,
        "interior_vertex_integer_level_manifest_sha256": sha256(canonical_bytes(interior_integer_levels)).hexdigest(),
        "maximum_interior_vertex_denominator": max(row[2] for row in interior_integer_levels),
        "positive_profile_rows_at_all_vertices": len(all_vertices) * 120,
        "positive_profile_rows_at_interior_vertices": len(intersections) * 120,
    }
    expected = {
        "lines": 150,
        "line_manifest_sha256": "eda2cd19ab89cb47fb58221070311b040ae5061c220b5477cdb11d1980c287a7",
        "interior_vertices": 1539,
        "sum_incidence_minus_one": 2623,
        "cells_by_incidence": 2774,
        "cells_by_exact_polygon_split": 2774,
        "unique_cell_signatures": 2774,
        "first_64_weak_signatures": 62,
        "all_128_weak_signatures": 122,
        "first_64_open_cells_hit": 56,
        "all_128_open_cells_hit": 108,
        "all_arrangement_vertices": 1575,
        "maximum_interior_vertex_denominator": 36,
    }
    for key, value in expected.items():
        assert report[key] == value, (key, report[key], value)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
