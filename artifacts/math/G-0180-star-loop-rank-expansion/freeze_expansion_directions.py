#!/usr/bin/env python3
"""Freeze the nested G-0180 expansion order before any new STAR pricing."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
from typing import Any


EXPECTED = {
    "records": "c4380bff3d96fafa084e387ef1b972a3f362a4614adaca8f596311958b54c4d4",
    "selected": "231752384d357be45a9d2513a9185539bf0df970640c28e4f259da37fc8a982f",
    "harvester": "506f251dff9ee30840dffe81e5112ca2713b136c634e07a36d3fca4c4c92e3ce",
    "diagnostic": "95eb3e24cb6b867c99e310bdbed40c2f4c6087e71d2867b4d441b677d9d7b69f",
    "diagnostic_source": "ee5a0301d1fb45505469f1d6bbc470cbe43eb52467ca0497a1d64b859ed56858",
}
HASH_DOMAIN = b"G-0179-unused-direction-order-v1\0"
REMOVED_SEQUENCES = {1548, 4259}


class FreezeError(RuntimeError):
    """A frozen input or deterministic selection invariant failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_json(value: Any) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_new(path: Path, payload: bytes) -> None:
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def load_harvester(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location("g0180_frozen_harvester", path)
    if spec is None or spec.loader is None:
        raise FreezeError("could not import frozen structural harvester")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def raw_i8(direction: tuple[int, ...]) -> bytes:
    if len(direction) != 11 or any(not -128 <= value <= 127 for value in direction):
        raise FreezeError("malformed signed-i8 direction")
    return bytes(value & 0xFF for value in direction)


def direction_digest(directions: list[tuple[int, ...]]) -> str:
    digest = hashlib.sha256()
    for direction in directions:
        digest.update(raw_i8(direction))
    return digest.hexdigest()


def hash_key(direction: tuple[int, ...]) -> tuple[bytes, bytes]:
    raw = raw_i8(direction)
    return hashlib.sha256(HASH_DOMAIN + raw).digest(), raw


def active(direction: tuple[int, ...]) -> bool:
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def validate_direction(direction: tuple[int, ...]) -> None:
    if sum(direction) != 0:
        raise FreezeError("direction sum drift")
    first = next((value for value in direction if value), None)
    if first is None or first < 0:
        raise FreezeError("direction orientation drift")
    if math.gcd(*direction) != 1:
        raise FreezeError("direction primitivity drift")
    if not active(direction) or direction[0] != 1:
        raise FreezeError("direction is not active d0=1")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--records", required=True, type=Path)
    parser.add_argument("--selected", required=True, type=Path)
    parser.add_argument("--harvester", required=True, type=Path)
    parser.add_argument("--diagnostic", required=True, type=Path)
    parser.add_argument("--diagnostic-source", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    arguments = parser.parse_args()
    if arguments.output.exists():
        raise FreezeError(f"refusing to overwrite {arguments.output}")

    paths = {
        "records": arguments.records.resolve(strict=True),
        "selected": arguments.selected.resolve(strict=True),
        "harvester": arguments.harvester.resolve(strict=True),
        "diagnostic": arguments.diagnostic.resolve(strict=True),
        "diagnostic_source": arguments.diagnostic_source.resolve(strict=True),
    }
    opening = {name: sha256_file(path) for name, path in paths.items()}
    if opening != EXPECTED:
        raise FreezeError(f"frozen input hash drift: {opening}")

    records_document = json.loads(paths["records"].read_bytes())
    all_records = records_document.get("records")
    if not isinstance(all_records, list) or len(all_records) != 5_773:
        raise FreezeError("record census drift")
    records = [
        record for record in all_records if record.get("sequence") not in REMOVED_SEQUENCES
    ]
    if len(records) != 5_771:
        raise FreezeError("retained-record census drift")

    selected_document = json.loads(paths["selected"].read_bytes())
    selected = [tuple(map(int, item)) for item in selected_document.get("directions", [])]
    if len(selected) != 5_771 or len(set(selected)) != 5_771:
        raise FreezeError("selected-direction census drift")

    harvester = load_harvester(paths["harvester"])
    prepared = [harvester.prepare_record(record) for record in records]
    adjacency = [
        harvester.candidate_directions(record, item)
        for record, item in zip(records, prepared, strict=True)
    ]
    universe = set().union(*(set(row) for row in adjacency))
    unpriced = universe - set(selected)
    if len(universe) != 16_661 or len(unpriced) != 10_890:
        raise FreezeError("candidate universe drift")

    diagnostic = json.loads(paths["diagnostic"].read_bytes())
    if diagnostic.get("result") != (
        "STABLE_TWO_PRIME_RANK_5291_WITH_480_UNRESOLVED_RECORD_DIRECTIONS"
    ):
        raise FreezeError("diagnostic result drift")
    dependent = diagnostic.get("dependent_records")
    if not isinstance(dependent, list) or len(dependent) != 480:
        raise FreezeError("dependent-record diagnostic drift")
    matched: list[tuple[int, ...]] = []
    previous_index = -1
    for item in dependent:
        record_index = item.get("retained_record_index")
        if not isinstance(record_index, int) or record_index <= previous_index:
            raise FreezeError("dependent-record ordering drift")
        previous_index = record_index
        raw_match = item.get("matched_expansion_direction")
        if raw_match is None:
            continue
        direction = tuple(map(int, raw_match))
        if direction not in adjacency[record_index] or direction not in unpriced:
            raise FreezeError("diagnostic match is not an unpriced own candidate")
        matched.append(direction)
    if len(matched) != 466 or len(set(matched)) != 466:
        raise FreezeError("dependent matching drift")

    hash_ranked = sorted(unpriced, key=hash_key)
    minimal = hash_ranked[:480]
    minimal_set = set(minimal)
    supplement = [direction for direction in matched if direction not in minimal_set]
    first_batch = minimal + supplement
    first_batch_set = set(first_batch)
    for direction in hash_ranked:
        if len(first_batch) == 1_024:
            break
        if direction not in first_batch_set:
            first_batch.append(direction)
            first_batch_set.add(direction)
    order = first_batch + [direction for direction in hash_ranked if direction not in first_batch_set]
    if len(order) != 10_890 or len(set(order)) != 10_890:
        raise FreezeError("expansion order census drift")
    for direction in order:
        validate_direction(direction)

    expected_expansion = diagnostic.get("candidate_expansion", {})
    checks = {
        "hash_ranked_unpriced_i8_sha256": direction_digest(hash_ranked),
        "minimal_prefix_i8_sha256": direction_digest(minimal),
        "dependent_matching_i8_sha256": direction_digest(matched),
        "support_supplement_i8_sha256": direction_digest(supplement),
        "first_batch_i8_sha256": direction_digest(first_batch),
        "expansion_order_i8_sha256": direction_digest(order),
    }
    for key, value in checks.items():
        if expected_expansion.get(key) != value:
            raise FreezeError(f"diagnostic expansion digest drift at {key}")

    lexicographic_unpriced = sorted(unpriced)
    closing = {name: sha256_file(path) for name, path in paths.items()}
    if closing != opening:
        raise FreezeError("input changed during direction freeze")
    result = {
        "schema": "g0180.star-loop-rank-expansion-directions.v1",
        "result": "NESTED_480_AND_1024_EXPANSION_FROZEN_BEFORE_STAR_PRICING",
        "claim_boundary": (
            "This freezes a post-G-0179 direction order only. The first 480 are "
            "domain-hash-selected without using the failed pivot structure, although the "
            "prefix length 480 was chosen after observing the G-0179 deficiency; the 1024 gate "
            "then includes every available deterministic support match for the disclosed "
            "two-prime nonpivot-record set. No expansion STAR price, target value, augmented "
            "rank, span result, representability result, or lower bound was used or is claimed."
        ),
        "selection_disclosure": {
            "unpriced_definition": (
                "Absent from the 5,771-column G-0179 STAR hinge matrix; values from any "
                "different residual or panel calculation were not consulted."
            ),
            "hash_prefix_480": (
                "Direction identities and order are target-, pivot-, and price-blind; prefix "
                "length 480 is rank-outcome-aware and has two columns of slack over the "
                "post-quotient minimum possible increment 478."
            ),
            "full_1024": (
                "Post-outcome rank-directed through structural incidence and the identical "
                "two-prime pivot-record set, but blind to all new STAR prices and to MAX11."
            ),
        },
        "bindings": {
            name: {"path": str(path), "bytes": path.stat().st_size, "sha256": opening[name]}
            for name, path in paths.items()
        },
        "candidate_census": {
            "candidate_universe": len(universe),
            "g0179_selected": len(selected),
            "g0179_star_unpriced": len(unpriced),
            "lexicographic_unpriced_i8_sha256": direction_digest(lexicographic_unpriced),
        },
        "order": {
            "hash_domain_utf8_with_terminal_nul": HASH_DOMAIN[:-1].decode() + "\\0",
            "hash_key": "SHA256(domain || raw_signed_i8_direction), raw_i8 tie-break",
            "hash_ranked_unpriced_i8_sha256": checks["hash_ranked_unpriced_i8_sha256"],
            "dependent_matching_count": len(matched),
            "dependent_matching_i8_sha256": checks["dependent_matching_i8_sha256"],
            "support_supplement_count": len(supplement),
            "support_supplement_i8_sha256": checks["support_supplement_i8_sha256"],
            "all_count": len(order),
            "all_i8_sha256": checks["expansion_order_i8_sha256"],
        },
        "gates": [
            {
                "name": "hash-prefix-480",
                "prefix_count": 480,
                "i8_sha256": checks["minimal_prefix_i8_sha256"],
                "maximum_possible_rank_increment": 480,
                "post_quotient_required_increment": 478,
                "slack_columns": 2,
                "prefix_length_is_rank_outcome_aware": True,
            },
            {
                "name": "rank-directed-1024",
                "prefix_count": 1_024,
                "i8_sha256": checks["first_batch_i8_sha256"],
                "contains_all_466_dependent_record_matches": True,
                "quotient_relevant_dependent_record_matches": 465,
                "removed_record_match_sequence": 3_140,
            },
        ],
        "directions": [list(direction) for direction in order],
        "all_directions_unique_primitive_active_d0_eq_1": True,
        "inputs_rehashed_unchanged_at_end": True,
    }
    write_new(arguments.output, canonical_json(result))
    print(
        json.dumps(
            {
                "output": str(arguments.output.resolve()),
                "output_sha256": sha256_file(arguments.output),
                "all_i8_sha256": checks["expansion_order_i8_sha256"],
                "gate_480_i8_sha256": checks["minimal_prefix_i8_sha256"],
                "gate_1024_i8_sha256": checks["first_batch_i8_sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as error:
        print(f"freeze_expansion_directions: {error}", file=sys.stderr)
        raise SystemExit(1)
