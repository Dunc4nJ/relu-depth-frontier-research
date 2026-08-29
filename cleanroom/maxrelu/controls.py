"""Two-arm controls with typed subject outcomes and operational status."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
import json
import re
import resource
import time

from .model import (
    CertificateFormatError,
    SubjectSpec,
    parse_certificate_bytes,
)
from .verifier import Census, VerificationResult


_OUTCOMES = frozenset(
    {"ACCEPT", "REJECT", "INCOMPLETE", "PARSED", "PARSER_REJECT"}
)


@dataclass(frozen=True)
class ParserControlResult:
    """Completed parser attempt, distinct from an operational exception."""

    outcome: str
    subject_id: str
    input_raw_sha256: str
    input_normalized_sha256: str | None
    reason: str | None

    def __post_init__(self) -> None:
        if self.outcome not in {"PARSED", "PARSER_REJECT"}:
            raise ValueError("parser outcome must be PARSED or PARSER_REJECT")
        if type(self.subject_id) is not str or not self.subject_id:
            raise ValueError("parser subject_id must be nonempty")
        for field_name in ("input_raw_sha256", "input_normalized_sha256"):
            value = getattr(self, field_name)
            if value is not None and (
                type(value) is not str
                or re.fullmatch(r"[0-9a-f]{64}", value) is None
            ):
                raise ValueError(f"{field_name} must be a lowercase SHA-256 digest")
        if self.outcome == "PARSED" and self.input_normalized_sha256 is None:
            raise ValueError("PARSED requires a normalized subject digest")
        if self.outcome == "PARSER_REJECT" and self.reason is None:
            raise ValueError("PARSER_REJECT requires a reason")

    def payload(self) -> dict[str, object]:
        return {
            "schema": "maxrelu-cleanroom-parser-control-v1",
            "outcome": self.outcome,
            "subject_id": self.subject_id,
            "input_raw_sha256": self.input_raw_sha256,
            "input_normalized_sha256": self.input_normalized_sha256,
            "reason": self.reason,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def parse_for_control(raw: bytes, spec: SubjectSpec) -> ParserControlResult:
    """Turn an expected schema decision into a typed, hash-bound outcome.

    Only ``CertificateFormatError`` becomes ``PARSER_REJECT``.  Programming,
    resource, and other unexpected exceptions escape for the outer control
    harness to classify as operational aborts.
    """

    if type(raw) is not bytes:
        raise TypeError("parser control input must be bytes")
    if type(spec) is not SubjectSpec:
        raise TypeError("parser control spec must be an exact SubjectSpec")
    raw_sha256 = hashlib.sha256(raw).hexdigest()
    try:
        certificate = parse_certificate_bytes(raw, spec)
    except CertificateFormatError as exc:
        return ParserControlResult(
            outcome="PARSER_REJECT",
            subject_id=spec.subject_id,
            input_raw_sha256=raw_sha256,
            input_normalized_sha256=None,
            reason=f"{type(exc).__name__}: {exc}",
        )
    return ParserControlResult(
        outcome="PARSED",
        subject_id=certificate.subject_id,
        input_raw_sha256=certificate.raw_sha256,
        input_normalized_sha256=certificate.normalized_sha256,
        reason=None,
    )


@dataclass(frozen=True)
class ArmObservation:
    arm: str
    mutation_id: str
    expected_outcome: str
    observed_outcome: str | None
    operational_status: str
    subject_id: str | None
    input_raw_sha256: str | None
    normalized_subject_sha256: str | None
    census: Census | None
    elapsed_ns: int
    process_peak_rss_kib: int
    result_sha256: str | None
    outcome_reason: str | None
    operational_error: str | None

    @property
    def expected(self) -> str:
        return self.expected_outcome

    @property
    def observed(self) -> str | None:
        return self.observed_outcome

    @property
    def expectation_met(self) -> bool:
        return (
            self.operational_status == "COMPLETED"
            and self.observed_outcome == self.expected_outcome
        )

    def payload(self) -> dict[str, object]:
        return {
            "arm": self.arm,
            "mutation_id": self.mutation_id,
            "expected_outcome": self.expected_outcome,
            "observed_outcome": self.observed_outcome,
            "operational_status": self.operational_status,
            "expectation_met": self.expectation_met,
            "subject_id": self.subject_id,
            "input_raw_sha256": self.input_raw_sha256,
            "normalized_subject_sha256": self.normalized_subject_sha256,
            "census": self.census.payload() if self.census is not None else None,
            "elapsed_ns": self.elapsed_ns,
            "process_peak_rss_kib": self.process_peak_rss_kib,
            "result_sha256": self.result_sha256,
            "outcome_reason": self.outcome_reason,
            "operational_error": self.operational_error,
        }


@dataclass(frozen=True)
class ControlReport:
    method: str
    implementation_sha256: str
    environment_sha256: str
    positive: ArmObservation
    hostile: ArmObservation

    @property
    def status(self) -> str:
        if (
            self.positive.operational_status != "COMPLETED"
            or self.hostile.operational_status != "COMPLETED"
        ):
            return "INCOMPLETE"
        if self.positive.expectation_met and self.hostile.expectation_met:
            return "PASS"
        return "FAIL"

    def payload(self) -> dict[str, object]:
        return {
            "schema": "maxrelu-cleanroom-control-v2",
            "method": self.method,
            "implementation_sha256": self.implementation_sha256,
            "environment_sha256": self.environment_sha256,
            "positive": self.positive.payload(),
            "hostile": self.hostile.payload(),
            "status": self.status,
        }

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            self.payload(), sort_keys=True, separators=(",", ":"), allow_nan=False
        ).encode("ascii")

    def sha256(self) -> str:
        return hashlib.sha256(self.canonical_bytes()).hexdigest()


def _aborted_observation(
    *,
    arm: str,
    mutation_id: str,
    expected_outcome: str,
    started_ns: int,
    error: str,
) -> ArmObservation:
    return ArmObservation(
        arm=arm,
        mutation_id=mutation_id,
        expected_outcome=expected_outcome,
        observed_outcome=None,
        operational_status="ABORTED",
        subject_id=None,
        input_raw_sha256=None,
        normalized_subject_sha256=None,
        census=None,
        elapsed_ns=time.perf_counter_ns() - started_ns,
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        result_sha256=None,
        outcome_reason=None,
        operational_error=error,
    )


def _observe(
    arm: str,
    mutation_id: str,
    expected_outcome: str,
    invocation: Callable[[], VerificationResult | ParserControlResult],
) -> ArmObservation:
    started = time.perf_counter_ns()
    try:
        result = invocation()
    except Exception as exc:
        return _aborted_observation(
            arm=arm,
            mutation_id=mutation_id,
            expected_outcome=expected_outcome,
            started_ns=started,
            error=f"{type(exc).__name__}: {exc}",
        )

    if isinstance(result, VerificationResult):
        observed_outcome = result.outcome
        subject_id = result.subject_id
        raw_sha256 = result.input_raw_sha256
        normalized_sha256 = result.input_normalized_sha256
        census = result.census
        result_sha256 = result.sha256()
        outcome_reason = ",".join(result.failure_reasons) or None
    elif isinstance(result, ParserControlResult):
        observed_outcome = result.outcome
        subject_id = result.subject_id
        raw_sha256 = result.input_raw_sha256
        normalized_sha256 = result.input_normalized_sha256
        census = None
        result_sha256 = result.sha256()
        outcome_reason = result.reason
    else:
        return _aborted_observation(
            arm=arm,
            mutation_id=mutation_id,
            expected_outcome=expected_outcome,
            started_ns=started,
            error="arm returned an unsupported result type",
        )

    return ArmObservation(
        arm=arm,
        mutation_id=mutation_id,
        expected_outcome=expected_outcome,
        observed_outcome=observed_outcome,
        operational_status="COMPLETED",
        subject_id=subject_id,
        input_raw_sha256=raw_sha256,
        normalized_subject_sha256=normalized_sha256,
        census=census,
        elapsed_ns=time.perf_counter_ns() - started,
        process_peak_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
        result_sha256=result_sha256,
        outcome_reason=outcome_reason,
        operational_error=None,
    )


def run_two_arm_control(
    method: str,
    positive: Callable[[], VerificationResult | ParserControlResult],
    hostile: Callable[[], VerificationResult | ParserControlResult],
    *,
    implementation_sha256: str,
    environment_sha256: str,
    positive_mutation_id: str,
    hostile_mutation_id: str,
    positive_expected_outcome: str = "ACCEPT",
    hostile_expected_outcome: str = "REJECT",
) -> ControlReport:
    """Run both directions without conflating subject nulls and aborts.

    A completed verifier may correctly report ``INCOMPLETE`` for a planted
    census defect, and that arm can be expected by the control.  An exception,
    timeout wrapper, or unsupported return is operationally ``ABORTED`` and
    always makes the control report ``INCOMPLETE``.  Parser controls may expect
    ``PARSED``/``PARSER_REJECT`` through :func:`parse_for_control`.
    """

    if type(method) is not str or not method:
        raise ValueError("control method must be a nonempty string")
    for name, digest in (
        ("implementation_sha256", implementation_sha256),
        ("environment_sha256", environment_sha256),
    ):
        if type(digest) is not str or re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError(f"{name} must be a lowercase SHA-256 hex digest")
    for name, mutation_id in (
        ("positive_mutation_id", positive_mutation_id),
        ("hostile_mutation_id", hostile_mutation_id),
    ):
        if type(mutation_id) is not str or not mutation_id:
            raise ValueError(f"{name} must be a nonempty string")
    if positive_mutation_id == hostile_mutation_id:
        raise ValueError("positive and hostile mutation IDs must differ")
    for name, outcome in (
        ("positive_expected_outcome", positive_expected_outcome),
        ("hostile_expected_outcome", hostile_expected_outcome),
    ):
        if outcome not in _OUTCOMES:
            raise ValueError(f"{name} is not a supported typed outcome")

    positive_observation = _observe(
        "positive", positive_mutation_id, positive_expected_outcome, positive
    )
    hostile_observation = _observe(
        "hostile", hostile_mutation_id, hostile_expected_outcome, hostile
    )
    return ControlReport(
        method,
        implementation_sha256,
        environment_sha256,
        positive_observation,
        hostile_observation,
    )
