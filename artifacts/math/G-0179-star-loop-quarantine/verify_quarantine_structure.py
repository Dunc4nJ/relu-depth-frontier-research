#!/usr/bin/env python3
"""Certify the structural premises of the d[0] = 1 STAR quarantine.

This verifier reads no priced matrix, rank, determinant, residual, or fitted
coefficient.  It checks only the frozen old/new orbit inventories and the
preselected structural-matching directions.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
from pathlib import Path
from typing import Any


N = 11
EXPECTED_PRIMARY_SHA256 = (
    "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48"
)
EXPECTED_PRIMARY_RECORDS = 163_740
EXPECTED_STAR_SHA256 = (
    "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4"
)
EXPECTED_STAR_RECORDS = 5_773
EXPECTED_DIRECTIONS_I8_SHA256 = (
    "858c182304ae5256dfa85e720803b54013afb70b7b67383aa6680ecbc0d8336d"
)
EXPECTED_DIRECTIONS = 5_771


class VerificationError(RuntimeError):
    """A frozen structural premise failed."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def check_primary(path: Path) -> dict[str, Any]:
    observed = sha256_path(path)
    if observed != EXPECTED_PRIMARY_SHA256:
        raise VerificationError(f"primary map hash drift: {observed}")
    records = 0
    topology_loop_counts: dict[tuple[int, int], int] = {}
    with gzip.open(path, "rt", encoding="ascii") as stream:
        for line_number, line in enumerate(stream, 1):
            item = json.loads(line)
            if line_number == 1:
                if item.get("record_type") != "header":
                    raise VerificationError("primary header drift")
                if item.get("primary_signed_W_orbits") != EXPECTED_PRIMARY_RECORDS:
                    raise VerificationError("primary header census drift")
                continue
            if item.get("record_type") != "signed_W_orbit":
                raise VerificationError(f"primary record type drift at line {line_number}")
            pair = item.get("representative_pair")
            if not isinstance(pair, list) or len(pair) != 2:
                raise VerificationError(f"primary pair drift at line {line_number}")
            observed_loops = []
            for branch in pair:
                if not isinstance(branch, list):
                    raise VerificationError(f"primary branch drift at line {line_number}")
                observed_loops.append(sum(int(edge[0] == edge[1]) for edge in branch))
            topology = item.get("topology", {})
            declared = (
                topology.get("min_branch_loops"),
                topology.get("max_branch_loops"),
            )
            if observed_loops != [0, 0] or declared != (0, 0):
                raise VerificationError(
                    f"loop-bearing primary representative at orbit {item.get('orbit_index')}"
                )
            topology_loop_counts[declared] = topology_loop_counts.get(declared, 0) + 1
            records += 1
    if records != EXPECTED_PRIMARY_RECORDS:
        raise VerificationError(f"primary record census drift: {records}")
    return {
        "records": records,
        "all_representative_branches_loopless": True,
        "topology_loop_count_histogram": {
            f"min_{key[0]}_max_{key[1]}": value
            for key, value in sorted(topology_loop_counts.items())
        },
        "consequence": (
            "For every ordering of every frozen primary signed-W representative, "
            "the first back-degree coordinate is zero. Hence these columns have no "
            "primitive ordered-cone hinge coordinate with d[0] != 0."
        ),
    }


