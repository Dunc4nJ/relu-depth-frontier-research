#!/usr/bin/env python3
"""Incremental two-prime Schur update on the 768 G-0033 held-out rows.

The valid G-0033 prefix-256 basis has rank 6,883 on 7,659 frozen rows.  This
script treats that square basis as the new interpolation base and projects the
remaining rows 256:1024 through every 22,265 column: the 22,263 registered
plus all-tree graph atoms and the explicit 5E/5L zero-signed-graph bases.
It then either constructs a common two-prime extension relation or lifts a
finite-field separating dual.  Every displayed relation/separator is replayed
blockwise against all columns before it is serialized.

The result is finite-field and finite-coordinate only.  It is neither a
rational identity nor an unrestricted MAX11 statement.
"""

from __future__ import annotations

import argparse
from collections import Counter
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
PRIMES = (1_000_003, 1_000_033)
BASE_RANK = 6_883
BASE_ROWS = 7_659
OLD_ROWS = 7_403
ABSORBED_ROWS = 256
OLD_BATCH_ROWS = 256
AVAILABLE_ROWS = 1_024
NEW_ROW_START = ABSORBED_ROWS
NEW_ROWS = AVAILABLE_ROWS - NEW_ROW_START
REGISTERED_COLUMNS = 13_419
MISSING_COLUMNS = 8_844
GRAPH_COLUMNS = REGISTERED_COLUMNS + MISSING_COLUMNS
FIVE_E_COLUMN = GRAPH_COLUMNS
FIVE_L_COLUMN = GRAPH_COLUMNS + 1
COMBINED_COLUMNS = GRAPH_COLUMNS + 2
TARGET_ROW = 7_145
TARGET_VALUE = factorial(N)
LINEAR_ROW_START = TARGET_ROW - (N - 1)

SCHEMA = "max11-g0046-heldout768-registered-all-tree-bases-schur-v1"
FAVORABLE_BASE_SCHEMA = "max11-g0033-registered-all-tree-block-schur-prefix256-v1"
FAVORABLE_BASE_RESULT = (
    "TWO_PRIME_PREFIX256_TARGET_REMAINS_IN_REGISTERED_ALL_TREE_SPAN"
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G25 = ROOT / "artifacts/math/G-0025"
G33 = ROOT / "artifacts/math/G-0033"
CORE_SCRIPT = G33 / "all_tree_block_schur.py"
BASE_REPORT = G33 / "all_tree_block_schur_prefix256_v1.json.gz"
G0040_SOURCE = ROOT / "artifacts/math/G-0040/src/lib.rs"
G0040_REPORT = ROOT / "artifacts/math/G-0040/loop_inclusive_g0028_first_pricing_v1.json"
G0044_REPORT = ROOT / "artifacts/math/G-0044/wang_basu_transfer_report_v1.json"
DEFAULT_OUTPUT = HERE / "heldout768_all_tree_schur_v1.json.gz"
SCRIPT_PATH = Path(__file__).resolve()

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


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
        raise FileNotFoundError(f"not a contained regular input: {path}")
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
        raise FileExistsError(f"stale output partial exists: {partial}")
    raw = canonical_bytes(value)
    with partial.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def mem_available_gib() -> float:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) / (1024 * 1024)
    raise RuntimeError("MemAvailable absent from /proc/meminfo")


def input_paths(core: Any) -> dict[str, Path]:
    paths = {f"core_{key}": path for key, path in core.input_paths().items()}
    paths.update(
        {
            "g0033_base_report": BASE_REPORT,
            "g0033_core_script": CORE_SCRIPT,
            "g0040_loop_semantics_source": G0040_SOURCE,
            "g0040_pricing_report": G0040_REPORT,
            "g0044_span_transfer_report": G0044_REPORT,
        }
    )
    return paths


def input_hashes(core: Any) -> dict[str, str]:
    return {key: sha256_path(path) for key, path in input_paths(core).items()}


def nmod_matrix(core: Any, array: np.ndarray, prime: int) -> Any:
    return core.nmod_matrix(np.ascontiguousarray(array, dtype=np.int64), prime)


def validate_base_report(core: Any, report: dict[str, Any]) -> dict[str, Any]:
    relation = report.get("enlarged_modular_relations")
    dimensions = report.get("dimensions")
    bindings = report.get("bindings")
    if (
        report.get("schema") != FAVORABLE_BASE_SCHEMA
        or report.get("result") != FAVORABLE_BASE_RESULT
        or not isinstance(relation, dict)
        or not isinstance(dimensions, dict)
        or dimensions.get("current_rows") != OLD_ROWS
        or dimensions.get("new_prefix_rows") != ABSORBED_ROWS
        or dimensions.get("combined_columns") != GRAPH_COLUMNS
        or relation.get("new_rank") != BASE_RANK
        or not isinstance(bindings, dict)
    ):
        raise ValueError("G-0033 favorable base schema/result/dimensions mismatch")
    recorded_before = bindings.get("input_hashes_before")
    recorded_after = bindings.get("input_hashes_after")
    live_core_hashes = core.input_hashes()
    if (
        not isinstance(recorded_before, dict)
        or recorded_before != recorded_after
        or recorded_before != live_core_hashes
        or bindings.get("inputs_stable") is not True
        or bindings.get("script_stable") is not True
        or bindings.get("script_sha256_before") != sha256_path(CORE_SCRIPT)
        or bindings.get("script_sha256_after") != sha256_path(CORE_SCRIPT)
    ):
        raise ValueError("G-0033 base report no longer binds its live producer inputs")
    return relation


def validate_support(
    core: Any,
    support: Sequence[dict[str, Any]],
    columns: np.ndarray,
    registered_pairs: Sequence[Pair],
    missing_pairs: Sequence[Pair],
    missing_class_indices: Sequence[int],
    expected_sha256: str,
) -> dict[str, Any]:
    if len(support) != len(columns):
        raise ValueError("support/column census mismatch")
    observed_sha256 = hashlib.sha256(canonical_bytes(support)).hexdigest()
    if observed_sha256 != expected_sha256:
        raise ValueError("support descriptor hash mismatch")
    for position, (item, raw_column) in enumerate(zip(support, columns, strict=True)):
        column = int(raw_column)
        if not isinstance(item, dict) or item.get("support_position") != position:
            raise ValueError(f"malformed support position {position}")
        # Inherited G-0019/G-0025 descriptors predate the
        # ``combined_union_column`` field.  Their family/class pair is the
        # canonical column binding; newer descriptors additionally carry the
        # redundant absolute index, which must agree when present.
        explicit_columns = [
            int(item[key])
            for key in ("combined_union_column", "union_index")
            if key in item
        ]
        if explicit_columns and any(value != column for value in explicit_columns):
            raise ValueError(f"explicit support column mismatch at {position}")
        if column < REGISTERED_COLUMNS:
            family = "same" if column < 9_804 else "cross"
            class_index = column if family == "same" else column - 9_804
            if (
                item.get("family") != family
                or item.get("class_index") != class_index
                or item.get("pair")
                != core.serialize_pair(registered_pairs[column], offset=1)
            ):
                raise ValueError(f"registered support mismatch at {position}")
        else:
            local = column - REGISTERED_COLUMNS
            if (
                not (0 <= local < MISSING_COLUMNS)
                or item.get("family") != "missing_all_tree"
                or item.get("missing_local_index") != local
                or item.get("all_tree_class_index") != int(missing_class_indices[local])
                or item.get("pair") != core.serialize_pair(missing_pairs[local], offset=1)
            ):
                raise ValueError(f"missing-tree support mismatch at {position}")
    return {
        "support_descriptor_sha256": observed_sha256,
        "support_positions_and_columns_match": True,
        "family_class_and_pair_bindings_match": True,
    }


