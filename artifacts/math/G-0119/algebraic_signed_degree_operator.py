#!/usr/bin/env python3
"""Exact joint gate for the preregistered G-0119 algebraic lift operator."""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import combinations_with_replacement, permutations
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence

from flint import fmpz_mat
import numpy as np
import pynauty


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "PREREGISTRATION.md"
CERT6 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT10 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_10_4.json"
CERT395 = ROOT / "artifacts/math/G-0115/unrestricted_full_semantic_certificate_v1.json"
MAP9 = ROOT / "artifacts/math/G-0115/parity_lift_representatives_v1.jsonl.gz"
MATRIX9 = ROOT / "artifacts/math/G-0115/unrestricted_full_semantic_matrix_v1.npy"
MATRIX9_META = ROOT / "artifacts/math/G-0115/unrestricted_full_semantic_matrix_v1.json"
KERNEL = ROOT / "artifacts/math/G-0115/semantic_repair.py"
DP_PATH = ROOT / "artifacts/math/G-0094/cleanroom_star_quotient.py"

EXPECTED = {
    CERT6: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT10: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    CERT395: "628a836542339a522fde173f13749bad29f150bdff69e7f66aeae26f786e963e",
    MAP9: "2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148",
    MATRIX9: "f1a4f7fb1a449d2f1ef8a41fc948c1fb893039ae3f8d432b691d4ae1cfbdff1e",
    MATRIX9_META: "8e4f59489d2eb87813f2020f60e5f61ca8caef6f3d2b5b30941b14fd3a8d569b",
    KERNEL: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    DP_PATH: "d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71",
}

FEATURE_NAMES = (
    "1",
    "a",
    "b",
    "a2",
    "ab",
    "b2",
    "q",
    "r",
    "aq",
    "bq",
    "ar",
    "br",
)
FEATURES = len(FEATURE_NAMES)
INT64_SAFE_BOUND = 1 << 62

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]
Semantic = tuple[tuple[int, ...], dict[Direction, int]]


class GateError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GateError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha(value: object) -> str:
    return hashlib.sha256(canonical(value)).hexdigest()


def array_sha(array: np.ndarray) -> str:
    return hashlib.sha256(memoryview(np.ascontiguousarray(array)).cast("B")).hexdigest()


def write_exclusive(path: Path, value: object) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def bind_inputs() -> dict[str, str]:
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"bound input drift: {observed}")
    return {str(path.relative_to(ROOT)): digest for path, digest in observed.items()}


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    require(spec is not None and spec.loader is not None, f"cannot load {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def parse_pair(raw: object, n: int) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[Side] = []
    for raw_side in raw:
        require(isinstance(raw_side, list), "malformed side")
        side: list[Edge] = []
        for raw_edge in raw_side:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            u, v = map(int, raw_edge)
            require(1 <= u <= v <= n, "edge outside arity")
            side.append((u - 1, v - 1))
        sides.append(tuple(sorted(side)))
    require(len(sides[0]) == len(sides[1]), "unequal branch degree")
    return sides[0], sides[1]


@dataclass(frozen=True)
class Term:
    coefficient: Fraction
    pair: Pair


def load_certificate(path: Path, n: int, degree: int) -> list[Term]:
    require(sha256(path) == EXPECTED[path], f"certificate drift: {path}")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n and isinstance(document.get("terms"), list), "bad certificate")
    output = []
    for raw in document["terms"]:
        pair = parse_pair(raw["pair"], n)
        require(len(pair[0]) == degree, "degree drift")
        output.append(Term(Fraction(raw["coefficient"]), pair))
    return output


def coefficient_lcm(terms: Sequence[Term]) -> int:
    value = 1
    for term in terms:
        value = math.lcm(value, term.coefficient.denominator)
    return value


def cancel_with_common(pair: Pair) -> tuple[Pair, Counter[Edge]]:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    return (tuple(sorted(left.elements())), tuple(sorted(right.elements()))), common


