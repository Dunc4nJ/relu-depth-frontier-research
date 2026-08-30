#!/usr/bin/env python3
"""Complete frozen-dictionary Schur rank/solve gate for G-0081.

The registered subject is all 8,107 old columns and all 18,582 G-0079
same-component columns on all 16,738 frozen rows modulo 1,000,003.  Prices
are never used to select columns.  Public execution requires a separately
committed, clean, Git-anchored preregistration; this source ships first for
hostile review.

Every modular branch is discovery-only.  A member branch still needs an
exact rational lift and a global CPWL identity replay.  A separator branch
only separates this finite dictionary on these frozen rows.
"""

from __future__ import annotations

import argparse
import ast
import ctypes
import fcntl
import gzip
import hashlib
import json
import multiprocessing as mp
import os
import platform
import re
import resource
import secrets
import select
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time
import traceback
from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType

import numpy as np
from numpy.lib.format import open_memmap

if __name__ != "__main__":
    raise RuntimeError(
        "G-0081 is a CLI-only registered runner; importing it exposes no scientific entry"
    )

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
GIT_COMMIT_PATTERN = re.compile(r"[0-9a-fA-F]{40,64}")
CACHE_RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}")
CAPABILITY_DOMAIN = b"G0081_PARENT_CHILD_CAPABILITY_V1\0"
CAPABILITY_SECRET_BYTES = 32
PR_SET_PDEATHSIG = 1
GIT_EXECUTABLE = Path("/usr/bin/git")
EXPECTED_ORIGIN_URL = "git@github.com:Dunc4nJ/relu-depth-frontier-research.git"
EXPECTED_PUBLISHED_REF = "refs/heads/master"

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
class GitAnchor:
    preregistration_commit: str
    execution_head_commit: str
    preregistration_blob_oid: str
    head_preregistration_blob_oid: str
    head_runner_blob_oid: str
    object_format: str
    worktree: str
    git_dir: str
    git_common_dir: str
    git_config_sha256: str
    git_executable: str
    git_executable_sha256: str
    origin_url: str | None
    published_ref: str | None
    published_head_commit: str | None

    def receipt(self) -> dict[str, str | None]:
        return {
            "preregistration_commit": self.preregistration_commit,
            "execution_head_commit": self.execution_head_commit,
            "preregistration_blob_oid": self.preregistration_blob_oid,
            "head_preregistration_blob_oid": self.head_preregistration_blob_oid,
            "head_runner_blob_oid": self.head_runner_blob_oid,
            "object_format": self.object_format,
            "worktree": self.worktree,
            "git_dir": self.git_dir,
            "git_common_dir": self.git_common_dir,
            "git_config_sha256": self.git_config_sha256,
            "git_executable": self.git_executable,
            "git_executable_sha256": self.git_executable_sha256,
            "origin_url": self.origin_url,
            "published_ref": self.published_ref,
            "published_head_commit": self.published_head_commit,
        }


@dataclass(frozen=True)
class Registration:
    path: Path
    sha256: str
    runner_sha256: str
    output: Path
    cache_dir: Path
    document: dict[str, object]
    git_anchor: GitAnchor


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
    """Replace only the current execution's progress journal; never a final artifact."""
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


def trusted_git_layout(repository: Path) -> tuple[Path, Path]:
    """Resolve the repository metadata without consulting Git or inherited env."""
    repository = repository.resolve()
    marker = repository / ".git"
    if marker.is_symlink():
        raise GateError("campaign .git marker must not be a symlink")
    if not marker.is_dir():
        raise GateError("campaign requires one ordinary no-follow .git directory")
    git_dir = marker.resolve()
    if not git_dir.is_dir() or git_dir.is_symlink():
        raise GateError("resolved campaign Git directory is not a regular directory")
    common_marker = git_dir / "commondir"
    if common_marker.exists() or common_marker.is_symlink():
        raise GateError("linked-worktree Git commondir is outside this protocol")
    common_dir = git_dir
    if not common_dir.is_dir() or common_dir.is_symlink():
        raise GateError("resolved campaign common Git directory is not regular")
    alternates = common_dir / "objects/info/alternates"
    if alternates.exists() or alternates.is_symlink():
        raise GateError("Git object alternates are forbidden for campaign custody")
    replace_dir = common_dir / "refs/replace"
    if replace_dir.is_symlink() or (
        replace_dir.is_dir() and any(replace_dir.rglob("*"))
    ):
        raise GateError("Git replacement refs are forbidden for campaign custody")
    return git_dir, common_dir


def clean_git_environment() -> dict[str, str]:
    """Allowlist Git's environment; inherited repository selectors are forbidden."""
    return {
        "PATH": "/usr/bin:/bin",
        "LANG": "C",
        "LC_ALL": "C",
        "GIT_OPTIONAL_LOCKS": "0",
        "GIT_CONFIG_NOSYSTEM": "1",
        "GIT_CONFIG_GLOBAL": os.devnull,
        "GIT_NO_REPLACE_OBJECTS": "1",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_SSH_COMMAND": (
            "/usr/bin/ssh -F /dev/null -oBatchMode=yes "
            "-oStrictHostKeyChecking=yes"
        ),
    }


def git_process(
    repository: Path,
    arguments: Sequence[str],
) -> subprocess.CompletedProcess[bytes]:
    repository = repository.resolve()
    if not GIT_EXECUTABLE.is_file() or GIT_EXECUTABLE.is_symlink():
        raise GateError("fixed Git executable is absent, nonregular, or a symlink")
    command = [str(GIT_EXECUTABLE), "--no-replace-objects", "--literal-pathspecs"]
    if not arguments or arguments[0] != "init":
        git_dir, _common_dir = trusted_git_layout(repository)
        command.extend(
            [f"--git-dir={git_dir}", f"--work-tree={repository}"]
        )
    command.extend(arguments)
    return subprocess.run(
        command,
        cwd=repository,
        env=clean_git_environment(),
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
    )


def git_bytes(repository: Path, arguments: Sequence[str]) -> bytes:
    completed = git_process(repository, arguments)
    if completed.returncode != 0:
        raise GateError(
            f"git {' '.join(arguments)} failed ({completed.returncode}): "
            f"{completed.stderr.decode(errors='replace')[-2000:]}"
        )
    return completed.stdout


def git_blob_at_commit(
    repository: Path,
    commit: str,
    path: Path,
) -> tuple[str, bytes]:
    relative = str(path.resolve(strict=False).relative_to(repository.resolve()))
    listing = git_bytes(
        repository,
        ["ls-tree", "-z", "--full-tree", commit, "--", relative],
    )
    records = [record for record in listing.split(b"\0") if record]
    if len(records) != 1 or b"\t" not in records[0]:
        raise GateError(f"Git commit {commit} does not contain exactly one {relative}")
    header, listed_path = records[0].split(b"\t", 1)
    try:
        mode, kind, object_id = header.decode("ascii").split()
    except (UnicodeDecodeError, ValueError) as error:
        raise GateError(f"malformed Git tree record for {relative}") from error
    if (
        kind != "blob"
        or mode not in {"100644", "100755"}
        or listed_path != os.fsencode(relative)
    ):
        raise GateError(f"Git tree entry is not the expected regular file: {relative}")
    return object_id, git_bytes(repository, ["cat-file", "blob", object_id])


