#!/usr/bin/env python3
"""Enumerate complete loopless signed-W degree-k universes for small n.

The canonical quotient is deliberately inherited from G-0027: nauty enumerates
uncoloured incidence multigraphs, pynauty supplies automorphism generators, and
balanced twin-monochromatic signings are quotiented by automorphisms and global
sign reversal.  This script adds an independent orbit-count calculation using
Burnside's lemma on the induced action on valid sign masks.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict, deque
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
G0027_PATH = ROOT / "artifacts/math/G-0027/enumerate_signed_loopless.py"
SCHEMA = "max11-gmp9-loopless-signed-degree-k-universe-v1"
EXPECTED_SIMPLE = {9: 6_197, 10: 7_203}


def load_g0027():
    spec = importlib.util.spec_from_file_location("g0027_enumerator", G0027_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {G0027_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


G = load_g0027()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_records(records: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_bytes(record))
    return digest.hexdigest()


def write_gzip_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical_bytes(value)
    with path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            compressed.write(raw)
    print(
        f"WROTE {path} raw_bytes={len(raw)} compressed_bytes={path.stat().st_size} "
        f"sha256={sha256_path(path)}",
        flush=True,
    )


def compose(left: Sequence[int], right: Sequence[int]) -> tuple[int, ...]:
    """Return left after right for transformations represented by image tuples."""

    return tuple(left[right[index]] for index in range(len(right)))


def induced_action_group(
    masks: Sequence[int], generators: Sequence[Sequence[int]], occurrence_count: int
) -> set[tuple[int, ...]]:
    """Close Aut(|W|) x C2 on the finite set of valid sign masks."""

    ordered = tuple(sorted(map(int, masks)))
    position = {mask: index for index, mask in enumerate(ordered)}
    full = (1 << occurrence_count) - 1
    actions: list[tuple[int, ...]] = []
    for generator in generators:
        actions.append(tuple(position[G.permute_mask(mask, generator)] for mask in ordered))
    actions.append(tuple(position[full ^ mask] for mask in ordered))
    identity = tuple(range(len(ordered)))
    group = {identity}
    queue = deque([identity])
    while queue:
        current = queue.popleft()
        for generator in actions:
            image = compose(generator, current)
            if image not in group:
                group.add(image)
                queue.append(image)
    return group


def burnside_orbit_count(
    masks: Sequence[int], generators: Sequence[Sequence[int]], occurrence_count: int
) -> tuple[int, int, int]:
    """Return (orbits, fixed-point numerator, induced-group denominator)."""

    if not masks:
        return 0, 0, 1
    group = induced_action_group(masks, generators, occurrence_count)
    fixed_sum = sum(
        sum(index == image for index, image in enumerate(transformation))
        for transformation in group
    )
    if fixed_sum % len(group):
        raise AssertionError("Burnside fixed-point sum is not divisible by group order")
    return fixed_sum // len(group), fixed_sum, len(group)


def record_with_stats(
    active_vertices: int,
    signed_mass: int,
    neighbourhoods: Sequence[tuple[int, int]],
    positive_mask: int,
) -> dict[str, object]:
    record = G.signed_record(
        active_vertices, signed_mass, neighbourhoods, positive_mask
    )
    multiplicities = Counter(tuple(edge) for edge in record["negative_edges"])
    multiplicities.update(tuple(edge) for edge in record["positive_edges"])
    record["max_multiplicity"] = max(multiplicities.values(), default=0)
    record["negative_edges"] = sorted(record["negative_edges"])
    record["positive_edges"] = sorted(record["positive_edges"])
    return record


def run_synthetic_controls() -> dict[str, object]:
    masks = [0b0011, 0b0101, 0b1010, 0b1100]
    generators = [(2, 3, 0, 1)]
    traversed = len(G.mask_orbits(masks, generators, 4))
    burnside, numerator, denominator = burnside_orbit_count(masks, generators, 4)
    if traversed != 2 or burnside != traversed:
        raise AssertionError("synthetic orbit/Burnside control failed")

    twins = [(0, 1), (0, 1)]
    if G.valid_balanced_masks(twins, 1):
        raise AssertionError("opposite twin occurrences were not cancelled")
    return {
        "synthetic_orbit_count": traversed,
        "synthetic_burnside_fixed_point_numerator": numerator,
        "synthetic_burnside_group_order_denominator": denominator,
        "opposite_twins_cancel_to_lower_mass": True,
    }


def enumerate_universe(n: int, branch_edges: int) -> dict[str, object]:
    begun = time.monotonic()
    zero = {
        "active_vertices": 0,
        "signed_mass": 0,
        "negative_edges": [],
        "positive_edges": [],
        "abs_components": 0,
        "abs_beta": 0,
        "max_multiplicity": 0,
    }
    records: list[dict[str, object]] = [zero]
    strata: list[dict[str, object]] = [
        {
            "signed_mass": 0,
            "active_vertices": 0,
            "uncoloured_abs_graphs": 1,
            "traversal_orbits": 1,
            "burnside_orbits": 1,
        }
    ]
    total_abs = 1
    total_traversal = 1
    total_burnside = 1
    graphs_with_valid_signings = 0
    burnside_fixed_sum_total = 1
    burnside_group_order_sum = 1
    multiplicity_counts: Counter[int] = Counter({0: 1})
    topology_counts: Counter[tuple[int, int, int, int, int]] = Counter()

    for signed_mass in range(1, branch_edges + 1):
        occurrence_count = 2 * signed_mass
        for active_vertices in range(2, min(n, 4 * signed_mass) + 1):
            abs_count = 0
            traversal_count = 0
            burnside_count = 0
            for graph in G.genbg_graphs(active_vertices, signed_mass):
                abs_count += 1
                neighbourhoods = G.occurrence_neighbourhoods(graph, active_vertices)
                masks = G.valid_balanced_masks(neighbourhoods, signed_mass)
                if not masks:
                    continue
                generators = G.automorphism_generators(graph, active_vertices)
                representatives = G.mask_orbits(masks, generators, occurrence_count)
                burnside, fixed_numerator, group_denominator = burnside_orbit_count(
                    masks, generators, occurrence_count
                )
                if burnside != len(representatives):
                    raise AssertionError(
                        f"orbit/Burnside mismatch at s={signed_mass}, r={active_vertices}: "
                        f"{len(representatives)} != {burnside}"
                    )
                graphs_with_valid_signings += 1
                burnside_fixed_sum_total += fixed_numerator
                burnside_group_order_sum += group_denominator
                traversal_count += len(representatives)
                burnside_count += burnside
                for positive_mask in representatives:
                    record = record_with_stats(
                        active_vertices, signed_mass, neighbourhoods, positive_mask
                    )
                    records.append(record)
                    maximum = int(record["max_multiplicity"])
                    multiplicity_counts[maximum] += 1
                    topology_counts[
                        (
                            signed_mass,
                            active_vertices,
                            int(record["abs_components"]),
                            int(record["abs_beta"]),
                            maximum,
                        )
                    ] += 1
            if abs_count or traversal_count:
                print(
                    f"GMP9 n={n} k={branch_edges} s={signed_mass} r={active_vertices} "
                    f"abs={abs_count} traversal={traversal_count} burnside={burnside_count}",
                    flush=True,
                )
                strata.append(
                    {
                        "signed_mass": signed_mass,
                        "active_vertices": active_vertices,
                        "uncoloured_abs_graphs": abs_count,
                        "traversal_orbits": traversal_count,
                        "burnside_orbits": burnside_count,
                    }
                )
                total_abs += abs_count
                total_traversal += traversal_count
                total_burnside += burnside_count

    if total_traversal != len(records) or total_burnside != total_traversal:
        raise AssertionError("universe census did not reconcile")
    simple_count = sum(count for maximum, count in multiplicity_counts.items() if maximum <= 1)
    expected_simple = EXPECTED_SIMPLE.get(n) if branch_edges == 4 else None
    if expected_simple is not None and simple_count != expected_simple:
        raise AssertionError(
            f"n={n} simple-W known answer failed: {simple_count} != {expected_simple}"
        )
    synthetic = run_synthetic_controls()
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "n": n,
        "branch_edge_occurrences": branch_edges,
        "loopless": True,
        "quotient": "coordinate relabeling and global branch/sign reversal",
        "records": records,
        "records_sha256": sha256_records(records),
        "census": {
            "uncoloured_abs_multigraphs": total_abs,
            "signed_graph_orbits": total_traversal,
            "strata": strata,
            "max_multiplicity_counts": dict(sorted(multiplicity_counts.items())),
            "simple_w_max_multiplicity_leq_one": simple_count,
            "topology_histogram": [
                {
                    "signed_mass": s,
                    "active_vertices": r,
                    "abs_components": components,
                    "abs_beta": beta,
                    "max_multiplicity": maximum,
                    "signed_graph_orbits": count,
                }
                for (s, r, components, beta, maximum), count in sorted(topology_counts.items())
            ],
        },
        "controls": {
            **synthetic,
            "orbit_traversal_equals_burnside_for_every_absolute_graph": True,
            "graphs_with_valid_signings_denominator": graphs_with_valid_signings,
            "aggregate_burnside_fixed_point_numerator": burnside_fixed_sum_total,
            "aggregate_induced_group_order_denominator": burnside_group_order_sum,
            "simple_w_expected": expected_simple,
            "simple_w_observed": simple_count,
            "simple_w_known_answer_pass": expected_simple is None or simple_count == expected_simple,
        },
        "producer": {
            "script_sha256": sha256_path(Path(__file__).resolve()),
            "g0027_source": str(G0027_PATH.relative_to(ROOT)),
            "g0027_source_sha256": sha256_path(G0027_PATH),
            "python": sys.version,
        },
        "wall_seconds": time.monotonic() - begun,
        "no_claim": (
            "This is a finite signed-graph orbit census for loopless degree-k pair atoms. "
            "It does not assert distinct functions, a span rank, MAX membership, or anything at n=11."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--branch-edges", type=int, default=4)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 2 <= args.n <= 16:
        raise ValueError("n must lie in 2..16")
    if not 0 <= args.branch_edges <= 5:
        raise ValueError("this campaign tool supports branch degree 0..5")
    report = enumerate_universe(args.n, args.branch_edges)
    write_gzip_json(args.output, report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
