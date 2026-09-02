#!/usr/bin/env python3
"""Project the measured 5,000-column n=11 pass to frozen denominators."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--universe-records", type=int, default=754_017)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = json.loads(args.report.read_text(encoding="utf-8"))
    measured_columns = int(report["columns_evaluated_denominator"])
    total_seconds = float(report["total_seconds"])
    generation_seconds = float(report["generation_seconds"])
    if not (
        report["verdict"] == "PASS"
        and measured_columns == 5_000
        and int(report["input"]["threads_maximum"]) == 6
        and [item["prime"] for item in report["modular_cross_checks"]]
        == [1_000_003, 1_000_033]
        and all(item["agreement_numerator"] == measured_columns for item in report["modular_cross_checks"])
    ):
        raise RuntimeError("benchmark report does not match the preregistered denominator")

    projections = []
    for label, denominator in [
        ("G-0027 records", args.universe_records),
        ("source columns including 5L", args.universe_records + 1),
        ("source columns plus target evaluation", args.universe_records + 2),
    ]:
        projected_total = total_seconds * denominator / measured_columns
        projected_generation = generation_seconds * denominator / measured_columns
        projections.append(
            {
                "label": label,
                "columns_denominator": denominator,
                "projected_total_seconds": projected_total,
                "projected_total_hours": projected_total / 3600,
                "projected_generation_seconds": projected_generation,
                "projected_generation_hours": projected_generation / 3600,
            }
        )
    payload = {
        "schema": "max11-price-universe-benchmark-projection-v1",
        "verdict": "PASS",
        "benchmark_report": str(args.report),
        "benchmark_report_sha256": sha256_file(args.report),
        "measured_columns_denominator": measured_columns,
        "threads_maximum": 6,
        "measured_total_seconds": total_seconds,
        "measured_generation_seconds": generation_seconds,
        "measured_pricing_and_output_seconds": total_seconds - generation_seconds,
        "throughput_columns_numerator": measured_columns,
        "throughput_seconds_denominator": total_seconds,
        "peak_rss_kib": report["peak_rss_kib"],
        "bigint_promoted_columns_numerator": report["i128_to_bigint_promoted_columns_numerator"],
        "bigint_promoted_columns_denominator": measured_columns,
        "projections": projections,
        "no_claim": "These are linear projections from one 5,000-column prefix timing, not measured full passes and not evidence about n=11 membership.",
    }
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
