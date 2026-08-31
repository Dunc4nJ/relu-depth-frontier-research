#!/usr/bin/env python3
"""Independent post-fix controls for the G-0117 exact replay and lemma seam."""

from __future__ import annotations

from collections import defaultdict
import hashlib
from itertools import permutations
import json
import math
import os
from pathlib import Path
from typing import Iterable


N = 11
FACTORIAL_N = math.factorial(N)
PRIMES = (1_000_000_007, 1_000_000_009)
FIRST_DIRECTION = (0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1)
EXPECTED_HASHES = {
    "exact_executable": "3dcb3b43c4075f1206ecda874bd9013dd9328eb67e1b9a2f59b21391882c4574",
    "exact_source": "1232548952fee91827f8dfddf26dd01eacfc49c57a448f6d258add9b778f414a",
    "modular_executable": "7c8c83b668026e1e15be89a1459c8e23c79937582d245464ce0a6b5e49b9925b",
    "modular_source": "d27ece785362d84aea134e04893449f4bca926243aba29ec4fef377fb7a7003e",
    "kernel": "84b37ea50f012bfe8310de84b1ca27a7c1b77de90978635dd483798759d4c6aa",
    "uniqueness_lemma": "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17",
    "exact_preregistration": "a76f3ee0bf77f8c5a2180830b2879cf9b1b75fbac797a166a19fb605706a0a12",
}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(value, dict)
    return value


def gcd_word(word: Iterable[int]) -> int:
    value = 0
    for coordinate in word:
        value = math.gcd(value, abs(coordinate))
    return value


def normalized_direction(word: tuple[int, ...]) -> tuple[int, ...] | None:
    first = next((value for value in word if value), None)
    if first is None:
        return None
    divisor = gcd_word(word)
    sign = 1 if first > 0 else -1
    return tuple(sign * value // divisor for value in word)


def active_direction(direction: tuple[int, ...]) -> bool:
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def signed_matrix(record: dict[str, object]) -> list[list[int]]:
    active = int(record["active_vertices"])
    matrix = [[0] * active for _ in range(active)]
    for sign, name in ((-1, "negative_edges"), (1, "positive_edges")):
        for edge in record[name]:
            u, v = map(int, edge)
            matrix[u][v] += sign
            matrix[v][u] += sign
    return matrix


def increments_table(record: dict[str, object]) -> list[list[int]]:
    active = int(record["active_vertices"])
    matrix = signed_matrix(record)
    table = [[0] * (1 << active) for _ in range(active)]
    for vertex in range(active):
        for mask in range(1, 1 << active):
            bit = mask & -mask
            other = bit.bit_length() - 1
            table[vertex][mask] = table[vertex][mask ^ bit] + matrix[vertex][other]
    return table


def matching_injections(
    table: list[list[int]], active: int, direction: tuple[int, ...], scale: int
) -> int:
    full = (1 << active) - 1
    inactive = N - active
    current = [0] * (1 << active)
    current[0] = 1
    for rank, coordinate in enumerate(direction):
        expected = scale * coordinate
        following = [0] * (1 << active)
        for mask, count in enumerate(current):
            if not count:
                continue
            placed = mask.bit_count()
            if placed > rank:
                continue
            inactive_used = rank - placed
            if expected == 0 and inactive_used < inactive:
                following[mask] += count
            for vertex in range(active):
                bit = 1 << vertex
                if not mask & bit and table[vertex][mask] == expected:
                    following[mask | bit] += count
        current = following
    return current[full]


def targeted_hinge_coefficient(record: dict[str, object], direction: tuple[int, ...]) -> int:
    assert sum(direction) == 0
    assert gcd_word(direction) == 1
    assert next(value for value in direction if value) > 0
    assert active_direction(direction)
    active = int(record["active_vertices"])
    table = increments_table(record)
    unlabelled = sum(
        abs(scale) * matching_injections(table, active, direction, scale)
        for scale in range(-5, 6)
        if scale
    )
    return unlabelled * math.factorial(N - active)


def linear_vector_dp(record: dict[str, object]) -> list[int]:
    active = int(record["active_vertices"])
    inactive = N - active
    table = increments_table(record)
    current = [[0, 0, 0] for _ in range(1 << active)]
    current[0][0] = 1
    correction = [0] * N
    for rank in range(N):
        following = [[0, 0, 0] for _ in range(1 << active)]
        for mask, counts in enumerate(current):
            placed = mask.bit_count()
            if placed > rank:
                continue
            inactive_used = rank - placed
            for status, count in enumerate(counts):
                if not count:
                    continue
                if inactive_used < inactive:
                    following[mask][status] += count
                for vertex in range(active):
                    bit = 1 << vertex
                    if mask & bit:
                        continue
                    increment = table[vertex][mask]
                    new_status = status
                    if status == 0 and increment:
                        new_status = 1 if increment > 0 else 2
                    new_mask = mask | bit
                    following[new_mask][new_status] += count
                    if new_status == 2:
                        remaining_slots = N - rank - 1
                        remaining_active = active - new_mask.bit_count()
                        remaining_inactive = remaining_slots - remaining_active
                        completions = math.factorial(remaining_slots) // math.factorial(
                            remaining_inactive
                        )
                        correction[rank] += count * increment * completions
        current = following
    assert sum(current[(1 << active) - 1]) * math.factorial(inactive) == FACTORIAL_N
    return [
        10 * rank * math.factorial(N - 2)
        + correction[rank] * math.factorial(inactive)
        for rank in range(N)
    ]


