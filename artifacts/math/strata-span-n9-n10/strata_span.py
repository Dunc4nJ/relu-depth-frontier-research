#!/usr/bin/env python3
"""Exact modular span scan for natural strata of the saved n=9/n=10 systems.

The saved systems are indexed by simple branch pairs (A,B).  This script first
cancels common edges and quotients the resulting signed graph W=B-A by vertex
relabeling and global sign reversal.  Whenever several saved templates collapse
to the same W, their complete sparse integer columns are compared byte-for-byte
after canonical JSON serialization before one representative is retained.

Ranks are computed over both registered primes with python-flint.  A single RREF
of the full augmented system supplies an invertible row transformation; candidate
submatrices are then ranked in its nonzero row block.  This changes neither rank
nor target membership and makes the stratum scan substantially cheaper.
"""

from __future__ import annotations

import argparse
import gc
import gzip
import hashlib
import json
import os
import sqlite3
import tempfile
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence

import flint
from pynauty import Graph, certificate


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SYSTEMS = {
    9: ROOT / "handoff/2026-09-02-amberbluff/systems/loopless_system_n9.jsonl.gz",
    10: ROOT / "handoff/2026-09-02-amberbluff/systems/loopless_system_n10.jsonl.gz",
}
G0027 = ROOT / "artifacts/math/G-0027/loopless_signed_degree5_universe_v1.json.gz"
DEFAULT_OUTPUT = HERE / "strata_span_results.json"
PRIMES = (1_000_003, 1_000_033)
EXPECTED_FULL_RANK = {9: 1_506, 10: 2_166}
FEATURES = ("s", "beta", "components", "max_multiplicity")

Edge = tuple[int, int]


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def atomic_write_json(path: Path, value: object) -> None:
    payload = json.dumps(value, indent=2, sort_keys=True) + "\n"
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(payload)
    temporary.replace(path)


def normalize_edge(raw: Sequence[int]) -> Edge:
    if len(raw) != 2:
        raise ValueError(f"not an edge: {raw!r}")
    a, b = map(int, raw)
    if a == b:
        raise ValueError(f"saved loopless system contains loop {(a, b)!r}")
    return (min(a, b), max(a, b))


def ordered_signed_certificate(
    negative: Sequence[Edge], positive: Sequence[Edge], n: int
) -> bytes:
    """Canonical incidence certificate with the two signs kept ordered."""

    negative = tuple(sorted(negative))
    positive = tuple(sorted(positive))
    total = n + len(negative) + len(positive)
    adjacency: dict[int, list[int]] = {vertex: [] for vertex in range(total)}
    cursor = n
    for a, b in negative:
        adjacency[cursor] = [a, b]
        cursor += 1
    for a, b in positive:
        adjacency[cursor] = [a, b]
        cursor += 1
    coloring = [set(range(n))]
    negative_nodes = set(range(n, n + len(negative)))
    positive_nodes = set(range(n + len(negative), total))
    if negative_nodes:
        coloring.append(negative_nodes)
    if positive_nodes:
        coloring.append(positive_nodes)
    return certificate(
        Graph(
            total,
            directed=False,
            adjacency_dict=adjacency,
            vertex_coloring=coloring,
        )
    )


def signed_w_key(negative: Sequence[Edge], positive: Sequence[Edge], n: int) -> bytes:
    """S_n x global-sign-reversal key for a cancelled signed multigraph."""

    return min(
        ordered_signed_certificate(negative, positive, n),
        ordered_signed_certificate(positive, negative, n),
    )


def cancelled_w(first: Sequence[Sequence[int]], second: Sequence[Sequence[int]]) -> tuple[tuple[Edge, ...], tuple[Edge, ...]]:
    first_edges = tuple(normalize_edge(edge) for edge in first)
    second_edges = tuple(normalize_edge(edge) for edge in second)
    if len(set(first_edges)) != len(first_edges) or len(set(second_edges)) != len(second_edges):
        raise ValueError("saved simple-pair system contains a repeated branch edge")
    first_set = set(first_edges)
    second_set = set(second_edges)
    return tuple(sorted(first_set - second_set)), tuple(sorted(second_set - first_set))


def signed_stats(negative: Sequence[Edge], positive: Sequence[Edge]) -> dict[str, int]:
    if len(negative) != len(positive):
        raise ValueError("unbalanced signed graph")
    multiplicities: Counter[Edge] = Counter(negative)
    multiplicities.update(positive)
    if set(negative) & set(positive):
        raise ValueError("signed graph was not cancelled")
    vertices = {vertex for edge in multiplicities for vertex in edge}
    parent = {vertex: vertex for vertex in vertices}

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for a, b in multiplicities:
        left, right = find(a), find(b)
        if left != right:
            parent[right] = left
    components = len({find(vertex) for vertex in vertices}) if vertices else 0
    mass = len(negative)
    return {
        "s": mass,
        "beta": 2 * mass - len(vertices) + components,
        "components": components,
        "max_multiplicity": max(multiplicities.values(), default=0),
        "active_vertices": len(vertices),
    }


