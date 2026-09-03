#!/usr/bin/env python3
"""Select an exact modular column basis for a secondary LP matrix."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import select_exact_support


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def prepare(matrix_dir: Path, pivot_report: Path, output: Path, prime: int) -> dict:
    started = time.monotonic()
    meta_path, _meta, rows, columns, start, index, value, source, target = (
        select_exact_support.load_matrix(matrix_dir)
    )
    pivot = json.loads(pivot_report.read_text())
    candidate_sources = [int(item) for item in pivot["sketches"][0]["pivot_columns"]]
    position_of = {int(source_index): position for position, source_index in enumerate(source)}
    missing = [source_index for source_index in candidate_sources if source_index not in position_of]
    if missing:
        raise ValueError(f"{len(missing)} pivot sources are absent from the LP matrix")
    candidate_positions = [position_of[source_index] for source_index in candidate_sources]
    rank_a, rank_augmented, selected_local = select_exact_support.analyze_candidate(
        rows,
        candidate_positions,
        start,
        index,
        value,
        target,
        prime,
    )
    if rank_a != rows or rank_augmented != rows:
        raise RuntimeError(f"candidate basis rank is {rank_a}/{rank_augmented}, expected {rows}/{rows}")
    selected_positions = [candidate_positions[local] for local in selected_local]
    selected_sources = [int(source[position]) for position in selected_positions]
    if len(selected_positions) != rows:
        raise RuntimeError(f"selected {len(selected_positions)}/{rows} basis columns")
    report = {
        "schema": "max11-highs-initial-basis-v1",
        "verdict": "PASS",
        "exact": "modular",
        "prime": prime,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "candidate_pivot_report": str(pivot_report),
        "candidate_pivot_report_sha256": sha256(pivot_report),
        "candidate_columns_numerator": len(candidate_positions),
        "candidate_columns_denominator": columns,
        "rank_a_mod_prime": rank_a,
        "rank_augmented_mod_prime": rank_augmented,
        "basis_columns_numerator": len(selected_positions),
        "basis_columns_denominator": rows,
        "column_positions": selected_positions,
        "source_indices": selected_sources,
        "seconds": time.monotonic() - started,
        "no_claim": "This is an exact modular LP starting basis, not a rational identity or sparse certificate.",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--pivot-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prime", type=int, required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.matrix_dir, args.pivot_report, args.output, args.prime), indent=2))


if __name__ == "__main__":
    main()
