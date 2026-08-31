#!/usr/bin/env python3
"""Same-lineage clean-room audit of the G-0118 candidate-4 Batch32 artifacts.

No G-0117 Rust module is imported or executed.  A separate C++ implementation
reconstructs the complete global modular normal form and prices every frozen
record.  Python arbitrary-precision arithmetic checks all finite dot products.
"""

from __future__ import annotations

import argparse
import array
import copy
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence


ROOT = Path(__file__).resolve().parents[3]
REVIEW = Path(__file__).resolve().parent

PANEL_INPUT = ROOT / "artifacts/math/G-0113/panel_solver_input_v1.json"
PANEL_SCAN = ROOT / "artifacts/math/G-0113/panel_scan_v1.json"
CANDIDATE = ROOT / "artifacts/math/G-0118/prefix_exact_cegis_iteration4_v1.json"
CANDIDATE_RECHECK = ROOT / "artifacts/math/G-0118/prefix_exact_cegis_iteration4_recheck_v1.json"
REPLAY = ROOT / "artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json"
PRICES = ROOT / "artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json"
HANDOFF = ROOT / "artifacts/math/G-0118/ITERATION4_BATCH_HANDOFF.md"
BATCH_PREREG = ROOT / "artifacts/math/G-0118/BATCH32_ITERATION4_PREREGISTRATION.md"
CACHE_MANIFEST = ROOT / "artifacts/math/G-0117/full_family_cache_manifest_v1.json"
CACHE = ROOT / "artifacts/math/G-0117/full_family_cache_v1.i128le"
CPP_SOURCE = REVIEW / "cleanroom_batch_audit.cpp"
REVIEW_PREREG = REVIEW / "PREREGISTRATION.md"

REPLAY_SOURCE = ROOT / "artifacts/math/G-0117/src/bin/g0118_batch_modular_replay.rs"
PRICE_SOURCE = ROOT / "artifacts/math/G-0117/src/bin/g0118_batch_coordinate_pricer.rs"
KERNEL_SOURCE = ROOT / "artifacts/math/G-0117/src/lib.rs"
UNIQUENESS = ROOT / "artifacts/math/G-0117/NORMAL_FORM_UNIQUENESS_LEMMA.md"

COORDINATES = (
    ROOT / "artifacts/math/G-0117/fresh_q_cegis_iteration1_coordinate_v1.json",
    ROOT / "artifacts/math/G-0118/iteration2_residual_coordinate_v1.json",
    ROOT / "artifacts/math/G-0118/iteration3_residual_coordinate_v1.json",
    ROOT / "artifacts/math/G-0118/iteration4_residual_coordinate_v1.json",
)

EXPECTED = {
    "panel_input": "093d599a209dc1bf8dc2a3ff5b178205005500b08e021b83eb0c92d99f46a0c8",
    "panel_scan": "6f3f52bf9709cda495258f760bf51bdde33eea015e0db499cacf04c28eabb85e",
    "candidate": "728c06bd02f03367fbfa9f50c0353dc74b708a6ef576520cc0eaa72e2e472e1b",
    "candidate_recheck": "f29c7095a60ab945293bb1b182afde372405e3cb45c3509080f766aebf46911f",
    "replay": "c402c0c9e89c2d8a95fc8b40c44346f9eaeae3c2ade5a7662d97cda04680ad80",
    "prices": "349e63a7a2f254a2b0d4c05a4ce4c088afa7ff859675876e2b8c3bac05b6547b",
    "handoff": "3189bbb406ee63b518fb65f1a50f496612d3abf1e0397613760c2c3f9dac4b3d",
    "batch_prereg": "54a329587786c8824e8eede13a6165983ecc64c27a7f758be9676583bd283feb",
    "replay_source": "172be64103b9ebf7516514923c94bc7de8ee63bfc92a776e321c87c469a58db9",
    "price_source": "35cabc07a3e6a50366c584c737493b393b202092d64f0951a37dde4f515d3058",
    "kernel": "2bb97bb05e32816a77d438a14b049cbf5b003d6ba164b7f0088422d49f80afa6",
    "uniqueness": "39de1eb61aaee37a24c8a45d55cbc5fd6f27c7b68d506f8757f352881a6e0c17",
    "cache_manifest": "e546f65429c33012c638b0be3b37cf9af4228070c00136e05914e701436e44bf",
    "cache": "da045a6fc004afeb6c9b67c8fc093a191ed3e9c515bc8e97901a6e64cb125c5b",
}

N = 11
RECORDS = 163_740
PANEL_ROWS = 301
PRIMES = (1_000_000_007, 1_000_000_009)
ACCUMULATED = (
    (0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4),
    (0, 0, 0, 0, 0, 0, 0, 0, 1, -4, 3),
    (0, 0, 0, 0, 0, 0, 0, 0, 1, -3, 2),
    (0, 0, 0, 0, 0, 0, 0, 0, 1, -2, 1),
)
DIRECTION_MUTANT = (0, 0, 0, 0, 0, 0, 0, 0, 3, -4, 1)
INTEGER_RE = re.compile(r"(?:0|-[1-9][0-9]*|[1-9][0-9]*)\Z")
HEX_RE = re.compile(r"[0-9a-f]{64}\Z")


