#!/usr/bin/env python3
"""Independent lattice-point falsifier for symmetric max-certificates.

METHOD (deliberately disjoint from the upstream ordered-cone verifier and from
``tools/verify11``): evaluate both sides of the claimed identity

    sum_t  c_t * sum_{sigma in S_n} atom_t(x_{sigma(1)}, ..., x_{sigma(n)})
        ==  max(x_1, ..., x_n)

pointwise and exactly at every lattice point of ``{0,1}^n`` and ``{0,1,2}^n``.
No cone normal form, no summation-by-parts, no hinge bookkeeping, no dynamic
program over vertex placements is used anywhere in this file.

The atom of a term is, following the pinned upstream verifier,

    atom(x) = max( sum_{(a,b) in left}  max(x_a, x_b),
                   sum_{(a,b) in right} max(x_a, x_b) ).

Both sides of the identity are symmetric, so a point is fully described by the
multiset of its coordinate values.  For ``{0,1}^n`` there are ``n+1`` such value
profiles, for ``{0,1,2}^n`` there are ``C(n+2,2)``; checking the profiles checks
all ``2^n`` resp. ``3^n`` points.

A term touches only its active vertex set ``V`` (``v = |V|``).  Since the atom
ignores the other coordinates,

    sum_{sigma in S_n} atom(x_sigma) = (n-v)! * sum_{phi: V -> [n] injective} atom(x_phi)

and, at a profile with multiplicities ``m_0, m_1, m_2``, the number of injective
placements realising a given value pattern ``p: V -> {0,1,2}`` is the product of
falling factorials ``prod_j (m_j)_{c_j(p)}`` where ``c_j(p)`` counts the active
vertices that pattern ``p`` sends to value ``j``.  Patterns are therefore only
needed grouped by their count vector, which is what this tool computes: the
``B^v`` patterns are enumerated with numpy, bucketed exactly by (count vector,
atom value) with ``np.bincount``, and contracted against an exact integer
placement matrix.  All accumulation is exact (Python integers and
``fractions.Fraction``); no floating point value ever enters a comparison.

Agreement on lattice points falsifies but does not prove the identity; this
tool is a referee-side check, not a certificate verifier.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import sys
import time
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

import numpy as np

TOOL_NAME = "t2-referee/lattice_check.py"
TOOL_VERSION = "1.0.0"

# Enumerate patterns in chunks so that a large active set cannot blow memory.
PATTERN_CHUNK = 1 << 20
# Bound past which int64 contraction is refused in favour of Python integers.
INT64_SAFE = 1 << 62


# --------------------------------------------------------------------------
# certificate loading / validation
# --------------------------------------------------------------------------


class CertificateError(ValueError):
    """The certificate file does not conform to the upstream schema."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_side(raw_side: Iterable[Sequence[int]], n: int, unsorted_seen: list[bool]):
    """Convert one branch to 0-indexed endpoint pairs.

    Upstream requires ``1 <= a <= b <= n``.  ``max(x_a, x_b)`` is symmetric, so
    an unsorted pair is semantically harmless; it is normalised here and the
    fact is recorded in the report rather than rejected.
    """
    side = []
    for raw_pair in raw_side:
        pair = tuple(raw_pair)
        if len(pair) != 2:
            raise CertificateError("each endpoint pair must contain exactly two endpoints")
        a, b = int(pair[0]), int(pair[1])
        if not (1 <= a <= n and 1 <= b <= n):
            raise CertificateError(f"invalid endpoint pair {(a, b)} for n={n}")
        if a > b:
            unsorted_seen[0] = True
            a, b = b, a
        side.append((a - 1, b - 1))
    return tuple(side)


def parse_term(term: dict, n: int, unsorted_seen: list[bool]):
    """Return ``(coefficient, left, right)`` for one certificate term."""
    coefficient = Fraction(term["coefficient"])
    if not coefficient:
        return coefficient, None, None
    sides = tuple(term["pair"])
    if len(sides) != 2:
        raise CertificateError("each term must contain exactly two sides")
    left = _read_side(sides[0], n, unsorted_seen)
    right = _read_side(sides[1], n, unsorted_seen)
    if len(left) != len(right):
        raise CertificateError("the two sides of a pair must have the same size")
    return coefficient, left, right


