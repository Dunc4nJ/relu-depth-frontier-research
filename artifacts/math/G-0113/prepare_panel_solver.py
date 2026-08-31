#!/usr/bin/env python3
"""Prepare the exact signed records and 301-row target for the G-0113e scan."""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PREREGISTRATION = HERE / "PANEL_SOLVER_PREREGISTRATION.md"
MAP = HERE / "degree5_signed_orbit_representatives_v1.jsonl.gz"
TRANSFER = HERE / "common_nonloop_transfer_verification_v1.json"
ROWS = ROOT / "artifacts/math/G-0111/dual_rows_v1.json"
EXACT_MATRIX = ROOT / "artifacts/math/G-0108/restricted_exact_integer_augmented_v1.npy"
G0109 = ROOT / "artifacts/math/G-0109/transport_prototype.py"
G0111 = ROOT / "artifacts/math/G-0111/src/main.rs"

EXPECTED_HASHES = {
    PREREGISTRATION: "f2536d5d311570f5e676647bf5707e23bc00964547c80e2310f8f475e4c463b9",
    MAP: "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48",
    TRANSFER: "a829faa3543f2f4e8d9efab5c619674dc3f5c6d43f98a6adf46e6b1849c20b34",
    ROWS: "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c",
    EXACT_MATRIX: "d73747a4fb0c8061605ffbc557442f787f45af8966c25fded72b8437711f50c5",
    G0109: "44821eb32bfd49b8a7480e6f6d3370808739e309148d1a59e56927c0547e6df2",
    G0111: "ea88f3ff0aa1051f0d2a54d035a092de4e8283dc459a4329b84817f78da7d29b",
}
EXPECTED_RECORDS = 163_740
EXPECTED_DISJOINT = 133_449
EXPECTED_SHARED_ONLY = 30_291
SCHEMA = "max11-g0113-panel-solver-input-v1"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class PreparationError(RuntimeError):
    pass


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def pair_from_json(raw: Sequence[Sequence[Sequence[int]]]) -> Pair:
    if len(raw) != 2:
        raise PreparationError("pair side count drift")
    sides: list[Side] = []
    for side in raw:
        parsed = tuple(sorted((int(edge[0]), int(edge[1])) for edge in side))
        if len(parsed) != 5 or any(not (1 <= u <= v <= 11) for u, v in parsed):
            raise PreparationError("full representative pair drift")
        sides.append(parsed)
    return sides[0], sides[1]


def cancelled_pair(pair: Pair) -> Pair:
    left = Counter(pair[0])
    right = Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    negative = tuple(sorted(left.elements()))
    positive = tuple(sorted(right.elements()))
    if len(negative) != len(positive):
        raise PreparationError("cancelled masses differ")
    return negative, positive


def compact_signed(pair: Pair) -> tuple[list[list[int]], list[list[int]], int]:
    negative, positive = cancelled_pair(pair)
    support = sorted({vertex for edge in negative + positive for vertex in edge})
    labels = {vertex: index for index, vertex in enumerate(support)}
    compact_negative = [[labels[u], labels[v]] for u, v in negative]
    compact_positive = [[labels[u], labels[v]] for u, v in positive]
    return compact_negative, compact_positive, len(support)


def read_map_records() -> tuple[list[dict[str, object]], list[int]]:
    disjoint: list[dict[str, object]] = []
    shared_only: list[dict[str, object]] = []
    controls_by_mass: dict[int, int] = {}
    first_shared_only: int | None = None
    with gzip.open(MAP, "rt", encoding="ascii") as stream:
        header = json.loads(next(stream))
        if int(header.get("primary_signed_W_orbits", -1)) != EXPECTED_RECORDS:
            raise PreparationError("map header count drift")
        for expected_orbit, line in enumerate(stream):
            raw = json.loads(line)
            if int(raw["orbit_index"]) != expected_orbit:
                raise PreparationError("map orbit order drift")
            memberships = raw["memberships"]
            in_disjoint = bool(memberships["DISJOINT"])
            in_shared = bool(memberships["SHARED_DISTINCT"])
            if not (in_disjoint or in_shared):
                raise PreparationError("primary record lacks primary membership")
            pair = pair_from_json(raw["representative_pair"])
            if any(u == v for side in pair for u, v in side):
                raise PreparationError("loop in primary representative")
            negative, positive, active = compact_signed(pair)
            mass = len(negative)
            if mass != int(raw["topology"]["signed_mass"]):
                raise PreparationError("signed mass topology drift")
            if active != int(raw["topology"]["active_vertices"]):
                raise PreparationError("active support topology drift")
            descriptor = raw["primary_representative"]
            prepared: dict[str, object] = {
                "sequence": -1,
                "orbit_index": expected_orbit,
                "signed_class_sha256": str(raw["signed_class_sha256"]),
                "stage": "DISJOINT" if in_disjoint else "SHARED_DISTINCT_ONLY",
                "in_disjoint": in_disjoint,
                "in_shared_distinct": in_shared,
                "signed_mass": mass,
                "active_vertices": active,
                "negative_edges": negative,
                "positive_edges": positive,
                "representative": {
                    "source_term": int(descriptor["source_term"]),
                    "left_added_edge": list(map(int, descriptor["left_added_edge"])),
                    "right_added_edge": list(map(int, descriptor["right_added_edge"])),
                },
            }
            controls_by_mass.setdefault(mass, expected_orbit)
            if in_disjoint:
                disjoint.append(prepared)
            else:
                if first_shared_only is None:
                    first_shared_only = expected_orbit
                shared_only.append(prepared)
    if len(disjoint) != EXPECTED_DISJOINT or len(shared_only) != EXPECTED_SHARED_ONLY:
        raise PreparationError(
            f"stage census drift: {len(disjoint)}, {len(shared_only)}"
        )
    records = disjoint + shared_only
    for sequence, record in enumerate(records):
        record["sequence"] = sequence
    orbit_to_sequence = {int(record["orbit_index"]): index for index, record in enumerate(records)}
    if sorted(controls_by_mass) != list(range(6)) or first_shared_only is None:
        raise PreparationError("control stratum selection failed")
    control_orbits = [controls_by_mass[mass] for mass in range(6)] + [first_shared_only]
    control_sequences = sorted({orbit_to_sequence[orbit] for orbit in control_orbits})
    return records, control_sequences


