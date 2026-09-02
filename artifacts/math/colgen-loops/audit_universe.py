#!/usr/bin/env python3
"""Verify G-0038 custody/schema/counts and draw deterministic control samples."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass, field
import gzip
import hashlib
import json
from pathlib import Path
import random
import struct
import time
from typing import BinaryIO


SCHEMA = "max11-loop-inclusive-signed-degree5-universe-v1"
REPORT_SCHEMA = "max11-gmp13-loop-inclusive-universe-audit-v1"
EXPECTED_RECORDS = 7_015_841
EXPECTED_COMPRESSED_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_FRAMED_SHA256 = (
    "89ffe6d0f8aec9fb0ef8d91c5f15b75c89a6bd0d5bdd5b554c155f5c18e177cd"
)
EXPECTED_ORBIT_SHA256 = (
    "e49035b2700272f6edc1d1792bbceb0d5811a870820dd982d67a243b79423ef5"
)


class AuditError(RuntimeError):
    pass


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_line(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def validate_edge(raw: object, active_vertices: int) -> tuple[int, int]:
    if not isinstance(raw, list) or len(raw) != 2:
        raise AuditError("edge must be a two-element list")
    left, right = raw
    if not isinstance(left, int) or not isinstance(right, int):
        raise AuditError("edge endpoints must be integers")
    if not (0 <= left <= right < active_vertices):
        raise AuditError(f"edge {(left, right)} outside active vertex range")
    return left, right


def validate_record(value: object, expected_sequence: int) -> tuple[int, int, int]:
    if not isinstance(value, dict):
        raise AuditError("orbit record must be an object")
    if value.get("schema") != SCHEMA or value.get("record_type") != "orbit":
        raise AuditError("orbit schema/type mismatch")
    if value.get("sequence") != expected_sequence:
        raise AuditError(
            f"sequence mismatch {value.get('sequence')} != {expected_sequence}"
        )
    signed_mass = value.get("signed_mass")
    active_vertices = value.get("active_vertices")
    components = value.get("abs_components")
    beta = value.get("abs_beta")
    if not isinstance(signed_mass, int) or not 0 <= signed_mass <= 5:
        raise AuditError("signed_mass outside 0..5")
    if not isinstance(active_vertices, int) or not 0 <= active_vertices <= 11:
        raise AuditError("active_vertices outside 0..11")
    if not isinstance(components, int) or components < 0:
        raise AuditError("invalid abs_components")
    if not isinstance(beta, int):
        raise AuditError("invalid abs_beta")
    negative_raw = value.get("negative_edges")
    positive_raw = value.get("positive_edges")
    if not isinstance(negative_raw, list) or not isinstance(positive_raw, list):
        raise AuditError("signed edge sides must be lists")
    if len(negative_raw) != signed_mass or len(positive_raw) != signed_mass:
        raise AuditError("side occurrence count differs from signed_mass")
    if signed_mass == 0:
        if active_vertices != 0 or components != 0 or beta != 0:
            raise AuditError("zero record metadata mismatch")
        negative: list[tuple[int, int]] = []
        positive: list[tuple[int, int]] = []
    else:
        if active_vertices == 0:
            raise AuditError("nonzero record has no active vertices")
        negative = [validate_edge(edge, active_vertices) for edge in negative_raw]
        positive = [validate_edge(edge, active_vertices) for edge in positive_raw]
        if negative != sorted(negative) or positive != sorted(positive):
            raise AuditError("signed edge occurrences are not sorted")
        if set(negative) & set(positive):
            raise AuditError("opposite signs share an uncancelled edge")
        used = {vertex for edge in negative + positive for vertex in edge}
        if used != set(range(active_vertices)):
            raise AuditError("active vertices are not exactly the used coordinate prefix")
    negative_loops = sum(left == right for left, right in negative)
    positive_loops = sum(left == right for left, right in positive)
    if value.get("negative_loop_count") != negative_loops:
        raise AuditError("negative_loop_count does not replay")
    if value.get("positive_loop_count") != positive_loops:
        raise AuditError("positive_loop_count does not replay")
    if beta != 2 * signed_mass - active_vertices + components:
        raise AuditError("abs_beta identity failed")
    return signed_mass, active_vertices, negative_loops + positive_loops


@dataclass
class Reservoir:
    size: int
    seed: int
    eligible: int = 0
    rows: list[dict[str, object]] = field(default_factory=list)
    _random: random.Random = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._random = random.Random(self.seed)

    def consider(self, value: dict[str, object]) -> None:
        self.eligible += 1
        if len(self.rows) < self.size:
            self.rows.append(value)
            return
        replacement = self._random.randrange(self.eligible)
        if replacement < self.size:
            self.rows[replacement] = value

    def finish(self) -> list[dict[str, object]]:
        if len(self.rows) != self.size:
            raise AuditError(
                f"reservoir undersized: {len(self.rows)}/{self.size} from {self.eligible}"
            )
        return sorted(self.rows, key=lambda row: int(row["sequence"]))


def sequence_hash(rows: list[dict[str, object]]) -> str:
    digest = hashlib.sha256()
    for row in rows:
        digest.update(struct.pack("<Q", int(row["sequence"])))
    return digest.hexdigest()


def create_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")


def create_jsonl(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as handle:
        for row in rows:
            handle.write(canonical_line(row))


def run(
    universe: Path,
    manifest_path: Path,
    output_dir: Path,
    sample_size: int,
    seed: int,
) -> dict[str, object]:
    started = time.monotonic()
    manifest = json.loads(manifest_path.read_text())
    stream_manifest = manifest["stream"]
    if stream_manifest["record_count"] != EXPECTED_RECORDS:
        raise AuditError("manifest record count differs from frozen known answer")
    if stream_manifest["compressed_sha256"] != EXPECTED_COMPRESSED_SHA256:
        raise AuditError("manifest compressed hash differs from frozen known answer")
    compressed_hash = sha256_path(universe)
    if compressed_hash != EXPECTED_COMPRESSED_SHA256:
        raise AuditError("compressed universe hash mismatch")
    if universe.stat().st_size != stream_manifest["compressed_bytes"]:
        raise AuditError("compressed byte count mismatch")

    benchmark = Reservoir(sample_size, seed)
    python_n9 = Reservoir(sample_size, seed + 9)
    python_n10 = Reservoir(sample_size, seed + 10)
    loopless_n11 = Reservoir(sample_size, seed + 11)
    framed_digest = hashlib.sha256()
    orbit_digest = hashlib.sha256()
    strata_counts: Counter[tuple[int, int]] = Counter()
    strata_digests = {
        (int(row["signed_mass"]), int(row["active_vertices"])): hashlib.sha256()
        for row in stream_manifest["strata"]
    }
    loop_counts: Counter[int] = Counter()
    mass_counts: Counter[int] = Counter()

    with gzip.open(universe, "rb") as handle:
        header_line = handle.readline()
        if not header_line:
            raise AuditError("universe stream is empty")
        framed_digest.update(header_line)
        header = json.loads(header_line)
        if canonical_line(header) != header_line:
            raise AuditError("header line is not canonical JSON")
        if (
            header.get("schema") != SCHEMA
            or header.get("record_type") != "header"
            or header.get("n") != 11
            or header.get("branch_edge_occurrences") != 5
            or header.get("loops_allowed") is not True
            or header.get("expected_record_count") != EXPECTED_RECORDS
        ):
            raise AuditError("header contract mismatch")
        if hashlib.sha256(header_line).hexdigest() != stream_manifest["canonical_header_sha256"]:
            raise AuditError("canonical header hash mismatch")

        record_count = 0
        for line_number, line in enumerate(handle, start=2):
            if not line.endswith(b"\n"):
                raise AuditError(f"line {line_number} lacks newline framing")
            value = json.loads(line)
            if canonical_line(value) != line:
                raise AuditError(f"line {line_number} is not canonical JSON")
            signed_mass, active_vertices, total_loops = validate_record(
                value, record_count
            )
            key = (signed_mass, active_vertices)
            if key not in strata_digests:
                raise AuditError(f"unexpected stratum {key}")
            framed_digest.update(line)
            orbit_digest.update(line)
            strata_digests[key].update(line)
            strata_counts[key] += 1
            loop_counts[total_loops] += 1
            mass_counts[signed_mass] += 1
            benchmark.consider(value)
            if total_loops == 0:
                loopless_n11.consider(value)
            else:
                if active_vertices <= 9:
                    python_n9.consider(value)
                if active_vertices <= 10:
                    python_n10.consider(value)
            record_count += 1
            if record_count % 1_000_000 == 0:
                print(
                    f"GMP13_AUDIT_PROGRESS records={record_count}/{EXPECTED_RECORDS}",
                    flush=True,
                )

    if record_count != EXPECTED_RECORDS:
        raise AuditError(f"record count mismatch {record_count}/{EXPECTED_RECORDS}")
    if framed_digest.hexdigest() != EXPECTED_FRAMED_SHA256:
        raise AuditError("framed uncompressed hash mismatch")
    if orbit_digest.hexdigest() != EXPECTED_ORBIT_SHA256:
        raise AuditError("orbit-only uncompressed hash mismatch")

    expected_strata = {
        (int(row["signed_mass"]), int(row["active_vertices"])): int(row["record_count"])
        for row in stream_manifest["strata"]
    }
    if dict(strata_counts) != {key: value for key, value in expected_strata.items() if value}:
        # Counter omits the three declared zero strata.
        observed_with_zeros = {key: strata_counts[key] for key in expected_strata}
        if observed_with_zeros != expected_strata:
            raise AuditError("stratum counts differ from manifest")
    for row in stream_manifest["strata"]:
        key = (int(row["signed_mass"]), int(row["active_vertices"]))
        if strata_digests[key].hexdigest() != row["canonical_jsonl_sha256"]:
            raise AuditError(f"stratum hash mismatch {key}")

    samples = {
        "benchmark_n11": benchmark.finish(),
        "python_n9": python_n9.finish(),
        "python_n10": python_n10.finish(),
        "loopless_n11": loopless_n11.finish(),
    }
    reservoirs = {
        "benchmark_n11": benchmark,
        "python_n9": python_n9,
        "python_n10": python_n10,
        "loopless_n11": loopless_n11,
    }
    sample_metadata: dict[str, object] = {}
    for name, rows in samples.items():
        path = output_dir / f"sample_{name}.jsonl"
        create_jsonl(path, rows)
        sample_metadata[name] = {
            "path": str(path),
            "sha256": sha256_path(path),
            "seed": reservoirs[name].seed,
            "eligible_record_denominator": reservoirs[name].eligible,
            "sample_size": len(rows),
            "sample_denominator": sample_size,
            "sequence_sha256_u64_le": sequence_hash(rows),
        }

    report = {
        "schema": REPORT_SCHEMA,
        "result": "PASS",
        "universe": str(universe),
        "universe_compressed_bytes": universe.stat().st_size,
        "universe_compressed_sha256": compressed_hash,
        "manifest": str(manifest_path),
        "manifest_sha256": sha256_path(manifest_path),
        "records_checked": record_count,
        "record_denominator": EXPECTED_RECORDS,
        "canonical_framed_jsonl_sha256": framed_digest.hexdigest(),
        "canonical_orbit_jsonl_sha256": orbit_digest.hexdigest(),
        "strata_checked": len(expected_strata),
        "strata_denominator": len(stream_manifest["strata"]),
        "record_count_by_signed_mass": {
            str(key): mass_counts[key] for key in range(6)
        },
        "record_count_by_total_signed_loop_occurrences": {
            str(key): loop_counts[key] for key in range(11)
        },
        "loop_bearing_records": record_count - loop_counts[0],
        "loopless_records": loop_counts[0],
        "samples": sample_metadata,
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "This verifies and samples the finite serialized G-0038 denominator. "
            "It does not establish a MAX11 identity, membership or non-membership, "
            "or completeness for arbitrary two-hidden-layer ReLU networks."
        ),
    }
    create_json(output_dir / "universe_audit.json", report)
    return report


def self_test() -> None:
    record = {
        "schema": SCHEMA,
        "record_type": "orbit",
        "sequence": 0,
        "signed_mass": 1,
        "active_vertices": 2,
        "negative_edges": [[0, 0]],
        "positive_edges": [[0, 1]],
        "negative_loop_count": 1,
        "positive_loop_count": 0,
        "abs_components": 1,
        "abs_beta": 1,
    }
    assert validate_record(record, 0) == (1, 2, 1)
    mutant = dict(record, negative_loop_count=0)
    try:
        validate_record(mutant, 0)
    except AuditError:
        pass
    else:
        raise AssertionError("wrong loop-count mutant survived")
    opposite = dict(record, positive_edges=[[0, 0]], positive_loop_count=1)
    try:
        validate_record(opposite, 0)
    except AuditError:
        pass
    else:
        raise AssertionError("uncancelled opposite-sign mutant survived")
    reservoir = Reservoir(3, 17)
    for sequence in range(20):
        reservoir.consider({"sequence": sequence})
    assert len(reservoir.finish()) == 3 and reservoir.eligible == 20
    print("GMP13_AUDIT_SELF_TEST_PASS positive=1 mutants=2/2 reservoir=3/3")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--universe", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--sample-size", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=2_026_090_213)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    if args.universe is None or args.manifest is None or args.output_dir is None:
        raise SystemExit("--universe, --manifest, and --output-dir are required")
    if args.sample_size <= 0:
        raise SystemExit("--sample-size must be positive")
    report = run(
        args.universe,
        args.manifest,
        args.output_dir,
        args.sample_size,
        args.seed,
    )
    print(
        "GMP13_UNIVERSE_AUDIT_PASS "
        f"records={report['records_checked']}/{report['record_denominator']} "
        f"strata={report['strata_checked']}/{report['strata_denominator']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
