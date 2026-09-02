#!/usr/bin/env python3
"""Enumerate loopless signed-W degree-k orbits for a parameterized arity.

The orbit engine is the frozen G-0027 incidence-graph implementation: nauty
enumerates absolute multigraphs, pynauty supplies their automorphisms, valid
balanced twin-monochromatic signings are quotiented by those automorphisms and
global sign reversal. Records retain exactly the six mathematical fields used
by G-0027. Census metadata adds marginal and joint topology counts.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import io
import json
import math
from pathlib import Path
import sys
import time
from typing import Iterator


ROOT = Path(__file__).resolve().parents[3]
G0027_PATH = ROOT / "artifacts/math/G-0027/enumerate_signed_loopless.py"
G0027_UNIVERSE = ROOT / "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
SCHEMA = "relu-depth-frontier-gmp15-loopless-signed-degree-k-universe-v1"
EXPECTED_G0027_RECORDS = 754_017
EXPECTED_G0027_RECORDS_SHA256 = (
    "5fc1b608612ca4668e772a9234a8795f12f17a746392ffdf492e8888548cc541"
)
EXPECTED_G0027_FILE_SHA256 = (
    "8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8"
)
EXPECTED_SIMPLE_PAIR_ORBITS = {(5, 2): 19, (6, 2): 25, (11, 5): 462_627, (12, 5): 490_480}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


G = load_module(G0027_PATH, "gmp15_g0027_enumerator")


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_gzip_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                json.dump(value, text, sort_keys=True, separators=(",", ":"))
                text.write("\n")


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def partitions(n: int, minimum: int = 1) -> Iterator[tuple[int, ...]]:
    yield (n,)
    for first in range(minimum, n // 2 + 1):
        for rest in partitions(n - first, first):
            yield (first, *rest)


def cycle_type_count(partition: tuple[int, ...], n: int) -> int:
    counts = Counter(partition)
    denominator = math.prod(
        length**multiplicity * math.factorial(multiplicity)
        for length, multiplicity in counts.items()
    )
    return math.factorial(n) // denominator


def edge_orbit_lengths(partition: tuple[int, ...]) -> list[int]:
    cycles: list[list[int]] = []
    cursor = 0
    for length in partition:
        cycles.append(list(range(cursor, cursor + length)))
        cursor += length
    permutation = [0] * cursor
    for cycle in cycles:
        for index, vertex in enumerate(cycle):
            permutation[vertex] = cycle[(index + 1) % len(cycle)]
    unseen = {(left, right) for left in range(cursor) for right in range(left + 1, cursor)}
    lengths: list[int] = []
    while unseen:
        start = min(unseen)
        current = start
        length = 0
        while current in unseen:
            unseen.remove(current)
            length += 1
            left, right = permutation[current[0]], permutation[current[1]]
            current = (min(left, right), max(left, right))
        if current != start:
            raise AssertionError("edge action did not close at its start")
        lengths.append(length)
    return lengths


def fixed_simple_graph_count(orbit_lengths: list[int], edges: int) -> int:
    coefficients = [1] + [0] * edges
    for length in orbit_lengths:
        for degree in range(edges, length - 1, -1):
            coefficients[degree] += coefficients[degree - length]
    return coefficients[edges]


def squared_cycle_type(partition: tuple[int, ...]) -> tuple[int, ...]:
    result: list[int] = []
    for length in partition:
        if length % 2 == 0:
            result.extend((length // 2, length // 2))
        else:
            result.append(length)
    return tuple(sorted(result, reverse=True))


def simple_pair_burnside(n: int, edges: int) -> dict[str, int]:
    fixed_without_swap = 0
    fixed_with_swap = 0
    for partition in partitions(n):
        multiplicity = cycle_type_count(partition, n)
        fixed = fixed_simple_graph_count(edge_orbit_lengths(partition), edges)
        fixed_without_swap += multiplicity * fixed * fixed
        fixed_squared = fixed_simple_graph_count(
            edge_orbit_lengths(squared_cycle_type(partition)), edges
        )
        fixed_with_swap += multiplicity * fixed_squared
    denominator = 2 * math.factorial(n)
    numerator = fixed_without_swap + fixed_with_swap
    if numerator % denominator:
        raise AssertionError("Burnside numerator is not divisible by group order")
    return {
        "orbits": numerator // denominator,
        "burnside_numerator": numerator,
        "fixed_without_swap_numerator": fixed_without_swap,
        "swap_coset_numerator": fixed_with_swap,
        "group_order_denominator": denominator,
    }


def maximum_multiplicity(record: dict[str, object]) -> int:
    counts = Counter(
        tuple(edge)
        for edge in list(record["negative_edges"]) + list(record["positive_edges"])
    )
    return max(counts.values(), default=0)


def record_signature(record: dict[str, object]) -> tuple[object, ...]:
    negative = tuple(sorted(tuple(edge) for edge in record["negative_edges"]))
    positive = tuple(sorted(tuple(edge) for edge in record["positive_edges"]))
    first, second = min((negative, positive), (positive, negative))
    return (
        int(record["active_vertices"]),
        int(record["signed_mass"]),
        first,
        second,
        int(record["abs_components"]),
        int(record["abs_beta"]),
    )


def duplicate_control(records: list[dict[str, object]]) -> dict[str, object]:
    def require_unique(subject: list[dict[str, object]]) -> None:
        seen: set[tuple[object, ...]] = set()
        for index, record in enumerate(subject):
            signature = record_signature(record)
            if signature in seen:
                raise AssertionError(f"duplicate serialized representative at index {index}")
            seen.add(signature)

    require_unique(records)
    mutant = records + [records[1]]
    try:
        require_unique(mutant)
    except AssertionError:
        rejected = True
    else:
        raise AssertionError("planted duplicate survived")
    return {
        "serialized_representatives_unique": len(records),
        "serialized_representative_denominator": len(records),
        "planted_exact_duplicate_rejected": rejected,
        "planted_exact_duplicate_denominator": 1,
    }


def reference_reproduction(
    n: int,
    branch_edges: int,
    records_sha256: str,
    strata: list[dict[str, object]],
    topology_histogram: list[dict[str, object]],
    reference: Path | None,
) -> dict[str, object] | None:
    if reference is None:
        return None
    if n != 11 or branch_edges != 5:
        raise ValueError("the frozen G-0027 reference applies only to n=11,k=5")
    reference_hash = sha256_path(reference)
    if reference_hash != EXPECTED_G0027_FILE_SHA256:
        raise AssertionError("frozen G-0027 file hash mismatch")
    with gzip.open(reference, "rt", encoding="utf-8") as handle:
        document = json.load(handle)
    checks = {
        "record_count": len(document["records"]) == EXPECTED_G0027_RECORDS,
        "records_sha256": records_sha256
        == document["records_sha256"]
        == EXPECTED_G0027_RECORDS_SHA256,
        "strata": strata == document["census"]["strata"],
        "topology_histogram": topology_histogram == document["topology_histogram"],
    }
    if not all(checks.values()):
        raise AssertionError(f"n=11 G-0027 reproduction failed: {checks}")
    return {
        "reference": str(reference.relative_to(ROOT)),
        "reference_sha256": reference_hash,
        "records_reproduced": EXPECTED_G0027_RECORDS,
        "record_denominator": EXPECTED_G0027_RECORDS,
        "records_sha256": records_sha256,
        "strata_reproduced": len(strata),
        "strata_denominator": len(document["census"]["strata"]),
        "topology_rows_reproduced": len(topology_histogram),
        "topology_row_denominator": len(document["topology_histogram"]),
        "checks": checks,
    }


def enumerate_universe(n: int, branch_edges: int, reference: Path | None) -> dict[str, object]:
    started = time.monotonic()
    zero = {
        "active_vertices": 0,
        "signed_mass": 0,
        "negative_edges": [],
        "positive_edges": [],
        "abs_components": 0,
        "abs_beta": 0,
    }
    records = [zero]
    records_digest = hashlib.sha256(canonical_bytes(zero))
    strata: list[dict[str, object]] = [
        {
            "signed_mass": 0,
            "active_vertices": 0,
            "uncoloured_abs_graphs": 1,
            "signed_graph_orbits": 1,
        }
    ]
    total_absolute = 1
    total_orbits = 1
    signed_mass_counts: Counter[int] = Counter({0: 1})
    beta_counts: Counter[int] = Counter({0: 1})
    component_counts: Counter[int] = Counter({0: 1})
    multiplicity_counts: Counter[int] = Counter({0: 1})
    topology: Counter[tuple[int, int, int, int]] = Counter()
    topology_with_multiplicity: Counter[tuple[int, int, int, int, int]] = Counter()
    absolute_graphs_with_valid_signings = 0

    for signed_mass in range(1, branch_edges + 1):
        occurrence_count = 2 * signed_mass
        for active_vertices in range(2, min(n, 4 * signed_mass) + 1):
            absolute_count = 0
            orbit_count = 0
            for graph in G.genbg_graphs(active_vertices, signed_mass):
                absolute_count += 1
                neighbourhoods = G.occurrence_neighbourhoods(graph, active_vertices)
                masks = G.valid_balanced_masks(neighbourhoods, signed_mass)
                if not masks:
                    continue
                absolute_graphs_with_valid_signings += 1
                representatives = G.mask_orbits(
                    masks,
                    G.automorphism_generators(graph, active_vertices),
                    occurrence_count,
                )
                orbit_count += len(representatives)
                for positive_mask in representatives:
                    record = G.signed_record(
                        active_vertices,
                        signed_mass,
                        neighbourhoods,
                        positive_mask,
                    )
                    records.append(record)
                    records_digest.update(canonical_bytes(record))
                    maximum = maximum_multiplicity(record)
                    components = int(record["abs_components"])
                    beta = int(record["abs_beta"])
                    signed_mass_counts[signed_mass] += 1
                    beta_counts[beta] += 1
                    component_counts[components] += 1
                    multiplicity_counts[maximum] += 1
                    topology[(signed_mass, active_vertices, components, beta)] += 1
                    topology_with_multiplicity[
                        (signed_mass, active_vertices, components, beta, maximum)
                    ] += 1
            if absolute_count or orbit_count:
                print(
                    f"GMP15 n={n} k={branch_edges} s={signed_mass} r={active_vertices} "
                    f"abs={absolute_count} signed={orbit_count}",
                    flush=True,
                )
                strata.append(
                    {
                        "signed_mass": signed_mass,
                        "active_vertices": active_vertices,
                        "uncoloured_abs_graphs": absolute_count,
                        "signed_graph_orbits": orbit_count,
                    }
                )
                total_absolute += absolute_count
                total_orbits += orbit_count

    if len(records) != total_orbits or sum(signed_mass_counts.values()) != total_orbits:
        raise AssertionError("orbit and record denominators do not reconcile")
    direct_mass = Counter(int(record["signed_mass"]) for record in records)
    if direct_mass != signed_mass_counts:
        raise AssertionError("direct signed-mass recount differs from enumeration counters")
    records_sha256 = records_digest.hexdigest()
    topology_histogram = [
        {
            "signed_mass": signed_mass,
            "active_vertices": active_vertices,
            "abs_components": components,
            "abs_beta": beta,
            "signed_graph_orbits": count,
        }
        for (signed_mass, active_vertices, components, beta), count in sorted(topology.items())
    ]
    joint_histogram = [
        {
            "signed_mass": signed_mass,
            "active_vertices": active_vertices,
            "abs_components": components,
            "abs_beta": beta,
            "max_multiplicity": maximum,
            "signed_graph_orbits": count,
        }
        for (
            signed_mass,
            active_vertices,
            components,
            beta,
            maximum,
        ), count in sorted(topology_with_multiplicity.items())
    ]

    reproduction = reference_reproduction(
        n,
        branch_edges,
        records_sha256,
        strata,
        topology_histogram,
        reference,
    )
    duplicate = duplicate_control(records)
    full_support_tree_count = sum(
        count
        for (mass, active, components, beta, _maximum), count in topology_with_multiplicity.items()
        if (mass, active, components, beta) == (5, 11, 1, 0)
    )
    g0027_controls = G.run_controls(full_support_tree_count=full_support_tree_count)
    burnside_controls = {}
    for subject in ((5, 2), (6, 2), (n, branch_edges)):
        if subject in burnside_controls:
            continue
        result = simple_pair_burnside(*subject)
        expected = EXPECTED_SIMPLE_PAIR_ORBITS.get(subject)
        if expected is not None and result["orbits"] != expected:
            raise AssertionError(f"simple-pair Burnside known answer failed for {subject}")
        burnside_controls[f"n{subject[0]}_k{subject[1]}"] = {
            **result,
            "expected_orbits": expected,
            "known_answer_pass": expected is None or result["orbits"] == expected,
        }

    simple_w_count = multiplicity_counts[0] + multiplicity_counts[1]
    raw_simple_pair_count = burnside_controls[f"n{n}_k{branch_edges}"]["orbits"]
    if any(
        maximum_multiplicity(record) <= 1
        and math.comb(n, 2) - 2 * int(record["signed_mass"])
        < branch_edges - int(record["signed_mass"])
        for record in records
    ):
        raise AssertionError("a simple W record lacks enough unused common edges")
    if raw_simple_pair_count < simple_w_count:
        raise AssertionError("surjective raw-pair/W relation has reversed cardinalities")
    no_swap_orbits_numerator = burnside_controls[f"n{n}_k{branch_edges}"][
        "fixed_without_swap_numerator"
    ]
    no_swap_orbits = no_swap_orbits_numerator // math.factorial(n)
    if no_swap_orbits == raw_simple_pair_count:
        raise AssertionError("omitting the branch-swap coset did not change the control")

    return {
        "schema": SCHEMA,
        "result": "PASS",
        "n": n,
        "branch_edge_occurrences": branch_edges,
        "loopless": True,
        "quotient": "coordinate relabeling and global branch/sign reversal",
        "record_schema": [
            "active_vertices",
            "signed_mass",
            "negative_edges",
            "positive_edges",
            "abs_components",
            "abs_beta",
        ],
        "function_collapse": (
            "common edge occurrences cancel from W=B-A; for fixed branch size, "
            "the fully symmetrised atom depends only on W"
        ),
        "records_included": True,
        "records_sha256": records_sha256,
        "records": records,
        "census": {
            "uncoloured_abs_multigraphs": total_absolute,
            "absolute_graphs_with_valid_signings": absolute_graphs_with_valid_signings,
            "signed_graph_orbits": total_orbits,
            "strata": strata,
            "counts_by_signed_mass": dict(sorted(signed_mass_counts.items())),
            "counts_by_abs_beta": dict(sorted(beta_counts.items())),
            "counts_by_abs_components": dict(sorted(component_counts.items())),
            "counts_by_max_multiplicity": dict(sorted(multiplicity_counts.items())),
            "simple_w_max_multiplicity_leq_one": simple_w_count,
            "topology_histogram": topology_histogram,
            "topology_multiplicity_histogram": joint_histogram,
        },
        "controls": {
            **duplicate,
            "direct_signed_mass_recount": dict(sorted(direct_mass.items())),
            "direct_signed_mass_recount_denominator": len(records),
            "g0027_small_controls": g0027_controls,
            "g0027_n11_reproduction": reproduction,
            "simple_pair_burnside": burnside_controls,
            "raw_simple_pair_orbits": raw_simple_pair_count,
            "simple_w_orbits_reachable_from_simple_pairs": simple_w_count,
            "simple_pair_to_w_orbit_map_surjective": True,
            "simple_pair_to_w_orbit_map_injective": raw_simple_pair_count == simple_w_count,
            "raw_pair_orbit_excess_over_simple_w_orbits": raw_simple_pair_count
            - simple_w_count,
            "reachability_construction": (
                "For simple W of signed mass s, choose 5-s unused loopless edges and "
                "add them to both signed sides; W=0 uses any simple five-edge graph."
            ),
            "omitted_swap_coset_mutation_rejected": True,
            "ordered_pair_orbits_without_swap": no_swap_orbits,
        },
        "producer": {
            "script": str(Path(__file__).resolve().relative_to(ROOT)),
            "script_sha256": sha256_path(Path(__file__).resolve()),
            "g0027_source": str(G0027_PATH.relative_to(ROOT)),
            "g0027_source_sha256": sha256_path(G0027_PATH),
            "python": sys.version,
            "networkx": G.nx.__version__,
            "pynauty": G.pynauty.__version__,
            "genbg": G.locate_program("genbg"),
        },
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "Finite exhaustive orbit census for loopless signed-W degree-k pair atoms only. "
            "No column-span rank, MAX_n membership, identity, or arbitrary-network theorem."
        ),
    }


def create_outputs(
    document: dict[str, object],
    universe_path: Path,
    manifest_path: Path,
    stage_order_path: Path | None,
) -> None:
    write_gzip_json(universe_path, document)
    stage_metadata = None
    if stage_order_path is not None:
        records = document["records"]
        order = [0] + [
            index
            for index, record in enumerate(records)
            if index != 0
            and int(record["signed_mass"]) == 5
            and int(record["abs_beta"]) <= 1
        ]
        if order[0] != 0 or len(order) != len(set(order)):
            raise AssertionError("stage-A order prefix or uniqueness failed")
        write_json(stage_order_path, order)
        stage_metadata = {
            "path": str(stage_order_path.relative_to(ROOT)),
            "sha256": sha256_path(stage_order_path),
            "index_count": len(order),
            "index_denominator": len(document["records"]),
            "record_zero_first": order[0] == 0,
            "selection_after_record_zero": "signed_mass=5 and abs_beta<=1",
            "selected_nonzero_records": len(order) - 1,
            "selected_nonzero_denominator": len(document["records"]) - 1,
        }
    manifest = {
        "schema": "relu-depth-frontier-gmp15-loopless-universe-manifest-v1",
        "result": "PASS",
        "universe": {
            "path": str(universe_path.relative_to(ROOT)),
            "sha256": sha256_path(universe_path),
            "compressed_bytes": universe_path.stat().st_size,
            "records_sha256": document["records_sha256"],
            "record_count": document["census"]["signed_graph_orbits"],
            "n": document["n"],
            "branch_edge_occurrences": document["branch_edge_occurrences"],
        },
        "counts": {
            "by_signed_mass": document["census"]["counts_by_signed_mass"],
            "by_abs_beta": document["census"]["counts_by_abs_beta"],
            "by_abs_components": document["census"]["counts_by_abs_components"],
            "by_max_multiplicity": document["census"]["counts_by_max_multiplicity"],
            "topology_multiplicity_histogram": document["census"][
                "topology_multiplicity_histogram"
            ],
        },
        "stage_a_order": stage_metadata,
        "controls": document["controls"],
        "producer": document["producer"],
        "wall_seconds": document["wall_seconds"],
        "no_claim": document["no_claim"],
    }
    write_json(manifest_path, manifest)
    print(
        f"GMP15_ENUMERATION_PASS n={document['n']} "
        f"records={document['census']['signed_graph_orbits']} "
        f"universe_sha256={manifest['universe']['sha256']} "
        f"stage_a={None if stage_metadata is None else stage_metadata['index_count']}",
        flush=True,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, required=True)
    parser.add_argument("--branch-edges", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--stage-order", type=Path)
    parser.add_argument("--reference-g0027", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not 2 <= args.n <= 16:
        raise ValueError("n must lie in 2..16")
    if not 1 <= args.branch_edges <= 5:
        raise ValueError("branch degree must lie in 1..5")
    if args.stage_order is not None and (args.n, args.branch_edges) != (12, 5):
        raise ValueError("the registered stage-A order is only for n=12,k=5")
    reference = args.reference_g0027.resolve() if args.reference_g0027 is not None else None
    stage_order = args.stage_order.resolve() if args.stage_order is not None else None
    document = enumerate_universe(args.n, args.branch_edges, reference)
    create_outputs(document, args.output.resolve(), args.manifest.resolve(), stage_order)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
