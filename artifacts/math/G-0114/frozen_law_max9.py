#!/usr/bin/env python3
"""Replay the frozen 148-weight local law on MAX8 -> MAX9 exactly."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from functools import reduce
import hashlib
from itertools import combinations
import json
from math import lcm
import os
from pathlib import Path
import sys
import time
from typing import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0090 = ROOT / "artifacts/math/G-0090"
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(G0090))
import degree_raising_identity as identity  # noqa: E402
import graph_recurrence as graph  # noqa: E402
import known_certificate_normal_form as normal  # noqa: E402


SCRIPT = Path(__file__).resolve()
LAW_REPORT = HERE / "degree_raising_identity_v1.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
EVALUATOR = G0090 / "known_certificate_normal_form.py"
EXPECTED = {
    "law_report": "1a59b11a0dbb6e4bd91861c001687d1f93000f1bde7340d62f027626e5f77d6f",
    "certificate_8_3": "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    "certificate_9_4": "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
    "evaluator": "eeb70dd51d2d24eb5a2a9215a7700c8d12822cd08b5116b8245c830b7855c57b",
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def one_based(pair: graph.Pair) -> normal.Pair:
    return tuple(
        tuple((u + 1, v + 1) for u, v in side)
        for side in pair
    )  # type: ignore[return-value]


def aggregate_shard(
    payload: tuple[int, list[tuple[int, int, normal.Pair]]]
) -> dict[str, object]:
    n, terms = payload
    base_linear = [0] * n
    mutation_linear = [0] * n
    base_hinges: dict[normal.Direction, int] = {}
    mutation_hinges: dict[normal.Direction, int] = {}
    raw_word_min: int | None = None
    raw_word_max = 0
    for base_coefficient, mutation_coefficient, pair in terms:
        column = normal.exact_semantic_column(pair, n)
        for index, value in enumerate(column.linear):
            base_linear[index] += base_coefficient * value
            mutation_linear[index] += mutation_coefficient * value
        for direction, value in column.hinges.items():
            if base_coefficient:
                updated = base_hinges.get(direction, 0) + base_coefficient * value
                if updated:
                    base_hinges[direction] = updated
                else:
                    base_hinges.pop(direction, None)
            if mutation_coefficient:
                updated = mutation_hinges.get(direction, 0) + mutation_coefficient * value
                if updated:
                    mutation_hinges[direction] = updated
                else:
                    mutation_hinges.pop(direction, None)
        raw_word_min = column.raw_words if raw_word_min is None else min(raw_word_min, column.raw_words)
        raw_word_max = max(raw_word_max, column.raw_words)
    return {
        "base_linear": base_linear,
        "mutation_linear": mutation_linear,
        "base_hinges": base_hinges,
        "mutation_hinges": mutation_hinges,
        "classes": len(terms),
        "raw_word_min": raw_word_min,
        "raw_word_max": raw_word_max,
    }


def add_hinges(target: dict[normal.Direction, int], source: dict[normal.Direction, int]) -> None:
    for direction, value in source.items():
        updated = target.get(direction, 0) + value
        if updated:
            target[direction] = updated
        else:
            target.pop(direction, None)


def residual_digest(linear: Sequence[int], hinges: dict[normal.Direction, int], denominator: int) -> str:
    payload = {
        "linear": [str(Fraction(value, denominator)) for value in linear],
        "hinges": [
            {"direction": list(direction), "coefficient": str(Fraction(value, denominator))}
            for direction, value in sorted(hinges.items())
        ],
    }
    return hashlib.sha256(canonical(payload)).hexdigest()


def first_residual(
    linear: Sequence[int], hinges: dict[normal.Direction, int], denominator: int
) -> dict[str, object] | None:
    for index, value in enumerate(linear):
        if value:
            return {"kind": "linear", "coordinate": index + 1,
                    "coefficient": str(Fraction(value, denominator))}
    if hinges:
        direction = min(hinges)
        return {"kind": "hinge", "direction": list(direction),
                "coefficient": str(Fraction(hinges[direction], denominator))}
    return None


def load_law() -> tuple[dict[str, Fraction], str]:
    report = json.loads(LAW_REPORT.read_text(encoding="utf-8"))
    decision = report["local_incidence_test"]["joint_shared_law_decision"]
    require(decision["result"] == "EXACT_Q_MEMBERSHIP", "bound law is not a membership solution")
    law = {
        item["descriptor"]: Fraction(item["coefficient"])
        for item in decision["support"]
    }
    require(len(law) == decision["support_size"] == 148, "frozen law support drift")
    return law, hashlib.sha256(canonical(decision["support"])).hexdigest()


def build_fibers(law: dict[str, Fraction]) -> dict[str, object]:
    document = json.loads(CERT8.read_text(encoding="utf-8"))
    require(document["n"] == 8 and len(document["terms"]) == 69, "MAX8 source drift")
    edges = tuple(combinations(range(9), 2))
    base_coefficients: dict[str, Fraction] = defaultdict(Fraction)
    mutation_coefficients: dict[str, Fraction] = defaultdict(Fraction)
    representatives: dict[str, normal.Pair] = {}
    matched_by_relation = {"share_one_nonloop": 0, "disjoint_nonloop": 0}
    raw_unequal = 0
    matched_raw = 0
    law_signature_seen: dict[str, int] = defaultdict(int)
    mutation_signature: str | None = None
    for term in document["terms"]:
        coefficient = Fraction(term["coefficient"])
        pair = graph.read_pair(term["pair"], 8)
        for left in edges:
            for right in edges:
                if left == right or set(left) == set(right):
                    continue
                kind = graph.relation(left, right)
                raw_unequal += 1
                signature = identity.local_signature(pair, left, right, 9)
                weight = law.get(signature)
                if weight is None:
                    continue
                if mutation_signature is None:
                    mutation_signature = signature
                lifted: graph.Pair = (
                    tuple(sorted(pair[0] + (left,))),
                    tuple(sorted(pair[1] + (right,))),
                )
                full_class = graph.certificate(lifted, 9)
                base_coefficients[full_class] += coefficient * weight
                if signature == mutation_signature:
                    mutation_coefficients[full_class] += coefficient
                representatives.setdefault(full_class, one_based(lifted))
                matched_by_relation[kind] += 1
                law_signature_seen[signature] += 1
                matched_raw += 1
    require(raw_unequal == 69 * (34_776 // 69 + 52_164 // 69), "unequal raw census drift")
    require(mutation_signature is not None, "no frozen-law signature occurred at n=9")
    base_coefficients = {key: value for key, value in base_coefficients.items() if value}
    mutation_coefficients = {key: value for key, value in mutation_coefficients.items() if value}
    require(base_coefficients, "frozen law produced no nonzero quotient coefficient")
    require(mutation_coefficients, "mutation signature cancelled on every graph class")
    class_keys = sorted(set(base_coefficients) | set(mutation_coefficients))
    denominator = reduce(lcm, (
        value.denominator for value in list(base_coefficients.values())
        + list(mutation_coefficients.values())
    ), 1)
    integer_terms = [
        (
            base_coefficients.get(key, Fraction()).numerator
            * (denominator // base_coefficients.get(key, Fraction()).denominator),
            mutation_coefficients.get(key, Fraction()).numerator
            * (denominator // mutation_coefficients.get(key, Fraction()).denominator),
            representatives[key],
        )
        for key in class_keys
    ]
    require(all(base or mutation for base, mutation, _pair in integer_terms), "zero class escaped filter")
    return {
        "integer_terms": integer_terms,
        "denominator": denominator,
        "raw_unequal": raw_unequal,
        "matched_raw": matched_raw,
        "matched_by_relation": matched_by_relation,
        "frozen_signatures_seen": len(law_signature_seen),
        "frozen_signatures_missing": len(law) - len(law_signature_seen),
        "nonzero_base_classes": len(base_coefficients),
        "nonzero_mutation_classes": len(mutation_coefficients),
        "mutation_signature": mutation_signature,
        "base_class_coefficients_sha256": hashlib.sha256(canonical([
            [hashlib.sha256(bytes.fromhex(key)).hexdigest(), str(base_coefficients[key])]
            for key in sorted(base_coefficients)
        ])).hexdigest(),
    }


def run(output: Path, workers: int) -> None:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {
        "law_report": sha256(LAW_REPORT),
        "certificate_8_3": sha256(CERT8),
        "certificate_9_4": sha256(CERT9),
        "evaluator": sha256(EVALUATOR),
    }
    require(bindings == EXPECTED, "bound input drift")
    law, law_support_sha256 = load_law()
    fibers = build_fibers(law)
    integer_terms = fibers.pop("integer_terms")
    worker_count = min(workers, len(integer_terms))
    shards: list[list[tuple[int, int, normal.Pair]]] = [[] for _ in range(worker_count)]
    for index, term in enumerate(integer_terms):
        shards[index % worker_count].append(term)
    base_linear = [0] * 9
    mutation_linear = [0] * 9
    base_hinges: dict[normal.Direction, int] = {}
    mutation_hinges: dict[normal.Direction, int] = {}
    processed = 0
    raw_word_min: int | None = None
    raw_word_max = 0
    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(aggregate_shard, (9, shard)) for shard in shards]
        for future in as_completed(futures):
            result = future.result()
            processed += int(result["classes"])
            for index, value in enumerate(result["base_linear"]):
                base_linear[index] += int(value)
            for index, value in enumerate(result["mutation_linear"]):
                mutation_linear[index] += int(value)
            add_hinges(base_hinges, result["base_hinges"])
            add_hinges(mutation_hinges, result["mutation_hinges"])
            shard_min = result["raw_word_min"]
            if shard_min is not None:
                raw_word_min = int(shard_min) if raw_word_min is None else min(raw_word_min, int(shard_min))
            raw_word_max = max(raw_word_max, int(result["raw_word_max"]))
    require(processed == len(integer_terms), "semantic class census drift")
    denominator = int(fibers["denominator"])
    residual_linear = list(base_linear)
    residual_linear[8] -= denominator
    residual = first_residual(residual_linear, base_hinges, denominator)
    mutation_residual = first_residual(mutation_linear, mutation_hinges, denominator)
    require(mutation_residual is not None, "one-unit law-weight mutation changed no semantic row")
    report = {
        "schema": "max11-g0114-frozen-law-max9-v1",
        "bindings": {**bindings, "script_sha256_at_start": script_hash,
                     "law_support_sha256": law_support_sha256},
        "claim_boundary": (
            "Exact replay of one frozen 148-weight local-signature solution on the public "
            "MAX8-derived unequal-nonloop lift. Failure rejects this law vector, not the "
            "entire small-arity solution space, all possible operators, or MAX11."
        ),
        "frozen_law": {
            "support_size": len(law),
            "source": "local_incidence_test.joint_shared_law_decision.support",
            "missing_signature_policy": "zero",
        },
        "fiber_census": fibers,
        "complete_normal_form": {
            "classes_processed": processed,
            "worker_count": worker_count,
            "coefficient_denominator_lcm_digits": len(str(denominator)),
            "raw_direction_word_count_min": raw_word_min,
            "raw_direction_word_count_max": raw_word_max,
            "residual_linear_support_size": sum(value != 0 for value in residual_linear),
            "residual_hinge_support_size": len(base_hinges),
            "residual_sha256": residual_digest(residual_linear, base_hinges, denominator),
        },
        "decision": {
            "result": "EXACT_MAX9_REPLAY_PASS" if residual is None else "EXACT_MAX9_REPLAY_FAIL",
            "first_residual": residual,
            "all_linear_and_hinge_rows_replayed": True,
        },
        "controls": {
            "one_unit_first_occurring_law_weight_mutation_rejected": True,
            "mutation_first_nonzero_row": mutation_residual,
            "quotient_coordinate_relabel_and_branch_swap": graph.invariant_controls(),
            "fiber_raw_count_reconciled": True,
        },
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as destination:
        destination.write(canonical(report))
        destination.flush()
        os.fsync(destination.fileno())
    print(json.dumps({
        "output": str(output),
        "decision": report["decision"]["result"],
        "classes": processed,
        "matched_raw": fibers["matched_raw"],
        "residual_hinges": len(base_hinges),
        "wall_seconds": report["wall_seconds"],
    }, sort_keys=True))


def self_test() -> dict[str, object]:
    certificate = normal.load_certificate(8)
    pair = certificate.terms[0].pair
    dynamic = normal.direction_histogram(pair, 8)
    require(sum(dynamic.values()) == 40_320, "subset DP permutation count")
    small = normal.load_certificate(5).terms[1].pair
    require(normal.direction_histogram(small, 5) == normal.brute_direction_histogram(small, 5),
            "subset DP disagrees with literal permutations")
    return {"subset_DP_matches_bruteforce": True, "n8_permutation_census": 40_320}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--workers", type=int, default=min(16, os.cpu_count() or 1))
    args = parser.parse_args()
    require(1 <= args.workers <= 32, "workers outside 1..32")
    if args.self_test:
        require(args.output is None, "self-test refuses output")
        print(json.dumps(self_test(), sort_keys=True))
        return
    require(args.output is not None and not args.output.exists(), "unused output required")
    run(args.output, args.workers)


if __name__ == "__main__":
    main()
