#!/usr/bin/env python3
"""Translate a G-0027 exact witness to the pinned upstream pair format."""

from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def pair_representative(record: dict[str, Any], branch_edges: int) -> list[list[list[int]]]:
    signed_mass = int(record["signed_mass"])
    negative = [[int(u), int(v)] for u, v in record["negative_edges"]]
    positive = [[int(u), int(v)] for u, v in record["positive_edges"]]
    if len(negative) != signed_mass or len(positive) != signed_mass:
        raise ValueError("signed record edge count does not equal signed_mass")
    if not 0 <= signed_mass <= branch_edges:
        raise ValueError("signed_mass lies outside branch size")
    # G-0027 proves that any common loopless carrier gives the same fully
    # symmetrised atom.  Use a fixed carrier for byte-deterministic output.
    common = [[0, 1] for _ in range(branch_edges - signed_mass)]
    return [negative + common, positive + common]


def synthetic_five_l_pair(branch_edges: int) -> list[list[list[int]]]:
    # Five common self-loops symmetrise to 5*(n-1)! times each coordinate,
    # exactly the synthetic 5L column.  A loopless common edge would instead
    # reproduce G-0027's signed-mass-zero max-edge atom.
    loops = [[0, 0] for _ in range(branch_edges)]
    return [list(loops), list(loops)]


def one_based(pair: list[list[list[int]]]) -> list[list[list[int]]]:
    return [[[u + 1, v + 1] for u, v in side] for side in pair]


def convert(universe_path: Path, witness_path: Path, output: Path) -> dict[str, Any]:
    universe_sha = sha256(universe_path)
    opener = gzip.open if universe_path.suffix == ".gz" else open
    with opener(universe_path, "rt", encoding="utf-8") as handle:
        universe = json.load(handle)
    witness = json.loads(witness_path.read_text(encoding="utf-8"))
    if universe.get("schema") != "max11-g0027-loopless-signed-degree5-universe-v1":
        raise ValueError("unsupported universe schema")
    if int(witness["n"]) != int(universe["n"]):
        raise ValueError("witness and universe dimensions differ")
    if witness.get("system_sha256") != universe_sha:
        raise ValueError("witness is not hash-bound to the named universe")

    records = universe["records"]
    branch_edges = int(universe["branch_edge_occurrences"])
    seen: set[int] = set()
    terms = []
    for entry in witness["coefficients"]:
        source_index = int(entry["column"])
        if source_index in seen:
            raise ValueError(f"witness repeats source column {source_index}")
        seen.add(source_index)
        coefficient = Fraction(entry["coefficient"])
        if not coefficient:
            continue
        if 0 <= source_index < len(records):
            pair = pair_representative(records[source_index], branch_edges)
        elif source_index == len(records):
            pair = synthetic_five_l_pair(branch_edges)
        else:
            raise ValueError(f"witness source column {source_index} is outside the universe")
        if any(len(side) != branch_edges for side in pair):
            raise AssertionError("constructed upstream branch has the wrong size")
        terms.append({"coefficient": str(coefficient), "pair": one_based(pair)})

    payload = {"n": int(universe["n"]), "terms": terms}
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")
    return {
        "verdict": "PASS",
        "universe": str(universe_path),
        "universe_sha256": universe_sha,
        "witness": str(witness_path),
        "witness_sha256": sha256(witness_path),
        "support_terms_numerator": len(terms),
        "witness_entries_denominator": len(witness["coefficients"]),
        "output": str(output),
        "output_sha256": sha256(output),
        "no_claim": "Format translation is not an independent verification of the identity.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--universe", type=Path, required=True)
    parser.add_argument("--witness", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(convert(args.universe, args.witness, args.output), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
