#!/usr/bin/env python3
"""Turn floating L1 supports into exact modularly consistent independent supports."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from pathlib import Path

import flint
import numpy as np


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_u64le(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(8, "little"))
    return digest.hexdigest()


def pivot_columns(rref, rank: int) -> list[int]:
    pivots = []
    candidate = 0
    for row in range(rank):
        while candidate < rref.ncols() and not rref[row, candidate]:
            candidate += 1
        if candidate == rref.ncols():
            raise RuntimeError("RREF pivot scan failed")
        pivots.append(candidate)
        candidate += 1
    return pivots


def load_matrix(matrix_dir: Path):
    meta_path = matrix_dir / "matrix.json"
    meta = json.loads(meta_path.read_text())
    files = meta["files"]
    rows = int(meta["rows_denominator"])
    columns = int(meta["columns_denominator"])
    nnz = int(meta["nonzeros_denominator"])
    start = np.memmap(matrix_dir / files["start"]["path"], mode="r", dtype="<u8")
    index = np.memmap(matrix_dir / files["index"]["path"], mode="r", dtype="<u4")
    value = np.memmap(matrix_dir / files["value"]["path"], mode="r", dtype="<i8")
    source = np.memmap(matrix_dir / files["source"]["path"], mode="r", dtype="<u8")
    target = np.memmap(matrix_dir / files["target"]["path"], mode="r", dtype="<i8")
    if len(start) != columns + 1 or int(start[-1]) != nnz or len(index) != nnz or len(value) != nnz:
        raise ValueError("CSC dimension mismatch")
    return meta_path, meta, rows, columns, start, index, value, source, target


def analyze_candidate(rows, positions, start, index, value, target, prime):
    augmented = flint.nmod_mat(rows, len(positions) + 1, prime)
    for local_column, position in enumerate(positions):
        begin, end = int(start[position]), int(start[position + 1])
        for cursor in range(begin, end):
            augmented[int(index[cursor]), local_column] = int(value[cursor]) % prime
    for row, entry in enumerate(target):
        if entry:
            augmented[row, len(positions)] = int(entry) % prime
    reduced, rank_augmented = augmented.rref(inplace=True)
    pivots = pivot_columns(reduced, rank_augmented)
    target_is_pivot = len(positions) in pivots
    rank_a = rank_augmented - int(target_is_pivot)
    selected_local = [position for position in pivots if position < len(positions)]
    del augmented, reduced
    return rank_a, rank_augmented, selected_local


def select(matrix_dir: Path, l1_report: Path, output: Path, report_path: Path, prime: int, base_pivot: Path | None):
    started = time.monotonic()
    meta_path, meta, rows, columns, start, index, value, source, target = load_matrix(matrix_dir)
    lp = json.loads(l1_report.read_text())
    if int(lp["columns_denominator"]) != columns:
        raise ValueError("LP/matrix column mismatch")
    trials = []
    feasible = []
    for record in lp["rounds"]:
        positions = [int(entry["column_position"]) for entry in record["candidate"]]
        phase = time.monotonic()
        rank_a, rank_augmented, selected_local = analyze_candidate(rows, positions, start, index, value, target, prime)
        selected_positions = [positions[local] for local in selected_local]
        trial = {
            "round": int(record["round"]),
            "candidate_support_numerator": len(positions),
            "candidate_support_denominator": columns,
            "rank_a_mod_prime": rank_a,
            "rank_augmented_mod_prime": rank_augmented,
            "verdict": "MEMBER" if rank_a == rank_augmented else "NON_MEMBER",
            "independent_support_numerator": len(selected_positions),
            "seconds": time.monotonic() - phase,
        }
        trials.append(trial)
        print(f"SUPPORT_TRIAL round={trial['round']} verdict={trial['verdict']} rank={rank_a}/{rank_augmented} support={len(positions)}/{columns} seconds={trial['seconds']:.3f}", flush=True)
        if rank_a == rank_augmented:
            feasible.append((len(selected_positions), int(record["round"]), selected_positions))
    if not feasible:
        raise RuntimeError("no floating support contains the target modulo the named prime")
    _, chosen_round, selected_positions = min(feasible)
    selected_sources = [int(source[position]) for position in selected_positions]

    if base_pivot is None:
        pivot_document = {
            "schema": "max11-streamrank-pivots-v1",
            "input": meta["system"],
            "input_sha256": meta["system_sha256"],
            "n": int(meta["n"]),
            "branch_edge_occurrences": 4,
            "modulus": prime,
            "source_columns_denominator": columns,
            "subject": "saved-system:all",
            "sketches": [{
                "sketch": {"algorithm": "identity-real-rows", "seed": 0, "buckets": rows},
                "rank_a": len(selected_sources),
                "rank_augmented": len(selected_sources),
                "verdict": "MEMBER",
                "pivot_columns": selected_sources,
                "pivot_columns_u64_le_sha256": sha256_u64le(selected_sources),
                "pivot_buckets": [],
            }],
        }
    else:
        pivot_document = json.loads(base_pivot.read_text())
        original = pivot_document["sketches"][0]
        # Select independent sketch rows for the exact square minor.
        rank = len(selected_positions)
        transposed = flint.nmod_mat(rank, rows, prime)
        for local_column, position in enumerate(selected_positions):
            begin, end = int(start[position]), int(start[position + 1])
            for cursor in range(begin, end):
                transposed[local_column, int(index[cursor])] = int(value[cursor]) % prime
        reduced, real_rank = transposed.rref(inplace=True)
        if real_rank != rank:
            raise RuntimeError(f"selected sketch support row rank {real_rank}/{rank}")
        row_positions = pivot_columns(reduced, rank)
        del transposed, reduced
        pivot_buckets = [int(original["pivot_buckets"][position]) for position in row_positions]
        replacement = dict(original)
        replacement.update({
            "rank_a": rank,
            "rank_augmented": rank,
            "verdict": "MEMBER",
            "pivot_columns": selected_sources,
            "pivot_columns_u64_le_sha256": sha256_u64le(selected_sources),
            "pivot_buckets": pivot_buckets,
            "left_separator": None,
        })
        pivot_document["sketches"] = [replacement]
        pivot_document["subject"] = f"L1/reweighted-L1 support from {l1_report}"
        pivot_document["source_column_count"] = len(selected_sources)
        pivot_document["no_claim"] = "This support passes one exact modular sketch consistency test; it is not an identity until exact rational lifting and all-row verification pass."

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(pivot_document, indent=2, sort_keys=True) + "\n")
    report = {
        "schema": "max11-sparse-support-selection-v1",
        "verdict": "PASS",
        "exact": "modular",
        "prime": prime,
        "matrix_report": str(meta_path),
        "matrix_report_sha256": sha256(meta_path),
        "l1_report": str(l1_report),
        "l1_report_sha256": sha256(l1_report),
        "base_pivot_report": str(base_pivot) if base_pivot else None,
        "base_pivot_report_sha256": sha256(base_pivot) if base_pivot else None,
        "trials": trials,
        "chosen_round": chosen_round,
        "chosen_independent_support_numerator": len(selected_sources),
        "chosen_independent_support_denominator": columns,
        "pivot_report": str(output),
        "pivot_report_sha256": sha256(output),
        "seconds": time.monotonic() - started,
        "no_claim": "Modular consistency of a floated support is not an exact rational identity; the emitted pivot report is only an input to exact lifting and all-row verification.",
    }
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--matrix-dir", type=Path, required=True)
    parser.add_argument("--l1-report", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--prime", type=int, required=True)
    parser.add_argument("--base-pivot-report", type=Path)
    args = parser.parse_args()
    print(json.dumps(select(args.matrix_dir, args.l1_report, args.output, args.report, args.prime, args.base_pivot_report), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
