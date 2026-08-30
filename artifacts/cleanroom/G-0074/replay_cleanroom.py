#!/usr/bin/env python3
"""Independent exact semantic replay of the registered G-0074 witness.

Authorship: AzureHill, fresh-context clean-room auditor (Codex/GPT-5.4).

This file deliberately does not import or execute the G-0074 producer.  It
reconstructs each nonzero witness expression from the frozen MAX10
certificate, evaluates the four-level and three-level symmetrized columns with
a disjoint typed-forest dynamic program, and replays one common rational
coefficient vector on the registered Farey nodes and independent midpoints.

The replay proves equality only on the at-most-three-valued locus certified by
the Farey interpolation argument.  It is not a global CPWL identity.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import json
import math
import struct
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any, Iterable, Sequence

import numpy as np


EXPECTED_ARTIFACT_SHA256 = (
    "5de36fa1cf39d8524577cdc681b68220c9e807670aef7b14595e8b380bcd4fcb"
)
EXPECTED_PRODUCER_SHA256 = (
    "269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d"
)
EXPECTED_PREFLIGHT_SHA256 = (
    "a89e5b9a2366fb1d119981a49de2c72b8686255e0e522f7ce2ba0af829c26969"
)
EXPECTED_PREFLIGHT_SCIENCE_SHA256 = (
    "fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df"
)
EXPECTED_SCIENCE_SHA256 = (
    "1d56ed5afb9cf9dfcc602c43b34a215790066ebb3041087957db955a5476741c"
)
EXPECTED_SPARSE_SHA256 = (
    "f40be381b1ab2c8bc406c10a387719e07ebf0bafe07bffb065065048a8388d63"
)
EXPECTED_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
EXPECTED_ROW_MANIFEST_SHA256 = (
    "53e1766ce236da801ae963b47ee9ce42cdf5a10b978ccd69c9c9152b03ca140f"
)
EXPECTED_SELECTED_COMBINED_SHA256: str | None = (
    "efaf97c58cc2228115be1cba85882fcacc30f4e48966e5e9bb2137f2f38890ba"
)
EXPECTED_SELECTED_MIDPOINT_SHA256: str | None = (
    "b02d8c97eddaffd4f10c12c6ed7258f0ba187d3800a455794649205cec842fd8"
)
EXPECTED_INDEPENDENT_RANK_COLUMNS_SHA256: str | None = (
    "91e52a6b801ccf2d0353cebe1c6ec3612b1b828e3bec254e5203d1f8fa4ac80d"
)
EXPECTED_AUXILIARY_RANK_SELECTION_SHA256: str | None = (
    "7160e80b67e657032ed62d74506ce8b331e9cfe23b85ba35cbb58e04798bb953"
)
EXPECTED_SUPPORT_PIVOT_ROWS_SHA256 = (
    "8bc2b85ca15d8708cb4aeb5a847d25eb369aa85c6a041ef5caa1204e72df46ab"
)

N = 11
PRIMES = (1_000_003, 1_000_033, 1_000_037)
FAREY_F6 = (
    (0, 1),
    (1, 6),
    (1, 5),
    (1, 4),
    (1, 3),
    (2, 5),
    (1, 2),
    (3, 5),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (1, 1),
)


class AuditError(RuntimeError):
    """Fail-closed clean-room audit error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    require(path.is_file() and not path.is_symlink(), f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def load_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def four_profiles() -> list[tuple[int, int, int, int]]:
    profiles: list[tuple[int, int, int, int]] = []
    for zero in range(N + 1):
        for one in range(N + 1 - zero):
            for two in range(N + 1 - zero - one):
                profiles.append((zero, one, two, N - zero - one - two))
    require(len(profiles) == 364, "four-profile census drift")
    return profiles


def three_profiles() -> list[tuple[int, int, int]]:
    profiles = [
        (zero, middle, N - zero - middle)
        for zero in range(N + 1)
        for middle in range(N + 1 - zero)
    ]
    require(len(profiles) == 78, "three-profile census drift")
    return profiles


def assignment_count(profile: Sequence[int]) -> int:
    total = math.factorial(sum(profile))
    for count in profile:
        total //= math.factorial(count)
    return total


def midpoint_ratios() -> tuple[tuple[int, int], ...]:
    nodes = [Fraction(numerator, denominator) for numerator, denominator in FAREY_F6]
    return tuple(
        ((left + right) / 2).as_integer_ratio()
        for left, right in zip(nodes, nodes[1:])
    )


def row_descriptors() -> list[dict[str, Any]]:
    descriptors: list[dict[str, Any]] = [
        {"kind": "G-0073-four-level", "profile": list(profile)}
        for profile in four_profiles()
    ]
    for numerator, denominator in FAREY_F6:
        for profile in three_profiles():
            descriptors.append(
                {
                    "kind": "three-level-Farey-F6",
                    "ratio": [numerator, denominator],
                    "profile": list(profile),
                }
            )
    return descriptors


def target_panel(
    profiles: Sequence[Sequence[int]], levels: Sequence[int]
) -> list[int]:
    targets: list[int] = []
    for profile in profiles:
        highest = max(level for level, count in zip(levels, profile, strict=True) if count)
        targets.append(assignment_count(profile) * highest)
    return targets


def int64_sha256(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<q", int(value)))
    return digest.hexdigest()


def matrix_columns_sha256(columns: Sequence[Sequence[int]]) -> str:
    digest = hashlib.sha256()
    for column in columns:
        for value in column:
            digest.update(struct.pack("<q", int(value)))
    return digest.hexdigest()


def components(edges: Sequence[tuple[int, int]]) -> list[tuple[int, ...]]:
    adjacency = {vertex: set() for vertex in range(1, 11)}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    answer: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for initial in range(1, 11):
        if initial in seen:
            continue
        stack = [initial]
        seen.add(initial)
        component: list[int] = []
        while stack:
            vertex = stack.pop()
            component.append(vertex)
            for neighbor in adjacency[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        answer.append(tuple(sorted(component)))
    return sorted(answer, key=lambda item: (len(item), item))


def normalized_pair(term: dict[str, Any]) -> list[list[tuple[int, int]]] | None:
    pair = term.get("pair")
    if not isinstance(pair, list) or len(pair) != 2:
        return None
    sides: list[list[tuple[int, int]]] = []
    for side in pair:
        if not isinstance(side, list) or len(side) != 4:
            return None
        edges: list[tuple[int, int]] = []
        for edge in side:
            if not isinstance(edge, list) or len(edge) != 2:
                return None
            left, right = map(int, edge)
            if not (1 <= left <= 10 and 1 <= right <= 10) or left == right:
                return None
            edges.append(tuple(sorted((left, right))))
        if len(set(edges)) != 4:
            return None
        sides.append(edges)
    return sides


def eligible_base(term: dict[str, Any]) -> bool:
    sides = normalized_pair(term)
    if sides is None:
        return False
    union = sides[0] + sides[1]
    if len(set(union)) != 8:
        return False
    return sorted(map(len, components(union))) in ([2, 8], [3, 7], [4, 6], [5, 5])


Seed = tuple[int, int, int, int, int]


def certificate_bases_and_seeds(
    certificate: dict[str, Any],
) -> tuple[list[tuple[int, dict[str, Any]]], list[Seed], dict[str, int]]:
    require(certificate.get("n") == 10, "certificate dimension drift")
    terms = certificate.get("terms")
    require(isinstance(terms, list), "certificate terms missing")
    bases = [(index, term) for index, term in enumerate(terms) if eligible_base(term)]
    require(len(bases) == 252, "eligible MAX10 base census drift")
    seeds: list[Seed] = []
    topology: dict[str, int] = {}
    for base_position, (term_index, term) in enumerate(bases):
        sides = normalized_pair(term)
        require(sides is not None, "eligible base normalization failed")
        forest_components = components(sides[0] + sides[1])
        key = "+".join(map(str, map(len, forest_components)))
        topology[key] = topology.get(key, 0) + 1
        component_of = {
            vertex: set(component)
            for component in forest_components
            for vertex in component
        }
        for anchor in range(1, 11):
            for auxiliary in sorted(set(range(1, 11)) - component_of[anchor]):
                for orientation in (0, 1):
                    seeds.append(
                        (base_position, term_index, anchor, auxiliary, orientation)
                    )
    require(
        topology == {"2+8": 168, "3+7": 39, "4+6": 32, "5+5": 13},
        "eligible topology census drift",
    )
    require(len(seeds) == 18_400, "raw seed census drift")
    return bases, seeds, topology


def expression_from_seed(
    bases: Sequence[tuple[int, dict[str, Any]]], seed: Seed
) -> dict[str, Any]:
    base_position, term_index, anchor, auxiliary, orientation = seed
    observed_term_index, term = bases[base_position]
    require(observed_term_index == term_index, "seed term-index mismatch")
    return {
        "left": term["pair"][0],
        "right": term["pair"][1],
        "anchor": anchor,
        "auxiliary": auxiliary,
        "new_label": 11,
        "orientation": orientation,
    }


def validate_expression(expression: dict[str, Any]) -> None:
    require(expression.get("new_label") == 11, "expression new-label drift")
    require(expression.get("orientation") in (0, 1), "expression orientation drift")
    edges: list[tuple[int, int]] = []
    for name in ("left", "right"):
        side = expression.get(name)
        require(isinstance(side, list) and len(side) == 4, f"malformed {name} branch")
        for edge in side:
            require(isinstance(edge, list) and len(edge) == 2, "malformed expression edge")
            edges.append(tuple(sorted(map(int, edge))))
    forest_components = components(edges)
    require(len(forest_components) == 2, "expression union is not a two-component forest")
    anchor = int(expression["anchor"])
    auxiliary = int(expression["auxiliary"])
    require(
        not any(anchor in component and auxiliary in component for component in forest_components),
        "anchor and auxiliary are not cross-component",
    )


def adjacency_with_branches(expression: dict[str, Any]) -> dict[int, list[tuple[int, int]]]:
    adjacency: dict[int, list[tuple[int, int]]] = {vertex: [] for vertex in range(1, 11)}
    for branch, name in enumerate(("left", "right")):
        for left, right in expression[name]:
            adjacency[int(left)].append((int(right), branch))
            adjacency[int(right)].append((int(left), branch))
    return adjacency


def component_order(
    adjacency: dict[int, list[tuple[int, int]]], root: int
) -> tuple[list[int], dict[int, tuple[int, int]]]:
    parent: dict[int, tuple[int, int]] = {root: (0, -1)}
    order: list[int] = []
    stack = [root]
    while stack:
        vertex = stack.pop()
        order.append(vertex)
        for neighbor, branch in adjacency[vertex]:
            if neighbor == parent[vertex][0]:
                continue
            require(neighbor not in parent, "expression component contains a cycle")
            parent[neighbor] = (vertex, branch)
            stack.append(neighbor)
    return order, parent


def baseline_component_dp(
    expression: dict[str, Any], root: int
) -> list[dict[tuple[int, ...], int]]:
    """Count four-colour states `(counts..., left_sum, right_sum)`."""

    adjacency = adjacency_with_branches(expression)
    order, parent = component_order(adjacency, root)
    tables: dict[int, list[dict[tuple[int, ...], int]]] = {}
    for vertex in reversed(order):
        by_colour: list[dict[tuple[int, ...], int]] = []
        for colour in range(4):
            counts = [0] * 4
            counts[colour] = 1
            by_colour.append({(*counts, 0, 0): 1})
        for child, branch in adjacency[vertex]:
            if parent.get(child, (None, None))[0] != vertex:
                continue
            child_table = tables[child]
            merged: list[dict[tuple[int, ...], int]] = []
            for colour in range(4):
                destination: dict[tuple[int, ...], int] = {}
                for left_state, left_count in by_colour[colour].items():
                    for child_colour in range(4):
                        edge_value = max(colour, child_colour)
                        for right_state, right_count in child_table[child_colour].items():
                            state = (
                                *(left_state[index] + right_state[index] for index in range(4)),
                                left_state[4] + right_state[4] + (edge_value if branch == 0 else 0),
                                left_state[5] + right_state[5] + (edge_value if branch == 1 else 0),
                            )
                            destination[state] = destination.get(state, 0) + left_count * right_count
                merged.append(destination)
            by_colour = merged
        tables[vertex] = by_colour
    return tables[root]


def baseline_semantic_column(expression: dict[str, Any]) -> list[int]:
    profiles = four_profiles()
    profile_index = {profile: index for index, profile in enumerate(profiles)}
    expected = [assignment_count(profile) for profile in profiles]
    anchor = int(expression["anchor"])
    auxiliary = int(expression["auxiliary"])
    orientation = int(expression["orientation"])
    first = baseline_component_dp(expression, anchor)
    second = baseline_component_dp(expression, auxiliary)
    sums = [0] * len(profiles)
    counts = [0] * len(profiles)
    for anchor_colour in range(4):
        for auxiliary_colour in range(4):
            for first_state, first_count in first[anchor_colour].items():
                for second_state, second_count in second[auxiliary_colour].items():
                    base_counts = tuple(
                        first_state[index] + second_state[index] for index in range(4)
                    )
                    left_sum = first_state[4] + second_state[4]
                    right_sum = first_state[5] + second_state[5]
                    multiplicity = first_count * second_count
                    for new_colour in range(4):
                        profile = list(base_counts)
                        profile[new_colour] += 1
                        row = profile_index[tuple(profile)]
                        y_spoke = max(2 * anchor_colour, auxiliary_colour + new_colour)
                        doubled_anchor = 2 * anchor_colour
                        if orientation == 0:
                            value = max(left_sum + doubled_anchor, right_sum + y_spoke)
                        else:
                            value = max(left_sum + y_spoke, right_sum + doubled_anchor)
                        sums[row] += multiplicity * value
                        counts[row] += multiplicity
    require(counts == expected, "baseline Sym_avg multiplicity mismatch")
    return sums


def affine_component_dp(
    expression: dict[str, Any], root: int
) -> list[dict[tuple[int, ...], int]]:
    """Count three-colour affine states.

    A state is `(c0,c1,c2, Lt,L1,Rt,R1)` and represents branch sums
    `Lt*t+L1` and `Rt*t+R1`.  Edge maxima stay affine because `0<=t<=1`.
    """

    adjacency = adjacency_with_branches(expression)
    order, parent = component_order(adjacency, root)
    tables: dict[int, list[dict[tuple[int, ...], int]]] = {}
    for vertex in reversed(order):
        by_colour: list[dict[tuple[int, ...], int]] = []
        for colour in range(3):
            counts = [0] * 3
            counts[colour] = 1
            by_colour.append({(*counts, 0, 0, 0, 0): 1})
        for child, branch in adjacency[vertex]:
            if parent.get(child, (None, None))[0] != vertex:
                continue
            child_table = tables[child]
            merged: list[dict[tuple[int, ...], int]] = []
            for colour in range(3):
                destination: dict[tuple[int, ...], int] = {}
                for left_state, left_count in by_colour[colour].items():
                    for child_colour in range(3):
                        edge_colour = max(colour, child_colour)
                        edge_t = int(edge_colour == 1)
                        edge_one = int(edge_colour == 2)
                        for right_state, right_count in child_table[child_colour].items():
                            state = (
                                *(left_state[index] + right_state[index] for index in range(3)),
                                left_state[3] + right_state[3] + (edge_t if branch == 0 else 0),
                                left_state[4] + right_state[4] + (edge_one if branch == 0 else 0),
                                left_state[5] + right_state[5] + (edge_t if branch == 1 else 0),
                                left_state[6] + right_state[6] + (edge_one if branch == 1 else 0),
                            )
                            destination[state] = destination.get(state, 0) + left_count * right_count
                merged.append(destination)
            by_colour = merged
        tables[vertex] = by_colour
    return tables[root]


def scaled_colour(colour: int, numerator: int, denominator: int) -> int:
    return (0, numerator, denominator)[colour]


def three_semantic_panels(
    expression: dict[str, Any], ratios: Sequence[tuple[int, int]]
) -> list[list[int]]:
    profiles = three_profiles()
    profile_index = {profile: index for index, profile in enumerate(profiles)}
    expected = [assignment_count(profile) for profile in profiles]
    panels = [[0] * len(profiles) for _ in ratios]
    counts = [0] * len(profiles)
    anchor = int(expression["anchor"])
    auxiliary = int(expression["auxiliary"])
    orientation = int(expression["orientation"])
    first = affine_component_dp(expression, anchor)
    second = affine_component_dp(expression, auxiliary)
    for anchor_colour in range(3):
        for auxiliary_colour in range(3):
            for first_state, first_count in first[anchor_colour].items():
                for second_state, second_count in second[auxiliary_colour].items():
                    base_counts = tuple(
                        first_state[index] + second_state[index] for index in range(3)
                    )
                    left_t = first_state[3] + second_state[3]
                    left_one = first_state[4] + second_state[4]
                    right_t = first_state[5] + second_state[5]
                    right_one = first_state[6] + second_state[6]
                    multiplicity = first_count * second_count
                    for new_colour in range(3):
                        profile = list(base_counts)
                        profile[new_colour] += 1
                        row = profile_index[tuple(profile)]
                        counts[row] += multiplicity
                        for panel, (numerator, denominator) in zip(panels, ratios, strict=True):
                            anchor_value = scaled_colour(anchor_colour, numerator, denominator)
                            auxiliary_value = scaled_colour(auxiliary_colour, numerator, denominator)
                            new_value = scaled_colour(new_colour, numerator, denominator)
                            left_sum = left_t * numerator + left_one * denominator
                            right_sum = right_t * numerator + right_one * denominator
                            y_spoke = max(2 * anchor_value, auxiliary_value + new_value)
                            doubled_anchor = 2 * anchor_value
                            if orientation == 0:
                                value = max(left_sum + doubled_anchor, right_sum + y_spoke)
                            else:
                                value = max(left_sum + y_spoke, right_sum + doubled_anchor)
                            panel[row] += multiplicity * value
    require(counts == expected, "three-level Sym_avg multiplicity mismatch")
    return panels


def carrier_panel(
    profiles: Sequence[Sequence[int]], levels: Sequence[int], name: str
) -> list[int]:
    result: list[int] = []
    for profile in profiles:
        total = assignment_count(profile)
        if name == "C_L":
            value = Fraction(
                total * sum(count * level for count, level in zip(profile, levels, strict=True)),
                N,
            )
        elif name == "C_E":
            value = Fraction(0)
            for first in range(len(profile)):
                for second in range(len(profile)):
                    ordered = profile[first] * (profile[second] - int(first == second))
                    value += Fraction(total * ordered, N * (N - 1)) * max(
                        levels[first], levels[second]
                    )
        elif name == "C_Y":
            value = Fraction(0)
            for first in range(len(profile)):
                for second in range(len(profile)):
                    remaining_second = profile[second] - int(first == second)
                    if remaining_second <= 0:
                        continue
                    for third in range(len(profile)):
                        remaining_third = (
                            profile[third]
                            - int(first == third)
                            - int(second == third)
                        )
                        if remaining_third <= 0:
                            continue
                        ordered = profile[first] * remaining_second * remaining_third
                        value += Fraction(total * ordered, N * (N - 1) * (N - 2)) * max(
                            2 * levels[first], levels[second] + levels[third]
                        )
        else:
            raise AuditError(f"unknown carrier: {name}")
        require(value.denominator == 1, f"nonintegral {name} assignment sum")
        result.append(value.numerator)
    return result


def combined_carrier(name: str) -> tuple[list[int], list[int]]:
    baseline = carrier_panel(four_profiles(), (0, 1, 2, 3), name)
    farey: list[int] = []
    for numerator, denominator in FAREY_F6:
        farey.extend(carrier_panel(three_profiles(), (0, numerator, denominator), name))
    midpoints: list[int] = []
    for numerator, denominator in midpoint_ratios():
        midpoints.extend(carrier_panel(three_profiles(), (0, numerator, denominator), name))
    return baseline + farey, midpoints


def semantic_expression_columns(expression: dict[str, Any]) -> tuple[list[int], list[int]]:
    validate_expression(expression)
    ratios = FAREY_F6 + midpoint_ratios()
    panels = three_semantic_panels(expression, ratios)
    combined = baseline_semantic_column(expression)
    for panel in panels[: len(FAREY_F6)]:
        combined.extend(panel)
    midpoint: list[int] = []
    for panel in panels[len(FAREY_F6) :]:
        midpoint.extend(panel)
    require(len(combined) == 1378 and len(midpoint) == 936, "column shape drift")
    return combined, midpoint


def validate_bindings(repo: Path, outcome: dict[str, Any]) -> int:
    bindings = outcome.get("bindings")
    require(isinstance(bindings, dict), "outcome bindings missing")
    for name, binding in bindings.items():
        require(isinstance(binding, dict), f"malformed binding: {name}")
        path = repo / str(binding["path"])
        require(path.is_file(), f"binding missing: {name}: {path}")
        require(sha256_path(path) == binding["sha256"], f"binding digest drift: {name}")
        require(path.stat().st_size == binding["bytes"], f"binding size drift: {name}")
    return len(bindings)


def verify_documents(
    repo: Path, artifact: Path, certificate_path: Path
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    require(sha256_path(artifact) == EXPECTED_ARTIFACT_SHA256, "outcome artifact digest drift")
    producer_path = repo / "artifacts/math/G-0074/farey_three_level_gate.py"
    preflight_path = repo / "artifacts/math/G-0074/farey_three_level_preflight_v1.json.gz"
    require(sha256_path(producer_path) == EXPECTED_PRODUCER_SHA256, "producer digest drift")
    require(sha256_path(preflight_path) == EXPECTED_PREFLIGHT_SHA256, "preflight digest drift")
    require(sha256_path(certificate_path) == EXPECTED_CERTIFICATE_SHA256, "certificate digest drift")
    outcome = load_gzip_json(artifact)
    preflight = load_gzip_json(preflight_path)
    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    require(isinstance(certificate, dict), "malformed certificate")
    require(outcome.get("script_sha256") == EXPECTED_PRODUCER_SHA256, "outcome producer pin drift")
    require(preflight.get("script_sha256") == EXPECTED_PRODUCER_SHA256, "preflight producer pin drift")
    preflight_science = {
        key: preflight[key] for key in ("schema", "bindings", "controls", "subject")
    }
    require(
        canonical_sha256(preflight_science) == EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "preflight scientific payload digest drift",
    )
    require(
        preflight.get("scientific_payload_sha256") == EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "preflight stored scientific digest drift",
    )
    science = {
        key: outcome[key]
        for key in (
            "schema",
            "subject",
            "preflight_scientific_payload_sha256",
            "matrix",
            "decision",
            "interior_member_replay",
        )
    }
    require(canonical_sha256(science) == EXPECTED_SCIENCE_SHA256, "outcome science digest drift")
    require(outcome.get("scientific_payload_sha256") == EXPECTED_SCIENCE_SHA256, "stored science digest drift")
    require(outcome.get("bindings") == preflight.get("bindings"), "binding set changed after preflight")
    require(outcome.get("controls") == preflight.get("controls"), "controls changed after preflight")
    require(outcome.get("subject") == preflight.get("subject"), "subject changed after preflight")
    require(
        outcome.get("preflight_scientific_payload_sha256") == EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "outcome does not bind preflight science",
    )
    validate_bindings(repo, outcome)
    require(outcome.get("schema") == "max11-g0074-farey-three-level-gate-v1", "schema drift")
    require(outcome["decision"].get("result") == "FAREY_GATE_EXACT_Q_MEMBERSHIP", "decision drift")
    require(outcome["decision"].get("exact_dual") is None, "member outcome contains dual")
    return outcome, preflight, certificate


def validate_targets(outcome: dict[str, Any]) -> tuple[list[int], list[int], list[int]]:
    baseline_target = target_panel(four_profiles(), (0, 1, 2, 3))
    farey_target: list[int] = []
    for numerator, denominator in FAREY_F6:
        farey_target.extend(target_panel(three_profiles(), (0, numerator, denominator)))
    midpoint_target: list[int] = []
    for numerator, denominator in midpoint_ratios():
        midpoint_target.extend(target_panel(three_profiles(), (0, numerator, denominator)))
    combined_target = baseline_target + farey_target
    matrix = outcome["matrix"]
    interior = outcome["interior_member_replay"]
    require(int64_sha256(baseline_target) == matrix["baseline_target_sha256"], "baseline target hash drift")
    require(int64_sha256(farey_target) == matrix["farey_target_int64_c_sha256"], "Farey target hash drift")
    require(int64_sha256(combined_target) == matrix["combined_target_int64_c_sha256"], "combined target hash drift")
    require(int64_sha256(midpoint_target) == interior["target_sha256"], "midpoint target hash drift")
    require(len(combined_target) == 1378 and len(midpoint_target) == 936, "target shape drift")
    require(canonical_sha256(row_descriptors()) == EXPECTED_ROW_MANIFEST_SHA256, "row manifest drift")
    require(matrix["row_manifest_sha256"] == EXPECTED_ROW_MANIFEST_SHA256, "stored row manifest drift")
    return combined_target, midpoint_target, baseline_target


def validate_sparse_descriptors(
    outcome: dict[str, Any],
    bases: Sequence[tuple[int, dict[str, Any]]],
    seeds: Sequence[Seed],
) -> list[dict[str, Any]]:
    solution = outcome["decision"]["exact_solution"]
    sparse = solution.get("sparse_coefficients")
    require(isinstance(sparse, list), "sparse coefficients missing")
    require(len(sparse) == solution.get("support_size") == 443, "support size drift")
    require(canonical_sha256(sparse) == EXPECTED_SPARSE_SHA256, "sparse witness digest drift")
    require(solution.get("sparse_coefficients_sha256") == EXPECTED_SPARSE_SHA256, "stored sparse digest drift")
    orbit_items = [item for item in sparse if item["descriptor"].get("kind") == "Y-spoke-orbit-representative"]
    carrier_items = [item for item in sparse if item["descriptor"].get("kind") == "carrier"]
    require(len(orbit_items) == 442 and len(carrier_items) == 1, "support kind census drift")
    require(
        carrier_items[0]["column_index"] == 8105
        and carrier_items[0]["coefficient"] == "1"
        and carrier_items[0]["descriptor"]
        == {"kind": "carrier", "name": "C_E", "representative": "max(x_1,x_2)"},
        "selected carrier convention drift",
    )
    indices = [int(item["column_index"]) for item in sparse]
    require(indices == sorted(indices) and len(indices) == len(set(indices)), "support column ordering drift")
    require(all(0 <= index < 8104 for index in indices[:-1]), "orbit column index outside family")
    for item in orbit_items:
        representative = item["descriptor"]["representative"]
        expression = representative["expression"]
        base_position = int(representative["base_position"])
        term_index = int(representative["base_term_index"])
        raw_index = int(representative["raw_index"])
        require(0 <= base_position < len(bases), "descriptor base position outside census")
        require(0 <= raw_index < len(seeds), "descriptor raw index outside census")
        require(bases[base_position][0] == term_index, "descriptor base term mismatch")
        require(
            bases[base_position][1]["pair"] == [expression["left"], expression["right"]],
            "descriptor expression/certificate branch mismatch",
        )
        expected_seed = (
            base_position,
            term_index,
            int(expression["anchor"]),
            int(expression["auxiliary"]),
            int(expression["orientation"]),
        )
        require(seeds[raw_index] == expected_seed, "descriptor raw-index binding mismatch")
        validate_expression(expression)
    return sparse


def exact_common_denominator_replay(
    coefficients: Sequence[Fraction],
    columns: Sequence[Sequence[int]],
    target: Sequence[int],
) -> tuple[int, int]:
    require(len(coefficients) == len(columns), "coefficient/column shape mismatch")
    denominator = 1
    for coefficient in coefficients:
        denominator = math.lcm(denominator, coefficient.denominator)
    weights = [
        coefficient.numerator * (denominator // coefficient.denominator)
        for coefficient in coefficients
    ]
    nonzero = 0
    for row, expected in enumerate(target):
        observed = sum(weight * column[row] for weight, column in zip(weights, columns, strict=True))
        if observed != int(expected) * denominator:
            nonzero += 1
            if nonzero <= 3:
                print(f"nonzero exact residual at row {row}", file=sys.stderr)
    require(nonzero == 0, f"exact witness has {nonzero} nonzero rows")
    return denominator.bit_length(), nonzero


class ModularColumnBasis:
    """Independent NumPy-backed column-echelon basis modulo a small prime."""

    def __init__(self, rows: int, prime: int) -> None:
        self.rows = rows
        self.prime = prime
        self.pivots: list[int] = []
        self.vectors: list[np.ndarray] = []

    def add(self, source: Sequence[int]) -> bool:
        require(len(source) == self.rows, "rank column length drift")
        vector = np.remainder(np.asarray(source, dtype=np.int64), self.prime)
        for pivot, basis in zip(self.pivots, self.vectors, strict=True):
            multiplier = int(vector[pivot])
            if multiplier:
                vector = np.remainder(vector - multiplier * basis, self.prime)
        nonzero = np.flatnonzero(vector)
        if nonzero.size == 0:
            return False
        pivot = int(nonzero[0])
        inverse = pow(int(vector[pivot]), -1, self.prime)
        vector = np.remainder(vector * inverse, self.prime)
        self.pivots.append(pivot)
        self.vectors.append(vector)
        return True

    @property
    def rank(self) -> int:
        return len(self.pivots)


def independent_support_rank(
    witness_columns: Sequence[Sequence[int]],
) -> tuple[list[list[int]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Certify the materialized support rank, without claiming a full-matrix rank."""

    rank_columns = [list(column) for column in witness_columns]
    rank_descriptors: list[dict[str, Any]] = [
        {"kind": "registered-nonzero-support", "position": index}
        for index in range(len(rank_columns))
    ]
    linear_column, _linear_midpoint = combined_carrier("C_L")
    first_basis = ModularColumnBasis(1378, PRIMES[0])
    for index, column in enumerate(rank_columns):
        require(first_basis.add(column), f"witness support is dependent at position {index}")
    require(first_basis.rank == 443, "registered support rank is not 443")
    require(first_basis.add(linear_column), "C_L does not extend registered support")
    rank_columns.append(linear_column)
    rank_descriptors.append({"kind": "carrier", "name": "C_L"})
    require(first_basis.rank == 444, "support-plus-C_L rank drift")
    rank_results: list[dict[str, Any]] = []
    for prime in PRIMES:
        verifier = ModularColumnBasis(1378, prime)
        for column in rank_columns:
            require(verifier.add(column), f"rank-444 minor vanished modulo {prime}")
        require(verifier.rank == 444, f"rank below 444 modulo {prime}")
        require(
            canonical_sha256(verifier.pivots) == EXPECTED_SUPPORT_PIVOT_ROWS_SHA256,
            f"support pivot-row digest drift modulo {prime}",
        )
        rank_results.append(
            {
                "prime": prime,
                "rank": verifier.rank,
                "pivot_rows_sha256": canonical_sha256(verifier.pivots),
            }
        )
    auxiliary = [rank_descriptors[-1]]
    return rank_columns, auxiliary, rank_results


def run(
    repo: Path, artifact: Path, certificate_path: Path, workers: int
) -> dict[str, Any]:
    started = time.monotonic()
    outcome, _preflight, certificate = verify_documents(repo, artifact, certificate_path)
    binding_count = validate_bindings(repo, outcome)
    combined_target, midpoint_target, baseline_target = validate_targets(outcome)
    bases, seeds, topology = certificate_bases_and_seeds(certificate)
    sparse = validate_sparse_descriptors(outcome, bases, seeds)

    orbit_items = [
        item
        for item in sparse
        if item["descriptor"]["kind"] == "Y-spoke-orbit-representative"
    ]
    expressions = [
        item["descriptor"]["representative"]["expression"] for item in orbit_items
    ]
    with ProcessPoolExecutor(max_workers=workers) as pool:
        orbit_results = list(pool.map(semantic_expression_columns, expressions, chunksize=1))
    orbit_result_iterator = iter(orbit_results)

    combined_columns: list[list[int]] = []
    midpoint_columns: list[list[int]] = []
    coefficients: list[Fraction] = []
    orbit_count = 0
    pair_carrier = combined_carrier("C_E")
    for position, item in enumerate(sparse, start=1):
        descriptor = item["descriptor"]
        if descriptor["kind"] == "carrier":
            combined, midpoint = pair_carrier
        else:
            combined, midpoint = next(orbit_result_iterator)
            orbit_count += 1
        combined_columns.append(combined)
        midpoint_columns.append(midpoint)
        coefficients.append(Fraction(str(item["coefficient"])))
        if position % 32 == 0 or position == len(sparse):
            print(
                f"clean-room witness columns: {position}/{len(sparse)}; elapsed={time.monotonic() - started:.1f}s",
                file=sys.stderr,
                flush=True,
            )

    selected_combined_digest = matrix_columns_sha256(combined_columns)
    selected_midpoint_digest = matrix_columns_sha256(midpoint_columns)
    if EXPECTED_SELECTED_COMBINED_SHA256 is not None:
        require(selected_combined_digest == EXPECTED_SELECTED_COMBINED_SHA256, "selected combined digest drift")
    if EXPECTED_SELECTED_MIDPOINT_SHA256 is not None:
        require(selected_midpoint_digest == EXPECTED_SELECTED_MIDPOINT_SHA256, "selected midpoint digest drift")

    combined_denominator_bits, _ = exact_common_denominator_replay(
        coefficients, combined_columns, combined_target
    )
    midpoint_denominator_bits, _ = exact_common_denominator_replay(
        coefficients, midpoint_columns, midpoint_target
    )
    require(combined_denominator_bits == midpoint_denominator_bits, "replay denominator drift")

    # Cross-check the baseline prefix against the already clean-room-derived G-0073
    # target encoding, without importing that audit implementation.
    require(
        int64_sha256(baseline_target)
        == "a3d3be16df8de6f25b40e318f656efbee4607806413e72a48b2d276d7f21f4d7",
        "baseline target digest differs from G-0073",
    )

    rank_columns, auxiliary_rank_selection, rank_results = independent_support_rank(
        combined_columns
    )
    rank_columns_digest = matrix_columns_sha256(rank_columns)
    auxiliary_digest = canonical_sha256(auxiliary_rank_selection)
    if EXPECTED_INDEPENDENT_RANK_COLUMNS_SHA256 is not None:
        require(rank_columns_digest == EXPECTED_INDEPENDENT_RANK_COLUMNS_SHA256, "rank-column digest drift")
    if EXPECTED_AUXILIARY_RANK_SELECTION_SHA256 is not None:
        require(auxiliary_digest == EXPECTED_AUXILIARY_RANK_SELECTION_SHA256, "rank-selection digest drift")

    interior = outcome["interior_member_replay"]
    require(
        interior.get("rows_checked") == len(midpoint_target)
        and interior.get("midpoint_ratios") == [list(ratio) for ratio in midpoint_ratios()],
        "registered midpoint panel metadata drift",
    )
    return {
        "verdict": "PASS_THREE_LEVEL_CLEANROOM_SEMANTIC_REPLAY",
        "authorship": {
            "agent": "AzureHill",
            "role": "fresh-context clean-room auditor",
            "model_lineage": "Codex/GPT-5.4; same-lineage T1, not T2 or human review",
        },
        "artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "scientific_payload_sha256": EXPECTED_SCIENCE_SHA256,
        "preflight_scientific_payload_sha256": EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "sparse_coefficients_sha256": EXPECTED_SPARSE_SHA256,
        "binding_count": binding_count,
        "eligible_base_count": len(bases),
        "raw_seed_count": len(seeds),
        "topology_census": topology,
        "selected_descriptor_errors": 0,
        "selected_orbit_columns": orbit_count,
        "selected_carrier_columns": len(sparse) - orbit_count,
        "common_coefficient_vector_size": len(coefficients),
        "combined_rows": len(combined_target),
        "baseline_rows": len(baseline_target),
        "farey_rows": len(combined_target) - len(baseline_target),
        "midpoint_rows": len(midpoint_target),
        "selected_combined_int64_columnmajor_sha256": selected_combined_digest,
        "selected_midpoint_int64_columnmajor_sha256": selected_midpoint_digest,
        "exact_common_denominator_bits": combined_denominator_bits,
        "combined_exact_residual_nonzero_rows": 0,
        "midpoint_exact_residual_nonzero_rows": 0,
        "independent_rank_columns": len(rank_columns),
        "independent_rank_columns_sha256": rank_columns_digest,
        "auxiliary_rank_selection": auxiliary_rank_selection,
        "auxiliary_rank_selection_sha256": auxiliary_digest,
        "rank_results": rank_results,
        "claim_boundary": (
            "One emitted 443-term rational vector equals MAX11 on the 364 frozen "
            "four-level rows, all 13*78 Farey F6 three-level rows, and all 12*78 "
            "interior midpoint rows. Together with the separately stated Farey "
            "piecewise-affine argument this supports the at-most-three-valued locus "
            "only; it is not a global CPWL identity or unrestricted depth theorem."
        ),
        "limitations": [
            "The audit reconstructs the 443 nonzero witness columns, not all 8,107 columns, so it does not reproduce the full matrix hashes or a rank upper bound.",
            "The sparse artifact does not expose the 17 zero-coefficient pivot descriptors. This audit proves rank 444 for the 443 support columns plus C_L, but does not independently reproduce the producer's rank-460 lower bound or pivot lists.",
            "Orbit-index canonicalization and the full 8,104-orbit census remain frozen-preflight bindings; every emitted expression itself is independently certificate-bound.",
            "This is fresh same-model-lineage T1 evidence, not T2 or human refereeing.",
        ],
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    default_repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("artifacts/math/G-0074/farey_three_level_gate_v1.json.gz"),
    )
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument(
        "--certificate",
        type=Path,
        default=Path("subjects/max-relu-known/certificates/certificate_10_4.json"),
    )
    arguments = parser.parse_args()
    repo = arguments.repo.resolve()
    artifact = arguments.artifact if arguments.artifact.is_absolute() else repo / arguments.artifact
    certificate = (
        arguments.certificate
        if arguments.certificate.is_absolute()
        else repo / arguments.certificate
    )
    require(arguments.workers >= 1, "workers must be positive")
    result = run(repo, artifact, certificate, arguments.workers)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, KeyError, IndexError, TypeError, ValueError) as error:
        print(f"CLEANROOM AUDIT FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
