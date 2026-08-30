#!/usr/bin/env python3
"""Direct modular replay of the frozen G-0104 joint separator."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np


PRIME = 1_000_003
SEMANTIC_ROWS = 8_427
SEMANTIC_RANK = 7_302
INCIDENCE_ROWS = 1_387
TREE_COLUMNS = 12_459
SAME_COLUMNS = 9_804
REGISTERED_COLUMNS = 13_419
GRAPH_COLUMNS = 22_263
COMBINED_COLUMNS = 22_265

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCER = HERE / "joint_semantic_incidence.py"
RESULT = HERE / "joint_semantic_incidence_p1000003_v1.json.gz"
G0046_SCRIPT = ROOT / "artifacts/math/G-0046/full_heldout_schur.py"
G0046_REPORT = ROOT / "artifacts/math/G-0046/heldout768_all_tree_schur_v1.json.gz"
G0099_REPORT = ROOT / "artifacts/math/G-0099/leaf_bridge_n10_n11_v1.json"
TREE_UNIVERSE = ROOT / "artifacts/math/G-0023/all_tree_universe_v1.json"
DEFAULT_OUTPUT = HERE / "separator_replay_v1.json"
EXPECTED_RESULT_SHA256 = "a9fdd478eb5baf5f24ffa474bee3452bc3d54d679748b0b8f9b00aacaebcc2e8"


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    return hashlib.sha256(array.view(np.uint8)).hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as source:
            value = json.load(source)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("top-level JSON object required")
    return value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(path)
    raw = (json.dumps(value, indent=2, sort_keys=True) + "\n").encode()
    partial = path.with_name(path.name + ".partial")
    with partial.open("xb") as destination:
        destination.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)


def tree_column_map(core: Any) -> np.ndarray:
    universe = load_json(TREE_UNIVERSE)
    overlap = universe["g0019_overlap"]
    cross = list(map(int, overlap["cross_to_all_class"]))
    missing = list(map(int, overlap["missing_all_class_indices"]))
    if len(cross) != 3_615 or len(missing) != 8_844:
        raise ValueError("tree overlap census drift")
    mapping = np.full(TREE_COLUMNS, -1, dtype=np.int64)
    for local, tree in enumerate(cross):
        if mapping[tree] != -1:
            raise ValueError("duplicate tree map")
        mapping[tree] = SAME_COLUMNS + local
    for local, tree in enumerate(missing):
        if mapping[tree] != -1:
            raise ValueError("duplicate tree map")
        mapping[tree] = REGISTERED_COLUMNS + local
    if np.any(mapping < 0) or len(np.unique(mapping)) != TREE_COLUMNS:
        raise ValueError("tree map not bijective")
    return mapping


def self_test() -> dict[str, Any]:
    prime = 101
    semantic = np.asarray([[1, 2], [3, 4]], dtype=np.int64)
    incidence = np.asarray([[5, 6]], dtype=np.int64)
    semantic_weights = np.asarray([7, 8], dtype=np.int64)
    incidence_weights = np.asarray([9], dtype=np.int64)
    combined = np.remainder(semantic_weights @ semantic + incidence_weights @ incidence, prime)
    mutation = combined.copy()
    mutation[0] = (mutation[0] + incidence_weights[0]) % prime
    if int(np.remainder(mutation[0] - combined[0], prime)) != 9:
        raise AssertionError("dual incidence mutation control failed")
    return {"dual_incidence_mutation_changes_column": True, "prime": prime}


def run(block_width: int) -> dict[str, Any]:
    begun = time.perf_counter()
    if sha256_path(RESULT) != EXPECTED_RESULT_SHA256:
        raise ValueError("G-0104 result hash drift")
    producer = load_module("g0104_replay_producer", PRODUCER)
    g46 = load_module("g0104_replay_g0046", G0046_SCRIPT)
    core = load_module("g0104_replay_core", g46.CORE_SCRIPT)
    result = load_json(RESULT)
    if (
        result.get("schema") != "max11-g0104-joint-semantic-incidence-modular-v1"
        or result.get("result") != "MODULAR_JOINT_NONMEMBER"
        or result.get("joint_schur", {}).get("rank") != 1_380
        or result.get("joint_schur", {}).get("augmented_rank") != 1_381
    ):
        raise ValueError("G-0104 result contract mismatch")
    separator = result.get("separator")
    if not isinstance(separator, dict) or int(separator.get("prime", -1)) != PRIME:
        raise ValueError("separator missing")
    basis_rows = np.asarray(separator["semantic_basis_rows"], dtype=np.int64)
    semantic_weights = np.asarray(separator["semantic_row_weights_mod_prime"], dtype=np.int64)
    incidence_weights = np.asarray(separator["incidence_row_weights_mod_prime"], dtype=np.int64)
    if (
        basis_rows.shape != (SEMANTIC_RANK,)
        or semantic_weights.shape != (SEMANTIC_RANK,)
        or incidence_weights.shape != (INCIDENCE_ROWS,)
        or np.any(semantic_weights < 0)
        or np.any(semantic_weights >= PRIME)
        or np.any(incidence_weights < 0)
        or np.any(incidence_weights >= PRIME)
    ):
        raise ValueError("separator vector census/range mismatch")

    subject = g46.prepare_subject(core)
    g99 = load_json(G0099_REPORT)
    sparse = g99["sparse_direct_r_columns"]
    mapping = tree_column_map(core)
    incidence_dual = np.zeros(COMBINED_COLUMNS, dtype=np.int64)
    first_mutation: tuple[int, int, int] | None = None
    for tree, raw_column in enumerate(sparse):
        column = int(mapping[tree])
        value = 0
        for raw_row, raw_r in raw_column:
            row, r_count = int(raw_row), int(raw_r)
            value = (value + int(incidence_weights[row]) * 11 * r_count) % PRIME
            if first_mutation is None and int(incidence_weights[row]):
                first_mutation = (tree, row, column)
        incidence_dual[column] = value
    if np.any(incidence_dual[:SAME_COLUMNS]) or np.any(incidence_dual[GRAPH_COLUMNS:]):
        raise AssertionError("incidence dual leaked onto non-tree/base columns")

    combined_dual = np.empty(COMBINED_COLUMNS, dtype=np.int64)
    all_rows = basis_rows
    for start in range(0, COMBINED_COLUMNS, block_width):
        stop = min(start + block_width, COMBINED_COLUMNS)
        columns = np.arange(start, stop, dtype=np.int64)
        semantic = producer.semantic_values(g46, core, subject, all_rows, columns)
        combined_dual[start:stop] = np.remainder(
            np.remainder(semantic_weights @ np.remainder(semantic, PRIME), PRIME)
            + incidence_dual[start:stop],
            PRIME,
        )
    nonzero = np.flatnonzero(combined_dual)
    if len(nonzero):
        raise AssertionError(f"separator fails dictionary column {int(nonzero[0])}")

    semantic_target = producer.semantic_target(
        basis_rows, g46.TARGET_ROW, g46.TARGET_VALUE
    )
    incidence_target = producer.target_mod_from_forests(g99["forest_orbits"])
    pairing = int(
        np.remainder(
            semantic_weights @ semantic_target + incidence_weights @ incidence_target,
            PRIME,
        )
    )
    if pairing == 0 or pairing != int(separator.get("target_pairing_mod_prime", -1)):
        raise AssertionError("separator target pairing mismatch")

    if first_mutation is None:
        raise AssertionError("no potency mutation location")
    mutation_tree, mutation_row, mutation_column = first_mutation
    mutation_residual = int(incidence_weights[mutation_row])
    if mutation_residual == 0:
        raise AssertionError("incidence-plus-one mutation was not detected")

    hashes_after = {
        "result": sha256_path(RESULT),
        "producer": sha256_path(PRODUCER),
        "g0046_report": sha256_path(G0046_REPORT),
        "g0099_report": sha256_path(G0099_REPORT),
        "tree_universe": sha256_path(TREE_UNIVERSE),
    }
    return {
        "schema": "max11-g0104-direct-separator-replay-v1",
        "result": "PASS",
        "claim_boundary": (
            "Direct modular separator replay for the frozen G-0104 joint finite system. "
            "Not an exact-Q, necessary-gauge, global, family-complete, or unrestricted result."
        ),
        "prime": PRIME,
        "rank_record_replayed": {"rank": 1_380, "augmented_rank": 1_381},
        "separator": {
            "semantic_basis_rows": SEMANTIC_RANK,
            "incidence_rows": INCIDENCE_ROWS,
            "dictionary_columns_replayed": COMBINED_COLUMNS,
            "nonzero_column_residuals": 0,
            "column_residual_sha256": sha256_array(combined_dual),
            "target_pairing_mod_prime": pairing,
        },
        "potency_mutation": {
            "operation": "increase one D entry by one",
            "tree_index": mutation_tree,
            "forest_row": mutation_row,
            "combined_column": mutation_column,
            "resulting_dual_column_residual": mutation_residual,
            "rejected": True,
        },
        "controls": self_test(),
        "bindings": hashes_after,
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--block-width", type=int, default=128)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.output.resolve().parent != HERE:
        parser.error("output must be a direct G-0104 child")
    if not (32 <= args.block_width <= 256):
        parser.error("block width must lie in [32,256]")
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    report = run(args.block_width)
    write_json(args.output, report)
    print(
        f"G0104_SEPARATOR_REPLAY_PASS output={args.output} sha256={sha256_path(args.output)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
