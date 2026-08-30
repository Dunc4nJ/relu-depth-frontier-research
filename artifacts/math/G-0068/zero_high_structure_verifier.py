#!/usr/bin/env python3
"""Fail-closed structural certificate for G-0068's zero-high columns.

This verifier rebuilds the registered single-edge subject through the pinned
G-0049 implementation, applies an exact subset dynamic program to every
genuine signed-mass-five atom, and independently checks the alternating-cycle
description inside this *finite pinned natural family*.  It deliberately does
not assert a converse for arbitrary signed graphs or arbitrary MAX11 atoms.

``--self-test`` runs exhaustive small cases plus semantic controls without
writing.  ``--run`` performs the complete 11,542-column census, replays all
526 predicted zeros through G-0049's complete exact normal form, and writes a
deterministic gzip report (mtime zero) without overwriting an existing file.
"""

from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
import gzip
import hashlib
import importlib.util
import itertools
import json
from math import factorial, gcd
import multiprocessing as mp
import os
from pathlib import Path
import sys
from types import ModuleType
from typing import Any, Iterable, Iterator, Sequence


N = 11
SCHEMA = "max11-g0068-zero-high-structure-certificate-v1"
RESULT = "PASS_PINNED_NATURAL_FAMILY_ONLY"

EXPECTED_REGISTERED_COLUMNS = 13_419
EXPECTED_SAME_COLUMNS = 9_804
EXPECTED_CROSS_COLUMNS = 3_615
EXPECTED_SAME_MASS5_COLUMNS = 7_927
EXPECTED_SAME_MASS4_COLUMNS = 1_877
EXPECTED_GENUINE_COLUMNS = 11_542
EXPECTED_ZERO_HIGH_COLUMNS = 526
EXPECTED_NONZERO_HIGH_COLUMNS = 11_016

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

# Compact-JSON plus one newline, as emitted by canonical_bytes().
EXPECTED_ZERO_SAME_CLASS_INDICES_SHA256 = (
    "b9fe1c96bb5ec3ff8508f24b5d13366f863b6263b2a8904c561a9a6b2789f9e9"
)
EXPECTED_ZERO_SUBJECT_COLUMNS_SHA256 = (
    "b7be6bac98d5600cd4901ec3234ef3182504237ffda4f336da164cef380ab441"
)
EXPECTED_NONZERO_WITNESS_ROWS_SHA256 = (
    "a92516927060bc05581b9e34be131228399cb6a852bda23ab8faa85570f5564d"
)
EXPECTED_ZERO_SEMANTIC_ROWS_SHA256 = (
    "74c5d285b925bd788436d4403a4cc159afcb64d37abe929b0f3964ee94d07f93"
)
EXPECTED_NONZERO_CHARGE_ROWS_SHA256 = (
    "487b130350478248281e9313dd36cdcf8a26105d06f992a9460c369989c854c4"
)

EXPECTED_ZERO_CYCLE_LENGTH_HISTOGRAM = {4: 507, 6: 19}
EXPECTED_ZERO_CHARGE_HISTOGRAM = {
    -20: 6,
    -12: 5,
    -10: 56,
    -8: 6,
    -6: 61,
    -4: 45,
    -2: 32,
    0: 207,
    2: 25,
    4: 43,
    6: 14,
    8: 8,
    10: 18,
}

EXPECTED_SMALL_CASES = {
    (4, 2): (90, 72, 18),
    (5, 2): (810, 810, 0),
    (5, 3): (4_100, 3_270, 830),
    (5, 4): (3_150, 1_440, 1_710),
}

EXPECTED_SEMANTIC_CONTROLS: dict[str, dict[str, object]] = {
    "same_1": {
        "degree5_high_key_count": 750,
        "semantic_column_sha256": (
            "99485243d82e24ebfae8d35782c5d90980066e067c49f2bbee28e5550db4135f"
        ),
    },
    "cross_0": {
        "degree5_high_key_count": 2_567,
        "semantic_column_sha256": (
            "30604df51a70a0b81527c0bf395a780b2f67c547aa0607b9d3329be6b7facc18"
        ),
    },
    "cross_3614": {
        "degree5_high_key_count": 2_996,
        "semantic_column_sha256": (
            "0038b72a3e9e285ca953d3f79f434fb0ceca3aabed501dfc6486c23274d3581d"
        ),
    },
}

EXPECTED_ZERO_WITNESSES: dict[int, dict[str, object]] = {
    161: {
        "boolean_charge": 0,
        "total_hinge_key_count": 13_208,
        "semantic_column_sha256": (
            "f974ab397de0a03e7f177ba87a05ecbbc2ab879f0033c37033fa5b1ae53e458a"
        ),
    },
    3_600: {
        "boolean_charge": 0,
        "total_hinge_key_count": 13_818,
        "semantic_column_sha256": (
            "bbf1a2120103c99fe246d5cca61274c60a9794e1c7556ac0d329f6cbc9f4ad02"
        ),
    },
    7_172: {
        "boolean_charge": -12,
        "total_hinge_key_count": 16_108,
        "semantic_column_sha256": (
            "f8d330b3fcbaca7d5dc0562828b2a6684614dabcd351eafc2b1e109ad6ebfcab"
        ),
    },
}

