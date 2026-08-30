#!/usr/bin/env python3
"""Exact joint S1 gate for the exhaustive natural zero-high block.

The primary subject is the ordered same-family class manifest certified by
G-0068.  This program trusts that manifest only for class selection.  It
rebuilds every pair, complete primitive normal form, linear coordinate vector,
degree-five vanishing check, semantic digest, and Boolean charge independently.

Let C_P be the 1,288 exact G-0061 pivot columns and H the reconstructed
candidate columns on all 99,858 D4 rows.  Instead of explicitly forming the
expensive Schur product C_P B^{-1} H_R, the gate works with

    N = [C_P | H].

Since rank_Q(C_P)=1,288, rank(N)-1,288 is exactly the candidate quotient rank.
The fast gate applies a deterministic integer CountSketch to N.  Full target
rank after left multiplication is a one-sided exact certificate.  A deficient
sketch is never promoted: its nullvectors are replayed on every complete row,
then the exact fallback streams actual rows while retaining an original-row
basis of size at most 1,288+K.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
import gc
from math import factorial, gcd
import gzip
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import platform
import resource
import sys
import time
from types import ModuleType
from typing import Any, Iterable, Sequence

from flint import nmod_mat
import numpy as np


N_COORDINATES = 11
COMPLETE_ROWS = 99_858
BASELINE_COLUMNS = 1_358
BASELINE_RANK = 1_288
PRIMARY_EXPECTED_RAW_CANDIDATES = 526
FULL_ORBIT_MULTIPLIER = factorial(N_COORDINATES)
PRIMES = (1_000_003, 1_000_033)
DEFAULT_SKETCH_BUCKETS = 4_096
DEFAULT_ROW_BLOCK = 2_048
SKETCH_RANK_BLOCK = 512
SKETCH_SEED = "max11-g0070-direct-s1-plus-zero-high-v1"

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
G0049_SCRIPT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
G0060_SCRIPT = ROOT / "artifacts/math/G-0060/boolean_mobius_ancestry.py"
G0060_REPORT = ROOT / "artifacts/math/G-0060/report_v1.json"
G0061_SCRIPT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift.py"
G0061_REPORT = ROOT / "artifacts/math/G-0061/exact_s1_kernel_lift_v1.json.gz"
STRUCTURE_REPORT = (
    ROOT / "artifacts/math/G-0068/zero_high_structure_verifier_v1.json.gz"
)
DEFAULT_OUTPUT = HERE / "joint_zero_high_s1_quotient_gate_v1.json.gz"
SCRIPT_PATH = Path(__file__).resolve()

EXPECTED_INPUT_HASHES = {
    "g0049_script_sha256": "0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04",
    "g0060_script_sha256": "da249cad23877d78be4de93ebdc49f771033e9084b1b7168893f35bbeb8c6e53",
    "g0060_report_sha256": "2bf930f9bcc77c6da27199e5e9374fd0a0d31844222d9afff43c65b50b58513a",
    "g0061_script_sha256": "2e0ad714b2f56104fc70b98c5527f291769acb7a32053e44840a643d7046e7e8",
    "g0061_report_sha256": "d372ac740e485b4608b23a879ed466051aa1d45f899aa9dce89ff8d2ee13b7f2",
    "g0068_structure_report_sha256": "fb909ed5f675b6b937e26e5929033513e3da6f3294e0df8e934b91dcd4ebe444",
}

SCHEMA = "max11-g0070-joint-zero-high-s1-quotient-gate-v1"
STRUCTURE_SCHEMA = "max11-g0068-zero-high-structure-certificate-v1"


class GateError(RuntimeError):
    """Fail-closed binding, semantic, arithmetic, or theorem-boundary error."""


Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


@dataclass(frozen=True)
class CandidateSpec:
    namespace: str
    family: str
    class_index: int
    union_column: int
    pair: Pair
    signed_mass: int


@dataclass
class CandidateSemantic:
    unique_position: int
    namespace: str
    family: str
    class_index: int
    union_column: int
    pair: Pair
    signed_mass: int
    rows: np.ndarray
    values: np.ndarray
    linear: tuple[int, ...]
    seed_charge: int
    lambda_value: int
    semantic_sha256: str
    full_normal_form_sha256: str
    hinge_only_sha256: str
    aliases: list[dict[str, Any]]

    def as_sparse_result(self) -> dict[str, Any]:
        return {
            "order": self.unique_position,
            "namespace": self.namespace,
            "source_id": self.union_column,
            "sequence": 7_000_000 + self.unique_position,
            "active_vertices": N_COORDINATES,
            "rows": self.rows,
            "values": self.values,
            "lambda": self.lambda_value,
            "semantic_sha256": self.semantic_sha256,
        }


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"input is not a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json_gz(path: Path) -> dict[str, Any]:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"gzip input is not a regular non-symlink file: {path}")
    with gzip.open(path, "rt", encoding="ascii") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise GateError(f"top-level JSON object required: {path}")
    return value


def import_bound(name: str, path: Path, expected_hash: str) -> ModuleType:
    observed = sha256_path(path)
    if not expected_hash or observed != expected_hash:
        raise GateError(f"bound script drift: {path}: {observed}/{expected_hash}")
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise GateError(f"cannot import bound module: {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def input_bindings(*, require_structure: bool = True) -> dict[str, str]:
    paths = {
        "g0049_script_sha256": G0049_SCRIPT,
        "g0060_script_sha256": G0060_SCRIPT,
        "g0060_report_sha256": G0060_REPORT,
        "g0061_script_sha256": G0061_SCRIPT,
        "g0061_report_sha256": G0061_REPORT,
    }
    if require_structure:
        paths["g0068_structure_report_sha256"] = STRUCTURE_REPORT
    observed = {key: sha256_path(path) for key, path in paths.items()}
    expected = {key: EXPECTED_INPUT_HASHES[key] for key in paths}
    if observed != expected:
        raise GateError(f"input binding drift: observed={observed}, expected={expected}")
    return observed


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[int(u), int(v)] for u, v in branch] for branch in pair]


def zero_based(pair: Pair) -> Pair:
    return tuple(
        tuple((u - 1, v - 1) for u, v in branch) for branch in pair
    )  # type: ignore[return-value]


def cancelled_signed_mass(pair: Pair) -> tuple[int, int]:
    left = Counter(pair[0])
    right = Counter(pair[1])
    common = left & right
    cancelled = sum(common.values())
    return len(pair[0]) - cancelled, len(pair[1]) - cancelled


def positive_mass(direction: Direction) -> int:
    if len(direction) != N_COORDINATES or sum(direction):
        raise GateError(f"malformed zero-sum direction: {direction}")
    return sum(value for value in direction if value > 0)


def load_structure_indices() -> tuple[list[int], dict[str, Any]]:
    report = load_json_gz(STRUCTURE_REPORT)
    if report.get("schema") != STRUCTURE_SCHEMA:
        raise GateError(f"G-0068 structure schema drift: {report.get('schema')}")
    try:
        block = report["scientific_payload"]["zero_high"]
        indices = list(map(int, block["same_class_indices"]))
        subject_columns = list(map(int, block["subject_columns"]))
    except (KeyError, TypeError, ValueError) as error:
        raise GateError("malformed G-0068 zero-high structural payload") from error
    if indices != sorted(set(indices)):
        raise GateError("G-0068 same-class manifest is not strictly ascending")
    if subject_columns != sorted(set(subject_columns)):
        raise GateError("G-0068 subject-column manifest is not strictly ascending")
    if len(indices) != int(block.get("count", -1)) or len(indices) != len(subject_columns):
        raise GateError("G-0068 structural manifest census drift")
    for field, values in (
        ("same_class_indices_sha256", indices),
        ("subject_columns_sha256", subject_columns),
    ):
        expected = block.get(field)
        if expected is not None and expected != canonical_sha256(values):
            raise GateError(f"G-0068 structural manifest hash drift: {field}")
    return indices, {
        "schema": report["schema"],
        "reported_count": len(indices),
        "reported_same_class_indices_sha256": canonical_sha256(indices),
        "reported_subject_columns_sha256": canonical_sha256(subject_columns),
        "reported_subject_columns": subject_columns,
        "reported_boolean_charge_histogram": block.get("boolean_charge_histogram"),
        "reported_boolean_charge_rows": block.get("boolean_charge_rows"),
        "reported_cycle_length_histogram": block.get("cycle_length_histogram"),
        "reported_complete_zero_semantic_rows_sha256": report["scientific_payload"][
            "complete_zero_semantic_replay"
        ]["rows_sha256"],
    }


def build_candidate_specs(
    g0049: ModuleType,
    primary_indices: Sequence[int],
    *,
    expected_primary_subject_columns: Sequence[int],
    append_natural_mass4_base: bool,
) -> tuple[list[CandidateSpec], dict[str, Any]]:
    same, cross, reconstruction = g0049.build_raw_lift_families()
    if len(same) != 9_804 or len(cross) != 3_615:
        raise GateError("G-0049 registered family census drift")
    same_subject_position: dict[int, int] = {}
    subject_position = 0
    for class_index, pair in enumerate(same):
        mass = cancelled_signed_mass(pair)
        if mass == (5, 5):
            same_subject_position[class_index] = subject_position
            subject_position += 1
        elif mass != (4, 4):
            raise GateError(f"unexpected same-family signed mass: {class_index}/{mass}")
    if subject_position != 7_927:
        raise GateError(f"same-family genuine subject census drift: {subject_position}")
    observed_subject_columns = [same_subject_position[index] for index in primary_indices]
    if observed_subject_columns != list(map(int, expected_primary_subject_columns)):
        raise GateError("G-0049 reconstruction disagrees with G-0068 subject positions")

    specs: list[CandidateSpec] = []
    for class_index in primary_indices:
        if not 0 <= class_index < len(same):
            raise GateError(f"same class index out of range: {class_index}")
        pair = same[class_index]
        if cancelled_signed_mass(pair) != (5, 5):
            raise GateError(f"zero-high subject lost genuine mass five: {class_index}")
        specs.append(
            CandidateSpec(
                namespace="g0070_primary_zero_high",
                family="same",
                class_index=class_index,
                union_column=class_index,
                pair=pair,
                signed_mass=5,
            )
        )
    structural_indices = []
    if append_natural_mass4_base:
        for class_index, pair in enumerate(same):
            if cancelled_signed_mass(pair) != (4, 4):
                continue
            structural_indices.append(class_index)
            specs.append(
                CandidateSpec(
                    namespace="g0070_structural_mass4_appendix",
                    family="same",
                    class_index=class_index,
                    union_column=class_index,
                    pair=pair,
                    signed_mass=4,
                )
            )
        if len(structural_indices) != 1_877:
            raise GateError(f"structural mass-four census drift: {len(structural_indices)}")
    return specs, {
        "primary_raw_candidates": len(primary_indices),
        "independently_reconstructed_primary_subject_columns_sha256": canonical_sha256(
            observed_subject_columns
        ),
        "structural_mass4_raw_aliases_appended": len(structural_indices),
        "structural_mass4_indices_sha256": (
            canonical_sha256(structural_indices) if structural_indices else None
        ),
        "ordered_raw_descriptors_sha256": canonical_sha256(
            [
                {
                    "namespace": spec.namespace,
                    "family": spec.family,
                    "class_index": spec.class_index,
                    "union_column": spec.union_column,
                    "signed_mass": spec.signed_mass,
                    "pair": serialize_pair(spec.pair),
                }
                for spec in specs
            ]
        ),
        "g0049_reconstruction_sha256": canonical_sha256(reconstruction),
    }


_WORKER_G0049: ModuleType | None = None
_WORKER_CHARGE: ModuleType | None = None
_WORKER_ROW_INDEX: dict[Direction, int] | None = None


def semantic_task(
    task: tuple[int, CandidateSpec],
) -> tuple[int, dict[str, Any]]:
    order, spec = task
    if _WORKER_G0049 is None or _WORKER_CHARGE is None or _WORKER_ROW_INDEX is None:
        raise GateError("semantic worker globals are not initialized")
    column = _WORKER_G0049.exact_semantic_column(spec.pair, N_COORDINATES)
    linear = tuple(map(int, column.linear))
    if len(linear) != N_COORDINATES:
        raise GateError(f"linear normal form has wrong dimension: {spec.class_index}")
    sparse: list[tuple[int, int, Direction]] = []
    serialized_hinges = []
    degree_histogram: Counter[int] = Counter()
    for direction in sorted(column.hinges):
        coefficient = int(column.hinges[direction])
        direction = tuple(map(int, direction))
        if not coefficient:
            raise GateError(f"zero hinge coefficient survived: {spec.class_index}")
        if gcd(*(abs(value) for value in direction)) != 1:
            raise GateError(f"nonprimitive hinge survived: {spec.class_index}/{direction}")
        # G-0049 absorbs directions nonpositive on the ordered cone into the
        # linear term; its stored hinge keys are exactly the complementary
        # primitive, first-nonzero-positive directions.
        if _WORKER_G0049.nonpositive_on_ordered_cone(direction):
            raise GateError(f"linearized direction survived as a hinge: {spec.class_index}/{direction}")
        degree = positive_mass(direction)
        degree_histogram[degree] += 1
        row = _WORKER_ROW_INDEX.get(direction)
        if row is None:
            raise GateError(f"hinge escaped complete D4 universe: {direction}")
        sparse.append((row, coefficient, direction))
        serialized_hinges.append(
            {"direction": list(direction), "coefficient": coefficient}
        )
    if spec.namespace == "g0070_primary_zero_high" and any(
        degree >= 5 for degree in degree_histogram
    ):
        raise GateError(f"primary zero-high class emitted a D5-only hinge: {spec.class_index}")
    rows = np.fromiter((row for row, _value, _direction in sparse), dtype=np.uint32)
    values = np.fromiter((value for _row, value, _direction in sparse), dtype=np.int64)
    if len(rows) != len(set(map(int, rows))) or np.any(values == 0):
        raise GateError(f"malformed sparse normal form: {spec.class_index}")
    if len(rows) and np.any(rows[1:] <= rows[:-1]):
        # G-0049 sorts directions; the complete universe must preserve that order.
        raise GateError(f"complete-row ordering drift: {spec.class_index}")
    observed_semantic = _WORKER_G0049.semantic_column_digest(column)
    reconstructed = _WORKER_G0049.SemanticColumn(
        linear=linear,
        hinges={direction: value for _row, value, direction in sparse},
        raw_direction_count=0,
        permutation_count=0,
    )
    if _WORKER_G0049.semantic_column_digest(reconstructed) != observed_semantic:
        raise GateError(f"semantic digest reconstruction drift: {spec.class_index}")
    pair_zero = zero_based(spec.pair)
    charge = _WORKER_CHARGE.boolean_mobius_charge(
        N_COORDINATES,
        lambda point, pair=pair_zero: _WORKER_CHARGE.pair_atom_value(pair, point),
    )
    if charge.denominator != 1:
        raise GateError(f"nonintegral Boolean charge: {spec.class_index}/{charge}")
    seed_charge = int(charge)
    lambda_value = FULL_ORBIT_MULTIPLIER * seed_charge
    normal_form = {"linear": list(linear), "hinges": serialized_hinges}
    return order, {
        "spec": spec,
        "rows": rows,
        "values": values,
        "linear": linear,
        "seed_charge": seed_charge,
        "lambda": lambda_value,
        "semantic_sha256": observed_semantic,
        "full_normal_form_sha256": canonical_sha256(normal_form),
        "hinge_only_sha256": canonical_sha256(serialized_hinges),
        "degree_histogram": dict(sorted(degree_histogram.items())),
        "support_size": len(rows),
        "linear_nonzero_coordinates": sum(bool(value) for value in linear),
    }


def normalize_histogram(value: object) -> dict[str, int] | None:
    if value is None:
        return None
    if not isinstance(value, dict):
        raise GateError("histogram is not a JSON object")
    return {str(key): int(count) for key, count in sorted(value.items(), key=lambda x: int(x[0]))}


def reconstruct_and_deduplicate_candidates(
    specs: Sequence[CandidateSpec],
    universe: tuple[Direction, ...],
    g0049: ModuleType,
    charge_tools: ModuleType,
    *,
    workers: int,
    reported_primary_charge_histogram: object,
    reported_primary_charge_rows: object,
    reported_primary_semantic_rows_sha256: str,
) -> tuple[list[CandidateSemantic], dict[str, Any]]:
    if len(universe) != COMPLETE_ROWS:
        raise GateError(f"complete D4 universe row drift: {len(universe)}")
    row_index = {direction: row for row, direction in enumerate(universe)}
    if len(row_index) != COMPLETE_ROWS:
        raise GateError("complete D4 universe contains duplicate directions")

    global _WORKER_G0049, _WORKER_CHARGE, _WORKER_ROW_INDEX
    _WORKER_G0049 = g0049
    _WORKER_CHARGE = charge_tools
    _WORKER_ROW_INDEX = row_index
    tasks = list(enumerate(specs))
    started = time.perf_counter()
    if workers == 1:
        raw = [semantic_task(task) for task in tasks]
    else:
        import multiprocessing as mp

        context = mp.get_context("fork")
        raw = []
        with context.Pool(processes=workers, maxtasksperchild=32) as pool:
            for item in pool.imap_unordered(semantic_task, tasks, chunksize=1):
                raw.append(item)
                if len(raw) % 50 == 0 or len(raw) == len(tasks):
                    print(
                        f"G0070_SEMANTICS columns={len(raw)}/{len(tasks)}",
                        file=sys.stderr,
                        flush=True,
                    )
    raw.sort(key=lambda item: item[0])
    if [order for order, _item in raw] != list(range(len(specs))):
        raise GateError("semantic worker output ordering drift")

    unique: list[CandidateSemantic] = []
    by_full_hash: dict[str, int] = {}
    raw_to_unique: list[int] = []
    raw_descriptors = []
    primary_charge_histogram: Counter[int] = Counter()
    all_charge_histogram: Counter[int] = Counter()
    hinge_groups: Counter[str] = Counter()
    degree_histogram: Counter[int] = Counter()
    for raw_position, (_order, item) in enumerate(raw):
        spec: CandidateSpec = item["spec"]
        if spec.namespace == "g0070_primary_zero_high":
            primary_charge_histogram[int(item["seed_charge"])] += 1
        all_charge_histogram[int(item["seed_charge"])] += 1
        degree_histogram.update(
            {int(key): int(count) for key, count in item["degree_histogram"].items()}
        )
        hinge_groups[str(item["hinge_only_sha256"])] += 1
        alias = {
            "raw_position": raw_position,
            "namespace": spec.namespace,
            "family": spec.family,
            "class_index": spec.class_index,
            "union_column": spec.union_column,
            "signed_mass": spec.signed_mass,
            "pair": serialize_pair(spec.pair),
        }
        full_hash = str(item["full_normal_form_sha256"])
        prior = by_full_hash.get(full_hash)
        if prior is None:
            unique_position = len(unique)
            by_full_hash[full_hash] = unique_position
            unique.append(
                CandidateSemantic(
                    unique_position=unique_position,
                    namespace=spec.namespace,
                    family=spec.family,
                    class_index=spec.class_index,
                    union_column=spec.union_column,
                    pair=spec.pair,
                    signed_mass=spec.signed_mass,
                    rows=item["rows"],
                    values=item["values"],
                    linear=item["linear"],
                    seed_charge=int(item["seed_charge"]),
                    lambda_value=int(item["lambda"]),
                    semantic_sha256=str(item["semantic_sha256"]),
                    full_normal_form_sha256=full_hash,
                    hinge_only_sha256=str(item["hinge_only_sha256"]),
                    aliases=[alias],
                )
            )
        else:
            previous = unique[prior]
            if (
                previous.linear != item["linear"]
                or not np.array_equal(previous.rows, item["rows"])
                or not np.array_equal(previous.values, item["values"])
                or previous.seed_charge != int(item["seed_charge"])
                or previous.lambda_value != int(item["lambda"])
                or previous.semantic_sha256 != str(item["semantic_sha256"])
            ):
                raise GateError("full-normal-form hash alias has inconsistent semantics")
            previous.aliases.append(alias)
            unique_position = prior
        raw_to_unique.append(unique_position)
        raw_descriptors.append(
            {
                **alias,
                "unique_position": unique_position,
                "support_size": int(item["support_size"]),
                "linear_nonzero_coordinates": int(item["linear_nonzero_coordinates"]),
                "seed_boolean_mobius_charge": int(item["seed_charge"]),
                "full_orbit_lambda": int(item["lambda"]),
                "semantic_sha256": str(item["semantic_sha256"]),
                "full_normal_form_sha256": full_hash,
                "hinge_only_sha256": str(item["hinge_only_sha256"]),
            }
        )

    observed_primary_histogram = {
        str(key): value for key, value in sorted(primary_charge_histogram.items())
    }
    reported = normalize_histogram(reported_primary_charge_histogram)
    if reported is not None and reported != observed_primary_histogram:
        raise GateError(
            "independent Boolean-charge histogram disagrees with G-0068: "
            f"{observed_primary_histogram}/{reported}"
        )
    observed_charge_rows = [
        [
            int(item["spec"].class_index),
            int(item["seed_charge"]),
        ]
        for _order, item in raw
        if item["spec"].namespace == "g0070_primary_zero_high"
    ]
    if reported_primary_charge_rows != observed_charge_rows:
        raise GateError("independent per-class Boolean charges disagree with G-0068")
    observed_semantic_rows = [
        [
            int(item["spec"].class_index),
            0,
            int(item["support_size"]),
            str(item["semantic_sha256"]),
        ]
        for _order, item in raw
        if item["spec"].namespace == "g0070_primary_zero_high"
    ]
    observed_semantic_rows_sha256 = canonical_sha256(observed_semantic_rows)
    if observed_semantic_rows_sha256 != reported_primary_semantic_rows_sha256:
        raise GateError(
            "independent complete zero semantic rows disagree with G-0068: "
            f"{observed_semantic_rows_sha256}/{reported_primary_semantic_rows_sha256}"
        )
    unique_descriptors = [
        {
            "unique_position": item.unique_position,
            "canonical_namespace": item.namespace,
            "canonical_family": item.family,
            "canonical_class_index": item.class_index,
            "canonical_union_column": item.union_column,
            "signed_mass": item.signed_mass,
            "support_size": len(item.rows),
            "linear": list(item.linear),
            "seed_boolean_mobius_charge": item.seed_charge,
            "full_orbit_lambda": item.lambda_value,
            "semantic_sha256": item.semantic_sha256,
            "full_normal_form_sha256": item.full_normal_form_sha256,
            "hinge_only_sha256": item.hinge_only_sha256,
            "aliases": item.aliases,
        }
        for item in unique
    ]
    return unique, {
        "raw_candidates": len(specs),
        "unique_full_normal_forms": len(unique),
        "exact_duplicate_aliases_removed": len(specs) - len(unique),
        "raw_to_unique": raw_to_unique,
        "raw_to_unique_sha256": canonical_sha256(raw_to_unique),
        "raw_descriptors_sha256": canonical_sha256(raw_descriptors),
        "unique_descriptors_sha256": canonical_sha256(unique_descriptors),
        "unique_descriptors": unique_descriptors,
        "primary_boolean_charge_histogram": observed_primary_histogram,
        "primary_boolean_charge_rows_sha256": canonical_sha256(observed_charge_rows),
        "primary_complete_zero_semantic_rows_sha256": observed_semantic_rows_sha256,
        "all_boolean_charge_histogram": {
            str(key): value for key, value in sorted(all_charge_histogram.items())
        },
        "primary_charged_columns": sum(
            count for charge, count in primary_charge_histogram.items() if charge
        ),
        "primary_zero_charge_columns": primary_charge_histogram.get(0, 0),
        "hinge_only_duplicate_group_count": sum(
            count > 1 for count in hinge_groups.values()
        ),
        "hinge_only_duplicate_multiplicity_histogram": {
            str(size): count
            for size, count in sorted(Counter(hinge_groups.values()).items())
        },
        "complete_hinge_positive_mass_histogram": {
            str(key): value for key, value in sorted(degree_histogram.items())
        },
        "full_orbit_lambda_rule": "11! times exact seed Boolean Mobius charge",
        "full_orbit_multiplier": FULL_ORBIT_MULTIPLIER,
        "semantic_seconds": time.perf_counter() - started,
    }


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.uint32)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def from_nmod(matrix: nmod_mat, *, dtype: np.dtype[Any] = np.dtype(np.uint32)) -> np.ndarray:
    return np.asarray(matrix.tolist(), dtype=dtype)


def pivot_columns_from_rref(rref_matrix: nmod_mat, rank: int) -> list[int]:
    pivots = []
    for row in range(rank):
        pivot = next(
            (
                column
                for column in range(rref_matrix.ncols())
                if int(rref_matrix[row, column])
            ),
            None,
        )
        if pivot is None:
            raise GateError(f"RREF row {row} lacks a pivot")
        pivots.append(pivot)
    if len(set(pivots)) != rank:
        raise GateError("RREF pivot duplication")
    return pivots


def modular_matrix_sha256(matrix: np.ndarray, prime: int, namespace: str) -> str:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype="<u4")
    digest = hashlib.sha256()
    digest.update(
        (
            f"{namespace};uint32-little-row-major;"
            f"shape={matrix.shape[0]}x{matrix.shape[1]};prime={prime}\n"
        ).encode("ascii")
    )
    digest.update(reduced.tobytes(order="C"))
    return digest.hexdigest()


def signed_matrix_sha256(matrix: np.ndarray, namespace: str) -> str:
    value = np.ascontiguousarray(matrix, dtype="<i8")
    digest = hashlib.sha256()
    digest.update(
        (
            f"{namespace};int64-little-row-major;"
            f"shape={matrix.shape[0]}x{matrix.shape[1]}\n"
        ).encode("ascii")
    )
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def direction_token(direction: Direction) -> bytes:
    return ",".join(map(str, direction)).encode("ascii")


def countsketch_row_map(
    universe: tuple[Direction, ...], buckets: int, seed: str
) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
    if buckets < 1 or not seed or not seed.isascii():
        raise GateError("invalid CountSketch bucket count or seed")
    row_buckets = np.empty(len(universe), dtype=np.uint32)
    row_signs = np.empty(len(universe), dtype=np.int8)
    digest = hashlib.sha256()
    for row, direction in enumerate(universe):
        payload = (
            b"max11-g0070-direct-countsketch-v1|"
            + seed.encode("ascii")
            + b"|"
            + direction_token(direction)
        )
        hashed = hashlib.sha256(payload).digest()
        row_buckets[row] = int.from_bytes(hashed[:8], "little") % buckets
        row_signs[row] = 1 if hashed[8] & 1 else -1
        digest.update(int(row_buckets[row]).to_bytes(4, "little"))
        digest.update(int(row_signs[row]).to_bytes(1, "little", signed=True))
    contract = {
        "schema": "max11-g0070-direction-keyed-signed-countsketch-v1",
        "complete_row_count": len(universe),
        "buckets": buckets,
        "seed": seed,
        "row_map_raw_sha256": digest.hexdigest(),
        "definition": (
            "SHA256(ASCII('max11-g0070-direct-countsketch-v1|' + seed + '|' "
            "+ comma-separated primitive direction)); bucket=little_u64(bytes[0:8]) "
            "mod buckets; sign=+1 iff low bit of byte[8] is one, else -1"
        ),
    }
    contract["contract_sha256"] = canonical_sha256(contract)
    return row_buckets, row_signs, contract


def semantic_l1_bound(semantic: dict[str, Any]) -> int:
    values = semantic["values"]
    if not isinstance(values, np.ndarray) or values.dtype.kind not in "iu":
        raise GateError("semantic values lost exact integer array")
    return sum(abs(int(value)) for value in values)


def build_direct_countsketch(
    semantics: Sequence[dict[str, Any]],
    row_buckets: np.ndarray,
    row_signs: np.ndarray,
    buckets: int,
) -> tuple[np.ndarray, dict[str, Any]]:
    started = time.perf_counter()
    sketch = np.zeros((buckets, len(semantics)), dtype=np.int64)
    maximum_l1 = 0
    total_nonzeros = 0
    for column, semantic in enumerate(semantics):
        rows = semantic["rows"]
        values = semantic["values"]
        if not isinstance(rows, np.ndarray) or not isinstance(values, np.ndarray):
            raise GateError("semantic sparse arrays lost NumPy representation")
        if len(rows) != len(values):
            raise GateError("semantic sparse row/value length mismatch")
        l1 = semantic_l1_bound(semantic)
        maximum_l1 = max(maximum_l1, l1)
        if l1 >= 1 << 63:
            raise GateError("signed CountSketch accumulator may overflow int64")
        selected_buckets = row_buckets[rows]
        contributions = values * row_signs[rows].astype(np.int64, copy=False)
        np.add.at(sketch[:, column], selected_buckets, contributions)
        total_nonzeros += len(rows)
    if int(np.max(np.abs(sketch))) > maximum_l1:
        raise GateError("CountSketch entry exceeds exact column L1 bound")
    return sketch, {
        "shape": list(sketch.shape),
        "input_sparse_nonzeros": total_nonzeros,
        "maximum_column_l1_bound": maximum_l1,
        "maximum_absolute_sketch_entry": int(np.max(np.abs(sketch))),
        "signed_integer_matrix_sha256": signed_matrix_sha256(
            sketch, "max11-g0070-direct-countsketch-v1"
        ),
        "seconds": time.perf_counter() - started,
    }


def normalized_kernel_vectors(
    field: nmod_mat, rank: int, prime: int
) -> tuple[list[np.ndarray], list[dict[str, Any]]]:
    kernel, nullity_object = field.nullspace()
    nullity = int(nullity_object)
    expected = field.ncols() - rank
    if nullity != expected:
        raise GateError(f"kernel nullity drift: {nullity}/{expected}")
    vectors = []
    records = []
    for basis_column in range(nullity):
        vector = np.fromiter(
            (
                int(kernel[row, basis_column]) % prime
                for row in range(field.ncols())
            ),
            dtype=np.uint32,
            count=field.ncols(),
        )
        support_indices = np.flatnonzero(vector)
        if not len(support_indices):
            raise GateError("nullspace backend emitted the zero vector")
        distinguished = int(support_indices[0])
        scale = pow(int(vector[distinguished]), -1, prime)
        vector = np.remainder(vector.astype(np.uint64) * scale, prime).astype(np.uint32)
        if int(vector[distinguished]) != 1:
            raise GateError("kernel normalization failed")
        replay = field * to_nmod(vector.reshape(-1, 1), prime)
        if any(int(replay[row, 0]) % prime for row in range(replay.nrows())):
            raise GateError("normalized kernel vector failed matrix replay")
        sparse = [[int(index), int(vector[index])] for index in np.flatnonzero(vector)]
        vectors.append(vector)
        records.append(
            {
                "basis_column": basis_column,
                "distinguished_coordinate": distinguished,
                "support_size": len(sparse),
                "sparse_coefficients_sha256": canonical_sha256(sparse),
            }
        )
    return vectors, records


def rank_and_kernel(
    matrix: np.ndarray, prime: int, *, want_kernel: bool
) -> tuple[int, list[np.ndarray], dict[str, Any]]:
    field = to_nmod(matrix, prime)
    rank = int(field.rank())
    vectors: list[np.ndarray] = []
    kernel_records: list[dict[str, Any]] = []
    if want_kernel and rank < matrix.shape[1]:
        vectors, kernel_records = normalized_kernel_vectors(field, rank, prime)
    record = {
        "prime": prime,
        "shape": list(matrix.shape),
        "rank": rank,
        "nullity": matrix.shape[1] - rank,
        "modular_matrix_sha256": modular_matrix_sha256(
            matrix, prime, "max11-g0070-rank-input-v1"
        ),
        "kernel_basis": kernel_records,
    }
    del field
    gc.collect()
    return rank, vectors, record


def modular_sparse_replay(
    semantics: Sequence[dict[str, Any]],
    coefficients: np.ndarray,
    prime: int,
    *,
    keep_residual: bool = False,
) -> tuple[dict[str, Any], np.ndarray | None]:
    if len(semantics) != len(coefficients):
        raise GateError("modular replay coefficient length mismatch")
    residual = np.zeros(COMPLETE_ROWS, dtype=np.uint32)
    potency = 0
    sparse_coefficients = []
    for column, (semantic, raw_coefficient) in enumerate(
        zip(semantics, coefficients, strict=True)
    ):
        coefficient = int(raw_coefficient) % prime
        if not coefficient:
            continue
        rows = semantic["rows"]
        values = np.remainder(semantic["values"], prime).astype(
            np.uint64, copy=False
        )
        updated = (
            residual[rows].astype(np.uint64, copy=False) + values * coefficient
        ) % prime
        residual[rows] = updated.astype(np.uint32)
        potency = (potency + int(semantic["lambda"]) * coefficient) % prime
        sparse_coefficients.append([column, coefficient])
    bad = np.flatnonzero(residual)
    record = {
        "coefficient_support_size": len(sparse_coefficients),
        "sparse_coefficients_sha256": canonical_sha256(sparse_coefficients),
        "nonzero_complete_rows": len(bad),
        "lexicographically_first_nonzero_complete_row": (
            int(bad[0]) if len(bad) else None
        ),
        "lambda_mod_prime": potency,
        "complete_residual_sha256": hashlib.sha256(
            residual.astype("<u4", copy=False).tobytes(order="C")
        ).hexdigest(),
        "all_99858_rows_zero": not len(bad),
    }
    return record, residual if keep_residual else None


def replay_sketch_kernel_proposals(
    vectors: Sequence[np.ndarray],
    semantics: Sequence[dict[str, Any]],
    prime: int,
) -> tuple[list[int], list[dict[str, Any]]]:
    violation_rows = []
    records = []
    for basis_column, vector in enumerate(vectors):
        replay, _residual = modular_sparse_replay(
            semantics, vector, prime, keep_residual=False
        )
        first = replay["lexicographically_first_nonzero_complete_row"]
        if first is not None:
            violation_rows.append(int(first))
        potent = bool(replay["all_99858_rows_zero"] and replay["lambda_mod_prime"])
        records.append(
            {
                "basis_column": basis_column,
                "complete_sparse_replay": replay,
                "is_exact_modular_hinge_relation": bool(replay["all_99858_rows_zero"]),
                "is_potent_exact_modular_hinge_relation": potent,
            }
        )
    return sorted(set(violation_rows)), records


class DirectRowOracle:
    """Materialize only requested rows of [exact S1 pivot basis | candidates]."""

    def __init__(
        self,
        baseline_union_rows: np.ndarray,
        baseline_matrix: np.ndarray,
        pivot_columns: Sequence[int],
        candidates: Sequence[CandidateSemantic],
    ) -> None:
        self.baseline_union_rows = np.asarray(baseline_union_rows, dtype=np.uint32)
        self.baseline_matrix = baseline_matrix
        self.pivot_columns = np.asarray(pivot_columns, dtype=np.int32)
        self.candidates = list(candidates)
        if len(self.pivot_columns) != BASELINE_RANK:
            raise GateError("direct oracle pivot-column census drift")
        if baseline_matrix.shape != (len(self.baseline_union_rows), BASELINE_COLUMNS):
            raise GateError("direct oracle baseline matrix shape drift")
        if len(self.baseline_union_rows) and np.any(
            self.baseline_union_rows[1:] <= self.baseline_union_rows[:-1]
        ):
            raise GateError("baseline union rows are not strictly ascending")
        self.total_columns = BASELINE_RANK + len(candidates)
        self.complete_to_union = np.full(COMPLETE_ROWS, -1, dtype=np.int32)
        self.complete_to_union[self.baseline_union_rows] = np.arange(
            len(self.baseline_union_rows), dtype=np.int32
        )

    def rows(self, labels: Sequence[int], prime: int) -> np.ndarray:
        labels_array = np.asarray(labels, dtype=np.int64)
        if len(labels_array) != len(set(map(int, labels_array))):
            raise GateError("direct oracle received duplicate row labels")
        if np.any(labels_array < 0) or np.any(labels_array >= COMPLETE_ROWS):
            raise GateError("direct oracle row label out of range")
        output = np.zeros((len(labels_array), self.total_columns), dtype=np.int64)
        union_positions = self.complete_to_union[labels_array]
        present = np.flatnonzero(union_positions >= 0)
        if len(present):
            output[present, :BASELINE_RANK] = self.baseline_matrix[
                np.ix_(union_positions[present], self.pivot_columns)
            ]
        complete_to_local = np.full(COMPLETE_ROWS, -1, dtype=np.int32)
        complete_to_local[labels_array] = np.arange(len(labels_array), dtype=np.int32)
        for candidate_position, candidate in enumerate(self.candidates):
            local = complete_to_local[candidate.rows]
            mask = local >= 0
            if np.any(mask):
                output[
                    local[mask], BASELINE_RANK + candidate_position
                ] = candidate.values[mask]
        return np.remainder(output, prime).astype(np.uint32)

    def block(self, start: int, stop: int, prime: int) -> np.ndarray:
        if not 0 <= start < stop <= COMPLETE_ROWS:
            raise GateError(f"invalid direct row block: {start}/{stop}")
        length = stop - start
        output = np.zeros((length, self.total_columns), dtype=np.int64)
        left = int(np.searchsorted(self.baseline_union_rows, start, side="left"))
        right = int(np.searchsorted(self.baseline_union_rows, stop, side="left"))
        if right > left:
            labels = self.baseline_union_rows[left:right].astype(np.int64, copy=False)
            output[labels - start, :BASELINE_RANK] = self.baseline_matrix[
                np.ix_(np.arange(left, right), self.pivot_columns)
            ]
        for candidate_position, candidate in enumerate(self.candidates):
            left_c = int(np.searchsorted(candidate.rows, start, side="left"))
            right_c = int(np.searchsorted(candidate.rows, stop, side="left"))
            if right_c > left_c:
                local_rows = candidate.rows[left_c:right_c].astype(np.int64) - start
                output[
                    local_rows, BASELINE_RANK + candidate_position
                ] = candidate.values[left_c:right_c]
        return np.remainder(output, prime).astype(np.uint32)


def select_original_row_basis(
    matrix: np.ndarray,
    labels: np.ndarray,
    prime: int,
) -> tuple[np.ndarray, np.ndarray, int]:
    """Return independent input rows, never RREF linear combinations."""
    if matrix.ndim != 2 or labels.shape != (matrix.shape[0],):
        raise GateError("row-basis matrix/label shape mismatch")
    # Reduce before the uint32 conversion.  Casting a negative exact entry first
    # would wrap it modulo 2^32 rather than modulo ``prime``.
    reduced_matrix = np.remainder(matrix, prime).astype(np.uint32, copy=False)
    nonzero = np.flatnonzero(np.any(reduced_matrix, axis=1))
    selected_matrix = np.ascontiguousarray(reduced_matrix[nonzero])
    selected_labels = labels[nonzero]
    if not len(selected_matrix):
        return selected_matrix, selected_labels, 0
    field = to_nmod(selected_matrix, prime)
    transposed_rref, rank_object = field.transpose().rref()
    rank = int(rank_object)
    pivots = pivot_columns_from_rref(transposed_rref, rank)
    basis = np.ascontiguousarray(selected_matrix[pivots], dtype=np.uint32)
    basis_labels = np.ascontiguousarray(selected_labels[pivots])
    if int(to_nmod(basis, prime).rank()) != rank:
        raise GateError("selected original rows do not replay their reported rank")
    del field, transposed_rref
    gc.collect()
    return basis, basis_labels, rank


def modular_minor_certificate(
    row_basis: np.ndarray,
    source_labels: np.ndarray,
    rank: int,
    prime: int,
    *,
    row_namespace: str,
) -> dict[str, Any]:
    if row_basis.shape[0] != rank or source_labels.shape != (rank,):
        raise GateError("minor certificate basis shape drift")
    field = to_nmod(row_basis, prime)
    row_rref, replay_rank_object = field.rref()
    replay_rank = int(replay_rank_object)
    if replay_rank != rank:
        raise GateError("minor certificate row rank drift")
    pivot_columns = pivot_columns_from_rref(row_rref, rank)
    minor = np.ascontiguousarray(row_basis[:, pivot_columns], dtype=np.uint32)
    determinant = int(to_nmod(minor, prime).det()) % prime
    if not determinant:
        raise GateError("minor certificate determinant vanished")
    labels = list(map(int, source_labels))
    return {
        "kind": "explicit_nonzero_modular_minor",
        "row_namespace": row_namespace,
        "rank": rank,
        "source_row_labels": labels,
        "source_row_labels_sha256": canonical_sha256(labels),
        "pivot_columns": pivot_columns,
        "pivot_columns_sha256": canonical_sha256(pivot_columns),
        "minor_shape": [rank, rank],
        "minor_modular_sha256": modular_matrix_sha256(
            minor, prime, "max11-g0070-rank-minor-v1"
        ),
        "determinant_mod_prime": determinant,
    }


def countsketch_prime_gate(
    signed_sketch: np.ndarray,
    prime: int,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, list[np.ndarray]]:
    started = time.perf_counter()
    target = signed_sketch.shape[1]
    basis = np.zeros((0, target), dtype=np.uint32)
    basis_labels = np.zeros(0, dtype=np.int64)
    rank = 0
    processed_buckets = 0
    for start in range(0, signed_sketch.shape[0], SKETCH_RANK_BLOCK):
        if rank == target:
            break
        stop = min(start + SKETCH_RANK_BLOCK, signed_sketch.shape[0])
        block = np.remainder(signed_sketch[start:stop], prime).astype(np.uint32)
        labels = np.arange(start, stop, dtype=np.int64)
        basis, basis_labels, rank = select_original_row_basis(
            np.vstack((basis, block)),
            np.concatenate((basis_labels, labels)),
            prime,
        )
        processed_buckets = stop
    vectors: list[np.ndarray] = []
    kernel_records = []
    if rank < target:
        field = to_nmod(basis, prime)
        vectors, kernel_records = normalized_kernel_vectors(field, rank, prime)
        del field
    certificate = modular_minor_certificate(
        basis,
        basis_labels,
        rank,
        prime,
        row_namespace="deterministic_CountSketch_bucket",
    )
    return (
        {
            "prime": prime,
            "rank": rank,
            "target_full_column_rank": target,
            "nullity": target - rank,
            "full_rank_one_sided_certificate": rank == target,
            "sketch_buckets_processed_before_certificate": processed_buckets,
            "full_sketch_scanned_if_deficient": (
                rank == target or processed_buckets == signed_sketch.shape[0]
            ),
            "selected_sketch_bucket_minor": certificate,
            "kernel_basis": kernel_records,
            "seconds": time.perf_counter() - started,
        },
        basis,
        basis_labels,
        vectors,
    )


def cegis_from_sketch_kernel(
    sketch_basis: np.ndarray,
    initial_vectors: Sequence[np.ndarray],
    semantics: Sequence[dict[str, Any]],
    oracle: DirectRowOracle,
    prime: int,
    *,
    max_rounds: int,
) -> tuple[list[int], list[dict[str, Any]]]:
    constraints = np.ascontiguousarray(sketch_basis, dtype=np.uint32)
    vectors = list(initial_vectors)
    violation_rows: list[int] = []
    rounds = []
    seen_rows: set[int] = set()
    for round_index in range(max_rounds):
        proposed_rows, proposal_records = replay_sketch_kernel_proposals(
            vectors, semantics, prime
        )
        fresh = [row for row in proposed_rows if row not in seen_rows]
        rounds.append(
            {
                "round": round_index,
                "constraint_rank": constraints.shape[0],
                "proposal_count": len(vectors),
                "fresh_lexicographically_first_violating_rows": fresh,
                "proposal_replays": proposal_records,
            }
        )
        if not fresh:
            break
        seen_rows.update(fresh)
        violation_rows.extend(fresh)
        actual = oracle.rows(fresh, prime)
        stacked = np.vstack((constraints, actual))
        labels = np.arange(stacked.shape[0], dtype=np.int64)
        constraints, _labels, rank = select_original_row_basis(
            stacked, labels, prime
        )
        if rank == oracle.total_columns:
            vectors = []
            break
        field = to_nmod(constraints, prime)
        vectors, _kernel_records = normalized_kernel_vectors(field, rank, prime)
        del field
    return sorted(set(violation_rows)), rounds


def streaming_source_row_gate(
    oracle: DirectRowOracle,
    pivot_complete_rows: Sequence[int],
    lambda_vector: np.ndarray,
    semantics: Sequence[dict[str, Any]],
    prime: int,
    *,
    seed_rows: Sequence[int],
    block_size: int,
) -> dict[str, Any]:
    started = time.perf_counter()
    initial_labels = list(dict.fromkeys([*map(int, pivot_complete_rows), *map(int, seed_rows)]))
    initial_matrix = oracle.rows(initial_labels, prime)
    basis, basis_labels, rank = select_original_row_basis(
        initial_matrix, np.asarray(initial_labels, dtype=np.int64), prime
    )
    if rank < BASELINE_RANK:
        raise GateError(f"G-0061 pivot rows lost baseline rank at {prime}: {rank}")
    rank_trace = [
        {
            "processed_through_complete_row": None,
            "rank": rank,
            "source": "G0061 pivot rows plus CountSketch CEGIS violations",
        }
    ]
    processed_rows = 0
    for start in range(0, COMPLETE_ROWS, block_size):
        if rank == oracle.total_columns:
            break
        stop = min(start + block_size, COMPLETE_ROWS)
        block = oracle.block(start, stop, prime)
        labels = np.arange(start, stop, dtype=np.int64)
        stacked = np.vstack((basis, block))
        stacked_labels = np.concatenate((basis_labels, labels))
        old_rank = rank
        basis, basis_labels, rank = select_original_row_basis(
            stacked, stacked_labels, prime
        )
        processed_rows = stop
        if rank != old_rank:
            rank_trace.append(
                {
                    "processed_through_complete_row": stop - 1,
                    "rank": rank,
                    "rank_gain": rank - old_rank,
                    "source": "lexicographic complete-row stream",
                }
            )

    scanned_all = processed_rows == COMPLETE_ROWS or rank == oracle.total_columns
    if rank < oracle.total_columns and processed_rows != COMPLETE_ROWS:
        raise GateError("deficient source-row stream terminated before the complete universe")
    minor = modular_minor_certificate(
        basis,
        basis_labels,
        rank,
        prime,
        row_namespace="complete_D4_source_row",
    )
    augmented = np.vstack(
        (basis, np.remainder(lambda_vector, prime).astype(np.uint32).reshape(1, -1))
    )
    augmented_rank = int(to_nmod(augmented, prime).rank())
    gain = augmented_rank - rank
    if gain not in (0, 1):
        raise GateError(f"invalid Lambda augmented gain: {gain}")

    potent_circuit = None
    kernel_records = []
    if rank < oracle.total_columns:
        field = to_nmod(basis, prime)
        vectors, kernel_records = normalized_kernel_vectors(field, rank, prime)
        for basis_column, vector in enumerate(vectors):
            potency = int(
                np.remainder(
                    np.remainder(lambda_vector, prime).astype(np.uint64)
                    @ vector.astype(np.uint64),
                    prime,
                )
            )
            if not potency:
                continue
            normalized = np.remainder(
                vector.astype(np.uint64) * pow(potency, -1, prime), prime
            ).astype(np.uint32)
            replay, _residual = modular_sparse_replay(
                semantics, normalized, prime, keep_residual=False
            )
            if not replay["all_99858_rows_zero"] or replay["lambda_mod_prime"] != 1:
                raise GateError("potent source-kernel vector failed complete replay")
            sparse = [
                [int(index), int(normalized[index])]
                for index in np.flatnonzero(normalized)
            ]
            potent_circuit = {
                "kernel_basis_column": basis_column,
                "normalization": "full Lambda dot coefficients equals one mod prime",
                "sparse_coefficients": sparse,
                "sparse_coefficients_sha256": canonical_sha256(sparse),
                "complete_sparse_replay": replay,
            }
            break
        del field
    if bool(potent_circuit) != bool(gain):
        raise GateError("Lambda rank gain and potent-kernel replay disagree")
    return {
        "prime": prime,
        "target_columns": oracle.total_columns,
        "rank": rank,
        "candidate_quotient_rank": rank - BASELINE_RANK,
        "nullity": oracle.total_columns - rank,
        "augmented_rank": augmented_rank,
        "lambda_augmented_gain": gain,
        "complete_rows_scanned_before_certificate": processed_rows,
        "full_rank_early_stop": rank == oracle.total_columns,
        "all_rows_scanned_if_deficient": rank == oracle.total_columns or scanned_all,
        "source_row_minor": minor,
        "rank_trace": rank_trace,
        "kernel_basis": kernel_records,
        "potent_modular_circuit": potent_circuit,
        "seconds": time.perf_counter() - started,
    }


def load_upstreams() -> tuple[
    dict[str, Any],
    dict[str, Any],
    dict[str, Any],
    ModuleType,
    ModuleType,
    ModuleType,
    ModuleType,
    dict[str, Any],
]:
    direct = input_bindings(require_structure=True)
    g0061 = import_bound("g0070_g0061", G0061_SCRIPT, direct["g0061_script_sha256"])
    inherited, g0057_report, g0059_report, g0057 = g0061.checked_bindings()
    g0061_report = g0061.load_json_gz(G0061_REPORT)
    if int(g0061_report["exact_rank_certificate"]["exact_rank_Q"]) != BASELINE_RANK:
        raise GateError("G-0061 exact baseline rank certificate drift")
    exact_replay = g0061_report.get("exact_complete_replay", {})
    if (
        exact_replay.get("all_exact_integer_hinge_residuals_zero") is not True
        or exact_replay.get("all_exact_lambda_residuals_zero") is not True
        or int(exact_replay.get("relations_replayed", -1))
        != BASELINE_COLUMNS - BASELINE_RANK
    ):
        raise GateError(
            "G-0061 did not certify that its exact kernel relations preserve both "
            "complete hinge semantics and Lambda"
        )
    g0049 = import_bound("g0070_g0049", G0049_SCRIPT, direct["g0049_script_sha256"])
    charge_tools = import_bound(
        "g0070_g0060", G0060_SCRIPT, direct["g0060_script_sha256"]
    )
    return (
        {**direct, "inherited_g0061_bindings": inherited},
        g0057_report,
        g0059_report,
        g0057,
        g0061,
        g0049,
        charge_tools,
        g0061_report,
    )


def memory_available_bytes() -> int:
    pages = os.sysconf("SC_AVPHYS_PAGES")
    page_size = os.sysconf("SC_PAGE_SIZE")
    return int(pages) * int(page_size)


def resource_preflight(
    buckets: int,
    estimated_candidates: int,
    minimum_available_gib: float,
) -> dict[str, Any]:
    total_columns = BASELINE_RANK + estimated_candidates
    sketch_int64 = buckets * total_columns * 8
    sketch_modular_and_flint = buckets * total_columns * (4 + 8)
    baseline_dense = 43_757 * BASELINE_COLUMNS * 8
    source_basis_workspace = 2 * (total_columns + DEFAULT_ROW_BLOCK) * total_columns * 8
    conservative = (
        sketch_int64
        + sketch_modular_and_flint
        + baseline_dense
        + source_basis_workspace
        + 768 * (1 << 20)
    )
    available = memory_available_bytes()
    threshold = int(minimum_available_gib * (1 << 30))
    return {
        "available_bytes": available,
        "available_gib": available / (1 << 30),
        "minimum_available_gib": minimum_available_gib,
        "estimated_candidate_columns": estimated_candidates,
        "estimated_total_direct_columns": total_columns,
        "sketch_buckets": buckets,
        "conservative_peak_bytes": conservative,
        "conservative_peak_gib": conservative / (1 << 30),
        "passes_threshold": available >= max(threshold, conservative),
    }


def environment(workers: int) -> dict[str, Any]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "workers": workers,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def synthetic_schur_equivalence_control() -> dict[str, Any]:
    prime = 101
    baseline = np.array(
        [[1, 0], [0, 1], [2, 3], [4, 5]], dtype=np.int64
    )
    candidates = np.array(
        [[7, 11], [13, 17], [19, 23], [29, 31]], dtype=np.int64
    )
    baseline_lambda = np.array([37, 41], dtype=np.int64)
    candidate_lambda = np.array([0, 47], dtype=np.int64)
    pivot_rows = [0, 1]
    minor = to_nmod(baseline[pivot_rows], prime)
    coefficients = from_nmod(
        minor.solve(to_nmod(candidates[pivot_rows], prime)), dtype=np.dtype(np.uint32)
    )
    residual = np.remainder(
        candidates - baseline @ coefficients.astype(np.int64), prime
    ).astype(np.uint32)
    delta = np.remainder(
        candidate_lambda - baseline_lambda @ coefficients.astype(np.int64), prime
    ).astype(np.uint32)
    direct = np.column_stack((baseline, candidates))
    direct_rank = int(to_nmod(direct, prime).rank())
    residual_rank = int(to_nmod(residual, prime).rank())
    direct_augmented_rank = int(
        to_nmod(
            np.vstack((direct, np.concatenate((baseline_lambda, candidate_lambda)))),
            prime,
        ).rank()
    )
    residual_augmented_rank = int(to_nmod(np.vstack((residual, delta)), prime).rank())
    if direct_rank != 2 + residual_rank:
        raise GateError("synthetic direct/Schur quotient-rank identity failed")
    if direct_augmented_rank - direct_rank != residual_augmented_rank - residual_rank:
        raise GateError("synthetic direct/Schur Lambda-gain identity failed")
    if int(delta[0]) == 0:
        raise GateError("zero candidate Lambda incorrectly forced zero Schur delta")
    return {
        "prime": prime,
        "direct_rank_equals_baseline_plus_schur_rank": True,
        "direct_and_schur_lambda_augmented_gains_equal": True,
        "zero_candidate_lambda_has_nonzero_schur_delta": True,
    }


def self_test() -> dict[str, Any]:
    prime = 101
    matrix = np.array(
        [[1, 0], [2, 0], [0, 1], [1, 1]], dtype=np.uint32
    )
    labels = np.array([10, 11, 12, 13], dtype=np.int64)
    basis, basis_labels, rank = select_original_row_basis(matrix, labels, prime)
    if rank != 2 or list(map(int, basis_labels)) != [10, 12]:
        raise GateError(
            f"transpose-RREF original-row selection drift: {rank}/{basis_labels}"
        )
    signed_basis, signed_labels, signed_rank = select_original_row_basis(
        np.array([[-1, 0], [0, 1]], dtype=np.int64),
        np.array([20, 21], dtype=np.int64),
        prime,
    )
    if (
        signed_rank != 2
        or list(map(int, signed_labels)) != [20, 21]
        or not np.array_equal(
            signed_basis, np.array([[prime - 1, 0], [0, 1]], dtype=np.uint32)
        )
    ):
        raise GateError("signed original-row reduction wrapped before prime reduction")
    certificate = modular_minor_certificate(
        basis, basis_labels, rank, prime, row_namespace="synthetic_source_row"
    )
    semantics = [
        {
            "rows": np.array([0, 2], dtype=np.uint32),
            "values": np.array([1, 1], dtype=np.int64),
            "lambda": 3,
        },
        {
            "rows": np.array([0, 2], dtype=np.uint32),
            "values": np.array([-1, -1], dtype=np.int64),
            "lambda": 5,
        },
    ]
    vector = np.array([1, 1], dtype=np.uint32)
    replay, _ = modular_sparse_replay(semantics, vector, prime)
    if not replay["all_99858_rows_zero"] or replay["lambda_mod_prime"] != 8:
        raise GateError("synthetic complete sparse replay failed")
    mutant = vector.copy()
    mutant[1] = 2
    mutant_replay, _ = modular_sparse_replay(semantics, mutant, prime)
    if mutant_replay["all_99858_rows_zero"]:
        raise GateError("synthetic coefficient mutant escaped")

    signed_sketch = np.array([[1, 0], [0, 1], [1, 1]], dtype=np.int64)
    sketch_record, sketch_basis, _labels, sketch_vectors = countsketch_prime_gate(
        signed_sketch, prime
    )
    if not sketch_record["full_rank_one_sided_certificate"] or sketch_vectors:
        raise GateError("synthetic full-rank CountSketch certificate failed")

    dependent_semantics = [
        {
            "rows": np.array([0, 1], dtype=np.uint32),
            "values": np.array([2, 3], dtype=np.int64),
        },
        {
            "rows": np.array([0, 1], dtype=np.uint32),
            "values": np.array([-4, -6], dtype=np.int64),
        },
    ]
    dependent_direct_sketch, _dependent_controls = build_direct_countsketch(
        dependent_semantics,
        np.array([0, 1], dtype=np.uint32),
        np.array([1, -1], dtype=np.int8),
        2,
    )
    dependent_record, _basis, _labels, dependent_vectors = countsketch_prime_gate(
        dependent_direct_sketch, prime
    )
    if (
        dependent_record["rank"] != 1
        or dependent_record["nullity"] != 1
        or dependent_record["full_rank_one_sided_certificate"]
        or len(dependent_vectors) != 1
        or not np.array_equal(
            dependent_direct_sketch[:, 1], -2 * dependent_direct_sketch[:, 0]
        )
    ):
        raise GateError("common-map dependent-column CountSketch plant escaped")
    dependent_semantics[1]["values"] = np.array([-4, -5], dtype=np.int64)
    mutant_direct_sketch, _mutant_controls = build_direct_countsketch(
        dependent_semantics,
        np.array([0, 1], dtype=np.uint32),
        np.array([1, -1], dtype=np.int8),
        2,
    )
    mutant_record, _basis, _labels, mutant_vectors = countsketch_prime_gate(
        mutant_direct_sketch, prime
    )
    if not mutant_record["full_rank_one_sided_certificate"] or mutant_vectors:
        raise GateError("dependent-column CountSketch coefficient mutant escaped")

    deficient_sketch = np.array([[1, 0]], dtype=np.uint32)
    deficient_field = to_nmod(deficient_sketch, prime)
    initial_vectors, _records = normalized_kernel_vectors(deficient_field, 1, prime)

    class TinyOracle:
        total_columns = 2

        @staticmethod
        def rows(row_labels: Sequence[int], modulus: int) -> np.ndarray:
            full = np.array([[1, 0], [0, 1]], dtype=np.uint32)
            return np.remainder(full[list(row_labels)], modulus).astype(np.uint32)

    violation_rows, rounds = cegis_from_sketch_kernel(
        deficient_sketch,
        initial_vectors,
        semantics=[
            {
                "rows": np.array([0], dtype=np.uint32),
                "values": np.array([1], dtype=np.int64),
                "lambda": 0,
            },
            {
                "rows": np.array([1], dtype=np.uint32),
                "values": np.array([1], dtype=np.int64),
                "lambda": 1,
            },
        ],
        oracle=TinyOracle(),  # type: ignore[arg-type]
        prime=prime,
        max_rounds=2,
    )
    if violation_rows != [1] or not rounds:
        raise GateError("synthetic CountSketch CEGIS did not add the first violating row")
    return {
        "transpose_rref_selects_original_rows_with_preserved_labels": True,
        "selected_original_row_labels": list(map(int, basis_labels)),
        "signed_original_rows_reduced_before_uint32_conversion": True,
        "selected_minor_determinant_mod_prime": certificate["determinant_mod_prime"],
        "direct_vs_schur": synthetic_schur_equivalence_control(),
        "complete_sparse_relation_replayed": True,
        "coefficient_mutant_rejected": True,
        "full_rank_direct_countsketch_certified": True,
        "common_map_dependent_column_plant_detected": True,
        "dependent_column_coefficient_mutant_rejected": True,
        "deficient_countsketch_cegis_added_lex_first_violation": True,
        "full_orbit_multiplier": FULL_ORBIT_MULTIPLIER,
    }


def deterministic_view(value: object) -> object:
    dynamic = {
        "seconds",
        "semantic_seconds",
        "wall_seconds",
        "available_bytes",
        "available_gib",
        "process_max_rss_kib",
    }
    if isinstance(value, dict):
        return {
            key: deterministic_view(item)
            for key, item in value.items()
            if key not in dynamic
        }
    if isinstance(value, list):
        return [deterministic_view(item) for item in value]
    return value


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = time.perf_counter()
    script_hash_before = sha256_path(SCRIPT_PATH)
    (
        bindings,
        g0057_report,
        g0059_report,
        g0057,
        g0061,
        g0049,
        charge_tools,
        g0061_report,
    ) = load_upstreams()
    primary_indices, structure_controls = load_structure_indices()
    if len(primary_indices) != PRIMARY_EXPECTED_RAW_CANDIDATES:
        raise GateError(
            f"frozen primary zero-high census drift: {len(primary_indices)}/"
            f"{PRIMARY_EXPECTED_RAW_CANDIDATES}"
        )
    estimated_candidates = len(primary_indices) + (
        252 if args.append_natural_mass4_base else 0
    )
    preflight = resource_preflight(
        args.sketch_buckets, estimated_candidates, args.minimum_available_gib
    )
    if not preflight["passes_threshold"]:
        raise GateError(f"resource preflight failed: {preflight}")

    (
        universe,
        baseline_results,
        baseline_union_rows,
        baseline_matrix,
        baseline_lambda,
        baseline_controls,
    ) = g0061.regenerate_semantics(g0057, g0057_report, g0059_report, args.workers)
    pivot_rows, pivot_columns, _bases, pivot_controls = g0061.modular_kernel_data(
        g0059_report
    )
    specs, subject_controls = build_candidate_specs(
        g0049,
        primary_indices,
        expected_primary_subject_columns=structure_controls[
            "reported_subject_columns"
        ],
        append_natural_mass4_base=args.append_natural_mass4_base,
    )
    candidates, semantic_controls = reconstruct_and_deduplicate_candidates(
        specs,
        universe,
        g0049,
        charge_tools,
        workers=args.workers,
        reported_primary_charge_histogram=structure_controls[
            "reported_boolean_charge_histogram"
        ],
        reported_primary_charge_rows=structure_controls[
            "reported_boolean_charge_rows"
        ],
        reported_primary_semantic_rows_sha256=structure_controls[
            "reported_complete_zero_semantic_rows_sha256"
        ],
    )
    if not candidates:
        raise GateError("candidate deduplication produced an empty subject")
    if args.append_natural_mass4_base:
        structural_unique_positions = {
            int(unique_position)
            for unique_position, spec in zip(
                semantic_controls["raw_to_unique"], specs, strict=True
            )
            if spec.namespace == "g0070_structural_mass4_appendix"
        }
        if len(structural_unique_positions) != 252:
            raise GateError(
                "structural mass-four aliases did not collapse to 252 base semantics: "
                f"{len(structural_unique_positions)}"
            )
        if any(candidates[position].lambda_value for position in structural_unique_positions):
            raise GateError("a structural mass-four base semantic acquired nonzero Lambda")
        subject_controls["structural_mass4_unique_base_semantics"] = 252
        subject_controls["all_structural_mass4_base_lambdas_zero"] = True
    pivot_semantics = [baseline_results[column] for column in pivot_columns]
    candidate_results = [candidate.as_sparse_result() for candidate in candidates]
    direct_semantics = [*pivot_semantics, *candidate_results]
    direct_lambda = np.array(
        [int(baseline_lambda[column]) for column in pivot_columns]
        + [candidate.lambda_value for candidate in candidates],
        dtype=np.int64,
    )
    total_columns = BASELINE_RANK + len(candidates)
    if len(direct_semantics) != total_columns or direct_lambda.shape != (total_columns,):
        raise GateError("direct matrix semantic/lambda census drift")
    if args.sketch_buckets < total_columns:
        raise GateError(
            f"CountSketch has {args.sketch_buckets} rows but the exact direct matrix "
            f"has {total_columns} columns; a full-rank certificate would be impossible"
        )

    row_buckets, row_signs, row_map_contract = countsketch_row_map(
        universe, args.sketch_buckets, args.sketch_seed
    )
    signed_sketch, sketch_controls = build_direct_countsketch(
        direct_semantics, row_buckets, row_signs, args.sketch_buckets
    )
    sketch_results = []
    sketch_bases: dict[int, np.ndarray] = {}
    sketch_vectors: dict[int, list[np.ndarray]] = {}
    for prime in PRIMES:
        result, basis, _basis_labels, vectors = countsketch_prime_gate(
            signed_sketch, prime
        )
        sketch_results.append(result)
        sketch_bases[prime] = basis
        sketch_vectors[prime] = vectors

    sketch_full_primes = [
        int(item["prime"])
        for item in sketch_results
        if item["full_rank_one_sided_certificate"]
    ]
    fallback_results = []
    cegis_results = []
    if not sketch_full_primes:
        oracle = DirectRowOracle(
            baseline_union_rows, baseline_matrix, pivot_columns, candidates
        )
        for prime in PRIMES:
            violation_rows, rounds = cegis_from_sketch_kernel(
                sketch_bases[prime],
                sketch_vectors[prime],
                direct_semantics,
                oracle,
                prime,
                max_rounds=args.cegis_rounds,
            )
            cegis_results.append(
                {
                    "prime": prime,
                    "rounds": rounds,
                    "distinct_source_violation_rows": violation_rows,
                    "distinct_source_violation_rows_sha256": canonical_sha256(
                        violation_rows
                    ),
                }
            )
            fallback_results.append(
                streaming_source_row_gate(
                    oracle,
                    pivot_rows,
                    direct_lambda,
                    direct_semantics,
                    prime,
                    seed_rows=violation_rows,
                    block_size=args.row_block,
                )
            )

    exact_full_source = [
        int(item["prime"])
        for item in fallback_results
        if int(item["rank"]) == total_columns
    ]
    exact_full_primes = sorted(set(sketch_full_primes + exact_full_source))
    exact_quotient_rank = len(candidates) if exact_full_primes else None
    any_potent_modular = any(
        item.get("potent_modular_circuit") is not None for item in fallback_results
    )
    if exact_quotient_rank is not None:
        result_label = "FULL_ZERO_HIGH_BLOCK_INJECTIVE_MODULO_EXACT_S1_OVER_Q"
    elif any_potent_modular:
        result_label = "POTENT_MODULAR_CIRCUIT_DISCOVERED_PENDING_EXACT_Q_LIFT"
    else:
        result_label = "DEFICIENT_MODULAR_QUOTIENT_PENDING_EXACT_Q_LIFT_OR_NO_GO"

    report: dict[str, Any] = {
        "schema": SCHEMA,
        "script_sha256": script_hash_before,
        "result": result_label,
        "bindings": bindings,
        "subject": {
            "mode": (
                "primary_plus_structural_natural_mass4_base_semantics"
                if args.append_natural_mass4_base
                else "primary_526_zero_high_only"
            ),
            "structure_report": structure_controls,
            "raw_selection": subject_controls,
            "hash_bound_fresh_semantic_reconstruction": semantic_controls,
            "candidate_engine_supports_252_semantic_natural_mass4_appendix": True,
        },
        "exact_s1_baseline": {
            "original_columns": BASELINE_COLUMNS,
            "exact_rank_Q": BASELINE_RANK,
            "exact_kernel_relations_replayed": int(
                g0061_report["exact_complete_replay"]["relations_replayed"]
            ),
            "all_exact_integer_hinge_residuals_zero": g0061_report[
                "exact_complete_replay"
            ]["all_exact_integer_hinge_residuals_zero"],
            "all_exact_lambda_residuals_zero": g0061_report[
                "exact_complete_replay"
            ]["all_exact_lambda_residuals_zero"],
            "pivot_replacement_preserves_hinge_and_lambda_span_over_Q": True,
            "selected_pivot_columns": pivot_columns,
            "selected_pivot_columns_sha256": canonical_sha256(pivot_columns),
            "selected_pivot_complete_rows": pivot_rows,
            "selected_pivot_complete_rows_sha256": canonical_sha256(pivot_rows),
            "pivot_controls": pivot_controls,
            "semantic_regeneration": baseline_controls,
        },
        "direct_matrix_identity": {
            "definition": "N=[the 1288 exact S1 pivot columns | unique candidates]",
            "shape": [COMPLETE_ROWS, total_columns],
            "candidate_quotient_rank_identity": "rank(N)-1288",
            "lambda_gain_identity": "rank(vertical_stack(N,lambda))-rank(N)",
            "explicit_schur_product_materialized": False,
            "reason": (
                "the direct rank identity is exact and avoids approximately "
                "43757*1288*K modular multiply-adds"
            ),
        },
        "stage_S0_direct_countsketch": {
            "row_map": row_map_contract,
            "integer_sketch": sketch_controls,
            "prime_results": sketch_results,
            "full_rank_certifying_primes": sketch_full_primes,
            "one_sided_theorem": (
                "rank(SN)<=rank(N)<=1288+K; therefore rank(SN)=1288+K "
                "forces exact rank_Q(N)=1288+K"
            ),
        },
        "deficient_sketch_cegis": cegis_results,
        "exact_source_row_fallback": fallback_results,
        "exact_Q_bridge": {
            "certifying_primes": exact_full_primes,
            "exact_candidate_quotient_rank_Q": exact_quotient_rank,
            "exact_combined_rank_Q": (
                BASELINE_RANK + exact_quotient_rank
                if exact_quotient_rank is not None
                else None
            ),
            "full_unique_candidate_block_Q_independent_modulo_S1": (
                exact_quotient_rank == len(candidates)
            ),
            "one_good_prime_is_sufficient_for_full_rank_bridge": True,
        },
        "controls": {
            "self_test": self_test(),
            "resource_preflight": preflight,
        },
        "claim_boundary": [
            "The primary run concerns exactly the G-0068-certified 526 zero-high natural representatives after exact full-normal-form deduplication.",
            "Zero seed charge does not imply zero quotient delta: all zero-charge columns remain in the joint matrix.",
            "Primary-block injectivity modulo S1 does not retire the natural family because the 1,877 admissible structural mass-four aliases, collapsing to 252 zero-Lambda base semantics, are omitted unless the explicit appendix mode is run.",
            "Neither mode covers other mass-five atoms, asymmetric atoms, higher signed masses, or unrestricted two-hidden-layer ReLU networks.",
            "A modular potent circuit remains discovery evidence until aligned coefficients are lifted over Q, all hinge rows replay exactly, the complete linear normal form is corrected, and the compiled MAX11 network is independently replayed.",
        ],
        "mandatory_next_gate": (
            "If a potent modular circuit survives, obtain a canonical aligned solution "
            "over additional good primes, rationally reconstruct it, replay every hinge "
            "and Lambda coordinate over Z/Q, reconstruct the baseline linear normal "
            "forms, correct the 11-coordinate linear residual, and independently replay "
            "the compiled network. If the primary block is injective, run the structural "
            "252-semantic natural mass-four appendix before making any natural-family claim."
        ),
        "environment": environment(args.workers),
        "wall_seconds": time.perf_counter() - started,
    }
    report["canonical_scientific_payload_sha256"] = canonical_sha256(
        deterministic_view(report)
    )
    if input_bindings(require_structure=True) != {
        key: value for key, value in bindings.items() if key in EXPECTED_INPUT_HASHES
    }:
        raise GateError("direct inputs changed during execution")
    if sha256_path(SCRIPT_PATH) != script_hash_before:
        raise GateError("G-0070 script changed during execution")
    return report


def write_gzip_atomic(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen output: {path}")
    if path.resolve().parent != HERE.resolve():
        raise GateError("G-0070 output must be a direct artifact-directory child")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial output exists: {partial}")
    raw = canonical_bytes(value)
    with partial.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--self-test", action="store_true")
    modes.add_argument("--preflight-only", action="store_true")
    modes.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=min(4, os.cpu_count() or 1))
    parser.add_argument("--sketch-buckets", type=int, default=DEFAULT_SKETCH_BUCKETS)
    parser.add_argument("--sketch-seed", default=SKETCH_SEED)
    parser.add_argument("--row-block", type=int, default=DEFAULT_ROW_BLOCK)
    parser.add_argument("--cegis-rounds", type=int, default=8)
    parser.add_argument("--minimum-available-gib", type=float, default=20.0)
    parser.add_argument("--append-natural-mass4-base", action="store_true")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(list(argv))
    if not 1 <= args.workers <= 16:
        parser.error("--workers must be in [1,16]")
    minimum_sketch_buckets = BASELINE_RANK + PRIMARY_EXPECTED_RAW_CANDIDATES + (
        252 if args.append_natural_mass4_base else 0
    )
    if args.sketch_buckets < minimum_sketch_buckets:
        parser.error(
            f"--sketch-buckets must be at least {minimum_sketch_buckets} for the "
            "selected subject"
        )
    if not args.sketch_seed or not args.sketch_seed.isascii():
        parser.error("--sketch-seed must be nonempty ASCII")
    if not 64 <= args.row_block <= 8_192:
        parser.error("--row-block must be in [64,8192]")
    if not 1 <= args.cegis_rounds <= 64:
        parser.error("--cegis-rounds must be in [1,64]")
    if args.minimum_available_gib <= 0:
        parser.error("--minimum-available-gib must be positive")
    if args.append_natural_mass4_base and args.output == DEFAULT_OUTPUT and not args.no_write:
        parser.error("appendix mode requires an explicit non-default --output")
    return args


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    if args.preflight_only:
        bindings = input_bindings(require_structure=True)
        indices, structure = load_structure_indices()
        estimated = len(indices) + (252 if args.append_natural_mass4_base else 0)
        report = {
            "schema": SCHEMA,
            "result": "PREFLIGHT_PASS",
            "bindings": bindings,
            "structure": structure,
            "resources": resource_preflight(
                args.sketch_buckets, estimated, args.minimum_available_gib
            ),
            "self_test": self_test(),
        }
        if not report["resources"]["passes_threshold"]:
            raise GateError(f"resource preflight failed: {report['resources']}")
        print(json.dumps(report, sort_keys=True))
        return 0
    report = run(args)
    if not args.no_write:
        write_gzip_atomic(args.output, report)
    print(
        json.dumps(
            {
                "schema": report["schema"],
                "result": report["result"],
                "scientific_sha256": report["canonical_scientific_payload_sha256"],
                "output": None if args.no_write else str(args.output),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
