#!/usr/bin/env python3
"""Exact one-sided rank gate for the genuine mass-five single-edge lifts.

The natural MAX10-to-MAX11 single-edge construction has 13,419 registered
orbit representatives, but 1,877 same-component representatives contain the
same appended edge in both branches.  After exact multiset cancellation those
are signed-mass-four atoms and are identically zero on degree-five-only hinge
rows.  This gate therefore freezes the 11,542 genuine signed-mass-five
representatives: 7,927 same-component classes and all 3,615 cross-component
classes.

Each exact semantic column is streamed into a deterministic CountSketch of
the complete degree-five-only row space.  If the sketch has full column rank
modulo one prime, left multiplication cannot have increased rank, so the
complete 557,964-by-11,542 integer matrix has full column rank modulo that
prime and hence over Q and R.  A deficient sketch is explicitly inconclusive;
it is not a kernel certificate and requires complete-row kernel replay.

The default execution modes are self-test, preflight, and a bounded smoke
test.  The multi-hour subject run requires the explicit ``--full`` flag.
"""

from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import gzip
import hashlib
import importlib.util
import json
from math import factorial
import multiprocessing as mp
import os
from pathlib import Path
import platform
import resource
import sys
import tempfile
import time
from types import ModuleType
from typing import Any, Iterable, Sequence

import numpy as np


N = 11
PRIME = 1_000_003
SKETCH_SEED = "max11-g0068-genuine-mass5-single-edge-v1"
EXPECTED_DEFAULT_ROW_MAP_CONTRACT_SHA256 = (
    "91b2d66c8c9893779f0fe3e440b2a1d48700b957fceea264a03bc340c2dbdc9c"
)
EXPECTED_D4_ROWS = 99_858
EXPECTED_D5_ROWS = 657_822
EXPECTED_D5_ONLY_ROWS = 557_964
EXPECTED_D5_ONLY_SHA256 = (
    "657f53d4eccbf3ef7cd97b14baef4f6d2e9a7629aee9181d2cc8956bd2f296f1"
)
EXPECTED_D5_ONLY_FIRST = (0, 0, 0, 0, 0, 0, 0, 0, 1, -5, 4)
EXPECTED_D5_ONLY_LAST = (4, 0, 0, 0, 0, 0, 0, 0, 0, -5, 1)

EXPECTED_REGISTERED_COLUMNS = 13_419
EXPECTED_SAME_COLUMNS = 9_804
EXPECTED_CROSS_COLUMNS = 3_615
EXPECTED_SAME_MASS5_COLUMNS = 7_927
EXPECTED_SAME_MASS4_COLUMNS = 1_877
EXPECTED_GENUINE_MASS5_COLUMNS = 11_542

EXPECTED_SAME_REPRESENTATIVES_SHA256 = (
    "a419298cb7cd066b5bb1e96b787f143f657b4e1240fb613bcca365cfcdd7df00"
)
EXPECTED_CROSS_REPRESENTATIVES_SHA256 = (
    "8393111b212b1e530bc863f326ad3f82e2264340a51e821cdf0f911c2757f038"
)
EXPECTED_REGISTERED_REPRESENTATIVES_SHA256 = (
    "0db1701e29d1fc1e3e9c5bc03e036e3a94141b600379ce1bb2e00b0554a525de"
)
EXPECTED_GENUINE_DESCRIPTORS_SHA256 = (
    "715badf62ae08198e494e991f3b13884d64ae305bc1d8b61963c2ab6951d28db"
)
EXPECTED_GENUINE_INDICES_SHA256 = (
    "c4079290a2c8f66c25a7c40e0cbca9e9496a3d5e6c6290a5af455f5cc5626a9e"
)
EXPECTED_LOWER_DESCRIPTORS_SHA256 = (
    "9e54063c1e3eb09d79e858c8ae76bd403db12e61c729e802d534176700b122d9"
)
EXPECTED_LOWER_INDICES_SHA256 = (
    "0fa5f41b4d0e1fbe0f6f6365ea7d6daae7151b7a49148bc6536c621d123069c9"
)
ZERO_HIGH_SAME_WITNESSES: dict[int, dict[str, object]] = {
    161: {
        "pair": [
            [[1, 2], [1, 3], [1, 4], [1, 5], [6, 11]],
            [[1, 6], [2, 7], [6, 8], [9, 10], [2, 11]],
        ],
        "boolean_charge": 0,
    },
    3_600: {
        "pair": [
            [[1, 2], [1, 3], [1, 4], [5, 6], [7, 11]],
            [[1, 7], [1, 8], [7, 9], [9, 10], [2, 11]],
        ],
        "boolean_charge": 0,
    },
    7_172: {
        "pair": [
            [[1, 2], [1, 3], [2, 4], [5, 6], [7, 11]],
            [[1, 5], [1, 7], [8, 9], [8, 10], [3, 11]],
        ],
        "boolean_charge": -12,
    },
}
POST_CENSUS_CHARGED_TREE_EXTENSION_COLUMNS = (
    13_831,
    13_921,
    14_293,
    14_295,
    14_300,
    14_305,
    14_444,
    14_558,
    14_559,
    14_580,
    14_881,
    15_160,
    15_163,
    15_165,
    15_181,
    15_609,
    15_782,
    16_031,
    16_247,
    16_656,
    16_666,
    17_140,
    17_362,
    17_384,
    17_581,
    18_558,
    19_321,
    19_418,
    21_886,
    21_901,
    21_927,
    22_161,
)
EXPECTED_POST_CENSUS_EXTENSION_SHA256 = (
    "b3c64d69bb69efbde44b8d903ecbfc94f6def25525972592e1cf3cc2efbf779c"
)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0049_SCRIPT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
G0054_SCRIPT = ROOT / "artifacts/math/G-0054/s0_union_rank_gate.py"
G0060_SCRIPT = ROOT / "artifacts/math/G-0060/boolean_mobius_ancestry.py"
G0060_REPORT = ROOT / "artifacts/math/G-0060/report_v1.json"
CERTIFICATE = ROOT / (
    "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
)
SAME_CLASSES = ROOT / "artifacts/math/G-0006/isomorphism_classes_v2.json"
CROSS_CLASSES = ROOT / "artifacts/math/G-0009/cross_component_classes.json"
SCRIPT_PATH = Path(__file__).resolve()
DEFAULT_SMOKE_OUTPUT = HERE / "single_edge_degree5_kernel_gate_smoke_v1.json.gz"
DEFAULT_FULL_OUTPUT = HERE / "single_edge_degree5_kernel_gate_v1.json.gz"
DEFAULT_CACHE_DIR = HERE / "single_edge_degree5_sketch_cache_v1"
SHARD_SCHEMA = "max11-g0068-resumable-sketch-shard-v1"
CACHE_MANIFEST_SCHEMA = "max11-g0068-resumable-sketch-cache-manifest-v1"

EXPECTED_INPUT_HASHES = {
    "g0049_semantics_script_sha256": (
        "0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04"
    ),
    "g0054_rank_script_sha256": (
        "cf8b4527863a02b97e169c4473c728d6f8f5c14bc37e6351e3b7e42ac11a6fe2"
    ),
    "max10_certificate_sha256": (
        "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
    ),
    "same_classes_sha256": (
        "3f24edd0b8928256e90fe41fbafd846b693efd37285065da907a1ffdf9561f48"
    ),
    "cross_classes_sha256": (
        "c1a6c84ec189690ec640733283da3e566dcc9ef3c312dafbf243f4727eb88878"
    ),
    "g0060_boolean_charge_script_sha256": (
        "da249cad23877d78be4de93ebdc49f771033e9084b1b7168893f35bbeb8c6e53"
    ),
    "g0060_boolean_charge_report_sha256": (
        "2bf930f9bcc77c6da27199e5e9374fd0a0d31844222d9afff43c65b50b58513a"
    ),
}
INPUT_PATHS = {
    "g0049_semantics_script_sha256": G0049_SCRIPT,
    "g0054_rank_script_sha256": G0054_SCRIPT,
    "max10_certificate_sha256": CERTIFICATE,
    "same_classes_sha256": SAME_CLASSES,
    "cross_classes_sha256": CROSS_CLASSES,
    "g0060_boolean_charge_script_sha256": G0060_SCRIPT,
    "g0060_boolean_charge_report_sha256": G0060_REPORT,
}