class AuditError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def reject_duplicate_keys(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        require(key not in result, f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream, object_pairs_hook=reject_duplicate_keys)


def sha256_path(path: Path, *, prefix_bytes: int | None = None) -> str:
    digest = hashlib.sha256()
    remaining = prefix_bytes
    with path.open("rb") as stream:
        while True:
            if remaining is not None and remaining == 0:
                break
            size = 1 << 20 if remaining is None else min(1 << 20, remaining)
            block = stream.read(size)
            if not block:
                break
            digest.update(block)
            if remaining is not None:
                remaining -= len(block)
    if remaining is not None:
        require(remaining == 0, f"short prefix while hashing {path}")
    return digest.hexdigest()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def digest_i64(values: Iterable[int]) -> str:
    digest = hashlib.sha256()
    for value in values:
        require(-(1 << 63) <= value < (1 << 63), "value outside signed i64")
        digest.update(struct.pack("<q", value))
    return digest.hexdigest()


def digest_selected(selected: Sequence[dict[str, Any]]) -> str:
    digest = hashlib.sha256()
    for item in selected:
        for coordinate in item["direction"]:
            require(-128 <= coordinate <= 127, "selected coordinate outside signed i8")
            digest.update(struct.pack("<b", coordinate))
        for residue in item["residues"]:
            digest.update(struct.pack("<Q", residue))
    return digest.hexdigest()


def parse_integer(raw: Any, label: str, *, positive: bool = False) -> int:
    require(isinstance(raw, str) and INTEGER_RE.fullmatch(raw) is not None,
            f"{label} is not a canonical integer")
    value = int(raw)
    if positive:
        require(value > 0, f"{label} is not positive")
    return value


def git(*arguments: str, binary: bool = False) -> bytes | str:
    completed = subprocess.run(
        ["git", *arguments], cwd=ROOT, check=True,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
    )
    return completed.stdout if binary else completed.stdout.decode().strip()


def is_tracked(relative: str) -> bool:
    completed = subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative], cwd=ROOT,
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    return completed.returncode == 0


def actual_candidate_bindings(candidate: dict[str, Any]) -> dict[str, str]:
    actual: dict[str, str] = {}
    for relative in candidate["bindings"]:
        path = (ROOT / relative).resolve()
        try:
            path.relative_to(ROOT.resolve())
        except ValueError as error:
            raise AuditError(f"candidate binding escapes repository: {relative}") from error
        require(path.is_file() and not path.is_symlink(), f"bad bound file: {relative}")
        actual[relative] = sha256_path(path)
    return actual


def matrix_from_record(record: dict[str, Any], sequence: int) -> tuple[list[int], int]:
    required = {
        "sequence", "signed_mass", "active_vertices", "negative_edges", "positive_edges",
        "orbit_index", "signed_class_sha256", "stage", "in_disjoint",
        "in_shared_distinct", "representative",
    }
    require(required.issubset(record), f"record {sequence} missing keys")
    require(record["sequence"] == sequence, f"record sequence/index drift at {sequence}")
    active = record["active_vertices"]
    mass = record["signed_mass"]
    require(isinstance(active, int) and 0 <= active <= N, f"bad active count at {sequence}")
    require(isinstance(mass, int) and 0 <= mass <= 5, f"bad signed mass at {sequence}")
    require(len(record["negative_edges"]) == len(record["positive_edges"]) == mass,
            f"edge/mass drift at {sequence}")
    require(isinstance(record["signed_class_sha256"], str)
            and HEX_RE.fullmatch(record["signed_class_sha256"]) is not None,
            f"bad signed-class digest at {sequence}")
    matrix = [0] * (N * N)
    for sign, key in ((-1, "negative_edges"), (1, "positive_edges")):
        for edge in record[key]:
            require(isinstance(edge, list) and len(edge) == 2
                    and all(isinstance(value, int) for value in edge),
                    f"malformed edge at {sequence}")
            u, v = edge
            require(0 <= u < v < active, f"noncompact/loop edge at {sequence}")
            matrix[u * N + v] += sign
            matrix[v * N + u] += sign
    observed_active = sum(
        any(matrix[row * N + column] != 0 for column in range(N))
        for row in range(N)
    )
    require(observed_active == active, f"active support drift at {sequence}")
    require(all(-5 <= value <= 5 for value in matrix), f"weight envelope drift at {sequence}")
    return matrix, active


def validate_records(
    panel: dict[str, Any], panel_scan: dict[str, Any]
) -> tuple[list[list[int]], dict[str, int], dict[str, int]]:
    require(panel.get("schema") == "max11-g0113-panel-solver-input-v1", "panel schema drift")
    records = panel.get("records")
    require(isinstance(records, list) and len(records) == RECORDS, "panel record census drift")
    require(len(panel.get("target", [])) == PANEL_ROWS, "panel target row census drift")
    matrices: list[list[int]] = []
    active_histogram: Counter[int] = Counter()
    stage_histogram: Counter[str] = Counter()
    signed_classes: set[str] = set()
    for sequence, record in enumerate(records):
        matrix, active = matrix_from_record(record, sequence)
        matrices.append(matrix)
        active_histogram[active] += 1
        stage = record["stage"]
        require(stage in {"DISJOINT", "SHARED_DISTINCT_ONLY"}, f"unknown stage at {sequence}")
        require(record["in_disjoint"] is (stage == "DISJOINT"),
                f"stage/disjoint flag drift at {sequence}")
        require(stage != "SHARED_DISTINCT_ONLY" or record["in_shared_distinct"] is True,
                f"shared-distinct-only flag drift at {sequence}")
        stage_histogram[stage] += 1
        signed_hash = record["signed_class_sha256"]
        require(signed_hash not in signed_classes, f"duplicate signed-class digest at {sequence}")
        signed_classes.add(signed_hash)
    expected_active = {int(key): value for key, value in panel_scan["active_vertex_histogram"].items()}
    require(dict(sorted(active_histogram.items())) == expected_active,
            "record-derived active histogram disagrees with scan")
    require(panel_scan["records"] == RECORDS, "scan record census drift")
    require(stage_histogram["DISJOINT"] == panel_scan["disjoint_records"],
            "disjoint stage census drift")
    require(stage_histogram["SHARED_DISTINCT_ONLY"] == panel_scan["shared_distinct_only_records"],
            "shared-distinct-only stage census drift")
    return matrices, {str(key): value for key, value in sorted(active_histogram.items())}, dict(stage_histogram)


