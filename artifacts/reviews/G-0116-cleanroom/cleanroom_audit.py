#!/usr/bin/env python3
"""Independent semantic and structural audit of the frozen G-0116 gate."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
INPUT = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
ROWS = ROOT / "artifacts/math/G-0111/dual_rows_v1.json"
SOURCE = ROOT / "artifacts/math/G-0116/src/main.rs"
OFFICIAL = ROOT / "artifacts/math/G-0116/cycle_cut_panel_benchmark_v1.json"
FROZEN = {
    INPUT: "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    ROWS: "0b849d7dbb171367d9a55ad4b6da4631b4278caa38d9b5f9cbda04c6cb80535c",
    SOURCE: "875b0046e24f32d9649fe0d9c5295dfbd75678fea46df96f6d9f287c6a987bfd",
    OFFICIAL: "94d54b1a64340ff49d6bbdf35cc429e71a25628ba6764b16039d15c258176310",
}
N = 11
DEGREE = 5
COLORS = 4
DIRECT_SEQUENCES = (0, 3)
DIRECT_ROWS = (0, 150, 300)


class AuditFailure(RuntimeError):
    """A frozen binding, invariant, or semantic equality failed."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while block := handle.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        json.dump(value, handle, indent=2, sort_keys=True)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def canonical_edge(edge: Sequence[int], active: int) -> tuple[int, int]:
    if len(edge) != 2:
        raise AuditFailure("edge arity drift")
    u, v = map(int, edge)
    if not (0 <= u < v < active):
        raise AuditFailure("edge is not compact canonical loopless")
    return u, v


def dsu_beta_and_feedback_witness(
    active: int, support: set[tuple[int, int]]
) -> tuple[int, set[int]]:
    parent = list(range(active))

    def find(value: int) -> int:
        while parent[value] != value:
            parent[value] = parent[parent[value]]
            value = parent[value]
        return value

    non_tree: list[tuple[int, int]] = []
    for u, v in sorted(support):
        first, second = find(u), find(v)
        if first == second:
            non_tree.append((u, v))
        else:
            parent[first] = second
    components = len({find(vertex) for vertex in range(active)}) if active else 0
    beta = len(support) + components - active if active else 0
    if beta != len(non_tree):
        raise AuditFailure("cycle-rank/forest partition disagreement")
    # One endpoint of each non-tree edge is a feedback set: after deleting it,
    # every surviving edge belongs to the chosen spanning forest.
    removed = {u for u, _ in non_tree}
    check_parent = list(range(active))

    def check_find(value: int) -> int:
        while check_parent[value] != value:
            check_parent[value] = check_parent[check_parent[value]]
            value = check_parent[value]
        return value

    for u, v in sorted(support):
        if u in removed or v in removed:
            continue
        first, second = check_find(u), check_find(v)
        if first == second:
            raise AuditFailure("constructive feedback witness left a cycle")
        check_parent[first] = second
    if len(removed) > beta:
        raise AuditFailure("feedback witness exceeded cycle rank")
    return beta, removed


