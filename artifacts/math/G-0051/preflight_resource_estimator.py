#!/usr/bin/env python3
"""Fail-closed resource preflight for the signed-mass <= 4 quotient gate.

This program does not run the quotient computation.  It certifies the frozen
column census, constructs the complete degree-four primitive-direction
universe, reports dense resource bounds, and optionally benchmarks at most
eight deterministically hash-selected mass-four columns per active-support
stratum.  The hard sample cap prevents this preflight from silently becoming
the large experiment it is meant to precede.

No-claim: a sample benchmark, a row sketch, or modular rank agreement is not a
MAX11 identity or a bounded impossibility theorem.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import gzip
import hashlib
import heapq
import importlib.util
import json
import os
from pathlib import Path
import platform
import shutil
import statistics
import sys
import time
from types import ModuleType
from typing import Any, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
MANIFEST = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_manifest_v1.json"
)
STREAM = ROOT / (
    "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
)
LOW_SEARCH = ROOT / "artifacts/math/G-0047/low_mass_circuit_search.py"
EXACT_Q_REPORT = ROOT / "artifacts/math/G-0050/exact_q_bridge_v1.json.gz"

EXPECTED_MANIFEST_SHA256 = (
    "1d6d7ce58c4302b899e922939030706428c54870d32cc5b0e60f43e2c25ee640"
)
EXPECTED_STREAM_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_LOW_SEARCH_SHA256 = (
    "2c28663459755f631c44e2444be4c2540ae9772c26c542c7c9807e63eeee10fd"
)
EXPECTED_EXACT_Q_REPORT_SHA256 = (
    "64d49d39595842187d90caf114d7940f830cb5287e518adbb52110a983dce73b"
)

EXPECTED_DEGREE3_ROWS = 10_065
EXPECTED_DEGREE4_ROWS = 99_858
EXPECTED_MASS4_BY_ACTIVE = {
    2: 7,
    3: 259,
    4: 3_131,
    5: 14_491,
    6: 31_452,
    7: 37_350,
    8: 27_412,
    9: 13_617,
    10: 5_009,
    11: 1_465,
}
EXPECTED_PROPER_THROUGH_MASS4 = 136_035
EXPECTED_FULL_THROUGH_MASS4 = 1_468
EXPECTED_LOW_PROPER_BASIS = 488
EXPECTED_REDUCED_COLUMNS = 134_684
MAX_SAMPLE_PER_STRATUM = 8
SCHEMA = "max11-g0051-mass4-resource-preflight-v1"


class PreflightError(RuntimeError):
    """Fail-closed input or semantic mismatch."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        return json.load(source)


def load_low_search() -> ModuleType:
    observed = sha256_path(LOW_SEARCH)
    if observed != EXPECTED_LOW_SEARCH_SHA256:
        raise PreflightError(
            f"low-search drift: {observed} != {EXPECTED_LOW_SEARCH_SHA256}"
        )
    spec = importlib.util.spec_from_file_location("g0051_low_search", LOW_SEARCH)
    if spec is None or spec.loader is None:
        raise PreflightError("cannot import frozen low-mass semantic generator")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def input_gate() -> tuple[dict[str, Any], dict[str, Any], list[int]]:
    bindings = {
        "manifest_sha256": sha256_path(MANIFEST),
        "stream_sha256": sha256_path(STREAM),
        "low_search_sha256": sha256_path(LOW_SEARCH),
        "exact_q_report_sha256": sha256_path(EXACT_Q_REPORT),
    }
    expected = {
        "manifest_sha256": EXPECTED_MANIFEST_SHA256,
        "stream_sha256": EXPECTED_STREAM_SHA256,
        "low_search_sha256": EXPECTED_LOW_SEARCH_SHA256,
        "exact_q_report_sha256": EXPECTED_EXACT_Q_REPORT_SHA256,
    }
    if bindings != expected:
        raise PreflightError(f"binding drift: observed={bindings}, expected={expected}")

    with MANIFEST.open("r", encoding="utf-8") as source:
        manifest = json.load(source)
    if manifest["stream"]["compressed_sha256"] != EXPECTED_STREAM_SHA256:
        raise PreflightError("manifest does not bind the frozen stream")
    if int(manifest["stream"]["record_count"]) != 7_015_841:
        raise PreflightError("complete G-0038 record census drift")

    exact_q = load_json_gz(EXACT_Q_REPORT)
    if exact_q.get("result") != "EXACT_Q_PROPER_RANK_488_AND_THREE_SEED_QUOTIENT_RANK_3":
        raise PreflightError("G-0050 exact-Q bridge is not favorable/frozen")
    basis = list(
        map(
            int,
            exact_q["fixed_exact_basis"]["proper_basis_column_indices"],
        )
    )
    if len(basis) != EXPECTED_LOW_PROPER_BASIS or len(set(basis)) != len(basis):
        raise PreflightError("G-0050 proper-basis census drift")
    if not all(0 <= value < 3_307 for value in basis):
        raise PreflightError("G-0050 proper-basis index outside frozen prefix")
    return manifest, exact_q, basis


