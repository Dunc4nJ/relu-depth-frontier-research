#!/usr/bin/env python3
"""Independent exact and global review of the pinned G-0118 iteration-2 candidate.

The iteration-2 solver is hashed but never imported or executed.  Finite-row
arithmetic uses Python integers over independently assembled frozen columns.
The complete modular normal form uses the sibling clean-room C++ subset-DP.
Any first nonzero hinge coordinate is then recomputed with a separate targeted
Python injection DP over arbitrary-precision integers.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
import os
import re
import struct
import subprocess
import tempfile
from functools import reduce
from math import gcd
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent
CANDIDATE = ROOT / "artifacts/math/G-0118/prefix_exact_cegis_iteration2_v1.json"
PANEL_INPUT = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
RETAINED = ROOT / "artifacts/math/G-0113/panel_retained_columns_v1.json"
PANEL_SCAN = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
COORDINATE_1 = ROOT / "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json"
COORDINATE_2 = ROOT / "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json"
CACHE = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"
PREREGISTRATION = ROOT / "artifacts/math/G-0118/ITERATION2_PREFIX_PREREGISTRATION.md"
PRODUCER = ROOT / "artifacts/math/G-0118/prefix_exact_cegis_iteration2.py"
GLOBAL_SOURCE = REVIEW / "cleanroom_global_replay.cpp"

EXPECTED_CANDIDATE_SHA256 = (
    "1d3fd50449fd63c0f8d795cb4d1428fd7a89ef97bcd709c01c579115ea8ccb4b"
)
PANEL_ROWS = 301
LINEAR_ROWS = 11
HINGE_ROWS = 2
ROWS = PANEL_ROWS + LINEAR_ROWS + HINGE_ROWS
PREFIX_RECORDS = 40_000
PANEL_RECORD_BYTES = PANEL_ROWS * 16
PREFIX_BYTES = PREFIX_RECORDS * PANEL_RECORD_BYTES
PRIMES = (1_000_000_007, 1_000_000_009)
INTEGER_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
DIRECTION_1 = (0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4)
DIRECTION_2 = (0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3)


class ReviewError(RuntimeError):
    """Fail-closed review error."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ReviewError(message)


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def sha256_prefix(path: Path, length: int) -> str:
    digest = hashlib.sha256()
    remaining = length
    with path.open("rb") as stream:
        while remaining:
            block = stream.read(min(1 << 20, remaining))
            require(bool(block), f"short file while hashing prefix of {path}")
            digest.update(block)
            remaining -= len(block)
    return digest.hexdigest()


