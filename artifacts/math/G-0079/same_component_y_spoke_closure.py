#!/usr/bin/env python3
"""Outcome-blind preflight and modular Schur gate for the Y-spoke closure.

The new subject consists of every support-three Y-spoke obtained from the
252 frozen MAX10 two-component forest bases by choosing the auxiliary leaf
in the *same* component as the doubled anchor (but distinct from it), with
both outer-branch orientations.  This is complementary to G-0073, whose
auxiliary leaf lies in the opposite component.

Preflight freezes the complete orbit census, cross-family disjointness,
semantic controls, and exact G-0078 separator-price controls.  Registered
execution is deliberately disabled until the source, preregistration, and
preflight receipt have been independently frozen below.  A modular outcome
will remain discovery-only; it cannot establish rational membership or
nonmembership without an exact replayed certificate.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import json
from math import gcd, lcm
import os
from pathlib import Path
import platform
import sys
import time
from types import ModuleType
from typing import Any, Iterable, Sequence

import flint
from flint import nmod_mat
import networkx as nx
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()

G0073_SCRIPT = ROOT / "artifacts/math/G-0073/y_spoke_profile_gate.py"
G0073_PREFLIGHT = ROOT / "artifacts/math/G-0073/y_spoke_orbit_preflight_v1.json.gz"
G0075_SCRIPT = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate.py"
G0075_PREFLIGHT = ROOT / "artifacts/math/G-0075/four_level_preflight_v1.json.gz"
G0075_OUTCOME = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate_v1.json.gz"
G0076_SCRIPT = ROOT / "artifacts/math/G-0076/target_aware_kernel_resolver.py"
G0076_PREFLIGHT = ROOT / "artifacts/math/G-0076/target_aware_kernel_preflight_v1.json.gz"
G0076_OUTCOME = ROOT / "artifacts/math/G-0076/target_aware_kernel_resolver_v1.json.gz"
G0076_KERNEL = ROOT / "artifacts/math/G-0076/target_aware_kernel_p1000003_v1.npy.gz"
G0077_SCRIPT = ROOT / "artifacts/math/G-0077/exact_left_dual_lift.py"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
G0078_SCRIPT = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual.py"
G0078_EXACT = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz"
FULL_OLD_MATRIX = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"

SCHEMA_PREFLIGHT = "max11-g0079-same-component-y-spoke-preflight-v1"
SCHEMA_RUN = "max11-g0079-same-component-y-spoke-schur-v1"
N = 11
OLD_LABELS = 10
BASE_COUNT = 252
OLD_RAW_COUNT = 18_400
OLD_ORBIT_COUNT = 8_104
NEW_RAW_COUNT = 26_960
NEW_ORBIT_COUNT = 18_582
UNION_ORBIT_COUNT = 26_686
TOTAL_ROWS = 16_738
OLD_COLUMNS = 8_107
PRIME = 1_000_003
GLOBAL_OLD_START = 0
GLOBAL_OLD_STOP = 8_106
GLOBAL_NEW_START = 8_107
GLOBAL_NEW_STOP = 26_688
GLOBAL_TARGET_COLUMN = 26_689
PRICE_ZERO_CONTROLS = 60
PRICE_NONZERO_CONTROLS = 60
PERFORMANCE_CONSERVATIVE_FACTOR = 8.0
MAX_PROJECTED_DENSE_SECONDS = 10_800.0
MINIMUM_AVAILABLE_GIB = 32.0
MINIMUM_FREE_DISK_GIB = 12.0
CEGIS_MISMATCH_BATCH = 64
MAX_CEGIS_ROWS = 1_024
MAX_CEGIS_ROUNDS = 16
MAX_REGISTERED_WALL_SECONDS = 21_600.0

EXPECTED_BINDINGS = {
    "g0073_producer": (
        G0073_SCRIPT,
        "333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67",
    ),
    "g0073_preflight": (
        G0073_PREFLIGHT,
        "05908cba9a9ea47ccda0d07f2fa5af630c38c7031986ede57cb6a78dad611e1d",
    ),
    "g0075_producer": (
        G0075_SCRIPT,
        "ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab",
    ),
    "g0075_preflight": (
        G0075_PREFLIGHT,
        "bbe4e8410e2d042deea2844aa7099f2601feaa201d903557ca09d5f16f2514e0",
    ),
    "g0075_outcome": (
        G0075_OUTCOME,
        "ec8f1f1213f9105a5aa51d1b842ac2dc331d82224157d598a7caf0af93425371",
    ),
    "g0076_producer": (
        G0076_SCRIPT,
        "1499b96abb926d54d96f2b3163748f40dfd5810325424dbb41409a829213c4e2",
    ),
    "g0076_preflight": (
        G0076_PREFLIGHT,
        "32970ecc3a6bd8ebe26169eeaad5120930e78c00be2bf204d4b21bdb86f4ce14",
    ),
    "g0076_outcome": (
        G0076_OUTCOME,
        "374d684459c12e76184dfc1da50e8993b1d4dbda474c13ea4319665997570bfb",
    ),
    "g0076_kernel": (
        G0076_KERNEL,
        "53b2e58fb6737132d2da4fab8980f98977e04f06f57853234e55f915fd277170",
    ),
    "g0077_producer": (
        G0077_SCRIPT,
        "278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279",
    ),
    "g0077_modular": (
        G0077_MODULAR,
        "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4",
    ),
    "g0078_producer": (
        G0078_SCRIPT,
        "6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229",
    ),
    "g0078_exact": (
        G0078_EXACT,
        "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96",
    ),
    "full_old_matrix_npy": (
        FULL_OLD_MATRIX,
        "5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f",
    ),
    "environment_manifest": (
        ENVIRONMENT_MANIFEST,
        "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c",
    ),
}

EXPECTED_G0073_PREFLIGHT_SCIENCE = (
    "d440ecf8b5119f1c6b8f872444cb364995d1f4043513519d57fbbd3eeb3517b8"
)
EXPECTED_G0078_EXACT_SCIENCE = (
    "0bb1a524503359529bb592030f220be86d88756b797e55c4be04c031852bd573"
)
EXPECTED_FULL_OLD_RAW_SHA256 = (
    "41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095"
)

# The first commit is deliberately preflight-only.  The registered
# implementation flips this only before its final source hash is written into
# a separate preregistration artifact.  Source never embeds the prereg hash:
# doing so would create a circular hash dependency.
REGISTERED_IMPLEMENTATION_COMPLETE = False


class GateError(RuntimeError):
    """A frozen binding, semantic invariant, or experiment rail failed."""


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


def raw_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def read_gzip(path: Path) -> dict[str, Any]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise GateError(f"expected JSON object: {path}")
    return value


def write_gzip(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped:
            zipped.write(canonical_bytes(value))


def load_source_module(path: Path, expected: str, name: str) -> ModuleType:
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != expected:
        raise GateError(f"source binding drift: {path}")
    module = ModuleType(name)
    module.__file__ = str(path)
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def verify_bindings(*, hash_full_matrix: bool) -> dict[str, dict[str, object]]:
    report: dict[str, dict[str, object]] = {}
    for name, (path, expected) in EXPECTED_BINDINGS.items():
        if name == "full_old_matrix_npy" and not hash_full_matrix:
            observed = expected
        else:
            observed = sha256_path(path)
        if observed != expected:
            raise GateError(f"binding drift for {name}: {observed} != {expected}")
        report[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
            "hash_replayed": name != "full_old_matrix_npy" or hash_full_matrix,
        }
    g73 = read_gzip(G0073_PREFLIGHT)
    g78 = read_gzip(G0078_EXACT)
    if g73.get("scientific_payload_sha256") != EXPECTED_G0073_PREFLIGHT_SCIENCE:
        raise GateError("G-0073 preflight scientific payload drift")
    if g78.get("scientific_payload_sha256") != EXPECTED_G0078_EXACT_SCIENCE:
        raise GateError("G-0078 exact scientific payload drift")
    return report


@dataclass(frozen=True)
class Family:
    bases: list[object]
    old_seeds: list[object]
    old_representatives: list[object]
    new_seeds: list[object]
    new_representatives: list[object]
    old_certificates: frozenset[bytes]
    new_certificates: frozenset[bytes]
    new_orbit_report: dict[str, object]


def enumerate_same_component_seeds(g73: ModuleType, bases: Sequence[object]) -> list[object]:
    seeds: list[object] = []
    for base in bases:
        component_of = {
            vertex: component_index
            for component_index, component in enumerate(base.components)
            for vertex in component
        }
        for anchor in range(1, OLD_LABELS + 1):
            component = base.components[component_of[anchor]]
            for auxiliary in component:
                if auxiliary == anchor:
                    continue
                for orientation in (0, 1):
                    seeds.append(
                        g73.Seed(
                            len(seeds),
                            base.position,
                            base.term_index,
                            g73.Expression(
                                base.left,
                                base.right,
                                anchor,
                                auxiliary,
                                N,
                                orientation,
                            ),
                        )
                    )
    if len(seeds) != NEW_RAW_COUNT:
        raise GateError(f"same-component raw census drift: {len(seeds)}")
    if len({seed.key for seed in seeds}) != NEW_RAW_COUNT:
        raise GateError("same-component raw seed keys are not unique")
    return seeds


def build_new_orbits(
    g73: ModuleType,
    seeds: Sequence[object],
    *,
    verify_vf2: bool,
) -> tuple[list[object], frozenset[bytes], dict[str, object]]:
    groups: dict[bytes, list[object]] = defaultdict(list)
    sequence: list[str] = []
    for seed in seeds:
        certificate = g73.orbit_certificate(seed.expression)
        groups[certificate].append(seed)
        sequence.append(hashlib.sha256(certificate).hexdigest())
    ordered = sorted(groups, key=lambda value: hashlib.sha256(value).hexdigest())
    representatives = [
        min(groups[certificate], key=lambda seed: canonical_bytes(g73.seed_record(seed)))
        for certificate in ordered
    ]
    if len(representatives) != NEW_ORBIT_COUNT:
        raise GateError(f"same-component orbit census drift: {len(representatives)}")

    vf2_checks = 0
    if verify_vf2:
        node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
        for certificate in ordered:
            reference = g73.networkx_graph(groups[certificate][0].expression)
            for seed in groups[certificate][1:]:
                if not nx.is_isomorphic(
                    reference,
                    g73.networkx_graph(seed.expression),
                    node_match=node_match,
                ):
                    raise GateError("new pynauty orbit merge failed independent VF2")
                vf2_checks += 1

    manifest = [
        {
            "certificate_sha256": hashlib.sha256(certificate).hexdigest(),
            "raw_seed_count": len(groups[certificate]),
            "representative": g73.seed_record(representatives[index]),
        }
        for index, certificate in enumerate(ordered)
    ]
    report = {
        "raw_seed_count": len(seeds),
        "orbit_count": len(representatives),
        "class_size_histogram": {
            str(size): count
            for size, count in sorted(Counter(map(len, groups.values())).items())
        },
        "orbit_sequence_sha256": canonical_sha256(sequence),
        "orbit_manifest_sha256": canonical_sha256(manifest),
        "representative_manifest_sha256": canonical_sha256(
            [g73.seed_record(seed) for seed in representatives]
        ),
        "vf2_nonrepresentative_checks": vf2_checks,
        "vf2_complete": verify_vf2,
    }
    return representatives, frozenset(groups), report


def reconstruct_family(g75: ModuleType, *, verify_vf2: bool) -> Family:
    g73 = g75.G73
    bases = g73.load_bases()
    old_seeds = g73.enumerate_seeds(bases)
    old_representatives, old_report = g73.build_orbits(
        old_seeds, verify_vf2=verify_vf2
    )
    if len(bases) != BASE_COUNT or len(old_seeds) != OLD_RAW_COUNT:
        raise GateError("frozen G-0073 base/raw census drift")
    if len(old_representatives) != OLD_ORBIT_COUNT:
        raise GateError("frozen G-0073 orbit census drift")
    expected_old = (
        g73.EXPECTED_ORBIT_MANIFEST_SHA256,
        g73.EXPECTED_REPRESENTATIVE_MANIFEST_SHA256,
    )
    observed_old = (
        old_report.get("orbit_manifest_sha256"),
        old_report.get("representative_manifest_sha256"),
    )
    if observed_old != expected_old:
        raise GateError(f"G-0073 orbit reconstruction drift: {observed_old}")

    new_seeds = enumerate_same_component_seeds(g73, bases)
    new_representatives, new_certificates, new_report = build_new_orbits(
        g73, new_seeds, verify_vf2=verify_vf2
    )
    old_certificates = frozenset(
        g73.orbit_certificate(seed.expression) for seed in old_representatives
    )
    intersection = old_certificates & new_certificates
    if intersection:
        raise GateError(f"old/new orbit families overlap in {len(intersection)} classes")
    if len(old_certificates | new_certificates) != UNION_ORBIT_COUNT:
        raise GateError("combined orbit-union census drift")
    return Family(
        bases=list(bases),
        old_seeds=list(old_seeds),
        old_representatives=list(old_representatives),
        new_seeds=list(new_seeds),
        new_representatives=list(new_representatives),
        old_certificates=old_certificates,
        new_certificates=new_certificates,
        new_orbit_report=new_report,
    )


def deterministic_indices(total: int, count: int, label: str) -> list[int]:
    selected: set[int] = set()
    counter = 0
    while len(selected) < count:
        digest = hashlib.sha256(f"{label};{counter}\n".encode()).digest()
        selected.add(int.from_bytes(digest[:8], "big") % total)
        counter += 1
    return sorted(selected)


def raw_row_levels(g75: ModuleType, raw_row: int) -> np.ndarray:
    if not 0 <= raw_row < TOTAL_ROWS:
        raise GateError(f"raw row outside registered system: {raw_row}")
    g74 = g75.G74
    g73 = g75.G73
    if raw_row < g75.PANEL_COUNT * len(g75.positive_profiles()):
        profiles = g75.positive_profiles()
        panel, offset = divmod(raw_row, len(profiles))
        ratio = g75.panel_ratios()[panel]
        codes = g73.assignments(profiles[offset])
        return np.asarray((0, ratio[0], ratio[1], g75.DENOMINATOR), dtype=np.int16)[codes]
    offset = raw_row - g75.PANEL_COUNT * len(g75.positive_profiles())
    if offset < len(g73.all_profiles()):
        return g73.assignments(g73.all_profiles()[offset])
    farey_offset = offset - len(g73.all_profiles())
    profiles3 = g74.all_three_profiles()
    ratio_index, profile_index = divmod(farey_offset, len(profiles3))
    numerator, denominator = g74.FAREY_F6[ratio_index]
    return g74.three_assignments(profiles3[profile_index], numerator, denominator)


def evaluate_representatives_on_rows(
    g75: ModuleType,
    bases: Sequence[object],
    representatives: Sequence[object],
    raw_rows: Sequence[int],
) -> np.ndarray:
    g73 = g75.G73
    grouped = g73.group_by_base(representatives, len(bases))
    matrix = np.zeros((len(raw_rows), len(representatives)), dtype=np.int64)
    for output_row, raw_row in enumerate(raw_rows):
        levels = raw_row_levels(g75, int(raw_row))
        for base in bases:
            entries = grouped[base.position]
            if not entries:
                continue
            columns = np.asarray([column for column, _seed in entries], dtype=np.intp)
            values = g73.evaluate_seed_block(
                base, [seed for _column, seed in entries], levels
            )
            matrix[output_row, columns] = values.sum(axis=1, dtype=np.int64)
    return matrix


def load_exact_separator() -> dict[str, object]:
    report = read_gzip(G0078_EXACT)
    payload = report.get("scientific_payload")
    if not isinstance(payload, dict):
        raise GateError("G-0078 exact artifact lacks scientific payload")
    rows = list(map(int, payload.get("selected_raw_rows", [])))
    divisors = list(map(int, payload.get("selected_raw_row_divisors", [])))
    numerators = list(map(int, payload.get("integer_dual_numerators", [])))
    failing_row = int(payload.get("failing_raw_row", -1))
    failing_divisor = int(payload.get("failing_raw_row_divisor", 0))
    failing_weight = int(payload.get("integer_failing_row_weight", 0))
    if (
        len(rows) != 229
        or len(divisors) != 229
        or len(numerators) != 229
        or len(set(rows)) != 229
        or failing_row in rows
        or min(divisors, default=0) <= 0
        or failing_divisor <= 0
        or not payload.get("all_A_columns_annihilated_exactly")
        or not payload.get("exact_target_pairing_nonzero")
    ):
        raise GateError("malformed G-0078 exact separator")
    return {
        "rows": rows + [failing_row],
        "selected_rows": rows,
        "selected_divisors": divisors,
        "selected_numerators": numerators,
        "failing_row": failing_row,
        "failing_divisor": failing_divisor,
        "failing_weight": failing_weight,
    }


def exact_prices(values: np.ndarray, separator: dict[str, object]) -> list[Fraction]:
    rows = separator["selected_rows"]
    divisors = separator["selected_divisors"]
    numerators = separator["selected_numerators"]
    if not isinstance(rows, list) or not isinstance(divisors, list) or not isinstance(numerators, list):
        raise GateError("separator lists malformed")
    if values.shape[0] != len(rows) + 1:
        raise GateError("price matrix row census drift")
    prices: list[Fraction] = []
    for column in range(values.shape[1]):
        value = sum(
            Fraction(int(numerators[index]) * int(values[index, column]), int(divisors[index]))
            for index in range(len(rows))
        )
        value += Fraction(
            int(separator["failing_weight"]) * int(values[-1, column]),
            int(separator["failing_divisor"]),
        )
        prices.append(value)
    return prices


def preflight_price_controls(g75: ModuleType, family: Family) -> dict[str, object]:
    """Cross-check frozen columns without inspecting any new-family price.

    Actual new-family prices are a registered scientific outcome and are
    therefore forbidden in preflight.  The hostile arm mutates each frozen
    control column at one certificate row, exercising the exact functional
    with a planted nonzero whose value is known before any new atom is read.
    """
    separator = load_exact_separator()
    raw_rows = list(map(int, separator["rows"]))
    old_indices = deterministic_indices(
        len(family.old_representatives),
        PRICE_ZERO_CONTROLS,
        "max11-g0079-old-zero-price-controls-v1",
    )
    old_representatives = [family.old_representatives[index] for index in old_indices]
    old_values = evaluate_representatives_on_rows(
        g75, family.bases, old_representatives, raw_rows
    )

    old_full = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
    if old_full.shape != (TOTAL_ROWS, OLD_COLUMNS + 1) or old_full.dtype != np.dtype("<i8"):
        raise GateError("frozen old matrix shape/dtype drift")
    expected_old = np.ascontiguousarray(
        old_full[np.ix_(np.asarray(raw_rows, dtype=np.intp), np.asarray(old_indices, dtype=np.intp))]
    )
    if not np.array_equal(old_values, expected_old):
        mismatch = np.argwhere(old_values != expected_old)[0]
        raise GateError(
            f"cross-family old semantic reconstruction mismatch at {tuple(map(int, mismatch))}"
        )
    old_prices = exact_prices(old_values, separator)
    if any(old_prices):
        raise GateError("a sampled frozen G-0073 column has nonzero exact G-0078 price")
    hostile_values = old_values.copy()
    hostile_expected: list[Fraction] = []
    numerators = list(map(int, separator["selected_numerators"]))
    divisors = list(map(int, separator["selected_divisors"]))
    for column in range(PRICE_NONZERO_CONTROLS):
        certificate_row = column % len(numerators)
        hostile_values[certificate_row, column] += divisors[certificate_row]
        hostile_expected.append(Fraction(numerators[certificate_row]))
    hostile_prices = exact_prices(hostile_values, separator)
    if hostile_prices != hostile_expected or any(value == 0 for value in hostile_prices):
        raise GateError("planted nonzero exact-price controls failed")
    return {
        "separator_artifact_sha256": EXPECTED_BINDINGS["g0078_exact"][1],
        "separator_scientific_payload_sha256": EXPECTED_G0078_EXACT_SCIENCE,
        "raw_row_count": len(raw_rows),
        "raw_rows_sha256": canonical_sha256(raw_rows),
        "old_zero_control_count": len(old_indices),
        "old_zero_indices": old_indices,
        "old_zero_indices_sha256": canonical_sha256(old_indices),
        "old_values_int64_c_sha256": raw_sha256(old_values),
        "old_cross_reconstruction_exact": True,
        "old_exact_prices_all_zero": True,
        "synthetic_nonzero_control_count": len(hostile_expected),
        "synthetic_mutation": (
            "for control column j, add its selected-row primitive divisor at "
            "certificate support row j"
        ),
        "synthetic_nonzero_exact_prices": [str(value) for value in hostile_prices],
        "synthetic_nonzero_exact_prices_sha256": canonical_sha256(
            [str(value) for value in hostile_prices]
        ),
        "actual_new_family_columns_priced": 0,
        "interpretation": (
            "The old zeros cross-check frozen semantics and the planted mutations exercise "
            "the nonzero path.  No actual new-family price is inspected before registration."
        ),
    }


def semantic_segment_controls(g75: ModuleType, family: Family) -> dict[str, object]:
    """Cross the optimized evaluator over early, late, and G-0074 row segments."""

    sentinel_rows = [0, 119, 15_240, 15_359, 15_360, 15_723, 15_724, 16_737]
    old_indices = deterministic_indices(
        len(family.old_representatives),
        16,
        "max11-g0079-segment-old-cross-controls-v1",
    )
    old_representatives = [family.old_representatives[index] for index in old_indices]
    reconstructed = evaluate_representatives_on_rows(
        g75, family.bases, old_representatives, sentinel_rows
    )
    old_full = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
    frozen = np.ascontiguousarray(
        old_full[
            np.ix_(
                np.asarray(sentinel_rows, dtype=np.intp),
                np.asarray(old_indices, dtype=np.intp),
            )
        ]
    )
    if not np.array_equal(reconstructed, frozen):
        mismatch = np.argwhere(reconstructed != frozen)[0]
        raise GateError(
            f"segment sentinel old reconstruction mismatch at {tuple(map(int, mismatch))}"
        )

    g73 = g75.G73
    class_sizes = Counter(
        g73.orbit_certificate(seed.expression) for seed in family.new_seeds
    )
    strata: dict[tuple[tuple[int, int], int, int], tuple[int, object]] = {}
    for index, seed in enumerate(family.new_representatives):
        base = family.bases[seed.base_position]
        topology = tuple(sorted(map(len, base.components)))
        certificate = g73.orbit_certificate(seed.expression)
        key = (topology, int(seed.expression.orientation), int(class_sizes[certificate]))
        strata.setdefault(key, (index, seed))
    literal_checks = 0
    serialized_strata: list[dict[str, object]] = []
    for key in sorted(strata):
        index, seed = strata[key]
        base = family.bases[seed.base_position]
        for raw_row in sentinel_rows:
            levels = raw_row_levels(g75, raw_row)
            optimized = int(
                g73.evaluate_seed_block(base, [seed], levels)[0].sum(dtype=np.int64)
            )
            literal = sum(
                int(g73.evaluate_expression(seed.expression, levels[:, point]))
                for point in range(levels.shape[1])
            )
            if optimized != literal:
                raise GateError(
                    f"new optimized/literal mismatch at rep={index}, raw_row={raw_row}"
                )
            literal_checks += 1
        serialized_strata.append(
            {
                "topology": list(key[0]),
                "orientation": key[1],
                "orbit_class_size": key[2],
                "local_new_index": index,
                "global_column_id": GLOBAL_NEW_START + index,
            }
        )
    return {
        "sentinel_raw_rows": sentinel_rows,
        "sentinel_raw_rows_sha256": canonical_sha256(sentinel_rows),
        "segments_covered": [
            "G-0075 panel 0",
            "G-0075 panel 127",
            "G-0075/G-0074 boundary",
            "G-0073 baseline/G-0074 Farey boundary",
            "final G-0074 Farey row",
        ],
        "old_column_count": len(old_indices),
        "old_column_indices": old_indices,
        "old_cross_reconstruction_int64_c_sha256": raw_sha256(reconstructed),
        "old_cross_reconstruction_exact": True,
        "new_stratum_count": len(serialized_strata),
        "new_strata": serialized_strata,
        "new_strata_sha256": canonical_sha256(serialized_strata),
        "new_optimized_literal_checks": literal_checks,
        "new_optimized_literal_exact": True,
    }


def numpy_rref_pivots(rows: np.ndarray) -> list[int]:
    pivots: list[int] = []
    search = 0
    for row in rows:
        support = np.flatnonzero(row[search:])
        if support.size == 0:
            raise GateError("archived modular kernel row lacks a pivot")
        pivot = search + int(support[0])
        if int(row[pivot]) != 1:
            raise GateError("archived modular kernel pivot is not normalized")
        pivots.append(pivot)
        search = pivot + 1
    if pivots != sorted(set(pivots)):
        raise GateError("archived modular kernel pivots are not canonical")
    return pivots


def verify_old_basis_contract() -> dict[str, object]:
    """Verify the single-prime P/R contract before any new-family Schur use."""

    modular = read_gzip(G0077_MODULAR)
    outcome = read_gzip(G0076_OUTCOME)
    resolution = outcome.get("modular_resolution")
    if not isinstance(resolution, dict):
        raise GateError("G-0076 modular resolution missing")
    kernel_replay = resolution.get("kernel_replay")
    if not isinstance(kernel_replay, dict):
        raise GateError("G-0076 kernel replay receipt missing")
    if (
        modular.get("prime") != PRIME
        or modular.get("rank_A") != 6_876
        or modular.get("rows") != TOTAL_ROWS
        or modular.get("A_columns") != OLD_COLUMNS
        or resolution.get("prime") != PRIME
        or resolution.get("rank_A") != 6_876
        or resolution.get("nullity_A") != OLD_COLUMNS - 6_876
        or kernel_replay.get("all_rows") != TOTAL_ROWS
        or kernel_replay.get("all_augmented_columns") != OLD_COLUMNS + 1
        or kernel_replay.get("all_kernel_vectors") != OLD_COLUMNS - 6_876
        or kernel_replay.get("zero_mod_prime") is not True
        or resolution.get("full_input_augmented_int64_c_sha256")
        != EXPECTED_FULL_OLD_RAW_SHA256
    ):
        raise GateError("G-0076/G-0077 old-rank contract drift")

    with gzip.open(G0076_KERNEL, "rb") as source:
        kernel = np.load(source, allow_pickle=False)
    if (
        kernel.shape != (OLD_COLUMNS - 6_876, OLD_COLUMNS + 1)
        or kernel.dtype != np.uint32
        or np.any(kernel[:, -1])
    ):
        raise GateError("archived G-0076 A-kernel shape/target drift")
    pivots = numpy_rref_pivots(kernel[:, :-1])
    basis_columns = np.asarray(modular.get("basis_columns"), dtype=np.int64)
    expected_basis_columns = np.asarray(
        [column for column in range(OLD_COLUMNS) if column not in set(pivots)],
        dtype=np.int64,
    )
    basis_rows = np.asarray(modular.get("basis_rows"), dtype=np.int64)
    if (
        basis_columns.shape != (6_876,)
        or basis_rows.shape != (6_876,)
        or not np.array_equal(basis_columns, expected_basis_columns)
        or len(set(map(int, basis_rows))) != 6_876
    ):
        raise GateError("G-0077 P/R basis reconstruction drift")

    full = np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)
    raw_square = np.ascontiguousarray(
        full[np.ix_(basis_rows.astype(np.intp), basis_columns.astype(np.intp))]
    )
    square_field, square_reduced = to_nmod(raw_square, PRIME)
    square_rank = int(square_field.rank())
    if square_rank != 6_876:
        raise GateError("raw G-0077 B=A[R,P] is singular at the registered prime")
    report = {
        "prime": PRIME,
        "basis_rows_sha256": canonical_sha256(basis_rows.astype(int).tolist()),
        "basis_columns_sha256": canonical_sha256(basis_columns.astype(int).tolist()),
        "raw_basis_square_int64_c_sha256": raw_sha256(raw_square),
        "raw_basis_square_rank": square_rank,
        "raw_basis_square_nonsingular": True,
        "archived_kernel_rows": kernel.shape[0],
        "archived_kernel_rref_pivots_sha256": canonical_sha256(pivots),
        "archived_all_row_kernel_replay_bound": True,
        "rank_A": 6_876,
        "rank_argument": (
            "raw B nonsingularity gives rank(A)>=6876; the 1231 independent canonical "
            "kernel rows, whose all-16738-row replay is hash-bound above, give rank(A)<=6876"
        ),
        "all_old_columns_have_zero_quotient": True,
        "old_span_argument": (
            "the RREF kernel pivot columns are exactly the complement of P, and each pivot "
            "relation expresses that old column in P on all frozen rows"
        ),
        "additional_prime_policy": (
            "no additional prime may reuse this P/R contract; it must derive and replay its own"
        ),
    }
    del kernel, raw_square, square_field, square_reduced
    return report


def performance_benchmark() -> dict[str, object]:
    """Measure the kernels used by the rank-adaptive registered design.

    The benchmark is diagnostic and host-specific, so its timings stay
    outside the scientific payload.  Exact operation counts and the rejection
    of the dense Schur design are stable parts of the preregistered subject.
    """

    rng = np.random.default_rng(79_0079)
    benchmark_rank = 192
    raw = rng.integers(0, PRIME, size=(benchmark_rank, benchmark_rank), dtype=np.uint32)
    raw[np.diag_indices(benchmark_rank)] = (
        raw[np.diag_indices(benchmark_rank)].astype(np.uint64) + 1
    ) % PRIME
    field = nmod_mat(
        benchmark_rank,
        benchmark_rank,
        memoryview(np.ascontiguousarray(raw).ravel()),
        PRIME,
    )
    identity = nmod_mat(benchmark_rank, benchmark_rank, PRIME)
    for index in range(benchmark_rank):
        identity[index, index] = 1
    begun = time.perf_counter()
    try:
        inverse = field.inv()
    except Exception:
        # A deterministic random square can exceptionally be singular.  The
        # diagonal-shift search is deterministic and does not touch subject data.
        inverse = None
        for shift in range(2, 32):
            shifted = raw.copy()
            diagonal = shifted[np.diag_indices(benchmark_rank)].astype(np.uint64)
            shifted[np.diag_indices(benchmark_rank)] = (diagonal + shift) % PRIME
            field = nmod_mat(
                benchmark_rank,
                benchmark_rank,
                memoryview(np.ascontiguousarray(shifted).ravel()),
                PRIME,
            )
            try:
                inverse = field.inv()
                raw = shifted
                break
            except Exception:
                continue
        if inverse is None:
            raise GateError("could not construct invertible modular benchmark square")
    inverse_seconds = time.perf_counter() - begun
    if field * inverse != identity:
        raise GateError("modular inverse benchmark failed replay")

    price_rows, price_columns = 1024, 4096
    weights = rng.integers(0, PRIME, size=price_rows, dtype=np.int64)
    values = rng.integers(
        0, PRIME, size=(price_rows, price_columns), dtype=np.int64
    )
    begun = time.perf_counter()
    price_checksum = 0
    repetitions = 3
    for _ in range(repetitions):
        price_checksum ^= int(np.sum((weights @ values) % PRIME) % PRIME)
    price_seconds = (time.perf_counter() - begun) / repetitions

    # Exercise the actual FLINT bulk-multiply and rank kernels used by a
    # possible dense fallback.  These sizes are large enough to escape timer
    # noise while remaining a small, non-subject fixture.
    multiply_m, multiply_k, multiply_n = 1024, 768, 2048
    multiply_left = rng.integers(
        0, PRIME, size=(multiply_m, multiply_k), dtype=np.uint32
    )
    multiply_right = rng.integers(
        0, PRIME, size=(multiply_k, multiply_n), dtype=np.uint32
    )
    multiply_left_field = nmod_mat(
        multiply_m,
        multiply_k,
        memoryview(np.ascontiguousarray(multiply_left).ravel()),
        PRIME,
    )
    multiply_right_field = nmod_mat(
        multiply_k,
        multiply_n,
        memoryview(np.ascontiguousarray(multiply_right).ravel()),
        PRIME,
    )
    begun = time.perf_counter()
    multiply_product = multiply_left_field * multiply_right_field
    multiply_seconds = time.perf_counter() - begun
    multiply_checksum = int(multiply_product[0, 0]) ^ int(
        multiply_product[multiply_m - 1, multiply_n - 1]
    )

    rank_rows, rank_columns = 2048, 4096
    rank_array = rng.integers(
        0, PRIME, size=(rank_rows, rank_columns), dtype=np.uint32
    )
    begun = time.perf_counter()
    rank_field = nmod_mat(
        rank_rows,
        rank_columns,
        memoryview(np.ascontiguousarray(rank_array).ravel()),
        PRIME,
    )
    rank_conversion_seconds = time.perf_counter() - begun
    begun = time.perf_counter()
    observed_rank = int(rank_field.rank())
    rank_seconds = time.perf_counter() - begun
    if observed_rank != rank_rows:
        raise GateError("large modular rank benchmark was not full row rank")

    rank = 6_876
    new_columns = NEW_ORBIT_COUNT
    quotient_rows = TOTAL_ROWS - rank
    dense_schur_multiply_adds = quotient_rows * rank * (new_columns + 1)
    dense_schur_entries = quotient_rows * (new_columns + 1)
    dense_schur_new_only_multiply_adds = quotient_rows * rank * new_columns
    dense_rref_scale_units = quotient_rows * quotient_rows * (new_columns + 1)
    price_operations = rank * new_columns
    quotient_batch_operations = CEGIS_MISMATCH_BATCH * rank * (
        rank + new_columns
    )
    maximum_small_rref_scale_units = (
        MAX_CEGIS_ROWS * MAX_CEGIS_ROWS * (new_columns + 1)
    )
    price_rate = (price_rows * price_columns) / max(price_seconds, 1e-9)
    cubic_inverse_projection = inverse_seconds * (rank / benchmark_rank) ** 3
    multiply_rate = (
        multiply_m * multiply_k * multiply_n / max(multiply_seconds, 1e-9)
    )
    rank_rate = (
        rank_rows * rank_rows * rank_columns / max(rank_seconds, 1e-9)
    )
    projected_dense_multiply_seconds = dense_schur_multiply_adds / multiply_rate
    projected_dense_rank_seconds = dense_rref_scale_units / rank_rate
    projected_quotient_batch_seconds = quotient_batch_operations / multiply_rate
    projected_maximum_small_rref_seconds = maximum_small_rref_scale_units / rank_rate
    projected_dense_kernel_seconds = PERFORMANCE_CONSERVATIVE_FACTOR * (
        cubic_inverse_projection
        + projected_dense_multiply_seconds
        + projected_dense_rank_seconds
        + rank_conversion_seconds
        * (dense_schur_entries / (rank_rows * rank_columns))
    )
    new_matrix_bytes = TOTAL_ROWS * new_columns * 8
    basis_values_bytes = rank * new_columns * 4
    inverse_bytes = rank * rank * 4
    return {
        "host": platform.platform(),
        "benchmark_rank": benchmark_rank,
        "modular_inverse_seconds": inverse_seconds,
        "modular_inverse_replay": True,
        "price_kernel_shape": [price_rows, price_columns],
        "price_kernel_seconds": price_seconds,
        "price_kernel_checksum": price_checksum,
        "dense_schur_multiply_adds": dense_schur_multiply_adds,
        "dense_schur_new_only_multiply_adds": dense_schur_new_only_multiply_adds,
        "dense_schur_entries": dense_schur_entries,
        "dense_rref_scale_units": dense_rref_scale_units,
        "dense_schur_design_rejected": True,
        "flint_multiply_shape": [multiply_m, multiply_k, multiply_n],
        "flint_multiply_seconds": multiply_seconds,
        "flint_multiply_checksum": multiply_checksum,
        "flint_multiply_scalar_rate": multiply_rate,
        "flint_rank_shape": [rank_rows, rank_columns],
        "flint_rank_conversion_seconds": rank_conversion_seconds,
        "flint_rank_seconds": rank_seconds,
        "flint_rank": observed_rank,
        "flint_rank_scale_rate": rank_rate,
        "projected_dense_multiply_seconds": projected_dense_multiply_seconds,
        "projected_dense_rank_seconds": projected_dense_rank_seconds,
        "performance_conservative_factor": PERFORMANCE_CONSERVATIVE_FACTOR,
        "projected_dense_kernel_seconds_conservative": projected_dense_kernel_seconds,
        "maximum_authorized_projected_dense_seconds": MAX_PROJECTED_DENSE_SECONDS,
        "dense_fallback_projection_passes_wall_gate": (
            projected_dense_kernel_seconds <= MAX_PROJECTED_DENSE_SECONDS
        ),
        "adaptive_price_operations_per_iteration": price_operations,
        "quotient_batch_operations": quotient_batch_operations,
        "projected_quotient_batch_seconds": projected_quotient_batch_seconds,
        "maximum_small_rref_scale_units": maximum_small_rref_scale_units,
        "projected_maximum_small_rref_seconds": projected_maximum_small_rref_seconds,
        "cubic_initial_inverse_projection_seconds": cubic_inverse_projection,
        "projected_persistent_new_matrix_bytes": new_matrix_bytes,
        "projected_basis_values_bytes": basis_values_bytes,
        "projected_inverse_bytes": inverse_bytes,
        "minimum_projected_peak_bytes": (
            new_matrix_bytes + basis_values_bytes + 4 * inverse_bytes
        ),
        "minimum_available_gib_gate": MINIMUM_AVAILABLE_GIB,
        "minimum_free_disk_gib_gate": MINIMUM_FREE_DISK_GIB,
        "honest_limit": (
            "The initial 6,876-square inversion and semantic generation can scale differently "
            "from these fixtures. Registered execution must benchmark the actual frozen minor "
            "and stop rather than extrapolate through an unmet wall-clock/RAM gate."
        ),
    }


def pivot_columns(rref: nmod_mat, rank: int) -> list[int]:
    pivots: list[int] = []
    search = 0
    for row in range(rank):
        while search < rref.ncols() and not int(rref[row, search]):
            search += 1
        if search >= rref.ncols() or int(rref[row, search]) != 1:
            raise GateError("modular RREF pivot scan failed")
        pivots.append(search)
        search += 1
    return pivots


def to_nmod(array: np.ndarray, prime: int) -> tuple[nmod_mat, np.ndarray]:
    reduced = np.empty(array.shape, dtype=np.uint32)
    np.remainder(array, prime, out=reduced, casting="unsafe")
    return (
        nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime),
        reduced,
    )


def schur_fixture_decision(
    a: np.ndarray,
    b: np.ndarray,
    target: np.ndarray,
    basis_columns: Sequence[int],
    basis_rows: Sequence[int],
    prime: int,
) -> dict[str, object]:
    if a.ndim != 2 or b.ndim != 2 or target.shape != (a.shape[0],):
        raise GateError("malformed Schur fixture")
    p = np.asarray(basis_columns, dtype=np.intp)
    r = np.asarray(basis_rows, dtype=np.intp)
    q = np.asarray([row for row in range(a.shape[0]) if row not in set(map(int, r))], dtype=np.intp)
    minor_field, minor_reduced = to_nmod(np.ascontiguousarray(a[np.ix_(r, p)]), prime)
    rhs = np.ascontiguousarray(np.column_stack((b[r], target[r])))
    rhs_field, rhs_reduced = to_nmod(rhs, prime)
    try:
        coordinates = minor_field.solve(rhs_field)
    except Exception as error:
        raise GateError(f"Schur fixture basis minor is singular: {error}") from error
    aqp_field, aqp_reduced = to_nmod(np.ascontiguousarray(a[np.ix_(q, p)]), prime)
    q_augmented = np.ascontiguousarray(np.column_stack((b[q], target[q])))
    q_field, q_reduced = to_nmod(q_augmented, prime)
    schur = q_field - aqp_field * coordinates
    rref, rank_object = schur.rref()
    rank = int(rank_object)
    pivots = pivot_columns(rref, rank)
    target_coordinate = b.shape[1]
    epsilon = 1 if target_coordinate in pivots else 0
    del (
        minor_field,
        minor_reduced,
        rhs_field,
        rhs_reduced,
        coordinates,
        aqp_field,
        aqp_reduced,
        q_field,
        q_reduced,
        schur,
        rref,
    )
    return {
        "schur_rank_augmented": rank,
        "schur_rank_new_columns": rank - epsilon,
        "target_coordinate": target_coordinate,
        "target_coordinate_is_pivot": bool(epsilon),
        "epsilon": epsilon,
    }


def nmod_to_numpy(matrix: nmod_mat) -> np.ndarray:
    rows, columns = matrix.nrows(), matrix.ncols()
    return np.fromiter(
        (int(matrix[row, column]) for row in range(rows) for column in range(columns)),
        dtype=np.uint32,
        count=rows * columns,
    ).reshape(rows, columns)


def canonical_basic_solution(
    rows: np.ndarray, target: np.ndarray, prime: int
) -> dict[str, object]:
    """Free-zero lexicographic basic solution or target-pivot separation."""

    if rows.ndim != 2 or target.shape != (rows.shape[0],):
        raise GateError("malformed accumulated quotient system")
    augmented = np.ascontiguousarray(np.column_stack((rows, target)))
    field, reduced = to_nmod(augmented, prime)
    rref, rank_object = field.rref()
    rank = int(rank_object)
    pivots = pivot_columns(rref, rank)
    target_coordinate = rows.shape[1]
    if target_coordinate in pivots:
        target_pivot_row = pivots.index(target_coordinate)
        return {
            "decision": "MODULAR_SEPARATION",
            "rank_augmented": rank,
            "rank_columns": rank - 1,
            "target_coordinate": target_coordinate,
            "target_pivot_row": target_pivot_row,
            "pivots": pivots,
            "solution": None,
        }
    solution = np.zeros(rows.shape[1], dtype=np.uint32)
    for row, pivot in enumerate(pivots):
        if pivot >= target_coordinate:
            raise GateError("target-last RREF pivot ordering failed")
        solution[pivot] = int(rref[row, target_coordinate])
    replay = np.remainder(
        rows.astype(np.int64) @ solution.astype(np.int64), prime
    ).astype(np.uint32)
    expected = np.remainder(target, prime).astype(np.uint32)
    if not np.array_equal(replay, expected):
        raise GateError("canonical free-zero basic solution failed replay")
    return {
        "decision": "MODULAR_COMPATIBLE_ON_ACCUMULATED_ROWS",
        "rank_augmented": rank,
        "rank_columns": rank,
        "target_coordinate": target_coordinate,
        "target_pivot_row": None,
        "pivots": pivots,
        "support": np.flatnonzero(solution).astype(int).tolist(),
        "solution": solution,
    }


def quotient_row_fixture(
    a: np.ndarray,
    c: np.ndarray,
    target: np.ndarray,
    basis_columns: Sequence[int],
    basis_rows: Sequence[int],
    raw_row: int,
    prime: int,
) -> tuple[np.ndarray, int, np.ndarray]:
    p = np.asarray(basis_columns, dtype=np.intp)
    r = np.asarray(basis_rows, dtype=np.intp)
    minor_field, minor_reduced = to_nmod(np.ascontiguousarray(a[np.ix_(r, p)]), prime)
    row_field, row_reduced = to_nmod(
        np.ascontiguousarray(a[raw_row, p]).reshape(-1, 1), prime
    )
    lam_column = minor_field.transpose().solve(row_field)
    lam = nmod_to_numpy(lam_column).reshape(-1).astype(np.int64)
    c_r = np.remainder(c[r], prime).astype(np.int64)
    q = np.remainder(c[raw_row].astype(np.int64) - lam @ c_r, prime).astype(np.uint32)
    t = int(
        (
            int(target[raw_row])
            - int(lam @ np.remainder(target[r], prime).astype(np.int64))
        )
        % prime
    )
    del minor_field, minor_reduced, row_field, row_reduced, lam_column
    return q, t, lam.astype(np.uint32)


def primitive_integer_equation(
    coefficients: Sequence[Fraction], target: Fraction
) -> dict[str, object]:
    """Clear all denominators once; never divide coordinatewise modulo p."""

    denominator_lcm = 1
    for value in [*coefficients, target]:
        denominator_lcm = lcm(denominator_lcm, value.denominator)
    integers = [
        value.numerator * (denominator_lcm // value.denominator)
        for value in coefficients
    ]
    integer_target = target.numerator * (denominator_lcm // target.denominator)
    common = 0
    for value in [*integers, integer_target]:
        common = gcd(common, abs(value))
    if common == 0:
        common = 1
    integers = [value // common for value in integers]
    integer_target //= common
    first_nonzero = next((value for value in [*integers, integer_target] if value), 1)
    if first_nonzero < 0:
        integers = [-value for value in integers]
        integer_target = -integer_target
    for rational, integer in zip(coefficients, integers, strict=True):
        if Fraction(integer * common, denominator_lcm) != rational:
            raise GateError("LCM-cleared coefficient failed exact replay")
    if Fraction(integer_target * common, denominator_lcm) != target:
        raise GateError("LCM-cleared target failed exact replay")
    return {
        "denominator_lcm": denominator_lcm,
        "primitive_gcd": common,
        "integer_coefficients": integers,
        "integer_target": integer_target,
        "coordinatewise_modular_division_used": False,
    }


def run_small_controls(g75: ModuleType, family: Family | None) -> dict[str, object]:
    a = np.asarray([[1], [0], [1]], dtype=np.int64)
    b = np.asarray([[0], [1], [1]], dtype=np.int64)
    member = schur_fixture_decision(
        a, b, np.asarray([1, 2, 3], dtype=np.int64), [0], [0], 101
    )
    nonmember = schur_fixture_decision(
        a, b, np.asarray([1, 2, 4], dtype=np.int64), [0], [0], 101
    )
    if member["epsilon"] != 0 or member["target_coordinate_is_pivot"]:
        raise GateError("modular Schur member fixture failed")
    if nonmember["epsilon"] != 1 or not nonmember["target_coordinate_is_pivot"]:
        raise GateError("modular Schur nonmember fixture failed")

    member_target = np.asarray([1, 2, 3], dtype=np.int64)
    q0, t0, _lambda0 = quotient_row_fixture(
        a, b, member_target, [0], [0], 1, 101
    )
    basic = canonical_basic_solution(
        q0.reshape(1, -1), np.asarray([t0], dtype=np.int64), 101
    )
    if basic["decision"] != "MODULAR_COMPATIBLE_ON_ACCUMULATED_ROWS":
        raise GateError("target-last free-zero member fixture failed")
    coefficient = np.asarray(basic["solution"], dtype=np.int64)
    minor = int(a[0, 0]) % 101
    old_coordinate = (
        int(member_target[0]) - int(b[0] @ coefficient)
    ) * pow(minor, -1, 101) % 101
    replay = np.remainder(
        a[:, 0].astype(np.int64) * old_coordinate + b.astype(np.int64) @ coefficient,
        101,
    )
    if not np.array_equal(replay, member_target % 101):
        raise GateError("q/t fixture did not imply full member replay")

    nonmember_target = np.asarray([1, 2, 4], dtype=np.int64)
    first_q, first_t, first_lambda = quotient_row_fixture(
        a, b, nonmember_target, [0], [0], 1, 101
    )
    first_system = canonical_basic_solution(
        first_q.reshape(1, -1), np.asarray([first_t], dtype=np.int64), 101
    )
    first_solution = np.asarray(first_system["solution"], dtype=np.int64)
    first_old_coordinate = (
        int(nonmember_target[0]) - int(b[0] @ first_solution)
    ) * pow(minor, -1, 101) % 101
    residual = np.remainder(
        nonmember_target
        - a[:, 0].astype(np.int64) * first_old_coordinate
        - b.astype(np.int64) @ first_solution,
        101,
    )
    mismatch_rows = np.flatnonzero(residual).astype(int).tolist()
    if mismatch_rows != [2]:
        raise GateError("first-mismatch fixture drift")
    second_q, second_t, second_lambda = quotient_row_fixture(
        a, b, nonmember_target, [0], [0], mismatch_rows[0], 101
    )
    accumulated = np.vstack((first_q, second_q))
    accumulated_target = np.asarray([first_t, second_t], dtype=np.int64)
    before_augmented_rank = int(
        nmod_mat(np.column_stack((first_q.reshape(1, -1), [first_t])).tolist(), 101).rank()
    )
    after_augmented_rank = int(
        nmod_mat(np.column_stack((accumulated, accumulated_target)).tolist(), 101).rank()
    )
    separated = canonical_basic_solution(accumulated, accumulated_target, 101)
    if (
        after_augmented_rank != before_augmented_rank + 1
        or separated["decision"] != "MODULAR_SEPARATION"
    ):
        raise GateError("violated quotient row did not raise augmented rank")
    if len(set([1, *mismatch_rows])) != 2:
        raise GateError("CEGIS row-cycle control failed")

    q_transpose = nmod_mat(accumulated.T.tolist(), 101)
    left_nullspace, left_nullity_object = q_transpose.nullspace()
    left_nullity = int(left_nullity_object)
    separator_lambda: np.ndarray | None = None
    for column in range(left_nullity):
        candidate = np.fromiter(
            (int(left_nullspace[row, column]) for row in range(accumulated.shape[0])),
            dtype=np.int64,
            count=accumulated.shape[0],
        )
        if int(candidate @ accumulated_target) % 101:
            separator_lambda = candidate
            break
    if separator_lambda is None:
        raise GateError("target-pivot fixture did not yield a left separator")
    raw_quotient_functionals = np.zeros((2, a.shape[0]), dtype=np.int64)
    for index, (raw_row, lam) in enumerate(
        ((1, first_lambda), (2, second_lambda))
    ):
        raw_quotient_functionals[index, raw_row] = 1
        raw_quotient_functionals[index, 0] = -int(lam[0])
    raw_separator = np.remainder(
        separator_lambda @ raw_quotient_functionals, 101
    ).astype(np.int64)
    if (
        np.any(np.remainder(raw_separator @ a, 101))
        or np.any(np.remainder(raw_separator @ b, 101))
        or int(raw_separator @ nonmember_target) % 101 == 0
    ):
        raise GateError("quotient separator failed raw A/C/target mapping replay")

    target_order_mutant = np.column_stack((accumulated_target, accumulated))
    if np.array_equal(
        target_order_mutant,
        np.column_stack((accumulated, accumulated_target)),
    ):
        raise GateError("target-first column-order mutant was not detected")

    lcm_control = primitive_integer_equation(
        [Fraction(1, 2), Fraction(-2, 3)], Fraction(5, 6)
    )
    if (
        lcm_control["denominator_lcm"] != 6
        or lcm_control["integer_coefficients"] != [3, -4]
        or lcm_control["integer_target"] != 5
    ):
        raise GateError("K=1 LCM clearing control failed")

    bases = g75.G73.load_bases() if family is None else family.bases
    topology = Counter(tuple(sorted(map(len, base.components))) for base in bases)
    expected_topology = {(2, 8): 168, (3, 7): 39, (4, 6): 32, (5, 5): 13}
    if dict(topology) != expected_topology:
        raise GateError("base component topology drift")
    expected_by_topology = {
        "2+8": 168 * 2 * (2 * 1 + 8 * 7),
        "3+7": 39 * 2 * (3 * 2 + 7 * 6),
        "4+6": 32 * 2 * (4 * 3 + 6 * 5),
        "5+5": 13 * 2 * (5 * 4 + 5 * 4),
    }
    if sum(expected_by_topology.values()) != NEW_RAW_COUNT:
        raise GateError("closed-form same-component census failed")

    controls: dict[str, object] = {
        "component_topology": {
            f"{first}+{second}": count
            for (first, second), count in sorted(topology.items())
        },
        "same_component_raw_count_by_topology": expected_by_topology,
        "same_component_raw_count": NEW_RAW_COUNT,
        "modular_schur_member_fixture": member,
        "modular_schur_nonmember_fixture": nonmember,
        "quotient_row_target_identity_replay": True,
        "target_last_lex_rref_free_zero": True,
        "violated_row_strict_augmented_rank_gain": True,
        "cegis_no_row_cycle": True,
        "quotient_separator_raw_mapping_replay": True,
        "target_first_order_mutant_rejected": True,
        "k1_lcm_clearing_control": lcm_control,
        "target_coordinate_decision_logic": (
            "epsilon=1 iff the final target coordinate is a pivot of the Schur-augmented RREF"
        ),
        "modular_results_are_discovery_only": True,
    }
    if family is None:
        return controls

    g73 = g75.G73
    if len(family.new_seeds[::2]) != NEW_RAW_COUNT // 2:
        raise GateError("orientation-deletion mutant did not halve raw census")
    first = family.new_seeds[0]
    base = family.bases[first.base_position]
    component_of = {
        vertex: component_index
        for component_index, component in enumerate(base.components)
        for vertex in component
    }
    opposite_auxiliary = base.components[1 - component_of[first.expression.anchor]][0]
    cross_mutant = g73.Expression(
        first.expression.left,
        first.expression.right,
        first.expression.anchor,
        opposite_auxiliary,
        first.expression.new_label,
        first.expression.orientation,
    )
    if g73.orbit_certificate(cross_mutant) not in family.old_certificates:
        raise GateError("cross-component mutant did not land in G-0073")
    if g73.orbit_certificate(first.expression) not in family.new_certificates:
        raise GateError("same-component control seed missing from new family")

    support_checks = 0
    facet_checks = 0
    for seed in family.new_representatives:
        expression = seed.expression
        labels = {
            *[vertex for edge in expression.left + expression.right for vertex in edge],
            expression.anchor,
            expression.auxiliary,
            expression.new_label,
        }
        if labels != set(range(1, N + 1)):
            raise GateError("new orbit representative lost full support")
        component = base.components[0]  # overwritten below through the actual base
        actual_base = family.bases[seed.base_position]
        component = next(
            item for item in actual_base.components if expression.anchor in item
        )
        if expression.auxiliary not in component or expression.auxiliary == expression.anchor:
            raise GateError("new representative violates same-component predicate")
        doubled = [0] * N
        leaves = [0] * N
        doubled[expression.anchor - 1] = 2
        leaves[expression.auxiliary - 1] = 1
        leaves[N - 1] = 1
        if not (
            sum(doubled) == sum(leaves) == 2
            and doubled[N - 1] == 0
            and leaves[N - 1] == 1
        ):
            raise GateError("facet-11 endpoint exposure control failed")
        support_checks += 1
        facet_checks += 1
    controls.update(
        {
            "orientation_deletion_mutant_raw_count": len(family.new_seeds[::2]),
            "orientation_deletion_mutant_rejected": True,
            "opposite_component_mutant_lands_in_g0073": True,
            "all_new_orbit_representatives_full_support": support_checks,
            "all_new_orbit_representatives_facet_11_exposure": facet_checks,
            "old_new_orbit_disjointness": True,
            "combined_orbit_count": UNION_ORBIT_COUNT,
        }
    )
    return controls


def build_preflight(*, verify_vf2: bool) -> dict[str, object]:
    begun = time.perf_counter()
    start_script_sha256 = sha256_path(SCRIPT)
    bindings = verify_bindings(hash_full_matrix=True)
    g75 = load_source_module(
        G0075_SCRIPT,
        EXPECTED_BINDINGS["g0075_producer"][1],
        "max11_g0075_frozen_for_g0079",
    )
    family = reconstruct_family(g75, verify_vf2=verify_vf2)
    controls = run_small_controls(g75, family)
    controls["old_basis_contract"] = verify_old_basis_contract()
    controls["exact_separator_prices"] = preflight_price_controls(g75, family)
    controls["semantic_segments"] = semantic_segment_controls(g75, family)
    subject = {
        "base_count": len(family.bases),
        "base_manifest_sha256": canonical_sha256(
            [
                {
                    "position": base.position,
                    "term_index": base.term_index,
                    "left": g75.G73.serialize_side(base.left),
                    "right": g75.G73.serialize_side(base.right),
                    "components": [list(component) for component in base.components],
                }
                for base in family.bases
            ]
        ),
        "old_family": {
            "predicate": "auxiliary is in the component opposite the doubled anchor",
            "raw_seed_count": len(family.old_seeds),
            "orbit_count": len(family.old_representatives),
            "orbit_manifest_sha256": g75.G73.EXPECTED_ORBIT_MANIFEST_SHA256,
            "representative_manifest_sha256": (
                g75.G73.EXPECTED_REPRESENTATIVE_MANIFEST_SHA256
            ),
        },
        "new_family": {
            "predicate": (
                "auxiliary is distinct from and in the same base-forest component as "
                "the doubled anchor; both outer orientations"
            ),
            **family.new_orbit_report,
        },
        "cross_family": {
            "orbit_intersection_count": 0,
            "combined_y_spoke_orbit_count": UNION_ORBIT_COUNT,
            "carrier_columns": ["C_L", "C_E", "C_Y"],
            "combined_columns_with_carriers": UNION_ORBIT_COUNT + 3,
            "global_column_ids": {
                "old_including_carriers": [GLOBAL_OLD_START, GLOBAL_OLD_STOP],
                "new_y_spokes": [GLOBAL_NEW_START, GLOBAL_NEW_STOP],
                "target": GLOBAL_TARGET_COLUMN,
                "local_new_to_global": "global=8107+local_new_index",
            },
        },
        "registered_rows": {
            "count": TOTAL_ROWS,
            "order": (
                "15,360 G-0075 rows (128 panels x 120 positive four-colour profiles), "
                "then all 1,378 G-0074 rows"
            ),
            "old_augmented_matrix_raw_sha256": EXPECTED_FULL_OLD_RAW_SHA256,
        },
        "registered_modular_gate": {
            "prime": PRIME,
            "additional_primes_forbidden": (
                "G-0077 P/R are valid only at 1,000,003; any additional prime must "
                "derive and bind its own complete P/R basis and old-column quotient replay"
            ),
            "baseline_basis": "canonical G-0077 basis columns P and basis rows R",
            "schur_formula": (
                "S_Q=[B_Q|b_Q]-A[Q,P]*A[R,P]^{-1}*[B_R|b_R] mod p"
            ),
            "decision": (
                "rank-adaptive quotient-row constraint generation: begin with the exact "
                "G-0078 separator row, then accumulate q_s*c=t_s where "
                "q_s=C[s,:]-A[s,P]*B^{-1}*C[R,:], "
                "t_s=b[s]-A[s,P]*B^{-1}*b[R], and B=A[R,P]. At each K, RREF the "
                "small K by 18,583 augmented system, choose the canonical free-zero basic "
                "solution (support <=K), solve old-basis coordinates, replay raw rows in "
                "order, and add the first mismatch. A target-coordinate pivot is modular "
                "separation; an all-16,738-row replay is modular compatibility."
            ),
            "dense_schur_design_rejected": (
                "the registered run never forms or RREFs the complete 9,862 by 18,583 "
                "Schur matrix; a dense fallback would require a separate preregistered experiment"
            ),
            "stage_order": [
                "exact-price and serialize all 18,582 new columns under G-0078 separator",
                "if every exact price is zero, emit exact bounded separation certificate",
                "otherwise recompute canonical q_2410,t_2410 from raw P/R/B and prove the complete exact-price row and target are one common nonzero scalar multiple modulo p; seed CEGIS with canonical q_2410,t_2410, never by silently identifying the 230-row exact functional with e_2410 quotient normalization",
                "replay the canonical basic solution, collect the first 64 nonzero residual rows in raw order, and greedily append only rows that strictly raise augmented rank",
                "stop unresolved at 1,024 accumulated quotient rows, 16 batches, or six hours; never switch to a dense fallback in this experiment",
            ],
            "performance_contract": {
                "required_rank_fixture": [2048, 4096],
                "conservative_factor": PERFORMANCE_CONSERVATIVE_FACTOR,
                "maximum_projected_dense_seconds": MAX_PROJECTED_DENSE_SECONDS,
                "minimum_available_gib": MINIMUM_AVAILABLE_GIB,
                "minimum_free_disk_gib": MINIMUM_FREE_DISK_GIB,
                "mismatch_batch_size": CEGIS_MISMATCH_BATCH,
                "maximum_accumulated_rows": MAX_CEGIS_ROWS,
                "maximum_batches": MAX_CEGIS_ROUNDS,
                "maximum_wall_seconds": MAX_REGISTERED_WALL_SECONDS,
                "failure_scope": (
                    "if any live wall/RAM/disk gate or CEGIS cap fails, stop with the exhaustive "
                    "price artifact and current checkpoint but no full target-membership decision"
                ),
            },
            "scope": (
                "finite-field target compatibility/separation for the complete combined "
                "26,686-orbit Y-spoke family plus three carriers on exactly 16,738 rows"
            ),
        },
    }
    scientific = {
        "schema": SCHEMA_PREFLIGHT,
        "bindings": bindings,
        "controls": controls,
        "subject": subject,
    }
    benchmark = performance_benchmark()
    end_bindings = verify_bindings(hash_full_matrix=True)
    end_script_sha256 = sha256_path(SCRIPT)
    if bindings != end_bindings or start_script_sha256 != end_script_sha256:
        raise GateError("preflight source/input custody changed during execution")
    return {
        **scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "script_sha256": end_script_sha256,
        "custody": {
            "start_script_sha256": start_script_sha256,
            "end_script_sha256": end_script_sha256,
            "all_upstream_hashes_replayed_at_start_and_end": True,
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "python_flint": flint.__version__,
            "networkx": nx.__version__,
            "platform": platform.platform(),
        },
        "performance_benchmark": benchmark,
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "This preflight freezes a finite construction family and modular diagnostic only. "
            "It contains no registered target-membership outcome and makes no rational, real, "
            "global-identity, unrestricted-network, lower-bound, novelty, or priority claim."
        ),
    }


def enforce_registered_pins(arguments: argparse.Namespace) -> None:
    if not REGISTERED_IMPLEMENTATION_COMPLETE:
        raise GateError("registered execution is absent from this preflight-only source")
    if arguments.output is None:
        raise GateError("--run requires an explicit --output path")
    if arguments.preflight_receipt is None:
        raise GateError("--run requires an explicit --preflight-receipt path")
    if arguments.prereg_artifact is None:
        raise GateError("--run requires an explicit --prereg-artifact path")
    supplied = (
        arguments.expected_source_sha256,
        arguments.expected_prereg_sha256,
        arguments.expected_preflight_sha256,
        arguments.expected_preflight_science_sha256,
    )
    if any(not isinstance(value, str) or len(value) != 64 for value in supplied):
        raise GateError("--run requires four explicit lowercase SHA-256 pins")
    actual_source = sha256_path(SCRIPT)
    actual_prereg = sha256_path(arguments.prereg_artifact)
    actual_preflight = sha256_path(arguments.preflight_receipt)
    if actual_source != arguments.expected_source_sha256:
        raise GateError("live registered source differs from explicit source pin")
    if actual_prereg != arguments.expected_prereg_sha256:
        raise GateError("live preregistration differs from explicit prereg pin")
    if actual_preflight != arguments.expected_preflight_sha256:
        raise GateError("live preflight differs from explicit preflight pin")
    try:
        prereg = json.loads(arguments.prereg_artifact.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise GateError(f"could not parse preregistration artifact: {error}") from error
    if not isinstance(prereg, dict) or prereg.get("schema") != "max11-g0079-preregistration-v1":
        raise GateError("malformed G-0079 preregistration artifact")
    if (
        prereg.get("registered_source_sha256") != actual_source
        or prereg.get("preflight_receipt_sha256") != actual_preflight
        or prereg.get("preflight_scientific_payload_sha256")
        != arguments.expected_preflight_science_sha256
        or prereg.get("experiment_status") != "planned"
    ):
        raise GateError("live preregistration content drift")
    receipt = read_gzip(arguments.preflight_receipt)
    if (
        receipt.get("scientific_payload_sha256")
        != arguments.expected_preflight_science_sha256
    ):
        raise GateError("preflight scientific payload drift")
    subject = receipt.get("subject")
    if not isinstance(subject, dict):
        raise GateError("preflight subject missing")
    new_family = subject.get("new_family")
    if not isinstance(new_family, dict) or new_family.get("vf2_complete") is not True:
        raise GateError("registered run refuses a preflight without complete VF2 replay")


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--skip-full-vf2", action="store_true")
    parser.add_argument("--workers", type=int, default=max(1, min(8, os.cpu_count() or 1)))
    parser.add_argument("--preflight-receipt", type=Path)
    parser.add_argument("--prereg-artifact", type=Path)
    parser.add_argument("--expected-source-sha256")
    parser.add_argument("--expected-prereg-sha256")
    parser.add_argument("--expected-preflight-sha256")
    parser.add_argument("--expected-preflight-science-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.workers < 1:
        raise GateError("workers must be positive")
    if arguments.output is not None and arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output}")
    bindings = verify_bindings(hash_full_matrix=False)
    g75 = load_source_module(
        G0075_SCRIPT,
        EXPECTED_BINDINGS["g0075_producer"][1],
        "max11_g0075_frozen_for_g0079_main",
    )
    if arguments.self_test:
        controls = run_small_controls(g75, None)
        print(
            json.dumps(
                {
                    "schema": "max11-g0079-self-test-v1",
                    "bindings_checked": sorted(bindings),
                    "controls": controls,
                    "registered_execution_enabled": REGISTERED_IMPLEMENTATION_COMPLETE,
                    "result": "PASS",
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments.preflight_only:
        if arguments.output is None:
            raise GateError("--preflight-only requires an explicit --output")
        report = build_preflight(verify_vf2=not arguments.skip_full_vf2)
        write_gzip(arguments.output, report)
        print(
            json.dumps(
                {
                    "schema": report["schema"],
                    "scientific_payload_sha256": report["scientific_payload_sha256"],
                    "script_sha256": report["script_sha256"],
                    "preflight_sha256": sha256_path(arguments.output),
                    "vf2_complete": not arguments.skip_full_vf2,
                    "output": str(arguments.output),
                },
                sort_keys=True,
            )
        )
        return 0
    enforce_registered_pins(arguments)
    raise GateError(
        "registered Schur implementation is intentionally absent from the preflight commit"
    )


if __name__ == "__main__":
    raise SystemExit(main())
