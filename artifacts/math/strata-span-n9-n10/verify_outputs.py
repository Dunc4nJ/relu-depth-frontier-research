#!/usr/bin/env python3
"""Fail-closed audit of the gmp.7 stratum tables.

This verifier independently reloads the two saved systems and the G-0027
census through the producer's exact classifiers.  It repeats W-collapse column
equality and partition/mutation controls, then checks all table arithmetic and
cross-prime agreement.  It does not replay the expensive modular eliminations;
rerun ``strata_span.py`` for that.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import tempfile
from pathlib import Path


HERE = Path(__file__).resolve().parent
DEFAULT_INPUT = HERE / "strata_span_results.json"
DEFAULT_OUTPUT = HERE / "verification.json"


def load_producer():
    path = HERE / "strata_span.py"
    specification = importlib.util.spec_from_file_location("gmp7_strata_span", path)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load strata_span.py")
    module = importlib.util.module_from_spec(specification)
    sys.modules[specification.name] = module
    specification.loader.exec_module(module)
    return module


def normalized_counts(value: dict[str, dict[object, int]]) -> dict[str, dict[str, int]]:
    return {
        feature: {str(key): int(count) for key, count in counts.items()}
        for feature, counts in value.items()
    }


def candidate_map(prime_result: dict[str, object]) -> dict[tuple[str, tuple[int, ...]], tuple[int, int, bool, bool]]:
    return {
        (item["feature"], tuple(item["allowed_values"])): (
            int(item["rank"]),
            int(item["augmented_rank"]),
            bool(item["max_member"]),
            bool(item["full_span"]),
        )
        for item in prime_result["candidates"]
    }


def relative_candidate_map(prime_result: dict[str, object]) -> dict[str, tuple[int, int, bool, bool]]:
    return {
        item["rule_id"]: (
            int(item["rank"]),
            int(item["augmented_rank"]),
            bool(item["max_member"]),
            bool(item["full_span"]),
        )
        for item in prime_result["relative_candidates"]
    }


def verify_tables(data: dict[str, object], producer) -> dict[str, object]:
    if data["schema"] != "max11-gmp7-natural-w-strata-span-v1":
        raise AssertionError("unexpected result schema")
    if data["primes"] != [1_000_003, 1_000_033]:
        raise AssertionError("prime list changed")

    input_checks: dict[str, str] = {}
    for relative, receipt in data["inputs"].items():
        path = producer.ROOT / relative
        if path.stat().st_size != receipt["bytes"]:
            raise AssertionError(f"input byte count changed: {relative}")
        digest = producer.sha256_path(path)
        if digest != receipt["sha256"]:
            raise AssertionError(f"input hash changed: {relative}")
        input_checks[relative] = digest

    rescans: dict[str, object] = {}
    with tempfile.TemporaryDirectory(prefix="gmp7-verify-") as temporary:
        scratch = Path(temporary)
        for n in (9, 10):
            system = producer.scan_saved_system(n, producer.SYSTEMS[n], scratch)
            stored = data["systems"][str(n)]
            if system.raw_template_count != stored["raw_template_count"]:
                raise AssertionError(f"n={n} raw template count mismatch")
            if len(system.records) != stored["w_orbit_count"]:
                raise AssertionError(f"n={n} W count mismatch")
            if system.duplicate_w_columns_compared != stored["collapsed_duplicate_count"]:
                raise AssertionError(f"n={n} collapse count mismatch")
            if normalized_counts(producer.feature_counts(system.records)) != stored["feature_counts"]:
                raise AssertionError(f"n={n} feature census mismatch")
            if len(system.row_keys) != stored["hinge_row_count"]:
                raise AssertionError(f"n={n} hinge-row count mismatch")
            controls = producer.partition_controls(system.records)
            if controls["positive_partition_audits_passed"] != list(producer.FEATURES):
                raise AssertionError("positive partition control did not cover every feature")
            if controls["planted_duplicate_mislabels_rejected"] != list(producer.FEATURES):
                raise AssertionError("planted partition mutant escaped")

            prime_results = stored["prime_results"]
            if [item["prime"] for item in prime_results] != [1_000_003, 1_000_033]:
                raise AssertionError(f"n={n} prime result list changed")
            if candidate_map(prime_results[0]) != candidate_map(prime_results[1]):
                raise AssertionError(f"n={n} candidate ranks disagree across primes")
            if relative_candidate_map(prime_results[0]) != relative_candidate_map(prime_results[1]):
                raise AssertionError(f"n={n} relative candidate ranks disagree across primes")
            expected_rank = producer.EXPECTED_FULL_RANK[n]
            for prime_result in prime_results:
                full = prime_result["full"]
                if not (
                    full["rank"] == expected_rank
                    and full["augmented_rank"] == expected_rank
                    and full["max_member"] is True
                ):
                    raise AssertionError(f"n={n} full known-answer gate failed")
                for candidate in prime_result["candidates"]:
                    if candidate["max_member"] != (
                        candidate["rank"] == candidate["augmented_rank"]
                    ):
                        raise AssertionError("candidate membership flag disagrees with augmented rank")
                    if candidate["full_span"] != (candidate["rank"] == expected_rank):
                        raise AssertionError("candidate full-span flag disagrees with rank")
                for candidate in prime_result["relative_candidates"]:
                    if candidate["max_member"] != (
                        candidate["rank"] == candidate["augmented_rank"]
                    ):
                        raise AssertionError("relative membership flag disagrees with augmented rank")
                    if candidate["full_span"] != (candidate["rank"] == expected_rank):
                        raise AssertionError("relative full-span flag disagrees with rank")
                for table in prime_result["cumulative_tables"]:
                    prior_rank = 0
                    prior_count = 0
                    for step in table["steps"]:
                        if step["rank_growth"] != step["rank"] - prior_rank:
                            raise AssertionError("cumulative rank growth does not telescope")
                        if step["cumulative_column_count"] != prior_count + step["added_stratum_count"]:
                            raise AssertionError("cumulative stratum sizes do not telescope")
                        prior_rank = step["rank"]
                        prior_count = step["cumulative_column_count"]
                    if prior_count != len(system.records) or prior_rank != expected_rank:
                        raise AssertionError("cumulative table does not end at full family")

            tree = prime_results[0]["n9_tree_negative_control"]
            if n == 9 and not (
                tree["column_count"] == 739
                and tree["rank"] == 360
                and tree["augmented_rank"] == 361
                and tree["max_member"] is False
            ):
                raise AssertionError("n=9 tree NON-MEMBER known-answer gate failed")
            rescans[str(n)] = {
                "raw_template_count": system.raw_template_count,
                "w_orbit_count": len(system.records),
                "collapsed_duplicate_columns_rechecked": system.duplicate_w_columns_compared,
                "candidate_rank_cross_prime_agreement": True,
                "relative_candidate_rank_cross_prime_agreement": True,
                "partition_mutants_rejected": list(producer.FEATURES),
            }

        _payload, n11_records = producer.load_g0027_records(producer.G0027)
        if normalized_counts(producer.feature_counts(n11_records)) != data["g0027"]["feature_counts"]:
            raise AssertionError("G-0027 independent feature recount mismatch")
        if len(n11_records) != 754_017:
            raise AssertionError("G-0027 denominator changed")
        for item in data["n11_relative_rule_counts"]:
            recomputed = sum(
                producer.matches_relative_rule(record, 5, item["constraints"])
                for record in n11_records
            )
            if recomputed != item["column_count"]:
                raise AssertionError(f"n=11 relative count mismatch for {item['rule_id']}")

    first = data["common_full_span_rules"][0]
    if not (
        first["feature"] == "s"
        and first["allowed_values"] == [3, 4]
        and first["n9"]["column_count"] == 6_175
        and first["n10"]["column_count"] == 7_181
        and first["n11_column_count"] == 18_254
        and first["n11_universe_denominator"] == 754_017
    ):
        raise AssertionError("smallest common full-rank rule changed")

    relative_first = data["smallest_common_relative_full_span_rules"][0]
    if not (
        relative_first["constraints"]
        == {"mass_deficit_leq": 1, "max_multiplicity_leq": 1}
        and relative_first["n9"]["column_count"] == 6_175
        and relative_first["n10"]["column_count"] == 7_181
        and relative_first["n11_column_count"] == 243_155
        and relative_first["n11_universe_denominator"] == 754_017
    ):
        raise AssertionError("smallest degree-relative common full-rank rule changed")

    requested = {
        9: {
            "mass_deficit_leq=0": (1_505, 1_505, True),
            "beta_leq=1;mass_deficit_leq=0": (1_152, 1_152, True),
            "beta_leq=2;mass_deficit_leq=0": (1_446, 1_446, True),
            "components_eq=1": (978, 978, True),
            "max_multiplicity_eq=1": (1_506, 1_506, True),
        },
        10: {
            "mass_deficit_leq=0": (2_165, 2_165, True),
            "beta_leq=1;mass_deficit_leq=0": (1_807, 1_807, True),
            "beta_leq=2;mass_deficit_leq=0": (2_106, 2_106, True),
            "components_eq=1": (978, 979, False),
            "max_multiplicity_eq=1": (2_166, 2_166, True),
        },
    }
    for n, gates in requested.items():
        observed = relative_candidate_map(data["systems"][str(n)]["prime_results"][0])
        for rule_id, expected in gates.items():
            if observed[rule_id][:3] != expected:
                raise AssertionError(f"requested relative gate changed: n={n}, {rule_id}")

    growth = data["full_mass_beta_growth_extrapolation"]
    if sum(item["n11_full_mass_stratum_count"] for item in growth) != 735_732:
        raise AssertionError("full-mass beta growth table has wrong n=11 denominator")
    if sum(item["n9_rank_growth"] or 0 for item in growth) != 1_505:
        raise AssertionError("n=9 full-mass beta growth does not telescope")
    if sum(item["n10_rank_growth"] or 0 for item in growth) != 2_165:
        raise AssertionError("n=10 full-mass beta growth does not telescope")

    return {
        "schema": "max11-gmp7-strata-output-verification-v1",
        "result": "PASS",
        "modular_rank_replay": False,
        "modular_rank_replay_command": (
            "source .venv/bin/activate && OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 "
            "OMP_NUM_THREADS=6 python artifacts/math/strata-span-n9-n10/strata_span.py --threads 6"
        ),
        "input_sha256": input_checks,
        "rescans": rescans,
        "g0027_records_rechecked": 754_017,
        "n11_relative_rules_recounted": len(data["n11_relative_rule_counts"]),
        "known_answer_gates": {
            "n9_full_rank_both_primes": 1_506,
            "n10_full_rank_both_primes": 2_166,
            "n9_tree_rank_both_primes": 360,
            "n9_tree_augmented_rank_both_primes": 361,
        },
        "no_claim": (
            "This audit checks inputs, exact W collapse, censuses, controls, table arithmetic, "
            "and cross-prime agreement. It does not independently replay modular elimination "
            "and makes no MAX11 or rational-identity claim."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    producer = load_producer()
    data = json.loads(args.input.read_text())
    report = verify_tables(data, producer)
    report["result_json_sha256"] = producer.sha256_path(args.input)
    report["producer_sha256"] = producer.sha256_path(HERE / "strata_span.py")
    producer.atomic_write_json(args.output, report)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
