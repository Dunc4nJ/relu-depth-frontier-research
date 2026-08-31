#!/usr/bin/env python3
"""Exact rank-cap gate for preregistered source-local G-0115 operators."""

from __future__ import annotations

import argparse
from collections import defaultdict
from fractions import Fraction
import hashlib
from itertools import combinations_with_replacement
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Mapping, Sequence

from flint import fmpq_mat, fmpz_mat
import numpy as np


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
sys.path.insert(0, str(HERE))
import parity_lift_census as census  # noqa: E402
import semantic_repair as kernel  # noqa: E402
import transport_support_probe as support  # noqa: E402


CERT8 = ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json"
MAP = HERE / "parity_lift_representatives_v1.jsonl.gz"
MATRIX = HERE / "unrestricted_full_semantic_matrix_v1.npy"
MATRIX_META = HERE / "unrestricted_full_semantic_matrix_v1.json"
SUPPORT_REPORT = HERE / "transport_support_probe_v1.json"
PREREG = HERE / "TRANSPORT_LAW_PREREGISTRATION.md"
ADDENDUM = HERE / "TRANSPORT_LAW_CONTROL_ADDENDUM.md"
EXPECTED = {
    CERT8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    MAP: "2fa23b8346858e85b4689a36c795ddac6d109ff42535d2238502b3c64117a148",
    MATRIX: "f1a4f7fb1a449d2f1ef8a41fc948c1fb893039ae3f8d432b691d4ae1cfbdff1e",
    MATRIX_META: "8e4f59489d2eb87813f2020f60e5f61ca8caef6f3d2b5b30941b14fd3a8d569b",
    SUPPORT_REPORT: "fedbbc7e845d8af20cfb0f6f71814f149193486234e5ec26535da3f67806be56",
    PREREG: "1c276c26e16227fb0cef37910363a2db7364db24d2b8586a4c185ae07c531e49",
    ADDENDUM: "a6472ae3aa0d146ac42d8479ef3b06a50b3ca0ceaf4dedb3896e4df93f223439",
    HERE / "parity_lift_census.py": "4ea2109ada7a30faaea224f3c0e7da46ccccfb6ca0c8bbaf70746c97b1d6ab1a",
    HERE / "semantic_repair.py": "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    HERE / "transport_support_probe.py": "4e27a4c11fe4fa66708b8b1d59771c8902a4747329c5fcc6cb63fe59a66628ba",
}
N = 9
HINGES = 20_685
CLASSES = 22_666
CAP = 64
WITNESS = CAP + 1
PRIME = 1_000_003


