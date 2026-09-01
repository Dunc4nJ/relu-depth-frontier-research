#!/usr/bin/env python3
"""Bind the two hard-coded old-primary semantic controls to G-0113 input."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
from typing import Any


EXPECTED_PANEL_INPUT_SHA256 = (
    "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8"
)
EXPECTED_SEMANTIC_RECEIPT_SHA256 = (
    "f74d95d3fe443b42cfe28df9617e1435e78062418b718900b7010b7d2bd0209b"
)
EXPECTED_MAIN_SOURCE_SHA256 = (
    "128093d8f664f70036bec75f82df107413c338703b651206221e8da8fe2ce6e2"
)
EXPECTED_RECORDS = {
    5341: {
        "sequence": 5341,
        "orbit_index": 6573,
        "signed_class_sha256": "0a56e5e1c4ba00ca1ca3cbe7ceb2a2cb3629955c3980158b912284aaf51ece14",
        "signed_mass": 1,
        "active_vertices": 3,
        "negative_edges": [[0, 2]],
        "positive_edges": [[1, 2]],
    },
    66223: {
        "sequence": 66223,
        "orbit_index": 81231,
        "signed_class_sha256": "7eeeb8d17e925ec236e56bd5a64e14d7c57305afca58d40ff828417459139f7e",
        "signed_mass": 1,
        "active_vertices": 4,
        "negative_edges": [[0, 1]],
        "positive_edges": [[2, 3]],
    },
}


class BindingError(RuntimeError):
    """A frozen semantic-control binding failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def require_hash(path: Path, expected: str, label: str) -> None:
    observed = sha256_file(path)
    if observed != expected:
        raise BindingError(f"{label} hash drift: {observed}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("panel_solver_input", type=Path)
    parser.add_argument("semantic_receipt", type=Path)
    parser.add_argument("main_source", type=Path)
    parser.add_argument("output", type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise BindingError(f"refusing to overwrite {arguments.output}")

    inputs = [
        arguments.panel_solver_input.resolve(strict=True),
        arguments.semantic_receipt.resolve(strict=True),
        arguments.main_source.resolve(strict=True),
    ]
    expected_hashes = [
        EXPECTED_PANEL_INPUT_SHA256,
        EXPECTED_SEMANTIC_RECEIPT_SHA256,
        EXPECTED_MAIN_SOURCE_SHA256,
    ]
    labels = ["G-0113 panel input", "semantic receipt", "Rust main source"]
    for path, expected, label in zip(inputs, expected_hashes, labels, strict=True):
        require_hash(path, expected, label)
    opening = {str(path): sha256_file(path) for path in inputs}

    panel = json.loads(inputs[0].read_bytes())
    records = panel.get("records")
    if panel.get("schema") != "max11-g0113-panel-solver-input-v1":
        raise BindingError("panel-input schema drift")
    if not isinstance(records, list) or len(records) != 163_740:
        raise BindingError("panel-input record census drift")
    observed: dict[int, dict[str, Any]] = {}
    for record in records:
        sequence = record.get("sequence")
        if sequence in EXPECTED_RECORDS:
            if sequence in observed:
                raise BindingError(f"duplicate controlled sequence {sequence}")
            observed[sequence] = record
    if set(observed) != set(EXPECTED_RECORDS):
        raise BindingError("a controlled old-primary sequence is missing")
    for sequence, expected in EXPECTED_RECORDS.items():
        record = observed[sequence]
        for key, value in expected.items():
            if record.get(key) != value:
                raise BindingError(
                    f"old-primary sequence {sequence} field {key} drift: "
                    f"{record.get(key)!r}"
                )

    semantic = json.loads(inputs[1].read_bytes())
    if semantic.get("result") != "BOTH_KNOWN_OLD_SPAN_UNIT_COLUMNS_CERTIFIED":
        raise BindingError("semantic-control result drift")
    control = semantic["controls"]["sequence4259_old_primary_relation"]
    if control.get("old_primary_relation") != (
        "record = 2*primary_solver_sequence_5341 - primary_solver_sequence_66223"
    ):
        raise BindingError("semantic-control relation drift")
    declared = control.get("primary_map_record_hashes")
    expected_declared = {
        "solver_sequence_5341_orbit_index_6573": EXPECTED_RECORDS[5341][
            "signed_class_sha256"
        ],
        "solver_sequence_66223_orbit_index_81231": EXPECTED_RECORDS[66223][
            "signed_class_sha256"
        ],
    }
    if declared != expected_declared:
        raise BindingError("semantic receipt old-primary hash declaration drift")
    if semantic["bindings"]["source"]["main_source_sha256"] != EXPECTED_MAIN_SOURCE_SHA256:
        raise BindingError("semantic receipt/main-source binding drift")

    closing = {str(path): sha256_file(path) for path in inputs}
    if closing != opening:
        raise BindingError("input changed during semantic binding verification")
    result = {
        "schema": "g0179.semantic-old-primary-binding.v1",
        "result": "OLD_PRIMARY_HARDCODE_BINDINGS_CERTIFIED",
        "claim_boundary": (
            "This binds the exact two hard-coded primary Record values used by the "
            "sequence-4259 semantic control to frozen G-0113 panel-input sequences "
            "5341 and 66223. It does not independently recompute their normal forms, "
            "the 4259 identity, the 5771-square rank, or any representability claim."
        ),
        "controlled_records": {
            str(sequence): {key: observed[sequence][key] for key in expected}
            for sequence, expected in EXPECTED_RECORDS.items()
        },
        "all_exact_record_fields_match": True,
        "semantic_receipt_declares_matching_class_hashes": True,
        "semantic_receipt_binds_exact_main_source": True,
        "bindings": {
            "verifier": str(Path(__file__).resolve()),
            "verifier_sha256": sha256_file(Path(__file__).resolve()),
            "inputs_opening_sha256": opening,
        },
        "inputs_rehashed_unchanged_at_end": True,
    }
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(arguments.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as stream:
        stream.write(canonical_json(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(
        json.dumps(
            {
                "result": result["result"],
                "output": str(arguments.output.resolve()),
                "output_sha256": sha256_file(arguments.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
