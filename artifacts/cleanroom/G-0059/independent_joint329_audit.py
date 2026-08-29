#!/usr/bin/env python3
"""Clean-room certificate replay for the frozen G-0059 joint-329 gate.

This auditor does not import the G-0059 producer implementation.  It binds the
producer bytes, independently reconstructs the MAX10-induced 328-column order,
regenerates the frozen complete-row semantics through the already-certified
G-0057 semantic kernel, and replays the modular certificates from report data.

For each prime, the baseline rank 1,288 is certified without another baseline
RREF: a reported nonzero 1,288 minor supplies the lower bound, while 70 sparse,
normalized, independently replayed kernel vectors supply the matching upper
bound.  The Schur residual and delta are then rebuilt, and the joint 329-column
and subordinate 328-column ranks are recomputed directly.
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
import sys
from types import ModuleType
from typing import Any, Sequence

from flint import nmod_mat
import networkx as nx
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRODUCER_COMMIT = "0d2d1a4"
PRODUCER_SCRIPT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle.py"
PRODUCER_REPORT = ROOT / "artifacts/math/G-0059/modular_quotient_oracle_v1.json.gz"
G0057_SCRIPT = ROOT / "artifacts/math/G-0057/s1_high_active_extension_gate.py"
G0057_REPORT = ROOT / "artifacts/math/G-0057/s1_baseline_gate_v1.json.gz"
G0058_SCRIPT = ROOT / "artifacts/math/G-0058/support8_proper_filtration.py"
G0058_REPORT = ROOT / "artifacts/math/G-0058/support8_proper_filtration_v1.json.gz"
MAX10_CERTIFICATE = (
    ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
)

EXPECTED_PRODUCER_SCRIPT_SHA256 = (
    "dd743b702a99541e835b52bbdf5ec4c50c9650344bdf2ea0d4f81d22a7678ecd"
)
EXPECTED_PRODUCER_REPORT_SHA256 = (
    "72ade3d6c9c507d6843f161419dc92b7b1273a299a7eff7c9def6a7d3e0ddb37"
)
EXPECTED_PRODUCER_SCIENTIFIC_SHA256 = (
    "9f5d1dfde5a8ccaa4e0e02d98a588e41025c1a973211a7829f14af9ab74c5d6b"
)
EXPECTED_G0057_SCRIPT_SHA256 = (
    "2555f4f683f4aee768b337bdb62c8fbf9f569ff6a9bff9f14de368140ea2920d"
)
EXPECTED_G0057_REPORT_SHA256 = (
    "1e2f992254d977dce0551ff8b003147edf042b07cf5d015477d30594d2027f38"
)
EXPECTED_G0058_SCRIPT_SHA256 = (
    "0de659ebef2dea44bc07c3c5f2fbb5f50c7d50338534bdc0e686d087bd120629"
)
EXPECTED_G0058_REPORT_SHA256 = (
    "90d801abeb6820a27fe8f181dc35b0cf06ac23dac6a98c2d2bc2548db3397d2f"
)
EXPECTED_MAX10_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
EXPECTED_G0038_STREAM_SHA256 = (
    "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd"
)
EXPECTED_TERM_ORDER_SHA256 = (
    "6b967f3604ef2774ebf2d5c6c1860ea2da5328a77a97673acb2cff9ad16d60f1"
)
EXPECTED_SORTED_SEQUENCE_SHA256 = (
    "8623fd90b06687da72f1aa012b1ecb94825caeef7f7748b9cfe5c80effd4ddf7"
)
EXPECTED_BASELINE_MATRIX_SHA256 = (
    "1a2fd2a5fcb702ffe747c9e20f1234d4d43316975eff1b4669337e945f2f467d"
)
EXPECTED_BASELINE_UNION_SHA256 = (
    "b5e032829ce5a28ee24eab75a03983593f3eb405812938ba55960a501fa5cd82"
)

PRIMES = (1_000_003, 1_000_033)
ROW_COUNT = 99_858
BASELINE_COLUMN_COUNT = 1_358
BASELINE_RANK = 1_288
BASELINE_NULLITY = 70
BLOCK_COUNT = 328
JOINT_COUNT = 329
MAX10_TERM_COUNT = 402
SINGLE_SEQUENCE = 92_489
SCHEMA = "max11-g0059-independent-joint329-audit-v1"
DEFAULT_OUTPUT = HERE / "independent_joint329_audit_v1.json.gz"

Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]


class AuditError(RuntimeError):
    """Fail-closed audit error."""


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


def array_sha256(value: np.ndarray, dtype: str = "<u4") -> str:
    return hashlib.sha256(
        value.astype(dtype, copy=False).tobytes(order="C")
    ).hexdigest()


def dense_integer_matrix_sha256(value: np.ndarray) -> str:
    digest = hashlib.sha256()
    digest.update(
        f"int64-little-row-major;shape={value.shape[0]}x{value.shape[1]}\n".encode()
    )
    for start in range(0, value.shape[0], 256):
        digest.update(
            value[start : start + 256]
            .astype("<i8", copy=False)
            .tobytes(order="C")
        )
    return digest.hexdigest()


def load_json_gz(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AuditError(f"expected top-level JSON object: {path}")
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if observed != expected_hash:
        raise AuditError(f"bound script drift: {path}: {observed}/{expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise AuditError(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def deterministic_producer_view(value: object) -> object:
    dynamic = {"seconds", "wall_seconds", "semantic_seconds", "available_gib"}
    if isinstance(value, dict):
        return {
            str(key): deterministic_producer_view(item)
            for key, item in value.items()
            if str(key) not in dynamic
        }
    if isinstance(value, list):
        return [deterministic_producer_view(item) for item in value]
    return value


def verify_producer() -> tuple[dict[str, Any], dict[str, str]]:
    observed = {
        "producer_script_sha256": sha256_path(PRODUCER_SCRIPT),
        "producer_report_sha256": sha256_path(PRODUCER_REPORT),
        "g0057_script_sha256": sha256_path(G0057_SCRIPT),
        "g0057_report_sha256": sha256_path(G0057_REPORT),
        "g0058_script_sha256": sha256_path(G0058_SCRIPT),
        "g0058_report_sha256": sha256_path(G0058_REPORT),
        "max10_certificate_sha256": sha256_path(MAX10_CERTIFICATE),
    }
    expected = {
        "producer_script_sha256": EXPECTED_PRODUCER_SCRIPT_SHA256,
        "producer_report_sha256": EXPECTED_PRODUCER_REPORT_SHA256,
        "g0057_script_sha256": EXPECTED_G0057_SCRIPT_SHA256,
        "g0057_report_sha256": EXPECTED_G0057_REPORT_SHA256,
        "g0058_script_sha256": EXPECTED_G0058_SCRIPT_SHA256,
        "g0058_report_sha256": EXPECTED_G0058_REPORT_SHA256,
        "max10_certificate_sha256": EXPECTED_MAX10_CERTIFICATE_SHA256,
    }
    if observed != expected:
        raise AuditError(f"immutable binding drift: {observed}/{expected}")
    report = load_json_gz(PRODUCER_REPORT)
    if report.get("script_sha256") != EXPECTED_PRODUCER_SCRIPT_SHA256:
        raise AuditError("producer embedded script binding drift")
    scientific_keys = (
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
    scientific = {key: report[key] for key in scientific_keys}
    observed_scientific = canonical_sha256(deterministic_producer_view(scientific))
    if (
        report.get("canonical_scientific_payload_sha256")
        != EXPECTED_PRODUCER_SCIENTIFIC_SHA256
        or observed_scientific != EXPECTED_PRODUCER_SCIENTIFIC_SHA256
    ):
        raise AuditError("producer scientific projection/hash mismatch")
    mutant = json.loads(json.dumps(scientific))
    mutant["prime_results"][0]["seconds"] = 999.0
    mutant["controls"]["available_gib"] = 0.001
    if canonical_sha256(deterministic_producer_view(mutant)) != observed_scientific:
        raise AuditError("producer scientific hash is not runtime invariant")
    return report, observed


def normalize_edge(edge: Sequence[int]) -> tuple[int, int]:
    if len(edge) != 2:
        raise AuditError(f"malformed edge: {edge}")
    a, b = map(int, edge)
    return (a, b) if a <= b else (b, a)


def cancel_pair(raw_pair: Sequence[Sequence[Sequence[int]]]) -> Pair:
    if len(raw_pair) != 2:
        raise AuditError("certificate pair is not binary")
    left = Counter(normalize_edge(edge) for edge in raw_pair[0])
    right = Counter(normalize_edge(edge) for edge in raw_pair[1])
    common = left & right
    left -= common
    right -= common
    return tuple(sorted(left.elements())), tuple(sorted(right.elements()))


def compact_pair(pair: Pair) -> Pair:
    vertices = sorted({vertex for side in pair for edge in side for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(vertices)}
    return tuple(
        tuple((relabel[a], relabel[b]) for a, b in side) for side in pair
    )  # type: ignore[return-value]


def incidence_data(pair: Pair) -> tuple[dict[int, set[int]], list[set[int]]]:
    vertices = sorted({vertex for side in pair for edge in side for vertex in edge})
    coordinate = {vertex: index for index, vertex in enumerate(vertices)}
    coordinate_count = len(vertices)
    edge_count = sum(map(len, pair))
    total = coordinate_count + 2 + edge_count
    adjacency = {index: set() for index in range(total)}
    edge_node = coordinate_count + 2
    for branch, side in enumerate(pair):
        branch_node = coordinate_count + branch
        for a, b in side:
            for neighbour in {branch_node, coordinate[a], coordinate[b]}:
                adjacency[edge_node].add(neighbour)
                adjacency[neighbour].add(edge_node)
            edge_node += 1
    colours = [
        set(range(coordinate_count)),
        set(range(coordinate_count, coordinate_count + 2)),
        set(range(coordinate_count + 2, total)),
    ]
    return adjacency, colours


def incidence_certificate(pair: Pair) -> bytes:
    adjacency, colours = incidence_data(pair)
    graph = pynauty.Graph(
        len(adjacency), adjacency_dict=adjacency, vertex_coloring=colours
    )
    return pynauty.certificate(graph)


def incidence_graph(pair: Pair) -> nx.Graph:
    adjacency, colours = incidence_data(pair)
    kinds: dict[int, str] = {}
    for kind, nodes in zip(("coordinate", "branch", "edge"), colours, strict=True):
        for node in nodes:
            kinds[node] = kind
    graph = nx.Graph()
    for node, neighbours in adjacency.items():
        graph.add_node(node, kind=kinds[node])
        for neighbour in neighbours:
            graph.add_edge(node, neighbour)
    return graph


def record_pair(record: dict[str, Any]) -> Pair:
    return (
        tuple(normalize_edge(edge) for edge in record["negative_edges"]),
        tuple(normalize_edge(edge) for edge in record["positive_edges"]),
    )


def reconstruct_block(theorem: ModuleType) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    certificate = json.loads(MAX10_CERTIFICATE.read_text(encoding="utf-8"))
    terms = certificate.get("terms")
    if (
        certificate.get("n") != 10
        or not isinstance(terms, list)
        or len(terms) != MAX10_TERM_COUNT
    ):
        raise AuditError("MAX10 certificate schema/census drift")

    retained: list[dict[str, Any]] = []
    mass_histogram: Counter[int] = Counter()
    for term_index, term in enumerate(terms):
        pair = cancel_pair(term["pair"])
        if len(pair[0]) != len(pair[1]):
            raise AuditError(f"unbalanced cancelled term {term_index}")
        mass = len(pair[0])
        mass_histogram[mass] += 1
        if mass != 4:
            continue
        pair = compact_pair(pair)
        retained.append(
            {
                "term_index": term_index,
                "coefficient": str(term["coefficient"]),
                "pair": pair,
                "active_vertices": len(
                    {vertex for side in pair for edge in side for vertex in edge}
                ),
                "certificate": incidence_certificate(pair),
            }
        )
    certificates = [item["certificate"] for item in retained]
    active_histogram = Counter(item["active_vertices"] for item in retained)
    if (
        len(retained) != BLOCK_COUNT
        or len(set(certificates)) != BLOCK_COUNT
        or active_histogram != Counter({8: 10, 9: 44, 10: 274})
    ):
        raise AuditError("independent MAX10 mass-four filtration drift")

    if sha256_path(theorem.SIGNED_STREAM) != EXPECTED_G0038_STREAM_SHA256:
        raise AuditError("G0038 stream binding drift")
    needed = set(certificates)
    matched: dict[bytes, dict[str, Any]] = {}
    mass4_census = 0
    with gzip.open(theorem.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise AuditError("G0038 stream header drift")
        for line in source:
            record = json.loads(line)
            mass = int(record["signed_mass"])
            if mass < 4:
                continue
            if mass > 4:
                break
            mass4_census += 1
            if int(record["active_vertices"]) not in (8, 9, 10):
                continue
            key = incidence_certificate(record_pair(record))
            if key in needed:
                if key in matched:
                    raise AuditError("duplicate G0038 incidence class")
                matched[key] = record
    if mass4_census != 134_193 or set(matched) != needed:
        raise AuditError(
            f"G0038 lookup mismatch: census={mass4_census}, matches={len(matched)}"
        )

    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    records: list[dict[str, Any]] = []
    sequences: list[int] = []
    manifest: list[dict[str, Any]] = []
    for position, item in enumerate(retained):
        record = matched[item["certificate"]]
        if not nx.is_isomorphic(
            incidence_graph(item["pair"]),
            incidence_graph(record_pair(record)),
            node_match=node_match,
        ):
            raise AuditError(f"canonical/VF2 mismatch at retained position {position}")
        sequence = int(record["sequence"])
        records.append(record)
        sequences.append(sequence)
        manifest.append(
            {
                "block_position": position,
                "certificate_term_index": int(item["term_index"]),
                "source_coefficient": item["coefficient"],
                "active_vertices": int(item["active_vertices"]),
                "g0038_sequence": sequence,
                "incidence_certificate_sha256": hashlib.sha256(
                    item["certificate"]
                ).hexdigest(),
            }
        )
    if (
        len(set(sequences)) != BLOCK_COUNT
        or SINGLE_SEQUENCE in sequences
        or canonical_sha256(sequences) != EXPECTED_TERM_ORDER_SHA256
        or canonical_sha256(sorted(sequences)) != EXPECTED_SORTED_SEQUENCE_SHA256
    ):
        raise AuditError("independent MAX10/G0038 ordered manifest drift")
    metadata = {
        "source_term_count": len(terms),
        "multiset_cancellation_signed_mass_histogram": {
            str(key): value for key, value in sorted(mass_histogram.items())
        },
        "retained_signed_mass4_term_count": len(retained),
        "quotient_class_count": len(set(certificates)),
        "active_vertex_histogram": {
            str(key): value for key, value in sorted(active_histogram.items())
        },
        "g0038_mass4_census": mass4_census,
        "networkx_vf2_checks": len(records),
        "manifest_sha256": canonical_sha256(manifest),
        "term_order_sequence_sha256": canonical_sha256(sequences),
        "sorted_sequence_sha256": canonical_sha256(sorted(sequences)),
        "joint_order_sequence_sha256": canonical_sha256([SINGLE_SEQUENCE, *sequences]),
    }
    return records, manifest, metadata


def build_integer_matrix(
    results: list[dict[str, Any]], total_rows: int
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any]]:
    mask = np.zeros(total_rows, dtype=np.bool_)
    total_nonzeros = 0
    for result in results:
        rows = result["rows"]
        values = result["values"]
        if (
            not isinstance(rows, np.ndarray)
            or not isinstance(values, np.ndarray)
            or len(rows) != len(values)
            or len(rows) != len(set(map(int, rows)))
        ):
            raise AuditError("malformed regenerated sparse semantic column")
        mask[rows] = True
        total_nonzeros += len(rows)
    union_rows = np.flatnonzero(mask).astype(np.uint32)
    positions = np.full(total_rows, -1, dtype=np.int32)
    positions[union_rows] = np.arange(len(union_rows), dtype=np.int32)
    matrix = np.zeros((len(union_rows), len(results)), dtype=np.int64)
    for column, result in enumerate(results):
        local = positions[result["rows"]]
        if np.any(local < 0):
            raise AuditError("semantic entry escaped independently built union")
        matrix[local, column] = result["values"]
    if int(np.count_nonzero(matrix)) != total_nonzeros:
        raise AuditError("dense integer matrix lost or duplicated sparse entries")
    lambdas = np.array([int(result["lambda"]) for result in results], dtype=np.int64)
    metadata = {
        "union_row_count": len(union_rows),
        "union_row_indices_sha256": array_sha256(union_rows),
        "matrix_shape": list(matrix.shape),
        "matrix_sha256": dense_integer_matrix_sha256(matrix),
        "lambda_row_sha256": hashlib.sha256(
            lambdas.astype("<i8", copy=False).tobytes(order="C")
        ).hexdigest(),
        "total_nonzeros": total_nonzeros,
    }
    return union_rows, matrix, lambdas, metadata


def prepare_semantics(
    report: dict[str, Any], workers: int
) -> tuple[
    tuple[tuple[int, ...], ...],
    list[dict[str, Any]],
    list[dict[str, Any]],
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    dict[str, Any],
    list[dict[str, Any]],
]:
    g0057 = import_bound("g0059_audit_g0057", G0057_SCRIPT, EXPECTED_G0057_SCRIPT_SHA256)
    g0057.G0054 = g0057.import_bound(
        "g0059_audit_g0054", g0057.G0054_SCRIPT, g0057.EXPECTED_G0054_SCRIPT_SHA256
    )
    theorem = g0057.G0054.load_theorem("g0059_audit_theorem")
    g0057.THEOREM = theorem
    universe = g0057.G0054.direction_universe()
    if len(universe) != ROW_COUNT:
        raise AuditError("complete direction universe census drift")
    g0057.ROW_INDEX = {direction: index for index, direction in enumerate(universe)}

    block_records, manifest, mapping = reconstruct_block(theorem)
    producer_mapping = report["max10_induced_block_reconstruction"]
    if (
        manifest != producer_mapping["manifest"]
        or mapping["manifest_sha256"] != producer_mapping["manifest_sha256"]
        or mapping["term_order_sequence_sha256"]
        != producer_mapping["term_order_sequence_sha256"]
        or mapping["sorted_sequence_sha256"]
        != producer_mapping["sorted_sequence_sha256"]
    ):
        raise AuditError("independent 328-column manifest differs from producer")

    (
        s0_sequences,
        proper_indices,
        seed_indices,
        selected_candidates,
        _prices,
        _exact_manifest,
        _manifest_metadata,
    ) = g0057.load_frozen_manifests("baseline-only")
    if selected_candidates:
        raise AuditError("frozen G0057 baseline unexpectedly includes candidates")
    g0050 = g0057.import_bound(
        "g0059_audit_g0050", g0057.G0050_SCRIPT, g0057.EXPECTED_G0050_SCRIPT_SHA256
    )
    extract = g0050.import_extract()
    search = extract.load_search()
    lowmass_records = search.load_records(search.load_g47())
    if len(lowmass_records) != 3_310:
        raise AuditError("low-mass source census drift")

    needed_mass4 = set(s0_sequences) | {SINGLE_SEQUENCE} | {
        int(record["sequence"]) for record in block_records
    }
    mass4_records = g0057.read_mass4_records(theorem, needed_mass4)
    payloads: list[tuple[int, str, int, dict[str, Any]]] = []
    for pivot_position, sequence in enumerate(s0_sequences):
        payloads.append(
            (len(payloads), "s0_mass4_pivot", pivot_position, mass4_records[sequence])
        )
    for index in proper_indices:
        payloads.append(
            (len(payloads), "lowmass_proper_basis", index, lowmass_records[index])
        )
    for index in seed_indices:
        payloads.append(
            (len(payloads), "lowmass_full_seed", index, lowmass_records[index])
        )
    if len(payloads) != BASELINE_COLUMN_COUNT:
        raise AuditError("baseline payload census drift")
    payloads.append(
        (
            len(payloads),
            "g0059_single_support8",
            SINGLE_SEQUENCE,
            mass4_records[SINGLE_SEQUENCE],
        )
    )
    for position, record in enumerate(block_records):
        payloads.append(
            (len(payloads), "g0059_max10_induced_mass4", position, record)
        )

    results, _seconds = g0057.generate_semantics(
        payloads, g0057.ROW_INDEX, workers, "G0059_CLEANROOM_SEMANTIC"
    )
    baseline_results = results[:BASELINE_COLUMN_COUNT]
    candidate_results = results[BASELINE_COLUMN_COUNT:]
    expected_candidate_order = [SINGLE_SEQUENCE] + [
        int(item["g0038_sequence"]) for item in manifest
    ]
    if [int(result["sequence"]) for result in candidate_results] != expected_candidate_order:
        raise AuditError("regenerated joint candidate order drift")
    if any(int(result["lambda"]) for result in candidate_results):
        raise AuditError("joint candidate lambda is not zero")

    baseline_rows, baseline_matrix, lambda_row, baseline_metadata = build_integer_matrix(
        baseline_results, ROW_COUNT
    )
    if (
        baseline_metadata["matrix_sha256"] != EXPECTED_BASELINE_MATRIX_SHA256
        or baseline_metadata["union_row_indices_sha256"]
        != EXPECTED_BASELINE_UNION_SHA256
        or baseline_metadata["matrix_shape"]
        != report["baseline"]["integer_matrix_shape"]
        or baseline_metadata["lambda_row_sha256"]
        != report["baseline"]["lambda_row_sha256"]
    ):
        raise AuditError("independently regenerated baseline binding drift")

    candidate_rows = np.unique(
        np.concatenate([result["rows"] for result in candidate_results])
    ).astype(np.uint32, copy=False)
    combined_rows = np.union1d(baseline_rows, candidate_rows).astype(
        np.uint32, copy=False
    )
    complete_positions = np.full(ROW_COUNT, -1, dtype=np.int32)
    complete_positions[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    candidate_matrix = np.zeros((len(combined_rows), JOINT_COUNT), dtype=np.int64)
    for column, result in enumerate(candidate_results):
        candidate_matrix[complete_positions[result["rows"]], column] = result["values"]
    baseline_positions = complete_positions[baseline_rows]
    candidate_metadata = {
        "candidate_matrix_shape": list(candidate_matrix.shape),
        "candidate_matrix_sha256": hashlib.sha256(
            candidate_matrix.astype("<i8", copy=False).tobytes(order="C")
        ).hexdigest(),
        "candidate_total_nonzeros": int(np.count_nonzero(candidate_matrix)),
        "combined_union_row_count": len(combined_rows),
        "combined_union_row_indices_sha256": array_sha256(combined_rows),
        "ordered_sparse_stream_sha256": g0057.ordered_sparse_stream_hash(
            candidate_results
        ),
    }
    producer_candidate = report["candidate_semantics"]
    if (
        {
            key: candidate_metadata[key]
            for key in (
                "candidate_matrix_shape",
                "candidate_matrix_sha256",
                "candidate_total_nonzeros",
                "combined_union_row_count",
                "combined_union_row_indices_sha256",
            )
        }
        != producer_candidate["combined_union"]
        or candidate_metadata["ordered_sparse_stream_sha256"]
        != producer_candidate["ordered_sparse_stream_sha256"]
    ):
        raise AuditError("independently regenerated candidate matrix binding drift")

    single = candidate_results[0]
    support8 = {
        index
        for index, direction in enumerate(universe)
        if Counter(direction) == Counter({-1: 4, 0: 3, 1: 4})
    }
    if (
        set(map(int, single["rows"])) != support8
        or set(map(int, single["values"])) != {6_912}
        or len(support8) != 3_465
    ):
        raise AuditError("sequence 92489 support-eight semantics drift")
    mapping["manifest"] = manifest
    mapping["manifest_matches_producer_byte_for_byte"] = True
    return (
        universe,
        baseline_results,
        candidate_results,
        baseline_rows,
        baseline_matrix,
        lambda_row,
        combined_rows,
        candidate_matrix,
        {"baseline": baseline_metadata, "candidate": candidate_metadata},
        manifest,
    )


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.int64)
    return nmod_mat(
        reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime
    )


def from_nmod(matrix: nmod_mat) -> np.ndarray:
    return np.asarray(matrix.tolist(), dtype=np.int64)


def rank_pair(residual: np.ndarray, delta: np.ndarray, prime: int) -> dict[str, int]:
    if residual.shape[1] != len(delta):
        raise AuditError("rank-pair shape mismatch")
    base = np.ascontiguousarray(residual.T, dtype=np.int64)
    augmented = np.ascontiguousarray(
        np.column_stack((base, np.remainder(delta, prime))), dtype=np.int64
    )
    rank = int(to_nmod(base, prime).rank())
    augmented_rank = int(to_nmod(augmented, prime).rank())
    return {
        "prefix": residual.shape[1],
        "rank_residual": rank,
        "rank_residual_plus_delta": augmented_rank,
        "augmented_gain": augmented_rank - rank,
    }


def verify_kernel_certificate(
    baseline: np.ndarray,
    lambda_row: np.ndarray,
    profile: dict[str, Any],
    prime: int,
) -> dict[str, Any]:
    pivots = list(map(int, profile["pivot_columns"]))
    nonpivots = [column for column in range(BASELINE_COLUMN_COUNT) if column not in set(pivots)]
    payload = profile["kernel_basis"]
    if (
        len(pivots) != BASELINE_RANK
        or len(payload) != BASELINE_NULLITY
        or len(nonpivots) != BASELINE_NULLITY
    ):
        raise AuditError(f"baseline rank/nullity certificate census drift at {prime}")
    normalized = np.zeros((BASELINE_COLUMN_COUNT, BASELINE_NULLITY), dtype=np.int64)
    support_total = 0
    for basis_index, item in enumerate(payload):
        support = [[int(a), int(b)] for a, b in item["support"]]
        distinguished = int(item["distinguished_nonpivot_column"])
        if (
            int(item["basis_column"]) != basis_index
            or distinguished != nonpivots[basis_index]
            or dict(support).get(distinguished) != 1
            or [column for column, _ in support if column in nonpivots]
            != [distinguished]
            or canonical_sha256(support) != item["sparse_vector_sha256"]
            or canonical_sha256([column for column, _ in support])
            != item["support_indices_sha256"]
        ):
            raise AuditError(f"kernel normalization/hash drift at {prime}/{basis_index}")
        columns = np.array([column for column, _ in support], dtype=np.int64)
        coefficients = np.array([value for _, value in support], dtype=np.int64)
        replay = np.remainder(
            np.remainder(baseline[:, columns], prime) @ coefficients, prime
        )
        if np.any(replay):
            raise AuditError(f"kernel complete-union replay failed at {prime}/{basis_index}")
        if int(np.remainder(lambda_row[columns] @ coefficients, prime)):
            raise AuditError(f"kernel lambda pairing failed at {prime}/{basis_index}")
        normalized[columns, basis_index] = coefficients
        support_total += len(support)
    observed_hash = array_sha256(normalized)
    if observed_hash != profile["normalized_kernel_matrix_sha256"]:
        raise AuditError(f"normalized kernel matrix hash drift at {prime}")
    return {
        "kernel_vector_count": len(payload),
        "kernel_support_entry_count": support_total,
        "normalized_kernel_matrix_sha256": observed_hash,
        "all_complete_union_replays_zero": True,
        "all_lambda_pairings_zero": True,
        "distinct_free_coordinates_equal_one": True,
        "rank_upper_bound_from_independent_kernels": BASELINE_COLUMN_COUNT
        - BASELINE_NULLITY,
    }


def analyze_prime(
    prime: int,
    report: dict[str, Any],
    baseline_rows: np.ndarray,
    baseline: np.ndarray,
    lambda_row: np.ndarray,
    combined_rows: np.ndarray,
    candidate: np.ndarray,
) -> dict[str, Any]:
    profile = next(
        item
        for item in report["baseline"]["per_prime_rank_profiles_and_preserved_nullspaces"]
        if int(item["prime"]) == prime
    )
    producer = next(item for item in report["prime_results"] if int(item["prime"]) == prime)
    columns = list(map(int, profile["pivot_columns"]))
    row_positions = list(map(int, profile["pivot_union_row_positions"]))
    if len(columns) != BASELINE_RANK or len(row_positions) != BASELINE_RANK:
        raise AuditError(f"pivot certificate census drift at {prime}")
    minor = np.ascontiguousarray(baseline[np.ix_(row_positions, columns)], dtype=np.int64)
    determinant = int(to_nmod(minor, prime).det())
    if not determinant or determinant != int(producer["pivot_minor"]["determinant_mod_prime"]):
        raise AuditError(f"pivot minor determinant mismatch at {prime}")
    if (
        hashlib.sha256(minor.astype("<i8", copy=False).tobytes(order="C")).hexdigest()
        != producer["pivot_minor"]["minor_int64_sha256"]
    ):
        raise AuditError(f"pivot minor integer hash mismatch at {prime}")
    kernel = verify_kernel_certificate(baseline, lambda_row, profile, prime)

    lambda_c = np.remainder(lambda_row[columns], prime).astype(np.int64, copy=False)
    weights = np.array(
        producer["sparse_on_pivot_rows_dual"]["weights_mod_prime"], dtype=np.int64
    )
    if len(weights) != BASELINE_RANK:
        raise AuditError(f"dual length drift at {prime}")
    dual_minor = from_nmod(
        to_nmod(minor.T, prime) * to_nmod(weights.reshape(-1, 1), prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_minor - lambda_c, prime)):
        raise AuditError(f"B^T w=lambda_C failed at {prime}")
    baseline_on_rows = np.ascontiguousarray(baseline[row_positions, :], dtype=np.int64)
    dual_all = from_nmod(
        to_nmod(weights.reshape(1, -1), prime) * to_nmod(baseline_on_rows, prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_all - lambda_row, prime)):
        raise AuditError(f"sparse dual failed on baseline at {prime}")

    complete_to_combined = np.full(ROW_COUNT, -1, dtype=np.int32)
    complete_to_combined[combined_rows] = np.arange(len(combined_rows), dtype=np.int32)
    pivot_complete_rows = baseline_rows[row_positions]
    pivot_combined = complete_to_combined[pivot_complete_rows]
    candidate_on_rows = np.ascontiguousarray(candidate[pivot_combined, :], dtype=np.int64)
    coefficients = np.array(
        producer["candidate_schur_coefficients"]["candidate_major_mod_prime"],
        dtype=np.int64,
    ).T
    if coefficients.shape != (BASELINE_RANK, JOINT_COUNT):
        raise AuditError(f"candidate coefficient shape drift at {prime}")
    solved = from_nmod(to_nmod(minor, prime) * to_nmod(coefficients, prime))
    if np.any(np.remainder(solved - candidate_on_rows, prime)):
        raise AuditError(f"B A=h_R replay failed at {prime}")

    baseline_position = np.full(ROW_COUNT, -1, dtype=np.int32)
    baseline_position[baseline_rows] = np.arange(len(baseline_rows), dtype=np.int32)
    basis_combined = np.zeros((len(combined_rows), BASELINE_RANK), dtype=np.int64)
    rows_present = baseline_position[combined_rows] >= 0
    basis_combined[rows_present, :] = baseline[
        baseline_position[combined_rows[rows_present]], :
    ][:, columns]
    predicted = from_nmod(
        to_nmod(basis_combined, prime) * to_nmod(coefficients, prime)
    )
    residual = np.remainder(candidate - predicted, prime).astype(np.int64, copy=False)
    del basis_combined, predicted, solved
    gc.collect()
    if np.any(residual[pivot_combined, :]):
        raise AuditError(f"Schur residual is nonzero on pivot rows at {prime}")
    delta = np.remainder(-np.remainder(lambda_c @ coefficients, prime), prime).astype(
        np.int64, copy=False
    )
    dual_prices = from_nmod(
        to_nmod(weights.reshape(1, -1), prime) * to_nmod(candidate_on_rows, prime)
    ).reshape(-1)
    if np.any(np.remainder(dual_prices + delta, prime)):
        raise AuditError(f"dual price/delta bridge failed at {prime}")

    per_column = producer["all_candidate_residual_columns"]
    for index, item in enumerate(per_column):
        if (
            int(item["candidate_position"]) != index
            or int(item["support_size"]) != int(np.count_nonzero(residual[:, index]))
            or item["residual_sha256"] != array_sha256(residual[:, index])
            or int(item["delta_mod_prime"]) != int(delta[index])
            or int(item["dual_price_mod_prime"]) != int(dual_prices[index])
        ):
            raise AuditError(f"per-column Schur certificate drift at {prime}/{index}")

    joint = rank_pair(residual, delta, prime)
    block = rank_pair(residual[:, 1:], delta[1:], prime)
    single = rank_pair(residual[:, :1], delta[:1], prime)
    expected_joint = {
        key: int(producer["joint_sequence_92489_plus_max10_block"]["full_prefix"][key])
        for key in joint
    }
    expected_block = {
        key: int(producer["max10_induced_block"]["full_prefix"][key]) for key in block
    }
    expected_single = {
        key: int(producer["single_sequence_92489"][key]) for key in single
    }
    if joint != expected_joint or block != expected_block or single != expected_single:
        raise AuditError(
            f"independent quotient rank mismatch at {prime}: "
            f"joint={joint}/{expected_joint}, block={block}/{expected_block}"
        )
    if joint != {
        "prefix": JOINT_COUNT,
        "rank_residual": 323,
        "rank_residual_plus_delta": 323,
        "augmented_gain": 0,
    }:
        raise AuditError(f"unexpected joint329 verdict at {prime}: {joint}")
    if block != {
        "prefix": BLOCK_COUNT,
        "rank_residual": 322,
        "rank_residual_plus_delta": 322,
        "augmented_gain": 0,
    }:
        raise AuditError(f"unexpected block-only diagnostic at {prime}: {block}")
    joint_report = producer["joint_sequence_92489_plus_max10_block"]
    if (
        joint_report["first_gain_prefix"] is not None
        or joint_report["potent_circuit"] is not None
        or joint_report["binary_search_rank_queries"]
        != [joint_report["full_prefix"]]
    ):
        raise AuditError(f"negative joint prefix/witness contract drift at {prime}")

    result = {
        "prime": prime,
        "baseline_rank_certificate": {
            "pivot_minor_size": BASELINE_RANK,
            "determinant_mod_prime": determinant,
            "nonzero_minor_rank_lower_bound": BASELINE_RANK,
            **kernel,
            "certified_rank": BASELINE_RANK,
            "certified_nullity": BASELINE_NULLITY,
        },
        "dual_and_schur": {
            "B_transpose_w_equals_lambda_C": True,
            "sparse_dual_replays_all_1358_columns": True,
            "B_A_equals_candidate_pivot_rows_for_all_329": True,
            "all_residuals_zero_on_pivot_rows": True,
            "all_dual_prices_equal_negative_delta": True,
            "joint_residual_sha256": array_sha256(residual),
            "joint_delta_sha256": array_sha256(delta),
        },
        "primary_joint329": joint,
        "subordinate_block328": block,
        "single_sequence_92489": single,
        "negative_prefix_contract": {
            "only_full_prefix_was_queried": True,
            "first_gain_prefix": None,
            "potent_circuit": None,
        },
    }
    del residual, coefficients, candidate_on_rows, minor, baseline_on_rows
    gc.collect()
    return result


def synthetic_controls() -> dict[str, Any]:
    prime = PRIMES[0]
    residual = np.array([[1, 1], [0, 0]], dtype=np.int64)
    delta = np.array([0, 1], dtype=np.int64)
    left = rank_pair(residual[:, :1], delta[:1], prime)
    right = rank_pair(residual[:, 1:], delta[1:], prime)
    joint = rank_pair(residual, delta, prime)
    if left["augmented_gain"] or right["augmented_gain"] or joint["augmented_gain"] != 1:
        raise AuditError("joint-family regression control failed")
    pair: Pair = (
        ((0, 0), (1, 2), (2, 3), (3, 3)),
        ((4, 4), (5, 6), (6, 7), (7, 7)),
    )
    transformed: Pair = (
        tuple((9 - b, 9 - a) for a, b in pair[1]),
        tuple((9 - b, 9 - a) for a, b in pair[0]),
    )
    if incidence_certificate(pair) != incidence_certificate(transformed):
        raise AuditError("coordinate/branch equivalence control failed")
    return {
        "left_singleton_gain": left["augmented_gain"],
        "right_singleton_gain": right["augmented_gain"],
        "joint_gain": joint["augmented_gain"],
        "separate_no_gain_does_not_imply_joint_no_gain": True,
        "typed_incidence_invariant_under_coordinate_relabelling_and_global_branch_swap": True,
    }


def run(workers: int) -> dict[str, Any]:
    script_hash_before = sha256_path(Path(__file__))
    producer, bindings = verify_producer()
    controls = synthetic_controls()
    (
        _universe,
        _baseline_results,
        _candidate_results,
        baseline_rows,
        baseline_matrix,
        lambda_row,
        combined_rows,
        candidate_matrix,
        semantic_metadata,
        manifest,
    ) = prepare_semantics(producer, workers)

    prime_results = [
        analyze_prime(
            prime,
            producer,
            baseline_rows,
            baseline_matrix,
            lambda_row,
            combined_rows,
            candidate_matrix,
        )
        for prime in PRIMES
    ]
    if any(item["primary_joint329"]["augmented_gain"] for item in prime_results):
        raise AuditError("frozen negative producer verdict did not survive clean-room replay")
    if producer["cross_prime_comparison"]["joint_329_augmented_gains"] != [0, 0]:
        raise AuditError("producer cross-prime joint summary drift")
    if producer["result"] != "NO_JOINT_329_QUOTIENT_GAIN_AT_EITHER_FROZEN_PRIME":
        raise AuditError("producer result label drift")

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "result": "INDEPENDENTLY_REPLAYED_NO_JOINT_329_GAIN_AT_BOTH_FROZEN_PRIMES",
        "producer_commit": PRODUCER_COMMIT,
        "bindings": {
            **bindings,
            "producer_scientific_payload_sha256": EXPECTED_PRODUCER_SCIENTIFIC_SHA256,
            "g0038_stream_sha256": EXPECTED_G0038_STREAM_SHA256,
        },
        "producer_integrity": {
            "embedded_script_hash_matches_frozen_script": True,
            "scientific_projection_recomputed": True,
            "runtime_mutation_invariance_replayed": True,
        },
        "independent_candidate_order": {
            "max10_source_terms": MAX10_TERM_COUNT,
            "retained_mass4_columns": BLOCK_COUNT,
            "joint_column_count": JOINT_COUNT,
            "joint_order": "sequence 92489, then 328 MAX10-induced atoms in certificate-term order",
            "manifest": manifest,
            "manifest_sha256": canonical_sha256(manifest),
            "term_order_sequence_sha256": EXPECTED_TERM_ORDER_SHA256,
            "sorted_sequence_sha256": EXPECTED_SORTED_SEQUENCE_SHA256,
        },
        "regenerated_semantics": semantic_metadata,
        "prime_replays": prime_results,
        "controls": controls,
        "bounded_conclusion": (
            "For the frozen 1,358-column G-0057 baseline and ordered joint family "
            "consisting of sequence 92,489 plus the 328 proper mass-four atoms induced "
            "by the public MAX10 certificate, the independently rebuilt Schur residual "
            "has rank 323 and remains rank 323 after appending delta over both F_1000003 "
            "and F_1000033. The 328-only residual/augmented ranks are 322/322."
        ),
        "claim_boundary": [
            "This is a bounded two-prime modular no-gain result for one frozen baseline and one 329-column family.",
            "The audit does not infer a rational rank or a theorem over Q from agreement at two primes.",
            "The 328 induced atoms are not the full set of 132,728 proper mass-four atoms.",
            "The audit reuses the hash-bound G-0057 complete-row semantic generator; it independently reconstructs ordering, matrices, certificates, Schur algebra, and ranks, but is not a second implementation of the primitive-normal-form semantic kernel.",
            "No potent circuit exists in either audited finite field for the joint family, so there is no modular witness to lift or full-row circuit to replay in the negative branch.",
        ],
        "script_sha256": script_hash_before,
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise AuditError("audit script changed during execution")
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
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.self_test:
        verify_producer()
        print(json.dumps({"result": "SELF_TEST_PASS", "controls": synthetic_controls()}, sort_keys=True))
        return
    output = args.output.resolve()
    try:
        output.relative_to(HERE.resolve())
    except ValueError as error:
        raise SystemExit("audit output must remain in the clean-room G-0059 directory") from error
    report = run(args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
