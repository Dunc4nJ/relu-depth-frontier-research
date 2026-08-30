#!/usr/bin/env python3
"""Final exact test of the frozen law plus four uniform relation corrections."""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from fractions import Fraction
from functools import reduce
import hashlib
from itertools import combinations_with_replacement
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
import frozen_law_max9 as frozen  # noqa: E402
import graph_recurrence as graph  # noqa: E402
import known_certificate_normal_form as normal  # noqa: E402


SCRIPT = Path(__file__).resolve()
FROZEN_REPORT = HERE / "frozen_law_max9_v1.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
EXPECTED = {
    "frozen_report": "90519cde87e30c26c4d91b50873164b91b9e36b85ff55466491c07dd38e2011c",
    "certificate_8_3": "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    "evaluator": "eeb70dd51d2d24eb5a2a9215a7700c8d12822cd08b5116b8245c830b7855c57b",
}
COLUMNS = (
    "frozen_law",
    "common_nonloop",
    "share_one_nonloop",
    "disjoint_nonloop",
    "has_loop",
)


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


def add_hinges(target: dict[normal.Direction, int], source: dict[normal.Direction, int]) -> None:
    for direction, value in source.items():
        updated = target.get(direction, 0) + value
        if updated:
            target[direction] = updated
        else:
            target.pop(direction, None)


def aggregate_shard(
    payload: tuple[int, list[tuple[tuple[int, ...], normal.Pair]]]
) -> dict[str, object]:
    n, terms = payload
    linears = [[0] * n for _ in COLUMNS]
    hinges: list[dict[normal.Direction, int]] = [{} for _ in COLUMNS]
    raw_word_min: int | None = None
    raw_word_max = 0
    for coefficients, pair in terms:
        column = normal.exact_semantic_column(pair, n)
        for column_index, coefficient in enumerate(coefficients):
            if not coefficient:
                continue
            for coordinate, value in enumerate(column.linear):
                linears[column_index][coordinate] += coefficient * value
            for direction, value in column.hinges.items():
                updated = hinges[column_index].get(direction, 0) + coefficient * value
                if updated:
                    hinges[column_index][direction] = updated
                else:
                    hinges[column_index].pop(direction, None)
        raw_word_min = column.raw_words if raw_word_min is None else min(raw_word_min, column.raw_words)
        raw_word_max = max(raw_word_max, column.raw_words)
    return {
        "linears": linears,
        "hinges": hinges,
        "classes": len(terms),
        "raw_word_min": raw_word_min,
        "raw_word_max": raw_word_max,
    }


