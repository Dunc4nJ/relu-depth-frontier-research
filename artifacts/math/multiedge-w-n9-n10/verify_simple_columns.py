#!/usr/bin/env python3
"""Exact simple-W bridge from enumerated records through colgen to saved systems."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[3]
STRATA_SOURCE = ROOT / "artifacts/math/strata-span-n9-n10/strata_span.py"
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rank_multiedge as binary  # noqa: E402


EXPECTED_SIMPLE = {9: 6_197, 10: 7_203}
EXPECTED_RAW = {9: 10_976, 10: 12_248}
SCHEMA = "max11-gmp9-simple-column-bridge-v1"


def load_strata():
    spec = importlib.util.spec_from_file_location("gmp7_strata", STRATA_SOURCE)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {STRATA_SOURCE}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


S = load_strata()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def load_universe(path: Path) -> dict[str, object]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt") as handle:
        return json.load(handle)


def atomic_write_json(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")
    temporary.replace(path)


def verify(args: argparse.Namespace) -> dict[str, object]:
    started = time.monotonic()
    n = args.n
    universe = load_universe(args.universe)
    records = universe["records"]
    if int(universe["n"]) != n or int(universe["branch_edge_occurrences"]) != 4:
        raise ValueError("universe dimensions do not match")
    maxima = [binary.recompute_max_multiplicity(record) for record in records]
    simple_indices = [index for index, maximum in enumerate(maxima) if maximum <= 1]
    if len(simple_indices) != EXPECTED_SIMPLE[n]:
        raise AssertionError("simple-W universe count known answer failed")

    with tempfile.TemporaryDirectory(prefix=f"gmp9-n{n}-") as scratch:
        database = sqlite3.connect(Path(scratch) / "saved-columns.sqlite")
        database.execute("PRAGMA journal_mode=OFF")
        database.execute("PRAGMA synchronous=OFF")
        database.execute("PRAGMA temp_store=FILE")
        database.execute(
            "CREATE TABLE columns (w_key BLOB PRIMARY KEY, payload BLOB NOT NULL, seen INTEGER NOT NULL) WITHOUT ROWID"
        )
        raw_count = 0
        duplicate_count = 0
        with gzip.open(args.saved_system, "rt") as handle:
            for line in handle:
                item = json.loads(line)
                negative, positive = S.cancelled_w(item["A"], item["B"])
                key = S.signed_w_key(negative, positive, n)
                payload = canonical_bytes({"h": item["h"], "lin": item["lin"]})
                prior = database.execute(
                    "SELECT payload FROM columns WHERE w_key=?", (sqlite3.Binary(key),)
                ).fetchone()
                if prior is None:
                    database.execute(
                        "INSERT INTO columns(w_key,payload,seen) VALUES (?,?,0)",
                        (sqlite3.Binary(key), sqlite3.Binary(payload)),
                    )
                elif bytes(prior[0]) != payload:
                    raise AssertionError("saved same-W templates have unequal exact columns")
                else:
                    duplicate_count += 1
                raw_count += 1
        database.commit()
        saved_unique = int(database.execute("SELECT COUNT(*) FROM columns").fetchone()[0])
        if raw_count != EXPECTED_RAW[n] or saved_unique != EXPECTED_SIMPLE[n]:
            raise AssertionError("saved-system denominator known answer failed")

        universe_keys: dict[int, bytes] = {}
        distinct_keys: set[bytes] = set()
        for index in simple_indices:
            record = records[index]
            key = S.signed_w_key(
                tuple(tuple(edge) for edge in record["negative_edges"]),
                tuple(tuple(edge) for edge in record["positive_edges"]),
                n,
            )
            if key in distinct_keys:
                raise AssertionError("enumerated simple-W canonical key is duplicated")
            if database.execute(
                "SELECT 1 FROM columns WHERE w_key=?", (sqlite3.Binary(key),)
            ).fetchone() is None:
                raise AssertionError("enumerated simple-W key is absent from saved system")
            distinct_keys.add(key)
            universe_keys[index] = key
        if len(distinct_keys) != saved_unique:
            raise AssertionError("simple-W key sets have unequal denominators")

        exact_matches = 0
        mutation_rejections = 0
        for index, linear, hinges in binary.read_columns(args.columns):
            if index not in universe_keys:
                continue
            hinge_map = {
                ",".join(map(str, direction)): coefficient
                for direction, coefficient in hinges
            }
            payload_value = {"h": hinge_map, "lin": linear}
            payload = canonical_bytes(payload_value)
            key = universe_keys[index]
            expected = database.execute(
                "SELECT payload,seen FROM columns WHERE w_key=?", (sqlite3.Binary(key),)
            ).fetchone()
            if expected is None or bytes(expected[0]) != payload:
                raise AssertionError(f"colgen simple-W exact mismatch at record {index}")
            if int(expected[1]) != 0:
                raise AssertionError("enumerated simple-W column visited more than once")
            database.execute(
                "UPDATE columns SET seen=1 WHERE w_key=?", (sqlite3.Binary(key),)
            )
            exact_matches += 1

            # Equality-destroying one-unit mutation must no longer match.
            mutated = {"h": dict(hinge_map), "lin": list(linear)}
            mutated["lin"][0] += 1
            if canonical_bytes(mutated) == bytes(expected[0]):
                raise AssertionError("planted coefficient mutation escaped detection")
            mutation_rejections += 1
        database.commit()
        unseen = int(database.execute("SELECT COUNT(*) FROM columns WHERE seen=0").fetchone()[0])
        database.close()
        if exact_matches != EXPECTED_SIMPLE[n] or unseen != 0:
            raise AssertionError("not every simple-W column was exactly compared")

    return {
        "schema": SCHEMA,
        "result": "PASS",
        "n": n,
        "universe": str(args.universe),
        "universe_sha256": sha256_path(args.universe),
        "exact_columns": str(args.columns),
        "exact_columns_sha256": sha256_path(args.columns),
        "saved_system": str(args.saved_system),
        "saved_system_sha256": sha256_path(args.saved_system),
        "strata_key_source": str(STRATA_SOURCE.relative_to(ROOT)),
        "strata_key_source_sha256": sha256_path(STRATA_SOURCE),
        "denominators": {
            "universe_records": len(records),
            "simple_w_records": len(simple_indices),
            "saved_raw_templates": raw_count,
            "saved_unique_w": saved_unique,
            "saved_collapsed_duplicates": duplicate_count,
        },
        "controls": {
            "simple_w_canonical_key_sets_equal": True,
            "exact_simple_w_columns_equal": exact_matches,
            "exact_simple_w_column_denominator": len(simple_indices),
            "one_unit_coefficient_mutations_rejected": mutation_rejections,
            "one_unit_coefficient_mutation_denominator": len(simple_indices),
        },
        "wall_seconds": time.monotonic() - started,
        "no_claim": (
            "This exact bridge validates the finite simple-W subset only. It does not "
            "validate a rank, an exact-Q MAX identity, or any n=11 statement."
        ),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, choices=(9, 10), required=True)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--columns", type=Path, required=True)
    parser.add_argument("--saved-system", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    result = verify(args)
    atomic_write_json(args.output, result)
    print(
        f"GMP9_SIMPLE_BRIDGE_PASS n={args.n} "
        f"matches={result['controls']['exact_simple_w_columns_equal']}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