EXPECTED_MUTATION = {
    "degree5_high_key_count": 12_813,
    "semantic_column_sha256": (
        "a5b62c202adf6bad08f6073ed13b79d58ce47df373143e03331498715d5b49ea"
    ),
    "first_degree5_key_and_coefficient": [
        [0, 0, 0, 0, 0, 1, -2, -2, -1, 2, 2],
        960,
    ],
}

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT_PATH = Path(__file__).resolve()
G0049_SCRIPT = ROOT / "artifacts/math/G-0049/verify_g0046_relation.py"
G0068_SCRIPT = ROOT / "artifacts/math/G-0068/single_edge_degree5_kernel_gate.py"
CERTIFICATE = ROOT / (
    "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
)
SAME_CLASSES = ROOT / "artifacts/math/G-0006/isomorphism_classes_v2.json"
CROSS_CLASSES = ROOT / "artifacts/math/G-0009/cross_component_classes.json"
DEFAULT_OUTPUT = HERE / "zero_high_structure_verifier_v1.json.gz"

EXPECTED_INPUT_HASHES = {
    "g0049_semantics_script_sha256": (
        "0b0a11a8c7883174dd895024d71d580c36005edd28c75c29e96f46ab8d246d04"
    ),
    "g0068_subject_contract_script_sha256": (
        "80b467fe65835a3d36c5adde9a87bb8191b38f69734718784db38f0b356a7f61"
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
}
INPUT_PATHS = {
    "g0049_semantics_script_sha256": G0049_SCRIPT,
    "g0068_subject_contract_script_sha256": G0068_SCRIPT,
    "max10_certificate_sha256": CERTIFICATE,
    "same_classes_sha256": SAME_CLASSES,
    "cross_classes_sha256": CROSS_CLASSES,
}

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class VerificationError(RuntimeError):
    """A pinned input, exact invariant, or expected output drifted."""


@dataclass(frozen=True)
class SubjectColumn:
    subject_column: int
    union_column: int
    family: str
    class_index: int
    pair: Pair


def require(condition: bool, message: str) -> None:
    if not condition:
        raise VerificationError(message)


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise VerificationError(f"bound path is not a regular non-symlink file: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(block_size), b""):
            digest.update(block)
    return digest.hexdigest()


def unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    output: dict[str, object] = {}
    for key, value in pairs:
        if key in output:
            raise VerificationError(f"duplicate JSON key: {key}")
        output[key] = value
    return output


def input_bindings() -> dict[str, str]:
    observed = {label: sha256_path(path) for label, path in INPUT_PATHS.items()}
    require(observed == EXPECTED_INPUT_HASHES, f"upstream input drift: {observed}")
    observed["zero_high_structure_verifier_sha256"] = sha256_path(SCRIPT_PATH)
    return observed


def load_semantics(name: str = "g0068_zero_high_bound_g0049") -> ModuleType:
    require(
        sha256_path(G0049_SCRIPT)
        == EXPECTED_INPUT_HASHES["g0049_semantics_script_sha256"],
        "G-0049 semantic implementation drift",
    )
    spec = importlib.util.spec_from_file_location(name, G0049_SCRIPT)
    if spec is None or spec.loader is None:
        raise VerificationError("cannot import pinned G-0049 semantic implementation")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[int(u), int(v)] for u, v in side] for side in pair]


def cancelled_pair(pair: Pair) -> Pair:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right

    def subtract_in_order(side: Side) -> Side:
        remaining = common.copy()
        output: list[Edge] = []
        for edge in side:
            if remaining[edge]:
                remaining[edge] -= 1
            else:
                output.append(edge)
        return tuple(output)

    return subtract_in_order(pair[0]), subtract_in_order(pair[1])


def cancelled_mass(pair: Pair) -> tuple[int, int]:
    reduced = cancelled_pair(pair)
    return len(reduced[0]), len(reduced[1])


def family_descriptor(
    family: str, class_index: int, union_column: int, pair: Pair
) -> dict[str, object]:
    return {
        "family": family,
        "class_index": class_index,
        "union_column": union_column,
        "pair": serialize_pair(pair),
        "signed_mass": list(cancelled_mass(pair)),
    }