def base_atom_linear(column: int) -> np.ndarray:
    """Exact ordered-cone linear coordinates for the two s=0 span bases."""
    if column == FIVE_E_COLUMN:
        # Five common nonloops: 5 * 2*r*(N-2)!.
        return np.asarray(
            [5 * 2 * rank * factorial(N - 2) for rank in range(N)],
            dtype=np.int64,
        )
    if column == FIVE_L_COLUMN:
        # Five common loops: 5 * (N-1)! at every ordered rank.
        return np.full(N, 5 * factorial(N - 1), dtype=np.int64)
    raise ValueError(f"not a zero-signed-graph base column: {column}")


def base_atom_values(row_ids: np.ndarray, columns: np.ndarray) -> np.ndarray:
    result = np.zeros((len(row_ids), len(columns)), dtype=np.int64)
    linear_mask = (row_ids >= LINEAR_ROW_START) & (row_ids <= TARGET_ROW)
    linear_positions = np.flatnonzero(linear_mask)
    ranks = row_ids[linear_positions] - LINEAR_ROW_START
    for position, raw_column in enumerate(columns):
        linear = base_atom_linear(int(raw_column))
        result[linear_positions, position] = linear[ranks]
    return result


def validate_denominator_sources() -> dict[str, Any]:
    pricing = load_json(G0040_REPORT)
    transfer = load_json(G0044_REPORT)
    controls = pricing.get("controls")
    signed_transfer = transfer.get("signed_W_transfer")
    if (
        pricing.get("schema") != "max11-g0040-loop-aware-streaming-pricing-v1"
        or not isinstance(controls, dict)
        or controls.get("zero_record_equals_five_common_nonloops") is not True
        or not isinstance(controls.get("five_common_nonloops_residues"), list)
        or not isinstance(controls.get("five_common_loops_residues"), list)
        or transfer.get("schema") != "max-wang-basu-exact-transfer-audit-v1"
        or not isinstance(signed_transfer, dict)
        or signed_transfer.get("all_checks_hold") is not True
        or "five-common-loop" not in signed_transfer.get("MAX11_consequence", "")
    ):
        raise ValueError("G-0040/G-0044 denominator-source contract mismatch")
    return {
        "g0040_zero_record_is_5E": True,
        "g0040_5E_prices": controls["five_common_nonloops_residues"],
        "g0040_5L_prices": controls["five_common_loops_residues"],
        "g0044_signed_W_transfer_includes_both_bases": True,
    }


def base_basis_values(
    core: Any,
    indices: np.ndarray,
    basis_rows: np.ndarray,
    block: Any,
    old_subject: dict[str, Any],
    old_batch: np.ndarray,
    missing_selected: np.ndarray,
    missing_residual: np.ndarray,
    registered_new: np.ndarray,
) -> np.ndarray:
    result = np.empty((len(basis_rows), len(indices)), dtype=np.int64)
    graph_positions = np.flatnonzero(indices < GRAPH_COLUMNS)
    base_positions = np.flatnonzero(indices >= GRAPH_COLUMNS)
    if len(base_positions):
        if np.any(indices[base_positions] > FIVE_L_COLUMN):
            raise ValueError("combined column outside the two-base denominator")
        result[:, base_positions] = base_atom_values(
            basis_rows, indices[base_positions]
        )
    if not len(graph_positions):
        return result
    graph_indices = indices[graph_positions]
    old_positions = np.flatnonzero(basis_rows < OLD_ROWS)
    absorbed_positions = np.flatnonzero(basis_rows >= OLD_ROWS)
    if len(old_positions):
        result[np.ix_(old_positions, graph_positions)] = core.combined_basis_values(
            graph_indices,
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            basis_rows[old_positions],
        )
    if len(absorbed_positions):
        absorbed_indices = basis_rows[absorbed_positions] - OLD_ROWS
        if np.any(absorbed_indices < 0) or np.any(absorbed_indices >= ABSORBED_ROWS):
            raise ValueError("base basis row lies outside the absorbed prefix")
        absorbed = core.combined_new_values(
            graph_indices, registered_new, missing_residual, ABSORBED_ROWS
        )
        result[np.ix_(absorbed_positions, graph_positions)] = absorbed[absorbed_indices]
    return result


def heldout_values(
    indices: np.ndarray,
    registered_new: np.ndarray,
    missing_residual: np.ndarray,
) -> np.ndarray:
    # All held-out rows are hinge coordinates, so 5E and 5L are exactly zero.
    result = np.zeros((NEW_ROWS, len(indices)), dtype=np.int64)
    registered_positions = np.flatnonzero(indices < REGISTERED_COLUMNS)
    missing_positions = np.flatnonzero(
        (indices >= REGISTERED_COLUMNS) & (indices < GRAPH_COLUMNS)
    )
    if np.any(indices > FIVE_L_COLUMN):
        raise ValueError("combined column outside the two-base denominator")
    if len(registered_positions):
        result[:, registered_positions] = registered_new[
            np.ix_(
                np.arange(NEW_ROW_START, AVAILABLE_ROWS),
                indices[registered_positions],
            )
        ]
    if len(missing_positions):
        local = indices[missing_positions] - REGISTERED_COLUMNS
        residual_start = 1 + OLD_BATCH_ROWS + NEW_ROW_START
        residual_stop = 1 + OLD_BATCH_ROWS + AVAILABLE_ROWS
        result[:, missing_positions] = missing_residual[
            np.ix_(np.arange(residual_start, residual_stop), local)
        ]
    return result