def load_rows_and_target() -> tuple[dict[str, object], list[int], dict[str, object]]:
    rows_document = json.loads(ROWS.read_text(encoding="utf-8"))
    rows = rows_document.get("rows")
    if rows_document.get("schema") != "max11-g0111-actual-dual-rows-v1" or not isinstance(
        rows, list
    ) or len(rows) != 301:
        raise PreparationError("301-row descriptor contract drift")
    target: list[int] = []
    profile_histogram: Counter[tuple[int, ...]] = Counter()
    for row in rows:
        levels = list(map(int, row["levels"]))
        profile = list(map(int, row["profile"]))
        stabilizer = int(row["formal_stabilizer"])
        if levels != sorted(set(levels)) or levels[0] != 0:
            raise PreparationError("row levels not strict four-level panel")
        if len(profile) != 4 or sum(profile) != 11 or any(count <= 0 for count in profile):
            raise PreparationError("row formal profile drift")
        if stabilizer != math.prod(math.factorial(count) for count in profile):
            raise PreparationError("formal stabilizer drift")
        target.append(math.factorial(11) // stabilizer * levels[-1])
        profile_histogram[tuple(profile)] += 1
    exact = np.load(EXACT_MATRIX, mmap_mode="r", allow_pickle=False)
    if exact.shape != (301, 26_690) or exact.dtype != np.dtype("<i8"):
        raise PreparationError("G-0108 exact matrix contract drift")
    if not np.array_equal(np.asarray(target, dtype=np.int64), exact[:, -1]):
        raise PreparationError("target normalization disagrees with G-0108 exact matrix")
    target_array = np.asarray(target, dtype="<i8")
    receipt = {
        "rows": len(rows),
        "positive_profiles": len(profile_histogram),
        "profile_row_count_histogram": {
            ",".join(map(str, profile)): count
            for profile, count in sorted(profile_histogram.items())
        },
        "target_int64_le_sha256": hashlib.sha256(target_array.tobytes()).hexdigest(),
        "target_min": min(target),
        "target_max": max(target),
        "matches_g0108_exact_matrix_last_column": True,
    }
    return rows_document, target, receipt


def write_exclusive(path: Path, value: object) -> None:
    if path.exists():
        raise PreparationError(f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(canonical_bytes(value))
        handle.flush()
        os.fsync(handle.fileno())


def generate(input_path: Path, receipt_path: Path) -> dict[str, object]:
    bindings: dict[str, str] = {}
    for path, expected in EXPECTED_HASHES.items():
        observed = sha256_path(path)
        if observed != expected:
            raise PreparationError(f"binding drift for {path}: {observed}")
        bindings[str(path.relative_to(ROOT))] = observed
    records, controls = read_map_records()
    _rows_document, target, row_receipt = load_rows_and_target()
    prepared = {
        "schema": SCHEMA,
        "primes": [2_000_081, 3_000_017],
        "rows_path": str(ROWS.relative_to(ROOT)),
        "target": target,
        "control_sequences": controls,
        "records": records,
    }
    write_exclusive(input_path, prepared)
    receipt: dict[str, object] = {
        "schema": "max11-g0113-panel-solver-preparation-v1",
        "result": "PREPARED",
        "bindings": bindings,
        "input": {
            "path": str(input_path.relative_to(ROOT)),
            "sha256": sha256_path(input_path),
            "bytes": input_path.stat().st_size,
            "records": len(records),
            "disjoint_stage": EXPECTED_DISJOINT,
            "shared_distinct_only_stage": EXPECTED_SHARED_ONLY,
            "control_sequences": controls,
        },
        "rows_and_target": row_receipt,
        "claim_boundary": (
            "Input normalization and semantic-record preparation only; no fresh column "
            "evaluation, rank, target membership, panel identity, or global claim."
        ),
    }
    write_exclusive(receipt_path, receipt)
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input", type=Path, default=HERE / "panel_solver_input_v1.json"
    )
    parser.add_argument(
        "--receipt", type=Path, default=HERE / "panel_solver_preparation_v1.json"
    )
    args = parser.parse_args()
    receipt = generate(args.input.resolve(), args.receipt.resolve())
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
