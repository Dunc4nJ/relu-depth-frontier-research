#!/usr/bin/env python3
"""Two-prime Schur/quotient oracle over the frozen G-0057 S1 baseline.

For each prime this executable independently selects a rank-1288 pivot minor
``B = H[R,C]`` of the exact-integer 1,358-column G-0057 baseline.  It solves
the sparse-on-R dual

    B^T w_R = lambda_C

and replays ``w_R^T H[R,:] = lambda`` on every baseline column.  A new
zero-lambda column h is then reduced by

    a = B^-1 h_R,  r = h - H_C a,  delta = -lambda_C a.

For a candidate batch, augmented gain is decided by

    rank([r_1 ... r_k; delta_1 ... delta_k])
      - rank([r_1 ... r_k]),

not by one arbitrary scalar price when a residual is nonzero.  The two primes
remain separate.  Any potent modular circuit is replayed on all 99,858 frozen
hinge rows and is only an exact-Q lift target.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gc
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Any, Sequence

from flint import nmod_mat
import networkx as nx
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0057_SCRIPT = ROOT / "artifacts/math/G-0057/s1_high_active_extension_gate.py"
G0057_REPORT = ROOT / "artifacts/math/G-0057/s1_baseline_gate_v1.json.gz"
G0058_SCRIPT = ROOT / "artifacts/math/G-0058/support8_proper_filtration.py"
G0058_REPORT = ROOT / "artifacts/math/G-0058/support8_proper_filtration_v1.json.gz"
MAX10_CERTIFICATE = (
    ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
)

EXPECTED_G0057_SCRIPT_SHA256 = "2555f4f683f4aee768b337bdb62c8fbf9f569ff6a9bff9f14de368140ea2920d"
EXPECTED_G0057_REPORT_SHA256 = "1e2f992254d977dce0551ff8b003147edf042b07cf5d015477d30594d2027f38"
EXPECTED_G0057_PAYLOAD_SHA256 = "093a80a38c777678ddda0a76184650b75865784eb2eda7a0a91e5c653021af11"
EXPECTED_G0058_SCRIPT_SHA256 = "0de659ebef2dea44bc07c3c5f2fbb5f50c7d50338534bdc0e686d087bd120629"
EXPECTED_G0058_REPORT_SHA256 = "90d801abeb6820a27fe8f181dc35b0cf06ac23dac6a98c2d2bc2548db3397d2f"
EXPECTED_G0058_PAYLOAD_SHA256 = "7d54e8e24529c41ccb463e351312fe618d31ff7283649e3526e1095a83a0deba"
EXPECTED_MAX10_CERTIFICATE_SHA256 = "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
EXPECTED_STREAM_SHA256 = "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
EXPECTED_TERM_ORDER_SEQUENCE_SHA256 = "6b967f3604ef2774ebf2d5c6c1860ea2da5328a77a97673acb2cff9ad16d60f1"
EXPECTED_SORTED_SEQUENCE_SHA256 = "8623fd90b06687da72f1aa012b1ecb94825caeef7f7748b9cfe5c80effd4ddf7"
EXPECTED_BASELINE_MATRIX_SHA256 = "1a2fd2a5fcb702ffe747c9e20f1234d4d43316975eff1b4669337e945f2f467d"
EXPECTED_BASELINE_STREAM_SHA256 = "b24a0a63100839f9661377b5ffa2c266752b139592b13eed27cfb553ffaf6ce8"
EXPECTED_BASELINE_UNION_ROWS_SHA256 = "b5e032829ce5a28ee24eab75a03983593f3eb405812938ba55960a501fa5cd82"

PRIMES = (1_000_003, 1_000_033)
EXPECTED_ROWS = 99_858
EXPECTED_BASELINE_COLUMNS = 1_358
EXPECTED_BASELINE_RANK = 1_288
EXPECTED_BASELINE_NULLITY = 70
EXPECTED_MAX10_TERMS = 402
EXPECTED_MAX10_BLOCK = 328
SINGLE_SEQUENCE = 92_489
DEFAULT_OUTPUT = HERE / "modular_quotient_oracle_v1.json.gz"
SCHEMA = "max11-g0059-modular-schur-quotient-oracle-v1"

Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]


class OracleError(RuntimeError):
    """Fail-closed input, semantic, or algebra error."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def deterministic_scientific_view(value: object) -> object:
    """Remove runtime/resource measurements from the hash-bound projection."""

    dynamic_keys = {"seconds", "wall_seconds", "semantic_seconds", "available_gib"}
    if isinstance(value, dict):
        return {
            key: deterministic_scientific_view(item)
            for key, item in value.items()
            if key not in dynamic_keys
        }
    if isinstance(value, list):
        return [deterministic_scientific_view(item) for item in value]
    return value


