#!/usr/bin/env python3
"""Compile the G-0115 residual repair plus lower-arity identities to MAX9."""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import importlib.util
from itertools import chain
import json
import math
import os
from pathlib import Path
import sys
import time
from typing import Sequence


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
SCRIPT = Path(__file__).resolve()
KERNEL_PATH = HERE / "semantic_repair.py"
RESIDUAL_CERTIFICATE = HERE / "semantic_repair_corrected_certificate_v1.json"
LOWER_CERTIFICATES = {
    5: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_5_2.json",
    6: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_6_2.json",
    7: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_7_3.json",
    8: ROOT / "literature/repos/max-relu-certificates/certificates/certificate_8_3.json",
}
EXPECTED = {
    KERNEL_PATH: "e400d35b6eb73a3e8821ed32c4c02742d46a15276aa2832b494dc9322d57f93d",
    RESIDUAL_CERTIFICATE: "ec0120da03f777a8e2497bea23809d96752b4389d217099d1e037cb264a873ab",
    LOWER_CERTIFICATES[5]: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    LOWER_CERTIFICATES[6]: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    LOWER_CERTIFICATES[7]: "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    LOWER_CERTIFICATES[8]: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
}
N = 9


class CompilationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise CompilationError(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def canonical(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(",", ":")) + "\n").encode()


def write_exclusive(path: Path, payload: dict[str, object]) -> None:
    require(not path.exists() and not path.is_symlink(), f"refusing to overwrite {path}")
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(descriptor, "wb") as destination:
        destination.write(canonical(payload))
        destination.flush()
        os.fsync(destination.fileno())


def load_kernel():
    observed = {path: sha256(path) for path in EXPECTED}
    require(observed == EXPECTED, f"compiler binding drift: {observed}")
    spec = importlib.util.spec_from_file_location("g0115_compiler_kernel", KERNEL_PATH)
    require(spec is not None and spec.loader is not None, "cannot load semantic kernel")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    module.bind_inputs()
    return module


def add_semantic(
    linear: list[Fraction],
    hinges: dict[tuple[int, ...], Fraction],
    semantic,
    coefficient: Fraction,
) -> None:
    for coordinate, value in enumerate(semantic[0]):
        linear[coordinate] += coefficient * int(value)
    for direction, value in semantic[1].items():
        updated = hinges.get(direction, Fraction()) + coefficient * int(value)
        if updated:
            hinges[direction] = updated
        else:
            hinges.pop(direction, None)


def elementary_source(kernel, arity: int):
    zero_based_pairs = {
        1: ((((0, 0),)), (((0, 0),))),
        2: ((((0, 1),)), (((0, 1),))),
        3: ((((0, 1),)), (((2, 2),))),
        4: ((((0, 1),)), (((2, 3),))),
    }
    pair = zero_based_pairs[arity]
    return [(Fraction(1, math.factorial(arity)), pair)]


def load_source_certificate(kernel, arity: int):
    if arity <= 4:
        return elementary_source(kernel, arity), None
    path = LOWER_CERTIFICATES[arity]
    document = json.loads(path.read_text(encoding="utf-8"))
    require(document.get("n") == arity and isinstance(document.get("terms"), list), "lower certificate drift")
    terms = []
    for raw in document["terms"]:
        pair = kernel.parse_pair(raw["pair"], arity)
        terms.append((Fraction(raw["coefficient"]), pair))
    return terms, path


def verify_source_max(kernel, dp, arity: int, terms):
    linear = [Fraction() for _ in range(arity)]
    hinges: dict[tuple[int, ...], Fraction] = {}
    for coefficient, pair in terms:
        add_semantic(linear, hinges, kernel.normal_form(dp, pair, arity), coefficient)
    expected = [Fraction() for _ in range(arity - 1)] + [Fraction(1)]
    require(linear == expected and not hinges, f"MAX{arity} source identity replay failed")
    return {"terms": len(terms), "linear": [str(value) for value in linear], "hinges": 0}


