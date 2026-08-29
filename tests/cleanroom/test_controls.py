from __future__ import annotations

from fractions import Fraction
import hashlib
import json
from pathlib import Path
import platform
import sys
import unittest

from cleanroom.maxrelu import (
    parse_for_control,
    run_two_arm_control,
    verify_certificate,
)

from _fixture import (
    fixture_bytes,
    fixture_certificate,
    fixture_object,
    fixture_spec,
)


_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_IMPLEMENTATION_HASHER = hashlib.sha256()
for _relative in (
    "cleanroom/maxrelu/__init__.py",
    "cleanroom/maxrelu/model.py",
    "cleanroom/maxrelu/verifier.py",
    "cleanroom/maxrelu/controls.py",
):
    _IMPLEMENTATION_HASHER.update(_relative.encode("utf-8") + b"\0")
    _IMPLEMENTATION_HASHER.update((_PROJECT_ROOT / _relative).read_bytes())
_IMPLEMENTATION_SHA256 = _IMPLEMENTATION_HASHER.hexdigest()
_ENVIRONMENT_SHA256 = hashlib.sha256(
    json.dumps(
        {
            "implementation": platform.python_implementation(),
            "python": sys.version,
            "platform": platform.platform(),
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
).hexdigest()


def _run_control(
    method,
    positive,
    hostile,
    hostile_mutation_id,
    *,
    positive_expected_outcome="ACCEPT",
    hostile_expected_outcome="REJECT",
):
    return run_two_arm_control(
        method,
        positive,
        hostile,
        implementation_sha256=_IMPLEMENTATION_SHA256,
        environment_sha256=_ENVIRONMENT_SHA256,
        positive_mutation_id="synthetic-pristine",
        hostile_mutation_id=hostile_mutation_id,
        positive_expected_outcome=positive_expected_outcome,
        hostile_expected_outcome=hostile_expected_outcome,
    )


def _scaled_by_two_certificate():
    value = fixture_object()
    for term in value["terms"]:
        term["coefficient"] = str(Fraction(term["coefficient"]) * 2)
    return fixture_certificate(value)


class ControlHarnessTests(unittest.TestCase):
    def test_known_answer_reports_both_directions(self) -> None:
        report = _run_control(
            "known-answer",
            lambda: verify_certificate(fixture_certificate()),
            lambda: verify_certificate(_scaled_by_two_certificate()),
            "coefficients-x2-target-fixed",
        )
        self.assertEqual(report.positive.observed, "ACCEPT")
        self.assertEqual(report.hostile.observed, "REJECT")
        self.assertEqual(report.status, "PASS")
        self.assertIsNotNone(report.positive.result_sha256)
        self.assertIsNotNone(report.hostile.result_sha256)
        self.assertEqual(
            report.positive.normalized_subject_sha256,
            verify_certificate(fixture_certificate()).input_normalized_sha256,
        )
        self.assertEqual(report.positive.census.observed_contributions, 4)
        self.assertGreaterEqual(report.positive.elapsed_ns, 0)
        self.assertGreater(report.positive.process_peak_rss_kib, 0)
        self.assertEqual(len(report.sha256()), 64)

    def test_census_control_qualifies_expected_typed_incomplete(self) -> None:
        report = _run_control(
            "census-reconciliation",
            lambda: verify_certificate(fixture_certificate()),
            lambda: verify_certificate(
                fixture_certificate(), rank_plans={0: (1, 1), 1: (0, 1)}
            ),
            "omit-rank-0-duplicate-rank-1",
            hostile_expected_outcome="INCOMPLETE",
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.hostile.observed, "INCOMPLETE")
        self.assertEqual(report.hostile.operational_status, "COMPLETED")
        self.assertTrue(report.hostile.expectation_met)
        self.assertEqual(
            report.payload()["hostile"]["observed_outcome"], "INCOMPLETE"
        )

    def test_exception_is_incomplete_and_never_passes_as_rejection(self) -> None:
        def interrupted_arm():
            raise RuntimeError("planted interruption")

        report = _run_control(
            "incomplete-work-refusal",
            lambda: verify_certificate(fixture_certificate()),
            interrupted_arm,
            "planted-interruption",
            hostile_expected_outcome="INCOMPLETE",
        )
        self.assertEqual(report.positive.observed, "ACCEPT")
        self.assertIsNone(report.hostile.observed)
        self.assertEqual(report.hostile.operational_status, "ABORTED")
        self.assertEqual(report.status, "INCOMPLETE")
        self.assertFalse(report.hostile.expectation_met)
        self.assertIn("RuntimeError", report.hostile.operational_error)

    def test_timeout_is_operational_abort_not_typed_subject_incomplete(self) -> None:
        def timed_out_arm():
            raise TimeoutError("planted deadline expiry")

        report = _run_control(
            "timeout-refusal",
            lambda: verify_certificate(fixture_certificate()),
            timed_out_arm,
            "planted-timeout",
            hostile_expected_outcome="INCOMPLETE",
        )
        self.assertEqual(report.positive.observed, "ACCEPT")
        self.assertIsNone(report.hostile.observed)
        self.assertEqual(report.hostile.operational_status, "ABORTED")
        self.assertEqual(report.status, "INCOMPLETE")
        self.assertFalse(report.hostile.expectation_met)
        self.assertIn("TimeoutError", report.hostile.operational_error)

    def test_parser_rejection_is_a_typed_expected_subject_outcome(self) -> None:
        hostile = fixture_object()
        hostile["unexpected"] = True
        report = _run_control(
            "parser-contract",
            lambda: parse_for_control(fixture_bytes(), fixture_spec()),
            lambda: parse_for_control(fixture_bytes(hostile), fixture_spec()),
            "unknown-root-key",
            positive_expected_outcome="PARSED",
            hostile_expected_outcome="PARSER_REJECT",
        )
        self.assertEqual(report.status, "PASS")
        self.assertEqual(report.positive.observed, "PARSED")
        self.assertEqual(report.hostile.observed, "PARSER_REJECT")
        self.assertEqual(report.hostile.operational_status, "COMPLETED")
        self.assertIsNotNone(report.hostile.input_raw_sha256)
        self.assertIsNone(report.hostile.normalized_subject_sha256)

    def test_unwrapped_parser_exception_is_operational_abort(self) -> None:
        def unwrapped_parser_error():
            hostile = fixture_object()
            hostile["unexpected"] = True
            from cleanroom.maxrelu import parse_certificate_bytes

            return parse_certificate_bytes(fixture_bytes(hostile), fixture_spec())

        report = _run_control(
            "parser-contract-unwrapped",
            lambda: parse_for_control(fixture_bytes(), fixture_spec()),
            unwrapped_parser_error,
            "unknown-root-key-unwrapped",
            positive_expected_outcome="PARSED",
            hostile_expected_outcome="PARSER_REJECT",
        )
        self.assertEqual(report.status, "INCOMPLETE")
        self.assertEqual(report.hostile.operational_status, "ABORTED")
        self.assertIsNone(report.hostile.observed)

    def test_wrong_positive_verdict_is_fail(self) -> None:
        report = _run_control(
            "directionality",
            lambda: verify_certificate(_scaled_by_two_certificate()),
            lambda: verify_certificate(_scaled_by_two_certificate()),
            "coefficients-x2-target-fixed",
        )
        self.assertEqual(report.status, "FAIL")
        self.assertEqual(report.positive.observed, "REJECT")


if __name__ == "__main__":
    unittest.main()