def audit_records(records: list[dict[str, object]]) -> dict[str, object]:
    if len(records) != 163_740:
        raise AuditFailure("record census drift")
    beta_histogram: Counter[int] = Counter()
    active_histogram: Counter[int] = Counter()
    mass_histogram: Counter[int] = Counter()
    maximum_witness = 0
    for sequence, record in enumerate(records):
        if int(record["sequence"]) != sequence:
            raise AuditFailure("sequence drift")
        mass = int(record["signed_mass"])
        active = int(record["active_vertices"])
        if not (0 <= mass <= DEGREE and 0 <= active <= N):
            raise AuditFailure("mass/active bound drift")
        negative = [canonical_edge(edge, active) for edge in record["negative_edges"]]
        positive = [canonical_edge(edge, active) for edge in record["positive_edges"]]
        if len(negative) != mass or len(positive) != mass:
            raise AuditFailure("equal occurrence mass drift")
        if set(negative) & set(positive):
            raise AuditFailure("cancelled sides retain a common edge")
        endpoints = {vertex for edge in negative + positive for vertex in edge}
        expected_active = max(endpoints) + 1 if endpoints else 0
        if active != expected_active or endpoints != set(range(active)):
            raise AuditFailure("compact active support drift")
        support = set(negative) | set(positive)
        beta, witness = dsu_beta_and_feedback_witness(active, support)
        if beta > 4:
            raise AuditFailure("absolute cycle rank exceeds frozen gate")
        maximum_witness = max(maximum_witness, len(witness))
        beta_histogram[beta] += 1
        active_histogram[active] += 1
        mass_histogram[mass] += 1
    return {
        "records": len(records),
        "mass_histogram": dict(sorted(mass_histogram.items())),
        "active_histogram": dict(sorted(active_histogram.items())),
        "absolute_cycle_rank_histogram": dict(sorted(beta_histogram.items())),
        "maximum_absolute_cycle_rank": max(beta_histogram),
        "maximum_constructive_feedback_witness": maximum_witness,
        "all_cancelled_sides_disjoint": True,
        "all_compact_loopless": True,
    }


def audit_rows(rows: list[dict[str, object]], target: Sequence[int]) -> dict[str, object]:
    if len(rows) != 301 or len(target) != 301:
        raise AuditFailure("row/target census drift")
    targets: list[int] = []
    profiles: set[tuple[int, ...]] = set()
    for row in rows:
        levels = tuple(map(int, row["levels"]))
        profile = tuple(map(int, row["profile"]))
        if len(levels) != COLORS or levels[0] != 0 or any(
            one >= two for one, two in zip(levels, levels[1:])
        ):
            raise AuditFailure("row levels are not strict four-level panels")
        if len(profile) != COLORS or sum(profile) != N or min(profile) <= 0:
            raise AuditFailure("formal profile drift")
        stabilizer = math.prod(math.factorial(count) for count in profile)
        if int(row["formal_stabilizer"]) != stabilizer:
            raise AuditFailure("formal stabilizer drift")
        targets.append(math.factorial(N) // stabilizer * levels[-1])
        profiles.add(profile)
    if targets != list(map(int, target)):
        raise AuditFailure("prepared target normalization drift")
    target_bytes = np.asarray(targets, dtype="<i8").tobytes()
    return {
        "rows": len(rows),
        "positive_formal_profiles": len(profiles),
        "target_int64_le_sha256": hashlib.sha256(target_bytes).hexdigest(),
        "formal_stabilizers_exact": True,
        "strict_zero_based_levels": True,
    }


def ordered_pair_sum(levels: Sequence[int], profile: Sequence[int]) -> int:
    total = 0
    for first in range(COLORS):
        for second in range(COLORS):
            if profile[first] == 0 or profile[second] == 0:
                continue
            if first == second and profile[first] < 2:
                continue
            remainder = list(profile)
            remainder[first] -= 1
            remainder[second] -= 1
            multiplicity = math.factorial(N - 2) // math.prod(
                math.factorial(count) for count in remainder
            )
            total += multiplicity * max(levels[first], levels[second])
    return total


def branch_state_histogram(record: dict[str, object]) -> dict[int, int]:
    """Enumerate active colours and retain both branch edge-count words."""
    active = int(record["active_vertices"])
    negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]
    positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]
    assignments = 1 << (2 * active)
    histogram: defaultdict[int, int] = defaultdict(int)
    chunk = 1 << 18
    shifts = (2 * np.arange(active, dtype=np.uint64))[None, :]
    for start in range(0, assignments, chunk):
        stop = min(start + chunk, assignments)
        codes = np.arange(start, stop, dtype=np.uint64)[:, None]
        colors = ((codes >> shifts) & np.uint64(3)).astype(np.uint8)
        count_word = np.zeros(stop - start, dtype=np.uint64)
        for color in range(COLORS):
            counts = np.count_nonzero(colors == color, axis=1).astype(np.uint64)
            count_word |= counts << np.uint64(4 * color)

        def edge_word(edges: Iterable[tuple[int, int]]) -> np.ndarray:
            word = np.zeros(stop - start, dtype=np.uint64)
            for u, v in edges:
                category = np.maximum(colors[:, u], colors[:, v]).astype(np.uint64)
                word += np.left_shift(np.uint64(1), 3 * category)
            return word

        packed = count_word | (edge_word(negative) << np.uint64(16))
        packed |= edge_word(positive) << np.uint64(28)
        keys, multiplicities = np.unique(packed, return_counts=True)
        for key, multiplicity in zip(keys.tolist(), multiplicities.tolist(), strict=True):
            histogram[int(key)] += int(multiplicity)
    if sum(histogram.values()) != assignments:
        raise AuditFailure("literal active-colour census drift")
    return dict(histogram)


