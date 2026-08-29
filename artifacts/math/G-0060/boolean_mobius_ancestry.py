#!/usr/bin/env python3
"""Exact controls for the Boolean-Mobius ancestor-support obstruction.

The mathematical theorem is in ``README.md``.  This program does not prove
the universal statement; it replays its finite calibrations exactly:

* the full Boolean difference of MAX_11 is one;
* the exact MAX_3 network has one charged, full-support second neuron;
* a biased full-support term can be charged, while deleting one coordinate
  makes the charge vanish by pairwise cancellation;
* full ancestor support is not sufficient for nonzero charge; and
* every pinned MAX5--MAX10 certificate obeys the same charge-conservation
  identity term by term.

Only integer and ``fractions.Fraction`` arithmetic is used.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import itertools
import json
import math
from fractions import Fraction
from pathlib import Path
from typing import Any, Callable, Iterable, Sequence


ROOT = Path(__file__).resolve().parents[3]
CERTIFICATE_DIR = ROOT / "literature/repos/max-relu-certificates/certificates"
EXPECTED_CERTIFICATE_SHA256 = {
    5: "698f70d87ec6b2ef07cd1d0287447dd2361f4b6d0d98571cc7485182b194e694",
    6: "026a74970c84dc8e4ff271b871a95e882358e5a7b4e98226508a55ed6af94a83",
    7: "b79aaaf423187cf5aaa51c9272799bf36198759dd018a1a286716cce7b1b53be",
    8: "68b2a2698ab13a85164a8a0c5635649a92c5c1059c6c058115ebe3af2f0171c3",
    9: "4eb96684d0ce02d324f2fa0f7f95adf5dbc8fb99d3e3e9362cb435b9b3c22d88",
    10: "10f38b27fa555866eda7c3ee10d5da51f3cd1db810a74860d6ab8ef8a30982e4",
}


class AuditFailure(RuntimeError):
    """Raised when an exact obligation or hostile control fails."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditFailure(message)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def relu(value: Fraction) -> Fraction:
    return max(Fraction(0), value)


def indicator(mask: int, n: int) -> tuple[Fraction, ...]:
    return tuple(Fraction((mask >> coordinate) & 1) for coordinate in range(n))


def boolean_mobius_charge(
    n: int, function: Callable[[tuple[Fraction, ...]], Fraction]
) -> Fraction:
    """Return sum_S (-1)^(n-|S|) f(1_S) exactly."""

    total = Fraction(0)
    for mask in range(1 << n):
        sign = -1 if (n - mask.bit_count()) % 2 else 1
        total += sign * function(indicator(mask, n))
    return total


def max_charge(n: int) -> Fraction:
    return boolean_mobius_charge(n, lambda x: max(x))


def max3_calibration() -> dict[str, Any]:
    """Replay the exact MAX3 formula and its charge decomposition."""

    def local_v(x: tuple[Fraction, ...]) -> Fraction:
        return relu(x[1] - x[2])

    def nested(x: tuple[Fraction, ...]) -> Fraction:
        return relu(relu(x[0] - x[2]) - relu(x[1] - x[2]))

    def carrier(x: tuple[Fraction, ...]) -> Fraction:
        return x[2]

    grid_checks = 0
    for raw in itertools.product(range(-2, 3), repeat=3):
        x = tuple(Fraction(value) for value in raw)
        require(carrier(x) + local_v(x) + nested(x) == max(x), "MAX3 identity failed")
        grid_checks += 1

    carrier_charge = boolean_mobius_charge(3, carrier)
    local_charge = boolean_mobius_charge(3, local_v)
    nested_charge = boolean_mobius_charge(3, nested)
    charges = {
        "linear_x3": carrier_charge,
        "local_relu_x2_minus_x3": local_charge,
        "nested_full_support_term": nested_charge,
    }
    target_charge = max_charge(3)
    require(carrier_charge == 0, "linear MAX3 carrier acquired a third-order charge")
    require(local_charge == 0, "proper-support MAX3 term acquired a third-order charge")
    require(nested_charge == 1, "full-support MAX3 term lost its third-order charge")
    require(sum(charges.values(), Fraction(0)) == target_charge == 1, "MAX3 charge drift")
    return {
        "global_grid_points": grid_checks,
        "charges": {key: str(value) for key, value in charges.items()},
        "target_charge": str(target_charge),
    }


