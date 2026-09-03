#!/usr/bin/env python3
"""Fail-closed verification for the streamrank overlap benchmark artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent

RAW_SHA256 = {
    "baseline-nvl-n11-first20000-pivots.json": "71aca8c25e6b4ebfe500947078e7dfa4b70c1f6c52bd5f37a686bc460ce7767c",
    "baseline-nvl-n11-first20000.json": "81bcc5c0989cef8fce5013f52705c3891b30c66ca597906cd511e028fed1606c",
    "baseline-nvl-n11-first20000.log": "799cc157118a00d502226724f951d173cdc1a4213f2ae96fdc78539480825513",
    "controls-final/cpu-n10.json": "39167f220ce43a986fea58f45ac37cb4d36278930787984aee03c62309d2a9c3",
    "controls-final/cpu-n9.json": "f73c68f09c1a49571fd07f5670053ae13c16fdf8cbfb9228c05ed1e16fd07e7b",
    "controls-final/cuda-n10.json": "15a138437c267830faa0a289ea2c16cb6c2f2d5044e9cdaa8bc0de00730780b3",
    "controls-final/cuda-n9-mutant-rank359.exit-code": "4355a46b19d348dc2f57c046f8ef63d4538ebb936000f3c9ee954a27460dd865",
    "controls-final/cuda-n9-mutant-rank359.json": "b5fc5665371b1842f358add3e8ee3fcd1b80892217f4427bac62aabb5c95a843",
    "controls-final/cuda-n9.json": "ccaeb49d55d636bc12659dfe6bd49248a4f42742f7f506744b87afddd68b8e17",
    "controls-final/headroom-before.txt": "322fb377c696849bcfc705d0b3590d96e6a1ade0c01fc4bbcb820cc230b8a226",
    "final-nvl-n11-first20000-pivots.json": "71aca8c25e6b4ebfe500947078e7dfa4b70c1f6c52bd5f37a686bc460ce7767c",
    "final-nvl-n11-first20000.json": "2e6d3d57b2417944eb4d1deff5f279169546cc5adabab2311b445b85cfc5b5ca",
    "final-nvl-n11-first20000.log": "ef3fd35080bf7dd0c5459243fb6bc5381d0466a0078eaee14f3facf511ac7249",
    "local-abort-control.json": "5a2606628c7b21fa73b3dd5a10a80f36f7e8f9f724609e379b86e156984f67b7",
    "overlap-v1-aborted-3072.log": "cbe6c5823d43038e393e3e2f4cf4f1d121ed642b1b7fd6179b11795e0ac25ddb",
    "stageA-first20000-order.json": "29bf756acd53f7fed328d5a5f4b03f40c462e59d0e625fbd94395d696e4470ef",
    "stageA-first20000-s1-expected-pivots.json": "71aca8c25e6b4ebfe500947078e7dfa4b70c1f6c52bd5f37a686bc460ce7767c",
}

CONTROL_CASES = {
    "cpu-n10.json": ("cpu", 10, 12_248, 2_166, 2_166, "MEMBER", 6),
    "cuda-n10.json": ("cuda", 10, 12_248, 2_166, 2_166, "MEMBER", 16),
    "cpu-n9.json": ("cpu", 9, 739, 360, 361, "NON_MEMBER", 6),
    "cuda-n9.json": ("cuda", 9, 739, 360, 361, "NON_MEMBER", 16),
}

REFERENCE_PIVOT_HASHES = {
    9: "3885bf4223184e19c9d6cfdc1632d24d33c47c7cbc4a859f4208257af0933cdd",
    10: "13ef82302f2e50e9f9555cd77eab1881bd3ef87f33677badd2b9fe079e39a87d",
}

INPUT_HASHES = {
    9: "729699ed4d6b6fb77c9d3d3709ca5ac65d8aa487888bbd6ec116698c90782991",
    10: "bda8eddae71365fa6f1cfaa0ef26b7a78a829ce8b8fd5902cd6155ea97e17e18",
}

PHASE_FIELDS = (
    "generate_s",
    "sketch_s",
    "gemm_s",
    "host_reduce_s",
    "basis_update_s",
    "io_s",
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load(relative: str) -> Any:
    with (ROOT / relative).open(encoding="utf-8") as handle:
        return json.load(handle)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def pivot_hash(columns: list[int]) -> str:
    payload = b"".join(struct.pack("<Q", column) for column in columns)
    return hashlib.sha256(payload).hexdigest()


def phase_totals(report: dict[str, Any]) -> dict[str, float]:
    fields = PHASE_FIELDS + (("sparse_drop_s",) if "sparse_drop_s" in report["progress"][0] else ())
    return {field: sum(point[field] for point in report["progress"]) for field in fields}


def verify_benchmark(
    label: str, report: dict[str, Any], expected_pivots: list[int]
) -> None:
    expected_header = {
        "schema": "max11-streamrank-pivots-v1",
        "backend": "cuda",
        "n": 11,
        "source_column_count": 20_000,
        "source_columns_denominator": 20_000,
        "threads": 16,
        "batch_size": 1_024,
        "buckets": 64_000,
        "modulus": 1_000_003,
    }
    for field, expected in expected_header.items():
        require(report[field] == expected, f"{label}: {field} mismatch")
    require(len(report["sketches"]) == 1, f"{label}: expected one sketch")
    sketch = report["sketches"][0]
    require(sketch["sketch"]["seed"] == 2_026_090_201, f"{label}: seed mismatch")
    require(sketch["rank_a"] == 7_330, f"{label}: rank(A) mismatch")
    require(sketch["rank_augmented"] == 7_331, f"{label}: augmented rank mismatch")
    require(sketch["verdict"] == "NON_MEMBER", f"{label}: verdict mismatch")
    require(sketch["pivot_columns"] == expected_pivots, f"{label}: pivot list mismatch")
    require(
        sketch["pivot_columns_u64_le_sha256"] == pivot_hash(expected_pivots),
        f"{label}: embedded pivot hash mismatch",
    )
    require(len(report["progress"]) == 20, f"{label}: expected 20 batches")
    require(report["progress"][-1]["source_columns_processed"] == 20_000, f"{label}: incomplete")
    for batch_index, point in enumerate(report["progress"]):
        for field in PHASE_FIELDS:
            require(field in point, f"{label}: batch {batch_index} lacks {field}")
            require(point[field] >= 0.0, f"{label}: batch {batch_index} has negative {field}")


def verify_control(name: str, expected: tuple[Any, ...]) -> dict[str, Any]:
    backend, n, columns, rank_a, rank_augmented, verdict, threads = expected
    report = load(f"controls-final/{name}")
    require(report["result"] == "CONTROL_PASS", f"{name}: expected CONTROL_PASS")
    require(report["backend"] == backend, f"{name}: backend mismatch")
    require(report["n"] == n, f"{name}: n mismatch")
    require(report["threads"] == threads, f"{name}: thread count mismatch")
    require(report["modulus"] == 1_000_003, f"{name}: modulus mismatch")
    require(report["source_column_count"] == columns, f"{name}: column count mismatch")
    require(report["source_columns_denominator"] == columns, f"{name}: denominator mismatch")
    require(report["input_sha256"] == INPUT_HASHES[n], f"{name}: input hash mismatch")
    require(
        report["expected"]
        == {
            "source_columns": columns,
            "rank_a": rank_a,
            "rank_augmented": rank_augmented,
            "verdict": verdict,
            "exact_match": True,
        },
        f"{name}: expected block mismatch",
    )
    require(len(report["sketches"]) == 2, f"{name}: expected two seeds")
    require(
        [sketch["sketch"]["seed"] for sketch in report["sketches"]]
        == [2_026_090_201, 2_026_090_202],
        f"{name}: seed list mismatch",
    )
    for sketch in report["sketches"]:
        require(sketch["rank_a"] == rank_a, f"{name}: rank(A) mismatch")
        require(sketch["rank_augmented"] == rank_augmented, f"{name}: augmented rank mismatch")
        require(sketch["verdict"] == verdict, f"{name}: verdict mismatch")
        require(sketch["source_columns_denominator"] == columns, f"{name}: sketch denominator mismatch")
        require(
            sketch["pivot_columns_u64_le_sha256"] == REFERENCE_PIVOT_HASHES[n],
            f"{name}: reference pivot hash mismatch",
        )
        require(
            pivot_hash(sketch["pivot_columns"]) == REFERENCE_PIVOT_HASHES[n],
            f"{name}: recomputed pivot hash mismatch",
        )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "verification.json")
    parser.add_argument("--manifest", type=Path, default=ROOT / "MANIFEST.sha256")
    args = parser.parse_args()

    observed_hashes = {relative: sha256(ROOT / relative) for relative in RAW_SHA256}
    require(observed_hashes == RAW_SHA256, "raw artifact SHA-256 mismatch")

    order = load("stageA-first20000-order.json")
    expected_pivots = load("stageA-first20000-s1-expected-pivots.json")
    require(len(order) == 20_000, "benchmark order denominator mismatch")
    require(len(set(order)) == 20_000, "benchmark order contains duplicates")
    require(len(expected_pivots) == 7_330, "expected pivot denominator mismatch")

    baseline = load("baseline-nvl-n11-first20000.json")
    final = load("final-nvl-n11-first20000.json")
    verify_benchmark("baseline", baseline, expected_pivots)
    verify_benchmark("final", final, expected_pivots)
    require(
        load("baseline-nvl-n11-first20000-pivots.json") == expected_pivots,
        "baseline extracted pivot file mismatch",
    )
    require(
        load("final-nvl-n11-first20000-pivots.json") == expected_pivots,
        "final extracted pivot file mismatch",
    )
    baseline_trace = [
        (point["source_columns_processed"], point["ranks"]) for point in baseline["progress"]
    ]
    final_trace = [
        (point["source_columns_processed"], point["ranks"]) for point in final["progress"]
    ]
    require(baseline_trace == final_trace, "per-batch source/rank trace mismatch")
    require(
        all("sparse_drop_s" in point and point["sparse_drop_s"] >= 0.0 for point in final["progress"]),
        "final report lacks nonnegative sparse-drop timer",
    )
    speedup = baseline["wall_seconds"] / final["wall_seconds"]
    require(speedup >= 2.0, f"wall-time speedup gate failed: {speedup}")

    controls = {
        name: verify_control(name, expected) for name, expected in CONTROL_CASES.items()
    }
    for n in (9, 10):
        cpu = controls[f"cpu-n{n}.json"]
        cuda = controls[f"cuda-n{n}.json"]
        require(
            [sketch["pivot_columns"] for sketch in cpu["sketches"]]
            == [sketch["pivot_columns"] for sketch in cuda["sketches"]],
            f"n={n}: CPU/CUDA pivot lists differ",
        )

    mutant = load("controls-final/cuda-n9-mutant-rank359.json")
    require((ROOT / "controls-final/cuda-n9-mutant-rank359.exit-code").read_text().strip() == "1", "mutant exit code was not 1")
    require(mutant["result"] == "CONTROL_FAIL", "mutant did not fail closed")
    require(mutant["expected"]["exact_match"] is False, "mutant unexpectedly matched")
    require(mutant["expected"]["rank_a"] == 359, "mutant expected rank changed")
    require(mutant["sketches"][0]["rank_a"] == 360, "mutant observed rank changed")

    abort_control = load("local-abort-control.json")
    require(abort_control["result"] == "ABORTED_GATE", "pipeline abort control did not stop")
    require(abort_control["source_column_count"] == 64, "pipeline abort count changed")
    require(len(abort_control["progress"]) == 1, "pipeline abort did not stop after one batch")

    receipt = {
        "schema": "streamrank-overlap-verification-v1",
        "result": "PASS",
        "benchmark": {
            "source_columns_denominator": 20_000,
            "baseline_wall_seconds": baseline["wall_seconds"],
            "final_wall_seconds": final["wall_seconds"],
            "wall_speedup_ratio": speedup,
            "pivot_columns_denominator": len(expected_pivots),
            "pivot_lists_byte_identical": True,
            "per_batch_source_rank_trace_identical": True,
            "baseline_phase_totals_seconds": phase_totals(baseline),
            "final_phase_totals_seconds": phase_totals(final),
        },
        "controls": {
            "passing_cases_denominator": len(controls),
            "passing_cases_numerator": sum(
                report["result"] == "CONTROL_PASS" for report in controls.values()
            ),
            "cpu_cuda_pivot_parity_n": [9, 10],
            "hostile_expected_rank_control": "CONTROL_FAIL_EXIT_1",
            "pipeline_abort_control": "ABORTED_GATE_AFTER_64_OF_20000",
        },
        "binaries_sha256": {
            "baseline_instrumented": "23d1bac794f695375ea849efd469423d76e0da5ba6f79043b7a94aad9486a86a",
            "final_overlap": "36c0e3ce8918164bd1d0a30e63399d1f446fef7b61df3bdeb16a2a6ed3a3fe5e",
        },
        "raw_artifacts_sha256": observed_hashes,
        "no_claim": "Performance and modular pivot parity do not prove an identity or an unrestricted depth lower bound.",
    }
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path = args.manifest.resolve()
    manifest_entries = []
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.resolve() != manifest_path:
            manifest_entries.append(f"{sha256(path)}  {path.relative_to(ROOT)}")
    manifest_path.write_text("\n".join(manifest_entries) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
