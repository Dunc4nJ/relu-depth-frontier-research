#!/usr/bin/env python3
"""Registered complete exact-price runner for G-0079.

The first outcome-bearing stage evaluates the complete 18,582-column
same-component family under the frozen G-0078 exact left functional.  It is an
independently runnable stage boundary and writes a complete price receipt.  If
all prices vanish, the two evaluator paths emit a bounded exact-separator
candidate for independent replay.  Otherwise the complete signed price vector
is guidance for a later, separately preregistered solver and makes no
membership claim.  This source contains no quotient execution path.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import resource
import shutil
import sys
import time
from types import ModuleType
from typing import Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREFLIGHT_SOURCE = HERE / "same_component_y_spoke_closure.py"
PREFLIGHT_RECEIPT = HERE / "same_component_y_spoke_preflight_v1.json.gz"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
G0078_EXACT = ROOT / "artifacts/math/G-0078/sparse_exact_left_dual_v1.json.gz"
FULL_OLD_MATRIX = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
ENVIRONMENT_MANIFEST = ROOT / "environment/g0075.subject.manifest"
REGISTERED_PYTHON = ROOT / ".venv/bin/python"
REGISTERED_PYTHON_RELATIVE = ".venv/bin/python"

SCHEMA_PREREGISTRATION = "max11-g0079-preregistration-v1"
SCHEMA_PRICE = "max11-g0079-complete-exact-price-vector-v1"

PRIME = 1_000_003
TOTAL_ROWS = 16_738
OLD_COLUMNS = 8_107
NEW_COLUMNS = 18_582
COMBINED_DICTIONARY_COLUMNS = 26_689
GLOBAL_NEW_START = 8_107
GLOBAL_NEW_STOP = 26_688
GLOBAL_TARGET_COLUMN = 26_689
EXACT_SUPPORT_ROWS = 230
PRICE_MINIMUM_AVAILABLE_GIB = 8.0
MINIMUM_FREE_DISK_GIB = 12.0
EXPECTED_PYTHON_VERSION = "3.13.7"

EXPECTED_PREFLIGHT_SOURCE_SHA256 = (
    "3b4626f36c8c505274b108b3cd80a17127de6e911c16962cbdbcff557a22b5da"
)
EXPECTED_PREFLIGHT_RECEIPT_SHA256 = (
    "12ea9a384a064c4cd9e17e37688384f4241b2fbe85cea501b892ad1ab2b4fd91"
)
EXPECTED_PREFLIGHT_SCIENCE_SHA256 = (
    "2774dfa1b49de1e661633c3176e091519b25f479a68041cc2d08887ada38f73b"
)
EXPECTED_G0077_MODULAR_SHA256 = (
    "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4"
)
EXPECTED_G0078_EXACT_SHA256 = (
    "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96"
)
EXPECTED_FULL_OLD_MATRIX_SHA256 = (
    "5c04ef6cadebf41e31cf01f822210305d4977ebbf0aebeba2bacc73e765c5c9f"
)
EXPECTED_ENVIRONMENT_SHA256 = (
    "12ad4b74f2736a883c562389d6ac50089ea07d5182593c7f75d564af80eb2a7c"
)
EXPECTED_NEW_ORBIT_MANIFEST_SHA256 = (
    "412fb195a6017d2e5c55a42726514e27e210bee52fd8df555d5804fc06f5f58c"
)
EXPECTED_NEW_REPRESENTATIVE_MANIFEST_SHA256 = (
    "b5782585f158ff81ef8e2778c8ac24b7da0cc3e180de66bac496bff1a54f6d02"
)
RESULT_EXACT_ZERO = (
    "EXACT_BOUNDED_NONMEMBERSHIP_CANDIDATE_COMPLETE_FROZEN_DICTIONARY"
)
RESULT_PRICE_NONZERO = "EXACT_PRICE_SEED_CONTINUE_WITH_FULL_DICTIONARY"


class RunnerError(RuntimeError):
    """A binding, arithmetic, custody, cache, or decision invariant failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise RunnerError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_sha256(array: np.ndarray) -> str:
    contiguous = np.ascontiguousarray(array)
    return hashlib.sha256(memoryview(contiguous).cast("B")).hexdigest()


def read_gzip(path: Path) -> dict[str, object]:
    if not path.is_file() or path.is_symlink():
        raise RunnerError(f"not a regular gzip JSON file: {path}")
    with gzip.open(path, "rt", encoding="utf-8") as source:
        document = json.load(source)
    if not isinstance(document, dict):
        raise RunnerError(f"malformed gzip JSON object: {path}")
    return document