def check_star(path: Path) -> dict[str, Any]:
    observed = sha256_path(path)
    if observed != EXPECTED_STAR_SHA256:
        raise VerificationError(f"STAR record hash drift: {observed}")
    document = json.loads(path.read_bytes())
    records = document.get("records")
    if not isinstance(records, list) or len(records) != EXPECTED_STAR_RECORDS:
        raise VerificationError("STAR record census drift")
    if [record.get("sequence") for record in records] != list(range(EXPECTED_STAR_RECORDS)):
        raise VerificationError("STAR sequence/order drift")
    orientation_histogram: dict[str, int] = {}
    common_edge_count_histogram: dict[int, int] = {}
    common_loop_count_histogram: dict[int, int] = {}
    for record in records:
        pair = record.get("representative_pair")
        cancelled_pair = record.get("cancelled_signed_pair")
        if not isinstance(pair, list) or len(pair) != 2:
            raise VerificationError(f"full pair drift at {record['sequence']}")
        if not isinstance(cancelled_pair, list) or len(cancelled_pair) != 2:
            raise VerificationError(f"cancelled pair drift at {record['sequence']}")
        full_sides = []
        for branch in pair:
            if not isinstance(branch, list) or len(branch) != 5:
                raise VerificationError(
                    f"full degree-five branch drift at {record['sequence']}"
                )
            full_sides.append([tuple(map(int, edge)) for edge in branch])
        left_counts: dict[tuple[int, int], int] = {}
        right_counts: dict[tuple[int, int], int] = {}
        for edge in full_sides[0]:
            left_counts[edge] = left_counts.get(edge, 0) + 1
        for edge in full_sides[1]:
            right_counts[edge] = right_counts.get(edge, 0) + 1
        common: list[tuple[int, int]] = []
        negative: list[tuple[int, int]] = []
        positive: list[tuple[int, int]] = []
        for edge in sorted(set(left_counts) | set(right_counts)):
            shared = min(left_counts.get(edge, 0), right_counts.get(edge, 0))
            common.extend([edge] * shared)
            negative.extend([edge] * (left_counts.get(edge, 0) - shared))
            positive.extend([edge] * (right_counts.get(edge, 0) - shared))
        expected_cancelled = [
            [list(edge) for edge in negative],
            [list(edge) for edge in positive],
        ]
        if expected_cancelled != cancelled_pair:
            raise VerificationError(
                f"full/cancelled pair mismatch at {record['sequence']}"
            )
        support = sorted({vertex for edge in negative + positive for vertex in edge})
        relabel = {vertex: index for index, vertex in enumerate(support)}
        expected_negative_compact = [[relabel[u], relabel[v]] for u, v in negative]
        expected_positive_compact = [[relabel[u], relabel[v]] for u, v in positive]
        if record.get("original_active_labels") != support:
            raise VerificationError(
                f"active-label relabelling drift at {record['sequence']}"
            )
        if int(record.get("active_vertices", -1)) != len(support):
            raise VerificationError(
                f"active-vertex census drift at {record['sequence']}"
            )
        if record.get("negative_edges") != expected_negative_compact:
            raise VerificationError(
                f"negative compact relabelling drift at {record['sequence']}"
            )
        if record.get("positive_edges") != expected_positive_compact:
            raise VerificationError(
                f"positive compact relabelling drift at {record['sequence']}"
            )
        signed_mass = int(record["signed_mass"])
        if len(negative) != signed_mass or len(positive) != signed_mass:
            raise VerificationError(f"signed-mass drift at {record['sequence']}")
        if len(common) != 5 - signed_mass:
            raise VerificationError(
                f"common-edge cardinality drift at {record['sequence']}"
            )
        common_loops = sum(int(u == v) for u, v in common)
        common_edge_count_histogram[len(common)] = (
            common_edge_count_histogram.get(len(common), 0) + 1
        )
        common_loop_count_histogram[common_loops] = (
            common_loop_count_histogram.get(common_loops, 0) + 1
        )
        negative_loops = sum(
            int(edge[0] == edge[1]) for edge in record["negative_edges"]
        )
        positive_loops = sum(
            int(edge[0] == edge[1]) for edge in record["positive_edges"]
        )
        if negative_loops != record["negative_loop_count"]:
            raise VerificationError(f"negative loop count drift at {record['sequence']}")
        if positive_loops != record["positive_loop_count"]:
            raise VerificationError(f"positive loop count drift at {record['sequence']}")
        if negative_loops + positive_loops != 1:
            raise VerificationError(f"nonexclusive residual loop at {record['sequence']}")
        label = f"negative_{negative_loops}_positive_{positive_loops}"
        orientation_histogram[label] = orientation_histogram.get(label, 0) + 1
    if common_loop_count_histogram != {0: len(records)}:
        raise VerificationError(
            f"common-loop padding entered frozen STAR representatives: "
            f"{common_loop_count_histogram}"
        )
    return {
        "records": len(records),
        "all_representative_pairs_are_degree_five": True,
        "all_full_to_cancelled_decompositions_replayed": True,
        "all_compact_signed_pairs_relabelled_exactly_from_full_pairs": True,
        "all_common_edges_are_nonloops": common_loop_count_histogram == {0: len(records)},
        "common_edge_count_histogram": {
            str(key): value for key, value in sorted(common_edge_count_histogram.items())
        },
        "common_loop_count_histogram": {
            str(key): value for key, value in sorted(common_loop_count_histogram.items())
        },
        "all_records_have_exactly_one_residual_unit_loop": True,
        "signed_loop_orientation_histogram": dict(sorted(orientation_histogram.items())),
        "consequence": (
            "Place the residual-loop vertex first and orient the signed word so its "
            "first nonzero coordinate is positive. The resulting primitive word has "
            "d[0] = 1; therefore d[0] = 1 coordinates can detect STAR coefficients "
            "while vanishing on every frozen loopless primary signed-W column. Every "
            "replayed common edge is a nonloop and contributes only an "
            "ordered-chamber-linear, zero-interior-hinge carrier after full S_11 "
            "symmetrization."
        ),
    }


