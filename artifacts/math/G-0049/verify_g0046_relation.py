#!/usr/bin/env python3
"""Clean-room verification of a favorable G-0046 modular relation.

This verifier deliberately does not import G-0046 or its G-0033 semantic
helpers.  It has two independent gates:

1. replay the serialized relation on all 8,427 frozen coordinates from the
   separately persisted baseline/cross/missing matrices; and
2. reconstruct every support atom from its pair descriptor with a fresh
   subset dynamic program, aggregate the complete primitive hinge normal
   form, and compare it with the exact MAX11 target normal form.

Both gates are finite-field statements.  Passing them is necessary before a
rational lift is attempted; it is not itself an exact-Q or unrestricted
two-hidden-layer theorem.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
import gzip
import hashlib
import json
from math import factorial, gcd
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any, Iterable, Sequence

import numpy as np


N = 11
PRIMES = (1_000_003, 1_000_033)
CRT_MODULUS = PRIMES[0] * PRIMES[1]
SELECTED_HINGES = 7_135
LINEAR_ROWS = N
SELECTED_ROWS = SELECTED_HINGES + LINEAR_ROWS
WITNESS_ROWS = 1
OLD_BATCH_ROWS = 256
NEW_BATCH_ROWS = 1_024
TOTAL_ROWS = SELECTED_ROWS + WITNESS_ROWS + OLD_BATCH_ROWS + NEW_BATCH_ROWS
TARGET_ROW = SELECTED_HINGES + N - 1
TARGET_VALUE = factorial(N)

BASE_RANK = 6_883
REGISTERED_COLUMNS = 13_419
BASELINE_COLUMNS = 9_804
CROSS_COLUMNS = REGISTERED_COLUMNS - BASELINE_COLUMNS
MISSING_COLUMNS = 8_844
GRAPH_COLUMNS = REGISTERED_COLUMNS + MISSING_COLUMNS
FIVE_E_COLUMN = GRAPH_COLUMNS
FIVE_L_COLUMN = GRAPH_COLUMNS + 1
COMBINED_COLUMNS = GRAPH_COLUMNS + 2

SCHEMA = "max11-g0049-cleanroom-full-relation-verification-v1"
G0046_SCHEMA = "max11-g0046-heldout768-registered-all-tree-bases-schur-v1"
FAVORABLE_RESULT = (
    "TWO_PRIME_HELDOUT768_TARGET_REMAINS_IN_REGISTERED_ALL_TREE_5E_5L_SPAN"
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G6 = ROOT / "artifacts/math/G-0006"
G8 = ROOT / "artifacts/math/G-0008"
G9 = ROOT / "artifacts/math/G-0009"
G14 = ROOT / "artifacts/math/G-0014"
G19 = ROOT / "artifacts/math/G-0019"
G23 = ROOT / "artifacts/math/G-0023"
G25 = ROOT / "artifacts/math/G-0025"
G33 = ROOT / "artifacts/math/G-0033"
G40 = ROOT / "artifacts/math/G-0040"
G44 = ROOT / "artifacts/math/G-0044"
G46 = ROOT / "artifacts/math/G-0046"

G0046_REPORT = G46 / "heldout768_all_tree_schur_v1.json.gz"
G0046_SCRIPT = G46 / "full_heldout_schur.py"
DEFAULT_OUTPUT = HERE / "g0046_relation_cleanroom_verification_v1.json.gz"
SCRIPT_PATH = Path(__file__).resolve()

CERTIFICATE = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
BASELINE_CLASSES = G6 / "isomorphism_classes_v2.json"
CROSS_CLASSES = G9 / "cross_component_classes.json"
ALL_TREE_UNIVERSE = G23 / "all_tree_universe_v1.json"

SELECTION = G8 / "cut_selection_01_02_03_04.json"
BASELINE_MATRIX = G8 / "cut_matrix_01_02_03_04.npz"
CROSS_MATRIX = G19 / "cross_full_cut_matrix_int64.npy"
MISSING_SELECTED_MATRIX = G23 / "missing_all_tree_cut_matrix_int64.npy"
REGISTERED_WITNESS_ROW = G25 / "registered_union_provisional_witness_row_v1.npy"
REGISTERED_OLD_BATCH = G25 / "registered_union_residual_batch_rows_v1.npy"
REGISTERED_NEW_BATCH = G25 / "registered_union_rank6677_residual_rows_1024_v1.npy"
MISSING_RESIDUAL_ROWS = G33 / "missing_tree_residual_rows_v1.npy"

OLD_SCHUR_REPORT = G25 / "registered_union_residual_batch_schur_v1.json.gz"
NEW_BATCH_REPORT = G25 / "registered_union_rank6677_residual_rows_1024_v1.json.gz"
MISSING_RESIDUAL_REPORT = G33 / "missing_tree_residual_rows_v1.json"
WITNESS_REPORT = G25 / "registered_union_provisional_witness_row_v1.json"
BASELINE_MATRIX_REPORT = G8 / "cut_selection_01_02_03_04.json"
CROSS_MATRIX_REPORT = G19 / "cross_full_cut_matrix_report_v1.json"
MISSING_SELECTED_REPORT = G23 / "missing_all_tree_cut_matrix_report_v1.json"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"not a contained regular input: {path}")
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


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise FileNotFoundError(f"not a contained regular input: {path}")
    if path.suffix == ".gz":
        with gzip.open(path, "rt", encoding="utf-8") as source:
            raw = source.read()
    else:
        raw = path.read_text(encoding="utf-8")
    value = json.loads(raw, object_pairs_hook=unique_object)
    if not isinstance(value, dict):
        raise ValueError(f"top-level object required: {path}")
    return value


def write_gzip(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial exists: {partial}")
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


def crt_pair(first: int, second: int) -> int:
    p1, p2 = PRIMES
    return (
        int(first) + p1 * (((int(second) - int(first)) * pow(p1, -1, p2)) % p2)
    ) % CRT_MODULUS


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[int(u), int(v)] for u, v in side] for side in pair]


def pair_list_sha256(pairs: Sequence[Pair]) -> str:
    return hashlib.sha256(canonical_bytes([serialize_pair(pair) for pair in pairs])).hexdigest()


def parse_pair(raw: object, *, one_based: bool = True, loopless: bool = True) -> Pair:
    if not isinstance(raw, list) or len(raw) != 2:
        raise ValueError("pair must contain exactly two branches")
    sides: list[Side] = []
    lower, upper = (1, N) if one_based else (0, N - 1)
    for raw_side in raw:
        if not isinstance(raw_side, list) or len(raw_side) != 5:
            raise ValueError("support branch must contain exactly five edges")
        side: list[Edge] = []
        for raw_edge in raw_side:
            if (
                not isinstance(raw_edge, list)
                or len(raw_edge) != 2
                or any(type(value) is not int for value in raw_edge)
            ):
                raise ValueError("malformed support edge")
            u, v = map(int, raw_edge)
            if not (lower <= u <= v <= upper) or (loopless and u == v):
                raise ValueError(f"noncanonical support edge {(u, v)}")
            side.append((u, v))
        sides.append(tuple(side))
    return sides[0], sides[1]


def zero_based(pair: Pair) -> Pair:
    return tuple(tuple((u - 1, v - 1) for u, v in side) for side in pair)  # type: ignore[return-value]


def one_based(pair: Pair) -> Pair:
    return tuple(tuple((u + 1, v + 1) for u, v in side) for side in pair)  # type: ignore[return-value]


def build_raw_lift_families() -> tuple[list[Pair], list[Pair], dict[str, Any]]:
    """Reconstruct both registered raw families without importing their producers."""

    document = load_json(CERTIFICATE)
    terms = document.get("terms")
    if not isinstance(terms, list):
        raise ValueError("MAX10 certificate has no term list")
    bases: list[tuple[int, Side, Side, tuple[tuple[int, ...], ...]]] = []
    same_pairs: list[Pair] = []
    same_metadata: list[tuple[int, ...]] = []
    for term_index, term in enumerate(terms):
        if not isinstance(term, dict):
            raise ValueError("malformed MAX10 certificate term")
        raw_pair = term.get("pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise ValueError("malformed MAX10 pair")
        left = tuple(tuple(sorted(map(int, edge))) for edge in raw_pair[0])
        right = tuple(tuple(sorted(map(int, edge))) for edge in raw_pair[1])
        all_edges = left + right
        if any(a == b for a, b in all_edges) or len(set(all_edges)) != 8:
            continue
        vertices = {vertex for edge in all_edges for vertex in edge}
        if len(vertices) != 10:
            continue
        parent = {vertex: vertex for vertex in vertices}

        def find(vertex: int) -> int:
            while parent[vertex] != vertex:
                parent[vertex] = parent[parent[vertex]]
                vertex = parent[vertex]
            return vertex

        for a, b in set(all_edges):
            root_a, root_b = find(a), find(b)
            if root_a != root_b:
                parent[root_b] = root_a
        components_by_root: dict[int, list[int]] = {}
        for vertex in vertices:
            components_by_root.setdefault(find(vertex), []).append(vertex)
        if len(components_by_root) != 2:
            continue
        components = tuple(tuple(component) for component in components_by_root.values())
        base_index = len(bases)
        bases.append((term_index, left, right, components))
        for component_index, component in enumerate(components):
            for left_endpoint in component:
                for right_endpoint in component:
                    same_pairs.append(
                        (left + ((left_endpoint, N),), right + ((right_endpoint, N),))
                    )
                    same_metadata.append(
                        (
                            base_index,
                            term_index,
                            component_index,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
    cross_pairs: list[Pair] = []
    cross_metadata: list[tuple[int, ...]] = []
    for base_index, (term_index, left, right, components) in enumerate(bases):
        for left_component, right_component in ((0, 1), (1, 0)):
            for left_endpoint in components[left_component]:
                for right_endpoint in components[right_component]:
                    cross_pairs.append(
                        (left + ((left_endpoint, N),), right + ((right_endpoint, N),))
                    )
                    cross_metadata.append(
                        (
                            base_index,
                            term_index,
                            left_component,
                            right_component,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
    if len(bases) != 252 or len(same_pairs) != 16_000 or len(cross_pairs) != 9_200:
        raise AssertionError("raw registered-family census mismatch")

    same_classes = load_json(BASELINE_CLASSES)
    cross_classes = load_json(CROSS_CLASSES)
    same_metadata_sha = hashlib.sha256(
        json.dumps(same_metadata, separators=(",", ":")).encode("ascii")
    ).hexdigest()
    cross_metadata_sha = hashlib.sha256(canonical_bytes(cross_metadata)).hexdigest()
    for label, classes, pairs, metadata_sha, expected_schema, expected_classes in (
        (
            "same",
            same_classes,
            same_pairs,
            same_metadata_sha,
            "max11-minimal-lifts-isomorphism-v2",
            BASELINE_COLUMNS,
        ),
        (
            "cross",
            cross_classes,
            cross_pairs,
            cross_metadata_sha,
            "max11-cross-component-lifts-isomorphism-v1",
            CROSS_COLUMNS,
        ),
    ):
        representatives = classes.get("representative_raw_indices")
        if (
            classes.get("schema") != expected_schema
            or classes.get("n") != N
            or classes.get("raw_candidate_count") != len(pairs)
            or classes.get("class_count") != expected_classes
            or classes.get("candidate_metadata_sha256") != metadata_sha
            or classes.get("raw_pair_list_sha256") != pair_list_sha256(pairs)
            or classes.get("source_certificate_sha256") != sha256_path(CERTIFICATE)
            or not isinstance(representatives, list)
            or len(representatives) != expected_classes
            or len(set(map(int, representatives))) != expected_classes
            or any(not (0 <= int(index) < len(pairs)) for index in representatives)
        ):
            raise ValueError(f"{label} quotient/raw-family binding mismatch")
    same_reps = [same_pairs[int(index)] for index in same_classes["representative_raw_indices"]]
    cross_reps = [cross_pairs[int(index)] for index in cross_classes["representative_raw_indices"]]
    return same_reps, cross_reps, {
        "MAX10_certificate_sha256": sha256_path(CERTIFICATE),
        "same_raw_count": len(same_pairs),
        "same_representative_count": len(same_reps),
        "same_raw_pair_list_sha256": pair_list_sha256(same_pairs),
        "cross_raw_count": len(cross_pairs),
        "cross_representative_count": len(cross_reps),
        "cross_raw_pair_list_sha256": pair_list_sha256(cross_pairs),
    }


def load_missing_pairs() -> tuple[list[Pair], list[int], dict[str, Any]]:
    universe = load_json(ALL_TREE_UNIVERSE)
    n11 = universe.get("n11_subject")
    overlap = universe.get("g0019_overlap")
    if (
        universe.get("schema") != "max11-g0023-all-balanced-coloured-trees-v1"
        or universe.get("result") != "PASS"
        or not isinstance(n11, dict)
        or not isinstance(overlap, dict)
    ):
        raise ValueError("all-tree universe contract mismatch")
    raw_representatives = n11.get("representatives")
    missing_indices = overlap.get("missing_all_class_indices")
    if (
        not isinstance(raw_representatives, list)
        or len(raw_representatives) != 12_459
        or not isinstance(missing_indices, list)
        or len(missing_indices) != MISSING_COLUMNS
    ):
        raise ValueError("all-tree representative/missing census mismatch")
    zero_pairs = [parse_pair(value, one_based=False) for value in raw_representatives]
    if pair_list_sha256(zero_pairs) != n11.get("representative_pairs_sha256"):
        raise ValueError("all-tree representative pair hash mismatch")
    indices = list(map(int, missing_indices))
    if (
        len(set(indices)) != MISSING_COLUMNS
        or any(not (0 <= index < len(zero_pairs)) for index in indices)
        or hashlib.sha256(canonical_bytes(indices)).hexdigest()
        != overlap.get("missing_all_class_indices_sha256")
    ):
        raise ValueError("missing all-tree index binding mismatch")
    pairs = [one_based(zero_pairs[index]) for index in indices]
    return pairs, indices, {
        "universe_sha256": sha256_path(ALL_TREE_UNIVERSE),
        "all_tree_representative_count": len(zero_pairs),
        "missing_representative_count": len(pairs),
        "missing_indices_sha256": overlap["missing_all_class_indices_sha256"],
    }


def five_e_linear() -> tuple[int, ...]:
    return tuple(5 * 2 * rank * factorial(N - 2) for rank in range(N))


def five_l_linear() -> tuple[int, ...]:
    return tuple(5 * factorial(N - 1) for _ in range(N))


@dataclass(frozen=True)
class SupportSubject:
    pairs: tuple[Pair | None, ...]
    columns: tuple[int, ...]
    support: tuple[dict[str, Any], ...]
    controls: dict[str, Any]


def validate_support(relation: dict[str, Any]) -> SupportSubject:
    support = relation.get("support")
    raw_columns = relation.get("basis_columns_combined_union")
    expected_sha = relation.get("support_descriptor_sha256")
    if not isinstance(support, list) or not isinstance(raw_columns, list):
        raise ValueError("relation lacks support/column arrays")
    if len(support) != len(raw_columns):
        raise ValueError("support/column length mismatch")
    observed_sha = hashlib.sha256(canonical_bytes(support)).hexdigest()
    if expected_sha != observed_sha:
        raise ValueError("support descriptor hash mismatch")
    columns = tuple(map(int, raw_columns))
    if (
        len(set(columns)) != len(columns)
        or any(not (0 <= column < COMBINED_COLUMNS) for column in columns)
    ):
        raise ValueError("relation columns are duplicate or out of range")

    same, cross, registered_controls = build_raw_lift_families()
    missing, missing_indices, missing_controls = load_missing_pairs()
    pairs: list[Pair | None] = []
    family_counts: Counter[str] = Counter()
    for position, (item, column) in enumerate(zip(support, columns, strict=True)):
        if not isinstance(item, dict) or int(item.get("support_position", -1)) != position:
            raise ValueError(f"malformed support position {position}")
        explicit = [
            int(item[key])
            for key in ("combined_union_column", "union_index")
            if key in item
        ]
        if explicit and any(value != column for value in explicit):
            raise ValueError(f"explicit support column mismatch at {position}")
        if column < BASELINE_COLUMNS:
            expected_pair = same[column]
            valid_metadata = (
                item.get("family") == "same"
                and int(item.get("class_index", -1)) == column
            )
        elif column < REGISTERED_COLUMNS:
            local = column - BASELINE_COLUMNS
            expected_pair = cross[local]
            valid_metadata = (
                item.get("family") == "cross"
                and int(item.get("class_index", -1)) == local
            )
        elif column < GRAPH_COLUMNS:
            local = column - REGISTERED_COLUMNS
            expected_pair = missing[local]
            valid_metadata = (
                item.get("family") == "missing_all_tree"
                and int(item.get("missing_local_index", -1)) == local
                and int(item.get("all_tree_class_index", -1)) == missing_indices[local]
            )
        else:
            expected_pair = None
            label = "five_common_nonloops" if column == FIVE_E_COLUMN else "five_common_loops"
            linear = five_e_linear() if column == FIVE_E_COLUMN else five_l_linear()
            valid_metadata = (
                item.get("family") == "zero_signed_graph_base"
                and item.get("base") == label
                and item.get("linear_coordinates") == list(linear)
                and item.get("hinge_coordinates_all_zero") is True
                and int(item.get("combined_union_column", -1)) == column
            )
        if not valid_metadata:
            raise ValueError(f"support family/class metadata mismatch at {position}")
        if expected_pair is not None:
            observed_pair = parse_pair(item.get("pair"))
            if observed_pair != expected_pair:
                raise ValueError(f"support pair/source mismatch at {position}")
            pairs.append(observed_pair)
        else:
            pairs.append(None)
        family_counts[str(item.get("family"))] += 1
    return SupportSubject(
        pairs=tuple(pairs),
        columns=columns,
        support=tuple(support),
        controls={
            "support_descriptor_sha256": observed_sha,
            "support_count": len(support),
            "unique_combined_columns": len(columns),
            "family_counts": dict(sorted(family_counts.items())),
            "registered_raw_family_reconstruction": registered_controls,
            "missing_all_tree_reconstruction": missing_controls,
            "every_graph_pair_matches_reconstructed_source": True,
            "explicit_5E_5L_descriptors_match_exact_vectors": True,
        },
    )


def validate_direction(raw: object) -> Direction:
    if not isinstance(raw, list) or len(raw) != N or any(type(x) is not int for x in raw):
        raise ValueError("malformed hinge direction")
    direction = tuple(map(int, raw))
    if (
        sum(direction) != 0
        or not any(direction)
        or next(value for value in direction if value) <= 0
        or gcd(*(abs(value) for value in direction)) != 1
    ):
        raise ValueError(f"noncanonical hinge direction: {direction}")
    return direction


def validate_rows(g0046: dict[str, Any]) -> tuple[list[Direction], dict[str, Any]]:
    selection = load_json(SELECTION)
    old = load_json(OLD_SCHUR_REPORT)
    new = load_json(NEW_BATCH_REPORT)
    missing = load_json(MISSING_RESIDUAL_REPORT)
    selected_raw = selection.get("directions")
    old_raw = old.get("batch", {}).get("directions") if isinstance(old.get("batch"), dict) else None
    new_raw = new.get("batch", {}).get("directions") if isinstance(new.get("batch"), dict) else None
    missing_raw = missing.get("directions")
    if (
        selection.get("schema") != "max11-exact-hinge-cut-selection-v1"
        or selection.get("n") != N
        or selection.get("selected_count") != SELECTED_HINGES
        or not isinstance(selected_raw, list)
        or len(selected_raw) != SELECTED_HINGES
        or old.get("schema") != "max11-g0025-registered-union-residual-batch-schur-v1"
        or not isinstance(old_raw, list)
        or len(old_raw) != OLD_BATCH_ROWS
        or new.get("schema") != "max11-g0025-registered-union-rank6677-residual-rows-1024-v1"
        or not isinstance(new_raw, list)
        or len(new_raw) != NEW_BATCH_ROWS
        or missing.get("schema") != "max11-g0033-missing-tree-residual-rows-v1"
        or not isinstance(missing_raw, list)
        or len(missing_raw) != WITNESS_ROWS + OLD_BATCH_ROWS + NEW_BATCH_ROWS
    ):
        raise ValueError("frozen row-source schema/census mismatch")
    selected = [validate_direction(value) for value in selected_raw]
    old_batch = [validate_direction(value) for value in old_raw]
    new_batch = [validate_direction(value) for value in new_raw]
    witness = (0, 0, 0, 0, 0, 0, 0, 1, -5, 0, 4)
    expected_missing = [witness] + old_batch + new_batch
    observed_missing = [validate_direction(value) for value in missing_raw]
    if observed_missing != expected_missing:
        raise ValueError("missing-row direction order disagrees with independent sources")
    all_hinges = selected + observed_missing
    if len(set(all_hinges)) != len(all_hinges):
        raise ValueError("frozen hinge rows are not disjoint")
    row_descriptors: list[dict[str, Any]] = [
        {"kind": "hinge", "direction": list(direction)} for direction in selected
    ]
    row_descriptors.extend({"kind": "linear", "rank": rank} for rank in range(N))
    row_descriptors.extend(
        {"kind": "hinge", "direction": list(direction)} for direction in observed_missing
    )
    if len(row_descriptors) != TOTAL_ROWS:
        raise AssertionError("complete row descriptor census mismatch")
    row_hash = hashlib.sha256(canonical_bytes(row_descriptors)).hexdigest()
    # G-0046 must bind the exact producer state that owns these rows.
    row_bindings = g0046.get("row_bindings")
    if not isinstance(row_bindings, dict):
        raise ValueError("G-0046 row bindings absent")
    expected_file_hashes = {
        "old_registered_batch_matrix_sha256": sha256_path(REGISTERED_OLD_BATCH),
        "registered_new_matrix_sha256": sha256_path(REGISTERED_NEW_BATCH),
        "missing_selected_matrix_sha256": sha256_path(MISSING_SELECTED_MATRIX),
        "missing_residual_matrix_sha256": sha256_path(MISSING_RESIDUAL_ROWS),
    }
    if any(row_bindings.get(key) != value for key, value in expected_file_hashes.items()):
        raise ValueError("G-0046 row binding does not match frozen row files")
    return all_hinges, {
        "total_rows": TOTAL_ROWS,
        "selected_hinge_rows": SELECTED_HINGES,
        "linear_rows": LINEAR_ROWS,
        "witness_rows": WITNESS_ROWS,
        "old_batch_rows": OLD_BATCH_ROWS,
        "new_batch_rows": NEW_BATCH_ROWS,
        "all_hinge_directions_unique": True,
        "missing_direction_order_matches_witness_old_new_sources": True,
        "row_descriptor_sha256": row_hash,
        "bound_matrix_file_sha256": expected_file_hashes,
    }


def g0046_declared_input_paths() -> dict[str, Path]:
    """Independent spelling of the producer's declared direct input surface."""

    return {
        "core_current_schur_report": G25 / "registered_union_residual_batch_schur_v1.json.gz",
        "core_current_complete_replay": G25 / "registered_union_rank6677_complete_modular_replay_v1.json.gz",
        "core_current_complete_replay_script": G25 / "complete_rank6677_modular_replay.py",
        "core_legacy_registered_relation": G25 / "registered_union_extended_modular_relation_v1.json.gz",
        "core_registered_new_rows": REGISTERED_NEW_BATCH,
        "core_registered_new_report": NEW_BATCH_REPORT,
        "core_registered_new_generator": G25 / "registered_union_rank6677_residual_rows_1024.py",
        "core_old_registered_batch_rows": REGISTERED_OLD_BATCH,
        "core_missing_selected_rows": MISSING_SELECTED_MATRIX,
        "core_missing_selected_report": MISSING_SELECTED_REPORT,
        "core_missing_residual_rows": MISSING_RESIDUAL_ROWS,
        "core_missing_residual_report": MISSING_RESIDUAL_REPORT,
        "core_missing_residual_generator": G33 / "missing_tree_residual_rows.py",
        "core_all_tree_universe": ALL_TREE_UNIVERSE,
        "core_all_tree_known_answer": G23 / "n9_known_answer_v1.json",
        "core_all_tree_selection": SELECTION,
        "core_all_tree_semantic_generator": G14 / "semantic_matrix_audit.py",
        "core_all_tree_generator": G23 / "all_tree_exact.py",
        "core_old_relation_loader": G25 / "extended_modular_relation.py",
        "core_old_block_schur": G25 / "batched_block_schur.py",
        "core_registered_pair_loader": G25 / "provisional_witness_row.py",
        "core_full_semantics": G6 / "exact_lift_search.py",
        "g0033_base_report": G33 / "all_tree_block_schur_prefix256_v1.json.gz",
        "g0033_core_script": G33 / "all_tree_block_schur.py",
        "g0040_loop_semantics_source": G40 / "src/lib.rs",
        "g0040_pricing_report": G40 / "loop_inclusive_g0028_first_pricing_v1.json",
        "g0044_span_transfer_report": G44 / "wang_basu_transfer_report_v1.json",
    }