def build_class_coefficients(law: dict[str, Fraction]) -> dict[str, object]:
    document = json.loads(CERT8.read_text(encoding="utf-8"))
    require(document["n"] == 8 and len(document["terms"]) == 69, "MAX8 source drift")
    edges = tuple(combinations_with_replacement(range(9), 2))
    class_coefficients: dict[str, list[Fraction]] = {}
    representatives: dict[str, normal.Pair] = {}
    raw_counts = {name: 0 for name in COLUMNS[1:]}
    frozen_matched_raw = 0
    for term in document["terms"]:
        source_coefficient = Fraction(term["coefficient"])
        pair = graph.read_pair(term["pair"], 8)
        for left in edges:
            for right in edges:
                kind = identity.edge_relation(left, right)
                signature_weight = Fraction()
                if kind in ("share_one_nonloop", "disjoint_nonloop"):
                    signature = identity.local_signature(pair, left, right, 9)
                    signature_weight = law.get(signature, Fraction())
                    if signature_weight:
                        frozen_matched_raw += 1
                lifted: graph.Pair = (
                    tuple(sorted(pair[0] + (left,))),
                    tuple(sorted(pair[1] + (right,))),
                )
                full_class = graph.certificate(lifted, 9)
                coefficients = class_coefficients.setdefault(full_class, [Fraction() for _ in COLUMNS])
                coefficients[0] += source_coefficient * signature_weight
                relation_index = COLUMNS.index(kind)
                coefficients[relation_index] += source_coefficient
                raw_counts[kind] += 1
                representatives.setdefault(full_class, frozen.one_based(lifted))
    expected = {
        "common_nonloop": 69 * 36,
        "share_one_nonloop": 34_776,
        "disjoint_nonloop": 52_164,
        "has_loop": 69 * (45 * 45 - 36 - 504 - 756),
    }
    require(raw_counts == expected, "raw relation census drift")
    class_coefficients = {
        key: values for key, values in class_coefficients.items() if any(values)
    }
    denominator = reduce(lcm, (
        value.denominator
        for values in class_coefficients.values()
        for value in values
        if value
    ), 1)
    integer_terms = []
    for key in sorted(class_coefficients):
        values = class_coefficients[key]
        integers = tuple(value.numerator * (denominator // value.denominator) for value in values)
        require(any(integers), "zero quotient class escaped filter")
        integer_terms.append((integers, representatives[key]))
    return {
        "integer_terms": integer_terms,
        "denominator": denominator,
        "raw_counts": raw_counts,
        "frozen_matched_raw": frozen_matched_raw,
        "nonzero_full_atom_classes": len(integer_terms),
        "class_coefficient_matrix_sha256": hashlib.sha256(canonical([
            [hashlib.sha256(bytes.fromhex(key)).hexdigest(), [str(value) for value in class_coefficients[key]]]
            for key in sorted(class_coefficients)
        ])).hexdigest(),
    }


def to_sparse(
    linear: Sequence[int], hinges: dict[normal.Direction, int], denominator: int
) -> identity.SparseVector:
    output: identity.SparseVector = {}
    for index, value in enumerate(linear):
        if value:
            output[("n9", "linear", index)] = Fraction(value, denominator)
    for direction, value in hinges.items():
        if value:
            output[("n9", "hinge", direction)] = Fraction(value, denominator)
    return output


def freeze_dual_replay(
    decision: dict[str, object],
    named_columns: dict[str, identity.SparseVector],
    target: identity.SparseVector,
) -> dict[str, object]:
    require(decision["result"] == "EXACT_Q_NONMEMBERSHIP", "dual replay requires nonmembership")
    rows = []
    weights = []
    for item in decision["dual_support"]:
        raw = item["row"]
        row = (raw[0], raw[1], tuple(raw[2]) if isinstance(raw[2], list) else raw[2])
        rows.append(row)
        weights.append(int(item["integer_weight"]))
    matrix = [
        {
            "row": identity.row_to_json(row),
            "integer_weight": str(weights[index]),
            "column_values": {
                name: str(named_columns[name].get(row, Fraction())) for name in COLUMNS
            },
            "target_value": str(target.get(row, Fraction())),
        }
        for index, row in enumerate(rows)
    ]
    column_pairings = {
        name: sum(
            weights[index] * named_columns[name].get(row, Fraction())
            for index, row in enumerate(rows)
        )
        for name in COLUMNS
    }
    target_pairing = sum(
        weights[index] * target.get(row, Fraction())
        for index, row in enumerate(rows)
    )
    require(all(value == 0 for value in column_pairings.values()), "frozen dual missed a column")
    require(target_pairing != 0, "frozen dual missed target")
    require(str(target_pairing) == decision["integer_target_pairing"], "dual target pairing drift")
    return {
        "rows": matrix,
        "column_pairings": {name: str(value) for name, value in column_pairings.items()},
        "target_pairing": str(target_pairing),
        "all_five_columns_annihilated": True,
        "target_not_annihilated": True,
        "matrix_sha256": hashlib.sha256(canonical(matrix)).hexdigest(),
    }


def run(output: Path, workers: int) -> None:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {
        "frozen_report": sha256(FROZEN_REPORT),
        "certificate_8_3": sha256(CERT8),
        "evaluator": sha256(G0090 / "known_certificate_normal_form.py"),
    }
    require(bindings == EXPECTED, "bound input drift")
    law, law_support_sha256 = frozen.load_law()
    fibers = build_class_coefficients(law)
    integer_terms = fibers.pop("integer_terms")
    worker_count = min(workers, len(integer_terms))
    shards: list[list[tuple[tuple[int, ...], normal.Pair]]] = [[] for _ in range(worker_count)]
    for index, term in enumerate(integer_terms):
        shards[index % worker_count].append(term)
    linears = [[0] * 9 for _ in COLUMNS]
    hinges: list[dict[normal.Direction, int]] = [{} for _ in COLUMNS]
    processed = 0
    raw_word_min: int | None = None
    raw_word_max = 0
    with ProcessPoolExecutor(max_workers=worker_count) as pool:
        futures = [pool.submit(aggregate_shard, (9, shard)) for shard in shards]
        for future in as_completed(futures):
            result = future.result()
            processed += int(result["classes"])
            for column_index in range(len(COLUMNS)):
                for coordinate, value in enumerate(result["linears"][column_index]):
                    linears[column_index][coordinate] += int(value)
                add_hinges(hinges[column_index], result["hinges"][column_index])
            shard_min = result["raw_word_min"]
            if shard_min is not None:
                raw_word_min = int(shard_min) if raw_word_min is None else min(raw_word_min, int(shard_min))
            raw_word_max = max(raw_word_max, int(result["raw_word_max"]))
    require(processed == len(integer_terms), "semantic class census drift")
    denominator = int(fibers["denominator"])
    named_columns = {
        name: to_sparse(linears[index], hinges[index], denominator)
        for index, name in enumerate(COLUMNS)
    }
    target = identity.target_vector(9, "n9")
    decision = identity.exact_decide(named_columns, target, "frozen-law-plus-uniform-relations-MAX9")
    primitive_dual_replay = freeze_dual_replay(decision, named_columns, target)
    frozen_residual_linear = list(linears[0])
    frozen_residual_linear[8] -= denominator
    frozen_residual_sha256 = frozen.residual_digest(
        frozen_residual_linear, hinges[0], denominator
    )
    previous = json.loads(FROZEN_REPORT.read_text(encoding="utf-8"))
    require(
        frozen_residual_sha256 == previous["complete_normal_form"]["residual_sha256"],
        "recomputed frozen-law residual disagrees with bound prior run",
    )
    report = {
        "schema": "max11-g0114-small-correction-span-v1",
        "bindings": {**bindings, "script_sha256_at_start": script_hash,
                     "law_support_sha256": law_support_sha256},
        "claim_boundary": (
            "Exact MAX9 decision for the frozen 148-weight output plus the four tied "
            "uniform relation aggregates. Nonmembership rejects this small repair space, "
            "not refitted incidence families, the complete degree-five dictionary, or MAX11."
        ),
        "columns": list(COLUMNS),
        "fiber_census": fibers,
        "complete_normal_form": {
            "classes_processed": processed,
            "workers": worker_count,
            "raw_direction_word_count_min": raw_word_min,
            "raw_direction_word_count_max": raw_word_max,
            "linear_support_sizes": {
                COLUMNS[index]: sum(value != 0 for value in linears[index])
                for index in range(len(COLUMNS))
            },
            "hinge_support_sizes": {
                COLUMNS[index]: len(hinges[index]) for index in range(len(COLUMNS))
            },
            "column_sha256": {
                name: identity.vector_digest(named_columns[name]) for name in COLUMNS
            },
            "frozen_residual_sha256_matches_prior": True,
        },
        "decision": decision,
        "primitive_dual_replay": primitive_dual_replay,
        "controls": {
            "public_MAX8_certificate_replayed": identity.core.one_star.replay_certificate(
                identity.core.one_star.load_certificate(CERT8, 8, 3)
            ),
            "exact_coefficient_mutation_rejected": (
                decision.get("one_unit_weight_mutation_rejected_at") is not None
                if decision["result"] == "EXACT_Q_MEMBERSHIP"
                else True
            ),
            "quotient_invariance": graph.invariant_controls(),
            "class_and_raw_censuses_reconciled": True,
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
        "decision": decision["result"],
        "rank": decision["rank_over_Q"],
        "augmented_rank": decision["augmented_rank_over_Q"],
        "classes": processed,
        "wall_seconds": report["wall_seconds"],
    }, sort_keys=True))


def self_test() -> dict[str, object]:
    require(identity.edge_relation((0, 0), (1, 2)) == "has_loop", "loop relation")
    require(identity.edge_relation((0, 1), (0, 1)) == "common_nonloop", "common relation")
    require(identity.edge_relation((0, 1), (1, 2)) == "share_one_nonloop", "share relation")
    require(identity.edge_relation((0, 1), (2, 3)) == "disjoint_nonloop", "disjoint relation")
    return {"four_relation_partition": True}


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
