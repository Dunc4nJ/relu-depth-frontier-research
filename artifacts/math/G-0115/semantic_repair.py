#!/usr/bin/env python3
"""Exact semantic benchmark and residual repair for the G-0115 parity lift."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
import importlib.util
from itertools import permutations
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Iterable, Sequence

from flint import fmpq_mat, fmpz_mat, nmod_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
MAP = HERE / "parity_lift_representatives_v1.jsonl.gz"
CENSUS = HERE / "parity_lift_census_v1.json"
CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
CERT9 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_9_4.json"
DP_PATH = ROOT / "artifacts/math/G-0094/cleanroom_star_quotient.py"
EXPECTED = {
    MAP: "2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148",
    CENSUS: "844dba5cf023f68a083261dd1612503c16309297f21ca57e26497f7a6df28d7a",
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    CERT9: "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
    DP_PATH: "d63f08e9e641109154d0e16f0d84d04a0ad4edd4402b8ffe5d01985de9163f71",
}
N = 9
EXPECTED_REPAIR = 22_338
EXPECTED_RETAINED = 328
EXPECTED_MISSING = 9
EXPECTED_DIRECTIONS = 20_685
PRIMES = (1_000_003, 1_000_033, 1_000_037)

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]
Direction = tuple[int, ...]
Semantic = tuple[tuple[int, ...], dict[Direction, int]]


class RepairError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RepairError(message)


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


def bind_inputs() -> dict[str, str]:
    observed = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): value for path, value in EXPECTED.items()}
    require(observed == expected, f"input drift: {observed}")
    return observed


def load_dp():
    require(sha256(DP_PATH) == EXPECTED[DP_PATH], "DP drift")
    spec = importlib.util.spec_from_file_location("g0115_bound_dp", DP_PATH)
    require(spec is not None and spec.loader is not None, "cannot load DP")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def parse_pair(raw: object, n: int = N) -> Pair:
    require(isinstance(raw, list) and len(raw) == 2, "malformed pair")
    sides: list[Side] = []
    for side_raw in raw:
        require(isinstance(side_raw, list), "malformed side")
        side: list[Edge] = []
        for edge_raw in side_raw:
            require(isinstance(edge_raw, list) and len(edge_raw) == 2, "malformed edge")
            u, v = map(int, edge_raw)
            require(1 <= u <= v <= n, "endpoint outside arity")
            side.append((u - 1, v - 1))
        sides.append(tuple(sorted(side)))
    require(len(sides[0]) == len(sides[1]), "unequal branch degree")
    return sides[0], sides[1]


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[[u + 1, v + 1] for u, v in side] for side in pair]


def cancel(pair: Pair) -> Pair:
    left, right = Counter(pair[0]), Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    return tuple(sorted(left.elements())), tuple(sorted(right.elements()))


def load_certificate(path: Path, n: int, degree: int) -> list[tuple[Fraction, Pair]]:
    require(sha256(path) == EXPECTED[path], "certificate drift")
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == n and isinstance(document.get("terms"), list), "bad certificate")
    output = []
    for term in document["terms"]:
        pair = parse_pair(term["pair"], n)
        require(len(pair[0]) == degree, "certificate degree drift")
        output.append((Fraction(term["coefficient"]), pair))
    return output


def normal_form(dp, pair: Pair, n: int = N) -> Semantic:
    linear, directions, coefficients = dp.ordered_normal_form(pair, n)
    hinges = {
        tuple(map(int, direction)): int(coefficient)
        for direction, coefficient in zip(directions, coefficients, strict=True)
        if int(coefficient)
    }
    return tuple(map(int, linear)), hinges


def alternating(n: int) -> tuple[int, ...]:
    return tuple((-1) ** (n - rank) * math.comb(n - 1, rank - 1) for rank in range(1, n + 1))


def lambda_value(linear: Sequence[int]) -> int:
    return sum(a * int(b) for a, b in zip(alternating(len(linear)), linear, strict=True))


def add_scaled(
    linear: list[Fraction], hinges: dict[Direction, Fraction], semantic: Semantic, coefficient: Fraction
) -> None:
    for index, value in enumerate(semantic[0]):
        linear[index] += coefficient * value
    for direction, value in semantic[1].items():
        hinges[direction] = hinges.get(direction, Fraction()) + coefficient * value
        if not hinges[direction]:
            del hinges[direction]


def certificate_replay(dp, path: Path, n: int, degree: int) -> dict[str, object]:
    terms = load_certificate(path, n, degree)
    linear = [Fraction() for _ in range(n)]
    hinges: dict[Direction, Fraction] = {}
    for coefficient, pair in terms:
        add_scaled(linear, hinges, normal_form(dp, pair, n), coefficient)
    expected = [Fraction() for _ in range(n)]
    expected[-1] = 1
    require(linear == expected and not hinges, f"MAX{n} replay failed")
    mutant, pair = terms[0]
    mutation = normal_form(dp, pair, n)
    require(bool(mutation[1]) or any(mutation[0]), "mutation term is zero")
    return {"n": n, "terms": len(terms), "linear": [str(v) for v in linear], "hinges": 0}


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
        direction = tuple(b - a for a, b in zip(base, other, strict=True))
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


def graph_features(pair: Pair) -> tuple[object, ...]:
    negative, positive = cancel(pair)
    active = sorted({vertex for side in (negative, positive) for edge in side for vertex in edge})
    absolute_degrees = Counter()
    branch_degrees = [Counter(), Counter()]
    for branch_index, side in enumerate((negative, positive)):
        for u, v in side:
            absolute_degrees[u] += 1
            branch_degrees[branch_index][u] += 1
            if v != u:
                absolute_degrees[v] += 1
                branch_degrees[branch_index][v] += 1
    parent = {v: v for v in active}

    def find(v: int) -> int:
        while parent[v] != v:
            parent[v] = parent[parent[v]]
            v = parent[v]
        return v

    for side in (negative, positive):
        for u, v in side:
            if u == v:
                continue
            ru, rv = find(u), find(v)
            if ru != rv:
                parent[rv] = ru
    components = len({find(v) for v in active}) if active else 0
    mass = len(negative)
    beta = 2 * mass - len(active) + components
    abs_degree = tuple(sorted(absolute_degrees.values(), reverse=True))
    signed_degree = tuple(sorted((tuple(sorted(branch_degrees[i].values(), reverse=True)) for i in range(2))))
    loops = tuple(sorted(sum(u == v for u, v in side) for side in (negative, positive)))
    return mass, len(active), components, beta, abs_degree, signed_degree, loops


def padded_l1(first: Sequence[int], second: Sequence[int]) -> int:
    size = max(len(first), len(second))
    return sum(abs((first[i] if i < len(first) else 0) - (second[i] if i < len(second) else 0)) for i in range(size))


def feature_distance(first: tuple[object, ...], second: tuple[object, ...]) -> tuple[int, ...]:
    f_mass, f_active, f_components, f_beta, f_abs, f_signed, f_loops = first
    s_mass, s_active, s_components, s_beta, s_abs, s_signed, s_loops = second
    signed_direct = padded_l1(f_signed[0], s_signed[0]) + padded_l1(f_signed[1], s_signed[1])
    signed_swap = padded_l1(f_signed[0], s_signed[1]) + padded_l1(f_signed[1], s_signed[0])
    return (
        abs(f_mass - s_mass),
        abs(f_active - s_active),
        abs(f_components - s_components),
        abs(f_beta - s_beta),
        padded_l1(f_abs, s_abs),
        min(signed_direct, signed_swap),
        padded_l1(f_loops, s_loops),
    )


def load_map_and_targets() -> tuple[list[dict[str, object]], list[dict[str, object]], list[tuple[Fraction, Pair]]]:
    target = load_certificate(CERT9, N, 4)
    retained: list[dict[str, object]] = []
    repair: list[dict[str, object]] = []
    present_indices: set[int] = set()
    with gzip.open(MAP, "rt", encoding="utf-8") as source:
        header = json.loads(next(source))
        require(header.get("signed_W_orbits") == 22_666, "map header drift")
        for line in source:
            record = json.loads(line)
            indices = list(map(int, record["public_term_indices"]))
            if indices:
                require(len(indices) == 1, "public signed class is not unique")
                present_indices.update(indices)
                retained.append(record)
            else:
                repair.append(record)
    missing = [term for index, term in enumerate(target) if index not in present_indices]
    require(len(retained) == EXPECTED_RETAINED, "retained count drift")
    require(len(repair) == EXPECTED_REPAIR, "repair count drift")
    require(len(missing) == EXPECTED_MISSING, "missing count drift")
    missing_features = [graph_features(pair) for _coefficient, pair in missing]
    for record in repair:
        pair = parse_pair(record["representative"]["pair"])
        feature = graph_features(pair)
        record["topology_distance"] = list(min(feature_distance(feature, target_feature) for target_feature in missing_features))
    repair.sort(key=lambda record: (tuple(record["topology_distance"]), record["signed_certificate_sha256"]))
    return retained, repair, missing


def direction_universe(n: int = N, degree: int = 4) -> tuple[Direction, ...]:
    def weak(total: int, parts: int, prefix: tuple[int, ...] = ()) -> Iterable[tuple[int, ...]]:
        if parts == 1:
            yield prefix + (total,)
            return
        for first in range(total + 1):
            yield from weak(total - first, parts - 1, prefix + (first,))

    compositions = tuple(weak(degree, n))
    directions: set[Direction] = set()
    from itertools import combinations_with_replacement
    for left, right in combinations_with_replacement(compositions, 2):
        if left == right:
            continue
        direction = tuple(b - a for a, b in zip(left, right, strict=True))
        prefix = 0
        prefixes = []
        for value in direction[:-1]:
            prefix += value
            prefixes.append(prefix)
        if all(value >= 0 for value in prefixes):
            continue
        divisor = math.gcd(*(abs(value) for value in direction))
        directions.add(tuple(value // divisor for value in direction))
    result = tuple(sorted(directions))
    require(len(result) == EXPECTED_DIRECTIONS, f"direction census drift: {len(result)}")
    return result


def benchmark(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = bind_inputs()
    dp = load_dp()
    controls = {
        "MAX8": certificate_replay(dp, CERT8, 8, 3),
        "MAX9": certificate_replay(dp, CERT9, 9, 4),
    }
    retained, repair, missing = load_map_and_targets()
    universe = direction_universe()
    universe_set = set(universe)
    sample = repair[:128]
    sample_started = time.perf_counter()
    nonzeros = []
    semantics: list[Semantic] = []
    for record in sample:
        semantic = normal_form(dp, parse_pair(record["representative"]["pair"]))
        require(set(semantic[1]) <= universe_set, "sample hinge outside universe")
        semantics.append(semantic)
        nonzeros.append(len(semantic[1]))
    sample_seconds = time.perf_counter() - sample_started
    for index in (0, 127):
        literal = literal_normal_form(parse_pair(sample[index]["representative"]["pair"]), N)
        require(literal == semantics[index], f"literal/DP mismatch {index}")
    first = semantics[0]
    mutated_pair = list(map(list, parse_pair(sample[0]["representative"]["pair"])))
    # Replace one edge while preserving branch degree; this must change semantics.
    left = list(mutated_pair[0])
    old = left[0]
    replacement = (old[0], (old[1] + 1) % N)
    replacement = tuple(sorted(replacement))
    if replacement == old:
        replacement = tuple(sorted((old[0], (old[1] + 2) % N)))
    left[0] = replacement
    mutant: Pair = (tuple(sorted(left)), tuple(mutated_pair[1]))
    require(normal_form(dp, mutant) != first, "edge mutation did not change semantics")
    projected_seconds = sample_seconds * len(repair) / len(sample)
    projected_nonzeros = int(sum(nonzeros) * len(repair) / len(sample))
    report = {
        "schema": "max11-g0115-semantic-repair-benchmark-v1",
        "result": "PASS_RESOURCE_GATE" if projected_seconds <= 4 * 3600 else "STOP_RESOURCE_GATE",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "family": {
            "retained_fixed_classes": len(retained),
            "repair_classes": len(repair),
            "missing_public_terms": len(missing),
            "complete_hinge_universe": len(universe),
        },
        "benchmark": {
            "ordered_prefix_columns": len(sample),
            "seconds": sample_seconds,
            "nonzeros_min": min(nonzeros),
            "nonzeros_median": sorted(nonzeros)[len(nonzeros) // 2],
            "nonzeros_max": max(nonzeros),
            "nonzeros_total": sum(nonzeros),
            "projected_full_seconds": projected_seconds,
            "projected_full_nonzeros": projected_nonzeros,
            "projected_sparse_row_u32_value_i64_bytes": projected_nonzeros * 12,
            "full_dense_int64_bytes": (len(universe) + 1) * len(repair) * 8,
        },
        "controls": {
            "known_certificates": controls,
            "literal_9_factorial_atoms_match_DP": True,
            "edge_mutation_changes_semantics": True,
            "all_sample_hinges_in_complete_universe": True,
        },
        "claim_boundary": "Resource and semantic-kernel benchmark only; no repair rank or coefficient was computed.",
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during benchmark")
    fd = os.open(output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "wb") as destination:
        destination.write(canonical(report))
        destination.flush()
        os.fsync(destination.fileno())
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark", action="store_true")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args(argv)
    require(args.benchmark and args.output is not None and not args.output.exists(), "benchmark requires unused output")
    report = benchmark(args.output.resolve())
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