def biased_and_dense_controls() -> dict[str, Any]:
    """Exercise bias safety, coordinate pairing, and the failed converse."""

    n = 11

    # On the Boolean cube this is one only at 1_[11].  It is a valid single
    # second-neuron term: each x_i is compiled as relu(x_i)-relu(-x_i), and
    # the second bias is -10.
    dense_threshold = lambda x: relu(sum(x, Fraction(0)) - 10)

    # This term ignores x_11.  It takes the same value at S and S union {11},
    # so the two Mobius summands cancel even though the biases are nonzero.
    local_threshold = lambda x: relu(sum(x[:10], Fraction(0)) - 9)

    # Full coordinate dependence is necessary, not sufficient.  On the
    # Boolean cube this full-support term is the degree-one function |S|.
    dense_uncharged = lambda x: relu(sum(x, Fraction(0)))

    dense_charge = boolean_mobius_charge(n, dense_threshold)
    local_charge = boolean_mobius_charge(n, local_threshold)
    uncharged = boolean_mobius_charge(n, dense_uncharged)
    require(dense_charge == 1, "biased dense threshold should have unit charge")
    require(local_charge == 0, "proper-support biased term should have zero charge")
    require(uncharged == 0, "full-support linear-on-cube term should be uncharged")

    paired_equalities = 0
    for mask in range(1 << 10):
        without_last = indicator(mask, n)
        with_last = indicator(mask | (1 << 10), n)
        require(
            local_threshold(without_last) == local_threshold(with_last),
            "local term unexpectedly depends on x_11",
        )
        paired_equalities += 1

    # Equality-destroying target mutation: remove the value at the full cube
    # vertex.  For n=11 that one missing contribution changes charge 1 to 0.
    def holed_max11(x: tuple[Fraction, ...]) -> Fraction:
        if all(value == 1 for value in x):
            return Fraction(0)
        return max(x)

    holed_charge = boolean_mobius_charge(n, holed_max11)
    require(holed_charge == 0, "full-vertex target mutation was not detected")

    return {
        "biased_dense_threshold_charge": str(dense_charge),
        "biased_proper_support_threshold_charge": str(local_charge),
        "full_support_but_uncharged_charge": str(uncharged),
        "proper_support_coordinate_pairs_checked": paired_equalities,
        "holed_max11_charge": str(holed_charge),
    }


def parse_pair(term: dict[str, Any], n: int) -> tuple[tuple[tuple[int, int], ...], ...]:
    raw_pair = term.get("pair")
    require(isinstance(raw_pair, list) and len(raw_pair) == 2, "malformed pair")
    branches: list[tuple[tuple[int, int], ...]] = []
    for raw_branch in raw_pair:
        require(isinstance(raw_branch, list), "malformed branch")
        branch: list[tuple[int, int]] = []
        for raw_edge in raw_branch:
            require(isinstance(raw_edge, list) and len(raw_edge) == 2, "malformed edge")
            u, v = map(int, raw_edge)
            require(1 <= u <= v <= n, "edge endpoint outside certificate dimension")
            branch.append((u - 1, v - 1))
        branches.append(tuple(branch))
    require(len(branches[0]) == len(branches[1]), "unequal branch sizes")
    return tuple(branches)


def pair_atom_value(
    pair: tuple[tuple[tuple[int, int], ...], ...], x: Sequence[Fraction]
) -> Fraction:
    values = []
    for branch in pair:
        values.append(sum((max(x[u], x[v]) for u, v in branch), Fraction(0)))
    return max(values)


def pair_support(pair: tuple[tuple[tuple[int, int], ...], ...]) -> set[int]:
    return {endpoint for branch in pair for edge in branch for endpoint in edge}