def extra_verifier_input_paths() -> dict[str, Path]:
    return {
        "certificate": CERTIFICATE,
        "baseline_classes": BASELINE_CLASSES,
        "cross_classes": CROSS_CLASSES,
        "all_tree_universe": ALL_TREE_UNIVERSE,
        "selection": SELECTION,
        "baseline_matrix": BASELINE_MATRIX,
        "cross_matrix": CROSS_MATRIX,
        "missing_selected_matrix": MISSING_SELECTED_MATRIX,
        "registered_witness_row": REGISTERED_WITNESS_ROW,
        "registered_old_batch": REGISTERED_OLD_BATCH,
        "registered_new_batch": REGISTERED_NEW_BATCH,
        "missing_residual_rows": MISSING_RESIDUAL_ROWS,
        "old_schur_report": OLD_SCHUR_REPORT,
        "new_batch_report": NEW_BATCH_REPORT,
        "missing_residual_report": MISSING_RESIDUAL_REPORT,
        "witness_report": WITNESS_REPORT,
        "cross_matrix_report": CROSS_MATRIX_REPORT,
        "missing_selected_report": MISSING_SELECTED_REPORT,
    }


def validate_g0046_bindings(report: dict[str, Any], report_path: Path) -> dict[str, Any]:
    bindings = report.get("bindings")
    if not isinstance(bindings, dict):
        raise ValueError("G-0046 bindings absent")
    before = bindings.get("input_hashes_before")
    after = bindings.get("input_hashes_after")
    if (
        not isinstance(before, dict)
        or before != after
        or bindings.get("inputs_stable") is not True
        or bindings.get("script_stable") is not True
        or bindings.get("script_sha256_before") != bindings.get("script_sha256_after")
    ):
        raise ValueError("G-0046 producer did not freeze stable inputs/script")
    paths = g0046_declared_input_paths()
    actual = {label: sha256_path(path) for label, path in paths.items()}
    if set(before) != set(actual) or any(str(before[key]) != value for key, value in actual.items()):
        raise ValueError("G-0046 declared input hashes do not match clean-room observations")
    script_sha = sha256_path(G0046_SCRIPT)
    if bindings.get("script_sha256_before") != script_sha:
        raise ValueError("G-0046 script hash does not match frozen producer binding")
    return {
        "g0046_report_sha256": sha256_path(report_path),
        "g0046_script_sha256": script_sha,
        "producer_direct_input_count": len(actual),
        "producer_direct_input_hashes": actual,
        "producer_inputs_and_script_stable": True,
    }


