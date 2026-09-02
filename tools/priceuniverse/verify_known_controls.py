#!/usr/bin/env python3
"""Independently reconcile the n=9 and n=10 exact-pricing controls."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import flint


EXACTLIFT = Path(__file__).resolve().parents[1] / "exactlift"
sys.path.insert(0, str(EXACTLIFT))
import exactlift  # noqa: E402


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def load_violators(path: Path) -> dict[int, int]:
    result: dict[int, int] = {}
    with path.open(encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            row = json.loads(line)
            index = int(row["source_index"])
            if index in result:
                raise ValueError(f"duplicate violator {index} at {path}:{line_number}")
            result[index] = int(row["scaled_price"])
    return result


def modular_report_is_complete(report: dict) -> bool:
    denominator = int(report["columns_evaluated_denominator"])
    checks = report["modular_cross_checks"]
    return [int(item["prime"]) for item in checks] == [1_000_003, 1_000_033] and all(
        int(item["agreement_numerator"]) == denominator
        and int(item["agreement_denominator"]) == denominator
        for item in checks
    )


def n9_span_check(system: Path, trees: list[int], extra: list[int]) -> list[dict]:
    n, source_count, row_index = exactlift.scan_system(system)
    if (n, source_count, len(extra)) != (9, 10_976, 1):
        raise RuntimeError("n=9 control denominator mismatch")
    selected = trees + extra
    positions = {source_index: column for column, source_index in enumerate(selected)}
    rows = len(row_index) + n
    by_source = {
        index: column
        for index, column in enumerate(exactlift.iter_columns(system))
        if index in positions
    }
    # Retrieve by source key so enumeration order cannot silently change the matrix.
    checks = []
    for prime in (1_000_003, 1_000_033):
        tree_matrix = flint.nmod_mat(rows, len(trees), prime)
        augmented = flint.nmod_mat(rows, len(selected), prime)
        for column_position, source_index in enumerate(selected):
            column = by_source[source_index]
            for row, value in exactlift.column_entries(column, row_index):
                augmented[row, column_position] = value % prime
                if column_position < len(trees):
                    tree_matrix[row, column_position] = value % prime
        tree_rank = int(tree_matrix.rank())
        augmented_rank = int(augmented.rank())
        checks.append(
            {
                "prime": prime,
                "tree_rank_numerator": tree_rank,
                "tree_columns_denominator": len(trees),
                "tree_plus_extra_rank_numerator": augmented_rank,
                "tree_plus_extra_columns_denominator": len(selected),
            }
        )
        if (tree_rank, augmented_rank) != (360, 360):
            raise RuntimeError(f"extra zero column is not in tree span at prime {prime}")
    return checks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n9-system", type=Path, required=True)
    parser.add_argument("--n9-all-report", type=Path, required=True)
    parser.add_argument("--n9-all-violators", type=Path, required=True)
    parser.add_argument("--n9-tree-report", type=Path, required=True)
    parser.add_argument("--n9-mutant-report", type=Path, required=True)
    parser.add_argument("--n10-build-report", type=Path, required=True)
    parser.add_argument("--n10-separator", type=Path, required=True)
    parser.add_argument("--n10-price-report", type=Path, required=True)
    parser.add_argument("--n10-violators", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    n9_all = load_json(args.n9_all_report)
    n9_tree = load_json(args.n9_tree_report)
    n9_mutant = load_json(args.n9_mutant_report)
    n9_violators = load_violators(args.n9_all_violators)
    trees = []
    for source_index, column in enumerate(exactlift.iter_columns(args.n9_system)):
        if exactlift.is_union_spanning_tree(column, 9):
            trees.append(source_index)
    zeros = sorted(set(range(10_976)) - set(n9_violators))
    extra_zeros = sorted(set(zeros) - set(trees))
    if not (
        n9_all["verdict"] == n9_tree["verdict"] == n9_mutant["verdict"] == "PASS"
        and len(trees) == 739
        and int(n9_tree["annihilated_columns_numerator"]) == 739
        and int(n9_tree["violating_columns_numerator"]) == 0
        and int(n9_mutant["annihilated_columns_numerator"]) == 0
        and int(n9_mutant["violating_columns_numerator"]) == 739
        and int(n9_all["annihilated_columns_numerator"]) == 740
        and int(n9_all["violating_columns_numerator"]) == 10_236
        and not (set(trees) & set(n9_violators))
        and modular_report_is_complete(n9_all)
        and modular_report_is_complete(n9_tree)
        and modular_report_is_complete(n9_mutant)
    ):
        raise RuntimeError("n=9 price controls do not match their denominators")
    n9_rank_checks = n9_span_check(args.n9_system, trees, extra_zeros)

    n10_build = load_json(args.n10_build_report)
    n10_separator = load_json(args.n10_separator)
    n10_price = load_json(args.n10_price_report)
    n10_violators = load_violators(args.n10_violators)
    subfamily = set(map(int, n10_separator["proper_subfamily_pivot_columns"]))
    dropped = int(n10_separator["dropped_pivot_source_index"])
    denominator = int(n10_price["integer_scaled_common_denominator"])
    if not (
        n10_build["verdict"] == n10_price["verdict"] == "PASS"
        and all(
            (int(item["full_rank_numerator"]), int(item["proper_subfamily_rank_numerator"]))
            == (2_166, 2_165)
            for item in n10_build["rank_checks"]
        )
        and len(subfamily) == 2_165
        and not (subfamily & set(n10_violators))
        and n10_violators == {dropped: denominator}
        and int(n10_price["annihilated_columns_numerator"]) == 12_247
        and int(n10_price["violating_columns_numerator"]) == 1
        and modular_report_is_complete(n10_price)
    ):
        raise RuntimeError("n=10 codimension-one price control failed")

    payload = {
        "schema": "max11-price-universe-known-controls-v1",
        "verdict": "PASS",
        "n9": {
            "system": str(args.n9_system),
            "system_sha256": sha256_file(args.n9_system),
            "tree_columns_annihilated_numerator": 739,
            "tree_columns_denominator": 739,
            "mutated_tree_columns_nonzero_numerator": 739,
            "mutated_tree_columns_denominator": 739,
            "all_saved_columns_denominator": 10_976,
            "all_saved_nonzero_prices_numerator": 10_236,
            "all_saved_zero_prices_numerator": 740,
            "extra_zero_source_indices": extra_zeros,
            "extra_zero_in_tree_span_rank_checks": n9_rank_checks,
            "price_report_sha256": sha256_file(args.n9_all_report),
            "price_vector_sha256": n9_all["exact_price_vector_sha256"],
        },
        "n10": {
            "all_saved_columns_denominator": 12_248,
            "proper_subfamily_columns_denominator": 2_165,
            "proper_subfamily_rank_numerator": 2_165,
            "full_span_rank_numerator": 2_166,
            "full_span_rank_denominator": 2_166,
            "zero_price_columns_numerator": 12_247,
            "nonzero_price_columns_numerator": 1,
            "dropped_pivot_source_index": dropped,
            "dropped_scaled_price_numerator": denominator,
            "common_denominator": denominator,
            "rank_checks": n10_build["rank_checks"],
            "price_report_sha256": sha256_file(args.n10_price_report),
            "price_vector_sha256": n10_price["exact_price_vector_sha256"],
        },
        "modular_primes": [1_000_003, 1_000_033],
        "no_claim": "These are exact known-answer controls over the finite n=9 and n=10 saved systems; they say nothing about n=11 membership.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
