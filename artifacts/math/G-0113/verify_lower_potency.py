#!/usr/bin/env python3
"""Method-disjoint replay of the G-0113 lower-arity null.

Unlike the producer's subset dynamic program, this verifier literally visits
all 7! label orders for every lifted atom and accumulates the ordered-cone
linear and hinge coefficients.  It is confirmatory self-replay by the same
agent, not independent T2 review.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import time
from typing import Sequence

from flint import fmpz_mat


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULT = HERE / "lower_potency_v1.json"
CERT6 = ROOT / "subjects/max-relu-known/certificates/certificate_6_2.json"
EXPECTED = {
    "result": "d67f102624dfa494b76fd2c5ad7602c91c2ab5786fee68d34cdfb37c04aaf665",
    "cert6": "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
}

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Semantic = tuple[tuple[int, ...], dict[tuple[int, ...], int]]


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode("ascii")


def object_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def parse_source() -> list[dict[str, object]]:
    require(sha256(CERT6) == EXPECTED["cert6"], "MAX6 certificate hash drift")
    document = json.loads(CERT6.read_text(encoding="utf-8"))
    require(document.get("n") == 6 and len(document.get("terms", [])) == 4, "MAX6 shape drift")
    output = []
    for term in document["terms"]:
        sides = []
        for raw_side in term["pair"]:
            require(len(raw_side) == 2, "MAX6 branch degree drift")
            sides.append(tuple((int(u) - 1, int(v) - 1) for u, v in raw_side))
        output.append({"coefficient": Fraction(term["coefficient"]), "pair": (sides[0], sides[1])})
    return output


def attachment_choices(side: Side) -> tuple[tuple[Edge, Edge], ...]:
    choices = []
    for u, v in side:
        choices.extend((((u, 6), (u, 6)), ((v, 6), (v, 6)), ((u, 6), (v, 6))))
    choices.append(((6, 6), (6, 6)))
    require(len(choices) == 7, "attachment choice drift")
    return tuple(choices)


def lifted(pair: Pair, left_choice: int, right_choice: int) -> Pair:
    return (
        pair[0] + attachment_choices(pair[0])[left_choice],
        pair[1] + attachment_choices(pair[1])[right_choice],
    )


def vanishes_on_ordered_cone(direction: Sequence[int]) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


def direct_normal_form(pair: Pair) -> Semantic:
    """Brute force the full S7 sum with no subset-DP or histogram formula."""

    linear = [0] * 7
    hinges: dict[tuple[int, ...], int] = defaultdict(int)
    for order in itertools.permutations(range(7)):
        position = [0] * 7
        for rank, vertex in enumerate(order):
            position[vertex] = rank
        left = [0] * 7
        right = [0] * 7
        for u, v in pair[0]:
            left[max(position[u], position[v])] += 1
        for u, v in pair[1]:
            right[max(position[u], position[v])] += 1
        for index, value in enumerate(left):
            linear[index] += value
        direction = tuple(right[index] - left[index] for index in range(7))
        if not any(direction):
            continue
        divisor = math.gcd(*(abs(value) for value in direction))
        first = next(value for value in direction if value)
        if first < 0:
            for index, value in enumerate(direction):
                linear[index] += value
            primitive = tuple(-value // divisor for value in direction)
        else:
            primitive = tuple(value // divisor for value in direction)
        if not vanishes_on_ordered_cone(primitive):
            hinges[primitive] += divisor
    return tuple(linear), {direction: value for direction, value in hinges.items() if value}


def add_semantic(target: tuple[list[int], dict[tuple[int, ...], int]], source: Semantic, weight: int) -> None:
    for index, value in enumerate(source[0]):
        target[0][index] += weight * value
    for direction, value in source[1].items():
        updated = target[1].get(direction, 0) + weight * value
        if updated:
            target[1][direction] = updated
        else:
            target[1].pop(direction, None)


def columns_to_rows(columns: list[Semantic]) -> tuple[list[list[int]], list[object]]:
    directions = sorted({direction for _linear, hinges in columns for direction in hinges})
    # Lists, rather than tuples, deliberately match the JSON round trip of the
    # producer labels.  The frozen v1 verifier stopped before scientific
    # acceptance because this normalization was missing.
    labels: list[object] = [["linear", index] for index in range(7)] + [["hinge", list(direction)] for direction in directions]
    rows = [[linear[index] for linear, _hinges in columns] for index in range(7)]
    rows.extend([[hinges.get(direction, 0) for _linear, hinges in columns] for direction in directions])
    return rows, labels


def replay_separator(subject: dict[str, object], rows: list[list[int]], labels: list[object]) -> dict[str, object]:
    support = subject["separator"]["primitive_integer_support"]
    weights = [0] * len(rows)
    for item in support:
        row = int(item["row"])
        require(item["label"] == labels[row], f"separator label drift at row {row}")
        weights[row] = int(item["weight"])
    residuals = [sum(weights[row] * rows[row][column] for row in range(len(rows))) for column in range(len(rows[0]))]
    pairing = weights[6]
    require(not any(residuals), "separator does not annihilate direct matrix")
    require(str(pairing) == subject["separator"]["target_pairing"] and pairing != 0, "target pairing drift")
    mutation = residuals[0] + weights[next(index for index, weight in enumerate(weights) if weight)]
    require(mutation != 0, "one-entry mutation escaped")
    return {
        "support_size": sum(weight != 0 for weight in weights),
        "target_pairing": str(pairing),
        "all_columns_annihilated": True,
        "one_entry_mutation_detected": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "unused output path required")
    begun = time.perf_counter()
    require(sha256(RESULT) == EXPECTED["result"], "producer result hash drift")
    producer = json.loads(RESULT.read_text(encoding="utf-8"))
    require(producer.get("result") == "LOWER_RAW_POTENCY_FAIL_STOP", "unexpected producer decision")
    source = parse_source()
    raw: list[Semantic] = []
    descriptors = []
    denominator = math.lcm(*(term["coefficient"].denominator for term in source))
    tied_accumulators = [([0] * 7, {}) for _ in range(49)]
    for term_index, term in enumerate(source):
        coefficient: Fraction = term["coefficient"]
        weight = coefficient.numerator * (denominator // coefficient.denominator)
        for left_choice in range(7):
            for right_choice in range(7):
                semantic = direct_normal_form(lifted(term["pair"], left_choice, right_choice))
                raw.append(semantic)
                descriptors.append({"term": term_index, "left_choice": left_choice, "right_choice": right_choice})
                add_semantic(tied_accumulators[left_choice * 7 + right_choice], semantic, weight)
    tied = [(tuple(linear), dict(hinges)) for linear, hinges in tied_accumulators]
    require(len(raw) == 196 and len(tied) == 49, "family census drift")

    raw_rows, raw_labels = columns_to_rows(raw)
    tied_rows, tied_labels = columns_to_rows(tied)
    require(object_sha256(descriptors) == producer["family"]["raw_descriptor_sha256"], "descriptor hash mismatch")
    require(object_sha256(raw_rows) == producer["family"]["raw_complete_row_matrix_sha256"], "RAW matrix hash mismatch")
    require(object_sha256(tied_rows) == producer["family"]["tied_complete_row_matrix_sha256"], "TIED matrix hash mismatch")

    raw_target = [0] * len(raw_rows)
    raw_target[6] = 1
    tied_target = [0] * len(tied_rows)
    tied_target[6] = 1
    raw_rank = int(fmpz_mat(raw_rows).rank())
    raw_augmented = int(fmpz_mat([row + [raw_target[index]] for index, row in enumerate(raw_rows)]).rank())
    tied_rank = int(fmpz_mat(tied_rows).rank())
    tied_augmented = int(fmpz_mat([row + [tied_target[index]] for index, row in enumerate(tied_rows)]).rank())
    require((raw_rank, raw_augmented) == (62, 63), "RAW rank pair mismatch")
    require((tied_rank, tied_augmented) == (31, 32), "TIED rank pair mismatch")

    report = {
        "schema": "max11-g0113-lower-potency-bruteforce-replay-v1",
        "result": "CONSISTENT",
        "bindings": {
            "producer_result_sha256": EXPECTED["result"],
            "source_certificate_sha256": EXPECTED["cert6"],
            "verifier_sha256": sha256(Path(__file__)),
        },
        "method": "literal enumeration of all 7! label orders for every lifted atom",
        "orders_per_atom": math.factorial(7),
        "raw_atoms": len(raw),
        "RAW": {
            "matrix_sha256": object_sha256(raw_rows),
            "rank_Q": raw_rank,
            "augmented_rank_Q": raw_augmented,
            "separator_replay": replay_separator(producer["RAW"], raw_rows, raw_labels),
        },
        "TIED": {
            "matrix_sha256": object_sha256(tied_rows),
            "rank_Q": tied_rank,
            "augmented_rank_Q": tied_augmented,
            "separator_replay": replay_separator(producer["TIED"], tied_rows, tied_labels),
        },
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Same-agent method-disjoint replay of the bounded MAX6-to-MAX7 family null. "
            "It is not T2 review and makes no MAX11 or unrestricted-network claim."
        ),
    }
    descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as target:
        target.write(canonical_bytes(report))
        target.flush()
        os.fsync(target.fileno())
    print(json.dumps({"output": str(args.output), "result": "CONSISTENT", "wall_seconds": report["wall_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
