#!/usr/bin/env python3
"""Two-panel modular circuit screen for the provisional exact rank-659 member."""

from __future__ import annotations

import collections
import hashlib
import importlib.util
import json
import mmap
from pathlib import Path
import sys
from typing import Any

import numpy as np


ROOT = Path("/data/projects/relu-depth-frontier-research")
PRIOR = Path("/tmp/g0168-explore.kEmA87")
NEXT = Path("/tmp/g0168-next.yerj9c")
SOURCE = Path("/tmp/g0168-screen.vvx85D")
HERE = Path(__file__).parent
RECORDS = 163_740
DIRECTIONS = 4_096
OLD_RANK = 349
PRIOR_ADDED = 119
NEXT_ADDED = 127
PAIR_ADDED = 64
PAIR_DIRECTIONS = 128
CURRENT_RANK = 659
PREVIOUS_RANK = 595
PROBES = 512
CURRENT_ROWS = 924
PAIR_ROW_OFFSET = 796
PRIMES = (1_000_003, 1_000_033)
ORIGINAL_BATCH = 128
CIRCUIT_BATCH = 514
INT64_MAX = np.iinfo(np.int64).max


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1 << 20):
            digest.update(chunk)
    return digest.hexdigest()


def json_sha256(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def mod_matmul(left: np.ndarray, right: np.ndarray, prime: int) -> np.ndarray:
    left = np.asarray(left, dtype=np.int64) % prime
    right = np.asarray(right, dtype=np.int64) % prime
    assert left.ndim == right.ndim == 2 and left.shape[1] == right.shape[0]
    worst_case = left.shape[1] * (prime - 1) * (prime - 1)
    assert worst_case <= INT64_MAX, (
        f"unsafe int64 modular matmul envelope: inner={left.shape[1]} "
        f"prime={prime} bound={worst_case}"
    )
    return (left @ right) % prime


def rref_mod(matrix: np.ndarray, prime: int) -> tuple[np.ndarray, list[int]]:
    reduced = np.asarray(matrix, dtype=np.int64).copy() % prime
    rows, columns = reduced.shape
    rank = 0
    pivots: list[int] = []
    assert (prime - 1) * (prime - 1) <= INT64_MAX
    for column in range(columns):
        candidates = np.flatnonzero(reduced[rank:, column])
        if not len(candidates):
            continue
        pivot = rank + int(candidates[0])
        if pivot != rank:
            reduced[[rank, pivot]] = reduced[[pivot, rank]]
        inverse = pow(int(reduced[rank, column]), -1, prime)
        reduced[rank] = (reduced[rank] * inverse) % prime
        factors = reduced[:, column].copy()
        factors[rank] = 0
        reduced = (reduced - factors[:, None] * reduced[rank][None, :]) % prime
        pivots.append(column)
        rank += 1
        if rank == rows:
            break
    return reduced[:rank], pivots


def inverse_mod(matrix: np.ndarray, prime: int) -> np.ndarray:
    size = matrix.shape[0]
    assert matrix.shape == (size, size)
    augmented = np.concatenate(
        [np.asarray(matrix, dtype=np.int64) % prime, np.eye(size, dtype=np.int64)],
        axis=1,
    )
    for column in range(size):
        candidates = np.flatnonzero(augmented[column:, column])
        if not len(candidates):
            raise RuntimeError(f"singular coordinate square modulo {prime} at {column}")
        pivot = column + int(candidates[0])
        if pivot != column:
            augmented[[column, pivot]] = augmented[[pivot, column]]
        inverse = pow(int(augmented[column, column]), -1, prime)
        augmented[column] = (augmented[column] * inverse) % prime
        factors = augmented[:, column].copy()
        factors[column] = 0
        augmented = (
            augmented - factors[:, None] * augmented[column][None, :]
        ) % prime
    assert np.array_equal(augmented[:, :size], np.eye(size, dtype=np.int64))
    return augmented[:, size:]


def relation_pairings(
    rref: np.ndarray,
    pivots: list[int],
    residual: np.ndarray,
    prime: int,
) -> tuple[list[int], np.ndarray]:
    columns = len(residual)
    pivot_set = set(pivots)
    free = [index for index in range(columns) if index not in pivot_set]
    if not free:
        return free, np.empty(0, dtype=np.int64)
    pivot_residual = np.asarray(residual[pivots], dtype=np.int64).reshape(1, -1)
    projection = mod_matmul(pivot_residual, rref[:, free], prime)[0]
    pairings = (np.asarray(residual[free], dtype=np.int64) - projection) % prime
    return free, pairings


def circuit_from_free(
    rref: np.ndarray,
    pivots: list[int],
    free_column: int,
    direction_indices: list[int],
    residual: np.ndarray,
    prime: int,
) -> dict[str, Any]:
    coefficients = np.zeros(len(direction_indices), dtype=np.int64)
    coefficients[free_column] = 1
    coefficients[pivots] = (-rref[:, free_column]) % prime
    support = np.flatnonzero(coefficients)
    residual_pairing = int(
        mod_matmul(
            np.asarray(residual, dtype=np.int64).reshape(1, -1),
            coefficients.reshape(-1, 1),
            prime,
        )[0, 0]
    )
    support_indices = [direction_indices[int(index)] for index in support]
    support_coefficients = [int(coefficients[int(index)]) for index in support]
    payload = [
        [direction, coefficient]
        for direction, coefficient in zip(support_indices, support_coefficients)
    ]
    return {
        "free_local_column": free_column,
        "free_direction_index": direction_indices[free_column],
        "support": len(support_indices),
        "direction_indices": support_indices,
        "coefficients_mod_prime": support_coefficients,
        "coefficient_support_sha256": json_sha256(payload),
        "residual_pairing_mod_prime": residual_pairing,
    }


def dependency_profile(
    matrix: np.ndarray,
    residual: np.ndarray,
    direction_indices: list[int],
    prime: int,
    include_witness: bool,
) -> dict[str, Any]:
    assert matrix.shape[1] == len(residual) == len(direction_indices)
    rref, pivots = rref_mod(matrix, prime)
    free, pairings = relation_pairings(rref, pivots, residual, prime)
    incompatible_positions = np.flatnonzero(pairings)
    incompatible = bool(len(incompatible_positions))
    output: dict[str, Any] = {
        "rank": len(pivots),
        "nullity": len(direction_indices) - len(pivots),
        "augmented_rank": len(pivots) + int(incompatible),
        "residual_incompatible": incompatible,
    }
    if include_witness and incompatible:
        free_column = free[int(incompatible_positions[0])]
        witness = circuit_from_free(
            rref, pivots, free_column, direction_indices, residual, prime
        )
        annihilation = mod_matmul(
            matrix,
            np.asarray(
                [
                    witness["coefficients_mod_prime"][
                        witness["direction_indices"].index(index)
                    ]
                    if index in witness["direction_indices"]
                    else 0
                    for index in direction_indices
                ],
                dtype=np.int64,
            ).reshape(-1, 1),
            prime,
        )
        assert not np.any(annihilation)
        assert witness["residual_pairing_mod_prime"] != 0
        output["incompatibility_witness"] = witness
    return output


def quotient_groups(matrix: np.ndarray, prime: int) -> dict[str, Any]:
    exact: dict[bytes, list[int]] = collections.defaultdict(list)
    proportional: dict[bytes, list[int]] = collections.defaultdict(list)
    zero: list[int] = []
    for index in range(matrix.shape[1]):
        vector = np.ascontiguousarray(matrix[:, index], dtype=np.int64)
        exact[vector.tobytes()].append(index)
        nonzero = np.flatnonzero(vector)
        if not len(nonzero):
            zero.append(index)
            continue
        pivot = int(vector[int(nonzero[0])])
        normalized = (vector * pow(pivot, -1, prime)) % prime
        proportional[np.ascontiguousarray(normalized).tobytes()].append(index)
    exact_groups = sorted(
        (group for group in exact.values() if len(group) > 1),
        key=lambda group: (group[0], len(group), group),
    )
    proportional_groups = sorted(
        (group for group in proportional.values() if len(group) > 1),
        key=lambda group: (group[0], len(group), group),
    )
    return {
        "zero_indices": zero,
        "duplicate_groups": exact_groups,
        "proportional_groups": proportional_groups,
        "duplicate_group_count": len(exact_groups),
        "proportional_group_count": len(proportional_groups),
        "duplicate_member_count": sum(len(group) for group in exact_groups),
        "proportional_member_count": sum(len(group) for group in proportional_groups),
    }


def add_candidate(
    candidates: dict[tuple[int, ...], set[str]], indices: list[int], label: str
) -> None:
    key = tuple(indices)
    if len(key) < 2 or len(key) > CIRCUIT_BATCH or len(set(key)) != len(key):
        return
    candidates.setdefault(key, set()).add(label)


def evenly_spaced(group: list[int], size: int) -> list[int]:
    return [group[(offset * len(group)) // size] for offset in range(size)]


def build_candidates(
    directions: list[tuple[int, ...]], panel1_groups: dict[str, Any]
) -> dict[tuple[int, ...], set[str]]:
    candidates: dict[tuple[int, ...], set[str]] = {}
    for start in range(0, DIRECTIONS - ORIGINAL_BATCH + 1, 32):
        add_candidate(
            candidates,
            list(range(start, start + ORIGINAL_BATCH)),
            f"contiguous128_{start}",
        )
    groupings: dict[str, dict[object, list[int]]] = {}
    for prefix in range(4, 10):
        grouped: dict[object, list[int]] = collections.defaultdict(list)
        for index, direction in enumerate(directions):
            grouped[direction[:prefix]].append(index)
        groupings[f"prefix_{prefix}"] = grouped
    features: dict[object, list[int]] = collections.defaultdict(list)
    signs: dict[object, list[int]] = collections.defaultdict(list)
    for index, direction in enumerate(directions):
        features[
            (
                sum(value != 0 for value in direction),
                sum(abs(value) for value in direction),
                max(abs(value) for value in direction),
                sum(value > 0 for value in direction),
                sum(value < 0 for value in direction),
            )
        ].append(index)
        signs[tuple((value > 0) - (value < 0) for value in direction)].append(index)
    groupings["features"] = features
    groupings["sign_pattern"] = signs
    for grouping_name, grouped in groupings.items():
        for key, group in grouped.items():
            for size in (ORIGINAL_BATCH, CIRCUIT_BATCH):
                if len(group) < size:
                    continue
                selections = [group[:size], group[-size:], evenly_spaced(group, size)]
                for variant, selection in enumerate(selections):
                    add_candidate(
                        candidates,
                        selection,
                        f"{grouping_name}_{key}_n{size}_v{variant}",
                    )
    for start in range(0, DIRECTIONS - CIRCUIT_BATCH + 1, 256):
        add_candidate(
            candidates,
            list(range(start, start + CIRCUIT_BATCH)),
            f"contiguous514_{start}",
        )
    add_candidate(
        candidates,
        list(range(DIRECTIONS - CIRCUIT_BATCH, DIRECTIONS)),
        f"contiguous514_{DIRECTIONS - CIRCUIT_BATCH}",
    )
    for kind in ("duplicate_groups", "proportional_groups"):
        for group in panel1_groups[kind]:
            digest = json_sha256(group)[:16]
            if len(group) <= CIRCUIT_BATCH:
                add_candidate(candidates, group, f"panel1_{kind}_{digest}")
            else:
                for variant, selection in enumerate(
                    [group[:CIRCUIT_BATCH], group[-CIRCUIT_BATCH:], evenly_spaced(group, CIRCUIT_BATCH)]
                ):
                    add_candidate(
                        candidates,
                        selection,
                        f"panel1_{kind}_{digest}_v{variant}",
                    )
    return candidates


def whole_panel_sparse_circuits(
    panel1: np.ndarray,
    panel2: np.ndarray,
    residual: np.ndarray,
    prime: int,
) -> dict[str, Any]:
    rref, pivots = rref_mod(panel1, prime)
    pivot_set = set(pivots)
    free = [index for index in range(DIRECTIONS) if index not in pivot_set]
    assert len(pivots) <= PROBES
    panel2_projection = mod_matmul(panel2[:, pivots], rref[:, free], prime)
    panel2_remainders = (panel2[:, free] - panel2_projection) % prime
    panel1_free, panel1_pairings = relation_pairings(
        rref, pivots, residual, prime
    )
    assert panel1_free == free
    panel1_incompatible = bool(np.any(panel1_pairings))

    panel2_rref, panel2_pivots = rref_mod(panel2, prime)
    _, panel2_pairings = relation_pairings(
        panel2_rref, panel2_pivots, residual, prime
    )
    panel2_incompatible = bool(np.any(panel2_pairings))

    remainder_rref, remainder_pivots = rref_mod(panel2_remainders, prime)
    _, combined_pairings = relation_pairings(
        remainder_rref, remainder_pivots, panel1_pairings, prime
    )
    combined_incompatible = bool(np.any(combined_pairings))
    combined_rank = len(pivots) + len(remainder_pivots)
    assert combined_rank <= 2 * PROBES
    cross_panel = np.flatnonzero(~np.any(panel2_remainders, axis=0))
    pivot_residual = residual[pivots].reshape(1, -1)
    residual_projection = mod_matmul(pivot_residual, rref[:, free], prime)[0]
    pairings = (residual[free] - residual_projection) % prime
    cross_nonzero = [int(position) for position in cross_panel if pairings[int(position)] != 0]
    witnesses = []
    for position in cross_nonzero[:50]:
        free_column = free[position]
        witness = circuit_from_free(
            rref,
            pivots,
            free_column,
            list(range(DIRECTIONS)),
            residual,
            prime,
        )
        coefficient_vector = np.zeros(DIRECTIONS, dtype=np.int64)
        coefficient_vector[witness["direction_indices"]] = witness["coefficients_mod_prime"]
        assert not np.any(mod_matmul(panel1, coefficient_vector[:, None], prime))
        assert not np.any(mod_matmul(panel2, coefficient_vector[:, None], prime))
        witnesses.append(witness)
    stable_free_indices = [free[int(position)] for position in cross_panel]
    stable_nonzero_indices = [free[position] for position in cross_nonzero]
    stable_pairing_payload = [
        [free[int(position)], int(pairings[int(position)])] for position in cross_panel
    ]
    return {
        "whole_matrix_rank_tuple": {
            "panel_1": {
                "rank": len(pivots),
                "augmented_with_residual_rank": len(pivots)
                + int(panel1_incompatible),
                "residual_compatible": not panel1_incompatible,
            },
            "panel_2": {
                "rank": len(panel2_pivots),
                "augmented_with_residual_rank": len(panel2_pivots)
                + int(panel2_incompatible),
                "residual_compatible": not panel2_incompatible,
            },
            "combined_panels": {
                "rank": combined_rank,
                "augmented_with_residual_rank": combined_rank
                + int(combined_incompatible),
                "residual_compatible": not combined_incompatible,
            },
            "derivation": "combined rank = rank(panel1) + rank(panel2 remainder modulo the panel1 pivot span)",
        },
        "panel1_rank": len(pivots),
        "panel1_nullity": len(free),
        "maximum_circuit_support": len(pivots) + 1,
        "pivot_direction_indices_sha256": json_sha256(pivots),
        "cross_panel_annihilating_individual_circuits": len(cross_panel),
        "cross_panel_nonzero_residual_pairing_circuits": len(cross_nonzero),
        "cross_panel_free_direction_indices": stable_free_indices,
        "cross_panel_nonzero_residual_free_direction_indices": stable_nonzero_indices,
        "cross_panel_residual_pairings_sha256": json_sha256(stable_pairing_payload),
        "nonzero_residual_witnesses_first_50": witnesses,
        "claim_boundary": "These are only the lexicographic panel-1 null-basis circuits that individually survive panel 2; candidate screens separately test combinations inside predeclared supports.",
    }


def analyze_prime(
    prime: int,
    quotient1: np.ndarray,
    quotient2: np.ndarray,
    residual: np.ndarray,
    directions: list[tuple[int, ...]],
    provenance: dict[str, str],
) -> dict[str, Any]:
    combined = np.concatenate([quotient1, quotient2], axis=0)
    panel1_groups = quotient_groups(quotient1, prime)
    panel2_groups = quotient_groups(quotient2, prime)
    combined_groups = quotient_groups(combined, prime)
    candidates = build_candidates(directions, panel1_groups)
    scored: list[dict[str, Any]] = []
    for indices_tuple, labels in candidates.items():
        indices = list(indices_tuple)
        selected_residual = residual[indices]
        panel1_profile = dependency_profile(
            quotient1[:, indices], selected_residual, indices, prime, False
        )
        combined_profile = dependency_profile(
            combined[:, indices], selected_residual, indices, prime, True
        )
        scored.append(
            {
                "labels": sorted(labels),
                "indices": indices,
                "indices_sha256": json_sha256(indices),
                "size": len(indices),
                "panel1": panel1_profile,
                "combined_panels": combined_profile,
            }
        )
    scored.sort(
        key=lambda item: (
            not item["combined_panels"]["residual_incompatible"],
            -(item["combined_panels"]["nullity"]),
            item["combined_panels"]["rank"],
            item["size"],
            item["indices_sha256"],
        )
    )
    sparse = whole_panel_sparse_circuits(
        quotient1, quotient2, residual, prime
    )
    sizes = sorted({item["size"] for item in scored})
    size_summary = {
        str(size): {
            "tested": sum(item["size"] == size for item in scored),
            "panel1_incompatible": sum(
                item["size"] == size and item["panel1"]["residual_incompatible"]
                for item in scored
            ),
            "combined_incompatible": sum(
                item["size"] == size
                and item["combined_panels"]["residual_incompatible"]
                for item in scored
            ),
            "minimum_panel1_rank": min(
                item["panel1"]["rank"] for item in scored if item["size"] == size
            ),
            "minimum_combined_rank": min(
                item["combined_panels"]["rank"]
                for item in scored
                if item["size"] == size
            ),
        }
        for size in sizes
    }
    return {
        "schema": "g0178.rank659_two_panel_probe_quotient_analysis.v1",
        "provisional_only": True,
        "prime": prime,
        "basis": CURRENT_RANK,
        "probes_per_panel": PROBES,
        "directions": DIRECTIONS,
        "panel_1_groups": panel1_groups,
        "panel_2_groups": panel2_groups,
        "combined_panel_groups": combined_groups,
        "whole_panel1_sparse_circuit_scan": sparse,
        "candidate_batches_tested": len(scored),
        "candidate_size_summary": size_summary,
        "total_panel1_incompatible_candidates": sum(
            item["panel1"]["residual_incompatible"] for item in scored
        ),
        "total_combined_panel_incompatible_candidates": sum(
            item["combined_panels"]["residual_incompatible"] for item in scored
        ),
        "all_candidate_batches": scored,
        "inputs": provenance,
        "int64_safety": {
            "checked_before_every_modular_matmul": True,
            "formula": "inner_dimension*(prime-1)^2 <= 2^63-1",
            "largest_inner_dimension": CURRENT_RANK,
            "largest_checked_bound": CURRENT_RANK * (prime - 1) * (prime - 1),
        },
        "claim_boundary": "Both panels are finite restrictions. A two-panel modular circuit is only a high-value full-pricing target, not a global dependency or obstruction.",
    }


def compare_primes(
    first: dict[str, Any], second: dict[str, Any], output_hashes: dict[str, str]
) -> dict[str, Any]:
    by_prime = []
    maps = []
    for analysis in (first, second):
        maps.append(
            {item["indices_sha256"]: item for item in analysis["all_candidate_batches"]}
        )
        by_prime.append(analysis["prime"])
    common_digests = sorted(set(maps[0]) & set(maps[1]))
    stable_incompatible = []
    stable_subrank = []
    for digest in common_digests:
        left = maps[0][digest]
        right = maps[1][digest]
        assert left["indices"] == right["indices"] and left["size"] == right["size"]
        if (
            left["combined_panels"]["residual_incompatible"]
            and right["combined_panels"]["residual_incompatible"]
        ):
            left_witness = left["combined_panels"]["incompatibility_witness"]
            right_witness = right["combined_panels"]["incompatibility_witness"]
            stable_incompatible.append(
                {
                    "indices_sha256": digest,
                    "size": left["size"],
                    "labels_prime_1": left["labels"],
                    "labels_prime_2": right["labels"],
                    "combined_rank_prime_1": left["combined_panels"]["rank"],
                    "combined_rank_prime_2": right["combined_panels"]["rank"],
                    "support_same_across_primes": (
                        left_witness["direction_indices"]
                        == right_witness["direction_indices"]
                    ),
                    "witness_prime_1": left_witness,
                    "witness_prime_2": right_witness,
                }
            )
        if (
            left["combined_panels"]["rank"] < left["size"]
            and right["combined_panels"]["rank"] < right["size"]
        ):
            stable_subrank.append(
                {
                    "indices_sha256": digest,
                    "size": left["size"],
                    "rank_prime_1": left["combined_panels"]["rank"],
                    "rank_prime_2": right["combined_panels"]["rank"],
                    "nullity_prime_1": left["combined_panels"]["nullity"],
                    "nullity_prime_2": right["combined_panels"]["nullity"],
                    "compatible_both": not (
                        left["combined_panels"]["residual_incompatible"]
                        or right["combined_panels"]["residual_incompatible"]
                    ),
                    "labels": sorted(set(left["labels"] + right["labels"])),
                }
            )
    stable_incompatible.sort(
        key=lambda item: (
            min(
                item["witness_prime_1"]["support"],
                item["witness_prime_2"]["support"],
            ),
            item["size"],
            item["indices_sha256"],
        )
    )
    stable_subrank.sort(
        key=lambda item: (
            -min(item["nullity_prime_1"], item["nullity_prime_2"]),
            item["size"],
            item["indices_sha256"],
        )
    )
    sparse_first = first["whole_panel1_sparse_circuit_scan"]
    sparse_second = second["whole_panel1_sparse_circuit_scan"]
    individual_stable_nonzero = sorted(
        set(sparse_first["cross_panel_nonzero_residual_free_direction_indices"])
        & set(sparse_second["cross_panel_nonzero_residual_free_direction_indices"])
    )
    groups_agreement = {
        "panel1_duplicate_groups_exactly_equal": (
            first["panel_1_groups"]["duplicate_groups"]
            == second["panel_1_groups"]["duplicate_groups"]
        ),
        "panel1_proportional_groups_exactly_equal": (
            first["panel_1_groups"]["proportional_groups"]
            == second["panel_1_groups"]["proportional_groups"]
        ),
        "combined_duplicate_groups_exactly_equal": (
            first["combined_panel_groups"]["duplicate_groups"]
            == second["combined_panel_groups"]["duplicate_groups"]
        ),
        "combined_proportional_groups_exactly_equal": (
            first["combined_panel_groups"]["proportional_groups"]
            == second["combined_panel_groups"]["proportional_groups"]
        ),
    }
    if stable_incompatible:
        assessment = {
            "classification": "HIGH_YIELD_PREDICTED_OBSTRUCTION_TARGET",
            "reason": "At least one predeclared support has a nonzero residual pairing on a circuit annihilating both disjoint panels under both primes.",
            "next_gate": "Full-price only the minimum-support stable-incompatible support.",
            "target": stable_incompatible[0]["indices_sha256"],
        }
    elif individual_stable_nonzero:
        assessment = {
            "classification": "HIGH_YIELD_PREDICTED_OBSTRUCTION_TARGET",
            "reason": "A lexicographic panel-1 circuit independently annihilates panel 2 and pairs nontrivially with the residual under both primes.",
            "next_gate": "Full-price the minimum-support two-prime witness.",
            "target": individual_stable_nonzero[0],
        }
    elif stable_subrank:
        assessment = {
            "classification": "DEPENDENCY_RICH_BUT_RESIDUAL_COMPATIBLE_ON_PROBES",
            "reason": "Two-prime cross-panel dependencies exist, but every detected candidate circuit pairs to zero with the residual.",
            "next_gate": "Treat only as rank-efficient interpolation evidence; STAR-outside-primary gate outranks another equal-residual batch.",
            "target": stable_subrank[0]["indices_sha256"],
        }
    else:
        assessment = {
            "classification": "NO_HIGH_YIELD_TARGET_FOUND",
            "reason": "No candidate dependency survived both panels and primes with a nonzero residual pairing.",
            "next_gate": "Advance to STAR-outside-primary rather than full-pricing another probe-selected batch.",
            "target": None,
        }
    minimum_support = None
    minimum_digest = None
    if stable_incompatible:
        minimum_support = min(
            min(
                item["witness_prime_1"]["support"],
                item["witness_prime_2"]["support"],
            )
            for item in stable_incompatible
        )
        minimum_digest = stable_incompatible[0]["indices_sha256"]
    return {
        "schema": "g0178.rank659_two_prime_two_panel_comparison.v1",
        "provisional_only": True,
        "primes": by_prime,
        "prime_output_hashes": output_hashes,
        "candidate_batches_common_to_both_primes": len(common_digests),
        "two_prime_cross_panel_stable_incompatible_candidates": len(stable_incompatible),
        "two_prime_cross_panel_stable_subrank_candidates": len(stable_subrank),
        "two_prime_individual_panel1_circuits_surviving_panel2_with_nonzero_residual_pairing": len(individual_stable_nonzero),
        "individual_stable_nonzero_free_direction_indices": individual_stable_nonzero,
        "minimum_stable_incompatible_support": minimum_support,
        "minimum_stable_incompatible_candidate_digest": minimum_digest,
        "stable_incompatible_candidates": stable_incompatible,
        "stable_subrank_candidates": stable_subrank,
        "group_agreement": groups_agreement,
        "target_assessment": assessment,
        "claim_boundary": "Two-prime agreement reduces modular-collision risk but does not turn two finite probe panels into complete-family evidence.",
    }


def main() -> None:
    if sys.flags.optimize != 0:
        raise RuntimeError("optimized Python prohibited")
    if len(sys.argv) != 4:
        raise SystemExit(
            "usage: analyze_two_panel_fingerprints.py PRIME1.json PRIME2.json COMPARISON.json"
        )
    output_paths = [Path(raw) for raw in sys.argv[1:]]
    assert all(not path.exists() for path in output_paths)

    receipt_path = HERE / "fingerprint_receipt.json"
    member_path = SOURCE / "exact_924_member.json"
    global_path = SOURCE / "global_replay_924_member.json"
    pair_matrix_path = SOURCE / "duplicate_pairs128.record-major.i64le"
    pair_receipt_path = SOURCE / "duplicate_pairs128_full_price_receipt.json"
    pair_selection_path = SOURCE / "selected_duplicate_pairs_128.json"
    current796_path = NEXT / "exact_796_member.json"
    prior_member_path = PRIOR / "exact_augmented_member.json"
    prior_matrix_path = PRIOR / "fresh128.record-major.i64le"
    next_matrix_path = NEXT / "next128.record-major.i64le"

    paths = [
        receipt_path,
        member_path,
        global_path,
        pair_matrix_path,
        pair_receipt_path,
        pair_selection_path,
        current796_path,
        prior_member_path,
        prior_matrix_path,
        next_matrix_path,
    ]
    opening_hashes = {str(path): file_sha256(path) for path in paths}
    with receipt_path.open() as source:
        receipt = json.load(source)
    with member_path.open() as source:
        member = json.load(source)
    with global_path.open() as source:
        global_result = json.load(source)
    with pair_receipt_path.open() as source:
        pair_receipt = json.load(source)
    with pair_selection_path.open() as source:
        pair_selection = json.load(source)
    with current796_path.open() as source:
        current796 = json.load(source)
    with prior_member_path.open() as source:
        prior_member = json.load(source)

    assert receipt["schema"] == "g0178.rank659_two_disjoint_probe_panels.v1"
    assert receipt["basis_records"] == CURRENT_RANK
    assert receipt["probe_records_per_panel"] == PROBES
    assert receipt["probe_panels"] == 2 and receipt["directions"] == DIRECTIONS
    assert receipt["global_direct_exact_4096_dot_bridge"] is True
    assert receipt["inputs"]["member_sha256"] == opening_hashes[str(member_path)]
    assert receipt["inputs"]["global_sha256"] == opening_hashes[str(global_path)]
    assert receipt["inputs"]["pair_matrix_sha256"] == opening_hashes[str(pair_matrix_path)]
    assert receipt["inputs"]["pair_receipt_sha256"] == opening_hashes[str(pair_receipt_path)]
    assert receipt["inputs"]["pair_selection_sha256"] == opening_hashes[str(pair_selection_path)]
    assert global_result["inputs"]["member_sha256"] == opening_hashes[str(member_path)]
    assert member["result"] == "EXACT_924_ROW_DUPLICATE_PAIR_BATCH_MEMBER_PROVISIONAL"
    assert member["rows"] == CURRENT_ROWS and member["all_924_rows_exactly_replayed"] is True
    assert member["selected_minor_rank_over_Q"] == CURRENT_RANK
    assert member["current_selected_minor_rank"] == PREVIOUS_RANK
    assert member["inputs"]["current_member_sha256"] == opening_hashes[str(current796_path)]
    assert member["inputs"]["prior_member_sha256"] == opening_hashes[str(prior_member_path)]
    assert member["inputs"]["prior_matrix_sha256"] == opening_hashes[str(prior_matrix_path)]
    assert member["inputs"]["next_matrix_sha256"] == opening_hashes[str(next_matrix_path)]
    assert member["inputs"]["pair_matrix_sha256"] == opening_hashes[str(pair_matrix_path)]
    assert member["inputs"]["receipt_sha256"] == opening_hashes[str(pair_receipt_path)]
    assert member["inputs"]["selection_sha256"] == opening_hashes[str(pair_selection_path)]
    assert pair_receipt["matrix_sha256"] == opening_hashes[str(pair_matrix_path)]
    assert pair_receipt["inputs"]["selection_sha256"] == opening_hashes[str(pair_selection_path)]
    assert pair_selection["selected_direction_indices"] == [
        index for pair in pair_selection["selected_pairs"] for index in pair
    ]
    assert len(pair_selection["selected_direction_indices"]) == PAIR_DIRECTIONS

    basis = np.asarray(member["basis_sequences"], dtype=np.int64)
    coordinate_rows = [int(value) for value in member["coordinate_rows"]]
    pair_coordinate_indices = [
        int(value) for value in member["pair_coordinate_direction_indices"]
    ]
    pair_witness_sequences = [int(value) for value in member["pair_witness_sequences"]]
    assert len(basis) == len(coordinate_rows) == CURRENT_RANK
    assert len(pair_coordinate_indices) == len(pair_witness_sequences) == PAIR_ADDED
    assert len(set(pair_coordinate_indices)) == PAIR_ADDED
    assert all(0 <= index < PAIR_DIRECTIONS for index in pair_coordinate_indices)
    assert list(basis[PREVIOUS_RANK:]) == pair_witness_sequences
    assert coordinate_rows[PREVIOUS_RANK:] == [
        PAIR_ROW_OFFSET + index for index in pair_coordinate_indices
    ]
    assert receipt["coordinate_envelope"]["pair_coordinate_direction_indices"] == pair_coordinate_indices
    assert receipt["coordinate_envelope"]["pair_coordinate_rows"] == coordinate_rows[PREVIOUS_RANK:]
    assert receipt["coordinate_envelope"]["pair_witness_sequences"] == pair_witness_sequences
    assert list(basis[:PREVIOUS_RANK]) == current796["basis_sequences"]

    prior_indices = [int(value) for value in prior_member["fresh_coordinate_direction_indices"]]
    next_indices = [int(value) for value in current796["next_coordinate_direction_indices"]]
    assert len(prior_indices) == PRIOR_ADDED and len(next_indices) == NEXT_ADDED

    solver_path = ROOT / "artifacts/math/G-0164/all128_direct_basis_master_v1.py"
    spec = importlib.util.spec_from_file_location("g0178_fingerprint_g0164", solver_path)
    assert spec is not None and spec.loader is not None
    solver = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(solver)
    state = solver.validate_sealed_inputs()
    old_coordinate_rows = state["coordinate_rows"]
    assert len(old_coordinate_rows) == OLD_RANK
    assert prior_member["coordinate_rows"] == old_coordinate_rows + [
        540 + index for index in prior_indices
    ]
    assert current796["coordinate_rows"] == (
        prior_member["coordinate_rows"] + [668 + index for index in next_indices]
    )
    assert coordinate_rows == current796["coordinate_rows"] + [
        PAIR_ROW_OFFSET + index for index in pair_coordinate_indices
    ]

    prepared = state["g0135_prepared"]
    components = prepared["components"]
    panel_rows = [row for row in old_coordinate_rows if row < 301]
    linear_rows = [row - 301 for row in old_coordinate_rows if 301 <= row < 312]
    hinge_sources: list[list[int]] = []
    hinge_sources.extend(components["accumulated"])
    hinge_sources.extend(components["old_batch_block"]["rows"])
    hinge_sources.extend(components["new_batch_block"]["rows"])
    hinge_sources.extend(prepared["stage_b_rows"])
    hinge_sources.extend(state["all_pool_rows"])
    hinge_indices = [row - 312 for row in old_coordinate_rows if row >= 312]
    assert len(panel_rows) + len(linear_rows) + len(hinge_indices) == OLD_RANK
    ancestor = prepared["ancestor"]
    cache_file = ancestor.AUDITED.CACHE_PATH.open("rb")
    cache_map = mmap.mmap(cache_file.fileno(), 0, access=mmap.ACCESS_READ)
    cache = np.ndarray(
        shape=(RECORDS, 301),
        dtype=np.dtype([("lo", "<i8"), ("hi", "<i8")]),
        buffer=cache_map,
    )

    def old_coordinates(records: np.ndarray) -> np.ndarray:
        parts: list[np.ndarray] = []
        panel = np.asarray(cache["lo"][records][:, panel_rows], dtype=np.int64)
        panel_hi = np.asarray(cache["hi"][records][:, panel_rows], dtype=np.int64)
        assert np.array_equal(panel_hi, np.where(panel < 0, -1, 0))
        parts.append(panel)
        linear = np.asarray(components["linear"], dtype=np.int64)[records]
        parts.append(linear[:, linear_rows])
        parts.append(
            np.asarray(
                [
                    [hinge_sources[index][int(record)] for index in hinge_indices]
                    for record in records
                ],
                dtype=np.int64,
            )
        )
        result = np.concatenate(parts, axis=1)
        assert result.shape == (len(records), OLD_RANK)
        return result

    selected_records = np.asarray(receipt["selected_records"], dtype=np.int64)
    assert len(selected_records) == CURRENT_RANK + 2 * PROBES
    assert np.array_equal(selected_records[:CURRENT_RANK], basis)
    assert list(selected_records[CURRENT_RANK : CURRENT_RANK + PROBES]) == receipt["probe_panel_1_records"]
    assert list(selected_records[CURRENT_RANK + PROBES :]) == receipt["probe_panel_2_records"]
    assert len(set(receipt["probe_panel_1_records"]) & set(receipt["probe_panel_2_records"])) == 0

    prior_prices = np.memmap(
        prior_matrix_path, dtype="<i8", mode="r", shape=(RECORDS, 128)
    )
    next_prices = np.memmap(
        next_matrix_path, dtype="<i8", mode="r", shape=(RECORDS, 128)
    )
    pair_prices = np.memmap(
        pair_matrix_path,
        dtype="<i8",
        mode="r",
        shape=(RECORDS, PAIR_DIRECTIONS),
    )
    coordinates = np.concatenate(
        [
            old_coordinates(selected_records),
            np.asarray(prior_prices[selected_records][:, prior_indices], dtype=np.int64),
            np.asarray(next_prices[selected_records][:, next_indices], dtype=np.int64),
            np.asarray(pair_prices[selected_records][:, pair_coordinate_indices], dtype=np.int64),
        ],
        axis=1,
    )
    assert coordinates.shape == (CURRENT_RANK + 2 * PROBES, CURRENT_RANK)

    matrix_path = Path(receipt["matrix_path"])
    assert matrix_path == HERE / "basis659_probe512x2_direction4096.record-major.i64le"
    assert matrix_path.stat().st_size == receipt["matrix_bytes"]
    assert file_sha256(matrix_path) == receipt["matrix_sha256"]
    fingerprints = np.memmap(
        matrix_path,
        dtype="<i8",
        mode="r",
        shape=(CURRENT_RANK + 2 * PROBES, DIRECTIONS),
    )
    residual_items = global_result["nonzero_hinge_signed_lexicographic_prefix"]
    assert len(residual_items) == DIRECTIONS
    directions = [
        tuple(int(value) for value in item["direction"]) for item in residual_items
    ]
    assert all(directions[index] < directions[index + 1] for index in range(DIRECTIONS - 1))

    provenance = {
        "fingerprint_receipt_sha256": opening_hashes[str(receipt_path)],
        "fingerprint_matrix_sha256": receipt["matrix_sha256"],
        "member_sha256": opening_hashes[str(member_path)],
        "global_sha256": opening_hashes[str(global_path)],
        "pair_matrix_sha256": opening_hashes[str(pair_matrix_path)],
        "pair_receipt_sha256": opening_hashes[str(pair_receipt_path)],
        "pair_selection_sha256": opening_hashes[str(pair_selection_path)],
        "current796_member_sha256": opening_hashes[str(current796_path)],
        "prior_member_sha256": opening_hashes[str(prior_member_path)],
        "prior_matrix_sha256": opening_hashes[str(prior_matrix_path)],
        "next_matrix_sha256": opening_hashes[str(next_matrix_path)],
    }

    analyses = []
    for prime in PRIMES:
        square = np.asarray(coordinates[:CURRENT_RANK], dtype=np.int64).T
        inverse = inverse_mod(square, prime)
        row_lambdas = mod_matmul(
            np.asarray(fingerprints[:CURRENT_RANK], dtype=np.int64).T,
            inverse,
            prime,
        )
        predicted = mod_matmul(coordinates[CURRENT_RANK:], row_lambdas.T, prime)
        quotient = (
            np.asarray(fingerprints[CURRENT_RANK:], dtype=np.int64) - predicted
        ) % prime
        assert quotient.shape == (2 * PROBES, DIRECTIONS)
        residual = np.asarray(
            [int(item["coefficient"]) % prime for item in residual_items],
            dtype=np.int64,
        )
        analysis = analyze_prime(
            prime,
            quotient[:PROBES],
            quotient[PROBES:],
            residual,
            directions,
            provenance,
        )
        analyses.append(analysis)
        output_path = output_paths[len(analyses) - 1]
        output_path.write_text(
            json.dumps(analysis, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        print(
            json.dumps(
                {
                    "prime": prime,
                    "candidate_batches": analysis["candidate_batches_tested"],
                    "panel1_incompatible": analysis["total_panel1_incompatible_candidates"],
                    "combined_incompatible": analysis["total_combined_panel_incompatible_candidates"],
                    "whole_panel_cross_nonzero": analysis["whole_panel1_sparse_circuit_scan"]["cross_panel_nonzero_residual_pairing_circuits"],
                    "output": str(output_path),
                },
                sort_keys=True,
            ),
            flush=True,
        )

    prime_hashes = {
        str(analysis["prime"]): file_sha256(path)
        for analysis, path in zip(analyses, output_paths[:2])
    }
    comparison = compare_primes(analyses[0], analyses[1], prime_hashes)
    output_paths[2].write_text(
        json.dumps(comparison, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(comparison["target_assessment"], sort_keys=True), flush=True)

    cache_map.close()
    cache_file.close()
    assert {str(path): file_sha256(path) for path in paths} == opening_hashes


if __name__ == "__main__":
    main()
