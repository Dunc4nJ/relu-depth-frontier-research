"""Exact ordered-cone accumulator for symmetrized MAX certificates."""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from fractions import Fraction
import hashlib
from itertools import permutations
import json
from math import factorial, gcd, lcm
import re

from .model import Certificate, Side, Term


class VerificationInputError(ValueError):
    """The verifier invocation, rather than the certificate, is malformed."""


_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_SUBJECT_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,127}\Z")


def _validate_side_object(
    side: object, n: int, expected_k: int | None, location: str
) -> None:
    if type(side) is not tuple:
        raise VerificationInputError(f"{location} must be an exact tuple")
    if expected_k is not None and len(side) != expected_k:
        raise VerificationInputError(
            f"{location} has length {len(side)}; certificate k={expected_k}"
        )
    if not side:
        raise VerificationInputError(f"{location} must be nonempty")
    for pair_index, pair in enumerate(side):
        pair_location = f"{location}[{pair_index}]"
        if type(pair) is not tuple or len(pair) != 2:
            raise VerificationInputError(
                f"{pair_location} must be an exact two-integer tuple"
            )
        a, b = pair
        if type(a) is not int or type(b) is not int:
            raise VerificationInputError(
                f"{pair_location} endpoints must be genuine integers"
            )
        if not (1 <= a <= b <= n):
            raise VerificationInputError(
                f"{pair_location} must satisfy 1 <= a <= b <= n"
            )


def _validate_certificate_object(certificate: object) -> Certificate:
    """Validate the entire public dataclass boundary before any arithmetic."""

    if type(certificate) is not Certificate:
        raise VerificationInputError("certificate must be an exact Certificate object")
    if (
        type(certificate.subject_id) is not str
        or _SUBJECT_ID_RE.fullmatch(certificate.subject_id) is None
    ):
        raise VerificationInputError("certificate subject_id has an invalid shape")
    for field_name in ("raw_sha256", "normalized_sha256"):
        digest = getattr(certificate, field_name)
        if type(digest) is not str or _SHA256_RE.fullmatch(digest) is None:
            raise VerificationInputError(
                f"certificate {field_name} must be a lowercase SHA-256 digest"
            )
    if type(certificate.n) is not int or certificate.n <= 0:
        raise VerificationInputError("certificate n must be a positive genuine integer")
    if type(certificate.k) is not int or certificate.k <= 0:
        raise VerificationInputError("certificate k must be a positive genuine integer")
    if type(certificate.term_count) is not int or certificate.term_count <= 0:
        raise VerificationInputError(
            "certificate term_count must be a positive genuine integer"
        )
    if type(certificate.terms) is not tuple or not certificate.terms:
        raise VerificationInputError(
            "certificate terms must be a nonempty exact tuple (positive term count)"
        )
    if len(certificate.terms) != certificate.term_count:
        raise VerificationInputError(
            "certificate term_count does not equal the number of terms"
        )
    for term_index, term in enumerate(certificate.terms):
        location = f"certificate.terms[{term_index}]"
        if type(term) is not Term:
            raise VerificationInputError(f"{location} must be an exact Term object")
        if type(term.coefficient) is not Fraction or term.coefficient == 0:
            raise VerificationInputError(
                f"{location}.coefficient must be a nonzero exact Fraction"
            )
        _validate_side_object(
            term.left, certificate.n, certificate.k, f"{location}.left"
        )
        _validate_side_object(
            term.right, certificate.n, certificate.k, f"{location}.right"
        )
        if len(term.left) != len(term.right):
            raise VerificationInputError(f"{location} side lengths differ")
    return certificate


@dataclass(frozen=True)
class CanonicalHinge:
    direction: tuple[int, ...]
    magnitude: int
    flipped: bool


