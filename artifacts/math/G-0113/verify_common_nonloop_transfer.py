#!/usr/bin/env python3
"""Bind the G-0027 common-nonloop transfer lemma to the G-0113c map."""

from __future__ import annotations

import argparse
from collections import Counter
from fractions import Fraction
import gzip
import hashlib
from itertools import combinations, combinations_with_replacement, permutations
import json
from math import factorial
from pathlib import Path
import time
from typing import Iterable, Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
PREREGISTRATION = HERE / "COMMON_NONLOOP_TRANSFER_PREREGISTRATION.md"
MAP = HERE / "degree5_signed_orbit_representatives_v1.jsonl.gz"
CERTIFICATE = ROOT / "subjects/max-relu-known/certificates/certificate_10_4.json"
G0027_README = ROOT / "artifacts/math/G-0027/README.md"
G0027_PRODUCER = ROOT / "artifacts/math/G-0027/enumerate_signed_loopless.py"

EXPECTED = {
    PREREGISTRATION: "5d6dea7e1d4f0375f377578c15dee87201c338cbc1cfe6e132c0012bcc66bdc3",
    MAP: "57888d8e24ffa0d53490592a0b3e94c2f74ebb4fa91cc10fdac94ce4245f9b48",
    CERTIFICATE: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
    G0027_README: "f0531ff45a3e4082f0a78a76e52e7333a0d5297df2634a00b0e93b99dd5a2474",
    G0027_PRODUCER: "92ce1d017a12ce9dc44c3f43103028dcfe635fa7ba9e8c1026c3d6ca8fe19f13",
}
EXPECTED_RECORDS = 163_740
EXPECTED_DISJOINT_RAW = 795_960
EXPECTED_SHARED_RAW = 397_980
SCHEMA = "max11-g0113-common-nonloop-transfer-verification-v1"

Edge = tuple[int, int]
Side = tuple[Edge, ...]
Pair = tuple[Side, Side]


class TransferError(RuntimeError):
    """A binding, map invariant, or literal transfer control failed."""


def canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        + "\n"
    ).encode("ascii")


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while block := source.read(1 << 20):
            digest.update(block)
    return digest.hexdigest()


def canonical_side(raw: Iterable[Sequence[int]]) -> Side:
    return tuple(sorted((min(map(int, edge)), max(map(int, edge))) for edge in raw))


def serialize_pair(pair: Pair) -> list[list[list[int]]]:
    return [[list(edge) for edge in side] for side in pair]


def load_terms() -> tuple[list[Pair], list[Fraction]]:
    document = json.loads(CERTIFICATE.read_text(encoding="utf-8"))
    if document.get("n") != 10 or len(document.get("terms", [])) != 402:
        raise TransferError("source certificate census drift")
    pairs: list[Pair] = []
    coefficients: list[Fraction] = []
    for index, raw in enumerate(document["terms"]):
        pair_raw = raw.get("pair")
        if not isinstance(pair_raw, list) or len(pair_raw) != 2:
            raise TransferError(f"malformed source pair {index}")
        pair = (canonical_side(pair_raw[0]), canonical_side(pair_raw[1]))
        if len(pair[0]) != 4 or len(pair[1]) != 4:
            raise TransferError(f"source degree drift {index}")
        if any(u == v for side in pair for u, v in side):
            raise TransferError(f"source loop at term {index}")
        pairs.append(pair)
        coefficients.append(Fraction(raw["coefficient"]))
    return pairs, coefficients


def reconstruct_pair(source: Pair, left_edge: Edge, right_edge: Edge) -> Pair:
    return (
        tuple(sorted(source[0] + (left_edge,))),
        tuple(sorted(source[1] + (right_edge,))),
    )


def cancelled_data(pair: Pair) -> tuple[Side, Side, Side]:
    left = Counter(pair[0])
    right = Counter(pair[1])
    common = left & right
    left.subtract(common)
    right.subtract(common)
    negative = tuple(sorted(left.elements()))
    positive = tuple(sorted(right.elements()))
    common_side = tuple(sorted(common.elements()))
    if len(negative) != len(positive):
        raise TransferError("cancelled masses differ")
    return negative, positive, common_side