def stratum_census(manifest: dict[str, Any]) -> dict[str, Any]:
    mass4 = {
        int(row["active_vertices"]): int(row["record_count"])
        for row in manifest["stream"]["strata"]
        if int(row["signed_mass"]) == 4 and int(row["record_count"])
    }
    if mass4 != EXPECTED_MASS4_BY_ACTIVE:
        raise PreflightError(f"mass-four stratum drift: {mass4}")
    proper = sum(
        int(row["record_count"])
        for row in manifest["stream"]["strata"]
        if 1 <= int(row["signed_mass"]) <= 4
        and int(row["active_vertices"]) < 11
    )
    full = sum(
        int(row["record_count"])
        for row in manifest["stream"]["strata"]
        if 1 <= int(row["signed_mass"]) <= 4
        and int(row["active_vertices"]) == 11
    )
    if proper != EXPECTED_PROPER_THROUGH_MASS4 or full != EXPECTED_FULL_THROUGH_MASS4:
        raise PreflightError(f"proper/full census drift: {(proper, full)}")
    reduced = sum(EXPECTED_MASS4_BY_ACTIVE.values()) + EXPECTED_LOW_PROPER_BASIS + 3
    if reduced != EXPECTED_REDUCED_COLUMNS:
        raise PreflightError(f"reduced-column arithmetic drift: {reduced}")
    return {
        "mass4_by_active_vertices": {str(key): value for key, value in mass4.items()},
        "proper_columns_signed_mass_1_through_4": proper,
        "full_columns_signed_mass_1_through_4": full,
        "literal_columns_signed_mass_1_through_4": proper + full,
        "exact_span_equivalent_reduced_columns": reduced,
        "reduction": (
            "replace all 3,307 signed-mass<=3 proper columns by the frozen exact-Q "
            "488-column G-0050 basis; retain the three old full-support seeds and "
            "every signed-mass-4 record"
        ),
    }


def row_universe(low: ModuleType) -> tuple[dict[str, Any], tuple[tuple[int, ...], ...]]:
    started = time.perf_counter()
    degree3 = low.direction_universe(11, 3)
    degree4 = low.direction_universe(11, 4)
    seconds = time.perf_counter() - started
    degree3_set = set(degree3)
    degree4_set = set(degree4)
    if len(degree3) != EXPECTED_DEGREE3_ROWS:
        raise PreflightError(f"degree-three row drift: {len(degree3)}")
    if len(degree4) != EXPECTED_DEGREE4_ROWS:
        raise PreflightError(f"degree-four row drift: {len(degree4)}")
    if not degree3_set <= degree4_set:
        raise PreflightError("degree-three primitive directions do not embed in degree four")
    support_histogram = Counter(sum(value != 0 for value in row) for row in degree4)
    expected_support = {3: 825, 4: 8_250, 5: 28_182, 6: 38_346, 7: 20_790, 8: 3_465}
    if support_histogram != Counter(expected_support):
        raise PreflightError(f"degree-four support histogram drift: {support_histogram}")
    return (
        {
            "degree3_rows": len(degree3),
            "degree4_rows": len(degree4),
            "new_rows_beyond_degree3": len(degree4_set - degree3_set),
            "degree3_is_subset_of_degree4": True,
            "degree3_rows_sha256": canonical_sha256([list(row) for row in degree3]),
            "degree4_rows_sha256": canonical_sha256([list(row) for row in degree4]),
            "degree4_support_histogram": {
                str(key): value for key, value in sorted(support_histogram.items())
            },
            "generation_seconds": seconds,
        },
        degree4,
    )


