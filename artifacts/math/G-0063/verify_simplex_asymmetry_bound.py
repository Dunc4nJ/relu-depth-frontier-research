#!/usr/bin/env python3
"""Exact simplex-asymmetry bound and public-certificate controls.

This script has two jobs:

1. derive the rational lower bound on a stabilizer A in
       Delta_n + A = B,  A,B in P_{n,d};
2. independently evaluate lambda_Delta and lambda_{-Delta} on the negative
   and positive sides of the public symmetric MAX5--MAX10 certificates.

Only exact integer/Fraction arithmetic is used.  The certificate computation
does not enumerate N! permutations: at the simplex facet normals there are
only N possible preimages of the distinguished coordinate, each occurring
(N-1)! times.
"""

from __future__ import annotations

import argparse
from fractions import Fraction
import hashlib
import json
from math import factorial
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "maxrelu-g0063-simplex-asymmetry-bound-v1"
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CERT_DIR = ROOT / "literature/repos/max-relu-certificates/certificates"
SOURCE_PDF = HERE / "source/2607.03815.pdf"
SOURCE_PDF_SHA256 = "4875ffd0fdc33624d8da00fa87709b88a6087587d27db21571f447aa23d2182b"
DEFAULT_OUTPUT = HERE / "simplex_asymmetry_certificate_controls_v1.json"