SCHEMA = "max11-g0068-genuine-single-edge-degree5-kernel-gate-v1"
SMOKE_RESULT = "SMOKE_PASS_NO_THEOREM"
FULL_RANK_RESULT = (
    "NONZERO_HIGH_SKETCH_FULL_RANK_CERTIFIES_KERNEL_IS_EXPLICIT_ZERO_HIGH_BLOCK"
)
DEFICIENT_RESULT = (
    "NONZERO_HIGH_SKETCH_DEFICIENT_INCONCLUSIVE_PENDING_COMPLETE_ROW_KERNEL_REPLAY"
)
THEOREM_BOUNDARY = (
    "After explicit zero-high columns are removed, full sketch column rank "
    "certifies full degree5-only matrix column rank for the remaining block. "
    "Sketch deficiency is inconclusive pending complete-row kernel replay."
)

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class GateError(RuntimeError):
    """Fail-closed binding, semantic, or resource error."""


@dataclass(frozen=True)
class SubjectColumn:
    subject_column: int
    union_column: int
    family: str
    class_index: int
    pair: Pair
    signed_mass: int


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"bound input is not a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def input_bindings() -> dict[str, str]:
    observed = {label: sha256_path(path) for label, path in INPUT_PATHS.items()}
    if observed != EXPECTED_INPUT_HASHES:
        raise GateError(
            f"upstream input drift: observed={observed}, expected={EXPECTED_INPUT_HASHES}"
        )
    return observed


def load_bound_module(name: str, path: Path, expected_hash: str) -> ModuleType:
    if sha256_path(path) != expected_hash:
        raise GateError(f"bound module drift: {path}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_semantics(name: str = "g0068_bound_g0049") -> ModuleType:
    return load_bound_module(
        name, G0049_SCRIPT, EXPECTED_INPUT_HASHES["g0049_semantics_script_sha256"]
    )


def load_rank_tools(name: str = "g0068_bound_g0054") -> ModuleType:
    return load_bound_module(
        name, G0054_SCRIPT, EXPECTED_INPUT_HASHES["g0054_rank_script_sha256"]
    )


def load_charge_tools(name: str = "g0068_bound_g0060") -> ModuleType:
    return load_bound_module(
        name,
        G0060_SCRIPT,
        EXPECTED_INPUT_HASHES["g0060_boolean_charge_script_sha256"],
    )


def cancelled_signed_mass(pair: Pair) -> tuple[int, int]:
    left = Counter(pair[0])
    right = Counter(pair[1])
    common = left & right
    cancelled = sum(common.values())
    return len(pair[0]) - cancelled, len(pair[1]) - cancelled


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[int(u), int(v)] for u, v in side] for side in pair]


def family_descriptor(
    family: str, class_index: int, union_column: int, pair: Pair
) -> dict[str, object]:
    mass = cancelled_signed_mass(pair)
    return {
        "family": family,
        "class_index": class_index,
        "union_column": union_column,
        "pair": serialize_pair(pair),
        "signed_mass": list(mass),
    }


def load_subject(semantics: ModuleType) -> tuple[list[SubjectColumn], dict[str, Any]]:
    same, cross, reconstruction = semantics.build_raw_lift_families()
    if len(same) != EXPECTED_SAME_COLUMNS or len(cross) != EXPECTED_CROSS_COLUMNS:
        raise GateError("registered-family census drift")
    if semantics.pair_list_sha256(same) != EXPECTED_SAME_REPRESENTATIVES_SHA256:
        raise GateError("same representative ordering drift")
    if semantics.pair_list_sha256(cross) != EXPECTED_CROSS_REPRESENTATIVES_SHA256:
        raise GateError("cross representative ordering drift")
    if (
        semantics.pair_list_sha256(same + cross)
        != EXPECTED_REGISTERED_REPRESENTATIVES_SHA256
    ):
        raise GateError("registered representative ordering drift")

    genuine_descriptors: list[dict[str, object]] = []
    lower_descriptors: list[dict[str, object]] = []
    genuine: list[SubjectColumn] = []
    same_histogram: Counter[tuple[int, int]] = Counter()
    cross_histogram: Counter[tuple[int, int]] = Counter()
    for family, pairs, offset, histogram in (
        ("same", same, 0, same_histogram),
        ("cross", cross, EXPECTED_SAME_COLUMNS, cross_histogram),
    ):
        for class_index, pair in enumerate(pairs):
            union_column = offset + class_index
            mass = cancelled_signed_mass(pair)
            histogram[mass] += 1
            descriptor = family_descriptor(family, class_index, union_column, pair)
            if mass == (5, 5):
                subject_column = len(genuine)
                genuine.append(
                    SubjectColumn(
                        subject_column=subject_column,
                        union_column=union_column,
                        family=family,
                        class_index=class_index,
                        pair=pair,
                        signed_mass=5,
                    )
                )
                genuine_descriptors.append(descriptor)
            elif family == "same" and mass == (4, 4):
                lower_descriptors.append(descriptor)
            else:
                raise GateError(
                    f"unexpected registered signed mass: {family}/{class_index}/{mass}"
                )

    expected_same_histogram = {(5, 5): 7_927, (4, 4): 1_877}
    expected_cross_histogram = {(5, 5): 3_615}
    if dict(same_histogram) != expected_same_histogram:
        raise GateError(f"same signed-mass census drift: {same_histogram}")
    if dict(cross_histogram) != expected_cross_histogram:
        raise GateError(f"cross signed-mass census drift: {cross_histogram}")
    if len(genuine) != EXPECTED_GENUINE_MASS5_COLUMNS:
        raise GateError(f"genuine mass-five census drift: {len(genuine)}")
    if len(lower_descriptors) != EXPECTED_SAME_MASS4_COLUMNS:
        raise GateError(f"structural mass-four census drift: {len(lower_descriptors)}")

    genuine_indices = [int(value["union_column"]) for value in genuine_descriptors]
    lower_indices = [int(value["union_column"]) for value in lower_descriptors]
    observed_hashes = {
        "genuine_descriptors_sha256": canonical_sha256(genuine_descriptors),
        "genuine_union_indices_sha256": canonical_sha256(genuine_indices),
        "lower_descriptors_sha256": canonical_sha256(lower_descriptors),
        "lower_union_indices_sha256": canonical_sha256(lower_indices),
    }
    expected_hashes = {
        "genuine_descriptors_sha256": EXPECTED_GENUINE_DESCRIPTORS_SHA256,
        "genuine_union_indices_sha256": EXPECTED_GENUINE_INDICES_SHA256,
        "lower_descriptors_sha256": EXPECTED_LOWER_DESCRIPTORS_SHA256,
        "lower_union_indices_sha256": EXPECTED_LOWER_INDICES_SHA256,
    }
    if observed_hashes != expected_hashes:
        raise GateError(
            f"mass-partition descriptor drift: {observed_hashes}/{expected_hashes}"
        )
    if genuine[0].union_column != 1 or genuine[-1].union_column != 13_418:
        raise GateError("genuine family endpoint drift")
    if lower_indices[0] != 0 or lower_indices[-1] != 9_802:
        raise GateError("structural lower-family endpoint drift")
    for class_index, witness in ZERO_HIGH_SAME_WITNESSES.items():
        if serialize_pair(same[class_index]) != witness["pair"]:
            raise GateError(f"zero-high witness pair drift at same class {class_index}")
        if cancelled_signed_mass(same[class_index]) != (5, 5):
            raise GateError(f"zero-high witness lost genuine mass five: {class_index}")

    controls = {
        "registered_columns": len(same) + len(cross),
        "same_columns": len(same),
        "cross_columns": len(cross),
        "same_signed_mass_histogram": {"4": 1_877, "5": 7_927},
        "cross_signed_mass_histogram": {"5": 3_615},
        "genuine_mass5_columns": len(genuine),
        "structural_mass4_columns": len(lower_descriptors),
        "genuine_first_union_column": genuine[0].union_column,
        "genuine_last_union_column": genuine[-1].union_column,
        "structural_mass4_first_union_column": lower_indices[0],
        "structural_mass4_last_union_column": lower_indices[-1],
        **observed_hashes,
        "upstream_reconstruction": reconstruction,
    }
    return genuine, controls


def exact_boolean_charge(charge_tools: ModuleType, pair: Pair) -> int:
    zero_based_pair = tuple(
        tuple((u - 1, v - 1) for u, v in side) for side in pair
    )
    value = charge_tools.boolean_mobius_charge(
        N, lambda point: charge_tools.pair_atom_value(zero_based_pair, point)
    )
    if value.denominator != 1:
        raise GateError(f"integer pair atom acquired fractional Boolean charge: {value}")
    return int(value)