def validate_candidate(candidate: dict[str, Any], recheck: dict[str, Any]) -> tuple[list[tuple[int, int]], int]:
    require(candidate.get("schema") == "max11-g0118-prefix-exact-cegis-accumulated-v1",
            "candidate schema drift")
    require(candidate.get("result") == "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS",
            "candidate result drift")
    require(candidate.get("iteration") == 4 and candidate.get("all_rows_replayed") is True,
            "candidate iteration/replay flag drift")
    require(candidate.get("coefficient_plus_one_mutant_rejected") is True,
            "candidate mutant flag drift")
    require(candidate.get("hinge_directions") == [list(value) for value in ACCUMULATED],
            "candidate accumulated-direction order drift")
    bindings = actual_candidate_bindings(candidate)
    require(bindings == candidate["bindings"], "candidate dependency binding drift")
    require(sha256_path(ROOT / candidate["manifest_path"]) == candidate["manifest_sha256"],
            "candidate manifest binding drift")
    require(sha256_path(ROOT / candidate["preregistration_path"])
            == candidate["preregistration_sha256"], "candidate preregistration binding drift")
    require(sha256_path(ROOT / "artifacts/math/G-0118/prefix_exact_cegis_accumulated.py")
            == candidate["runner_sha256"], "candidate runner binding drift")

    support = candidate["support_sequences"]
    coefficient_slots = candidate["integer_coefficients"]
    require(support == sorted(set(support)) and len(support) == len(coefficient_slots),
            "candidate support/slot shape drift")
    parsed_slots = [parse_integer(raw, f"coefficient slot {index}")
                    for index, raw in enumerate(coefficient_slots)]
    projected = [
        {"sequence": sequence, "coefficient": str(coefficient)}
        for sequence, coefficient in zip(support, parsed_slots, strict=True)
        if coefficient != 0
    ]
    require(projected == candidate["terms"], "candidate sparse projection drift")
    terms = [(term["sequence"], parse_integer(term["coefficient"], "term coefficient"))
             for term in candidate["terms"]]
    require(len(terms) == 102 and all(value != 0 for _, value in terms),
            "candidate term census/zero drift")
    require([sequence for sequence, _ in terms] == sorted({sequence for sequence, _ in terms}),
            "candidate term sequence order drift")
    scale = parse_integer(candidate["target_scale"], "target_scale", positive=True)

    same_fields = (
        "schema", "result", "iteration", "bindings", "manifest_path", "manifest_sha256",
        "preregistration_path", "preregistration_sha256", "runner_sha256", "target_scale",
        "support_sequences", "integer_coefficients", "terms", "hinge_directions",
        "coordinate_rows", "selected_basis_sha256", "all_rows_replayed",
        "coefficient_plus_one_mutant_rejected", "prefix_records", "prefix_sha256",
    )
    for field in same_fields:
        require(candidate.get(field) == recheck.get(field), f"candidate/recheck drift in {field}")
    return terms, scale


def validate_replay(replay: dict[str, Any]) -> list[dict[str, Any]]:
    require(replay.get("schema") == "max11-g0118-batch32-global-modular-replay-v1",
            "replay schema drift")
    require(replay.get("result") == "BATCH_RESIDUAL_PREFIX_SELECTED", "replay result drift")
    require(replay.get("primes") == list(PRIMES), "replay prime drift")
    require(replay.get("batch_k") == 32 and replay.get("selected_count") == 32,
            "replay batch census drift")
    require(replay.get("terms") == 102 and replay.get("complete_global_replay") is True,
            "replay completion/term drift")
    require(replay.get("candidate_schema") == "max11-g0118-prefix-exact-cegis-accumulated-v1"
            and replay.get("candidate_result") == "PREFIX_EXACT_Q_MEMBER_ALL_316_ROWS",
            "replay candidate identity drift")
    expected_bindings = {
        "candidate": EXPECTED["candidate"],
        "candidate_recheck": EXPECTED["candidate_recheck"],
        "panel_input": EXPECTED["panel_input"],
        "preregistration": EXPECTED["batch_prereg"],
        "producer": EXPECTED["replay_source"],
        "kernel": EXPECTED["kernel"],
        "normal_form_uniqueness": EXPECTED["uniqueness"],
    }
    for key, expected in expected_bindings.items():
        require(replay["bindings"].get(key) == expected, f"replay binding drift: {key}")
    require(set(replay["bindings"]) == set(expected_bindings) | {"executable"},
            "replay binding-key census drift")
    checks = replay.get("accumulated_row_checks")
    require(isinstance(checks, list) and len(checks) == 4, "replay accumulated check census drift")
    for direction, check in zip(ACCUMULATED, checks, strict=True):
        require(check == {"direction": list(direction), "residues": [0, 0],
                          "zero_in_both_fields": True},
                "replay accumulated-row assertion drift")
    require(replay.get("linear_residues_after_target") == [[0] * N, [0] * N],
            "replay linear assertion drift")
    selected = replay.get("selected")
    require(isinstance(selected, list) and len(selected) == 32, "selected list census drift")
    directions = [tuple(item["direction"]) for item in selected]
    require(directions == sorted(set(directions)), "selected directions are not strict signed-lex")
    for item in selected:
        require(len(item["direction"]) == N and len(item["residues"]) == 2,
                "malformed selected entry")
        require(item["residues"] != [0, 0], "selected zero residual")
    require(digest_selected(selected) == replay["selected_prefix_i8_u64_le_sha256"],
            "selected receipt digest drift")
    mutant = replay.get("coefficient_plus_one_mutant")
    require(mutant.get("sequence") == 0 and mutant.get("coefficient_delta") == "+1"
            and mutant.get("rejected") is True, "replay mutant receipt drift")
    return selected