def binomial_basis_coefficients(delta: Sequence[Fraction]) -> list[Fraction]:
    require(len(delta) == N, "delta arity drift")
    coefficients: list[Fraction] = []
    for rank in range(1, N):
        value = delta[rank - 1] - sum(
            coefficients[arity - 1] * math.comb(rank - 1, arity - 1)
            for arity in range(1, rank)
        )
        coefficients.append(value)
    reconstructed = [
        sum(
            coefficients[arity - 1] * math.comb(rank - 1, arity - 1)
            for arity in range(1, N)
        )
        for rank in range(1, N + 1)
    ]
    require(reconstructed == list(delta), "delta escaped the U1..U8 binomial basis")
    return coefficients


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--certificate", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args(argv)
    begun = time.perf_counter()
    script_hash = sha256(SCRIPT)
    kernel = load_kernel()
    dp = kernel.load_dp()
    residual = json.loads(RESIDUAL_CERTIFICATE.read_text(encoding="utf-8"))
    base_linear = [Fraction(value) for value in residual["semantics"]["retained_plus_repair_linear"]]
    target_linear = [Fraction() for _ in range(N - 1)] + [Fraction(1)]
    delta = [target_linear[index] - base_linear[index] for index in range(N)]
    alternating = [(-1) ** (N - rank) * math.comb(N - 1, rank - 1) for rank in range(1, N + 1)]
    require(sum(Fraction(a) * value for a, value in zip(alternating, delta, strict=True)) == 0, "correction changes Lambda")
    alpha = binomial_basis_coefficients(delta)

    source_controls = {}
    correction_terms = []
    correction_linear = [Fraction() for _ in range(N)]
    correction_hinges: dict[tuple[int, ...], Fraction] = {}
    correction_counts = {}
    for arity in range(1, N):
        source_terms, source_path = load_source_certificate(kernel, arity)
        source_controls[f"MAX{arity}"] = verify_source_max(kernel, dp, arity, source_terms)
        embedded_scale = alpha[arity - 1] / math.factorial(N - arity)
        correction_counts[str(arity)] = 0
        for source_index, (source_coefficient, pair) in enumerate(source_terms):
            coefficient = embedded_scale * source_coefficient
            if not coefficient:
                continue
            semantic = kernel.normal_form(dp, pair, N)
            add_semantic(correction_linear, correction_hinges, semantic, coefficient)
            correction_terms.append(
                {
                    "coefficient": str(coefficient),
                    "pair": kernel.serialize_pair(pair),
                    "provenance": {
                        "kind": "embedded_lower_MAX",
                        "source_arity": arity,
                        "source_term_index": source_index,
                        "binomial_basis_coefficient": str(alpha[arity - 1]),
                        "inactive_label_factor": math.factorial(N - arity),
                        "source_certificate": (
                            str(source_path.relative_to(ROOT)) if source_path is not None else "elementary"
                        ),
                    },
                }
            )
            correction_counts[str(arity)] += 1
        print(f"G0115_COMPILE MAX{arity} terms={correction_counts[str(arity)]}", flush=True)

    require(not correction_hinges, "embedded lower-arity correction has nonzero hinges")
    require(correction_linear == delta, "embedded lower-arity correction linear drift")
    full_linear = [base_linear[index] + correction_linear[index] for index in range(N)]
    require(full_linear == target_linear, "compiled identity linear target drift")

    candidate_terms = []
    for kind, terms in (
        ("coefficient_frozen_retained", residual["retained_fixed_terms"]),
        ("coefficient_frozen_repair", residual["repair_terms"]),
    ):
        for source_index, term in enumerate(terms):
            candidate_terms.append(
                {
                    "coefficient": term["coefficient"],
                    "pair": term["pair"],
                    "provenance": {"kind": kind, "source_term_index": source_index},
                }
            )
    full_terms = list(chain(candidate_terms, correction_terms))
    certificate = {
        "schema": "g0115-compiled-full-max9-identity-v1",
        "n": N,
        "target": "MAX9",
        "terms": full_terms,
        "support_structure": {
            "coefficient_frozen_retained": len(residual["retained_fixed_terms"]),
            "coefficient_frozen_repair": len(residual["repair_terms"]),
            "lower_correction_by_arity": correction_counts,
            "total": len(full_terms),
        },
        "lower_binomial_basis_coefficients": {
            str(arity): str(alpha[arity - 1]) for arity in range(1, N)
        },
        "semantics": {
            "hinge_nonzeros": 0,
            "linear": [str(value) for value in full_linear],
            "rational_lambda": "1",
        },
        "bindings": {
            str(path.relative_to(ROOT)): digest for path, digest in EXPECTED.items()
        }
        | {"compiler_sha256_at_start": script_hash},
        "claim_boundary": (
            "Exact mixed-degree MAX9 identity compiled from the G-0115 coefficient-frozen "
            "residual repair and independently certified MAX1--MAX8 identities; this is not "
            "a MAX10/MAX11 identity or an induction theorem."
        ),
    }
    write_exclusive(args.certificate.resolve(), certificate)
    certificate_hash = sha256(args.certificate.resolve())
    mutated_correction = correction_linear.copy()
    mutation_pair = kernel.parse_pair(correction_terms[0]["pair"])
    add_semantic(
        mutated_correction,
        {},
        kernel.normal_form(dp, mutation_pair, N),
        Fraction(1),
    )
    require(mutated_correction != delta, "correction coefficient mutation escaped")
    report = {
        "schema": "g0115-full-max9-compilation-report-v1",
        "result": "PASS",
        "bindings": certificate["bindings"],
        "source_identity_controls": source_controls,
        "base_linear": [str(value) for value in base_linear],
        "required_correction": [str(value) for value in delta],
        "lower_binomial_basis_coefficients": certificate["lower_binomial_basis_coefficients"],
        "correction_hinge_nonzeros": 0,
        "correction_linear_replayed": True,
        "compiled_linear": [str(value) for value in full_linear],
        "support_structure": certificate["support_structure"],
        "mutation_rejected": True,
        "certificate_path": str(args.certificate.resolve().relative_to(ROOT)),
        "certificate_sha256": certificate_hash,
        "certificate_canonical_sha256": hashlib.sha256(canonical(certificate)).hexdigest(),
        "wall_seconds": time.perf_counter() - begun,
        "claim_boundary": certificate["claim_boundary"],
    }
    require(sha256(SCRIPT) == script_hash, "compiler changed during execution")
    write_exclusive(args.report.resolve(), report)
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