def existing_values(
    core: Any,
    indices: np.ndarray,
    block: Any,
    old_subject: dict[str, Any],
    old_batch: np.ndarray,
    missing_selected: np.ndarray,
    missing_residual: np.ndarray,
    registered_new: np.ndarray,
) -> np.ndarray:
    result = np.empty((BASE_ROWS, len(indices)), dtype=np.int64)
    graph_positions = np.flatnonzero(indices < GRAPH_COLUMNS)
    base_positions = np.flatnonzero(indices >= GRAPH_COLUMNS)
    if len(graph_positions):
        graph_indices = indices[graph_positions]
        result[np.ix_(np.arange(OLD_ROWS), graph_positions)] = core.combined_basis_values(
            graph_indices,
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            np.arange(OLD_ROWS, dtype=np.int64),
        )
        result[np.ix_(np.arange(OLD_ROWS, BASE_ROWS), graph_positions)] = (
            core.combined_new_values(
                graph_indices, registered_new, missing_residual, ABSORBED_ROWS
            )
        )
    if len(base_positions):
        result[:, base_positions] = base_atom_values(
            np.arange(BASE_ROWS, dtype=np.int64), indices[base_positions]
        )
    if np.any(indices > FIVE_L_COLUMN):
        raise ValueError("combined column outside the two-base denominator")
    return result


def project_delta(
    core: Any,
    prime: int,
    lambda_mod: Any,
    basis_rows: np.ndarray,
    block: Any,
    old_subject: dict[str, Any],
    old_batch: np.ndarray,
    missing_selected: np.ndarray,
    missing_residual: np.ndarray,
    registered_new: np.ndarray,
    block_width: int,
) -> np.ndarray:
    delta = np.empty((NEW_ROWS, COMBINED_COLUMNS), dtype=np.int64)
    begun = time.perf_counter()
    for start in range(0, COMBINED_COLUMNS, block_width):
        stop = min(start + block_width, COMBINED_COLUMNS)
        indices = np.arange(start, stop, dtype=np.int64)
        basis = base_basis_values(
            core,
            indices,
            basis_rows,
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            registered_new,
        )
        prediction = core.matrix_to_numpy(lambda_mod * nmod_matrix(core, basis, prime))
        observed = heldout_values(indices, registered_new, missing_residual)
        delta[:, start:stop] = np.remainder(observed - prediction, prime)
        print(
            f"G0046_PROJECT prime={prime} columns={stop}/{COMBINED_COLUMNS} "
            f"seconds={time.perf_counter()-begun:.1f}",
            flush=True,
        )
    return delta


def prefix_records(core: Any, delta: np.ndarray, error: np.ndarray, prime: int) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for prefix in (128, 256, 512, NEW_ROWS):
        rank = int(nmod_matrix(core, delta[:prefix], prime).rank())
        augmented = int(
            nmod_matrix(core, np.column_stack((delta[:prefix], error[:prefix])), prime).rank()
        )
        records.append(
            {
                "heldout_prefix": prefix,
                "absolute_source_prefix": NEW_ROW_START + prefix,
                "rank_D": rank,
                "augmented_rank": augmented,
                "target_residual_in_span": rank == augmented,
            }
        )
    return records


def rank_and_pivots(
    core: Any, delta: np.ndarray, error: np.ndarray, prime: int
) -> dict[str, Any]:
    matrix = nmod_matrix(core, delta, prime)
    rref, rank_obj = matrix.rref()
    rank = int(rank_obj)
    columns = core.pivot_columns(rref, rank, delta.shape[1])
    transposed_rref, transposed_rank_obj = matrix.transpose().rref()
    if int(transposed_rank_obj) != rank:
        raise AssertionError("row/column modular ranks disagree")
    rows = core.pivot_columns(transposed_rref, rank, delta.shape[0])
    augmented_rank = int(
        nmod_matrix(core, np.column_stack((delta, error)), prime).rank()
    )
    graph_rank = sum(int(column < GRAPH_COLUMNS) for column in columns)
    registered_rank = sum(int(column < REGISTERED_COLUMNS) for column in columns)
    five_e_pivot = FIVE_E_COLUMN in columns
    five_l_pivot = FIVE_L_COLUMN in columns
    rank_with_5e = graph_rank + int(five_e_pivot)
    if five_l_pivot:
        rank_with_5l = graph_rank + 1
        five_l_quotient_status = "independent-of-graph-span"
    elif not five_e_pivot:
        rank_with_5l = graph_rank
        five_l_quotient_status = "in-graph-span"
    else:
        five_e_pivot_row = columns.index(FIVE_E_COLUMN)
        uses_five_e_direction = bool(rref[five_e_pivot_row, FIVE_L_COLUMN])
        rank_with_5l = graph_rank + int(uses_five_e_direction)
        five_l_quotient_status = (
            "shares-the-5E-new-quotient-direction"
            if uses_five_e_direction
            else "in-graph-span"
        )
    if rank != graph_rank + int(five_e_pivot) + int(five_l_pivot):
        raise AssertionError("5E/5L pivot reconciliation failed")
    return {
        "prime": prime,
        "rank_D": rank,
        "rank_D_with_target_residual": augmented_rank,
        "target_residual_in_column_span_D": augmented_rank == rank,
        "pivot_rows": rows,
        "pivot_columns_union": columns,
        "registered_pivot_column_count": registered_rank,
        "missing_tree_pivot_column_count": graph_rank - registered_rank,
        "zero_signed_graph_base_rank_effects": {
            "rank_without_5E_5L": graph_rank,
            "rank_with_5E_only": rank_with_5e,
            "rank_with_5L_only": rank_with_5l,
            "rank_with_both": rank,
            "five_E_pivot": five_e_pivot,
            "five_L_pivot_after_5E": five_l_pivot,
            "five_L_quotient_status": five_l_quotient_status,
            "five_E_delta_nonzero_count": int(np.count_nonzero(delta[:, FIVE_E_COLUMN])),
            "five_L_delta_nonzero_count": int(np.count_nonzero(delta[:, FIVE_L_COLUMN])),
            "five_E_delta_sha256": sha256_array(delta[:, FIVE_E_COLUMN]),
            "five_L_delta_sha256": sha256_array(delta[:, FIVE_L_COLUMN]),
        },
    }