def zero_high_witness_replay(
    semantics: ModuleType, charge_tools: ModuleType
) -> list[dict[str, object]]:
    same, _, _ = semantics.build_raw_lift_families()
    results = []
    for class_index, expected in ZERO_HIGH_SAME_WITNESSES.items():
        pair = same[class_index]
        column = semantics.exact_semantic_column(pair, N)
        high = degree5_only_fingerprint(column.hinges)
        if high:
            raise GateError(
                f"hostile genuine-mass-five witness has high-degree support: {class_index}"
            )
        charge = exact_boolean_charge(charge_tools, pair)
        if charge != int(expected["boolean_charge"]):
            raise GateError(
                f"Boolean charge drift at same class {class_index}: {charge}"
            )
        lower_histogram = Counter(positive_mass(direction) for direction in column.hinges)
        if any(degree >= 5 for degree in lower_histogram):
            raise GateError(f"zero-high witness leaked a degree-five hinge: {class_index}")
        results.append(
            {
                "family": "same",
                "class_index": class_index,
                "union_column": class_index,
                "pair": serialize_pair(pair),
                "signed_mass": 5,
                "degree5_only_nonzero_hinges": 0,
                "lower_degree_nonzero_hinges": len(column.hinges),
                "lower_degree_hinge_count_by_positive_mass": {
                    str(key): value for key, value in sorted(lower_histogram.items())
                },
                "linear_nonzero_coordinates": sum(bool(value) for value in column.linear),
                "linear_l1": sum(abs(value) for value in column.linear),
                "exact_boolean_mobius_charge": charge,
                "full_lower_degree_normal_form_sha256": (
                    semantics.semantic_column_digest(column)
                ),
            }
        )
    return results


def positive_mass(direction: Direction) -> int:
    if sum(direction) != 0:
        raise GateError(f"hinge direction is not zero-sum: {direction}")
    return sum(value for value in direction if value > 0)


def degree_only_fingerprint(
    hinges: dict[Direction, int], degree: int
) -> dict[Direction, int]:
    result: dict[Direction, int] = {}
    for direction, coefficient in hinges.items():
        mass = positive_mass(direction)
        if mass > degree:
            raise GateError(
                f"degree-{degree} atom emitted direction of positive mass {mass}"
            )
        if mass == degree and int(coefficient):
            result[direction] = int(coefficient)
    return result


def degree5_only_fingerprint(hinges: dict[Direction, int]) -> dict[Direction, int]:
    return degree_only_fingerprint(hinges, 5)


def direction_token(direction: Direction) -> bytes:
    return ",".join(map(str, direction)).encode("ascii")


def sketch_coordinate(
    direction: Direction, buckets: int, prime: int, seed: str
) -> tuple[int, int]:
    if buckets < 1 or prime < 3:
        raise GateError("invalid sketch modulus or bucket count")
    payload = (
        b"max11-g0068-countsketch-v1|"
        + seed.encode("ascii")
        + b"|"
        + direction_token(direction)
    )
    hashed = hashlib.sha256(payload).digest()
    bucket = int.from_bytes(hashed[:8], "little") % buckets
    weight = int.from_bytes(hashed[8:16], "little") % (prime - 1) + 1
    return bucket, weight


def sketch_map_contract(buckets: int, prime: int, seed: str) -> dict[str, object]:
    payload = {
        "schema": "max11-g0068-direction-keyed-countsketch-map-v1",
        "complete_row_universe": "D5 set-minus D4",
        "complete_row_count": EXPECTED_D5_ONLY_ROWS,
        "complete_row_canonical_json_sha256": EXPECTED_D5_ONLY_SHA256,
        "prime": prime,
        "buckets": buckets,
        "seed": seed,
        "map_definition": (
            "For primitive direction d, SHA256(ASCII('max11-g0068-countsketch-v1|' "
            "+ seed + '|' + comma-separated d)); bucket=little_u64(bytes[0:8]) "
            "mod buckets; weight=1+(little_u64(bytes[8:16]) mod (prime-1))."
        ),
        "extension_rule": (
            "An extension cache is immutable and separate from the natural-basis cache. "
            "It is column-compatible exactly when it binds this complete contract hash; "
            "a consumer concatenates natural then extension columns without rewriting "
            "either source manifest."
        ),
    }
    return {**payload, "contract_sha256": canonical_sha256(payload)}


def post_census_extension_contract() -> dict[str, object]:
    columns = list(POST_CENSUS_CHARGED_TREE_EXTENSION_COLUMNS)
    observed_hash = canonical_sha256(columns)
    if len(columns) != 32 or observed_hash != EXPECTED_POST_CENSUS_EXTENSION_SHA256:
        raise GateError("post-census charged-tree extension descriptor drift")
    if len(set(columns)) != len(columns) or columns != sorted(columns):
        raise GateError("post-census extension descriptors are duplicate or unordered")
    return {
        "status": "POST_CENSUS_EXTENSION_NOT_PART_OF_G0068_SMOKE_OR_BASE_RANK",
        "combined_union_columns": columns,
        "column_count": len(columns),
        "ordered_columns_sha256": observed_hash,
        "append_position": "after the completed natural nonzero-high census",
        "compatibility_requirement": (
            "extension cache must bind the identical row-map contract hash"
        ),
    }


def sketch_fingerprint(
    fingerprint: dict[Direction, int], buckets: int, prime: int, seed: str
) -> np.ndarray:
    vector = np.zeros(buckets, dtype=np.uint32)
    for direction in sorted(fingerprint):
        coefficient = int(fingerprint[direction])
        bucket, weight = sketch_coordinate(direction, buckets, prime, seed)
        vector[bucket] = (int(vector[bucket]) + coefficient * weight) % prime
    return vector


def hash_modular_matrix(matrix: np.ndarray, prime: int, namespace: str) -> str:
    array = np.ascontiguousarray(np.remainder(matrix, prime), dtype="<u4")
    digest = hashlib.sha256()
    digest.update(
        (
            f"{namespace};uint32-little-row-major;"
            f"shape={matrix.shape[0]}x{matrix.shape[1]};prime={prime}\n"
        ).encode(
            "ascii"
        )
    )
    digest.update(array.tobytes(order="C"))
    return digest.hexdigest()


def direct_sketch_oracle(
    fingerprints: Sequence[dict[Direction, int]],
    buckets: int,
    prime: int,
    seed: str,
) -> dict[str, object]:
    rows = tuple(sorted({row for column in fingerprints for row in column}))
    direct = np.zeros((buckets, len(fingerprints)), dtype=np.uint32)
    for direction in rows:
        payload = (
            b"max11-g0068-countsketch-v1|"
            + seed.encode("ascii")
            + b"|"
            + ",".join(str(value) for value in direction).encode("ascii")
        )
        hashed = hashlib.sha256(payload).digest()
        bucket = int.from_bytes(hashed[:8], "little") % buckets
        weight = int.from_bytes(hashed[8:16], "little") % (prime - 1) + 1
        for column_index, fingerprint in enumerate(fingerprints):
            direct[bucket, column_index] = (
                int(direct[bucket, column_index])
                + int(fingerprint.get(direction, 0)) * weight
            ) % prime

    streamed = np.column_stack(
        [sketch_fingerprint(value, buckets, prime, seed) for value in fingerprints]
    )
    if not np.array_equal(direct, streamed):
        mismatch = np.argwhere(direct != streamed)[0]
        raise GateError(f"direct/streamed sketch mismatch at {tuple(map(int, mismatch))}")
    mutant_fingerprints = [dict(value) for value in fingerprints]
    if rows:
        first = rows[0]
        mutant_fingerprints[0][first] = mutant_fingerprints[0].get(first, 0) + 1
        mutant = np.column_stack(
            [
                sketch_fingerprint(value, buckets, prime, seed)
                for value in mutant_fingerprints
            ]
        )
        if np.array_equal(mutant, streamed):
            raise GateError("coefficient-plus-one sketch mutant escaped")
    return {
        "complete_nonzero_row_union": len(rows),
        "columns": len(fingerprints),
        "buckets": buckets,
        "prime": prime,
        "direct_equals_streamed": True,
        "coefficient_plus_one_mutant_rejected": bool(rows),
        "sketch_matrix_sha256": hash_modular_matrix(
            streamed, prime, "max11-g0068-direct-streamed-oracle-v1"
        ),
    }