def rebuild_subject(
    semantics: ModuleType,
) -> tuple[list[Pair], list[Pair], list[SubjectColumn], dict[str, object]]:
    same, cross, reconstruction = semantics.build_raw_lift_families()
    require(len(same) == EXPECTED_SAME_COLUMNS, "same class census drift")
    require(len(cross) == EXPECTED_CROSS_COLUMNS, "cross class census drift")
    require(
        semantics.pair_list_sha256(same) == EXPECTED_SAME_REPRESENTATIVES_SHA256,
        "same representative order drift",
    )
    require(
        semantics.pair_list_sha256(cross) == EXPECTED_CROSS_REPRESENTATIVES_SHA256,
        "cross representative order drift",
    )
    require(
        semantics.pair_list_sha256(same + cross)
        == EXPECTED_REGISTERED_REPRESENTATIVES_SHA256,
        "registered representative order drift",
    )

    genuine_descriptors: list[dict[str, object]] = []
    lower_descriptors: list[dict[str, object]] = []
    subject: list[SubjectColumn] = []
    mass_histograms: dict[str, Counter[tuple[int, int]]] = {
        "same": Counter(),
        "cross": Counter(),
    }
    for family, pairs, offset in (
        ("same", same, 0),
        ("cross", cross, EXPECTED_SAME_COLUMNS),
    ):
        for class_index, pair in enumerate(pairs):
            union_column = offset + class_index
            mass = cancelled_mass(pair)
            mass_histograms[family][mass] += 1
            descriptor = family_descriptor(family, class_index, union_column, pair)
            if mass == (5, 5):
                subject.append(
                    SubjectColumn(
                        subject_column=len(subject),
                        union_column=union_column,
                        family=family,
                        class_index=class_index,
                        pair=pair,
                    )
                )
                genuine_descriptors.append(descriptor)
            elif family == "same" and mass == (4, 4):
                lower_descriptors.append(descriptor)
            else:
                raise VerificationError(
                    f"unexpected signed mass at {family}/{class_index}: {mass}"
                )

    require(
        dict(mass_histograms["same"]) == {(5, 5): 7_927, (4, 4): 1_877},
        f"same mass partition drift: {mass_histograms['same']}",
    )
    require(
        dict(mass_histograms["cross"]) == {(5, 5): 3_615},
        f"cross mass partition drift: {mass_histograms['cross']}",
    )
    require(len(subject) == EXPECTED_GENUINE_COLUMNS, "genuine subject census drift")

    genuine_indices = [value["union_column"] for value in genuine_descriptors]
    lower_indices = [value["union_column"] for value in lower_descriptors]
    hashes = {
        "genuine_descriptors_sha256": canonical_sha256(genuine_descriptors),
        "genuine_union_indices_sha256": canonical_sha256(genuine_indices),
        "lower_descriptors_sha256": canonical_sha256(lower_descriptors),
        "lower_union_indices_sha256": canonical_sha256(lower_indices),
    }
    require(
        hashes
        == {
            "genuine_descriptors_sha256": EXPECTED_GENUINE_DESCRIPTORS_SHA256,
            "genuine_union_indices_sha256": EXPECTED_GENUINE_INDICES_SHA256,
            "lower_descriptors_sha256": EXPECTED_LOWER_DESCRIPTORS_SHA256,
            "lower_union_indices_sha256": EXPECTED_LOWER_INDICES_SHA256,
        },
        f"subject descriptor drift: {hashes}",
    )
    controls: dict[str, object] = {
        "registered_columns": len(same) + len(cross),
        "same_columns": len(same),
        "cross_columns": len(cross),
        "same_mass5_columns": mass_histograms["same"][(5, 5)],
        "same_mass4_columns": mass_histograms["same"][(4, 4)],
        "cross_mass5_columns": mass_histograms["cross"][(5, 5)],
        "genuine_mass5_columns": len(subject),
        **hashes,
        "upstream_reconstruction": reconstruction,
    }
    require(
        controls["registered_columns"] == EXPECTED_REGISTERED_COLUMNS,
        "registered subject size drift",
    )
    return same, cross, subject, controls


def signed_neighbour_masks(pair: Pair, n: int) -> tuple[list[int], list[int]]:
    reduced = cancelled_pair(pair)
    require(len(reduced[0]) == len(reduced[1]), "unbalanced reduced pair")
    negative = [0] * n
    positive = [0] * n
    seen: set[Edge] = set()
    for masks, side in ((negative, reduced[0]), (positive, reduced[1])):
        require(len(side) == len(set(side)), "parallel edge within a branch")
        for u, v in side:
            require(1 <= u < v <= n, f"non-loopless edge {(u, v)}")
            edge = (u, v)
            require(edge not in seen, f"uncancelled signed duplicate edge {edge}")
            seen.add(edge)
            u0, v0 = u - 1, v - 1
            masks[u0] |= 1 << v0
            masks[v0] |= 1 << u0
    return negative, positive


def _q_values(negative: Sequence[int], positive: Sequence[int], n: int) -> list[int]:
    q = [0] * (1 << n)
    for mask in range(1, 1 << n):
        bit = mask & -mask
        vertex = bit.bit_length() - 1
        previous = mask ^ bit
        q[mask] = (
            q[previous]
            + (positive[vertex] & previous).bit_count()
            - (negative[vertex] & previous).bit_count()
        )
    return q


def _flag_transition_bits(previous_bits: int, sign_flag: int) -> int:
    output = 0
    for previous_flag in range(4):
        if previous_bits & (1 << previous_flag):
            output |= 1 << (previous_flag | sign_flag)
    return output


FLAG_TRANSITIONS = tuple(
    tuple(_flag_transition_bits(bits, sign) for bits in range(16))
    for sign in (0, 1, 2)
)


