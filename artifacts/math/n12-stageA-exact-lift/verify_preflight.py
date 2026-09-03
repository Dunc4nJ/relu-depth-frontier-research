#!/usr/bin/env python3
"""Fail-closed verifier for the A100 n=12 exact-lift interface preflight."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


UNIVERSE_SHA = "f98352ea4d1517f0b88aba0b38d34be0edb0b845aac3eaa724f3bd1f8f83f640"


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_dir = args.run_dir

    plan = json.loads((run_dir / "gather/gather_plan.json").read_text())
    require(plan["schema"] == "max11-exact-pivot-gather-plan-v1", "plan schema")
    require(plan["universe_count"] == 787_523, "n=12 universe count")
    require(plan["synthetic_five_l_index"] == 787_523, "n=12 5L source index")
    require(plan["rank_a"] == plan["rank_augmented"] == 1, "fixture rank")
    require(plan["batch_count"] == 1, "batch count")

    batch = run_dir / "batches/batch-000.mcolgen1"
    direct = run_dir / "direct-tiny-n12.mcolgen1"
    require(batch.read_bytes() == direct.read_bytes(), "two colgen paths disagree")
    with batch.open("rb") as handle:
        header = handle.read(28)
    magic, n, branch_edges, modulus, count = struct.unpack("<8sHHQQ", header)
    require(magic == b"MCOLGEN1", "MCOLGEN magic")
    require((n, branch_edges, modulus, count) == (12, 5, 0, 1), "n=12 MCOLGEN header")

    build = json.loads((run_dir / "tiny-n12-build.json").read_text())
    require(build["schema"] == "max11-sketch-member-problem-v1", "build schema")
    require(build["verdict"] == "PASS", "builder verdict")
    require(build["source_universe_sha256"] == UNIVERSE_SHA, "universe SHA")
    require(build["pivot_columns_numerator"] == 1, "pivot numerator")
    require(build["pivot_columns_denominator"] == 1, "pivot denominator")
    require(build["exact_batch_records_numerator"] == 1, "batch numerator")
    require(build["exact_batch_records_denominator"] == 1, "batch denominator")
    require(build["linear_rows_denominator"] == 12, "n=12 linear rows")
    require(build["problem_schema"] == "ELIFTQ02", "problem schema")
    require(build["problem_sha256"] == sha256(run_dir / "tiny-n12.eliftq02"), "problem SHA")

    mutant_batch = run_dir / "mutant-batches/batch-000.mcolgen1"
    with mutant_batch.open("rb") as handle:
        mutant_header = handle.read(28)
    mutant_magic, mutant_n, mutant_edges, mutant_modulus, mutant_count = struct.unpack(
        "<8sHHQQ", mutant_header
    )
    require(
        (mutant_magic, mutant_n, mutant_edges, mutant_modulus, mutant_count)
        == (b"MCOLGEN1", 11, 5, 0, 1),
        "planted n=11 MCOLGEN header",
    )
    require(mutant_batch.read_bytes()[10:] == batch.read_bytes()[10:], "mutant changed payload")
    mutant_status = int((run_dir / "mutant.exit_code").read_text().strip())
    mutant_stderr = (run_dir / "mutant.stderr.log").read_text()
    require(mutant_status != 0, "dimension mutant exit status")
    require("incompatible dimensions/modulus" in mutant_stderr, "dimension mutant reason")
    require(not (run_dir / "mutant.eliftq02").exists(), "mutant wrote a problem")
    require(not (run_dir / "mutant-build.json").exists(), "mutant wrote a report")

    report = {
        "schema": "exp0037-n12-exact-lift-preflight-v1",
        "result": "PASS",
        "colgen_n12_columns_numerator": 1,
        "colgen_n12_columns_denominator": 1,
        "colgen_replays_equal_numerator": 1,
        "colgen_replays_equal_denominator": 1,
        "lift_builder_n12_accepts_numerator": 1,
        "lift_builder_n12_accepts_denominator": 1,
        "dimension_mutants_rejected_numerator": 1,
        "dimension_mutants_rejected_denominator": 1,
        "mcolgen_sha256": sha256(batch),
        "problem_sha256": sha256(run_dir / "tiny-n12.eliftq02"),
        "build_report_sha256": sha256(run_dir / "tiny-n12-build.json"),
        "no_claim": (
            "This interface preflight uses a structurally marked one-column fixture. "
            "It is not an n=12 membership result, exact identity, or successful rational lift."
        ),
    }
    encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
    if args.output.exists():
        require(args.output.read_text() == encoded, "stored verification differs")
    else:
        args.output.write_text(encoded)
    print("N12_EXACT_LIFT_PREFLIGHT_PASS colgen=1/1 builder=1/1 mutant=1/1")


if __name__ == "__main__":
    main()
