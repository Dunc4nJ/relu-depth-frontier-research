#!/usr/bin/env python3
"""Verify MCOLGEN1 and direct-colgen ingress produce identical prices."""

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
    parser.add_argument("--mcolgen-input", type=Path, required=True)
    parser.add_argument("--mcolgen-report", type=Path, required=True)
    parser.add_argument("--direct-report", type=Path, required=True)
    parser.add_argument("--mcolgen-violators", type=Path, required=True)
    parser.add_argument("--direct-violators", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    left = json.loads(args.mcolgen_report.read_text(encoding="utf-8"))
    right = json.loads(args.direct_report.read_text(encoding="utf-8"))
    keys = [
        "columns_evaluated_denominator",
        "annihilated_columns_numerator",
        "violating_columns_numerator",
        "integer_scaled_common_denominator",
        "exact_price_vector_sha256",
        "modular_cross_checks",
    ]
    checks = {
        "both_reports_pass": left["verdict"] == right["verdict"] == "PASS",
        "named_fields_identical": all(left[key] == right[key] for key in keys),
        "violator_bytes_identical": args.mcolgen_violators.read_bytes()
        == args.direct_violators.read_bytes(),
        "mcolgen_report_binds_input": left["input"]["sha256"]
        == sha256_file(args.mcolgen_input),
    }
    payload = {
        "schema": "max11-price-universe-ingress-parity-v1",
        "verdict": "PASS" if all(checks.values()) else "FAIL",
        "checks": checks,
        "columns_denominator": left["columns_evaluated_denominator"],
        "exact_price_vector_sha256": left["exact_price_vector_sha256"],
        "mcolgen_input": str(args.mcolgen_input),
        "mcolgen_input_sha256": sha256_file(args.mcolgen_input),
        "mcolgen_report_sha256": sha256_file(args.mcolgen_report),
        "direct_report_sha256": sha256_file(args.direct_report),
        "violators_sha256": sha256_file(args.mcolgen_violators),
        "modular_primes": [1_000_003, 1_000_033],
        "no_claim": "This checks two ingress paths on eight finite n=11 columns only; it is not a MAX11 result.",
    }
    if payload["verdict"] != "PASS":
        raise RuntimeError(f"ingress parity failed: {checks}")
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