def load_certificate(path: Path) -> dict:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if "n" not in data or "terms" not in data:
        raise CertificateError("certificate must define 'n' and 'terms'")
    n = int(data["n"])
    if n < 1:
        raise CertificateError("n must be positive")
    return {"n": n, "terms": data["terms"]}


# --------------------------------------------------------------------------
# profiles, falling factorials, placement matrices
# --------------------------------------------------------------------------


def profiles_for(n: int, base: int) -> list[tuple[int, ...]]:
    """Value-multiplicity profiles of ``{0,...,base-1}^n``, canonical order.

    Order for base 3 is ``m2`` ascending, then ``m1`` ascending; for base 2 it
    is ``m1`` ascending.  ``m0`` is determined.  The order fixes what "first
    failing profile" means.
    """
    if base == 2:
        return [(n - m1, m1) for m1 in range(n + 1)]
    if base == 3:
        out = []
        for m2 in range(n + 1):
            for m1 in range(n - m2 + 1):
                out.append((n - m1 - m2, m1, m2))
        return out
    raise ValueError("base must be 2 or 3")


def falling(m: int, c: int) -> int:
    if c > m:
        return 0
    result = 1
    for i in range(c):
        result *= m - i
    return result


def count_classes(v: int, base: int) -> int:
    return (v + 1) if base == 2 else (v + 1) * (v + 1)


def placement_matrix(n: int, v: int, base: int) -> np.ndarray:
    """Exact injective-placement counts, shape ``(#profiles, #count classes)``.

    Entry ``[p, idx]`` is the number of injections from the ``v`` active
    vertices into the ``n`` coordinates of a point with profile ``p`` that
    realise count class ``idx``.
    """
    profs = profiles_for(n, base)
    ncls = count_classes(v, base)
    matrix = np.zeros((len(profs), ncls), dtype=np.int64)
    for row, prof in enumerate(profs):
        if base == 2:
            m0, m1 = prof
            for c1 in range(v + 1):
                matrix[row, c1] = falling(m0, v - c1) * falling(m1, c1)
        else:
            m0, m1, m2 = prof
            for c1 in range(v + 1):
                for c2 in range(v + 1 - c1):
                    matrix[row, c1 * (v + 1) + c2] = (
                        falling(m0, v - c1 - c2) * falling(m1, c1) * falling(m2, c2)
                    )
    return matrix


# --------------------------------------------------------------------------
# per-structure atom tables
# --------------------------------------------------------------------------


def canonical_structure(left, right):
    """Relabel active vertices to 0..v-1 and orient the unordered branch pair.

    Two terms with the same key have identical atom tables, which is all the
    cache needs (the map need not separate all non-isomorphic terms).
    """
    active = sorted({a for e in left + right for a in e})
    index = {label: i for i, label in enumerate(active)}
    cl = tuple(sorted((index[a], index[b]) for a, b in left))
    cr = tuple(sorted((index[a], index[b]) for a, b in right))
    lo, hi = (cl, cr) if cl <= cr else (cr, cl)
    return len(active), lo, hi