def verify_git_anchor(
    repository: Path,
    preregistration_path: Path,
    preregistration_sha256: str,
    claimed_commit: str,
    runner_path: Path,
    runner_sha256: str,
    *,
    expected_head: str | None = None,
    expected_origin_url: str | None = None,
    expected_published_ref: str | None = None,
    expected_published_head: str | None = None,
) -> GitAnchor:
    repository = repository.resolve()
    preregistration_path = preregistration_path.resolve(strict=False)
    runner_path = runner_path.resolve(strict=False)
    if not preregistration_path.is_relative_to(
        repository
    ) or not runner_path.is_relative_to(repository):
        raise GateError("Git-anchored files must be inside the campaign repository")
    if GIT_COMMIT_PATTERN.fullmatch(claimed_commit) is None:
        raise GateError("preregistration anchor must be one full hexadecimal commit ID")
    git_dir, common_dir = trusted_git_layout(repository)
    top = git_bytes(repository, ["rev-parse", "--show-toplevel"]).decode().strip()
    if Path(top).resolve() != repository:
        raise GateError("campaign ROOT is not the active Git worktree root")
    observed_git_dir = Path(
        git_bytes(repository, ["rev-parse", "--absolute-git-dir"])
        .decode()
        .strip()
    ).resolve()
    observed_common_dir = Path(
        git_bytes(repository, ["rev-parse", "--path-format=absolute", "--git-common-dir"])
        .decode()
        .strip()
    ).resolve()
    if observed_git_dir != git_dir or observed_common_dir != common_dir:
        raise GateError("Git-reported metadata directories differ from no-follow layout")
    config_path = common_dir / "config"
    git_config_sha256 = sha256_path(config_path)
    dangerous_config = git_process(
        repository,
        [
            "config",
            "--local",
            "--get-regexp",
            (
                r"^(url\..*\.insteadof|core\.sshcommand|"
                r"remote\.origin\.(uploadpack|receivepack)|"
                r"core\.alternaterefscommand)$"
            ),
        ],
    )
    if dangerous_config.returncode not in {0, 1} or dangerous_config.stdout.strip():
        raise GateError("campaign Git config contains forbidden transport/object indirection")
    replacement_refs = git_bytes(repository, ["for-each-ref", "refs/replace"])
    if replacement_refs.strip():
        raise GateError("campaign Git database contains packed replacement refs")
    anchor = (
        git_bytes(repository, ["rev-parse", "--verify", f"{claimed_commit}^{{commit}}"])
        .decode("ascii")
        .strip()
    )
    if anchor != claimed_commit.lower():
        raise GateError("preregistration anchor is not the exact full commit ID")
    head = (
        git_bytes(repository, ["rev-parse", "--verify", "HEAD^{commit}"])
        .decode("ascii")
        .strip()
    )
    if expected_head is not None and head != expected_head:
        raise GateError("Git HEAD changed after registered execution began")
    origin_url: str | None = None
    published_ref: str | None = None
    published_head: str | None = None
    if (expected_origin_url is None) != (expected_published_ref is None):
        raise GateError("published Git identity requires both origin URL and ref")
    if expected_origin_url is not None and expected_published_ref is not None:
        origin_url = git_bytes(repository, ["remote", "get-url", "origin"]).decode().strip()
        if origin_url != expected_origin_url:
            raise GateError("campaign origin URL differs from registered publication remote")
        published_ref = expected_published_ref
        if expected_published_head is None:
            listing = git_bytes(
                repository,
                [
                    "ls-remote",
                    "--exit-code",
                    expected_origin_url,
                    expected_published_ref,
                ],
            )
            records = [line.split() for line in listing.splitlines() if line.strip()]
            if len(records) != 1 or len(records[0]) != 2:
                raise GateError("publication remote returned an ambiguous registered ref")
            published_head = records[0][0].decode("ascii")
            published_ref = records[0][1].decode("ascii")
        else:
            published_head = expected_published_head
        if published_ref != expected_published_ref or published_head != head:
            raise GateError("execution HEAD is not the exact registered published head")
    ancestry = git_process(repository, ["merge-base", "--is-ancestor", anchor, head])
    if ancestry.returncode == 1:
        raise GateError("preregistration commit is not an ancestor of execution HEAD")
    if ancestry.returncode != 0:
        raise GateError(
            "Git could not establish preregistration ancestry: "
            + ancestry.stderr.decode(errors="replace")[-2000:]
        )

    preregistration_relative = str(preregistration_path.relative_to(repository))
    runner_relative = str(runner_path.relative_to(repository))
    dirty = git_bytes(
        repository,
        [
            "status",
            "--porcelain=v1",
            "-z",
            "--untracked-files=all",
            "--",
            preregistration_relative,
            runner_relative,
        ],
    )
    if dirty:
        raise GateError(
            "runner or preregistration is dirty, staged, deleted, or untracked relative to HEAD"
        )

    live_preregistration = stable_regular_bytes(preregistration_path)
    live_runner = stable_regular_bytes(runner_path)
    if hashlib.sha256(live_preregistration).hexdigest() != preregistration_sha256:
        raise GateError("live preregistration bytes differ from the registered SHA-256")
    if hashlib.sha256(live_runner).hexdigest() != runner_sha256:
        raise GateError("live runner bytes differ from the registered SHA-256")
    anchor_blob, anchor_bytes = git_blob_at_commit(
        repository, anchor, preregistration_path
    )
    head_preregistration_blob, head_preregistration_bytes = git_blob_at_commit(
        repository, head, preregistration_path
    )
    head_runner_blob, head_runner_bytes = git_blob_at_commit(
        repository, head, runner_path
    )
    if (
        anchor_bytes != live_preregistration
        or head_preregistration_bytes != live_preregistration
    ):
        raise GateError(
            "preregistration bytes differ between anchor commit, execution HEAD, and worktree"
        )
    if head_runner_bytes != live_runner:
        raise GateError("runner bytes differ between execution HEAD and worktree")
    object_format = (
        git_bytes(repository, ["rev-parse", "--show-object-format"])
        .decode("ascii")
        .strip()
    )
    return GitAnchor(
        preregistration_commit=anchor,
        execution_head_commit=head,
        preregistration_blob_oid=anchor_blob,
        head_preregistration_blob_oid=head_preregistration_blob,
        head_runner_blob_oid=head_runner_blob,
        object_format=object_format,
        worktree=str(repository),
        git_dir=str(git_dir),
        git_common_dir=str(common_dir),
        git_config_sha256=git_config_sha256,
        git_executable=str(GIT_EXECUTABLE),
        git_executable_sha256=sha256_path(GIT_EXECUTABLE),
        origin_url=origin_url,
        published_ref=published_ref,
        published_head_commit=published_head,
    )


def capture_custody(registration: Registration) -> dict[str, str]:
    runner_sha256 = registration.runner_sha256
    if sha256_path(SCRIPT) != runner_sha256:
        raise GateError("live G-0081 runner differs from registered source pin")
    anchor = verify_git_anchor(
        ROOT,
        registration.path,
        registration.sha256,
        registration.git_anchor.preregistration_commit,
        SCRIPT,
        runner_sha256,
        expected_head=registration.git_anchor.execution_head_commit,
        expected_origin_url=EXPECTED_ORIGIN_URL,
        expected_published_ref=EXPECTED_PUBLISHED_REF,
        expected_published_head=registration.git_anchor.published_head_commit,
    )
    if anchor != registration.git_anchor:
        raise GateError("live Git anchor differs from validated registration")
    values = {
        label: sha256_path(path) for label, (path, _expected) in STATIC_BINDINGS.items()
    }
    values["g0081_runner"] = runner_sha256
    values["g0081_preregistration_path"] = relative_path(registration.path)
    values["g0081_preregistration"] = registration.sha256
    values.update({f"git_{key}": value for key, value in anchor.receipt().items()})
    return values


def recapture_custody(expected: dict[str, str]) -> dict[str, str]:
    required = (
        "g0081_preregistration_path",
        "g0081_preregistration",
        "g0081_runner",
        "git_preregistration_commit",
        "git_execution_head_commit",
    )
    if any(key not in expected for key in required):
        raise GateError("cached custody lacks committed Git-anchor fields")
    path = ROOT / expected["g0081_preregistration_path"]
    anchor = verify_git_anchor(
        ROOT,
        path,
        expected["g0081_preregistration"],
        expected["git_preregistration_commit"],
        SCRIPT,
        expected["g0081_runner"],
        expected_head=expected["git_execution_head_commit"],
        expected_origin_url=EXPECTED_ORIGIN_URL,
        expected_published_ref=EXPECTED_PUBLISHED_REF,
        expected_published_head=expected.get("git_published_head_commit"),
    )
    values = {
        label: sha256_path(source)
        for label, (source, _digest) in STATIC_BINDINGS.items()
    }
    values["g0081_runner"] = expected["g0081_runner"]
    values["g0081_preregistration_path"] = expected["g0081_preregistration_path"]
    values["g0081_preregistration"] = expected["g0081_preregistration"]
    values.update({f"git_{key}": value for key, value in anchor.receipt().items()})
    return values


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


def create_fresh_cache_namespace(directory: Path) -> tuple[int, int]:
    """Create the registered cache directory exactly once, without following it."""
    require_contained(directory)
    parent = directory.parent
    if not parent.is_dir() or parent.is_symlink():
        raise GateError("cache namespace parent must be an existing regular directory")
    directory_flags = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(
        os, "O_NOFOLLOW", 0
    )
    parent_fd = os.open(parent, directory_flags)
    try:
        try:
            os.mkdir(directory.name, mode=0o700, dir_fd=parent_fd)
        except FileExistsError as error:
            raise GateError(
                "registered cache namespace must not exist before public execution"
            ) from error
        namespace_fd = os.open(directory.name, directory_flags, dir_fd=parent_fd)
        try:
            opened = os.fstat(namespace_fd)
            listed = os.stat(directory.name, dir_fd=parent_fd, follow_symlinks=False)
            if (
                not stat.S_ISDIR(opened.st_mode)
                or not stat.S_ISDIR(listed.st_mode)
                or (opened.st_dev, opened.st_ino) != (listed.st_dev, listed.st_ino)
            ):
                raise GateError("fresh cache namespace inode identity drift")
            identity = (opened.st_dev, opened.st_ino)
        finally:
            os.close(namespace_fd)
    finally:
        os.close(parent_fd)
    return identity