def degree5_universe_certificate(rank_tools: ModuleType) -> dict[str, object]:
    started = time.perf_counter()
    degree4 = rank_tools.direction_universe(N, 4)
    degree5 = rank_tools.direction_universe(N, 5)
    degree4_set = set(degree4)
    degree5_set = set(degree5)
    if len(degree4) != EXPECTED_D4_ROWS or len(degree5) != EXPECTED_D5_ROWS:
        raise GateError(f"degree row census drift: {len(degree4)}/{len(degree5)}")
    if not degree4_set.issubset(degree5_set):
        raise GateError("degree-four direction universe is not a subset of degree five")
    degree5_only = tuple(direction for direction in degree5 if direction not in degree4_set)
    if len(degree5_only) != EXPECTED_D5_ONLY_ROWS:
        raise GateError(f"degree-five-only census drift: {len(degree5_only)}")
    if len(EXPECTED_D5_ONLY_FIRST) != N or len(EXPECTED_D5_ONLY_LAST) != N:
        raise GateError("frozen degree-five-only endpoint has wrong dimension")
    if degree5_only[0] != EXPECTED_D5_ONLY_FIRST:
        raise GateError(f"degree-five-only first row drift: {degree5_only[0]}")
    if degree5_only[-1] != EXPECTED_D5_ONLY_LAST:
        raise GateError(f"degree-five-only last row drift: {degree5_only[-1]}")
    if any(positive_mass(direction) != 5 for direction in degree5_only):
        raise GateError("degree-five-only universe contains a non-mass-five direction")

    digest = hashlib.sha256()
    digest.update(b"[")
    for index, direction in enumerate(degree5_only):
        if index:
            digest.update(b",")
        digest.update(json.dumps(list(direction), separators=(",", ":")).encode("ascii"))
    digest.update(b"]\n")
    universe_hash = digest.hexdigest()
    if universe_hash != EXPECTED_D5_ONLY_SHA256:
        raise GateError(f"degree-five-only universe hash drift: {universe_hash}")
    return {
        "degree4_rows": len(degree4),
        "degree5_rows": len(degree5),
        "degree4_is_subset_of_degree5": True,
        "degree5_only_rows": len(degree5_only),
        "degree5_only_definition": (
            "primitive zero-sum directions with positive-coordinate mass exactly five; "
            "equivalently D5 set-minus D4"
        ),
        "degree5_only_lex_first": list(degree5_only[0]),
        "degree5_only_lex_last": list(degree5_only[-1]),
        "degree5_only_canonical_json_sha256": universe_hash,
        "seconds": time.perf_counter() - started,
    }


_WORKER_SEMANTICS: ModuleType | None = None


def worker_initialize() -> None:
    global _WORKER_SEMANTICS
    _WORKER_SEMANTICS = load_semantics(
        f"g0068_worker_g0049_{os.getpid()}_{time.time_ns()}"
    )


def compute_sketch_column(
    task: tuple[int, Pair, int, int, str]
) -> tuple[int, np.ndarray, dict[str, object]]:
    subject_column, pair, buckets, prime, seed = task
    global _WORKER_SEMANTICS
    if _WORKER_SEMANTICS is None:
        worker_initialize()
    assert _WORKER_SEMANTICS is not None
    started = time.perf_counter()
    column = _WORKER_SEMANTICS.exact_semantic_column(pair, N)
    fingerprint = degree5_only_fingerprint(column.hinges)
    vector = sketch_fingerprint(fingerprint, buckets, prime, seed)
    metadata = {
        "subject_column": subject_column,
        "raw_direction_count": column.raw_direction_count,
        "all_primitive_hinges": len(column.hinges),
        "degree5_only_nonzero_hinges": len(fingerprint),
        "degree5_only_coefficient_l1": sum(abs(value) for value in fingerprint.values()),
        "semantic_column_sha256": _WORKER_SEMANTICS.semantic_column_digest(column),
        "sketch_column_sha256": hashlib.sha256(vector.astype("<u4").tobytes()).hexdigest(),
        "seconds": time.perf_counter() - started,
    }
    if not fingerprint:
        metadata["zero_high_full_lower_normal_form"] = {
            "linear": [int(value) for value in column.linear],
            "hinges": [
                {
                    "direction": list(direction),
                    "coefficient": int(column.hinges[direction]),
                }
                for direction in sorted(column.hinges)
            ],
        }
    return subject_column, vector, metadata


def generate_streamed_sketch(
    subject: Sequence[SubjectColumn],
    buckets: int,
    prime: int,
    seed: str,
    workers: int,
    max_tasks_per_child: int,
    progress_every: int,
) -> tuple[np.ndarray, list[dict[str, object]]]:
    if not subject:
        raise GateError("empty sketch subject")
    sketch = np.zeros((buckets, len(subject)), dtype=np.uint32)
    metadata: list[dict[str, object] | None] = [None] * len(subject)
    tasks = [
        (column.subject_column, column.pair, buckets, prime, seed)
        for column in subject
    ]
    if [value[0] for value in tasks] != list(range(len(subject))):
        raise GateError("subject columns are not contiguous in execution order")

    if workers == 1:
        worker_initialize()
        results: Iterable[tuple[int, np.ndarray, dict[str, object]]] = map(
            compute_sketch_column, tasks
        )
        executor = None
    else:
        context = mp.get_context("spawn")
        executor = ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=worker_initialize,
            max_tasks_per_child=max_tasks_per_child,
        )
        results = executor.map(compute_sketch_column, tasks, chunksize=1)
    try:
        for completed, (index, vector, record) in enumerate(results, start=1):
            if not (0 <= index < len(subject)) or metadata[index] is not None:
                raise GateError(f"duplicate or invalid semantic result index: {index}")
            if vector.shape != (buckets,) or vector.dtype != np.uint32:
                raise GateError(f"semantic worker vector contract drift at {index}")
            sketch[:, index] = vector
            metadata[index] = record
            if progress_every and completed % progress_every == 0:
                print(
                    f"G0068_PROGRESS completed={completed}/{len(subject)}",
                    flush=True,
                )
    finally:
        if executor is not None:
            executor.shutdown(wait=True, cancel_futures=True)
    if any(value is None for value in metadata):
        raise GateError("semantic result stream is incomplete")
    return sketch, [value for value in metadata if value is not None]


def tiny_direct_vs_streamed_oracle(semantics: ModuleType) -> dict[str, object]:
    pairs: list[Pair] = [
        (((1, 2), (1, 3)), ((1, 4), (2, 3))),
        (((1, 2), (1, 3)), ((1, 4), (2, 4))),
        (((1, 2), (1, 3)), ((2, 3), (3, 4))),
    ]
    fingerprints = []
    for pair in pairs:
        if cancelled_signed_mass(pair) != (2, 2):
            raise GateError("tiny oracle pair is not signed mass two")
        dp = semantics.exact_semantic_column(pair, 4)
        brute = semantics.brute_direction_histogram(pair, 4)
        if semantics.direction_histogram(pair, 4) != brute:
            raise GateError("tiny subset-DP/literal permutation oracle failed")
        fingerprints.append(degree_only_fingerprint(dp.hinges, 2))
    oracle = direct_sketch_oracle(
        fingerprints, buckets=8, prime=101, seed="g0068-tiny-oracle"
    )
    if oracle["complete_nonzero_row_union"] == 0:
        raise GateError("tiny direct/streamed oracle has empty support")
    return oracle


def self_test() -> dict[str, object]:
    bindings = input_bindings()
    semantics = load_semantics("g0068_self_test_g0049")
    rank_tools = load_rank_tools("g0068_self_test_g0054")
    charge_tools = load_charge_tools("g0068_self_test_g0060")
    subject, census = load_subject(semantics)
    if census["registered_columns"] != EXPECTED_REGISTERED_COLUMNS:
        raise GateError("registered subject census escaped")

    same, _, _ = semantics.build_raw_lift_families()
    structural_zero = semantics.exact_semantic_column(same[0], N)
    if cancelled_signed_mass(same[0]) != (4, 4):
        raise GateError("hostile real zero-column subject lost common-edge cancellation")
    if degree5_only_fingerprint(structural_zero.hinges):
        raise GateError("structural mass-four column leaked onto degree-five-only rows")
    genuine_control = semantics.exact_semantic_column(subject[0].pair, N)
    if not degree5_only_fingerprint(genuine_control.hinges):
        raise GateError("first genuine mass-five control unexpectedly has zero high-degree support")
    zero_high_witnesses = zero_high_witness_replay(semantics, charge_tools)
    if len(zero_high_witnesses) != 3:
        raise GateError("zero-high hostile witness census drift")

    tiny = tiny_direct_vs_streamed_oracle(semantics)
    default_row_map = sketch_map_contract(16_384, PRIME, SKETCH_SEED)
    if (
        default_row_map["contract_sha256"]
        != EXPECTED_DEFAULT_ROW_MAP_CONTRACT_SHA256
    ):
        raise GateError("default extension-compatible row-map contract drift")
    planned_extension = post_census_extension_contract()
    upstream_controls = rank_tools.self_test()
    cache_control = cache_roundtrip_control()
    identity = np.eye(2, dtype=np.int64)
    if rank_tools.rank_array(identity, PRIME) != 2:
        raise GateError("full-rank bridge synthetic control failed")
    collapsed = np.array([[1, 1]], dtype=np.int64)
    if rank_tools.rank_array(collapsed, PRIME) != 1:
        raise GateError("deficient-sketch synthetic control failed")

    return {
        "schema": SCHEMA,
        "result": "SELF_TEST_PASS",
        "bindings": bindings,
        "family_census": census,
        "zero_high_genuine_mass5_witnesses": zero_high_witnesses,
        "tiny_direct_vs_streamed_oracle": tiny,
        "default_row_map_contract": default_row_map,
        "post_census_extension_contract": planned_extension,
        "resumable_cache_control": cache_control,
        "hostile_controls": {
            "original_13419_column_formulation_rejected": True,
            "reason": (
                "1,877 registered same-component representatives are signed mass four "
                "after exact common-edge cancellation and are zero on degree-five-only rows"
            ),
            "real_union_column_zero_checked": 0,
            "real_union_column_zero_degree5_only_hinges": 0,
            "first_genuine_union_column_checked": subject[0].union_column,
            "first_genuine_has_nonzero_degree5_only_support": True,
            "genuine_mass5_full_rank_formulation_rejected": True,
            "genuine_mass5_zero_high_class_indices": [161, 3_600, 7_172],
            "priority_zero_high_class_7172_has_charge_minus_12": True,
            "full_rank_sketch_bridge_control": True,
            "deficient_sketch_is_not_interpreted_as_full_matrix_deficiency": True,
        },
        "upstream_g0054_controls": upstream_controls,
        "theorem_boundary": THEOREM_BOUNDARY,
    }


