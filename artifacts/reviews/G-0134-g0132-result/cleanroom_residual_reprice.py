#!/usr/bin/env python3
"""Independent exact repricing for the preregistered G-0134 residual arm.

This checker deliberately does not import or execute the G-0132 producer.  It
reconstructs the signed cut-increment word of each frozen family record and
counts, by a fresh subset dynamic program, every labelled permutation whose
word is a nonzero integer multiple of the audited primitive direction.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
N = 11
DEGREE = 5
FACTORIAL_N = math.factorial(N)
EXPECTED_RECORDS = 163_740
EXPECTED_SELECTED = 176
EXPECTED_ZERO_SELECTED = 44
EXPECTED_TERMS = 132
EXPECTED_DIRECTION = (0, 0, 0, 0, 0, 0, 1, -3, -2, 1, 3)
EXPECTED_REPORTED_COEFFICIENT = int(
    "363926958096805201036820427711562039306502598983761375638772015048"
    "437029843340726060005211433825934240455425251219346437121889771857"
    "125452344913600504791360"
)
EXPECTED_TARGET_SCALE = int(
    "228939300549633824046898265509033533573266869090075154028780928966"
    "372029191484969994311291763985035205029484044477509051690157011675"
    "3181129941246082620"
)

PATHS = {
    "candidate": "artifacts/math/G-0128/full_family_master_result_v2.json",
    "records": "artifacts/math/G-0113/panel_solver_input_v1.json",
    "result": "artifacts/math/G-0132/member_global_normal_form_replay_v1.json",
    "manifest": "artifacts/math/G-0132/member_global_normal_form_manifest_v1.json",
    "source_audit": "artifacts/reviews/G-0133-g0132-source/SOURCE_AUDIT_RECEIPT.json",
    "preregistration": "artifacts/reviews/G-0134-g0132-result/PREREGISTRATION.md",
}

EXPECTED_SHA256 = {
    "candidate": "17c4fd5c8890006feaf5b9b9d6dbd542002dfca80e85b27b2dcacec16ebca838",
    "records": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    "result": "d720d38f98057535f31b06a038bf96c2ea17486431f32d49ae48b2b207a6ff50",
    "manifest": "b4c37ce45d70647a2537ca2e05ecaeb75a47edf29427767a6eff9744f31b0732",
    "source_audit": "8027f630749c3b4ce5611945d63cc526c09042c0b8f66baee1d1e9fc2c61efca",
    "preregistration": "5f0ec755c8aa96bccde392be97e3189f6eb1fc9dfbff508a5ced13ecd9fca6d2",
}

COMMITS = {
    "audit_preregistration": "64866f6dac08a0be897b8decc80d40d76b0046c8",
    "producer": "618c5e7883bf6ee02f1a0f202dbec1f3a9e15a0b",
    "source_audit": "c0d2442ee3fb083c9267380cf40c81417fa0ae02",
    "manifest": "441fd60884c23f4ede7a0689be736fb0fcb37b5d",
    "result": "5d84d6080eabcd833f4f96364ae02d7aeb7d72a3",
}


class AuditFailure(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def exact_int(value: Any, label: str) -> int:
    require(not isinstance(value, bool), f"{label}: boolean is not an integer")
    if isinstance(value, int):
        return value
    require(isinstance(value, str), f"{label}: expected canonical decimal string")
    require(value == "0" or value == "-0" or value.lstrip("-").isdigit(), f"{label}: malformed decimal")
    require(value not in {"-0"} and not value.startswith("+") and not value.startswith("00")
            and not value.startswith("-0"), f"{label}: noncanonical decimal")
    return int(value)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(relative: str) -> Any:
    path = ROOT / relative
    require(path.is_file() and not path.is_symlink(), f"unsafe or missing input: {relative}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def frozen_hashes() -> dict[str, str]:
    observed = {name: sha256_file(ROOT / PATHS[name]) for name in PATHS}
    for name, expected in EXPECTED_SHA256.items():
        require(observed[name] == expected, f"{name} SHA-256 drift")
    return observed


def safe_path(relative: str) -> Path:
    require(isinstance(relative, str) and relative and not Path(relative).is_absolute(), "unsafe path text")
    parts = Path(relative).parts
    require(".." not in parts and "." not in parts, f"unsafe relative path: {relative}")
    current = ROOT
    for part in parts:
        current = current / part
        require(not current.is_symlink(), f"symlink input refused: {relative}")
    resolved = current.resolve(strict=True)
    require(ROOT == resolved or ROOT in resolved.parents, f"path escape: {relative}")
    require(resolved.is_file(), f"not a regular file: {relative}")
    return resolved


def validate_hash_text(value: Any, label: str) -> str:
    require(isinstance(value, str) and len(value) == 64, f"{label}: SHA-256 shape")
    require(value == value.lower() and all(character in "0123456789abcdef" for character in value),
            f"{label}: SHA-256 canonical text")
    return value


def git_output(*arguments: str) -> str:
    process = subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return process.stdout.decode().strip()


def git_is_ancestor(ancestor: str, descendant: str) -> bool:
    process = subprocess.run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return process.returncode == 0


def git_object_exists(commit: str, relative: str) -> bool:
    process = subprocess.run(
        ["git", "cat-file", "-e", f"{commit}:{relative}"], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return process.returncode == 0


def verify_admission(
    manifest: dict[str, Any], result_payload: dict[str, Any], source_audit: dict[str, Any]
) -> dict[str, Any]:
    require(source_audit.get("schema") == "max11-g0133-g0132-source-audit-receipt-v1", "source audit schema")
    require(source_audit.get("verdict") == "PASS", "source audit verdict")
    require(source_audit.get("scientific_manifest_observed") is False, "source audit manifest boundary")
    require(source_audit.get("scientific_output_observed") is False, "source audit output boundary")
    subject = source_audit.get("subject")
    require(isinstance(subject, dict), "source audit subject")
    source = subject.get("source")
    require(isinstance(source, dict) and source.get("git_commit") == COMMITS["producer"], "source commit")

    require(manifest.get("schema") == "max11-g0132-member-global-normal-form-manifest-v1", "manifest schema")
    require(manifest.get("selected_branch") == "MEMBER", "manifest branch")
    require(manifest.get("producer_git_commit") == COMMITS["producer"], "manifest producer commit")
    require(manifest.get("source_audit_git_commit") == COMMITS["source_audit"], "manifest source-audit commit")
    require(manifest.get("preregistration_git_commit") == "6db51f8716d0ba0a82606bddc7573dafd889f2fe",
            "manifest protocol commit")
    require(manifest.get("output_path") == PATHS["result"], "manifest output path")
    parameters = manifest.get("parameters")
    require(isinstance(parameters, dict), "manifest parameters")
    expected_parameters = {
        "n": N, "records": EXPECTED_RECORDS, "rows": 380, "selected_slots": EXPECTED_SELECTED,
        "terms": EXPECTED_TERMS, "carry_directions": 68, "target_coordinate": 10,
        "labelled_permutations": EXPECTED_TERMS * FACTORIAL_N,
    }
    for key, expected in expected_parameters.items():
        require(exact_int(parameters.get(key), f"manifest parameters.{key}") == expected,
                f"manifest parameter {key}")
    require(parameters.get("arithmetic") == "signed_num_bigint_BigInt_unconditional_exact", "manifest arithmetic")

    require(result_payload.get("manifest_path") == PATHS["manifest"], "result manifest path")
    require(result_payload.get("manifest_sha256") == EXPECTED_SHA256["manifest"], "result manifest hash")
    require(result_payload.get("complete_global_replay") is True, "result complete replay flag")
    require(result_payload.get("inputs_rehashed_at_end") is True, "result end rehash flag")
    require(exact_int(result_payload.get("terms"), "result terms") == EXPECTED_TERMS, "result terms")
    require(exact_int(result_payload.get("labelled_permutations_checked"), "result permutation census")
            == EXPECTED_TERMS * FACTORIAL_N, "result permutation census")
    require(result_payload.get("arithmetic") == "signed_num_bigint_BigInt_unconditional_exact", "result arithmetic")
    require(result_payload.get("bindings") == manifest.get("bindings"), "result/manifest binding drift")

    binding_rows: list[tuple[str, str, str]] = []
    manifest_bindings = manifest.get("bindings")
    require(isinstance(manifest_bindings, dict), "manifest bindings")
    for label, entry in manifest_bindings.items():
        require(isinstance(entry, dict), f"binding {label} shape")
        binding_rows.append((f"binding:{label}", entry.get("path"), entry.get("sha256")))
    transitive = manifest.get("transitive_inputs")
    require(isinstance(transitive, list) and len(transitive) == 41, "manifest transitive census")
    for index, entry in enumerate(transitive):
        require(isinstance(entry, dict), f"transitive {index} shape")
        binding_rows.append((f"transitive:{index:03d}", entry.get("path"), entry.get("sha256")))
    audit_artifacts = source_audit.get("audit_artifacts")
    require(isinstance(audit_artifacts, dict), "source audit artifacts")
    for label, entry in audit_artifacts.items():
        require(isinstance(entry, dict), f"source audit artifact {label}")
        binding_rows.append((f"source-audit:{label}", entry.get("path"), entry.get("sha256")))

    observed: dict[str, dict[str, Any]] = {}
    resolved_seen: set[Path] = set()
    for label, relative, expected_hash in binding_rows:
        require(isinstance(relative, str), f"{label}: path")
        expected = validate_hash_text(expected_hash, label)
        resolved = safe_path(relative)
        require(resolved not in resolved_seen, f"duplicate resolved input: {relative}")
        resolved_seen.add(resolved)
        actual = sha256_file(resolved)
        require(actual == expected, f"{label}: content drift for {relative}")
        observed[relative] = {"sha256": actual, "bytes": resolved.stat().st_size}

    ancestry = [
        (COMMITS["audit_preregistration"], COMMITS["producer"]),
        (COMMITS["producer"], COMMITS["source_audit"]),
        (COMMITS["source_audit"], COMMITS["manifest"]),
        (COMMITS["manifest"], COMMITS["result"]),
    ]
    require(all(git_is_ancestor(left, right) for left, right in ancestry), "admission ancestry")
    require(git_output("rev-parse", f'{COMMITS["result"]}^') == COMMITS["manifest"], "result parent is manifest")
    require(not git_object_exists(COMMITS["manifest"], PATHS["result"]), "result pre-existed at manifest commit")
    require(git_object_exists(COMMITS["result"], PATHS["result"]), "result absent at result commit")
    require(not git_object_exists(f'{COMMITS["manifest"]}^', PATHS["manifest"]), "manifest pre-existed")
    require(git_object_exists(COMMITS["manifest"], PATHS["manifest"]), "manifest absent at manifest commit")
    require(git_output("diff-tree", "--no-commit-id", "--name-only", "-r", COMMITS["manifest"])
            == PATHS["manifest"], "manifest commit atomic scope")
    require(git_output("diff-tree", "--no-commit-id", "--name-only", "-r", COMMITS["result"])
            == PATHS["result"], "result commit atomic scope")

    return {
        "source_audit_verdict": "PASS",
        "source_commit": COMMITS["producer"],
        "source_audit_commit": COMMITS["source_audit"],
        "manifest_commit": COMMITS["manifest"],
        "result_commit": COMMITS["result"],
        "strict_ancestry": True,
        "manifest_absent_before_manifest_commit": True,
        "result_absent_at_manifest_commit": True,
        "single_path_manifest_commit": True,
        "single_path_result_commit": True,
        "bound_files": len(observed),
        "files": observed,
    }


def gcd_all(values: Iterable[int]) -> int:
    current = 0
    for value in values:
        current = math.gcd(current, abs(value))
    return current


def active_direction(direction: Sequence[int]) -> bool:
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def validate_direction(direction: Sequence[int]) -> tuple[int, ...]:
    result = tuple(exact_int(value, f"direction[{index}]") for index, value in enumerate(direction))
    require(len(result) == N, "direction length")
    require(sum(result) == 0, "direction must sum to zero")
    first = next((value for value in result if value), None)
    require(first is not None and first > 0, "direction must use first-positive orientation")
    require(gcd_all(result) == 1, "direction must be primitive")
    require(active_direction(result), "direction is linear on the ordered chamber")
    require(max(map(abs, result)) <= DEGREE, "direction exceeds degree-five increment bound")
    return result


def validate_edge(edge: Any, active: int, label: str) -> tuple[int, int]:
    require(isinstance(edge, list) and len(edge) == 2, f"{label}: edge shape")
    u = exact_int(edge[0], f"{label}[0]")
    v = exact_int(edge[1], f"{label}[1]")
    require(0 <= u < v < active, f"{label}: edge must be compact, ordered, and loopless")
    return u, v


def increment_table(record: dict[str, Any]) -> tuple[list[list[int]], int, int]:
    active = exact_int(record.get("active_vertices"), "active_vertices")
    mass = exact_int(record.get("signed_mass"), "signed_mass")
    require(1 <= active <= N and 1 <= mass <= DEGREE, "record active/mass bounds")
    negative_raw = record.get("negative_edges")
    positive_raw = record.get("positive_edges")
    require(isinstance(negative_raw, list) and isinstance(positive_raw, list), "edge lists")
    require(len(negative_raw) == mass and len(positive_raw) == mass, "signed mass edge census")

    matrix = [[0] * active for _ in range(active)]
    for sign, raw_edges, name in ((-1, negative_raw, "negative"), (1, positive_raw, "positive")):
        for index, raw_edge in enumerate(raw_edges):
            u, v = validate_edge(raw_edge, active, f"{name}_edges[{index}]")
            matrix[u][v] += sign
            matrix[v][u] += sign

    states = 1 << active
    table = [[0] * states for _ in range(active)]
    for vertex in range(active):
        row = table[vertex]
        for mask in range(1, states):
            bit = mask & -mask
            other = bit.bit_length() - 1
            row[mask] = row[mask ^ bit] + matrix[vertex][other]
    return table, active, mass


def matching_active_injections(
    table: Sequence[Sequence[int]], active: int, direction: Sequence[int], scale: int
) -> int:
    """Count active-vertex injections; inactive labels are intentionally indistinct here."""

    inactive = N - active
    current: dict[int, int] = {0: 1}
    for rank, coordinate in enumerate(direction):
        expected = scale * coordinate
        following: dict[int, int] = {}
        for mask, count in current.items():
            placed = mask.bit_count()
            inactive_used = rank - placed
            require(0 <= inactive_used <= inactive, "injection-state census")
            if expected == 0 and inactive_used < inactive:
                following[mask] = following.get(mask, 0) + count
            for vertex, increments in enumerate(table):
                bit = 1 << vertex
                if mask & bit == 0 and increments[mask] == expected:
                    new_mask = mask | bit
                    following[new_mask] = following.get(new_mask, 0) + count
        current = following
        if not current:
            return 0
    return current.get((1 << active) - 1, 0)


def record_direction_price(
    record: dict[str, Any], direction: Sequence[int]
) -> tuple[int, dict[str, Any]]:
    table, active, mass = increment_table(record)
    counts: dict[int, int] = {}
    unlabelled_weight = 0
    for scale in range(-DEGREE, DEGREE + 1):
        if scale == 0:
            continue
        count = matching_active_injections(table, active, direction, scale)
        if count:
            counts[scale] = count
            unlabelled_weight += abs(scale) * count

    inactive_factorial = math.factorial(N - active)
    price = unlabelled_weight * inactive_factorial
    active_injections = math.factorial(N) // inactive_factorial
    labelled_census = active_injections * inactive_factorial
    require(labelled_census == FACTORIAL_N, "per-record labelled orbit census")
    return price, {
        "active_vertices": active,
        "signed_mass": mass,
        "matching_active_injections_by_scale": {str(key): value for key, value in sorted(counts.items())},
        "matching_labelled_permutations": sum(counts.values()) * inactive_factorial,
        "inactive_label_factorial": inactive_factorial,
        "labelled_permutations_census": labelled_census,
    }


def prepare_model(record: dict[str, Any]) -> dict[str, Any]:
    table, active, mass = increment_table(record)
    transitions: list[dict[int, tuple[int, ...]]] = []
    raw_transitions: list[tuple[tuple[int, int], ...]] = []
    for mask in range(1 << active):
        by_increment: dict[int, list[int]] = {}
        raw: list[tuple[int, int]] = []
        for vertex, increments in enumerate(table):
            bit = 1 << vertex
            if mask & bit:
                continue
            new_mask = mask | bit
            increment = increments[mask]
            by_increment.setdefault(increment, []).append(new_mask)
            raw.append((new_mask, increment))
        transitions.append({key: tuple(value) for key, value in by_increment.items()})
        raw_transitions.append(tuple(raw))
    inactive_factorial = math.factorial(N - active)
    return {
        "active": active,
        "mass": mass,
        "inactive": N - active,
        "inactive_factorial": inactive_factorial,
        "transitions": transitions,
        "raw_transitions": raw_transitions,
    }


def matching_model_injections(model: dict[str, Any], direction: Sequence[int], scale: int) -> int:
    active = model["active"]
    inactive = model["inactive"]
    transitions = model["transitions"]
    current: dict[int, int] = {0: 1}
    for rank, coordinate in enumerate(direction):
        expected = scale * coordinate
        following: dict[int, int] = {}
        for mask, count in current.items():
            inactive_used = rank - mask.bit_count()
            require(0 <= inactive_used <= inactive, "model injection-state census")
            if expected == 0 and inactive_used < inactive:
                following[mask] = following.get(mask, 0) + count
            for new_mask in transitions[mask].get(expected, ()):
                following[new_mask] = following.get(new_mask, 0) + count
        current = following
        if not current:
            return 0
    return current.get((1 << active) - 1, 0)


def model_direction_price(model: dict[str, Any], direction: Sequence[int]) -> tuple[int, dict[int, int]]:
    max_direction = max(map(abs, direction))
    scale_limit = model["mass"] // max_direction
    counts: dict[int, int] = {}
    weight = 0
    for scale in range(-scale_limit, scale_limit + 1):
        if scale == 0:
            continue
        count = matching_model_injections(model, direction, scale)
        if count:
            counts[scale] = count
            weight += abs(scale) * count
    return weight * model["inactive_factorial"], counts


def model_linear_vector(model: dict[str, Any]) -> tuple[list[int], int]:
    """Sum exact negative-first word corrections over all active injections.

    Inactive labels are indistinguishable during the DP and restored by the
    final factorial multiplier.  Status 0/+1/-1 records the sign of the first
    nonzero cut increment.  Carrying the partial correction vectors gives a
    route distinct from the producer's full-word aggregation.
    """

    active = model["active"]
    inactive = model["inactive"]
    raw_transitions = model["raw_transitions"]
    current: dict[tuple[int, int], tuple[int, list[int]]] = {(0, 0): (1, [0] * N)}
    for rank in range(N):
        following: dict[tuple[int, int], tuple[int, list[int]]] = {}

        def add_transition(mask: int, status: int, count: int, sums: list[int],
                           new_mask: int, increment: int) -> None:
            new_status = status
            if status == 0 and increment:
                new_status = 1 if increment > 0 else -1
            key = (new_mask, new_status)
            prior_count, prior_sums = following.get(key, (0, [0] * N))
            merged = [prior_sums[index] + sums[index] for index in range(N)]
            if new_status == -1:
                merged[rank] += count * increment
            following[key] = (prior_count + count, merged)

        for (mask, status), (count, sums) in current.items():
            inactive_used = rank - mask.bit_count()
            require(0 <= inactive_used <= inactive, "linear injection-state census")
            if inactive_used < inactive:
                add_transition(mask, status, count, sums, mask, 0)
            for new_mask, increment in raw_transitions[mask]:
                add_transition(mask, status, count, sums, new_mask, increment)
        current = following

    full = (1 << active) - 1
    injection_count = 0
    correction = [0] * N
    for status in (0, 1, -1):
        count, sums = current.get((full, status), (0, [0] * N))
        injection_count += count
        if status == -1:
            correction = [left + right for left, right in zip(correction, sums)]
    expected_injections = math.factorial(N) // model["inactive_factorial"]
    require(injection_count == expected_injections, "linear active-injection census")
    base_multiplier = 2 * DEGREE * math.factorial(N - 2)
    linear = [
        base_multiplier * rank + correction[rank] * model["inactive_factorial"]
        for rank in range(N)
    ]
    return linear, injection_count * model["inactive_factorial"]


def enumerate_earlier_degree_directions(target: Sequence[int]) -> list[tuple[int, ...]]:
    first_index = next(index for index, value in enumerate(target) if value)
    require(all(value == 0 for value in target[:first_index]), "target prefix")
    earlier: list[tuple[int, ...]] = []
    for suffix in itertools.product(range(-DEGREE, DEGREE + 1), repeat=N - first_index):
        candidate = (0,) * first_index + suffix
        if candidate >= tuple(target) or sum(candidate) != 0:
            continue
        first = next((value for value in candidate if value), None)
        if first is None or first < 0 or gcd_all(candidate) != 1 or not active_direction(candidate):
            continue
        earlier.append(candidate)
    require(earlier == sorted(set(earlier)), "earlier direction order")
    return earlier


def parse_terms(candidate: dict[str, Any]) -> tuple[list[tuple[int, int]], int]:
    require(candidate.get("schema") == "max11-g0128-full-family-master-result-v2", "candidate schema")
    require(candidate.get("result") == "FULL_FAMILY_380ROW_EXACT_Q_MEMBER", "candidate branch")
    require(exact_int(candidate.get("records"), "records") == EXPECTED_RECORDS, "candidate records")
    require(exact_int(candidate.get("rows"), "rows") == 380, "candidate rows")

    selected = candidate.get("selected_sequences")
    coefficients = candidate.get("integer_coefficients")
    declared_terms = candidate.get("terms")
    require(isinstance(selected, list) and isinstance(coefficients, list), "selected/coefficient arrays")
    require(isinstance(declared_terms, list), "terms array")
    require(len(selected) == len(coefficients) == EXPECTED_SELECTED, "selected slot census")
    selected_int = [exact_int(value, f"selected_sequences[{index}]") for index, value in enumerate(selected)]
    require(selected_int == sorted(set(selected_int)), "selected sequence order/uniqueness")
    require(all(0 <= value < EXPECTED_RECORDS for value in selected_int), "selected sequence range")
    coefficient_int = [exact_int(value, f"integer_coefficients[{index}]") for index, value in enumerate(coefficients)]
    require(sum(value == 0 for value in coefficient_int) == EXPECTED_ZERO_SELECTED, "zero selected census")
    projected = [(sequence, coefficient) for sequence, coefficient in zip(selected_int, coefficient_int) if coefficient]
    require(len(projected) == EXPECTED_TERMS, "nonzero term census")

    parsed_declared: list[tuple[int, int]] = []
    for index, term in enumerate(declared_terms):
        require(isinstance(term, dict), f"terms[{index}] shape")
        parsed_declared.append(
            (exact_int(term.get("sequence"), f"terms[{index}].sequence"),
             exact_int(term.get("coefficient"), f"terms[{index}].coefficient"))
        )
    require(parsed_declared == projected, "declared terms differ from nonzero selected projection")
    target_scale = exact_int(candidate.get("target_scale"), "target_scale")
    require(target_scale == EXPECTED_TARGET_SCALE and target_scale > 0, "target scale")
    require(gcd_all([target_scale, *(coefficient for _, coefficient in projected)]) == 1, "primitive normalization")
    return projected, target_scale


def parse_records(payload: dict[str, Any], needed: set[int]) -> dict[int, dict[str, Any]]:
    require(payload.get("schema") == "max11-g0113-panel-solver-input-v1", "record schema")
    records = payload.get("records")
    require(isinstance(records, list) and len(records) == EXPECTED_RECORDS, "full record census")
    selected: dict[int, dict[str, Any]] = {}
    for expected_sequence, record in enumerate(records):
        require(isinstance(record, dict), f"record {expected_sequence} shape")
        sequence = exact_int(record.get("sequence"), f"record {expected_sequence} sequence")
        require(sequence == expected_sequence, f"record order at {expected_sequence}")
        if sequence in needed:
            selected[sequence] = record
    require(set(selected) == needed, "missing selected records")
    return selected


def reprice(
    terms: Sequence[tuple[int, int]], models: dict[int, dict[str, Any]], direction: Sequence[int],
    *, include_rows: bool = True,
) -> tuple[int, list[dict[str, Any]]]:
    aggregate = 0
    rows: list[dict[str, Any]] = []
    for term_index, (sequence, certificate_coefficient) in enumerate(terms):
        model = models[sequence]
        orbit_price, counts = model_direction_price(model, direction)
        contribution = certificate_coefficient * orbit_price
        aggregate += contribution
        if include_rows:
            rows.append({
                "term_index": term_index,
                "sequence": sequence,
                "certificate_coefficient": str(certificate_coefficient),
                "record_direction_price": orbit_price,
                "weighted_contribution": str(contribution),
                "active_vertices": model["active"],
                "signed_mass": model["mass"],
                "matching_active_injections_by_scale": {
                    str(key): value for key, value in sorted(counts.items())
                },
                "matching_labelled_permutations": sum(counts.values()) * model["inactive_factorial"],
                "inactive_label_factorial": model["inactive_factorial"],
                "labelled_permutations_census": FACTORIAL_N,
            })
    return aggregate, rows


def brute_record_price(record: dict[str, Any], direction: Sequence[int], n: int) -> int:
    """Small-n literal oracle used only by self-test."""

    table, active, _ = increment_table(record)
    require(n == N, "production-shaped brute oracle currently uses N=11")
    total = 0
    active_vertices = tuple(range(active))
    inactive_labels = tuple(range(active, n))
    for permutation in itertools.permutations((*active_vertices, *inactive_labels)):
        mask = 0
        word: list[int] = []
        for label in permutation:
            if label < active:
                word.append(table[label][mask])
                mask |= 1 << label
            else:
                word.append(0)
        first = next((value for value in word if value), 0)
        if not first:
            continue
        divisor = gcd_all(word)
        oriented = tuple((1 if first > 0 else -1) * value // divisor for value in word)
        if oriented == tuple(direction) and active_direction(oriented):
            total += divisor
    return total


def self_test() -> None:
    validate_direction(EXPECTED_DIRECTION)
    require(not active_direction((1, -1, 0, 0, 0, 0, 0, 0, 0, 0, 0)), "inactive fixture")
    bad = list(EXPECTED_DIRECTION)
    bad[-1] += 1
    try:
        validate_direction(bad)
    except AuditFailure:
        pass
    else:
        raise AuditFailure("nonzero-sum mutant accepted")

    # A compact record with nine inactive labels makes the literal 11! oracle
    # too large, so the self-test instead checks the DP's exact scale partition
    # against a hand-derived zero direction mismatch and census identities.
    record = {
        "active_vertices": 2,
        "signed_mass": 1,
        "negative_edges": [[0, 1]],
        "positive_edges": [[0, 1]],
    }
    price, census = record_direction_price(record, EXPECTED_DIRECTION)
    require(price == 0, "cancelled-edge known zero")
    require(census["labelled_permutations_census"] == FACTORIAL_N, "self-test census")


def run(core_only: bool) -> dict[str, Any]:
    hashes_at_start = frozen_hashes()
    candidate = load_json(PATHS["candidate"])
    terms, target_scale = parse_terms(candidate)
    record_payload = load_json(PATHS["records"])
    records = parse_records(record_payload, {sequence for sequence, _ in terms})
    models = {sequence: prepare_model(record) for sequence, record in records.items()}

    result_payload = load_json(PATHS["result"])
    manifest_payload = load_json(PATHS["manifest"])
    source_audit_payload = load_json(PATHS["source_audit"])
    require(result_payload.get("schema") == "max11-g0132-member-global-normal-form-replay-v1", "result schema")
    require(result_payload.get("result") == "MEMBER_EXACT_GLOBAL_NORMAL_FORM_RESIDUAL", "result branch")
    reported = result_payload.get("first_nonzero_hinge")
    require(isinstance(reported, dict), "reported hinge shape")
    direction = validate_direction(reported.get("direction"))
    require(direction == EXPECTED_DIRECTION, "released direction differs from preregistered audit subject")
    reported_coefficient = exact_int(reported.get("coefficient"), "reported coefficient")
    require(reported_coefficient == EXPECTED_REPORTED_COEFFICIENT, "released coefficient drift")

    admission_at_start = None if core_only else verify_admission(
        manifest_payload, result_payload, source_audit_payload
    )

    independent_coefficient, per_term = reprice(terms, models, direction)
    hashes_at_end = frozen_hashes()
    require(hashes_at_end == hashes_at_start, "inputs changed during audit")
    require(sum(row["labelled_permutations_census"] for row in per_term)
            == EXPECTED_TERMS * FACTORIAL_N, "all-term orbit census")

    output: dict[str, Any] = {
        "schema": "max11-g0134-cleanroom-residual-reprice-v1",
        "mode": "core-only" if core_only else "full",
        "direction": list(direction),
        "reported_coefficient": str(reported_coefficient),
        "independent_coefficient": str(independent_coefficient),
        "exact_match": independent_coefficient == reported_coefficient,
        "nonzero": independent_coefficient != 0,
        "terms": len(terms),
        "labelled_permutations_reconciled": len(terms) * FACTORIAL_N,
        "target_scale": str(target_scale),
        "target_subtraction_coordinate_10": str(target_scale * FACTORIAL_N),
        "hinge_target_contribution": "0",
        "per_term": per_term,
        "hashes_at_start": hashes_at_start,
        "hashes_at_end": hashes_at_end,
        "checker_sha256": sha256_file(Path(__file__).resolve()),
    }
    if not core_only:
        candidate_carry = candidate.get("hinge_directions")
        require(isinstance(candidate_carry, list) and len(candidate_carry) == 68, "candidate carry directions")
        carry_directions = [validate_direction(value) for value in candidate_carry]
        require(len(set(carry_directions)) == len(carry_directions), "carry direction uniqueness")
        result_carry = result_payload.get("carry_forward_checks")
        require(isinstance(result_carry, list) and len(result_carry) == 68, "result carry checks")
        for index, (expected_direction, observed) in enumerate(zip(carry_directions, result_carry)):
            require(isinstance(observed, dict), f"carry check {index} shape")
            require(exact_int(observed.get("index"), f"carry check {index} index") == index, "carry index")
            require(validate_direction(observed.get("direction")) == expected_direction, "carry direction drift")
            require(exact_int(observed.get("coefficient"), "carry coefficient") == 0, "reported carry nonzero")
            require(observed.get("exact_zero") is True, "reported carry zero flag")

        earlier_directions = enumerate_earlier_degree_directions(direction)
        require(set(carry_directions).issubset(set(earlier_directions)), "carry direction is not earlier")
        direction_coefficients: dict[tuple[int, ...], int] = {direction: independent_coefficient}
        for index, audit_direction in enumerate(earlier_directions, 1):
            coefficient, _ = reprice(terms, models, audit_direction, include_rows=False)
            direction_coefficients[audit_direction] = coefficient
            if index % 32 == 0:
                print(f"lex-first exact progress: {index}/{len(earlier_directions)}", file=sys.stderr, flush=True)
        lexicographic_first = all(direction_coefficients[value] == 0 for value in earlier_directions)
        require(lexicographic_first, "independent earlier hinge is nonzero")

        carry_receipts = []
        for index, carry_direction in enumerate(carry_directions):
            coefficient = direction_coefficients[carry_direction]
            require(coefficient == 0, f"independent carried direction {index} nonzero")
            carry_receipts.append({"index": index, "direction": list(carry_direction), "coefficient": "0"})

        linear_aggregate = [0] * N
        per_term_linear = []
        for term_index, (sequence, certificate_coefficient) in enumerate(terms):
            linear, labelled_census = model_linear_vector(models[sequence])
            require(labelled_census == FACTORIAL_N, "linear per-term labelled census")
            for index, value in enumerate(linear):
                linear_aggregate[index] += certificate_coefficient * value
            per_term_linear.append({
                "term_index": term_index,
                "sequence": sequence,
                "linear_vector": [str(value) for value in linear],
                "labelled_permutations_census": labelled_census,
            })
        linear_before_target = linear_aggregate.copy()
        linear_aggregate[10] -= target_scale * FACTORIAL_N
        require(linear_aggregate == [0] * N, "independent linear residual after target subtraction")
        reported_linear = result_payload.get("linear_residuals_after_target")
        require(isinstance(reported_linear, list) and [exact_int(value, "reported linear") for value in reported_linear]
                == linear_aggregate, "reported linear residual drift")
        require(exact_int(result_payload.get("target_subtraction_coordinate_10"), "target subtraction")
                == target_scale * FACTORIAL_N, "reported target subtraction")

        def mutation_first(delta_sequence: int, delta_coefficient: int) -> dict[str, Any] | None:
            for audit_direction in [*earlier_directions, direction]:
                record_price, _ = model_direction_price(models[delta_sequence], audit_direction)
                mutated = direction_coefficients[audit_direction] + delta_coefficient * record_price
                if mutated:
                    return {"direction": list(audit_direction), "coefficient": str(mutated)}
            return None

        first_sequence, first_coefficient = terms[0]
        final_sequence, final_coefficient = terms[-1]
        first_plus_one = mutation_first(first_sequence, 1)
        final_plus_one = mutation_first(final_sequence, 1)
        omitted_final = mutation_first(final_sequence, -final_coefficient)
        require(first_plus_one is not None, "first coefficient +1 mutant escaped")
        require(final_plus_one is not None, "final coefficient +1 mutant escaped")
        require(omitted_final is not None, "omitted final term mutant escaped")

        negative_direction_rejected = False
        nonprimitive_direction_rejected = False
        try:
            validate_direction(tuple(-value for value in direction))
        except AuditFailure:
            negative_direction_rejected = True
        try:
            validate_direction(tuple(2 * value for value in direction))
        except AuditFailure:
            nonprimitive_direction_rejected = True
        require(negative_direction_rejected and nonprimitive_direction_rejected, "direction mutants escaped")

        first_model = models[first_sequence]
        first_price, _ = model_direction_price(first_model, direction)
        swapped_record = dict(records[first_sequence])
        swapped_record["negative_edges"] = records[first_sequence]["positive_edges"]
        swapped_record["positive_edges"] = records[first_sequence]["negative_edges"]
        swapped_model = prepare_model(swapped_record)
        swapped_price, _ = model_direction_price(swapped_model, direction)
        original_linear, _ = model_linear_vector(first_model)
        swapped_linear, _ = model_linear_vector(swapped_model)
        require(swapped_price == first_price and swapped_linear == original_linear, "branch-swap invariance")

        permutation = tuple(reversed(range(first_model["active"])))
        relabelled_record = dict(records[first_sequence])
        for edge_key in ("negative_edges", "positive_edges"):
            relabelled_record[edge_key] = [
                sorted((permutation[edge[0]], permutation[edge[1]]))
                for edge in records[first_sequence][edge_key]
            ]
        relabelled_model = prepare_model(relabelled_record)
        relabelled_price, _ = model_direction_price(relabelled_model, direction)
        relabelled_linear, _ = model_linear_vector(relabelled_model)
        require(relabelled_price == first_price and relabelled_linear == original_linear, "relabel invariance")

        output.update({
            "verdict": "CONSISTENT_RESIDUAL",
            "claim_boundary": (
                "The independently exact nonzero residual refutes only the frozen 132-term "
                "coefficient vector. It does not establish family nonmembership, a compiled "
                "two-hidden-layer architecture, MAX11 settlement, REFEREED/FORMALIZED standing, "
                "or a Lean theorem."
            ),
            "lexicographic_first": "VERIFIED",
            "earlier_degree_five_directions_checked": len(earlier_directions),
            "earlier_direction_residuals": [
                {"direction": list(value), "coefficient": str(direction_coefficients[value])}
                for value in earlier_directions
            ],
            "carry_forward_checks": carry_receipts,
            "linear_aggregate_before_target": [str(value) for value in linear_before_target],
            "linear_residuals_after_target": [str(value) for value in linear_aggregate],
            "per_term_linear": per_term_linear,
            "controls": {
                "first_coefficient_plus_one": first_plus_one,
                "final_coefficient_plus_one": final_plus_one,
                "omitted_final_term": omitted_final,
                "reported_coefficient_plus_one_rejected": independent_coefficient != reported_coefficient + 1,
                "target_scale_plus_one_linear_residual": ["0"] * 10 + [str(-FACTORIAL_N)],
                "target_coordinate_10_plus_one_linear_residual": ["0"] * 10 + ["-1"],
                "negative_direction_rejected": negative_direction_rejected,
                "nonprimitive_direction_rejected": nonprimitive_direction_rejected,
                "branch_swap_invariant": True,
                "active_vertex_relabelling_invariant": True,
                "record_omission_or_reorder_rejected_by_full_sequence_census": True,
            },
            "attempt_history": [
                {
                    "attempt": 1,
                    "status": "PASS",
                    "scope": "core exact target-direction reprice",
                    "receipt_written": False,
                },
                {
                    "attempt": 2,
                    "status": "FAIL_CLOSED",
                    "scope": "first full audit pass",
                    "reason": (
                        "audit-side assertion incorrectly required the 68 provenance-ordered "
                        "carried directions to be lexicographically sorted; no receipt written"
                    ),
                    "scientific_mismatch": False,
                },
                {
                    "attempt": 3,
                    "status": "PASS",
                    "scope": "full custody, exact residual, firstness, carried, linear, and mutant audit",
                },
            ],
        })
        admission_at_end = verify_admission(manifest_payload, result_payload, source_audit_payload)
        require(admission_at_start == admission_at_end, "complete custody changed during full audit")
        output["custody"] = {
            "at_start": admission_at_start,
            "at_end_identical": True,
            "fixed_primary_hashes_at_end": hashes_at_end,
        }
    return output


def write_exclusive(path: Path, payload: dict[str, Any]) -> None:
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        path.unlink(missing_ok=True)
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--core-only", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.self_test:
        self_test()
        print("G-0134 clean-room self-test: PASS")
        return
    payload = run(args.core_only)
    if args.output is not None:
        write_exclusive(args.output, payload)
    print(json.dumps({key: payload[key] for key in (
        "direction", "reported_coefficient", "independent_coefficient", "exact_match",
        "nonzero", "terms", "labelled_permutations_reconciled")}, sort_keys=True))


if __name__ == "__main__":
    main()