def occurrence_certificate(first: Side, second: Side, n: int) -> bytes:
    adjacency: dict[int, set[int]] = {index: set() for index in range(n)}
    first_nodes: list[int] = []
    second_nodes: list[int] = []
    for bucket, side in ((first_nodes, first), (second_nodes, second)):
        for u, v in side:
            node = len(adjacency)
            adjacency[node] = set()
            bucket.append(node)
            for coordinate in {u, v}:
                adjacency[node].add(coordinate)
                adjacency[coordinate].add(node)
    coloring = [set(range(n))]
    if first_nodes:
        coloring.append(set(first_nodes))
    if second_nodes:
        coloring.append(set(second_nodes))
    graph = pynauty.Graph(
        number_of_vertices=len(adjacency),
        directed=False,
        adjacency_dict={node: sorted(neighbors) for node, neighbors in adjacency.items()},
        vertex_coloring=coloring,
    )
    return pynauty.certificate(graph)


def signed_hash(pair: Pair, n: int) -> str:
    residual, _common = cancel_with_common(pair)
    direct = occurrence_certificate(residual[0], residual[1], n)
    swapped = occurrence_certificate(residual[1], residual[0], n)
    return hashlib.sha256(min(direct, swapped)).hexdigest()


def relabel_edge(edge: Edge, permutation: Sequence[int]) -> Edge:
    return tuple(sorted((permutation[edge[0]], permutation[edge[1]])))  # type: ignore[return-value]


def relabel_pair(pair: Pair, permutation: Sequence[int]) -> Pair:
    return tuple(
        tuple(sorted(relabel_edge(edge, permutation) for edge in side)) for side in pair
    )  # type: ignore[return-value]


def edge_counter_difference(pair: Pair) -> Counter[Edge]:
    value = Counter(pair[0])
    value.subtract(Counter(pair[1]))
    return +value - (-value)


def signed_edge_dict(pair: Pair) -> dict[Edge, int]:
    result: dict[Edge, int] = {}
    left, right = Counter(pair[0]), Counter(pair[1])
    for edge in set(left) | set(right):
        value = left[edge] - right[edge]
        if value:
            result[edge] = value
    return result


def incidence(edge_values: dict[Edge, int], n: int, loop_twice: bool = False) -> tuple[int, ...]:
    output = [0] * n
    for (u, v), value in edge_values.items():
        output[u] += value
        if v != u or loop_twice:
            output[v] += value
    return tuple(output)


def descriptor_features(pair: Pair, left_edge: Edge, right_edge: Edge, n: int, loop_twice: bool = False) -> tuple[int, ...]:
    w = signed_edge_dict(pair)
    u: dict[Edge, int] = {left_edge: 1}
    u[right_edge] = u.get(right_edge, 0) - 1
    u = {edge: value for edge, value in u.items() if value}
    dw = incidence(w, n, loop_twice=loop_twice)
    du = incidence(u, n, loop_twice=loop_twice)
    a = sum(value * u.get(edge, 0) for edge, value in w.items())
    b = sum(x * y for x, y in zip(dw, du, strict=True))
    q = sum(value * value for value in u.values())
    r = sum(value * value for value in du)
    return (1, a, b, a * a, a * b, b * b, q, r, a * q, b * q, a * r, b * r)


def normal_form(dp, pair: Pair, n: int) -> Semantic:
    linear, directions, coefficients = dp.ordered_normal_form(pair, n)
    hinges = {
        tuple(map(int, direction)): int(coefficient)
        for direction, coefficient in zip(directions, coefficients, strict=True)
        if int(coefficient)
    }
    return tuple(map(int, linear)), hinges


