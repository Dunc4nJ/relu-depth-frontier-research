#!/usr/bin/env python3
"""Complete frozen-dictionary Schur rank/solve gate for G-0081.

The registered subject is all 8,107 old columns and all 18,582 G-0079
same-component columns on all 16,738 frozen rows modulo 1,000,003.  Prices
are never used to select columns.  Public execution requires a separately
frozen preregistration; this source ships first for hostile review.

Every modular branch is discovery-only.  A member branch still needs an
exact rational lift and a global CPWL identity replay.  A separator branch
only separates this finite dictionary on these frozen rows.
"""

from __future__ import annotations

import argparse
import ctypes
import fcntl
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import platform
import resource
import secrets
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import numpy as np
from numpy.lib.format import open_memmap

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()

G0079_RUNNER = ROOT / "artifacts/math/G-0079/same_component_y_spoke_cegis.py"
G0079_PRICE = ROOT / "artifacts/math/G-0079/same_component_y_spoke_prices_v2.json.gz"
G0079_PREFLIGHT_SOURCE = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_closure.py"
)
G0079_PREFLIGHT = (
    ROOT / "artifacts/math/G-0079/same_component_y_spoke_preflight_v1.json.gz"
)
NATIVE_ADAPTER = ROOT / "artifacts/math/G-0079/native_flint_nmod_adapter.py"
INVERSE_RECEIPT = ROOT / "artifacts/math/G-0079/native_flint_inverse_receipt_v1.json"
INVERSE_CACHE = ROOT / "artifacts/math/G-0079/cache/old_basis_inverse_p1000003_v1.npy"
G0077_SOURCE = ROOT / "artifacts/math/G-0077/exact_left_dual_lift.py"
G0077_PREFLIGHT = ROOT / "artifacts/math/G-0077/exact_left_dual_preflight_v1.json.gz"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
G0078_SOURCE = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual.py"
G0078_PREFLIGHT = ROOT / "artifacts/math/G-0078/sparse_exact_preflight_v1.json.gz"
G0078_EXACT = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz"
FULL_OLD_MATRIX = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"
REGISTERED_PYTHON = ROOT / ".venv/bin/python"

SCHEMA_PREREGISTRATION = "max11-g0081-complete-native-schur-preregistration-v1"
SCHEMA_RESULT = "max11-g0081-complete-native-schur-result-v1"
SCHEMA_C_CACHE = "max11-g0081-complete-new-matrix-cache-v1"
SCHEMA_S_CACHE = "max11-g0081-pre-rref-schur-cache-v1"
SCHEMA_R_CACHE = "max11-g0081-in-place-rref-cache-v1"

PRIME = 1_000_003
TOTAL_ROWS = 16_738
OLD_COLUMNS = 8_107
NEW_COLUMNS = 18_582
BASIS_RANK = 6_876
QUOTIENT_ROWS = TOTAL_ROWS - BASIS_RANK
SCHUR_COLUMNS = NEW_COLUMNS + 1
GLOBAL_NEW_START = OLD_COLUMNS
GLOBAL_TARGET_COLUMN = OLD_COLUMNS + NEW_COLUMNS
FOUR_PROFILE_COUNT = 364
THREE_PROFILE_COUNT = 78
WORKERS = 8
CHUNK_ROWS = 8
PROGRESS_COMMIT_CHUNKS = 16
MAXIMUM_WALL_SECONDS = 21_600.0
MINIMUM_AVAILABLE_GIB = 12.0
MINIMUM_FREE_DISK_GIB = 12.0
PROJECTED_MINIMUM_PEAK_BYTES = 3_755_753_472
EXPECTED_DENSE_SCHUR_ENTRIES = 183_265_546
EXPECTED_PROJECTED_DENSE_MULTIPLY_SECONDS = 538.0544315638452
EXPECTED_PROJECTED_DENSE_RANK_SECONDS = 408.36025315134856
EXPECTED_PROJECTED_KERNEL_SECONDS = 10_710.702239091652
EXPECTED_REGISTERED_PYTHON = "3.13.7"

EXPECTED_G0079_RUNNER_SHA256 = (
    "7539515641c241a28be45cea88445bd4f598f7c0693ab521c31805530c9f67da"
)
EXPECTED_G0079_PRICE_SHA256 = (
    "5d6754c91f7971aa3fdad2d1f171645f32fa57c26b4a001bb3b6ac9d5e802958"
)
EXPECTED_G0079_PRICE_SCIENCE_SHA256 = (
    "357e2437849dac4074995892a6f174d9f225848280e2bf53d9f9ea1010d9e265"
)
EXPECTED_SUPPORT_VALUES_RAW_SHA256 = (
    "a38b8237b108284ecafaa4f97a0c0c29a60b3a9dd58521389762effb4e4619b2"
)
EXPECTED_TARGET_VALUES_RAW_SHA256 = (
    "b4d8462ffc8be8b94dd997ab7792315d398afca5e3253a40d5d92bcfeac9fb3a"
)
EXPECTED_NATIVE_ADAPTER_SHA256 = (
    "bb7677f84865c0ec380237fddb94a05d4c0806c979f41c4eddd8f7b27fdf59cf"
)
EXPECTED_INVERSE_RECEIPT_SHA256 = (
    "9820a3afcb8e0cd453a7219703669867467291e94e439e7742eafda0c3a584c2"
)
EXPECTED_INVERSE_CACHE_SHA256 = (
    "2888960f52e64e36e8ab26c1fc69f65c8c53bda4d39a1a51ad17fbd759805e86"
)
EXPECTED_INVERSE_DATA_SHA256 = (
    "4238321f534bd0005e0952019faf340b32669cce4041f252aa0f029215994af3"
)
EXPECTED_BASIS_ROWS_SHA256 = (
    "b2948637191c00c60aaf4c2d5ae6bd81fa05ddb05dabf419776a503e46d5388c"
)
EXPECTED_BASIS_COLUMNS_SHA256 = (
    "68bbfdfea522e88e97fad989952a0bb88ae4875d74ea6f9cfb50425f4ee5a683"
)

STATIC_BINDINGS: dict[str, tuple[Path, str]] = {
    "g0079_registered_runner": (G0079_RUNNER, EXPECTED_G0079_RUNNER_SHA256),
    "g0079_complete_price": (G0079_PRICE, EXPECTED_G0079_PRICE_SHA256),
    "g0079_preflight_source": (
        G0079_PREFLIGHT_SOURCE,
        "3b4626f36c8c505274b108b3cd80a17127de6e911c16962cbdbcff557a22b5da",
    ),
    "g0079_preflight_receipt": (
        G0079_PREFLIGHT,
        "12ea9a384a064c4cd9e17e37688384f4241b2fbe85cea501b892ad1ab2b4fd91",
    ),
    "native_adapter": (NATIVE_ADAPTER, EXPECTED_NATIVE_ADAPTER_SHA256),
    "inverse_receipt": (INVERSE_RECEIPT, EXPECTED_INVERSE_RECEIPT_SHA256),
    "inverse_cache": (INVERSE_CACHE, EXPECTED_INVERSE_CACHE_SHA256),
    "g0077_source": (
        G0077_SOURCE,
        "278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279",
    ),
    "g0077_preflight": (
        G0077_PREFLIGHT,
        "49e6e9714ef427d461d2940f7ccc7751ebf0b3d06a4a29065779b251429602a6",
    ),
    "g0077_modular": (
        G0077_MODULAR,
        "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4",
    ),
    "g0078_source": (
        G0078_SOURCE,
        "6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229",
    ),
    "g0078_preflight": (
        G0078_PREFLIGHT,
        "34e60905e504448980317057e617fe3e7dbf27ef1c07d1541d8c0c2b593a24be",
    ),
    "g0078_exact": (
        G0078_EXACT,
        "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96",
    ),
    "full_old_matrix": (
        FULL_OLD_MATRIX,
        "5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f",
    ),
    "environment_manifest": (
        ENVIRONMENT_MANIFEST,
        "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c",
    ),
}


class GateError(RuntimeError):
    """A frozen binding, cache, arithmetic, ABI, or claim invariant failed."""


@dataclass(frozen=True)
class Registration:
    path: Path
    sha256: str
    runner_sha256: str
    output: Path
    cache_dir: Path
    document: dict[str, object]


@dataclass(frozen=True)
class CachePaths:
    directory: Path
    c_final: Path
    c_partial: Path
    c_progress: Path
    c_receipt: Path
    c_receipt_pending: Path
    s_final: Path
    s_partial: Path
    s_receipt: Path
    s_receipt_pending: Path
    r_final: Path
    r_partial: Path
    r_receipt: Path
    r_receipt_pending: Path
    lock: Path


@dataclass(frozen=True)
class BasePlan:
    columns: np.ndarray
    anchors: np.ndarray
    auxiliaries: np.ndarray
    orientations: np.ndarray
    left: tuple[tuple[int, int], ...]
    right: tuple[tuple[int, int], ...]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def require_contained(path: Path) -> None:
    if not path.resolve(strict=False).is_relative_to(ROOT.resolve()):
        raise GateError(f"path escapes campaign workspace: {path}")


def relative_path(path: Path) -> str:
    require_contained(path)
    return str(path.resolve(strict=False).relative_to(ROOT.resolve()))


def stable_regular_bytes(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        descriptor = os.open(path, flags)
    except OSError as error:
        raise GateError(f"cannot open frozen regular file {path}: {error}") from error
    with os.fdopen(descriptor, "rb") as source:
        before = os.fstat(source.fileno())
        if not stat.S_ISREG(before.st_mode):
            raise GateError(f"not a regular file: {path}")
        payload = source.read()
        after = os.fstat(source.fileno())
    fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, key) != getattr(after, key) for key in fields):
        raise GateError(f"file changed while read: {path}")
    if len(payload) != after.st_size:
        raise GateError(f"byte census drift: {path}")
    return payload


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not one regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray, block_rows: int = 32) -> str:
    if array.ndim == 0:
        return hashlib.sha256(
            memoryview(np.ascontiguousarray(array)).cast("B")
        ).hexdigest()
    digest = hashlib.sha256()
    for start in range(0, array.shape[0], block_rows):
        block = np.ascontiguousarray(array[start : start + block_rows])
        digest.update(memoryview(block).cast("B"))
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, object]:
    payload = stable_regular_bytes(path)
    try:
        value = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateError(f"invalid JSON: {path}") from error
    if not isinstance(value, dict):
        raise GateError(f"JSON root is not an object: {path}")
    return value


