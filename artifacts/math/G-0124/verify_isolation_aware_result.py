#!/usr/bin/env python3
"""Independent exact verifier for the two G-0124 lower-transition null witnesses."""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

from flint import fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DEFAULT_RESULT = HERE / "isolation_aware_reynolds_gap_result_v1.json"
EXPECTED_RESULT_SHA256 = "63e2e30a42b102c3dea6e8cac781f28532f82573febc103a0ab756362da58142"
EXPECTED_PREREG_SHA256 = "c70d2e3edace6a9148796ec364d3c5b10e5ca285204e0db83beadd490a98134d"
EXPECTED_PRODUCER_SHA256 = "a9247ea54b9025fe799a89bbb1ff24cc5949c0c6250c55a994a6d350774517ee"
PRODUCER = HERE / "isolation_aware_reynolds_gap.py"
EXPECTED_STAGE = {
    "A": {
        "rows": 21_331,
        "columns": 18,
        "rank": 14,
        "augmented_rank": 15,
        "matrix_sha256": "80bf6f947bc842359ccc214dc3c617b31776cc75317f8cfe7ee4d9ea63759182",
        "witness_sha256": "041ad4699f9445d5a687753293a44f53727156dfcf4d3f51872084fa83ac9f97",
    },
    "B": {
        "rows": 21_331,
        "columns": 34,
        "rank": 28,
        "augmented_rank": 29,
        "matrix_sha256": "32824add0622f6e568b390e4bb5574b6fd6b4badc191b223641075c853cd066f",
        "witness_sha256": "f3f89d5b40e3812932415a4b15d56926f312625a0fe3290d8aacf96a8e2f7fde",
    },
}
EXPECTED_TARGET_SHA256 = "63e625ae45badc1d2b17450fb8e49d26eec906bfb57259a8133873c55ee90f60"
CERTIFICATES = ROOT / "literature/repos/max-relu-certificates/certificates"
CERT5 = CERTIFICATES / "certificate_5_2.json"
CERT6 = CERTIFICATES / "certificate_6_2.json"
CERT7 = CERTIFICATES / "certificate_7_3.json"
CERT8 = CERTIFICATES / "certificate_8_3.json"
EXPECTED_CERTIFICATE_SHA256 = {
    CERT5: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    CERT6: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    CERT7: "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
}


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


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def rank(matrix: list[list[int]]) -> int:
    return int(fmpz_mat(matrix).rank())


def augmented(matrix: list[list[int]], target: list[int]) -> list[list[int]]:
    require(len(matrix) == len(target), "matrix/target length mismatch")
    return [row + [value] for row, value in zip(matrix, target, strict=True)]


def row_label_key(value: dict[str, object]) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


