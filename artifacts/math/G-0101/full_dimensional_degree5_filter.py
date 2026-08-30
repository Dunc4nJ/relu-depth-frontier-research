#!/usr/bin/env python3
"""Exact affine-dimension filter for active degree-five MAX11 atoms.

This script audits the frozen G-0038 orbit stream.  It proves no semantic
span statement: it only decides which active signed-mass-five graphical
atoms can themselves have affine dimension ten.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import platform
import sys
import time
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_STREAM = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
DEFAULT_MANIFEST = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json"
)
DEFAULT_OUTPUT = Path(__file__).with_name("full_dimensional_degree5_census_v1.json")

EXPECTED_COMPRESSED_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_TARGET_JSONL_SHA256 = (
    "016bc3cfd5a27262c3d3659d35c6789e07aeeb8f9085de42e71d72cd900ce446"
)
EXPECTED_TARGET_COUNT = 384_425
EXPECTED_CONNECTED_FULL = 12_459
EXPECTED_TWO_COMPONENT_FULL = 83_595
EXPECTED_TWO_COMPONENT_BALANCED = 10_232
EXPECTED_FULL_TOTAL = 96_054


class FilterError(RuntimeError):
    """Raised when an input, theorem invariant, or control drifts."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def components(
    edges: Sequence[tuple[int, int]], n: int
) -> tuple[tuple[tuple[int, ...], ...], tuple[int, ...]]:
    parent = list(range(n))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    def union(left: int, right: int) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[right_root] = left_root

    for left, right in edges:
        if left != right:
            union(left, right)
    blocks: dict[int, list[int]] = {}
    for vertex in range(n):
        blocks.setdefault(find(vertex), []).append(vertex)
    ordered = tuple(sorted((tuple(block) for block in blocks.values()), key=min))
    component_of = [0] * n
    for index, block in enumerate(ordered):
        for vertex in block:
            component_of[vertex] = index
    return ordered, tuple(component_of)


def branch_mass(
    edges: Sequence[tuple[int, int]], component_of: Sequence[int], count: int
) -> tuple[int, ...]:
    mass = [0] * count
    for left, right in edges:
        if component_of[left] != component_of[right]:
            raise FilterError("an edge crossed a computed union component")
        mass[component_of[left]] += 1
    return tuple(mass)


def classify(row: dict[str, object], n: int = 11) -> dict[str, object]:
    negative = tuple(tuple(map(int, edge)) for edge in row["negative_edges"])
    positive = tuple(tuple(map(int, edge)) for edge in row["positive_edges"])
    if len(negative) != 5 or len(positive) != 5:
        raise FilterError("target record is not a balanced five/five signing")
    if set(negative) & set(positive):
        raise FilterError("opposite-sign twins survived cancellation")
    active = {vertex for edge in negative + positive for vertex in edge}
    if active != set(range(n)):
        raise FilterError(f"record is not active on all {n} coordinates")
    blocks, component_of = components(negative + positive, n)
    count = len(blocks)
    negative_mass = branch_mass(negative, component_of, count)
    positive_mass = branch_mass(positive, component_of, count)
    delta = tuple(p - q for p, q in zip(positive_mass, negative_mass))
    if sum(delta) != 0:
        raise FilterError("equal branch degrees did not give zero total imbalance")
    offset_survives = any(delta)
    dimension = n - count + int(offset_survives)
    full = dimension == n - 1
    if full != (count == 1 or (count == 2 and offset_survives)):
        raise FilterError("closed-form full-dimensional criterion disagreed")
    if int(row["abs_components"]) != count:
        raise FilterError("serialized component count disagreed")
    if int(row["abs_beta"]) != 10 - n + count:
        raise FilterError("serialized beta disagreed")
    return {
        "components": [list(block) for block in blocks],
        "component_count": count,
        "negative_component_mass": list(negative_mass),
        "positive_component_mass": list(positive_mass),
        "component_imbalance": list(delta),
        "offset_survives_mod_direction_span": offset_survives,
        "affine_dimension": dimension,
        "full_dimensional": full,
    }


