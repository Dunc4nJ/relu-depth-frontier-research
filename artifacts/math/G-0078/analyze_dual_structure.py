#!/usr/bin/env python3
"""Reproduce the structural analysis of the frozen G-0078 exact dual.

Exact outputs in this program use the serialized rational functional and
integer arithmetic.  The full-system augmentation experiment is deliberately
reported separately: it is a rank computation over one finite field and is
discovery evidence only.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import gzip
import hashlib
from itertools import product
import json
from math import comb, factorial, gcd, lcm
from pathlib import Path
from typing import Iterable, Sequence

from flint import fmpz_mat, nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()

G0078_OUTCOME = HERE / "sparse_exact_left_dual_v1.json.gz"
G0077_MODULAR = ROOT / "artifacts/math/G-0077/canonical_modular_dual_v1.json.gz"
G0077_SCRIPT = ROOT / "artifacts/math/G-0077/exact_left_dual_lift.py"
G0078_SCRIPT = HERE / "sparse_exact_left_dual.py"
G0073_SCRIPT = ROOT / "artifacts/math/G-0073/y_spoke_profile_gate.py"
G0074_SCRIPT = ROOT / "artifacts/math/G-0074/farey_three_level_gate.py"
G0075_SCRIPT = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate.py"
G0075_OUTCOME = ROOT / "artifacts/math/G-0075/four_level_augmented_rank_gate_v1.json.gz"
FULL_CACHE = ROOT / "artifacts/math/G-0076/cache/full-N.npy"
FROZEN_OUTPUT = HERE / "dual_structure_v1.json"

N = 11
A_COLUMNS = 8_107
AUGMENTED_COLUMNS = 8_108
ROWS = 16_738
RANK_A = 6_876
PRIME = 1_000_003
PROFILES_PER_PANEL = 120
PANELS = 128
DENOMINATOR = 257
PANEL_SEED = "max11-g0075-genuinely-four-valued-panels-v1"

EXPECTED_FILE_SHA256 = {
    G0078_OUTCOME: "8e08caecbf5a4d7b457a32f445702121dc1d095b4e368d45db8bc64847b4ae96",
    G0077_MODULAR: "9221d7111a67630a4962d88b97f0cfd7a6b8fd50d3dc9717e580440492d67ed4",
    G0077_SCRIPT: "278aabc77cf32ab8fea8e84f80667eeb88ddc29255f646a1616d88bd4664f279",
    G0078_SCRIPT: "6aec90e28318b45680d3ee94254ff491d5eab89df9eec112fe9b5e66ce4f5229",
    G0073_SCRIPT: "333dba4065c08d54742177941305c13841e6237001f364cf5a68a9e4ec2ebf67",
    G0074_SCRIPT: "269472b1eaeb38db852f92e0587243bba6429a300a7acdd35e0930a6b235f10d",
    G0075_SCRIPT: "ba169bb9b3734c14d30afebba925a358e6f68a0cdd9734a30d78390438567bab",
    G0075_OUTCOME: "ec8f1f1213f9105a5aa51d1b842ac2dc331d82224157d598a7caf0af93425371",
}
EXPECTED_FULL_RAW_SHA256 = (
    "41498698f122d01b624cf83e48f7e36c0b56082a4062654e36a55a7c34c49095"
)
EXPECTED_G0078_SCIENCE_SHA256 = (
    "0bb1a524503359529bb592030f220be86d88756b797e55c4be04c031852bd573"
)

FAREY_F6 = (
    (0, 1),
    (1, 6),
    (1, 5),
    (1, 4),
    (1, 3),
    (2, 5),
    (1, 2),
    (3, 5),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (1, 1),
)

CANDIDATE_NAMES = ("M1", "M2", "CY", "M3", "M4", "M5", "P", "Q", "R")


class AnalysisError(RuntimeError):
    """A binding, exact identity, or deterministic replay check failed."""


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise AnalysisError(f"not a regular file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def raw_array_sha256(array: np.ndarray, row_block: int = 256) -> str:
    if array.ndim != 2:
        raise AnalysisError("raw array binding requires a matrix")
    digest = hashlib.sha256()
    for start in range(0, array.shape[0], row_block):
        value = np.ascontiguousarray(array[start : start + row_block])
        digest.update(memoryview(value).cast("B"))
    return digest.hexdigest()


def read_gzip_json(path: Path) -> dict[str, object]:
    with gzip.open(path, "rt", encoding="utf-8") as source:
        value = json.load(source)
    if not isinstance(value, dict):
        raise AnalysisError(f"expected a JSON object: {path}")
    return value


def portable(path: Path) -> str:
    return str(path.relative_to(ROOT))


def fraction_text(value: Fraction) -> str:
    if value.denominator == 1:
        return str(value.numerator)
    return f"{value.numerator}/{value.denominator}"


def positive_profiles() -> list[tuple[int, int, int, int]]:
    profiles = [
        (c0, c1, c2, N - c0 - c1 - c2)
        for c0 in range(1, N - 2)
        for c1 in range(1, N - c0 - 1)
        for c2 in range(1, N - c0 - c1)
        if N - c0 - c1 - c2 >= 1
    ]
    if len(profiles) != PROFILES_PER_PANEL:
        raise AnalysisError("positive-profile census drift")
    return profiles


def all_four_profiles() -> list[tuple[int, int, int, int]]:
    return [
        (zero, one, two, N - zero - one - two)
        for zero in range(N + 1)
        for one in range(N + 1 - zero)
        for two in range(N + 1 - zero - one)
    ]


def all_three_profiles() -> list[tuple[int, int, int]]:
    return [
        (zero, middle, N - zero - middle)
        for zero in range(N + 1)
        for middle in range(N + 1 - zero)
    ]


def assignment_count(profile: Sequence[int]) -> int:
    value = factorial(sum(profile))
    for count in profile:
        value //= factorial(count)
    return value


def panel_ratios() -> list[tuple[int, int]]:
    ratios: list[tuple[int, int]] = []
    seen: set[tuple[int, int]] = set()
    counter = 0
    while len(ratios) < PANELS:
        digest = hashlib.sha256(
            f"{PANEL_SEED};panel={counter}\n".encode()
        ).digest()
        first = 1 + int.from_bytes(digest[:8], "big") % (DENOMINATOR - 1)
        second = 1 + int.from_bytes(digest[8:16], "big") % (DENOMINATOR - 1)
        counter += 1
        if first == second:
            continue
        ratio = tuple(sorted((first, second)))
        if ratio in seen:
            continue
        seen.add(ratio)
        ratios.append(ratio)
    return ratios


def falling(value: int, count: int) -> int:
    if count > value:
        return 0
    return factorial(value) // factorial(value - count)


def subset_max_row(
    profile: Sequence[int], levels: Sequence[int], subset_size: int
) -> int:
    """Assignment sum of max(x_1,...,x_subset_size)."""
    total = assignment_count(profile)
    denominator = falling(N, subset_size)
    result = 0
    cumulative = 0
    for level, count in zip(levels, profile, strict=True):
        previous = cumulative
        cumulative += count
        at_most = total * falling(cumulative, subset_size) // denominator
        below = total * falling(previous, subset_size) // denominator
        result += (at_most - below) * int(level)
    return result


def tuple_completion_weights(
    profiles: Sequence[Sequence[int]], colours: int, arity: int = 5
) -> tuple[np.ndarray, np.ndarray]:
    codes = np.asarray(list(product(range(colours), repeat=arity)), dtype=np.int8)
    usage = np.stack([(codes == colour).sum(axis=1) for colour in range(colours)], axis=1)
    weights = np.zeros((len(profiles), len(codes)), dtype=np.int64)
    factorials = [factorial(index) for index in range(N + 1)]
    for row, profile_value in enumerate(profiles):
        profile = np.asarray(profile_value, dtype=np.int8)
        valid = np.all(usage <= profile, axis=1)
        remainder = profile[None, :] - usage
        divisor = np.ones(len(codes), dtype=np.int64)
        for colour in range(colours):
            divisor *= np.asarray(
                [factorials[int(value)] for value in remainder[:, colour]],
                dtype=np.int64,
            )
        weights[row, valid] = factorials[N - arity] // divisor[valid]
    return codes, weights


def candidate_values(codes: np.ndarray, levels: Sequence[int]) -> np.ndarray:
    z = np.asarray(levels, dtype=np.int64)[codes]
    x1, x2, x3, x4, x5 = z.T
    p_value = np.maximum(
        np.maximum(2 * x5, x1 + x2),
        np.maximum(x1, x3) + np.maximum(x1, x4),
    )
    q_value = np.maximum(2 * x5, np.maximum(x1 + x2, x3 + x4))
    r_value = np.maximum(
        np.maximum(2 * x5, x1 + x3), np.maximum(x1 + x2, x3 + x4)
    )
    return np.column_stack(
        (
            x1,
            np.maximum(x1, x2),
            np.maximum(2 * x1, x2 + x3),
            np.maximum.reduce((x1, x2, x3)),
            np.maximum.reduce((x1, x2, x3, x4)),
            np.maximum.reduce((x1, x2, x3, x4, x5)),
            p_value,
            q_value,
            r_value,
        )
    )


def build_candidate_columns() -> np.ndarray:
    positive = positive_profiles()
    codes4, weights_positive = tuple_completion_weights(positive, 4)
    blocks = [
        weights_positive @ candidate_values(codes4, (0, first, second, DENOMINATOR))
        for first, second in panel_ratios()
    ]

    profiles4 = all_four_profiles()
    if len(profiles4) != 364:
        raise AnalysisError("four-profile census drift")
    _, weights4 = tuple_completion_weights(profiles4, 4)
    old_blocks = [weights4 @ candidate_values(codes4, (0, 1, 2, 3))]

    profiles3 = all_three_profiles()
    if len(profiles3) != 78:
        raise AnalysisError("three-profile census drift")
    codes3, weights3 = tuple_completion_weights(profiles3, 3)
    old_blocks.extend(
        weights3 @ candidate_values(codes3, (0, numerator, denominator))
        for numerator, denominator in FAREY_F6
    )
    result = np.ascontiguousarray(np.vstack((*blocks, *old_blocks)), dtype=np.int64)
    if result.shape != (ROWS, len(CANDIDATE_NAMES)):
        raise AnalysisError(f"candidate matrix shape drift: {result.shape}")
    return result


def nmod_from_int64(array: np.ndarray, prime: int = PRIME) -> nmod_mat:
    value = np.ascontiguousarray(array)
    reduced = np.empty(value.shape, dtype=np.uint32)
    np.remainder(value, prime, out=reduced, casting="unsafe")
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def nmod_column_matrix_to_numpy(matrix: nmod_mat) -> np.ndarray:
    return np.fromiter(
        (int(matrix[row, column]) for row in range(matrix.nrows()) for column in range(matrix.ncols())),
        dtype=np.int64,
        count=matrix.nrows() * matrix.ncols(),
    ).reshape(matrix.nrows(), matrix.ncols())


def rank_mod(array: np.ndarray) -> int:
    return int(nmod_from_int64(array).rank())


def verify_file_bindings() -> dict[str, object]:
    bindings: dict[str, object] = {}
    for path, expected in EXPECTED_FILE_SHA256.items():
        observed = sha256_path(path)
        if observed != expected:
            raise AnalysisError(f"binding drift for {path}: {observed} != {expected}")
        bindings[portable(path)] = {"sha256": observed, "bytes": path.stat().st_size}
    return bindings


def load_full_subject() -> tuple[np.ndarray, dict[str, object]]:
    if not FULL_CACHE.is_file() or FULL_CACHE.is_symlink():
        raise AnalysisError(
            "missing regular G-0076 full-N cache; regenerate it with the frozen G-0076 producer"
        )
    full = np.load(FULL_CACHE, mmap_mode="r", allow_pickle=False)
    if full.shape != (ROWS, AUGMENTED_COLUMNS) or full.dtype != np.dtype("<i8"):
        raise AnalysisError(f"full subject shape/dtype drift: {full.shape}, {full.dtype}")
    observed = raw_array_sha256(full)
    if observed != EXPECTED_FULL_RAW_SHA256:
        raise AnalysisError(f"full subject raw hash drift: {observed}")
    return full, {
        "path": portable(FULL_CACHE),
        "raw_int64_c_sha256": observed,
        "shape": list(full.shape),
        "dtype": str(full.dtype),
    }


def certificate_data() -> tuple[dict[str, object], dict[str, object]]:
    outcome = read_gzip_json(G0078_OUTCOME)
    if outcome.get("scientific_payload_sha256") != EXPECTED_G0078_SCIENCE_SHA256:
        raise AnalysisError("G-0078 scientific payload drift")
    science = outcome.get("scientific_payload")
    if not isinstance(science, dict):
        raise AnalysisError("missing G-0078 scientific payload")
    modular = read_gzip_json(G0077_MODULAR)
    return science, modular


def exact_certificate_replay(
    full: np.ndarray, science: dict[str, object]
) -> tuple[dict[str, object], list[int], list[int], list[int], int, int]:
    rows = [int(value) for value in science["selected_raw_rows"]]
    divisors = [int(value) for value in science["selected_raw_row_divisors"]]
    numerators = [int(value) for value in science["integer_dual_numerators"]]
    failing_row = int(science["failing_raw_row"])
    failing_divisor = int(science["failing_raw_row_divisor"])
    failing_weight = int(science["integer_failing_row_weight"])
    selected_columns = [int(value) for value in science["selected_A_columns"]]
    if not (
        len(rows) == len(divisors) == len(numerators) == len(selected_columns) == 229
    ):
        raise AnalysisError("G-0078 certificate census drift")
    if len(set(rows)) != len(rows) or failing_row in set(rows):
        raise AnalysisError("duplicate certificate row")
    if any(value == 0 for value in numerators) or failing_weight == 0:
        raise AnalysisError("certificate support contains a zero weight")

    selected_raw = np.ascontiguousarray(full[np.asarray(rows, dtype=np.intp)])
    divisor_array = np.asarray(divisors, dtype=np.int64)
    if np.any(np.remainder(selected_raw, divisor_array[:, None])):
        raise AnalysisError("selected raw-row divisor fails exact division")
    failing_raw = np.ascontiguousarray(full[failing_row])
    if np.any(np.remainder(failing_raw, failing_divisor)):
        raise AnalysisError("failing raw-row divisor fails exact division")

    square = np.ascontiguousarray(
        selected_raw[:, np.asarray(selected_columns, dtype=np.intp)]
        // divisor_array[:, None]
    )
    square_rank = int(
        fmpz_mat(square.shape[0], square.shape[1], memoryview(square.ravel())).rank()
    )
    if square_rank != 229:
        raise AnalysisError(f"selected exact square rank drift: {square_rank}")

    numerator_row = fmpz_mat(len(rows), 1, numerators).transpose()
    first_nonzero: dict[str, str | int] | None = None
    for start in range(0, A_COLUMNS, 64):
        stop = min(start + 64, A_COLUMNS)
        primitive = np.ascontiguousarray(
            selected_raw[:, start:stop] // divisor_array[:, None]
        )
        residual = numerator_row * fmpz_mat(
            primitive.shape[0], primitive.shape[1], memoryview(primitive.ravel())
        )
        failing = failing_raw[start:stop] // failing_divisor
        for local in range(stop - start):
            value = int(residual[0, local]) + failing_weight * int(failing[local])
            if value:
                first_nonzero = {
                    "column": start + local,
                    "residual": str(value),
                }
                break
        if first_nonzero is not None:
            break
    if first_nonzero is not None:
        raise AnalysisError(f"exact certificate replay failed: {first_nonzero}")

    primitive_target = selected_raw[:, A_COLUMNS] // divisor_array
    target_pairing = sum(
        numerator * int(value)
        for numerator, value in zip(numerators, primitive_target, strict=True)
    ) + failing_weight * int(failing_raw[A_COLUMNS] // failing_divisor)
    if str(target_pairing) != str(science["exact_target_pairing"]) or target_pairing == 0:
        raise AnalysisError("exact target pairing drift")

    first_mutant_column = None
    primitive_first_row = selected_raw[0, :A_COLUMNS] // divisors[0]
    support = np.flatnonzero(primitive_first_row)
    if support.size:
        first_mutant_column = int(support[0])
    if first_mutant_column is None:
        raise AnalysisError("one-unit numerator mutant unexpectedly annihilates every A column")

    circuit_rows = [*rows, failing_row]
    return (
        {
            "all_8107_A_columns_annihilated_exactly": True,
            "target_pairing": str(target_pairing),
            "target_pairing_nonzero": True,
            "selected_exact_square_rank": square_rank,
            "selected_rows": len(rows),
            "circuit_rows": len(circuit_rows),
            "left_kernel_dimension_on_circuit_rows": 1,
            "all_circuit_weights_nonzero": True,
            "is_vector_matroid_circuit": True,
            "one_unit_first_numerator_mutant_rejected": True,
            "one_unit_mutant_first_nonzero_column": first_mutant_column,
            "circuit_raw_rows_sha256": canonical_sha256(circuit_rows),
            "reason": (
                "229 rows are independent by an exact nonsingular square; the failing row "
                "is their exact nontrivial combination on every A column; every coefficient "
                "in the unique dependence is nonzero"
            ),
        },
        rows,
        divisors,
        numerators,
        failing_row,
        failing_weight,
    )


def dual_weight(rows: list[int], divisors: list[int], numerators: list[int], failing_row: int,
                failing_divisor: int, failing_weight: int) -> dict[int, Fraction]:
    result = {
        row: Fraction(numerator, divisor)
        for row, divisor, numerator in zip(rows, divisors, numerators, strict=True)
    }
    result[failing_row] = Fraction(failing_weight, failing_divisor)
    return result


def panel_profile_structure(weights: dict[int, Fraction]) -> dict[str, object]:
    if any(not 0 <= row < PANELS * PROFILES_PER_PANEL for row in weights):
        raise AnalysisError("dual support is not contained in G-0075 panel rows")
    panels = sorted({row // PROFILES_PER_PANEL for row in weights})
    profile_indices = sorted({row % PROFILES_PER_PANEL for row in weights})
    if panels != list(range(21)):
        raise AnalysisError(f"unexpected panel support: {panels}")
    matrix = np.zeros((len(panels), PROFILES_PER_PANEL), dtype=np.int64)
    for row, value in weights.items():
        matrix[row // PROFILES_PER_PANEL, row % PROFILES_PER_PANEL] = (
            (value.numerator % PRIME) * pow(value.denominator, -1, PRIME)
        ) % PRIME
    modular_rank = rank_mod(matrix)
    if modular_rank != len(panels):
        raise AnalysisError(f"panel/profile weight rank drift: {modular_rank}")
    ratios = panel_ratios()
    counts = [sum(row // PROFILES_PER_PANEL == panel for row in weights) for panel in panels]
    profile_coverage = {
        str(index): sum(row % PROFILES_PER_PANEL == index for row in weights)
        for index in profile_indices
    }
    return {
        "support_rows": len(weights),
        "panels": len(panels),
        "panel_indices": panels,
        "panel_ratios": [list(ratios[index]) for index in panels],
        "support_count_by_panel": counts,
        "profile_types": len(profile_indices),
        "profile_indices": profile_indices,
        "profile_coverage": profile_coverage,
        "panel_profile_array_shape": [len(panels), PROFILES_PER_PANEL],
        "rank_mod_1000003": modular_rank,
        "rank_over_Q": len(panels),
        "rank_over_Q_reason": (
            "full row rank modulo 1,000,003 exhibits a nonzero integer minor, "
            "so the rational rank is at least 21 and cannot exceed 21"
        ),
        "separable_rank_one": False,
    }


def exact_subset_max_prices(
    weights: dict[int, Fraction], target_pairing: Fraction
) -> tuple[dict[str, object], list[Fraction]]:
    profiles = positive_profiles()
    ratios = panel_ratios()
    prices: list[Fraction] = [Fraction(0)] * (N + 1)
    records: dict[str, object] = {}
    for subset_size in range(1, N + 1):
        price = Fraction(0)
        for row, weight in weights.items():
            panel, profile_index = divmod(row, PROFILES_PER_PANEL)
            first, second = ratios[panel]
            price += weight * subset_max_row(
                profiles[profile_index], (0, first, second, DENOMINATOR), subset_size
            )
        prices[subset_size] = price
        records[str(subset_size)] = {
            "pairing": fraction_text(price),
            "ratio_to_target": fraction_text(price / target_pairing),
            "nonzero": price != 0,
        }
    expected = {
        1: Fraction(0),
        2: Fraction(0),
        3: Fraction(614_792, 533_093),
        4: Fraction(646_637, 533_093),
        **{index: Fraction(1) for index in range(5, 12)},
    }
    for index, wanted in expected.items():
        if prices[index] / target_pairing != wanted:
            raise AnalysisError(f"M_{index} exact price ratio drift")
    return records, prices


def order_statistic_vector(prices: list[Fraction], target: Fraction) -> dict[str, object]:
    normalized = {index: prices[index] / target for index in range(1, N + 1)}
    raw_subset_prices = {
        index: Fraction(comb(N, index)) * normalized[index]
        for index in range(1, N + 1)
    }
    order_prices: dict[int, Fraction] = {}
    for index in range(N, 0, -1):
        order_prices[index] = raw_subset_prices[index] - sum(
            Fraction(comb(later - 1, index - 1)) * order_prices[later]
            for later in range(index + 1, N + 1)
        )
    denominator = 1
    for value in order_prices.values():
        denominator = lcm(denominator, value.denominator)
    numerators = [int(order_prices[index] * denominator) for index in range(1, N + 1)]
    common = 0
    for value in numerators:
        common = gcd(common, abs(value))
    if common > 1:
        denominator //= common
        numerators = [value // common for value in numerators]
    expected = [
        0,
        5_150_988,
        -8_945_012,
        3_454_783,
        48_463,
        48_463,
        48_463,
        48_463,
        48_463,
        48_463,
        48_463,
    ]
    if denominator != 48_463 or numerators != expected or sum(numerators) != 0:
        raise AnalysisError("order-statistic transform drift")
    return {
        "sorted_coordinate_convention": "x_(1) <= ... <= x_(11)",
        "primitive_integer_vector": numerators,
        "denominator_relative_to_target": denominator,
        "identity": "L(x_(j)) / L(MAX11) = vector[j] / 48463",
        "translation_sum_zero": True,
        "derivation": (
            "binomial inversion of E_k=sum_{|S|=k} max_{i in S} x_i="
            "sum_{j=k}^11 binom(j-1,k-1)x_(j)"
        ),
    }


def exact_candidate_prices(
    candidates: np.ndarray, weights: dict[int, Fraction], target: Fraction
) -> dict[str, object]:
    records: dict[str, object] = {}
    for column, name in enumerate(CANDIDATE_NAMES):
        price = sum(weight * int(candidates[row, column]) for row, weight in weights.items())
        records[name] = {
            "pairing": fraction_text(price),
            "ratio_to_target": fraction_text(price / target),
            "nonzero": price != 0,
        }
    if records["M1"]["nonzero"] or records["M2"]["nonzero"] or records["CY"]["nonzero"]:
        raise AnalysisError("frozen carrier exact price drift")
    if not all(bool(records[name]["nonzero"]) for name in ("M3", "M4", "M5", "P", "Q", "R")):
        raise AnalysisError("expected P^2 escape candidate has zero exact price")
    if not np.array_equal(2 * candidates[:, 5], 4 * candidates[:, 6] + candidates[:, 7] - 4 * candidates[:, 8]):
        raise AnalysisError("symmetrized MAX5 decomposition relation failed")
    return records


def modular_quotient_analysis(
    full: np.ndarray, candidates: np.ndarray, modular: dict[str, object]
) -> tuple[dict[str, object], dict[str, object]]:
    controls: dict[str, object] = {}
    for candidate_column, full_column, name in (
        (0, 8_104, "M1"),
        (1, 8_105, "M2"),
        (2, 8_106, "CY"),
    ):
        matches = np.array_equal(candidates[:, candidate_column], full[:, full_column])
        if not matches:
            raise AnalysisError(f"{name} row construction does not match frozen carrier")
        controls[f"{name}_matches_frozen_column_{full_column}"] = True

    rows = np.asarray(modular.get("basis_rows"), dtype=np.intp)
    columns = np.asarray(modular.get("basis_columns"), dtype=np.intp)
    if rows.shape != (RANK_A,) or columns.shape != (RANK_A,):
        raise AnalysisError("G-0077 basis census drift")
    if len(set(map(int, rows))) != RANK_A or len(set(map(int, columns))) != RANK_A:
        raise AnalysisError("G-0077 basis duplication")

    basis = np.ascontiguousarray(full[np.ix_(rows, columns)])
    basis_field = nmod_from_int64(basis)
    if int(basis_field.rank()) != RANK_A:
        raise AnalysisError("frozen G-0077 basis lost modular rank")

    values = np.ascontiguousarray(
        np.column_stack((candidates[:, 3:], full[:, A_COLUMNS])), dtype=np.int64
    )
    rhs_field = nmod_from_int64(np.ascontiguousarray(values[rows]))
    coordinates_field = basis_field.solve(rhs_field)
    coordinates = nmod_column_matrix_to_numpy(coordinates_field)
    del basis_field, rhs_field, coordinates_field, basis

    residual = np.empty(values.shape, dtype=np.int64)
    for start in range(0, ROWS, 64):
        stop = min(start + 64, ROWS)
        raw = np.ascontiguousarray(full[start:stop, :A_COLUMNS][:, columns])
        reduced = np.empty(raw.shape, dtype=np.int64)
        np.remainder(raw, PRIME, out=reduced)
        predicted = (reduced @ coordinates) % PRIME
        residual[start:stop] = (values[start:stop] - predicted) % PRIME
    if np.count_nonzero(residual[rows]):
        raise AnalysisError("quotient residual is nonzero on basis rows")

    quotient_names = ("M3", "M4", "M5", "P", "Q", "R", "MAX11")
    residual_hashes = {
        name: hashlib.sha256(
            np.ascontiguousarray(residual[:, index], dtype="<u4").tobytes()
        ).hexdigest()
        for index, name in enumerate(quotient_names)
    }
    residual_nonzero_counts = {
        name: int(np.count_nonzero(residual[:, index]))
        for index, name in enumerate(quotient_names)
    }

    groups: dict[str, list[int]] = {
        "M3": [0],
        "M4": [1],
        "M5": [2],
        "P": [3],
        "Q": [4],
        "R": [5],
        "M3_M4": [0, 1],
        "P_Q_R": [3, 4, 5],
        "M3_M4_M5_P_Q_R": [0, 1, 2, 3, 4, 5],
    }
    group_records: dict[str, object] = {}
    for name, selected in groups.items():
        candidate_rank = rank_mod(residual[:, selected])
        augmented_rank = rank_mod(residual[:, [*selected, 6]])
        group_records[name] = {
            "candidate_columns": [quotient_names[index] for index in selected],
            "candidate_quotient_rank": candidate_rank,
            "with_target_quotient_rank": augmented_rank,
            "epsilon_mod_1000003": augmented_rank - candidate_rank,
        }
    expected = {
        "M3": (1, 2),
        "M4": (1, 2),
        "M5": (1, 2),
        "P": (1, 2),
        "Q": (1, 2),
        "R": (1, 2),
        "M3_M4": (2, 3),
        "P_Q_R": (3, 4),
        "M3_M4_M5_P_Q_R": (5, 6),
    }
    for name, (rank_value, augmented_value) in expected.items():
        record = group_records[name]
        if (
            record["candidate_quotient_rank"] != rank_value
            or record["with_target_quotient_rank"] != augmented_value
        ):
            raise AnalysisError(f"modular quotient result drift for {name}")
    controls["quotient_zero_on_all_6876_basis_rows"] = True
    controls["symmetrized_MAX5_relation_holds_on_all_16738_rows"] = True
    return (
        {
            "evidence_status": "DISCOVERY_ONLY_SINGLE_PRIME",
            "prime": PRIME,
            "base_A_rank_mod_prime": RANK_A,
            "quotient_residual_sha256_uint32_le": residual_hashes,
            "quotient_residual_nonzero_counts": residual_nonzero_counts,
            "groups": group_records,
            "interpretation": (
                "all six legal escape columns leave a one-dimensional modular target gain; "
                "this does not prove rational nonmembership because the registered prime may "
                "be exceptional for the augmented family"
            ),
        },
        controls,
    )


def run_self_test() -> None:
    if len(positive_profiles()) != 120 or len(all_four_profiles()) != 364 or len(all_three_profiles()) != 78:
        raise AnalysisError("profile self-test failed")
    ratios = panel_ratios()
    if ratios[0] != (160, 247) or ratios[20] != (120, 183) or len(ratios) != 128:
        raise AnalysisError("panel-ratio self-test failed")
    for profiles, colours in ((positive_profiles(), 4), (all_four_profiles(), 4), (all_three_profiles(), 3)):
        _codes, weights = tuple_completion_weights(profiles, colours)
        observed = weights.sum(axis=1)
        expected = np.asarray([assignment_count(profile) for profile in profiles], dtype=np.int64)
        if not np.array_equal(observed, expected):
            raise AnalysisError("tuple-completion weight self-test failed")
    print("SELF_TEST_PASS")


def analyze() -> dict[str, object]:
    bindings = verify_file_bindings()
    full, full_binding = load_full_subject()
    bindings[portable(FULL_CACHE)] = full_binding
    science, modular = certificate_data()
    (
        replay,
        rows,
        divisors,
        numerators,
        failing_row,
        failing_weight,
    ) = exact_certificate_replay(full, science)
    failing_divisor = int(science["failing_raw_row_divisor"])
    weights = dual_weight(
        rows, divisors, numerators, failing_row, failing_divisor, failing_weight
    )
    target = Fraction(int(replay["target_pairing"]))
    structure = panel_profile_structure(weights)
    subset_prices, price_values = exact_subset_max_prices(weights, target)
    order_vector = order_statistic_vector(price_values, target)
    candidates = build_candidate_columns()
    candidate_prices = exact_candidate_prices(candidates, weights, target)
    modular_analysis, controls = modular_quotient_analysis(full, candidates, modular)
    controls.update(
        {
            "all_frozen_file_bindings_match": True,
            "full_subject_raw_hash_matches": True,
            "exact_certificate_all_column_replay_passes": True,
            "exact_target_pairing_matches_G0078": True,
            "panel_ratio_and_profile_reconstruction_passes": True,
            "M1_M2_CY_exact_prices_are_zero": True,
            "M3_M4_exact_prices_are_nonzero": True,
        }
    )
    exact = {
        "certificate_replay_and_circuit": replay,
        "panel_profile_structure": structure,
        "subset_max_orbit_prices": {
            "definition": "M_k = Sym_avg(max(x_1,...,x_k))",
            "target_pairing_symbol": "T=L(MAX11)",
            "values": subset_prices,
        },
        "order_statistic_restriction": order_vector,
        "candidate_prices": candidate_prices,
        "P2_falsifiers": {
            "M3": {
                "legal_block": "triangle conv([e1,e2] union {e3}) in P^2",
                "exact_pairing_nonzero": True,
            },
            "M4": {
                "legal_block": "tetrahedron conv([e1,e2] union [e3,e4]) in P^2",
                "exact_pairing_nonzero": True,
            },
            "conclusion": (
                "L is not an identity annihilating all P^2 blocks and therefore is not, by "
                "itself, an unrestricted four-level face-gluing obstruction"
            ),
        },
        "MAX5_orbit_relation": "2*M5 = 4*P + Q - 4*R on all bound rows",
    }
    payload = {
        "schema": "max11-g0078-dual-structure-v1",
        "script_sha256": sha256_path(SCRIPT),
        "bindings": bindings,
        "exact_results": exact,
        "modular_discovery": modular_analysis,
        "controls": controls,
        "claim_boundary": {
            "proved_exactly": (
                "the frozen functional is a 230-row circuit annihilating the frozen 8107-column "
                "family; its listed prices, subset-max transform, and P^2 falsifiers are exact"
            ),
            "not_proved": (
                "no unrestricted MAX11 lower bound, no general face-gluing theorem, no novelty "
                "claim, and no rational conclusion for the candidate-augmented full system"
            ),
            "single_prime_only": (
                "the M3/M4/M5/P/Q/R full-system quotient ranks are discovery evidence modulo "
                "1,000,003 and may not be promoted to characteristic zero"
            ),
        },
    }
    payload["scientific_payload_sha256"] = canonical_sha256(
        {
            key: value
            for key, value in payload.items()
            if key not in ("script_sha256", "bindings", "scientific_payload_sha256")
        }
    )
    return payload


def write_output(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_bytes(value))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--self-test", action="store_true")
    group.add_argument("--output", type=Path)
    group.add_argument("--check-frozen", action="store_true")
    arguments = parser.parse_args()
    if arguments.self_test:
        run_self_test()
        return
    value = analyze()
    if arguments.output is not None:
        write_output(arguments.output, value)
        print(canonical_sha256(value))
        return
    if not FROZEN_OUTPUT.is_file() or FROZEN_OUTPUT.is_symlink():
        raise AnalysisError(f"missing frozen output: {FROZEN_OUTPUT}")
    expected = FROZEN_OUTPUT.read_bytes()
    observed = canonical_bytes(value)
    if observed != expected:
        raise AnalysisError(
            f"frozen output drift: observed={hashlib.sha256(observed).hexdigest()} "
            f"expected={hashlib.sha256(expected).hexdigest()}"
        )
    print(f"FROZEN_REPLAY_PASS sha256={hashlib.sha256(observed).hexdigest()}")


if __name__ == "__main__":
    main()
