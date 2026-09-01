#!/usr/bin/env python3
"""Build finite pre-normalization orbit certificates for the 17 mass-4 identities.

Uniform-loop relations are certified by a lexicographic rank bijection inside
each exact raw-word fiber.  Mixed-loop relations are certified after maximal
same-word cancellation by the involution (w,k,sign) -> (-w,k,-sign), followed
by an exact zero first-moment check.  No primitive-direction normalization or
ReLU normal-form folding is used.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from hashlib import sha256
import json
from math import factorial
from pathlib import Path
from typing import Iterable


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CANDIDATE = ROOT / "artifacts/math/G-0187-exact-sparse-kernel-basis/candidate/exact_sparse_left_kernel_basis_v1.jsonl"
RAW_INPUT = ROOT / "artifacts/math/G-0189-sparse-kernel-full-nf-scan/audit/g0109_92_input.json"
RAW_PROBE_SOURCE = HERE / "src/main.rs"
RAW_PROBE_BINARY = HERE / "target/release/g0109-normal-form-probe"
INDEPENDENT_AUDIT = ROOT / "artifacts/math/G-0189-sparse-kernel-full-nf-scan/audit/independent_g0109_audit_receipt.json"
DEFAULT_OUTPUT = HERE / "results/orbit_level_certificate_v1.json"

UNIFORM_COLUMNS = [12, 17, 21, 24, 68, 72, 75, 82, 90, 91, 108, 117, 121, 122]
MIXED_COLUMNS = [15, 28, 87]
N = 11


def file_sha256(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def row_table_hash(rows: Iterable[tuple[tuple[int, ...], int]]) -> str:
    """Hash an ordered integer table with a deliberately simple encoding."""
    digest = sha256()
    for word, value in rows:
        line = ",".join(map(str, word)) + ":" + str(value) + "\n"
        digest.update(line.encode("ascii"))
    return digest.hexdigest()


def first_nonzero_positive(word: tuple[int, ...]) -> bool:
    for value in word:
        if value:
            return value > 0
    raise RuntimeError("zero word has no orientation")


def negate(word: tuple[int, ...]) -> tuple[int, ...]:
    return tuple(-value for value in word)


def term_histogram(form: dict) -> dict[tuple[int, ...], int]:
    histogram = {tuple(term["word"]): int(term["multiplicity"]) for term in form["raw_terms"]}
    require(sum(histogram.values()) == factorial(N), f"raw census drift q{form['sequence']}")
    return histogram


def aggregate_relation(relation: dict, forms: dict[int, dict]):
    positive = defaultdict(int)
    negative = defaultdict(int)
    positive_base = [0] * N
    negative_base = [0] * N
    positive_sequences = []
    negative_sequences = []
    for _row, sequence, coefficient_text in relation["terms"]:
        coefficient = int(coefficient_text)
        require(abs(coefficient) == 1, f"non-unit coefficient in column {relation['basis_column']}")
        form = forms[sequence]
        destination = positive if coefficient > 0 else negative
        base_destination = positive_base if coefficient > 0 else negative_base
        sequences = positive_sequences if coefficient > 0 else negative_sequences
        sequences.append(sequence)
        for word, multiplicity in term_histogram(form).items():
            destination[word] += multiplicity
        for rank, value in enumerate(form["base_linear"]):
            base_destination[rank] += int(value)
    require(len(positive_sequences) == len(negative_sequences) == 3, "expected a 3-versus-3 relation")
    return {
        "positive": dict(positive),
        "negative": dict(negative),
        "positive_base": positive_base,
        "negative_base": negative_base,
        "positive_sequences": sorted(positive_sequences),
        "negative_sequences": sorted(negative_sequences),
    }


def uniform_certificate(relation: dict, forms: dict[int, dict]) -> dict:
    data = aggregate_relation(relation, forms)
    positive = data["positive"]
    negative = data["negative"]
    union = sorted(positive.keys() | negative.keys())
    mismatches = [(word, positive.get(word, 0) - negative.get(word, 0)) for word in union]
    mismatches = [(word, value) for word, value in mismatches if value]
    require(not mismatches, f"uniform fiber mismatch in column {relation['basis_column']}")
    require(data["positive_base"] == data["negative_base"], "uniform base-linear mismatch")
    expected_side = 3 * factorial(N)
    require(sum(positive.values()) == sum(negative.values()) == expected_side, "uniform side census drift")

    fiber_sizes = Counter(positive[word] for word in union)
    table_rows = [(word, positive[word]) for word in union]
    return {
        "basis_column": relation["basis_column"],
        "positive_sequences": data["positive_sequences"],
        "negative_sequences": data["negative_sequences"],
        "raw_word_fibers": len(union),
        "occurrences_each_side": expected_side,
        "matched_occurrences": expected_side,
        "minimum_fiber_size": min(positive.values()),
        "maximum_fiber_size": max(positive.values()),
        "fiber_size_histogram": [[size, count] for size, count in sorted(fiber_sizes.items())],
        "canonical_fiber_table_sha256": row_table_hash(table_rows),
        "positive_base_linear": data["positive_base"],
        "negative_base_linear": data["negative_base"],
        "exact_fiberwise_equality": True,
        "bijection": {
            "occurrence_encoding": "(q_sequence, pi), with pi a one-line permutation of vertices 0,...,10",
            "fiber_key": "the unnormalized back-degree word w(q,pi)",
            "within_fiber_order": "lexicographic order on (q_sequence, pi)",
            "map": "send the k-th positive occurrence in fiber w to the k-th negative occurrence in the same fiber w",
            "inverse": "send the k-th negative occurrence in fiber w to the k-th positive occurrence in the same fiber w",
        },
    }


def mixed_certificate(relation: dict, forms: dict[int, dict]) -> dict:
    data = aggregate_relation(relation, forms)
    positive = data["positive"]
    negative = data["negative"]
    union = positive.keys() | negative.keys()
    residual = {
        word: positive.get(word, 0) - negative.get(word, 0)
        for word in union
        if positive.get(word, 0) != negative.get(word, 0)
    }
    zero = (0,) * N
    require(residual.get(zero, 0) == 0, "zero-word residual cannot enter negation involution")
    require(
        all(residual.get(negate(word), 0) == -value for word, value in residual.items()),
        f"mixed residual is not odd in column {relation['basis_column']}",
    )

    representatives = sorted(word for word in residual if first_nonzero_positive(word))
    require(len(representatives) * 2 == len(residual), "negation-orbit census drift")
    moment = [0] * N
    for word in representatives:
        coefficient = residual[word]
        for rank, value in enumerate(word):
            moment[rank] += coefficient * value
    base_residual = [
        data["positive_base"][rank] - data["negative_base"][rank]
        for rank in range(N)
    ]
    total_linear = [base_residual[rank] + moment[rank] for rank in range(N)]
    require(total_linear == [0] * N, f"mixed zero-moment failure in column {relation['basis_column']}")

    same_word_cancelled = sum(min(positive.get(word, 0), negative.get(word, 0)) for word in union)
    residual_l1 = sum(abs(value) for value in residual.values())
    require(2 * same_word_cancelled + residual_l1 == 6 * factorial(N), "mixed occurrence partition drift")
    pair_rows = [(word, residual[word]) for word in representatives]
    abs_coefficients = Counter(abs(residual[word]) for word in representatives)
    return {
        "basis_column": relation["basis_column"],
        "positive_sequences": data["positive_sequences"],
        "negative_sequences": data["negative_sequences"],
        "occurrences_each_side_before_cancellation": 3 * factorial(N),
        "same_word_pairs_cancelled": same_word_cancelled,
        "residual_raw_words": len(residual),
        "negation_orbits": len(representatives),
        "residual_occurrences_both_signs": residual_l1,
        "residual_occurrence_pairs": residual_l1 // 2,
        "maximum_abs_residual_fiber": max(map(abs, residual.values())),
        "representative_abs_coefficient_histogram": [
            [coefficient, count] for coefficient, count in sorted(abs_coefficients.items())
        ],
        "canonical_positive_orientation_pair_table_sha256": row_table_hash(pair_rows),
        "positive_base_linear": data["positive_base"],
        "negative_base_linear": data["negative_base"],
        "base_linear_residual": base_residual,
        "relu_pair_linear_moment": moment,
        "total_linear_residual": total_linear,
        "exact_oddness_under_word_negation": True,
        "involution": {
            "prestep": "cancel equal-side ranks within every identical raw-word fiber",
            "residual_occurrence_encoding": "(w,k,sign), 1 <= k <= |R(w)| and sign = sign(R(w))",
            "map": "I(w,k,sign)=(-w,k,-sign)",
            "fixed_point_free": True,
            "relu_orbit_contribution": "for first-nonzero-positive w, R(w)[rho(w.x)-rho(-w.x)]=R(w) w.x",
        },
    }


def deletion_control(relation: dict, forms: dict[int, dict], expected_class: str) -> dict:
    """Delete the least positive q atom and check that the claimed symmetry breaks."""
    data = aggregate_relation(relation, forms)
    deleted_sequence = data["positive_sequences"][0]
    deleted = term_histogram(forms[deleted_sequence])
    positive = dict(data["positive"])
    for word, multiplicity in deleted.items():
        next_value = positive[word] - multiplicity
        if next_value:
            positive[word] = next_value
        else:
            del positive[word]
    union = positive.keys() | data["negative"].keys()
    residual = {
        word: positive.get(word, 0) - data["negative"].get(word, 0)
        for word in union
        if positive.get(word, 0) != data["negative"].get(word, 0)
    }
    odd = all(residual.get(negate(word), 0) == -value for word, value in residual.items())
    if expected_class == "uniform":
        require(residual, "uniform deletion control unexpectedly preserves equality")
    else:
        require(not odd, "mixed deletion control unexpectedly preserves oddness")
    return {
        "basis_column": relation["basis_column"],
        "deleted_positive_sequence": deleted_sequence,
        "residual_raw_words": len(residual),
        "residual_l1_multiplicity": sum(abs(value) for value in residual.values()),
        "fiberwise_equality_after_deletion": not residual,
        "oddness_after_deletion": odd,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-output", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    raw_output = args.raw_output.resolve()
    output = args.output.resolve()
    require(not output.exists(), "refusing to overwrite output")
    audit = json.loads(INDEPENDENT_AUDIT.read_text())
    require(
        audit["result"] == "GO_INDEPENDENT_EXACT_REPLAY_CONFIRMS_ALL_17_GLOBAL_IDENTITIES",
        "independent G0189 audit is not GO",
    )

    with CANDIDATE.open() as handle:
        next(handle)
        relations = [json.loads(line) for line in handle]
    raw_document = json.loads(raw_output.read_text())
    require(raw_document["schema"] == "g0193-g0109-raw-word-probe-v1", "raw schema drift")
    forms = {form["sequence"]: form for form in raw_document["raw_forms"]}
    require(len(forms) == 92, "raw form count drift")

    uniform = [uniform_certificate(relations[column], forms) for column in UNIFORM_COLUMNS]
    mixed = [mixed_certificate(relations[column], forms) for column in MIXED_COLUMNS]
    controls = [
        deletion_control(relations[column], forms, "uniform") for column in UNIFORM_COLUMNS
    ] + [
        deletion_control(relations[column], forms, "mixed") for column in MIXED_COLUMNS
    ]

    certificate = {
        "schema": "g0193.finite-raw-orbit-certificates.v1",
        "result": "GO_FINITE_RAW_ORBIT_PROOFS_FOR_ALL_17_IDENTITIES",
        "claim_boundary": (
            "Exact finite n=11 proof objects for the 17 frozen relations. The common fiber-rank rule is "
            "an explicit bijection schema, but it is census-defined and is not a local graph bijection, a "
            "parameterized theorem, a novelty claim, or a MAX11 result."
        ),
        "raw_word_definition": (
            "Extend each signed adjacency matrix W by zero inactive vertices. For pi in S_11, "
            "w_r = W[pi_r,pi_r] + sum_{s<r} W[pi_r,pi_s]. No sign orientation, gcd division, "
            "primitive-direction quotient, activity test, or ReLU folding is applied."
        ),
        "bindings": {
            "candidate": {"path": str(CANDIDATE), "sha256": file_sha256(CANDIDATE)},
            "raw_input": {"path": str(RAW_INPUT), "sha256": file_sha256(RAW_INPUT)},
            "raw_output": {"path": str(raw_output), "bytes": raw_output.stat().st_size, "sha256": file_sha256(raw_output)},
            "raw_probe_source": {"path": str(RAW_PROBE_SOURCE), "sha256": file_sha256(RAW_PROBE_SOURCE)},
            "raw_probe_binary": {"path": str(RAW_PROBE_BINARY), "sha256": file_sha256(RAW_PROBE_BINARY)},
            "independent_g0189_audit": {"path": str(INDEPENDENT_AUDIT), "sha256": file_sha256(INDEPENDENT_AUDIT)},
        },
        "summary": {
            "uniform_relations": len(uniform),
            "uniform_relations_with_exact_raw_fiber_bijection": sum(item["exact_fiberwise_equality"] for item in uniform),
            "mixed_relations": len(mixed),
            "mixed_relations_with_exact_sign_reversing_involution_and_zero_total_moment": sum(
                item["exact_oddness_under_word_negation"] and item["total_linear_residual"] == [0] * N
                for item in mixed
            ),
            "hostile_atom_deletion_controls": len(controls),
            "hostile_controls_rejected": sum(
                (not item["fiberwise_equality_after_deletion"])
                and (item["basis_column"] in UNIFORM_COLUMNS or not item["oddness_after_deletion"])
                for item in controls
            ),
        },
        "uniform_fiber_bijections": uniform,
        "mixed_sign_reversing_involutions": mixed,
        "hostile_atom_deletion_controls": controls,
    }
    require(certificate["summary"]["uniform_relations_with_exact_raw_fiber_bijection"] == 14, "uniform GO count drift")
    require(certificate["summary"]["mixed_relations_with_exact_sign_reversing_involution_and_zero_total_moment"] == 3, "mixed GO count drift")
    require(certificate["summary"]["hostile_controls_rejected"] == 17, "hostile control count drift")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(certificate, sort_keys=True, separators=(",", ":")) + "\n")
    print(json.dumps({
        "output": str(output),
        "bytes": output.stat().st_size,
        "sha256": file_sha256(output),
        "source_sha256": file_sha256(Path(__file__)),
        "summary": certificate["summary"],
        "uniform_columns": [item["basis_column"] for item in uniform],
        "mixed": [
            {
                "basis_column": item["basis_column"],
                "negation_orbits": item["negation_orbits"],
                "moment": item["relu_pair_linear_moment"],
                "base": item["base_linear_residual"],
            }
            for item in mixed
        ],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