def common_minor(
    core: Any, deltas: dict[int, np.ndarray], records: dict[int, dict[str, Any]]
) -> dict[str, Any] | None:
    ranks = {prime: int(records[prime]["rank_D"]) for prime in PRIMES}
    if len(set(ranks.values())) != 1 or next(iter(ranks.values())) == 0:
        return None
    rank = next(iter(ranks.values()))
    p1, p2 = PRIMES
    candidates = [
        (records[p1]["pivot_rows"], records[p1]["pivot_columns_union"], f"lex-RREF-mod-{p1}"),
        (records[p2]["pivot_rows"], records[p2]["pivot_columns_union"], f"lex-RREF-mod-{p2}"),
        (records[p1]["pivot_rows"], records[p2]["pivot_columns_union"], "p1-rows-p2-columns"),
        (records[p2]["pivot_rows"], records[p1]["pivot_columns_union"], "p2-rows-p1-columns"),
    ]
    seen: set[tuple[tuple[int, ...], tuple[int, ...]]] = set()
    for raw_rows, raw_columns, selection in candidates:
        rows = list(map(int, raw_rows))
        columns = list(map(int, raw_columns))
        key = (tuple(rows), tuple(columns))
        if key in seen or len(rows) != rank or len(columns) != rank:
            continue
        seen.add(key)
        determinants = []
        valid = True
        for prime in PRIMES:
            determinant = int(
                nmod_matrix(core, deltas[prime][np.ix_(rows, columns)], prime).det()
            )
            determinants.append({"prime": prime, "determinant": determinant})
            valid = valid and determinant != 0
        if valid:
            return {
                "selection": selection,
                "rank": rank,
                "new_batch_row_indices": rows,
                "extension_combined_columns": columns,
                "determinants_mod_primes": determinants,
                "common_nonsingular": True,
            }
    return None


def validate_combination_on_existing_rows(
    core: Any,
    base_columns: np.ndarray,
    base_coefficients: np.ndarray,
    extension_columns: np.ndarray,
    extension_coefficients: np.ndarray,
    prime: int,
    block: Any,
    old_subject: dict[str, Any],
    old_batch: np.ndarray,
    missing_selected: np.ndarray,
    missing_residual: np.ndarray,
    registered_new: np.ndarray,
    block_width: int,
) -> np.ndarray:
    observed = np.zeros(BASE_ROWS, dtype=np.int64)
    for indices, coefficients in (
        (base_columns, base_coefficients),
        (extension_columns, extension_coefficients),
    ):
        for start in range(0, len(indices), block_width):
            stop = min(start + block_width, len(indices))
            block_indices = indices[start:stop]
            values = existing_values(
                core,
                block_indices,
                block,
                old_subject,
                old_batch,
                missing_selected,
                missing_residual,
                registered_new,
            )
            observed = np.remainder(
                observed
                + np.remainder(values, prime)
                @ np.remainder(coefficients[start:stop], prime),
                prime,
            )
    return observed


def extension_support_descriptor(
    core: Any,
    column: int,
    support_position: int,
    registered_pairs: Sequence[Pair],
    missing_pairs: Sequence[Pair],
    missing_class_indices: Sequence[int],
) -> dict[str, Any]:
    if column < GRAPH_COLUMNS:
        return core.combined_support_descriptor(
            column,
            support_position,
            registered_pairs,
            missing_pairs,
            missing_class_indices,
        )
    if column == FIVE_E_COLUMN:
        label = "five_common_nonloops"
        linear = base_atom_linear(column)
    elif column == FIVE_L_COLUMN:
        label = "five_common_loops"
        linear = base_atom_linear(column)
    else:
        raise ValueError(f"extension column outside denominator: {column}")
    return {
        "support_position": support_position,
        "family": "zero_signed_graph_base",
        "base": label,
        "combined_union_column": column,
        "linear_coordinates": linear.astype(int).tolist(),
        "hinge_coordinates_all_zero": True,
    }


def build_relations(
    core: Any,
    minor: dict[str, Any],
    deltas: dict[int, np.ndarray],
    errors: dict[int, np.ndarray],
    square: np.ndarray,
    target_basis: np.ndarray,
    basis_rows: np.ndarray,
    base_columns: np.ndarray,
    base_support: list[dict[str, Any]],
    registered_pairs: Sequence[Pair],
    missing_pairs: Sequence[Pair],
    missing_class_indices: Sequence[int],
    block: Any,
    old_subject: dict[str, Any],
    old_batch: np.ndarray,
    missing_selected: np.ndarray,
    missing_residual: np.ndarray,
    registered_new: np.ndarray,
    block_width: int,
) -> dict[str, Any]:
    extension_columns = np.asarray(minor["extension_combined_columns"], dtype=np.int64)
    new_row_indices = np.asarray(minor["new_batch_row_indices"], dtype=np.int64)
    if np.intersect1d(extension_columns, base_columns).size:
        raise AssertionError("extension reuses a base support column")
    extension_basis = base_basis_values(
        core,
        extension_columns,
        basis_rows,
        block,
        old_subject,
        old_batch,
        missing_selected,
        missing_residual,
        registered_new,
    )
    new_base = heldout_values(base_columns, registered_new, missing_residual)
    new_extension = heldout_values(extension_columns, registered_new, missing_residual)
    target_existing = np.zeros(BASE_ROWS, dtype=np.int64)
    target_existing[TARGET_ROW] = TARGET_VALUE
    modular_records: list[dict[str, Any]] = []
    for prime in PRIMES:
        d_minor = deltas[prime][np.ix_(new_row_indices, extension_columns)]
        y = core.matrix_to_numpy(
            nmod_matrix(core, d_minor, prime).solve(
                nmod_matrix(core, errors[prime][new_row_indices].reshape(-1, 1), prime)
            )
        ).reshape(-1)
        rhs = np.remainder(
            target_basis
            - core.matrix_to_numpy(
                nmod_matrix(core, extension_basis, prime)
                * nmod_matrix(core, y.reshape(-1, 1), prime)
            ).reshape(-1),
            prime,
        )
        square_mod = nmod_matrix(core, square, prime)
        x = core.matrix_to_numpy(
            square_mod.solve(nmod_matrix(core, rhs.reshape(-1, 1), prime))
        ).reshape(-1)
        existing_observed = validate_combination_on_existing_rows(
            core,
            base_columns,
            x,
            extension_columns,
            y,
            prime,
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            registered_new,
            block_width,
        )
        if np.any(np.remainder(existing_observed - target_existing, prime)):
            raise AssertionError(f"extended relation failed an existing row at {prime}")
        new_observed = np.remainder(
            np.remainder(new_base, prime) @ x
            + np.remainder(new_extension, prime) @ y,
            prime,
        )
        if np.any(new_observed):
            first = int(np.flatnonzero(new_observed)[0])
            raise AssertionError(f"extended relation failed held-out row {first} at {prime}")
        coefficients = np.concatenate((x, y)).astype(np.int64, copy=False)
        schur_det = next(
            int(item["determinant"])
            for item in minor["determinants_mod_primes"]
            if int(item["prime"]) == prime
        )
        modular_records.append(
            {
                "prime": prime,
                "rank": len(coefficients),
                "basis_square_determinant_mod_prime": int(square_mod.det()) * schur_det % prime,
                "old_determinant_times_schur_determinant": True,
                "coefficients_mod_prime": coefficients.astype(int).tolist(),
                "coefficient_vector_int64_sha256": sha256_array(coefficients),
                "nonzero_coefficient_count": int(np.count_nonzero(coefficients)),
                "complete_existing_and_new_row_replay": True,
            }
        )
    support = [dict(item) for item in base_support]
    support.extend(
        extension_support_descriptor(
            core,
            int(column),
            BASE_RANK + offset,
            registered_pairs,
            missing_pairs,
            missing_class_indices,
        )
        for offset, column in enumerate(extension_columns)
    )
    return {
        "new_rank": BASE_RANK + len(extension_columns),
        "basis_rows": basis_rows.astype(int).tolist()
        + [BASE_ROWS + int(index) for index in new_row_indices],
        "basis_columns_combined_union": base_columns.astype(int).tolist()
        + extension_columns.astype(int).tolist(),
        "support": support,
        "support_descriptor_sha256": hashlib.sha256(canonical_bytes(support)).hexdigest(),
        "modular_records": modular_records,
    }