def read_gzip(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not one regular gzip JSON file: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise GateError(f"gzip JSON root is not an object: {path}")
    return value


def write_json_exclusive(path: Path, value: object) -> None:
    require_contained(path)
    if path.exists() or path.is_symlink():
        raise GateError(f"refusing to overwrite: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(canonical_bytes(value))
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_json_atomic(path: Path, value: object) -> None:
    """Replace only a resumable progress journal; never a final artifact."""
    require_contained(path)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}-{secrets.token_hex(4)}")
    write_json_exclusive(temporary, value)
    os.replace(temporary, path)


def write_gzip_exclusive(path: Path, value: object) -> None:
    require_contained(path)
    if path.exists() or path.is_symlink():
        raise GateError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
                zipped.write(canonical_bytes(value))
            raw.flush()
            os.fsync(raw.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def open_memmap_exclusive(
    path: Path,
    *,
    dtype: np.dtype,
    shape: tuple[int, int],
) -> np.memmap:
    """Create one NPY inode with O_EXCL, then verify open_memmap kept it."""
    require_contained(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags, 0o644)
    before = os.fstat(descriptor)
    os.close(descriptor)
    try:
        matrix = open_memmap(path, mode="w+", dtype=dtype, shape=shape)
        after = path.stat(follow_symlinks=False)
        if (before.st_dev, before.st_ino) != (after.st_dev, after.st_ino):
            raise GateError(
                f"exclusive NPY inode changed during initialization: {path}"
            )
        return matrix
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def promote_exclusive(source: Path, destination: Path) -> None:
    """Promote by hard link so an existing destination can never be replaced."""
    require_contained(source)
    require_contained(destination)
    if not source.is_file() or source.is_symlink():
        raise GateError(f"promotion source is not one regular file: {source}")
    try:
        os.link(source, destination, follow_symlinks=False)
    except FileExistsError as error:
        raise GateError(
            f"refusing to overwrite promoted cache: {destination}"
        ) from error
    source.unlink()


def load_owned_module(path: Path, expected_sha256: str, name: str) -> ModuleType:
    source = stable_regular_bytes(path)
    observed = hashlib.sha256(source).hexdigest()
    if observed != expected_sha256:
        raise GateError(f"owned source drift for {path}: {observed}")
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    module.__cached__ = None
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)  # noqa: S102 -- exact owned bytes
    module.__cached__ = None
    return module


def replay_static_bindings() -> dict[str, dict[str, object]]:
    report: dict[str, dict[str, object]] = {}
    for label, (path, expected) in STATIC_BINDINGS.items():
        observed = sha256_path(path)
        if observed != expected:
            raise GateError(f"binding drift for {label}: {observed} != {expected}")
        report[label] = {
            "path": relative_path(path),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    return report


def capture_custody(
    runner_sha256: str,
    preregistration_path: Path | None = None,
) -> dict[str, str]:
    if sha256_path(SCRIPT) != runner_sha256:
        raise GateError("live G-0081 runner differs from registered source pin")
    values = {
        label: sha256_path(path) for label, (path, _expected) in STATIC_BINDINGS.items()
    }
    values["g0081_runner"] = runner_sha256
    if preregistration_path is not None:
        require_contained(preregistration_path)
        values["g0081_preregistration_path"] = relative_path(preregistration_path)
        values["g0081_preregistration"] = sha256_path(preregistration_path)
    return values


def recapture_custody(expected: dict[str, str]) -> dict[str, str]:
    path_text = expected.get("g0081_preregistration_path")
    path = ROOT / path_text if path_text is not None else None
    return capture_custody(expected["g0081_runner"], path)


def cache_paths(directory: Path) -> CachePaths:
    require_contained(directory)
    return CachePaths(
        directory=directory,
        c_final=directory / "complete_new_matrix_p1000003_v1.npy",
        c_partial=directory / "complete_new_matrix_p1000003_v1.partial.npy",
        c_progress=directory / "complete_new_matrix_p1000003_v1.progress.json",
        c_receipt=directory / "complete_new_matrix_p1000003_v1.receipt.json",
        c_receipt_pending=directory
        / "complete_new_matrix_p1000003_v1.receipt.pending.json",
        s_final=directory / "pre_rref_schur_augmented_p1000003_v1.npy",
        s_partial=directory / "pre_rref_schur_augmented_p1000003_v1.partial.npy",
        s_receipt=directory / "pre_rref_schur_augmented_p1000003_v1.receipt.json",
        s_receipt_pending=directory
        / "pre_rref_schur_augmented_p1000003_v1.receipt.pending.json",
        r_final=directory / "in_place_rref_augmented_p1000003_v1.npy",
        r_partial=directory / "in_place_rref_augmented_p1000003_v1.partial.npy",
        r_receipt=directory / "in_place_rref_augmented_p1000003_v1.receipt.json",
        r_receipt_pending=directory
        / "in_place_rref_augmented_p1000003_v1.receipt.pending.json",
        lock=directory / "execution.lock",
    )


@contextmanager
def exclusive_cache_lock(path: Path) -> Iterator[None]:
    require_contained(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise GateError(f"another G-0081 execution owns {path}") from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        yield
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def binding_hash_map() -> dict[str, str]:
    return {label: digest for label, (_path, digest) in STATIC_BINDINGS.items()}


def validate_registration(arguments: argparse.Namespace) -> Registration:
    required = {
        "--preregistration": arguments.preregistration,
        "--expected-runner-sha256": arguments.expected_runner_sha256,
        "--expected-preregistration-sha256": arguments.expected_preregistration_sha256,
        "--output": arguments.output,
        "--cache-dir": arguments.cache_dir,
    }
    missing = [key for key, value in required.items() if value is None]
    if missing:
        raise GateError(f"registered execution missing arguments: {missing}")
    preregistration = arguments.preregistration
    output = arguments.output
    directory = arguments.cache_dir
    assert (
        isinstance(preregistration, Path)
        and isinstance(output, Path)
        and isinstance(directory, Path)
    )
    require_contained(preregistration)
    require_contained(output)
    require_contained(directory)
    runner_sha256 = sha256_path(SCRIPT)
    if arguments.expected_runner_sha256 != runner_sha256:
        raise GateError("explicit runner pin differs from live source")
    payload = stable_regular_bytes(preregistration)
    preregistration_sha256 = hashlib.sha256(payload).hexdigest()
    if preregistration_sha256 != arguments.expected_preregistration_sha256:
        raise GateError("explicit preregistration pin differs from live bytes")
    try:
        document = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise GateError("preregistration is not valid JSON") from error
    if not isinstance(document, dict):
        raise GateError("preregistration JSON root is not an object")
    expected = {
        "schema": SCHEMA_PREREGISTRATION,
        "experiment_status": "planned",
        "registered_source_sha256": runner_sha256,
        "registered_bindings_sha256": binding_hash_map(),
        "prime": PRIME,
        "rows": TOTAL_ROWS,
        "old_columns": OLD_COLUMNS,
        "new_columns": NEW_COLUMNS,
        "basis_rank": BASIS_RANK,
        "quotient_rows": QUOTIENT_ROWS,
        "all_new_columns_retained": True,
        "price_filtering_allowed": False,
        "workers": WORKERS,
        "chunk_rows": CHUNK_ROWS,
        "maximum_wall_seconds": MAXIMUM_WALL_SECONDS,
        "minimum_available_gib": MINIMUM_AVAILABLE_GIB,
        "minimum_free_disk_gib": MINIMUM_FREE_DISK_GIB,
        "projected_minimum_peak_bytes": PROJECTED_MINIMUM_PEAK_BYTES,
        "registered_python": ".venv/bin/python",
        "python_version": EXPECTED_REGISTERED_PYTHON,
        "cache_dir": relative_path(directory),
        "output": relative_path(output),
        "native_rref_abi": "slong nmod_mat_rref(nmod_mat_t); mutates to RREF",
        "stage_order": [
            "complete-all-column-C-cache",
            "independent-230-row-semantic-replay",
            "complete-pre-RREF-Schur-cache",
            "native-target-last-RREF-and-persist-transform",
            "member-solution-or-separator-discovery",
        ],
    }
    for key, value in expected.items():
        if document.get(key) != value:
            raise GateError(f"preregistration field drift: {key}")
    if document.get("preregistration_path") != relative_path(preregistration):
        raise GateError("preregistration self-path drift")
    if (
        Path(sys.executable).resolve() != REGISTERED_PYTHON.resolve()
        or platform.python_version() != EXPECTED_REGISTERED_PYTHON
    ):
        raise GateError("registered interpreter path/version drift")
    if output.exists() or output.is_symlink():
        raise GateError(f"refusing to overwrite registered output: {output}")
    return Registration(
        preregistration,
        preregistration_sha256,
        runner_sha256,
        output,
        directory,
        document,
    )


def load_g0079_context() -> tuple[
    ModuleType, ModuleType, object, object, dict[str, object]
]:
    runner = load_owned_module(
        G0079_RUNNER, EXPECTED_G0079_RUNNER_SHA256, "max11_g0079_owned_for_g0081"
    )
    runner.replay_fixed_bindings()
    preflight, receipt = runner.validate_preflight()
    g75, family = runner.reconstruct_family(preflight, receipt)
    semantic = runner.semantic_module_chain_report(g75)
    if len(family.new_representatives) != NEW_COLUMNS:
        raise GateError("G-0079 representative census drift")
    return runner, preflight, g75, family, semantic


def load_price_contract(runner: ModuleType) -> tuple[dict[str, object], object]:
    report = read_gzip(G0079_PRICE)
    scientific = report.get("scientific_payload")
    if not isinstance(scientific, dict):
        raise GateError("G-0079 price artifact lacks scientific payload")
    if (
        report.get("schema") != "max11-g0079-complete-exact-price-vector-v2"
        or report.get("runner_sha256") != EXPECTED_G0079_RUNNER_SHA256
        or report.get("scientific_payload_sha256")
        != EXPECTED_G0079_PRICE_SCIENCE_SHA256
        or canonical_sha256(scientific) != EXPECTED_G0079_PRICE_SCIENCE_SHA256
    ):
        raise GateError("G-0079 price artifact top-level contract drift")
    dictionary = scientific.get("registered_dictionary")
    vector = scientific.get("complete_price_vector")
    branch = scientific.get("branch_contract")
    if (
        not isinstance(dictionary, dict)
        or not isinstance(vector, dict)
        or not isinstance(branch, dict)
    ):
        raise GateError("G-0079 price artifact structure drift")
    ids = vector.get("global_column_ids")
    prices = vector.get("prices")
    prices_mod = vector.get("prices_mod_prime")
    if (
        dictionary.get("old_columns_including_carriers") != OLD_COLUMNS
        or dictionary.get("new_columns") != NEW_COLUMNS
        or dictionary.get("total_columns") != OLD_COLUMNS + NEW_COLUMNS
        or not isinstance(ids, list)
        or ids != list(range(GLOBAL_NEW_START, GLOBAL_TARGET_COLUMN))
        or not isinstance(prices, list)
        or len(prices) != NEW_COLUMNS
        or not isinstance(prices_mod, list)
        or len(prices_mod) != NEW_COLUMNS
        or canonical_sha256(prices) != vector.get("prices_sha256")
        or canonical_sha256(prices_mod) != vector.get("prices_mod_prime_sha256")
        or vector.get("support_values_int64_c_sha256")
        != EXPECTED_SUPPORT_VALUES_RAW_SHA256
        or vector.get("target_values_int64_sha256") != EXPECTED_TARGET_VALUES_RAW_SHA256
        or vector.get("all_18582_columns_serialized") is not True
        or branch.get("all_new_columns_retained_if_nonzero") is not True
        or branch.get("price_filtering_allowed") is not False
    ):
        raise GateError("G-0079 complete price-vector contract drift")
    functional = runner.exact_functional(
        load_owned_module(
            G0079_PREFLIGHT_SOURCE,
            STATIC_BINDINGS["g0079_preflight_source"][1],
            "max11_g0079_preflight_for_price_contract",
        )
    )
    exact = scientific.get("exact_functional")
    if (
        not isinstance(exact, dict)
        or int(exact.get("target_pairing_mod_prime", 0)) == 0
    ):
        raise GateError("G-0079 target price is zero or malformed")
    return report, functional


class FastEvaluator:
    """All-column evaluator with the 364/78 assignment-code caches frozen."""

    def __init__(
        self,
        g75: ModuleType,
        bases: Sequence[object],
        representatives: Sequence[object],
        *,
        require_complete: bool = True,
    ):
        self.g75 = g75
        self.g74 = g75.G74
        self.g73 = g75.G73
        self.bases = tuple(bases)
        self.representatives = tuple(representatives)
        four_profiles = tuple(self.g73.all_profiles())
        three_profiles = tuple(self.g74.all_three_profiles())
        if (
            len(four_profiles) != FOUR_PROFILE_COUNT
            or len(three_profiles) != THREE_PROFILE_COUNT
        ):
            raise GateError("assignment-profile census drift")
        self.four_profiles = four_profiles
        self.three_profiles = three_profiles
        self.four_codes = tuple(
            np.ascontiguousarray(self.g73.assignments(profile), dtype=np.int16)
            for profile in four_profiles
        )
        self.three_codes = tuple(
            np.ascontiguousarray(
                self.g74.three_assignments(profile, 1, 2), dtype=np.int16
            )
            for profile in three_profiles
        )
        self.positive_profiles = tuple(self.g75.positive_profiles())
        self.positive_four_indices = tuple(
            four_profiles.index(profile) for profile in self.positive_profiles
        )
        self.panel_ratios = tuple(self.g75.panel_ratios())
        self.farey = tuple(self.g74.FAREY_F6)
        if (
            len(self.positive_profiles) != 120
            or len(self.panel_ratios) != 128
            or len(self.farey) != 13
        ):
            raise GateError("frozen row-panel census drift")
        grouped = self.g73.group_by_base(representatives, len(bases))
        plans: list[BasePlan] = []
        for base in bases:
            entries = grouped[base.position]
            if not entries:
                continue
            seeds = [seed for _column, seed in entries]
            plans.append(
                BasePlan(
                    columns=np.asarray(
                        [column for column, _seed in entries], dtype=np.intp
                    ),
                    anchors=np.asarray(
                        [seed.expression.anchor - 1 for seed in seeds], dtype=np.intp
                    ),
                    auxiliaries=np.asarray(
                        [seed.expression.auxiliary - 1 for seed in seeds], dtype=np.intp
                    ),
                    orientations=np.asarray(
                        [seed.expression.orientation for seed in seeds], dtype=np.int8
                    ),
                    left=tuple(base.left),
                    right=tuple(base.right),
                )
            )
        self.plans = tuple(plans)
        if require_complete and (
            len(self.representatives) != NEW_COLUMNS
            or len(self.plans) != len(self.bases)
        ):
            raise GateError("fast-evaluator family plan census drift")

    def levels(self, raw_row: int) -> np.ndarray:
        if not 0 <= raw_row < TOTAL_ROWS:
            raise GateError(f"raw row outside frozen system: {raw_row}")
        panel_rows = len(self.panel_ratios) * len(self.positive_profiles)
        if raw_row < panel_rows:
            panel, local = divmod(raw_row, len(self.positive_profiles))
            a, b = self.panel_ratios[panel]
            lookup = np.asarray((0, a, b, self.g75.DENOMINATOR), dtype=np.int16)
            return lookup[self.four_codes[self.positive_four_indices[local]]]
        offset = raw_row - panel_rows
        if offset < len(self.four_codes):
            return self.four_codes[offset]
        farey_offset = offset - len(self.four_codes)
        ratio_index, profile_index = divmod(farey_offset, len(self.three_codes))
        numerator, denominator = self.farey[ratio_index]
        lookup = np.asarray((0, numerator, denominator), dtype=np.int16)
        return lookup[self.three_codes[profile_index]]

    def evaluate_row(self, raw_row: int) -> np.ndarray:
        levels = self.levels(raw_row)
        output = np.zeros(len(self.representatives), dtype=np.int64)
        for plan in self.plans:
            left = np.zeros(levels.shape[1], dtype=np.int16)
            right = np.zeros(levels.shape[1], dtype=np.int16)
            for a, b in plan.left:
                left += np.maximum(levels[a - 1], levels[b - 1])
            for a, b in plan.right:
                right += np.maximum(levels[a - 1], levels[b - 1])
            simple = 2 * levels[plan.anchors]
            leaf = levels[plan.auxiliaries] + levels[10]
            common = np.maximum(left, right)[None, :] + simple
            branch = np.where(
                plan.orientations[:, None] == 0,
                right[None, :] + leaf,
                left[None, :] + leaf,
            )
            output[plan.columns] = np.maximum(common, branch).sum(
                axis=1, dtype=np.int64
            )
        return output

    def evaluate_rows(self, rows: Sequence[int]) -> np.ndarray:
        return np.stack([self.evaluate_row(int(row)) for row in rows])

    def cache_contract(self) -> dict[str, object]:
        return {
            "four_profile_assignment_code_matrices": len(self.four_codes),
            "three_profile_assignment_code_matrices": len(self.three_codes),
            "four_profile_manifest_sha256": canonical_sha256(
                [list(map(int, p)) for p in self.four_profiles]
            ),
            "three_profile_manifest_sha256": canonical_sha256(
                [list(map(int, p)) for p in self.three_profiles]
            ),
            "new_columns": len(self.representatives),
        }


_WORKER_EVALUATOR: FastEvaluator | None = None
_WORKER_CACHE: np.ndarray | None = None


def initialize_matrix_worker(cache_path: str) -> None:
    global _WORKER_CACHE
    if _WORKER_EVALUATOR is None:
        raise GateError("fork worker did not inherit FastEvaluator")
    _WORKER_CACHE = np.load(cache_path, mmap_mode="r+", allow_pickle=False)
    if _WORKER_CACHE.shape != (
        TOTAL_ROWS,
        NEW_COLUMNS,
    ) or _WORKER_CACHE.dtype != np.dtype("<u4"):
        raise GateError("fork worker cache shape/dtype drift")


def evaluate_matrix_chunk(task: tuple[int, int, int]) -> tuple[int, int, int, str]:
    chunk, start, stop = task
    if _WORKER_EVALUATOR is None or _WORKER_CACHE is None:
        raise GateError("matrix worker is uninitialized")
    values = _WORKER_EVALUATOR.evaluate_rows(range(start, stop))
    reduced = np.remainder(values, PRIME).astype(np.dtype("<u4"), copy=False)
    _WORKER_CACHE[start:stop] = reduced
    digest = hashlib.sha256(
        memoryview(np.ascontiguousarray(reduced)).cast("B")
    ).hexdigest()
    return chunk, start, stop, digest


def chunk_tasks() -> list[tuple[int, int, int]]:
    return [
        (chunk, start, min(start + CHUNK_ROWS, TOTAL_ROWS))
        for chunk, start in enumerate(range(0, TOTAL_ROWS, CHUNK_ROWS))
    ]


def fsync_path(path: Path) -> None:
    with path.open("rb") as source:
        os.fsync(source.fileno())


def completed_chunk_hashes(
    matrix: np.ndarray, tasks: Sequence[tuple[int, int, int]]
) -> dict[str, str]:
    return {
        str(chunk): hashlib.sha256(
            memoryview(np.ascontiguousarray(matrix[start:stop])).cast("B")
        ).hexdigest()
        for chunk, start, stop in tasks
    }


def validate_complete_cache(
    data_path: Path,
    receipt_path: Path,
    *,
    schema: str,
    shape: tuple[int, int],
    custody: dict[str, str],
) -> tuple[np.ndarray, dict[str, object]]:
    if (
        not data_path.is_file()
        or data_path.is_symlink()
        or not receipt_path.is_file()
        or receipt_path.is_symlink()
    ):
        raise GateError(f"complete cache pair missing or nonregular: {data_path}")
    receipt = read_json(receipt_path)
    matrix = np.load(data_path, mmap_mode="r", allow_pickle=False)
    if (
        receipt.get("schema") != schema
        or receipt.get("state") != "complete"
        or receipt.get("shape") != list(shape)
        or receipt.get("dtype") != "<u4"
        or receipt.get("prime") != PRIME
        or receipt.get("all_new_columns_retained") is not True
        or receipt.get("price_filtering_allowed") is not False
        or receipt.get("custody", {}).get("start") != custody
        or receipt.get("custody", {}).get("end") != custody
        or receipt.get("custody", {}).get("identical") is not True
        or matrix.shape != shape
        or matrix.dtype != np.dtype("<u4")
        or sha256_path(data_path) != receipt.get("npy_sha256")
        or raw_sha256(matrix) != receipt.get("raw_uint32_c_sha256")
    ):
        raise GateError(f"complete cache receipt/data drift: {data_path}")
    for start in range(0, shape[0], 32):
        if np.any(matrix[start : min(start + 32, shape[0])] >= PRIME):
            raise GateError(f"cache contains noncanonical residues: {data_path}")
    return matrix, receipt


def build_or_load_c_cache(
    paths: CachePaths,
    evaluator: FastEvaluator,
    custody: dict[str, str],
    deadline: float,
) -> tuple[np.ndarray, dict[str, object]]:
    final_pair = (paths.c_final.exists(), paths.c_receipt.exists())
    partial_pair = (paths.c_partial.exists(), paths.c_progress.exists())
    if final_pair == (True, True):
        if any(partial_pair) or paths.c_receipt_pending.exists():
            raise GateError("complete C cache coexists with partial state")
        return validate_complete_cache(
            paths.c_final,
            paths.c_receipt,
            schema=SCHEMA_C_CACHE,
            shape=(TOTAL_ROWS, NEW_COLUMNS),
            custody=custody,
        )
    if (
        any(final_pair)
        or paths.c_receipt_pending.exists()
        or partial_pair in ((True, False), (False, True))
    ):
        raise GateError(
            "partial/final C cache transaction drift; hostile audit required"
        )

    tasks = chunk_tasks()
    if partial_pair == (False, False):
        if paths.c_partial.exists() or paths.c_progress.exists():
            raise GateError("refusing ambiguous C cache initialization")
        paths.directory.mkdir(parents=True, exist_ok=True)
        matrix = open_memmap_exclusive(
            paths.c_partial,
            dtype=np.dtype("<u4"),
            shape=(TOTAL_ROWS, NEW_COLUMNS),
        )
        matrix.flush()
        fsync_path(paths.c_partial)
        progress: dict[str, object] = {
            "schema": SCHEMA_C_CACHE,
            "state": "building",
            "shape": [TOTAL_ROWS, NEW_COLUMNS],
            "dtype": "<u4",
            "prime": PRIME,
            "workers": WORKERS,
            "chunk_rows": CHUNK_ROWS,
            "all_new_columns_retained": True,
            "price_filtering_allowed": False,
            "evaluator": evaluator.cache_contract(),
            "custody": custody,
            "completed_chunks": {},
        }
        write_json_exclusive(paths.c_progress, progress)
    else:
        progress = read_json(paths.c_progress)
        matrix = np.load(paths.c_partial, mmap_mode="r+", allow_pickle=False)
        if (
            progress.get("schema") != SCHEMA_C_CACHE
            or progress.get("state") != "building"
            or progress.get("shape") != [TOTAL_ROWS, NEW_COLUMNS]
            or progress.get("dtype") != "<u4"
            or progress.get("prime") != PRIME
            or progress.get("workers") != WORKERS
            or progress.get("chunk_rows") != CHUNK_ROWS
            or progress.get("all_new_columns_retained") is not True
            or progress.get("price_filtering_allowed") is not False
            or progress.get("evaluator") != evaluator.cache_contract()
            or progress.get("custody") != custody
            or matrix.shape != (TOTAL_ROWS, NEW_COLUMNS)
            or matrix.dtype != np.dtype("<u4")
        ):
            raise GateError("resumable C cache contract drift")
        completed = progress.get("completed_chunks")
        if not isinstance(completed, dict):
            raise GateError("C cache progress chunk map malformed")
        for chunk, start, stop in tasks:
            key = str(chunk)
            if key in completed:
                observed = hashlib.sha256(
                    memoryview(np.ascontiguousarray(matrix[start:stop])).cast("B")
                ).hexdigest()
                if completed[key] != observed:
                    raise GateError(f"completed C cache chunk mutation: {chunk}")

    completed = progress["completed_chunks"]
    assert isinstance(completed, dict)
    remaining = [task for task in tasks if str(task[0]) not in completed]
    global _WORKER_EVALUATOR
    _WORKER_EVALUATOR = evaluator
    context = mp.get_context("fork")
    pending: list[tuple[int, int, int, str]] = []
    if remaining:
        with context.Pool(
            WORKERS,
            initializer=initialize_matrix_worker,
            initargs=(str(paths.c_partial),),
        ) as pool:
            try:
                for result in pool.imap(evaluate_matrix_chunk, remaining, chunksize=1):
                    pending.append(result)
                    if time.monotonic() >= deadline:
                        pool.terminate()
                        raise TimeoutError(
                            "C cache construction crossed six-hour deadline"
                        )
                    if len(pending) >= PROGRESS_COMMIT_CHUNKS:
                        matrix.flush()
                        fsync_path(paths.c_partial)
                        for chunk, _start, _stop, digest in pending:
                            completed[str(chunk)] = digest
                        write_json_atomic(paths.c_progress, progress)
                        pending.clear()
            except BaseException:
                pool.terminate()
                raise
        if pending:
            matrix.flush()
            fsync_path(paths.c_partial)
            for chunk, _start, _stop, digest in pending:
                completed[str(chunk)] = digest
            write_json_atomic(paths.c_progress, progress)
    if len(completed) != len(tasks):
        raise GateError("C cache build ended with missing chunks")
    live_hashes = completed_chunk_hashes(matrix, tasks)
    if live_hashes != completed:
        raise GateError("C cache final chunk-hash replay failed")
    matrix.flush()
    fsync_path(paths.c_partial)
    end_custody = recapture_custody(custody)
    if end_custody != custody:
        raise GateError("C cache source custody changed during construction")
    receipt = {
        "schema": SCHEMA_C_CACHE,
        "state": "complete",
        "path": relative_path(paths.c_final),
        "shape": [TOTAL_ROWS, NEW_COLUMNS],
        "dtype": "<u4",
        "prime": PRIME,
        "workers": WORKERS,
        "worker_start_method": "fork",
        "chunk_rows": CHUNK_ROWS,
        "chunk_count": len(tasks),
        "chunk_hashes_sha256": canonical_sha256(live_hashes),
        "all_new_columns_retained": True,
        "price_filtering_allowed": False,
        "evaluator": evaluator.cache_contract(),
        "npy_sha256": sha256_path(paths.c_partial),
        "raw_uint32_c_sha256": raw_sha256(matrix),
        "custody": {"start": custody, "end": end_custody, "identical": True},
    }
    write_json_exclusive(paths.c_receipt_pending, receipt)
    if paths.c_final.exists() or paths.c_receipt.exists():
        raise GateError("refusing to overwrite final C cache transaction")
    del matrix
    promote_exclusive(paths.c_partial, paths.c_final)
    promote_exclusive(paths.c_receipt_pending, paths.c_receipt)
    paths.c_progress.unlink()
    return validate_complete_cache(
        paths.c_final,
        paths.c_receipt,
        schema=SCHEMA_C_CACHE,
        shape=(TOTAL_ROWS, NEW_COLUMNS),
        custody=custody,
    )


def validate_inverse(
    adapter: ModuleType,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, object]]:
    rows, columns, modular = adapter.load_basis_contract()
    receipt = read_json(INVERSE_RECEIPT)
    inverse = np.load(INVERSE_CACHE, mmap_mode="r", allow_pickle=False)
    if (
        receipt.get("schema") != "max11-g0079-native-flint-inverse-v1"
        or receipt.get("adapter_script_sha256") != EXPECTED_NATIVE_ADAPTER_SHA256
        or receipt.get("inverse_npy_sha256") != EXPECTED_INVERSE_CACHE_SHA256
        or receipt.get("inverse_uint32_c_sha256") != EXPECTED_INVERSE_DATA_SHA256
        or receipt.get("reloaded_inverse_uint32_c_sha256")
        != EXPECTED_INVERSE_DATA_SHA256
        or receipt.get("full_export_stream_equality") is not True
        or receipt.get("full_product_replay", {}).get("identity_replay") is not True
        or inverse.shape != (BASIS_RANK, BASIS_RANK)
        or inverse.dtype != np.dtype("<u4")
        or raw_sha256(inverse) != EXPECTED_INVERSE_DATA_SHA256
        or canonical_sha256(rows.astype(int).tolist()) != EXPECTED_BASIS_ROWS_SHA256
        or canonical_sha256(columns.astype(int).tolist())
        != EXPECTED_BASIS_COLUMNS_SHA256
    ):
        raise GateError("certified inverse/basis contract drift")
    q = np.asarray(sorted(set(range(TOTAL_ROWS)) - set(map(int, rows))), dtype=np.int64)
    if q.shape != (QUOTIENT_ROWS,):
        raise GateError("ordered complement Q census drift")
    return rows, columns, q, modular


def validate_resource_contract(paths: CachePaths) -> dict[str, object]:
    with Path("/proc/meminfo").open("rt", encoding="utf-8") as source:
        available_bytes = next(
            (
                int(line.split()[1]) * 1024
                for line in source
                if line.startswith("MemAvailable:")
            ),
            0,
        )
    free_bytes = shutil.disk_usage(paths.directory.parent.resolve()).free
    c_bytes = TOTAL_ROWS * NEW_COLUMNS * 4
    s_bytes = QUOTIENT_ROWS * SCHUR_COLUMNS * 4
    needed_disk = 2 * 1024**3
    if not paths.c_final.exists():
        needed_disk += c_bytes
    if not paths.s_final.exists():
        needed_disk += s_bytes
    if not paths.r_final.exists():
        needed_disk += s_bytes
    if available_bytes < int(MINIMUM_AVAILABLE_GIB * 1024**3):
        raise MemoryError(
            f"available memory {available_bytes} below {MINIMUM_AVAILABLE_GIB} GiB gate"
        )
    if free_bytes < max(int(MINIMUM_FREE_DISK_GIB * 1024**3), needed_disk):
        raise OSError(
            f"free disk {free_bytes} below registered gate {max(int(MINIMUM_FREE_DISK_GIB * 1024**3), needed_disk)}"
        )
    return {
        "available_bytes": available_bytes,
        "free_disk_bytes": free_bytes,
        "dynamic_required_disk_bytes": needed_disk,
        "minimum_available_gib": MINIMUM_AVAILABLE_GIB,
        "minimum_free_disk_gib": MINIMUM_FREE_DISK_GIB,
        "projected_minimum_native_peak_bytes": PROJECTED_MINIMUM_PEAK_BYTES,
        "dense_schur_entries": EXPECTED_DENSE_SCHUR_ENTRIES,
        "projected_dense_multiply_seconds": EXPECTED_PROJECTED_DENSE_MULTIPLY_SECONDS,
        "projected_dense_rank_seconds": EXPECTED_PROJECTED_DENSE_RANK_SECONDS,
        "projected_whole_kernel_seconds_conservative": EXPECTED_PROJECTED_KERNEL_SECONDS,
    }


def validate_preflight_resource_estimates() -> dict[str, object]:
    receipt = read_gzip(G0079_PREFLIGHT)
    performance = receipt.get("performance_benchmark")
    if not isinstance(performance, dict):
        raise GateError("G-0079 preflight lacks performance benchmark")
    expected = {
        "dense_schur_entries": EXPECTED_DENSE_SCHUR_ENTRIES,
        "projected_dense_multiply_seconds": EXPECTED_PROJECTED_DENSE_MULTIPLY_SECONDS,
        "projected_dense_rank_seconds": EXPECTED_PROJECTED_DENSE_RANK_SECONDS,
        "projected_dense_kernel_seconds_conservative": EXPECTED_PROJECTED_KERNEL_SECONDS,
        "minimum_projected_peak_bytes": PROJECTED_MINIMUM_PEAK_BYTES,
        "python_flint_bulk_minor_conversion_allowed": False,
    }
    for key, value in expected.items():
        if performance.get(key) != value:
            raise GateError(f"frozen resource estimate drift: {key}")
    return expected


def independent_support_replay(
    runner: ModuleType,
    preflight: ModuleType,
    g75: ModuleType,
    family: object,
    price_report: dict[str, object],
    functional: object,
    c_matrix: np.ndarray,
    old: np.ndarray,
    deadline: float,
) -> dict[str, object]:
    rows = np.asarray(functional.rows, dtype=np.int64)
    if rows.shape != (230,) or len(set(map(int, rows))) != 230:
        raise GateError("G-0078 support row census drift")
    values = runner.evaluate_representatives_nested_on_rows(
        preflight,
        g75,
        family.bases,
        family.new_representatives,
        rows.astype(int).tolist(),
    )
    if time.monotonic() >= deadline:
        raise TimeoutError("independent 230-row replay crossed six-hour deadline")
    if values.shape != (230, NEW_COLUMNS) or values.dtype != np.dtype("<i8"):
        raise GateError("independent support matrix shape/dtype drift")
    observed_raw = raw_sha256(values)
    if observed_raw != EXPECTED_SUPPORT_VALUES_RAW_SHA256:
        raise GateError("independent 230-row raw semantic hash drift")
    if not np.array_equal(
        np.remainder(values, PRIME).astype(np.uint32), c_matrix[rows]
    ):
        raise GateError("independent 230-row replay differs from C cache residues")
    target_values = np.ascontiguousarray(old[rows, -1])
    if raw_sha256(target_values) != EXPECTED_TARGET_VALUES_RAW_SHA256:
        raise GateError("230-row MAX11 target raw hash drift")
    scientific = price_report["scientific_payload"]
    vector = scientific["complete_price_vector"]
    exact_prices = runner.integer_pairings(functional.primitive_weights, values)
    if list(map(str, exact_prices)) != vector["prices"]:
        raise GateError("independent support replay does not reproduce exact prices")
    target_pairing = sum(
        weight * int(value)
        for weight, value in zip(
            functional.primitive_weights, target_values, strict=True
        )
    )
    if target_pairing != functional.expected_primitive_target:
        raise GateError(
            "independent support replay does not reproduce exact target price"
        )
    return {
        "support_rows": rows.astype(int).tolist(),
        "support_rows_sha256": canonical_sha256(rows.astype(int).tolist()),
        "independent_nested_raw_int64_c_sha256": observed_raw,
        "cache_residues_all_match": True,
        "exact_prices_all_match": True,
        "target_raw_int64_sha256": raw_sha256(target_values),
        "exact_target_pairing": str(target_pairing),
        "all_new_columns_replayed": NEW_COLUMNS,
    }


def bind_extended_native(native: object) -> None:
    native.lib.nmod_mat_rref.argtypes = [ctypes.c_void_p]
    native.lib.nmod_mat_rref.restype = ctypes.c_long
    native.lib.nmod_mat_det.argtypes = [ctypes.c_void_p]
    native.lib.nmod_mat_det.restype = ctypes.c_ulong


def fill_native_array(native: object, matrix: object, source: np.ndarray) -> None:
    rows, columns = source.shape
    for row in range(rows):
        values = np.remainder(source[row], PRIME).astype(np.uint64, copy=False)
        native.row(matrix, row, columns)[:] = values


def load_native_cache(native: object, path: Path, shape: tuple[int, int]) -> object:
    source = np.load(path, mmap_mode="r", allow_pickle=False)
    if source.shape != shape or source.dtype != np.dtype("<u4"):
        raise GateError(f"native cache source shape/dtype drift: {path}")
    matrix = native.initialize(shape[0], shape[1], PRIME)
    try:
        for row in range(shape[0]):
            native.row(matrix, row, shape[1])[:] = source[row].astype(np.uint64)
    except BaseException:
        native.clear(matrix)
        raise
    return matrix


def export_native_cache(
    native: object,
    matrix: object,
    paths: CachePaths,
    custody: dict[str, str],
) -> dict[str, object]:
    if any(
        path.exists() or path.is_symlink()
        for path in (
            paths.s_final,
            paths.s_partial,
            paths.s_receipt,
            paths.s_receipt_pending,
        )
    ):
        raise GateError("refusing to overwrite/merge Schur cache state")
    exported = open_memmap_exclusive(
        paths.s_partial,
        dtype=np.dtype("<u4"),
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
    )
    raw_digest = hashlib.sha256()
    for row in range(QUOTIENT_ROWS):
        values = native.row(matrix, row, SCHUR_COLUMNS).astype(np.uint32)
        exported[row] = values
        raw_digest.update(memoryview(np.ascontiguousarray(values)).cast("B"))
    exported.flush()
    fsync_path(paths.s_partial)
    end = recapture_custody(custody)
    if end != custody:
        raise GateError("source custody changed during Schur construction")
    receipt = {
        "schema": SCHEMA_S_CACHE,
        "state": "complete",
        "path": relative_path(paths.s_final),
        "shape": [QUOTIENT_ROWS, SCHUR_COLUMNS],
        "dtype": "<u4",
        "prime": PRIME,
        "column_order": "all 18,582 new columns in registered order, then target",
        "all_new_columns_retained": True,
        "price_filtering_allowed": False,
        "npy_sha256": sha256_path(paths.s_partial),
        "raw_uint32_c_sha256": raw_digest.hexdigest(),
        "custody": {"start": custody, "end": end, "identical": True},
    }
    write_json_exclusive(paths.s_receipt_pending, receipt)
    del exported
    promote_exclusive(paths.s_partial, paths.s_final)
    promote_exclusive(paths.s_receipt_pending, paths.s_receipt)
    return receipt


def construct_or_load_s_cache(
    adapter: ModuleType,
    paths: CachePaths,
    custody: dict[str, str],
    old: np.ndarray,
    c_matrix: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    q: np.ndarray,
) -> tuple[np.ndarray, dict[str, object]]:
    pair = (paths.s_final.exists(), paths.s_receipt.exists())
    partial = (paths.s_partial.exists(), paths.s_receipt_pending.exists())
    if pair == (True, True):
        if any(partial):
            raise GateError("complete Schur cache coexists with partial state")
        return validate_complete_cache(
            paths.s_final,
            paths.s_receipt,
            schema=SCHEMA_S_CACHE,
            shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
            custody=custody,
        )
    if any(pair) or any(partial):
        raise GateError("partial Schur cache transaction; hostile audit required")

    inverse = np.load(INVERSE_CACHE, mmap_mode="r", allow_pickle=False)
    native = adapter.NativeFlint()
    bind_extended_native(native)
    aqp = native.initialize(QUOTIENT_ROWS, BASIS_RANK, PRIME)
    binv = native.initialize(BASIS_RANK, BASIS_RANK, PRIME)
    lam = native.initialize(QUOTIENT_ROWS, BASIS_RANK, PRIME)
    right = None
    schur = None
    try:
        for local, raw_row in enumerate(q):
            adapter.fill_native_row(
                native, aqp, local, np.remainder(old[int(raw_row), columns], PRIME)
            )
        for row in range(BASIS_RANK):
            adapter.fill_native_row(native, binv, row, inverse[row])
        native.lib.nmod_mat_mul(
            native.pointer(lam), native.pointer(aqp), native.pointer(binv)
        )
        native.clear(aqp)
        aqp = None
        native.clear(binv)
        binv = None
        right = native.initialize(BASIS_RANK, SCHUR_COLUMNS, PRIME)
        joined = np.empty(SCHUR_COLUMNS, dtype=np.uint64)
        for local, raw_row in enumerate(rows):
            joined[:-1] = c_matrix[int(raw_row)]
            joined[-1] = int(old[int(raw_row), -1]) % PRIME
            adapter.fill_native_row(native, right, local, joined)
        schur = native.initialize(QUOTIENT_ROWS, SCHUR_COLUMNS, PRIME)
        native.lib.nmod_mat_mul(
            native.pointer(schur), native.pointer(lam), native.pointer(right)
        )
        native.clear(lam)
        lam = None
        native.clear(right)
        right = None
        raw = np.empty(SCHUR_COLUMNS, dtype=np.uint64)
        for local, raw_row in enumerate(q):
            raw[:-1] = c_matrix[int(raw_row)]
            raw[-1] = int(old[int(raw_row), -1]) % PRIME
            row_view = native.row(schur, local, SCHUR_COLUMNS)
            row_view[:] = np.remainder(raw + PRIME - row_view, PRIME)
        export_native_cache(native, schur, paths, custody)
    finally:
        for matrix in (schur, right, lam, binv, aqp):
            if matrix is not None:
                native.clear(matrix)
        native.cleanup()
    return validate_complete_cache(
        paths.s_final,
        paths.s_receipt,
        schema=SCHEMA_S_CACHE,
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
        custody=custody,
    )


def price_scalar_relation(
    schur_row: np.ndarray,
    prices_mod: Sequence[int],
    target_mod: int,
) -> dict[str, object]:
    price = np.asarray([*map(int, prices_mod), int(target_mod)], dtype=np.uint64)
    row = np.remainder(np.asarray(schur_row, dtype=np.uint64), PRIME)
    if row.shape != (SCHUR_COLUMNS,) or price.shape != (SCHUR_COLUMNS,):
        raise GateError("price/Schur scalar fixture shape drift")
    first = next((index for index, value in enumerate(price) if int(value)), None)
    if first is None:
        raise GateError("price augmented row is zero modulo registered prime")
    scalar = int(row[first]) * pow(int(price[first]), -1, PRIME) % PRIME
    if scalar == 0 or not np.array_equal(row, np.remainder(price * scalar, PRIME)):
        raise GateError(
            "G-0078 price row is not one common nonzero Schur scalar multiple"
        )
    return {
        "first_nonzero_coordinate": first,
        "scalar_mod_prime": scalar,
        "schur_row_uint32_sha256": raw_sha256(row.astype(np.uint32)),
        "price_augmented_uint32_sha256": raw_sha256(price.astype(np.uint32)),
        "common_nonzero_scalar_all_coordinates": True,
    }


def recompute_failing_schur_row(
    old: np.ndarray,
    c_matrix: np.ndarray,
    inverse: np.ndarray,
    basis_rows: np.ndarray,
    basis_columns: np.ndarray,
    failing_row: int,
) -> np.ndarray:
    coordinates = np.remainder(
        np.remainder(old[failing_row, basis_columns], PRIME).astype(np.uint64)
        @ inverse.astype(np.uint64),
        PRIME,
    )
    right = np.empty((BASIS_RANK, SCHUR_COLUMNS), dtype=np.uint32)
    right[:, :-1] = c_matrix[basis_rows]
    right[:, -1] = np.remainder(old[basis_rows, -1], PRIME).astype(np.uint32)
    correction = np.remainder(coordinates @ right.astype(np.uint64), PRIME)
    raw = np.empty(SCHUR_COLUMNS, dtype=np.uint64)
    raw[:-1] = c_matrix[failing_row]
    raw[-1] = int(old[failing_row, -1]) % PRIME
    return np.remainder(raw + PRIME - correction, PRIME).astype(np.uint32)


def scan_rref(native: object, matrix: object, rank: int) -> tuple[list[int], list[int]]:
    if not 0 <= rank <= QUOTIENT_ROWS:
        raise GateError("native RREF returned impossible rank")
    pivots: list[int] = []
    rhs: list[int] = []
    previous = -1
    for row_index in range(rank):
        row = np.remainder(native.row(matrix, row_index, SCHUR_COLUMNS), PRIME)
        nonzero = np.flatnonzero(row)
        if not len(nonzero):
            raise GateError("native RREF rank row is zero")
        pivot = int(nonzero[0])
        if pivot <= previous or int(row[pivot]) != 1:
            raise GateError("native RREF pivot order/normalization drift")
        pivots.append(pivot)
        rhs.append(int(row[-1]))
        previous = pivot
    for row_index in range(rank, QUOTIENT_ROWS):
        if np.count_nonzero(
            np.remainder(native.row(matrix, row_index, SCHUR_COLUMNS), PRIME)
        ):
            raise GateError("native RREF tail contains nonzero row")
    return pivots, rhs


def scan_rref_array(matrix: np.ndarray, rank: int) -> tuple[list[int], list[int]]:
    if matrix.shape != (QUOTIENT_ROWS, SCHUR_COLUMNS) or matrix.dtype != np.dtype(
        "<u4"
    ):
        raise GateError("persisted RREF shape/dtype drift")
    if not 0 <= rank <= QUOTIENT_ROWS:
        raise GateError("persisted RREF rank outside row census")
    pivots: list[int] = []
    rhs: list[int] = []
    previous = -1
    for row_index in range(rank):
        row = np.remainder(matrix[row_index], PRIME)
        nonzero = np.flatnonzero(row)
        if not len(nonzero):
            raise GateError("persisted RREF rank row is zero")
        pivot = int(nonzero[0])
        if pivot <= previous or int(row[pivot]) != 1:
            raise GateError("persisted RREF pivot order/normalization drift")
        pivots.append(pivot)
        rhs.append(int(row[-1]))
        previous = pivot
    for start in range(rank, QUOTIENT_ROWS, 32):
        if np.count_nonzero(
            np.remainder(matrix[start : min(start + 32, QUOTIENT_ROWS)], PRIME)
        ):
            raise GateError("persisted RREF tail contains a nonzero row")
    return pivots, rhs


def export_native_rref_cache(
    native: object,
    matrix: object,
    rank_augmented: int,
    pivots: Sequence[int],
    paths: CachePaths,
    custody: dict[str, str],
    rref_seconds: float,
) -> dict[str, object]:
    targets = (paths.r_final, paths.r_partial, paths.r_receipt, paths.r_receipt_pending)
    if any(path.exists() or path.is_symlink() for path in targets):
        raise GateError("refusing to overwrite/merge RREF cache state")
    exported = open_memmap_exclusive(
        paths.r_partial,
        dtype=np.dtype("<u4"),
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
    )
    raw_digest = hashlib.sha256()
    for row in range(QUOTIENT_ROWS):
        values = np.remainder(native.row(matrix, row, SCHUR_COLUMNS), PRIME).astype(
            np.uint32
        )
        exported[row] = values
        raw_digest.update(memoryview(np.ascontiguousarray(values)).cast("B"))
    exported.flush()
    fsync_path(paths.r_partial)
    pivot_new = [int(pivot) for pivot in pivots if pivot < NEW_COLUMNS]
    free_new = sorted(set(range(NEW_COLUMNS)) - set(pivot_new))
    target_pivot = bool(pivots and pivots[-1] == NEW_COLUMNS)
    rank_new = rank_augmented - int(target_pivot)
    end = recapture_custody(custody)
    if end != custody:
        raise GateError("source custody changed while persisting RREF")
    receipt = {
        "schema": SCHEMA_R_CACHE,
        "state": "complete",
        "path": relative_path(paths.r_final),
        "source_pre_RREF_S_path": relative_path(paths.s_final),
        "source_pre_RREF_S_sha256": sha256_path(paths.s_final),
        "shape": [QUOTIENT_ROWS, SCHUR_COLUMNS],
        "dtype": "<u4",
        "prime": PRIME,
        "column_order": "all 18,582 new columns in registered order, then target",
        "all_new_columns_retained": True,
        "price_filtering_allowed": False,
        "in_place_FLINT_RREF": True,
        "rank_schur_new": rank_new,
        "rank_schur_augmented": rank_augmented,
        "target_coordinate_is_pivot": target_pivot,
        "ordered_pivot_columns": list(map(int, pivots)),
        "ordered_pivot_columns_sha256": canonical_sha256(list(map(int, pivots))),
        "ordered_pivot_local_new_columns": pivot_new,
        "ordered_free_local_new_columns": free_new,
        "ordered_free_local_new_columns_sha256": canonical_sha256(free_new),
        "nullspace_parameterization": (
            "For each free new column f, set x_f=1 and all other free coordinates to zero; "
            "for pivot row i with pivot p_i set x_p_i=-RREF[i,f] mod p. The stored full "
            "target-last RREF and ordered pivot/free lists therefore preserve the complete "
            "finite-row new-column nullspace transform for later global gated-facet CEGIS."
        ),
        "rref_seconds": rref_seconds,
        "npy_sha256": sha256_path(paths.r_partial),
        "raw_uint32_c_sha256": raw_digest.hexdigest(),
        "custody": {"start": custody, "end": end, "identical": True},
    }
    write_json_exclusive(paths.r_receipt_pending, receipt)
    del exported
    promote_exclusive(paths.r_partial, paths.r_final)
    promote_exclusive(paths.r_receipt_pending, paths.r_receipt)
    return receipt


def load_or_compute_rref(
    adapter: ModuleType,
    paths: CachePaths,
    custody: dict[str, str],
) -> tuple[np.ndarray, dict[str, object], list[int], list[int]]:
    pair = (paths.r_final.exists(), paths.r_receipt.exists())
    partial = (paths.r_partial.exists(), paths.r_receipt_pending.exists())
    if pair == (True, True):
        if any(partial):
            raise GateError("complete RREF cache coexists with partial state")
        rref, receipt = validate_complete_cache(
            paths.r_final,
            paths.r_receipt,
            schema=SCHEMA_R_CACHE,
            shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
            custody=custody,
        )
        rank = int(receipt.get("rank_schur_augmented", -1))
        pivots, rhs = scan_rref_array(rref, rank)
        pivot_new = [pivot for pivot in pivots if pivot < NEW_COLUMNS]
        free_new = sorted(set(range(NEW_COLUMNS)) - set(pivot_new))
        target_pivot = bool(pivots and pivots[-1] == NEW_COLUMNS)
        if (
            receipt.get("source_pre_RREF_S_sha256") != sha256_path(paths.s_final)
            or receipt.get("ordered_pivot_columns") != pivots
            or receipt.get("ordered_pivot_columns_sha256") != canonical_sha256(pivots)
            or receipt.get("ordered_pivot_local_new_columns") != pivot_new
            or receipt.get("ordered_free_local_new_columns") != free_new
            or receipt.get("ordered_free_local_new_columns_sha256")
            != canonical_sha256(free_new)
            or receipt.get("rank_schur_new") != rank - int(target_pivot)
            or receipt.get("target_coordinate_is_pivot") is not target_pivot
        ):
            raise GateError("persisted RREF transform/receipt drift")
        return rref, receipt, pivots, rhs
    if any(pair) or any(partial):
        raise GateError("partial RREF cache transaction; hostile audit required")

    native = adapter.NativeFlint()
    bind_extended_native(native)
    matrix = load_native_cache(native, paths.s_final, (QUOTIENT_ROWS, SCHUR_COLUMNS))
    try:
        started = time.perf_counter()
        rank = int(native.lib.nmod_mat_rref(native.pointer(matrix)))
        rref_seconds = time.perf_counter() - started
        pivots, rhs = scan_rref(native, matrix, rank)
        export_native_rref_cache(
            native, matrix, rank, pivots, paths, custody, rref_seconds
        )
    finally:
        native.clear(matrix)
        native.cleanup()
    rref, receipt = validate_complete_cache(
        paths.r_final,
        paths.r_receipt,
        schema=SCHEMA_R_CACHE,
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
        custody=custody,
    )
    replay_pivots, replay_rhs = scan_rref_array(rref, rank)
    if replay_pivots != pivots or replay_rhs != rhs:
        raise GateError("persisted RREF differs from in-memory native result")
    return rref, receipt, pivots, rhs


def canonical_free_zero_solution(
    pivots: Sequence[int], rhs: Sequence[int]
) -> tuple[np.ndarray, np.ndarray]:
    if len(pivots) != len(rhs) or NEW_COLUMNS in pivots:
        raise GateError("cannot derive member solution from target-pivot RREF")
    new_pivots = np.asarray(
        [pivot for pivot in pivots if pivot < NEW_COLUMNS], dtype=np.int64
    )
    coefficients = np.asarray(
        [rhs[index] for index, pivot in enumerate(pivots) if pivot < NEW_COLUMNS],
        dtype=np.uint64,
    )
    if len(new_pivots) != len(pivots):
        raise GateError("unexpected non-new pivot in target-last member RREF")
    return new_pivots, coefficients


def derive_and_replay_solution(
    old: np.ndarray,
    c_matrix: np.ndarray,
    inverse: np.ndarray,
    basis_rows: np.ndarray,
    basis_columns: np.ndarray,
    new_pivots: np.ndarray,
    new_coefficients: np.ndarray,
) -> dict[str, object]:
    selected_c_r = c_matrix[basis_rows][:, new_pivots].astype(np.uint64)
    residual_r = np.remainder(
        np.remainder(old[basis_rows, -1], PRIME).astype(np.uint64)
        + PRIME
        - np.remainder(selected_c_r @ new_coefficients, PRIME),
        PRIME,
    )
    old_basis_coefficients = np.remainder(inverse.astype(np.uint64) @ residual_r, PRIME)
    residual_digest = hashlib.sha256()
    first_failure: tuple[int, int] | None = None
    for start in range(0, TOTAL_ROWS, 16):
        stop = min(start + 16, TOTAL_ROWS)
        old_values = np.remainder(old[start:stop][:, basis_columns], PRIME).astype(
            np.uint64
        )
        new_values = c_matrix[start:stop][:, new_pivots].astype(np.uint64)
        predicted = np.remainder(
            old_values @ old_basis_coefficients + new_values @ new_coefficients, PRIME
        )
        target = np.remainder(old[start:stop, -1], PRIME).astype(np.uint64)
        residual = np.remainder(predicted + PRIME - target, PRIME).astype(np.uint32)
        residual_digest.update(memoryview(np.ascontiguousarray(residual)).cast("B"))
        if first_failure is None:
            local = np.flatnonzero(residual)
            if len(local):
                first_failure = (start + int(local[0]), int(residual[int(local[0])]))
    if first_failure is not None:
        raise GateError(
            f"canonical modular solution raw-row replay failed: {first_failure}"
        )
    old_records = [
        {"global_column": int(column), "coefficient_mod_prime": int(value)}
        for column, value in zip(basis_columns, old_basis_coefficients, strict=True)
        if int(value)
    ]
    new_records = [
        {
            "local_new_column": int(column),
            "global_column": GLOBAL_NEW_START + int(column),
            "coefficient_mod_prime": int(value),
        }
        for column, value in zip(new_pivots, new_coefficients, strict=True)
        if int(value)
    ]
    return {
        "canonical_rule": "target-last RREF, all free new coordinates zero; old nonbasis coordinates zero",
        "old_basis_nonzero_coefficients": old_records,
        "new_pivot_nonzero_coefficients": new_records,
        "old_basis_nonzero_count": len(old_records),
        "new_nonzero_count": len(new_records),
        "all_16738_raw_rows_replayed": True,
        "residual_uint32_c_sha256": residual_digest.hexdigest(),
        "residual_all_zero": True,
    }


def full_row_rank_minor_evidence(
    adapter: ModuleType,
    s_cache: np.ndarray,
    pivot_new_columns: Sequence[int],
    old: np.ndarray,
    basis_rows: np.ndarray,
    basis_columns: np.ndarray,
) -> dict[str, object]:
    if len(pivot_new_columns) != QUOTIENT_ROWS:
        return {
            "rank_new_equals_quotient_rows": False,
            "characteristic_zero_consequence": None,
        }
    native = adapter.NativeFlint()
    bind_extended_native(native)
    schur_minor = native.initialize(QUOTIENT_ROWS, QUOTIENT_ROWS, PRIME)
    old_basis_minor = native.initialize(BASIS_RANK, BASIS_RANK, PRIME)
    try:
        selected = np.asarray(pivot_new_columns, dtype=np.intp)
        for row in range(QUOTIENT_ROWS):
            native.row(schur_minor, row, QUOTIENT_ROWS)[:] = s_cache[
                row, selected
            ].astype(np.uint64)
        for local, raw_row in enumerate(basis_rows):
            native.row(old_basis_minor, local, BASIS_RANK)[:] = np.remainder(
                old[int(raw_row), basis_columns], PRIME
            ).astype(np.uint64)
        schur_determinant = (
            int(native.lib.nmod_mat_det(native.pointer(schur_minor))) % PRIME
        )
        basis_determinant = (
            int(native.lib.nmod_mat_det(native.pointer(old_basis_minor))) % PRIME
        )
        integer_block_minor_determinant = basis_determinant * schur_determinant % PRIME
        if (
            schur_determinant == 0
            or basis_determinant == 0
            or integer_block_minor_determinant == 0
        ):
            raise GateError("RREF full-row pivot minor has zero native determinant")
    finally:
        native.clear(old_basis_minor)
        native.clear(schur_minor)
        native.cleanup()
    return {
        "rank_new_equals_quotient_rows": True,
        "modular_schur_minor_shape": [QUOTIENT_ROWS, QUOTIENT_ROWS],
        "integer_block_minor_shape": [TOTAL_ROWS, TOTAL_ROWS],
        "integer_block_minor_row_order": "basis rows R followed by ordered complement Q",
        "integer_block_minor_column_order": "old basis columns P followed by selected new pivots",
        "pivot_local_new_columns": list(map(int, pivot_new_columns)),
        "pivot_local_new_columns_sha256": canonical_sha256(
            list(map(int, pivot_new_columns))
        ),
        "old_basis_det_mod_prime": basis_determinant,
        "modular_schur_det_mod_prime": schur_determinant,
        "integer_block_minor_det_mod_prime": integer_block_minor_determinant,
        "block_determinant_identity": "det([B,C_R;A_QP,C_Q]) = det(B)*det(C_Q-A_QP*B^-1*C_R) mod p",
        "cached_schur_entries_claimed_integer_over_Q": False,
        "integer_raw_column_minor_nonzero_over_Q": True,
        "characteristic_zero_consequence": (
            "The raw 16,738-square integer minor [old basis P | selected new pivots], in row "
            "order [R,Q], has determinant det(B)*det(S_selected) nonzero modulo 1,000,003. "
            "Its integer determinant is therefore nonzero over Q, so every target vector on "
            "these frozen rows has some rational coefficient vector in this frozen dictionary. "
            "This proves rational finite-row existence but is not an exact lift of the displayed "
            "modular coefficients, a global CPWL identity, or an unrestricted-network theorem."
        ),
    }


def native_rref_and_decide(
    adapter: ModuleType,
    paths: CachePaths,
    custody: dict[str, str],
    old: np.ndarray,
    c_matrix: np.ndarray,
    inverse: np.ndarray,
    basis_rows: np.ndarray,
    basis_columns: np.ndarray,
) -> dict[str, object]:
    s_cache = np.load(paths.s_final, mmap_mode="r", allow_pickle=False)
    _rref, rref_receipt, pivots, rhs = load_or_compute_rref(adapter, paths, custody)
    rank_augmented = int(rref_receipt["rank_schur_augmented"])
    target_pivot = bool(pivots and pivots[-1] == NEW_COLUMNS)
    if NEW_COLUMNS in pivots[:-1]:
        raise GateError("target-last pivot appears before final pivot")
    rank_new = rank_augmented - int(target_pivot)
    pivot_new = [pivot for pivot in pivots if pivot < NEW_COLUMNS]
    if len(pivot_new) != rank_new:
        raise GateError("new-column pivot census differs from rank")
    base = {
        "rank_schur_new": rank_new,
        "rank_schur_augmented": rank_augmented,
        "target_last": True,
        "target_coordinate_is_pivot": target_pivot,
        "pivot_local_new_columns": pivot_new,
        "pivot_global_new_columns": [GLOBAL_NEW_START + pivot for pivot in pivot_new],
        "pivot_local_new_columns_sha256": canonical_sha256(pivot_new),
        "rref_seconds": rref_receipt["rref_seconds"],
        "persisted_RREF": rref_receipt,
    }
    if target_pivot:
        base.update(
            {
                "result": "MODULAR_SEPARATION_DISCOVERY",
                "claim_boundary": (
                    "The target is separated only from the complete frozen 26,689-column "
                    "dictionary on the frozen 16,738 rows modulo 1,000,003. This is not a "
                    "characteristic-zero, global, or unrestricted lower bound."
                ),
            }
        )
        return base
    new_pivots, new_coefficients = canonical_free_zero_solution(pivots, rhs)
    solution = derive_and_replay_solution(
        old, c_matrix, inverse, basis_rows, basis_columns, new_pivots, new_coefficients
    )
    minor = full_row_rank_minor_evidence(
        adapter, s_cache, pivot_new, old, basis_rows, basis_columns
    )
    if minor["rank_new_equals_quotient_rows"]:
        boundary = (
            "The certified nonzero raw integer block minor proves rational spanning of every "
            "target on these 16,738 frozen rows. The displayed coefficients remain modular; "
            "a separately replayed exact Q lift is required for explicit rational coefficients, "
            "and global CPWL replay is required for any unrestricted depth-two theorem."
        )
    else:
        boundary = (
            "This is exact modular compatibility for the complete frozen dictionary on "
            "16,738 rows. It supplies no rational coefficients until an exact Q lift, and "
            "no global CPWL identity or unrestricted depth-two theorem until global replay."
        )
    base.update(
        {
            "result": "MODULAR_MEMBERSHIP_DISCOVERY",
            "solution": solution,
            "full_row_rank_minor_evidence": minor,
            "claim_boundary": boundary,
        }
    )
    return base


def internal_kernel(
    registration: Registration, scratch_output: Path
) -> dict[str, object]:
    begun = time.monotonic()
    deadline = begun + MAXIMUM_WALL_SECONDS
    custody = capture_custody(registration.runner_sha256, registration.path)
    bindings = replay_static_bindings()
    resources = validate_resource_contract(cache_paths(registration.cache_dir))
    resource_estimates = validate_preflight_resource_estimates()
    runner, preflight, g75, family, semantic = load_g0079_context()
    price_report, functional = load_price_contract(runner)
    adapter = load_owned_module(
        NATIVE_ADAPTER, EXPECTED_NATIVE_ADAPTER_SHA256, "max11_native_adapter_for_g0081"
    )
    basis_rows, basis_columns, q, _modular = validate_inverse(adapter)
    old = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
    inverse = np.load(INVERSE_CACHE, mmap_mode="r", allow_pickle=False)
    if old.shape != (TOTAL_ROWS, OLD_COLUMNS + 1) or old.dtype != np.dtype("<i8"):
        raise GateError("frozen old augmented matrix shape/dtype drift")
    paths = cache_paths(registration.cache_dir)
    evaluator = FastEvaluator(g75, family.bases, family.new_representatives)
    c_matrix, c_receipt = build_or_load_c_cache(paths, evaluator, custody, deadline)
    support_replay = independent_support_replay(
        runner,
        preflight,
        g75,
        family,
        price_report,
        functional,
        c_matrix,
        old,
        deadline,
    )
    s_cache, s_receipt = construct_or_load_s_cache(
        adapter, paths, custody, old, c_matrix, basis_rows, basis_columns, q
    )
    exact_payload = read_gzip(G0078_EXACT).get("scientific_payload")
    if not isinstance(exact_payload, dict):
        raise GateError("G-0078 exact payload missing")
    failing_row = int(exact_payload.get("failing_raw_row", -1))
    q_positions = {int(raw): index for index, raw in enumerate(q)}
    if failing_row not in q_positions:
        raise GateError("artifact-specified G-0078 failing row is not in Q")
    recomputed = recompute_failing_schur_row(
        old, c_matrix, inverse, basis_rows, basis_columns, failing_row
    )
    if not np.array_equal(recomputed, s_cache[q_positions[failing_row]]):
        raise GateError(
            "recomputed failing-row Schur vector differs from pre-RREF cache"
        )
    price_scientific = price_report["scientific_payload"]
    price_vector = price_scientific["complete_price_vector"]
    price_exact = price_scientific["exact_functional"]
    scalar = price_scalar_relation(
        recomputed,
        price_vector["prices_mod_prime"],
        int(price_exact["target_pairing_mod_prime"]),
    )
    scalar["artifact_specified_failing_raw_row"] = failing_row
    scalar["ordered_Q_position"] = q_positions[failing_row]
    decision = native_rref_and_decide(
        adapter, paths, custody, old, c_matrix, inverse, basis_rows, basis_columns
    )
    end_custody = capture_custody(registration.runner_sha256, registration.path)
    if end_custody != custody:
        raise GateError("registered input/source custody changed during native kernel")
    scientific = {
        "schema": SCHEMA_RESULT,
        "result": decision["result"],
        "subject": {
            "prime": PRIME,
            "rows": TOTAL_ROWS,
            "old_columns": OLD_COLUMNS,
            "new_columns": NEW_COLUMNS,
            "all_new_columns_retained": True,
            "price_filtering_allowed": False,
            "basis_rank": BASIS_RANK,
            "quotient_rows": QUOTIENT_ROWS,
        },
        "C_cache": c_receipt,
        "independent_230_row_replay": support_replay,
        "pre_RREF_S_cache": s_receipt,
        "price_row_scalar_relation": scalar,
        "native_decision": decision,
        "claim_boundary": decision["claim_boundary"],
    }
    report = {
        "schema": SCHEMA_RESULT,
        "scientific_payload": scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "runner_sha256": registration.runner_sha256,
        "preregistration_sha256": registration.sha256,
        "bindings": bindings,
        "semantic_source_execution": semantic,
        "resource_gate": resources,
        "frozen_resource_estimates": resource_estimates,
        "custody": {"start": custody, "end": end_custody, "identical": True},
        "wall_seconds": time.monotonic() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
            "workers": WORKERS,
            "multiprocessing_start_method": "fork",
            "native_flint": "3.6.0",
        },
    }
    write_json_exclusive(scratch_output, report)
    return report


def resource_unresolved_report(
    registration: Registration,
    reason: str,
    begun: float,
    start_custody: dict[str, str],
) -> dict[str, object]:
    end = capture_custody(registration.runner_sha256, registration.path)
    scientific = {
        "schema": SCHEMA_RESULT,
        "result": "RESOURCE_UNRESOLVED",
        "reason": reason,
        "scientific_outcome_computed": False,
        "claim_boundary": "No modular membership or separation decision was obtained.",
    }
    return {
        "schema": SCHEMA_RESULT,
        "scientific_payload": scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "runner_sha256": registration.runner_sha256,
        "preregistration_sha256": registration.sha256,
        "custody": {
            "start": start_custody,
            "end": end,
            "identical": start_custody == end,
        },
        "wall_seconds": time.monotonic() - begun,
    }


def public_run(registration: Registration) -> dict[str, object]:
    paths = cache_paths(registration.cache_dir)
    paths.directory.mkdir(parents=True, exist_ok=True)
    begun = time.monotonic()
    start_custody = capture_custody(registration.runner_sha256, registration.path)
    with exclusive_cache_lock(paths.lock):
        try:
            validate_resource_contract(paths)
        except (MemoryError, OSError) as error:
            report = resource_unresolved_report(
                registration, str(error), begun, start_custody
            )
            write_gzip_exclusive(registration.output, report)
            return report
        token = secrets.token_hex(32)
        scratch = (
            paths.directory
            / f".kernel-outcome-{os.getpid()}-{secrets.token_hex(8)}.json"
        )
        if scratch.exists() or scratch.is_symlink():
            raise GateError("internal scratch collision")
        command = [
            str(REGISTERED_PYTHON),
            "-B",
            str(SCRIPT),
            "--internal-run",
            "--preregistration",
            str(registration.path),
            "--expected-runner-sha256",
            registration.runner_sha256,
            "--expected-preregistration-sha256",
            registration.sha256,
            "--output",
            str(registration.output),
            "--cache-dir",
            str(registration.cache_dir),
            "--internal-scratch-output",
            str(scratch),
            "--internal-token",
            token,
        ]
        environment = dict(os.environ)
        environment["G0081_INTERNAL_TOKEN"] = token
        process = subprocess.Popen(
            command,
            cwd=ROOT,
            env=environment,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
        try:
            stdout, stderr = process.communicate(timeout=MAXIMUM_WALL_SECONDS)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid, signal.SIGTERM)
            try:
                process.communicate(timeout=5)
            except subprocess.TimeoutExpired:
                os.killpg(process.pid, signal.SIGKILL)
                process.communicate()
            report = resource_unresolved_report(
                registration,
                f"isolated process group exceeded {MAXIMUM_WALL_SECONDS} seconds",
                begun,
                start_custody,
            )
            write_gzip_exclusive(registration.output, report)
            return report
        if process.returncode != 0:
            raise GateError(
                f"isolated kernel failed closed (exit={process.returncode}); "
                f"stdout={stdout[-2000:]!r}; stderr={stderr[-4000:]!r}"
            )
        if not scratch.is_file() or scratch.is_symlink():
            raise GateError("isolated kernel returned without one scratch report")
        report = read_json(scratch)
        if (
            report.get("schema") != SCHEMA_RESULT
            or report.get("runner_sha256") != registration.runner_sha256
            or report.get("preregistration_sha256") != registration.sha256
            or report.get("custody", {}).get("identical") is not True
        ):
            raise GateError("isolated kernel scratch contract drift")
        scratch.unlink()
        end = capture_custody(registration.runner_sha256, registration.path)
        if end != start_custody:
            raise GateError("launcher custody changed across isolated kernel")
        report["launcher"] = {
            "isolated_process_group": True,
            "hard_timeout_seconds": MAXIMUM_WALL_SECONDS,
            "native_cleanup_confined_to_child": True,
            "child_stdout": stdout.strip(),
            "child_stderr_tail": stderr[-4000:],
            "start_end_custody_identical": True,
        }
        write_gzip_exclusive(registration.output, report)
        return report


def numpy_rref_fixture(values: np.ndarray, prime: int) -> tuple[np.ndarray, int]:
    matrix = np.remainder(np.asarray(values, dtype=np.int64), prime).copy()
    pivot_row = 0
    for column in range(matrix.shape[1]):
        pivot = next(
            (row for row in range(pivot_row, matrix.shape[0]) if matrix[row, column]),
            None,
        )
        if pivot is None:
            continue
        matrix[[pivot_row, pivot]] = matrix[[pivot, pivot_row]]
        matrix[pivot_row] = (
            matrix[pivot_row] * pow(int(matrix[pivot_row, column]), -1, prime) % prime
        )
        for row in range(matrix.shape[0]):
            if row != pivot_row and matrix[row, column]:
                matrix[row] = (
                    matrix[row] - matrix[row, column] * matrix[pivot_row]
                ) % prime
        pivot_row += 1
        if pivot_row == matrix.shape[0]:
            break
    return matrix, pivot_row


def native_fixture(adapter: ModuleType, values: np.ndarray) -> tuple[np.ndarray, int]:
    native = adapter.NativeFlint()
    bind_extended_native(native)
    rows, columns = values.shape
    matrix = native.initialize(rows, columns, PRIME)
    try:
        fill_native_array(native, matrix, values)
        rank = int(native.lib.nmod_mat_rref(native.pointer(matrix)))
        result = np.stack(
            [native.row(matrix, row, columns).astype(np.uint32) for row in range(rows)]
        )
        return result, rank
    finally:
        native.clear(matrix)
        native.cleanup()


def self_test_native(adapter: ModuleType) -> dict[str, object]:
    native = adapter.NativeFlint()
    bind_extended_native(native)
    left = native.initialize(2, 2, PRIME)
    right = native.initialize(2, 3, PRIME)
    product = native.initialize(2, 3, PRIME)
    try:
        a = np.asarray([[2, 3], [5, 7]], dtype=np.int64)
        b = np.asarray([[11, 13, 17], [19, 23, 29]], dtype=np.int64)
        fill_native_array(native, left, a)
        fill_native_array(native, right, b)
        native.lib.nmod_mat_mul(
            native.pointer(product), native.pointer(left), native.pointer(right)
        )
        observed = np.stack(
            [native.row(product, row, 3).astype(np.uint32) for row in range(2)]
        )
        expected = np.remainder(a @ b, PRIME).astype(np.uint32)
        if not np.array_equal(observed, expected):
            raise GateError("native multiply fixture failed")
    finally:
        native.clear(product)
        native.clear(right)
        native.clear(left)
        native.cleanup()
    member = np.asarray([[1, 2, 5], [0, 1, 7]], dtype=np.int64)
    separator = np.asarray([[1, 0, 5], [0, 0, 1]], dtype=np.int64)
    for label, fixture, target_pivot in (
        ("member", member, False),
        ("separator", separator, True),
    ):
        expected_rref, expected_rank = numpy_rref_fixture(fixture, PRIME)
        actual_rref, actual_rank = native_fixture(adapter, fixture)
        if actual_rank != expected_rank or not np.array_equal(
            actual_rref, expected_rref.astype(np.uint32)
        ):
            raise GateError(f"native in-place RREF {label} fixture failed")
        pivots = [int(np.flatnonzero(row)[0]) for row in actual_rref[:actual_rank]]
        if (2 in pivots) != target_pivot:
            raise GateError(f"target-last pivot scan {label} fixture failed")
    member_rref, member_rank = native_fixture(adapter, member)
    pivots = [int(np.flatnonzero(row)[0]) for row in member_rref[:member_rank]]
    rhs = [int(row[-1]) for row in member_rref[:member_rank]]
    solution_columns = [pivot for pivot in pivots if pivot < 2]
    solution = np.zeros(2, dtype=np.int64)
    for index, column in enumerate(solution_columns):
        solution[column] = rhs[index]
    if not np.array_equal(
        np.remainder(member[:, :2] @ solution, PRIME),
        np.remainder(member[:, -1], PRIME),
    ):
        raise GateError("free-zero target-last solution fixture failed")
    return {
        "native_multiply": True,
        "native_in_place_rref_member": True,
        "native_in_place_rref_separator": True,
        "target_last_pivot_scan": True,
        "free_zero_solution": True,
        "rref_abi": "ctypes nmod_mat_rref(nmod_mat_t)->slong; in-place",
    }


def self_test_cache_mutation() -> dict[str, object]:
    with tempfile.TemporaryDirectory(dir=HERE) as temporary_text:
        temporary = Path(temporary_text)
        data = temporary / "fixture.npy"
        receipt_path = temporary / "fixture.json"
        values = open_memmap_exclusive(data, dtype=np.dtype("<u4"), shape=(3, 4))
        values[:] = np.arange(12, dtype=np.uint32).reshape(3, 4)
        values.flush()
        custody = {"g0081_runner": "fixture"}
        receipt = {
            "schema": "fixture",
            "state": "complete",
            "shape": [3, 4],
            "dtype": "<u4",
            "prime": PRIME,
            "all_new_columns_retained": True,
            "price_filtering_allowed": False,
            "custody": {"start": custody, "end": custody, "identical": True},
            "npy_sha256": sha256_path(data),
            "raw_uint32_c_sha256": raw_sha256(values),
        }
        write_json_exclusive(receipt_path, receipt)
        validate_complete_cache(
            data, receipt_path, schema="fixture", shape=(3, 4), custody=custody
        )
        mutant = np.load(data, mmap_mode="r+")
        mutant[1, 2] += 1
        mutant.flush()
        rejected = False
        try:
            validate_complete_cache(
                data, receipt_path, schema="fixture", shape=(3, 4), custody=custody
            )
        except GateError:
            rejected = True
        if not rejected:
            raise GateError("matrix-cache mutation self-test escaped")
    return {"valid_cache_accepted": True, "one_entry_cache_mutation_rejected": True}


def self_test_fast_evaluator(
    runner: ModuleType,
    preflight: ModuleType,
    g75: ModuleType,
    family: object,
) -> dict[str, object]:
    support = set(map(int, runner.exact_functional(preflight).rows))
    rows = [row for row in (12, 15360, 16737, 16001, 15555) if row not in support][:3]
    columns = [0, 9173, NEW_COLUMNS - 1]
    representatives = [family.new_representatives[column] for column in columns]
    evaluator = FastEvaluator(
        g75, family.bases, representatives, require_complete=False
    )
    fast = evaluator.evaluate_rows(rows)
    frozen = preflight.evaluate_representatives_on_rows(
        g75, family.bases, representatives, rows
    )
    nested = runner.evaluate_representatives_nested_on_rows(
        preflight, g75, family.bases, representatives, rows
    )
    if not np.array_equal(fast, frozen) or not np.array_equal(fast, nested):
        raise GateError("tiny fast/frozen/nested evaluator control failed")
    return {
        "raw_rows": rows,
        "local_new_columns": columns,
        "entries_checked": len(rows) * len(columns),
        "rows_disjoint_from_G0078_price_support": True,
        "fast_equals_frozen_flattened_equals_nested": True,
        "scientific_outcome": False,
    }


def self_test_logic() -> dict[str, object]:
    prices = [0] * NEW_COLUMNS
    prices[0] = 3
    prices[2] = 5
    target = 7
    scalar = 11
    row = np.asarray(
        [value * scalar % PRIME for value in (*prices, target)], dtype=np.uint32
    )
    relation = price_scalar_relation(row, prices, target)
    mutant = row.copy()
    mutant[1] = 1
    rejected = False
    try:
        price_scalar_relation(mutant, prices, target)
    except GateError:
        rejected = True
    if not rejected:
        raise GateError("price-row scalar mutant escaped")
    full_q = np.asarray([[1, 2, 5], [3, 4, 6]], dtype=np.int64)
    rank_new = numpy_rref_fixture(full_q[:, :2], 101)[1]
    rank_aug = numpy_rref_fixture(full_q, 101)[1]
    if rank_new != 2 or rank_aug != 2:
        raise GateError("rank-full-Q implication member fixture failed")
    separator = np.asarray([[1, 2, 5], [2, 4, 6]], dtype=np.int64)
    if (
        numpy_rref_fixture(separator[:, :2], 101)[1] != 1
        or numpy_rref_fixture(separator, 101)[1] != 2
    ):
        raise GateError("rank-full-Q implication hostile fixture failed")
    return {
        "price_row_common_scalar": relation,
        "price_row_one_entry_mutant_rejected": True,
        "rank_full_Q_forces_every_frozen_Q_target_member": True,
        "rank_deficient_left_can_have_target_pivot": True,
        "characteristic_zero_minor_statement_is_one_sided": True,
    }


def self_test() -> dict[str, object]:
    bindings = replay_static_bindings()
    resource_estimates = validate_preflight_resource_estimates()
    runner, preflight, g75, family, semantic = load_g0079_context()
    price_report, functional = load_price_contract(runner)
    adapter = load_owned_module(
        NATIVE_ADAPTER,
        EXPECTED_NATIVE_ADAPTER_SHA256,
        "max11_native_adapter_for_g0081_selftest",
    )
    validate_inverse(adapter)
    if (
        Path(sys.executable).resolve() != REGISTERED_PYTHON.resolve()
        or platform.python_version() != EXPECTED_REGISTERED_PYTHON
        or functional.rows.shape != (230,)
        or price_report.get("scientific_payload_sha256")
        != EXPECTED_G0079_PRICE_SCIENCE_SHA256
    ):
        raise GateError("frozen self-test metadata drift")
    return {
        "schema": "max11-g0081-complete-native-schur-self-test-v1",
        "result": "PASS",
        "bindings": bindings,
        "frozen_resource_estimates": resource_estimates,
        "semantic_source_execution": semantic,
        "native": self_test_native(adapter),
        "cache_mutation": self_test_cache_mutation(),
        "evaluator": self_test_fast_evaluator(runner, preflight, g75, family),
        "logic": self_test_logic(),
        "all_18582_columns_in_actual_runner": True,
        "price_filtering_in_actual_runner": False,
        "actual_quotient_or_rank_evaluated": False,
        "actual_result_artifact_created": False,
        "no_claim": "Synthetic and tiny non-outcome controls only; no G-0081 rank or solve was evaluated.",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--check-registration", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--internal-run", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--expected-runner-sha256")
    parser.add_argument("--expected-preregistration-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    parser.add_argument("--internal-scratch-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--internal-token", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        extras = (
            arguments.preregistration,
            arguments.expected_runner_sha256,
            arguments.expected_preregistration_sha256,
            arguments.output,
            arguments.cache_dir,
            arguments.internal_scratch_output,
            arguments.internal_token,
        )
        if any(value is not None for value in extras):
            raise GateError("--self-test refuses registered/internal arguments")
        print(json.dumps(self_test(), sort_keys=True))
        return
    registration = validate_registration(arguments)
    if arguments.check_registration:
        if (
            arguments.internal_scratch_output is not None
            or arguments.internal_token is not None
        ):
            raise GateError("registration check refuses internal arguments")
        bindings = replay_static_bindings()
        print(
            json.dumps(
                {
                    "schema": "max11-g0081-registration-check-v1",
                    "result": "PASS",
                    "runner_sha256": registration.runner_sha256,
                    "preregistration_sha256": registration.sha256,
                    "bindings": bindings,
                    "output_unused": True,
                    "actual_quotient_or_rank_evaluated": False,
                },
                sort_keys=True,
            )
        )
        return
    if arguments.internal_run:
        if (
            arguments.internal_scratch_output is None
            or arguments.internal_token is None
            or not secrets.compare_digest(
                arguments.internal_token, os.environ.get("G0081_INTERNAL_TOKEN", "")
            )
        ):
            raise GateError("internal kernel lacks launcher's one-time token")
        scratch = arguments.internal_scratch_output
        require_contained(scratch)
        if scratch.exists() or scratch.is_symlink():
            raise GateError("refusing to overwrite internal scratch output")
        begun = time.monotonic()
        start_custody = capture_custody(registration.runner_sha256, registration.path)
        try:
            report = internal_kernel(registration, scratch)
        except (MemoryError, OSError, TimeoutError) as error:
            # Resource exhaustion is an explicit non-outcome.  Serialize it in
            # the child so the public launcher can preserve the same custody
            # checks and exclusive final-output transaction as a normal result.
            report = resource_unresolved_report(
                registration,
                f"{type(error).__name__}: {error}",
                begun,
                start_custody,
            )
            write_json_exclusive(scratch, report)
        print(
            json.dumps(
                {
                    "schema": SCHEMA_RESULT,
                    "result": report["scientific_payload"]["result"],
                    "scientific_payload_sha256": report["scientific_payload_sha256"],
                },
                sort_keys=True,
            )
        )
        return
    if (
        arguments.internal_scratch_output is not None
        or arguments.internal_token is not None
    ):
        raise GateError("public run refuses internal arguments")
    report = public_run(registration)
    print(
        json.dumps(
            {
                "schema": SCHEMA_RESULT,
                "result": report["scientific_payload"]["result"],
                "scientific_payload_sha256": report["scientific_payload_sha256"],
                "output": relative_path(registration.output),
                "output_sha256": sha256_path(registration.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
