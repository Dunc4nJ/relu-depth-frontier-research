#!/usr/bin/env python3
"""Enumerate the complete n=11 loop-inclusive signed-W degree-four quotient.

The underlying nauty+pynauty census is the independently audited G-0038
enumerator, stopped after signed mass four.  Every regenerated record is also
compared, in canonical order, with the degree-four prefix of the pinned G-0038
degree-five stream.  The n=10 file is the complete active-support projection
needed for the known-answer rank control.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import time
from typing import Any, Sequence


ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "artifacts/cleanroom/G-0038/independent_loop_inclusive_census.py"
REFERENCE = (
    ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
EXPECTED_SOURCE_SHA256 = "16bf2f5182162698a5812d88635286803b9961cea887a436e809c0c9ca0982cb"
EXPECTED_REFERENCE_SHA256 = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
EXPECTED_N11_RECORDS = 137_504
EXPECTED_N10_RECORDS = 136_036
RECORD_KEYS = (
    "signed_mass",
    "active_vertices",
    "negative_edges",
    "positive_edges",
    "negative_loop_count",
    "positive_loop_count",
    "abs_components",
    "abs_beta",
)
UNIVERSE_RECORD_KEYS = (
    "sequence",
    "signed_mass",
    "active_vertices",
    "negative_edges",
    "positive_edges",
    "abs_components",
    "abs_beta",
)


class EnumerationError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_census_module() -> Any:
    observed = sha256_path(SOURCE)
    if observed != EXPECTED_SOURCE_SHA256:
        raise EnumerationError(
            f"census source hash mismatch: expected {EXPECTED_SOURCE_SHA256}, got {observed}"
        )
    spec = importlib.util.spec_from_file_location("sou_g0038_census", SOURCE)
    if spec is None or spec.loader is None:
        raise EnumerationError("could not load the G-0038 census module")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def core_record(record: dict[str, object]) -> dict[str, object]:
    return {key: record[key] for key in RECORD_KEYS}


def universe_record(record: dict[str, object], sequence: int) -> dict[str, object]:
    enriched = dict(record)
    enriched["sequence"] = sequence
    return {key: enriched[key] for key in UNIVERSE_RECORD_KEYS}


def compare_reference(records: list[dict[str, object]]) -> dict[str, object]:
    observed = sha256_path(REFERENCE)
    if observed != EXPECTED_REFERENCE_SHA256:
        raise EnumerationError(
            f"reference hash mismatch: expected {EXPECTED_REFERENCE_SHA256}, got {observed}"
        )
    with gzip.open(REFERENCE, "rt", encoding="ascii") as source:
        header = json.loads(next(source))
        if not (
            header.get("schema") == "max11-loop-inclusive-signed-degree5-universe-v1"
            and header.get("n") == 11
            and header.get("branch_edge_occurrences") == 5
            and header.get("loops_allowed") is True
        ):
            raise EnumerationError("pinned G-0038 reference header is incompatible")
        compared = 0
        next_signed_mass = None
        for raw in source:
            reference = json.loads(raw)
            signed_mass = int(reference["signed_mass"])
            if signed_mass > 4:
                next_signed_mass = signed_mass
                break
            if compared >= len(records):
                raise EnumerationError("reference degree-four prefix is longer than regeneration")
            if core_record(reference) != records[compared]:
                raise EnumerationError(f"reference mismatch at record {compared}")
            if int(reference["sequence"]) != compared:
                raise EnumerationError(f"reference sequence mismatch at record {compared}")
            compared += 1
    if compared != len(records) or next_signed_mass != 5:
        raise EnumerationError(
            f"reference prefix boundary mismatch: compared={compared}, next={next_signed_mass}"
        )
    return {
        "path": str(REFERENCE.relative_to(ROOT)),
        "sha256": observed,
        "records_compared_numerator": compared,
        "records_compared_denominator": len(records),
        "next_reference_signed_mass": next_signed_mass,
        "verdict": "IDENTICAL",
    }


def write_gzip_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    payload = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(payload)


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def make_universe(n: int, records: list[dict[str, object]]) -> dict[str, object]:
    selected = [record for record in records if int(record["active_vertices"]) <= n]
    return {
        "schema": "max11-sou-loop-inclusive-signed-degree4-universe-v1",
        "n": n,
        "branch_edge_occurrences": 4,
        "loopless": False,
        "padding_convention": "zero common loops; remaining common padding nonloop",
        "record_zero_carrier": "4E",
        "external_carrier": "4L",
        "records": [universe_record(record, index) for index, record in enumerate(selected)],
    }


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-n11", type=Path, required=True)
    parser.add_argument("--output-n10", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--progress-every", type=int, default=10_000)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    started = time.monotonic()
    module = load_census_module()
    controls = module.self_test()
    records: list[dict[str, object]] = []
    census = module.run_census(
        max_signed_mass=4,
        progress_every=args.progress_every,
        record_consumer=lambda record: records.append(core_record(record)),
    )
    if len(records) != EXPECTED_N11_RECORDS:
        raise EnumerationError(
            f"n=11 record count mismatch: expected {EXPECTED_N11_RECORDS}, got {len(records)}"
        )
    mass_counts = Counter(int(record["signed_mass"]) for record in records)
    expected_mass_counts = {0: 1, 1: 5, 2: 107, 3: 3_198, 4: 134_193}
    if dict(mass_counts) != expected_mass_counts:
        raise EnumerationError(f"signed-mass count mismatch: {dict(mass_counts)}")
    reference_comparison = compare_reference(records)
    universe_n11 = make_universe(11, records)
    universe_n10 = make_universe(10, records)
    if len(universe_n10["records"]) != EXPECTED_N10_RECORDS:
        raise EnumerationError("n=10 projected record count mismatch")
    write_gzip_json(args.output_n11, universe_n11)
    write_gzip_json(args.output_n10, universe_n10)
    manifest = {
        "schema": "max11-sou-loop-inclusive-degree4-enumeration-v1",
        "result": "PASS",
        "command": sys.argv,
        "method": (
            "independent G-0038 nauty+pynauty census stopped at signed mass four, "
            "with recordwise comparison to the pinned degree-five stream prefix"
        ),
        "source": {
            "path": str(SOURCE.relative_to(ROOT)),
            "sha256": sha256_path(SOURCE),
        },
        "reference_comparison": reference_comparison,
        "self_test_controls": controls,
        "census": census,
        "mass_counts": {str(key): value for key, value in sorted(mass_counts.items())},
        "n11": {
            "path": str(args.output_n11),
            "records": len(universe_n11["records"]),
            "columns_with_4L": len(universe_n11["records"]) + 1,
            "sha256": sha256_path(args.output_n11),
        },
        "n10": {
            "path": str(args.output_n10),
            "records": len(universe_n10["records"]),
            "columns_with_4L": len(universe_n10["records"]) + 1,
            "sha256": sha256_path(args.output_n10),
        },
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "This enumerates the finite loop-inclusive degree-four signed-W quotient only. "
            "It does not decide MAX11 membership or establish an unrestricted depth bound."
        ),
    }
    write_json(args.manifest, manifest)
    print(canonical_bytes({
        "result": "PASS",
        "n11_records": len(universe_n11["records"]),
        "n10_records": len(universe_n10["records"]),
        "n11_sha256": sha256_path(args.output_n11),
        "n10_sha256": sha256_path(args.output_n10),
        "manifest_sha256": sha256_path(args.manifest),
    }).decode("ascii"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