class RankGateError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RankGateError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def atomic_json(path: Path, value: object) -> None:
    require(not path.exists(), f"output exists: {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(value))
        destination.flush()
        os.fsync(destination.fileno())


def class_hash(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def modular_pivots(matrix: np.ndarray, prime: int, limit: int) -> tuple[list[int], list[int]]:
    work = np.remainder(matrix, prime).astype(np.int64, copy=True)
    row_ids = np.arange(work.shape[0], dtype=np.int64)
    pivot_columns: list[int] = []
    rank = 0
    for column in range(work.shape[1]):
        candidates = np.flatnonzero(work[rank:, column])
        if not len(candidates):
            continue
        pivot = rank + int(candidates[0])
        if pivot != rank:
            work[[rank, pivot]] = work[[pivot, rank]]
            row_ids[[rank, pivot]] = row_ids[[pivot, rank]]
        inverse = pow(int(work[rank, column]), prime - 2, prime)
        work[rank, column:] = np.remainder(work[rank, column:] * inverse, prime)
        if rank + 1 < work.shape[0]:
            factors = work[rank + 1 :, column].copy()
            nonzero = np.flatnonzero(factors)
            if len(nonzero):
                target_rows = rank + 1 + nonzero
                update = factors[nonzero, None] * work[rank, column:][None, :]
                work[target_rows, column:] = np.remainder(
                    work[target_rows, column:] - update,
                    prime,
                )
        pivot_columns.append(column)
        rank += 1
        if rank == limit:
            break
    return list(map(int, row_ids[:rank])), pivot_columns


def fraction_matrix_rank(matrix: Sequence[Sequence[Fraction]]) -> int:
    return int(fmpq_mat([[str(value) for value in row] for row in matrix]).rank())


def convention_witness(
    convention: str,
    signatures: Sequence[str],
    signature_pairs: Mapping[str, Mapping[str, int]],
    pair_signed: Mapping[str, int],
    pair_multiplicity: Mapping[str, int],
    semantic_matrix: np.ndarray,
    sampled_hinges: Sequence[int],
) -> dict[str, object]:
    modular = np.zeros((len(signatures), len(sampled_hinges)), dtype=np.int64)
    exact_rows: dict[int, list[Fraction]] = {}
    for signature_index, signature in enumerate(signatures):
        output = np.zeros(len(sampled_hinges), dtype=np.int64)
        for pair_id, integer_weight in signature_pairs[signature].items():
            signed_index = pair_signed[pair_id]
            row = semantic_matrix[signed_index, sampled_hinges].astype(np.int64, copy=False)
            if convention == "raw_sum":
                scale = integer_weight % PRIME
            else:
                require(convention == "full_atom_average", f"unknown convention: {convention}")
                scale = integer_weight * pow(pair_multiplicity[pair_id], PRIME - 2, PRIME) % PRIME
            output = np.remainder(output + scale * row, PRIME)
        modular[signature_index] = output
    pivot_rows, pivot_columns = modular_pivots(modular, PRIME, WITNESS)
    require(len(pivot_rows) == WITNESS, f"{convention}: did not exceed cap on sampled hinges")
    chosen_signatures = [signatures[index] for index in pivot_rows]
    chosen_hinges = [sampled_hinges[index] for index in pivot_columns]
    exact_minor: list[list[Fraction]] = []
    for signature_index in pivot_rows:
        signature = signatures[signature_index]
        row_values = [Fraction() for _ in chosen_hinges]
        for pair_id, integer_weight in signature_pairs[signature].items():
            signed_index = pair_signed[pair_id]
            denominator = 1 if convention == "raw_sum" else pair_multiplicity[pair_id]
            scale = Fraction(integer_weight, denominator)
            for position, hinge in enumerate(chosen_hinges):
                row_values[position] += scale * int(semantic_matrix[signed_index, hinge])
        exact_minor.append(row_values)
    exact_rank = fraction_matrix_rank(exact_minor)
    require(exact_rank == WITNESS, f"{convention}: modular witness did not lift to Q")
    integer_minor = all(value.denominator == 1 for row in exact_minor for value in row)
    if integer_minor:
        require(int(fmpz_mat([[value.numerator for value in row] for row in exact_minor]).rank()) == WITNESS, "integer rank replay drift")
    digest = hashlib.sha256()
    for row in exact_minor:
        digest.update(canonical([str(value) for value in row]))
    universe = kernel.direction_universe()
    return {
        "convention": convention,
        "sampled_hinge_count": len(sampled_hinges),
        "sampled_matrix_shape": [len(signatures), len(sampled_hinges)],
        "exact_Q_witness_rank": exact_rank,
        "complete_family_exact_Q_rank_lower_bound": exact_rank,
        "parameter_cap": CAP,
        "cap_exceeded": exact_rank > CAP,
        "witness_signatures": chosen_signatures,
        "witness_hinge_indices": chosen_hinges,
        "witness_hinge_directions": [list(universe[index]) for index in chosen_hinges],
        "witness_minor": [[str(value) for value in row] for row in exact_minor],
        "witness_minor_sha256": digest.hexdigest(),
        "integer_minor": integer_minor,
        "modular_discovery_prime": PRIME,
        "modular_rank_at_least_witness": True,
    }


def run(output: Path) -> dict[str, object]:
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    bindings = {str(path.relative_to(ROOT)): sha256(path) for path in EXPECTED}
    expected = {str(path.relative_to(ROOT)): value for path, value in EXPECTED.items()}
    require(bindings == expected, f"input drift: {bindings}")
    metadata = json.loads(MATRIX_META.read_text(encoding="utf-8"))
    require(metadata["matrix"]["file_sha256"] == EXPECTED[MATRIX], "matrix metadata drift")
    semantic_matrix = np.load(MATRIX, mmap_mode="r", allow_pickle=False)
    require(semantic_matrix.shape == (CLASSES, HINGES + N) and semantic_matrix.dtype == np.dtype("<i4"), "matrix shape/dtype drift")
    source = census.load_certificate(CERT8, 8, 3, 69)
    denominator = math.lcm(*(term.coefficient.denominator for term in source))
    source_integers = {
        term.index: term.coefficient.numerator * (denominator // term.coefficient.denominator)
        for term in source
    }
    retained, repair, _missing = kernel.load_map_and_targets()
    records = retained + repair
    signed_index = {str(record["signed_certificate_sha256"]): index for index, record in enumerate(records)}
    require(len(signed_index) == CLASSES, "signed class order drift")
    edges = tuple(combinations_with_replacement(range(1, N + 1), 2))
    signature_pairs: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    pair_signed: dict[str, int] = {}
    pair_multiplicity: dict[str, int] = defaultdict(int)
    incidence_to_coarse: dict[str, str] = {}
    radius1_to_incidence: dict[str, str] = {}
    raw_count = 0
    for term in source:
        integer_weight = source_integers[term.index]
        for left in edges:
            for right in edges:
                lifted: support.Pair = (
                    tuple(sorted(term.pair[0] + (left,))),
                    tuple(sorted(term.pair[1] + (right,))),
                )
                pair_id = class_hash(census.pair_certificate(lifted))
                signed_id = class_hash(census.signed_certificate(lifted))
                require(signed_id in signed_index, "raw lift signed class absent from matrix order")
                prior = pair_signed.setdefault(pair_id, signed_index[signed_id])
                require(prior == signed_index[signed_id], "full atom fiber crosses signed classes")
                bundle = support.signature_bundle(term.pair, left, right)
                coarse, incidence, radius1 = bundle["coarse"], bundle["incidence"], bundle["radius1"]
                require(incidence_to_coarse.setdefault(incidence, coarse) == coarse, "incidence does not refine coarse")
                require(radius1_to_incidence.setdefault(radius1, incidence) == incidence, "radius1 does not refine incidence")
                signature_pairs[coarse][pair_id] += integer_weight
                pair_multiplicity[pair_id] += 1
                raw_count += 1
        print(f"G0115_TRANSPORT_RANK_SOURCE {term.index + 1}/{len(source)}", flush=True)
    require(raw_count == 139_725 and len(pair_multiplicity) == 28_378, "raw/full atom census drift")
    signature_pairs = {
        signature: {pair_id: value for pair_id, value in pairs.items() if value}
        for signature, pairs in signature_pairs.items()
    }
    signature_pairs = {signature: pairs for signature, pairs in signature_pairs.items() if pairs}
    signatures = sorted(signature_pairs)
    support_report = json.loads(SUPPORT_REPORT.read_text(encoding="utf-8"))
    require(len(signatures) == support_report["signature_families"]["coarse"]["active_source_weighted_signatures"], "coarse signature count drift")
    sampled_hinges = sorted(set(np.linspace(0, HINGES - 1, 256, dtype=np.int64).tolist()))
    require(len(sampled_hinges) == 256, "sampled hinge collision")
    witnesses = {
        convention: convention_witness(
            convention,
            signatures,
            signature_pairs,
            pair_signed,
            pair_multiplicity,
            semantic_matrix,
            sampled_hinges,
        )
        for convention in ("raw_sum", "full_atom_average")
    }
    require(all(witness["cap_exceeded"] for witness in witnesses.values()), "a convention did not exceed cap")
    result = {
        "schema": "max11-g0115-transport-functional-rank-cap-v1",
        "result": "EXACT_PARAMETER_CAP_EXCEEDED",
        "bindings": {**bindings, "script_sha256_at_start": script_hash},
        "family": {
            "source_terms": len(source),
            "source_coefficient_denominator": denominator,
            "raw_descriptors": raw_count,
            "full_atom_orbits": len(pair_multiplicity),
            "active_coarse_signatures": len(signatures),
            "incidence_signatures_refine_coarse": len(incidence_to_coarse),
            "radius1_signatures_refine_incidence": len(radius1_to_incidence),
            "refinement_span_containment": "coarse subset incidence subset radius1",
        },
        "rank_witnesses": witnesses,
        "decision": {
            "raw_sum": "STOP_EXCEEDS_64_INDEPENDENT_PARAMETER_CAP",
            "full_atom_average": "STOP_EXCEEDS_64_INDEPENDENT_PARAMETER_CAP",
            "incidence_and_radius1": (
                "STOP_BY_EXACT_REFINEMENT: each contains the coarse functional span, whose "
                "exact Q rank is at least 65 under both aggregation conventions."
            ),
            "functional_membership_fit_executed": False,
            "reason": (
                "The preregistered description cap is crossed before target fitting. Continuing "
                "would turn a high-dimensional compressed solve into a post-hoc transport story."
            ),
        },
        "claim_boundary": (
            "Exact 65-dimensional lower bounds for the preregistered coarse source-local hinge "
            "families, and hence their refinements. This rejects eligibility under the frozen "
            "64-parameter transport cap; it does not prove functional nonmembership, rule out "
            "other operators, or decide MAX11."
        ),
        "wall_seconds": time.perf_counter() - begun,
    }
    require(sha256(SCRIPT) == script_hash, "script changed during run")
    atomic_json(output, result)
    return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = run(args.output.resolve())
    print(json.dumps({
        "result": result["result"],
        "family": result["family"],
        "rank_witnesses": {
            name: {
                "exact_Q_witness_rank": witness["exact_Q_witness_rank"],
                "cap_exceeded": witness["cap_exceeded"],
                "witness_minor_sha256": witness["witness_minor_sha256"],
            }
            for name, witness in result["rank_witnesses"].items()
        },
        "wall_seconds": result["wall_seconds"],
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
