#!/usr/bin/env python3
"""Exact census and finite-sieve search for cross-component MAX10 lifts.

The frozen MAX10 certificate contains 252 full-support, loopless two-forest
terms.  G-0008 attached vertex 11 to two endpoints in the *same* forest
component, producing beta=1.  This script uses the disjoint complementary
choice: the A endpoint and B endpoint lie in different components.  The two
new coloured edges join the two components through vertex 11, so every raw
candidate is a full-support coloured tree (beta=0).

Commands deliberately separate exact graph quotienting, orbit-grid discovery,
held-out hinge cuts, exact rational solving, and complete hinge replay.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from fractions import Fraction
import gzip
import hashlib
import json
from math import factorial, lcm
from pathlib import Path
import sys
import time
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
G6 = ROOT / "artifacts/math/G-0006"
G8 = ROOT / "artifacts/math/G-0008"
sys.path.insert(0, str(G6))
sys.path.insert(0, str(G8))

import exact_lift_search as g6  # noqa: E402
import build_cut_matrix as g8  # noqa: E402
import evaluate_minimal_lifts as g6_eval  # noqa: E402


N = 11
CLASS_SCHEMA = "max11-cross-component-lifts-isomorphism-v1"
ORBIT_SCHEMA = "max11-cross-component-lifts-orbits-v1"
CUT_SELECTION_SCHEMA = "max11-g0009-heldout-selection-v1"
CUT_SHARD_SCHEMA = "max11-cross-component-heldout-cut-shard-v1"
CUT_MATRIX_SCHEMA = "max11-cross-component-heldout-cut-matrix-v1"
RANK_SCHEMA = "max11-cross-component-rank-report-v1"
SOLUTION_SCHEMA = "max11-cross-component-joint-solution-v1"
RESIDUAL_SCHEMA = "max11-cross-component-joint-residual-v1"

Pair = g6.Pair


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relative_root(path: Path) -> str:
    return str(path.resolve().relative_to(ROOT))


def write_json(path: Path, value: object) -> None:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    print(f"{path} bytes={len(raw)} sha256={sha256_bytes(raw)}", flush=True)


def write_gzip_json(path: Path, value: object) -> None:
    raw = canonical_bytes(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as compressed:
            compressed.write(raw)
    print(
        f"{path} uncompressed_bytes={len(raw)} compressed_bytes={path.stat().st_size} "
        f"sha256={sha256_path(path)}",
        flush=True,
    )


def pair_list_sha256(pairs: Sequence[Pair]) -> str:
    payload = [
        [[[a, b] for a, b in left], [[a, b] for a, b in right]]
        for left, right in pairs
    ]
    return sha256_bytes(canonical_bytes(payload))


def build_cross_family() -> tuple[list[Pair], list[tuple[int, ...]], str]:
    bases, _same_metadata, _same_digest = g6.build_bases()
    pairs: list[Pair] = []
    metadata: list[tuple[int, ...]] = []
    for base_index, (term_index, left, right, components) in enumerate(bases):
        if len(components) != 2:
            raise AssertionError((base_index, components))
        for left_component, right_component in ((0, 1), (1, 0)):
            for left_endpoint in components[left_component]:
                for right_endpoint in components[right_component]:
                    pair = (
                        tuple(left) + ((left_endpoint, N),),
                        tuple(right) + ((right_endpoint, N),),
                    )
                    pairs.append(pair)
                    metadata.append(
                        (
                            base_index,
                            term_index,
                            left_component,
                            right_component,
                            left_endpoint,
                            right_endpoint,
                        )
                    )
    if len(pairs) != 9_200 or len(metadata) != 9_200:
        raise AssertionError((len(pairs), len(metadata)))
    digest = sha256_bytes(canonical_bytes(metadata))
    return pairs, metadata, digest


def validate_tree_family(pairs: Sequence[Pair]) -> dict[str, object]:
    import networkx as nx

    active_histogram: dict[int, int] = defaultdict(int)
    component_histogram: dict[int, int] = defaultdict(int)
    beta_histogram: dict[int, int] = defaultdict(int)
    for index, pair in enumerate(pairs):
        edges = tuple(pair[0]) + tuple(pair[1])
        if any(a == b for a, b in edges):
            raise AssertionError(f"loop at raw candidate {index}")
        if len(edges) != 10 or len(set(edges)) != 10:
            raise AssertionError(f"non-simple union at raw candidate {index}")
        graph = nx.Graph()
        graph.add_nodes_from(range(1, N + 1))
        graph.add_edges_from(edges)
        active = sum(1 for vertex in graph if graph.degree(vertex))
        components = nx.number_connected_components(graph)
        beta = len(edges) - active + components
        if active != N or components != 1 or beta != 0 or not nx.is_tree(graph):
            raise AssertionError((index, active, components, beta))
        active_histogram[active] += 1
        component_histogram[components] += 1
        beta_histogram[beta] += 1
    return {
        "active_vertex_histogram": {str(k): v for k, v in sorted(active_histogram.items())},
        "component_histogram": {str(k): v for k, v in sorted(component_histogram.items())},
        "colored_multigraph_beta_histogram": {str(k): v for k, v in sorted(beta_histogram.items())},
        "loopless": True,
        "simple_uncoloured_union": True,
        "all_networkx_trees": True,
    }


def build_classes() -> dict[str, object]:
    import networkx as nx

    pairs, metadata, metadata_digest = build_cross_family()
    topology = validate_tree_family(pairs)
    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    buckets: dict[str, list[int]] = defaultdict(list)
    representative_graphs: list[object] = []
    representatives: list[int] = []
    raw_to_class: list[int] = []
    begun = time.time()
    for raw_index, pair in enumerate(pairs):
        graph = g6.incidence_graph(pair)
        wl_hash = nx.weisfeiler_lehman_graph_hash(
            graph, node_attr="kind", iterations=16, digest_size=32
        )
        class_index = None
        for possible_class in buckets[wl_hash]:
            if nx.is_isomorphic(
                graph, representative_graphs[possible_class], node_match=node_match
            ):
                class_index = possible_class
                break
        if class_index is None:
            class_index = len(representatives)
            representatives.append(raw_index)
            representative_graphs.append(graph)
            buckets[wl_hash].append(class_index)
        raw_to_class.append(class_index)
        if (raw_index + 1) % 1000 == 0:
            print(
                f"quotient raw={raw_index+1}/{len(pairs)} classes={len(representatives)} "
                f"seconds={time.time()-begun:.1f}",
                flush=True,
            )
    class_sizes = [0] * len(representatives)
    for class_index in raw_to_class:
        class_sizes[class_index] += 1
    if sum(class_sizes) != len(pairs):
        raise AssertionError("class census mismatch")
    return {
        "schema": CLASS_SCHEMA,
        "n": N,
        "family": (
            "cross-component two-edge lifts of the 252 full-support MAX10 two-forest terms"
        ),
        "source_certificate_path": relative_root(g6.CERTIFICATE),
        "source_certificate_sha256": sha256_path(g6.CERTIFICATE),
        "raw_candidate_count": len(pairs),
        "candidate_metadata_sha256": metadata_digest,
        "raw_pair_list_sha256": pair_list_sha256(pairs),
        "topology": topology,
        "disjoint_from_g0008_reason": (
            "every G-0009 union is connected with beta=0; every G-0008 same-component lift "
            "leaves the other base component disconnected and has colored-multigraph beta=1"
        ),
        "equivalence": "vertex relabelling and one global A/B colour swap",
        "accelerator": "NetworkX Weisfeiler-Lehman node-attribute hash, 16 iterations",
        "authority": "NetworkX exact VF2 typed-incidence-graph isomorphism within each WL bucket",
        "networkx_version": nx.__version__,
        "class_count": len(representatives),
        "representative_raw_indices": representatives,
        "raw_to_class": raw_to_class,
        "class_sizes": class_sizes,
        "claim_boundary": (
            "Exact quotient of this 9,200-item generated list only; completeness is relative to "
            "the pinned 252 MAX10 base terms, not all abstract MAX11 trees."
        ),
    }


def load_classes(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != CLASS_SCHEMA or document.get("n") != N:
        raise ValueError("wrong cross-component class schema")
    pairs, _metadata, metadata_digest = build_cross_family()
    if document.get("raw_candidate_count") != len(pairs):
        raise ValueError("raw candidate census mismatch")
    if document.get("candidate_metadata_sha256") != metadata_digest:
        raise ValueError("candidate metadata digest mismatch")
    if document.get("raw_pair_list_sha256") != pair_list_sha256(pairs):
        raise ValueError("raw pair digest mismatch")
    if document.get("source_certificate_sha256") != sha256_path(g6.CERTIFICATE):
        raise ValueError("source certificate digest mismatch")
    representatives = document.get("representative_raw_indices")
    raw_to_class = document.get("raw_to_class")
    if not isinstance(representatives, list) or not isinstance(raw_to_class, list):
        raise ValueError("malformed quotient maps")
    if len(representatives) != document.get("class_count") or len(raw_to_class) != len(pairs):
        raise ValueError("quotient map length mismatch")
    return document


def build_orbit_group(group_index: int, output_directory: Path) -> Path:
    pairs, metadata, metadata_digest = build_cross_family()
    del pairs
    bases, _same_metadata, _same_digest = g6.build_bases()
    entries_by_base: list[list[tuple[int, int]]] = [[] for _ in bases]
    for base_index, _term, _lc, _rc, left_endpoint, right_endpoint in metadata:
        entries_by_base[base_index].append((left_endpoint, right_endpoint))
    groups = g6.profile_groups()
    if not (0 <= group_index < len(groups)):
        raise ValueError(f"group index must lie in [0,{len(groups)})")
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
        new_edge_values = edge_values[
            [edge_index[(endpoint, N)] for endpoint in range(1, N)]
        ]
        row = np.empty(len(metadata), dtype=np.int64)
        offset = 0
        for base_index, (_term, left, right, _components) in enumerate(bases):
            left_base = edge_values[[edge_index[edge] for edge in left]].sum(
                axis=0, dtype=np.int16
            )
            right_base = edge_values[[edge_index[edge] for edge in right]].sum(
                axis=0, dtype=np.int16
            )
            # endpoint_sums[p-1,q-1] needs independent A/B axes.
            endpoint_sums = np.maximum(
                (left_base[None, :] + new_edge_values)[:, None, :],
                (right_base[None, :] + new_edge_values)[None, :, :],
            ).sum(axis=2, dtype=np.int64)
            for left_endpoint, right_endpoint in entries_by_base[base_index]:
                row[offset] = endpoint_sums[left_endpoint - 1, right_endpoint - 1]
                offset += 1
        if offset != len(metadata):
            raise AssertionError((offset, len(metadata)))
        rows.append(row)
        targets.append(
            state_count * max(level for level, count in enumerate(profile) if count)
        )
        print(
            f"orbit-group={group_index} profile={profile_index+1}/{len(profiles)} "
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


def load_cross_orbits(directory: Path, metadata_digest: str):
    rows = []
    targets = []
    profiles = []
    files = []
    groups = g6.profile_groups()
    for group_index, expected_profiles in enumerate(groups):
        path = directory / f"group-{group_index:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != ORBIT_SCHEMA:
                raise ValueError(f"orbit schema mismatch: {path}")
            if str(data["candidate_sha256"][0]) != metadata_digest:
                raise ValueError(f"orbit metadata mismatch: {path}")
            if int(data["group_index"][0]) != group_index or int(data["group_count"][0]) != len(groups):
                raise ValueError(f"orbit group metadata mismatch: {path}")
            observed = [tuple(map(int, row)) for row in data["profiles"].tolist()]
            if observed != expected_profiles:
                raise ValueError(f"orbit profiles mismatch: {path}")
            expected_targets = [
                g6.assignment_count(profile)
                * max(level for level, count in enumerate(profile) if count)
                for profile in expected_profiles
            ]
            if data["targets"].tolist() != expected_targets:
                raise ValueError(f"orbit targets mismatch: {path}")
            rows.append(data["rows"])
            targets.append(data["targets"])
            profiles.append(data["profiles"])
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)})
    matrix = np.concatenate(rows, axis=0)
    target = np.concatenate(targets)
    profile_array = np.concatenate(profiles, axis=0)
    if matrix.shape != (364, 9_200) or target.shape != (364,):
        raise AssertionError((matrix.shape, target.shape))
    if [tuple(map(int, row)) for row in profile_array.tolist()] != g6.all_profiles():
        raise AssertionError("orbit profile coverage mismatch")
    return matrix, target, profile_array, files


def reduced_orbit_matrices(classes_path: Path, cross_orbit_directory: Path):
    cross_classes = load_classes(classes_path)
    cross_raw, target, profiles, cross_files = load_cross_orbits(
        cross_orbit_directory, str(cross_classes["candidate_metadata_sha256"])
    )
    cross_reps = np.asarray(cross_classes["representative_raw_indices"], dtype=np.int64)
    cross_map = np.asarray(cross_classes["raw_to_class"], dtype=np.int64)
    if not np.array_equal(cross_raw, cross_raw[:, cross_reps[cross_map]]):
        raise AssertionError("cross-component quotient changes an orbit evaluation")
    same_classes_path = G6 / "isomorphism_classes_v2.json"
    same_classes = g6.load_classes(same_classes_path)
    same_raw, same_target, same_profiles, same_files = g6.load_orbit_matrix(
        G6 / "orbit_data", str(same_classes["candidate_metadata_sha256"])
    )
    if not np.array_equal(target, same_target) or not np.array_equal(profiles, same_profiles):
        raise AssertionError("same/cross orbit targets or profile order disagree")
    same_reps = np.asarray(same_classes["representative_raw_indices"], dtype=np.int64)
    same_map = np.asarray(same_classes["raw_to_class"], dtype=np.int64)
    if not np.array_equal(same_raw, same_raw[:, same_reps[same_map]]):
        raise AssertionError("G-0008 quotient changes an orbit evaluation")
    return {
        "same": same_raw[:, same_reps],
        "cross": cross_raw[:, cross_reps],
        "target": target,
        "profiles": profiles,
        "same_classes": same_classes,
        "cross_classes": cross_classes,
        "same_files": same_files,
        "cross_files": cross_files,
        "same_classes_path": same_classes_path,
        "cross_classes_path": classes_path,
    }


def make_heldout_selection() -> dict[str, object]:
    first_path = G8 / "cut_selection.json"
    second_path = G8 / "cut_selection_02.json"
    first = json.loads(first_path.read_text(encoding="utf-8"))
    second = json.loads(second_path.read_text(encoding="utf-8"))
    first_directions = {tuple(map(int, row)) for row in first["directions"]}
    second_directions = tuple(tuple(map(int, row)) for row in second["directions"])
    overlap = first_directions.intersection(second_directions)
    if overlap:
        raise AssertionError(f"purported held-out rows overlap training rows: {len(overlap)}")
    if list(second_directions) != sorted(set(second_directions)):
        raise AssertionError("held-out directions are not uniquely sorted")
    for direction in second_directions:
        if len(direction) != N or sum(direction) != 0 or g6.nonpositive_on_ordered_cone(direction):
            raise AssertionError(f"invalid held-out direction: {direction}")
    return {
        "schema": CUT_SELECTION_SCHEMA,
        "n": N,
        "directions": [list(direction) for direction in second_directions],
        "selected_count": len(second_directions),
        "training_selection": relative_root(first_path),
        "training_selection_sha256": sha256_path(first_path),
        "source_selection": relative_root(second_path),
        "source_selection_sha256": sha256_path(second_path),
        "training_overlap_count": 0,
        "selection_rule": (
            "the complete lexicographically sorted second G-0008 cut batch, which was derived "
            "from the first-batch solution residual and has zero rows in common with the first batch"
        ),
        "claim_boundary": (
            "Held out from the G-0008 887-row solve, but adaptively selected from that solve's "
            "residual; it is not an IID or preregistered statistical test set."
        ),
    }


def load_heldout_selection(path: Path) -> tuple[dict[str, object], tuple[tuple[int, ...], ...]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != CUT_SELECTION_SCHEMA or document.get("n") != N:
        raise ValueError("wrong held-out selection schema")
    if document.get("training_selection_sha256") != sha256_path(G8 / "cut_selection.json"):
        raise ValueError("training selection hash mismatch")
    if document.get("source_selection_sha256") != sha256_path(G8 / "cut_selection_02.json"):
        raise ValueError("source selection hash mismatch")
    directions = tuple(tuple(map(int, row)) for row in document["directions"])
    if len(directions) != document.get("selected_count") or list(directions) != sorted(set(directions)):
        raise ValueError("held-out direction census/order mismatch")
    return document, directions


def family_pairs_and_representatives(family: str, cross_classes_path: Path):
    if family == "cross":
        pairs, _metadata, _digest = build_cross_family()
        classes = load_classes(cross_classes_path)
        classes_path = cross_classes_path
    elif family == "same":
        pairs, _digest = g6.raw_candidate_pairs()
        classes_path = G6 / "isomorphism_classes_v2.json"
        classes = g6.load_classes(classes_path)
    else:
        raise ValueError(f"unknown family {family}")
    representatives = list(map(int, classes["representative_raw_indices"]))
    return pairs, representatives, classes_path


def build_cut_shard(
    family: str,
    selection_path: Path,
    cross_classes_path: Path,
    shard_index: int,
    shard_count: int,
    output_directory: Path,
) -> Path:
    if not (0 <= shard_index < shard_count):
        raise ValueError("invalid shard index/count")
    _selection, directions = load_heldout_selection(selection_path)
    pairs, representatives, classes_path = family_pairs_and_representatives(
        family, cross_classes_path
    )
    start = len(representatives) * shard_index // shard_count
    stop = len(representatives) * (shard_index + 1) // shard_count
    row_index = {direction: index for index, direction in enumerate(directions)}
    matrix = np.empty((len(directions) + N, stop - start), dtype=np.int64)
    begun = time.time()
    for local_index, class_index in enumerate(range(start, stop)):
        pair = pairs[representatives[class_index]]
        matrix[:, local_index] = g8.restricted_column(pair, row_index, len(directions))
        if (local_index + 1) % 50 == 0:
            print(
                f"cut family={family} shard={shard_index}/{shard_count} "
                f"columns={local_index+1}/{stop-start} seconds={time.time()-begun:.1f}",
                flush=True,
            )
    output_directory.mkdir(parents=True, exist_ok=True)
    destination = output_directory / f"{family}-shard-{shard_index:02d}-of-{shard_count:02d}.npz"
    np.savez_compressed(
        destination,
        schema=np.asarray([CUT_SHARD_SCHEMA]),
        family=np.asarray([family]),
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
    family: str,
    selection_path: Path,
    cross_classes_path: Path,
    shard_directory: Path,
    shard_count: int,
    output: Path,
) -> None:
    _selection, directions = load_heldout_selection(selection_path)
    _pairs, representatives, classes_path = family_pairs_and_representatives(
        family, cross_classes_path
    )
    matrices = []
    indices = []
    files = []
    for shard_index in range(shard_count):
        path = shard_directory / f"{family}-shard-{shard_index:02d}-of-{shard_count:02d}.npz"
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != CUT_SHARD_SCHEMA or str(data["family"][0]) != family:
                raise ValueError(f"cut shard schema/family mismatch: {path}")
            if str(data["selection_sha256"][0]) != sha256_path(selection_path):
                raise ValueError(f"cut shard selection mismatch: {path}")
            if str(data["classes_sha256"][0]) != sha256_path(classes_path):
                raise ValueError(f"cut shard classes mismatch: {path}")
            if int(data["shard_index"][0]) != shard_index or int(data["shard_count"][0]) != shard_count:
                raise ValueError(f"cut shard index/count mismatch: {path}")
            matrices.append(data["matrix"])
            indices.append(data["class_indices"])
        files.append({"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)})
    matrix = np.concatenate(matrices, axis=1)
    class_indices = np.concatenate(indices)
    expected = np.arange(len(representatives), dtype=np.int64)
    if not np.array_equal(class_indices, expected):
        raise AssertionError("cut shard class coverage/order mismatch")
    if matrix.shape != (len(directions) + N, len(representatives)):
        raise AssertionError(matrix.shape)
    output.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output,
        schema=np.asarray([CUT_MATRIX_SCHEMA]),
        family=np.asarray([family]),
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
    path: Path,
    family: str,
    selection_path: Path,
    classes_path: Path,
    class_count: int,
) -> np.ndarray:
    with np.load(path, allow_pickle=False) as data:
        if str(data["schema"][0]) != CUT_MATRIX_SCHEMA or str(data["family"][0]) != family:
            raise ValueError(f"cut matrix schema/family mismatch: {path}")
        if str(data["selection_sha256"][0]) != sha256_path(selection_path):
            raise ValueError(f"cut matrix selection mismatch: {path}")
        if str(data["classes_sha256"][0]) != sha256_path(classes_path):
            raise ValueError(f"cut matrix classes mismatch: {path}")
        indices = data["class_indices"]
        matrix = data["matrix"]
    if not np.array_equal(indices, np.arange(class_count, dtype=np.int64)):
        raise ValueError(f"cut matrix class order mismatch: {path}")
    return matrix


def modular_rank_record(matrix: np.ndarray, target: np.ndarray, primes: Sequence[int]):
    from flint import nmod_mat

    augmented = np.column_stack((matrix, target))
    records = []
    for prime in primes:
        begun = time.time()
        rank = nmod_mat(matrix.tolist(), prime).rank()
        augmented_rank = nmod_mat(augmented.tolist(), prime).rank()
        records.append(
            {
                "prime": prime,
                "rank": rank,
                "augmented_rank": augmented_rank,
                "target_member": rank == augmented_rank,
                "seconds": round(time.time() - begun, 6),
            }
        )
    return records


def exact_rank_record(
    matrix: np.ndarray, target: np.ndarray, witness_prime: int
) -> dict[str, object]:
    """Certify the Q-rank with a compact exact row-span witness.

    A nonzero r-by-r minor selected modulo ``witness_prime`` proves rank at
    least r over Q.  Exact rational reconstruction of every remaining row
    from the r pivot rows proves rank at most r.  Target membership is then
    checked by one exact solve on the same minor and replay on every row.
    This avoids materialising the whole wide matrix as Python big integers.
    """

    from flint import fmpq, fmpq_mat, nmod_mat

    begun = time.time()
    modular = nmod_mat(matrix.tolist(), witness_prime)
    rref, rank = modular.rref()
    basis_columns = pivot_columns(rref, rank, matrix.shape[1])
    if len(basis_columns) != rank:
        raise AssertionError("exact-witness basis-column extraction failed")
    basis_modular = nmod_mat(matrix[:, basis_columns].tolist(), witness_prime)
    transposed_rref, row_rank = basis_modular.transpose().rref()
    pivot_rows = pivot_columns(transposed_rref, row_rank, matrix.shape[0])
    if row_rank != rank or len(pivot_rows) != rank:
        raise AssertionError("exact-witness pivot-row extraction failed")

    minor = fmpq_mat(matrix[np.ix_(pivot_rows, basis_columns)].tolist())
    if not minor.det():
        raise AssertionError("modularly nonzero witness minor vanished over Q")
    pivot_set = set(pivot_rows)
    nonpivot_rows = [row for row in range(matrix.shape[0]) if row not in pivot_set]
    row_coefficients = None
    if nonpivot_rows:
        # L * minor = remaining_rows[:,basis_columns].
        remaining_basis = fmpq_mat(
            matrix[np.ix_(nonpivot_rows, basis_columns)].tolist()
        )
        coefficients_t = minor.transpose().solve(remaining_basis.transpose())
        row_coefficients = coefficients_t.transpose()
        pivot_matrix = fmpq_mat(matrix[pivot_rows, :].tolist())
        reconstructed = row_coefficients * pivot_matrix
        expected = fmpq_mat(matrix[nonpivot_rows, :].tolist())
        if reconstructed != expected:
            raise AssertionError("exact row-span witness replay failed")

    rhs = fmpq_mat([[int(target[row])] for row in pivot_rows])
    solution = minor.solve(rhs)
    basis_full = fmpq_mat(matrix[:, basis_columns].tolist())
    replay = basis_full * solution
    first_residual = None
    for row in range(matrix.shape[0]):
        residual = replay[row, 0] - int(target[row])
        if residual:
            first_residual = {"row": row, "residual": str(fmpq(residual))}
            break
    member = first_residual is None
    dual_witness = None
    if not member:
        assert first_residual is not None and row_coefficients is not None
        failed_row = int(first_residual["row"])
        nonpivot_position = nonpivot_rows.index(failed_row)
        terms = []
        target_pairing = fmpq(int(target[failed_row]))
        for position, pivot_row in enumerate(pivot_rows):
            coefficient = -row_coefficients[nonpivot_position, position]
            if coefficient:
                terms.append({"row": pivot_row, "coefficient": str(coefficient)})
                target_pairing += coefficient * int(target[pivot_row])
        terms.append({"row": failed_row, "coefficient": "1"})
        if not target_pairing or target_pairing != -fmpq(first_residual["residual"]):
            raise AssertionError("exact dual target pairing disagreement")
        dual_witness = {
            "terms": terms,
            "term_count": len(terms),
            "annihilates_all_candidate_columns": True,
            "target_pairing": str(target_pairing),
            "terms_canonical_sha256": sha256_bytes(canonical_bytes(terms)),
        }
    return {
        "authority": (
            "python-flint exact fmpq minor plus complete rational row-span and target replay"
        ),
        "witness_prime": witness_prime,
        "rank_over_Q": rank,
        "augmented_rank_over_Q": rank if member else rank + 1,
        "target_member_over_Q": member,
        "basis_column_count": len(basis_columns),
        "pivot_row_count": len(pivot_rows),
        "basis_columns_int64_sha256": sha256_bytes(
            np.asarray(basis_columns, dtype=np.int64).tobytes(order="C")
        ),
        "pivot_rows_int64_sha256": sha256_bytes(
            np.asarray(pivot_rows, dtype=np.int64).tobytes(order="C")
        ),
        "all_nonpivot_rows_replayed_exactly": True,
        "target_replayed_exactly": member,
        "first_target_residual": first_residual,
        "nonmembership_dual_witness": dual_witness,
        "seconds": round(time.time() - begun, 6),
    }


def build_rank_report(
    classes_path: Path,
    cross_orbit_directory: Path,
    selection_path: Path | None,
    same_cut_path: Path | None,
    cross_cut_path: Path | None,
    primes: Sequence[int],
    exact: bool,
) -> dict[str, object]:
    orbit = reduced_orbit_matrices(classes_path, cross_orbit_directory)
    same_orbit = orbit["same"]
    cross_orbit = orbit["cross"]
    orbit_target = orbit["target"]
    systems: dict[str, tuple[np.ndarray, np.ndarray]] = {
        "orbit_same": (same_orbit, orbit_target),
        "orbit_cross": (cross_orbit, orbit_target),
        "orbit_union": (np.concatenate((same_orbit, cross_orbit), axis=1), orbit_target),
    }
    heldout_metadata = None
    if selection_path is not None:
        if same_cut_path is None or cross_cut_path is None:
            raise ValueError("both same and cross held-out matrices are required")
        selection, directions = load_heldout_selection(selection_path)
        same_classes_path = orbit["same_classes_path"]
        same_cut = load_cut_matrix(
            same_cut_path,
            "same",
            selection_path,
            same_classes_path,
            same_orbit.shape[1],
        )
        cross_cut = load_cut_matrix(
            cross_cut_path,
            "cross",
            selection_path,
            classes_path,
            cross_orbit.shape[1],
        )
        if same_cut.shape[0] != len(directions) + N or cross_cut.shape[0] != len(directions) + N:
            raise AssertionError((same_cut.shape, cross_cut.shape, len(directions)))
        cut_target = np.zeros(len(directions) + N, dtype=np.int64)
        cut_target[-1] = factorial(N)
        joint_target = np.concatenate((orbit_target, cut_target))
        systems.update(
            {
                "heldout_same": (same_cut, cut_target),
                "heldout_cross": (cross_cut, cut_target),
                "heldout_union": (np.concatenate((same_cut, cross_cut), axis=1), cut_target),
                "joint_same": (np.concatenate((same_orbit, same_cut), axis=0), joint_target),
                "joint_cross": (np.concatenate((cross_orbit, cross_cut), axis=0), joint_target),
                "joint_union": (
                    np.concatenate(
                        (
                            np.concatenate((same_orbit, cross_orbit), axis=1),
                            np.concatenate((same_cut, cross_cut), axis=1),
                        ),
                        axis=0,
                    ),
                    joint_target,
                ),
            }
        )
        heldout_metadata = {
            "selection_path": relative_root(selection_path),
            "selection_sha256": sha256_path(selection_path),
            "direction_count": len(directions),
            "same_matrix": relative_root(same_cut_path),
            "same_matrix_sha256": sha256_path(same_cut_path),
            "cross_matrix": relative_root(cross_cut_path),
            "cross_matrix_sha256": sha256_path(cross_cut_path),
            "adaptive_holdout_warning": selection["claim_boundary"],
        }
    results = {}
    for name, (matrix, target) in systems.items():
        print(f"ranking {name} shape={matrix.shape}", flush=True)
        record = {
            "rows": matrix.shape[0],
            "columns": matrix.shape[1],
            "matrix_int64_c_sha256": sha256_bytes(matrix.tobytes(order="C")),
            "target_int64_c_sha256": sha256_bytes(target.tobytes(order="C")),
            "modular": modular_rank_record(matrix, target, primes),
        }
        if exact:
            record["exact"] = exact_rank_record(matrix, target, primes[0])
        results[name] = record
    if "joint_union" in results:
        same_ranks = [item["rank"] for item in results["joint_same"]["modular"]]
        union_ranks = [item["rank"] for item in results["joint_union"]["modular"]]
        modular_gains = [union - same for same, union in zip(same_ranks, union_ranks)]
    else:
        same_ranks = [item["rank"] for item in results["orbit_same"]["modular"]]
        union_ranks = [item["rank"] for item in results["orbit_union"]["modular"]]
        modular_gains = [union - same for same, union in zip(same_ranks, union_ranks)]
    return {
        "schema": RANK_SCHEMA,
        "n": N,
        "cross_family": "9,200 raw cross-component MAX10 lifts, exactly quotiented",
        "same_component_baseline": "G-0008's 9,804 exact classes",
        "cross_classes_path": relative_root(classes_path),
        "cross_classes_sha256": sha256_path(classes_path),
        "same_classes_path": relative_root(orbit["same_classes_path"]),
        "same_classes_sha256": sha256_path(orbit["same_classes_path"]),
        "cross_class_count": cross_orbit.shape[1],
        "same_class_count": same_orbit.shape[1],
        "orbit_grid": "all 364 S_11-orbits of {0,1,2,3}^11",
        "heldout": heldout_metadata,
        "primes": list(primes),
        "results": results,
        "rank_gain_cross_over_same": modular_gains,
        "claim_boundary": (
            "Modular ranks are exact only over their named finite fields. When present, the "
            "python-flint fmpq minor plus complete row-span replay certifies the rank over Q. "
            "Finite-grid or selected-cut target membership is never a global functional identity; "
            "complete hinge replay is required."
        ),
    }


def pivot_columns(rref_matrix, row_count: int, column_count: int) -> list[int]:
    pivots = []
    for row in range(row_count):
        for column in range(column_count):
            if rref_matrix[row, column]:
                pivots.append(column)
                break
    return pivots


def load_joint_system(
    classes_path: Path,
    cross_orbit_directory: Path,
    selection_path: Path,
    same_cut_path: Path,
    cross_cut_path: Path,
):
    orbit = reduced_orbit_matrices(classes_path, cross_orbit_directory)
    _selection, directions = load_heldout_selection(selection_path)
    same_cut = load_cut_matrix(
        same_cut_path,
        "same",
        selection_path,
        orbit["same_classes_path"],
        orbit["same"].shape[1],
    )
    cross_cut = load_cut_matrix(
        cross_cut_path,
        "cross",
        selection_path,
        classes_path,
        orbit["cross"].shape[1],
    )
    orbit_union = np.concatenate((orbit["same"], orbit["cross"]), axis=1)
    cut_union = np.concatenate((same_cut, cross_cut), axis=1)
    system = np.concatenate((orbit_union, cut_union), axis=0)
    cut_target = np.zeros(len(directions) + N, dtype=np.int64)
    cut_target[-1] = factorial(N)
    target = np.concatenate((orbit["target"], cut_target))
    return orbit, system, target


def solve_joint(
    classes_path: Path,
    cross_orbit_directory: Path,
    selection_path: Path,
    same_cut_path: Path,
    cross_cut_path: Path,
    prime: int,
) -> dict[str, object]:
    from flint import fmpq, fmpq_mat, nmod_mat

    orbit, system, target = load_joint_system(
        classes_path, cross_orbit_directory, selection_path, same_cut_path, cross_cut_path
    )
    begun = time.time()
    modular = nmod_mat(system.tolist(), prime)
    rref, rank = modular.rref()
    augmented_rank = nmod_mat(np.column_stack((system, target)).tolist(), prime).rank()
    if augmented_rank != rank:
        return {
            "schema": SOLUTION_SCHEMA,
            "n": N,
            "system_rows": system.shape[0],
            "candidate_columns": system.shape[1],
            "prime": prime,
            "rank_mod_prime": rank,
            "augmented_rank_mod_prime": augmented_rank,
            "target_member_mod_prime": False,
            "claim_boundary": (
                "Nonmembership over one finite field is not by itself rational nonmembership; "
                "consult the exact rank report before making a Q-span claim."
            ),
        }
    basis_columns = pivot_columns(rref, rank, system.shape[1])
    basis_modular = nmod_mat(system[:, basis_columns].tolist(), prime)
    transposed_rref, row_rank = basis_modular.transpose().rref()
    pivot_rows = pivot_columns(transposed_rref, row_rank, system.shape[0])
    if row_rank != rank or len(pivot_rows) != rank:
        raise AssertionError("pivot row extraction failed")
    exact = fmpq_mat(rank, rank)
    rhs = fmpq_mat(rank, 1)
    for rr, source_row in enumerate(pivot_rows):
        for cc, source_column in enumerate(basis_columns):
            value = int(system[source_row, source_column])
            if value:
                exact[rr, cc] = value
        if target[source_row]:
            rhs[rr, 0] = int(target[source_row])
    coefficients = exact.solve(rhs)
    for source_row in range(system.shape[0]):
        value = fmpq(0)
        for cc, source_column in enumerate(basis_columns):
            entry = int(system[source_row, source_column])
            if entry:
                value += coefficients[cc, 0] * entry
        if value != int(target[source_row]):
            raise AssertionError(f"exact joint replay failed at row {source_row}")

    same_pairs, _ = g6.raw_candidate_pairs()
    same_reps = list(map(int, orbit["same_classes"]["representative_raw_indices"]))
    cross_pairs, _metadata, _digest = build_cross_family()
    cross_reps = list(map(int, orbit["cross_classes"]["representative_raw_indices"]))
    same_count = len(same_reps)
    terms = []
    for cc, source_column in enumerate(basis_columns):
        internal = coefficients[cc, 0]
        if not internal:
            continue
        if source_column < same_count:
            family = "same"
            class_index = source_column
            raw_index = same_reps[class_index]
            pair = same_pairs[raw_index]
        else:
            family = "cross"
            class_index = source_column - same_count
            raw_index = cross_reps[class_index]
            pair = cross_pairs[raw_index]
        terms.append(
            {
                "coefficient": str(internal / factorial(N)),
                "internal_coefficient": str(internal),
                "family": family,
                "class_index": class_index,
                "representative_raw_index": raw_index,
                "pair": [[list(edge) for edge in side] for side in pair],
            }
        )
    return {
        "schema": SOLUTION_SCHEMA,
        "n": N,
        "family": "union of G-0008 same-component and G-0009 cross-component MAX10 lifts",
        "classes_sha256": {
            "same": sha256_path(orbit["same_classes_path"]),
            "cross": sha256_path(classes_path),
        },
        "selection_sha256": sha256_path(selection_path),
        "cut_matrix_sha256": {
            "same": sha256_path(same_cut_path),
            "cross": sha256_path(cross_cut_path),
        },
        "system_int64_c_sha256": sha256_bytes(system.tobytes(order="C")),
        "target_int64_c_sha256": sha256_bytes(target.tobytes(order="C")),
        "system_rows": system.shape[0],
        "candidate_columns": system.shape[1],
        "prime": prime,
        "rank_mod_prime": rank,
        "augmented_rank_mod_prime": augmented_rank,
        "target_member_mod_prime": True,
        "exact_constraint_replay": True,
        "basis_column_count": len(basis_columns),
        "nonzero_term_count": len(terms),
        "seconds": round(time.time() - begun, 6),
        "normalization": "internal a=11!*certificate coefficient",
        "warning": "finite orbit-plus-heldout-cut solution only; complete hinge replay required",
        "terms": terms,
    }


def parse_solution(path: Path) -> tuple[list[Pair], list[Fraction], dict[str, object]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != SOLUTION_SCHEMA or document.get("n") != N:
        raise ValueError("wrong joint solution schema")
    if document.get("exact_constraint_replay") is not True:
        raise ValueError("solution lacks exact finite-system replay")
    pairs = []
    coefficients = []
    for term in document["terms"]:
        pair = tuple(
            tuple(tuple(map(int, edge)) for edge in side) for side in term["pair"]
        )
        if len(pair) != 2 or any(len(side) != 5 for side in pair):
            raise ValueError("malformed solution pair")
        coefficient = Fraction(term["coefficient"])
        if not coefficient:
            raise ValueError("zero term serialized")
        pairs.append(pair)
        coefficients.append(coefficient)
    if len(pairs) != document.get("nonzero_term_count"):
        raise ValueError("solution term census mismatch")
    return pairs, coefficients, document


def complete_residual(solution_path: Path, workers: int) -> dict[str, object]:
    pairs, coefficients, solution = parse_solution(solution_path)
    denominator_scale = 1
    for coefficient in coefficients:
        denominator_scale = lcm(denominator_scale, coefficient.denominator)
    integer_coefficients = [
        coefficient.numerator * (denominator_scale // coefficient.denominator)
        for coefficient in coefficients
    ]
    linear = [0] * N
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    raw_counts = [0] * len(pairs)
    begun = time.time()
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for index, column in executor.map(g6._column_worker, enumerate(pairs), chunksize=1):
            coefficient = integer_coefficients[index]
            raw_counts[index] = column.raw_direction_count
            for rank, value in enumerate(column.linear):
                linear[rank] += coefficient * value
            for direction, value in column.hinges.items():
                hinges[direction] += coefficient * value
            if (index + 1) % 25 == 0:
                print(
                    f"complete residual columns={index+1}/{len(pairs)} seconds={time.time()-begun:.1f}",
                    flush=True,
                )
    linear[-1] -= denominator_scale
    nonzero = sorted((direction, value) for direction, value in hinges.items() if value)
    return {
        "schema": RESIDUAL_SCHEMA,
        "n": N,
        "solution_sha256": sha256_path(solution_path),
        "term_count": len(pairs),
        "denominator_scale": str(denominator_scale),
        "linear_residual": [str(value) for value in linear],
        "nonzero_hinge_count": len(nonzero),
        "raw_direction_count_min": min(raw_counts, default=0),
        "raw_direction_count_max": max(raw_counts, default=0),
        "global_identity": not any(linear) and not nonzero,
        "hinges": [
            {"direction": list(direction), "coefficient": str(value)}
            for direction, value in nonzero
        ],
        "seconds": round(time.time() - begun, 6),
        "claim_boundary": (
            "Zero certifies only this serialized finite-family combination; nonzero refutes only "
            "this selected solution, not the entire same-plus-cross rational span."
        ),
        "finite_solution_warning": solution.get("warning"),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    classes_parser = subparsers.add_parser("classes")
    classes_parser.add_argument("--output", type=Path, required=True)
    orbit_parser = subparsers.add_parser("orbit-group")
    orbit_parser.add_argument("--group-index", type=int, required=True)
    orbit_parser.add_argument("--output-directory", type=Path, required=True)
    selection_parser = subparsers.add_parser("heldout-selection")
    selection_parser.add_argument("--output", type=Path, required=True)
    cut_parser = subparsers.add_parser("cut-shard")
    cut_parser.add_argument("--family", choices=("same", "cross"), required=True)
    cut_parser.add_argument("--selection", type=Path, required=True)
    cut_parser.add_argument("--classes", type=Path, required=True)
    cut_parser.add_argument("--shard-index", type=int, required=True)
    cut_parser.add_argument("--shard-count", type=int, required=True)
    cut_parser.add_argument("--output-directory", type=Path, required=True)
    assemble_parser = subparsers.add_parser("assemble-cuts")
    assemble_parser.add_argument("--family", choices=("same", "cross"), required=True)
    assemble_parser.add_argument("--selection", type=Path, required=True)
    assemble_parser.add_argument("--classes", type=Path, required=True)
    assemble_parser.add_argument("--shard-directory", type=Path, required=True)
    assemble_parser.add_argument("--shard-count", type=int, required=True)
    assemble_parser.add_argument("--output", type=Path, required=True)
    rank_parser = subparsers.add_parser("rank")
    rank_parser.add_argument("--classes", type=Path, required=True)
    rank_parser.add_argument("--cross-orbit-directory", type=Path, required=True)
    rank_parser.add_argument("--selection", type=Path)
    rank_parser.add_argument("--same-cut", type=Path)
    rank_parser.add_argument("--cross-cut", type=Path)
    rank_parser.add_argument("--prime", type=int, action="append", default=[])
    rank_parser.add_argument("--exact", action="store_true")
    rank_parser.add_argument("--output", type=Path, required=True)
    solve_parser = subparsers.add_parser("solve-joint")
    solve_parser.add_argument("--classes", type=Path, required=True)
    solve_parser.add_argument("--cross-orbit-directory", type=Path, required=True)
    solve_parser.add_argument("--selection", type=Path, required=True)
    solve_parser.add_argument("--same-cut", type=Path, required=True)
    solve_parser.add_argument("--cross-cut", type=Path, required=True)
    solve_parser.add_argument("--prime", type=int, default=1_000_003)
    solve_parser.add_argument("--output", type=Path, required=True)
    residual_parser = subparsers.add_parser("residual")
    residual_parser.add_argument("--solution", type=Path, required=True)
    residual_parser.add_argument("--workers", type=int, default=8)
    residual_parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if args.command == "classes":
        write_json(args.output, build_classes())
    elif args.command == "orbit-group":
        build_orbit_group(args.group_index, args.output_directory)
    elif args.command == "heldout-selection":
        write_json(args.output, make_heldout_selection())
    elif args.command == "cut-shard":
        build_cut_shard(
            args.family,
            args.selection,
            args.classes,
            args.shard_index,
            args.shard_count,
            args.output_directory,
        )
    elif args.command == "assemble-cuts":
        assemble_cut_matrix(
            args.family,
            args.selection,
            args.classes,
            args.shard_directory,
            args.shard_count,
            args.output,
        )
    elif args.command == "rank":
        primes = args.prime or [1_000_003, 1_000_033]
        write_json(
            args.output,
            build_rank_report(
                args.classes,
                args.cross_orbit_directory,
                args.selection,
                args.same_cut,
                args.cross_cut,
                primes,
                args.exact,
            ),
        )
    elif args.command == "solve-joint":
        write_json(
            args.output,
            solve_joint(
                args.classes,
                args.cross_orbit_directory,
                args.selection,
                args.same_cut,
                args.cross_cut,
                args.prime,
            ),
        )
    elif args.command == "residual":
        write_gzip_json(args.output, complete_residual(args.solution, args.workers))


if __name__ == "__main__":
    main()