def verify_witness(stage: str, decision: dict[str, object]) -> dict[str, object]:
    expected = EXPECTED_STAGE[stage]
    require(decision["stage"] == stage, f"Stage {stage} label drift")
    require(decision["result"] == "EXACT_Q_NONMEMBERSHIP", f"Stage {stage} result drift")
    require(decision["rows"] == expected["rows"], f"Stage {stage} row count drift")
    require(decision["columns"] == expected["columns"], f"Stage {stage} column count drift")
    require(decision["rank_over_Q"] == expected["rank"], f"Stage {stage} reported rank drift")
    require(
        decision["augmented_rank_over_Q"] == expected["augmented_rank"],
        f"Stage {stage} reported augmented rank drift",
    )
    require(decision["matrix_sha256"] == expected["matrix_sha256"], f"Stage {stage} matrix digest drift")
    require(decision["target_sha256"] == EXPECTED_TARGET_SHA256, f"Stage {stage} target digest drift")

    witness = decision["witness"]
    matrix = [[int(value) for value in row] for row in witness["coefficient_matrix"]]
    target = [int(value) for value in witness["target"]]
    require(len(matrix) == expected["augmented_rank"], f"Stage {stage} witness row count drift")
    require(all(len(row) == expected["columns"] for row in matrix), f"Stage {stage} witness width drift")
    require(len(witness["row_indices"]) == len(matrix), f"Stage {stage} witness index count drift")
    require(len(witness["row_labels"]) == len(matrix), f"Stage {stage} witness label count drift")
    payload = {"matrix": matrix, "target": target}
    observed_digest = canonical_sha(payload)
    require(observed_digest == expected["witness_sha256"], f"Stage {stage} witness payload digest drift")
    require(witness["canonical_sha256"] == observed_digest, f"Stage {stage} reported witness digest drift")
    matrix_rank = rank(matrix)
    augmented_rank = rank(augmented(matrix, target))
    require(
        (matrix_rank, augmented_rank) == (expected["rank"], expected["augmented_rank"]),
        f"Stage {stage} exact witness ranks failed",
    )
    require(sum(value != 0 for value in target) == 1, f"Stage {stage} target support drift")
    require(rank(augmented(matrix, [0] * len(target))) == matrix_rank, f"Stage {stage} zero-target control failed")
    return {
        "matrix": matrix,
        "target": target,
        "labels": witness["row_labels"],
        "summary": {
            "rows": len(matrix),
            "columns": len(matrix[0]),
            "rank_over_Q": matrix_rank,
            "augmented_rank_over_Q": augmented_rank,
            "canonical_sha256": observed_digest,
            "zero_target_rank_over_Q": matrix_rank,
        },
    }


def isolation_count(raw_pair: list[list[list[int]]], n: int) -> int:
    used = {int(label) for side in raw_pair for edge in side for label in edge}
    require(all(1 <= label <= n for label in used), "certificate label outside source arity")
    return n - len(used)


def q_distribution(path: Path, source_n: int) -> Counter[int]:
    document = json.loads(path.read_text(encoding="utf-8"))
    return Counter(isolation_count(term["pair"], source_n) for term in document["terms"])


def verify_q_distributions(document: dict[str, object]) -> dict[str, object]:
    for path, digest in EXPECTED_CERTIFICATE_SHA256.items():
        require(sha256(path) == digest, f"certificate binding drift: {path}")
    gap6 = q_distribution(CERT6, 6) + q_distribution(CERT5, 6)
    gap8 = q_distribution(CERT8, 8) + q_distribution(CERT7, 8)
    expected = {
        "Gap6_to_Gap7": gap6,
        "Gap8_to_Gap9": gap8,
    }
    output = {}
    for name, observed in expected.items():
        serialized = {
            int(key): int(value)
            for key, value in document["transitions"][name]["q_distribution_by_source_term"].items()
        }
        require(serialized == dict(observed), f"{name} q distribution drift")
        require(len(observed) >= 2, f"{name} q statistic is constant")
        output[name] = {str(key): value for key, value in sorted(observed.items())}
    return output


def verify_overlap(stage_a: dict[str, object], stage_b: dict[str, object]) -> dict[str, object]:
    rows_a = {
        row_label_key(label): row
        for label, row in zip(stage_a["labels"], stage_a["matrix"], strict=True)
    }
    rows_b = {
        row_label_key(label): row
        for label, row in zip(stage_b["labels"], stage_b["matrix"], strict=True)
    }
    shared = sorted(set(rows_a) & set(rows_b))
    require(shared, "the two witnesses have no common labelled rows")
    for key in shared:
        row_a = rows_a[key]
        row_b = rows_b[key]
        require(row_a[:17] == row_b[:17], "shared-row intercept mismatch")
        require(row_a[17] == sum(row_b[17:]), "Stage A main-effect/slope-sum mismatch")
    return {"shared_labelled_rows": len(shared), "intercepts_match": True, "stage_A_equals_slope_sum": True}