def write_gzip_exclusive(path: Path, document: object) -> None:
    require_contained(path)
    if path.exists() or path.is_symlink():
        raise RunnerError(f"refusing to overwrite registered output: {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as raw:
            with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as zipped_file:
                zipped_file.write(canonical_bytes(document))
            raw.flush()
            os.fsync(raw.fileno())
    except BaseException:
        try:
            path.unlink()
        except FileNotFoundError:
            pass
        raise


def write_json_atomic(path: Path, document: object) -> None:
    require_contained(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp-{os.getpid()}")
    if temporary.exists() or temporary.is_symlink():
        raise RunnerError(f"temporary path already exists: {temporary}")
    payload = canonical_bytes(document)
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(descriptor, "wb") as target:
            target.write(payload)
            target.flush()
            os.fsync(target.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise


def require_contained(path: Path) -> None:
    resolved = path.resolve(strict=False)
    if not resolved.is_relative_to(ROOT.resolve()):
        raise RunnerError(f"path escapes campaign workspace: {path}")


def relative_path(path: Path) -> str:
    require_contained(path)
    return str(path.resolve(strict=False).relative_to(ROOT.resolve()))


def available_gib() -> float:
    with Path("/proc/meminfo").open("rt", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) / 1024**2
    raise RunnerError("could not read MemAvailable from /proc/meminfo")


def free_disk_gib(path: Path) -> float:
    return shutil.disk_usage(path.resolve()).free / 1024**3


def load_module(path: Path, expected_sha256: str, name: str) -> ModuleType:
    if not path.is_file() or path.is_symlink():
        raise RunnerError(f"not a regular source file: {path}")
    source = path.read_bytes()
    observed = hashlib.sha256(source).hexdigest()
    if observed != expected_sha256:
        raise RunnerError(f"source binding drift for {path}: {observed}")
    module = ModuleType(name)
    module.__file__ = str(path)
    module.__package__ = None
    module.__cached__ = None
    module.__spec__ = None
    sys.modules[name] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module


def fixed_binding_paths() -> dict[str, tuple[Path, str]]:
    return {
        "preflight_source": (PREFLIGHT_SOURCE, EXPECTED_PREFLIGHT_SOURCE_SHA256),
        "preflight_receipt": (PREFLIGHT_RECEIPT, EXPECTED_PREFLIGHT_RECEIPT_SHA256),
        "g0077_modular": (G0077_MODULAR, EXPECTED_G0077_MODULAR_SHA256),
        "g0078_exact": (G0078_EXACT, EXPECTED_G0078_EXACT_SHA256),
        "full_old_matrix": (FULL_OLD_MATRIX, EXPECTED_FULL_OLD_MATRIX_SHA256),
        "environment_manifest": (ENVIRONMENT_MANIFEST, EXPECTED_ENVIRONMENT_SHA256),
    }


def replay_fixed_bindings() -> dict[str, dict[str, object]]:
    report: dict[str, dict[str, object]] = {}
    for label, (path, expected) in fixed_binding_paths().items():
        observed = sha256_path(path)
        if observed != expected:
            raise RunnerError(f"fixed binding drift for {label}: {observed} != {expected}")
        report[label] = {
            "path": relative_path(path),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    return report


def validate_preflight() -> tuple[ModuleType, dict[str, object]]:
    preflight = load_module(
        PREFLIGHT_SOURCE,
        EXPECTED_PREFLIGHT_SOURCE_SHA256,
        "max11_g0079_frozen_preflight_for_runner",
    )
    receipt = read_gzip(PREFLIGHT_RECEIPT)
    subject = receipt.get("subject")
    controls = receipt.get("controls")
    if not isinstance(subject, dict) or not isinstance(controls, dict):
        raise RunnerError("malformed G-0079 preflight receipt")
    new_family = subject.get("new_family")
    cross_family = subject.get("cross_family")
    prices = controls.get("exact_separator_prices")
    if (
        receipt.get("schema") != preflight.SCHEMA_PREFLIGHT
        or receipt.get("scientific_payload_sha256")
        != EXPECTED_PREFLIGHT_SCIENCE_SHA256
        or receipt.get("script_sha256") != EXPECTED_PREFLIGHT_SOURCE_SHA256
        or not isinstance(new_family, dict)
        or new_family.get("raw_seed_count") != 26_960
        or new_family.get("orbit_count") != NEW_COLUMNS
        or new_family.get("orbit_manifest_sha256")
        != EXPECTED_NEW_ORBIT_MANIFEST_SHA256
        or new_family.get("representative_manifest_sha256")
        != EXPECTED_NEW_REPRESENTATIVE_MANIFEST_SHA256
        or new_family.get("vf2_complete") is not True
        or not isinstance(cross_family, dict)
        or cross_family.get("orbit_intersection_count") != 0
        or cross_family.get("combined_columns_with_carriers")
        != COMBINED_DICTIONARY_COLUMNS
        or not isinstance(prices, dict)
        or prices.get("actual_new_family_columns_priced") != 0
    ):
        raise RunnerError("frozen G-0079 preflight contract drift")
    return preflight, receipt


@dataclass(frozen=True)
class Registration:
    preregistration: dict[str, object]
    preregistration_sha256: str
    runner_sha256: str
    preregistration_path: Path
    stage_output: Path


def validate_registration(arguments: argparse.Namespace) -> Registration:
    if arguments.preregistration is None:
        raise RunnerError("registered stage requires --preregistration")
    preregistration_path = arguments.preregistration
    require_contained(preregistration_path)
    runner_sha256 = sha256_path(SCRIPT)
    if not preregistration_path.is_file() or preregistration_path.is_symlink():
        raise RunnerError("preregistration must be one regular file")
    preregistration_bytes = preregistration_path.read_bytes()
    preregistration_sha256 = hashlib.sha256(preregistration_bytes).hexdigest()
    if arguments.expected_runner_sha256 != runner_sha256:
        raise RunnerError("live runner differs from explicit source pin")
    if arguments.expected_preregistration_sha256 != preregistration_sha256:
        raise RunnerError("live preregistration differs from explicit pin")
    try:
        document = json.loads(preregistration_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RunnerError("preregistration bytes are not valid JSON") from error
    if not isinstance(document, dict):
        raise RunnerError("preregistration JSON is not an object")
    common_expected = {
        "schema": SCHEMA_PREREGISTRATION,
        "experiment_status": "planned",
        "registered_source_sha256": runner_sha256,
        "preflight_source_sha256": EXPECTED_PREFLIGHT_SOURCE_SHA256,
        "preflight_receipt_sha256": EXPECTED_PREFLIGHT_RECEIPT_SHA256,
        "preflight_scientific_payload_sha256": EXPECTED_PREFLIGHT_SCIENCE_SHA256,
        "prime": PRIME,
        "new_columns": NEW_COLUMNS,
        "all_new_columns_retained_after_nonzero_price": True,
        "dense_fallback_allowed": False,
        "registered_python": REGISTERED_PYTHON_RELATIVE,
        "python_version": EXPECTED_PYTHON_VERSION,
        "environment_manifest_sha256": EXPECTED_ENVIRONMENT_SHA256,
    }
    for key, expected in common_expected.items():
        if document.get(key) != expected:
            raise RunnerError(f"preregistration field drift: {key}")
    if (
        Path(sys.executable).resolve() != REGISTERED_PYTHON.resolve()
        or platform.python_version() != EXPECTED_PYTHON_VERSION
    ):
        raise RunnerError("registered interpreter path/version drift")
    if document.get("preregistration_path") != relative_path(preregistration_path):
        raise RunnerError("preregistration self-path drift")
    if document.get("stage_order") != ["exact-price"]:
        raise RunnerError("preregistration stage order drift")
    price_stage = document.get("price_stage")
    if not isinstance(price_stage, dict):
        raise RunnerError("preregistration price-stage record malformed")
    output_text = price_stage.get("output")
    if not isinstance(output_text, str):
        raise RunnerError("registered stage output path missing")
    stage_output = ROOT / output_text
    require_contained(stage_output)
    if arguments.output is None or arguments.output.resolve(strict=False) != stage_output.resolve(strict=False):
        raise RunnerError("CLI output path differs from preregistration")
    stage_contract = {
        "minimum_available_gib": PRICE_MINIMUM_AVAILABLE_GIB,
        "minimum_free_disk_gib": MINIMUM_FREE_DISK_GIB,
        "new_columns": NEW_COLUMNS,
        "primary_evaluator": "frozen flattened-max producer",
        "independent_evaluator": "direct nested-max replay over every support-row/column entry",
        "serialize_all_prices": True,
        "quotient_execution_in_this_source": False,
    }
    for key, expected in stage_contract.items():
        if price_stage.get(key) != expected:
            raise RunnerError(f"preregistered price-stage contract drift: {key}")
    return Registration(
        preregistration=document,
        preregistration_sha256=preregistration_sha256,
        runner_sha256=runner_sha256,
        preregistration_path=preregistration_path,
        stage_output=stage_output,
    )


def reconstruct_family(
    preflight: ModuleType, receipt: dict[str, object]
) -> tuple[ModuleType, object]:
    g75 = load_module(
        preflight.G0075_SCRIPT,
        preflight.EXPECTED_BINDINGS["g0075_producer"][1],
        "max11_g0075_frozen_for_g0079_runner",
    )
    family = preflight.reconstruct_family(g75, verify_vf2=False)
    new_report = family.new_orbit_report
    receipt_report = receipt["subject"]["new_family"]
    compared_fields = (
        "raw_seed_count",
        "orbit_count",
        "class_size_histogram",
        "orbit_sequence_sha256",
        "orbit_manifest_sha256",
        "representative_manifest_sha256",
    )
    if any(new_report.get(key) != receipt_report.get(key) for key in compared_fields):
        raise RunnerError("registered family reconstruction/order differs from preflight")
    if (
        new_report.get("representative_manifest_sha256")
        != EXPECTED_NEW_REPRESENTATIVE_MANIFEST_SHA256
        or len(family.new_representatives) != NEW_COLUMNS
    ):
        raise RunnerError("new representative manifest/order drift")
    return g75, family


@dataclass(frozen=True)
class ExactFunctional:
    rows: np.ndarray
    primitive_weights: tuple[int, ...]
    denominator_lcm: int
    common_gcd: int
    expected_primitive_target: int
    source_payload_sha256: str


def exact_functional(preflight: ModuleType) -> ExactFunctional:
    report = read_gzip(G0078_EXACT)
    payload = report.get("scientific_payload")
    if not isinstance(payload, dict):
        raise RunnerError("G-0078 exact scientific payload missing")
    separator = preflight.load_exact_separator()
    rows = np.asarray(separator["rows"], dtype=np.int64)
    denominators = list(map(int, separator["selected_divisors"])) + [
        int(separator["failing_divisor"])
    ]
    numerators = list(map(int, separator["selected_numerators"])) + [
        int(separator["failing_weight"])
    ]
    if rows.shape != (EXACT_SUPPORT_ROWS,) or len(denominators) != EXACT_SUPPORT_ROWS:
        raise RunnerError("exact functional support census drift")
    denominator_lcm = math.lcm(*denominators)
    cleared = [
        numerator * (denominator_lcm // denominator)
        for numerator, denominator in zip(numerators, denominators, strict=True)
    ]
    common_gcd = math.gcd(*map(abs, cleared))
    if common_gcd <= 0:
        raise RunnerError("exact functional has zero global gcd")
    primitive = tuple(value // common_gcd for value in cleared)
    if math.gcd(*map(abs, primitive)) != 1:
        raise RunnerError("LCM-cleared exact functional is not globally primitive")
    for numerator, denominator, weight in zip(
        numerators, denominators, primitive, strict=True
    ):
        if Fraction(weight * common_gcd, denominator_lcm) != Fraction(
            numerator, denominator
        ):
            raise RunnerError("common-LCM exact functional replay failed")
    target = Fraction(str(payload.get("exact_target_pairing")))
    scaled_target = target * denominator_lcm / common_gcd
    if scaled_target.denominator != 1 or scaled_target.numerator == 0:
        raise RunnerError("G-0078 target pairing does not clear to a nonzero integer")
    return ExactFunctional(
        rows=rows,
        primitive_weights=primitive,
        denominator_lcm=denominator_lcm,
        common_gcd=common_gcd,
        expected_primitive_target=scaled_target.numerator,
        source_payload_sha256=str(report.get("scientific_payload_sha256")),
    )


def integer_pairings(weights: Sequence[int], values: np.ndarray) -> list[int]:
    if values.ndim != 2 or values.shape[0] != len(weights):
        raise RunnerError("integer-pairing matrix shape drift")
    pairings = [0] * values.shape[1]
    for row, weight in enumerate(weights):
        pairings = [
            current + weight * int(value)
            for current, value in zip(pairings, values[row], strict=True)
        ]
    return pairings


def evaluate_representatives_nested_on_rows(
    preflight: ModuleType,
    g75: ModuleType,
    bases: Sequence[object],
    representatives: Sequence[object],
    raw_rows: Sequence[int],
) -> np.ndarray:
    """Independent direct-nested-max evaluator for every registered column.

    The frozen producer uses an algebraically flattened max identity.  This
    replay instead computes ``y=max(2*x_k,x_l+x_11)`` and then the original
    outer max literally, while retaining only assignment/profile generation.
    """

    g73 = g75.G73
    grouped = g73.group_by_base(representatives, len(bases))
    matrix = np.zeros((len(raw_rows), len(representatives)), dtype=np.int64)
    for output_row, raw_row in enumerate(raw_rows):
        levels = preflight.raw_row_levels(g75, int(raw_row))
        for base in bases:
            entries = grouped[base.position]
            if not entries:
                continue
            columns = np.asarray([column for column, _seed in entries], dtype=np.intp)
            seeds = [seed for _column, seed in entries]
            left = np.zeros(levels.shape[1], dtype=np.int16)
            right = np.zeros(levels.shape[1], dtype=np.int16)
            for a, b in base.left:
                left += np.maximum(levels[a - 1], levels[b - 1])
            for a, b in base.right:
                right += np.maximum(levels[a - 1], levels[b - 1])
            anchors = np.asarray(
                [seed.expression.anchor - 1 for seed in seeds], dtype=np.intp
            )
            auxiliaries = np.asarray(
                [seed.expression.auxiliary - 1 for seed in seeds], dtype=np.intp
            )
            orientations = np.asarray(
                [seed.expression.orientation for seed in seeds], dtype=np.int8
            )
            simple = 2 * levels[anchors]
            y_value = np.maximum(simple, levels[auxiliaries] + levels[10])
            orientation_zero = np.maximum(
                left[None, :] + simple,
                right[None, :] + y_value,
            )
            orientation_one = np.maximum(
                left[None, :] + y_value,
                right[None, :] + simple,
            )
            literal = np.where(
                orientations[:, None] == 0,
                orientation_zero,
                orientation_one,
            )
            matrix[output_row, columns] = literal.sum(axis=1, dtype=np.int64)
    return matrix


def representative_price_records(
    g75: ModuleType,
    family: object,
    prices: Sequence[int],
) -> list[dict[str, object]]:
    g73 = g75.G73
    class_sizes: dict[bytes, int] = {}
    for seed in family.new_seeds:
        certificate = g73.orbit_certificate(seed.expression)
        class_sizes[certificate] = class_sizes.get(certificate, 0) + 1
    records: list[dict[str, object]] = []
    for local_index, (seed, price) in enumerate(
        zip(family.new_representatives, prices, strict=True)
    ):
        expression = seed.expression
        base = family.bases[seed.base_position]
        certificate = g73.orbit_certificate(expression)
        topology = sorted(map(len, base.components))
        anchor_component_size = next(
            len(component) for component in base.components if expression.anchor in component
        )
        descriptor = g73.seed_record(seed)
        records.append(
            {
                "local_index": local_index,
                "global_id": GLOBAL_NEW_START + local_index,
                "price": str(price),
                "representative_sha256": canonical_sha256(descriptor),
                "base_position": seed.base_position,
                "base_term_index": seed.base_term_index,
                "component_topology": f"{topology[0]}+{topology[1]}",
                "anchor_component_size": anchor_component_size,
                "anchor": expression.anchor,
                "auxiliary": expression.auxiliary,
                "orientation": expression.orientation,
                "orbit_class_size": class_sizes[certificate],
            }
        )
    if len(records) != NEW_COLUMNS:
        raise RunnerError("representative price-record census drift")
    return records


def registration_custody_paths(registration: Registration) -> dict[str, Path]:
    paths = {label: path for label, (path, _digest) in fixed_binding_paths().items()}
    paths["runner"] = SCRIPT
    paths["preregistration"] = registration.preregistration_path
    return paths


def capture_custody(paths: dict[str, Path]) -> dict[str, str]:
    return {label: sha256_path(path) for label, path in sorted(paths.items())}


def validate_host_for_price(output: Path) -> dict[str, float]:
    output.parent.mkdir(parents=True, exist_ok=True)
    memory = available_gib()
    disk = free_disk_gib(output.parent)
    if memory < PRICE_MINIMUM_AVAILABLE_GIB:
        raise RunnerError(
            f"exact-price memory gate unmet: {memory:.3f} < {PRICE_MINIMUM_AVAILABLE_GIB} GiB"
        )
    if disk < MINIMUM_FREE_DISK_GIB:
        raise RunnerError(
            f"exact-price disk gate unmet: {disk:.3f} < {MINIMUM_FREE_DISK_GIB} GiB"
        )
    return {"available_gib": memory, "free_disk_gib": disk}


def run_price_stage(arguments: argparse.Namespace) -> dict[str, object]:
    begun = time.perf_counter()
    registration = validate_registration(arguments)
    if registration.stage_output.exists() or registration.stage_output.is_symlink():
        raise RunnerError("registered price output already exists")
    resources = validate_host_for_price(registration.stage_output)
    replay_fixed_bindings()
    custody_paths = registration_custody_paths(registration)
    start_custody = capture_custody(custody_paths)
    preflight, receipt = validate_preflight()
    g75, family = reconstruct_family(preflight, receipt)
    functional = exact_functional(preflight)

    evaluation_started = time.perf_counter()
    values = preflight.evaluate_representatives_on_rows(
        g75,
        family.bases,
        family.new_representatives,
        functional.rows.astype(int).tolist(),
    )
    evaluation_seconds = time.perf_counter() - evaluation_started
    if values.shape != (EXACT_SUPPORT_ROWS, NEW_COLUMNS) or values.dtype != np.int64:
        raise RunnerError("complete new-family exact-price matrix shape/dtype drift")
    independent_started = time.perf_counter()
    independent_values = evaluate_representatives_nested_on_rows(
        preflight,
        g75,
        family.bases,
        family.new_representatives,
        functional.rows.astype(int).tolist(),
    )
    independent_evaluation_seconds = time.perf_counter() - independent_started
    if not np.array_equal(independent_values, values):
        mismatch = np.argwhere(independent_values != values)[0]
        raise RunnerError(
            "flattened/direct-nested full evaluator mismatch at "
            f"{tuple(map(int, mismatch))}"
        )

    pairing_started = time.perf_counter()
    prices = integer_pairings(functional.primitive_weights, values)
    target_values = np.ascontiguousarray(
        np.load(FULL_OLD_MATRIX, mmap_mode="r", allow_pickle=False)[
            functional.rows.astype(np.intp), -1
        ]
    )
    reconstructed_target_values = np.asarray(
        [
            np.max(preflight.raw_row_levels(g75, int(row)), axis=0).sum(
                dtype=np.int64
            )
            for row in functional.rows
        ],
        dtype=np.int64,
    )
    if not np.array_equal(target_values, reconstructed_target_values):
        raise RunnerError("independent MAX11 target reconstruction differs from full-N")
    independent_prices = integer_pairings(
        functional.primitive_weights, independent_values
    )
    if independent_prices != prices:
        raise RunnerError("independent full exact-price vector replay failed")
    target_pairing = sum(
        weight * int(value)
        for weight, value in zip(
            functional.primitive_weights, target_values, strict=True
        )
    )
    if target_pairing != functional.expected_primitive_target:
        raise RunnerError(
            "complete price stage target pairing differs from frozen G-0078 exact value"
        )
    pairing_seconds = time.perf_counter() - pairing_started

    zero_count = sum(value == 0 for value in prices)
    nonzero_count = NEW_COLUMNS - zero_count
    if len(prices) != NEW_COLUMNS:
        raise RunnerError("complete exact-price vector census drift")
    result = RESULT_EXACT_ZERO if nonzero_count == 0 else RESULT_PRICE_NONZERO
    global_ids = list(range(GLOBAL_NEW_START, GLOBAL_NEW_STOP + 1))
    if len(global_ids) != NEW_COLUMNS:
        raise RunnerError("new global-ID mapping census drift")
    price_strings = list(map(str, prices))
    price_records = representative_price_records(g75, family, prices)
    price_vector_gcd = math.gcd(*map(abs, prices))
    price_target_gcd = math.gcd(price_vector_gcd, abs(target_pairing))
    prices_mod_prime = [value % PRIME for value in prices]
    modular_nonzero_count = sum(value != 0 for value in prices_mod_prime)
    target_mod_prime = target_pairing % PRIME
    if target_mod_prime == 0:
        raise RunnerError("exact target pairing vanishes at the registered prime")

    scientific = {
        "schema": SCHEMA_PRICE,
        "result": result,
        "registered_dictionary": {
            "old_columns_including_carriers": OLD_COLUMNS,
            "new_columns": NEW_COLUMNS,
            "total_columns": COMBINED_DICTIONARY_COLUMNS,
            "new_global_ids": [GLOBAL_NEW_START, GLOBAL_NEW_STOP],
            "target_global_id": GLOBAL_TARGET_COLUMN,
            "new_representative_manifest_sha256": (
                EXPECTED_NEW_REPRESENTATIVE_MANIFEST_SHA256
            ),
        },
        "exact_functional": {
            "source": relative_path(G0078_EXACT),
            "source_scientific_payload_sha256": functional.source_payload_sha256,
            "support_rows": functional.rows.astype(int).tolist(),
            "support_rows_sha256": canonical_sha256(
                functional.rows.astype(int).tolist()
            ),
            "common_denominator_lcm": functional.denominator_lcm,
            "single_global_primitive_gcd": functional.common_gcd,
            "primitive_integer_weights": list(map(str, functional.primitive_weights)),
            "primitive_integer_weights_sha256": canonical_sha256(
                list(map(str, functional.primitive_weights))
            ),
            "coordinatewise_row_gcd_or_modular_division_used": False,
            "exact_target_pairing": str(target_pairing),
            "exact_target_pairing_nonzero": target_pairing != 0,
            "target_pairing_mod_prime": target_mod_prime,
        },
        "complete_price_vector": {
            "column_order": "local new representative order 0..18581; global=8107+local",
            "global_column_ids": global_ids,
            "prices": price_strings,
            "prices_sha256": canonical_sha256(price_strings),
            "price_records": price_records,
            "price_records_sha256": canonical_sha256(price_records),
            "zero_count": zero_count,
            "nonzero_count": nonzero_count,
            "price_vector_gcd": str(price_vector_gcd),
            "price_vector_with_target_gcd": str(price_target_gcd),
            "first_nonzero_local_index": next(
                (index for index, value in enumerate(prices) if value), None
            ),
            "prices_mod_prime": prices_mod_prime,
            "prices_mod_prime_sha256": canonical_sha256(prices_mod_prime),
            "modular_nonzero_count": modular_nonzero_count,
            "first_modular_nonzero_local_index": next(
                (index for index, value in enumerate(prices_mod_prime) if value), None
            ),
            "all_18582_columns_serialized": True,
            "support_values_int64_c_sha256": raw_sha256(values),
            "independent_nested_support_values_int64_c_sha256": raw_sha256(
                independent_values
            ),
            "all_4273860_entries_match_independent_nested_evaluator": True,
            "target_values_int64_sha256": raw_sha256(target_values),
            "independent_target_values_int64_sha256": raw_sha256(
                reconstructed_target_values
            ),
        },
        "branch_contract": {
            "all_zero": (
                "the exact G-0078 functional annihilates every old and new column and "
                "pairs nontrivially with the target on both internal evaluator paths; emit "
                "a bounded exact candidate pending independent external replay/promotion"
            ),
            "some_nonzero": (
                "the exact price row is guidance only; all 18,582 new columns, including "
                "every zero-price column, remain eligible for a later separately registered solver"
            ),
            "all_new_columns_retained_if_nonzero": True,
            "price_filtering_allowed": False,
            "quotient_execution_in_this_source": False,
            "independent_external_replay_required_for_promotion": True,
        },
        "claim_boundary": (
            "If all prices are zero, the result is exact nonmembership only in the span of "
            "the complete frozen 26,689-column dictionary on the frozen 16,738 rows. It is "
            "not an unrestricted network lower bound or global CPWL identity result. If any "
            "price is nonzero, this stage proves neither membership nor nonmembership."
        ),
    }
    end_custody = capture_custody(custody_paths)
    if end_custody != start_custody:
        raise RunnerError("registered price-stage custody changed during execution")
    report = {
        "schema": SCHEMA_PRICE,
        "scientific_payload": scientific,
        "scientific_payload_sha256": canonical_sha256(scientific),
        "runner_sha256": registration.runner_sha256,
        "preregistration_sha256": registration.preregistration_sha256,
        "preflight_receipt_sha256": EXPECTED_PREFLIGHT_RECEIPT_SHA256,
        "custody": {
            "start": start_custody,
            "end": end_custody,
            "identical": True,
        },
        "resources": resources,
        "evaluation_seconds": evaluation_seconds,
        "independent_evaluation_seconds": independent_evaluation_seconds,
        "pairing_seconds": pairing_seconds,
        "wall_seconds": time.perf_counter() - begun,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }
    write_gzip_exclusive(registration.stage_output, report)
    return report


def modular_rank_fixture(matrix: np.ndarray, prime: int) -> int:
    work = np.remainder(np.asarray(matrix, dtype=np.int64), prime).copy()
    if work.ndim != 2:
        raise RunnerError("modular-rank fixture must be a matrix")
    pivot_row = 0
    for column in range(work.shape[1]):
        pivot = next(
            (row for row in range(pivot_row, work.shape[0]) if work[row, column]),
            None,
        )
        if pivot is None:
            continue
        if pivot != pivot_row:
            work[[pivot_row, pivot]] = work[[pivot, pivot_row]]
        work[pivot_row] = (
            work[pivot_row] * pow(int(work[pivot_row, column]), -1, prime)
        ) % prime
        for row in range(work.shape[0]):
            if row != pivot_row and work[row, column]:
                work[row] = (
                    work[row] - work[row, column] * work[pivot_row]
                ) % prime
        pivot_row += 1
        if pivot_row == work.shape[0]:
            break
    return pivot_row


def unit_controls() -> dict[str, object]:
    weights = (3, -4, 5)
    values = np.asarray(
        [[2, 0, -1], [3, 6, 2], [4, 8, 5]], dtype=np.int64
    )
    observed = integer_pairings(weights, values)
    expected = [
        sum(weight * int(values[row, column]) for row, weight in enumerate(weights))
        for column in range(values.shape[1])
    ]
    if observed != expected:
        raise RunnerError("common-integer price fixture failed")
    mutant = values.copy()
    mutant[0, 0] += 1
    if integer_pairings(weights, mutant)[0] == observed[0]:
        raise RunnerError("one-unit price mutant escaped")

    rng = np.random.default_rng(0x79)
    left = rng.integers(0, 50, size=31, dtype=np.int64)
    right = rng.integers(0, 50, size=31, dtype=np.int64)
    simple = rng.integers(0, 50, size=(7, 31), dtype=np.int64)
    leaf = rng.integers(0, 50, size=(7, 31), dtype=np.int64)
    nested_zero = np.maximum(left[None, :] + simple, right[None, :] + np.maximum(simple, leaf))
    flattened_zero = np.maximum(
        np.maximum(left, right)[None, :] + simple,
        right[None, :] + leaf,
    )
    nested_one = np.maximum(right[None, :] + simple, left[None, :] + np.maximum(simple, leaf))
    flattened_one = np.maximum(
        np.maximum(left, right)[None, :] + simple,
        left[None, :] + leaf,
    )
    if not np.array_equal(nested_zero, flattened_zero) or not np.array_equal(
        nested_one, flattened_one
    ):
        raise RunnerError("nested/flattened max-identity fixture failed")
    flattened_mutant = np.maximum(
        np.maximum(left, right)[None, :] + simple,
        right[None, :] + leaf + 1,
    )
    if np.array_equal(nested_zero, flattened_mutant):
        raise RunnerError("flattened max-identity mutant escaped")

    # L is the first coordinate. C_nonzero has price one, C_zero price zero,
    # and b=C_nonzero+C_zero. Filtering to piercers falsely separates b.
    complete_c = np.asarray([[1, 0], [0, 1]], dtype=np.int64)
    target = np.asarray([1, 1], dtype=np.int64)
    prices = [int(complete_c[0, column]) for column in range(2)]
    if prices != [1, 0] or int(target[0]) != 1:
        raise RunnerError("zero-price retention fixture price drift")
    complete_rank = modular_rank_fixture(complete_c, 101)
    complete_augmented_rank = modular_rank_fixture(
        np.column_stack((complete_c, target)), 101
    )
    piercer_only = complete_c[:, [0]]
    piercer_rank = modular_rank_fixture(piercer_only, 101)
    piercer_augmented_rank = modular_rank_fixture(
        np.column_stack((piercer_only, target)), 101
    )
    if not (
        complete_rank == complete_augmented_rank == 2
        and piercer_rank == 1
        and piercer_augmented_rank == 2
    ):
        raise RunnerError("zero-price indispensable-column fixture failed")

    synthetic_levels = rng.integers(0, 20, size=(11, 43), dtype=np.int64)
    frozen_target = int(np.max(synthetic_levels, axis=0).sum(dtype=np.int64))
    literal_target = sum(max(map(int, synthetic_levels[:, column])) for column in range(43))
    if frozen_target != literal_target:
        raise RunnerError("independent MAX11 target fixture failed")
    return {
        "common_integer_price_fixture": True,
        "one_unit_price_mutant_rejected": True,
        "nested_flattened_both_orientations": True,
        "flattened_identity_mutant_rejected": True,
        "zero_price_indispensable_column_retained": True,
        "piercer_only_filtering_false_separation_detected": True,
        "independent_MAX11_target_fixture": True,
    }


def self_test() -> dict[str, object]:
    bindings = replay_fixed_bindings()
    preflight, receipt = validate_preflight()
    g75, family = reconstruct_family(preflight, receipt)
    functional = exact_functional(preflight)
    if (
        preflight.__cached__ is not None
        or g75.__cached__ is not None
        or Path(sys.executable).resolve() != REGISTERED_PYTHON.resolve()
        or platform.python_version() != EXPECTED_PYTHON_VERSION
        or functional.denominator_lcm != 180
        or functional.common_gcd != 60
        or len(functional.primitive_weights) != EXACT_SUPPORT_ROWS
        or len(family.new_representatives) != NEW_COLUMNS
    ):
        raise RunnerError("price-runner frozen metadata self-test failed")
    controls = unit_controls()
    if RESULT_PRICE_NONZERO == RESULT_EXACT_ZERO:
        raise RunnerError("price-stage branch labels collapsed")
    return {
        "schema": "max11-g0079-complete-price-runner-self-test-v1",
        "result": "PASS",
        "fixed_bindings": bindings,
        "preflight_scientific_payload_sha256": receipt.get(
            "scientific_payload_sha256"
        ),
        "new_representative_manifest_sha256": (
            family.new_orbit_report["representative_manifest_sha256"]
        ),
        "exact_functional_support_rows": EXACT_SUPPORT_ROWS,
        "common_denominator_lcm": functional.denominator_lcm,
        "single_global_primitive_gcd": functional.common_gcd,
        "single_owned_byte_semantic_load": True,
        "bytecode_cache_execution_allowed": False,
        "registered_python": REGISTERED_PYTHON_RELATIVE,
        "python_version": platform.python_version(),
        "controls": controls,
        "actual_new_family_values_evaluated": 0,
        "quotient_execution_implemented": False,
        "no_claim": (
            "Self-test reconstructs manifests and synthetic controls only. It evaluates zero "
            "actual new-family prices and makes no membership or nonmembership claim."
        ),
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--check-registration", action="store_true")
    mode.add_argument("--price-stage", action="store_true")
    parser.add_argument("--preregistration", type=Path)
    parser.add_argument("--expected-runner-sha256")
    parser.add_argument("--expected-preregistration-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    if arguments.self_test:
        if any(
            value is not None
            for value in (
                arguments.preregistration,
                arguments.expected_runner_sha256,
                arguments.expected_preregistration_sha256,
                arguments.output,
            )
        ):
            raise RunnerError("--self-test refuses registered-run arguments")
        print(json.dumps(self_test(), sort_keys=True))
        return
    required = {
        "--preregistration": arguments.preregistration,
        "--expected-runner-sha256": arguments.expected_runner_sha256,
        "--expected-preregistration-sha256": (
            arguments.expected_preregistration_sha256
        ),
        "--output": arguments.output,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        raise RunnerError(f"registered mode missing required arguments: {missing}")
    if arguments.check_registration:
        registration = validate_registration(arguments)
        if registration.stage_output.exists() or registration.stage_output.is_symlink():
            raise RunnerError("registered price output is not unused")
        start = capture_custody(registration_custody_paths(registration))
        replay_fixed_bindings()
        validate_preflight()
        end = capture_custody(registration_custody_paths(registration))
        if end != start:
            raise RunnerError("registration-check custody changed during execution")
        print(
            json.dumps(
                {
                    "schema": "max11-g0079-price-registration-check-v1",
                    "result": "PASS",
                    "runner_sha256": registration.runner_sha256,
                    "preregistration_sha256": registration.preregistration_sha256,
                    "output_unused": True,
                    "custody_identical": True,
                    "actual_new_family_values_evaluated": 0,
                    "quotient_execution_implemented": False,
                },
                sort_keys=True,
            )
        )
        return
    report = run_price_stage(arguments)
    scientific = report["scientific_payload"]
    summary = {
        "schema": SCHEMA_PRICE,
        "result": scientific["result"],
        "scientific_payload_sha256": report["scientific_payload_sha256"],
        "output": relative_path(arguments.output),
        "output_sha256": sha256_path(arguments.output),
        "new_columns_priced": NEW_COLUMNS,
    }
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
