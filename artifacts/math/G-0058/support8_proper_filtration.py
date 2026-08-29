#!/usr/bin/env python3
"""Fail-fast exact audit of the proposed proper-core support-8 filtration.

The hypothesis under test says that every proper signed-mass-four orbit has
zero hinge coefficient on every primitive degree-four direction with exactly
eight nonzero coordinates.  The verifier scans the frozen stream in canonical
sequence order using the committed clean-room subset-state DP.  On the first
counterexample it stops, reproduces the entire compact hinge column by direct
factorial enumeration, and embeds it into the ambient eleven-coordinate row
universe with the exact unused-label multiplicity.

No-claim: refuting this filtration does not produce a lambda-nonzero circuit
or determine any restricted or full matrix rank.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
import io
from itertools import combinations, permutations
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
STREAM = ROOT / "artifacts/math/G-0038/loop_inclusive_signed_degree5_universe_v1.jsonl.gz"
G0052_SCRIPT = ROOT / "artifacts/math/G-0052/mass4_full_core_census.py"
G0052_REPORT = ROOT / "artifacts/math/G-0052/mass4_full_core_census_v1.json.gz"
G0054_SCRIPT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py"
G0054_REPORT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate_v1.json.gz"
G0055_PRICING_SCRIPT = ROOT / "artifacts/math/G-0055/proper_mass4_pricing_schedule.py"
G0055_PRICING_REPORT = ROOT / (
    "artifacts/math/G-0055/proper_mass4_pricing_schedule_v1.json.gz"
)
G0056_SCRIPT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift.py"
G0056_REPORT = ROOT / "artifacts/math/G-0056/exact_s0_kernel_lift_v1.json.gz"
CLEAN_SCRIPT = ROOT / (
    "artifacts/cleanroom/G-0051-mass4-preflight-audit/"
    "independent_mass4_preflight_audit.py"
)
DEFAULT_OUTPUT = HERE / "support8_proper_filtration_v1.json.gz"

EXPECTED_HASHES = {
    "g0038_stream": "e4cc44c602a8eb3e864e396b967b178f4c0d6f670a48c8c2f233ffac2606c5fd",
    "g0052_script": "435832fb62ca75981a11f3193f4546c0ca817ad7752a0636bbaeb8730cc23d51",
    "g0052_report": "23658ef43603cc775a2938789bd2792616a018b726d7272981c24186fd071b37",
    "g0054_script": "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2",
    "g0054_report": "c9a80de54a367cd78eac820cac83568508fa65afbc9a26f74c941495ff334053",
    "g0055_pricing_script": "5f78397925e0873b696dc9d4b6c0562b9af58a0198e74ca636049f932fbade17",
    "g0055_pricing_report": "f6e6c824cbebab126f7452bc922859f5b53fa54f1af91cfb71dfefca41ba5cdc",
    "g0056_script": "484d86ccc494019c802f3f793c8f40c4deda2e7e86913191888a2188fef527c7",
    "g0056_report": "131312761477dc3ae47167caa83aabdde1d7dc6da40b71e33c40c8b5401088d4",
    "clean_script": "76c67f4499228fd07b3cdea782bf6fe7b351fe333948062484aa8285c9cdc616",
}
EXPECTED_ACTIVE_HISTOGRAM = {
    2: 7,
    3: 259,
    4: 3_131,
    5: 14_491,
    6: 31_452,
    7: 37_350,
    8: 27_412,
    9: 13_617,
    10: 5_009,
    11: 1_465,
}
EXPECTED_COUNTEREXAMPLE_SEQUENCE = 92_489
EXPECTED_LOCAL_DIRECTION_COUNT = 21
EXPECTED_LOCAL_COEFFICIENT = 1_152
EXPECTED_AMBIENT_ROW_COUNT = 3_465
SCHEMA = "max11-g0058-support8-proper-filtration-refutation-v1"

Direction = tuple[int, ...]
Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]

CLEAN: ModuleType | None = None


class GateError(RuntimeError):
    """Fail-closed semantic or certificate mismatch."""


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_clean() -> ModuleType:
    if sha256_path(CLEAN_SCRIPT) != EXPECTED_HASHES["clean_script"]:
        raise GateError("clean-room semantic kernel hash drift")
    spec = importlib.util.spec_from_file_location("g0058_clean_semantics", CLEAN_SCRIPT)
    if spec is None or spec.loader is None:
        raise GateError("cannot load clean-room semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def compact_record(record: dict[str, object]) -> tuple[dict[str, object], int]:
    branches = [record.get("negative_edges"), record.get("positive_edges")]
    if not all(isinstance(branch, list) for branch in branches):
        raise GateError("record has malformed edge branches")
    typed = branches  # narrowed by the guard above
    used = sorted(
        {
            int(vertex)
            for branch in typed
            for edge in branch  # type: ignore[union-attr]
            for vertex in edge
        }
    )
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact = {
        "negative_edges": [
            [relabel[int(left)], relabel[int(right)]]
            for left, right in typed[0]  # type: ignore[union-attr]
        ],
        "positive_edges": [
            [relabel[int(left)], relabel[int(right)]]
            for left, right in typed[1]  # type: ignore[union-attr]
        ],
    }
    active = len(used)
    if active != int(record["active_vertices"]):
        raise GateError(f"active-vertex drift at sequence {record['sequence']}")
    return compact, active


def support8_payload(hinges: Counter[Direction]) -> list[list[object]]:
    return [
        [list(direction), int(coefficient)]
        for direction, coefficient in sorted(hinges.items())
        if coefficient and sum(value != 0 for value in direction) == 8
    ]


def initialize_worker() -> None:
    global CLEAN
    CLEAN = load_clean()


def filtration_worker(record: dict[str, object]) -> dict[str, object]:
    if CLEAN is None:
        raise GateError("clean-room worker was not initialized")
    compact, active = compact_record(record)
    hinges = CLEAN.independent_hinge_column(compact, n=active)
    payload = support8_payload(hinges)
    return {
        "sequence": int(record["sequence"]),
        "active_vertices": active,
        "support8_payload": payload,
        "complete_hinge_direction_count": sum(bool(value) for value in hinges.values()),
    }


def direct_permutation_hinges(record: dict[str, object], n: int) -> Counter[Direction]:
    """Independent n! replay without the subset-state DP."""
    branches: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    result: Counter[Direction] = Counter()
    for order in permutations(range(n)):
        position = [0] * n
        for rank, vertex in enumerate(order):
            position[vertex] = rank
        words = []
        for branch in branches:
            word = [0] * n
            for left, right in branch:
                word[max(position[left], position[right])] += 1
            words.append(tuple(word))
        base, other = sorted(words)
        if base == other:
            continue
        direction = tuple(right - left for left, right in zip(base, other, strict=True))
        prefixes = []
        prefix = 0
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        primitive = tuple(value // divisor for value in direction)
        result[primitive] += divisor
    return +result


def embed(direction: Direction, positions: tuple[int, ...], n: int = 11) -> Direction:
    result = [0] * n
    for local, ambient in enumerate(positions):
        result[ambient] = direction[local]
    return tuple(result)


def counterexample_controls(
    clean: ModuleType, compact: dict[str, object]
) -> tuple[Counter[Direction], dict[str, object]]:
    dp_hinges = +clean.independent_hinge_column(compact, n=8)
    brute_hinges = direct_permutation_hinges(compact, n=8)
    if dp_hinges != brute_hinges:
        raise GateError("counterexample subset DP differs from direct 8! replay")
    payload = support8_payload(dp_hinges)
    if len(dp_hinges) != EXPECTED_LOCAL_DIRECTION_COUNT or len(payload) != (
        EXPECTED_LOCAL_DIRECTION_COUNT
    ):
        raise GateError("counterexample local hinge census drift")
    if {int(item[1]) for item in payload} != {EXPECTED_LOCAL_COEFFICIENT}:
        raise GateError("counterexample coefficient drift")

    local_directions = [tuple(map(int, item[0])) for item in payload]
    for direction in local_directions:
        if (
            direction[0] != 1
            or Counter(direction) != Counter({1: 4, -1: 4})
            or min(
                sum(direction[:stop]) for stop in range(1, len(direction))
            ) >= 0
        ):
            raise GateError("support-8 direction fails balanced ambiguous-word control")

    canonical_balanced_words = []
    for positive_positions in combinations(range(1, 8), 3):
        word = [-1] * 8
        word[0] = 1
        for position in positive_positions:
            word[position] = 1
        canonical_balanced_words.append(tuple(word))
    nonnegative_words = [
        word
        for word in canonical_balanced_words
        if min(sum(word[:stop]) for stop in range(1, 8)) >= 0
    ]
    ambiguous_words = sorted(set(canonical_balanced_words) - set(nonnegative_words))
    if (
        len(canonical_balanced_words) != 35
        or len(nonnegative_words) != 14
        or ambiguous_words != sorted(local_directions)
    ):
        raise GateError("Catalan balanced-word decomposition drift")
    analytic_coefficient = 2 * factorial(4) * factorial(4)
    if analytic_coefficient != EXPECTED_LOCAL_COEFFICIENT:
        raise GateError("analytic local multiplicity drift")

    ambient_rows = sorted(
        embed(direction, positions)
        for positions in combinations(range(11), 8)
        for direction in local_directions
    )
    if len(ambient_rows) != EXPECTED_AMBIENT_ROW_COUNT or len(set(ambient_rows)) != (
        EXPECTED_AMBIENT_ROW_COUNT
    ):
        raise GateError("ambient support-8 embedding census drift")
    complete_support8 = sorted(
        direction
        for direction in clean.primitive_ambiguous_directions(4, 11)
        if sum(value != 0 for value in direction) == 8
    )
    if ambient_rows != complete_support8:
        raise GateError("embedded local directions do not equal the complete ambient H8 rows")
    ambient_coefficient = factorial(11 - 8) * EXPECTED_LOCAL_COEFFICIENT
    ambient_column = [[list(row), ambient_coefficient] for row in ambient_rows]

    mutant = {
        "negative_edges": compact["negative_edges"],
        "positive_edges": [
            [0, 0],
            [1, 1],
            [2, 2],
            [2, 2],
        ],
    }
    mutant_hinges = clean.independent_hinge_column(mutant, n=8)
    if support8_payload(mutant_hinges):
        raise GateError("overlapping-loop mutation did not destroy support-8 hinges")

    return dp_hinges, {
        "subset_state_DP_matches_direct_8_factorial_replay": True,
        "direct_permutations_replayed": factorial(8),
        "canonical_balanced_sign_words": 35,
        "nonnegative_Catalan_words_removed_as_linear": 14,
        "ambiguous_hinge_words": 21,
        "analytic_multiplicity_per_word": analytic_coefficient,
        "complete_ambient_support8_row_count": len(ambient_rows),
        "ambient_rows_sha256": canonical_sha256([list(row) for row in ambient_rows]),
        "ambient_unused_label_multiplicity": factorial(11 - 8),
        "ambient_coefficient_on_every_support8_row": ambient_coefficient,
        "ambient_column_sha256": canonical_sha256(ambient_column),
        "ambient_column_total_weight": ambient_coefficient * len(ambient_rows),
        "overlapping_loop_mutant_has_no_support8_hinge": True,
    }


def read_mass4_stream() -> tuple[dict[str, object], list[dict[str, object]], list[tuple[int, int]], Counter[int]]:
    high_proper: list[dict[str, object]] = []
    proper_sequence_active: list[tuple[int, int]] = []
    active_histogram: Counter[int] = Counter()
    previous_sequence = -1
    with gzip.open(STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise GateError("G-0038 stream is missing its header")
        for line in source:
            record = json.loads(line)
            mass = int(record["signed_mass"])
            if mass < 4:
                continue
            if mass > 4:
                break
            sequence = int(record["sequence"])
            if sequence <= previous_sequence:
                raise GateError("mass-four stream is not in canonical sequence order")
            previous_sequence = sequence
            active = int(record["active_vertices"])
            active_histogram[active] += 1
            if active < 11:
                proper_sequence_active.append((sequence, active))
                if active >= 8:
                    high_proper.append(record)
    if dict(active_histogram) != EXPECTED_ACTIVE_HISTOGRAM:
        raise GateError(f"mass-four active census drift: {dict(active_histogram)}")
    if len(proper_sequence_active) != 132_728 or len(high_proper) != 46_038:
        raise GateError("proper/high-active census drift")
    return header, high_proper, proper_sequence_active, active_histogram


def run(workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    paths = {
        "g0038_stream": STREAM,
        "g0052_script": G0052_SCRIPT,
        "g0052_report": G0052_REPORT,
        "g0054_script": G0054_SCRIPT,
        "g0054_report": G0054_REPORT,
        "g0055_pricing_script": G0055_PRICING_SCRIPT,
        "g0055_pricing_report": G0055_PRICING_REPORT,
        "g0056_script": G0056_SCRIPT,
        "g0056_report": G0056_REPORT,
        "clean_script": CLEAN_SCRIPT,
    }
    observed_hashes = {name: sha256_path(path) for name, path in paths.items()}
    if observed_hashes != EXPECTED_HASHES:
        raise GateError(f"input binding drift: {observed_hashes}")
    _header, high_proper, proper_sequence_active, active_histogram = read_mass4_stream()

    first: dict[str, object] | None = None
    checked_high = 0
    context = mp.get_context("fork")
    pool = context.Pool(
        processes=workers,
        initializer=initialize_worker,
        maxtasksperchild=128,
    )
    terminated = False
    try:
        for checked_high, result in enumerate(
            pool.imap(filtration_worker, high_proper, chunksize=1), start=1
        ):
            if result["support8_payload"]:
                first = result
                pool.terminate()
                terminated = True
                break
            if checked_high % 500 == 0:
                print(
                    f"G0058_FILTER high_proper={checked_high}/{len(high_proper)}",
                    file=sys.stderr,
                    flush=True,
                )
    finally:
        if not terminated:
            pool.close()
        pool.join()
    if first is None:
        raise GateError("hypothesis unexpectedly survived the complete high-active scan")
    first_sequence = int(first["sequence"])
    if first_sequence != EXPECTED_COUNTEREXAMPLE_SEQUENCE:
        raise GateError(f"lex-first counterexample drift: {first_sequence}")
    record = next(
        candidate
        for candidate in high_proper
        if int(candidate["sequence"]) == first_sequence
    )
    compact, active = compact_record(record)
    if active != 8:
        raise GateError("counterexample active support drift")
    clean = load_clean()
    hinges, controls = counterexample_controls(clean, compact)
    payload = support8_payload(hinges)
    if payload != first["support8_payload"]:
        raise GateError("parent/worker counterexample payload mismatch")

    with gzip.open(G0055_PRICING_REPORT, "rt", encoding="utf-8") as source:
        pricing_report = json.load(source)
    priced_counterexample = [
        item
        for item in pricing_report["exact_first_block_pricing"]["per_record"]
        if int(item["sequence"]) == first_sequence
    ]
    if len(priced_counterexample) != 1 or int(
        priced_counterexample[0]["pairing_numerator"]
    ) != 0:
        raise GateError("G-0055 counterexample price binding drift")

    prior = [item for item in proper_sequence_active if item[0] < first_sequence]
    prior_dimension_excluded = sum(active_value < 8 for _sequence, active_value in prior)
    prior_DP_checked = sum(active_value >= 8 for _sequence, active_value in prior)
    if prior_DP_checked != checked_high - 1:
        raise GateError("lex-first prefix accounting mismatch")

    descriptor = {
        "sequence": first_sequence,
        "signed_mass": int(record["signed_mass"]),
        "active_vertices": active,
        "negative_edges": record["negative_edges"],
        "positive_edges": record["positive_edges"],
        "negative_loop_count": int(record["negative_loop_count"]),
        "positive_loop_count": int(record["positive_loop_count"]),
        "abs_beta": int(record["abs_beta"]),
        "abs_components": int(record["abs_components"]),
    }
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "REFUTED_LEX_FIRST_PROPER_SUPPORT8_COUNTEREXAMPLE_SEQUENCE_92489",
        "bindings": observed_hashes,
        "stream_census": {
            "mass4_records": sum(active_histogram.values()),
            "proper_mass4_records": len(proper_sequence_active),
            "full_mass4_records": active_histogram[11],
            "proper_active8_through_10_records": len(high_proper),
            "active_vertex_histogram": {
                str(key): value for key, value in sorted(active_histogram.items())
            },
        },
        "lex_first_proof": {
            "canonical_stream_order_verified": True,
            "prior_proper_record_count": len(prior),
            "prior_active_at_most_7_excluded_by_dimension": prior_dimension_excluded,
            "prior_active_at_least_8_checked_by_cleanroom_DP": prior_DP_checked,
            "first_counterexample_sequence": first_sequence,
        },
        "counterexample": {
            "descriptor": descriptor,
            "descriptor_sha256": canonical_sha256(descriptor),
            "complete_local_hinge_direction_count": len(hinges),
            "support8_direction_count": len(payload),
            "support8_coefficient_histogram": {
                str(key): value
                for key, value in sorted(Counter(int(item[1]) for item in payload).items())
            },
            "support8_payload": payload,
            "support8_payload_sha256": canonical_sha256(payload),
        },
        "controls": controls,
        "g0055_discriminator_blind_spot": {
            "counterexample_is_in_frozen_first_block_pricing": True,
            "g0053_dual_pairing_numerator": 0,
            "support8_ambient_column_is_nonzero": True,
            "interpretation": (
                "The old one-coordinate G-0053 dual price does not detect this "
                "support-eight column; zero price was correctly not claimed to imply irrelevance."
            ),
        },
        "conclusion": (
            "The proposed identity is false: a proper active-eight mass-four orbit has "
            "coefficient 6912 on every one of the 3465 ambient support-eight rows."
        ),
        "claim_boundary": (
            "This exact counterexample refutes only the proposed proper-core support-8 "
            "vanishing filtration. It does not determine rank(H8), produce a lambda-nonzero "
            "circuit, prove a mass-at-most-four construction, or decide unrestricted MAX11."
        ),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "workers": workers,
        },
        "wall_seconds": time.perf_counter() - started,
        "script_sha256": script_hash_before,
    }
    report["canonical_payload_sha256"] = canonical_sha256(report)
    if sha256_path(Path(__file__)) != script_hash_before:
        raise GateError("script changed during execution")
    return report


def write_gzip_atomic(path: Path, value: object, replace: bool) -> None:
    resolved = path.resolve()
    try:
        resolved.relative_to(ROOT.resolve())
    except ValueError as error:
        raise GateError("output must remain inside project") from error
    if resolved.exists() and not replace:
        raise FileExistsError(f"refusing to overwrite {resolved}; pass --replace")
    temporary = resolved.with_name(resolved.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    resolved.parent.mkdir(parents=True, exist_ok=True)
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(compressed, encoding="ascii") as target:
                target.write(canonical_bytes(value).decode("ascii"))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(resolved)


def main(argv: Sequence[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args(argv)
    if args.workers < 1:
        raise SystemExit("workers must be positive")
    if args.self_test:
        clean = load_clean()
        planted = {
            "negative_edges": [[4, 4], [5, 5], [6, 6], [7, 7]],
            "positive_edges": [[0, 0], [1, 1], [2, 2], [3, 3]],
        }
        _hinges, controls = counterexample_controls(clean, planted)
        print(json.dumps({"result": "PASS", "controls": controls}, sort_keys=True))
        return
    report = run(args.workers)
    write_gzip_atomic(args.output, report, args.replace)
    print(json.dumps({"result": report["result"], "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