def bytes_record(rows: int, columns: int) -> dict[str, Any]:
    int64_bytes = rows * columns * 8
    uint32_bytes = rows * columns * 4
    return {
        "shape": [rows, columns],
        "int64_bytes": int64_bytes,
        "int64_decimal_gb": int64_bytes / 1e9,
        "int64_gib": int64_bytes / (1 << 30),
        "one_prime_uint32_bytes": uint32_bytes,
        "one_prime_uint32_decimal_gb": uint32_bytes / 1e9,
        "one_prime_uint32_gib": uint32_bytes / (1 << 30),
    }


def resource_table() -> dict[str, Any]:
    rows = EXPECTED_DEGREE4_ROWS
    stages = {
        "s4_full_only": 1_465,
        "all_full_plus_g0050_proper_basis": 1_956,
        "then_all_s4_active10_proper": 6_965,
        "then_all_s4_active9_proper": 20_582,
        "complete_span_equivalent_reduced_subject": EXPECTED_REDUCED_COLUMNS,
        "literal_complete_subject": (
            EXPECTED_PROPER_THROUGH_MASS4 + EXPECTED_FULL_THROUGH_MASS4
        ),
    }
    return {name: bytes_record(rows, columns) for name, columns in stages.items()}


def host_resources() -> dict[str, Any]:
    meminfo: dict[str, int] = {}
    with Path("/proc/meminfo").open("r", encoding="utf-8") as source:
        for line in source:
            key, raw = line.split(":", 1)
            value = int(raw.strip().split()[0]) * 1024
            meminfo[key] = value
    disk = shutil.disk_usage(ROOT)
    return {
        "logical_cpus": os.cpu_count(),
        "memory_total_bytes": meminfo.get("MemTotal"),
        "memory_available_bytes": meminfo.get("MemAvailable"),
        "swap_total_bytes": meminfo.get("SwapTotal"),
        "project_filesystem_total_bytes": disk.total,
        "project_filesystem_free_bytes": disk.free,
    }