def exact_mass5_dp(pair: Pair, n: int = N) -> dict[str, object]:
    """Decide and witness the exact degree-five ordered-cone criterion.

    Left edges have sign -1 and right edges sign +1.  For an order, an added
    vertex must close edges of at most one sign; this is exactly zero local
    cross-sign cancellation.  Since the raw positive mass is the prime 5,
    visiting both signs in q(A)=|E_+[A]|-|E_-[A]| also forces primitive gcd 1.
    Thus the two-bit prefix-sign state is complete for this mass-five subject.
    """

    negative, positive = signed_neighbour_masks(pair, n)
    require(len(cancelled_pair(pair)[0]) == 5, "mass-five DP received other mass")
    q = _q_values(negative, positive, n)
    full = (1 << n) - 1
    require(q[full] == 0, "balanced signed graph has nonzero total q")
    reachable = [0] * (1 << n)
    reachable[0] = 1  # bit 0: neither a negative nor positive prefix seen
    for mask in range(1, 1 << n):
        sign_flag = 1 if q[mask] < 0 else 2 if q[mask] > 0 else 0
        output = 0
        vertex_bits = mask
        while vertex_bits:
            bit = vertex_bits & -vertex_bits
            vertex_bits ^= bit
            vertex = bit.bit_length() - 1
            previous = mask ^ bit
            if (negative[vertex] & previous) and (positive[vertex] & previous):
                continue
            output |= FLAG_TRANSITIONS[sign_flag][reachable[previous]]
        reachable[mask] = output

    if not (reachable[full] & (1 << 3)):
        return {"has_degree5_hinge": False}

    # Reconstruct the first predecessor under the frozen *forward* tie-break:
    # predecessor masks ascending, appended vertices low-to-high, prior flags
    # 0..3.  For one fixed current mask, ascending predecessor masks means the
    # removed/appended vertex is considered high-to-low.
    reverse_order: list[int] = []
    mask = full
    target_flag = 3
    while mask:
        sign_flag = 1 if q[mask] < 0 else 2 if q[mask] > 0 else 0
        found: tuple[int, int, int] | None = None
        for vertex in range(n - 1, -1, -1):
            bit = 1 << vertex
            if not (mask & bit):
                continue
            previous = mask ^ bit
            if (negative[vertex] & previous) and (positive[vertex] & previous):
                continue
            for previous_flag in range(4):
                if (
                    reachable[previous] & (1 << previous_flag)
                    and (previous_flag | sign_flag) == target_flag
                ):
                    found = vertex, previous, previous_flag
                    break
            if found is not None:
                break
        require(found is not None, "DP witness predecessor reconstruction failed")
        vertex, mask, target_flag = found
        reverse_order.append(vertex)
    require(target_flag == 0, "DP witness did not terminate at its initial state")
    order0 = list(reversed(reverse_order))

    previous = 0
    raw: list[int] = []
    prefixes: list[int] = []
    running = 0
    for vertex in order0:
        negative_count = (negative[vertex] & previous).bit_count()
        positive_count = (positive[vertex] & previous).bit_count()
        require(not (negative_count and positive_count), "witness contains cancellation")
        increment = positive_count - negative_count
        raw.append(increment)
        running += increment
        prefixes.append(running)
        previous |= 1 << vertex
    raw_gcd = 0
    for value in raw:
        raw_gcd = gcd(raw_gcd, abs(value))
    require(raw_gcd == 1, f"mass-five active word has unexpected gcd {raw_gcd}")
    require(sum(max(value, 0) for value in raw) == 5, "witness lost raw mass five")
    require(min(prefixes) < 0 < max(prefixes), "witness is not cone-active")
    return {
        "has_degree5_hinge": True,
        "order": [vertex + 1 for vertex in order0],
        "raw_increments": raw,
        "min_prefix": min(prefixes),
        "max_prefix": max(prefixes),
    }


def graph_components(adjacency: Sequence[set[int]]) -> int:
    unseen = set(range(len(adjacency)))
    components = 0
    while unseen:
        components += 1
        start = min(unseen)
        unseen.remove(start)
        queue = [start]
        while queue:
            vertex = queue.pop()
            for neighbour in adjacency[vertex]:
                if neighbour in unseen:
                    unseen.remove(neighbour)
                    queue.append(neighbour)
    return components


def alternating_cycle_predicate(pair: Pair, n: int = N) -> dict[str, object]:
    """Independent unsigned 2-core/edge-colour predicate for the pinned family."""

    reduced = cancelled_pair(pair)
    adjacency = [set() for _ in range(n)]
    signs: dict[Edge, int] = {}
    for sign, side in ((-1, reduced[0]), (1, reduced[1])):
        for u, v in side:
            require(1 <= u < v <= n, "cycle predicate requires loopless edges")
            edge = (u - 1, v - 1)
            require(edge not in signs, "cycle predicate received duplicate signed edge")
            signs[edge] = sign
            adjacency[edge[0]].add(edge[1])
            adjacency[edge[1]].add(edge[0])
    require(all(adjacency), "natural subject acquired an isolated vertex")

    degrees = [len(neighbours) for neighbours in adjacency]
    removed = [False] * n
    queue = deque(vertex for vertex, degree in enumerate(degrees) if degree <= 1)
    while queue:
        vertex = queue.popleft()
        if removed[vertex] or degrees[vertex] > 1:
            continue
        removed[vertex] = True
        for neighbour in adjacency[vertex]:
            if not removed[neighbour]:
                degrees[neighbour] -= 1
                if degrees[neighbour] == 1:
                    queue.append(neighbour)
    core = [vertex for vertex in range(n) if not removed[vertex]]
    if not core:
        return {
            "alternating_cycle": False,
            "cycle_length": 0,
            "component_count": graph_components(adjacency),
        }

    core_set = set(core)
    core_edges = [
        edge for edge in signs if edge[0] in core_set and edge[1] in core_set
    ]
    require(len(core_edges) == len(core), "natural 2-core is not one simple cycle")
    for vertex in core:
        require(
            sum(neighbour in core_set for neighbour in adjacency[vertex]) == 2,
            "natural 2-core has non-cycle degree",
        )
    core_adjacency = [set() for _ in range(n)]
    for u, v in core_edges:
        core_adjacency[u].add(v)
        core_adjacency[v].add(u)
    seen = {min(core)}
    stack = [min(core)]
    while stack:
        vertex = stack.pop()
        for neighbour in core_adjacency[vertex]:
            if neighbour not in seen:
                seen.add(neighbour)
                stack.append(neighbour)
    require(seen == core_set, "natural 2-core contains multiple cycles")

    alternating = True
    for vertex in core:
        incident_signs = {
            signs[tuple(sorted((vertex, neighbour)))]
            for neighbour in core_adjacency[vertex]
        }
        if incident_signs != {-1, 1}:
            alternating = False
            break
    return {
        "alternating_cycle": alternating,
        "cycle_length": len(core),
        "component_count": graph_components(adjacency),
    }


