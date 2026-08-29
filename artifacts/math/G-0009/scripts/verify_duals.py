#!/usr/bin/env python3
"""Replay the two compact exact nonmembership duals in the G-0009 reports.

The verifier reconstructs the named finite joint systems from the certified
orbit and held-out matrices.  For each sparse rational dual ``y`` it checks

    y^T A = 0                 and                 y^T b != 0

exactly over the integers after clearing denominators.  It also emits explicit
semantics for every row used by a dual, so the witness is independently
readable rather than merely an opaque vector of row indices.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import json
from math import factorial, lcm
from pathlib import Path
import sys

import numpy as np


HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import beta2_evaluate as beta2_eval  # noqa: E402
import cross_component_search as cross  # noqa: E402


N = 11
ORBIT_ROW_COUNT = 364
SCHEMA = "max11-g0009-sparse-dual-verification-v1"


def row_semantics(
    row: int,
    profiles: np.ndarray,
    directions: tuple[tuple[int, ...], ...],
    target: np.ndarray,
) -> dict[str, object]:
    """Return the exact meaning of a row in the 886-row joint convention."""

    if 0 <= row < len(profiles):
        profile = tuple(map(int, profiles[row]))
        state_count = cross.g6.assignment_count(profile)
        largest_level = max(level for level, count in enumerate(profile) if count)
        return {
            "joint_row": row,
            "block": "orbit",
            "orbit_profile_index": row,
            "value_multiplicities_for_levels_0_1_2_3": list(profile),
            "distinct_assignment_count": state_count,
            "candidate_row_formula": (
                "sum over all distinct assignments x with the stated multiplicities of "
                "max(sum_{ij in A} max(x_i,x_j), sum_{ij in B} max(x_i,x_j))"
            ),
            "target_formula": "distinct_assignment_count * largest_occupied_level",
            "target_value": int(target[row]),
            "largest_occupied_level": largest_level,
        }
    hinge_start = len(profiles)
    hinge_stop = hinge_start + len(directions)
    if hinge_start <= row < hinge_stop:
        direction_index = row - hinge_start
        return {
            "joint_row": row,
            "block": "heldout_hinge",
            "heldout_direction_index": direction_index,
            "primitive_direction": list(directions[direction_index]),
            "candidate_row_formula": (
                "coefficient of this canonical primitive ReLU hinge direction in the "
                "fully symmetrized atom"
            ),
            "target_value": int(target[row]),
        }
    linear_stop = hinge_stop + N
    if hinge_stop <= row < linear_stop:
        coordinate = row - hinge_stop + 1
        return {
            "joint_row": row,
            "block": "linear",
            "coordinate": coordinate,
            "candidate_row_formula": (
                "coefficient of the indicated ordered-cone linear coordinate in the "
                "fully symmetrized atom"
            ),
            "target_formula": "11! for coordinate 11 and 0 otherwise",
            "target_value": int(target[row]),
        }
    raise IndexError(f"joint row {row} outside 0..{linear_stop - 1}")


def verify_one(
    *,
    label: str,
    matrix: np.ndarray,
    target: np.ndarray,
    profiles: np.ndarray,
    directions: tuple[tuple[int, ...], ...],
    report_path: Path,
    result_key: str,
) -> dict[str, object]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    result = report["results"][result_key]
    exact = result["exact"]
    witness = exact["nonmembership_dual_witness"]
    if not isinstance(witness, dict):
        raise AssertionError(f"{label}: report has no nonmembership dual")
    if matrix.shape != (ORBIT_ROW_COUNT + len(directions) + N, result["columns"]):
        raise AssertionError(f"{label}: joint shape disagreement: {matrix.shape}")
    matrix_sha = cross.sha256_bytes(matrix.tobytes(order="C"))
    target_sha = cross.sha256_bytes(target.tobytes(order="C"))
    if matrix_sha != result["matrix_int64_c_sha256"]:
        raise AssertionError(f"{label}: reconstructed matrix hash disagreement")
    if target_sha != result["target_int64_c_sha256"]:
        raise AssertionError(f"{label}: reconstructed target hash disagreement")

    terms = witness["terms"]
    if cross.sha256_bytes(cross.canonical_bytes(terms)) != witness["terms_canonical_sha256"]:
        raise AssertionError(f"{label}: witness term hash disagreement")
    parsed = [(int(term["row"]), Fraction(term["coefficient"])) for term in terms]
    denominator_scale = 1
    for _row, coefficient in parsed:
        denominator_scale = lcm(denominator_scale, coefficient.denominator)

    # Object dtype ensures arbitrary-precision integer arithmetic.  The vector
    # is small (one entry per candidate column), so this is inexpensive.
    annihilation_numerators = np.zeros(matrix.shape[1], dtype=object)
    target_pairing_numerator = 0
    semantic_terms = []
    for row, coefficient in parsed:
        integer_coefficient = coefficient.numerator * (
            denominator_scale // coefficient.denominator
        )
        annihilation_numerators += integer_coefficient * matrix[row].astype(object)
        target_pairing_numerator += integer_coefficient * int(target[row])
        semantic_terms.append(
            {
                "coefficient": str(coefficient),
                "row": row,
                "semantics": row_semantics(row, profiles, directions, target),
            }
        )
    nonzero_column_indices = [
        index for index, value in enumerate(annihilation_numerators) if value
    ]
    pairing = Fraction(target_pairing_numerator, denominator_scale)
    expected_pairing = Fraction(witness["target_pairing"])
    if nonzero_column_indices:
        raise AssertionError(
            f"{label}: dual fails to annihilate {len(nonzero_column_indices)} columns"
        )
    if pairing != expected_pairing or not pairing:
        raise AssertionError(
            f"{label}: target pairing {pairing} != reported nonzero {expected_pairing}"
        )

    return {
        "label": label,
        "result_key": result_key,
        "report_path": cross.relative_root(report_path),
        "report_sha256": cross.sha256_path(report_path),
        "matrix_shape": list(matrix.shape),
        "matrix_int64_c_sha256": matrix_sha,
        "target_int64_c_sha256": target_sha,
        "dual_term_count": len(parsed),
        "dual_terms_canonical_sha256": witness["terms_canonical_sha256"],
        "cleared_denominator": denominator_scale,
        "annihilated_candidate_column_count": matrix.shape[1],
        "nonzero_annihilation_column_count": 0,
        "target_pairing": str(pairing),
        "target_pairing_nonzero": True,
        "verified_over_Q": True,
        "semantic_terms": semantic_terms,
    }


def build_verification(args: argparse.Namespace) -> dict[str, object]:
    baseline = cross.reduced_orbit_matrices(args.cross_classes, args.cross_orbits)
    selection, directions = cross.load_heldout_selection(args.selection)
    del selection
    cross_cut = cross.load_cut_matrix(
        args.cross_cut,
        "cross",
        args.selection,
        args.cross_classes,
        baseline["cross"].shape[1],
    )
    cut_target = np.zeros(len(directions) + N, dtype=np.int64)
    cut_target[-1] = factorial(N)
    joint_target = np.concatenate((baseline["target"], cut_target))
    cross_joint = np.concatenate((baseline["cross"], cross_cut), axis=0)

    beta_matrix, beta_target, beta_profiles, _files, _classes = beta2_eval.reduced_beta2(
        args.beta2_classes, args.beta2_orbits
    )
    if not np.array_equal(beta_target, baseline["target"]):
        raise AssertionError("cross/beta2 target convention disagreement")
    if not np.array_equal(beta_profiles, baseline["profiles"]):
        raise AssertionError("cross/beta2 orbit-profile convention disagreement")
    beta_cut = beta2_eval.load_cut_matrix(
        args.beta2_cut,
        args.selection,
        args.beta2_classes,
        beta_matrix.shape[1],
    )
    beta_joint = np.concatenate((beta_matrix, beta_cut), axis=0)

    verifications = [
        verify_one(
            label="cross_component_joint_nonmembership",
            matrix=cross_joint,
            target=joint_target,
            profiles=baseline["profiles"],
            directions=directions,
            report_path=args.cross_report,
            result_key="joint_cross",
        ),
        verify_one(
            label="beta2_common_edge_joint_nonmembership",
            matrix=beta_joint,
            target=joint_target,
            profiles=baseline["profiles"],
            directions=directions,
            report_path=args.beta2_report,
            result_key="joint_beta2",
        ),
    ]
    return {
        "schema": SCHEMA,
        "n": N,
        "joint_row_convention": {
            "row_count": len(joint_target),
            "orbit_rows": [0, ORBIT_ROW_COUNT - 1],
            "heldout_hinge_rows": [ORBIT_ROW_COUNT, ORBIT_ROW_COUNT + len(directions) - 1],
            "linear_rows": [ORBIT_ROW_COUNT + len(directions), len(joint_target) - 1],
            "normalization": (
                "candidate coefficients use internal a=11!*certificate coefficient; orbit "
                "targets are distinct-assignment MAX11 sums; hinge target is zero; linear "
                "target is 11!*e_11"
            ),
        },
        "selection_path": cross.relative_root(args.selection),
        "selection_sha256": cross.sha256_path(args.selection),
        "verification": verifications,
        "all_verified": all(item["verified_over_Q"] for item in verifications),
        "claim_boundary": (
            "Each witness excludes MAX11 from its named family on this reconstructed 886-row "
            "finite system.  It neither excludes larger atom families nor proves a global "
            "functional statement."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cross-classes", type=Path, required=True)
    parser.add_argument("--cross-orbits", type=Path, required=True)
    parser.add_argument("--cross-cut", type=Path, required=True)
    parser.add_argument("--cross-report", type=Path, required=True)
    parser.add_argument("--beta2-classes", type=Path, required=True)
    parser.add_argument("--beta2-orbits", type=Path, required=True)
    parser.add_argument("--beta2-cut", type=Path, required=True)
    parser.add_argument("--beta2-report", type=Path, required=True)
    parser.add_argument("--selection", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    document = build_verification(args)
    cross.write_json(args.output, document)


if __name__ == "__main__":
    main()
