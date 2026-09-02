#!/usr/bin/env python3
"""Structural and replay verifier for the gmp.9 finite-universe outputs."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import gzip
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rank_multiedge as common  # noqa: E402


EXPECTED = {
    7: {"columns": 8_282, "multiplicity": {0: 1, 1: 2_033, 2: 5_118, 3: 1_014, 4: 116}, "ranks": [296, 512, 553, 553]},
    8: {"columns": 13_146, "multiplicity": {0: 1, 1: 4_314, 2: 7_506, 3: 1_201, 4: 124}, "ranks": [776, 1_196, 1_262, 1_262]},
    9: {"columns": 16_311, "multiplicity": {0: 1, 1: 6_196, 2: 8_723, 3: 1_265, 4: 126}, "ranks": [1_506, 2_148, 2_232, 2_232]},
    10: {"columns": 17_775, "multiplicity": {0: 1, 1: 7_202, 2: 9_162, 3: 1_283, 4: 127}, "ranks": [2_166, 3_013, 3_108, 3_108]},
}
EXPECTED_ROWS = {7: 931, 8: 2_983, 9: 8_304, 10: 20_695}
EXPECTED_PRIMES = (1_000_003, 1_000_033)


def load_json(path: Path) -> dict[str, object]:
    with path.open() as handle:
        return json.load(handle)


def load_universe(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt") as handle:
        return json.load(handle)


def load_strata_key_module():
    path = ROOT / "artifacts/math/strata-span-n9-n10/strata_span.py"
    spec = importlib.util.spec_from_file_location("gmp7_verify_key", path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def components(edges: list[tuple[int, int]], active_vertices: int) -> int:
    parent = list(range(active_vertices))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for left, right in edges:
        a, b = find(left), find(right)
        if a != b:
            parent[b] = a
    return len({find(vertex) for vertex in range(active_vertices)})


def validate_universe(n: int, universe: dict[str, object], key_module) -> dict[str, object]:
    expected = EXPECTED[n]
    records = universe["records"]
    if universe.get("result") != "PASS" or int(universe["n"]) != n:
        raise AssertionError(f"n={n} universe header failed")
    if len(records) != expected["columns"]:
        raise AssertionError(f"n={n} universe denominator failed")
    keys = set()
    maxima = Counter()
    for index, record in enumerate(records):
        active = int(record["active_vertices"])
        mass = int(record["signed_mass"])
        negative = [tuple(map(int, edge)) for edge in record["negative_edges"]]
        positive = [tuple(map(int, edge)) for edge in record["positive_edges"]]
        if len(negative) != mass or len(positive) != mass:
            raise AssertionError(f"n={n} record {index}: signed mass mismatch")
        all_edges = negative + positive
        if any(not (0 <= edge[0] < edge[1] < active) for edge in all_edges):
            raise AssertionError(f"n={n} record {index}: noncanonical edge")
        if set(negative) & set(positive):
            raise AssertionError(f"n={n} record {index}: uncancelled opposite edge")
        used = {vertex for edge in all_edges for vertex in edge}
        if mass == 0:
            if active != 0 or all_edges:
                raise AssertionError("zero record malformed")
            recomputed_components = 0
        else:
            if used != set(range(active)):
                raise AssertionError(f"n={n} record {index}: inactive vertex in support")
            recomputed_components = components(all_edges, active)
        recomputed_beta = 2 * mass - active + recomputed_components
        maximum = common.recompute_max_multiplicity(record)
        if int(record["abs_components"]) != recomputed_components:
            raise AssertionError(f"n={n} record {index}: component mismatch")
        if int(record["abs_beta"]) != recomputed_beta:
            raise AssertionError(f"n={n} record {index}: beta mismatch")
        if int(record["max_multiplicity"]) != maximum:
            raise AssertionError(f"n={n} record {index}: multiplicity mismatch")
        maxima[maximum] += 1
        key = key_module.signed_w_key(tuple(negative), tuple(positive), n)
        if key in keys:
            raise AssertionError(f"n={n} record {index}: duplicate signed-W orbit")
        keys.add(key)
    if dict(sorted(maxima.items())) != expected["multiplicity"]:
        raise AssertionError(f"n={n} multiplicity census failed")
    census = universe["census"]
    if int(census["signed_graph_orbits"]) != len(records):
        raise AssertionError(f"n={n} census total failed")
    if not universe["controls"].get("orbit_traversal_equals_burnside_for_every_absolute_graph"):
        raise AssertionError(f"n={n} Burnside gate absent")
    return {"records": len(records), "canonical_keys": len(keys), "multiplicity": dict(maxima)}


def validate_rank_report(n: int, report: dict[str, object], field: str) -> None:
    expected = EXPECTED[n]
    if report.get("result") != "PASS" or int(report["n"]) != n:
        raise AssertionError(f"n={n} {field} rank report header failed")
    if int(report["universe_column_denominator"]) != expected["columns"]:
        raise AssertionError(f"n={n} {field} column denominator failed")
    if int(report["normal_form_row_denominator"]) != EXPECTED_ROWS[n]:
        raise AssertionError(f"n={n} {field} row denominator failed")
    table = report["rank_table"]
    ranks = [int(step["rank"]) for step in table]
    augmented = [int(step["augmented_rank"]) for step in table]
    if ranks != expected["ranks"] or augmented != ranks:
        raise AssertionError(f"n={n} {field} rank table failed")
    if [int(step["maximum_multiplicity_leq"]) for step in table] != [1, 2, 3, 4]:
        raise AssertionError(f"n={n} {field} threshold order failed")
    if not all(step["max_member"] for step in table):
        raise AssertionError(f"n={n} {field} MAX membership failed")
    controls = report["controls"]
    if int(controls["duplicate_rank_growth"]) != 0 or not controls["duplicate_pivot_rejected"]:
        raise AssertionError(f"n={n} {field} planted duplicate was accepted")
    if not controls["target_pivot_rejected"]:
        raise AssertionError(f"n={n} {field} target pivot gate failed")


def validate_bundle(require_columns: bool, replay_enumeration: bool) -> dict[str, object]:
    key_module = load_strata_key_module()
    universe_checks = {}
    universes = {}
    for n in (7, 8, 9, 10):
        path = HERE / f"universe_n{n}_k4.json.gz"
        universe = load_universe(path)
        universes[n] = universe
        universe_checks[n] = validate_universe(n, universe, key_module)

    if replay_enumeration:
        with tempfile.TemporaryDirectory(prefix="gmp9-enumeration-replay-") as temporary:
            for n in (7, 8, 9, 10):
                replay_path = Path(temporary) / f"universe_n{n}.json.gz"
                subprocess.run(
                    [
                        sys.executable,
                        str(HERE / "enumerate_degree4.py"),
                        "--n",
                        str(n),
                        "--branch-edges",
                        "4",
                        "--output",
                        str(replay_path),
                    ],
                    cwd=ROOT,
                    check=True,
                    stdout=subprocess.DEVNULL,
                )
                replay = load_universe(replay_path)
                if replay["records_sha256"] != universes[n]["records_sha256"]:
                    raise AssertionError(f"n={n} enumeration record replay mismatch")
                if replay["census"] != universes[n]["census"]:
                    raise AssertionError(f"n={n} enumeration census replay mismatch")

    modular_reports = {}
    for n in (9, 10):
        reports = []
        for prime in EXPECTED_PRIMES:
            report = load_json(HERE / f"rank_n{n}_p{prime}.json")
            if int(report["prime"]) != prime:
                raise AssertionError(f"n={n} prime label failed")
            validate_rank_report(n, report, f"F_{prime}")
            reports.append(report)
        if reports[0]["rank_table"] != reports[1]["rank_table"]:
            raise AssertionError(f"n={n} cross-prime tables disagree")
        modular_reports[n] = reports

        bridge = load_json(HERE / f"simple_bridge_n{n}.json")
        controls = bridge["controls"]
        expected_simple = EXPECTED[n]["multiplicity"][0] + EXPECTED[n]["multiplicity"][1]
        if int(controls["exact_simple_w_columns_equal"]) != expected_simple:
            raise AssertionError(f"n={n} exact bridge denominator failed")
        if int(controls["one_unit_coefficient_mutations_rejected"]) != expected_simple:
            raise AssertionError(f"n={n} bridge mutation gate failed")
        for report in reports:
            if bridge["universe_sha256"] != report["universe_sha256"]:
                raise AssertionError(f"n={n} bridge/rank universe hash mismatch")
            if bridge["exact_columns_sha256"] != report["exact_columns_sha256"]:
                raise AssertionError(f"n={n} bridge/rank column hash mismatch")

    exact_q_reports = {}
    for n in (7, 8):
        report = load_json(HERE / f"rank_n{n}_Q.json")
        validate_rank_report(n, report, "Q")
        exact_q_reports[n] = report

    if require_columns:
        for n in (7, 8, 9, 10):
            path = HERE / f"columns_n{n}_k4_exact.bin"
            if not path.exists():
                raise AssertionError(f"required transient column stream missing: {path}")
            expected_hash = (
                exact_q_reports[n]["exact_columns_sha256"]
                if n in exact_q_reports
                else modular_reports[n][0]["exact_columns_sha256"]
            )
            if common.sha256_path(path) != expected_hash:
                raise AssertionError(f"n={n} exact column stream hash mismatch")

    # Both-direction verifier controls: corruptions must fail closed.
    mutant = copy.deepcopy(modular_reports[9][0])
    mutant["rank_table"][1]["rank"] += 1
    try:
        validate_rank_report(9, mutant, "planted-rank-mutant")
    except AssertionError:
        rank_mutant_rejected = True
    else:
        raise AssertionError("planted rank-table mutation was accepted")

    mutant_universe = copy.deepcopy(universes[9])
    mutant_universe["records"][1]["max_multiplicity"] += 1
    try:
        validate_universe(9, mutant_universe, key_module)
    except AssertionError:
        universe_mutant_rejected = True
    else:
        raise AssertionError("planted universe mutation was accepted")

    return {
        "schema": "max11-gmp9-output-verification-v1",
        "result": "PASS",
        "universe_checks": universe_checks,
        "modular_primes": list(EXPECTED_PRIMES),
        "cross_prime_rank_tables_equal": True,
        "exact_q_arities": [7, 8],
        "require_transient_columns": require_columns,
        "enumeration_replayed": replay_enumeration,
        "controls": {
            "positive_bundle_accepted": True,
            "planted_rank_table_mutation_rejected": rank_mutant_rejected,
            "planted_universe_mutation_rejected": universe_mutant_rejected,
        },
        "no_claim": (
            "This verifier checks the finite n=7..10 outputs only. It does not rerun "
            "dense ranks, prove an exact-Q identity at n=9 or n=10, or decide n=11."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--require-columns", action="store_true")
    parser.add_argument("--replay-enumeration", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    started = time.monotonic()
    result = validate_bundle(args.require_columns, args.replay_enumeration)
    result["wall_seconds"] = time.monotonic() - started
    common.atomic_write_json(args.output, result)
    print(
        f"GMP9_VERIFY_PASS replay_enumeration={args.replay_enumeration} "
        f"require_columns={args.require_columns}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