def memory_available_bytes() -> int:
    with Path("/proc/meminfo").open("r", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise GateError("cannot read MemAvailable")


def resource_preflight(
    buckets: int, columns: int, minimum_available_gib: float
) -> dict[str, object]:
    available = memory_available_bytes()
    entries = buckets * columns
    sketch_u32 = entries * 4
    rank_int64 = entries * 8
    # python-flint's current bridge materializes an int64 array and a Python
    # integer list before constructing nmod_mat.  This is deliberately a
    # conservative planning estimate, not a measured allocation theorem.
    python_list_estimate = entries * 36
    conservative_peak = sketch_u32 + rank_int64 + python_list_estimate + (2 << 30)
    required = int(minimum_available_gib * (1 << 30))
    return {
        "available_bytes": available,
        "available_gib": available / (1 << 30),
        "minimum_available_gib": minimum_available_gib,
        "passes_threshold": available >= required,
        "sketch_shape": [buckets, columns],
        "sketch_entries": entries,
        "sketch_uint32_bytes": sketch_u32,
        "sketch_uint32_gib": sketch_u32 / (1 << 30),
        "rank_int64_copy_bytes": rank_int64,
        "rank_int64_copy_gib": rank_int64 / (1 << 30),
        "python_integer_list_planning_bytes": python_list_estimate,
        "conservative_peak_planning_bytes": conservative_peak,
        "conservative_peak_planning_gib": conservative_peak / (1 << 30),
        "estimate_status": "PLANNING_ESTIMATE_NOT_A_BOUND",
    }


def environment(workers: int) -> dict[str, object]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "workers": workers,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def semantic_statistics(records: Sequence[dict[str, object]]) -> dict[str, object]:
    def values(key: str) -> list[int]:
        return [int(record[key]) for record in records]

    column_order = [int(record["subject_column"]) for record in records]
    semantic_hashes = [str(record["semantic_column_sha256"]) for record in records]
    return {
        "completed_columns": len(records),
        "subject_column_order_sha256": canonical_sha256(column_order),
        "semantic_column_hashes_sha256": canonical_sha256(semantic_hashes),
        "raw_direction_count_min": min(values("raw_direction_count")),
        "raw_direction_count_max": max(values("raw_direction_count")),
        "all_primitive_hinges_min": min(values("all_primitive_hinges")),
        "all_primitive_hinges_max": max(values("all_primitive_hinges")),
        "degree5_only_nonzero_hinges_min": min(values("degree5_only_nonzero_hinges")),
        "degree5_only_nonzero_hinges_max": max(values("degree5_only_nonzero_hinges")),
        "sum_worker_seconds": sum(float(record["seconds"]) for record in records),
    }


def subject_descriptor(column: SubjectColumn) -> dict[str, object]:
    return {
        "subject_column": column.subject_column,
        "union_column": column.union_column,
        "family": column.family,
        "class_index": column.class_index,
        "signed_mass": column.signed_mass,
        "pair": serialize_pair(column.pair),
    }


def load_gzip_json(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"cache metadata is not a regular non-symlink file: {path}")
    with gzip.open(path, "rt", encoding="ascii") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise GateError(f"cache metadata is not an object: {path}")
    return value


def ensure_cache_dir(cache_dir: Path) -> Path:
    resolved = cache_dir.resolve()
    if resolved.parent != HERE.resolve():
        raise GateError("cache directory must be a direct G-0068 child")
    if cache_dir.exists():
        if cache_dir.is_symlink() or not cache_dir.is_dir():
            raise GateError(f"cache path is not a regular directory: {cache_dir}")
    else:
        cache_dir.mkdir(mode=0o755)
    return cache_dir


def write_npy_atomic(path: Path, matrix: np.ndarray) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen cache matrix: {path}")
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial cache matrix exists: {temporary}")
    with temporary.open("xb") as destination:
        np.save(destination, np.ascontiguousarray(matrix, dtype="<u4"), allow_pickle=False)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)


def cache_shard_paths(cache_dir: Path, start: int, stop: int) -> tuple[Path, Path]:
    stem = f"sketch-{start:05d}-{stop - 1:05d}"
    return cache_dir / f"{stem}.npy", cache_dir / f"{stem}.json.gz"


def validate_cached_shard(
    matrix_path: Path,
    metadata_path: Path,
    expected_contract: dict[str, object],
) -> tuple[np.ndarray, list[dict[str, object]], dict[str, object]]:
    metadata = load_gzip_json(metadata_path)
    for key, expected in expected_contract.items():
        if metadata.get(key) != expected:
            raise GateError(
                f"cache shard contract drift in {metadata_path.name}: {key}="
                f"{metadata.get(key)!r}/{expected!r}"
            )
    if sha256_path(matrix_path) != metadata.get("npy_file_sha256"):
        raise GateError(f"cache shard file hash drift: {matrix_path}")
    matrix = np.load(matrix_path, mmap_mode="r", allow_pickle=False)
    expected_shape = tuple(map(int, metadata["shape"]))
    if matrix.shape != expected_shape or matrix.dtype != np.dtype("uint32"):
        raise GateError(
            f"cache shard matrix contract drift: {matrix.shape}/{matrix.dtype}"
        )
    observed_matrix_hash = hash_modular_matrix(
        matrix,
        int(metadata["prime"]),
        "max11-g0068-cache-shard-v1",
    )
    if observed_matrix_hash != metadata.get("modular_matrix_sha256"):
        raise GateError(f"cache shard modular matrix hash drift: {matrix_path}")
    records = metadata.get("semantic_records")
    if not isinstance(records, list) or len(records) != matrix.shape[1]:
        raise GateError(f"cache shard semantic-record census drift: {metadata_path}")
    global_indices = [int(record["subject_column"]) for record in records]
    if global_indices != list(range(int(metadata["start"]), int(metadata["stop"]))):
        raise GateError(f"cache shard semantic-record ordering drift: {metadata_path}")
    if canonical_sha256(records) != metadata.get("semantic_records_sha256"):
        raise GateError(f"cache shard semantic-record hash drift: {metadata_path}")
    return matrix, records, metadata


