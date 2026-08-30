#!/usr/bin/env python3
"""Nested exact four-level augmented-rank gate for the frozen Y-spoke family.

Only a full 8,108-column modular rank is theorem-bearing.  Every deficient
direct matrix is explicitly inconclusive and is retained only for
construction-side constraint generation.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import importlib.util
import json
from math import comb, factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Sequence

import flint
from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
G0074_SCRIPT = ROOT / "artifacts/math/G-0074/farey_three_level_gate.py"
G0074_PREFLIGHT = ROOT / "artifacts/math/G-0074/farey_three_level_preflight_v1.json.gz"
G0074_OUTCOME = ROOT / "artifacts/math/G-0074/farey_three_level_gate_v1.json.gz"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"

SCHEMA = "max11-g0075-four-level-augmented-rank-gate-v1"
PREFLIGHT_SCHEMA = "max11-g0075-four-level-augmented-rank-preflight-v1"
N = 11
DENOMINATOR = 257
PANEL_COUNT = 128
TRANCHES = (64, 128)
PANEL_SEED = "max11-g0075-genuinely-four-valued-panels-v1"
PRIMES = (1_000_003, 1_000_033, 1_000_037)
EXPECTED_COLUMNS = 8_107
EXPECTED_AUGMENTED_COLUMNS = 8_108
EXPECTED_G0074_RANK = 460
EXPECTED_G0074_SCRIPT_SHA256 = (
    "269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d"
)
EXPECTED_G0074_PREFLIGHT_SHA256 = (
    "a89e5b9a2366fb1d119981a49de2c72b8686255e0e522f7ce2ba0af829c26969"
)
EXPECTED_G0074_PREFLIGHT_SCIENTIFIC_SHA256 = (
    "fc166ac93a268c54c85c9e15f43fcd9c0cfba16b3ebb4d3c3951df39c3c188df"
)
EXPECTED_G0074_OUTCOME_SHA256 = (
    "5de36fa1cf39d8524577cdc681b68220c9e807670aef7b14595e8b380bcd4fcb"
)
EXPECTED_G0074_OUTCOME_SCIENTIFIC_SHA256 = (
    "1d56ed5afb9cf9dfcc602c43b34a215790066ebb3041087957db955a5476741c"
)
EXPECTED_G0074_MATRIX_SHA256 = (
    "2521811babdf42205cc6ba49d7315666b6e7c8414a45e3ff0949b2445774f5c0"
)
EXPECTED_G0074_TARGET_SHA256 = (
    "4aed6fcf1f8a41b9e5919f418e0ad887af4516cd4056b6dbb5181c415e5af301"
)
EXPECTED_G0074_PIVOT_ROWS_SHA256 = (
    "ae2c251e791268b1fe42107cf82e44442dbd8e050eb368e35e19115d644cd8e2"
)

# Filled only after the subject/control preflight is frozen and reviewed.
EXPECTED_ENVIRONMENT_SHA256: str | None = (
    "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c"
)
EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256: str | None = (
    "74aca0d8898174800df31576d311122b930a77ea708dd1fdc1241ca34b2598e4"
)
EXPECTED_PANEL_MANIFEST_SHA256: str | None = (
    "b44d1542dfc96fa8180ace56dbefdede9cf30a6fbb0882c71075c04660b2e124"
)
EXPECTED_G0074_PIVOT_ROW_LIST_SHA256: str | None = (
    "ae2c251e791268b1fe42107cf82e44442dbd8e050eb368e35e19115d644cd8e2"
)


class GateError(RuntimeError):
    """A frozen binding, semantic control, or certificate contract failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def read_gzip(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise GateError(f"malformed JSON object: {path}")
    return document


def write_gzip(path: Path, document: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(document))


def load_frozen_g0074() -> ModuleType:
    observed = sha256_path(G0074_SCRIPT)
    if observed != EXPECTED_G0074_SCRIPT_SHA256:
        raise GateError(f"G-0074 producer drift: {observed}")
    name = "g0074_frozen_for_g0075"
    specification = importlib.util.spec_from_file_location(name, G0074_SCRIPT)
    if specification is None or specification.loader is None:
        raise GateError("could not construct G-0074 import specification")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


G74 = load_frozen_g0074()
G73 = G74.G73


def verify_bindings(*, require_environment: bool) -> dict[str, dict[str, object]]:
    expected: dict[str, tuple[Path, str | None]] = {
        "g0074_producer": (G0074_SCRIPT, EXPECTED_G0074_SCRIPT_SHA256),
        "g0074_preflight": (G0074_PREFLIGHT, EXPECTED_G0074_PREFLIGHT_SHA256),
        "g0074_outcome": (G0074_OUTCOME, EXPECTED_G0074_OUTCOME_SHA256),
    }
    if require_environment:
        expected["environment_manifest"] = (
            ENVIRONMENT_MANIFEST,
            EXPECTED_ENVIRONMENT_SHA256,
        )
    bindings: dict[str, dict[str, object]] = {}
    for name, (path, wanted) in expected.items():
        if wanted is None:
            raise GateError(f"binding {name} is not frozen")
        observed = sha256_path(path)
        if observed != wanted:
            raise GateError(f"binding drift for {name}: {observed} != {wanted}")
        bindings[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    preflight = read_gzip(G0074_PREFLIGHT)
    outcome = read_gzip(G0074_OUTCOME)
    if (
        preflight.get("scientific_payload_sha256")
        != EXPECTED_G0074_PREFLIGHT_SCIENTIFIC_SHA256
    ):
        raise GateError("G-0074 preflight scientific payload drift")
    if (
        outcome.get("scientific_payload_sha256")
        != EXPECTED_G0074_OUTCOME_SCIENTIFIC_SHA256
    ):
        raise GateError("G-0074 outcome scientific payload drift")
    matrix = outcome.get("matrix")
    decision = outcome.get("decision")
    if not isinstance(matrix, dict) or not isinstance(decision, dict):
        raise GateError("malformed G-0074 registered outcome")
    if (
        matrix.get("combined_matrix_int64_c_sha256") != EXPECTED_G0074_MATRIX_SHA256
        or matrix.get("combined_target_int64_c_sha256") != EXPECTED_G0074_TARGET_SHA256
        or decision.get("result") != "FAREY_GATE_EXACT_Q_MEMBERSHIP"
    ):
        raise GateError("G-0074 outcome decision or matrix drift")
    return bindings


def positive_profiles() -> list[tuple[int, int, int, int]]:
    profiles = [
        (c0, c1, c2, N - c0 - c1 - c2)
        for c0 in range(1, N - 2)
        for c1 in range(1, N - c0 - 1)
        for c2 in range(1, N - c0 - c1)
        if N - c0 - c1 - c2 >= 1
    ]
    if len(profiles) != comb(N - 1, 3):
        raise GateError("positive four-colour profile census drift")
    return profiles


def missing_profiles() -> list[tuple[int, int, int, int]]:
    profiles = [profile for profile in G73.all_profiles() if 0 in profile]
    if len(profiles) != 364 - 120:
        raise GateError("missing-colour profile census drift")
    return profiles


def assignment_count(profile: Sequence[int]) -> int:
    result = factorial(sum(profile))
    for count in profile:
        result //= factorial(count)
    return result


def panel_ratios() -> list[tuple[int, int]]:
    ratios: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    counter = 0
    while len(ratios) < PANEL_COUNT:
        digest = hashlib.sha256(
            f"{PANEL_SEED};panel={counter}\n".encode()
        ).digest()
        first = 1 + int.from_bytes(digest[:8], "big") % (DENOMINATOR - 1)
        second = 1 + int.from_bytes(digest[8:16], "big") % (DENOMINATOR - 1)
        counter += 1
        if first == second:
            continue
        ratio = tuple(sorted((first, second)))
        if ratio in seen:
            continue
        seen.add(ratio)
        ratios.append(ratio)
    return ratios


def row_descriptor(panel: int, ratio: tuple[int, int], profile: Sequence[int]) -> dict[str, object]:
    return {
        "kind": "genuinely-four-valued-profile",
        "panel": panel,
        "levels": [0, ratio[0], ratio[1], DENOMINATOR],
        "counts": list(map(int, profile)),
    }


_WORKER_BASES: Sequence[object] | None = None
_WORKER_REPRESENTATIVES: Sequence[object] | None = None
_WORKER_GROUPED: Sequence[Sequence[tuple[int, object]]] | None = None


def initialize_worker(bases: Sequence[object], representatives: Sequence[object]) -> None:
    global _WORKER_BASES, _WORKER_REPRESENTATIVES, _WORKER_GROUPED
    _WORKER_BASES = bases
    _WORKER_REPRESENTATIVES = representatives
    _WORKER_GROUPED = G73.group_by_base(representatives, len(bases))


def mapped_assignments(profile: tuple[int, int, int, int], ratio: tuple[int, int]) -> np.ndarray:
    codes = G73.assignments(profile)
    lookup = np.asarray((0, ratio[0], ratio[1], DENOMINATOR), dtype=np.int16)
    levels = lookup[codes]
    if levels.shape != (N, assignment_count(profile)):
        raise GateError("mapped assignment shape drift")
    return levels


def evaluate_columns_grouped(levels: np.ndarray) -> np.ndarray:
    if _WORKER_BASES is None or _WORKER_REPRESENTATIVES is None or _WORKER_GROUPED is None:
        raise GateError("panel worker was not initialized")
    row = np.zeros(len(_WORKER_REPRESENTATIVES) + 3, dtype=np.int64)
    for base in _WORKER_BASES:
        entries = _WORKER_GROUPED[base.position]
        if not entries:
            continue
        columns = np.asarray([column for column, _seed in entries], dtype=np.intp)
        values = G73.evaluate_seed_block(
            base, [seed for _column, seed in entries], levels
        )
        row[columns] = values.sum(axis=1, dtype=np.int64)
    offset = len(_WORKER_REPRESENTATIVES)
    row[offset] = levels[0].sum(dtype=np.int64)
    row[offset + 1] = np.maximum(levels[0], levels[1]).sum(dtype=np.int64)
    row[offset + 2] = np.maximum(2 * levels[0], levels[1] + levels[2]).sum(
        dtype=np.int64
    )
    return row


def evaluate_panel(task: tuple[int, tuple[int, int]]) -> tuple[int, np.ndarray, np.ndarray]:
    panel, ratio = task
    profiles = positive_profiles()
    matrix = np.zeros((len(profiles), EXPECTED_COLUMNS), dtype=np.int64)
    target = np.zeros(len(profiles), dtype=np.int64)
    for row, profile in enumerate(profiles):
        levels = mapped_assignments(profile, ratio)
        matrix[row] = evaluate_columns_grouped(levels)
        target[row] = levels.shape[1] * DENOMINATOR
    return panel, matrix, target


def reconstruct_g0074_pivots(
    bases: Sequence[object], representatives: Sequence[object], workers: int, profile_budget: int
) -> tuple[np.ndarray, np.ndarray, list[int], dict[str, object]]:
    matrix, target, report = G74.build_combined_matrix(
        bases, representatives, workers, profile_budget
    )
    if (
        report.get("combined_matrix_int64_c_sha256") != EXPECTED_G0074_MATRIX_SHA256
        or report.get("combined_target_int64_c_sha256") != EXPECTED_G0074_TARGET_SHA256
    ):
        raise GateError("reconstructed G-0074 matrix drift")
    diagnostic = G74.modular_analysis(matrix, target, PRIMES[0])
    pivot_rows = list(map(int, diagnostic["pivot_rows"]))
    if (
        int(diagnostic["column_rank"]) != EXPECTED_G0074_RANK
        or int(diagnostic["augmented_rank"]) != EXPECTED_G0074_RANK
        or diagnostic["pivot_rows_sha256"] != EXPECTED_G0074_PIVOT_ROWS_SHA256
        or len(pivot_rows) != EXPECTED_G0074_RANK
    ):
        raise GateError("G-0074 pivot-row reconstruction drift")
    selected_matrix = np.ascontiguousarray(matrix[np.asarray(pivot_rows, dtype=np.intp)])
    selected_target = np.ascontiguousarray(target[np.asarray(pivot_rows, dtype=np.intp)])
    selected_augmented = np.column_stack((selected_matrix, selected_target))
    return selected_augmented, matrix, pivot_rows, {
        "rank": EXPECTED_G0074_RANK,
        "pivot_rows": pivot_rows,
        "pivot_rows_sha256": canonical_sha256(pivot_rows),
        "selected_augmented_int64_c_sha256": hashlib.sha256(
            selected_augmented.tobytes(order="C")
        ).hexdigest(),
    }


def direct_panel_rows(
    bases: Sequence[object], representatives: Sequence[object], ratio: tuple[int, int], profiles: Sequence[tuple[int, int, int, int]]
) -> tuple[np.ndarray, np.ndarray]:
    initialize_worker(bases, representatives)
    matrix = np.zeros((len(profiles), EXPECTED_COLUMNS), dtype=np.int64)
    target = np.zeros(len(profiles), dtype=np.int64)
    lookup = np.asarray((0, ratio[0], ratio[1], DENOMINATOR), dtype=np.int16)
    for row, profile in enumerate(profiles):
        levels = lookup[G73.assignments(profile)]
        matrix[row] = evaluate_columns_grouped(levels)
        highest = max(lookup[index] for index, count in enumerate(profile) if count)
        target[row] = levels.shape[1] * int(highest)
    return matrix, target


def missing_profile_reduction_control(
    bases: Sequence[object], representatives: Sequence[object]
) -> dict[str, object]:
    # Check every missing-colour count type on two deterministic generic panels.
    panels = panel_ratios()[:2]
    profiles = missing_profiles()
    degrees = np.asarray([6] * (EXPECTED_COLUMNS - 3) + [1, 1, 2], dtype=np.int64)
    checks = 0
    for ratio in panels:
        direct_matrix, direct_target = direct_panel_rows(
            bases, representatives, ratio, profiles
        )
        panel_cache: dict[tuple[int, int], tuple[np.ndarray, np.ndarray]] = {}
        for row, profile in enumerate(profiles):
            occupied = [index for index, count in enumerate(profile) if count]
            physical = [0, ratio[0], ratio[1], DENOMINATOR]
            offset = physical[occupied[0]]
            top = physical[occupied[-1]]
            if len(occupied) == 1:
                normalized = (0, 1)
                middle_counts = (profile[occupied[0]], 0, 0)
                scale = 0
            elif len(occupied) == 2:
                normalized = (0, top - offset)
                middle_counts = (profile[occupied[0]], 0, profile[occupied[1]])
                scale = top - offset
            else:
                normalized = (
                    physical[occupied[1]] - offset,
                    top - offset,
                )
                middle_counts = (
                    profile[occupied[0]],
                    profile[occupied[1]],
                    profile[occupied[2]],
                )
                scale = top - offset
            if len(occupied) == 1:
                predicted = degrees * offset * assignment_count(profile)
                predicted_target = offset * assignment_count(profile)
            else:
                key = normalized
                if key not in panel_cache:
                    _index, matrix3, target3 = G74.evaluate_ratio_panel(
                        0,
                        normalized[0],
                        normalized[1],
                        bases,
                        representatives,
                    )
                    panel_cache[key] = matrix3, target3
                matrix3, target3 = panel_cache[key]
                index3 = G74.all_three_profiles().index(tuple(middle_counts))
                predicted = matrix3[index3] + degrees * offset * assignment_count(profile)
                predicted_target = int(target3[index3]) + offset * assignment_count(profile)
                if scale != normalized[1]:
                    raise GateError("missing-colour scale bookkeeping drift")
            if not np.array_equal(direct_matrix[row], predicted):
                raise GateError(f"missing-colour row reduction failed: {ratio}, {profile}")
            if int(direct_target[row]) != int(predicted_target):
                raise GateError("missing-colour target reduction failed")
            checks += 1
    return {
        "panels_checked": len(panels),
        "missing_profiles_per_panel": len(profiles),
        "all_8107_column_rows_checked": checks,
        "shift_degrees": {"Y_spoke": 6, "C_L": 1, "C_E": 1, "C_Y": 2, "target": 1},
        "exact_integer_reduction": True,
    }


def run_controls(bases: Sequence[object], representatives: Sequence[object]) -> dict[str, object]:
    profiles = positive_profiles()
    ratios = panel_ratios()
    if len(set(ratios)) != PANEL_COUNT or not all(0 < a < b < DENOMINATOR for a, b in ratios):
        raise GateError("panel manifest is not unique and strictly interior")
    if sum(assignment_count(profile) for profile in profiles) != 3_498_000:
        raise GateError("positive-profile assignment census drift")
    if len(missing_profiles()) != 244:
        raise GateError("missing-profile census drift")
    if EXPECTED_G0074_RANK + 32 * len(profiles) >= EXPECTED_AUGMENTED_COLUMNS:
        raise GateError("32-panel impossibility control failed")
    if EXPECTED_G0074_RANK + 64 * len(profiles) < EXPECTED_AUGMENTED_COLUMNS:
        raise GateError("64-panel row-floor control failed")

    # Vectorized semantics against literal expressions on deterministic small slices.
    initialize_worker(bases, representatives)
    literal_checks = 0
    ratio = ratios[0]
    for profile in profiles[::37]:
        levels = mapped_assignments(profile, ratio)
        vector = evaluate_columns_grouped(levels)
        for column in range(0, min(64, len(representatives)), 11):
            expression = representatives[column].expression
            literal = sum(
                int(G73.evaluate_expression(expression, levels[:, index]))
                for index in range(levels.shape[1])
            )
            if literal != int(vector[column]):
                raise GateError("literal/vectorized four-level semantic control failed")
            literal_checks += 1

    descriptors = [row_descriptor(0, ratios[0], profile) for profile in profiles]
    if len({canonical_sha256(item) for item in descriptors}) != len(profiles):
        raise GateError("direct source-row descriptors are not unique")
    mutated = [{**item, "panel": 1} for item in descriptors]
    if canonical_sha256(descriptors) == canonical_sha256(mutated):
        raise GateError("source-row descriptor mutation was not detected")

    square = np.asarray([[1, 2], [3, 5]], dtype=np.int64)
    if int(nmod_mat(square.tolist(), PRIMES[0]).det()) % PRIMES[0] == 0:
        raise GateError("nonzero modular determinant control failed")
    singular = square.copy()
    singular[1] = 3 * singular[0]
    if int(nmod_mat(singular.tolist(), PRIMES[0]).det()) % PRIMES[0] != 0:
        raise GateError("singular determinant mutant control failed")

    max_assignments = max(map(assignment_count, profiles))
    max_source_entry_bound = 6 * DENOMINATOR * max_assignments
    if max_source_entry_bound >= 2**63:
        raise GateError("int64 source-entry overflow bound failed")
    missing = missing_profile_reduction_control(bases, representatives)
    return {
        "positive_profile_count": len(profiles),
        "positive_profile_assignment_total": 3_498_000,
        "missing_profile_count": len(missing_profiles()),
        "minimum_decisive_panel_count": 64,
        "thirty_two_panels_provably_insufficient": True,
        "nested_tranches": list(TRANCHES),
        "literal_vectorized_checks": literal_checks,
        "direct_row_descriptors_unique": True,
        "source_row_descriptor_mutant_rejected": True,
        "modular_determinant_controls": True,
        "maximum_assignment_count": max_assignments,
        "maximum_source_entry_bound": max_source_entry_bound,
        "int64_overflow_excluded": True,
        "missing_colour_reduction": missing,
    }


def build_preflight(
    *, workers: int, profile_budget: int, require_environment: bool
) -> tuple[Sequence[object], Sequence[object], dict[str, object]]:
    bindings = verify_bindings(require_environment=require_environment)
    bases, _seeds, representatives, upstream = G74.build_preflight(verify_vf2=False)
    G74.enforce_frozen_preflight(upstream)
    if len(representatives) != 8_104:
        raise GateError("G-0074 orbit census drift")
    controls = run_controls(bases, representatives)
    selected, _matrix, pivot_rows, pivot_report = reconstruct_g0074_pivots(
        bases, representatives, workers, profile_budget
    )
    if selected.shape != (EXPECTED_G0074_RANK, EXPECTED_AUGMENTED_COLUMNS):
        raise GateError("G-0074 selected augmented shape drift")
    ratios = panel_ratios()
    profiles = positive_profiles()
    panels = [
        {"panel": index, "levels": [0, a, b, DENOMINATOR]}
        for index, (a, b) in enumerate(ratios)
    ]
    subject = {
        "orbit_columns": len(representatives),
        "carrier_columns": ["C_L", "C_E", "C_Y"],
        "columns": EXPECTED_COLUMNS,
        "augmented_columns": EXPECTED_AUGMENTED_COLUMNS,
        "positive_profiles_per_panel": len(profiles),
        "positive_profile_manifest_sha256": canonical_sha256(profiles),
        "panels": panels,
        "panel_manifest_sha256": canonical_sha256(panels),
        "nested_tranches": list(TRANCHES),
        "source_rows_by_tranche": {
            str(count): EXPECTED_G0074_RANK + count * len(profiles)
            for count in TRANCHES
        },
        "panel_seed": PANEL_SEED,
        "row_compression": "none",
        "unsketched_g0074_pivot_rows": EXPECTED_G0074_RANK,
        "g0074_pivot_row_list_sha256": canonical_sha256(pivot_rows),
        "decision_rule": (
            "only modular rank 8108 of the complete augmented integer matrix is decisive; "
            "it yields a nonzero integer minor and exact Q/R nonmembership of the target in "
            "the frozen family. Every deficient direct matrix is inconclusive"
        ),
    }
    scientific = {
        "schema": PREFLIGHT_SCHEMA,
        "bindings": bindings,
        "controls": controls,
        "g0074_pivot_rows": pivot_report,
        "subject": subject,
    }
    report = {
        **scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "script_sha256": sha256_path(SCRIPT),
        "environment": {
            "python": sys.version,
            "platform": platform.platform(),
            "numpy": np.__version__,
            "python_flint": getattr(flint, "__version__", "unknown"),
        },
        "claim_boundary": (
            "Preflight freezes a one-sided exact family gate. It views no four-level rank "
            "outcome and asserts no MAX11 construction or unrestricted lower bound."
        ),
    }
    return bases, representatives, report


def enforce_frozen_preflight(report: dict[str, object]) -> None:
    subject = report.get("subject")
    pivot = report.get("g0074_pivot_rows")
    if not isinstance(subject, dict) or not isinstance(pivot, dict):
        raise GateError("malformed G-0075 preflight")
    observed = (
        report.get("scientific_payload_sha256"),
        subject.get("panel_manifest_sha256"),
        subject.get("g0074_pivot_row_list_sha256"),
    )
    expected = (
        EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256,
        EXPECTED_PANEL_MANIFEST_SHA256,
        EXPECTED_G0074_PIVOT_ROW_LIST_SHA256,
    )
    if None in expected or observed != expected:
        raise GateError(f"frozen G-0075 preflight drift: {observed} != {expected}")


def build_panel_rows(
    *,
    bases: Sequence[object],
    representatives: Sequence[object],
    workers: int,
    start_panel: int,
    stop_panel: int,
    initial_rows: np.ndarray | None,
    initial_digest: hashlib._Hash | None,
) -> tuple[np.ndarray, hashlib._Hash, list[dict[str, object]], float]:
    begun = time.perf_counter()
    ratios = panel_ratios()
    profiles = positive_profiles()
    expected_initial_rows = start_panel * len(profiles)
    if initial_rows is None:
        if expected_initial_rows != 0:
            raise GateError("nonzero panel start requires prior direct rows")
        rows = np.empty(
            (stop_panel * len(profiles), EXPECTED_AUGMENTED_COLUMNS),
            dtype=np.int64,
        )
    else:
        if initial_rows.shape != (
            expected_initial_rows,
            EXPECTED_AUGMENTED_COLUMNS,
        ):
            raise GateError("prior direct-row tranche shape drift")
        rows = np.empty(
            (stop_panel * len(profiles), EXPECTED_AUGMENTED_COLUMNS),
            dtype=np.int64,
        )
        rows[:expected_initial_rows] = initial_rows
    digest = hashlib.sha256() if initial_digest is None else initial_digest.copy()
    panel_reports: list[dict[str, object]] = []
    context = mp.get_context("fork")
    with ProcessPoolExecutor(
        max_workers=workers,
        mp_context=context,
        initializer=initialize_worker,
        initargs=(bases, representatives),
    ) as pool:
        tasks = [(panel, ratios[panel]) for panel in range(start_panel, stop_panel)]
        for expected_panel, result in zip(
            range(start_panel, stop_panel), pool.map(evaluate_panel, tasks), strict=True
        ):
            panel, matrix, target = result
            if panel != expected_panel or matrix.shape != (len(profiles), EXPECTED_COLUMNS):
                raise GateError("panel output order or shape drift")
            augmented = np.column_stack((matrix, target))
            matrix_sha = hashlib.sha256(matrix.tobytes(order="C")).hexdigest()
            target_sha = hashlib.sha256(target.tobytes(order="C")).hexdigest()
            digest.update(matrix.tobytes(order="C"))
            digest.update(target.tobytes(order="C"))
            row_start = panel * len(profiles)
            rows[row_start : row_start + len(profiles)] = augmented
            ratio = ratios[panel]
            panel_reports.append(
                {
                    "panel": panel,
                    "levels": [0, ratio[0], ratio[1], DENOMINATOR],
                    "matrix_int64_c_sha256": matrix_sha,
                    "target_int64_c_sha256": target_sha,
                    "maximum_absolute_entry": int(np.max(np.abs(matrix))),
                }
            )
            print(
                f"G0075_PANEL completed={panel + 1}/{stop_panel}",
                file=sys.stderr,
                flush=True,
            )
    return rows, digest, panel_reports, time.perf_counter() - begun


def modular_augmented_analysis(matrix: np.ndarray, prime: int) -> dict[str, object]:
    begun = time.perf_counter()
    if matrix.shape[1] != EXPECTED_AUGMENTED_COLUMNS:
        raise GateError("malformed augmented matrix")
    transposed = nmod_mat(np.ascontiguousarray(matrix.T).tolist(), prime)
    rref, rank_object = transposed.rref()
    augmented_rank = int(rank_object)
    report: dict[str, object] = {
        "prime": prime,
        "augmented_rank": augmented_rank,
        "full_augmented_rank": augmented_rank == EXPECTED_AUGMENTED_COLUMNS,
    }
    if augmented_rank == EXPECTED_AUGMENTED_COLUMNS:
        pivot_rows: list[int] = []
        search_from = 0
        for row in range(EXPECTED_AUGMENTED_COLUMNS):
            pivot = next(
                (
                    column
                    for column in range(search_from, matrix.shape[0])
                    if rref[row, column] != 0
                ),
                None,
            )
            if pivot is None:
                raise GateError("full-rank transpose RREF row lacks pivot")
            pivot_rows.append(pivot)
            search_from = pivot + 1
        square_array = np.ascontiguousarray(
            matrix[np.asarray(pivot_rows, dtype=np.intp)]
        )
        square = nmod_mat(square_array.tolist(), prime)
        determinant = int(square.det()) % prime
        if determinant == 0:
            raise GateError("selected full-rank augmented minor has zero determinant")
        report["exact_integer_obstruction_certificate"] = {
            "selected_row_indices": pivot_rows,
            "selected_row_indices_sha256": canonical_sha256(pivot_rows),
            "square_int64_c_sha256": hashlib.sha256(
                square_array.tobytes(order="C")
            ).hexdigest(),
            "determinant_mod_prime": determinant,
            "nonzero_integer_determinant": True,
            "characteristic_zero_augmented_rank": EXPECTED_AUGMENTED_COLUMNS,
        }
    else:
        report["exact_integer_obstruction_certificate"] = None
    del transposed, rref
    report["seconds"] = time.perf_counter() - begun
    return report


def analyze_tranche(
    *,
    tranche: int,
    source_rows: np.ndarray,
    source_digest: hashlib._Hash,
    panel_reports: Sequence[dict[str, object]],
    g0074_pivots: np.ndarray,
) -> dict[str, object]:
    expected_new_rows = tranche * len(positive_profiles())
    if source_rows.shape != (expected_new_rows, EXPECTED_AUGMENTED_COLUMNS):
        raise GateError("direct source-row tranche shape drift")
    augmented = np.ascontiguousarray(np.vstack((source_rows, g0074_pivots)))
    if augmented.shape != (
        expected_new_rows + EXPECTED_G0074_RANK,
        EXPECTED_AUGMENTED_COLUMNS,
    ):
        raise GateError("tranche augmented shape drift")
    diagnostics: list[dict[str, object]] = []
    decisive = False
    for prime in PRIMES:
        report = modular_augmented_analysis(augmented, prime)
        diagnostics.append(report)
        if report["full_augmented_rank"]:
            decisive = True
            break
    scientific_diagnostics = [
        {key: value for key, value in report.items() if key != "seconds"}
        for report in diagnostics
    ]
    return {
        "tranche_panels": tranche,
        "new_direct_source_rows": expected_new_rows,
        "total_direct_row_span_inputs": (
            EXPECTED_G0074_RANK + tranche * len(positive_profiles())
        ),
        "source_stream_sha256": source_digest.hexdigest(),
        "panel_reports": list(panel_reports),
        "direct_panel_rows_int64_c_sha256": hashlib.sha256(
            source_rows.tobytes(order="C")
        ).hexdigest(),
        "augmented_matrix_int64_c_sha256": hashlib.sha256(
            augmented.tobytes(order="C")
        ).hexdigest(),
        "shape": list(augmented.shape),
        "modular_diagnostics": scientific_diagnostics,
        "rank_seconds": [report["seconds"] for report in diagnostics],
        "decision": (
            "FROZEN_FAMILY_EXACT_QR_NONMEMBERSHIP"
            if decisive
            else "FOUR_LEVEL_DIRECT_GATE_INCONCLUSIVE"
        ),
        "interpretation": (
            "A nonzero modular determinant of an 8108-column integer minor proves exact "
            "Q/R target nonmembership in the frozen 8107-column family."
            if decisive
            else "No full augmented rank was found; direct-matrix deficiency licenses no membership "
            "or nonmembership conclusion."
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(16, os.cpu_count() or 1)))
    parser.add_argument("--profile-budget", type=int, default=600_000)
    parser.add_argument("--expected-script-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    begun = time.perf_counter()
    session_script_sha = sha256_path(SCRIPT)
    if arguments.workers < 1:
        raise GateError("workers must be positive")
    if arguments.output is not None and arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output}")
    if arguments.run:
        if arguments.output is None:
            raise GateError("registered run requires --output")
        if arguments.expected_script_sha256 != session_script_sha:
            raise GateError("registered run requires exact preregistered script SHA-256")
    bases, representatives, preflight = build_preflight(
        workers=arguments.workers,
        profile_budget=arguments.profile_budget,
        require_environment=True,
    )
    if sha256_path(SCRIPT) != session_script_sha:
        raise GateError("G-0075 producer drifted during preflight")
    if preflight.get("script_sha256") != session_script_sha:
        raise GateError("G-0075 preflight recorded the wrong producer")
    verify_bindings(require_environment=True)
    if arguments.self_test:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "mode": "self-test",
                    "controls": preflight["controls"],
                    "subject": preflight["subject"],
                },
                sort_keys=True,
            )
        )
        return
    if arguments.preflight_only:
        if arguments.output is not None:
            write_gzip(arguments.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return

    observed_script = sha256_path(SCRIPT)
    enforce_frozen_preflight(preflight)
    g0074_pivots, _matrix, pivot_rows, pivot_report = reconstruct_g0074_pivots(
        bases, representatives, arguments.workers, arguments.profile_budget
    )
    del _matrix
    if canonical_sha256(pivot_rows) != EXPECTED_G0074_PIVOT_ROW_LIST_SHA256:
        raise GateError("registered G-0074 pivot list drift")

    rows64, digest64, panels64, seconds64 = build_panel_rows(
        bases=bases,
        representatives=representatives,
        workers=arguments.workers,
        start_panel=0,
        stop_panel=64,
        initial_rows=None,
        initial_digest=None,
    )
    result64 = analyze_tranche(
        tranche=64,
        source_rows=rows64,
        source_digest=digest64,
        panel_reports=panels64,
        g0074_pivots=g0074_pivots,
    )
    tranches = [result64]
    generation_seconds = {"64": seconds64}
    if result64["decision"] != "FROZEN_FAMILY_EXACT_QR_NONMEMBERSHIP":
        rows128, digest128, panels128_tail, seconds128_tail = build_panel_rows(
            bases=bases,
            representatives=representatives,
            workers=arguments.workers,
            start_panel=64,
            stop_panel=128,
            initial_rows=rows64,
            initial_digest=digest64,
        )
        del rows64
        result128 = analyze_tranche(
            tranche=128,
            source_rows=rows128,
            source_digest=digest128,
            panel_reports=panels64 + panels128_tail,
            g0074_pivots=g0074_pivots,
        )
        tranches.append(result128)
        generation_seconds["128_tail"] = seconds128_tail

    decisive = next(
        (
            report
            for report in tranches
            if report["decision"] == "FROZEN_FAMILY_EXACT_QR_NONMEMBERSHIP"
        ),
        None,
    )
    scientific_tranches = [
        {key: value for key, value in report.items() if key != "rank_seconds"}
        for report in tranches
    ]
    scientific = {
        "schema": SCHEMA,
        "preflight_scientific_payload_sha256": preflight["scientific_payload_sha256"],
        "subject": preflight["subject"],
        "g0074_pivot_rows": pivot_report,
        "tranches": scientific_tranches,
        "decision": (
            "FROZEN_FAMILY_EXACT_QR_NONMEMBERSHIP"
            if decisive is not None
            else "FOUR_LEVEL_DIRECT_GATE_INCONCLUSIVE"
        ),
    }
    report = {
        **scientific,
        "mode": "registered-run",
        "bindings": preflight["bindings"],
        "controls": preflight["controls"],
        "script_sha256": observed_script,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "generation_seconds": generation_seconds,
        "rank_seconds": {
            str(item["tranche_panels"]): item["rank_seconds"] for item in tranches
        },
        "workers": arguments.workers,
        "wall_seconds": time.perf_counter() - begun,
        "interpretation_boundary": (
            "A decisive outcome rejects only the frozen Y-spoke-plus-carriers family over "
            "real output coefficients. It is not an unrestricted ReLU lower bound. A "
            "deficient outcome is inconclusive and is not a construction."
        ),
    }
    if sha256_path(SCRIPT) != session_script_sha:
        raise GateError("G-0075 producer drifted during registered execution")
    verify_bindings(require_environment=True)
    write_gzip(arguments.output, report)
    print(
        json.dumps(
            {
                "output": str(arguments.output),
                "output_sha256": sha256_path(arguments.output),
                "scientific_payload_sha256": report["scientific_payload_sha256"],
                "decision": scientific["decision"],
                "tranche_diagnostics": [
                    {
                        "tranche": item["tranche_panels"],
                        "decision": item["decision"],
                        "modular_diagnostics": item["modular_diagnostics"],
                    }
                    for item in tranches
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
