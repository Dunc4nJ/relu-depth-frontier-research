#!/usr/bin/env python3
"""Time-boxed exact G-0053-dual pricing of proper signed-mass-4 atoms.

The output is a scheduling artifact.  A price is one coordinate in a very large
quotient dual and is not itself a rank, dependence, or construction test.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import statistics
import sys
import time
from typing import Any, Hashable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0052_SCRIPT = ROOT / "artifacts/math/G-0052/mass4_full_core_census.py"
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
G0053_SCRIPT = ROOT / "artifacts/math/G-0053/mass3_dual_extension.py"
G0053_REPORT = ROOT / "artifacts/math/G-0053/mass3_dual_extension_v1.json.gz"
FILTRATION_SCRIPT = HERE / "dual_support_filtration.py"
FILTRATION_REPORT = HERE / "dual_support_filtration_v1.json.gz"
EXPECTED_G0052_SCRIPT_HASH = "435832fb62ca75981a11f3193f4546c0ca817ad7752a0636bbaeb8730cc23d51"
EXPECTED_G0052_REPORT_HASH = "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37"
EXPECTED_G0053_SCRIPT_HASH = "dac2425f18c96712e2718a5bb6706ddd04e44c8d854307befa50954b48148b9b"
EXPECTED_G0053_REPORT_HASH = "b998c750b676593c65b44adaff9fd0f72788fbe95a65aafa7499d802cda37d0d"
EXPECTED_FILTRATION_SCRIPT_HASH = "ec7da66d1ea13d388e073e33fa0e8a9441d5a919a13d4fcf71cdecc4d1f7182c"
EXPECTED_FILTRATION_REPORT_HASH = "3453aaae9422a777857e77ca8dc9ac015dbb2ad252d7535ba9b1fb698986d885"
DEFAULT_OUTPUT = HERE / "proper_mass4_pricing_schedule_v1.json.gz"
SCHEMA = "max11-g0055-proper-mass4-pricing-schedule-v1"
N = 11
EXPECTED_COUNTS = {7: 37_350, 8: 27_412, 9: 13_617, 10: 5_009}

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

THEOREM: Any = None
INDUCED: dict[int, dict[Direction, int]] = {}


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


def import_bound(name: str, path: Path, expected_hash: str) -> Any:
    if sha256_path(path) != expected_hash:
        raise ValueError(f"bound script drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compact_pair(record: dict[str, object]) -> tuple[Pair, int]:
    pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    used = sorted({vertex for branch in pair for edge in branch for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact: Pair = tuple(
        tuple((relabel[u], relabel[v]) for u, v in branch) for branch in pair
    )  # type: ignore[assignment]
    return compact, len(used)


def load_induced_maps() -> tuple[dict[int, dict[Direction, int]], int]:
    if sha256_path(FILTRATION_SCRIPT) != EXPECTED_FILTRATION_SCRIPT_HASH:
        raise ValueError("G-0055 filtration script drift")
    if sha256_path(FILTRATION_REPORT) != EXPECTED_FILTRATION_REPORT_HASH:
        raise ValueError("G-0055 filtration report drift")
    report = load_json_gz(FILTRATION_REPORT)
    denominator = int(report["frozen_dual"]["common_denominator"])
    maps: dict[int, dict[Direction, int]] = {}
    for active in range(7, 11):
        entries = report["induced_dual_by_active_support"][str(active)]["entries"]
        maps[active] = {
            tuple(map(int, entry["direction"])): int(entry["numerator"])
            for entry in entries
        }
    return maps, denominator


def init_worker(induced: dict[int, dict[Direction, int]]) -> None:
    global THEOREM, INDUCED
    g0052 = import_bound("g0055_pricing_worker_g0052", G0052_SCRIPT, EXPECTED_G0052_SCRIPT_HASH)
    THEOREM = g0052.load_theorem()
    INDUCED = induced


def price_worker(record: dict[str, object]) -> dict[str, object]:
    pair, active = compact_pair(record)
    if active not in INDUCED:
        raise AssertionError(f"worker received unsupported active count {active}")
    counter = THEOREM.permutation_t_counter_dp(pair, active)
    local_price_numerator = 0
    priced_t_key_count = 0
    priced_primitive_directions: set[Direction] = set()
    induced = INDUCED[active]
    for (base, other), multiplicity in counter.items():
        if base == other:
            continue
        direction = tuple(b - a for a, b in zip(base, other, strict=True))
        if sum(direction):
            raise AssertionError("equal-degree branch direction does not sum to zero")
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        primitive = tuple(value // divisor for value in direction)
        coefficient = induced.get(primitive, 0)
        if coefficient:
            local_price_numerator += multiplicity * divisor * coefficient
            priced_t_key_count += 1
            priced_primitive_directions.add(primitive)
    pairing_numerator = factorial(N - active) * local_price_numerator
    return {
        "sequence": int(record["sequence"]),
        "active_vertices": active,
        "total_loops": int(record["negative_loop_count"])
        + int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "pairing_numerator": pairing_numerator,
        "distinct_subset_DP_T_keys": len(counter),
        "priced_T_key_count": priced_t_key_count,
        "priced_primitive_direction_count": len(priced_primitive_directions),
    }


def read_high_active_records(theorem: Any) -> dict[int, list[dict[str, object]]]:
    groups: dict[int, list[dict[str, object]]] = {active: [] for active in EXPECTED_COUNTS}
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise ValueError("missing G-0038 stream header")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            active = int(record["active_vertices"])
            if active in groups:
                groups[active].append(record)
    observed = {active: len(records) for active, records in groups.items()}
    if observed != EXPECTED_COUNTS:
        raise AssertionError(f"high-active mass-4 census drift: {observed}")
    return groups


def evenly_spaced(records: list[dict[str, object]], count: int) -> list[dict[str, object]]:
    if count >= len(records):
        return records
    if count == 1:
        return [records[0]]
    indices = sorted({round(index * (len(records) - 1) / (count - 1)) for index in range(count)})
    return [records[index] for index in indices]


def price_records(
    records: list[dict[str, object]], workers: int, induced: dict[int, dict[Direction, int]], label: str
) -> tuple[list[dict[str, object]], float]:
    started = time.perf_counter()
    results: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with context.Pool(
        processes=workers,
        initializer=init_worker,
        initargs=(induced,),
        maxtasksperchild=256,
    ) as pool:
        for result in pool.imap(price_worker, records, chunksize=8):
            results.append(result)
            if len(results) % 1_000 == 0 or len(results) == len(records):
                print(f"G0055_PRICE {label}={len(results)}/{len(records)}", file=sys.stderr, flush=True)
    elapsed = time.perf_counter() - started
    results.sort(key=lambda item: int(item["sequence"]))
    return results, elapsed


def benchmark(
    groups: dict[int, list[dict[str, object]]], workers: int, induced: dict[int, dict[Direction, int]],
    per_active: int,
) -> dict[str, object]:
    summaries = []
    total_projection = 0.0
    for active in range(10, 6, -1):
        sample = evenly_spaced(groups[active], per_active)
        results, elapsed = price_records(sample, workers, induced, f"benchmark-a{active}")
        rate = len(results) / elapsed
        projection = len(groups[active]) / rate
        total_projection += projection
        summaries.append(
            {
                "active_vertices": active,
                "sample_count": len(results),
                "wall_seconds": elapsed,
                "records_per_second": rate,
                "projected_full_active_seconds": projection,
                "median_T_key_count": statistics.median(
                    int(result["distinct_subset_DP_T_keys"]) for result in results
                ),
            }
        )
    return {
        "workers": workers,
        "per_active": per_active,
        "by_active": summaries,
        "projected_all_high_active_seconds": total_projection,
    }


def known_sample_map(denominator: int) -> dict[int, int]:
    report = load_json_gz(G0053_REPORT)
    result: dict[int, int] = {}
    for item in report["per_record_discrepancies"]:
        if item["kind"] != "proper_sample":
            continue
        fraction = Fraction(str(item["dual_pairing"]))
        numerator = fraction * denominator
        if numerator.denominator != 1:
            raise AssertionError("G-0053 price denominator does not divide frozen denominator")
        result[int(item["sequence"])] = numerator.numerator
    if len(result) != 470:
        raise AssertionError(f"G-0053 proper sample drift: {len(result)}")
    return result


def distribution(values: list[int]) -> dict[str, object]:
    ordered = sorted(values)
    return {
        "minimum": ordered[0],
        "median": ordered[(len(ordered) - 1) // 2],
        "maximum": ordered[-1],
        "mean": str(Fraction(sum(ordered), len(ordered))),
    }


def stratum_key(result: dict[str, object]) -> tuple[int, int, int]:
    return (
        int(result["active_vertices"]),
        int(result["total_loops"]),
        int(result["abs_beta"]),
    )


def record_stratum_key(record: dict[str, object]) -> tuple[int, int, int]:
    return (
        int(record["active_vertices"]),
        int(record["negative_loop_count"]) + int(record["positive_loop_count"]),
        int(record["abs_beta"]),
    )


def select_first_stratum_blocks(
    groups: dict[int, list[dict[str, object]]], block_size: int
) -> tuple[dict[int, list[dict[str, object]]], dict[tuple[int, int, int], int]]:
    selected: dict[int, list[dict[str, object]]] = {active: [] for active in groups}
    source_counts: Counter[tuple[int, int, int]] = Counter()
    by_stratum: dict[tuple[int, int, int], list[dict[str, object]]] = defaultdict(list)
    for active_records in groups.values():
        for record in active_records:
            key = record_stratum_key(record)
            source_counts[key] += 1
            by_stratum[key].append(record)
    for key, members in sorted(by_stratum.items()):
        members.sort(key=lambda record: int(record["sequence"]))
        selected[key[0]].extend(members[:block_size])
    for active in selected:
        selected[active].sort(key=lambda record: int(record["sequence"]))
    return selected, dict(source_counts)


def summarize_and_schedule(
    results: list[dict[str, object]], block_size: int,
    source_counts: dict[tuple[int, int, int], int],
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    grouped: dict[tuple[int, int, int], list[dict[str, object]]] = defaultdict(list)
    for result in results:
        grouped[stratum_key(result)].append(result)
    rows: list[dict[str, object]] = []
    for key, members in grouped.items():
        members.sort(key=lambda item: int(item["sequence"]))
        prices = [int(member["pairing_numerator"]) for member in members]
        nonzero = [value for value in prices if value]
        divisor = 0
        for value in nonzero:
            divisor = gcd(divisor, abs(value))
        rows.append(
            {
                "stratum": list(key),
                "source_stratum_record_count": source_counts[key],
                "priced_prefix_record_count": len(members),
                "nonzero_price_count": len(nonzero),
                "zero_price_count": len(members) - len(nonzero),
                "priced_prefix_escape_fraction": str(Fraction(len(nonzero), len(members))),
                "distinct_nonzero_price_count": len(set(nonzero)),
                "gcd_nonzero_price_numerators": divisor,
                "T_key_count": distribution(
                    [int(member["distinct_subset_DP_T_keys"]) for member in members]
                ),
                "sequence_sha256": canonical_sha256(
                    [int(member["sequence"]) for member in members]
                ),
                "price_stream_sha256": canonical_sha256(
                    [[int(member["sequence"]), int(member["pairing_numerator"])] for member in members]
                ),
                "members": members,
            }
        )
    rows.sort(
        key=lambda row: (
            -int(row["stratum"][0]),
            -Fraction(str(row["priced_prefix_escape_fraction"])),
            -int(row["distinct_nonzero_price_count"]),
            int(row["T_key_count"]["median"]),
            tuple(row["stratum"]),
        )
    )
    blocks: list[dict[str, object]] = []
    public_rows: list[dict[str, object]] = []
    for rank, row in enumerate(rows, start=1):
        members = row.pop("members")
        public_row = dict(row)
        public_row["priority_rank"] = rank
        public_rows.append(public_row)
        nonzero_members = [member for member in members if int(member["pairing_numerator"])]
        zero_members = [member for member in members if not int(member["pairing_numerator"])]
        ordered_members = nonzero_members + zero_members
        if len(ordered_members) > block_size:
            raise AssertionError("selected prefix stratum exceeded one schedule block")
        sequences = [int(member["sequence"]) for member in ordered_members]
        blocks.append(
            {
                "block_id": f"A{row['stratum'][0]}-R{rank:03d}-B0001",
                "stratum_priority_rank": rank,
                "stratum": row["stratum"],
                "source_stratum_record_count": source_counts[tuple(row["stratum"])],
                "record_count": len(ordered_members),
                "nonzero_price_count": len(nonzero_members),
                "sequences": sequences,
                "sequences_sha256": canonical_sha256(sequences),
            }
        )
    return public_rows, blocks


def run(
    workers: int, benchmark_per_active: int, max_wall_seconds: float, block_size: int
) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    for path, expected in (
        (G0052_REPORT, EXPECTED_G0052_REPORT_HASH),
        (G0053_REPORT, EXPECTED_G0053_REPORT_HASH),
    ):
        if sha256_path(path) != expected:
            raise ValueError(f"bound report drift: {path}")
    if sha256_path(G0053_SCRIPT) != EXPECTED_G0053_SCRIPT_HASH:
        raise ValueError("G-0053 script drift")
    g0052 = import_bound("g0055_pricing_g0052", G0052_SCRIPT, EXPECTED_G0052_SCRIPT_HASH)
    theorem = g0052.load_theorem()
    induced, denominator = load_induced_maps()
    groups = read_high_active_records(theorem)
    selected, source_counts = select_first_stratum_blocks(groups, block_size)
    benchmark_report = benchmark(groups, workers, induced, benchmark_per_active)
    print(json.dumps({"benchmark": benchmark_report}, sort_keys=True), file=sys.stderr, flush=True)

    results: list[dict[str, object]] = []
    completed_active: list[int] = []
    active_timings = []
    census_started = time.perf_counter()
    for active in range(10, 6, -1):
        elapsed = time.perf_counter() - census_started
        benchmark_item = next(
            item
            for item in benchmark_report["by_active"]
            if int(item["active_vertices"]) == active
        )
        projected = len(selected[active]) / float(benchmark_item["records_per_second"])
        if completed_active and elapsed + projected > max_wall_seconds:
            break
        active_results, active_elapsed = price_records(
            selected[active], workers, induced, f"active-{active}-first-blocks"
        )
        results.extend(active_results)
        completed_active.append(active)
        active_timings.append(
            {
                "active_vertices": active,
                "record_count": len(active_results),
                "wall_seconds": active_elapsed,
                "records_per_second": len(active_results) / active_elapsed,
            }
        )
        if time.perf_counter() - census_started >= max_wall_seconds:
            break
    if not completed_active:
        raise RuntimeError("time box did not permit one complete active-support census")

    sample = known_sample_map(denominator)
    comparisons = 0
    for result in results:
        sequence = int(result["sequence"])
        if sequence in sample:
            comparisons += 1
            if int(result["pairing_numerator"]) != sample[sequence]:
                raise AssertionError(f"G-0053 sampled price mismatch at sequence {sequence}")

    results.sort(key=lambda item: int(item["sequence"]))
    strata, blocks = summarize_and_schedule(results, block_size, source_counts)
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "EXACT_HIGH_ACTIVE_FIRST_BLOCK_PRICING_SCHEDULE_FROZEN",
        "bindings": {
            "g0052_script_sha256": EXPECTED_G0052_SCRIPT_HASH,
            "g0052_report_sha256": EXPECTED_G0052_REPORT_HASH,
            "g0053_script_sha256": EXPECTED_G0053_SCRIPT_HASH,
            "g0053_report_sha256": EXPECTED_G0053_REPORT_HASH,
            "filtration_script_sha256": EXPECTED_FILTRATION_SCRIPT_HASH,
            "filtration_report_sha256": EXPECTED_FILTRATION_REPORT_HASH,
        },
        "time_box": {
            "requested_census_wall_seconds": max_wall_seconds,
            "benchmark": benchmark_report,
            "selection_projected_seconds_from_benchmark": sum(
                len(selected[int(item["active_vertices"])])
                / float(item["records_per_second"])
                for item in benchmark_report["by_active"]
            ),
            "completed_active_supports": completed_active,
            "unprocessed_active_supports": [
                active for active in range(10, 6, -1) if active not in completed_active
            ],
            "active_timings": active_timings,
        },
        "exact_first_block_pricing": {
            "selection_rule": (
                "For every nonempty (active_vertices,total_loops,abs_beta) stratum with "
                "active support 7 through 10, take the first min(block_size,stratum_size) "
                "records in frozen G-0038 sequence order."
            ),
            "dual_denominator": denominator,
            "record_count": len(results),
            "completed_stratum_count": len(strata),
            "nonzero_price_count": sum(bool(int(item["pairing_numerator"])) for item in results),
            "zero_price_count": sum(not int(item["pairing_numerator"]) for item in results),
            "distinct_price_numerator_count": len(
                {int(item["pairing_numerator"]) for item in results}
            ),
            "g0053_sample_prices_replayed": comparisons,
            "all_replayed_sample_prices_match": True,
            "per_record": results,
            "per_record_sha256": canonical_sha256(results),
        },
        "priority_rule": (
            "Lexicographic: active support descending; exact priced-prefix nonzero-price fraction "
            "descending; distinct nonzero prices descending; median DP T-key cost ascending; topology key. "
            "Within a stratum, nonzero-price records precede zero-price records and each class "
            "retains frozen G-0038 sequence order."
        ),
        "strata": strata,
        "block_size": block_size,
        "priority_blocks": blocks,
        "priority_blocks_sha256": canonical_sha256(blocks),
        "claim_boundary": [
            "The frozen G-0053 dual price is only one scheduling coordinate in a high-dimensional quotient dual.",
            "A nonzero price proves escape from that one annihilator identity, not linear independence or a construction.",
            "A zero price does not make a column irrelevant to hinge cancellation.",
            "The reported escape fractions are exact only for deterministic first blocks, not entire strata.",
            "Only the selected prefix blocks in active-support groups listed as completed were priced.",
        ],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "wall_seconds": time.perf_counter() - started,
        "script_sha256": script_hash_before,
    }
    scientific_payload = {
        key: report[key]
        for key in (
            "schema",
            "result",
            "bindings",
            "exact_first_block_pricing",
            "priority_rule",
            "strata",
            "block_size",
            "priority_blocks",
            "priority_blocks_sha256",
            "claim_boundary",
        )
    }
    report["canonical_scientific_payload_sha256"] = canonical_sha256(scientific_payload)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise RuntimeError("script changed during execution")
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
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--benchmark-per-active", type=int, default=32)
    parser.add_argument("--benchmark-only", action="store_true")
    parser.add_argument("--max-wall-seconds", type=float, default=600.0)
    parser.add_argument("--block-size", type=int, default=32)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.workers < 1 or args.benchmark_per_active < 1 or args.block_size < 1:
        raise SystemExit("worker, benchmark, and block counts must be positive")
    induced, _denominator = load_induced_maps()
    g0052 = import_bound("g0055_pricing_benchmark_g0052", G0052_SCRIPT, EXPECTED_G0052_SCRIPT_HASH)
    groups = read_high_active_records(g0052.load_theorem())
    if args.benchmark_only:
        print(json.dumps(benchmark(groups, args.workers, induced, args.benchmark_per_active), sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.benchmark_per_active, args.max_wall_seconds, args.block_size)
    write_gzip_atomic(output, report)
    print(json.dumps({"output": str(output), "completed_active_supports": report["time_box"]["completed_active_supports"]}, sort_keys=True))


if __name__ == "__main__":
    main()
