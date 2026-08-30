#!/usr/bin/env python3
"""Independent semantic replay of the frozen G-0073 profile witness.

Authorship: SapphireCrane, fresh-context clean-room auditor (Codex/GPT-5).

This file deliberately does not import or execute the G-0073 producer.  It
reconstructs the selected expression columns from the frozen outcome
descriptors and MAX10 certificate using a typed-tree dynamic program, then
checks the emitted rational witness with :class:`fractions.Fraction`.

The replay establishes only equality on the 364 frozen {0,1,2,3}-profiles.
It does not establish a global CPWL identity or independently reconstruct the
unselected 7,849 columns of the registered family.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import struct
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Any


EXPECTED_ARTIFACT_SHA256 = (
    "59b81312f44e98ae61481fcac2e61075d60d187c4bf5b4201a821c44ec3b60bb"
)
EXPECTED_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
EXPECTED_SCRIPT_SHA256 = (
    "333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67"
)
EXPECTED_PREFLIGHT_SHA256 = (
    "05908cba9a9ea47ccda0d07f2fa5af630c38c7031986ede57cb6a78dad611e1d"
)
EXPECTED_PREFLIGHT_SCIENCE_SHA256 = (
    "d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8"
)
EXPECTED_SCIENCE_SHA256 = (
    "6c006df13c7e010128b8f2ce71b5a2eb9e599581d575f262ef8084637ef92f56"
)
EXPECTED_SPARSE_SHA256 = (
    "aa28b03000d18c1471ed7806614fb33f824e63343a7753f39f872905d31b2309"
)
EXPECTED_PROFILE_BYTES_SHA256 = (
    "4a310e81ec054d031bb7438e64f8885939bc0565c05af789f3217741516fd9de"
)
EXPECTED_TARGET_BYTES_SHA256 = (
    "a3d3be16df8de6f25b40e318f656efbee4607806413e72a48b2d276d7f21f4d7"
)
EXPECTED_SELECTED_COLUMNS_SHA256 = (
    "2464581cc6aea5d50b242fdaaf5d841e58535efefba6f1ee74303ad0436bd480"
)
EXPECTED_PIVOT_COLUMNS_SHA256 = (
    "d5365b6312f4929c91f7c97ffdba05f125abc63770623af9d09e1cf08e509ed7"
)
EXPECTED_CLEANROOM_PIVOT_ROWS_SHA256 = (
    "da754b0732654b245e986b7571b8db6be2761986e2f923cea0697b075cb5e801"
)


class AuditError(RuntimeError):
    """Fail-closed clean-room audit error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def canonical_bytes(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_gzip_json(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        value = json.load(handle)
    require(isinstance(value, dict), f"expected JSON object: {path}")
    return value


def components(edges: list[tuple[int, int]]) -> list[tuple[int, ...]]:
    adjacency = {vertex: set() for vertex in range(1, 11)}
    for left, right in edges:
        adjacency[left].add(right)
        adjacency[right].add(left)
    answer: list[tuple[int, ...]] = []
    seen: set[int] = set()
    for initial in range(1, 11):
        if initial in seen:
            continue
        stack = [initial]
        seen.add(initial)
        component: list[int] = []
        while stack:
            vertex = stack.pop()
            component.append(vertex)
            for neighbor in adjacency[vertex]:
                if neighbor not in seen:
                    seen.add(neighbor)
                    stack.append(neighbor)
        answer.append(tuple(sorted(component)))
    return sorted(answer, key=lambda item: (len(item), item))


def eligible_base(term: dict[str, Any]) -> bool:
    pair = term.get("pair")
    if not isinstance(pair, list) or len(pair) != 2:
        return False
    sides: list[list[tuple[int, int]]] = []
    for side in pair:
        if not isinstance(side, list) or len(side) != 4:
            return False
        normalized: list[tuple[int, int]] = []
        for edge in side:
            if not isinstance(edge, list) or len(edge) != 2:
                return False
            left, right = map(int, edge)
            if not (1 <= left <= 10 and 1 <= right <= 10) or left == right:
                return False
            normalized.append(tuple(sorted((left, right))))
        if len(set(normalized)) != 4:
            return False
        sides.append(normalized)
    union = sides[0] + sides[1]
    if len(set(union)) != 8:
        return False
    return sorted(map(len, components(union))) in ([2, 8], [3, 7], [4, 6], [5, 5])


def profiles_and_targets() -> tuple[list[tuple[int, int, int, int]], list[int], list[int]]:
    profiles: list[tuple[int, int, int, int]] = []
    for count_zero in range(12):
        for count_one in range(12 - count_zero):
            for count_two in range(12 - count_zero - count_one):
                count_three = 11 - count_zero - count_one - count_two
                profiles.append((count_zero, count_one, count_two, count_three))
    require(len(profiles) == 364, "profile census drift")
    multiplicities: list[int] = []
    targets: list[int] = []
    for profile in profiles:
        multiplicity = math.factorial(11)
        for count in profile:
            multiplicity //= math.factorial(count)
        highest_level = max(level for level, count in enumerate(profile) if count)
        multiplicities.append(multiplicity)
        targets.append(multiplicity * highest_level)
    require(sum(multiplicities) == 4**11, "profile assignments do not partition the 4-ary cube")
    return profiles, multiplicities, targets


State = tuple[int, int, int, int, int, int]


def rooted_component_dp(expression: dict[str, Any], root: int) -> list[dict[State, int]]:
    """Count branch sums and colour histograms on one rooted forest component."""

    adjacency: dict[int, list[tuple[int, int]]] = {vertex: [] for vertex in range(1, 11)}
    for branch, name in ((0, "left"), (1, "right")):
        for left, right in expression[name]:
            adjacency[left].append((right, branch))
            adjacency[right].append((left, branch))

    parent: dict[int, tuple[int, int]] = {root: (0, -1)}
    order: list[int] = []
    stack = [root]
    while stack:
        vertex = stack.pop()
        order.append(vertex)
        for neighbor, branch in adjacency[vertex]:
            if neighbor == parent[vertex][0]:
                continue
            require(neighbor not in parent, "base union is not a forest")
            parent[neighbor] = (vertex, branch)
            stack.append(neighbor)

    tables: dict[int, list[dict[State, int]]] = {}
    for vertex in reversed(order):
        by_color: list[dict[State, int]] = []
        for color in range(4):
            counts = [0, 0, 0, 0]
            counts[color] = 1
            by_color.append({(*counts, 0, 0): 1})
        for child, branch in adjacency[vertex]:
            if parent.get(child, (None, None))[0] != vertex:
                continue
            child_table = tables[child]
            merged_by_color: list[dict[State, int]] = []
            for color in range(4):
                destination: dict[State, int] = {}
                for left_state, left_multiplicity in by_color[color].items():
                    for child_color in range(4):
                        edge_value = max(color, child_color)
                        increment_left = edge_value if branch == 0 else 0
                        increment_right = edge_value if branch == 1 else 0
                        for right_state, right_multiplicity in child_table[child_color].items():
                            state = (
                                left_state[0] + right_state[0],
                                left_state[1] + right_state[1],
                                left_state[2] + right_state[2],
                                left_state[3] + right_state[3],
                                left_state[4] + right_state[4] + increment_left,
                                left_state[5] + right_state[5] + increment_right,
                            )
                            destination[state] = (
                                destination.get(state, 0)
                                + left_multiplicity * right_multiplicity
                            )
                merged_by_color.append(destination)
            by_color = merged_by_color
        tables[vertex] = by_color
    return tables[root]


def semantic_column(
    expression: dict[str, Any],
    profile_index: dict[tuple[int, int, int, int], int],
    expected_multiplicities: list[int],
) -> list[int]:
    """Compute one exact distinct-assignment profile column by tree DP."""

    anchor = int(expression["anchor"])
    auxiliary = int(expression["auxiliary"])
    orientation = int(expression["orientation"])
    anchor_table = rooted_component_dp(expression, anchor)
    auxiliary_table = rooted_component_dp(expression, auxiliary)
    sums = [0] * 364
    counts = [0] * 364
    for anchor_color in range(4):
        for auxiliary_color in range(4):
            for anchor_state, anchor_multiplicity in anchor_table[anchor_color].items():
                for auxiliary_state, auxiliary_multiplicity in auxiliary_table[
                    auxiliary_color
                ].items():
                    base_counts = [
                        anchor_state[index] + auxiliary_state[index] for index in range(4)
                    ]
                    left_sum = anchor_state[4] + auxiliary_state[4]
                    right_sum = anchor_state[5] + auxiliary_state[5]
                    multiplicity = anchor_multiplicity * auxiliary_multiplicity
                    for new_color in range(4):
                        base_counts[new_color] += 1
                        row = profile_index[tuple(base_counts)]
                        base_counts[new_color] -= 1
                        y_spoke = max(
                            2 * anchor_color, auxiliary_color + new_color
                        )
                        doubled_anchor = 2 * anchor_color
                        if orientation == 0:
                            value = max(
                                left_sum + doubled_anchor, right_sum + y_spoke
                            )
                        else:
                            value = max(
                                left_sum + y_spoke, right_sum + doubled_anchor
                            )
                        sums[row] += multiplicity * value
                        counts[row] += multiplicity
    require(counts == expected_multiplicities, "profile-assignment multiplicity mismatch")
    return sums


def carrier_columns(
    profiles: list[tuple[int, int, int, int]], multiplicities: list[int]
) -> tuple[list[int], list[int]]:
    linear: list[int] = []
    pair_max: list[int] = []
    for profile, total in zip(profiles, multiplicities, strict=True):
        linear_value = Fraction(
            total * sum(level * profile[level] for level in range(4)), 11
        )
        pair_value = Fraction(0)
        for first in range(4):
            for second in range(4):
                probability = Fraction(profile[first], 11) * Fraction(
                    profile[second] - int(first == second), 10
                )
                pair_value += total * probability * max(first, second)
        require(
            linear_value.denominator == pair_value.denominator == 1,
            "carrier profile sum is not integral",
        )
        linear.append(linear_value.numerator)
        pair_max.append(pair_value.numerator)
    return linear, pair_max


def rank_columns_mod(columns: list[list[int]], prime: int) -> tuple[int, list[int]]:
    """Independent column-echelon rank and selected row basis modulo prime."""

    basis: dict[int, list[int]] = {}
    pivot_rows: list[int] = []
    for source in columns:
        vector = [value % prime for value in source]
        for row, basis_vector in basis.items():
            multiplier = vector[row]
            if multiplier:
                vector = [
                    (value - multiplier * basis_value) % prime
                    for value, basis_value in zip(vector, basis_vector, strict=True)
                ]
        row = next((index for index, value in enumerate(vector) if value), None)
        if row is None:
            continue
        inverse = pow(vector[row], -1, prime)
        vector = [(value * inverse) % prime for value in vector]
        basis[row] = vector
        pivot_rows.append(row)
    return len(basis), pivot_rows


def verify_bindings(repo: Path, outcome: dict[str, Any]) -> int:
    bindings = outcome.get("bindings")
    require(isinstance(bindings, dict), "outcome bindings missing")
    for name, binding in bindings.items():
        path = Path(str(binding["path"]).replace("$REPO", str(repo)))
        require(path.is_file(), f"binding missing: {name}: {path}")
        require(sha256_path(path) == binding["sha256"], f"binding digest drift: {name}")
        if "bytes" in binding:
            require(path.stat().st_size == binding["bytes"], f"binding size drift: {name}")
    return len(bindings)


def run(repo: Path, artifact: Path, certificate_path: Path) -> dict[str, Any]:
    started = time.monotonic()
    require(sha256_path(artifact) == EXPECTED_ARTIFACT_SHA256, "outcome artifact digest drift")
    require(
        sha256_path(certificate_path) == EXPECTED_CERTIFICATE_SHA256,
        "MAX10 certificate digest drift",
    )
    require(
        sha256_path(repo / "artifacts/math/G-0073/y_spoke_profile_gate.py")
        == EXPECTED_SCRIPT_SHA256,
        "frozen producer digest drift",
    )
    require(
        sha256_path(repo / "artifacts/math/G-0073/y_spoke_orbit_preflight_v1.json.gz")
        == EXPECTED_PREFLIGHT_SHA256,
        "preflight artifact digest drift",
    )

    outcome = load_gzip_json(artifact)
    preflight = load_gzip_json(
        repo / "artifacts/math/G-0073/y_spoke_orbit_preflight_v1.json.gz"
    )
    require(
        preflight.get("scientific_payload_sha256") == EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "preflight scientific payload drift",
    )
    require(
        outcome.get("preflight_scientific_payload_sha256")
        == EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "outcome does not bind the frozen preflight",
    )
    science = {
        key: outcome[key]
        for key in (
            "decision",
            "matrix",
            "preflight_scientific_payload_sha256",
            "schema",
            "subject",
        )
    }
    require(sha256_bytes(canonical_bytes(science)) == EXPECTED_SCIENCE_SHA256, "science digest drift")
    binding_count = verify_bindings(repo, outcome)

    certificate = json.loads(certificate_path.read_text(encoding="utf-8"))
    require(certificate.get("n") == 10, "certificate dimension drift")
    terms = certificate.get("terms")
    require(isinstance(terms, list), "certificate terms missing")
    bases = [(index, term) for index, term in enumerate(terms) if eligible_base(term)]
    require(len(bases) == 252, "eligible MAX10 base census drift")
    topology: dict[str, int] = {}
    raw_seeds: list[tuple[int, int, int, int, int]] = []
    for base_position, (term_index, term) in enumerate(bases):
        forest_components = components(
            [tuple(sorted(edge)) for side in term["pair"] for edge in side]
        )
        key = "+".join(map(str, map(len, forest_components)))
        topology[key] = topology.get(key, 0) + 1
        component_of = {
            vertex: set(component)
            for component in forest_components
            for vertex in component
        }
        for anchor in range(1, 11):
            for auxiliary in sorted(set(range(1, 11)) - component_of[anchor]):
                for orientation in (0, 1):
                    raw_seeds.append(
                        (base_position, term_index, anchor, auxiliary, orientation)
                    )
    require(topology == {"2+8": 168, "3+7": 39, "4+6": 32, "5+5": 13}, "topology census drift")
    require(len(raw_seeds) == 18_400, "raw seed census drift")

    solution = outcome["decision"]["exact_profile_solution"]
    sparse = solution["sparse_coefficients"]
    require(sha256_bytes(canonical_bytes(sparse)) == EXPECTED_SPARSE_SHA256, "sparse witness digest drift")
    orbit_items = [
        item
        for item in sparse
        if item["descriptor"]["kind"] == "Y-spoke-orbit-representative"
    ]
    carrier_items = [
        item for item in sparse if item["descriptor"]["kind"] == "carrier"
    ]
    require(len(orbit_items) == 256 and len(carrier_items) == 1, "witness support shape drift")
    require(
        [item["column_index"] for item in orbit_items] == list(range(256)),
        "selected orbit-column sequence drift",
    )
    require(
        carrier_items[0]["column_index"] == 8105
        and carrier_items[0]["descriptor"]
        == {"kind": "carrier", "name": "C_E", "representative": "max(x_1,x_2)"},
        "selected carrier convention drift",
    )

    for item in orbit_items:
        representative = item["descriptor"]["representative"]
        expression = representative["expression"]
        base_position = int(representative["base_position"])
        term_index = int(representative["base_term_index"])
        require(0 <= base_position < len(bases), "selected base position outside census")
        require(bases[base_position][0] == term_index, "base-position/term-index mismatch")
        require(
            bases[base_position][1]["pair"] == [expression["left"], expression["right"]],
            "selected expression does not match certificate term",
        )
        raw_index = int(representative["raw_index"])
        expected_seed = (
            base_position,
            term_index,
            int(expression["anchor"]),
            int(expression["auxiliary"]),
            int(expression["orientation"]),
        )
        require(raw_seeds[raw_index] == expected_seed, "selected raw-index binding mismatch")
        forest_components = components(
            [
                tuple(sorted(edge))
                for side in (expression["left"], expression["right"])
                for edge in side
            ]
        )
        require(
            not any(
                expression["anchor"] in component
                and expression["auxiliary"] in component
                for component in forest_components
            ),
            "selected anchor and auxiliary are not cross-component",
        )
        require(
            expression["new_label"] == 11 and expression["orientation"] in (0, 1),
            "selected expression metadata drift",
        )

    profiles, multiplicities, targets = profiles_and_targets()
    profile_bytes = b"".join(
        struct.pack("<h", count) for profile in profiles for count in profile
    )
    target_bytes = b"".join(struct.pack("<q", target) for target in targets)
    require(sha256_bytes(profile_bytes) == EXPECTED_PROFILE_BYTES_SHA256, "profile byte digest drift")
    require(sha256_bytes(target_bytes) == EXPECTED_TARGET_BYTES_SHA256, "target byte digest drift")
    require(
        sha256_bytes(canonical_bytes([list(profile) for profile in profiles]))
        == outcome["matrix"]["profile_manifest_sha256"],
        "profile manifest drift",
    )

    profile_index = {profile: index for index, profile in enumerate(profiles)}
    orbit_columns: list[list[int]] = []
    for index, item in enumerate(orbit_items, start=1):
        expression = item["descriptor"]["representative"]["expression"]
        orbit_columns.append(
            semantic_column(expression, profile_index, multiplicities)
        )
        if index % 32 == 0:
            print(
                f"clean-room columns: {index}/256; elapsed={time.monotonic() - started:.1f}s",
                file=sys.stderr,
                flush=True,
            )

    linear_carrier, pair_carrier = carrier_columns(profiles, multiplicities)
    witness_columns = orbit_columns + [pair_carrier]
    coefficients = [Fraction(item["coefficient"]) for item in orbit_items] + [
        Fraction(carrier_items[0]["coefficient"])
    ]
    residuals: list[Fraction] = []
    for row, target in enumerate(targets):
        value = sum(
            (
                coefficient * column[row]
                for coefficient, column in zip(
                    coefficients, witness_columns, strict=True
                )
            ),
            Fraction(0),
        )
        residuals.append(value - target)
    require(not any(residuals), "exact Fraction witness residual is nonzero")

    selected_hasher = hashlib.sha256()
    for column in witness_columns:
        for value in column:
            selected_hasher.update(struct.pack("<q", value))
    selected_digest = selected_hasher.hexdigest()
    require(
        selected_digest == EXPECTED_SELECTED_COLUMNS_SHA256,
        "clean-room selected-column digest drift",
    )

    pivot_column_indices = [*range(256), 8104, 8105]
    require(
        sha256_bytes(canonical_bytes(pivot_column_indices))
        == EXPECTED_PIVOT_COLUMNS_SHA256,
        "registered pivot-column digest drift",
    )
    pivot_columns = orbit_columns + [linear_carrier, pair_carrier]
    rank_results: list[dict[str, Any]] = []
    for prime in (1_000_003, 1_000_033, 1_000_037):
        rank, rows = rank_columns_mod(pivot_columns, prime)
        row_digest = sha256_bytes(canonical_bytes(rows))
        require(rank == 258, f"selected pivot rank below 258 at {prime}")
        require(
            row_digest == EXPECTED_CLEANROOM_PIVOT_ROWS_SHA256,
            f"clean-room pivot-row digest drift at {prime}",
        )
        rank_results.append(
            {"prime": prime, "rank": rank, "cleanroom_pivot_rows_sha256": row_digest}
        )

    return {
        "verdict": "PASS_BOUNDED_CLEANROOM_SEMANTIC_REPLAY",
        "authorship": {
            "agent": "SapphireCrane",
            "role": "fresh-context clean-room auditor",
            "model_lineage": "Codex/GPT-5; same-lineage T1, not T2",
        },
        "artifact_sha256": EXPECTED_ARTIFACT_SHA256,
        "scientific_payload_sha256": EXPECTED_SCIENCE_SHA256,
        "sparse_coefficients_sha256": EXPECTED_SPARSE_SHA256,
        "binding_count": binding_count,
        "eligible_base_count": len(bases),
        "raw_seed_count": len(raw_seeds),
        "selected_descriptor_errors": 0,
        "profile_rows": len(profiles),
        "total_distinct_assignments": sum(multiplicities),
        "selected_witness_columns": len(witness_columns),
        "selected_columns_int64_columnmajor_sha256": selected_digest,
        "fraction_residual_nonzero_rows": 0,
        "pivot_columns": len(pivot_columns),
        "pivot_rank_results": rank_results,
        "claim_boundary": (
            "Exact equality of the emitted 257-term rational combination on the 364 "
            "frozen {0,1,2,3} symmetric profiles only. This is not a global CPWL "
            "identity, a MAX11 network certificate, an unrestricted depth result, or "
            "an independent upper-bound audit of the full 8,107-column matrix rank."
        ),
        "elapsed_seconds": round(time.monotonic() - started, 3),
    }


def main() -> int:
    default_repo = Path(__file__).resolve().parents[3]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=default_repo)
    parser.add_argument(
        "--artifact",
        type=Path,
        default=Path("artifacts/math/G-0073/y_spoke_profile_gate_v1.json.gz"),
    )
    parser.add_argument(
        "--certificate",
        type=Path,
        default=Path("subjects/max-relu-known/certificates/certificate_10_4.json"),
    )
    arguments = parser.parse_args()
    repo = arguments.repo.resolve()
    artifact = arguments.artifact
    certificate = arguments.certificate
    if not artifact.is_absolute():
        artifact = repo / artifact
    if not certificate.is_absolute():
        certificate = repo / certificate
    result = run(repo, artifact, certificate)
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (AuditError, KeyError, IndexError, TypeError, ValueError) as error:
        print(f"CLEANROOM AUDIT FAIL: {error}", file=sys.stderr)
        raise SystemExit(1) from error
