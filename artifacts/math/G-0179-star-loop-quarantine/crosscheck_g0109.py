#!/usr/bin/env python3
"""Compare the loop-aware G-0179 normal forms with frozen G-0109 exactly."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any


ROOT = Path("/data/projects/relu-depth-frontier-research")
HERE = Path(__file__).resolve().parent
RECORDS = HERE / "star_outside_primary_records.json"
G0109_MANIFEST = ROOT / "artifacts/math/G-0109/Cargo.toml"
G0109_SOURCE = ROOT / "artifacts/math/G-0109/src/main.rs"
G0109_BINARY = ROOT / "artifacts/math/G-0109/target/release/g0109-normal-form-probe"
G0179_MANIFEST = HERE / "Cargo.toml"
G0179_SOURCE = HERE / "src/lib.rs"
G0179_MAIN_SOURCE = HERE / "src/main.rs"
G0179_BINARY = HERE / "target/release/g0179-star-loop-pricer"
SELECTED_SEQUENCES = [1548, 22, 2986, 447]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def swap(record: dict[str, Any], sequence: int) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "signed_mass": record["signed_mass"],
        "active_vertices": record["active_vertices"],
        "negative_edges": record["positive_edges"],
        "positive_edges": record["negative_edges"],
        "negative_loop_count": record["positive_loop_count"],
        "positive_loop_count": record["negative_loop_count"],
    }


def semantic_normal_form(form: dict[str, Any]) -> dict[str, Any]:
    # Branch swap negates the raw signed word, so the chosen base/correction
    # decomposition and negative-word diagnostic count legitimately change.
    # The unique CPWL normal form is the final linear vector plus hinges.
    return {"linear": form["linear"], "hinges": form["hinges"]}


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit(
            f"usage: {Path(sys.argv[0]).name} FRESH_WORK_DIRECTORY OUTPUT.json"
        )
    work_directory = Path(sys.argv[1]).resolve()
    output_path = Path(sys.argv[2]).resolve()
    if work_directory.exists():
        raise RuntimeError(f"refusing to use existing work directory {work_directory}")
    if output_path.exists():
        raise RuntimeError(f"refusing to overwrite {output_path}")
    work_directory.mkdir(parents=True)
    document = json.loads(RECORDS.read_text(encoding="utf-8"))
    by_sequence = {record["sequence"]: record for record in document["records"]}
    originals = [by_sequence[sequence] for sequence in SELECTED_SEQUENCES]
    if [record["active_vertices"] for record in originals] != [2, 4, 5, 6]:
        raise RuntimeError("deterministic sample topology drift")
    compact_fields = (
        "sequence",
        "signed_mass",
        "active_vertices",
        "negative_edges",
        "positive_edges",
        "negative_loop_count",
        "positive_loop_count",
    )
    compact = [{key: record[key] for key in compact_fields} for record in originals]
    pairs: list[tuple[int, int]] = []
    records: list[dict[str, Any]] = []
    for index, record in enumerate(compact):
        records.append(record)
        swapped = swap(record, 900_000 + index)
        records.append(swapped)
        pairs.append((len(records) - 2, len(records) - 1))
    input_path = work_directory / "g0109_crosscheck_input.json"
    g0109_output = work_directory / "g0109_crosscheck_reference.json"
    g0179_output = work_directory / "g0109_crosscheck_candidate.json"
    for path in (input_path, g0109_output, g0179_output):
        if path.exists():
            raise RuntimeError(f"refusing to overwrite {path}")
    input_path.write_bytes(
        canonical_bytes({"schema": "max11-g0109-normal-form-input-v1", "records": records})
    )

    subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(G0109_MANIFEST)],
        check=True,
    )
    subprocess.run(
        ["cargo", "build", "--release", "--manifest-path", str(G0179_MANIFEST)],
        check=True,
    )
    subprocess.run([str(G0109_BINARY), str(input_path), str(g0109_output)], check=True)
    subprocess.run(
        [str(G0179_BINARY), "probe", str(input_path), str(g0179_output)], check=True
    )
    reference = json.loads(g0109_output.read_text(encoding="utf-8"))["normal_forms"]
    candidate = json.loads(g0179_output.read_text(encoding="utf-8"))["normal_forms"]
    if reference != candidate:
        for index, (expected, actual) in enumerate(zip(reference, candidate, strict=True)):
            if expected != actual:
                raise RuntimeError(f"normal-form mismatch at sample index {index}")
        raise RuntimeError("normal-form count mismatch")
    for original_index, swapped_index in pairs:
        if semantic_normal_form(candidate[original_index]) != semantic_normal_form(candidate[swapped_index]):
            raise RuntimeError(f"branch-swap mismatch for pair {original_index}/{swapped_index}")
    if not all(form["diagonal_multiplier"] == 1 for form in candidate):
        raise RuntimeError("diagonal multiplier drift")

    normal_form_digest = hashlib.sha256()
    for form in candidate:
        normal_form_digest.update(canonical_bytes(form))
    output = {
        "schema": "g0179.g0109-loop-normal-form-crosscheck.v1",
        "result": "EXACT_MATCH",
        "claim_boundary": (
            "Exact agreement on eight deterministic small loop-bearing normal forms "
            "(four records and their branch swaps) only; not a full-family proof."
        ),
        "sample_source_sequences": SELECTED_SEQUENCES,
        "sample_active_vertices": [2, 4, 5, 6],
        "normal_forms_compared": len(candidate),
        "branch_swap_pairs_compared": len(pairs),
        "diagonal_multiplier_one": True,
        "all_fields_exactly_equal": True,
        "branch_swaps_final_linear_and_hinges_exactly_equal": True,
        "canonical_normal_forms_sha256": normal_form_digest.hexdigest(),
        "bindings": {
            "crosscheck_source": str(Path(__file__).resolve()),
            "crosscheck_source_sha256": sha256_path(Path(__file__).resolve()),
            "records": str(RECORDS),
            "records_sha256": sha256_path(RECORDS),
            "input": str(input_path),
            "input_sha256": sha256_path(input_path),
            "g0109_source": str(G0109_SOURCE),
            "g0109_source_sha256": sha256_path(G0109_SOURCE),
            "g0109_binary": str(G0109_BINARY),
            "g0109_binary_sha256": sha256_path(G0109_BINARY),
            "g0109_output_sha256": sha256_path(g0109_output),
            "g0179_source": str(G0179_SOURCE),
            "g0179_source_sha256": sha256_path(G0179_SOURCE),
            "g0179_main_source": str(G0179_MAIN_SOURCE),
            "g0179_main_source_sha256": sha256_path(G0179_MAIN_SOURCE),
            "g0179_binary": str(G0179_BINARY),
            "g0179_binary_sha256": sha256_path(G0179_BINARY),
            "g0179_output_sha256": sha256_path(g0179_output),
        },
    }
    output_path.write_bytes(canonical_bytes(output))
    print(json.dumps({**{key: output[key] for key in ("result", "normal_forms_compared", "branch_swap_pairs_compared")}, "output": str(output_path), "output_sha256": sha256_path(output_path)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