def literal_normal_form(record: dict[str, object]) -> tuple[list[int], dict[tuple[int, ...], int], int]:
    """Enumerate labelled active-rank injections, independently of the Rust DP."""
    active = int(record["active_vertices"])
    matrix = signed_matrix(record)
    inactive_factor = math.factorial(N - active)
    linear = [10 * rank * math.factorial(N - 2) for rank in range(N)]
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    injections = 0

    # positions[vertex] is the rank occupied by that labelled active vertex.
    for positions in permutations(range(N), active):
        by_rank = {rank: vertex for vertex, rank in enumerate(positions)}
        placed: list[int] = []
        word = [0] * N
        for rank in range(N):
            vertex = by_rank.get(rank)
            if vertex is None:
                continue
            word[rank] = sum(matrix[vertex][other] for other in placed)
            placed.append(vertex)
        raw = tuple(word)
        assert sum(raw) == 0
        injections += 1
        first = next((value for value in raw if value), None)
        if first is None:
            continue
        if first < 0:
            for rank, value in enumerate(raw):
                linear[rank] += value * inactive_factor
        direction = normalized_direction(raw)
        assert direction is not None
        assert sum(direction) == 0
        assert gcd_word(direction) == 1
        assert next(value for value in direction if value) > 0
        if active_direction(direction):
            # This is exactly condition 4 in the written uniqueness lemma.
            assert any(sum(direction[: stop + 1]) < 0 for stop in range(N - 1))
            hinges[direction] += gcd_word(raw) * inactive_factor
        else:
            # First-positive plus no negative prefix makes d.x strictly negative
            # throughout the ordered chamber, so its ReLU contribution is zero.
            prefixes = [sum(direction[: stop + 1]) for stop in range(N - 1)]
            assert all(prefix >= 0 for prefix in prefixes)
            assert any(prefix > 0 for prefix in prefixes)

    labelled = injections * inactive_factor
    assert labelled == FACTORIAL_N
    return linear, dict(hinges), labelled


def assert_exact_modular_agreement(exact: dict[str, object], modular: dict[str, object]) -> None:
    exact_direction = exact["first_hinge_residual"]
    modular_direction = modular["first_hinge_residual"]
    assert (exact_direction is None) == (modular_direction is None)
    if exact_direction is not None:
        coefficient = int(exact_direction["coefficient"])
        assert exact_direction["direction"] == modular_direction["direction"]
        assert modular_direction["residues"] == [coefficient % prime for prime in PRIMES]
    exact_linear = [int(value) for value in exact["linear_residuals"]]
    for field, prime in enumerate(PRIMES):
        assert modular["linear_residues_after_target"][field] == [
            value % prime for value in exact_linear
        ]


