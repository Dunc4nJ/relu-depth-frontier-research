#!/usr/bin/env python3
"""Preregistered modular MAX11 semantic + leaf/bridge incidence gate.

This is a finite-field candidate-generator experiment.  It does not assume
that the incidence condition is necessary and it cannot establish an
unrestricted lower bound.  See PREREGISTRATION.md for the frozen question.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
import hashlib
import importlib.util
import json
from math import factorial
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any, Sequence

import numpy as np


N = 11
PRIME = 1_000_003
SEMANTIC_ROWS = 8_427
SEMANTIC_RANK = 7_302
INCIDENCE_ROWS = 1_387
REGISTERED_COLUMNS = 13_419
SAME_COLUMNS = 9_804
CROSS_COLUMNS = 3_615
MISSING_COLUMNS = 8_844
GRAPH_COLUMNS = 22_263
COMBINED_COLUMNS = 22_265
FIVE_E_COLUMN = 22_263
FIVE_L_COLUMN = 22_264
TREE_COLUMNS = 12_459

SCHEMA = "max11-g0104-joint-semantic-incidence-modular-v1"
RESULT_MEMBER = "MODULAR_JOINT_MEMBER"
RESULT_NONMEMBER = "MODULAR_JOINT_NONMEMBER"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT_PATH = Path(__file__).resolve()
PREREG = HERE / "PREREGISTRATION.md"
G0046_SCRIPT = ROOT / "artifacts/math/G-0046/full_heldout_schur.py"
G0046_REPORT = ROOT / "artifacts/math/G-0046/heldout768_all_tree_schur_v1.json.gz"
G0049_SCRIPT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
G0049_REPORT = ROOT / "artifacts/math/G-0049/g0046_relation_cleanroom_verification_v1.json.gz"
G0099_MANIFEST = ROOT / "artifacts/math/G-0099/MANIFEST.json"
G0099_REPORT = ROOT / "artifacts/math/G-0099/leaf_bridge_n10_n11_v1.json"
TREE_UNIVERSE = ROOT / "artifacts/math/G-0023/all_tree_universe_v1.json"
DEFAULT_OUTPUT = HERE / "joint_semantic_incidence_p1000003_v1.json.gz"

FROZEN_DIRECT_HASHES = {
    "g0099_manifest": "508d4cec92e18da90f889bfbc1e4e34f73db5d56ee66bc0f65d21ee0a1b87121",
    "g0099_report": "a853803b0a59174d497cf9e1f9d6409db9157290a74cd6d56a5156adba36a7d9",
    "g0046_report": "924ecdb9dfdbf8e445fa1c46d0e3ac96d0cf2435227a18bd6a635cdda898cf2b",
    "g0033_report": "c82556e2569bd9618d7328f96c45a8f48e675b00bd2f3e5544962cd687fe8159",
    "g0033_missing_rows": "879bcbfe596bb6dd0ae3ed7f62396ca180280fbd0d250848a2ecbe0371cb7491",
    "g0033_missing_report": "be8c4cafd3afd8172d8fb50376470e44bde6bca6107e68557a4a59723165ea6a",
    "g0049_report": "77f3d68c022b752e7725537278d3cc4a658df183214992626b469ca4ab6dece1",
}


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def sha256_array(value: np.ndarray) -> str:
    array = np.ascontiguousarray(value)
    digest = hashlib.sha256()
    view = array.view(np.uint8).reshape(-1)
    for offset in range(0, view.nbytes, 1 << 24):
        digest.update(view[offset : offset + (1 << 24)])
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"not a regular contained input: {path}")
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as source:
            value = json.load(source)
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"top-level object required: {path}")
    return value


def load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {name} from {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def write_gzip(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial output: {partial}")
    raw = canonical_bytes(value)
    with partial.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    raise RuntimeError("MemAvailable absent from /proc/meminfo")


def require_memory(minimum: float, stage: str) -> float:
    observed = mem_available_gib()
    if observed < minimum:
        raise MemoryError(
            f"refusing {stage}: {observed:.2f} GiB available < {minimum:.2f} GiB"
        )
    return observed


def direct_paths(core: Any) -> dict[str, Path]:
    return {
        "g0099_manifest": G0099_MANIFEST,
        "g0099_report": G0099_REPORT,
        "g0046_report": G0046_REPORT,
        "g0033_report": ROOT / "artifacts/math/G-0033/all_tree_block_schur_prefix256_v1.json.gz",
        "g0033_missing_rows": core.MISSING_RESIDUAL_ROWS,
        "g0033_missing_report": core.MISSING_RESIDUAL_REPORT,
        "g0049_report": G0049_REPORT,
    }


def validate_direct_hashes(core: Any) -> dict[str, str]:
    observed = {name: sha256_path(path) for name, path in direct_paths(core).items()}
    if observed != FROZEN_DIRECT_HASHES:
        raise ValueError(f"frozen direct input hash drift: {observed}")
    return observed


def nmod_matrix(core: Any, array: np.ndarray, prime: int = PRIME) -> Any:
    return core.nmod_matrix(np.ascontiguousarray(array, dtype=np.int64), prime)


def semantic_values(
    g46: Any,
    core: Any,
    subject: dict[str, Any],
    rows: np.ndarray,
    columns: np.ndarray,
) -> np.ndarray:
    rows = np.asarray(rows, dtype=np.int64)
    columns = np.asarray(columns, dtype=np.int64)
    if np.any(rows < 0) or np.any(rows >= SEMANTIC_ROWS):
        raise ValueError("semantic row outside frozen 8,427-row domain")
    if np.any(columns < 0) or np.any(columns >= COMBINED_COLUMNS):
        raise ValueError("semantic column outside frozen dictionary")
    result = np.empty((len(rows), len(columns)), dtype=np.int64)
    old_pos = np.flatnonzero(rows < g46.BASE_ROWS)
    new_pos = np.flatnonzero(rows >= g46.BASE_ROWS)
    if len(old_pos):
        result[old_pos] = g46.base_basis_values(
            core,
            columns,
            rows[old_pos],
            subject["block"],
            subject["old_subject"],
            subject["old_batch"],
            subject["missing_selected"],
            subject["missing_residual"],
            subject["registered_new"],
        )
    if len(new_pos):
        heldout = g46.heldout_values(
            columns, subject["registered_new"], subject["missing_residual"]
        )
        result[new_pos] = heldout[rows[new_pos] - g46.BASE_ROWS]
    return result


def semantic_target(rows: np.ndarray, target_row: int, target_value: int) -> np.ndarray:
    target = np.zeros(len(rows), dtype=np.int64)
    target[rows == target_row] = target_value
    return target


def target_mod_from_forests(forests: Sequence[dict[str, Any]]) -> np.ndarray:
    if len(forests) != INCIDENCE_ROWS:
        raise ValueError("forest census drift")
    values = np.empty(INCIDENCE_ROWS, dtype=np.int64)
    for row, item in enumerate(forests):
        if int(item.get("index", -1)) != row:
            raise ValueError(f"forest index drift at {row}")
        value = Fraction(str(item.get("target_coefficient")))
        if value.denominator % PRIME == 0:
            raise ZeroDivisionError("target denominator is zero modulo prime")
        values[row] = value.numerator * pow(value.denominator, -1, PRIME) % PRIME
    return values


def validate_incidence_and_alignment(
    core: Any, subject: dict[str, Any], g99: dict[str, Any]
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    if (
        g99.get("schema") != "max11-g0099-leaf-bridge-n10-n11-v1"
        or g99.get("result") != "EXACT_INCIDENCE_SURJECTION"
        or g99.get("claim_class") != "exact"
    ):
        raise ValueError("G-0099 frozen report contract mismatch")
    manifest = load_json(G0099_MANIFEST)
    if (
        manifest.get("schema") != "max11-g0099-frozen-manifest-v1"
        or manifest.get("frozen") is not True
        or manifest.get("outputs", {}).get(
            "artifacts/math/G-0099/leaf_bridge_n10_n11_v1.json"
        )
        != FROZEN_DIRECT_HASHES["g0099_report"]
    ):
        raise ValueError("G-0099 manifest/report binding mismatch")

    universe = load_json(TREE_UNIVERSE)
    n11 = universe.get("n11_subject")
    overlap = universe.get("g0019_overlap")
    source = g99.get("tree_source")
    if not isinstance(n11, dict) or not isinstance(overlap, dict) or not isinstance(source, dict):
        raise ValueError("tree universe metadata missing")
    if (
        sha256_path(TREE_UNIVERSE) != source.get("source_sha256")
        or n11.get("representative_pairs_sha256")
        != source.get("source_representative_pairs_sha256")
        or int(source.get("tree_orbit_count", -1)) != TREE_COLUMNS
    ):
        raise ValueError("G-0099 tree order is not bound to live G-0023")

    cross_to_all = list(map(int, overlap.get("cross_to_all_class", [])))
    missing_indices = list(map(int, overlap.get("missing_all_class_indices", [])))
    if (
        len(cross_to_all) != CROSS_COLUMNS
        or len(missing_indices) != MISSING_COLUMNS
        or missing_indices != list(map(int, subject["missing_class_indices"]))
    ):
        raise ValueError("G-0023/G-0033 tree overlap census drift")
    tree_to_column = np.full(TREE_COLUMNS, -1, dtype=np.int64)
    for local, tree in enumerate(cross_to_all):
        if not (0 <= tree < TREE_COLUMNS) or tree_to_column[tree] != -1:
            raise ValueError("duplicate/out-of-range registered tree index")
        tree_to_column[tree] = SAME_COLUMNS + local
    for local, tree in enumerate(missing_indices):
        if not (0 <= tree < TREE_COLUMNS) or tree_to_column[tree] != -1:
            raise ValueError("duplicate/out-of-range missing tree index")
        tree_to_column[tree] = REGISTERED_COLUMNS + local
    if np.any(tree_to_column < 0) or len(np.unique(tree_to_column)) != TREE_COLUMNS:
        raise ValueError("tree-to-combined-column map is not a bijection")

    sparse = g99.get("sparse_direct_r_columns")
    reverse = g99.get("sparse_reverse_q_rows")
    forests = g99.get("forest_orbits")
    if (
        not isinstance(sparse, list)
        or len(sparse) != TREE_COLUMNS
        or not isinstance(reverse, list)
        or len(reverse) != INCIDENCE_ROWS
        or not isinstance(forests, list)
        or len(forests) != INCIDENCE_ROWS
        or canonical_sha256(sparse) != g99.get("sparse_direct_r_columns_sha256")
        or canonical_sha256(reverse) != g99.get("sparse_reverse_q_rows_sha256")
    ):
        raise ValueError("G-0099 sparse incidence serialization drift")

    incidence = np.zeros((INCIDENCE_ROWS, COMBINED_COLUMNS), dtype=np.int64)
    nonzeros = 0
    for tree, raw_column in enumerate(sparse):
        column = int(tree_to_column[tree])
        seen: set[int] = set()
        for raw_row, raw_r in raw_column:
            row, r_value = int(raw_row), int(raw_r)
            if not (0 <= row < INCIDENCE_ROWS) or row in seen or r_value <= 0:
                raise ValueError(f"malformed direct incidence at tree {tree}")
            seen.add(row)
            incidence[row, column] = 11 * r_value
            nonzeros += 1
    if nonzeros != 171_131 or int(np.count_nonzero(incidence)) != nonzeros:
        raise ValueError("incidence nonzero census drift")
    if np.any(incidence[:, :SAME_COLUMNS]) or np.any(incidence[:, GRAPH_COLUMNS:]):
        raise ValueError("D is nonzero on a declared non-tree/base column")

    # Subject-bound mutation control: compare one direct count with the
    # independently enumerated reverse count and stabilizers, then mutate r.
    mutation = g99.get("double_count", {}).get("one_incidence_mutation", {})
    mutation_tree = int(mutation.get("tree", -1))
    mutation_row = int(mutation.get("forest", -1))
    r_lookup = {int(row): int(value) for row, value in sparse[mutation_tree]}
    q_lookup = {int(tree): int(value) for tree, value in reverse[mutation_row]}
    r_value = r_lookup[mutation_row]
    q_value = q_lookup[mutation_tree]
    a_tree = int(g99["tree_stabilizers"][mutation_tree])
    a_forest = int(forests[mutation_row]["stabilizer"])
    if a_forest * r_value != a_tree * q_value:
        raise ValueError("unmutated direct/reverse stabilizer identity failed")
    if a_forest * (r_value + 1) == a_tree * q_value:
        raise AssertionError("incidence mutation was not rejected")

    target = target_mod_from_forests(forests)
    return incidence, target, tree_to_column, {
        "tree_to_column_bijection": True,
        "registered_tree_columns": CROSS_COLUMNS,
        "missing_tree_columns": MISSING_COLUMNS,
        "non_tree_and_base_D_columns_zero": True,
        "incidence_nonzeros": nonzeros,
        "direct_sparse_sha256": canonical_sha256(sparse),
        "reverse_sparse_sha256": canonical_sha256(reverse),
        "mutation": {
            "tree": mutation_tree,
            "forest": mutation_row,
            "original_identity_holds": True,
            "r_plus_one_identity_rejected": True,
        },
    }


def build_semantic_square(
    g46: Any,
    core: Any,
    subject: dict[str, Any],
    rows: np.ndarray,
    columns: np.ndarray,
    block_width: int,
    minimum_gib: float,
) -> np.ndarray:
    square = np.empty((len(rows), len(columns)), dtype=np.int64)
    begun = time.perf_counter()
    for start in range(0, len(columns), block_width):
        require_memory(minimum_gib, "semantic-square block")
        stop = min(start + block_width, len(columns))
        square[:, start:stop] = semantic_values(
            g46, core, subject, rows, columns[start:stop]
        )
        if stop == len(columns) or stop % (8 * block_width) == 0:
            print(
                f"G0104_SQUARE columns={stop}/{len(columns)} "
                f"seconds={time.perf_counter()-begun:.1f}",
                flush=True,
            )
    return square


def replay_semantic_vector(
    g46: Any,
    core: Any,
    subject: dict[str, Any],
    columns: np.ndarray,
    coefficients: np.ndarray,
    block_width: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    rows = np.arange(SEMANTIC_ROWS, dtype=np.int64)
    observed = np.zeros(SEMANTIC_ROWS, dtype=np.int64)
    for start in range(0, len(columns), block_width):
        stop = min(start + block_width, len(columns))
        values = semantic_values(g46, core, subject, rows, columns[start:stop])
        observed = np.remainder(
            observed
            + np.remainder(values, PRIME)
            @ np.remainder(coefficients[start:stop], PRIME),
            PRIME,
        )
    target = semantic_target(rows, g46.TARGET_ROW, g46.TARGET_VALUE)
    residual = np.remainder(observed - target, PRIME)
    nonzero = np.flatnonzero(residual)
    return residual, {
        "rows_replayed": SEMANTIC_ROWS,
        "nonzero_residuals": int(len(nonzero)),
        "first_nonzero_row": int(nonzero[0]) if len(nonzero) else None,
        "residual_sha256": sha256_array(residual),
    }


def support_descriptor(
    core: Any,
    subject: dict[str, Any],
    column: int,
    support_position: int,
    coefficient: int,
) -> dict[str, Any]:
    item: dict[str, Any] = {
        "support_position": support_position,
        "combined_union_column": column,
        "coefficient_mod_prime": coefficient,
    }
    if column < REGISTERED_COLUMNS:
        item.update(
            {
                "family": "same" if column < SAME_COLUMNS else "cross",
                "class_index": column if column < SAME_COLUMNS else column - SAME_COLUMNS,
                "pair": core.serialize_pair(subject["registered_pairs"][column], offset=1),
            }
        )
    elif column < GRAPH_COLUMNS:
        local = column - REGISTERED_COLUMNS
        item.update(
            {
                "family": "missing_all_tree",
                "missing_local_index": local,
                "all_tree_class_index": int(subject["missing_class_indices"][local]),
                "pair": core.serialize_pair(subject["missing_pairs"][local], offset=1),
            }
        )
    elif column == FIVE_E_COLUMN:
        item.update({"family": "zero_signed_graph_base", "base": "five_common_nonloops"})
    elif column == FIVE_L_COLUMN:
        item.update({"family": "zero_signed_graph_base", "base": "five_common_loops"})
    else:
        raise ValueError("support column outside dictionary")
    return item


def self_test(core: Any) -> dict[str, Any]:
    prime = 101
    square = np.asarray([[1, 2], [3, 5]], dtype=np.int64)
    a_extra = np.asarray([[7, 11], [13, 17]], dtype=np.int64)
    d_basis = np.asarray([[19, 23], [29, 31]], dtype=np.int64)
    d_extra = np.asarray([[37, 41], [43, 47]], dtype=np.int64)
    semantic_target_small = np.asarray([53, 59], dtype=np.int64)
    incidence_target_small = np.asarray([61, 67], dtype=np.int64)
    square_mod = core.nmod_matrix(square.tolist(), prime)
    lam = square_mod.transpose().solve(
        core.nmod_matrix(d_basis.T.tolist(), prime)
    ).transpose()
    delta = np.remainder(
        d_extra
        - core.matrix_to_numpy(lam * core.nmod_matrix(a_extra.tolist(), prime)),
        prime,
    )
    error = np.remainder(
        incidence_target_small
        - core.matrix_to_numpy(
            lam * core.nmod_matrix(semantic_target_small.reshape(-1, 1).tolist(), prime)
        ).reshape(-1),
        prime,
    )
    y = core.matrix_to_numpy(
        core.nmod_matrix(delta.tolist(), prime).solve(
            core.nmod_matrix(error.reshape(-1, 1).tolist(), prime)
        )
    ).reshape(-1)
    x = core.matrix_to_numpy(
        square_mod.solve(
            core.nmod_matrix(
                np.remainder(semantic_target_small - a_extra @ y, prime)
                .reshape(-1, 1)
                .tolist(),
                prime,
            )
        )
    ).reshape(-1)
    if np.any(np.remainder(square @ x + a_extra @ y - semantic_target_small, prime)):
        raise AssertionError("toy semantic Schur replay failed")
    if np.any(np.remainder(d_basis @ x + d_extra @ y - incidence_target_small, prime)):
        raise AssertionError("toy incidence Schur replay failed")
    mutated = np.remainder(d_basis @ x + d_extra @ y - (incidence_target_small + [1, 0]), prime)
    if int(np.count_nonzero(mutated)) != 1 or int(mutated[0]) != prime - 1:
        raise AssertionError("toy target mutation failed to trip")
    return {
        "toy_joint_schur_replay": True,
        "toy_target_plus_one_rejected": True,
        "prime": prime,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    begun = time.perf_counter()
    available_before = require_memory(args.minimum_available_gib, "G-0104 start")
    g46 = load_module("g0104_g0046", G0046_SCRIPT)
    core = load_module("g0104_g0033_core", g46.CORE_SCRIPT)
    g49 = load_module("g0104_g0049", G0049_SCRIPT)
    script_hash_before = sha256_path(SCRIPT_PATH)
    prereg_hash_before = sha256_path(PREREG)
    direct_before = validate_direct_hashes(core)
    transitive_before = g46.input_hashes(core)
    controls: dict[str, Any] = {"algebraic_self_test": self_test(core)}

    g46_report = load_json(G0046_REPORT)
    controls["g0046_live_bindings"] = g49.validate_g0046_bindings(
        g46_report, G0046_REPORT
    )
    relation_subject = g49.validate_relation(g46_report)
    subject = g46.prepare_subject(core)
    relation = relation_subject.relation
    basis_rows = np.asarray(relation["basis_rows"], dtype=np.int64)
    basis_columns = np.asarray(
        relation["basis_columns_combined_union"], dtype=np.int64
    )
    coefficient_record = next(
        item for item in relation["modular_records"] if int(item["prime"]) == PRIME
    )
    old_coefficients = np.asarray(
        coefficient_record["coefficients_mod_prime"], dtype=np.int64
    )
    if (
        basis_rows.shape != (SEMANTIC_RANK,)
        or basis_columns.shape != (SEMANTIC_RANK,)
        or old_coefficients.shape != (SEMANTIC_RANK,)
    ):
        raise ValueError("G-0046 final semantic basis census drift")

    g99 = load_json(G0099_REPORT)
    incidence, incidence_target, tree_to_column, alignment = validate_incidence_and_alignment(
        core, subject, g99
    )
    controls["tree_alignment_and_incidence_mutation"] = alignment

    selected_trees = np.asarray(g99["rank_and_image"]["selected_columns"], dtype=np.int64)
    selected_combined = tree_to_column[selected_trees]
    d_minor = incidence[:, selected_combined]
    d_minor_mod = nmod_matrix(core, d_minor)
    d_det = int(d_minor_mod.det())
    if d_det == 0:
        raise AssertionError("G-0099 selected D minor lost rank")
    d_preimage = core.matrix_to_numpy(
        d_minor_mod.solve(nmod_matrix(core, incidence_target.reshape(-1, 1)))
    ).reshape(-1)
    d_replay = np.remainder(d_minor @ d_preimage - incidence_target, PRIME)
    if np.any(d_replay):
        raise AssertionError("G-0099 target failed selected-minor replay")
    controls["incidence_surjectivity"] = {
        "rank": INCIDENCE_ROWS,
        "selected_minor_determinant_mod_prime": d_det,
        "target_in_image": True,
        "all_rows_replayed": True,
        "selected_tree_indices_sha256": sha256_array(selected_trees),
        "selected_combined_columns_sha256": sha256_array(selected_combined),
    }

    if args.preflight_only:
        return {
            "schema": SCHEMA,
            "result": "PREFLIGHT_ONLY",
            "claim_boundary": "Bindings, alignment, controls, and D-only replay; no joint solve ran.",
            "controls": controls,
            "bindings": {
                "direct_input_hashes": direct_before,
                "transitive_semantic_hashes": transitive_before,
                "script_sha256": script_hash_before,
                "preregistration_sha256": prereg_hash_before,
            },
        }

    square_started = time.perf_counter()
    semantic_square = build_semantic_square(
        g46,
        core,
        subject,
        basis_rows,
        basis_columns,
        args.block_width,
        args.minimum_available_gib,
    )
    square_sha = sha256_array(semantic_square)
    require_memory(args.minimum_available_gib, "semantic-square modularization")
    semantic_square_mod = nmod_matrix(core, semantic_square)
    semantic_det = int(semantic_square_mod.det())
    expected_det = int(coefficient_record["basis_square_determinant_mod_prime"])
    if semantic_det == 0 or semantic_det != expected_det:
        raise AssertionError(
            f"semantic basis determinant drift: {semantic_det} != {expected_det}"
        )
    basis_target = semantic_target(basis_rows, g46.TARGET_ROW, g46.TARGET_VALUE)
    basis_residual = np.remainder(
        np.remainder(semantic_square, PRIME) @ old_coefficients - basis_target,
        PRIME,
    )
    if np.any(basis_residual):
        raise AssertionError("G-0046 coefficient vector fails reconstructed semantic square")
    semantic_old_residual, semantic_old_replay = replay_semantic_vector(
        g46,
        core,
        subject,
        basis_columns,
        old_coefficients,
        args.block_width,
    )
    if np.any(semantic_old_residual):
        raise AssertionError("G-0046 semantic-only candidate failed full sampled replay")
    controls["semantic_only_g0046_membership"] = {
        **semantic_old_replay,
        "rank": SEMANTIC_RANK,
        "basis_determinant_mod_prime": semantic_det,
        "semantic_square_sha256": square_sha,
        "all_8427_rows_zero": True,
    }

    old_incidence_observed = np.remainder(
        incidence[:, basis_columns] @ old_coefficients, PRIME
    )
    old_incidence_residual = np.remainder(
        old_incidence_observed - incidence_target, PRIME
    )
    old_incidence_nonzero = np.flatnonzero(old_incidence_residual)
    if not len(old_incidence_nonzero):
        raise AssertionError("registered-only G-0046 solution unexpectedly satisfies D")
    controls["registered_only_solution_rejected_on_D"] = {
        "nonzero_rows": int(len(old_incidence_nonzero)),
        "first_nonzero_row": int(old_incidence_nonzero[0]),
        "first_nonzero_residual": int(old_incidence_residual[old_incidence_nonzero[0]]),
        "residual_sha256": sha256_array(old_incidence_residual),
        "rejected": True,
    }

    require_memory(args.minimum_available_gib, "incidence interpolation solve")
    interpolation_started = time.perf_counter()
    d_on_basis = incidence[:, basis_columns]
    lambda_mod = semantic_square_mod.transpose().solve(
        nmod_matrix(core, d_on_basis.T)
    ).transpose()
    lambda_values = core.matrix_to_numpy(lambda_mod)
    interpolation_check = np.remainder(
        core.matrix_to_numpy(lambda_mod * semantic_square_mod) - d_on_basis,
        PRIME,
    )
    if np.any(interpolation_check):
        raise AssertionError("incidence interpolation failed")
    error = np.remainder(
        incidence_target
        - core.matrix_to_numpy(
            lambda_mod * nmod_matrix(core, basis_target.reshape(-1, 1))
        ).reshape(-1),
        PRIME,
    )
    if np.any(np.remainder(error + old_incidence_residual, PRIME)):
        raise AssertionError("old-incidence-residual/Schur-error bridge failed")

    require_memory(args.minimum_available_gib, "joint Schur projection")
    delta = np.empty((INCIDENCE_ROWS, COMBINED_COLUMNS), dtype=np.int64)
    projection_started = time.perf_counter()
    for start in range(0, COMBINED_COLUMNS, args.block_width):
        require_memory(args.minimum_available_gib, "joint Schur projection block")
        stop = min(start + args.block_width, COMBINED_COLUMNS)
        columns = np.arange(start, stop, dtype=np.int64)
        values = semantic_values(g46, core, subject, basis_rows, columns)
        predicted = core.matrix_to_numpy(lambda_mod * nmod_matrix(core, values))
        delta[:, start:stop] = np.remainder(
            incidence[:, start:stop] - predicted, PRIME
        )
        if stop == COMBINED_COLUMNS or stop % (8 * args.block_width) == 0:
            print(
                f"G0104_PROJECT columns={stop}/{COMBINED_COLUMNS} "
                f"seconds={time.perf_counter()-projection_started:.1f}",
                flush=True,
            )
    if np.any(delta[:, basis_columns]):
        raise AssertionError("semantic basis columns have nonzero joint Schur delta")
    delta_sha = sha256_array(delta)

    require_memory(args.minimum_available_gib, "joint Schur rank")
    delta_mod = nmod_matrix(core, delta)
    rref, rank_obj = delta_mod.rref()
    rank = int(rank_obj)
    pivot_columns = core.pivot_columns(rref, rank, COMBINED_COLUMNS)
    augmented_rank = int(
        nmod_matrix(core, np.column_stack((delta, error))).rank()
    )
    member = rank == augmented_rank
    print(
        f"G0104_RESULT prime={PRIME} rank={rank} augmented={augmented_rank} member={member}",
        flush=True,
    )

    candidate: dict[str, Any] | None = None
    separator: dict[str, Any] | None = None
    if member:
        # Determine independent Schur rows as pivots of the transposed matrix.
        transposed_rref, transposed_rank_obj = delta_mod.transpose().rref()
        if int(transposed_rank_obj) != rank:
            raise AssertionError("joint Schur row/column ranks disagree")
        pivot_rows = core.pivot_columns(transposed_rref, rank, INCIDENCE_ROWS)
        extension_columns = np.asarray(pivot_columns, dtype=np.int64)
        extension_rows = np.asarray(pivot_rows, dtype=np.int64)
        schur_minor = delta[np.ix_(extension_rows, extension_columns)]
        schur_rhs = error[extension_rows]
        y = core.matrix_to_numpy(
            nmod_matrix(core, schur_minor).solve(
                nmod_matrix(core, schur_rhs.reshape(-1, 1))
            )
        ).reshape(-1)
        extension_basis_values = semantic_values(
            g46, core, subject, basis_rows, extension_columns
        )
        rhs = np.remainder(
            basis_target
            - core.matrix_to_numpy(
                nmod_matrix(core, extension_basis_values)
                * nmod_matrix(core, y.reshape(-1, 1))
            ).reshape(-1),
            PRIME,
        )
        x = core.matrix_to_numpy(
            semantic_square_mod.solve(nmod_matrix(core, rhs.reshape(-1, 1)))
        ).reshape(-1)
        full = np.zeros(COMBINED_COLUMNS, dtype=np.int64)
        if np.intersect1d(basis_columns, extension_columns).size:
            raise AssertionError("joint extension reused a semantic basis column")
        full[basis_columns] = x
        full[extension_columns] = y
        active = np.flatnonzero(full)
        semantic_residual, semantic_replay = replay_semantic_vector(
            g46, core, subject, active, full[active], args.block_width
        )
        incidence_residual = np.remainder(incidence @ full - incidence_target, PRIME)
        if np.any(semantic_residual) or np.any(incidence_residual):
            raise AssertionError("exported joint candidate failed full-row replay")
        mutated_target = incidence_target.copy()
        mutated_target[0] = (mutated_target[0] + 1) % PRIME
        mutation_residual = np.remainder(incidence @ full - mutated_target, PRIME)
        if (
            int(np.count_nonzero(mutation_residual)) != 1
            or int(mutation_residual[0]) != PRIME - 1
        ):
            raise AssertionError("target-plus-one mutation was not rejected")
        support = [
            support_descriptor(core, subject, int(column), position, int(full[column]))
            for position, column in enumerate(active)
        ]
        candidate = {
            "prime": PRIME,
            "construction": "lexicographic joint-Schur pivot minor",
            "rank": SEMANTIC_RANK + rank,
            "semantic_basis_columns": basis_columns.astype(int).tolist(),
            "incidence_schur_pivot_rows": extension_rows.astype(int).tolist(),
            "incidence_schur_extension_columns": extension_columns.astype(int).tolist(),
            "active_columns": active.astype(int).tolist(),
            "coefficients_mod_prime": full[active].astype(int).tolist(),
            "active_column_count": int(len(active)),
            "coefficient_vector_dense_sha256": sha256_array(full),
            "support": support,
            "support_sha256": canonical_sha256(support),
            "semantic_replay": semantic_replay,
            "incidence_replay": {
                "rows_replayed": INCIDENCE_ROWS,
                "nonzero_residuals": 0,
                "residual_sha256": sha256_array(incidence_residual),
            },
            "target_plus_one_mutation": {
                "coordinate": 0,
                "nonzero_residuals": 1,
                "residual_at_coordinate": int(mutation_residual[0]),
                "rejected": True,
            },
        }
        result = RESULT_MEMBER
    else:
        null_matrix, nullity_obj = delta_mod.transpose().nullspace()
        nullity = int(nullity_obj)
        null_values = core.matrix_to_numpy(null_matrix)
        witness: np.ndarray | None = None
        pairing = 0
        for column in range(nullity):
            trial = np.asarray(null_values[:, column], dtype=np.int64)
            trial_pairing = int(np.remainder(trial @ error, PRIME))
            if trial_pairing:
                witness = trial
                pairing = trial_pairing
                break
        if witness is None or np.any(np.remainder(witness @ delta, PRIME)):
            raise AssertionError("joint nonmembership yielded no valid Schur separator")
        old_weights = np.remainder(-(witness @ lambda_values), PRIME)
        if int(np.remainder(old_weights @ basis_target + witness @ incidence_target, PRIME)) == 0:
            raise AssertionError("lifted joint separator has zero target pairing")
        separator = {
            "prime": PRIME,
            "semantic_basis_rows": basis_rows.astype(int).tolist(),
            "semantic_row_weights_mod_prime": old_weights.astype(int).tolist(),
            "incidence_row_weights_mod_prime": witness.astype(int).tolist(),
            "all_dictionary_columns_annihilated": True,
            "target_pairing_mod_prime": pairing,
            "claim_boundary": "Finite-field separator for the frozen joint system only.",
        }
        result = RESULT_NONMEMBER

    direct_after = validate_direct_hashes(core)
    transitive_after = g46.input_hashes(core)
    script_hash_after = sha256_path(SCRIPT_PATH)
    prereg_hash_after = sha256_path(PREREG)
    if direct_after != direct_before or transitive_after != transitive_before:
        raise RuntimeError("a bound input changed during G-0104")
    if script_hash_after != script_hash_before or prereg_hash_after != prereg_hash_before:
        raise RuntimeError("script or preregistration changed during G-0104")

    return {
        "schema": SCHEMA,
        "result": result,
        "object_level_question": (
            "Over F_1000003, is MAX11 on all 8,427 frozen semantic rows jointly "
            "representable by the 22,265 G-0046 columns while its 12,459 tree "
            "coefficients map under frozen G-0099 D to the exact MAX10 c2 vector?"
        ),
        "claim_boundary": (
            "Finite-field membership/nonmembership for one frozen semantic row set, "
            "one finite dictionary, and an imposed incidence constraint. D is not known "
            "necessary. This is not a rational lift, global identity, family-completeness "
            "result, or unrestricted two-hidden-layer MAX11 theorem."
        ),
        "dimensions": {
            "semantic_rows": SEMANTIC_ROWS,
            "incidence_rows": INCIDENCE_ROWS,
            "joint_rows": SEMANTIC_ROWS + INCIDENCE_ROWS,
            "semantic_rank": SEMANTIC_RANK,
            "columns": COMBINED_COLUMNS,
            "tree_columns": TREE_COLUMNS,
            "incidence_nonzeros": 171_131,
        },
        "joint_schur": {
            "prime": PRIME,
            "rows": INCIDENCE_ROWS,
            "columns": COMBINED_COLUMNS,
            "rank": rank,
            "augmented_rank": augmented_rank,
            "target_in_span": member,
            "delta_int64_sha256": delta_sha,
            "error_int64_sha256": sha256_array(error),
            "pivot_columns": pivot_columns,
            "pivot_columns_sha256": canonical_sha256(pivot_columns),
        },
        "candidate": candidate,
        "separator": separator,
        "controls": controls,
        "timings": {
            "semantic_square_seconds": round(time.perf_counter() - square_started, 6),
            "incidence_interpolation_seconds": round(
                projection_started - interpolation_started, 6
            ),
            "schur_projection_seconds": round(
                time.perf_counter() - projection_started, 6
            ),
            "wall_seconds": round(time.perf_counter() - begun, 6),
        },
        "bindings": {
            "direct_input_hashes_before": direct_before,
            "direct_input_hashes_after": direct_after,
            "transitive_semantic_hashes_before": transitive_before,
            "transitive_semantic_hashes_after": transitive_after,
            "inputs_stable": True,
            "script_sha256_before": script_hash_before,
            "script_sha256_after": script_hash_after,
            "script_stable": True,
            "preregistration_sha256_before": prereg_hash_before,
            "preregistration_sha256_after": prereg_hash_after,
            "preregistration_stable": True,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
            "block_width": args.block_width,
            "available_gib_before": available_before,
            "available_gib_after": mem_available_gib(),
            "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--block-width", type=int, default=128)
    parser.add_argument("--minimum-available-gib", type=float, default=12.0)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not (32 <= args.block_width <= 256):
        parser.error("--block-width must lie in [32,256]")
    if args.minimum_available_gib < 12:
        parser.error("--minimum-available-gib must be at least 12")
    if args.output.resolve().parent != HERE:
        parser.error("output must be a direct G-0104 child")
    return args


def main() -> int:
    args = parse_args()
    g46 = load_module("g0104_g0046_selftest", G0046_SCRIPT)
    core = load_module("g0104_g0033_core_selftest", g46.CORE_SCRIPT)
    if args.self_test:
        print(json.dumps(self_test(core), sort_keys=True))
        return 0
    report = run(args)
    write_gzip(args.output, report)
    print(
        f"G0104_PASS result={report['result']} output={args.output} "
        f"sha256={sha256_path(args.output)}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