def cache_roundtrip_control() -> dict[str, object]:
    matrix = np.array([[1, 0], [2, 3], [0, 4]], dtype=np.uint32)
    records = [
        {"subject_column": 0, "semantic_column_sha256": "a" * 64},
        {"subject_column": 1, "semantic_column_sha256": "b" * 64},
    ]
    with tempfile.TemporaryDirectory(prefix=".g0068-cache-control-", dir=HERE) as raw:
        directory = Path(raw)
        matrix_path = directory / "sketch-00000-00001.npy"
        metadata_path = directory / "sketch-00000-00001.json.gz"
        contract: dict[str, object] = {
            "schema": SHARD_SCHEMA,
            "script_sha256": sha256_path(SCRIPT_PATH),
            "input_hashes": input_bindings(),
            "prime": 101,
            "seed": "g0068-cache-control",
            "buckets": 3,
            "start": 0,
            "stop": 2,
            "columns": 2,
            "subject_descriptors_sha256": canonical_sha256([0, 1]),
            "shape": [3, 2],
            "dtype": "uint32",
        }
        write_npy_atomic(matrix_path, matrix)
        metadata = {
            **contract,
            "npy_file": matrix_path.name,
            "npy_file_sha256": sha256_path(matrix_path),
            "modular_matrix_sha256": hash_modular_matrix(
                matrix, 101, "max11-g0068-cache-shard-v1"
            ),
            "semantic_records_sha256": canonical_sha256(records),
            "semantic_records": records,
        }
        write_gzip_atomic(metadata_path, metadata, direct_child=False)
        replay, replay_records, _ = validate_cached_shard(
            matrix_path, metadata_path, contract
        )
        if not np.array_equal(replay, matrix) or replay_records != records:
            raise GateError("cache roundtrip control changed matrix or semantic records")
        overwrite_rejected = False
        try:
            write_npy_atomic(matrix_path, matrix)
        except FileExistsError:
            overwrite_rejected = True
        if not overwrite_rejected:
            raise GateError("cache no-overwrite control escaped")
        mutant = dict(contract)
        mutant["seed"] = "mutated-seed"
        drift_rejected = False
        try:
            validate_cached_shard(matrix_path, metadata_path, mutant)
        except GateError:
            drift_rejected = True
        if not drift_rejected:
            raise GateError("cache contract-drift control escaped")
    return {
        "npy_and_metadata_roundtrip": True,
        "per_column_semantic_records_replayed": True,
        "existing_shard_overwrite_rejected": True,
        "contract_drift_rejected": True,
    }


def load_or_generate_sketch_cache(
    subject: Sequence[SubjectColumn],
    args: argparse.Namespace,
    bindings: dict[str, str],
) -> tuple[np.ndarray, list[dict[str, object]], dict[str, object]]:
    cache_dir = ensure_cache_dir(args.cache_dir)
    script_hash = sha256_path(SCRIPT_PATH)
    row_map = sketch_map_contract(args.sketch_buckets, args.prime, args.seed)
    sketch = np.zeros((args.sketch_buckets, len(subject)), dtype=np.uint32)
    all_records: list[dict[str, object] | None] = [None] * len(subject)
    deterministic_shards = []
    reused_shards = 0
    generated_shards = 0
    for start in range(0, len(subject), args.shard_columns):
        stop = min(start + args.shard_columns, len(subject))
        shard_subject = list(subject[start:stop])
        descriptors = [subject_descriptor(column) for column in shard_subject]
        descriptor_hash = canonical_sha256(descriptors)
        matrix_path, metadata_path = cache_shard_paths(cache_dir, start, stop)
        expected_contract: dict[str, object] = {
            "schema": SHARD_SCHEMA,
            "script_sha256": script_hash,
            "input_hashes": bindings,
            "prime": args.prime,
            "seed": args.seed,
            "buckets": args.sketch_buckets,
            "start": start,
            "stop": stop,
            "columns": stop - start,
            "subject_descriptors_sha256": descriptor_hash,
            "shape": [args.sketch_buckets, stop - start],
            "dtype": "uint32",
            "row_map_contract_sha256": row_map["contract_sha256"],
        }
        if matrix_path.exists() or metadata_path.exists():
            if not (matrix_path.exists() and metadata_path.exists()):
                raise GateError(
                    f"incomplete no-overwrite cache shard pair: {matrix_path}/{metadata_path}"
                )
            shard_matrix, shard_records, metadata = validate_cached_shard(
                matrix_path, metadata_path, expected_contract
            )
            reused_shards += 1
        else:
            remapped = [
                SubjectColumn(
                    subject_column=local,
                    union_column=column.union_column,
                    family=column.family,
                    class_index=column.class_index,
                    pair=column.pair,
                    signed_mass=column.signed_mass,
                )
                for local, column in enumerate(shard_subject)
            ]
            shard_matrix, local_records = generate_streamed_sketch(
                remapped,
                args.sketch_buckets,
                args.prime,
                args.seed,
                args.workers,
                args.max_tasks_per_child,
                args.progress_every,
            )
            shard_records = []
            for local, (record, column) in enumerate(
                zip(local_records, shard_subject, strict=True)
            ):
                enriched = dict(record)
                enriched["local_shard_column"] = local
                enriched["subject_column"] = start + local
                enriched["union_column"] = column.union_column
                enriched["family"] = column.family
                enriched["class_index"] = column.class_index
                shard_records.append(enriched)
            write_npy_atomic(matrix_path, shard_matrix)
            metadata = {
                **expected_contract,
                "npy_file": matrix_path.name,
                "npy_file_sha256": sha256_path(matrix_path),
                "modular_matrix_sha256": hash_modular_matrix(
                    shard_matrix,
                    args.prime,
                    "max11-g0068-cache-shard-v1",
                ),
                "semantic_records_sha256": canonical_sha256(shard_records),
                "semantic_records": shard_records,
                "no_overwrite_resume_contract": (
                    "If both shard files exist they are hash- and contract-validated and "
                    "reused. If neither exists they are written atomically once. A lone "
                    "file, stale partial, hash drift, or contract drift fails closed."
                ),
            }
            write_gzip_atomic(metadata_path, metadata, direct_child=False)
            generated_shards += 1
        sketch[:, start:stop] = np.asarray(shard_matrix, dtype=np.uint32)
        for record in shard_records:
            subject_column = int(record["subject_column"])
            if all_records[subject_column] is not None:
                raise GateError(f"cache supplied duplicate subject column {subject_column}")
            all_records[subject_column] = record
        deterministic_shards.append(
            {
                "start": start,
                "stop": stop,
                "matrix_file": matrix_path.name,
                "matrix_file_sha256": sha256_path(matrix_path),
                "metadata_file": metadata_path.name,
                "metadata_file_sha256": sha256_path(metadata_path),
                "modular_matrix_sha256": metadata["modular_matrix_sha256"],
                "semantic_records_sha256": metadata["semantic_records_sha256"],
            }
        )
    if any(record is None for record in all_records):
        raise GateError("resumable cache did not cover every subject column")
    records = [record for record in all_records if record is not None]
    manifest = {
        "schema": CACHE_MANIFEST_SCHEMA,
        "script_sha256": script_hash,
        "input_hashes": bindings,
        "prime": args.prime,
        "seed": args.seed,
        "buckets": args.sketch_buckets,
        "columns": len(subject),
        "complete_degree5_only_rows": EXPECTED_D5_ONLY_ROWS,
        "complete_degree5_only_rows_sha256": EXPECTED_D5_ONLY_SHA256,
        "row_map_contract": row_map,
        "post_census_extension_contract": post_census_extension_contract(),
        "subject_descriptors_sha256": canonical_sha256(
            [subject_descriptor(column) for column in subject]
        ),
        "shard_columns": args.shard_columns,
        "shards": deterministic_shards,
        "ordered_semantic_records_sha256": canonical_sha256(records),
        "extension_contract": (
            "Future columns, including the scheduled charged novel-tree block and its "
            "current compact 32-column basis, may be stored in a separate immutable "
            "manifest with the identical row_map_contract.contract_sha256. A consumer "
            "then concatenates those columns after this natural basis without "
            "regenerating or overwriting either cache."
        ),
        "no_overwrite_resume_contract": (
            "Existing complete shard pairs are validated and reused; no shard is ever "
            "overwritten. Incomplete or drifting shard pairs fail closed."
        ),
    }
    manifest_path = cache_dir / "manifest.json.gz"
    if manifest_path.exists():
        observed_manifest = load_gzip_json(manifest_path)
        if observed_manifest != manifest:
            raise GateError("existing cache manifest does not match reconstructed manifest")
    else:
        write_gzip_atomic(manifest_path, manifest, direct_child=False)
    execution = {
        "cache_directory": cache_dir.name,
        "manifest_file": manifest_path.name,
        "manifest_file_sha256": sha256_path(manifest_path),
        "manifest_payload_sha256": canonical_sha256(manifest),
        "total_shards": len(deterministic_shards),
        "generated_shards_this_run": generated_shards,
        "reused_shards_this_run": reused_shards,
        "no_overwrite_resume_contract_enforced": True,
    }
    return sketch, records, execution


