#!/usr/bin/env python3
"""Enumerate complete loopless signed-W degree-four universes.

This is the degree-four adaptation of G-0027.  Records retain G-0027's exact
six-field schema.  The producer reuses its nauty incidence enumeration and
automorphism traversal, and independently checks every graph-level orbit
count with Burnside's lemma on the induced action on valid sign masks.

Record zero is the zero signed graph.  Under colgen with branch size four it
is the 4E carrier: four common loopless edges, whose fully symmetrized column
has no hinge part.  The distinct 4L common-loop carrier is a pure linear
column and is deliberately not serialized as a loopless signed-W record.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0027_PATH = ROOT / "artifacts/math/G-0027/enumerate_signed_loopless.py"
BRANCH_EDGES = 4
SCHEMA = "max11-kwa-loopless-signed-degree4-universe-v1"
EXPECTED_TOTALS = {9: 16_311, 10: 17_775}


def load_g0027():
    spec = importlib.util.spec_from_file_location("kwa_g0027_enumerator", G0027_PATH)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {G0027_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


G = load_g0027()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_records(records: Iterable[object]) -> str:
    digest = hashlib.sha256()
    for record in records:
        digest.update(canonical_bytes(record))
    return digest.hexdigest()


def write_gzip_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            compressed.write(raw)
    print(
        f"WROTE {path} raw_bytes={len(raw)} compressed_bytes={path.stat().st_size} "
        f"sha256={sha256_path(path)}",
        flush=True,
    )


def compose(left: Sequence[int], right: Sequence[int]) -> tuple[int, ...]:
    return tuple(left[right[index]] for index in range(len(right)))


def induced_action_group(
    masks: Sequence[int], generators: Sequence[Sequence[int]], occurrence_count: int
) -> set[tuple[int, ...]]:
    ordered = tuple(sorted(map(int, masks)))
    position = {mask: index for index, mask in enumerate(ordered)}
    full = (1 << occurrence_count) - 1
    actions = [
        tuple(position[G.permute_mask(mask, generator)] for mask in ordered)
        for generator in generators
    ]
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
) -> int:
    if not masks:
        return 0
    group = induced_action_group(masks, generators, occurrence_count)
    fixed_sum = sum(
        sum(index == image for index, image in enumerate(transformation))
        for transformation in group
    )
    if fixed_sum % len(group):
        raise AssertionError("Burnside fixed-point sum is not divisible by group order")
    return fixed_sum // len(group)


def zero_record() -> dict[str, object]:
    return {
        "active_vertices": 0,
        "signed_mass": 0,
        "negative_edges": [],
        "positive_edges": [],
        "abs_components": 0,
        "abs_beta": 0,
    }


def run_controls(total_orbits: int, n: int) -> dict[str, object]:
    masks = [0b0011, 0b0101, 0b1010, 0b1100]
    generators = [(2, 3, 0, 1)]
    traversal = len(G.mask_orbits(masks, generators, 4))
    burnside = burnside_orbit_count(masks, generators, 4)
    if traversal != 2 or burnside != traversal:
        raise AssertionError("synthetic orbit/Burnside control failed")
    if G.valid_balanced_masks([(0, 1), (0, 1)], 1):
        raise AssertionError("opposite twin occurrences did not cancel")
    expected = EXPECTED_TOTALS.get(n)
    if expected is not None and total_orbits != expected:
        raise AssertionError(f"n={n} orbit control failed: {total_orbits} != {expected}")
    return {
        "result": "PASS",
        "synthetic_orbit_count": traversal,
        "synthetic_burnside_orbit_count": burnside,
        "opposite_twins_cancel_to_lower_stratum": True,
        "known_total_orbits": expected,
        "known_total_matches": None if expected is None else total_orbits == expected,
    }


def enumerate_universe(n: int) -> dict[str, object]:
    if not 2 <= n <= 16:
        raise ValueError("n must lie in 2..=16")
    begun = time.monotonic()
    records = [zero_record()]
    strata: list[dict[str, object]] = [
        {
            "signed_mass": 0,
            "active_vertices": 0,
            "uncoloured_abs_graphs": 1,
            "signed_graph_orbits": 1,
            "burnside_orbits": 1,
        }
    ]
    topology_counts: Counter[tuple[int, int, int, int]] = Counter()
    total_abs = 1
    total_orbits = 1

    for signed_mass in range(1, BRANCH_EDGES + 1):
        occurrence_count = 2 * signed_mass
        for active_vertices in range(2, min(n, 4 * signed_mass) + 1):
            abs_count = 0
            orbit_count = 0
            burnside_count = 0
            for graph in G.genbg_graphs(active_vertices, signed_mass):
                abs_count += 1
                neighbourhoods = G.occurrence_neighbourhoods(graph, active_vertices)
                masks = G.valid_balanced_masks(neighbourhoods, signed_mass)
                if not masks:
                    continue
                generators = G.automorphism_generators(graph, active_vertices)
                representatives = G.mask_orbits(masks, generators, occurrence_count)
                burnside = burnside_orbit_count(masks, generators, occurrence_count)
                if burnside != len(representatives):
                    raise AssertionError(
                        f"orbit/Burnside mismatch at s={signed_mass}, r={active_vertices}: "
                        f"{len(representatives)} != {burnside}"
                    )
                orbit_count += len(representatives)
                burnside_count += burnside
                components = G.connected_components_of_edges(neighbourhoods, active_vertices)
                beta_abs = 2 * signed_mass - active_vertices + components
                topology_counts[(signed_mass, active_vertices, components, beta_abs)] += len(
                    representatives
                )
                records.extend(
                    G.signed_record(active_vertices, signed_mass, neighbourhoods, positive_mask)
                    for positive_mask in representatives
                )
            if abs_count or orbit_count:
                print(
                    f"KWA n={n} k=4 s={signed_mass} r={active_vertices} "
                    f"abs={abs_count} traversal={orbit_count} burnside={burnside_count}",
                    flush=True,
                )
                strata.append(
                    {
                        "signed_mass": signed_mass,
                        "active_vertices": active_vertices,
                        "uncoloured_abs_graphs": abs_count,
                        "signed_graph_orbits": orbit_count,
                        "burnside_orbits": burnside_count,
                    }
                )
                total_abs += abs_count
                total_orbits += orbit_count

    if len(records) != total_orbits:
        raise AssertionError("record/orbit census mismatch")
    return {
        "schema": SCHEMA,
        "result": "PASS",
        "n": n,
        "branch_edge_occurrences": BRANCH_EDGES,
        "loopless": True,
        "quotient": "coordinate relabeling and global branch/sign reversal",
        "function_collapse": (
            "common edge occurrences cancel from W=B-A; for fixed branch size four, "
            "the fully symmetrized atom depends only on W"
        ),
        "carrier_record_zero": "4E: four common loopless edges",
        "external_linear_carrier": "4L: four common loops; not a loopless signed-W record",
        "census": {
            "uncoloured_abs_multigraphs": total_abs,
            "signed_graph_orbits": total_orbits,
            "strata": strata,
        },
        "records_included": True,
        "records_sha256": sha256_records(records),
        "records": records,
        "topology_histogram": [
            {
                "signed_mass": mass,
                "active_vertices": vertices,
                "abs_components": components,
                "abs_beta": beta,
                "signed_graph_orbits": count,
            }
            for (mass, vertices, components, beta), count in sorted(topology_counts.items())
        ],
        "controls": run_controls(total_orbits, n),
        "toolchain": {
            "python": sys.version,
            "networkx": G.nx.__version__,
            "pynauty": G.pynauty.__version__,
            "genbg": G.locate_program("genbg"),
        },
        "g0027_source": str(G0027_PATH.relative_to(ROOT)),
        "g0027_source_sha256": sha256_path(G0027_PATH),
        "script_sha256": sha256_path(Path(__file__).resolve()),
        "wall_seconds": time.monotonic() - begun,
        "claim_boundary": (
            "Finite exhaustive signed-graph quotient covering loopless degree-four pair atoms "
            "at the named n. Different signed-graph orbits are not asserted to define distinct "
            "functions. No span, characteristic-zero identity, network completeness, or "
            "unrestricted MAX11 claim."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    write_gzip_json(args.output, enumerate_universe(args.n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
