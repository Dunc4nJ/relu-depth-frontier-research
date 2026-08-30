#!/usr/bin/env python3
"""Direct global span gate for the G-0071 asymmetric loop--edge orbit family.

The registered subject is the 3,754 full-S_11 orbit classes induced by the
5,040 labelled G-0071 seeds, together with the two pure degree-five linear
carriers.  Every graph column is reconstructed in the complete ordered-cone
normal form.  A deterministic direction-keyed CountSketch is applied only to
the hinge coordinates; all eleven linear coordinates remain exact.

Failure of target membership in this sketched integer system is a one-sided
falsifier for the same modular full system.  Membership is discovery evidence
only and must be replayed on the complete normal form before any construction
claim.  Modular nonmembership is not an exact-Q no-go.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
from itertools import permutations
import json
from math import factorial, gcd
import os
from pathlib import Path
import platform
import resource
import sys
import time
from typing import Any, Iterable, Sequence

import numpy as np
import pynauty
import flint
from flint import nmod_mat


ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
SCRIPT_PATH = Path(__file__).resolve()
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
CERTIFICATE_5 = ROOT / "subjects/max-relu-known/certificates/certificate_5_2.json"
G0071_SCRIPT = ROOT / "artifacts/math/G-0071/loop_edge_face_gluing_preflight.py"

N = 11
OLD_N = 10
EXPECTED_BASES = 252
EXPECTED_RAW_SEEDS = 5_040
EXPECTED_ORBITS = 3_754
PRIMES = (1_000_003, 1_000_033)
DEFAULT_BUCKETS = 4_096
DEFAULT_SEED = "max11-g0072-loop-edge-orbit-span-v1"
SCHEMA = "max11-g0072-asymmetric-loop-edge-global-span-gate-v1"

EXPECTED_BINDINGS = {
    "certificate_5_2": (
        CERTIFICATE_5,
        "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    ),
    "certificate_10_4": (
        CERTIFICATE,
        "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    ),
    "g0071_preflight": (
        G0071_SCRIPT,
        "f4504c4a80e22a15ca1b40c1f70fcd7f5ae7956932d635f78619432330968e9f",
    ),
}
EXPECTED_SEED_MANIFEST = "9cf4430a67623e7ba0698cd90cff271f69a30230d6b4d12da400c99b2594b5b9"
EXPECTED_ORBIT_SEQUENCE = "8ed1982cecb767412cb74149a5086cadbc61789dd0a6704b8dd9dc88b83360cb"
EXPECTED_ORBIT_CLASS_MANIFEST = "aeebb03311dcf7b6862c1444b5eb4df240f0b2dfc544a30d1ca1f6e67200e02a"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]


class GateError(RuntimeError):
    """A frozen subject, exact semantic, or gate invariant failed."""


@dataclass(frozen=True)
class Base:
    term_index: int
    coefficient: str
    left: Side
    right: Side


@dataclass(frozen=True)
class Seed:
    base_term_index: int
    coefficient: str
    anchor: int
    orientation: int
    pair: Pair

    @property
    def key(self) -> tuple[int, int, int]:
        return self.base_term_index, self.anchor, self.orientation


@dataclass(frozen=True)
class SemanticColumn:
    linear: tuple[int, ...]
    hinges: dict[Direction, int]
    raw_direction_count: int
    permutation_count: int


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path, block_size: int = 1 << 20) -> str:
    if not path.is_file() or path.is_symlink():
        raise GateError(f"not a regular frozen input: {path}")
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(block_size):
            digest.update(block)
    return digest.hexdigest()


def verify_bindings() -> dict[str, dict[str, object]]:
    output: dict[str, dict[str, object]] = {}
    for name, (path, expected) in EXPECTED_BINDINGS.items():
        observed = sha256_path(path)
        if observed != expected:
            raise GateError(f"binding mismatch for {name}: {observed} != {expected}")
        output[name] = {
            "path": str(path.relative_to(ROOT)),
            "sha256": observed,
            "bytes": path.stat().st_size,
        }
    module_path = Path(pynauty.__file__).resolve()
    output["pynauty"] = {
        "path": str(module_path),
        "sha256": sha256_path(module_path),
        "version": getattr(pynauty, "__version__", "unknown"),
    }
    flint_path = Path(flint.__file__).resolve()
    output["python_flint"] = {
        "path": str(flint_path),
        "sha256": sha256_path(flint_path),
        "version": getattr(flint, "__version__", "unknown"),
    }
    backend_module = sys.modules[nmod_mat.__module__]
    backend_path = Path(backend_module.__file__).resolve()
    output["python_flint_nmod_backend"] = {
        "path": str(backend_path),
        "sha256": sha256_path(backend_path),
        "module": nmod_mat.__module__,
    }
    return output


def canonical_side(side: Iterable[Edge]) -> Side:
    return tuple(sorted((min(a, b), max(a, b)) for a, b in side))


def canonical_pair(pair: Pair) -> Pair:
    first, second = canonical_side(pair[0]), canonical_side(pair[1])
    return (first, second) if first <= second else (second, first)


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[int(a), int(b)] for a, b in side] for side in pair]


def two_component_full_support(left: Side, right: Side) -> bool:
    all_edges = left + right
    if any(a == b for a, b in all_edges) or len(set(all_edges)) != 8:
        return False
    vertices = {vertex for item in all_edges for vertex in item}
    if vertices != set(range(1, OLD_N + 1)):
        return False
    parent = {vertex: vertex for vertex in vertices}

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for a, b in all_edges:
        root_a, root_b = find(a), find(b)
        if root_a != root_b:
            parent[root_b] = root_a
    return len({find(vertex) for vertex in vertices}) == 2


def load_bases() -> list[Base]:
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    terms = document.get("terms")
    if document.get("n") != OLD_N or not isinstance(terms, list) or len(terms) != 402:
        raise GateError("malformed pinned MAX10 certificate")
    bases: list[Base] = []
    for term_index, term in enumerate(terms):
        raw_pair = term.get("pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise GateError(f"malformed certificate pair at term {term_index}")
        sides: list[Side] = []
        for raw_side in raw_pair:
            if not isinstance(raw_side, list):
                raise GateError(f"malformed certificate side at term {term_index}")
            side: list[Edge] = []
            for raw_edge in raw_side:
                if (
                    not isinstance(raw_edge, list)
                    or len(raw_edge) != 2
                    or any(type(value) is not int for value in raw_edge)
                ):
                    raise GateError(f"malformed edge at term {term_index}")
                a, b = sorted(map(int, raw_edge))
                if not (1 <= a <= b <= OLD_N):
                    raise GateError(f"edge outside MAX10 at term {term_index}")
                side.append((a, b))
            sides.append(canonical_side(side))
        left, right = sides
        if len(left) != 4 or len(right) != 4:
            raise GateError(f"wrong branch mass at term {term_index}")
        if two_component_full_support(left, right):
            bases.append(Base(term_index, str(term["coefficient"]), left, right))
    if len(bases) != EXPECTED_BASES:
        raise GateError(f"base census drift: {len(bases)} != {EXPECTED_BASES}")
    return bases


def enumerate_seeds(bases: Sequence[Base]) -> list[Seed]:
    seeds: list[Seed] = []
    for base in bases:
        for anchor in range(1, OLD_N + 1):
            loop = (anchor, anchor)
            spoke = (anchor, N)
            seeds.append(
                Seed(
                    base.term_index,
                    base.coefficient,
                    anchor,
                    0,
                    (canonical_side(base.left + (loop,)), canonical_side(base.right + (spoke,))),
                )
            )
            seeds.append(
                Seed(
                    base.term_index,
                    base.coefficient,
                    anchor,
                    1,
                    (canonical_side(base.left + (spoke,)), canonical_side(base.right + (loop,))),
                )
            )
    if len(seeds) != EXPECTED_RAW_SEEDS or len({seed.key for seed in seeds}) != len(seeds):
        raise GateError("seed census is not exactly 252*10*2")
    return seeds


def seed_manifest(seeds: Sequence[Seed]) -> str:
    records = [
        {
            "base_term_index": seed.base_term_index,
            "coefficient": seed.coefficient,
            "anchor": seed.anchor,
            "orientation": seed.orientation,
            "pair": serialize_pair(seed.pair),
        }
        for seed in sorted(seeds, key=lambda item: item.key)
    ]
    return canonical_sha256(records)


def orbit_certificate(pair: Pair, n: int = N) -> bytes:
    if len(pair) != 2 or len(pair[0]) != len(pair[1]):
        raise GateError("orbit pair must have two equal-mass branches")
    mass = len(pair[0])
    branch_start = n
    occurrence_start = n + 2
    number_of_vertices = n + 2 + 2 * mass
    adjacency = {index: set() for index in range(number_of_vertices)}

    def connect(first: int, second: int) -> None:
        adjacency[first].add(second)
        adjacency[second].add(first)

    occurrence = occurrence_start
    for branch, side in enumerate(pair):
        branch_node = branch_start + branch
        for a, b in side:
            if not (1 <= a <= b <= n):
                raise GateError("orbit edge outside ambient labels")
            connect(occurrence, branch_node)
            connect(occurrence, a - 1)
            if a != b:
                connect(occurrence, b - 1)
            occurrence += 1
    graph = pynauty.Graph(
        number_of_vertices=number_of_vertices,
        directed=False,
        adjacency_dict={node: sorted(neighbours) for node, neighbours in adjacency.items()},
        vertex_coloring=[
            set(range(0, branch_start)),
            set(range(branch_start, occurrence_start)),
            set(range(occurrence_start, number_of_vertices)),
        ],
    )
    return pynauty.certificate(graph)


def build_orbit_representatives(seeds: Sequence[Seed]) -> tuple[list[Pair], dict[str, object]]:
    groups: dict[bytes, list[Pair]] = defaultdict(list)
    orbit_sequence: list[str] = []
    for seed in seeds:
        certificate = orbit_certificate(seed.pair)
        groups[certificate].append(canonical_pair(seed.pair))
        orbit_sequence.append(hashlib.sha256(certificate).hexdigest())
    ordered_keys = sorted(groups, key=lambda key: hashlib.sha256(key).hexdigest())
    representatives = [min(groups[key]) for key in ordered_keys]
    if len(representatives) != EXPECTED_ORBITS:
        raise GateError(f"orbit census drift: {len(representatives)} != {EXPECTED_ORBITS}")
    sequence_sha = canonical_sha256(orbit_sequence)
    manifest = [
        {
            "orbit_certificate_sha256": hashlib.sha256(key).hexdigest(),
            "raw_seed_count": len(groups[key]),
        }
        for key in ordered_keys
    ]
    manifest_sha = canonical_sha256(manifest)
    if sequence_sha != EXPECTED_ORBIT_SEQUENCE:
        raise GateError("G-0071 orbit sequence cross-check failed")
    if manifest_sha != EXPECTED_ORBIT_CLASS_MANIFEST:
        raise GateError("G-0071 orbit class manifest cross-check failed")
    return representatives, {
        "raw_seeds": len(seeds),
        "orbit_classes": len(representatives),
        "class_size_histogram": {
            str(size): count for size, count in sorted(Counter(map(len, groups.values())).items())
        },
        "orbit_sequence_sha256": sequence_sha,
        "orbit_class_manifest_sha256": manifest_sha,
        "representative_pair_manifest_sha256": canonical_sha256(
            [serialize_pair(pair) for pair in representatives]
        ),
    }


def signed_adjacency(pair: Pair, n: int) -> tuple[tuple[int, ...], ...]:
    weights = [[0] * n for _ in range(n)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_a, one_b in side:
            a, b = one_a - 1, one_b - 1
            if not (0 <= a <= b < n):
                raise GateError("semantic edge outside ambient dimension")
            weights[a][b] += sign
            if a != b:
                weights[b][a] += sign
    return tuple(tuple(row) for row in weights)


def direction_histogram(pair: Pair, n: int) -> dict[Direction, int]:
    """Exact subset-DP census of right-minus-left rank words, including loops."""

    weights = signed_adjacency(pair, n)
    full = (1 << n) - 1
    subset_sums = [[0] * (1 << n) for _ in range(n)]
    for vertex in range(n):
        for mask in range(1, 1 << n):
            bit = mask & -mask
            neighbour = bit.bit_length() - 1
            subset_sums[vertex][mask] = (
                subset_sums[vertex][mask ^ bit] + weights[vertex][neighbour]
            )
    masks_by_size: list[list[int]] = [[] for _ in range(n + 1)]
    for mask in range(1 << n):
        masks_by_size[mask.bit_count()].append(mask)
    cache: dict[int, dict[Direction, int]] = {0: {(): 1}}
    for size in range(1, n + 1):
        for mask in masks_by_size[size]:
            output: dict[Direction, int] = defaultdict(int)
            bits = mask
            while bits:
                bit = bits & -bits
                bits ^= bit
                vertex = bit.bit_length() - 1
                lower = mask ^ bit
                high = weights[vertex][vertex] + subset_sums[vertex][lower]
                for prefix, multiplicity in cache[lower].items():
                    output[prefix + (high,)] += multiplicity
            cache[mask] = dict(output)
        stale = size - 2
        if stale >= 0:
            for mask in masks_by_size[stale]:
                cache.pop(mask, None)
    histogram = cache[full]
    if sum(histogram.values()) != factorial(n):
        raise GateError("subset-DP permutation census mismatch")
    return histogram


def brute_direction_histogram(pair: Pair, n: int) -> dict[Direction, int]:
    weights = signed_adjacency(pair, n)
    output: dict[Direction, int] = defaultdict(int)
    for ordering in permutations(range(n)):
        lower: set[int] = set()
        word: list[int] = []
        for vertex in ordering:
            word.append(weights[vertex][vertex] + sum(weights[vertex][other] for other in lower))
            lower.add(vertex)
        output[tuple(word)] += 1
    return dict(output)


def brute_direction_histogram_without_diagonal(pair: Pair, n: int) -> dict[Direction, int]:
    """Hostile mutant: repeat the brute route while incorrectly dropping loops."""

    weights = signed_adjacency(pair, n)
    output: dict[Direction, int] = defaultdict(int)
    for ordering in permutations(range(n)):
        lower: set[int] = set()
        word: list[int] = []
        for vertex in ordering:
            word.append(sum(weights[vertex][other] for other in lower))
            lower.add(vertex)
        output[tuple(word)] += 1
    return dict(output)


def nonpositive_on_ordered_cone(direction: Direction) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


def semantic_from_histogram(
    pair: Pair, n: int, histogram: dict[Direction, int]
) -> SemanticColumn:
    left_loops = sum(a == b for a, b in pair[0])
    left_nonloops = len(pair[0]) - left_loops
    loop_factor = factorial(n - 1)
    nonloop_factor = factorial(n - 2) if n >= 2 else 0
    linear = [
        left_loops * loop_factor + left_nonloops * 2 * rank * nonloop_factor
        for rank in range(n)
    ]
    hinges: dict[Direction, int] = defaultdict(int)
    for raw_direction, multiplicity in histogram.items():
        if not any(raw_direction):
            continue
        magnitude = gcd(*(abs(value) for value in raw_direction))
        first = next(value for value in raw_direction if value)
        if first < 0:
            for rank, value in enumerate(raw_direction):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // magnitude for value in raw_direction)
        else:
            primitive = tuple(value // magnitude for value in raw_direction)
        if not nonpositive_on_ordered_cone(primitive):
            hinges[primitive] += multiplicity * magnitude
    return SemanticColumn(
        linear=tuple(linear),
        hinges=dict(hinges),
        raw_direction_count=len(histogram),
        permutation_count=sum(histogram.values()),
    )


def exact_semantic_column(pair: Pair, n: int = N) -> SemanticColumn:
    if len(pair) != 2 or not pair[0] or len(pair[0]) != len(pair[1]):
        raise GateError("semantic pair must have two nonempty equal-mass branches")
    return semantic_from_histogram(pair, n, direction_histogram(pair, n))


def semantic_digest(column: SemanticColumn) -> str:
    digest = hashlib.sha256()
    digest.update(canonical_bytes({"linear": list(column.linear)}))
    for direction in sorted(column.hinges):
        digest.update(
            canonical_bytes(
                {"direction": list(direction), "coefficient": column.hinges[direction]}
            )
        )
    return digest.hexdigest()


def evaluate_normal_form(column: SemanticColumn, point: Sequence[int]) -> int:
    if len(point) != len(column.linear):
        raise GateError("normal-form evaluation dimension mismatch")
    value = sum(coefficient * coordinate for coefficient, coordinate in zip(column.linear, point))
    for direction, coefficient in column.hinges.items():
        value += coefficient * max(
            0, sum(direction[rank] * point[rank] for rank in range(len(point)))
        )
    return value


def direct_full_symmetrized_pair_value(pair: Pair, point: Sequence[int]) -> int:
    """Independent small-n oracle using literal coordinate permutations."""

    n = len(point)
    total = 0
    for relabelling in permutations(range(n)):
        branch_values = []
        for side in pair:
            branch_values.append(
                sum(
                    max(point[relabelling[a - 1]], point[relabelling[b - 1]])
                    for a, b in side
                )
            )
        total += max(branch_values)
    return total


def relabel_pair(pair: Pair, permutation: dict[int, int]) -> Pair:
    return canonical_pair(
        tuple(
            canonical_side((permutation[a], permutation[b]) for a, b in side)
            for side in pair
        )  # type: ignore[arg-type]
    )


def sketch_location(direction: Direction, buckets: int, seed: str) -> tuple[int, int]:
    token = ",".join(map(str, direction)).encode("ascii")
    payload = b"max11-g0072-direction-countsketch-v1|" + seed.encode("ascii") + b"|" + token
    hashed = hashlib.sha256(payload).digest()
    bucket = int.from_bytes(hashed[:8], "little") % buckets
    sign = 1 if hashed[8] & 1 else -1
    return bucket, sign


def sketch_semantic(column: SemanticColumn, buckets: int, seed: str) -> np.ndarray:
    output = np.zeros(buckets + len(column.linear), dtype=np.int64)
    l1 = 0
    for direction, value in column.hinges.items():
        bucket, sign = sketch_location(direction, buckets, seed)
        output[bucket] += sign * value
        l1 += abs(value)
    if l1 >= 1 << 63 or (buckets and int(np.max(np.abs(output[:buckets]))) > l1):
        raise GateError("CountSketch accumulator bound failed")
    output[buckets:] = column.linear
    return output


def _sketch_worker(task: tuple[int, Pair, int, str]) -> tuple[int, np.ndarray, dict[str, object]]:
    position, pair, buckets, seed = task
    column = exact_semantic_column(pair)
    vector = sketch_semantic(column, buckets, seed)
    return position, vector, {
        "position": position,
        "pair_sha256": canonical_sha256(serialize_pair(pair)),
        "semantic_sha256": semantic_digest(column),
        "raw_direction_count": column.raw_direction_count,
        "active_hinges": len(column.hinges),
        "hinge_l1": sum(abs(value) for value in column.hinges.values()),
        "maximum_absolute_sketch_entry": int(np.max(np.abs(vector[:buckets]))),
    }


def five_common_nonloop_linear(n: int = N, mass: int = 5) -> tuple[int, ...]:
    return tuple(mass * 2 * rank * factorial(n - 2) for rank in range(n))


def five_common_loop_linear(n: int = N, mass: int = 5) -> tuple[int, ...]:
    return tuple(mass * factorial(n - 1) for _ in range(n))


def signed_matrix_sha256(matrix: np.ndarray, namespace: str) -> str:
    value = np.ascontiguousarray(matrix, dtype="<i8")
    digest = hashlib.sha256()
    digest.update(
        f"{namespace};int64-little-row-major;shape={value.shape[0]}x{value.shape[1]}\n".encode(
            "ascii"
        )
    )
    digest.update(value.tobytes(order="C"))
    return digest.hexdigest()


def to_nmod(matrix: np.ndarray, prime: int) -> nmod_mat:
    reduced = np.ascontiguousarray(np.remainder(matrix, prime), dtype=np.uint32)
    return nmod_mat(reduced.shape[0], reduced.shape[1], memoryview(reduced.ravel()), prime)


def modular_membership(
    matrix: np.ndarray, target: np.ndarray, prime: int, *, retain_solution: bool
) -> tuple[dict[str, object], np.ndarray | None]:
    if matrix.ndim != 2 or target.shape != (matrix.shape[0],):
        raise GateError("modular membership shape mismatch")
    started = time.perf_counter()
    field = to_nmod(matrix, prime)
    rank = int(field.rank())
    augmented_integer = np.column_stack((matrix, -target))
    augmented = to_nmod(augmented_integer, prime)
    augmented_rank = int(augmented.rank())
    if augmented_rank not in (rank, rank + 1):
        raise GateError("augmented rank law failed")
    member = augmented_rank == rank
    solution: np.ndarray | None = None
    support: list[list[int]] = []
    if member and retain_solution:
        kernel, nullity_object = augmented.nullspace()
        nullity = int(nullity_object)
        if nullity != augmented.ncols() - augmented_rank:
            raise GateError("augmented nullity drift")
        vector: np.ndarray | None = None
        for basis_column in range(nullity):
            candidate = np.fromiter(
                (int(kernel[row, basis_column]) % prime for row in range(augmented.ncols())),
                dtype=np.uint32,
                count=augmented.ncols(),
            )
            if int(candidate[-1]):
                vector = candidate
                break
        if vector is None:
            raise GateError("membership rank passed but no target-bearing kernel vector exists")
        scale = pow(int(vector[-1]), -1, prime)
        normalized = np.remainder(vector.astype(np.uint64) * scale, prime).astype(np.uint32)
        solution = normalized[:-1]
        replay = field * to_nmod(solution.reshape(-1, 1), prime)
        for row in range(field.nrows()):
            if int(replay[row, 0]) % prime != int(target[row]) % prime:
                raise GateError("modular solution failed exact sketched-system replay")
        support = [[int(index), int(solution[index])] for index in np.flatnonzero(solution)]
    report = {
        "prime": prime,
        "column_rank": rank,
        "augmented_rank": augmented_rank,
        "target_in_sketched_span": member,
        "rank_gap": augmented_rank - rank,
        "solution_support_size": len(support) if solution is not None else None,
        "solution_sparse_sha256": canonical_sha256(support) if solution is not None else None,
        "seconds": time.perf_counter() - started,
        "interpretation": (
            "membership is discovery-only pending complete-normal-form replay"
            if member
            else "modular sketched nonmembership; not an exact-Q no-go"
        ),
    }
    return report, solution


def memory_available_bytes() -> int:
    with Path("/proc/meminfo").open("r", encoding="utf-8") as source:
        for line in source:
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    raise GateError("cannot read MemAvailable")


def resource_preflight(buckets: int, columns: int, minimum_available_gib: float) -> dict[str, object]:
    available = memory_available_bytes()
    rows = buckets + N
    entries = rows * columns
    # Matrix, modular input, FLINT storage, augmented copy, and one elimination
    # workspace are conservatively budgeted at eight int64-equivalents.
    planning_peak = entries * 8 * 8 + (2 << 30)
    threshold = int(minimum_available_gib * (1 << 30))
    return {
        "available_bytes": available,
        "available_gib": available / (1 << 30),
        "minimum_available_gib": minimum_available_gib,
        "passes_threshold": available >= threshold and available >= planning_peak,
        "matrix_shape": [rows, columns],
        "matrix_entries": entries,
        "signed_matrix_bytes": entries * 8,
        "conservative_peak_planning_bytes": planning_peak,
        "conservative_peak_planning_gib": planning_peak / (1 << 30),
        "estimate_status": "PLANNING_ESTIMATE_NOT_A_BOUND",
    }


def subject_preflight(buckets: int, seed: str, minimum_available_gib: float) -> tuple[list[Pair], dict[str, object]]:
    bindings = verify_bindings()
    bases = load_bases()
    seeds = enumerate_seeds(bases)
    observed_manifest = seed_manifest(seeds)
    if observed_manifest != EXPECTED_SEED_MANIFEST:
        raise GateError("G-0071 raw seed manifest cross-check failed")
    representatives, orbit_report = build_orbit_representatives(seeds)
    samples: list[dict[str, object]] = []
    for position in (0, len(representatives) // 2, len(representatives) - 1):
        column = exact_semantic_column(representatives[position])
        samples.append(
            {
                "position": position,
                "pair_sha256": canonical_sha256(serialize_pair(representatives[position])),
                "semantic_sha256": semantic_digest(column),
                "raw_direction_count": column.raw_direction_count,
                "active_hinges": len(column.hinges),
                "permutation_count": column.permutation_count,
            }
        )
    resources = resource_preflight(buckets, len(representatives) + 2, minimum_available_gib)
    return representatives, {
        "bindings": bindings,
        "script_sha256": sha256_path(SCRIPT_PATH),
        "base_count": len(bases),
        "raw_seed_manifest_sha256": observed_manifest,
        "orbits": orbit_report,
        "semantic_smoke": samples,
        "countsketch": {
            "buckets": buckets,
            "seed": seed,
            "hinge_map": (
                "SHA256('max11-g0072-direction-countsketch-v1|' + seed + '|' + "
                "comma-separated primitive direction); first 8 bytes little-endian modulo "
                "buckets, byte 8 low bit selects sign"
            ),
            "linear_coordinates": "all 11 exact and unsketched",
        },
        "resources": resources,
    }


def build_sketched_matrix(
    representatives: Sequence[Pair], buckets: int, seed: str, workers: int
) -> tuple[np.ndarray, dict[str, object]]:
    started = time.perf_counter()
    graph_columns = len(representatives)
    matrix = np.zeros((buckets + N, graph_columns + 2), dtype=np.int64)
    records: list[dict[str, object] | None] = [None] * graph_columns
    tasks = [(position, pair, buckets, seed) for position, pair in enumerate(representatives)]
    completed = 0
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_sketch_worker, task): task[0] for task in tasks}
        for future in as_completed(futures):
            position, vector, record = future.result()
            matrix[:, position] = vector
            records[position] = record
            completed += 1
            if completed % 100 == 0 or completed == graph_columns:
                print(
                    f"G0072_SEMANTICS completed={completed}/{graph_columns} "
                    f"seconds={time.perf_counter()-started:.1f}",
                    file=sys.stderr,
                    flush=True,
                )
    if any(record is None for record in records):
        raise GateError("semantic worker completion census failed")
    matrix[buckets:, graph_columns] = five_common_nonloop_linear()
    matrix[buckets:, graph_columns + 1] = five_common_loop_linear()
    typed_records = [record for record in records if record is not None]
    return matrix, {
        "graph_columns": graph_columns,
        "pure_linear_carriers": ["five-common-nonloops", "five-common-loops"],
        "total_columns": matrix.shape[1],
        "rows": matrix.shape[0],
        "hinge_countsketch_rows": buckets,
        "exact_linear_rows": N,
        "semantic_column_order_sha256": canonical_sha256(typed_records),
        "semantic_column_digest_sequence_sha256": canonical_sha256(
            [record["semantic_sha256"] for record in typed_records]
        ),
        "raw_direction_count_min": min(int(record["raw_direction_count"]) for record in typed_records),
        "raw_direction_count_max": max(int(record["raw_direction_count"]) for record in typed_records),
        "active_hinges_min": min(int(record["active_hinges"]) for record in typed_records),
        "active_hinges_max": max(int(record["active_hinges"]) for record in typed_records),
        "hinge_l1_max": max(int(record["hinge_l1"]) for record in typed_records),
        "maximum_absolute_sketch_entry": max(
            int(record["maximum_absolute_sketch_entry"]) for record in typed_records
        ),
        "signed_matrix_sha256": signed_matrix_sha256(matrix, SCHEMA),
        "seconds": time.perf_counter() - started,
    }


def inherited_weight_boolean_probe(bases: Sequence[Base]) -> dict[str, object]:
    """Exploratory falsifier for the obvious inherited MAX10 coefficient choice."""

    values = [Fraction(0) for _ in range(N + 1)]
    for base in bases:
        coefficient = Fraction(base.coefficient)
        for anchor in range(1, OLD_N + 1):
            pairs = (
                (base.left + ((anchor, anchor),), base.right + ((anchor, N),)),
                (base.left + ((anchor, N),), base.right + ((anchor, anchor),)),
            )
            for pair in pairs:
                subtotals = [0] * (N + 1)
                for mask in range(1, 1 << N):
                    branch_values = [
                        sum(
                            bool(mask & (1 << (a - 1)))
                            or bool(mask & (1 << (b - 1)))
                            for a, b in side
                        )
                        for side in pair
                    ]
                    subtotals[mask.bit_count()] += max(branch_values)
                for top_count in range(1, N + 1):
                    values[top_count] += (
                        coefficient
                        * factorial(top_count)
                        * factorial(N - top_count)
                        * subtotals[top_count]
                    )
    normalized = [str(value / factorial(N)) for value in values[1:]]
    return {
        "mode": "exploratory-pre-registration-observation",
        "coefficient_rule": "sum every anchor and both orientations with its source MAX10 coefficient",
        "normalized_full_orbit_values_on_boolean_Hamming_layers_1_through_11": normalized,
        "constant_across_nonzero_layers": len(set(normalized)) == 1,
        "conclusion": "obvious inherited weighting is globally refuted" if len(set(normalized)) != 1 else "not refuted",
        "no_claim": "This does not test arbitrary coefficients in the 3,754-orbit span.",
    }


def known_max5_control() -> dict[str, object]:
    """Recover the pinned exact MAX5 certificate with this semantic engine."""

    document = json.loads(CERTIFICATE_5.read_text(encoding="utf-8"))
    terms = document.get("terms")
    if document.get("n") != 5 or not isinstance(terms, list) or len(terms) != 3:
        raise GateError("malformed known MAX5 control certificate")
    linear = [Fraction(0) for _ in range(5)]
    hinges: dict[Direction, Fraction] = defaultdict(Fraction)
    for term in terms:
        raw_pair = term.get("pair")
        if not isinstance(raw_pair, list) or len(raw_pair) != 2:
            raise GateError("malformed known MAX5 control term")
        pair: Pair = tuple(
            canonical_side(tuple(map(int, edge)) for edge in side) for side in raw_pair
        )  # type: ignore[assignment]
        column = exact_semantic_column(pair, 5)
        coefficient = Fraction(str(term["coefficient"]))
        for rank, value in enumerate(column.linear):
            linear[rank] += coefficient * value
        for direction, value in column.hinges.items():
            hinges[direction] += coefficient * value
    nonzero_hinges = {direction: value for direction, value in hinges.items() if value}
    # The public rational coefficients already include the inverse orbit-size
    # normalization, so that certificate equals MAX5 itself.  The registered
    # G-0072 search uses 11!*MAX11; nonzero target scaling does not change
    # span membership at either registered prime.
    target = [Fraction(0)] * 4 + [Fraction(1)]
    if nonzero_hinges or linear != target:
        raise GateError("loop-capable semantic engine failed the pinned exact MAX5 identity")
    return {
        "certificate_terms": len(terms),
        "hinge_residuals": 0,
        "linear_coordinates": [str(value) for value in linear],
        "target_normalization": "MAX5 on the ordered cone (public coefficient convention)",
    }


def run_self_test() -> dict[str, object]:
    toy: Pair = (((1, 1), (2, 3)), ((1, 4), (2, 2)))
    dp = direction_histogram(toy, 4)
    brute = brute_direction_histogram(toy, 4)
    if dp != brute:
        raise GateError("loop-inclusive subset DP disagrees with brute permutations")
    exact = semantic_from_histogram(toy, 4, dp)
    brute_semantic = semantic_from_histogram(toy, 4, brute)
    if exact != brute_semantic:
        raise GateError("loop-inclusive semantic normalization disagrees with brute route")
    swapped = exact_semantic_column((toy[1], toy[0]), 4)
    if exact.linear != swapped.linear or exact.hinges != swapped.hinges:
        raise GateError("branch-swap semantic invariance failed")
    relabelled = relabel_pair(toy, {1: 2, 2: 3, 3: 4, 4: 1})
    relabelled_column = exact_semantic_column(relabelled, 4)
    if exact.linear != relabelled_column.linear or exact.hinges != relabelled_column.hinges:
        raise GateError("coordinate-relabel semantic invariance failed")
    direct_points = ((-3, -1, 2, 5), (0, 0, 1, 4), (-2, 1, 1, 1))
    for point in direct_points:
        direct_value = direct_full_symmetrized_pair_value(toy, point)
        normal_form_value = evaluate_normal_form(exact, point)
        if direct_value != normal_form_value:
            raise GateError("loop-inclusive normal form disagrees with literal full symmetrization")

    # Planted loop omission: remove diagonal weights from this same rank word.
    # It must disagree with the correct brute-force histogram.
    if brute_direction_histogram_without_diagonal(toy, 4) == dp:
        raise GateError("loop-omission mutant escaped")

    carrier_nonloop: Pair = (((1, 2),) * 5, ((1, 2),) * 5)
    carrier_loop: Pair = (((1, 1),) * 5, ((1, 1),) * 5)
    nonloop_column = exact_semantic_column(carrier_nonloop, 4)
    loop_column = exact_semantic_column(carrier_loop, 4)
    if nonloop_column.hinges or nonloop_column.linear != five_common_nonloop_linear(4):
        raise GateError("five-common-nonloop carrier formula failed")
    if loop_column.hinges or loop_column.linear != five_common_loop_linear(4):
        raise GateError("five-common-loop carrier formula failed")

    first_sketch = sketch_semantic(exact, 17, "control-seed")
    repeat_sketch = sketch_semantic(exact, 17, "control-seed")
    changed_sketch = sketch_semantic(exact, 17, "mutated-seed")
    if not np.array_equal(first_sketch, repeat_sketch):
        raise GateError("CountSketch is nondeterministic")
    if np.array_equal(first_sketch, changed_sketch):
        raise GateError("CountSketch seed mutant escaped")

    synthetic = np.asarray([[1, 0], [0, 1], [0, 0]], dtype=np.int64)
    good = np.asarray([1, 1, 0], dtype=np.int64)
    bad = np.asarray([1, 1, 1], dtype=np.int64)
    good_report, solution = modular_membership(synthetic, good, PRIMES[0], retain_solution=True)
    bad_report, _ = modular_membership(synthetic, bad, PRIMES[0], retain_solution=False)
    if not good_report["target_in_sketched_span"] or solution is None:
        raise GateError("synthetic member was not recovered")
    if bad_report["target_in_sketched_span"]:
        raise GateError("synthetic nonmember mutant escaped")
    full_collision_subject = np.asarray([[1], [1]], dtype=np.int64)
    full_collision_target = np.asarray([1, -1], dtype=np.int64)
    full_report, _ = modular_membership(
        full_collision_subject, full_collision_target, PRIMES[0], retain_solution=False
    )
    sketched_report, _ = modular_membership(
        np.asarray([[2]], dtype=np.int64),
        np.asarray([0], dtype=np.int64),
        PRIMES[0],
        retain_solution=False,
    )
    if full_report["target_in_sketched_span"] or not sketched_report["target_in_sketched_span"]:
        raise GateError("planted CountSketch false-membership direction control failed")
    max5 = known_max5_control()
    return {
        "loop_inclusive_subset_DP_equals_brute_permutations": True,
        "loop_inclusive_normal_form_equals_brute_route": True,
        "branch_swap_invariance": True,
        "coordinate_relabel_invariance": True,
        "loop_inclusive_normal_form_matches_literal_full_symmetrization": len(direct_points),
        "loop_omission_mutant_rejected": True,
        "five_common_nonloop_carrier_formula": True,
        "five_common_loop_carrier_formula": True,
        "countsketch_repeat_determinism": True,
        "countsketch_seed_mutant_detected": True,
        "synthetic_member_recovered": True,
        "synthetic_nonmember_rejected": True,
        "countsketch_collision_can_create_false_membership_not_false_nonmembership": True,
        "known_MAX5_exact_certificate_recovered": max5,
    }


def write_gzip(path: Path, value: object) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
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


def environment(workers: int) -> dict[str, object]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "numpy": np.__version__,
        "python_flint": getattr(flint, "__version__", "unknown"),
        "pynauty": getattr(pynauty, "__version__", "unknown"),
        "workers": workers,
        "process_max_rss_kib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
    }


def parse_primes(raw: str) -> tuple[int, ...]:
    primes = tuple(int(item) for item in raw.split(",") if item)
    if primes != PRIMES:
        raise GateError(f"registered primes must be exactly {PRIMES}")
    return primes


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--exploratory-inherited-weights", action="store_true")
    mode.add_argument("--run", action="store_true")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--buckets", type=int, default=DEFAULT_BUCKETS)
    parser.add_argument("--seed", default=DEFAULT_SEED)
    parser.add_argument("--primes", default=",".join(map(str, PRIMES)))
    parser.add_argument("--minimum-available-gib", type=float, default=12.0)
    parser.add_argument("--expected-script-sha256")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> None:
    arguments = parse_arguments()
    begun = time.perf_counter()
    if arguments.workers < 1 or arguments.buckets < 1:
        raise GateError("workers and buckets must be positive")
    controls = run_self_test()
    if arguments.self_test:
        print(json.dumps({"schema": SCHEMA, "mode": "self-test", "controls": controls}, sort_keys=True))
        return

    representatives, preflight = subject_preflight(
        arguments.buckets, arguments.seed, arguments.minimum_available_gib
    )
    if arguments.preflight_only:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "mode": "preflight-only",
                    "controls": controls,
                    "preflight": preflight,
                    "claim_boundary": "No registered span matrix or target membership result was computed.",
                },
                sort_keys=True,
            )
        )
        return
    if arguments.exploratory_inherited_weights:
        print(
            json.dumps(
                {
                    "schema": SCHEMA,
                    "mode": "exploratory-inherited-weights",
                    "controls": controls,
                    "preflight": preflight,
                    "result": inherited_weight_boolean_probe(load_bases()),
                },
                sort_keys=True,
            )
        )
        return


    observed_script = sha256_path(SCRIPT_PATH)
    if not arguments.expected_script_sha256 or arguments.expected_script_sha256 != observed_script:
        raise GateError("--run requires the exact preregistered script SHA-256")
    if arguments.buckets != DEFAULT_BUCKETS or arguments.seed != DEFAULT_SEED:
        raise GateError("registered run requires the frozen bucket count and seed")
    parse_primes(arguments.primes)
    if arguments.output is None:
        raise GateError("--run requires --output")
    if not preflight["resources"]["passes_threshold"]:
        raise GateError("resource preflight failed")

    matrix, matrix_report = build_sketched_matrix(
        representatives, arguments.buckets, arguments.seed, arguments.workers
    )
    target = np.zeros(matrix.shape[0], dtype=np.int64)
    target[-1] = factorial(N)
    prime_reports: list[dict[str, object]] = []
    solutions: dict[str, list[int]] = {}
    for prime in PRIMES:
        report, solution = modular_membership(matrix, target, prime, retain_solution=True)
        prime_reports.append(report)
        if solution is not None:
            solutions[str(prime)] = [int(value) for value in solution]
    outcome = (
        "TARGET_IN_SKETCHED_SPAN_AT_BOTH_PRIMES_PENDING_COMPLETE_REPLAY"
        if all(report["target_in_sketched_span"] for report in prime_reports)
        else "TARGET_OUTSIDE_SKETCHED_SPAN_AT_AT_LEAST_ONE_REGISTERED_PRIME"
    )
    result: dict[str, object] = {
        "schema": SCHEMA,
        "mode": "registered-run",
        "result": outcome,
        "bindings": preflight,
        "controls": controls,
        "matrix": matrix_report,
        "target": {
            "hinge_coordinates": "all zero",
            "linear_coordinates": [0] * (N - 1) + [factorial(N)],
            "normalization": "unnormalized full S_11 symmetrization",
        },
        "prime_results": prime_reports,
        "modular_solutions": solutions,
        "environment": environment(arguments.workers),
        "wall_seconds": time.perf_counter() - begun,
        "interpretation_boundary": (
            "A target-bearing modular solution is discovery evidence only until complete exact "
            "normal-form replay, cross-prime alignment, exact-Q lift, and compilation. Modular "
            "sketched nonmembership is not an exact-Q or unrestricted-network no-go."
        ),
    }
    scientific_payload = {
        "schema": SCHEMA,
        "result": outcome,
        "subject": {
            "bindings": preflight["bindings"],
            "script_sha256": preflight["script_sha256"],
            "base_count": preflight["base_count"],
            "raw_seed_manifest_sha256": preflight["raw_seed_manifest_sha256"],
            "orbits": preflight["orbits"],
            "semantic_smoke": preflight["semantic_smoke"],
            "countsketch": preflight["countsketch"],
        },
        "controls": controls,
        "matrix": {key: value for key, value in matrix_report.items() if key != "seconds"},
        "target": result["target"],
        "prime_results": [
            {key: value for key, value in report.items() if key != "seconds"}
            for report in prime_reports
        ],
        "modular_solutions": solutions,
        "interpretation_boundary": result["interpretation_boundary"],
    }
    result["scientific_payload_sha256"] = canonical_sha256(scientific_payload)
    result["scientific_payload_contract"] = {
        "included_top_level_keys": sorted(scientific_payload),
        "excluded_operational_fields": [
            "preflight.resources",
            "matrix.seconds",
            "prime_results[*].seconds",
            "environment",
            "wall_seconds",
        ],
    }
    write_gzip(arguments.output, result)
    print(
        json.dumps(
            {
                "result": outcome,
                "output": str(arguments.output),
                "output_sha256": sha256_path(arguments.output),
                "scientific_payload_sha256": result["scientific_payload_sha256"],
                "prime_results": prime_reports,
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