@dataclass(frozen=True)
class RelationSubject:
    report: dict[str, Any]
    relation: dict[str, Any]
    support: SupportSubject
    coefficients: dict[int, np.ndarray]
    controls: dict[str, Any]


def validate_relation(report: dict[str, Any]) -> RelationSubject:
    dimensions = report.get("dimensions")
    records = report.get("prime_records")
    relation = report.get("enlarged_modular_relations")
    if (
        report.get("schema") != G0046_SCHEMA
        or report.get("result") != FAVORABLE_RESULT
        or not isinstance(dimensions, dict)
        or dimensions
        != {
            "base_rank": BASE_RANK,
            "base_rows": 7_659,
            "absorbed_source_rows": 256,
            "heldout_source_row_start": 256,
            "heldout_rows": 768,
            "total_rows": TOTAL_ROWS,
            "registered_columns": REGISTERED_COLUMNS,
            "missing_all_tree_columns": MISSING_COLUMNS,
            "registered_plus_all_tree_graph_columns": GRAPH_COLUMNS,
            "zero_signed_graph_base_columns": 2,
            "five_E_column": FIVE_E_COLUMN,
            "five_L_column": FIVE_L_COLUMN,
            "combined_columns": COMBINED_COLUMNS,
        }
        or not isinstance(records, list)
        or [int(item.get("prime", -1)) for item in records] != list(PRIMES)
        or any(item.get("target_residual_in_column_span_D") is not True for item in records)
        or len({int(item.get("rank_D", -1)) for item in records}) != 1
        or not isinstance(relation, dict)
    ):
        raise ValueError("G-0046 favorable two-prime report contract mismatch")
    schur_rank = int(records[0]["rank_D"])
    rank = int(relation.get("new_rank", -1))
    basis_rows = relation.get("basis_rows")
    modular_records = relation.get("modular_records")
    if (
        rank != BASE_RANK + schur_rank
        or not isinstance(basis_rows, list)
        or len(basis_rows) != rank
        or len(set(map(int, basis_rows))) != rank
        or any(not (0 <= int(row) < TOTAL_ROWS) for row in basis_rows)
        or not isinstance(modular_records, list)
        or [int(item.get("prime", -1)) for item in modular_records] != list(PRIMES)
        or any(item.get("complete_existing_and_new_row_replay") is not True for item in modular_records)
    ):
        raise ValueError("G-0046 enlarged relation census mismatch")
    support = validate_support(relation)
    if len(support.columns) != rank:
        raise ValueError("relation rank/support length mismatch")
    coefficients: dict[int, np.ndarray] = {}
    sparsity = []
    for record in modular_records:
        prime = int(record["prime"])
        raw = record.get("coefficients_mod_prime")
        if not isinstance(raw, list) or len(raw) != rank:
            raise ValueError(f"coefficient vector length mismatch at {prime}")
        vector = np.asarray([int(value) for value in raw], dtype=np.int64)
        if np.any(vector < 0) or np.any(vector >= prime):
            raise ValueError(f"coefficient outside canonical residue range at {prime}")
        nonzero = int(np.count_nonzero(vector))
        if (
            record.get("coefficient_vector_int64_sha256") != sha256_array(vector)
            or int(record.get("nonzero_coefficient_count", -1)) != nonzero
            or int(record.get("rank", -1)) != rank
        ):
            raise ValueError(f"coefficient hash/census mismatch at {prime}")
        coefficients[prime] = vector
        sparsity.append(
            {
                "prime": prime,
                "serialized_basis_support": rank,
                "nonzero_coefficients": nonzero,
                "zero_coefficients": rank - nonzero,
                "density": nonzero / rank,
                "sparse_relative_to_full_denominator": rank < COMBINED_COLUMNS,
            }
        )
    active_union = [
        position
        for position in range(rank)
        if any(int(coefficients[prime][position]) for prime in PRIMES)
    ]
    active_by_prime = {
        prime: [position for position in range(rank) if int(coefficients[prime][position])]
        for prime in PRIMES
    }
    missing_positions = [
        position
        for position, column in enumerate(support.columns)
        if REGISTERED_COLUMNS <= column < GRAPH_COLUMNS
    ]
    base_positions = [
        position for position, column in enumerate(support.columns) if column >= GRAPH_COLUMNS
    ]
    if (
        len(active_union) != 7_100
        or len(active_by_prime[PRIMES[0]]) != 7_099
        or len(active_by_prime[PRIMES[1]]) != 7_100
        or any(support.columns[position] >= REGISTERED_COLUMNS for position in active_union)
        or len(missing_positions) != 35
        or any(
            int(coefficients[prime][position])
            for prime in PRIMES
            for position in missing_positions + base_positions
        )
        or base_positions
    ):
        raise ValueError("G-0046 registered-only active-support contract mismatch")
    return RelationSubject(
        report=report,
        relation=relation,
        support=support,
        coefficients=coefficients,
        controls={
            "schur_rank": schur_rank,
            "relation_rank": rank,
            "both_prime_memberships_serialized": True,
            "coefficient_serialization": sparsity,
            "active_union_count": len(active_union),
            "active_counts_by_prime": {
                str(prime): len(active_by_prime[prime]) for prime in PRIMES
            },
            "active_union_all_registered": True,
            "serialized_missing_tree_positions": len(missing_positions),
            "all_serialized_missing_tree_coefficients_zero_at_both_primes": True,
            "serialized_5E_5L_positions": len(base_positions),
            "no_5E_5L_basis_pivoted": True,
            "support": support.controls,
        },
    )


