#!/usr/bin/env python3
"""Evaluate the frozen 4,916-class beta=2 common-edge family.

This script is intentionally downstream of ``enumerate_beta2_common.py``.
It reuses the exact orbit and held-out-cut conventions from G-0006/G-0008
and compares beta=2 against the union of the beta=1 same-component baseline
and G-0009's beta=0 cross-component family.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from math import factorial
from pathlib import Path
import sys
import time

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G6 = ROOT / "artifacts/math/G-0006"
G9 = ROOT / "artifacts/math/G-0009"
sys.path.insert(0, str(G6))
sys.path.insert(0, str(HERE))

import exact_lift_search as g6  # noqa: E402
import evaluate_minimal_lifts as g6_eval  # noqa: E402
import cross_component_search as cross  # noqa: E402
import enumerate_beta2_common as beta2  # noqa: E402


N = 11
ORBIT_SCHEMA = "max11-beta2-common-internal-lifts-orbits-v1"
CUT_SHARD_SCHEMA = "max11-beta2-common-heldout-cut-shard-v1"
CUT_MATRIX_SCHEMA = "max11-beta2-common-heldout-cut-matrix-v1"
RANK_SCHEMA = "max11-beta2-common-rank-report-v1"


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return cross.sha256_path(path)


def build_orbit_group(group_index: int, output_directory: Path) -> Path:
    pairs, metadata, metadata_digest, _component_sizes = beta2.build_family()
    del pairs
    bases, _same_metadata, _same_digest = g6.build_bases()
    entries_by_base: list[list[tuple[int, int]]] = [[] for _ in bases]
    for base_index, _term, _component, a, b in metadata:
        entries_by_base[base_index].append((a, b))
    groups = g6.profile_groups()
    if not (0 <= group_index < len(groups)):
        raise ValueError("invalid orbit group index")
    profiles = groups[group_index]
    edges = [(a, b) for a in range(1, N + 1) for b in range(a, N + 1)]
    edge_index = {edge: index for index, edge in enumerate(edges)}
    rows = []
    targets = []
    begun = time.time()
    for profile_index, profile in enumerate(profiles):
        levels = g6_eval.assignments(profile)
        state_count = levels.shape[1]
        edge_values = np.asarray(
            [np.maximum(levels[a - 1], levels[b - 1]) for a, b in edges],
            dtype=np.uint8,
        )
        row = np.empty(len(metadata), dtype=np.int64)
        offset = 0
        for base_index, (_term, left, right, _components) in enumerate(bases):
            left_base = edge_values[[edge_index[edge] for edge in left]].sum(
                axis=0, dtype=np.int16
            )
            right_base = edge_values[[edge_index[edge] for edge in right]].sum(
                axis=0, dtype=np.int16
            )
            base_sum = np.maximum(left_base, right_base).sum(dtype=np.int64)
            for edge in entries_by_base[base_index]:
                # Exact pointwise common-edge identity avoids a redundant outer max.
                row[offset] = base_sum + edge_values[edge_index[edge]].sum(dtype=np.int64)
                offset += 1
        if offset != len(metadata):
            raise AssertionError((offset, len(metadata)))
        rows.append(row)
        targets.append(
            state_count * max(level for level, count in enumerate(profile) if count)
        )
        print(
            f"beta2 orbit-group={group_index} profile={profile_index+1}/{len(profiles)} "
            f"states={state_count} seconds={time.time()-begun:.1f}",
            flush=True,
        )
    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"group-{group_index:02d}.npz"
    np.savez_compressed(
        destination,
        schema=np.asarray([ORBIT_SCHEMA]),
        candidate_sha256=np.asarray([metadata_digest]),
        group_index=np.asarray([group_index], dtype=np.int64),
        group_count=np.asarray([len(groups)], dtype=np.int64),
        profiles=np.asarray(profiles, dtype=np.int64),
        rows=np.asarray(rows, dtype=np.int64),
        targets=np.asarray(targets, dtype=np.int64),
    )
    print(
        f"{destination} rows={len(rows)} sha256={sha256_path(destination)} "
        f"seconds={time.time()-begun:.1f}",
        flush=True,
    )
    return destination


def load_orbits(directory: Path, metadata_digest: str):
    rows = []
    targets = []
    profiles = []
    files = []
    groups = g6.profile_groups()
    for group_index, expected_profiles in enumerate(groups):
        path = directory / f"group-{group_index:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != ORBIT_SCHEMA:
                raise ValueError(f"beta2 orbit schema mismatch: {path}")
            if str(data["candidate_sha256"][0]) != metadata_digest:
                raise ValueError(f"beta2 orbit metadata mismatch: {path}")
            if int(data["group_index"][0]) != group_index or int(data["group_count"][0]) != len(groups):
                raise ValueError(f"beta2 orbit group metadata mismatch: {path}")
            observed = [tuple(map(int, row)) for row in data["profiles"].tolist()]
            if observed != expected_profiles:
                raise ValueError(f"beta2 orbit profile mismatch: {path}")
            expected_targets = [
                g6.assignment_count(profile)
                * max(level for level, count in enumerate(profile) if count)
                for profile in expected_profiles
            ]
            if data["targets"].tolist() != expected_targets:
                raise ValueError(f"beta2 orbit target mismatch: {path}")
            rows.append(data["rows"])
            targets.append(data["targets"])
            profiles.append(data["profiles"])
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)})
    matrix = np.concatenate(rows, axis=0)
    target = np.concatenate(targets)
    profile_array = np.concatenate(profiles, axis=0)
    if matrix.shape != (364, 6_740) or target.shape != (364,):
        raise AssertionError((matrix.shape, target.shape))
    if [tuple(map(int, row)) for row in profile_array.tolist()] != g6.all_profiles():
        raise AssertionError("beta2 orbit profile coverage mismatch")
    return matrix, target, profile_array, files


def reduced_beta2(classes_path: Path, orbit_directory: Path):
    classes = beta2.load_classes(classes_path)
    raw, target, profiles, files = load_orbits(
        orbit_directory, str(classes["candidate_metadata_sha256"])
    )
    representatives = np.asarray(classes["representative_raw_indices"], dtype=np.int64)
    raw_to_class = np.asarray(classes["raw_to_class"], dtype=np.int64)
    if not np.array_equal(raw, raw[:, representatives[raw_to_class]]):
        raise AssertionError("beta2 exact quotient changes an orbit evaluation")
    return raw[:, representatives], target, profiles, files, classes


def build_cut_shard(
    selection_path: Path,
    classes_path: Path,
    shard_index: int,
    shard_count: int,
    output_directory: Path,
) -> Path:
    if not (0 <= shard_index < shard_count):
        raise ValueError("invalid beta2 cut shard")
    _selection, directions = cross.load_heldout_selection(selection_path)
    pairs, _metadata, _digest, _sizes = beta2.build_family()
    classes = beta2.load_classes(classes_path)
    representatives = list(map(int, classes["representative_raw_indices"]))
    start = len(representatives) * shard_index // shard_count
    stop = len(representatives) * (shard_index + 1) // shard_count
    row_index = {direction: index for index, direction in enumerate(directions)}
    matrix = np.empty((len(directions) + N, stop - start), dtype=np.int64)
    begun = time.time()
    for local_index, class_index in enumerate(range(start, stop)):
        matrix[:, local_index] = cross.g8.restricted_column(
            pairs[representatives[class_index]], row_index, len(directions)
        )
        if (local_index + 1) % 50 == 0:
            print(
                f"beta2 cut shard={shard_index}/{shard_count} "
                f"columns={local_index+1}/{stop-start} seconds={time.time()-begun:.1f}",
                flush=True,
            )
    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"beta2-shard-{shard_index:02d}-of-{shard_count:02d}.npz"
    np.savez_compressed(
        destination,
        schema=np.asarray([CUT_SHARD_SCHEMA]),
        selection_sha256=np.asarray([sha256_path(selection_path)]),
        classes_sha256=np.asarray([sha256_path(classes_path)]),
        shard_index=np.asarray([shard_index], dtype=np.int64),
        shard_count=np.asarray([shard_count], dtype=np.int64),
        class_indices=np.arange(start, stop, dtype=np.int64),
        matrix=matrix,
    )
    print(
        f"{destination} shape={matrix.shape} matrix_sha256={sha256_bytes(matrix.tobytes(order='C'))} "
        f"file_sha256={sha256_path(destination)} seconds={time.time()-begun:.1f}",
        flush=True,
    )
    return destination


def assemble_cut_matrix(
    selection_path: Path,
    classes_path: Path,
    shard_directory: Path,
    shard_count: int,
    output: Path,
) -> None:
    _selection, directions = cross.load_heldout_selection(selection_path)
    classes = beta2.load_classes(classes_path)
    class_count = int(classes["class_count"])
    matrices = []
    indices = []
    files = []
    for shard_index in range(shard_count):
        path = shard_directory / f"beta2-shard-{shard_index:02d}-of-{shard_count:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != CUT_SHARD_SCHEMA:
                raise ValueError(f"beta2 cut shard schema mismatch: {path}")
            if str(data["selection_sha256"][0]) != sha256_path(selection_path):
                raise ValueError(f"beta2 cut shard selection mismatch: {path}")
            if str(data["classes_sha256"][0]) != sha256_path(classes_path):
                raise ValueError(f"beta2 cut shard classes mismatch: {path}")
            if int(data["shard_index"][0]) != shard_index or int(data["shard_count"][0]) != shard_count:
                raise ValueError(f"beta2 cut shard index mismatch: {path}")
            matrices.append(data["matrix"])
            indices.append(data["class_indices"])
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)})
    matrix = np.concatenate(matrices, axis=1)
    class_indices = np.concatenate(indices)
    if not np.array_equal(class_indices, np.arange(class_count, dtype=np.int64)):
        raise AssertionError("beta2 cut shard class coverage mismatch")
    if matrix.shape != (len(directions) + N, class_count):
        raise AssertionError(matrix.shape)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        schema=np.asarray([CUT_MATRIX_SCHEMA]),
        selection_sha256=np.asarray([sha256_path(selection_path)]),
        classes_sha256=np.asarray([sha256_path(classes_path)]),
        class_indices=class_indices,
        matrix=matrix,
        shard_manifest_json=np.asarray([json.dumps(files, sort_keys=True, separators=(",", ":"))]),
    )
    print(
        f"{output} shape={matrix.shape} matrix_sha256={sha256_bytes(matrix.tobytes(order='C'))} "
        f"file_sha256={sha256_path(output)}",
        flush=True,
    )


def load_cut_matrix(
    path: Path, selection_path: Path, classes_path: Path, class_count: int
) -> np.ndarray:
    with np.load(path, allow_pickle=False) as data:
        if str(data["schema"][0]) != CUT_MATRIX_SCHEMA:
            raise ValueError("beta2 cut matrix schema mismatch")
        if str(data["selection_sha256"][0]) != sha256_path(selection_path):
            raise ValueError("beta2 cut matrix selection mismatch")
        if str(data["classes_sha256"][0]) != sha256_path(classes_path):
            raise ValueError("beta2 cut matrix classes mismatch")
        indices = data["class_indices"]
        matrix = data["matrix"]
    if not np.array_equal(indices, np.arange(class_count, dtype=np.int64)):
        raise ValueError("beta2 cut matrix class order mismatch")
    return matrix


def rank_report(
    cross_classes_path: Path,
    cross_orbit_directory: Path,
    beta2_classes_path: Path,
    beta2_orbit_directory: Path,
    selection_path: Path | None,
    same_cut_path: Path | None,
    cross_cut_path: Path | None,
    beta2_cut_path: Path | None,
    primes: list[int],
    exact: bool,
) -> dict[str, object]:
    baseline = cross.reduced_orbit_matrices(cross_classes_path, cross_orbit_directory)
    beta_matrix, beta_target, beta_profiles, beta_files, beta_classes = reduced_beta2(
        beta2_classes_path, beta2_orbit_directory
    )
    if not np.array_equal(beta_target, baseline["target"]) or not np.array_equal(
        beta_profiles, baseline["profiles"]
    ):
        raise AssertionError("beta2/baseline orbit convention mismatch")
    baseline_orbit = np.concatenate((baseline["same"], baseline["cross"]), axis=1)
    union_orbit = np.concatenate((baseline_orbit, beta_matrix), axis=1)
    systems = {
        "orbit_baseline": (baseline_orbit, beta_target),
        "orbit_beta2": (beta_matrix, beta_target),
        "orbit_union": (union_orbit, beta_target),
    }
    heldout = None
    if selection_path is not None:
        if same_cut_path is None or cross_cut_path is None or beta2_cut_path is None:
            raise ValueError("all three held-out matrices are required")
        _selection, directions = cross.load_heldout_selection(selection_path)
        same_cut = cross.load_cut_matrix(
            same_cut_path,
            "same",
            selection_path,
            baseline["same_classes_path"],
            baseline["same"].shape[1],
        )
        cross_cut = cross.load_cut_matrix(
            cross_cut_path,
            "cross",
            selection_path,
            cross_classes_path,
            baseline["cross"].shape[1],
        )
        beta_cut = load_cut_matrix(
            beta2_cut_path, selection_path, beta2_classes_path, beta_matrix.shape[1]
        )
        baseline_cut = np.concatenate((same_cut, cross_cut), axis=1)
        union_cut = np.concatenate((baseline_cut, beta_cut), axis=1)
        cut_target = np.zeros(len(directions) + N, dtype=np.int64)
        cut_target[-1] = factorial(N)
        joint_target = np.concatenate((beta_target, cut_target))
        systems.update(
            {
                "heldout_baseline": (baseline_cut, cut_target),
                "heldout_beta2": (beta_cut, cut_target),
                "heldout_union": (union_cut, cut_target),
                "joint_baseline": (
                    np.concatenate((baseline_orbit, baseline_cut), axis=0),
                    joint_target,
                ),
                "joint_beta2": (
                    np.concatenate((beta_matrix, beta_cut), axis=0), joint_target
                ),
                "joint_union": (
                    np.concatenate((union_orbit, union_cut), axis=0), joint_target
                ),
            }
        )
        heldout = {
            "selection_sha256": sha256_path(selection_path),
            "direction_count": len(directions),
            "same_cut_sha256": sha256_path(same_cut_path),
            "cross_cut_sha256": sha256_path(cross_cut_path),
            "beta2_cut_sha256": sha256_path(beta2_cut_path),
        }
    results = {}
    for name, (matrix, target) in systems.items():
        print(f"beta2 ranking {name} shape={matrix.shape}", flush=True)
        record = {
            "rows": matrix.shape[0],
            "columns": matrix.shape[1],
            "matrix_int64_c_sha256": sha256_bytes(matrix.tobytes(order="C")),
            "target_int64_c_sha256": sha256_bytes(target.tobytes(order="C")),
            "modular": cross.modular_rank_record(matrix, target, primes),
        }
        if exact:
            record["exact"] = cross.exact_rank_record(matrix, target, primes[0])
        results[name] = record
    return {
        "schema": RANK_SCHEMA,
        "n": N,
        "baseline": "G-0008 beta=1 same-component union G-0009 beta=0 cross-component",
        "beta2_family": "4,916 exact common-internal-edge classes",
        "beta2_classes_sha256": sha256_path(beta2_classes_path),
        "beta2_orbit_files": beta_files,
        "heldout": heldout,
        "primes": primes,
        "results": results,
        "claim_boundary": (
            "Exact ranks, when requested, use a nonzero rational minor plus complete row-span "
            "replay. Finite orbit/cut membership is not a global identity."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    orbit_parser = subparsers.add_parser("orbit-group")
    orbit_parser.add_argument("--group-index", type=int, required=True)
    orbit_parser.add_argument("--output-directory", type=Path, required=True)
    cut_parser = subparsers.add_parser("cut-shard")
    cut_parser.add_argument("--selection", type=Path, required=True)
    cut_parser.add_argument("--classes", type=Path, required=True)
    cut_parser.add_argument("--shard-index", type=int, required=True)
    cut_parser.add_argument("--shard-count", type=int, required=True)
    cut_parser.add_argument("--output-directory", type=Path, required=True)
    assemble_parser = subparsers.add_parser("assemble-cuts")
    assemble_parser.add_argument("--selection", type=Path, required=True)
    assemble_parser.add_argument("--classes", type=Path, required=True)
    assemble_parser.add_argument("--shard-directory", type=Path, required=True)
    assemble_parser.add_argument("--shard-count", type=int, required=True)
    assemble_parser.add_argument("--output", type=Path, required=True)
    rank_parser = subparsers.add_parser("rank")
    rank_parser.add_argument("--cross-classes", type=Path, required=True)
    rank_parser.add_argument("--cross-orbit-directory", type=Path, required=True)
    rank_parser.add_argument("--beta2-classes", type=Path, required=True)
    rank_parser.add_argument("--beta2-orbit-directory", type=Path, required=True)
    rank_parser.add_argument("--selection", type=Path)
    rank_parser.add_argument("--same-cut", type=Path)
    rank_parser.add_argument("--cross-cut", type=Path)
    rank_parser.add_argument("--beta2-cut", type=Path)
    rank_parser.add_argument("--prime", type=int, action="append", default=[])
    rank_parser.add_argument("--exact", action="store_true")
    rank_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "orbit-group":
        build_orbit_group(args.group_index, args.output_directory)
    elif args.command == "cut-shard":
        build_cut_shard(
            args.selection,
            args.classes,
            args.shard_index,
            args.shard_count,
            args.output_directory,
        )
    elif args.command == "assemble-cuts":
        assemble_cut_matrix(
            args.selection,
            args.classes,
            args.shard_directory,
            args.shard_count,
            args.output,
        )
    elif args.command == "rank":
        cross.write_json(
            args.output,
            rank_report(
                args.cross_classes,
                args.cross_orbit_directory,
                args.beta2_classes,
                args.beta2_orbit_directory,
                args.selection,
                args.same_cut,
                args.cross_cut,
                args.beta2_cut,
                args.prime or [1_000_003, 1_000_033],
                args.exact,
            ),
        )


if __name__ == "__main__":
    main()