@contextmanager
def exclusive_cache_lock(path: Path) -> Iterator[int]:
    require_contained(path)
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise GateError("cache lock parent must be a regular directory")
    flags = (
        os.O_RDWR
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        descriptor = os.open(path, flags, 0o600)
    except OSError as error:
        raise GateError(f"cache lock could not be opened without following links: {path}") from error
    try:
        opened = os.fstat(descriptor)
        listed = path.stat(follow_symlinks=False)
        if (
            not stat.S_ISREG(opened.st_mode)
            or not stat.S_ISREG(listed.st_mode)
            or (opened.st_dev, opened.st_ino) != (listed.st_dev, listed.st_ino)
        ):
            raise GateError("cache lock descriptor/path identity drift before mutation")
        try:
            fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise GateError(f"another G-0081 execution owns {path}") from error
        os.ftruncate(descriptor, 0)
        os.write(descriptor, f"pid={os.getpid()}\n".encode())
        os.fsync(descriptor)
        yield descriptor
    finally:
        try:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
        finally:
            os.close(descriptor)


def write_all(descriptor: int, payload: bytes) -> None:
    offset = 0
    while offset < len(payload):
        written = os.write(descriptor, payload[offset:])
        if written <= 0:
            raise GateError("anonymous capability pipe accepted no bytes")
        offset += written


def close_quietly(descriptor: int) -> None:
    try:
        os.close(descriptor)
    except OSError:
        pass


def set_parent_death_signal(expected_parent_pid: int, death_signal: int) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    prctl = libc.prctl
    prctl.argtypes = [
        ctypes.c_int,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
        ctypes.c_ulong,
    ]
    prctl.restype = ctypes.c_int
    if prctl(PR_SET_PDEATHSIG, death_signal, 0, 0, 0) != 0:
        error_number = ctypes.get_errno()
        raise GateError(f"prctl(PR_SET_PDEATHSIG) failed: errno={error_number}")
    if os.getppid() != expected_parent_pid:
        if os.getpgrp() == os.getpid():
            os.killpg(os.getpgrp(), signal.SIGKILL)
        os.kill(os.getpid(), signal.SIGKILL)


def kill_kernel_process_group(_signum: int, _frame: object) -> None:
    os.killpg(os.getpgrp(), signal.SIGKILL)


def binding_hash_map() -> dict[str, str]:
    return {label: digest for label, (_path, digest) in STATIC_BINDINGS.items()}


def validate_registration(
    arguments: argparse.Namespace,
    *,
    expected_published_head: str | None = None,
) -> Registration:
    required = {
        "--preregistration": arguments.preregistration,
        "--preregistration-commit": arguments.preregistration_commit,
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
    assert isinstance(arguments.preregistration_commit, str)
    git_anchor = verify_git_anchor(
        ROOT,
        preregistration,
        preregistration_sha256,
        arguments.preregistration_commit,
        SCRIPT,
        runner_sha256,
        expected_origin_url=EXPECTED_ORIGIN_URL,
        expected_published_ref=EXPECTED_PUBLISHED_REF,
        expected_published_head=expected_published_head,
    )
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
        "registration_protocol": "published-git-layout-ancestor-clean-HEAD-v2",
        "execution_protocol": "public-local-closure-fork-pipe-pdeath-group-v2",
        "cache_policy": "fresh-namespace-no-reuse-v1",
        "interrupted_run_policy": "registration-spent-new-preregistration-required",
        "parent_finalization_protocol": "stage-chain-and-rref-replay-v1",
        "registered_git_executable": str(GIT_EXECUTABLE),
        "registered_git_executable_sha256": sha256_path(GIT_EXECUTABLE),
        "published_origin_url": EXPECTED_ORIGIN_URL,
        "published_ref": EXPECTED_PUBLISHED_REF,
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
    cache_run_id = document.get("cache_run_id")
    if (
        not isinstance(cache_run_id, str)
        or CACHE_RUN_ID_PATTERN.fullmatch(cache_run_id) is None
        or directory.parent.resolve() != HERE.resolve()
        or directory.name != f"cache-{cache_run_id}"
    ):
        raise GateError("registered cache path is not the fresh run-ID namespace")
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
        git_anchor,
    )


def revalidate_public_registration(
    registration: Registration,
    *,
    recheck_publication_remote: bool = True,
) -> Registration:
    """Rebuild a caller-supplied Registration through the sole public validator."""
    if type(registration) is not Registration:
        raise GateError("public execution requires an exact validated Registration")
    arguments = argparse.Namespace(
        preregistration=registration.path,
        preregistration_commit=registration.git_anchor.preregistration_commit,
        expected_runner_sha256=registration.runner_sha256,
        expected_preregistration_sha256=registration.sha256,
        output=registration.output,
        cache_dir=registration.cache_dir,
    )
    rebuilt = validate_registration(
        arguments,
        expected_published_head=(
            None
            if recheck_publication_remote
            else registration.git_anchor.published_head_commit
        ),
    )
    if rebuilt != registration:
        raise GateError("caller-supplied Registration differs from public revalidation")
    return rebuilt


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


def initialize_matrix_worker(cache_path: str, expected_parent_pid: int) -> None:
    global _WORKER_CACHE
    # Pool workers inherit the kernel's SIGTERM group-kill handler across fork.
    # Restore normal Pool.terminate() semantics; PDEATHSIG below independently
    # kills each worker if the kernel parent disappears.
    signal.signal(signal.SIGTERM, signal.SIG_DFL)
    set_parent_death_signal(expected_parent_pid, signal.SIGKILL)
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
    execution_capability_sha256: str,
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
        or receipt.get("execution_capability_sha256")
        != execution_capability_sha256
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


def build_fresh_c_cache(
    paths: CachePaths,
    evaluator: FastEvaluator,
    custody: dict[str, str],
    deadline: float,
    execution_capability_sha256: str,
) -> tuple[np.ndarray, dict[str, object]]:
    c_paths = (
        paths.c_final,
        paths.c_partial,
        paths.c_progress,
        paths.c_receipt,
        paths.c_receipt_pending,
    )
    if any(path.exists() or path.is_symlink() for path in c_paths):
        raise GateError("public execution refuses every pre-existing C cache or journal")
    tasks = chunk_tasks()
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
        "execution_capability_sha256": execution_capability_sha256,
        "evaluator": evaluator.cache_contract(),
        "custody": custody,
        "completed_chunks": {},
    }
    write_json_exclusive(paths.c_progress, progress)

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
            initargs=(str(paths.c_partial), os.getpid()),
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
        "execution_capability_sha256": execution_capability_sha256,
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
        execution_capability_sha256=execution_capability_sha256,
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
    execution_capability_sha256: str,
    c_receipt: dict[str, object],
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
        "execution_capability_sha256": execution_capability_sha256,
        "source_C_npy_sha256": sha256_path(paths.c_final),
        "source_C_raw_uint32_c_sha256": c_receipt["raw_uint32_c_sha256"],
        "source_C_receipt_sha256": sha256_path(paths.c_receipt),
        "npy_sha256": sha256_path(paths.s_partial),
        "raw_uint32_c_sha256": raw_digest.hexdigest(),
        "custody": {"start": custody, "end": end, "identical": True},
    }
    write_json_exclusive(paths.s_receipt_pending, receipt)
    del exported
    promote_exclusive(paths.s_partial, paths.s_final)
    promote_exclusive(paths.s_receipt_pending, paths.s_receipt)
    return receipt


def construct_fresh_s_cache(
    adapter: ModuleType,
    paths: CachePaths,
    custody: dict[str, str],
    old: np.ndarray,
    c_matrix: np.ndarray,
    rows: np.ndarray,
    columns: np.ndarray,
    q: np.ndarray,
    execution_capability_sha256: str,
    c_receipt: dict[str, object],
) -> tuple[np.ndarray, dict[str, object]]:
    s_paths = (
        paths.s_final,
        paths.s_partial,
        paths.s_receipt,
        paths.s_receipt_pending,
    )
    if any(path.exists() or path.is_symlink() for path in s_paths):
        raise GateError("public execution refuses every pre-existing Schur cache")

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
        export_native_cache(
            native,
            schur,
            paths,
            custody,
            execution_capability_sha256,
            c_receipt,
        )
    finally:
        for matrix in (schur, right, lam, binv, aqp):
            if matrix is not None:
                native.clear(matrix)
        native.cleanup()
    matrix, receipt = validate_complete_cache(
        paths.s_final,
        paths.s_receipt,
        schema=SCHEMA_S_CACHE,
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
        custody=custody,
        execution_capability_sha256=execution_capability_sha256,
    )
    if (
        receipt.get("source_C_npy_sha256") != sha256_path(paths.c_final)
        or receipt.get("source_C_raw_uint32_c_sha256")
        != c_receipt.get("raw_uint32_c_sha256")
        or receipt.get("source_C_receipt_sha256") != sha256_path(paths.c_receipt)
    ):
        raise GateError("Schur cache is not bound to the current-run C transaction")
    return matrix, receipt


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
    pivot_array = np.asarray(pivots, dtype=np.int64)
    for row_index in range(rank):
        pivot_values = np.remainder(
            native.row(matrix, row_index, SCHUR_COLUMNS)[pivot_array], PRIME
        )
        if np.count_nonzero(pivot_values) != 1 or int(pivot_values[row_index]) != 1:
            raise GateError("native RREF pivot columns are not the identity matrix")
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
    pivot_array = np.asarray(pivots, dtype=np.int64)
    for start in range(0, rank, 32):
        stop = min(start + 32, rank)
        pivot_block = np.remainder(matrix[start:stop][:, pivot_array], PRIME)
        for local, row_index in enumerate(range(start, stop)):
            if (
                np.count_nonzero(pivot_block[local]) != 1
                or int(pivot_block[local, row_index]) != 1
            ):
                raise GateError("persisted RREF pivot columns are not the identity matrix")
    return pivots, rhs


