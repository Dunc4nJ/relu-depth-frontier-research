#!/usr/bin/env python3
"""Map the frozen G-0113 MAX10 lift into the G-0027 record universe.

The output order contains record 0 first, followed by the remaining G-0113
signed-W orbits in their frozen orbit-index order.  This program only builds
and audits a finite dictionary; it does not test target membership.
"""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from typing import Iterable, Sequence

import pynauty


ROOT = Path(__file__).resolve().parents[3]
DEFAULT_G0113_MAP = (
    ROOT / "artifacts/math/G-0113/degree5_signed_orbit_representatives_v1.jsonl.gz"
)
DEFAULT_UNIVERSE = (
    ROOT / "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
)
DEFAULT_CERTIFICATE = (
    ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
)
DEFAULT_ORDER = Path(__file__).resolve().parent / "max10-lift-g0027-order.json"
DEFAULT_REPORT = Path(__file__).resolve().parent / "max10-lift-map-report.json"

EXPECTED_G0113_MAP_SHA256 = (
    "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48"
)
EXPECTED_UNIVERSE_SHA256 = (
    "8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8"
)
EXPECTED_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
EXPECTED_SOURCE_TERMS = 402
EXPECTED_RAW_PER_SOURCE = 55 * 54
EXPECTED_RAW_EXTENSIONS = EXPECTED_SOURCE_TERMS * EXPECTED_RAW_PER_SOURCE
EXPECTED_LIFT_ORBITS = 163_740
EXPECTED_UNIVERSE_RECORDS = 754_017
N = 11

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class MappingError(RuntimeError):
    """A frozen binding or exact mapping invariant failed."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise MappingError(message)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def canonical_side(raw: Iterable[Sequence[int]]) -> Side:
    return tuple(sorted((min(map(int, edge)), max(map(int, edge))) for edge in raw))


def cancelled_pair(pair: Pair) -> Pair:
    negative = Counter(pair[0])
    positive = Counter(pair[1])
    common = negative & positive
    negative.subtract(common)
    positive.subtract(common)
    result = tuple(sorted(negative.elements())), tuple(sorted(positive.elements()))
    require(len(result[0]) == len(result[1]), "unbalanced signed mass")
    return result


def signed_certificate(pair: Pair, n: int = N) -> bytes:
    """G-0113 typed-incidence certificate after common-edge cancellation."""

    negative, positive = cancelled_pair(pair)
    adjacency: dict[int, set[int]] = {index: set() for index in range(n + 2)}
    negative_branch, positive_branch = n, n + 1
    occurrences: set[int] = set()
    for branch, side in ((negative_branch, negative), (positive_branch, positive)):
        for u, v in side:
            require(1 <= u <= v <= n, f"edge {(u, v)} outside [1,{n}]")
            occurrence = len(adjacency)
            occurrences.add(occurrence)
            adjacency[occurrence] = {branch, u - 1}
            adjacency[branch].add(occurrence)
            adjacency[u - 1].add(occurrence)
            if v != u:
                adjacency[occurrence].add(v - 1)
                adjacency[v - 1].add(occurrence)
    coloring = [set(range(n)), {negative_branch, positive_branch}]
    if occurrences:
        coloring.append(occurrences)
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={node: sorted(neighbours) for node, neighbours in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph)


def certificate_sha256(pair: Pair, n: int = N) -> str:
    return hashlib.sha256(signed_certificate(pair, n)).hexdigest()


def topology(pair: Pair) -> dict[str, int]:
    negative, positive = cancelled_pair(pair)
    signed_mass = len(negative)
    vertices = sorted({v for edge in negative + positive for v in edge})
    if not vertices:
        return {
            "signed_mass": 0,
            "active_vertices": 0,
            "abs_components": 0,
            "abs_beta": 0,
        }
    parent = {vertex: vertex for vertex in vertices}

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    for u, v in negative + positive:
        first, second = find(u), find(v)
        if first != second:
            parent[second] = first
    components = len({find(vertex) for vertex in vertices})
    active = len(vertices)
    return {
        "signed_mass": signed_mass,
        "active_vertices": active,
        "abs_components": components,
        "abs_beta": 2 * signed_mass - active + components,
    }


def relation(left: Edge, right: Edge) -> str:
    require(left != right, "added edges are not distinct")
    overlap = len(set(left) & set(right))
    require(overlap in {0, 1}, "distinct nonloop edges have invalid overlap")
    return "DISJOINT" if overlap == 0 else "SHARED_DISTINCT"


def load_source_terms(path: Path) -> tuple[list[Pair], list[Fraction]]:
    require(sha256_path(path) == EXPECTED_CERTIFICATE_SHA256, "source certificate drift")
    document = json.loads(path.read_text(encoding="utf-8"))
    terms = document.get("terms")
    require(document.get("n") == 10, "source arity drift")
    require(isinstance(terms, list) and len(terms) == EXPECTED_SOURCE_TERMS, "source term count drift")
    pairs: list[Pair] = []
    coefficients: list[Fraction] = []
    for index, term in enumerate(terms):
        raw_pair = term.get("pair")
        require(isinstance(raw_pair, list) and len(raw_pair) == 2, f"source pair {index} malformed")
        pair = canonical_side(raw_pair[0]), canonical_side(raw_pair[1])
        require(len(pair[0]) == len(pair[1]) == 4, f"source degree drift at {index}")
        require(
            all(1 <= u < v <= 10 for side in pair for u, v in side),
            f"source term {index} is not loop-free",
        )
        pairs.append(pair)
        coefficients.append(Fraction(term["coefficient"]))
    return pairs, coefficients


def extension_pair(source: Pair, left: Edge, right: Edge) -> Pair:
    return tuple(
        tuple(sorted(side + (added,)))
        for side, added in zip(source, (left, right), strict=True)
    )  # type: ignore[return-value]


def audit_g0113(
    path: Path, source_pairs: Sequence[Pair], source_coefficients: Sequence[Fraction]
) -> tuple[list[dict[str, object]], list[set[int]], list[int]]:
    require(sha256_path(path) == EXPECTED_G0113_MAP_SHA256, "G-0113 map drift")
    records: list[dict[str, object]] = []
    term_orbits = [set() for _ in range(EXPECTED_SOURCE_TERMS)]
    raw_by_term = [0] * EXPECTED_SOURCE_TERMS
    with gzip.open(path, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        require(header.get("record_type") == "header", "G-0113 header absent")
        require(header.get("primary_signed_W_orbits") == EXPECTED_LIFT_ORBITS, "G-0113 header count drift")
        require(header.get("source_certificate_sha256") == EXPECTED_CERTIFICATE_SHA256, "G-0113 source binding drift")
        for line in source:
            record = json.loads(line)
            orbit_index = len(records)
            require(record.get("record_type") == "signed_W_orbit", f"record type drift at {orbit_index}")
            require(record.get("orbit_index") == orbit_index, f"orbit order drift at {orbit_index}")
            raw_pair = record.get("representative_pair")
            require(isinstance(raw_pair, list) and len(raw_pair) == 2, f"representative pair malformed at {orbit_index}")
            pair = canonical_side(raw_pair[0]), canonical_side(raw_pair[1])
            require(len(pair[0]) == len(pair[1]) == 5, f"representative degree drift at {orbit_index}")
            require(all(1 <= u < v <= N for side in pair for u, v in side), f"loop-bearing representative at {orbit_index}")
            observed_hash = certificate_sha256(pair)
            require(observed_hash == record.get("signed_class_sha256"), f"signed certificate drift at {orbit_index}")
            observed_topology = topology(pair)
            frozen_topology = record.get("topology")
            require(isinstance(frozen_topology, dict), f"topology absent at {orbit_index}")
            for field, value in observed_topology.items():
                require(frozen_topology.get(field) == value, f"topology {field} drift at {orbit_index}")

            fibers = record.get("source_fibers")
            require(isinstance(fibers, dict), f"source fibers absent at {orbit_index}")
            for slice_name in ("DISJOINT", "SHARED_DISTINCT"):
                fiber = fibers.get(slice_name)
                require(isinstance(fiber, dict), f"{slice_name} fiber absent at {orbit_index}")
                entries = fiber.get("entries")
                require(isinstance(entries, list), f"{slice_name} entries malformed at {orbit_index}")
                entry_raw = 0
                for entry in entries:
                    term = int(entry["source_term"])
                    require(0 <= term < EXPECTED_SOURCE_TERMS, "source term outside frozen range")
                    left = tuple(map(int, entry["representative_left_added_edge"]))
                    right = tuple(map(int, entry["representative_right_added_edge"]))
                    require(len(left) == len(right) == 2, "added edge malformed")
                    require(all(1 <= u < v <= N for u, v in (left, right)), "added edge is not loop-free")
                    require(relation(left, right) == slice_name, "source-fiber relation drift")
                    require(Fraction(entry["source_coefficient"]) == source_coefficients[term], "source coefficient drift")
                    require(certificate_sha256(extension_pair(source_pairs[term], left, right)) == observed_hash, "source fiber maps to wrong signed orbit")
                    multiplicity = int(entry["raw_multiplicity"])
                    require(multiplicity > 0, "nonpositive raw multiplicity")
                    require(
                        Fraction(entry["coefficient_times_multiplicity"])
                        == source_coefficients[term] * multiplicity,
                        "weighted multiplicity drift",
                    )
                    entry_raw += multiplicity
                    raw_by_term[term] += multiplicity
                    term_orbits[term].add(orbit_index)
                require(entry_raw == int(fiber["raw_multiplicity_sum"]), "fiber raw sum drift")
            records.append(record)
    require(len(records) == EXPECTED_LIFT_ORBITS, "G-0113 body count drift")
    require(sum(raw_by_term) == EXPECTED_RAW_EXTENSIONS, "global raw extension count drift")
    require(all(value == EXPECTED_RAW_PER_SOURCE for value in raw_by_term), "per-source raw extension count drift")
    require(all(term_orbits), "a source term maps to no signed-W orbit")
    hashes = [str(record["signed_class_sha256"]) for record in records]
    require(len(set(hashes)) == EXPECTED_LIFT_ORBITS, "duplicate G-0113 signed certificate")
    return records, term_orbits, raw_by_term


def universe_pair(record: dict[str, object]) -> Pair:
    return (
        tuple((int(u) + 1, int(v) + 1) for u, v in record["negative_edges"]),
        tuple((int(u) + 1, int(v) + 1) for u, v in record["positive_edges"]),
    )


def map_universe(path: Path) -> tuple[dict[str, int], str, list[dict[str, object]]]:
    require(sha256_path(path) == EXPECTED_UNIVERSE_SHA256, "G-0027 universe drift")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    records = document.get("records")
    require(document.get("schema") == "max11-g0027-loopless-signed-degree5-universe-v1", "G-0027 schema drift")
    require(document.get("result") == "PASS", "G-0027 is not a passing universe")
    require(document.get("n") == N and document.get("branch_edge_occurrences") == 5, "G-0027 arity/degree drift")
    require(isinstance(records, list) and len(records) == EXPECTED_UNIVERSE_RECORDS, "G-0027 record count drift")
    certificate_to_index: dict[str, int] = {}
    stream_digest = hashlib.sha256()
    for index, record in enumerate(records):
        require(isinstance(record, dict), f"G-0027 record {index} malformed")
        pair = universe_pair(record)
        observed_topology = topology(pair)
        for field, value in observed_topology.items():
            require(record.get(field) == value, f"G-0027 topology {field} drift at {index}")
        digest = certificate_sha256(pair)
        require(digest not in certificate_to_index, f"duplicate G-0027 signed certificate at {index}")
        certificate_to_index[digest] = index
        stream_digest.update((digest + "\n").encode("ascii"))
    return certificate_to_index, stream_digest.hexdigest(), records


def write_new(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="ascii") as destination:
        destination.write(json.dumps(value, sort_keys=True, separators=(",", ":")))
        destination.write("\n")


def run(args: argparse.Namespace) -> dict[str, object]:
    source_pairs, source_coefficients = load_source_terms(args.source_certificate)
    lift_records, term_orbits, raw_by_term = audit_g0113(
        args.g0113_map, source_pairs, source_coefficients
    )
    universe_map, universe_certificate_stream_sha256, universe_records = map_universe(
        args.universe
    )

    frozen_order: list[int] = []
    missing: list[int] = []
    mapping_digest = hashlib.sha256()
    zero_orbits: list[int] = []
    for record in lift_records:
        orbit_index = int(record["orbit_index"])
        signed_hash = str(record["signed_class_sha256"])
        index = universe_map.get(signed_hash)
        if index is None:
            missing.append(orbit_index)
            continue
        frozen_order.append(index)
        if index == 0:
            zero_orbits.append(orbit_index)
        g0027 = universe_records[index]
        frozen_topology = record["topology"]
        for field in ("signed_mass", "active_vertices", "abs_components", "abs_beta"):
            require(g0027[field] == frozen_topology[field], f"mapped topology {field} drift at orbit {orbit_index}")
        mapping_digest.update(
            canonical_bytes(
                {
                    "g0027_record_index": index,
                    "g0113_orbit_index": orbit_index,
                    "signed_class_sha256": signed_hash,
                }
            )
        )
    require(not missing, f"{len(missing)} G-0113 signed orbits missing from G-0027")
    require(len(frozen_order) == len(set(frozen_order)) == EXPECTED_LIFT_ORBITS, "lift mapping is not injective")
    require(zero_orbits == [37_083], f"zero-orbit mapping drift: {zero_orbits}")

    order = [0] + [index for index in frozen_order if index != 0]
    require(len(order) == EXPECTED_LIFT_ORBITS and len(set(order)) == len(order), "output order census drift")
    write_new(args.output_order, order)

    source_term_map: list[dict[str, object]] = []
    source_map_digest = hashlib.sha256()
    for term, orbit_indices in enumerate(term_orbits):
        indices = sorted(frozen_order[orbit] for orbit in orbit_indices)
        index_digest = hashlib.sha256(canonical_bytes(indices)).hexdigest()
        entry = {
            "source_term": term,
            "raw_extensions": raw_by_term[term],
            "distinct_signed_W_orbits": len(indices),
            "g0027_record_indices_sha256": index_digest,
        }
        source_term_map.append(entry)
        source_map_digest.update(canonical_bytes(entry))

    nonzero_witness = next(record for record in lift_records if record["topology"]["signed_mass"] > 0)
    witness_pair = canonical_side(nonzero_witness["representative_pair"][0]), canonical_side(nonzero_witness["representative_pair"][1])
    first_edge = witness_pair[0][0]
    loop_mutant: Pair = (
        tuple(sorted(((first_edge[0], first_edge[0]),) + witness_pair[0][1:])),
        witness_pair[1],
    )
    loop_mutant_hash = certificate_sha256(loop_mutant)
    require(loop_mutant_hash not in universe_map, "loop mutant unexpectedly entered loop-free G-0027 universe")

    report: dict[str, object] = {
        "schema": "max11-naive-induction-lift-map-v1",
        "result": "PASS",
        "definition": {
            "source": "all 402 terms of the pinned degree-four MAX10 certificate",
            "embedding": "labels 1..10 are embedded in [11]; quotienting by S_11 covers every injective relabeling",
            "extension": "append ordered distinct nonloop edges e_L and e_R on [11], one to each branch",
            "raw_strata": {
                "DISJOINT_per_source": 55 * 36,
                "SHARED_DISTINCT_per_source": 55 * 18,
                "union_per_source": EXPECTED_RAW_PER_SOURCE,
            },
            "quotient": "cancel common occurrences, then quotient signed W by S_11 relabeling and global sign reversal",
            "order": "G-0027 record 0 first, then nonzero records in frozen G-0113 orbit-index order",
        },
        "bindings": {
            "source_certificate": str(args.source_certificate.relative_to(ROOT)),
            "source_certificate_sha256": sha256_path(args.source_certificate),
            "g0113_representative_map": str(args.g0113_map.relative_to(ROOT)),
            "g0113_representative_map_sha256": sha256_path(args.g0113_map),
            "g0027_universe": str(args.universe.relative_to(ROOT)),
            "g0027_universe_sha256": sha256_path(args.universe),
        },
        "counts": {
            "source_terms_denominator": EXPECTED_SOURCE_TERMS,
            "raw_extensions_denominator": EXPECTED_RAW_EXTENSIONS,
            "signed_W_orbits_denominator": EXPECTED_LIFT_ORBITS,
            "g0027_universe_records_denominator": EXPECTED_UNIVERSE_RECORDS,
            "mapped_signed_W_orbits_numerator": len(frozen_order),
            "missing_signed_W_orbits_numerator": len(missing),
            "raw_extensions_outside_loopless_universe_numerator": 0,
            "zero_orbits": len(zero_orbits),
            "zero_g0113_orbit_index": zero_orbits[0],
            "record_zero_first": order[0] == 0,
        },
        "outside_explanation": "0 / 1,193,940 raw extensions and 0 / 163,740 signed-W orbits are outside G-0027: every pinned source edge and every allowed added edge is a nonloop, cancellation leaves balanced signed mass at most five, and exact typed-incidence certificates map every orbit injectively.",
        "source_term_mapping": {
            "terms_with_at_least_one_orbit_numerator": sum(bool(value) for value in term_orbits),
            "terms_denominator": EXPECTED_SOURCE_TERMS,
            "term_orbit_incidence_numerator": sum(len(value) for value in term_orbits),
            "mapping_stream_sha256": source_map_digest.hexdigest(),
            "per_source_term": source_term_map,
        },
        "mapping": {
            "g0113_to_g0027_stream_sha256": mapping_digest.hexdigest(),
            "g0027_certificate_stream_sha256": universe_certificate_stream_sha256,
            "order_file": str(args.output_order.relative_to(ROOT)),
            "order_file_sha256": sha256_path(args.output_order),
        },
        "controls": {
            "positive_all_g0113_representative_certificates_recomputed": len(lift_records),
            "positive_all_source_fiber_witnesses_recomputed": True,
            "positive_every_source_raw_multiplicity_sum": EXPECTED_RAW_PER_SOURCE,
            "positive_zero_orbit_maps_to_g0027_record_zero": True,
            "negative_loop_mutant_rejected_by_loopless_universe": True,
            "negative_loop_mutant_certificate_sha256": loop_mutant_hash,
            "full_g0027_certificate_uniqueness_replayed": len(universe_map),
        },
        "known_answer_n9_to_n10": {
            "recorded_same_construction_outcome_found": False,
            "note": "Repository search found no recorded n=9-certificate to n=10 arbitrary-distinct-edge lift span decision. G-0112 records MAX6-to-MAX7 controls, not this requested n=9-to-n=10 analogue.",
        },
        "no_claim": "This exact map identifies one finite source-derived dictionary inside G-0027. It neither proves target membership nor an exact MAX11 identity, and a later modular decision remains bounded to its named sketch, prime, and family.",
    }
    write_new(args.output_report, report)
    return report


def self_test() -> None:
    pair: Pair = (((1, 2), (2, 3)), ((1, 3), (3, 4)))
    perm = {1: 4, 2: 3, 3: 2, 4: 1}

    def relabel(side: Side) -> Side:
        return tuple(sorted((min(perm.get(u, u), perm.get(v, v)), max(perm.get(u, u), perm.get(v, v))) for u, v in side))

    base = signed_certificate(pair)
    require(base == signed_certificate((relabel(pair[0]), relabel(pair[1]))), "relabel self-test failed")
    require(base == signed_certificate((pair[1], pair[0])), "branch-swap self-test failed")
    mutant: Pair = (pair[0] + ((1, 2),), pair[1] + ((1, 4),))
    require(base != signed_certificate(mutant), "multiplicity mutant self-test failed")
    require(relation((1, 2), (3, 4)) == "DISJOINT", "disjoint relation self-test failed")
    require(relation((1, 2), (2, 3)) == "SHARED_DISTINCT", "shared relation self-test failed")
    print("SELF_TEST_PASS")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g0113-map", type=Path, default=DEFAULT_G0113_MAP)
    parser.add_argument("--universe", type=Path, default=DEFAULT_UNIVERSE)
    parser.add_argument("--source-certificate", type=Path, default=DEFAULT_CERTIFICATE)
    parser.add_argument("--output-order", type=Path, default=DEFAULT_ORDER)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    for field in (
        "g0113_map",
        "universe",
        "source_certificate",
        "output_order",
        "output_report",
    ):
        setattr(args, field, getattr(args, field).resolve())
    if args.self_test:
        self_test()
        return
    report = run(args)
    print(json.dumps({"result": report["result"], "counts": report["counts"], "mapping": report["mapping"]}, sort_keys=True))


if __name__ == "__main__":
    main()
