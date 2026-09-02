#!/usr/bin/env python3
"""Fail-closed verifier for EXP-0037 controls and four n=12 CUDA arms."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


BASE = Path(__file__).resolve().parent
UNIVERSE_SHA = "f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640"
ORDER_SHA = "691cb0368545f8834c98e891bbb771476e547ce9e140887c9791710a8786a7c1"
SYSTEM_SHA = {
    9: "729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991",
    10: "bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18",
}
CONTROL_PIVOT_SHA = {
    9: "3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd",
    10: "13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d",
}
PRIMES = (1_000_003, 1_000_033)
SEEDS = (2_026_090_201, 2_026_090_202)
ARM_COLUMNS = 148_629
BUCKETS = 128_000
RANK_ABORT = 100_000
SATURATION_CEILING = 127_000
RSS_ABORT_KIB = 230_686_720
GPU_ABORT_MIB = 90_000
GPU_TOTAL_MIB = 95_830
BINARY_SHA = "cdf835b269d25a37f110d72f16865e6f511d5154b5caf7808dd2eb1d82bc85c3"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def load_json(path: Path) -> dict[str, Any]:
    require(path.is_file(), f"missing JSON: {path}")
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"top-level JSON object required: {path}")
    return value


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
        require(key not in flags, f"duplicate command flag {key}")
        flags[key] = str(value)
    return flags


def verify_pivots(sketch: dict[str, Any], expected_rank: int) -> str:
    pivots = sketch.get("pivot_columns")
    require(isinstance(pivots, list), "missing pivot list")
    require(len(pivots) == expected_rank, "pivot denominator differs from rank")
    require(len(set(pivots)) == len(pivots), "duplicate pivot source index")
    computed = pivot_sha(pivots)
    require(computed == sketch.get("pivot_columns_u64_le_sha256"), "pivot SHA mismatch")
    return computed


def verify_control(path: Path, backend: str, n: int, prime: int) -> list[str]:
    report = load_json(path)
    expected = {
        9: (739, 360, 361, "NON_MEMBER", "union-trees", 1080, 256),
        10: (12_248, 2166, 2166, "MEMBER", "all", 6498, 1024),
    }[n]
    columns, rank_a, rank_aug, verdict, filter_name, buckets, cpu_batch = expected
    batch = 1024 if backend == "cuda" and n == 10 else cpu_batch
    require(report.get("schema") == "max11-streamrank-pivots-v1", "control schema")
    require(report.get("result") == "CONTROL_PASS", "known-answer control did not pass")
    require(report.get("backend") == backend, "control backend mismatch")
    require(report.get("n") == n, "control n mismatch")
    require(report.get("branch_edge_occurrences") == 4, "control branch degree")
    require(report.get("modulus") == prime, "control prime")
    require(report.get("buckets") == buckets, "control bucket count")
    require(report.get("batch_size") == batch, "control batch size")
    require(report.get("gemm_block") == 1024, "control GEMM block")
    require(report.get("rank_panel") == 64, "control rank panel")
    expected_threads = 6 if backend == "cpu" else 60
    require(report.get("threads") == expected_threads, "control thread count")
    require(report.get("input_sha256") == SYSTEM_SHA[n], "control input SHA")
    require(report.get("source_column_count") == columns, "control source columns")
    require(report.get("source_columns_denominator") == columns, "control column denominator")
    require(report.get("expected") == {
        "source_columns": columns,
        "rank_a": rank_a,
        "rank_augmented": rank_aug,
        "verdict": verdict,
        "exact_match": True,
    }, "control expectation record")
    flags = command_flags(report, "run-saved")
    require(flags.get("--backend") == backend, "control command backend")
    require(flags.get("--filter") == filter_name, "control command filter")
    require(flags.get("--modulus") == str(prime), "control command prime")
    require(flags.get("--threads") == str(expected_threads), "control command threads")
    sketches = report.get("sketches")
    require(isinstance(sketches, list) and len(sketches) == 2, "control sketch count")
    hashes = []
    for item, seed in zip(sketches, SEEDS, strict=True):
        require(item["sketch"]["seed"] == seed, "control seed/order")
        require(item.get("rank_a") == rank_a, "control rank(A)")
        require(item.get("rank_augmented") == rank_aug, "control augmented rank")
        require(item.get("verdict") == verdict, "control verdict")
        require(item.get("saturated") is False, "control saturation")
        computed = verify_pivots(item, rank_a)
        require(computed == CONTROL_PIVOT_SHA[n], "control canonical pivot SHA")
        if n == 9:
            separator = item.get("left_separator")
            require(isinstance(separator, dict), "n=9 separator missing")
            require(separator.get("verified_basis_columns_denominator") == rank_a,
                    "n=9 separator verification denominator")
        else:
            require(item.get("left_separator") is None, "MEMBER control emitted separator")
        hashes.append(computed)
    return hashes


def verify_control_mutant(path: Path) -> None:
    report = load_json(path)
    require(report.get("result") == "CONTROL_FAIL", "planted rank mutant was accepted")
    require(report.get("expected", {}).get("rank_a") == 359, "mutant was not the frozen defect")
    require(report.get("expected", {}).get("exact_match") is False, "mutant exact_match")
    require(len(report.get("sketches", [])) == 1, "mutant sketch count")
    item = report["sketches"][0]
    require(item["sketch"]["seed"] == SEEDS[0], "mutant seed")
    require(item.get("rank_a") == 360 and item.get("rank_augmented") == 361,
            "mutant changed actual known answer")
    require(item.get("verdict") == "NON_MEMBER", "mutant actual verdict")
    verify_pivots(item, 360)


def parse_telemetry(path: Path) -> tuple[int, int, int]:
    require(path.is_file(), f"missing telemetry: {path}")
    rows = 0
    max_gpu = 0
    max_rss = 0
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        require(reader.fieldnames == [
            "timestamp_utc", "gpu_used_mib", "gpu_total_mib",
            "gpu_util_percent", "process_rss_kib",
        ], "telemetry schema")
        for row in reader:
            rows += 1
            gpu = int(row["gpu_used_mib"].strip())
            total = int(row["gpu_total_mib"].strip())
            rss = int(row["process_rss_kib"].strip())
            require(total == GPU_TOTAL_MIB, "GPU total changed")
            max_gpu = max(max_gpu, gpu)
            max_rss = max(max_rss, rss)
    require(rows > 0, "empty telemetry")
    require(max_gpu < GPU_ABORT_MIB, "external GPU gate should have aborted")
    require(max_rss < RSS_ABORT_KIB, "external RSS gate should have aborted")
    return rows, max_gpu, max_rss


def verify_arm(path: Path, prime: int, seed: int) -> dict[str, Any]:
    report = load_json(path)
    require(report.get("schema") == "max11-streamrank-pivots-v1", "arm schema")
    require(report.get("result") == "OBSERVATION", "arm is not an observation")
    require(report.get("backend") == "cuda", "arm backend")
    require(report.get("n") == 12, "arm n")
    require(report.get("branch_edge_occurrences") == 5, "arm branch degree")
    require(report.get("modulus") == prime, "arm prime")
    require(report.get("buckets") == BUCKETS, "arm buckets")
    require(report.get("batch_size") == 1024, "arm batch size")
    require(report.get("gemm_block") == 8192, "arm GEMM block")
    require(report.get("rank_panel") == 64, "arm rank panel")
    require(report.get("threads") == 60, "arm threads")
    require(report.get("input_sha256") == UNIVERSE_SHA, "arm universe SHA")
    require(report.get("order_file_sha256") == ORDER_SHA, "arm order SHA")
    require(report.get("source_column_count") == ARM_COLUMNS, "arm source columns")
    require(report.get("source_columns_denominator") == ARM_COLUMNS, "arm denominator")
    require(report.get("max_rss_kib", RSS_ABORT_KIB) < RSS_ABORT_KIB, "arm RSS gate")
    require(report.get("progress", [])[-1]["source_columns_processed"] == ARM_COLUMNS,
            "arm did not process full denominator")
    carrier = report.get("five_l_carrier")
    require(carrier == {
        "label": "5L",
        "source_index": 787_523,
        "exact_linear_coefficient_each_of_n_coordinates": 199_584_000,
        "coordinate_count": 12,
        "hinge_count": 0,
    }, "arm 5L carrier")
    flags = command_flags(report, "run-universe")
    frozen_flags = {
        "--backend": "cuda", "--n": "12", "--branch-edges": "5",
        "--modulus": str(prime), "--buckets": str(BUCKETS),
        "--seeds": str(seed), "--batch-size": "1024",
        "--gemm-block": "8192", "--rank-panel": "64", "--threads": "60",
        "--include-five-l": "true", "--abort-rank-above": str(RANK_ABORT),
        "--abort-rss-kib-above": str(RSS_ABORT_KIB),
    }
    for key, value in frozen_flags.items():
        require(flags.get(key) == value, f"arm command flag {key}")
    require(not any(key.startswith("--expected-") for key in flags), "post-result expectation")
    sketches = report.get("sketches")
    require(isinstance(sketches, list) and len(sketches) == 1, "arm sketch count")
    item = sketches[0]
    require(item["sketch"]["seed"] == seed, "arm seed")
    rank_a = item.get("rank_a")
    rank_aug = item.get("rank_augmented")
    require(isinstance(rank_a, int) and rank_a <= RANK_ABORT, "arm rank gate")
    require(rank_a <= SATURATION_CEILING, "arm saturation ceiling")
    require(item.get("saturated") is False, "arm reports saturated")
    verdict = item.get("verdict")
    require(verdict in {"MEMBER", "NON_MEMBER"}, "arm verdict")
    if verdict == "MEMBER":
        require(rank_aug == rank_a, "MEMBER rank relation")
        require(item.get("left_separator") is None, "MEMBER emitted separator")
    else:
        require(rank_aug == rank_a + 1, "NON_MEMBER rank relation")
        separator = item.get("left_separator")
        require(isinstance(separator, dict), "NON_MEMBER separator missing")
        require(separator.get("verified_basis_columns_denominator") == rank_a,
                "NON_MEMBER separator denominator")
    computed = verify_pivots(item, rank_a)
    gpu_peak = item.get("reducer_metrics", {}).get("gpu_peak_allocated_bytes")
    require(isinstance(gpu_peak, int) and gpu_peak < GPU_ABORT_MIB * 1024 * 1024,
            "reported GPU allocation exceeds gate")
    telemetry_path = path.with_suffix(".telemetry.csv")
    telemetry_rows, telemetry_gpu, telemetry_rss = parse_telemetry(telemetry_path)
    require(not path.with_suffix(".external-gate.txt").exists(), "external gate fired")
    for suffix in (".stdout.log", ".stderr.log", ".supervisor.log"):
        require(path.with_suffix(suffix).is_file(), f"missing arm log {suffix}")
    return {
        "file": path.name,
        "file_sha256": sha256_path(path),
        "prime": prime,
        "seed": seed,
        "rank_a": rank_a,
        "rank_augmented": rank_aug,
        "verdict": verdict,
        "pivot_columns_u64_le_sha256": computed,
        "wall_seconds": report.get("wall_seconds"),
        "max_rss_kib": report.get("max_rss_kib"),
        "gpu_peak_allocated_bytes": gpu_peak,
        "telemetry_rows": telemetry_rows,
        "telemetry_max_gpu_used_mib": telemetry_gpu,
        "telemetry_max_process_rss_kib": telemetry_rss,
    }


def expect_rejection(function: Any, *args: Any) -> None:
    try:
        function(*args)
    except AssertionError:
        return
    raise AssertionError("planted in-memory mutation was accepted")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", type=Path)
    parser.add_argument("--controls-only", action="store_true")
    parser.add_argument("--one-arm", nargs=2, type=int, metavar=("PRIME", "SEED"))
    args = parser.parse_args()
    require(not (args.controls_only and args.one_arm), "choose one verification mode")

    binary_line = (BASE / "controls/binary.sha256").read_text(encoding="utf-8").strip()
    binary_parts = binary_line.split()
    require(len(binary_parts) == 2, "binary SHA record")
    require(binary_parts[1] == "tools/streamrank/target/release/max11-streamrank",
            "binary path record")
    require(binary_parts[0] == BINARY_SHA, "binary SHA record")

    control_files: dict[str, str] = {}
    comparisons = 0
    for n in (10, 9):
        for prime in PRIMES:
            by_backend = {}
            for backend in ("cpu", "cuda"):
                path = BASE / f"controls/{backend}-n{n}-p{prime}.json"
                by_backend[backend] = verify_control(path, backend, n, prime)
                control_files[str(path.relative_to(BASE))] = sha256_path(path)
            require(by_backend["cpu"] == by_backend["cuda"],
                    f"CPU/CUDA pivot mismatch n={n} p={prime}")
            comparisons += len(SEEDS)
    mutant_path = BASE / "controls/cuda-n9-p1000003-mutant-expected-rank359.json"
    verify_control_mutant(mutant_path)
    control_files[str(mutant_path.relative_to(BASE))] = sha256_path(mutant_path)

    if args.controls_only:
        print(
            "EXP0037_CONTROLS_PASS "
            f"reports=8/8 pivots={comparisons}/8 planted_mutant=1/1"
        )
        return

    if args.one_arm:
        prime, seed = args.one_arm
        require(prime in PRIMES, "unregistered arm prime")
        require(seed in SEEDS, "unregistered arm seed")
        path = BASE / f"n12-stageA-m128000-p{prime}-s{seed}-cuda.json"
        print(json.dumps(verify_arm(path, prime, seed), sort_keys=True))
        return

    arms = []
    raw_arms = []
    for prime in PRIMES:
        for seed in SEEDS:
            path = BASE / f"n12-stageA-m128000-p{prime}-s{seed}-cuda.json"
            raw = load_json(path)
            raw_arms.append((raw, path, prime, seed))
            arms.append(verify_arm(path, prime, seed))
    verdicts = {arm["verdict"] for arm in arms}
    aggregate = next(iter(verdicts)) if len(verdicts) == 1 else "DISAGREE"

    bad_control = copy.deepcopy(raw_arms[0][0])
    bad_control["threads"] = 59
    mutant_tmp = BASE / raw_arms[0][1].name
    original_load = globals()["load_json"]
    globals()["load_json"] = lambda path: bad_control if path == mutant_tmp else original_load(path)
    try:
        expect_rejection(verify_arm, mutant_tmp, raw_arms[0][2], raw_arms[0][3])
    finally:
        globals()["load_json"] = original_load

    bad_pivot = copy.deepcopy(raw_arms[0][0])
    bad_pivot["sketches"][0]["pivot_columns_u64_le_sha256"] = "0" * 64
    globals()["load_json"] = lambda path: bad_pivot if path == mutant_tmp else original_load(path)
    try:
        expect_rejection(verify_arm, mutant_tmp, raw_arms[0][2], raw_arms[0][3])
    finally:
        globals()["load_json"] = original_load

    report = {
        "schema": "exp0037-n12-stageA-verification-v1",
        "result": "PASS",
        "binary_sha256": binary_parts[0],
        "control_systems": 2,
        "control_primes": 2,
        "control_seeds": 2,
        "cpu_cuda_pivot_comparisons_numerator": comparisons,
        "cpu_cuda_pivot_comparisons_denominator": 8,
        "known_answer_reports_numerator": 8,
        "known_answer_reports_denominator": 8,
        "planted_file_mutants_rejected_numerator": 1,
        "planted_file_mutants_rejected_denominator": 1,
        "planted_verifier_mutants_rejected_numerator": 2,
        "planted_verifier_mutants_rejected_denominator": 2,
        "control_file_sha256": control_files,
        "arms_completed_numerator": len(arms),
        "arms_completed_denominator": 4,
        "aggregate_modular_sketch_verdict": aggregate,
        "arms": arms,
        "no_claim": (
            "Four finite modular sketches do not establish exact-Q consistency or verify "
            "MAX_12 on every real row; NON_MEMBER would concern only the registered finite family."
        ),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.write_report:
        args.write_report.write_text(encoded, encoding="utf-8")
    else:
        stored = BASE / "verification.json"
        if stored.is_file():
            require(load_json(stored) == report, "stored verification report differs")
    print(
        "EXP0037_VERIFY_PASS "
        f"controls=8/8 pivots={comparisons}/8 arms={len(arms)}/4 "
        f"mutants=3/3 aggregate={aggregate}"
    )


if __name__ == "__main__":
    main()
