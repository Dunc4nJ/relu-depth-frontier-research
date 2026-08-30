#!/usr/bin/env python3
"""Isolated native-FLINT adapter for the frozen G-0079 old basis minor.

This module deliberately bypasses the ``python-flint`` bulk ``nmod_mat``
constructor, whose temporary-copy path was observed to die on the actual
6,876-square minor.  It loads the exact bundled FLINT/GMP shared objects,
allocates native matrices, fills rows blockwise, inverts in a child process,
exports a little-endian uint32 NumPy artifact, and replays selected columns.

It computes no new-family values and no target-membership outcome.
"""

from __future__ import annotations

import argparse
import ctypes
import gzip
import hashlib
import json
import os
from pathlib import Path
import resource
import subprocess
import sys
import tempfile
import time
from typing import Sequence

import numpy as np
from numpy.lib.format import open_memmap


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
FULL_OLD_MATRIX = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"

PRIME = 1_000_003
RANK = 6_876
OLD_COLUMNS = 8_107
TOTAL_ROWS = 16_738
THREADS = 8
ROW_BLOCK = 32
REPLAY_COLUMNS = (0, 3_438, 6_875)

EXPECTED_FULL_OLD_SHA256 = (
    "5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f"
)
EXPECTED_G0077_MODULAR_SHA256 = (
    "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4"
)
EXPECTED_BASIS_ROWS_SHA256 = (
    "b2948637191c00c60aaf4c2d5ae6bd81fa05ddb05dabf419776a503e46d5388c"
)
EXPECTED_BASIS_COLUMNS_SHA256 = (
    "68bbfdfea522e88e97fad989952a0bb88ae4875d74ea6f9cfb50425f4ee5a683"
)
EXPECTED_RAW_B_DATA_SHA256 = (
    "04e28706954c864190583db0f1b089aecd546a9c270f7a22b9fb96de6a2a95c7"
)
EXPECTED_FLINT_BASENAME = "libflint-6839011d.so.24.0.0"
EXPECTED_FLINT_SHA256 = (
    "871a4132fd1e9f3638391b2208e07088f8e3e72a10e41d45f58b150a60c2a1a9"
)
EXPECTED_GMP_BASENAME = "libgmp-e0c82b6b.so.10.5.0"
EXPECTED_GMP_SHA256 = (
    "33d24e675b10f8b1ab93a8ad3fa2ed5012e1b0d89dcdb97273877c6c6b9450d8"
)


