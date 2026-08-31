#!/usr/bin/env python3
"""Independent exact replay of the small G-0119 inconsistency witness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from flint import fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREREGISTRATION.md"
PRODUCER_REPORT = HERE / "algebraic_signed_degree_operator_v1.json"
EXPECTED = {
    PREREGISTRATION: "f10eb7e013d0442ce54bd1ea8ce212916cfd8e6daf2bb6f27390c826bdc8d155",
    PRODUCER_REPORT: "85438a5fe983b638dd95f92c046be5b4a83ab88e0680de2f9c1c0eb05c0991cb",
}
EXPECTED_WITNESS = "21f13b2a9ee2be7f07b1b193621efdba17ee3303fabb829cf86c7a46aea88d8e"


class ReplayError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReplayError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def replay() -> dict[str, object]:
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"input drift: {observed}")
    report = json.loads(PRODUCER_REPORT.read_text(encoding="utf-8"))
    require(report.get("result") == "EXACT_Q_NONMEMBERSHIP", "producer result drift")
    decision = report["joint_exact_Q_decision"]
    witness = decision["witness"]
    matrix = [[int(value) for value in row] for row in witness["coefficient_matrix"]]
    target = [int(value) for value in witness["target"]]
    require(len(matrix) == len(target) == 21, "witness row count drift")
    require(all(len(row) == 24 for row in matrix), "witness column count drift")
    digest = canonical_sha({"matrix": matrix, "target": target})
    require(digest == EXPECTED_WITNESS == witness["canonical_sha256"], "witness digest drift")

    exact_rank = int(fmpz_mat(matrix).rank())
    augmented = [row + [rhs] for row, rhs in zip(matrix, target, strict=True)]
    exact_augmented_rank = int(fmpz_mat(augmented).rank())
    require((exact_rank, exact_augmented_rank) == (20, 21), "exact witness rank drift")
    require(
        exact_rank == int(witness["rank_over_Q"])
        and exact_augmented_rank == int(witness["augmented_rank_over_Q"]),
        "serialized rank claim drift",
    )

    # Potency direction: erase the only nonzero target entry.  The augmented
    # matrix must then lose the contradictory dimension and return to rank 20.
    require(sum(bool(value) for value in target) == 1, "target sparsity drift")
    zero_target_augmented = [row + [0] for row in matrix]
    zero_target_rank = int(fmpz_mat(zero_target_augmented).rank())
    require(zero_target_rank == exact_rank, "zero-target mutant did not collapse contradiction")

    require(report["MAX10_to_MAX11"]["evaluated"] is False, "MAX11 boundary drift")
    public = report["controls"]["public_certificates"]
    require(
        all(value["one_unit_first_coefficient_mutation_rejected"] for value in public.values()),
        "public coefficient mutation control drift",
    )
    require(
        report["controls"]["G0115_395_matrix_replay"]["one_unit_coefficient_mutation_rejected"],
        "G-0115 coefficient mutation control drift",
    )
    return {
        "schema": "g0119-independent-small-witness-replay-v1",
        "result": "CONSISTENT",
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in observed.items()
        }
        | {"script_sha256_at_start": sha256(SCRIPT)},
        "witness": {
            "rows": len(matrix),
            "columns": len(matrix[0]),
            "canonical_sha256": digest,
            "rank_over_Q": exact_rank,
            "augmented_rank_over_Q": exact_augmented_rank,
        },
        "controls": {
            "zero_target_mutant_rank": zero_target_rank,
            "zero_target_mutant_collapsed_contradiction": True,
            "producer_public_coefficient_mutations_rejected": sorted(public),
            "producer_G0115_coefficient_mutation_rejected": True,
            "MAX10_to_MAX11_not_evaluated": True,
        },
        "independence_boundary": (
            "Parsed only the serialized 21-row integer witness and recomputed its exact ranks; "
            "did not import the producer, load the full semantic matrices, regenerate lift "
            "features, or evaluate MAX11."
        ),
        "claim_boundary": (
            "Replays exact joint nonmembership only for the frozen G-0119 24-parameter operator. "
            "It says nothing about other operators or MAX11 representability."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    script_hash = sha256(SCRIPT)
    value = replay()
    require(sha256(SCRIPT) == script_hash, "verifier changed during execution")
    write_exclusive(args.output.resolve(), value)
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