def checked_npy(path: Path, shape: tuple[int, ...]) -> np.ndarray:
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    if array.shape != shape or array.dtype != np.int64:
        raise ValueError(f"matrix shape/dtype mismatch: {path} {array.shape} {array.dtype}")
    return array


def modular_matvec(matrix: np.ndarray, coefficients: np.ndarray, prime: int, block: int = 128) -> np.ndarray:
    if matrix.ndim != 2 or coefficients.shape != (matrix.shape[1],):
        raise ValueError("matvec dimension mismatch")
    output = np.zeros(matrix.shape[0], dtype=np.int64)
    int64_max = np.iinfo(np.int64).max
    for start in range(0, matrix.shape[1], block):
        stop = min(start + block, matrix.shape[1])
        coeff = coefficients[start:stop]
        if not np.any(coeff):
            continue
        values = np.asarray(matrix[:, start:stop], dtype=np.int64)
        bound = int(np.max(np.abs(values), initial=0)) * int(np.max(coeff, initial=0)) * len(coeff)
        if bound >= int64_max:
            raise OverflowError(f"unsafe int64 modular matvec bound {bound}")
        output = np.remainder(output + values @ coeff, prime)
    return output


def relation_universe_coefficients(subject: RelationSubject, prime: int) -> tuple[np.ndarray, np.ndarray]:
    graph = np.zeros(GRAPH_COLUMNS, dtype=np.int64)
    bases = np.zeros(2, dtype=np.int64)
    vector = subject.coefficients[prime]
    for position, column in enumerate(subject.support.columns):
        if column < GRAPH_COLUMNS:
            graph[column] = vector[position]
        else:
            bases[column - GRAPH_COLUMNS] = vector[position]
    return graph, bases


