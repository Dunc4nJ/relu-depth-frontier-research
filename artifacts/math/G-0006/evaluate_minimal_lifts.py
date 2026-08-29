#!/usr/bin/env python3
"""Exact orbit-evaluation sieve for a restricted MAX11 lift family.

Family: start from each full-vertex, simple, two-component forest term in the frozen MAX10
certificate.  Add vertex 11 with one new A edge and one new B edge whose old endpoints lie in the
same component.  This creates the minimal cycle or cross-colour overlap needed to escape the
balanced-tree separator.

The program evaluates every candidate on all permutation orbits of {0,1,2,3}^11.  Membership of
the MAX11 evaluation vector in the candidate span is only a necessary condition for a global
identity.  It is a discovery sieve, not a certificate verifier.
"""

from __future__ import annotations

import argparse
import hashlib
from itertools import combinations
import json
from math import factorial
from pathlib import Path

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[3]
CERTIFICATE = (
    PROJECT_ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
)
N = 11
GROUP_ASSIGNMENT_BUDGET = 600_000


def build_bases():
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    bases = []
    candidate_metadata = []
    for term_index, term in enumerate(document["terms"]):
        left = tuple(tuple(sorted(edge)) for edge in term["pair"][0])
        right = tuple(tuple(sorted(edge)) for edge in term["pair"][1])
        all_edges = left + right
        if any(a == b for a, b in all_edges) or len(set(all_edges)) != 8:
            continue
        vertices = {vertex for edge in all_edges for vertex in edge}
        if len(vertices) != 10:
            continue

        parent = {vertex: vertex for vertex in vertices}

        def find(vertex):
            while parent[vertex] != vertex:
                parent[vertex] = parent[parent[vertex]]
                vertex = parent[vertex]
            return vertex

        for a, b in set(all_edges):
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_b] = root_a
        components_by_root = {}
        for vertex in vertices:
            components_by_root.setdefault(find(vertex), []).append(vertex)
        if len(components_by_root) != 2:
            continue
        components = tuple(tuple(component) for component in components_by_root.values())
        base_index = len(bases)
        bases.append((term_index, left, right, components))
        for component_index, component in enumerate(components):
            for left_endpoint in component:
                for right_endpoint in component:
                    candidate_metadata.append(
                        (
                            base_index,
                            term_index,
                            component_index,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
    if len(bases) != 252 or len(candidate_metadata) != 16_000:
        raise AssertionError((len(bases), len(candidate_metadata)))
    digest = hashlib.sha256(
        json.dumps(candidate_metadata, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    return bases, candidate_metadata, digest


def all_profiles() -> list[tuple[int, int, int, int]]:
    return [
        (count_zero, count_one, count_two, N - count_zero - count_one - count_two)
        for count_zero in range(N + 1)
        for count_one in range(N + 1 - count_zero)
        for count_two in range(N + 1 - count_zero - count_one)
    ]


def assignment_count(profile: tuple[int, int, int, int]) -> int:
    result = factorial(N)
    for count in profile:
        result //= factorial(count)
    return result


def profile_groups() -> list[list[tuple[int, int, int, int]]]:
    groups: list[list[tuple[int, int, int, int]]] = []
    current: list[tuple[int, int, int, int]] = []
    current_weight = 0
    for profile in all_profiles():
        weight = assignment_count(profile)
        if current and current_weight + weight > GROUP_ASSIGNMENT_BUDGET:
            groups.append(current)
            current = []
            current_weight = 0
        current.append(profile)
        current_weight += weight
    if current:
        groups.append(current)
    if sum(map(len, groups)) != 364:
        raise AssertionError("profile grouping lost a row")
    return groups


def assignments(profile: tuple[int, int, int, int]) -> np.ndarray:
    _, count_one, count_two, count_three = profile
    vertices = tuple(range(N))
    output = []
    for threes in combinations(vertices, count_three):
        three_set = set(threes)
        without_three = tuple(vertex for vertex in vertices if vertex not in three_set)
        for twos in combinations(without_three, count_two):
            two_set = set(twos)
            without_two = tuple(vertex for vertex in without_three if vertex not in two_set)
            for ones in combinations(without_two, count_one):
                value = [0] * N
                for vertex in ones:
                    value[vertex] = 1
                for vertex in twos:
                    value[vertex] = 2
                for vertex in threes:
                    value[vertex] = 3
                output.append(value)
    result = np.asarray(output, dtype=np.uint8).T
    if result.shape != (N, assignment_count(profile)):
        raise AssertionError((profile, result.shape))
    return result


def build_group(group_index: int, output_directory: Path) -> Path:
    bases, candidate_metadata, candidate_digest = build_bases()
    groups = profile_groups()
    if not (0 <= group_index < len(groups)):
        raise SystemExit(f"group index must be in [0,{len(groups)})")
    profiles = groups[group_index]
    edges = [(a, b) for a in range(1, N + 1) for b in range(a, N + 1)]
    edge_index = {edge: index for index, edge in enumerate(edges)}
    rows = []
    targets = []

    for profile in profiles:
        levels = assignments(profile)
        state_count = levels.shape[1]
        edge_values = np.asarray(
            [np.maximum(levels[a - 1], levels[b - 1]) for a, b in edges],
            dtype=np.uint8,
        )
        new_edge_values = edge_values[
            [edge_index[(endpoint, N)] for endpoint in range(1, N)]
        ]
        row = np.empty(len(candidate_metadata), dtype=np.int64)
        offset = 0
        for _, left, right, components in bases:
            left_base = edge_values[[edge_index[edge] for edge in left]].sum(
                axis=0, dtype=np.int16
            )
            right_base = edge_values[[edge_index[edge] for edge in right]].sum(
                axis=0, dtype=np.int16
            )
            left_values = left_base[None, :] + new_edge_values
            right_values = right_base[None, :] + new_edge_values
            endpoint_sums = np.maximum(
                left_values[:, None, :], right_values[None, :, :]
            ).sum(axis=2, dtype=np.int64)
            for component in components:
                for left_endpoint in component:
                    for right_endpoint in component:
                        row[offset] = endpoint_sums[left_endpoint - 1, right_endpoint - 1]
                        offset += 1
        if offset != len(candidate_metadata):
            raise AssertionError("candidate row length mismatch")
        rows.append(row)
        target_level = max(level for level, count in enumerate(profile) if count)
        targets.append(state_count * target_level)

    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"group-{group_index:02d}.npz"
    np.savez(
        destination,
        schema=np.asarray(["max11-minimal-lifts-orbits-v1"]),
        candidate_sha256=np.asarray([candidate_digest]),
        group_index=np.asarray([group_index], dtype=np.int64),
        group_count=np.asarray([len(groups)], dtype=np.int64),
        profiles=np.asarray(profiles, dtype=np.int64),
        rows=np.asarray(rows, dtype=np.int64),
        targets=np.asarray(targets, dtype=np.int64),
    )
    return destination


def modular_span(output_directory: Path, prime: int) -> tuple[int, bool, list[tuple]]:
    _, candidate_metadata, candidate_digest = build_bases()
    groups = profile_groups()
    rows = []
    targets = []
    profiles = []
    for group_index in range(len(groups)):
        path = output_directory / f"group-{group_index:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != "max11-minimal-lifts-orbits-v1":
                raise ValueError(f"schema mismatch: {path}")
            if str(data["candidate_sha256"][0]) != candidate_digest:
                raise ValueError(f"candidate digest mismatch: {path}")
            if int(data["group_index"][0]) != group_index:
                raise ValueError(f"group index mismatch: {path}")
            rows.append(data["rows"])
            targets.append(data["targets"])
            profiles.append(data["profiles"])
    matrix = np.concatenate(rows, axis=0)
    target = np.concatenate(targets)
    profile_array = np.concatenate(profiles, axis=0)
    if matrix.shape != (364, len(candidate_metadata)):
        raise AssertionError(matrix.shape)
    if [tuple(row) for row in profile_array.tolist()] != all_profiles():
        raise AssertionError("profile order/coverage mismatch")
    if prime <= 3:
        raise ValueError("prime must exceed all grid levels")

    basis: dict[int, np.ndarray] = {}

    def reduce_vector(vector: np.ndarray) -> np.ndarray:
        for pivot in sorted(basis):
            if vector[pivot]:
                vector = (vector - vector[pivot] * basis[pivot]) % prime
        return vector

    for column_index in range(matrix.shape[1]):
        vector = reduce_vector(matrix[:, column_index] % prime)
        nonzero = np.flatnonzero(vector)
        if len(nonzero):
            pivot = int(nonzero[0])
            vector = vector * pow(int(vector[pivot]), prime - 2, prime) % prime
            basis[pivot] = vector
    residual = reduce_vector(target % prime)
    failures = [
        (tuple(profile_array[index].tolist()), int(value))
        for index, value in enumerate(residual)
        if value
    ]
    return len(basis), not failures, failures


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("groups", "build", "rank"))
    parser.add_argument("--group", type=int)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--prime", type=int, default=1_000_003)
    args = parser.parse_args()

    if args.mode == "groups":
        for index, group in enumerate(profile_groups()):
            print(index, len(group), sum(assignment_count(profile) for profile in group))
    elif args.mode == "build":
        if args.group is None:
            raise SystemExit("build mode requires --group")
        print(build_group(args.group, args.output_directory))
    else:
        rank, member, failures = modular_span(args.output_directory, args.prime)
        print(f"prime={args.prime} rank={rank} target_member={member}")
        if failures:
            print(f"first residual rows: {failures[:10]}")


if __name__ == "__main__":
    main()