def exact_rank(rows: Iterable[Sequence[int]]) -> int:
    matrix = [list(map(Fraction, row)) for row in rows if any(row)]
    if not matrix:
        return 0
    row_count, column_count = len(matrix), len(matrix[0])
    rank = 0
    for column in range(column_count):
        pivot = next(
            (index for index in range(rank, row_count) if matrix[index][column]),
            None,
        )
        if pivot is None:
            continue
        matrix[rank], matrix[pivot] = matrix[pivot], matrix[rank]
        pivot_value = matrix[rank][column]
        matrix[rank] = [entry / pivot_value for entry in matrix[rank]]
        for index in range(row_count):
            if index == rank or not matrix[index][column]:
                continue
            factor = matrix[index][column]
            matrix[index] = [
                entry - factor * pivot_entry
                for entry, pivot_entry in zip(matrix[index], matrix[rank])
            ]
        rank += 1
        if rank == row_count:
            break
    return rank


def zonotope_vertices(
    edges: Sequence[tuple[int, int]], n: int = 11
) -> tuple[tuple[int, ...], ...]:
    vertices: set[tuple[int, ...]] = set()
    for choices in itertools.product((0, 1), repeat=len(edges)):
        point = [0] * n
        for edge, choice in zip(edges, choices):
            point[edge[choice]] += 1
        vertices.add(tuple(point))
    return tuple(sorted(vertices))


def direct_vertex_affine_dimension(row: dict[str, object], n: int = 11) -> int:
    negative = tuple(tuple(map(int, edge)) for edge in row["negative_edges"])
    positive = tuple(tuple(map(int, edge)) for edge in row["positive_edges"])
    vertices = zonotope_vertices(negative, n) + zonotope_vertices(positive, n)
    origin = vertices[0]
    return exact_rank(
        tuple(entry - base for entry, base in zip(vertex, origin))
        for vertex in vertices[1:]
    )


def exhaustive_small_formula_control() -> dict[str, object]:
    """Check the dimension formula on every active disjoint 2+2 atom at n=4."""

    n, degree = 4, 2
    edge_types = tuple((left, right) for left in range(n) for right in range(left, n))
    histogram: Counter[tuple[int, bool, int]] = Counter()
    tested = 0
    for negative in itertools.combinations_with_replacement(edge_types, degree):
        for positive in itertools.combinations_with_replacement(edge_types, degree):
            if set(negative) & set(positive):
                continue
            active = {vertex for edge in negative + positive for vertex in edge}
            if active != set(range(n)):
                continue
            blocks, component_of = components(negative + positive, n)
            negative_mass = branch_mass(negative, component_of, len(blocks))
            positive_mass = branch_mass(positive, component_of, len(blocks))
            delta = tuple(p - q for p, q in zip(positive_mass, negative_mass))
            predicted = n - len(blocks) + int(any(delta))
            row = {
                "negative_edges": [list(edge) for edge in negative],
                "positive_edges": [list(edge) for edge in positive],
            }
            direct = direct_vertex_affine_dimension(row, n)
            if direct != predicted:
                raise FilterError(
                    "exhaustive n=4 formula control failed: "
                    f"negative={negative}, positive={positive}, "
                    f"predicted={predicted}, direct={direct}"
                )
            histogram[(len(blocks), any(delta), direct)] += 1
            tested += 1
    if tested == 0:
        raise FilterError("exhaustive n=4 control tested no active atoms")
    return {
        "n": n,
        "branch_degree": degree,
        "active_disjoint_atoms_tested": tested,
        "histogram": {
            f"components={component_count},delta_nonzero={str(delta_nonzero).lower()},dimension={dimension}": count
            for (component_count, delta_nonzero, dimension), count in sorted(
                histogram.items()
            )
        },
    }


def cross_component_sign_swap(row: dict[str, object]) -> dict[str, object]:
    """Turn a balanced two-component signing into an imbalanced one."""

    audited = classify(row)
    if audited["component_count"] != 2 or any(audited["component_imbalance"]):
        raise FilterError("mutation seed is not a balanced two-component atom")
    component_of = {}
    for index, block in enumerate(audited["components"]):
        for vertex in block:
            component_of[int(vertex)] = index
    negative = [tuple(map(int, edge)) for edge in row["negative_edges"]]
    positive = [tuple(map(int, edge)) for edge in row["positive_edges"]]
    negative_index = next(
        index for index, edge in enumerate(negative) if component_of[edge[0]] == 0
    )
    positive_index = next(
        index for index, edge in enumerate(positive) if component_of[edge[0]] == 1
    )
    negative_edge, positive_edge = negative[negative_index], positive[positive_index]
    negative[negative_index], positive[positive_index] = positive_edge, negative_edge
    mutant = dict(row)
    mutant["negative_edges"] = [list(edge) for edge in sorted(negative)]
    mutant["positive_edges"] = [list(edge) for edge in sorted(positive)]
    mutant["negative_loop_count"] = sum(left == right for left, right in negative)
    mutant["positive_loop_count"] = sum(left == right for left, right in positive)
    return mutant