def export_native_rref_cache(
    native: object,
    matrix: object,
    rank_augmented: int,
    pivots: Sequence[int],
    paths: CachePaths,
    custody: dict[str, str],
    rref_seconds: float,
    execution_capability_sha256: str,
    s_receipt: dict[str, object],
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
        "execution_capability_sha256": execution_capability_sha256,
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
        "source_pre_RREF_S_raw_uint32_c_sha256": s_receipt[
            "raw_uint32_c_sha256"
        ],
        "source_pre_RREF_S_receipt_sha256": sha256_path(paths.s_receipt),
        "npy_sha256": sha256_path(paths.r_partial),
        "raw_uint32_c_sha256": raw_digest.hexdigest(),
        "custody": {"start": custody, "end": end, "identical": True},
    }
    write_json_exclusive(paths.r_receipt_pending, receipt)
    del exported
    promote_exclusive(paths.r_partial, paths.r_final)
    promote_exclusive(paths.r_receipt_pending, paths.r_receipt)
    return receipt


def compute_fresh_rref(
    adapter: ModuleType,
    paths: CachePaths,
    custody: dict[str, str],
    execution_capability_sha256: str,
    s_receipt: dict[str, object],
) -> tuple[np.ndarray, dict[str, object], list[int], list[int]]:
    r_paths = (
        paths.r_final,
        paths.r_partial,
        paths.r_receipt,
        paths.r_receipt_pending,
    )
    if any(path.exists() or path.is_symlink() for path in r_paths):
        raise GateError("public execution refuses every pre-existing RREF cache")

    native = adapter.NativeFlint()
    bind_extended_native(native)
    matrix = load_native_cache(native, paths.s_final, (QUOTIENT_ROWS, SCHUR_COLUMNS))
    try:
        started = time.perf_counter()
        rank = int(native.lib.nmod_mat_rref(native.pointer(matrix)))
        rref_seconds = time.perf_counter() - started
        pivots, rhs = scan_rref(native, matrix, rank)
        export_native_rref_cache(
            native,
            matrix,
            rank,
            pivots,
            paths,
            custody,
            rref_seconds,
            execution_capability_sha256,
            s_receipt,
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
        execution_capability_sha256=execution_capability_sha256,
    )
    replay_pivots, replay_rhs = scan_rref_array(rref, rank)
    if (
        replay_pivots != pivots
        or replay_rhs != rhs
        or receipt.get("source_pre_RREF_S_sha256") != sha256_path(paths.s_final)
        or receipt.get("source_pre_RREF_S_raw_uint32_c_sha256")
        != s_receipt.get("raw_uint32_c_sha256")
        or receipt.get("source_pre_RREF_S_receipt_sha256")
        != sha256_path(paths.s_receipt)
    ):
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
    execution_capability_sha256: str,
    s_receipt: dict[str, object],
) -> dict[str, object]:
    s_cache = np.load(paths.s_final, mmap_mode="r", allow_pickle=False)
    _rref, rref_receipt, pivots, rhs = compute_fresh_rref(
        adapter,
        paths,
        custody,
        execution_capability_sha256,
        s_receipt,
    )
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


def resource_unresolved_report(
    registration: Registration,
    reason: str,
    begun: float,
    start_custody: dict[str, str],
) -> dict[str, object]:
    end = capture_custody(registration)
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
        "git_anchor": registration.git_anchor.receipt(),
        "custody": {
            "start": start_custody,
            "end": end,
            "identical": start_custody == end,
        },
        "wall_seconds": time.monotonic() - begun,
    }


def open_log_exclusive(path: Path) -> int:
    require_contained(path)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    return os.open(path, flags, 0o600)


def read_log_tail(path: Path, maximum_bytes: int) -> str:
    payload = stable_regular_bytes(path)
    return payload[-maximum_bytes:].decode(errors="replace")


def signal_isolated_process_group(pid: int, selected_signal: int) -> None:
    try:
        os.killpg(pid, selected_signal)
        return
    except ProcessLookupError:
        pass
    try:
        os.kill(pid, selected_signal)
    except ProcessLookupError:
        pass


def wait_for_child(pid: int, deadline: float) -> int | None:
    while True:
        try:
            observed, wait_status = os.waitpid(pid, os.WNOHANG)
        except InterruptedError:
            continue
        if observed == pid:
            return os.waitstatus_to_exitcode(wait_status)
        if time.monotonic() >= deadline:
            return None
        time.sleep(min(0.1, max(0.0, deadline - time.monotonic())))


def parent_finalize_cache_chain(
    registration: Registration,
    paths: CachePaths,
    namespace_identity: tuple[int, int],
    lock_fd: int,
    custody: dict[str, str],
    execution_capability_sha256: str,
    report: dict[str, object],
) -> dict[str, object]:
    """Read-only parent replay that roots the child decision in fresh C/S/R bytes."""
    directory_stat = paths.directory.stat(follow_symlinks=False)
    lock_stat = os.fstat(lock_fd)
    if (
        not stat.S_ISDIR(directory_stat.st_mode)
        or (directory_stat.st_dev, directory_stat.st_ino) != namespace_identity
        or not stat.S_ISREG(lock_stat.st_mode)
    ):
        raise GateError("parent finalizer cache namespace/lock identity drift")
    expected_names = {
        paths.lock.name,
        paths.c_final.name,
        paths.c_receipt.name,
        paths.s_final.name,
        paths.s_receipt.name,
        paths.r_final.name,
        paths.r_receipt.name,
    }
    observed_names = {path.name for path in paths.directory.iterdir()}
    if observed_names != expected_names:
        raise GateError(
            "successful cache namespace has unexpected, partial, or missing files: "
            f"{sorted(observed_names ^ expected_names)}"
        )
    c_matrix, c_receipt = validate_complete_cache(
        paths.c_final,
        paths.c_receipt,
        schema=SCHEMA_C_CACHE,
        shape=(TOTAL_ROWS, NEW_COLUMNS),
        custody=custody,
        execution_capability_sha256=execution_capability_sha256,
    )
    s_matrix, s_receipt = validate_complete_cache(
        paths.s_final,
        paths.s_receipt,
        schema=SCHEMA_S_CACHE,
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
        custody=custody,
        execution_capability_sha256=execution_capability_sha256,
    )
    r_matrix, r_receipt = validate_complete_cache(
        paths.r_final,
        paths.r_receipt,
        schema=SCHEMA_R_CACHE,
        shape=(QUOTIENT_ROWS, SCHUR_COLUMNS),
        custody=custody,
        execution_capability_sha256=execution_capability_sha256,
    )
    if (
        s_receipt.get("source_C_npy_sha256") != sha256_path(paths.c_final)
        or s_receipt.get("source_C_raw_uint32_c_sha256")
        != c_receipt.get("raw_uint32_c_sha256")
        or s_receipt.get("source_C_receipt_sha256")
        != sha256_path(paths.c_receipt)
        or r_receipt.get("source_pre_RREF_S_sha256")
        != sha256_path(paths.s_final)
        or r_receipt.get("source_pre_RREF_S_raw_uint32_c_sha256")
        != s_receipt.get("raw_uint32_c_sha256")
        or r_receipt.get("source_pre_RREF_S_receipt_sha256")
        != sha256_path(paths.s_receipt)
    ):
        raise GateError("parent finalizer C-to-S-to-R source chain drift")
    scientific = report.get("scientific_payload")
    if not isinstance(scientific, dict) or canonical_sha256(scientific) != report.get(
        "scientific_payload_sha256"
    ):
        raise GateError("parent finalizer scientific payload hash drift")
    decision = scientific.get("native_decision")
    if (
        scientific.get("C_cache") != c_receipt
        or scientific.get("pre_RREF_S_cache") != s_receipt
        or not isinstance(decision, dict)
        or decision.get("persisted_RREF") != r_receipt
    ):
        raise GateError("parent finalizer report/cache receipt projection drift")

    adapter = load_owned_module(
        NATIVE_ADAPTER,
        EXPECTED_NATIVE_ADAPTER_SHA256,
        "max11_native_adapter_for_g0081_parent_finalizer",
    )
    native = adapter.NativeFlint()
    bind_extended_native(native)
    replay = load_native_cache(
        native, paths.s_final, (QUOTIENT_ROWS, SCHUR_COLUMNS)
    )
    replay_started = time.perf_counter()
    try:
        rank = int(native.lib.nmod_mat_rref(native.pointer(replay)))
        pivots, rhs = scan_rref(native, replay, rank)
        for row in range(QUOTIENT_ROWS):
            expected_row = np.remainder(
                native.row(replay, row, SCHUR_COLUMNS), PRIME
            ).astype(np.uint32)
            if not np.array_equal(expected_row, r_matrix[row]):
                raise GateError(
                    f"parent RREF replay differs from persisted R at row {row}"
                )
    finally:
        native.clear(replay)
        native.cleanup()
    replay_seconds = time.perf_counter() - replay_started
    target_pivot = bool(pivots and pivots[-1] == NEW_COLUMNS)
    rank_new = rank - int(target_pivot)
    parent_result = (
        "MODULAR_SEPARATION_DISCOVERY"
        if target_pivot
        else "MODULAR_MEMBERSHIP_DISCOVERY"
    )
    pivot_new = [pivot for pivot in pivots if pivot < NEW_COLUMNS]
    if (
        r_receipt.get("rank_schur_augmented") != rank
        or r_receipt.get("rank_schur_new") != rank_new
        or r_receipt.get("ordered_pivot_columns") != pivots
        or r_receipt.get("target_coordinate_is_pivot") is not target_pivot
        or decision.get("result") != parent_result
        or decision.get("rank_schur_augmented") != rank
        or decision.get("rank_schur_new") != rank_new
        or decision.get("target_coordinate_is_pivot") is not target_pivot
        or decision.get("pivot_local_new_columns") != pivot_new
    ):
        raise GateError("parent RREF-derived decision differs from child declaration")

    member_replay = False
    if not target_pivot:
        basis_rows, basis_columns, _q, _modular = validate_inverse(adapter)
        old = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
        inverse = np.load(INVERSE_CACHE, mmap_mode="r", allow_pickle=False)
        new_pivots, new_coefficients = canonical_free_zero_solution(pivots, rhs)
        parent_solution = derive_and_replay_solution(
            old,
            c_matrix,
            inverse,
            basis_rows,
            basis_columns,
            new_pivots,
            new_coefficients,
        )
        if parent_solution != decision.get("solution"):
            raise GateError("parent all-row member replay differs from child solution")
        parent_minor = full_row_rank_minor_evidence(
            adapter,
            s_matrix,
            pivot_new,
            old,
            basis_rows,
            basis_columns,
        )
        if parent_minor != decision.get("full_row_rank_minor_evidence"):
            raise GateError("parent determinant evidence differs from child decision")
        member_replay = True

    stage_chain = {
        "registered_run_binding_sha256": canonical_sha256(
            {
                "domain": "G0081/registered-run/v2",
                "runner_sha256": registration.runner_sha256,
                "preregistration_sha256": registration.sha256,
                "git_anchor": registration.git_anchor.receipt(),
                "cache_run_id": registration.document["cache_run_id"],
                "cache_dir": relative_path(registration.cache_dir),
                "output": relative_path(registration.output),
                "static_bindings": binding_hash_map(),
                "prime": PRIME,
            }
        ),
        "C_npy_sha256": c_receipt["npy_sha256"],
        "C_receipt_sha256": sha256_path(paths.c_receipt),
        "S_npy_sha256": s_receipt["npy_sha256"],
        "S_receipt_sha256": sha256_path(paths.s_receipt),
        "R_npy_sha256": r_receipt["npy_sha256"],
        "R_receipt_sha256": sha256_path(paths.r_receipt),
        "execution_capability_sha256": execution_capability_sha256,
        "scientific_payload_sha256": report["scientific_payload_sha256"],
    }
    return {
        "protocol": "fresh-stage-chain-and-independent-rref-replay-v1",
        "fresh_namespace_inode_reverified": True,
        "exact_success_file_census": sorted(expected_names),
        "C_to_S_to_R_receipt_chain_recomputed": True,
        "stage_chain": stage_chain,
        "stage_chain_sha256": canonical_sha256(stage_chain),
        "parent_RREF_byte_for_byte_equal": True,
        "parent_RREF_seconds": replay_seconds,
        "parent_derived_result": parent_result,
        "parent_all_16738_row_member_replay": member_replay,
        "active_same_UID_or_root_adversary_excluded_from_threat_model": True,
    }