def canonical_json_sha256(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(payload).hexdigest()


def digest_i64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(-(1 << 63) <= value < (1 << 63), "value does not fit signed i64")
        digest.update(struct.pack("<q", value))
    return digest.hexdigest()


def digest_i128(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(-(1 << 127) <= value < (1 << 127), "value does not fit signed i128")
        digest.update(value.to_bytes(16, "little", signed=True))
    return digest.hexdigest()


def cache_block(cache_stream: Any, sequence: int) -> bytes:
    cache_stream.seek(sequence * PANEL_RECORD_BYTES)
    block = cache_stream.read(PANEL_RECORD_BYTES)
    require(len(block) == PANEL_RECORD_BYTES, f"short cache record {sequence}")
    return block


def decode_panel_block(block: bytes) -> list[int]:
    return [
        int.from_bytes(block[offset : offset + 16], "little", signed=True)
        for offset in range(0, len(block), 16)
    ]


def vector_i128_bytes(values: Iterable[int]) -> bytes:
    return b"".join(int(value).to_bytes(16, "little", signed=True) for value in values)


def actual_candidate_bindings(candidate: dict[str, Any]) -> dict[str, str]:
    bindings: dict[str, str] = {}
    for relative in candidate["bindings"]:
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as error:
            raise ReviewError(f"binding escapes repository: {relative}") from error
        require(path.is_file() and not path.is_symlink(), f"binding is not a regular file: {relative}")
        bindings[relative] = sha256_path(path)
    return bindings


def parse_integer(raw: Any, label: str, *, positive: bool = False) -> int:
    require(
        isinstance(raw, str) and INTEGER_RE.fullmatch(raw) is not None,
        f"{label} is not a canonical decimal integer",
    )
    value = int(raw)
    if positive:
        require(value > 0, f"{label} is not positive")
    return value


def verify_coordinate(
    coordinate: dict[str, Any],
    direction: tuple[int, ...],
    record_count: int,
    label: str,
) -> tuple[list[list[int]], list[int], dict[str, Any]]:
    require(coordinate.get("schema") == "max11-g0117-coordinate-price-v1", f"{label} schema drift")
    require(coordinate.get("records") == record_count, f"{label} record census drift")
    require(tuple(coordinate.get("direction", [])) == direction, f"{label} direction drift")
    linear = coordinate.get("linear_vectors")
    hinges = coordinate.get("hinge_coefficients")
    require(isinstance(linear, list) and len(linear) == record_count, f"{label} linear census drift")
    require(isinstance(hinges, list) and len(hinges) == record_count, f"{label} hinge census drift")
    require(all(len(vector) == LINEAR_ROWS for vector in linear), f"{label} linear width drift")
    linear_digest = digest_i64(value for vector in linear for value in vector)
    hinge_digest = digest_i64(hinges)
    require(
        linear_digest == coordinate.get("linear_vectors_i64_le_sha256"),
        f"{label} linear stream digest drift",
    )
    require(
        hinge_digest == coordinate.get("hinge_coefficients_i64_le_sha256"),
        f"{label} hinge stream digest drift",
    )
    return linear, hinges, {
        "records": record_count,
        "direction": list(direction),
        "linear_vectors_i64_le_sha256": linear_digest,
        "hinge_coefficients_i64_le_sha256": hinge_digest,
        "nonzero_hinge_coefficients": sum(value != 0 for value in hinges),
        "maximum_hinge_coefficient": max(hinges),
    }


def signed_weights(record: dict[str, Any], n: int = 11) -> list[list[int]]:
    weights = [[0] * n for _ in range(n)]
    signed_mass = record["signed_mass"]
    require(
        len(record["negative_edges"]) == len(record["positive_edges"]) == signed_mass,
        f"edge/signed-mass mismatch at sequence {record['sequence']}",
    )
    for sign, key in ((-1, "negative_edges"), (1, "positive_edges")):
        for edge in record[key]:
            require(
                isinstance(edge, list)
                and len(edge) == 2
                and all(isinstance(vertex, int) and 0 <= vertex < n for vertex in edge),
                f"malformed edge at sequence {record['sequence']}",
            )
            u, v = edge
            require(u != v, f"selected G-0118 atom has a loop at sequence {record['sequence']}")
            weights[u][v] += sign
            weights[v][u] += sign
    active = sum(any(value != 0 for value in row) for row in weights)
    require(active == record["active_vertices"], f"active-vertex mismatch at sequence {record['sequence']}")
    require(all(abs(value) <= 5 for row in weights for value in row), "signed multiplicity exceeds five")
    return weights


def direction_is_canonical_active(direction: Sequence[int]) -> bool:
    if len(direction) < 2 or sum(direction) != 0:
        return False
    nonzero = [value for value in direction if value]
    if not nonzero or nonzero[0] <= 0:
        return False
    if reduce(gcd, (abs(value) for value in nonzero)) != 1:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return True
    return False


def coordinate_price(
    record: dict[str, Any],
    direction: Sequence[int],
    *,
    n: int = 11,
    maximum_scale: int = 5,
) -> int:
    """Exact hinge price from active-vertex rank injections.

    Inactive vertices are indistinguishable inside the DP; their labelled
    multiplicity is restored by `(n-k)!`, exactly as in the frozen formula.
    """

    require(direction_is_canonical_active(direction), "coordinate direction is not canonical active")
    weights = signed_weights(record, n)
    active_vertices = [vertex for vertex in range(n) if any(weights[vertex])]
    k = len(active_vertices)
    inactive = n - k
    full = (1 << k) - 1

    increments = [[0] * k for _ in range(1 << k)]
    for mask in range(1 << k):
        for local_vertex, vertex in enumerate(active_vertices):
            increments[mask][local_vertex] = sum(
                weights[vertex][active_vertices[other]]
                for other in range(k)
                if mask & (1 << other)
            )

    def injection_count(target: Sequence[int]) -> int:
        states: dict[int, int] = {0: 1}
        for rank in range(n):
            next_states: dict[int, int] = {}
            for mask, count in states.items():
                skipped = rank - mask.bit_count()
                if target[rank] == 0 and skipped < inactive:
                    next_states[mask] = next_states.get(mask, 0) + count
                for local_vertex in range(k):
                    bit = 1 << local_vertex
                    if mask & bit or increments[mask][local_vertex] != target[rank]:
                        continue
                    next_mask = mask | bit
                    next_states[next_mask] = next_states.get(next_mask, 0) + count
            states = next_states
            if not states:
                return 0
        return states.get(full, 0)

    price = 0
    for scale in range(-maximum_scale, maximum_scale + 1):
        if scale == 0:
            continue
        raw_word = [scale * value for value in direction]
        if any(abs(value) > 5 for value in raw_word):
            continue
        price += abs(scale) * injection_count(raw_word)
    return math.factorial(inactive) * price


def independent_linear_vector(
    record: dict[str, Any],
    *,
    n: int = 11,
    branch_edges: int = 5,
) -> list[int]:
    """Exact full-permutation linear correction without a direction histogram."""

    weights = signed_weights(record, n)
    state_count = 1 << n
    # state 0 = no nonzero raw entry yet; 1 = first-positive; 2 = first-negative.
    counts = [[0, 0, 0] for _ in range(state_count)]
    sums = [[[0] * n for _ in range(3)] for _ in range(state_count)]
    counts[0][0] = 1

    increments = [[0] * n for _ in range(state_count)]
    for mask in range(state_count):
        for vertex in range(n):
            increments[mask][vertex] = sum(
                weights[vertex][other]
                for other in range(n)
                if mask & (1 << other)
            )

    for mask in range(state_count - 1):
        rank = mask.bit_count()
        for sign_state in range(3):
            count = counts[mask][sign_state]
            if count == 0:
                continue
            source_sums = sums[mask][sign_state]
            for vertex in range(n):
                bit = 1 << vertex
                if mask & bit:
                    continue
                increment = increments[mask][vertex]
                next_sign = sign_state
                if sign_state == 0 and increment != 0:
                    next_sign = 1 if increment > 0 else 2
                next_mask = mask | bit
                counts[next_mask][next_sign] += count
                destination = sums[next_mask][next_sign]
                for coordinate in range(rank):
                    destination[coordinate] += source_sums[coordinate]
                destination[rank] += count * increment

    full = state_count - 1
    require(sum(counts[full]) == math.factorial(n), "linear DP does not reconcile to n!")
    correction = sums[full][2]
    if branch_edges == 0:
        return correction
    require(n >= 2, "base-linear formula requires n>=2")
    base_factor = 2 * branch_edges * math.factorial(n - 2)
    return [correction[rank] + base_factor * rank for rank in range(n)]


def brute_raw_histogram(record: dict[str, Any], n: int) -> dict[tuple[int, ...], int]:
    weights = signed_weights(record, n)
    histogram: dict[tuple[int, ...], int] = {}
    for order in itertools.permutations(range(n)):
        placed: list[int] = []
        word: list[int] = []
        for vertex in order:
            word.append(sum(weights[vertex][other] for other in placed))
            placed.append(vertex)
        key = tuple(word)
        histogram[key] = histogram.get(key, 0) + 1
    return histogram


def normalize_histogram(
    histogram: dict[tuple[int, ...], int], n: int
) -> tuple[dict[tuple[int, ...], int], list[int]]:
    hinges: dict[tuple[int, ...], int] = {}
    correction = [0] * n
    for word, count in histogram.items():
        first = next((value for value in word if value), 0)
        if first == 0:
            continue
        scale = reduce(gcd, (abs(value) for value in word))
        negative = first < 0
        direction = tuple(((-value if negative else value) // scale) for value in word)
        prefix = 0
        active = False
        for value in direction[:-1]:
            prefix += value
            active = active or prefix < 0
        if negative:
            for index, value in enumerate(word):
                correction[index] += count * value
        if active:
            hinges[direction] = hinges.get(direction, 0) + count * scale
    return hinges, correction


def python_self_test() -> dict[str, Any]:
    record = {
        "sequence": 0,
        "signed_mass": 2,
        "active_vertices": 5,
        "negative_edges": [[0, 1], [1, 2]],
        "positive_edges": [[0, 2], [3, 4]],
    }
    histogram = brute_raw_histogram(record, 5)
    hinges, correction = normalize_histogram(histogram, 5)
    require(sum(histogram.values()) == math.factorial(5), "literal Python census drift")
    require(
        independent_linear_vector(record, n=5, branch_edges=0) == correction,
        "targeted linear DP disagrees with literal permutations",
    )
    for direction, expected in hinges.items():
        require(
            coordinate_price(record, direction, n=5, maximum_scale=2) == expected,
            f"targeted hinge DP disagrees at {direction}",
        )
    mutant = copy.deepcopy(record)
    mutant["positive_edges"][0] = [0, 3]
    mutant_histogram = brute_raw_histogram(mutant, 5)
    require(mutant_histogram != histogram, "Python edge mutant escaped literal semantics")
    return {
        "result": "PASS",
        "literal_permutations": math.factorial(5),
        "raw_words": len(histogram),
        "active_hinges": len(hinges),
        "linear_dp_matches_literal": True,
        "hinge_coordinate_dp_matches_literal": True,
        "edge_mutant_rejected": True,
    }


def compile_global_replayer() -> tuple[Path, dict[str, Any]]:
    source_sha = sha256_path(GLOBAL_SOURCE)
    binary = Path(tempfile.gettempdir()) / f"g0118-iteration2-global-{source_sha[:16]}"
    temporary = binary.with_name(f"{binary.name}.{os.getpid()}.tmp")
    command = [
        "g++",
        "-std=c++20",
        "-O3",
        "-DNDEBUG",
        "-Wall",
        "-Wextra",
        "-Werror",
        str(GLOBAL_SOURCE),
        "-o",
        str(temporary),
    ]
    try:
        subprocess.run(command, check=True)
        os.replace(temporary, binary)
    finally:
        if temporary.exists():
            temporary.unlink()
    compiler = subprocess.run(
        ["g++", "--version"], check=True, text=True, stdout=subprocess.PIPE
    ).stdout.splitlines()[0]
    return binary, {
        "source_sha256": source_sha,
        "binary_sha256": sha256_path(binary),
        "compiler": compiler,
        "compile_command": command[:-1] + ["/tmp/<binary>"],
    }


def run_cpp_self_test(binary: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(binary), "--self-test"],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
    )
    result = json.loads(completed.stdout)
    require(result.get("result") == "PASS", "C++ global self-test did not pass")
    return result


def global_input_lines(
    candidate: dict[str, Any], records: list[dict[str, Any]]
) -> Iterator[str]:
    scale = parse_integer(candidate["target_scale"], "target_scale", positive=True)
    yield "G0118_GLOBAL_INPUT_V1\n"
    yield f"primes {PRIMES[0]} {PRIMES[1]} {scale % PRIMES[0]} {scale % PRIMES[1]}\n"
    yield f"terms {len(candidate['terms'])}\n"
    for term in candidate["terms"]:
        sequence = term["sequence"]
        coefficient = parse_integer(term["coefficient"], f"term {sequence} coefficient")
        record = records[sequence]
        yield (
            f"term {sequence} {coefficient % PRIMES[0]} {coefficient % PRIMES[1]} "
            f"{record['active_vertices']} {record['signed_mass']} "
            f"{len(record['negative_edges'])} {len(record['positive_edges'])}\n"
        )
        for u, v in record["negative_edges"]:
            yield f"negative {u} {v}\n"
        for u, v in record["positive_edges"]:
            yield f"positive {u} {v}\n"
    yield "end\n"


def run_global_replay(
    binary: Path,
    candidate: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    descriptor: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", prefix="g0118-iteration2-global-", suffix=".txt", delete=False
        ) as stream:
            descriptor = Path(stream.name)
            stream.writelines(global_input_lines(candidate, records))
        with descriptor.open("r", encoding="utf-8") as input_stream:
            completed = subprocess.run(
                [str(binary)],
                stdin=input_stream,
                check=True,
                text=True,
                stdout=subprocess.PIPE,
            )
        result = json.loads(completed.stdout)
    finally:
        if descriptor is not None and descriptor.exists():
            descriptor.unlink()
    require(
        result.get("schema") == "g0118-iteration2-cleanroom-global-modular-replay-v1",
        "global replay schema drift",
    )
    require(result.get("primes") == list(PRIMES), "global replay prime drift")
    require(result.get("terms") == len(candidate["terms"]), "global term census drift")
    require(
        result.get("labelled_permutations") == len(candidate["terms"]) * math.factorial(11),
        "global labelled-permutation census drift",
    )
    return result


def residual_summary(residual: Sequence[int]) -> dict[str, Any]:
    nonzero = [(index, value) for index, value in enumerate(residual) if value]
    return {
        "nonzero_rows": len(nonzero),
        "first_nonzero_row": nonzero[0][0] if nonzero else None,
        "first_nonzero_value": str(nonzero[0][1]) if nonzero else None,
        "decimal_rows_sha256": canonical_json_sha256([str(value) for value in residual]),
    }


def expect_rejection(callable_object: Any, label: str) -> str:
    try:
        callable_object()
    except ReviewError as error:
        return str(error)
    raise ReviewError(f"{label} mutant escaped")


def validate_sparse_shape(candidate: dict[str, Any]) -> None:
    support = candidate["support_sequences"]
    coefficients = candidate["integer_coefficients"]
    require(
        isinstance(support, list) and all(isinstance(sequence, int) for sequence in support),
        "support is not an integer sequence list",
    )
    require(support == sorted(set(support)), "support is not strictly increasing and unique")
    require(len(support) == len(coefficients), "support/coefficient slot census mismatch")
    parsed = [parse_integer(raw, f"coefficient slot {index}") for index, raw in enumerate(coefficients)]
    projected = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(support, parsed, strict=True)
        if coefficient != 0
    ]
    require(candidate["terms"] == projected, "sparse term projection mismatch")


def main(output: Path) -> None:
    candidate_sha = sha256_path(CANDIDATE)
    require(candidate_sha == EXPECTED_CANDIDATE_SHA256, "candidate SHA-256 drift")
    candidate = load_json(CANDIDATE)
    require(
        candidate.get("schema") == "max11-g0118-prefix-exact-cegis-iteration2-v1",
        "candidate schema drift",
    )

    bindings_before = actual_candidate_bindings(candidate)
    require(candidate["bindings"] == bindings_before, "candidate input binding drift")
    source_hashes = {
        "candidate": candidate_sha,
        "preregistration": sha256_path(PREREGISTRATION),
        "producer_hashed_not_executed": sha256_path(PRODUCER),
        "review_preregistration": sha256_path(REVIEW / "PREREGISTRATION.md"),
        "review_python": sha256_path(Path(__file__)),
        "review_cpp": sha256_path(GLOBAL_SOURCE),
    }
    require(
        candidate["preregistration_sha256"] == source_hashes["preregistration"],
        "candidate preregistration binding drift",
    )
    require(
        candidate["runner_sha256"] == source_hashes["producer_hashed_not_executed"],
        "candidate producer binding drift",
    )

    panel_input = load_json(PANEL_INPUT)
    retained = load_json(RETAINED)
    coordinate_1 = load_json(COORDINATE_1)
    coordinate_2 = load_json(COORDINATE_2)
    require(panel_input.get("schema") == "max11-g0113-panel-solver-input-v1", "panel schema drift")
    records = panel_input["records"]
    require(len(records) == 163_740, "panel record census drift")
    require(
        all(record.get("sequence") == sequence for sequence, record in enumerate(records)),
        "panel sequence/index mapping drift",
    )
    require(len(panel_input["target"]) == PANEL_ROWS, "panel target row census drift")

    linear_1, hinges_1, coordinate_receipt_1 = verify_coordinate(
        coordinate_1, DIRECTION_1, len(records), "iteration-1 coordinate"
    )
    linear_2, hinges_2, coordinate_receipt_2 = verify_coordinate(
        coordinate_2, DIRECTION_2, len(records), "iteration-2 coordinate"
    )
    require(linear_1 == linear_2, "two coordinate files disagree on the linear stream")
    require(
        coordinate_1["bindings"]["panel_input"] == bindings_before[
            "artifacts/math/G-0113/panel_solver_input_v1.json"
        ],
        "iteration-1 coordinate/panel binding drift",
    )
    require(
        coordinate_2["bindings"]["panel_input"] == bindings_before[
            "artifacts/math/G-0113/panel_solver_input_v1.json"
        ],
        "iteration-2 coordinate/panel binding drift",
    )

    require(
        retained.get("schema") == "max11-g0113-panel-retained-columns-v1",
        "retained-column schema drift",
    )
    retained_by_sequence: dict[int, dict[str, Any]] = {}
    record_keys = (
        "sequence",
        "orbit_index",
        "signed_class_sha256",
        "stage",
        "in_disjoint",
        "in_shared_distinct",
        "representative",
    )
    for column in retained["columns"]:
        sequence = column["sequence"]
        require(sequence not in retained_by_sequence, "duplicate retained sequence")
        require(len(column["vector"]) == PANEL_ROWS, "retained vector row-count drift")
        require(
            hashlib.sha256(vector_i128_bytes(column["vector"])).hexdigest()
            == column["panel_vector_sha256"],
            f"retained vector digest drift at sequence {sequence}",
        )
        require(
            all(column[key] == records[sequence][key] for key in record_keys),
            f"retained/input provenance drift at sequence {sequence}",
        )
        retained_by_sequence[sequence] = column

    require(CACHE.stat().st_size >= PREFIX_BYTES, "cache shorter than frozen prefix")
    prefix_sha_before = sha256_prefix(CACHE, PREFIX_BYTES)
    require(prefix_sha_before == candidate["prefix_sha256"], "frozen cache-prefix digest drift")
    require(candidate["prefix_records"] == PREFIX_RECORDS, "candidate prefix count drift")

    validate_sparse_shape(candidate)
    support = candidate["support_sequences"]
    coefficients = [
        parse_integer(raw, f"coefficient slot {index}")
        for index, raw in enumerate(candidate["integer_coefficients"])
    ]
    scale = parse_integer(candidate["target_scale"], "target_scale", positive=True)
    terms = candidate["terms"]
    require(len(support) == 123, "iteration-2 support slot census drift")
    require(len(terms) == 100, "iteration-2 nonzero-term census drift")
    require(candidate["hinge_directions"] == [list(DIRECTION_1), list(DIRECTION_2)], "hinge row order drift")

    common_basis = [
        column["sequence"]
        for column in retained["columns"]
        if column["selected_p1"] and column["selected_p2"]
    ]
    require(len(common_basis) == 115, "common panel basis census drift")
    require(common_basis == sorted(set(common_basis)), "common panel basis order drift")
    trials = candidate["trials"]
    require(len(trials) == 9, "iteration-2 trial census drift")
    added_sequences: list[int] = []
    for iteration, trial in enumerate(trials[:-1]):
        require(trial["iteration"] == iteration, "trial iteration order drift")
        require(trial["result"] == "SEPARATOR_VIOLATED", "non-final trial result drift")
        require(trial["augmented_rank"] == trial["rank"] + 1, "rank-growth trial is not strict")
        added_sequences.append(trial["first_violating_sequence"])
    require(trials[-1] == {"augmented_rank": 123, "iteration": 8, "rank": 123, "result": "EXACT_Q_MEMBER"}, "final trial drift")
    require(added_sequences == sorted(set(added_sequences)), "added trial sequences are not increasing/unique")
    require(support == sorted(set(common_basis) | set(added_sequences)), "support provenance drift")
    family = set(range(PREFIX_RECORDS)) | set(common_basis)
    require(len(family) == candidate["family_sequences"] == 40_003, "prefix family census drift")

    coordinate_rows = candidate["coordinate_rows"]
    require(
        coordinate_rows == sorted(set(coordinate_rows))
        and len(coordinate_rows) == len(support)
        and all(0 <= row < ROWS for row in coordinate_rows),
        "coordinate-row basis shape/order drift",
    )
    require({ROWS - 2, ROWS - 1}.issubset(coordinate_rows), "coordinate-row basis omits a hinge row")

    with CACHE.open("rb") as cache_stream:
        overlap_sequences = sorted(
            sequence for sequence in retained_by_sequence if sequence < PREFIX_RECORDS
        )
        for sequence in overlap_sequences:
            require(
                cache_block(cache_stream, sequence)
                == vector_i128_bytes(retained_by_sequence[sequence]["vector"]),
                f"cache/retained byte mismatch at sequence {sequence}",
            )

        def panel_vector(sequence: int) -> list[int]:
            if sequence < PREFIX_RECORDS:
                return decode_panel_block(cache_block(cache_stream, sequence))
            require(sequence in retained_by_sequence, f"missing retained vector {sequence}")
            return retained_by_sequence[sequence]["vector"]

        columns = {
            sequence: panel_vector(sequence)
            + linear_1[sequence]
            + [hinges_1[sequence], hinges_2[sequence]]
            for sequence in support
        }

    require(all(len(column) == ROWS for column in columns.values()), "assembled column height drift")
    selected_basis_sha = digest_i128(
        columns[sequence][row] for row in range(ROWS) for sequence in support
    )
    require(selected_basis_sha == candidate["selected_basis_sha256"], "selected-basis digest drift")

    factorial_11 = math.factorial(11)
    require(factorial_11 == 39_916_800, "11! arithmetic drift")
    unscaled_target = panel_input["target"] + [0] * 10 + [factorial_11, 0, 0]
    require(len(unscaled_target) == ROWS, "target row order/height drift")
    scaled_target = [scale * value for value in unscaled_target]
    aggregate = [0] * ROWS
    for term in terms:
        coefficient = parse_integer(term["coefficient"], f"term {term['sequence']} coefficient")
        column = columns[term["sequence"]]
        for row, value in enumerate(column):
            aggregate[row] += coefficient * value
    residual = [left - right for left, right in zip(aggregate, scaled_target, strict=True)]
    require(not any(residual), "candidate fails independently assembled 314-row replay")

    coefficient_mutants: list[dict[str, Any]] = []
    for term_index, term in enumerate(terms):
        mutant_residual = [
            residual[row] + columns[term["sequence"]][row] for row in range(ROWS)
        ]
        summary = residual_summary(mutant_residual)
        require(summary["nonzero_rows"] > 0, f"+1 coefficient mutant escaped at term {term_index}")
        coefficient_mutants.append(
            {"term_index": term_index, "sequence": term["sequence"], **summary}
        )

    swapped = [dict(term) for term in terms]
    swapped[0]["sequence"], swapped[1]["sequence"] = swapped[1]["sequence"], swapped[0]["sequence"]
    swapped_aggregate = [0] * ROWS
    for term in swapped:
        for row, value in enumerate(columns[term["sequence"]]):
            swapped_aggregate[row] += int(term["coefficient"]) * value
    require(swapped_aggregate != scaled_target, "sequence-mapping swap mutant escaped")

    target_mutants = {
        "target_scale_plus_one": [(scale + 1) * value for value in unscaled_target],
        "factorial_10": [
            scale * value for value in panel_input["target"] + [0] * 10 + [math.factorial(10), 0, 0]
        ],
        "linear_target_coordinate_9": [
            scale * value
            for value in panel_input["target"] + [0] * 9 + [factorial_11, 0, 0, 0]
        ],
    }
    for label, mutant_target in target_mutants.items():
        require(aggregate != mutant_target, f"{label} mutant escaped")
    wrong_row_order = aggregate[:PANEL_ROWS] + [aggregate[-1]] + aggregate[PANEL_ROWS:-1]
    require(wrong_row_order != scaled_target, "row-order mutant escaped")

    sparse_duplicate = copy.deepcopy(candidate)
    sparse_duplicate["support_sequences"][1] = sparse_duplicate["support_sequences"][0]
    sparse_term_mutant = copy.deepcopy(candidate)
    sparse_term_mutant["terms"][0]["sequence"] = sparse_term_mutant["terms"][1]["sequence"]
    bad_binding = dict(bindings_before)
    first_binding = next(iter(bad_binding))
    bad_binding[first_binding] = "0" * 64
    structural_mutants = {
        "duplicate_support": expect_rejection(
            lambda: validate_sparse_shape(sparse_duplicate), "duplicate support"
        ),
        "term_sequence_projection": expect_rejection(
            lambda: validate_sparse_shape(sparse_term_mutant), "term projection"
        ),
        "binding_hash": expect_rejection(
            lambda: require(candidate["bindings"] == bad_binding, "binding digest mismatch"),
            "binding hash",
        ),
    }

    # Re-derive every support hinge price from signed graphs, and every support
    # linear vector from a separate sign-state DP.  Neither path consumes the
    # producer's finite-row replay assertions.
    independent_linears: dict[int, list[int]] = {}
    for position, sequence in enumerate(support):
        record = records[sequence]
        price_1 = coordinate_price(record, DIRECTION_1)
        price_2 = coordinate_price(record, DIRECTION_2)
        require(price_1 == hinges_1[sequence], f"independent first-hinge mismatch at {sequence}")
        require(price_2 == hinges_2[sequence], f"independent second-hinge mismatch at {sequence}")
        linear = independent_linear_vector(record)
        require(linear == linear_1[sequence], f"independent linear mismatch at {sequence}")
        independent_linears[sequence] = linear
        if position == 0 or (position + 1) % 20 == 0 or position + 1 == len(support):
            print(
                f"independent frozen-coordinate replay {position + 1}/{len(support)} sequence={sequence}",
                file=os.sys.stderr,
                flush=True,
            )

    python_controls = python_self_test()
    binary, compiler_receipt = compile_global_replayer()
    cpp_controls = run_cpp_self_test(binary)
    global_result = run_global_replay(binary, candidate, records)

    cpp_linears = {
        item["sequence"]: item["linear"] for item in global_result["term_linear_vectors"]
    }
    require(
        set(cpp_linears) == {term["sequence"] for term in terms},
        "C++ per-term linear sequence census drift",
    )
    for sequence, cpp_linear in cpp_linears.items():
        require(cpp_linear == independent_linears[sequence], f"C++/Python linear mismatch at {sequence}")

    first_direction = global_result["first_nonzero_hinge_direction"]
    exact_global_coordinate: dict[str, Any] | None = None
    if first_direction is not None:
        require(direction_is_canonical_active(first_direction), "first global direction is noncanonical")
        exact_value = 0
        contributions: list[dict[str, Any]] = []
        for term in terms:
            sequence = term["sequence"]
            price = coordinate_price(records[sequence], first_direction)
            if price:
                contribution = int(term["coefficient"]) * price
                exact_value += contribution
                contributions.append(
                    {
                        "sequence": sequence,
                        "price": price,
                        "coefficient": term["coefficient"],
                        "contribution": str(contribution),
                    }
                )
        require(exact_value != 0, "nonzero modular hinge aliases to zero exact coordinate")
        residues = [exact_value % prime for prime in PRIMES]
        require(
            residues == global_result["first_nonzero_hinge_residues"],
            "independent exact coordinate does not project to global residues",
        )
        exact_global_coordinate = {
            "direction": first_direction,
            "value": str(exact_value),
            "residues": residues,
            "nonzero_term_prices": len(contributions),
            "contributions": contributions,
            "method": (
                "Python BigInt coefficient accumulation over independently targeted active-vertex "
                "rank-injection prices; no C++ direction histogram reused"
            ),
        }
    elif global_result["first_nonzero_linear_coordinate"] is not None:
        coordinate = global_result["first_nonzero_linear_coordinate"]
        exact_value = sum(
            int(term["coefficient"]) * independent_linears[term["sequence"]][coordinate]
            for term in terms
        )
        if coordinate == 10:
            exact_value -= scale * factorial_11
        require(exact_value != 0, "nonzero modular linear residual aliases to zero exact coordinate")
        residues = [exact_value % prime for prime in PRIMES]
        require(
            residues
            == [
                global_result["linear_residues"][str(PRIMES[0])][coordinate],
                global_result["linear_residues"][str(PRIMES[1])][coordinate],
            ],
            "independent exact linear coordinate does not project to global residues",
        )
        exact_global_coordinate = {
            "linear_coordinate": coordinate,
            "value": str(exact_value),
            "residues": residues,
            "method": "Python BigInt accumulation over independent sign-state linear DPs",
        }

    if global_result["both_primes_global_zero"]:
        require(exact_global_coordinate is None, "global zero screen nevertheless has exact residual")
        disposition = "MODULAR_ZERO_SCREEN_EXACT_GLOBAL_REPLAY_REQUIRED"
    else:
        require(exact_global_coordinate is not None, "global nonzero lacks an exact coordinate replay")
        disposition = "CANDIDATE_GLOBALLY_REFUTED"

    bindings_after = actual_candidate_bindings(candidate)
    require(bindings_after == bindings_before, "candidate-bound input changed during review")
    require(sha256_path(CANDIDATE) == candidate_sha, "candidate changed during review")
    require(sha256_prefix(CACHE, PREFIX_BYTES) == prefix_sha_before, "cache prefix changed during review")
    require(sha256_path(GLOBAL_SOURCE) == source_hashes["review_cpp"], "review C++ source changed during run")
    require(sha256_path(Path(__file__)) == source_hashes["review_python"], "review Python source changed during run")

    omitted_zero_sequences = [
        sequence
        for sequence, coefficient in zip(support, coefficients, strict=True)
        if coefficient == 0
    ]
    receipt = {
        "schema": "g0118-iteration2-independent-candidate-review-v1",
        "result": disposition,
        "claim_boundary": (
            "Exact 314-row membership is finite membership only. Modular zero is only a screen. "
            "A nonzero global residual refutes only this exact candidate, not the frozen family, "
            "family completeness, unrestricted two-hidden-layer MAX11, or the all-arity target."
        ),
        "independence": {
            "reviewer": "CrimsonSpire / Codex / same-lineage fresh context (T1)",
            "iteration2_solver_imported": False,
            "iteration2_solver_executed": False,
            "finite_method": "Python BigInt accumulation from frozen panel/coordinate records",
            "global_method": "independent C++ full-permutation subset histogram and normal form",
            "exact_residual_method": (
                "independent Python active-injection coordinate DP or sign-state linear DP"
            ),
        },
        "bindings": {
            **source_hashes,
            "candidate_declared_inputs": bindings_before,
            "candidate_declared_inputs_stable_after_run": True,
            "cache_prefix_sha256": prefix_sha_before,
        },
        "sequence_and_support": {
            "prefix_records": PREFIX_RECORDS,
            "prefix_bytes": PREFIX_BYTES,
            "prefix_sha256": prefix_sha_before,
            "retained_overlap_sequences_checked": len(overlap_sequences),
            "common_panel_basis_sequences": len(common_basis),
            "rank_growing_added_sequences": added_sequences,
            "support_slots": len(support),
            "support_sequences_sha256": canonical_json_sha256(support),
            "nonzero_terms": len(terms),
            "omitted_zero_slots": len(omitted_zero_sequences),
            "omitted_zero_sequences": omitted_zero_sequences,
            "family_sequences": len(family),
            "selected_basis_i128le_sha256": selected_basis_sha,
            "coordinate_rows": coordinate_rows,
            "coordinate_rows_sha256": canonical_json_sha256(coordinate_rows),
            "gcd_of_scale_and_all_serialized_coefficients": str(
                reduce(gcd, [scale] + [abs(value) for value in coefficients])
            ),
        },
        "coordinate_streams": [coordinate_receipt_1, coordinate_receipt_2],
        "independent_coordinate_semantics": {
            "support_sequences_checked": len(support),
            "linear_vectors_exact": True,
            "first_hinge_prices_exact": True,
            "second_hinge_prices_exact": True,
        },
        "finite_replay": {
            "rows": ROWS,
            "panel_rows": PANEL_ROWS,
            "linear_rows": LINEAR_ROWS,
            "hinge_rows": HINGE_ROWS,
            "factorial_11": factorial_11,
            "target_scale": str(scale),
            "unscaled_target_decimal_sha256": canonical_json_sha256(unscaled_target),
            "scaled_target_decimal_sha256": canonical_json_sha256(
                [str(value) for value in scaled_target]
            ),
            "aggregate_decimal_sha256": canonical_json_sha256(
                [str(value) for value in aggregate]
            ),
            "all_314_rows_exact": True,
            "panel_rows_exact": not any(residual[:PANEL_ROWS]),
            "linear_rows_exact": not any(residual[PANEL_ROWS : PANEL_ROWS + LINEAR_ROWS]),
            "hinge_rows_exact": not any(residual[-HINGE_ROWS:]),
        },
        "controls": {
            "python_self_test": python_controls,
            "cpp_self_test": cpp_controls,
            "all_plus_one_coefficient_mutants_rejected": True,
            "plus_one_mutants": coefficient_mutants,
            "sequence_mapping_swap_rejected": True,
            "target_scale_plus_one_rejected": True,
            "factorial_10_target_rejected": True,
            "wrong_linear_target_coordinate_rejected": True,
            "row_order_mutant_rejected": True,
            "structural_mutants": structural_mutants,
        },
        "global_modular_replay": global_result,
        "exact_first_global_residual": exact_global_coordinate,
        "compiler": compiler_receipt,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.self_test:
        if arguments.output is not None:
            raise SystemExit("--self-test and --output are mutually exclusive")
        python_result = python_self_test()
        executable, compiler = compile_global_replayer()
        cpp_result = run_cpp_self_test(executable)
        print(
            json.dumps(
                {
                    "schema": "g0118-iteration2-review-self-test-v1",
                    "result": "PASS",
                    "python": python_result,
                    "cpp": cpp_result,
                    "compiler": compiler,
                },
                sort_keys=True,
            )
        )
    else:
        if arguments.output is None:
            raise SystemExit("--output is required unless --self-test is used")
        main(arguments.output.resolve())
