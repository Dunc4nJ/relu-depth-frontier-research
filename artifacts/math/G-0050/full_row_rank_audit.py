#!/usr/bin/env python3
"""Hash-bound audit wrapper for the complete low-mass quotient rank run."""

from __future__ import annotations

import gzip
import hashlib
import importlib.util
import json
from math import gcd
from pathlib import Path
import sys
from typing import Any


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RAW_SCRIPT = ROOT / "artifacts/math/G-0047/low_mass_circuit_search.py"
RAW_REPORT = HERE / "full_row_rank_raw_v1.json.gz"
LEX_GATE_REPORT = ROOT / "artifacts/math/G-0048/complete_modular_gate_v1.json.gz"
EXPECTED_RAW_SCRIPT_HASH = "2c28663459755f631c44e2444be4c2540ae9772c26c542c7c9807e63eeee10fd"
EXPECTED_RAW_REPORT_HASH = "c588e92b236dd1bbdfefda9304e936d4ded72bc46e030346dc9548b24ad03251"
EXPECTED_LEX_GATE_REPORT_HASH = "5f4c51e88a26dbfa1aee53e93c140d8687df7f5a0d1033fb6912ff27812b263b"
DEFAULT_OUTPUT = HERE / "full_row_rank_audit_v1.json.gz"
SCHEMA = "max11-g0050-full-row-rank-audit-v1"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def load_search() -> Any:
    if sha256_path(RAW_SCRIPT) != EXPECTED_RAW_SCRIPT_HASH:
        raise ValueError("rank source script drift")
    spec = importlib.util.spec_from_file_location("g0050_search", RAW_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import rank source")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def direction_valid(direction: tuple[int, ...]) -> bool:
    divisor = 0
    for value in direction:
        divisor = gcd(divisor, abs(value))
    return len(direction) == 11 and sum(direction) == 0 and divisor == 1


def seed_descriptor(record: dict[str, object]) -> dict[str, object]:
    return {
        "sequence": int(record["sequence"]),
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": int(record["active_vertices"]),
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
    }


def run() -> dict[str, object]:
    script_hash_before = sha256_path(Path(__file__))
    if sha256_path(RAW_REPORT) != EXPECTED_RAW_REPORT_HASH:
        raise ValueError("raw full-row rank report drift")
    if sha256_path(LEX_GATE_REPORT) != EXPECTED_LEX_GATE_REPORT_HASH:
        raise ValueError("lex row-universe gate drift")
    raw = load_json_gz(RAW_REPORT)
    lex_gate = load_json_gz(LEX_GATE_REPORT)
    search = load_search()
    theorem = search.load_g47()
    records = search.load_records(theorem)
    universe = search.direction_universe()

    seed_directions = set()
    for record in records[-3:]:
        pair, active = search.compact_pair(record)
        _linear, hinges = theorem.primitive_normal_form(
            theorem.permutation_t_counter_dp(pair, active), active
        )
        seed_directions.update(hinges)
    selected = tuple(sorted(seed_directions)) + tuple(
        direction for direction in universe if direction not in seed_directions
    )
    selected_payload = [list(direction) for direction in selected]
    selected_hash = canonical_sha256(selected_payload)
    if selected_hash != raw["rows"]["selected_directions_sha256"]:
        raise AssertionError("seed-first row ordering hash mismatch")
    lex_payload = lex_gate["frozen_row_universe"]["directions"]
    lex_universe = tuple(tuple(map(int, direction)) for direction in lex_payload)
    if set(selected) != set(lex_universe) or len(selected) != len(lex_universe):
        raise AssertionError("raw and lex row universes differ as sets")

    expected = [(1_000_003, 488, 491, 3), (1_000_033, 488, 491, 3)]
    observed = [
        (
            int(item["prime"]),
            int(item["proper_rank"]),
            int(item["rank_with_three_full_support_seeds"]),
            int(item["seed_quotient_rank_gain"]),
        )
        for item in raw["modular_results"]
    ]
    if observed != expected:
        raise AssertionError(f"rank result drift: {observed}")
    if any(full - proper != gain for _, proper, full, gain in observed):
        raise AssertionError("rank-gain arithmetic failed")

    first_row = selected[0]
    if not direction_valid(first_row):
        raise AssertionError("first frozen row is invalid")
    first_row_mutant = (first_row[0] + 1,) + first_row[1:]
    if direction_valid(first_row_mutant):
        raise AssertionError("first-row +1 mutant was not rejected")
    rank_field_mutant_detected = all(
        full - (proper + 1) != gain for _, proper, full, gain in observed
    )
    target_gain_mutant_detected = all(gain != 2 for _, _proper, _full, gain in observed)
    if not rank_field_mutant_detected or not target_gain_mutant_detected:
        raise AssertionError("rank metadata mutant was not rejected")

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("audit script changed during run")
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "AUDITED_TWO_FIELD_FULL_ROW_SEED_QUOTIENT_GAIN_THREE",
        "script_sha256": script_hash_before,
        "bindings": {
            "rank_source_script_sha256": EXPECTED_RAW_SCRIPT_HASH,
            "raw_rank_report_sha256": EXPECTED_RAW_REPORT_HASH,
            "lex_complete_gate_report_sha256": EXPECTED_LEX_GATE_REPORT_HASH,
            "g0038_stream_sha256": raw["bindings"]["g0038_stream_sha256"],
        },
        "complete_row_universe": {
            "row_count": len(selected),
            "seed_first_directions": selected_payload,
            "seed_first_directions_sha256": selected_hash,
            "lex_directions_sha256": lex_gate["frozen_row_universe"]["directions_sha256"],
            "same_set_as_lex_complete_gate": True,
        },
        "column_census": {
            "proper_core_columns": 3307,
            "full_core_seed_columns": 3,
            "seed_descriptors": [seed_descriptor(record) for record in records[-3:]],
            "seed_descriptors_sha256": canonical_sha256(
                [seed_descriptor(record) for record in records[-3:]]
            ),
        },
        "rank_results": [
            {
                "prime": prime,
                "proper_rank": proper,
                "rank_with_three_full_support_seeds": full,
                "seed_quotient_rank_gain": gain,
            }
            for prime, proper, full, gain in observed
        ],
        "controls": {
            "first_row": list(first_row),
            "first_row_valid": True,
            "first_row_first_coordinate_plus_one_mutant": list(first_row_mutant),
            "first_row_mutant_rejected_by_zero_sum_primitive_direction_validator": True,
            "proper_rank_plus_one_metadata_mutant_rejected_by_gain_arithmetic": (
                rank_field_mutant_detected
            ),
            "target_gain_two_mutant_rejected": target_gain_mutant_detected,
        },
        "bounded_two_field_conclusion": (
            "Over F_1000003 and F_1000033, on the complete 10,065-row primitive degree-three "
            "hinge system, the three full-core signed-mass-3 seed cosets are independent modulo "
            "the span of all 3,307 proper-core signed-mass-1-through-3 columns."
        ),
        "claim_boundary": (
            "The two modular rank gains do not by themselves prove quotient gain three over Q: "
            "rank_Q of the proper block could exceed 488 while dropping modulo both primes. "
            "An exact rational upper bound rank_Q(proper)<=488 plus exact seed-coset checks is "
            "required before excluding rational signed-mass<=3 certificates."
        ),
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
    temporary.replace(path)


def main() -> None:
    report = run()
    write_gzip_atomic(DEFAULT_OUTPUT, report)
    print(json.dumps({"result": report["result"], "output": str(DEFAULT_OUTPUT)}, sort_keys=True))


if __name__ == "__main__":
    main()