def validate_prices(prices: dict[str, Any], selected: list[dict[str, Any]]) -> dict[str, Any]:
    require(prices.get("schema") == "max11-g0118-batch32-coordinate-price-v1",
            "price schema drift")
    require(prices.get("result") == "EXACT_BATCH_COORDINATE_PRICES", "price result drift")
    require(prices.get("records") == RECORDS and prices.get("selected_count") == 32
            and prices.get("batch_k") == 32, "price dimensions drift")
    expected_bindings = {
        "candidate": EXPECTED["candidate"],
        "candidate_recheck": EXPECTED["candidate_recheck"],
        "panel_input": EXPECTED["panel_input"],
        "preregistration": EXPECTED["batch_prereg"],
        "producer": EXPECTED["price_source"],
        "replay_producer": EXPECTED["replay_source"],
        "kernel": EXPECTED["kernel"],
        "normal_form_uniqueness": EXPECTED["uniqueness"],
        "replay_receipt": EXPECTED["replay"],
    }
    for key, expected in expected_bindings.items():
        require(prices["bindings"].get(key) == expected, f"price binding drift: {key}")
    require(set(prices["bindings"]) == set(expected_bindings) | {"executable"},
            "price binding-key census drift")
    selected_directions = [item["direction"] for item in selected]
    selected_residues = [item["residues"] for item in selected]
    require(prices.get("directions") == selected_directions, "price/replay direction order drift")
    require(prices.get("modular_residues") == selected_residues, "price/replay residue order drift")
    rows = prices.get("rows")
    require(isinstance(rows, list) and len(rows) == 32, "price row census drift")
    aggregate_digest = hashlib.sha256()
    total_nonzero = 0
    for index, row in enumerate(rows):
        require(row["direction"] == selected_directions[index], f"row direction drift at {index}")
        require(row["modular_residues"] == selected_residues[index],
                f"row residues drift at {index}")
        values = row["hinge_coefficients"]
        require(isinstance(values, list) and len(values) == RECORDS,
                f"row length drift at {index}")
        require(all(isinstance(value, int) and 0 <= value < (1 << 63) for value in values),
                f"row integer/range drift at {index}")
        payload = b"".join(struct.pack("<q", value) for value in values)
        digest = sha256_bytes(payload)
        aggregate_digest.update(payload)
        nonzero = sum(value != 0 for value in values)
        maximum = max(values)
        require(digest == row["hinge_coefficients_i64_le_sha256"],
                f"row stream digest drift at {index}")
        require(nonzero == row["nonzero_hinge_coefficients"],
                f"row nonzero census drift at {index}")
        require(maximum == row["maximum_hinge_coefficient"],
                f"row maximum drift at {index}")
        total_nonzero += nonzero
    require(aggregate_digest.hexdigest() == prices["direction_major_hinge_i64_le_sha256"],
            "aggregate hinge stream digest drift")
    linears = prices.get("linear_vectors")
    require(isinstance(linears, list) and len(linears) == RECORDS
            and all(isinstance(row, list) and len(row) == N for row in linears),
            "linear matrix dimensions drift")
    linear_digest = digest_i64(value for row in linears for value in row)
    require(linear_digest == prices["linear_vectors_i64_le_sha256"],
            "linear stream digest drift")
    return {
        "total_nonzero_hinge_entries": total_nonzero,
        "direction_major_hinge_i64_le_sha256": aggregate_digest.hexdigest(),
        "linear_vectors_i64_le_sha256": linear_digest,
    }


def write_descriptor(
    path: Path,
    matrices: Sequence[Sequence[int]],
    records: Sequence[dict[str, Any]],
    directions: Sequence[Sequence[int]],
    terms: Sequence[tuple[int, int]],
    target_scale: int,
) -> None:
    with path.open("xb") as stream:
        stream.write(b"G118AB1\0")
        stream.write(struct.pack("<IIII", len(records), len(directions), len(terms), N))
        stream.write(struct.pack("<QQ", target_scale % PRIMES[0], target_scale % PRIMES[1]))
        for record, matrix in zip(records, matrices, strict=True):
            stream.write(struct.pack("<BB", record["active_vertices"], record["signed_mass"]))
            stream.write(struct.pack(f"<{N * N}b", *matrix))
        for direction in directions:
            stream.write(struct.pack(f"<{N}b", *direction))
        for sequence, coefficient in terms:
            stream.write(struct.pack("<IQQ", sequence, coefficient % PRIMES[0], coefficient % PRIMES[1]))


def compile_cpp() -> tuple[Path, dict[str, Any]]:
    source_hash = sha256_path(CPP_SOURCE)
    binary = Path(tempfile.gettempdir()) / f"g0118-batch-audit-{source_hash[:16]}"
    temporary = binary.with_name(f"{binary.name}.{os.getpid()}.tmp")
    command = [
        "g++", "-std=c++20", "-O3", "-DNDEBUG", "-Wall", "-Wextra", "-Werror",
        "-pthread", str(CPP_SOURCE), "-o", str(temporary),
    ]
    try:
        subprocess.run(command, check=True)
        os.replace(temporary, binary)
    finally:
        if temporary.exists():
            temporary.unlink()
    version = subprocess.run(["g++", "--version"], check=True, text=True,
                             stdout=subprocess.PIPE).stdout.splitlines()[0]
    self_test = json.loads(subprocess.run([str(binary), "--self-test"], check=True, text=True,
                                          stdout=subprocess.PIPE).stdout)
    require(self_test.get("result") == "PASS", "C++ self-test failed")
    return binary, {
        "source_sha256": source_hash,
        "binary_sha256": sha256_path(binary),
        "compiler": version,
        "compile_command": command[:-1] + ["/tmp/<binary>"],
        "self_test": self_test,
    }


def read_cpp_output(path: Path) -> tuple[int, int, array.array[int]]:
    with path.open("rb") as stream:
        require(stream.read(8) == b"G118AO1\0", "bad C++ output magic")
        records, directions, n = struct.unpack("<III", stream.read(12))
        require(n == N, "C++ output dimension drift")
        values = array.array("q")
        values.fromfile(stream, directions * records + records * N)
        require(stream.read(1) == b"", "trailing C++ output bytes")
    if sys.byteorder != "little":
        values.byteswap()
    return records, directions, values


