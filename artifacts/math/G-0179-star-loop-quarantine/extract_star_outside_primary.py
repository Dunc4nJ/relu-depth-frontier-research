#!/usr/bin/env python3
"""Regenerate G-0113 STAR orbits and emit the loop-bearing part outside primary.

This is deliberately target-blind.  It imports the frozen G-0113 census
implementation, regenerates every STAR signed certificate from the source
MAX10 certificate, and subtracts the exact class hashes in the frozen primary
representative map.  It computes no MAX11 target value or rank.
"""

from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path("/data/projects/relu-depth-frontier-research")
G0113 = ROOT / "artifacts/math/G-0113"
SOURCE = G0113 / "degree5_quotient_census.py"
PRIMARY_MAP = G0113 / "degree5_signed_orbit_representatives_v1.jsonl.gz"
CENSUS_REPORT = G0113 / "degree5_quotient_census_v1.json"
EXPECTED_PRIMARY_MAP_SHA256 = (
    "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48"
)
EXPECTED_OUTSIDE = 5_773
EXPECTED_MASS_HISTOGRAM = {1: 1, 2: 7, 3: 66, 4: 781, 5: 4_918}
EXPECTED_ACTIVE_HISTOGRAM = {
    2: 1,
    4: 3,
    5: 3,
    6: 19,
    7: 66,
    8: 106,
    9: 431,
    10: 921,
    11: 4_223,
}
SCHEMA = "g0179.star-outside-primary-loop-records.v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_g0113() -> Any:
    spec = importlib.util.spec_from_file_location("g0179_frozen_g0113", SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError("could not import frozen G-0113 producer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_primary_hashes(module: Any) -> tuple[set[str], dict[str, Any]]:
    if sha256_path(PRIMARY_MAP) != EXPECTED_PRIMARY_MAP_SHA256:
        raise RuntimeError("frozen primary representative map hash drift")
    report = json.loads(CENSUS_REPORT.read_text(encoding="utf-8"))
    if report["representative_map"]["compressed_sha256"] != EXPECTED_PRIMARY_MAP_SHA256:
        raise RuntimeError("G-0113 report/map binding drift")
    hashes: set[str] = set()
    header: dict[str, Any] | None = None
    records = 0
    with gzip.open(PRIMARY_MAP, "rt", encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            item = json.loads(line)
            if line_number == 1:
                header = item
                if item.get("record_type") != "header" or item.get("schema") != module.MAP_SCHEMA:
                    raise RuntimeError("primary map header drift")
                continue
            if item.get("record_type") != "signed_W_orbit":
                raise RuntimeError(f"unexpected primary map record at line {line_number}")
            class_hash = item.get("signed_class_sha256")
            if not isinstance(class_hash, str) or len(class_hash) != 64:
                raise RuntimeError(f"malformed class hash at line {line_number}")
            if class_hash in hashes:
                raise RuntimeError("duplicate primary class hash")
            hashes.add(class_hash)
            records += 1
    if header is None or records != 163_740 or header.get("primary_signed_W_orbits") != records:
        raise RuntimeError("primary record census drift")
    if records != report["representative_map"]["records"]:
        raise RuntimeError("primary report record census drift")
    return hashes, header


def compact_signed_pair(module: Any, pair: Any) -> dict[str, Any]:
    negative, positive = module.cancelled_pair(pair)
    support = sorted({vertex for edge in negative + positive for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(support)}

    def compact(side: Any) -> list[list[int]]:
        return [[relabel[u], relabel[v]] for u, v in side]

    return {
        "signed_mass": len(negative),
        "active_vertices": len(support),
        "negative_loop_count": sum(u == v for u, v in negative),
        "positive_loop_count": sum(u == v for u, v in positive),
        "negative_edges": compact(negative),
        "positive_edges": compact(positive),
        "original_active_labels": support,
        "cancelled_signed_pair": module.serialize_pair((negative, positive)),
    }


def main() -> int:
    if sys.flags.optimize != 0:
        raise RuntimeError("optimized Python is prohibited; assertions are load-bearing")
    if len(sys.argv) != 2:
        raise SystemExit(f"usage: {Path(sys.argv[0]).name} OUTPUT.json")
    output_path = Path(sys.argv[1]).resolve()
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite {output_path}")

    module = load_g0113()
    terms = module.load_terms()
    primary_hashes, primary_header = load_primary_hashes(module)
    star_counts, star_representatives, _samples = module.star_census(terms)
    if sum(star_counts.values()) != module.EXPECTED_STAR_RAW:
        raise RuntimeError("regenerated STAR raw census drift")
    if len(star_counts) != module.EXPECTED_STAR_ORBITS:
        raise RuntimeError("regenerated STAR orbit census drift")

    # The primary map stores SHA-256 of the exact pynauty certificate.  Check
    # collision-freedom within this regenerated STAR census before subtraction.
    by_hash: dict[str, bytes] = {}
    for certificate in star_counts:
        class_hash = hashlib.sha256(certificate).hexdigest()
        previous = by_hash.setdefault(class_hash, certificate)
        if previous != certificate:
            raise RuntimeError("SHA-256 collision between STAR certificates")
    outside = [
        certificate
        for certificate in star_counts
        if hashlib.sha256(certificate).hexdigest() not in primary_hashes
    ]
    outside.sort(key=module.orbit_sort_key)
    if len(outside) != EXPECTED_OUTSIDE:
        raise RuntimeError(f"STAR-outside-primary census drift: {len(outside)}")

    records: list[dict[str, Any]] = []
    mass_histogram: Counter[int] = Counter()
    active_histogram: Counter[int] = Counter()
    added_edge_type_histogram: Counter[str] = Counter()
    for sequence, certificate in enumerate(outside):
        descriptor = star_representatives[certificate]
        term_index, left_edge, right_edge = descriptor
        added = (left_edge, right_edge)
        loop_flags = [u == v for u, v in added]
        if loop_flags.count(True) != 1 or left_edge == right_edge:
            raise RuntimeError("outside representative is not one distinct loop/nonloop addition")
        pair = module.pair_from_descriptor(terms, descriptor)
        compact = compact_signed_pair(module, pair)
        mass_histogram[compact["signed_mass"]] += 1
        active_histogram[compact["active_vertices"]] += 1
        added_edge_type_histogram[
            "LEFT_LOOP_RIGHT_NONLOOP" if loop_flags[0] else "LEFT_NONLOOP_RIGHT_LOOP"
        ] += 1
        records.append(
            {
                "sequence": sequence,
                "signed_class_sha256": hashlib.sha256(certificate).hexdigest(),
                "raw_star_multiplicity": star_counts[certificate],
                "source_coefficient": str(terms[term_index].coefficient),
                "star_representative": module.serialize_descriptor(descriptor),
                "representative_pair": module.serialize_pair(pair),
                **compact,
            }
        )

    if dict(sorted(mass_histogram.items())) != EXPECTED_MASS_HISTOGRAM:
        raise RuntimeError(f"signed-mass histogram drift: {mass_histogram}")
    if dict(sorted(active_histogram.items())) != EXPECTED_ACTIVE_HISTOGRAM:
        raise RuntimeError(f"active-vertex histogram drift: {active_histogram}")
    if sum(added_edge_type_histogram.values()) != EXPECTED_OUTSIDE:
        raise RuntimeError("added-edge type census drift")

    direction_order_digest = hashlib.sha256()
    for certificate in outside:
        direction_order_digest.update(len(certificate).to_bytes(8, "little"))
        direction_order_digest.update(certificate)
    record_manifest_digest = hashlib.sha256()
    for record in records:
        record_manifest_digest.update(module.canonical_bytes(record))

    output = {
        "schema": SCHEMA,
        "result": "EXACT_STAR_OUTSIDE_PRIMARY_RECORDS",
        "claim_boundary": (
            "Exact target-blind finite extraction of regenerated G-0113 STAR signed-W "
            "orbits absent from the frozen distinct-nonloop primary map. This computes no "
            "MAX11 target value, span membership, rank, obstruction, or family completeness."
        ),
        "bindings": {
            "producer": str(Path(__file__).resolve()),
            "producer_sha256": sha256_path(Path(__file__).resolve()),
            "g0113_producer": str(SOURCE),
            "g0113_producer_sha256": sha256_path(SOURCE),
            "source_certificate": str(module.CERTIFICATE),
            "source_certificate_sha256": sha256_path(module.CERTIFICATE),
            "primary_map": str(PRIMARY_MAP),
            "primary_map_sha256": sha256_path(PRIMARY_MAP),
            "g0113_census_report": str(CENSUS_REPORT),
            "g0113_census_report_sha256": sha256_path(CENSUS_REPORT),
        },
        "source_censuses": {
            "source_terms": len(terms),
            "star_raw_extensions": sum(star_counts.values()),
            "star_signed_W_orbits": len(star_counts),
            "primary_signed_W_orbits": len(primary_hashes),
            "primary_header_source_certificate_sha256": primary_header[
                "source_certificate_sha256"
            ],
        },
        "outside_records": len(records),
        "ordering": "sorted by frozen G-0113 orbit_sort_key(certificate)",
        "ordered_exact_certificate_bytes_sha256": direction_order_digest.hexdigest(),
        "canonical_record_manifest_sha256": record_manifest_digest.hexdigest(),
        "signed_mass_histogram": {str(key): value for key, value in sorted(mass_histogram.items())},
        "active_vertices_histogram": {
            str(key): value for key, value in sorted(active_histogram.items())
        },
        "representative_added_edge_type_histogram": dict(
            sorted(added_edge_type_histogram.items())
        ),
        "all_representatives_one_distinct_loop_nonloop_addition": True,
        "records": records,
    }
    output_path.write_bytes(module.canonical_bytes(output))
    print(
        json.dumps(
            {
                "result": output["result"],
                "outside_records": len(records),
                "signed_mass_histogram": output["signed_mass_histogram"],
                "active_vertices_histogram": output["active_vertices_histogram"],
                "output": str(output_path),
                "output_sha256": sha256_path(output_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