def atom_table(v: int, left, right, base: int) -> np.ndarray:
    """Sum of the atom over every pattern in each count class.

    Returns an exact int64 vector indexed by count class.  ``left``/``right``
    are given in relabelled 0..v-1 coordinates.
    """
    edges_l = np.asarray(left, dtype=np.int64).reshape(-1, 2)
    edges_r = np.asarray(right, dtype=np.int64).reshape(-1, 2)
    k = edges_l.shape[0]
    max_atom = (base - 1) * k
    ncls = count_classes(v, base)
    stride = max_atom + 1
    hist = np.zeros(ncls * stride, dtype=np.int64)

    total = base**v
    powers = base ** np.arange(v, dtype=np.int64)
    for start in range(0, total, PATTERN_CHUNK):
        stop = min(start + PATTERN_CHUNK, total)
        codes = np.arange(start, stop, dtype=np.int64)
        pattern = ((codes[:, None] // powers[None, :]) % base).astype(np.int16)

        left_sum = np.zeros(stop - start, dtype=np.int32)
        for a, b in edges_l:
            left_sum += np.maximum(pattern[:, a], pattern[:, b])
        right_sum = np.zeros(stop - start, dtype=np.int32)
        for a, b in edges_r:
            right_sum += np.maximum(pattern[:, a], pattern[:, b])
        atom = np.maximum(left_sum, right_sum).astype(np.int64)

        if base == 2:
            cls = pattern.sum(axis=1).astype(np.int64)
        else:
            c1 = (pattern == 1).sum(axis=1).astype(np.int64)
            c2 = (pattern == 2).sum(axis=1).astype(np.int64)
            cls = c1 * (v + 1) + c2

        hist += np.bincount(cls * stride + atom, minlength=ncls * stride)

    weights = np.arange(stride, dtype=np.int64)
    return hist.reshape(ncls, stride) @ weights


def structure_weights(
    n: int, left, right, base: int, matrix_cache: dict
) -> tuple[list[int], int]:
    """Per-profile symmetrized value of one term, as exact integers.

    Returns ``(weights, scale)`` with ``weights[p] * scale`` equal to
    ``sum_{sigma in S_n} atom(x_sigma)`` at profile ``p``; ``scale`` is
    ``(n-v)!`` for the ``v`` active vertices of the term.
    """
    v, cl, cr = canonical_structure(left, right)
    table = atom_table(v, cl, cr, base)
    key = (n, v, base)
    matrix = matrix_cache.get(key)
    if matrix is None:
        matrix = placement_matrix(n, v, base)
        matrix_cache[key] = matrix

    # int64 is used only where an a-priori bound proves it cannot overflow.
    bound = int(table.max(initial=0)) * int(matrix.max(initial=0)) * table.size
    if bound >= INT64_SAFE:  # pragma: no cover - unreachable for n <= 14
        rows = matrix.tolist()
        column = table.tolist()
        weights = [sum(a * b for a, b in zip(row, column)) for row in rows]
    else:
        weights = (matrix @ table).tolist()
    return weights, math.factorial(n - v)


# --------------------------------------------------------------------------
# worker
# --------------------------------------------------------------------------


def _accumulate(terms: list, n: int, bases: tuple[int, ...]) -> dict:
    """Sum a chunk of terms into ``{base: {denominator: [numerators]}}``."""
    matrix_cache: dict = {}
    table_cache: dict = {}
    unsorted_seen = [False]
    acc: dict[int, dict[int, list[int]]] = {base: {} for base in bases}
    nprofiles = {base: len(profiles_for(n, base)) for base in bases}
    nonzero = 0

    for term in terms:
        coefficient, left, right = parse_term(term, n, unsorted_seen)
        if left is None:
            continue
        nonzero += 1
        num = coefficient.numerator
        den = coefficient.denominator
        for base in bases:
            key = (canonical_structure(left, right), base)
            cached = table_cache.get(key)
            if cached is None:
                cached = structure_weights(n, left, right, base, matrix_cache)
                table_cache[key] = cached
            weights, scale = cached
            bucket = acc[base].get(den)
            if bucket is None:
                bucket = [0] * nprofiles[base]
                acc[base][den] = bucket
            factor = num * scale
            for i, w in enumerate(weights):
                if w:
                    bucket[i] += factor * w

    return {"acc": acc, "unsorted": unsorted_seen[0], "nonzero": nonzero}


def _worker(payload):
    terms, n, bases = payload
    return _accumulate(terms, n, bases)


# --------------------------------------------------------------------------
# driver
# --------------------------------------------------------------------------


def target_value(profile: Sequence[int]) -> int:
    """``max(x)`` at a profile: the largest value with nonzero multiplicity."""
    for value in range(len(profile) - 1, -1, -1):
        if profile[value]:
            return value
    raise AssertionError("empty profile")


def merge_denominator_groups(items: list[tuple[int, list[int]]]) -> tuple[int, list[int]]:
    """Put every profile column over one exact common denominator.

    ``items`` pairs a denominator with the vector of integer numerators it
    carries, one entry per profile.  All profiles share the same denominator
    set, so the expensive gcd work is done once for the whole vector instead of
    once per profile.  Combination is pairwise so operand sizes stay balanced.
    """
    if not items:
        return 1, []
    if len(items) == 1:
        return items[0]
    mid = len(items) // 2
    den_a, num_a = merge_denominator_groups(items[:mid])
    den_b, num_b = merge_denominator_groups(items[mid:])
    if den_a == den_b:
        return den_a, [a + b for a, b in zip(num_a, num_b)]
    common = math.gcd(den_a, den_b)
    scale_a = den_b // common
    scale_b = den_a // common
    return den_a * scale_a, [a * scale_a + b * scale_b for a, b in zip(num_a, num_b)]


def _int_digest(value: int) -> str:
    """SHA-256 of an integer's exact two's-complement big-endian encoding."""
    width = value.bit_length() // 8 + 2
    return hashlib.sha256(value.to_bytes(width, "big", signed=True)).hexdigest()


def render_ratio(num: int, den: int, max_chars: int) -> object:
    """Render ``num/den`` exactly, or as a verifiable digest when enormous.

    The fraction is reduced only when its operands are small enough that the
    gcd is cheap.  On a failing certificate with thousands of distinct
    coefficient denominators the common denominator has millions of bits, and
    both reducing it and converting it to decimal are pointless work for a
    referee who only needs to know that the two sides differ.
    """
    approx_digits = (num.bit_length() + den.bit_length()) // 3 + 3
    if approx_digits <= max_chars:
        if max_chars + 128 > 4300:
            sys.set_int_max_str_digits(max_chars + 128)
        value = Fraction(num, den)
        return str(value)
    return {
        "truncated": True,
        "reason": (
            f"exact value needs about {approx_digits} characters, "
            "over --max-value-chars"
        ),
        "reduced": False,
        "numerator_bits": num.bit_length(),
        "denominator_bits": den.bit_length(),
        "sign": (num > 0) - (num < 0),
        "sha256_of_exact_numerator": _int_digest(num),
        "sha256_of_exact_denominator": _int_digest(den),
    }


def short(value: object, width: int = 88) -> str:
    """One-line console rendering of a possibly enormous exact value."""
    if isinstance(value, dict):
        return (
            f"<unreduced {value['numerator_bits']}-bit / "
            f"{value['denominator_bits']}-bit rational, sign {value['sign']}, "
            f"numerator sha256 {value['sha256_of_exact_numerator'][:16]}>"
        )
    if len(value) <= width:
        return value
    return f"{value[: width // 2]}...{value[-width // 2 :]} ({len(value)} chars)"


def check_certificate(
    path: Path,
    bases: tuple[int, ...] = (2, 3),
    processes: int = 4,
    max_value_chars: int = 4000,
) -> dict:
    path = Path(path)
    started = time.time()
    certificate = load_certificate(path)
    n = certificate["n"]
    terms = certificate["terms"]

    processes = max(1, int(processes))
    if processes > 1 and len(terms) > 1:
        chunk = max(1, math.ceil(len(terms) / (processes * 4)))
        chunks = [terms[i : i + chunk] for i in range(0, len(terms), chunk)]
        import multiprocessing as mp

        context = mp.get_context("fork" if sys.platform != "win32" else "spawn")
        with context.Pool(processes) as pool:
            partials = pool.map(_worker, [(c, n, bases) for c in chunks])
    else:
        partials = [_accumulate(terms, n, bases)]

    unsorted_seen = any(part["unsorted"] for part in partials)
    nonzero_terms = sum(part["nonzero"] for part in partials)

    results = {}
    all_pass = True
    for base in bases:
        merged: dict[int, list[int]] = {}
        for part in partials:
            for den, nums in part["acc"][base].items():
                bucket = merged.get(den)
                if bucket is None:
                    merged[den] = list(nums)
                else:
                    for i, value in enumerate(nums):
                        bucket[i] += value
        profs = profiles_for(n, base)
        common_den, numerators = merge_denominator_groups(sorted(merged.items()))
        if not numerators:
            numerators = [0] * len(profs)
        failing = [
            i
            for i, prof in enumerate(profs)
            # Exact comparison without reducing the fraction: num/den == t
            # exactly when num == t * den, and den > 0 always.
            if numerators[i] != target_value(prof) * common_den
        ]
        # Only the first failure is rendered: reducing a fraction whose
        # denominator is the common multiple of thousands of coefficients is
        # expensive, and the remaining failures add nothing a referee needs.
        first_failure = None
        if failing:
            i = failing[0]
            rhs_int = target_value(profs[i])
            first_failure = {
                "profile_multiplicities": list(profs[i]),
                "profile_index": i,
                "certificate_value": render_ratio(numerators[i], common_den, max_value_chars),
                "target_value": str(rhs_int),
                "difference": render_ratio(
                    numerators[i] - rhs_int * common_den, common_den, max_value_chars
                ),
            }
        verdict = "PASS" if not failing else "FAIL"
        all_pass = all_pass and not failing
        results[f"{{0..{base - 1}}}^n"] = {
            "base": base,
            "profiles_checked": len(profs),
            "lattice_points_covered": base**n,
            "failing_profiles": len(failing),
            "failing_profile_indices": failing,
            "distinct_coefficient_denominators": len(merged),
            "common_denominator_bits": common_den.bit_length(),
            "verdict": verdict,
            "first_failure": first_failure,
        }

    elapsed = time.time() - started
    return {
        "tool": TOOL_NAME,
        "tool_version": TOOL_VERSION,
        "certificate_path": str(path),
        "certificate_sha256": sha256_file(path),
        "n": n,
        "terms": len(terms),
        "nonzero_terms": nonzero_terms,
        "unsorted_endpoint_pairs_normalised": unsorted_seen,
        "processes": processes,
        "bases": list(bases),
        "profiles_checked": sum(r["profiles_checked"] for r in results.values()),
        "lattice_points_covered": sum(r["lattice_points_covered"] for r in results.values()),
        "per_base": results,
        "verdict": "PASS" if all_pass else "FAIL",
        "wall_seconds": round(elapsed, 3),
        "no_claim": (
            "Agreement on lattice points falsifies but does not prove the identity; "
            "this tool is a referee-side check, not a certificate verifier."
        ),
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("certificate", type=Path)
    parser.add_argument(
        "--profiles",
        choices=["01", "012", "both"],
        default="both",
        help="lattice to check: {0,1}^n, {0,1,2}^n, or both (default)",
    )
    parser.add_argument("--processes", type=int, default=4)
    parser.add_argument(
        "--max-value-chars",
        type=int,
        default=4000,
        help="failure values longer than this are stored as a digest record",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="write the JSON report here; refuses to overwrite an existing file",
    )
    args = parser.parse_args(argv)

    if args.output is not None and args.output.exists():
        print(f"refusing to overwrite existing output {args.output}", file=sys.stderr)
        return 2

    bases = {"01": (2,), "012": (3,), "both": (2, 3)}[args.profiles]
    report = check_certificate(
        args.certificate,
        bases=bases,
        processes=args.processes,
        max_value_chars=args.max_value_chars,
    )

    print(f"certificate     : {report['certificate_path']}")
    print(f"sha256          : {report['certificate_sha256']}")
    print(f"n               : {report['n']}   terms: {report['terms']}")
    print(f"profiles checked: {report['profiles_checked']}")
    print(f"lattice points  : {report['lattice_points_covered']}")
    print(f"wall seconds    : {report['wall_seconds']}")
    for name, entry in report["per_base"].items():
        print(f"  {name:<10} {entry['verdict']}  ({entry['failing_profiles']} failing profiles)")
        failure = entry["first_failure"]
        if failure is not None:
            print(f"    first failure at multiplicities {failure['profile_multiplicities']}")
            print(f"      certificate = {short(failure['certificate_value'])}")
            print(f"      target      = {failure['target_value']}")
    print(f"VERDICT         : {report['verdict']}")

    if args.output is not None:
        with open(args.output, "x", encoding="utf-8") as handle:
            json.dump(report, handle, indent=2, sort_keys=True)
            handle.write("\n")
        print(f"report written  : {args.output}")

    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