def decode_state(key: int) -> tuple[tuple[int, ...], tuple[int, ...], tuple[int, ...]]:
    counts = tuple((key >> (4 * color)) & 15 for color in range(COLORS))
    negative = tuple((key >> (16 + 3 * color)) & 7 for color in range(COLORS))
    positive = tuple((key >> (28 + 3 * color)) & 7 for color in range(COLORS))
    return counts, negative, positive


def literal_panel_vector(
    record: dict[str, object], rows: list[dict[str, object]]
) -> tuple[list[int], dict[int, int]]:
    histogram = branch_state_histogram(record)
    grouped: defaultdict[tuple[int, ...], list[tuple[tuple[int, ...], tuple[int, ...], int]]]
    grouped = defaultdict(list)
    for key, multiplicity in histogram.items():
        counts, negative, positive = decode_state(key)
        grouped[counts].append((negative, positive, multiplicity))
    inactive = N - int(record["active_vertices"])
    mass = int(record["signed_mass"])
    vector: list[int] = []
    represented_by_row: dict[int, int] = {}
    for row_index, row in enumerate(rows):
        levels = tuple(map(int, row["levels"]))
        profile = tuple(map(int, row["profile"]))
        nonlinear = 0
        represented = 0
        for counts, states in grouped.items():
            if any(count > bound for count, bound in zip(counts, profile, strict=True)):
                continue
            remainder = tuple(
                bound - count for count, bound in zip(counts, profile, strict=True)
            )
            if sum(remainder) != inactive:
                continue
            fill = math.factorial(inactive) // math.prod(
                math.factorial(count) for count in remainder
            )
            for negative, positive, multiplicity in states:
                first = sum(count * level for count, level in zip(negative, levels, strict=True))
                second = sum(count * level for count, level in zip(positive, levels, strict=True))
                weight = multiplicity * fill
                nonlinear += weight * max(first, second)
                represented += weight
        expected = math.factorial(N) // int(row["formal_stabilizer"])
        if represented != expected:
            raise AuditFailure(f"literal formal census drift at row {row_index}")
        common = (DEGREE - mass) * ordered_pair_sum(levels, profile)
        vector.append(nonlinear + common)
        represented_by_row[row_index] = represented
    return vector, represented_by_row


def direct_formal_assignment_value(
    record: dict[str, object], row: dict[str, object]
) -> tuple[int, int]:
    """Literal full-label recursion; no histogram, signed q, or ReLU rewrite."""
    levels = tuple(map(int, row["levels"]))
    remaining = list(map(int, row["profile"]))
    colors = [0] * N
    negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]
    positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]
    common_count = DEGREE - int(record["signed_mass"])
    total = 0
    assignments = 0

    def recurse(vertex: int) -> None:
        nonlocal total, assignments
        if vertex == N:
            first = sum(max(levels[colors[u]], levels[colors[v]]) for u, v in negative)
            second = sum(max(levels[colors[u]], levels[colors[v]]) for u, v in positive)
            common = common_count * max(levels[colors[0]], levels[colors[1]])
            total += max(first, second) + common
            assignments += 1
            return
        for color in range(COLORS):
            if remaining[color] == 0:
                continue
            remaining[color] -= 1
            colors[vertex] = color
            recurse(vertex + 1)
            remaining[color] += 1

    recurse(0)
    expected = math.factorial(N) // int(row["formal_stabilizer"])
    if assignments != expected:
        raise AuditFailure("direct formal-assignment census drift")
    return total, assignments