def hash_selected_mass4(sample_per_stratum: int) -> list[dict[str, Any]]:
    heaps: dict[int, list[tuple[int, int, dict[str, Any]]]] = defaultdict(list)
    seen = Counter()
    with gzip.open(STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise PreflightError("G-0038 stream header missing")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass > 4:
                break
            if signed_mass != 4:
                continue
            active = int(record["active_vertices"])
            seen[active] += 1
            key = int.from_bytes(hashlib.sha256(canonical_bytes(record)).digest(), "big")
            item = (-key, int(record["sequence"]), record)
            heap = heaps[active]
            if len(heap) < sample_per_stratum:
                heapq.heappush(heap, item)
            elif key < -heap[0][0]:
                heapq.heapreplace(heap, item)
    if dict(seen) != EXPECTED_MASS4_BY_ACTIVE:
        raise PreflightError(f"streamed mass-four census drift: {dict(seen)}")
    selected = []
    for active in sorted(heaps):
        for negative_key, sequence, record in heaps[active]:
            selected.append(
                {
                    "active_vertices": active,
                    "selection_sha256": f"{-negative_key:064x}",
                    "sequence": sequence,
                    "record": record,
                }
            )
    return sorted(
        selected,
        key=lambda item: (
            int(item["active_vertices"]),
            str(item["selection_sha256"]),
            int(item["sequence"]),
        ),
    )


def benchmark_columns(
    low: ModuleType,
    degree4: tuple[tuple[int, ...], ...],
    sample_per_stratum: int,
) -> dict[str, Any]:
    if not 1 <= sample_per_stratum <= MAX_SAMPLE_PER_STRATUM:
        raise PreflightError(
            f"sample-per-stratum must lie in 1..{MAX_SAMPLE_PER_STRATUM}"
        )
    selection_started = time.perf_counter()
    selected = hash_selected_mass4(sample_per_stratum)
    selection_seconds = time.perf_counter() - selection_started
    index = {direction: row for row, direction in enumerate(degree4)}
    low.init_worker(index)
    observations = []
    generation_started = time.perf_counter()
    for item in selected:
        started = time.perf_counter()
        sequence, active, sparse, invariant = low.column_worker(item["record"])
        seconds = time.perf_counter() - started
        if sequence != int(item["sequence"]) or active != int(item["active_vertices"]):
            raise PreflightError("sample descriptor/semantic result mismatch")
        if any(not value for _row, value in sparse):
            raise PreflightError("semantic worker emitted an explicit zero")
        if [row for row, _value in sparse] != sorted({row for row, _value in sparse}):
            raise PreflightError("semantic worker emitted duplicate or unsorted rows")
        support_histogram = Counter(
            sum(value != 0 for value in degree4[row]) for row, _value in sparse
        )
        observations.append(
            {
                "active_vertices": active,
                "selection_sha256": item["selection_sha256"],
                "sequence": sequence,
                "nonzeros": len(sparse),
                "density": len(sparse) / EXPECTED_DEGREE4_ROWS,
                "maximum_absolute_entry": max((abs(value) for _row, value in sparse), default=0),
                "row_support_histogram": {
                    str(key): value for key, value in sorted(support_histogram.items())
                },
                "eleventh_binary_difference": invariant,
                "generation_seconds": seconds,
            }
        )
    generation_seconds = time.perf_counter() - generation_started

    summaries: dict[str, Any] = {}
    estimated_nonzeros = 0.0
    estimated_single_worker_seconds = 0.0
    for active, count in EXPECTED_MASS4_BY_ACTIVE.items():
        rows = [item for item in observations if item["active_vertices"] == active]
        nonzeros = [int(item["nonzeros"]) for item in rows]
        seconds = [float(item["generation_seconds"]) for item in rows]
        mean_nonzeros = statistics.fmean(nonzeros)
        mean_seconds = statistics.fmean(seconds)
        estimated_nonzeros += count * mean_nonzeros
        estimated_single_worker_seconds += count * mean_seconds
        summaries[str(active)] = {
            "stratum_columns": count,
            "sample_columns": len(rows),
            "nonzeros_minimum": min(nonzeros),
            "nonzeros_median": statistics.median(nonzeros),
            "nonzeros_maximum": max(nonzeros),
            "nonzeros_mean": mean_nonzeros,
            "seconds_minimum": min(seconds),
            "seconds_median": statistics.median(seconds),
            "seconds_maximum": max(seconds),
            "seconds_mean": mean_seconds,
        }
    return {
        "selection": (
            "the lexicographically smallest SHA-256 values of canonical records within each "
            "mass-four active-support stratum; fixed before semantic generation"
        ),
        "selection_seconds": selection_seconds,
        "semantic_generation_seconds": generation_seconds,
        "observations": observations,
        "stratum_summaries": summaries,
        "planning_extrapolation_not_a_bound": {
            "estimated_mass4_nonzeros": estimated_nonzeros,
            "estimated_csc_bytes_row_u32_value_i64": (
                estimated_nonzeros * 12 + (sum(EXPECTED_MASS4_BY_ACTIVE.values()) + 1) * 8
            ),
            "estimated_csc_bytes_row_u32_value_u32_one_prime": (
                estimated_nonzeros * 8 + (sum(EXPECTED_MASS4_BY_ACTIVE.values()) + 1) * 8
            ),
            "estimated_single_worker_generation_seconds": estimated_single_worker_seconds,
            "idealized_eight_worker_generation_seconds": estimated_single_worker_seconds / 8,
            "warning": (
                "Hash-selected samples measure planning scale only. They are neither upper "
                "bounds nor evidence about quotient rank."
            ),
        },
    }


def self_test() -> dict[str, Any]:
    from flint import nmod_mat

    prime = 1_000_003
    identity = nmod_mat(2, 2, [1, 0, 0, 1], prime)
    identity_augmented = nmod_mat(3, 2, [1, 0, 0, 1, 1, 1], prime)
    if int(identity.rank()) != 2 or int(identity_augmented.rank()) != 2:
        raise AssertionError("full-column-rank negative control failed")
    hinge = nmod_mat(1, 2, [1, 1], prime)
    hinge_augmented = nmod_mat(2, 2, [1, 1, 1, 0], prime)
    if int(hinge.rank()) != 1 or int(hinge_augmented.rank()) != 2:
        raise AssertionError("rank-gain positive control failed")
    if (1 - 1) % prime or (1 * 1 + 0 * (-1)) % prime != 1:
        raise AssertionError("planted circuit replay failed")
    return {
        "result": "PASS",
        "full_column_rank_excludes_a_circuit": True,
        "augmented_row_rank_gain_detects_planted_nonzero_lambda_circuit": True,
        "hard_sample_cap": MAX_SAMPLE_PER_STRATUM,
    }


def build_report(sample_per_stratum: int) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    manifest, _exact_q, basis = input_gate()
    census = stratum_census(manifest)
    low = load_low_search()
    rows, degree4 = row_universe(low)
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "PREFLIGHT_ONLY_NO_LARGE_QUOTIENT_LAUNCH",
        "script_sha256": script_hash_before,
        "bindings": {
            "g0038_manifest_sha256": EXPECTED_MANIFEST_SHA256,
            "g0038_stream_sha256": EXPECTED_STREAM_SHA256,
            "g0047_low_search_sha256": EXPECTED_LOW_SEARCH_SHA256,
            "g0050_exact_q_report_sha256": EXPECTED_EXACT_Q_REPORT_SHA256,
            "g0050_proper_basis_indices_sha256": canonical_sha256(basis),
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
        },
        "host_resources_observed": host_resources(),
        "column_census": census,
        "row_universe": rows,
        "dense_resource_table": resource_table(),
        "self_test": self_test(),
        "claim_boundary": (
            "The complete mass-four global hinge gate has 99,858 primitive degree-four rows. "
            "The 10,065 degree-three rows are only an embedded subset and cannot support a "
            "mass-four conclusion. Resource estimates and bounded samples establish no rank, "
            "identity, or impossibility result."
        ),
    }
    if sample_per_stratum:
        report["bounded_semantic_benchmark"] = benchmark_columns(
            low, degree4, sample_per_stratum
        )
    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("preflight script changed during execution")
    report["wall_seconds"] = time.perf_counter() - started
    report["canonical_payload_sha256"] = canonical_sha256(report)
    return report


def write_json_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument(
        "--sample-per-stratum",
        type=int,
        default=0,
        help=f"bounded semantic sample in 0..{MAX_SAMPLE_PER_STRATUM}",
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return
    if not args.preflight_only:
        raise SystemExit("refusing to proceed without --preflight-only")
    if not 0 <= args.sample_per_stratum <= MAX_SAMPLE_PER_STRATUM:
        raise SystemExit(f"--sample-per-stratum must lie in 0..{MAX_SAMPLE_PER_STRATUM}")
    report = build_report(args.sample_per_stratum)
    if args.output is not None:
        output = args.output.resolve()
        try:
            output.relative_to(ROOT.resolve())
        except ValueError as error:
            raise SystemExit("output must remain inside the project") from error
        write_json_atomic(output, report)
        print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))
    else:
        print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