def separating_dual(
    core: Any,
    delta: np.ndarray,
    error: np.ndarray,
    lambdas: np.ndarray,
    target_basis: np.ndarray,
    basis_rows: np.ndarray,
    prime: int,
) -> dict[str, Any]:
    null_matrix, nullity_obj = nmod_matrix(core, delta.T, prime).nullspace()
    nullity = int(nullity_obj)
    null_values = core.matrix_to_numpy(null_matrix)
    witness: np.ndarray | None = None
    pairing = 0
    for column in range(nullity):
        candidate = np.asarray(null_values[:, column], dtype=np.int64)
        candidate_pairing = int(np.remainder(candidate @ error, prime))
        if candidate_pairing:
            witness = candidate
            pairing = candidate_pairing
            break
    if witness is None:
        raise AssertionError("rank exclusion yielded no separating null vector")
    if np.any(np.remainder(witness @ delta, prime)):
        raise AssertionError("separator does not annihilate the Schur columns")
    old_weights = np.remainder(
        -(witness @ np.remainder(lambdas, prime)), prime
    ).astype(np.int64, copy=False)
    if int(np.remainder(old_weights @ target_basis, prime)) != pairing:
        raise AssertionError("lifted separator target pairing mismatch")
    return {
        "prime": prime,
        "left_nullity": nullity,
        "selection": "first nullspace basis vector with nonzero target pairing",
        "old_basis_rows": basis_rows.astype(int).tolist(),
        "old_basis_row_weights_mod_prime": old_weights.astype(int).tolist(),
        "new_rows": [BASE_ROWS + index for index in range(NEW_ROWS)],
        "new_row_weights_mod_prime": witness.astype(int).tolist(),
        "all_combined_columns_annihilated": True,
        "target_pairing_mod_prime": pairing,
        "old_weights_int64_sha256": sha256_array(old_weights),
        "new_weights_int64_sha256": sha256_array(witness),
        "claim_boundary": (
            "Finite-field separator on 7,659+768 rows and 22,265 columns only; "
            "not an exact-Q or unrestricted-network lower bound."
        ),
    }


def self_test(core: Any) -> dict[str, Any]:
    prime = 101
    square = np.asarray([[1, 2], [3, 5]], dtype=np.int64)
    new_basis = np.asarray([[7, 11], [13, 17]], dtype=np.int64)
    candidates_on_basis = np.asarray([[19, 23], [29, 31]], dtype=np.int64)
    candidates_new = np.asarray([[37, 41], [43, 47]], dtype=np.int64)
    target = np.asarray([53, 59], dtype=np.int64)
    square_mod = nmod_matrix(core, square, prime)
    lambda_mod = square_mod.transpose().solve(
        nmod_matrix(core, new_basis.T, prime)
    ).transpose()
    delta = np.remainder(
        candidates_new
        - core.matrix_to_numpy(lambda_mod * nmod_matrix(core, candidates_on_basis, prime)),
        prime,
    )
    error = np.remainder(
        -core.matrix_to_numpy(
            lambda_mod * nmod_matrix(core, target.reshape(-1, 1), prime)
        ).reshape(-1),
        prime,
    )
    direct = np.block([[square, candidates_on_basis], [new_basis, candidates_new]])
    if int(nmod_matrix(core, direct, prime).rank()) != int(square_mod.rank()) + int(
        nmod_matrix(core, delta, prime).rank()
    ):
        raise AssertionError("toy Schur rank identity failed")
    rank = int(nmod_matrix(core, delta, prime).rank())
    augmented = int(nmod_matrix(core, np.column_stack((delta, error)), prime).rank())
    mutated = error.copy()
    mutated[0] = (mutated[0] + 1) % prime
    mutant_augmented = int(
        nmod_matrix(core, np.column_stack((delta, mutated)), prime).rank()
    )
    if rank > augmented or mutant_augmented < rank:
        raise AssertionError("toy membership/mutant rank monotonicity failed")
    g6 = load_module("g0046_base_atom_g6_selftest", core.G6_SCRIPT)
    repeated_edge = tuple((1, 2) for _ in range(5))
    identical_nonloop = g6.exact_hinge_column((repeated_edge, repeated_edge))
    five_e = base_atom_linear(FIVE_E_COLUMN)
    five_l = base_atom_linear(FIVE_L_COLUMN)
    if (
        identical_nonloop.hinges
        or np.asarray(identical_nonloop.linear, dtype=np.int64).tolist()
        != five_e.tolist()
        or five_l.tolist() != [5 * factorial(N - 1)] * N
    ):
        raise AssertionError("5E/5L exact linear semantics self-test failed")
    probe_rows = np.asarray(
        [0, LINEAR_ROW_START, TARGET_ROW, TARGET_ROW + 1], dtype=np.int64
    )
    probe = base_atom_values(
        probe_rows, np.asarray([FIVE_E_COLUMN, FIVE_L_COLUMN], dtype=np.int64)
    )
    expected_probe = np.asarray(
        [
            [0, 0],
            [int(five_e[0]), int(five_l[0])],
            [int(five_e[-1]), int(five_l[-1])],
            [0, 0],
        ],
        dtype=np.int64,
    )
    if not np.array_equal(probe, expected_probe):
        raise AssertionError("5E/5L row-placement self-test failed")
    wrong_five_e = np.full(N, 10 * factorial(N - 1), dtype=np.int64)
    wrong_five_l = np.asarray(
        [5 * 2 * rank * factorial(N - 1) for rank in range(N)], dtype=np.int64
    )
    if np.array_equal(five_e, wrong_five_e) or np.array_equal(five_l, wrong_five_l):
        raise AssertionError("5E/5L hostile semantics mutants escaped")
    return {
        "toy_schur_rank_identity": True,
        "toy_target_membership_defined": augmented in (rank, rank + 1),
        "target_plus_one_mutant_evaluated": True,
        "zero_signed_graph_bases": {
            "5E_matches_independent_identical_nonloop_G6_column": True,
            "5L_matches_grouped_five_loop_formula": True,
            "hinge_coordinates_all_zero": True,
            "row_placement_checked": True,
            "constant_5E_and_rank_scaled_5L_mutants_rejected": True,
            "five_E_linear": five_e.astype(int).tolist(),
            "five_L_linear": five_l.astype(int).tolist(),
        },
        "heldout_partition": {
            "absorbed": ABSORBED_ROWS,
            "available": AVAILABLE_ROWS,
            "heldout": NEW_ROWS,
            "reconciles": ABSORBED_ROWS + NEW_ROWS == AVAILABLE_ROWS,
        },
        "core_self_test": core.self_test(),
    }


