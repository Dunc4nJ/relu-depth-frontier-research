#!/usr/bin/env python3
"""Literal formal-assignment replay for all frozen G-0116 control vectors."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import resource
import struct
import sys
import time
from typing import Any

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
INPUT = HERE / "panel_solver_input_v1.json"
ROWS = ROOT / "artifacts/math/G-0111/dual_rows_v1.json"
GATE = ROOT / "artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json"
REFERENCE = ROOT / "artifacts/math/G-0109/transport_prototype.py"
EXPECTED = {
    INPUT: "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    ROWS: "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c",
    GATE: "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310",
    REFERENCE: "44821eb32bfd49b8a7480e6f6d3370808739e309148d1a59e56927c0547e6df2",
}
TARGET_I64_LE_SHA256 = "19beb89b85e3a95989be9a97d749a48609cb4912897bc20da60bfcd1690bf260"


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def digest_i128(values: np.ndarray) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(int(value).to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def digest_i64(values: list[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        digest.update(struct.pack("<q", int(value)))
    return digest.hexdigest()


def load_reference():
    spec = importlib.util.spec_from_file_location("g0113_frozen_g0109", REFERENCE)
    require(spec is not None and spec.loader is not None, "cannot load G-0109 reference")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def literal_value(reference, record: dict[str, Any], assignments: np.ndarray) -> int:
    return int(reference.literal_record_value(record, assignments))


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, sort_keys=True, separators=(",", ":"))
        destination.write("\n")
        destination.flush()
        os.fsync(destination.fileno())


def replay(output_path: Path) -> dict[str, object]:
    started = time.perf_counter()
    bindings = {str(path.relative_to(ROOT)): sha256_path(path) for path in EXPECTED}
    expected_bindings = {str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()}
    require(bindings == expected_bindings, f"input binding drift: {bindings}")
    reference = load_reference()
    source = json.loads(INPUT.read_text(encoding="utf-8"))
    rows_document = json.loads(ROWS.read_text(encoding="utf-8"))
    gate = json.loads(GATE.read_text(encoding="utf-8"))
    require(source["schema"] == "max11-g0113-panel-solver-input-v1", "input schema drift")
    require(rows_document["schema"] == "max11-g0111-actual-dual-rows-v1", "row schema drift")
    rows = rows_document["rows"]
    require(len(rows) == len(source["target"]) == 301, "panel dimension drift")
    expected_hashes = {
        int(control["sequence"]): str(control["panel_vector_sha256"])
        for control in gate["controls"]
    }
    require(len(expected_hashes) == 8, "gate control census drift")
    records = [source["records"][sequence] for sequence in expected_hashes]
    require(
        [int(record["sequence"]) for record in records] == list(expected_hashes),
        "control order drift",
    )

    literal = np.empty((len(records), len(rows)), dtype=np.int64)
    swapped = np.empty_like(literal)
    padding_mutant = dict(records[0])
    padding_mutant["signed_mass"] = int(padding_mutant["signed_mass"]) - 1
    mutant = np.empty(len(rows), dtype=np.int64)
    target = []
    assignment_census = 0
    for row_index, row in enumerate(rows):
        profile = [int(value) for value in row["profile"]]
        formal_stabilizer = math.prod(math.factorial(value) for value in profile)
        require(formal_stabilizer == int(row["formal_stabilizer"]), "formal stabilizer drift")
        assignments = reference.assignment_matrix(row)
        expected_assignments = math.factorial(11) // formal_stabilizer
        require(assignments.shape == (11, expected_assignments), "assignment census drift")
        assignment_census += expected_assignments
        target.append(expected_assignments * max(int(value) for value in row["levels"]))
        for record_index, record in enumerate(records):
            literal[record_index, row_index] = literal_value(reference, record, assignments)
            branch_swap = dict(record)
            branch_swap["negative_edges"] = record["positive_edges"]
            branch_swap["positive_edges"] = record["negative_edges"]
            swapped[record_index, row_index] = literal_value(reference, branch_swap, assignments)
        mutant[row_index] = literal_value(reference, padding_mutant, assignments)
        if (row_index + 1) % 50 == 0 or row_index + 1 == len(rows):
            print(f"G0113_LITERAL_PROGRESS rows={row_index + 1}/301", flush=True)

    require(np.array_equal(literal, swapped), "branch-swap literal replay failed")
    observed_hashes = {
        int(record["sequence"]): digest_i128(literal[index])
        for index, record in enumerate(records)
    }
    require(observed_hashes == expected_hashes, "literal vector hash replay failed")
    require(target == [int(value) for value in source["target"]], "literal target replay failed")
    target_hash = digest_i64(target)
    require(target_hash == TARGET_I64_LE_SHA256, "literal target hash drift")

    padding_mutant_rejected = not np.array_equal(mutant, literal[0])
    require(padding_mutant_rejected, "common-padding mutant escaped literal replay")

    report = {
        "schema": "max11-g0113-panel-literal-controls-v1",
        "result": "PASS_LITERAL_CONTROLS",
        "claim_boundary": (
            "Literal formal-assignment replay of eight frozen control vectors and the 301-entry "
            "target only; no all-record rank, global identity, completeness, or MAX11 claim."
        ),
        "bindings": bindings,
        "control_sequences": list(expected_hashes),
        "control_vector_sha256": observed_hashes,
        "rows": len(rows),
        "summed_assignment_columns": assignment_census,
        "target_i64_le_sha256": target_hash,
        "branch_swap_preserved": True,
        "common_padding_mutant_rejected": padding_mutant_rejected,
        "wall_seconds": time.perf_counter() - started,
        "maximum_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }
    write_exclusive(output_path, report)
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    print(json.dumps(replay(args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