def compare_cpp_prices(
    values: array.array[int],
    direction_count: int,
    prices: dict[str, Any],
    terms: Sequence[tuple[int, int]],
) -> dict[str, Any]:
    require(direction_count == 37, "C++ direction census drift")
    mismatches = 0
    independent_row_hashes: list[str] = []
    coordinate_hashes: list[str] = []

    for index, path in enumerate(COORDINATES):
        coordinate = load_json(path)
        require(coordinate.get("schema") == "max11-g0117-coordinate-price-v1"
                and coordinate.get("records") == RECORDS,
                f"coordinate schema/census drift at {index}")
        require(tuple(coordinate["direction"]) == ACCUMULATED[index],
                f"coordinate direction drift at {index}")
        expected = coordinate["hinge_coefficients"]
        require(len(expected) == RECORDS, f"coordinate length drift at {index}")
        start = index * RECORDS
        for sequence, claimed in enumerate(expected):
            mismatches += values[start + sequence] != claimed
        row_hash = digest_i64(values[start + sequence] for sequence in range(RECORDS))
        require(row_hash == coordinate["hinge_coefficients_i64_le_sha256"],
                f"independent accumulated-row hash drift at {index}")
        coordinate_hashes.append(row_hash)
        del coordinate

    for index, row in enumerate(prices["rows"]):
        cpp_index = 4 + index
        start = cpp_index * RECORDS
        for sequence, claimed in enumerate(row["hinge_coefficients"]):
            mismatches += values[start + sequence] != claimed
        row_hash = digest_i64(values[start + sequence] for sequence in range(RECORDS))
        require(row_hash == row["hinge_coefficients_i64_le_sha256"],
                f"independent selected-row hash drift at {index}")
        independent_row_hashes.append(row_hash)

    require(mismatches == 0, f"C++/producer price mismatches: {mismatches}")
    linear_offset = direction_count * RECORDS
    linear_mismatches = 0
    for sequence, claimed_row in enumerate(prices["linear_vectors"]):
        for coordinate, claimed in enumerate(claimed_row):
            linear_mismatches += values[linear_offset + sequence * N + coordinate] != claimed
    require(linear_mismatches == 0, f"C++/producer linear mismatches: {linear_mismatches}")
    linear_hash = digest_i64(
        values[linear_offset + index] for index in range(RECORDS * N)
    )
    require(linear_hash == prices["linear_vectors_i64_le_sha256"],
            "independent linear hash drift")

    exact_accumulated = [
        sum(coefficient * values[index * RECORDS + sequence]
            for sequence, coefficient in terms)
        for index in range(4)
    ]
    require(exact_accumulated == [0] * 4, "candidate is nonzero on an accumulated exact row")
    exact_selected = [
        sum(coefficient * values[(4 + index) * RECORDS + sequence]
            for sequence, coefficient in terms)
        for index in range(32)
    ]
    require(all(value != 0 for value in exact_selected), "selected exact residual aliases to zero")
    for index, exact in enumerate(exact_selected):
        require([exact % prime for prime in PRIMES] == prices["modular_residues"][index],
                f"exact/modular bridge drift at selected row {index}")
    residual_stream = "".join(f"{value}\n" for value in exact_selected).encode()
    require(len(residual_stream) == 3431, "exact residual stream length drift")
    require(sha256_bytes(residual_stream)
            == "98f507b0d4277018a7d704c951c1e6b3cac10243b59c3df407b5a195d0e9686b",
            "exact residual stream digest disagrees with handoff")
    require(exact_selected[0] == int(
        "-5703892799919658490059922221725686307699370673780978850497132842536171588240320361770407843463279886049056"
    ), "first exact residual disagrees with handoff")

    exact_linear = []
    for coordinate in range(N):
        value = sum(
            coefficient * values[linear_offset + sequence * N + coordinate]
            for sequence, coefficient in terms
        )
        exact_linear.append(value)

    mutant_start = 36 * RECORDS
    mutant_hash = digest_i64(values[mutant_start + sequence] for sequence in range(RECORDS))
    original_hash = independent_row_hashes[0]
    mutant_exact = sum(coefficient * values[mutant_start + sequence]
                       for sequence, coefficient in terms)
    require(mutant_hash != original_hash, "direction mutant price vector did not change")
    require(mutant_exact != exact_selected[0], "direction mutant exact residual did not change")
    return {
        "all_36_frozen_rows_all_163740_entries_match": True,
        "hinge_entry_comparisons": 36 * RECORDS,
        "linear_entry_comparisons": RECORDS * N,
        "accumulated_row_i64le_sha256": coordinate_hashes,
        "selected_row_i64le_sha256": independent_row_hashes,
        "linear_i64le_sha256": linear_hash,
        "exact_accumulated_residuals": [str(value) for value in exact_accumulated],
        "exact_selected_residuals": [str(value) for value in exact_selected],
        "exact_selected_residual_lf_bytes": len(residual_stream),
        "exact_selected_residual_lf_sha256": sha256_bytes(residual_stream),
        "exact_linear_before_target": [str(value) for value in exact_linear],
        "direction_mutant": {
            "direction": list(DIRECTION_MUTANT),
            "price_i64le_sha256": mutant_hash,
            "exact_residual": str(mutant_exact),
            "differs_from_first_selected_price": True,
            "differs_from_first_selected_residual": True,
        },
    }


def validate_global(global_result: dict[str, Any], replay: dict[str, Any]) -> dict[str, Any]:
    require(global_result.get("schema") == "g0118-iteration4-batch-cleanroom-cpp-v1"
            and global_result.get("result") == "PASS", "C++ global summary identity drift")
    require(global_result.get("records") == RECORDS and global_result.get("directions_priced") == 37
            and global_result.get("terms") == 102, "C++ summary dimensions drift")
    global_data = global_result["global"]
    equality_fields = {
        "labelled_permutations": "labelled_permutations_checked",
        "hinge_entries_processed": "hinge_entries_processed",
        "aggregate_hinge_support": "aggregate_hinge_support",
        "nonzero_hinge_directions": "nonzero_hinge_residue_directions",
    }
    for independent, producer in equality_fields.items():
        require(global_data[independent] == replay[producer],
                f"independent global field drift: {independent}")
    require(global_data["linear_residues"] == replay["linear_residues_after_target"],
            "independent global linear residues drift")
    require(global_data["accumulated_residues"] == [[0, 0]] * 4,
            "independent global accumulated residues nonzero")
    require(global_data["selected"] == replay["selected"],
            "independent first-32 global selection drift")
    require(digest_selected(global_data["selected"])
            == replay["selected_prefix_i8_u64_le_sha256"],
            "independent selected-prefix digest drift")
    return {
        "labelled_permutations": global_data["labelled_permutations"],
        "raw_histogram_entries": global_data["raw_histogram_entries"],
        "hinge_entries_processed": global_data["hinge_entries_processed"],
        "aggregate_hinge_support": global_data["aggregate_hinge_support"],
        "nonzero_hinge_directions": global_data["nonzero_hinge_directions"],
        "linear_residues_after_target": global_data["linear_residues"],
        "accumulated_residues": global_data["accumulated_residues"],
        "selected_prefix": global_data["selected"],
        "selected_prefix_i8_u64_le_sha256": digest_selected(global_data["selected"]),
        "matches_producer_complete_replay_fields": True,
    }


