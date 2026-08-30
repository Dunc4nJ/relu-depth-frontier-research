#!/usr/bin/env python3
"""Target-aware modular resolver for the surviving G-0075 MAX11 system.

This experiment regenerates every registered G-0075 four-level row, appends
all (not only the selected pivot subset of) G-0074 rows, and computes one
canonical right-kernel quotient over the first registered prime.  Its primary
output is the rank gap epsilon = rank([A|b]) - rank(A).

Neither value of modular epsilon is a characteristic-zero certificate.  Only
a later exact all-row right replay or exact all-column left-dual replay may be
promoted to rational membership or nonmembership.
"""

from __future__ import annotations

import argparse
from concurrent.futures import ProcessPoolExecutor
import gzip
import hashlib
import importlib.util
import json
import multiprocessing as mp
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Iterable, Sequence

import flint
from flint import nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
CACHE_DEFAULT = HERE / "cache"
G0075_SCRIPT = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate.py"
G0075_PREFLIGHT = ROOT / "artifacts/math/G-0075/four_level_preflight_v1.json.gz"
G0075_OUTCOME = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate_v1.json.gz"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"

SCHEMA = "max11-g0076-target-aware-kernel-resolver-v1"
PREFLIGHT_SCHEMA = "max11-g0076-target-aware-kernel-preflight-v1"
CACHE_SCHEMA = "max11-g0076-target-aware-cache-v1"
PRIME = 1_000_003
PANELS = 128
PROFILES_PER_PANEL = 120
OLD_ROWS = 1_378
OLD_PIVOT_ROWS = 460
A_COLUMNS = 8_107
AUGMENTED_COLUMNS = 8_108
DIRECT_ROWS = PANELS * PROFILES_PER_PANEL
TOTAL_ROWS = DIRECT_ROWS + OLD_ROWS
MINIMUM_AVAILABLE_BYTES = 24 * 1024**3
KERNEL_REPLAY_BLOCK = 64

