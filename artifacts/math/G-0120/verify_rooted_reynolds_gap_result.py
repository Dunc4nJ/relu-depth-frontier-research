#!/usr/bin/env python3
"""Independent exact verifier for the frozen G-0120 null witness."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from flint import fmpz_mat


HERE = Path(__file__).resolve().parent
DEFAULT_RESULT = HERE / "rooted_reynolds_gap_result.json"
EXPECTED_RESULT_SHA256 = "918de947cd2fb0bbc49849cbe76253b28f282c4f553c46525c73d6e98a6c9754"
EXPECTED_MATRIX_SHA256 = "9261eefc7a1ef15dce5e43bb2fd97a683670671b8a88be3821a3fe5338f1c51d"
EXPECTED_TARGET_SHA256 = "c324b6a1eb38cba6045c890864a3930da3c6fefc2af77d45559488ad9d9581ed"
EXPECTED_WITNESS_SHA256 = "fb2100573ae3c72ddbea628834ac5f575ef9a96ece8d35efb70614bd5bcfe07c"


class VerificationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_sha(value: object) -> str:
    payload = (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return hashlib.sha256(payload).hexdigest()


def rank(matrix: list[list[int]]) -> int:
    return int(fmpz_mat(matrix).rank())


def augmented(matrix: list[list[int]], target: list[int]) -> list[list[int]]:
    require(len(matrix) == len(target), "matrix/target length mismatch")
    return [row + [value] for row, value in zip(matrix, target, strict=True)]


def verify(path: Path) -> dict[str, object]:
    observed_sha = sha256(path)
    require(observed_sha == EXPECTED_RESULT_SHA256, "result artifact hash drift")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document["schema"] == "g0120-rooted-reynolds-gap-v1", "schema drift")
    require(document["result"] == "EXACT_Q_NONMEMBERSHIP", "result drift")
    require(document["MAX10_to_MAX11"]["evaluated"] is False, "MAX11 stop-rule drift")

    decision = document["joint_exact_Q_decision"]
    require(decision["rows"] == 21_331 and decision["columns"] == 17, "joint shape drift")
    require(decision["rank_over_Q"] == 13, "reported matrix rank drift")
    require(decision["augmented_rank_over_Q"] == 14, "reported augmented rank drift")
    require(decision["matrix_sha256"] == EXPECTED_MATRIX_SHA256, "matrix digest drift")
    require(decision["target_sha256"] == EXPECTED_TARGET_SHA256, "target digest drift")

    witness = decision["witness"]
    matrix = [[int(value) for value in row] for row in witness["coefficient_matrix"]]
    target = [int(value) for value in witness["target"]]
    require(len(matrix) == 14 and all(len(row) == 17 for row in matrix), "witness shape drift")
    payload = {"matrix": matrix, "target": target}
    require(canonical_sha(payload) == EXPECTED_WITNESS_SHA256, "witness digest drift")
    require(witness["canonical_sha256"] == EXPECTED_WITNESS_SHA256, "reported witness digest drift")
    matrix_rank = rank(matrix)
    augmented_rank = rank(augmented(matrix, target))
    require((matrix_rank, augmented_rank) == (13, 14), "exact witness ranks failed")

    # The producer conservatively retained fourteen independent augmented rows.
    # Its first thirteen rows already form a smaller exact inconsistency witness.
    reduced_matrix = matrix[:13]
    reduced_target = target[:13]
    reduced_rank = rank(reduced_matrix)
    reduced_augmented_rank = rank(augmented(reduced_matrix, reduced_target))
    require((reduced_rank, reduced_augmented_rank) == (12, 13), "reduced witness ranks failed")
    reduced_digest = canonical_sha({"matrix": reduced_matrix, "target": reduced_target})

    zero_target = [0] * len(target)
    require(rank(augmented(matrix, zero_target)) == matrix_rank, "zero-target control failed")
    require(sum(value != 0 for value in target) == 1, "planted target support drift")

    transitions = document["transitions"]
    expected_transitions = {
        "Gap6_to_Gap7": (5_488, 909, 630, 7),
        "Gap8_to_Gap9": (255_150, 35_327, 20_685, 9),
    }
    for name, (raw, classes, hinges, linear) in expected_transitions.items():
        report = transitions[name]
        require(report["raw_descriptors"] == raw, f"{name} raw count drift")
        require(report["signed_W_classes"] == classes, f"{name} signed-class drift")
        require(report["complete_hinge_rows"] == hinges, f"{name} hinge-row drift")
        require(report["linear_rows"] == linear, f"{name} linear-row drift")
        reconciliation = report["reconciliation"]
        require(
            reconciliation["raw_descriptors"]
            == reconciliation["fiber_raw_sum"]
            == reconciliation["orbit_raw_sum"]
            == raw,
            f"{name} reconciliation failed",
        )

    controls = document["controls"]
    require(controls["moving_root_mutant_rejected"], "moving-root mutant escaped")
    require(controls["unrooted_classifier_mutant_rejected"], "unrooted mutant escaped")
    require(controls["branch_edge_semantic_mutant_rejected"], "branch-edge mutant escaped")
    for replay in controls["public_certificate_replays"].values():
        require(replay["hinge_residual_nonzeros"] == 0, "public replay hinge residual")
        require(replay["one_unit_first_coefficient_mutation_rejected"], "public mutation escaped")
    for replay in controls["source_gap_replays"].values():
        require(replay["hinge_residual_nonzeros"] == 0, "gap replay hinge residual")
        require(replay["termwise_induction_replayed"], "termwise induction replay failed")

    return {
        "verdict": "VERIFIED_EXACT_Q_NONMEMBERSHIP",
        "result_sha256": observed_sha,
        "full_witness": {
            "rows": len(matrix),
            "columns": len(matrix[0]),
            "rank_over_Q": matrix_rank,
            "augmented_rank_over_Q": augmented_rank,
            "canonical_sha256": EXPECTED_WITNESS_SHA256,
        },
        "reduced_witness": {
            "rows": len(reduced_matrix),
            "columns": len(reduced_matrix[0]),
            "rank_over_Q": reduced_rank,
            "augmented_rank_over_Q": reduced_augmented_rank,
            "canonical_sha256": reduced_digest,
        },
        "zero_target_control_rank_over_Q": matrix_rank,
        "MAX10_to_MAX11_evaluated": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    args = parser.parse_args()
    print(json.dumps(verify(args.result.resolve()), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