def zero_high_kernel_records(
    records: Sequence[dict[str, object]],
    subject: Sequence[SubjectColumn],
    charge_tools: ModuleType,
) -> list[dict[str, object]]:
    output = []
    for record in records:
        if int(record["degree5_only_nonzero_hinges"]):
            continue
        subject_column = int(record["subject_column"])
        column = subject[subject_column]
        normal_form = record.get("zero_high_full_lower_normal_form")
        if not isinstance(normal_form, dict):
            raise GateError(f"zero-high column lacks full lower normal form: {subject_column}")
        hinges = normal_form.get("hinges")
        linear = normal_form.get("linear")
        if not isinstance(hinges, list) or not isinstance(linear, list):
            raise GateError(f"malformed zero-high lower normal form: {subject_column}")
        charge = exact_boolean_charge(charge_tools, column.pair)
        output.append(
            {
                "subject_column": subject_column,
                "union_column": column.union_column,
                "family": column.family,
                "class_index": column.class_index,
                "pair": serialize_pair(column.pair),
                "signed_mass": column.signed_mass,
                "exact_boolean_mobius_charge": charge,
                "lower_degree_nonzero_hinges": len(hinges),
                "linear_nonzero_coordinates": sum(bool(value) for value in linear),
                "semantic_column_sha256": record["semantic_column_sha256"],
                "full_lower_degree_normal_form": normal_form,
            }
        )
    return output


def smoke_run(args: argparse.Namespace) -> dict[str, object]:
    started = time.perf_counter()
    before = input_bindings()
    semantics = load_semantics("g0068_smoke_g0049")
    rank_tools = load_rank_tools("g0068_smoke_g0054")
    charge_tools = load_charge_tools("g0068_smoke_g0060")
    subject, census = load_subject(semantics)
    universe = degree5_universe_certificate(rank_tools)
    by_family_class = {
        (column.family, column.class_index): column for column in subject
    }
    sample_keys = (
        ("same", 1),
        ("same", 161),
        ("same", 3_600),
        ("same", 7_172),
        ("cross", 0),
        ("cross", EXPECTED_CROSS_COLUMNS - 1),
    )
    if any(key not in by_family_class for key in sample_keys):
        raise GateError("smoke family/class selection drift")
    sample = [by_family_class[key] for key in sample_keys]
    sample_positions = tuple(column.subject_column for column in sample)
    remapped = [
        SubjectColumn(
            subject_column=index,
            union_column=column.union_column,
            family=column.family,
            class_index=column.class_index,
            pair=column.pair,
            signed_mass=column.signed_mass,
        )
        for index, column in enumerate(sample)
    ]

    streamed_started = time.perf_counter()
    streamed, worker_records = generate_streamed_sketch(
        remapped,
        args.sketch_buckets,
        args.prime,
        args.seed,
        args.workers,
        args.max_tasks_per_child,
        args.progress_every,
    )
    streamed_seconds = time.perf_counter() - streamed_started

    direct_started = time.perf_counter()
    direct_columns = [semantics.exact_semantic_column(column.pair, N) for column in remapped]
    direct_fingerprints = [degree5_only_fingerprint(column.hinges) for column in direct_columns]
    direct_oracle = direct_sketch_oracle(
        direct_fingerprints, args.sketch_buckets, args.prime, args.seed
    )
    direct_seconds = time.perf_counter() - direct_started
    direct_matrix = np.column_stack(
        [
            sketch_fingerprint(value, args.sketch_buckets, args.prime, args.seed)
            for value in direct_fingerprints
        ]
    )
    if not np.array_equal(streamed, direct_matrix):
        raise GateError("spawned streamed pass does not match independent direct smoke pass")
    direct_digests = [semantics.semantic_column_digest(column) for column in direct_columns]
    worker_digests = [str(record["semantic_column_sha256"]) for record in worker_records]
    if direct_digests != worker_digests:
        raise GateError("smoke semantic digests differ across passes")
    zero_high_local = [
        index for index, value in enumerate(direct_fingerprints) if not value
    ]
    if zero_high_local != [1, 2, 3]:
        raise GateError(f"smoke zero-high witness positions drift: {zero_high_local}")
    active_local = [index for index in range(len(sample)) if index not in zero_high_local]
    sketch_rank = rank_tools.rank_array(streamed, args.prime)
    active_sketch_rank = rank_tools.rank_array(streamed[:, active_local], args.prime)
    if sketch_rank > len(active_local) or active_sketch_rank != sketch_rank:
        raise GateError("smoke sketch rank exceeds sample column count")
    witness_replay = zero_high_witness_replay(semantics, charge_tools)
    after = input_bindings()
    if before != after:
        raise GateError("upstream inputs changed during smoke execution")

    sample_descriptors = [
        {
            "smoke_column": index,
            "subject_column": sample_positions[index],
            "union_column": column.union_column,
            "family": column.family,
            "class_index": column.class_index,
            "pair": serialize_pair(column.pair),
        }
        for index, column in enumerate(sample)
    ]
    return {
        "schema": SCHEMA,
        "mode": "smoke",
        "result": SMOKE_RESULT,
        "script_sha256": sha256_path(SCRIPT_PATH),
        "input_hashes_before": before,
        "input_hashes_after": after,
        "inputs_stable": True,
        "complete_degree5_only_universe": universe,
        "registered_family_partition": census,
        "sample": {
            "selection_rule": (
                "one nonzero-high same control, the three frozen genuine-mass5 "
                "zero-high witnesses, and first/last cross controls"
            ),
            "columns": len(sample),
            "descriptors": sample_descriptors,
            "descriptors_sha256": canonical_sha256(sample_descriptors),
        },
        "streamed_semantics": semantic_statistics(worker_records),
        "direct_vs_streamed_oracle": {
            **direct_oracle,
            "spawned_stream_equals_direct_second_pass": True,
            "semantic_column_hashes_match_across_passes": True,
            "streamed_seconds": streamed_seconds,
            "direct_second_pass_seconds": direct_seconds,
        },
        "row_map_contract": sketch_map_contract(
            args.sketch_buckets, args.prime, args.seed
        ),
        "post_census_extension_contract": post_census_extension_contract(),
        "smoke_rank": {
            "prime": args.prime,
            "rank": sketch_rank,
            "columns": len(sample),
            "explicit_zero_high_columns": len(zero_high_local),
            "nonzero_high_columns": len(active_local),
            "nonzero_high_block_rank": active_sketch_rank,
            "diagnostic_only": True,
        },
        "zero_high_witnesses": witness_replay,
        "hostile_pilot_contract": {
            "independent_evenly_spaced_pilot_columns": 128,
            "independent_same_family_samples": 64,
            "independent_cross_family_samples": 64,
            "independent_zero_high_same_samples": 3,
            "independent_zero_high_cross_samples": 0,
            "independent_sketch_rank": 125,
            "independent_high_nnz_min": 0,
            "independent_high_nnz_max": 39_927,
            "contract_enforced_here": (
                "the three exact witness pairs, empty degree5-only fingerprints, "
                "full lower-degree semantic digests/nnz, and Boolean charges are replayed"
            ),
            "priority_next_gate": (
                "project the class-7172 zero-high column, whose exact Boolean charge is "
                "-12, through the frozen lower-mass quotient"
            ),
        },
        "full_run_resource_preflight": resource_preflight(
            args.sketch_buckets,
            EXPECTED_GENUINE_MASS5_COLUMNS,
            args.minimum_available_gib,
        ),
        "theorem_boundary": THEOREM_BOUNDARY,
        "claim_boundary": (
            "This smoke artifact validates bindings, the exact family partition, the "
            "complete row census, and direct-versus-streamed semantics on six frozen "
            "columns. It computes no rank of the 11,542-column subject and proves no "
            "MAX11 construction or obstruction."
        ),
        "environment": environment(args.workers),
        "wall_seconds": time.perf_counter() - started,
    }