def direction_digest(directions: list[list[int]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        if len(direction) != N:
            raise VerificationError("direction width drift")
        if any(value < -128 or value > 127 for value in direction):
            raise VerificationError("direction does not fit signed i8")
        digest.update(bytes(value & 0xFF for value in direction))
    return digest.hexdigest()


def check_directions(path: Path) -> dict[str, Any]:
    document = json.loads(path.read_bytes())
    directions = document.get("directions")
    if not isinstance(directions, list) or len(directions) != EXPECTED_DIRECTIONS:
        raise VerificationError("matching-direction census drift")
    observed_digest = direction_digest(directions)
    if observed_digest != EXPECTED_DIRECTIONS_I8_SHA256:
        raise VerificationError(f"matching-direction digest drift: {observed_digest}")
    if document.get("directions_i8_sha256") != observed_digest:
        raise VerificationError("matching document/direction digest mismatch")
    for index, direction in enumerate(directions):
        if direction[0] != 1:
            raise VerificationError(f"direction {index} does not have d[0] = 1")
        if sum(direction) != 0:
            raise VerificationError(f"direction {index} does not sum to zero")
        if math.gcd(*direction) != 1:
            raise VerificationError(f"direction {index} is not primitive")
        first_nonzero = next((value for value in direction if value), None)
        if first_nonzero is None or first_nonzero < 0:
            raise VerificationError(f"direction {index} orientation drift")
        prefix = 0
        active = False
        for value in direction[:-1]:
            prefix += value
            active |= prefix < 0
        if not active:
            raise VerificationError(f"direction {index} is linear on the ordered cone")
    return {
        "directions": len(directions),
        "directions_i8_sha256": observed_digest,
        "all_d0_equal_one": True,
        "all_sum_zero_primitive_first_positive_and_ordered_cone_active": True,
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("primary_map", type=Path)
    parser.add_argument("star_records", type=Path)
    parser.add_argument("matching_directions", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.output.exists():
        raise VerificationError(f"refusing to overwrite {arguments.output}")
    inputs = [
        arguments.primary_map.resolve(),
        arguments.star_records.resolve(),
        arguments.matching_directions.resolve(),
    ]
    opening_hashes = {str(path): sha256_path(path) for path in inputs}
    result = {
        "schema": "g0179.d0-quarantine-structural-premises.v2",
        "result": "QUARANTINE_STRUCTURAL_PREMISES_CERTIFIED",
        "claim_boundary": (
            "Exact finite structural-premise verification only. This does not price "
            "the matched minor, compute a rank or kernel, decide MAX11 membership, "
            "establish completeness of any ansatz, or prove a neural-network lower bound."
        ),
        "old_primary": check_primary(inputs[0]),
        "star_outside_primary": check_star(inputs[1]),
        "matching_directions": check_directions(inputs[2]),
        "target_fact": (
            "On the ordered chamber x[0] <= ... <= x[10], MAX11 equals x[10] and "
            "therefore has zero coefficient on every hinge coordinate, including d[0] = 1."
        ),
        "ambient_space": (
            "O is the real span of the 163,740 canonical fully S_11-symmetrized "
            "G-0113 primary columns together with the pure carriers 5E and 5L. "
            "For a degree-five pair, cancelling common edges changes the full atom "
            "only by their additive fully symmetrized carrier columns. The replayed "
            "STAR representatives have only common nonloops; more generally a change "
            "from c common loops to canonical nonloop padding adds c(L-E), which lies "
            "in O because L-E=(5L-5E)/5 over R or Q. This is a linear-span statement, "
            "not a nonnegative-cone statement."
        ),
        "conditional_gate": (
            "After separately certifying q_1548 and q_4259 in O, if the selected "
            "5,771 by 5,771 integer hinge matrix has nonzero determinant, the remaining "
            "STAR-outside-primary columns form a direct summand modulo O and the kernel "
            "of the selected d[0] = 1 hinge restriction inside span(O union STAR) is "
            "exactly O. Hence any selected-hinge-free target, including MAX11, belongs "
            "to span(O union STAR) if and only if it already belongs to O. This does "
            "not say STAR adds no functions to the total span."
        ),
        "bindings": {
            "verifier": str(Path(__file__).resolve()),
            "verifier_sha256": sha256_path(Path(__file__).resolve()),
            "inputs_opening_sha256": opening_hashes,
        },
        "inputs_rehashed_at_end": True,
    }
    closing_hashes = {str(path): sha256_path(path) for path in inputs}
    if closing_hashes != opening_hashes:
        raise VerificationError("input changed during structural verification")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    with arguments.output.open("xb") as handle:
        handle.write(canonical_bytes(result))
        handle.flush()
    print(json.dumps({
        "result": result["result"],
        "output": str(arguments.output.resolve()),
        "output_sha256": sha256_path(arguments.output),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
