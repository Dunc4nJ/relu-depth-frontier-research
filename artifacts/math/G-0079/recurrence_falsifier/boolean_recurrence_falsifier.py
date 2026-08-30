#!/usr/bin/env python3
"""Exact Boolean-layer falsifier for simple MAX10 -> MAX11 Y-spoke recurrences.

This program is deliberately separate from the registered G-0079 producer.  It
tests only coefficient rules inherited from the public MAX10 certificate.  It
does not price the new columns under the G-0078 dual and does not test arbitrary
coefficients in the 26,686-orbit cross+same Y-spoke family.

For every eligible two-component MAX10 forest term, every ordered k != l, and
both outer orientations, define

    Y = max(2*x_k, x_l + x_11),
    phi_0 = max(A + 2*x_k, B + Y),
    phi_1 = max(A + Y, B + 2*x_k).

Each raw seed is fully S_11-averaged and initially receives its source MAX10
coefficient.  The exact eleven Boolean Hamming layers then reject three nested
recurrence ansatzes, even after adjoining the existing C_L, C_E, and C_Y
carriers.  Exact integer row duals are emitted for independent replay.
"""

from __future__ import annotations

import argparse
from collections import Counter
from dataclasses import dataclass
from fractions import Fraction
from functools import reduce
import hashlib
import json
from math import comb, gcd, lcm
from pathlib import Path
import platform
from typing import Iterable, Sequence

import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
SCRIPT = Path(__file__).resolve()
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"

SCHEMA = "max11-g0079-boolean-recurrence-falsifier-v1"
EXPECTED_CERTIFICATE_SHA256 = (
    "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4"
)
OLD_N = 10
N = 11
EXPECTED_BASES = 252
EXPECTED_TOPOLOGY = {(2, 8): 168, (3, 7): 39, (4, 6): 32, (5, 5): 13}
EXPECTED_CROSS_SEEDS = 18_400
EXPECTED_SAME_SEEDS = 26_960
EXPECTED_ALL_SEEDS = 45_360
PRIMES = (1_000_003, 1_000_033, 1_000_037)

Edge = tuple[int, int]
Side = tuple[Edge, ...]


class FalsifierError(RuntimeError):
    """A bound input, exact identity, census, or certificate check failed."""


@dataclass(frozen=True)
class Base:
    position: int
    term_index: int
    coefficient: Fraction
    left: Side
    right: Side
    components: tuple[tuple[int, ...], tuple[int, ...]]

    @property
    def topology(self) -> tuple[int, int]:
        return tuple(sorted(map(len, self.components)))  # type: ignore[return-value]