def full_run(args: argparse.Namespace) -> dict[str, object]:
    started = time.perf_counter()
    if args.sketch_buckets < EXPECTED_GENUINE_MASS5_COLUMNS:
        raise GateError(
            f"full-run sketch needs at least {EXPECTED_GENUINE_MASS5_COLUMNS} buckets"
        )
    before = input_bindings()
    semantics = load_semantics("g0068_full_g0049")
    rank_tools = load_rank_tools("g0068_full_g0054")
    charge_tools = load_charge_tools("g0068_full_g0060")
    subject, census = load_subject(semantics)
    universe = degree5_universe_certificate(rank_tools)
    preflight = resource_preflight(
        args.sketch_buckets, len(subject), args.minimum_available_gib
    )
    if not preflight["passes_threshold"]:
        raise GateError(f"full-run resource preflight failed: {preflight}")

    generation_started = time.perf_counter()
    sketch, records, cache_execution = load_or_generate_sketch_cache(
        subject, args, before
    )
    generation_seconds = time.perf_counter() - generation_started
    zero_indices = [
        int(record["subject_column"])
        for record in records
        if int(record["degree5_only_nonzero_hinges"]) == 0
    ]
    active_indices = [
        int(record["subject_column"])
        for record in records
        if int(record["degree5_only_nonzero_hinges"]) != 0
    ]
    if not zero_indices or len(zero_indices) + len(active_indices) != len(subject):
        raise GateError("semantic zero/nonzero-high partition is malformed")
    if np.any(sketch[:, zero_indices]):
        raise GateError("explicit zero-high column has a nonzero streamed sketch entry")
    frozen_witness_subjects = {
        column.subject_column
        for column in subject
        if column.family == "same" and column.class_index in ZERO_HIGH_SAME_WITNESSES
    }
    if not frozen_witness_subjects.issubset(set(zero_indices)):
        raise GateError("frozen genuine-mass-five zero-high witness escaped full partition")
    zero_kernel = zero_high_kernel_records(records, subject, charge_tools)
    if len(zero_kernel) != len(zero_indices):
        raise GateError("zero-high kernel record census drift")

    full_sketch_hash = hash_modular_matrix(
        sketch, args.prime, "max11-g0068-full-degree5-only-sketch-v1"
    )
    active_sketch = np.ascontiguousarray(sketch[:, active_indices])
    active_sketch_hash = hash_modular_matrix(
        active_sketch,
        args.prime,
        "max11-g0068-nonzero-high-degree5-only-sketch-v1",
    )
    rank_started = time.perf_counter()
    sketch_rank = rank_tools.rank_array(active_sketch, args.prime)
    rank_seconds = time.perf_counter() - rank_started
    if sketch_rank == len(active_indices):
        result = FULL_RANK_RESULT
        characteristic_zero_bridge = {
            "status": "EXACT",
            "reason": (
                "The explicitly partitioned zero-high columns vanish on every complete "
                "degree-five-only row. Full sketch column rank on the remaining block "
                "exhibits full rank of that complete block modulo the prime. A nonzero "
                "modular maximal minor is a nonzero integer minor, so over Q and R the "
                "complete natural-family high-degree kernel is exactly the coordinate "
                "span of the emitted zero-high columns."
            ),
        }
    else:
        result = DEFICIENT_RESULT
        characteristic_zero_bridge = {
            "status": "NO_CONCLUSION",
            "reason": (
                "Left sketching may destroy rank. The displayed deficiency is not a "
                "dependency of the complete matrix and must not be lifted or promoted."
            ),
        }
    after = input_bindings()
    if before != after:
        raise GateError("upstream inputs changed during full execution")
    return {
        "schema": SCHEMA,
        "mode": "full",
        "result": result,
        "script_sha256": sha256_path(SCRIPT_PATH),
        "input_hashes_before": before,
        "input_hashes_after": after,
        "inputs_stable": True,
        "complete_degree5_only_universe": universe,
        "registered_family_partition": census,
        "subject": {
            "columns": len(subject),
            "explicit_zero_high_columns": len(zero_indices),
            "nonzero_high_columns": len(active_indices),
            "definition": (
                "all registered natural single-edge representatives with exact cancelled "
                "signed branch mass (5,5)"
            ),
        },
        "semantic_generation": {
            **semantic_statistics(records),
            "seconds": generation_seconds,
        },
        "resumable_first_pass_cache": cache_execution,
        "deterministic_sketch": {
            "definition": (
                "For each primitive direction d, SHA256(ASCII('max11-g0068-countsketch-v1|' "
                "+ seed + '|' + comma-separated d)); bucket=little_u64(bytes[0:8]) mod "
                "buckets; weight=1+(little_u64(bytes[8:16]) mod (prime-1))."
            ),
            "seed": args.seed,
            "buckets": args.sketch_buckets,
            "columns": len(subject),
            "explicit_zero_high_columns": len(zero_indices),
            "rank_subject_columns": len(active_indices),
            "prime": args.prime,
            "full_including_zero_columns_matrix_sha256": full_sketch_hash,
            "nonzero_high_block_matrix_sha256": active_sketch_hash,
            "nonzero_high_block_rank": sketch_rank,
            "rank_seconds": rank_seconds,
        },
        "zero_high_kernel_block": {
            "columns": len(zero_kernel),
            "subject_column_indices": zero_indices,
            "subject_column_indices_sha256": canonical_sha256(zero_indices),
            "records_sha256": canonical_sha256(zero_kernel),
            "records": zero_kernel,
            "mandatory_next_gate": (
                "reduce the complete emitted lower-degree normal forms against the exact "
                "lower-mass quotient and test the Boolean-charge/target coordinate"
            ),
        },
        "characteristic_zero_bridge": characteristic_zero_bridge,
        "resource_preflight": preflight,
        "theorem_boundary": THEOREM_BOUNDARY,
        "claim_boundary": (
            "A full-rank nonzero-high result proves only that the complete high-degree "
            "kernel of the 11,542 genuine natural lifts is the emitted coordinate span of "
            "the exact zero-high columns. Those columns remain potentially constructive "
            "and require the lower-degree quotient gate; the 1,877 structural mass-four "
            "lifts also remain allowable corrections. This does not cover other mass-five "
            "atoms, higher signed masses, asymmetric atoms, or unrestricted two-hidden-"
            "layer networks. A deficient nonzero-high sketch is inconclusive pending "
            "complete-row kernel replay."
        ),
        "environment": environment(args.workers),
        "wall_seconds": time.perf_counter() - started,
    }


def write_gzip_atomic(
    path: Path, value: object, *, direct_child: bool = True
) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen output: {path}")
    if direct_child:
        if path.resolve().parent != HERE.resolve():
            raise GateError("output must be a direct G-0068 child")
    else:
        try:
            path.resolve().relative_to(HERE.resolve())
        except ValueError as error:
            raise GateError("cache output must remain inside G-0068") from error
    temporary = path.with_name(path.name + ".partial")
    if temporary.exists():
        raise FileExistsError(f"stale partial output exists: {temporary}")
    raw = canonical_bytes(value)
    with temporary.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    temporary.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--smoke", action="store_true")
    modes.add_argument("--full", action="store_true")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--max-tasks-per-child", type=int, default=16)
    parser.add_argument("--progress-every", type=int, default=100)
    parser.add_argument("--prime", type=int, default=PRIME)
    parser.add_argument("--sketch-buckets", type=int, default=16_384)
    parser.add_argument("--seed", default=SKETCH_SEED)
    parser.add_argument("--minimum-available-gib", type=float, default=20.0)
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--shard-columns", type=int, default=128)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(argv)
    if not (1 <= args.workers <= 16):
        parser.error("--workers must be in [1,16]")
    if args.max_tasks_per_child < 1:
        parser.error("--max-tasks-per-child must be positive")
    if args.progress_every < 0:
        parser.error("--progress-every must be nonnegative")
    if args.prime < 3:
        parser.error("--prime must be at least three")
    if args.sketch_buckets < 1:
        parser.error("--sketch-buckets must be positive")
    if args.minimum_available_gib <= 0:
        parser.error("--minimum-available-gib must be positive")
    if args.shard_columns < 1 or args.shard_columns > EXPECTED_GENUINE_MASS5_COLUMNS:
        parser.error(
            f"--shard-columns must be in [1,{EXPECTED_GENUINE_MASS5_COLUMNS}]"
        )
    if not args.seed or not args.seed.isascii():
        parser.error("--seed must be nonempty ASCII")
    if args.output is not None and not (args.smoke or args.full):
        parser.error("--output applies only to --smoke or --full")
    if args.no_write and not (args.smoke or args.full):
        parser.error("--no-write applies only to --smoke or --full")
    if args.full and args.no_write:
        parser.error("--full always persists the resumable first-pass cache and report")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if args.preflight_only:
        bindings = input_bindings()
        semantics = load_semantics("g0068_preflight_g0049")
        rank_tools = load_rank_tools("g0068_preflight_g0054")
        _, census = load_subject(semantics)
        report = {
            "schema": SCHEMA,
            "result": "PREFLIGHT_PASS",
            "bindings": bindings,
            "family_census": census,
            "complete_degree5_only_universe": degree5_universe_certificate(rank_tools),
            "resources": resource_preflight(
                args.sketch_buckets,
                EXPECTED_GENUINE_MASS5_COLUMNS,
                args.minimum_available_gib,
            ),
            "theorem_boundary": THEOREM_BOUNDARY,
        }
        print(json.dumps(report, sort_keys=True))
        return 0
    report = smoke_run(args) if args.smoke else full_run(args)
    if not args.no_write:
        output = args.output or (DEFAULT_SMOKE_OUTPUT if args.smoke else DEFAULT_FULL_OUTPUT)
        write_gzip_atomic(output, report)
        print(
            json.dumps(
                {
                    "result": report["result"],
                    "output": str(output),
                    "output_sha256": sha256_path(output),
                },
                sort_keys=True,
            )
        )
    else:
        print(
            json.dumps(
                {
                    "result": report["result"],
                    "mode": report["mode"],
                    "wall_seconds": report["wall_seconds"],
                    "no_write": True,
                },
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
