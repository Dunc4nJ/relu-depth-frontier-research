#!/usr/bin/env python3
"""Search the only low-signed-mass MAX11 seeds that escape proper support.

The Nth binary finite-difference invariant annihilates every fully
symmetrised atom using fewer than N active labels.  In the complete G-0038
signed-mass <=3 prefix, only sequences 3308, 3309, and 3310 use all 11
labels.  This program asks whether a nonzero combination of those three seed
hinge columns can be cancelled by the other 3,307 low-mass columns.

The rank calculation is modular discovery on a deterministic row prefix.  A
negative modular result is not promoted to a rational theorem; a positive
relation is only a candidate until exact-Q lifting and complete-row replay.
"""

from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import importlib.util
from itertools import combinations, combinations_with_replacement
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from typing import Any, Iterator

from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0047_SCRIPT = HERE / "induction_span_obstruction.py"
G0047_REPORT = HERE / "induction_span_obstruction_v1.json.gz"
EXPECTED_G0047_SCRIPT_HASH = (
    "0906a834e4f4ee7635a25b8a5c4ab17bfd1ca34d65004e17a64d4eaccdd1ad2d"
)
EXPECTED_G0047_REPORT_HASH = (
    "47f02e125c4010e50d943c31ef4278f9d8679b0e54d26d86ea5414ac12ebf83a"
)
PRIMES = (1_000_003, 1_000_033)
SEED_SEQUENCES = (3308, 3309, 3310)
EXPECTED_RECORDS = 3_310
EXPECTED_PROPER = 3_307
EXPECTED_DIRECTIONS = 10_065
DEFAULT_ROWS = 5_000
DEFAULT_OUTPUT = HERE / "low_mass_circuit_search_v1.json.gz"
SCHEMA = "max11-g0047-low-mass-circuit-search-v1"

Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]
Direction = tuple[int, ...]

G47: Any = None
SELECTED_INDEX: dict[Direction, int] = {}


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def load_g47() -> Any:
    if sha256_path(G0047_SCRIPT) != EXPECTED_G0047_SCRIPT_HASH:
        raise ValueError("G-0047 theorem script hash drift")
    if sha256_path(G0047_REPORT) != EXPECTED_G0047_REPORT_HASH:
        raise ValueError("G-0047 theorem report hash drift")
    spec = importlib.util.spec_from_file_location("g0047_induction_obstruction", G0047_SCRIPT)
    if spec is None or spec.loader is None:
        raise ImportError("cannot import frozen G-0047 theorem script")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def weak_compositions(total: int, parts: int, prefix: Direction = ()) -> Iterator[Direction]:
    if parts == 1:
        yield prefix + (total,)
        return
    for first in range(total + 1):
        yield from weak_compositions(total - first, parts - 1, prefix + (first,))