def resource_preflight(block_width: int) -> dict[str, Any]:
    return {
        "square_int64_bytes": BASE_RANK * BASE_RANK * 8,
        "heldout_support_int64_bytes": NEW_ROWS * BASE_RANK * 8,
        "two_delta_int64_bytes": 2 * NEW_ROWS * COMBINED_COLUMNS * 8,
        "largest_basis_block_int64_bytes": BASE_RANK * block_width * 8,
        "reference_prefix256_run": {
            "wall_seconds": 746.691443,
            "process_max_rss_kib": 4_739_092,
            "source_report_sha256": sha256_path(BASE_REPORT),
        },
        "projection_row_ratio_vs_reference": NEW_ROWS / ABSORBED_ROWS,
        "planning_estimate_not_a_measurement": (
            "roughly 20-45 minutes and 6-12 GiB RSS; the completed report's live "
            "wall_seconds/process_max_rss_kib supersede this estimate"
        ),
    }


def prepare_subject(core: Any) -> dict[str, Any]:
    base = load_json(BASE_REPORT)
    relation = validate_base_report(core, base)
    basis_rows = np.asarray(relation.get("basis_rows", []), dtype=np.int64)
    base_columns = np.asarray(
        relation.get("basis_columns_combined_union", []), dtype=np.int64
    )
    support = relation.get("support")
    modular_records = relation.get("modular_records")
    if (
        basis_rows.shape != (BASE_RANK,)
        or base_columns.shape != (BASE_RANK,)
        or len(np.unique(basis_rows)) != BASE_RANK
        or len(np.unique(base_columns)) != BASE_RANK
        or np.any(basis_rows < 0)
        or np.any(basis_rows >= BASE_ROWS)
        or np.any(base_columns < 0)
        or np.any(base_columns >= GRAPH_COLUMNS)
        or not isinstance(support, list)
        or len(support) != BASE_RANK
        or not isinstance(modular_records, list)
        or [int(item.get("prime", -1)) for item in modular_records] != list(PRIMES)
    ):
        raise ValueError("G-0033 base basis/support/modular census mismatch")

    directions, _, source_stream_sha256 = core.load_directions_and_residues()
    if len(directions) != AVAILABLE_ROWS:
        raise ValueError("source direction census is not 1,024")
    missing_pairs, missing_class_indices, missing_index_sha = core.load_missing_pairs()
    (
        registered_new,
        missing_residual,
        missing_selected,
        old_batch,
        row_bindings,
    ) = core.validate_row_inputs(directions, missing_index_sha)
    relation_loader = core.load_module("g0046_relation_loader", core.RELATION_SCRIPT)
    old_subject = relation_loader.load_subject()
    block = core.load_module("g0046_block_loader", core.BLOCK_SCRIPT)
    row_loader = core.load_module("g0046_pair_loader", core.ROW_SCRIPT)
    same_pairs, cross_pairs, pair_census = row_loader.load_registered_pairs()
    registered_pairs = same_pairs + cross_pairs
    if len(registered_pairs) != REGISTERED_COLUMNS:
        raise AssertionError("registered pair census mismatch")
    common_edge_histogram: Counter[int] = Counter()
    identical_branch_count = 0
    for left, right in registered_pairs:
        left_counter = Counter(left)
        right_counter = Counter(right)
        common_edge_histogram[sum((left_counter & right_counter).values())] += 1
        identical_branch_count += int(left_counter == right_counter)
    if identical_branch_count != 0 or dict(sorted(common_edge_histogram.items())) != {
        0: 11_542,
        1: 1_877,
    }:
        raise ValueError("registered denominator common-edge census drifted")
    denominator_controls = validate_denominator_sources()
    denominator_controls.update(
        {
            "registered_pair_count": len(registered_pairs),
            "registered_identical_branch_count": identical_branch_count,
            "registered_common_edge_count_histogram": {
                str(key): value for key, value in sorted(common_edge_histogram.items())
            },
            "explicit_5E_5L_are_not_duplicate_registered_pairs": True,
        }
    )
    support_controls = validate_support(
        core,
        support,
        base_columns,
        registered_pairs,
        missing_pairs,
        missing_class_indices,
        str(relation.get("support_descriptor_sha256", "")),
    )
    return {
        "base": base,
        "relation": relation,
        "basis_rows": basis_rows,
        "base_columns": base_columns,
        "support": support,
        "modular_records": modular_records,
        "directions": directions,
        "source_stream_sha256": source_stream_sha256,
        "missing_pairs": missing_pairs,
        "missing_class_indices": missing_class_indices,
        "registered_new": registered_new,
        "missing_residual": missing_residual,
        "missing_selected": missing_selected,
        "old_batch": old_batch,
        "row_bindings": row_bindings,
        "old_subject": old_subject,
        "block": block,
        "registered_pairs": registered_pairs,
        "pair_census": pair_census,
        "denominator_controls": denominator_controls,
        "support_controls": support_controls,
    }