def verify(path: Path) -> dict[str, object]:
    observed_result_sha = sha256(path)
    require(observed_result_sha == EXPECTED_RESULT_SHA256, "result artifact hash drift")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document["schema"] == "g0124-isolation-aware-rooted-reynolds-v1", "schema drift")
    require(document["result"] == "LOWER_TRANSITION_EXACT_Q_NONMEMBERSHIP", "result drift")
    require(document["chosen_stage"] is None, "a lower stage was unexpectedly chosen")
    require(document["MAX10_to_MAX11"]["evaluated"] is False, "MAX11 holdout was opened")
    require(
        document["bindings"]["artifacts/math/G-0124/PREREGISTRATION.md"] == EXPECTED_PREREG_SHA256,
        "preregistration binding drift",
    )
    require(
        document["bindings"]["artifacts/math/G-0124/isolation_aware_reynolds_gap.py"]
        == EXPECTED_PRODUCER_SHA256,
        "producer binding drift",
    )
    stage_a = verify_witness("A", document["lower_decisions"]["stage_A"])
    stage_b = verify_witness("B", document["lower_decisions"]["stage_B"])
    overlap = verify_overlap(stage_a, stage_b)
    distributions = verify_q_distributions(document)
    controls = document["controls"]
    require(controls["old_witness"]["stage_A_old_witness_killed"], "Stage A did not kill old witness")
    require(controls["old_witness"]["stage_B_old_witness_killed"], "Stage B did not kill old witness")
    for stage in ("A", "B"):
        shift = controls["q_origin_shift"][stage]
        require(
            shift["span_preserved"]
            and shift["original_rank_over_Q"] == shift["shifted_rank_over_Q"] == shift["joined_rank_over_Q"],
            f"Stage {stage} q-origin span control failed",
        )
    return {
        "verdict": "VERIFIED_TWO_EXACT_Q_LOWER_NULLS",
        "result_sha256": observed_result_sha,
        "stage_A_witness": stage_a["summary"],
        "stage_B_witness": stage_b["summary"],
        "cross_stage_overlap": overlap,
        "independently_recomputed_q_distributions": distributions,
        "MAX10_to_MAX11_evaluated": False,
        "claim_boundary": document["claim_boundary"],
    }


