#!/usr/bin/env python3
"""Fail-closed verifier for the finite MAX10-derived n=11 lift test."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
ORDER_SHA = "0ca84e6b40e9aedfac0c6d294822c11c2d314a38c24c37ad3771c04af92a1d56"
MAP_REPORT_SHA = "07fb44d1f36a56d8bb180fbda5ac4701fe1f121ecfe04251d7dc2b2d8e085d49"
UNIVERSE_SHA = "8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8"
BINARY_SHA = "cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3"
SEEDS = (2_026_090_201, 2_026_090_202)
PRIMARY_PRIME = 1_000_003
SECOND_PRIME = 1_000_033
ORDER_COLUMNS = 163_740
SUBJECT_COLUMNS = 163_741
BUCKETS = 64_000
CONTROL_PIVOT_SHA = {
    9: "3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd",
    10: "13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d",
}
N9_LIFT_SOURCE_SHA = "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88"
N9_LIFT_UNIVERSE_SHA = "c22d925e66ab83ae31eb873346ef3709a17753e3b0c36fc03e2d3b12d2123cb3"
N9_LIFT_ORDER_SHA = "1b099f8040665aa4895f3989b297aa7389e725241aceebde47411d09c0653498"
N9_LIFT_MAP_SHA = "a8525ef549ac15a103935893797afa5e483c75069fe59aa62981a654545295cc"
N9_LIFT_PIVOT_SHA = "ea63faabeae00cf8414b90a4f4a655cd65169fa70569913a0676ed847fc3327f"
N9_LIFT_ORBITS = 114_814
N9_LIFT_COLUMNS = 114_815


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> Any:
    require(path.is_file(), f"missing JSON: {path}")
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def pivot_sha(columns: list[int]) -> str:
    digest = hashlib.sha256()
    for column in columns:
        require(isinstance(column, int) and 0 <= column < 1 << 64, "invalid pivot index")
        digest.update(struct.pack("<Q", column))
    return digest.hexdigest()


def command_flags(report: dict[str, Any], subcommand: str) -> dict[str, str]:
    command = report.get("command")
    require(isinstance(command, list) and len(command) >= 2, "missing command array")
    require(command[1] == subcommand, f"unexpected subcommand: {command[1:2]}")
    tail = command[2:]
    require(len(tail) % 2 == 0, "command flags are not key/value pairs")
    flags: dict[str, str] = {}
    for key, value in zip(tail[::2], tail[1::2], strict=True):
        require(isinstance(key, str) and key.startswith("--"), f"bad flag {key!r}")
        require(key not in flags, f"duplicate flag {key}")
        flags[key] = str(value)
    return flags


def verify_pivots(sketch: dict[str, Any], rank_a: int) -> str:
    pivots = sketch.get("pivot_columns")
    require(isinstance(pivots, list), "missing pivot list")
    require(len(pivots) == rank_a, "pivot count differs from rank(A)")
    require(len(set(pivots)) == rank_a, "duplicate pivot index")
    computed = pivot_sha(pivots)
    require(computed == sketch.get("pivot_columns_u64_le_sha256"), "pivot SHA mismatch")
    return computed


def verify_mapping() -> dict[str, Any]:
    order_path = BASE / "max10-lift-g0027-order.json"
    map_path = BASE / "max10-lift-map-report.json"
    require(sha256_path(order_path) == ORDER_SHA, "order file SHA")
    require(sha256_path(map_path) == MAP_REPORT_SHA, "map report SHA")
    order = load_json(order_path)
    require(isinstance(order, list) and len(order) == ORDER_COLUMNS, "order denominator")
    require(order[0] == 0, "record zero is not first")
    require(len(set(order)) == ORDER_COLUMNS, "duplicate order indices")
    require(all(isinstance(i, int) and 0 <= i < 754_017 for i in order), "order index range")
    report = load_json(map_path)
    counts = report.get("counts", {})
    require(counts.get("source_terms_denominator") == 402, "source term denominator")
    require(counts.get("raw_extensions_denominator") == 1_193_940, "raw extension denominator")
    require(counts.get("signed_W_orbits_denominator") == ORDER_COLUMNS, "orbit denominator")
    require(counts.get("mapped_signed_W_orbits_numerator") == ORDER_COLUMNS, "mapped orbit numerator")
    require(counts.get("missing_signed_W_orbits_numerator") == 0, "missing orbits")
    require(counts.get("raw_extensions_outside_loopless_universe_numerator") == 0,
            "raw extensions outside loopless universe")
    require(report.get("mapping", {}).get("order_file_sha256") == ORDER_SHA, "embedded order SHA")
    return {
        "order_file_sha256": ORDER_SHA,
        "map_report_sha256": MAP_REPORT_SHA,
        "order_columns_denominator": ORDER_COLUMNS,
    }


def verify_control(path: Path, n: int) -> dict[str, Any]:
    report = load_json(path)
    expected = {
        9: (739, 360, 361, "NON_MEMBER", 1080),
        10: (12_248, 2166, 2166, "MEMBER", 6498),
    }[n]
    columns, rank_a, rank_augmented, verdict, buckets = expected
    require(report.get("schema") == "max11-streamrank-pivots-v1", "control schema")
    require(report.get("result") == "CONTROL_PASS", "control did not pass")
    require(report.get("backend") == "cuda", "control backend")
    require(report.get("n") == n and report.get("branch_edge_occurrences") == 4,
            "control system shape")
    require(report.get("modulus") == PRIMARY_PRIME, "control prime")
    require(report.get("buckets") == buckets, "control buckets")
    require(report.get("threads") == 8, "control threads")
    require(report.get("source_column_count") == columns, "control source column count")
    require(report.get("source_columns_denominator") == columns, "control denominator")
    sketches = report.get("sketches")
    require(isinstance(sketches, list) and len(sketches) == 2, "control sketch count")
    pivot_hashes = []
    for sketch, seed in zip(sketches, SEEDS, strict=True):
        require(sketch.get("sketch", {}).get("seed") == seed, "control seed/order")
        require(sketch.get("rank_a") == rank_a, "control rank(A)")
        require(sketch.get("rank_augmented") == rank_augmented, "control augmented rank")
        require(sketch.get("verdict") == verdict, "control verdict")
        require(sketch.get("saturated") is False, "control saturation")
        computed = verify_pivots(sketch, rank_a)
        require(computed == CONTROL_PIVOT_SHA[n], "control known pivot SHA")
        separator = sketch.get("left_separator")
        if verdict == "NON_MEMBER":
            require(isinstance(separator, dict), "NON_MEMBER control separator")
            require(separator.get("verified_basis_columns_denominator") == rank_a,
                    "separator verification denominator")
        else:
            require(separator is None, "MEMBER control emitted separator")
        pivot_hashes.append(computed)
    return {
        "path": path.name,
        "sha256": sha256_path(path),
        "columns_denominator": columns,
        "rank_a": rank_a,
        "rank_augmented": rank_augmented,
        "verdict": verdict,
        "pivot_sha256": pivot_hashes,
    }


def verify_n9_lift_control() -> dict[str, Any]:
    """Verify construction custody and the same-lift n=9 -> n=10 rank arm."""
    universe_path = BASE / "n9-lift-n10-family-universe.json.gz"
    order_path = BASE / "n9-lift-n10-order.json"
    map_path = BASE / "n9-lift-n10-map-report.json"
    rank_path = BASE / "n9-lift-n10-plus5L-m64000-p1000003-s1-cuda.json"
    require(sha256_path(universe_path) == N9_LIFT_UNIVERSE_SHA, "n9 lift universe SHA")
    require(sha256_path(order_path) == N9_LIFT_ORDER_SHA, "n9 lift order SHA")
    require(sha256_path(map_path) == N9_LIFT_MAP_SHA, "n9 lift map SHA")
    order = load_json(order_path)
    require(isinstance(order, list) and len(order) == N9_LIFT_ORBITS,
            "n9 lift order denominator")
    require(order[0] == 0 and len(set(order)) == N9_LIFT_ORBITS,
            "n9 lift record-zero/uniqueness control")
    require(all(isinstance(i, int) and 0 <= i < N9_LIFT_ORBITS for i in order),
            "n9 lift order range")

    mapping = load_json(map_path)
    require(mapping.get("schema") == "max9-to-max10-lift-family-map-v1", "n9 lift map schema")
    require(mapping.get("result") == "PASS", "n9 lift map result")
    bindings = mapping.get("bindings", {})
    require(bindings.get("source_certificate_sha256") == N9_LIFT_SOURCE_SHA,
            "n9 lift source certificate SHA")
    require(bindings.get("family_universe_sha256") == N9_LIFT_UNIVERSE_SHA,
            "n9 lift embedded universe SHA")
    require(bindings.get("order_file_sha256") == N9_LIFT_ORDER_SHA,
            "n9 lift embedded order SHA")
    counts = mapping.get("counts", {})
    require(counts.get("source_terms_denominator") == 337, "n9 lift source denominator")
    require(counts.get("raw_extensions_denominator") == 667_260,
            "n9 lift raw denominator")
    require(counts.get("raw_disjoint_numerator") == 424_620,
            "n9 lift disjoint numerator")
    require(counts.get("raw_shared_distinct_numerator") == 242_640,
            "n9 lift shared numerator")
    require(counts.get("signed_W_orbits_denominator") == N9_LIFT_ORBITS,
            "n9 lift orbit denominator")
    require(counts.get("mapped_signed_W_orbits_numerator") == N9_LIFT_ORBITS,
            "n9 lift mapped numerator")
    require(counts.get("raw_extensions_outside_loopless_family_numerator") == 0,
            "n9 lift raw outside family")
    require(counts.get("signed_W_orbits_outside_loopless_family_numerator") == 0,
            "n9 lift orbits outside family")
    source_mapping = mapping.get("source_term_mapping", {})
    require(source_mapping.get("terms_denominator") == 337,
            "n9 lift mapped-term denominator")
    require(source_mapping.get("terms_with_at_least_one_orbit_numerator") == 337,
            "n9 lift mapped-term numerator")
    require(source_mapping.get("term_orbit_incidence_numerator") == 280_627,
            "n9 lift term-orbit incidence numerator")

    report = load_json(rank_path)
    require(report.get("schema") == "max11-streamrank-pivots-v1", "n9 lift rank schema")
    require(report.get("result") == "CONTROL_PASS", "n9 lift rank denominator control")
    require(report.get("backend") == "cuda", "n9 lift rank backend")
    require(report.get("n") == 10 and report.get("branch_edge_occurrences") == 5,
            "n9 lift rank system shape")
    require(report.get("modulus") == PRIMARY_PRIME, "n9 lift rank prime")
    require(report.get("buckets") == BUCKETS and report.get("threads") == 8,
            "n9 lift rank resources")
    require(report.get("input_sha256") == N9_LIFT_UNIVERSE_SHA,
            "n9 lift rank universe SHA")
    require(report.get("order_file_sha256") == N9_LIFT_ORDER_SHA,
            "n9 lift rank order SHA")
    require(report.get("source_column_count") == N9_LIFT_COLUMNS,
            "n9 lift rank source numerator")
    require(report.get("source_columns_denominator") == N9_LIFT_COLUMNS,
            "n9 lift rank source denominator")
    require(report.get("five_l_carrier") == {
        "label": "5L",
        "source_index": N9_LIFT_ORBITS,
        "exact_linear_coefficient_each_of_n_coordinates": 1_814_400,
        "coordinate_count": 10,
        "hinge_count": 0,
    }, "n9 lift 5L carrier")
    sketches = report.get("sketches")
    require(isinstance(sketches, list) and len(sketches) == 1, "n9 lift sketch count")
    sketch = sketches[0]
    require(sketch.get("sketch", {}).get("seed") == SEEDS[0], "n9 lift seed")
    require(sketch.get("rank_a") == 17_127, "n9 lift rank(A)")
    require(sketch.get("rank_augmented") == 17_127, "n9 lift augmented rank")
    require(sketch.get("verdict") == "MEMBER" and sketch.get("saturated") is False,
            "n9 lift verdict/saturation")
    require(sketch.get("left_separator") is None, "n9 lift MEMBER separator")
    require(verify_pivots(sketch, 17_127) == N9_LIFT_PIVOT_SHA, "n9 lift pivot SHA")
    return {
        "definition": "337-term MAX9 certificate, fixed [9] in [10], ordered distinct nonloop edge per branch, S_10/global-sign quotient, plus 5L",
        "source_terms_denominator": 337,
        "raw_extensions_denominator": 667_260,
        "lift_orbits_denominator": N9_LIFT_ORBITS,
        "columns_denominator": N9_LIFT_COLUMNS,
        "rank_a": 17_127,
        "rank_augmented": 17_127,
        "verdict": "MEMBER",
        "prime": PRIMARY_PRIME,
        "seed": SEEDS[0],
        "map_report_sha256": N9_LIFT_MAP_SHA,
        "rank_report_sha256": sha256_path(rank_path),
        "pivot_columns_u64_le_sha256": N9_LIFT_PIVOT_SHA,
    }


def verify_subject(path: Path) -> dict[str, Any]:
    report = load_json(path)
    require(isinstance(report, dict), "subject top-level object")
    require(report.get("schema") == "max11-streamrank-pivots-v1", "subject schema")
    # The preregistered denominator check makes streamrank label this
    # CONTROL_PASS even though no rank or verdict was supplied in advance.
    require(report.get("result") == "CONTROL_PASS", "subject denominator control")
    require(report.get("expected") == {
        "source_columns": SUBJECT_COLUMNS,
        "rank_a": None,
        "rank_augmented": None,
        "verdict": None,
        "exact_match": True,
    }, "subject expected-column record")
    require(report.get("backend") == "cuda", "subject backend")
    require(report.get("n") == 11 and report.get("branch_edge_occurrences") == 5,
            "subject system shape")
    prime = report.get("modulus")
    require(prime in {PRIMARY_PRIME, SECOND_PRIME}, "subject prime")
    require(report.get("buckets") == BUCKETS, "subject buckets")
    require(report.get("batch_size") == 1024, "subject batch size")
    require(report.get("gemm_block") == 8192, "subject GEMM block")
    require(report.get("rank_panel") == 64, "subject rank panel")
    require(report.get("threads") == 8, "subject threads")
    require(report.get("input_sha256") == UNIVERSE_SHA, "subject universe SHA")
    require(report.get("order_file_sha256") == ORDER_SHA, "subject order SHA")
    require(report.get("source_column_count") == SUBJECT_COLUMNS, "subject source column count")
    require(report.get("source_columns_denominator") == SUBJECT_COLUMNS, "subject denominator")
    require(report.get("progress", [])[-1].get("source_columns_processed") == SUBJECT_COLUMNS,
            "subject incomplete progress denominator")
    require(report.get("five_l_carrier") == {
        "label": "5L",
        "source_index": 754_017,
        "exact_linear_coefficient_each_of_n_coordinates": 18_144_000,
        "coordinate_count": 11,
        "hinge_count": 0,
    }, "subject 5L carrier")
    flags = command_flags(report, "run-universe")
    frozen = {
        "--backend": "cuda",
        "--n": "11",
        "--branch-edges": "5",
        "--modulus": str(prime),
        "--buckets": str(BUCKETS),
        "--batch-size": "1024",
        "--gemm-block": "8192",
        "--rank-panel": "64",
        "--threads": "8",
        "--include-five-l": "true",
        "--expected-columns": str(SUBJECT_COLUMNS),
    }
    for key, value in frozen.items():
        require(flags.get(key) == value, f"subject command flag {key}")
    require(not any(key.startswith("--expected-rank") or key == "--expected-verdict"
                    for key in flags), "post-result expectation in subject command")
    sketches = report.get("sketches")
    require(isinstance(sketches, list) and len(sketches) == 1, "one sequential sketch per report")
    sketch = sketches[0]
    seed = sketch.get("sketch", {}).get("seed")
    require(seed in SEEDS and flags.get("--seeds") == str(seed), "subject seed")
    rank_a = sketch.get("rank_a")
    rank_augmented = sketch.get("rank_augmented")
    require(isinstance(rank_a, int) and 0 <= rank_a < BUCKETS, "subject rank(A)")
    require(sketch.get("saturated") is False, "subject saturation")
    verdict = sketch.get("verdict")
    require(verdict in {"MEMBER", "NON_MEMBER"}, "subject verdict")
    if verdict == "MEMBER":
        require(rank_augmented == rank_a, "MEMBER rank relation")
        require(sketch.get("left_separator") is None, "MEMBER emitted separator")
    else:
        require(rank_augmented == rank_a + 1, "NON_MEMBER rank relation")
        separator = sketch.get("left_separator")
        require(isinstance(separator, dict), "NON_MEMBER separator")
        require(separator.get("verified_basis_columns_denominator") == rank_a,
                "subject separator verification denominator")
    pivot = verify_pivots(sketch, rank_a)
    return {
        "path": path.name,
        "sha256": sha256_path(path),
        "prime": prime,
        "seed": seed,
        "columns_denominator": SUBJECT_COLUMNS,
        "rank_a": rank_a,
        "rank_augmented": rank_augmented,
        "verdict": verdict,
        "saturated": False,
        "pivot_columns_u64_le_sha256": pivot,
        "wall_seconds": report.get("wall_seconds"),
        "max_rss_kib": report.get("max_rss_kib"),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--subject", type=Path, action="append", default=[])
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    result = {
        "schema": "max10-lift-test-verification-v1",
        "binary_sha256": BINARY_SHA,
        "mapping": verify_mapping(),
        "controls": [
            verify_control(BASE / "control-n10-m6498-p1000003-s1s2-cuda.json", 10),
            verify_control(BASE / "control-n9-trees-m1080-p1000003-s1s2-cuda.json", 9),
        ],
        "same_lift_known_answer_control": verify_n9_lift_control(),
        "subjects": [verify_subject(path.resolve()) for path in args.subject],
        "no_claim": (
            "This verifies finite modular report custody and internal consistency only; "
            "it does not verify an exact rational identity or unrestricted MAX11 representability."
        ),
    }
    if args.subject:
        seen = {(item["prime"], item["seed"]) for item in result["subjects"]}
        require(len(seen) == len(result["subjects"]), "duplicate prime/seed subject report")
        p1 = [item for item in result["subjects"] if item["prime"] == PRIMARY_PRIME]
        if len(p1) == 2:
            require({item["seed"] for item in p1} == set(SEEDS), "primary-prime seed coverage")
            if all(item["verdict"] == "MEMBER" for item in p1):
                p2 = [item for item in result["subjects"] if item["prime"] == SECOND_PRIME]
                require(len(p2) == 2 and {item["seed"] for item in p2} == set(SEEDS),
                        "second-prime reports required after two primary-prime MEMBER results")
    rendered = json.dumps(result, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        args.write_report.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
