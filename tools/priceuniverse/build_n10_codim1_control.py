#!/usr/bin/env python3
"""Build an exact codimension-one n=10 pricing control.

The full-rank pivot support and saved independent-row minor come from the n=10
known-answer lift.  Removing one pivot column leaves a rank-(r-1) proper
subfamily.  Solving M^T y = e_drop produces the exact functional whose kernel
inside the full saved-system span is exactly that subfamily span.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import resource
import sys
import time
from pathlib import Path

import flint


EXACTLIFT = Path(__file__).resolve().parents[1] / "exactlift"
sys.path.insert(0, str(EXACTLIFT))
import support_lift  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fraction_parts(value: flint.fmpq) -> tuple[int, int]:
    return int(value.p), int(value.q)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", type=Path, required=True)
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--selected-rows", type=Path, required=True)
    parser.add_argument("--sketch-index", type=int, default=0)
    parser.add_argument("--drop-position", type=int, default=-1)
    parser.add_argument("--primes", default="1000003,1000033")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()

    started = time.monotonic()
    pivot_document, sketch = support_lift.read_pivots(args.pivot_report, args.sketch_index)
    n = int(pivot_document["n"])
    pivots = list(map(int, sketch["pivot_columns"]))
    rank = len(pivots)
    drop = args.drop_position if args.drop_position >= 0 else rank + args.drop_position
    if not 0 <= drop < rank:
        raise ValueError("drop position outside pivot support")
    columns, source_count = support_lift.load_saved_selected(args.system, pivots, n)
    row_index = support_lift.build_row_index(columns)
    row_keys = list(row_index)
    row_document = json.loads(args.selected_rows.read_text(encoding="utf-8"))
    selected_rows = list(map(int, row_document["selected_rows"]))
    if len(selected_rows) != rank or len(set(selected_rows)) != rank:
        raise ValueError("selected row artifact is not a rank-sized set")
    row_count = len(row_index) + n
    if any(not 0 <= row < row_count for row in selected_rows):
        raise ValueError("selected row outside real row union")

    selected_position = {row: position for position, row in enumerate(selected_rows)}
    minor = flint.fmpz_mat(rank, rank)
    for column_position, column in enumerate(columns):
        for row, value in support_lift.entries(column, row_index):
            position = selected_position.get(row)
            if position is not None:
                minor[position, column_position] = value

    primes = [int(value) for value in args.primes.split(",") if value]
    rank_checks = []
    keep = [column for column in range(rank) if column != drop]
    for prime in primes:
        modular = flint.nmod_mat(minor, prime)
        subminor = flint.nmod_mat(rank, rank - 1, prime)
        for new_column, old_column in enumerate(keep):
            for row in range(rank):
                subminor[row, new_column] = modular[row, old_column]
        full_rank = int(modular.rank())
        subfamily_rank = int(subminor.rank())
        rank_checks.append(
            {
                "prime": prime,
                "full_rank_numerator": full_rank,
                "full_rank_denominator": rank,
                "proper_subfamily_rank_numerator": subfamily_rank,
                "proper_subfamily_columns_denominator": rank - 1,
            }
        )
        if (full_rank, subfamily_rank) != (rank, rank - 1):
            raise RuntimeError(f"rank control failed at prime {prime}")

    rhs = flint.fmpq_mat(rank, 1)
    rhs[drop, 0] = 1
    solve_started = time.monotonic()
    separator_vector = flint.fmpq_mat(minor.transpose()).solve(rhs, algorithm="dixon")
    solve_seconds = time.monotonic() - solve_started
    if flint.fmpq_mat(minor.transpose()) * separator_vector != rhs:
        raise RuntimeError("exact separator solve did not replay")

    linear_weights = [flint.fmpq(0) for _ in range(n)]
    hinge_weights: dict[str, flint.fmpq] = {}
    for position, real_row in enumerate(selected_rows):
        value = separator_vector[position, 0]
        if not value:
            continue
        if real_row < len(row_keys):
            hinge_weights[row_keys[real_row]] = value
        else:
            linear_weights[real_row - len(row_keys)] = value

    denominator_lcm = 1
    for value in [*linear_weights, *hinge_weights.values()]:
        _, denominator = fraction_parts(value)
        denominator_lcm = math.lcm(denominator_lcm, denominator)
    separator = {
        "schema": "max11-exact-sketch-separator-v1",
        "method": "exact codimension-one dual of n=10 pivot minor",
        "n": n,
        "subject": "saved-system:proper-pivot-subfamily-codimension-one",
        "proper_subfamily_pivot_columns": [pivots[position] for position in keep],
        "dropped_pivot_source_index": pivots[drop],
        "linear_weights": [str(value) for value in linear_weights],
        "hinge_weights": {key: str(value) for key, value in sorted(hinge_weights.items())},
        "coefficient_denominator_lcm": str(denominator_lcm),
        "no_claim": "This is a codimension-one control inside the finite n=10 saved-system span, not a MAX11 result.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(separator, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report = {
        "schema": "max11-price-universe-n10-codim1-control-v1",
        "verdict": "PASS",
        "system": str(args.system),
        "system_sha256": sha256_file(args.system),
        "source_columns_denominator": source_count,
        "pivot_report": str(args.pivot_report),
        "pivot_report_sha256": sha256_file(args.pivot_report),
        "selected_rows": str(args.selected_rows),
        "selected_rows_sha256": sha256_file(args.selected_rows),
        "full_basis_columns_denominator": rank,
        "proper_subfamily_columns_denominator": rank - 1,
        "dropped_pivot_position": drop,
        "dropped_pivot_source_index": pivots[drop],
        "rank_checks": rank_checks,
        "exact_defining_pairings": {
            "annihilated_subfamily_columns_numerator": rank - 1,
            "annihilated_subfamily_columns_denominator": rank - 1,
            "dropped_column_pairing": "1",
        },
        "nonzero_linear_weights_numerator": sum(bool(value) for value in linear_weights),
        "nonzero_hinge_weights_numerator": len(hinge_weights),
        "coefficient_denominator_lcm": str(denominator_lcm),
        "separator": str(args.output),
        "separator_sha256": sha256_file(args.output),
        "exact_solve_seconds": solve_seconds,
        "total_seconds": time.monotonic() - started,
        "max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "no_claim": "The direct ranks and separator concern only a proper subfamily of the finite n=10 saved system.",
    }
    args.report.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
