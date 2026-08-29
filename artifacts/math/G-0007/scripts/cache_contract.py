#!/usr/bin/env python3
"""Run-isolated, provenance-keyed cache contract for G-0007."""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import pickle
import stat
from typing import Any

ROOT = pathlib.Path('/data/projects/relu-depth-frontier-research')
SCRIPTS = pathlib.Path(__file__).resolve().parent
SCHEMA = 'g0007-column-cache-v2'
TREE_SCHEMA = 'g0007-tree-representatives-v2'
INDEX_SCHEMA = 'g0007-cache-index-v1'
RESULT_SCHEMA = 'g0007-result-v1'
KERNEL = ROOT / 'literature/repos/max-relu-certificates/verify_certificate.py'
CERT8 = ROOT / 'literature/repos/max-relu-certificates/certificates/certificate_8_3.json'
CERT9 = ROOT / 'literature/repos/max-relu-certificates/certificates/certificate_9_4.json'
CERT10 = ROOT / 'literature/repos/max-relu-certificates/certificates/certificate_10_4.json'


def _validated_run_dir() -> pathlib.Path:
    raw = os.environ.get('G0007_RUN_DIR')
    if not raw:
        raise SystemExit(
            'G0007_RUN_DIR is required; create a fresh directory with '
            'mktemp -d /tmp/g0007-replay.XXXXXX and chmod 700'
        )
    path = pathlib.Path(raw)
    if not path.is_absolute() or path.is_symlink():
        raise SystemExit('G0007_RUN_DIR must be an absolute, non-symlink path')
    info = path.stat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid():
        raise SystemExit('G0007_RUN_DIR must be a directory owned by this user')
    if stat.S_IMODE(info.st_mode) != 0o700:
        raise SystemExit('G0007_RUN_DIR must have mode 0700')
    return path