def source_refutation_control(core: Any, subject: dict[str, Any]) -> dict[str, Any]:
    base_columns = subject["base_columns"]
    registered_new = subject["registered_new"]
    missing_residual = subject["missing_residual"]
    values = heldout_values(base_columns, registered_new, missing_residual)
    directions = subject["directions"]
    records = []
    for modular_record in subject["modular_records"]:
        prime = int(modular_record["prime"])
        coefficients = np.asarray(
            modular_record.get("coefficients_mod_prime", []), dtype=np.int64
        )
        if coefficients.shape != (BASE_RANK,):
            raise ValueError(f"malformed base coefficients at {prime}")
        residual = np.remainder(np.remainder(values, prime) @ coefficients, prime)
        nonzero = np.flatnonzero(residual)
        if len(nonzero) != 681 or int(nonzero[0]) != 0:
            raise AssertionError(f"held-out refutation control drifted at {prime}")
        expected_first = {1_000_003: 825_403, 1_000_033: 397_784}[prime]
        if int(residual[0]) != expected_first:
            raise AssertionError(f"held-out first residual drifted at {prime}")
        records.append(
            {
                "prime": prime,
                "nonzero_heldout_rows": int(len(nonzero)),
                "first_nonzero_heldout_offset": int(nonzero[0]),
                "first_nonzero_absolute_source_row": NEW_ROW_START + int(nonzero[0]),
                "first_nonzero_direction": list(directions[NEW_ROW_START + int(nonzero[0])]),
                "first_nonzero_residual": int(residual[nonzero[0]]),
                "residual_vector_int64_sha256": sha256_array(residual),
            }
        )
    return {
        "result": "PREFIX256_RELATION_REFUTED_ON_HELDOUT_ROWS",
        "heldout_rows": NEW_ROWS,
        "records": records,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    begun = time.perf_counter()
    available_before = mem_available_gib()
    if available_before < args.minimum_available_gib:
        raise MemoryError(
            f"refusing full Schur run with {available_before:.2f} GiB available; "
            f"minimum is {args.minimum_available_gib:.2f} GiB"
        )
    core = load_module("g0046_g0033_core", CORE_SCRIPT)
    script_hash_before = sha256_path(SCRIPT_PATH)
    hashes_before = input_hashes(core)
    controls = self_test(core)
    subject = prepare_subject(core)
    refutation = source_refutation_control(core, subject)
    if args.preflight_only:
        return {
            "schema": SCHEMA,
            "result": "PREFLIGHT_ONLY",
            "claim_boundary": "Input/control/resource preflight only; no Schur decision ran.",
            "controls": controls,
            "denominator_controls": subject["denominator_controls"],
            "source_refutation_control": refutation,
            "resource_preflight": resource_preflight(args.block_width),
            "bindings": {"input_hashes": hashes_before, "script_sha256": script_hash_before},
        }

    basis_rows = subject["basis_rows"]
    base_columns = subject["base_columns"]
    registered_new = subject["registered_new"]
    missing_residual = subject["missing_residual"]
    missing_selected = subject["missing_selected"]
    old_batch = subject["old_batch"]
    block = subject["block"]
    old_subject = subject["old_subject"]
    square_started = time.perf_counter()
    square = base_basis_values(
        core,
        base_columns,
        basis_rows,
        block,
        old_subject,
        old_batch,
        missing_selected,
        missing_residual,
        registered_new,
    )
    if square.shape != (BASE_RANK, BASE_RANK):
        raise AssertionError("base square shape mismatch")
    square_sha256 = sha256_array(square)
    target_basis = np.zeros(BASE_RANK, dtype=np.int64)
    target_basis[basis_rows == TARGET_ROW] = TARGET_VALUE
    if np.count_nonzero(target_basis) != 1:
        raise AssertionError("target row is absent or duplicated in the base basis")
    new_base_values = heldout_values(base_columns, registered_new, missing_residual)
    square_seconds = time.perf_counter() - square_started

    deltas: dict[int, np.ndarray] = {}
    errors: dict[int, np.ndarray] = {}
    lambdas: dict[int, np.ndarray] = {}
    prime_records: dict[int, dict[str, Any]] = {}
    for prime, base_record in zip(PRIMES, subject["modular_records"], strict=True):
        prime_started = time.perf_counter()
        square_mod = nmod_matrix(core, square, prime)
        determinant = int(square_mod.det())
        if determinant == 0 or determinant != int(
            base_record.get("basis_square_determinant_mod_prime", -1)
        ):
            raise AssertionError(f"base square determinant mismatch at {prime}")
        saved_coefficients = np.asarray(
            base_record.get("coefficients_mod_prime", []), dtype=np.int64
        )
        if saved_coefficients.shape != (BASE_RANK,) or np.any(
            np.remainder(
                np.remainder(square, prime) @ saved_coefficients
                - np.remainder(target_basis, prime),
                prime,
            )
        ):
            raise AssertionError(f"saved base coefficients fail the base square at {prime}")
        lambda_mod = square_mod.transpose().solve(
            nmod_matrix(core, new_base_values.T, prime)
        ).transpose()
        lambda_values = core.matrix_to_numpy(lambda_mod)
        if np.any(
            np.remainder(
                core.matrix_to_numpy(lambda_mod * square_mod) - new_base_values,
                prime,
            )
        ):
            raise AssertionError(f"held-out row interpolation failed at {prime}")
        error = np.remainder(
            -core.matrix_to_numpy(
                lambda_mod * nmod_matrix(core, target_basis.reshape(-1, 1), prime)
            ).reshape(-1),
            prime,
        )
        source_residual = np.remainder(
            np.remainder(new_base_values, prime) @ saved_coefficients, prime
        )
        if np.any(np.remainder(error + source_residual, prime)):
            raise AssertionError(f"source-residual/Schur-error bridge failed at {prime}")
        delta = project_delta(
            core,
            prime,
            lambda_mod,
            basis_rows,
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            registered_new,
            args.block_width,
        )
        if np.any(delta[:, base_columns]):
            raise AssertionError(f"base support columns have nonzero Schur delta at {prime}")
        rank_record = rank_and_pivots(core, delta, error, prime)
        registered_rank = int(rank_record["registered_pivot_column_count"])
        registered_augmented = int(
            nmod_matrix(
                core,
                np.column_stack((delta[:, :REGISTERED_COLUMNS], error)),
                prime,
            ).rank()
        )
        rank_record.update(
            {
                "base_square_determinant_mod_prime": determinant,
                "registered_only_rank_D": registered_rank,
                "registered_only_augmented_rank": registered_augmented,
                "registered_only_target_in_span": registered_augmented == registered_rank,
                "all_tree_and_base_rank_gain_over_registered_only": int(
                    rank_record["rank_D"]
                )
                - registered_rank,
                # The decisive full-prefix ranks are already computed above.
                # Re-running eight large RREFs merely to draw an intermediate
                # curve would roughly double the critical-path work.
                "prefix_records": [
                    {
                        "heldout_prefix": NEW_ROWS,
                        "absolute_source_prefix": AVAILABLE_ROWS,
                        "rank_D": int(rank_record["rank_D"]),
                        "augmented_rank": int(rank_record["rank_D_with_target_residual"]),
                        "target_residual_in_span": bool(
                            rank_record["target_residual_in_column_span_D"]
                        ),
                    }
                ],
                "delta_int64_sha256": sha256_array(delta),
                "target_residual_int64_sha256": sha256_array(error),
                "source_candidate_nonzero_heldout_rows": int(np.count_nonzero(source_residual)),
                "prime_seconds": round(time.perf_counter() - prime_started, 6),
            }
        )
        deltas[prime] = delta
        errors[prime] = error
        lambdas[prime] = lambda_values
        prime_records[prime] = rank_record
        print(
            f"G0046_RESULT prime={prime} rank={rank_record['rank_D']} "
            f"augmented={rank_record['rank_D_with_target_residual']} "
            f"registered_rank={registered_rank}",
            flush=True,
        )

    inside = {
        prime: bool(prime_records[prime]["target_residual_in_column_span_D"])
        for prime in PRIMES
    }
    ranks = {prime: int(prime_records[prime]["rank_D"]) for prime in PRIMES}
    minor = common_minor(core, deltas, prime_records) if all(inside.values()) else None
    relation: dict[str, Any] | None = None
    separators: list[dict[str, Any]] = []
    if all(inside.values()) and len(set(ranks.values())) == 1 and ranks[PRIMES[0]] == 0:
        relation = subject["relation"]
        result_code = "TWO_PRIME_HELDOUT768_TARGET_REMAINS_IN_BASE_SPAN"
    elif all(inside.values()) and minor is not None:
        relation = build_relations(
            core,
            minor,
            deltas,
            errors,
            square,
            target_basis,
            basis_rows,
            base_columns,
            subject["support"],
            subject["registered_pairs"],
            subject["missing_pairs"],
            subject["missing_class_indices"],
            block,
            old_subject,
            old_batch,
            missing_selected,
            missing_residual,
            registered_new,
            args.block_width,
        )
        result_code = "TWO_PRIME_HELDOUT768_TARGET_REMAINS_IN_REGISTERED_ALL_TREE_5E_5L_SPAN"
    elif not all(inside.values()):
        for prime in PRIMES:
            if not inside[prime]:
                separators.append(
                    separating_dual(
                        core,
                        deltas[prime],
                        errors[prime],
                        lambdas[prime],
                        target_basis,
                        basis_rows,
                        prime,
                    )
                )
        result_code = "FINITE_FIELD_HELDOUT768_TARGET_OUTSIDE_REGISTERED_ALL_TREE_5E_5L_SPAN"
    elif len(set(ranks.values())) != 1:
        result_code = "TWO_PRIME_HELDOUT768_RANK_DISAGREEMENT"
    else:
        result_code = "TWO_PRIME_HELDOUT768_MEMBERSHIP_WITHOUT_COMMON_EXTENSION_MINOR"

    hashes_after = input_hashes(core)
    script_hash_after = sha256_path(SCRIPT_PATH)
    if hashes_after != hashes_before:
        raise RuntimeError("a bound input changed during the G-0046 computation")
    if script_hash_after != script_hash_before:
        raise RuntimeError("the G-0046 script changed during its live run")
    report = {
        "schema": SCHEMA,
        "result": result_code,
        "object_level_question": (
            "After the valid G-0033 rank-6,883 prefix-256 basis, do held-out rows "
            "256:1024 remain solvable using all 22,265 registered-plus-all-tree-plus-"
            "5E/5L columns?"
        ),
        "claim_boundary": (
            "All ranks, relations, and separators are over two finite fields on "
            "7,659+768 rows and 22,265 columns. This is not rational membership, "
            "global functional equality, pair-family completeness, or unrestricted MAX11."
        ),
        "dimensions": {
            "base_rank": BASE_RANK,
            "base_rows": BASE_ROWS,
            "absorbed_source_rows": ABSORBED_ROWS,
            "heldout_source_row_start": NEW_ROW_START,
            "heldout_rows": NEW_ROWS,
            "total_rows": BASE_ROWS + NEW_ROWS,
            "registered_columns": REGISTERED_COLUMNS,
            "missing_all_tree_columns": MISSING_COLUMNS,
            "registered_plus_all_tree_graph_columns": GRAPH_COLUMNS,
            "zero_signed_graph_base_columns": 2,
            "five_E_column": FIVE_E_COLUMN,
            "five_L_column": FIVE_L_COLUMN,
            "combined_columns": COMBINED_COLUMNS,
        },
        "source_complete_residual_stream_sha256": subject["source_stream_sha256"],
        "source_refutation_control": refutation,
        "base_square": {
            "shape": [BASE_RANK, BASE_RANK],
            "int64_c_sha256": square_sha256,
            "construction_seconds": round(square_seconds, 6),
        },
        "prime_records": [prime_records[prime] for prime in PRIMES],
        "common_schur_minor": minor,
        "enlarged_modular_relations": relation,
        "separating_duals": separators,
        "controls": {
            "algebraic_self_test": controls,
            "base_support_binding": subject["support_controls"],
            "denominator_completeness": subject["denominator_controls"],
            "base_candidate_refuted_on_heldout_rows": True,
            "source_candidate_residual_equals_negative_schur_target": True,
            "base_support_columns_project_to_zero": True,
            "registered_pair_census": subject["pair_census"],
        },
        "row_bindings": subject["row_bindings"],
        "resource_preflight": resource_preflight(args.block_width),
        "bindings": {
            "input_hashes_before": hashes_before,
            "input_hashes_after": hashes_after,
            "inputs_stable": True,
            "script_sha256_before": script_hash_before,
            "script_sha256_after": script_hash_after,
            "script_stable": True,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": __import__("flint").__version__,
            "block_width": args.block_width,
            "available_gib_before": available_before,
            "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }
    write_gzip(args.output, report)
    print(
        f"G0046_PASS result={result_code} report_sha256={sha256_path(args.output)}",
        flush=True,
    )
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--block-width", type=int, default=256)
    parser.add_argument("--minimum-available-gib", type=float, default=12.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--preflight-only", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if not (32 <= args.block_width <= 512):
        parser.error("--block-width must be in [32,512]")
    if args.minimum_available_gib < 4:
        parser.error("--minimum-available-gib must be at least 4")
    if args.output.resolve().parent != HERE:
        parser.error("output must be a direct G-0046 child")
    return args


def main() -> int:
    args = parse_args()
    core = load_module("g0046_g0033_core_selftest", CORE_SCRIPT)
    if args.self_test:
        print(json.dumps(self_test(core), sort_keys=True))
        return 0
    report = run(args)
    if args.preflight_only:
        print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