def validate_partition(records: Sequence[dict[str, int]], feature: str, buckets: dict[int, list[int]]) -> None:
    flat = [index for indices in buckets.values() for index in indices]
    if len(flat) != len(records) or sorted(flat) != list(range(len(records))):
        raise AssertionError(f"{feature} buckets are not a disjoint exhaustive partition")
    for value, indices in buckets.items():
        if any(records[index][feature] != value for index in indices):
            raise AssertionError(f"{feature} bucket contains a mislabeled record")


def partition_controls(records: Sequence[dict[str, int]]) -> dict[str, object]:
    """Positive partition audit plus a planted duplicate/mislabel rejection."""

    passed: list[str] = []
    rejected: list[str] = []
    for feature in FEATURES:
        buckets: defaultdict[int, list[int]] = defaultdict(list)
        for index, record in enumerate(records):
            buckets[record[feature]].append(index)
        validate_partition(records, feature, dict(buckets))
        passed.append(feature)

        mutant = {value: list(indices) for value, indices in buckets.items()}
        source_value = records[0][feature]
        false_value = max(mutant) + 1
        if false_value == source_value:
            false_value += 1
        mutant.setdefault(false_value, []).append(0)
        try:
            validate_partition(records, feature, mutant)
        except AssertionError:
            rejected.append(feature)
        else:
            raise AssertionError(f"planted {feature} partition mutation was accepted")
    return {
        "positive_partition_audits_passed": passed,
        "planted_duplicate_mislabels_rejected": rejected,
    }


@dataclass
class SavedSystem:
    n: int
    path: Path
    raw_template_count: int
    records: list[dict[str, int]]
    representative_raw_indices: list[int]
    row_keys: list[str]
    duplicate_w_columns_compared: int
    controls: dict[str, object]