def sha256_path(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def q(value: Fraction | int) -> str:
    return str(value)


def support_pair(pair: list[list[list[int]]], x: list[int]) -> int:
    """Support of conv(Z_left union Z_right) at x.

    Each graph edge [a,b] denotes the segment [e_a,e_b], so its support is
    max(x_a,x_b).  Loops are handled without a special case.
    """

    return max(
        sum(max(x[a - 1], x[b - 1]) for a, b in side)
        for side in pair
    )


def symmetrized_lambdas(pair: list[list[list[int]]], N: int) -> tuple[int, int]:
    """Return (lambda_Delta, lambda_-Delta) for one full S_N orbit sum.

    Work in H={x: sum x_i=0}.  For the centered coordinate simplex
    Delta=conv(e_i-1/N), facet normals are q_i=1-N e_i.  By Lemma 13 of
    Bakaev--Yehudayoff, lambda_Delta(K)=N^{-1} sum_i h_K(q_i).
    The orbit sum is S_N invariant, hence this is h_K(q_1).  Among the N!
    permutations, each possible preimage of coordinate 1 occurs (N-1)!
    times.  The same argument with -q_i gives lambda_-Delta.
    """

    plus_sum = 0
    minus_sum = 0
    for special in range(N):
        q_plus = [1] * N
        q_plus[special] = -(N - 1)
        q_minus = [-1] * N
        q_minus[special] = N - 1
        plus_sum += support_pair(pair, q_plus)
        minus_sum += support_pair(pair, q_minus)
    multiplicity = factorial(N - 1)
    return multiplicity * plus_sum, multiplicity * minus_sum


def certificate_control(path: Path) -> dict[str, Any]:
    with path.open() as stream:
        certificate = json.load(stream)
    N = int(certificate["n"])
    sides: dict[str, dict[str, Any]] = {
        "A_negative": {"term_count": 0, "lambda_Delta": Fraction(0), "lambda_minus_Delta": Fraction(0)},
        "B_positive": {"term_count": 0, "lambda_Delta": Fraction(0), "lambda_minus_Delta": Fraction(0)},
    }
    for term in certificate["terms"]:
        coefficient = Fraction(term["coefficient"])
        if coefficient == 0:
            raise ValueError(f"zero coefficient in {path}")
        side = sides["A_negative" if coefficient < 0 else "B_positive"]
        lam_plus, lam_minus = symmetrized_lambdas(term["pair"], N)
        weight = abs(coefficient)
        side["term_count"] += 1
        side["lambda_Delta"] += weight * lam_plus
        side["lambda_minus_Delta"] += weight * lam_minus

    A = sides["A_negative"]
    B = sides["B_positive"]
    dim = N - 1
    if A["lambda_Delta"] <= 0 or B["lambda_Delta"] <= 0:
        raise AssertionError("both signed sides must be non-singleton")
    for side in sides.values():
        side["rho_Delta"] = side["lambda_minus_Delta"] / side["lambda_Delta"]

    delta_plus_residual = B["lambda_Delta"] - A["lambda_Delta"]
    delta_minus_residual = B["lambda_minus_Delta"] - A["lambda_minus_Delta"]
    if delta_plus_residual != 1 or delta_minus_residual != dim:
        raise AssertionError(
            f"outer-additivity replay failed for {path.name}: "
            f"got ({delta_plus_residual},{delta_minus_residual}), expected (1,{dim})"
        )

    p = Fraction(3)  # all pinned certificates are two-hidden-layer certificates
    universal_bound = Fraction(0)
    rho_specific_bound: Fraction | None = None
    if dim > p:
        universal_bound = Fraction(dim - p, 1) / (p - Fraction(1, p))
        rho_A = A["rho_Delta"]
        if rho_A < p:
            rho_specific_bound = Fraction(dim - p, 1) / (p - rho_A)
        if A["lambda_Delta"] < universal_bound:
            raise AssertionError(f"universal bound violated by {path.name}")
        if rho_specific_bound is not None and A["lambda_Delta"] < rho_specific_bound:
            raise AssertionError(f"rho-specific bound violated by {path.name}")

    serial_sides: dict[str, Any] = {}
    for name, side in sides.items():
        serial_sides[name] = {
            "term_count": side["term_count"],
            "lambda_Delta": q(side["lambda_Delta"]),
            "lambda_minus_Delta": q(side["lambda_minus_Delta"]),
            "rho_Delta": q(side["rho_Delta"]),
        }
    return {
        "certificate": str(path.relative_to(ROOT)),
        "certificate_sha256": sha256_path(path),
        "N_coordinates": N,
        "simplex_dimension_n": dim,
        "depth_d": 2,
        "p_equals_2_to_d_minus_1": "3",
        "sides": serial_sides,
        "identity_checks": {
            "lambda_Delta_B_minus_A": q(delta_plus_residual),
            "expected_lambda_Delta_of_Delta": "1",
            "lambda_minus_Delta_B_minus_A": q(delta_minus_residual),
            "expected_lambda_minus_Delta_of_Delta": q(dim),
        },
        "necessary_bound": {
            "universal_lower_bound_on_lambda_Delta_A": q(universal_bound),
            "rho_specific_lower_bound_on_lambda_Delta_A": (
                q(rho_specific_bound) if rho_specific_bound is not None else None
            ),
            "universal_bound_slack": q(A["lambda_Delta"] - universal_bound),
            "rho_specific_bound_slack": (
                q(A["lambda_Delta"] - rho_specific_bound)
                if rho_specific_bound is not None
                else None
            ),
        },
    }


def target_bound(n: int, d: int) -> dict[str, Any]:
    p = Fraction(2**d - 1)
    if n <= p:
        raise ValueError("the nontrivial bound requires n > 2^d-1")
    bound = Fraction(n - p, 1) / (p - Fraction(1, p))
    zonotope_bound = Fraction(n - p, 1) / (p - 1)
    return {
        "simplex_dimension_n": n,
        "depth_d": d,
        "p_equals_2_to_d_minus_1": q(p),
        "rho_A_interval_from_depth_and_reflection": [q(Fraction(1, p)), q(p)],
        "universal_lower_bound_on_lambda_Delta_A": q(bound),
        "zonotope_A_lower_bound_on_lambda_Delta_A": q(zonotope_bound),
    }


def build_report() -> dict[str, Any]:
    if sha256_path(SOURCE_PDF) != SOURCE_PDF_SHA256:
        raise AssertionError("primary-source PDF hash mismatch")
    certificate_paths = sorted(
        CERT_DIR.glob("certificate_*.json"),
        key=lambda path: int(path.name.split("_")[1]),
    )
    if [json.loads(path.read_text())["n"] for path in certificate_paths] != list(range(5, 11)):
        raise AssertionError("expected exactly the pinned MAX5--MAX10 controls")
    return {
        "schema": SCHEMA,
        "status": "PASS",
        "claim": "necessary_condition_only",
        "primary_source": {
            "title": "A simplex-based measure of symmetry",
            "authors": ["Egor Bakaev", "Amir Yehudayoff"],
            "arxiv_id": "2607.03815",
            "url": "https://arxiv.org/abs/2607.03815",
            "pdf": str(SOURCE_PDF.relative_to(ROOT)),
            "pdf_sha256": SOURCE_PDF_SHA256,
            "locators": {
                "lambda_and_rho_definitions": "PDF pp. 2--3 (paper pp. 1--2)",
                "outer_additivity_and_simplex_characterization": "PDF pp. 6 and 20--24 (paper pp. 5 and 19--23), Definition and Theorem 6",
                "depth_class_and_bound": "PDF pp. 6--7 and 25--27 (paper pp. 5--6 and 24--26), Theorems 7--10",
                "virtual_polytope_neural_network_correspondence": "PDF p. 25 (paper p. 24), displayed Lemma in Section 6.1",
            },
        },
        "target_MAX11": target_bound(10, 2),
        "public_certificate_controls": [certificate_control(path) for path in certificate_paths],
        "boundaries": [
            "The bound is necessary, not sufficient for A or B to lie in P_{n,d}.",
            "It does not obstruct arbitrarily large stabilizers.",
            "The public controls validate the algebra but do not approach equality and do not establish sharpness.",
        ],
    }


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, indent=2) + "\n"


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check-frozen", action="store_true")
    args = parser.parse_args(argv)
    report = build_report()
    payload = canonical_json(report)
    if args.check_frozen:
        if not args.output.is_file():
            raise SystemExit(f"missing frozen report: {args.output}")
        if args.output.read_text() != payload:
            raise SystemExit("frozen report differs from exact recomputation")
        print("PASS: frozen report matches exact recomputation")
        return 0
    args.output.write_text(payload)
    print(f"PASS: wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