def key_for_count(audit: dict[str, object], row: dict[str, object]) -> tuple[object, ...]:
    return (
        int(audit["component_count"]),
        int(row["abs_beta"]),
        int(row["negative_loop_count"]),
        int(row["positive_loop_count"]),
        bool(audit["full_dimensional"]),
    )


def scan(stream: Path, manifest: Path) -> dict[str, object]:
    started = time.monotonic()
    compressed_hash = sha256_path(stream)
    if compressed_hash != EXPECTED_COMPRESSED_SHA256:
        raise FilterError("frozen G-0038 compressed stream hash drifted")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    if manifest_data["stream"]["compressed_sha256"] != compressed_hash:
        raise FilterError("manifest/stream compressed hash mismatch")
    target_manifest = next(
        row
        for row in manifest_data["stream"]["strata"]
        if row["signed_mass"] == 5 and row["active_vertices"] == 11
    )
    if (
        target_manifest["record_count"] != EXPECTED_TARGET_COUNT
        or target_manifest["canonical_jsonl_sha256"]
        != EXPECTED_TARGET_JSONL_SHA256
    ):
        raise FilterError("target stratum manifest drifted")

    counts: Counter[tuple[object, ...]] = Counter()
    examples: dict[str, dict[str, object]] = {}
    target_digest = hashlib.sha256()
    target_count = 0
    with gzip.open(stream, "rb") as handle:
        for raw in handle:
            if (
                b'"record_type":"orbit"' not in raw
                or b'"active_vertices":11' not in raw
                or b'"signed_mass":5' not in raw
            ):
                continue
            target_digest.update(raw)
            row = json.loads(raw)
            target_count += 1
            audit = classify(row)
            counts[key_for_count(audit, row)] += 1
            category = (
                "connected_full"
                if audit["component_count"] == 1
                else "two_component_full"
                if audit["component_count"] == 2 and audit["full_dimensional"]
                else "two_component_balanced"
                if audit["component_count"] == 2
                else "three_component_nonfull"
                if audit["component_count"] == 3
                else "other_nonfull"
            )
            if category not in examples:
                examples[category] = {"record": row, "criterion": audit}

    if target_count != EXPECTED_TARGET_COUNT:
        raise FilterError(f"target count drifted: {target_count}")
    if target_digest.hexdigest() != EXPECTED_TARGET_JSONL_SHA256:
        raise FilterError("target canonical JSONL digest drifted")

    connected_full = sum(
        value for (component_count, _beta, _nl, _pl, full), value in counts.items()
        if component_count == 1 and full
    )
    two_component_full = sum(
        value for (component_count, _beta, _nl, _pl, full), value in counts.items()
        if component_count == 2 and full
    )
    two_component_balanced = sum(
        value for (component_count, _beta, _nl, _pl, full), value in counts.items()
        if component_count == 2 and not full
    )
    full_total = sum(
        value for (*_prefix, full), value in counts.items() if full
    )
    expected = (
        EXPECTED_CONNECTED_FULL,
        EXPECTED_TWO_COMPONENT_FULL,
        EXPECTED_TWO_COMPONENT_BALANCED,
        EXPECTED_FULL_TOTAL,
    )
    observed = (
        connected_full,
        two_component_full,
        two_component_balanced,
        full_total,
    )
    if observed != expected:
        raise FilterError(f"census drifted: observed={observed}, expected={expected}")

    direct_controls: dict[str, object] = {}
    for name in (
        "connected_full",
        "two_component_full",
        "two_component_balanced",
        "three_component_nonfull",
    ):
        example = examples[name]
        direct_dimension = direct_vertex_affine_dimension(example["record"])
        criterion_dimension = int(example["criterion"]["affine_dimension"])
        if direct_dimension != criterion_dimension:
            raise FilterError(f"direct vertex-rank control failed for {name}")
        direct_controls[name] = {
            "sequence": example["record"]["sequence"],
            "criterion_dimension": criterion_dimension,
            "direct_vertex_affine_dimension": direct_dimension,
            "component_imbalance": example["criterion"]["component_imbalance"],
        }

    balanced_seed = examples["two_component_balanced"]["record"]
    mutant = cross_component_sign_swap(balanced_seed)
    seed_audit, mutant_audit = classify(balanced_seed), classify(mutant)
    seed_rank = direct_vertex_affine_dimension(balanced_seed)
    mutant_rank = direct_vertex_affine_dimension(mutant)
    if not (
        seed_rank == 9
        and not seed_audit["full_dimensional"]
        and mutant_rank == 10
        and mutant_audit["full_dimensional"]
    ):
        raise FilterError("cross-component sign-swap mutation control failed")

    by_components_full = {
        str(component_count): sum(
            value
            for (count, _beta, _nl, _pl, full), value in counts.items()
            if count == component_count and full
        )
        for component_count in sorted({int(key[0]) for key in counts})
    }
    by_components_nonfull = {
        str(component_count): sum(
            value
            for (count, _beta, _nl, _pl, full), value in counts.items()
            if count == component_count and not full
        )
        for component_count in sorted({int(key[0]) for key in counts})
    }
    c2_by_loops = {
        f"negative={negative_loops},positive={positive_loops},full={str(full).lower()}": value
        for (
            component_count,
            _beta,
            negative_loops,
            positive_loops,
            full,
        ), value in sorted(counts.items())
        if component_count == 2
    }
    return {
        "schema": "max11-g0101-full-dimensional-degree5-census-v1",
        "result": "PASS",
        "theorem": {
            "dimension_formula": "n-c+1[delta!=0]",
            "delta_definition": (
                "positive branch edge-occurrence mass minus negative branch "
                "edge-occurrence mass on each union-graph component"
            ),
            "active_equal_degree_full_criterion": (
                "c=1, or c=2 and delta is nonzero"
            ),
        },
        "bindings": {
            "producer": str(Path(__file__).resolve().relative_to(ROOT)),
            "producer_sha256": sha256_path(Path(__file__).resolve()),
            "stream": str(stream.relative_to(ROOT)),
            "compressed_sha256": compressed_hash,
            "target_canonical_jsonl_sha256": target_digest.hexdigest(),
            "target_records": target_count,
            "python": sys.version,
            "platform": platform.platform(),
        },
        "census": {
            "active_signed_mass_five_total": target_count,
            "full_dimensional_total": full_total,
            "rank_deficient_total": target_count - full_total,
            "connected_full": connected_full,
            "two_component_full": two_component_full,
            "two_component_balanced_rank_deficient": two_component_balanced,
            "by_components_full": by_components_full,
            "by_components_nonfull": by_components_nonfull,
            "two_component_loop_histogram": c2_by_loops,
        },
        "controls": {
            "exhaustive_small_formula": exhaustive_small_formula_control(),
            "direct_exact_vertex_rank": direct_controls,
            "cross_component_sign_swap": {
                "seed_sequence": balanced_seed["sequence"],
                "seed_component_imbalance": seed_audit["component_imbalance"],
                "seed_exact_dimension": seed_rank,
                "mutant_component_imbalance": mutant_audit["component_imbalance"],
                "mutant_exact_dimension": mutant_rank,
                "same_unsigned_union": sorted(
                    balanced_seed["negative_edges"] + balanced_seed["positive_edges"]
                )
                == sorted(mutant["negative_edges"] + mutant["positive_edges"]),
            },
        },
        "claim_boundary": (
            "Exact affine-dimension theorem and census for the frozen active "
            "signed-mass-five graphical orbit universe only. Rank-deficient atoms "
            "may still be needed as correction terms. This is not semantic-span "
            "completeness, a MAX11 identity, or an unrestricted ReLU lower bound."
        ),
        "wall_seconds": time.monotonic() - started,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stream", type=Path, default=DEFAULT_STREAM)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    result = scan(args.stream.resolve(), args.manifest.resolve())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_suffix(args.output.suffix + ".tmp")
    temporary.write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    temporary.replace(args.output)
    print(json.dumps(result["census"], sort_keys=True))


if __name__ == "__main__":
    main()