EXPECTED_G0075_SCRIPT_SHA256 = (
    "ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab"
)
EXPECTED_G0075_PREFLIGHT_SHA256 = (
    "bbe4e8410e2d042deea2844aa7099f2601feaa201d903557ca09d5f16f2514e0"
)
EXPECTED_G0075_PREFLIGHT_SCIENTIFIC_SHA256 = (
    "74aca0d8898174800df31576d311122b930a77ea708dd1fdc1241ca34b2598e4"
)
EXPECTED_G0075_OUTCOME_SHA256 = (
    "ec8f1f1213f9105a5aa51d1b842ac2dc331d82224157d598a7caf0af93425371"
)
EXPECTED_G0075_OUTCOME_SCIENTIFIC_SHA256 = (
    "f55f4c23cb14fcf5974e527e4775183420c028fdf9a859f4febeb265405950da"
)
EXPECTED_G0075_DIRECT128_SHA256 = (
    "7f77779fa2fe7cde13d64c4823158d8a0054d524897c570f554e7a51a746cf94"
)
EXPECTED_G0075_SELECTED460_AUGMENTED_SHA256 = (
    "f029fddb62924f2e6739396c58b81fbe7d393bad1b22bdec49819c4fa82a2184"
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
EXPECTED_ENVIRONMENT_SHA256 = (
    "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c"
)

# Filled only after the outcome-blind preflight has been reviewed and frozen.
EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256: str | None = (
    "30252895c2607f5385580b0b0c5ca15f7af30cebc83b054c2e1586e810efaafd"
)


class ResolverError(RuntimeError):
    """A frozen binding, cache invariant, or algebraic contract failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise ResolverError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_array_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def stream_array_sha256(array: np.ndarray, row_block: int = 256) -> str:
    if array.ndim != 2:
        raise ResolverError("stream hash requires a matrix")
    digest = hashlib.sha256()
    for start in range(0, array.shape[0], row_block):
        block = np.ascontiguousarray(array[start : start + row_block])
        digest.update(memoryview(block).cast("B"))
    return digest.hexdigest()


def concatenated_sha256(arrays: Iterable[np.ndarray]) -> str:
    digest = hashlib.sha256()
    for array in arrays:
        contiguous = np.ascontiguousarray(array)
        digest.update(memoryview(contiguous).cast("B"))
    return digest.hexdigest()


def read_gzip(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise ResolverError(f"malformed JSON object: {path}")
    return value


def write_gzip(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(value))


def atomic_write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.unlink(missing_ok=True)
    with temporary.open("xb") as target:
        target.write(canonical_bytes(value))
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def atomic_save_npy(path: Path, array: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.unlink(missing_ok=True)
    with temporary.open("xb") as target:
        np.save(target, np.ascontiguousarray(array), allow_pickle=False)
        target.flush()
        os.fsync(target.fileno())
    os.replace(temporary, path)


def atomic_save_gzip_npy(path: Path, array: np.ndarray) -> dict[str, object]:
    """Persist a deterministic, portable copy of a theorem-relevant array."""
    if path.exists():
        if not path.is_file() or path.is_symlink():
            raise ResolverError(f"invalid archival kernel path: {path}")
        with gzip.open(path, "rb") as source:
            existing = np.load(source, allow_pickle=False)
        if (
            existing.shape != array.shape
            or existing.dtype != array.dtype
            or raw_array_sha256(existing) != raw_array_sha256(array)
        ):
            raise ResolverError(f"archival kernel drift: {path}")
        return {
            "raw_c_sha256": raw_array_sha256(array),
            "gzip_npy_sha256": sha256_path(path),
            "bytes": path.stat().st_size,
        }
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".partial")
    temporary.unlink(missing_ok=True)
    with temporary.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            np.save(zipped, np.ascontiguousarray(array), allow_pickle=False)
        raw.flush()
        os.fsync(raw.fileno())
    os.replace(temporary, path)
    return {
        "raw_c_sha256": raw_array_sha256(array),
        "gzip_npy_sha256": sha256_path(path),
        "bytes": path.stat().st_size,
    }


def load_frozen_g0075() -> ModuleType:
    observed = sha256_path(G0075_SCRIPT)
    if observed != EXPECTED_G0075_SCRIPT_SHA256:
        raise ResolverError(f"G-0075 producer drift: {observed}")
    name = "g0075_frozen_for_g0076"
    specification = importlib.util.spec_from_file_location(name, G0075_SCRIPT)
    if specification is None or specification.loader is None:
        raise ResolverError("could not construct G-0075 import specification")
    module = importlib.util.module_from_spec(specification)
    sys.modules[name] = module
    specification.loader.exec_module(module)
    return module


G75 = load_frozen_g0075()


def verify_bindings() -> tuple[dict[str, dict[str, object]], dict[str, object]]:
    expected = {
        "g0075_producer": (G0075_SCRIPT, EXPECTED_G0075_SCRIPT_SHA256),
        "g0075_preflight": (G0075_PREFLIGHT, EXPECTED_G0075_PREFLIGHT_SHA256),
        "g0075_outcome": (G0075_OUTCOME, EXPECTED_G0075_OUTCOME_SHA256),
        "environment_manifest": (ENVIRONMENT_MANIFEST, EXPECTED_ENVIRONMENT_SHA256),
    }
    bindings: dict[str, dict[str, object]] = {}
    for name, (path, wanted) in expected.items():
        observed = sha256_path(path)
        if observed != wanted:
            raise ResolverError(f"binding drift for {name}: {observed} != {wanted}")
        bindings[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    preflight = read_gzip(G0075_PREFLIGHT)
    outcome = read_gzip(G0075_OUTCOME)
    if (
        preflight.get("scientific_payload_sha256")
        != EXPECTED_G0075_PREFLIGHT_SCIENTIFIC_SHA256
        or outcome.get("scientific_payload_sha256")
        != EXPECTED_G0075_OUTCOME_SCIENTIFIC_SHA256
    ):
        raise ResolverError("G-0075 scientific payload drift")
    if outcome.get("decision") != "FOUR_LEVEL_DIRECT_GATE_INCONCLUSIVE":
        raise ResolverError("G-0075 outcome decision drift")
    tranches = outcome.get("tranches")
    if not isinstance(tranches, list) or len(tranches) != 2:
        raise ResolverError("malformed G-0075 tranche report")
    final = tranches[-1]
    if not isinstance(final, dict):
        raise ResolverError("malformed G-0075 final tranche")
    if (
        final.get("direct_panel_rows_int64_c_sha256")
        != EXPECTED_G0075_DIRECT128_SHA256
        or final.get("augmented_matrix_int64_c_sha256")
        != EXPECTED_G0075_SELECTED460_AUGMENTED_SHA256
        or final.get("shape") != [DIRECT_ROWS + OLD_PIVOT_ROWS, AUGMENTED_COLUMNS]
    ):
        raise ResolverError("G-0075 registered matrix binding drift")
    return bindings, outcome


def final_panel_reports(outcome: dict[str, object]) -> list[dict[str, object]]:
    tranches = outcome["tranches"]
    final = tranches[-1]  # type: ignore[index]
    reports = final.get("panel_reports")  # type: ignore[union-attr]
    if not isinstance(reports, list) or len(reports) != PANELS:
        raise ResolverError("malformed registered panel reports")
    normalized: list[dict[str, object]] = []
    for expected_panel, report in enumerate(reports):
        if not isinstance(report, dict) or report.get("panel") != expected_panel:
            raise ResolverError("registered panel ordering drift")
        normalized.append(report)
    return normalized


def panel_cache_path(cache: Path, panel: int) -> Path:
    return cache / "panels" / f"panel-{panel:03d}.npy"


def validate_panel_array(
    array: np.ndarray, panel: int, report: dict[str, object]
) -> dict[str, object]:
    if array.shape != (PROFILES_PER_PANEL, AUGMENTED_COLUMNS):
        raise ResolverError(f"panel {panel} cache shape drift: {array.shape}")
    if array.dtype != np.dtype(np.int64) or not array.flags.c_contiguous:
        raise ResolverError(f"panel {panel} cache dtype/order drift")
    matrix_sha = raw_array_sha256(array[:, :A_COLUMNS])
    target_sha = raw_array_sha256(array[:, A_COLUMNS])
    if (
        matrix_sha != report.get("matrix_int64_c_sha256")
        or target_sha != report.get("target_int64_c_sha256")
    ):
        raise ResolverError(f"panel {panel} registered hash mismatch")
    return {
        "panel": panel,
        "levels": report.get("levels"),
        "matrix_int64_c_sha256": matrix_sha,
        "target_int64_c_sha256": target_sha,
        "augmented_int64_c_sha256": raw_array_sha256(array),
        "shape": list(array.shape),
    }


def load_panel(cache: Path, panel: int, report: dict[str, object]) -> np.ndarray:
    path = panel_cache_path(cache, panel)
    if not path.is_file() or path.is_symlink():
        raise ResolverError(f"missing regular panel cache: {path}")
    array = np.load(path, mmap_mode="r", allow_pickle=False)
    validate_panel_array(array, panel, report)
    return array


def prepare_subject(
    *, workers: int, profile_budget: int
) -> tuple[Sequence[object], Sequence[object], dict[str, object], dict[str, object]]:
    bindings, outcome = verify_bindings()
    bases, representatives, reconstructed = G75.build_preflight(
        workers=workers,
        profile_budget=profile_budget,
        require_environment=True,
    )
    G75.enforce_frozen_preflight(reconstructed)
    if (
        reconstructed.get("scientific_payload_sha256")
        != EXPECTED_G0075_PREFLIGHT_SCIENTIFIC_SHA256
    ):
        raise ResolverError("reconstructed G-0075 preflight drift")
    return bases, representatives, bindings, outcome


def build_panel_cache(
    *,
    cache: Path,
    bases: Sequence[object],
    representatives: Sequence[object],
    outcome: dict[str, object],
    workers: int,
) -> tuple[list[dict[str, object]], float]:
    begun = time.perf_counter()
    reports = final_panel_reports(outcome)
    missing: list[int] = []
    for panel, report in enumerate(reports):
        path = panel_cache_path(cache, panel)
        if path.exists():
            load_panel(cache, panel, report)
        else:
            missing.append(panel)
    if missing:
        ratios = G75.panel_ratios()
        context = mp.get_context("fork")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=G75.initialize_worker,
            initargs=(bases, representatives),
        ) as pool:
            tasks = [(panel, ratios[panel]) for panel in missing]
            for expected_panel, result in zip(
                missing, pool.map(G75.evaluate_panel, tasks), strict=True
            ):
                panel, matrix, target = result
                if panel != expected_panel:
                    raise ResolverError("panel worker output order drift")
                augmented = np.ascontiguousarray(np.column_stack((matrix, target)))
                validate_panel_array(augmented, panel, reports[panel])
                atomic_save_npy(panel_cache_path(cache, panel), augmented)
                print(
                    f"G0076_CACHE_PANEL completed={panel + 1}/{PANELS}",
                    file=sys.stderr,
                    flush=True,
                )
    cache_reports: list[dict[str, object]] = []
    direct_digest = hashlib.sha256()
    for panel, report in enumerate(reports):
        array = load_panel(cache, panel, report)
        cache_reports.append(validate_panel_array(array, panel, report))
        direct_digest.update(memoryview(np.ascontiguousarray(array)).cast("B"))
    if direct_digest.hexdigest() != EXPECTED_G0075_DIRECT128_SHA256:
        raise ResolverError("complete direct-panel cache hash drift")
    return cache_reports, time.perf_counter() - begun


def build_g0074_cache(
    *,
    cache: Path,
    bases: Sequence[object],
    representatives: Sequence[object],
    outcome: dict[str, object],
    workers: int,
    profile_budget: int,
) -> tuple[np.ndarray, list[int], dict[str, object], float]:
    begun = time.perf_counter()
    path = cache / "g0074-all-rows.npy"
    if path.exists():
        if not path.is_file() or path.is_symlink():
            raise ResolverError("invalid G-0074 cache path")
        augmented = np.load(path, mmap_mode="r", allow_pickle=False)
        if augmented.shape != (OLD_ROWS, AUGMENTED_COLUMNS):
            raise ResolverError("G-0074 cache shape drift")
        matrix_sha = raw_array_sha256(augmented[:, :A_COLUMNS])
        target_sha = raw_array_sha256(augmented[:, A_COLUMNS])
    else:
        matrix, target, report = G75.G74.build_combined_matrix(
            bases, representatives, workers, profile_budget
        )
        matrix_sha = raw_array_sha256(matrix)
        target_sha = raw_array_sha256(target)
        if (
            matrix_sha != report.get("combined_matrix_int64_c_sha256")
            or target_sha != report.get("combined_target_int64_c_sha256")
        ):
            raise ResolverError("reconstructed G-0074 report drift")
        augmented_memory = np.ascontiguousarray(np.column_stack((matrix, target)))
        atomic_save_npy(path, augmented_memory)
        del matrix, target, augmented_memory
        augmented = np.load(path, mmap_mode="r", allow_pickle=False)
    if (
        augmented.dtype != np.dtype(np.int64)
        or not augmented.flags.c_contiguous
        or matrix_sha != EXPECTED_G0074_MATRIX_SHA256
        or target_sha != EXPECTED_G0074_TARGET_SHA256
    ):
        raise ResolverError("G-0074 full-row cache binding drift")
    pivot_report = outcome.get("g0074_pivot_rows")
    if not isinstance(pivot_report, dict):
        raise ResolverError("missing registered G-0074 pivot report")
    pivot_rows = list(map(int, pivot_report.get("pivot_rows", [])))
    if (
        len(pivot_rows) != OLD_PIVOT_ROWS
        or canonical_sha256(pivot_rows) != EXPECTED_G0074_PIVOT_ROWS_SHA256
    ):
        raise ResolverError("registered G-0074 pivot list drift")
    return augmented, pivot_rows, {
        "shape": list(augmented.shape),
        "matrix_int64_c_sha256": matrix_sha,
        "target_int64_c_sha256": target_sha,
        "augmented_int64_c_sha256": raw_array_sha256(augmented),
    }, time.perf_counter() - begun


def build_full_cache(
    *,
    cache: Path,
    outcome: dict[str, object],
    g0074: np.ndarray,
    pivot_rows: Sequence[int],
) -> tuple[np.ndarray, dict[str, object], float]:
    begun = time.perf_counter()
    reports = final_panel_reports(outcome)
    path = cache / "full-N.npy"
    temporary = path.with_name(path.name + ".partial")
    if not path.exists():
        cache.mkdir(parents=True, exist_ok=True)
        temporary.unlink(missing_ok=True)
        full = np.lib.format.open_memmap(
            temporary,
            mode="w+",
            dtype=np.int64,
            shape=(TOTAL_ROWS, AUGMENTED_COLUMNS),
        )
        for panel, report in enumerate(reports):
            block = load_panel(cache, panel, report)
            start = panel * PROFILES_PER_PANEL
            full[start : start + PROFILES_PER_PANEL] = block
        full[DIRECT_ROWS:] = g0074
        full.flush()
        del full
        os.replace(temporary, path)
    if not path.is_file() or path.is_symlink():
        raise ResolverError("invalid full cache path")
    full = np.load(path, mmap_mode="r", allow_pickle=False)
    if (
        full.shape != (TOTAL_ROWS, AUGMENTED_COLUMNS)
        or full.dtype != np.dtype(np.int64)
        or not full.flags.c_contiguous
    ):
        raise ResolverError("full cache shape/dtype/order drift")
    direct_sha = stream_array_sha256(full[:DIRECT_ROWS])
    if direct_sha != EXPECTED_G0075_DIRECT128_SHA256:
        raise ResolverError("full cache direct prefix drift")
    if (
        raw_array_sha256(full[DIRECT_ROWS:, :A_COLUMNS])
        != EXPECTED_G0074_MATRIX_SHA256
        or raw_array_sha256(full[DIRECT_ROWS:, A_COLUMNS])
        != EXPECTED_G0074_TARGET_SHA256
    ):
        raise ResolverError("full cache G-0074 suffix drift")
    selected = np.ascontiguousarray(g0074[np.asarray(pivot_rows, dtype=np.intp)])
    selected_hash = concatenated_sha256((full[:DIRECT_ROWS], selected))
    if selected_hash != EXPECTED_G0075_SELECTED460_AUGMENTED_SHA256:
        raise ResolverError("registered selected-460 projection drift")
    report = {
        "shape": list(full.shape),
        "dtype": full.dtype.str,
        "row_order": "all 128 G-0075 panels in registered order, then all 1,378 G-0074 rows",
        "direct_prefix_int64_c_sha256": direct_sha,
        "g0075_selected460_projection_int64_c_sha256": selected_hash,
        "full_augmented_int64_c_sha256": stream_array_sha256(full),
    }
    return full, report, time.perf_counter() - begun


def available_memory_bytes() -> int:
    for line in Path("/proc/meminfo").read_text(encoding="utf-8").splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise ResolverError("could not read MemAvailable")


def to_nmod(matrix: np.ndarray, prime: int) -> tuple[nmod_mat, np.ndarray]:
    if matrix.ndim != 2:
        raise ResolverError("modular conversion requires a matrix")
    reduced = np.empty(matrix.shape, dtype=np.uint32)
    np.remainder(matrix, prime, out=reduced, casting="unsafe")
    field = nmod_mat(
        reduced.shape[0],
        reduced.shape[1],
        memoryview(reduced.ravel()),
        prime,
    )
    return field, reduced


def nmod_to_numpy(matrix: nmod_mat) -> np.ndarray:
    rows, columns = matrix.nrows(), matrix.ncols()
    if rows == 0 or columns == 0:
        return np.empty((rows, columns), dtype=np.uint32)
    return np.asarray(matrix.entries(), dtype=np.uint32).reshape(rows, columns)


def pivot_coordinates(rref: np.ndarray) -> list[int]:
    pivots: list[int] = []
    search = 0
    for row in rref:
        support = np.flatnonzero(row[search:])
        if support.size == 0:
            raise ResolverError("RREF row lacks a pivot")
        pivot = search + int(support[0])
        pivots.append(pivot)
        search = pivot + 1
    if pivots != sorted(set(pivots)):
        raise ResolverError("invalid RREF pivot sequence")
    return pivots


def canonical_kernel(field: nmod_mat, prime: int) -> tuple[nmod_mat, np.ndarray, int]:
    raw, nullity_object = field.nullspace()
    nullity = int(nullity_object)
    columns = field.ncols()
    raw_rows = np.empty((nullity, columns), dtype=np.uint32)
    for basis in range(nullity):
        raw_rows[basis] = np.fromiter(
            (int(raw[row, basis]) for row in range(columns)),
            dtype=np.uint32,
            count=columns,
        )
    del raw
    raw_field, raw_reduced = to_nmod(raw_rows, prime)
    del raw_rows, raw_reduced
    canonical, rank_object = raw_field.rref()
    rank = int(rank_object)
    del raw_field
    if rank != nullity:
        raise ResolverError("raw kernel basis lost rank during canonicalization")
    array = nmod_to_numpy(canonical)
    if len(pivot_coordinates(array)) != nullity:
        raise ResolverError("canonical kernel RREF check failed")
    return canonical, array, nullity


def derive_a_kernel(
    h_n: np.ndarray, prime: int
) -> tuple[nmod_mat, np.ndarray, int, int]:
    nullity_n, augmented_columns = h_n.shape
    if augmented_columns < 1:
        raise ResolverError("empty augmented coordinate space")
    target = h_n[:, -1]
    target_bearing = np.flatnonzero(target)
    epsilon = 0 if target_bearing.size else 1
    if epsilon == 1:
        candidate = np.ascontiguousarray(h_n[:, :-1])
    else:
        anchor = int(target_bearing[0])
        others = np.asarray(
            [index for index in range(nullity_n) if index != anchor], dtype=np.intp
        )
        anchor_value = int(target[anchor])
        left = anchor_value * h_n[others, :-1].astype(np.int64)
        right = target[others].astype(np.int64)[:, None] * h_n[
            anchor, :-1
        ].astype(np.int64)[None, :]
        candidate = np.ascontiguousarray((left - right) % prime, dtype=np.uint32)
    expected_nullity = nullity_n - (1 if epsilon == 0 else 0)
    candidate_field, candidate_reduced = to_nmod(candidate, prime)
    del candidate, candidate_reduced
    canonical, rank_object = candidate_field.rref()
    rank = int(rank_object)
    del candidate_field
    if rank != expected_nullity:
        raise ResolverError(
            f"derived A-kernel rank drift: {rank} != {expected_nullity}"
        )
    array = nmod_to_numpy(canonical)
    if len(pivot_coordinates(array)) != expected_nullity:
        raise ResolverError("canonical A-kernel RREF check failed")
    return canonical, array, expected_nullity, epsilon


def replay_kernel_blocks(
    field: nmod_mat, h_n: np.ndarray, prime: int, block_size: int
) -> None:
    nullity = h_n.shape[0]
    for start in range(0, nullity, block_size):
        stop = min(start + block_size, nullity)
        block = np.ascontiguousarray(h_n[start:stop].T)
        block_field, reduced = to_nmod(block, prime)
        del block, reduced
        residual = field * block_field
        zero = nmod_mat(residual.nrows(), residual.ncols(), prime)
        if residual != zero:
            raise ResolverError(f"kernel replay failed on columns {start}:{stop}")
        del block_field, residual, zero
        print(
            f"G0076_KERNEL_REPLAY completed={stop}/{nullity}",
            file=sys.stderr,
            flush=True,
        )


def canonical_target_vector(
    h_n: np.ndarray, h_a: np.ndarray, pivots_a: Sequence[int], prime: int
) -> np.ndarray:
    target_rows = np.flatnonzero(h_n[:, -1])
    if target_rows.size == 0:
        raise ResolverError("cannot construct target vector from epsilon-one kernel")
    anchor = int(target_rows[0])
    inverse = pow(int(h_n[anchor, -1]), -1, prime)
    vector = np.ascontiguousarray(
        (-inverse * h_n[anchor].astype(np.int64)) % prime, dtype=np.uint32
    )
    for row, pivot in enumerate(pivots_a):
        coefficient = int(vector[pivot])
        if coefficient:
            vector[:-1] = (
                vector[:-1].astype(np.int64)
                - coefficient * h_a[row].astype(np.int64)
            ) % prime
    if int(vector[-1]) != prime - 1:
        raise ResolverError("target vector normalization drift")
    if any(int(vector[pivot]) for pivot in pivots_a):
        raise ResolverError("target vector was not reduced against ker(A)")
    return vector


def save_kernel_array(cache: Path, name: str, array: np.ndarray) -> dict[str, object]:
    path = cache / "kernels" / name
    if path.exists():
        existing = np.load(path, mmap_mode="r", allow_pickle=False)
        if (
            existing.shape != array.shape
            or existing.dtype != array.dtype
            or raw_array_sha256(existing) != raw_array_sha256(array)
        ):
            raise ResolverError(f"kernel checkpoint drift: {path}")
    else:
        atomic_save_npy(path, array)
    return {
        "shape": list(array.shape),
        "dtype": array.dtype.str,
        "raw_c_sha256": raw_array_sha256(array),
    }


def resolve_full_kernel(
    *,
    cache: Path,
    full: np.ndarray,
    full_report: dict[str, object],
    kernel_output: Path,
) -> tuple[dict[str, object], float]:
    begun = time.perf_counter()
    available = available_memory_bytes()
    if available < MINIMUM_AVAILABLE_BYTES:
        raise ResolverError(
            f"need at least {MINIMUM_AVAILABLE_BYTES} available bytes, observed {available}"
        )
    print(
        f"G0076_NULLSPACE_BEGIN rows={full.shape[0]} columns={full.shape[1]} prime={PRIME}",
        file=sys.stderr,
        flush=True,
    )
    field, reduced = to_nmod(full, PRIME)
    del reduced
    h_n_field, h_n, nullity_n = canonical_kernel(field, PRIME)
    del h_n_field
    rank_n = AUGMENTED_COLUMNS - nullity_n
    h_a_field, h_a, nullity_a, epsilon = derive_a_kernel(h_n, PRIME)
    del h_a_field
    rank_a = A_COLUMNS - nullity_a
    if epsilon != rank_n - rank_a or epsilon not in (0, 1):
        raise ResolverError("rank-gap identity failed")
    replay_kernel_blocks(field, h_n, PRIME, KERNEL_REPLAY_BLOCK)
    pivots_n = pivot_coordinates(h_n)
    pivots_a = pivot_coordinates(h_a)
    target_projection = h_n[:, -1]
    target_support = np.flatnonzero(target_projection).astype(int).tolist()
    h_n_checkpoint = save_kernel_array(cache, f"p{PRIME}-HN.npy", h_n)
    h_a_checkpoint = save_kernel_array(cache, f"p{PRIME}-HA.npy", h_a)
    h_n_checkpoint["archival_copy"] = atomic_save_gzip_npy(kernel_output, h_n)
    target_checkpoint: dict[str, object] | None = None
    if epsilon == 0:
        target_vector = canonical_target_vector(h_n, h_a, pivots_a, PRIME)
        vector_field, vector_reduced = to_nmod(target_vector.reshape(-1, 1), PRIME)
        del vector_reduced
        residual = field * vector_field
        if residual != nmod_mat(TOTAL_ROWS, 1, PRIME):
            raise ResolverError("canonical target vector failed full modular replay")
        del residual, vector_field
        target_checkpoint = save_kernel_array(
            cache, f"p{PRIME}-canonical-target.npy", target_vector
        )
        target_checkpoint["support_size_in_A"] = int(np.count_nonzero(target_vector[:-1]))
        target_checkpoint["target_coordinate"] = int(target_vector[-1])
        pivot_set = set(pivots_a)
        target_checkpoint["basis_columns"] = [
            column for column in range(A_COLUMNS) if column not in pivot_set
        ]
    del field
    decision = (
        "MODULAR_TARGET_COMPATIBLE_EXACT_STATUS_UNRESOLVED"
        if epsilon == 0
        else "MODULAR_TARGET_SEPARATED_EXACT_STATUS_UNRESOLVED"
    )
    report = {
        "prime": PRIME,
        "rank_N": rank_n,
        "nullity_N": nullity_n,
        "rank_A": rank_a,
        "nullity_A": nullity_a,
        "epsilon": epsilon,
        "decision": decision,
        "H_N": {
            **h_n_checkpoint,
            "rref_pivot_coordinates": pivots_n,
            "rref_pivot_coordinates_sha256": canonical_sha256(pivots_n),
        },
        "H_A": {
            **h_a_checkpoint,
            "rref_pivot_coordinates": pivots_a,
            "rref_pivot_coordinates_sha256": canonical_sha256(pivots_a),
        },
        "target_projection": {
            "nonzero": bool(target_support),
            "support": target_support,
            "support_sha256": canonical_sha256(target_support),
            "raw_uint32_sha256": raw_array_sha256(target_projection),
        },
        "canonical_target_vector": target_checkpoint,
        "full_input_augmented_int64_c_sha256": full_report[
            "full_augmented_int64_c_sha256"
        ],
        "kernel_replay": {
            "all_rows": TOTAL_ROWS,
            "all_augmented_columns": AUGMENTED_COLUMNS,
            "all_kernel_vectors": nullity_n,
            "block_size": KERNEL_REPLAY_BLOCK,
            "zero_mod_prime": True,
        },
        "interpretation": (
            "The target is compatible with this finite row system modulo the registered prime; "
            "this is not rational membership. The canonical target vector is a candidate for "
            "exact Dixon lifting and global/cell replay."
            if epsilon == 0
            else "The target adds one rank modulo the registered prime; this is not rational "
            "nonmembership. An exact replayed left dual is required."
        ),
    }
    return report, time.perf_counter() - begun


def resolve_small(matrix: np.ndarray, target: np.ndarray, prime: int) -> dict[str, int]:
    augmented = np.ascontiguousarray(np.column_stack((matrix, target)))
    field, reduced = to_nmod(augmented, prime)
    del reduced
    h_n_field, h_n, nullity_n = canonical_kernel(field, prime)
    del h_n_field
    h_a_field, h_a, nullity_a, epsilon = derive_a_kernel(h_n, prime)
    del h_a_field
    replay_kernel_blocks(field, h_n, prime, max(1, nullity_n))
    rank_n = augmented.shape[1] - nullity_n
    rank_a = matrix.shape[1] - nullity_a
    del field, h_n, h_a
    if epsilon != rank_n - rank_a:
        raise ResolverError("small rank-gap control failed")
    return {"rank_A": rank_a, "rank_N": rank_n, "epsilon": epsilon}


def run_controls() -> dict[str, object]:
    p = 101
    member = resolve_small(
        np.asarray([[1], [2]], dtype=np.int64),
        np.asarray([3, 6], dtype=np.int64),
        p,
    )
    nonmember = resolve_small(
        np.asarray([[1], [0]], dtype=np.int64),
        np.asarray([0, 1], dtype=np.int64),
        p,
    )
    if member != {"rank_A": 1, "rank_N": 1, "epsilon": 0}:
        raise ResolverError("planted member control failed")
    if nonmember != {"rank_A": 1, "rank_N": 2, "epsilon": 1}:
        raise ResolverError("planted nonmember control failed")

    # Exercise the canonical target-normalization path, not merely the rank gap.
    target_matrix = np.asarray(
        [[1, 0, 1], [0, 1, 1], [1, 1, 2]], dtype=np.int64
    )
    target_rhs = np.asarray([5, 7, 12], dtype=np.int64)
    target_augmented = np.ascontiguousarray(
        np.column_stack((target_matrix, target_rhs))
    )
    target_field, target_reduced = to_nmod(target_augmented, p)
    del target_reduced
    target_hn_field, target_hn, _target_dn = canonical_kernel(target_field, p)
    del target_hn_field
    target_ha_field, target_ha, _target_da, target_epsilon = derive_a_kernel(
        target_hn, p
    )
    del target_ha_field
    target_pivots = pivot_coordinates(target_ha)
    target_vector = canonical_target_vector(
        target_hn, target_ha, target_pivots, p
    )
    target_vector_field, target_vector_reduced = to_nmod(
        target_vector.reshape(-1, 1), p
    )
    del target_vector_reduced
    if (
        target_epsilon != 0
        or target_field * target_vector_field
        != nmod_mat(target_matrix.shape[0], 1, p)
    ):
        raise ResolverError("canonical modular target-vector control failed")
    target_vector_mutant = target_vector.copy()
    target_vector_mutant[0] = (int(target_vector_mutant[0]) + 1) % p
    mutant_field, mutant_reduced = to_nmod(target_vector_mutant.reshape(-1, 1), p)
    del mutant_reduced
    if target_field * mutant_field == nmod_mat(target_matrix.shape[0], 1, p):
        raise ResolverError("target-vector mutation was not rejected")
    del target_field, target_vector_field, mutant_field
    exceptional_false_separation = resolve_small(
        np.asarray([[p]], dtype=np.int64),
        np.asarray([1], dtype=np.int64),
        p,
    )
    exceptional_false_compatibility = resolve_small(
        np.asarray([[1], [0]], dtype=np.int64),
        np.asarray([0, p], dtype=np.int64),
        p,
    )
    if exceptional_false_separation["epsilon"] != 1:
        raise ResolverError("bad-prime false-separation control failed")
    if exceptional_false_compatibility["epsilon"] != 0:
        raise ResolverError("bad-prime false-compatibility control failed")
    original = np.asarray([[1, 2], [3, 4]], dtype=np.int64)
    mutated = original.copy()
    mutated[0, 0] += 1
    if raw_array_sha256(original) == raw_array_sha256(mutated):
        raise ResolverError("cache mutation control failed")
    return {
        "flat_typed_memoryview_nmod_constructor": True,
        "planted_member_rank_gap": member,
        "planted_nonmember_rank_gap": nonmember,
        "canonical_target_vector_full_replay": True,
        "canonical_target_vector_mutant_rejected": True,
        "exceptional_prime_false_separation_detected": True,
        "exceptional_prime_false_compatibility_detected": True,
        "modular_epsilon_never_promoted_without_exact_replay": True,
        "cache_mutation_rejected": True,
    }


def build_preflight() -> dict[str, object]:
    bindings, outcome = verify_bindings()
    panels = final_panel_reports(outcome)
    pivot_report = outcome.get("g0074_pivot_rows")
    if not isinstance(pivot_report, dict):
        raise ResolverError("missing G-0074 pivot report")
    pivots = list(map(int, pivot_report.get("pivot_rows", [])))
    controls = run_controls()
    subject = {
        "A_shape": [TOTAL_ROWS, A_COLUMNS],
        "N_shape": [TOTAL_ROWS, AUGMENTED_COLUMNS],
        "row_order": "all 128 G-0075 panels in registered order, then all 1,378 G-0074 rows",
        "g0075_panel_rows": DIRECT_ROWS,
        "g0074_rows": OLD_ROWS,
        "g0074_row_policy": "all rows; selected 460 used only as a registered projection check",
        "panel_manifest_sha256": canonical_sha256(
            [{"panel": item["panel"], "levels": item["levels"]} for item in panels]
        ),
        "g0074_pivot_rows_sha256": canonical_sha256(pivots),
        "prime": PRIME,
        "kernel_policy": "canonical RREF row basis of ker([A|b])",
        "rank_gap_policy": (
            "epsilon=0 iff the target-coordinate projection of ker([A|b]) is nonzero; "
            "epsilon=1 otherwise"
        ),
        "decision_rule": (
            "both modular branches are discovery-only; emit a reusable canonical quotient and "
            "require later exact all-row right replay or exact all-column left-dual replay"
        ),
        "cache_policy": "resumable but non-evidentiary; every block is rechecked against registered raw hashes",
    }
    scientific = {
        "schema": PREFLIGHT_SCHEMA,
        "bindings": bindings,
        "controls": controls,
        "subject": subject,
    }
    return {
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
            "Preflight freezes a target-aware modular diagnostic and reusable quotient. "
            "It contains no G-0076 rank outcome and asserts no rational representation, "
            "rational obstruction, global MAX11 identity, or unrestricted depth theorem."
        ),
    }


def enforce_frozen_preflight(preflight: dict[str, object]) -> None:
    if EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256 is None:
        raise ResolverError("registered execution disabled until preflight is frozen")
    if preflight.get("scientific_payload_sha256") != EXPECTED_PREFLIGHT_SCIENTIFIC_SHA256:
        raise ResolverError("frozen G-0076 preflight drift")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(16, os.cpu_count() or 1)))
    parser.add_argument("--profile-budget", type=int, default=600_000)
    parser.add_argument("--cache", type=Path, default=CACHE_DEFAULT)
    parser.add_argument("--kernel-output", type=Path)
    parser.add_argument("--expected-script-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    begun = time.perf_counter()
    session_script_sha = sha256_path(SCRIPT)
    arguments.cache = arguments.cache.resolve()
    if arguments.kernel_output is not None:
        arguments.kernel_output = arguments.kernel_output.resolve()
    if arguments.workers < 1:
        raise ResolverError("workers must be positive")
    if arguments.output is not None and arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output}")
    if arguments.run:
        if arguments.output is None or arguments.kernel_output is None:
            raise ResolverError("registered run requires --output and --kernel-output")
        if arguments.expected_script_sha256 != session_script_sha:
            raise ResolverError("registered run requires exact preregistered script SHA-256")
    preflight = build_preflight()
    if sha256_path(SCRIPT) != session_script_sha:
        raise ResolverError("G-0076 producer drifted during preflight")
    if preflight.get("script_sha256") != session_script_sha:
        raise ResolverError("G-0076 preflight recorded the wrong producer")
    if arguments.self_test:
        print(json.dumps({
            "schema": SCHEMA,
            "mode": "self-test",
            "controls": preflight["controls"],
            "subject": preflight["subject"],
        }, sort_keys=True))
        return
    if arguments.preflight_only:
        if arguments.output is not None:
            write_gzip(arguments.output, preflight)
        print(json.dumps(preflight, sort_keys=True))
        return
    enforce_frozen_preflight(preflight)
    bases, representatives, bindings, outcome = prepare_subject(
        workers=arguments.workers, profile_budget=arguments.profile_budget
    )
    panel_reports, panel_seconds = build_panel_cache(
        cache=arguments.cache,
        bases=bases,
        representatives=representatives,
        outcome=outcome,
        workers=arguments.workers,
    )
    g0074, pivot_rows, g0074_report, g0074_seconds = build_g0074_cache(
        cache=arguments.cache,
        bases=bases,
        representatives=representatives,
        outcome=outcome,
        workers=arguments.workers,
        profile_budget=arguments.profile_budget,
    )
    full, full_report, full_seconds = build_full_cache(
        cache=arguments.cache,
        outcome=outcome,
        g0074=g0074,
        pivot_rows=pivot_rows,
    )
    cache_manifest = {
        "schema": CACHE_SCHEMA,
        "producer_sha256": session_script_sha,
        "g0075_outcome_sha256": EXPECTED_G0075_OUTCOME_SHA256,
        "panels": panel_reports,
        "g0074": g0074_report,
        "full": full_report,
    }
    atomic_write_json(arguments.cache / "manifest.json", cache_manifest)
    kernel_report, kernel_seconds = resolve_full_kernel(
        cache=arguments.cache,
        full=full,
        full_report=full_report,
        kernel_output=arguments.kernel_output,
    )
    scientific = {
        "schema": SCHEMA,
        "preflight_scientific_payload_sha256": preflight[
            "scientific_payload_sha256"
        ],
        "subject": preflight["subject"],
        "cache_input_manifest_sha256": canonical_sha256(cache_manifest),
        "full_matrix": full_report,
        "modular_resolution": kernel_report,
        "decision": kernel_report["decision"],
    }
    report = {
        **scientific,
        "mode": "registered-run",
        "bindings": bindings,
        "controls": preflight["controls"],
        "script_sha256": session_script_sha,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "seconds": {
            "panel_cache": panel_seconds,
            "g0074_cache": g0074_seconds,
            "full_cache": full_seconds,
            "kernel": kernel_seconds,
            "wall": time.perf_counter() - begun,
        },
        "workers": arguments.workers,
        "cache_custody": {
            "cache_path": str(arguments.cache),
            "cache_manifest_sha256": sha256_path(arguments.cache / "manifest.json"),
            "kernel_checkpoint_npy_sha256": {
                "H_N": sha256_path(arguments.cache / "kernels" / f"p{PRIME}-HN.npy"),
                "H_A": sha256_path(arguments.cache / "kernels" / f"p{PRIME}-HA.npy"),
            },
            "archival_kernel_path": str(arguments.kernel_output),
        },
        "interpretation_boundary": (
            "This outcome classifies target compatibility over one finite field for exactly "
            "the bound 16,738-row frozen system and exports its kernel quotient. It is not "
            "a rational membership or nonmembership result, a global MAX11 construction, "
            "or an unrestricted two-hidden-layer ReLU theorem."
        ),
    }
    if sha256_path(SCRIPT) != session_script_sha:
        raise ResolverError("G-0076 producer drifted during registered execution")
    verify_bindings()
    write_gzip(arguments.output, report)
    print(json.dumps({
        "output": str(arguments.output),
        "output_sha256": sha256_path(arguments.output),
        "scientific_payload_sha256": report["scientific_payload_sha256"],
        "decision": report["decision"],
        "rank_A": kernel_report["rank_A"],
        "rank_N": kernel_report["rank_N"],
        "epsilon": kernel_report["epsilon"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