class AdapterError(RuntimeError):
    """A native binding, allocation, inversion, export, or replay failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise AdapterError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def read_gzip(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise AdapterError(f"malformed JSON object: {path}")
    return document


def write_json_exclusive(path: Path, document: object) -> None:
    if path.exists() or path.is_symlink():
        raise AdapterError(f"refusing to overwrite output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = canonical_bytes(document)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def library_paths() -> tuple[Path, Path]:
    library_directory = (
        Path(sys.prefix)
        / "lib"
        / f"python{sys.version_info.major}.{sys.version_info.minor}"
        / "site-packages"
        / "python_flint.libs"
    )
    gmp = library_directory / EXPECTED_GMP_BASENAME
    flint = library_directory / EXPECTED_FLINT_BASENAME
    observed = {
        "gmp": sha256_path(gmp),
        "flint": sha256_path(flint),
    }
    expected = {
        "gmp": EXPECTED_GMP_SHA256,
        "flint": EXPECTED_FLINT_SHA256,
    }
    if observed != expected:
        raise AdapterError(f"native library binding drift: {observed} != {expected}")
    return gmp, flint


NMOD_MAT_OPAQUE_WORDS = 16
NModMatOpaque = ctypes.c_ulong * NMOD_MAT_OPAQUE_WORDS
GUARD_WORDS = 4
GUARD_CANARY = 0xD9E3779B97F4A7C1


class GuardedNModMat(ctypes.Structure):
    _fields_ = [
        ("before", ctypes.c_ulong * GUARD_WORDS),
        ("storage", NModMatOpaque),
        ("after", ctypes.c_ulong * GUARD_WORDS),
    ]


class NativeFlint:
    """Minimal typed surface of the frozen bundled FLINT library."""

    def __init__(self) -> None:
        gmp_path, flint_path = library_paths()
        self.gmp_path = gmp_path
        self.flint_path = flint_path
        self.gmp = ctypes.CDLL(str(gmp_path), mode=ctypes.RTLD_GLOBAL)
        self.lib = ctypes.CDLL(str(flint_path), mode=ctypes.RTLD_LOCAL)
        try:
            version = (ctypes.c_char * 6).in_dll(self.lib, "flint_version").value
        except ValueError as error:
            raise AdapterError("bundled FLINT lacks flint_version") from error
        self.version = version.decode("ascii") if version is not None else ""
        if self.version != "3.6.0":
            raise AdapterError(f"unexpected bundled FLINT version: {self.version}")
        self.lib.flint_set_num_threads.argtypes = [ctypes.c_int]
        self.lib.flint_set_num_threads.restype = None
        self.lib.nmod_mat_init.argtypes = [
            ctypes.c_void_p,
            ctypes.c_long,
            ctypes.c_long,
            ctypes.c_ulong,
        ]
        self.lib.nmod_mat_init.restype = None
        self.lib.nmod_mat_clear.argtypes = [ctypes.c_void_p]
        self.lib.nmod_mat_clear.restype = None
        self.lib.nmod_mat_inv.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.lib.nmod_mat_inv.restype = ctypes.c_int
        self.lib.nmod_mat_mul.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        self.lib.nmod_mat_mul.restype = None
        self.lib.nmod_mat_row_ptr.argtypes = [ctypes.c_void_p, ctypes.c_long]
        self.lib.nmod_mat_row_ptr.restype = ctypes.POINTER(ctypes.c_ulong)
        self.lib.nmod_mat_nrows.argtypes = [ctypes.c_void_p]
        self.lib.nmod_mat_nrows.restype = ctypes.c_long
        self.lib.nmod_mat_ncols.argtypes = [ctypes.c_void_p]
        self.lib.nmod_mat_ncols.restype = ctypes.c_long
        self.lib.flint_cleanup_master.argtypes = []
        self.lib.flint_cleanup_master.restype = None
        self.lib.flint_set_num_threads(THREADS)

    @staticmethod
    def pointer(matrix: GuardedNModMat) -> ctypes.c_void_p:
        return ctypes.cast(
            ctypes.byref(matrix, GuardedNModMat.storage.offset), ctypes.c_void_p
        )

    @staticmethod
    def check_guards(matrix: GuardedNModMat) -> None:
        expected = [GUARD_CANARY] * GUARD_WORDS
        if list(matrix.before) != expected or list(matrix.after) != expected:
            raise AdapterError("opaque nmod_mat guard canary was corrupted")

    def initialize(self, rows: int, columns: int, prime: int) -> GuardedNModMat:
        matrix = GuardedNModMat()
        matrix.before[:] = [GUARD_CANARY] * GUARD_WORDS
        matrix.after[:] = [GUARD_CANARY] * GUARD_WORDS
        if (
            ctypes.sizeof(matrix.storage) != 128
            or ctypes.addressof(matrix) % 8
            or GuardedNModMat.storage.offset % 8
        ):
            raise AdapterError("opaque nmod_mat storage size/alignment drift")
        pointer = self.pointer(matrix)
        self.lib.nmod_mat_init(pointer, rows, columns, prime)
        if (
            self.lib.nmod_mat_nrows(pointer) != rows
            or self.lib.nmod_mat_ncols(pointer) != columns
        ):
            try:
                self.lib.nmod_mat_clear(pointer)
            finally:
                raise AdapterError("native nmod_mat initialization/layout check failed")
        self.check_guards(matrix)
        return matrix

    def clear(self, matrix: GuardedNModMat) -> None:
        self.check_guards(matrix)
        self.lib.nmod_mat_clear(self.pointer(matrix))
        self.check_guards(matrix)

    def row(self, matrix: GuardedNModMat, row: int, columns: int) -> np.ndarray:
        self.check_guards(matrix)
        pointer = self.pointer(matrix)
        if not 0 <= row < self.lib.nmod_mat_nrows(pointer):
            raise AdapterError("native row index outside matrix")
        if columns != self.lib.nmod_mat_ncols(pointer):
            raise AdapterError("native row-view column census drift")
        row_pointer = self.lib.nmod_mat_row_ptr(pointer, row)
        if not bool(row_pointer):
            raise AdapterError("native nmod_mat_row_ptr returned null")
        return np.ctypeslib.as_array(row_pointer, shape=(columns,))

    def cleanup(self) -> None:
        self.lib.flint_cleanup_master()


def fill_native_row(
    native: NativeFlint,
    matrix: GuardedNModMat,
    row: int,
    values: np.ndarray,
) -> None:
    vector = np.ascontiguousarray(values, dtype=np.uint64)
    if vector.ndim != 1:
        raise AdapterError("native row-fill shape drift")
    row_view = native.row(matrix, row, vector.shape[0])
    row_view[:] = vector


def invert_array_fixture(values: np.ndarray, prime: int) -> np.ndarray:
    source = np.asarray(values, dtype=np.int64)
    if source.ndim != 2 or source.shape[0] != source.shape[1]:
        raise AdapterError("fixture matrix must be square")
    size = source.shape[0]
    native = NativeFlint()
    matrix = native.initialize(size, size, prime)
    inverse = native.initialize(size, size, prime)
    try:
        for row in range(size):
            fill_native_row(native, matrix, row, np.remainder(source[row], prime))
        if (
            native.lib.nmod_mat_inv(
                native.pointer(inverse), native.pointer(matrix)
            )
            != 1
        ):
            raise AdapterError("fixture matrix is singular")
        validate_full_native_product(native, matrix, inverse, size=size, prime=prime)
        exported = np.empty((size, size), dtype=np.uint32)
        for row in range(size):
            exported[row] = native.row(inverse, row, size).astype(np.uint32)
        return exported
    finally:
        native.clear(inverse)
        native.clear(matrix)
        native.cleanup()


def load_basis_contract() -> tuple[np.ndarray, np.ndarray, dict[str, object]]:
    observed_inputs = {
        "full_old_matrix": sha256_path(FULL_OLD_MATRIX),
        "g0077_modular": sha256_path(G0077_MODULAR),
    }
    expected_inputs = {
        "full_old_matrix": EXPECTED_FULL_OLD_SHA256,
        "g0077_modular": EXPECTED_G0077_MODULAR_SHA256,
    }
    if observed_inputs != expected_inputs:
        raise AdapterError(f"old-basis input binding drift: {observed_inputs}")
    modular = read_gzip(G0077_MODULAR)
    rows = np.asarray(modular.get("basis_rows"), dtype=np.int64)
    columns = np.asarray(modular.get("basis_columns"), dtype=np.int64)
    if (
        modular.get("prime") != PRIME
        or modular.get("rank_A") != RANK
        or modular.get("rows") != TOTAL_ROWS
        or modular.get("A_columns") != OLD_COLUMNS
        or rows.shape != (RANK,)
        or columns.shape != (RANK,)
        or canonical_sha256(rows.astype(int).tolist()) != EXPECTED_BASIS_ROWS_SHA256
        or canonical_sha256(columns.astype(int).tolist())
        != EXPECTED_BASIS_COLUMNS_SHA256
    ):
        raise AdapterError("G-0077 P/R basis contract drift")
    return rows, columns, modular


def raw_basis_blocks(
    full: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    *,
    block_rows: int = ROW_BLOCK,
):
    for start in range(0, len(rows), block_rows):
        stop = min(start + block_rows, len(rows))
        selected = np.asarray(rows[start:stop], dtype=np.intp)
        block = np.ascontiguousarray(full[selected][:, columns])
        yield start, stop, block


def replay_inverse_columns(
    full: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    inverse: np.ndarray,
    replay_columns: Sequence[int],
) -> dict[str, object]:
    selected = np.asarray(list(replay_columns), dtype=np.intp)
    vectors = np.ascontiguousarray(inverse[:, selected], dtype=np.uint64)
    if vectors.shape != (RANK, len(selected)):
        raise AdapterError("inverse replay-vector shape drift")
    failures: list[list[int]] = []
    replay_digest = hashlib.sha256()
    for start, stop, block in raw_basis_blocks(full, rows, columns):
        reduced = np.remainder(block, PRIME).astype(np.uint64, copy=False)
        products = np.remainder(reduced @ vectors, PRIME).astype(np.uint32)
        replay_digest.update(memoryview(np.ascontiguousarray(products)).cast("B"))
        for local_row, raw_row in enumerate(range(start, stop)):
            for vector_index, column in enumerate(selected):
                expected = 1 if raw_row == int(column) else 0
                if int(products[local_row, vector_index]) != expected:
                    failures.append(
                        [raw_row, int(column), int(products[local_row, vector_index])]
                    )
                    if len(failures) >= 8:
                        break
            if len(failures) >= 8:
                break
        if failures:
            break
    if failures:
        raise AdapterError(f"B*B^-1 replay failed: {failures}")
    return {
        "columns": list(map(int, selected)),
        "all_rows_per_column": RANK,
        "identity_replay": True,
        "product_stream_uint32_sha256": replay_digest.hexdigest(),
    }


def validate_full_native_product(
    native: NativeFlint,
    matrix: GuardedNModMat,
    inverse: GuardedNModMat,
    *,
    size: int,
    prime: int,
) -> dict[str, object]:
    product = native.initialize(size, size, prime)
    begun = time.perf_counter()
    try:
        native.lib.nmod_mat_mul(
            native.pointer(product),
            native.pointer(matrix),
            native.pointer(inverse),
        )
        multiply_seconds = time.perf_counter() - begun
        digest = hashlib.sha256()
        for row in range(size):
            values = native.row(product, row, size)
            reduced = np.remainder(values, prime).astype(np.uint32)
            digest.update(memoryview(np.ascontiguousarray(reduced)).cast("B"))
            if int(reduced[row]) != 1 or np.count_nonzero(reduced) != 1:
                first = np.flatnonzero(
                    reduced != np.eye(1, size, row, dtype=np.uint32)[0]
                )
                raise AdapterError(
                    "full B*B^-1 identity replay failed at row "
                    f"{row}, first columns={first[:8].astype(int).tolist()}"
                )
        return {
            "all_entries_checked": size * size,
            "identity_replay": True,
            "product_uint32_c_sha256": digest.hexdigest(),
            "native_multiply_seconds": multiply_seconds,
        }
    finally:
        native.clear(product)


def invert_old_basis(output: Path, receipt_path: Path) -> dict[str, object]:
    if output.exists() or output.is_symlink():
        raise AdapterError(f"refusing to overwrite inverse output: {output}")
    if receipt_path.exists() or receipt_path.is_symlink():
        raise AdapterError(f"refusing to overwrite receipt: {receipt_path}")
    output.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    start_script_sha256 = sha256_path(SCRIPT)
    rows, columns, modular = load_basis_contract()
    full = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
    if full.shape != (TOTAL_ROWS, OLD_COLUMNS + 1) or full.dtype != np.dtype("<i8"):
        raise AdapterError("full old matrix shape/dtype drift")

    native = NativeFlint()
    matrix = native.initialize(RANK, RANK, PRIME)
    inverse = native.initialize(RANK, RANK, PRIME)
    raw_digest = hashlib.sha256()
    fill_started = time.perf_counter()
    try:
        for start, stop, block in raw_basis_blocks(full, rows, columns):
            raw_digest.update(memoryview(block).cast("B"))
            reduced = np.remainder(block, PRIME).astype(np.uint64, copy=False)
            for offset, row in enumerate(range(start, stop)):
                fill_native_row(native, matrix, row, reduced[offset])
        fill_seconds = time.perf_counter() - fill_started
        if raw_digest.hexdigest() != EXPECTED_RAW_B_DATA_SHA256:
            raise AdapterError("live raw B stream hash drift")

        inverse_started = time.perf_counter()
        invertible = native.lib.nmod_mat_inv(
            native.pointer(inverse), native.pointer(matrix)
        )
        inverse_seconds = time.perf_counter() - inverse_started
        if invertible != 1:
            raise AdapterError("frozen B is singular in native FLINT")

        full_product_replay = validate_full_native_product(
            native, matrix, inverse, size=RANK, prime=PRIME
        )

        export_started = time.perf_counter()
        exported = open_memmap(
            output,
            mode="w+",
            dtype=np.dtype("<u4"),
            shape=(RANK, RANK),
        )
        data_digest = hashlib.sha256()
        for row in range(RANK):
            vector = native.row(inverse, row, RANK).astype(np.uint32)
            exported[row] = vector
            data_digest.update(memoryview(np.ascontiguousarray(vector)).cast("B"))
        exported.flush()
        with output.open("rb") as target:
            os.fsync(target.fileno())
        export_seconds = time.perf_counter() - export_started
        inverse_view = np.load(output, mmap_mode="r", allow_pickle=False)
        if inverse_view.shape != (RANK, RANK) or inverse_view.dtype != np.dtype("<u4"):
            raise AdapterError("exported inverse shape/dtype drift")
        reloaded_data_digest = hashlib.sha256()
        for row in range(RANK):
            vector = np.ascontiguousarray(inverse_view[row])
            if np.any(vector >= PRIME):
                raise AdapterError("reloaded inverse entry lies outside canonical residue range")
            reloaded_data_digest.update(memoryview(vector).cast("B"))
        if reloaded_data_digest.hexdigest() != data_digest.hexdigest():
            raise AdapterError("full reloaded inverse bytes differ from native export stream")
        replay = replay_inverse_columns(
            full, rows, columns, inverse_view, REPLAY_COLUMNS
        )
        inverse_probe = [
            int(inverse_view[0, 0]),
            int(inverse_view[RANK // 2, RANK // 2]),
            int(inverse_view[RANK - 1, RANK - 1]),
        ]
        del inverse_view, exported
    except BaseException:
        try:
            output.unlink()
        except FileNotFoundError:
            pass
        raise
    finally:
        try:
            native.clear(inverse)
            native.clear(matrix)
            native.cleanup()
        except BaseException:
            try:
                output.unlink()
            except FileNotFoundError:
                pass
            raise

    end_script_sha256 = sha256_path(SCRIPT)
    end_gmp_path, end_flint_path = library_paths()
    end_inputs = {
        "full_old_matrix": sha256_path(FULL_OLD_MATRIX),
        "g0077_modular": sha256_path(G0077_MODULAR),
        "libflint": sha256_path(end_flint_path),
        "libgmp": sha256_path(end_gmp_path),
    }
    if (
        end_script_sha256 != start_script_sha256
        or end_inputs["full_old_matrix"] != EXPECTED_FULL_OLD_SHA256
        or end_inputs["g0077_modular"] != EXPECTED_G0077_MODULAR_SHA256
        or end_inputs["libflint"] != EXPECTED_FLINT_SHA256
        or end_inputs["libgmp"] != EXPECTED_GMP_SHA256
    ):
        raise AdapterError("native inversion custody changed during execution")
    receipt = {
        "schema": "max11-g0079-native-flint-inverse-v1",
        "result": "NATIVE_INVERSE_EXPORTED_AND_REPLAYED",
        "prime": PRIME,
        "shape": [RANK, RANK],
        "threads": THREADS,
        "adapter_script_sha256": end_script_sha256,
        "bindings": {
            "full_old_matrix_sha256": EXPECTED_FULL_OLD_SHA256,
            "g0077_modular_sha256": EXPECTED_G0077_MODULAR_SHA256,
            "basis_rows_sha256": EXPECTED_BASIS_ROWS_SHA256,
            "basis_columns_sha256": EXPECTED_BASIS_COLUMNS_SHA256,
            "raw_B_int64_c_sha256": EXPECTED_RAW_B_DATA_SHA256,
            "libflint_path": str(native.flint_path),
            "libflint_sha256": EXPECTED_FLINT_SHA256,
            "libflint_version": native.version,
            "libgmp_path": str(native.gmp_path),
            "libgmp_sha256": EXPECTED_GMP_SHA256,
        },
        "python_flint_bulk_constructor_used": False,
        "native_calls": [
            "nmod_mat_init",
            "nmod_mat_nrows",
            "nmod_mat_ncols",
            "nmod_mat_row_ptr",
            "blockwise row assignment through exported row pointers",
            "nmod_mat_inv",
            "nmod_mat_mul",
            "nmod_mat_clear",
        ],
        "fill_seconds": fill_seconds,
        "inverse_seconds": inverse_seconds,
        "export_seconds": export_seconds,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "inverse_npy_path": str(output),
        "inverse_npy_sha256": sha256_path(output),
        "inverse_uint32_c_sha256": data_digest.hexdigest(),
        "reloaded_inverse_uint32_c_sha256": reloaded_data_digest.hexdigest(),
        "full_export_stream_equality": True,
        "inverse_probe": inverse_probe,
        "replay": replay,
        "full_product_replay": full_product_replay,
        "custody": {
            "start_script_sha256": start_script_sha256,
            "end_script_sha256": end_script_sha256,
            "inputs_rehashed_at_end": end_inputs,
        },
        "claim_boundary": (
            "This receipt proves only an in-memory full B*B^-1 identity, byte-for-byte "
            "equality of the entire exported/reloaded inverse, and selected arithmetic "
            "replays for the frozen old-basis minor modulo 1,000,003. It computes no new-"
            "family prices and no target-membership or separation result."
        ),
    }
    write_json_exclusive(receipt_path, receipt)
    return receipt


def fixture_child() -> dict[str, object]:
    source = np.asarray([[1, 2, 3], [0, 1, 4], [5, 6, 0]], dtype=np.int64)
    inverse = invert_array_fixture(source, 101)
    product = np.remainder(
        source.astype(np.uint64) @ inverse.astype(np.uint64), 101
    ).astype(np.uint32)
    if not np.array_equal(product, np.eye(3, dtype=np.uint32)):
        raise AdapterError("native fixture inverse replay failed")
    mutant = inverse.copy()
    mutant[0, 0] = (int(mutant[0, 0]) + 1) % 101
    mutant_product = np.remainder(
        source.astype(np.uint64) @ mutant.astype(np.uint64), 101
    ).astype(np.uint32)
    if np.array_equal(mutant_product, np.eye(3, dtype=np.uint32)):
        raise AdapterError("one-unit inverse mutant escaped replay")
    return {
        "fixture_inverse_replayed": True,
        "one_unit_mutant_rejected": True,
        "inverse": inverse.astype(int).tolist(),
    }


def require_digest(label: str, observed: str, expected: str) -> None:
    if observed != expected:
        raise AdapterError(f"{label} binding drift: {observed} != {expected}")


def self_test() -> dict[str, object]:
    completed = subprocess.run(
        [sys.executable, str(SCRIPT), "--fixture-child"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
        timeout=60,
    )
    if completed.returncode != 0:
        raise AdapterError(
            "isolated native fixture failed: "
            f"returncode={completed.returncode}, stderr={completed.stderr[-2000:]}"
        )
    try:
        child = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise AdapterError("isolated native fixture returned malformed JSON") from error
    if (
        child.get("fixture_inverse_replayed") is not True
        or child.get("one_unit_mutant_rejected") is not True
    ):
        raise AdapterError("isolated native fixture controls did not pass")
    basis_rows, basis_columns, modular = load_basis_contract()
    if (
        basis_rows.shape != (RANK,)
        or basis_columns.shape != (RANK,)
        or modular.get("primitive_square_int64_sha256")
        != "38af8661f6a408590968a993e095ae6d161c6208c7a28ffdddc7adcba57a8506"
    ):
        raise AdapterError("live subject metadata binding self-test failed")
    binding_mutants_rejected = 0
    for label, expected in (
        ("full_old_matrix", EXPECTED_FULL_OLD_SHA256),
        ("g0077_modular", EXPECTED_G0077_MODULAR_SHA256),
    ):
        try:
            require_digest(label, expected, "0" * 64)
        except AdapterError:
            binding_mutants_rejected += 1
        else:
            raise AdapterError(f"{label} binding mutant escaped")
    inverse = np.asarray(child["inverse"], dtype=np.uint32)
    with tempfile.TemporaryDirectory(prefix="g0079-native-adapter-") as directory:
        output = Path(directory) / "fixture.npy"
        array = open_memmap(output, mode="w+", dtype="<u4", shape=inverse.shape)
        array[:] = inverse
        array.flush()
        del array
        replayed = np.load(output, mmap_mode="r", allow_pickle=False)
        if not np.array_equal(replayed, inverse):
            raise AdapterError("native fixture NumPy export replay failed")
    gmp, flint = library_paths()
    end_library_hashes = {
        "libflint": sha256_path(flint),
        "libgmp": sha256_path(gmp),
    }
    if end_library_hashes != {
        "libflint": EXPECTED_FLINT_SHA256,
        "libgmp": EXPECTED_GMP_SHA256,
    }:
        raise AdapterError("native library custody changed during self-test")
    return {
        "schema": "max11-g0079-native-flint-adapter-self-test-v1",
        "result": "PASS",
        "fixture_inverse_replayed": True,
        "one_unit_mutant_rejected": True,
        "native_fault_isolated_in_child": True,
        "binding_mutants_rejected": binding_mutants_rejected,
        "live_subject_metadata_binding_replayed": True,
        "opaque_storage_bytes": 128,
        "opaque_guard_canaries_replayed": True,
        "little_endian_uint32_export_replayed": True,
        "python_flint_imported": False,
        "python_flint_bulk_constructor_used": False,
        "libflint_sha256": sha256_path(flint),
        "libgmp_sha256": sha256_path(gmp),
        "no_claim": "No actual G-0079 matrix or target outcome was evaluated.",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--fixture-child", action="store_true", help=argparse.SUPPRESS)
    mode.add_argument("--invert-old-basis", action="store_true")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--receipt", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        if arguments.output is not None or arguments.receipt is not None:
            raise AdapterError("--self-test refuses output arguments")
        print(json.dumps(self_test(), sort_keys=True))
        return
    if arguments.fixture_child:
        if arguments.output is not None or arguments.receipt is not None:
            raise AdapterError("--fixture-child refuses output arguments")
        print(json.dumps(fixture_child(), sort_keys=True))
        return
    if arguments.output is None or arguments.receipt is None:
        raise AdapterError("--invert-old-basis requires --output and --receipt")
    report = invert_old_basis(arguments.output, arguments.receipt)
    print(json.dumps(report, sort_keys=True))


if __name__ == "__main__":
    main()