def scan_saved_system(n: int, path: Path, scratch: Path) -> SavedSystem:
    """Quotient by W and compare every collapsed duplicate column exactly."""

    database_path = scratch / f"n{n}-w-columns.sqlite"
    connection = sqlite3.connect(database_path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.execute(
        "CREATE TABLE columns (w_key BLOB PRIMARY KEY, payload BLOB NOT NULL) WITHOUT ROWID"
    )
    records: list[dict[str, int]] = []
    representatives: list[int] = []
    row_keys: set[str] = set()
    raw_count = 0
    duplicate_count = 0

    with gzip.open(path, "rt") as handle:
        for raw_index, line in enumerate(handle):
            item = json.loads(line)
            negative, positive = cancelled_w(item["A"], item["B"])
            if len(item["A"]) != (n - 1) // 2 or len(item["B"]) != (n - 1) // 2:
                raise AssertionError("saved branch degree disagrees with n")
            key = signed_w_key(negative, positive, n)
            payload = canonical_json_bytes({"h": item["h"], "lin": item["lin"]})
            prior = connection.execute(
                "SELECT payload FROM columns WHERE w_key = ?", (sqlite3.Binary(key),)
            ).fetchone()
            if prior is None:
                connection.execute(
                    "INSERT INTO columns(w_key,payload) VALUES (?,?)",
                    (sqlite3.Binary(key), sqlite3.Binary(payload)),
                )
                representatives.append(raw_index)
                records.append(signed_stats(negative, positive))
                row_keys.update(item["h"])
            else:
                # Equality of canonical sparse maps checks every stored integer row;
                # absent keys are zero on both sides.
                if bytes(prior[0]) != payload:
                    raise AssertionError(
                        f"templates with the same W have unequal exact columns at raw index {raw_index}"
                    )
                duplicate_count += 1
            raw_count += 1
    connection.commit()
    unique_count = connection.execute("SELECT COUNT(*) FROM columns").fetchone()[0]
    connection.close()
    if unique_count != len(records) or raw_count != unique_count + duplicate_count:
        raise AssertionError("W quotient accounting mismatch")

    controls = partition_controls(records)
    controls.update(
        {
            "all_collapsed_duplicate_columns_equal_as_sparse_integer_columns": True,
            "collapsed_duplicate_denominator": duplicate_count,
        }
    )
    return SavedSystem(
        n=n,
        path=path,
        raw_template_count=raw_count,
        records=records,
        representative_raw_indices=representatives,
        row_keys=sorted(row_keys),
        duplicate_w_columns_compared=duplicate_count,
        controls=controls,
    )


def feature_counts(records: Sequence[dict[str, int]]) -> dict[str, dict[int, int]]:
    return {
        feature: dict(sorted(Counter(record[feature] for record in records).items()))
        for feature in FEATURES
    }


def candidate_rules(records: Sequence[dict[str, int]]) -> list[dict[str, object]]:
    """Atomic strata and three natural cumulative orders, deduplicated by predicate."""

    counts = feature_counts(records)
    by_key: dict[tuple[str, tuple[int, ...]], dict[str, object]] = {}
    for feature in FEATURES:
        values = sorted(counts[feature])
        orders = {
            "low_to_high": values,
            "high_to_low": list(reversed(values)),
            "small_strata_first": sorted(values, key=lambda value: (counts[feature][value], value)),
        }
        for value in values:
            key = (feature, (value,))
            by_key[key] = {
                "feature": feature,
                "allowed_values": [value],
                "origins": ["atomic"],
            }
        for origin, order in orders.items():
            allowed: list[int] = []
            for value in order:
                allowed.append(value)
                key = (feature, tuple(sorted(allowed)))
                rule = by_key.setdefault(
                    key,
                    {
                        "feature": feature,
                        "allowed_values": list(key[1]),
                        "origins": [],
                    },
                )
                origins = rule["origins"]
                assert isinstance(origins, list)
                if origin not in origins:
                    origins.append(origin)

    result: list[dict[str, object]] = []
    for rule in by_key.values():
        feature = str(rule["feature"])
        allowed = set(map(int, rule["allowed_values"]))
        indices = [index for index, record in enumerate(records) if record[feature] in allowed]
        result.append({**rule, "column_indices": indices, "column_count": len(indices)})
    result.sort(
        key=lambda rule: (
            int(rule["column_count"]),
            str(rule["feature"]),
            tuple(rule["allowed_values"]),
        )
    )
    return result


def matches_relative_rule(record: dict[str, int], k: int, constraints: dict[str, int]) -> bool:
    if "mass_deficit_leq" in constraints and k - record["s"] > constraints["mass_deficit_leq"]:
        return False
    if "beta_leq" in constraints and record["beta"] > constraints["beta_leq"]:
        return False
    if "components_leq" in constraints and record["components"] > constraints["components_leq"]:
        return False
    if "components_eq" in constraints and record["components"] != constraints["components_eq"]:
        return False
    if "max_multiplicity_leq" in constraints and record["max_multiplicity"] > constraints["max_multiplicity_leq"]:
        return False
    if "max_multiplicity_eq" in constraints and record["max_multiplicity"] != constraints["max_multiplicity_eq"]:
        return False
    return True


def relative_candidate_rules(records: Sequence[dict[str, int]], k: int) -> list[dict[str, object]]:
    """Degree-relative mass rules and the requested natural threshold intersections.

    Intersections with topology/multiplicity are enumerated for the top-mass
    stratum (deficit zero) and the top-two-mass union (deficit at most one).
    This is an explicit finite grid, not an unrestricted search over predicates.
    """

    specifications: dict[str, dict[str, int]] = {}

    def add(constraints: dict[str, int]) -> None:
        rule_id = ";".join(f"{key}={constraints[key]}" for key in sorted(constraints))
        specifications.setdefault(rule_id, constraints)

    for deficit in range(k + 1):
        add({"mass_deficit_leq": deficit})
    for beta in range(max(record["beta"] for record in records) + 1):
        add({"beta_leq": beta})
    for components in range(max(record["components"] for record in records) + 1):
        add({"components_leq": components})
    for multiplicity in range(max(record["max_multiplicity"] for record in records) + 1):
        add({"max_multiplicity_leq": multiplicity})
    add({"components_eq": 1})
    add({"max_multiplicity_eq": 1})

    for deficit in (0, 1):
        for beta in range(max(record["beta"] for record in records) + 1):
            add({"mass_deficit_leq": deficit, "beta_leq": beta})
        for components in range(max(record["components"] for record in records) + 1):
            add({"mass_deficit_leq": deficit, "components_leq": components})
        for multiplicity in range(max(record["max_multiplicity"] for record in records) + 1):
            add({"mass_deficit_leq": deficit, "max_multiplicity_leq": multiplicity})

    rules: list[dict[str, object]] = []
    for rule_id, constraints in specifications.items():
        indices = [
            index
            for index, record in enumerate(records)
            if matches_relative_rule(record, k, constraints)
        ]
        rules.append(
            {
                "rule_id": rule_id,
                "constraints": constraints,
                "column_indices": indices,
                "column_count": len(indices),
            }
        )
    rules.sort(key=lambda rule: (rule["column_count"], rule["rule_id"]))
    return rules


def build_augmented_matrix(system: SavedSystem, prime: int) -> flint.nmod_mat:
    rows = len(system.row_keys) + system.n
    columns = len(system.records)
    matrix = flint.nmod_mat(rows, columns + 1, prime)
    row_index = {key: index for index, key in enumerate(system.row_keys)}
    representative_to_column = {
        raw_index: column for column, raw_index in enumerate(system.representative_raw_indices)
    }
    seen = 0
    with gzip.open(system.path, "rt") as handle:
        for raw_index, line in enumerate(handle):
            column = representative_to_column.get(raw_index)
            if column is None:
                continue
            item = json.loads(line)
            for key, coefficient in item["h"].items():
                matrix[row_index[key], column] = int(coefficient) % prime
            for index, coefficient in enumerate(item["lin"]):
                matrix[len(system.row_keys) + index, column] = int(coefficient) % prime
            seen += 1
    if seen != columns:
        raise AssertionError("did not reload every W representative")
    matrix[rows - 1, columns] = 1
    return matrix


def pivot_columns(matrix: flint.nmod_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    search_from = 0
    for row in range(rank):
        while search_from < matrix.ncols() and matrix[row, search_from] == 0:
            search_from += 1
        if search_from == matrix.ncols():
            raise AssertionError("RREF row has no pivot")
        pivots.append(search_from)
        search_from += 1
    return pivots


def compact_rows_from_rref(matrix: flint.nmod_mat, rank: int) -> list[list[int]]:
    return [
        [int(matrix[row, column]) for column in range(matrix.ncols())]
        for row in range(rank)
    ]


def rank_selected(compact_rows: Sequence[Sequence[int]], columns: Sequence[int], prime: int) -> int:
    selected = [[row[column] for column in columns] for row in compact_rows]
    return flint.nmod_mat(selected, prime).rank()


def rank_selected_with_target(
    compact_rows: Sequence[Sequence[int]], columns: Sequence[int], target_column: int, prime: int
) -> tuple[int, int, bool]:
    """Return rank(A), rank([A|b]), and membership after one augmented RREF."""

    selected_columns = list(columns) + [target_column]
    selected = [[row[column] for column in selected_columns] for row in compact_rows]
    reduced, augmented_rank = flint.nmod_mat(selected, prime).rref()
    target_is_pivot = len(columns) in pivot_columns(reduced, augmented_rank)
    rank = augmented_rank - int(target_is_pivot)
    return rank, augmented_rank, not target_is_pivot


def cumulative_tables(
    records: Sequence[dict[str, int]], candidates: Sequence[dict[str, object]]
) -> list[dict[str, object]]:
    """Expose rank growth for each requested cumulative ordering."""

    counts = feature_counts(records)
    lookup = {
        (str(item["feature"]), tuple(map(int, item["allowed_values"]))): item
        for item in candidates
    }
    tables: list[dict[str, object]] = []
    for feature in FEATURES:
        values = sorted(counts[feature])
        orders = {
            "low_to_high": values,
            "high_to_low": list(reversed(values)),
            "small_strata_first": sorted(values, key=lambda value: (counts[feature][value], value)),
        }
        for order_name, order in orders.items():
            steps: list[dict[str, object]] = []
            allowed: list[int] = []
            previous_rank = 0
            for value in order:
                allowed.append(value)
                candidate = lookup[(feature, tuple(sorted(allowed)))]
                rank = int(candidate["rank"])
                steps.append(
                    {
                        "added_value": value,
                        "added_stratum_count": counts[feature][value],
                        "allowed_values": sorted(allowed),
                        "cumulative_column_count": candidate["column_count"],
                        "rank": rank,
                        "rank_growth": rank - previous_rank,
                        "augmented_rank": candidate["augmented_rank"],
                        "max_member": candidate["max_member"],
                        "full_span": candidate["full_span"],
                    }
                )
                previous_rank = rank
            tables.append(
                {
                    "feature": feature,
                    "order": order_name,
                    "stratum_order": order,
                    "steps": steps,
                }
            )
    return tables


def tree_indices(system: SavedSystem) -> list[int]:
    return [
        index
        for index, record in enumerate(system.records)
        if record["s"] == 4
        and record["beta"] == 0
        and record["components"] == 1
        and record["active_vertices"] == 9
    ]


def scan_prime(
    system: SavedSystem,
    rules: Sequence[dict[str, object]],
    relative_rules: Sequence[dict[str, object]],
    prime: int,
) -> dict[str, object]:
    started = time.monotonic()
    full_matrix = build_augmented_matrix(system, prime)
    built_seconds = time.monotonic() - started
    rref_started = time.monotonic()
    reduced, augmented_rank = full_matrix.rref()
    rref_seconds = time.monotonic() - rref_started
    del full_matrix
    gc.collect()

    columns = len(system.records)
    pivots = pivot_columns(reduced, augmented_rank)
    target_is_pivot = columns in pivots
    full_rank = augmented_rank - int(target_is_pivot)
    expected = EXPECTED_FULL_RANK[system.n]
    if full_rank != expected or augmented_rank != expected or target_is_pivot:
        raise AssertionError(
            f"n={system.n} p={prime} full gate failed: "
            f"rank={full_rank}, augmented={augmented_rank}, target_pivot={target_is_pivot}"
        )

    compact_started = time.monotonic()
    compact_rows = compact_rows_from_rref(reduced, augmented_rank)
    compact_seconds = time.monotonic() - compact_started
    del reduced
    gc.collect()

    tree = tree_indices(system)
    tree_rank, tree_augmented_rank, tree_member = rank_selected_with_target(
        compact_rows, tree, columns, prime
    )
    if system.n == 9:
        if len(tree) != 739 or tree_rank != 360 or tree_augmented_rank != 361:
            raise AssertionError(
                f"n=9 tree gate failed at p={prime}: "
                f"{len(tree)} columns, ranks {tree_rank}/{tree_augmented_rank}"
            )

    candidates: list[dict[str, object]] = []
    rank_cache: dict[tuple[int, ...], tuple[int, int, bool, float]] = {}
    for number, rule in enumerate(rules, 1):
        count = int(rule["column_count"])
        result = {
            "feature": rule["feature"],
            "allowed_values": rule["allowed_values"],
            "origins": rule["origins"],
            "column_count": count,
            "full_rank_denominator": full_rank,
        }
        rank_started = time.monotonic()
        index_key = tuple(rule["column_indices"])
        cached = rank_cache.get(index_key)
        if cached is None:
            rank, augmented_rank, max_member = rank_selected_with_target(
                compact_rows, index_key, columns, prime
            )
            rank_seconds = time.monotonic() - rank_started
            rank_cache[index_key] = (rank, augmented_rank, max_member, rank_seconds)
        else:
            rank, augmented_rank, max_member, rank_seconds = cached
        result.update(
            {
                "rank": rank,
                "augmented_rank": augmented_rank,
                "rank_upper_bound": count,
                "full_span": rank == full_rank,
                "max_member": max_member,
                "disposition": "ranked_augmented",
                "rank_seconds": rank_seconds,
                "rank_cache_hit": cached is not None,
            }
        )
        candidates.append(result)
        print(
            f"n={system.n} p={prime} candidate={number}/{len(rules)} "
            f"count={count} rank={result['rank']} full={result['full_span']}",
            flush=True,
        )

    relative_candidates: list[dict[str, object]] = []
    for number, rule in enumerate(relative_rules, 1):
        index_key = tuple(rule["column_indices"])
        cached = rank_cache.get(index_key)
        if cached is None:
            rank_started = time.monotonic()
            rank, augmented_rank, max_member = rank_selected_with_target(
                compact_rows, index_key, columns, prime
            )
            rank_seconds = time.monotonic() - rank_started
            rank_cache[index_key] = (rank, augmented_rank, max_member, rank_seconds)
        else:
            rank, augmented_rank, max_member, rank_seconds = cached
        result = {
            "rule_id": rule["rule_id"],
            "constraints": rule["constraints"],
            "column_count": rule["column_count"],
            "rank": rank,
            "augmented_rank": augmented_rank,
            "max_member": max_member,
            "full_span": rank == full_rank,
            "full_rank_denominator": full_rank,
            "rank_seconds": rank_seconds,
            "rank_cache_hit": cached is not None,
        }
        relative_candidates.append(result)
        print(
            f"n={system.n} p={prime} relative={number}/{len(relative_rules)} "
            f"rule={rule['rule_id']} count={rule['column_count']} "
            f"rank={rank} aug={augmented_rank} full={rank == full_rank}",
            flush=True,
        )

    del compact_rows
    gc.collect()
    return {
        "prime": prime,
        "full": {
            "column_count": columns,
            "hinge_row_count": len(system.row_keys),
            "linear_row_count": system.n,
            "rank": full_rank,
            "augmented_rank": augmented_rank,
            "max_member": True,
            "expected_rank_gate": expected,
        },
        "n9_tree_negative_control": {
            "applicable": system.n == 9,
            "predicate": "s=4,beta=0,components=1,active_vertices=9",
            "column_count": len(tree),
            "rank": tree_rank,
            "augmented_rank": tree_augmented_rank,
            "max_member": tree_member,
        },
        "candidates": candidates,
        "cumulative_tables": cumulative_tables(system.records, candidates),
        "relative_candidates": relative_candidates,
        "timing_seconds": {
            "matrix_build": built_seconds,
            "full_augmented_rref": rref_seconds,
            "compact_row_extract": compact_seconds,
            "total": time.monotonic() - started,
        },
    }


def load_g0027_records(path: Path) -> tuple[dict[str, object], list[dict[str, int]]]:
    with gzip.open(path, "rt") as handle:
        payload = json.load(handle)
    raw_records = payload["records"]
    records: list[dict[str, int]] = []
    for raw in raw_records:
        negative = tuple(normalize_edge(edge) for edge in raw["negative_edges"])
        positive = tuple(normalize_edge(edge) for edge in raw["positive_edges"])
        stats = signed_stats(negative, positive)
        expected = {
            "s": int(raw["signed_mass"]),
            "beta": int(raw["abs_beta"]),
            "components": int(raw["abs_components"]),
            "active_vertices": int(raw["active_vertices"]),
        }
        if any(stats[key] != value for key, value in expected.items()):
            raise AssertionError("G-0027 stored topology disagrees with independent recomputation")
        records.append(stats)
    if len(records) != 754_017:
        raise AssertionError(f"G-0027 census gate failed: {len(records)} records")
    return payload, records


def add_n11_counts(result: dict[str, object], records: Sequence[dict[str, int]]) -> None:
    for n_text, n_result in result["systems"].items():
        del n_text
        seen: set[tuple[str, tuple[int, ...]]] = set()
        for prime_result in n_result["prime_results"]:
            for candidate in prime_result["candidates"]:
                key = (
                    str(candidate["feature"]),
                    tuple(map(int, candidate["allowed_values"])),
                )
                if key in seen:
                    continue
                seen.add(key)
                feature, allowed_tuple = key
                allowed = set(allowed_tuple)
                count = sum(record[feature] in allowed for record in records)
                n_result["n11_same_rule_counts"].append(
                    {
                        "feature": feature,
                        "allowed_values": list(allowed_tuple),
                        "column_count": count,
                        "universe_denominator": len(records),
                    }
                )
        n_result["n11_same_rule_counts"].sort(
            key=lambda item: (item["column_count"], item["feature"], item["allowed_values"])
        )


def add_n11_relative_counts(result: dict[str, object], records: Sequence[dict[str, int]]) -> None:
    """Apply the same constraints at degree k=5, so mass is transferred by k-s."""

    seen: dict[str, dict[str, object]] = {}
    for n in (9, 10):
        for item in result["systems"][str(n)]["prime_results"][0]["relative_candidates"]:
            seen.setdefault(
                item["rule_id"],
                {"rule_id": item["rule_id"], "constraints": item["constraints"]},
            )
    counts: list[dict[str, object]] = []
    for item in seen.values():
        count = sum(matches_relative_rule(record, 5, item["constraints"]) for record in records)
        counts.append(
            {
                **item,
                "column_count": count,
                "universe_denominator": len(records),
            }
        )
    counts.sort(key=lambda item: (item["column_count"], item["rule_id"]))
    result["n11_relative_rule_counts"] = counts


def common_full_span_rules(result: dict[str, object]) -> list[dict[str, object]]:
    per_n: dict[int, dict[tuple[str, tuple[int, ...]], dict[str, object]]] = {}
    for n in (9, 10):
        n_result = result["systems"][str(n)]
        prime_maps: list[dict[tuple[str, tuple[int, ...]], dict[str, object]]] = []
        for prime_result in n_result["prime_results"]:
            prime_maps.append(
                {
                    (item["feature"], tuple(item["allowed_values"])): item
                    for item in prime_result["candidates"]
                }
            )
        merged: dict[tuple[str, tuple[int, ...]], dict[str, object]] = {}
        for key in set(prime_maps[0]) & set(prime_maps[1]):
            if all(mapping[key]["full_span"] for mapping in prime_maps):
                merged[key] = {
                    "column_count": prime_maps[0][key]["column_count"],
                    "ranks": {str(prime): mapping[key]["rank"] for prime, mapping in zip(PRIMES, prime_maps)},
                }
        per_n[n] = merged

    n11_lookup = {
        (item["feature"], tuple(item["allowed_values"])): item["column_count"]
        for item in result["systems"]["9"]["n11_same_rule_counts"]
    }
    common: list[dict[str, object]] = []
    for key in set(per_n[9]) & set(per_n[10]):
        common.append(
            {
                "feature": key[0],
                "allowed_values": list(key[1]),
                "n9": per_n[9][key],
                "n10": per_n[10][key],
                "n11_column_count": n11_lookup[key],
                "n11_universe_denominator": 754_017,
                "n11_max_membership": "NOT_TESTED",
            }
        )
    common.sort(key=lambda item: (item["n11_column_count"], item["feature"], item["allowed_values"]))
    return common


def smallest_common_relative_full_span_rules(result: dict[str, object]) -> list[dict[str, object]]:
    """Rules full-rank and target-member at both arities and both primes."""

    per_n: dict[int, dict[str, dict[str, object]]] = {}
    for n in (9, 10):
        prime_maps = [
            {item["rule_id"]: item for item in prime_result["relative_candidates"]}
            for prime_result in result["systems"][str(n)]["prime_results"]
        ]
        per_n[n] = {
            rule_id: {
                "column_count": prime_maps[0][rule_id]["column_count"],
                "ranks": {
                    str(prime_result["prime"]): prime_map[rule_id]["rank"]
                    for prime_result, prime_map in zip(
                        result["systems"][str(n)]["prime_results"], prime_maps
                    )
                },
                "augmented_ranks": {
                    str(prime_result["prime"]): prime_map[rule_id]["augmented_rank"]
                    for prime_result, prime_map in zip(
                        result["systems"][str(n)]["prime_results"], prime_maps
                    )
                },
            }
            for rule_id in set(prime_maps[0]) & set(prime_maps[1])
            if all(
                prime_map[rule_id]["full_span"] and prime_map[rule_id]["max_member"]
                for prime_map in prime_maps
            )
        }
    n11 = {item["rule_id"]: item for item in result["n11_relative_rule_counts"]}
    common: list[dict[str, object]] = []
    for rule_id in set(per_n[9]) & set(per_n[10]):
        common.append(
            {
                "rule_id": rule_id,
                "constraints": n11[rule_id]["constraints"],
                "n9": per_n[9][rule_id],
                "n10": per_n[10][rule_id],
                "n11_column_count": n11[rule_id]["column_count"],
                "n11_universe_denominator": n11[rule_id]["universe_denominator"],
                "n11_max_membership": "NOT_TESTED",
            }
        )
    common.sort(key=lambda item: (item["n11_column_count"], item["rule_id"]))
    return common


def low_to_high_growth_extrapolation(result: dict[str, object]) -> list[dict[str, object]]:
    """Order-conditional empirical n=11 increments from pooled n=9/n=10 rates.

    For a feature value v, let dr_n(v) be the rank increase when v is appended
    in the feature's low-to-high cumulative order.  The recorded rate is

        (dr_9(v) + dr_10(v)) / (count_9(v) + count_10(v)).

    Multiplying this rate by the n=11 stratum count is only an extrapolation,
    not a rank bound.  Values absent at n=9/n=10 have no prediction.
    """

    n11_counts = result["g0027"]["feature_counts"]
    rows: list[dict[str, object]] = []
    for feature in FEATURES:
        growth_by_n: dict[int, dict[int, tuple[int, int]]] = {}
        for n in (9, 10):
            tables = result["systems"][str(n)]["prime_results"][0]["cumulative_tables"]
            table = next(
                item for item in tables if item["feature"] == feature and item["order"] == "low_to_high"
            )
            growth_by_n[n] = {
                int(step["added_value"]): (
                    int(step["rank_growth"]),
                    int(step["added_stratum_count"]),
                )
                for step in table["steps"]
            }
        all_values = sorted(map(int, n11_counts[feature]))
        for value in all_values:
            n11_stratum_count = int(n11_counts[feature][value])
            if value in growth_by_n[9] and value in growth_by_n[10]:
                numerator = growth_by_n[9][value][0] + growth_by_n[10][value][0]
                denominator = growth_by_n[9][value][1] + growth_by_n[10][value][1]
                predicted = round(numerator * n11_stratum_count / denominator)
                rate = numerator / denominator
            else:
                numerator = denominator = predicted = None
                rate = None
            rows.append(
                {
                    "feature": feature,
                    "value": value,
                    "n11_stratum_count": n11_stratum_count,
                    "pooled_rank_growth_numerator": numerator,
                    "pooled_added_columns_denominator": denominator,
                    "pooled_growth_per_column": rate,
                    "predicted_n11_rank_growth_rounded": predicted,
                    "order_condition": "low_to_high",
                }
            )
    return rows


def full_mass_beta_growth_extrapolation(
    result: dict[str, object], n11_records: Sequence[dict[str, int]]
) -> list[dict[str, object]]:
    """Degree-relative beta growth inside s=k, pooled across n=9 and n=10.

    Rank growth depends on order.  This table fixes beta=0,1,... and restricts
    throughout to the full-mass stratum s=k.  Values beta>4 have no low-arity
    analogue and therefore receive no numerical prediction.
    """

    low: dict[int, dict[int, dict[str, int]]] = {}
    for n in (9, 10):
        candidates = {
            item["rule_id"]: item
            for item in result["systems"][str(n)]["prime_results"][0]["relative_candidates"]
        }
        prior_rank = 0
        prior_count = 0
        rows: dict[int, dict[str, int]] = {}
        for beta in range(5):
            item = candidates[f"beta_leq={beta};mass_deficit_leq=0"]
            rows[beta] = {
                "added_columns": int(item["column_count"]) - prior_count,
                "rank_growth": int(item["rank"]) - prior_rank,
            }
            prior_count = int(item["column_count"])
            prior_rank = int(item["rank"])
        low[n] = rows

    n11_counts = Counter(
        record["beta"] for record in n11_records if record["s"] == 5
    )
    result_rows: list[dict[str, object]] = []
    for beta in sorted(n11_counts):
        if beta in low[9] and beta in low[10]:
            numerator = low[9][beta]["rank_growth"] + low[10][beta]["rank_growth"]
            denominator = low[9][beta]["added_columns"] + low[10][beta]["added_columns"]
            predicted = round(numerator * n11_counts[beta] / denominator)
            rate = numerator / denominator
        else:
            numerator = denominator = predicted = rate = None
        result_rows.append(
            {
                "beta": beta,
                "n9_added_columns": low.get(9, {}).get(beta, {}).get("added_columns"),
                "n9_rank_growth": low.get(9, {}).get(beta, {}).get("rank_growth"),
                "n10_added_columns": low.get(10, {}).get(beta, {}).get("added_columns"),
                "n10_rank_growth": low.get(10, {}).get(beta, {}).get("rank_growth"),
                "pooled_rank_growth_numerator": numerator,
                "pooled_added_columns_denominator": denominator,
                "pooled_growth_per_column": rate,
                "n11_full_mass_stratum_count": n11_counts[beta],
                "predicted_n11_rank_growth_rounded": predicted,
                "order_condition": "within s=k, add beta=0,1,...",
            }
        )
    return result_rows


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--threads", type=int, default=6)
    parser.add_argument(
        "--postprocess-existing",
        action="store_true",
        help="recount n=11 relative rules/growth without replaying modular ranks",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not 1 <= args.threads <= 6:
        raise SystemExit("--threads must be between 1 and the bead limit 6")
    flint.ctx.threads = args.threads
    os.environ.setdefault("OMP_NUM_THREADS", str(args.threads))
    os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
    os.environ.setdefault("MKL_NUM_THREADS", "1")

    if args.postprocess_existing:
        existing = json.loads(args.output.read_text())
        _payload, n11_records = load_g0027_records(G0027)
        add_n11_relative_counts(existing, n11_records)
        existing["smallest_common_relative_full_span_rules"] = (
            smallest_common_relative_full_span_rules(existing)
        )
        existing["full_mass_beta_growth_extrapolation"] = (
            full_mass_beta_growth_extrapolation(existing, n11_records)
        )
        atomic_write_json(args.output, existing)
        print(f"POSTPROCESSED {args.output}", flush=True)
        return

    result: dict[str, object] = {
        "schema": "max11-gmp7-natural-w-strata-span-v1",
        "primes": list(PRIMES),
        "threads": args.threads,
        "inputs": {
            str(path.relative_to(ROOT)): {
                "bytes": path.stat().st_size,
                "sha256": sha256_path(path),
            }
            for path in (*SYSTEMS.values(), G0027)
        },
        "systems": {},
        "g0027": {},
        "common_full_span_rules": [],
        "n11_relative_rule_counts": [],
        "smallest_common_relative_full_span_rules": [],
        "no_claim": (
            "These finite two-prime ranks size natural first experiments only. "
            "They neither decide MAX11 nor prove a rational identity or a depth lower bound."
        ),
    }

    with tempfile.TemporaryDirectory(prefix="gmp7-strata-") as temporary:
        scratch = Path(temporary)
        for n in (9, 10):
            scan_started = time.monotonic()
            system = scan_saved_system(n, SYSTEMS[n], scratch)
            rules = candidate_rules(system.records)
            relative_rules = relative_candidate_rules(system.records, (n - 1) // 2)
            n_result = {
                "raw_template_count": system.raw_template_count,
                "w_orbit_count": len(system.records),
                "collapsed_duplicate_count": system.duplicate_w_columns_compared,
                "hinge_row_count": len(system.row_keys),
                "feature_counts": feature_counts(system.records),
                "controls": system.controls,
                "scan_seconds": time.monotonic() - scan_started,
                "prime_results": [],
                "n11_same_rule_counts": [],
            }
            result["systems"][str(n)] = n_result
            atomic_write_json(args.output, result)
            for prime in PRIMES:
                print(f"START n={n} prime={prime}", flush=True)
                n_result["prime_results"].append(
                    scan_prime(system, rules, relative_rules, prime)
                )
                atomic_write_json(args.output, result)
            del system
            gc.collect()

        print("START G-0027 census recount", flush=True)
        g0027_payload, n11_records = load_g0027_records(G0027)
        result["g0027"] = {
            "schema": g0027_payload.get("schema"),
            "record_count": len(n11_records),
            "feature_counts": feature_counts(n11_records),
            "controls": partition_controls(n11_records),
        }
        del g0027_payload
        add_n11_counts(result, n11_records)
        add_n11_relative_counts(result, n11_records)
        result["common_full_span_rules"] = common_full_span_rules(result)
        result["smallest_common_relative_full_span_rules"] = (
            smallest_common_relative_full_span_rules(result)
        )
        result["low_to_high_growth_extrapolation"] = low_to_high_growth_extrapolation(result)
        result["full_mass_beta_growth_extrapolation"] = (
            full_mass_beta_growth_extrapolation(result, n11_records)
        )
        atomic_write_json(args.output, result)
    print(f"WROTE {args.output}", flush=True)


if __name__ == "__main__":
    main()