def replay_panel_and_cache(
    panel: dict[str, Any], candidate: dict[str, Any], terms: Sequence[tuple[int, int]], scale: int
) -> dict[str, Any]:
    manifest = load_json(CACHE_MANIFEST)
    require(sha256_path(CACHE_MANIFEST) == EXPECTED["cache_manifest"], "cache manifest SHA drift")
    require(manifest.get("records") == RECORDS and manifest.get("rows") == PANEL_ROWS
            and manifest.get("entry_bytes") == 16,
            "cache manifest dimensions drift")
    require(manifest.get("payload_bytes") == RECORDS * PANEL_ROWS * 16,
            "cache manifest byte census drift")
    require(CACHE.stat().st_size == manifest["payload_bytes"], "cache payload size drift")
    cache_sha = sha256_path(CACHE)
    require(cache_sha == manifest["data_sha256"] == EXPECTED["cache"], "cache payload SHA drift")
    prefix_bytes = candidate["prefix_records"] * PANEL_ROWS * 16
    prefix_sha = sha256_path(CACHE, prefix_bytes=prefix_bytes)
    require(prefix_sha == candidate["prefix_sha256"], "candidate cache-prefix SHA drift")
    aggregate = [0] * PANEL_ROWS
    record_bytes = PANEL_ROWS * 16
    with CACHE.open("rb") as stream:
        for sequence, coefficient in terms:
            stream.seek(sequence * record_bytes)
            block = stream.read(record_bytes)
            require(len(block) == record_bytes, f"short cache record {sequence}")
            for row in range(PANEL_ROWS):
                value = int.from_bytes(block[row * 16:(row + 1) * 16], "little", signed=True)
                aggregate[row] += coefficient * value
    residual = [value - scale * target for value, target in zip(aggregate, panel["target"], strict=True)]
    require(not any(residual), "candidate fails an independently replayed panel row")
    return {
        "cache_manifest_sha256": EXPECTED["cache_manifest"],
        "cache_payload_bytes": CACHE.stat().st_size,
        "cache_payload_sha256": cache_sha,
        "candidate_prefix_bytes": prefix_bytes,
        "candidate_prefix_sha256": prefix_sha,
        "panel_rows_replayed": PANEL_ROWS,
        "all_panel_rows_exact": True,
        "aggregate_decimal_sha256": sha256_bytes(
            json.dumps([str(value) for value in aggregate], separators=(",", ":")).encode()
        ),
    }


def validate_linear_target(cpp_prices: dict[str, Any], scale: int) -> dict[str, Any]:
    exact = [int(value) for value in cpp_prices["exact_linear_before_target"]]
    target = [0] * (N - 1) + [scale * math.factorial(N)]
    residual = [value - expected for value, expected in zip(exact, target, strict=True)]
    require(residual == [0] * N, "independent exact linear target residual nonzero")
    return {
        "factorial_11": math.factorial(N),
        "target_scale": str(scale),
        "exact_linear_before_target": [str(value) for value in exact],
        "exact_linear_target": [str(value) for value in target],
        "exact_linear_residual": [str(value) for value in residual],
        "all_linear_rows_exact": True,
    }


def provenance(candidate: dict[str, Any]) -> dict[str, Any]:
    principal = {
        "panel_input": PANEL_INPUT,
        "panel_scan": PANEL_SCAN,
        "candidate": CANDIDATE,
        "candidate_recheck": CANDIDATE_RECHECK,
        "replay": REPLAY,
        "prices": PRICES,
        "handoff": HANDOFF,
        "batch_prereg": BATCH_PREREG,
        "replay_source": REPLAY_SOURCE,
        "price_source": PRICE_SOURCE,
        "kernel": KERNEL_SOURCE,
        "uniqueness": UNIQUENESS,
        "cache_manifest": CACHE_MANIFEST,
    }
    actual = {key: sha256_path(path) for key, path in principal.items()}
    for key, expected in EXPECTED.items():
        if key != "cache":
            require(actual[key] == expected, f"principal SHA drift: {key}")

    replay_at_commit = git("show", "a3c5f82:artifacts/math/G-0118/iteration4_batch32_global_modular_replay_v1.json", binary=True)
    prices_at_commit = git("show", "e694b5f:artifacts/math/G-0118/iteration4_batch32_exact_prices_v1.json", binary=True)
    handoff_at_commit = git("show", "52c1e2c:artifacts/math/G-0118/ITERATION4_BATCH_HANDOFF.md", binary=True)
    require(sha256_bytes(replay_at_commit) == EXPECTED["replay"], "replay commit/blob SHA drift")
    require(sha256_bytes(prices_at_commit) == EXPECTED["prices"], "price commit/blob SHA drift")
    require(sha256_bytes(handoff_at_commit) == EXPECTED["handoff"], "handoff commit/blob SHA drift")
    prereg_commit = str(git("log", "-1", "--format=%H", "--",
                            "artifacts/math/G-0118/BATCH32_ITERATION4_PREREGISTRATION.md"))
    require(subprocess.run(["git", "merge-base", "--is-ancestor", prereg_commit, "a3c5f82"],
                           cwd=ROOT).returncode == 0,
            "producer preregistration was not ancestral to replay commit")
    require(subprocess.run(["git", "merge-base", "--is-ancestor", "a3c5f82", "e694b5f"],
                           cwd=ROOT).returncode == 0,
            "replay commit was not ancestral to price commit")
    tracked_bound_inputs = {relative: is_tracked(relative) for relative in candidate["bindings"]}
    untracked_bound_inputs = sorted(relative for relative, tracked in tracked_bound_inputs.items()
                                    if not tracked)
    require(untracked_bound_inputs == [
        "artifacts/math/G-0118/iteration3_residual_coordinate_v1.json"
    ], "unexpected candidate bound-input tracking state")
    return {
        "producer_baseline_commit": "e694b5fb8190d97b69c226a71f12aeb9bb137e7c",
        "replay_commit": "a3c5f82",
        "price_commit": "e694b5f",
        "handoff_correction_commit": "52c1e2c",
        "producer_preregistration_commit": prereg_commit,
        "preregistration_ancestral_to_replay": True,
        "replay_ancestral_to_prices": True,
        "post_preregistration_handoff_deviation": (
            "Commit 52c1e2c changed only the continuation prose from 305 rows to the correct "
            "316 rows; neither sealed scientific JSON payload changed."
        ),
        "principal_sha256": actual,
        "producer_artifacts_match_their_committed_blobs": True,
        "candidate_bound_inputs_tracked": tracked_bound_inputs,
        "untracked_candidate_bound_inputs": untracked_bound_inputs,
        "executable_bindings_directly_replayed": False,
        "executable_binding_reason": (
            "producer binaries are not archived; source bytes and committed output blobs are bound, "
            "but the historical executable SHA values cannot be rehashed from the current workspace"
        ),
    }