def i128_vector_sha256(vector: Sequence[int]) -> str:
    digest = hashlib.sha256()
    for value in vector:
        digest.update(int(value).to_bytes(16, byteorder="little", signed=True))
    return digest.hexdigest()


def run(output: Path) -> dict[str, object]:
    observed_bindings = {str(path.relative_to(ROOT)): sha256_path(path) for path in FROZEN}
    for path, expected in FROZEN.items():
        if observed_bindings[str(path.relative_to(ROOT))] != expected:
            raise AuditFailure(f"frozen SHA-256 drift: {path}")
    input_document = json.loads(INPUT.read_text(encoding="utf-8"))
    rows_document = json.loads(ROWS.read_text(encoding="utf-8"))
    official = json.loads(OFFICIAL.read_text(encoding="utf-8"))
    if input_document.get("schema") != "max11-g0113-panel-solver-input-v1":
        raise AuditFailure("input schema drift")
    if rows_document.get("schema") != "max11-g0111-actual-dual-rows-v1":
        raise AuditFailure("row schema drift")
    if official.get("result") != "PASS_ACCELERATOR_GATE":
        raise AuditFailure("official G-0116 gate is not passing")
    official_bindings = official.get("bindings", {})
    if official_bindings != {
        "input": FROZEN[INPUT],
        "producer": FROZEN[SOURCE],
        "rows": FROZEN[ROWS],
    }:
        raise AuditFailure("official report binding drift")
    records = input_document["records"]
    rows = rows_document["rows"]
    structural = audit_records(records)
    row_audit = audit_rows(rows, input_document["target"])
    official_controls = {int(item["sequence"]): item for item in official["controls"]}
    direct_results: dict[str, object] = {}
    for sequence in DIRECT_SEQUENCES:
        vector, represented = literal_panel_vector(records[sequence], rows)
        vector_hash = i128_vector_sha256(vector)
        if vector_hash != official_controls[sequence]["panel_vector_sha256"]:
            raise AuditFailure(f"literal vector hash disagreement at sequence {sequence}")
        direct_rows: dict[str, object] = {}
        for row_index in DIRECT_ROWS:
            literal, assignments = direct_formal_assignment_value(
                records[sequence], rows[row_index]
            )
            if literal != vector[row_index] or assignments != represented[row_index]:
                raise AuditFailure(
                    f"direct formal assignment disagreement at sequence {sequence}, row {row_index}"
                )
            direct_rows[str(row_index)] = {
                "value": literal,
                "formal_assignments": assignments,
            }
        direct_results[str(sequence)] = {
            "active_vertices": int(records[sequence]["active_vertices"]),
            "signed_mass": int(records[sequence]["signed_mass"]),
            "literal_panel_vector_sha256": vector_hash,
            "official_panel_vector_sha256": official_controls[sequence]["panel_vector_sha256"],
            "direct_formal_rows": direct_rows,
        }
    report = {
        "schema": "max11-g0116-cleanroom-audit-v1",
        "result": "PASS_BOUNDED",
        "bindings": observed_bindings,
        "record_audit": structural,
        "row_audit": row_audit,
        "literal_semantic_controls": direct_results,
        "shared-code_evidence_limit": (
            "G-0116 cycle-cut/exhaustive agreement shares signed-edge, signed-q, and panel-folding "
            "code; this clean-room literal branch-max route supplies the independent semantic leg."
        ),
        "claim_boundary": (
            "The exact frozen G-0116 evaluator semantics are corroborated on controls 0 and 3, "
            "and every frozen input record satisfies the low-cycle structural precondition. This "
            "does not execute the 163,740-column rank scan, establish panel membership, prove a "
            "global identity or completeness theorem, or settle MAX11."
        ),
    }
    write_exclusive(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path, default=HERE / "cleanroom_audit_v1.json"
    )
    args = parser.parse_args()
    report = run(args.output.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