def validate_matrix_bindings() -> dict[str, Any]:
    witness_report = load_json(WITNESS_REPORT)
    cross_report = load_json(CROSS_MATRIX_REPORT)
    missing_report = load_json(MISSING_SELECTED_REPORT)
    new_report = load_json(NEW_BATCH_REPORT)
    residual_report = load_json(MISSING_RESIDUAL_REPORT)
    expected = {
        "baseline_matrix": sha256_path(BASELINE_MATRIX),
        "cross_matrix": sha256_path(CROSS_MATRIX),
        "missing_selected_matrix": sha256_path(MISSING_SELECTED_MATRIX),
        "registered_witness_row": sha256_path(REGISTERED_WITNESS_ROW),
        "registered_old_batch": sha256_path(REGISTERED_OLD_BATCH),
        "registered_new_batch": sha256_path(REGISTERED_NEW_BATCH),
        "missing_residual_rows": sha256_path(MISSING_RESIDUAL_ROWS),
    }
    if (
        witness_report.get("schema")
        != "max11-g0025-registered-union-provisional-witness-row-v1"
        or witness_report.get("result") != "EXACT_REGISTERED_UNION_ROW_EVALUATED"
        or not isinstance(witness_report.get("row"), dict)
        or witness_report["row"].get("file_sha256") != expected["registered_witness_row"]
    ):
        raise ValueError("registered witness row report/file mismatch")
    if (
        cross_report.get("matrix_npy_sha256") != expected["cross_matrix"]
        or missing_report.get("matrix_npy_sha256") != expected["missing_selected_matrix"]
        or new_report.get("row_matrix", {}).get("file_sha256")
        != expected["registered_new_batch"]
        or residual_report.get("row_matrix", {}).get("npy_sha256")
        != expected["missing_residual_rows"]
    ):
        raise ValueError("persisted row-matrix report/file binding mismatch")
    return {"matrix_file_sha256": expected, "producer_reports_match_files": True}


def sampled_replay(subject: RelationSubject) -> dict[str, Any]:
    begun = time.perf_counter()
    matrix_controls = validate_matrix_bindings()
    with np.load(BASELINE_MATRIX, allow_pickle=False) as archive:
        if str(archive["schema"][0]) != "max11-exact-hinge-cut-matrix-v1":
            raise ValueError("baseline matrix schema mismatch")
        baseline = np.asarray(archive["matrix"], dtype=np.int64)
    if baseline.shape != (SELECTED_ROWS, BASELINE_COLUMNS):
        raise ValueError("baseline selected matrix shape mismatch")
    cross = checked_npy(CROSS_MATRIX, (SELECTED_ROWS, CROSS_COLUMNS))
    missing_selected = checked_npy(MISSING_SELECTED_MATRIX, (SELECTED_ROWS, MISSING_COLUMNS))
    witness = checked_npy(REGISTERED_WITNESS_ROW, (REGISTERED_COLUMNS,))
    old_batch = checked_npy(REGISTERED_OLD_BATCH, (OLD_BATCH_ROWS, REGISTERED_COLUMNS))
    new_batch = checked_npy(REGISTERED_NEW_BATCH, (NEW_BATCH_ROWS, REGISTERED_COLUMNS))
    missing_residual = checked_npy(
        MISSING_RESIDUAL_ROWS, (WITNESS_ROWS + OLD_BATCH_ROWS + NEW_BATCH_ROWS, MISSING_COLUMNS)
    )
    prime_results = []
    coefficient_mutants = []
    for prime in PRIMES:
        graph, bases = relation_universe_coefficients(subject, prime)
        registered = graph[:REGISTERED_COLUMNS]
        baseline_coeff = registered[:BASELINE_COLUMNS]
        cross_coeff = registered[BASELINE_COLUMNS:]
        missing_coeff = graph[REGISTERED_COLUMNS:]
        residual = np.zeros(TOTAL_ROWS, dtype=np.int64)
        residual[:SELECTED_ROWS] = np.remainder(
            modular_matvec(baseline, baseline_coeff, prime)
            + modular_matvec(cross, cross_coeff, prime)
            + modular_matvec(missing_selected, missing_coeff, prime),
            prime,
        )
        residual[SELECTED_ROWS] = int(
            np.remainder(
                modular_matvec(witness.reshape(1, -1), registered, prime)[0]
                + modular_matvec(missing_residual[:1], missing_coeff, prime)[0],
                prime,
            )
        )
        old_start = SELECTED_ROWS + WITNESS_ROWS
        old_stop = old_start + OLD_BATCH_ROWS
        residual[old_start:old_stop] = np.remainder(
            modular_matvec(old_batch, registered, prime)
            + modular_matvec(missing_residual[1 : 1 + OLD_BATCH_ROWS], missing_coeff, prime),
            prime,
        )
        residual[old_stop:] = np.remainder(
            modular_matvec(new_batch, registered, prime)
            + modular_matvec(missing_residual[1 + OLD_BATCH_ROWS :], missing_coeff, prime),
            prime,
        )
        residual[SELECTED_HINGES:SELECTED_ROWS] = np.remainder(
            residual[SELECTED_HINGES:SELECTED_ROWS]
            + bases[0] * np.asarray(five_e_linear(), dtype=np.int64)
            + bases[1] * np.asarray(five_l_linear(), dtype=np.int64),
            prime,
        )
        residual[TARGET_ROW] = (int(residual[TARGET_ROW]) - TARGET_VALUE) % prime
        nonzero = np.flatnonzero(residual)
        if len(nonzero):
            raise AssertionError(
                f"sampled full-row replay failed at prime {prime}, row {int(nonzero[0])}, "
                f"residual {int(residual[nonzero[0]])}"
            )
        prime_results.append(
            {
                "prime": prime,
                "rows_replayed": TOTAL_ROWS,
                "nonzero_residual_rows": 0,
                "residual_int64_sha256": sha256_array(residual),
                "target_row": TARGET_ROW,
                "target_value": TARGET_VALUE,
            }
        )
        # A +1 mutation on the first graph support produces exactly that nonzero column.
        graph_positions = [
            position for position, column in enumerate(subject.support.columns) if column < GRAPH_COLUMNS
        ]
        if not graph_positions:
            raise AssertionError("relation has no graph support for coefficient mutant")
        mutant_position = graph_positions[0]
        mutant_column = subject.support.columns[mutant_position]
        if mutant_column < BASELINE_COLUMNS:
            sampled_column = np.concatenate(
                (
                    baseline[:, mutant_column],
                    witness[mutant_column : mutant_column + 1],
                    old_batch[:, mutant_column],
                    new_batch[:, mutant_column],
                )
            )
        elif mutant_column < REGISTERED_COLUMNS:
            local = mutant_column - BASELINE_COLUMNS
            sampled_column = np.concatenate(
                (
                    cross[:, local],
                    witness[mutant_column : mutant_column + 1],
                    old_batch[:, mutant_column],
                    new_batch[:, mutant_column],
                )
            )
        else:
            local = mutant_column - REGISTERED_COLUMNS
            sampled_column = np.concatenate((missing_selected[:, local], missing_residual[:, local]))
        mutant_nonzero = np.flatnonzero(np.remainder(sampled_column, prime))
        if not len(mutant_nonzero):
            raise AssertionError("coefficient-plus-one sampled mutant escaped")
        coefficient_mutants.append(
            {
                "prime": prime,
                "support_position": mutant_position,
                "combined_column": mutant_column,
                "first_detecting_row": int(mutant_nonzero[0]),
                "residual": int(sampled_column[mutant_nonzero[0]] % prime),
                "rejected": True,
            }
        )
    # Target-row misindexing must fail independently of the subject coefficients.
    row_mutant = np.zeros(TOTAL_ROWS, dtype=np.int64)
    row_mutant[TARGET_ROW] = TARGET_VALUE
    row_mutant[TARGET_ROW - 1] -= TARGET_VALUE
    if not np.count_nonzero(np.remainder(row_mutant, PRIMES[0])):
        raise AssertionError("target-row mutant escaped")
    constant_five_e_mutant = tuple(5 * factorial(N - 1) for _ in range(N))
    rank_scaled_five_l_mutant = tuple(5 * 2 * rank * factorial(N - 2) for rank in range(N))
    if constant_five_e_mutant == five_e_linear() or rank_scaled_five_l_mutant == five_l_linear():
        raise AssertionError("5E/5L base-semantics mutants escaped")
    return {
        "gate": "all-8427-frozen-rows-direct-matrix-replay",
        "result": "PASS",
        "prime_results": prime_results,
        "matrix_bindings": matrix_controls,
        "hostile_controls": {
            "coefficient_plus_one": coefficient_mutants,
            "target_row_minus_one_mutant_rejected": True,
            "constant_5E_mutant_rejected": True,
            "rank_scaled_5L_mutant_rejected": True,
        },
        "seconds": round(time.perf_counter() - begun, 6),
    }