def boolean_charge(pair: Pair, n: int = N) -> int:
    """Exact top Boolean Mobius coefficient of max(branch sums)."""

    edge_masks = [
        tuple((1 << (u - 1)) | (1 << (v - 1)) for u, v in side)
        for side in pair
    ]
    total = 0
    for point in range(1 << n):
        left = sum(bool(point & edge) for edge in edge_masks[0])
        right = sum(bool(point & edge) for edge in edge_masks[1])
        sign = -1 if (n - point.bit_count()) & 1 else 1
        total += sign * max(left, right)
    return total


def _dp_worker(task: tuple[int, str, int, Pair]) -> dict[str, object]:
    subject_column, family, class_index, pair = task
    result = exact_mass5_dp(pair)
    return {
        "subject_column": subject_column,
        "family": family,
        "class_index": class_index,
        **result,
    }


def run_dp_census(
    subject: Sequence[SubjectColumn], workers: int
) -> list[dict[str, object]]:
    tasks = [
        (value.subject_column, value.family, value.class_index, value.pair)
        for value in subject
    ]
    if workers == 1:
        return [_dp_worker(task) for task in tasks]
    context = mp.get_context("spawn")
    with ProcessPoolExecutor(max_workers=workers, mp_context=context) as pool:
        return list(pool.map(_dp_worker, tasks, chunksize=32))


_WORKER_SEMANTICS: ModuleType | None = None


def _semantic_worker_init() -> None:
    global _WORKER_SEMANTICS
    _WORKER_SEMANTICS = load_semantics("g0068_zero_high_worker_g0049")


def positive_mass(direction: Sequence[int]) -> int:
    return sum(value for value in direction if value > 0)


def _semantic_worker(
    task: tuple[str, Pair],
) -> tuple[str, dict[str, object]]:
    label, pair = task
    require(_WORKER_SEMANTICS is not None, "semantic worker was not initialized")
    column = _WORKER_SEMANTICS.exact_semantic_column(pair, N)
    require(column.permutation_count == factorial(N), "semantic permutation census drift")
    high = sorted(
        (direction, coefficient)
        for direction, coefficient in column.hinges.items()
        if positive_mass(direction) == 5
    )
    first = None if not high else [list(high[0][0]), int(high[0][1])]
    return label, {
        "degree5_high_key_count": len(high),
        "total_hinge_key_count": len(column.hinges),
        "semantic_column_sha256": _WORKER_SEMANTICS.semantic_column_digest(column),
        "first_degree5_key_and_coefficient": first,
    }


def run_semantic_tasks(
    tasks: Sequence[tuple[str, Pair]], workers: int
) -> dict[str, dict[str, object]]:
    if workers == 1:
        _semantic_worker_init()
        rows = [_semantic_worker(task) for task in tasks]
    else:
        context = mp.get_context("spawn")
        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=_semantic_worker_init,
        ) as pool:
            rows = list(pool.map(_semantic_worker, tasks, chunksize=4))
    require(len(rows) == len({label for label, _ in rows}), "duplicate semantic task label")
    return dict(rows)


def mutation_pair() -> Pair:
    return (
        ((1, 2), (1, 5), (2, 4), (5, 6), (7, 11)),
        ((1, 3), (1, 7), (8, 9), (8, 10), (3, 11)),
    )


def all_full_support_pairs(n: int, mass: int) -> Iterator[Pair]:
    edges = tuple(itertools.combinations(range(1, n + 1), 2))
    full_support = set(range(1, n + 1))
    for left in itertools.combinations(edges, mass):
        left_set = set(left)
        remaining = tuple(edge for edge in edges if edge not in left_set)
        for right in itertools.combinations(remaining, mass):
            support = {vertex for edge in left + right for vertex in edge}
            if support == full_support:
                yield tuple(left), tuple(right)


def literal_has_high(pair: Pair, n: int, mass: int) -> bool:
    negative, positive = signed_neighbour_masks(pair, n)
    for order in itertools.permutations(range(n)):
        previous = 0
        raw: list[int] = []
        prefixes: list[int] = []
        running = 0
        for vertex in order:
            increment = (
                (positive[vertex] & previous).bit_count()
                - (negative[vertex] & previous).bit_count()
            )
            raw.append(increment)
            running += increment
            prefixes.append(running)
            previous |= 1 << vertex
        divisor = 0
        for value in raw:
            divisor = gcd(divisor, abs(value))
        if divisor == 0 or not (min(prefixes) < 0 < max(prefixes)):
            continue
        if sum(max(value, 0) for value in raw) == mass * divisor:
            return True
    return False


def generic_subset_dp_has_high(pair: Pair, n: int, mass: int) -> bool:
    """Composite-safe control DP: retains the raw-word gcd in every state."""

    negative, positive = signed_neighbour_masks(pair, n)
    q = _q_values(negative, positive, n)
    reachable: list[set[tuple[int, int]]] = [set() for _ in range(1 << n)]
    reachable[0].add((0, 0))
    for mask in range(1, 1 << n):
        sign_flag = 1 if q[mask] < 0 else 2 if q[mask] > 0 else 0
        for vertex in range(n):
            bit = 1 << vertex
            if not (mask & bit):
                continue
            previous = mask ^ bit
            negative_count = (negative[vertex] & previous).bit_count()
            positive_count = (positive[vertex] & previous).bit_count()
            # A primitive mass-m word must have zero raw cancellation.
            if negative_count and positive_count:
                continue
            increment = positive_count - negative_count
            for previous_flag, previous_gcd in reachable[previous]:
                reachable[mask].add(
                    (previous_flag | sign_flag, gcd(previous_gcd, abs(increment)))
                )
    return (3, 1) in reachable[-1]