def public_run(invocation: argparse.Namespace) -> dict[str, object]:
    registration = validate_registration(invocation)
    paths = cache_paths(registration.cache_dir)
    namespace_identity = create_fresh_cache_namespace(paths.directory)
    begun = time.monotonic()
    absolute_deadline = begun + MAXIMUM_WALL_SECONDS
    with exclusive_cache_lock(paths.lock) as lock_fd:
        start_custody = capture_custody(registration)
        try:
            validate_resource_contract(paths)
        except (MemoryError, OSError) as error:
            report = resource_unresolved_report(
                registration, str(error), begun, start_custody
            )
            report["launcher"] = {
                "protocol": "public-local-closure-fork-v2",
                "kernel_started": False,
                "exclusive_cache_lock": True,
                "hard_timeout_seconds": MAXIMUM_WALL_SECONDS,
            }
            write_gzip_exclusive(registration.output, report)
            return report

        nonce = secrets.token_hex(8)
        scratch = paths.directory / f".kernel-outcome-{os.getpid()}-{nonce}.json"
        stdout_path = paths.directory / f".kernel-stdout-{os.getpid()}-{nonce}.log"
        stderr_path = paths.directory / f".kernel-stderr-{os.getpid()}-{nonce}.log"
        if any(
            path.exists() or path.is_symlink()
            for path in (scratch, stdout_path, stderr_path)
        ):
            raise GateError("isolated child scratch/log collision")
        stdout_fd = open_log_exclusive(stdout_path)
        try:
            stderr_fd = open_log_exclusive(stderr_path)
        except BaseException:
            os.close(stdout_fd)
            stdout_path.unlink()
            raise
        pipe_read, pipe_write = os.pipe2(getattr(os, "O_CLOEXEC", 0))
        capability_frame = CAPABILITY_DOMAIN + secrets.token_bytes(
            CAPABILITY_SECRET_BYTES
        )
        parent_pid = os.getpid()
        execution_capability_sha256 = hashlib.sha256(capability_frame).hexdigest()
        capability_consumed = False

        def consume_child_entry() -> dict[str, object]:
            nonlocal capability_consumed, pipe_read
            if capability_consumed:
                raise GateError("fork-child authority was already consumed")
            capability_consumed = True
            rebuilt = revalidate_public_registration(
                registration, recheck_publication_remote=False
            )
            if rebuilt != registration:
                raise GateError("fork child registration differs from parent validation")
            expected_lock_path = cache_paths(rebuilt.cache_dir).lock
            if expected_lock_path.resolve(strict=False) != paths.lock.resolve(strict=False):
                raise GateError("fork child derived a different registered cache lock")
            if os.getpid() == parent_pid or os.getppid() != parent_pid:
                raise GateError("scientific child PID/PPID differs from the public fork")
            if os.getpgrp() != os.getpid():
                raise GateError("scientific child is not its isolated process-group leader")
            pipe_stat = os.fstat(pipe_read)
            if not stat.S_ISFIFO(pipe_stat.st_mode):
                raise GateError("fork-child authority FD is not an anonymous pipe")
            payload = bytearray()
            try:
                while len(payload) < len(capability_frame):
                    block = os.read(pipe_read, len(capability_frame) - len(payload))
                    if not block:
                        break
                    payload.extend(block)
                trailing = os.read(pipe_read, 1)
            finally:
                os.close(pipe_read)
                pipe_read = -1
            if trailing or not secrets.compare_digest(
                bytes(payload), capability_frame
            ):
                raise GateError("fork-child authority frame is absent, truncated, or forged")
            lock_stat = os.fstat(lock_fd)
            path_stat = expected_lock_path.stat(follow_symlinks=False)
            if (
                not stat.S_ISREG(lock_stat.st_mode)
                or not stat.S_ISREG(path_stat.st_mode)
                or (lock_stat.st_dev, lock_stat.st_ino)
                != (path_stat.st_dev, path_stat.st_ino)
            ):
                raise GateError("inherited registered lock inode identity drift")
            probe = os.open(
                expected_lock_path,
                os.O_RDWR | getattr(os, "O_NOFOLLOW", 0),
            )
            try:
                try:
                    fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    pass
                else:
                    fcntl.flock(probe, fcntl.LOCK_UN)
                    raise GateError("inherited registered cache lock is not held")
            finally:
                os.close(probe)
            return {
                "protocol": "public-local-closure-fork-authority-v2",
                "capability_frame_sha256": execution_capability_sha256,
                "capability_pipe_consumed_and_closed": True,
                "fork_parent_pid": parent_pid,
                "kernel_pid": os.getpid(),
                "lock_path": relative_path(expected_lock_path),
                "inherited_exclusive_lock_verified": True,
                "registration_revalidated_in_child": True,
                "isolated_session_and_process_group": True,
                "parent_death_signal": (
                    "SIGKILL; timeout SIGTERM handler kills isolated group"
                ),
                "fork_workers_parent_death_signal": "SIGKILL",
            }

        def scientific_kernel(kernel_entry: dict[str, object]) -> dict[str, object]:
            kernel_begun = time.monotonic()
            deadline = kernel_begun + MAXIMUM_WALL_SECONDS
            custody = capture_custody(registration)
            bindings = replay_static_bindings()
            resources = validate_resource_contract(paths)
            resource_estimates = validate_preflight_resource_estimates()
            runner, preflight, g75, family, semantic = load_g0079_context()
            price_report, functional = load_price_contract(runner)
            adapter = load_owned_module(
                NATIVE_ADAPTER,
                EXPECTED_NATIVE_ADAPTER_SHA256,
                "max11_native_adapter_for_g0081",
            )
            basis_rows, basis_columns, q, _modular = validate_inverse(adapter)
            old = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
            inverse = np.load(INVERSE_CACHE, mmap_mode="r", allow_pickle=False)
            if old.shape != (TOTAL_ROWS, OLD_COLUMNS + 1) or old.dtype != np.dtype(
                "<i8"
            ):
                raise GateError("frozen old augmented matrix shape/dtype drift")
            evaluator = FastEvaluator(g75, family.bases, family.new_representatives)
            c_matrix, c_receipt = build_fresh_c_cache(
                paths,
                evaluator,
                custody,
                deadline,
                execution_capability_sha256,
            )
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
            s_cache, s_receipt = construct_fresh_s_cache(
                adapter,
                paths,
                custody,
                old,
                c_matrix,
                basis_rows,
                basis_columns,
                q,
                execution_capability_sha256,
                c_receipt,
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
                adapter,
                paths,
                custody,
                old,
                c_matrix,
                inverse,
                basis_rows,
                basis_columns,
                execution_capability_sha256,
                s_receipt,
            )
            end_custody = capture_custody(registration)
            if end_custody != custody:
                raise GateError(
                    "registered input/source custody changed during native kernel"
                )
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
            return {
                "schema": SCHEMA_RESULT,
                "scientific_payload": scientific,
                "scientific_payload_sha256": canonical_sha256(scientific),
                "runner_sha256": registration.runner_sha256,
                "preregistration_sha256": registration.sha256,
                "git_anchor": registration.git_anchor.receipt(),
                "kernel_entry": kernel_entry,
                "bindings": bindings,
                "semantic_source_execution": semantic,
                "resource_gate": resources,
                "frozen_resource_estimates": resource_estimates,
                "custody": {
                    "start": custody,
                    "end": end_custody,
                    "identical": True,
                },
                "wall_seconds": time.monotonic() - kernel_begun,
                "process_max_rss_kib": resource.getrusage(
                    resource.RUSAGE_SELF
                ).ru_maxrss,
                "environment": {
                    "python": platform.python_version(),
                    "numpy": np.__version__,
                    "platform": platform.platform(),
                    "workers": WORKERS,
                    "multiprocessing_start_method": "fork",
                    "native_flint": "3.6.0",
                },
            }

        def child_entry() -> None:
            exit_code = 1
            kernel_entry: dict[str, object] | None = None
            try:
                os.close(pipe_write)
                os.dup2(stdout_fd, 1)
                os.dup2(stderr_fd, 2)
                if stdout_fd not in {1, 2}:
                    os.close(stdout_fd)
                if stderr_fd not in {1, 2}:
                    os.close(stderr_fd)
                os.setsid()
                signal.signal(signal.SIGTERM, kill_kernel_process_group)
                set_parent_death_signal(parent_pid, signal.SIGKILL)
                kernel_entry = consume_child_entry()
                try:
                    child_report = scientific_kernel(kernel_entry)
                except (MemoryError, OSError, TimeoutError) as error:
                    child_report = resource_unresolved_report(
                        registration,
                        f"{type(error).__name__}: {error}",
                        begun,
                        start_custody,
                    )
                    child_report["kernel_entry"] = kernel_entry
                write_json_exclusive(scratch, child_report)
                exit_code = 0
            except BaseException:  # noqa: BLE001 -- isolated child exits closed
                traceback.print_exc()
            finally:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                finally:
                    os._exit(exit_code)

        try:
            pid = os.fork()
        except BaseException:
            os.close(pipe_read)
            os.close(pipe_write)
            os.close(stdout_fd)
            os.close(stderr_fd)
            stdout_path.unlink()
            stderr_path.unlink()
            raise
        if pid == 0:
            child_entry()
            raise AssertionError("os._exit returned")

        try:
            os.close(pipe_read)
            os.close(stdout_fd)
            os.close(stderr_fd)
            pipe_error: OSError | None = None
            try:
                write_all(pipe_write, capability_frame)
            except OSError as error:
                pipe_error = error
            finally:
                os.close(pipe_write)
            exit_code = wait_for_child(pid, absolute_deadline)
        except BaseException:
            close_quietly(pipe_read)
            close_quietly(pipe_write)
            close_quietly(stdout_fd)
            close_quietly(stderr_fd)
            signal_isolated_process_group(pid, signal.SIGKILL)
            wait_for_child(pid, time.monotonic() + 5.0)
            for log_path in (stdout_path, stderr_path):
                try:
                    log_path.unlink()
                except FileNotFoundError:
                    pass
            raise
        timed_out = exit_code is None
        if timed_out:
            signal_isolated_process_group(pid, signal.SIGTERM)
            exit_code = wait_for_child(pid, time.monotonic() + 5.0)
            if exit_code is None:
                signal_isolated_process_group(pid, signal.SIGKILL)
                exit_code = wait_for_child(pid, time.monotonic() + 5.0)
            if exit_code is None:
                raise GateError(
                    "timed-out isolated child could not be reaped after SIGKILL"
                )
        stdout = read_log_tail(stdout_path, 2_000)
        stderr = read_log_tail(stderr_path, 4_000)
        stdout_path.unlink()
        stderr_path.unlink()

        if timed_out:
            report = resource_unresolved_report(
                registration,
                f"isolated process group exceeded {MAXIMUM_WALL_SECONDS} seconds",
                begun,
                start_custody,
            )
            report["launcher"] = {
                "protocol": "public-local-closure-fork-v2",
                "kernel_started": True,
                "exclusive_cache_lock": True,
                "isolated_process_group": True,
                "parent_death_guard": True,
                "hard_timeout_seconds": MAXIMUM_WALL_SECONDS,
                "timed_out_group_terminated": True,
                "child_stdout": stdout.strip(),
                "child_stderr_tail": stderr,
            }
            write_gzip_exclusive(registration.output, report)
            return report
        if pipe_error is not None or exit_code != 0:
            raise GateError(
                f"isolated kernel failed closed (exit={exit_code}, pipe={pipe_error!r}); "
                f"stdout={stdout!r}; stderr={stderr!r}"
            )
        if not scratch.is_file() or scratch.is_symlink():
            raise GateError("isolated kernel returned without one scratch report")
        report = read_json(scratch)
        expected_capability_sha256 = hashlib.sha256(capability_frame).hexdigest()
        kernel_entry = report.get("kernel_entry")
        scientific_payload = report.get("scientific_payload")
        if (
            report.get("schema") != SCHEMA_RESULT
            or report.get("runner_sha256") != registration.runner_sha256
            or report.get("preregistration_sha256") != registration.sha256
            or report.get("git_anchor") != registration.git_anchor.receipt()
            or report.get("custody", {}).get("identical") is not True
            or not isinstance(scientific_payload, dict)
            or canonical_sha256(scientific_payload)
            != report.get("scientific_payload_sha256")
            or not isinstance(kernel_entry, dict)
            or kernel_entry.get("capability_frame_sha256") != expected_capability_sha256
            or kernel_entry.get("fork_parent_pid") != parent_pid
            or kernel_entry.get("inherited_exclusive_lock_verified") is not True
        ):
            raise GateError("isolated kernel scratch/entry contract drift")
        scratch.unlink()
        end = capture_custody(registration)
        if end != start_custody:
            raise GateError("launcher custody changed across isolated kernel")
        if scientific_payload.get("result") == "RESOURCE_UNRESOLVED":
            report["parent_finalization"] = {
                "protocol": "not-applicable-resource-unresolved",
                "scientific_outcome_computed": False,
            }
        else:
            report["parent_finalization"] = parent_finalize_cache_chain(
                registration,
                paths,
                namespace_identity,
                lock_fd,
                start_custody,
                execution_capability_sha256,
                report,
            )
        report["launcher"] = {
            "protocol": "public-local-closure-fork-v2",
            "kernel_started": True,
            "exclusive_cache_lock": True,
            "isolated_process_group": True,
            "parent_death_guard": True,
            "fork_workers_parent_death_guard": True,
            "capability_pipe_inherited_consumed_closed": True,
            "hard_timeout_seconds": MAXIMUM_WALL_SECONDS,
            "native_cleanup_confined_to_child": True,
            "child_stdout": stdout.strip(),
            "child_stderr_tail": stderr,
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
        execution_capability_sha256 = "ab" * 32
        receipt = {
            "schema": "fixture",
            "state": "complete",
            "shape": [3, 4],
            "dtype": "<u4",
            "prime": PRIME,
            "all_new_columns_retained": True,
            "price_filtering_allowed": False,
            "execution_capability_sha256": execution_capability_sha256,
            "custody": {"start": custody, "end": custody, "identical": True},
            "npy_sha256": sha256_path(data),
            "raw_uint32_c_sha256": raw_sha256(values),
        }
        write_json_exclusive(receipt_path, receipt)
        validate_complete_cache(
            data,
            receipt_path,
            schema="fixture",
            shape=(3, 4),
            custody=custody,
            execution_capability_sha256=execution_capability_sha256,
        )
        mutant = np.load(data, mmap_mode="r+")
        mutant[1, 2] += 1
        mutant.flush()
        rejected = False
        try:
            validate_complete_cache(
                data,
                receipt_path,
                schema="fixture",
                shape=(3, 4),
                custody=custody,
                execution_capability_sha256=execution_capability_sha256,
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
    source_s = np.asarray([[1, 0, 1], [0, 1, 1]], dtype=np.int64)
    forged_rref = np.asarray([[1, 0, 0], [0, 0, 1]], dtype=np.int64)
    true_rref, true_rank = numpy_rref_fixture(source_s, 101)
    forged_rank = numpy_rref_fixture(forged_rref, 101)[1]
    true_target_pivot = bool(
        [int(np.flatnonzero(row)[0]) for row in true_rref[:true_rank]][-1] == 2
    )
    forged_target_pivot = bool(
        [int(np.flatnonzero(row)[0]) for row in forged_rref[:forged_rank]][-1] == 2
    )
    if (
        np.array_equal(true_rref, forged_rref)
        or true_target_pivot
        or not forged_target_pivot
    ):
        raise GateError("forged branch-reversing RREF hostile control drift")
    return {
        "price_row_common_scalar": relation,
        "price_row_one_entry_mutant_rejected": True,
        "rank_full_Q_forces_every_frozen_Q_target_member": True,
        "rank_deficient_left_can_have_target_pivot": True,
        "characteristic_zero_minor_statement_is_one_sided": True,
        "branch_reversing_non_row_equivalent_RREF_control_detected": True,
    }


def self_test_git_anchor() -> dict[str, object]:
    with tempfile.TemporaryDirectory(dir=HERE) as temporary_text:
        repository = Path(temporary_text)
        git_bytes(repository, ["init", "-q"])
        git_bytes(repository, ["config", "user.name", "G-0081 fixture"])
        git_bytes(repository, ["config", "user.email", "g0081-fixture@example.invalid"])
        runner = repository / "runner.py"
        preregistration = repository / "preregistration.json"
        runner_payload = b"print('frozen runner')\n"
        preregistration_payload = b'{"experiment_status":"planned"}\n'
        runner.write_bytes(runner_payload)
        preregistration.write_bytes(preregistration_payload)
        git_bytes(repository, ["add", "runner.py", "preregistration.json"])
        git_bytes(repository, ["commit", "-q", "-m", "commit preregistration"])
        anchor = git_bytes(repository, ["rev-parse", "HEAD"]).decode("ascii").strip()
        (repository / "unrelated.txt").write_text("later HEAD\n", encoding="utf-8")
        git_bytes(repository, ["add", "unrelated.txt"])
        git_bytes(repository, ["commit", "-q", "-m", "advance head"])
        accepted = verify_git_anchor(
            repository,
            preregistration,
            hashlib.sha256(preregistration_payload).hexdigest(),
            anchor,
            runner,
            hashlib.sha256(runner_payload).hexdigest(),
        )

        preregistration.write_bytes(b'{"experiment_status":"post-outcome"}\n')
        dirty_rejected = False
        try:
            verify_git_anchor(
                repository,
                preregistration,
                sha256_path(preregistration),
                anchor,
                runner,
                hashlib.sha256(runner_payload).hexdigest(),
            )
        except GateError:
            dirty_rejected = True
        if not dirty_rejected:
            raise GateError(
                "dirty post-outcome preregistration escaped Git anchor gate"
            )
        preregistration.write_bytes(preregistration_payload)

        runner.write_bytes(b"print('dirty runner')\n")
        dirty_runner_rejected = False
        try:
            verify_git_anchor(
                repository,
                preregistration,
                hashlib.sha256(preregistration_payload).hexdigest(),
                anchor,
                runner,
                sha256_path(runner),
            )
        except GateError:
            dirty_runner_rejected = True
        if not dirty_runner_rejected:
            raise GateError("dirty runner escaped Git HEAD gate")
        runner.write_bytes(runner_payload)

        untracked = repository / "late-preregistration.json"
        untracked.write_bytes(preregistration_payload)
        untracked_rejected = False
        try:
            verify_git_anchor(
                repository,
                untracked,
                hashlib.sha256(preregistration_payload).hexdigest(),
                anchor,
                runner,
                hashlib.sha256(runner_payload).hexdigest(),
            )
        except GateError:
            untracked_rejected = True
        if not untracked_rejected:
            raise GateError(
                "untracked post-outcome preregistration escaped Git anchor gate"
            )
        untracked.unlink()

        changed_payload = b'{"experiment_status":"planned-but-changed"}\n'
        preregistration.write_bytes(changed_payload)
        git_bytes(repository, ["add", "preregistration.json"])
        git_bytes(repository, ["commit", "-q", "-m", "change preregistration"])
        changed_after_anchor_rejected = False
        try:
            verify_git_anchor(
                repository,
                preregistration,
                hashlib.sha256(changed_payload).hexdigest(),
                anchor,
                runner,
                hashlib.sha256(runner_payload).hexdigest(),
            )
        except GateError:
            changed_after_anchor_rejected = True
        if not changed_after_anchor_rejected:
            raise GateError("clean post-anchor preregistration mutation escaped")

        poisoned = {
            "GIT_DIR": str(repository / "foreign.git"),
            "GIT_WORK_TREE": str(repository / "foreign-worktree"),
            "GIT_INDEX_FILE": str(repository / "foreign.index"),
            "GIT_OBJECT_DIRECTORY": str(repository / "foreign-objects"),
            "GIT_ALTERNATE_OBJECT_DIRECTORIES": str(repository / "alternates"),
            "GIT_NAMESPACE": "attacker",
            "GIT_CONFIG_GLOBAL": str(repository / "attacker.gitconfig"),
            "GIT_CONFIG_SYSTEM": str(repository / "attacker-system.gitconfig"),
            "GIT_REPLACE_REF_BASE": "refs/replace-attacker/",
            "PATH": str(repository),
        }
        saved = {key: os.environ.get(key) for key in poisoned}
        try:
            os.environ.update(poisoned)
            poisoned_environment_accepted = verify_git_anchor(
                repository,
                preregistration,
                hashlib.sha256(changed_payload).hexdigest(),
                git_bytes(repository, ["rev-parse", "HEAD"]).decode("ascii").strip(),
                runner,
                hashlib.sha256(runner_payload).hexdigest(),
            )
        finally:
            for key, value in saved.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
        if poisoned_environment_accepted.worktree != str(repository.resolve()):
            raise GateError("poisoned Git environment changed the trusted worktree")

    with tempfile.TemporaryDirectory(dir=HERE) as foreign_fixture_text:
        fixture_root = Path(foreign_fixture_text)
        actual = fixture_root / "actual"
        foreign = fixture_root / "foreign"
        actual.mkdir()
        foreign.mkdir()
        for repository in (actual, foreign):
            git_bytes(repository, ["init", "-q"])
            git_bytes(repository, ["config", "user.name", "G-0081 fixture"])
            git_bytes(
                repository,
                ["config", "user.email", "g0081-fixture@example.invalid"],
            )
        runner_payload = b"print('same runner')\n"
        preregistration_payload = b'{"experiment_status":"planned"}\n'
        (actual / "runner.py").write_bytes(runner_payload)
        git_bytes(actual, ["add", "runner.py"])
        git_bytes(actual, ["commit", "-q", "-m", "actual lacks preregistration"])
        (actual / "preregistration.json").write_bytes(preregistration_payload)
        (foreign / "runner.py").write_bytes(runner_payload)
        (foreign / "preregistration.json").write_bytes(preregistration_payload)
        git_bytes(foreign, ["add", "runner.py", "preregistration.json"])
        git_bytes(foreign, ["commit", "-q", "-m", "foreign has preregistration"])
        foreign_anchor = (
            git_bytes(foreign, ["rev-parse", "HEAD"]).decode("ascii").strip()
        )
        saved_git_dir = os.environ.get("GIT_DIR")
        saved_work_tree = os.environ.get("GIT_WORK_TREE")
        try:
            os.environ["GIT_DIR"] = str(foreign / ".git")
            os.environ["GIT_WORK_TREE"] = str(actual)
            foreign_rejected = False
            try:
                verify_git_anchor(
                    actual,
                    actual / "preregistration.json",
                    hashlib.sha256(preregistration_payload).hexdigest(),
                    foreign_anchor,
                    actual / "runner.py",
                    hashlib.sha256(runner_payload).hexdigest(),
                )
            except GateError:
                foreign_rejected = True
        finally:
            if saved_git_dir is None:
                os.environ.pop("GIT_DIR", None)
            else:
                os.environ["GIT_DIR"] = saved_git_dir
            if saved_work_tree is None:
                os.environ.pop("GIT_WORK_TREE", None)
            else:
                os.environ["GIT_WORK_TREE"] = saved_work_tree
        if not foreign_rejected:
            raise GateError("foreign Git object database escaped the trusted layout")
    return {
        "committed_ancestor_anchor_accepted": True,
        "anchor_commit": accepted.preregistration_commit,
        "execution_head_bound": True,
        "dirty_post_outcome_preregistration_rejected": True,
        "dirty_runner_rejected": True,
        "untracked_post_outcome_preregistration_rejected": True,
        "clean_post_anchor_byte_change_rejected": True,
        "poisoned_Git_environment_ignored": True,
        "foreign_object_database_with_actual_untracked_prereg_rejected": True,
        "scientific_outcome_computed": False,
    }


def self_test_entry_capability() -> dict[str, object]:
    environment = dict(os.environ)
    environment["G0081_INTERNAL_TOKEN"] = "caller-chosen-token"
    direct_cli = subprocess.run(
        [
            str(REGISTERED_PYTHON),
            "-B",
            str(SCRIPT),
            "--run",
            "--internal-run",
            "--internal-token",
            "caller-chosen-token",
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if direct_cli.returncode == 0 or b"unrecognized arguments" not in direct_cli.stderr:
        raise GateError("removed direct internal CLI unexpectedly remained callable")
    import_attempt = subprocess.run(
        [
            str(REGISTERED_PYTHON),
            "-B",
            "-c",
            (
                "import importlib.util; "
                f"s=importlib.util.spec_from_file_location('g0081_attack',{str(SCRIPT)!r}); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m)"
            ),
        ],
        cwd=ROOT,
        env=environment,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        check=False,
        timeout=10,
    )
    if (
        import_attempt.returncode == 0
        or b"CLI-only registered runner" not in import_attempt.stderr
    ):
        raise GateError("ordinary import did not fail before exposing runner helpers")
    tree = ast.parse(stable_regular_bytes(SCRIPT), filename=str(SCRIPT))
    forbidden = {
        "internal_kernel",
        "forked_kernel_child",
        "consume_kernel_capability",
    }
    module_functions = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    module_classes = {
        node.name for node in tree.body if isinstance(node, ast.ClassDef)
    }
    if forbidden & module_functions or "KernelCapability" in module_classes:
        raise GateError("module-level scientific entry/capability remains exposed")
    return {
        "ordinary_import_rejected_before_helper_definition": True,
        "no_module_level_scientific_entry_or_capability": True,
        "direct_internal_cli_and_caller_environment_token_rejected": True,
        "actual_fork_authority_is_public_run_local": True,
        "scientific_outcome_computed": False,
    }


def self_test_fresh_namespace_lock() -> dict[str, object]:
    with tempfile.TemporaryDirectory(dir=HERE) as temporary_text:
        parent = Path(temporary_text)
        namespace = parent / "cache-00000000000000000000000000000000"
        create_fresh_cache_namespace(namespace)
        if not namespace.is_dir() or namespace.is_symlink():
            raise GateError("fresh cache namespace fixture was not a regular directory")
        existing_rejected = False
        try:
            create_fresh_cache_namespace(namespace)
        except GateError:
            existing_rejected = True
        if not existing_rejected:
            raise GateError("existing empty cache namespace was reused")

        victim = parent / "victim.txt"
        victim_payload = b"must remain byte-identical\n"
        victim.write_bytes(victim_payload)
        symlink_lock = namespace / "execution.lock"
        symlink_lock.symlink_to(victim)
        symlink_lock_rejected = False
        try:
            with exclusive_cache_lock(symlink_lock):
                pass
        except GateError:
            symlink_lock_rejected = True
        if not symlink_lock_rejected or victim.read_bytes() != victim_payload:
            raise GateError("symlink cache lock was followed or mutated its victim")

        symlink_namespace = parent / "cache-11111111111111111111111111111111"
        symlink_target = parent / "namespace-target"
        symlink_target.mkdir()
        symlink_namespace.symlink_to(symlink_target, target_is_directory=True)
        namespace_symlink_rejected = False
        try:
            create_fresh_cache_namespace(symlink_namespace)
        except GateError:
            namespace_symlink_rejected = True
        if not namespace_symlink_rejected or list(symlink_target.iterdir()):
            raise GateError("symlink cache namespace was accepted or mutated")

        normal_namespace = parent / "cache-22222222222222222222222222222222"
        create_fresh_cache_namespace(normal_namespace)
        with exclusive_cache_lock(normal_namespace / "execution.lock") as descriptor:
            opened = os.fstat(descriptor)
            if not stat.S_ISREG(opened.st_mode):
                raise GateError("normal exclusive cache lock is not regular")
    return {
        "fresh_absent_namespace_created_exclusively": True,
        "existing_empty_namespace_rejected": True,
        "namespace_symlink_rejected_target_unchanged": True,
        "lock_symlink_rejected_victim_byte_identical": True,
        "normal_no_follow_exclusive_lock_accepted": True,
        "scientific_outcome_computed": False,
    }


def process_is_running(pid: int) -> bool:
    try:
        fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").split()
    except (FileNotFoundError, ProcessLookupError):
        return False
    return len(fields) >= 3 and fields[2] not in {"X", "Z"}


def self_test_process_boundary() -> dict[str, object]:
    # Simulate the fork race in which the public parent disappears before the
    # child arms PR_SET_PDEATHSIG.  The mandatory post-prctl PPID check must
    # kill the isolated child rather than let it reach any kernel work.
    race_pid = os.fork()
    if race_pid == 0:
        os.setsid()
        signal.signal(signal.SIGTERM, kill_kernel_process_group)
        set_parent_death_signal(os.getpid(), signal.SIGKILL)
        os._exit(77)
    race_exit = wait_for_child(race_pid, time.monotonic() + 5.0)
    if race_exit is None:
        signal_isolated_process_group(race_pid, signal.SIGKILL)
        race_exit = wait_for_child(race_pid, time.monotonic() + 5.0)
    if race_exit != -signal.SIGKILL:
        raise GateError(f"parent-death fork-race fixture escaped: {race_exit}")

    ready_read, ready_write = os.pipe2(getattr(os, "O_CLOEXEC", 0))
    parent_pid = os.getpid()
    kernel_pid = os.fork()
    if kernel_pid == 0:
        exit_code = 78
        try:
            os.close(ready_read)
            os.setsid()
            signal.signal(signal.SIGTERM, kill_kernel_process_group)
            set_parent_death_signal(parent_pid, signal.SIGKILL)
            local_kernel_pid = os.getpid()
            worker_pid = os.fork()
            if worker_pid == 0:
                os.close(ready_write)
                signal.signal(signal.SIGTERM, signal.SIG_DFL)
                set_parent_death_signal(local_kernel_pid, signal.SIGKILL)
                while True:
                    signal.pause()
            write_all(ready_write, f"{worker_pid}\n".encode("ascii"))
            os.close(ready_write)
            while True:
                signal.pause()
        except BaseException:  # noqa: BLE001 -- fork fixture reports by exit code
            traceback.print_exc()
        finally:
            os._exit(exit_code)
    os.close(ready_write)
    readable, _writable, _exceptional = select.select([ready_read], [], [], 5.0)
    if not readable:
        signal_isolated_process_group(kernel_pid, signal.SIGKILL)
        wait_for_child(kernel_pid, time.monotonic() + 5.0)
        os.close(ready_read)
        raise GateError("timeout/group fixture child never became ready")
    worker_payload = os.read(ready_read, 64)
    os.close(ready_read)
    try:
        worker_pid = int(worker_payload.strip())
    except ValueError as error:
        signal_isolated_process_group(kernel_pid, signal.SIGKILL)
        wait_for_child(kernel_pid, time.monotonic() + 5.0)
        raise GateError(
            "timeout/group fixture returned malformed worker PID"
        ) from error
    premature_exit = wait_for_child(kernel_pid, time.monotonic() + 0.2)
    if premature_exit is not None:
        raise GateError(
            f"timeout/group fixture exited before deadline: {premature_exit}"
        )
    signal_isolated_process_group(kernel_pid, signal.SIGTERM)
    timeout_exit = wait_for_child(kernel_pid, time.monotonic() + 5.0)
    if timeout_exit is None:
        signal_isolated_process_group(kernel_pid, signal.SIGKILL)
        timeout_exit = wait_for_child(kernel_pid, time.monotonic() + 5.0)
    if timeout_exit is None or timeout_exit == 0:
        raise GateError(f"isolated timeout fixture was not terminated: {timeout_exit}")
    worker_deadline = time.monotonic() + 5.0
    while process_is_running(worker_pid) and time.monotonic() < worker_deadline:
        time.sleep(0.05)
    if process_is_running(worker_pid):
        os.kill(worker_pid, signal.SIGKILL)
        raise GateError("isolated timeout left a live worker outside the group reap")
    return {
        "post_prctl_parent_pid_race_check_kills_child": True,
        "absolute_deadline_detects_live_child": True,
        "timeout_SIGTERM_terminates_isolated_group": True,
        "worker_parent_death_SIGKILL_prevents_orphan": True,
        "timed_out_child_reaped": True,
        "scientific_outcome_computed": False,
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
        "git_anchor": self_test_git_anchor(),
        "entry_capability": self_test_entry_capability(),
        "fresh_namespace_lock": self_test_fresh_namespace_lock(),
        "process_boundary": self_test_process_boundary(),
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
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--preregistration-commit")
    parser.add_argument("--expected-runner-sha256")
    parser.add_argument("--expected-preregistration-sha256")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--cache-dir", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        extras = (
            arguments.preregistration,
            arguments.preregistration_commit,
            arguments.expected_runner_sha256,
            arguments.expected_preregistration_sha256,
            arguments.output,
            arguments.cache_dir,
        )
        if any(value is not None for value in extras):
            raise GateError("--self-test refuses registered/internal arguments")
        print(json.dumps(self_test(), sort_keys=True))
        return
    if arguments.check_registration:
        registration = validate_registration(arguments)
        bindings = replay_static_bindings()
        print(
            json.dumps(
                {
                    "schema": "max11-g0081-registration-check-v1",
                    "result": "PASS",
                    "runner_sha256": registration.runner_sha256,
                    "preregistration_sha256": registration.sha256,
                    "git_anchor": registration.git_anchor.receipt(),
                    "bindings": bindings,
                    "output_unused": True,
                    "actual_quotient_or_rank_evaluated": False,
                },
                sort_keys=True,
            )
        )
        return
    report = public_run(arguments)
    assert isinstance(arguments.output, Path)
    print(
        json.dumps(
            {
                "schema": SCHEMA_RESULT,
                "result": report["scientific_payload"]["result"],
                "scientific_payload_sha256": report["scientific_payload_sha256"],
                "output": relative_path(arguments.output),
                "output_sha256": sha256_path(arguments.output),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