def full_reconstruction(path: Path) -> dict[str, object]:
    quick = verify(path)
    require(sha256(PRODUCER) == EXPECTED_PRODUCER_SHA256, "producer drift before reconstruction")
    document = json.loads(path.read_text(encoding="utf-8"))
    producer = load_module("g0124_full_reconstruction_producer", PRODUCER)
    base = load_module("g0124_full_reconstruction_base", producer.BASE_PATH)
    producer.bind_inputs()
    base.bind_inputs()
    dp = base.load_dp("g0124_full_reconstruction_dp")
    c5 = base.load_certificate(base.CERT5, 5, 2)
    c6 = base.load_certificate(base.CERT6, 6, 2)
    c7 = base.load_certificate(base.CERT7, 7, 3)
    c8 = base.load_certificate(base.CERT8, 8, 3)
    first = producer.aggregate_isolation(
        base, dp, base.gap_terms(c6, c5, 6), 6, 2, "Gap6_to_Gap7"
    )
    second = producer.aggregate_isolation(
        base, dp, base.gap_terms(c8, c7, 8), 8, 3, "Gap8_to_Gap9"
    )
    aggregates = (first, second)
    labels = [
        {"transition": aggregate.transition, **label}
        for aggregate in aggregates
        for label in aggregate.row_labels
    ]
    stage_reports = {}
    for stage in ("A", "B"):
        decision = document["lower_decisions"][f"stage_{stage}"]
        matrix = producer.np.concatenate(
            [producer.stage_matrix(aggregate, stage) for aggregate in aggregates], axis=0
        )
        target = producer.np.concatenate([producer.target_for(aggregate) for aggregate in aggregates])
        require(matrix.shape == (21_331, EXPECTED_STAGE[stage]["columns"]), f"Stage {stage} full shape drift")
        require(producer.matrix_sha(matrix) == decision["matrix_sha256"], f"Stage {stage} full matrix digest drift")
        require(producer.vector_sha(target) == decision["target_sha256"], f"Stage {stage} full target digest drift")
        require(producer.rank_exact(matrix) == decision["rank_over_Q"], f"Stage {stage} full rank drift")
        require(
            producer.rank_exact(producer.np.column_stack((matrix, target)))
            == decision["augmented_rank_over_Q"],
            f"Stage {stage} full augmented rank drift",
        )
        witness = decision["witness"]
        indices = [int(index) for index in witness["row_indices"]]
        extracted_matrix = [[str(int(value)) for value in matrix[index]] for index in indices]
        extracted_target = [str(int(target[index])) for index in indices]
        extracted_labels = [labels[index] for index in indices]
        require(extracted_matrix == witness["coefficient_matrix"], f"Stage {stage} witness row extraction drift")
        require(extracted_target == witness["target"], f"Stage {stage} witness target extraction drift")
        require(extracted_labels == witness["row_labels"], f"Stage {stage} witness label extraction drift")
        stage_reports[stage] = {
            "rows": int(matrix.shape[0]),
            "columns": int(matrix.shape[1]),
            "rank_over_Q": int(decision["rank_over_Q"]),
            "augmented_rank_over_Q": int(decision["augmented_rank_over_Q"]),
            "matrix_sha256": producer.matrix_sha(matrix),
            "target_sha256": producer.vector_sha(target),
            "serialized_witness_rows_reextracted": len(indices),
            "row_indices_labels_values_match": True,
        }
    old_result = json.loads(producer.BASE_RESULT.read_text(encoding="utf-8"))
    transition_reports = {
        first.transition: producer.transition_report(
            base, first, old_result["transitions"][first.transition]
        ),
        second.transition: producer.transition_report(
            base, second, old_result["transitions"][second.transition]
        ),
    }
    for name, report in transition_reports.items():
        recorded = document["transitions"][name]
        require(report["matrix34_canonical_sha256"] == recorded["matrix34_canonical_sha256"], f"{name} matrix34 digest drift")
        require(report["row_order_sha256"] == recorded["row_order_sha256"], f"{name} row-order digest drift")
        require(report["q_distribution_by_source_term"] == recorded["q_distribution_by_source_term"], f"{name} q distribution drift")
    origin_shift = producer.span_shift_controls(base, aggregates)
    require(origin_shift == document["controls"]["q_origin_shift"], "q-origin span reconstruction drift")
    require(sha256(PRODUCER) == EXPECTED_PRODUCER_SHA256, "producer changed during reconstruction")
    return {
        "verdict": "FULL_SYSTEM_RECONSTRUCTION_CONSISTENT",
        "quick_witness_verdict": quick["verdict"],
        "implementation_independence": False,
        "independence_note": (
            "Reconstruction imports the frozen producer aggregation functions; it verifies full-system "
            "hashes and witness extraction but is not a clean-room semantic reimplementation."
        ),
        "stage_A": stage_reports["A"],
        "stage_B": stage_reports["B"],
        "transition_matrix34_and_row_order_digests_match": True,
        "q_origin_shift_recomputed": origin_shift,
        "MAX10_to_MAX11_evaluated": False,
    }


def self_test() -> dict[str, object]:
    matrix = [[1, 0], [0, 1], [1, 1]]
    target = [0, 0, 1]
    require(rank(matrix) == 2 and rank(augmented(matrix, target)) == 3, "rank-gap positive control failed")
    require(rank(augmented(matrix, [0, 0, 0])) == 2, "zero-target negative control failed")
    payload = {"matrix": matrix, "target": target}
    mutant = {"matrix": [row.copy() for row in matrix], "target": target.copy()}
    mutant["matrix"][0][0] += 1
    require(canonical_sha(payload) != canonical_sha(mutant), "digest mutation control failed")
    return {"rank_gap_control": [2, 3], "zero_target_control": 2, "digest_mutation_rejected": True}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=DEFAULT_RESULT)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--full-reconstruction", action="store_true")
    args = parser.parse_args()
    require(not (args.self_test and args.full_reconstruction), "choose at most one special mode")
    if args.self_test:
        value = self_test()
    elif args.full_reconstruction:
        value = full_reconstruction(args.result.resolve())
    else:
        value = verify(args.result.resolve())
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