def small_case_controls() -> list[dict[str, int]]:
    rows: list[dict[str, int]] = []
    for (n, mass), expected in EXPECTED_SMALL_CASES.items():
        total = 0
        literal_high = 0
        dp_high = 0
        for pair in all_full_support_pairs(n, mass):
            total += 1
            literal = literal_has_high(pair, n, mass)
            dynamic = generic_subset_dp_has_high(pair, n, mass)
            require(literal == dynamic, f"literal/DP mismatch at n={n}, m={mass}")
            literal_high += int(literal)
            dp_high += int(dynamic)
        observed = (total, dp_high, total - dp_high)
        require(observed == expected, f"small-case census drift: {(n, mass, observed)}")
        rows.append(
            {
                "n": n,
                "mass": mass,
                "full_support_pairs": total,
                "degree_mass_high": dp_high,
                "zero_high": total - dp_high,
                "literal_dp_mismatches": literal_high - dp_high,
            }
        )
    return rows


def self_test(
    semantics: ModuleType,
    same: Sequence[Pair],
    cross: Sequence[Pair],
    *,
    include_semantics: bool,
) -> dict[str, object]:
    controls = small_case_controls()
    for class_index in EXPECTED_ZERO_WITNESSES:
        require(
            exact_mass5_dp(same[class_index])["has_degree5_hinge"] is False,
            f"known zero-high DP witness drift: {class_index}",
        )
        require(
            alternating_cycle_predicate(same[class_index])["alternating_cycle"] is True,
            f"known alternating-cycle witness drift: {class_index}",
        )
        require(
            boolean_charge(same[class_index])
            == EXPECTED_ZERO_WITNESSES[class_index]["boolean_charge"],
            f"known Boolean charge drift: {class_index}",
        )
    require(exact_mass5_dp(same[1])["has_degree5_hinge"] is True, "same control lost high")
    require(exact_mass5_dp(cross[0])["has_degree5_hinge"] is True, "cross control lost high")
    mutant = mutation_pair()
    require(exact_mass5_dp(mutant)["has_degree5_hinge"] is True, "mutation escaped DP")
    require(
        alternating_cycle_predicate(mutant)["alternating_cycle"] is False,
        "sign mutation retained alternating-cycle predicate",
    )

    semantic_controls: dict[str, object] = {"executed": include_semantics}
    if include_semantics:
        tasks = [
            ("same_1", same[1]),
            ("cross_0", cross[0]),
            ("cross_3614", cross[3_614]),
            ("mutant_7172", mutant),
        ] + [
            (f"zero_{class_index}", same[class_index])
            for class_index in EXPECTED_ZERO_WITNESSES
        ]
        observed = run_semantic_tasks(tasks, workers=1)
        for label, expected in EXPECTED_SEMANTIC_CONTROLS.items():
            for key, value in expected.items():
                require(observed[label][key] == value, f"semantic control drift: {label}/{key}")
        for class_index, expected in EXPECTED_ZERO_WITNESSES.items():
            row = observed[f"zero_{class_index}"]
            require(row["degree5_high_key_count"] == 0, "zero witness gained high key")
            for key in ("total_hinge_key_count", "semantic_column_sha256"):
                require(row[key] == expected[key], f"zero semantic drift: {class_index}/{key}")
        for key, value in EXPECTED_MUTATION.items():
            require(observed["mutant_7172"][key] == value, f"mutation drift: {key}")
        semantic_controls = {"executed": True, "rows": observed}
    return {
        "result": "SELF_TEST_PASS",
        "small_case_literal_vs_subset_dp": controls,
        "known_zero_high_classes": sorted(EXPECTED_ZERO_WITNESSES),
        "semantic_controls": semantic_controls,
    }