RUN_DIR = _validated_run_dir()
TREE_MANIFEST = RUN_DIR / 'tree_reps_manifest.json'
CACHE_INDEX = RUN_DIR / 'cache_index.json'


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_path(path: pathlib.Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def secure_read(path: pathlib.Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0)
    descriptor = os.open(path, flags)
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise SystemExit(f'refusing non-regular or foreign-owned file: {path}')
        if stat.S_IMODE(info.st_mode) & 0o077:
            raise SystemExit(f'refusing group/world-accessible run file: {path}')
        with os.fdopen(descriptor, 'rb', closefd=False) as source:
            return source.read()
    finally:
        os.close(descriptor)


def atomic_write(path: pathlib.Path, data: bytes) -> None:
    temporary = path.with_name(f'.{path.name}.tmp.{os.getpid()}')
    flags = (
        os.O_WRONLY
        | os.O_CREAT
        | os.O_EXCL
        | getattr(os, 'O_NOFOLLOW', 0)
    )
    descriptor = os.open(temporary, flags, 0o600)
    try:
        with os.fdopen(descriptor, 'wb', closefd=False) as target:
            target.write(data)
            target.flush()
            os.fsync(descriptor)
        os.replace(temporary, path)
    finally:
        os.close(descriptor)
        if temporary.exists():
            temporary.unlink()


def atomic_json(path: pathlib.Path, value: Any) -> None:
    encoded = json.dumps(value, sort_keys=True, separators=(',', ':')).encode() + b'\n'
    atomic_write(path, encoded)


def _fingerprint(metadata: dict[str, Any]) -> str:
    encoded = json.dumps(metadata, sort_keys=True, separators=(',', ':')).encode()
    return hashlib.sha256(encoded).hexdigest()


def cache_path(kind: str, metadata: dict[str, Any]) -> pathlib.Path:
    return RUN_DIR / f'{kind}_{_fingerprint(metadata)}.pkl'


def _read_index(required: bool) -> dict[str, Any]:
    if not CACHE_INDEX.exists():
        if required:
            raise SystemExit(f'missing cache index: {CACHE_INDEX}')
        return {'schema': INDEX_SCHEMA, 'entries': {}}
    index = json.loads(secure_read(CACHE_INDEX))
    if index.get('schema') != INDEX_SCHEMA or not isinstance(index.get('entries'), dict):
        raise SystemExit(f'invalid cache index: {CACHE_INDEX}')
    return index


def save_columns(kind: str, metadata: dict[str, Any], columns: list[Any]) -> pathlib.Path:
    path = cache_path(kind, metadata)
    payload = pickle.dumps(
        {'metadata': metadata, 'columns': columns},
        protocol=5,
    )
    atomic_write(path, payload)
    index = _read_index(required=False)
    index['entries'][path.name] = {
        'sha256': sha256_bytes(payload),
        'bytes': len(payload),
        'metadata': metadata,
    }
    atomic_json(CACHE_INDEX, index)
    return path


def load_columns(
    kind: str,
    metadata: dict[str, Any],
    expected_count: int,
    *,
    required: bool,
) -> tuple[list[Any] | None, pathlib.Path]:
    path = cache_path(kind, metadata)
    if not path.exists():
        if required:
            raise SystemExit(
                f'missing run-scoped cache {path}; run its producer first'
            )
        return None, path
    index = _read_index(required=True)
    entry = index['entries'].get(path.name)
    if not isinstance(entry, dict) or entry.get('metadata') != metadata:
        raise SystemExit(f'cache-index provenance mismatch: {path}')
    payload_bytes = secure_read(path)
    if entry.get('sha256') != sha256_bytes(payload_bytes) or entry.get('bytes') != len(payload_bytes):
        raise SystemExit(f'cache byte-hash mismatch: {path}')
    payload = pickle.loads(payload_bytes)
    if not isinstance(payload, dict) or payload.get('metadata') != metadata:
        raise SystemExit(f'cache payload provenance mismatch: {path}')
    columns = payload.get('columns')
    if not isinstance(columns, list) or len(columns) != expected_count:
        raise SystemExit(
            f'cache schema/count mismatch: {path}; expected {expected_count} columns'
        )
    return columns, path


def n9_metadata() -> dict[str, Any]:
    return {
        'schema': SCHEMA,
        'kind': 'n9_published_columns',
        'n': 9,
        'expected_count': 337,
        'kernel_sha256': sha256_path(KERNEL),
        'certificate_sha256': sha256_path(CERT9),
        'producer_sha256': sha256_path(SCRIPTS / 'n9_mod_rank.py'),
        'contract_sha256': sha256_path(pathlib.Path(__file__).resolve()),
    }


def load_tree_manifest() -> dict[str, Any]:
    if not TREE_MANIFEST.exists():
        raise SystemExit(
            f'missing {TREE_MANIFEST}; run colored_tree_closure.py first'
        )
    manifest = json.loads(secure_read(TREE_MANIFEST))
    if manifest.get('schema') != TREE_SCHEMA:
        raise SystemExit(f'tree-representative schema mismatch: {TREE_MANIFEST}')
    expected_sources = {
        'certificate_8_3.json': sha256_path(CERT8),
        'certificate_9_4.json': sha256_path(CERT9),
        'certificate_10_4.json': sha256_path(CERT10),
    }
    if manifest.get('source_sha256') != expected_sources:
        raise SystemExit(f'tree-representative source mismatch: {TREE_MANIFEST}')
    generator = SCRIPTS / 'colored_tree_closure.py'
    if manifest.get('generator_sha256') != sha256_path(generator):
        raise SystemExit(f'tree-representative generator mismatch: {TREE_MANIFEST}')
    expected_outputs = {
        'max9_bridge': ('max9_bridge_reps.json', 710),
        'max9_all_trees': ('max9_all_tree_reps.json', 739),
        'max9_extra_trees': ('max9_extra_tree_reps.json', 29),
        'max11_bridge': ('max11_bridge_reps.json', 11072),
        'max11_all_trees': ('max11_all_tree_reps.json', 12459),
    }
    outputs = manifest.get('outputs', {})
    for name, (filename, expected_count) in expected_outputs.items():
        item = outputs.get(name, {})
        path = RUN_DIR / filename
        if item.get('filename') != filename or item.get('count') != expected_count:
            raise SystemExit(f'tree-representative metadata mismatch for {name}')
        data = secure_read(path)
        if item.get('sha256') != sha256_bytes(data) or item.get('bytes') != len(data):
            raise SystemExit(f'tree-representative byte-hash mismatch for {name}')
    return manifest


def bridge_metadata() -> dict[str, Any]:
    manifest = load_tree_manifest()
    bridge = manifest['outputs']['max9_bridge']
    return {
        'schema': SCHEMA,
        'kind': 'n9_bridge_columns',
        'n': 9,
        'expected_count': 710,
        'kernel_sha256': sha256_path(KERNEL),
        'representatives_sha256': bridge['sha256'],
        'representative_generator_sha256': manifest['generator_sha256'],
        'producer_sha256': sha256_path(SCRIPTS / 'n9_bridge_rank.py'),
        'contract_sha256': sha256_path(pathlib.Path(__file__).resolve()),
    }


def write_result(name: str, result: dict[str, Any]) -> pathlib.Path:
    producer = SCRIPTS / f'{name}.py'
    payload = {
        'schema': RESULT_SCHEMA,
        'name': name,
        'producer_sha256': sha256_path(producer),
        'cache_index_sha256': sha256_path(CACHE_INDEX) if CACHE_INDEX.exists() else None,
        'tree_manifest_sha256': sha256_path(TREE_MANIFEST) if TREE_MANIFEST.exists() else None,
        'result': result,
    }
    path = RUN_DIR / f'result_{name}.json'
    atomic_json(path, payload)
    return path