def signed_adjacency(pair: Pair, n: int = N) -> tuple[tuple[int, ...], ...]:
    weights = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_u, one_v in side:
            u, v = one_u - 1, one_v - 1
            if not (0 <= u <= v < n):
                raise ValueError("pair endpoint outside semantic dimension")
            if u == v:
                weights[u][u] += sign
            else:
                weights[u][v] += sign
                weights[v][u] += sign
    return tuple(tuple(row) for row in weights)


def signed_cache_key(pair: Pair, n: int = N) -> tuple[int, ...]:
    """Branch-swap canonical exact-labelled key; never merges unproved relabelings."""

    matrix = signed_adjacency(pair, n)
    flat = tuple(value for row in matrix for value in row)
    negative = tuple(-value for value in flat)
    return min(flat, negative)


def direction_histogram(pair: Pair, n: int = N) -> dict[Direction, int]:
    """Fresh subset-DP census of the exact right-minus-left rank word."""

    weights = signed_adjacency(pair, n)
    full = (1 << n) - 1
    subset_sums = [[0] * (1 << n) for _ in range(n)]
    for vertex in range(n):
        for mask in range(1, 1 << n):
            bit = mask & -mask
            neighbour = bit.bit_length() - 1
            subset_sums[vertex][mask] = (
                subset_sums[vertex][mask ^ bit] + weights[vertex][neighbour]
            )
    masks_by_size: list[list[int]] = [[] for _ in range(n + 1)]
    for mask in range(1 << n):
        masks_by_size[mask.bit_count()].append(mask)
    cache: dict[int, dict[Direction, int]] = {0: {(): 1}}
    for size in range(1, n + 1):
        for mask in masks_by_size[size]:
            output: dict[Direction, int] = defaultdict(int)
            bits = mask
            while bits:
                bit = bits & -bits
                bits ^= bit
                vertex = bit.bit_length() - 1
                lower = mask ^ bit
                high = subset_sums[vertex][lower]
                for prefix, multiplicity in cache[lower].items():
                    output[prefix + (high,)] += multiplicity
            cache[mask] = dict(output)
        stale = size - 2
        if stale >= 0:
            for mask in masks_by_size[stale]:
                cache.pop(mask, None)
    histogram = cache[full]
    if sum(histogram.values()) != factorial(n):
        raise AssertionError("subset-DP permutation census mismatch")
    return histogram


def brute_direction_histogram(pair: Pair, n: int) -> dict[Direction, int]:
    from itertools import permutations

    weights = signed_adjacency(pair, n)
    output: dict[Direction, int] = defaultdict(int)
    for ordering in permutations(range(n)):
        lower: set[int] = set()
        word = []
        for vertex in ordering:
            word.append(weights[vertex][vertex] + sum(weights[vertex][other] for other in lower))
            lower.add(vertex)
        output[tuple(word)] += 1
    return dict(output)


def nonpositive_on_ordered_cone(direction: Direction) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


@dataclass(frozen=True)
class SemanticColumn:
    linear: tuple[int, ...]
    hinges: dict[Direction, int]
    raw_direction_count: int
    permutation_count: int