def canonical_bytes(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def canonical_sha256(value: object) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def fraction_text(value: Fraction) -> str:
    return str(value.numerator) if value.denominator == 1 else str(value)


def canonical_side(raw: Iterable[Iterable[int]]) -> Side:
    return tuple(sorted(tuple(sorted(map(int, edge))) for edge in raw))  # type: ignore[return-value]


def forest_components(left: Side, right: Side) -> tuple[tuple[int, ...], tuple[int, ...]] | None:
    edges = left + right
    if any(a == b for a, b in edges) or len(set(edges)) != OLD_N - 2:
        return None
    if {vertex for edge in edges for vertex in edge} != set(range(1, OLD_N + 1)):
        return None
    parent = list(range(OLD_N + 1))

    def find(vertex: int) -> int:
        while parent[vertex] != vertex:
            parent[vertex] = parent[parent[vertex]]
            vertex = parent[vertex]
        return vertex

    for first, second in edges:
        first_root, second_root = find(first), find(second)
        if first_root == second_root:
            return None
        parent[second_root] = first_root
    groups: dict[int, list[int]] = {}
    for vertex in range(1, OLD_N + 1):
        groups.setdefault(find(vertex), []).append(vertex)
    components = tuple(sorted(tuple(group) for group in groups.values()))
    if len(components) != 2:
        return None
    return components  # type: ignore[return-value]


def load_bases() -> tuple[list[Base], list[dict[str, object]]]:
    if sha256_path(CERTIFICATE) != EXPECTED_CERTIFICATE_SHA256:
        raise FalsifierError("MAX10 certificate digest drift")
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    terms = document.get("terms")
    if document.get("n") != OLD_N or not isinstance(terms, list):
        raise FalsifierError("malformed MAX10 certificate")
    bases: list[Base] = []
    manifest: list[dict[str, object]] = []
    for term_index, term in enumerate(terms):
        pair = term.get("pair")
        if not isinstance(pair, list) or len(pair) != 2:
            raise FalsifierError(f"malformed pair at term {term_index}")
        left, right = (canonical_side(side) for side in pair)
        if len(left) != 4 or len(right) != 4:
            continue
        components = forest_components(left, right)
        if components is None:
            continue
        coefficient = Fraction(str(term.get("coefficient")))
        if coefficient == 0:
            raise FalsifierError("eligible source term has zero coefficient")
        base = Base(len(bases), term_index, coefficient, left, right, components)
        bases.append(base)
        manifest.append(
            {
                "position": base.position,
                "term_index": term_index,
                "coefficient": fraction_text(coefficient),
                "left": [list(edge) for edge in left],
                "right": [list(edge) for edge in right],
                "components": [list(component) for component in components],
                "topology": list(base.topology),
            }
        )
    topology = Counter(base.topology for base in bases)
    if len(bases) != EXPECTED_BASES or dict(topology) != EXPECTED_TOPOLOGY:
        raise FalsifierError(f"eligible-base census drift: {len(bases)}, {topology}")
    return bases, manifest


def boolean_data() -> tuple[np.ndarray, np.ndarray]:
    masks = np.arange(1 << N, dtype=np.uint16)
    levels = np.asarray([((masks >> vertex) & 1) for vertex in range(N)], dtype=np.int16)
    hamming = np.asarray([int(mask).bit_count() for mask in masks], dtype=np.int8)
    return levels, hamming


def evaluate_arm(
    base: Base,
    pairs: Sequence[tuple[int, int]],
    orientation: int,
    levels: np.ndarray,
) -> np.ndarray:
    if orientation not in (0, 1):
        raise FalsifierError("orientation outside {0,1}")
    left = np.zeros(levels.shape[1], dtype=np.int16)
    right = np.zeros(levels.shape[1], dtype=np.int16)
    for first, second in base.left:
        left += np.maximum(levels[first - 1], levels[second - 1])
    for first, second in base.right:
        right += np.maximum(levels[first - 1], levels[second - 1])
    anchors = np.asarray([anchor - 1 for anchor, _auxiliary in pairs], dtype=np.intp)
    auxiliaries = np.asarray([auxiliary - 1 for _anchor, auxiliary in pairs], dtype=np.intp)
    simple = 2 * levels[anchors]
    leaf_sum = levels[auxiliaries] + levels[N - 1]
    common = np.maximum(left, right)[None, :] + simple
    branch_tail = (
        right[None, :] + leaf_sum if orientation == 0 else left[None, :] + leaf_sum
    )
    return np.maximum(common, branch_tail).sum(axis=0, dtype=np.int64)


def rref(matrix: Sequence[Sequence[Fraction]]) -> tuple[list[list[Fraction]], list[int]]:
    rows = [list(map(Fraction, row)) for row in matrix]
    if not rows:
        return rows, []
    columns = len(rows[0])
    if any(len(row) != columns for row in rows):
        raise FalsifierError("ragged exact matrix")
    pivots: list[int] = []
    pivot_row = 0
    for column in range(columns):
        selected = next(
            (row for row in range(pivot_row, len(rows)) if rows[row][column]), None
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        scale = rows[pivot_row][column]
        rows[pivot_row] = [value / scale for value in rows[pivot_row]]
        for row in range(len(rows)):
            if row == pivot_row or not rows[row][column]:
                continue
            coefficient = rows[row][column]
            rows[row] = [
                value - coefficient * pivot
                for value, pivot in zip(rows[row], rows[pivot_row], strict=True)
            ]
        pivots.append(column)
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return rows, pivots


def exact_rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    return len(rref(matrix)[1])


def primitive_integer_vector(values: Sequence[Fraction]) -> list[int]:
    denominator = reduce(lcm, (value.denominator for value in values), 1)
    integers = [value.numerator * (denominator // value.denominator) for value in values]
    common = reduce(gcd, (abs(value) for value in integers), 0) or 1
    integers = [value // common for value in integers]
    first = next((value for value in integers if value), 1)
    return [-value for value in integers] if first < 0 else integers


def exact_left_dual(
    matrix: Sequence[Sequence[Fraction]], target: Sequence[Fraction]
) -> dict[str, object]:
    rows = len(matrix)
    columns = len(matrix[0]) if rows else 0
    transpose = [[matrix[row][column] for row in range(rows)] for column in range(columns)]
    reduced, pivots = rref(transpose)
    free = [column for column in range(rows) if column not in set(pivots)]
    for free_column in free:
        candidate = [Fraction(0) for _ in range(rows)]
        candidate[free_column] = 1
        for row, pivot in enumerate(pivots):
            candidate[pivot] = -reduced[row][free_column]
        pairing = sum(
            coefficient * value for coefficient, value in zip(candidate, target, strict=True)
        )
        if pairing:
            integers = primitive_integer_vector(candidate)
            integer_pairing = sum(
                coefficient * value
                for coefficient, value in zip(integers, target, strict=True)
            )
            if any(
                sum(integers[row] * matrix[row][column] for row in range(rows))
                for column in range(columns)
            ):
                raise FalsifierError("emitted Boolean row dual does not annihilate its matrix")
            if not integer_pairing.denominator == 1 or not integer_pairing:
                raise FalsifierError("emitted Boolean row dual lost target pairing")
            return {
                "hamming_layers": list(range(1, N + 1)),
                "primitive_integer_weights": integers,
                "target_pairing": int(integer_pairing),
                "annihilates_every_ansatz_column_exactly": True,
            }
    raise FalsifierError("nonmember rank gap did not yield an exact target-bearing row dual")


def modular_rank(matrix: Sequence[Sequence[Fraction]], prime: int) -> int:
    rows = [
        [value.numerator * pow(value.denominator, -1, prime) % prime for value in row]
        for row in matrix
    ]
    if not rows:
        return 0
    pivot_row = 0
    for column in range(len(rows[0])):
        selected = next(
            (row for row in range(pivot_row, len(rows)) if rows[row][column] % prime),
            None,
        )
        if selected is None:
            continue
        rows[pivot_row], rows[selected] = rows[selected], rows[pivot_row]
        inverse = pow(rows[pivot_row][column] % prime, -1, prime)
        rows[pivot_row] = [(value * inverse) % prime for value in rows[pivot_row]]
        for row in range(len(rows)):
            coefficient = rows[row][column] % prime
            if row == pivot_row or not coefficient:
                continue
            rows[row] = [
                (value - coefficient * pivot) % prime
                for value, pivot in zip(rows[row], rows[pivot_row], strict=True)
            ]
        pivot_row += 1
        if pivot_row == len(rows):
            break
    return pivot_row


def canonical_solution(
    matrix: Sequence[Sequence[Fraction]], target: Sequence[Fraction]
) -> list[Fraction] | None:
    augmented = [list(row) + [target[index]] for index, row in enumerate(matrix)]
    reduced, pivots = rref(augmented)
    variables = len(matrix[0])
    if variables in pivots:
        return None
    solution = [Fraction(0) for _ in range(variables)]
    for row, pivot in enumerate(pivots):
        if pivot < variables:
            solution[pivot] = reduced[row][variables]
    replay = [
        sum(value * coefficient for value, coefficient in zip(row, solution, strict=True))
        for row in matrix
    ]
    if replay != list(target):
        raise FalsifierError("canonical exact member solution failed replay")
    return solution


def analyze_ansatz(
    name: str,
    column_names: Sequence[str],
    values: dict[str, list[Fraction]],
    target: Sequence[Fraction],
) -> dict[str, object]:
    matrix = [[values[column][layer] for column in column_names] for layer in range(1, N + 1)]
    augmented = [row + [target[index]] for index, row in enumerate(matrix)]
    rank = exact_rank(matrix)
    augmented_rank = exact_rank(augmented)
    modular = {
        str(prime): {
            "rank": modular_rank(matrix, prime),
            "augmented_rank": modular_rank(augmented, prime),
        }
        for prime in PRIMES
    }
    record: dict[str, object] = {
        "name": name,
        "coefficient_field": "Q",
        "rows": N,
        "columns": len(column_names),
        "column_order": list(column_names),
        "rank": rank,
        "augmented_rank": augmented_rank,
        "target_in_span": rank == augmented_rank,
        "modular_cross_checks": modular,
    }
    if rank != augmented_rank:
        if augmented_rank != rank + 1:
            raise FalsifierError("target rank gap is not one")
        record["exact_row_dual"] = exact_left_dual(matrix, target)
        record["canonical_basic_solution"] = None
    else:
        solution = canonical_solution(matrix, target)
        if solution is None:
            raise FalsifierError("equal ranks produced no exact member solution")
        sparse = [
            {"column": column_names[index], "coefficient": fraction_text(value)}
            for index, value in enumerate(solution)
            if value
        ]
        record["exact_row_dual"] = None
        record["canonical_basic_solution"] = {
            "support_size": len(sparse),
            "sparse_coefficients": sparse,
            "all_eleven_layers_replay_exactly": True,
        }
    return record


def analytic_identity_controls() -> dict[str, object]:
    checks = 0
    for u in range(-9, 10):
        for raw_d in range(-9, 10):
            r = max(0, raw_d)
            phi_zero = max(u, r)
            phi_one = max(u + r, 0)
            expected_sum = 2 * max(u, 0) + r + max(0, r - abs(u))
            expected_difference = -max(-r, min(u, r))
            if phi_zero + phi_one != expected_sum:
                raise FalsifierError("orientation-sum identity failed")
            if phi_zero - phi_one != expected_difference:
                raise FalsifierError("orientation-difference identity failed")
            checks += 1
    return {
        "integer_pair_checks": checks,
        "definitions": [
            "u=A-B",
            "r=ReLU(x_l+x_11-2*x_k)",
        ],
        "orientation_sum_identity": (
            "phi_0+phi_1 = 2*max(A,B)+4*x_k+r+ReLU(r-|A-B|)"
        ),
        "orientation_difference_identity": (
            "phi_0-phi_1 = -clip(A-B,-r,r)"
        ),
        "interpretation": (
            "equal-orientation inheritance requires cancellation of thresholded branch-gap "
            "terms ReLU(r-|A-B|), which is not implied by the MAX10 identity's ordinary "
            "hinge cancellation"
        ),
    }


def build_report() -> dict[str, object]:
    bases, base_manifest = load_bases()
    levels, hamming = boolean_data()
    topology_labels = ["2+8", "3+7", "4+6", "5+5"]
    orientation_names = [
        f"{relation}_{topology}_o{orientation}"
        for relation in ("cross", "same")
        for topology in topology_labels
        for orientation in (0, 1)
    ]
    values: dict[str, list[Fraction]] = {
        name: [Fraction(0) for _ in range(N + 1)] for name in orientation_names
    }
    seed_manifest: list[dict[str, object]] = []
    raw_counts = Counter()

    for base in bases:
        component_of = {
            vertex: component_index
            for component_index, component in enumerate(base.components)
            for vertex in component
        }
        topology = f"{base.topology[0]}+{base.topology[1]}"
        for relation in ("cross", "same"):
            pairs = [
                (anchor, auxiliary)
                for anchor in range(1, OLD_N + 1)
                for auxiliary in range(1, OLD_N + 1)
                if anchor != auxiliary
                and (component_of[anchor] == component_of[auxiliary])
                == (relation == "same")
            ]
            for orientation in (0, 1):
                name = f"{relation}_{topology}_o{orientation}"
                arm = evaluate_arm(base, pairs, orientation, levels)
                raw_counts[relation] += len(pairs)
                for anchor, auxiliary in pairs:
                    seed_manifest.append(
                        {
                            "base_position": base.position,
                            "base_term_index": base.term_index,
                            "anchor": anchor,
                            "auxiliary": auxiliary,
                            "orientation": orientation,
                            "relation": relation,
                            "topology": topology,
                        }
                    )
                for layer in range(1, N + 1):
                    subtotal = int(arm[hamming == layer].sum(dtype=np.int64))
                    values[name][layer] += (
                        base.coefficient * subtotal / Fraction(comb(N, layer))
                    )

    if (
        raw_counts["cross"] != EXPECTED_CROSS_SEEDS
        or raw_counts["same"] != EXPECTED_SAME_SEEDS
        or len(seed_manifest) != EXPECTED_ALL_SEEDS
    ):
        raise FalsifierError(f"raw seed census drift: {raw_counts}, {len(seed_manifest)}")

    equal_orientation_names: list[str] = []
    for relation in ("cross", "same"):
        for topology in topology_labels:
            name = f"{relation}_{topology}"
            equal_orientation_names.append(name)
            values[name] = [
                values[f"{relation}_{topology}_o0"][layer]
                + values[f"{relation}_{topology}_o1"][layer]
                for layer in range(N + 1)
            ]
    for relation in ("cross", "same"):
        values[relation] = [
            sum(
                (values[f"{relation}_{topology}"][layer] for topology in topology_labels),
                Fraction(0),
            )
            for layer in range(N + 1)
        ]
    values["uniform_all"] = [
        values["cross"][layer] + values["same"][layer]
        for layer in range(N + 1)
    ]

    carriers = {
        "C_L": levels[0],
        "C_E": np.maximum(levels[0], levels[1]),
        "C_Y": np.maximum(2 * levels[0], levels[1] + levels[2]),
    }
    for name, column in carriers.items():
        values[name] = [Fraction(0) for _ in range(N + 1)]
        for layer in range(1, N + 1):
            values[name][layer] = Fraction(
                int(column[hamming == layer].sum(dtype=np.int64)), comb(N, layer)
            )
    target = [Fraction(0)] + [Fraction(1) for _ in range(N)]

    ansatzes = [
        analyze_ansatz(
            "one inherited scalar for all cross+same spokes",
            ["uniform_all", "C_L", "C_E", "C_Y"],
            values,
            target[1:],
        ),
        analyze_ansatz(
            "independent inherited scalars for cross and same spokes",
            ["cross", "same", "C_L", "C_E", "C_Y"],
            values,
            target[1:],
        ),
        analyze_ansatz(
            "independent inherited scalars by relation and component topology; orientations equal",
            [*equal_orientation_names, "C_L", "C_E", "C_Y"],
            values,
            target[1:],
        ),
        analyze_ansatz(
            "boundary control: independent inherited scalars by relation, topology, and orientation",
            [*orientation_names, "C_L", "C_E", "C_Y"],
            values,
            target[1:],
        ),
    ]
    expected_rank_pairs = [(3, 4), (4, 5), (10, 11), (11, 11)]
    observed_rank_pairs = [
        (int(record["rank"]), int(record["augmented_rank"])) for record in ansatzes
    ]
    if observed_rank_pairs != expected_rank_pairs:
        raise FalsifierError(
            f"frozen Boolean ansatz ranks drift: {observed_rank_pairs} != {expected_rank_pairs}"
        )

    layer_values = {
        name: [fraction_text(values[name][layer]) for layer in range(1, N + 1)]
        for name in [
            "uniform_all",
            "cross",
            "same",
            *equal_orientation_names,
            *orientation_names,
            "C_L",
            "C_E",
            "C_Y",
        ]
    }
    controls = analytic_identity_controls()
    science = {
        "schema": SCHEMA,
        "input": {
            "certificate_path": str(CERTIFICATE.relative_to(ROOT)),
            "certificate_sha256": EXPECTED_CERTIFICATE_SHA256,
            "certificate_terms": 402,
        },
        "family": {
            "eligible_base_definition": (
                "two sides of four distinct nonloop edges whose eight-edge union is a "
                "full-support two-component forest on labels 1..10"
            ),
            "eligible_bases": len(bases),
            "component_topology": {
                f"{first}+{second}": count
                for (first, second), count in sorted(EXPECTED_TOPOLOGY.items())
            },
            "base_manifest_sha256": canonical_sha256(base_manifest),
            "raw_seed_definition": (
                "for each eligible base, every ordered distinct k,l in 1..10 and both "
                "outer orientations; each seed is S_11-averaged and weighted by its "
                "source MAX10 coefficient before ansatz multipliers"
            ),
            "cross_raw_seeds": raw_counts["cross"],
            "same_raw_seeds": raw_counts["same"],
            "all_raw_seeds": len(seed_manifest),
            "raw_seed_manifest_sha256": canonical_sha256(seed_manifest),
        },
        "boolean_subject": {
            "hamming_layers": list(range(1, N + 1)),
            "normalization": (
                "at layer h, average each labelled seed over all binom(11,h) Boolean masks; "
                "this equals its full S_11 average at any Boolean point of weight h"
            ),
            "target_values": ["1"] * N,
            "carrier_columns": ["C_L", "C_E", "C_Y"],
            "layer_values": layer_values,
            "layer_values_sha256": canonical_sha256(layer_values),
        },
        "analytic_structure": controls,
        "exact_results": ansatzes,
        "decision": (
            "The uniform, relation-split, and relation-by-topology equal-orientation "
            "inheritance rules are exactly incompatible with MAX11 already on the eleven "
            "Boolean Hamming layers, even with C_L/C_E/C_Y. Orientation-specific arms can "
            "interpolate these eleven layers, so the test does not reject richer recurrences."
        ),
        "claim_boundary": (
            "This rejects only the displayed source-MAX10-coefficient recurrence ansatzes. "
            "It does not reject arbitrary coefficients in the 26,686 Y-spoke orbits, does "
            "not inspect the registered G-0078 prices, and proves no finite-full-row or "
            "global MAX11 construction/impossibility statement."
        ),
    }
    return {
        **science,
        "scientific_payload_sha256": canonical_sha256(science),
        "script_sha256": sha256_path(SCRIPT),
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "platform": platform.platform(),
        },
    }


def run_self_test() -> dict[str, object]:
    identity = analytic_identity_controls()
    member = [[Fraction(1)], [Fraction(2)]]
    nonmember = [[Fraction(1)], [Fraction(0)]]
    if exact_rank(member) != exact_rank([row + [rhs] for row, rhs in zip(member, [3, 6])]):
        raise FalsifierError("exact member fixture failed")
    if exact_rank(nonmember) + 1 != exact_rank(
        [row + [rhs] for row, rhs in zip(nonmember, [0, 1])]
    ):
        raise FalsifierError("exact nonmember fixture failed")
    return {
        "schema": f"{SCHEMA}-self-test",
        "analytic_identity_controls": identity,
        "exact_member_and_nonmember_rank_fixtures": True,
        "result": "PASS",
    }


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", type=Path)
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    arguments = parse_arguments()
    if arguments.self_test:
        print(json.dumps(run_self_test(), sort_keys=True))
        return 0
    report = build_report()
    if arguments.check is not None:
        frozen = json.loads(arguments.check.read_text(encoding="utf-8"))
        if frozen != report:
            raise FalsifierError("frozen Boolean recurrence artifact differs from replay")
        print(
            json.dumps(
                {
                    "artifact_sha256": sha256_path(arguments.check),
                    "scientific_payload_sha256": report["scientific_payload_sha256"],
                    "result": "BYTE_SEMANTICS_REPLAY_PASS",
                },
                sort_keys=True,
            )
        )
        return 0
    if not arguments.run or arguments.output is None:
        raise FalsifierError("--run requires --output")
    if arguments.output.exists():
        raise FileExistsError(f"refusing to overwrite {arguments.output}")
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_bytes(canonical_bytes(report))
    print(
        json.dumps(
            {
                "artifact": str(arguments.output),
                "artifact_sha256": sha256_path(arguments.output),
                "scientific_payload_sha256": report["scientific_payload_sha256"],
                "rank_pairs": [
                    [record["rank"], record["augmented_rank"]]
                    for record in report["exact_results"]
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