def direction_universe(n: int = 11, degree: int = 3) -> tuple[Direction, ...]:
    compositions = tuple(weak_compositions(degree, n))
    directions: set[Direction] = set()
    for left, right in combinations_with_replacement(compositions, 2):
        if left == right:
            continue
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = 0
        for value in direction:
            divisor = gcd(divisor, abs(value))
        directions.add(tuple(value // divisor for value in direction))
    result = tuple(sorted(directions))
    if (n, degree) == (11, 3) and len(result) != EXPECTED_DIRECTIONS:
        raise AssertionError(f"degree-three direction census {len(result)}")
    return result


def load_records(module: Any) -> list[dict[str, object]]:
    if sha256_path(module.SIGNED_STREAM) != module.EXPECTED_SIGNED_STREAM_HASH:
        raise ValueError("G-0038 stream drift")
    records = []
    with gzip.open(module.SIGNED_STREAM, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        if header.get("record_type") != "header":
            raise ValueError("missing G-0038 header")
        for line in source:
            record = json.loads(line)
            signed_mass = int(record["signed_mass"])
            if signed_mass > 3:
                break
            if signed_mass:
                records.append(record)
    if len(records) != EXPECTED_RECORDS:
        raise AssertionError("low-mass record census mismatch")
    if tuple(int(record["sequence"]) for record in records[-3:]) != SEED_SEQUENCES:
        raise AssertionError("full-support seed positions drifted")
    if any(int(record["active_vertices"]) != 11 for record in records[-3:]):
        raise AssertionError("seed active-support census drifted")
    if any(int(record["active_vertices"]) >= 11 for record in records[:-3]):
        raise AssertionError("proper-support denominator contains another full-support record")
    return records


def compact_pair(record: dict[str, object]) -> tuple[Pair, int]:
    pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    used = sorted({vertex for branch in pair for edge in branch for vertex in edge})
    relabel = {vertex: index for index, vertex in enumerate(used)}
    compact: Pair = tuple(
        tuple((relabel[u], relabel[v]) for u, v in branch) for branch in pair
    )  # type: ignore[assignment]
    return compact, len(used)


def init_worker(selected_index: dict[Direction, int]) -> None:
    global G47, SELECTED_INDEX
    G47 = load_g47()
    SELECTED_INDEX = selected_index


def column_worker(record: dict[str, object]) -> tuple[int, int, list[tuple[int, int]], int]:
    pair, active = compact_pair(record)
    _linear, local_hinges = G47.primitive_normal_form(
        G47.permutation_t_counter_dp(pair, active), active
    )
    multiplier = factorial(11 - active)
    selected: dict[int, int] = {}
    for positions in combinations(range(11), active):
        for local_direction, weight in local_hinges.items():
            embedded = [0] * 11
            for index, value in enumerate(local_direction):
                embedded[positions[index]] = value
            row = SELECTED_INDEX.get(tuple(embedded))
            if row is not None:
                selected[row] = selected.get(row, 0) + multiplier * weight
    full_pair: Pair = (
        tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
        tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
    )
    binary_vector = G47.binary_chamber_vector_from_full_symmetry(full_pair, 11)
    invariant = G47.dot(G47.alternating_invariant(11), binary_vector)
    return int(record["sequence"]), active, sorted(selected.items()), invariant


def modular_rank(matrix: np.ndarray, prime: int) -> int:
    reduced = np.remainder(matrix, prime).astype(np.int64, copy=False)
    flat = reduced.ravel(order="C").tolist()
    value = nmod_mat(matrix.shape[0], matrix.shape[1], flat, prime)
    del flat, reduced
    return int(value.rank())


def self_test() -> dict[str, object]:
    module = load_g47()
    if module.self_test().get("result") != "PASS":
        raise AssertionError("frozen G-0047 self-test failed")
    universe = direction_universe(5, 3)
    if not universe:
        raise AssertionError("small direction universe empty")
    # A proper-support MAX3 path has zero fifth binary difference.
    pair: Pair = (((0, 1),), ((0, 2),))
    vector = module.binary_chamber_vector_from_full_symmetry(pair, 5)
    if module.dot(module.alternating_invariant(5), vector):
        raise AssertionError("proper-support finite-difference control failed")
    return {
        "result": "PASS",
        "frozen_G0047_self_test": True,
        "small_direction_universe_nonempty": True,
        "proper_support_binary_difference_zero": True,
    }


def run(rows: int, workers: int) -> dict[str, object]:
    started = time.perf_counter()
    script_hash_before = sha256_path(Path(__file__))
    controls = self_test()
    module = load_g47()
    records = load_records(module)
    universe = direction_universe()

    # The three seed supports are mandatory rows; the remainder is the
    # lexicographically first complement, so row growth is nested and replayable.
    seed_directions: set[Direction] = set()
    seed_invariants = []
    for record in records[-3:]:
        pair, active = compact_pair(record)
        if active != 11:
            raise AssertionError("non-full seed")
        _linear, hinges = module.primitive_normal_form(
            module.permutation_t_counter_dp(pair, active), active
        )
        seed_directions.update(hinges)
        full_pair: Pair = (
            tuple(tuple(map(int, edge)) for edge in record["negative_edges"]),
            tuple(tuple(map(int, edge)) for edge in record["positive_edges"]),
        )
        vector = module.binary_chamber_vector_from_full_symmetry(full_pair, 11)
        seed_invariants.append(
            module.dot(module.alternating_invariant(11), vector)
        )
    if seed_invariants != [239_500_800] * 3 or len(seed_directions) != 1_485:
        raise AssertionError("seed invariant/support control drift")
    if not (len(seed_directions) <= rows <= len(universe)):
        raise ValueError(f"--rows must lie in [{len(seed_directions)},{len(universe)}]")
    complement = [direction for direction in universe if direction not in seed_directions]
    selected = tuple(sorted(seed_directions)) + tuple(
        complement[: rows - len(seed_directions)]
    )
    if len(selected) != rows or len(set(selected)) != rows:
        raise AssertionError("selected row census mismatch")
    selected_index = {direction: index for index, direction in enumerate(selected)}

    matrix = np.zeros((rows, len(records)), dtype=np.int64)
    active_histogram: Counter[int] = Counter()
    invariant_histogram: Counter[int] = Counter()
    context = mp.get_context("fork")
    completed = 0
    with context.Pool(
        processes=workers,
        initializer=init_worker,
        initargs=(selected_index,),
        maxtasksperchild=64,
    ) as pool:
        for sequence, active, sparse, invariant in pool.imap_unordered(
            column_worker, records, chunksize=1
        ):
            column = sequence - 1
            for row, value in sparse:
                matrix[row, column] = value
            active_histogram[active] += 1
            invariant_histogram[invariant] += 1
            completed += 1
            if completed % 250 == 0 or completed == len(records):
                print(
                    f"G0047_LOW_MASS columns={completed}/{len(records)}",
                    file=sys.stderr,
                    flush=True,
                )
    if completed != len(records):
        raise AssertionError("column generation incomplete")
    if invariant_histogram[239_500_800] != 3 or sum(
        count for value, count in invariant_histogram.items() if value
    ) != 3:
        raise AssertionError("proper-support invariant did not vanish exactly")
    if any(np.count_nonzero(matrix[:, sequence - 1]) == 0 for sequence in SEED_SEQUENCES):
        raise AssertionError("selected rows missed a seed")

    prime_results = []
    for prime in PRIMES:
        begun = time.perf_counter()
        proper_rank = modular_rank(matrix[:, :EXPECTED_PROPER], prime)
        full_rank = modular_rank(matrix, prime)
        gain = full_rank - proper_rank
        if not (0 <= gain <= 3):
            raise AssertionError("seed quotient rank out of range")
        prime_results.append(
            {
                "prime": prime,
                "proper_rank": proper_rank,
                "rank_with_three_full_support_seeds": full_rank,
                "seed_quotient_rank_gain": gain,
                "seconds": time.perf_counter() - begun,
            }
        )
    gains = [record["seed_quotient_rank_gain"] for record in prime_results]
    if gains == [3, 3]:
        result = "THREE_SEEDS_INDEPENDENT_MOD_PROPER_ON_SELECTED_ROWS"
        interpretation = (
            "No nonzero seed combination can be cancelled by proper-support low-mass columns "
            "over either tested field on this row system. This modular result is a powerful "
            "falsifier but is not by itself an exact-Q theorem."
        )
    else:
        result = "LOW_MASS_SEED_QUOTIENT_DEPENDENCY_REQUIRES_LIFT"
        interpretation = (
            "At least one modular seed combination lies in the proper-support span on selected "
            "rows. Extract coefficients, replay all 10,065 hinge rows, then lift over Q."
        )

    script_hash_after = sha256_path(Path(__file__))
    if script_hash_after != script_hash_before:
        raise RuntimeError("script changed during execution")
    report = {
        "schema": SCHEMA,
        "result": result,
        "interpretation": interpretation,
        "script_sha256": script_hash_before,
        "bindings": {
            "g0047_script_sha256": EXPECTED_G0047_SCRIPT_HASH,
            "g0047_report_sha256": EXPECTED_G0047_REPORT_HASH,
            "g0038_stream_sha256": module.EXPECTED_SIGNED_STREAM_HASH,
        },
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "workers": workers,
        },
        "self_test": controls,
        "denominator": {
            "signed_masses": [1, 2, 3],
            "columns": len(records),
            "proper_support_columns": EXPECTED_PROPER,
            "full_support_seed_sequences": list(SEED_SEQUENCES),
            "active_vertex_histogram": {
                str(key): value for key, value in sorted(active_histogram.items())
            },
            "binary_finite_difference_histogram": {
                str(key): value for key, value in sorted(invariant_histogram.items())
            },
        },
        "rows": {
            "complete_degree_three_primitive_hinge_universe": len(universe),
            "seed_support_union": len(seed_directions),
            "selected": rows,
            "selection": (
                "all 1,485 seed-support directions followed by the lexicographically first "
                "complement directions"
            ),
            "selected_directions_sha256": hashlib.sha256(
                canonical_bytes([list(direction) for direction in selected])
            ).hexdigest(),
        },
        "modular_results": prime_results,
        "sharp_retry_predicate": (
            "If seed quotient gain is below three at both primes, extract the shared modular "
            "dependency. If gain is three, extend to exact-Q rank on this same selected system "
            "before promoting the mechanism as killed."
        ),
        "no_claim": (
            "This is modular discovery on a deterministic subset of the complete degree-three "
            "hinge universe. It proves neither a rational construction nor a rational/global "
            "obstruction until the stated exact-Q/full-row replay is performed."
        ),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_payload_sha256"] = hashlib.sha256(canonical_bytes(report)).hexdigest()
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output: {temporary}")
    with temporary.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(canonical_bytes(value))
        raw.flush()
        os.fsync(raw.fileno())
    temporary.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), indent=2, sort_keys=True))
        return
    if args.workers < 1:
        raise SystemExit("--workers must be positive")
    output = args.output.resolve()
    try:
        output.relative_to(ROOT.resolve())
    except ValueError as error:
        raise SystemExit("output must remain inside the project") from error
    report = run(args.rows, args.workers)
    write_gzip_atomic(output, report)
    print(json.dumps({"result": report["result"], "output": str(output)}, sort_keys=True))


if __name__ == "__main__":
    main()
