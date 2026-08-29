#!/usr/bin/env python3
"""Exact discovery pipeline for the minimally cyclic MAX11 lift family.

This file deliberately separates three claims:

* ``classes`` proves only graph-isomorphism deduplication of the 16,000 raw
  lifts (vertex relabelling and one global colour swap are quotiented out);
* ``orbit-solve`` finds an exact rational solution on the finite
  ``{0,1,2,3}^11 / S_11`` evaluation grid;
* ``hinge-residual`` evaluates that proposed solution in the complete exact
  ordered-cone hinge normal form.  Only a zero residual here is a global
  identity.

The first two stages are discovery tools.  They must not be described as an
unrestricted MAX11 certificate.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass
from fractions import Fraction
import gzip
import hashlib
import json
from math import factorial, gcd, lcm
from pathlib import Path
import sys
from typing import Iterable, Iterator, Sequence


HERE = Path(__file__).resolve().parent
PROJECT_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))

from evaluate_minimal_lifts import (  # noqa: E402
    CERTIFICATE,
    N,
    all_profiles,
    assignment_count,
    build_bases,
    profile_groups,
)


CLASS_SCHEMA = "max11-minimal-lifts-isomorphism-v2"
ORBIT_SOLUTION_SCHEMA = "max11-minimal-lifts-orbit-solution-v3"
HINGE_RESIDUAL_SCHEMA = "max11-minimal-lifts-hinge-residual-v1"
FULL_MASK = (1 << N) - 1


Pair = tuple[tuple[tuple[int, int], ...], tuple[tuple[int, int], ...]]
Direction = tuple[int, ...]


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode(
        "utf-8"
    )


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def raw_candidate_pairs() -> tuple[list[Pair], str]:
    bases, metadata, candidate_digest = build_bases()
    pairs: list[Pair] = []
    for base_index, _term_index, _component_index, left_endpoint, right_endpoint in metadata:
        _, left, right, _ = bases[base_index]
        pairs.append(
            (
                tuple(left) + ((left_endpoint, N),),
                tuple(right) + ((right_endpoint, N),),
            )
        )
    if len(pairs) != 16_000:
        raise AssertionError(len(pairs))
    return pairs, candidate_digest


def pair_list_sha256(pairs: Sequence[Pair]) -> str:
    payload = [
        [[[a, b] for a, b in left], [[a, b] for a, b in right]]
        for left, right in pairs
    ]
    return sha256_bytes(canonical_json_bytes(payload))


def incidence_graph(pair: Pair):
    """Return a typed incidence graph whose automorphisms allow one colour swap."""

    import networkx as nx

    graph = nx.Graph()
    for vertex in range(1, N + 1):
        graph.add_node(("v", vertex), kind="vertex")
    # The two same-typed colour nodes may swap, but force all five edge atoms
    # of a colour to move together.
    for colour in range(2):
        graph.add_node(("c", colour), kind="colour")
    edge_index = 0
    for colour, side in enumerate(pair):
        for a, b in side:
            edge_node = ("e", edge_index)
            edge_index += 1
            graph.add_node(edge_node, kind="edge")
            graph.add_edge(edge_node, ("c", colour))
            graph.add_edge(edge_node, ("v", a))
            graph.add_edge(edge_node, ("v", b))
    if edge_index != 10:
        raise AssertionError(edge_index)
    return graph


def build_isomorphism_classes() -> dict[str, object]:
    """Deduplicate with WL only as a bucket filter and exact VF2 as authority."""

    import networkx as nx

    pairs, candidate_digest = raw_candidate_pairs()
    node_match = nx.algorithms.isomorphism.categorical_node_match("kind", None)
    buckets: dict[str, list[int]] = defaultdict(list)
    representative_graphs: list[object] = []
    representative_indices: list[int] = []
    raw_to_class: list[int] = []

    for raw_index, pair in enumerate(pairs):
        graph = incidence_graph(pair)
        wl_hash = nx.weisfeiler_lehman_graph_hash(
            graph, node_attr="kind", iterations=16, digest_size=32
        )
        class_index = None
        for possible_class in buckets[wl_hash]:
            if nx.is_isomorphic(
                graph, representative_graphs[possible_class], node_match=node_match
            ):
                class_index = possible_class
                break
        if class_index is None:
            class_index = len(representative_indices)
            representative_indices.append(raw_index)
            representative_graphs.append(graph)
            buckets[wl_hash].append(class_index)
        raw_to_class.append(class_index)

    class_sizes = [0] * len(representative_indices)
    for class_index in raw_to_class:
        class_sizes[class_index] += 1
    if len(representative_indices) != 9_804:
        raise AssertionError(
            f"expected independently observed 9804 classes, got {len(representative_indices)}"
        )
    if sum(class_sizes) != len(pairs):
        raise AssertionError("class census mismatch")

    return {
        "schema": CLASS_SCHEMA,
        "n": N,
        "raw_candidate_count": len(pairs),
        "candidate_metadata_sha256": candidate_digest,
        "raw_pair_list_sha256": pair_list_sha256(pairs),
        "source_certificate_path": str(CERTIFICATE.relative_to(PROJECT_ROOT)),
        "source_certificate_sha256": sha256_path(CERTIFICATE),
        "equivalence": "vertex relabelling and one global A/B colour swap",
        "accelerator": "NetworkX Weisfeiler-Lehman node-attribute hash, 16 iterations",
        "authority": "NetworkX exact VF2 typed-graph isomorphism within each WL bucket",
        "networkx_version": nx.__version__,
        "class_count": len(representative_indices),
        "representative_raw_indices": representative_indices,
        "raw_to_class": raw_to_class,
        "class_sizes": class_sizes,
    }


def load_classes(path: Path) -> dict[str, object]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != CLASS_SCHEMA:
        raise ValueError(f"wrong class schema in {path}")
    pairs, candidate_digest = raw_candidate_pairs()
    if document.get("raw_candidate_count") != len(pairs):
        raise ValueError("raw candidate count mismatch")
    if document.get("candidate_metadata_sha256") != candidate_digest:
        raise ValueError("candidate metadata digest mismatch")
    if document.get("raw_pair_list_sha256") != pair_list_sha256(pairs):
        raise ValueError("raw pair-list digest mismatch")
    if document.get("source_certificate_sha256") != sha256_path(CERTIFICATE):
        raise ValueError("source certificate digest mismatch")
    representatives = document.get("representative_raw_indices")
    raw_to_class = document.get("raw_to_class")
    if not isinstance(representatives, list) or not isinstance(raw_to_class, list):
        raise ValueError("invalid class mapping")
    if len(representatives) != document.get("class_count") or len(raw_to_class) != len(pairs):
        raise ValueError("class mapping length mismatch")
    return document


def load_orbit_matrix(orbit_directory: Path, candidate_digest: str):
    import numpy as np

    rows = []
    targets = []
    profiles = []
    input_files = []
    expected_groups = profile_groups()
    for group_index, expected_profiles in enumerate(expected_groups):
        path = orbit_directory / f"group-{group_index:02d}.npz"
        input_files.append(
            {"name": path.name, "bytes": path.stat().st_size, "sha256": sha256_path(path)}
        )
        with np.load(path, allow_pickle=False) as data:
            if str(data["schema"][0]) != "max11-minimal-lifts-orbits-v1":
                raise ValueError(f"orbit schema mismatch: {path}")
            if str(data["candidate_sha256"][0]) != candidate_digest:
                raise ValueError(f"orbit candidate metadata digest mismatch: {path}")
            if int(data["group_index"][0]) != group_index:
                raise ValueError(f"orbit group index mismatch: {path}")
            if int(data["group_count"][0]) != len(expected_groups):
                raise ValueError(f"orbit group count mismatch: {path}")
            observed_profiles = [tuple(map(int, row)) for row in data["profiles"].tolist()]
            if observed_profiles != expected_profiles:
                raise ValueError(f"orbit profile order mismatch: {path}")
            expected_targets = [
                assignment_count(profile)
                * max(level for level, count in enumerate(profile) if count)
                for profile in expected_profiles
            ]
            if data["targets"].tolist() != expected_targets:
                raise ValueError(f"orbit target mismatch: {path}")
            rows.append(data["rows"])
            targets.append(data["targets"])
            profiles.append(data["profiles"])
    matrix = np.concatenate(rows, axis=0)
    target = np.concatenate(targets)
    profile_array = np.concatenate(profiles, axis=0)
    if matrix.shape != (364, 16_000) or target.shape != (364,):
        raise AssertionError((matrix.shape, target.shape))
    if [tuple(map(int, row)) for row in profile_array.tolist()] != all_profiles():
        raise AssertionError("concatenated orbit profile coverage/order mismatch")
    return matrix, target, profile_array, input_files


def pivot_columns(rref_matrix, row_count: int, column_count: int) -> list[int]:
    pivots: list[int] = []
    for row in range(row_count):
        for column in range(column_count):
            if rref_matrix[row, column]:
                pivots.append(column)
                break
    return pivots


def solve_orbit_grid(
    class_path: Path, orbit_directory: Path, prime: int
) -> dict[str, object]:
    """Find and exactly verify one sparse basis solution on all 364 grid orbits."""

    import numpy as np
    from flint import fmpq, fmpq_mat, nmod_mat

    classes = load_classes(class_path)
    candidate_digest = str(classes["candidate_metadata_sha256"])
    matrix, target, profile_array, orbit_input_files = load_orbit_matrix(
        orbit_directory, candidate_digest
    )
    representatives = np.asarray(classes["representative_raw_indices"], dtype=np.int64)
    raw_to_class = np.asarray(classes["raw_to_class"], dtype=np.int64)
    representative_by_raw = representatives[raw_to_class]
    if not np.array_equal(matrix, matrix[:, representative_by_raw]):
        raise AssertionError("an asserted isomorphism class changes an orbit evaluation")
    reduced = matrix[:, representatives]
    row_count, column_count = reduced.shape

    modular = nmod_mat(reduced.tolist(), prime)
    reduced_rref, rank = modular.rref()
    basis_columns = pivot_columns(reduced_rref, rank, column_count)
    if len(basis_columns) != rank:
        raise AssertionError("candidate pivot extraction failed")

    basis_modular = nmod_mat(
        reduced[:, np.asarray(basis_columns, dtype=np.int64)].tolist(), prime
    )
    transposed_rref, transposed_rank = basis_modular.transpose().rref()
    pivot_rows = pivot_columns(transposed_rref, transposed_rank, row_count)
    if transposed_rank != rank or len(pivot_rows) != rank:
        raise AssertionError("coordinate pivot extraction failed")

    exact = fmpq_mat(rank, rank)
    rhs = fmpq_mat(rank, 1)
    for row_position, source_row in enumerate(pivot_rows):
        for column_position, source_column in enumerate(basis_columns):
            value = int(reduced[source_row, source_column])
            if value:
                exact[row_position, column_position] = value
        target_value = int(target[source_row])
        if target_value:
            rhs[row_position, 0] = target_value
    solution = exact.solve(rhs)

    for source_row in range(row_count):
        value = fmpq(0)
        for column_position, source_column in enumerate(basis_columns):
            coefficient = int(reduced[source_row, source_column])
            if coefficient:
                value += solution[column_position, 0] * coefficient
        if value != int(target[source_row]):
            raise AssertionError(f"exact orbit verification failed at row {source_row}")

    pairs, candidate_digest = raw_candidate_pairs()
    terms = []
    for column_position, class_index in enumerate(basis_columns):
        orbit_average_coefficient = solution[column_position, 0]
        if not orbit_average_coefficient:
            continue
        # The grid rows sum over distinct assignments of a repeated-value
        # profile, whereas a certificate atom sums over all n! permutations.
        # Each assignment has stabilizer product(count_i!), so a grid solution
        # against (#assignments)*MAX is n! times the certificate normalization.
        coefficient = orbit_average_coefficient / factorial(N)
        raw_index = int(representatives[class_index])
        left, right = pairs[raw_index]
        terms.append(
            {
                "coefficient": str(coefficient),
                "orbit_average_coefficient": str(orbit_average_coefficient),
                "class_index": class_index,
                "representative_raw_index": raw_index,
                "pair": [[list(edge) for edge in left], [list(edge) for edge in right]],
            }
        )

    return {
        "schema": ORBIT_SOLUTION_SCHEMA,
        "n": N,
        "family": "same-component two-edge lifts of full-active MAX10 two-forest terms",
        "candidate_metadata_sha256": candidate_digest,
        "raw_pair_list_sha256": classes["raw_pair_list_sha256"],
        "source_certificate_sha256": classes["source_certificate_sha256"],
        "class_file_sha256": sha256_path(class_path),
        "orbit_grid": "all 364 S_11-orbits of {0,1,2,3}^11",
        "coefficient_normalization": (
            "stored coefficient = internal distinct-assignment orbit-solve coefficient / 11!; "
            "therefore full unnormalized S_11 atoms target MAX11, not 11!*MAX11"
        ),
        "orbit_directory": str(orbit_directory),
        "modular_discovery_prime": prime,
        "grid_rank": rank,
        "class_count": column_count,
        "basis_column_count": len(basis_columns),
        "nonzero_term_count": len(terms),
        "profiles_sha256": sha256_bytes(profile_array.tobytes(order="C")),
        "target_sha256": sha256_bytes(target.tobytes(order="C")),
        "raw_orbit_matrix_int64_c_sha256": sha256_bytes(matrix.tobytes(order="C")),
        "quotient_orbit_matrix_int64_c_sha256": sha256_bytes(
            reduced.tobytes(order="C")
        ),
        "orbit_input_files": orbit_input_files,
        "warning": "finite-grid identity only; run hinge-residual before any global claim",
        "terms": terms,
    }


def signed_adjacency(pair: Pair) -> list[list[int]]:
    weights = [[0] * N for _ in range(N)]
    for sign, side in ((-1, pair[0]), (1, pair[1])):
        for one_based_a, one_based_b in side:
            a, b = one_based_a - 1, one_based_b - 1
            if a == b:
                # Not reached by this family, but keeps the meaning explicit.
                weights[a][a] += sign
            else:
                weights[a][b] += sign
                weights[b][a] += sign
    return weights


def direction_histogram(pair: Pair) -> dict[Direction, int]:
    """Count all 11! orderings by their exact right-minus-left direction."""

    weights = signed_adjacency(pair)
    subset_sums = [[0] * (1 << N) for _ in range(N)]
    for vertex in range(N):
        for mask in range(1, 1 << N):
            bit = mask & -mask
            neighbour = bit.bit_length() - 1
            subset_sums[vertex][mask] = (
                subset_sums[vertex][mask ^ bit] + weights[vertex][neighbour]
            )

    cache: dict[int, dict[Direction, int]] = {0: {(): 1}}
    for cardinality in range(1, N + 1):
        for mask in range(1, 1 << N):
            if mask.bit_count() != cardinality:
                continue
            output: dict[Direction, int] = defaultdict(int)
            remaining_vertices = mask
            while remaining_vertices:
                bit = remaining_vertices & -remaining_vertices
                vertex = bit.bit_length() - 1
                remaining_vertices ^= bit
                lower_mask = mask ^ bit
                high_coordinate = subset_sums[vertex][lower_mask]
                for lower_direction, multiplicity in cache[lower_mask].items():
                    output[lower_direction + (high_coordinate,)] += multiplicity
            cache[mask] = dict(output)
        # No future state can refer to masks two or more levels below.  Keeping
        # only the current and immediately previous cardinalities sharply caps
        # process memory during large parallel runs.
        stale_cardinality = cardinality - 2
        if stale_cardinality >= 0:
            for stale_mask in [m for m in cache if m.bit_count() == stale_cardinality]:
                del cache[stale_mask]
    histogram = cache[FULL_MASK]
    if sum(histogram.values()) != factorial(N):
        raise AssertionError("permutation multiplicity census failed")
    return histogram


def nonpositive_on_ordered_cone(direction: Direction) -> bool:
    if sum(direction) != 0:
        return False
    prefix = 0
    for value in direction[:-1]:
        prefix += value
        if prefix < 0:
            return False
    return True


@dataclass(frozen=True)
class HingeColumn:
    linear: tuple[int, ...]
    hinges: dict[Direction, int]
    raw_direction_count: int
    permutation_count: int


def exact_hinge_column(pair: Pair) -> HingeColumn:
    """Return the full symmetrized atom in canonical ordered-cone coordinates."""

    if any(a == b for side in pair for a, b in side):
        raise ValueError("G-0006 exact hinge columns are certified only for loopless pairs")
    if any(len(side) != 5 for side in pair):
        raise ValueError("G-0006 exact hinge columns require five edges per side")

    histogram = direction_histogram(pair)
    # Each loopless edge sends 2*r*(n-2)! permutations to rank r.  Every side
    # here contains exactly five edges, so the left-base symmetrization is
    # universal before lexicographic-orientation corrections.
    linear = [5 * 2 * rank * factorial(N - 2) for rank in range(N)]
    hinges: dict[Direction, int] = defaultdict(int)

    for raw_direction, multiplicity in histogram.items():
        if not any(raw_direction):
            continue
        magnitude = 0
        for value in raw_direction:
            magnitude = gcd(magnitude, abs(value))
        first = next(value for value in raw_direction if value)
        if first < 0:
            # max(0,-g*h) = -g*h + g*max(0,h).  The first term changes the
            # linear base when orienting the primitive direction positively.
            for rank, value in enumerate(raw_direction):
                linear[rank] += multiplicity * value
            primitive = tuple(-value // magnitude for value in raw_direction)
        else:
            primitive = tuple(value // magnitude for value in raw_direction)
        if not nonpositive_on_ordered_cone(primitive):
            hinges[primitive] += multiplicity * magnitude

    return HingeColumn(
        linear=tuple(linear),
        hinges=dict(hinges),
        raw_direction_count=len(histogram),
        permutation_count=sum(histogram.values()),
    )


def _column_worker(payload: tuple[int, Pair]) -> tuple[int, HingeColumn]:
    index, pair = payload
    return index, exact_hinge_column(pair)


def parsed_solution(path: Path) -> tuple[list[Pair], list[Fraction], dict[str, object]]:
    document = json.loads(path.read_text(encoding="utf-8"))
    if document.get("schema") != ORBIT_SOLUTION_SCHEMA or document.get("n") != N:
        raise ValueError(f"not a {ORBIT_SOLUTION_SCHEMA} document: {path}")
    pairs: list[Pair] = []
    coefficients: list[Fraction] = []
    for term in document["terms"]:
        sides = term["pair"]
        pair = tuple(tuple(tuple(map(int, edge)) for edge in side) for side in sides)
        if len(pair) != 2 or any(len(side) != 5 for side in pair):
            raise ValueError("solution term is not a 5-by-5 pair")
        pairs.append(pair)  # type: ignore[arg-type]
        coefficients.append(Fraction(term["coefficient"]))
    return pairs, coefficients, document


def complete_hinge_residual(solution_path: Path, workers: int) -> dict[str, object]:
    pairs, coefficients, solution = parsed_solution(solution_path)
    denominator_scale = 1
    for coefficient in coefficients:
        denominator_scale = lcm(denominator_scale, coefficient.denominator)
    integer_coefficients = [
        coefficient.numerator * (denominator_scale // coefficient.denominator)
        for coefficient in coefficients
    ]

    linear = [0] * N
    hinges: dict[Direction, int] = defaultdict(int)
    raw_direction_counts = [0] * len(pairs)
    permutation_counts = [0] * len(pairs)
    payloads = list(enumerate(pairs))
    with ProcessPoolExecutor(max_workers=workers) as executor:
        for index, column in executor.map(_column_worker, payloads, chunksize=1):
            coefficient = integer_coefficients[index]
            raw_direction_counts[index] = column.raw_direction_count
            permutation_counts[index] = column.permutation_count
            if not coefficient:
                continue
            for rank, value in enumerate(column.linear):
                linear[rank] += coefficient * value
            for direction, value in column.hinges.items():
                hinges[direction] += coefficient * value

    linear[-1] -= denominator_scale
    nonzero_hinges = sorted(
        (direction, value) for direction, value in hinges.items() if value
    )
    return {
        "schema": HINGE_RESIDUAL_SCHEMA,
        "n": N,
        "solution_file_sha256": sha256_path(solution_path),
        "term_count": len(pairs),
        "denominator_scale": str(denominator_scale),
        "linear_residual": [str(value) for value in linear],
        "nonzero_hinge_count": len(nonzero_hinges),
        "raw_direction_count_min": min(raw_direction_counts, default=0),
        "raw_direction_count_max": max(raw_direction_counts, default=0),
        "permutation_census_all_11_factorial": all(
            count == factorial(N) for count in permutation_counts
        ),
        "global_identity": not any(linear) and not nonzero_hinges,
        "hinges": [
            {"direction": list(direction), "coefficient": str(value)}
            for direction, value in nonzero_hinges
        ],
        "warning": (
            "A nonzero residual refutes only this finite-grid seed solution, not the full "
            "9804-class family."
        ),
        "source_grid_rank": solution["grid_rank"],
    }


def write_json(path: Path, document: object) -> None:
    payload = canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    print(f"{path} bytes={len(payload)} sha256={sha256_bytes(payload)}")


def write_json_gzip(path: Path, document: object) -> None:
    payload = canonical_json_bytes(document)
    path.parent.mkdir(parents=True, exist_ok=True)
    # mtime=0 makes the compressed evidence byte-reproducible.
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            compressed.write(payload)
    print(
        f"{path} uncompressed_bytes={len(payload)} compressed_bytes={path.stat().st_size} "
        f"sha256={sha256_path(path)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    classes_parser = subparsers.add_parser("classes")
    classes_parser.add_argument("--output", type=Path, required=True)

    orbit_parser = subparsers.add_parser("orbit-solve")
    orbit_parser.add_argument("--classes", type=Path, required=True)
    orbit_parser.add_argument("--orbit-directory", type=Path, required=True)
    orbit_parser.add_argument("--prime", type=int, default=1_000_003)
    orbit_parser.add_argument("--output", type=Path, required=True)

    residual_parser = subparsers.add_parser("hinge-residual")
    residual_parser.add_argument("--solution", type=Path, required=True)
    residual_parser.add_argument("--workers", type=int, default=8)
    residual_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    if args.command == "classes":
        write_json(args.output, build_isomorphism_classes())
    elif args.command == "orbit-solve":
        write_json(
            args.output,
            solve_orbit_grid(args.classes, args.orbit_directory, args.prime),
        )
    else:
        write_json_gzip(
            args.output, complete_hinge_residual(args.solution, args.workers)
        )


if __name__ == "__main__":
    main()