def literal_normal_form(pair: Pair, n: int) -> Semantic:
    linear = [0] * n
    hinges: Counter[Direction] = Counter()
    for order in permutations(range(n)):
        position = [0] * n
        for rank, label in enumerate(order):
            position[label] = rank
        forms = []
        for side in pair:
            vector = [0] * n
            for u, v in side:
                vector[max(position[u], position[v])] += 1
            forms.append(tuple(vector))
        base, other = sorted(forms)
        direction = tuple(y - x for x, y in zip(base, other, strict=True))
        prefix = 0
        sign_definite = True
        for value in direction[:-1]:
            prefix += value
            if prefix < 0:
                sign_definite = False
        for index, value in enumerate(base):
            linear[index] += value
        if sign_definite:
            continue
        divisor = math.gcd(*(abs(value) for value in direction))
        primitive = tuple(value // divisor for value in direction)
        hinges[primitive] += divisor
    return tuple(linear), dict(hinges)


def add_semantic(
    linear: list[Fraction], hinges: dict[Direction, Fraction], semantic: Semantic, coefficient: Fraction
) -> None:
    for index, value in enumerate(semantic[0]):
        linear[index] += coefficient * value
    for direction, value in semantic[1].items():
        updated = hinges.get(direction, Fraction()) + coefficient * value
        if updated:
            hinges[direction] = updated
        else:
            hinges.pop(direction, None)


def replay_public(dp, path: Path, n: int, degree: int) -> dict[str, object]:
    terms = load_certificate(path, n, degree)
    linear = [Fraction() for _ in range(n)]
    hinges: dict[Direction, Fraction] = {}
    first_semantic: Semantic | None = None
    for term in terms:
        semantic = normal_form(dp, term.pair, n)
        if first_semantic is None and term.coefficient:
            first_semantic = semantic
        add_semantic(linear, hinges, semantic, term.coefficient)
    target = [Fraction() for _ in range(n - 1)] + [Fraction(1)]
    require(not hinges and linear == target, f"public MAX{n} replay failed")
    require(first_semantic is not None, "missing mutation term")
    mutated_linear = linear.copy()
    mutated_hinges = dict(hinges)
    add_semantic(mutated_linear, mutated_hinges, first_semantic, Fraction(1, coefficient_lcm(terms)))
    require(bool(mutated_hinges) or mutated_linear != target, f"public MAX{n} mutation escaped")
    return {
        "n": n,
        "degree": degree,
        "terms": len(terms),
        "coefficient_lcm": coefficient_lcm(terms),
        "linear": [str(value) for value in linear],
        "hinge_residual_nonzeros": 0,
        "one_unit_first_coefficient_mutation_rejected": True,
    }


def vector_from_semantic(semantic: Semantic, directions: Sequence[Direction]) -> np.ndarray:
    row = {direction: index for index, direction in enumerate(directions)}
    output = np.zeros(len(directions) + len(semantic[0]), dtype=np.int64)
    for direction, value in semantic[1].items():
        require(direction in row, "semantic direction outside row universe")
        output[row[direction]] = value
    output[len(directions) :] = np.asarray(semantic[0], dtype=np.int64)
    return output


def common_counts(common: Counter[Edge]) -> tuple[int, int]:
    loops = sum(multiplicity for (u, v), multiplicity in common.items() if u == v)
    nonloops = sum(multiplicity for (u, v), multiplicity in common.items() if u != v)
    return loops, nonloops


@dataclass
class Aggregate:
    n: int
    degree: int
    denominator: int
    raw_count: int
    signed_classes: int
    directions: tuple[Direction, ...]
    features: np.ndarray  # rows x 12, scaled by source denominator
    row_labels: list[dict[str, object]]
    overflow_bounds: list[int]
    feature_sha256: str
    reconciliation: dict[str, object]


def aggregate_from_representatives(
    *,
    dp,
    source: Sequence[Term],
    n: int,
    degree: int,
    records: Sequence[dict[str, object]] | None = None,
    matrix: np.ndarray | None = None,
    directions: Sequence[Direction] | None = None,
) -> Aggregate:
    denominator = coefficient_lcm(source)
    source_integer = [int(term.coefficient * denominator) for term in source]
    edges = tuple(combinations_with_replacement(range(n), 2))
    expected_raw = len(source) * len(edges) * len(edges)
    global_common_loop = np.zeros(FEATURES, dtype=np.int64)
    global_common_nonloop = np.zeros(FEATURES, dtype=np.int64)

    if records is None:
        dynamic: dict[str, dict[str, object]] = {}
        for term_index, term in enumerate(source):
            coefficient = source_integer[term_index]
            for left_edge in edges:
                for right_edge in edges:
                    pair: Pair = (
                        tuple(sorted(term.pair[0] + (left_edge,))),
                        tuple(sorted(term.pair[1] + (right_edge,))),
                    )
                    features = descriptor_features(term.pair, left_edge, right_edge, n)
                    weighted = [coefficient * value for value in features]
                    residual, common = cancel_with_common(pair)
                    key = signed_hash(residual, n)
                    bucket = dynamic.setdefault(
                        key,
                        {"representative": residual, "weights": [0] * FEATURES, "raw": 0},
                    )
                    bucket["raw"] = int(bucket["raw"]) + 1
                    values = bucket["weights"]
                    require(isinstance(values, list), "dynamic weight shape")
                    for index, value in enumerate(weighted):
                        values[index] += value
                    loops, nonloops = common_counts(common)
                    global_common_loop += np.asarray(weighted, dtype=np.int64) * loops
                    global_common_nonloop += np.asarray(weighted, dtype=np.int64) * nonloops
        keys = sorted(dynamic)
        weights = np.asarray([dynamic[key]["weights"] for key in keys], dtype=np.int64)
        semantics = []
        direction_set: set[Direction] = set()
        for key in keys:
            semantic = normal_form(dp, dynamic[key]["representative"], n)  # type: ignore[arg-type]
            semantics.append(semantic)
            direction_set.update(semantic[1])
        local_directions = tuple(sorted(direction_set))
        semantic_matrix = np.stack(
            [vector_from_semantic(semantic, local_directions) for semantic in semantics], axis=0
        )
        representative_loop = np.zeros(len(keys), dtype=np.int64)
        representative_nonloop = np.zeros(len(keys), dtype=np.int64)
        raw_reconciliation = sum(int(dynamic[key]["raw"]) for key in keys)
    else:
        require(matrix is not None and directions is not None, "bound records require matrix and directions")
        local_directions = tuple(directions)
        semantic_matrix = matrix
        require(len(records) == semantic_matrix.shape[0], "record/matrix count drift")
        index_by_hash: dict[str, int] = {}
        representative_loop = np.zeros(len(records), dtype=np.int64)
        representative_nonloop = np.zeros(len(records), dtype=np.int64)
        for index, record in enumerate(records):
            key = str(record["signed_certificate_sha256"])
            require(key not in index_by_hash, "duplicate signed class")
            index_by_hash[key] = index
            pair = parse_pair(record["representative"]["pair"], n)  # type: ignore[index]
            _residual, common = cancel_with_common(pair)
            representative_loop[index], representative_nonloop[index] = common_counts(common)
        weights = np.zeros((len(records), FEATURES), dtype=np.int64)
        raw_reconciliation = 0
        for term_index, term in enumerate(source):
            coefficient = source_integer[term_index]
            for left_edge in edges:
                for right_edge in edges:
                    pair = (
                        tuple(sorted(term.pair[0] + (left_edge,))),
                        tuple(sorted(term.pair[1] + (right_edge,))),
                    )
                    features = descriptor_features(term.pair, left_edge, right_edge, n)
                    weighted = np.asarray([coefficient * value for value in features], dtype=np.int64)
                    residual, common = cancel_with_common(pair)
                    key = signed_hash(residual, n)
                    require(key in index_by_hash, f"raw descriptor escaped bound map: {key}")
                    weights[index_by_hash[key], :] += weighted
                    loops, nonloops = common_counts(common)
                    global_common_loop += weighted * loops
                    global_common_nonloop += weighted * nonloops
                    raw_reconciliation += 1

    require(raw_reconciliation == expected_raw, "raw descriptor reconciliation failed")
    require(weights.shape == (semantic_matrix.shape[0], FEATURES), "weight matrix shape drift")

    # Correct the bound representative's common padding, then restore the raw
    # descriptor common padding.  These contributions have no hinge rows.
    loop_semantic = normal_form(dp, (((0, 0),), ((0, 0),)), n)
    nonloop_semantic = normal_form(dp, (((0, 1),), ((0, 1),)), n)
    require(not loop_semantic[1] and not nonloop_semantic[1], "common edge acquired a hinge")
    common_loop_vector = vector_from_semantic(loop_semantic, local_directions)
    common_nonloop_vector = vector_from_semantic(nonloop_semantic, local_directions)

    row_max = np.zeros(semantic_matrix.shape[0], dtype=np.int64)
    for start in range(0, semantic_matrix.shape[0], 128):
        stop = min(start + 128, semantic_matrix.shape[0])
        block = semantic_matrix[start:stop].astype(np.int64, copy=False)
        row_max[start:stop] = np.max(np.abs(block), axis=1)
    overflow_bounds = []
    for feature in range(FEATURES):
        base_bound = sum(
            abs(int(weights[index, feature])) * int(row_max[index]) for index in range(weights.shape[0])
        )
        correction_loop = abs(
            int(global_common_loop[feature])
            - sum(int(weights[index, feature]) * int(representative_loop[index]) for index in range(weights.shape[0]))
        ) * int(np.max(np.abs(common_loop_vector)))
        correction_nonloop = abs(
            int(global_common_nonloop[feature])
            - sum(int(weights[index, feature]) * int(representative_nonloop[index]) for index in range(weights.shape[0]))
        ) * int(np.max(np.abs(common_nonloop_vector)))
        bound = base_bound + correction_loop + correction_nonloop
        require(bound < INT64_SAFE_BOUND, f"feature {feature} int64 bound exceeded: {bound}")
        overflow_bounds.append(bound)

    # The bound MAX9 matrix is intentionally a memory map.  Accumulate only
    # its nonzero entries instead of materializing a 3.7 GiB int64 copy or
    # performing twelve dense passes over structural zeros.
    feature_columns = np.zeros((FEATURES, semantic_matrix.shape[1]), dtype=np.int64)
    for index in range(semantic_matrix.shape[0]):
        row = semantic_matrix[index]
        nonzero_columns = np.flatnonzero(row)
        if not len(nonzero_columns):
            continue
        active_features = np.flatnonzero(weights[index])
        if not len(active_features):
            continue
        values = row[nonzero_columns].astype(np.int64, copy=False)
        feature_columns[np.ix_(active_features, nonzero_columns)] += (
            weights[index, active_features, None] * values[None, :]
        )
    correction_loop = global_common_loop - weights.T @ representative_loop
    correction_nonloop = global_common_nonloop - weights.T @ representative_nonloop
    feature_columns += correction_loop[:, None] * common_loop_vector[None, :]
    feature_columns += correction_nonloop[:, None] * common_nonloop_vector[None, :]
    features_by_row = np.ascontiguousarray(feature_columns.T, dtype=np.int64)

    row_labels = [
        {"kind": "hinge", "direction": list(direction)} for direction in local_directions
    ] + [{"kind": "linear", "rank": rank + 1} for rank in range(n)]
    require(len(row_labels) == features_by_row.shape[0], "row label shape drift")
    return Aggregate(
        n=n,
        degree=degree,
        denominator=denominator,
        raw_count=expected_raw,
        signed_classes=weights.shape[0],
        directions=local_directions,
        features=features_by_row,
        row_labels=row_labels,
        overflow_bounds=overflow_bounds,
        feature_sha256=array_sha(features_by_row),
        reconciliation={
            "raw_descriptors": raw_reconciliation,
            "signed_class_weight_sum_feature_1": int(weights[:, 0].sum()),
            "direct_raw_weight_sum_feature_1": sum(source_integer) * len(edges) * len(edges),
            "common_loop_feature_sums": list(map(int, global_common_loop)),
            "common_nonloop_feature_sums": list(map(int, global_common_nonloop)),
        },
    )


def replay_395(matrix: np.ndarray) -> dict[str, object]:
    require(sha256(CERT395) == EXPECTED[CERT395], "395 certificate drift")
    document = json.loads(CERT395.read_text(encoding="utf-8"))
    terms = document["terms"]
    coefficients = [Fraction(term["coefficient"]) for term in terms]
    denominator = 1
    for coefficient in coefficients:
        denominator = math.lcm(denominator, coefficient.denominator)
    integer = np.asarray([int(value * denominator) for value in coefficients], dtype=np.int64)
    columns = np.asarray([int(term["column_index"]) for term in terms], dtype=np.int64)
    require(len(set(map(int, columns))) == len(columns) == 395, "395 support drift")
    bound = sum(abs(int(value)) for value in integer) * int(np.max(np.abs(matrix[columns].astype(np.int64))))
    require(bound < INT64_SAFE_BOUND, "395 replay int64 bound exceeded")
    residual = integer @ matrix[columns].astype(np.int64)
    target = np.zeros(matrix.shape[1], dtype=np.int64)
    target[-1] = denominator
    require(np.array_equal(residual, target), "395 matrix replay failed")
    mutant = residual + matrix[int(columns[0])].astype(np.int64)
    require(not np.array_equal(mutant, target), "395 coefficient mutation escaped")
    return {
        "terms": len(terms),
        "coefficient_lcm": denominator,
        "exact_matrix_replay": True,
        "one_unit_coefficient_mutation_rejected": True,
        "int64_bound": bound,
    }


def load_bound_n9(dp, kernel) -> tuple[list[dict[str, object]], np.ndarray, tuple[Direction, ...]]:
    retained, repair, _missing = kernel.load_map_and_targets()
    records = retained + repair
    matrix = np.load(MATRIX9, mmap_mode="r", allow_pickle=False)
    require(matrix.shape == (22_666, 20_694) and matrix.dtype == np.dtype("<i4"), "MAX9 matrix drift")
    directions = kernel.direction_universe(9, 4)
    require(len(directions) == 20_685, "MAX9 direction universe drift")

    # Column order and common-padding correction are checked on fixed rows.
    row_by_direction = {direction: index for index, direction in enumerate(directions)}
    for index in (0, 327, len(records) - 1):
        pair = parse_pair(records[index]["representative"]["pair"], 9)
        semantic = normal_form(dp, pair, 9)
        vector = np.zeros(matrix.shape[1], dtype=np.int64)
        for direction, value in semantic[1].items():
            vector[row_by_direction[direction]] = value
        vector[len(directions) :] = np.asarray(semantic[0], dtype=np.int64)
        require(np.array_equal(vector, matrix[index]), f"bound MAX9 column order mismatch {index}")
    return records, matrix, directions


def rank_exact(matrix: np.ndarray) -> int:
    return int(fmpz_mat([[int(value) for value in row] for row in matrix]).rank())


def independent_row_indices(matrix: np.ndarray, target_rank: int) -> list[int]:
    basis: dict[int, list[Fraction]] = {}
    selected: list[int] = []
    for index, raw in enumerate(matrix):
        row = [Fraction(int(value)) for value in raw]
        for pivot in sorted(basis):
            if row[pivot]:
                factor = row[pivot]
                base = basis[pivot]
                row = [x - factor * y for x, y in zip(row, base, strict=True)]
        pivot = next((column for column, value in enumerate(row) if value), None)
        if pivot is None:
            continue
        scale = row[pivot]
        row = [value / scale for value in row]
        basis[pivot] = row
        selected.append(index)
        if len(selected) == target_rank:
            return selected
    raise GateError(f"could not find {target_rank} exact independent rows")


def solve_joint(first: Aggregate, second: Aggregate) -> dict[str, object]:
    require((first.degree, second.degree) == (2, 3), "calibration degree drift")
    a_first = np.concatenate((first.features, first.degree * first.features), axis=1)
    a_second = np.concatenate((second.features, second.degree * second.features), axis=1)
    matrix = np.concatenate((a_first, a_second), axis=0)
    target_first = np.zeros(first.features.shape[0], dtype=np.int64)
    target_first[-1] = first.denominator
    target_second = np.zeros(second.features.shape[0], dtype=np.int64)
    target_second[-1] = second.denominator
    target = np.concatenate((target_first, target_second))
    augmented = np.column_stack((matrix, target))
    rank = rank_exact(matrix)
    augmented_rank = rank_exact(augmented)
    require(augmented_rank in (rank, rank + 1), "augmented rank jump exceeded one")
    row_labels = [
        {"transition": "MAX6_to_MAX7", **label} for label in first.row_labels
    ] + [{"transition": "MAX8_to_MAX9", **label} for label in second.row_labels]
    output: dict[str, object] = {
        "rows": int(matrix.shape[0]),
        "columns": int(matrix.shape[1]),
        "rank_over_Q": rank,
        "augmented_rank_over_Q": augmented_rank,
        "matrix_sha256": array_sha(matrix),
        "target_sha256": array_sha(target),
    }
    if augmented_rank > rank:
        selected = independent_row_indices(augmented, augmented_rank)
        witness_matrix = matrix[selected]
        witness_target = target[selected]
        witness_augmented = augmented[selected]
        witness_rank = rank_exact(witness_matrix)
        witness_augmented_rank = rank_exact(witness_augmented)
        require(witness_rank < witness_augmented_rank, "selected rows are not an inconsistency witness")
        output.update(
            {
                "result": "EXACT_Q_NONMEMBERSHIP",
                "witness": {
                    "row_indices": selected,
                    "row_labels": [row_labels[index] for index in selected],
                    "coefficient_matrix": [[str(int(value)) for value in row] for row in witness_matrix],
                    "target": [str(int(value)) for value in witness_target],
                    "rank_over_Q": witness_rank,
                    "augmented_rank_over_Q": witness_augmented_rank,
                    "canonical_sha256": canonical_sha(
                        {
                            "matrix": witness_matrix.tolist(),
                            "target": witness_target.tolist(),
                        }
                    ),
                },
            }
        )
        return output

    # Deterministic exact solution from independent augmented rows, free variables zero.
    selected = independent_row_indices(matrix, rank)
    rows = [[Fraction(int(value)) for value in matrix[index]] + [Fraction(int(target[index]))] for index in selected]
    pivot_rows: dict[int, list[Fraction]] = {}
    for row in rows:
        for pivot in sorted(pivot_rows):
            if row[pivot]:
                factor = row[pivot]
                row = [x - factor * y for x, y in zip(row, pivot_rows[pivot], strict=True)]
        pivot = next((column for column, value in enumerate(row[:-1]) if value), None)
        require(pivot is not None, "solution row lost pivot")
        scale = row[pivot]
        row = [value / scale for value in row]
        pivot_rows[pivot] = row
    for pivot in sorted(pivot_rows, reverse=True):
        row = pivot_rows[pivot]
        for earlier in sorted(p for p in pivot_rows if p < pivot):
            if pivot_rows[earlier][pivot]:
                factor = pivot_rows[earlier][pivot]
                pivot_rows[earlier] = [
                    x - factor * y for x, y in zip(pivot_rows[earlier], row, strict=True)
                ]
    solution = [Fraction() for _ in range(matrix.shape[1])]
    for pivot, row in pivot_rows.items():
        solution[pivot] = row[-1]
    for row, rhs in zip(matrix, target, strict=True):
        require(sum(Fraction(int(value)) * coefficient for value, coefficient in zip(row, solution, strict=True)) == int(rhs), "serialized solution replay failed")
    output.update(
        {
            "result": "EXACT_Q_MEMBERSHIP",
            "solution": [str(value) for value in solution],
            "support": sum(bool(value) for value in solution),
            "free_variables_set_to_zero": matrix.shape[1] - rank,
        }
    )
    return output


def feature_controls(dp) -> dict[str, object]:
    n = 7
    pair: Pair = (((0, 1), (0, 2), (4, 4)), ((1, 2), (2, 3), (5, 6)))
    left_edge, right_edge = (0, 1), (2, 3)
    baseline = descriptor_features(pair, left_edge, right_edge, n)
    permutations_to_check = (
        tuple((index + 2) % n for index in range(n)),
        (1, 0, 2, 3, 4, 6, 5),
    )
    for permutation in permutations_to_check:
        require(
            descriptor_features(
                relabel_pair(pair, permutation),
                relabel_edge(left_edge, permutation),
                relabel_edge(right_edge, permutation),
                n,
            )
            == baseline,
            "simultaneous relabelling changed features",
        )
    swapped = descriptor_features((pair[1], pair[0]), right_edge, left_edge, n)
    require(swapped == baseline, "branch swap changed features")
    source_only = descriptor_features(relabel_pair(pair, permutations_to_check[0]), left_edge, right_edge, n)
    require(source_only != baseline, "source-only relabelling mutant escaped")
    edge_only = descriptor_features(pair, relabel_edge(left_edge, permutations_to_check[0]), right_edge, n)
    require(edge_only != baseline, "one-edge relabelling mutant escaped")
    loop_pair: Pair = (((0, 0), (0, 1)), ((1, 2), (3, 4)))
    loop_once = descriptor_features(loop_pair, (0, 0), (1, 2), n, loop_twice=False)
    loop_twice = descriptor_features(loop_pair, (0, 0), (1, 2), n, loop_twice=True)
    require(loop_once != loop_twice, "loop-incidence mutant escaped")
    require(
        signed_hash(pair, n)
        == signed_hash(relabel_pair(pair, permutations_to_check[0]), n)
        == signed_hash((pair[1], pair[0]), n),
        "signed orbit control failed",
    )
    literal_pair: Pair = (((0, 1), (0, 2)), ((1, 2), (3, 4)))
    literal = literal_normal_form(literal_pair, 5)
    dynamic = normal_form(dp, literal_pair, 5)
    require(literal == dynamic, "literal/DP normal form control failed")
    return {
        "simultaneous_relabellings_preserved": len(permutations_to_check),
        "global_branch_swap_preserved": True,
        "source_only_relabelling_mutant_rejected": True,
        "one_edge_relabelling_mutant_rejected": True,
        "loop_twice_incidence_mutant_rejected": True,
        "signed_orbit_relabelling_and_swap_preserved": True,
        "literal_permutation_equals_dp": True,
    }


def self_test() -> dict[str, object]:
    require(FEATURES == 12 and len(set(FEATURE_NAMES)) == FEATURES, "feature schema drift")
    require(int(fmpz_mat([[1, 2], [2, 4]]).rank()) == 1, "flint rank control failed")
    dp = load_module(DP_PATH, "g0119_selftest_dp")
    controls = feature_controls(dp)
    return {"feature_schema": list(FEATURE_NAMES), "flint_exact_rank": True, **controls}


def run(report_path: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    prereg_hash = sha256(PREREGISTRATION)
    bindings = bind_inputs()
    dp = load_module(DP_PATH, "g0119_bound_dp")
    kernel = load_module(KERNEL, "g0119_bound_kernel")
    controls = feature_controls(dp)

    public_controls = {
        "MAX6": replay_public(dp, CERT6, 6, 2),
        "MAX8": replay_public(dp, CERT8, 8, 3),
        "MAX10": replay_public(dp, CERT10, 10, 4),
    }

    records9, matrix9, directions9 = load_bound_n9(dp, kernel)
    controls["G0115_395_matrix_replay"] = replay_395(matrix9)
    source6 = load_certificate(CERT6, 6, 2)
    source8 = load_certificate(CERT8, 8, 3)
    aggregate7 = aggregate_from_representatives(dp=dp, source=source6, n=7, degree=2)
    aggregate9 = aggregate_from_representatives(
        dp=dp,
        source=source8,
        n=9,
        degree=3,
        records=records9,
        matrix=matrix9,
        directions=directions9,
    )
    for aggregate in (aggregate7, aggregate9):
        require(
            aggregate.reconciliation["signed_class_weight_sum_feature_1"]
            == aggregate.reconciliation["direct_raw_weight_sum_feature_1"],
            f"MAX{aggregate.n} feature-1 reconciliation failed",
        )
    joint = solve_joint(aggregate7, aggregate9)

    transitions = {}
    for label, aggregate in (("MAX6_to_MAX7", aggregate7), ("MAX8_to_MAX9", aggregate9)):
        transitions[label] = {
            "source_degree": aggregate.degree,
            "target_n": aggregate.n,
            "source_coefficient_lcm": aggregate.denominator,
            "raw_descriptors": aggregate.raw_count,
            "signed_W_classes": aggregate.signed_classes,
            "complete_hinge_rows": len(aggregate.directions),
            "linear_rows": aggregate.n,
            "feature_matrix_sha256": aggregate.feature_sha256,
            "row_order_sha256": canonical_sha(aggregate.row_labels),
            "int64_absolute_bounds": aggregate.overflow_bounds,
            "reconciliation": aggregate.reconciliation,
        }

    result = {
        "schema": "g0119-algebraic-signed-degree-operator-v1",
        "result": joint["result"],
        "bindings": bindings
        | {
            "artifacts/math/G-0119/PREREGISTRATION.md": prereg_hash,
            "artifacts/math/G-0119/algebraic_signed_degree_operator.py": script_hash,
        },
        "operator": {
            "feature_order": list(FEATURE_NAMES),
            "degree_dependence": "alpha_j + k*beta_j",
            "parameters": 24,
            "aggregation": "raw_sum",
            "loop_incidence": "one",
        },
        "controls": controls | {"public_certificates": public_controls},
        "transitions": transitions,
        "joint_exact_Q_decision": joint,
        "MAX10_to_MAX11": {
            "evaluated": False,
            "reason": (
                "Preregistered stop: lower-transition joint system is inconsistent."
                if joint["result"] == "EXACT_Q_NONMEMBERSHIP"
                else "Lower joint law passed; target replay requires a separately materialized frozen-law run."
            ),
        },
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": (
            "Exact decision only for the frozen twelve-monomial affine-in-degree raw-sum operator. "
            "A null does not decide other algebraic operators, lift-span membership, the full degree-five "
            "graphical dictionary, or unrestricted MAX11 representability."
        ),
    }
    require(sha256(SCRIPT) == script_hash, "script changed during execution")
    write_exclusive(report_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    require(args.self_test ^ args.run, "choose exactly one of --self-test or --run")
    if args.self_test:
        print(json.dumps(self_test(), sort_keys=True))
        return 0
    require(args.report is not None, "--run requires --report")
    value = run(args.report.resolve())
    print(json.dumps(value, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