def write_exclusive(path: Path, value: object) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "w", encoding="utf-8") as destination:
        json.dump(value, destination, indent=2, sort_keys=True)
        destination.write("\n")


def main() -> None:
    review = Path(__file__).resolve().parent
    root = review.parents[2]
    g0117 = root / "artifacts/math/G-0117"
    panel_path = root / "artifacts/math/G-0113/panel_solver_input_v1.json"
    panel = load(panel_path)
    records = panel["records"]

    paths = {
        "exact_executable": g0117 / "target/release/global_exact_replay",
        "exact_source": g0117 / "src/bin/global_exact_replay.rs",
        "modular_executable": g0117 / "target/release/global_modular_replay",
        "modular_source": g0117 / "src/bin/global_modular_replay.rs",
        "kernel": g0117 / "src/lib.rs",
        "uniqueness_lemma": g0117 / "NORMAL_FORM_UNIQUENESS_LEMMA.md",
        "exact_preregistration": g0117 / "EXACT_GLOBAL_REPLAY_PREREGISTRATION.md",
    }
    actual_hashes = {name: sha256_path(path) for name, path in paths.items()}
    assert actual_hashes == EXPECTED_HASHES

    exact = load(review / "postfix_current_exact_planted.json")
    mutant = load(review / "postfix_current_exact_mutant.json")
    modular = load(review / "postfix_current_modular_planted.json")
    large_exact = load(review / "postfix_exact_large_bigint.json")
    large_modular = load(review / "postfix_modular_large_bigint.json")
    linear_exact = load(review / "postfix_exact_linear_branch.json")
    linear_modular = load(review / "postfix_modular_linear_branch.json")

    for output, executable_name, source_name in (
        (exact, "exact_executable", "exact_source"),
        (mutant, "exact_executable", "exact_source"),
        (large_exact, "exact_executable", "exact_source"),
        (linear_exact, "exact_executable", "exact_source"),
        (modular, "modular_executable", "modular_source"),
        (large_modular, "modular_executable", "modular_source"),
        (linear_modular, "modular_executable", "modular_source"),
    ):
        assert output["bindings"]["executable"] == actual_hashes[executable_name]
        assert output["bindings"]["producer"] == actual_hashes[source_name]
        assert output["bindings"]["kernel"] == actual_hashes["kernel"]
        assert output["bindings"]["normal_form_uniqueness"] == actual_hashes["uniqueness_lemma"]

    # Independent targeted subset DPs for the high-active controls, plus literal
    # active-rank injection enumeration for the hinge-free active-three control.
    linear0 = linear_vector_dp(records[0])
    linear1 = linear_vector_dp(records[1])
    linear5341, hinges5341, labelled5341 = literal_normal_form(records[5341])
    assert labelled5341 == FACTORIAL_N
    h0 = targeted_hinge_coefficient(records[0], FIRST_DIRECTION)
    h1 = targeted_hinge_coefficient(records[1], FIRST_DIRECTION)
    assert h0 == 123_648
    assert h1 == 33_792

    planted_linear = [7 * left - 6 * right for left, right in zip(linear0, linear1, strict=True)]
    planted_linear[-1] -= 14 * FACTORIAL_N
    assert 7 * h0 - 6 * h1 == 662_784
    assert exact["first_hinge_residual"] == {
        "direction": list(FIRST_DIRECTION),
        "coefficient": "662784",
    }
    assert exact["linear_residuals"] == [str(value) for value in planted_linear]

    mutant_linear = [8 * left - 6 * right for left, right in zip(linear0, linear1, strict=True)]
    mutant_linear[-1] -= 14 * FACTORIAL_N
    assert 8 * h0 - 6 * h1 == 786_432
    assert mutant["first_hinge_residual"] == {
        "direction": list(FIRST_DIRECTION),
        "coefficient": "786432",
    }
    assert mutant["linear_residuals"] == [str(value) for value in mutant_linear]

    large_certificate = load(review / "postfix_large_bigint_certificate.json")
    huge = int(large_certificate["terms"][0]["coefficient"])
    assert huge > 2**256
    large_linear = [huge * value for value in linear0]
    large_linear[-1] -= FACTORIAL_N
    assert int(large_exact["first_hinge_residual"]["coefficient"]) == huge * h0
    assert large_exact["linear_residuals"] == [str(value) for value in large_linear]

    assert hinges5341 == {}
    linear5341[-1] -= FACTORIAL_N
    assert linear_exact["first_hinge_residual"] is None
    assert linear_exact["exact_nonzero_hinge_directions"] == 0
    assert linear_exact["first_linear_residual"] == {"coordinate": 1, "coefficient": "2903040"}
    assert linear_exact["linear_residuals"] == [str(value) for value in linear5341]

    assert_exact_modular_agreement(exact, modular)
    assert_exact_modular_agreement(large_exact, large_modular)
    assert_exact_modular_agreement(linear_exact, linear_modular)

    forbidden_outputs = [
        "postfix_current_exact_hostile_should_not_exist.json",
        "postfix_current_modular_hostile_should_not_exist.json",
        "postfix_exact_forged_should_not_exist.json",
        "postfix_modular_forged_should_not_exist.json",
        "postfix_exact_mismatched_receipt_should_not_exist.json",
        "postfix_modular_mismatched_receipt_should_not_exist.json",
        "postfix_converter_forged_should_not_exist.json",
        "postfix_isolated_stale_exact_should_not_exist.json",
        "postfix_isolated_stale_lemma_should_not_exist.json",
    ]
    assert all(not (review / name).exists() for name in forbidden_outputs)

    planted_certificate = load(g0117 / "planted_certificate_v2.json")
    assert planted_certificate["source_exact_postprocess"]["sha256"] == "a" * 64

    result = {
        "schema": "max11-g0117-postfix-independent-controls-v1",
        "result": "PASS_BOUNDED_WITH_EXTERNAL_PROVENANCE_OBLIGATION",
        "bindings": actual_hashes,
        "independent_normal_form_controls": {
            "targeted_subset_dp_sequences": [0, 1],
            "literal_injection_sequence": 5341,
            "labelled_permutations_for_literal_control": FACTORIAL_N,
            "statement_match": (
                "Every retained direction is zero-sum, primitive, first-positive, and has a "
                "negative proper prefix; omitted first-positive directions have only "
                "nonnegative proper prefixes and their ReLU vanishes on the open chamber."
            ),
            "sequence_0_first_hinge": 123_648,
            "sequence_1_first_hinge": 33_792,
            "planted_first_residual": 662_784,
            "mutant_first_residual": 786_432,
            "sequence_5341_hinge_support": 0,
            "sequence_5341_first_linear_residual": 2_903_040,
        },
        "bigint": {
            "coefficient_digits": len(str(huge)),
            "larger_than_2_pow_256": True,
            "exact_first_hinge_equals_coefficient_times_123648": True,
        },
        "exact_modular_agreement": {
            "primes": list(PRIMES),
            "planted": True,
            "large_bigint": True,
            "linear_fallback": True,
        },
        "negative_controls": {
            "forbidden_outputs_absent": forbidden_outputs,
            "unknown_fields_rejected": True,
            "old_forged_certificate_rejected": True,
            "mismatched_receipt_rejected": True,
            "isolated_stale_source_rejected": True,
            "isolated_stale_uniqueness_lemma_rejected": True,
            "forged_converter_chain_rejected": True,
        },
        "scope_caveat": (
            "The replay layer checks receipt syntax and internal consistency, not the external "
            "postprocess/report/retained files. The production converter is the trust boundary "
            "that rehashes and cleanly reruns those artifacts; a real subject replay is pending."
        ),
    }
    write_exclusive(review / "postfix_controls.json", result)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