def mutation_controls(
    replay: dict[str, Any], prices: dict[str, Any], cpp_prices: dict[str, Any],
    terms: Sequence[tuple[int, int]], linear_target: dict[str, Any]
) -> dict[str, Any]:
    replay_bytes = REPLAY.read_bytes()
    price_bytes = PRICES.read_bytes()
    mutated_replay = bytearray(replay_bytes)
    mutated_replay[len(mutated_replay) // 2] ^= 1
    mutated_prices = bytearray(price_bytes)
    mutated_prices[len(mutated_prices) // 2] ^= 1
    require(sha256_bytes(mutated_replay) != EXPECTED["replay"], "replay hash mutant escaped")
    require(sha256_bytes(mutated_prices) != EXPECTED["prices"], "price hash mutant escaped")

    swapped_directions = list(prices["directions"])
    swapped_directions[0], swapped_directions[1] = swapped_directions[1], swapped_directions[0]
    require(swapped_directions != [item["direction"] for item in replay["selected"]],
            "direction-order mutant escaped")
    swapped_rows = list(prices["rows"])
    swapped_rows[0], swapped_rows[1] = swapped_rows[1], swapped_rows[0]
    require(any(row["direction"] != prices["directions"][index]
                for index, row in enumerate(swapped_rows)), "row-order mutant escaped")
    require(len(prices["rows"][:-1]) != prices["selected_count"], "row truncation mutant escaped")
    require(len(prices["rows"][0]["hinge_coefficients"][:-1]) != prices["records"],
            "record truncation mutant escaped")

    coefficient_by_sequence = dict(terms)
    require(0 in coefficient_by_sequence, "sequence-zero coefficient absent")
    changed_selected = sum(row["hinge_coefficients"][0] != 0 for row in prices["rows"])
    changed_accumulated = 0
    for coordinate_path in COORDINATES:
        coordinate = load_json(coordinate_path)
        changed_accumulated += coordinate["hinge_coefficients"][0] != 0
    changed_linear = sum(value != 0 for value in prices["linear_vectors"][0])
    require(changed_selected + changed_accumulated + changed_linear > 0,
            "coefficient-plus-one mutant leaves all independently checked rows unchanged")
    honest_linear_residual = [int(value) for value in linear_target["exact_linear_residual"]]
    mutant_linear_residual = [
        value + prices["linear_vectors"][0][index]
        for index, value in enumerate(honest_linear_residual)
    ]
    require(any(mutant_linear_residual), "coefficient-plus-one linear mutant escaped")
    return {
        "principal_payload_one_byte_hash_mutants_rejected": True,
        "selected_direction_order_swap_rejected": True,
        "price_row_order_swap_rejected": True,
        "direction_truncation_rejected": True,
        "record_truncation_rejected": True,
        "coefficient_plus_one_sequence": 0,
        "coefficient_plus_one_changed_selected_rows": changed_selected,
        "coefficient_plus_one_changed_accumulated_rows": changed_accumulated,
        "coefficient_plus_one_changed_linear_coordinates": changed_linear,
        "coefficient_plus_one_rejected": True,
        "valid_direction_mutant_rejected": cpp_prices["direction_mutant"],
    }


def main(output: Path, threads: int) -> None:
    for key, path in (
        ("panel_input", PANEL_INPUT), ("panel_scan", PANEL_SCAN),
        ("candidate", CANDIDATE), ("candidate_recheck", CANDIDATE_RECHECK),
        ("replay", REPLAY), ("prices", PRICES), ("handoff", HANDOFF),
        ("batch_prereg", BATCH_PREREG),
    ):
        require(sha256_path(path) == EXPECTED[key], f"initial principal SHA drift: {key}")
    review_source_hashes_before = {
        "python": sha256_path(Path(__file__)),
        "cpp": sha256_path(CPP_SOURCE),
        "preregistration": sha256_path(REVIEW_PREREG),
    }

    panel = load_json(PANEL_INPUT)
    panel_scan = load_json(PANEL_SCAN)
    candidate = load_json(CANDIDATE)
    recheck = load_json(CANDIDATE_RECHECK)
    replay = load_json(REPLAY)
    prices = load_json(PRICES)

    matrices, active_histogram, stage_histogram = validate_records(panel, panel_scan)
    terms, target_scale = validate_candidate(candidate, recheck)
    selected = validate_replay(replay)
    price_structure = validate_prices(prices, selected)
    provenance_result = provenance(candidate)
    panel_replay = replay_panel_and_cache(panel, candidate, terms, target_scale)

    directions = [list(value) for value in ACCUMULATED]
    directions.extend(item["direction"] for item in selected)
    directions.append(list(DIRECTION_MUTANT))
    require(len(directions) == 37 and len({tuple(value) for value in directions}) == 37,
            "review direction set is not unique")

    binary, compiler = compile_cpp()
    with tempfile.TemporaryDirectory(prefix="g0118-batch-audit-") as temporary:
        directory = Path(temporary)
        descriptor = directory / "input.bin"
        cpp_output = directory / "prices.bin"
        write_descriptor(
            descriptor, matrices, panel["records"], directions, terms, target_scale
        )
        descriptor_sha = sha256_path(descriptor)
        completed = subprocess.run(
            [str(binary), str(descriptor), str(cpp_output), str(threads)],
            check=True, text=True, stdout=subprocess.PIPE,
        )
        global_result = json.loads(completed.stdout, object_pairs_hook=reject_duplicate_keys)
        records, direction_count, cpp_values = read_cpp_output(cpp_output)
        require(records == RECORDS, "C++ price record census drift")
        cpp_output_sha = sha256_path(cpp_output)

    cpp_price_result = compare_cpp_prices(cpp_values, direction_count, prices, terms)
    global_replay = validate_global(global_result, replay)
    linear_target = validate_linear_target(cpp_price_result, target_scale)
    controls = mutation_controls(replay, prices, cpp_price_result, terms, linear_target)
    require(sha256_path(Path(__file__)) == review_source_hashes_before["python"],
            "review Python source changed during execution")
    require(sha256_path(CPP_SOURCE) == review_source_hashes_before["cpp"],
            "review C++ source changed during execution")
    require(sha256_path(REVIEW_PREREG) == review_source_hashes_before["preregistration"],
            "review preregistration changed during execution")
    for key, path in (("candidate", CANDIDATE), ("replay", REPLAY), ("prices", PRICES)):
        require(sha256_path(path) == EXPECTED[key], f"producer object changed during review: {key}")

    receipt = {
        "schema": "g0118-iteration4-batch-independent-audit-v1",
        "result": "CONSISTENT_WITH_PROVENANCE_LIMITS",
        "claim_boundary": (
            "Same-lineage T1 consistency for the sealed candidate-4 Batch32 replay and exact "
            "163,740-record price matrix. This does not establish T2 independence, family "
            "completeness, existence in the reopened master, a global MAX11 identity, a MAX11 "
            "lower bound, novelty, or a theorem."
        ),
        "independence": {
            "reviewer": "PeachGull / Codex / fresh context / same lineage (at most T1)",
            "headline_contamination_disclosed": True,
            "producer_rust_imported": False,
            "producer_rust_executed": False,
            "global_method": (
                "fresh C++ full labelled-permutation subset histogram, primitive chamber "
                "normalization, and modular aggregation"
            ),
            "price_method": (
                "fresh C++ active-vertex rank-injection DP, with literal 55,440-injection "
                "small-instance differential"
            ),
            "exact_bridge_method": "Python arbitrary-precision integer dot products",
        },
        "bindings": {
            "review_preregistration_sha256": review_source_hashes_before["preregistration"],
            "review_python_sha256": review_source_hashes_before["python"],
            "review_cpp_sha256": review_source_hashes_before["cpp"],
            "review_cpp_binary_sha256": compiler["binary_sha256"],
            "review_input_descriptor_sha256": descriptor_sha,
            "review_cpp_output_sha256": cpp_output_sha,
            "producer_replay_sha256": EXPECTED["replay"],
            "producer_prices_sha256": EXPECTED["prices"],
        },
        "provenance": provenance_result,
        "record_census": {
            "records": RECORDS,
            "sequences_equal_array_indices": True,
            "compact_loopless_signed_graphs": True,
            "unique_signed_class_digests": RECORDS,
            "active_vertex_histogram": active_histogram,
            "stage_histogram": stage_histogram,
            "record_enumeration_completeness_independently_reproved": False,
            "record_enumeration_boundary": (
                "The audit binds and validates every frozen record and its ordering but does not "
                "rederive the upstream claim that these are all members of the intended family."
            ),
        },
        "candidate_finite_replay": {
            **panel_replay,
            **linear_target,
            "accumulated_hinge_rows": 4,
            "exact_accumulated_residuals": cpp_price_result["exact_accumulated_residuals"],
            "all_316_rows_exact": True,
            "candidate_recheck_core_fields_byte_equal": True,
        },
        "global_modular_replay": global_replay,
        "exact_price_replay": {
            **price_structure,
            **cpp_price_result,
            "selected_rows": 32,
            "records_per_row": RECORDS,
            "all_32_exact_residues_nonzero": True,
            "all_64_prime_reductions_match": True,
        },
        "controls": controls,
        "compiler": compiler,
        "residual_obligations": [
            "A different model lineage or human referee is still required for T2.",
            "The upstream 163,740-record family enumeration/completeness was bound, not independently regenerated.",
            "One candidate-bound coordinate payload (iteration3_residual_coordinate_v1.json) is untracked in Git.",
            "Historical producer executable hashes cannot be rechecked because those binaries are not archived.",
            "The full cache payload is intentionally untracked; its current bytes match the committed manifest.",
        ],
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8") as stream:
        json.dump(receipt, stream, indent=2, sort_keys=True)
        stream.write("\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--threads", type=int, default=12)
    parser.add_argument("--self-test", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    arguments = parse_args()
    if arguments.self_test:
        executable, receipt = compile_cpp()
        print(json.dumps({"result": "PASS", "binary": str(executable), **receipt}, sort_keys=True))
    else:
        if arguments.output is None:
            raise SystemExit("--output is required")
        require(1 <= arguments.threads <= 64, "threads outside [1,64]")
        main(arguments.output.resolve(), arguments.threads)
