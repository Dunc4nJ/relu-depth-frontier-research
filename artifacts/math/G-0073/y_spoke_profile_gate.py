#!/usr/bin/env python3
"""Exact symmetric-profile gate for the non-graphical MAX11 Y-spoke family.

This is a necessary construction sieve, not a global identity verifier.  It
uses free coefficients on full S_11 orbit representatives; it never inherits
the MAX10 coefficients.  A profile survivor must advance to generic-slice and
complete CPWL replay before it can support a MAX11 claim.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import importlib
from itertools import combinations, permutations
import json
from math import factorial
import os
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Sequence

import flint
from flint import fmpq_mat, fmpz_mat, nmod_mat
import networkx as nx
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
G0006_SELECTOR = ROOT / "artifacts/math/G-0006/evaluate_minimal_lifts.py"

SCHEMA = "max11-g0073-y-spoke-profile-gate-v1"
PREFLIGHT_SCHEMA = "max11-g0073-y-spoke-orbit-preflight-v1"
OLD_N = 10
N = 11
EXPECTED_BASES = 252
EXPECTED_RAW_SEEDS = 18_400
PRIMES = (1_000_003, 1_000_033)
DEFAULT_PROFILE_BUDGET = 600_000

EXPECTED_BINDINGS = {
    "certificate_10_4": (
        CERTIFICATE,
        "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    ),
    "g0006_selector": (
        G0006_SELECTOR,
        "a2ed2e6d8749770fb5a0732ab65f84b592d0562c68947f5ae35676237e1f2862",
    ),
}

# Filled only after the orbit/charge preflight is frozen and reviewed.  The
# registered matrix path refuses to run while any pin is absent.
EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256: str | None = (
    "d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8"
)
EXPECTED_RAW_SEED_MANIFEST_SHA256: str | None = (
    "6afd2be571bdb14307642486bb4b57bc9b56a770838a946af0ca28edd4d6bf1b"
)
EXPECTED_ORBIT_MANIFEST_SHA256: str | None = (
    "19bdedd49d7c59706b7befdd6b676f410fc7f4e5b2c4aa417da34c2df66deec3"
)
EXPECTED_REPRESENTATIVE_MANIFEST_SHA256: str | None = (
    "324b1d1b76f073ddd2228b8a0b67971b8d766c32e4a00252c7c86e0c3a2483c7"
)
EXPECTED_CHARGE_ROWS_SHA256: str | None = (
    "791d9474837d396f310d13fb9a512f132828073af19ae83411d7ac8fcbfc9335"
)
EXPECTED_ORBIT_COUNT: int | None = 8_104


Edge = tuple[int, int]
Side = tuple[Edge, ...]
Profile = tuple[int, int, int, int]


class GateError(RuntimeError):
    """A frozen subject, exact control, or registered decision drifted."""


@dataclass(frozen=True)
class Base:
    position: int
    term_index: int
    left: Side
    right: Side
    components: tuple[tuple[int, ...], tuple[int, ...]]


@dataclass(frozen=True)
class Expression:
    left: Side
    right: Side
    anchor: int
    auxiliary: int
    new_label: int
    orientation: int


@dataclass(frozen=True)
class Seed:
    raw_index: int
    base_position: int
    base_term_index: int
    expression: Expression

    @property
    def key(self) -> tuple[int, int, int, int]:
        expression = self.expression
        return (
            self.base_term_index,
            expression.anchor,
            expression.auxiliary,
            expression.orientation,
        )


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def portable_path(path: Path) -> str:
    resolved = path.resolve()
    for label, root in (("$REPO", ROOT), ("$PYTHON_PREFIX", Path(sys.prefix).resolve())):
        try:
            return f"{label}/{resolved.relative_to(root).as_posix()}"
        except ValueError:
            pass
    return str(resolved)


def write_gzip(path: Path, document: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(document))


def canonical_side(edges: Iterable[Edge]) -> Side:
    return tuple(sorted((min(a, b), max(a, b)) for a, b in edges))


def serialize_side(side: Side) -> list[list[int]]:
    return [[int(a), int(b)] for a, b in side]


def serialize_expression(expression: Expression) -> dict[str, object]:
    return {
        "left": serialize_side(expression.left),
        "right": serialize_side(expression.right),
        "anchor": expression.anchor,
        "auxiliary": expression.auxiliary,
        "new_label": expression.new_label,
        "orientation": expression.orientation,
    }


def seed_record(seed: Seed) -> dict[str, object]:
    return {
        "raw_index": seed.raw_index,
        "base_position": seed.base_position,
        "base_term_index": seed.base_term_index,
        "expression": serialize_expression(seed.expression),
    }


def profile_column_descriptors(representatives: Sequence[Seed]) -> list[dict[str, object]]:
    descriptors: list[dict[str, object]] = [
        {
            "kind": "Y-spoke-orbit-representative",
            "representative": seed_record(seed),
        }
        for seed in representatives
    ]
    descriptors.extend(
        [
            {"kind": "carrier", "name": "C_L", "representative": "x_1"},
            {
                "kind": "carrier",
                "name": "C_E",
                "representative": "max(x_1,x_2)",
            },
            {
                "kind": "carrier",
                "name": "C_Y",
                "representative": "max(2*x_1,x_2+x_3)",
            },
        ]
    )
    return descriptors


def connected_components(left: Side, right: Side) -> tuple[tuple[int, ...], tuple[int, ...]]:
    edges = left + right
    if any(a == b for a, b in edges) or len(set(edges)) != 8:
        raise GateError("base union must contain eight distinct nonloops")
    parent = list(range(OLD_N + 1))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for a, b in edges:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a
    groups: dict[int, list[int]] = defaultdict(list)
    for vertex in range(1, OLD_N + 1):
        groups[find(vertex)].append(vertex)
    components = tuple(sorted((tuple(values) for values in groups.values())))
    if len(components) != 2 or set().union(*map(set, components)) != set(range(1, 11)):
        raise GateError("base union is not a two-component full-support forest")
    return components  # type: ignore[return-value]


def load_bases() -> list[Base]:
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    terms = document.get("terms")
    if document.get("n") != OLD_N or not isinstance(terms, list):
        raise GateError("malformed MAX10 certificate")
    bases: list[Base] = []
    for term_index, term in enumerate(terms):
        pair = term.get("pair")
        if not isinstance(pair, list) or len(pair) != 2:
            raise GateError(f"malformed pair at term {term_index}")
        sides: list[Side] = []
        for raw_side in pair:
            if not isinstance(raw_side, list):
                raise GateError(f"malformed side at term {term_index}")
            parsed: list[Edge] = []
            for item in raw_side:
                if (
                    not isinstance(item, list)
                    or len(item) != 2
                    or any(type(value) is not int for value in item)
                ):
                    raise GateError(f"malformed edge at term {term_index}")
                a, b = sorted(map(int, item))
                if not (1 <= a <= b <= OLD_N):
                    raise GateError(f"edge outside 1..10 at term {term_index}")
                parsed.append((a, b))
            sides.append(canonical_side(parsed))
        left, right = sides
        if len(left) != 4 or len(right) != 4:
            continue
        try:
            components = connected_components(left, right)
        except GateError:
            continue
        bases.append(Base(len(bases), term_index, left, right, components))
    if len(bases) != EXPECTED_BASES:
        raise GateError(f"base census drift: {len(bases)} != {EXPECTED_BASES}")
    return bases


def enumerate_seeds(bases: Sequence[Base]) -> list[Seed]:
    seeds: list[Seed] = []
    for base in bases:
        component_of = {
            vertex: component_index
            for component_index, component in enumerate(base.components)
            for vertex in component
        }
        for anchor in range(1, OLD_N + 1):
            opposite = base.components[1 - component_of[anchor]]
            for auxiliary in opposite:
                for orientation in (0, 1):
                    seeds.append(
                        Seed(
                            len(seeds),
                            base.position,
                            base.term_index,
                            Expression(
                                base.left,
                                base.right,
                                anchor,
                                auxiliary,
                                N,
                                orientation,
                            ),
                        )
                    )
    if len(seeds) != EXPECTED_RAW_SEEDS or len({seed.key for seed in seeds}) != len(seeds):
        raise GateError(f"Y-spoke seed census drift: {len(seeds)}")
    return seeds


def expression_graph_data(
    expression: Expression,
    *,
    double_coefficient_occurrences: int = 2,
    drop_last_base_edge: bool = False,
) -> tuple[dict[int, set[int]], list[set[int]], dict[int, str]]:
    """Typed occurrence graph for exact coordinate/branch orbit equivalence."""

    if expression.orientation not in (0, 1):
        raise GateError("orientation must be zero or one")
    labels = {
        *[vertex for edge in expression.left + expression.right for vertex in edge],
        expression.anchor,
        expression.auxiliary,
        expression.new_label,
    }
    if labels != set(range(1, N + 1)):
        raise GateError("expression does not have exact full support 1..11")
    if expression.anchor in (expression.auxiliary, expression.new_label):
        raise GateError("Y-spoke labels must be distinct")
    if expression.auxiliary == expression.new_label:
        raise GateError("Y-spoke leaves must be distinct")
    if double_coefficient_occurrences < 1:
        raise GateError("coefficient occurrence count must be positive")

    adjacency: dict[int, set[int]] = {}
    kinds: dict[int, str] = {}

    def node(kind: str) -> int:
        index = len(adjacency)
        adjacency[index] = set()
        kinds[index] = kind
        return index

    def connect(first: int, second: int) -> None:
        adjacency[first].add(second)
        adjacency[second].add(first)

    coordinates = [node("coordinate") for _ in range(N)]
    outer = node("outer-max")
    branches = [node("branch-sum"), node("branch-sum")]
    connect(outer, branches[0])
    connect(outer, branches[1])

    occurrences: list[tuple[int, Edge]] = []
    for branch, side in enumerate((expression.left, expression.right)):
        for edge in side:
            occurrences.append((branch, edge))
    if drop_last_base_edge:
        occurrences.pop()
    for branch, (a, b) in occurrences:
        edge_node = node("graphical-max")
        connect(edge_node, branches[branch])
        connect(edge_node, coordinates[a - 1])
        connect(edge_node, coordinates[b - 1])

    simple_branch = expression.orientation
    y_branch = 1 - expression.orientation
    simple_form = node("linear-form")
    connect(simple_form, branches[simple_branch])
    for _ in range(double_coefficient_occurrences):
        incidence = node("unit-incidence")
        connect(simple_form, incidence)
        connect(incidence, coordinates[expression.anchor - 1])

    y_node = node("y-max")
    connect(y_node, branches[y_branch])
    doubled_arm = node("linear-form")
    leaf_arm = node("linear-form")
    connect(y_node, doubled_arm)
    connect(y_node, leaf_arm)
    for _ in range(double_coefficient_occurrences):
        incidence = node("unit-incidence")
        connect(doubled_arm, incidence)
        connect(incidence, coordinates[expression.anchor - 1])
    for label in (expression.auxiliary, expression.new_label):
        incidence = node("unit-incidence")
        connect(leaf_arm, incidence)
        connect(incidence, coordinates[label - 1])

    color_order = [
        "coordinate",
        "outer-max",
        "branch-sum",
        "graphical-max",
        "linear-form",
        "y-max",
        "unit-incidence",
    ]
    coloring = [{index for index, kind in kinds.items() if kind == name} for name in color_order]
    if any(not block for block in coloring):
        raise GateError("typed expression graph lost a required color class")
    return adjacency, coloring, kinds


def orbit_certificate(expression: Expression, **mutants: object) -> bytes:
    adjacency, coloring, _kinds = expression_graph_data(expression, **mutants)
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={index: sorted(neighbours) for index, neighbours in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph)


def networkx_graph(expression: Expression) -> nx.Graph:
    adjacency, _coloring, kinds = expression_graph_data(expression)
    graph = nx.Graph()
    for index, kind in kinds.items():
        graph.add_node(index, kind=kind)
    for first, neighbours in adjacency.items():
        for second in neighbours:
            if first < second:
                graph.add_edge(first, second)
    return graph


def relabel_expression(expression: Expression, permutation: dict[int, int]) -> Expression:
    def side(raw: Side) -> Side:
        return canonical_side((permutation[a], permutation[b]) for a, b in raw)

    return Expression(
        side(expression.left),
        side(expression.right),
        permutation[expression.anchor],
        permutation[expression.auxiliary],
        permutation[expression.new_label],
        expression.orientation,
    )


def swap_expression_branches(expression: Expression) -> Expression:
    return Expression(
        expression.right,
        expression.left,
        expression.anchor,
        expression.auxiliary,
        expression.new_label,
        1 - expression.orientation,
    )


def build_orbits(seeds: Sequence[Seed], *, verify_vf2: bool) -> tuple[list[Seed], dict[str, object]]:
    groups: dict[bytes, list[Seed]] = defaultdict(list)
    sequence: list[str] = []
    for seed in seeds:
        certificate = orbit_certificate(seed.expression)
        groups[certificate].append(seed)
        sequence.append(hashlib.sha256(certificate).hexdigest())
    ordered_certificates = sorted(groups, key=lambda item: hashlib.sha256(item).hexdigest())
    representatives = [min(groups[item], key=lambda seed: canonical_bytes(seed_record(seed))) for item in ordered_certificates]

    vf2_checks = 0
    if verify_vf2:
        node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
        for certificate in ordered_certificates:
            representative_graph = networkx_graph(groups[certificate][0].expression)
            for seed in groups[certificate][1:]:
                if not nx.is_isomorphic(
                    representative_graph,
                    networkx_graph(seed.expression),
                    node_match=node_match,
                ):
                    raise GateError("pynauty orbit class failed independent typed-DAG VF2")
                vf2_checks += 1

    manifest = [
        {
            "certificate_sha256": hashlib.sha256(certificate).hexdigest(),
            "raw_seed_count": len(groups[certificate]),
            "representative": seed_record(representatives[position]),
        }
        for position, certificate in enumerate(ordered_certificates)
    ]
    report = {
        "raw_seed_count": len(seeds),
        "orbit_count": len(representatives),
        "class_size_histogram": {
            str(size): count for size, count in sorted(Counter(map(len, groups.values())).items())
        },
        "orbit_sequence_sha256": canonical_sha256(sequence),
        "orbit_manifest_sha256": canonical_sha256(manifest),
        "representative_manifest_sha256": canonical_sha256(
            [seed_record(seed) for seed in representatives]
        ),
        "vf2_nonrepresentative_checks": vf2_checks,
    }
    return representatives, report


def all_profiles(n: int = N) -> list[Profile]:
    return [
        (zero, one, two, n - zero - one - two)
        for zero in range(n + 1)
        for one in range(n + 1 - zero)
        for two in range(n + 1 - zero - one)
    ]


def assignment_count(profile: Profile) -> int:
    result = factorial(sum(profile))
    for count in profile:
        result //= factorial(count)
    return result


def assignments(profile: Profile) -> np.ndarray:
    n = sum(profile)
    _, count_one, count_two, count_three = profile
    vertices = tuple(range(n))
    output: list[list[int]] = []
    for threes in combinations(vertices, count_three):
        three_set = set(threes)
        without_three = tuple(vertex for vertex in vertices if vertex not in three_set)
        for twos in combinations(without_three, count_two):
            two_set = set(twos)
            without_two = tuple(vertex for vertex in without_three if vertex not in two_set)
            for ones in combinations(without_two, count_one):
                row = [0] * n
                for vertex in ones:
                    row[vertex] = 1
                for vertex in twos:
                    row[vertex] = 2
                for vertex in threes:
                    row[vertex] = 3
                output.append(row)
    result = np.asarray(output, dtype=np.int16).T
    if result.shape != (n, assignment_count(profile)):
        raise GateError(f"assignment census drift at {profile}: {result.shape}")
    return result


def evaluate_expression(expression: Expression, point: Sequence[int]) -> int:
    left = sum(max(point[a - 1], point[b - 1]) for a, b in expression.left)
    right = sum(max(point[a - 1], point[b - 1]) for a, b in expression.right)
    simple = 2 * point[expression.anchor - 1]
    y_value = max(simple, point[expression.auxiliary - 1] + point[expression.new_label - 1])
    if expression.orientation == 0:
        return max(left + simple, right + y_value)
    return max(left + y_value, right + simple)


def evaluate_seed_block(base: Base, seeds: Sequence[Seed], levels: np.ndarray) -> np.ndarray:
    if not seeds:
        return np.empty((0, levels.shape[1]), dtype=np.int16)
    left = np.zeros(levels.shape[1], dtype=np.int16)
    right = np.zeros(levels.shape[1], dtype=np.int16)
    for a, b in base.left:
        left += np.maximum(levels[a - 1], levels[b - 1])
    for a, b in base.right:
        right += np.maximum(levels[a - 1], levels[b - 1])
    anchors = np.asarray([seed.expression.anchor - 1 for seed in seeds], dtype=np.intp)
    auxiliaries = np.asarray([seed.expression.auxiliary - 1 for seed in seeds], dtype=np.intp)
    orientations = np.asarray([seed.expression.orientation for seed in seeds], dtype=np.int8)
    simple = 2 * levels[anchors]
    leaf_sum = levels[auxiliaries] + levels[N - 1]
    common = np.maximum(left, right)[None, :] + simple
    branch_tail = np.where(
        orientations[:, None] == 0,
        right[None, :] + leaf_sum,
        left[None, :] + leaf_sum,
    )
    # Exact flattening of the two nested maxes:
    # max(A+2k, B+max(2k,l+n)) = max(max(A,B)+2k, B+l+n),
    # with A replacing B in the second orientation.
    return np.maximum(common, branch_tail).astype(np.int16, copy=False)


def group_by_base(seeds: Sequence[Seed], base_count: int) -> list[list[tuple[int, Seed]]]:
    grouped: list[list[tuple[int, Seed]]] = [[] for _ in range(base_count)]
    for column, seed in enumerate(seeds):
        grouped[seed.base_position].append((column, seed))
    return grouped


def boolean_charge_census(bases: Sequence[Base], seeds: Sequence[Seed]) -> dict[str, object]:
    masks = np.arange(1 << N, dtype=np.uint16)
    levels = np.asarray(
        [[(int(mask) >> vertex) & 1 for mask in masks] for vertex in range(N)],
        dtype=np.int16,
    )
    signs = np.asarray(
        [(-1) ** (N - int(mask).bit_count()) for mask in masks], dtype=np.int64
    )
    charges = np.zeros(len(seeds), dtype=np.int64)
    grouped = group_by_base(seeds, len(bases))
    for base in bases:
        entries = grouped[base.position]
        indices = [index for index, _seed in entries]
        values = evaluate_seed_block(base, [seed for _index, seed in entries], levels)
        charges[np.asarray(indices, dtype=np.intp)] = values.astype(np.int64) @ signs
    rows = [[seed.raw_index, int(charges[seed.raw_index])] for seed in seeds]
    histogram = Counter(map(int, charges.tolist()))
    return {
        "zero_count": int(np.count_nonzero(charges == 0)),
        "nonzero_count": int(np.count_nonzero(charges != 0)),
        "minimum": int(charges.min()),
        "maximum": int(charges.max()),
        "histogram": {str(key): count for key, count in sorted(histogram.items())},
        "charge_rows_sha256": canonical_sha256(rows),
    }


def profile_groups(budget: int) -> list[list[Profile]]:
    if budget < max(assignment_count(profile) for profile in all_profiles()):
        raise GateError("profile budget is below the largest single profile")
    groups: list[list[Profile]] = []
    group: list[Profile] = []
    weight = 0
    for profile in all_profiles():
        count = assignment_count(profile)
        if group and weight + count > budget:
            groups.append(group)
            group = []
            weight = 0
        group.append(profile)
        weight += count
    if group:
        groups.append(group)
    if sum(map(len, groups)) != 364:
        raise GateError("profile grouping lost rows")
    if sum(assignment_count(profile) for profile in all_profiles()) != 4**N:
        raise GateError("profile assignment partition does not cover the full 4-ary cube")
    return groups


def evaluate_profile_group(
    group_index: int,
    profiles: Sequence[Profile],
    bases: Sequence[Base],
    representatives: Sequence[Seed],
) -> tuple[int, np.ndarray, np.ndarray, np.ndarray]:
    grouped = group_by_base(representatives, len(bases))
    matrix = np.zeros((len(profiles), len(representatives) + 3), dtype=np.int64)
    target = np.zeros(len(profiles), dtype=np.int64)
    profile_array = np.asarray(profiles, dtype=np.int16)
    for row, profile in enumerate(profiles):
        levels = assignments(profile)
        for base in bases:
            entries = grouped[base.position]
            if not entries:
                continue
            columns = np.asarray([column for column, _seed in entries], dtype=np.intp)
            values = evaluate_seed_block(base, [seed for _column, seed in entries], levels)
            matrix[row, columns] = values.sum(axis=1, dtype=np.int64)
        offset = len(representatives)
        matrix[row, offset] = levels[0].sum(dtype=np.int64)
        matrix[row, offset + 1] = np.maximum(levels[0], levels[1]).sum(dtype=np.int64)
        matrix[row, offset + 2] = np.maximum(
            2 * levels[0], levels[1] + levels[2]
        ).sum(dtype=np.int64)
        highest = max((level for level, count in enumerate(profile) if count), default=0)
        target[row] = levels.shape[1] * highest
    return group_index, profile_array, matrix, target


def build_profile_matrix(
    bases: Sequence[Base],
    representatives: Sequence[Seed],
    workers: int,
    budget: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    begun = time.perf_counter()
    groups = profile_groups(budget)
    results: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray]] = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {
            pool.submit(evaluate_profile_group, index, group, bases, representatives): index
            for index, group in enumerate(groups)
        }
        for future in as_completed(futures):
            index, profiles, matrix, target = future.result()
            results[index] = profiles, matrix, target
            print(
                f"G0073_PROFILE_GROUP completed={len(results)}/{len(groups)} index={index}",
                file=sys.stderr,
                flush=True,
            )
    profile_array = np.concatenate([results[index][0] for index in range(len(groups))])
    matrix = np.concatenate([results[index][1] for index in range(len(groups))])
    target = np.concatenate([results[index][2] for index in range(len(groups))])
    if [tuple(map(int, row)) for row in profile_array.tolist()] != all_profiles():
        raise GateError("profile output order drift")
    expected_shape = (364, len(representatives) + 3)
    if matrix.shape != expected_shape or target.shape != (364,):
        raise GateError(f"profile matrix shape drift: {matrix.shape}")
    # Constant inputs are exact closed-form sentinels for every orbit column,
    # each carrier, and the target.  They catch row-order, carrier scaling, and
    # expression-degree errors after multiprocessing assembly.
    row_by_profile = {
        tuple(map(int, profile)): row for row, profile in enumerate(profile_array.tolist())
    }
    constant_rows: dict[str, dict[str, int]] = {}
    for level in range(4):
        profile = tuple(N if value == level else 0 for value in range(4))
        row = row_by_profile[profile]
        expected = np.asarray(
            [6 * level] * len(representatives) + [level, level, 2 * level],
            dtype=np.int64,
        )
        if not np.array_equal(matrix[row], expected) or int(target[row]) != level:
            raise GateError(f"constant-profile closed form failed at level {level}")
        constant_rows[str(level)] = {
            "orbit_value": 6 * level,
            "C_L": level,
            "C_E": level,
            "C_Y": 2 * level,
            "target": level,
        }
    report = {
        "rows": 364,
        "orbit_columns": len(representatives),
        "carrier_columns": ["C_L", "C_E", "C_Y"],
        "columns": matrix.shape[1],
        "profile_groups": len(groups),
        "profile_assignment_budget": budget,
        "total_distinct_assignments": 4**N,
        "constant_profile_controls": constant_rows,
        "column_manifest_sha256": canonical_sha256(
            profile_column_descriptors(representatives)
        ),
        "profile_manifest_sha256": canonical_sha256(
            [list(map(int, profile)) for profile in all_profiles()]
        ),
        "matrix_int64_c_sha256": hashlib.sha256(matrix.tobytes(order="C")).hexdigest(),
        "target_int64_c_sha256": hashlib.sha256(target.tobytes(order="C")).hexdigest(),
        "seconds": time.perf_counter() - begun,
    }
    return profile_array, matrix, target, report


def pivot_columns_from_rref(rref: object, rank: int, columns: int) -> list[int]:
    pivots: list[int] = []
    for row in range(rank):
        pivot = next((column for column in range(columns) if rref[row, column] != 0), None)  # type: ignore[index]
        if pivot is None:
            raise GateError("RREF row lacks a pivot")
        pivots.append(pivot)
    if pivots != sorted(set(pivots)):
        raise GateError("invalid RREF pivot sequence")
    return pivots


def exact_sparse_profile_solution(
    matrix: np.ndarray,
    target: np.ndarray,
    pivot_rows: Sequence[int],
    pivot_columns: Sequence[int],
    column_descriptors: Sequence[dict[str, object]],
) -> dict[str, object]:
    rank = len(pivot_rows)
    if rank == 0 or len(pivot_columns) != rank:
        raise GateError("exact sparse solve requires equally many nonempty pivot rows and columns")
    square_array = matrix[np.ix_(list(pivot_rows), list(pivot_columns))]
    square = fmpq_mat(fmpz_mat(square_array.tolist()))
    if int(square.rank()) != rank:
        raise GateError("exact sparse solve received a singular pivot minor")
    rhs = fmpq_mat(fmpz_mat([[int(target[row])] for row in pivot_rows]))
    solution = square.solve(rhs)
    residual = square * solution - rhs
    zero = fmpq_mat(residual.nrows(), residual.ncols())
    if residual != zero:
        raise GateError("exact pivot solution failed replay")

    # Method-disjoint exact replay: parse the FLINT solution into stdlib
    # Fractions and evaluate every original row through the original wide
    # column indices.  This checks both the backend result and index mapping.
    coefficients = [Fraction(str(solution[position, 0])) for position in range(rank)]
    for row in range(matrix.shape[0]):
        observed = sum(
            int(matrix[row, column]) * coefficients[position]
            for position, column in enumerate(pivot_columns)
        )
        if observed != Fraction(int(target[row])):
            raise GateError(f"exact sparse full-matrix replay failed at row {row}")
    sparse: list[dict[str, object]] = [
        {
            "column_index": int(column),
            "coefficient": str(coefficients[position]),
            "descriptor": column_descriptors[column],
        }
        for position, column in enumerate(pivot_columns)
        if coefficients[position]
    ]
    return {
        "support_size": len(sparse),
        "sparse_coefficients": sparse,
        "sparse_coefficients_sha256": canonical_sha256(sparse),
        "pivot_rows_sha256": canonical_sha256(list(map(int, pivot_rows))),
        "pivot_columns_sha256": canonical_sha256(list(map(int, pivot_columns))),
        "coefficient_convention": (
            "coefficients multiply Sym_avg(Phi)=1/11!*sum_{sigma in S_11} Phi(sigma*x); "
            "a compiler using the unnormalized permutation sum must divide each coefficient by 11!"
        ),
        "exact_replay": {
            "rows_checked": matrix.shape[0],
            "original_columns": matrix.shape[1],
            "selected_original_columns": len(pivot_columns),
            "flint_pivot_residual_zero": True,
            "stdlib_fraction_full_residual_zero": True,
        },
    }


def exact_profile_dual(
    matrix: np.ndarray,
    target: np.ndarray,
    gram: fmpz_mat,
    exact_rank: int,
) -> dict[str, object] | None:
    nullspace, nullity_object = gram.nullspace()
    nullity = int(nullity_object)
    if nullity != matrix.shape[0] - exact_rank:
        raise GateError("exact Gram nullity disagrees with exact rank")
    for basis_column in range(nullity):
        integer_dual = [int(nullspace[row, basis_column]) for row in range(matrix.shape[0])]
        target_inner = sum(
            integer_dual[row] * int(target[row]) for row in range(matrix.shape[0])
        )
        if target_inner == 0:
            continue
        candidate = fmpz_mat([[value] for value in integer_dual])
        if gram * candidate != fmpz_mat(matrix.shape[0], 1):
            raise GateError("FLINT nullspace vector failed exact Gram replay")
        for column in range(matrix.shape[1]):
            observed = sum(
                integer_dual[row] * int(matrix[row, column])
                for row in range(matrix.shape[0])
            )
            if observed != 0:
                raise GateError(f"exact profile dual failed wide replay at column {column}")
        normalized = [
            [row, str(Fraction(value, target_inner))]
            for row, value in enumerate(integer_dual)
            if value
        ]
        if sum(
            Fraction(value, target_inner) * int(target[row])
            for row, value in enumerate(integer_dual)
        ) != 1:
            raise GateError("normalized exact profile dual does not send target to one")
        integer_sparse = [[row, value] for row, value in enumerate(integer_dual) if value]
        return {
            "support_size": len(integer_sparse),
            "integer_sparse_rows": integer_sparse,
            "integer_target_inner_product": target_inner,
            "normalized_sparse_rows": normalized,
            "normalized_sparse_rows_sha256": canonical_sha256(normalized),
            "exact_replay": {
                "gram_kernel": True,
                "all_original_columns_annihilated": matrix.shape[1],
                "normalized_target_inner_product": "1",
            },
        }
    return None


def rank_and_solve(
    matrix: np.ndarray,
    target: np.ndarray,
    column_descriptors: Sequence[dict[str, object]],
) -> dict[str, object]:
    if len(column_descriptors) != matrix.shape[1]:
        raise GateError("column descriptor count disagrees with profile matrix")
    reports: list[dict[str, object]] = []
    for prime in PRIMES:
        begun = time.perf_counter()
        field = nmod_mat(matrix.tolist(), prime)
        rref, rank_object = field.rref()
        rank = int(rank_object)
        augmented_rank = int(
            nmod_mat(np.column_stack((matrix, target)).tolist(), prime).rank()
        )
        pivots = pivot_columns_from_rref(rref, rank, matrix.shape[1])
        reports.append(
            {
                "prime": prime,
                "column_rank": rank,
                "augmented_rank": augmented_rank,
                "rank_gap": augmented_rank - rank,
                "pivot_columns_sha256": canonical_sha256(pivots),
                "seconds": time.perf_counter() - begun,
            }
        )

    # Resolve the necessarily rank-deficient 364-profile system exactly over
    # Q.  Positive homogeneity creates predetermined proportional rows, so a
    # full-row-rank acceptance condition would be unreachable.  Over Q/R,
    # G=M*M^T has col(G)=col(M) and ker(G)=ker(M^T) by the sum-of-squares
    # identity y^T G y=||M^T y||^2.  This is not a modular-field argument.
    max_abs = max(abs(int(matrix.min())), abs(int(matrix.max())))
    gram_entry_bound = matrix.shape[1] * max_abs * max_abs
    if gram_entry_bound >= 2**63:
        raise GateError(f"int64 Gram bound is unsafe: {gram_entry_bound}")
    gram_array = matrix @ matrix.T
    if gram_array.dtype != np.int64 or not np.array_equal(gram_array, gram_array.T):
        raise GateError("integer Gram construction drift")
    gram_sentinel_checks = 0
    sentinel_rows = sorted({0, matrix.shape[0] // 2, matrix.shape[0] - 1})
    for first in sentinel_rows:
        for second in sentinel_rows:
            expected = sum(
                int(matrix[first, column]) * int(matrix[second, column])
                for column in range(matrix.shape[1])
            )
            if int(gram_array[first, second]) != expected:
                raise GateError("int64 Gram disagrees with Python-integer sentinel")
            gram_sentinel_checks += 1
    gram = fmpz_mat(gram_array.tolist())
    gram_rref, gram_denominator, exact_rank_object = gram.rref()
    exact_rank = int(exact_rank_object)
    pivot_rows = pivot_columns_from_rref(gram_rref, exact_rank, matrix.shape[0])
    exact_common = {
        "exact_rank": exact_rank,
        "row_nullity": matrix.shape[0] - exact_rank,
        "gram_int64_c_sha256": hashlib.sha256(gram_array.tobytes(order="C")).hexdigest(),
        "gram_entry_absolute_bound": gram_entry_bound,
        "gram_python_integer_sentinel_checks": gram_sentinel_checks,
        "gram_rref_common_denominator": str(gram_denominator),
        "exact_pivot_rows_sha256": canonical_sha256(pivot_rows),
    }

    dual = exact_profile_dual(matrix, target, gram, exact_rank)
    if dual is not None:
        return {
            "result": "PROFILE_GATE_EXACT_Q_NONMEMBERSHIP",
            "prime_results": reports,
            "exact_resolution": exact_common,
            "exact_profile_solution": None,
            "exact_profile_dual": dual,
            "interpretation": (
                "The normalized exact dual annihilates every frozen family/carrier profile column "
                "but sends the target to one.  This excludes a global identity inside only this "
                "frozen Y-spoke orbit family even with real output coefficients; it is not an "
                "unrestricted network lower bound."
            ),
        }

    # Target is in col(M).  Select an exact sparse original-column basis from
    # the independent rows and replay its solution on all 364 rows.
    restricted_array = matrix[np.asarray(pivot_rows, dtype=np.intp), :]
    pivot_columns: list[int] | None = None
    column_basis_selection: dict[str, object] | None = None
    for prime in PRIMES:
        restricted_field = nmod_mat(restricted_array.tolist(), prime)
        restricted_rref, restricted_rank_object = restricted_field.rref()
        restricted_rank = int(restricted_rank_object)
        if restricted_rank != exact_rank:
            continue
        pivot_columns = pivot_columns_from_rref(
            restricted_rref, exact_rank, matrix.shape[1]
        )
        column_basis_selection = {
            "method": "modular nonzero-minor selection followed by exact-Q solve",
            "prime": prime,
            "rank": restricted_rank,
        }
        break
    if pivot_columns is None:
        restricted = fmpz_mat(restricted_array.tolist())
        restricted_rref, restricted_denominator, restricted_rank_object = restricted.rref()
        restricted_rank = int(restricted_rank_object)
        if restricted_rank != exact_rank:
            raise GateError("exact restricted row matrix rank disagrees with Gram rank")
        pivot_columns = pivot_columns_from_rref(
            restricted_rref, exact_rank, matrix.shape[1]
        )
        column_basis_selection = {
            "method": "exact fmpz fraction-free RREF",
            "rank": restricted_rank,
            "common_denominator": str(restricted_denominator),
        }
    exact = exact_sparse_profile_solution(
        matrix,
        target,
        pivot_rows,
        pivot_columns,
        column_descriptors,
    )
    exact["column_basis_selection"] = column_basis_selection
    return {
        "result": "PROFILE_GATE_EXACT_Q_MEMBERSHIP",
        "prime_results": reports,
        "exact_resolution": exact_common,
        "exact_profile_solution": exact,
        "exact_profile_dual": None,
        "interpretation": (
            "The emitted sparse exact-Q coefficients replay on every frozen profile row.  This is "
            "a necessary finite-profile survivor only, not a global CPWL identity; failure of this "
            "particular basic interpolant on later generic rows would not reject the full family."
        ),
    }


def verify_bindings() -> dict[str, dict[str, object]]:
    report: dict[str, dict[str, object]] = {}
    for name, (path, expected) in EXPECTED_BINDINGS.items():
        observed = sha256_path(path)
        if observed != expected:
            raise GateError(f"binding drift for {name}: {observed} != {expected}")
        report[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    for name, module in (
        ("pynauty", pynauty),
        ("networkx", nx),
        ("python_flint", flint),
        ("numpy", np),
    ):
        path = Path(module.__file__).resolve()
        report[name] = {
            "path": portable_path(path),
            "sha256": sha256_path(path),
            "version": getattr(module, "__version__", "unknown"),
        }
    # Bind the principal implementation files actually exercised below, not
    # merely each package's lightweight __init__.py entrypoint.  The frozen
    # preflight scientific hash turns these observed hashes into run-time pins.
    backend_modules = {
        "pynauty_graph": "pynauty.graph",
        "pynauty_nautywrap": "pynauty.nautywrap",
        "networkx_graph": "networkx.classes.graph",
        "networkx_isomorph": "networkx.algorithms.isomorphism.isomorph",
        "networkx_matchhelpers": "networkx.algorithms.isomorphism.matchhelpers",
        "networkx_vf2userfunc": "networkx.algorithms.isomorphism.vf2userfunc",
        "networkx_isomorphvf2": "networkx.algorithms.isomorphism.isomorphvf2",
        "python_flint_fmpq_mat": "flint.types.fmpq_mat",
        "python_flint_fmpz_mat": "flint.types.fmpz_mat",
        "python_flint_nmod_mat": "flint.types.nmod_mat",
        "numpy_multiarray_umath": "numpy._core._multiarray_umath",
    }
    for name, module_name in backend_modules.items():
        module = importlib.import_module(module_name)
        path = Path(module.__file__).resolve()
        report[name] = {
            "path": portable_path(path),
            "sha256": sha256_path(path),
            "bytes": path.stat().st_size,
        }
    return report


def run_controls(bases: Sequence[Base], seeds: Sequence[Seed]) -> dict[str, object]:
    topology = Counter(tuple(sorted(map(len, base.components))) for base in bases)
    expected_topology = {(2, 8): 168, (3, 7): 39, (4, 6): 32, (5, 5): 13}
    if dict(topology) != expected_topology:
        raise GateError(f"component topology drift: {topology}")
    if len(seeds[::2]) != 9_200:
        raise GateError("orientation-deletion mutant did not halve the census")

    sample = seeds[len(seeds) // 3].expression
    direct_checks = 0
    coefficient_mutant_differences = 0
    for left_value in range(13):
        for right_value in range(13):
            for anchor_value in range(4):
                for auxiliary_value in range(4):
                    for new_value in range(4):
                        simple = 2 * anchor_value
                        leaf_sum = auxiliary_value + new_value
                        y_direct = max(simple, leaf_sum)
                        y_relu = simple + max(0, leaf_sum - simple)
                        if y_direct != y_relu:
                            raise GateError("Y compiler identity failed")
                        nested_zero = max(left_value + simple, right_value + y_direct)
                        flat_zero = max(
                            max(left_value, right_value) + simple,
                            right_value + leaf_sum,
                        )
                        nested_one = max(left_value + y_direct, right_value + simple)
                        flat_one = max(
                            max(left_value, right_value) + simple,
                            left_value + leaf_sum,
                        )
                        if nested_zero != flat_zero or nested_one != flat_one:
                            raise GateError("nested-to-flat Y identity failed")
                        mutant_simple = anchor_value
                        mutant_zero = max(
                            left_value + mutant_simple,
                            right_value + max(mutant_simple, leaf_sum),
                        )
                        if mutant_zero != nested_zero:
                            coefficient_mutant_differences += 1
                        direct_checks += 1
    if direct_checks != 10_816 or coefficient_mutant_differences == 0:
        raise GateError("exhaustive scalar identity/mutant control drift")
    for point in (
        tuple(range(N)),
        tuple(reversed(range(N))),
        tuple((3 * index + 1) % 7 for index in range(N)),
    ):
        left = sum(max(point[a - 1], point[b - 1]) for a, b in sample.left)
        right = sum(max(point[a - 1], point[b - 1]) for a, b in sample.right)
        simple = 2 * point[sample.anchor - 1]
        g = point[sample.auxiliary - 1] + point[sample.new_label - 1] - simple
        if sample.orientation == 0:
            compiled = right + simple + max(0, g) + max(
                0, left - right - max(0, g)
            )
        else:
            compiled = right + simple + max(
                0, left - right + max(0, g)
            )
        if compiled != evaluate_expression(sample, point):
            raise GateError("outer ReLU compiler identity failed")

    # Cross the optimized block evaluator against the literal expression on
    # all Boolean inputs for seeds spanning the ordered subject.
    masks = np.arange(1 << N, dtype=np.uint16)
    boolean_levels = np.asarray(
        [[(int(mask) >> vertex) & 1 for mask in masks] for vertex in range(N)],
        dtype=np.int16,
    )
    block_literal_checks = 0
    for seed in (seeds[0], seeds[len(seeds) // 2], seeds[-1]):
        base = bases[seed.base_position]
        observed = evaluate_seed_block(base, [seed], boolean_levels)[0]
        expected = np.asarray(
            [
                evaluate_expression(seed.expression, boolean_levels[:, column])
                for column in range(boolean_levels.shape[1])
            ],
            dtype=np.int16,
        )
        if not np.array_equal(observed, expected):
            raise GateError("optimized seed block disagrees with literal evaluator")
        block_literal_checks += len(expected)

    permutation = {label: ((3 * (label - 1) + 4) % N) + 1 for label in range(1, N + 1)}
    if len(set(permutation.values())) != N:
        raise GateError("control relabeling is not a permutation")
    certificate = orbit_certificate(sample)
    if orbit_certificate(relabel_expression(sample, permutation)) != certificate:
        raise GateError("coordinate relabeling changed the orbit certificate")
    if orbit_certificate(swap_expression_branches(sample)) != certificate:
        raise GateError("branch swap changed the orbit certificate")
    if orbit_certificate(sample, double_coefficient_occurrences=1) == certificate:
        raise GateError("coefficient mutation escaped orbit certificate")
    if orbit_certificate(sample, drop_last_base_edge=True) == certificate:
        raise GateError("edge-deletion mutation escaped orbit certificate")

    # Exact facet exposure: the coefficient of x_11 distinguishes the two
    # endpoints 2e_k and e_l+e_11, exposing 2e_k on F_11.
    doubled = [0] * N
    doubled[sample.anchor - 1] = 2
    leaves = [0] * N
    leaves[sample.auxiliary - 1] = 1
    leaves[sample.new_label - 1] = 1
    if not (doubled[N - 1] < leaves[N - 1] and sum(doubled) == sum(leaves) == 2):
        raise GateError("Y-spoke facet exposure failed")
    mutant = [0] * N
    mutant[sample.anchor - 1] = 1
    if sum(mutant) == sum(leaves):
        raise GateError("facet coefficient mutant was not detected")

    # Small-n normalization oracle: distinct assignments times the profile
    # stabilizer must equal a literal permutation sum.
    normalization_checks = 0
    for profile in all_profiles(4):
        levels = assignments(profile)
        distinct_sum = int(np.maximum(2 * levels[0], levels[1] + levels[2]).sum())
        canonical_point = tuple(
            level for level, count in enumerate(profile) for _ in range(count)
        )
        literal = sum(
            max(2 * point[0], point[1] + point[2])
            for point in permutations(canonical_point)
        )
        stabilizer = 1
        for count in profile:
            stabilizer *= factorial(count)
        if literal != stabilizer * distinct_sum:
            raise GateError(f"profile normalization failed at {profile}")
        normalization_checks += 1

    # Exercise the installed exact backend through the same full-row-rank
    # path used by a positive registered outcome.  This catches API drift and
    # verifies that sparse indices refer to original matrix columns.
    toy_matrix = np.asarray(
        [[1, 0, 1], [0, 1, 1], [1, 1, 2]], dtype=np.int64
    )
    toy_target = np.asarray([2, 3, 5], dtype=np.int64)
    toy_descriptors = [{"kind": "toy", "column": column} for column in range(3)]
    toy_decision = rank_and_solve(toy_matrix, toy_target, toy_descriptors)
    if toy_decision["result"] != "PROFILE_GATE_EXACT_Q_MEMBERSHIP":
        raise GateError("exact solver injection control failed")
    toy_solution = toy_decision["exact_profile_solution"]
    if not isinstance(toy_solution, dict) or not toy_solution.get("exact_replay"):
        raise GateError("exact solver injection did not replay")
    toy_mutant = rank_and_solve(
        toy_matrix,
        np.asarray([2, 3, 6], dtype=np.int64),
        toy_descriptors,
    )
    if toy_mutant["result"] != "PROFILE_GATE_EXACT_Q_NONMEMBERSHIP":
        raise GateError("exact solver target-mutation control failed")

    return {
        "component_topology": {f"{a}+{b}": count for (a, b), count in sorted(topology.items())},
        "orientation_deletion_mutant_count": len(seeds[::2]),
        "nested_flat_scalar_identity_assignments": direct_checks,
        "unit_anchor_coefficient_mutant_differences": coefficient_mutant_differences,
        "outer_relu_compiler_points": 3,
        "optimized_literal_boolean_checks": block_literal_checks,
        "coordinate_relabel_invariance": True,
        "outer_branch_swap_invariance": True,
        "coefficient_mutant_rejected": True,
        "edge_deletion_mutant_rejected": True,
        "facet_11_exposes_2e_anchor": True,
        "facet_degree_mutant_rejected": True,
        "n4_profile_stabilizer_checks": normalization_checks,
        "exact_solver_target_injection": True,
        "exact_solver_target_mutation_rejected": True,
    }


def build_preflight(*, verify_vf2: bool) -> tuple[list[Base], list[Seed], list[Seed], dict[str, object]]:
    bindings = verify_bindings()
    bases = load_bases()
    seeds = enumerate_seeds(bases)
    controls = run_controls(bases, seeds)
    representatives, orbit_report = build_orbits(seeds, verify_vf2=verify_vf2)
    charge_report = boolean_charge_census(bases, seeds)
    subject = {
        "base_count": len(bases),
        "base_manifest_sha256": canonical_sha256(
            [
                {
                    "position": base.position,
                    "term_index": base.term_index,
                    "left": serialize_side(base.left),
                    "right": serialize_side(base.right),
                    "components": [list(component) for component in base.components],
                }
                for base in bases
            ]
        ),
        "raw_seed_manifest_sha256": canonical_sha256([seed_record(seed) for seed in seeds]),
        "orbits": orbit_report,
        "boolean_charge": charge_report,
        "carriers": ["C_L=Sym(x_1)", "C_E=Sym(max(x_1,x_2))", "C_Y=Sym(max(2x_1,x_2+x_3))"],
        "profile_normalization": (
            "Sym_avg(Phi)=1/11!*sum over S_11; M[p,j]=|X_p|*Sym_avg(Phi_j)(x_p) "
            "=sum over distinct assignments X_p of representative Phi_j; "
            "target[p]=|X_p|*max(profile level)"
        ),
        "coefficient_policy": "one free coefficient per full-S_11 orbit; no inherited MAX10 weights",
    }
    scientific = {
        "schema": PREFLIGHT_SCHEMA,
        "bindings": bindings,
        "controls": controls,
        "subject": subject,
    }
    report = {
        **scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "script_sha256": sha256_path(SCRIPT),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pynauty": getattr(pynauty, "__version__", "unknown"),
            "networkx": nx.__version__,
            "python_flint": getattr(flint, "__version__", "unknown"),
        },
        "claim_boundary": (
            "This freezes a free orbit family and necessary profile normalization only.  It is not "
            "a coefficient-preserving MAX10 lift, profile span result, or global MAX11 identity."
        ),
    }
    return bases, seeds, representatives, report


def enforce_frozen_preflight(report: dict[str, object]) -> None:
    expected_values = (
        EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256,
        EXPECTED_RAW_SEED_MANIFEST_SHA256,
        EXPECTED_ORBIT_MANIFEST_SHA256,
        EXPECTED_REPRESENTATIVE_MANIFEST_SHA256,
        EXPECTED_CHARGE_ROWS_SHA256,
        EXPECTED_ORBIT_COUNT,
    )
    if any(value is None for value in expected_values):
        raise GateError("registered execution is disabled until the preflight pins are frozen")
    subject = report["subject"]
    if not isinstance(subject, dict):
        raise GateError("malformed preflight subject")
    orbits = subject["orbits"]
    charge = subject["boolean_charge"]
    if not isinstance(orbits, dict) or not isinstance(charge, dict):
        raise GateError("malformed preflight orbit/charge report")
    observed = (
        report["scientific_payload_sha256"],
        subject["raw_seed_manifest_sha256"],
        orbits["orbit_manifest_sha256"],
        orbits["representative_manifest_sha256"],
        charge["charge_rows_sha256"],
        orbits["orbit_count"],
    )
    if observed != expected_values:
        raise GateError(f"frozen preflight drift: {observed} != {expected_values}")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--profile-budget", type=int, default=DEFAULT_PROFILE_BUDGET)
    parser.add_argument("--skip-full-vf2", action="store_true")
    parser.add_argument("--expected-script-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    begun = time.perf_counter()
    if arguments.workers < 1:
        raise GateError("workers must be positive")
    bases, seeds, representatives, preflight = build_preflight(
        verify_vf2=not arguments.skip_full_vf2
    )
    if arguments.self_test:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "mode": "self-test",
                    "controls": preflight["controls"],
                    "raw_seed_count": len(seeds),
                    "orbit_count": len(representatives),
                },
                sort_keys=True,
            )
        )
        return
    if arguments.preflight_only:
        if arguments.output is not None:
            write_gzip(arguments.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return

    observed_script = sha256_path(SCRIPT)
    if arguments.expected_script_sha256 != observed_script:
        raise GateError("registered run requires the exact preregistered script SHA-256")
    if arguments.output is None:
        raise GateError("registered run requires --output")
    enforce_frozen_preflight(preflight)
    profiles, matrix, target, matrix_report = build_profile_matrix(
        bases,
        representatives,
        arguments.workers,
        arguments.profile_budget,
    )
    decision = rank_and_solve(
        matrix,
        target,
        profile_column_descriptors(representatives),
    )
    scientific = {
        "schema": SCHEMA,
        "subject": preflight["subject"],
        "preflight_scientific_payload_sha256": preflight["scientific_payload_sha256"],
        "matrix": {key: value for key, value in matrix_report.items() if key != "seconds"},
        "decision": {
            **decision,
            "prime_results": [
                {key: value for key, value in report.items() if key != "seconds"}
                for report in decision["prime_results"]
            ],
        },
    }
    result = {
        **scientific,
        "mode": "registered-run",
        "bindings": preflight["bindings"],
        "controls": preflight["controls"],
        "script_sha256": observed_script,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "matrix_seconds": matrix_report["seconds"],
        "rank_seconds": [report["seconds"] for report in decision["prime_results"]],
        "workers": arguments.workers,
        "wall_seconds": time.perf_counter() - begun,
        "profiles_int16_c_sha256": hashlib.sha256(profiles.tobytes(order="C")).hexdigest(),
        "interpretation_boundary": (
            "Exact membership on 364 symmetric profiles is necessary only.  No global identity, "
            "network certificate, or unrestricted depth claim follows without generic-slice and "
            "complete CPWL replay."
        ),
    }
    write_gzip(arguments.output, result)
    print(
        json.dumps(
            {
                "output": str(arguments.output),
                "output_sha256": sha256_path(arguments.output),
                "scientific_payload_sha256": result["scientific_payload_sha256"],
                "decision": decision,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