def array_sha256(value: np.ndarray, dtype: str = "<u4") -> str:
    return hashlib.sha256(value.astype(dtype, copy=False).tobytes(order="C")).hexdigest()


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise OracleError(f"top-level object required: {path}")
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise OracleError(f"bound script drift: {path}: {observed} != {expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise OracleError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def checked_bindings() -> tuple[dict[str, str], dict[str, Any], dict[str, Any]]:
    observed = {
        "g0057_script_sha256": sha256_path(G0057_SCRIPT),
        "g0057_report_sha256": sha256_path(G0057_REPORT),
        "g0058_script_sha256": sha256_path(G0058_SCRIPT),
        "g0058_report_sha256": sha256_path(G0058_REPORT),
        "max10_certificate_sha256": sha256_path(MAX10_CERTIFICATE),
    }
    expected = {
        "g0057_script_sha256": EXPECTED_G0057_SCRIPT_SHA256,
        "g0057_report_sha256": EXPECTED_G0057_REPORT_SHA256,
        "g0058_script_sha256": EXPECTED_G0058_SCRIPT_SHA256,
        "g0058_report_sha256": EXPECTED_G0058_REPORT_SHA256,
        "max10_certificate_sha256": EXPECTED_MAX10_CERTIFICATE_SHA256,
    }
    if observed != expected:
        raise OracleError(f"input binding drift: observed={observed}, expected={expected}")
    g0057 = load_json_gz(G0057_REPORT)
    g0058 = load_json_gz(G0058_REPORT)
    if g0057.get("canonical_scientific_payload_sha256") != EXPECTED_G0057_PAYLOAD_SHA256:
        raise OracleError("G-0057 scientific payload drift")
    if g0058.get("canonical_payload_sha256") != EXPECTED_G0058_PAYLOAD_SHA256:
        raise OracleError("G-0058 payload drift")
    return observed, g0057, g0058


def normalize_edge(edge: Sequence[int]) -> tuple[int, int]:
    if len(edge) != 2:
        raise OracleError(f"malformed edge: {edge}")
    a, b = map(int, edge)
    return (a, b) if a <= b else (b, a)


def cancel_common_edges(raw_pair: Sequence[Sequence[Sequence[int]]]) -> Pair:
    if len(raw_pair) != 2:
        raise OracleError("pair must have two branches")
    left = Counter(normalize_edge(edge) for edge in raw_pair[0])
    right = Counter(normalize_edge(edge) for edge in raw_pair[1])
    common = left & right
    left -= common
    right -= common
    return tuple(sorted(left.elements())), tuple(sorted(right.elements()))


def compact_pair(pair: Pair) -> Pair:
    used = sorted({vertex for side in pair for edge in side for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    return tuple(
        tuple((relabel[a], relabel[b]) for a, b in side) for side in pair
    )  # type: ignore[return-value]


def incidence_data(pair: Pair) -> tuple[dict[int, set[int]], list[set[int]]]:
    active = sorted({vertex for side in pair for edge in side for vertex in edge})
    coordinates = {vertex: index for index, vertex in enumerate(active)}
    coordinate_count = len(active)
    edge_count = sum(map(len, pair))
    total = coordinate_count + 2 + edge_count
    adjacency = {index: set() for index in range(total)}
    edge_node = coordinate_count + 2
    for colour, side in enumerate(pair):
        colour_node = coordinate_count + colour
        for a, b in side:
            # A loop has one coordinate neighbour; parallel occurrences remain
            # distinct edge nodes.  The same-typed colour nodes may globally swap.
            for neighbour in {colour_node, coordinates[a], coordinates[b]}:
                adjacency[edge_node].add(neighbour)
                adjacency[neighbour].add(edge_node)
            edge_node += 1
    colouring = [
        set(range(coordinate_count)),
        set(range(coordinate_count, coordinate_count + 2)),
        set(range(coordinate_count + 2, total)),
    ]
    return adjacency, colouring


def incidence_certificate(pair: Pair) -> bytes:
    adjacency, colouring = incidence_data(pair)
    graph = pynauty.Graph(
        len(adjacency), adjacency_dict=adjacency, vertex_coloring=colouring
    )
    return pynauty.certificate(graph)


def incidence_graph(pair: Pair) -> nx.Graph:
    adjacency, colouring = incidence_data(pair)
    kind_by_node: dict[int, str] = {}
    for kind, nodes in zip(("coordinate", "colour", "edge"), colouring, strict=True):
        for node in nodes:
            kind_by_node[node] = kind
    graph = nx.Graph()
    for node, neighbours in adjacency.items():
        graph.add_node(node, kind=kind_by_node[node])
        for neighbour in neighbours:
            graph.add_edge(node, neighbour)
    return graph


def pair_from_record(record: dict[str, Any]) -> Pair:
    return (
        tuple(normalize_edge(edge) for edge in record["negative_edges"]),
        tuple(normalize_edge(edge) for edge in record["positive_edges"]),
    )


def reconstruct_max10_block(theorem: ModuleType) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    certificate = json.loads(MAX10_CERTIFICATE.read_text(encoding="utf-8"))
    terms = certificate.get("terms")
    if certificate.get("n") != 10 or not isinstance(terms, list) or len(terms) != EXPECTED_MAX10_TERMS:
        raise OracleError("MAX10 certificate schema/census drift")

    retained: list[dict[str, Any]] = []
    cancelled_mass_histogram: Counter[int] = Counter()
    for term_index, term in enumerate(terms):
        pair = cancel_common_edges(term["pair"])
        if len(pair[0]) != len(pair[1]):
            raise OracleError(f"unbalanced cancellation at MAX10 term {term_index}")
        signed_mass = len(pair[0])
        cancelled_mass_histogram[signed_mass] += 1
        if signed_mass != 4:
            continue
        compact = compact_pair(pair)
        active = len({vertex for side in compact for edge in side for vertex in edge})
        retained.append(
            {
                "term_index": term_index,
                "coefficient": str(term["coefficient"]),
                "pair": compact,
                "active_vertices": active,
                "incidence_certificate": incidence_certificate(compact),
            }
        )
    certificates = [item["incidence_certificate"] for item in retained]
    active_histogram = Counter(int(item["active_vertices"]) for item in retained)
    if (
        len(retained) != EXPECTED_MAX10_BLOCK
        or len(set(certificates)) != EXPECTED_MAX10_BLOCK
        or active_histogram != Counter({8: 10, 9: 44, 10: 274})
    ):
        raise OracleError(
            f"MAX10 retained quotient drift: count={len(retained)}, "
            f"unique={len(set(certificates))}, active={active_histogram}"
        )

    needed = set(certificates)
    matches: dict[bytes, dict[str, Any]] = {}
    mass4_count = 0
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header" or sha256_path(theorem.SIGNED_STREAM) != EXPECTED_STREAM_SHA256:
            raise OracleError("G-0038 signed stream binding/header drift")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass < 4:
                continue
            if signed_mass > 4:
                break
            mass4_count += 1
            if int(record["active_vertices"]) not in (8, 9, 10):
                continue
            key = incidence_certificate(pair_from_record(record))
            if key in needed:
                if key in matches:
                    raise OracleError("G-0038 orbit stream contains duplicate incidence class")
                matches[key] = record
    if mass4_count != 134_193 or set(matches) != needed:
        raise OracleError(f"G-0038 mass4 lookup drift: census={mass4_count}, matches={len(matches)}")

    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    sequences: list[int] = []
    records: list[dict[str, Any]] = []
    vf2_checks = 0
    manifest: list[dict[str, Any]] = []
    for item in retained:
        match = matches[item["incidence_certificate"]]
        if not nx.is_isomorphic(
            incidence_graph(item["pair"]),
            incidence_graph(pair_from_record(match)),
            node_match=node_match,
        ):
            raise OracleError(f"pynauty/VF2 disagreement at term {item['term_index']}")
        vf2_checks += 1
        sequence = int(match["sequence"])
        sequences.append(sequence)
        records.append(match)
        manifest.append(
            {
                "block_position": len(manifest),
                "certificate_term_index": int(item["term_index"]),
                "source_coefficient": item["coefficient"],
                "active_vertices": int(item["active_vertices"]),
                "g0038_sequence": sequence,
                "incidence_certificate_sha256": hashlib.sha256(
                    item["incidence_certificate"]
                ).hexdigest(),
            }
        )
    if (
        len(set(sequences)) != EXPECTED_MAX10_BLOCK
        or min(sequences) != 114_832
        or max(sequences) != 136_009
        or SINGLE_SEQUENCE in sequences
        or canonical_sha256(sequences) != EXPECTED_TERM_ORDER_SEQUENCE_SHA256
        or canonical_sha256(sorted(sequences)) != EXPECTED_SORTED_SEQUENCE_SHA256
    ):
        raise OracleError("MAX10-to-G0038 sequence manifest drift")
    metadata = {
        "source_term_count": len(terms),
        "multiset_cancellation_signed_mass_histogram": {
            str(key): value for key, value in sorted(cancelled_mass_histogram.items())
        },
        "retained_signed_mass4_term_count": len(retained),
        "quotient_class_count": len(set(certificates)),
        "active_vertex_histogram": {
            str(key): value for key, value in sorted(active_histogram.items())
        },
        "equivalence": "coordinate isomorphism and one global branch swap via typed incidence graph",
        "pynauty_canonical_certificates_all_unique": True,
        "networkx_VF2_matches_replayed": vf2_checks,
        "g0038_unique_orbit_lookups": len(matches),
        "term_order_sequence_sha256": canonical_sha256(sequences),
        "sorted_sequence_sha256": canonical_sha256(sorted(sequences)),
        "sequence_minimum": min(sequences),
        "sequence_maximum": max(sequences),
        "sequence_92489_absent": SINGLE_SEQUENCE not in sequences,
        "manifest": manifest,
        "manifest_sha256": canonical_sha256(manifest),
    }
    return records, metadata


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.int64)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def from_nmod(matrix: nmod_mat) -> np.ndarray:
    return np.asarray(matrix.tolist(), dtype=np.int64)


def pivot_columns(rref: nmod_mat, rank: int, column_count: int) -> list[int]:
    pivots: list[int] = []
    column = 0
    for row in range(rank):
        while column < column_count and not rref[row, column]:
            column += 1
        if column == column_count:
            raise OracleError("RREF pivot extraction exhausted columns")
        pivots.append(column)
        column += 1
    return pivots


def sparse_kernel_payload(
    kernel: nmod_mat,
    nullity: int,
    prime: int,
    pivot_columns_selected: list[int],
) -> list[dict[str, Any]]:
    pivot_set = set(pivot_columns_selected)
    nonpivot_columns = [
        column for column in range(kernel.nrows()) if column not in pivot_set
    ]
    if len(nonpivot_columns) != nullity:
        raise OracleError("kernel nonpivot census drift")
    vectors: list[dict[str, Any]] = []
    for basis_column in range(nullity):
        distinguished = nonpivot_columns[basis_column]
        distinguished_value = int(kernel[distinguished, basis_column]) % prime
        if not distinguished_value:
            raise OracleError(
                f"zero distinguished free coordinate at kernel vector {basis_column}"
            )
        scale = pow(distinguished_value, -1, prime)
        support = [
            [row, int(kernel[row, basis_column]) * scale % prime]
            for row in range(kernel.nrows())
            if int(kernel[row, basis_column]) % prime
        ]
        nonpivot_support = [column for column, _value in support if column in nonpivot_columns]
        if nonpivot_support != [distinguished] or dict(support)[distinguished] != 1:
            raise OracleError(
                f"free-coordinate normalization drift at kernel vector {basis_column}"
            )
        vectors.append(
            {
                "basis_column": basis_column,
                "distinguished_nonpivot_column": distinguished,
                "support": support,
                "support_indices_sha256": canonical_sha256([item[0] for item in support]),
                "sparse_vector_sha256": canonical_sha256(support),
            }
        )
    return vectors


def rank_profile(matrix: np.ndarray, prime: int) -> dict[str, Any]:
    started = time.perf_counter()
    field = to_nmod(matrix, prime)
    rref, rank_object = field.rref()
    rank = int(rank_object)
    columns = pivot_columns(rref, rank, matrix.shape[1])
    del rref
    kernel, nullity_object = field.nullspace()
    nullity = int(nullity_object)
    kernel_payload = sparse_kernel_payload(kernel, nullity, prime, columns)
    normalized_kernel = np.zeros((matrix.shape[1], nullity), dtype=np.int64)
    for basis_column, item in enumerate(kernel_payload):
        for row, coefficient in item["support"]:
            normalized_kernel[int(row), basis_column] = int(coefficient)
    kernel_replay = field * to_nmod(normalized_kernel, prime)
    if any(
        int(kernel_replay[row, column]) % prime
        for row in range(kernel_replay.nrows())
        for column in range(kernel_replay.ncols())
    ):
        raise OracleError(f"normalized baseline kernel replay failed at {prime}")
    distinguished = [
        int(item["distinguished_nonpivot_column"]) for item in kernel_payload
    ]
    if len(set(distinguished)) != nullity:
        raise OracleError(f"distinguished free coordinates are not unique at {prime}")
    normalized_kernel_sha256 = array_sha256(normalized_kernel)
    del kernel_replay, normalized_kernel, kernel, field
    gc.collect()
    if rank != EXPECTED_BASELINE_RANK or nullity != EXPECTED_BASELINE_NULLITY:
        raise OracleError(f"baseline rank/nullity drift at {prime}: {rank}/{nullity}")

    column_basis_transpose = to_nmod(matrix[:, columns].T, prime)
    transposed_rref, row_rank_object = column_basis_transpose.rref()
    row_rank = int(row_rank_object)
    rows = pivot_columns(transposed_rref, row_rank, matrix.shape[0])
    del transposed_rref, column_basis_transpose
    gc.collect()
    if row_rank != rank:
        raise OracleError(f"row/column rank disagreement at {prime}")
    return {
        "prime": prime,
        "rank": rank,
        "nullity": nullity,
        "pivot_columns": columns,
        "pivot_columns_sha256": canonical_sha256(columns),
        "pivot_union_row_positions": rows,
        "pivot_union_row_positions_sha256": canonical_sha256(rows),
        "kernel_basis": kernel_payload,
        "kernel_support_manifest_sha256": canonical_sha256(
            [item["support_indices_sha256"] for item in kernel_payload]
        ),
        "kernel_sparse_manifest_sha256": canonical_sha256(
            [item["sparse_vector_sha256"] for item in kernel_payload]
        ),
        "distinguished_nonpivot_columns": distinguished,
        "distinguished_nonpivot_columns_sha256": canonical_sha256(distinguished),
        "normalized_kernel_matrix_sha256": normalized_kernel_sha256,
        "all_70_normalized_kernel_vectors_replay_to_zero": True,
        "each_vector_has_one_distinct_free_coordinate_equal_to_one": True,
        "seconds": time.perf_counter() - started,
    }


def rank_record(residual: np.ndarray, delta: np.ndarray, prime: int, prefix: int) -> dict[str, Any]:
    if not (1 <= prefix <= residual.shape[1]) or delta.shape != (residual.shape[1],):
        raise OracleError("malformed quotient prefix")
    started = time.perf_counter()
    # Transposition keeps the same rank while exposing only `prefix` rows to RREF.
    base = np.ascontiguousarray(residual[:, :prefix].T, dtype=np.int64)
    augmented = np.ascontiguousarray(
        np.column_stack((base, np.remainder(delta[:prefix], prime))), dtype=np.int64
    )
    rank = int(to_nmod(base, prime).rank())
    augmented_rank = int(to_nmod(augmented, prime).rank())
    gain = augmented_rank - rank
    if gain not in (0, 1):
        raise OracleError(f"invalid quotient augmented gain {gain}")
    return {
        "prefix": prefix,
        "rank_residual": rank,
        "rank_residual_plus_delta": augmented_rank,
        "augmented_gain": gain,
        "seconds": time.perf_counter() - started,
    }


def first_gain_prefix(residual: np.ndarray, delta: np.ndarray, prime: int) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    cache: dict[int, dict[str, Any]] = {}

    def query(prefix: int) -> dict[str, Any]:
        if prefix not in cache:
            cache[prefix] = rank_record(residual, delta, prime, prefix)
        return cache[prefix]

    full = query(residual.shape[1])
    if not int(full["augmented_gain"]):
        return full, [cache[key] for key in sorted(cache)]
    low, high = 1, residual.shape[1]
    while low < high:
        middle = (low + high) // 2
        if int(query(middle)["augmented_gain"]):
            high = middle
        else:
            low = middle + 1
    first = query(low)
    if low > 1 and int(query(low - 1)["augmented_gain"]):
        raise OracleError("binary-search monotonicity replay failed")
    return first, [cache[key] for key in sorted(cache)]


def quotient_potent_vector(
    residual: np.ndarray, delta: np.ndarray, prime: int, prefix: int
) -> tuple[np.ndarray, dict[str, Any]]:
    field = to_nmod(residual[:, :prefix], prime)
    rank = int(field.rank())
    kernel, nullity_object = field.nullspace()
    nullity = int(nullity_object)
    if nullity != prefix - rank:
        raise OracleError("quotient nullity drift")
    for basis_column in range(nullity):
        vector = np.fromiter(
            (int(kernel[row, basis_column]) % prime for row in range(prefix)),
            dtype=np.int64,
            count=prefix,
        )
        potency = int(np.remainder(delta[:prefix] @ vector, prime))
        if potency:
            vector = np.remainder(vector * pow(potency, -1, prime), prime).astype(np.int64)
            if np.any(np.remainder(residual[:, :prefix] @ vector, prime)):
                raise OracleError("quotient potent vector residual replay failed")
            if int(np.remainder(delta[:prefix] @ vector, prime)) != 1:
                raise OracleError("quotient potent vector normalization failed")
            support = [[index, int(value)] for index, value in enumerate(vector) if value]
            del kernel, field
            return vector, {
                "quotient_rank": rank,
                "quotient_nullity": nullity,
                "kernel_basis_column_used": basis_column,
                "normalization": "delta_dot_candidate_coefficients_mod_prime_equals_one",
                "support": support,
                "support_sha256": canonical_sha256(support),
            }
    raise OracleError("augmented gain had no potent quotient null vector")


def build_candidate_matrix(
    baseline_union_rows: np.ndarray,
    candidate_results: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    candidate_rows = np.unique(
        np.concatenate([result["rows"] for result in candidate_results])
    ).astype(np.uint32, copy=False)
    combined_rows = np.union1d(baseline_union_rows, candidate_rows).astype(np.uint32, copy=False)
    positions = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    positions[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    candidate_matrix = np.zeros((len(combined_rows), len(candidate_results)), dtype=np.int64)
    for column, result in enumerate(candidate_results):
        local = positions[result["rows"]]
        if np.any(local < 0):
            raise OracleError("candidate escaped combined union")
        candidate_matrix[local, column] = result["values"]
    baseline_positions = positions[baseline_union_rows]
    if np.any(baseline_positions < 0):
        raise OracleError("baseline union escaped combined union")
    metadata = {
        "combined_union_row_count": len(combined_rows),
        "combined_union_row_indices_sha256": array_sha256(combined_rows),
        "candidate_matrix_shape": list(candidate_matrix.shape),
        "candidate_matrix_sha256": hashlib.sha256(
            candidate_matrix.astype("<i8", copy=False).tobytes(order="C")
        ).hexdigest(),
        "candidate_total_nonzeros": int(np.count_nonzero(candidate_matrix)),
    }
    return combined_rows, baseline_positions, candidate_matrix, metadata


def analyze_prime(
    prime: int,
    profile: dict[str, Any],
    baseline_union_rows: np.ndarray,
    baseline_matrix: np.ndarray,
    lambda_row: np.ndarray,
    combined_rows: np.ndarray,
    baseline_positions: np.ndarray,
    candidate_matrix: np.ndarray,
    baseline_results: list[dict[str, Any]],
    candidate_results: list[dict[str, Any]],
    g0057: ModuleType,
) -> dict[str, Any]:
    started = time.perf_counter()
    if (
        len(candidate_results) != EXPECTED_MAX10_BLOCK + 1
        or int(candidate_results[0]["sequence"]) != SINGLE_SEQUENCE
    ):
        raise OracleError("joint candidate order/census drift")
    block_results = candidate_results[1:]
    columns = list(map(int, profile["pivot_columns"]))
    row_positions = list(map(int, profile["pivot_union_row_positions"]))
    complete_pivot_rows = baseline_union_rows[row_positions].astype(np.uint32, copy=False)
    minor = np.ascontiguousarray(baseline_matrix[np.ix_(row_positions, columns)], dtype=np.int64)
    minor_field = to_nmod(minor, prime)
    determinant = int(minor_field.det())
    if not determinant:
        raise OracleError(f"singular selected pivot minor at {prime}")

    lambda_c = np.remainder(lambda_row[columns], prime).astype(np.int64, copy=False)
    dual_rhs = to_nmod(lambda_c.reshape(-1, 1), prime)
    dual_field = minor_field.transpose().solve(dual_rhs)
    dual = from_nmod(dual_field).reshape(-1)
    baseline_on_rows = np.ascontiguousarray(baseline_matrix[row_positions, :], dtype=np.int64)
    dual_replay = from_nmod(
        to_nmod(dual.reshape(1, -1), prime) * to_nmod(baseline_on_rows, prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_replay - lambda_row, prime)):
        first = int(np.flatnonzero(np.remainder(dual_replay - lambda_row, prime))[0])
        raise OracleError(f"sparse dual replay failed at {prime}, column {first}")

    complete_to_combined = np.full(EXPECTED_ROWS, -1, dtype=np.int32)
    complete_to_combined[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    pivot_combined_positions = complete_to_combined[complete_pivot_rows]
    candidate_on_rows = np.ascontiguousarray(candidate_matrix[pivot_combined_positions, :], dtype=np.int64)
    coefficients_field = minor_field.solve(to_nmod(candidate_on_rows, prime))
    coefficients = from_nmod(coefficients_field)
    if np.any(
        np.remainder(
            from_nmod(minor_field * coefficients_field) - candidate_on_rows,
            prime,
        )
    ):
        raise OracleError(f"B^-1 candidate solve replay failed at {prime}")

    basis_on_combined = np.zeros((len(combined_rows), len(columns)), dtype=np.int64)
    basis_on_combined[baseline_positions, :] = baseline_matrix[:, columns]
    predicted_field = to_nmod(basis_on_combined, prime) * coefficients_field
    predicted = from_nmod(predicted_field)
    residual = np.remainder(candidate_matrix - predicted, prime).astype(np.int64, copy=False)
    if np.any(residual[pivot_combined_positions, :]):
        raise OracleError(f"Schur residual nonzero on pivot rows at {prime}")
    delta = np.remainder(
        -np.remainder(lambda_c @ coefficients, prime), prime
    ).astype(np.int64, copy=False)
    dual_prices = np.remainder(
        dual @ np.remainder(candidate_on_rows, prime), prime
    ).astype(np.int64, copy=False)
    if np.any(np.remainder(dual_prices + delta, prime)):
        raise OracleError(f"dual-price/delta bridge failed at {prime}")

    single_record = rank_record(residual[:, :1], delta[:1], prime, 1)
    single_record.update(
        {
            "sequence": SINGLE_SEQUENCE,
            "dual_price_mod_prime": int(dual_prices[0]),
            "delta_mod_prime": int(delta[0]),
            "residual_support_size": int(np.count_nonzero(residual[:, 0])),
            "residual_sha256": array_sha256(residual[:, 0]),
            "single_price_is_decisive": bool(not np.any(residual[:, 0])),
        }
    )

    block_residual = residual[:, 1:]
    block_delta = delta[1:]
    first_record, prefix_queries = first_gain_prefix(block_residual, block_delta, prime)
    full_record = next(
        item for item in prefix_queries if int(item["prefix"]) == EXPECTED_MAX10_BLOCK
    )
    def lift_potent_circuit(
        family_residual: np.ndarray,
        family_delta: np.ndarray,
        family_coefficients: np.ndarray,
        family_results: list[dict[str, Any]],
        first_prefix: int,
        family_order: str,
    ) -> dict[str, Any]:
        candidate_coefficients, quotient_witness = quotient_potent_vector(
            family_residual, family_delta, prime, first_prefix
        )
        baseline_pivot_coefficients = np.remainder(
            -(family_coefficients[:, :first_prefix] @ candidate_coefficients), prime
        ).astype(np.int64, copy=False)
        full_coefficients = [0] * (EXPECTED_BASELINE_COLUMNS + first_prefix)
        for position, column in enumerate(columns):
            full_coefficients[column] = int(baseline_pivot_coefficients[position])
        for position, value in enumerate(candidate_coefficients):
            full_coefficients[EXPECTED_BASELINE_COLUMNS + position] = int(value)
        witness_results = baseline_results + family_results[:first_prefix]
        full_replay = g0057.replay_witness(witness_results, full_coefficients, prime)
        return {
            "family_order": family_order,
            "first_gain_prefix": first_prefix,
            "last_added_family_position": first_prefix - 1,
            "last_added_sequence": int(family_results[first_prefix - 1]["sequence"]),
            "quotient_witness": quotient_witness,
            "baseline_pivot_coefficients": baseline_pivot_coefficients.astype(int).tolist(),
            "baseline_pivot_coefficients_sha256": canonical_sha256(
                baseline_pivot_coefficients.astype(int).tolist()
            ),
            "candidate_coefficients": candidate_coefficients.astype(int).tolist(),
            "candidate_coefficients_sha256": canonical_sha256(
                candidate_coefficients.astype(int).tolist()
            ),
            "full_99858_row_replay": full_replay,
        }

    potent_circuit = None
    if int(full_record["augmented_gain"]):
        potent_circuit = lift_potent_circuit(
            block_residual,
            block_delta,
            coefficients[:, 1:],
            block_results,
            int(first_record["prefix"]),
            "328 MAX10-induced atoms in original certificate-term order",
        )

    joint_first_record, joint_prefix_queries = first_gain_prefix(residual, delta, prime)
    joint_full_record = next(
        item
        for item in joint_prefix_queries
        if int(item["prefix"]) == EXPECTED_MAX10_BLOCK + 1
    )
    joint_potent_circuit = None
    if int(joint_full_record["augmented_gain"]):
        joint_potent_circuit = lift_potent_circuit(
            residual,
            delta,
            coefficients,
            candidate_results,
            int(joint_first_record["prefix"]),
            "sequence 92489 first, then 328 MAX10-induced atoms in original certificate-term order",
        )

    residual_columns = []
    for index in range(residual.shape[1]):
        column = residual[:, index]
        residual_columns.append(
            {
                "candidate_position": index,
                "sequence": int((block_results[index - 1] if index else {"sequence": SINGLE_SEQUENCE})["sequence"]),
                "support_size": int(np.count_nonzero(column)),
                "residual_sha256": array_sha256(column),
                "delta_mod_prime": int(delta[index]),
                "dual_price_mod_prime": int(dual_prices[index]),
            }
        )

    result = {
        "prime": prime,
        "baseline_rank": int(profile["rank"]),
        "baseline_nullity": int(profile["nullity"]),
        "pivot_minor": {
            "rank": len(columns),
            "pivot_columns": columns,
            "pivot_columns_sha256": canonical_sha256(columns),
            "pivot_complete_rows": complete_pivot_rows.astype(int).tolist(),
            "pivot_complete_rows_sha256": canonical_sha256(
                complete_pivot_rows.astype(int).tolist()
            ),
            "determinant_mod_prime": determinant,
            "minor_int64_sha256": hashlib.sha256(
                minor.astype("<i8", copy=False).tobytes(order="C")
            ).hexdigest(),
        },
        "sparse_on_pivot_rows_dual": {
            "weights_mod_prime": dual.astype(int).tolist(),
            "weights_sha256": canonical_sha256(dual.astype(int).tolist()),
            "all_1358_baseline_columns_replayed": True,
            "support_is_exactly_selected_pivot_rows": True,
        },
        "candidate_schur_coefficients": {
            "shape": list(coefficients.shape),
            "candidate_major_mod_prime": coefficients.T.astype(int).tolist(),
            "candidate_major_sha256": canonical_sha256(coefficients.T.astype(int).tolist()),
            "all_B_times_a_equal_h_R": True,
        },
        "single_sequence_92489": single_record,
        "max10_induced_block": {
            "column_count": EXPECTED_MAX10_BLOCK,
            "full_prefix": full_record,
            "first_gain_prefix": (
                int(first_record["prefix"]) if int(full_record["augmented_gain"]) else None
            ),
            "binary_search_rank_queries": prefix_queries,
            "residual_matrix_shape": list(block_residual.shape),
            "residual_matrix_sha256": array_sha256(block_residual),
            "delta_sha256": array_sha256(block_delta),
            "potent_circuit": potent_circuit,
        },
        "joint_sequence_92489_plus_max10_block": {
            "column_count": EXPECTED_MAX10_BLOCK + 1,
            "ordered_composition": [
                {"position": 0, "sequence": SINGLE_SEQUENCE},
                {
                    "positions": [1, EXPECTED_MAX10_BLOCK],
                    "family": "MAX10-induced atoms in original certificate-term order",
                },
            ],
            "full_prefix": joint_full_record,
            "first_gain_prefix": (
                int(joint_first_record["prefix"])
                if int(joint_full_record["augmented_gain"])
                else None
            ),
            "binary_search_rank_queries": joint_prefix_queries,
            "residual_matrix_shape": list(residual.shape),
            "residual_matrix_sha256": array_sha256(residual),
            "delta_sha256": array_sha256(delta),
            "potent_circuit": joint_potent_circuit,
        },
        "all_candidate_residual_columns": residual_columns,
        "all_residuals_zero_on_pivot_rows": True,
        "all_dual_prices_equal_negative_delta": True,
        "seconds": time.perf_counter() - started,
    }
    del predicted, predicted_field, residual, basis_on_combined, coefficients_field
    gc.collect()
    return result


def synthetic_schur_controls() -> dict[str, Any]:
    # Nonzero residual makes a nonzero scalar price non-decisive.
    residual = np.array([[1]], dtype=np.int64)
    delta = np.array([1], dtype=np.int64)
    nondecisive = rank_record(residual, delta, PRIMES[0], 1)
    if int(nondecisive["augmented_gain"]):
        raise OracleError("synthetic nondecisive-price control failed")
    # Two equal residuals with unequal deltas create a potent quotient circuit,
    # even though each singleton separately has zero augmented gain.  This is
    # the direct regression control for accidentally omitting a joint-family gate.
    residual = np.array([[1, 1], [0, 0]], dtype=np.int64)
    delta = np.array([0, 1], dtype=np.int64)
    singleton_left = rank_record(residual[:, :1], delta[:1], PRIMES[0], 1)
    singleton_right = rank_record(residual[:, 1:], delta[1:], PRIMES[0], 1)
    decisive = rank_record(residual, delta, PRIMES[0], 2)
    vector, witness = quotient_potent_vector(residual, delta, PRIMES[0], 2)
    if (
        int(singleton_left["augmented_gain"])
        or int(singleton_right["augmented_gain"])
        or int(decisive["augmented_gain"]) != 1
        or len(np.flatnonzero(vector)) != 2
    ):
        raise OracleError("synthetic potent-circuit control failed")
    return {
        "nonzero_price_with_nonzero_residual_has_no_gain": nondecisive,
        "joint_regression_left_singleton_has_no_gain": singleton_left,
        "joint_regression_right_singleton_has_no_gain": singleton_right,
        "two_column_potent_circuit_has_gain": decisive,
        "potent_circuit_replayed": witness,
        "passed": True,
    }


def prepare_semantics(
    g0057: ModuleType,
    g0057_report: dict[str, Any],
    g0058_report: dict[str, Any],
    workers: int,
) -> tuple[
    tuple[tuple[int, ...], ...],
    list[dict[str, Any]],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
    dict[str, Any],
]:
    g0057.G0054 = g0057.import_bound(
        "g0059_g0054", g0057.G0054_SCRIPT, g0057.EXPECTED_G0054_SCRIPT_SHA256
    )
    g0057.THEOREM = g0057.G0054.load_theorem("g0059_theorem")
    universe = g0057.G0054.direction_universe()
    if len(universe) != EXPECTED_ROWS:
        raise OracleError("complete direction universe census drift")
    g0057.ROW_INDEX = {direction: index for index, direction in enumerate(universe)}

    block_records, block_metadata = reconstruct_max10_block(g0057.THEOREM)
    (
        s0_sequences,
        proper_indices,
        seed_indices,
        selected_candidates,
        _prices,
        exact_manifest,
        _manifest_metadata,
    ) = g0057.load_frozen_manifests("baseline-only")
    if selected_candidates:
        raise OracleError("G-0057 baseline-only unexpectedly selected candidates")
    g0050 = g0057.import_bound(
        "g0059_g0050", g0057.G0050_SCRIPT, g0057.EXPECTED_G0050_SCRIPT_SHA256
    )
    extract = g0050.import_extract()
    search = extract.load_search()
    lowmass_records = search.load_records(search.load_g47())
    if len(lowmass_records) != 3_310:
        raise OracleError("low-mass record census drift")

    needed_mass4 = set(s0_sequences) | {SINGLE_SEQUENCE} | {
        int(record["sequence"]) for record in block_records
    }
    mass4_records = g0057.read_mass4_records(g0057.THEOREM, needed_mass4)
    payloads: list[tuple[int, str, int, dict[str, Any]]] = []
    for pivot_position, sequence in enumerate(s0_sequences):
        payloads.append(
            (len(payloads), "s0_mass4_pivot", pivot_position, mass4_records[sequence])
        )
    for column_index in proper_indices:
        payloads.append(
            (len(payloads), "lowmass_proper_basis", column_index, lowmass_records[column_index])
        )
    for column_index in seed_indices:
        payloads.append(
            (len(payloads), "lowmass_full_seed", column_index, lowmass_records[column_index])
        )
    if len(payloads) != EXPECTED_BASELINE_COLUMNS:
        raise OracleError("baseline payload census drift")
    payloads.append(
        (len(payloads), "g0059_single_support8", SINGLE_SEQUENCE, mass4_records[SINGLE_SEQUENCE])
    )
    for block_position, record in enumerate(block_records):
        payloads.append(
            (len(payloads), "g0059_max10_induced_mass4", block_position, record)
        )

    results, semantic_seconds = g0057.generate_semantics(
        payloads, g0057.ROW_INDEX, workers, "G0059_SEMANTIC"
    )
    baseline_results = results[:EXPECTED_BASELINE_COLUMNS]
    candidate_results = results[EXPECTED_BASELINE_COLUMNS:]
    block_results = candidate_results[1:]
    exact_s0_check = g0057.verify_exact_s0_basis_semantics(
        baseline_results[: g0057.EXPECTED_S0_PIVOTS], exact_manifest
    )
    lowmass_check = g0057.verify_lowmass_semantics_independently(
        search,
        [lowmass_records[index] for index in proper_indices + seed_indices],
        baseline_results[g0057.EXPECTED_S0_PIVOTS :],
        g0057.ROW_INDEX,
        workers,
    )
    if any(int(result["lambda"]) for result in candidate_results):
        raise OracleError("proper candidate has nonzero lambda")
    if [int(result["sequence"]) for result in block_results] != [
        int(record["sequence"]) for record in block_records
    ]:
        raise OracleError("MAX10 block semantic order drift")

    baseline_union_rows, baseline_matrix, lambda_row, baseline_metadata = (
        g0057.build_union_matrix(universe, baseline_results)
    )
    expected_union = g0057_report["complete_integer_semantics"]["exact_union"]
    if (
        baseline_metadata["matrix_sha256"] != EXPECTED_BASELINE_MATRIX_SHA256
        or baseline_metadata["union_row_indices_sha256"] != EXPECTED_BASELINE_UNION_ROWS_SHA256
        or g0057.ordered_sparse_stream_hash(baseline_results) != EXPECTED_BASELINE_STREAM_SHA256
        or baseline_metadata != expected_union
    ):
        raise OracleError("regenerated baseline differs from frozen G-0057 report")

    single = candidate_results[0]
    expected_support8 = set(
        index
        for index, direction in enumerate(universe)
        if sum(value != 0 for value in direction) == 8
        and Counter(direction) == Counter({-1: 4, 0: 3, 1: 4})
    )
    if (
        int(single["sequence"]) != SINGLE_SEQUENCE
        or set(map(int, single["rows"])) != expected_support8
        or set(map(int, single["values"])) != {6_912}
        or len(expected_support8) != 3_465
        or g0058_report["controls"]["ambient_coefficient_on_every_support8_row"] != 6_912
    ):
        raise OracleError("sequence 92489 support-eight semantic bridge failed")

    controls = {
        "semantic_seconds": semantic_seconds,
        "exact_s0_basis_crosscheck": exact_s0_check,
        "independent_lowmass_crosscheck": lowmass_check,
        "baseline_matrix_and_union_exactly_match_g0057": True,
        "all_329_proper_candidate_lambdas_zero": True,
        "sequence_92489_is_6912_times_complete_support8_indicator": True,
    }
    return (
        universe,
        baseline_results,
        candidate_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        block_metadata,
        controls,
    )


def run(workers: int, minimum_available_gib: float) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    bindings, g0057_report, g0058_report = checked_bindings()
    g0057 = import_bound("g0059_g0057", G0057_SCRIPT, EXPECTED_G0057_SCRIPT_SHA256)
    preflight = g0057.resource_preflight(minimum_available_gib)
    synthetic = synthetic_schur_controls()
    (
        _universe,
        baseline_results,
        candidate_results,
        baseline_union_rows,
        baseline_matrix,
        lambda_row,
        block_metadata,
        semantic_controls,
    ) = prepare_semantics(g0057, g0057_report, g0058_report, workers)

    profiles = [rank_profile(baseline_matrix, prime) for prime in PRIMES]
    combined_rows, baseline_positions, candidate_matrix, combined_metadata = (
        build_candidate_matrix(baseline_union_rows, candidate_results)
    )
    prime_results = [
        analyze_prime(
            prime,
            profile,
            baseline_union_rows,
            baseline_matrix,
            lambda_row,
            combined_rows,
            baseline_positions,
            candidate_matrix,
            baseline_results,
            candidate_results,
            g0057,
        )
        for prime, profile in zip(PRIMES, profiles, strict=True)
    ]

    pivot_columns_common = profiles[0]["pivot_columns"] == profiles[1]["pivot_columns"]
    pivot_rows_common = (
        profiles[0]["pivot_union_row_positions"]
        == profiles[1]["pivot_union_row_positions"]
    )
    kernel_supports_common = [
        item["support_indices_sha256"] for item in profiles[0]["kernel_basis"]
    ] == [item["support_indices_sha256"] for item in profiles[1]["kernel_basis"]]
    distinguished_common = (
        profiles[0]["distinguished_nonpivot_columns"]
        == profiles[1]["distinguished_nonpivot_columns"]
    )
    aligned_residue_pairs: list[list[int]] = []
    identical_residue_count = 0
    differing_residue_count = 0
    if kernel_supports_common and distinguished_common:
        for left, right in zip(
            profiles[0]["kernel_basis"], profiles[1]["kernel_basis"], strict=True
        ):
            left_support = list(left["support"])
            right_support = list(right["support"])
            if [item[0] for item in left_support] != [item[0] for item in right_support]:
                raise OracleError("cross-prime normalized kernel support alignment drift")
            for (column, left_value), (_right_column, right_value) in zip(
                left_support, right_support, strict=True
            ):
                aligned_residue_pairs.append(
                    [int(column), int(left_value), int(right_value)]
                )
                if int(left_value) == int(right_value):
                    identical_residue_count += 1
                else:
                    differing_residue_count += 1
    block_gains = [
        int(result["max10_induced_block"]["full_prefix"]["augmented_gain"])
        for result in prime_results
    ]
    joint_gains = [
        int(
            result["joint_sequence_92489_plus_max10_block"]["full_prefix"][
                "augmented_gain"
            ]
        )
        for result in prime_results
    ]
    if joint_gains == [1, 1]:
        result_label = "BOTH_PRIMES_JOINT_329_FAMILY_HAS_REPLAYED_QUOTIENT_GAIN"
    elif joint_gains == [0, 0]:
        result_label = "NO_JOINT_329_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME"
    else:
        result_label = "MIXED_PRIME_JOINT_329_QUOTIENT_OUTCOME"

    block_first_gain_prefixes = [
        result["max10_induced_block"]["first_gain_prefix"]
        for result in prime_results
    ]
    joint_first_gain_prefixes = [
        result["joint_sequence_92489_plus_max10_block"]["first_gain_prefix"]
        for result in prime_results
    ]

    cross_prime = {
        "pivot_columns_identical": pivot_columns_common,
        "pivot_complete_rows_identical": pivot_rows_common,
        "kernel_basis_supports_identical_in_order": kernel_supports_common,
        "distinguished_free_coordinates_identical_in_order": distinguished_common,
        "normalized_kernel_value_pairs_compared": len(aligned_residue_pairs),
        "normalized_kernel_identical_residue_count": identical_residue_count,
        "normalized_kernel_differing_residue_count": differing_residue_count,
        "aligned_normalized_kernel_residue_pairs_sha256": (
            canonical_sha256(aligned_residue_pairs)
            if kernel_supports_common and distinguished_common
            else None
        ),
        "common_pivot_columns": profiles[0]["pivot_columns"] if pivot_columns_common else None,
        "common_pivot_complete_rows": (
            baseline_union_rows[profiles[0]["pivot_union_row_positions"]].astype(int).tolist()
            if pivot_rows_common
            else None
        ),
        "common_kernel_support_manifest_sha256": (
            profiles[0]["kernel_support_manifest_sha256"] if kernel_supports_common else None
        ),
        "max10_block_augmented_gains": block_gains,
        "max10_block_first_gain_prefixes": block_first_gain_prefixes,
        "max10_block_first_gain_prefixes_agree_when_both_primes_gain": (
            block_first_gain_prefixes[0] == block_first_gain_prefixes[1]
            if block_gains == [1, 1]
            else None
        ),
        "joint_329_augmented_gains": joint_gains,
        "joint_329_first_gain_prefixes": joint_first_gain_prefixes,
        "joint_329_first_gain_prefixes_agree_when_both_primes_gain": (
            joint_first_gain_prefixes[0] == joint_first_gain_prefixes[1]
            if joint_gains == [1, 1]
            else None
        ),
        "no_exact_Q_inference_from_two_prime_agreement": True,
    }

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": result_label,
        "bindings": bindings,
        "max10_induced_block_reconstruction": block_metadata,
        "baseline": {
            "column_count": EXPECTED_BASELINE_COLUMNS,
            "integer_matrix_shape": list(baseline_matrix.shape),
            "integer_matrix_sha256": EXPECTED_BASELINE_MATRIX_SHA256,
            "union_row_count": len(baseline_union_rows),
            "union_row_indices_sha256": EXPECTED_BASELINE_UNION_ROWS_SHA256,
            "lambda_row_sha256": hashlib.sha256(
                lambda_row.astype("<i8", copy=False).tobytes(order="C")
            ).hexdigest(),
            "per_prime_rank_profiles_and_preserved_nullspaces": profiles,
        },
        "candidate_semantics": {
            "ordered_composition": [
                {"namespace": "single_support8", "count": 1, "sequence": SINGLE_SEQUENCE},
                {"namespace": "max10_induced_mass4", "count": EXPECTED_MAX10_BLOCK},
            ],
            "combined_union": combined_metadata,
            "ordered_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(candidate_results),
        },
        "prime_results": prime_results,
        "cross_prime_comparison": cross_prime,
        "controls": {
            "resource_preflight": preflight,
            "synthetic_schur_controls": synthetic,
            **semantic_controls,
        },
        "epistemic_status": "COMPUTED_BOUNDED_MODULAR_DISCOVERY_GATE",
        "claim_boundary": [
            "All Schur residuals, duals, ranks, deltas, nullspaces, and circuits are finite-field statements at the separately reported primes.",
            "Equal ranks or matching supports at two primes do not establish the rank or kernel over Q; exact reconstruction and integer functional replay remain separate obligations.",
            "A single dual price is decisive only when the full Schur residual is zero; batch gain is rank([R;delta])-rank(R).",
            "The 328-column block consists only of signed-mass-four supports induced by the frozen public MAX10 certificate, not all 132,728 proper mass-four atoms.",
            "Even a lifted circuit in this restricted orbit family would not by itself settle unrestricted arbitrary-real-weight two-hidden-layer MAX11.",
        ],
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "timing": {"wall_seconds": time.perf_counter() - started},
        "script_sha256": script_hash_before,
    }
    scientific_payload = {
        key: report[key]
        for key in (
            "schema",
            "result",
            "bindings",
            "max10_induced_block_reconstruction",
            "baseline",
            "candidate_semantics",
            "prime_results",
            "cross_prime_comparison",
            "controls",
            "epistemic_status",
            "claim_boundary",
        )
    }
    report["canonical_scientific_payload_sha256"] = canonical_sha256(
        deterministic_scientific_view(scientific_payload)
    )
    report["canonical_scientific_payload_projection"] = (
        "recursive report projection excluding seconds, wall_seconds, semantic_seconds, and available_gib"
    )
    if sha256_path(Path(__file__)) != script_hash_before:
        raise OracleError("script changed during execution")
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--minimum-available-gib", type=float, default=16.0)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.self_test:
        checked_bindings()
        controls = synthetic_schur_controls()
        pair = (((0, 0), (1, 2), (2, 3), (3, 3)), ((4, 4), (5, 6), (6, 7), (7, 7)))
        transformed = (
            tuple((9 - b, 9 - a) for a, b in pair[1]),
            tuple((9 - b, 9 - a) for a, b in pair[0]),
        )
        if incidence_certificate(pair) != incidence_certificate(transformed):
            raise OracleError("incidence relabelling/branch-swap self-test failed")
        print(json.dumps({"result": "SELF_TEST_PASS", "controls": controls}, sort_keys=True))
        return
    g0057 = import_bound("g0059_preflight_g0057", G0057_SCRIPT, EXPECTED_G0057_SCRIPT_SHA256)
    if args.preflight_only:
        checked_bindings()
        print(json.dumps(g0057.resource_preflight(args.minimum_available_gib), sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside project") from error
    report = run(args.workers, args.minimum_available_gib)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