def complete_report(workers: int) -> dict[str, object]:
    bindings = input_bindings()
    semantics = load_semantics()
    same, cross, subject, subject_controls = rebuild_subject(semantics)
    print("stage=small-case-and-hostile-controls", file=sys.stderr, flush=True)
    self_controls = self_test(semantics, same, cross, include_semantics=False)

    print(
        f"stage=exact-subset-dp columns={len(subject)} workers={workers}",
        file=sys.stderr,
        flush=True,
    )
    dp_rows = run_dp_census(subject, workers)
    require(len(dp_rows) == len(subject), "DP census row count drift")
    zero_subject = [
        int(row["subject_column"])
        for row in dp_rows
        if row["has_degree5_hinge"] is False
    ]
    zero_set = set(zero_subject)
    zero_columns = [subject[index] for index in zero_subject]
    zero_classes = [value.class_index for value in zero_columns]
    require(all(value.family == "same" for value in zero_columns), "cross zero-high found")
    require(len(zero_classes) == EXPECTED_ZERO_HIGH_COLUMNS, "zero-high count drift")
    require(zero_classes == sorted(zero_classes), "zero classes are not ascending")
    require(zero_subject == sorted(zero_subject), "zero subject columns are not ascending")
    zero_class_hash = canonical_sha256(zero_classes)
    zero_subject_hash = canonical_sha256(zero_subject)
    require(
        zero_class_hash == EXPECTED_ZERO_SAME_CLASS_INDICES_SHA256,
        f"zero same-class list drift: {zero_class_hash}",
    )
    require(
        zero_subject_hash == EXPECTED_ZERO_SUBJECT_COLUMNS_SHA256,
        f"zero subject-column list drift: {zero_subject_hash}",
    )

    witness_rows = [
        [
            int(row["subject_column"]),
            str(row["family"]),
            int(row["class_index"]),
            row["order"],
            row["raw_increments"],
            int(row["min_prefix"]),
            int(row["max_prefix"]),
        ]
        for row in dp_rows
        if row["has_degree5_hinge"] is True
    ]
    require(len(witness_rows) == EXPECTED_NONZERO_HIGH_COLUMNS, "active count drift")
    witness_hash = canonical_sha256(witness_rows)
    require(
        witness_hash == EXPECTED_NONZERO_WITNESS_ROWS_SHA256,
        f"ordered DP witness payload drift: {witness_hash}",
    )

    print("stage=independent-cycle-and-charge-census", file=sys.stderr, flush=True)
    cycle_zero_subject: list[int] = []
    cycle_histogram: Counter[int] = Counter()
    topology_histogram: Counter[tuple[str, int, int]] = Counter()
    for column in subject:
        cycle = alternating_cycle_predicate(column.pair)
        topology_histogram[
            (column.family, int(cycle["component_count"]), int(cycle["cycle_length"]) > 0)
        ] += 1
        if cycle["alternating_cycle"]:
            cycle_zero_subject.append(column.subject_column)
            cycle_histogram[int(cycle["cycle_length"])] += 1
    require(
        cycle_zero_subject == zero_subject,
        "independent alternating-cycle list differs from exact DP zero list",
    )
    require(
        dict(cycle_histogram) == EXPECTED_ZERO_CYCLE_LENGTH_HISTOGRAM,
        f"zero cycle-length histogram drift: {cycle_histogram}",
    )
    require(
        topology_histogram
        == Counter(
            {
                ("same", 2, 1): EXPECTED_SAME_MASS5_COLUMNS,
                ("cross", 1, 0): EXPECTED_CROSS_COLUMNS,
            }
        ),
        f"natural-family topology drift: {topology_histogram}",
    )

    charge_rows = [[value.class_index, boolean_charge(value.pair)] for value in zero_columns]
    charge_histogram = Counter(row[1] for row in charge_rows)
    require(
        dict(charge_histogram) == EXPECTED_ZERO_CHARGE_HISTOGRAM,
        f"zero Boolean-charge histogram drift: {charge_histogram}",
    )
    nonzero_charge_rows = [row for row in charge_rows if row[1] != 0]
    require(len(nonzero_charge_rows) == 319, "nonzero-charge zero-high count drift")
    nonzero_charge_hash = canonical_sha256(nonzero_charge_rows)
    require(
        nonzero_charge_hash == EXPECTED_NONZERO_CHARGE_ROWS_SHA256,
        f"nonzero charge list drift: {nonzero_charge_hash}",
    )

    print(
        f"stage=complete-semantic-replay zero_columns={len(zero_columns)} workers={workers}",
        file=sys.stderr,
        flush=True,
    )
    semantic_tasks = [
        (f"zero_{value.class_index}", value.pair) for value in zero_columns
    ] + [
        ("same_1", same[1]),
        ("cross_0", cross[0]),
        ("cross_3614", cross[3_614]),
        ("mutant_7172", mutation_pair()),
    ]
    semantic = run_semantic_tasks(semantic_tasks, workers)
    semantic_rows = []
    for value in zero_columns:
        row = semantic[f"zero_{value.class_index}"]
        require(
            row["degree5_high_key_count"] == 0,
            f"DP/cycle zero failed complete semantic replay: {value.class_index}",
        )
        semantic_rows.append(
            [
                value.class_index,
                int(row["degree5_high_key_count"]),
                int(row["total_hinge_key_count"]),
                str(row["semantic_column_sha256"]),
            ]
        )
    semantic_hash = canonical_sha256(semantic_rows)
    require(
        semantic_hash == EXPECTED_ZERO_SEMANTIC_ROWS_SHA256,
        f"complete zero semantic payload drift: {semantic_hash}",
    )
    for label, expected in EXPECTED_SEMANTIC_CONTROLS.items():
        for key, value in expected.items():
            require(semantic[label][key] == value, f"semantic control drift: {label}/{key}")
    for class_index, expected in EXPECTED_ZERO_WITNESSES.items():
        row = semantic[f"zero_{class_index}"]
        for key in ("total_hinge_key_count", "semantic_column_sha256"):
            require(row[key] == expected[key], f"known zero semantic drift: {class_index}/{key}")
    for key, value in EXPECTED_MUTATION.items():
        require(semantic["mutant_7172"][key] == value, f"mutation control drift: {key}")

    selected_zero_controls = {
        str(index): semantic[f"zero_{index}"]
        for index in (8, 161, 2_887, 3_600, 7_172, 9_794)
    }
    semantic_control_rows = {
        label: semantic[label]
        for label in ("same_1", "cross_0", "cross_3614", "mutant_7172")
    }

    scientific_payload: dict[str, object] = {
        "claim_boundary": {
            "licensed": (
                "An exact finite characterization of degree-five-zero columns inside the "
                "11,542-column pinned natural G-0068 single-edge family."
            ),
            "not_licensed": (
                "No converse for arbitrary signed graphs, no statement about other mass-five "
                "atoms, and no unrestricted MAX11 or two-hidden-layer conclusion."
            ),
        },
        "input_bindings": bindings,
        "subject": subject_controls,
        "exact_dp_criterion": {
            "left_edge_sign": -1,
            "right_edge_sign": 1,
            "prefix_potential": "q(A)=|E_+[A]|-|E_-[A]|",
            "mass5_condition": (
                "Some vertex order closes edges of at most one sign at every step, and q on "
                "proper prefixes visits both negative and positive values."
            ),
            "prime_gcd_note": (
                "With zero local cancellation the raw positive mass is 5. Cone activity rules "
                "out gcd 5, so the primitive positive mass is exactly 5."
            ),
            "state_space": "all 2^11 subsets times two prefix-sign-history bits",
            "witness_tie_break": (
                "subset masks ascending; candidate vertices low-to-high; predecessor flags 0..3"
            ),
        },
        "zero_high": {
            "count": len(zero_columns),
            "same_class_indices": zero_classes,
            "same_class_indices_sha256": zero_class_hash,
            "subject_columns": zero_subject,
            "subject_columns_sha256": zero_subject_hash,
            "all_are_same_family": True,
            "independent_alternating_cycle_subject_columns_match": True,
            "cycle_length_histogram": {
                str(key): value for key, value in sorted(cycle_histogram.items())
            },
            "boolean_charge_rows_schema": ["same_class_index", "boolean_charge"],
            "boolean_charge_rows": charge_rows,
            "boolean_charge_histogram": {
                str(key): value for key, value in sorted(charge_histogram.items())
            },
            "nonzero_charge_count": len(nonzero_charge_rows),
            "nonzero_charge_rows_sha256": nonzero_charge_hash,
        },
        "nonzero_high": {
            "count": len(witness_rows),
            "witness_rows_schema": [
                "subject_column",
                "family",
                "class_index",
                "order",
                "raw_increments",
                "min_prefix",
                "max_prefix",
            ],
            "witness_rows": witness_rows,
            "witness_rows_sha256": witness_hash,
        },
        "complete_zero_semantic_replay": {
            "count": len(semantic_rows),
            "row_schema": [
                "same_class_index",
                "degree5_high_key_count",
                "total_hinge_key_count",
                "semantic_column_sha256",
            ],
            "rows": semantic_rows,
            "rows_sha256": semantic_hash,
            "all_degree5_high_key_counts_zero": True,
        },
        "controls": {
            "small_case_literal_vs_subset_dp": self_controls[
                "small_case_literal_vs_subset_dp"
            ],
            "selected_zero_semantics": selected_zero_controls,
            "nonzero_and_mutation_semantics": semantic_control_rows,
            "mutation_description": (
                "On same class 7172's fixed unsigned graph, exchange branch membership of "
                "cycle edge (1,3) and off-cycle edge (1,5)."
            ),
            "mutation_pair": serialize_pair(mutation_pair()),
        },
    }
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": RESULT,
        "scientific_payload": scientific_payload,
        "scientific_payload_sha256": canonical_sha256(scientific_payload),
    }
    return report