@dataclass(frozen=True)
class TermCensus:
    term_index: int
    schedule_kind: str
    expected: int
    observed: int
    unique: int
    missing: int
    duplicates: int
    coverage_sha256: str
    duplicate_multiset_sha256: str
    schedule_identity_sha256: str

    @property
    def complete(self) -> bool:
        return (
            self.observed == self.expected
            and self.unique == self.expected
            and self.missing == 0
            and self.duplicates == 0
        )

    def payload(self) -> dict[str, object]:
        return {
            "term_index": self.term_index,
            "schedule_kind": self.schedule_kind,
            "expected": self.expected,
            "observed": self.observed,
            "unique": self.unique,
            "missing": self.missing,
            "duplicates": self.duplicates,
            "coverage_sha256": self.coverage_sha256,
            "duplicate_multiset_sha256": self.duplicate_multiset_sha256,
            "schedule_identity_sha256": self.schedule_identity_sha256,
            "complete": self.complete,
        }


@dataclass(frozen=True)
class Census:
    expected_terms: int
    processed_terms: int
    permutations_per_term: int
    expected_contributions: int
    observed_contributions: int
    unique_contributions: int
    missing_contributions: int
    duplicate_contributions: int
    terms: tuple[TermCensus, ...]

    @property
    def complete(self) -> bool:
        return (
            self.processed_terms == self.expected_terms
            and self.observed_contributions == self.expected_contributions
            and self.unique_contributions == self.expected_contributions
            and self.missing_contributions == 0
            and self.duplicate_contributions == 0
            and all(term.complete for term in self.terms)
        )

    def payload(self) -> dict[str, object]:
        return {
            "expected_terms": self.expected_terms,
            "processed_terms": self.processed_terms,
            "permutations_per_term": self.permutations_per_term,
            "expected_contributions": self.expected_contributions,
            "observed_contributions": self.observed_contributions,
            "unique_contributions": self.unique_contributions,
            "missing_contributions": self.missing_contributions,
            "duplicate_contributions": self.duplicate_contributions,
            "complete": self.complete,
            "terms": [term.payload() for term in self.terms],
        }


@dataclass(frozen=True)
class Residual:
    linear: tuple[int, ...]
    target: tuple[int, ...]
    linear_minus_target: tuple[int, ...]
    hinges: tuple[tuple[tuple[int, ...], int], ...]

    @property
    def hinge_zero(self) -> bool:
        return not self.hinges

    @property
    def target_matched(self) -> bool:
        return all(value == 0 for value in self.linear_minus_target)

    def payload(self) -> dict[str, object]:
        return {
            "linear": list(self.linear),
            "target": list(self.target),
            "linear_minus_target": list(self.linear_minus_target),
            "hinges": [
                {"direction": list(direction), "coefficient": coefficient}
                for direction, coefficient in self.hinges
            ],
            "hinge_zero": self.hinge_zero,
            "target_matched": self.target_matched,
        }


