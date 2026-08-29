#!/usr/bin/env python3
"""Freeze a textual attestation of one isolated G-0007 replay run."""

import json

from cache_contract import (
    CACHE_INDEX,
    CERT8,
    CERT9,
    CERT10,
    KERNEL,
    RESULT_SCHEMA,
    ROOT,
    RUN_DIR,
    SCRIPTS,
    TREE_MANIFEST,
    atomic_json,
    bridge_metadata,
    cache_path,
    load_columns,
    load_tree_manifest,
    n9_metadata,
    secure_read,
    sha256_bytes,
    sha256_path,
)

cache_index_bytes = secure_read(CACHE_INDEX)
tree_manifest_bytes = secure_read(TREE_MANIFEST)
cache_index = json.loads(cache_index_bytes)
tree_manifest = json.loads(tree_manifest_bytes)
cache_index_sha256 = sha256_bytes(cache_index_bytes)
tree_manifest_sha256 = sha256_bytes(tree_manifest_bytes)

# Revalidate the manifests/caches against source and producer bytes that
# exist at attestation time, not merely against self-reported metadata.
load_tree_manifest()
n9_meta = n9_metadata()
bridge_meta = bridge_metadata()
load_columns('n9_columns', n9_meta, 337, required=True)
load_columns('n9_bridge_columns', bridge_meta, 710, required=True)
expected_cache_names = {
    cache_path('n9_columns', n9_meta).name,
    cache_path('n9_bridge_columns', bridge_meta).name,
}
if set(cache_index.get('entries', {})) != expected_cache_names:
    raise SystemExit('cache index does not contain exactly the two expected caches')

results = {}
for path in sorted(RUN_DIR.glob('result_*.json')):
    payload = json.loads(secure_read(path))
    if payload.get('schema') != RESULT_SCHEMA:
        raise SystemExit(f'invalid result schema: {path}')
    producer = SCRIPTS / f"{payload['name']}.py"
    if payload.get('producer_sha256') != sha256_path(producer):
        raise SystemExit(f'result producer mismatch: {path}')
    if payload.get('cache_index_sha256') != cache_index_sha256:
        raise SystemExit(f'result cache-index mismatch: {path}')
    if payload.get('tree_manifest_sha256') != tree_manifest_sha256:
        raise SystemExit(f'result tree-manifest mismatch: {path}')
    results[payload['name']] = payload

required = {
    'n9_alltree_rank',
    'n9_bridge_rank_exact',
    'n9_cached_verify',
    'n9_hybrid_rank',
    'n9_hybrid_solve',
    'n9_support_uniqueness',
}
if set(results) != required:
    raise SystemExit(f'missing or extra result records: {sorted(set(results)^required)}')

generated = {}
for filename in ('n9_hybrid_solution.json', 'n9_hybrid_certificate.json'):
    data = secure_read(RUN_DIR / filename)
    frozen = ROOT / 'artifacts/math/G-0007/data' / filename
    digest = sha256_bytes(data)
    if digest != sha256_path(frozen) or data != frozen.read_bytes():
        raise SystemExit(f'generated output differs from frozen data: {filename}')
    generated[filename] = {
        'sha256': digest,
        'bytes': len(data),
        'frozen_sha256': sha256_path(frozen),
        'byte_equal_to_frozen': True,
    }

solve_result = results['n9_hybrid_solve']['result']
if solve_result.get('solution_sha256') != generated['n9_hybrid_solution.json']['sha256']:
    raise SystemExit('solution result hash does not match generated output')
if solve_result.get('certificate_sha256') != generated['n9_hybrid_certificate.json']['sha256']:
    raise SystemExit('certificate result hash does not match generated output')

attestation = {
    'schema': 'g0007-replay-attestation-v1',
    'repository': str(ROOT),
    'sources': {
        'verify_certificate.py': sha256_path(KERNEL),
        'certificate_8_3.json': sha256_path(CERT8),
        'certificate_9_4.json': sha256_path(CERT9),
        'certificate_10_4.json': sha256_path(CERT10),
    },
    'scripts': {
        path.name: sha256_path(path)
        for path in sorted(SCRIPTS.glob('*.py'))
    },
    'tree_manifest': {
        'sha256': tree_manifest_sha256,
        'payload': tree_manifest,
    },
    'cache_index': {
        'sha256': cache_index_sha256,
        'payload': cache_index,
    },
    'results': results,
    'generated': generated,
}
path = RUN_DIR / 'replay_attestation.json'
atomic_json(path, attestation)
print(json.dumps(attestation, indent=2, sort_keys=True))
print('attestation_sha256', sha256_path(path))