def write_gzip(path: Path, value: object) -> None:
    require(path.parent == HERE, f"output must remain in {HERE}")
    if path.exists():
        raise FileExistsError(f"refusing to overwrite frozen output: {path}")
    partial = path.with_name(path.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"stale partial exists: {partial}")
    raw = canonical_bytes(value)
    with partial.open("xb") as destination:
        with gzip.GzipFile(filename="", mode="wb", fileobj=destination, mtime=0) as stream:
            stream.write(raw)
        destination.flush()
        os.fsync(destination.fileno())
    partial.replace(path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def validate_written_report(path: Path, report: dict[str, object]) -> None:
    with gzip.open(path, "rb") as source:
        raw = source.read()
    require(raw == canonical_bytes(report), "written gzip payload is not canonical")
    parsed = json.loads(raw, object_pairs_hook=unique_object)
    require(parsed == report, "written report failed exact reload")
    payload = parsed.get("scientific_payload")
    require(
        canonical_sha256(payload) == parsed.get("scientific_payload_sha256"),
        "scientific payload digest mismatch after reload",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true", help="run controls without writing")
    mode.add_argument("--run", action="store_true", help="run complete census and replay")
    parser.add_argument("--workers", type=int, default=min(8, os.cpu_count() or 1))
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    require(1 <= args.workers <= 64, "workers must be in [1,64]")
    if args.self_test:
        bindings = input_bindings()
        semantics = load_semantics()
        same, cross, _, subject_controls = rebuild_subject(semantics)
        report = {
            "schema": SCHEMA,
            "input_bindings": bindings,
            "subject": subject_controls,
            **self_test(semantics, same, cross, include_semantics=True),
        }
        print(canonical_bytes(report).decode("ascii"), end="")
        return

    report = complete_report(args.workers)
    write_gzip(args.output.resolve(), report)
    validate_written_report(args.output.resolve(), report)
    summary = {
        "result": report["result"],
        "output": str(args.output.resolve()),
        "output_sha256": sha256_path(args.output.resolve()),
        "scientific_payload_sha256": report["scientific_payload_sha256"],
        "zero_high_columns": EXPECTED_ZERO_HIGH_COLUMNS,
        "nonzero_high_columns": EXPECTED_NONZERO_HIGH_COLUMNS,
    }
    print(canonical_bytes(summary).decode("ascii"), end="")


if __name__ == "__main__":
    try:
        main()
    except (VerificationError, FileExistsError, ValueError, AssertionError) as error:
        print(f"FAIL_CLOSED: {error}", file=sys.stderr)
        raise SystemExit(2) from error
