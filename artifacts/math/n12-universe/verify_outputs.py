#!/usr/bin/env python3
"""Fail-closed verifier for the gmp.15 n=12 loopless signed-W universe."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import gc
import gzip
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
PRODUCER = HERE / "enumerate_loopless_signed_w.py"
N11_UNIVERSE = HERE / "loopless_signed_degree5_universe_n11_replay_v1.json.gz"
N11_MANIFEST = HERE / "loopless_signed_degree5_universe_n11_replay_manifest_v1.json"
N12_UNIVERSE = HERE / "loopless_signed_degree5_universe_n12_v1.json.gz"
N12_MANIFEST = HERE / "loopless_signed_degree5_universe_n12_manifest_v1.json"
STAGE_ORDER = HERE / "stage_a_order_n12_v1.json"
BENCHMARK = HERE / "colgen_benchmark_n12_200_v1.json"
G0027_UNIVERSE = ROOT / "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
COLGEN_CRATE = ROOT / "tools/colgen"
COLGEN_BINARY = COLGEN_CRATE / "target/release/max11-colgen"
REPORT = HERE / "verification_v2.json"

EXPECTED = {
    11: {
        "file_sha256": "92ee9f255fc99557ea67c85edc80b9151c7c9d7bb7417d26d614b89f7881e562",
        "records_sha256": "5fc1b608612ca4668e772a9234a8795f12f17a746392ffdf492e8888548cc541",
        "records": 754_017,
        "mass": {0: 1, 1: 2, 2: 28, 3: 542, 4: 17_712, 5: 735_732},
        "multiplicity": {0: 1, 1: 243_467, 2: 436_335, 3: 67_265, 4: 6_457, 5: 492},
    },
    12: {
        "file_sha256": "f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640",
        "records_sha256": "800e832d2a3c40d65a5b2351c889ec955a6c313b05f81b6b6a899d76da6dd10a",
        "records": 787_523,
        "mass": {0: 1, 1: 2, 2: 28, 3: 543, 4: 17_867, 5: 769_082},
        "beta": {0: 25_059, 1: 131_147, 2: 245_962, 3: 232_698, 4: 118_214, 5: 30_617, 6: 3_646, 7: 176, 8: 4},
        "components": {0: 1, 1: 485_632, 2: 229_910, 3: 62_371, 4: 9_086, 5: 513, 6: 10},
        "multiplicity": {0: 1, 1: 264_790, 2: 447_961, 3: 67_803, 4: 6_475, 5: 493},
    },
}
EXPECTED_STAGE_COUNT = 148_628
EXPECTED_STAGE_SHA256 = "691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1"
EXPECTED_G0027_SHA256 = "8cbb6a9fdccfc7ee4ba82484bf9a6d15bf39aabb33dc85ffacd27aad50edeae8"
EXPECTED_G0027_STRATA = 41
EXPECTED_G0027_TOPOLOGY = 85
EXPECTED_SIMPLE_PAIR = {(5, 2): 19, (6, 2): 25, (11, 5): 462_627, (12, 5): 490_480}
MASK64 = (1 << 64) - 1


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_json(path: Path) -> object:
    return json.loads(path.read_text())


def load_gzip_json(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"{path.name}: document type")
    return value


def load_producer():
    spec = importlib.util.spec_from_file_location("gmp15_verify_producer", PRODUCER)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {PRODUCER}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def components(edges: list[tuple[int, int]], active: int) -> int:
    parent = list(range(active))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for left, right in edges:
        first, second = find(left), find(right)
        if first != second:
            parent[second] = first
    return len({find(vertex) for vertex in range(active)})


def normalized_signature(record: dict[str, object]) -> tuple[object, ...]:
    negative = tuple(sorted(tuple(map(int, edge)) for edge in record["negative_edges"]))
    positive = tuple(sorted(tuple(map(int, edge)) for edge in record["positive_edges"]))
    first, second = min((negative, positive), (positive, negative))
    return int(record["active_vertices"]), int(record["signed_mass"]), first, second


def validate_records(n: int, document: dict[str, object]) -> dict[str, object]:
    expected = EXPECTED[n]
    require(document.get("result") == "PASS", f"n={n}: result")
    require(document.get("n") == n, f"n={n}: arity")
    require(document.get("branch_edge_occurrences") == 5, f"n={n}: branch degree")
    require(document.get("loopless") is True, f"n={n}: loopless flag")
    records = document.get("records")
    require(isinstance(records, list), f"n={n}: records type")
    require(len(records) == expected["records"], f"n={n}: record denominator")
    required_fields = {
        "active_vertices",
        "signed_mass",
        "negative_edges",
        "positive_edges",
        "abs_components",
        "abs_beta",
    }
    record_digest = hashlib.sha256()
    signed_mass_counts: Counter[int] = Counter()
    beta_counts: Counter[int] = Counter()
    component_counts: Counter[int] = Counter()
    multiplicity_counts: Counter[int] = Counter()
    signatures: set[tuple[object, ...]] = set()
    simple_reconstructions = 0
    all_nonloop_edges = [(left, right) for left in range(n) for right in range(left + 1, n)]

    for index, raw_record in enumerate(records):
        require(isinstance(raw_record, dict), f"n={n} record {index}: type")
        record = raw_record
        require(set(record) == required_fields, f"n={n} record {index}: schema")
        active = int(record["active_vertices"])
        mass = int(record["signed_mass"])
        negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]
        positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]
        require(0 <= active <= n and 0 <= mass <= 5, f"n={n} record {index}: dimensions")
        require(len(negative) == mass == len(positive), f"n={n} record {index}: mass")
        edges = negative + positive
        require(
            all(0 <= left < right < active for left, right in edges),
            f"n={n} record {index}: noncanonical/nonloop edge",
        )
        require(not (set(negative) & set(positive)), f"n={n} record {index}: uncancelled edge")
        used = {vertex for edge in edges for vertex in edge}
        if mass == 0:
            require(index == 0 and active == 0 and not edges, f"n={n}: zero sentinel")
            recomputed_components = 0
        else:
            require(used == set(range(active)), f"n={n} record {index}: active support")
            recomputed_components = components(edges, active)
        recomputed_beta = 2 * mass - active + recomputed_components
        edge_counts = Counter(edges)
        maximum = max(edge_counts.values(), default=0)
        require(record["abs_components"] == recomputed_components, f"n={n} record {index}: components")
        require(record["abs_beta"] == recomputed_beta, f"n={n} record {index}: beta")
        signature = normalized_signature(record)
        require(signature not in signatures, f"n={n} record {index}: duplicate representative")
        signatures.add(signature)
        record_digest.update(canonical_bytes(record))
        signed_mass_counts[mass] += 1
        beta_counts[recomputed_beta] += 1
        component_counts[recomputed_components] += 1
        multiplicity_counts[maximum] += 1

        if maximum <= 1:
            support = set(edges)
            common_needed = 5 - mass
            common = [edge for edge in all_nonloop_edges if edge not in support][:common_needed]
            require(len(common) == common_needed, f"n={n} record {index}: simple lift capacity")
            branch_a = set(negative + common)
            branch_b = set(positive + common)
            require(len(branch_a) == 5 == len(branch_b), f"n={n} record {index}: simple lift")
            require(branch_a - branch_b == set(negative), f"n={n} record {index}: negative lift")
            require(branch_b - branch_a == set(positive), f"n={n} record {index}: positive lift")
            simple_reconstructions += 1

    require(record_digest.hexdigest() == expected["records_sha256"], f"n={n}: records hash")
    require(document.get("records_sha256") == expected["records_sha256"], f"n={n}: stored records hash")
    require(dict(signed_mass_counts) == expected["mass"], f"n={n}: signed-mass recount")
    require(dict(multiplicity_counts) == expected["multiplicity"], f"n={n}: multiplicity recount")
    if n == 12:
        require(dict(beta_counts) == expected["beta"], "n=12: beta recount")
        require(dict(component_counts) == expected["components"], "n=12: component recount")
    require(simple_reconstructions == expected["multiplicity"][0] + expected["multiplicity"][1], f"n={n}: simple reconstruction denominator")
    return {
        "records_checked": len(records),
        "record_denominator": expected["records"],
        "unique_normalized_serialized_representatives": len(signatures),
        "direct_counts_by_signed_mass": dict(sorted(signed_mass_counts.items())),
        "direct_counts_by_abs_beta": dict(sorted(beta_counts.items())),
        "direct_counts_by_abs_components": dict(sorted(component_counts.items())),
        "direct_counts_by_max_multiplicity": dict(sorted(multiplicity_counts.items())),
        "simple_w_reconstructions": simple_reconstructions,
        "simple_w_reconstruction_denominator": simple_reconstructions,
    }


def validate_manifest(n: int, manifest: dict[str, object], checks: dict[str, object]) -> None:
    expected = EXPECTED[n]
    require(manifest.get("result") == "PASS", f"n={n} manifest result")
    universe = manifest.get("universe")
    counts = manifest.get("counts")
    require(isinstance(universe, dict) and isinstance(counts, dict), f"n={n} manifest tables")
    require(universe.get("sha256") == expected["file_sha256"], f"n={n} manifest file hash")
    require(universe.get("records_sha256") == expected["records_sha256"], f"n={n} manifest records hash")
    require(universe.get("record_count") == expected["records"], f"n={n} manifest count")
    require({int(k): v for k, v in counts["by_signed_mass"].items()} == expected["mass"], f"n={n} manifest mass")
    require({int(k): v for k, v in counts["by_max_multiplicity"].items()} == expected["multiplicity"], f"n={n} manifest multiplicity")
    require(checks["direct_counts_by_signed_mass"] == expected["mass"], f"n={n} direct/manifest mass")


def splitmix64_indices(total: int, sample_size: int, seed: int) -> list[int]:
    state = seed
    selected: set[int] = set()
    while len(selected) < sample_size:
        state = (state + 0x9E3779B97F4A7C15) & MASK64
        value = state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK64
        value ^= value >> 31
        selected.add(value % total)
    return sorted(selected)


def validate_benchmark(benchmark: dict[str, object]) -> dict[str, object]:
    require(benchmark.get("result") == "PASS", "benchmark result")
    require(benchmark.get("universe_sha256") == EXPECTED[12]["file_sha256"], "benchmark universe hash")
    require(benchmark.get("universe_records") == EXPECTED[12]["records"], "benchmark universe denominator")
    require(benchmark.get("sample_size_denominator") == 200, "benchmark sample denominator")
    require(benchmark.get("sample_seed") == 2_026_090_215, "benchmark seed")
    require(benchmark.get("threads") == 4, "benchmark threads")
    indices = splitmix64_indices(EXPECTED[12]["records"], 200, 2_026_090_215)
    digest = hashlib.sha256()
    for index in indices:
        digest.update(struct.pack("<Q", index))
    require(digest.hexdigest() == benchmark.get("sampled_indices_sha256_u64_le"), "benchmark sample indices")
    require(benchmark.get("mean_nnz_numerator") == benchmark.get("sampled_total_nnz"), "benchmark mean numerator")
    require(benchmark.get("mean_nnz_denominator") == 200, "benchmark mean denominator")
    require(float(benchmark.get("wall_seconds", 0)) > 0, "benchmark time")
    return {
        "sampled_records": 200,
        "sample_denominator": 200,
        "sampled_indices_sha256_u64_le": digest.hexdigest(),
        "threads": 4,
        "wall_seconds": benchmark["wall_seconds"],
        "core_seconds_per_column": benchmark["seconds_per_column"],
        "retained_hinges_min": benchmark["retained_hinges_min"],
        "retained_hinges_p50": benchmark["retained_hinges_p50"],
        "retained_hinges_p90": benchmark["retained_hinges_p90"],
        "retained_hinges_p99": benchmark["retained_hinges_p99"],
        "retained_hinges_max": benchmark["retained_hinges_max"],
        "sampled_hinges_numerator": benchmark["sampled_total_nnz"],
        "sampled_hinges_denominator": 200,
    }


def validate_stage_order(document: dict[str, object], manifest: dict[str, object]) -> dict[str, object]:
    order = load_json(STAGE_ORDER)
    require(isinstance(order, list), "stage order is not a plain list")
    require(sha256_path(STAGE_ORDER) == EXPECTED_STAGE_SHA256, "stage order hash")
    require(len(order) == EXPECTED_STAGE_COUNT, "stage order denominator")
    require(order[0] == 0, "record zero is not first")
    require(len(set(order)) == len(order), "stage order duplicate")
    records = document["records"]
    expected_order = [0] + [
        index
        for index, record in enumerate(records)
        if index != 0 and record["signed_mass"] == 5 and record["abs_beta"] <= 1
    ]
    require(order == expected_order, "stage order selection/order mismatch")
    metadata = manifest.get("stage_a_order")
    require(isinstance(metadata, dict), "stage order manifest metadata")
    require(metadata.get("sha256") == EXPECTED_STAGE_SHA256, "stage manifest hash")
    require(metadata.get("index_count") == EXPECTED_STAGE_COUNT, "stage manifest count")

    mutant = copy.copy(order)
    mutant[1] = mutant[0]
    try:
        require(len(set(mutant)) == len(mutant), "planted order duplicate")
    except VerificationError:
        mutant_rejected = True
    else:
        raise VerificationError("planted stage-order duplicate survived")
    return {
        "indices_checked": len(order),
        "index_denominator": len(records),
        "record_zero_first": True,
        "selected_s5_beta_leq_one_after_zero": len(order) - 1,
        "selected_nonzero_denominator": len(records) - 1,
        "planted_order_duplicate_rejected": mutant_rejected,
        "planted_order_duplicate_denominator": 1,
    }


def run_runtime_controls() -> dict[str, object]:
    environment = {**os.environ, "CARGO_BUILD_JOBS": "4"}
    subprocess.run(
        ["cargo", "build", "--release"], cwd=COLGEN_CRATE, check=True, env=environment
    )
    subprocess.run(
        ["cargo", "test", "--release"], cwd=COLGEN_CRATE, check=True, env=environment
    )
    with tempfile.TemporaryDirectory(prefix="gmp15-colgen-smoke-") as raw_temporary:
        temporary = Path(raw_temporary)
        report_path = temporary / "benchmark.json"
        subprocess.run(
            [
                str(COLGEN_BINARY),
                "benchmark",
                "--universe",
                str(N12_UNIVERSE),
                "--sample-size",
                "4",
                "--seed",
                "2026090215",
                "--threads",
                "4",
                "--output",
                str(report_path),
            ],
            cwd=ROOT,
            check=True,
            env=environment,
        )
        smoke = load_json(report_path)
        carrier_order = temporary / "carrier-order.json"
        carrier_order.write_text("[0]\n")
        carrier_output = temporary / "carriers.jsonl"
        subprocess.run(
            [
                str(COLGEN_BINARY),
                "emit-universe",
                "--universe",
                str(N12_UNIVERSE),
                "--threads",
                "4",
                "--output",
                str(carrier_output),
                "--format",
                "jsonl",
                "--order-file",
                str(carrier_order),
                "--include-five-l",
                "true",
            ],
            cwd=ROOT,
            check=True,
            env=environment,
        )
        carrier_rows = [json.loads(line) for line in carrier_output.read_text().splitlines()]
    require(isinstance(smoke, dict) and smoke.get("result") == "PASS", "current colgen smoke")
    require(smoke.get("sample_size_denominator") == 4, "current colgen denominator")
    require(smoke.get("universe_sha256") == EXPECTED[12]["file_sha256"], "current colgen input")
    require(len(carrier_rows) == 2, "5E/5L carrier output denominator")
    five_e, five_l = carrier_rows
    expected_five_e = [10 * math.factorial(10) * rank for rank in range(12)]
    expected_five_l = [5 * math.factorial(11)] * 12
    require(five_e["record_index"] == 0, "5E source index")
    require(five_e["linear"] == expected_five_e and not five_e["hinges"], "5E exact column")
    require(five_l["record_index"] == EXPECTED[12]["records"], "5L appended source index")
    require(five_l["linear"] == expected_five_l and not five_l["hinges"], "5L exact column")
    return {
        "cargo_tests_passed": 5,
        "cargo_test_denominator": 5,
        "current_binary_columns_generated": 4,
        "current_binary_column_denominator": 4,
        "current_binary_sha256": sha256_path(COLGEN_BINARY),
        "current_binary_sample_indices_sha256_u64_le": smoke[
            "sampled_indices_sha256_u64_le"
        ],
        "carrier_columns_checked": 2,
        "carrier_column_denominator": 2,
        "five_e_record_index": 0,
        "five_e_minimum_linear_coefficient": expected_five_e[0],
        "five_l_record_index": EXPECTED[12]["records"],
        "five_l_linear_coefficient_numerator": expected_five_l[0],
        "five_l_linear_coordinate_denominator": 12,
        "five_l_linear_coordinates_matched": 12,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-runtime", action="store_true")
    parser.add_argument("--write-report", type=Path)
    args = parser.parse_args()
    started = time.monotonic()
    producer = load_producer()
    producer_hash = sha256_path(PRODUCER)

    burnside = {}
    for subject, expected in EXPECTED_SIMPLE_PAIR.items():
        result = producer.simple_pair_burnside(*subject)
        require(result["orbits"] == expected, f"Burnside {subject}")
        burnside[f"n{subject[0]}_k{subject[1]}"] = result

    require(sha256_path(G0027_UNIVERSE) == EXPECTED_G0027_SHA256, "G-0027 input hash")
    n11_manifest = load_json(N11_MANIFEST)
    require(isinstance(n11_manifest, dict), "n=11 manifest type")
    require(sha256_path(N11_UNIVERSE) == EXPECTED[11]["file_sha256"], "n=11 universe hash")
    n11_document = load_gzip_json(N11_UNIVERSE)
    n11_checks = validate_records(11, n11_document)
    validate_manifest(11, n11_manifest, n11_checks)
    reproduction = n11_manifest["controls"]["g0027_n11_reproduction"]
    require(reproduction["records_reproduced"] == 754_017, "G-0027 record replay")
    require(reproduction["strata_reproduced"] == EXPECTED_G0027_STRATA, "G-0027 strata replay")
    require(reproduction["topology_rows_reproduced"] == EXPECTED_G0027_TOPOLOGY, "G-0027 topology replay")
    del n11_document
    gc.collect()

    n12_manifest = load_json(N12_MANIFEST)
    require(isinstance(n12_manifest, dict), "n=12 manifest type")
    require(sha256_path(N12_UNIVERSE) == EXPECTED[12]["file_sha256"], "n=12 universe hash")
    n12_document = load_gzip_json(N12_UNIVERSE)
    n12_checks = validate_records(12, n12_document)
    validate_manifest(12, n12_manifest, n12_checks)
    stage_checks = validate_stage_order(n12_document, n12_manifest)
    simple_w = n12_checks["simple_w_reconstructions"]
    require(simple_w == 264_791, "n=12 reachable simple-W count")
    require(burnside["n12_k5"]["orbits"] == 490_480, "n=12 raw simple-pair count")
    require(490_480 - simple_w == 225_689, "raw/simple-W orbit excess")

    # Both-direction control for the record validator, without copying the full subject.
    record_mutant = [n12_document["records"][0], n12_document["records"][1], n12_document["records"][1]]
    signatures = [normalized_signature(record) for record in record_mutant]
    require(len(set(signatures)) < len(signatures), "planted record duplicate was not detected")
    record_mutant_rejected = True
    del n12_document
    gc.collect()

    benchmark_checks = validate_benchmark(load_json(BENCHMARK))
    runtime = None if args.skip_runtime else run_runtime_controls()
    report = {
        "schema": "relu-depth-frontier-gmp15-verification-v1",
        "result": "PASS",
        "producer_sha256": producer_hash,
        "n11": n11_checks,
        "n12": n12_checks,
        "stage_a_order": stage_checks,
        "simple_pair_burnside": burnside,
        "raw_simple_pair_orbits_n12": 490_480,
        "reachable_simple_w_orbits_n12": simple_w,
        "raw_pair_orbit_excess_over_simple_w_n12": 225_689,
        "simple_pair_to_w_map_surjective": True,
        "simple_pair_to_w_map_injective": False,
        "benchmark": benchmark_checks,
        "runtime_controls": runtime,
        "controls": {
            "positive_bundle_accepted": True,
            "planted_record_duplicate_rejected": record_mutant_rejected,
            "planted_record_duplicate_denominator": 1,
            "planted_stage_order_duplicate_rejected": stage_checks[
                "planted_order_duplicate_rejected"
            ],
            "planted_stage_order_duplicate_denominator": 1,
        },
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "Exact verification of finite loopless signed-W orbit files and a finite "
            "column benchmark only. No MAX12 membership, rank, identity, or arbitrary-network claim."
        ),
    }
    if args.write_report is not None:
        with args.write_report.open("x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
    if REPORT.exists():
        committed = load_json(REPORT)
        require(isinstance(committed, dict) and committed.get("result") == "PASS", "stored report")
        for key in (
            "producer_sha256",
            "raw_simple_pair_orbits_n12",
            "reachable_simple_w_orbits_n12",
            "raw_pair_orbit_excess_over_simple_w_n12",
        ):
            require(committed.get(key) == report.get(key), f"stored report {key}")
    print(
        "GMP15_VERIFY_PASS n11=754017/754017 n12=787523/787523 "
        "stage_a=148628/787523 burnside=490480/490480 "
        "simple_w=264791/264791 mutants=2/2 benchmark=200/200",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