@dataclass(frozen=True)
class VerificationResult:
    subject_id: str
    input_raw_sha256: str
    input_normalized_sha256: str
    n: int
    integer_scale: int
    target_scale: Fraction
    residual: Residual
    census: Census
    symmetrization_transport_checked: bool
    execution_complete: bool
    failure_reasons: tuple[str, ...]

    @property
    def incomplete(self) -> bool:
        return (
            not self.execution_complete
            or not self.census.complete
            or not self.symmetrization_transport_checked
        )

    @property
    def accepted(self) -> bool:
        return (
            not self.incomplete
            and self.residual.hinge_zero
            and self.residual.target_matched
            and not self.failure_reasons
        )

    @property
    def outcome(self) -> str:
        if self.incomplete:
            return "INCOMPLETE"
        return "ACCEPT" if self.accepted else "REJECT"

    @property
    def verdict(self) -> str:
        """Backward-compatible name for the typed subject outcome."""

        return self.outcome

    @property
    def cannot_verify(self) -> bool:
        return self.outcome == "INCOMPLETE"

    def payload(self) -> dict[str, object]:
        target_scale = (
            str(self.target_scale.numerator)
            if self.target_scale.denominator == 1
            else f"{self.target_scale.numerator}/{self.target_scale.denominator}"
        )
        return {
            "schema": "maxrelu-cleanroom-residual-v2",
            "subject_id": self.subject_id,
            "input_raw_sha256": self.input_raw_sha256,
            "input_normalized_sha256": self.input_normalized_sha256,
            "n": self.n,
            "integer_scale": self.integer_scale,
            "target_scale": target_scale,
            "execution_complete": self.execution_complete,
            "symmetrization_transport_checked": self.symmetrization_transport_checked,
            "census": self.census.payload(),
            "residual": self.residual.payload(),
            "failure_reasons": list(self.failure_reasons),
            "outcome": self.outcome,
            "cannot_verify": self.cannot_verify,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.payload(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        ).encode("ascii")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def side_linear_form(side: Side, permutation: Sequence[int], n: int) -> tuple[int, ...]:
    """Convert a labelled side to its linear form on ``x1 <= ... <= xn``.

    ``permutation[label-1]`` is the zero-based ordered-coordinate rank assigned
    to that label.  Enumerating every such tuple is the same inverse-permutation
    convention used in the symmetrization formula.
    """

    if type(n) is not int or n <= 0:
        raise VerificationInputError("n must be a positive genuine integer")
    _validate_side_object(side, n, None, "side")
    if (
        len(permutation) != n
        or any(type(value) is not int for value in permutation)
        or set(permutation) != set(range(n))
    ):
        raise VerificationInputError("permutation is not a bijection of range(n)")
    linear = [0] * n
    for a, b in side:
        coordinate = max(permutation[a - 1], permutation[b - 1])
        linear[coordinate] += 1
    return tuple(linear)


def ordered_cone_sign(direction: Sequence[int]) -> str:
    """Classify an exact linear form on the full ordered cone.

    Equal-cardinality sides make the coefficient sum zero.  Writing
    ``x[i+1] = x[i] + gap[i]`` shows that the gap coefficients are the
    negatives of the proper prefix sums.  Their signs decide whether the form
    is nonnegative, nonpositive, zero, or genuinely mixed on the cone.
    """

    if not direction:
        raise VerificationInputError("direction must be nonempty")
    if any(type(value) is not int for value in direction):
        raise VerificationInputError("direction entries must be genuine integers")
    if sum(direction) != 0:
        return "mixed"
    if all(value == 0 for value in direction):
        return "zero"
    prefix = 0
    gap_coefficients: list[int] = []
    for value in direction[:-1]:
        prefix += value
        gap_coefficients.append(-prefix)
    if all(value >= 0 for value in gap_coefficients):
        return "nonnegative"
    if all(value <= 0 for value in gap_coefficients):
        return "nonpositive"
    return "mixed"


def canonicalize_hinge(direction: Sequence[int]) -> CanonicalHinge:
    """Primitive positive orientation of a nonzero integer hinge direction."""

    if not direction or any(type(value) is not int for value in direction):
        raise VerificationInputError("hinge direction must be nonempty genuine integers")
    magnitude = 0
    for value in direction:
        magnitude = gcd(magnitude, abs(value))
    if magnitude == 0:
        raise VerificationInputError("zero direction has no hinge orientation")
    first = next(value for value in direction if value != 0)
    flipped = first < 0
    sign = -1 if flipped else 1
    primitive = tuple(sign * value // magnitude for value in direction)
    return CanonicalHinge(primitive, magnitude, flipped)


def _integer_target_scale(value: Fraction | int) -> Fraction:
    if type(value) is int:
        result = Fraction(value, 1)
    elif type(value) is Fraction:
        result = value
    else:
        raise VerificationInputError("target_scale must be Fraction or genuine integer")
    if result <= 0:
        raise VerificationInputError("target_scale must be positive")
    return result


def _permutation_from_rank(n: int, rank: int) -> tuple[int, ...]:
    values = list(range(n))
    result: list[int] = []
    remainder = rank
    for width in range(n, 0, -1):
        block = factorial(width - 1)
        index, remainder = divmod(remainder, block)
        result.append(values.pop(index))
    return tuple(result)


def _ranked_permutations(
    n: int, plan: Iterable[int] | None
) -> Iterable[tuple[int, tuple[int, ...]]]:
    permutation_count = factorial(n)
    if plan is None:
        yield from enumerate(permutations(range(n)))
        return
    for rank in plan:
        if type(rank) is not int:
            raise VerificationInputError("contribution rank must be a genuine integer")
        if not (0 <= rank < permutation_count):
            raise VerificationInputError(
                f"contribution rank {rank} outside [0, {permutation_count})"
            )
        yield rank, _permutation_from_rank(n, rank)


def _schedule_digests(
    *,
    schedule_kind: str,
    expected: int,
    coverage: bytearray,
    duplicate_extras: Mapping[int, int],
) -> tuple[str, str, str]:
    """Bind coverage and duplicate identities with one hash per term.

    The verifier already maintains the compact coverage bitset for exact census
    accounting.  Hashing it once costs O(n!/8) bytes per term, rather than a
    cryptographic update for every contribution.  Valid schedules allocate no
    duplicate map; hostile schedules canonically bind only their extra ranks.
    """

    coverage_sha256 = hashlib.sha256(bytes(coverage)).hexdigest()
    duplicate_payload = [
        [rank, extra_count]
        for rank, extra_count in sorted(duplicate_extras.items())
    ]
    duplicate_bytes = json.dumps(
        duplicate_payload, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    duplicate_sha256 = hashlib.sha256(duplicate_bytes).hexdigest()
    identity_bytes = json.dumps(
        {
            "schedule_kind": schedule_kind,
            "expected": expected,
            "coverage_sha256": coverage_sha256,
            "duplicate_multiset_sha256": duplicate_sha256,
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("ascii")
    return (
        coverage_sha256,
        duplicate_sha256,
        hashlib.sha256(identity_bytes).hexdigest(),
    )


def _add_scaled(target: list[int], source: Sequence[int], coefficient: int) -> None:
    for index, value in enumerate(source):
        target[index] += coefficient * value


def verify_certificate(
    certificate: Certificate,
    *,
    target_scale: Fraction | int = 1,
    rank_plans: Mapping[int, Iterable[int]] | None = None,
) -> VerificationResult:
    """Accumulate and decide one certificate using exact integer arithmetic.

    ``rank_plans`` exists for deterministic sharding and planted census controls.
    ``None`` selects the complete lexicographic schedule for every term.  Once an
    explicit mapping is supplied, a missing term key is itself a missing schedule
    and produces a typed ``INCOMPLETE`` result.  A complete result requires every
    rank exactly once for every term.
    """

    certificate = _validate_certificate_object(certificate)
    target_fraction = _integer_target_scale(target_scale)
    if rank_plans is None:
        plans: Mapping[int, Iterable[int]] | None = None
    else:
        if not isinstance(rank_plans, Mapping):
            raise VerificationInputError("rank_plans must be a mapping or None")
        plans = rank_plans
        for key, plan in plans.items():
            if type(key) is not int or not (0 <= key < len(certificate.terms)):
                raise VerificationInputError(f"rank plan has unknown term index: {key!r}")
            if isinstance(plan, (str, bytes)):
                raise VerificationInputError(
                    f"rank plan for term {key} must be an integer iterable"
                )
            try:
                iter(plan)
            except TypeError as exc:
                raise VerificationInputError(
                    f"rank plan for term {key} must be iterable"
                ) from exc

    integer_scale = target_fraction.denominator
    for term in certificate.terms:
        integer_scale = lcm(integer_scale, term.coefficient.denominator)
    integer_coefficients = []
    for term in certificate.terms:
        scaled = term.coefficient * integer_scale
        if scaled.denominator != 1:
            raise AssertionError("denominator LCM did not integerize a coefficient")
        integer_coefficients.append(scaled.numerator)
    target_integer = target_fraction * integer_scale
    if target_integer.denominator != 1:
        raise AssertionError("denominator LCM did not integerize the target")

    n = certificate.n
    permutation_count = factorial(n)
    linear = [0] * n
    hinges: dict[tuple[int, ...], int] = {}
    term_censuses: list[TermCensus] = []

    for term_index, (term, integer_coefficient) in enumerate(
        zip(certificate.terms, integer_coefficients, strict=True)
    ):
        if plans is None:
            plan: Iterable[int] | None = None
            schedule_kind = "complete-lexicographic"
        elif term_index in plans:
            plan = plans[term_index]
            schedule_kind = "explicit-ranks"
        else:
            plan = ()
            schedule_kind = "missing-explicit-plan"
        seen = bytearray((permutation_count + 7) // 8)
        observed = 0
        unique = 0
        duplicates = 0
        duplicate_extras: dict[int, int] = {}
        for rank, permutation in _ranked_permutations(n, plan):
            observed += 1
            byte_index, bit_index = divmod(rank, 8)
            mask = 1 << bit_index
            if seen[byte_index] & mask:
                duplicates += 1
                duplicate_extras[rank] = duplicate_extras.get(rank, 0) + 1
            else:
                seen[byte_index] |= mask
                unique += 1

            left = side_linear_form(term.left, permutation, n)
            right = side_linear_form(term.right, permutation, n)
            direction = tuple(b - a for a, b in zip(left, right, strict=True))
            sign = ordered_cone_sign(direction)
            if sign == "zero" or sign == "nonpositive":
                base = left
                hinge = None
            elif sign == "nonnegative":
                base = right
                hinge = None
            else:
                canonical = canonicalize_hinge(direction)
                if canonical.flipped:
                    # ReLU(-g p) = g ReLU(p) - g p, so the adjusted base is right.
                    base = right
                else:
                    base = left
                hinge = canonical

            _add_scaled(linear, base, integer_coefficient)
            if hinge is not None:
                hinges[hinge.direction] = (
                    hinges.get(hinge.direction, 0)
                    + integer_coefficient * hinge.magnitude
                )

        coverage_digest, duplicate_digest, schedule_digest = _schedule_digests(
            schedule_kind=schedule_kind,
            expected=permutation_count,
            coverage=seen,
            duplicate_extras=duplicate_extras,
        )
        term_censuses.append(
            TermCensus(
                term_index=term_index,
                schedule_kind=schedule_kind,
                expected=permutation_count,
                observed=observed,
                unique=unique,
                missing=permutation_count - unique,
                duplicates=duplicates,
                coverage_sha256=coverage_digest,
                duplicate_multiset_sha256=duplicate_digest,
                schedule_identity_sha256=schedule_digest,
            )
        )

    nonzero_hinges = tuple(
        sorted(
            (direction, coefficient)
            for direction, coefficient in hinges.items()
            if coefficient != 0
        )
    )
    target = [0] * n
    target[-1] = target_integer.numerator
    difference = tuple(a - b for a, b in zip(linear, target, strict=True))
    census = Census(
        expected_terms=len(certificate.terms),
        processed_terms=len(term_censuses),
        permutations_per_term=permutation_count,
        expected_contributions=len(certificate.terms) * permutation_count,
        observed_contributions=sum(item.observed for item in term_censuses),
        unique_contributions=sum(item.unique for item in term_censuses),
        missing_contributions=sum(item.missing for item in term_censuses),
        duplicate_contributions=sum(item.duplicates for item in term_censuses),
        terms=tuple(term_censuses),
    )
    transport_checked = census.complete
    residual = Residual(
        linear=tuple(linear),
        target=tuple(target),
        linear_minus_target=difference,
        hinges=nonzero_hinges,
    )
    failures: list[str] = []
    if not census.complete:
        failures.append("census-incomplete")
    if not transport_checked:
        failures.append("symmetrization-transport-unchecked")
    if not residual.hinge_zero:
        failures.append("hinge-residual-nonzero")
    if not residual.target_matched:
        failures.append("linear-target-mismatch")

    return VerificationResult(
        subject_id=certificate.subject_id,
        input_raw_sha256=certificate.raw_sha256,
        input_normalized_sha256=certificate.normalized_sha256,
        n=n,
        integer_scale=integer_scale,
        target_scale=target_fraction,
        residual=residual,
        census=census,
        symmetrization_transport_checked=transport_checked,
        execution_complete=True,
        failure_reasons=tuple(failures),
    )