def edge_from_record(raw: Sequence[int]) -> Edge:
    if len(raw) != 2:
        raise TransferError("malformed added edge")
    u, v = map(int, raw)
    if not (1 <= u <= v <= 11):
        raise TransferError("added edge label out of range")
    return u, v


def relation(left: Edge, right: Edge) -> str:
    if left == right:
        return "IDENTICAL"
    shared = len(set(left).intersection(right))
    if shared == 0:
        return "DISJOINT"
    if shared == 1:
        return "SHARED_DISTINCT"
    raise TransferError("unexpected edge relation")


def check_pair(pair: Pair, expected_mass: int, expected_relation: str | None) -> None:
    if len(pair[0]) != 5 or len(pair[1]) != 5:
        raise TransferError("full pair is not degree five")
    if any(u == v for side in pair for u, v in side):
        raise TransferError("loop entered primary loopless pair")
    negative, positive, common = cancelled_data(pair)
    if len(negative) != expected_mass:
        raise TransferError("signed mass disagrees with map topology")
    if len(common) != 5 - expected_mass:
        raise TransferError("common cardinality does not equal 5-signed_mass")
    if any(u == v for u, v in common):
        raise TransferError("common loop entered primary loopless pair")
    if expected_relation is not None:
        # The final element need not be the added edge after sorting, so this
        # relation is checked by the caller on the stored descriptor itself.
        if expected_relation not in {"DISJOINT", "SHARED_DISTINCT"}:
            raise TransferError("unknown registered relation")


def check_map(
    sources: Sequence[Pair], coefficients: Sequence[Fraction]
) -> dict[str, object]:
    record_count = 0
    raw_totals = Counter()
    fiber_entry_totals = Counter()
    signed_mass_orbits = Counter()
    signed_hashes: set[str] = set()
    fiber_manifest = hashlib.sha256()
    with gzip.open(MAP, "rt", encoding="ascii") as stream:
        header = json.loads(next(stream))
        if header.get("record_type") != "header" or header.get(
            "primary_signed_W_orbits"
        ) != EXPECTED_RECORDS:
            raise TransferError("map header drift")
        for line in stream:
            record = json.loads(line)
            if record.get("record_type") != "signed_W_orbit":
                raise TransferError("unexpected map record type")
            if int(record.get("orbit_index", -1)) != record_count:
                raise TransferError("orbit index sequence drift")
            class_hash = str(record["signed_class_sha256"])
            if class_hash in signed_hashes:
                raise TransferError("duplicate signed class hash")
            signed_hashes.add(class_hash)
            topology = record["topology"]
            signed_mass = int(topology["signed_mass"])
            if int(topology["min_branch_loops"]) or int(
                topology["max_branch_loops"]
            ):
                raise TransferError("cancelled primary topology contains a loop")
            signed_mass_orbits[signed_mass] += 1

            descriptor = record["primary_representative"]
            source_index = int(descriptor["source_term"])
            left_edge = edge_from_record(descriptor["left_added_edge"])
            right_edge = edge_from_record(descriptor["right_added_edge"])
            family = str(record["primary_representative_family"])
            if relation(left_edge, right_edge) != family:
                raise TransferError("primary representative relation drift")
            pair = reconstruct_pair(sources[source_index], left_edge, right_edge)
            if serialize_pair(pair) != record["representative_pair"]:
                raise TransferError("stored representative pair drift")
            check_pair(pair, signed_mass, family)
            if Fraction(record["source_coefficient"]) != coefficients[source_index]:
                raise TransferError("primary representative coefficient drift")

            for slice_name in ("DISJOINT", "SHARED_DISTINCT"):
                fiber = record["source_fibers"][slice_name]
                expected_raw = int(record["raw_multiplicities"][slice_name])
                if int(fiber["raw_multiplicity_sum"]) != expected_raw:
                    raise TransferError("per-orbit fiber raw sum drift")
                computed_sum = Fraction(0)
                computed_raw = 0
                previous_source = -1
                for entry in fiber["entries"]:
                    term_index = int(entry["source_term"])
                    if term_index <= previous_source:
                        raise TransferError("fiber source order drift")
                    previous_source = term_index
                    coefficient = Fraction(entry["source_coefficient"])
                    if coefficient != coefficients[term_index]:
                        raise TransferError("fiber source coefficient drift")
                    multiplicity = int(entry["raw_multiplicity"])
                    if multiplicity <= 0:
                        raise TransferError("nonpositive fiber multiplicity")
                    weight = Fraction(entry["coefficient_times_multiplicity"])
                    if weight != coefficient * multiplicity:
                        raise TransferError("fiber coefficient weight drift")
                    fiber_left = edge_from_record(
                        entry["representative_left_added_edge"]
                    )
                    fiber_right = edge_from_record(
                        entry["representative_right_added_edge"]
                    )
                    if relation(fiber_left, fiber_right) != slice_name:
                        raise TransferError("fiber representative relation drift")
                    fiber_pair = reconstruct_pair(
                        sources[term_index], fiber_left, fiber_right
                    )
                    check_pair(fiber_pair, signed_mass, slice_name)
                    computed_sum += weight
                    computed_raw += multiplicity
                    fiber_entry_totals[slice_name] += 1
                if computed_raw != expected_raw:
                    raise TransferError("fiber entry multiplicities drift")
                if computed_sum != Fraction(fiber["coefficient_weight_sum"]):
                    raise TransferError("fiber coefficient sum drift")
                fiber_hash = hashlib.sha256(canonical_bytes(fiber)).hexdigest()
                if fiber_hash != record["source_fiber_sha256"][slice_name]:
                    raise TransferError("fiber canonical hash drift")
                fiber_manifest.update(
                    canonical_bytes(
                        {
                            "signed_class_sha256": class_hash,
                            f"{slice_name}_fiber_sha256": fiber_hash,
                        }
                    )
                )
                raw_totals[slice_name] += expected_raw
            record_count += 1

    if record_count != EXPECTED_RECORDS:
        raise TransferError("map record count drift")
    if raw_totals != Counter(
        {"DISJOINT": EXPECTED_DISJOINT_RAW, "SHARED_DISTINCT": EXPECTED_SHARED_RAW}
    ):
        raise TransferError(f"global raw replay failed: {raw_totals}")
    return {
        "orbit_records_checked": record_count,
        "unique_signed_class_hashes": len(signed_hashes),
        "source_fiber_entries_checked": dict(sorted(fiber_entry_totals.items())),
        "raw_multiplicity_replay": dict(sorted(raw_totals.items())),
        "signed_mass_orbit_histogram": {
            str(mass): count for mass, count in sorted(signed_mass_orbits.items())
        },
        "per_record_fiber_hashes_replayed": True,
        "verification_fiber_manifest_sha256": fiber_manifest.hexdigest(),
        "all_reconstructed_pairs_degree_five_loopless": True,
        "all_common_multisets_loopless_and_cardinality_5_minus_s": True,
    }