def exact_semantic_column(pair: Pair, n: int = N) -> SemanticColumn:
    if len(pair) != 2 or not pair[0] or len(pair[0]) != len(pair[1]):
        raise ValueError("semantic pair branches must be nonempty and equal-size")
    histogram = direction_histogram(pair, n)
    left_loops = sum(int(u == v) for u, v in pair[0])
    left_nonloops = len(pair[0]) - left_loops
    loop_factor = factorial(n - 1)
    nonloop_factor = factorial(n - 2) if n >= 2 else 0
    linear = [
        left_loops * loop_factor + left_nonloops * 2 * rank * nonloop_factor
        for rank in range(n)
    ]
    hinges: dict[Direction, int] = defaultdict(int)
    for raw_direction, multiplicity in histogram.items():
        if not any(raw_direction):
            continue
        magnitude = gcd(*(abs(value) for value in raw_direction))
        first = next(value for value in raw_direction if value)
        if first < 0:
            for rank, value in enumerate(raw_direction):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // magnitude for value in raw_direction)
        else:
            primitive = tuple(value // magnitude for value in raw_direction)
        if not nonpositive_on_ordered_cone(primitive):
            hinges[primitive] += multiplicity * magnitude
    return SemanticColumn(
        linear=tuple(linear),
        hinges=dict(hinges),
        raw_direction_count=len(histogram),
        permutation_count=sum(histogram.values()),
    )


def semantic_column_digest(column: SemanticColumn) -> str:
    digest = hashlib.sha256()
    digest.update(canonical_bytes({"linear": list(column.linear)}))
    for direction in sorted(column.hinges):
        digest.update(
            canonical_bytes(
                {"direction": list(direction), "coefficient": int(column.hinges[direction])}
            )
        )
    return digest.hexdigest()


def _aggregate_shard(
    shard: list[tuple[int, Pair, int]],
) -> dict[str, Any]:
    linear = [0] * N
    hinges: dict[Direction, int] = {}
    raw_min: int | None = None
    raw_max = 0
    active_min = None
    active_max = 0
    descriptor_digest = hashlib.sha256()
    for support_position, pair, coefficient in shard:
        column = exact_semantic_column(pair)
        if column.permutation_count != factorial(N):
            raise AssertionError("semantic worker permutation count mismatch")
        descriptor_digest.update(
            canonical_bytes(
                {
                    "support_position": support_position,
                    "coefficient_mod_crt": coefficient,
                    "column_sha256": semantic_column_digest(column),
                }
            )
        )
        for rank, value in enumerate(column.linear):
            linear[rank] = (linear[rank] + coefficient * value) % CRT_MODULUS
        for direction, value in column.hinges.items():
            updated = (hinges.get(direction, 0) + coefficient * value) % CRT_MODULUS
            if updated:
                hinges[direction] = updated
            else:
                hinges.pop(direction, None)
        raw_min = column.raw_direction_count if raw_min is None else min(raw_min, column.raw_direction_count)
        raw_max = max(raw_max, column.raw_direction_count)
        active_count = len(column.hinges)
        active_min = active_count if active_min is None else min(active_min, active_count)
        active_max = max(active_max, active_count)
    return {
        "linear": linear,
        "hinges": hinges,
        "processed": len(shard),
        "raw_direction_count_min": raw_min,
        "raw_direction_count_max": raw_max,
        "active_direction_count_min": active_min,
        "active_direction_count_max": active_max,
        "semantic_descriptor_stream_sha256": descriptor_digest.hexdigest(),
    }


def merge_hinges(destination: dict[Direction, int], source: dict[Direction, int]) -> None:
    for direction, value in source.items():
        updated = (destination.get(direction, 0) + int(value)) % CRT_MODULUS
        if updated:
            destination[direction] = updated
        else:
            destination.pop(direction, None)


def global_normal_form_replay(subject: RelationSubject, workers: int) -> dict[str, Any]:
    begun = time.perf_counter()
    coefficient_pairs = [
        crt_pair(subject.coefficients[PRIMES[0]][position], subject.coefficients[PRIMES[1]][position])
        for position in range(len(subject.support.columns))
    ]
    graph_active_positions = [
        position
        for position, coefficient in enumerate(coefficient_pairs)
        if coefficient and subject.support.columns[position] < GRAPH_COLUMNS
    ]
    if len(graph_active_positions) != 7_100:
        raise ValueError("global replay active registered support census mismatch")

    # Exact labelled signed-W/branch-swap cache.  Source quotients already bind
    # vertex-relabel classes; this cache never performs a heuristic merge.
    cached: dict[tuple[int, ...], tuple[Pair, int, list[int]]] = {}
    for position in graph_active_positions:
        pair = subject.support.pairs[position]
        if pair is None:
            raise AssertionError("active graph support has no pair")
        key = signed_cache_key(pair)
        if key in cached:
            representative, coefficient, positions = cached[key]
            # Equal exact-labelled W up to global sign is a proved equal atom
            # because both branches contain five loopless edges.
            cached[key] = (
                representative,
                (coefficient + coefficient_pairs[position]) % CRT_MODULUS,
                positions + [position],
            )
        else:
            cached[key] = (pair, coefficient_pairs[position], [position])
    effective = [
        (min(positions), pair, coefficient)
        for pair, coefficient, positions in cached.values()
        if coefficient
    ]
    effective.sort(key=lambda item: item[0])
    shard_count = min(max(1, workers), len(effective))
    shards: list[list[tuple[int, Pair, int]]] = [[] for _ in range(shard_count)]
    for index, item in enumerate(effective):
        shards[index % shard_count].append(item)

    linear = [0] * N
    hinges: dict[Direction, int] = {}
    shard_records: list[dict[str, Any]] = []
    processed = 0
    raw_min: int | None = None
    raw_max = 0
    active_min: int | None = None
    active_max = 0
    with ProcessPoolExecutor(max_workers=shard_count) as pool:
        futures = {pool.submit(_aggregate_shard, shard): index for index, shard in enumerate(shards)}
        for future in as_completed(futures):
            index = futures[future]
            value = future.result()
            processed += int(value["processed"])
            for rank, entry in enumerate(value["linear"]):
                linear[rank] = (linear[rank] + int(entry)) % CRT_MODULUS
            merge_hinges(hinges, value["hinges"])
            local_raw_min = value["raw_direction_count_min"]
            local_active_min = value["active_direction_count_min"]
            if local_raw_min is not None:
                raw_min = int(local_raw_min) if raw_min is None else min(raw_min, int(local_raw_min))
            if local_active_min is not None:
                active_min = (
                    int(local_active_min)
                    if active_min is None
                    else min(active_min, int(local_active_min))
                )
            raw_max = max(raw_max, int(value["raw_direction_count_max"] or 0))
            active_max = max(active_max, int(value["active_direction_count_max"] or 0))
            shard_records.append(
                {
                    "shard": index,
                    "support_atoms": int(value["processed"]),
                    "semantic_descriptor_stream_sha256": value[
                        "semantic_descriptor_stream_sha256"
                    ],
                }
            )
            print(
                f"G0049_GLOBAL shard={index+1}/{shard_count} "
                f"atoms={processed}/{len(effective)} hinges={len(hinges)} "
                f"seconds={time.perf_counter()-begun:.1f}",
                flush=True,
            )
    if processed != len(effective):
        raise AssertionError("global semantic shard census mismatch")

    # Include explicit bases even though the frozen relation has no selected
    # base support.  Their zero coefficients are checked above; this code path
    # prevents a future nonzero base from being silently omitted.
    base_coefficients = {FIVE_E_COLUMN: 0, FIVE_L_COLUMN: 0}
    for position, column in enumerate(subject.support.columns):
        if column in base_coefficients:
            base_coefficients[column] = coefficient_pairs[position]
    for column, vector in ((FIVE_E_COLUMN, five_e_linear()), (FIVE_L_COLUMN, five_l_linear())):
        coefficient = base_coefficients[column]
        for rank, value in enumerate(vector):
            linear[rank] = (linear[rank] + coefficient * value) % CRT_MODULUS
    linear[-1] = (linear[-1] - TARGET_VALUE) % CRT_MODULUS

    prime_results = []
    for prime in PRIMES:
        nonzero_directions = sorted(
            direction for direction, value in hinges.items() if int(value) % prime
        )
        linear_residual = [int(value % prime) for value in linear]
        digest = hashlib.sha256()
        for direction in nonzero_directions:
            digest.update(
                canonical_bytes(
                    {
                        "direction": list(direction),
                        "residual_mod_prime": int(hinges[direction] % prime),
                    }
                )
            )
        digest.update(canonical_bytes({"linear_residual_mod_prime": linear_residual}))
        prime_results.append(
            {
                "prime": prime,
                "nonzero_primitive_hinge_residuals": len(nonzero_directions),
                "nonzero_linear_residuals": int(sum(value != 0 for value in linear_residual)),
                "first_nonzero_primitive_hinge": (
                    list(nonzero_directions[0]) if nonzero_directions else None
                ),
                "first_nonzero_primitive_hinge_residual": (
                    int(hinges[nonzero_directions[0]] % prime) if nonzero_directions else None
                ),
                "linear_residual_mod_prime": linear_residual,
                "complete_residual_stream_sha256": digest.hexdigest(),
            }
        )
    failed = [
        item
        for item in prime_results
        if item["nonzero_primitive_hinge_residuals"] or item["nonzero_linear_residuals"]
    ]

    first_position = graph_active_positions[0]
    first_pair = subject.support.pairs[first_position]
    if first_pair is None:
        raise AssertionError("coefficient mutant pair absent")
    mutation_column = exact_semantic_column(first_pair)
    mutation_detected = bool(mutation_column.hinges) or any(mutation_column.linear)
    if not mutation_detected:
        raise AssertionError("global coefficient-plus-one mutant escaped")
    result = {
        "gate": "complete-primitive-normal-form-subset-DP-replay",
        "result": "PASS" if not failed else "FAIL",
        "prime_results": prime_results,
        "support_semantics": {
            "active_serialized_graph_atoms": len(graph_active_positions),
            "exact_signed_W_cache_keys": len(cached),
            "effective_nonzero_cache_classes": len(effective),
            "cache_merges": len(graph_active_positions) - len(cached),
            "support_atoms_subset_DP_reconstructed": processed,
            "raw_direction_count_min": raw_min,
            "raw_direction_count_max": raw_max,
            "active_direction_count_min": active_min,
            "active_direction_count_max": active_max,
            "permutation_count_per_atom": factorial(N),
            "aggregate_nonzero_CRT_hinge_keys_before_prime_projection": len(hinges),
            "shards": sorted(shard_records, key=lambda item: item["shard"]),
        },
        "base_semantics": {
            "5E_linear_coordinates": list(five_e_linear()),
            "5L_linear_coordinates": list(five_l_linear()),
            "5E_coefficient_mod_CRT": base_coefficients[FIVE_E_COLUMN],
            "5L_coefficient_mod_CRT": base_coefficients[FIVE_L_COLUMN],
            "hinge_coordinates_all_zero": True,
        },
        "hostile_controls": {
            "coefficient_plus_one_support_position": first_position,
            "coefficient_plus_one_mutant_detected": mutation_detected,
            "constant_5E_mutant_rejected": five_e_linear() != five_l_linear(),
            "rank_scaled_5L_mutant_rejected": five_l_linear() != five_e_linear(),
        },
        "seconds": round(time.perf_counter() - begun, 6),
    }
    return result


def self_test() -> dict[str, Any]:
    # A genuinely nontrivial four-vertex two-edge pair.  The DP is checked
    # against literal S_4 enumeration, not against any campaign helper.
    toy: Pair = (((1, 2), (3, 4)), ((1, 3), (2, 4)))
    if direction_histogram(toy, 4) != brute_direction_histogram(toy, 4):
        raise AssertionError("subset-DP/literal-permutation histogram mismatch")
    column = exact_semantic_column(toy, 4)
    swapped: Pair = (toy[1], toy[0])
    swapped_column = exact_semantic_column(swapped, 4)
    if column.linear != swapped_column.linear or column.hinges != swapped_column.hinges:
        raise AssertionError("branch-swap semantic invariance failed")
    mutant: Pair = (((1, 2), (2, 4)), toy[1])
    mutant_column = exact_semantic_column(mutant, 4)
    if column.linear == mutant_column.linear and column.hinges == mutant_column.hinges:
        raise AssertionError("endpoint semantic mutant escaped")

    for first, second in ((0, 0), (1, 2), (PRIMES[0] - 1, PRIMES[1] - 1)):
        combined = crt_pair(first, second)
        if combined % PRIMES[0] != first or combined % PRIMES[1] != second:
            raise AssertionError("CRT pair roundtrip failed")
    if five_e_linear() != tuple(10 * rank * factorial(N - 2) for rank in range(N)):
        raise AssertionError("5E formula self-test failed")
    if five_l_linear() != tuple(5 * factorial(N - 1) for _ in range(N)):
        raise AssertionError("5L formula self-test failed")
    if five_e_linear() == five_l_linear():
        raise AssertionError("5E/5L hostile base mutants are indistinguishable")

    toy_matrix = np.asarray([[1, 2, 3], [4, 5, 6]], dtype=np.int64)
    toy_coefficients = np.asarray([7, 8, 9], dtype=np.int64)
    observed = modular_matvec(toy_matrix, toy_coefficients, 101, block=2)
    expected = np.asarray(
        [sum(int(a) * int(b) for a, b in zip(row, toy_coefficients, strict=True)) % 101 for row in toy_matrix],
        dtype=np.int64,
    )
    if not np.array_equal(observed, expected):
        raise AssertionError("bounded modular matvec self-test failed")

    malformed = '{"a":1,"a":2}'
    try:
        json.loads(malformed, object_pairs_hook=unique_object)
    except ValueError:
        duplicate_rejected = True
    else:
        duplicate_rejected = False
    if not duplicate_rejected:
        raise AssertionError("duplicate JSON key mutant escaped")
    return {
        "subset_DP_equals_literal_S4_enumeration": True,
        "branch_swap_invariance": True,
        "endpoint_mutant_rejected": True,
        "CRT_roundtrips": True,
        "5E_5L_exact_formulas": True,
        "constant_5E_and_rank_scaled_5L_mutants_rejected": True,
        "bounded_modular_matvec_equals_python_integer_reference": True,
        "duplicate_JSON_key_rejected": True,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    begun = time.perf_counter()
    script_sha_before = sha256_path(SCRIPT_PATH)
    report_sha_before = sha256_path(args.g0046_report)
    extra_before = {
        label: sha256_path(path) for label, path in extra_verifier_input_paths().items()
    }
    controls = self_test()
    g0046 = load_json(args.g0046_report)
    producer_bindings = validate_g0046_bindings(g0046, args.g0046_report)
    subject = validate_relation(g0046)
    _directions, row_controls = validate_rows(g0046)
    if args.preflight_only:
        return {
            "schema": SCHEMA,
            "result": "PREFLIGHT_ONLY",
            "claim_boundary": "Bindings, schemas, support and rows only; no relation replay ran.",
            "controls": controls,
            "producer_bindings": producer_bindings,
            "relation": subject.controls,
            "rows": row_controls,
        }

    sampled = sampled_replay(subject)
    global_replay = global_normal_form_replay(subject, args.workers)
    report_sha_after = sha256_path(args.g0046_report)
    extra_after = {
        label: sha256_path(path) for label, path in extra_verifier_input_paths().items()
    }
    script_sha_after = sha256_path(SCRIPT_PATH)
    if report_sha_after != report_sha_before:
        raise RuntimeError("G-0046 report changed during clean-room verification")
    if extra_after != extra_before:
        raise RuntimeError("a clean-room verifier input changed during execution")
    if script_sha_after != script_sha_before:
        raise RuntimeError("G-0049 verifier changed during execution")

    passed = sampled.get("result") == "PASS" and global_replay.get("result") == "PASS"
    result_code = (
        "TWO_PRIME_SAMPLED_AND_GLOBAL_MODULAR_IDENTITY_VERIFIED"
        if passed
        else "GLOBAL_NORMAL_FORM_REFUTES_SAMPLED_MODULAR_CANDIDATE"
    )
    return {
        "schema": SCHEMA,
        "result": result_code,
        "object_level_question": (
            "Does the frozen G-0046 relation independently replay on every one of its "
            "8,427 sampled coordinates and in the complete primitive ordered-cone normal "
            "form at both registered primes?"
        ),
        "claim_boundary": (
            "Even a pass establishes only two finite-field identities for the displayed "
            "7,302-support modular relation. It is not an exact rational lift, a real "
            "global identity, pair-family completeness, or unrestricted MAX11. A global "
            "normal-form failure refutes this candidate despite sampled survival."
        ),
        "g0046": {
            "path": str(args.g0046_report.relative_to(ROOT)),
            "sha256": report_sha_before,
            "schema": g0046.get("schema"),
            "result": g0046.get("result"),
        },
        "relation": subject.controls,
        "row_bindings": row_controls,
        "sampled_coordinate_replay": sampled,
        "complete_global_normal_form_replay": global_replay,
        "controls": controls,
        "bindings": {
            "producer": producer_bindings,
            "verifier_inputs_before": extra_before,
            "verifier_inputs_after": extra_after,
            "verifier_inputs_stable": True,
            "verifier_script_sha256_before": script_sha_before,
            "verifier_script_sha256_after": script_sha_after,
            "verifier_script_stable": True,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": args.workers,
            "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        },
        "wall_seconds": round(time.perf_counter() - begun, 6),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--g0046-report", type=Path, default=G0046_REPORT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not (1 <= args.workers <= 16):
        parser.error("--workers must be in [1,16]")
    if args.g0046_report.resolve().parent != G46.resolve():
        parser.error("--g0046-report must be a direct G-0046 child")
    if args.output.resolve().parent != HERE.resolve():
        parser.error("--output must be a direct G-0049 child")
    return args


def main() -> int:
    args = parse_args()
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    report = run(args)
    if args.preflight_only:
        print(json.dumps(report, sort_keys=True))
        return 0
    write_gzip(args.output, report)
    print(
        f"G0049_{'PASS' if report['result'].startswith('TWO_PRIME') else 'REFUTED'} "
        f"result={report['result']} report_sha256={sha256_path(args.output)}",
        flush=True,
    )
    return 0 if report["result"].startswith("TWO_PRIME") else 1


if __name__ == "__main__":
    raise SystemExit(main())