def certificate_charge_summary(
    document: dict[str, Any], path: Path, expected_sha256: str | None
) -> dict[str, Any]:
    n = int(document.get("n", -1))
    require(n >= 2, "invalid certificate arity")
    if expected_sha256 is not None:
        require(sha256(path) == expected_sha256, f"certificate_{n} digest drift")
    terms = document.get("terms")
    require(isinstance(terms, list) and terms, "certificate has no terms")

    weighted_seed_charge = Fraction(0)
    nonzero_charge_terms = 0
    full_support_terms = 0
    proper_support_terms = 0
    charge_histogram: dict[int, int] = {}
    parsed: list[tuple[dict[str, Any], int]] = []
    for term in terms:
        require(isinstance(term, dict), "certificate term is not an object")
        coefficient = Fraction(str(term.get("coefficient")))
        pair = parse_pair(term, n)
        support = pair_support(pair)
        charge = boolean_mobius_charge(n, lambda x, pair=pair: pair_atom_value(pair, x))
        require(charge.denominator == 1, "integer pair atom acquired fractional charge")
        charge_integer = int(charge)
        parsed.append((term, charge_integer))
        charge_histogram[charge_integer] = charge_histogram.get(charge_integer, 0) + 1
        weighted_seed_charge += coefficient * charge
        if len(support) == n:
            full_support_terms += 1
        else:
            proper_support_terms += 1
            require(charge == 0, "proper-support certificate atom has nonzero full charge")
        if charge:
            nonzero_charge_terms += 1
            require(len(support) == n, "charged certificate atom lacks full support")

    target_charge = max_charge(n)
    symmetrized_charge = math.factorial(n) * weighted_seed_charge
    require(
        symmetrized_charge == target_charge == Fraction((-1) ** (n + 1)),
        f"certificate_{n} charge conservation failed",
    )
    return {
        "n": n,
        "sha256": expected_sha256 or sha256(path),
        "terms": len(terms),
        "full_support_terms": full_support_terms,
        "proper_support_terms": proper_support_terms,
        "nonzero_charge_terms": nonzero_charge_terms,
        "seed_charge_histogram": {str(key): value for key, value in sorted(charge_histogram.items())},
        "weighted_seed_charge": str(weighted_seed_charge),
        "full_symmetrization_factor": math.factorial(n),
        "symmetrized_certificate_charge": str(symmetrized_charge),
        "target_charge": str(target_charge),
        "_parsed": parsed,
    }


def certificate_calibrations() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    summaries: list[dict[str, Any]] = []
    documents: dict[int, tuple[dict[str, Any], Path]] = {}
    for n, expected_hash in EXPECTED_CERTIFICATE_SHA256.items():
        suffix = 2 if n in (5, 6) else 3 if n in (7, 8) else 4
        path = CERTIFICATE_DIR / f"certificate_{n}_{suffix}.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        summary = certificate_charge_summary(document, path, expected_hash)
        summary.pop("_parsed")
        summaries.append(summary)
        documents[n] = (document, path)

    # Hostile control: perturb the coefficient of a charged MAX5 term.  The
    # necessary charge identity must fail even though the JSON remains shaped.
    original, path = documents[5]
    mutated = copy.deepcopy(original)
    pristine = certificate_charge_summary(original, path, EXPECTED_CERTIFICATE_SHA256[5])
    charged_index = next(
        index for index, (_, charge) in enumerate(pristine["_parsed"]) if charge != 0
    )
    old = Fraction(str(mutated["terms"][charged_index]["coefficient"]))
    mutated["terms"][charged_index]["coefficient"] = str(old + Fraction(1, 120))
    rejected = False
    try:
        certificate_charge_summary(mutated, path, None)
    except AuditFailure:
        rejected = True
    require(rejected, "charged coefficient mutation escaped conservation check")
    return summaries, {
        "max5_charged_coefficient_mutation_rejected": True,
        "mutated_term_index": charged_index,
    }


def run_audit() -> dict[str, Any]:
    target_charges = {str(n): str(max_charge(n)) for n in range(2, 12)}
    require(target_charges["11"] == "1", "MAX11 charge is not one")
    certificates, hostile = certificate_calibrations()
    return {
        "schema": "g0060-boolean-mobius-ancestry-controls-v1",
        "arithmetic": "integers and fractions.Fraction",
        "max_target_charges_n2_through_n11": target_charges,
        "max11_cube_vertices": 1 << 11,
        "max3_exact_network_calibration": max3_calibration(),
        "biased_and_dense_controls": biased_and_dense_controls(),
        "pinned_certificate_calibrations": certificates,
        "hostile_controls": hostile,
        "result": "PASS",
        "claim_boundary": (
            "These exact finite controls calibrate a necessary Boolean interaction invariant. "
            "They do not prove the universal theorem, construct MAX11, bound dense networks, "
            "or certify the MAX5-MAX10 identities globally."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check-report",
        type=Path,
        help="require exact equality with a frozen JSON report",
    )
    args = parser.parse_args()
    report = run_audit()
    if args.check_report is not None:
        frozen = json.loads(args.check_report.read_text(encoding="utf-8"))
        require(report == frozen, "frozen report differs from exact replay")
    print(json.dumps(report, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