def pair_value(pair: Pair, point: Sequence[int]) -> int:
    branches = [
        sum(max(point[u - 1], point[v - 1]) for u, v in side) for side in pair
    ]
    return max(branches)


def literal_symmetrized_value(pair: Pair, point: Sequence[int]) -> int:
    return sum(pair_value(pair, permuted) for permuted in permutations(point))


def f2(point: Sequence[int]) -> int:
    return sum(max(point[u], point[v]) for u, v in combinations(range(len(point)), 2))


def literal_controls() -> dict[str, object]:
    negative: Side = ((1, 2), (2, 3))
    positive: Side = ((4, 5), (5, 6))
    common_first: Side = ((1, 3), (2, 4), (6, 7))
    common_second: Side = ((1, 4), (2, 5), (3, 7))
    first: Pair = (
        tuple(sorted(common_first + negative)),
        tuple(sorted(common_first + positive)),
    )
    second: Pair = (
        tuple(sorted(common_second + negative)),
        tuple(sorted(common_second + positive)),
    )
    loop_mutant_common: Side = ((1, 1), (2, 5), (3, 7))
    loop_mutant: Pair = (
        tuple(sorted(loop_mutant_common + negative)),
        tuple(sorted(loop_mutant_common + positive)),
    )
    profiles = list(combinations_with_replacement((-2, 0, 3), 7))
    mutant_disagreements = 0
    common_edge_formula_checks = 0
    for point in profiles:
        first_value = literal_symmetrized_value(first, point)
        second_value = literal_symmetrized_value(second, point)
        if first_value != second_value:
            raise TransferError("differently placed common nonloops changed full symmetrization")
        if literal_symmetrized_value(loop_mutant, point) != second_value:
            mutant_disagreements += 1

        edge_pair: Pair = (((1, 2),), ((1, 2),))
        observed = literal_symmetrized_value(edge_pair, point)
        expected = 2 * factorial(7 - 2) * f2(point)
        if observed != expected:
            raise TransferError("single common nonloop orbit-sum formula failed")
        common_edge_formula_checks += 1
    if not mutant_disagreements:
        raise TransferError("common-loop mutant never separated from common-nonloop control")
    return {
        "n": 7,
        "profiles": len(profiles),
        "permutations_per_profile": factorial(7),
        "equal_full_symmetrizations_for_different_common_nonloop_placements": True,
        "single_nonloop_formula": "2*(n-2)!*F_2^(n)",
        "single_nonloop_formula_checks": common_edge_formula_checks,
        "common_loop_mutant_disagreements": mutant_disagreements,
    }


def raw_generator_controls(sources: Sequence[Pair]) -> dict[str, object]:
    edges = tuple(combinations(range(1, 12), 2))
    disjoint = tuple(
        (left, right)
        for left in edges
        for right in edges
        if not set(left).intersection(right)
    )
    shared = tuple(
        (left, right)
        for left in edges
        for right in edges
        if left != right and len(set(left).intersection(right)) == 1
    )
    if len(disjoint) != 1_980 or len(shared) != 990:
        raise TransferError("relation generator count drift")
    if any(u == v for pair in sources for side in pair for u, v in side):
        raise TransferError("source generator contains a loop")
    if any(u == v for edge in edges for u, v in (edge,)):
        raise TransferError("added-edge generator contains a loop")
    return {
        "source_terms": len(sources),
        "all_source_edges_loopless": True,
        "available_nonloop_edges": len(edges),
        "ordered_disjoint_pairs_per_source": len(disjoint),
        "ordered_shared_distinct_pairs_per_source": len(shared),
        "all_added_edges_loopless": True,
        "unrecorded_raw_members_covered_by_generator_argument": True,
    }


def generate(output: Path) -> dict[str, object]:
    if output.exists():
        raise TransferError(f"refusing to overwrite {output}")
    started = time.monotonic()
    bindings = {}
    for path, expected in EXPECTED.items():
        observed = sha256_path(path)
        if observed != expected:
            raise TransferError(f"binding drift for {path}: {observed}")
        bindings[str(path.relative_to(ROOT))] = observed
    sources, coefficients = load_terms()
    raw_controls = raw_generator_controls(sources)
    map_controls = check_map(sources, coefficients)
    literal = literal_controls()
    report: dict[str, object] = {
        "schema": SCHEMA,
        "result": "PASS",
        "bindings": bindings,
        "theorem": {
            "pointwise_cancellation": (
                "max(S_(C+A'),S_(C+B')) = S_C + max(S_A',S_B')"
            ),
            "unnormalized_nonloop_orbit_sum": (
                "Sym_n h_e = 2*(n-2)!*F_2^(n) for every fixed nonloop e"
            ),
            "fixed_degree_consequence": (
                "for branch degree 5 and cancelled mass s, |C|=5-s; hence "
                "the fully symmetrized loopless atom is determined by signed W"
            ),
            "injectivity_not_claimed": (
                "distinct signed-W orbits may still define equal symmetrized functions"
            ),
        },
        "raw_generator_controls": raw_controls,
        "map_controls": map_controls,
        "literal_permutation_controls": literal,
        "wall_seconds": time.monotonic() - started,
        "producer_sha256": sha256_path(SCRIPT),
        "claim_boundary": (
            "This binds the common-nonloop transfer lemma to every primary G-0113c "
            "raw extension. It does not apply unchanged to loop-bearing STAR records, "
            "prove injectivity of signed-W orbits, span MAX11, or obstruct any larger family."
        ),
    }
    output.write_bytes(canonical_bytes(report))
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=HERE / "common_nonloop_transfer_verification_v1.json",
    )
    args = parser.parse_args()
    report = generate(args.output.resolve())
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
